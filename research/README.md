# Research package: Navy (NAVWAR / PEO C4I) acquisition source map

Phase-one deliverables for the Federal Program Office Intelligence Trial: source discovery, data
understanding, worked examples, and an implementation plan for the NAVWAR / PEO C4I pilot.
Research and planning only: no production writes, no outreach.

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
11. `contact_observations.json` and `contact_recommendations.json` - likely public contacts per office with confidence labels
12. `../datapack/lrae_navwar_*/` - the NAVWAR LRAE releases (2023 export, June 2024, June 2025) as regenerable packages: every row accounted for, joins labelled, reconciliation, target-schema layers, diffs between releases

Supporting files: `documents_manifest.jsonl` (every document fetched: URL, hash, retrieval
method and time), `manual_pdf_requests.json` (documents that still need a human to fetch),
`tools/fetch.py` (the fetch-and-record helper), `tools/lrae_package.py` (rebuilds the LRAE
data package from saved bytes; `collect` records the lookups it needs).

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
| LRAE data packages (reviewer request 2026-09-17) | done (2026-09-18); three releases packaged (2023 export, June 2024, June 2025), every sheet reconciled, joins labelled for 2025, release diffs in the newer packages |

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
