#!/usr/bin/env python3
"""Read SAM.gov's federal hierarchy into the Department of the Air Force organization memory (the `memory` stage of the
airforce profile).

    AGENCY=airforce python research/tools/org_memory_airforce.py build           # research/agencies/airforce/memory/organization_seed.json
    AGENCY=airforce python research/tools/org_memory_airforce.py build --check   # exit 1 when a build would change the file
    AGENCY=airforce python research/tools/org_memory_airforce.py collect         # fetch the records the build reads, not yet saved
    python research/tools/org_memory_airforce.py selfcheck

The Department publishes no forecast in a readable file and its own sites (af.mil, spaceforce.mil) answer 403 here, so
the memory rests on SAM.gov federal organization records alone: the Department, AFMC, AFLCMC, AFRL, AFTC, AFNWC, three
PEOs (Digital, Weapons, Strategic Systems) and the seven contracting offices the profile sweeps, each with the codes and
the hierarchy its record prints. An office record's path also names the organizations between it and the Department
(Space Systems Command and two of its PEOs, and three organizations under AFLCMC and AFNWC); those are nodes too, resting on
the record that names them, with no code, since the path prints none. `child_of` is the nearest organization above on
the record's own path that the memory holds.

Every record is `review_status: draft` and carries `generator: org_memory_airforce`; a rebuild is byte for byte the
same while the saved records are.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agency import KEY, MANIFEST, MEMORY, NOTE_TAG, P, ROOT  # noqa: E402
from org_memory_army import SAM_ORG, by_url, sam_parent, sam_record, slug  # noqa: E402
from org_memory_darpa import node, observation, relationship, unique_aliases  # noqa: E402
from org_memory_lrae import squash  # noqa: E402

SEED = MEMORY / "organization_seed.json"
GENERATOR = "org_memory_airforce"
AGENCY_ID = P["agency"]["node"]
# SAM.gov organization id -> node: the Department, the materiel command and its centers, the PEOs above the swept
# offices, then the swept contracting offices themselves (the profile's sam_org_nodes).
SAM_NODES = {"300000251": AGENCY_ID, "100000570": "command:afmc", "100000997": "command:aflcmc", "100000740": "center:afrl",
             "100013254": "command:aftc", "100001019": "command:afnwc", "500188321": "peo:digital", "100001009": "peo:weapons",
             "100001021": "peo:strategic", **P["sam_org_nodes"]}
KINDS = {"agency": "agency", "command": "command", "center": "technical_center", "peo": "program_executive_office",
         "contracting": "contracting_office"}
SAM_FIELDS = ("orgKey", "name", "type", "level", "fullParentPath", "fullParentPathName", "aacCode", "fpdsCode", "cgac", "code",
              "shortName", "codeHierarchy")
CONTRACT = ("08_org_memory_format.md: observations are what a source states; relationships are dated claims resting on "
            "observations; interpretations are our readings; corrections are retractions")
SCOPE = ("Department of the Air Force acquisition (the Air Force and the Space Force): the Department, AFMC and its centers, "
         "the PEOs above the swept offices and the contracting offices swept, as SAM.gov's federal hierarchy prints them")
NOTES = "drafted by org_memory_airforce from SAM.gov federal organization records; names as printed in the source"


def rows() -> list[dict]:
    return [json.loads(l) for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]


def kind_of(nid: str) -> str:
    return KINDS[nid.split(":", 1)[0]]


def codes_of(org_id: str, nid: str, rec: dict) -> dict:
    """The codes a record states: the DoDAAC of an office, the FPDS agency code of the Department, the short code of a
    command or PEO (AFMC, PEO-DIGITAL) where SAM.gov prints one."""
    codes = {"sam_organization_id": org_id}
    aac, code = str(rec.get("aacCode") or "").strip(), str(rec.get("code") or "").strip()
    if aac:
        codes["uic"] = aac
    if nid == AGENCY_ID:
        codes["fpds_agency_id"] = str(rec.get("fpdsCode") or P["agency"]["subtier_code"])
    elif code and code != aac and not code.isdigit():
        codes["office_code"] = code
    return codes


def path_nodes(recs: dict[str, dict]) -> dict[str, tuple[str, str, str]]:
    """The organizations below the Department that a record's own path names and the memory holds no record for:
    orgKey -> (node id, name as the path prints it, the orgKey of the first record whose path names it). A PEO by its
    printed name; any other is a command. A path whose names do not pair with its keys is not read."""
    out = {}
    for org_id, rec in recs.items():
        keys, names = str(rec.get("fullParentPath") or "").split("."), str(rec.get("fullParentPathName") or "").split(".")
        if len(keys) != len(names):
            continue
        for key, name in list(zip(keys, names))[2:-1]:
            if key not in SAM_NODES and key not in out:
                name = squash(name)
                nid = f"peo:{slug(name[4:])}" if name.startswith("PEO ") else f"command:{slug(name)}"
                out[key] = (nid, name, org_id)
    return out


def build_seed(manifest: list[dict]) -> dict:
    obs, rels, nodes = [], [], []
    sam = {oid: by_url(manifest, SAM_ORG.format(oid)) for oid in SAM_NODES}
    missing = [k for k, v in sam.items() if v is None]
    if missing:
        raise SystemExit(f"SAM.gov records not saved yet: {', '.join(missing)}; run `collect` first")
    recs = {org_id: sam_record(row) for org_id, row in sam.items()}
    on_path = path_nodes(recs)
    known = {**SAM_NODES, **{k: v[0] for k, v in on_path.items()}}
    obs_of = {}

    def child_of(nid: str, parent: str, oid: str, day: str, path_name: str) -> None:
        rels.append(relationship(f"rel:airforce:{len(rels) + 1:03d}", "child_of", nid, parent, [oid], day, dates_status="unknown",
                                 dates_note="the record states the organization's place in the hierarchy, not since when",
                                 status_note=f"stated by the SAM.gov organization record of the latest cited retrieval "
                                             f"({path_name}); not re-verified since"))

    for org_id, nid in SAM_NODES.items():
        row, rec = sam[org_id], recs[org_id]
        day = row["retrieved_at"][:10]
        oid = obs_of[org_id] = f"obs:airforce:{len(obs) + 1:03d}"
        passage = json.dumps({k: rec[k] for k in SAM_FIELDS if rec.get(k) is not None}, separators=(",", ":"), ensure_ascii=False)
        stated = [v[0] for v in on_path.values() if v[2] == org_id]
        obs.append(observation(oid, row, day, "naming", passage, [nid, *stated]))
        codes = codes_of(org_id, nid, rec)
        aliases = [{"text": t, "observation_ids": [oid]} for t in (codes.get("uic"), codes.get("office_code"), rec.get("shortName")) if t]
        if nid == AGENCY_ID:
            aliases.append({"text": P["agency"]["subtier_name"], "observation_ids": [oid]})
        n = node(nid, kind_of(nid), squash(str(rec.get("name") or "")) or nid, [oid], unique_aliases(aliases), codes)
        n["generator"], n["notes"] = GENERATOR, NOTES
        nodes.append(n)
        parent = sam_parent(rec, known)
        if parent:
            child_of(nid, parent, oid, day, rec.get("fullParentPathName"))
        if kind_of(nid) == "contracting_office":
            rels.append(relationship(f"rel:airforce:{len(rels) + 1:03d}", "contracts_for", nid, AGENCY_ID, [oid], day,
                                     role="contracting office of the Department of the Air Force", dates_status="unknown",
                                     status_note="stated by the SAM.gov organization record; not re-verified since"))
    # The organizations the office records' paths name (Space Systems Command and its PEOs among them):
    # each rests on the record whose path states it, and sits under the nearest known organization above it there.
    for key, (nid, name, org_id) in on_path.items():
        rec, row = recs[org_id], sam[org_id]
        n = node(nid, kind_of(nid), name, [obs_of[org_id]], [], {"sam_organization_id": key})
        n["generator"] = GENERATOR
        n["notes"] = (f"named on the path of the SAM.gov record {org_id} ({rec.get('name')}), which prints no type or code for it; "
                      "the type is read from the printed name; " + NOTES)
        nodes.append(n)
        path = str(rec["fullParentPath"]).split(".")
        parent = sam_parent({"fullParentPath": ".".join(path[:path.index(key) + 1])}, known)
        if parent:
            child_of(nid, parent, obs_of[org_id], row["retrieved_at"][:10], rec.get("fullParentPathName"))
    for r in rels:
        r["generator"] = GENERATOR
    return {"generated": max(r["retrieved_at"][:10] for r in sam.values()), "contract": CONTRACT, "scope": SCOPE,
            "nodes": nodes, "observations": obs, "relationships": rels, "interpretations": []}


def dumps(seed: dict) -> str:
    return json.dumps(seed, indent=1, ensure_ascii=False) + "\n"


def build(check: bool = False) -> int:
    if KEY != "airforce":
        print(f"this reader builds the airforce memory; the profile is {KEY} (set AGENCY=airforce)", file=sys.stderr)
        return 2
    seed = build_seed(rows())
    text = dumps(seed)
    kinds = Counter(n["type"] for n in seed["nodes"])
    print(f"{len(seed['nodes'])} node(s) {dict(kinds)}, {len(seed['observations'])} observation(s), {len(seed['relationships'])} relationship(s)")
    if check:
        if not SEED.exists() or SEED.read_text(encoding="utf-8") != text:
            print(f"{SEED.relative_to(ROOT)} differs from a fresh build; run `build` to regenerate", file=sys.stderr)
            return 1
        return 0
    SEED.parent.mkdir(parents=True, exist_ok=True)
    SEED.write_text(text, encoding="utf-8")
    print(f"written to {SEED.relative_to(ROOT)}")
    return 0


def collect() -> int:
    """The SAM.gov organization records the build reads, not yet saved."""
    from fetch import collect_missing  # noqa: E402
    return 1 if collect_missing([(SAM_ORG.format(oid), f"SAM.gov federal organization record{NOTE_TAG}: {oid} ({nid})")
                                 for oid, nid in SAM_NODES.items()]) else 0


def selfcheck() -> int:
    # The FA2487 record's path as SAM.gov printed it in a notice hierarchy on 2026-09-26: its nearest known ancestor is AFTC.
    assert sam_parent({"fullParentPath": "100000000.300000251.100000570.100013254.500020405"}, SAM_NODES) == "command:aftc"
    assert sam_parent({"fullParentPath": "100000000.300000251"}, SAM_NODES) is None
    # The FA8807 record as SAM.gov answered it on 2026-09-26, trimmed: its path names SSC and a PEO the memory has no record for.
    rec = {"fullParentPath": "100000000.300000251.500188815.500188822.500038471",
           "fullParentPathName": "DEPT OF DEFENSE.DEPT OF THE AIR FORCE.SPACE SYSTEMS COMMAND.PEO MILITARY COMMUNICATION AND POSITION "
                                 "NAVIGATION TIMING.FA8807 MIL COMM AND PNT SSC/CGK"}
    assert path_nodes({"500038471": rec}) == {
        "500188815": ("command:space-systems-command", "SPACE SYSTEMS COMMAND", "500038471"),
        "500188822": ("peo:military-communication-and-position-navigation-timing", "PEO MILITARY COMMUNICATION AND POSITION NAVIGATION TIMING", "500038471")}
    assert path_nodes({"x": {**rec, "fullParentPathName": "A.B"}}) == {}, "a path whose names do not pair with its keys is not read"
    assert [kind_of(n) for n in (AGENCY_ID, "command:afmc", "center:afrl", "peo:digital", "contracting:fa8650")] == [
        "agency", "command", "technical_center", "program_executive_office", "contracting_office"]
    assert codes_of("100000570", "command:afmc", {"code": "AFMC"}) == {"sam_organization_id": "100000570", "office_code": "AFMC"}
    assert codes_of("100025313", "contracting:fa8650", {"aacCode": "FA8650", "code": "FA8650"}) == {"sam_organization_id": "100025313", "uic": "FA8650"}
    assert codes_of("300000251", AGENCY_ID, {"fpdsCode": "5700", "code": "5700"})["fpds_agency_id"] == "5700"
    # The profile's patterns against numbers the saved notices and portal pages print, and not another agency's.
    topic, piid, sol, rfp = (re.compile(p) for p in (P["topic_re"], P["piid_re"], P["solicitation_re"], P["reading"]["rfp_re"]))
    assert all(topic.fullmatch(c) for c in ("AF193-005", "AF19C-T001", "AF212-0001", "AF203-DCSO1", "AFX255-DPCSO1", "SF254-D1001",
                                            "X224-ODCSO1", "DAF26BZ01-DV001", "DAF26TZ06-NV006"))
    assert not any(topic.search(c) for c in ("N251-001", "A20-179", "ARM26BX06-NV012", "HR001119S0035-14"))
    assert piid.search("FA875024CB108") and piid.search("FA8650-26-C-B017") and not piid.search("W58RGZ-26-C-0001")
    assert sol.search("FA2487-24-Q-B001") and not sol.search("N00039-24-R-4019")
    assert rfp.findall("FA2394-26-R-B003") == ["FA2394-26-R-B003"] and rfp.findall("FA873026RB001") == ["FA873026RB001"]
    assert not rfp.findall("FA8750-25-S-7004"), "a BAA (S) is not a request for proposals"
    print("org_memory_airforce selfcheck ok")
    return 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        sys.exit(2)
    if argv[0] in ("selfcheck", "--selfcheck"):
        sys.exit(selfcheck())
    if argv[0] == "collect":
        sys.exit(collect())
    if argv[0] == "--check" or argv[:2] == ["build", "--check"]:
        sys.exit(build(check=True))
    if argv[0] == "build":
        sys.exit(build())
    print(__doc__)
    sys.exit(2)
