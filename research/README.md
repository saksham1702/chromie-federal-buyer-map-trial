# Navy agency intelligence: the research package

An intelligence layer over the Department of the Navy's acquisition record: which office wants what, when, and on
what evidence. The package collects official public sources, models them into a dated organization memory and
dated events, loads them into the agency-intelligence tables in one transaction, and reads them back as a weekly
pulse, office books and object pages. Nothing is written to production; every run builds a local database from
nothing.

## Repository structure

```
chromie-federal-buyer-map-trial/
├── README.md                     # The trial assignment: what the system must prove
├── PROJECT_BRIEF.md              # The user problem and the product it asks for
├── AGENTS.md                     # Working agreement: evidence, facts and inferences kept apart
├── SECURITY.md                   # Data boundary: public official sources only
├── DECISIONS.md                  # Dated technical and product decisions, each with its reason
├── pyproject.toml                # The Python package and its dependencies
├── .env.example                  # The variables a run reads (values stay in a local .env)
│
├── src/buyer_map/                # The starter demo: validates and ranks the synthetic graph
├── data/
│   ├── synthetic/                # The example agency graph the starter demo reads
│   └── raw/                      # Every page and file downloaded (shared separately)
├── datapack/                     # Forecast releases as tables, rebuilt by lrae_package.py
├── build/                        # A pipeline run's outputs: SQL, graph, back-test results
├── tests/                        # The pytest suite: one file per tool or layer
│
└── research/
    ├── README.md                 # This file
    ├── docs/                     # The write-ups, in review order below
    ├── sources/                  # Source registry, documents manifest, coverage and source status
    ├── memory/                   # Navy organization memory: offices, people, vendors
    ├── events/                   # Navy dated statements, one file per family
    ├── results/                  # What the Navy layer reads back: corpus, labels, pulse
    ├── cassettes/                # Recorded model answers, so a rebuild costs nothing
    ├── agencies/                 # One folder per further agency, each with its README
    │   ├── darpa/                # DARPA layer: memory, events, results, sources
    │   ├── army/                 # Army layer: same folders, forecast from Army Materiel Command
    │   └── airforce/ nasa/ doe/ dhs/ noaa/   # Added 2026-09-26: memory and sources, not built yet
    └── tools/
        ├── pipeline.py           # Runs every stage in order (--list, --agency, --collect)
        ├── agency.py             # The Navy, DARPA and Army profiles; loads the rest
        ├── agency_profiles/      # One profile per later agency: codes, feeds, filters
        ├── fetch.py              # Saves one address under data/raw/ with its manifest row
        ├── context_fetch.py      # Renders a refused page through context.dev
        ├── browserbase_fetch.py  # Takes a file through a hosted browser
        ├── markdown.py           # A saved webpage as Markdown, shared by every HTML reader
        ├── backfill_manifest.py  # Adds manifest rows for saved files that have none
        ├── sam_notices.py        # SAM.gov notices by number and by contracting office
        ├── fpds_sweep.py         # FPDS awards by contracting office, and their modifications
        ├── assistance.py         # Grants and cooperative agreements from USAspending
        ├── sbir.py               # SBIR and STTR topics from the DoD portal
        ├── news.py               # Articles as dated observations (Exa, GDELT, RouterGrowth)
        ├── oversight.py          # Oversight reports into dated findings
        ├── remarks.py            # Leaders' speeches, statements and testimony into dated events
        ├── congress.py           # Committee reports into the directives that name the agency
        ├── fedreg.py             # The agency's Federal Register documents
        ├── protests.py           # GAO bid protests into dated protest events
        ├── budget.py             # Budget justification books into line items and amounts
        ├── lrae_package.py       # Forecast releases into the datapack, release against release
        ├── org_memory_lrae.py    # Navy organization memory from the forecasts
        ├── org_memory_darpa.py   # DARPA organization memory from its own pages
        ├── org_memory_army.py    # Army organization memory, and the shared SAM.gov hierarchy reader
        ├── org_memory_airforce.py  # Department of the Air Force memory from SAM.gov's hierarchy
        ├── org_memory_nasa.py    # NASA memory from its own publications
        ├── org_memory_doe.py     # Department of Energy memory
        ├── org_memory_dhs.py     # Department of Homeland Security memory
        ├── org_memory_noaa.py    # NOAA memory
        ├── people.py             # Every named contact merged into people with dated positions
        ├── small_business.py     # Small business offices of the department and each command
        ├── notice_kinds.py       # What a SAM.gov special notice announces
        ├── llm.py                # The recorded model call every reader shares
        ├── reader.py             # The rules a model's reading must pass (verbatim passage)
        ├── vocabulary.py         # Event types, their procurement stage and polarity
        ├── agency_layers_sql.py  # Memory, datapack and events as one SQL transaction
        ├── schema_subset.py      # The table subset a local database needs
        ├── graph_export.py       # The organization graph as the program-office resolver reads it
        ├── backtest.py           # The frozen corpus, the outcome labels and the back-test
        ├── baselines.py          # The simple baselines the back-test must beat
        ├── pulse.py              # Each requirement scored as of a date, the week's changes, actions
        ├── buying_dna.py         # A contracting office's buying book from its awards
        ├── vendors.py            # Vendors resolved by their unique entity identifier
        ├── coverage.py           # Which source covers each question, and what each collected
        ├── trace.py              # One requirement across forecasts, notices and awards
        ├── pages.py              # Object pages: office, vendor, person, requirement cell
        ├── office_wiki.py        # A page per program office, written from the record
        ├── ask.py                # The questions: what changed, who buys, meeting brief, incumbents
        ├── navy.py               # The read surface in one command, for any agency profile
        ├── outreach.py           # From what a company sells to one outreach letter
        ├── outreach_compare.py   # The same question to Claude with and without these tools
        ├── dossier_compare.py    # The comparison on one full company dossier
        ├── monitor_forecast_revision.py  # Alerts when a forecast line's window or value moves
        ├── replay_attributions.py  # Attributions replayed through the production resolver
        └── promote_plan.py       # Promotion SQL written to a file, never run
```

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
10. `docs/19_navy_versus_darpa.md`: the same layer read against DARPA, family by family, what that corrected in `docs/14`, and (section 8) the DARPA layer as built on 2026-09-24 under `agencies/darpa/`

The second agency lives under `agencies/darpa/` with the same four folders (`memory`, `events`, `results`, `sources`)
and a README listing every file, the tool that writes it and how to rebuild it;
the tools write there when `AGENCY=darpa` is set (`tools/agency.py` holds the Navy, DARPA and Army profiles; `tools/pipeline.py --agency darpa`).
Its `results/` holds the corpus frozen from the `darpa_proof` database, the outcome labels, the office reads and the notice
kinds (read on 2026-09-25, replayed from the shared cassettes), the pulse and the Buying DNA (`docs/19`, section 9);
`pages.py` and `ask.py` read them under `AGENCY=darpa`.
The ledger and the saved bytes are shared, and a collector running under another profile marks its note with the
profile key (`oversight watch [darpa]: ...`), so each layer's readers keep their own documents.

The third agency lives under `agencies/army/` in the same four folders, with its README; its tools run with
`AGENCY=army` against the `army_proof` database. The Army Materiel Command forecast is its datapack
(`datapack/amc_2026-05/`), the ASA(ALT) organization chart and SAM.gov organization records seed its memory, and
the collect stages that sweep its notices, awards and leaders have not been run, so it has no outcome yet.

Five more layers were added on 2026-09-26, each as one profile under `tools/agency_profiles/` (`airforce`, `nasa`,
`doe`, `dhs`, `noaa`), an organization memory reader (`tools/org_memory_<key>.py`) and an `agencies/<key>/` folder
with its README, source registry and coverage matrix: the Department of the Air Force with the Space Force, NASA with
all centers, the Department of Energy (headquarters, the Office of Science, ARPA-E, EERE and NNSA), the Department of
Homeland Security as a whole, and NOAA under Commerce. Their first collection ran on 2026-09-26 and 2026-09-27 without
API keys; each README lists what was collected and what was not, and the build stages have not run for them yet.


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
| `small_business.py` | The small business office of the department and each command, from the Department of War's directory and each office page |
| `lrae_package.py`, `org_memory_lrae.py` | The forecast releases into the datapack and the organization memory |
| `agency_layers_sql.py` | The memory, the datapack and every family's events as one transaction of SQL for the agency-intelligence tables |
| `backtest.py`, `baselines.py` | The frozen corpus and the outcome labels; the back-test and its baselines are computed into `build/` |
| `pulse.py`, `vocabulary.py` | Every requirement cell scored as of a date, the week's changes and the actions with evidence; the stage and polarity vocabulary |
| `buying_dna.py`, `vendors.py` | Office books from the saved awards; vendors resolved by UEI |
| `pages.py`, `trace.py` | Object pages (office, vendor, person, cell) and the traced questions (`status`, `need`, `notice`, `award`) |
| `ask.py` | Questions put to the twin: what changed inside an organization on a topic, which offices buy a capability, a meeting brief, how long past buys took, what weakens each incumbent, a competitor's moves, whom to team with for a capability, meeting notes kept apart, and the evidence room for one requirement |
| `office_wiki.py` | A page per program office written from the record, and the model's reading, against those pages, of a notice filed at a contracting office that names no office, a live award signed at an office that owns no requirement, an SBIR topic a command published and a committee statement addressed to the department; the views use the kinds a masked check holds |
| `notice_kinds.py` | What a SAM.gov special notice announces (an industry day, an intent to award a sole source, a request for information, a draft solicitation), read by one recorded model call and kept only when the words that state it are in the notice |
| `outreach.py` | From what a company sells to one outreach letter: a model walks the object pages to the agency, command, program executive office and program office, that office's requirements, the initiatives above it and the people tied to it, and the rules refuse whatever the record does not carry; `audit SLUG` writes the run as one file a second model can check without the tools |
| `outreach_compare.py` | The same question put to Claude out of the box (web only, or on a copy of this data with the walk removed) and to Claude on the platform's tools (alone, or with the web), every answer checked by the outreach rules and by a blind second model, with tokens, turns, time and the platform tools each session called |
| `navy.py` | The platform's read surface in one place, as of the record's date: the organization tree, forecast rows in full, notices, topics, initiatives, people, object pages, the twin's questions, the pulse, protests, office wiki pages, buying books, vendors, traces, forecast revisions, the outreach checks and where each record is published; an office opens with its wiki page, buying book, next actions, ending incumbents, protests and forecast revisions beside it; `serve` offers every command as an MCP tool, the only way a platform session reaches the record |
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
