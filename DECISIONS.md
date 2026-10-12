# Decisions

Add dated technical and product decisions here.


## 2026-10-09 - Agents read production through the `agent` views

- **Fact.** The owner applied `research/sql/agent_views.sql` to production on 2026-10-09 in the SQL editor (no login on
  this box may create a schema or role). Read back through the read-only MCP user: six views, `agent_reader` holds
  select, anon/authenticated/service_role hold nothing on the schema; the security advisor names nothing in it.
- **Fix.** `budget_lines.placed_office` tested `org_type = 'agency'`; production types the agency's own organization
  `other`, so 2,820 Navy lines read as placed in "Department of the Navy". The rule is now
  `existing_agency_id = agency id`, checked on the local copy (Link 16 block reads agency level); the owner ran the
  view again the same day and production reads the same split (Navy 12,413 agency level, 423 in an office).
- **Assumption.** Office placements kept only in research files (`office_owners.json`) are not in production, so a
  pursuit from production names no budget holder for a line at agency level; it says "not placed in an office".
- **Budget statements.** 2,218 agency budget items in production carry no book columns: congressional directives (HHS 401,
  Navy 375, VA 224, ...), funding changes whose amounts are quoted strings ("$14B"), and app-written summary figures
  in fields of their own shape and unit (HHS, VA, SBA, CMS). `agent.budget_statements` shows them with `body` and the
  item's own fields as written; nothing is converted to $M, since the units differ per item. Every agency budget item
  sits in exactly one of the two budget views (checked on the local copy; 294 items with no agency stay out of all views).

## 2026-10-12 - Agent views show e-mail addresses and phone numbers

- **Owner, 2026-10-12:** "we now have to use emails contacts everything". `agent.names_only` is removed from
  `research/sql/agent_views.sql`: titles, bodies, needs and excerpts show addresses and numbers as the record holds them.
  The paste file `research/sql/agent_views_v2.sql` is regenerated; `names_only.sql` stays cancelled.
- **Checked.** `research/evals/agent_views_v2_local_test.sql` on `dhs_proof`, rolled back: every `*_left` and `*_bad`
  is 0; 4 items and 13 excerpts carry a contact (DHS was built names only, so its text holds few).
- **Production.** Applied 2026-10-12 at the owner's request, through the Management API (`build/pursuit_cisa/run_sql.py`,
  a rolled-back run first). Eight views, all readable by `agent_reader`; the file's checks pass (GSA 344 of 345 posts
  titled, NOAA statements 0 local paths, GSA forecast needs all dated, NIH needs over 1,000).

## 2026-10-12 - E-mails back in production, and on each person in the agent views

- **Owner, 2026-10-12:** "touch prod data emails are needed"; name matches "use, labelled".
- **View.** `agent.people_readings` gains `email`, `phone`, `contact_basis`: our contact's own address by id, else a
  contact from another source (SAM, the app) with the same name at the same agency and one address only, labelled
  "same name at the same agency, from <source>" (a match, not a stated link). Agencies are matched on the agency's name,
  its "X, DEPARTMENT OF" form or "DEPT OF THE X" inside the contact's agency text, only for agencies with readings.
- **Data.** HHS, DHS, DOT and EPA were built names only. A person's id comes from the raw key before the digest, so
  `prod-load-test/correction/emails_back.py` reran the people merge with addresses kept and set `gov_contacts.email`
  by id where null on our rows (identity keys untouched): HHS 1,413, DHS 1,188, DOT 650, EPA 262. Rehearsed on each
  local copy, then a rolled-back run on production, then applied. People with an e-mail in the view: DHS 844 of 2,006,
  HHS 876 of 1,867, DOT 409 of 592, EPA 153 of 205.
- **Open.** The builder still defaults to names only and captures no phone; flipping it changes people items for every
  agency, so it waits on a local rebuild compare before the next top-up.
