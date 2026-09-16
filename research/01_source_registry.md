# 01 - Source registry: what each source proves, how it is reached, how often to look

Written 2026-09-16. The machine-readable registry is `source_registry.json` (one record per
source, field names chosen to load into Chromie's `gov_procurement_sources`). The table below is
generated from that file; the prose explains how the sources fit together. Every `verified` row
has an inspected example whose hash is in `documents_manifest.jsonl`; rows marked `blocked`,
`restricted` or `not_inspected` say why and appear in `manual_pdf_requests.json` when a human
retrieval would resolve them.

## In plain terms

Six kinds of public record cover the life of a Navy requirement: the organization pages that say
who owns what; the budget books that say what the Department wants to fund; the congressional
documents that say what was funded or changed; the Long-Range Acquisition Estimates that say what
each office plans to buy and when; SAM.gov notices for the live acquisition; and FPDS/USAspending
for the award and everything after it. For NAVWAR all six exist in public. The forecast layer is
unusually strong because the Navy's LRAE spreadsheet names the requirement office on every row.
The weak points are access, not existence: most Navy web hosts block automated clients, the
budget host resets connections, and solicitation documents increasingly sit inside PIEE.

## Sources by lifecycle stage

| Stage | Source | Access | Status | Inspected example | Monitor |
| --- | --- | --- | --- | --- | --- |
| Organization and ownership | PEO C4I official site (peoc4i.navy.mil) | webpage | verified | 11 program offices listed with tear-sheet links; footer 'One NAVWAR ... PEO C4I & Space, PEO Digital, PEO MLB' (wayback, 2026-09-16) | weekly hash diff of Program-Offices, Leadership, Contact and each tear |
| Organization and ownership | NAVWAR official site (navwar.navy.mil) | webpage | verified | 'NAVWAR HQ ... procures the IW systems sought by PEO C4I, PEO MLB and PEO Digital'; NIWCs 'the technical heart (wayback, 2026-09-16) | weekly hash diff of About, Work-With-Us, Small-Business-Programs; mont |
| Organization and ownership | DVIDS (Defense Visual Information Distribution Service) unit pages and releases | webpage | verified | change of command: Castillejo to PMW 150 relieving Jolie; Andalis to PMW 760 (direct, 2026-09-16) | daily fetch of unit pages, diff headline list |
| Organization and ownership | Department of the Navy PAE press releases (navy.mil, paemaritime.navy.mil, DVIDS mirror) | webpage | verified | consolidation list names PEO C4I, PEO Digital, PEO IWS, PEO MLB, DRPMs, Minotaur, NAVWAR, NAVSEA, NAVAIR, MCSC (direct, 2026-09-16) | weekly check of PAE domains and DVIDS for new releases |
| Organization and ownership | NAVSEA Small Business Partnerships documents (org chart, Deputy Program Manager roster) | pdf | verified | two-page table: title, phone, code, description (PMS 396, PMS 397, PMS 450, ...) (wayback, 2026-09-16) | quarterly |
| Organization and ownership | Federal Register API | api | verified | query 'Naval Information Warfare' returns dated notices with agencies and PDF links (direct, 2026-09-16) | weekly query per organization name |
| Agency intent | Department of the Navy budget materials (FMB): justification books by appropriation | pdf | verified | 37 PDF links: RDTEN_BA1-3 ... BA7-8, OPN_BA1 ... BA5-8, OMN, WPN, APN, SCN, Highlights_Book, DON_Budget_Card (direct, 2026-09-16) | annual at budget release, then monthly checks for amended books |
| Agency intent | DoD Comptroller budget materials | pdf | blocked | index page captured by Wayback 2026-05-23 contains no document links (client-rendered); PDFs not retrieved | annual |
| Agency intent | Federal IT Dashboard / IT Collect public API | api | verified | landing page reachable; detailed pull deferred to the existing prod ingest (direct, 2026-09-16) | weekly (existing prod job) |
| Agency intent | Navy posture statements and acquisition testimony (congress.gov hearings, committee sites) | api | not_inspected | not yet sampled for Navy acquisition hearings | weekly during posture season |
| Congressional decisions | govinfo API (committee reports, explanatory statements, enacted laws, bills) | api | verified | H. Rept. 119-698, NDAA FY2027, issued 2026-06-15, with download links (direct, 2026-09-16) | daily poll of new CRPT/CREC/PLAW packages matching defense keywords |
| Congressional decisions | congress.gov API (bills, amendments, committee reports, hearings) | api | verified | bill endpoint responds with DEMO_KEY (direct, 2026-09-16) | daily |
| Planned requirements | NAVWAR Long-Range Acquisition Estimate (LRAE Annex 25) | spreadsheet | verified | 833 rows; 144 rows name a PEO program office, all contracted by N00039; 200 rows carry an existing contract nu (wayback, 2026-09-16) | monthly check for a new release; diff rows by PID number |
| Planned requirements | Department of the Navy OSBP Long Range Acquisition Estimate index | webpage | blocked | three fetch attempts reset; queued for a WARP-off session | monthly |
| Planned requirements | NAVSEA Enterprise Long-Range Acquisition Estimate | spreadsheet | verified | sheet 'Annex 25 Template'; 228 distinct requirement offices; N00024 NAVSEA HQ is the top contracting UIC (wayback, 2026-09-16) | monthly |
| Planned requirements | ONR and NRL Long-Range Acquisition Estimate | spreadsheet | verified | two data sheets plus validation lists; header on row 7 (direct, 2026-09-16) | monthly |
| Planned requirements | LRAEs posted as SAM.gov Special Notices (NAVSUP, NAWCAD pattern) | api | not_inspected | pointer only; notice attachment not retrieved (needs SAM API key) | weekly search of Special Notices for 'Long Range Acquisition' |
| Planned requirements | PEO C4I industry engagement (AFCEA WEST events, Industry Intake Form) via DVIDS | webpage | verified | 'third annual engagement event at AFCEA WEST 2026, featuring all 11 program offices' (direct, 2026-09-16) | daily via DVIDS unit page |
| Planned requirements | NAVWAR Commercial Solutions Openings | webpage | verified | page links a SAM notice and the PIEE vendor instructions (wayback, 2026-09-16) | weekly |
| Planned requirements | SBIR/STTR topics (sbir.gov; DoD SBIR/STTR portal) | webpage | verified | search page reachable; Navy topic sampling deferred (direct, 2026-09-16) | per cycle (three times a year) |
| Active acquisition | SAM.gov Contract Opportunities public data extract (daily CSV of current notices) | export | verified | 241,486,025 bytes; 47 columns incl. AAC Code, Sol#, Type, PostedDate, AwardNumber; 535 NAVWAR-family notices ( (direct, 2026-09-16) | nightly download and diff on notice id + modified date |
| Active acquisition | SAM.gov Opportunities API v2 (search, description, attachments) | api | blocked | HTTP 404, empty body, server istio-envoy, with and without a key (direct, 2026-09-16) | hourly for watched offices once a key is available |
| Active acquisition | PIEE Solicitation Module (replaced NAVWAR eCommerce) | manual | restricted | official access-instructions PDF (TLS chain is DoD PKI; fetched with verification off and recorded) (direct, 2026-09-16) | not automated; rely on SAM synopses and record the gap |
| Active acquisition | SeaPort-NxG portal (Navy services vehicle) | manual | blocked | connection failed (HTTP 000) on every attempt | not automated; awards tracked through FPDS referenced IDVs |
| Awards and execution | FPDS ATOM public feed | api | verified | 10 actions; funding offices N00039 and N00024 (NAVSEA HQ); descriptions such as 'LTS/CLTS PRODUCTION AND SUSTA (direct, 2026-09-16) | daily pull per contracting office since last signed date |
| Awards and execution | USAspending API v2 | api | verified | description names 'PROGRAM MANAGER, WARFARE TACTICAL NETWORKS (PMW 160)'; PoP 2021-10-27 to 2026-10-26; solici (direct, 2026-09-16) | weekly refresh of watched awards; nightly keyword search for office co |
| Awards and execution | DoD (Department of War) daily contract announcements (RSS + article pages) | api | verified | 10 items: 'Contracts for Sept. 15, 2026' ... with war.gov article links and pubDate (direct, 2026-09-16) | daily RSS poll; fetch each day's article through the fallback path |
| Awards and execution | GAO bid protest decisions and docket | webpage | blocked | blocked (HTTP 403); Chromie's existing pursuit-intelligence runner already covers GAO | weekly |
| Organization and ownership | Internet Archive Wayback Machine (dated copies of official pages) | api | verified | 2026-05-19 capture shows the PAE Mission Systems front page (wayback, 2026-09-16) | on demand |
| Active acquisition | SAM.gov Contract Opportunities archived yearly extracts (FYxxxx_archived_opportunities.csv) | export | not_inspected | listing inspected (36 files); no yearly file downloaded yet (direct, 2026-09-16) | quarterly re-pull of the two most recent fiscal years |
| Active acquisition | SAM.gov site API (opps v2/v3 and sgs search, keyless) | api | verified | NILE ISS 6 RFI detail with description body naming PEO C4I / PMW 150; 15 solicitation numbers searched, notice (direct, 2026-09-16) | on demand per solicitation number surfaced by FPDS, the LRAE or the da |

## How the sources connect

Three kinds of join carry a requirement across stages (details and pitfalls in
`03_data_connection_map.md`):

- Shared identifiers: contracting office UIC (LRAE, FPDS, SAM, PIID prefix), contract number
  (LRAE "Existing Contract Number", FPDS, USAspending), solicitation number (SAM, FPDS),
  referenced IDV (FPDS, USAspending).
- Office codes and names in text: the LRAE requirement-office column; "PMW 160" in award and
  notice descriptions; tear sheets that map programs to offices; DVIDS releases that map people
  to offices with dates.
- Program names: the only bridge between a budget line and an office, so it is always recorded
  as an inference with both documents cited.

## Requested, enacted, obligated, ceiling

These four numbers describe different things and live in different sources; the registry keeps
them apart and the connection map (section 3 there) defines each. In short: the request is in
the Department of the Navy justification books; the enacted amount and any marks are in the
appropriations acts, explanatory statements and committee reports on govinfo; obligations are
per action in FPDS and per award in USAspending; the ceiling is the award's base-and-all-options
value. The LRAE's value ranges are estimates and belong to none of the four.

Where the budget-to-contract connection cannot be established publicly: no public source maps a
program element or procurement line item to a contract number. The join stops at the program
name in the exhibit narrative. For PEO C4I that means a CANES procurement line can be tied to
PMW 160 through the tear sheet and to CANES awards through award descriptions, but the dollar
flow from that line to a specific contract is not observable.

## Access findings

| Path | Sources | Notes |
| --- | --- | --- |
| Open, direct | USAspending API, FPDS ATOM, SAM public extract listing, govinfo, congress.gov, Federal Register, DVIDS, paemaritime.navy.mil, ONR, IT Dashboard, sbir.gov, PIEE landing, DoD contracts RSS | no key or a free api.data.gov key |
| Akamai bot protection (HTTP 403 to curl and headless Chrome) | navwar, peoc4i, navsea, navair, niwc, navy.mil, defense.gov pages, gao.gov | Wayback captures used; a WARP-off session or Browserbase is the live fallback |
| Firewall resets | secnav.navy.mil (budget library, OSBP) | one direct fetch of the FY2027 page succeeded; the Wayback crawler receives "Request Rejected" stubs; manual queue |
| Login or key required | PIEE Solicitation Module (vendor login), SeaPort-NxG (vehicle holder) | recorded as `restricted` or `blocked`; SAM synopses and FPDS awards stand in |
| Documented host dead | api.sam.gov (Opportunities public API): 404 from two networks; its keys come from a SAM.gov account, not api.data.gov | the keyless SAM.gov site API (notice detail, description, attachments, archived search) replaces it |

## Cadence and lag

| Source | Publication cadence | Reporting lag | Proposed monitor |
| --- | --- | --- | --- |
| SAM public extract | daily | one day | nightly download, diff by notice id and modified date |
| FPDS ATOM | continuous | about 90 days for DoD actions | daily pull per contracting office |
| USAspending | daily loads | follows FPDS | weekly refresh of watched awards; nightly keyword search |
| NAVWAR LRAE | roughly annual with updates | forecast (estimate) | monthly check for a new release; diff rows by PID |
| DoN budget books | annual, plus amendments | request year minus one | annual at release, monthly for amendments |
| govinfo / congress.gov | daily | days | daily poll of new defense packages |
| DVIDS unit pages | event-driven | same day | daily headline diff |
| Official organization pages and tear sheets | irregular | months behind leadership changes | weekly hash diff |

## Reusability

Every Navy activity inspected (NAVWAR, NAVSEA Enterprise, ONR/NRL) publishes its LRAE in the same
"Annex 25" template with the same column names, so one spreadsheet adapter and one
requirement-office alias table serve the whole Department. The registry records use the
`gov_procurement_sources` field names (`source_key`, `access_mode`, `refresh_cadence` as
`proposed_monitor_frequency`, `verification_status`, `last_verified_at`, `known_access_gaps` as
`access_restrictions`) so they can be loaded without renaming.
