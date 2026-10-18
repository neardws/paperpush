"""Generic IEEE targets, sourced guidance, and attended ReX safety contracts."""

import json
from pathlib import Path

import pytest

from paperpush.database import get_venue
from paperpush.requirements import get_requirements
from paperpush.requirements_check import check_manuscript_requirements
from paperpush.subfile import SubFile, parse, render_template
from paperpush.validate import validate
from paperpush.venues import get_field_validators, get_runner, get_venue_impl
from tests.pdf_builder import text_line, write_pdf
from tests.test_configured_portals import browser  # shared offline browser fixture

TARGET = "ieee:unconfigured-journal"
FIXTURES = Path(__file__).parent / "fixtures" / "platforms" / "rex"


@pytest.mark.parametrize("code", ["t-its", "abc123", "tnse-cs", "X-7"])
def test_dynamic_target_schema_runner_and_roundtrip(code):
    venue = get_venue(f"IEEE:{code}")
    assert venue.slug == f"ieee:{code.lower()}"
    assert venue.submission_url == f"https://ieee.atyponrex.com/journal/{code.lower()}"
    assert venue.platform == "rex"
    assert parse(render_template(venue)).venue == venue.slug
    assert get_runner(venue.slug).__self__.slug == venue.slug
    assert get_field_validators(venue.slug) == {}


@pytest.mark.parametrize("code", ["", "../x", "x/y", "x?redirect=evil", "x#fragment", "%2f", "x_y", "x--y", "-x", "x-", "x.y", " x", "é", "a" * 65, "https://example.org", "x\\y"])
def test_invalid_codes_rejected_everywhere(code):
    for lookup in (get_venue, get_requirements, get_venue_impl):
        with pytest.raises(KeyError, match="Invalid IEEE journal code"):
            lookup(f"ieee:{code}")


@pytest.mark.parametrize("slug,code", [("ieee_twc", "twc"), ("ieee_tnse", "tnse-cs"), ("ieee_iot", "iot"), ("ieee_tits", "t-its")])
def test_known_code_keeps_configured_rules(slug, code):
    direct, dynamic = get_venue(slug), get_venue(f"ieee:{code}")
    assert direct.fields == dynamic.fields
    a, b = get_requirements(slug).to_dict(), get_requirements(dynamic.slug).to_dict()
    for key in ("slug", "inherits"):
        a.pop(key, None)
        b.pop(key, None)
    assert a == b
    assert direct.inherits == "ieee"
    assert get_venue_impl(slug).__class__.__name__ == "RexVenue"


def test_unconfigured_has_no_invented_limits(tmp_path):
    reqs = get_requirements(TARGET)
    assert reqs.manuscript.max_pages is None
    assert reqs.abstract.max_words is None
    assert reqs.abstract.min_words is None
    assert reqs.keywords.max is None
    assert reqs.figures.min_dpi is None
    assert reqs.references.max_count is None
    assert any("Only generic IEEE checks" in n for n in reqs.notes)
    path = write_pdf(tmp_path / "paper.pdf", [text_line(72, 700, "Prior work (Smith, 2024).")])
    issues = check_manuscript_requirements(get_venue(TARGET), {"manuscript_file": str(path), "abstract": "word " * 300})
    assert issues and all(i.level == "warning" for i in issues)
    assert any("Only generic IEEE checks" in i.message for i in issues)
    assert any("150–250" in i.message for i in issues)
    assert any("square-bracket" in i.message for i in issues)
    assert any("detection was not possible" in i.message for i in issues)


@pytest.mark.parametrize("slug,words,exceeds", [("ieee_twc", 201, True), ("ieee:twc", 201, True), (TARGET, 301, False)])
def test_journal_abstract_limit_remains_enforced(slug, words, exceeds):
    issues = check_manuscript_requirements(get_venue(slug), {"abstract": "word " * words})
    assert any(i.level == "error" and "word limit" in i.message for i in issues) == exceeds
    if slug != TARGET:
        assert not any("150–250" in i.message for i in issues)


@pytest.mark.parametrize("citation,warning", [("Previous work [1].", False), ("Previous work [1, 2].", False), ("Previous work (Smith, 2024).", True), ("Previous work.\nReferences\n[1] Smith, 2024.", True)])
def test_ieee_reference_style_checks_body(tmp_path, citation, warning):
    path = write_pdf(tmp_path / "paper.pdf", [text_line(72, 700 - n * 20, line) for n, line in enumerate(citation.splitlines())])
    issues = check_manuscript_requirements(get_venue(TARGET), {"manuscript_file": str(path)})
    assert any("IEEE references:" in i.message for i in issues) == warning


def test_latex_pair_required_and_archive_class_checked(tmp_path):
    import zipfile

    source, pdf = tmp_path / "source.zip", tmp_path / "paper.pdf"
    write_pdf(pdf, [text_line(72, 700, "Prior work [1].")])
    with zipfile.ZipFile(source, "w") as z:
        z.writestr("main.tex", r"% \documentclass{IEEEtran}" + "\n" + r"\documentclass{article}")
    venue = get_venue(TARGET)
    values = {"title": "Test", "abstract": "word " * 180, "authors": "Ada | ada@example.org | Example University | | yes", "manuscript_file": str(pdf), "latex_source_file": str(source)}
    issues = validate(SubFile(venue=TARGET, values=values), venue, check_sensitive=False, check_links=False, check_references=False, check_hidden_text=False)
    assert any(i.level == "error" and i.field == "latex_pdf_file" for i in issues)
    assert any("IEEEtran" in i.message and "source.zip:main.tex" in i.message for i in issues)
    values["latex_pdf_file"] = str(pdf)
    issues = validate(SubFile(venue=TARGET, values=values), venue, check_sensitive=False, check_links=False, check_references=False, check_hidden_text=False)
    assert not any(i.level == "error" for i in issues)


def test_generic_cli_preparation_pipeline(tmp_path, capsys):
    from paperpush.cli import main

    sub, values = tmp_path / "paper.sub", tmp_path / "values.json"
    assert main(["subfile", TARGET, "-o", str(sub)]) == 0
    assert main(["schema", TARGET]) == 0
    assert main(["requirements", TARGET]) == 0
    assert "Only generic IEEE checks" in capsys.readouterr().out
    values.write_text(json.dumps({"fields": [{"id": "title", "value": "Copied title", "confidence": "high", "source": "manuscript"}], "unfilled": []}))
    assert main(["autofill", str(sub), "-d", str(tmp_path), "--engine", "manual", "--values", str(values)]) == 0
    assert parse(sub.read_text()).values["title"] == "Copied title"
    # Missing author metadata/files must still be caught without a browser.
    assert main(["validate", str(sub), "--dont-check-links", "--dont-check-references"]) == 1


@pytest.mark.parametrize("fixture", sorted(FIXTURES.glob("*.html")), ids=lambda p: p.stem)
def test_all_wizard_steps_never_click_or_confirm(browser, fixture, tmp_path):
    impl = get_venue_impl(TARGET)
    page = browser.new_page()
    page.route("**/*", lambda route: route.abort())
    page.set_content(fixture.read_text())
    source, pdf, letter = tmp_path / "main.tex", tmp_path / "main.pdf", tmp_path / "letter.pdf"
    source.write_text(r"\documentclass{IEEEtran}")
    pdf.write_bytes(b"fixture")
    letter.write_bytes(b"fixture")
    values = {"title": "Copied title", "abstract": "Copied abstract", "keywords": "Networks; Systems", "authors": "Ada | ada@example.org | University | | yes", "portal_article_type": "Research Article", "latex_source_file": str(source), "latex_pdf_file": str(pdf), "cover_letter": str(letter), "additional_information": "consent yes", "submission_requirements": "yes", "peer_review_type": "Double anonymized"}
    filled, manual = impl.fill_page(page, values)
    assert page.evaluate("window.clicks") == []
    assert "confirm" in impl.page_instructions(page).lower() or fixture.stem == "final-review"
    assert "authors" in manual
    assert "additional_information" in manual
    if fixture.stem == "upload-manuscript":
        assert {"latex_source_file", "latex_pdf_file", "cover_letter"} <= set(filled)
        changes = page.evaluate("window.changes")
        impl.fill_page(page, values)
        assert page.evaluate("window.changes") == changes
    elif fixture.stem == "article-type":
        assert "portal_article_type" in filled
    elif fixture.stem == "title":
        assert page.get_by_label("Title", exact=True).input_value() == "Copied title"
    elif fixture.stem == "abstract":
        assert page.get_by_role("textbox").inner_text() == "Copied abstract"
    elif fixture.stem == "final-review":
        assert filled == []
        assert page.get_by_label("Title", exact=True).input_value() == "reviewed title"
    assert page.evaluate("window.clicks") == []
    page.close()


def test_rex_incomplete_pair_and_ambiguous_upload_are_manual(browser, tmp_path):
    impl = get_venue_impl(TARGET)
    page = browser.new_page()
    page.set_content((FIXTURES / "upload-manuscript.html").read_text())
    source = tmp_path / "main.tex"
    source.write_text("test")
    assert impl.fill_page(page, {"latex_source_file": str(source)}) == ([], ["latex_source_file"])
    page.set_content('<label>Main Document - LaTeX<input type="file"></label>' * 2 + '<label>Main Document - LaTeX PDF<input type="file"></label>')
    filled, manual = impl.fill_page(page, {"latex_source_file": str(source), "latex_pdf_file": str(source)})
    assert "latex_source_file" in manual
    page.close()


@pytest.mark.parametrize("html", ["<label>Title<input readonly></label>", '<label>Title<input type="hidden"></label>', "<label>Title<button>Submit</button></label>", "<label>Title<input disabled></label>", "<label>Title<input></label>" * 2])
def test_rex_unsafe_or_ambiguous_widget_is_manual(browser, html):
    page = browser.new_page()
    page.set_content(html)
    assert get_venue_impl(TARGET).fill_page(page, {"title": "Test"}) == ([], ["title"])
    page.close()


@pytest.mark.parametrize("label", ["Submit", "Complete my submission", "Complete my revision", "Build Reviewer PDF", "Save", "Continue", "Save and Continue", "Confirm", "Confirm title", "Confirm author(s)"])
def test_forbidden_buttons_never_clicked_even_with_binding_override(browser, label, monkeypatch):
    from dataclasses import replace
    from paperpush.venues.rex import main as rex

    venue = replace(get_venue(TARGET), portal_fields={"title": "button"})
    monkeypatch.setattr(rex, "get_venue", lambda slug: venue)
    page = browser.new_page()
    page.set_content(f'<button onclick="window.clicked=true">{label}</button><script>window.clicked=false</script>')
    assert get_venue_impl(TARGET).fill_page(page, {"title": "Test"}) == ([], ["title"])
    assert page.evaluate("window.clicked") is False
    page.close()


def test_changed_upload_with_same_name_is_not_skipped(browser, tmp_path):
    impl = get_venue_impl(TARGET)
    page = browser.new_page()
    page.set_content((FIXTURES / "upload-manuscript.html").read_text())
    letter = tmp_path / "letter.pdf"
    letter.write_bytes(b"old content")
    impl.fill_page(page, {"cover_letter": str(letter)})
    letter.write_bytes(b"replacement content")
    impl.fill_page(page, {"cover_letter": str(letter)})
    assert page.get_by_label("Cover Letter", exact=True).evaluate("el => el.files[0].size") == len(b"replacement content")
    assert page.evaluate("window.clicks") == []
    page.close()


@pytest.mark.parametrize("options,value,filled", [("<option>Review</option><option>Review Article</option>", "Review", True), ("<option disabled>Review</option>", "Review", False), ("<option>Review</option>", "Unknown", False), ("<option>Review</option><option>Review</option>", "Review", False)])
def test_article_type_requires_one_exact_enabled_option(browser, options, value, filled):
    page = browser.new_page()
    page.set_content(f'<label for="type">Article Type</label><select id="type">{options}</select>')
    result, manual = get_venue_impl(TARGET).fill_page(page, {"portal_article_type": value})
    assert ("portal_article_type" in result) == filled
    page.close()


def test_generic_mcp_exposes_rules_and_refuses_detached_browser(tmp_path, monkeypatch):
    from paperpush import mcp_server

    result = mcp_server.describe_venue(TARGET)
    assert result["platform"] == "rex"
    assert any("generic" in x.lower() for x in result["unverified"])
    sub = tmp_path / "paper.sub"
    sub.write_text(render_template(get_venue(TARGET)))
    monkeypatch.setattr(mcp_server.subprocess, "Popen", lambda *a, **kw: pytest.fail("must not detach attended ReX"))
    assert mcp_server.submit(str(sub))["status"] == "action_required"


@pytest.mark.parametrize("label,accept,filled", [("Main Document - MS Word", ".doc,.docx", False), ("Main Manuscript", "", False), ("Main Manuscript", "application/pdf", True), ("Manuscript PDF", "", True)])
def test_pdf_is_not_sent_to_word_only_main_slot(browser, tmp_path, label, accept, filled):
    page = browser.new_page()
    page.set_content(f'<label>{label}<input type="file" accept="{accept}"></label>')
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"fixture")
    result, manual = get_venue_impl(TARGET).fill_page(page, {"manuscript_file": str(pdf)})
    assert ("manuscript_file" in result) == filled
    assert page.locator('input[type="file"]').evaluate("el => el.files.length") == int(filled)
    page.close()
