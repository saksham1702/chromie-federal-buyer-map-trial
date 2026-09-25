#!/usr/bin/env python3
"""People layer: every person a saved source names beside an office, as a dated observation,
merged into one person per identity, so an action can say whom the public record ties to an office.

Sources, all already on disk:
  - SAM.gov notice points of contact (data/raw/sam_notices/<id>.json): name, e-mail, primary or secondary. Their
    office is the one the notice text names (one, specific) else the contracting office the notice was posted under.
  - contact_observations.json: the LRAE forecast POC columns and release passages a reviewer read (program managers,
    executives), each with the office it was resolved to and the date it was observed.
  - remarks_events.json: the speaker of each speech, statement and conference page and the witnesses of each hearing,
    with the role as the text writes it; the Department when the text names no office.
  - news_observations.json: whoever an article states relieved whom as program manager, or was named to lead an
    office, dated by the article and placed by the office its own clause names.
  - organization_seed.json person nodes, so a person the memory already knows keeps the memory's contact id.

Merge rule: one person per e-mail, and one person for two e-mails under one name at a shared office; without an e-mail, one person per normalised name and office (ranks and
honorifics dropped, "Last, First" turned around, middle initials dropped). Two people who share a name, have no
e-mail and sit in different offices stay two people. Nobody is invented: every position points at the document.

  python research/tools/people.py build          # writes research/memory/people.json
  python research/tools/people.py show pmw:101   # whom the sources tie to an office, newest first, and the routes in

Routes come from contact_recommendations.json: per office, the requirement side (the program manager), the
acquisition side (the contracting points of contact on its forecast rows), the published channels (an office
mailbox, the small business office, an intake portal) and the portfolio executive, each resting on the
observations it names and dated by the newest of them. The small business offices small_business.py reads from the
Department of War's directory join them, and an office with none of its own, or above it, falls back to the department's.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agency_layers_sql import POSITION_ROLES, role_type, uid  # noqa: E402

PEOPLE = ROOT / "research" / "memory" / "people.json"
OBSERVATIONS = ROOT / "research" / "memory" / "contact_observations.json"
RECOMMENDATIONS = ROOT / "research" / "memory" / "contact_recommendations.json"
REVIEWS = ROOT / "research" / "memory" / "review_log.json"
REMARKS = ROOT / "research" / "events" / "remarks_events.json"
NEWS = ROOT / "research" / "events" / "news_observations.json"
SEED = ROOT / "research" / "memory" / "organization_seed.json"
SMALL_BUSINESS = ROOT / "research" / "memory" / "small_business_offices.json"
SOURCE = "chromie-federal-buyer-map-trial/research/memory/people.json"
DEPARTMENT = "agency:don"

HONORIFICS = {"mr", "mrs", "ms", "dr", "hon", "the", "honorable", "capt", "cdr", "lcdr", "lt", "ltjg", "ens", "adm", "vadm",
              "radm", "rdml", "gen", "ltgen", "maj", "col", "ltcol", "sgt", "phd", "ph", "d", "jr", "sr", "ii", "iii", "iv",
              "ret", "usn", "usmc", "sc", "esq"}
EXECUTIVE = ("secretary of the navy", "assistant secretary", "chief of naval operations", "commandant", "vice chief",
             "under secretary", "deputy secretary", "executive officer", "commander,", "commander of", "director",
             "portfolio acquisition executive")
# A SAM.gov point of contact is the contracting shop's named contact; the schema has no finer word for it.
POC_ROLE = "contract_specialist"
# The read text gets a lower confidence than a structured field: the model named the person, a lint checked the span.
CONFIDENCE = {"sam_gov_site_api": "0.90", "contact_observations": "0.90", "organization_seed": "0.90",
              "navy_mil_speeches": "0.70", "house_committee_repository": "0.70", "conference_pages_exa": "0.60", "news_articles": "0.80"}
REMARKS_PROVIDER = {"speech": "navy_mil_speeches", "statement": "navy_mil_speeches", "testimony": "house_committee_repository",
                    "conference": "conference_pages_exa"}


TITLE_WORDS = {"contract", "contracting", "contracts", "specialist", "officer", "manager", "director", "deputy", "assistant", "chief",
               "head", "lead", "buyer", "analyst", "engineer", "program", "procurement", "purchasing", "agent", "representative",
               "coordinator", "administrator", "branch", "division", "code", "pco", "aco", "cor", "ph", "phd", "jr", "sr", "ii", "iii",
               "usn", "usmc", "ret", "ses"}  # words that make what follows a comma a title or suffix, not a given name


def person_name(name: str) -> str:
    """The name without what a form appends to it: 'Kerry Payne (Contract Specialist)' and 'Frederick Mitchell, Contract
    Specialist' give the name; 'Marsh, Stephanie L.' stays, since one word before the comma is a surname; a two-word
    surname written first ('ST DENIS, DANIEL') is turned around, since no title follows its comma."""
    name = " ".join(re.sub(r"\(.*?\)", " ", name or "").split())
    head, comma, tail = name.partition(",")
    if not comma or len(head.split()) < 2:
        return name
    return head.strip() if not tail.strip() or set(re.findall(r"[a-z]+", tail.lower())) & TITLE_WORDS else f"{tail.strip()} {head.strip()}"


def norm_name(name: str) -> str:
    """'CAPT Raphael R. Castillejo' and 'Castillejo, Raphael' both give 'raphael castillejo'."""
    name = person_name(name)
    if "," in name:
        last, _, first = name.partition(",")
        name = f"{first} {last}"
    tokens = [t for t in re.split(r"[^a-z]+", name.lower()) if t and t not in HONORIFICS and len(t) > 1]
    return " ".join(tokens)


def role_of(raw: str) -> str:
    """The schema's position vocabulary; a department executive is an acquisition leader there."""
    text = (raw or "").lower()
    if any(k in text for k in EXECUTIVE) and role_type(raw) == "other":
        return "acquisition_leader"
    return role_type(raw)


def position(office: str, role: str, raw_title: str, observed_at: str, source: str, ref: str, url: str, context: str = "") -> dict:
    assert role in POSITION_ROLES, role
    return {"office": office, "org": uid("org", office), "role_type": role, "raw_title": (raw_title or "")[:200], "observed_at": observed_at[:10],
            "source": source, "source_ref": ref, "source_url": url, "confidence": CONFIDENCE.get(source, "0.60"), "context": context[:160]}


# ------------------------------------------------------------------ sources

def observed_role(row: dict) -> str:
    """The forecast sheets name a contracting or secondary point of contact; otherwise read the title."""
    role = row.get("role_type") or ""
    if role.endswith("_poc"):
        return POC_ROLE
    return role if role in POSITION_ROLES else role_of(row.get("role_as_written"))


def sam_contacts() -> list[tuple[str, str, dict]]:
    """(name, email, position) per point of contact on every saved notice detail."""
    from trace import NOTICES, SAM_ORG_NODES, SAM_VIEW, match_context, notice_detail, resolve_offices, specific_offices  # noqa: E402
    parents = match_context()["parents"]
    out = []
    for path in sorted(NOTICES.glob("*.json")) if NOTICES.exists() else []:
        if path.name.endswith(".resources.json") or path.name.startswith(("._", "search_")):
            continue
        d = notice_detail(path.stem)
        if not d or not d["posted"]:
            continue
        raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        pocs = (raw.get("data2") or raw.get("data") or {}).get("pointOfContact") or []
        named = specific_offices(resolve_offices(d["text"]), parents)
        office = named[0] if len(named) == 1 else SAM_ORG_NODES.get(d["organization_id"])
        if not office:
            continue
        for poc in pocs:
            title = f"{poc.get('type') or 'point of'} point of contact on {d['type']} {d['solicitation'] or d['id']}"
            for name, email in split_pocs((poc.get("fullName") or "").strip(), (poc.get("email") or "").strip().lower()):
                if norm_name(name):
                    out.append((name, email, position(office, POC_ROLE, title, d["posted"], "sam_gov_site_api", d["id"],
                                                      SAM_VIEW.format(d["id"]), d["title"])))
    return out


LEGACY_POC = re.compile(r"^Point of Contact\s*-\s*", re.I)


def split_pocs(full: str, email: str) -> list[tuple[str, str]]:
    """A notice carried over from the old system writes every contact in one field, 'Point of Contact - Name, Title,
    phone; Name, Title, phone', then a mailto link. One (name, e-mail) per contact; an address goes to the contact
    whose surname it carries."""
    if not LEGACY_POC.match(full):
        return [(full, email)]
    mails = [m.lower() for m in re.findall(r"mailto:([^\"'>\s]+)", full)] + ([email] if email else [])
    out = []
    for part in LEGACY_POC.sub("", full).split("\n", 1)[0].split(";"):
        name = part.split(",", 1)[0].strip()
        surname = (norm_name(name).split() or [""])[-1]
        out.append((name, next((m for m in mails if surname and surname in m.split("@")[0]), "")))
    return out


def observed_contacts() -> list[tuple[str, str, dict]]:
    if not OBSERVATIONS.exists():
        return []
    out = []
    for row in json.loads(OBSERVATIONS.read_text(encoding="utf-8")):
        if row.get("kind") != "person" or not row.get("office_id_as_resolved") or not row.get("observed_at"):
            continue
        channel = (row.get("channel_as_written") or "").strip().lower()
        out.append((row["name"], channel if "@" in channel else "",
                    position(row["office_id_as_resolved"], observed_role(row), row.get("role_as_written") or "",
                             row["observed_at"], "contact_observations", row["id"], row.get("source_url") or "", row.get("passage") or "")))
    return out


def remarks_people() -> list[tuple[str, str, dict]]:
    """The speaker of each document and the witnesses of each hearing; office from the events when one office recurs."""
    if not REMARKS.exists():
        return []
    from trace import resolve_offices  # noqa: E402
    out = []
    for doc in json.loads(REMARKS.read_text(encoding="utf-8"))["documents"]:
        if not doc.get("issued"):
            continue
        source = REMARKS_PROVIDER.get(doc["kind"], "navy_mil_speeches")
        orgs = Counter(o for e in doc.get("events") or [] for o in (e.get("organizations") or []) if o != DEPARTMENT)
        office = orgs.most_common(1)[0][0] if len(orgs) == 1 else DEPARTMENT
        people = []
        if doc.get("speaker_name"):
            people.append((doc["speaker_name"], doc.get("speaker_role") or "", f"spoke: {doc['title']}"))
        for w in doc.get("witnesses") or []:
            if isinstance(w, dict) and w.get("name"):
                people.append((w["name"], w.get("position") or "", f"witness: {doc['title']}"))
        for name, role, context in people:
            if not norm_name(name):
                continue
            named = [o["office"] for o in resolve_offices(role) if not o["former"]]
            where = named[0] if len(named) == 1 else office
            out.append((name, "", position(where, role_of(role), role, doc["issued"], source, doc["url"], doc["url"], context)))
    return out


def news_people() -> list[tuple[str, str, dict]]:
    """Whoever an article states took charge of an office, dated by the article; a change no office places stays in the article."""
    if not NEWS.exists():
        return []
    out = []
    for article in json.loads(NEWS.read_text(encoding="utf-8"))["articles"]:
        for change in article.get("leadership") or []:
            if article.get("published") and change["office"]:
                out.append((change["name"], "", position(change["office"], role_of(change["role_as_written"]), change["role_as_written"],
                                                          article["published"], "news_articles", article["id"], article["url"], change["passage"])))
    return out


def unplaced_changes() -> list[dict]:
    """The changes of charge the articles state for an office the memory does not know, so the gap is a row and not a silence."""
    if not NEWS.exists():
        return []
    return [{"name": c["name"], "role_as_written": c["role_as_written"], "published": a.get("published", ""), "url": a["url"], "passage": c["passage"]}
            for a in json.loads(NEWS.read_text(encoding="utf-8"))["articles"] for c in a.get("leadership") or [] if not c["office"]]


def seed_people() -> dict[str, dict]:
    """Normalised name -> {seed id, name, offices} for the persons the organization memory already holds."""
    if not SEED.exists():
        return {}
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    people = {n["id"]: n for n in seed["nodes"] if n["type"] == "person"}
    offices: dict[str, set] = {}
    for rel in seed["relationships"]:
        if rel["type"] == "leads" and rel["from"] in people:
            offices.setdefault(rel["from"], set()).add(rel["to"])
    return {norm_name(n["name"]): {"seed_id": nid, "name": n["name"], "offices": sorted(offices.get(nid, ()))} for nid, n in people.items()}


# ------------------------------------------------------------------ merge

def merge(rows: list[tuple[str, str, dict]], seed: dict[str, dict] | None = None) -> list[dict]:
    seed = seed or {}
    by_key: dict[str, dict] = {}
    for name, email, pos in rows:
        normal = norm_name(name)
        known = seed.get(normal)
        if known and (not known["offices"] or pos["office"] in known["offices"] or pos["office"] == DEPARTMENT):
            key = f"seed:{known['seed_id']}"
        elif email:
            key = f"email:{email}"
        else:
            key = f"name:{normal}:{pos['office']}"
        person = by_key.setdefault(key, {"key": key, "id": uid("person", key), "seed_id": known["seed_id"] if key.startswith("seed:") else None,
                                         "names": Counter(), "emails": set(), "positions": []})
        person["names"][name.strip()] += 1
        if email:
            person["emails"].add(email)
        person["positions"].append(pos)
    # One person under two e-mails when the name is the same and an office is shared: the move from navy.mil to
    # us.navy.mil gave staff a second address. Name-only rows stay apart by office as the rule says.
    clusters: dict[str, list[dict]] = {}
    for key in sorted(by_key):
        person = by_key[key]
        if not key.startswith("email:"):
            continue
        offices = {p["office"] for p in person["positions"]}
        group = clusters.setdefault(norm_name(person["names"].most_common(1)[0][0]), [])
        into = [c for c in group if c["offices"] & offices]
        if not into:
            group.append({"person": person, "offices": offices})
            continue
        keep = into[0]
        for other in [person] + [c["person"] for c in into[1:]]:
            keep["person"]["names"].update(other["names"])
            keep["person"]["emails"] |= other["emails"]
            keep["person"]["positions"] += other["positions"]
            keep["offices"] |= {p["office"] for p in other["positions"]}
            del by_key[other["key"]]
        group[:] = [c for c in group if c not in into[1:]]
    out = []
    for person in by_key.values():
        positions = sorted(person["positions"], key=lambda p: (p["observed_at"], p["source_ref"]), reverse=True)
        seen, unique = set(), []
        for p in positions:
            k = (p["office"], p["role_type"], p["source"], p["source_ref"])
            if k not in seen:
                seen.add(k)
                unique.append(p)
        out.append({"id": person["id"], "key": person["key"], "seed_id": person["seed_id"],
                    "name": person_name(max(person["names"], key=lambda n: ("," not in person_name(n), person["names"][n], len(n)))),
                    "emails": sorted(person["emails"]), "positions": unique,
                    "offices": sorted({p["office"] for p in unique}), "last_seen": unique[0]["observed_at"]})
    return sorted(out, key=lambda p: (p["last_seen"], p["name"]), reverse=True)


def build(argv: list[str]) -> int:
    rows = sam_contacts() + observed_contacts() + remarks_people() + news_people()
    people = merge(rows, seed_people())
    payload = {"source": SOURCE, "observations": len(rows), "people": len(people),
               "by_source": dict(Counter(p["source"] for r in rows for p in [r[2]]).most_common()),
               "by_role": dict(Counter(p["role_type"] for person in people for p in person["positions"]).most_common()),
               "unplaced_changes": unplaced_changes(), "rows": people}
    PEOPLE.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(rows)} observation(s) -> {len(people)} people; by source {payload['by_source']}; by role {payload['by_role']}; "
          f"{len(payload['unplaced_changes'])} change(s) of charge name an office the memory does not know")
    return 0


def contacts_for(org_ids: list[str], people: list[dict], as_of: str | None = None, limit: int = 3) -> list[dict]:
    """Whom the record ties to any of these organization ids (most specific first, then newest), observed by as_of."""
    rank = {org: i for i, org in enumerate(org_ids)}
    rows = []
    for person in people:
        fits = [(rank[p["org"]], -int(p["observed_at"].replace("-", "")), p) for p in person["positions"]
                if p["org"] in rank and (not as_of or p["observed_at"] <= as_of)]
        if fits:
            best = min(fits, key=lambda r: r[:2])
            rows.append((best[0], best[1], person, best[2]))
    rows.sort(key=lambda r: (r[0], r[1], r[2]["name"]))
    return [{"name": person["name"], "role": p["role_type"], "title": p["raw_title"], "office": p["office"], "observed_at": p["observed_at"],
             "source": p["source"], "source_ref": p["source_ref"], "source_url": p["source_url"], "email": (person["emails"] or [""])[0]}
            for _, _, person, p in rows[:limit]]


SMALL_BUSINESS_ROUTE = "small_business_office"
ROUTE_ORDER = ("program_manager", "contracting_poc", "office_channel", SMALL_BUSINESS_ROUTE, "industry_intake_channel", "executive")
SIDE = {"program_manager": "requirement", "contracting_poc": "acquisition", "office_channel": "channel",
        SMALL_BUSINESS_ROUTE: "small business office", "industry_intake_channel": "channel", "executive": "executive"}


def load_routes() -> list[dict]:
    """Every recommended route with the date and the source of the observations it rests on, and whether each of
    those observations was checked against the saved file it cites."""
    if not RECOMMENDATIONS.exists() or not OBSERVATIONS.exists():
        return []
    observed = {o["id"]: o for o in json.loads(OBSERVATIONS.read_text(encoding="utf-8"))}
    reviews = json.loads(REVIEWS.read_text(encoding="utf-8")) if REVIEWS.exists() else []
    checked = {r["target"] for r in reviews if r["outcome"] in ("confirmed", "corrected")}
    rows = []
    for rec in json.loads(RECOMMENDATIONS.read_text(encoding="utf-8")):
        basis = [observed[i] for i in rec["contact_observation_ids"] if i in observed]
        if not basis:
            continue
        newest = max(basis, key=lambda o: o["observed_at"])
        rows.append({"org": uid("org", rec["office_id"]), "office_id": rec["office_id"], "route": rec["route_type"],
                     "side": SIDE.get(rec["route_type"], "other"), "recommendation": rec["recommendation"],
                     "confidence": rec["source_confidence"], "currency": rec["currency_confidence"],
                     "review_status": rec["review_status"], "observed_at": newest["observed_at"], "source_url": newest["source_url"],
                     "checked": all(o["id"] in checked for o in basis)})
    for sb in json.loads(SMALL_BUSINESS.read_text(encoding="utf-8")) if SMALL_BUSINESS.exists() else []:
        rows.append({"org": uid("org", sb["office_id"]), "office_id": sb["office_id"], "route": SMALL_BUSINESS_ROUTE,
                     "side": SIDE[SMALL_BUSINESS_ROUTE], "recommendation": "; ".join([f"{sb['name']}, {sb['url']}", *sb["lines"]]),
                     "confidence": "high", "currency": "unknown", "review_status": "draft", "observed_at": sb["observed_at"],
                     "source_url": sb["url"] if sb["page_saved"] else sb["source_url"], "checked": False})
    return rows


def routes_for(org_ids: list[str], routes: list[dict], as_of: str | None = None) -> list[dict]:
    """The routes into the most specific of these organizations that has any, observed by as_of: the program
    manager and the contracting side of the office itself before its parent's channels."""
    rank = {org: i for i, org in enumerate(org_ids)}
    fits = [r for r in routes if r["org"] in rank and (not as_of or r["observed_at"] <= as_of)]
    if not any(r["route"] == SMALL_BUSINESS_ROUTE for r in fits):  # any office can start at the department's small business office
        fits += [r for r in routes if r["office_id"] == DEPARTMENT and r["route"] == SMALL_BUSINESS_ROUTE and (not as_of or r["observed_at"] <= as_of)]
    order = {route: i for i, route in enumerate(ROUTE_ORDER)}
    fits.sort(key=lambda r: (rank.get(r["org"], len(rank)), order.get(r["route"], len(order)), r["recommendation"]))
    return [{k: v for k, v in r.items() if k != "org"} for r in fits]


def first_routes(routes: list[dict], n: int) -> list[dict]:
    """The first n routes, and the small business office after them when it is not among them: a small company's first
    contact at a command."""
    return routes[:n] + [r for r in routes[n:] if r["route"] == SMALL_BUSINESS_ROUTE][:1]


def show(argv: list[str]) -> int:
    office = argv[0] if argv else "pmw:101"
    people = json.loads(PEOPLE.read_text(encoding="utf-8"))["rows"]
    for c in contacts_for([uid("org", office)], people, limit=20):
        print(f"{c['observed_at']}  {c['name']:32} {c['role']:20} {c['source']:26} {c['source_ref'][:40]}")
    for r in routes_for([uid("org", office)], load_routes()):
        print(f"{r['observed_at']}  {r['side']:12} {r['route']:24} {r['recommendation'][:90]}")
    return 0


def selfcheck() -> int:
    assert norm_name("CAPT Raphael R. Castillejo") == norm_name("Castillejo, Raphael") == "raphael castillejo"
    assert norm_name("The Honorable Hung Cao") == "hung cao" and norm_name("Mr. Eric Andalis") == "eric andalis"
    assert norm_name("Ashley, Megan") == "megan ashley" and norm_name("") == "" and norm_name("A.") == ""
    assert norm_name("Frederick Mitchell, Contract Specialist") == norm_name("Frederick Mitchell") == "frederick mitchell"
    assert person_name("Kerry Payne (Contract Specialist)") == "Kerry Payne" and person_name("Marsh, Stephanie L.") == "Marsh, Stephanie L."
    assert norm_name("ST DENIS, DANIEL") == norm_name("Daniel St. Denis") == "daniel st denis" and person_name("De Vera, Jennifer") == "Jennifer De Vera"
    assert person_name("William H. Luebke, Ph.D.") == "William H. Luebke", "a suffix after the comma is no given name"
    assert role_of("Chief of Naval Operations") == "acquisition_leader" and role_of("Program Manager, PMW 150") == "program_manager"
    assert role_of("Deputy Program Manager") == "deputy_program_manager" and role_of("liaison") == "other"
    assert role_of("portfolio acquisition executive") == "acquisition_leader"
    assert role_of("Contract Specialist") == "contract_specialist" and role_of("") == "other"
    pos = lambda office, ref, day="2026-01-01", src="sam_gov_site_api": position(office, POC_ROLE, "poc", day, src, ref, "u")  # noqa: E731
    people = merge([("Megan Ashley", "megan@navy.mil", pos("pmw:101", "n1")), ("Ashley, Megan", "megan@navy.mil", pos("peo:c4i", "n2", "2026-02-01")),
                    ("Jim Day", "", pos("pmw:120", "n3")), ("Jim Day", "", pos("pmw:130", "n4")),
                    ("Mr. Eric Andalis", "", pos("pmw:760", "r1", "2025-08-19", "contact_observations"))],
                   {"eric andalis": {"seed_id": "person:andalis", "name": "Eric Andalis", "offices": ["pmw:760"]}})
    by = {p["name"]: p for p in people}
    assert len(people) == 4, [p["key"] for p in people]                       # e-mail merges two spellings; two Jim Days stay apart
    assert by["Megan Ashley"]["offices"] == ["peo:c4i", "pmw:101"] and by["Megan Ashley"]["last_seen"] == "2026-02-01"
    assert sum(p["name"] == "Jim Day" for p in people) == 2
    assert by["Mr. Eric Andalis"]["seed_id"] == "person:andalis" and by["Mr. Eric Andalis"]["id"] == uid("person", "seed:person:andalis")
    moved = merge([("Kimberly Ellis", "kimberly.ellis3@navy.mil", pos("pmw:740", "a")), ("Kimberly Ellis", "kimberly.a.ellis10.civ@us.navy.mil", pos("pmw:740", "b")),
                   ("Kimberly Ellis", "kimberly.ellis@nrl.navy.mil", pos("center:nrl", "c"))])
    assert len(moved) == 2 and moved[0]["emails"] == ["kimberly.a.ellis10.civ@us.navy.mil", "kimberly.ellis3@navy.mil"], moved  # one office: one person
    got = contacts_for([uid("org", "pmw:101"), uid("org", "peo:c4i")], people)
    assert [c["name"] for c in got] == ["Megan Ashley"] and got[0]["office"] == "pmw:101" and got[0]["email"] == "megan@navy.mil"
    assert contacts_for([uid("org", "pmw:101")], people, as_of="2025-12-31") == []
    route = lambda office, kind, day: {"org": uid("org", office), "office_id": office, "route": kind, "side": SIDE[kind],
                                       "recommendation": kind, "confidence": "high", "currency": "high", "review_status": "draft",
                                       "observed_at": day, "source_url": "u"}
    routes = [route("command:navwar", "industry_intake_channel", "2026-09-16"), route("pmw:160", "contracting_poc", "2025-06-01"),
              route("pmw:160", "program_manager", "2025-01-01"), route("pmw:170", "program_manager", "2025-01-01")]
    chain_ = [uid("org", "pmw:160"), uid("org", "peo:c4i"), uid("org", "command:navwar")]
    assert [r["route"] for r in routes_for(chain_, routes)] == ["program_manager", "contracting_poc", "industry_intake_channel"]
    assert [r["route"] for r in routes_for(chain_, routes, "2025-03-01")] == ["program_manager"]  # nothing observed later
    routes += [route(DEPARTMENT, SMALL_BUSINESS_ROUTE, "2026-09-24")]
    assert [r["route"] for r in routes_for(chain_, routes)][-1] == SMALL_BUSINESS_ROUTE        # the department's, after the chain's own
    assert [r["route"] for r in first_routes(routes_for(chain_, routes), 2)] == ["program_manager", "contracting_poc", SMALL_BUSINESS_ROUTE]
    own = routes_for([uid("org", "command:navwar")], routes + [route("command:navwar", SMALL_BUSINESS_ROUTE, "2026-09-16")])
    assert [r["office_id"] for r in own if r["route"] == SMALL_BUSINESS_ROUTE] == ["command:navwar"]  # a command's own office replaces it
    legacy = ('Point of Contact - Clayton R Thomas, Contract Specialist,  619-524-7199; Stephen R Beckner, Contracting Officer, '
              '619-524-7389\n\n<a href="mailto:clayton.r.thomas@navy.mil">Contract Specialist</a>')
    assert split_pocs(legacy, "") == [("Clayton R Thomas", "clayton.r.thomas@navy.mil"), ("Stephen R Beckner", "")]
    assert split_pocs("Megan Ashley", "megan.ashley@navy.mil") == [("Megan Ashley", "megan.ashley@navy.mil")]
    print("selfcheck ok")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] == "--selfcheck":
        return selfcheck()
    return {"build": build, "show": show}[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
