#!/usr/bin/env python3
"""Harvest SAM.gov notices by solicitation number or notice id through sam.gov's site API.

    python research/tools/sam_notices.py SOLNUM_OR_NOTICEID [...]

Uses the keyless endpoints the SAM.gov web application itself calls (`api_key=null`), which
Chromie's runner also uses; the documented public host api.sam.gov answered 404 from every
network tried on 2026-09-16. For each notice: saves the detail JSON (description text included),
lists attachments, downloads PDF/DOCX/TXT attachments under a size cap, extracts their text,
and records every retrieval in research/documents_manifest.jsonl. Prints office-code mentions.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "raw" / "sam_notices"
MANIFEST = ROOT / "research" / "documents_manifest.jsonl"
SGS = "https://sam.gov/api/prod/sgs/v1/search/"
OPPS = "https://sam.gov/api/prod/opps"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/hal+json, application/json"}
OFFICE_RE = re.compile(
    r"(PM[WA]\s?/?\s?A?\s?-?\s?\d{3}|PMS\s?-?\s?\d{3}|PEO\s?C4I|Program Executive Office[^.;]{0,80}|"
    r"Naval Enterprise Networks|\bNEN\b|[Pp]rogram [Oo]ffice[^.;]{0,60}|Tactical Networks|Communications and GPS Navigation|"
    r"Battlespace Awareness|Command and Control Systems|International C4I|Ship Integration|Undersea Communications|"
    r"Shore and Expeditionary|Cybersecurity Program|Multifunctional Information Distribution)"
)
MAX_ATTACHMENT = 25_000_000


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(url: str, timeout: int = 90) -> tuple[int, bytes, dict]:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read(), dict(resp.headers)


def record(url: str, body: bytes | None, path: Path | None, note: str, status: int | None, mime: str = "", error: str = "") -> None:
    row = {"url": url, "method": "direct", "retrieved_at": now(), "note": note, "status": status, "tls_verified": True}
    if body is not None and path is not None:
        row.update(size=len(body), sha256=hashlib.sha256(body).hexdigest(), path=str(path.relative_to(ROOT)), mime=mime)
    if error:
        row["error"] = error
    with MANIFEST.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def search(query: str) -> list[dict]:
    hits = []
    for active in ("false", "true"):
        q = urllib.parse.urlencode({"index": "opp", "page": 0, "size": 25, "q": query, "mode": "search", "is_active": active})
        try:
            _, body, _ = get(f"{SGS}?{q}")
            hits += json.loads(body).get("_embedded", {}).get("results", [])
        except Exception as exc:  # noqa: BLE001
            print(f"  search error {query} active={active}: {exc}")
        time.sleep(0.8)
    seen, out = set(), []
    for h in hits:
        if h.get("_id") not in seen:
            seen.add(h["_id"]); out.append(h)
    return out


def text_of(name: str, data: bytes) -> str:
    low = name.lower()
    try:
        if low.endswith(".pdf"):
            from pypdf import PdfReader
            return " ".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
        if low.endswith(".docx"):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                xml = z.read("word/document.xml").decode("utf-8", "ignore")
            return re.sub(r"<[^>]+>", " ", xml)
        if low.endswith((".txt", ".csv")):
            return data.decode("utf-8", "ignore")
    except Exception as exc:  # noqa: BLE001
        return f"[extraction failed: {exc}]"
    return ""


def mentions(text: str) -> list[str]:
    out = []
    for m in OFFICE_RE.finditer(text):
        s, e = max(0, m.start() - 90), min(len(text), m.end() + 90)
        out.append(re.sub(r"\s+", " ", text[s:e]).strip())
        if len(out) >= 6:
            break
    return out


def harvest_notice(notice_id: str, label: str) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    url = f"{OPPS}/v2/opportunities/{notice_id}?api_key=null"
    status, body, _ = get(url)
    detail = json.loads(body)
    path = OUT / f"{notice_id}.json"; path.write_bytes(body)
    record(url, body, path, f"SAM notice detail {label}: {detail.get('data2', {}).get('title', '')[:80]}", status, "application/json")
    d2 = detail.get("data2", {})
    desc = re.sub(r"<[^>]+>", " ", " ".join(x.get("body", "") for x in detail.get("description", []) if isinstance(x, dict)))
    desc = re.sub(r"\s+", " ", desc)
    result = {"notice_id": notice_id, "title": d2.get("title"), "type": d2.get("type"), "solicitation": d2.get("solicitationNumber"),
              "posted": (detail.get("postedDate") or "")[:10], "org_id": d2.get("organizationId"),
              "poc": [(p.get("fullName"), p.get("email"), p.get("type")) for p in d2.get("pointOfContact", [])],
              "description_chars": len(desc), "description_mentions": mentions(desc), "attachments": []}
    time.sleep(0.8)
    rurl = f"{OPPS}/v3/opportunities/{notice_id}/resources?api_key=null&random={int(time.time()*1000)}"
    try:
        rstatus, rbody, _ = get(rurl)
        rpath = OUT / f"{notice_id}.resources.json"; rpath.write_bytes(rbody)
        record(rurl, rbody, rpath, f"SAM notice attachment list {label}", rstatus, "application/json")
        rows = []
        def walk(o):
            if isinstance(o, dict):
                if "resourceId" in o:
                    rows.append(o)
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(json.loads(rbody))
    except Exception as exc:  # noqa: BLE001
        rows = []; result["attachments_error"] = str(exc)[:120]
    for r in rows[:12]:
        rid = r.get("resourceId"); name = str(r.get("name") or r.get("fileName") or r.get("description") or rid)
        size = int(r.get("size") or 0)
        entry = {"resource_id": rid, "name": name, "size": size, "mime": r.get("mimeType"), "kind": r.get("type")}
        if r.get("type") == "link":
            # NAVWAR notices usually attach only a PIEE Solicitation Module link; record it, do not follow it.
            entry.update(uri=r.get("uri"), description=r.get("description"), skipped="external link, not a file")
            result["attachments"].append(entry); continue
        if size and size > MAX_ATTACHMENT:
            entry["skipped"] = "over size cap"; result["attachments"].append(entry); continue
        if not name.lower().endswith((".pdf", ".docx", ".txt", ".csv", ".xlsx")):
            entry["skipped"] = "not an extractable type"; result["attachments"].append(entry); continue
        durl = f"{OPPS}/v3/opportunities/resources/files/{rid}/download?api_key=null"
        try:
            time.sleep(1.0)
            dstatus, dbody, dh = get(durl, timeout=180)
            safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:90]
            dpath = OUT / notice_id / safe; dpath.parent.mkdir(parents=True, exist_ok=True); dpath.write_bytes(dbody)
            record(durl, dbody, dpath, f"SAM attachment {label}: {name[:70]}", dstatus, dh.get("Content-Type", ""))
            txt = text_of(name, dbody)
            entry.update(bytes=len(dbody), text_chars=len(txt), mentions=mentions(txt))
        except Exception as exc:  # noqa: BLE001
            entry["error"] = str(exc)[:120]
            record(durl, None, None, f"SAM attachment {label}: {name[:70]}", None, error=str(exc)[:120])
        result["attachments"].append(entry)
    return result


def main(argv: list[str]) -> int:
    summary = []
    for arg in argv:
        label = arg
        if re.fullmatch(r"[0-9a-f]{32}", arg):
            ids = [(arg, "", "", "")]
        else:
            hits = search(arg)
            ids = [(h["_id"], (h.get("publishDate") or "")[:10], (h.get("type") or {}).get("value") if isinstance(h.get("type"), dict) else h.get("type"), h.get("title")) for h in hits]
            print(f"\n== {arg}: {len(ids)} notice(s)")
            for nid, d, t, title in ids:
                print(f"   {d} | {t} | {nid} | {str(title)[:70]}")
        for nid, d, t, title in ids[:6]:
            try:
                res = harvest_notice(nid, f"{label}")
                summary.append(res)
                print(f"   -> {res['posted']} {res['type']} {res['solicitation']} | desc {res['description_chars']} chars | attachments {len(res['attachments'])}")
                for m in res["description_mentions"][:3]:
                    print(f"      desc: ...{m}...")
                for a in res["attachments"]:
                    print(f"      att: {a['name'][:60]} {a.get('bytes', a.get('size'))}B {a.get('skipped') or a.get('error') or ''}")
                    for m in (a.get("mentions") or [])[:3]:
                        print(f"           ...{m}...")
            except Exception as exc:  # noqa: BLE001
                print(f"   -> error {nid}: {exc}")
            time.sleep(1.0)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
