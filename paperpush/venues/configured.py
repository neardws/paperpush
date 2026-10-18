"""Conservative, reusable form filling for configurable portal deployments.

Bindings are fixture-tested hypotheses, not recordings of authenticated portals.
The author opens the form and navigates wizard pages; this engine only writes to
visible inputs. It NEVER clicks, presses Enter, saves, registers, or submits a
manuscript. This matters especially on conference portals where even creating a
new draft can be called 'Submit'. Unknown and policy widgets remain manual.

Attempted public platform references (fetch outcomes in docs/venue-source-audit.json;
not claims about a particular venue's configuration):
https://help.hotcrp.com/help/authors
https://edas.info/doc/authors.html
https://cmt3.research.microsoft.com/docs/help/author/author-submission-form.html
https://docs.openreview.net/getting-started/using-the-openreview.net-interface/submitting-a-paper
https://easychair.org/help/faq
https://clarivate.com/academia-government/scientific-and-academic-research/research-publishing-solutions/scholarone/
"""

from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import sync_playwright

from ..autofill import effective_role
from ..database import get_venue
from .base import Venue
from .common import DEFAULT_TIMEOUT_SECONDS, apply_default_timeouts, hold_open_on_failure, open_run_context, wait_for_human
from .login import VenueLoginError, fill_login_form


@dataclass(frozen=True)
class Platform:
    """Input selectors, with explicit deployment overrides in venues.json."""

    fields: dict[str, str]
    username: str
    password: str
    login_button: str
    signed_in: str


# Deliberately narrow selectors: no generic input[type=file] fallback, no
# first-match disambiguation, and no action selectors in venue data.
PLATFORMS = {
    "rex": Platform({"title": 'input[name="title"]', "abstract": 'textarea[name="abstract"]', "manuscript_file": 'input[type="file"][name="manuscript"]'}, 'input[type="email"]', 'input[type="password"]', 'button[type="submit"]', 'a[href*="logout"]'),
    "scholarone": Platform({"title": '#MANUSCRIPT_TITLE, textarea[name="MANUSCRIPT_TITLE"]', "abstract": '#ABSTRACT, textarea[name="ABSTRACT"]', "manuscript_file": 'input[type="file"][name="FILE_TO_UPLOAD"]'}, "#USERID", "#PASSWORD", "#logInButton", 'a:has-text("Log Out"), a:has-text("Logout")'),
    "hotcrp": Platform({"title": 'input[name="title"]', "abstract": 'textarea[name="abstract"]', "manuscript_file": 'input[type="file"][name="paperUpload"]'}, 'input[name="email"]', 'input[name="password"]', 'button[name="signin"]', 'a[href*="signout"]'),
    "edas": Platform({"title": 'input[name="title"]', "abstract": 'textarea[name="abstract"]', "keywords": 'input[name="keywords"]', "manuscript_file": 'input[type="file"][name="upload"]'}, 'input[name="username"]', 'input[name="password"]', 'input[type="submit"][value="Login"]', 'a[href*="logout"]'),
    "cmt": Platform({"title": 'input[name="Title"]', "abstract": 'textarea[name="Abstract"]', "manuscript_file": 'input[type="file"][name="file"]'}, "#Email", "#Password", 'button[type="submit"]', 'a[href*="Logout"]'),
    "openreview": Platform({"title": 'input[name="title"], textarea[name="title"]', "abstract": 'textarea[name="abstract"]', "keywords": 'input[name="keywords"]', "manuscript_file": 'input[type="file"][name="pdf"]'}, "#email-input", "#password-input", 'button[type="submit"]', 'a[href*="logout"]'),
    "easychair": Platform({"title": 'input[name="title"]', "abstract": 'textarea[name="abstract"]', "keywords": 'textarea[name="keywords"]', "manuscript_file": 'input[type="file"][name="paper"]'}, 'input[name="name"]', 'input[name="password"]', 'input[name="LogIn"]', 'a[href*="signout"], a[href*="logout"]'),
}


class ConfiguredVenue(Venue):
    """Shared attended runner. A new deployment needs only a slug binding."""

    requires_terminal = True

    def __init__(self, slug: str):
        self.slug = slug

    @property
    def platform(self) -> Platform:
        return PLATFORMS[get_venue(self.slug).platform]

    @property
    def portal_url(self) -> str:
        url = get_venue(self.slug).submission_url
        if not url:
            raise ValueError(f"{self.slug}: portal URL is unverified; add a sourced edition URL before opening a browser")
        return url

    def is_logged_in(self, page, *, timeout_ms=None) -> bool:
        marker = page.locator(self.platform.signed_in)
        return marker.count() == 1 and marker.is_visible()

    def login(self, page, username: str, password: str, *, timeout_ms: int = 15000) -> None:
        page.goto(self.login_url)
        platform = self.platform
        fill_login_form(page, username, password, userid_sel=platform.username, password_sel=platform.password, submit_sel=platform.login_button, timeout_ms=timeout_ms)
        try:
            page.locator(platform.signed_in).wait_for(state="visible", timeout=timeout_ms)
        except Exception as exc:
            raise VenueLoginError(f"{self.slug}: could not confirm sign-in; complete SSO/CAPTCHA manually") from exc

    def fill_page(self, page, values: dict) -> tuple[list[str], list[str]]:
        """Fill unambiguous visible inputs; return (filled, manual field ids).

        Author profile search/repeated author rows, consent, payment, licensing,
        reviewers, and custom declarations are intentionally left to the author.
        No guessed column mapping or account creation is performed.
        """
        venue = get_venue(self.slug)
        bindings = {**self.platform.fields, **venue.portal_fields}
        filled, manual = [], []
        for field in venue.fields:
            value = values.get(field.id, "")
            if not value:
                continue
            if effective_role(field) == "never" or field.type not in {"text", "textarea", "file", "filelist", "choice", "multichoice"}:
                manual.append(field.id)
                continue
            selector = bindings.get(field.id)
            if not selector:
                manual.append(field.id)
                continue
            widget = page.locator(selector)
            if widget.count() != 1 or not widget.is_visible() or not widget.is_enabled():
                manual.append(field.id)
                continue
            tag, kind = widget.evaluate("el => [el.tagName.toLowerCase(), (el.type || '').toLowerCase()]")
            # A misconfigured selector must never turn into a click or a write
            # to a hidden field, consent checkbox, or submit control.
            if field.type in {"file", "filelist"} and tag == "input" and kind == "file":
                paths = [line.split("|", 1)[0].strip() for line in str(value).splitlines() if line.strip()]
                if len(paths) > 1 and widget.get_attribute("multiple") is None:
                    manual.append(field.id)
                    continue
                widget.set_input_files(paths)
            elif field.type in {"choice", "multichoice"} and tag == "select":
                widget.select_option(label=str(value).strip())
            elif field.type in {"text", "textarea"} and (tag == "textarea" or (tag == "input" and kind in {"text", "email", "url", "search"})):
                widget.fill(str(value))
            else:
                manual.append(field.id)
                continue
            filled.append(field.id)
        return filled, manual

    def submit(self, values: dict, *, headless: bool = False, debug: bool = False, new_session: bool = False, timeout: float = DEFAULT_TIMEOUT_SECONDS, keep_open_on_failure: bool = True) -> None:
        url = self.portal_url  # fail before launching for an unknown edition URL
        if headless:
            raise ValueError("Configured portal drivers require an attended browser to navigate wizard pages")
        with sync_playwright() as playwright, hold_open_on_failure(headless=headless, keep_open=keep_open_on_failure):
            browser = playwright.chromium.launch(headless=False)
            context = open_run_context(browser, self.session_path(), new_session=new_session)
            apply_default_timeouts(context, timeout)
            page = context.new_page()
            self.ensure_signed_in(page, context, debug=debug)
            if debug:
                page.pause()
            print(f"{self.slug}: fixture-tested driver; review the {url} edition and open its submission form.")
            wait_for_human("Open the form in this browser. PaperPush will fill visible inputs only")
            while True:
                filled, manual = self.fill_page(page, values)
                print(f"Filled: {', '.join(filled) or '(none)'}. Manual/on another page: {', '.join(manual) or '(none)'}. Review all portal declarations yourself.")
                if hasattr(self, "page_instructions"):
                    print(self.page_instructions(page))
                try:
                    command = input("Navigate to another wizard page and type 'fill' to fill it; Enter finishes and closes the browser. Only you can submit: ")
                except (EOFError, KeyboardInterrupt, OSError):
                    break
                if command.strip().lower() != "fill":
                    break
            browser.close()
