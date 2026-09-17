# Decisions

Add dated technical and product decisions here.


## 2026-09-16 - Phase one is research and planning, not the README prototype

Phase one covers source discovery, data understanding, worked examples, and an implementation
plan. The README's resolver, forecaster, PDF pipeline, and
Supabase proposal move to the backlog. Code in this phase is limited to one artifact validator
and a fetch-and-record helper.

## 2026-09-16 - Deliverables live in research/, on branch trial/navy-navwar-peo-c4i

`build/` is gitignored, so the reviewable package is committed under `research/` with the
README's file names kept where they overlap (source_registry.json, organization_seed.json,
manual_pdf_requests.json, documents_manifest.jsonl). Downloaded bytes stay in `data/raw/`.

## 2026-09-16 - Evidence rules

Official public sources only. A Wayback Machine capture of an official page is a dated copy of
that page and its capture timestamp is the "available by" date. Third-party mirrors are
pointers, never evidence. Chromie's production schema is used as column-level shape only; no
production identifiers or data appear in these artifacts.

## 2026-09-16 - Access paths for Akamai-blocked Navy sites

navwar, peoc4i, navsea, navair, niwc, navy.mil, gao and dodig return HTTP 403 to curl and to
headless Chrome from this machine; secnav's budget library closes the TLS handshake;
comptroller.defense.gov interrupts. Egress is Cloudflare WARP. Approved fallbacks, in order:
Wayback capture, a WARP-off fetch session, Browserbase remote browser, manual retrieval queue.

## 2026-09-16 - "PAE" is a reorganization, not a data system

The README asks for an investigation of the "Navy PAE system". Official releases show PAE means
Portfolio Acquisition Executive: the Department of the Navy stood up PAE Mission Systems on
2026-05-11, consolidating mission-systems elements of PEO C4I, PEO Digital, PEO IWS, PEO MLB,
three DRPMs, Minotaur, NAVWAR, NAVSEA, NAVAIR and MCSC. The organization map models this as a
dated reorganization; there is no PAE record system to crosswalk.

## 2026-09-16 - The Navy LRAE is the primary forecast source and the anchor for attribution

NAVWAR's Long-Range Acquisition Estimate (sheet "LRAE Annex 25", release 2025-06-19) carries an
"Associated Program or Requirement Office" column, the contracting UIC, the existing contract
number and the incumbent on one row, and its PID numbers embed the office code. ONR/NRL publish
the same template, so one adapter covers Navy activities. Every row is an estimate and is
recorded as such; a forecast never counts as ownership evidence on its own.

## 2026-09-16 - Conflicting official statements are kept side by side

The NAVWAR acquisition-pathways page captured 2026-09-01 still lists PEO C4I, PEO MLB and PEO
Digital as NAVWAR components, while the 2026-05-11 release consolidates them into PAE Mission
Systems. The seed graph keeps both edges, dates the consolidation, and flags the pair for
review rather than choosing one.

## 2026-09-16 - Department of the Navy budget library is an access gap for automation

secnav.navy.mil/fmc returns a "Request Rejected" firewall stub to the Wayback crawler as well
as to this machine. Budget exhibits will be retrieved in a WARP-off session or manually and
recorded in manual_pdf_requests.json until then.

## 2026-09-16 - Registry records use Chromie's source-table vocabulary and four statuses

`source_registry.json` uses the `gov_procurement_sources` field names where they exist and
records each source as `verified` (an inspected example with a hashed document), `blocked` (every
approved access path failed), `restricted` (login or key required) or `not_inspected`. The
Wayback Machine is listed as a retrieval path, not as a source of record: a capture is a dated
copy of an official URL and is always cited with its original URL and capture timestamp.

## 2026-09-16 - DoD contract announcements are monitored through the RSS feed

The defense.gov/war.gov article pages return 403 to automation, but the ArticleCS RSS endpoint
answers directly with titles, dates and links. The registry treats the feed as the trigger and
the article body as a fallback-path fetch.

## 2026-09-16 - Attribution evidence classes and the modification rule

Every reviewed attribution carries one of four classes: directly_documented (an official record
of the action names the office), inferred (only a corroborating official document names it: an
LRAE follow-on row, a tear-sheet program list, an article naming the awarding office), ambiguous
(candidates without a document tying program to office) or unresolved (no signal; the path to
resolution is recorded). Modifications are attributed through their base award. Multi-office
descriptions keep every named office and never collapse to one.

## 2026-09-16 - Alerts always carry the evidence class and the ancestry as of the event date

An alert names what changed, the office and its parent chain as of the event date (PEO C4I under
NAVWAR before 2026-05-11, under PAE Mission Systems from that date), the documents with dates, the
uncertainty, and why it matters. A forecast alert says it is a forecast; a budget alert says the
office link is an inference by program name.

## 2026-09-16 - The SAM.gov full public extract is the notice history for backtests

The daily ContractOpportunitiesFullCSV.csv (about 230 MB, range requests supported) carries notice
id, solicitation number, office and AAC code, posted date, type and award fields, so it provides
first-notice dates without an API key. Inspection showed it holds the current dataset only
(84,504 rows, almost all 2025-2026); older years are separate archived files in the same extract
service and are the next retrieval. The file stays in data/raw/ (not committed) and is referenced
by hash.

## 2026-09-16 - Backtest cutoff rule

A backtest's cutoff is the day before the first public RFI or solicitation, or, for SeaPort-NxG
task orders and sole-source actions that never appear on SAM.gov, the day before award. Evidence
counts only if its "available by" date is on or before the cutoff: a document's release date, an
archive capture timestamp when the page is undated, or for FPDS records the signed date plus about
90 days of DoD publication lag. Later documents are recorded as post-cutoff checks, never as
evidence. The validator enforces the date rule and the rule that every cited evidence URL has a
fetched, hashed manifest row.

## 2026-09-16 - SAM.gov notices come from the keyless site API, not the documented public API

The documented Opportunities API host (api.sam.gov) returned HTTP 404 with an empty body for
every path from two different networks, and its documentation issues keys from a SAM.gov
account, not api.data.gov. The JSON endpoints behind the SAM.gov web application
(`/api/prod/opps/v2/opportunities/{id}`, `/opps/v3/.../resources`, `/sgs/v1/search/`) answer
without a key, return full description text and attachments, and reach archived notices back to
2014; Chromie's runner already uses them. Saksham's api.data.gov key is kept in the ignored
`.env` for other api.data.gov-fronted services (govinfo, congress.gov) and is not sent to SAM.

## 2026-09-16 - The Navy web block is geographic; Browserbase is the standing live-fetch path

Turning Cloudflare WARP off moved the egress to an Indian ISP address and every .mil host still
returned 403 or dropped the connection, so the block is on non-US addresses, not on WARP. A
Browserbase hosted browser (US egress) returned the live PEO C4I, NAVWAR, PEO Digital, PEO MLB,
NIWC, navy.mil, war.gov, DON CIO and DoD Comptroller pages and files; secnav.navy.mil still
resets. Live pages are recorded with method "browserbase". The Comptroller's P-1 and R-1 display
tables are the source of record for line and program-element amounts; the DoN exhibit narratives
remain queued for the text that names programs and milestones.

## 2026-09-16 - The PEO C4I web presence is gone; the PAE publishes portfolios, not offices

Every path on peoc4i.navy.mil now serves the PAE Mission Systems site (missionsystems.navy.mil),
which names five capability portfolios and no program offices. The April 2026 archive captures of
the office pages and tear sheets are the last public record of the PMW inventory in that form. The
organization map keeps the PEO C4I parentage with the dated consolidation edge and records the
office-to-portfolio mapping only as a candidate until the PAE publishes it.

## 2026-09-17 - Organization memory is a dated graph that holds PEO and PAE structures together

No reliable org chart exists for Navy acquisition offices, and the PAE reorganization is in
progress. The memory therefore stores offices as nodes with dated relationships and an alias table
fed by a registry of code families (`org_code_families.json`); records resolve to the ancestry
valid on their own date; PAE consolidations are added as dated edges and never overwrite PEO
history. Specification in `08_org_memory_format.md`.

## 2026-09-17 - Manual first, then monitor

Each source is worked by hand once and the steps written down (`09_manual_collection_runbook.md`)
so the source list can be verified before automation; the monitor design then replaces each manual
step with a scheduled diff.

## 2026-09-17 - Recall over precision for offices and contacts

Because PEO and PAE ownership is ambiguous and a wrong first contact only costs a redirect, weak
attributions still list ranked candidate offices and public contacts with a confidence label
(`contact_candidates.json`); alerts surface uncertainty rather than suppress it.

## 2026-09-18 - A manual cycle becomes a package only when it regenerates from saved bytes

The reviewer's request for accurate, traceable data is met by `datapack/`: the source hash is the
contract, the build reads only bytes recorded in the manifest, every row of the sheet gets one
decision with a reason, every join is labelled explicit or inferred with unmatched rows kept, and
the output hashes are recorded so a second run proves idempotence. Network lookups are a separate
`collect` step so the build never depends on what a host answers today. Rows are also written in
the layers of the proposed production model (needs, requirements, funding observations,
procurement references, evidence) so nothing is reshaped later.

## 2026-09-18 - Observations, relationships and interpretations are stored apart; corrections are retractions

After review, `organization_seed.json` separates what a source states (observations with the exact
words, revision and date) from the dated claims resting on them (relationships) and from our own
readings (interpretations). Effective dates exist only when a source gives them; otherwise they are
`unknown`, and currency is a separate field, so an open end date never reads as "confirmed
current". A wrong claim is retracted with a reason and a pointer to its replacement; only a
real-world change documented by a source gets an end date. The reviewer's identity and date are
recorded apart from the assistant's draft. Contacts follow the same split: `contact_observations.json`
holds what a source says about a person or channel (with sheet, row and PID for the forecast),
`contact_recommendations.json` holds routes with a source confidence and a currency confidence, and
`review_log.json` records every check against saved bytes.

## 2026-09-18 - Every LRAE release is its own package; diffs never merge rows

Three NAVWAR releases are now saved (2023 export, June 2024, June 2025). Each is packaged
separately from its own bytes, and a diff between releases is written into the newer package. The
diff keys on the PID where both rows have one and on title plus office code otherwise, because
the June 2024 release has no PID column and PIDs turned out to be only partly stable. Weak matches
are reported as such rather than forced; a record that cannot be followed across releases reads as
removed and added, and the reviewer sees it.
