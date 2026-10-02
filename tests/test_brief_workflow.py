"""The startup brief workflow's checker (research/workflow/check.py): quotes against the saved sources, record
identifiers through a resolver, and the people rules. Runs on inline text alone; the record is not needed."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("brief_check", ROOT / "research" / "workflow" / "check.py")
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)

SOURCE = check.norm('The office "will hold an industry day on 3 November 2026 for the autonomy line" per the notice.')
BRIEF = """## Sources

| Identifier | What it says (exact quote) | Status | Source | Class | Provenance |
|---|---|---|---|---|---|
| HR001126S0001 | "will hold an industry day on 3 November 2026" | Live | SAM.gov | primary | tool |
| NOT-A-RECORD-9 | "an invented passage nobody published anywhere" | Live | SAM.gov | primary | tool |
| https://example.gov/a | "will hold an industry day on 3 November 2026" | Live | example.gov | primary | web |

Ask the program manager, the decision-maker, at jane.doe@gmail.com.
"""


def resolver(ident):
    return "record" if ident == "HR001126S0001" else None


def test_quotes_identifiers_and_people():
    got = check.check(BRIEF, SOURCE, resolver)
    assert got["quotes"]["checked"] == 3 and got["quotes"]["not_found"] == 1
    assert got["quotes"]["failures"][0]["quote"].startswith("an invented passage")
    ids = got["identifiers"]
    assert ids["checked"] == 2, "web rows are not resolved against the record"
    assert [u["identifier"] for u in ids["unresolved"]] == ["NOT-A-RECORD-9"]
    people = [p["text"] for p in got["problems"] if p["check"] == "people"]
    assert any("decision-maker" in p for p in people) and any("jane.doe@gmail.com" in p for p in people)


def test_no_resolver_says_so():
    got = check.check(BRIEF, SOURCE, None)
    assert got["identifiers"]["checked"] == 0 and "AGENCY" in got["identifiers"]["note"]


def test_workflow_files_present():
    wf = ROOT / "research" / "workflow"
    script = (wf / "startup-agency-brief.js").read_text(encoding="utf-8")
    assert script.startswith("export const meta = {")
    assert "research/workflow/check.py" in script.replace("${DIR}", "research/workflow")
    linked = ROOT / ".claude" / "workflows" / "startup-agency-brief.js"
    assert linked.resolve() == (wf / "startup-agency-brief.js").resolve()
