# 07 - Implementation backlog, effort, blockers, expansion

Written 2026-09-16. Effort is in engineer-days for one person who knows the Chromie runner; S is
under a day, M is two to three days, L is a week or more. Priority P0 is needed before any
monitoring runs; P1 makes the pilot useful; P2 completes the brief's ambitions; P3 is expansion.

## In plain terms

Most of the plumbing already exists in Chromie. The first two weeks of work are Navy adapters
(the LRAE spreadsheet, the budget exhibits, the organization pages) and the alias table, plus
loading the reviewed examples as a regression set. The blockers are access, not engineering: a
SAM API key, a network path to the Navy web hosts, and two documents that need a human download.

## Backlog

| # | Item | Priority | Effort | Depends on | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | Load `source_registry.json` into `gov_procurement_sources` (Navy rows) and run the health check | P0 | S | none | field names already aligned |
| 2 | Alias table for office codes (PMW/PMA/PMS, LRAE HQ codes, NIWC competency codes) as `gov_organizations.aliases` on the existing PEO C4I rows plus new rows for PAE Mission Systems, PEO EIS (historical), PMW 220/250, NEN | P0 | S | organization_seed.json | add 2026 names as aliases; date the PAE consolidation edge |
| 3 | Annex 25 LRAE adapter: download, hash, parse rows keyed by PID, detect row-level changes, emit forecast facts | P0 | M | 1, 2 | one parser for NAVWAR, NAVSEA, ONR/NRL; header row differs (6 vs 7) |
| 4 | FPDS ATOM adapter for contracting offices N00039, N66001, N65236 with month-window backfill from FY2019 and daily increments | P0 | M | 1 | 10 entries per page; DoD ~90-day lag; store funding office and referenced IDV |
| 5 | Attribution pass over new FPDS actions with the production resolver; write `gov_procurement_organizations` edges with evidence class; route non-direct results to review | P0 | M | 2, 4 | resolver exists; add LRAE existing-contract join and tear-sheet program map as corroboration inputs |
| 6 | Load the 19 reviewed examples as a regression set and replay them through the resolver | P1 | S | 2, 5 | precision on direct cases must be 100%; abstention on EX16, EX19 |
| 7 | SAM daily extract adapter (nightly download, diff by notice id + modified date, lineage by solicitation number) | P1 | M | 1 | 230 MB file; range requests supported; extract already carries `AAC Code` for office filtering |
| 8 | SAM Opportunities API adapter for descriptions and attachments of watched offices | P1 | S | user's api.data.gov key | blocked until a key is provided |
| 9 | DVIDS unit-page adapter (headline diff, release text, leadership and reorganization extraction) | P1 | S | 1 | NAVWAR and PEOC4I units; other units on expansion |
| 10 | Budget exhibit adapter: P-40 and R-2 cover pages to line item / PE / cost profile rows; request-vs-enacted deltas; program-name join to offices via tear sheets | P1 | L | budget books retrieved | OPN BA2 FY2027 parsed in this package; RDT&E BA7-8 still to retrieve; FY2026 books for the enacted baseline |
| 11 | Congressional adapter: govinfo packages for NDAA and Defense appropriations; funding-table rows and directive language for tracked programs | P1 | M | 1 | table extraction from long PDFs/XML is the hard part |
| 12 | Organization-page monitor with hash diff and review items; archive-capture fallback; reorg-release reader | P1 | M | 2 | Akamai-blocked hosts need the fallback path |
| 13 | Alert rules and templates (new requirement, funding change, forecast revision, recompete) writing `gov_intel_facts` and links | P1 | M | 3, 4, 10 | formats in `06_continuous_monitor_design.md` |
| 14 | Review queue views for Navy attribution and alerts; reviewer outcomes feed the alias table and gold set | P1 | M | 5, 13 | existing gate-review tables may serve |
| 15 | Backtest harness: cutoff-dated evidence sets, prediction record, comparison with the first notice or award; advance-notice metric | P2 | M | 3, 4, 7 | rules in `05_early_signals_and_backtests.md` |
| 16 | Typed tables for forecast rows and budget lines (or agreed JSON shapes in `gov_intel_facts`) | P2 | M | schema owner's review | production schema change; not in this phase |
| 17 | Tear-sheet parser (office, programs, PM, contacts) and people edges with observation dates | P2 | S | 12 | 11 PEO C4I sheets inspected |
| 18 | DoD contracts RSS + article fallback fetch; Federal Register weekly query | P2 | S | 1 | low yield for program-office attribution, useful for large awards |
| 19 | Browserbase transport for Akamai-blocked hosts (test one page; keep if it passes) | P2 | S | Browserbase key | SLED trial's `BrowserFetcher(remote=True)` is reusable |
| 20 | Expansion: PEO Digital, PEO MLB, PEO IWS offices and their LRAE codes; NAVSEA and NAVAIR LRAEs; Army PAEs; civilian agencies through the existing per-agency ingest | P3 | L | 1-14 | same adapters, new alias tables and organization URLs |

## Blockers and what unblocks them

| Blocker | Effect | Unblock |
| --- | --- | --- |
| No SAM Opportunities API key in this environment | notice descriptions and attachments unavailable; solicitation documents are where most `inferred` cases would become `directly_documented` | register a free api.data.gov key (user) and store it outside git |
| Geographic block on navwar, peoc4i, navsea, navair, niwc, navy.mil, war.gov, comptroller, gao.gov (non-US addresses get 403; WARP on or off) | live pages unreadable from this machine; archive captures lag | Browserbase US-egress browser (tested 2026-09-16, works) or a US-hosted fetcher in production |
| secnav.navy.mil firewall resets (budget library, OSBP LRAE index), also through Browserbase | DoN exhibit narratives (RDT&E BA7-8, FY2026 books) and the Navy-wide LRAE index still missing; line amounts are covered by the Comptroller P-1/R-1 tables | manual queue in `manual_pdf_requests.json`; a US residential or government network |
| PIEE and SeaPort-NxG require accounts | solicitation packages and task-order competitions invisible | accept the gap; rely on SAM synopses and FPDS awards; record as `restricted` |
| DoD FPDS publication delay (~90 days) | award and recompete signals arrive late | forecast (LRAE) and period-of-performance signals carry the early warning |
| Wayback CDX index intermittently offline | historical LRAE versions cannot be enumerated | retry; keep the raw-capture path that works |
| PEO Digital and PEO MLB office inventories not retrieved | sibling offices only partly modeled (hard negatives incomplete) | manual queue; organization pages once a fetch path exists |

## Expansion plan

1. Within PAE Mission Systems: PEO Digital and PEO MLB offices (alias table from their pages),
   PEO IWS offices (already in Chromie's graph; NAVSEA LRAE codes `IWS-x.0` observed), DRPM
   Overmatch. Same adapters; new aliases and URLs.
2. Rest of the Department of the Navy: NAVSEA Enterprise LRAE (228 requirement offices observed),
   NAVAIR and warfare-center LRAEs, ONR/NRL (already parsed); NAVSEA's Deputy Program Manager
   roster for codes and people; the same OPN/RDT&E books cover every Navy line.
3. Other military departments: the Army's PAE structure is already partly in Chromie's graph
   (PAE Fires); Army and Air Force LRAE equivalents (forecasts) and J-books use similar exhibits
   with different conventions, so the exhibit parser needs a per-department profile.
4. Civilian agencies: the Agency Brain per-agency ingest pattern plus agency procurement forecasts
   (already a `doc_type`), with FPDS/USAspending/SAM adapters unchanged.

## Definition of done for the next phase

A reviewer picks any NAVWAR HQ action from the last quarter and sees an attribution with an
evidence class and quoted passage, or a reasoned abstention; picks any PEO C4I office and sees
its LRAE rows, budget lines, notices and awards with dates; and receives the four alert types
with evidence when the underlying sources change.
