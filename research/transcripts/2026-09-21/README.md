# Transcripts of 2026-09-21: the examples surviving ingestion and retrieval

A database built from nothing on 2026-09-21, loaded once, then read by the tools. Every file
here is the unedited standard output of one command against that database.

## How the database was built

| step | command |
| --- | --- |
| schema | `python research/tools/sandbox_schema.py schema.sql` — the loaded-table subset (tables, constraints, indexes, trigger functions, triggers; FK targets as stubs) dumped from the local Supabase container. Every column that `origin/main`'s `20260917051648_reconcile_agency_intelligence_prerequisites.sql` and `20260917051658_agency_program_intelligence.sql` declare for the loaded tables is present in that dump (checked column by column on 2026-09-21) |
| rows | `python research/tools/agency_layers_sql.py > layers.sql 2> layers.skipped.txt` — producer version 3, from the committed `datapack/` and `research/organization_seed.json` |
| load | `createdb navy_proof; psql navy_proof -v ON_ERROR_STOP=1 -f schema.sql; psql navy_proof -v ON_ERROR_STOP=1 -f layers.sql` |

Row counts are in `row_counts.txt` and equal the counts of the database handed to the contributor
on 2026-09-21. What the loader refused to load, and why, is `layers.skipped.txt` (unchanged). Every
office (30), edge (31) and evidence row (522) carries a `source_url`.

## What each transcript answers

| file | command | reviewer ask |
| --- | --- | --- |
| `notice_f69d6c52_mids_wdl_sf3.txt` | `trace.py notice f69d6c525c9f494fa08ea8fd852f5cdd` | notice id -> owning office, its names over time with observation ids and URLs, ancestry hop by hop with the relationship and its evidence, the PEO-level consolidation kept at its level, related forecasts (the SF2 line as a related buy, not a candidate), related notices with links, awards with the FPDS record cited |
| `notice_e24dd802_egypt_aints.txt` | `trace.py notice e24dd802a17a40f3ba9192ebf4af7fd3` | the same for an RFP that is open; the forecast line as a candidate with its spreadsheet row; "no award found in the saved FPDS lookup ... as of 2026-09-20" with the lookup cited |
| `need_ntcdl_follow_on.txt` | `trace.py need N00039-25-RFPREQ-PMW/A-170-0001` | one requirement across three releases with each release's URL and hash, the incumbent's ceiling and obligations with their USAspending record, the loaded row ids, and the `Watch` block: where it stands, why it matters, what would confirm or invalidate it |
| `award_N0003922F3000.txt` | `trace.py award N0003922F3000` | a contract read back to the forecast and forward to its successor candidate |
| `status_fy26.txt` | `trace.py status` | every FY26-or-earlier line; negatives scoped to the searches' retrieval dates; `related:` notices kept out of the reading |
| `monitor_forecast_revision.txt` | `monitor_forecast_revision.py` | the revision alerts, with succession reported at the ancestor's level |
| `selfchecks.txt` | `--selfcheck` of the three tools | the rules above hold on fixed inputs |

The tools fetch nothing. Every source URL in these files is a row of `research/documents_manifest.jsonl`
or an observation in `research/organization_seed.json`, and the bytes are under `data/raw/`.
