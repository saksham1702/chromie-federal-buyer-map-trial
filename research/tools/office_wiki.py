"""A page per program office, and a model that reads a notice against them.

A notice a contracting office filed without naming the program office behind it is read by a model against the
office directory (one line per program office: its name and the program names its records use) and the pages of
the offices whose records share the notice's program names. The model names one office or none, and quotes the
notice words and the page line that tie them; the rules keep an answer only when both quotes are verbatim and the
notice words are more than generic words. A reading stays a reading: it never moves the notice from the office that filed it.
The same reading, each kind with its own prompt, places the live contract awards a contracting office signed, the SBIR/STTR
topics a command published and the committee statements addressed to the department.

    python research/tools/office_wiki.py page "PMW 160"
    python research/tools/office_wiki.py read NOTICE_ID
    python research/tools/office_wiki.py build [--check]
    python research/tools/office_wiki.py trial [--kind notices|awards|topics] [--limit N]
    python research/tools/office_wiki.py --selfcheck
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from backtest import CORPUS, chain  # noqa: E402
from llm import structured  # noqa: E402
from pages import OFFICE_CODE_RE, OWNER_TYPES, READS, SOLICITATION_RE, Layer, compact, office_words, plain_title, rank_offices, read_offices, title_words  # noqa: E402
from pulse import ENDS_RE, office_name  # noqa: E402
from reader import flatten  # noqa: E402

SHOWN = 6
SYSTEM = ("You read one U.S. Navy procurement notice that its contracting office filed without naming the program office "
          "behind it, and name the program office it comes from, using only the office directory and the office pages "
          "given. Answer with: office, copied exactly from the directory (the text before the first colon of a line), or "
          "empty when nothing given ties the notice to one office; notice_words, a few words copied exactly from the "
          "notice that tie it to that office; page_line, one line copied exactly from that office's directory entry or "
          "page that names the same program or work; reason, at most 25 words. A contracting office, a vehicle, a NAICS "
          "code or a generic word (support, engineering, services, training) never ties a notice to an office.")

def system_for(record: str, basis: str, tie: str, never: str) -> str:
    return (f"You read one {record} and name the program office {tie}, using only the office directory and the office pages "
            "given. Answer with: office, copied exactly from the directory (the text before the first colon of a line), or "
            f"empty when nothing given ties it to one office; notice_words, a few words copied exactly from the {basis} that "
            "tie it to that office; page_line, one line copied exactly from that office's directory entry or page that names "
            f"the same program or work; reason, at most 25 words. The page line names the same program, system, platform or "
            "product the words name, by its name, acronym or number; an office's name or mission area alone (ship, aircraft, "
            f"undersea, networks, communications) never ties it. {never} or a generic word (support, engineering, services, "
            "training) never ties it to an office.")


# kind -> (the prompt, how the record is introduced, whose program names the pages share)
KINDS = {
    "notices": (SYSTEM, "Notice filed at", "the notice's"),
    "awards": (system_for("U.S. Navy contract award that its contracting office signed, as its description states it", "award description",
                          "whose program or work the award buys", "A contracting office, a funding office, a vendor, a vehicle, a NAICS code"),
               "Contract award signed at", "the award's"),
    "topics": (system_for("U.S. Navy SBIR or STTR topic that its command published", "topic",
                          "whose program the topic's work serves or would transition to", "The command that published it, the SBIR program, a phase"),
               "Topic published by", "the topic's"),
    "directives": (system_for("statement a congressional committee report addresses to the Department of the Navy", "statement",
                              "that manages the program or work the statement addresses", "The department, a committee, a fiscal year, an account"),
                   "Committee statement addressed to", "the statement's"),
}
FAMILY = {"notices": "notice", "awards": "incumbent", "topics": "programs", "directives": "congress"}

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["office", "notice_words", "page_line", "reason"],
          "properties": {"office": {"type": "string"}, "notice_words": {"type": "string"}, "page_line": {"type": "string"},
                         "reason": {"type": "string"}}}


def owners(corpus: dict) -> list[str]:
    return [oid for oid, o in corpus["orgs"].items() if o.get("org_type") in OWNER_TYPES]


def program_names(by_word: dict[str, Counter], known: set[str], oid: str, top: int = 12) -> list[str]:
    """The program names an office's records use most, in capitals as the titles write them."""
    mine = sorted(((w, c[oid]) for w, c in by_word.items() if w in known and c[oid] > 0), key=lambda x: (-x[1], x[0]))
    return [w.upper() for w, _ in mine[:top]]


def directory(corpus: dict, by_word: dict[str, Counter], known: set[str]) -> dict[str, str]:
    """Office name -> its directory line, for every program office whose records carry a program name."""
    out = {}
    for oid in owners(corpus):
        if names := program_names(by_word, known, oid):
            name = office_name(oid, corpus["orgs"])
            out[name] = f"{name}: {corpus['orgs'][oid]['name']}; program names: {', '.join(names)}"
    return out


def page(corpus: dict, oid: str, by_word: dict[str, Counter], known: set[str], skip: frozenset = frozenset()) -> str:
    """One office's page from the record: where it sits, its program names, and its newest forecast rows, notices,
    contract work and topics, each a line of the record's own words. `skip` leaves records out, as a trial must."""
    orgs = corpus["orgs"]
    mine = [e for e in corpus["events"] if e["org"] == oid and e["id"] not in skip]
    newest = lambda fam: sorted((e for e in mine if e["family"] == fam), key=lambda e: e["available_by"], reverse=True)
    rows = [n for n in corpus["needs"] if n["owner_id"] == oid and f"need:{n['key']}" not in skip]
    work = Counter(plain_title(e["title"])[:80] for e in mine if e["family"] == "incumbent" and ": " in e["title"])
    lines = [f"## {office_name(oid, orgs)}: {orgs[oid]['name']}",
             "above it: " + (" > ".join(office_name(x, orgs) for x in chain(oid, orgs)[1:]) or "-"),
             "program names: " + (", ".join(program_names(by_word, known, oid)) or "none")]
    lines += [f"forecast row: {n['title'][:100]}" for n in rows[-SHOWN:]]
    lines += [f"notice {e['available_by']}: {plain_title(e['title'])[:100]}" for e in newest("notice")[:SHOWN]]
    lines += [f"contract work ({n}): {w}" for w, n in sorted(work.items(), key=lambda x: (-x[1], x[0]))[:SHOWN]]
    lines += [f"topic: {plain_title(e['title'])[:100]}" for e in newest("programs")[:3]]
    return "\n".join(lines)


def masked(text: str, orgs: dict) -> str:
    """A notice with every office code and organization name taken out: what a notice that names no office reads like."""
    names = {o.get("acronym", "") for o in orgs.values()} | {o["name"] for o in orgs.values()}
    text = OFFICE_CODE_RE.sub("[office]", text)
    for name in sorted((n for n in names if len(n) >= 4), key=len, reverse=True):
        text = re.sub(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", "[office]", text, flags=re.I)
    return text


def ask(title: str, text: str, filed: str, corpus: dict, by_word: dict[str, Counter], known: set[str], records: int,
        skip: frozenset = frozenset(), replay_only: bool = False, kind: str = "notices") -> dict:
    """The model's reading of one record, kept only when the rules hold; the answer, how it was had, and what failed."""
    system, lead, whose = KINDS[kind]
    listing = directory(corpus, by_word, known)
    shortlist = [oid for oid, _, _ in rank_offices(title, by_word, records, known)]
    pages_ = {office_name(oid, corpus["orgs"]): page(corpus, oid, by_word, known, skip) for oid in shortlist}
    user = (f"{lead} {filed}:\n{title}\n{text[:2500]}\n\nOffice directory:\n" + "\n".join(listing.values())
            + (f"\n\nPages of the offices whose records share {whose} program names:\n\n" + "\n\n".join(pages_.values()) if pages_ else ""))
    answer, how = structured(system, user, SCHEMA, "office_read", replay_only=replay_only)
    return {**answer, "problems": problems(answer, f"{title} {text}", listing, pages_), "cassette": how["cassette"]}


def problems(answer: dict, notice: str, listing: dict[str, str], pages_: dict[str, str]) -> list[str]:
    """What the notice and the pages do not support: an office outside the directory, a quote not verbatim, notice
    words that are only generic words."""
    office = answer["office"].strip()
    if not office:
        return []
    out = []
    if office not in listing:
        out.append("office is not in the directory")
    if not answer["notice_words"] or flatten(answer["notice_words"]).lower() not in flatten(notice).lower():
        out.append("notice words are not in the notice verbatim")
    elif not title_words(answer["notice_words"]):
        out.append("notice words are only generic words")
    source = f"{listing.get(office, '')}\n{pages_.get(office, '')}"
    if not answer["page_line"] or flatten(answer["page_line"]).lower() not in flatten(source).lower():
        out.append("page line is not on the office's page verbatim")
    return out


def unread(corpus: dict, kind: str, read: dict) -> list[dict]:
    """The records of a kind the model reads: notices filed at a contracting office no record places, the live awards a
    contracting office signed, and the topics and committee statements no program office was named for."""
    orgs = corpus["orgs"]
    kind_of = lambda e: orgs.get(e["org"], {}).get("org_type")  # noqa: E731
    mine = [e for e in corpus["events"] if e["family"] == FAMILY[kind] and kind_of(e) not in OWNER_TYPES]
    if kind == "notices":
        return [e for e in mine if e["id"] not in read and kind_of(e) == "contracting_office"]
    if kind == "awards":
        as_of = max(e["available_by"] for e in corpus["events"])
        return [e for e in mine if (m := ENDS_RE.search(e["title"])) and m.group(1) >= as_of]
    return mine


def build(corpus: dict, replay_only: bool = False, workers: int = 8) -> dict:
    """The model's reading of every unread record of each kind, each with its quotes and what the rules found; an answer
    the rules refuse is kept with its problems and places nothing."""
    by_word, words_of, known = office_words(corpus)
    read = read_offices(corpus, Layer(corpus, [], routes=[]).org_id)
    todo = [(kind, e) for kind in KINDS for e in unread(corpus, kind, read)]
    one = lambda job: ask(plain_title(job[1]["title"]), job[1]["text"], office_name(job[1]["org"], corpus["orgs"]) or "the department", corpus,
                          by_word, known, len(words_of), replay_only=replay_only, kind=job[0])
    with ThreadPoolExecutor(workers) as pool:
        answers = list(pool.map(one, todo))
    out: dict[str, dict] = {kind: {} for kind in KINDS}
    for (kind, e), a in zip(todo, answers):
        out[kind][e["id"]] = {k: a[k] for k in ("office", "notice_words", "page_line", "problems", "cassette")}
    return out


def trial(corpus: dict, limit: int = 0, workers: int = 8, replay_only: bool = False, kind: str = "notices") -> dict:
    """Each record that names its program office, with its office names masked and the records tied to it left out of the
    pages: does the model name the office the record named? Notices are grouped by solicitation number; an award counts
    when its description or the notice under its solicitation named the office, a topic when its text did."""
    by_word, words_of, known = office_words(corpus)
    under: dict[str, list[dict]] = {}
    for e in corpus["events"]:
        if kind == "notices" and e["family"] == "notice" and (m := SOLICITATION_RE.search(e["text"])):
            under.setdefault(compact(m.group(1)), []).append(e)
        elif kind != "notices" and e["family"] == FAMILY[kind] and (kind != "awards" or "placed by the office" in e["text"]):
            under[e["id"]] = [e]
    jobs = []
    for group in under.values():
        stated = [e for e in group if corpus["orgs"].get(e["org"], {}).get("org_type") in OWNER_TYPES]
        if not stated:
            continue
        trimmed, out_ids = dict(by_word), [e for e in group if e["id"] in words_of]
        for e in out_ids:
            for w in words_of[e["id"]]:
                trimmed[w] = trimmed[w].copy() if trimmed[w] is by_word[w] else trimmed[w]
                trimmed[w][e["org"]] -= 1
        skip = frozenset(e["id"] for e in group)
        jobs += [(e, trimmed, len(words_of) - len(out_ids), skip) for e in stated]
    jobs = jobs[:limit] if limit else jobs
    orgs = corpus["orgs"]

    def one(job):
        e, trimmed, records, skip = job
        title = masked(plain_title(e["title"]), orgs)
        got = ask(title, masked(e["text"], orgs), "the command" if kind == "topics" else "the contracting office", corpus, trimmed, known, records,
                  skip, replay_only, kind)
        guess = rank_offices(title, trimmed, records, known)
        return e, got, guess[0][0] if guess else ""

    with ThreadPoolExecutor(workers) as pool:
        done = list(pool.map(one, jobs))
    by_name = {office_name(oid, orgs): oid for oid in owners(corpus)}
    tally, misses = Counter(), []
    for e, got, word_first in done:
        said = by_name.get(got["office"].strip(), "") if not got["problems"] else ""
        verdict = {kind: "none" if not oid else "right" if oid == e["org"] else "one level apart" if e["org"] in chain(oid, orgs) or oid in chain(e["org"], orgs)
                   else "wrong" for kind, oid in (("model", said), ("words", word_first))}
        tally.update(f"{kind}: {v}" for kind, v in verdict.items())
        if said and said == word_first:
            tally[f"model and words agree: {verdict['model']}"] += 1
        if got["problems"]:
            tally["model answers refused by the rules"] += 1
        if verdict["model"] == "wrong":
            misses.append({"record": plain_title(e["title"])[:90], "office": office_name(e["org"], orgs), "model": got["office"], "quote": got["notice_words"]})
    return {kind: len(done), "tally": dict(sorted(tally.items())), "misses": misses}


def selfcheck() -> int:
    orgs = {"p": {"acronym": "PMW 160", "name": "Tactical Networks", "parent": "", "org_type": "program_office"},
            "q": {"acronym": "PMW 101", "name": "MIDS Program Office", "parent": "", "org_type": "program_office"}}
    assert masked("in support of PMW 160 Tactical Networks for ADNS", orgs) == "in support of [office] [office] for ADNS"
    listing = {"PMW 160": "PMW 160: Tactical Networks; program names: ADNS, CANES"}
    ok = {"office": "PMW 160", "notice_words": "ADNS Increment III", "page_line": "program names: ADNS, CANES", "reason": ""}
    assert problems(ok, "RFP for ADNS Increment III routers", listing, {}) == []
    assert problems({**ok, "office": "PMW 999"}, "RFP for ADNS Increment III routers", listing, {}) == ["office is not in the directory", "page line is not on the office's page verbatim"]
    assert problems({**ok, "notice_words": "ADNS Inc 3"}, "RFP for ADNS Increment III routers", listing, {}) == ["notice words are not in the notice verbatim"]
    assert problems({**ok, "notice_words": "support services"}, "support services for ADNS", listing, {}) == ["notice words are only generic words"]
    assert problems({**ok, "office": ""}, "anything", listing, {}) == [], "no office is an answer, not a failure"
    print("office_wiki selfcheck ok")
    return 0


def main(argv: list[str]) -> int:
    if "--selfcheck" in argv:
        return selfcheck()
    ap = argparse.ArgumentParser(prog="office_wiki.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("page").add_argument("office")
    sub.add_parser("read").add_argument("notice_id")
    sub.add_parser("build").add_argument("--check", action="store_true", help="replay the saved answers and compare with the saved file")
    t = sub.add_parser("trial")
    t.add_argument("--limit", type=int, default=0)
    t.add_argument("--kind", choices=[k for k in KINDS if k != "directives"], default="notices")
    args = ap.parse_args(argv)
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    by_word, words_of, known = office_words(corpus)
    if args.cmd == "page":
        oid = next((oid for oid in owners(corpus) if office_name(oid, corpus["orgs"]).lower() == args.office.lower()), None)
        print(page(corpus, oid, by_word, known) if oid else f"no program office named {args.office!r}")
    elif args.cmd == "read":
        e = next((e for e in corpus["events"] if e["id"].startswith(args.notice_id)), None)
        if e is None:
            print(f"no statement {args.notice_id}", file=sys.stderr)
            return 1
        print(json.dumps(ask(plain_title(e["title"]), e["text"], office_name(e["org"], corpus["orgs"]), corpus, by_word, known, len(words_of)), indent=1))
    elif args.cmd == "build":
        out = build(corpus, replay_only=args.check)
        text = json.dumps(out, indent=1, sort_keys=True) + "\n"
        for kind, reads in out.items():
            placed = sum(1 for a in reads.values() if a["office"] and not a["problems"])
            print(f"{kind}: {len(reads)} read, {placed} placed by the model with both quotes verbatim")
        if args.check:
            same = READS.exists() and READS.read_text(encoding="utf-8") == text
            print("office reads match the saved file" if same else "office reads differ from the saved file", file=sys.stderr)
            return 0 if same else 1
        READS.write_text(text, encoding="utf-8")
    else:
        print(json.dumps(trial(corpus, args.limit, kind=args.kind), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
