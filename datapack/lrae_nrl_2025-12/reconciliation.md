# Reconciliation - lrae_nrl_2025-12

Sheet `NRL`, header on Excel row 7, data rows 8-24.
Record key: the row itself, as release and row number (this release has no PID column). No two rows are merged at import.

## Rows

| Decision | Rows |
| --- | --- |
| raw | 17 |
| included | 17 |
| excluded | 0 |
| unresolved | 0 |

Sum of decisions: 17 (equals raw: yes).

## Reasons

| Decision | Reason | Rows |
| --- | --- | --- |
| included | activity-wide release; code resolves to dept:nrl-7600 | 4 |
| included | activity-wide release; code resolves to dept:nrl-7300 | 3 |
| included | activity-wide release; code resolves to dept:nrl-7500 | 3 |
| included | activity-wide release; code resolves to dept:nrl-6100 | 2 |
| included | activity-wide release; code resolves to dept:nrl-8100 | 2 |
| included | activity-wide release; code blank names no office the memory knows | 1 |
| included | activity-wide release; code resolves to dept:nrl-5500 | 1 |
| included | activity-wide release; code resolves to dept:nrl-5700 | 1 |

## Included rows per office

| Office | Rows |
| --- | --- |
| (no office the memory knows) | 1 |
| dept:nrl-5500 | 1 |
| dept:nrl-5700 | 1 |
| dept:nrl-6100 | 2 |
| dept:nrl-7300 | 3 |
| dept:nrl-7500 | 3 |
| dept:nrl-7600 | 4 |
| dept:nrl-8100 | 2 |

## Unresolved codes

none

## Rows sharing a title and an office

Nothing is marked duplicate at import: a row is a source record until a reviewer resolves its identity. Rows that repeat a title under one office code are listed with what tells them apart (description, value, award window), so the reviewer sees what the spreadsheet actually says. Across releases the matcher reports such a key as a candidate rather than choosing a row.

No two rows share a title under one office code in this release.

## Joins (included rows only)

| Join | Lines | Matched | Unmatched | Not collected |
| --- | --- | --- | --- | --- |
| office | 17 | 16 | 1 | 0 |
| existing_contract | 15 | 0 | 6 | 9 |
| notice | 9 | 0 | 0 | 9 |
| contact | 32 | 0 | 32 | 0 |

Explicit joins: office code through the alias table, contract number found in FPDS, notice text containing the PID or contract number, POC name matching a contact observation for the same office. Inferred joins: forecast row tied to an award through an attribution example, or a notice that only cites a shared vehicle. A shared vehicle (SeaPort-NxG IDV, SEWP, GSA schedule) alone is never a join.

FPDS and SAM.gov lookups were collected for lrae_navwar_2025-06 only; lines marked 'not collected' here are honest gaps, not misses. Contact observations were built from the 2025 release, so older rows show no contact match.

## Releases

Earliest saved release; nothing to diff against.
