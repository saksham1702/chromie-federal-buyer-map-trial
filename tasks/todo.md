# Working list - Navy (NAVWAR / PEO C4I) source map and monitoring plan

Plan: ~/.claude/plans/eager-hopping-rivest.md (approved 2026-09-16). Branch: trial/navy-navwar-peo-c4i.

## P0 setup
- [x] branch, research/README.md, tasks/todo.md, DECISIONS.md entry
- [x] tests/test_research_artifacts.py (skips until artifacts exist, enforces once they do)
- [x] research/tools/fetch.py (fetch, hash, record; direct or Wayback)

## P1 existing work + pilot definition (00_existing_work_and_pilot.md, organization_seed.json v1)
- [x] summarize trial repo + prod scaffolding: exists / usable / missing
- [x] verify PAE Mission Systems reorg from official releases (DVIDS, paemaritime), fetch + hash
- [x] verify PEO C4I program-office inventory (Wayback copies of peoc4i.navy.mil, tear sheets)
- [x] verify NAVWAR HQ / NIWC Pacific / NIWC Atlantic contracting offices (FPDS DoDAACs)
- [x] sibling PEOs (Digital, MLB) as hard negatives
- [x] define comprehensive coverage; list known public-data gaps

## P2 source registry (source_registry.json, 01_source_registry.md, documents_manifest, manual queue)
- [ ] organization sources
- [ ] agency-intent sources (DoN budget books, posture, IT Dashboard)
- [ ] congressional sources (govinfo, congress.gov)
- [ ] planned-requirement sources (LRAEs, industry days, CSO, SBIR)
- [ ] active-acquisition sources (SAM extract, SAM API, PIEE, SeaPort-NxG)
- [ ] award sources (USAspending, FPDS, contract announcements, GAO)
- [ ] identifier crosswalk narrative; requested vs enacted vs obligated vs ceiling

## P3 organization map + data-connection map
- [ ] 02_organization_map.md (timeline: SPAWAR->NAVWAR, PEO EIS->Digital/MLB, PAE Mission Systems)
- [ ] 03_data_connection_map.md (identifiers, joins, gaps, mermaid)

## P4 attribution process + >=10 examples across >=3 PMWs
- [ ] candidate pool from FPDS N00039 (+NIWC) and SAM extract
- [ ] examples incl. same-office-different-PEO, funding!=contracting, task order vs IDV, reorg case, unknown
- [ ] optional 1h cross-check with prod resolve_program_office() offline

## P5 early signals + >=5 backtests
- [ ] current signals (budget, congressional marks, LRAE, industry day, expirations)
- [ ] backtests with cutoff discipline; validator enforces available_by <= cutoff

## P6 monitor design + backlog + final review
- [ ] 06_continuous_monitor_design.md with 4 sample alerts and table mapping
- [ ] 07_implementation_backlog.md
- [ ] random spot-check of 3 examples + 1 backtest; git clean; dot_clean

## Needs from Saksham
- [ ] personal api.data.gov key for SAM Opportunities API (attachments only)
- [ ] WARP-off window when the blocked-URL batch is ready
