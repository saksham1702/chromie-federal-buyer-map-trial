# Research package: Navy (NAVWAR / PEO C4I) acquisition source map

Deliverables for the Federal Program Office Intelligence Trial: source discovery, data
understanding, worked examples, and an implementation plan for the NAVWAR / PEO C4I pilot.
The package also loads into the production agency-intelligence tables, replays its own
attributions through the production resolver, and produces one of the designed alerts from
the loaded rows. No production writes and no outreach: everything runs against a local
database, and the promotion statements are written to a file for a person to run.

## Review order

1. `00_existing_work_and_pilot.md` - what exists, what the pilot covers, verified organization
2. `01_source_registry.md` + `source_registry.json` - every source, inspected once
3. `02_organization_map.md` + `organization_seed.json`
4. `03_data_connection_map.md`
5. `04_attribution_process_and_examples.md` + `attribution_examples.json`
6. `05_early_signals_and_backtests.md` + `backtests.json`
7. `06_continuous_monitor_design.md`
8. `07_implementation_backlog.md`
9. `08_org_memory_format.md` + `org_code_families.json` - the dated PEO-plus-PAE organization memory and the code registry a parser uses
10. `09_manual_collection_runbook.md` - each source worked by hand once, with what a monitor replaces
11. `11_worked_examples_end_to_end.md` - one organization change, one forecast revision and one ambiguous match followed from the spreadsheet row to the alert, with what is deliberately left incomplete
12. `12_three_use_cases_navy.md` - the three uses of the data (a requirement before solicitation, an active notice traced to its office, a past requirement with its award and funding), each walked on a Navy example with every hop cited, plus the forecast-status table; produced by `tools/trace.py`
13. `contact_observations.json` and `contact_recommendations.json` - likely public contacts per office with confidence labels
14. `../datapack/lrae_navwar_*/` - the NAVWAR LRAE releases (2023 export, June 2024, June 2025) as regenerable packages. Committed: `SOURCE.json` (source hash, output hashes) and `reconciliation.md`. The CSV tables (rows, decisions, joins, layers, diffs) are regenerated locally with `python research/tools/lrae_package.py build` and shared out of band; their hashes are in `SOURCE.json`
15. `navy-sources-map.md` - prose companion to the registry: every source once, what it can and cannot establish, how they join, evidence-strength rules (contributed; the registry and manifest stay the authorities)

Supporting files: `documents_manifest.jsonl` (every document fetched: URL, hash, retrieval
method and time), `manual_pdf_requests.json` (documents that still need a human to fetch),
`tools/fetch.py` (the fetch-and-record helper), `tools/lrae_package.py` (rebuilds the LRAE
data package from saved bytes; `collect` records the lookups it needs).

Tools that run against the production schema, all offline apart from read-only lookups and
all carrying a `--selfcheck`:

| Tool | What it does |
| --- | --- |
| `tools/agency_layers_sql.py` | turns the organization memory and the LRAE packages into one transaction of SQL for the agency-intelligence tables |
| `tools/replay_attributions.py` | feeds each reviewed attribution's own passages to the production `resolve_program_office()` and reports where it agrees |
| `tools/monitor_forecast_revision.py` | alert C from `06`: LRAE lines whose forecast award window moved between releases |
| `tools/promote_plan.py` | matches the loaded offices against production, and writes the promotion statements to a file for review |
| `tools/trace.py` | the three questions from one data set: `status` (which forecast lines whose window has arrived show a notice or an award), `need` (one requirement across releases, offices, contracts, notices and awards), `notice` (an active notice traced to its office, history and candidate lines), `award` (a contract read back to the forecast and forward to what followed); estimates, ceilings and obligations always in separate columns |
| `tools/sandbox_schema.py` | the schema subset the loader fills (tables, constraints, indexes, trigger functions, triggers; FK-only targets as stubs), dumped from the local database with owners, grants and RLS dropped, so a contributor builds the database locally and runs `trace.py notice` / `need` against it |

## Status

| Deliverable | Status |
| --- | --- |
| 00 existing work + pilot definition | done (2026-09-16) |
| 01 source registry | done (2026-09-16); budget books pending manual retrieval |
| 02 organization map | done (2026-09-16) |
| 03 data-connection map | done (2026-09-16) |
| 04 attribution process + examples | done (2026-09-16); 19 reviewed examples, 17 directly documented after reading SAM.gov notices |
| 05 early signals + backtests | done; 10 backtests, 5 with public first-notice dates; budget-line table from Comptroller P-1/R-1; House FY2027 marks |
| 06 continuous-monitor design | done (2026-09-16); forecast-revision alert pattern confirmed against the 2024-to-2025 LRAE release diff (2026-09-18) |
| 07 implementation backlog | done (2026-09-16) |
| 08 organization memory format + code families | restructured 2026-09-18: observations, relationships, interpretations; retractions instead of end dates; reviewer fields |
| 09 manual collection runbook | done (2026-09-17) |
| contacts | split 2026-09-18 into observations (what a source says) and recommendations (routes with two confidences); every observation checked against saved bytes in `review_log.json` |
| 11 worked examples end to end (reviewer request 2026-09-20) | done (2026-09-20); organization change, forecast revision and ambiguous match traced source row to alert |
| LRAE data packages (reviewer request 2026-09-17) | done (2026-09-18); three releases packaged (2023 export, June 2024, June 2025), every sheet reconciled, joins labelled for 2025, release diffs in the newer packages. 2026-09-20: a row is a source record and nothing is marked duplicate at import (June 2024 rows 406, 408-411 recovered) |
| 12 three use cases on Navy examples (reviewer request 2026-09-20) | done (2026-09-20); NTCDL follow-on (upcoming), MIDS WDL SF3 presolicitation traced to the TDL Program Office, PMW 160 ESS with three generations of awards; forecast-status table over every FY26-or-earlier line; `tools/trace.py` reproduces each from the loaded tables and saved lookups |

## Evidence rules

- Official public sources only. A Wayback Machine capture of an official page counts as a dated
  copy of that page; the capture timestamp is recorded and is the "available by" date.
- Third-party mirrors (GovTribe, HigherGov, GovWin) may be cited as pointers, never as evidence.
- Every claim carries a source URL and an observation date. Inferences are labelled as such.
- Downloaded bytes live in `data/raw/` (not committed); their hashes are in
  `documents_manifest.jsonl`.

## Check

```bash
python -m pytest tests/
```
