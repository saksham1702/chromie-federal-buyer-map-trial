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
- [x] complete FY2026 FPDS scan for N00039 (2026-09-18, through June 2026): BT06 timing miss, no Platform Integration 2.0 award, NMT sustainment orders only
- [ ] optional 1h: replay the 19 examples through prod `resolve_program_office()` offline

## Needs from the operator
- [x] api.data.gov key received and stored in .env; SAM itself is served by the keyless site API (api.sam.gov host dead), so the key is only for other api.data.gov services
- [x] WARP-off tested 2026-09-16: block is geographic (Indian egress also 403); Browserbase (US egress) works and fetched 70+ live pages and files

## Phase two: reviewer comments of 2026-09-17 (data accuracy first)
- [x] LRAE reproducible package: `research/tools/lrae_package.py`, `datapack/lrae_navwar_2025-06/`, `tests/test_lrae_datapack.py`
- [x] contacts: `contact_observations.json`, `contact_recommendations.json`, `review_log.json` (all observations checked against saved bytes)
- [x] organization memory: `organization_seed.json` v2 (observations / relationships / interpretations, retractions, reviewer fields); 08 rewritten; PMS 485 dates unknown
- [x] review-bot findings: UIC family tightened and alias-first classifier; budget line wording; PMS 485
- [x] second and third LRAE releases (June 2024, 2023 export) recovered via the Wayback index and packaged with diffs
- [ ] independent reproduction of a sample with reviewer identity and date recorded

## Phase three: reviewer comments of 2026-09-20 (data accuracy as it lands)

- [x] "over $1B" is not $1B: open-ended ranges refused rather than flattened, `as_stated` kept
      on every row that loads, 4 rows and 65 "No Range Specified" skipped out loud
- [x] historical org relationships survive the import: NEN under PEO EIS to 2020-05-13 loads
      beside the current parent. PMS 485 still blocked - its dated claim is retracted and the
      surviving one has no end date
- [x] follow a requirement across releases with or without a PID: staged matcher plus
      similarity candidates. Followed records 105 -> 178 (2024-25), 31 -> 66 (2023-25),
      59 -> 138 (2023-24); ambiguous keys kept with their reasoning
- [x] office assignments are per-release observations; a release naming a different office
      branches instead of overwriting. Self-checked, since no release pair exercises it
- [x] `research/11_worked_examples_end_to_end.md`: org change, forecast revision, ambiguous
      match, each traced from the spreadsheet row to the alert
- [x] found while walking it: per-release office rows fanned every alert out once per release
      (28 rows for 14 revisions). Alerts now collapse to one and name a contested owner
- [ ] reviewer to verify the three examples against the sources
- [ ] decide: a requirement that slips a fiscal year and changes value is reported as a slip
      only, because value chains are scoped to one fiscal period (0 value revisions, 14 timing)
- [ ] deferred at the reviewer's request: shipping raw files and generated CSVs as one package
- not doing now: AI-client change measurement

## Phase four: reviewer comments of 2026-09-20 10:50 (dedupe, three use cases, Navy examples)

Deadline: reviewer's call 2026-09-21 11:40 PST. Commit locally only.

- [x] Dedupe: a source row is a source record. `record_key()` = PID, else `row:<n>`;
      no `duplicate` decision; keys asserted unique per release; reconciliation lists
      rows sharing title+office with the description that tells them apart
- [x] Test first: `test_lrae_datapack.py` keys unique, decision set without `duplicate`;
      selfcheck case for rows 406/408-411 shape
- [x] Rebuild three datapacks; 2024 included 154 -> 161; prose that described the old key
      (09 runbook, DECISIONS 2026-09-18, navy-sources-map, SOURCE.json text)
- [x] DECISIONS entry: import never merges rows; identity is resolved later, as a candidate
- [x] Reload a clean scratch db from the rebuilt layers (append-only tables: fresh db, not UPDATE)
- [x] `research/12_three_use_cases_navy.md`: upcoming (NTCDL follow-on, PMW/A 170), active
      notice -> owner (MIDS WDL SF3, PMA/PMW 101 vs C4IEXEC code), historical (PMW 160 ESS
      N0003917F3000 -> N0003922F3000 -> N0003926FG001) with estimate | ceiling | obligations
      kept apart; table of FY<=26 forecast lines: solicited? awarded?
- [x] Live top-ups recorded in the manifest through fetch.py / sam_notices.py (no unrecorded reads)
- [x] `research/tools/trace.py`: `upcoming`, `notice <id|solnum>`, `history <pid|piid>` over the
      loaded tables + datapack + saved SAM/FPDS; `--selfcheck`. Renamed subcommand `notice` (was `rfp`)
- [x] README index + status row for 12; TASK.md; ctx file; commits
- found on the way: NAVWAR notices of 2026-08 rename PMA/PMW 101 to "TDL Program Office (PMW-530)";
      a 2026-05 notice puts PMW/A 170 under PAE MS CPE Comms/Sensor/EW/PNT. Both in the org memory
      (obs:080-085, rel:065/066, rel:011 ended, int:006), dates inferred from the PAE stand-up
- found on the way: MIDS-LVT (2026-04-13, two IDVs $307.7M each) and ADNS MAC (2026-05-21/22, five
      IDVs $452.9M each) were awarded; MIDS WDL SF2 awarded 2025-09-29 on the forecast quarter
- [ ] reviewer: accept/reject the seven candidate rows in research/12 section 4; decide the bridge-vs-follow-on
      home of the NTCDL ESS presolicitation; confirm int:006 and the PMW-530 aliases

## Phase six: reviewer comments of 2026-09-20 23:29 (handed to the contributor)

- [x] database kit for the contributor: `sandbox_schema.py`, `~/Downloads/navy-db-kit-2026-09-21` (+ zip), verified by two independent loads
- [ ] asks 1-5 (negatives wording; notice -> office -> names -> forecasts -> awards with source + record id; same vs related; PEO/PAE scoped; one watch example): contributor, in the sandbox
- [ ] ask 6 (push importer fixes to PR #1, fresh load with main's migrations, transcripts): owner, after the contributor's changes land
- [ ] sandbox re-sync so the generator and DECISIONS entry reach him; issues filed from the `ask` template
