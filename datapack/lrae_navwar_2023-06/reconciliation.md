# Reconciliation - lrae_navwar_2023-06

Sheet `LRAE Annex 25`, header on Excel row 8, data rows 9-741.
Record key: hash of title and office code (this release has no PID column).

## Rows

| Decision | Rows |
| --- | --- |
| raw | 733 |
| included | 127 |
| excluded | 507 |
| duplicate | 0 |
| unresolved | 99 |

Sum of decisions: 733 (equals raw: yes).

## Reasons

| Decision | Reason | Rows |
| --- | --- | --- |
| excluded | technical_center_division code of center:niwc-atlantic, outside the PEO C4I portfolio (division itself not in alias table) | 480 |
| excluded | code resolves to pms:485 (program_office), outside the PEO C4I portfolio | 13 |
| excluded | headquarters_competency code of command:navwar, outside the PEO C4I portfolio (division itself not in alias table) | 10 |
| excluded | code resolves to drpm:overmatch (portfolio_or_front_office), outside the PEO C4I portfolio | 3 |
| excluded | code resolves to peo:digital (other organization), outside the PEO C4I portfolio | 1 |
| included | code resolves to pmw:170, a PEO C4I office (alias table) | 47 |
| included | code resolves to pmw:150, a PEO C4I office (alias table) | 16 |
| included | code resolves to pmw:740, a PEO C4I office (alias table) | 14 |
| included | code resolves to pmw:160, a PEO C4I office (alias table) | 10 |
| included | code resolves to pmw:750, a PEO C4I office (alias table) | 7 |
| included | code resolves to pmw:790, a PEO C4I office (alias table) | 7 |
| included | code resolves to pmw:101, a PEO C4I office (alias table) | 6 |
| included | code resolves to pmw:760, a PEO C4I office (alias table) | 6 |
| included | code resolves to pmw:120, a PEO C4I office (alias table) | 5 |
| included | code resolves to pmw:770, a PEO C4I office (alias table) | 5 |
| included | code resolves to peo:c4i, a PEO C4I office (alias table) | 3 |
| included | code resolves to pmw:130, a PEO C4I office (alias table) | 1 |
| unresolved | code None matches no code family | 49 |
| unresolved | code 535 matches no code family | 18 |
| unresolved | family peo_mlb_portfolio_code recognised but code Pf007NERP has no alias-table entry | 7 |
| unresolved | code Cyber Defense matches no code family | 6 |
| unresolved | code 532 matches no code family | 5 |
| unresolved | code 534 matches no code family | 2 |
| unresolved | code 536 matches no code family | 2 |
| unresolved | code CSBO matches no code family | 2 |
| unresolved | family peo_mlb_portfolio_code recognised but code Pf004MNHR has no alias-table entry | 2 |
| unresolved | family peo_mlb_portfolio_code recognised but code Pf005NABS has no alias-table entry | 2 |
| unresolved | code FRD matches no code family | 1 |
| unresolved | code HPCMP matches no code family | 1 |
| unresolved | code MCPNT Directorate matches no code family | 1 |
| unresolved | code Pf1-PAS matches no code family | 1 |

## Included rows per office

| Office | Rows |
| --- | --- |
| peo:c4i | 3 |
| pmw:101 | 6 |
| pmw:120 | 5 |
| pmw:130 | 1 |
| pmw:150 | 16 |
| pmw:160 | 10 |
| pmw:170 | 47 |
| pmw:740 | 14 |
| pmw:750 | 7 |
| pmw:760 | 6 |
| pmw:770 | 5 |
| pmw:790 | 7 |

## Unresolved codes

`532`, `534`, `535`, `536`, `CSBO`, `Cyber Defense`, `FRD`, `HPCMP`, `MCPNT Directorate`, `None`, `Pf004MNHR`, `Pf005NABS`, `Pf007NERP`, `Pf1-PAS`

## Duplicates

This release has no PID column, so the record key is title plus office code; rows sharing that key are marked `duplicate` above and listed here for the reviewer:

- rows 291, 294: liptm00455-maritime prototypes (c) (LSUBP00021)

## Joins (included rows only)

| Join | Lines | Matched | Unmatched | Not collected |
| --- | --- | --- | --- | --- |
| office | 127 | 127 | 0 | 0 |
| existing_contract | 27 | 5 | 3 | 19 |
| notice | 154 | 2 | 25 | 127 |
| contact | 252 | 97 | 155 | 0 |

Explicit joins: office code through the alias table, contract number found in FPDS, notice text containing the PID or contract number, POC name matching a contact observation for the same office. Inferred joins: forecast row tied to an award through an attribution example, or a notice that only cites a shared vehicle. A shared vehicle (SeaPort-NxG IDV, SEWP, GSA schedule) alone is never a join.

FPDS and SAM.gov lookups were collected for lrae_navwar_2025-06 only; lines marked 'not collected' here are honest gaps, not misses. Contact observations were built from the 2025 release, so older rows show no contact match.

## Releases

Earliest saved release; nothing to diff against.
