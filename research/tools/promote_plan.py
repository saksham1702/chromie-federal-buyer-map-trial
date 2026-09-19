#!/usr/bin/env python3
"""Plan a promotion of the loaded Navy pilot into the production agency-intelligence tables.

    python research/tools/promote_plan.py                 # match offices, print the plan
    python research/tools/promote_plan.py --emit-sql FILE  # write SQL for a human to run
    python research/tools/promote_plan.py --selfcheck

Read-only against production. It never writes there and holds no code that could:
the only production calls are GET, and the SQL it can emit goes to a file for a
person to read and run.

Why a plan rather than a push. The production layer tables are append-only - both
UPDATE and DELETE raise - so a row inserted against the wrong office cannot be
removed, only retracted. The offices also already exist in production with their own
ids, while the local load minted its own, so a straight copy would create duplicate
program offices that un-deletable assertions then point at. Everything here exists to
make that mismatch visible before anything is written.

Matching is deliberately narrow. An office code carries the claim; an exact name or
alias is accepted only when the organization types agree; anything matching two
production rows is refused rather than guessed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

LOCAL_DSN = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
ENV_FILE = Path.home() / "chromie/.env.local"

# Types that may stand in for one another. A program office is never a contracting
# office, and matching across the line would put the buy on the wrong desk.
TYPE_FAMILY = {
    "program_office": "program",
    "direct_reporting_program_manager": "program",
    "program_executive_office": "portfolio",
    "acquisition_portfolio": "portfolio",
    "contracting_office": "contracting",
    "contracting_activity": "contracting",
    "contracting_directorate": "contracting",
    "contracting_division": "contracting",
    "contracting_branch": "contracting",
    "hca_office": "contracting",
    "technical_office": "technical",
    "field_activity": "technical",
    "agency": "agency",
    "department": "agency",
    "other": "other",
}
FAMILIES = ("PMW", "PMA", "PMS", "PEO")
# `PMW/A 170` is one office with a service letter. `PMA/PMW 101` is one office written
# under two code families, and collapsing it to the second loses the designation a
# production row might be stored under.
CODE_RE = re.compile(
    r"\b(?P<first>PMW|PMA|PMS|PEO)\s*(?:/\s*(?P<second>PMW|PMA|PMS|PEO|[A-Z])\s*)?-?\s*(?P<number>\d{3})\b")

# Tables whose rows carry a reference to an office and therefore have to be rewritten.
OFFICE_REFS = {
    "gov_organization_relationships": ("source_organization_id", "target_organization_id"),
    "gov_need_organizations": ("organization_id",),
    "gov_contact_positions": ("organization_id",),
}

# Insert order is foreign-key order, and the list is the dependency closure: evidence
# cannot be written without the Brain items it points at, and positions cannot be
# written without their contacts. `created_at` and `recorded_at` are left to
# production defaults; `observed_at` is data and is carried.
PROMOTION = (
    ("gov_contacts", "id, identity_key, name, agency, role, source"),
    ("agency_brain_items", "id, agency_id, section, kind, claim_key, title, body, source, as_of"),
    ("gov_intelligence_evidence",
     "id, brain_item_id, excerpt, source_url, published_at, provider, source_key"),
    ("gov_needs", "id, agency_id, title, description, lifecycle, source, source_key"),
    ("gov_need_requirements", "id, need_id, requirement_key, kind"),
    ("gov_intelligence_assertions",
     "id, assertion_kind, lineage_key, basis, rationale, producer, producer_version, "
     "source_key, observed_at, supersedes_id, valid_from, valid_to"),
    ("gov_requirement_revisions",
     "assertion_id, requirement_id, statement, expected_from, expected_to"),
    ("gov_funding_observations",
     "assertion_id, need_id, measure, amount, amount_low, amount_high, currency_code, "
     "unit_multiplier, fiscal_year, period_start, period_end, scope_description"),
    ("gov_need_organizations", "assertion_id, need_id, organization_id, role"),
    ("gov_assertion_evidence", "assertion_id, evidence_id, relationship, is_direct"),
    ("gov_contact_positions",
     "id, contact_id, organization_id, role_type, raw_title, valid_from, valid_to, "
     "source, source_ref"),
    ("gov_organization_relationships",
     "id, source_organization_id, target_organization_id, relationship_type, "
     "valid_from, valid_to, confidence, source, source_ref"),
)
REMAP_OFFICE = {"organization_id", "source_organization_id", "target_organization_id"}
REMAP_AGENCY = {"agency_id"}

# An assertion will not commit without its typed detail row: the completeness check is
# a constraint trigger deferred to commit, so holding a detail table back while still
# writing its assertions rolls the whole transaction back at the very end, and the
# tables that were ready never land either.
DETAIL_OF_KIND = {
    "requirement": "gov_requirement_revisions",
    "funding": "gov_funding_observations",
    "need_organization": "gov_need_organizations",
    "program_organization": "gov_program_organizations",
    "program_need": "gov_program_needs",
    "procurement_attribution": "gov_procurement_attributions",
    "program_procurement": "gov_program_procurements",
    "need_procurement": "gov_need_procurements",
    "procurement_lineage": "gov_procurement_lineage",
}


def lit(value) -> str:
    """Quote for Postgres. standard_conforming_strings is on, so doubling ' is enough."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (dict, list)):
        return "'" + json.dumps(value, sort_keys=True).replace("'", "''") + "'::jsonb"
    return "'" + str(value).replace("'", "''") + "'"


def order_assertions(rows: list[dict]) -> list[dict]:
    """A superseding assertion cannot be inserted before the one it supersedes.

    The guard looks the prior row up at insert time, so ordering is not optional and
    a chain of any depth has to come out parent-first.
    """
    remaining = {r["id"]: r for r in rows}
    placed, out = set(), []
    while remaining:
        ready = [r for r in remaining.values()
                 if not r.get("supersedes_id") or r["supersedes_id"] in placed
                 or r["supersedes_id"] not in remaining]
        if not ready:
            raise SystemExit("supersession cycle; cannot order assertions")
        for row in ready:
            out.append(row)
            placed.add(row["id"])
            del remaining[row["id"]]
    return out


def local(sql: str):
    out = subprocess.run(["psql", LOCAL_DSN, "-At", "-c", sql], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"local psql failed: {out.stderr.strip()}")
    return json.loads(out.stdout.strip() or "[]")


def rows_of(table: str, columns: str = "*"):
    return local(f"select coalesce(json_agg(row_to_json(t)),'[]') from "
                 f"(select {columns} from public.{table}) t")


def prod_env() -> tuple[str, str]:
    if not ENV_FILE.exists():
        raise SystemExit(f"no {ENV_FILE}; cannot reach production read-only")
    values = {}
    for line in ENV_FILE.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    url, key = values.get("SUPABASE_URL"), values.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise SystemExit("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing")
    return url, key


def prod_get(table: str, select: str) -> list[dict]:
    """GET only. PostgREST caps a page at 1000, so this pages until short."""
    url, key = prod_env()
    out, offset = [], 0
    while True:
        target = (f"{url}/rest/v1/{table}?select={select}&order=id&limit=1000&offset={offset}")
        result = subprocess.run(
            ["curl", "-sS", "-X", "GET", target,
             "-H", f"apikey: {key}", "-H", f"Authorization: Bearer {key}"],
            capture_output=True, text=True)
        if result.returncode != 0:
            raise SystemExit(f"production read failed: {result.stderr.strip()}")
        page = json.loads(result.stdout or "[]")
        if isinstance(page, dict):
            raise SystemExit(f"production read failed: {page}")
        out += page
        if len(page) < 1000:
            return out
        offset += 1000


# ----------------------------------------------------------------- office match

def office_codes(row: dict) -> set[str]:
    text = [row.get("acronym") or "", row.get("name") or "", *(row.get("aliases") or [])]
    text += [str(v) for v in (row.get("external_ids") or {}).values()]
    out = set()
    for value in text:
        for m in CODE_RE.finditer(value.upper()):
            number, second = m.group("number"), m.group("second")
            out.add(m.group("first") + number)
            if second in FAMILIES:
                out.add(second + number)
    return out


def office_names(row: dict) -> set[str]:
    values = {(row.get("name") or "").strip().lower()}
    values |= {a.strip().lower() for a in (row.get("aliases") or [])}
    return {v for v in values if v}


def compatible(a: str, b: str) -> bool:
    return TYPE_FAMILY.get(a, a) == TYPE_FAMILY.get(b, b)


def match_offices(local_rows: list[dict], prod_rows: list[dict]) -> tuple[dict, dict, list]:
    by_code, by_name = {}, {}
    for row in prod_rows:
        for code in office_codes(row):
            by_code.setdefault(code, []).append(row)
        for name in office_names(row):
            by_name.setdefault(name, []).append(row)

    resolved, ambiguous, unmatched = {}, {}, []
    for row in local_rows:
        hits = {p["id"]: p for code in office_codes(row) for p in by_code.get(code, [])
                if compatible(row["org_type"], p["org_type"])}
        how = "office code"
        if not hits:
            hits = {p["id"]: p for name in office_names(row) for p in by_name.get(name, [])
                    if compatible(row["org_type"], p["org_type"])}
            how = "exact name"
        if len(hits) == 1:
            target = next(iter(hits.values()))
            resolved[row["id"]] = {"local": row, "prod": target, "how": how}
        elif hits:
            ambiguous[row["id"]] = {"local": row, "candidates": list(hits.values())}
        else:
            unmatched.append(row)

    # One local office hitting two production rows is refused above. The reverse is
    # just as wrong and easier to miss: two distinct offices resolving to the same
    # production row silently merges them, and the layer tables are append-only, so
    # the merge cannot be undone afterwards. Refuse both sides of the collision.
    claimed: dict[str, list[str]] = {}
    for local_id, entry in resolved.items():
        claimed.setdefault(entry["prod"]["id"], []).append(local_id)
    for local_ids in claimed.values():
        if len(local_ids) < 2:
            continue
        refs = {i: resolved[i]["local"]["source_ref"] for i in local_ids}
        for local_id in local_ids:
            entry = resolved.pop(local_id)
            ambiguous[local_id] = {
                "local": entry["local"], "candidates": [entry["prod"]],
                "note": "shares this production row with "
                        + ", ".join(refs[i] for i in local_ids if i != local_id)}
    return resolved, ambiguous, unmatched


def referenced_offices() -> dict[str, set[str]]:
    """Offices each table points at. An unresolved office blocks its own table only."""
    used: dict[str, set[str]] = {}
    for table, columns in OFFICE_REFS.items():
        for row in rows_of(table, ", ".join(columns)):
            used.setdefault(table, set()).update(row[c] for c in columns if row.get(c))
    return used


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-sql", type=Path)
    args = parser.parse_args(argv)

    local_orgs = rows_of("gov_organizations",
                         "id, source_ref, name, acronym, org_type, aliases, external_ids")
    prod_orgs = prod_get("gov_organizations", "id,name,acronym,org_type,external_ids,aliases")
    print(f"local offices {len(local_orgs)} | production offices {len(prod_orgs)}\n")

    resolved, ambiguous, unmatched = match_offices(local_orgs, prod_orgs)
    by_table = referenced_offices()
    used = set().union(*by_table.values()) if by_table else set()

    print(f"resolved {len(resolved)}   ambiguous {len(ambiguous)}   unmatched {len(unmatched)}\n")
    for entry in sorted(resolved.values(), key=lambda e: e["local"]["source_ref"]):
        mark = "*" if entry["local"]["id"] in used else " "
        print(f" {mark} {entry['local']['source_ref']:<22} by {entry['how']:<11} -> {entry['prod']['name'][:60]}")
    for entry in sorted(ambiguous.values(), key=lambda e: e["local"]["source_ref"]):
        mark = "*" if entry["local"]["id"] in used else " "
        reason = entry.get("note") or f"{len(entry['candidates'])} production rows"
        print(f" {mark} {entry['local']['source_ref']:<22} AMBIGUOUS, {reason}:")
        for candidate in entry["candidates"]:
            print(f"     - {candidate['org_type']:<26} {candidate['name'][:56]}")
    for row in sorted(unmatched, key=lambda r: r["source_ref"]):
        mark = "*" if row["id"] in used else " "
        print(f" {mark} {row['source_ref']:<22} NO PRODUCTION ROW   ({row['org_type']})")
    print("\n * marks an office some row being promoted points at.\n")

    by_id = {r["id"]: r for r in local_orgs}
    unresolved = {oid for oid in used if oid not in resolved}

    # A table is promotable when every office its rows point at resolves. Blocking the
    # whole load on an edge nobody needs would hold back the part that is ready.
    # The whole dependency closure, not just the interesting tables: evidence needs
    # its Brain items and positions need their contacts, and leaving either out emits
    # SQL that fails on a foreign key at the far end of a long transaction.
    tables = tuple(table for table, _ in PROMOTION)
    ready, held = [], []
    for table in tables:
        count = len(rows_of(table, "1"))
        blocked_by = sorted(by_id[o]["source_ref"] for o in by_table.get(table, set())
                            if o in unresolved)
        (held if blocked_by else ready).append((table, count, blocked_by))

    print("ready to promote:")
    for table, count, _ in ready:
        print(f"  {count:>6}  {table}")
    print(f"\n  {len(resolved)} office references rewritten to production ids; "
          f"0 offices created.")

    if held:
        held_detail_kinds = {kind for kind, detail in DETAIL_OF_KIND.items()
                             if detail in {t for t, _, _ in held}}
        print("\nheld back:")
        for table, count, blocked_by in held:
            print(f"  {count:>6}  {table}   needs {', '.join(blocked_by)}")
        if held_detail_kinds:
            print(f"  ...and every assertion of kind {', '.join(sorted(held_detail_kinds))}, "
                  f"which cannot commit without its detail row")
        print("\nThese offices do not exist in production under any name or code:")
        for oid in sorted(unresolved, key=lambda o: by_id[o]["source_ref"]):
            row = by_id[oid]
            print(f"  {row['source_ref']:<22} {row['org_type']:<28} {row['name'][:44]}")
        print("Creating them is an organization-registry decision, not part of this load.")

    if not ready:
        print("\nNothing is promotable. No SQL written.")
        return 1
    if not args.emit_sql:
        print("\nRe-run with --emit-sql FILE to write the statements for review. "
              "Nothing is ever written to production by this tool.")
        return 0

    office_map = {local_id: entry["prod"]["id"] for local_id, entry in resolved.items()}
    agency_map = map_agencies()
    promotable = {table for table, _, _ in ready}
    written = emit_sql(args.emit_sql, promotable, office_map, agency_map,
                       held=[(t, c, b) for t, c, b in held])
    print(f"\nwrote {args.emit_sql}")
    for table, count in written:
        print(f"  {count:>6}  {table}")
    print("\nRead it, then run it yourself against production. This tool will not.")
    return 0


def map_agencies() -> dict[str, str]:
    """Production already has the agencies; a promotion points at them, never inserts."""
    local_rows = rows_of("agencies", "id, level, toptier_code, subtier_code, canonical_name")
    prod_rows = prod_get("agencies", "id,level,toptier_code,subtier_code,canonical_name")
    index = {(r["level"], r["toptier_code"], r["subtier_code"]): r for r in prod_rows}
    mapping = {}
    for row in local_rows:
        key = (row["level"], row["toptier_code"], row["subtier_code"])
        target = index.get(key)
        if not target:
            raise SystemExit(f"no production agency for {key}; refusing to guess")
        mapping[row["id"]] = target["id"]
    return mapping


def emit_sql(path: Path, promotable: set[str], office_map: dict[str, str],
             agency_map: dict[str, str], held: list) -> list[tuple[str, int]]:
    lines = [
        "-- Navy pilot promotion, generated by research/tools/promote_plan.py.",
        "-- Read before running. These tables are append-only: UPDATE and DELETE raise,",
        "-- and an assertion allows one retraction and nothing else. Inserted rows stay.",
        f"-- Offices are rewritten to {len(office_map)} existing production rows; none are created.",
        "",
        "begin;",
        "set constraints all deferred;",
        "",
    ]
    held_kinds = {kind for kind, detail in DETAIL_OF_KIND.items()
                  if detail not in promotable}
    dropped: set[str] = set()
    written = []
    for table, columns in PROMOTION:
        if table not in promotable:
            continue
        names = [c.strip() for c in columns.split(",")]
        rows = rows_of(table, columns)
        if table == "gov_intelligence_assertions":
            keep = [r for r in rows if r["assertion_kind"] not in held_kinds]
            dropped = {r["id"] for r in rows if r["assertion_kind"] in held_kinds}
            rows = order_assertions(keep)
        if table == "gov_assertion_evidence" and dropped:
            rows = [r for r in rows if r["assertion_id"] not in dropped]
        if not rows:
            continue
        values = []
        for row in rows:
            cells = []
            for name in names:
                value = row[name]
                if name in REMAP_OFFICE and value is not None:
                    value = office_map[value]
                elif name in REMAP_AGENCY and value is not None:
                    value = agency_map[value]
                cells.append(lit(value))
            values.append("  (" + ", ".join(cells) + ")")
        lines.append(f"insert into public.{table} ({', '.join(names)}) values")
        lines.append(",\n".join(values))
        lines.append("on conflict do nothing;")
        lines.append("")
        written.append((table, len(rows)))
    for table, count, blocked_by in held:
        lines.append(f"-- held back: {count} rows of {table}, "
                     f"pending production offices for {', '.join(blocked_by)}")
    if dropped:
        lines.append(f"-- held back with them: {len(dropped)} assertions of kind "
                     f"{', '.join(sorted(held_kinds))}, which cannot commit without "
                     f"their detail rows")
    lines += ["", "commit;"]
    path.write_text("\n".join(lines) + "\n")
    return written


def selfcheck() -> int:
    assert office_codes({"name": "Tactical Networks (PMW 160)"}) == {"PMW160"}
    # A single letter after the slash is a service variant of one office.
    assert office_codes({"name": "Communications and GPS Navigation (PMW/A 170)"}) == {"PMW170"}
    # Two families after the slash are two designations of one office, and a
    # production row may be filed under either, so both have to be searchable.
    assert office_codes({"name": "PMA/PMW 101 MIDS"}) == {"PMA101", "PMW101"}
    assert office_codes({"acronym": "PMS 485"}) == {"PMS485"}
    assert office_codes({"external_ids": {"office_code": "PMW 740"}}) == {"PMW740"}
    assert office_codes({"name": "NAVWAR HQ contracts directorate"}) == set()

    assert compatible("program_office", "program_office")
    assert compatible("direct_reporting_program_manager", "program_office")
    assert compatible("contracting_activity", "contracting_office")
    # The one that matters: a buy must never land on a contracting desk as its owner.
    assert not compatible("program_office", "contracting_office")
    assert not compatible("program_executive_office", "program_office")

    loc = [{"id": "L1", "source_ref": "pmw:160", "name": "PMW 160 Tactical Networks",
            "org_type": "program_office", "aliases": [], "external_ids": {}},
           {"id": "L2", "source_ref": "pmw:999", "name": "Nowhere Office",
            "org_type": "program_office", "aliases": [], "external_ids": {}},
           {"id": "L3", "source_ref": "dup", "name": "Twin",
            "org_type": "program_office", "aliases": [], "external_ids": {}}]
    pro = [{"id": "P1", "name": "Tactical Networks (PMW 160)", "org_type": "program_office",
            "aliases": [], "external_ids": {}},
           {"id": "P2", "name": "Twin", "org_type": "program_office", "aliases": [], "external_ids": {}},
           {"id": "P3", "name": "Twin", "org_type": "program_office", "aliases": [], "external_ids": {}},
           {"id": "P4", "name": "PMW 160 Contracts", "org_type": "contracting_office",
            "aliases": [], "external_ids": {}}]
    resolved, ambiguous, unmatched = match_offices(loc, pro)
    assert set(resolved) | set(ambiguous) | {r["id"] for r in unmatched} == {"L1", "L2", "L3"}
    # P4 shares the code but not the family, so the code match stays single.
    assert resolved["L1"]["prod"]["id"] == "P1" and resolved["L1"]["how"] == "office code"
    assert [r["id"] for r in unmatched] == ["L2"]
    assert "L3" in ambiguous and len(ambiguous["L3"]["candidates"]) == 2

    # Two local offices resolving onto one production row merges them permanently,
    # so both sides of the collision are refused rather than either being picked.
    twins = [{"id": "A", "source_ref": "a", "name": "PMW 300 One", "org_type": "program_office",
              "aliases": [], "external_ids": {}},
             {"id": "B", "source_ref": "b", "name": "PMW 300 Two", "org_type": "program_office",
              "aliases": [], "external_ids": {}}]
    one = [{"id": "P9", "name": "Something (PMW 300)", "org_type": "program_office",
            "aliases": [], "external_ids": {}}]
    r2, a2, u2 = match_offices(twins, one)
    assert r2 == {}, "a shared production row must not resolve for either office"
    assert set(a2) == {"A", "B"} and "shares this production row with b" in a2["A"]["note"]

    # Every assertion kind must know the detail table it cannot commit without.
    detail_tables = {t for t, _ in PROMOTION}
    assert set(DETAIL_OF_KIND.values()) >= {"gov_requirement_revisions",
                                            "gov_funding_observations",
                                            "gov_need_organizations"}
    assert detail_tables & set(DETAIL_OF_KIND.values())
    assert lit(None) == "null" and lit(True) == "true" and lit(3) == "3"
    assert lit("O'Brien") == "'O''Brien'"
    assert lit({"b": 1, "a": 2}) == """'{"a": 2, "b": 1}'::jsonb"""
    # No text[] column is in PROMOTION, so a list can only be jsonb here. If an array
    # column is ever added, this renders it wrong and the assertion has to change too.
    assert lit(["x"]) == """'["x"]'::jsonb"""
    assert not any(c.strip() in {"aliases", "normalized_aliases", "jurisdiction_path"}
                   for _, cols in PROMOTION for c in cols.split(",")), \
        "an array column reached PROMOTION; lit() would emit jsonb for it"

    # A superseding assertion cannot be inserted before the one it supersedes: the
    # guard looks the prior row up at insert time.
    chain = [{"id": "c", "supersedes_id": "b"}, {"id": "a", "supersedes_id": None},
             {"id": "b", "supersedes_id": "a"}]
    order = [r["id"] for r in order_assertions(chain)]
    assert order.index("a") < order.index("b") < order.index("c"), order
    # A row superseding something outside this batch is already safe to insert.
    assert [r["id"] for r in order_assertions([{"id": "z", "supersedes_id": "elsewhere"}])] == ["z"]

    # Every table that is referenced must itself be promoted, or the emitted SQL
    # fails on a foreign key at the far end of a long transaction.
    promoted = [t for t, _ in PROMOTION]
    for parent, child in (("gov_contacts", "gov_contact_positions"),
                          ("agency_brain_items", "gov_intelligence_evidence"),
                          ("gov_needs", "gov_need_requirements"),
                          ("gov_intelligence_assertions", "gov_requirement_revisions"),
                          ("gov_intelligence_evidence", "gov_assertion_evidence")):
        assert promoted.index(parent) < promoted.index(child), f"{parent} must precede {child}"

    print("selfcheck ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(selfcheck() if "--selfcheck" in sys.argv else main(sys.argv[1:]))
