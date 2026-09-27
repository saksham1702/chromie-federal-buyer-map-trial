# Air Force agency intelligence

The Department of the Air Force, the Air Force and the Space Force together, read by the same tools as the Navy, DARPA
and Army layers: which program office wants what, when, and on what evidence. Nothing here is written by hand except the
source registry and the coverage matrix; every other file is the output of one tool under `research/tools/`, run with
`AGENCY=airforce`.

## Layout

| File | Written by | What it holds (as built on 2026-09-26) |
| --- | --- | --- |
| `memory/organization_seed.json` | `org_memory_airforce.py build` | 22 nodes: the Department (SAM.gov 300000251, FPDS code 5700); eight commands (AFMC, AFLCMC, AFTC, AFNWC, and four named only on an office record's path: SPACE SYSTEMS COMMAND, HANSCOM AIR FORCE LIFE CYCLE MANAGEMENT CENTER, COMMAND, CONTROL AND COMMUNICATION BATTLE MANAGEMENT - HANSCOM AIR FORCE B, INTERCONTINENTAL BALLISTIC MISSILE); AFRL as a technical center; five PEOs (Digital, Weapons, Strategic Systems, Military Communication and Position Navigation Timing, Assured Access to Space); seven contracting offices with their DoDAACs (FA8650, FA8750, FA8730, FA2487, FA8219, FA8807, FA8811). 16 observations and 28 relationships, each resting on a saved SAM.gov organization record |
| `sources/source_registry.json` | by hand | 20 sources, four of them the Department's own (the Office of Small Business Programs site, the AFLCMC Business and Enterprise Systems Smart Guide, the budget materials, the leaders' pages) and one the DoD small business forecast page |
| `sources/coverage_matrix.json` | by hand, validated by `coverage.py` | 8 organizations by 13 evidence families |
| `sources/source_status.json` | `coverage.py status` | What each registered source last collected: 4 of 20 have collected something |

The `events/` and `results/` folders are empty: no collect or build stage other than the organization memory has been
run for this layer. `build/airforce/` (gitignored) holds nothing yet.

## Rebuilding

The database is local only (port 54322); set `SCHEMA_DB_CONTAINER` to the running database container first.

    export AGENCY=airforce
    python research/tools/org_memory_airforce.py collect          # the SAM.gov organization records not yet saved
    python research/tools/org_memory_airforce.py build            # the organization memory
    python research/tools/org_memory_airforce.py build --check    # exit 1 when a build would change the file
    python research/tools/pipeline.py --db airforce_proof --refresh

A build stage reads only what is saved; the saved bytes, the documents ledger and the model cassettes are shared with
the other layers. The af.mil hosts tried (airforcesmallbiz.af.mil, aflcmc.af.mil) and business.defense.gov answer 403
to a direct request from this address, and api.usaspending.gov does not verify over TLS from it.

## How the Air Force differs from the Navy

| Point | Navy | Air Force |
| --- | --- | --- |
| Forecast | Long Range Acquisition Estimates, one package per command release | None in a readable file: the Office of Small Business Programs page titled Acquisition Forecasts (Wayback capture of 2026-05-15) links no forecast, and the one directorate forecast found (the AFLCMC Business and Enterprise Systems Smart Guide, 4QFY26) is a PDF this address cannot retrieve |
| Organization source | Command pages, the forecast's office column and the NAVSEA deputy program manager list | SAM.gov federal organization records only; an office record's path also names the organizations above it, which are read as nodes |
| Contracting | Offices swept by office code (N00039 and others) | Seven offices by DoDAAC (FA8650 and FA8750 under AFRL, FA8730 under AFLCMC at Hanscom, FA2487 under AFTC at Eglin, FA8219 under AFNWC, FA8807 and FA8811 under Space Systems Command); an instrument number opens with its office's DoDAAC (DFARS 204.1603) |
| Space Force | Not applicable | SAM.gov files Space Systems Command (500188815) directly under the Department, with its PEOs between it and the offices; the portal releases Space Force topics under the USAF component with SF and DAF prefixes |
| SBIR/STTR topics | Component NAVY, codes N251-001 | Component USAF, codes AF193-005, AF212-0001, AFX255-DPCSO1, SF254-D1001, X224-ODCSO1, DAF26BZ01-DV001 |
| Budget | Procurement lines (Exhibit P-1) | Procurement lines (Exhibit P-40, line items printed as 3010F:); no book is saved |

## Results, 2026-09-26

The organization memory holds 22 nodes, every one resting on an observation. The shared portal index pages of
2026-09-22 carry 790 USAF-component topics: 318 under AFRL commands, 236 under AFMC, 37 under SSC, 20 under AFWERX, 17
under AFLCMC and its PEOs and 13 under PEO-AFNWC STRATEGIC SYSTEMS; the topic stage has not been run, so none is an event
yet. The coverage matrix covers 11 of its 104 cells (organization and programs); every other cell states why it is empty.

## Open

- No forecast is loaded. The AFLCMC Business and Enterprise Systems Smart Guide answers 403 here and has no Wayback
  capture; a hosted-browser retrieval would save it, and it is a PDF, which the forecast reader does not read.
- USAspending does not verify over TLS from this address, so the Department's offices are not ranked by obligations;
  the seven swept offices are the ones the SAM.gov notice searches and the scope name.
- No AFWERX or SpaceWERX contracting organization was found: a SAM.gov search for FA8649 returned AFWERX topics and no
  office.
- SAF/AQ and the AFLCMC offices at Robins have no node: SAM.gov holds no secretariat office, and no Robins office code
  was searched.
- These collect stages have not been run: notices, contracts, changes, dockets, register, audits, leaders, committee
  reports, grants, news, conference and topics. The committee reports saved for the Navy layer are shared and have not
  been read with the Air Force pattern.
- The budget stage is deferred: `data/raw/jbooks_airforce` holds no book.
