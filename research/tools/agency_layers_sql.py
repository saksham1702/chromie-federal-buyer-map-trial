#!/usr/bin/env python3
"""Turn the Navy org memory and the LRAE datapacks into SQL for the prod agency-intelligence schema.

    python research/tools/agency_layers_sql.py > /tmp/navy_layers.sql
    psql "$LOCAL_DB" -v ON_ERROR_STOP=1 -f /tmp/navy_layers.sql
    python research/tools/agency_layers_sql.py --selfcheck

Reads research/organization_seed.json (offices, observations, relationships, readings)
and datapack/lrae_navwar_*/layers/*.csv (needs, requirements, funding, procurement
references, evidence). Writes SQL against the tables the production migrations
`reconcile_agency_intelligence_prerequisites` and `agency_program_intelligence`
create. No network, no database driver, stdlib only, so the same inputs always
produce the same bytes.

The production model puts everything time-varying on `gov_intelligence_assertions`:
one dated, evidence-backed claim with a basis, a rationale and an optional
supersession, and a thin typed detail row keyed on `assertion_id`. Evidence is an
Agency Brain item wrapped in `gov_intelligence_evidence`. A `documented` assertion
will not commit without direct supporting evidence, so every claim here is written
with its detail and its citation in the same transaction.

Every id is a uuid5 of a fixed namespace and the record's own key, so re-running
inserts nothing. Nothing invents a value a source does not carry: rows the schema
cannot accept are counted and reported on stderr rather than padded.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "research" / "organization_seed.json"
RELEASES = ["lrae_navwar_2023-06", "lrae_navwar_2024-06", "lrae_navwar_2025-06"]

NS = uuid.UUID("7c3d1f5a-9b24-4f8e-8c61-2a0d5e7b41c3")
SEED_SOURCE = "chromie-federal-buyer-map-trial/research/organization_seed.json"
LRAE_SOURCE = "chromie-federal-buyer-map-trial/datapack"
PRODUCER = "chromie-federal-buyer-map-trial/agency_layers_sql.py"
PRODUCER_VERSION = "2"

skipped: dict[str, int] = {}


def note_skip(reason: str) -> None:
    skipped[reason] = skipped.get(reason, 0) + 1


def uid(kind: str, key: str) -> str:
    return str(uuid.uuid5(NS, f"{kind}:{key}"))


def sha(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


# ------------------------------------------------------------------ SQL literals

def lit(value) -> str:
    """Quote for Postgres. standard_conforming_strings is on, so doubling ' is enough."""
    if value is None or value == "":
        return "null"
    return "'" + str(value).replace("'", "''") + "'"


def arr(values) -> str:
    values = [v for v in values if v]
    if not values:
        return "'{}'::text[]"
    return "array[" + ",".join(lit(v) for v in values) + "]::text[]"


def jsonb(value) -> str:
    return lit(json.dumps(value, sort_keys=True, separators=(",", ":"))) + "::jsonb"


def norm(text: str) -> str:
    return " ".join(str(text).split()).strip().lower()


def insert(table: str, columns: list[str], rows: list[list[str]], out: list[str]) -> None:
    if not rows:
        out.append(f"-- {table}: nothing to insert")
        out.append("")
        return
    out.append(f"insert into {table} ({', '.join(columns)}) values")
    out.append(",\n".join("  (" + ", ".join(r) + ")" for r in rows))
    out.append("on conflict do nothing;")
    out.append("")


# -------------------------------------------------------------------- agencies

AGENCY_DOD = uid("agency", "097")
AGENCY_NAVY = uid("agency", "097:1700")


def emit_agencies(out: list[str]) -> None:
    insert("public.agencies",
           ["id", "parent_agency_id", "level", "canonical_name", "normalized_name",
            "abbreviation", "toptier_code", "subtier_code"],
           [[lit(AGENCY_DOD), "null", lit("toptier"), lit("Department of Defense"),
             lit("department of defense"), lit("DOD"), lit("097"), "null"],
            [lit(AGENCY_NAVY), lit(AGENCY_DOD), lit("subtier"), lit("Department of the Navy"),
             lit("department of the navy"), lit("DON"), lit("097"), lit("1700")]],
           out)


# --------------------------------------------------------------------- offices

# `direct_reporting_program_manager` is not in the production vocabulary. A DRPM is
# a program office; what makes it direct-reporting is who it reports to, which is a
# relationship, not a type.
ORG_TYPE = {
    "agency": "agency",
    "command": "contracting_activity",
    "acquisition_portfolio": "acquisition_portfolio",
    "program_executive_office": "program_executive_office",
    "program_office": "program_office",
    "technical_center": "technical_office",
    "contracting_office": "contracting_office",
    "direct_reporting_program_manager": "program_office",
}

ROLE_TYPE = [
    ("deputy program manager", "deputy_program_manager"),
    ("program executive officer", "acquisition_leader"),
    ("executive director", "acquisition_leader"),
    ("commander", "acquisition_leader"),
    ("director of contracts", "contracting_leader"),
    ("contracting officer", "contracting_officer"),
    ("contract specialist", "contract_specialist"),
    ("program manager", "program_manager"),
    ("technical director", "technical_lead"),
]


def role_type(role_as_written: str | None) -> str:
    text = (role_as_written or "").lower()
    for needle, mapped in ROLE_TYPE:
        if needle in text:
            return mapped
    return "other"


# The production resolver treats a row with no confidence as having no provenance
# and will not consider it at all, so a number is part of the interface rather than
# something the sources supply. The mapping is deliberate and narrow: a claim a source
# states outright scores 1.0, one we derived scores 0.5, and 0.5 sits below the
# resolver's MIN_HIERARCHY_CONFIDENCE so a derived edge cannot drive an ancestry walk.
DOCUMENTED, DERIVED = "1.0", "0.5"


def chain_or_branch(previous: tuple[str, str] | None, office_id: str) -> str | None:
    """The assertion a new office observation supersedes, or None to start its own chain.

    Supersession may not change the subject. A later release naming the same office is a
    re-statement and chains; one naming a different office is a different claim, so it
    branches and both observations stay current for a reviewer to resolve.
    """
    return previous[1] if previous and previous[0] == office_id else None


def loadable_value(low: str, high: str) -> bool:
    """Both bounds or nothing: the column has no shape for an open-ended range."""
    return bool(low) and bool(high)


def confidence_for(evidence_class: str) -> str:
    return DOCUMENTED if evidence_class == "directly_documented" else DERIVED


def former_names(node: dict) -> list[str]:
    """A former name is an alias. name_history is otherwise dropped on the floor."""
    out = []
    for entry in node.get("name_history") or []:
        name = entry.get("name") if isinstance(entry, dict) else entry
        if name:
            out.append(str(name))
    return out


def live_parent_claims(seed: dict, org_ids: dict[str, str]) -> dict[str, set[str]]:
    claims: dict[str, set[str]] = {}
    for rel in seed["relationships"]:
        if rel["type"] != "child_of" or rel["review_status"] == "retracted":
            continue
        if rel["current_status"]["state"] != "last_confirmed":
            continue
        if rel["from"] in org_ids and rel["to"] in org_ids:
            claims.setdefault(rel["from"], set()).add(rel["to"])
    return claims


def emit_offices(seed: dict, out: list[str]) -> dict[str, str]:
    org_ids: dict[str, str] = {}
    rows = []
    for node in seed["nodes"]:
        if node["type"] == "person":
            continue
        org_id = uid("org", node["id"])
        org_ids[node["id"]] = org_id
        aliases = [a["text"] for a in node.get("aliases", [])] + former_names(node)
        seen, unique = set(), []
        for alias in aliases:
            if norm(alias) not in seen:
                seen.add(norm(alias))
                unique.append(alias)
        codes = node.get("codes") or {}
        rows.append([
            lit(org_id), lit(AGENCY_NAVY),
            lit(AGENCY_NAVY) if node["type"] == "agency" else "null",
            "null",  # parent set below, once every office exists
            lit(node["name"]), lit(norm(node["name"])),
            lit(codes.get("office_code") or codes.get("uic")),
            lit(ORG_TYPE[node["type"]]),
            arr(unique), arr(norm(a) for a in unique),
            jsonb(codes),
            lit(node.get("valid_from")), lit(node.get("valid_to")),
            lit("US"), arr(["US"]), lit("federal"),
            DOCUMENTED if node.get("observation_ids") else DERIVED,
            lit(SEED_SOURCE), lit(node["id"]),
        ])
        for unmapped in ("location", "notes", "capability_portfolios"):
            if node.get(unmapped):
                note_skip(f"gov_organizations has no column for node.{unmapped}")

    insert("public.gov_organizations",
           ["id", "agency_id", "existing_agency_id", "parent_organization_id", "name",
            "normalized_name", "acronym", "org_type", "aliases", "normalized_aliases",
            "external_ids", "valid_from", "valid_to", "jurisdiction_code",
            "jurisdiction_path", "government_level", "confidence", "source", "source_ref"],
           rows, out)

    # parent_organization_id holds one edge. Where the sources give exactly one live
    # `child_of` claim that is the parent; where they give two, the column stays empty
    # and the claims go to gov_organization_relationships instead of one being picked.
    for child, parents in sorted(live_parent_claims(seed, org_ids).items()):
        if len(parents) == 1:
            out.append(f"update public.gov_organizations set parent_organization_id = {lit(org_ids[next(iter(parents))])} "
                       f"where id = {lit(org_ids[child])} and parent_organization_id is null;")
        else:
            note_skip("office with competing live parents left without parent_organization_id")
    out.append("")
    return org_ids


def emit_people(seed: dict, org_ids: dict[str, str], out: list[str]) -> None:
    people = {n["id"]: n for n in seed["nodes"] if n["type"] == "person"}
    insert("public.gov_contacts", ["id", "identity_key", "name", "agency", "role", "source"],
           [[lit(uid("contact", node_id)), lit(f"navy-org-memory:{node_id}"), lit(node["name"]),
             lit("Department of the Navy"), lit("program"), lit(SEED_SOURCE)]
            for node_id, node in people.items()], out)

    rows = []
    for rel in seed["relationships"]:
        if rel["type"] != "leads":
            continue
        if rel["from"] not in people or rel["to"] not in org_ids:
            note_skip("leads relationship without a person and an office at its ends")
            continue
        if rel["review_status"] == "retracted":
            note_skip("retracted leadership claim not loaded")
            continue
        # valid_to is the only way to say a position is over. A leadership claim a
        # source ended or superseded without giving a date would land as an open
        # current position beside the successor, so it is left out.
        state = rel["current_status"]["state"]
        if state in ("ended", "superseded") and not rel.get("effective_to"):
            note_skip(f"leadership claim is {state} with no end date; no column can say so")
            continue
        rows.append([
            lit(uid("position", rel["id"])), lit(uid("contact", rel["from"])), lit(org_ids[rel["to"]]),
            lit(role_type(rel.get("role_as_written"))), lit(rel.get("role_as_written")),
            lit(rel.get("effective_from")), lit(rel.get("effective_to")),
            lit(SEED_SOURCE), lit(rel["id"]),
        ])
    insert("public.gov_contact_positions",
           ["id", "contact_id", "organization_id", "role_type", "raw_title",
            "valid_from", "valid_to", "source", "source_ref"], rows, out)


# --------------------------------------------------------------- office edges

# The production vocabulary has no `child_of`: parentage is the hierarchy column.
# What is left are the edges that column cannot carry.
REL_TYPE = {
    "contracts_for": "contracting_supports",
    "part_of": "functionally_aligned_to",
    "child_of": "functionally_aligned_to",
    "consolidated_into": "successor_to",
}
REVERSED = {"consolidated_into"}  # A consolidated into B means B is the successor


def emit_relationships(seed: dict, org_ids: dict[str, str], out: list[str]) -> None:
    parent_column = {child: next(iter(parents))
                     for child, parents in live_parent_claims(seed, org_ids).items() if len(parents) == 1}
    rows = []
    for rel in seed["relationships"]:
        if rel["type"] == "leads":
            continue
        if rel["review_status"] == "retracted":
            note_skip("retracted claim not loaded (the production table has no retraction)")
            continue
        if rel["type"] not in REL_TYPE:
            note_skip(f"no production relationship_type for `{rel['type']}`")
            continue
        if rel["from"] not in org_ids or rel["to"] not in org_ids:
            note_skip("relationship endpoint missing from the office table")
            continue
        state = rel["current_status"]["state"]
        # The parent column holds the one live `child_of` claim, so that row would be a
        # duplicate. Every other `child_of` row is the office's history - a parent it has
        # since left - and dropping those was flattening the record: NEN under PEO EIS
        # until 2020-05-13 vanished behind NEN under PEO Digital, and the same would
        # happen to every office the PEO/PAE migration moves.
        if (rel["type"] == "child_of" and state == "last_confirmed"
                and parent_column.get(rel["from"]) == rel["to"]):
            continue
        # valid_to is the only way to say a claim is over. A claim a source ended or
        # superseded without giving a date would read as current, so it is left out
        # rather than published as live.
        if state in ("ended", "superseded") and not rel.get("effective_to"):
            note_skip(f"claim is {state} with no end date; no column can say so")
            continue
        source_org, target_org = rel["from"], rel["to"]
        if rel["type"] in REVERSED:
            source_org, target_org = target_org, source_org
        rows.append([
            lit(uid("orgrel", rel["id"])), lit(org_ids[source_org]), lit(org_ids[target_org]),
            lit(REL_TYPE[rel["type"]]), lit(rel.get("effective_from")), lit(rel.get("effective_to")),
            confidence_for(rel["evidence_class"]), lit(SEED_SOURCE), lit(rel["id"]),
        ])
    insert("public.gov_organization_relationships",
           ["id", "source_organization_id", "target_organization_id", "relationship_type",
            "valid_from", "valid_to", "confidence", "source", "source_ref"], rows, out)


# -------------------------------------------------------------------- evidence

# Evidence must point at a Brain item, a Brain document or a procurement reference;
# a bare URL is not accepted. A source statement is a Brain item, which is what one
# is, so the observations land there and the evidence row wraps them.
SECTION = {
    "leadership": "people",
    "contracting_support": "procurement_patterns",
    "parentage": "mission_priorities",
    "consolidation": "mission_priorities",
    "listing": "mission_priorities",
    "naming": "mission_priorities",
    "existence": "mission_priorities",
}


def emit_seed_evidence(seed: dict, out: list[str]) -> dict[str, str]:
    """Returns observation id -> evidence uuid."""
    by_obs, items, evidence = {}, [], []
    for obs in seed["observations"]:
        claim_key = f"navy-org-memory:{obs['id']}"
        item_id = uid("brainitem", claim_key)
        ev_id = uid("evidence", claim_key)
        by_obs[obs["id"]] = ev_id
        passage = obs.get("passage") or obs["statement_type"]
        items.append([
            lit(item_id), lit(AGENCY_NAVY), lit(SECTION.get(obs["statement_type"], "mission_priorities")),
            lit("narrative"), lit(claim_key),
            lit(f"{obs['statement_type']} observed {obs['observed_at']}"), lit(passage),
            jsonb({"url": obs.get("source_url"), "revision": obs.get("source_revision"),
                   "statement_type": obs["statement_type"], "seed_id": obs["id"],
                   "access": obs.get("access")}),
            lit(obs.get("observed_at")),
        ])
        url = obs.get("source_url") or ""
        evidence.append([
            lit(ev_id), lit(item_id), lit(passage),
            lit(url) if url.startswith("http") else "null",
            lit(obs.get("observed_at")), lit("navy-org-memory"), lit(claim_key),
        ])
    insert("public.agency_brain_items",
           ["id", "agency_id", "section", "kind", "claim_key", "title", "body", "source", "as_of"],
           items, out)
    insert("public.gov_intelligence_evidence",
           ["id", "brain_item_id", "excerpt", "source_url", "published_at", "provider", "source_key"],
           evidence, out)
    return by_obs


# ------------------------------------------------------------------ LRAE layers

def read_layer(release: str, name: str) -> list[dict]:
    with (ROOT / "datapack" / release / "layers" / f"{name}.csv").open(newline="") as handle:
        return list(csv.DictReader(handle))


# Federal fiscal quarters: FY26 Q1 starts October 2025.
QUARTER_START = {"Q1": (-1, 10), "Q2": (0, 1), "Q3": (0, 4), "Q4": (0, 7)}
QUARTER_END = {"Q1": (-1, 12, 31), "Q2": (0, 3, 31), "Q3": (0, 6, 30), "Q4": (0, 9, 30)}
MEASURE = {"procurement_estimate": "procurement_estimate", "budget_request": "budget_request",
           "enacted_funding": "enacted_funding", "obligation": "obligation"}
NEED_ROLE = {"requirement_owner": "originating_requirement_owner", "contracting": "contracting_office"}


def fiscal_year(text: str) -> int | None:
    text = (text or "").strip().upper()
    if text.startswith("FY") and text[2:].isdigit():
        year = int(text[2:])
        return 2000 + year if year < 100 else year
    return None


def quarter_bounds(fy: int | None, quarter: str) -> tuple[str | None, str | None]:
    quarter = (quarter or "").strip().upper()
    if fy is None or quarter not in QUARTER_START:
        return None, None
    offset, month = QUARTER_START[quarter]
    end_offset, end_month, end_day = QUARTER_END[quarter]
    return f"{fy + offset:04d}-{month:02d}-01", f"{fy + end_offset:04d}-{end_month:02d}-{end_day:02d}"


def assertion(rows: list, ident: str, kind: str, lineage: str, basis: str, rationale: str,
              source_key: str, observed_at: str | None, supersedes: str | None = None,
              valid_from: str | None = None, valid_to: str | None = None) -> None:
    rows.append([
        lit(ident), lit(kind), lit(lineage), lit(basis), lit(rationale),
        lit(PRODUCER), lit(PRODUCER_VERSION), lit(source_key), lit(observed_at),
        lit(supersedes), lit(valid_from), lit(valid_to),
    ])


ASSERTION_COLUMNS = ["id", "assertion_kind", "lineage_key", "basis", "rationale", "producer",
                     "producer_version", "source_key", "observed_at", "supersedes_id",
                     "valid_from", "valid_to"]


def emit_lrae(org_ids: dict[str, str], out: list[str]) -> None:
    # Evidence first: every LRAE claim cites one spreadsheet row.
    items, evidence, ev_by_id = [], [], {}
    for release in RELEASES:
        for row in read_layer(release, "evidence"):
            claim_key = f"navwar-lrae:{row['id']}"
            item_id, ev_id = uid("brainitem", claim_key), uid("evidence", claim_key)
            ev_by_id[row["id"]] = ev_id
            body = f"{release} {row['locator']}, source sha256 {row['source_sha256']}"
            items.append([
                lit(item_id), lit(AGENCY_NAVY), lit("forecast"), lit("narrative"), lit(claim_key),
                lit(f"LRAE {release} {row['locator']}"), lit(body),
                jsonb({"release": release, "locator": row["locator"],
                       "sha256": row["source_sha256"], "release_date": row["release_date"]}),
                lit(row["release_date"]),
            ])
            evidence.append([lit(ev_id), lit(item_id), lit(body), "null",
                             lit(row["release_date"]), lit("navwar-lrae"), lit(claim_key)])
    insert("public.agency_brain_items",
           ["id", "agency_id", "section", "kind", "claim_key", "title", "body", "source", "as_of"],
           items, out)
    insert("public.gov_intelligence_evidence",
           ["id", "brain_item_id", "excerpt", "source_url", "published_at", "provider", "source_key"],
           evidence, out)

    # A record key identifies the same planned action across releases, so the need is
    # keyed on it alone and each release becomes a revision of its requirement rather
    # than a second need describing the same thing.
    needs, need_releases, first_seen = {}, {}, {}
    # Each release states its own date. Merging the need records must not let a 2025
    # release date attach to the 2023 revision of a line that appears in both.
    stated_on: dict[tuple[str, str], str | None] = {}
    per_release: dict[tuple[str, str], dict] = {}
    for release in RELEASES:
        for row in read_layer(release, "needs"):
            key = row["record_key"]
            needs.setdefault(key, row)
            needs[key] = {**needs[key], **{k: v for k, v in row.items() if v}}
            need_releases.setdefault(key, []).append(release)
            per_release[(release, key)] = row
            seen = row["valid_from"] or None
            stated_on[(release, key)] = seen
            if seen and (first_seen.get(key) is None or seen < first_seen[key]):
                first_seen[key] = seen

    insert("public.gov_needs", ["id", "agency_id", "title", "description", "lifecycle", "source", "source_key"],
           [[lit(uid("need", key)), lit(AGENCY_NAVY), lit(row["title"]),
             lit(f"NAVWAR Long Range Acquisition Estimate line {key}, first seen {first_seen.get(key) or 'undated'}, "
                 f"released in {', '.join(need_releases[key])}"),
             lit("identified"), lit(LRAE_SOURCE), lit(key)]
            for key, row in needs.items()], out)

    assertions, details, links = [], {"need_organization": [], "requirement": [], "funding": []}, []

    def cite(assertion_id: str, evidence_id: str | None, direct: bool) -> bool:
        if not evidence_id:
            note_skip("claim with no evidence row; not loaded")
            return False
        links.append([lit(assertion_id), lit(evidence_id), lit("supports"), "true" if direct else "false"])
        return True

    # Which office owns the requirement and which one contracts for it, per release.
    #
    # Merging the need records and reading one office off the result applies the
    # newest release's office to every earlier year. Each release is its own dated
    # observation instead. Where consecutive releases name the same office the later
    # assertion supersedes the earlier, so the current view holds one row; where they
    # name different offices supersession is refused by design (it may not change the
    # subject), both observations stay live, and the disagreement is visible rather
    # than resolved by whichever row was read last.
    last_office: dict[tuple[str, str], tuple[str, str]] = {}
    for release in RELEASES:
        for key in sorted(k for r, k in per_release if r == release):
            row = per_release[(release, key)]
            ev_id = ev_by_id.get(row["evidence_id"])
            for local_id, role in ((row["office_id"], "requirement_owner"),
                                   ("contracting:" + row["contracting_office_uic"].lower(), "contracting")):
                if local_id not in org_ids:
                    note_skip(f"LRAE office {local_id} has no node in the org memory")
                    continue
                ident = uid("assert", f"needorg:{release}:{key}:{local_id}:{role}")
                if not cite(ident, ev_id, True):
                    continue
                previous = last_office.get((key, role))
                prior = chain_or_branch(previous, local_id)
                if previous and prior is None:
                    note_skip(f"office for a {role.replace('_', ' ')} changed between releases; "
                              f"both observations kept")
                last_office[(key, role)] = (local_id, ident)
                assertion(assertions, ident, "need_organization",
                          f"need_organization:{key}:{role}", "documented",
                          f"{release} names this office as the {role.replace('_', ' ')}.",
                          f"{LRAE_SOURCE}:{release}:{key}:{role}",
                          stated_on.get((release, key)), prior)
                details["need_organization"].append(
                    [lit(ident), lit(uid("need", key)), lit(org_ids[local_id]), lit(NEED_ROLE[role])])

    # One requirement per need, one revision assertion per release it appeared in.
    # A later release supersedes the earlier assertion, which is how a slipping
    # award date stays visible instead of being overwritten.
    requirements, revisions_by_need, funding_scope = [], {}, {}
    for release in RELEASES:
        for row in read_layer(release, "need_requirements"):
            key = row["need_id"].split(":", 2)[2]
            req_id = uid("requirement", key)
            if key not in revisions_by_need:
                requirements.append([lit(req_id), lit(uid("need", key)), lit("lrae-line"), lit("scope")])
                revisions_by_need[key] = []
            ident = uid("assert", f"requirement:{key}:{release}")
            ev_id = ev_by_id.get(row["evidence_id"])
            if not cite(ident, ev_id, True):
                continue
            prior = revisions_by_need[key][-1] if revisions_by_need[key] else None
            revisions_by_need[key].append(ident)
            award_fy = fiscal_year(row["award_fy"])
            expected_from, expected_to = quarter_bounds(award_fy, row["award_quarter"])
            statement = row["description"] or needs[key]["title"]
            assertion(assertions, ident, "requirement", f"requirement:{key}", "documented",
                      f"{release} states the scope, method ({row['procurement_method'] or 'unstated'}) "
                      f"and award timing ({row['award_fy'] or 'unstated'} {row['award_quarter']}).".strip(),
                      f"{LRAE_SOURCE}:{release}:{row['id']}", stated_on.get((release, key)), prior)
            details["requirement"].append(
                [lit(ident), lit(req_id), lit(statement), lit(expected_from), lit(expected_to)])

    # An LRAE value range is an estimate, not an obligation, and `measure` says so.
    #
    # The table accepts a flat amount or a closed range and nothing else. The LRAE
    # never states a flat amount, so a row is loadable only when the source gives
    # both bounds. "> $1B+" gives a floor and no ceiling; writing the floor as the
    # amount would publish "exactly $1B" for a buy the Navy only said exceeds $1B,
    # and writing the floor as both bounds would be the same lie twice. Those rows
    # and the "No Range Specified" ones stay out until the column can hold an open
    # range, and the wording the source used travels with every row that does load.
    for release in RELEASES:
        for row in read_layer(release, "funding_observations"):
            stated = (row["as_stated"] or "").strip()
            if not row["amount_low_usd"] and not row["amount_high_usd"]:
                note_skip(f"no value stated ({stated or 'blank'})")
                continue
            if not row["amount_low_usd"] or not row["amount_high_usd"]:
                note_skip(f"open-ended value the schema cannot hold ({stated})")
                continue
            key = row["need_id"].split(":", 2)[2]
            ident = uid("assert", f"funding:{key}:{release}")
            ev_id = ev_by_id.get(row["evidence_id"])
            if not cite(ident, ev_id, True):
                continue
            fy = fiscal_year(row["fiscal_year"])
            start, end = quarter_bounds(fy, row["period"])
            low, high = row["amount_low_usd"], row["amount_high_usd"]
            # Supersession may not change the measurement scope, so a re-estimate of
            # the same need for the same fiscal period chains and only the latest
            # stays current. A move to a different fiscal year is a different
            # measurement, not a correction, and both remain on the record.
            scope = (key, "procurement_estimate", fy, start, end)
            prior = funding_scope.get(scope)
            funding_scope[scope] = ident
            assertion(assertions, ident, "funding",
                      f"funding:{key}:{row['fiscal_year'] or 'unstated'}:{row['period'] or 'unstated'}",
                      "documented",
                      f"{release} states an anticipated total value of {row['as_stated'] or 'an unstated range'}.",
                      f"{LRAE_SOURCE}:{release}:{row['id']}", stated_on.get((release, key)), prior)
            details["funding"].append([
                lit(ident), lit(uid("need", key)), lit("procurement_estimate"),
                "null", lit(low), lit(high),
                str(fy) if fy else "null", lit(start), lit(end),
                lit(f"NAVWAR LRAE {release} anticipated total contract value, "
                    f"stated as {stated}"),
            ])

    insert("public.gov_intelligence_assertions", ASSERTION_COLUMNS, assertions, out)
    insert("public.gov_need_organizations", ["assertion_id", "need_id", "organization_id", "role"],
           details["need_organization"], out)
    insert("public.gov_need_requirements", ["id", "need_id", "requirement_key", "kind"], requirements, out)
    insert("public.gov_requirement_revisions",
           ["assertion_id", "requirement_id", "statement", "expected_from", "expected_to"],
           details["requirement"], out)
    insert("public.gov_funding_observations",
           ["assertion_id", "need_id", "measure", "amount", "amount_low", "amount_high",
            "fiscal_year", "period_start", "period_end", "scope_description"],
           details["funding"], out)
    insert("public.gov_assertion_evidence", ["assertion_id", "evidence_id", "relationship", "is_direct"],
           links, out)

    # gov_procurement_refs keys on a row that already exists in sam_opportunities,
    # usa_awards, usa_award_children or gov_procurement_records. An incumbent PIID
    # read off a forecast spreadsheet is none of those until it is ingested.
    piids = {row["identifier"] for release in RELEASES for row in read_layer(release, "procurement_refs")}
    for _ in piids:
        note_skip("incumbent PIID has no procurement record to reference")


def main() -> int:
    seed = json.loads(SEED.read_text())
    out: list[str] = ["-- generated by research/tools/agency_layers_sql.py; do not edit by hand",
                      "begin;",
                      "set constraints all deferred;", ""]
    emit_agencies(out)
    org_ids = emit_offices(seed, out)
    emit_people(seed, org_ids, out)
    emit_relationships(seed, org_ids, out)
    emit_seed_evidence(seed, out)
    emit_lrae(org_ids, out)
    out += ["commit;"]
    sys.stdout.write("\n".join(out) + "\n")
    for reason, count in sorted(skipped.items()):
        print(f"skipped: {reason} x{count}", file=sys.stderr)
    return 0


def selfcheck() -> int:
    assert lit("O'Brien") == "'O''Brien'"
    assert lit(None) == "null" and lit("") == "null"
    assert arr([]) == "'{}'::text[]" and arr(["a", "", "b'c"]) == "array['a','b''c']::text[]"
    assert norm("  PMW   160 ") == "pmw 160"

    assert fiscal_year("FY26") == 2026 and fiscal_year("") is None and fiscal_year("TBD") is None
    # FY26 Q1 is the last quarter of calendar 2025; backwards would date every
    # first-quarter forecast a year late.
    assert quarter_bounds(2026, "Q1") == ("2025-10-01", "2025-12-31")
    assert quarter_bounds(2026, "Q4") == ("2026-07-01", "2026-09-30")
    assert quarter_bounds(None, "Q1") == (None, None) and quarter_bounds(2026, "") == (None, None)

    assert role_type("Deputy Program Manager") == "deputy_program_manager"
    assert role_type("Program Executive Officer (acting from 2023-05)") == "acquisition_leader"
    assert role_type(None) == "other"

    assert sha({"b": 1, "a": 2}) == sha({"a": 2, "b": 1}), "hash must not depend on key order"
    assert uid("org", "pmw:160") == uid("org", "pmw:160") != uid("need", "pmw:160")

    def rel(ident, kind, src, dst, state="last_confirmed", review="draft", to=None):
        return {"id": ident, "type": kind, "from": src, "to": dst, "review_status": review,
                "current_status": {"state": state}, "effective_from": None, "effective_to": to,
                "effective_dates_status": "unknown", "evidence_class": "directly_documented"}

    seed = {"nodes": [{"id": f"o:{n}", "type": "program_office", "name": f"Office {n}",
                       "aliases": [], "codes": {}} for n in range(4)],
            "relationships": [rel("r1", "child_of", "o:0", "o:1"),
                              rel("r2", "child_of", "o:2", "o:0"),
                              rel("r3", "child_of", "o:2", "o:1"),
                              rel("r4", "contracts_for", "o:3", "o:1"),
                              rel("r5", "consolidated_into", "o:3", "o:0"),
                              rel("r6", "child_of", "o:3", "o:1", state="ended"),
                              rel("r7", "child_of", "o:3", "o:2", review="retracted"),
                              # o:0 sits under o:1 now and sat under o:2 until 2020-05-13.
                              # This is the NEN case: PEO EIS then PEO Digital.
                              rel("r10", "child_of", "o:0", "o:2", state="ended", to="2020-05-13")]}
    lines: list[str] = []
    ids = emit_offices(seed, lines)
    updates = [l for l in lines if l.startswith("update")]
    assert len(updates) == 1 and ids["o:0"] in updates[0] and ids["o:1"] in updates[0]
    assert ids["o:2"] not in updates[0], "office with two live parents must stay unparented"

    lines = []
    emit_relationships(seed, ids, lines)
    body = "\n".join(lines)
    assert "'contracting_supports'" in body, "contracts_for must map to contracting_supports"
    # o:3 consolidated into o:0 makes o:0 the successor, so the edge points the other way.
    successor = [l for l in body.splitlines() if "'successor_to'" in l][0]
    assert successor.index(ids["o:0"]) < successor.index(ids["o:3"])
    # r1 is already the parent column; r6 ended with no date; r7 is retracted.
    # r2, r3 and r10 load. r10 is the office's former parent, and an office keeping its
    # current parent in the column must not cost it the parent it used to have.
    assert body.count("'functionally_aligned_to'") == 3, body.count("'functionally_aligned_to'")
    former = [l for l in body.splitlines() if "'r10'" in l]
    assert len(former) == 1 and "'2020-05-13'" in former[0], former
    assert former[0].index(ids["o:0"]) < former[0].index(ids["o:2"]), "the child is the source of a child_of edge"

    # A leadership claim a source superseded without a date must not load as a
    # current position beside the person who replaced them.
    seed["nodes"].append({"id": "person:a", "type": "person", "name": "A", "aliases": [], "codes": {}})
    seed["nodes"].append({"id": "person:b", "type": "person", "name": "B", "aliases": [], "codes": {}})
    seed["relationships"] += [
        {**rel("r8", "leads", "person:a", "o:0", state="superseded"), "role_as_written": "Program Manager"},
        {**rel("r9", "leads", "person:b", "o:0"), "role_as_written": "Program Manager"}]
    lines = []
    m_ids = dict(ids)
    m_ids.pop("person:a", None)
    emit_people(seed, m_ids, lines)
    body = "\n".join(lines)
    assert body.count("'Program Manager'") == 1, "superseded leader must not load as current"

    # "> $1B+" states a floor and no ceiling. Reading the floor as the amount
    # publishes "exactly $1B" for a buy the source only said exceeds it.
    # A release that re-states the same office chains; one that names a different office
    # branches, so the older observation is not overwritten by the newer office.
    assert chain_or_branch(("office:nen", "assert:1"), "office:nen") == "assert:1"
    assert chain_or_branch(("office:nen", "assert:1"), "office:other") is None
    assert chain_or_branch(None, "office:nen") is None

    assert loadable_value("1000000000", "") is False
    assert loadable_value("", "") is False
    assert loadable_value("100000000", "250000000") is True

    assert confidence_for("directly_documented") == "1.0"
    assert confidence_for("inferred") == "0.5" and float(DERIVED) < 0.8, \
        "a derived edge must stay under the resolver's hierarchy threshold"

    print("selfcheck ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(selfcheck() if "--selfcheck" in sys.argv else main())
