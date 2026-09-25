#!/usr/bin/env python3
"""Programs family: Navy SBIR/STTR topics from the DoD SBIR/STTR portal (DSIP).

Every SBIR host (sbir.gov, navysbir.com, dodsbirsttr.mil) answers this machine's address with 403 and the portal's
API refuses the hosted browser's request context too, so each API page is fetched from inside a loaded portal page
in a hosted US browser (Browserbase). The API honours the sort and ignores every filter, so the sweep reads all
components newest first and stops at the window start; Navy rows within the window keep their detail record. Every
page and detail is saved with its hash in the manifest and the rows are rebuilt from the saved files alone, so a
rerun without the network gives the same rows.

  python research/tools/sbir.py sweep --fetch [--since 2019-10-01] [--size 500] [--pages N]
  python research/tools/sbir.py build              # research/events/sbir_topics.json from the saved pages and details
  python research/tools/sbir.py show N241-032
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from browserbase_fetch import fail, save  # noqa: E402
from llm import env_value  # noqa: E402
from lrae_package import manifest_rows, saved  # noqa: E402

PORTAL = "https://www.dodsbirsttr.mil/topics-app/"
API = "https://www.dodsbirsttr.mil/topics/api/public/topics"
from agency import EVENTS, P, NOTE_TAG  # noqa: E402

OUT = EVENTS / "sbir_topics.json"
PROVIDER = "sbir_sttr_topics"
SINCE = "2019-10-01"  # FY2020 on, the study window
DEPARTMENT = P["agency"]["node"]
COMPONENT = P["sbir_component"]  # the portal's component column: NAVY, DARPA, ...
# The portal's `command` column against the organization memory; a command the memory lacks falls to the Department.
COMMANDS = P["sbir_commands"]
FETCH_JS = "async (u) => { const r = await fetch(u, {headers: {Accept: 'application/json'}}); return {s: r.status, t: await r.text()}; }"
TAG_RE = re.compile(r"<[^>]+>")


def page_url(page_no: int, size: int) -> str:
    param = urllib.parse.quote(json.dumps({"sortBy": "topicStartDate,desc"}))
    return f"{API}/search?searchParam={param}&size={size}&page={page_no}"


def detail_url(topic_id: str) -> str:
    return f"{API}/{topic_id}/details"


def ms_day(ms) -> str:
    """The portal prints epoch milliseconds; the day in UTC is the day it means."""
    if not ms or not str(ms).isdigit():
        return ""
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def strip_html(text) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", text or ""))).strip()


class Browser:
    """One hosted browser session with the portal loaded; the API is read from inside that page."""

    def __enter__(self):
        from browserbase import Browserbase
        from playwright.sync_api import sync_playwright
        key = env_value("BROWSERBASE_API_KEY")
        if not key:
            raise SystemExit("BROWSERBASE_API_KEY is not set")
        created = Browserbase(api_key=key).sessions.create(browser_settings={"recordSession": False}, api_timeout=1800)
        print("session", created.id[:8], flush=True)
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.connect_over_cdp(created.connect_url)
        self.ctx = self.browser.contexts[0]
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        self.page.goto(PORTAL, wait_until="domcontentloaded", timeout=60_000)
        return self

    def __exit__(self, *exc):
        try:
            self.browser.close()
        finally:
            self.pw.stop()

    def fetch_json(self, url: str, note: str):
        r = self.page.evaluate(FETCH_JS, url)
        body = r["t"].encode("utf-8")
        if r["s"] != 200:
            fail(url, note, f"HTTP {r['s']}", r["s"])
            return None
        try:
            parsed = json.loads(body)
        except ValueError:
            fail(url, note, f"not JSON ({len(body)} bytes)", 200)
            return None
        save(url, body, "application/json", 200, note, url)
        return parsed


def read(row: dict) -> dict:
    return json.loads((ROOT / row["path"]).read_text(encoding="utf-8"))


def sweep(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="sbir.py sweep")
    ap.add_argument("--fetch", action="store_true", help="touch the network; without it the sweep only reports what is saved")
    ap.add_argument("--since", default=SINCE)
    ap.add_argument("--size", type=int, default=500)
    ap.add_argument("--pages", type=int, default=200, help="stop after this many index pages (1 = only what is newest)")
    ap.add_argument("--reverse", action="store_true",
                    help="fetch the details oldest first, so a second sweep can meet the first in the middle (each keeps its own list of "
                         "what is saved, so the two overlap after they meet; stop both once every topic has its detail)")
    args = ap.parse_args(argv)
    manifest = manifest_rows()
    have = {r["url"] for r in manifest if r.get("status") == 200 and r.get("path")}
    if not args.fetch:
        print(f"{sum(u.startswith(API + '/search') for u in have)} index page(s) and {sum(u.endswith('/details') for u in have)} detail(s) saved; --fetch to sweep")
        return 0
    page_no, navy, restarts = 0, [], 0
    while page_no < args.pages:
        try:
            with Browser() as b:
                while page_no < args.pages:
                    d = b.fetch_json(page_url(page_no, args.size), f"DSIP topics index{NOTE_TAG} page {page_no}, newest first")
                    rows = (d or {}).get("data") or []
                    starts = [ms_day(r.get("topicStartDate")) for r in rows]
                    fresh = [r for r in rows if r.get("component") == COMPONENT and ms_day(r.get("topicStartDate")) >= args.since]
                    navy += fresh
                    print(f"  page {page_no}: {len(rows)} topic(s), {len(fresh)} Navy in window, starts {min(starts, default='')}..{max(starts, default='')}", flush=True)
                    page_no += 1
                    if not rows or min(starts) < args.since:
                        page_no = args.pages
                        break
                for i, r in enumerate(navy[::-1] if args.reverse else navy):
                    url = detail_url(r["topicId"])
                    if url in have:
                        continue
                    b.fetch_json(url, f"DSIP topic{NOTE_TAG} {r.get('topicCode')} detail")
                    have.add(url)
                    if i % 100 == 0:
                        print(f"  detail {i} of {len(navy)}", flush=True)
                    time.sleep(0.3)
        except Exception as exc:  # noqa: BLE001 - a hosted session that dies mid-sweep is reopened, not fatal
            restarts += 1
            print(f"  session lost ({type(exc).__name__}: {str(exc)[:80]}); restart {restarts}", flush=True)
            if restarts > 3:
                return 1
    print(f"{len(navy)} Navy topic(s) since {args.since}; details saved for {sum(detail_url(r['topicId']) in have for r in navy)}")
    return 0


def topic_row(r: dict, detail: dict | None, saved_row: dict | None, parents: dict, resolve) -> dict:
    text = strip_html(" ".join(filter(None, [(detail or {}).get("objective"), (detail or {}).get("description"),
                                             (detail or {}).get("phase3Description")])))
    keywords = strip_html((detail or {}).get("keywords") or "")
    offices = resolve(" ".join([r.get("topicTitle") or "", keywords, text]), parents)
    return {"topic_id": r["topicId"], "code": r.get("topicCode") or "", "title": strip_html(r.get("topicTitle")), "program": r.get("program") or "",
            "component": r.get("component") or "", "command": r.get("command") or "", "org": COMMANDS.get(r.get("command") or "", DEPARTMENT),
            "cycle": r.get("cycleName") or "", "solicitation": r.get("solicitationTitle") or "", "status": r.get("topicStatus") or "",
            "pre_release": min(filter(None, [ms_day(r.get("topicPreReleaseStartDate")), ms_day(r.get("topicStartDate"))]), default=""),
            "open": ms_day(r.get("topicStartDate")), "close": ms_day(r.get("topicEndDate")), "keywords": keywords,
            "technology_areas": (detail or {}).get("technologyAreas") or [], "text": text[:6000], "offices": offices,
            "url": detail_url(r["topicId"]), "sha256": (saved_row or {}).get("sha256", ""), "retrieved_at": (saved_row or {}).get("retrieved_at", ""),
            "path": (saved_row or {}).get("path", "")}


def resolve_specific(text: str, parents: dict) -> list[str]:
    from trace import resolve_offices, specific_offices  # noqa: E402
    return specific_offices(resolve_offices(text), parents)


def build(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="sbir.py build")
    ap.add_argument("--since", default=SINCE)
    args = ap.parse_args(argv)
    from trace import match_context  # noqa: E402
    parents = match_context()["parents"]
    manifest = manifest_rows()
    pages = [r for r in manifest if r.get("status") == 200 and r.get("path") and r.get("url", "").startswith(API + "/search") and (ROOT / r["path"]).exists()]
    latest: dict[str, dict] = {}
    for row in sorted(pages, key=lambda r: r["retrieved_at"]):
        for r in read(row).get("data") or []:
            if r.get("component") == COMPONENT and ms_day(r.get("topicStartDate")) >= args.since:
                latest[r["topicId"]] = r
    rows = []
    for topic_id, r in latest.items():
        saved_row = saved(manifest, lambda m, u=detail_url(topic_id): m.get("url") == u)
        rows.append(topic_row(r, read(saved_row) if saved_row else None, saved_row, parents, resolve_specific))
    rows.sort(key=lambda t: (t["pre_release"], t["code"]))
    payload = {"built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "since": args.since, "provider": PROVIDER,
               "topics": len(rows), "with_detail": sum(bool(t["path"]) for t in rows), "with_office": sum(bool(t["offices"]) for t in rows),
               "by_command": dict(Counter(t["command"] for t in rows).most_common()),
               "by_fiscal_year": dict(sorted(Counter(fiscal_year(t["pre_release"]) for t in rows).items())), "rows": rows}
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{payload['topics']} {COMPONENT} topic(s) since {args.since}, {payload['with_detail']} with detail, {payload['with_office']} naming a program office; "
          f"by command {payload['by_command']} -> {OUT.relative_to(ROOT)}")
    return 0


def fiscal_year(day: str) -> str:
    if not day:
        return "undated"
    year, month = int(day[:4]), int(day[5:7])
    return f"FY{year + 1 if month >= 10 else year}"


def show(argv: list[str]) -> int:
    rows = json.loads(OUT.read_text(encoding="utf-8"))["rows"]
    for t in rows:
        if t["code"] in argv or t["topic_id"] in argv:
            print(json.dumps({k: (v[:400] if isinstance(v, str) else v) for k, v in t.items()}, indent=1, ensure_ascii=False))
    return 0


FIXTURE = {"topicId": "abc_1", "topicCode": "N251-001", "topicTitle": "Antenna for <b>MIDS</b>", "program": "SBIR", "component": "NAVY",
           "command": "NAVWAR", "cycleName": "DOD_SBIR_2025_P1_C1", "solicitationTitle": "DoD SBIR 2025.1", "topicStatus": "Closed",
           "topicPreReleaseStartDate": "1733893200000", "topicStartDate": "1736485200000", "topicEndDate": "1739077200000"}


def selfcheck() -> int:
    assert ms_day("1748433600000") == "2025-05-28" and ms_day(None) == "" and ms_day("") == ""
    assert strip_html("<p>Develop &amp; demo</p>  <br/>x") == "Develop & demo x"
    assert fiscal_year("2025-10-01") == "FY2026" and fiscal_year("2025-09-30") == "FY2025" and fiscal_year("") == "undated"
    assert "sortBy" in urllib.parse.unquote(page_url(0, 500)) and page_url(3, 10).endswith("&size=10&page=3")
    detail = {"objective": "<p>Build a link for PMW 101 (MIDS).</p>", "description": "x", "keywords": "MANET, antenna", "technologyAreas": ["Air Platform"]}
    named = lambda text, parents: ["pmw:101"] if "PMW 101" in text else []  # noqa: E731 - the resolver is the trace module's; here only the plumbing
    t = topic_row(FIXTURE, detail, {"sha256": "ab", "retrieved_at": "2026-09-22T00:00:00Z", "path": "data/raw/x"}, {}, named)
    assert (t["pre_release"], t["open"], t["close"]) == ("2024-12-11", "2025-01-10", "2025-02-09"), (t["pre_release"], t["open"], t["close"])
    assert t["title"] == "Antenna for MIDS" and t["org"] == "command:navwar" and t["offices"] == ["pmw:101"] and t["keywords"] == "MANET, antenna"
    bare = topic_row({**FIXTURE, "command": "MCSC", "topicPreReleaseStartDate": None}, None, None, {}, named)
    assert bare["org"] == DEPARTMENT and bare["pre_release"] == bare["open"] == "2025-01-10" and bare["offices"] == [] and bare["path"] == ""
    # the 20.4 special cycle printed a pre-release date after the open date; the event is the earlier of the two
    odd = topic_row({**FIXTURE, "command": "ONR", "topicPreReleaseStartDate": "1739077200000"}, None, None, {}, named)
    assert odd["org"] == "command:onr" and odd["pre_release"] == "2025-01-10", odd["pre_release"]
    print("selfcheck ok")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] == "--selfcheck":
        return selfcheck()
    return {"sweep": sweep, "build": build, "show": show}[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
