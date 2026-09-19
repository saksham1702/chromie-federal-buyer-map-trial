# 10 - Loading this research into the production agency-intelligence schema

Written 2026-09-19. The production schema exists: `gov_intelligence_assertions` and
its typed detail tables, shipped in the `agency_program_intelligence` migration. This
file records what the Navy pilot data can fill, what it cannot, and what trying it
found out about the design.

Loader: `research/tools/agency_layers_sql.py` (stdlib only, no network, no database
driver, `--selfcheck`). It emits one transaction of SQL; `psql` applies it.

## What loaded

Against a local database carrying the production migrations.

| Table | Rows | From |
| --- | --- | --- |
| `agencies` | 2 | Department of Defense, Department of the Navy |
| `gov_organizations` | 29 | seed nodes, minus 11 people |
| `gov_organization_relationships` | 29 | office edges the hierarchy column cannot carry |
| `gov_contacts` / `gov_contact_positions` | 11 / 13 | people and the `leads` claims |
| `agency_brain_items` | 508 | 79 source statements + 429 spreadsheet rows |
| `gov_intelligence_evidence` | 508 | one wrapper per Brain item |
| `gov_intelligence_assertions` | 1613 | 820 need-organization, 429 requirement, 364 funding |
| `gov_assertion_evidence` | 1613 | every assertion cites its source directly |
| `gov_needs` | 410 | 429 LRAE lines, 19 appearing in two releases |
| `gov_need_organizations` | 820 | requirement owner and contracting office per need |
| `gov_need_requirements` | 410 | one LRAE line per need |
| `gov_requirement_revisions` | 429 | one per release the line appeared in |
| `gov_funding_observations` | 364 | value ranges, all `procurement_estimate` |
| `gov_programs` | **0** | no source (see below) |
| `gov_procurement_refs` | **0** | blocked (see below) |

The transaction commits, which is the real test: `gov_intelligence_complete_assertion`
is deferred to commit and rejects any assertion missing its typed detail or, for a
`documented` basis, a directly supporting citation. All 1613 have both. Re-running the
loader inserts nothing.

## What the design got right

**Supersession keeps a slipping date visible.** "All SATCOM Multi Award Contract" is
forecast for award in FY24 Q2 in the June 2023 release and FY27 Q2 in June 2025. The
2025 assertion carries `supersedes_id` pointing at the 2023 one; the view
`gov_current_intelligence_assertions` returns only the later. Nineteen lines span two
releases. Overwriting would have erased every one of these.

**The evidence requirement is not decorative.** It forced each of the 508 source
statements into a Brain item before any claim could cite it, which is the behaviour
the research contract already asked for and previously had no enforcement behind.

**Separating `measure` from amount matters.** All 364 loaded values are
`procurement_estimate`, roughly $41B of forecast ceiling across twelve offices, led by
PMW/A 170 at $17.4B over 89 needs. Read as obligations those numbers would be wrong by
orders of magnitude.

**One parent column is the right call.** 16 of 29 offices have a single live parentage
claim and take `parent_organization_id`; 18 seed claims collapse into those 16 edges.
The column goes empty on exactly the four PEOs the 2026-05-11 reorganisation touched,
where a later source superseded the earlier parentage. That is correct behaviour, not
a gap: the remaining claims keep their dates in `gov_organization_relationships`.

## What could not load

**Programs.** The LRAE names requirements, offices and contracts. It never names a
program, and the org memory names offices. `gov_programs` is empty rather than filled
with PMW office names dressed as programs, which would make an office look like a
program everywhere the two join. Filling it needs a budget exhibit or a PEO program
inventory.

**Procurement references, locally only.** `gov_procurement_refs` keys on a row that
already exists in `sam_opportunities`, `usa_awards`, `usa_award_children` or
`gov_procurement_records`. The local database has no awards at all, so the layer and
the 96 need-to-contract links stay empty there.

That is a property of the local database, not of the data. Checked against the
production database on 2026-09-19: it holds 1,207,239 awards, and **42 of the 65
incumbent contract numbers read off the LRAE are already in it**, with recipient and
end date - Viasat on N0003916D0010 to 2026-06-29, Lockheed Martin on N0003918C0033,
Raytheon on N0003921C5002, and so on. Loaded there, layer 5 resolves for those 42 and
each planned buy gains its incumbent, that vendor, and the date their contract runs
out. The remaining 23 are the ones to chase.

**Retractions on office edges.** `gov_organization_relationships` has `valid_from` and
`valid_to` and no way to say a claim was withdrawn as wrong rather than ended as true.
Three retracted claims are left out. An ended claim and a retracted one are different
statements and the table cannot tell them apart.

**`listed_with`.** One seed claim records that two offices appeared in the same list
without asserting a relationship between them. The production vocabulary
(`functionally_aligned_to`, `contracting_supports`, `delegated_authority_from`,
`contract_administers_for`, `successor_to`) has nothing that weak, and mapping it to
`functionally_aligned_to` would assert more than the source says.

**Interpretations.** The five readings no single source states have no layer. Without
somewhere to put them they get promoted into relationships they have not earned and
the ancestry walk starts returning guesses.

**Smaller losses.** 65 LRAE lines state no value range and are left out of funding
rather than stored as zero. `gov_organizations` has no column for a node's `location`,
`notes` or `capability_portfolios`, dropping 18 values; `name_history` is folded into
`aliases`, which is what former names are. `direct_reporting_program_manager` is not in
the type vocabulary, so a DRPM is loaded as `program_office` - defensible, since what
makes it direct-reporting is who it reports to, which is a relationship.

## State of the production database

Read-only check, 2026-09-19. The schema is deployed and **every one of its tables is
empty**: `gov_programs`, `gov_needs`, `gov_need_requirements`,
`gov_requirement_revisions`, `gov_funding_observations`, `gov_intelligence_assertions`,
`gov_intelligence_evidence`, `gov_assertion_evidence` and `gov_procurement_refs` all
hold zero rows. Nothing has been written into the agency-intelligence layers yet.

What is already there matters for how this would be promoted. `gov_organizations`
holds 1,488 rows including all eleven PEO C4I program offices, sourced
`official_navwar` and `sam_gov`; `gov_organization_relationships` holds 194;
`agency_brain_items` holds 23,128. A promotion must therefore **match** the Navy
offices to the rows that exist rather than insert its own, or it creates eleven
duplicate PMWs. The loader currently mints its own identities, which is correct for an
empty local database and wrong for production; matching on office code through
`external_ids` is the obvious join and is not written yet.

## Promotion path

`python research/tools/promote_plan.py` matches every loaded office against the
production registry and prints what a promotion would insert. It reads production
over GET only and contains no write path.

Matching is narrow on purpose: an office code carries the identity, an exact name or
alias is accepted only when the organization types agree, and anything matching two
production rows is refused rather than guessed. The type guard is not decoration - a
program office and a contracting office can share a code, and crossing that line
would file a planned buy under the desk that signs the paperwork instead of the one
that wants the thing.

Result against production on 2026-09-19: **21 of 29 offices resolve**, none
ambiguously - eleven by office code, ten by exact name. Nothing new is created.

| | rows | |
| --- | --- | --- |
| Ready | 410 needs, 410 requirements, 429 revisions, 364 funding observations, 820 need-organization links, 1613 assertions, 508 evidence, 1613 citations, 12 positions | every office reference resolves |
| Held | 29 organization relationships | six offices have no production row |

The six are NIWC Pacific, NIWC Atlantic, NAVWAR as a command, PEO EIS, PMW 205 and
PMW 220. Production holds the eleven PEO C4I program offices but none of these, under
any name or code; the only NAVWAR-command row is the pre-2019 "Naval Space and Warfare
Systems Command" typed `other`. Creating them is a decision about the organization
registry, not part of this load, so the tool holds that one table back and promotes
the rest rather than blocking everything on edges nobody is waiting for.

What is still missing before a promotion can run: the step that rewrites the loader's
office ids through this mapping, and a person reading the resulting diff. The layer
tables are append-only - both UPDATE and DELETE raise, and an assertion allows one
retraction and nothing else - so a row written against the wrong office cannot be
removed. That is the whole reason this is a plan and not a push.

## Two notes on the schema itself

`gov_intelligence_assertions` is `UNIQUE (producer, source_key)`, which makes
`source_key` the real idempotency key rather than the row id. A first load here used
one `source_key` per need for both its requirement-owner and its contracting-office
claim; 410 assertions were silently dropped by `ON CONFLICT DO NOTHING` and only the
detail-kind trigger caught it. Worth a comment on the constraint.

Supersession may not change the measurement scope, and for funding that includes the
fiscal year and period. A re-estimate of the same need for the same period chains
correctly and only the latest stays current. A move to a different fiscal year cannot
chain, and both estimates remain current - correctly, since they are different
measurements, but a caller summing forecast value has to group by fiscal year rather
than trust the current view to hold one row per need.
