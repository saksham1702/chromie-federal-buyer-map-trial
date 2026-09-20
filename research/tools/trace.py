#!/usr/bin/env python3
"""Follow a Navy requirement across forecasts, offices, notices and awards, from one data set.

    python research/tools/trace.py status  [--dsn DSN] [--office pmw:170] [--through 26]
    python research/tools/trace.py need    <PID | record key>            [--dsn DSN]
    python research/tools/trace.py notice  <SAM notice id | solicitation number>
    python research/tools/trace.py award   <PIID>
    python research/tools/trace.py --selfcheck

The three questions the reviewer asked for, answered from the same rows:

  status  - which forecast lines whose solicitation window has arrived show a public
            notice or an award, which show only activity on the incumbent, and which
            show nothing (with the reason a trail may be missing).
  need    - one requirement followed across releases: every revision with its date,
            the office each release named, the incumbent contract with its ceiling and
            obligations kept apart from the estimate, the notices and awards tied to it.
  notice  - an active notice traced to the office it names, that office's ancestry and
            history from the organization memory, and the forecast lines that may be
            the same requirement, each with the basis for the match.
  award   - a contract read back to the forecast lines that cite it and forward to the
            notices and awards that followed.

Offline. Reads the agency-intelligence tables through `psql`, the LRAE datapacks and the
saved SAM.gov, FPDS and USAspending responses listed in research/documents_manifest.jsonl.
It never fetches: a lookup that was not collected prints as "not collected" with the
command that would collect it. An LRAE value range is an estimate, a contract's
base-and-all-options is a ceiling, and FPDS/USAspending obligations are money placed;
the three print in separate columns and are never added together.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import MANIFEST, ROOT  # noqa: E402
from lrae_package import alias_map, contract_tokens, norm_code, norm_title  # noqa: E402

DEFAULT_DSN = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
RESEARCH = ROOT / "research"
PACKS = sorted(p for p in (ROOT / "datapack").glob("lrae_navwar_*") if p.is_dir())
NOTICES = ROOT / "data" / "raw" / "sam_notices"
SOL_RE = re.compile(r"N\d{5}-?\d{2}-?R-?[A-Z]?-?\d{3,4}(?![0-9])")
# SAM.gov notice type codes as the site API returns them.
NOTICE_TYPE = {"p": "presolicitation", "o": "solicitation", "k": "combined synopsis/solicitation", "r": "sources sought",
               "s": "special notice", "a": "award notice", "u": "justification (J&A)", "i": "intent to bundle", "g": "sale of surplus"}
STOP = {"the", "and", "for", "of", "to", "a", "in", "on", "with", "new", "follow", "contract", "contracts", "services", "service",
        "support", "system", "systems", "program", "navy", "navwar", "c", "fy24", "fy25", "fy26", "fy27", "rfp", "order", "task",
        # procurement vocabulary that any two lines may share without being the same buy
        "production", "development", "procurement", "spares", "terminals", "terminal", "integration", "modernization",
        "engineering", "lot", "buy", "award", "fund", "base", "idiq", "mac", "recompete", "compete", "upgrade", "sustainment",
        "logistics", "integrated", "professional", "technical", "management", "office", "solutions", "increase", "ceiling",
        "version", "receive", "multi", "multiple", "single", "iss", "ess", "pss", "hw", "sw", "software", "hardware", "year", "option"}


# ---------------------------------------------------------------- saved inputs

def manifest() -> list[dict]:
    return [json.loads(l) for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]


def saved(rows: list[dict], predicate) -> dict | None:
    hits = [r for r in rows if r.get("status") == 200 and r.get("path") and predicate(r.get("url", "")) and (ROOT / r["path"]).exists()]
    return hits[-1] if hits else None


def load_json(row: dict | None):
    return json.loads((ROOT / row["path"]).read_text(encoding="utf-8")) if row else None


def compact(token: str) -> str:
    return re.sub(r"[\s-]", "", (token or "").upper())


def fpds_actions(body: str) -> list[dict]:
    """Every contract action in an FPDS ATOM page, with the award and IDV ids read from their nested blocks."""
    out = []
    for entry in re.findall(r"<entry>(.*?)</entry>", body, re.S):
        def tag(name: str, block: str = entry) -> str:
            m = re.search(rf"<ns1:{name}(?:\s[^>]*)?>(.*?)</ns1:{name}>", block, re.S)
            return re.sub(r"&amp;", "&", m.group(1).strip()) if m else ""
        award_id = re.search(r"<ns1:awardID>(.*?)</ns1:awardID>", entry, re.S)
        block = award_id.group(1) if award_id else entry
        piid = re.search(r"<ns1:awardContractID>.*?<ns1:PIID>(.*?)</ns1:PIID>", block, re.S)
        idv = re.search(r"<ns1:referencedIDVID>.*?<ns1:PIID>(.*?)</ns1:PIID>", block, re.S)
        out.append({"piid": piid.group(1) if piid else tag("PIID"), "idv": idv.group(1) if idv else "",
                    "mod": tag("modNumber"), "signed": tag("signedDate")[:10], "obligated": tag("obligatedAmount"),
                    "base_and_all_options": tag("baseAndAllOptionsValue"), "solicitation": tag("solicitationID"),
                    "vendor": tag("vendorName"), "contracting_office": tag("contractingOfficeID"),
                    "description": tag("descriptionOfContractRequirement")})
    return out


def usaspending(rows: list[dict], piid: str) -> dict | None:
    row = saved(rows, lambda u: "usaspending" in u and (f"/CONT_AWD_{piid}_" in u or f"/CONT_IDV_{piid}_" in u))
    j = load_json(row)
    if not j:
        return None
    pop = j.get("period_of_performance") or {}
    ltx = j.get("latest_transaction_contract_data") or {}
    return {"piid": j.get("piid"), "type": j.get("type_description"), "description": (j.get("description") or ""),
            "ceiling": j.get("base_and_all_options"), "obligated": j.get("total_obligation"), "signed": j.get("date_signed"),
            "pop_start": pop.get("start_date"), "pop_end": pop.get("end_date"), "last_modified": str(pop.get("last_modified_date") or "")[:10],
            "recipient": (j.get("recipient") or {}).get("recipient_name"), "solicitation": ltx.get("solicitation_identifier"),
            "competed": ltx.get("extent_competed_description"), "offers": ltx.get("number_of_offers_received"),
            "parent": (j.get("parent_award") or {}).get("piid"), "awarding_office": (j.get("awarding_agency") or {}).get("office_agency_name"),
            "url": row["url"], "retrieved": row["retrieved_at"][:10], "sha": row["sha256"][:12]}


def fpds_by_piid(rows: list[dict], piid: str) -> tuple[list[dict], dict | None]:
    row = saved(rows, lambda u: f"q=PIID:{piid}&" in u)
    return (fpds_actions((ROOT / row["path"]).read_text(encoding="utf-8", errors="replace")) if row else []), row


def fpds_by_solicitation(rows: list[dict], sol: str) -> tuple[list[dict], dict | None]:
    row = saved(rows, lambda u: f"SOLICITATION_ID:{compact(sol)}" in u)
    return (fpds_actions((ROOT / row["path"]).read_text(encoding="utf-8", errors="replace")) if row else []), row


def sgs_hits(rows: list[dict]) -> dict[str, dict]:
    """Every SAM.gov search hit ever saved, by notice id, with the query that found it."""
    hits: dict[str, dict] = {}
    for r in rows:
        if r.get("status") != 200 or "sgs/v1/search" not in r.get("url", "") or not r.get("path") or not (ROOT / r["path"]).exists():
            continue
        try:
            body = json.loads((ROOT / r["path"]).read_text(encoding="utf-8"))
        except ValueError:
            continue
        for h in (body.get("_embedded") or {}).get("results") or []:
            kind = h.get("type")
            hits.setdefault(h["_id"], {"id": h["_id"], "title": h.get("title") or "", "type": kind.get("value") if isinstance(kind, dict) else kind,
                                       "posted": str(h.get("publishDate") or "")[:10], "active": h.get("isActive"),
                                       "solicitation": h.get("solicitationNumber") or "", "query_url": r["url"], "sha": r["sha256"][:12]})
    # Notices harvested in full (research/tools/sam_notices.py) count too, whether or not a search found them.
    for path in sorted(NOTICES.glob("*.json")) if NOTICES.exists() else []:
        if path.name.endswith(".resources.json") or path.stem in hits:
            continue
        d = notice_detail(path.stem)
        if d and d["title"]:
            hits[path.stem] = {"id": path.stem, "title": d["title"], "type": d["type"].title() if d["type"] in NOTICE_TYPE.values() else d["type"],
                               "posted": d["posted"], "active": None, "solicitation": d["solicitation"], "query_url": d["path"], "sha": ""}
    return hits


def notice_detail(notice_id: str) -> dict | None:
    path = NOTICES / f"{notice_id}.json"
    if not path.exists():
        return None
    try:
        d = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except ValueError:
        return None  # a saved body that is not the notice (an error page, an attachment listing)
    if not isinstance(d, dict):
        return None
    o = d.get("data2") or d.get("data") or d
    if not isinstance(o, dict):
        return None
    text = ""
    for candidate in re.findall(r'"((?:[^"\\]|\\.){300,})"', json.dumps(d)):
        text = max(text, candidate.encode().decode("unicode_escape", "ignore"), key=len)
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()
    return {"id": notice_id, "title": o.get("title") or "", "solicitation": o.get("solicitationNumber") or "",
            "type": NOTICE_TYPE.get(str(o.get("type") or ""), str(o.get("type") or "")), "posted": str(d.get("postedDate") or o.get("postedDate") or "")[:10],
            "award": o.get("award") or {}, "text": text, "path": str(path.relative_to(ROOT))}


# ---------------------------------------------------------------- datapacks

def pack_rows(pack: Path, name: str) -> list[dict]:
    path = pack / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def lrae_lines() -> list[dict]:
    """Every included LRAE row across the saved releases, with its decision and joins."""
    lines = []
    for pack in PACKS:
        joins = defaultdict(list)
        for j in pack_rows(pack, "joins.csv"):
            joins[j["row_number"]].append(j)
        decision = {c["row_number"]: c for c in pack_rows(pack, "rows_classified.csv")}
        source = json.loads((pack / "SOURCE.json").read_text(encoding="utf-8")) if (pack / "SOURCE.json").exists() else {}
        for r in pack_rows(pack, "rows_raw.csv"):
            c = decision.get(r["row_number"])
            if not c or c["include_decision"] != "included":
                continue
            lines.append({**r, "release": pack.name, "release_date": source.get("release_date", ""), "sha": source.get("sha256", "")[:12],
                          "record_key": c["record_key"], "office_id": c["office_id"], "joins": joins.get(r["row_number"], [])})
    return lines


def fiscal_year(text: str) -> int | None:
    m = re.search(r"(\d{2})\b", text or "")
    return 2000 + int(m.group(1)) if m else None


def window(fy: str, quarter: str) -> str:
    return f"{fy} {quarter}".strip() if (fy or quarter) and "TBD" not in f"{fy}{quarter}" else "TBD"


# ---------------------------------------------------------------- database

def query(dsn: str, sql: str) -> list[dict]:
    out = subprocess.run(["psql", dsn, "-At", "-c", sql], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"psql failed: {out.stderr.strip()}")
    return json.loads(out.stdout.strip() or "null") or []


def lit(value) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def ancestry(dsn: str, org_id: str) -> list[dict]:
    return query(dsn, f"""
        with recursive up as (
          select o.id, o.name, o.acronym, o.parent_organization_id, 1 as depth from public.gov_organizations o where o.id = {lit(org_id)}
          union all
          select p.id, p.name, p.acronym, p.parent_organization_id, up.depth + 1 from up join public.gov_organizations p on p.id = up.parent_organization_id)
        select json_agg(row_to_json(up) order by depth) from up""")


def org_history(dsn: str, org_id: str) -> list[dict]:
    return query(dsn, f"""
        select json_agg(row_to_json(t)) from (
          select r.source_ref, s.name as source_name, r.relationship_type, t.name as target_name, r.valid_from, r.valid_to, r.confidence
            from public.gov_organization_relationships r
            join public.gov_organizations s on s.id = r.source_organization_id
            join public.gov_organizations t on t.id = r.target_organization_id
           where r.source_organization_id = {lit(org_id)} or r.target_organization_id = {lit(org_id)}
           order by r.valid_from nulls first, r.source_ref) t""")


def find_org(dsn: str, needle: str) -> list[dict]:
    return query(dsn, f"""
        select json_agg(row_to_json(o)) from (
          select id, name, acronym, org_type, source_ref, parent_organization_id, valid_from, valid_to from public.gov_organizations
           where source_ref = {lit(needle)} or acronym = {lit(needle)} or name ilike {lit('%' + needle + '%')}
              or {lit(needle)} = any(aliases) order by name) o""")


def need_record(dsn: str, key: str) -> dict | None:
    needs = query(dsn, f"select json_agg(row_to_json(n)) from (select id, source_key, title, description, lifecycle from public.gov_needs where source_key = {lit(key)}) n")
    if not needs:
        return None
    need = needs[0]
    need["revisions"] = query(dsn, f"""
        select json_agg(row_to_json(t) order by observed_at) from (
          select a.observed_at::date as observed_at, a.source_key, a.basis, a.rationale, rv.statement, rv.expected_from, rv.expected_to,
                 a.supersedes_id is not null as supersedes_prior,
                 not exists (select 1 from public.gov_intelligence_assertions s where s.supersedes_id = a.id) as live
            from public.gov_intelligence_assertions a
            join public.gov_requirement_revisions rv on rv.assertion_id = a.id
            join public.gov_need_requirements rq on rq.id = rv.requirement_id
           where rq.need_id = {lit(need['id'])}) t""")
    need["funding"] = query(dsn, f"""
        select json_agg(row_to_json(t) order by observed_at) from (
          select a.observed_at::date as observed_at, f.measure, f.amount_low, f.amount_high, f.fiscal_year, f.period_start, f.period_end, f.scope_description,
                 not exists (select 1 from public.gov_intelligence_assertions s where s.supersedes_id = a.id) as live
            from public.gov_funding_observations f join public.gov_intelligence_assertions a on a.id = f.assertion_id
           where f.need_id = {lit(need['id'])}) t""")
    need["offices"] = query(dsn, f"""
        select json_agg(row_to_json(t) order by observed_at, role) from (
          select a.observed_at::date as observed_at, no.role, o.id as org_id, o.name, o.acronym,
                 not exists (select 1 from public.gov_intelligence_assertions s where s.supersedes_id = a.id) as live
            from public.gov_need_organizations no join public.gov_intelligence_assertions a on a.id = no.assertion_id
            join public.gov_organizations o on o.id = no.organization_id
           where no.need_id = {lit(need['id'])}) t""")
    need["evidence"] = query(dsn, f"""
        select json_agg(row_to_json(t)) from (
          select distinct e.excerpt, i.source
            from public.gov_assertion_evidence ae join public.gov_intelligence_evidence e on e.id = ae.evidence_id
            left join public.agency_brain_items i on i.id = e.brain_item_id
            join public.gov_intelligence_assertions a on a.id = ae.assertion_id
            join public.gov_requirement_revisions rv on rv.assertion_id = a.id
            join public.gov_need_requirements rq on rq.id = rv.requirement_id
           where rq.need_id = {lit(need['id'])}) t""")
    return need


def needs_for_office(dsn: str, org_id: str) -> list[dict]:
    return query(dsn, f"""
        select json_agg(row_to_json(t) order by title) from (
          select distinct n.id, n.source_key, n.title from public.gov_needs n
            join public.gov_need_organizations no on no.need_id = n.id and no.role = 'originating_requirement_owner'
           where no.organization_id = {lit(org_id)}) t""")


# ---------------------------------------------------------------- readings

def money_block(estimates: list[str], ceilings: list[tuple[str, object]], obligations: list[tuple[str, object]]) -> list[str]:
    """Three kinds of money, three lines, never one number."""
    fmt = lambda v: f"${float(v):,.0f}" if v not in (None, "", 0, "0", 0.0) else ("$0" if v in (0, "0", 0.0) else "not stated")  # noqa: E731
    return [f"  estimate (LRAE anticipated total value, as stated): {'; '.join(estimates) or 'none'}",
            f"  ceiling (base and all options, USAspending/FPDS):  {'; '.join(f'{p} {fmt(v)}' for p, v in ceilings) or 'none collected'}",
            f"  obligated to date (USAspending total_obligation):   {'; '.join(f'{p} {fmt(v)}' for p, v in obligations) or 'none collected'}"]


def reading(sol_window: str, notices: list[dict], awards: list[dict], incumbent_last: str, instrument: str, today: date) -> str:
    """One deterministic sentence on whether a forecast line has been solicited or awarded."""
    if awards:
        first = min(a["signed"] for a in awards if a.get("signed")) if any(a.get("signed") for a in awards) else "date unstated"
        return f"awarded: {len(awards)} action(s) under the line's solicitation, first signed {first}"
    kinds = {n.get("type", "").lower() for n in notices}
    latest = max((n.get("posted") or "" for n in notices), default="")
    if kinds & {"solicitation", "presolicitation", "combined synopsis/solicitation"}:
        return f"solicited: {', '.join(sorted(kinds & {'solicitation', 'presolicitation', 'combined synopsis/solicitation'}))} posted {latest}"
    if kinds & {"sources sought", "special notice"}:
        return f"market research only: {', '.join(sorted(kinds))} posted {latest}"
    if kinds & {"award notice", "justification (j&a)", "justification"}:
        return f"incumbent action noticed: {', '.join(sorted(kinds))} posted {latest}; no follow-on solicitation found"
    due = fiscal_year(sol_window)
    if due and date(due - 1, 10, 1) > today:
        return "not yet due"
    tail = "; SeaPort/GSA order competitions are not posted on SAM.gov" if "order" in (instrument or "").lower() else ""
    tail += f"; incumbent last acted {incumbent_last}" if incumbent_last else ""
    return "no public notice found" + tail


def notice_summaries(line: dict, hits: dict[str, dict]) -> list[dict]:
    """Notices the datapack joined to the line explicitly (the PID or an incumbent contract number in the text)."""
    out = []
    for j in line["joins"]:
        if j["join_type"] == "notice" and j["target_id"].startswith("sam:"):
            h = hits.get(j["target_id"][4:])
            if h:
                out.append({**h, "method": j["method"], "key": j["key_used"]})
    return out


def title_tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 2 and w not in STOP}


def distinctive_tokens(text: str) -> set[str]:
    """Program names and codes: words the source wrote in capitals or with a digit (NTCDL, MIDS-LVT, SF2, GPNTS)."""
    out = set()
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9/-]*", text or ""):
        for part in re.split(r"[/-]", raw):
            # A bare number (a lot, a DO, a year) names nothing; a code needs a letter.
            if len(part) >= 3 and re.search(r"[A-Za-z]", part) and (part.isupper() or re.search(r"\d", part)) and part.lower() not in STOP:
                out.add(part.lower())
    return out


SOLICITATION_STAGE = ("Presolicitation", "Solicitation", "Combined Synopsis/Solicitation")


def match_context() -> dict:
    """What candidate matching needs once: how rare each program token is across the latest release, and who is whose parent."""
    latest = PACKS[-1].name if PACKS else ""
    rarity: dict[str, int] = defaultdict(int)
    for l in lrae_lines():
        if l["release"] == latest:
            for t in distinctive_tokens(l["requirement_title"]):
                rarity[t] += 1
    seed = json.loads((RESEARCH / "organization_seed.json").read_text(encoding="utf-8"))
    parents = defaultdict(set)
    for r in seed["relationships"]:
        if r["type"] == "child_of" and r["review_status"] != "retracted":
            parents[r["from"]].add(r["to"])
    return {"rarity": rarity, "parents": parents, "offices_of": {}}


def notice_offices(notice_id: str, ctx: dict) -> set[str]:
    """Program offices a harvested notice names as current (not 'formerly'); empty when the detail is not saved."""
    if notice_id not in ctx["offices_of"]:
        d = notice_detail(notice_id)
        ctx["offices_of"][notice_id] = {o["office"] for o in resolve_offices(d["text"]) if not o["former"] and o["office"].startswith(("pmw:", "peo:"))} if d else set()
    return ctx["offices_of"][notice_id]


def related_office(line_office: str, notice_office: str, parents: dict) -> str:
    if line_office == notice_office:
        return "same office"
    if notice_office in parents.get(line_office, ()):
        return "notice names the line's parent"
    if line_office in parents.get(notice_office, ()):
        return "line filed under the notice office's parent code"
    return ""


def candidate_notices(line: dict, hits: dict[str, dict], ctx: dict) -> list[dict]:
    """Saved solicitation-stage hits that may be this line: candidates a reviewer accepts or rejects, never matches.

    Two titles are related when they share a program name or code (a capitalised word or one
    with a digit) that few lines carry, or two such tokens, or three words overall; generic
    procurement words never count. When the notice text is saved and names a current office
    that is neither the line's office nor its parent or child, the hit is dropped, and the
    office comparison travels with every candidate that survives.
    """
    words, codes = title_tokens(line["requirement_title"]), distinctive_tokens(line["requirement_title"])
    # A notice posted more than two fiscal years before the line's own window solicited something else.
    due = fiscal_year(line.get("solicitation_fy", "")) or fiscal_year(line.get("award_fy", ""))
    earliest = f"{due - 3}-10-01" if due else ""
    out = []
    for h in hits.values():
        if h["type"] not in SOLICITATION_STAGE or (earliest and h["posted"] and h["posted"] < earliest):
            continue
        shared = sorted(words & title_tokens(h["title"]))
        shared_codes = sorted(codes & distinctive_tokens(h["title"]))
        rare = [t for t in shared_codes if ctx["rarity"].get(t, 0) <= 3]
        if not (rare or len(shared_codes) >= 2 or len(shared) >= 3):
            continue
        offices = notice_offices(h["id"], ctx)
        relation = ""
        if offices:
            relations = [related_office(line["office_id"], o, ctx["parents"]) for o in offices]
            relation = next((r for r in relations if r), "")
            if not relation:
                continue  # the notice names a current office unrelated to this line
        basis = "shared program tokens " + ", ".join(shared_codes or shared[:4])
        if relation:
            basis += f"; {relation}"
        elif notice_detail(h["id"]) is not None:
            basis += "; notice text names no office the memory knows"
        else:
            basis += "; notice office not read (detail not saved)"
        out.append({**h, "method": "candidate", "key": basis})
    return sorted(out, key=lambda h: h["posted"])


def incumbent_recency(rows: list[dict], line: dict) -> tuple[str, str]:
    """Latest action on the incumbent contract(s): USAspending's last-modified date when saved, else the first FPDS page."""
    last, source = "", ""
    for token in contract_tokens(line["existing_contract_number"]):
        u = usaspending(rows, token)
        if u and u["last_modified"]:
            last, source = max(last, u["last_modified"]), "usaspending"
            continue
        actions, _ = fpds_by_piid(rows, token)
        if actions:
            last = max([last] + [a["signed"] for a in actions if a["signed"]])
            source = source or "fpds page 1"
    return last, source


def line_status(line: dict, rows: list[dict], hits: dict[str, dict], examples: dict[str, dict], today: date, ctx: dict) -> dict:
    notices = notice_summaries(line, hits)
    known = {n["id"] for n in notices}
    candidates = [c for c in candidate_notices(line, hits, ctx) if c["id"] not in known]
    sols = [compact(m) for m in SOL_RE.findall(line["requirement_title"].replace(" ", ""))]
    for n in notices:
        if n["solicitation"] and compact(n["solicitation"]) not in sols and n["type"] in SOLICITATION_STAGE:
            sols.append(compact(n["solicitation"]))
    candidate_sols = [compact(c["solicitation"]) for c in candidates if c["solicitation"] and compact(c["solicitation"]) not in sols]
    awards, candidate_awards = [], []
    for sol in sols:
        actions, _ = fpds_by_solicitation(rows, sol)
        awards += [a for a in actions if a["mod"] in ("0", "")]
    for sol in dict.fromkeys(candidate_sols):
        actions, _ = fpds_by_solicitation(rows, sol)
        candidate_awards += [{**a, "via": sol} for a in actions if a["mod"] in ("0", "")]
    incumbent_last, recency_source = incumbent_recency(rows, line)
    example = examples.get(line["pid"])
    sol_window = window(line["solicitation_fy"], line["solicitation_quarter"])
    verdict = reading(sol_window, notices, awards, incumbent_last, line["procurement_instrument"], today)
    if verdict.startswith(("no public notice", "not yet due", "incumbent action", "market research")) and candidates:
        c = candidates[-1]
        prior = verdict if verdict.startswith(("incumbent action", "market research")) else ""
        verdict = f"candidate: {c['type'].lower()} posted {c['posted']} ({c['key']})"
        if candidate_awards:
            first = min(a["signed"] for a in candidate_awards)
            verdict += f"; {len(candidate_awards)} award action(s) under that solicitation, first signed {first}"
        verdict += "; a reviewer decides whether it is this line" + (f"; meanwhile {prior}" if prior else "")
    return {"pid": line["pid"] or line["record_key"], "title": line["requirement_title"], "office": line["office_id"],
            "sol": sol_window, "award": window(line["award_fy"], line["award_quarter"]),
            "value": line["anticipated_total_value"], "instrument": line["procurement_instrument"],
            "notices": notices, "candidates": candidates, "awards": awards, "candidate_awards": candidate_awards,
            "incumbent_last": incumbent_last + ("*" if recency_source == "fpds page 1" else ""),
            "linked_award": f"{example['identifier']} ({example['id']}, reviewed attribution)" if example else "",
            "reading": verdict}


def paired_rows(key: str) -> dict[tuple[str, str], str]:
    """(release, row) -> match basis, for rows the release diffs paired with this key (confirmed or candidate)."""
    out: dict[tuple[str, str], str] = {}
    for pack in PACKS:
        for path in sorted(pack.glob("diff_*.csv")):
            m = re.match(r"diff_(lrae_navwar_[\d-]+)_(lrae_navwar_[\d-]+)\.csv", path.name)
            if not m:
                continue
            older, newer = m.groups()
            for ch in pack_rows(pack, path.name):
                if ch["key"] == key and ch["change"] in ("unchanged", "changed"):
                    basis = f"{ch['key_method']} ({ch['confidence']})"
                    if ch["old_row"]:
                        out[(older, ch["old_row"])] = basis
                    if ch["new_row"]:
                        out[(newer, ch["new_row"])] = basis
    return out


def successors(dsn: str, org_id: str) -> list[str]:
    """Successor organizations documented for the office or any ancestor (a reorganization is a successor edge, not a parent)."""
    return query(dsn, f"""
        with recursive up as (
          select o.id, o.parent_organization_id from public.gov_organizations o where o.id = {lit(org_id)}
          union all
          select p.id, p.parent_organization_id from up join public.gov_organizations p on p.id = up.parent_organization_id)
        select json_agg(distinct s.name || ' (from ' || coalesce(r.valid_from::text, 'an undated release') || ')')
          from up join public.gov_organization_relationships r on r.target_organization_id = up.id and r.relationship_type = 'successor_to'
          join public.gov_organizations s on s.id = r.source_organization_id""")


def print_office(dsn: str, org_id: str, indent: str = "  ") -> None:
    print(f"{indent}ancestry today: {' -> '.join(a['name'] for a in ancestry(dsn, org_id))}")
    succ = successors(dsn, org_id)
    if succ:
        print(f"{indent}succeeded by: {'; '.join(succ)}")
    for h in org_history(dsn, org_id):
        print(f"{indent}history: {h['source_name']} {h['relationship_type']} {h['target_name']} "
              f"[{h['valid_from'] or 'start unstated'} .. {h['valid_to'] or 'open'}] ({h['source_ref']})")


def attribution_examples() -> dict[str, dict]:
    rows = json.loads((RESEARCH / "attribution_examples.json").read_text(encoding="utf-8"))
    return {(x.get("related") or {}).get("forecast_pid", ""): x for x in rows if (x.get("related") or {}).get("forecast_pid")}


# ---------------------------------------------------------------- commands

def cmd_status(args) -> int:
    rows, hits, examples, today, ctx = manifest(), sgs_hits(manifest()), attribution_examples(), date.today(), match_context()
    latest = PACKS[-1].name
    lines = [l for l in lrae_lines() if l["release"] == latest]
    if args.office:
        lines = [l for l in lines if l["office_id"] == args.office]
    through = 2000 + int(args.through)
    due = [l for l in lines if (fiscal_year(l["solicitation_fy"]) or 9999) <= through]
    print(f"# Forecast lines in {latest} with a solicitation window through FY{args.through}: {len(due)} of {len(lines)} included lines")
    print(f"# Read against saved SAM.gov searches, FPDS lookups and attribution examples as of {today}. Nothing here is fetched live.")
    print("# Notice column: explicit joins first (PID or incumbent contract number in the notice text), then candidates marked ~: a shared program name or code that few lines carry, with the notice's own office compared to the line's. A candidate is a reviewer's call.")
    print("# Incumbent column: USAspending last-modified date; a * means only the first FPDS page was saved and later actions may exist.")
    print()
    print("| PID | title | office | sol | award | value as stated | notice | incumbent last action | award found | reading |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    counts = defaultdict(int)
    for l in sorted(due, key=lambda l: (l["office_id"], l["solicitation_fy"], l["solicitation_quarter"], l["requirement_title"])):
        s = line_status(l, rows, hits, examples, today, ctx)
        counts[s["reading"].split(":")[0].split(";")[0]] += 1
        notice = "; ".join(f"{n['type']} {n['posted']} ({n['solicitation'] or n['id'][:8]})" for n in s["notices"][:2])
        notice = "; ".join(x for x in [notice] + [f"~{c['type']} {c['posted']} ({c['solicitation'] or c['id'][:8]})" for c in s["candidates"][-2:]] if x) or "-"
        awards = "; ".join(f"{a['piid']} {a['signed']}" for a in s["awards"][:3]) or \
            "; ".join(f"~{a['piid']} {a['signed']}" for a in s["candidate_awards"][:3]) or (s["linked_award"] or "-")
        print(f"| {s['pid']} | {s['title'][:48]} | {s['office']} | {s['sol']} | {s['award']} | {s['value']} | {notice} | {s['incumbent_last'] or '-'} | {awards} | {s['reading'][:220]} |")
    print()
    print("Readings: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))
    return 0


def print_need(dsn: str, key: str) -> int:
    rows, hits, examples, ctx = manifest(), sgs_hits(manifest()), attribution_examples(), match_context()
    need = need_record(dsn, key)
    pairs = paired_rows(key)
    lines = [l for l in lrae_lines() if l["record_key"] == key or l["pid"] == key or (l["release"], l["row_number"]) in pairs]
    if not need and not lines:
        print(f"nothing loaded or packaged under {key!r}; try the PID or a record key like row:lrae_navwar_2024-06:406")
        return 1
    title = need["title"] if need else lines[-1]["requirement_title"]
    print(f"# {key} - {title}")
    if need:
        live = [o for o in need["offices"] if o["live"] and o["role"] == "originating_requirement_owner"]
        for o in live:
            print(f"Office (live claim, {o['observed_at']}): {o['name']}")
            print_office(dsn, o["org_id"])
        if len(live) > 1:
            print("  NOTE: more than one live owner claim; the releases disagree and both are kept")
    print("\n## Forecast history (one row per release that carried the line, with how the row was tied to this key)")
    print("| release | row | matched by | sol | award window | value as stated | office named | method | instrument |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for l in lines:
        basis = "PID on the row" if l["pid"] == key else ("record key" if l["record_key"] == key else pairs.get((l["release"], l["row_number"]), ""))
        print(f"| {l['release']} ({l['release_date']}) | {l['sheet']}!row {l['row_number']} (sha {l['sha']}) | {basis} | {window(l['solicitation_fy'], l['solicitation_quarter'])} | "
              f"{window(l['award_fy'], l['award_quarter'])} | {l['anticipated_total_value']} | {l['office_code_string'].split(' - ')[0]} -> {l['office_id']} | {l['procurement_method'] or '-'} | {l['procurement_instrument'] or '-'} |")
    if any("candidate" in pairs.get((l["release"], l["row_number"]), "") for l in lines):
        print("\nA row matched as a candidate is a reviewer's call, not the tool's; its field changes are reported against the pair in the release diff.")
    if need and need["revisions"]:
        print("\nLoaded revisions (gov_requirement_revisions): " + "; ".join(
            f"{r['observed_at']}: award {r['expected_from'] or '?'}..{r['expected_to'] or '?'}{' (live)' if r['live'] else ''}" for r in need["revisions"]))
    estimates = [f"{l['release_date']}: {l['anticipated_total_value'] or 'no range'}" for l in lines]
    ceilings, obligations = [], []
    print("\n## Incumbent and related contracts (saved USAspending / FPDS)")
    tokens = []
    for l in lines:
        for t in contract_tokens(l["existing_contract_number"]):
            if t not in tokens:
                tokens.append(t)
    for t in tokens:
        u = usaspending(rows, t)
        actions, atom = fpds_by_piid(rows, t)
        if u:
            print(f"- {t} ({u['type']}, {u['recipient']}): signed {u['signed']}, PoP {u['pop_start']} -> {u['pop_end']}, last modified {u['last_modified']}; "
                  f"solicitation {u['solicitation'] or 'unstated'}; {u['competed'] or ''}, offers {u['offers']}. USAspending {u['retrieved']} sha {u['sha']}")
            ceilings.append((t, u["ceiling"])); obligations.append((t, u["obligated"]))
        else:
            print(f"- {t}: USAspending not collected (python research/tools/fetch.py 'https://api.usaspending.gov/api/v2/awards/CONT_AWD_{t}_9700_-NONE-_-NONE-/')")
        if actions:
            recent = sorted(actions, key=lambda a: a["signed"])[-3:]
            print(f"  FPDS: first page of actions saved ({len(actions)}; later pages were not collected, so USAspending's last-modified date is the recency to trust); "
                  + "; ".join(f"{a['mod'] or 'base'} {a['signed']} obligated ${float(a['obligated'] or 0):,.0f}" for a in recent))
        elif atom is None:
            print(f"  FPDS PIID lookup not collected (python research/tools/lrae_package.py collect)")
    print("\n## Notices (saved SAM.gov searches joined to this line; ~ marks a candidate by shared title words)")
    seen = set()
    sols = set()
    candidate_sols = set()
    for l in lines:
        for n in notice_summaries(l, hits):
            if n["id"] in seen:
                continue
            seen.add(n["id"])
            print(f"- {n['posted']} {n['type']}: {n['title'][:90]} [{n['solicitation'] or 'no number'}] via {n['method']} key {n['key']}; search sha {n['sha']}")
            d = notice_detail(n["id"])
            if d and d["award"]:
                a = d["award"]
                print(f"    award block on the notice: {a.get('number')} on {a.get('date')} for ${float(a.get('amount') or 0):,.0f} to {(a.get('awardee') or {}).get('name')} (a modification, so it sits under the incumbent's ceiling above, not a new award)")
            if n["solicitation"] and n["type"] in SOLICITATION_STAGE:
                sols.add(compact(n["solicitation"]))
    for l in lines:
        for c in candidate_notices(l, hits, ctx):
            if c["id"] in seen:
                continue
            seen.add(c["id"])
            print(f"- ~{c['posted']} {c['type']}: {c['title'][:90]} [{c['solicitation'] or 'no number'}] candidate, {c['key']}")
            if c["solicitation"]:
                candidate_sols.add(compact(c["solicitation"]))
    for l in lines:
        sols.update(compact(m) for m in SOL_RE.findall(l["requirement_title"].replace(" ", "")))
    if not seen:
        print("- none joined; " + ("SeaPort/GSA order competitions are not posted on SAM.gov" if any("order" in l["procurement_instrument"].lower() for l in lines) else "no saved search hit contains the PID or the incumbent contract"))
    sols |= {s for s in candidate_sols if s not in sols}
    print("\n## Awards under solicitations tied to this line (saved FPDS SOLICITATION_ID lookups; ~ = reached through a candidate notice)")
    found = False
    for sol in sorted(sols):
        actions, atom = fpds_by_solicitation(rows, sol)
        base = [a for a in actions if a["mod"] in ("0", "")]
        mark = "~" if sol in candidate_sols else ""
        if base:
            found = True
            for a in base:
                print(f"- {mark}{sol}: {a['piid']} signed {a['signed']} to {a['vendor']}; base and all options ${float(a['base_and_all_options'] or 0):,.0f}; obligated at award ${float(a['obligated'] or 0):,.0f}; {a['description'][:80]}")
                ceilings.append((a["piid"], a["base_and_all_options"])); obligations.append((a["piid"] + " at award", a["obligated"]))
                u = usaspending(rows, a["piid"])
                if u:
                    obligations[-1] = (a["piid"], u["obligated"])
        elif atom is not None:
            print(f"- {sol}: FPDS lookup saved, no award recorded under it")
        else:
            print(f"- {sol}: not collected (python research/tools/fetch.py 'https://www.fpds.gov/ezsearch/FEEDS/ATOM?FEEDNAME=PUBLIC&q=SOLICITATION_ID:{sol}&start=0')")
    if not sols:
        print("- no solicitation number on the line or in its notices")
    pid = lines[-1]["pid"] if lines else key
    if pid in examples:
        x = examples[pid]
        print(f"- reviewed attribution {x['id']}: award {x['identifier']} ({x['evidence_class']}); {x.get('notes', '')[:140]}")
        u = usaspending(rows, x["identifier"])
        if u:
            ceilings.append((x["identifier"], u["ceiling"])); obligations.append((x["identifier"], u["obligated"]))
            print(f"  {x['identifier']}: signed {u['signed']}, PoP {u['pop_start']} -> {u['pop_end']}, {u['recipient']}, solicitation {u['solicitation'] or 'unstated'}")
    if not found and sols:
        pass
    print("\n## Money, kept apart")
    print("\n".join(money_block(estimates, ceilings, obligations)))
    return 0


def cmd_need(args) -> int:
    return print_need(args.dsn, args.key)


def resolve_offices(text: str) -> list[dict]:
    """Offices the notice names, through the organization memory's aliases; the matched wording travels with each."""
    seed = json.loads((RESEARCH / "organization_seed.json").read_text(encoding="utf-8"))
    squeeze = lambda s: re.sub(r"\s+", " ", s).lower().strip()  # noqa: E731
    flat = squeeze(text)
    # Notices write an acronym in brackets after a name; aliases sometimes do too. Compare
    # both with every bracketed part removed, so "(MIDS) International Program Office" and
    # "MIDS International Program Office (IPO)" meet on the words that stay.
    unbracket = lambda s: squeeze(re.sub(r"\s*\([^)]*\)", " ", s))  # noqa: E731
    flat_open = unbracket(text)
    out = []
    for node in seed["nodes"]:
        if node["type"] == "person":
            continue
        texts = [node["name"]] + [a["text"] if isinstance(a, dict) else a for a in node.get("aliases") or []] + list((node.get("codes") or {}).values())
        for t in texts:
            probe = squeeze(re.sub(r"\s*\(.*?\)\s*$", "", t))
            probe_open = unbracket(t)
            if len(probe) < 4:
                continue
            if probe in flat:
                start, hay = flat.find(probe), flat
            elif len(probe_open) >= 4 and probe_open in flat_open:
                start, hay, probe = flat_open.find(probe_open), flat_open, probe_open
            else:
                continue
            context = hay[max(0, start - 60): start + len(probe) + 60]
            former = bool(re.search(r"(formerly|previously)[^.]{0,80}" + re.escape(probe[:30]), hay))
            out.append({"office": node["id"], "name": node["name"], "matched": t, "former": former, "context": context})
            break
    return out


def cmd_notice(args) -> int:
    rows, hits, ctx = manifest(), sgs_hits(manifest()), match_context()
    detail = notice_detail(args.key)
    if detail is None:
        candidates = [h for h in hits.values() if compact(h["solicitation"]) == compact(args.key) or h["id"].startswith(args.key)]
        if not candidates:
            print(f"no saved notice or search hit for {args.key!r}; collect it with: python research/tools/sam_notices.py {args.key}")
            return 1
        for h in sorted(candidates, key=lambda h: h["posted"]):
            print(f"- {h['posted']} {h['type']}: {h['title'][:90]} [{h['solicitation']}] id {h['id']} active={h['active']}")
        print("\nDetail not saved for these; harvest one with: python research/tools/sam_notices.py <id>")
        return 0
    print(f"# {detail['title']}")
    print(f"{detail['type']} posted {detail['posted']}; solicitation {detail['solicitation'] or 'none'}; notice {detail['id']}; saved {detail['path']}")
    if detail["award"]:
        a = detail["award"]
        print(f"Award block: {a.get('number')} on {a.get('date')} for ${float(a.get('amount') or 0):,.0f} to {(a.get('awardee') or {}).get('name')}")
    print("\n## Offices named in the notice text")
    offices = resolve_offices(detail["text"])
    if not offices:
        print("- no organization-memory alias appears in the text; the office is not stated or uses a wording the memory lacks")
    for o in offices:
        print(f"- {o['office']} ({o['name'][:70]}) via alias {o['matched']!r}{' - named as the FORMER designation' if o['former'] else ''}\n    ...{o['context']}...")
    current = [o for o in offices if not o["former"] and o["office"].startswith(("pmw:", "peo:", "cpe:", "pae:"))]
    for o in current or offices:
        found = find_org(args.dsn, o["office"])
        if not found:
            print(f"\n{o['office']} is not in the loaded office table")
            continue
        org = found[0]
        print(f"\n## {org['name']} (loaded as {org['org_type']}, source_ref {org['source_ref']})")
        print_office(args.dsn, org["id"])
        if o["office"].startswith(("pmw:", "peo:")):
            print("\n## Forecast lines owned by this office that may be the same requirement")
            notice_words = title_tokens(detail["title"])
            notice_codes = distinctive_tokens(detail["title"])
            piids = set(contract_tokens(detail["text"]))
            shown = 0
            for n in needs_for_office(args.dsn, org["id"]):
                words, codes = title_tokens(n["title"]), distinctive_tokens(n["title"])
                shared_codes = sorted(codes & notice_codes)
                rare = [t for t in shared_codes if ctx["rarity"].get(t, 0) <= 3]
                shared = shared_codes if (rare or len(shared_codes) >= 2) else sorted(words & notice_words if len(words & notice_words) >= 3 else set())
                lines = [l for l in lrae_lines() if l["record_key"] == n["source_key"] or l["pid"] == n["source_key"]]
                line_piids = {t for l in lines for t in contract_tokens(l["existing_contract_number"])}
                explicit = piids & line_piids
                if explicit or shared:
                    shown += 1
                    latest = lines[-1] if lines else None
                    basis = f"explicit: incumbent contract {', '.join(sorted(explicit))} appears in the notice" if explicit else f"candidate: shared program tokens {', '.join(shared[:6])}"
                    when = f"sol {window(latest['solicitation_fy'], latest['solicitation_quarter'])}, award {window(latest['award_fy'], latest['award_quarter'])}, {latest['anticipated_total_value']}, {latest['release']}" if latest else ""
                    print(f"- {n['source_key']} {n['title'][:70]} ({when}) - {basis}")
            if not shown:
                print("- none: no owned forecast line shares two distinctive words with the notice or cites a contract the notice names")
    print("\n## Forecast lines under OTHER offices that share the notice's words (the office differs, so each is a candidate with a question attached)")
    named = {o["office"] for o in offices}
    others = 0
    notice_codes = distinctive_tokens(detail["title"])
    for l in lrae_lines():
        if l["release"] != PACKS[-1].name or l["office_id"] in named:
            continue
        shared = sorted(distinctive_tokens(l["requirement_title"]) & notice_codes)
        if shared and (len(shared) >= 2 or any(ctx["rarity"].get(t, 0) <= 3 for t in shared)):
            others += 1
            print(f"- {l['pid'] or l['record_key']} {l['requirement_title'][:64]} under {l['office_id']} ({l['office_code_string'].split(' - ')[0]}) - shared words {', '.join(shared[:5])}; "
                  f"sol {window(l['solicitation_fy'], l['solicitation_quarter'])}, award {window(l['award_fy'], l['award_quarter'])}, {l['anticipated_total_value']}")
            if others >= 10:
                break
    if not others:
        print("- none")
    print("\n## Related notices (saved searches sharing the solicitation number or title stem, or a saved notice whose text carries a rare program name from this title)")
    stem = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", detail["title"].lower()))[:45]
    rare = {t for t in distinctive_tokens(detail["title"]) if ctx["rarity"].get(t, 0) <= 3}

    def kin(h: dict) -> bool:
        if detail["solicitation"] and compact(h["solicitation"]) == compact(detail["solicitation"]):
            return True
        if stem and re.sub(r"[^a-z0-9 ]", " ", h["title"].lower()).startswith(stem):
            return True
        # An RFI often carries only a number in its title ("N0003925R4011 - Egypt A2"); the program name is in the body.
        d = notice_detail(h["id"]) if rare else None
        return bool(d and rare & distinctive_tokens(d["title"] + " " + d["text"]))

    related = [h for h in hits.values() if h["id"] != detail["id"] and kin(h)]
    for h in sorted(related, key=lambda h: h["posted"]):
        print(f"- {h['posted']} {h['type']}: {h['title'][:80]} [{h['solicitation'] or 'no number'}] id {h['id'][:12]}")
    if not related:
        print("- none saved")
    if detail["solicitation"]:
        actions, atom = fpds_by_solicitation(rows, detail["solicitation"])
        print("\n## Awards under this solicitation number (saved FPDS)")
        base = [a for a in actions if a["mod"] in ("0", "")]
        for a in base:
            print(f"- {a['piid']} signed {a['signed']} to {a['vendor']}; base and all options ${float(a['base_and_all_options'] or 0):,.0f}; obligated at award ${float(a['obligated'] or 0):,.0f}")
        if not base:
            print("- none recorded" if atom is not None else f"- not collected (python research/tools/fetch.py 'https://www.fpds.gov/ezsearch/FEEDS/ATOM?FEEDNAME=PUBLIC&q=SOLICITATION_ID:{compact(detail['solicitation'])}&start=0')")
    return 0


def cmd_award(args) -> int:
    rows, hits = manifest(), sgs_hits(manifest())
    piid = compact(args.piid)
    u = usaspending(rows, piid)
    actions, atom = fpds_by_piid(rows, piid)
    print(f"# {piid}")
    if u:
        print(f"{u['type']} to {u['recipient']}; {u['description'][:200]}\nsigned {u['signed']}; PoP {u['pop_start']} -> {u['pop_end']}; last modified {u['last_modified']}; "
              f"awarding office {u['awarding_office']}; solicitation {u['solicitation'] or 'unstated'}; {u['competed'] or 'competition unstated'}, offers {u['offers']}; parent {u['parent'] or '-'}\n"
              f"USAspending retrieved {u['retrieved']} (sha {u['sha']})")
    else:
        print(f"USAspending not collected: python research/tools/fetch.py 'https://api.usaspending.gov/api/v2/awards/CONT_AWD_{piid}_9700_-NONE-_-NONE-/'")
    if actions:
        print(f"FPDS actions saved: {len(actions)} on one page; first {min(a['signed'] for a in actions)} last {max(a['signed'] for a in actions)}")
    elif atom is None:
        print("FPDS PIID lookup not collected")
    print("\n## Forecast lines that cite this contract as the incumbent")
    cited = [l for l in lrae_lines() if piid in contract_tokens(l["existing_contract_number"])]
    for l in cited:
        print(f"- {l['release']} row {l['row_number']}: {l['pid'] or l['record_key']} {l['requirement_title'][:70]} | sol {window(l['solicitation_fy'], l['solicitation_quarter'])}, award {window(l['award_fy'], l['award_quarter'])}, {l['anticipated_total_value']}, {l['follow_on_or_new'] or '-'}")
    if not cited:
        print("- none")
    print("\n## Reviewed attributions naming this contract")
    for x in json.loads((RESEARCH / "attribution_examples.json").read_text(encoding="utf-8")):
        if compact(x["identifier"]) == piid:
            print(f"- {x['id']}: {', '.join(x['program_offices'])}; {x['evidence_class']}; {x['owner_summary'][:100]}; related {json.dumps(x.get('related'))[:160]}")
    print("\n## Notices whose saved search hit cites this contract number")
    for h in sorted((h for h in hits.values() if piid in compact(h["title"]) or piid in compact(h["solicitation"])), key=lambda h: h["posted"]):
        print(f"- {h['posted']} {h['type']}: {h['title'][:80]} [{h['solicitation']}] id {h['id'][:12]}")
    print("\n## Predecessor and successor candidates among saved awards (same parent vehicle and recipient, overlapping description)")
    kin = 0
    if u and u["parent"]:
        for row in rows:
            url = row.get("url", "")
            if row.get("status") != 200 or "/awards/CONT_AWD_" not in url or f"_{piid}_" in url:
                continue
            other_piid = url.split("/awards/CONT_AWD_")[1].split("_")[0]
            v = usaspending(rows, other_piid)
            if not v or v["parent"] != u["parent"] or v["recipient"] != u["recipient"]:
                continue
            shared = sorted(title_tokens(v["description"]) & title_tokens(u["description"]))
            if len(shared) >= 2:
                kin += 1
                role = "successor" if (v["signed"] or "") > (u["signed"] or "") else "predecessor"
                print(f"- {role} candidate {v['piid']}: signed {v['signed']}, PoP {v['pop_start']} -> {v['pop_end']}, ceiling ${float(v['ceiling'] or 0):,.0f}, obligated ${float(v['obligated'] or 0):,.0f}; shared words {', '.join(shared[:5])}")
    if not kin:
        print("- none among the saved awards")
    print("\n## Money, kept apart")
    print("\n".join(money_block([f"{l['release_date']}: {l['anticipated_total_value']}" for l in cited],
                                [(piid, u["ceiling"])] if u else [], [(piid, u["obligated"])] if u else [])))
    return 0


# ---------------------------------------------------------------- selfcheck

def selfcheck() -> int:
    atom = """<feed><entry><title>x</title><content><ns1:award><ns1:awardID><ns1:awardContractID><ns1:agencyID>9700</ns1:agencyID>
    <ns1:PIID>N0003926F4006</ns1:PIID><ns1:modNumber>0</ns1:modNumber></ns1:awardContractID><ns1:referencedIDVID><ns1:agencyID>9700</ns1:agencyID>
    <ns1:PIID>N0003925D4006</ns1:PIID></ns1:referencedIDVID></ns1:awardID><ns1:relevantContractDates><ns1:signedDate>2026-06-18 00:00:00</ns1:signedDate></ns1:relevantContractDates>
    <ns1:dollarValues><ns1:obligatedAmount>3083496.00</ns1:obligatedAmount><ns1:baseAndAllOptionsValue>82061676.54</ns1:baseAndAllOptionsValue></ns1:dollarValues>
    <ns1:vendor><ns1:vendorHeader><ns1:vendorName>ROCKWELL COLLINS, INC.</ns1:vendorName></ns1:vendorHeader></ns1:vendor>
    <ns1:contractData><ns1:descriptionOfContractRequirement>MIDS WDL SE&amp;I</ns1:descriptionOfContractRequirement></ns1:contractData></ns1:award></content></entry></feed>"""
    a = fpds_actions(atom)[0]
    assert (a["piid"], a["idv"], a["mod"], a["signed"]) == ("N0003926F4006", "N0003925D4006", "0", "2026-06-18"), a
    assert a["description"] == "MIDS WDL SE&I" and a["base_and_all_options"] == "82061676.54"

    today = date(2026, 9, 20)
    assert reading("FY26 Q2", [], [{"piid": "N1", "signed": "2026-04-13"}], "", "", today).startswith("awarded: 1 action")
    assert reading("FY26 Q2", [{"type": "Presolicitation", "posted": "2026-08-12"}], [], "", "", today).startswith("solicited: presolicitation posted 2026-08-12")
    assert reading("FY26 Q2", [{"type": "Sources Sought", "posted": "2026-02-10"}], [], "", "", today).startswith("market research only")
    assert reading("FY26 Q2", [{"type": "Award Notice", "posted": "2024-11-05"}], [], "", "", today).startswith("incumbent action noticed")
    assert reading("FY27 Q2", [], [], "", "", today) == "not yet due"
    assert reading("FY26 Q1", [], [], "2025-12-08", "Delivery Order/Task Order", today) == \
        "no public notice found; SeaPort/GSA order competitions are not posted on SAM.gov; incumbent last acted 2025-12-08"

    block = money_block(["2025-06-19: $250M - $1B"], [("N1", 307743354.0)], [("N1", 0.0)])
    assert "$307,743,354" in block[1] and block[2].endswith("N1 $0") and "$250M - $1B" in block[0]
    assert not any("total" in line.lower() and "$5" in line for line in block), "money kinds are never summed"

    text = ("NAVWAR, in support of the Tactical Data Link (TDL) Program Office (PMW-530) (formerly Multifunctional Information "
            "Distribution (MIDS) Program Office (MPO) (PMA/W-101)), intends to process a ceiling increase")
    offices = resolve_offices(text)
    assert any(o["office"] == "pmw:101" for o in offices), offices
    ipo = resolve_offices("NAVWAR, on behalf of the Multifunctional Information Distribution System (MIDS) International Program Office (IPO) issues a Full and Open RFP")
    assert any(o["office"] == "pmw:101" for o in ipo), "an acronym in brackets between the words must not hide the office"

    # Candidates rest on program names and codes, never on procurement vocabulary.
    assert distinctive_tokens("NTCDL – Follow-On Production and ESS Contract (C)") == {"ntcdl"}
    assert distinctive_tokens("MIDS WDL SF2 Production (C)") == {"mids", "wdl", "sf2"}
    assert distinctive_tokens("DO 0002 under SF1 Contract N0003923D4000") == {"sf1", "n0003923d4000"}, "a bare number names nothing"
    ctx = {"rarity": {"ntcdl": 2, "mids": 12, "wdl": 2}, "parents": {"pmw:101": {"peo:c4i"}}, "offices_of": {"n1": set(), "n2": {"pmw:101"}, "n3": {"pmw:170"}}}
    hits = {"n1": {"id": "n1", "title": "NTCDL Engineering Support Services - Sole Source", "type": "Presolicitation", "posted": "2026-05-22", "solicitation": "N0003926RB002"},
            "n2": {"id": "n2", "title": "MIDS Weapons Data Link (WDL) SWARMM Family 2", "type": "Solicitation", "posted": "2024-08-30", "solicitation": "N0003924R4100"},
            "n3": {"id": "n3", "title": "LBUCS Development and Production", "type": "Presolicitation", "posted": "2024-01-01", "solicitation": "X"}}
    line = {"requirement_title": "NTCDL – Follow-On Production and ESS Contract (C)", "office_id": "pmw:170", "solicitation_fy": "FY26", "award_fy": "FY27"}
    assert [c["id"] for c in candidate_notices(line, hits, ctx)] == ["n1"], "one rare program token is enough"
    line = {"requirement_title": "MIDS WDL SF2 Production (C)", "office_id": "peo:c4i", "solicitation_fy": "FY24", "award_fy": "FY25"}
    got = candidate_notices(line, hits, ctx)
    assert [c["id"] for c in got] == ["n2"] and "line filed under the notice office's parent code" in got[0]["key"], got
    line = {"requirement_title": "MIDS WDL SF2 Production (C)", "office_id": "peo:c4i", "solicitation_fy": "FY28", "award_fy": "FY29"}
    assert candidate_notices(line, hits, ctx) == [], "a notice three fiscal years before the line's window is not its solicitation"
    line = {"requirement_title": "LBUCS Receive Version 2 Development and Production", "office_id": "pmw:770", "solicitation_fy": "FY26", "award_fy": "FY26"}
    assert candidate_notices(line, hits, ctx) == [], "generic words never link, and a notice naming another office is dropped"
    assert related_office("pmw:101", "peo:c4i", ctx["parents"]) == "notice names the line's parent"
    assert compact("N00039-24-R-4019") == "N0003924R4019" and SOL_RE.findall("ADNSMACN0003925R9510(NewAwardFY25)") == ["N0003925R9510"]
    print("trace selfcheck ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    if "--selfcheck" in (argv or sys.argv[1:]):
        return selfcheck()
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("status", help="forecast lines whose solicitation window has arrived: solicited, awarded, or silent")
    s.add_argument("--office", default="", help="organization-memory id, e.g. pmw:170")
    s.add_argument("--through", default="26", help="two-digit fiscal year the solicitation window must fall in or before")
    s.set_defaults(func=cmd_status)
    n = sub.add_parser("need", help="one requirement across releases, offices, contracts, notices and awards")
    n.add_argument("key")
    n.set_defaults(func=cmd_need)
    o = sub.add_parser("notice", help="a SAM.gov notice traced to its office, history and candidate forecast lines")
    o.add_argument("key")
    o.set_defaults(func=cmd_notice)
    w = sub.add_parser("award", help="a contract read back to the forecast and forward to what followed")
    w.add_argument("piid")
    w.set_defaults(func=cmd_award)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
