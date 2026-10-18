# IEEE, ACM, and conference editions

The configurable portal drivers are **experimental, tested against synthetic HTML
fixtures only**. None was tested with an authenticated live portal. These are
attended CLI drivers: the author opens the new-paper form and navigates the
wizard; PaperPush fills unambiguous, visible inputs on each page. Type `fill` in
the terminal after navigating to another page. The browser stays open at that
prompt for review; Enter finishes and closes it. Detached MCP submission does
not provide this terminal interaction, so use the CLI for these drivers.

The preparation/validation entries include all requested starter journals, but
some are explicitly incomplete. A venue with no verified portal URL refuses to
launch a browser. A successful validation does not imply that its unverified
rules or its custom portal fields have been checked. `paperpush schema VENUE`,
MCP `describe_venue`, and validation warnings expose the unverified facts.

| Entries | Platform | Data coverage |
| --- | --- | --- |
| `ieee_jsac` | ScholarOne | Verified public policy; special-issue limits remain manual |
| `ieee_twc`, `ieee_tnse`, `ieee_iot` | IEEE Author Portal / ReX | Verified public policy and portal links |
| `ieee_tvt` | IEEE Author Portal / ReX | Verified public policy; direct portal URL unverified |
| `ieee_tmc`, `ieee_tpds`, `ieee_tits` | Provisional ScholarOne | Preparation fields only; guidelines/portal unverified |
| `acm_tosn`, `acm_csur`, `acm_tist` | Provisional ScholarOne | Preparation fields only; guideline fetch blocked; portal unverified |
| `infocom_2026` | Provisional EDAS | Preparation fields only; CFP fetch blocked; portal/rules unverified |
| `mobicom_2026_summer`, `mobicom_2026_winter` | HotCRP | Verified 2026 CFP and cycle deadlines |
| `mobisys_2026` | HotCRP | Verified 2026 CFP; **single-blind**, requires author identity |
| `sensys_2026_nov` | HotCRP | Verified second-cycle CFP, new submissions only |
| `neurips_2025` | OpenReview | Verified **historical 2025** main track; 2026 rules unavailable |
| `iclr_2027`, `aaai_2027` | OpenReview | Existing recorded drivers restored to listings, explicit editions; AAAI manuscript rules added |

Some IEEE society pages still describe ScholarOne account settings but now link
new submissions to ReX. The driver uses the published submission link, rather
than assuming all IEEE titles still use ScholarOne. No IEEE or ACM journal-wide
page cap is inferred from a paid-overlength threshold.

## Reusable drivers

`paperpush/venues/configured.py` contains input bindings for ScholarOne,
HotCRP, EDAS, Microsoft CMT, OpenReview, EasyChair, and ReX. CMT and EasyChair
currently have reusable fixture-tested profiles but no verified starter-venue
binding. ScholarOne and OpenReview deployments reuse the existing login helpers;
previous journal recordings and the ICLR/AAAI recordings are unchanged.

Add an entry with `platform`, `submission_url`, `source_urls`, and fields to
`venues.json`, a sourced entry to `manuscript_requirements.json`, and the normal
thin module under `paperpush/venues/<platform>/<slug>.py`:

```python
from ..configured import ConfiguredVenue

VENUE = ConfiguredVenue("example_2027_main")
```

For ScholarOne and OpenReview import `ConfiguredScholarOneVenue` or
`ConfiguredOpenReviewVenue` from `.configured` instead. Per-deployment CSS
bindings can be supplied in `portal_fields` (field id to selector), for example
`{"title": "#paper-title"}`. These are **input bindings**, never navigation or
action commands. They are hypotheses until verified against that deployment.
The filler requires exactly one visible, enabled widget of the expected input
type. Missing, ambiguous, unsupported, and policy fields are reported as manual.

Authors and profile search, conflicts, consent, copyright, licenses, payments,
custom declarations, and wizard navigation remain manual. The engine does not
click, press Enter, register a paper, save a manuscript, or submit. Its login
method is the separate operation allowed to click a login control. Synthetic
fixtures assert that filling triggers no clicks and leaves the final control
untouched. Never add generic “Next”, “Save”, “Register”, or “Submit” clicks: on
some platforms those actions finalize a submission.

## Updating a conference edition

There is no implicit “latest” alias. Select the explicit slug. Year, cycle,
deadlines (including the source's timezone), portal URL, reviewing policy, and
requirements belong to that entry. Deadlines are informational, not an automatic
permission to submit or a gate that prevents working on historical papers.

1. Fetch the new official CFP and submission instructions. Keep the exact URLs,
   retrieval date, and evidence. HTTP 200 alone is insufficient: several sites
   return empty shells, error pages, or browser-compatibility notices.
2. Create a new slug such as `mobicom_2027_winter`, set `edition.year` and
   `edition.cycle`, and record only verified deadlines and portal URLs. Use a
   blank `submission_url` and an `unverified` explanation when unavailable.
   Do not reuse the previous year's portal or numeric rules by default.
3. Add only fields actually supported by public instructions. Optional
   preparation selectors (for example submission stage) must say that they are
   not verified portal dropdowns. Unknown portal fields stay manual.
4. Add independently sourced manuscript rules. Use `max_pages` for a cap that
   includes references and appendices; `max_pages_before_refs` for content-only
   limits. `main_text_end_headings` records *explicit* additional exclusions.
   `count_includes` and `count_excludes` document scope; they do not themselves
   change counting. New or revised paper limits use `article_types`.
5. Set `anonymous` from the edition policy, not from its platform. The automatic
   anonymity pass already covers author strings, emails, affiliations, metadata,
   acknowledgments, camera-ready switches, and linked anonymous repositories.
   Do not anonymize MobiSys 2026: its policy explicitly changed.
6. Add a thin binding and sample entry, run the generators below, and test.
   Retain historical entries for reproducibility; deprecate them only when
   deliberately hiding them from listings.

SenSys 2026 second-cycle resubmissions can include a four-page response appendix;
the `november-new` configuration intentionally covers new submissions, where
appendices are forbidden. It is not a resubmission checker. NeurIPS 2025 checklist
presence is checked by heading; checklist answers and completeness require author
review. AAAI's separate reproducibility checklist is required at full-paper
submission; the pre-existing form leaves that upload optional during abstract
registration.

## Checks and sources

Template source checks recognize a required LaTeX class/style and required
options (`latex_class`, `latex_options`), ignoring commented-out declarations and
checking `.tex` files inside uploaded source archives. They recognize IEEEtran
and acmart; source inspection is heuristic and cannot prove that a PDF follows a
template. Word/PDF-only files cannot establish a LaTeX class. Recommended acmart
formatting is not turned into a mandatory class requirement. Compiled geometry
is checked only when a measured official `template_layout` is recorded; no IEEE
or ACM dimensions were invented or inferred from font appearance.

`allow_appendix: false` warns on detected appendix headings. Statement
`required_if` maps a statement id to a preparation boolean, checked only for an
explicit `yes`; unknown applicability must be reviewed by the author. Existing
figure dimensions/resolution and reference checks are reused where sourced.
TVT's artwork dimensions come from its legacy original-artwork instructions;
no universal IEEE/ACM DPI or reference-count cap was assumed.

Every new rule's venue entry lists its exact public source URL and retrieval
date. Field help carries its source and identifies unverified preparation fields.
[venue-source-audit.json](venue-source-audit.json) records successful and failed
fetches, including browser retries. It is a fetch audit, not a source of rules;
200 responses containing no guidelines were not used. Blocked ACM pages did not
produce guessed acmart requirements, page limits, or figure rules.

```bash
.venv/bin/python scripts/gen_venues_schema.py
.venv/bin/python scripts/gen_schema_docs.py
.venv/bin/python scripts/gen_readme_venues.py
.venv/bin/python scripts/gen_subfile_templates.py
.venv/bin/python tests/sample_subfiles.py
.venv/bin/pytest
```

Browser fixture tests need `python -m playwright install chromium`; they never
use a real submission site or stored credential. Real portal walkthroughs remain
opt-in and were not run for this change.
