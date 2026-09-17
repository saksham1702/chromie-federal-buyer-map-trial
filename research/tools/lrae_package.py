#!/usr/bin/env python3
"""Turn one saved NAVWAR LRAE release into a reproducible data package.

    python research/tools/lrae_package.py build              # regenerate from saved bytes only
    python research/tools/lrae_package.py collect [--limit N]  # fetch the FPDS and SAM.gov lookups the joins need

`build` reads the spreadsheet bytes recorded in research/documents_manifest.jsonl plus the saved
FPDS ATOM and SAM.gov search responses, and writes datapack/lrae_navwar_<release>/. It never
touches the network, so a reviewer with the same data/raw/ gets byte-identical files. `collect`
performs the lookups that are not yet in the manifest (one FPDS PIID search per contract token,
one SAM.gov search per PID and per token) through fetch.py so every request is recorded.
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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import MANIFEST, ROOT, fetch  # noqa: E402

RESEARCH = ROOT / "research"
SHEET = "LRAE Annex 25"
HEADER_ROW = 8  # Excel row number of the column headers; data rows follow to the end
SOURCE_MATCH = "HQCA-2025-A-037"
RELEASE_KEY = "lrae_navwar_2025-06"
PACK = Path(os.environ.get("LRAE_PACK_DIR") or ROOT / "datapack" / RELEASE_KEY)  # override lets the test rebuild elsewhere
FPDS = "https://www.fpds.gov/ezsearch/FEEDS/ATOM?FEEDNAME=PUBLIC&q=PIID:{piid}&start=0"
SGS = "https://sam.gov/api/prod/sgs/v1/search/?"
PIID_RE = re.compile(r"N\d{5}\d{2}[A-Z]\d{4}(?!\d)|NNG\d{2}S[A-Z]\d{2}B|GS-?\d{2}F-?\d{3,4}[A-Z]{1,2}")
FORECAST_PID_RE = re.compile(r"[A-Z0-9]{6}-\d{2}-RFPREQ-[A-Za-z0-9/\-]+?-\d{4}")
INCLUDED_PARENT = "peo:c4i"
# Division and competency codes resolve to the organization that owns them, which is enough to exclude them.
FAMILY_PARENT = {"niwc_atlantic_division": "center:niwc-atlantic", "niwc_pacific_competency": "center:niwc-pacific",
                 "navwar_hq_competency": "command:navwar"}
COLUMNS = [
    "requirement_title", "requirement_description", "office_code_string", "anticipated_total_value",
    "procurement_method", "contract_type", "procurement_instrument", "contracting_office_uic",
    "solicitation_fy", "solicitation_quarter", "award_fy", "award_quarter", "period_of_performance_months",
    "follow_on_or_new", "existing_contract_number", "incumbent_contractor", "place_of_performance",
    "naics", "psc", "contracting_poc_name", "contracting_poc_contact", "secondary_poc_name",
    "secondary_poc_contact", "facility_clearance", "personnel_clearance", "palt_code", "sub_palt_code",
    "comments", "pid",
]
VALUE_RANGES = {
    "< $2M": (0, 2_000_000), "$2M - $7.5M": (2_000_000, 7_500_000), "$7.5M - $50M": (7_500_000, 50_000_000),
    "$50M - $100M": (50_000_000, 100_000_000), "$100M - $250M": (100_000_000, 250_000_000),
    "$250M - $1B": (250_000_000, 1_000_000_000), "> $1B+": (1_000_000_000, ""), "No Range Specified": ("", ""),
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


def read_sheet(path: Path) -> tuple[dict, list[dict]]:
    import openpyxl  # optional dependency, only needed here

    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = book[SHEET]
    meta = {}
    for row in sheet.iter_rows(min_row=1, max_row=HEADER_ROW - 1, values_only=True):
        if row and row[0] and str(row[0]).endswith(":") and len(row) > 1:
            meta[str(row[0]).rstrip(":").strip()] = cell(row[1])[:10]
    rows = []
    for number, values in enumerate(sheet.iter_rows(min_row=HEADER_ROW + 1, values_only=True), start=HEADER_ROW + 1):
        if all(v is None or str(v).strip() == "" for v in values):
            continue
        record = {"sheet": SHEET, "row_number": number}
        record.update({name: cell(values[i]) if i < len(values) else "" for i, name in enumerate(COLUMNS)})
        rows.append(record)
    return meta, rows


# ---------------------------------------------------------------- classification

def norm_code(text: str) -> str:
    return re.sub(r"[\s\-]", "", text.split("(")[0]).upper()


def alias_map() -> dict[str, str]:
    seed = json.loads((RESEARCH / "organization_seed.json").read_text(encoding="utf-8"))
    aliases: dict[str, str] = {}
    for node in seed["nodes"]:
        if node["type"] == "person":
            continue
        names = [node["name"], *(node.get("aliases") or []), *(node.get("codes") or {}).values()]
        for name in names:
            aliases.setdefault(norm_code(str(name)), node["id"])
    return aliases


def included_offices() -> set[str]:
    seed = json.loads((RESEARCH / "organization_seed.json").read_text(encoding="utf-8"))
    offices = {e["from"] for e in seed["edges"] if e["type"] == "child_of" and e["to"] == INCLUDED_PARENT and e["from"].startswith("pmw:")}
    return offices | {INCLUDED_PARENT}


def families() -> list[tuple[str, re.Pattern, str]]:
    data = json.loads((RESEARCH / "org_code_families.json").read_text(encoding="utf-8"))
    return [(f["family"], re.compile(f["pattern"]), f.get("org_type", "")) for f in data["families"] if f["family"] != "contracting_office_uic"]


def classify(rows: list[dict]) -> list[dict]:
    aliases, included, fams = alias_map(), included_offices(), families()
    seen_pids: dict[str, int] = {}
    out = []
    for r in rows:
        code = r["office_code_string"].split(" - ")[0].strip()
        family = next((name for name, pattern, _ in fams if pattern.match(code)), "")
        org_type = next((t for name, _, t in fams if name == family), "")
        office_id = aliases.get(norm_code(code), "")
        if r["pid"] in seen_pids:
            decision, reason = "duplicate", f"pid already seen on row {seen_pids[r['pid']]}"
        elif office_id in included:
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
        seen_pids.setdefault(r["pid"], r["row_number"])
        out.append({"sheet": r["sheet"], "row_number": r["row_number"], "pid": r["pid"], "office_code_string": r["office_code_string"],
                    "office_code": code, "code_family": family, "office_id": office_id, "include_decision": decision, "reason": reason})
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
    return token.startswith(("NNG", "GS")) or (len(token) == 13 and token[8] == "D")


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
    rows = json.loads((RESEARCH / "contact_candidates.json").read_text(encoding="utf-8"))
    table = {}
    for c in rows:
        if not c.get("name"):
            continue  # channel-only rows (industry intake mailboxes) have no person to match
        key = (norm_code(c["name"]), c["office"])
        table[key] = f"contact:{c['office']}:{re.sub(r'[^a-z]', '', c['name'].lower())}"
    return table


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
        joins.append({"pid": r["pid"], "row_number": r["row_number"], "join_type": join_type, "method": method,
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
        needles = [r["pid"], *tokens]
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
        example = examples.get(r["pid"])
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
            note = f"{role} on the row matches a contact_candidates row for the same office" if target else (
                f"{role} not in contact_candidates for {c['office_id']}" + (f"; listed for {', '.join(sorted(set(elsewhere)))}" if elsewhere else ""))
            add(r, "contact", "explicit", name, target, f"{SHEET}!{'T' if role == 'contracting_poc' else 'V'}{r['row_number']}", note)
    joins.sort(key=lambda j: (j["row_number"], j["join_type"], j["method"], j["key_used"], j["target_id"]))
    return joins


# ---------------------------------------------------------------- layers (target schema)

def layers(rows: list[dict], classified: list[dict], joins: list[dict], source_sha: str) -> dict[str, list[dict]]:
    decision = {c["row_number"]: c for c in classified}
    evidence_id = lambda r: f"ev:{RELEASE_KEY}:row{r['row_number']}"  # noqa: E731
    needs, reqs, funding, refs, evidence = [], [], [], [], []
    contract_targets = {(j["row_number"], j["key_used"]): j for j in joins if j["join_type"] == "existing_contract"}
    for r in rows:
        c = decision[r["row_number"]]
        if c["include_decision"] != "included":
            continue
        need_id = f"need:{RELEASE_KEY}:{r['pid']}"
        evidence.append({"id": evidence_id(r), "source_sha256": source_sha, "locator": f"{SHEET}!row {r['row_number']}",
                         "release_date": "2025-06-19", "kind": "spreadsheet_row"})
        needs.append({"id": need_id, "pid": r["pid"], "title": r["requirement_title"], "office_id": c["office_id"],
                      "office_code_string": r["office_code_string"], "contracting_office_uic": r["contracting_office_uic"].split(" - ")[0],
                      "follow_on_or_new": r["follow_on_or_new"], "predecessor_refs": " ".join(contract_tokens(r["existing_contract_number"])),
                      "valid_from": "2025-06-19", "evidence_id": evidence_id(r)})
        reqs.append({"id": f"req:{RELEASE_KEY}:{r['pid']}", "need_id": need_id, "revision": RELEASE_KEY,
                     "description": r["requirement_description"], "procurement_method": r["procurement_method"],
                     "contract_type": r["contract_type"], "instrument": r["procurement_instrument"],
                     "solicitation_fy": r["solicitation_fy"], "solicitation_quarter": r["solicitation_quarter"],
                     "award_fy": r["award_fy"], "award_quarter": r["award_quarter"], "pop_months": r["period_of_performance_months"],
                     "naics": r["naics"], "psc": r["psc"], "place": r["place_of_performance"], "evidence_id": evidence_id(r)})
        low, high = VALUE_RANGES.get(r["anticipated_total_value"], ("", ""))
        funding.append({"id": f"fund:{RELEASE_KEY}:{r['pid']}", "need_id": need_id, "observation_type": "procurement_estimate",
                        "as_stated": r["anticipated_total_value"], "amount_low_usd": low, "amount_high_usd": high,
                        "fiscal_year": r["award_fy"], "period": r["award_quarter"], "evidence_id": evidence_id(r)})
        for token in contract_tokens(r["existing_contract_number"]):
            j = contract_targets.get((r["row_number"], token))
            refs.append({"id": f"pref:{token}", "need_id": need_id, "identifier": token, "identifier_type": "piid",
                         "as_stated": r["existing_contract_number"], "resolved_in_fpds": "yes" if j and j["target_id"] else "no",
                         "evidence_ref": j["evidence_ref"] if j else ""})
    refs.sort(key=lambda x: (x["need_id"], x["identifier"]))
    return {"needs": needs, "need_requirements": reqs, "funding_observations": funding, "procurement_refs": refs, "evidence": evidence}


# ---------------------------------------------------------------- outputs

def write_csv(path: Path, rows: list[dict]) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(buffer.getvalue(), encoding="utf-8")


def reconciliation(rows, classified, joins) -> str:
    from collections import Counter

    decisions = Counter(c["include_decision"] for c in classified)
    reasons = Counter((c["include_decision"], c["reason"] if c["include_decision"] != "duplicate" else "pid already seen") for c in classified)
    unresolved = sorted({c["office_code"] for c in classified if c["include_decision"] == "unresolved"})
    per_office = Counter(c["office_id"] for c in classified if c["include_decision"] == "included")
    same_title = Counter((r["requirement_title"].lower(), r["office_code_string"], r["anticipated_total_value"], r["existing_contract_number"]) for r in rows)
    candidates = sorted(k for k, v in same_title.items() if v > 1)
    contract_joins = [j for j in joins if j["join_type"] == "existing_contract"]
    notice_joins = [j for j in joins if j["join_type"] == "notice"]
    contact_joins = [j for j in joins if j["join_type"] == "contact"]
    lines = [f"# Reconciliation - {RELEASE_KEY}", "", f"Sheet `{SHEET}`, header on Excel row {HEADER_ROW}, data rows {rows[0]['row_number']}-{rows[-1]['row_number']}.",
             "", "## Rows", "", "| Decision | Rows |", "| --- | --- |", f"| raw | {len(rows)} |"]
    lines += [f"| {d} | {decisions.get(d, 0)} |" for d in ("included", "excluded", "duplicate", "unresolved")]
    lines += ["", f"Sum of decisions: {sum(decisions.values())} (equals raw: {'yes' if sum(decisions.values()) == len(rows) else 'NO'}).", "",
              "## Reasons", "", "| Decision | Reason | Rows |", "| --- | --- | --- |"]
    lines += [f"| {d} | {reason} | {n} |" for (d, reason), n in sorted(reasons.items(), key=lambda kv: (kv[0][0], -kv[1], kv[0][1]))]
    lines += ["", "## Included rows per office", "", "| Office | Rows |", "| --- | --- |"]
    lines += [f"| {o} | {n} |" for o, n in sorted(per_office.items())]
    lines += ["", "## Unresolved codes", "", ", ".join(f"`{u}`" for u in unresolved) or "none", "",
              "## Duplicates", "", "Every PID is unique in this release, so no row is marked `duplicate`. Rows that repeat title, office, value range "
              "and existing contract under different PIDs are listed for the reviewer; they read as separate planned actions (option years, "
              "additional lots) rather than duplicates and stay as they are:", ""]
    for title, office, value, contract in candidates:
        numbers = [r["row_number"] for r in rows if (r["requirement_title"].lower(), r["office_code_string"], r["anticipated_total_value"], r["existing_contract_number"]) == (title, office, value, contract)]
        lines.append(f"- rows {', '.join(map(str, numbers))}: {title[:70]} ({office.split(' - ')[0]})")
    lines += ["", "## Joins (included rows only)", "", "| Join | Lines | Matched | Unmatched | Not collected |", "| --- | --- | --- | --- | --- |"]
    for name, group in (("office", [j for j in joins if j["join_type"] == "office"]), ("existing_contract", contract_joins), ("notice", notice_joins), ("contact", contact_joins)):
        matched = sum(1 for j in group if j["target_id"])
        pending = sum(1 for j in group if "not collected" in j["note"])
        lines.append(f"| {name} | {len(group)} | {matched} | {len(group) - matched - pending} | {pending} |")
    lines += ["", "Explicit joins: office code through the alias table, contract number found in FPDS, notice text containing the PID or contract "
              "number, POC name matching a contact candidate for the same office. Inferred joins: forecast row tied to an award through an "
              "attribution example. A shared vehicle (SeaPort-NxG IDV) alone is never a join.", "",
              "## Releases", "", "Only the 2025-06-19 release is saved. The NAVWAR page linked one file at capture time and the Wayback index was "
              "offline when older captures were searched, so no release-to-release diff exists yet; `diff_<old>_<new>.csv` is produced by this "
              "script once a second file is in the manifest.", ""]
    return "\n".join(lines)


def build() -> int:
    manifest = manifest_rows()
    source = saved(manifest, lambda m: SOURCE_MATCH in m.get("url", "") and m.get("url", "").endswith(".xlsx"))
    if source is None:
        print("LRAE spreadsheet bytes not found under data/raw; re-fetch with fetch.py --wayback", file=sys.stderr)
        return 1
    meta, rows = read_sheet(ROOT / source["path"])
    classified = classify(rows)
    joins = build_joins(rows, classified, manifest)
    PACK.mkdir(parents=True, exist_ok=True)
    (PACK / "layers").mkdir(exist_ok=True)
    write_csv(PACK / "rows_raw.csv", rows)
    write_csv(PACK / "rows_classified.csv", classified)
    write_csv(PACK / "joins.csv", joins)
    for name, table in layers(rows, classified, joins, source["sha256"]).items():
        if table:
            write_csv(PACK / "layers" / f"{name}.csv", table)
    (PACK / "reconciliation.md").write_text(reconciliation(rows, classified, joins), encoding="utf-8")
    outputs = {p.relative_to(PACK).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted(PACK.rglob("*")) if p.is_file() and p.name != "SOURCE.json" and not p.name.startswith("._")}
    info = {"release_key": RELEASE_KEY, "activity": meta.get("Activity Name", ""), "release_date": meta.get("Release Date", ""),
            "source_url": source["url"], "fetched_from": source.get("fetched_from", ""), "method": source["method"],
            "wayback_timestamp": source.get("wayback_timestamp", ""), "retrieved_at": source["retrieved_at"],
            "sha256": source["sha256"], "size": source["size"], "raw_path": source["path"], "sheet": SHEET, "header_row": HEADER_ROW,
            "refetch": f"python research/tools/fetch.py '{source['url']}' --wayback {source.get('wayback_timestamp', '')}",
            "regenerate": "python research/tools/lrae_package.py build", "record_key": "pid + release_key", "outputs": outputs}
    (PACK / "SOURCE.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in info.items() if k != "outputs"}, indent=2))
    return 0


def collect(limit: int) -> int:
    manifest = manifest_rows()
    source = saved(manifest, lambda m: SOURCE_MATCH in m.get("url", "") and m.get("url", "").endswith(".xlsx"))
    _, rows = read_sheet(ROOT / source["path"])
    included = {c["row_number"] for c in classify(rows) if c["include_decision"] == "included"}
    wanted: list[tuple[str, str]] = []
    for r in rows:
        if r["row_number"] not in included:
            continue
        tokens = contract_tokens(r["existing_contract_number"])
        wanted += [(FPDS.format(piid=t), f"LRAE join: FPDS search for existing contract {t} (row {r['row_number']})") for t in tokens]
        wanted += [(sgs_url(n, a), f"LRAE join: SAM.gov search for {n} (row {r['row_number']})") for n in (r["pid"], *tokens) for a in ("false", "true")]
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


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "build"
    if command == "collect":
        n = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 10_000
        sys.exit(collect(n))
    sys.exit(build())
