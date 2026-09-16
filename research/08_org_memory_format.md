# 08 - Organization memory: a format that holds the PEO structure and the PAE structure at once

Written 2026-09-17. Implemented in `organization_seed.json` (the data) and
`org_code_families.json` (how a parser recognizes office codes). This document is the contract
for both.

## In plain terms

There is no reliable org chart for the Navy's acquisition offices, and the one being built (the
PAE portfolios) is only partly published while the old one (PEOs and PMWs) is still what every
contract and forecast refers to. So the memory is not a chart. It is a list of offices, a list of
dated relationships between them, and a list of every spelling and code under which an office
appears in the wild. Any record, old or new, is attached to whatever the office and its parents
were on that record's date. When the Navy changes something, a new dated relationship is added
and the old one is closed; nothing is deleted or overwritten.

## 1. Nodes

One node per organization or person, with:

| Field | Meaning |
| --- | --- |
| `id` | stable local id (`pmw:160`, `peo:c4i`, `pae:mission-systems`, `contracting:n00039`) |
| `type` | `agency`, `command`, `acquisition_portfolio` (PAE), `program_executive_office`, `program_office`, `technical_center`, `contracting_office`, `direct_reporting_program_manager`, `person` |
| `name`, `aliases` | current name plus every observed spelling and code; the code families below feed this list |
| `codes` | structured identifiers: office code (`PMW 160`), contracting UIC (`N00039`), FPDS agency id |
| `valid_from`, `valid_to` | when the organization existed under this identity; open when unknown or current |
| `name_history` | earlier names with their own date ranges (SPAWAR to NAVWAR, SSC Pacific to NIWC Pacific) |
| `evidence` | one or more official documents, each with `source_url` and `observed_at` (and passage, capture timestamp) |
| `notes`, `review_status` | free text and flags such as `conflict_flagged`, `needs_official_page` |

## 2. Edges

One edge per dated relationship, never a single parent pointer:

| Edge type | Meaning | Example |
| --- | --- | --- |
| `child_of` | organizational parent as stated by an official page | PMW 160 child_of PEO C4I |
| `consolidated_into` | a reorganization moved the organization (or its mission elements) into another, from a date | PEO C4I consolidated_into PAE Mission Systems, valid_from 2026-05-11 |
| `contracts_for` | this contracting office executes for that organization | N00039 contracts_for PMW 160 |
| `part_of` | component of a command | NIWC Pacific part_of NAVWAR |
| `leads` | a person's dated role | Castillejo leads PMW 150, valid_from 2025-08-19 |
| `listed_with` | co-listed on an official page without a stated reporting line | DRPM Overmatch listed_with NAVWAR |

Every edge carries `valid_from` / `valid_to` where known and its own evidence. Two edges can
coexist for the same child (PEO C4I child_of NAVWAR with an open end date, and consolidated_into
PAE Mission Systems from 2026-05-11); the pair is flagged for review rather than resolved by hand,
because the Navy's own pages currently say both.

## 3. Resolving a record to an office on its date

1. Extract candidate codes and names from the record (award description, notice text, LRAE
   requirement-office column, budget exhibit narrative).
2. Classify each code by the first matching family in `org_code_families.json` (PMW/PMA office,
   PMS office, IWS office, NIWC Atlantic division, NIWC Pacific competency, NAVWAR HQ competency,
   PEO front-office code, PEO MLB portfolio code, PAE capability portfolio, contracting UIC).
   Families say what kind of organization the code denotes and where it has been seen, so an
   NIWC competency is never mistaken for a program office, and a contracting UIC never for an owner.
3. Look the normalized code up in the alias table; an unknown code becomes a new node marked
   `unverified` and a review item.
4. Walk `child_of` and `consolidated_into` edges valid on the record's date to produce the
   ancestry as of that date. A 2019 award resolves to PMW 160 under PEO C4I under NAVWAR; a June
   2026 modification of the same award resolves to PMW 160 under PEO C4I within PAE Mission
   Systems, with NAVWAR HQ still the contracting office.
5. Attach the record with the evidence class from `04_attribution_process_and_examples.md`.

## 4. How the PAE migration is held

- PAE portfolios are nodes of type `acquisition_portfolio` with `valid_from` set to the
  establishment release date; consolidations are `consolidated_into` edges from each PEO.
- The PAE's published structure (five capability portfolios) is stored on the PAE node; the
  mapping of PMWs to portfolios is written down as a candidate in `02_organization_map.md` and
  not as edges until an official page states it.
- PEO and PMW nodes stay open (no `valid_to`) because contracts, forecasts and notices still
  cite them; when the Navy retires a code, the node gets a `valid_to` and the code stays in the
  alias table so old records keep resolving.
- The same applies backwards: PEO EIS is closed at 2020-05-13 with its offices moved to PEO
  Digital and PEO MLB by dated edges, so a 2019 SMIT award resolves to NEN under PEO EIS.

## 5. Adding and correcting

- Sources of change: organization pages (weekly hash diff), reorganization releases, new codes in
  the LRAE or in award text, change-of-command releases.
- Every change adds a node or edge with evidence; a correction closes the wrong edge with a
  `valid_to` and a note rather than deleting it.
- Conflicts are kept side by side and flagged; the review queue decides.

## 6. Mapping to Chromie

Nodes are `gov_organizations` rows (`org_type`, `aliases`, `valid_from`, `valid_to`, provenance);
edges are `gov_organization_relationships` rows (`relationship_type`, dates, provenance). The
resolver already reads validity dates. Two additions would help: `consolidated_into` as a
relationship type, and a small table for code families so the alias table is data, not code.
