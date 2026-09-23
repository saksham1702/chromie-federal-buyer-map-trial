"""Vendors resolved by their Unique Entity Identifier from the saved FPDS award pages: one vendor per UEI, every spelling
the feed used for it, its parent entity, and its awards by office. The record names a vendor as the feed spelled it on the
day, so DATA LINK SOLUTIONS L.L.C. and DATA LINK SOLUTIONS LLC are one vendor here and two strings there.

    python research/tools/vendors.py build [--check]      -> research/memory/vendors.json
    python research/tools/vendors.py resolve "Data Link Solutions"
    python research/tools/vendors.py --selfcheck
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from backtest import RESEARCH  # noqa: E402
from buying_dna import book  # noqa: E402

OUT = RESEARCH / "memory" / "vendors.json"


def resolve_entries(entries: dict[str, dict], as_of: str) -> dict:
    """Group the awards by UEI; a spelling belongs to the UEI it was seen with most often."""
    by_uei: dict[str, list[dict]] = defaultdict(list)
    unresolved = Counter()
    for e in entries.values():
        uei = e["coded"]["UEI"]["code"]
        if uei:
            by_uei[uei].append(e)
        elif e["vendor"]:
            unresolved[e["vendor"]] += 1
    vendors = []
    for uei, rows in by_uei.items():
        names = Counter(r["vendor"] for r in rows if r["vendor"])
        parents = Counter((r["coded"]["ultimateParentUEI"]["code"], r["coded"]["ultimateParentUEIName"]["code"]) for r in rows if r["coded"]["ultimateParentUEI"]["code"])
        parent_uei, parent_name = parents.most_common(1)[0][0] if parents else ("", "")
        signed = sorted(r["signed"] for r in rows if r["signed"])
        vendors.append({"uei": uei, "name": names.most_common(1)[0][0] if names else "", "spellings": sorted(names),
                        "parent_uei": parent_uei, "parent_name": parent_name, "awards": len(rows),
                        "first_signed": signed[0] if signed else "", "last_signed": signed[-1] if signed else "",
                        "live": sum(1 for r in rows if r["completion"] and r["completion"] > as_of),
                        "offices": dict(Counter(r["contracting_office"] for r in rows).most_common()),
                        "funding_offices": dict(Counter(r["funding_office"] for r in rows if r["funding_office"]).most_common(5))})
    vendors.sort(key=lambda v: (-v["awards"], v["uei"]))
    seen = Counter()
    for v in vendors:
        for s in v["spellings"]:
            seen[s] += 1
    spelling = {}
    for v in vendors:  # a spelling seen under two UEIs (a re-registration) points to the one with more awards, the first in the sort
        for s in v["spellings"]:
            spelling.setdefault(s, v["uei"])
    return {"as_of": as_of, "awards_read": len(entries), "vendors": vendors, "spelling_to_uei": spelling,
            "spellings_under_two_ueis": sorted(s for s, n in seen.items() if n > 1),
            "unresolved_spellings": dict(unresolved.most_common()),
            "summary": {"vendors": len(vendors), "with_two_or_more_spellings": sum(1 for v in vendors if len(v["spellings"]) > 1),
                        "with_a_parent": sum(1 for v in vendors if v["parent_uei"] and v["parent_uei"] != v["uei"]),
                        "awards_without_uei": sum(unresolved.values())}}


def load() -> dict:
    return json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}


def names_for(query: str, resolved: dict) -> list[str]:
    """Every spelling the feed used for the vendor a query names, or the query itself when nothing resolves."""
    q = query.lower()
    ueis = {u for s, u in resolved.get("spelling_to_uei", {}).items() if q in s.lower()}
    if not ueis:
        return [query]
    return sorted({s for v in resolved["vendors"] if v["uei"] in ueis for s in v["spellings"]})


def text(v: dict) -> str:
    lines = [f"{v['name']} (UEI {v['uei']}): {v['awards']} award(s) {v['first_signed']} to {v['last_signed']}, {v['live']} live",
             "spellings: " + "; ".join(v["spellings"]),
             "offices: " + ", ".join(f"{o} {n}" for o, n in v["offices"].items())]
    if v["funding_offices"]:
        lines.append("funding offices: " + ", ".join(f"{o} {n}" for o, n in v["funding_offices"].items()))
    if v["parent_uei"] and v["parent_uei"] != v["uei"]:
        lines.append(f"parent: {v['parent_name']} (UEI {v['parent_uei']})")
    return "\n".join(lines)


def build(argv: list[str]) -> int:
    check = "--check" in argv
    entries = book()
    as_of = max((e["signed"] for e in entries.values() if e["signed"]), default=date.today().isoformat())
    result = resolve_entries(entries, as_of)
    s = result["summary"]
    print(f"{result['awards_read']} award(s) read; {s['vendors']} vendor(s) by UEI, {s['with_two_or_more_spellings']} spelled two or more ways, "
          f"{s['with_a_parent']} under a parent entity; {s['awards_without_uei']} award(s) name a vendor without a UEI; "
          f"{len(result['spellings_under_two_ueis'])} spelling(s) seen under two UEIs")
    if check:
        saved = load()
        if saved != result:
            print("vendors.json differs from a fresh build; run without --check to regenerate", file=sys.stderr)
            return 1
        print("vendors.json matches a fresh build")
        return 0
    OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"-> {OUT.relative_to(RESEARCH.parent)}")
    return 0


def resolve(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: vendors.py resolve NAME", file=sys.stderr)
        return 2
    resolved = load()
    q = argv[0].lower()
    hits = [v for v in resolved.get("vendors", []) if any(q in s.lower() for s in v["spellings"])]
    if not hits:
        print(f"no vendor spelling contains {argv[0]!r}")
        return 1
    print("\n\n".join(text(v) for v in hits[:5]))
    return 0


def selfcheck() -> int:
    c = lambda uei, puei="", pname="": {"UEI": {"code": uei, "description": ""}, "ultimateParentUEI": {"code": puei, "description": ""},
                                          "ultimateParentUEIName": {"code": pname, "description": ""}}
    row = lambda piid, vendor, uei, signed, completion, office="N00039", **kw: {"piid": piid, "vendor": vendor, "signed": signed, "completion": completion,
                                                                              "contracting_office": office, "funding_office": kw.get("funding", ""), "coded": c(uei, **kw.get("parent", {}))}
    entries = {"A": row("A", "ACME & CO", "U1", "2024-01-01", "2027-01-01", parent={"puei": "P1", "pname": "ACME HOLDINGS"}),
               "B": row("B", "ACME AND CO", "U1", "2025-01-01", "2025-12-31", funding="PMW 1"),
               "C": row("C", "BETA LLC", "U2", "2023-05-05", "2024-05-05"),
               "D": row("D", "GAMMA INC", "", "2023-05-05", "2024-05-05")}
    r = resolve_entries(entries, "2026-09-21")
    v = r["vendors"][0]
    assert v["uei"] == "U1" and v["spellings"] == ["ACME & CO", "ACME AND CO"] and v["awards"] == 2 and v["live"] == 1 and v["parent_name"] == "ACME HOLDINGS", v
    assert v["funding_offices"] == {"PMW 1": 1} and r["spelling_to_uei"]["ACME AND CO"] == "U1" and r["unresolved_spellings"] == {"GAMMA INC": 1}
    assert r["summary"] == {"vendors": 2, "with_two_or_more_spellings": 1, "with_a_parent": 1, "awards_without_uei": 1}, r["summary"]
    assert names_for("acme", r) == ["ACME & CO", "ACME AND CO"] and names_for("nobody", r) == ["nobody"]
    assert "parent: ACME HOLDINGS" in text(v)
    print("vendors selfcheck ok")
    return 0


COMMANDS = {"build": build, "resolve": resolve}


def main(argv: list[str]) -> int:
    if argv[:1] == ["--selfcheck"]:
        return selfcheck()
    if not argv or argv[0] not in COMMANDS:
        print(__doc__, file=sys.stderr)
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
