#!/usr/bin/env python3
"""Fetch one URL, save the bytes under data/raw/, and record the retrieval in the manifest.

    python research/tools/fetch.py URL [--wayback [TIMESTAMP]] [--note TEXT] [--method M]

Direct fetches record status, final URL, MIME type, size and SHA-256. `--wayback` fetches the
closest Wayback Machine capture (or the given timestamp) of the original URL through the raw
`id_` endpoint and records the capture timestamp. Failures are recorded too, so blocked
documents are explicit rows rather than silent omissions. Stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
MANIFEST = ROOT / "research" / "documents_manifest.jsonl"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) chromie-federal-buyer-map-trial research fetch"


def _get(url: str, timeout: int = 90) -> tuple[int, str, bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.geturl(), resp.read(), resp.headers.get("Content-Type", "")


def closest_capture(url: str) -> str | None:
    api = "https://archive.org/wayback/available?url=" + urllib.parse.quote(url, safe="")
    try:
        _, _, body, _ = _get(api, timeout=60)
        closest = json.loads(body).get("archived_snapshots", {}).get("closest") or {}
        return closest.get("timestamp")
    except (urllib.error.URLError, ValueError, TimeoutError):
        return None


def safe_name(url: str) -> str:
    base = urllib.parse.unquote(urllib.parse.urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]) or "index"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", base)[:80]


def fetch(url: str, method: str, wayback: str | None, note: str) -> dict:
    row: dict = {
        "url": url,
        "method": method,
        "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": note,
    }
    target = url
    if method == "wayback":
        # A partial timestamp makes Wayback redirect to the nearest capture, so the
        # availability API is only a hint; the real capture time is read from the final URL.
        ts = wayback if wayback and wayback != "closest" else (closest_capture(url) or "2026")
        target = f"https://web.archive.org/web/{ts}id_/{url}"
    row["fetched_from"] = target
    try:
        status, final_url, body, mime = _get(target)
    except urllib.error.HTTPError as exc:
        row.update(status=exc.code, error=f"HTTP {exc.code}")
        return row
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        row.update(status=None, error=f"{type(exc).__name__}: {exc}")
        return row
    if method == "wayback":
        match = re.search(r"/web/(\d{14})id_/", final_url)
        row["wayback_timestamp"] = match.group(1) if match else None
        if body.startswith(b"<!DOCTYPE html>") and b"Wayback Machine" in body[:4000] and b"hasn't archived" in body:
            row.update(status=404, error="no wayback capture found")
            return row
    digest = hashlib.sha256(body).hexdigest()
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / f"{digest[:12]}_{safe_name(url)}"
    path.write_bytes(body)
    row.update(status=status, final_url=final_url, mime=mime.split(";")[0].strip(), size=len(body),
               sha256=digest, path=str(path.relative_to(ROOT)))
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--wayback", nargs="?", const="closest", default=None,
                        help="fetch the closest (or given YYYYMMDDhhmmss) Wayback capture")
    parser.add_argument("--method", choices=("direct", "wayback", "browserbase", "manual"))
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    method = args.method or ("wayback" if args.wayback else "direct")
    row = fetch(args.url, method, args.wayback, args.note)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps(row, sort_keys=True))
    return 0 if row.get("status") == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
