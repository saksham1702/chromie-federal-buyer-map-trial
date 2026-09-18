# Navy Acquisition Sources Map

## 1. Purpose

This file is a human-readable map of the Navy and federal acquisition sources used in this
research package. It states why each source is useful, what a source cannot establish by itself,
and how sources connect for identity, forecasts, notices, awards, and funding.

Use it as a navigation and source-of-truth guide when adding research or choosing what to
inspect next. It does not replace the structured authorities that hold the machine-readable
facts and provenance:

- `research/source_registry.json` — one record per source (fields, coverage, verification)
- `research/documents_manifest.jsonl` — retrieved bytes (URL, method, status, hash)
- `research/03_data_connection_map.md` — identifiers, joins, and where the chain breaks
- `research/09_manual_collection_runbook.md` — how to fetch and verify a source by hand
- `research/organization_seed.json` — dated organization and relationship claims
- `research/org_code_families.json` — how office and UIC codes are classified

## 2. How to Use and Update This File

1. Add a source here only after it has been inspected and represented in
   `research/source_registry.json`.
2. Do not mark a source verified here unless the registry and
   `research/documents_manifest.jsonl` support that status.
3. Keep what a source states separate from what we infer from it.
4. Record access restrictions and unresolved gaps; do not hide them.
5. When machine-readable facts change, update the structured authority first, then this
   summary.
6. Do not use this file as the only provenance record for a research claim.

## 3. Navy Acquisition Source Landscape

No single public system answers the buyer-map question for this pilot: who owns a requirement,
who buys it, what funding supports it, and what already happened on the street. The package
therefore uses several source families, each for a different stage of the same requirement.

**Organization and identity.** Official sites, releases, and dated documents name commands,
PEOs/PAEs, program offices, and people in roles. They answer “who is this organization, and
what did a source say about structure or leadership on a given date?” They do not, by
themselves, show contracts, notices, or budget amounts, and they drift during reorganization.

**Budget and agency intent.** Comptroller tables and Department of the Navy justification
materials state requested (and related) funding by appropriation, line item, and program
element. They answer “what did the Department ask to fund?” They do not publish a public map
from a budget line to a contract or, usually, to a PMW code.

**Planned requirements / forecasts.** Long-Range Acquisition Estimates and related industry
materials name upcoming buys with requirement-office codes, timing, and often an incumbent
contract. They answer “what does an office say it plans to buy?” They are estimates with
disclaimers; PIDs are internal; slips between releases are common.

**Active opportunities.** SAM.gov extracts, site APIs, and related acquisition pathways show
notices and solicitation numbers. They answer “is there a public notice yet?” Full solicitation
files often sit behind PIEE or vehicle portals that this package cannot automate.

**Awards and execution.** FPDS and USAspending record signed actions, obligations, contracting
and funding offices, and PIIDs. They answer “what was awarded, by whom, under which vehicle?”
Program-office ownership often appears only as free text in the description, and DoD FPDS rows
publish with a lag.

**Congressional action.** Committee reports and related govinfo material show marks, adds, and
cuts against budget lines. They answer “what did Congress change relative to the request?”
They do not create awards, and PE-level tables may need PDF extraction when HTML is incomplete.

**Historical / archive support.** Wayback captures and yearly SAM archives preserve what a page
or notice set looked like on a past date. They answer “what was available by the cutoff?” They
cannot invent pages the crawler never saw or years not yet pulled into the manifest.

```
Organization / identity  (who owns what, dated)
        |
Budget / agency intent   (request by BLI / PE)
        |                 (program name: inference only)
Planned forecast         (LRAE: office code, PID, incumbent)
        |
Active opportunity       (SAM: solicitation / notice)
        |
Award / execution        (FPDS / USAspending: PIID, DoDAAC, IDV)
        ^
Congressional marks -----+  (same BLI / PE as budget tables)
        ^
Archives / Wayback ------+  (dated copies for cutoffs and vanished pages)
```

## 4. Source-by-Source Reference

### Organization, Identity, and Leadership Sources

#### PEO C4I official site

`source_key: navy_peoc4i_site`

**Why we use it:**  
Primary public inventory of the eleven PEO C4I program offices, tear sheets, and dated
leadership statements that feed the organization graph and contact observations.

**What it can establish:**  
Office codes and names (PMW/PMA); mission and top programs as printed; who a tear sheet or
leadership page named in a role on the observation date; industry intake pointers on that site.

**What it cannot establish by itself:**  
Contracts or notices by office; budget lines; that a pre-reorganization capture is still the
current parent structure. Live peoc4i.navy.mil now serves PAE Mission Systems content; older
Wayback captures are historical, not automatically current.

**Useful identifiers / joins:**  
PMW/PMA office codes and names; program names on tear sheets; program manager names as of the
tear-sheet or page date.

**Access / maintenance notes:**  
Verified in the registry. Non-US hosts often get Akamai 403; inspected via Wayback and
Browserbase. Registry proposes weekly hash diffs of Program-Offices, Leadership, Contact, and
tear-sheet URLs; tear sheets update irregularly (roughly annual).

#### NAVWAR official site

`source_key: navy_navwar_site`

**Why we use it:**  
States how NAVWAR describes itself (HQ, NIWCs, relationship to PEOs/PAEs), where industry is
sent to buy, and where the LRAE and small-business links appear.

**What it can establish:**  
Dated structure and contracting-pathway statements (for example HQ procuring systems sought by
named PEOs); CSO and related acquisition pointers; OSBP contact and LRAE download links when
published on the page.

**What it cannot establish by itself:**  
Program-office-level detail; awards; that a contracting pathway equals requirement ownership.

**Useful identifiers / joins:**  
Organization names in navigation and prose; links into SAM, PIEE, and the LRAE file.

**Access / maintenance notes:**  
Verified. Often Wayback when direct fetch is blocked or DNS fails; Browserbase used for some
live About captures. Registry proposes weekly hash diffs of About, Work-With-Us, and
Small-Business-Programs, plus a monthly check for a new LRAE link.

#### DVIDS Navy unit releases

`source_key: dvids_navy_units`

**Why we use it:**  
Dated official releases for leadership changes, industry events, and reorganization
announcements that other pages may not timestamp clearly.

**What it can establish:**  
What a named release states on its publication date (for example a change of command naming
offices and people; PAE Mission Systems stand-up text when mirrored here).

**What it cannot establish by itself:**  
A complete org chart; contract identifiers; budget figures; anything the release does not say.

**Useful identifiers / joins:**  
Release date; office and program manager names in body text; unit tags.

**Access / maintenance notes:**  
Verified; direct fetch worked in inspected examples. Event-driven publication. Registry proposes
daily unit-page headline diffs. No unit-filtered RSS noted in the registry.

#### Department of the Navy PAE press releases

`source_key: navy_pae_press`

**Why we use it:**  
Authoritative public wording for when Portfolio Acquisition Executives were established and
which organizations were named in the consolidation.

**What it can establish:**  
Release date; PAE names and interim executives as stated; that mission systems elements of
listed organizations were pulled together (wording as published); broader Warfighting
Acquisition System framing when the release includes it.

**What it cannot establish by itself:**  
Which individual offices or functions moved; effective dates for individual PMWs; a full
post-reorg org chart.

**Useful identifiers / joins:**  
Organization names listed in the release; release date as observation date.

**Access / maintenance notes:**  
Verified. navy.mil often needs Browserbase from non-US networks; paemaritime.navy.mil and DVIDS
mirrors are more open. Event-driven; registry proposes weekly checks of PAE domains and DVIDS.

#### NAVSEA Small Business Partnerships organization documents

`source_key: navsea_small_business_org_docs`

**Why we use it:**  
When NAVSEA publishes codes and contact tables, they extend identity work beyond the NAVWAR
pilot (for example PMS codes adjacent to shared contracting).

**What it can establish:**  
Office codes, titles, and phone listings as printed in that PDF on its stated date.

**What it cannot establish by itself:**  
NAVWAR program offices; that one roster is a complete current NAVSEA hierarchy; live page
locations after Small-Business-Partnerships URLs went 404.

**Useful identifiers / joins:**  
PMS/IWS (and similar) office codes; names and phones as printed.

**Access / maintenance notes:**  
Verified via Wayback captures of the PDFs. Live partnership pages returned 404 on 2026-09-16;
current file location must be re-found. Roughly annual documents; registry proposes quarterly
checks.

#### Federal Register API

`source_key: federal_register`

**Why we use it:**  
Formal, dated Federal Register notices that rename or otherwise officially notice Navy
organizations—distinct from day-to-day .mil marketing pages.

**What it can establish:**  
Publication date, document type, agencies, title/abstract, and PDF link for matching notices.

**What it cannot establish by itself:**  
Acquisition forecasts, SAM notices, or awards; routine program-office inventories.

**Useful identifiers / joins:**  
document_number; publication_date; agency names in the notice.

**Access / maintenance notes:**  
Verified; open API; daily publication stream. Registry proposes weekly queries per organization
name. No access restriction noted in the registry.

#### PEO Digital official site

`source_key: peo_digital_site`

**Why we use it:**  
PEO Digital’s own consolidation notice and mission/offering pages for the Digital portfolio
under the PAE transition.

**What it can establish:**  
That the site states PEO Digital is part of PAE Mission Systems (as of the captured notice);
described solution or mission areas in the site’s own words.

**What it cannot establish by itself:**  
A PMW-coded office inventory. About/Offerings/Industry describe solution types and name no
offices; LRAE front-office codes remain the public handle in this package.

**Useful identifiers / joins:**  
Organization name “PEO Digital”; consolidation notice date as observed; solution-area labels as
text only (not office codes).

**Access / maintenance notes:**  
Verified via Browserbase (Akamai 403 otherwise). Irregular updates; registry proposes weekly
hash diffs.

#### DON CIO CHIPS magazine

`source_key: don_cio_chips`

**Why we use it:**  
Official DoN IT journalism with dated narrative of the PEO EIS split into PEO Digital and PEO
MLB (2020) and related IT acquisition context.

**What it can establish:**  
Dated organizational change statements quoted or stated in the article (for example
disestablishment and stand-up dates as the article gives them).

**What it cannot establish by itself:**  
Current office rosters; acquisitions; that historical context equals today’s inventory.

**Useful identifiers / joins:**  
Article date; organization names as written.

**Access / maintenance notes:**  
Verified via Browserbase; direct non-US fetches often get WAF stubs. Continuous publication;
registry proposes monthly checks.

#### PAE Mission Systems official site

`source_key: pae_mission_systems_site`

**Why we use it:**  
Current portfolio-level face of the consolidation (also served from former peoc4i.navy.mil
URLs) and the published industry intake path.

**What it can establish:**  
Five named capability portfolios as listed; Learn / Introduce / Propose-style engagement
routing; mission/vision text on the captured pages.

**What it cannot establish by itself:**  
Which former program offices sit in which portfolio (not published); leadership below the
interim PAE when those pages are missing or 404.

**Useful identifiers / joins:**  
Capability portfolio names as published; links out to SAM, SeaPort-NxG, SBIR/STTR when present.

**Access / maintenance notes:**  
Verified via Browserbase. Site still under construction in the registry sense. Registry proposes
weekly hash diffs and alerts when About, Leadership, or portfolio pages appear.

#### PEO MLB official site

`source_key: peo_mlb_site`

**Why we use it:**  
PEO MLB’s own consolidation statement and portfolio prose for manpower, logistics, and business
systems under the PAE transition.

**What it can establish:**  
That the site states PEO MLB is part of PAE Mission Systems; portfolio description in the
site’s words.

**What it cannot establish by itself:**  
A PMW-coded office inventory. Portfolio pages describe defense business systems in prose and
name no offices; LRAE codes such as Pf00* remain the public handle in this package.

**Useful identifiers / joins:**  
Organization name “PEO MLB”; consolidation notice as observed; portfolio labels as text only.

**Access / maintenance notes:**  
Verified via Browserbase (Akamai 403 otherwise). Irregular updates; registry proposes weekly
hash diffs.

### Budget, Agency Intent, and Congressional Sources

#### Department of the Navy budget justification books

`source_key: don_budget_justification_books`

**Why we use it:**  
FMB justification books are the Department’s narrative for what it asked Congress to fund.
Exhibit text can explain program purpose, requested activity, acquisition plans, and
year-to-year changes in ways the Comptroller line tables do not.

**What it can establish:**  
Requested (and related prior/current-year) amounts by appropriation, budget activity, program
element or line item, and project when the exhibit states them; program narratives that name
systems and occasionally offices.

**What it cannot establish by itself:**  
A solicitation or award; enacted funding; which contract a line funds; or the exact program
office that will own a future procurement. Program-title similarity to a PMW is inference, not
a public join.

**Useful identifiers / joins:**  
Appropriation; budget activity; program element / line item; project; fiscal-year amount
columns; program names in exhibit narrative (inference bridge only).

**Access / maintenance notes:**  
Registry verified the FY2027 materials page (37 PDF links). Host resets are common; some
narratives remain unretrieved. FY2027 OPN BA2 and Highlights books appear in the manifest;
RDT&E BA7-8 and FY2026 books stay in the T05 / `manual_pdf_requests.json` queue. Cadence:
annual at budget release, then monthly for amended books. Do not treat every target narrative
as collected.

#### DoD Comptroller budget materials

`source_key: dod_comptroller_budget_materials`

**Why we use it:**  
Structured P-1 / R-1 (and related) display tables give DoD-wide requested-budget identifiers
and fiscal-year columns in one place, so Navy procurement lines and RDT&E program elements can
be tracked without waiting on every DoN narrative PDF.

**What it can establish:**  
For each row: account/organization, budget activity, exhibit line number, budget line item
(BLI) or program element (PE), title, and fiscal-year columns as published (for FY2027 tables:
prior actual, enacted/spend-plan, and request by cost type). Useful for cross-checking DoN
books when those books are available.

**What it cannot establish by itself:**  
Office-level ownership; solicitations or awards; that a request equals enacted funding or
obligations. Keep identifiers distinct: BLI, PE, P-1/R-1 exhibit line number, program title,
and fiscal year are different fields. Example already in this package: OPN CANES is BLI 2915
and appears as P-1 line 64—the line number is not the BLI.

**Useful identifiers / joins:**  
P-1: budget line item, P-1 line number, title, fiscal-year columns. R-1: program element, R-1
line number, title, fiscal-year columns. Program title is the only public bridge toward an
office (inference).

**Access / maintenance notes:**  
Verified via Browserbase (403 from non-US direct). FY2027 `p1_display.xlsx` /
`r1_display.xlsx` are in the manifest. Site redirects to comptroller.war.gov. Proposed monitor:
annual.

#### Federal IT Dashboard / IT Collect

`source_key: it_dashboard_it_collect`

**Why we use it:**  
Public IT-investment reporting can, in principle, show planned DME/O&M funding and linked
contract PIIDs for Navy IT investments already covered by the platform’s agency IT portfolio
ingest.

**What it can establish:**  
Only what a detailed IT Collect pull would return (UII, investment title, agency, funding by
year, linked PIIDs, CIO rating). This package verified the landing page; a detailed Navy pull
was deferred to the existing production ingest.

**What it cannot establish by itself:**  
Weapon-system C4I procurement lines outside the IT portfolio; buyer-map office ownership for
non-IT lines.

**Useful identifiers / joins:**  
UII; investment title; agency code; linked contract PIIDs (when present in a full pull).

**Access / maintenance notes:**  
Verified at landing-page level only. API key required for IT Collect (already used in prod).
Registry proposes weekly via the existing job. Do not treat this source as deeply integrated in
the Navy pilot evidence set.

#### Navy posture statements and acquisition testimony

`source_key: navy_posture_testimony`

**Why we use it:**  
Conceptually, posture hearings and witness statements can state senior-leader priorities and
gaps that later appear as budget or acquisition themes.

**What it can establish:**  
Nothing validated in this package yet. The registry lists hearing date, committee, and witness
statement PDFs as the intended fields if sampled.

**What it cannot establish by itself:**  
Office-level acquisitions; funding tables; that testimony equals a funded line or a planned
buy.

**Useful identifiers / joins:**  
Hearing date; committee; witness/statement identifiers—once inspected.

**Access / maintenance notes:**  
**not_inspected.** No inspected example URL or hash. Registry proposes weekly checks during
posture season (typically Feb–May). Treat as a candidate source only until a Navy acquisition
hearing is sampled and recorded.

#### govinfo API

`source_key: govinfo_api`

**Why we use it:**  
Official GPO packages for committee reports, explanatory statements, bills, and laws carry the
congressional funding tables and directive language that mark requested lines up or down.

**What it can establish:**  
Package metadata (`packageId`, collection, `dateIssued`, title, download links) and, where
extracted, funding-table rows with line/PE, request vs recommended amounts, and committee
notes. Inspected example: H. Rept. 119-715 HTML yielded OPN table rows (including a House
CANES add); that is a committee recommendation, not final enacted funding.

**What it cannot establish by itself:**  
Contract-level effects; that a House or Senate mark is the enacted amount; RDT&E PE marks when
only HTML was parsed. T05 item 4 still requires PDF extraction of the FY2027 House report’s
RDT&E PE table—the PE table is not fully captured.

**Useful identifiers / joins:**  
`packageId`; collection (CRPT, CREC, PLAW, BILLS); funding-table line item / PE and fiscal-year
amounts as printed.

**Access / maintenance notes:**  
Verified; open with api.data.gov key (DEMO_KEY rate-limited). HTML granules parse OPN-style
tables as flat text; RDT&E PE table needs the PDF rendering. Daily poll of new defense
packages proposed.

#### congress.gov API

`source_key: congress_gov_api`

**Why we use it:**  
Legislative and report metadata for discovering which defense authorization and appropriations
bills, amendments, reports, and hearings exist and when they moved—so govinfo packages and
hearing documents can be fetched on purpose.

**What it can establish:**  
Bill numbers, actions with dates, committee report citations, and text-version pointers.
Endpoint sampling with DEMO_KEY succeeded.

**What it cannot establish by itself:**  
Line-level funding tables (use govinfo for those). Metadata that a report exists is not the
same as the substantive PE/line table inside the document.

**Useful identifiers / joins:**  
Bill number; action dates; committee report citations that point to govinfo packages.

**Access / maintenance notes:**  
Verified; api.data.gov key. Low difficulty for status JSON; report body via govinfo. Proposed
monitor: daily.

#### How these sources complement one another

Comptroller P-1/R-1 tables supply structured requested-budget identifiers and amounts. DoN
justification books add exhibit narrative where those PDFs are actually in hand. Congressional
govinfo (and congress.gov discovery) show proposed committee or legislative changes against the
same lines and PEs. Together they can create early funding signals. None of them alone proves
that a specific solicitation or award will occur, and none publishes a public map from a budget
line to a contract or PMW code.

### Planned Requirements and Acquisition Forecasts

#### NAVWAR Long-Range Acquisition Estimate (LRAE Annex 25)

`source_key: navwar_lrae_annex25`

**Why we use it:**  
Central forecast for the NAVWAR pilot. Each row can connect a planned buy to a requirement /
program-office code and a contracting path before any public solicitation is active—often with
an incumbent contract already named.

**What it can establish:**  
As captured in the Annex 25 packages: PID (when present), requirement title/description,
requirement/program-office code string, contracting office UIC, anticipated total-value range,
procurement method / contract type / instrument, planned solicitation FY+quarter, planned award
FY+quarter, follow-on vs new, existing contract number, incumbent contractor name, and
contracting POC name/contact. Office codes normalize through `org_code_families.json` and the
organization alias table (PEO PMW/PMA, NIWC, HQ/front-office families are distinct).

**What it cannot establish by itself:**  
That the buy will occur as written or on the stated quarter; a budget line; a final solicitation
number; that the contracting UIC owns the mission requirement; or that the contracting POC is a
program-office member. Title similarity to a later notice is only a candidate join unless
another identifier (e.g. existing contract) links them. PID is internal to the LRAE activity and
is not globally resolvable in SAM/FPDS.

**Useful identifiers / joins:**  
`pid`; `office_code_string` → organization (via alias / code family); `contracting_office_uic`;
`existing_contract_number` → FPDS/USAspending PIID; incumbent name (name-only); title/timing/NAICS
as inferred notice matches only.

**Access / maintenance notes:**  
Verified via Wayback (host blocks automation). Dated packages under
`datapack/lrae_navwar_2023-06/`, `…_2024-06/`, and `…_2025-06/` support release diffs by PID when
both sides have one, otherwise by title and office (the 2024 release has no PID values). Registry
proposes monthly link checks (weekly in release seasons); monitor diffs on office, value range,
quarters, method, existing contract, or incumbent.

#### Department of the Navy OSBP LRAE index

`source_key: don_osbp_lrae_index`

**Why we use it:**  
Would list which Navy activities publish LRAEs and where to find them—discovery beyond the
NAVWAR pilot and a path to other components’ forecast files.

**What it can establish:**  
In principle: links to each activity’s LRAE. This package has not retrieved the page, so it
establishes nothing row-level here.

**What it cannot establish by itself:**  
Row-level forecasts; a complete Navy-wide forecast inventory in this repo.

**Useful identifiers / joins:**  
None captured yet (page not retrieved).

**Access / maintenance notes:**  
**blocked.** Multiple connection resets (and Browserbase timeout) recorded; queued for a US
network session in `manual_pdf_requests.json`. Proposed monitor: monthly, once reachable. Do not
treat the repo as having indexed all Navy LRAEs.

#### NAVSEA Enterprise Long-Range Acquisition Estimate

`source_key: navsea_lrae_annex25`

**Why we use it:**  
Same Annex 25 forecast pattern for NAVSEA enterprise requirements—useful for shared contracting
paths and for offices (e.g. PMS, IWS) that appear adjacent to the NAVWAR pilot.

**What it can establish:**  
Per the captured December 2025 enterprise spreadsheet (Wayback): Annex 25 columns including
requirement/office codes (228 distinct offices in the inspected note), contracting UICs (top
UIC N00024), titles/timing, and existing-contract / incumbent fields where filled. Does not mean
every warfare center has been separately mapped; the live enterprise page later 404’d and
navigation moved toward per-warfare-center forecast pages.

**What it cannot establish by itself:**  
NAVWAR rows; that an enterprise file is a complete current map of every warfare-center forecast;
execution of any planned buy.

**Useful identifiers / joins:**  
Requirement/office codes (PMS, IWS-x.0, warfare-center departments, etc., via code families);
contracting UIC; existing contract number; title and planned quarters.

**Access / maintenance notes:**  
Verified via Wayback capture of the enterprise xlsx; live Small-Business-Partnerships LRAE URL
returned 404 on 2026-09-16. Proposed monitor: monthly; re-find the file from current NAVSEA
navigation when needed.

#### ONR and NRL Long-Range Acquisition Estimate

`source_key: onr_lrae_annex25`

**Why we use it:**  
Broader Navy forecast example: ONR/NRL publish planned research procurements in the same Annex 25
family, showing the template is reusable outside NAVWAR/NAVSEA PEOs.

**What it can establish:**  
Planned research procurements above the activity’s published threshold, on separate ONR and NRL
sheets with Annex 25-style columns (header on row 7 in the inspected file).

**What it cannot establish by itself:**  
PEO C4I / NAVWAR program-office requirements. ONR/NRL organizational codes are not the same
semantics as PMW/PMS structures; do not force them into PEO office families.

**Useful identifiers / joins:**  
Annex 25-style office and contracting fields as printed on those sheets; title and timing for
research buys.

**Access / maintenance notes:**  
Verified; direct download worked. Proposed monitor: monthly.

#### LRAEs posted as SAM.gov Special Notices

`source_key: lrae_as_sam_special_notice`

**Why we use it:**  
Hypothesis supported by the registry: some activities (NAVSUP, NAWCAD pattern) may post LRAE
material as SAM Special Notices, offering another discovery route when no activity-hosted
spreadsheet is found.

**What it can establish:**  
Nothing validated here yet. Intended fields if inspected: SAM notice id, posted date, and an
xlsx/pdf attachment.

**What it cannot establish by itself:**  
NAVWAR’s own hosted LRAE (NAVWAR publishes on its site). Not a substitute for a retrieved Annex 25
file until the attachment is captured.

**Useful identifiers / joins:**  
SAM notice id; posted date—once inspected.

**Access / maintenance notes:**  
**not_inspected.** Pointer URL only; attachment not retrieved (needs SAM API key or extract).
Proposed monitor: weekly Special Notice search for “Long Range Acquisition.” Not operationally
integrated in this package.

#### Why LRAE fields matter

| Field / identifier | What it helps answer | Important limitation |
| --- | --- | --- |
| PID (`pid`) | Stable row key across releases when present | LRAE-internal only; absent in the 2024 NAVWAR package |
| Requirement / program office (`office_code_string`) | Which office the activity associates with the planned buy | Needs normalization; several code families on one sheet |
| Contracting office UIC (`contracting_office_uic`) | Which contracting activity is expected to run the buy | Not the requirement owner |
| Existing contract (`existing_contract_number`) | Incumbent PIID to join FPDS / follow-on lineage | Sometimes concatenated IDV+order; may be blank |
| Incumbent (`incumbent_contractor`) | Named vendor on a follow-on plan | Name only; no UEI in the LRAE |
| Solicitation FY/quarter | Planned public-notice window | Estimate; often slips or reads TBD |
| Award FY/quarter | Planned award window | Estimate; not a signed date |
| Anticipated total value | Planning value range (incl. options as stated) | Not an obligation or award ceiling |
| Contracting POC name/contact | Contracting staff contact on the row | Not automatically a program-office member |
| Title / description | Human-readable planned buy | Title match to a later notice is inference only |
| Follow-on or new | Whether the row is framed as follow-on vs new work | Label is as written by the activity |

#### What an LRAE row does not prove

- That the forecast will execute on the stated schedule
- That a later solicitation will use the same wording or title
- That the listed contracting office owns the mission requirement
- That a named contracting POC is a member of the program office
- That the estimated value equals later obligations or an award ceiling
- That a title match alone identifies the later notice or award

Dated NAVWAR packages for 2023, 2024, and 2025 matter because adds, removals, and field changes
between releases are themselves early signals. Each version is evidence as of that release date
only—not retroactive truth about what “always” was planned.

### Industry Engagement and Active Opportunities

#### PEO C4I industry engagement

`source_key: peoc4i_industry_engagement`

**Why we use it:**  
Public engagement routes (AFCEA WEST events, Industry Intake Form) surface what offices told
industry they need, and when—early context before a formal SAM notice.

**What it can establish:**  
Event date; offices said to participate; stated priorities or gaps as printed; intake mechanism
named in the release (inspected WEST 2026 example: all eleven program offices featured).

**What it cannot establish by itself:**  
A solicitation, value, timing, or contracting office; that an engagement contact is a
decision-maker; that pre-reorganization PEO C4I framing still matches the PAE Mission Systems
structure.

**Useful identifiers / joins:**  
Event date; office names as written in the release; intake-channel pointers.

**Access / maintenance notes:**  
Verified via DVIDS (direct). Monitor daily via the DVIDS unit page. Engagement is not a buy.

#### NAVWAR Commercial Solutions Opening (CSO)

`source_key: navwar_cso`

**Why we use it:**  
NAVWAR’s published alternate pathway for commercial solutions—distinct from the ordinary
forecast → SAM synopsis → award trail when the activity opens a CSO problem set.

**What it can establish:**  
What the CSO pages state: problem statements, links to a SAM notice, and PIEE vendor-instruction
pointers (and DIU partnership language where present). Owner office only if the CSO text names it.

**What it cannot establish by itself:**  
That every NAVWAR buy uses this route; office ownership when the text is silent; full solicitation
packages behind PIEE.

**Useful identifiers / joins:**  
SAM notice links from the CSO page; solicitation pointers as published.

**Access / maintenance notes:**  
Verified via Wayback (Akamai 403 live). Proposed monitor: weekly. Do not equate CSO posting with
a conventional FAR solicitation without reading the linked notice type.

#### SBIR/STTR topics

`source_key: sbir_sttr_topics`

**Why we use it:**  
Topic releases can show Navy S&T needs—and sometimes a sponsoring office—earlier than a normal
production procurement.

**What it can establish:**  
Topic number, component, title/description, technical POC, and open/close dates when pulled from
sbir.gov / the DoD portal. Landing/search page was reached; Navy topic sampling was deferred.

**What it cannot establish by itself:**  
A conventional LRAE-style forecast; production requirements; a guaranteed follow-on contract.

**Useful identifiers / joins:**  
Topic number (e.g. N26x-xxx); component; technical POC as printed (not automatic decision
authority).

**Access / maintenance notes:**  
Verified at search-page level. Old topics.json API path 404; DoD portal is client-rendered.
Cadence: three DoD cycles per year.

#### SAM.gov public Contract Opportunities extract

`source_key: sam_public_csv_extract`

**Why we use it:**  
Broad, keyless discovery of current public notices by contracting office (AAC), with dates,
type, and solicitation number for nightly diffs.

**What it can establish:**  
Current-dataset notice id, title, solicitation number, department/agency/office fields, posted
date, notice type, set-aside, response deadline, NAICS/PSC, POC name/email, and award fields when
type is Award. Inspected pull: 535 NAVWAR-family notices (N00039 / N66001 / N65236).

**What it cannot establish by itself:**  
Attachment or full description text; program-office ownership from the contracting AAC alone;
notices older than the current daily “Full” file (historical yearly archives are a separate source
family, not covered here).

**Useful identifiers / joins:**  
Notice id; solicitation number; AAC / office fields (contracting identity only); NAICS/PSC for
candidates, never ownership.

**Access / maintenance notes:**  
Verified; large S3-backed CSV, no key. Nightly download and diff on notice id + modified date.

#### SAM.gov Opportunities API v2 (documented)

`source_key: sam_opportunities_api`

**Why we use it:**  
The documented public Opportunities API the project considered for search, description, and
attachments.

**What it can establish:**  
Nothing in the tested environment: api.sam.gov returned HTTP 404 (empty body, istio-envoy) with
and without a key from two networks.

**What it cannot establish by itself:**  
Live notice retrieval for this package. It is not the active working SAM method here.

**Useful identifiers / joins:**  
None captured (host unreachable). Documented fields would include noticeId, solicitationNumber,
POC, description URL, resourceLinks—if the host answered.

**Access / maintenance notes:**  
**blocked.** Keys would come from a SAM.gov account, not api.data.gov. Do not treat this as the
operational path; see `sam_gov_site_api`.

#### SAM.gov site API (working path)

`source_key: sam_gov_site_api`

**Why we use it:**  
Practical keyless endpoints the SAM.gov web app (and `research/tools/sam_notices.py`) use for
lookup by solicitation number or notice id, notice detail, description body, and attachment
lists/downloads where files exist.

**What it can establish:**  
Notice metadata and description text (e.g. NILE ISS 6 RFI naming PEO C4I / PMW 150); attachment
metadata; extractable PDF/DOCX text when a real file is attached. Office-code regex hits in text
are candidate mentions until validated under the attribution rules.

**What it cannot establish by itself:**  
SeaPort-NxG task-order competitions (not posted on SAM); bulk date-range discovery without the
daily extract; that a POC is a requirement-office member; that regex mention extraction proves
ownership. Many 2026 NAVWAR notices list only PIEE links, not downloadable SOWs.

**Useful identifiers / joins:**  
Notice id; `solicitationNumber`; description body; attachment resource ids / names; POC
name/email/type as contracting contacts.

**Access / maintenance notes:**  
Verified; undocumented but public (`api_key=null`). Distinct from the blocked documented host
api.sam.gov. On-demand per solicitation from FPDS, LRAE, or the daily extract; daily for watched
notices.

#### PIEE Solicitation Module

`source_key: piee_solicitation_module`

**Why we use it:**  
Full solicitation packages for many NAVWAR requirements now live here rather than as SAM
attachments—SAM synopses increasingly point only to a PIEE link.

**What it can establish:**  
In principle: solicitation number, issuing DoDAAC, attachments, amendments, vendor Q&A—for an
authenticated vendor account. This package retrieved only the public access-instructions PDF and
recorded the SAM attachment-list gap.

**What it cannot establish by itself:**  
Anything without a vendor login; automated monitoring of package content.

**Useful identifiers / joins:**  
Solicitation number as shown on SAM’s PIEE link text; issuing DoDAAC when visible after login.

**Access / maintenance notes:**  
**restricted** (manual). Not automated; rely on SAM synopses and record the gap.

#### SeaPort-NxG portal

`source_key: seaport_nxg`

**Why we use it:**  
Vehicle portal for Navy services task-order competitions under SeaPort-NxG IDVs (e.g. N00178-19-D-…).
Many PEO C4I support recompetes run here and never appear as SAM solicitations.

**What it can establish:**  
In principle: task-order solicitation numbers, ordering office, and awardee—for vehicle holders.
This network could not open the portal.

**What it cannot establish by itself:**  
Public completeness of competitions; that a vehicle holder is the incumbent on a specific
requirement without separate award/forecast evidence.

**Useful identifiers / joins:**  
Referenced IDV PIID on awards (tracked elsewhere); task-order solicitation numbers when visible
inside the portal.

**Access / maintenance notes:**  
**blocked** (manual; HTTP 000 every attempt). Not automated; awards tracked through FPDS
referenced IDVs when those are available.

#### Opportunity-stage distinctions

| Signal / record | What it means here | What it does not mean |
| --- | --- | --- |
| Industry engagement / industry day | Public outreach about needs or intake | A solicitation or funded buy |
| SBIR/STTR topic | Published S&T topic in a topic cycle | A production forecast or guaranteed follow-on |
| Sources sought / RFI | Market research or information request | A final RFP or award |
| Special notice | SAM notice type for announcements (e.g. industry day, ceiling, LRAE post) | Automatically a full solicitation package |
| Solicitation | Formal request for proposals/quotes as typed on SAM (or inside a vehicle) | An award; ownership without office text |
| Award | Signed action or award notice | That the notice text alone named the program office |

#### Useful SAM joins

- **Solicitation number → later award:** deterministic when the same identifier appears on both
  sides (do not expand award sources here).
- **Contracting office / AAC → contracting activity:** deterministic identity; never requirement
  ownership by itself.
- **Explicit PMW/PMS/PEO (or office-name) wording in description or attachments:** textual /
  direct evidence for attribution when quoted and validated.
- **Title similarity only:** candidate / inferred match to a forecast or later notice.
- **Notice id:** versions, amendments, and attachment lists for one opportunity.
- **Attachment links:** may be real files or PIEE-only pointers—record which.

### Awards and Contract Execution

#### FPDS ATOM public feed

`source_key: fpds_atom_feed`

**Why we use it:**  
Primary public history of signed contract actions—tracing an LRAE “Existing Contract Number,”
later awards and modifications, and the contracting vs funding organizations on each action.

**What it can establish:**  
Per action: PIID and mod number, referenced IDV, solicitation id, contracting office DoDAAC,
funding requesting office, signed date, vendor (name/UEI), obligated amount, description text,
NAICS/PSC, and related competition fields as published. Query by office + signed-date window or
by PIID for the full mod chain.

**What it cannot establish by itself:**  
Requirement/program-office ownership unless the description (or a linked SAM notice) explicitly
names it. Contracting office and funding office identify buyer and payer only. A miss in one
date window is not proof no award exists (~90-day DoD publication lag; host resets on long scans).

**Useful identifiers / joins:**  
PIID + mod; `referencedIDVID`; `solicitationID`; `contractingOfficeID`;
`fundingRequestingOfficeID`; vendor UEI/name; description text for office-code evidence.

**Access / maintenance notes:**  
Verified; open ATOM feed (10 entries/page). Daily pull per contracting office since last signed
date; long history scans use monthly/signed-date windows because the host resets. Do not treat a
negative window as definitive absence.

#### USAspending API v2

`source_key: usaspending_api`

**Why we use it:**  
Complements FPDS with award-level JSON: ceilings, total obligations, periods of performance,
parent IDV, and keyword search across descriptions (e.g. “PMW 160”).

**What it can establish:**  
Award identity (`piid`, generated unique id), recipient, awarding/funding agency-office names,
`total_obligation`, `base_and_all_options`, PoP start/end/potential end, `parent_award_piid`,
description, NAICS/PSC, plus transactions/subawards when retrieved. Not every FPDS ATOM field
has a one-to-one counterpart here.

**What it cannot establish by itself:**  
Requiring office unless named in the description; that obligations equal a budget request or an
LRAE estimate; that ceiling equals money spent.

**Useful identifiers / joins:**  
`piid`; `parent_award_piid`; solicitation when present on the award detail; description text;
office names as awarding/funding labels (not PMW ownership).

**Access / maintenance notes:**  
Verified; open API. Reporting lag follows FPDS. Weekly refresh of watched awards; nightly
keyword search for office codes proposed.

#### DoD daily contract announcements

`source_key: dod_contract_announcements`

**Why we use it:**  
Same-day public prose for larger announced awards—vendor, value, description, contracting
activity, and contract number when the article includes them—useful corroboration, not a
complete record.

**What it can establish:**  
What that day’s announcement states (RSS + article). Registry notes daily coverage for awards
over $7.5M; RSS answers directly; war.gov article bodies often need a US-egress path.

**What it cannot establish by itself:**  
That no award exists if it is absent from the feed; requiring office unless stated; FPDS-grade
identifier completeness. Prefer FPDS/USAspending for PIID lineage and money fields.

**Useful identifiers / joins:**  
Contract number when printed; awardee name; contracting activity name as published.

**Access / maintenance notes:**  
Verified RSS; article pages may 403 from non-US hosts (Browserbase fallback recorded). Daily
RSS poll proposed.

#### GAO bid protest decisions and docket

`source_key: gao_bid_protests`

**Why we use it:**  
Conceptually, protest decisions can surface contested solicitations, chronology, evaluation
issues, and related identifiers when a procurement is protested.

**What it can establish:**  
Nothing retrieved in this package. Intended fields if reachable: B-number, agency, solicitation
number, decision date, outcome.

**What it cannot establish by itself:**  
Office ownership; that every buy has a protest; a complete agency acquisition file. Not
integrated here.

**Useful identifiers / joins:**  
Solicitation number; B-number—once a usable sample is inspected.

**Access / maintenance notes:**  
**blocked** (HTTP 403 to automation). Registry notes the platform’s pursuit-intelligence runner
already covers GAO. Proposed cadence weekly if a fetch path exists; do not treat as collected.

#### What award fields tell us

| Field / identifier | What it helps answer | What it does not prove |
| --- | --- | --- |
| PIID (+ mod) | Which award/order and which modification | Who owns the requirement |
| Referenced IDV / parent award | Which vehicle the order sits under | Requirement office; that vehicle holder = incumbent on a specific need |
| Solicitation number | Join to SAM notice lineage when shared | Ownership by itself |
| Contracting office DoDAAC | Which activity signed/issued the action | Program-office ownership |
| Funding organization | Which organization is recorded as payer | Program-office ownership |
| Vendor / recipient | Who was awarded | Future incumbency without a linked forecast/award chain |
| Obligation | Money placed on an action or total obligated on an award | Ceiling, budget request, or LRAE estimate |
| Potential / ceiling (`base_and_all_options`) | Maximum award value as recorded | Money actually obligated or requested in the budget |
| Award description | Possible explicit office/program language | Ownership if the text is silent, administrative, or only a title match |
| Period of performance | Performance window on the award | That a follow-on will award when PoP ends |

Not every source exposes every row (e.g. ceiling and rich PoP are clearest on USAspending;
per-action obligation and mods are clearest on FPDS).

#### Keep the money fields separate

- **Budget request** — what the Department asked Congress for (justification / Comptroller
  tables).
- **LRAE estimated procurement value** — planning range on a forecast row (disclaimer applies).
- **Obligation** — money recorded on a contract action (FPDS) or total obligated on an award
  (USAspending).
- **Potential / ceiling** — base-and-all-options (or equivalent) maximum on the award.

These can sit in the same program context but answer different questions; do not treat them as
interchangeable amounts.

#### Award-stage joins

- **LRAE existing contract / PIID → FPDS action:** deterministic when the PIID matches.
- **SAM solicitation number → award `solicitationID`:** deterministic when shared.
- **Referenced IDV → vehicle:** deterministic.
- **Contracting DoDAAC → contracting activity:** deterministic identity, not ownership.
- **Funding code → funding organization:** deterministic identity, not ownership.
- **Explicit PMW/PMS/PEO (or office) wording in award description:** textual / direct
  attribution evidence when quoted and validated.
- **Program-title similarity alone:** candidate / inferred.
- **No public PE → PIID map:** do not invent one.

### Historical and Archive Sources

#### Internet Archive Wayback Machine

`source_key: wayback_machine`

**Why we use it:**  
Official Navy pages and spreadsheets change or disappear. Wayback is archive infrastructure—not
the original publisher—used to recover what an official URL showed at a capture time so
organization pages, LRAE releases, and similar material stay comparable across dates.

**What it can establish:**  
A dated copy of an official page or file when the crawler captured it: original URL, capture
timestamp, and raw bytes (often via the `id_` endpoint), with local hash in
`documents_manifest.jsonl`. Used here for LRAE xlsx packages, PEO/NAVWAR pages, tear sheets, and
similar when live hosts block or rewrite.

**What it cannot establish by itself:**  
That the content remained valid after the capture; the real-world effective date of an org change
unless the underlying page states it; that a missing snapshot means the source never existed;
pages the crawler was blocked from (or that returned WAF stubs).

**Useful identifiers / joins:**  
Original source URL; `wayback_timestamp` (capture); release/filename identifiers on recovered
files; SHA-256 of local bytes in the manifest. Capture date is availability/observation evidence,
not automatically the content’s effective date. Publication/release date on the document (when
present) stays separate from retrieval date.

**Access / maintenance notes:**  
Verified; on demand. CDX index can 503; some hosts (e.g. secnav) return firewall stubs to the
crawler. Prefer live official sources when stable; use Wayback when historical state matters or
the live page is gone/blocked.

#### SAM.gov archived yearly Contract Opportunities extracts

`source_key: sam_archived_yearly_extracts`

**Why we use it:**  
The daily SAM “Full” extract holds the current dataset only. Yearly
`FYxxxx_archived_opportunities.csv` files supply historical notices for backtests and first-notice
dates without look-ahead from today’s extract.

**What it can establish:**  
Same 47-column notice fields as the daily extract (notice id, solicitation number, AAC/office,
dates, type, description link, POC fields, etc.) for notices in that fiscal-year archive file.
**FY2025** is retrieved and used (about 1.1 GB; 399,820 rows; 666 NAVWAR-family notices; first-notice
dates for several backtests). **FY2021** is listed/probed for size but **not yet captured**—still an
open historical gap (e.g. BT05 solicitation lookup).

**What it cannot establish by itself:**  
Attachment text; program-office ownership from contracting AAC alone; that absence from one
year’s file proves a notice never existed. A historical notice is still only opportunity-stage
evidence until office language is validated.

**Useful identifiers / joins:**  
Notice id; solicitation number; AAC / office fields; posted/modified dates; notice type—as in
the daily extract schema. Large files; stream/filter by AAC; derived NAVWAR subsets should be
reproducible from the recorded archive hash.

**Access / maintenance notes:**  
Verified for FY2025 (direct, range requests). Quarterly re-pull of the two most recent fiscal
years proposed. Do not treat FY2021 as complete in this package.

#### Rules for using archived evidence

- Prefer the original official source when it is still available and stable.
- Use archived official copies when the live source changed, disappeared, or historical state
  matters.
- Record the original URL and archive/retrieval context (capture timestamp, method, hash).
- Keep observed/capture time separate from real-world effective dates (and from retrieval time).
- Backtests may use only evidence available by the declared cutoff date.
- A missing archive result is not proof of nonexistence.

## 5. How the Sources Connect

No single public system holds the full buyer map: who owns a requirement, what may be funded,
what may be bought, what is on the street, and what was awarded. The package therefore chains
several source families. Stages can be skipped; identifiers can change; pages and files can
update or disappear; one record can name several program offices; some chains stay unresolved.

### 5.1 End-to-End Evidence Flow

```
Organization / leadership evidence
        |
Budget / agency intent
        |
Acquisition forecast (LRAE)
        |
Industry engagement / public notice
        |
Solicitation (SAM and/or vehicle / PIEE)
        |
Award / execution (FPDS, USAspending)
        ^
Congressional marks -------------+  (same PE / BLI as budget tables)
Contact observations ------------+  (person + role + office + date)
Archived historical copies ------+  (Wayback; SAM yearly archives)
```

Read this as a common path, not a mandatory one. SeaPort-NxG task orders often jump from forecast
to award with no SAM solicitation. Budget and forecast rarely share a structured key. Archives
support cutoffs and vanished pages; they are not a parallel lifecycle stage.

### 5.2 Core Connection Paths

| Path | Main join(s) | Join class | What it helps establish | Main caution |
| --- | --- | --- | --- | --- |
| Organization source → organization node | Official office/program name; office code / alias in `organization_seed.json` | Deterministic when alias/code is known; textual/direct when based on explicit wording | Dated identity and structure claims | Live pages drift; prefer dated captures for history |
| LRAE requirement office → organization node | Normalized office code (`org_code_families.json` → alias table) | Deterministic after validated normalization | Which office the forecast associates with the planned buy | Several code families on one sheet; unknown codes stay unresolved |
| LRAE existing contract → FPDS / USAspending | PIID / existing contract number | Deterministic when exact identifier is shared | Incumbent award history for a follow-on row | LRAE sometimes concatenates IDV+order |
| LRAE contracting office → contracting activity | UIC / DoDAAC | Deterministic identity | Who is expected to run the buy | Not requirement ownership |
| LRAE planned requirement → SAM notice | Solicitation number if shared; else title / office / NAICS / timing | Deterministic when identifier shared; inferred/candidate on title/timing only | Candidate public notice for a forecast | PID is not in SAM; many buys never appear on SAM |
| SAM notice → award | Solicitation number | Deterministic when exact value is present in both | Notice lineage to signed action | SeaPort-NxG competitions often have no SAM notice |
| Award → contract vehicle | Referenced IDV / parent award | Deterministic | Which vehicle an order sits under | Multi-customer vehicles are not attributed as an office |
| Award → contracting organization | Contracting DoDAAC | Deterministic identity | Issuing / signing activity | Never mission ownership by itself |
| Award → funding organization | Funding office / code | Deterministic identity when coded | Paying organization | Separates systems commands; not PMW ownership |
| Notice / award text → program office | Explicit PMW / PMA / PMS / PEO (or office-name) wording | Textual/direct | Requirement owner for attribution | Quote context; multi-office lists; PEO alone ≠ PMW |
| Budget → program (→ office) | PE / BLI for table identity; program title toward office | Deterministic for PE/BLI row identity; candidate/inferred for title→office | Requested (and related) funding by line | No public PE→PIID map; title bridge is inference |
| Congressional mark → budget line | PE / BLI / line title in funding tables | Deterministic when the same identifier appears | Proposed adds/cuts vs request | Committee mark ≠ enacted funding |
| Organization / leadership source → contact observation | Person name + role + office + observation date | Textual/direct | What a source said about a contact on a date | Contracting POC ≠ program-office member |
| Contact observation → recommendation | `contact_observation_ids` | Explicit internal reference | Suggested outreach path with confidence/basis | Recommendation is not a source fact |

### 5.3 Deterministic, Textual, and Inferred Joins

**Deterministic.** An exact structured identifier or a validated alias connects two records—for
example PIID, solicitation number, referenced IDV, DoDAAC/UIC, or a normalized known office code
that resolves in the seed alias table.

**Textual/direct.** A source literally names the office, program, or person in relevant
context—for example “PMW 160” in an award description, a tear sheet naming a program manager, or
a SAM notice that opens with the program office.

**Inferred/candidate.** Multiple clues suggest a link without an exact shared identifier or a
direct ownership statement—for example similar title and quarter between LRAE and SAM, or a
program-name bridge from a budget line title to an office via a tear sheet.

Never silently upgrade an inferred join to a direct or deterministic join. Record the class with
the claim.

### 5.4 Where the Chain Breaks

- No universal public program-office identifier across forecast, SAM, FPDS, and budget systems
- No deterministic public PE → PIID map
- Contracting office ≠ requirement owner; funding organization ≠ requirement owner
- Titles and descriptions change across lifecycle stages (and mods re-author description text)
- PMW/PMA/PMS/PEO ownership often appears only in free text
- Reorganizations change parentage over time (dated edges; both eras may be true)
- Historical pages/files may disappear, lag, or leave no archive capture
- Forecast rows slip, change, or are removed between LRAE releases
- Current SAM daily extract alone is insufficient for every historical backtest (yearly archives;
  FY2021 still open)
- PEO Digital / PEO MLB do not currently expose a verified full PMW-style office-code inventory
- Some sources are blocked, restricted, or manual (documented Opportunities API, OSBP index,
  GAO, PIEE packages, SeaPort portal)
- One requirement or award description can name multiple program offices; do not collapse them

### 5.5 Example Resolution Pattern

Generic pattern (not a claim that every case succeeds):

1. Start with an LRAE forecast row.
2. Normalize the requirement-office code; resolve it against organization memory (alias table /
   code family). Unknown codes stay unresolved.
3. If an existing contract number is present, follow that PIID into FPDS / USAspending for award
   history and mods.
4. If a solicitation id appears on the award (or elsewhere), search SAM by that number; read
   notice (and attachment) text for explicit office wording.
5. Record contracting and funding organizations separately—never as ownership.
6. Assign an evidence class (`directly_documented`, `inferred`, `ambiguous`, or `unresolved`).
7. If evidence conflicts, is weak, or lists several offices, keep multiple candidates or
   unresolved status; do not force a single owner from title similarity or contracting UIC alone.

The buyer map is built from a chain of individually auditable claims, not one master identifier.

## 6. Identifier and Join-Key Guide

Lookup sheet for identifiers that appear in this research. Each row states what the identifier
is, where it shows up, what join is safe, and what it does not prove.

### 6.1 Identifier Quick Reference

| Identifier | Identifies | Common source(s) | Safe join use | Main limitation |
| --- | --- | --- | --- | --- |
| Program / requirement office code | Program or requirement office (when validated) | LRAE office column; award/notice free text; tear sheets | Validated office-code normalization → org node | Several code families; not a contracting UIC |
| Contracting DoDAAC / UIC | Contracting (or funding) activity | LRAE UIC; FPDS; SAM AAC; PIID/sol prefix | Exact identifier match (identity only) | Not requirement ownership |
| PIID | Contract, order, or IDV number | FPDS; USAspending; LRAE existing contract | Exact identifier match | Not program-office ownership |
| Referenced IDV / parent award | Contract vehicle / parent | FPDS `referencedIDVID`; USAspending `parent_award_piid` | Exact identifier match | Vehicle ≠ requirement owner |
| Solicitation number | Solicitation / notice lineage key | SAM; FPDS `solicitationID` | Exact identifier match across notice↔award | Absent from LRAE; missing on many SeaPort orders |
| SAM notice ID | One SAM opportunity / version | SAM only | Source-local (detail, attachments, versions) | Not a cross-system master ID; ≠ solicitation number |
| LRAE PID | Forecast row within LRAE releases | LRAE only | Source-local (row key / release diffs) | Not resolvable in SAM/FPDS/USAspending |
| PE | RDT&E program-element budget identity | Comptroller R-1; congressional PE tables; DoN books | Exact PE match in budget/congress tables | No public PE→PIID map |
| BLI | Procurement budget line-item identity | Comptroller P-1; congressional OPN tables | Exact BLI match in budget/congress tables | ≠ P-1 exhibit line number |
| P-1 / R-1 line number | Row position in a P-1 or R-1 exhibit | Comptroller display tables; some report tables | Cite as P-1/R-1 line only | Not the BLI or PE |
| Program / requirement title | Human-readable name of a buy or system | Budget titles; LRAE; SAM; awards; tear sheets | Candidate/inferred only (unless other keys join) | Titles change across systems |
| Person + role + office + observation date | A dated contact claim | Tear sheets; DVIDS; LRAE POC fields; SAM POC | Textual/direct observation | Contracting POC ≠ program-office member |

### 6.2 Organization and Office Codes

**A. Requirement / program-office codes.** Validated codes such as `PMW-160` or `PMS-485` (and
related PMW/PMA/PMS forms) identify program or requirement offices after normalization and alias
lookup. NIWC codes such as `LSUBP00035` identify technical-center divisions, not PMWs.

**B. Contracting-office identifiers.** Six-character DoDAAC/UIC values such as `N00039` identify
contracting (or funding) activities. They are a different entity type from program offices.

**C. Organization aliases / names.** Strings such as `PEOC4I`, `NAVWAR`, or “PEO C4I” are names or
aliases. Resolve them through the seed alias table and code families—never treat them as generic
UICs. Descriptive suffixes (e.g. `N00039 - NAVWAR`) must be stripped before classification.
Aliases and parentage can change over time; a code match identifies the entity, not automatically
its parent on every historical date.

```
raw value
  → normalize (upper-case; strip " - NAME" suffix; collapse spaces/hyphens)
  → alias lookup (organization_seed.json)
  → specific code families (PMW/PMS, NIWC, front-office, …)
  → generic contracting UIC family last
  → unresolved if still unknown (keep verbatim)
```

Tokens that resolve as aliases (`PEOC4I`, `NAVWAR`) are never classified as UICs.

### 6.3 Procurement Identifiers

#### PIID

Contract, order, or IDV identity. Exact PIID match joins an LRAE “Existing Contract Number” to
FPDS/USAspending actions. Modifications are usually read with the base award (mod text alone is
weak). A PIID does not identify the requirement owner by itself.

#### Referenced IDV / Parent Award

Connects an order/action to its vehicle (e.g. SeaPort-NxG IDVs). Deterministic vehicle grouping.
The parent vehicle does not prove who owns the underlying requirement; multi-customer vehicles
are not attributed as an office.

#### Solicitation Number

When the same value appears on a SAM notice and an award record, the join is deterministic and
stronger than title similarity. Not always present or consistent (absent from LRAE; often absent
for SeaPort-NxG task-order competitions).

#### SAM Notice ID

32-hex opportunity id inside SAM. Useful for notice detail, attachments, and versions.
Source-local—do not confuse with solicitation number; not a federal master acquisition ID; not
present in FPDS or the LRAE.

### 6.4 Budget Identifiers

#### Program Element (PE)

RDT&E / program-budget identity (e.g. in R-1 and congressional PE tables). Exact PE match joins
budget and congressional rows. This research has **no** deterministic public PE → PIID mapping;
office linkage by program title is candidate/inferred.

#### Budget Line Item (BLI)

Procurement budget identity where present (e.g. OPN BLI `2915` for CANES). Exact BLI match joins
P-1 / congressional procurement tables. Distinct from the exhibit row number: BLI `2915` is not
“P-1 line 64”.

#### P-1 / R-1 exhibit line number

Position/reference inside a particular Comptroller exhibit. Write it explicitly as a P-1 or R-1
line. It is not the BLI or PE and can shift with table structure.

#### Program / requirement title

Useful for navigation and candidate matching across budget, forecast, SAM, and awards. Titles
change. Title similarity alone is candidate/inferred—never a deterministic join—unless
corroborated by a structured key or explicit office wording.

### 6.5 Identifiers That Are Only Locally Useful

#### LRAE PID

Tracks forecast rows inside LRAE releases and release diffs when present (2024 NAVWAR package has
no PID values). Not established as globally resolvable in SAM/FPDS/USAspending. Not a federal
master procurement ID.

#### Contact observation ID

Internal ids such as `cobs:…` link `contact_recommendations.json` rows back to sourced
observations via `contact_observation_ids`. Explicit internal reference—not a government
identifier.

#### Organization memory IDs

Local canonical ids such as `pmw:160`, `peo:c4i`, `pms:485`, `contracting:n00039` in
`organization_seed.json`. They collapse multiple spellings/codes onto one research entity. Local
research identifiers—not government-issued IDs.

### Do not confuse

| Do not confuse | With | Why |
| --- | --- | --- |
| Requirement office code | Contracting DoDAAC/UIC | Different entity types; UIC never proves mission ownership |
| BLI | P-1 line number | BLI is the budget line identity; P-1 line is exhibit position |
| PE | PIID | No public PE→contract map in this package |
| Solicitation number | SAM notice ID | Notice id is SAM-local; solicitation can span systems |
| LRAE PID | Solicitation / award identifier | PID is LRAE-internal only |
| Contracting POC | Program-office member | LRAE/SAM POCs are contracting staff unless a source says otherwise |
| Program title | Stable identifier | Titles drift; similarity is candidate/inferred |
| Local organization ID | Government-issued identifier | Seed ids are research graph keys only |

## 7. Evidence Strength and Source Limitations

This section is how the package judges evidence without overstating what a source
proves. A join can be exact, and a publisher can be official, and the buyer-map
question (who owns the requirement) can still be unanswered.

### 7.1 Attribution Evidence Classes

Ownership and related claims use exactly these four classes. The class records
how the **relevant connection** is evidenced. It is not a grade of the publisher.

**`directly_documented`**

The source explicitly states the connection needed for the claim.

What can justify it: an award description that names a program office or code
("PMW 160", "IN SUPPORT OF PEO MLB PMW 220"); a SAM.gov notice for that action's
solicitation that names the office; an official organization or tear-sheet
statement that names the office/person relationship being claimed (for example a
tear sheet naming a program manager as of that sheet's date).

An official source is not automatically `directly_documented` for every claim.
The source must state the relevant connection. An FPDS row is official about the
contract fields it contains; it documents ownership only if the description (or
the linked notice for the same solicitation) names the office.

What to do: treat the named office as the documented owner of that record; quote
the passage; keep multi-office lists as multi-office; do not promote contracting
or funding identity into ownership.

**`inferred`**

Multiple clues support a likely connection, but no single source states the full
conclusion for the record being attributed. `inferred` is a separate evidence
class, not a weaker spelling of `directly_documented`.

Repository-supported clues: title similarity; timing (planned quarter versus a
posted or award window); an incumbent / existing-contract match to an LRAE
follow-on row; a program-name bridge through an official tear sheet; other
corroborating office context (for example a mission statement that agrees with
the LRAE). The LRAE is an estimate about a future requirement, so its
requirement-office column corroborates rather than documents the current award
unless that award's own text also names the office.

EX08 stays `inferred` even though the LRAE follow-on row and the PMW 740 tear
sheet agree: the award text never names the office. A later notice about a
successor requirement does not upgrade the class for this action.

What to do: record the class, the clues, and any counterevidence; send the
record to review; never silently upgrade the class.

**`ambiguous`**

Evidence supports more than one plausible office or interpretation, and the
available sources do not justify selecting one as fact.

A functional match between a program name and an office mission is candidate
generation, not ownership (EX16 before the solicitation notice was read).
Counterevidence that the same program name is held by more than one organization
(ADNS production at PMW 160 and ADNS in-service work at NIWC Pacific) also keeps
a name-only reading from becoming fact.

What to do: preserve competing candidates and the evidence for each; do not
collapse to a single owner.

**`unresolved`**

Public evidence is insufficient to support a defensible attribution. The system
should abstain rather than guess.

EX19 is the type case: generic vehicle text, no office named, no LRAE row, and
the task orders that might name a requirement were not retrieved. An unknown
office-code token that does not resolve in the alias table stays unresolved
verbatim (the "FRD" component inside EX07).

What to do: leave the owner empty; keep candidates only as candidates; record
the evidence gap and a resolution path when one is known; still surface a
meaningful signal (for example a large ceiling increase) for review.
Abstention is a result.

Things that never establish ownership on their own: contracting office, funding
office, vendor, vehicle, NAICS, PSC, platform or system name, or a semantic
resemblance.

### 7.2 Join Strength Is Not Claim Strength

Section 5's join class answers how two records were linked. The attribution
class in 7.1 answers whether the evidence states the claim (usually requirement
ownership). They are not the same scale and do not map one-to-one.

**Join class (Section 5)**

- **Deterministic** — an exact structured identifier or a validated alias
  connects two records (PIID, solicitation number, referenced IDV, DoDAAC/UIC,
  normalized known office code).
- **Textual/direct** — a source literally names the office, program, or person
  in relevant context.
- **Inferred/candidate** — clues without an exact shared identifier or a direct
  ownership statement.

**Attribution evidence class (this section)**

- `directly_documented` / `inferred` / `ambiguous` / `unresolved`

**A deterministic join proves record identity or entity identity only for the
thing the identifier actually identifies.**

Examples of the gap:

1. **Exact PIID join.** An LRAE "Existing Contract Number" matching an FPDS
   award is a deterministic record join. It identifies the incumbent award. It
   does not, by itself, prove program-office ownership of that award.
2. **Exact DoDAAC join.** `N00039` on an FPDS action deterministically
   identifies the contracting activity. It does not prove N00039 owns the
   mission requirement. The same code appears on PMW 160, PMW 120, PMW 150,
   PMS 485, and PMW 220 work.
3. **Explicit "PMW 160" in relevant notice or award text.** This is
   textual/direct evidence and, when the wording is about that action, may
   support `directly_documented` attribution.
4. **Similar title plus expected quarter.** This is candidate/inferred (LRAE
   row to a later SAM notice). It cannot be silently promoted to direct
   attribution, even if a later notice eventually names the office.

A textual/direct join can support `directly_documented` when the named
relationship is the claim being made. An inferred join cannot become
`directly_documented` without a source that states the missing connection.

### 7.3 Source Authority, Recency, and Scope

Source quality is not one-dimensional. Official Navy and federal sources are
preferred, but authority, recency, and a captured URL still do not make an
unrelated claim valid. An official contracting record is authoritative about
the contract fields it contains, not automatically about program-office
ownership. A live organization page can be official and still fail to answer
who owns a requirement, which offices moved, or who currently holds a role.

| Factor | Question to ask | Why it matters |
| --- | --- | --- |
| Source authority | Is this an official Navy/federal record of the fact being claimed? | Prefer official sources. Authority is field-specific: contracting identity, funding identity, forecast office, and ownership language are different facts. |
| Observation date / recency | When was the statement dated or captured? | Older sources remain valid historical evidence. They are not automatically current. Contact work keeps source confidence separate from currency confidence; a tear sheet older than a year stays a dated observation until a later source confirms or ends the role. |
| Effective-date support | Does the source state when a relationship began or ended? | Observation date is not the effective date of a real-world organization change. Effective dates stay unknown unless a source supports them (`documented`, derived/`inferred` with a note, or `unknown`). |
| Scope | What wording does the source actually use? | Preserve the stated scope. Do not broaden "mission systems elements of ..." into a claim that every subordinate office moved. |
| Directness | Does the source state the relevant relationship, or only nearby context? | An exact ownership or role statement is stronger than title similarity, mission fit, or a contracting-office mention. |
| Historical coverage | Can this feed answer the question as of a past cutoff? | Current SAM daily extracts and live .mil pages do not answer every historical question. Yearly SAM archives and Wayback captures are required for backtests. A miss in one window is not proof of absence (~90-day DoD FPDS lag; FY2021 archive still open). |
| Reproducibility | Can another researcher retrieve the same bytes? | Source URL plus a `documents_manifest.jsonl` retrieval (method, status, hash) and a locator (sheet/row, quoted passage) is stronger than an uncaptured page reference. Not every registry source has a captured hash. |
| Access status | What could this research actually inspect? | `verified` — an inspected example exists. `blocked` — fetch failed (documented SAM API host, OSBP LRAE index, GAO, SeaPort portal). `restricted` — content exists behind login (PIEE packages). `not_inspected` — candidate only (posture testimony; LRAE-as-SAM-notice). Blocked, restricted, and not_inspected sources cannot be used as if they had been read. |

### 7.4 Conflicting Evidence and Organizational Change

Do not silently overwrite one official source with another.

Dated observations remain in the file. Organization relationships are temporal
claims: walk `child_of` and `consolidated_into` edges whose observations are
dated on or before the record's date (skip retracted ones). Reorganization can
make multiple historical statements valid at different times. A 2019 award that
resolves to PMW 160 under PEO C4I under NAVWAR, and a June 2026 modification of
the same award that resolves under PAE Mission Systems, can both be true.

Contradictory current-facing sources may remain `conflicting`. Both readings
stay; the research does not delete one to invent a clean chart.

Incorrect research is retracted. A wrong claim gets `review_status: retracted`,
a reason, and a pointer to what replaces it. It is never closed with an end
date that would make the error look historically true. Invented PMS 485
effective dates were retracted; the replacement relationships keep dates
unknown.

Actual historical change is recorded separately from retraction. A
source-documented end gets `effective_to` with `effective_dates_status:
documented` and `current_status.state: ended` (PMW 150 and PMW 760
program-manager handovers on 2025-08-19). A later statement that differs
without a stated change date makes the old relationship `superseded`; the
handover date stays unknown (PMW 160 program manager between the 2023 and 2025
tear sheets).

**PEO C4I / PAE Mission Systems.** The 2026-05-11 DoN release documents
consolidation of "mission systems elements" of named organizations into PAE
Mission Systems; it does not itemize which offices or functions moved. Later
and current NAVWAR material can still describe PEOs as NAVWAR components, while
other live pages describe NAVWAR as a service provider to the PAEs and PEO
Digital / PEO MLB as part of PAE Mission Systems. The research keeps those
observations and the stated scope rather than inventing a clean transition the
sources do not state.

An open or null `effective_to` does not mean the relationship is definitely
current. Currency is read from `current_status` (`last_confirmed` means true as
of the latest observation, not re-verified since).

### 7.5 Common Overclaims to Avoid

| Observation | Incorrect conclusion | Correct treatment |
| --- | --- | --- |
| Contracting office is N00039 | N00039 owns the requirement | N00039 is the contracting activity; ownership needs separate evidence |
| Funding organization identified | Funding org owns the requirement | Funding identity is separate from mission ownership; it can separate systems commands (N00024 on EX09) but not PMWs inside NAVWAR |
| Same or similar title | Same procurement or program | Candidate join pending corroboration (shared identifier or explicit office wording) |
| Vendor appears on an award | Vendor is incumbent for every future related requirement | Incumbent status requires linkage to that requirement/contract context; one vendor can serve several offices |
| Old tear sheet names a program manager | Person is still current | Historical role observation; current currency needs a recent confirmation |
| Wayback snapshot captured on date X | Real-world relationship began on X | Source was observable/captured by X; effective date may remain unknown |
| PEO Digital / PEO MLB page lists solution areas | Solution areas are verified office codes | Do not manufacture an office inventory; LRAE front-office codes remain the public handle here |
| One source says "mission systems elements of..." | Every subordinate office moved | Preserve the stated scope |
| Repeated contact name across multiple rows of one LRAE release | Multiple independent sources | Repeated observations from one source release (`independent_sources: 1`) |
| No result in one FPDS/SAM query | No award or notice exists | Consider query limits, ~90-day publication lag, historical coverage (daily extract vs yearly archive), SeaPort-NxG/PIEE gaps, or `unresolved` |

### 7.6 When to Leave a Result Unresolved

`unresolved` is a valid result, not an error. It means the current public
evidence does not support a stronger claim.

Leave the result unresolved when, for example:

- no source explicitly links the requirement to an office
- candidate evidence conflicts and no source justifies selecting one owner
- only contracting or funding identity is known
- title similarity is the only bridge
- source access is blocked or restricted and no equivalent official evidence is
  available
- historical evidence exists but current status cannot be established
- one record involves multiple offices (or an unknown token) and the evidence
  does not justify collapsing them
- source dates do not establish an effective transition date
- modification text is administrative ("DE-OBLIGATION", "CEILING REALIGNMENT")
  and the base award also does not name an owner
- an unknown office code does not resolve in the alias table / code families

Expected behavior:

- preserve observations
- keep competing candidates when appropriate
- record the evidence gap and, when known, a resolution path
- avoid inventing missing fields (effective dates, office codes, parentage)
- wait for stronger evidence

Do not treat `unresolved` as a failed run. Route meaningful signals to review
and keep the evidence class honest. A claim in this package should not outrun
the evidence that can be quoted for it.

## 8. Known Gaps and Access Blockers

What this package has not yet retrieved, what access currently prevents, and what remains
structurally unresolved even when sources are in hand. A gap here is not permission to infer
the missing field.

### 8.1 Open Source-Collection Gaps

Only currently open or partial collection items. T05 items 2 (2024 NAVWAR LRAE), 3 (FY2026
FPDS rescan), 6 (NAVSEA LRAE location pointer), and 7 (Digital/MLB inventory check) are not
listed as open.

| Gap | Current status | Why it matters | What is missing |
| --- | --- | --- | --- |
| FY2021 SAM.gov yearly archive (`FY2021_archived_opportunities.csv`) for BT05 / solicitation `N0003921R3015` | missing | FY2025 archive is retrieved and used. BT05’s 2021 cutoff still lacks the desired yearly-archive evidence. Do not treat a miss in the current daily extract as proof that no notice existed. | Official FY2021 archive bytes, a reproducible NAVWAR-family subset, and a BT05 `cutoff_basis` update |
| House FY2027 RDT&E PE marks (`CRPT-119hrpt715`) | partial | Official package exists. HTML text and OPN table rows (including the CANES add) are captured. The RDT&E PE table did not surface in HTML and is not fully captured. Do not cite House RDT&E marks as complete. | Page-addressable extraction from the govinfo PDF for the tracked PEs |
| Department of the Navy narrative budget books (`RDTEN_BA7-8_Book.pdf`; FY2026 narrative books) | blocked / incomplete | Comptroller P-1/R-1 tables and FY2027 OPN BA2 / Highlights books are in the manifest. Exhibit narratives that name programs and acquisition plans are not. Do not fill those narratives from line titles. | Successful official retrieval of the remaining books from a path the host accepts (queued in `manual_pdf_requests.json`) |
| Senate report and FY2027 enacted funding table | missing | House OPN recommendations are extracted; they are not enacted amounts. Do not treat the House table as the enacted FY2027 figure. | Official Senate / enacted govinfo packages for the tracked lines and PEs |

### 8.2 Access and Network Blockers

Statuses are as tested in this environment. `blocked` means access/retrieval did not succeed
here; `restricted` means authenticated/manual access this package does not have;
`not_inspected` means the source is not validated for operational use. Blocked here is not a
claim that the source is unreachable from every network.

| Source / system | Status | Limitation | Current handling |
| --- | --- | --- | --- |
| DoN budget justification host (`secnav.navy.mil/fmc`; `don_budget_justification_books`) | blocked (remaining books) in the tested environment | Host resets automated connections; Wayback often returns a WAF stub; hosted browser also refused for this host. FY2027 materials page, OPN BA2, and Highlights retrieved; `RDTEN_BA7-8_Book.pdf` and FY2026 books not. | Manual / US-network queue; Comptroller P-1/R-1 as the structured request tables already in hand |
| `don_osbp_lrae_index` | blocked | Connection reset on automated attempts from this network; Wayback received a firewall stub; page not retrieved. | Queued for a US-network session; do not treat the repo as having indexed all Navy LRAEs |
| `sam_opportunities_api` (api.sam.gov) | blocked | HTTP 404 (empty body) with and without a key from two networks. | Working path is `sam_gov_site_api` plus the public CSV extract; do not treat the documented host as operational here |
| `piee_solicitation_module` | restricted | Full packages require a vendor login. Many 2026 NAVWAR SAM notices list only PIEE links. | SAM synopses and attachment-list gap recorded; public access-instructions PDF retrieved; no package-content monitoring |
| `seaport_nxg` | blocked | HTTP 000 from this network; task-order RFPs are visible to vehicle holders. | Awards tracked through FPDS referenced IDVs when those exist; no portal substitution |
| `gao_bid_protests` | blocked | HTTP 403 to automation from this network. | Documented gap in this package; registry notes the platform pursuit-intelligence runner covers GAO; not collected here |
| NAVSEA live Small-Business / warfare-center forecast pages | live 404 / hosted-browser in the tested environment | Enterprise LRAE URL returned 404 on 2026-09-16; Akamai 403 to non-US direct. Archive copy of the December 2025 enterprise file is verified. | Wayback enterprise xlsx; live pointer recorded (per-warfare-center forecast pages). T05 item 6 is not re-opened as a collection miss |
| `navy_posture_testimony` | not_inspected | No inspected example URL or hash. | Candidate source only until a Navy acquisition hearing is sampled |
| `lrae_as_sam_special_notice` | not_inspected | Pointer URL only; attachment not retrieved. | Not a substitute for a retrieved Annex 25 file; NAVWAR hosts its own LRAE |

### 8.3 Organizational and Attribution Gaps

These are not access or retrieval misses. They remain even when the related official
sources have been read.

- PEO Digital: no official office/code inventory has been verified. Live About / Offerings /
  Industry pages describe solution areas and name no offices. Do not manufacture an office
  list. LRAE codes such as `Digital TD` and `PCE` remain the public handle here.
- PEO MLB: same. Portfolio pages describe defense business systems in prose; LRAE codes such
  as `Pf007NERP` remain the public handle.
- PAE Mission Systems portfolio-to-PMW mapping remains an interpretation (`int:001`) where no
  source directly places former offices into the five named capability portfolios.
- Some reorganization / parentage effective dates remain unknown. PMS 485’s realignment date
  is unknown and is recorded that way after invented dates were retracted; that is a correctly
  represented evidence gap, not an unfixed mapping error.
- PMW 160 program-manager handover date between the 2023 and 2025 tear sheets remains
  unknown; the later sheet supersedes who was named in January 2025, not when the change
  occurred or who holds the role today.
- Some requirements stay multi-office or `unresolved` (EX07 named offices plus unresolved
  `FRD`; EX19 generic NIWC vehicle with no owner signal).
- No deterministic public PE → PIID bridge. Budget-to-office by program title stays
  candidate/inferred.
- Contracting office and funding organization still do not establish requirement ownership.
- Title-only bridges remain inferred.
- Some historical SAM coverage depends on yearly archives not yet captured (FY2021).
- Some contact/role recency remains unknown (tear sheets older than a year; LRAE POCs from
  the June 2025 release with no later confirmation).

### 8.4 What Would Close Each Gap

| Gap | Evidence needed | Result if found |
| --- | --- | --- |
| FY2021 SAM archive | Official yearly archive plus a reproducible NAVWAR-family subset | BT05 cutoff evidence can be validated against contemporaneous notice data |
| FY2027 House RDT&E marks | Official PDF pages containing the tracked PE rows | House mark values can be cited page-by-page |
| DoN narrative books | Successful official retrieval of `RDTEN_BA7-8_Book.pdf` and the FY2026 books | Program narrative / acquisition-plan context can be added |
| Senate / enacted FY2027 tables | Official Senate report and enacted-act funding tables for the tracked lines and PEs | Enacted (or Senate) amounts can replace House-only recommendations |
| PEO Digital / MLB office inventories | Official page or document that explicitly names office codes | New office nodes/codes may be added without inference |
| PAE portfolio mappings | Official source that directly maps PMWs/offices to capability portfolios | Interpretations can become direct relationships |
| Unknown org effective dates | Official dated realignment or change-of-command source | `effective_from` / `effective_to` can be `documented` rather than `unknown` |
| Unresolved / ambiguous requirement attribution | Explicit program-office wording on the action, or a corroborating identifier chain | Class can move to `directly_documented` or a supported `inferred` result |

Until that evidence exists: do not invent office inventories, PE→contract maps, effective
dates, or ownership from contracting/funding identity or title similarity.

**Current T05 state.** This branch does not close T05. Against `tasks/T05_source_gaps.md` and
the later research already in the repo:

- Complete: item 2 (earlier NAVWAR LRAE / 2024 release recovered under `datapack/`); item 3
  (FY2026 FPDS rescan for N00039, monthly windows through June 2026); item 6 (NAVSEA
  enterprise LRAE current-location pointer recorded); item 7 (PEO Digital and PEO MLB pages
  checked; no office-code inventory published; gap recorded).
- Still actionable: item 1 (FY2021 SAM.gov archive for BT05 / `N0003921R3015`); item 4
  (RDT&E PE marks from the House FY2027 report PDF of `CRPT-119hrpt715`).
- Blocked: item 5 (DoN exhibit narratives: `RDTEN_BA7-8_Book.pdf` and FY2026 books; host
  refuses non-US and hosted-browser requests in the tested environment).

## 9. Update and Review Rules

This file is a navigation summary. It is not a second copy of the registry, the manifest, or
the organization graph. Change the structured authority first when a fact changes; then update
this map so it still matches.

### 9.1 Which Artifact Is Authoritative

| Question | Authoritative artifact |
| --- | --- |
| What sources exist / source metadata | `research/source_registry.json` |
| What exact bytes were retrieved / when / how | `research/documents_manifest.jsonl` |
| How identifiers and data sources connect in detail | `research/03_data_connection_map.md` |
| How to collect / reproduce sources manually | `research/09_manual_collection_runbook.md` |
| Current organization-memory claims and observations | `research/organization_seed.json` |
| Office/code normalization families | `research/org_code_families.json` |
| Contact source facts | `research/contact_observations.json` |
| Contact recommendations | `research/contact_recommendations.json` |
| Review/check history | `research/review_log.json` |
| Human-readable overview / source map | `research/10_navy_sources_map.md` |

If this Markdown disagrees with one of the structured authorities, update the structured
authority first and then correct this file. Do not treat this Markdown as the machine-readable
source of truth, and do not use it as the only provenance record for a research claim.

Related attribution examples and process live in `research/04_attribution_process_and_examples.md`
and `research/attribution_examples.json`. They are the authority for evidence-class examples;
this map only restates the join and class rules at a glance.

### 9.2 Adding a New Source

Do not add a source here before `research/source_registry.json` knows about it. Inspect it by
hand before automating it.

1. Inspect the source manually (official public source only).
2. Decide what lifecycle stage and question it supports.
3. Record it in `research/source_registry.json`.
4. Retrieve it through the existing collection path where appropriate (`research/tools/fetch.py`,
   Wayback, hosted browser, or `research/tools/sam_notices.py`).
5. Ensure `research/documents_manifest.jsonl` records the retrieval or the unsuccessful attempt
   (including firewall stubs).
6. Document what the source can and cannot prove (in the registry first).
7. Add it to this Markdown, matching the registry status.
8. Update `research/03_data_connection_map.md` or `research/09_manual_collection_runbook.md`
   only if the new source changes joins or the collection procedure.
9. Add tests only when the new structured contract requires validation. A prose-only addition
   to this file does not require a test.

### 9.3 Updating an Existing Source

When a URL, access method, page/file, release, or access status changes:

- Write a new manifest row for the new retrieval or version. Do not rewrite historical
  retrieval rows.
- Preserve old observations that remain historically valid. A new page does not erase what an
  earlier dated capture stated.
- Update `verification_status` / access notes in `research/source_registry.json` when the
  current access picture changes (`verified`, `blocked`, `restricted`, `not_inspected` stay
  distinct).
- If a previously blocked source becomes usable, record the successful retrieval as a new
  manifest row and then change the registry status. Keep the earlier blocked attempts.
- Update this Markdown only after the structured source metadata has changed.

A new release does not automatically invalidate the old one. Historical versions remain
necessary for backtests and for dated organization reasoning. Diff the releases; do not
replace them.

### 9.4 Changing a Join or Attribution Rule

Adding a source is not the same as changing how sources relate.

- A new LRAE release (or a new SAM archive year) is new source/version evidence. Record it
  through 9.2 / 9.3.
- Deciding that a new identifier can deterministically join two systems is a methodology
  change.
- Moving a PMW mapping from `inferred` to `directly_documented` is an attribution change. It
  needs a source that actually states the connection.

For methodology or attribution changes:

1. Require repository evidence (quoted official text or an exact shared identifier).
2. Update the detailed docs first (`research/03_data_connection_map.md`,
   `research/04_attribution_process_and_examples.md`, and `research/attribution_examples.json`
   when an example class changes).
3. Update structured artifacts where the rule is encoded (`organization_seed.json`,
   `org_code_families.json`, datapack joins).
4. Update tests if a machine-readable rule changed.
5. Then update this summary.

Do not let this Markdown be the only place a join or evidence-class rule changes.

### 9.5 Handling Retractions and Corrections

A research error is not a real-world organization change.

- If an earlier research claim was wrong, retract or correct it in the structured artifact
  that holds the claim (`organization_seed.json` for org relationships; contact files for
  contact facts; attribution examples for ownership classes). Keep the record, with a reason
  and a pointer to what replaces it.
- Do not assign a historical end date to hide a mistake.
- If the real world changed, add a dated observation and update the relationship’s status
  (`ended`, `superseded`, or `conflicting`) from that source. That is separate from a
  retraction.
- If only this Markdown is wrong, fix the summary after checking that the structured
  authority was not also affected.

### 9.6 Review Checklist

For an edit to this Markdown:

- [ ] Source exists in `research/source_registry.json`
- [ ] Verification/access status matches the registry
- [ ] Relevant retrieval is represented in `research/documents_manifest.jsonl` where applicable
- [ ] “Can establish” claims do not exceed what the source actually states
- [ ] “Cannot establish” limitations remain explicit
- [ ] Contracting/funding identity is not presented as requirement ownership
- [ ] Inferred joins are not described as deterministic
- [ ] Observation/capture date is not presented as a real-world effective date without evidence
- [ ] Historical source versions are not silently overwritten
- [ ] `blocked` / `restricted` / `not_inspected` statuses remain distinct
- [ ] New office/code claims are supported by official evidence
- [ ] Open gaps remain visible
- [ ] Related structured artifact was updated first if the underlying fact changed
- [ ] No private contact data, paid enrichment, customer data, production credentials, or
      guessed emails were introduced

Keep this file short enough to scan. Detailed evidence belongs in the structured artifacts
and the existing research docs. When the source landscape changes, update the underlying
evidence first, then this map.
