# Research package: Navy (NAVWAR / PEO C4I) acquisition source map

Phase-one deliverables for the Federal Program Office Intelligence Trial, scoped by the
2026-09-16 assignment: source discovery, data understanding, worked examples, and an
implementation plan. Research and planning only: no production writes, no outreach.

## Review order

1. `00_existing_work_and_pilot.md` - what exists, what the pilot covers, verified organization
2. `01_source_registry.md` + `source_registry.json` - every source, inspected once
3. `02_organization_map.md` + `organization_seed.json`
4. `03_data_connection_map.md`
5. `04_attribution_process_and_examples.md` + `attribution_examples.json`
6. `05_early_signals_and_backtests.md` + `backtests.json`
7. `06_continuous_monitor_design.md`
8. `07_implementation_backlog.md`

Supporting files: `documents_manifest.jsonl` (every document fetched: URL, hash, retrieval
method and time), `manual_pdf_requests.json` (documents that still need a human to fetch),
`tools/fetch.py` (the fetch-and-record helper).

## Status

| Deliverable | Status |
| --- | --- |
| 00 existing work + pilot definition | in progress |
| 01 source registry | planned |
| 02 organization map | planned |
| 03 data-connection map | planned |
| 04 attribution process + examples | planned |
| 05 early signals + backtests | planned |
| 06 continuous-monitor design | planned |
| 07 implementation backlog | planned |

## Evidence rules

- Official public sources only. A Wayback Machine capture of an official page counts as a dated
  copy of that page; the capture timestamp is recorded and is the "available by" date.
- Third-party mirrors (GovTribe, HigherGov, GovWin) may be cited as pointers, never as evidence.
- Every claim carries a source URL and an observation date. Inferences are labelled as such.
- Downloaded bytes live in `data/raw/` (not committed); their hashes are in
  `documents_manifest.jsonl`.

## Check

```bash
python -m pytest tests/test_research_artifacts.py
```
