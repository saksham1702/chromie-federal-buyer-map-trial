# Reconciliation - lrae_navwar_2024-06

Sheet `LRAE Annex 25`, header on Excel row 8, data rows 9-858.
Record key: hash of title and office code (this release has no PID column).

## Rows

| Decision | Rows |
| --- | --- |
| raw | 850 |
| included | 154 |
| excluded | 663 |
| duplicate | 7 |
| unresolved | 26 |

Sum of decisions: 850 (equals raw: yes).

## Reasons

| Decision | Reason | Rows |
| --- | --- | --- |
| duplicate | record key already seen | 7 |
| excluded | technical_center_division code of center:niwc-atlantic, outside the PEO C4I portfolio (division itself not in alias table) | 450 |
| excluded | technical_center_division code of center:niwc-pacific, outside the PEO C4I portfolio (division itself not in alias table) | 183 |
| excluded | code resolves to pms:485 (program_office), outside the PEO C4I portfolio | 12 |
| excluded | headquarters_competency code of command:navwar, outside the PEO C4I portfolio (division itself not in alias table) | 12 |
| excluded | code resolves to drpm:overmatch (portfolio_or_front_office), outside the PEO C4I portfolio | 4 |
| excluded | code resolves to peo:mlb (portfolio_code), outside the PEO C4I portfolio | 1 |
| excluded | code resolves to peo:mlb (portfolio_or_front_office), outside the PEO C4I portfolio | 1 |
| included | code resolves to pmw:170, a PEO C4I office (alias table) | 40 |
| included | code resolves to pmw:101, a PEO C4I office (alias table) | 21 |
| included | code resolves to pmw:160, a PEO C4I office (alias table) | 20 |
| included | code resolves to pmw:150, a PEO C4I office (alias table) | 18 |
| included | code resolves to pmw:740, a PEO C4I office (alias table) | 18 |
| included | code resolves to pmw:760, a PEO C4I office (alias table) | 10 |
| included | code resolves to pmw:120, a PEO C4I office (alias table) | 7 |
| included | code resolves to pmw:770, a PEO C4I office (alias table) | 6 |
| included | code resolves to peo:c4i, a PEO C4I office (alias table) | 5 |
| included | code resolves to pmw:750, a PEO C4I office (alias table) | 5 |
| included | code resolves to pmw:790, a PEO C4I office (alias table) | 3 |
| included | code resolves to pmw:130, a PEO C4I office (alias table) | 1 |
| unresolved | family peo_mlb_portfolio_code recognised but code Pf007NERP has no alias-table entry | 13 |
| unresolved | family peo_front_office_or_hq_code recognised but code PCE has no alias-table entry | 5 |
| unresolved | family peo_mlb_portfolio_code recognised but code Pf004MNHR has no alias-table entry | 3 |
| unresolved | code COO matches no code family | 2 |
| unresolved | code CSO matches no code family | 1 |
| unresolved | code FRD matches no code family | 1 |
| unresolved | family peo_front_office_or_hq_code recognised but code JTNC has no alias-table entry | 1 |

## Included rows per office

| Office | Rows |
| --- | --- |
| peo:c4i | 5 |
| pmw:101 | 21 |
| pmw:120 | 7 |
| pmw:130 | 1 |
| pmw:150 | 18 |
| pmw:160 | 20 |
| pmw:170 | 40 |
| pmw:740 | 18 |
| pmw:750 | 5 |
| pmw:760 | 10 |
| pmw:770 | 6 |
| pmw:790 | 3 |

## Unresolved codes

`COO`, `CSO`, `FRD`, `JTNC`, `PCE`, `Pf004MNHR`, `Pf007NERP`

## Duplicates

This release has no PID column, so the record key is title plus office code; rows sharing that key are marked `duplicate` above and listed here for the reviewer:

- rows 452, 453: gpnts fy24 bulk buy #2 award and fund (PMW/A-170)
- rows 323, 404: gpnts fy25 bulk buy #1 award and fund (PMW/A-170)
- rows 410, 411: order to contract #n0003922d4001 (PMA/PMW-101)
- rows 408, 409: order to contract #n0003922d4001 (PMA/PMW-101)

## Joins (included rows only)

| Join | Lines | Matched | Unmatched | Not collected |
| --- | --- | --- | --- | --- |
| office | 154 | 154 | 0 | 0 |
| existing_contract | 31 | 18 | 2 | 11 |
| notice | 30 | 1 | 17 | 12 |
| contact | 272 | 179 | 93 | 0 |

Explicit joins: office code through the alias table, contract number found in FPDS, notice text containing the PID or contract number, POC name matching a contact observation for the same office. Inferred joins: forecast row tied to an award through an attribution example, or a notice that only cites a shared vehicle. A shared vehicle (SeaPort-NxG IDV, SEWP, GSA schedule) alone is never a join.

FPDS and SAM.gov lookups were collected for lrae_navwar_2025-06 only; lines marked 'not collected' here are honest gaps, not misses. Contact observations were built from the 2025 release, so older rows show no contact match.

## Releases

Compared with `lrae_navwar_2023-06` (staged: pid, title+office, office+incumbent, then title similarity >= 0.85 within the office (76 matched, 62 candidates)): 138 records followed across the releases, 62 of them candidates a reviewer still has to accept; 669 field changes on 138 of them; 712 added, 595 removed, 3 keys left ambiguous. Every row carries its match basis and the reasoning in `diff_lrae_navwar_2023-06_lrae_navwar_2024-06.csv`. Every release is kept as its own package.
