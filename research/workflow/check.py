"""Mechanical checks on a startup intelligence brief: table shape, exact quotes against the saved sources,
record identifiers against the record (report.py's resolver), the published ranking rule, the fit and lead order
lines, banned words, people rules and the tally.

usage: AGENCY=<key> python research/workflow/check.py BRIEF SOURCE_DIR [SOURCE_DIR ...]
Prints JSON: {"problems": [...], "tally": "...", "quotes": {...}, "identifiers": {...}}."""
import html
import json
import os
import re
import sys

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools")

PROV = {"repo", "tool", "web", "profile"}
CLASS = {"primary", "secondary"}
STATUS = {"Live", "Historical", "Adjacent"}
TIER = {"lead-eligible": 0, "conditional": 1, "route-only": 2, "historical": 3, "ruled-out": 4, "gated-out": 4}
GROUP_WORDS = [("instrument", 0), ("route", 1), ("live signal", 2), ("signal", 2), ("historical", 3), ("ruled out", 4), ("gated", 4)]
BANNED = re.compile(r"\b(likely|probably|imminent|expected soon|will release|rfp coming)\b", re.I)
CLAIMS = re.compile(r"every fact (?:is )?from", re.I)
GATE_CODE = re.compile(r"\bG[1-4]\b")
DECIDER = re.compile(r"decision[- ]maker", re.I)  # report.py's rule: the record ties people to roles, never to decisions
# ponytail: personal webmail domains only; a notice's published contact is allowed, so phones are left to the validators
PERSONAL = re.compile(r"\b[\w.+-]+@(?:gmail|yahoo|outlook|hotmail|icloud|proton)(?:mail)?\.\w+\b", re.I)
SECTIONS = [
    "Sources", "Bottom line", "What rules a route in or out", "Ranked opportunities", "P0 fields", "Agencies and offices",
    "Programs and requirements", "Budget lines behind the work", "What Congress has directed",
    "What leaders have said", "Oversight, Federal Register and news", "Solicitations, BAAs and planning notices",
    "How long from solicitation to award", "Awards and incumbents", "How its contracting office buys",
    "Contracts in this line ending soon", "What the winning companies did in the last two years", "SBIR and STTR",
    "People and program offices", "Where the office sits", "What changed in the last year",
    "Next actions from the record", "Teaming and access routes", "Past ", "Company capability and risk signals",
    "Bid protests", "Small business routes", "Brief for the first meeting", "Outreach drafts", "Still open",
    "Audit", "How this was produced",
]
QUOTE = re.compile(r'"([^"]{12,}?)"|“([^”]{12,}?)”')
TRANS = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
                       "‑": "-", " ": " ", " ": " ", "*": None, "`": None})


def norm(s):
    s = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), s)
    s = s.replace("\\n", " ").replace("\\t", " ").replace('\\"', '"').replace("\\/", "/")
    s = html.unescape(s).translate(TRANS)
    return re.sub(r"\s+", " ", s).strip().lower()


def haystack(dirs):
    parts = []
    for d in dirs:
        for root, _, files in os.walk(d, followlinks=True):
            for f in files:
                if f.endswith((".txt", ".md", ".json", ".html", ".tsv", ".csv")) and not f.startswith("brief"):
                    with open(os.path.join(root, f), errors="replace") as fh:
                        parts.append(norm(fh.read()))
    return "\n".join(parts)


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def unquoted(line):
    return QUOTE.sub(" ", line)


def check(text, hay, resolver=None):
    lines = text.split("\n")
    problems = []

    def bad(kind, i, msg):
        problems.append({"check": kind, "line": i + 1, "text": msg[:300]})

    heads = [(i, l[3:].strip()) for i, l in enumerate(lines) if l.startswith("## ")]
    pos = -1
    for want in SECTIONS:
        hit = next((i for i, h in heads if h.startswith(want) and i > pos), None)
        if hit is None:
            bad("section", pos, f"missing or out of order: '## {want}'")
        else:
            pos = hit

    fit = next((i for i, l in enumerate(lines) if l.startswith("**Fit:**")), None)
    if fit is None:
        bad("fit", 0, "no '**Fit:**' line in the Bottom line")
    elif len(lines[fit].split()) < 20 or re.match(r"\*\*Fit:\*\*\s*(yes|no)\W*$", lines[fit], re.I):
        bad("fit", fit, "fit line is a bare verdict; say what fits, what does not and what the agency does not buy")

    rows, tally_rows, evidence, not_in_file, quotes, failed = [], [], [], 0, 0, []
    in_ranked, group, ranked, header = False, None, [], ""
    for i, l in enumerate(lines):
        if l.startswith("## "):
            in_ranked = l.startswith("## Ranked opportunities")
        if in_ranked and l.startswith("**") and not l.startswith("| "):
            low = l.strip("* ").lower()
            group = next((g for w, g in GROUP_WORDS if low.startswith(w)), group)
        if not l.startswith("|") or set(l) <= set("|-: "):
            continue
        c = cells(l)
        if lines[i + 1].startswith("|---") if i + 1 < len(lines) else False:
            header = l
        not_in_file += sum(1 for x in c if x.lower().startswith("not in file"))
        if in_ranked and len(c) == 12 and c[0].isdigit():
            ranked.append((i, group, c))
            continue
        if len(c) == 6 and c[-1] in PROV and c[4] in CLASS:
            tally_rows.append(c)
            evidence.append((i, c[2] if header.startswith("| Field |") else c[0], c[-1]))
            if c[2] in STATUS:
                rows.append((i, c))
        elif header.startswith(("| Identifier |", "| Field |")) and l != header and (c[-1] not in PROV or c[4] not in CLASS):
            bad("row", i, f"six-column row with Class '{c[4]}' or Provenance '{c[-1]}' outside the allowed values")
        for x in c:
            if x == "":
                bad("row", i, "empty cell; write 'not in file' when the primary source lacks the fact")
                break

    for i, c in rows:
        for m in QUOTE.finditer(c[1]):
            q = m.group(1) or m.group(2)
            for frag in re.split(r"\s*(?:\.\.\.|…|\[\.\.\.\]|\[…\])\s*", q):
                frag = norm(frag).strip(" .,;:")
                if len(frag) < 12:
                    continue
                quotes += 1
                if frag not in hay:
                    failed.append({"line": i + 1, "provenance": c[-1], "quote": frag[:160]})

    for i, l in enumerate(lines):
        plain = unquoted(l)
        if "—" in plain:
            bad("style", i, "em dash outside a quote")
        m = BANNED.search(plain)
        if m:
            bad("style", i, f"banned word '{m.group(0)}' outside a quote")
        m = CLAIMS.search(plain)
        if m:
            bad("style", i, f"corpus claim '{m.group(0)}'; list the sources instead")
        if GATE_CODE.search(plain):
            bad("style", i, "gate code (G1, G2); say the test in plain words")
        if DECIDER.search(plain):
            bad("people", i, "names a decision-maker; the record ties people to offices and roles, never to decisions")
        m = PERSONAL.search(l)
        if m:
            bad("people", i, f"personal contact '{m.group(0)}'; only official mailboxes and contacts a notice publishes")

    check_ranked(ranked, lines, bad)

    prov = {p: sum(1 for c in tally_rows if c[-1] == p) for p in sorted(PROV)}
    st = {s: sum(1 for _, c in rows if c[2] == s) for s in sorted(STATUS)}
    cl = {k: sum(1 for c in tally_rows if c[4] == k) for k in sorted(CLASS)}
    tally = (f"Tally: cells 'not in file' {not_in_file}; evidence rows {len(tally_rows)}; "
             + "; ".join(f"rows {s} {n}" for s, n in st.items() if n) + "; "
             + "; ".join(f"rows from {p} {n}" for p, n in prov.items() if n) + "; "
             + "; ".join(f"rows on a {k} source {n}" for k, n in cl.items() if n))
    last = [l for l in lines if l.startswith("Tally:")]
    if not last or last[-1].strip() != tally:
        bad("tally", 0, "the last Tally line in Audit differs from the count; paste: " + tally)
    return {"problems": problems, "tally": tally,
            "quotes": {"checked": quotes, "not_found": len(failed), "failures": failed},
            "identifiers": identifiers(evidence, resolver, hay)}


def record_resolver():
    """report.py's resolver for the AGENCY in the environment, or None when the record's tools cannot load here."""
    if not os.environ.get("AGENCY"):
        return None
    sys.path.insert(0, TOOLS)
    try:
        import report
    except (ImportError, SystemExit):
        return None
    return report.resolve_any


def bare(ident):
    """The identifier without what a brief writes around it: a kind word before it, a description after a comma or
    in brackets ("PE 0603468E ACX-01, LASSO, FY 2027" -> "0603468E ACX-01")."""
    head = re.split(r"\s+\(|,\s|;\s", ident, maxsplit=1)[0].strip()
    return re.sub(r"^(PE|PIID|notice|contract|award|program element)\s+", "", head, flags=re.I)


def identifiers(evidence, resolver, hay=""):
    """Each tool or repo row's identifier must name a record, office, person, vendor or budget line in the record
    (report.py's resolver), or appear word for word in the record files and sources read (an observation id, a
    report number). A typo or an invented identifier does neither."""
    if resolver is None:
        return {"checked": 0, "unresolved": [], "note": "not checked: set AGENCY so the record's tools load"}
    checked, unresolved = 0, []
    for i, ident, prov in evidence:
        ident = ident.strip("` ")
        if prov not in ("tool", "repo") or not ident or ident.lower().startswith("not in file"):
            continue
        checked += 1
        short = bare(ident) or ident
        if norm(short) in hay or norm(short.split()[0]) in hay and len(short.split()[0]) >= 6:
            continue
        try:
            kind = resolver(ident) or resolver(short)
        except Exception as e:  # a record file this layer lacks: the row cannot be resolved, say why
            unresolved.append({"line": i + 1, "identifier": ident[:120], "why": f"{type(e).__name__}: {e}"[:160]})
            continue
        if not kind:
            unresolved.append({"line": i + 1, "identifier": ident[:120]})
    return {"checked": checked, "unresolved": unresolved}


def check_ranked(ranked, lines, bad):
    if not ranked:
        bad("rank", 0, "no ranked tables under '## Ranked opportunities'")
        return
    ids, seen_groups, prev = set(), [], None
    n = 0
    for i, g, c in ranked:
        n += 1
        if c[0] != str(n):
            bad("rank", i, f"rank {c[0]} out of sequence; expected {n}")
        if c[1] in ids:
            bad("rank", i, f"candidate {c[1]} listed twice")
        ids.add(c[1])
        if g is None:
            bad("rank", i, "table not under a group title (Instruments, Routes, Live signals, Historical, Ruled out)")
            continue
        try:
            f, a, u = (int(x.split("/")[0]) for x in c[6:9])
            score = float(c[9])
        except ValueError:
            bad("rank", i, "scores must read 'n/3' and the score a number")
            continue
        want = round(40 * f / 3 + 35 * a / 3 + 25 * u / 3, 1)
        if abs(want - score) > 0.051:
            bad("rank", i, f"{c[1]} score {score} but the rule gives {want}")
        if c[2] not in TIER:
            bad("rank", i, f"{c[1]} tier '{c[2]}' is not one of {list(TIER)}")
            continue
        if g == 0 and c[4] != "Live":
            bad("rank", i, f"{c[1]} is an instrument that is not Live; only an open instrument can lead")
        if g == 3 and c[4] != "Historical":
            bad("rank", i, f"{c[1]} sits under Historical with status {c[4]}")
        if TIER[c[2]] == 4 and g != 4:
            bad("rank", i, f"{c[1]} is ruled out but sits outside the Ruled out group")
        key = (g, TIER[c[2]], -score, 0 if "primary" in c[11] else 1, int(re.sub(r"\D", "", c[1]) or 0))
        if prev and key < prev:
            bad("rank", i, f"{c[1]} breaks the published order (group, tier, score, source class, id)")
        prev = key
        if not seen_groups or seen_groups[-1] != g:
            seen_groups.append(g)

    # rule 4: instruments of distinct offices first, then the first route of each office not yet named
    pool = [c for _, g, c in ranked if g == 0] + [c for _, g, c in ranked if g == 1]
    order, offices = [], []
    for c in pool:
        office = c[3].split(":")[0].strip()
        if office not in offices:
            offices.append(office)
            order.append(c[10])
        if len(order) == 3:
            break
    lo = next((i for i, l in enumerate(lines) if l.startswith("**Lead order:**")), None)
    if lo is None:
        bad("lead", 0, "no '**Lead order:**' line in the Bottom line")
        return
    at = [lines[lo].find(x) for x in order]
    if any(p < 0 for p in at) or at != sorted(at):
        bad("lead", lo, "Lead order line must name, in this order, the rule's lead, second and third: " + ", ".join(order))


if __name__ == "__main__":
    BRIEF = sys.argv[1]
    text = open(BRIEF).read()
    print(json.dumps(check(text, haystack(sys.argv[2:]), record_resolver()), indent=1))
