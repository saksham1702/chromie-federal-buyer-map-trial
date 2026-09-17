# Reconciliation - lrae_navwar_2025-06

Sheet `LRAE Annex 25`, header on Excel row 8, data rows 9-841.
Record key: PID.

## Rows

| Decision | Rows |
| --- | --- |
| raw | 833 |
| included | 148 |
| excluded | 636 |
| duplicate | 0 |
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

## Duplicates

Every PID is unique in this release, so no row is marked `duplicate`. Rows that repeat title, office, value range and existing contract under different PIDs are listed for the reviewer; they read as separate planned actions (option years, additional lots) rather than duplicates and stay as they are:

- rows 176, 177: delivery order for the ffp production of a clts array shipset (PMS-485)
- rows 454, 455: liptm00107 - naval tactical command support system - ntcss development (LSUBP00095)
- rows 87, 544: liptm00129, usmc communication systems, cables, corp production (LSUBP00004)
- rows 179, 458: navy enterprise resource planning plus (navy erp+) proof of concept fo (Pf007NERP)
- rows 340, 341: sldcada 2_sustainment_option exercise (c) (Pf007NERP)

## Joins (included rows only)

| Join | Lines | Matched | Unmatched | Not collected |
| --- | --- | --- | --- | --- |
| office | 148 | 148 | 0 | 0 |
| existing_contract | 46 | 43 | 3 | 0 |
| notice | 197 | 10 | 187 | 0 |
| contact | 279 | 279 | 0 | 0 |

Explicit joins: office code through the alias table, contract number found in FPDS, notice text containing the PID or contract number, POC name matching a contact observation for the same office. Inferred joins: forecast row tied to an award through an attribution example, or a notice that only cites a shared vehicle. A shared vehicle (SeaPort-NxG IDV, SEWP, GSA schedule) alone is never a join.

## Releases

Compared with `lrae_navwar_2023-06` (key: pid where present, else title+office): 31 records matched (166 field changes on 31 of them), 802 added, 702 removed, 0 keys matching several rows. Detail in `diff_lrae_navwar_2023-06_lrae_navwar_2025-06.csv`. Compared with `lrae_navwar_2024-06` (key: title+office): 105 records matched (261 field changes on 81 of them), 728 added, 745 removed, 0 keys matching several rows. Detail in `diff_lrae_navwar_2024-06_lrae_navwar_2025-06.csv`. Every release is kept as its own package.
