#!/usr/bin/env python3
"""Coverage matrix and source status: which registered source covers each command and
family, with a stated reason wherever nothing does, and per registered source what was last collected.

The matrix is written by hand in research/sources/coverage_matrix.json because the corpus cannot say what it does not
hold; this tool refuses a matrix that names a source the registry lacks, a source that has collected nothing, an
empty cell without a reason from the closed list, or a grid with a hole. The status is computed: events per source
from the frozen corpus, documents per source from the manifest by host, the newest retrieval and its hash.

  python research/tools/coverage.py check      # validate the matrix, print the grid
  python research/tools/coverage.py status [--check]   # write research/sources/source_status.json, or fail if it would change
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest import CORPUS  # noqa: E402

RESEARCH = ROOT / "research"
MATRIX = RESEARCH / "sources" / "coverage_matrix.json"
STATUS = RESEARCH / "sources" / "source_status.json"
REGISTRY = RESEARCH / "sources" / "source_registry.json"
MANIFEST = RESEARCH / "sources" / "documents_manifest.jsonl"
REASONS = ("no_public_source", "blocked", "restricted", "not_started")
WAYBACK_RE = re.compile(r"https?://web\.archive\.org/web/\d+(?:id_)?/(https?://.*)")
# Hosts the registry's URLs do not show but that belong to a registered source: renamed domains and the portals a
# source is read through.
EXTRA_HOSTS = {"sbir_sttr_topics": ["www.dodsbirsttr.mil", "www.sbir.gov", "api.www.sbir.gov", "www.navysbir.com"],
               "news_articles_exa": ["api.gdeltproject.org"],
               "dod_contract_announcements": ["www.war.gov"],
               "dod_comptroller_budget_materials": ["comptroller.war.gov"]}
# Pages found through a search are filed under the search source by the note the fetch left, not by their host.
NOTE_KEYS = (("remarks watch", "conference_pages_exa"), ("news sweep", "news_articles_exa"), ("news watch", "news_articles_exa"),
             ("news search", "news_articles_exa"),
             ("exa search", "conference_pages_exa"), ("search", "conference_pages_exa"))


def registry() -> dict[str, dict]:
    return {r["source_key"]: r for r in json.loads(REGISTRY.read_text(encoding="utf-8"))}


def host(url: str) -> str:
    m = WAYBACK_RE.match(url or "")
    return urllib.parse.urlparse(m.group(1) if m else url or "").netloc


def hosts_by_key(reg: dict[str, dict]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for key, row in reg.items():
        for url in (row.get("official_url"), (row.get("inspected_example") or {}).get("url")):
            if url and host(url) and host(url) != "web.archive.org":
                out[key].add(host(url))
        out[key].update(EXTRA_HOSTS.get(key, ()))
    return out


def key_for(row: dict, by_host: dict[str, list[str]]) -> list[str]:
    """The registered sources a manifest row belongs to: by host first, then by the note that fetched it."""
    keys = by_host.get(host(row.get("url", "")), [])
    if keys:
        return keys
    note = (row.get("note") or "").lower()
    return [key for prefix, key in NOTE_KEYS if note.startswith(prefix)][:1]


def status() -> dict:
    reg = registry()
    by_host: dict[str, list[str]] = defaultdict(list)
    for key, hosts in hosts_by_key(reg).items():
        for h in hosts:
            by_host[h].append(key)
    out = {key: {"events": 0, "newest_event": "", "documents": 0, "last_seen": "", "last_hash": "", "hosts": sorted(hosts_by_key(reg)[key])} for key in reg}
    if CORPUS.exists():
        for e in json.loads(CORPUS.read_text(encoding="utf-8"))["events"]:
            slot = out.get(e["provider"])
            if slot is not None:
                slot["events"] += 1
                slot["newest_event"] = max(slot["newest_event"], e["date"])
    unregistered: Counter = Counter()
    rows = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]
    # A page first found by a search and later re-fetched through the hosted browser keeps the search's source.
    by_url = {r["url"]: key_for(r, by_host) for r in rows if key_for(r, by_host)}
    for row in rows:
        if row.get("status") != 200 or not row.get("sha256"):
            continue
        keys = key_for(row, by_host) or by_url.get(row.get("url", ""), [])
        if not keys:
            unregistered[host(row.get("url", ""))] += 1
        for key in keys:
            slot = out[key]
            slot["documents"] += 1
            if row["retrieved_at"] > slot["last_seen"]:
                slot["last_seen"], slot["last_hash"] = row["retrieved_at"], row["sha256"]
    return {"sources": out, "unregistered_hosts": dict(sorted(unregistered.items()))}


def problems(matrix: dict, stat: dict, reg: dict[str, dict]) -> list[str]:
    out = []
    grid = {(c["org"], c["family"]) for c in matrix["cells"]}
    for org in matrix["organizations"]:
        for family in matrix["families"]:
            if (org, family) not in grid:
                out.append(f"hole: {org} x {family}")
    if len(grid) != len(matrix["cells"]):
        out.append("a cell is listed twice")
    for c in matrix["cells"]:
        where = f"{c['org']} x {c['family']}"
        if c.get("org") not in matrix["organizations"] or c.get("family") not in matrix["families"]:
            out.append(f"{where}: outside the grid")
        if c.get("sources"):
            for key in c["sources"]:
                if key not in reg:
                    out.append(f"{where}: {key} is not in the registry")
                elif not (stat["sources"][key]["events"] or stat["sources"][key]["documents"]):
                    out.append(f"{where}: {key} has collected nothing")
            if "reason" in c:
                out.append(f"{where}: both sources and a reason")
        elif c.get("reason") not in REASONS or not c.get("note"):
            out.append(f"{where}: empty cell needs a reason from {REASONS} and a note")
    return out


def grid_text(matrix: dict, stat: dict) -> str:
    width = max(len(f) for f in matrix["families"])
    lines = [f"{'':{width}}  " + "  ".join(f"{o[:10]:>10}" for o in matrix["organizations"])]
    by = {(c["org"], c["family"]): c for c in matrix["cells"]}
    for family in matrix["families"]:
        row = []
        for org in matrix["organizations"]:
            c = by[(org, family)]
            row.append(f"{len(c['sources']):>10}" if c.get("sources") else f"{c['reason'][:10]:>10}")
        lines.append(f"{family:{width}}  " + "  ".join(row))
    lines.append("(a number is how many registered sources cover the cell; a word is why none does)")
    return "\n".join(lines)


def check(argv: list[str]) -> int:
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    stat, reg = status(), registry()
    found = problems(matrix, stat, reg)
    print(grid_text(matrix, stat))
    for p in found:
        print("  problem:", p)
    covered = sum(bool(c.get("sources")) for c in matrix["cells"])
    print(f"{covered} of {len(matrix['cells'])} cells covered; {len(stat['unregistered_hosts'])} unregistered host(s): {sorted(stat['unregistered_hosts'])}")
    return 1 if found else 0


def status_cmd(argv: list[str]) -> int:
    stat = status()
    text = json.dumps(stat, indent=1, sort_keys=True) + "\n"
    if "--check" in argv:
        if not STATUS.exists() or STATUS.read_text(encoding="utf-8") != text:
            print("source_status.json differs from a fresh build; run `coverage.py status` to regenerate", file=sys.stderr)
            return 1
        print("source_status.json matches a fresh build")
        return 0
    STATUS.write_text(text, encoding="utf-8")
    live = [k for k, s in stat["sources"].items() if s["documents"] or s["events"]]
    print(f"{len(live)} of {len(stat['sources'])} registered sources have collected something -> {STATUS.relative_to(ROOT)}")
    return 0


def selfcheck() -> int:
    reg = {"a": {"official_url": "https://a.example/x", "inspected_example": {"url": "https://web.archive.org/web/2020/https://a2.example/y"}},
           "b": {"official_url": "https://b.example/"}}
    assert hosts_by_key(reg) == {"a": {"a.example", "a2.example"}, "b": {"b.example"}}, hosts_by_key(reg)
    by_host = {"a.example": ["a"]}
    assert key_for({"url": "https://a.example/p"}, by_host) == ["a"]
    assert key_for({"url": "https://z.example/p", "note": "remarks watch: conference page"}, by_host) == ["conference_pages_exa"]
    assert key_for({"url": "https://z.example/p", "note": "live page via Browserbase"}, by_host) == []
    assert key_for({"url": "https://z.example/p", "note": "news search: PMW 770 program manager: headline"}, by_host) == ["news_articles_exa"]
    matrix = {"organizations": ["X"], "families": ["f", "g"],
              "cells": [{"org": "X", "family": "f", "sources": ["a"]}, {"org": "X", "family": "g", "reason": "blocked", "note": "why"}]}
    stat = {"sources": {"a": {"events": 1, "documents": 0}, "b": {"events": 0, "documents": 0}}}
    assert problems(matrix, stat, reg) == []
    bad = {**matrix, "cells": [{"org": "X", "family": "f", "sources": ["b", "zz"]}, {"org": "X", "family": "g", "reason": "tired"}]}
    found = problems(bad, stat, reg)
    assert len(found) == 3 and any("collected nothing" in p for p in found) and any("not in the registry" in p for p in found), found
    assert problems({**matrix, "cells": matrix["cells"][:1]}, stat, reg) == ["hole: X x g"]
    assert "blocked" in grid_text(matrix, stat)
    print("selfcheck ok")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] == "--selfcheck":
        return selfcheck()
    return {"check": check, "status": status_cmd}[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
