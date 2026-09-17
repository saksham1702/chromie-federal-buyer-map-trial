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
day; three forecasts did not materialize in the window (BT06 slipped at least two quarters, confirmed by a complete FY2026 scan). Solicitation notices
themselves were absent for the SeaPort-NxG task orders, because those competitions run inside the
vehicle, not on SAM.gov.

## 1. Current early signals for the pilot portfolio

Each row records what may be needed and why, the likely office, the earliest dated
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
| PMW 120 requirements after its 2026 industry day | the office briefed industry twice in February 2026 and again in March 2026 (Special Notices NAVWAR-PMW120-INDUSTRYDAY-26) | PMW 120 | SAM.gov notices posted 2026-02-09, 2026-02-10, 2026-03-12 | LRAE lists the PMW 120 PSS follow-on (award FY26 Q2) and small RDT&E orders | industry-day content not retrieved (attachments need the API key) | an RFI or solicitation naming PMW 120 |
| MIDS Weapons Data Link production, next lot (SF3) and JTRS IDIQ ceiling growth | presolicitation for MIDS WDL SF3 (2026-08-12) and ceiling-increase special notices for MIDS WDL SF1 and MIDS JTRS IDIQ (August 2026) | PMA/PMW 101 (LRAE lists the earlier lot under the PEO C4I front office code) | SAM.gov notices N00039PRESOL_SF3 (2026-08-12), MIDS_WDL_SF1_CONTRACT_CEILING_INCREASE (2026-08-19), MIDS_JTRS_IDIQ_CONTRACT_CEILING_INCREASE (2026-08-27) | OPN line item 2614 Advanced Tactical Data Link Systems (related PE 0205604N) | lot quantities and values not in the notices | the SF3 solicitation and the ceiling modifications in FPDS |
| NILE ISS 6 (now at RFI stage) | Sources Sought N0003926RE013 posted 2026-01-29 | PMW 150 | LRAE row (2025-06-19) then the RFI | small value range; award forecast FY27 Q2 | none beyond timing | the solicitation |
| PMW 120 Maritime Integrated Broadcast Service (MIBS) satellite data terminal | market survey for a SATCOM data terminal (JTT-ME) for the MIBS program | PMW 120 | Sources Sought posted 2024-11-25 and 2025-01-07: "PEO C4I Battlespace Awareness and Information Operations (PMW 120) Maritime Integrated Broadcast Service (MIBS) program is conducting a market survey" | OPN P-1 line 61 Maritime Integrated Broadcast System (line item number not captured in the 1a table) shows FY25 8.5 ($M) and no FY26/FY27 request | funding line looks to be ending or moving; market survey may not lead to a buy | an RFP naming MIBS or a budget line reappearing |
| MIDS Weapons Data Link SF4 radios and SWARMM Family 3 radio | RFIs for NSA-certified MIDS WDL SF4 radios (2025-04-25, 2025-05-14) and a SWARMM Family 3 radio (2025-08) | PMA/PMW 101 (MIDS Program Office named in the notice) | SAM.gov Sources Sought notices, FY2025 archive | ATDLS line 2614 flat at 52.8; WDL SF3 presolicitation followed in August 2026 | RFIs precede production by a year or more | a presolicitation naming SF4 or SWARMM |
| GPNTS software support ceiling increase | sole-source modification to N00039-20-D-0021 announced | PMW/A 170 (named in the notice) | Presolicitation N00039-25-R-2005, 2025-02-13 | LRAE row "GPNTS - Software Ceiling Increase" (FY25 Q3 / Q4, $50M-$100M) | sole source, little competitive opening | the modification in FPDS |
| ADNS multiple-award production contract (order competitions to follow) | presolicitation announced the MAC with RFP in Q2FY25 and award in Q4FY25; RFP posted 2025-06-16; LRAE lists nine "ADNS MAC RFP #n" order rows through FY27 | PMW 160 (named in the notice) | Presolicitation N00039-25-R-9510, 2024-11-07 | OPN line item 3050 Ship Communications Automation (P-1 line 74) 162.1 (FY26) / 156.6 (FY27) | award not observed by September 2026 | the MAC award in FPDS, then the first order competitions |
| CANES maritime containerized secure units | the House added $50.0M above the FY2027 request to the CANES procurement line for "maritime containerized secure units", a configuration not in the request | PMW 160 (CANES program office; inference by program) | H. Rept. 119-715, OPN line item 2915 CANES (P-1 line 64), 2026-06-26 | request 493.0 + 50.0 = 543.0 ($M) if enacted | House position only; Senate and conference may differ; no LRAE row or notice yet for containerized units | the Senate report and enacted act keeping the add; an LRAE row or SAM notice for containerized CANES units |
| CANES production quantity change in FY2027 | request below the prior enacted amount | PMW 160 | OPN line item 2915 "CANES": FY2026 enacted 534.324, FY2027 request 493.046 ($ millions); FY2028 529.811 | request stage; enacted FY2027 pending in Congress | inference by program name; Congress may add or cut | the FY2027 appropriations explanatory statement line for CANES |

### 1a. Budget lines behind the pilot offices ($ millions)

From the DoD Comptroller FY2027 P-1 and R-1 display tables (retrieved 2026-09-16 through the
Browserbase path; hashes `4b0544bb7d42` and `d6c325bf6565`). The office column is an inference
by program name through the tear sheets; the tables themselves name no office. Amounts are the
"total" columns (FY2026 includes the PL 119-21 spend plan).

| OPN line item (P-1 line) | Title | Likely office (inference by program) | FY25 actual | FY26 enacted | FY27 request |
| --- | --- | --- | ---: | ---: | ---: |
| 2237 (P-1 line 45) | SURTASS | PMS 485 (SURTASS; NAVSEA) | 46.0 | 31.2 | 72.2 |
| 2614 (P-1 line 51) | ATDLS | PMA/PMW 101 (ATDLS / Link 16) | 68.5 | 58.7 | 52.8 |
| 2618 (P-1 line 52) | Navy Command and Control System (NCCS) | PMW 150 (NCCS) | 3.6 | 3.5 | 16.2 |
| 2657 (P-1 line 54) | Navstar GPS Receivers (SPACE) | PMW/A 170 (GPS receivers) | 38.0 | 45.7 | 43.1 |
| 2906 (P-1 line 62) | Tactical/Mobile C4I Systems | PMW 150 / PMW 790 (to confirm) | 66.5 | 64.9 | 48.3 |
| 2915 (P-1 line 64) | CANES | PMW 160 (CANES) | 440.0 | 534.3 | 493.0 |
| 2925 (P-1 line 66) | CANES-Intell | PMW 160 (CANES-Intell) | 50.7 | 46.3 | 43.0 |
| 2437 (P-1 line 72) | Battle Force Tactical Network | PMW 160 / PMW/A 170 (BFTN; office to confirm) | 104.0 | 106.6 | 125.7 |
| 3010 (P-1 line 73) | Shipboard Tactical Communications | PMW/A 170 (shipboard tactical comms) | 24.6 | 20.9 | 50.4 |
| 3050 (P-1 line 74) | Ship Communications Automation | PMW 160 (ADNS) | 127.3 | 162.1 | 156.6 |
| 3107 (P-1 line 76) | Submarine Broadcast Support | PMW 770 (submarine broadcast) | 129.5 | 113.1 | 173.1 |
| 3130 (P-1 line 77) | Submarine Communication Equipment | PMW 770 (submarine comms) | 68.3 | 84.6 | 88.1 |
| 3215 (P-1 line 78) | Satellite Communications Systems | PMW/A 170 (SATCOM) | 59.7 | 62.9 | 58.0 |
| 3216 (P-1 line 79) | Navy Multiband Terminal (NMT) | PMW/A 170 (NMT) | 162.9 | 63.4 | 57.8 |
| 3222 (P-1 line 80) | Mobile Advanced EHF Terminal (MAT) | PMW/A 170 (MAT, new line; LRAE row "MAT Production and Sustainment") | - | 220.5 | 202.3 |
| 3415 (P-1 line 82) | Info Systems Security Program (ISSP) | PMW 130 (ISSP) | 195.1 | 191.2 | 349.1 |
| 3501 (P-1 line 84) | Cryptologic Communications Equip | PMW 130 (cryptologic comms) | 15.5 | 7.8 | 7.4 |

| RDT&E PE | Title | Likely office | FY25 total | FY26 total | FY27 total |
| --- | --- | --- | ---: | ---: | ---: |
| 0101402N (BA 07, line 215) | Navy Strategic Communications | PMW 770 (Navy Strategic Communications) | 28.9 | 52.4 | 88.6 |
| 0303138N (BA 07, line 242) | Afloat Networks | PMW 160 (Afloat Networks: CANES, ADNS) | 56.1 | 78.5 | 68.4 |
| 0303140N (BA 07, line 243) | Information Systems Security Program | PMW 130 (ISSP) | 34.4 | 64.1 | 79.1 |
| 0603598N (BA 04, line 54) | ATRT Enterprise Rapid Capability | PEO C4I or NIWC (ATRT rapid capability; to confirm) | 51.5 | 116.5 | 87.6 |
| 0604231N (BA 05, line 115) | Command and Control Systems | PMW 150 (Command and Control Systems) | 139.7 | 64.5 | 73.5 |
| 0604707N (BA 04, line 94) | Space and Electronic Warfare (SEW) Architecture/Engineering Support | NIWC (SEW architecture; to confirm) | 8.6 | 6.6 | 8.7 |
| 0604777N (BA 05, line 155) | Navigation/ID System | PMW/A 170 (Navigation/ID; GPNTS) | 42.9 | 3.7 | 3.4 |
| 0605866N (BA 06, line 196) | Navy Space and Electronic Warfare (SEW) Support | NIWC (SEW support; to confirm) | 23.0 | 22.6 | 21.5 |
| 0608231N (BA 08, line 257) | Maritime Tactical Command and Control (MTC2) - Software Pilot Program | PMW 150 (MTC2 software) | 10.3 | 31.8 | 25.3 |

Movements worth an alert: the NMT line falls from 162.9 (FY25) to 57.8 (FY27) while a new Mobile
Advanced EHF Terminal line appears at 220.5 (FY26) and 202.3 (FY27), matching the LRAE's "MAT
Production and Sustainment" (sole source, $250M-$1B, award FY26 Q4) and the NMT-X follow-on; ISSP
procurement rises from 191.2 to 349.1 and its RDT&E PE from 34.4 to 79.1 (PMW 130); the Navy
Command and Control System line rises from 3.5 to 16.2 and MTC2 software RDT&E from 10.3 to 25.3
(PMW 150); Shipboard Tactical Communications rises from 20.9 to 50.4 and Submarine Broadcast
Support from 113.1 to 173.1 (PMW/A 170, PMW 770); Navy Strategic Communications RDT&E climbs from
28.9 to 88.6 (PMW 770); the Navigation/ID System PE collapses from 42.9 to 3.4 (PMW/A 170, GPNTS
development winding down); CANES dips from 534.3 to 493.0 before recovering in the out-years.

### 1b. Congressional marks on the same lines (House, FY2027)

House Appropriations Committee report on the Department of Defense Appropriations Act, 2027
(H. Rept. 119-715, issued 2026-06-26; govinfo HTML text, hash `9e66c22b30d4`). Amounts in $ thousands.
Only two of the tracked Other Procurement, Navy lines were changed by the House; the rest match the
request. The Senate report and the enacted act will move these again, and the enacted table is
the "enacted" figure for FY2027 in next year's comparison.

| P-1 line | Title | FY2027 request | House recommendation | Change | Committee note |
| --- | --- | ---: | ---: | ---: | --- |
| 51 | ATDLS | 52,758 | 52,758 | 0 |  |
| 52 | NAVY COMMAND AND CONTROL SYSTEM [NCCS] | 16,167 | 16,167 | 0 |  |
| 54 | NAVSTAR GPS RECEIVERS (SPACE) | 43,097 | 43,097 | 0 |  |
| 62 | TACTICAL/MOBILE C4I SYSTEMS | 48,262 | 48,262 | 0 |  |
| 63 | INTELLIGENCE SURVEILLANCE AND RECONNAISSANCE (ISR) | 11,824 | 11,824 | 0 |  |
| 64 | CANES | 493,046 | 543,046 | 50,000 | Program increase: maritime containerized secure units |
| 65 | RADIAC | 38,000 | 23,048 | -14,952 | Contract award delays |
| 66 | CANES-INTELL | 43,028 | 43,028 | 0 |  |
| 72 | BATTLE FORCE TACTICAL NETWORK | 125,661 | 125,661 | 0 |  |
| 73 | SHIPBOARD TACTICAL COMMUNICATIONS | 50,350 | 50,350 | 0 |  |
| 74 | SHIP COMMUNICATIONS AUTOMATION | 156,605 | 156,605 | 0 |  |
| 76 | SUBMARINE BROADCAST SUPPORT | 173,069 | 173,069 | 0 |  |
| 77 | SUBMARINE COMMUNICATION EQUIPMENT | 88,071 | 88,071 | 0 |  |
| 78 | SATELLITE COMMUNICATIONS SYSTEMS | 57,961 | 57,961 | 0 |  |
| 79 | NAVY MULTIBAND TERMINAL [NMT] | 57,768 | 57,768 | 0 |  |
| 80 | MOBILE ADVANCED EHF TERMINAL (MAT) | 202,305 | 202,305 | 0 |  |
| 82 | INFO SYSTEMS SECURITY PROGRAM [ISSP] | 349,099 | 349,099 | 0 |  |
| 84 | CRYPTOLOGIC COMMUNICATIONS EQUIPMENT | 7,419 | 7,419 | 0 |  |

The RDT&E program-element table for the Navy is in the same report but the HTML granule did not
yield the PE rows to the text search; the PDF rendering is the next step for those lines.

Congressional marks for the FY2027 procurement lines are extracted above from the House report;
the Senate report, the FY2027 enacted table and the RDT&E program-element marks are the next
pulls from govinfo. RDT&E program-element request amounts come from the Comptroller R-1 table;
the Navy RDT&E BA7-8 book (narratives per PE) remains in the manual queue for the exhibit text
that names programs and milestones.

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
| BT04 | MIDS-LVT IDIQ new contracts (PMA/PMW 101 follow-on to the 2015 multipl | pmw:101 | 2025-04-08 | incumbent MAC IDIQ N0003915D0042 (Data Link Solutions) signe; SAM.gov award notices for the two 2015 MIDS-LVT IDIQs (sol | 2025-04-09: Presolicitation and RFP N00039-24-R-4019 posted by NAVWAR HQ 'on behalf of the M | solicitation correct to the quarter (FY25 Q3) from the vehicles' age a |
| BT05 | PEO C4I engineering support for PMW 160, the 2021 recompete (N0003922F | pmw:160 | 2021-06-30 | incumbent order N0003917F3000 (Booz Allen, SeaPort-e IDV N00 | 2021-10-26: task order N0003922F3000 awarded to Booz Allen under SeaPort-NxG IDV N0017819D72 | correct (award the day before the incumbent order ended) |
| BT06 | PMW 120 Professional Support Services follow-on (forecast FY26 Q2 awar | pmw:120 | 2025-06-19 | LRAE row 'PMW 120 Professional Support Services (C)'; incumbent order N0003921F3003 (Booz Allen, SeaPort-NxG) with | 2026-05-07: no follow-on award observed in the FPDS actions retrieved (the FY2026 scan was c | probable slip past FY26 Q2 (incumbent extended in May 2026); not confi |
| BT07 | NILE In-Service Support (ISS) 6 engineering services (PMW 150) | pmw:150 | 2026-01-28 | LRAE row 'NILE In-Service Support (ISS) 6 Contract (C)'; companion LRAE rows 'NILE ISS 5 Task Order 5' (FY25 Q4 / FY2 | 2026-01-29: Sources Sought N0003926RE013 'NILE IN SERVICE SUPPORT (ISS) 6 ENGINEERING SERVIC | correct to the quarter (FY26 Q2) |
| BT08 | Egyptian Navy Autonomous INTelligence System (AINTS) platform integrat | pmw:740 | 2026-07-30 | LRAE row 'EGYPTIAN Navy AINTS (EG-P-LGQ, A2) (C)'; PMW 740 tear sheet | 2026-07-31: Presolicitation N0003926RE014 'Egyptian Navy Autonomous INTelligence System (AIN | missed by about five quarters: presolicitation in FY26 Q4 against a fo |
| BT09 | Royal Saudi Naval Forces in-Kingdom C4ISR support services recompete ( | pmw:740 | 2025-04-29 | incumbent order N0003920F3015 (SAIC, SeaPort-NxG IDV N001781; PMW 740 tear sheet | 2025-04-30: Presolicitation N0003925R4014 'RSNF InKSA Services': 'NAVWAR HQ, in support of P | solicitation in FY25 Q3, consistent with the incumbent's age; award (f |
| BT10 | ADNS (Automated Digital Network System) multiple-award production cont | pmw:160 | 2024-11-06 | 2016 presolicitation for ADNS Increment III (N00039-16-R-002; ADNS enclave orders under the 2017 IDV N0003917D0009 (Serc | 2024-11-07: Presolicitation N00039-25-R-9510 'PMW 160 Wide Area Networks (WAN) Multiple Awar | solicitation year correct; the agency's own presolicitation said RFP i |

Results in short: BT01 and BT05 predicted the recompete to the quarter and to the day from the
forecast and the incumbent's end date; BT07 is the cleanest forecast case, with the LRAE row
preceding a true public first notice (the NILE ISS 6 RFI) by seven months; BT04, BT09 and BT10
now have real first-notice dates from the FY2025 SAM.gov archive and show that the age of the
incumbent vehicle alone predicted the solicitation quarter, with the office confirmed in the
notice's first sentence each time; BT02 predicted the event from the incumbent's end date alone;
BT08 got the requirement and office right but the calendar wrong by five quarters; BT03 is a
forecast that did not appear in the observable window; BT06 is a timing miss (the complete FY2026 scan shows the incumbent extended, no follow-on award
scan is incomplete. Awards for BT04, BT09 and BT10 have not appeared in FPDS yet, which is the
pattern to expect given the roughly 90-day publication lag and slipping award dates.

Missed signals and false positives:

- Missed: the vehicle change from SeaPort-e to SeaPort-NxG (BT05) and the six-year period of
  performance (BT01) were not predictable from award records; set-aside types are only in the
  LRAE (BT02).
- False positives: the award quarters in BT03 and BT04 (FY26 Q1, FY25 Q3) passed without an award;
  the incumbents' vehicles were extended instead. BT08's solicitation quarter passed a year before
  the presolicitation appeared. In BT10 the agency's own presolicitation promised the RFP in
  Q2FY25 and award in Q4FY25; the RFP came a quarter late and the award has not appeared. A monitor that alerts on a forecast quarter must
  also watch for extension modifications on the incumbent, which is the usual public trace of a
  slip.
- Not observable: SeaPort-NxG task-order competitions do not create SAM.gov notices (nine
  solicitation numbers from the examples returned nothing), so "first RFI or solicitation" is
  undefined for a large share of PEO C4I support work; the LRAE and the incumbent's end date are
  the only advance signals for those. Sole-source actions do leave a J&A notice (the 2019
  SURTASS LTS/CLTS J&A names PMS 485).
- Notice text as confirmation: the NILE ISS 6 RFI and the AINTS presolicitation both name the
  owning office in their first sentence, so the office predicted from the LRAE was confirmed by
  the first public notice itself (BT07, BT08).

Advance notice measured: 224 days from the LRAE release to the first public notice in BT07 and
407 days in BT08; about 320 days from the LRAE release to award in BT01; about 1,700 days from the
incumbent's award record to the follow-on in BT02 and BT05 (the cadence signal); the LRAE's added
detail arrived 78 days before award in BT02.

What would strengthen these tests: earlier LRAE releases (the 2024 release and a 2023 export were recovered on 2026-09-18 and are packaged
under `datapack/`; re-running the forecast cutoffs against them is the next step); the FY2021
SAM.gov archive file for BT05's solicitation (the FY2025 file is retrieved and used above; the
daily "Full" file holds only the current dataset); FY2026 enacted budget lines for the
request-versus-enacted signal; and the 2026 LRAE release when it is published (the FY2026 FPDS scan is now complete through June 2026)
connections.

Update 2026-09-18: the June 2024 release and a 2023 export were recovered through the Wayback
index and packaged next to the June 2025 release (`datapack/lrae_navwar_*/`, with diffs in the
newer packages). Two findings for the backtests: PIDs are only partly stable across releases, so a
requirement has to be followed by title and office when its PID changes; and on the PEO C4I rows
that do match, the fields that move between releases are mostly the solicitation and award
quarters and fiscal years, which is the forecast-revision signal the monitor design assumed.

FY2026 FPDS scan (2026-09-18): every action signed by NAVWAR HQ (N00039) from 2025-10-01 to
2026-06-30 was retrieved month by month (pages in the manifest, note "FY2026 FPDS rescan"). The
July to September 2026 windows returned nothing, which is the publication lag, not an absence of
awards. Against the pending forecasts: no PMW 120 professional-support follow-on (BT06, incumbent
extended); no Platform Integration 2.0 award (the incumbent PEO C4I integration order was
modified in April 2026); NMT work continues on new Raytheon sustainment and engineering task
orders signed December 2025 to June 2026, which is sustainment, not the NMT-X production
follow-on the forecast lists. PMW 160 is the office most often named in FY2026 award text.
