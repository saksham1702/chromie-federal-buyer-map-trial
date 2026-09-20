#!/usr/bin/env python3
"""Turn the saved NAVWAR LRAE releases into reproducible data packages.

    python research/tools/lrae_package.py build              # regenerate every package from saved bytes only
    python research/tools/lrae_package.py collect [--limit N]  # fetch the FPDS and SAM.gov lookups the joins need

`build` reads the spreadsheet bytes recorded in research/documents_manifest.jsonl plus the saved
FPDS ATOM and SAM.gov search responses, and writes one datapack/lrae_navwar_<release>/ per saved
release, plus a diff between consecutive releases in the newer package. It never touches the
network, so a reviewer with the same data/raw/ gets byte-identical files. `collect` performs the
lookups that are not yet in the manifest (one FPDS PIID search per contract token, one SAM.gov
search per PID and per token) through fetch.py so every request is recorded.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.parse
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import MANIFEST, ROOT, fetch  # noqa: E402

RESEARCH = ROOT / "research"
SHEET = "LRAE Annex 25"
HEADER_ROW = 8  # Excel row number of the column headers in every release seen so far
PACK_BASE = Path(os.environ.get("LRAE_PACK_DIR") or ROOT / "datapack")  # override lets the test rebuild elsewhere
# Oldest first. `match` identifies the manifest row; `release_date` is the fallback when the sheet gives none.
RELEASES = [
    {"key": "lrae_navwar_2023-06", "match": "NAVWAR_LRAE_Report.xlsx", "release_date": "2023-06-20",
     "release_note": "sheet says '20 June 2023 / TDB'; the report was exported 2023-05-25 (Filters sheet)"},
    {"key": "lrae_navwar_2024-06", "match": "HQCA-2024-A-094", "release_date": "2024-06-20", "release_note": ""},
    {"key": "lrae_navwar_2025-06", "match": "HQCA-2025-A-037", "release_date": "2025-06-19", "release_note": ""},
]
JOINS_COLLECTED_FOR = "lrae_navwar_2025-06"  # the only release whose FPDS and SAM.gov lookups were collected
FPDS = "https://www.fpds.gov/ezsearch/FEEDS/ATOM?FEEDNAME=PUBLIC&q=PIID:{piid}&start=0"
SGS = "https://sam.gov/api/prod/sgs/v1/search/?"
PIID_RE = re.compile(r"N\d{5}\d{2}[A-Z]\d{4,5}(?!\d)|NNG\d{2}S[A-Z]\d{2}B|GS-?\d{2}F-?\d{3,4}[A-Z]{1,2}")
FORECAST_PID_RE = re.compile(r"[A-Z0-9]{6}-\d{2}-RFPREQ-[A-Za-z0-9/\-]+?-\d{4}")
INCLUDED_PARENT = "peo:c4i"
# Division and competency codes resolve to the organization that owns them, which is enough to exclude them.
FAMILY_PARENT = {"niwc_atlantic_division": "center:niwc-atlantic", "niwc_pacific_competency": "center:niwc-pacific",
                 "navwar_hq_competency": "command:navwar"}
# Header text (first line, lower-cased prefix) -> field name. Releases differ in column count and order.
HEADERS = {
    "requirement title": "requirement_title", "requirement description": "requirement_description",
    "associated program or requirement office": "office_code_string", "anticipated total value": "anticipated_total_value",
    "anticipated procurement method": "procurement_method", "anticipated contract type": "contract_type",
    "anticipated procurement instrument": "procurement_instrument", "contracting office uic": "contracting_office_uic",
    "anticipated solicitation - fiscal year": "solicitation_fy", "anticipated solicitation - quarter": "solicitation_quarter",
    "anticipated award - fiscal year": "award_fy", "anticipated award - quarter": "award_quarter",
    "anticipated period of performance": "period_of_performance_months", "follow-on or new": "follow_on_or_new",
    "existing contract number": "existing_contract_number", "incumbent contractor": "incumbent_contractor",
    "anticipated place of performance": "place_of_performance", "anticipated naics code": "naics", "anticipated psc": "psc",
    "contracting poc name": "contracting_poc_name", "contracting poc e-mail or phone": "contracting_poc_contact",
    "secondary poc name": "secondary_poc_name", "secondary poc e-mail or phone": "secondary_poc_contact",
    "anticipated facilities clearance": "facility_clearance", "anticipated personnel clearance": "personnel_clearance",
    "palt code": "palt_code", "sub palt code": "sub_palt_code", "comments or special requirements": "comments",
    "pid number": "pid", "url": "url",
}
COLUMNS = list(dict.fromkeys(HEADERS.values()))
TRACKED = ["office_code_string", "anticipated_total_value", "procurement_method", "contract_type", "procurement_instrument",
           "contracting_office_uic", "solicitation_fy", "solicitation_quarter", "award_fy", "award_quarter", "follow_on_or_new",
           "existing_contract_number", "incumbent_contractor"]
VALUE_RANGES = {
    "< $2M": (0, 2_000_000), "<$2M": (0, 2_000_000), "$2M - $7.5M": (2_000_000, 7_500_000), "> $2M - < $7.5M": (2_000_000, 7_500_000),
    "$7.5M - $50M": (7_500_000, 50_000_000), "> $7.5M - < $50M": (7_500_000, 50_000_000), "$50M - $100M": (50_000_000, 100_000_000),
    "> $50M - < $100M": (50_000_000, 100_000_000), "$100M - $250M": (100_000_000, 250_000_000), "> $100M - < $250M": (100_000_000, 250_000_000),
    "$250M - $1B": (250_000_000, 1_000_000_000), "> $250M - < $1B": (250_000_000, 1_000_000_000), "> $1B+": (1_000_000_000, ""),
    "> $1B": (1_000_000_000, ""), "No Range Specified": ("", ""),
}


# ---------------------------------------------------------------- saved inputs

def manifest_rows() -> list[dict]:
    return [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]


def saved(rows: list[dict], predicate) -> dict | None:
    """Latest successful manifest row matching the predicate whose bytes are still on disk."""
    hits = [r for r in rows if r.get("status") == 200 and r.get("path") and predicate(r) and (ROOT / r["path"]).exists()]
    return hits[-1] if hits else None


def cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def read_sheet(path: Path, release_key: str = "") -> tuple[dict, list[dict]]:
    import openpyxl  # optional dependency, only needed here

    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = book[SHEET]
    meta = {}
    for row in sheet.iter_rows(min_row=1, max_row=HEADER_ROW - 1, values_only=True):
        if row and row[0] and str(row[0]).endswith(":") and len(row) > 1:
            meta[str(row[0]).rstrip(":").strip()] = cell(row[1])
    header = next(sheet.iter_rows(min_row=HEADER_ROW, max_row=HEADER_ROW, values_only=True))
    fields = []
    for text in header:
        first = (str(text or "").split("\n")[0]).strip().lower()
        fields.append(next((name for prefix, name in HEADERS.items() if first.startswith(prefix)), None))
    rows = []
    for number, values in enumerate(sheet.iter_rows(min_row=HEADER_ROW + 1, values_only=True), start=HEADER_ROW + 1):
        if all(v is None or str(v).strip() == "" for v in values):
            continue
        record = {"sheet": SHEET, "row_number": number, "release": release_key}
        record.update({name: "" for name in COLUMNS})
        for i, name in enumerate(fields):
            if name and i < len(values):
                record[name] = cell(values[i])
        rows.append(record)
    return meta, rows


def record_key(r: dict) -> str:
    """PID when the row has one; otherwise the row itself, scoped to its release.

    A row is a source record. Two rows that share a title and an office code are
    distinct planned actions until a reviewer says otherwise: in the June 2024
    release (no PID column) rows 406 and 408-411 all read "Order to Contract
    #N0003922D4001" under PMA/PMW-101 and describe a Lot 7 order, terminal
    destruction, terminal shipment, a French MIS buy and a feasibility study.
    Hashing title and office collapsed them into one record. Identity across
    releases is the matcher's job (`pair_releases`), which reports a shared key as
    a candidate rather than resolving it.
    """
    if r["pid"]:
        return r["pid"]
    return f"row:{r.get('release', '')}:{r['row_number']}"


# ---------------------------------------------------------------- classification

def norm_code(text: str) -> str:
    return re.sub(r"[\s\-]", "", text.split("(")[0]).upper()


def alias_map() -> dict[str, str]:
    seed = json.loads((RESEARCH / "organization_seed.json").read_text(encoding="utf-8"))
    aliases: dict[str, str] = {}
    for node in seed["nodes"]:
        if node["type"] == "person":
            continue
        texts = [node["name"]] + [a["text"] if isinstance(a, dict) else a for a in node.get("aliases") or []]
        texts += list((node.get("codes") or {}).values())
        for text in texts:
            aliases.setdefault(norm_code(str(text)), node["id"])
    return aliases


def included_offices() -> set[str]:
    seed = json.loads((RESEARCH / "organization_seed.json").read_text(encoding="utf-8"))
    offices = {r["from"] for r in seed["relationships"] if r["type"] == "child_of" and r["to"] == INCLUDED_PARENT
               and r["from"].startswith("pmw:") and r["review_status"] != "retracted"}
    return offices | {INCLUDED_PARENT}


def families() -> list[tuple[str, re.Pattern, str]]:
    data = json.loads((RESEARCH / "org_code_families.json").read_text(encoding="utf-8"))
    return [(f["family"], re.compile(f["pattern"]), f.get("org_type", "")) for f in data["families"]]


def classify_code(token: str, aliases: dict[str, str] | None = None, fams: list | None = None) -> dict:
    """Alias table first, then the first matching code family. `token` may carry a ' - NAME' suffix."""
    aliases = aliases if aliases is not None else alias_map()
    fams = fams if fams is not None else families()
    code = token.split(" - ")[0].strip()
    office_id = aliases.get(norm_code(code), "")
    family = next((name for name, pattern, _ in fams if pattern.match(code)), "")
    if office_id and family == "contracting_office_uic" and not office_id.startswith("contracting:"):
        family = ""  # an alias-resolved organization name is never a UIC, whatever its length
    org_type = next((t for name, _, t in fams if name == family), "")
    return {"code": code, "office_id": office_id, "family": family, "org_type": org_type}


def classify(rows: list[dict]) -> list[dict]:
    aliases, included, fams = alias_map(), included_offices(), families()
    out = []
    for r in rows:
        hit = classify_code(r["office_code_string"], aliases, fams)
        code, family, org_type, office_id = hit["code"], hit["family"], hit["org_type"], hit["office_id"]
        key = record_key(r)
        if office_id in included:
            decision, reason = "included", f"code resolves to {office_id}, a PEO C4I office (alias table)"
        elif office_id:
            decision, reason = "excluded", f"code resolves to {office_id} ({org_type or 'other organization'}), outside the PEO C4I portfolio"
        elif family in FAMILY_PARENT:
            office_id = FAMILY_PARENT[family]
            decision, reason = "excluded", f"{org_type} code of {office_id}, outside the PEO C4I portfolio (division itself not in alias table)"
        elif family:
            decision, reason = "unresolved", f"family {family} recognised but code {code} has no alias-table entry"
        else:
            decision, reason = "unresolved", f"code {code} matches no code family"
        out.append({"sheet": r["sheet"], "row_number": r["row_number"], "record_key": key, "pid": r["pid"],
                    "office_code_string": r["office_code_string"], "office_code": code, "code_family": family,
                    "office_id": office_id, "include_decision": decision, "reason": reason})
    repeated = {k: n for k, n in Counter(c["record_key"] for c in out).items() if n > 1}
    if repeated:
        # A PID printed on two rows is a question for a person. Merging them would
        # discard one planned action; marking one a duplicate did exactly that.
        raise ValueError(f"record key repeats within one release: {repeated}")
    return out


# ---------------------------------------------------------------- joins

def contract_tokens(text: str) -> list[str]:
    compact = re.sub(r"[\s]", "", text.upper())
    tokens = []
    for match in PIID_RE.findall(compact.replace("-", "")):
        if match not in tokens:
            tokens.append(match)
    for match in PIID_RE.findall(compact):  # GSA schedule numbers keep their hyphens
        if match.startswith("GS") and match not in tokens:
            tokens.append(match)
    return tokens


def is_vehicle(token: str) -> bool:
    """IDVs (type letter D), SEWP and GSA schedule numbers are shared vehicles, never a requirement identity."""
    return token.startswith(("NNG", "GS")) or (len(token) in (13, 14) and token[8] == "D")


def fpds_entries(body: bytes) -> list[dict]:
    text = body.decode("utf-8", "replace")
    entries = []
    for chunk in text.split("<entry>")[1:]:
        def tag(name: str) -> str:
            found = re.search(rf"<ns1:{name}[^>]*>([^<]*)<", chunk)
            return found.group(1).strip() if found else ""
        entries.append({"piid": tag("PIID"), "signed": tag("signedDate")[:10], "contracting_office": tag("contractingOfficeID"),
                        "funding_office": tag("fundingRequestingOfficeID"), "vendor": tag("vendorName"),
                        "idv": tag("referencedIDVID"), "description": tag("descriptionOfContractRequirement")[:160]})
    return entries


def sgs_url(query: str, active: str) -> str:
    return SGS + urllib.parse.urlencode({"index": "opp", "page": 0, "size": 25, "q": query, "mode": "search", "is_active": active})


def sgs_hits(body: bytes, needle: str) -> list[dict]:
    try:
        results = json.loads(body).get("_embedded", {}).get("results", [])
    except json.JSONDecodeError:
        return []
    compact = needle.replace("-", "").upper()
    return [x for x in results if compact in json.dumps(x).replace("-", "").upper()]


def contacts() -> dict[tuple[str, str], str]:
    rows = json.loads((RESEARCH / "contact_observations.json").read_text(encoding="utf-8"))
    return {(norm_code(c["name"]), c["office_id_as_resolved"]): c["id"] for c in rows if c.get("name")}


def attribution_by_pid() -> dict[str, dict]:
    rows = json.loads((RESEARCH / "attribution_examples.json").read_text(encoding="utf-8"))
    table = {}
    for x in rows:
        match = FORECAST_PID_RE.match((x.get("related") or {}).get("forecast_pid") or "")
        if match:
            table[match.group(0)] = x
    return table


def build_joins(rows: list[dict], classified: list[dict], manifest: list[dict]) -> list[dict]:
    decision = {c["row_number"]: c for c in classified}
    contact_table, examples = contacts(), attribution_by_pid()
    joins = []

    def add(r, join_type, method, key, target, evidence, note):
        joins.append({"record_key": record_key(r), "pid": r["pid"], "row_number": r["row_number"], "join_type": join_type, "method": method,
                      "key_used": key, "target_id": target, "evidence_ref": evidence, "note": note})

    for r in rows:
        c = decision[r["row_number"]]
        if c["include_decision"] != "included":
            continue
        add(r, "office", "explicit", c["office_code"], c["office_id"],
            f"{SHEET}!C{r['row_number']}; organization_seed.json alias table", "requirement-office code matched an alias")
        tokens = contract_tokens(r["existing_contract_number"])
        if not tokens and r["existing_contract_number"]:
            add(r, "existing_contract", "explicit", r["existing_contract_number"], "", f"{SHEET}!O{r['row_number']}",
                "no contract identifier pattern recognised in the cell")
        for token in tokens:
            capture = saved(manifest, lambda m, t=token: f"PIID:{t}&" in m.get("url", ""))
            if capture is None:
                add(r, "existing_contract", "explicit", token, "", "", "FPDS lookup not collected yet")
                continue
            entries = fpds_entries((ROOT / capture["path"]).read_bytes())
            mine = [e for e in entries if e["piid"] == token]
            if mine:
                e = mine[0]
                add(r, "existing_contract", "explicit", token, f"fpds:{token}", f"sha256:{capture['sha256']}",
                    f"FPDS entries={len(mine)}; contracting {e['contracting_office']}; funding {e['funding_office']}; "
                    f"vendor {e['vendor']}; idv {e['idv'] or '-'}; first signed {e['signed']}")
            else:
                add(r, "existing_contract", "explicit", token, "", f"sha256:{capture['sha256']}", "FPDS PIID search returned no entry")
        needles = [n for n in [r["pid"], *tokens] if n]
        for needle in needles:
            found, refs, hits = False, [], []
            for active in ("false", "true"):
                capture = saved(manifest, lambda m, u=sgs_url(needle, active): m.get("url") == u)
                if capture is None:
                    continue
                found = True
                refs.append(f"sha256:{capture['sha256']}")
                hits += sgs_hits((ROOT / capture["path"]).read_bytes(), needle)
            if not found:
                add(r, "notice", "explicit", needle, "", "", "SAM.gov search not collected yet")
            elif hits:
                vehicle = is_vehicle(needle)
                for h in hits:
                    add(r, "notice", "inferred" if vehicle else "explicit", needle, f"sam:{h.get('_id', '')}", "; ".join(refs),
                        ("key is a shared vehicle (IDV or schedule); the notice cites the vehicle, which does not establish the same requirement; "
                         if vehicle else "notice text contains the key; ") + f"title {str(h.get('title', ''))[:80]}")
            else:
                add(r, "notice", "explicit", needle, "", "; ".join(refs), "SAM.gov search returned no notice containing the key")
        example = examples.get(r["pid"]) if r["pid"] else None
        if example:
            sam_refs = [e["source_url"] for e in example["evidence"] if "sam.gov" in e.get("source_url", "")]
            add(r, "notice", "inferred", r["pid"], f"attribution:{example['id']}", "attribution_examples.json " + example["id"],
                f"forecast row linked to award {example['identifier']} by office, title and existing contract; "
                f"{len(sam_refs)} SAM.gov notice(s) cited on that award; evidence class {example['evidence_class']}")
        for role, name_col in (("contracting_poc", "contracting_poc_name"), ("secondary_poc", "secondary_poc_name")):
            name = r[name_col]
            if not name:
                continue
            target = contact_table.get((norm_code(name), c["office_id"]), "")
            elsewhere = [v for (n, o), v in contact_table.items() if n == norm_code(name) and o != c["office_id"]]
            note = f"{role} on the row matches a contact observation for the same office" if target else (
                f"{role} has no contact observation for {c['office_id']}" + (f"; observed for {', '.join(sorted(set(elsewhere)))}" if elsewhere else ""))
            add(r, "contact", "explicit", name, target, f"{SHEET}!{'T' if role == 'contracting_poc' else 'V'}{r['row_number']}", note)
    joins.sort(key=lambda j: (j["row_number"], j["join_type"], j["method"], j["key_used"], j["target_id"]))
    return joins


# ---------------------------------------------------------------- layers (target schema)

def layers(rows: list[dict], classified: list[dict], joins: list[dict], source_sha: str, release: dict, release_date: str) -> dict[str, list[dict]]:
    decision = {c["row_number"]: c for c in classified}
    key = release["key"]
    evidence_id = lambda r: f"ev:{key}:row{r['row_number']}"  # noqa: E731
    needs, reqs, funding, refs, evidence = [], [], [], [], []
    contract_targets = {(j["row_number"], j["key_used"]): j for j in joins if j["join_type"] == "existing_contract"}
    for r in rows:
        c = decision[r["row_number"]]
        if c["include_decision"] != "included":
            continue
        rk = record_key(r)
        need_id = f"need:{key}:{rk}"
        evidence.append({"id": evidence_id(r), "source_sha256": source_sha, "locator": f"{SHEET}!row {r['row_number']}",
                         "release_date": release_date, "kind": "spreadsheet_row"})
        needs.append({"id": need_id, "record_key": rk, "pid": r["pid"], "title": r["requirement_title"], "office_id": c["office_id"],
                      "office_code_string": r["office_code_string"], "contracting_office_uic": r["contracting_office_uic"].split(" - ")[0],
                      "follow_on_or_new": r["follow_on_or_new"], "predecessor_refs": " ".join(contract_tokens(r["existing_contract_number"])),
                      "valid_from": release_date, "evidence_id": evidence_id(r)})
        reqs.append({"id": f"req:{key}:{rk}", "need_id": need_id, "revision": key,
                     "description": r["requirement_description"], "procurement_method": r["procurement_method"],
                     "contract_type": r["contract_type"], "instrument": r["procurement_instrument"],
                     "solicitation_fy": r["solicitation_fy"], "solicitation_quarter": r["solicitation_quarter"],
                     "award_fy": r["award_fy"], "award_quarter": r["award_quarter"], "pop_months": r["period_of_performance_months"],
                     "naics": r["naics"], "psc": r["psc"], "place": r["place_of_performance"], "evidence_id": evidence_id(r)})
        low, high = VALUE_RANGES.get(r["anticipated_total_value"], ("", ""))
        funding.append({"id": f"fund:{key}:{rk}", "need_id": need_id, "observation_type": "procurement_estimate",
                        "as_stated": r["anticipated_total_value"], "amount_low_usd": low, "amount_high_usd": high,
                        "fiscal_year": r["award_fy"], "period": r["award_quarter"], "evidence_id": evidence_id(r)})
        for token in contract_tokens(r["existing_contract_number"]):
            j = contract_targets.get((r["row_number"], token))
            refs.append({"id": f"pref:{key}:{rk}:{token}", "need_id": need_id, "identifier": token, "identifier_type": "piid",
                         "as_stated": r["existing_contract_number"], "resolved_in_fpds": "yes" if j and j["target_id"] else "no",
                         "evidence_ref": j["evidence_ref"] if j else ""})
    refs.sort(key=lambda x: (x["need_id"], x["identifier"]))
    return {"needs": needs, "need_requirements": reqs, "funding_observations": funding, "procurement_refs": refs, "evidence": evidence}


# ---------------------------------------------------------------- release matching

MATCH_MIN_RATIO = 0.85  # below this the two titles are different requirements, not a reword


def norm_title(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def office_code(r: dict) -> str:
    return (r["office_code_string"] or "").split(" - ")[0].strip().upper()


# Strongest signal first. Each entry is (basis, confidence, why, key function). A stage
# claims a pair only when the key hits exactly one row on each side; anything else is
# left for the next stage and, if nothing later resolves it, reported as ambiguous.
MATCH_STAGES = [
    ("pid", "confirmed", "same PID number in both releases",
     lambda r: [r["pid"]] if r["pid"] else []),
    ("title+office", "confirmed", "same requirement title under the same office code",
     lambda r: [norm_title(r["requirement_title"]) + "|" + office_code(r)] if norm_title(r["requirement_title"]) else []),
    ("office+incumbent", "confirmed", "same incumbent contract number under the same office code",
     lambda r: [office_code(r) + "|" + t for t in contract_tokens(r["existing_contract_number"])]),
]


def pair_releases(old_rows: list[dict], new_rows: list[dict]) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Follow the same requirement from one release to the next.

    No single key does this. The June 2024 release has no PID column at all, and PIDs are
    not stable where they exist: 31 of the 2023 export's 643 PIDs reappear in June 2025.
    So the stages run strongest first - PID, then exact title under the same office, then
    the incumbent contract number under the same office - and each one only claims a pair
    it can make 1:1. What survives all three gets one greedy pass of title similarity
    within the office, which produces candidates rather than matches: a reworded title is
    a judgement, so the score and the earlier wording travel with the row for a reviewer
    to accept or reject. A key that matched several rows and was never resolved is
    reported as `ambiguous` with the counts that made it so, not silently dropped.
    """
    pairs: list[dict] = []
    contested: list[dict] = []
    left_old, left_new = list(old_rows), list(new_rows)
    for basis, confidence, why, key_of in MATCH_STAGES:
        index_old: dict[str, list[dict]] = defaultdict(list)
        index_new: dict[str, list[dict]] = defaultdict(list)
        for r in left_old:
            for k in key_of(r):
                index_old[k].append(r)
        for r in left_new:
            for k in key_of(r):
                index_new[k].append(r)
        taken_old, taken_new = set(), set()
        for k in sorted(set(index_old) & set(index_new)):
            olds, news = index_old[k], index_new[k]
            if len(olds) == 1 and len(news) == 1:
                pairs.append({"old": olds[0], "new": news[0], "basis": basis, "confidence": confidence, "reason": why})
                taken_old.add(olds[0]["row_number"])
                taken_new.add(news[0]["row_number"])
            else:
                contested.append({"key": k, "basis": basis, "olds": olds, "news": news,
                                  "reason": f"{why}, but the key matches {len(olds)} earlier and {len(news)} later rows"})
        left_old = [r for r in left_old if r["row_number"] not in taken_old]
        left_new = [r for r in left_new if r["row_number"] not in taken_new]

    by_office: dict[str, list[dict]] = defaultdict(list)
    for r in left_new:
        by_office[office_code(r)].append(r)
    scored = []
    for r in left_old:
        for s in by_office.get(office_code(r), ()):
            ratio = SequenceMatcher(None, norm_title(r["requirement_title"]), norm_title(s["requirement_title"])).ratio()
            if ratio >= MATCH_MIN_RATIO:
                scored.append((round(ratio, 4), r, s))
    # Best score first, then row order, so the pass is greedy but deterministic.
    scored.sort(key=lambda x: (-x[0], x[1]["row_number"], x[2]["row_number"]))
    taken_old, taken_new = set(), set()
    for ratio, r, s in scored:
        if r["row_number"] in taken_old or s["row_number"] in taken_new:
            continue
        pairs.append({"old": r, "new": s, "basis": "title~office", "confidence": "candidate",
                      "reason": f'titles {ratio:.2f} alike under office {office_code(r)}; earlier row read "{r["requirement_title"][:70]}"'})
        taken_old.add(r["row_number"])
        taken_new.add(s["row_number"])
    left_old = [r for r in left_old if r["row_number"] not in taken_old]
    left_new = [r for r in left_new if r["row_number"] not in taken_new]
    return pairs, contested, left_old, left_new


# ---------------------------------------------------------------- release diff

def diff_releases(old_rows: list[dict], new_rows: list[dict]) -> tuple[list[dict], str]:
    """Added, removed, changed and candidate records between two releases, from `pair_releases`."""
    pairs, contested, only_old, only_new = pair_releases(old_rows, new_rows)
    matched_old = {p["old"]["row_number"] for p in pairs}
    matched_new = {p["new"]["row_number"] for p in pairs}

    def row(change, key, basis, confidence, reason, field="", old_value="", new_value="", old_row="", new_row="", office=""):
        return {"change": change, "key": key, "key_method": basis, "confidence": confidence, "field": field,
                "old_value": old_value, "new_value": new_value, "old_row": old_row, "new_row": new_row,
                "office": office, "reason": reason}

    out = []
    for c in contested:
        live_old = [r for r in c["olds"] if r["row_number"] not in matched_old]
        live_new = [r for r in c["news"] if r["row_number"] not in matched_new]
        if not live_old and not live_new:
            continue  # a later stage resolved every row this key touched
        out.append(row("ambiguous", c["key"], c["basis"], "candidate", c["reason"],
                       old_value=f"{len(c['olds'])} rows", new_value=f"{len(c['news'])} rows",
                       old_row=";".join(str(r["row_number"]) for r in c["olds"]),
                       new_row=";".join(str(r["row_number"]) for r in c["news"]),
                       office=office_code(c["news"][0] if c["news"] else c["olds"][0])))
    for p in pairs:
        o, n = p["old"], p["new"]
        key = n["pid"] or o["pid"] or f"row {o['row_number']}->{n['row_number']}"
        changed = [f for f in TRACKED if o[f] != n[f]]
        common = dict(key=key, basis=p["basis"], confidence=p["confidence"], reason=p["reason"],
                      old_row=o["row_number"], new_row=n["row_number"], office=office_code(n))
        if not changed:
            out.append(row("unchanged", **common))
        for field in changed:
            out.append(row("changed", field=field, old_value=o[field][:120], new_value=n[field][:120], **common))
    for r in only_old:
        out.append(row("removed", r["pid"] or f"row {r['row_number']}", "", "confirmed",
                       "no PID, title, incumbent contract or similar title in the later release",
                       old_value=r["requirement_title"][:120], old_row=r["row_number"], office=office_code(r)))
    for r in only_new:
        out.append(row("added", r["pid"] or f"row {r['row_number']}", "", "confirmed",
                       "no PID, title, incumbent contract or similar title in the earlier release",
                       new_value=r["requirement_title"][:120], new_row=r["row_number"], office=office_code(r)))
    out.sort(key=lambda x: (x["change"], str(x["old_row"]).zfill(6), str(x["new_row"]).zfill(6), x["field"]))
    confirmed = sum(1 for p in pairs if p["confidence"] == "confirmed")
    method = (f"staged: {', '.join(s[0] for s in MATCH_STAGES)}, then title similarity >= {MATCH_MIN_RATIO} "
              f"within the office ({confirmed} matched, {len(pairs) - confirmed} candidates)")
    return out, method


# ---------------------------------------------------------------- outputs

def write_csv(path: Path, rows: list[dict]) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(buffer.getvalue(), encoding="utf-8")


def reconciliation(release: dict, rows, classified, joins, diff_note: str) -> str:
    decisions = Counter(c["include_decision"] for c in classified)
    reasons = Counter((c["include_decision"], c["reason"]) for c in classified)
    unresolved = sorted({c["office_code"] for c in classified if c["include_decision"] == "unresolved"})
    per_office = Counter(c["office_id"] for c in classified if c["include_decision"] == "included")
    same = Counter((norm_title(r["requirement_title"]), office_code(r)) for r in rows if norm_title(r["requirement_title"]))
    shared = sorted(k for k, v in same.items() if v > 1)
    # Whether the release *has* a PID column, not whether every raw row filled one.
    # Section headers and blank continuation rows leave it empty, so `all` reported
    # the 2023 release as having no PID column while all 127 of its included rows
    # carry one. `diff` below already asks the question this way.
    pid_rows = sum(1 for r in rows if r["pid"])
    has_pid = pid_rows > 0
    key_note = (f"PID, where present ({pid_rows} of {len(rows)} raw rows); a row without one is its own record (release and row number)"
                if has_pid else "the row itself, as release and row number (this release has no PID column). No two rows are merged at import")
    lines = [f"# Reconciliation - {release['key']}", "", f"Sheet `{SHEET}`, header on Excel row {HEADER_ROW}, data rows {rows[0]['row_number']}-{rows[-1]['row_number']}.",
             f"Record key: {key_note}.",
             "", "## Rows", "", "| Decision | Rows |", "| --- | --- |", f"| raw | {len(rows)} |"]
    lines += [f"| {d} | {decisions.get(d, 0)} |" for d in ("included", "excluded", "unresolved")]
    lines += ["", f"Sum of decisions: {sum(decisions.values())} (equals raw: {'yes' if sum(decisions.values()) == len(rows) else 'NO'}).", "",
              "## Reasons", "", "| Decision | Reason | Rows |", "| --- | --- | --- |"]
    lines += [f"| {d} | {reason} | {n} |" for (d, reason), n in sorted(reasons.items(), key=lambda kv: (kv[0][0], -kv[1], kv[0][1]))]
    lines += ["", "## Included rows per office", "", "| Office | Rows |", "| --- | --- |"]
    lines += [f"| {o} | {n} |" for o, n in sorted(per_office.items())]
    lines += ["", "## Unresolved codes", "", ", ".join(f"`{u}`" for u in unresolved) or "none", "",
              "## Rows sharing a title and an office", "",
              "Nothing is marked duplicate at import: a row is a source record until a reviewer resolves its identity. "
              "Rows that repeat a title under one office code are listed with what tells them apart (description, value, "
              "award window), so the reviewer sees what the spreadsheet actually says. Across releases the matcher reports "
              "such a key as a candidate rather than choosing a row.", ""]
    if not shared:
        lines.append("No two rows share a title under one office code in this release.")
    for title, office in shared:
        group = [r for r in rows if (norm_title(r["requirement_title"]), office_code(r)) == (title, office)]
        lines.append(f"- {group[0]['requirement_title'][:70]} ({office}), {len(group)} rows:")
        for r in group:
            detail = " / ".join(line.strip() for line in r["requirement_description"].splitlines()
                                if line.strip() and norm_title(line) != norm_title(r["requirement_title"]))
            lines.append(f"  - row {r['row_number']}: {detail[:90] or 'no description beyond the title'} | {r['anticipated_total_value'] or 'no value'} | "
                         f"award {r['award_fy']} {r['award_quarter']}".rstrip())
    lines += ["", "## Joins (included rows only)", "", "| Join | Lines | Matched | Unmatched | Not collected |", "| --- | --- | --- | --- | --- |"]
    for name in ("office", "existing_contract", "notice", "contact"):
        group = [j for j in joins if j["join_type"] == name]
        matched = sum(1 for j in group if j["target_id"])
        pending = sum(1 for j in group if "not collected" in j["note"])
        lines.append(f"| {name} | {len(group)} | {matched} | {len(group) - matched - pending} | {pending} |")
    lines += ["", "Explicit joins: office code through the alias table, contract number found in FPDS, notice text containing the PID or contract "
              "number, POC name matching a contact observation for the same office. Inferred joins: forecast row tied to an award through an "
              "attribution example, or a notice that only cites a shared vehicle. A shared vehicle (SeaPort-NxG IDV, SEWP, GSA schedule) alone is never a join."]
    if release["key"] != JOINS_COLLECTED_FOR:
        lines += ["", f"FPDS and SAM.gov lookups were collected for {JOINS_COLLECTED_FOR} only; lines marked 'not collected' here are honest gaps, "
                  "not misses. Contact observations were built from the 2025 release, so older rows show no contact match."]
    lines += ["", "## Releases", "", diff_note, ""]
    return "\n".join(lines)


def build() -> int:
    manifest = manifest_rows()
    packages = []
    for release in RELEASES:
        source = saved(manifest, lambda m, rel=release: rel["match"] in m.get("url", "") and m.get("mime", "").endswith("sheet"))
        if source is None:
            print(f"{release['key']}: spreadsheet bytes not found under data/raw; skipped", file=sys.stderr)
            continue
        meta, rows = read_sheet(ROOT / source["path"], release["key"])
        release_date = meta.get("Release Date", "")[:10] if re.match(r"\d{4}-\d{2}-\d{2}", meta.get("Release Date", "")) else release["release_date"]
        packages.append((release, source, meta, rows, release_date))
    if not packages:
        return 1
    earlier: list[tuple[dict, list[dict]]] = []
    for release, source, meta, rows, release_date in packages:
        pack = PACK_BASE / release["key"]
        pack.mkdir(parents=True, exist_ok=True)
        (pack / "layers").mkdir(exist_ok=True)
        classified = classify(rows)
        joins = build_joins(rows, classified, manifest)
        write_csv(pack / "rows_raw.csv", rows)
        write_csv(pack / "rows_classified.csv", classified)
        write_csv(pack / "joins.csv", joins)
        for name, table in layers(rows, classified, joins, source["sha256"], release, release_date).items():
            if table:
                write_csv(pack / "layers" / f"{name}.csv", table)
        notes = []
        for prev_release, prev_rows in earlier:
            changes, method = diff_releases(prev_rows, rows)
            name = f"diff_{prev_release['key']}_{release['key']}.csv"
            if changes:
                write_csv(pack / name, changes)
            counts = Counter(ch["change"] for ch in changes)
            paired = {ch["key"] for ch in changes if ch["change"] in ("unchanged", "changed")}
            candidates = {ch["key"] for ch in changes if ch["change"] in ("unchanged", "changed") and ch["confidence"] == "candidate"}
            notes.append(f"Compared with `{prev_release['key']}` ({method}): {len(paired)} records followed across the releases, "
                         f"{len(candidates)} of them candidates a reviewer still has to accept; {counts.get('changed', 0)} field changes on "
                         f"{len({ch['key'] for ch in changes if ch['change'] == 'changed'})} of them; {counts.get('added', 0)} added, {counts.get('removed', 0)} removed, "
                         f"{counts.get('ambiguous', 0)} key{'' if counts.get('ambiguous', 0) == 1 else 's'} left ambiguous. Every row carries its match basis and the reasoning in `{name}`.")
        diff_note = " ".join(notes) + " Every release is kept as its own package." if notes else "Earliest saved release; nothing to diff against."
        (pack / "reconciliation.md").write_text(reconciliation(release, rows, classified, joins, diff_note), encoding="utf-8")
        outputs = {p.relative_to(pack).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(pack.rglob("*")) if p.is_file() and p.name != "SOURCE.json" and not p.name.startswith("._")}
        info = {"release_key": release["key"], "activity": meta.get("Activity Name", ""), "release_date": release_date,
                "release_date_as_written": meta.get("Release Date", ""), "release_note": release["release_note"],
                "source_url": source["url"], "fetched_from": source.get("fetched_from", ""), "method": source["method"],
                "wayback_timestamp": source.get("wayback_timestamp", ""), "retrieved_at": source["retrieved_at"],
                "sha256": source["sha256"], "size": source["size"], "raw_path": source["path"], "sheet": SHEET, "header_row": HEADER_ROW,
                "refetch": f"python research/tools/fetch.py '{source['url']}' --wayback {source.get('wayback_timestamp', '')}",
                "regenerate": "python research/tools/lrae_package.py build", "record_key": "pid, or the row itself (release key and row number) when the row has none; nothing is merged at import",
                "joins_collected": release["key"] == JOINS_COLLECTED_FOR, "outputs": outputs}
        (pack / "SOURCE.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(release["key"], release_date, len(rows), "rows;", Counter(c["include_decision"] for c in classified))
        earlier.append((release, rows))
    return 0


def collect(limit: int) -> int:
    manifest = manifest_rows()
    release = next(r for r in RELEASES if r["key"] == JOINS_COLLECTED_FOR)
    source = saved(manifest, lambda m: release["match"] in m.get("url", "") and m.get("mime", "").endswith("sheet"))
    _, rows = read_sheet(ROOT / source["path"], release["key"])
    included = {c["row_number"] for c in classify(rows) if c["include_decision"] == "included"}
    wanted: list[tuple[str, str]] = []
    for r in rows:
        if r["row_number"] not in included:
            continue
        tokens = contract_tokens(r["existing_contract_number"])
        wanted += [(FPDS.format(piid=t), f"LRAE join: FPDS search for existing contract {t} (row {r['row_number']})") for t in tokens]
        wanted += [(sgs_url(n, a), f"LRAE join: SAM.gov search for {n} (row {r['row_number']})") for n in (r["pid"], *tokens) if n for a in ("false", "true")]
    have = {m["url"] for m in manifest if m.get("status") == 200 and m.get("path")}
    todo = []
    for url, note in wanted:
        if url not in have and url not in {u for u, _ in todo}:
            todo.append((url, note))
    print(f"{len(todo)} lookups to collect")
    done = 0
    with MANIFEST.open("a", encoding="utf-8") as handle:
        for url, note in todo[:limit]:
            row = fetch(url, "direct", None, note)
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()
            done += 1
            print(row.get("status"), row.get("size"), url[:110])
            time.sleep(1.0)
    print(f"collected {done}")
    return 0


def selfcheck() -> int:
    blank = {c: "" for c in COLUMNS}

    def r(number, title, office, pid="", contract="", value="No Range Specified"):
        return {**blank, "sheet": SHEET, "row_number": number, "requirement_title": title, "pid": pid,
                "office_code_string": f"{office} - {office} - NAVWAR", "existing_contract_number": contract,
                "anticipated_total_value": value}

    # A PID carries a row when both releases have one.
    pairs, _, _, _ = pair_releases([r(1, "Alpha", "PMW-160", pid="N00039-23-RFPREQ-PMW-160-0001")],
                                   [r(9, "Alpha renamed", "PMW-160", pid="N00039-23-RFPREQ-PMW-160-0001")])
    assert [(p["basis"], p["confidence"]) for p in pairs] == [("pid", "confirmed")]

    # The release with no PID column still follows on title, then on the incumbent contract.
    pairs, _, _, _ = pair_releases([r(1, "Alpha", "PMW-160"), r(2, "Beta", "PMW-770", contract="N0003920D0061")],
                                   [r(9, "Alpha", "PMW-160"), r(8, "Beta, restructured buy", "PMW-770", contract="N0003920D0061")])
    assert sorted(p["basis"] for p in pairs) == ["office+incumbent", "title+office"]
    assert all(p["confidence"] == "confirmed" for p in pairs)

    # A reworded title is a candidate, not a match, and the reasoning travels with it.
    pairs, _, _, _ = pair_releases([r(1, "Shore Network Modernisation Support Services", "PMW-205")],
                                   [r(9, "Shore Network Modernization Support Services", "PMW-205")])
    assert len(pairs) == 1 and pairs[0]["basis"] == "title~office"
    assert pairs[0]["confidence"] == "candidate" and "alike under office PMW-205" in pairs[0]["reason"]

    # Different offices are never guessed at, however close the titles read.
    pairs, _, only_old, only_new = pair_releases([r(1, "Network Support Services", "PMW-205")],
                                                 [r(9, "Network Support Services", "PMW-160")])
    assert not pairs and len(only_old) == 1 and len(only_new) == 1

    # One key, several rows: kept as a candidate with the counts, never silently dropped.
    changes, _ = diff_releases([r(1, "Alpha", "PMW-160", contract="N0003920D0061"),
                                r(2, "Alpha II", "PMW-160", contract="N0003920D0061")],
                               [r(9, "Gamma", "PMW-160", contract="N0003920D0061")])
    ambiguous = [c for c in changes if c["change"] == "ambiguous"]
    assert len(ambiguous) == 1, ambiguous
    assert ambiguous[0]["confidence"] == "candidate"
    assert "2 earlier and 1 later rows" in ambiguous[0]["reason"]

    # A later stage that resolves every contested row withdraws the ambiguity.
    changes, _ = diff_releases([r(1, "Alpha", "PMW-160", contract="N0003920D0061"),
                                r(2, "Beta", "PMW-160", contract="N0003920D0061")],
                               [r(9, "Alpha", "PMW-160", contract="N0003920D0061"),
                                r(8, "Beta", "PMW-160", contract="N0003920D0061")])
    assert not [c for c in changes if c["change"] == "ambiguous"]
    assert {c["change"] for c in changes} == {"unchanged"}

    # Two rows with one title under one office are two records. The June 2024 release
    # lists five "Order to Contract #N0003922D4001" rows at PMA/PMW-101 describing
    # different work; neither is a duplicate of the other.
    twins = [dict(r(406, "Order to Contract #N0003922D4001", "PMA/PMW-101"), release="lrae_navwar_2024-06", requirement_description="Lot 7 DO#24F4014"),
             dict(r(408, "Order to Contract #N0003922D4001", "PMA/PMW-101"), release="lrae_navwar_2024-06", requirement_description="BU1 SRU Destruction")]
    assert len({record_key(t) for t in twins}) == 2
    assert [c["include_decision"] for c in classify(twins)] == ["included", "included"]
    # The same row number in another release is another record.
    assert record_key(dict(twins[0], release="lrae_navwar_2023-06")) != record_key(twins[0])
    # A PID on two rows is refused, not merged.
    try:
        classify([r(1, "Alpha", "PMW-160", pid="P1"), r(2, "Alpha, second lot", "PMW-160", pid="P1")])
    except ValueError as exc:
        assert "P1" in str(exc)
    else:
        raise AssertionError("a repeated PID must raise")

    # A tracked field that moved is reported once per field, against the pair.
    changes, _ = diff_releases([r(1, "Alpha", "PMW-160", pid="P1", value="$250M - $1B")],
                               [r(9, "Alpha", "PMW-160", pid="P1", value="> $1B+")])
    moved = [c for c in changes if c["change"] == "changed"]
    assert len(moved) == 1 and moved[0]["field"] == "anticipated_total_value"
    assert moved[0]["old_value"] == "$250M - $1B" and moved[0]["new_value"] == "> $1B+"

    print("selfcheck ok")
    return 0


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "build"
    if command in ("--selfcheck", "selfcheck"):
        sys.exit(selfcheck())
    if command == "collect":
        n = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 10_000
        sys.exit(collect(n))
    sys.exit(build())
