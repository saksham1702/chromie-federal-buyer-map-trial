# Reconciliation - lrae_navwar_2025-06

Sheet `LRAE Annex 25`, header on Excel row 8, data rows 9-841.
Record key: PID, where present (833 of 833 raw rows); a row without one is its own record (release and row number).

## Rows

| Decision | Rows |
| --- | --- |
| raw | 833 |
| included | 148 |
| excluded | 636 |
| unresolved | 49 |

Sum of decisions: 833 (equals raw: yes).

## Reasons

| Decision | Reason | Rows |
| --- | --- | --- |
| excluded | technical_center_division code of center:niwc-atlantic, outside the PEO C4I portfolio (division itself not in alias table) | 456 |
| excluded | technical_center_division code of center:niwc-pacific, outside the PEO C4I portfolio (division itself not in alias table) | 147 |
| excluded | code resolves to pms:485 (program_office), outside the PEO C4I portfolio | 16 |
| excluded | headquarters_competency code of command:navwar, outside the PEO C4I portfolio (division itself not in alias table) | 10 |
| excluded | code resolves to drpm:overmatch (portfolio_or_front_office), outside the PEO C4I portfolio | 4 |
| excluded | code resolves to center:niwc-pacific (other organization), outside the PEO C4I portfolio | 1 |
| excluded | code resolves to peo:mlb (portfolio_code), outside the PEO C4I portfolio | 1 |
| excluded | code resolves to peo:mlb (portfolio_or_front_office), outside the PEO C4I portfolio | 1 |
| included | code resolves to pmw:170, a PEO C4I office (alias table) | 37 |
| included | code resolves to pmw:101, a PEO C4I office (alias table) | 22 |
| included | code resolves to pmw:150, a PEO C4I office (alias table) | 18 |
| included | code resolves to pmw:160, a PEO C4I office (alias table) | 17 |
| included | code resolves to pmw:740, a PEO C4I office (alias table) | 17 |
| included | code resolves to pmw:750, a PEO C4I office (alias table) | 10 |
| included | code resolves to pmw:770, a PEO C4I office (alias table) | 9 |
| included | code resolves to pmw:760, a PEO C4I office (alias table) | 5 |
| included | code resolves to peo:c4i, a PEO C4I office (alias table) | 4 |
| included | code resolves to pmw:790, a PEO C4I office (alias table) | 4 |
| included | code resolves to pmw:130, a PEO C4I office (alias table) | 3 |
| included | code resolves to pmw:120, a PEO C4I office (alias table) | 2 |
| unresolved | family peo_mlb_portfolio_code recognised but code Pf007NERP has no alias-table entry | 25 |
| unresolved | family peo_mlb_portfolio_code recognised but code Pf004MNHR has no alias-table entry | 8 |
| unresolved | family peo_front_office_or_hq_code recognised but code Digital TD has no alias-table entry | 4 |
| unresolved | family peo_front_office_or_hq_code recognised but code PCE has no alias-table entry | 3 |
| unresolved | code NPT-34 matches no code family | 2 |
| unresolved | family peo_front_office_or_hq_code recognised but code DCE has no alias-table entry | 2 |
| unresolved | family peo_front_office_or_hq_code recognised but code PAS has no alias-table entry | 2 |
| unresolved | family peo_mlb_portfolio_code recognised but code Pf005NABS has no alias-table entry | 2 |
| unresolved | family peo_front_office_or_hq_code recognised but code JTNC has no alias-table entry | 1 |

## Included rows per office

| Office | Rows |
| --- | --- |
| peo:c4i | 4 |
| pmw:101 | 22 |
| pmw:120 | 2 |
| pmw:130 | 3 |
| pmw:150 | 18 |
| pmw:160 | 17 |
| pmw:170 | 37 |
| pmw:740 | 17 |
| pmw:750 | 10 |
| pmw:760 | 5 |
| pmw:770 | 9 |
| pmw:790 | 4 |

## Unresolved codes

`DCE`, `Digital TD`, `JTNC`, `NPT-34`, `PAS`, `PCE`, `Pf004MNHR`, `Pf005NABS`, `Pf007NERP`

## Rows sharing a title and an office

Nothing is marked duplicate at import: a row is a source record until a reviewer resolves its identity. Rows that repeat a title under one office code are listed with what tells them apart (description, value, award window), so the reviewer sees what the spreadsheet actually says. Across releases the matcher reports such a key as a candidate rather than choosing a row.

- Delivery Order for the FFP Production of a CLTS Array Shipset (PMS-485), 3 rows:
  - row 175: no description beyond the title | $7.5M - $50M | award FY28 Q1
  - row 176: Procure FFP CLTS Array Shipset Production via sole source IDIQ Delivery Order | $7.5M - $50M | award FY29 Q1
  - row 177: Procure FFP CLTS Array Shipset Production via sole source IDIQ Delivery Order | $7.5M - $50M | award FY30 Q1
- LIPTM00107 - Naval Tactical Command Support System - NTCSS Development (LSUBP00095), 2 rows:
  - row 454: Program Support. | < $2M | award FY25 Q4
  - row 455: Program Support | < $2M | award FY25 Q4
- LIPTM00129, USMC Communication Systems, Cables, Corp Production (LSUBP00004), 2 rows:
  - row 87: Fabricated Metal Cables | < $2M | award FY25 Q3
  - row 544: Fabricated metal cables | < $2M | award FY25 Q4
- Navy Enterprise Resource Planning Plus (Navy ERP+) Proof of Concept fo (PF007NERP), 2 rows:
  - row 179: Navy Enterprise Resource Planning Plus (Navy ERP+) Proof of Concept for DoN’s Budget to Re | $7.5M - $50M | award FY25 Q4
  - row 458: Navy Enterprise Resource Planning Plus (Navy ERP+) Proof of Concept for DoN’s Budget to Re | $7.5M - $50M | award FY25 Q4
- SLDCADA 2_Sustainment_Option Exercise (C) (PF007NERP), 2 rows:
  - row 340: SLDCADA 2_Sustainment_Option Exercise | $7.5M - $50M | award FY29 Q2
  - row 341: SLDCADA 2_Sustainment_Option Exercise | $7.5M - $50M | award FY30 Q2

## Joins (included rows only)

| Join | Lines | Matched | Unmatched | Not collected |
| --- | --- | --- | --- | --- |
| office | 148 | 148 | 0 | 0 |
| existing_contract | 46 | 43 | 3 | 0 |
| notice | 199 | 10 | 189 | 0 |
| contact | 279 | 279 | 0 | 0 |

Explicit joins: office code through the alias table, contract number found in FPDS, notice text containing the PID or contract number, POC name matching a contact observation for the same office. Inferred joins: forecast row tied to an award through an attribution example, or a notice that only cites a shared vehicle. A shared vehicle (SeaPort-NxG IDV, SEWP, GSA schedule) alone is never a join.

## Releases

Compared with `lrae_navwar_2023-06` (staged: pid, title+office, office+incumbent, then title similarity >= 0.85 within the office (35 matched, 31 candidates)): 66 records followed across the releases, 31 of them candidates a reviewer still has to accept; 368 field changes on 66 of them; 767 added, 667 removed, 1 key left ambiguous. Every row carries its match basis and the reasoning in `diff_lrae_navwar_2023-06_lrae_navwar_2025-06.csv`. Compared with `lrae_navwar_2024-06` (staged: pid, title+office, office+incumbent, then title similarity >= 0.85 within the office (105 matched, 73 candidates)): 178 records followed across the releases, 73 of them candidates a reviewer still has to accept; 567 field changes on 152 of them; 655 added, 672 removed, 5 keys left ambiguous. Every row carries its match basis and the reasoning in `diff_lrae_navwar_2024-06_lrae_navwar_2025-06.csv`. Every release is kept as its own package.
