#!/usr/bin/env python3
"""One event vocabulary: every event type sits at one stage of the
procurement path and carries a polarity, so a cell can say where the requirement stands, what would have to
happen next, and which statements argue for the buy and which against it.

Stage is the path position: strategy, budget, program, research, engagement, forecast, market_research,
solicitation, award, execution. Polarity is what the statement does to the case for a coming buy: positive
(the path moves), negative (delay, cancellation, extension, sole source, a cut), neutral (a fact about the
office that moves nothing by itself). Polarity is read from the type, and for four types from the words.

    python research/tools/vocabulary.py --selfcheck
"""

from __future__ import annotations

import re
import sys

STAGES = ("strategy", "budget", "program", "research", "engagement", "forecast", "market_research", "solicitation", "award", "execution")
# The path a requirement walks to a buy; execution is the incumbent's contract, not a step toward the next one.
PATH = ("forecast", "market_research", "solicitation", "award")
MILESTONE = {"forecast": "a forecast row", "market_research": "a sources sought or request for information",
             "solicitation": "a presolicitation or solicitation", "award": "an award"}

STAGE = {
    "strategy_change": "strategy", "capability_priority": "strategy", "congressional_directive": "strategy",
    "leadership_change": "strategy", "reorganization": "strategy",
    "funding_change": "budget", "budget_line": "budget",
    "program_created": "program", "program_delayed": "program", "program_cancelled": "program", "audit_finding": "program",
    "sbir_topic": "research", "sbir_selection": "research", "prototype_transition": "research",
    "industry_engagement": "engagement", "conference_appearance": "engagement",
    "forecast_created": "forecast", "forecast_changed": "forecast",
    "rfi_released": "market_research",
    "presolicitation_posted": "solicitation", "rfp_released": "solicitation", "justification_posted": "solicitation",
    "contract_awarded": "award", "protest": "award",
    "contract_modified": "execution", "contract_extended": "execution", "contract_expires": "execution",
}
POLARITY = {
    "program_delayed": "negative", "program_cancelled": "negative", "contract_extended": "negative", "protest": "negative",
    "justification_posted": "negative",  # a sole-source or limited-competition justification closes the buy to others
    "leadership_change": "neutral", "reorganization": "neutral", "audit_finding": "neutral", "contract_awarded": "neutral",
}
CUT_RE = re.compile(r"\b(cut|cuts|reduc\w*|decreas\w*|below|terminat\w*|cancel\w*|rescind\w*|shortfall|divest\w*|delay\w*)\b", re.I)
RENEWAL_RE = re.compile(r"\b(sole[- ]source|bridge|extension|extend\w*|exercis\w* (?:the |an? )?option|option period)\b", re.I)
AMOUNT_RE = re.compile(r"FY\d{4} \$(\d[\d,]*\.?\d*)M")
CUT_SHARE = 0.5  # a line that falls to under half of the year before, or to nothing, is a cut; a smaller dip moves nothing


# A capability a company names, with the words Navy records use for it. A topic outside the list is searched as written.
# Words that name a command as well as a field (space, as in Space and Naval Warfare) stay out.
CAPABILITIES = {
    "autonomy": ("autonomous", "autonomy", "unmanned", "uncrewed", "UUV", "USV", "UAS", "UAV", "robotic", "swarm"),
    "undersea": ("undersea", "underwater", "subsea", "sonar", "acoustic", "UUV", "seabed", "anti-submarine"),
    "cyber": ("cyber", "cybersecurity", "zero trust", "encryption", "cryptographic", "intrusion detection"),
    "artificial intelligence": ("artificial intelligence", "machine learning", "AI/ML", "neural network", "computer vision", "deep learning"),
    "communications": ("communications", "radio", "SATCOM", "data link", "datalink", "Link 16", "waveform", "antenna"),
    "satellites": ("satellite", "spacecraft", "orbital", "space-based", "SATCOM"),
    "electronic warfare": ("electronic warfare", "jamming", "jammer", "SIGINT", "electronic attack", "decoy"),
    "sensors": ("radar", "sensor", "electro-optical", "infrared", "EO/IR", "lidar", "sonar"),
    "command and control": ("command and control", "C2", "C4I", "battle management", "common operational picture", "mission planning"),
    "networks": ("network", "cloud", "enterprise services", "data center", "CANES", "ADNS", "NMCI", "NGEN"),
    "training": ("training", "simulation", "simulator", "trainer", "live virtual constructive", "LVC"),
    "logistics": ("logistics", "sustainment", "maintenance", "supply chain", "depot"),
    "positioning and timing": ("positioning", "navigation", "timing", "PNT", "GPS", "inertial"),
    "directed energy": ("directed energy", "laser", "high power microwave"),
    "counter unmanned": ("counter-UAS", "counter UAS", "C-UAS", "counter-drone", "counter unmanned"),
    "hypersonics": ("hypersonic",),
}
CAPABILITY_NAMES = {"autonomous systems": "autonomy", "unmanned systems": "autonomy", "ai": "artificial intelligence",
                    "machine learning": "artificial intelligence", "ew": "electronic warfare", "c2": "command and control",
                    "pnt": "positioning and timing", "c-uas": "counter unmanned", "asw": "undersea", "anti-submarine warfare": "undersea",
                    "space": "satellites"}


def capability_terms(topic: str) -> list[str]:
    """A topic's search words: a named capability's words, else the words as written; topics split on ; and ,."""
    out = []
    for part in (p.strip() for p in re.split(r"[;,]", topic)):
        name = CAPABILITY_NAMES.get(part.lower(), part.lower())
        out += CAPABILITIES.get(name, (part,) if part else ())
    return list(dict.fromkeys(out))


def stage(event_type: str) -> str:
    return STAGE.get(event_type, "strategy")


def money_polarity(amounts: list[float]) -> str:
    """Fiscal-year amounts in order: rising or holding is positive, falling to nothing or under half is a cut, a
    smaller dip is neutral; a line with no money in any year says nothing."""
    if not any(amounts):
        return "neutral"
    if len(amounts) < 2:
        return "positive"
    before, after = amounts[-2], amounts[-1]
    if after >= before:
        return "positive"
    return "negative" if after < before * CUT_SHARE else "neutral"


def polarity(event_type: str, statement: str = "", slip: bool = False) -> str:
    """The type decides; four types read the statement (the event's title, not the document behind it): a funding
    line's amounts or a funding claim's words, a budget line's amounts, a forecast revision that moved later, a
    modification that keeps the incumbent."""
    if event_type in POLARITY:
        return POLARITY[event_type]
    if event_type in ("funding_change", "budget_line"):
        amounts = [float(a.replace(",", "")) for a in AMOUNT_RE.findall(statement)]
        if amounts:
            return money_polarity(amounts)
        return "neutral" if event_type == "budget_line" else ("negative" if CUT_RE.search(statement) else "positive")
    if event_type == "forecast_changed":
        return "negative" if slip else "neutral"
    if event_type == "contract_modified":
        return "negative" if RENEWAL_RE.search(statement) else "neutral"
    return "positive"


def classify(event_type: str, statement: str = "", slip: bool = False) -> dict:
    return {"stage": stage(event_type), "polarity": polarity(event_type, statement, slip)}


def stage_of(events: list[dict], as_of: str, within_days: int = 730) -> str:
    """Where the requirement stands as of a date: the stage of the newest path event (forecast, market research,
    solicitation, award) inside the window; `shaping` when only earlier stages spoke; `dormant` when nothing did."""
    from datetime import date, timedelta
    since = (date.fromisoformat(as_of) - timedelta(days=within_days)).isoformat()
    recent = [e for e in events if since < e["available_by"] <= as_of]
    path = [e for e in recent if e.get("stage", stage(e["event_type"])) in PATH and e.get("polarity", polarity(e["event_type"])) != "negative"]
    if path:
        newest = max(path, key=lambda e: (e["available_by"], PATH.index(e.get("stage", stage(e["event_type"])))))
        return newest.get("stage", stage(newest["event_type"]))
    if any(e.get("stage", stage(e["event_type"])) != "execution" for e in recent):
        return "shaping"
    return "dormant"


def next_milestones(current: str) -> list[str]:
    """What would have to happen next: the path steps after the current stage, in order."""
    start = PATH.index(current) + 1 if current in PATH else 0
    return [MILESTONE[s] for s in PATH[start:]]


def selfcheck() -> int:
    assert set(STAGE.values()) <= set(STAGES) and set(POLARITY) <= set(STAGE)
    assert polarity("program_delayed") == "negative" and polarity("forecast_created") == "positive"
    assert polarity("funding_change", "the budget adds $1 billion for infrastructure") == "positive"
    assert polarity("funding_change", "the request cuts the line by 40 percent") == "negative"
    assert polarity("budget_line", "FY2026 $0.000M, FY2027 $0.000M") == "neutral"
    assert polarity("funding_change", "line 2614 ATDLS: FY2026 $58.739M, FY2027 $52.758M") == "neutral", "a dip of a tenth is not a cut"
    assert polarity("funding_change", "line 2614 ATDLS: FY2026 $58.739M, FY2027 $61.000M") == "positive"
    assert polarity("funding_change", "line 2614 ATDLS: FY2026 $58.739M, FY2027 $0.000M") == "negative"
    assert polarity("funding_change", "line 2614 ATDLS: FY2026 $58.739M, FY2027 $20.000M") == "negative"
    assert polarity("budget_line", "FY2026 $58.739M, FY2027 $52.758M") == "neutral" and polarity("budget_line", "no amounts") == "neutral"
    assert polarity("forecast_changed", slip=True) == "negative" and polarity("forecast_changed") == "neutral"
    assert polarity("contract_modified", "Notice of Intent to Award Sole Source Modification") == "negative"
    assert polarity("contract_modified", "administrative change") == "neutral"
    assert polarity("never_seen_before") == "positive" and stage("never_seen_before") == "strategy"
    ev = [{"event_type": "sbir_topic", "available_by": "2025-01-01"}, {"event_type": "forecast_created", "available_by": "2025-06-01"},
          {"event_type": "rfi_released", "available_by": "2026-02-01"}, {"event_type": "contract_expires", "available_by": "2020-01-01"}]
    assert stage_of(ev, "2026-09-01") == "market_research"
    assert stage_of(ev, "2025-03-01") == "shaping", stage_of(ev, "2025-03-01")
    assert stage_of(ev, "2021-01-01") == "dormant", "an old contract end alone places nothing on the path"
    assert stage_of(ev + [{"event_type": "forecast_changed", "available_by": "2026-05-01", "stage": "forecast", "polarity": "negative"}], "2026-09-01") == "market_research", \
        "a slip does not move the requirement back along the path"
    assert next_milestones("market_research") == [MILESTONE["solicitation"], MILESTONE["award"]]
    assert next_milestones("shaping") == [MILESTONE[s] for s in PATH] and next_milestones("award") == []
    assert "UUV" in capability_terms("autonomous systems") and capability_terms("Link 22; ai")[0] == "Link 22"
    assert "machine learning" in capability_terms("Link 22; ai") and capability_terms(" ; ") == []
    print("vocabulary selfcheck ok")
    return 0


if __name__ == "__main__":
    sys.exit(selfcheck() if "--selfcheck" in sys.argv[1:] else print(__doc__) or 2)
