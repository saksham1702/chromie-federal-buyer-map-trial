# Decisions

Add dated technical and product decisions here.


## 2026-09-16 - Phase one is research and planning, not the README prototype

The 2026-09-16 assignment scopes this phase to source discovery, data understanding, worked
examples, and an implementation plan. The README's resolver, forecaster, PDF pipeline, and
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
id, solicitation number, office and AAC code, posted date, type and award fields for the whole
public notice history, so it provides first-notice dates without an API key. It stays in
data/raw/ (not committed) and is referenced by hash.

## 2026-09-16 - Backtest cutoff rule

A backtest's cutoff is the day before the first public RFI or solicitation, or, for SeaPort-NxG
task orders and sole-source actions that never appear on SAM.gov, the day before award. Evidence
counts only if its "available by" date is on or before the cutoff: a document's release date, an
archive capture timestamp when the page is undated, or for FPDS records the signed date plus about
90 days of DoD publication lag. Later documents are recorded as post-cutoff checks, never as
evidence. The validator enforces the date rule and the rule that every cited evidence URL has a
fetched, hashed manifest row.
