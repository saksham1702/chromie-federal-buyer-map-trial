# DARPA agency intelligence

The Defense Advanced Research Projects Agency read by the same tools as the Navy layer: which technical office
wants what, when, and on what evidence. Nothing here is written by hand except the source registry and the
coverage matrix; every other file is the output of one tool under `research/tools/`, run with `AGENCY=darpa`.
The comparison with the Navy, family by family, is `research/docs/19_navy_versus_darpa.md`.

## Layout

| File | Written by | What it holds (as built on 2026-09-25) |
| --- | --- | --- |
| `memory/organization_seed.json` | `org_memory_darpa.py build` | 31 nodes: the agency, the Director's Office, six technical offices with their office codes, four former offices the notices still name (MTO, I2O, ACO, APO), the Contracts Management Office, eight contracting offices of other agencies that sign DARPA-funded awards, SBPO, CSO and eight persons, each claim resting on a verbatim passage of a saved page |
| `memory/people.json` | `people.py build` | 685 people from 1,296 observations (a role mailbox or an address written as the name is one contact per address): 1,162 SAM.gov points of contact, 127 staff listing entries with their start dates, 4 from darpa.mil pages, 3 from conference pages |
| `memory/vendors.json` | `vendors.py build` | 1,172 vendors resolved by UEI from 3,536 base awards |
| `memory/small_business_offices.json` | `small_business.py build` | The agency's small business office as the Department of War directory lists it, with its own page saved; the page prints no contact lines |
| `events/budget_lines.json` | `budget.py extract` | 48 program elements from the FY2026 and FY2027 RDT&E justification books (Exhibit R-2) |
| `events/sbir_topics.json` | `sbir.py build` | 170 DARPA-component SBIR/STTR topics open FY2020 on |
| `events/remarks_events.json` | `remarks.py extract` | 72 dated events from 16 documents: 52 from 8 hearing statements, 20 from 8 conference pages |
| `events/remarks_discovered.json` | `remarks.py discover` | The 8 conference pages the web search found, with the query that found each |
| `events/oversight_events.json` | `oversight.py extract` | 4 reports read (3 GAO products, 1 Inspector General evaluation); 1 finding kept, and 1 not kept because the remediation it named is not written so in the report |
| `events/news_observations.json` | `news.py build` | 5 observations from 2 darpa.mil articles |
| `events/fedreg_events.json` | `fedreg.py build` | 2 Federal Register documents whose title, action or abstract names DARPA |
| `events/congress_events.json` | `congress.py build` | 1 directive naming DARPA in the 3 committee reports saved |
| `events/protest_events.json` | `protests.py build` | Empty: the docket stage has not been run for DARPA |
| `events/assistance_awards.json` | `assistance.py build` | Empty until the collect job takes the USAspending grant and cooperative agreement pages |
| `results/notice_kinds.json` | `notice_kinds.py build` | What each of 404 special notices announces, 332 kept with the words that say so |
| `results/corpus.json` | `backtest.py freeze` | 5,531 dated events, 312 outcomes, 1,117 needs and 23 organizations frozen from the database; 4,126 of the events are incumbent awards and their end dates |
| `results/outcome_labels.json` | `backtest.py label` | The office and the names each outcome goes by, in its own words |
| `results/office_reads.json` | `office_wiki.py build` | 693 notices, 845 awards, 165 topics and 1 directive read against the office pages (a notice whose title carries an office code is placed by the record); 189 notices, 90 awards and 44 topics placed, the directive not placed |
| `results/pulse.json` | `pulse.py check` | 552 cells scored as of 2026-09-25, the week's changes and 546 actions, 388 of them an incumbent contract ending |
| `results/buying_dna.json` | `buying_dna.py build` | How the Contracts Management Office buys (2,462 base awards signed from 2019-10-03 to 2026-06-25), the 52 offices of other agencies that sign DARPA-funded awards, and the technical offices the awards are placed under |
| `sources/source_registry.json` | by hand | 19 sources, two of them the agency's own (the site and the staff listing) |
| `sources/coverage_matrix.json` | by hand, validated by `coverage.py` | 7 offices by 13 evidence families |
| `sources/source_status.json` | `coverage.py status` | What each registered source last collected: 16 of 19 have collected something |

`build/darpa/` (gitignored) holds what the load and read-back stages make: `schema.sql`, `layers.sql`, the
organization graph, the back-test results and the baselines.

## Rebuilding

The database is local only (port 54322); set `SCHEMA_DB_CONTAINER` to the running database container first.

    export AGENCY=darpa
    python research/tools/pipeline.py --db darpa_proof --list
    python research/tools/pipeline.py --db darpa_proof --only people --refresh    # one stage
    python research/tools/pipeline.py --db darpa_proof --refresh                  # every build and read-back stage
    python research/tools/pipeline.py --db darpa_proof --collect                  # also take what is new from each source

A build stage reads only what is saved; model answers replay from the shared cassettes, and a record not seen
before is one model call, which needs `OPENAI_API_KEY`. The read-back stages compare with the files above and
fail on any difference unless `--refresh` is given. The saved bytes, the documents ledger and the cassettes are
shared with the Navy layer.

## How DARPA differs from the Navy

| Point | Navy | DARPA |
| --- | --- | --- |
| Forecast | Long Range Acquisition Estimates, one package per command release | None published; the datapack and revision stages are skipped |
| Who owns a requirement | Program offices and program executive offices | Technical offices (`owner_types` in the profile) |
| Contracting | Several contracting offices, swept by office code | One (HR0011); awards other agencies sign for DARPA are swept by funding agency 97AE |
| Office codes in text | PMW, PMS and PMA with a three-digit number | The office abbreviation (BTO, DSO, STO, TTO and the former MTO, I2O, ACO, APO), with or without a number; CSO is not read, because it also names a commercial solutions opening |
| Incumbents | Contracts the forecast rows name, and the swept awards | The swept awards alone: 3,513 base awards state a completion date and a description |
| Grants | None swept | Grants and cooperative agreements from USAspending (452 since FY2020), which FPDS does not carry |
| Budget | Procurement lines (Exhibit P-1) | Program elements (Exhibit R-2), one RDT&E book a year |
| Leaders' words | A speech archive and hearing feeds | The budgets and testimony page, read as the leaders family |
| People | Notices, forecast contacts, speakers, witnesses | The same, plus the published staff listing with office and start date |
| Federal Register | Agency slug search | Term search on the full name, kept only where the title, action or abstract names DARPA |

Every difference is a key in the `DARPA` profile of `research/tools/agency.py`; the tools branch on the agency
only to choose its folders.

## Results, 2026-09-25

The back-test replays each outcome against the events public before it. With no forecast, DARPA's outcomes are
reached late or not at all by the three-family bar: recall 0.045 at 180 and 90 days and 0.051 at 30 days over
312 outcomes, 19 reached, median lead 309 days. The bar's precision is 0.774: of 244 pilot cells, 37 reached it,
6 are too recent to judge, and 24 of the 31 judged were followed by a notice or award within a year. The
one-family and two-family bars reach more (recall 0.529 and 0.228 at 180 days) at lower precision (0.725 and
0.562).

The incumbent book loads without a forecast: every swept award that states a completion date and a description
is an "incumbent contract ends" item (3,513 in the database), so the incumbent family now stands beside the
notices in the back-test, the pulse and the questions (`ask incumbents`, `ask moves`, `page vendor`). The
precision measured before the book loaded was 0.952 over 21 judged cells; both are kept as read.

A record owned by a technical office carries its code (DSO, not Defense Sciences Office), and the pilot offices
are named by code. The office-read prompts name DARPA, where they named the U.S. Navy under every profile, so the
model read every record again: 189 of 693 notices, 90 of 845 awards and 44 of 165 topics placed.

## Open

- The grants stage has not been run: the collect job takes the 452 awards, five pages of 100.
- The SAM.gov yearly extracts are registered for DARPA but not yet filtered to its notices before FY2022.
- The GAO protest docket answers the context.dev reader; the dockets stage has not been run for DARPA.
