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
| `ieee_twc`, `ieee_tnse`, `ieee_iot`, `ieee_tits` | IEEE Author Portal / ReX | Verified public policy and portal links; T-ITS source provided by Neil (page timestamp 2026-07-15) |
| `ieee_tvt`, `ieee_jsac` | IEEE Author Portal / ReX | Verified public policy; journal code / portal URL unverified (left blank); JSAC special-issue limits remain manual |
| `ieee_tmc`, `ieee_tpds` | IEEE Author Portal / ReX | Preparation fields only; guidelines and journal code / portal URL unverified (left blank) |
| `acm_tosn`, `acm_csur`, `acm_tist` | Provisional ScholarOne | Preparation fields only; guideline fetch blocked; portal unverified |
| `infocom_2026` | Provisional EDAS | Preparation fields only; CFP fetch blocked; portal/rules unverified |
| `mobicom_2026_summer`, `mobicom_2026_winter` | HotCRP | Verified 2026 CFP and cycle deadlines |
| `mobisys_2026` | HotCRP | Verified 2026 CFP; **single-blind**, requires author identity |
| `sensys_2026_nov` | HotCRP | Verified second-cycle CFP, new submissions only |
| `neurips_2025` | OpenReview | Verified **historical 2025** main track; 2026 rules unavailable |
| `iclr_2027`, `aaai_2027` | OpenReview | Existing recorded drivers restored to listings, explicit editions; AAAI manuscript rules added |

All IEEE journals now use IEEE Author Portal (ReX); ScholarOne is no longer
assumed for any IEEE journal (confirmed by the maintainer, 2026-10-18), even where
a society page still links ScholarOne (e.g. JSAC). A portal URL is set only when
the journal code is verified from a public link; otherwise it is left blank so
the filler cannot open a wrong page, and preparation/validation still work. Once
you have a journal's code from Author Portal, use `ieee:<code>` (generic IEEE
checks) or set that entry's `submission_url` to
`https://ieee.atyponrex.com/journal/<code>` to combine it with the journal's
sourced rules. ACM journals are unchanged. No IEEE or ACM journal-wide
page cap is inferred from a paid-overlength threshold.

## Any IEEE Author Portal journal

Use `ieee:<journal-code>` with the code from the journal's **own** submission
link, `https://ieee.atyponrex.com/journal/<journal-code>`. No new configuration
or Python module is needed. Codes accept ASCII letters/digits and single internal
hyphens (up to 64 characters); case is normalized. Syntax validation does not
prove a code exists or that a journal uses ReX. Journals on other systems still
need their own driver.

For example, T-ITS has code `t-its`. The same commands work for an arbitrary
journal after replacing `t-its` with its verified Author Portal code:

```bash
paperpush schema ieee:t-its
paperpush requirements ieee:t-its
paperpush subfile ieee:t-its -o /absolute/path/paper.sub
# Read the manuscript and write values.json yourself, using schema field roles.
paperpush autofill /absolute/path/paper.sub -d /absolute/path/manuscript-dir \
  --engine manual --values /absolute/path/values.json
paperpush validate /absolute/path/paper.sub
paperpush login ieee:t-its --status
paperpush login ieee:t-its  # author completes browser sign-in
paperpush submit /absolute/path/paper.sub
```

`ieee` is the shared preparation/schema base; to open a browser select a code.
Existing journal slugs still work. A code matching a configured journal reuses
its sourced journal rules (for example `ieee:twc` retains TWC's page and abstract
limits). An unknown code uses **only generic IEEE checks**, and requirements,
schema and validation explicitly tell the author to check the journal's own
Information for Authors manually. No page cap, abstract cap, keyword count,
review policy, or figure geometry is invented. Check anonymity yourself; run
`paperpush validate --anonymous /absolute/path/paper.sub` for a double-anonymized
submission. Arbitrary codes do not automatically share credentials with another
journal slug: log in using the same target used in the `.sub`.

The base records public IEEE style guidance: advisory IEEEtran source detection
(including archives), numbered square-bracket body citations, abstract guidance
of 150–250 words and no citations, and Index Terms guidance. These are warnings
or notes. Journal-specific abstract limits take precedence over the advisory
range. A missing LaTeX main source reports template detection as unchecked;
PDF/Word appearance cannot prove template compliance. Style checking is heuristic
and does not validate every reference or citation. No IEEE PDF geometry was
inferred. The Editorial Style Manual's reference examples provide the citation
evidence; the requested Reference Guide URL redirected to Google Docs and was
not treated as a PDF source.

Shared ReX fields include title, abstract, authors (email, affiliation, optional
known ORCID, exactly one corresponding author), Index Terms, manuscript PDF/Word,
LaTeX source and compiled PDF, optional cover letter, figures/supplements,
conflict statement, revision response and a conditional title page. Optional
files are preparation slots, not claims that every journal asks for them.
The public upload help documents Word or LaTeX main documents; standalone PDF
acceptance is journal-specific. The filler only sends a standalone PDF to a
slot explicitly labelled for PDF or accepting PDF; it leaves Word-only slots
manual for a PDF preparation copy. For LaTeX, set `latex_source_file` (`.tex`, `.zip`,
`.tar.gz`) and `latex_pdf_file` (compiled `.pdf`); set `manuscript_file` to the
same PDF for manuscript checks. Both members of the pair are required if either
is given. The author selects **Main Document - LaTeX** and exposes both upload
inputs before typing `fill`. The driver requires two distinct, unambiguous
visible file inputs before filling either member. For an archive, **Select Main
File** and **Confirm** remain manual. File type, ordering, figure labels and
conditional journal requirements must be reviewed in the portal.

The ten documented steps are Article Type, Upload Manuscript, Title, Abstract,
Authors, Affiliations, Author Details, Match Organizations, Additional
Information and Final Review. The driver prints step-specific instructions.
Where labelled editable correction fields exist, it fills them; otherwise it
reports them as manual. The documented manuscript highlighting/selection UI,
author metadata, country/location, ORCID linking, Ringgold matches, all
attestations and additional questions remain attended. `portal_article_type`
is an exact portal option supplied by the author, distinct from a configured
`article_type` preparation stage such as Initial/Revision. The driver never
clicks **Confirm**, **Save**, **Continue**, **Submit**, **Build Reviewer PDF**,
**Complete my submission**, or **Complete my revision**. Final Review is read
only to the filler. Repeating `fill` does not resend an already selected upload.

**Nothing was tested against the live IEEE portal.** Fixtures model public help
text and hypothetical labelled correction fields; they are not captured portal
DOM or evidence of end-to-end compatibility. Unknown widgets remain manual.
Use the attended CLI, not detached MCP submission.

Verified portal-code mappings (no guessed TVT/TMC/TPDS codes):

| Slug | Code | Public source |
| --- | --- | --- |
| `ieee_twc` | `twc` | https://www.comsoc.org/publications/journals/ieee-twc/policies-guidelines |
| `ieee_tnse` | `tnse-cs` | https://www.comsoc.org/publications/journals/ieee-tnse/policies-guidelines |
| `ieee_iot` | `iot` | https://ieee-iotj.org/guidelines-for-authors/ |
| `ieee_tits` | `t-its` | https://ieee-itss.org/pub/t-its/ (verified source provided by Neil; page timestamp 2026-07-15) |

Public workflow sources: [start submission](https://rex-docs.atypon.com/ieee-rex/author_portal/t_auth_start-new-submission.html),
[upload files](https://rex-docs.atypon.com/ieee-rex/author_portal/t_auth_upload-manuscript.html),
[LaTeX pair](https://rex-docs.atypon.com/ieee-rex/author_portal/t_auth_upload-latex.html),
[author details](https://rex-docs.atypon.com/ieee-rex/author_portal/t_auth_author-details.html),
[final review](https://rex-docs.atypon.com/ieee-rex/author_portal/t_auth_final-review.html).
The other step URLs are recorded in fixture comments and the fetch audit.
Style sources: [IEEE Editorial Style Manual](https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/IEEE-Editorial-Style-Manual-for-Authors.pdf),
[IEEE templates](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/authoring-tools-and-templates/tools-for-ieee-authors/ieee-article-templates/)
(the supplied pre-fetched Author Center excerpt), and
[IEEEtran distribution](https://ctan.org/pkg/ieeetran).

## Verified T-ITS profile

`ieee_tits` and `ieee:t-its` both use the verified rules from
https://ieee-itss.org/pub/t-its/ (page timestamp **2026-07-15**, provided by Neil,
preserved in commit `7fe8d5f`). The earlier curl failures do not make these
user-provided journal rules unverified. The ReX form driver is still tested
against fixtures only.

| Article type | Suggested pages | Main-text cap |
| --- | --- | --- |
| Regular | 10 | 16 |
| Short | 6 | 12 |
| Practitioner | 6 | 12 |
| Survey | 18 | 24 |

Up to six pages beyond the suggested length are allowed, with **$175 per extra
page after acceptance**. The suggested lengths and charges are notes for the
author; caps are enforced using `max_pages_before_refs`. The source does not
state whether references count, so confirm whether the entire document must
also fit. The verified web page takes precedence over its linked 2010 PDF where
they conflict.

T-ITS requires the IEEEtran double-column, single-spaced template and uses
**single-anonymous** review: author identity remains present. Its abstract must
have **150–250 words**, with both bounds enforced as errors. No references or
abbreviations are allowed; use one paragraph with no displayed equations,
tables or footnotes. These content/structure requirements are recorded in the
schema and notes for author review; automated citation detection remains a
heuristic warning, and abbreviation/paragraph completeness is not certified.

Use the three journal-specific keyword fields: optional `free_keywords` (0–2),
required `methodology_keywords` (1–2), and required `application_keywords` (1–2).
Each is a comma-separated multichoice field, giving at most **six keywords**
altogether. Pick methodology/application terms from the journal's official
lists; those lists are not bundled and membership is not verified. The generic
`keywords` field is removed for T-ITS so it cannot serve as an extra category
outside that total. These custom portal widgets remain manual in the ReX filler.

The cover letter stays optional in the preparation schema. Resubmissions of
rejected papers must state their rejection history and prior paper ID in the
cover letter. Final files after acceptance include PDF plus LaTeX/Word source,
original figures, and author biographies/photos for Regular and Survey papers.
Those workflow requirements are recorded as notes rather than unconditional
initial-submission gates.

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

Author metadata and profile search, conflicts, consent, copyright, licenses, payments,
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
