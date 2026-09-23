# Three uses of the data, walked on Navy examples

The agency intelligence answers three questions from one data set, with evidence on every
connection and a candidate, not a guess, wherever a connection is ambiguous: find a requirement
before it is solicited; start from an active notice and reach the office that owns it; read what
was solicited, awarded and funded in the past. This document walks one Navy example through each
(two through the second), then checks every June 2025 forecast line whose solicitation window has
arrived for a notice or an award. Estimates, ceilings and obligations stay in separate columns
throughout.

Everything below is reproducible offline from the saved bytes. The tool is
`research/tools/trace.py`; every lookup made for this document is a row in
`research/sources/documents_manifest.jsonl` with the note `use-case walkthrough`.

```
python research/tools/lrae_package.py build                 # datapack/ from the saved spreadsheets
python research/tools/agency_layers_sql.py > /tmp/layers.sql
psql "$DSN" -f /tmp/layers.sql                              # an empty database carrying main's migrations
python research/tools/trace.py --dsn "$DSN" status          # every FY26-or-earlier line: solicited? awarded?
python research/tools/trace.py --dsn "$DSN" need   N00039-25-RFPREQ-PMW/A-170-0001
python research/tools/trace.py --dsn "$DSN" notice f69d6c525c9f494fa08ea8fd852f5cdd
python research/tools/trace.py --dsn "$DSN" notice e24dd802a17a40f3ba9192ebf4af7fd3
python research/tools/trace.py --dsn "$DSN" award  N0003922F3000
```

The examples depend on two points about the source records:

- **A spreadsheet row is a source record.** The June 2024 release has no PID column. Rows 406
  and 408-411 all read "Order to Contract #N0003922D4001" under PMA/PMW-101 and describe a Lot 7
  order, terminal destruction, terminal shipment, a French MIS buy and a feasibility study. A row
  without a PID is its own record (release and row number), nothing is marked duplicate, a PID
  that repeats within one release stops the build, and the reconciliation lists rows sharing a
  title under one office with what tells them apart.
- **Two office changes the notices state.** NAVWAR notices of August 2026
  name the "Tactical Data Link (TDL) Program Office (PMW-530) (formerly MIDS Program Office (MPO)
  (PMA/W-101))"; a May 2026 notice places PMW/A 170 under "PAE Mission Systems - Capability
  Portfolio Executive (CPE): Comms, Sensor, Electronic Warfare (EW), and Positioning, Navigation,
  and Timing (PNT) (previously PEO C4I ...)". Both are observations (`obs:080`-`obs:085`) with
  aliases and dated relationships (`rel:065`, `rel:066`; `rel:011` ended), and one interpretation
  (`int:006`). Neither redesignation date is stated by a source; the PAE stand-up date is used as
  a convention and marked inferred.

Four rules hold in the tool and in this document:

- **A negative names the records searched and their date.** "No award found in the saved FPDS
  lookup", with the lookup's retrieval date, is what the saved bytes support; "nothing awarded"
  is not, and the tool never prints it. `trace.py status` prints the retrieval range of the
  searches it read.
- **Every connection carries its source.** The SAM.gov link and the saved record (URL, retrieval
  date, hash) for a notice; the spreadsheet row and the release's URL for a forecast line; the
  FPDS or USAspending record behind every ceiling and obligation; the observation ids, dates and
  URLs behind every office name, parent and reorganization. The loader writes the source
  URL onto every office, edge and spreadsheet-row evidence it inserts.
- **The same requirement is kept apart from a related buy in the same program.** Two titles
  stating different lots, families or generations (SF2 and SF3; Services II and III) are
  reported as *related procurements*, never as candidates for one another. SF2 is context for
  SF3 and stays a distinct buy.
- **A reorganization is reported at the level its source documents.** The May 2026 release
  consolidated PEO C4I's "mission systems elements" into PAE Mission Systems and itemized no
  offices. An office is placed under a PAE portfolio only when its own source says so (PMW/A 170,
  notice of 2026-05-22); otherwise the tool prints the PEO-level succession, the scope wording
  and the office's own parent claim with the date it was last confirmed.

---

## 1. A requirement before solicitation: the NTCDL follow-on (PMW/A 170)

**The line.** `N00039-25-RFPREQ-PMW/A-170-0001`, "NTCDL - Follow-On Production and ESS Contract".
Followed across all three releases:

| release | row (sha) | matched by | solicitation | award | value as stated | office | method |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2023-06-20 | `LRAE Annex 25` row 409 (48ad6e27241a) | PID | blank | FY27 Q1 | $250M - $1B | PMW/A-170 | - |
| 2024-06-20 | row 47 (c327bcd3a34a) | title + office (confirmed; loads under the PID, basis `inferred`) | TBD | FY25 Q3 | $250M - $1B | PMW/A-170 | Full and Open |
| 2025-06-19 | row 108 (697ec8c004d2) | PID | FY26 Q2 | FY27 Q2 | $250M - $1B | PMW/A-170 | Full and Open, single-award IDIQ, follow-on to N0003916C0087 (BAE) |

The award window moved FY27 Q1 -> FY25 Q3 -> FY27 Q2. The 2024 row has no PID and is tied to the
others by exact title under the same office code; the diff records that basis, and the loader
writes the row under the same need with basis `inferred` and the tie in the assertion's
rationale, so `gov_requirement_revisions` holds all three releases.

**The office and its history.** The 2025 release names PMW/A 170. The loaded ancestry reads
PMW/A 170 -> PAE Mission Systems CPE Comms, Sensor, EW and PNT -> PAE Mission Systems ->
Department of the Navy, with the former parentage kept as a dated row: PMW/A 170 under PEO C4I
until 2026-05-10 (`rel:011`, end inferred from the PAE stand-up; the 2026-02-10 RFI still said
PEO C4I, the 2026-05-22 presolicitation said "previously PEO C4I"). NAVWAR HQ (N00039) contracts
for the office (`rel:012`).

**The incumbent, with money kept apart** (USAspending, sha 22b17bac280d):

| | |
| --- | --- |
| N0003916C0087 | BAE Systems; definitive contract; solicitation N0003914R0001, full and open, 3 offers; signed 2016-09-21 |
| period of performance | 2017-09-29 -> 2028-09-29 (last modified 2026-05-20) |
| ceiling (base and all options) | $309,287,636 |
| obligated to date | $302,467,639 |
| forecast estimate for the follow-on | $250M - $1B in every release; not a ceiling, not an obligation |

The three-year extension the LRAE listed separately ("NTCDL - 3-Yr Contract Extension", 2023
row 412 / 2024 row 460) is the sole-source modification P00078 of 2024-10-31 for $84,971,820,
posted as an award notice on 2024-11-05 under N00039-23-R-2005. It sits under the incumbent's
ceiling above; it is not a new award.

**What the public record shows for the forecast window (FY26 Q2 = January-March 2026).**

| date | what | who it names | source |
| --- | --- | --- | --- |
| 2013-03-04 | RFI, then 2016-09-22 award notice | NAVWAR | SAM.gov N00039-14-R-0001 |
| 2021-08-19 | Sources Sought "NTCDL Scalable Surface Terminal Technologies", an overarching CDL solution for all Navy LOS ISR | PEO C4I, PMW/A 170 | SAM.gov bda6b614... |
| 2023-05-10 -> 2024-11-05 | intent, then award, of the sole-source extension | PEO C4I | N00039-23-R-2005 |
| 2026-02-10 | Sources Sought "NTCDL Engineering Support Services - RFI" (ESS and spares) | PEO C4I, PMW/A 170 | NAVWAR_HQCA_2026_A_005 |
| 2026-05-22 | Presolicitation: sole-source five-year single-award IDIQ for NTCDL ESS and spares to BAE | PAE MS CPE Comms/Sensor/EW/PNT, "previously PEO C4I, PMW/A 170" | N0003926RB002 |
| | no award found under N0003926RB002 in the saved FPDS lookup; incumbent actions P00098 (2025-11-12, $65,000) and P00099 (2025-12-08, $0) | | FPDS |

No full-and-open production solicitation appears in the saved SAM.gov searches for "NTCDL" or
"Network Tactical Common Data Link". What appeared in the forecast window was an
RFI and then a sole-source carve-out of the engineering-support half. The LRAE also carries
`N00039-25-RFPREQ-PMW/A-170-0276`, "NTCDL - Stand Alone Bridge Contract" (sole source,
single-award IDIQ, $7.5M - $50M, solicitation FY26 Q1, award FY26 Q3), which fits the ESS
presolicitation better than the follow-on line does. The tool reports the presolicitation as a
**candidate** for both lines (shared program token `ntcdl`, same office) and does not pick one;
the bridge line is the natural first reading.

**Reading.** No solicitation of the production follow-on appears in the searched records (the
saved SAM.gov searches). The incumbent runs to September 2028 with
$6.8M of ceiling headroom (its own ceiling less its own obligations), the engineering support is
being placed sole-source, and the award window has already moved twice. Budget line: OPN line
item 2950, Network Tactical Common Data Link. Earliest signals came five
years (2021 RFI) and three years (2013 RFI -> 2016 award) ahead of the buys they preceded.

**Watch.** This is the forward-looking example: a requirement to follow now, before its RFP.
`trace.py need N00039-25-RFPREQ-PMW/A-170-0001` ends with a `Watch` block read from the rows
above; the tool asserts nothing new there.

| | |
| --- | --- |
| reads as | `review`: the award notice of 2024-11-05 is an action on the incumbent after the line appeared (does the follow-on still stand?); also `restructured`: the bridge line `-0276` first appears in June 2025 beside it; also `delayed`: window closed, award window moved FY27 Q1 -> FY25 Q3 -> FY27 Q2; the ESS presolicitation stays a candidate |
| where it stands | solicitation window FY26 Q2 (January to March 2026) closed with no solicitation of the line in the saved searches; award window FY27 Q2 |
| why it matters | $250M - $1B as stated, full and open, single-award IDIQ, follow-on to N0003916C0087 (BAE); the incumbent ends 2028-09-29 with $6.8M of headroom, so a production vehicle has to exist before then or the incumbent has to be extended again |
| what is on the record | the ESS sole-source presolicitation N0003926RB002 (2026-05-22) as a candidate; the sibling bridge line `-0276` (sol FY26 Q1) sharing the program name |
| would confirm | a solicitation-stage notice carrying the PID or N0003916C0087; a solicitation-stage notice whose title carries `NTCDL` and names PMW/A 170 or its portfolio; an FPDS or USAspending action under a new solicitation number naming N0003916C0087 as predecessor; the next LRAE release keeping the line with an unchanged or nearer window |
| would invalidate | a J&A, extension or modification carrying N0003916C0087 past 2028-09-29; the next LRAE release dropping the line or folding it into `-0276`; an award under N0003926RB002 whose description covers production |
| how to re-check | `sam_notices.py ntcdl`; `fetch.py` on the USAspending award and the FPDS PIID feed for N0003916C0087 (the block prints the three commands) |

---

## 2. An active notice traced to its office: MIDS WDL SF3 (TDL Program Office, PMW-530)

**The notice.** Presolicitation `N00039PRESOL_SF3`, posted 2026-08-12, active: NAVWAR "in support
of the Tactical Data Link (TDL) Program Office (formerly Multifunctional Information Distribution
(MIDS) Program Office (MPO))" plans a full-and-open RFP in FY26 Q4 for 100 NSA-certified MIDS WDL
SWARMM Family 3 radios, single award, 24 months; an RFI ran in August 2025
(`MIDS-SWARMM-FAMILY-3`).

**The office, explicitly.** The text names the office. Two sibling notices a week later spell out
the code: the SF1 ceiling-increase notice (2026-08-19, contract N0003923D4000 with L3 T&RF) and
the JTRS ceiling-increase notice (2026-08-27, contract N0003924D4004 with Data Link Solutions)
both read "Tactical Data Link (TDL) Program Office (PMW-530) (formerly ... (PMA/W-101))". The
organization memory carries the new name and code as aliases of `pmw:101` resting on those
three observations; the redesignation date is not stated and is recorded as unknown. Resolved
ancestry: PMA/PMW 101 -> PEO C4I (`rel:001`, last confirmed 2026-04-12 by the PEO C4I site).
PEO C4I's mission-systems elements were consolidated into PAE Mission Systems from 2026-05-11
(`rel:045`); the release does not itemize which offices moved, and no source places PMW-530
under a PAE portfolio, so the office's placement after the consolidation is not established and
the tool says so rather than drawing the PEO's successor onto the office. Contracting office
N00039 (`rel:002`).

**The surrounding history, from the saved notices and awards.**

| family | notices | award | ceiling | obligated |
| --- | --- | --- | --- | --- |
| SF1 | award 2023-05-05, ceiling increase noticed 2026-08-19 | N0003923D4000, L3, single award, not competed | $84,950,000 | $0 at the vehicle |
| SF2 | RFI 2024-01-17; presol N0003924R4100 2024-07-30; RFP 2024-08-30 | N0003925D4006 (Rockwell Collins) and N0003925D4007 (L3), signed 2025-09-29, full and open, 2 offers each | $939,600,000 each | $0 at the vehicles; first orders 2025-09-29 F4056 $57,152,766 and F4057 $42,123,914; FY26 orders F4006 (ceiling $82,061,677, obligated $3,083,496) and F4007 (ceiling $87,575,256, obligated $233,428) |
| SF3 | RFI 2025-08-28; presolicitation 2026-08-12 (this notice) | no solicitation number issued (the presolicitation carries a placeholder), so no FPDS lookup exists; no award found in the searched records | | |
| SF4 | RFIs 2025-05-14 and 2026-07-29 | no solicitation; no award found in the searched records | | |

**The forecast.** No LRAE line for SF3 exists in the June 2025 release; the forecast is behind
the notice stream here. The SF2 line does
exist: `N00039-24-RFPREQ-PEO-C4I-0012`, "MIDS WDL SF2 Production", solicitation FY24 Q4, award
FY25 Q4, $250M - $1B, filed under `C4IEXEC`, the PEO C4I front-office code, not PMA/PMW-101. The
SF2 award landed 2025-09-29, in the forecast quarter. The tool lists the SF2 line against the SF3
notice as a **related procurement in the same program**, not as a candidate for the same
requirement: the titles state different generations (SF2 against SF3), so they are distinct buys,
and SF2 is context for SF3 (what the family's last competition looked like) rather than its
forecast. The office question travels with it: the notices name PMW-530 while the LRAE files the
family under the front office. The SF2 line's own candidates are the SF2 presolicitation and RFP
of 2024 under N0003924R4100, with the two awards of 2025-09-29 under that number.

**Reading.** The office is documented, not inferred. The value the notice implies is a ceiling
to be set at award; the SF2 vehicles show what that looked like a year earlier ($939.6M ceiling
each, $99M placed on day one). The LRAE's estimate for SF2 was $250M - $1B.

---

## 2b. A second notice, this one an RFP already out: Egyptian Navy AINTS (PMW 740)

**The notice.** Solicitation `N0003926RE014`, posted 2026-09-17, proposals due 2026-10-20: NAVWAR HQ
"in support of the Program Executive Office (PEO) Command, Control, Communications, Computers, and
Intelligence (C4I) International Integration Program Office (PMW 740)" issues the RFP for Autonomous
INTelligence System (AINTS) platform integration for the Egyptian Navy under FMS case EG-P-LGQ: a new
requirement, full and open, three-year period, CPFF labour with FFP material, award "estimated between
June 2027 - June 2030". The SOW is CUI behind an NDA, so nothing of the requirement's content is public
beyond that paragraph. The presolicitation of 2026-07-31 (`64f0d3726ec2`) carried the same text.

**The office, explicitly.** The text names PMW 740 and the memory resolves it on the alias `PMW 740`:
PMW 740 International C4I Integration Program Office -> PEO C4I (`rel:013`). PEO C4I's mission-systems
elements were consolidated into PAE Mission Systems from 2026-05-11 (`rel:045`), a PEO-level fact the tool
prints with the release's scope wording and without placing PMW 740 under any PAE portfolio; contracting
office N00039 (`rel:014`). Both notices are recorded as
observations (`obs:086`, `obs:087`) and they state that in July and September 2026, four months after
PAE Mission Systems stood up, NAVWAR still writes PEO C4I as PMW 740's parent. `rel:013` (PMW 740 under
PEO C4I) is therefore last confirmed 2026-09-17, no source places
PMW 740 under a PAE portfolio, and the PAE succession is read at the PEO level only. Compare PMW/A 170,
whose May 2026 notice did move it under a CPE (section 1).

**The trail, from the saved notices.**

| date | what | office named | source |
| --- | --- | --- | --- |
| 2025-02-27 | Sources Sought "N0003925R4011 - Egypt A2": RFI for Egyptian Navy AINTS Platform Integration, full-and-open RFP intended, SOW CUI under NDA, responses due 2025-04-01 | NAVWAR, no office | SAM.gov b4459cf9c745 |
| 2026-07-31 | Presolicitation N0003926RE014 | PEO C4I, PMW 740 | SAM.gov 64f0d3726ec2 |
| 2026-09-17 | Solicitation N0003926RE014, proposals due 2026-10-20 | PEO C4I, PMW 740 | SAM.gov e24dd802a17a |
| | no award found under N0003926RE014 or N0003925R4011 in the saved FPDS lookups | | FPDS |

The RFI's title is a number and "Egypt A2"; the program name is only in its body. The tool also
reads a saved notice's text for a rare program name from the traced title (`aints` occurs in one
forecast line), which is how the RFI joins the trail.

**The forecast.** `N00039-23-RFPREQ-PMW-740-0070`, "EGYPTIAN Navy AINTS (EG-P-LGQ, A2) (C)": PMW-740,
full and open, "C" type, cost-reimbursement, $100M - $250M, solicitation FY25 Q3, award FY26 Q2, 36
months, San Diego, NAICS 334511. Its PID says the record was opened in the FY23 cycle, but neither the
June 2023 nor the June 2024 release carries the title, the PID or an incumbent; its first public
appearance is the June 2025 release (row 10), four months after the RFI. The tool reports the notice
against this line as a **candidate** (shared program token `aints`, same office) and stops there: same
office, same case letters in the title, same NAICS, same three-year term, but no PID or contract number
in the notice text ties them explicitly. It is the natural reading.

**Forecast against record, if the match is accepted.**

| | forecast (June 2025) | record |
| --- | --- | --- |
| solicitation | FY25 Q3 (Apr-Jun 2025) | RFI 2025-02-27; presolicitation 2026-07-31; RFP 2026-09-17, five quarters late |
| award | FY26 Q2 (Jan-Mar 2026) | notice says June 2027 - June 2030, FY27 Q3 at the earliest; no award found in the searched FPDS records |
| value | estimate $100M - $250M | no ceiling (set at award); no obligations |

**Reading.** An open RFP, traced to a named office, with the RFI nineteen months ahead of
it. Here the notice stream led the forecast: the RFI was public before the line was. Money: one number
exists (the estimate) and it sits alone in its column. The Egypt maritime surveillance award of
2025-02-21 that the same search surfaced (NMSS, N00024-25-C-5310, $96.5M to Forward Slope) is a NAVSEA
action, not PMW 740's, and the tool does not attach it.

---

## 2c. A notice with no forecast line: the requirement is created from the notice

A requirement opens from more of an agency's signal than the forecast row: an RFI, an RFP, a
recompete, an industry day. The tool and the loader take a SAM.gov notice of any type as an entry
point (`trace.py notice`), and a contract as another (`trace.py award`, which closes with a recompete
reading). The rule for a notice:

- **One requirement per solicitation number.** Every notice under the number (RFI, presolicitation, RFP,
  amendment, award notice) is a dated revision of it; the latest is live. A notice with no number is its
  own record.
- **Resolved to a forecast line only when the line names it.** Exactly one line of the latest release
  carries the notice's PID, or its title carries the notice's solicitation number (basis documented), or
  it alone cites an incumbent contract the notice names, on a solicitation-stage notice posted after the
  line first appeared (basis inferred). Then the notice's revisions chain after the line's forecast
  revisions. A shared program name is a candidate and never resolves; two lines claiming one notice leave
  it its own record. Nothing is forced and no forecast row is invented.
- **The office is the one the text names**, through the alias table, taking the most specific current
  office (a text naming "PEO C4I ... PMW 740" names PMW 740); a text naming two branches asserts none.
  The organization SAM.gov posted the notice under is the contracting office.
- **A notice from another command** that names no office the memory knows is not this agency's need;
  it is counted on stderr and not loaded.
- **Related notices** (same title stem, a rare program name in the text) are printed with the offices
  they name, a candidate for the notice's office when the notice names none, and with the awards under
  their solicitation numbers: the program's earlier buys, context for this requirement.

Signal kinds as they enter:

| signal | entry | what is recorded |
| --- | --- | --- |
| forecast row (LRAE) | `need <PID>` | one need per record key, a revision per release |
| request for information / sources sought | `notice <id>` | requirement (lifecycle identified), office named, contracting office |
| presolicitation; solicitation (RFP, RFQ, combined synopsis); area of interest under a CSO | `notice <id>` | requirement (planned / in procurement), a revision per notice under the number |
| special notice: industry day, action on an existing contract, CSO, forecast posting | `notice <id>` | requirement (identified); the industry day joins the office's stream |
| justification; award notice | `notice <id>` | requirement (in procurement / fulfilled) |
| contract (recompete) | `award <PIID>` | end of performance against today, forecast rows naming it as incumbent, solicitation-stage notices citing it after the line appeared |

Three NAVWAR notices absent from every saved LRAE release, each started from its notice id alone:

**Clear attribution: MUSV Phase II Integration and Testing, presolicitation `N0003926RR002`, 2026-09-08
(`8fc40452`).** The text states the office: "The Department of the Navy Direct Reporting Portfolio Manager
(DRPM) / Portfolio Acquisition Executive (PAE) for Robotics and Autonomous Systems (RAS) hereby issues
this announcement". The office is `drpm:ras`, resting on the wording of this notice, the sibling MUSV
High-Capacity announcement (`N0003926RR001`, 2026-09-08, "a Portfolio Acquisition Executive (PAE) for Robotic and Autonomous Systems (RAS) announcement", no longer active) and the DRPM RAS
Industry Day special notice (2026-09-10, an industry day on 2026-09-24 "on the establishment of the DRPM"
naming the "Medium Unmanned Surface Vessel Phase II Request for Proposal" as forthcoming): `obs:088`-
`obs:091`, `rel:067` (under the Department of the Navy; dates unknown, since no source states when the
DRPM stood up), `rel:068` (NAVWAR HQ contracts for it; the SAM.gov organization on the notice is N00039).
The requirement loads as `notice:N0003926RR002` with the owner and the contracting office asserted. History
reached through the related notices: the MUSV RFP of 2020-07-20 (`N0002419R6302`, NAVSEA) and its award
`N0002420C6312` to L3 Technologies, signed 2020-07-13, ceiling $281,435,446 at award ($283,212,770 as
modified), obligated $58,655,312, period of performance 2020-07-13 to 2026-07-13, awarding office NAVSEA HQ,
full and open with five offers. No award under `N0003926RR002` or `N0003926RR001` in the saved FPDS
lookups. Reading: the MUSV program's contracting moved from NAVSEA HQ to NAVWAR HQ with the new
portfolio; the Phase I contract ended 57 days before the Phase II announcement.

**Ambiguous attribution: Next Generation Surveillance Array, solicitation `N0003926RE017`, 2026-07-27
(`d957eb7c`).** A passive towed array for SURTASS host platforms; the full RFP is CUI and CTI behind an NDA.
The text names NAVWAR and no office. Two RFIs under other numbers, 2023-08-08 (`MKTSVY_1948B2`) and
2024-12-12 (`MKTSVY_19DC4A`), name "the Program Executive Office, Undersea Warfare Systems (PEO UWS),
Maritime Surveillance Systems Program Office (PMS 485)". The tool lists PMS 485 as named by the related
notices, a candidate for the office, and asserts no owner on the solicitation; the requirement loads with
the contracting office only. PMS 485's own parent claim is in flux in the memory (PEO Submarines in the
2019 SURTASS notices, PEO UWS in the 2025 notices; `rel:060`, realignment date unknown), which is a second
reason not to draw a PEO onto this notice. Budget line: OPN 2237 SURTASS (P-1 line 45), office by
inference. No LRAE release carries NGSA (PMS 485 has other rows). No award in the saved FPDS lookup.

**Limited history: Expeditionary Very Low Frequency (ExVLF) Transmitter System, `N0003926RB004`,
2026-08-11 (`899c8727`).** An area of interest under the NAVWAR Commercial Solutions Opening
`N0003925S0001` (posted 2025-06-04 per the text): white papers, then pitches, then a prototype other
transaction agreement with a possible follow-on production award without further competition. Some 22,000
characters of text name no program office, portfolio or PEO. No earlier notice shares the title or a rare
program name; the "Very Low Frequency" searches return NAVFAC tower work of 2012-2014 and an Air Force NC3
RFI of 2026, none of them this program. No LRAE release carries a VLF line; no incumbent contract is
cited. The requirement loads as `notice:N0003926RB004` with the contracting office only, and every
negative names the search and its date.

The AINTS RFP, the MIDS-LVT presolicitation and the NTCDL ESS presolicitation keep their own records
beside the lines they may be.

---

## 3. What was solicited, awarded and funded: PMW 160 engineering support services

Three generations of one requirement, each a task order on a SeaPort vehicle, each attributed to
PMW 160 by the award's own description (`EX02`, `EX01`; the 2026 order's description names the
office the same way).

| | N0003917F3000 | N0003922F3000 | N0003926FG001 |
| --- | --- | --- | --- |
| solicitation | N0002415R3570 (SeaPort-e, 5 offers) | N0003921R3015 (SeaPort-NxG, 3 offers) | not stated; SeaPort-NxG order competition, 6 offers |
| signed | 2016-12-15 | 2021-10-26 | 2026-05-06 |
| period of performance | 2016-12-15 -> 2021-10-27 | 2021-10-27 -> 2026-10-26 | 2026-08-03 -> 2027-08-02 (potential 2032-02-02) |
| ceiling (base and all options) | $114,721,035 | $193,354,383 | $339,456,211 (exercised $57,045,726) |
| obligated to date | $111,338,289 | $188,936,333 | $21,545,079 |
| recipient | Booz Allen Hamilton | Booz Allen Hamilton | Booz Allen Hamilton |

**The forecast for the third.** June 2024 row 55 "PMW 160 Engineering Support Services (ESS)
Follow-on Contract": $100M - $250M, solicitation FY25 Q2, award FY26 Q3, follow-on to
N0017819D7264 (the SeaPort-NxG vehicle) with Booz Allen as incumbent. June 2025 row 128, PID
`N00039-24-RFPREQ-PMW-160-0002`: $250M - $1B, solicitation FY25 Q4, award FY26 Q3. The 2024 row
has no PID; the diff ties it to the 2025 row on office plus incumbent contract number (confirmed).
The award came 2026-05-06, inside the forecast quarter, at a ceiling of $339.5M against the
revised $250M - $1B estimate. The 2024 estimate ($100M - $250M) would have been low.

**Why there is no SAM.gov trail.** SeaPort-NxG order competitions are run on the vehicle, not
posted on SAM.gov; the saved searches on the PID and on the vehicle number return nothing, and
the tool says so rather than reporting a miss. The award appears in FPDS and USAspending only.
The tool finds N0003926FG001 from N0003922F3000 as a successor candidate (same parent vehicle,
same recipient, shared description words `tactical`, `networks`, `pmw`, `160`), and
N0003921F3003 as a predecessor candidate that a reader rejects (it is the PMW 120 order; the
shared words are `pmw` and `this`). Both are labelled candidates for exactly that reason.

**Two more awards the same check surfaced.** The MIDS-LVT recompete line
(`N00039-23-RFPREQ-PMA/PMW-101-0017`, solicitation FY25 Q3, award FY25 Q3, $250M - $1B) was
solicited 2025-04-09 under N00039-24-R-4019, in the forecast quarter, and awarded 2026-04-13,
four quarters late: N0003926DE001 (Data Link Solutions) and N0003926DE002 (L3), ceiling
$307,743,354 each, $0 obligated at award. The ADNS MAC line (`N00039-23-RFPREQ-PMW-160-0108`,
whose title carries the solicitation number N0003925R9510; solicitation FY25 Q4, award FY26 Q1)
was posted 2025-06-16 and awarded 2026-05-21/22 to five holders (Management Services Group,
Leidos, Serco, SESC, VT Milcom), ceiling $452,925,000 each, $0 obligated at award; the LRAE
lists nine "ADNS MAC RFP #n" order rows from FY26 Q1 to FY27 Q4, which are the order competitions
to come.

---

## 4. Have the forecast lines already been solicited or awarded?

`trace.py status` reads every included June 2025 line whose solicitation window is FY26 or
earlier (103 of 148) against the saved SAM.gov searches (by PID and by incumbent contract
number), the saved FPDS lookups (by solicitation number where a line or a notice carries one; by
incumbent PIID) and the reviewed attributions. Nothing is fetched live. Each reading opens with one
outcome word; states that also hold follow "also". The readings:

| reading | what it means |
| --- | --- |
| awarded | ADNS MAC: five IDVs under the solicitation number the line itself carries, signed 2026-05-21/22 |
| review | MIDS-LVT (J&A of 2023-11-28 on the incumbent vehicle, after the line first appeared) and the NTCDL follow-on (the sole-source modification of 2024-11-05): an action on the incumbent asks whether the follow-on still stands. Also the June 2024 rows with no row in June 2025, in their own table: awarded, folded into another line, or dropped |
| restructured | a line restates a value or an instrument between two stated values, or gains a sibling line in June 2025 that cites the same incumbent |
| delayed | the solicitation window closed with nothing in the saved searches (SeaPort and GSA order competitions are not posted on SAM.gov); where releases moved the award window the reading says so |
| open | the window runs to 2026-09-30 |
| with a candidate | appended to the reading, never promoted: MIDS WDL SF2, MIDS-LVT, the two NTCDL lines, the two RSNF lines, AINTS |

The NILE LLC 7M line reads `delayed`: its 2020 presolicitation and 2022 J&A cite the incumbent
vehicle and predate the line's first forecast appearance (June 2025), so they are the incumbent's
history, not the line's solicitation.

The candidate rows, with the basis the tool attaches to each:

| line | forecast | candidate notice | basis | awards under it |
| --- | --- | --- | --- | --- |
| MIDS WDL SF2 Production (peo:c4i) | sol FY24 Q4, award FY25 Q4 | presol 2024-07-30 and RFP 2024-08-30 under N0003924R4100 (the SF3 presolicitation of 2026-08-12 is listed as a related buy, not a candidate) | `mids`, `sf2`, `wdl` | N0003925D4006/D4007 2025-09-29 |
| MIDS-LVT IDIQ - New Contracts (pmw:101) | sol FY25 Q3, award FY25 Q3 | presol N00039-24-R-4019 2025-04-09 | `lvt`, `mids`; same office | N0003926DE001/DE002 2026-04-13 |
| NTCDL - Stand Alone Bridge Contract (pmw:170) | sol FY26 Q1, award FY26 Q3 | presol N0003926RB002 2026-05-22 | `ntcdl`; same office | no award found in the saved FPDS lookup |
| NTCDL - Follow-On Production and ESS (pmw:170) | sol FY26 Q2, award FY27 Q2 | the same presolicitation | `ntcdl`; same office; meanwhile the incumbent was extended (award notice 2024-11-05) | the same lookup: no award found |
| RSNF C4ISR Training Services III (pmw:740) | sol FY25 Q1, award FY25 Q4 | presol N0003925R4014 2025-04-30 | `rsnf` | |
| RSNF inKSA Support Services (pmw:740) | sol FY25 Q3, award FY26 Q1 | the same presolicitation | `rsnf` | |
| EGYPTIAN Navy AINTS (pmw:740) | sol FY25 Q3, award FY26 Q2 | RFI 2025-02-27; presol 2026-07-31; RFP N0003926RE014 2026-09-17 | `aints`; same office (section 2b) | no award found in the saved FPDS lookup |

A candidate is reported, never asserted: the reading names the shared token and the office
comparison so it can be accepted or rejected in one look. Two RSNF lines share one notice and
cannot both be it; that ambiguity is left standing. A notice for a different lot, family or
generation of the line's program is printed as `related:` in the notice column and never drives
the reading: the SF3 presolicitation is context for the SF2 line, not its solicitation.
