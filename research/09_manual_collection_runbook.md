# 09 - Manual collection runbook: how each source was worked by hand, and what to automate

Written 2026-09-17. The point of this document is that a reviewer can repeat every step by hand,
confirm the sources are the right ones, and then see exactly what a monitor would do instead.
Every step here was actually performed once for the pilot; the results are the hashed rows in
`documents_manifest.jsonl`.

## In plain terms

Six sources cover the life of a Navy requirement. Three are spreadsheets or tables you download
and filter (the NAVWAR forecast, the Comptroller budget tables, the SAM.gov daily extract). Two are
APIs you query by office code or contract number (FPDS, USAspending). One is a set of web pages
you read (organization pages, SAM.gov notices, DVIDS releases). Doing the whole cycle by hand for
one office takes about a working day; a monitor turns it into a nightly diff.

## Access before anything else

The Navy and DoD web hosts refuse non-US addresses. From India this is true with and without
Cloudflare WARP. Three ways in, in order: the Wayback Machine for dated copies of pages and files;
a US-hosted browser (Browserbase, tool `research/tools/browserbase_fetch.py`) for live pages; a
US network or a colleague in the US for `secnav.navy.mil`, which refuses even the hosted browser.
FPDS, USAspending, govinfo, SAM.gov and DVIDS are open from anywhere.

## Source by source

### A. NAVWAR Long-Range Acquisition Estimate (the forecast spreadsheet)

Manual steps performed:
1. Open the NAVWAR Small Business Programs page (live page needs the US browser; the archived
   copy of 2026-01-08 was used) and download the LRAE file. June 2025 release:
   `NAVWAR HQCA-2025-A-037 Long Range Acquisition Estimate JUN 2025.xlsx` (about 186 KB).
2. Open the single sheet `LRAE Annex 25`. Header is on Excel row 8; data rows run from row 9 to
   the end of the sheet.
3. Filter `Associated Program or Requirement Office` on the office codes of interest
   (`PMW-160`, `PMW/A-170`, `PMA/PMW-101`, ... ; 144 rows for PEO C4I offices).
4. For each row record: title, value range, method, contract type, `Contracting Office UIC`,
   solicitation FY/quarter, award FY/quarter, `Follow-on or New`, `Existing Contract Number`,
   `Incumbent Contractor`, contracting POC name and email, `PID Number`.
5. Look up each `Existing Contract Number` in FPDS (step D) to see the incumbent's period of
   performance and description.
Time: about two hours for the PEO C4I subset. Pitfalls: codes are hyphenated here and spaced
elsewhere; some rows list an IDV and an order concatenated; many quarters are `TBD`.
What the monitor does: monthly check of the download link (weekly in May-July and December);
parse rows by `PID Number`; alert on new rows, removed rows, or changes in office, value range,
quarters, method, existing contract or incumbent.

Reproducible package: this cycle is now scripted. `python research/tools/lrae_package.py build`
reads the saved spreadsheet bytes (hash in `documents_manifest.jsonl`) plus the saved FPDS and
SAM.gov lookups and regenerates `datapack/lrae_navwar_2025-06/` without touching the network:
`rows_raw.csv` (every row, original strings, sheet and Excel row number), `rows_classified.csv`
(one decision per row: included, excluded, duplicate, unresolved, with the reason and the
normalized office next to the original code), `joins.csv` (one line per join attempt from a
forecast row to office, existing contract, notice and contact, each labelled explicit or
inferred, unmatched rows kept), `reconciliation.md` (counts that add up to the raw count, the
unresolved codes, the possible duplicates, the release gap) and `layers/` (the same rows shaped
as needs, requirements, funding observations, procurement references and evidence).
`SOURCE.json` holds the source hash and the hash of every output; running the build twice gives
identical files. `collect` fetches any lookup the joins still need and records it in the
manifest first, so the build stays offline. `tests/test_lrae_datapack.py` checks the counts,
the office joins and the regeneration.

### B. Budget tables (what the Department asked for)

Manual steps performed:
1. DoD Comptroller "Budget Materials" page for the fiscal year (US browser required). Download
   `p1_display.xlsx` (procurement lines) and `r1_display.xlsx` (RDT&E program elements).
2. In P-1: filter `Account` = `1810N`, `Budget Activity` = `02`, `Cost Type Title` = `Weapon
   System Cost`; 55 lines. In R-1: filter `Organization` = `N` and search titles for the office's
   programs (Afloat Networks, Information Systems Security Program, Command and Control Systems).
3. Read FY2025 actual, FY2026 enacted and FY2027 request per line; note the related program
   element on the line's P-40 exhibit (for CANES: line item 2915, PE 0303138N).
4. For the narrative that names programs and milestones, the Department of the Navy books
   (`OPN_BA2_Book.pdf`, `RDTEN_BA7-8_Book.pdf`) from `secnav.navy.mil/fmc` are needed; only the
   OPN book and the Highlights book could be downloaded (resumable direct download succeeded
   twice, failed the rest of the time).
Time: one hour for the tables; the 932-page OPN book needs a script to find exhibits by line item.
What the monitor does: annual pull at the President's Budget release, monthly re-check for
amended books, alert when a tracked line or PE moves beyond a threshold against the prior enacted.

### C. SAM.gov notices

Manual steps performed:
1. Daily extract: the SAM.gov data-services listing shows `ContractOpportunitiesFullCSV.csv`
   (241 MB, range requests supported; it holds current notices, about 84,500 rows, not history).
   Filter `AAC Code` in (`N00039`, `N66001`, `N65236`); 535 notices on 2026-09-16.
2. For a solicitation number from FPDS or the LRAE, search SAM.gov's site API
   (`/api/prod/sgs/v1/search/?index=opp&q=<number>&is_active=false`, header
   `Accept: application/hal+json`), then open the notice detail
   (`/api/prod/opps/v2/opportunities/<id>?api_key=null`). The first sentence of the description
   names the requiring office in almost every NAVWAR notice. No key is needed. The documented
   public API host (api.sam.gov) did not answer from any network tried.
3. Attachments: the detail's resource list for 2026 NAVWAR notices holds only PIEE links; the
   statement of work is behind the PIEE login.
4. Older years: yearly archive files (`FYxxxx_archived_opportunities.csv`, about 1.1 GB each)
   in the same data service. FY2025 was pulled in 73 parallel byte ranges in about four minutes:
   399,820 rows, 666 for the NAVWAR family, which supplied the first-notice dates for the
   MIDS-LVT, RSNF and ADNS recompetes (posted 2024-11 to 2025-06).
Time: minutes per solicitation number; an hour for the extract filter.
What the monitor does: nightly extract diff by notice id and modified date; site-API lookup for
every solicitation number that appears in FPDS or the LRAE; flag notices whose text names an
office that differs from the LRAE row.

### D. FPDS awards (who signed, who paid, what it says)

Manual steps performed:
1. Query the public ATOM feed by contracting office and date window, ten entries per page:
   `https://www.fpds.gov/ezsearch/FEEDS/ATOM?FEEDNAME=PUBLIC&q=CONTRACTING_OFFICE_ID:N00039+SIGNED_DATE:[2025/10/01,2026/09/16]&start=0`
   (escape the brackets when using curl, or pass `-g`).
2. For each entry record PIID, modification number, referenced IDV, `contractingOfficeID`,
   `fundingRequestingOfficeID` (with names), signed date, description, solicitation id, NAICS,
   PSC, vendor, obligated amount.
3. Query `PIID:<number>` to see the base award and all modifications of one contract.
4. Read the description for an office code or explicit ownership language; if absent, keep the
   solicitation id for step C and the contract number for step A.
Time: about a second per page; 180 actions scanned in ten minutes; the host resets connections
after a few hundred pages, so scans run in date windows.
What the monitor does: daily pull per contracting office since the last signed date (DoD actions
appear about 90 days after signature); attribution pass on every new base award; alerts for
options, ceiling increases and extensions on watched contracts.

### E. USAspending (ceilings, obligations, periods of performance)

Manual steps performed:
1. Keyword search (`spending_by_award`) for an office code such as `PMW 160`.
2. Award detail by generated id, e.g.
   `https://api.usaspending.gov/api/v2/awards/CONT_AWD_N0003922F3000_9700_N0017819D7264_9700/`:
   description, awarding and funding office names, period of performance, base and all options,
   total obligation, parent IDV.
Time: seconds per award. What the monitor does: weekly refresh of watched awards; alert when the
period-of-performance end is within twelve months and no follow-on has been observed.

### F. Organization pages, tear sheets, releases (who owns what, who leads it)

Manual steps performed:
1. PEO C4I program-office page and tear sheets: archived copies (captures April 2026 and
   earlier) are the last available; the live domain now serves the PAE Mission Systems site.
   Record office code, name, programs listed, program manager and date printed on the sheet.
2. NAVWAR pages (Work-With-Us, About, Small Business) through the US browser or archive: read
   the structure statement and the footer navigation, and date every statement.
3. DVIDS unit pages for NAVWAR and PEO C4I: read releases for change-of-command, industry
   events and reorganization news; DVIDS is open from anywhere.
4. Reorganization releases (navy.mil, PAE domains, DVIDS): record what moved and the date.
Time: half a day for the pilot portfolio. What the monitor does: weekly hash diff of each page
and file; daily headline diff on DVIDS; a change opens a review item, and approved changes become
dated edges in the organization graph rather than overwrites.

### G. Congressional documents

Manual steps performed:
1. govinfo search (`POST api.govinfo.gov/search`, query `"CANES" "Other Procurement, Navy"
   collection:(CREC OR CRPT)`) lists the committee reports and explanatory statements that carry
   the Navy procurement tables; the newest for FY2027 is H. Rept. 119-715 (2026-06-26).
2. Fetch the package's HTML text (`/packages/CRPT-119hrpt715/htm`); the Other Procurement, Navy
   table appears as flat text between the "OTHER PROCUREMENT, NAVY" and "PROCUREMENT, MARINE
   CORPS" headings, one line per row: line number, title, request, recommendation, change, and a
   committee note when the amounts differ.
3. Read the tracked lines: on 2026-06-26 the House changed CANES (+50,000, "maritime
   containerized secure units") and RADIAC (-14,952, contract award delays); the other sixteen
   tracked lines equal the request.
4. The RDT&E program-element table did not surface in the HTML text; use the PDF rendering.
Time: half an hour once the right package is known. What the monitor does: daily poll for new
packages on the tracked bills (House report, Senate report, conference or explanatory statement,
enacted act); extract the funding-table rows for the tracked lines and PEs; alert on any change
against the request, with the committee note.

## Verification checklist for the reviewer

| Check | Where |
| --- | --- |
| The forecast spreadsheet is the current release and the office column is being read | `source_registry.json` row `navwar_lrae_annex25`; manifest row with hash |
| The office inventory matches what the Navy publishes | `organization_seed.json` nodes `pmw:*`, each with the page or tear sheet cited |
| Contracting versus requiring office is never confused | `04_attribution_process_and_examples.md`, EX09 (NAVSEA office through NAVWAR HQ) |
| SAM.gov notice text is being read for office names | EX12, EX13, EX14, EX15, EX16 (upgraded from the notices) |
| Budget lines are tied to offices only by program name, and say so | `05_early_signals_and_backtests.md` section 1a |
| Sources that could not be reached are listed, not skipped | `manual_pdf_requests.json`; registry rows marked blocked or restricted |
| The steps above reproduce the numbers in the documents | manifest hashes; `tests/test_research_artifacts.py` |

## From manual to monitor

Each section above ends with what the monitor does; `06_continuous_monitor_design.md` gives the
schedules and alert formats. Tooling candidates for the page-diff part: the fetch-and-record
helper already here on a schedule, a hosted change-monitor service (context.dev or similar) for
the organization pages and download links, and the US-hosted browser for the geo-blocked hosts.
The spreadsheet and API parts need no third-party service.
