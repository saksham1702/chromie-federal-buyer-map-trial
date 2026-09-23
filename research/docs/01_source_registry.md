# 01 - Source registry: what each source proves, how it is reached, how often to look

The machine-readable registry is `research/sources/source_registry.json` (one record per source, field names
chosen to load into Chromie's `gov_procurement_sources`). The table below summarizes that file;
the prose explains how the sources fit together. Every `verified` row has an inspected example
whose hash is in `research/sources/documents_manifest.jsonl`; rows marked `blocked` or `restricted` say why.

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
| Organization and ownership | PEO C4I official site (peoc4i.navy.mil) | webpage | verified | 11 program offices listed with tear-sheet links; footer 'One NAVWAR ... PEO C4I & Space, PEO Digital, PEO MLB' (wayback) | weekly hash diff of Program-Offices, Leadership, Contact and each tear sheet |
| Organization and ownership | NAVWAR official site (navwar.navy.mil) | webpage | verified | 'NAVWAR HQ ... procures the IW systems sought by PEO C4I, PEO MLB and PEO Digital'; NIWCs 'the technical heart' (wayback) | weekly hash diff of About, Work-With-Us, Small-Business-Programs |
| Organization and ownership | DVIDS (Defense Visual Information Distribution Service) unit pages and releases | webpage | verified | change of command: Castillejo to PMW 150 relieving Jolie; Andalis to PMW 760 (direct) | daily fetch of unit pages, diff headline list |
| Organization and ownership | Department of the Navy PAE press releases (navy.mil, paemaritime.navy.mil, DVIDS mirror) | webpage | verified | live navy.mil release: PAEs 'will have direct authority not only for program offices, but also over associated ...' (browserbase) | weekly check of PAE domains and DVIDS for new releases |
| Organization and ownership | NAVSEA Small Business Partnerships documents (org chart, Deputy Program Manager roster) | pdf | verified | two-page table: title, phone, code, description (PMS 396, PMS 397, PMS 450, ...) (wayback) | quarterly |
| Organization and ownership | Federal Register API | api | verified | query 'Naval Information Warfare' returns dated notices with agencies and PDF links (direct) | weekly query per organization name |
| Agency intent | Department of the Navy budget materials (FMB): justification books by appropriation | pdf | verified | 37 PDF links: RDTEN_BA1-3 ... BA7-8, OPN_BA1 ... BA5-8, OMN, WPN, APN, SCN, Highlights_Book, DON_Budget_Card (direct) | annual at budget release, then monthly checks for amended books |
| Agency intent | DoD Comptroller budget materials | spreadsheet | verified | p1_display.xlsx: 1,138 rows; 55 OPN BA2 lines incl. 2915 CANES 439,977 / 534,324 / 493,046 ($K) (browserbase) | annual |
| Agency intent | Federal IT Dashboard / IT Collect public API | api | verified | landing page reachable; detailed pull handled by the existing prod ingest (direct) | weekly (existing prod job) |
| Congressional decisions | govinfo API (committee reports, explanatory statements, enacted laws, bills) | api | verified | H. Rept. 119-715 (DoD Appropriations Act, 2027) HTML text; OPN table rows read as line, title, request, recommendation (direct) | daily poll of new CRPT/CREC/PLAW packages matching defense keywords |
| Congressional decisions | congress.gov API (bills, amendments, committee reports, hearings) | api | verified | bill endpoint responds with DEMO_KEY (direct) | daily |
| Planned requirements | NAVWAR Long-Range Acquisition Estimate (LRAE Annex 25) | spreadsheet | verified | 833 rows; 144 rows name a PEO program office, all contracted by N00039; 200 rows carry an existing contract number (wayback) | monthly check for a new release; diff rows by PID number |
| Planned requirements | NAVSEA Enterprise Long-Range Acquisition Estimate | spreadsheet | verified | sheet 'Annex 25 Template'; 228 distinct requirement offices; N00024 NAVSEA HQ is the top contracting UIC (wayback) | monthly |
| Planned requirements | ONR and NRL Long-Range Acquisition Estimate | spreadsheet | verified | two data sheets plus validation lists; header on row 7 (direct) | monthly |
| Planned requirements | PEO C4I industry engagement (AFCEA WEST events, Industry Intake Form) via DVIDS | webpage | verified | 'third annual engagement event at AFCEA WEST 2026, featuring all 11 program offices' (direct) | daily via DVIDS unit page |
| Planned requirements | NAVWAR Commercial Solutions Openings | webpage | verified | page links a SAM notice and the PIEE vendor instructions (wayback) | weekly |
| Planned requirements | SBIR/STTR topics (sbir.gov; DoD SBIR/STTR portal) | webpage | verified | search page reachable (direct) | per cycle (three times a year) |
| Active acquisition | SAM.gov Contract Opportunities public data extract (daily CSV of current notices) | export | verified | 241,486,025 bytes; 47 columns incl. AAC Code, Sol#, Type, PostedDate, AwardNumber; 535 NAVWAR-family notices (direct) | nightly download and diff on notice id + modified date |
| Active acquisition | PIEE Solicitation Module (replaced NAVWAR eCommerce) | manual | restricted | official access-instructions PDF (TLS chain is DoD PKI; fetched with verification off and recorded) (direct) | not automated; rely on SAM synopses |
| Active acquisition | SeaPort-NxG portal (Navy services vehicle) | manual | blocked | connection failed (HTTP 000) | not automated; awards tracked through FPDS referenced IDVs |
| Awards and execution | FPDS ATOM public feed | api | verified | 10 actions; funding offices N00039 and N00024 (NAVSEA HQ); descriptions such as 'LTS/CLTS PRODUCTION AND SUSTA...' (direct) | daily pull per contracting office since last signed date |
| Awards and execution | USAspending API v2 | api | verified | description names 'PROGRAM MANAGER, WARFARE TACTICAL NETWORKS (PMW 160)'; PoP 2021-10-27 to 2026-10-26 (direct) | weekly refresh of watched awards; nightly keyword search for office codes |
| Awards and execution | DoD (Department of War) daily contract announcements (RSS + article pages) | api | verified | 10 items: 'Contracts for Sept. 15, 2026' ... with war.gov article links and pubDate (direct) | daily RSS poll; fetch each day's article through the fallback path |
| Oversight | Oversight.gov federal report listing (inspector general reports) | webpage | verified | listing 'Navy': 50 rows, all with Department of War or the Navy as the agency reviewed; report pages carry date, OIG, report number, questioned costs and the PDF (direct) | weekly: the two listing queries, new report pages and files |
| Oversight | GAO reports (gao.gov products; feed for the latest 25, Exa discovery for older ones) | webpage | verified | Navy And Coast Guard Shipbuilding product page with the highlights as HTML (browserbase) | weekly feed poll; monthly search discovery |
| Leaders' words | U.S. Navy Press Office speech and testimony archives (navy.mil) | webpage | verified | first archive page: 20 CNO speeches June to August 2026 with datelines; article pages carry the full remarks (browserbase) | weekly: first archive page of each list, new articles |
| Leaders' words | House Committee Repository (docs.house.gov) Armed Services and Appropriations hearings | webpage | verified | Navy FY2027 Seapower budget hearing 2026-05-20: three witnesses, joint witness statement PDF (direct) | weekly: AS00 and AP00 feeds, new hearings naming the department |
| Leaders' words | Conference and event pages naming Navy officials (Exa discovery, organizer or trade page) | webpage | verified | Sea-Air-Space 2026 organizer page: CNO keynote at the Sea Services Luncheon (direct) | monthly discovery; known pages re-fetched before each major event |
| Awards and execution | GAO bid protest decisions and docket | webpage | blocked | HTTP 403; Chromie's existing pursuit-intelligence runner already covers GAO | weekly |
| Organization and ownership | Internet Archive Wayback Machine (dated copies of official pages) | api | verified | 2026-05-19 capture shows the PAE Mission Systems front page (wayback) | on demand |
| Active acquisition | SAM.gov Contract Opportunities archived yearly extracts (FYxxxx_archived_opportunities.csv) | export | verified | FY2025 file: 1,159,352,018 bytes, 399,820 rows, 666 NAVWAR-family notices (posted 2024-10 to 2025-09) (direct) | quarterly re-pull of the two most recent fiscal years |
| Active acquisition | SAM.gov site API (opps v2/v3 and sgs search, keyless) | api | verified | NILE ISS 6 RFI detail with description body naming PEO C4I / PMW 150 (direct) | on demand per solicitation number surfaced by FPDS or the LRAE |
| Organization and ownership | PEO Digital official site (peodigital.navy.mil) | webpage | verified | 'IMPORTANT NOTICE: On May 11, 2026 ... PEO Digital is now part of the PAE Mission Systems' (browserbase) | weekly hash diff |
| Organization and ownership | DON CIO CHIPS magazine (official DoN IT publication) | webpage | verified | 'On May 13, 2020, the Deputy Assistant Secretary of the Navy for Information Warfare and Enterprise ...' (browserbase) | monthly |
| Organization and ownership | PAE Mission Systems official site (missionsystems.navy.mil; also served at peoc4i.navy.mil) | webpage | verified | Industry page: five capability portfolios and the Learn / Introduce / Propose intake process (browserbase) | weekly hash diff; alert when About, Leadership or a portfolio page appears |
| Organization and ownership | PEO MLB official site (peomlb.navy.mil) | webpage | verified | 'PEO MLB is now part of the PAE Mission Systems'; navigation: About, Portfolio, Industry Engagement, Strategic (browserbase) | weekly hash diff |

## How the sources connect

Three kinds of join carry a requirement across stages (details and pitfalls in
`research/docs/03_data_connection_map.md`):

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
| Open, direct | USAspending API, FPDS ATOM, SAM public extract listing, govinfo, congress.gov, Federal Register, DVIDS, paemaritime.navy.mil, ONR, IT Dashboard, sbir.gov, PIEE landing, DoD contracts RSS, oversight.gov (listing, report pages, files), the GAO report feed, docs.house.gov (feeds, hearing pages, statements), most conference organizer pages | no key or a free api.data.gov key; gao.gov product pages, navy.mil archives and the Senate committee sites are in the geographic block below |
| Geographic block (HTTP 403 to any client from a non-US address) | navwar, peoc4i, navsea, navair, niwc, navy.mil, war.gov, comptroller, gao.gov, peodigital | Wayback captures for history; context.dev (a United States address) for live pages, Browserbase (US egress) for files |
| Firewall resets | secnav.navy.mil (budget library, OSBP) | Wayback and Browserbase are refused; the Comptroller's P-1/R-1 tables cover the line amounts |
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
