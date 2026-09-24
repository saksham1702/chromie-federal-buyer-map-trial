"""From a capability to one letter: the model walks and writes, the checks refuse what the record does not carry, and a
saved run replays from its cassettes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
from backtest import CORPUS, register_problems  # noqa: E402
from outreach import OUT, Layer, load_people, outreach, selfcheck, settled  # noqa: E402

SAVED = sorted(OUT.glob("[!.]*.json")) if OUT.exists() else []  # an external volume adds ._ shadow files beside each run


def test_the_checks_refuse_what_the_record_does_not_carry():
    assert selfcheck() == 0


@pytest.mark.skipif(not CORPUS.exists() or not SAVED, reason="no frozen corpus or no saved outreach run")
@pytest.mark.parametrize("path", SAVED, ids=[p.stem for p in SAVED])
def test_a_saved_run_replays_and_holds(path):
    saved = json.loads(path.read_text(encoding="utf-8"))
    layer = Layer(json.loads(CORPUS.read_text(encoding="utf-8")), load_people())
    try:
        again = outreach(layer, saved["company"], saved["profile"], saved["budget"], replay_only=True)
    except LookupError:
        pytest.skip("the record moved since this run was made; rerun outreach.py run")
    assert settled(again) == settled(saved)
    assert saved["status"] in ("written", "no fit") and not saved["chain_problems"] and not saved["email_problems"]
    if saved["email"]:
        assert not register_problems(saved["email"]["body"]) and (saved["contacts"] or saved["chain"]["routes"])
