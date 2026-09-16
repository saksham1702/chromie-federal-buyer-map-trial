# 06 - Continuous monitor: design, schedules, change detection, review, metrics, sample alerts

Written 2026-09-16. This is a design, not an implementation. It separates the reusable core from
the Navy-specific adapters, names the existing Chromie tables each part would use, and gives four
sample alerts built from evidence gathered in this package.

## In plain terms

The monitor watches six kinds of source on their own clocks, keeps every document it reads with
a hash and two dates (when it was published, when we fetched it), notices when a row or page
changes in a way that matters, ties the change to a program office through the same evidence
rules used for the worked examples, and hands anything uncertain to a person. Most of the
machinery is generic; what is Navy-specific is a short list of adapters (the Annex 25 spreadsheet,
the PEO and command web pages, the budget-book exhibits) and the alias table of office codes.

## 1. Shape

| Layer | Reusable core | Navy-specific adapter |
| --- | --- | --- |
| Source registry | `gov_procurement_sources` rows with `access_mode`, `refresh_cadence`, `verification_status`, `last_verified_at`, `known_access_gaps` | the 29 records in `source_registry.json` |
| Fetch and preserve | one fetch-and-record helper (direct, archive capture, browser, manual) writing a manifest row per retrieval, including failures and firewall stubs | fallback order per host (Wayback, WARP-off, Browserbase, manual) |
| Extract | PDF page-addressable text; spreadsheet row-addressable with a stable key; HTML text with link list | Annex 25 parser (header on row 6 or 7, PID as key); P-40/R-2 exhibit parser (line item, P-1 line, related PE, cost profile); tear-sheet parser (office, programs, PM) |
| Organization graph | `gov_organizations` + `gov_organization_relationships` with validity dates and provenance | alias table for PMW/PMA/PMS codes, LRAE HQ codes, NIWC competency codes; reorg-release reader |
| Attribution | evidence-gated resolver (`program_office_resolver.py`) producing an evidence class and abstentions; edges in `gov_procurement_organizations` with review status | Navy tear-sheet program-to-office map; LRAE existing-contract join |
| Signals and alerts | `gov_intel_facts` (event type, effective date, conflict status, superseded by) + `gov_intel_links` (office, award, notice, review status) | Navy alert rules below |
| Review | queue keyed on evidence class, value and novelty | reviewers who know NAVWAR |

## 2. Collection

Initial historical load, once:

| Source | Load | Key |
| --- | --- | --- |
| FPDS ATOM | all actions for N00039, N66001, N65236 from FY2019 (SPAWAR to NAVWAR rename) forward, paged by signed-date month | PIID + modification |
| USAspending | award detail for every PIID seen in FPDS; keyword search for each office alias | generated award id |
| SAM.gov | the full public extract once (about 230 MB), then the daily file | notice id + modified date; solicitation number for lineage |
| LRAE | current NAVWAR, NAVSEA, ONR releases plus every archived version that can be found | PID number, with row hash |
| Budget books | FY2019-FY2027 DoN OPN BA2 and RDT&E BA7-8 (and BA4-5 for development lines); enacted-year books for comparison | appropriation + line item / PE + fiscal year |
| Congress | govinfo packages for each year's NDAA and Defense appropriations (reports, explanatory statements, laws) | packageId; funding-table row |
| DVIDS | unit pages for NAVWAR and PEO C4I back to the earliest listed release | article id |
| Organization pages | current pages and tear sheets plus archived captures | URL + content hash |

Incremental schedules:

| Source | Cadence | Trigger for a fetch |
| --- | --- | --- |
| SAM daily extract | nightly | file `dateModified` changes |
| FPDS ATOM | daily | new actions since the last signed date per office; note the ~90-day DoD publication delay |
| USAspending | weekly, plus on demand for awards in an alert | award `last_modified_date` |
| DoD contracts RSS | daily | new item |
| DVIDS unit pages | daily | headline list diff |
| LRAE hosts | monthly, and weekly in May-July and December (release seasons observed) | new file link or file hash change |
| Organization pages and tear sheets | weekly | content hash change |
| Budget books | at the President's Budget release, then monthly for amendments; reprogramming actions when published | new file or hash change |
| govinfo / congress.gov | daily | new package matching the tracked bills |
| Federal Register | weekly | new document naming a tracked organization |

## 3. Documents

- Every retrieval writes a manifest row: original URL, final URL, method, retrieval time, HTTP
  status, MIME type, size, SHA-256, and for archive captures the capture timestamp. Failures and
  firewall stubs are rows too (`content_status: rejected_stub`), so a missing document is visible.
- Publication date is stored separately from retrieval date: the LRAE "Release Date" cell, the
  P-40 "Date: April 2026", a release's dateline, a tear sheet's distribution statement. Where a
  page carries no date, the archive capture timestamp is the "available by" date.
- Large PDFs are extracted page by page (page number kept with every passage); spreadsheets row by
  row with the stable key; a new hash of the same URL creates a new version and supersedes the old
  one rather than replacing it. Raw bytes stay in object storage; Chromie's
  `gov_procurement_documents` / `agency_brain_documents` hold the metadata and status.
- Size and safety limits: bounded file size, no macro execution, per-host rate limits and
  timeouts, resume for large books (the FY2027 OPN book needed a resumable download).

## 4. Detecting meaningful change and deduplicating

| Source | Unit | Meaningful change | Noise to ignore |
| --- | --- | --- | --- |
| LRAE | row by PID | new row; removed row; change in requirement office, value range, solicitation or award quarter, procurement method, existing contract, incumbent, follow-on/new | POC name or phone changes (recorded, not alerted) |
| SAM | notice lineage by solicitation number | first notice for a solicitation; type change (sources sought to solicitation); amendment that changes dates, set-aside or scope; award notice | re-posts with identical content |
| FPDS / USAspending | award by PIID | new award; option exercise; ceiling increase above a threshold; period-of-performance extension; description change | administrative modifications (COR change, clause updates, payment office) |
| Budget books | line item / PE | request differs from prior enacted beyond a threshold; new line; zeroed line; narrative names a new program | rounding |
| Congress | funding-table row | mark differs from request; directive language naming a tracked program | none |
| Organization pages | page | office added or removed; parent or name changed; leadership change | styling |
| DVIDS | release | leadership change; industry event; reorganization; program milestone | unrelated units |

Deduplication: one lineage per solicitation number across notice types (Chromie already tracks
notice amendments); one award per PIID with modifications as children; one forecast requirement
per PID across LRAE releases; one organization per canonical id with aliases.

## 5. Keeping ownership mappings current

See `02_organization_map.md` section 5. In monitor terms: a hash change on an organization page
or a reorganization release opens a review item; approved changes add dated edges and never
delete history; unknown codes seen in the LRAE or award text enter the alias table as
`unverified` and block automatic attribution until confirmed.

## 6. Source health

Each source carries `verification_status`, `last_verified_at`, consecutive failure count and the
last successful hash. Rules: a source that fails three consecutive fetches, or has not changed for
twice its expected cadence, is flagged stale; an HTTP 403 with a bot-protection body is classified
"blocked" and routed to the next fallback path; a 200 whose body is a firewall stub is classified
`rejected_stub`, not success. Flags surface in the review queue with the last good retrieval date.

## 7. Human review

Queue entries: every `inferred`, `ambiguous` or `unresolved` attribution above a value threshold;
every new organization code; every conflicting official statement; every alert whose evidence is a
single source. Reviewers confirm, correct or reject; confirmed results become reviewed examples
(gold candidates) and alias-table entries.

## 8. Metrics

| Metric | Definition | Where it comes from |
| --- | --- | --- |
| Coverage | share of NAVWAR HQ (and NIWC) actions in the window with an attribution or a reasoned abstention; share of PEO C4I LRAE rows tracked to a notice or award | FPDS, LRAE, attribution table |
| Attribution accuracy | precision by evidence class against reviewed examples; abstention correctness | review queue outcomes |
| Alert usefulness | reviewer rating per alert; share acted on | review queue |
| Advance notice | days between the earliest recorded signal and the first notice or award for the same requirement | backtests in `05_early_signals_and_backtests.md` |
| Source health | share of sources verified within cadence | source registry |

## 9. Sample alerts

Format: what changed; affected office and ancestry; evidence; uncertainty; why it matters.

**A. New requirement (LRAE row appears)**
- What changed: a new NAVWAR LRAE row "NILE In-Service Support (ISS) 6 Contract" with requirement
  office `PMW-150`, anticipated solicitation FY26 Q2, award FY27, existing contract N0003922D1004,
  incumbent Technology Unlimited Group, PID `N00039-25-RFPREQ-PMW-150-0067`.
- Office: PMW 150 Naval Command and Control Systems -> PEO C4I -> (from 2026-05-11) PAE Mission
  Systems; contracting office NAVWAR HQ N00039.
- Evidence: LRAE release 2025-06-19 (archive capture 2026-01-08); FPDS record of N0003922D1004.
- Uncertainty: forecast only; quarter and value range are estimates; no notice yet.
- Why it matters: a follow-on to a known incumbent contract with a stated quarter gives a
  capture team two to three quarters of warning.

**B. Funding change (request vs enacted)**
- What changed: OPN 1810N BA2 line item 2915 "CANES" (P-1 line 64, related PE 0303138N): FY2026
  enacted 534.324, FY2027 request 493.046 ($ millions), a decrease of about 41 million; the
  out-years return to the 505-533 range.
- Office: PMW 160 Tactical Networks (CANES is a PMW 160 program per the 2025 tear sheet); the
  budget line itself names no office, so the link is an inference by program.
- Evidence: FY2027 OPN BA2 justification book, P-40 exhibit dated April 2026 (pages 645-658);
  P-1 detail page.
- Uncertainty: enacted FY2027 figures will differ; the line funds many contracts and the effect on
  any one procurement is not observable publicly.
- Why it matters: a lower request year against a larger prior enacted amount changes quantities
  and timing for CANES production and installation buys in FY2027.

**C. Forecast revision (LRAE row changes between releases)**
- What changed (illustrative until a second LRAE release is captured): row PID
  `N00039-24-RFPREQ-PMW-160-0002` "PMW 160 Engineering Support Services (ESS) Follow-on" moves
  anticipated solicitation from FY25 Q4 to a later quarter, or its value range changes.
- Office: PMW 160 -> PEO C4I -> PAE Mission Systems.
- Evidence: the two LRAE versions with release dates and hashes; the row diff.
- Uncertainty: the LRAE is an estimate; a slip may reflect an acquisition-strategy change or a
  clerical update.
- Why it matters: slips and value changes move capture timelines and signal strategy changes.

**D. Potential recompete**
- What changed: order N0003922F3000 (Booz Allen, PEO C4I engineering support "IN SUPPORT OF
  PROGRAM MANAGER, WARFARE TACTICAL NETWORKS (PMW 160)") reaches its period-of-performance end on
  2026-10-26; the LRAE forecast a follow-on award in FY26 with the same incumbent; the predecessor
  order N0003917F3000 ran 2016-2021, so the requirement recurs on a five-year cycle.
- Office: PMW 160; contracting office NAVWAR HQ; vehicle SeaPort-NxG.
- Evidence: USAspending award detail; FPDS feeds for both orders; LRAE row.
- Uncertainty: the follow-on may already be awarded and not yet published (DoD publication lag);
  the vehicle may change.
- Why it matters: a recompete of a five-year support order is the most predictable event in the
  portfolio and the one a competitor can prepare for earliest.

## 10. Gaps against the existing Chromie model

- No entity for a forecast row (LRAE) or a budget line; both would be `gov_intel_facts` with
  structured `data` today, which is queryable but not typed. A typed row-keyed table for
  forecasts (PID, release, office, existing contract) and for budget lines (appropriation, line
  item, PE, fiscal-year columns) would make revisions and deltas first-class.
- `agency_brain_documents.doc_type` lacks LRAE, tear sheet, RFI and industry-day types; the
  Python model already lists some of them.
- Organization-scoped Agency Brain items exist (`scope_organization_id`), so PMW-level budget,
  forecast and people claims fit without schema change.
- Attribution edges (`gov_procurement_organizations`) have a relationship type and confidence but
  no evidence-class field; the class can live in `source_ref` or `match_basis` until a column exists.

## 11. Reusable versus Navy-specific, and expansion

Reusable without change: fetch-and-record, document versioning, FPDS/USAspending/SAM/govinfo/
Federal Register/DVIDS adapters, the organization graph, the resolver, the review queue, the
metrics. Reusable across the Navy: the Annex 25 LRAE parser (NAVWAR, NAVSEA, ONR/NRL and other
activities publish the same template) and the P-40/R-2 exhibit parser (all DoN books). Navy- and
portfolio-specific: the alias table, the tear-sheet program map, the list of organization URLs,
and the host fallback rules. Expansion order: other PAE Mission Systems components (PEO Digital,
PEO MLB, PEO IWS) using the same LRAE and FPDS adapters; NAVSEA and NAVAIR portfolios using their
LRAEs; other military departments by swapping the budget-book parser's exhibit conventions;
civilian agencies through the existing Agency Brain per-agency ingest pattern.
