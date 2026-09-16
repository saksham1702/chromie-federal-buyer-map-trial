# 05 - Requirements before solicitation: current signals and backtests

Written 2026-09-16. Machine-readable backtests: `backtests.json` (each with a cutoff date, the
evidence available by that date, the prediction, the actual event, and the comparison). The
validator refuses any evidence item dated after its cutoff.

## In plain terms

For NAVWAR's program offices the earliest public warning of a purchase is usually not a notice.
It is one of three things: the office's own forecast spreadsheet (which names the office, the
incumbent contract and the quarter), the end date of the incumbent contract (which has been
public since the day that contract was awarded), or a budget line moving. In the six cases tested,
the forecast and the incumbent's end date predicted two recompetes to the quarter and one to the
day; two forecasts did not materialize in the window; one is still pending. Solicitation notices
themselves were absent for the SeaPort-NxG task orders, because those competitions run inside the
vehicle, not on SAM.gov.

## 1. Current early signals for the pilot portfolio

Each row follows the brief: what may be needed and why, the likely office, the earliest dated
evidence, funding status and timing, uncertainty, and the event that would confirm or invalidate
it. Evidence tags: LRAE = NAVWAR Long-Range Acquisition Estimate released 2025-06-19; OPN = FY2027
Other Procurement, Navy BA2 justification book dated April 2026; FPDS = award records observed
2026-09-16; DVIDS = release dated as shown.

| Potential requirement | Why it may be needed | Likely office | Earliest dated evidence | Funding and timing | Uncertainty | Confirms / invalidates |
| --- | --- | --- | --- | --- | --- | --- |
| NMT-X follow-on (Navy Multiband Terminal) | incumbent production contract N00039-16-C-0050 (Raytheon) ages out; SATCOM terminal recapitalization | PMW/A 170 | LRAE row PID N00039-22-RFPREQ-PMW/A-170-0021 (sole source, > $1B, solicitation FY24 Q1, award FY26 Q1) | OPN line item 3216 "Navy Multiband Terminal (NMT)" (P-1 line 79) funded through FY2027; award forecast for FY26 Q1 not yet observed in FPDS | sole-source J&A may not surface on SAM until award; lag ~90 days | a sole-source notice or an award to Raytheon confirms; a competitive SATCOM MAC award absorbing it invalidates |
| All SATCOM Multi Award Contract | consolidation of SATCOM buys across the office | PMW/A 170 | LRAE row PID N00039-23-RFPREQ-PMW/A-170-0173 (full and open, $250M-$1B, solicitation FY26 Q2, award FY27 Q2) | OPN line item 3215 "Satellite Communications Systems" | new vehicle, no incumbent; strategy could change under PAE Mission Systems | a sources-sought or RFP in FY26 Q2 confirms |
| NTCDL follow-on production and engineering support | incumbent N0003916C0087 (BAE) ends; common data link recapitalization | PMW/A 170 | LRAE row PID N00039-25-RFPREQ-PMW/A-170-0001 (full and open, $250M-$1B, solicitation FY26 Q2, award FY27 Q2); a "stand-alone bridge contract" row (FY26 Q1-Q3) signals a gap-filler | OPN line item 2950 "Network Tactical Common Data Link (CDL)" (P-1 line 68) | bridge row suggests the follow-on is slipping | the bridge award (FY26 Q3) confirms the slip; an RFP in FY26 Q2 confirms the plan |
| PRP FY27 follow-on | incumbent N0003922D0070 (L3Harris) ends | PMW/A 170 | LRAE row PID N00039-25-RFPREQ-PMW/A-170-0277 (sole source, > $1B, solicitation FY26 Q2, award FY27 Q2) | not yet mapped to an OPN line | sole source; large value | a J&A or award in FY27 Q2 |
| SubHDR VA Block VI / CLB Block II / FMS procurement | submarine high data rate antenna production continues | PMW 770 | LRAE row PID N00039-25-RFPREQ-PMW-770-0019 (sole source, $250M-$1B, solicitation FY25 Q4, award FY26 Q4; incumbent Raytheon, existing N0003921C5002) | submarine communications lines in OPN BA2 (line items 3107, 3130) | sole source | award to Raytheon in FY26 Q4 |
| NILE In-Service Support 6 | recurring ISS task orders (ISS 5 TO 5 in FY26 Q1, ISS 6 contract FY27 Q2) | PMW 150 | LRAE rows PID N00039-25-RFPREQ-PMW-150-0067 and -0050 | Link 16/22 sustainment; small value range | recurring, low uncertainty | ISS 6 solicitation in FY26 Q2 |
| PMW 150 PSS recompete (follow-on to N0003921F3016) | incumbent Booz Allen order ages out | PMW 150 | LRAE row PID N00039-25-RFPREQ-PMW-150-0072 (solicitation FY26 Q1, award FY26 Q4) | support services | SeaPort-NxG competition: no SAM trail expected | award in FY26 Q4 (visible in FPDS from about early FY27) |
| PMW/A 170 cybersecurity, engineering and technical support follow-on; ILS follow-on | incumbent Highbury orders N0003921F3012 and N0003921F3004 age out | PMW/A 170 | LRAE rows PID N00039-25-RFPREQ-PMW/A-170-0240 (FY26 Q1 / FY26 Q4) and -0239 (SDVOSB, $100M-$250M, FY25 Q4 / FY26 Q2) | support services | set-aside changes possible | awards in FY26 Q2 and Q4 |
| Platform Integration and Modernization Support Services 2.0 | incumbent XST order N0003921F3014 ages out | PEO C4I front office (C4IEXEC) | LRAE row PID N00039-25-RFPREQ-C4IEXEC-0014 (solicitation FY26 Q1, award FY26 Q3) | portfolio-level support | portfolio reorganization into PAE Mission Systems may change the buyer | award in FY26 Q3 |
| CANES production quantity change in FY2027 | request below the prior enacted amount | PMW 160 | OPN line item 2915 "CANES": FY2026 enacted 534.324, FY2027 request 493.046 ($ millions); FY2028 529.811 | request stage; enacted FY2027 pending in Congress | inference by program name; Congress may add or cut | the FY2027 appropriations explanatory statement line for CANES |

Congressional marks for FY2026 and FY2027 lines (govinfo) and RDT&E program-element changes
(the RDT&E BA7-8 book is still in the manual queue) are the two signal families not yet
extracted; both sources are registered and reachable.

## 2. Backtests

Method. For each requirement: choose a cutoff before the first public RFI or solicitation (or,
for SeaPort-NxG task orders that never appear on SAM.gov, before the award); admit only evidence
whose "available by" date is on or before the cutoff, using the document's release date, or for
FPDS records the signed date plus about 90 days of DoD publication lag; write the prediction from
that evidence alone; then compare with the award record. Later documents are listed separately as
post-cutoff checks and never as evidence.

| Id | Requirement | Office | Cutoff | Pre-cutoff evidence | Actual | Result |
| --- | --- | --- | --- | --- | --- | --- |
| BT01 | PMW 160 Engineering Support Services follow-on (PEO C4I ESS for the Ta | pmw:160 | 2026-05-05 | LRAE row 'PMW 160 Engineering Support Services (ESS) Follow-; incumbent order N0003922F3000 (Booz Allen) signed 2021-10- | 2026-05-06: task order N0003926FG001 awarded to Booz Allen Hamilton under SeaPort-NxG IDV N0 | correct to the quarter (FY26 Q3) |
| BT02 | PMW 160 Professional Support Services recompete (follow-on to N0003920 | pmw:160 | 2025-03-31 | incumbent order N0003920F3016 (Alpha Omega Group) signed 202; PMW 160 tear sheet (1 May 2023) | 2025-09-05: task order N0003925F3011 awarded to Alpha Omega Group under SeaPort-NxG IDV N001 | correct (award 12 days before the incumbent's end date) |
| BT03 | CLTS-25 production and CLTS/LTS services follow-on (PMS 485 requiremen | pms:485 | 2025-06-19 | LRAE row 'CLTS-25 Production & CLTS/LTS Services IDIQ Contra; incumbent contract N0003919C0002 (BAE) signed 2019-07-03,  | 2026-06-15: no follow-on award observed in FPDS through actions signed by mid-June 2026 (pub | missed: the FY26 Q1 award has not appeared by the end of the observabl |
| BT04 | MIDS-LVT IDIQ new contracts (PMA/PMW 101 follow-on to the 2015 multipl | pmw:101 | 2025-06-19 | LRAE row 'MIDS-LVT IDIQ - New Contracts (C)'; incumbent MAC IDIQ N0003915D0042 (Data Link Solutions) signe; PMA/PMW 101  | 2026-05-14: no new MIDS-LVT IDIQ observed in FPDS for NAVWAR HQ through the observable windo | missed: no FY25 Q3 award; the incumbents' vehicles continued into FY26 |
| BT05 | PEO C4I engineering support for PMW 160, the 2021 recompete (N0003922F | pmw:160 | 2021-06-30 | incumbent order N0003917F3000 (Booz Allen, SeaPort-e IDV N00 | 2021-10-26: task order N0003922F3000 awarded to Booz Allen under SeaPort-NxG IDV N0017819D72 | correct (award the day before the incumbent order ended) |
| BT06 | PMW 120 Professional Support Services follow-on (forecast FY26 Q2 awar | pmw:120 | 2025-06-19 | LRAE row 'PMW 120 Professional Support Services (C)'; incumbent order N0003921F3003 (Booz Allen, SeaPort-NxG) with | 2026-05-07: no follow-on award observed in the FPDS actions retrieved (the FY2026 scan was c | probable slip past FY26 Q2 (incumbent extended in May 2026); not confi |

Results in short: BT01 and BT05 predicted the recompete to the quarter and to the day from the
forecast and the incumbent's end date; BT02 predicted the event from the incumbent's end date
alone, and the forecast (released after the solicitation) added the set-aside and value only
before award; BT03 and BT04 are forecasts that did not appear in the observable window; BT06 is
pending because the FY2026 award scan is incomplete.

Missed signals and false positives:

- Missed: the vehicle change from SeaPort-e to SeaPort-NxG (BT05) and the six-year period of
  performance (BT01) were not predictable from award records; set-aside types are only in the
  LRAE (BT02).
- False positives: the award quarters in BT03 and BT04 (FY26 Q1, FY25 Q3) passed without an award;
  the incumbents' vehicles were extended instead. A monitor that alerts on a forecast quarter must
  also watch for extension modifications on the incumbent, which is the usual public trace of a
  slip.
- Not observable: sole-source justifications and SeaPort task-order RFPs do not create SAM.gov
  notices, so "first RFI or solicitation" is undefined for a large share of PEO C4I support work;
  the LRAE and the incumbent's end date are the only advance signals for those.

Advance notice measured: about 320 days from the LRAE release to award in BT01; about 1,700 days
from the incumbent's award record to the follow-on in BT02 and BT05 (the cadence signal); the
LRAE's added detail arrived 78 days before award in BT02.

What would strengthen these tests: earlier LRAE releases (the 2024 release would move the
forecast cutoff back a year; the archive's index API was offline during this work), the SAM.gov
full extract for first-notice dates (download in progress; registered when complete), FY2026
enacted budget lines for the request-versus-enacted signal, and a complete FY2026 FPDS scan once
the host stops resetting connections.
