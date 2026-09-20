# Three uses of the data, walked on Navy examples

The reviewer asked for the agency intelligence to answer three questions from one data set,
with evidence on every connection and a candidate, not a guess, wherever a connection is
ambiguous: find a requirement before it is solicited; start from an active notice and reach
the office that owns it; read what was solicited, awarded and funded in the past. This document
walks one Navy example through each as far as the evidence allows (two through the second), then checks every June 2025
forecast line whose solicitation window has arrived for a notice or an award. Estimates,
ceilings and obligations stay in separate columns throughout.

Everything below is reproducible offline from the saved bytes. The tool is
`research/tools/trace.py`; every lookup made for this document is a row in
`research/documents_manifest.jsonl` with the note `use-case walkthrough`.

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

Two corrections were made first, because the examples depend on them:

- **A spreadsheet row is a source record.** The June 2024 release has no PID column and the
  package keyed its rows on a hash of title and office code. Rows 406 and 408-411 all read
  "Order to Contract #N0003922D4001" under PMA/PMW-101 and describe a Lot 7 order, terminal
  destruction, terminal shipment, a French MIS buy and a feasibility study; four were marked
  `duplicate` and never reached the layers. A row without a PID is now its own record
  (release and row number), nothing is marked duplicate, a PID that repeats within one release
  stops the build, and the reconciliation lists rows sharing a title under one office with what
  tells them apart. June 2024 goes from 154 to 160 included rows; the load from 410 to 416 needs.
- **Two office changes the notices state and the memory lacked.** NAVWAR notices of August 2026
  name the "Tactical Data Link (TDL) Program Office (PMW-530) (formerly MIDS Program Office (MPO)
  (PMA/W-101))"; a May 2026 notice places PMW/A 170 under "PAE Mission Systems - Capability
  Portfolio Executive (CPE): Comms, Sensor, Electronic Warfare (EW), and Positioning, Navigation,
  and Timing (PNT) (previously PEO C4I ...)". Both are now observations (`obs:080`-`obs:085`) with
  aliases and dated relationships (`rel:065`, `rel:066`; `rel:011` ended), and one interpretation
  (`int:006`). Neither redesignation date is stated by a source; the PAE stand-up date is used as
  a convention and marked inferred.

---

## 1. A requirement before solicitation: the NTCDL follow-on (PMW/A 170)

**The line.** `N00039-25-RFPREQ-PMW/A-170-0001`, "NTCDL - Follow-On Production and ESS Contract".
Followed across all three releases:

| release | row (sha) | matched by | solicitation | award | value as stated | office | method |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2023-06-20 | `LRAE Annex 25` row 409 (48ad6e27241a) | PID | blank | FY27 Q1 | $250M - $1B | PMW/A-170 | - |
| 2024-06-20 | row 47 (c327bcd3a34a) | title + office (confirmed) | TBD | FY25 Q3 | $250M - $1B | PMW/A-170 | Full and Open |
| 2025-06-19 | row 108 (697ec8c004d2) | PID | FY26 Q2 | FY27 Q2 | $250M - $1B | PMW/A-170 | Full and Open, single-award IDIQ, follow-on to N0003916C0087 (BAE) |

The award window moved FY27 Q1 -> FY25 Q3 -> FY27 Q2. The 2024 row has no PID and is tied to the
others by exact title under the same office code; the diff records that basis.

**The office and its history.** The 2025 release names PMW/A 170. Today the loaded ancestry reads
PMW/A 170 -> PAE Mission Systems CPE Comms, Sensor, EW and PNT -> PAE Mission Systems ->
Department of the Navy, with the former parentage kept as a dated row: PMW/A 170 under PEO C4I
until 2026-05-10 (`rel:011`, end inferred from the PAE stand-up; the 2026-02-10 RFI still said
PEO C4I, the 2026-05-22 presolicitation said "previously PEO C4I"). NAVWAR HQ (N00039) contracts
for the office (`rel:012`).

**The incumbent, with money kept apart** (USAspending 2026-09-20, sha 22b17bac280d):

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
| through 2026-09-20 | no award under N0003926RB002 in FPDS; incumbent actions P00098 (2025-11-12, $65,000) and P00099 (2025-12-08, $0) | | FPDS |

No full-and-open production solicitation appears in the saved SAM.gov searches for "NTCDL" or
"Network Tactical Common Data Link" as of 2026-09-20. What appeared in the forecast window was an
RFI and then a sole-source carve-out of the engineering-support half. The LRAE also carries
`N00039-25-RFPREQ-PMW/A-170-0276`, "NTCDL - Stand Alone Bridge Contract" (sole source,
single-award IDIQ, $7.5M - $50M, solicitation FY26 Q1, award FY26 Q3), which fits the ESS
presolicitation better than the follow-on line does. The tool reports the presolicitation as a
**candidate** for both lines (shared program token `ntcdl`, same office) and does not pick one;
that is a reviewer's call, and the bridge line is the natural first reading.

**Reading.** The production follow-on has not been solicited. The incumbent runs to September
2028 with $6.8M of ceiling headroom, the engineering support is being placed sole-source, and the
award window has already moved twice. Budget line: OPN line item 2950, Network Tactical Common
Data Link (see `05`, table 1a). Earliest signals came five years (2021 RFI) and three years (2013
RFI -> 2016 award) ahead of the buys they preceded.

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
organization memory now carries the new name and code as aliases of `pmw:101` resting on those
three observations; the redesignation date is not stated and is recorded as unknown. Resolved
ancestry: PMA/PMW 101 -> PEO C4I, succeeded by PAE Mission Systems from 2026-05-11 (`rel:045`).
Contracting office N00039 (`rel:002`).

**The surrounding history, from the saved notices and awards.**

| family | notices | award | ceiling | obligated |
| --- | --- | --- | --- | --- |
| SF1 | award 2023-05-05, ceiling increase noticed 2026-08-19 | N0003923D4000, L3, single award, not competed | $84,950,000 | $0 at the vehicle |
| SF2 | RFI 2024-01-17; presol N0003924R4100 2024-07-30; RFP 2024-08-30 | N0003925D4006 (Rockwell Collins) and N0003925D4007 (L3), signed 2025-09-29, full and open, 2 offers each | $939,600,000 each | $0 at the vehicles; first orders 2025-09-29 F4056 $57,152,766 and F4057 $42,123,914; FY26 orders F4006 (ceiling $82,061,677, obligated $3,083,496) and F4007 (ceiling $87,575,256, obligated $233,428) |
| SF3 | RFI 2025-08-28; presolicitation 2026-08-12 (this notice) | none yet | | |
| SF4 | RFIs 2025-05-14 and 2026-07-29 | none | | |

**The forecast.** No LRAE line for SF3 exists in the June 2025 release; the forecast is behind
the notice stream here, and the next LRAE release is where it should appear. The SF2 line does
exist: `N00039-24-RFPREQ-PEO-C4I-0012`, "MIDS WDL SF2 Production", solicitation FY24 Q4, award
FY25 Q4, $250M - $1B, filed under `C4IEXEC`, the PEO C4I front-office code, not PMA/PMW-101. The
SF2 award landed 2025-09-29, in the forecast quarter. The tool reports the SF3 notice against the
SF2 line as a **candidate** with two questions attached: the notices name PMW-530 while the LRAE
files the family under the front office (line filed under the notice office's parent code), and
SF3 is a later lot, not the same buy. Neither is resolved by the tool.

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
PMW 740 International C4I Integration Program Office -> PEO C4I, PEO C4I succeeded by PAE Mission Systems
from 2026-05-11 (`rel:045`); contracting office N00039 (`rel:014`). Both notices are recorded as
observations (`obs:086`, `obs:087`) and they say something the memory did not have: in July and
September 2026, four months after PAE Mission Systems stood up, NAVWAR still writes PEO C4I as PMW 740's
parent. `rel:013` (PMW 740 under PEO C4I) is therefore last confirmed 2026-09-17, no source yet places
PMW 740 under a PAE portfolio, and the PAE succession is read at the PEO level only. Compare PMW/A 170,
whose May 2026 notice did move it under a CPE (section 1).

**The trail, from the saved notices.**

| date | what | office named | source |
| --- | --- | --- | --- |
| 2025-02-27 | Sources Sought "N0003925R4011 - Egypt A2": RFI for Egyptian Navy AINTS Platform Integration, full-and-open RFP intended, SOW CUI under NDA, responses due 2025-04-01 | NAVWAR, no office | SAM.gov b4459cf9c745 |
| 2026-07-31 | Presolicitation N0003926RE014 | PEO C4I, PMW 740 | SAM.gov 64f0d3726ec2 |
| 2026-09-17 | Solicitation N0003926RE014, proposals due 2026-10-20 | PEO C4I, PMW 740 | SAM.gov e24dd802a17a |
| through 2026-09-20 | no award under N0003926RE014 or N0003925R4011 in FPDS | | FPDS |

The RFI's title is a number and "Egypt A2"; the program name is only in its body. The tool now also
reads a saved notice's text for a rare program name from the traced title (`aints` occurs in one
forecast line), which is how the RFI joins the trail; a notice whose detail was never harvested would
still be missed.

**The forecast.** `N00039-23-RFPREQ-PMW-740-0070`, "EGYPTIAN Navy AINTS (EG-P-LGQ, A2) (C)": PMW-740,
full and open, "C" type, cost-reimbursement, $100M - $250M, solicitation FY25 Q3, award FY26 Q2, 36
months, San Diego, NAICS 334511. Its PID says the record was opened in the FY23 cycle, but neither the
June 2023 nor the June 2024 release carries the title, the PID or an incumbent; its first public
appearance is the June 2025 release (row 10), four months after the RFI. The tool reports the notice
against this line as a **candidate** (shared program token `aints`, same office) and stops there: same
office, same case letters in the title, same NAICS, same three-year term, but no PID or contract number
in the notice text ties them explicitly. The reading is the reviewer's; it is the natural one.

**Forecast against record, if the match is accepted.**

| | forecast (June 2025) | record |
| --- | --- | --- |
| solicitation | FY25 Q3 (Apr-Jun 2025) | RFI 2025-02-27; presolicitation 2026-07-31; RFP 2026-09-17, five quarters late |
| award | FY26 Q2 (Jan-Mar 2026) | notice says June 2027 - June 2030, FY27 Q3 at the earliest; nothing awarded |
| value | estimate $100M - $250M | no ceiling yet (set at award); no obligations |

**Reading.** An RFP that is open today, traced to a named office, with the RFI nineteen months ahead of
it. Here the notice stream led the forecast: the RFI was public before the line was. Money: one number
exists (the estimate) and it sits alone in its column. The Egypt maritime surveillance award of
2025-02-21 that the same search surfaced (NMSS, N00024-25-C-5310, $96.5M to Forward Slope) is a NAVSEA
action, not PMW 740's, and the tool does not attach it.

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
incumbent PIID) and the reviewed attributions. Nothing is fetched live. Readings on 2026-09-20:

| reading | lines | what it means |
| --- | --- | --- |
| awarded | 1 | ADNS MAC: five IDVs under the solicitation number the line itself carries |
| solicited | 1 | NILE LLC 7M production: presolicitation and J&A on the incumbent vehicle |
| candidate | 7 | a solicitation-stage notice shares a rare program token with the line and names the same office, its parent, or no office the memory knows; two of these (MIDS-LVT, MIDS WDL SF2) have awards under the candidate's solicitation number |
| incumbent action noticed | 1 | an award notice for a modification of the incumbent, no follow-on solicitation |
| no public notice found | 93 | about half are delivery or task orders, whose SeaPort/GSA competitions are not posted on SAM.gov; the rest show only the incumbent's last action date, or nothing |

The candidate rows, with the basis the tool attaches to each:

| line | forecast | candidate notice | basis | awards under it |
| --- | --- | --- | --- | --- |
| MIDS WDL SF2 Production (peo:c4i) | sol FY24 Q4, award FY25 Q4 | RFP N0003924R4100 2024-08-30; presol SF3 2026-08-12 | `mids`, `wdl`; line filed under the notice office's parent code | N0003925D4006/D4007 2025-09-29 |
| MIDS-LVT IDIQ - New Contracts (pmw:101) | sol FY25 Q3, award FY25 Q3 | presol N00039-24-R-4019 2025-04-09 | `lvt`, `mids`; same office | N0003926DE001/DE002 2026-04-13 |
| NTCDL - Stand Alone Bridge Contract (pmw:170) | sol FY26 Q1, award FY26 Q3 | presol N0003926RB002 2026-05-22 | `ntcdl`; same office | none yet |
| NTCDL - Follow-On Production and ESS (pmw:170) | sol FY26 Q2, award FY27 Q2 | the same presolicitation | `ntcdl`; same office; meanwhile the incumbent was extended (award notice 2024-11-05) | none |
| RSNF C4ISR Training Services III (pmw:740) | sol FY25 Q1, award FY25 Q4 | presol N0003925R4014 2025-04-30 | `rsnf`; notice detail not saved | not collected |
| RSNF inKSA Support Services (pmw:740) | sol FY25 Q3, award FY26 Q1 | the same presolicitation | `rsnf`; notice detail not saved | not collected |
| EGYPTIAN Navy AINTS (pmw:740) | sol FY25 Q3, award FY26 Q2 | RFI 2025-02-27; presol 2026-07-31; RFP N0003926RE014 2026-09-17 | `aints`; same office (section 2b) | none as of 2026-09-20 |

A candidate is reported, never asserted: the reading names the shared token and the office
comparison so a reviewer can accept or reject it in one look. Two RSNF lines share one notice and
cannot both be it; that ambiguity is left standing.

**Coverage, stated plainly.** FPDS PIID lookups hold the first page of actions only, so the
"incumbent last action" column trusts USAspending's last-modified date and marks first-page-only
dates with `*`. The FPDS office scan of N00039 is complete October 2025 to June 2026 and partial
after; awards were checked by solicitation number, not by scanning every action. SAM.gov searches
were run on PIDs and incumbent contract numbers on 2026-09-16/17 and on the examples above today.

---

## 5. What the reviewer is asked to decide

1. The bridge line versus the follow-on line as the home of the NTCDL ESS sole-source
   presolicitation (section 1). The tool holds both as candidates.
2. Whether the SF2 forecast line, filed under the PEO C4I front-office code, belongs to the
   office the notices name (PMW-530, formerly PMA/PMW 101), and whether SF3 should be expected
   as a new line in the next LRAE release (section 2).
3. The PMW-530 redesignation: the aliases rest on three August 2026 notices; no source states
   when the office was renumbered. The node keeps the name production and the LRAE use.
4. `int:006`: that the CPE named in the May 2026 notice is the portfolio the PAE site lists as
   "Sensors, PNT, EW, & Communications Systems". High confidence, still an interpretation.
5. The seven candidate rows in section 4, and whether the RSNF notice detail should be harvested
   to settle which of the two lines it is.
6. The AINTS RFP against `N00039-23-RFPREQ-PMW-740-0070` (section 2b), and whether PMW 740 stays
   under PEO C4I while its own notices keep saying so.
7. Still open from `11`: a requirement that slips a fiscal year and changes value is reported as a
   slip only, because value chains are scoped to one fiscal period.
