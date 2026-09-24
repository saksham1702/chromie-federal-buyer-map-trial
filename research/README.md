# Navy agency intelligence: the research package

An intelligence layer over the Department of the Navy's acquisition record: which office wants what, when, and on
what evidence. The package collects official public sources, models them into a dated organization memory and
dated events, loads them into the agency-intelligence tables in one transaction, and reads them back as a weekly
pulse, office books and object pages. Nothing is written to production; every run builds a local database from
nothing.

## Layout

| Folder | What it holds |
| --- | --- |
| `docs/` | The write-ups, in review order below, and `architecture.txt` (the whole chain in plain text) |
| `sources/` | `source_registry.json` (every source: publisher, access route, cadence, what it answers), `documents_manifest.jsonl` (every document fetched: URL, hash, method, time, outcome), `coverage_matrix.json` and `source_status.json` (which source covers each command and family, and what each has collected) |
| `memory/` | `organization_seed.json` (offices, codes, parent claims, each with dated observations), `org_code_families.json`, `org_page_statements.json`, `attribution_examples.json` (reviewed contract-to-office attributions), `review_log.json`, `contact_observations.json` and `contact_recommendations.json`, `people.json` (dated positions), `vendors.json` (one vendor per UEI) |
| `events/` | Dated statements by family: `oversight_events.json`, `remarks_events.json`, `remarks_discovered.json`, `protest_events.json`, `congress_events.json`, `fedreg_events.json`, `sbir_topics.json`, `budget_lines.json`, `news_observations.json` |
| `results/` | What the layer reads back: `corpus.json` (every dated event and outcome frozen from the database), `outcome_labels.json` (the office and names each outcome goes by, in its own words), `pulse.json`, `buying_dna.json` |
| `tools/` | Every stage as a command-line tool with `--selfcheck`; `pipeline.py` runs them in order |
| `cassettes/` | Recorded model answers, so a rebuild replays byte for byte and costs nothing |
| `../datapack/` | The forecast releases (LRAE) as regenerable packages, rebuilt with `tools/lrae_package.py build` |

The JSON and JSONL data files, the cassettes and the datapack are shared separately and are not kept in the
repository; place them at the paths above before running the pipeline or the tests.

## Review order

1. `docs/00_existing_work_and_pilot.md`: what existed, what the pilot covers
2. `docs/01_source_registry.md`: every source, inspected once
3. `docs/02_organization_map.md` and `docs/08_org_memory_format.md`: the dated organization memory
4. `docs/03_data_connection_map.md`: how the sources join
5. `docs/04_attribution_process_and_examples.md`: from a contract to the office that wanted it
6. `docs/06_continuous_monitor_design.md`: the monitor, its alerts and the weekly pulse
7. `docs/13_news_as_a_signal.md`: an article as a dated observation
8. `docs/17_one_requirement_told_in_order.md`: one requirement as an analyst reads it, every statement in the order it appeared
9. `docs/14_reusing_this_for_another_agency.md`: what travels to the next agency and what is written once for it

## Running it

    .venv/bin/python research/tools/pipeline.py --list
    .venv/bin/python research/tools/pipeline.py --db navy            # offline rebuild from saved sources
    .venv/bin/python research/tools/pipeline.py --db navy --collect  # also takes what is new from every source
    .venv/bin/python research/tools/pipeline.py --db navy --collect --refresh  # and rewrites the saved results

Collection stages touch the network and run only with `--collect`; each takes only what is new. Build stages read
what is saved, so an offline rebuild repeats byte for byte. The read-back stages compare with the saved results
and fail on any difference unless `--refresh` is given.

## Tools

| Tool | What it does |
| --- | --- |
| `fetch.py`, `context_fetch.py`, `browserbase_fetch.py` | One address saved under `data/raw/` and recorded in the manifest; a page a host refuses is rendered through context.dev from a United States address, a file through a hosted browser with one |
| `fpds_sweep.py` | FPDS awards by contracting office and signed-date window; `histories` follows each running award through its modifications |
| `sam_notices.py` | SAM.gov notices by number, and every notice a contracting office posted since FY22 |
| `protests.py` | GAO's docket of Navy bid protests into dated protest events |
| `congress.py` | NDAA and defense appropriations committee reports into the directives that name the Navy |
| `fedreg.py` | The Department of the Navy's Federal Register documents |
| `news.py` | Articles as dated observations, with the changes of charge they state |
| `oversight.py`, `remarks.py` | Oversight reports and leaders' words read into dated events by one recorded model call each |
| `budget.py` | Budget justification books into P-1 line items with their fiscal-year amounts |
| `sbir.py` | Navy SBIR/STTR topics from the DoD portal |
| `people.py` | Every contact, speaker and witness the sources name, merged into people with dated positions; the routes into each office (requirement side, contracting side, published channels) |
| `lrae_package.py`, `org_memory_lrae.py` | The forecast releases into the datapack and the organization memory |
| `agency_layers_sql.py` | The memory, the datapack and every family's events as one transaction of SQL for the agency-intelligence tables |
| `backtest.py`, `baselines.py` | The frozen corpus and the outcome labels; the back-test and its baselines are computed into `build/` |
| `pulse.py`, `vocabulary.py` | Every requirement cell scored as of a date, the week's changes and the actions with evidence; the stage and polarity vocabulary |
| `buying_dna.py`, `vendors.py` | Office books from the saved awards; vendors resolved by UEI |
| `pages.py`, `trace.py` | Object pages (office, vendor, person, cell) and the traced questions (`status`, `need`, `notice`, `award`) |
| `ask.py` | Questions put to the twin: what changed inside an organization on a topic, which offices buy a capability, a meeting brief, how long past buys took, what weakens each incumbent, a competitor's moves, whom to team with for a capability, meeting notes kept apart, and the evidence room for one requirement |
| `coverage.py` | The command by family coverage grid and the per-source status |
| `graph_export.py`, `schema_subset.py` | The organization graph as the program-office resolver reads it; the schema subset for a local database |
| `llm.py`, `reader.py` | The recorded model call every reader shares, and the rules a reading must pass (verbatim passage, registry authority) |
| `replay_attributions.py`, `monitor_forecast_revision.py`, `promote_plan.py` | Attributions replayed through the production resolver, the forecast-revision alert (the `revisions` stage), and promotion SQL written to a file for review |

## Evidence rules

- Official public sources only. A Wayback Machine capture of an official page counts as a dated copy of that page.
- Third-party mirrors may be cited as pointers, never as evidence.
- Every claim carries a source URL, an observation date and the passage; inferences are labelled as such.
- Downloaded bytes live in `data/raw/` (not committed); their hashes are in `sources/documents_manifest.jsonl`.

## Check

    python -m pytest tests/
