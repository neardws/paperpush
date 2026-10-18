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
            assert any("UNVERIFIED" in n for n in reqs[slug].get("notes", [])) or slug in {"ieee", "ieee_tvt"}


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


@pytest.mark.parametrize("slug", ["ieee_tits", "ieee:t-its"])
@pytest.mark.parametrize("article_type,limit", [("Regular", 16), ("Short", 12), ("Practitioner", 12), ("Survey", 24)])
def test_verified_tits_page_caps_and_reference_scope(tmp_path, slug, article_type, limit):
    venue = get_venue(slug)
    reqs = resolve(get_requirements(slug), {"article_type": article_type})
    assert reqs.manuscript.max_pages_before_refs == limit
    assert reqs.manuscript.max_pages is None
    # References-counting policy is unstated: enforce main text, leave the
    # whole-document question to the author instead of inventing a stricter cap.
    at_limit = pdf(tmp_path, limit, 3)
    issues = check_manuscript_requirements(venue, {"article_type": article_type, "manuscript_file": str(at_limit)})
    assert not any(i.level == "error" and "page limit" in i.message for i in issues)
    over_limit = pdf(tmp_path, limit + 1, 1)
    issues = check_manuscript_requirements(venue, {"article_type": article_type, "manuscript_file": str(over_limit)})
    assert any(i.level == "error" and f"{limit}-page limit" in i.message for i in issues)


@pytest.mark.parametrize("slug", ["ieee_tits", "ieee:t-its"])
@pytest.mark.parametrize("words,error", [(149, True), (150, False), (250, False), (251, True)])
def test_tits_journal_abstract_bounds_are_errors(slug, words, error):
    issues = check_manuscript_requirements(get_venue(slug), {"abstract": "word " * words})
    assert any(i.level == "error" and i.field == "abstract" for i in issues) == error
    assert not any("IEEE style guidance: abstract" in i.message for i in issues)


@pytest.mark.parametrize("slug", ["ieee_tits", "ieee:t-its"])
def test_verified_tits_metadata_and_keyword_groups(slug):
    venue = get_venue(slug)
    reqs = get_requirements(slug)
    assert venue.submission_url == "https://ieee.atyponrex.com/journal/t-its"
    assert venue.anonymous is False and reqs.manuscript.anonymized is False
    assert reqs.manuscript.template_required is True
    assert reqs.manuscript.latex_class == "IEEEtran"
    assert reqs.manuscript.double_spacing is False
    assert reqs.abstract.no_references is True and reqs.abstract.no_abbreviations is True
    assert reqs.keywords.max == 6
    assert not any("UNVERIFIED" in n for n in reqs.notes)
    assert any("Single-anonymous" in n for n in reqs.notes)
    assert any("biographies and photos" in n for n in reqs.notes)
    assert any("prior paper ID" in n for n in reqs.cover_letter.notes)
    fields = {f.id: f for f in venue.fields}
    assert "keywords" not in fields
    assert not fields["cover_letter"].required
    for fid, required, minimum in [("free_keywords", False, 0), ("methodology_keywords", True, 1), ("application_keywords", True, 1)]:
        assert fields[fid].type == "multichoice"
        assert fields[fid].required is required
        assert fields[fid].min_count == minimum and fields[fid].max_count == 2


@pytest.mark.parametrize("slug", ["ieee_tits", "ieee:t-its"])
@pytest.mark.parametrize("field", ["free_keywords", "methodology_keywords", "application_keywords"])
def test_tits_keyword_groups_cannot_exceed_six_total(slug, field):
    values = {"free_keywords": "first, second", "methodology_keywords": "method one, method two", "application_keywords": "application one, application two"}
    options = dict(check_sensitive=False, check_links=False, check_references=False, check_manuscript=False, check_hidden_text=False, check_openreview=False)
    venue = get_venue(slug)
    assert not any(i.level == "error" and i.field in values for i in validate(SubFile(venue=slug, values=values), venue, **options))
    values[field] += ", extra"
    assert any(i.level == "error" and i.field == field for i in validate(SubFile(venue=slug, values=values), venue, **options))
    values[field] = ""
    errors = validate(SubFile(venue=slug, values=values), venue, **options)
    assert any(i.level == "error" and i.field == field for i in errors) == (field != "free_keywords")
