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

**Procurement references.** `gov_procurement_refs` keys on a row that already exists
in `sam_opportunities`, `usa_awards`, `usa_award_children` or
`gov_procurement_records`. 65 distinct incumbent contract PIIDs read off the LRAE are
none of those until ingested, so the whole layer stays empty and the 96 need-to-contract
links with it. This is the one place the pilot data hits a wall rather than a gap in
the sources.

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

## Note for the schema owner

`gov_intelligence_assertions` is `UNIQUE (producer, source_key)`, which makes
`source_key` the real idempotency key. Worth saying so in a comment: the first load
here used one `source_key` per need for both its requirement-owner and its
contracting-office claim, and 410 assertions were silently dropped by an
`ON CONFLICT DO NOTHING` before the detail-kind trigger caught the mismatch.

Separately, the type axis for funding is split elsewhere in the corpus: VA agency
awards are typed through `funding_instrument`, SBIR and STTR through `program_tags`,
which is `CHECK`-locked to those two values. Consolidating means backfilling 204,345
SBIR rows.
