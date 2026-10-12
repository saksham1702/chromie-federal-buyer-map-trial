---
name: pursuit
description: >
  For a vendor pursuing a topic at one federal agency, answer one of two questions from this repository's record, the
  same way every run: where the money for the topic is and who potentially holds it (budget), or who could back the
  pursuit with a support letter, a customer memo or an introduction (champions). Record first, through the agency's
  read surface (research/tools/navy.py, its MCP server named by the agency key, or with no checkout production's
  read-only agent views through the Supabase MCP server); the web only for the gaps the
  record states. Use when the user says "budget analysis for <topic> at <agency>", "where is the money for <topic>",
  "who holds the budget for <topic>", "who could champion <topic>", "letter of support", "customer memo", "potential
  champions at <agency>", or names an agency key (navy, darpa, army, airforce, dhs, doe, nasa, noaa, hhs, va, gsa,
  epa, dot) with a pursuit, budget or champion.
user-invokable: true
argument-hint: "<agency key> <topic> budget|champions [--office OFFICE] [--web]"
---

# Pursuit: the money, or the people who could back it

Two recipes over the record, each a spec in `research/report_specs/`: `pursuit-budget` and `pursuit-champions`. The
mechanics are the `intelligence-report` skill's (inventory, plan, gather, answer, check, render); this skill adds the
pursuit's rules and the web gap-fill. Work from the repository root with `.venv/bin/python`. Write to
`build/pursuit/<agency>-<recipe>-<topic slug>/` (DIR below).

## 1. What the record holds, first

```
.venv/bin/python research/tools/report.py inventory --agency KEY
```

Tell the user the record's date and what is absent before anything else. A missing domain is "not in this record",
never zero: no budget lines (only Navy, Army, Air Force, DARPA and DHS have them today) means the budget answer rests
on statements, directives, forecasts and awards; no people beyond contracting staff (Army, DOE, NOAA today) means
champions come from offices and notice contacts only.

## 2. Plan and gather

```
.venv/bin/python research/tools/report.py plan   --agency KEY --spec pursuit-budget|pursuit-champions --focus "TOPIC" --mode full
.venv/bin/python research/tools/report.py gather --agency KEY --spec pursuit-budget|pursuit-champions --focus "TOPIC" --mode full --out DIR
```

The plan picks three anchor offices: the offices whose statements carry the topic, contracting offices aside (an
inference; state its rule). If the user named an office, run the plan again with `--focus "OFFICE"` into a second DIR
so its per-office answers are gathered and checkable; never paste a command's output into `bundle.json` by hand. Without a shell, call the agency's MCP server tools instead (`search`, `report`, `people`, ...),
following each step's `mcp` field, and write what they returned into `DIR/bundle.json` as `gather` would.

Read `DIR/evidence.md`. Every step is answered or is a boundary that says what was read; keep every boundary. A
boundary section takes no claims (render drops them): put a fact it needs in the section whose call printed it.
`revisions` reads the agency's local database; when that is not loaded the step is "not read", never "nothing moved".

## 3. Write the answer, by the recipe's rule

`DIR/answer.json` in the schema `plan --schema` prints: a top-level `reading` (two or three sentences: the answer to
the pursuit's question), and per section `claims` (identifier, exact quote from the answer of the call named as its
source, source = that tool call), `inferences` (inference, rule, rests_on claim identifiers), `summary`, `not_found`.
An identifier names what the claim is about as the record writes it: a record id, a full office name, a person, a
budget line with its appropriation (`1319 line 0604518N`), a record file.

**Budget.** Each money claim carries its line or program identifier, fiscal year, amount and the measure exactly as
labelled (request, enacted, obligated, forecast estimate). Who holds it follows the chain: Congress funds the line;
the line is placed in an office on the basis the record states; the office's listed head is a *potential* budget
holder only as an inference resting on two claims (the role, and a line placed in that office). "Remaining" is a
floor, with its caveats. A contracting office holds no placed budget: it buys for others.

**Champions.** A candidate needs a documented role quoted as written, plus at least one separate fact tying the
person or office to this topic's problem or money (a forecast row or notice naming them, a line placed in their
office, a remark on the topic). Rank, the same every run: owns the problem and the money; owns the problem; end user
liaison; technical; potential decision maker. Contracting staff are a route, never an advocate. A post confirmed
current ranks above one last seen on a date. Every reading is "potential", rests on two claims or more, and says
what is still to confirm; "willing to advocate" is "none found" unless a source says so. An office with no named
person stays as an office row.

## 4. Check until clean, then render

```
.venv/bin/python research/tools/report.py check  --out DIR
.venv/bin/python research/tools/report.py render --out DIR
```

Fix every problem the checker names (a quote not in its step's answer, an unknown identifier, a role word without
"potential", an inference without a rule or on fewer than two claims) and run it again.

## 5. The web, only for the stated gaps (when the user asks for it, or `--web`)

After the record's report is clean, look up only what a boundary or `not_found` names. Navy's budget justification
books are already saved in `data/raw/jbooks/`: read those before the web. Then: the agency's budget
justification or comptroller pages, USAspending, congress.gov, SAM.gov, an official biography or organization chart to
confirm a post is current, a conference agenda. Save each page read:

```
<fetch> | .venv/bin/python research/workflow/save_source.py DIR/sources web/NAME.txt --source "URL"
.venv/bin/python research/workflow/save_source.py DIR/sources --failed "HTTP 403" --source "URL"
```

Web findings never enter `answer.json` (its quotes are checked against the record). List them in `DIR/web.md`, one
row each: what it adds, the exact quote, URL, retrieved date, and which gap it fills. Quote only page text you saved;
a search snippet or a fetch tool's summary is the tool's wording, labelled so, and confirms nothing. A blocked page is
"not collected". LinkedIn is self-stated, used only when name and office match. A work contact printed on an official
notice or forecast is a route; never a personal email or phone.

## 6. Without the repository: production's agent views

An agent with no checkout reads the same record from production, through the Supabase MCP server in read-only mode
(`execute_sql`), and only from the `agent` schema; never the raw tables. The views carry every loaded agency; filter on
`agency` with the name exactly as `agent.record_holds` prints it (`Department of the Navy`, not `%navy%`).

1. `agent.record_holds`: the sections held, their rows and newest date. Say what is absent first, as in section 1.
2. `agent.items` and `agent.needs`: the topic's statements and requirements (`title`/`body`/`description` `ilike`).
   The offices they name are the anchors (state the rule).
3. Budget: `agent.budget_lines`. Quote `book_column` and `measure` as written; never sum across measures (a program
   block repeats its book line). An empty `placed_office` means the line sits at agency level in this record: say
   "not placed in an office", never name a holder for it. Office placements that live only in the repository's
   research files (office_owners.json) are not in production. Then `agent.budget_statements`: congressional
   directives, funding changes quoted from remarks and summary figures (most of the civilian agencies' money is here).
   Quote `body` or `figures_as_written` as written, units included; never convert or add across items.
4. Champions: `agent.people_readings`. `reading` already says "potential"; keep `basis` and `observed_at`, and the
   two-claim rule of section 3 still holds.
5. `agent.evidence` by `item_id`: the excerpt and URL a statement rests on.

Usage rules (each one cost a wrong "not found" in the 2026-10-10 eval run):
- Forecasts: query `agent.needs` (`source like '%datapack'`), not `agent.items` section `forecast` (locator-only
  rows for most civilian agencies). `as_of`, `release`, `estimate_as_written` and `source_url` date and cite a need.
- Sub-agencies (CDC, NIH, FDA, FAA, NESDIS, CISA, PEOs): filter the parent `agency` (or `department`) and match the
  acronym in `office_path` (`needs.office_paths`), e.g. `office_path ~ '\mCDC\M'`. `agency = 'Centers for Disease
  Control and Prevention'` finds almost nothing. `agent.offices` lists the offices under an agency.
- Offices are stored as acronyms and codes (NESDIS, 75N9xx for NIH contracting): search `owner_offices`,
  `contracting_offices` and `office_path`, not only the full name.
- Short acronyms: case-sensitive word boundary (`~ '\mALS\M'`), then confirm with the full name; `ilike '%ALS%'`
  hits 'intervALS'. Old program names do not map to new ones (IVAS is now SBMC): search both.
- Budget lines: never sum across `measure`s (a program block repeats its book line); filter
  `measure ilike '%book line'` and name the book (PB2026 and PB2027 print the same year differently). A null
  `amount_musd` is a column with no figure in the record: say so, never zero. A program block's `source_url` is the
  program listing; the book's citation is in `agent.evidence` for the same `item_id`.
- Directives: search `body` as well as `title` (headings can be 'Briefing'); the year is `fiscal_year`
  (or `figures_as_written->>'fiscal_year'`). Qualify columns when joining a view to a table (`s.kind`).
- A null `source_url` after v2 means no public URL in the record: say so; never cite a `local://` path.
- People: `reading` already says "potential"; "leader by title" is a title only, never a decision maker or budget
  holder. Quote `title_as_written` (the source's words), not `role_as_written` (a role code). `post_status` and
  `observed_at` answer "is this person current": take the newest `observed_at` across all of the person's rows, since
  one person's posts can sit under several office keys (a center and its contracting office). Group one person by
  `person_id`; a name can still appear as two
  people ("GRIFFIN, JIM" and "James Griffin"): say so, never merge them yourself. A hearing witness whose title names
  another employer (GAO, MITRE, VFW) is not agency staff. Contracting staff are a route, never an advocate, and a
  forecast contact who also appears as contracting staff is a route too, whatever the reading says.
- `record_holds` counts rows, not coverage: read a few rows before calling a section covered.
- Views are slow: one statement per call, filter `agency` first, aggregate in SQL, no unions of many view subqueries.

Save each query and its full result under `DIR/sql/NN-view.json`. A claim's source is
`mcp:supabase execute_sql agent.VIEW item_id=ID` (or `need_id=`), its quote copied exactly from that saved result, its
identifier the record id, line or person as the row writes it. The rules of sections 3 and 5 apply unchanged.

## Rules

- Facts, inferences and recommendations stay apart. Never infer authority, a decision or advocacy from a title alone.
- Nothing is zero that was not read. Name offices as the record writes them. No likely, probably, imminent, soon.
- Read-only: no pipeline stage, no collection, no database write; production only through the `agent` views (section 6).

## Hand back

The path of `report.md` (and `web.md`), the checker's counts, the anchor offices with their basis, the boundaries,
and the top rows: for budget, the lines and amounts by fiscal year with who potentially holds them; for champions, the
ranked candidates with the two claims each rests on and what is still to confirm. Do not paste the whole report.
