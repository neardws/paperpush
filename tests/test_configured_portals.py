"""Synthetic HTML contract tests; no network, accounts, or live-portal claims."""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from paperpush.database import Field, Venue
from paperpush.venues import configured as c

FIXTURES = Path(__file__).parent / "fixtures" / "platforms"


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        if not Path(pw.chromium.executable_path).exists():
            pytest.skip("Install Chromium with python -m playwright install chromium for offline HTML tests")
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        yield browser
        browser.close()


@pytest.fixture
def deployment(monkeypatch):
    def install(platform, **kwargs):
        venue = Venue(slug="fixture", platform=platform, submission_url="https://example.invalid/2026", fields=[Field("title", "Title", "text", autofill="extract"), Field("abstract", "Abstract", "textarea", autofill="extract"), Field("authors", "Authors", "authorlist"), Field("manuscript_file", "Manuscript", "file", autofill="filemap"), Field("consent", "Consent", "boolean", autofill="never")], **kwargs)
        monkeypatch.setattr(c, "get_venue", lambda slug: venue)
        return c.ConfiguredVenue("fixture")

    return install


@pytest.mark.parametrize("platform", c.PLATFORMS)
def test_fills_inputs_and_uploads_without_final_action(browser, deployment, platform, tmp_path):
    impl = deployment(platform)
    page = browser.new_page()
    page.route("**/*", lambda route: route.abort())
    page.set_content((FIXTURES / f"{platform}.html").read_text())
    paper = tmp_path / "paper.pdf"
    paper.write_bytes(b"fixture")
    values = {"title": "Edge intelligence", "abstract": "An agentic mobile system.", "authors": "Ada | ada@example.org", "manuscript_file": str(paper), "consent": "yes"}
    filled, manual = impl.fill_page(page, values)
    assert filled == ["title", "abstract", "manuscript_file"]
    assert manual == ["authors", "consent"]
    assert page.locator(impl.platform.fields["title"]).input_value() == values["title"]
    assert page.locator('input[type="file"]').evaluate("el => el.files[0].name") == "paper.pdf"
    assert not page.locator('[name="consent"]').is_checked()
    assert not page.evaluate("window.submitted")
    assert page.evaluate("window.clicks") == 0
    page.close()


def test_ambiguous_hidden_disabled_and_action_bindings_are_manual(browser, deployment):
    for html in ['<input name="title"><input name="title">', '<input name="title" type="hidden">', '<input name="title" disabled>', '<button name="title" type="submit">Submit</button>']:
        impl = deployment("hotcrp", portal_fields={"title": '[name="title"]'})
        page = browser.new_page()
        page.set_content(html)
        assert impl.fill_page(page, {"title": "Test"}) == ([], ["title"])
        page.close()


def test_unknown_url_fails_before_browser(monkeypatch):
    monkeypatch.setattr(c, "get_venue", lambda slug: Venue(slug=slug, platform="edas"))
    with pytest.raises(ValueError, match="portal URL is unverified"):
        c.ConfiguredVenue("unknown").submit({})


def test_attended_driver_refuses_headless(deployment):
    with pytest.raises(ValueError, match="attended"):
        deployment("hotcrp").submit({}, headless=True)


def test_missing_portal_stops_cli_before_login(tmp_path, monkeypatch, capsys):
    from paperpush.cli import main
    from paperpush import credentials

    sub = tmp_path / "acm_tosn.sub"
    sub.write_text("@venue: acm_tosn\n")
    monkeypatch.setattr(credentials, "get_credential", lambda *a: pytest.fail("must stop before credential lookup"))
    assert main(["submit", str(sub)]) == 1
    assert "portal URL is unverified" in capsys.readouterr().err


def test_mcp_does_not_launch_a_driver_that_needs_terminal(tmp_path, monkeypatch):
    from paperpush import mcp_server
    from paperpush.database import get_venue
    from paperpush.subfile import render_template

    for slug, status in [("acm_tosn", "blocked"), ("mobicom_2026_winter", "action_required")]:
        path = tmp_path / (slug + ".sub")
        path.write_text(render_template(get_venue(slug)))
        monkeypatch.setattr(mcp_server.subprocess, "Popen", lambda *a, **k: pytest.fail("must not detach an attended driver"))
        result = mcp_server.submit(str(path))
        assert result["status"] == status
