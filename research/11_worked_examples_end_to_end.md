# Worked examples, end to end

Three records followed from the source file to the alert, so the reasoning can be checked
at every hop before the monitors are widened: an organization change, a forecast revision,
and an ambiguous office match. Each hop names the file and the row, so every claim below
can be opened in the spreadsheet it came from.

Reproduce all three:

```
python research/tools/lrae_package.py build          # datapack/ from the saved bytes
python research/tools/agency_layers_sql.py > /tmp/layers.sql
psql "$DSN" -f /tmp/layers.sql
python research/tools/monitor_forecast_revision.py --dsn "$DSN"
```

The numbers below come from that sequence against a local database on 2026-09-20.

---

## 1. An organization change: NEN leaves PEO EIS for PEO Digital

**What the source says.** `peodigital.navy.mil` article 3431521, read from a Wayback capture
of 2026-05-19 (`sha256 2116bf240c64`), recorded as `obs:013` with `observed_at` 2021-04-01:

> In May 2020 ... PEO EIS was disestablished to make way for two new PEOs, PEO Digital and
> Enterprise Services (PEO Digital) and PEO Manpower, Logistics and Business Solutions (PEO MLB).

**What the research holds.** Two relationships, not one, in `organization_seed.json`:

| id | edge | from | to | dates |
| --- | --- | --- | --- | --- |
| `rel:054` | `child_of` | `office:nen` | `peo:eis` | ends 2020-05-13, `documented` |
| `rel:055` | `child_of` | `office:nen` | `peo:digital` | starts 2020-05-14, `inferred` |

`rel:055`'s start date is marked inferred on purpose: the article says the programs moved in
May 2020, and the day after the 2020-05-13 memo is a convention this package chose, not a
date the Navy published.

**What reaches the database.** Both. The office row carries the current parent in the column
and the former parent stays in the relationship table with its end date:

```
gov_organizations
  PMW 205 Naval Enterprise Networks Program Office
    parent_organization_id -> Program Executive Office Digital and Enterprise Services

gov_organization_relationships
  rel:054  PMW 205 ... -> Program Executive Office Enterprise Information Systems
           functionally_aligned_to   valid_from (none)   valid_to 2020-05-13
```

**What was wrong before.** The loader skipped every `child_of` row for an office that had one
live parent, on the grounds that the parent column already said it. That was true of the live
edge and false of the ended one, so `rel:054` was dropped and the database showed NEN as
though it had always been under PEO Digital. The skip is now limited to the single live claim
the column actually holds (`agency_layers_sql.py`, `emit_relationships`). One relationship row
was recovered by the change; the same rule is what will keep the PEO/PAE migration legible as
offices move under PAE Mission Systems.

**Still held back, and why.** PMS 485's move from PEO Submarines to PEO Undersea Warfare is
in the research and does not load. The dated version of that claim (`rel:059`) is marked
`retracted` — a reviewer withdrew it — and the surviving version (`rel:061`) carries no end
date. `gov_organization_relationships` has no way to say "this claim is over but I cannot
date it", so publishing it would read as current. It is skipped out loud:
`claim is superseded with no end date; no column can say so`. This needs either a date from a
source or a retraction concept in the table; it is not something the loader can decide.

**To verify:** open the Wayback capture in `research/documents_manifest.jsonl`, then
`select * from gov_organization_relationships where source_ref = 'rel:054'`.

---

## 2. A forecast revision: MAT Production and Sustainment slips and grows

**The two spreadsheet rows.** Same PID, two releases, and note the title itself was rewritten:

| | June 2023 export | June 2025 release |
| --- | --- | --- |
| file | `NAVWAR_LRAE_Report.xlsx` (`sha256 48ad6e27241a`) | `NAVWAR HQCA-2025-A-037 ...xlsx` (`sha256 697ec8c004d2`) |
| sheet row | `LRAE Annex 25` row 383 | `LRAE Annex 25` row 100 |
| PID | `N00039-23-RFPREQ-PMW/A-170-0155` | `N00039-23-RFPREQ-PMW/A-170-0155` |
| title | Big Sky Production and Sustainment Contract | MAT Production and Sustainment |
| office | PMW/A-170 | PMW/A-170 |
| value | `$100M - $250M` | `$250M - $1B` |
| award | FY25 Q3 | FY26 Q4 |
| solicitation | FY24 Q2 | FY25 Q3 |

**How the two rows were matched.** On the PID, which both releases carry. This is the easy
case and it is rarer than it looks — see example 3 and the matching note at the end.

**What the loader writes.** Two dated observations per claim, never one merged record:

```
gov_need_organizations / gov_intelligence_assertions
  ...:lrae_navwar_2023-06:...-0155:requirement_owner   observed_at 2023-06-20
      "lrae_navwar_2023-06 names this office as the requirement owner."
  ...:lrae_navwar_2025-06:...-0155:requirement_owner   observed_at 2025-06-19
      "lrae_navwar_2025-06 names this office as the requirement owner."

gov_funding_observations
  2023-06-20   100000000 - 250000000   FY2025   "... stated as $100M - $250M"
  2025-06-19   250000000 - 1000000000  FY2026   "... stated as $250M - $1B"
```

The office is the same in both releases, so the later assertion supersedes the earlier one and
the current view holds a single owner. Had the 2025 release named a different office, the two
observations would both have stayed live — that rule is `chain_or_branch()` and it is covered
by a self-check, because no release pair in this data exercises it.

**The alert.**

```
**N00039-23-RFPREQ-PMW/A-170-0155** - MAT Production and Sustainment
- What changed: anticipated award slips FY25 Q3 -> FY26 Q4 between the 2023-06-20 and 2025-06-19 releases.
- Office: PMW/A 170 Communications and GPS Navigation Program Office. Ancestry: PMW/A 170 ...
  -> Program Executive Office Command, Control, Communications, Computers and Intelligence;
  succeeded by Portfolio Acquisition Executive Mission Systems (from 2026-05-11).
- Evidence: LRAE lrae_navwar_2023-06 LRAE Annex 25!row 383 (sha256 48ad6e27241a);
  LRAE lrae_navwar_2025-06 LRAE Annex 25!row 100 (sha256 697ec8c004d2).
- Uncertainty: the LRAE is an estimate. A move may be an acquisition-strategy change or a
  clerical correction, and the release does not say which.
```

**What the alert does not say, and why.** The value also moved, from `$100M - $250M` to
`$250M - $1B`, and the alert reports only the slip. A funding re-estimate chains to its
predecessor only when it covers the same fiscal period, because superseding across periods
would claim FY26 money replaced FY25 money rather than that the estimate changed. This
requirement moved from FY25 to FY26, so the two figures are separate measurements and the
value monitor does not pair them. Across the whole load that leaves 0 value-range revisions
against 14 award-window revisions, 13 of them slips. The rule is defensible and the blind spot
is real: a requirement that slips a year and doubles is reported as a slip. Worth a decision
before the monitors widen.

**To verify:** open row 383 of the 2023 file and row 100 of the 2025 file; both hashes are in
`datapack/lrae_navwar_*/SOURCE.json`.

---

## 3. An ambiguous match, kept as a candidate

Two shapes of ambiguity show up, and neither is resolved silently any more.

### 3a. One contract, six later rows

Matching 2024 against 2025 by incumbent contract number under the same office code:

```
key      PMS-485|N0003919C0002
basis    office+incumbent
rows     earlier 474  ->  later 11;174;175;176;177;416
reason   same incumbent contract number under the same office code, but the key matches
         1 earlier and 6 later rows
```

One 2024 line became six 2025 lines under the same contract — task orders broken out of an
IDIQ, most likely, but the spreadsheet does not say so. Picking one would invent a fact, so
the diff records it as `change = ambiguous`, `confidence = candidate`, with every row number
on both sides and the reason above. Eight such keys survive the 2024-to-2025 comparison, one
in 2023-to-2025, three in 2023-to-2024. A reviewer resolves them; the tool does not.

### 3b. A reworded title, matched on similarity

Where no PID, title or contract number matches, the last pass compares titles within the same
office code and keeps anything scoring 0.85 or better as a **candidate**, never a match:

```
change      unchanged
key         N00039-25-RFPREQ-Pf007NERP-0006
key_method  title~office
confidence  candidate
old_row     170 (June 2024)        new_row  138 (June 2025)
reason      titles 0.92 alike under office PF007NERP; earlier row read
            "Navy Enterprise Resource Planning Technical Support Services - 2 (C)"
```

The later row reads `Navy Enterprise Resource Planning (NERP) Technical Support Services (C)`
under the same office code. Almost certainly the same buy; still a candidate, because "almost
certainly" is a reviewer's call and not the tool's.

The score and the earlier wording travel with the row, so accepting or rejecting it is a
judgement a person makes with the evidence in front of them. Titles are never compared across
offices, however close they read.

### Why the matching is staged at all

No single key follows a requirement across releases:

- The June 2024 release **has no PID column at all**.
- PIDs are not stable where they do exist: 31 of the 2023 export's 643 PIDs reappear in
  June 2025.
- Titles get rewritten between releases, as example 2 shows on a row whose PID held.

So `pair_releases()` runs strongest-first — PID, then exact title under the same office, then
incumbent contract number under the same office — and each stage claims a pair only when it is
1:1. Whatever survives gets the similarity pass as candidates. Coverage, records followed
across two releases:

| comparison | was | now | of which candidates |
| --- | --- | --- | --- |
| 2024-06 -> 2025-06 | 105 | 178 | 51 |
| 2023-06 -> 2025-06 | 31 | 66 | 26 |
| 2023-06 -> 2024-06 | 59 | 138 | 62 |

Most rows still read as added or removed. That is the forecast churning, not a matcher giving
up quietly: every diff row now carries `key_method`, `confidence` and `reason`.

---

## Appendix: two more places the data is deliberately left incomplete

**"Over $1B" is not $1B.** Four 2025 rows state `> $1B+`, a floor with no ceiling —
`N00039-22-RFPREQ-PMW/A-170-0021` and `N00039-25-RFPREQ-PMW/A-170-0277` among them.
`gov_funding_observations` holds a flat amount or a closed range and nothing else. Writing the
floor as the amount would publish "exactly $1B" for a buy the Navy only said exceeds $1B, and
writing the floor as both bounds says the same thing twice. Those rows are refused with the
reason printed — `open-ended value the schema cannot hold (> $1B+)` — and stay in the CSV
layer with `as_stated` intact until the column can hold an open range. Every row that does
load carries the source wording: `... anticipated total contract value, stated as $250M - $1B`.

**65 rows state no range at all.** `No Range Specified` is refused the same way and counted
in the skip log rather than defaulted to zero.
