-- Read-only views an agent queries instead of the raw tables. Each row keeps the record's wording and carries its
-- source; a role reading the record cannot state is "potential"; a domain the record lacks shows in record_holds as
-- absent, never as zero. Idempotent. Apply to a local proof database first; production is the owner's step:
--     psql -h HOST -p PORT -U postgres -d DB -v ON_ERROR_STOP=1 -f research/sql/agent_views.sql
-- An agent connects as agent_reader (select on these views only), or through the Supabase MCP server in read-only mode.

create schema if not exists agent;

create or replace view agent.record_holds as
select a.canonical_name as agency, b.section, count(*) as rows,
       max(b.as_of) filter (where b.as_of between date '2000-01-01' and current_date) as newest
from agency_brain_items b
join agencies a on a.id = b.agency_id
group by 1, 2;
comment on view agent.record_holds is 'What the record holds per agency and section, with the newest date. Read it first: a section missing here was not collected, which is not the same as nothing happening.';

create or replace view agent.items as
select b.id as item_id, a.canonical_name as agency, b.section, b.event_type, b.title, b.body, b.as_of, b.published_at,
       coalesce(b.source ->> 'url', b.source -> 'listing' ->> 'url') as source_url,
       coalesce(b.source ->> 'sha256', b.source -> 'listing' ->> 'sha256') as sha256,
       coalesce(b.source ->> 'retrieved_at', b.source -> 'listing' ->> 'retrieved_at') as retrieved_at,
       b.source_provider, b.source_tier, o.name as organization
from agency_brain_items b
join agencies a on a.id = b.agency_id
left join gov_organizations o on o.id = b.primary_organization_id;
comment on view agent.items is 'Every dated statement in the record (notices, forecast rows, awards, budget, remarks, oversight, people), one row each with its source URL, sha256 and retrieval date. Search title and body with ilike.';

create or replace view agent.budget_lines as
select b.id as item_id, a.canonical_name as agency,
       coalesce(b.data ->> 'li', b.data ->> 'program') as line,
       b.data ->> 'title' as title,
       b.data ->> 'appropriation' as appropriation,
       b.data ->> 'budget_activity' as budget_activity,
       e.col as book_column,
       substring(e.col from 'fy(\d{4})')::int as fiscal_year,
       e.amt::numeric as amount_musd,
       case when b.data ? 'amounts_musd' then 'program block' else 'PB' || coalesce(b.data ->> 'pb', '?') || ' justification book line' end as measure,
       case when o.existing_agency_id = a.id then null else o.name end as placed_office,
       coalesce(b.source ->> 'url', b.source -> 'listing' ->> 'url') as source_url,
       coalesce(b.source ->> 'sha256', b.source -> 'listing' ->> 'sha256') as sha256,
       coalesce(b.source ->> 'retrieved_at', b.source -> 'listing' ->> 'retrieved_at') as retrieved_at,
       b.source ->> 'book_date' as book_date
from agency_brain_items b
join agencies a on a.id = b.agency_id
left join gov_organizations o on o.id = b.primary_organization_id
cross join lateral jsonb_each_text(case when jsonb_typeof(b.data -> 'amounts') = 'object' then b.data -> 'amounts'
                                        else b.data -> 'amounts_musd' end) as e(col, amt)
where b.section = 'budget' and (jsonb_typeof(b.data -> 'amounts') = 'object' or b.data ? 'amounts_musd') and e.amt is not null;
comment on view agent.budget_lines is 'One row per budget line (or program block) per book column, in $M as the book prints it. book_column is the column as written (fy2027_base, prior_years, to_complete); the column says what the year means, the view does not call it request or enacted. A program block (line:APPN:NNNN) repeats the amounts of the book line it reads, so never sum across measures. placed_office is empty when the record placed the line in no office below the agency. Budget statements that are not book lines are in agent.budget_statements.';

-- the budget section's other statements: they carry figures in words and in fields of their own shape, never in $M columns
create or replace view agent.budget_statements as
select b.id as item_id, a.canonical_name as agency, coalesce(b.event_type, 'statement') as kind, b.title, b.body,
       b.data as figures_as_written, b.as_of, b.published_at,
       coalesce(b.source ->> 'url', b.source -> 'listing' ->> 'url') as source_url,
       coalesce(b.source ->> 'retrieved_at', b.source -> 'listing' ->> 'retrieved_at') as retrieved_at,
       b.source_provider,
       case when o.existing_agency_id = a.id then null else o.name end as placed_office
from agency_brain_items b
join agencies a on a.id = b.agency_id
left join gov_organizations o on o.id = b.primary_organization_id
where b.section = 'budget' and not coalesce(jsonb_typeof(b.data -> 'amounts') = 'object' or b.data ? 'amounts_musd', false);
comment on view agent.budget_statements is 'Every budget statement agent.budget_lines does not carry: congressional directives (report language), funding changes quoted from remarks, and summary figures. body states the figures in words; figures_as_written is the record''s own fields, keys and units as the item wrote them (millions, billions, dollars). Quote them as written: never convert units, never add figures across items. A row without source_url has no source in the record: say so.';

create or replace view agent.people_readings as
select b.id as item_id, a.canonical_name as agency, b.data ->> 'name' as person, b.data ->> 'bucket' as bucket,
       case when b.data ->> 'bucket' in ('budget_holder', 'decision_maker', 'champion')
            then 'potential ' || replace(b.data ->> 'bucket', '_', ' ') else replace(b.data ->> 'bucket', '_', ' ') end as reading,
       array(select jsonb_array_elements_text(b.data -> 'basis')) as basis,
       p ->> 'role' as role_as_written, p ->> 'office' as office_key, p ->> 'status' as post_status,
       p ->> 'source' as post_source, p ->> 'source_url' as source_url, (p ->> 'observed_at')::date as observed_at,
       (select count(*) from gov_intelligence_evidence v where v.brain_item_id = b.id) as evidence_rows
from agency_brain_items b
join agencies a on a.id = b.agency_id
left join lateral jsonb_array_elements(coalesce(b.data -> 'posts', '[]'::jsonb)) as p on true
where b.section = 'people' and b.data ? 'bucket';
comment on view agent.people_readings is 'One row per person per post. reading is the record''s bucket, written as potential for budget holder, decision maker and champion: a reading, never a fact. basis says how it was reached (listed, stated, self-stated, inferred). Contracting staff are a route, never an advocate.';

create or replace view agent.needs as
select n.id as need_id, a.canonical_name as agency, n.title, n.description, n.lifecycle, n.source, n.source_key,
       (select string_agg(distinct coalesce(o.acronym, o.name), '; ') from gov_need_organizations x
          join gov_organizations o on o.id = x.organization_id
         where x.need_id = n.id and x.role = 'originating_requirement_owner') as owner_offices,
       (select string_agg(distinct coalesce(o.acronym, o.name), '; ') from gov_need_organizations x
          join gov_organizations o on o.id = x.organization_id
         where x.need_id = n.id and x.role = 'contracting_office') as contracting_offices
from gov_needs n
join agencies a on a.id = n.agency_id;
comment on view agent.needs is 'Each requirement (forecast row or notice group) with the office that owns it and the office that contracts for it, as the record ties them.';

create or replace view agent.evidence as
select v.brain_item_id as item_id, b.section, b.title, v.source_url, v.excerpt, v.published_at, v.provider
from gov_intelligence_evidence v
join agency_brain_items b on b.id = v.brain_item_id;
comment on view agent.evidence is 'The excerpts each statement rests on, with the source URL. Join to agent.items or agent.people_readings by item_id.';

do $$ begin
  if not exists (select from pg_roles where rolname = 'agent_reader') then create role agent_reader nologin; end if;
end $$;
grant usage on schema agent to agent_reader;
grant select on all tables in schema agent to agent_reader;
