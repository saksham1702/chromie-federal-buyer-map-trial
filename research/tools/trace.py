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

Three rules the output keeps:

  - A negative names the records searched and their retrieval date ("no award found in
    the saved FPDS lookup as of 2026-09-20"). It never says nothing was awarded.
  - Every connection carries its source: the URL, the retrieval date and the hash of the
    saved bytes, the spreadsheet row, or the observation ids in the organization memory.
  - Two titles naming different lots, families or generations (SF2 and SF3, Services II
    and III) are related procurements in one program, printed apart from candidates for
    the same requirement; they are context, never the same buy.
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


def search_dates(rows: list[dict]) -> tuple[str, str]:
    """Earliest and latest retrieval dates of the saved SAM.gov searches; every negative reading is scoped to them."""
    dates = sorted(r["retrieved_at"][:10] for r in rows if r.get("status") == 200 and "sgs/v1/search" in r.get("url", ""))
    return (dates[0], dates[-1]) if dates else ("", "")


def not_found(what: str, where: str, as_of: str) -> str:
    """A negative names the records searched and the date; it never claims the thing did not happen."""
    return f"no {what} found in {where}" + (f" as of {as_of}" if as_of else "")


def cite(row: dict | None) -> str:
    """One saved lookup, cited: URL, retrieval date, hash prefix."""
    return f"{row['url']} retrieved {row['retrieved_at'][:10]} sha {row['sha256'][:12]}" if row else "not collected"


SAM_VIEW = "https://sam.gov/opp/{}/view"


def notice_source(rows: list[dict], notice_id: str) -> dict | None:
    """The manifest row of a harvested notice detail (not its attachment list)."""
    return saved(rows, lambda u: f"/opportunities/{notice_id}?" in u and "/resources" not in u)


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
                          "source_url": source.get("source_url", ""), "fetched_from": source.get("fetched_from", ""),
                          "retrieved_at": source.get("retrieved_at", "")[:10], "raw_path": source.get("raw_path", ""),
                          "record_key": c["record_key"], "office_id": c["office_id"], "joins": joins.get(r["row_number"], [])})
    return lines


def release_sources(lines: list[dict]) -> list[str]:
    """One citation per release the lines came from: the spreadsheet URL, how and when it was fetched, its hash."""
    seen: dict[str, dict] = {}
    for l in lines:
        seen.setdefault(l["release"], l)
    return [f"{l['release']}: {l['source_url'] or 'source URL not recorded'} (retrieved {l['retrieved_at'] or '?'}"
            + (f" via {l['fetched_from']}" if l["fetched_from"] and l["fetched_from"] != l["source_url"] else "")
            + f"; sha256 {l['sha']}; saved {l['raw_path'] or '?'})" for _, l in sorted(seen.items())]


def quarter_dates(fy_text: str, quarter: str) -> tuple[date, date] | None:
    """Calendar bounds of a federal fiscal quarter: FY26 Q1 is October to December 2025."""
    fy, q = fiscal_year(fy_text), (quarter or "").strip().upper()
    starts = {"Q1": (-1, 10), "Q2": (0, 1), "Q3": (0, 4), "Q4": (0, 7)}
    if not fy or q not in starts:
        return None
    offset, month = starts[q]
    start = date(fy + offset, month, 1)
    return start, date(start.year, month + 2, {12: 31, 3: 31, 6: 30, 9: 30}[month + 2])


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
          select o.id, o.name, o.acronym, o.source_ref, o.parent_organization_id, 1 as depth from public.gov_organizations o where o.id = {lit(org_id)}
          union all
          select p.id, p.name, p.acronym, p.source_ref, p.parent_organization_id, up.depth + 1 from up join public.gov_organizations p on p.id = up.parent_organization_id)
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
          select distinct e.source_key, e.source_url, e.excerpt, a.source_key as assertion_key, a.observed_at::date as observed_at
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


def reading(sol_window: str, notices: list[dict], awards: list[dict], incumbent_last: str, instrument: str, today: date, searched: str = "") -> str:
    """One deterministic sentence on whether a forecast line has been solicited or awarded.

    A negative is scoped to the saved SAM.gov searches and their latest retrieval date; the
    saved records holding nothing is what is known, not that nothing happened.
    """
    if awards:
        first = min(a["signed"] for a in awards if a.get("signed")) if any(a.get("signed") for a in awards) else "date unstated"
        return f"awarded: {len(awards)} action(s) under the line's solicitation, first signed {first}"
    kinds = {n.get("type", "").lower() for n in notices}
    latest = max((n.get("posted") or "" for n in notices), default="")
    if kinds & {"solicitation", "presolicitation", "combined synopsis/solicitation"}:
        return f"solicited: {', '.join(sorted(kinds & {'solicitation', 'presolicitation', 'combined synopsis/solicitation'}))} posted {latest}"
    if kinds & {"sources sought", "special notice"}:
        return f"market research only: {', '.join(sorted(kinds))} posted {latest}"
    searched_in = "the saved SAM.gov searches"
    if kinds & {"award notice", "justification (j&a)", "justification"}:
        return f"incumbent action noticed: {', '.join(sorted(kinds))} posted {latest}; {not_found('follow-on solicitation', searched_in, searched)}"
    due = fiscal_year(sol_window)
    if due and date(due - 1, 10, 1) > today:
        return "not yet due"
    tail = "; SeaPort/GSA order competitions are not posted on SAM.gov" if "order" in (instrument or "").lower() else ""
    tail += f"; incumbent last acted {incumbent_last}" if incumbent_last else ""
    return not_found("public notice", searched_in, searched) + tail


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

# A lot, family, increment, phase, block or version number in a title. Two titles that carry
# different ones name different buys in one program.
GEN_RE = re.compile(r"\b(?:SF|SWARMM\s+Family|Family|Lot|Increment|Inc\.?|Phase|Block|Spiral|Generation|Gen|Version|Ver\.?)\s*-?\s*(\d{1,2}|[IVX]{1,4})\b", re.I)
ROMAN_RE = re.compile(r"\b([IVX]{2,4})\b")  # "C4ISR Training Services III"
ROMAN = {"I": 1, "V": 5, "X": 10}


def roman_to_int(text: str) -> int:
    total = 0
    for i, ch in enumerate(text.upper()):
        value = ROMAN[ch]
        total += -value if i + 1 < len(text) and ROMAN[text[i + 1].upper()] > value else value
    return total


def generations(text: str) -> set[int]:
    """Generation numbers a title states; empty when it states none."""
    out = set()
    for m in GEN_RE.finditer(text or ""):
        out.add(int(m.group(1)) if m.group(1).isdigit() else roman_to_int(m.group(1)))
    for m in ROMAN_RE.finditer(text or ""):  # ponytail: a bare II..XV is read as a generation; a stray acronym would too
        out.add(roman_to_int(m.group(1)))
    return out


def gen_label(text: str) -> str:
    return ", ".join(str(g) for g in sorted(generations(text))) or "none stated"


def relation_of(line_title: str, notice_title: str) -> str:
    """'candidate' when two titles may name one buy; 'related' when each states a different generation."""
    a, b = generations(line_title), generations(notice_title)
    return "related" if a and b and not (a & b) else "candidate"


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
    office comparison travels with every candidate that survives. A hit whose title states a
    different lot, family or generation from the line's comes back with method `related`: a
    procurement in the same program that is context for this line and never its solicitation.
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
        kind = relation_of(line["requirement_title"], h["title"])
        if kind == "related":
            basis += (f"; different generation (line {gen_label(line['requirement_title'])}, notice {gen_label(h['title'])}): "
                      "a related procurement in the same program, not this buy")
        out.append({**h, "method": kind, "key": basis})
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
    nearby = [c for c in candidate_notices(line, hits, ctx) if c["id"] not in known]
    candidates = [c for c in nearby if c["method"] == "candidate"]
    related = [c for c in nearby if c["method"] == "related"]
    _, searched = search_dates(rows)
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
    verdict = reading(sol_window, notices, awards, incumbent_last, line["procurement_instrument"], today, searched)
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
            "notices": notices, "candidates": candidates, "related": related, "awards": awards, "candidate_awards": candidate_awards,
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


def seed_index() -> dict:
    """The organization memory by id: nodes, observations, relationships, and live child_of edges by (child, parent)."""
    seed = json.loads((RESEARCH / "organization_seed.json").read_text(encoding="utf-8"))
    return {"nodes": {n["id"]: n for n in seed["nodes"]},
            "obs": {o["id"]: o for o in seed["observations"]},
            "rels": {r["id"]: r for r in seed["relationships"]},
            "child_of": {(r["from"], r["to"]): r for r in seed["relationships"]
                         if r["type"] == "child_of" and r["review_status"] != "retracted"}}


def evidence_of(obs_ids: list[str], idx: dict, limit: int = 2) -> str:
    """The observations behind a claim, newest last: id, date and source URL, with a count of the older ones."""
    obs = sorted((idx["obs"][o] for o in obs_ids or [] if o in idx["obs"]), key=lambda o: o["observed_at"])
    if not obs:
        return "no observation cited"
    shown = obs[-limit:]
    return (f"+{len(obs) - limit} earlier; " if len(obs) > limit else "") + "; ".join(f"{o['id']} {o['observed_at']} {o['source_url']}" for o in shown)


def succession(dsn: str, org_id: str) -> list[dict]:
    """Successor edges documented for the office or an ancestor, each with the organization it is documented for."""
    return query(dsn, f"""
        with recursive up as (
          select o.id, o.name, o.source_ref, o.parent_organization_id from public.gov_organizations o where o.id = {lit(org_id)}
          union all
          select p.id, p.name, p.source_ref, p.parent_organization_id from up join public.gov_organizations p on p.id = up.parent_organization_id)
        select json_agg(row_to_json(t)) from (
          select up.name as ancestor, up.source_ref as ancestor_ref, s.name as successor, s.source_ref as successor_ref,
                 r.valid_from, r.source_ref, r.source_url
            from up join public.gov_organization_relationships r on r.target_organization_id = up.id and r.relationship_type = 'successor_to'
            join public.gov_organizations s on s.id = r.source_organization_id order by r.valid_from, r.source_ref) t""")


def print_succession(dsn: str, org_id: str, chain: list[dict], idx: dict, indent: str) -> None:
    """A reorganization is reported at the level the source documents it, never pushed down onto the office.

    PEO C4I's mission-systems elements were consolidated into PAE Mission Systems; the release
    does not itemize offices. An office is placed under the successor only when its own source
    says so (then it is in the ancestry above); otherwise the succession prints as its
    ancestor's, with the office's own parent claim and when it was last confirmed.
    """
    office = chain[0]
    for s in succession(dsn, org_id):
        rel = idx["rels"].get(s["source_ref"]) or {}
        scope = rel.get("scope_as_stated") or "scope not stated by the source"
        level = "this office itself" if s["ancestor_ref"] == office["source_ref"] else f"an ancestor ({s['ancestor_ref']})"
        print(f"{indent}succession documented for {level}: {s['ancestor']} -> {s['successor']} from {s['valid_from'] or 'an undated release'} "
              f"({s['source_ref']}; evidence {evidence_of(rel.get('observation_ids'), idx)})")
        print(f"{indent}  scope as the source states it: {scope}")
        if s["ancestor_ref"] != office["source_ref"]:
            claim = idx["child_of"].get((office["source_ref"], s["ancestor_ref"]))
            if claim:
                status = claim["current_status"]
                held = f"{claim['id']} is {status['state']} as of {status['as_of']}" + (f": {status['note']}" if status.get("note") else "")
            else:
                held = "no parent claim in the memory ties it to that ancestor"
            print(f"{indent}  this office under {s['successor']}: not established by any loaded source; its parent claim {held}")


def print_names(node: dict, idx: dict, indent: str = "  ") -> None:
    """Every name and code the sources have used for the office, with the observation dates each rests on."""
    entries = [(node["name"], node.get("observation_ids") or [])] + [(a["text"], a["observation_ids"]) for a in node.get("aliases") or []]
    print(f"{indent}names over time ({len(entries)} in the organization memory; a name is only as current as its latest observation):")
    for text, obs_ids in entries:
        obs = sorted((idx["obs"][o] for o in obs_ids if o in idx["obs"]), key=lambda o: o["observed_at"])
        if not obs:
            print(f"{indent}  {text!r}: no observation cited")
            continue
        span = obs[0]["observed_at"] if obs[0]["observed_at"] == obs[-1]["observed_at"] else f"{obs[0]['observed_at']} .. {obs[-1]['observed_at']}"
        print(f"{indent}  {text!r}: observed {span} ({len(obs)}; latest {obs[-1]['id']} {obs[-1]['source_url']})")
    if node.get("codes"):
        print(f"{indent}  codes: {', '.join(f'{k} {v}' for k, v in node['codes'].items())}")


def print_office(dsn: str, org_id: str, idx: dict, indent: str = "  ") -> None:
    chain = ancestry(dsn, org_id)
    print(f"{indent}ancestry today: {' -> '.join(a['name'] for a in chain)}")
    for child, parent in zip(chain, chain[1:]):
        rel = idx["child_of"].get((child["source_ref"], parent["source_ref"]))
        if rel:
            status = rel["current_status"]
            print(f"{indent}  {child['source_ref']} under {parent['source_ref']}: {rel['id']}, from {rel['effective_from'] or 'start unstated'} "
                  f"({rel['effective_dates_status']} dates), {status['state']} as of {status['as_of']}; evidence {evidence_of(rel['observation_ids'], idx)}")
        else:
            print(f"{indent}  {child['source_ref']} under {parent['source_ref']}: parent column set, no child_of claim found in the memory")
    print_succession(dsn, org_id, chain, idx, indent)
    for h in org_history(dsn, org_id):
        rel = idx["rels"].get(h["source_ref"])
        print(f"{indent}history: {h['source_name']} {h['relationship_type']} {h['target_name']} "
              f"[{h['valid_from'] or 'start unstated'} .. {h['valid_to'] or 'open'}] ({h['source_ref']}"
              + (f"; evidence {evidence_of(rel.get('observation_ids'), idx)})" if rel else ")"))


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
    first, last = search_dates(rows)
    fpds = sorted(r["retrieved_at"][:10] for r in rows if r.get("status") == 200 and "fpds.gov" in r.get("url", ""))
    print(f"# Forecast lines in {latest} with a solicitation window through FY{args.through}: {len(due)} of {len(lines)} included lines")
    print(f"# Read on {today} against saved SAM.gov searches (retrieved {first} to {last}), FPDS lookups (retrieved {fpds[0] if fpds else '?'} to {fpds[-1] if fpds else '?'}) "
          "and attribution examples. Nothing here is fetched live: a negative reading says the saved records hold nothing, not that nothing happened.")
    print("# Notice column: explicit joins first (PID or incumbent contract number in the notice text), then candidates marked ~: a shared program name or code that few lines carry, with the notice's own office compared to the line's. A candidate is a reviewer's call. "
          "'related:' marks a notice for a different lot, family or generation of the same program: context, never this line's solicitation.")
    print("# Incumbent column: USAspending last-modified date; a * means only the first FPDS page was saved and later actions may exist.")
    print()
    print("| PID | title | office | sol | award | value as stated | notice | incumbent last action | award found | reading |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    counts = defaultdict(int)
    for l in sorted(due, key=lambda l: (l["office_id"], l["solicitation_fy"], l["solicitation_quarter"], l["requirement_title"])):
        s = line_status(l, rows, hits, examples, today, ctx)
        counts[s["reading"].split(":")[0].split(";")[0]] += 1
        notice = "; ".join(f"{n['type']} {n['posted']} ({n['solicitation'] or n['id'][:8]})" for n in s["notices"][:2])
        notice = "; ".join(x for x in [notice] + [f"~{c['type']} {c['posted']} ({c['solicitation'] or c['id'][:8]})" for c in s["candidates"][-2:]]
                           + [f"related: {c['type']} {c['posted']} ({c['solicitation'] or c['id'][:8]})" for c in s["related"][-2:]] if x) or "-"
        awards = "; ".join(f"{a['piid']} {a['signed']}" for a in s["awards"][:3]) or \
            "; ".join(f"~{a['piid']} {a['signed']}" for a in s["candidate_awards"][:3]) or (s["linked_award"] or "-")
        print(f"| {s['pid']} | {s['title'][:48]} | {s['office']} | {s['sol']} | {s['award']} | {s['value']} | {notice} | {s['incumbent_last'] or '-'} | {awards} | {s['reading'][:220]} |")
    print()
    print("Readings: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))
    return 0


def watch_block(lines: list[dict], today: date, incumbents: list[tuple[str, dict | None]], candidates: list[dict],
                related: list[dict], siblings: list[dict], office: str, searched: str) -> list[str]:
    """What to watch for a requirement whose RFP has not appeared: read from the rows above, nothing new asserted."""
    latest = lines[-1]
    pid = latest["pid"] or latest["record_key"]
    piids = [t for t, _ in incumbents]
    tokens = sorted(distinctive_tokens(latest["requirement_title"]))
    out = ["\n## Watch: a requirement to follow before its RFP (read from the rows above; the tool asserts nothing new)"]
    sol = quarter_dates(latest["solicitation_fy"], latest["solicitation_quarter"])
    sol_window, award_window = window(latest["solicitation_fy"], latest["solicitation_quarter"]), window(latest["award_fy"], latest["award_quarter"])
    if sol:
        first, last = sol
        if today < first:
            when = f"opens in {(first - today).days} days"
        elif today <= last:
            when = "is open now"
        else:
            when = f"closed {(today - last).days} days ago; {not_found('solicitation of this line', 'the saved SAM.gov searches', searched)}"
        out.append(f"- forecast: solicitation {sol_window} ({first} to {last}) {when}; award {award_window}; {latest['release']} row {latest['row_number']}")
    else:
        out.append(f"- forecast: solicitation window {sol_window} is not a dated quarter; award {award_window}; {latest['release']} row {latest['row_number']}")
    why = [latest["anticipated_total_value"] or "no value stated", latest["procurement_method"] or "method unstated",
           latest["procurement_instrument"] or "instrument unstated", latest["follow_on_or_new"] or "new/follow-on unstated"]
    if latest["existing_contract_number"]:
        why.append(f"incumbent {latest['existing_contract_number']}" + (f" ({latest['incumbent_contractor']})" if latest["incumbent_contractor"] else ""))
    out.append("- why it matters, as the forecast states it: " + "; ".join(why))
    pop_end = ""
    for t, u in incumbents:
        if not u:
            out.append(f"- incumbent {t}: USAspending not collected, so its end date and headroom are unknown here")
            continue
        pop_end = pop_end or u["pop_end"] or ""
        days = f" ({(date.fromisoformat(u['pop_end']) - today).days} days from {today})" if u["pop_end"] else ""
        ceiling, obligated = float(u["ceiling"] or 0), float(u["obligated"] or 0)
        out.append(f"- incumbent {t}: period of performance ends {u['pop_end'] or 'unstated'}{days}; ceiling ${ceiling:,.0f}, obligated ${obligated:,.0f}, "
                   f"headroom ${ceiling - obligated:,.0f} (this one contract's ceiling less its own obligations); USAspending retrieved {u['retrieved']}")
    if candidates:
        out.append("- on the record so far, as candidates: " + "; ".join(f"{c['type'].lower()} {c['posted']} [{c['solicitation'] or c['id'][:12]}] ({c['key']})" for c in candidates))
    if related:
        out.append("- related procurements in the program (not this buy): " + "; ".join(f"{c['type'].lower()} {c['posted']} [{c['solicitation'] or c['id'][:12]}]" for c in related))
    if siblings:
        out.append("- sibling forecast lines in the same office sharing a program name: " + "; ".join(f"{l['pid'] or l['record_key']} {l['requirement_title'][:50]} (sol {window(l['solicitation_fy'], l['solicitation_quarter'])})" for l in siblings))
    confirm = [f"a solicitation-stage SAM.gov notice carrying the PID {pid}" + (f" or the incumbent contract {', '.join(piids)}" if piids else ""),
               f"a solicitation-stage notice whose title carries {', '.join(tokens) or 'the line title'} and names {office} or its parent",
               "the next LRAE release keeping the line with an unchanged or nearer window"]
    if piids:
        confirm.insert(2, f"an FPDS or USAspending action under a new solicitation number naming {piids[0]} as the predecessor")
    invalidate = ["the next LRAE release dropping the line" + (f" or folding its scope into {', '.join(l['pid'] or l['record_key'] for l in siblings)}" if siblings else "")]
    if piids:
        invalidate.insert(0, f"a J&A, extension or modification carrying {piids[0]} past {pop_end or 'its current end date'}")
    if candidates:
        invalidate.append("an award under " + ", ".join(sorted({compact(c["solicitation"]) for c in candidates if c["solicitation"]}) or ["the candidate notice"]) + " whose description covers this line's scope")
    out.append("- would confirm: " + "; ".join(confirm))
    out.append("- would invalidate: " + "; ".join(invalidate))
    checks = [f"python research/tools/sam_notices.py {t}" for t in tokens[:2]]
    checks += [f"python research/tools/fetch.py 'https://api.usaspending.gov/api/v2/awards/CONT_AWD_{t}_9700_-NONE-_-NONE-/'" for t in piids[:1]]
    checks += [f"python research/tools/fetch.py 'https://www.fpds.gov/ezsearch/FEEDS/ATOM?FEEDNAME=PUBLIC&q=PIID:{t}&start=0'" for t in piids[:1]]
    out.append("- to re-check: " + "; ".join(checks))
    return out


def print_need(dsn: str, key: str) -> int:
    rows, hits, examples, ctx, idx = manifest(), sgs_hits(manifest()), attribution_examples(), match_context(), seed_index()
    _, searched = search_dates(rows)
    today = date.today()
    need = need_record(dsn, key)
    pairs = paired_rows(key)
    lines = [l for l in lrae_lines() if l["record_key"] == key or l["pid"] == key or (l["release"], l["row_number"]) in pairs]
    if not need and not lines:
        print(f"nothing loaded or packaged under {key!r}; try the PID or a record key like row:lrae_navwar_2024-06:406")
        return 1
    title = need["title"] if need else lines[-1]["requirement_title"]
    print(f"# {key} - {title}")
    office_id = ""
    if need:
        live = [o for o in need["offices"] if o["live"] and o["role"] == "originating_requirement_owner"]
        for o in live:
            print(f"Office (live claim, {o['observed_at']}): {o['name']}")
            print_office(dsn, o["org_id"], idx)
        if len(live) > 1:
            print("  NOTE: more than one live owner claim; the releases disagree and both are kept")
    if lines:
        office_id = lines[-1]["office_id"]
    print("\n## Forecast history (one row per release that carried the line, with how the row was tied to this key)")
    print("| release | row | matched by | sol | award window | value as stated | office named | method | instrument |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for l in lines:
        basis = "PID on the row" if l["pid"] == key else ("record key" if l["record_key"] == key else pairs.get((l["release"], l["row_number"]), ""))
        print(f"| {l['release']} ({l['release_date']}) | {l['sheet']}!row {l['row_number']} (sha {l['sha']}) | {basis} | {window(l['solicitation_fy'], l['solicitation_quarter'])} | "
              f"{window(l['award_fy'], l['award_quarter'])} | {l['anticipated_total_value']} | {l['office_code_string'].split(' - ')[0]} -> {l['office_id']} | {l['procurement_method'] or '-'} | {l['procurement_instrument'] or '-'} |")
    for src in release_sources(lines):
        print(f"  source {src}")
    if any("candidate" in pairs.get((l["release"], l["row_number"]), "") for l in lines):
        print("\nA row matched as a candidate is a reviewer's call, not the tool's; its field changes are reported against the pair in the release diff.")
    if need and need["revisions"]:
        print("\nLoaded revisions (gov_requirement_revisions): " + "; ".join(
            f"{r['observed_at']}: award {r['expected_from'] or '?'}..{r['expected_to'] or '?'}{' (live)' if r['live'] else ''}" for r in need["revisions"]))
    estimates = [f"{l['release_date']}: {l['anticipated_total_value'] or 'no range'}" for l in lines]
    ceilings, obligations, sources = [], [], {}
    print("\n## Incumbent and related contracts (saved USAspending / FPDS)")
    tokens = []
    for l in lines:
        for t in contract_tokens(l["existing_contract_number"]):
            if t not in tokens:
                tokens.append(t)
    incumbents = []
    for t in tokens:
        u = usaspending(rows, t)
        actions, atom = fpds_by_piid(rows, t)
        incumbents.append((t, u))
        if u:
            print(f"- {t} ({u['type']}, {u['recipient']}): signed {u['signed']}, PoP {u['pop_start']} -> {u['pop_end']}, last modified {u['last_modified']}; "
                  f"solicitation {u['solicitation'] or 'unstated'}; {u['competed'] or ''}, offers {u['offers']}")
            print(f"    source USAspending {u['url']} retrieved {u['retrieved']} sha {u['sha']}")
            ceilings.append((t, u["ceiling"])); obligations.append((t, u["obligated"]))
            sources[t] = f"USAspending {u['url']} retrieved {u['retrieved']} sha {u['sha']}"
        else:
            print(f"- {t}: USAspending not collected (python research/tools/fetch.py 'https://api.usaspending.gov/api/v2/awards/CONT_AWD_{t}_9700_-NONE-_-NONE-/')")
        if actions:
            recent = sorted(actions, key=lambda a: a["signed"])[-3:]
            print(f"  FPDS: first page of actions saved ({len(actions)}; later pages were not collected, so USAspending's last-modified date is the recency to trust); "
                  + "; ".join(f"{a['mod'] or 'base'} {a['signed']} obligated ${float(a['obligated'] or 0):,.0f}" for a in recent))
            print(f"    source FPDS {cite(atom)}")
        elif atom is None:
            print(f"  FPDS PIID lookup not collected (python research/tools/lrae_package.py collect)")
    print("\n## Notices (saved SAM.gov searches joined to this line; ~ marks a candidate by shared program name, a reviewer's call)")
    seen = set()
    sols = set()
    candidate_sols = set()
    candidates, related = [], []
    for l in lines:
        for n in notice_summaries(l, hits):
            if n["id"] in seen:
                continue
            seen.add(n["id"])
            print(f"- {n['posted']} {n['type']}: {n['title'][:90]} [{n['solicitation'] or 'no number'}] via {n['method']} key {n['key']}")
            print(f"    source {SAM_VIEW.format(n['id'])}; found by {n['query_url']} (sha {n['sha']})" if n["sha"] else f"    source {SAM_VIEW.format(n['id'])}; saved {n['query_url']}")
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
            (related if c["method"] == "related" else candidates).append(c)
    for c in candidates:
        print(f"- ~{c['posted']} {c['type']}: {c['title'][:90]} [{c['solicitation'] or 'no number'}] candidate, {c['key']}")
        print(f"    source {SAM_VIEW.format(c['id'])}")
        if c["solicitation"]:
            candidate_sols.add(compact(c["solicitation"]))
    for c in related:
        print(f"- related, not this buy: {c['posted']} {c['type']}: {c['title'][:90]} [{c['solicitation'] or 'no number'}] {c['key']}")
        print(f"    source {SAM_VIEW.format(c['id'])}")
    for l in lines:
        sols.update(compact(m) for m in SOL_RE.findall(l["requirement_title"].replace(" ", "")))
    if not seen:
        print("- " + not_found("notice joined to this line", "the saved SAM.gov searches", searched) + "; "
              + ("SeaPort/GSA order competitions are not posted on SAM.gov" if any("order" in l["procurement_instrument"].lower() for l in lines) else "no saved search hit contains the PID or the incumbent contract"))
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
                print(f"    source FPDS {cite(atom)}")
                ceilings.append((a["piid"], a["base_and_all_options"])); obligations.append((a["piid"] + " at award", a["obligated"]))
                sources[a["piid"]] = f"FPDS {cite(atom)}"
                u = usaspending(rows, a["piid"])
                if u:
                    obligations[-1] = (a["piid"], u["obligated"])
                    sources[a["piid"]] += f"; USAspending {u['url']} retrieved {u['retrieved']} sha {u['sha']}"
        elif atom is not None:
            print(f"- {mark}{sol}: {not_found('award', 'the saved FPDS lookup by solicitation number', atom['retrieved_at'][:10])}; source FPDS {cite(atom)}")
        else:
            print(f"- {mark}{sol}: not collected (python research/tools/fetch.py 'https://www.fpds.gov/ezsearch/FEEDS/ATOM?FEEDNAME=PUBLIC&q=SOLICITATION_ID:{sol}&start=0')")
    if not sols:
        print("- no solicitation number on the line or in its notices, so there is no FPDS lookup to make by solicitation")
    pid = lines[-1]["pid"] if lines else key
    if pid in examples:
        x = examples[pid]
        print(f"- reviewed attribution {x['id']}: award {x['identifier']} ({x['evidence_class']}); {x.get('notes', '')[:140]}")
        u = usaspending(rows, x["identifier"])
        if u:
            ceilings.append((x["identifier"], u["ceiling"])); obligations.append((x["identifier"], u["obligated"]))
            sources[x["identifier"]] = f"USAspending {u['url']} retrieved {u['retrieved']} sha {u['sha']}"
            print(f"  {x['identifier']}: signed {u['signed']}, PoP {u['pop_start']} -> {u['pop_end']}, {u['recipient']}, solicitation {u['solicitation'] or 'unstated'}")
    print("\n## Money, kept apart")
    print("\n".join(money_block(estimates, ceilings, obligations)))
    for piid, src in sources.items():
        print(f"  source for {piid}: {src}")
    if need:
        print("\n## Loaded records (the database rows the claims above rest on)")
        print(f"- need {need['id']} source_key {need['source_key']}")
        for r in need["revisions"]:
            print(f"- revision assertion {r['source_key']} observed {r['observed_at']}{' (live)' if r['live'] else ' (superseded)'}")
        for e in sorted(need["evidence"], key=lambda e: (e["observed_at"] or "", e["source_key"])):
            print(f"- evidence {e['source_key']}: {e['excerpt'][:80]}; source {e['source_url'] or 'URL not loaded'}")
    if lines and lines[-1]["release"] == PACKS[-1].name and not found:
        my_tokens = {t for t in distinctive_tokens(lines[-1]["requirement_title"]) if ctx["rarity"].get(t, 0) <= 3}
        siblings = [l for l in lrae_lines() if l["release"] == PACKS[-1].name and l["office_id"] == office_id
                    and l["record_key"] != lines[-1]["record_key"] and my_tokens & distinctive_tokens(l["requirement_title"])]
        print("\n".join(watch_block(lines, today, incumbents, candidates, related, siblings, office_id, searched)))
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


def line_match(detail: dict, title: str, lines: list[dict], ctx: dict, codes_only: bool = False) -> dict | None:
    """How a forecast line stands to a notice.

    explicit: the notice text names the line's incumbent contract. candidate: the titles share
    a program name or code few lines carry (or two of them, or three words when `codes_only`
    is off), so they may be one buy and a reviewer decides. related: they share a program but
    state different lots, families or generations, so they are distinct buys. None: no tie.
    """
    piids = set(contract_tokens(detail["text"]))
    line_piids = {t for l in lines for t in contract_tokens(l["existing_contract_number"])}
    explicit = piids & line_piids
    if explicit:
        return {"relation": "explicit", "basis": f"explicit: incumbent contract {', '.join(sorted(explicit))} appears in the notice text"}
    notice_words, notice_codes = title_tokens(detail["title"]), distinctive_tokens(detail["title"])
    words, codes = title_tokens(title), distinctive_tokens(title)
    shared_codes = sorted(codes & notice_codes)
    rare = [t for t in shared_codes if ctx["rarity"].get(t, 0) <= 3]
    if rare or len(shared_codes) >= 2:
        shared = shared_codes
    elif not codes_only and len(words & notice_words) >= 3:
        shared = sorted(words & notice_words)
    else:
        return None
    kind = relation_of(title, detail["title"])
    basis = f"shared program tokens {', '.join(shared[:6])}"
    if kind == "related":
        basis += f"; different generation (line {gen_label(title)}, notice {gen_label(detail['title'])}), so a distinct buy in the same program"
    return {"relation": kind, "basis": f"{kind}: {basis}"}


def line_bullet(key: str, title: str, lines: list[dict], match: dict, office_note: str = "") -> str:
    latest = lines[-1] if lines else None
    when = (f"sol {window(latest['solicitation_fy'], latest['solicitation_quarter'])}, award {window(latest['award_fy'], latest['award_quarter'])}, "
            f"{latest['anticipated_total_value'] or 'no value stated'}") if latest else "no datapack row"
    record = f"; record {latest['release']} {latest['sheet']}!row {latest['row_number']} (sha {latest['sha']})" if latest else ""
    return f"- {key} {title[:70]} ({when}){office_note} - {match['basis']}{record}"


def cmd_notice(args) -> int:
    rows, hits, ctx, idx = manifest(), sgs_hits(manifest()), match_context(), seed_index()
    detail = notice_detail(args.key)
    if detail is None:
        candidates = [h for h in hits.values() if compact(h["solicitation"]) == compact(args.key) or h["id"].startswith(args.key)]
        if not candidates:
            print(f"no saved notice or search hit for {args.key!r}; collect it with: python research/tools/sam_notices.py {args.key}")
            return 1
        for h in sorted(candidates, key=lambda h: h["posted"]):
            print(f"- {h['posted']} {h['type']}: {h['title'][:90]} [{h['solicitation']}] id {h['id']} active={h['active']} {SAM_VIEW.format(h['id'])}")
        print("\nDetail not saved for these; harvest one with: python research/tools/sam_notices.py <id>")
        return 0
    print(f"# {detail['title']}")
    print(f"{detail['type']} posted {detail['posted']}; solicitation {detail['solicitation'] or 'none'}; notice {detail['id']}")
    print(f"source {SAM_VIEW.format(detail['id'])}; record {cite(notice_source(rows, detail['id']))}; saved {detail['path']}")
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
    used_lines: list[dict] = []
    for o in current or offices:
        found = find_org(args.dsn, o["office"])
        if not found:
            print(f"\n{o['office']} is not in the loaded office table")
            continue
        org = found[0]
        print(f"\n## {org['name']} (loaded as {org['org_type']}, source_ref {org['source_ref']}, row {org['id']})")
        if o["office"] in idx["nodes"]:
            print_names(idx["nodes"][o["office"]], idx)
        print_office(args.dsn, org["id"], idx)
        if o["office"].startswith(("pmw:", "peo:")):
            owned = needs_for_office(args.dsn, org["id"])
            same, related = [], []
            for n in owned:
                lines = [l for l in lrae_lines() if l["record_key"] == n["source_key"] or l["pid"] == n["source_key"]]
                m = line_match(detail, n["title"], lines, ctx)
                if m:
                    (related if m["relation"] == "related" else same).append((n, lines, m))
                    used_lines += lines
            print("\n## Forecast lines owned by this office that may be the same requirement (an explicit tie, or a candidate a reviewer accepts or rejects)")
            for n, lines, m in same:
                print(line_bullet(n["source_key"], n["title"], lines, m))
            if not same:
                print(f"- none of the {len(owned)} loaded lines owned by this office shares a program name with the notice or cites a contract it names")
            print("\n## Related procurements in the same program owned by this office (a different lot, family or generation: context for this buy, not the same requirement)")
            for n, lines, m in related:
                print(line_bullet(n["source_key"], n["title"], lines, m))
            if not related:
                print("- none")
    print("\n## Forecast lines under OTHER offices sharing the notice's program names (the office differs, so each carries that question)")
    named = {o["office"] for o in offices}
    others_same, others_related = [], []
    for l in lrae_lines():
        if l["release"] != PACKS[-1].name or l["office_id"] in named:
            continue
        m = line_match(detail, l["requirement_title"], [l], ctx, codes_only=True)
        if m:
            (others_related if m["relation"] == "related" else others_same).append((l, m))
    for l, m in others_same[:10]:
        print(line_bullet(l["pid"] or l["record_key"], l["requirement_title"], [l], m, f" under {l['office_id']} ({l['office_code_string'].split(' - ')[0]})"))
        used_lines.append(l)
    if not others_same:
        print("- none")
    print("\n## Related procurements under OTHER offices (a different lot, family or generation of the program; not this buy)")
    for l, m in others_related[:10]:
        print(line_bullet(l["pid"] or l["record_key"], l["requirement_title"], [l], m, f" under {l['office_id']} ({l['office_code_string'].split(' - ')[0]})"))
        used_lines.append(l)
    if not others_related:
        print("- none")
    for src in release_sources(used_lines):
        print(f"  forecast source {src}")
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

    kin_hits = [h for h in hits.values() if h["id"] != detail["id"] and kin(h)]
    for h in sorted(kin_hits, key=lambda h: h["posted"]):
        gen = relation_of(detail["title"], h["title"])
        print(f"- {h['posted']} {h['type']}: {h['title'][:80]} [{h['solicitation'] or 'no number'}] {SAM_VIEW.format(h['id'])}"
              + (f" (different generation: {gen_label(h['title'])}; a related buy)" if gen == "related" else ""))
    if not kin_hits:
        print("- none saved")
    if detail["solicitation"]:
        actions, atom = fpds_by_solicitation(rows, detail["solicitation"])
        print("\n## Awards under this solicitation number (saved FPDS lookup by solicitation)")
        base = [a for a in actions if a["mod"] in ("0", "")]
        for a in base:
            u = usaspending(rows, a["piid"])
            print(f"- {a['piid']} signed {a['signed']} to {a['vendor']}; base and all options ${float(a['base_and_all_options'] or 0):,.0f}; obligated at award ${float(a['obligated'] or 0):,.0f}")
            print(f"    source FPDS {cite(atom)}" + (f"; USAspending {u['url']} retrieved {u['retrieved']} sha {u['sha']}" if u else ""))
        if not base:
            if atom is not None:
                print(f"- {not_found('award', 'the saved FPDS lookup by solicitation number', atom['retrieved_at'][:10])}; source FPDS {cite(atom)}")
            else:
                print(f"- not collected (python research/tools/fetch.py 'https://www.fpds.gov/ezsearch/FEEDS/ATOM?FEEDNAME=PUBLIC&q=SOLICITATION_ID:{compact(detail['solicitation'])}&start=0')")
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
    assert reading("FY26 Q1", [], [], "2025-12-08", "Delivery Order/Task Order", today, "2026-09-20") == \
        "no public notice found in the saved SAM.gov searches as of 2026-09-20; SeaPort/GSA order competitions are not posted on SAM.gov; incumbent last acted 2025-12-08"
    assert "no follow-on solicitation found in the saved SAM.gov searches as of 2026-09-20" in \
        reading("FY26 Q2", [{"type": "Award Notice", "posted": "2024-11-05"}], [], "", "", today, "2026-09-20"), "a negative names the records searched"
    assert not_found("award", "the saved FPDS lookup", "2026-09-20") == "no award found in the saved FPDS lookup as of 2026-09-20"
    assert quarter_dates("FY26", "Q1") == (date(2025, 10, 1), date(2025, 12, 31)) and quarter_dates("FY26", "Q4") == (date(2026, 7, 1), date(2026, 9, 30))
    assert quarter_dates("TBD", "") is None and quarter_dates("FY27", "Q2") == (date(2027, 1, 1), date(2027, 3, 31))

    # Same program, different generation: related, never the same buy.
    assert generations("MIDS WDL SF2 Production (C)") == {2} and generations("MIDS (WDL) SWARMM Family 3 (SF3) Radio") == {3}
    assert generations("RSNF C4ISR Training Services III (C)") == {3} and generations("NTCDL – Follow-On Production and ESS Contract (C)") == set()
    assert generations("LBUCS Receive Version 2 Development") == {2} and generations("DO 0002 under SF1 Contract N0003923D4000") == {1}
    assert generations("PEO C4I Engineering Support") == set(), "C4I is not a roman numeral"
    assert relation_of("MIDS WDL SF2 Production (C)", "MIDS Weapons Data Link (WDL) SWARMM Family 2") == "candidate"
    assert relation_of("MIDS WDL SF2 Production (C)", "MIDS (WDL) SWARMM Family 3 (SF3) Radio") == "related"
    assert relation_of("NTCDL – Follow-On Production", "NTCDL Engineering Support Services") == "candidate", "no generation on either side keeps a candidate"

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
    ctx = {"rarity": {"ntcdl": 2, "mids": 12, "wdl": 2, "sf3": 0}, "parents": {"pmw:101": {"peo:c4i"}}, "offices_of": {"n1": set(), "n2": {"pmw:101"}, "n3": {"pmw:170"}, "n4": {"pmw:101"}}}
    hits = {"n1": {"id": "n1", "title": "NTCDL Engineering Support Services - Sole Source", "type": "Presolicitation", "posted": "2026-05-22", "solicitation": "N0003926RB002"},
            "n2": {"id": "n2", "title": "MIDS Weapons Data Link (WDL) SWARMM Family 2", "type": "Solicitation", "posted": "2024-08-30", "solicitation": "N0003924R4100"},
            "n3": {"id": "n3", "title": "LBUCS Development and Production", "type": "Presolicitation", "posted": "2024-01-01", "solicitation": "X"},
            "n4": {"id": "n4", "title": "MIDS Weapons Data Link (WDL) SWARMM Family 3 (SF3) Radio", "type": "Presolicitation", "posted": "2026-08-12", "solicitation": "N00039PRESOL_SF3"}}
    line = {"requirement_title": "NTCDL – Follow-On Production and ESS Contract (C)", "office_id": "pmw:170", "solicitation_fy": "FY26", "award_fy": "FY27"}
    assert [c["id"] for c in candidate_notices(line, hits, ctx)] == ["n1"], "one rare program token is enough"
    line = {"requirement_title": "MIDS WDL SF2 Production (C)", "office_id": "peo:c4i", "solicitation_fy": "FY24", "award_fy": "FY25"}
    got = candidate_notices(line, hits, ctx)
    assert [(c["id"], c["method"]) for c in got] == [("n2", "candidate"), ("n4", "related")], got
    assert "line filed under the notice office's parent code" in got[0]["key"]
    assert "different generation (line 2, notice 3)" in got[1]["key"], "SF3 is context for the SF2 line, never its solicitation"
    detail = {"title": "MIDS Weapons Data Link (WDL) SWARMM Family 3 (SF3) Radio", "text": "no contract numbers here"}
    m = line_match(detail, "MIDS WDL SF2 Production (C)", [], ctx)
    assert m and m["relation"] == "related" and m["basis"].startswith("related: shared program tokens mids, wdl; different generation"), m
    m = line_match(detail, "MIDS WDL Terminal Spares", [], ctx)
    assert m and m["relation"] == "candidate" and m["basis"] == "candidate: shared program tokens mids, wdl", m
    assert line_match(detail, "MIDS-LVT IDIQ - New Contracts", [], ctx) is None, "one common program name is not a tie"
    assert line_match(detail, "LBUCS Development", [], ctx) is None
    m = line_match({"title": "x", "text": "extends N0003916C0087 for BAE"}, "NTCDL Follow-On", [{"existing_contract_number": "N00039-16-C-0087"}], ctx)
    assert m and m["relation"] == "explicit" and "N0003916C0087" in m["basis"], m
    line = {"requirement_title": "MIDS WDL SF2 Production (C)", "office_id": "peo:c4i", "solicitation_fy": "FY28", "award_fy": "FY29"}
    assert [(c["id"], c["method"]) for c in candidate_notices(line, hits, ctx)] == [("n4", "related")], \
        "a notice three fiscal years before the line's window is not its solicitation; the later SF3 notice stays a related buy"
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
