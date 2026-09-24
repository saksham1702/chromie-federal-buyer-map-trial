#!/usr/bin/env python3
"""From what a company sells to one outreach e-mail, walked by a model through the Navy record: the agency, the command,
the program executive office and the program office that buys the capability, that office's requirements, the
initiatives above it, the people the record ties to it, and a letter written from those alone.

Every judgment is a recorded model call: the search terms, each next move, the chain, the letter. The code looks things
up (the views of pages.Layer and `initiatives`) and checks what the model returns, and decides nothing else:
- each hop of the chain is above the program office in the organization tree and of its level, no level the tree holds
  is skipped, and the program office was opened and buys (a program office, a technical office, a department or a field
  activity, never a command or a contracting office);
- every requirement and initiative was shown, its quote is in the record verbatim, a requirement sits under the program
  office and an initiative sits under it, above it or at the department;
- every person was shown and the record ties them to the chain; every route was shown and leads into the chain;
- the letter goes to a chosen person or route, cites chosen records, names no other person, and every number, date and
  identifier in it is in the evidence or the profile.
A failed check gets one repair call that lists the problems; a run that still fails is kept and marked refused. A
profile the record holds nothing for comes back with no chain and no letter.

    python research/tools/outreach.py run --company NAME --profile TEXT_OR_FILE [--steps 32] [--check]
    python research/tools/outreach.py show SLUG
    python research/tools/outreach.py --selfcheck
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest import CORPUS, RESEARCH, chain, register_problems  # noqa: E402
from llm import MODEL, structured  # noqa: E402
from pages import Layer  # noqa: E402
from people import contacts_for, routes_for  # noqa: E402
from pulse import load_people, office_name  # noqa: E402
from reader import flatten  # noqa: E402

OUT = RESEARCH / "results" / "outreach"
TOOLS = ("search", "office", "cell", "topics", "people", "neighbors", "initiatives")
INITIATIVE_FAMILIES = ("leaders", "congress", "budget", "oversight", "conference", "news", "organization")
BUYING_TYPES = ("program_office", "technical_office", "department", "field_activity")  # where a requirement is owned, below a command
# The levels above a program office, each with the organization types that hold it; a level the record shows must be named.
LEVELS = {"peo": ("program_executive_office",), "command": ("contracting_activity", "acquisition_portfolio", "field_activity"), "agency": ("agency",)}
DEFAULT_STEPS = 32
MAX_NEXT = 3
SHOWN = 12
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9/.-]*\d[A-Za-z0-9/.-]*")
INTERNAL_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")  # a record's key in the corpus, never public
SEARCHED = ("search and topics match the whole term as written, case aside, so a term is a short name the record itself would "
            "write, one to three words (Link 16, MIDS, UUV, unmanned undersea, availability planning), never a long description")
PLAIN = ("Write in a formal register, past and present tense, no em dashes, and never with words such as likely, probably, "
         "imminent, expected or soon.")


def obj(**fields) -> dict:
    return {"type": "object", "additionalProperties": False, "required": list(fields), "properties": fields}


def arr(item: dict) -> dict:
    return {"type": "array", "items": item}


S, N, B = {"type": "string"}, {"type": "number"}, {"type": "boolean"}
CITED = arr(obj(identifier=S, quote=S, why=S))

SYSTEM_SEED = ("You find where the U.S. Navy buys what one company sells, in a record of dated, sourced statements. From the "
               "profile, name up to eight search terms a Navy forecast row, SBIR topic, notice, award or congressional statement "
               "would use for it: capability words, not marketing words; two may be the broader mission areas it serves; "
               + SEARCHED + "; each with its promise (0 to 1), how likely the term leads to the office that buys it. Then "
               "state in one sentence what would count as a requirement this company could bid on or team for. Terms are words "
               "to look up, never programs or offices you assume exist.")
SCHEMA_SEED = obj(terms=arr(obj(term=S, promise=N)), relevant_when=S)
SYSTEM_STEP = ("You walk a record of U.S. Navy procurement statements for one company to find the one program "
               "office that buys what it sells, that office's requirements, the initiatives that make the capability matter "
               "there (leaders' priorities, congressional directives, budget lines, oversight findings), and the people and "
               "routes into it. You see the profile, the path so far and the record's answer to your last move. Judge the "
               "answer's relevance to the company (0 to 1). Record findings only for a record the answer shows that bears on "
               "this company: its identifier exactly as shown (id or need_key), a few words copied exactly from its title or "
               "text, and why in one sentence. Then choose up to three next moves, each with a one-line reason and its promise (0 "
               "to 1), how likely it leads to the buying office, its requirements or its people; the walk takes the most "
               "promising move of every branch next, so a lead elsewhere is not lost: open an office "
               "where the signal is (office shows its forecast rows, topics, people and routes; initiatives shows what leaders, "
               "Congress, the budget and oversight say in its chain), follow a record (cell), climb or step sideways "
               "(neighbors), or search the record's own words. A program_office, technical_office, department or field_activity owns requirements; "
               "a command or contracting office files and signs for them. Stop the branch when the "
               "answer shows nothing for this company. "
               "Tools: search TERM; office NAME; cell NEED_KEY_OR_ID; topics TERM; people OFFICE; neighbors OFFICE; initiatives "
               "OFFICE. " + SEARCHED + ". " + PLAIN)
SCHEMA_STEP = obj(relevance=N, findings=CITED, next=arr(obj(tool={"type": "string", "enum": list(TOOLS)}, argument=S, reason=S, promise=N)),
                  stop_branch=B, note=S)
SYSTEM_CHAIN = ("From the walk below, name the one buying chain in the U.S. Navy for this company's capability, each office "
                "written exactly as the record writes it: the agency; the command; the program executive office; and the "
                "program office that owns the requirement, which must be one the walk opened. The levels above it are the ones "
                "the office view lists in its chain; leave a level empty only when that chain holds none. Then the requirements of that program office or under it that the company could bid on or team for, "
                "and the initiatives in its chain or at the department that make the capability matter there; each by its "
                "identifier as shown, with words copied exactly from that record and why in one sentence. Then whom to write "
                "to: people and routes the walk showed for that chain, each with why this is the one to write to; the program "
                "manager or the requirement side answers about the need, a contracting point of contact about one procurement. When the walk "
                "shows no program office that buys what the company sells, answer fit false with the reason in one sentence "
                "and leave the rest empty. Never name an office, record, person or route the walk did not show. " + PLAIN)
SCHEMA_CHAIN = obj(fit=B, agency=S, command=S, peo=S, program_office=S, why_office=S, requirements=CITED, initiatives=CITED,
                   people=arr(obj(name=S, why=S)), routes=arr(obj(route=S, why=S)), no_fit=S)
SYSTEM_EMAIL = ("Write one outreach e-mail from the company to a chosen person, the program side before a contracting point of "
                "contact; write to a route's office only when no person was chosen. Tailor it to this office: name the "
                "program office and the requirement by the record's own title and identifier, describe what the company sells in "
                "the record's own terms (never saying that it matches them), cite the initiative that makes it matter when one was chosen, and ask for one concrete next step (a short "
                "call, a capability briefing, or where to send a white paper). Use only facts from the evidence and the "
                "company's profile: no number, date, identifier, program, contract, office or person the evidence does not "
                "carry, and no claim about the company beyond its profile. The bracketed keys in the evidence are internal and "
                "go only in cites; the letter names a record by its title and by the solicitation, notice, contract or forecast "
                "number its text carries. Under 220 words. " + PLAIN + " Answer with: to (the "
                "chosen person's name exactly, or the office a chosen route names, its name without the link), subject, body, and cites (the "
                "keys the evidence shows in square brackets, without the brackets, of the records the body refers to).")
SCHEMA_EMAIL = obj(to=S, subject=S, body=S, cites=arr(S))


# ------------------------------------------------------------------ the layer as the model sees it

class Walk:
    """The layer behind seven views, with a record of everything shown: a finding, a chain or a letter may use only that."""

    def __init__(self, layer: Layer):
        self.layer = layer
        self.shown: dict[str, dict] = {}   # record id or forecast key -> the brief as shown
        self.opened: set[str] = set()      # offices the model opened
        self.people: dict[str, dict] = {}  # name -> the contact as shown
        self.routes: dict[str, dict] = {}  # recommendation -> the route as shown
        self.events = {e["id"]: e for e in layer.events}
        self.needs = {n["key"]: n for n in layer.needs}

    def call(self, tool: str, argument: str) -> dict:
        answer = self.initiatives(argument) if tool == "initiatives" else getattr(self.layer, tool)(argument)
        if tool in ("search", "topics") and not (answer.get("statements") or answer.get("topics") or answer.get("forecast_rows_total")):
            answer["note"] = "no record carries this term as written; try a shorter name the record writes"
        if isinstance(answer.get("offices"), dict):  # the tally by name, with each office's type: a buyer is told from a command
            answer["offices"] = [{"office": n, "type": self.layer.orgs.get(self.layer.org_id(n) or "", {}).get("org_type", ""), "statements": c}
                                 for n, c in answer["offices"].items()]
        if tool in ("office", "initiatives") and "error" not in answer:
            self.opened.add(self.layer.org_id(argument))
        self.note(answer)
        return answer

    def note(self, found) -> None:
        if isinstance(found, list):
            for x in found:
                self.note(x)
        elif isinstance(found, dict):
            if "id" in found and "family" in found:
                self.shown[found["id"]] = found
            elif "need_key" in found and "title" in found:
                self.shown[found["need_key"]] = found
            elif {"name", "role", "observed_at"} <= set(found):
                self.people[found["name"]] = found
            elif {"recommendation", "route"} <= set(found):
                self.routes[found["recommendation"]] = found
            for v in found.values():
                self.note(v)

    def initiatives(self, name: str) -> dict:
        """What leaders, Congress, the budget, oversight, conferences, news and reorganizations say in an office's chain
        and under it, and the ones filed elsewhere that the model reads to it; newest first. Department-wide statements
        name no office and are counted, not listed: search finds them by topic."""
        lay = self.layer
        oid = lay.org_id(name)
        if not oid:
            return {"office": name, "error": "no organization by that name; use neighbors or search to find one"}
        near = lay.subtree(oid) | set(chain(oid, lay.orgs))
        said = [e for e in lay.events if e["family"] in INITIATIVE_FAMILIES and e["available_by"] <= lay.as_of]
        mine = sorted((e for e in said if e["org"] in near or (e.get("model_read") or ("",))[0] in lay.subtree(oid)),
                      key=lambda e: (e["available_by"], e["id"]), reverse=True)
        wide = sum(1 for e in said if lay.orgs.get(e["org"], {}).get("org_type", "agency") == "agency")
        return {"office": office_name(oid, lay.orgs), "statements": len(mine), "families": dict(Counter(e["family"] for e in mine).most_common()),
                "newest": [{**lay.brief(e), "text": e["text"][:300]} for e in mine[:SHOWN]], "department_wide": wide}

    def text(self, identifier: str) -> str:
        if identifier in self.events:
            e = self.events[identifier]
            return f"{e['title']} {e['text']}"
        return self.needs[identifier]["title"] if identifier in self.needs else ""

    def home(self, identifier: str) -> set[str]:
        """The offices a record belongs to: where it was filed or read to, or the office that owns a forecast row."""
        if identifier in self.needs:
            return {self.needs[identifier]["owner_id"]}
        e = self.events.get(identifier, {})
        return {e.get("org", ""), e.get("filed", ""), (e.get("model_read") or ("",))[0]} - {""}

    def ancestors(self, oid: str) -> list[str]:
        """The office and every organization above it, the agency included."""
        out, orgs = [], self.layer.orgs
        while oid and oid in orgs and oid not in out:
            out.append(oid)
            oid = orgs[oid]["parent"]
        return out


# ------------------------------------------------------------------ the checks

def verbatim(quote: str, text: str) -> bool:
    return bool(quote.strip()) and flatten(quote).lower() in flatten(text).lower()


def cited_problems(walk: Walk, rows: list[dict], kind: str, fits) -> list[str]:
    out = []
    for r in rows:
        ident = r["identifier"]
        if ident not in walk.shown:
            out.append(f"{kind} {ident} was not shown")
        elif not verbatim(r["quote"], walk.text(ident)):
            out.append(f"{kind} {ident}: the quote is not in the record verbatim")
        elif not fits(walk.home(ident)):
            out.append(f"{kind} {ident} sits outside the chain")
    return out


def chain_problems(walk: Walk, a: dict) -> list[str]:
    """What the record does not support in a chain; no fit is an answer, not a failure."""
    if not a["fit"]:
        return [] if a["no_fit"].strip() else ["no fit given without a reason"]
    lay = walk.layer
    po = lay.org_id(a["program_office"])
    if not po:
        return [f"program office {a['program_office']!r} is not an organization in the record"]
    out = [] if lay.orgs[po].get("org_type") in BUYING_TYPES else [f"{a['program_office']} is a {lay.orgs[po].get('org_type')}, not a buying office"]
    if po not in walk.opened:
        out.append(f"{a['program_office']} was not opened")
    up = walk.ancestors(po)
    for label, types in LEVELS.items():
        oid = lay.org_id(a[label]) if a[label].strip() else None
        held = next((x for x in up[1:] if lay.orgs[x].get("org_type") in types), None)
        holds = f"the record puts it under {office_name(held, lay.orgs)}" if held else f"the record holds no {label} over it; leave it empty"
        if a[label].strip() and oid not in up[1:]:
            out.append(f"{label} {a[label]!r} is not above {a['program_office']} in the record; {holds}")
        elif oid and lay.orgs[oid].get("org_type") not in types:
            out.append(f"{label} {a[label]!r} is a {lay.orgs[oid].get('org_type')}, not a {label}; {holds}")
        elif held and not oid:
            out.append(f"{a['program_office']} sits under {office_name(held, lay.orgs)}; name it as the {label}")
    tree, above = lay.subtree(po), set(up)
    if not a["requirements"]:
        out.append("no requirement named")
    out += cited_problems(walk, a["requirements"], "requirement", lambda home: bool(home & tree))
    out += cited_problems(walk, a["initiatives"], "initiative",
                          lambda home: not home or bool(home & (tree | above)) or all(lay.orgs.get(h, {}).get("org_type") == "agency" for h in home))
    for r in a["initiatives"]:
        family = walk.events[r["identifier"]]["family"] if r["identifier"] in walk.events else "forecast row" if r["identifier"] in walk.needs else ""
        if family and family not in (*INITIATIVE_FAMILIES, "programs"):
            out.append(f"initiative {r['identifier']} is a {family} record, not what leaders, Congress, the budget, oversight or a topic says")
    both = {r["identifier"] for r in a["requirements"]} & {r["identifier"] for r in a["initiatives"]}
    out += [f"{ident} is named both as a requirement and as an initiative" for ident in sorted(both)]
    ours = {p["name"] for p in contacts_for(up, lay.roster, lay.as_of, limit=100)}
    # A refusal names what the walk did show for the chain, so the repair copies it rather than guessing again.
    mine = sorted(n for n in walk.people if n in ours)
    out += [f"person {p['name']!r} was not shown for this chain (shown for it: {', '.join(mine) or 'no one'})"
            for p in a["people"] if p["name"] not in walk.people or p["name"] not in ours]
    ways = [r["recommendation"] for r in routes_for(up, lay.routes, lay.routes_by) if r["recommendation"] in walk.routes]
    out += [f"route {r['route'][:60]!r} was not shown for this chain (shown for it: {' | '.join(w[:120] for w in ways) or 'none'})" for r in a["routes"]
            if len(r["route"].strip()) < 12 or not any(verbatim(r["route"], w) for w in ways)]
    if not a["people"] and not a["routes"]:
        out.append("no one to write to")
    return out + register_problems(" ".join([a["why_office"], *(r["why"] for k in ("requirements", "initiatives", "people", "routes") for r in a[k])]))


def evidence(walk: Walk, a: dict) -> str:
    """What the letter may say: the chain, each chosen record in full, the chosen people and routes as the record holds them."""
    lay = walk.layer
    lines = ["Chain: " + " > ".join(f"{office_name(o, lay.orgs)} ({lay.orgs[o]['name']})" for o in reversed(walk.ancestors(lay.org_id(a["program_office"]))))]
    for kind in ("requirements", "initiatives"):
        lines += [f"[{r['identifier']}] {kind[:-1].title()}: {walk.text(r['identifier'])[:700]}" for r in a[kind]]
    for p in a["people"]:
        c = walk.people[p["name"]]
        lines.append(f"Person: {c['name']}, {c['title']}, {c['office']}, observed {c['observed_at']}, e-mail {c['email'] or 'none on record'}")
    lines += [f"Route: {w} (observed {way['observed_at']})" for r in a["routes"] for w, way in walk.routes.items() if verbatim(r["route"], w)]
    return "\n".join(lines)


def email_problems(walk: Walk, a: dict, e: dict, proof: str, profile: str) -> list[str]:
    out = []
    names = {p["name"] for p in a["people"]}
    if e["to"] not in names and not any(verbatim(e["to"], r["route"]) for r in a["routes"]):
        out.append(f"the letter goes to {e['to']!r}, not a chosen person or route")
    chosen = {r["identifier"] for k in ("requirements", "initiatives") for r in a[k]}
    cites = [c.strip("[] ") for c in e["cites"]]
    out += [f"cites {c}, which is not the bracketed key of a chosen record" for c in cites if c not in chosen]
    if not {r["identifier"] for r in a["requirements"]} & set(cites):
        out.append("cites no requirement")
    letter = f"{e['subject']}\n{e['body']}"
    known = INTERNAL_RE.sub(" ", flatten(f"{proof}\n{profile}").lower())
    out += [f"names the internal key {k}" for k in sorted(set(INTERNAL_RE.findall(letter)))]
    for tok in sorted({t.rstrip(".-/") for t in TOKEN_RE.findall(letter)}):
        if not re.search(rf"(?<![a-z0-9]){re.escape(tok.lower())}(?![a-z0-9])", known):
            out.append(f"{tok!r} is in no evidence")
    body = flatten(letter).lower()
    out += [f"names {p['name']}, who was not chosen" for p in walk.layer.roster
            if p["name"] not in names and len(p["name"]) > 6 and flatten(p["name"]).lower() in body]
    if "—" in letter:
        out.append("em dash")
    return out + register_problems(letter)


# ------------------------------------------------------------------ the walk

def compact(found, limit: int = 6000) -> str:
    text = json.dumps(found, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + " ...[cut]"


def next_move(frontier: list[dict]) -> dict:
    """The frontier holds every move not yet walked, from every branch; the most promising goes next, the newest first
    among equals, so one strong branch cannot spend the budget while a better lead waits."""
    return frontier.pop(max(range(len(frontier)), key=lambda i: (frontier[i]["promise"], i)))


def outreach(layer: Layer, company: str, profile: str, steps: int = DEFAULT_STEPS, model: str = MODEL, replay_only: bool = False) -> dict:
    walk, calls = Walk(layer), []

    def ask(system, user, schema, name):
        out, meta = structured(system, user, schema, name, model=model, replay_only=replay_only)
        calls.append({"name": name, "cassette": meta["cassette"], "replayed": meta["replayed"], "usage": meta["usage"]})
        return out

    def checked(system, user, schema, name, problems):
        """One call, and one repair call when the checks refuse it."""
        answer = ask(system, user, schema, name)
        found = problems(answer)
        if found:
            answer = ask(system, f"{user}\n\nYour last answer: {json.dumps(answer, ensure_ascii=False)}\nThe checks refused it: "
                         + "; ".join(found) + ". Answer again, fixing these and changing nothing the checks accepted.", schema, name + "_repair")
            found = problems(answer)
        return answer, found

    who = f"Company: {company}\nProfile: {profile}"
    seed = ask(SYSTEM_SEED, who, SCHEMA_SEED, "outreach_seed")
    frontier = [{"tool": "search", "argument": t["term"].strip(), "reason": "seed term", "promise": t["promise"], "depth": 0, "path": [], "from": 0}
                for t in seed["terms"][:8] if t["term"].strip()]
    visited, log, findings, dropped = set(), [], [], 0
    while frontier and len(log) < steps:
        move = next_move(frontier)
        if (move["tool"], move["argument"].lower()) in visited:
            continue
        visited.add((move["tool"], move["argument"].lower()))
        answer = walk.call(move["tool"], move["argument"])
        path = move["path"] + [f"{move['tool']} {move['argument']}"]
        judged = ask(SYSTEM_STEP, f"{who}\nRelevant when: {seed['relevant_when']}\nPath: {' > '.join(path)}\nDepth: {move['depth']}. "
                     f"Steps left: {steps - len(log) - 1}.\nAnswer from the record:\n{compact(answer)}", SCHEMA_STEP, "outreach_step")
        kept = [{**f, "path": path} for f in judged["findings"] if f["identifier"] in walk.shown and verbatim(f["quote"], walk.text(f["identifier"]))]
        dropped += len(judged["findings"]) - len(kept)
        findings += kept
        log.append({"n": len(log) + 1, "tool": move["tool"], "argument": move["argument"], "reason": move["reason"], "promise": move["promise"],
                    "from": move["from"], "depth": move["depth"],
                    "relevance": judged["relevance"], "findings": len(kept), "stop_branch": judged["stop_branch"], "note": judged["note"],
                    "answer_summary": {k: v for k, v in answer.items() if k in ("statements", "families", "offices", "forecast_rows_total", "topics", "error")}})
        if not judged["stop_branch"]:
            frontier += [{**nxt, "argument": nxt["argument"].strip(), "depth": move["depth"] + 1, "path": path, "from": len(log)}
                         for nxt in reversed(judged["next"][:MAX_NEXT]) if nxt["argument"].strip()]  # reversed: among equals the first named goes first
    lay = layer.orgs
    opened = [{"office": office_name(o, lay), "name": lay[o]["name"], "type": lay[o].get("org_type", ""),
               "above": [office_name(x, lay) for x in walk.ancestors(o)[1:]]} for o in sorted(walk.opened, key=lambda o: office_name(o, lay))]
    dossier = (f"{who}\nRelevant when: {seed['relevant_when']}\nOffices opened: {compact(opened, 4000)}\n"
               f"Findings: {compact([{k: f[k] for k in ('identifier', 'quote', 'why')} | {'brief': walk.shown[f['identifier']]} for f in findings], 14000)}\n"
               f"People shown: {compact(list(walk.people.values()), 5000)}\n"
               f"Routes shown: {compact([{k: r[k] for k in ('side', 'recommendation', 'office_id', 'observed_at')} for r in walk.routes.values()], 5000)}\n"
               f"Walk notes: {compact([s['note'] for s in log], 4000)}")
    picked, picked_problems = checked(SYSTEM_CHAIN, dossier, SCHEMA_CHAIN, "outreach_chain", lambda a: chain_problems(walk, a))
    letter, letter_problems, proof = None, [], ""
    if picked["fit"] and not picked_problems:
        proof = evidence(walk, picked)
        why = compact({k: picked[k] for k in ("why_office", "requirements", "initiatives", "people", "routes")}, 6000)
        letter, letter_problems = checked(SYSTEM_EMAIL, f"{who}\nEvidence:\n{proof}\nThe chain and why: {why}", SCHEMA_EMAIL, "outreach_email",
                                          lambda e: email_problems(walk, picked, e, proof, f"{company} {profile}"))
    status = "refused" if picked_problems or letter_problems else "written" if letter else "no fit"
    return {"company": company, "profile": profile, "as_of": layer.as_of, "model": model, "budget": steps, "seed": seed, "steps": log,
            "findings": findings, "findings_dropped": dropped, "chain": picked, "chain_problems": picked_problems, "evidence": proof,
            "email": letter, "email_problems": letter_problems, "status": status,
            "contacts": [walk.people[p["name"]] for p in picked["people"] if p["name"] in walk.people], "calls": calls,
            "usage": {k: sum((c["usage"] or {}).get(k) or 0 for c in calls) for k in ("input_tokens", "output_tokens")}}


def settled(result: dict) -> dict:
    """A run without how each call was had: a replay of a live run holds when everything else is the same."""
    return {**result, "calls": [{k: v for k, v in c.items() if k != "replayed"} for c in result["calls"]]}


def readout(result: dict) -> str:
    a = result["chain"]
    lines = [f"{result['company']}: outreach, record as of {result['as_of']}; {result['status']}",
             f"Searched for: {', '.join(t['term'] for t in result['seed']['terms'])}", ""]
    for s in result["steps"]:
        came = f"from {s['from']}, " if s["from"] else ""
        lines.append(f"{s['n']:>2}. {s['tool']} {s['argument']}  ({came}promise {s['promise']}, relevance {s['relevance']}, findings {s['findings']})")
    if not a["fit"]:
        lines += ["", f"No chain: {a['no_fit']}"]
    else:
        lines += ["", "Chain: " + " > ".join(x for x in (a["agency"], a["command"], a["peo"], a["program_office"]) if x.strip()), f"  {a['why_office']}"]
        for kind in ("requirements", "initiatives"):
            lines += [f"{kind.title()}:"] + [f"- {r['identifier']}: \"{r['quote']}\"; {r['why']}" for r in a[kind]]
        lines += ["Write to:"] + [f"- {c['name']}, {c['title']}, {c['office']} ({c['email'] or 'no e-mail on record'}; observed {c['observed_at']}, {c['source']})"
                                  for c in result["contacts"]]
        lines += [f"- route: {r['route']}" for r in a["routes"]]
    for label, found in (("Chain refused", result["chain_problems"]), ("Letter refused", result["email_problems"])):
        lines += [f"{label}: " + "; ".join(found)] if found else []
    if result["email"]:
        e = result["email"]
        lines += ["", f"To: {e['to']}", f"Subject: {e['subject']}", "", e["body"], "", f"Cites: {', '.join(e['cites'])}"]
    lines += ["", f"{len(result['steps'])} step(s), {len(result['calls'])} model call(s), {sum(c['replayed'] for c in result['calls'])} replayed; "
              f"{result['findings_dropped']} finding(s) dropped as unshown or misquoted."]
    return "\n".join(lines)


def slug(company: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")


def run(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="outreach.py run")
    ap.add_argument("--company", required=True)
    ap.add_argument("--profile", required=True, help="what the company sells, in its own words, or a file holding it")
    ap.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    ap.add_argument("--check", action="store_true", help="replay from cassettes only and compare with the saved run")
    args = ap.parse_args(argv)
    profile = Path(args.profile).read_text(encoding="utf-8").strip() if Path(args.profile).is_file() else args.profile
    layer = Layer(json.loads(CORPUS.read_text(encoding="utf-8")), load_people())
    result = outreach(layer, args.company, profile, args.steps, replay_only=args.check)
    text = json.dumps(result, indent=1, ensure_ascii=False) + "\n"
    out = OUT / f"{slug(args.company)}.json"
    print(readout(result))
    if args.check:
        same = out.exists() and settled(json.loads(out.read_text(encoding="utf-8"))) == settled(result)
        print("outreach matches the saved run" if same else "outreach differs from the saved run", file=sys.stderr)
        return 0 if same else 1
    OUT.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return 0


def show(argv: list[str]) -> int:
    print(readout(json.loads((OUT / f"{argv[0]}.json").read_text(encoding="utf-8"))))
    return 0


def fixture() -> Walk:
    """The department over a command, a PEO and a program office, a sibling office under another PEO, a contracting
    office; a forecast row, a topic, a directive at the department, a priority under the sibling; one program manager."""
    orgs = {"don": {"acronym": "", "name": "Department of the Navy", "parent": "", "org_type": "agency"},
            "cmd": {"acronym": "", "name": "NAVWAR", "parent": "don", "org_type": "contracting_activity"},
            "peo": {"acronym": "", "name": "PEO C4I", "parent": "cmd", "org_type": "program_executive_office"},
            "pmw": {"acronym": "PMA/PMW 101", "name": "MIDS", "parent": "peo", "org_type": "program_office"},
            "peo2": {"acronym": "", "name": "PEO Digital", "parent": "cmd", "org_type": "program_executive_office"},
            "far": {"acronym": "PMW 205", "name": "Naval Enterprise Networks", "parent": "peo2", "org_type": "program_office"},
            "ko": {"acronym": "N00039", "name": "NAVWAR contracts", "parent": "cmd", "org_type": "contracting_office"}}
    ev = lambda i, fam, typ, day, org, text: {"id": i, "event_type": typ, "date": day, "available_by": day, "provider": fam, "family": fam,
                                                "org": org, "title": text, "text": text, "slip": False, "stage": "", "polarity": ""}
    events = [ev("t1", "programs", "sbir_topic", "2025-04-02", "pmw", "N252-D11 Advanced Interference Mitigation for MIDS tactical data links"),
              ev("c1", "congress", "congressional_directive", "2025-07-01", "don", "The committee directs a briefing on Link 16 terminal production capacity"),
              ev("l1", "leaders", "capability_priority", "2025-08-01", "far", "Enterprise network modernization is the first priority"),
              ev("n1", "notice", "presolicitation_posted", "2026-08-12", "ko", "SAM.gov presolicitation 2026-08-12: MIDS WDL SF3 Radio")]
    needs = [{"key": "N00039-25-RFPREQ-PMA/PMW-101-0046", "title": "MIDS WDL SF3 Radio (C)", "owner": "PMA/PMW 101", "owner_id": "pmw"}]
    roster = [{"name": "Ann Example", "emails": ["ann.example@us.navy.mil"],
               "positions": [{"office": "pmw:101", "org": "pmw", "role_type": "program_manager", "raw_title": "Program Manager", "observed_at": "2026-08-01",
                              "source": "sam", "source_ref": "x", "source_url": "", "confidence": "0.9", "context": "MIDS"}]},
              {"name": "Bob Elsewhere", "emails": [], "positions": [{"office": "pmw:205", "org": "far", "role_type": "program_manager", "raw_title": "Program Manager",
                                                                     "observed_at": "2026-08-01", "source": "sam", "source_ref": "y", "source_url": "",
                                                                     "confidence": "0.9", "context": ""}]}]
    return Walk(Layer({"orgs": orgs, "events": events, "needs": needs, "outcomes": []}, roster, as_of="2026-09-01", routes=[]))


def selfcheck() -> int:
    walk = fixture()
    ini = walk.call("initiatives", "PMA/PMW 101")
    assert [e["id"] for e in ini["newest"]] == [] and ini["department_wide"] == 1, "the department's directive is counted, the sibling's priority is not shown"
    assert walk.call("search", "Link 16 terminal maker")["note"].startswith("no record carries") and "note" not in walk.call("search", "Link 16")
    walk.call("office", "PMA/PMW 101")
    assert "c1" in walk.shown and "N00039-25-RFPREQ-PMA/PMW-101-0046" in walk.shown and "t1" in walk.shown and "Ann Example" in walk.people
    assert walk.opened == {"pmw"} and walk.ancestors("pmw") == ["pmw", "peo", "cmd", "don"]
    good = {"fit": True, "agency": "Department of the Navy", "command": "NAVWAR", "peo": "PEO C4I", "program_office": "PMA/PMW 101", "why_office": "It owns MIDS.",
            "requirements": [{"identifier": "N00039-25-RFPREQ-PMA/PMW-101-0046", "quote": "MIDS WDL SF3 Radio", "why": "a terminal"}],
            "initiatives": [{"identifier": "c1", "quote": "Link 16 terminal production capacity", "why": "Congress asks about capacity."}],
            "people": [{"name": "Ann Example", "why": "She manages the program."}], "routes": [], "no_fit": ""}
    assert chain_problems(walk, good) == [], chain_problems(walk, good)
    bad = [({"peo": ""}, "sits under PEO C4I; name it as the peo"), ({"command": "PEO Digital"}, "is not above PMA/PMW 101 in the record; the record puts it under NAVWAR"),
           ({"program_office": "PMW 205"}, "was not opened"), ({"program_office": "N00039"}, "not a buying office"),
           ({"command": "PEO C4I", "peo": "NAVWAR"}, "'NAVWAR' is a contracting_activity, not a peo; the record puts it under PEO C4I"),
           ({"initiatives": [{"identifier": "N00039-25-RFPREQ-PMA/PMW-101-0046", "quote": "MIDS WDL SF3 Radio", "why": ""}]}, "both as a requirement and as an initiative"), ({"agency": ""}, "name it as the agency"),
           ({"requirements": [{"identifier": "made-up", "quote": "x", "why": ""}]}, "made-up was not shown"),
           ({"requirements": [{"identifier": "t1", "quote": "MIDS radio", "why": ""}]}, "not in the record verbatim"),
           ({"initiatives": [{"identifier": "l1", "quote": "network modernization", "why": ""}]}, "sits outside the chain"),
           ({"initiatives": [{"identifier": "n1", "quote": "MIDS WDL SF3 Radio", "why": ""}]}, "is a notice record, not what leaders"),
           ({"people": [{"name": "Bob Elsewhere", "why": ""}]}, "was not shown for this chain (shown for it: Ann Example)"), ({"people": []}, "no one to write to"),
           ({"why_office": "An RFP is likely soon."}, "banned phrase")]
    walk.shown["l1"] = walk.layer.brief(walk.events["l1"])
    for change, problem in bad:
        found = chain_problems(walk, {**good, **change})
        assert any(problem in p for p in found), (change, found)
    assert chain_problems(walk, {**good, "fit": False, "no_fit": "The record holds no aerosol buyer."}) == []
    proof = evidence(walk, good)
    assert "Chain: Department of the Navy (Department of the Navy) > NAVWAR (NAVWAR) > PEO C4I (PEO C4I) > PMA/PMW 101 (MIDS)" in proof \
        and "ann.example@us.navy.mil" in proof, proof
    mail = {"to": "Ann Example", "subject": "MIDS WDL SF3 Radio (N00039-25-RFPREQ-PMA/PMW-101-0046)", "cites": ["N00039-25-RFPREQ-PMA/PMW-101-0046", "c1"],
            "body": "Ms. Example, our terminals fit the MIDS WDL SF3 Radio row, and the committee directs a briefing on Link 16 terminal production capacity."}
    assert email_problems(walk, good, mail, proof, "Acme builds Link 16 terminals") == [], email_problems(walk, good, mail, proof, "")
    for change, problem in [({"to": "Bob Elsewhere"}, "not a chosen person"), ({"cites": ["c1"]}, "cites no requirement"), ({"cites": ["x", "[N00039-25-RFPREQ-PMA/PMW-101-0046]"]}, "cites x"),
                            ({"body": "Contract N00039-26-C-0099 ends in FY2027."}, "'N00039-26-C-0099' is in no evidence"),
                            ({"body": "Bob Elsewhere suggested we write."}, "names Bob Elsewhere"), ({"body": "A short call — this week."}, "em dash"),
                            ({"body": "The RFP is imminent."}, "banned phrase"),
                            ({"body": "Requirement dd1980e1-8723-5748-9ff1-829aabbc0548 fits."}, "names the internal key dd1980e1")]:
        found = email_problems(walk, good, {**mail, **change}, proof, "Acme builds Link 16 terminals")
        assert any(problem in p for p in found), (change, found)
    moves = [{"argument": "a", "promise": 0.5}, {"argument": "b", "promise": 0.9}, {"argument": "c", "promise": 0.9}]
    assert [next_move(moves)["argument"] for _ in range(3)] == ["c", "b", "a"]
    assert slug("Acme Link, Inc.") == "acme-link-inc"
    print("outreach selfcheck ok")
    return 0


COMMANDS = {"run": run, "show": show}

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--selfcheck":
        sys.exit(selfcheck())
    if not args or args[0] not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    sys.exit(COMMANDS[args[0]](args[1:]))
