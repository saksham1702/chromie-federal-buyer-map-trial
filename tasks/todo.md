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
- [x] organization sources
- [x] agency-intent sources (DoN budget books, posture, IT Dashboard)
- [x] congressional sources (govinfo, congress.gov)
- [x] planned-requirement sources (LRAEs, industry days, CSO, SBIR)
- [x] active-acquisition sources (SAM extract, SAM API, PIEE, SeaPort-NxG)
- [x] award sources (USAspending, FPDS, contract announcements, GAO)
- [x] identifier crosswalk narrative; requested vs enacted vs obligated vs ceiling

## P3 organization map + data-connection map
- [x] 02_organization_map.md (timeline: SPAWAR->NAVWAR, PEO EIS->Digital/MLB, PAE Mission Systems)
- [x] 03_data_connection_map.md (identifiers, joins, gaps, mermaid)

## P4 attribution process + >=10 examples across >=3 PMWs
- [x] candidate pool from FPDS N00039 (+NIWC) and SAM extract
- [x] examples incl. same-office-different-PEO, funding!=contracting, task order vs IDV, reorg case, unknown
- [ ] optional 1h cross-check with prod resolve_program_office() offline

## P5 early signals + >=5 backtests
- [x] current signals (budget, congressional marks, LRAE, industry day, expirations)
- [x] backtests with cutoff discipline; validator enforces available_by <= cutoff

## P6 monitor design + backlog + final review
- [x] 06_continuous_monitor_design.md with 4 sample alerts and table mapping
- [x] 07_implementation_backlog.md
- [x] random spot-check of 3 examples + 1 backtest; git clean; dot_clean

## Done 2026-09-17
- [x] congressional marks: House FY2027 DoD appropriations report lines for the tracked OPN items (CANES +$50.0M)
- [x] PEO Digital / PEO MLB live pages checked: no office codes published
- [x] NAVSEA LRAE relocation pointer recorded (per-warfare-center forecast pages)
- [x] 08 organization memory format + org_code_families.json
- [x] 09 manual collection runbook with reviewer checklist
- [x] recall-first posture in 04/06; contact_candidates.json (public sources, confidence labels)

## Open follow-ups
- [x] register the SAM.gov full extract (current dataset only) and confirm BT07/BT08 first-notice dates
- [x] SAM archived FY2025 file downloaded and used (BT04 reworked, BT09/BT10 added); FY2021 still to pull for BT05
- [~] request-vs-enacted amounts now from the Comptroller P-1/R-1 tables; DoN RDT&E BA7-8 and FY2026 exhibit narratives still queued (secnav resets)
- [ ] complete FY2026 FPDS scan for N00039 (host resets) to settle BT06 and the PMW 120 / NMT / Platform Integration forecasts
- [ ] optional 1h: replay the 19 examples through prod `resolve_program_office()` offline

## Needs from Saksham
- [x] api.data.gov key received and stored in .env; SAM itself is served by the keyless site API (api.sam.gov host dead), so the key is only for other api.data.gov services
- [x] WARP-off tested 2026-09-16: block is geographic (Indian egress also 403); Browserbase (US egress) works and fetched 70+ live pages and files

## Phase two: reviewer comments of 2026-09-17 (data accuracy first)
- [x] LRAE reproducible package: `research/tools/lrae_package.py`, `datapack/lrae_navwar_2025-06/`, `tests/test_lrae_datapack.py`
- [ ] contacts: sourced facts separated from recommendations; role types; historical vs current confidence
- [ ] organization memory: observations / relationships / interpretations; retractions instead of `valid_to`; PMS 485 dates unknown
- [ ] second LRAE release for the diff (Wayback index still offline for older captures)
- [ ] independent reproduction of a sample with reviewer identity and date recorded
