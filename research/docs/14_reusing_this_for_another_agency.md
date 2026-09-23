# 14 - Reusing this for another agency: what travels, what is written once per agency

The pipeline runs as eight stages (`research/tools/pipeline.py`). Six of them hold no knowledge of
the Navy: they read whatever the organization seed, the datapack and the saved documents contain.
Two things are written once for each new agency: the reader for that agency's forecast artifact,
and the organization seed that names its offices. Everything downstream of those two follows.

## In plain terms

The agencies differ in what they publish and where. They do not differ in what a requirement is,
how a notice relates to a forecast line, what an award closes, or how an article is read as a
dated observation. The code that carries the second group is the pipeline; the first group is a
pair of adapters and a list of addresses.

## The stages

| stage | what it does | agency knowledge |
| --- | --- | --- |
| watch | polls the feeds and index pages for articles it has not saved | the feed addresses |
| sweep | one discovery query per office, then retrieves what is new | none; the queries are the seed read back |
| datapack | reads the forecast releases and compares them release to release | the forecast format |
| news | models every saved article as dated observations with a passage per claim | none |
| schema | writes the loaded-table subset of the production schema | none |
| layers | emits needs, assertions, evidence, organizations and brain items | none |
| database | creates the database from nothing and loads the schema and the rows | none |
| checks | every tool's selfcheck and the test suite | none |

`--collect` adds the two network stages; without it a rebuild is offline and deterministic, and
repeats byte for byte.

## What travels unchanged

| part | why it travels |
| --- | --- |
| `fetch.py`, `browserbase_fetch.py`, `research/sources/documents_manifest.jsonl` | every retrieval is recorded with its bytes, SHA-256 and retrieval time, whatever the host; the US-egress browser is the answer to any host that refuses this address |
| `sam_notices.py` | SAM.gov is the single notice system for the whole federal government, so the notice reader, the attachment handling and the office-code extraction are agency-independent |
| the award readers (FPDS, USAspending) | both are government-wide, keyed by contract and solicitation number |
| the staged matcher in `lrae_package.py` | identifier, then title under the same office, then incumbent contract, then title similarity, with a candidate that is never promoted; the stages are about records, not about the Navy |
| the reading vocabulary in `trace.py` | awarded, solicited, cancelled, review, restructured, delayed, open, not yet due, not dated, with one outcome word and the rest appended |
| `news.py` | the article model, the source types, the claim passage, and the reading against the record as new signal, corroboration or conflict; the provider behind discovery is a flag |
| `agency_layers_sql.py` | emits into the production tables (`gov_needs`, `gov_intelligence_assertions`, `gov_intelligence_evidence`, `agency_brain_items`), which are agency-independent |
| `research/docs/08_org_memory_format.md` | observation, relationship and interpretation, with nothing invented and every negative scoped to the searches it rests on |

## What is written once per agency

| item | effort | notes |
| --- | --- | --- |
| `research/memory/organization_seed.json` | the largest single piece | the offices, their aliases, their parentage and their people, each on a source; the sweep queries, the alias resolution and the relevance filter are all this file read back out |
| a forecast reader | one adapter | the Navy publishes the Long-Range Acquisition Estimate as a spreadsheet on a fixed template; another agency's equivalent has different columns and may not exist at all, in which case notices and awards carry the requirement on their own |
| the office alias table | with the seed | including names that were valid until a stated date, so an older document still resolves |
| the feed list in `news.py` | short | the agency's own newsroom, the department's contract announcements, and the trade titles that cover it |
| the egress decision | short | which of the agency's hosts refuse a non-US address, recorded as an access finding rather than as a silence |
| the budget table | manual | the P-1 and R-1 line items for the agency's programs |

## Where to start for other agencies

Each entry below is the artifact to look for first, to be confirmed during collection and recorded
in `research/docs/01_source_registry.md` with what was actually found. Nothing here is a stored fact.

| agency | forecast artifact to look for | notes on the other sources |
| --- | --- | --- |
| Air Force, including Space Force | acquisition forecasts published by the major commands and centers; no single department-wide spreadsheet is assumed | notices and awards as usual; the program offices are named in Space Systems Command and Air Force Life Cycle Management Center releases |
| Army | the long-range and advance planning briefings published by the program executive offices | the same notice and award path; the office names are in the PEO structure |
| Department of Energy | the procurement forecasts of the National Nuclear Security Administration and the site offices | management and operating contracts behave differently from ordinary procurements and need their own reading |
| Department of Homeland Security | the department's acquisition planning forecast | the components buy separately, so the office resolution matters more than the forecast format |
| NASA | the agency procurement forecast, by center | center-level offices and a large share of research awards |
| National Science Foundation | assistance awards rather than procurement | the requirement model applies to the procurement side only; the award side is grants and is read as such |
| NOAA | the acquisition forecast published by the department's procurement office | a large share of the work sits under the parent department's contracting offices |
| DARPA | no forecast of the same kind | the entry point is the broad agency announcement and the notices under it; the news layer carries more weight here than the forecast layer |
| Veterans Affairs | the forecast of contracting opportunities | a high volume of small actions, so the matching stages will produce more candidates than the Navy set does |

## The order of work for a new agency

1. Record the sources and the access findings first, including every host that refuses this
   address, so later silences are scoped.
2. Write the organization seed from the agency's own pages and notices, with each node on a source.
3. Collect notices and awards for the offices in the seed; these alone produce requirements,
   because a notice is an entry point.
4. Add the forecast reader if the agency publishes a forecast, and run the release comparison.
5. Run the news stages; the queries come from the seed, so this needs no new writing.
6. Load and read back. The checks that hold for the Navy hold here, because they test the rules,
   not the data.

## What does not change

Nothing is invented for a new agency. A record exists because a source states it, a negative names
the searches it rests on, and a conflict between two sources is reported rather than resolved.
