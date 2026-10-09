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
