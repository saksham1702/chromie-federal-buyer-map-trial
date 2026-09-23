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

Merge rule: one person per e-mail; without an e-mail, one person per normalised name and office (ranks and
honorifics dropped, "Last, First" turned around, middle initials dropped). Two people who share a name, have no
e-mail and sit in different offices stay two people. Nobody is invented: every position points at the document.

  python research/tools/people.py build          # writes research/memory/people.json
  python research/tools/people.py show pmw:101   # whom the sources tie to an office, newest first
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
REMARKS = ROOT / "research" / "events" / "remarks_events.json"
NEWS = ROOT / "research" / "events" / "news_observations.json"
SEED = ROOT / "research" / "memory" / "organization_seed.json"
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


def norm_name(name: str) -> str:
    """'CAPT Raphael R. Castillejo' and 'Castillejo, Raphael' both give 'raphael castillejo'."""
    name = re.sub(r"\(.*?\)", " ", name or "")
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
            name = (poc.get("fullName") or "").strip()
            if not norm_name(name):
                continue
            title = f"{poc.get('type') or 'point of'} point of contact on {d['type']} {d['solicitation'] or d['id']}"
            out.append((name, (poc.get("email") or "").strip().lower(),
                        position(office, POC_ROLE, title, d["posted"], "sam_gov_site_api", d["id"], SAM_VIEW.format(d["id"]), d["title"])))
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
    # One person per e-mail even when a name-keyed row later turns out to carry that e-mail elsewhere: nothing to
    # do here, the e-mail rows already merged; name-only rows stay apart by office as the rule says.
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
                    "name": max(person["names"], key=lambda n: ("," not in n, person["names"][n], len(n))),
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


def show(argv: list[str]) -> int:
    office = argv[0] if argv else "pmw:101"
    people = json.loads(PEOPLE.read_text(encoding="utf-8"))["rows"]
    for c in contacts_for([uid("org", office)], people, limit=20):
        print(f"{c['observed_at']}  {c['name']:32} {c['role']:20} {c['source']:26} {c['source_ref'][:40]}")
    return 0


def selfcheck() -> int:
    assert norm_name("CAPT Raphael R. Castillejo") == norm_name("Castillejo, Raphael") == "raphael castillejo"
    assert norm_name("The Honorable Hung Cao") == "hung cao" and norm_name("Mr. Eric Andalis") == "eric andalis"
    assert norm_name("Ashley, Megan") == "megan ashley" and norm_name("") == "" and norm_name("A.") == ""
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
    got = contacts_for([uid("org", "pmw:101"), uid("org", "peo:c4i")], people)
    assert [c["name"] for c in got] == ["Megan Ashley"] and got[0]["office"] == "pmw:101" and got[0]["email"] == "megan@navy.mil"
    assert contacts_for([uid("org", "pmw:101")], people, as_of="2025-12-31") == []
    print("selfcheck ok")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] == "--selfcheck":
        return selfcheck()
    return {"build": build, "show": show}[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
