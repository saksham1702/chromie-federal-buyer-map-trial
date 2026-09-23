# Reconciliation - lrae_onr_2025-12

Sheet `ONR`, header on Excel row 7, data rows 8-58.
Record key: the row itself, as release and row number (this release has no PID column). No two rows are merged at import.

## Rows

| Decision | Rows |
| --- | --- |
| raw | 51 |
| included | 51 |
| excluded | 0 |
| unresolved | 0 |

Sum of decisions: 51 (equals raw: yes).

## Reasons

| Decision | Reason | Rows |
| --- | --- | --- |
| included | activity-wide release; code resolves to dept:onr-code-34 | 7 |
| included | activity-wide release; code resolves to dept:onr-code-32 | 5 |
| included | activity-wide release; code resolves to activity:onr-global | 4 |
| included | activity-wide release; code resolves to dept:onr-code-02 | 4 |
| included | activity-wide release; code resolves to dept:onr-code-332 | 4 |
| included | activity-wide release; code resolves to dept:onr-code-53 | 4 |
| included | activity-wide release; code resolves to dept:onr-code-08 | 3 |
| included | activity-wide release; code resolves to dept:onr-code-07 | 2 |
| included | activity-wide release; code resolves to dept:onr-code-33 | 2 |
| included | activity-wide release; code resolves to dept:onr-code-35 | 2 |
| included | activity-wide release; code resolves to dept:onr-code-52 | 2 |
| included | activity-wide release; code resolves to dept:onr-code-56 | 2 |
| included | activity-wide release; code resolves to office:navalx | 2 |
| included | activity-wide release; code All ONR HQ Science & Technology Departments, NavalX, ONR Global (ONRG) and Marine Corps Warfighting Lab (MCWL) names no office the memory knows | 1 |
| included | activity-wide release; code blank names no office the memory knows | 1 |
| included | activity-wide release; code resolves to dept:onr-code-05 | 1 |
| included | activity-wide release; code resolves to dept:onr-code-31 | 1 |
| included | activity-wide release; code resolves to dept:onr-code-54 | 1 |
| included | activity-wide release; code resolves to dept:onr-code-55 | 1 |
| included | activity-wide release; code resolves to dept:onr-code-59 | 1 |
| included | activity-wide release; code resolves to dept:onr-pmr-51 | 1 |

## Included rows per office

| Office | Rows |
| --- | --- |
| (no office the memory knows) | 2 |
| activity:onr-global | 4 |
| dept:onr-code-02 | 4 |
| dept:onr-code-05 | 1 |
| dept:onr-code-07 | 2 |
| dept:onr-code-08 | 3 |
| dept:onr-code-31 | 1 |
| dept:onr-code-32 | 5 |
| dept:onr-code-33 | 2 |
| dept:onr-code-332 | 4 |
| dept:onr-code-34 | 7 |
| dept:onr-code-35 | 2 |
| dept:onr-code-52 | 2 |
| dept:onr-code-53 | 4 |
| dept:onr-code-54 | 1 |
| dept:onr-code-55 | 1 |
| dept:onr-code-56 | 2 |
| dept:onr-code-59 | 1 |
| dept:onr-pmr-51 | 1 |
| office:navalx | 2 |

## Unresolved codes

none

## Rows sharing a title and an office

Nothing is marked duplicate at import: a row is a source record until a reviewer resolves its identity. Rows that repeat a title under one office code are listed with what tells them apart (description, value, award window), so the reviewer sees what the spreadsheet actually says. Across releases the matcher reports such a key as a candidate rather than choosing a row.

No two rows share a title under one office code in this release.

## Joins (included rows only)

| Join | Lines | Matched | Unmatched | Not collected |
| --- | --- | --- | --- | --- |
| office | 51 | 49 | 2 | 0 |
| existing_contract | 69 | 0 | 2 | 67 |
| notice | 67 | 0 | 0 | 67 |
| contact | 0 | 0 | 0 | 0 |

Explicit joins: office code through the alias table, contract number found in FPDS, notice text containing the PID or contract number, POC name matching a contact observation for the same office. Inferred joins: forecast row tied to an award through an attribution example, or a notice that only cites a shared vehicle. A shared vehicle (SeaPort-NxG IDV, SEWP, GSA schedule) alone is never a join.

FPDS and SAM.gov lookups were collected for lrae_navwar_2025-06 only; lines marked 'not collected' here are honest gaps, not misses. Contact observations were built from the 2025 release, so older rows show no contact match.

## Releases

Earliest saved release; nothing to diff against.
