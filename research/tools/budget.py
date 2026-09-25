#!/usr/bin/env python3
"""Money family: the agency's own budget justification books, read line by line.

Every Exhibit P-40 (procurement line item justification) page of a saved book becomes part of one record per P-1
line item: the amounts the book prints for each fiscal year, the appropriation and budget activity, and the
justification prose, so a requirement's names (MIDS, CANES, ADNS) can be found in it. A line whose FY2027 total
differs from FY2026 is a funding_change event; a flat line is a budget_line event. Nothing is inferred: the amounts
are the book's, the date is the book's ("Date: April 2026"), credited on that month's last day.

An agency funded through research, development, test and evaluation alone (DARPA) publishes Exhibit R-2 pages
instead, one per program element; the profile's `budget.exhibit` picks the reader, and the record shape is the
same with the program element number where the P-1 line item number stands. Books are the `*_Book.pdf` files
under the profile's books folder and any ledger row whose note begins "budget book:" and names the agency.

  python research/tools/budget.py extract        # every *_Book.pdf under data/raw/jbooks -> research/events/budget_lines.json
  python research/tools/budget.py show MIDS      # the lines whose text names it
"""
from __future__ import annotations

import calendar
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "research" / "sources" / "documents_manifest.jsonl"
PDFTOTEXT = shutil.which("pdftotext") or "/opt/homebrew/bin/pdftotext"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agency import BOOKS, EVENTS, P, RAW, NOTE_TAG  # noqa: E402

BOOKS = BOOKS
OUT = EVENTS / "budget_lines.json"
PROVIDER = P["budget"]["provider"]
EXHIBIT = P["budget"]["exhibit"]  # "P-40" (procurement line items) or "R-2" (RDT&E program elements)
BOOK_NOTE = f"budget book{NOTE_TAG}:"
AGENCY_ABBREVIATION = P["agency"]["subtier_abbreviation"]

P40 = "Exhibit P-40, Budget Line Item Justification"
R2 = "Exhibit R-2, RDT&E Budget Item Justification"
PE_RE = re.compile(r"\bPE (\d{7}[A-Z]?) / (\S.*?)\s*$")
R2_BA_RE = re.compile(r"^\s*(\d{4}): ([^/]+?) / BA (\d+):\s*(.*?)\s*(?:PE \d{7}[A-Z]? /.*)?$")
TOTAL_PE_RE = re.compile(r"^\s*Total Program Element\s+(.*)$", re.M)
def columns_for(pb: str) -> tuple[str, ...]:
    """The twelve resource-summary columns of a book for President's Budget year `pb`: prior years, the two years
    before the request, the request (base, overseas/other, total), the four out-years, to complete, total. A
    book's columns are its own year's; reading a PB 2026 book under PB 2027 labels shifts every amount a year."""
    y = int(pb)
    return ("prior_years", f"fy{y - 2}", f"fy{y - 1}", f"fy{y}_base", f"fy{y}_ooc", f"fy{y}_total",
            f"fy{y + 1}", f"fy{y + 2}", f"fy{y + 3}", f"fy{y + 4}", "to_complete", "total")


COLUMNS = columns_for("2027")
# "1810N: Other Procurement, Navy / BA 02: Communications & Electronics Equip /        2026 / SPQ-9B Radar"; the layout
# text often cuts the budget activity to "BA" or "B" where the right-hand column overlaps, so it is read once per book.
LI_RE = re.compile(r"^\s*(\d{4}N):\s*([^/]+?)\s*/.*?\s(\d{4}) / (\S.*?)\s*$")
BA_RE = re.compile(r"\bBA (\d+): ([^/\n]+?)\s*/")
TOA_RE = re.compile(r"^\s*Total Obligation Authority \(\$ in Millions\)\s+(.*)$", re.M)
DATE_RE = re.compile(r"Date: ([A-Z][a-z]+) (\d{4})")
PB_RE = re.compile(r"PB (\d{4}) " + re.escape(P["budget"]["pb_label"]))
NUMBER = re.compile(r"^-?\d[\d,]*(?:\.\d+)?$")
MONTHS = {m: i for i, m in enumerate(calendar.month_name) if m}


def text_of(pdf: Path) -> str:
    return subprocess.run([PDFTOTEXT, "-layout", str(pdf), "-"], check=True, capture_output=True, text=True, errors="replace").stdout


def month_end(month: str, year: str) -> str:
    m = MONTHS[month]
    return f"{int(year):04d}-{m:02d}-{calendar.monthrange(int(year), m)[1]:02d}"


def amounts(tail: str, pb: str = "2027") -> dict[str, float | None]:
    """The twelve resource-summary columns as the row prints them: a number, or '-' and 'Cont' as none."""
    columns = columns_for(pb) if pb else COLUMNS
    values: list[float | None] = []
    for token in tail.split():
        values.append(float(token.replace(",", "")) if NUMBER.match(token) else None)
    values = (values + [None] * len(columns))[:len(columns)]
    return dict(zip(columns, values))


def request_years(a: dict) -> tuple[str, str]:
    """(the year before the request, the request total) as the amount keys name them: fy2026 and fy2027_total in a
    PB 2027 book, fy2025 and fy2026_total in a PB 2026 book."""
    total = next((k for k in a if k.endswith("_total")), "fy2027_total")
    return f"fy{int(total[2:6]) - 1}", total


FURNITURE = ("Exhibit P-40", "Appropriation /", "ID Code", "Line Item MDAP", "LI ", "Navy Page",
             "Exhibit R-2", "Appropriation/Budget Activity", "UNCLASSIFIED", "R-1 Program Element", "Total Program Element")


def prose(page: str) -> list[str]:
    """The justification sentences of a page: lines with words, not the table rows."""
    out = []
    for line in page.splitlines():
        s = re.sub(r"\s+", " ", line).strip()
        numeric = sum(bool(NUMBER.match(t)) or t == "-" for t in s.split())
        if len(s) >= 40 and numeric < 3 and not s.startswith(FURNITURE):
            out.append(s)
    return out


def parse_book(text: str) -> tuple[dict, list[dict]]:
    """(book header, one record per P-1 line item) from the layout text of a justification book."""
    header: dict = {}
    lines: dict[str, dict] = {}
    for page in text.split("\f"):
        if P40 not in page:
            continue
        if not header:
            d, pb = DATE_RE.search(page), PB_RE.search(page)
            header = {"date": f"{d.group(1)} {d.group(2)}" if d else "", "published": month_end(d.group(1), d.group(2)) if d else "", "pb": pb.group(1) if pb else ""}
        if "budget_activity" not in header and BA_RE.search(page):
            ba = BA_RE.search(page)
            header["budget_activity"] = f"BA {ba.group(1)}: {ba.group(2).strip()}"
        li = next((LI_RE.match(line) for line in page.splitlines() if LI_RE.match(line)), None)
        if not li:
            continue
        appropriation, approp_name, number, title = li.groups()
        row = lines.setdefault(number, {"li": number, "title": title, "appropriation": appropriation, "appropriation_name": approp_name.strip(),
                                        "pages": 0, "amounts": None, "text": []})
        row["pages"] += 1
        toa = TOA_RE.search(page)
        if toa and row["amounts"] is None:
            row["amounts"] = amounts(toa.group(1), header.get("pb") or "2027")
        row["text"].extend(prose(page))
    for row in lines.values():
        row["text"] = " ".join(dict.fromkeys(row["text"]))[:12000]
    return header, sorted(lines.values(), key=lambda r: r["li"])


def parse_book_r2(text: str) -> tuple[dict, list[dict]]:
    """(book header, one record per R-1 program element) from the layout text of an RDT&E justification book. The
    R-2 page names the appropriation, the budget activity (its name wraps to the next line) and the program element;
    the "Total Program Element" row carries the twelve resource-summary columns the P-40 reader knows."""
    header: dict = {}
    lines: dict[str, dict] = {}
    for page in text.split("\f"):
        if R2 not in page or "Exhibit R-2A" in page:
            continue
        if not header:
            d, pb = DATE_RE.search(page), PB_RE.search(page)
            header = {"date": f"{d.group(1)} {d.group(2)}" if d else "", "published": month_end(d.group(1), d.group(2)) if d else "", "pb": pb.group(1) if pb else ""}
        rows = page.splitlines()
        pe = next((PE_RE.search(line) for line in rows if PE_RE.search(line)), None)
        if not pe:
            continue
        number, title = pe.group(1), " ".join(pe.group(2).split())
        appropriation, approp_name, ba_number, ba_name = "", "", "", ""
        for i, line in enumerate(rows):
            m = R2_BA_RE.match(line)
            if m:
                appropriation, approp_name, ba_number, ba_name = m.group(1), m.group(2).strip(), m.group(3), m.group(4).strip()
                # The budget activity name wraps under the left column: "BA 1: Basic" / "Research".
                if i + 1 < len(rows):
                    tail = rows[i + 1].strip()
                    if tail and len(tail) < 60 and not any(ch.isdigit() for ch in tail) and not tail.startswith("Prior"):
                        ba_name = f"{ba_name} {tail}".strip()
                break
        row = lines.setdefault(number, {"li": number, "title": title, "appropriation": appropriation, "appropriation_name": approp_name,
                                        "budget_activity": f"BA {ba_number}: {ba_name}" if ba_number else "", "pages": 0, "amounts": None, "text": []})
        row["pages"] += 1
        total = TOTAL_PE_RE.search(page)
        if total and row["amounts"] is None:
            row["amounts"] = amounts(total.group(1), header.get("pb") or "2027")
        row["text"].extend(prose(page))
    for row in lines.values():
        row["text"] = " ".join(dict.fromkeys(row["text"]))[:12000]
    return header, sorted(lines.values(), key=lambda r: r["li"])


def parse(text: str) -> tuple[dict, list[dict]]:
    return parse_book_r2(text) if EXHIBIT == "R-2" else parse_book(text)


def event_type(row: dict) -> str:
    a = row["amounts"] or {}
    year_before, request = request_years(a)
    before, after = a.get(year_before), a.get(request)
    return "funding_change" if before is not None and after is not None and before != after else "budget_line"


def money(v: float | None) -> str:
    return "none" if v is None else f"${v:,.3f}M"


def event_title(row: dict) -> str:
    a = row["amounts"] or {}
    year_before, request = request_years(a)
    return (f"{row['appropriation']} line {row['li']} {row['title']}: FY{year_before[2:]} {money(a.get(year_before))}, "
            f"FY{request[2:6]} {money(a.get(request))}")


def manifest_row(path: str) -> dict:
    for line in MANIFEST.read_text(encoding="utf-8").splitlines() if MANIFEST.exists() else []:
        r = json.loads(line)
        if r.get("path") == path and r.get("sha256"):
            return r
    return {}


def noted_books() -> list[Path]:
    """The books the ledger records under a "budget book:" note naming this agency, wherever their bytes were saved."""
    out = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines() if MANIFEST.exists() else []:
        r = json.loads(line)
        note = r.get("note") or ""
        if r.get("status") == 200 and r.get("path") and note.startswith(BOOK_NOTE) and AGENCY_ABBREVIATION in note and (ROOT / r["path"]).exists():
            out.append(ROOT / r["path"])
    return out


def extract(argv: list[str]) -> int:
    books, records = [], []
    found = sorted(BOOKS.glob("*_Book.pdf")) if BOOKS.exists() else []
    for pdf in found + [b for b in noted_books() if b not in found]:
        if pdf.stat().st_size == 0 or pdf.name.startswith("._") or "Highlights" in pdf.name:
            continue
        header, rows = parse(text_of(pdf))
        if not rows:
            print(f"{pdf.name}: no {EXHIBIT} exhibits (another exhibit kind; not read yet)")
            continue
        rel = str(pdf.relative_to(ROOT))
        record = manifest_row(rel)
        book = {"path": rel, "url": record.get("fetched_from") or record.get("url", ""), "sha256": record.get("sha256", ""),
                "retrieved_at": record.get("retrieved_at", ""), **header, "lines": len(rows)}
        books.append(book)
        for row in rows:
            records.append({**row, "book": rel, "published": header["published"], "event_type": event_type(row), "event_title": event_title(row)})
        changed = sum(r["event_type"] == "funding_change" for r in records if r["book"] == rel)
        print(f"{pdf.name}: {len(rows)} line item(s), {changed} with FY2027 differing from FY2026, dated {header['date']}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"provider": PROVIDER, "books": books, "lines": records}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


def show(argv: list[str]) -> int:
    needle = (argv[0] if argv else "MIDS").lower()
    for row in json.loads(OUT.read_text(encoding="utf-8"))["lines"]:
        if needle in row["title"].lower() or needle in row["text"].lower():
            print(row["event_title"])
    return 0


FIXTURE = """Exhibit P-40, Budget Line Item Justification: PB 2027 Navy                       Date: April 2026
Appropriation / Budget Activity / Budget Sub Activity:                        P-1 Line Item Number / Title:
1810N: Other Procurement, Navy / BA 02: Communications & Electronics Equip /  3415 / MIDS
BSA 4: Communications and Electronic Equipment
          Resource Summary                          Prior Years   FY 2025   FY 2026   FY 2027 Base   FY 2027 OOC   FY 2027 Total   FY 2028   FY 2029   FY 2030   FY 2031  To Complete   Total
Gross/Weapon System Cost ($ in Millions)                321.645     7.402    10.000       12.500        0.000        12.500      0.000      0.000     0.000     0.000        Cont       Cont
Total Obligation Authority ($ in Millions)              321.645     7.402    10.000       12.500        0.000        12.500      0.000      0.000     0.000     0.000        Cont       Cont
 Description:
 The Multifunctional Information Distribution System (MIDS) program procures Link 16 terminals for ships and aircraft.
\fExhibit P-40, Budget Line Item Justification: PB 2027 Navy                       Date: April 2026
1810N: Other Procurement, Navy / BA 02: Communications & Electronics Equip /  3415 / MIDS
 [P40A / BR001 MIDS LVT TERMINALS]: Procures MIDS Low Volume Terminals and Joint Tactical Radio System terminals for the fleet.
\fExhibit P-40, Budget Line Item Justification: PB 2027 Navy                       Date: April 2026
1810N: Other Procurement, Navy / BA 02: Communications & Electronics Equip /  2026 / SPQ-9B Radar
Total Obligation Authority ($ in Millions)              321.645     7.402     0.000        0.000        0.000         0.000      0.000      0.000     0.000     0.000           -     329.047
"""


def selfcheck() -> int:
    header, rows = parse_book(FIXTURE)
    assert header == {"date": "April 2026", "published": "2026-04-30", "pb": "2027", "budget_activity": "BA 02: Communications & Electronics Equip"}, header
    assert [r["li"] for r in rows] == ["2026", "3415"] and rows[1]["title"] == "MIDS" and rows[1]["pages"] == 2
    a = rows[1]["amounts"]
    assert a["prior_years"] == 321.645 and a["fy2026"] == 10.0 and a["fy2027_total"] == 12.5 and a["to_complete"] is None and a["total"] is None
    assert rows[0]["amounts"]["total"] == 329.047 and rows[0]["amounts"]["to_complete"] is None
    assert event_type(rows[1]) == "funding_change" and event_type(rows[0]) == "budget_line" and event_type({"amounts": None}) == "budget_line"
    assert "Link 16 terminals" in rows[1]["text"] and "MIDS Low Volume Terminals" in rows[1]["text"] and "Resource Summary" not in rows[1]["text"]
    assert event_title(rows[1]) == "1810N line 3415 MIDS: FY2026 $10.000M, FY2027 $12.500M"
    m = LI_RE.match("1810N: Other Procurement, Navy / BA                         2026 / SPQ-9B Radar")
    assert m and m.group(3) == "2026" and m.group(4) == "SPQ-9B Radar", m
    m = LI_RE.match("1810N: Other Procurement, Navy / B                                            2312 / AN/SLQ-32")
    assert m and m.group(4) == "AN/SLQ-32" and m.group(2) == "Other Procurement, Navy", m
    assert month_end("February", "2027") == "2027-02-28"
    print("selfcheck ok")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] == "--selfcheck":
        return selfcheck()
    return {"extract": extract, "show": show}[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
