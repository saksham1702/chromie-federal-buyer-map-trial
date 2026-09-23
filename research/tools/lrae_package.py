#!/usr/bin/env python3
"""Turn the saved NAVWAR LRAE releases into reproducible data packages.

    python research/tools/lrae_package.py build              # regenerate every package from saved bytes only
    python research/tools/lrae_package.py collect [--limit N]  # fetch the FPDS and SAM.gov lookups the joins need

`build` reads the spreadsheet bytes recorded in research/sources/documents_manifest.jsonl plus the saved
FPDS ATOM and SAM.gov search responses, and writes one datapack/lrae_<activity>_<release>/ per saved
release, plus a diff between consecutive releases in the newer package. It never touches the
network, so a reviewer with the same data/raw/ gets byte-identical files. `collect` performs the
lookups that are not yet in the manifest (one FPDS PIID search per contract token, one SAM.gov
search per PID and per token) through fetch.py so every request is recorded.
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import os
import re
import sys
import tempfile
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
# Oldest first within an activity. `match` identifies the manifest row; `release_date` is the fallback when the
# sheet gives none; `scope` is which rows load: PEO C4I's offices only (the NAVWAR trial) or the whole activity.
# Releases are diffed and chained within one activity; a NAVSEA line is never a NAVWAR line's revision.
RELEASES = [
    {"key": "lrae_navwar_2023-06", "activity": "navwar", "match": "NAVWAR_LRAE_Report.xlsx", "release_date": "2023-06-20",
     "release_note": "sheet says '20 June 2023 / TDB'; the report was exported 2023-05-25 (Filters sheet)", "sheet": "LRAE Annex 25", "header_row": 8, "scope": "peo_c4i"},
    {"key": "lrae_navwar_2024-06", "activity": "navwar", "match": "HQCA-2024-A-094", "release_date": "2024-06-20",
     "release_note": '', "sheet": "LRAE Annex 25", "header_row": 8, "scope": "peo_c4i"},
    {"key": "lrae_navwar_2025-06", "activity": "navwar", "match": "HQCA-2025-A-037", "release_date": "2025-06-19",
     "release_note": '', "sheet": "LRAE Annex 25", "header_row": 8, "scope": "peo_c4i"},
    {"key": "lrae_navsea_2025-12", "activity": "navsea", "match": "LRAE-NAVSEA_Enterprise_LRAE_18DECEMBER2025", "release_date": "2025-12-18",
     "release_note": '', "sheet": "Annex 25 Template", "header_row": 8, "scope": "all"},
    {"key": "lrae_onr_2025-12", "activity": "onr", "match": "onr-and-nrl-long-range-acquisition-estimate", "release_date": "2025-12-19",
     "release_note": 'one workbook carries ONR and NRL as two sheets; each sheet is its own release', "sheet": "ONR", "header_row": 7, "scope": "all"},
    {"key": "lrae_nrl_2025-12", "activity": "nrl", "match": "onr-and-nrl-long-range-acquisition-estimate", "release_date": "2025-12-19",
     "release_note": 'one workbook carries ONR and NRL as two sheets; each sheet is its own release', "sheet": "NRL", "header_row": 7, "scope": "all"},
]
JOINS_COLLECTED_FOR = "lrae_navwar_2025-06"  # the only release whose FPDS and SAM.gov lookups were collected
FPDS = "https://www.fpds.gov/ezsearch/FEEDS/ATOM?FEEDNAME=PUBLIC&q=PIID:{piid}&start={start}"
FPDS_PAGE = 10  # actions a page; the feed runs oldest first and names the next page with a rel="next" link
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
    "\u2265 $50M\u2012<$100M": (50_000_000, 100_000_000),  # the NAVSEA sheet once writes the range with a >= and a figure dash
}


# ---------------------------------------------------------------- saved inputs

def manifest_rows() -> list[dict]:
    return [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]


def saved(rows: list[dict], predicate) -> dict | None:
    """Latest successful manifest row matching the predicate whose bytes are still on disk."""
    hits = [r for r in rows if r.get("status") == 200 and r.get("path") and predicate(r) and (ROOT / r["path"]).exists()]
    return hits[-1] if hits else None


def url_index(rows: list[dict]) -> dict[str, dict]:
    """`saved` for every URL at once: the latest successful row per URL whose bytes are on disk. For callers
    that look up thousands of URLs, where a scan of the manifest per lookup does not finish."""
    index: dict[str, dict] = {}
    for r in rows:
        if r.get("status") == 200 and r.get("path") and (ROOT / r["path"]).exists():
            index[r["url"]] = r
    return index


def cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def read_sheet(path: Path, release_key: str = "", sheet_name: str = SHEET, header_row: int = HEADER_ROW) -> tuple[dict, list[dict]]:
    import openpyxl  # optional dependency, only needed here

    # From bytes, not the path: openpyxl judges a file by its extension, and a saved download may have none.
    book = openpyxl.load_workbook(io.BytesIO(path.read_bytes()), read_only=True, data_only=True)
    sheet = book[sheet_name]
    meta = {}
    for row in sheet.iter_rows(min_row=1, max_row=header_row - 1, values_only=True):
        if row and row[0] and str(row[0]).endswith(":") and len(row) > 1:
            meta[str(row[0]).rstrip(":").strip()] = cell(row[1])
    header = next(sheet.iter_rows(min_row=header_row, max_row=header_row, values_only=True))
    fields = []
    for text in header:
        first = (str(text or "").split("\n")[0]).strip().lower()
        fields.append(next((name for prefix, name in HEADERS.items() if first.startswith(prefix)), None))
    rows = []
    for number, values in enumerate(sheet.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1):
        if all(v is None or str(v).strip() == "" for v in values):
            continue
        record = {"sheet": sheet_name, "row_number": number, "release": release_key}
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
    seed = json.loads((RESEARCH / "memory" / "organization_seed.json").read_text(encoding="utf-8"))
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
    seed = json.loads((RESEARCH / "memory" / "organization_seed.json").read_text(encoding="utf-8"))
    offices = {r["from"] for r in seed["relationships"] if r["type"] == "child_of" and r["to"] == INCLUDED_PARENT
               and r["from"].startswith("pmw:") and r["review_status"] != "retracted"}
    return offices | {INCLUDED_PARENT}


def families() -> list[tuple[str, re.Pattern, str]]:
    data = json.loads((RESEARCH / "memory" / "org_code_families.json").read_text(encoding="utf-8"))
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


def classify(rows: list[dict], scope: str = "peo_c4i") -> list[dict]:
    aliases, included, fams = alias_map(), included_offices(), families()
    out = []
    for r in rows:
        hit = classify_code(r["office_code_string"], aliases, fams)
        code, family, org_type, office_id = hit["code"], hit["family"], hit["org_type"], hit["office_id"]
        key = record_key(r)
        if scope == "all":
            # The whole activity loads. The office stays as the sheet wrote it until the memory knows it.
            decision, reason = "included", (f"activity-wide release; code resolves to {office_id}" if office_id
                                            else f"activity-wide release; code {code or 'blank'} names no office the memory knows")
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


# The coded fields FPDS states on an action, each with the description it carries; read only when asked (Buying DNA).
FPDS_CODED = ("typeOfSetAside", "extentCompeted", "numberOfOffersReceived", "principalNAICSCode", "productOrServiceCode",
              "typeOfContractPricing", "totalBaseAndAllOptionsValue", "totalObligatedAmount", "referencedIDVType",
              "referencedIDVMultipleOrSingle", "solicitationProcedures", "contractActionType", "ultimateParentUEI",
              "ultimateParentUEIName", "UEI")


def fpds_entries(body: bytes, width: int | None = 160, full: bool = False) -> list[dict]:
    """Every action on an FPDS ATOM page; `width` clips the description (None keeps it whole). `full` adds the coded
    fields as {"code", "description"} under `coded`; the tag must end at the name, so vendorUEI is not vendorUEIInformation."""
    text = body.decode("utf-8", "replace")
    entries = []
    for chunk in text.split("<entry>")[1:]:
        def tag(name: str) -> str:
            found = re.search(rf"<ns1:{name}[^>]*>([^<]*)<", chunk)
            return html.unescape(found.group(1)).strip() if found else ""  # the feed escapes & as &amp; inside vendor names

        def coded(name: str) -> dict:
            # An order states set-aside and offers on its vehicle: idvTypeOfSetAside, idvNumberOfOffersReceived.
            found = (re.search(rf"<ns1:{name}(?=[\s>])([^>]*)>([^<]*)<", chunk)
                     or re.search(rf"<ns1:idv{name[0].upper()}{name[1:]}(?=[\s>])([^>]*)>([^<]*)<", chunk))
            if not found:
                return {"code": "", "description": ""}
            desc = re.search(r'description="([^"]*)"', found.group(1))
            return {"code": found.group(2).strip(), "description": desc.group(1).strip() if desc else ""}
        idv = re.search(r"<ns1:referencedIDVID>.*?<ns1:PIID>([^<]*)<", chunk, re.S)  # the vehicle's id sits below its agency id
        office_name = re.search(r'<ns1:contractingOfficeID name="([^"]*)"', chunk)
        row = {"piid": tag("PIID"), "signed": tag("signedDate")[:10], "contracting_office": tag("contractingOfficeID"),
               "funding_office": tag("fundingRequestingOfficeID"), "vendor": tag("vendorName"),
               "idv": idv.group(1).strip() if idv else "", "description": tag("descriptionOfContractRequirement")[:width],
               "completion": tag("ultimateCompletionDate")[:10], "solicitation": tag("solicitationID"),
               "mod": tag("modNumber"), "reason": tag("reasonForModification"), "research": tag("research"),
               "contracting_office_name": html.unescape(office_name.group(1)).strip() if office_name else ""}
        if full:
            row["coded"] = {name: coded(name) for name in FPDS_CODED}
        entries.append(row)
    return entries


def fpds_url(piid: str, start: int = 0) -> str:
    return FPDS.format(piid=piid, start=start)


def fpds_history(manifest: list[dict] | dict[str, dict], piid: str) -> tuple[list[dict], list[dict], bool]:
    """The saved pages of one contract's FPDS history, oldest first, every action on them tagged with
    the page that carries it, and whether the last page is among them. Pages chain from `start=0` in
    steps of FPDS_PAGE; the history is complete when the newest saved page names no next one.
    `manifest` is the manifest rows or their `url_index`."""
    pages: list[dict] = []
    actions: list[dict] = []
    while True:
        url = fpds_url(piid, len(pages) * FPDS_PAGE)
        capture = manifest.get(url) if isinstance(manifest, dict) else saved(manifest, lambda m, u=url: m.get("url") == u)
        if capture is None:
            return pages, actions, False
        body = (ROOT / capture["path"]).read_bytes()
        pages.append(capture)
        actions += [dict(e, page=capture["sha256"]) for e in fpds_entries(body)]
        if b'rel="next"' not in body:
            return pages, actions, True


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
    rows = json.loads((RESEARCH / "memory" / "contact_observations.json").read_text(encoding="utf-8"))
    return {(norm_code(c["name"]), c["office_id_as_resolved"]): c["id"] for c in rows if c.get("name")}


def attribution_by_pid() -> dict[str, dict]:
    rows = json.loads((RESEARCH / "memory" / "attribution_examples.json").read_text(encoding="utf-8"))
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
    # Rows in this release citing each incumbent contract. A notice that cites a contract two
    # forecast rows share (a follow-on and a bridge, say) is joined to both as a candidate only.
    citers: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        if decision[r["row_number"]]["include_decision"] == "included":
            for token in contract_tokens(r["existing_contract_number"]):
                citers[token].append(str(r["row_number"]))

    def add(r, join_type, method, key, target, evidence, note):
        joins.append({"record_key": record_key(r), "pid": r["pid"], "row_number": r["row_number"], "join_type": join_type, "method": method,
                      "key_used": key, "target_id": target, "evidence_ref": evidence, "note": note})

    for r in rows:
        c = decision[r["row_number"]]
        if c["include_decision"] != "included":
            continue
        if c["office_id"]:
            add(r, "office", "explicit", c["office_code"], c["office_id"],
                f"{r['sheet']}!C{r['row_number']}; organization_seed.json alias table", "requirement-office code matched an alias")
        else:  # an activity-wide release keeps the row; the office stays as written until the memory knows it
            add(r, "office", "explicit", c["office_code"] or "(blank)", "", f"{r['sheet']}!C{r['row_number']}",
                "office string names no organization the memory knows")
        tokens = contract_tokens(r["existing_contract_number"])
        if not tokens and r["existing_contract_number"]:
            add(r, "existing_contract", "explicit", r["existing_contract_number"], "", f"{r['sheet']}!O{r['row_number']}",
                "no contract identifier pattern recognised in the cell")
        for token in tokens:
            pages, actions, complete = fpds_history(manifest, token)
            if not pages:
                add(r, "existing_contract", "explicit", token, "", "", "FPDS lookup not collected yet")
                continue
            mine = [e for e in actions if e["piid"] == token]
            if mine:
                e = mine[0]
                add(r, "existing_contract", "explicit", token, f"fpds:{token}", f"sha256:{pages[0]['sha256']}",
                    f"FPDS entries={len(mine)} on {len(pages)} page(s){'' if complete else ', history not saved to its last page'}; "
                    f"contracting {e['contracting_office']}; funding {e['funding_office']}; "
                    f"vendor {e['vendor']}; idv {e['idv'] or '-'}; first signed {e['signed']}")
            else:
                add(r, "existing_contract", "explicit", token, "", f"sha256:{pages[0]['sha256']}", "FPDS PIID search returned no entry")
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
                vehicle, shared_by = is_vehicle(needle), citers.get(needle, [])
                if vehicle:
                    why = "key is a shared vehicle (IDV or schedule); the notice cites the vehicle, which does not establish the same requirement; "
                elif len(shared_by) > 1:
                    why = (f"key is an incumbent contract that {len(shared_by)} forecast rows in this release cite (rows {', '.join(shared_by)}); "
                           "the notice cites the contract, which does not tell the rows apart; ")
                else:
                    why = "notice text contains the key; "
                for h in hits:
                    add(r, "notice", "explicit" if why.startswith("notice text") else "inferred", needle, f"sam:{h.get('_id', '')}", "; ".join(refs),
                        why + f"title {str(h.get('title', ''))[:80]}")
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
            add(r, "contact", "explicit", name, target, f"{r['sheet']}!{'T' if role == 'contracting_poc' else 'V'}{r['row_number']}", note)
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
        evidence.append({"id": evidence_id(r), "source_sha256": source_sha, "locator": f"{release['sheet']}!row {r['row_number']}",
                         "release_date": release_date, "kind": "spreadsheet_row"})
        needs.append({"id": need_id, "record_key": rk, "pid": r["pid"], "title": r["requirement_title"], "office_id": c["office_id"],
                      "office_code_string": r["office_code_string"], "contracting_office_uic": re.split(r"\s*[:-]\s*|\s+", r["contracting_office_uic"])[0].strip(),
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
    # A production follow-on and an engineering-support bridge share an office and an incumbent,
    # so this stage still claims a 1:1 pair but hands it to a reviewer.
    ("office+incumbent", "candidate", "same incumbent contract number under the same office code; a follow-on and a bridge can share both, so a reviewer decides",
     lambda r: [office_code(r) + "|" + t for t in contract_tokens(r["existing_contract_number"])]),
]


def pair_releases(old_rows: list[dict], new_rows: list[dict]) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Follow the same requirement from one release to the next.

    No single key does this. The June 2024 release has no PID column at all, and PIDs are
    not stable where they exist: 31 of the 2023 export's 643 PIDs reappear in June 2025.
    So the stages run strongest first - PID, then exact title under the same office, then
    the incumbent contract number under the same office - and each one only claims a pair
    it can make 1:1. The first two confirm a pair; the third only nominates one, because a
    production follow-on and an engineering-support bridge can share an office and an
    incumbent. What survives all three gets one greedy pass of title similarity within the
    office, which also produces candidates rather than matches: a reworded title is a
    judgement, so the score and the earlier wording travel with the row for a reviewer to
    accept or reject. A key that matched several rows and was never resolved is
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
            # One row can carry several keys in the same stage (a row citing two incumbent contract
            # numbers). A key claims only rows no earlier key of this stage took, so a row is paired
            # once, the way the stages themselves hand rows on.
            olds = [r for r in index_old[k] if r["row_number"] not in taken_old]
            news = [r for r in index_new[k] if r["row_number"] not in taken_new]
            if not olds or not news:
                continue
            if len(olds) == 1 and len(news) == 1:
                pairs.append({"old": olds[0], "new": news[0], "basis": basis, "confidence": confidence, "reason": why})
                taken_old.add(olds[0]["row_number"])
                taken_new.add(news[0]["row_number"])
            else:
                contested.append({"key": k, "basis": basis, "olds": olds, "news": news, "why": why,
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
        # Only the rows still unpaired after every stage are ambiguous. A row a later stage resolved is
        # reported as that pair, and a key with nothing left on one side is no longer a contest: its
        # remaining rows are added or removed rows and are reported as such.
        live_old = [r for r in c["olds"] if r["row_number"] not in matched_old]
        live_new = [r for r in c["news"] if r["row_number"] not in matched_new]
        if not live_old or not live_new:
            continue
        out.append(row("ambiguous", c["key"], c["basis"], "candidate",
                       f"{c['why']}, but the key matches {len(live_old)} earlier and {len(live_new)} later rows",
                       old_value=f"{len(live_old)} rows", new_value=f"{len(live_new)} rows",
                       old_row=";".join(str(r["row_number"]) for r in live_old),
                       new_row=";".join(str(r["row_number"]) for r in live_new),
                       office=office_code(live_new[0])))
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


# ---------------------------------------------------------------- accepted connections

DIFF_NAME = re.compile(r"diff_(lrae_[a-z]+_[\d-]+)_(lrae_[a-z]+_[\d-]+)\.csv")


def fold_map(pack_base: Path = PACK_BASE) -> tuple[dict[tuple[str, str], dict], list[str]]:
    """(release, record key) -> the key its chain loads under, for rows the release diffs tie with `confirmed`.

    A chain is the rows one requirement occupies across releases, joined by PID or by exact title
    under the same office code. A candidate pair (a similar title, a shared incumbent) never joins
    one. The chain loads under its PID, or under its earliest row key when no release gave it one,
    and every folded row carries its tie: the basis, the two rows and the diff that paired them.
    The loader writes that tie into the assertion it emits for the row, so a tool reading the
    database alone sees the full history. A chain that would join two different PIDs, or two rows
    of one release, is left unfolded and named in the second value: those are a reviewer's call.
    """
    packs = sorted(p for p in pack_base.glob("lrae_*") if p.is_dir() and (p / "rows_classified.csv").exists())
    keys: dict[tuple[str, str], str] = {}  # (release, row number) -> record key, included rows only
    for pack in packs:
        with (pack / "rows_classified.csv").open(newline="") as handle:
            for c in csv.DictReader(handle):
                if c["include_decision"] == "included":
                    keys[(pack.name, c["row_number"])] = c["record_key"]
    parent: dict[tuple[str, str], tuple[str, str]] = {}

    def find(node):
        while parent.setdefault(node, node) != node:
            node = parent[node]
        return node

    ties: dict[tuple[str, str], dict] = {}
    for pack in packs:
        for path in sorted(pack.glob("diff_*.csv")):
            m = DIFF_NAME.match(path.name)
            if not m:
                continue
            older, newer = m.groups()
            with path.open(newline="") as handle:
                for ch in csv.DictReader(handle):
                    if ch["change"] not in ("unchanged", "changed") or ch["confidence"] != "confirmed":
                        continue
                    a, b = (older, ch["old_row"]), (newer, ch["new_row"])
                    if a not in keys or b not in keys:
                        continue
                    parent[find(a)] = find(b)
                    tie = {"basis": ch["key_method"], "reason": ch["reason"],
                           "via": f"{older} row {ch['old_row']} -> {newer} row {ch['new_row']}, {path.name}"}
                    ties.setdefault(a, tie)
                    ties.setdefault(b, tie)
    chains: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for node in parent:
        chains[find(node)].append(node)
    folded, refused = {}, []
    for members in chains.values():
        if len(members) < 2:
            continue
        members.sort()
        pids = sorted({keys[m] for m in members if not keys[m].startswith("row:")})
        rows_of = ", ".join(f"{r} row {n}" for r, n in members)
        if len(pids) > 1:
            refused.append(f"{' | '.join(pids)}: one chain, two PIDs ({rows_of}); each row loads as its own record")
            continue
        if len({r for r, _ in members}) < len(members):
            refused.append(f"{pids[0] if pids else keys[members[0]]}: one chain, two rows of one release ({rows_of}); each row loads as its own record")
            continue
        canonical = pids[0] if pids else keys[members[0]]
        for m in members:
            if keys[m] != canonical:
                folded[(m[0], keys[m])] = {"key": canonical, **ties[m]}
    return folded, refused


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
    per_office = Counter(c["office_id"] or "(no office the memory knows)" for c in classified if c["include_decision"] == "included")
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
    lines = [f"# Reconciliation - {release['key']}", "", f"Sheet `{release['sheet']}`, header on Excel row {release['header_row']}, data rows {rows[0]['row_number']}-{rows[-1]['row_number']}.",
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
        meta, rows = read_sheet(ROOT / source["path"], release["key"], release["sheet"], release["header_row"])
        release_date = meta.get("Release Date", "")[:10] if re.match(r"\d{4}-\d{2}-\d{2}", meta.get("Release Date", "")) else release["release_date"]
        packages.append((release, source, meta, rows, release_date))
    if not packages:
        return 1
    earlier: dict[str, list[tuple[dict, list[dict]]]] = {}  # per activity: a release is diffed against its own predecessors
    for release, source, meta, rows, release_date in packages:
        pack = PACK_BASE / release["key"]
        pack.mkdir(parents=True, exist_ok=True)
        (pack / "layers").mkdir(exist_ok=True)
        classified = classify(rows, release["scope"])
        # Office joins come from the alias table for every release; FPDS, SAM.gov, contact and
        # attribution lookups were collected for the PEO C4I rows only and read "not collected" elsewhere.
        joins = build_joins(rows, classified, manifest)
        write_csv(pack / "rows_raw.csv", rows)
        write_csv(pack / "rows_classified.csv", classified)
        write_csv(pack / "joins.csv", joins)
        for name, table in layers(rows, classified, joins, source["sha256"], release, release_date).items():
            if table:
                write_csv(pack / "layers" / f"{name}.csv", table)
        notes = []
        for prev_release, prev_rows in earlier.get(release["activity"], []):
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
                "sha256": source["sha256"], "size": source["size"], "raw_path": source["path"], "sheet": release["sheet"],
                "header_row": release["header_row"], "scope": release["scope"],
                "refetch": f"python research/tools/fetch.py '{source['url']}' --wayback {source.get('wayback_timestamp', '')}",
                "regenerate": "python research/tools/lrae_package.py build", "record_key": "pid, or the row itself (release key and row number) when the row has none; nothing is merged at import",
                "joins_collected": release["key"] == JOINS_COLLECTED_FOR, "outputs": outputs}
        (pack / "SOURCE.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(release["key"], release_date, len(rows), "rows;", Counter(c["include_decision"] for c in classified))
        earlier.setdefault(release["activity"], []).append((release, rows))
    return 0


def collect(limit: int) -> int:
    manifest = manifest_rows()
    release = next(r for r in RELEASES if r["key"] == JOINS_COLLECTED_FOR)
    source = saved(manifest, lambda m: release["match"] in m.get("url", "") and m.get("mime", "").endswith("sheet"))
    _, rows = read_sheet(ROOT / source["path"], release["key"], release["sheet"], release["header_row"])
    included = {c["row_number"] for c in classify(rows, release["scope"]) if c["include_decision"] == "included"}
    wanted: list[tuple[str, str]] = []
    piids: set[str] = set()
    for r in rows:
        if r["row_number"] not in included:
            continue
        tokens = contract_tokens(r["existing_contract_number"])
        piids.update(tokens)
        wanted += [(fpds_url(t), f"LRAE join: FPDS search for existing contract {t} (row {r['row_number']})") for t in tokens]
        wanted += [(sgs_url(n, a), f"LRAE join: SAM.gov search for {n} (row {r['row_number']})") for n in (r["pid"], *tokens) if n for a in ("false", "true")]
    have = {m["url"] for m in manifest if m.get("status") == 200 and m.get("path")}
    todo = []
    for url, note in wanted:
        if url not in have and url not in {u for u, _ in todo}:
            todo.append((url, note))
    print(f"{len(todo)} lookups to collect")
    done = 0
    with MANIFEST.open("a", encoding="utf-8") as handle:
        def take(url: str, note: str) -> dict:
            row = fetch(url, "direct", None, note)
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()
            print(row.get("status"), row.get("size"), url[:110])
            time.sleep(1.0)
            return row

        for url, note in todo[:limit]:
            take(url, note)
            done += 1
        # The rest of each contract's history: the completion date a follow-on is timed against is
        # stated by the newest action, and the feed puts that on the last page.
        manifest = manifest_rows()
        for piid in sorted(piids):
            while done < limit:
                pages, _, complete = fpds_history(manifest, piid)
                if complete or not pages:
                    break
                row = take(fpds_url(piid, len(pages) * FPDS_PAGE),
                           f"LRAE join: FPDS history page {len(pages) + 1} for existing contract {piid}")
                done += 1
                if row.get("status") != 200:
                    break
                manifest.append(row)
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
    by_basis = {p["basis"]: p["confidence"] for p in pairs}
    assert by_basis["title+office"] == "confirmed"
    assert by_basis["office+incumbent"] == "candidate", "a follow-on and a bridge share office and incumbent; a reviewer decides"

    # Confirmed pairs fold into one chain under its PID; a candidate never joins one; two PIDs never fold.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        def pack(name, entries):
            (base / name).mkdir()
            write_csv(base / name / "rows_classified.csv",
                      [{"row_number": n, "record_key": k, "include_decision": d} for n, k, d in entries])

        pack("lrae_navwar_2023-06", [("409", "P1", "included"), ("5", "P7", "included")])
        pack("lrae_navwar_2024-06", [("47", "row:lrae_navwar_2024-06:47", "included"), ("48", "row:lrae_navwar_2024-06:48", "included"),
                                     ("9", "row:lrae_navwar_2024-06:9", "excluded")])
        pack("lrae_navwar_2025-06", [("108", "P1", "included"), ("6", "P8", "included")])
        cols = ["change", "key", "key_method", "confidence", "field", "old_value", "new_value", "old_row", "new_row", "office", "reason"]

        def ch(change, method, confidence, old, new):
            return {**{c: "" for c in cols}, "change": change, "key_method": method, "confidence": confidence,
                    "old_row": old, "new_row": new, "reason": "why"}

        write_csv(base / "lrae_navwar_2024-06" / "diff_lrae_navwar_2023-06_lrae_navwar_2024-06.csv",
                  [ch("changed", "title+office", "confirmed", "409", "47"), ch("unchanged", "office+incumbent", "candidate", "409", "48"),
                   ch("unchanged", "title+office", "confirmed", "5", "48")])
        write_csv(base / "lrae_navwar_2025-06" / "diff_lrae_navwar_2024-06_lrae_navwar_2025-06.csv",
                  [ch("unchanged", "title+office", "confirmed", "47", "108"), ch("unchanged", "title+office", "confirmed", "48", "6")])
        folded, refused = fold_map(base)
        tie = folded[("lrae_navwar_2024-06", "row:lrae_navwar_2024-06:47")]
        assert tie["key"] == "P1" and tie["basis"] == "title+office" and tie["via"].startswith("lrae_navwar_2023-06 row 409 -> lrae_navwar_2024-06 row 47")
        assert ("lrae_navwar_2023-06", "P1") not in folded, "the rows carrying the PID need no tie"
        assert ("lrae_navwar_2024-06", "row:lrae_navwar_2024-06:48") not in folded, "P7 -> row 48 -> P8 would join two PIDs"
        assert len(refused) == 1 and "P7 | P8" in refused[0], refused

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

    # A row citing two incumbent contract numbers carries two keys in one stage. It is paired once.
    pairs, _, _, _ = pair_releases([r(1, "Alpha", "PMW-160", contract="N0003920D0061, N0003921D0075")],
                                   [r(9, "Alpha follow-on", "PMW-160", contract="N0003920D0061, N0003921D0075")])
    assert len(pairs) == 1, pairs
    assert [(p["old"]["row_number"], p["new"]["row_number"]) for p in pairs] == [(1, 9)]

    # A row a later key or a later stage paired is not also reported inside an ambiguous group.
    changes, _ = diff_releases([r(1, "Alpha", "PMW-160", contract="N0003920D0061"),
                                r(2, "Beta", "PMW-160", contract="N0003920D0061")],
                               [r(9, "Alpha", "PMW-160", contract="N0003920D0061"),
                                r(8, "Gamma", "PMW-160", contract="N0003920D0061")])
    ambiguous = [c for c in changes if c["change"] == "ambiguous"]
    paired_rows = {(c["old_row"], c["new_row"]) for c in changes if c["change"] in ("unchanged", "changed")}
    assert ("1", "9") not in {(a["old_row"], a["new_row"]) for a in ambiguous}
    assert all("1" not in a["old_row"].split(";") and "9" not in a["new_row"].split(";") for a in ambiguous), ambiguous
    assert (1, 9) in {(int(o), int(n)) for o, n in paired_rows}, "the title still pairs Alpha across the releases"

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

    # A contract's FPDS history is read across its saved pages, oldest first, and is complete only
    # when the newest saved page names no next one.
    with tempfile.TemporaryDirectory() as tmp:
        def page(start: int, signed: str, more: bool) -> dict:
            body = f"<entry><ns1:PIID>P1</ns1:PIID><ns1:signedDate>{signed}</ns1:signedDate></entry>" + ('<link rel="next" href="x"/>' if more else "")
            path = Path(tmp) / f"p{start}"
            path.write_text(body, encoding="utf-8")
            return {"url": fpds_url("P1", start), "status": 200, "path": str(path), "sha256": f"sha{start}"}
        saved_pages = [page(0, "2020-01-01", True)]
        pages, actions, complete = fpds_history(saved_pages, "P1")
        assert (len(pages), complete, [a["signed"] for a in actions]) == (1, False, ["2020-01-01"])
        saved_pages.append(page(10, "2021-01-01", False))
        pages, actions, complete = fpds_history(saved_pages, "P1")
        assert (len(pages), complete, [a["page"] for a in actions]) == (2, True, ["sha0", "sha10"])
        assert fpds_history(saved_pages, "P2") == ([], [], False)

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
