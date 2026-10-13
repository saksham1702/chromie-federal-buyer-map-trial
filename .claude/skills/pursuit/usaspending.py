"""A contract's dollars from USAspending, which the agent views do not hold (contract rows carry piid, vendor, offices
and end date only). Public API, no key, read only. One line of JSON per award the PIID matches exactly.

    python3 .claude/skills/pursuit/usaspending.py award 70RTAC26FR0000045 [PIID ...]
    python3 .claude/skills/pursuit/usaspending.py check      # self-check against one known award

obligated = total obligated to date; ceiling = base and all options (a vehicle's ceiling for an IDV).
"""
import json
import sys
import urllib.request

API = "https://api.usaspending.gov/api/v2"
CONTRACTS = ["A", "B", "C", "D"]
IDVS = ["IDV_A", "IDV_B", "IDV_B_A", "IDV_B_B", "IDV_B_C", "IDV_C", "IDV_D", "IDV_E"]


def call(path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json", "User-Agent": "fbm-pursuit/1"})
    for attempt in range(3):  # the API answers an occasional 502
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 2:
                raise
    return {}


def compact(piid: str) -> str:
    return piid.replace("-", "").replace(" ", "").upper()


def award(piid: str) -> list[dict]:
    """Every award whose id is exactly this PIID: contracts first, then vehicles (IDVs)."""
    for codes in (CONTRACTS, IDVS):
        hits = call("/search/spending_by_award/", {
            "filters": {"award_ids": [piid], "award_type_codes": codes},
            "fields": ["Award ID", "generated_internal_id"], "limit": 10, "page": 1}).get("results", [])
        ids = [h["generated_internal_id"] for h in hits if compact(h.get("Award ID") or "") == compact(piid)]
        if ids:
            return [detail(i) for i in ids]
    return [{"piid": piid, "found": False, "note": "no USAspending contract or IDV has this exact award id"}]


def detail(uid: str) -> dict:
    j = call(f"/awards/{uid}/")
    pop = j.get("period_of_performance") or {}
    aw, fu = j.get("awarding_agency") or {}, j.get("funding_agency") or {}
    return {"piid": j.get("piid"), "found": True, "type": j.get("type_description"),
            "obligated": j.get("total_obligation"), "ceiling": j.get("base_and_all_options"),
            "outlays": j.get("total_outlay"), "signed": j.get("date_signed"),
            "start": pop.get("start_date"), "end": pop.get("end_date"), "potential_end": pop.get("potential_end_date"),
            "recipient": (j.get("recipient") or {}).get("recipient_name"),
            "awarding": " > ".join(x for x in ((aw.get("subtier_agency") or {}).get("name"), aw.get("office_agency_name")) if x),
            "funding": " > ".join(x for x in ((fu.get("subtier_agency") or {}).get("name"), fu.get("office_agency_name")) if x),
            "parent": (j.get("parent_award") or {}).get("piid"), "description": (j.get("description") or "")[:200],
            "url": f"https://www.usaspending.gov/award/{uid}"}


if __name__ == "__main__":
    cmd, args = (sys.argv[1:2] or ["check"])[0], sys.argv[2:]
    if cmd == "check":  # DHS enterprise cloud order (AWS): obligated $23,983,144.57 on 2026-10-13, can only grow
        r = award("70RTAC26FR0000045")[0]
        assert r["found"] and "AMAZON" in (r["recipient"] or "").upper() and r["obligated"] >= 23_983_144.57, r
        assert award("NOT-A-PIID-0000")[0]["found"] is False
        print("ok", json.dumps(r))
    elif cmd == "award" and args:
        for p in args:
            for r in award(p):
                print(json.dumps(r))
    else:
        sys.exit(__doc__)
