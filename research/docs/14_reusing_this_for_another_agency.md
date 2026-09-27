# 14 - Reusing this for another agency: what travels, what is written once per agency

The pipeline runs as forty-three stages in three groups (`research/tools/pipeline.py --list`): sixteen
collection stages that touch the network, fourteen modelling stages that read what is saved, and thirteen
load and read-back stages. The rules they apply (what a requirement is, how a notice relates to a
forecast line, what an award closes, how an article is read) hold for any agency. What does not travel
is a list of constants inside the tools: the office code tables, the agency filters, the feed list, the
forecast reader and the organization seed. The table in "What is written once per agency" names each.
`research/docs/19_navy_versus_darpa.md` is the first reading of this procedure against an agency, and
the corrections it made to this document are listed there in section 6. Since 2026-09-24 the constants are
one profile per agency in `research/tools/agency.py`, chosen by the environment variable `AGENCY`
(`pipeline.py --agency <key>`); the DARPA layer built that day is described in `research/docs/19`, section 8.
The constant names in the stage table below are the profile keys the tools now read them from. The read-back tools
(`pages.py`, `ask.py`, `office_wiki.py`, `backtest.py`) read one more key, `reading`: how the agency writes an office code
in a notice, a hull or platform designator to strip from a title (none for an agency without one), a contract number in
running text, and the words that name the buyer rather than the requirement (`research/docs/19`, section 9). A machine
without the platform database builds the proof database from the exported kit: `SCHEMA_KIT=<kit folder>` makes the
`schema` stage write that export with a stand-in for the one table it stubs.

## In plain terms

The agencies differ in what they publish and where. They do not differ in what a requirement is,
how a notice relates to a forecast line, what an award closes, or how an article is read as a
dated observation. The code that carries the second group is the pipeline; the first group is a
pair of adapters and a list of addresses.

## The stages

The agency-knowledge column names the constants as the code stands on 2026-09-24.

| stage(s) | tool | what it does | agency knowledge |
| --- | --- | --- | --- |
| watch, sweep, news | `news.py` | polls the feeds, runs one discovery query per office, models every saved article as dated observations | `FEEDS`, `OFFICIAL_NAMES`, `STANDING_TERMS`; the sweep queries are the seed read back |
| audits, oversight | `oversight.py` | polls oversight.gov and the GAO feed, reads each report into dated findings | `AGENCY`, `QUERIES`, `REVIEWED_RE`, `NAMES_RE` |
| podium, remarks | `remarks.py` | polls the speech archive and the House hearing feeds, reads each into dated events | the archive addresses on navy.mil, `AGENCY`, `NAMES_RE`; the House feeds travel |
| contracts, changes | `fpds_sweep.py` | sweeps FPDS for each contracting office's base awards and follows their histories | `OFFICES`; the parser reads any office's page, Other Transactions included |
| solicitations | `sam_notices.py` | sweeps SAM.gov for every notice each contracting office posted | `SWEEP_ORGS`, `SWEEP_CODES`, `OFFICE_RE` |
| topics, programs | `sbir.py` | sweeps the DoD SBIR/STTR portal (every component) and models the kept topics | `component == "NAVY"`, `DEPARTMENT`, `COMMANDS` |
| dockets, protests | `protests.py` | takes GAO's docket and reads each case page | the docket's agency filter, `AGENCY` |
| reports, directives | `congress.py` | takes the committee reports and keeps the directives naming the agency | `NAVY_RE` |
| register, federal | `fedreg.py` | takes the Federal Register documents and types them | the agency slug `navy-department` |
| memory, datapack, revisions | `org_memory_lrae.py`, `lrae_package.py`, `monitor_forecast_revision.py` | reads the forecast releases into the memory and the datapack, compares releases | the forecast format and the alias table; absent where there is no forecast |
| budget | `budget.py` | reads the justification books into line items | the exhibit the profile names: P-40 (procurement books, the Navy) or R-2 (RDT&E books, DARPA), and the PB label |
| people | `people.py` | merges every named contact, speaker and witness into dated positions | `DEPARTMENT`, `EXECUTIVE` |
| schema, layers, database, graph | `agency_layers_sql.py`, `schema_subset.py`, `graph_export.py` | emits and loads the rows, exports the graph | `AGENCY_NAVY`, `LRAE_PROVIDERS`; the tables are agency-independent |
| backtest, pulse, baselines, dna, vendors, coverage | `backtest.py`, `pulse.py`, `baselines.py`, `buying_dna.py`, `vendors.py`, `coverage.py`, `trace.py` | reads the layer back and measures it | `PILOT_OFFICES`; `PACKS` and `SAM_ORG_NODES` in the tracer; otherwise none |
| checks | | every tool's selfcheck and the test suite | none |

`--collect` adds the eleven network stages; without it a rebuild is offline and deterministic, and
repeats byte for byte.

## What travels unchanged

| part | why it travels |
| --- | --- |
| `fetch.py`, `context_fetch.py`, `browserbase_fetch.py`, `research/sources/documents_manifest.jsonl` | every retrieval is recorded with its bytes, SHA-256 and retrieval time, whatever the host; a page rendered from a United States address (context.dev) or a US-egress browser for files is the answer to any host that refuses this address |
| `sam_notices.py` | SAM.gov is the single notice system for the whole federal government, so the notice reader, the attachment handling and the organization search are agency-independent; the organization ids swept and the office-code pattern are not |
| the award readers (FPDS, USAspending) | both are government-wide, keyed by contract and solicitation number; `fpds_sweep.fpds_entries` read DARPA's Other Transaction agreements with the same fields as Navy contracts (`research/docs/19`, section 3) |
| the SBIR portal sweep | reads every component newest first, so the saved pages already hold the other agencies' topics (197 DARPA topics beside 1,118 Navy ones on 2026-09-24); only the build's component filter is per agency |
| the staged matcher in `lrae_package.py` | identifier, then title under the same office, then incumbent contract, then title similarity; a candidate is promoted only when a model reading both rows quotes each verbatim and names them one acquisition; the stages are about records, not about the Navy |
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
| the office code tables | short | `fpds_sweep.OFFICES` (contracting offices swept; an agency whose awards other agencies sign for it also needs a funding-agency query), `sam_notices.SWEEP_ORGS` and `SWEEP_CODES` (SAM.gov organization ids), `trace.SAM_ORG_NODES`, `backtest.PILOT_OFFICES` |
| the agency filters | short each | the SBIR component in `sbir.py`; the docket agency in `protests.py`; the name pattern in `congress.py`; the Federal Register agency slug in `fedreg.py` (some agencies have none); the queries and name patterns in `oversight.py` and `remarks.py`; `DEPARTMENT` and `EXECUTIVE` in `people.py`; the agency node and forecast providers in `agency_layers_sql.py` |
| the feed list in `news.py` | short | the agency's own newsroom, the department's contract announcements, and the trade titles that cover it |
| the egress decision | short | which of the agency's hosts refuse a non-US address, recorded as an access finding rather than as a silence |
| the budget reader | one adapter | `budget.py` parses P-40 exhibits of the Navy's procurement books (48 lines from one book) and, since 2026-09-24, R-2 exhibits of an RDT&E book (24 program elements of DARPA's FY2027 book); the profile names the exhibit |

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
| DARPA | none found on 2026-09-24 (`research/docs/19`): the Contracts Management Office lists BAAs, SBIR and STTR topics, Research Announcements and RFPs as its instruments | built on 2026-09-24 under `research/agencies/darpa/` (`research/docs/19`, section 8): its contracting office HR0011 signing as many base awards in FY2026 as NAVWAR headquarters, the first page all Other Transactions; the awards other agencies sign for it found by funding agency 97AE; 1,165 of over five thousand notices under one SAM.gov organization harvested; people published with role, office and start date; the FY2027 RDT&E book read as 24 program elements; the Federal Register, oversight and Congress families thin; its special notices (proposers days, RFIs, future-program announcements) now read by title |
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
