"""Sourced CS venue rules and the shared source/edition contracts."""

import json
import re
import zipfile
from pathlib import Path

import pytest

from paperpush.database import Field, Venue, get_venue
from paperpush.requirements import ManuscriptRequirements, ManuscriptRules, get_requirements, resolve
from paperpush.requirements_check import _heading_issues, _template_source_issues, check_manuscript_requirements
from paperpush.subfile import SubFile
from paperpush.template_check import identity_problems
from paperpush.validate import validate
from tests.pdf_builder import text_line, write_pdf

MANUSCRIPT = Field("manuscript_file", "Manuscript", "file")


def pdf(tmp_path, content_pages, reference_pages=0, appendix_pages=0):
    pages = [text_line(72, 700, "Introduction" if n == 0 else "Main results") for n in range(content_pages)]
    pages += [text_line(72, 700, "References" if n == 0 else "1. Example citation, 2024.") for n in range(reference_pages)]
    pages += [text_line(72, 700, "Appendix" if n == 0 else "Additional proof") for n in range(appendix_pages)]
    return write_pdf(tmp_path / f"paper-{content_pages}-{reference_pages}-{appendix_pages}.pdf", pages)


@pytest.mark.parametrize("slug,stage,limit", [("ieee_tvt", "Regular (initial)", 14), ("ieee_tvt", "Correspondence (initial)", 5), ("ieee_tvt", "Regular (revision)", 16), ("ieee_tvt", "Correspondence (revision)", 6), ("ieee_twc", "Initial", 13), ("ieee_twc", "Revision", 16), ("ieee_tnse", "", 18)])
def test_ieee_limits_include_references_and_follow_stage(tmp_path, slug, stage, limit):
    venue = get_venue(slug)
    path = pdf(tmp_path, limit - 1, 2)
    issues = check_manuscript_requirements(venue, {"manuscript_file": str(path), "article_type": stage})
    assert any(i.level == "error" and f"{limit}-page limit" in i.message for i in issues)
    path = pdf(tmp_path, limit - 1, 1)
    issues = check_manuscript_requirements(venue, {"manuscript_file": str(path), "article_type": stage})
    assert not any(i.level == "error" and "page limit" in i.message for i in issues)


@pytest.mark.parametrize("slug,limit", [("mobicom_2026_winter", 12), ("mobisys_2026", 12), ("neurips_2025", 9), ("sensys_2026_nov", 12)])
def test_conference_reference_pages_excluded(tmp_path, slug, limit):
    path = pdf(tmp_path, limit, 4)
    issues = check_manuscript_requirements(get_venue(slug), {"manuscript_file": str(path)})
    assert not any(i.level == "error" and "page limit" in i.message for i in issues)
    path = pdf(tmp_path, limit + 1, 1)
    issues = check_manuscript_requirements(get_venue(slug), {"manuscript_file": str(path)})
    assert any(i.level == "error" and "page limit" in i.message for i in issues)


def test_sensys_short_limit_and_appendix_prohibition(tmp_path):
    path = pdf(tmp_path, 7, 1, 1)
    issues = check_manuscript_requirements(get_venue("sensys_2026_nov"), {"manuscript_file": str(path), "article_type": "Experiences short paper"})
    assert any("6-page limit" in i.message for i in issues)
    assert any(i.message.startswith("appendix:") for i in issues)


def test_conditional_ethics_statement(tmp_path):
    path = pdf(tmp_path, 1)
    reqs = get_requirements("sensys_2026_nov")
    assert not _heading_issues(MANUSCRIPT, path, reqs, {"human_participants": "no"})
    assert not _heading_issues(MANUSCRIPT, path, reqs, {})
    assert any("ethics" in i.message for i in _heading_issues(MANUSCRIPT, path, reqs, {"human_participants": "yes"}))


@pytest.mark.parametrize("slug,anonymous", [("mobicom_2026_winter", True), ("sensys_2026_nov", True), ("neurips_2025", True), ("mobisys_2026", False)])
def test_anonymity_uses_edition_policy(tmp_path, slug, anonymous):
    path = write_pdf(tmp_path / "paper.pdf", [text_line(72, 700, "Ada Example"), text_line(72, 700, "ada@example.edu")])
    author = "~Ada_Example1 | Ada Example | example.edu" if slug == "neurips_2025" else "Ada Example | ada@example.edu | Example University |  | yes"
    sub = SubFile(venue=slug, values={"title": "Test", "abstract": "An abstract", "authors": author, "manuscript_file": str(path)})
    issues = validate(sub, get_venue(slug), check_sensitive=False, check_links=False, check_references=False, check_hidden_text=False, check_openreview=False)
    assert any("anonymity:" in i.message for i in issues) == anonymous


@pytest.mark.parametrize(
    "style,options,text,ok",
    [
        ("IEEEtran", [], r"\documentclass[journal]{IEEEtran}", True),
        ("IEEEtran", [], r"% \documentclass{IEEEtran}" + "\n" + r"\documentclass{article}", False),
        ("acmart", ["sigconf", "anonymous"], r"\documentclass[anonymous,review,sigconf]{acmart}", True),
        ("acmart", ["sigconf", "anonymous"], r"\documentclass[sigconf]{acmart}", False),
        ("acmart", [], r"\documentclass{IEEEtran}", False),
        ("neurips_2025", [], r"\documentclass{article}\usepackage{neurips_2025}", True),
    ],
)
def test_class_and_options(style, options, text, ok):
    assert (not list(identity_problems(text, style, options))) == ok


def test_class_checked_inside_source_bundle(tmp_path):
    path = tmp_path / "source.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("main.tex", r"\documentclass{article}")
        archive.writestr("part.tex", r"\section{Methods}")
    reqs = ManuscriptRequirements(slug="fixture", manuscript=ManuscriptRules(template_required=True, latex_class="acmart"))
    issues = _template_source_issues(Venue(slug="fixture", fields=[MANUSCRIPT]), reqs, {"manuscript_file": str(path)})
    assert len(issues) == 1
    assert "source.zip:main.tex" in issues[0].message and "acmart" in issues[0].message


def test_new_entries_have_provenance_and_explicit_editions():
    raw = json.loads(Path("paperpush/venues.json").read_text())
    reqs = json.loads(Path("paperpush/manuscript_requirements.json").read_text())
    slugs = [s for s in raw if raw[s].get("platform")]
    for slug in slugs:
        venue = get_venue(slug)
        assert venue.source_urls
        assert reqs[slug]["source_urls"]
        if venue.venue_type == "conference":
            assert re.fullmatch(r"\d{4}", venue.edition["year"])
            assert venue.edition["cycle"]
            assert venue.edition["year"] in slug
        if not venue.submission_url:
            assert venue.unverified
            assert any("UNVERIFIED" in n for n in reqs[slug].get("notes", [])) or slug == "ieee_tvt"


def test_charge_threshold_is_not_a_page_cap():
    assert get_requirements("ieee_iot").manuscript.max_pages is None
    assert get_requirements("ieee_jsac").manuscript.max_pages is None


def test_sourced_tvt_figure_and_reference_rules(tmp_path):
    from PIL import Image

    manuscript = pdf(tmp_path, 1)
    image = tmp_path / "figure.png"
    Image.new("RGB", (3000, 3000)).save(image, dpi=(300, 300))
    issues = check_manuscript_requirements(get_venue("ieee_tvt"), {"manuscript_file": str(manuscript), "figure_files": str(image), "article_type": "Regular (initial)"})
    assert any("220 mm" in i.message for i in issues)
    assert any("no 'References' section" in i.message for i in issues)
