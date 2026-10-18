"""Attended IEEE Author Portal filler, based on public help, not live DOM.

https://rex-docs.atypon.com/ieee-rex/author_portal/
The documented selection/confirmation workflow needs a human. This runner only
fills uniquely labelled editable inputs already exposed by the author. It has
no manuscript click, keyboard navigation, or confirmation operations.
"""

from pathlib import Path

from ...autofill import effective_role
from ...database import get_venue
from ..configured import ConfiguredVenue

LABELS = {
    "portal_article_type": ("Article Type",),
    "title": ("Title", "Manuscript Title"),
    "abstract": ("Abstract",),
    "keywords": ("Keywords", "Index Terms"),
    "manuscript_file": ("Main Document - MS Word", "Main Manuscript", "Manuscript PDF"),
    "latex_source_file": ("Main Document - LaTeX",),
    "latex_pdf_file": ("Main Document - LaTeX PDF",),
    "cover_letter": ("Cover Letter",),
    "figure_files": ("Figures",),
    "supplementary_files": ("Supplementary Files",),
    "competing_interests_file": ("Conflict of Interest Statement",),
    "author_response_file": ("Author Response",),
    "title_page_file": ("Title Page",),
}

STEP_HELP = {
    "Article Type": "Review the article type and all submission requirements yourself, then click Confirm.",
    "Upload Manuscript": "Open Add Files and select the manuscript type yourself. For LaTeX expose both Main Document - LaTeX and Main Document - LaTeX PDF uploads, then type fill. Select Main File for an archive and Confirm yourself. Review COI, revision response and any required title page.",
    "Title": "Review the extracted title, or use No, let me select it / Something is wrong with my title. Confirm title yourself.",
    "Abstract": "Review the extracted abstract, or use No, let me select it / Something is wrong with my abstract. Confirm abstract yourself.",
    "Authors": "Review every extracted name; use No, let me fix them if needed. Confirm author(s) yourself.",
    "Affiliations": "Review every affiliation including institution and country; confirm affiliations yourself.",
    "Author Details": "Review each author's email, country/location, affiliations and ORCID connection; choose exactly one corresponding author and Confirm yourself.",
    "Match Organizations": "Review Ringgold matches or search Find Organization for each affiliation; select matches and Confirm yourself.",
    "Additional Information": "Answer the journal's questions and declarations yourself; review and click Confirm yourself.",
    "Final Review": "Review all sections yourself. Only you may click Build Reviewer PDF, Complete my submission, or Complete my revision.",
}


class RexVenue(ConfiguredVenue):
    """Current-step filling with author-controlled wizard navigation."""

    @property
    def portal_url(self):
        if self.slug == "ieee":
            raise ValueError("Choose an IEEE journal with ieee:<journal-code>, for example ieee:t-its")
        return super().portal_url

    def current_step(self, page):
        # Final Review also has section headings named Title, Abstract, etc.
        for step in ("Final Review", *[s for s in STEP_HELP if s != "Final Review"]):
            headings = page.get_by_role("heading", name=step, exact=True)
            if any(h.is_visible() for h in headings.all()):
                return step
        return ""

    def page_instructions(self, page):
        step = self.current_step(page)
        return f"ReX {step}: {STEP_HELP[step]}" if step else "ReX: open the desired wizard step yourself; selection and confirmation controls remain manual."

    def _widget(self, page, field, venue):
        if field.id in venue.portal_fields:
            return page.locator(venue.portal_fields[field.id])
        labels = LABELS.get(field.id, ())
        widget = None
        for label in labels:
            candidate = page.get_by_label(label, exact=True)
            widget = candidate if widget is None else widget.or_(candidate)
        # Retain original fixture bindings, without a generic file fallback.
        selector = self.platform.fields.get(field.id)
        if selector:
            candidate = page.locator(selector)
            widget = candidate if widget is None else widget.or_(candidate)
        return widget

    def fill_page(self, page, values):
        venue = get_venue(self.slug)
        filled, manual = [], []
        # Never edit a review summary, even if it contains editable controls.
        final = self.current_step(page) == "Final Review"
        pair_ready = False
        if not final and values.get("latex_source_file") and values.get("latex_pdf_file"):
            fields = {f.id: f for f in venue.fields}
            widgets = [self._widget(page, fields[fid], venue) for fid in ("latex_source_file", "latex_pdf_file")]
            pair_ready = all(w is not None and w.count() == 1 and w.is_visible() and w.is_enabled() and w.evaluate("el => el.tagName === 'INPUT' && el.type === 'file'") for w in widgets)
            if pair_ready:
                pair_ready = widgets[0].or_(widgets[1]).count() == 2
        for field in venue.fields:
            value = str(values.get(field.id, "")).strip()
            if not value:
                continue
            if final or effective_role(field) == "never" or field.id not in LABELS:
                manual.append(field.id)
                continue
            # Do not send half a LaTeX pair, or upload the preparation PDF as
            # another main document alongside the LaTeX pair.
            if (field.id in {"latex_source_file", "latex_pdf_file"} and not pair_ready) or (field.id == "manuscript_file" and values.get("latex_source_file")):
                manual.append(field.id)
                continue
            widget = self._widget(page, field, venue)
            if widget is None or widget.count() != 1 or not widget.is_visible() or not widget.is_enabled():
                manual.append(field.id)
                continue
            tag, kind, editable = widget.evaluate("el => [el.tagName.toLowerCase(), (el.type || '').toLowerCase(), el.isContentEditable]")
            if field.type in {"file", "filelist"} and tag == "input" and kind == "file":
                paths = [line.split("|", 1)[0].strip() for line in value.splitlines() if line.strip()]
                if field.id == "manuscript_file" and Path(paths[0]).suffix.lower() not in {".pdf", ".doc", ".docx"}:
                    manual.append(field.id)
                    continue
                if field.id == "manuscript_file" and Path(paths[0]).suffix.lower() == ".pdf":
                    # Public help documents Word or a LaTeX/PDF pair. Never
                    # put the preparation PDF into a Word-only main slot.
                    accepts = (widget.get_attribute("accept") or "").lower().split(",")
                    pdf_slot = page.get_by_label("Manuscript PDF", exact=True)
                    explicit_pdf = pdf_slot.count() == 1 and widget.or_(pdf_slot).count() == 1
                    if not explicit_pdf and not {".pdf", "application/pdf"}.intersection(a.strip() for a in accepts):
                        manual.append(field.id)
                        continue
                if len(paths) != 1 and widget.get_attribute("multiple") is None:
                    manual.append(field.id)
                    continue
                # Repeated 'fill' must not send the same upload again.
                selected = widget.evaluate("el => Array.from(el.files, f => [f.name, f.size, f.lastModified])")
                expected = [[Path(p).name, Path(p).stat().st_size, Path(p).stat().st_mtime_ns // 1_000_000] for p in paths]
                if selected != expected:
                    widget.set_input_files(paths)
            elif field.id == "portal_article_type" and tag == "select":
                options = widget.locator("option").evaluate_all("(els, label) => els.filter(el => el.label.trim() === label && !el.disabled && !el.parentElement.disabled).map(el => el.value)", value)
                if len(options) != 1:
                    manual.append(field.id)
                    continue
                widget.select_option(value=options[0])
            elif field.type in {"text", "textarea"} and (tag == "textarea" or (tag == "input" and kind in {"text", "email", "url", "search"}) or (editable and widget.get_attribute("role") == "textbox")):
                if widget.is_editable():
                    widget.fill(value)
                else:
                    manual.append(field.id)
                    continue
            else:
                manual.append(field.id)
                continue
            filled.append(field.id)
        return filled, manual
