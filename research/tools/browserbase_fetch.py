#!/usr/bin/env python3
"""Fetch geo-blocked official pages and files through a Browserbase (US egress) browser.

    BROWSERBASE_API_KEY=... python research/tools/browserbase_fetch.py URL [URL ...]

The .mil hosts fronted by Akamai refuse requests from non-US addresses; a hosted US browser is
the approved fallback. Pages are saved as rendered HTML, files (PDF, XLSX) as bytes, and every
retrieval is recorded in research/documents_manifest.jsonl with method "browserbase". Links to
tear sheets, LRAE spreadsheets and budget exhibits found on fetched pages are downloaded too.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
MANIFEST = ROOT / "research" / "documents_manifest.jsonl"
FILE_LINK_RE = re.compile(r"\.(pdf|xlsx|xls|docx)(\?|$)", re.I)
WANTED_LINK_RE = re.compile(r"tear.?sheet|long.?range|lrae|r-1|p-1|budget|exhibit|org.?chart|fact.?sheet", re.I)
MAX_FILE = 80_000_000


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_name(url: str) -> str:
    base = urllib.parse.unquote(urllib.parse.urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]) or "index"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", base)[:80]


def record(row: dict) -> None:
    with MANIFEST.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def save(url: str, body: bytes, mime: str, status: int, note: str, final_url: str = "") -> dict:
    digest = hashlib.sha256(body).hexdigest()
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / f"{digest[:12]}_{safe_name(url)}"
    path.write_bytes(body)
    row = {"url": url, "method": "browserbase", "retrieved_at": now(), "note": note, "status": status,
           "final_url": final_url or url, "mime": mime.split(";")[0].strip(), "size": len(body), "sha256": digest,
           "path": str(path.relative_to(ROOT)), "tls_verified": True}
    record(row)
    return row


def fail(url: str, note: str, error: str, status: int | None = None) -> dict:
    row = {"url": url, "method": "browserbase", "retrieved_at": now(), "note": note, "status": status, "error": error[:200], "tls_verified": True}
    record(row)
    return row


def main(urls: list[str]) -> int:
    sys.path.insert(0, str(Path(os.environ.get("SLED_TRIAL_SRC", "/Users/pookie/chromie-sled-intelligence-trial/src"))))
    from sled_trial.net.browser import create_session  # reuses the SLED trial's Browserbase wrapper
    from playwright.sync_api import sync_playwright

    session = create_session(session_seconds=1800)
    print("session", session["id"][:8])
    discovered: list[tuple[str, str]] = []
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(session["connectUrl"])
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        def get_file(url: str, note: str) -> None:
            try:
                resp = ctx.request.get(url, timeout=180_000)
                body = resp.body()
                mime = resp.headers.get("content-type", "")
                if resp.status != 200:
                    fail(url, note, f"HTTP {resp.status}", resp.status); print(f"  {resp.status} | {url[-80:]}"); return
                if len(body) > MAX_FILE:
                    fail(url, note, f"over size cap ({len(body)} bytes)", 200); print(f"  too large | {url[-80:]}"); return
                if "text/html" in mime and FILE_LINK_RE.search(url):
                    fail(url, note, "HTML returned for a file URL (moved or missing)", 200); print(f"  html-for-file | {url[-80:]}"); return
                save(url, body, mime, resp.status, note, resp.url)
                print(f"  200 {mime.split(';')[0]} {len(body)} | {url[-80:]}")
            except Exception as exc:  # noqa: BLE001
                fail(url, note, f"{type(exc).__name__}: {exc}"); print(f"  ERR {type(exc).__name__} | {url[-80:]}")

        for url in urls:
            note = f"live page via Browserbase: {url}"
            if FILE_LINK_RE.search(url):
                get_file(url, f"live file via Browserbase: {url[-80:]}"); time.sleep(1.5); continue
            try:
                r = page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                time.sleep(1.5)
                html = page.content()
                status = r.status if r else None
                title = page.title()
                if status and status >= 400:
                    fail(url, note, f"HTTP {status}", status); print(f"  {status} | {title[:50]!r} | {url}"); continue
                save(url, html.encode("utf-8"), "text/html", status or 200, f"{note} | title: {title[:80]}", page.url)
                print(f"  {status} | {title[:60]!r} | {len(html)} | {url}")
                base = page.url
                for href in set(re.findall(r'href="([^"#]+)"', html, re.I)):
                    full = urllib.parse.urljoin(base, href.replace("&amp;", "&"))
                    if FILE_LINK_RE.search(full) and WANTED_LINK_RE.search(urllib.parse.unquote(full)):
                        discovered.append((full, f"linked from {url}"))
            except Exception as exc:  # noqa: BLE001
                fail(url, note, f"{type(exc).__name__}: {exc}"); print(f"  ERR {type(exc).__name__}: {str(exc)[:60]} | {url}")
            time.sleep(1.5)
        seen = set()
        print(f"\n== discovered files: {len(discovered)}")
        for full, note in discovered:
            if full in seen:
                continue
            seen.add(full)
            if len(seen) > 30:
                print("  (cap reached)"); break
            get_file(full, f"live file via Browserbase ({note[:60]})"); time.sleep(1.5)
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
