"""The twin's object pages: every page ends with the sources that speak about the object and when each last spoke."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
from backtest import CORPUS  # noqa: E402
from pages import Layer  # noqa: E402
from pages import DNA, cell, office, person, sources, vendor  # noqa: E402
from pulse import load_people  # noqa: E402

pytestmark = pytest.mark.skipif(not CORPUS.exists(), reason="no frozen corpus on disk")


@pytest.fixture(scope="module")
def layer():
    roster = load_people()
    return Layer(json.loads(CORPUS.read_text(encoding="utf-8")), roster), roster


def test_every_page_ends_with_its_sources_and_silent_families(layer):
    lay, roster = layer
    dna = json.loads(DNA.read_text(encoding="utf-8")) if DNA.exists() else {}
    for text in (office(lay, "N00039", dna), vendor(lay, "Leidos"), cell(lay, next(n["key"] for n in lay.needs if n["owner"] == "PMA/PMW 101"))):
        assert "sources speaking about this object:" in text and "families silent:" in text, text[:200]
        assert "&amp;" not in text and "&#" not in text, "HTML entities belong to the feed, not the record"
    who = next(r["name"] for r in roster if len(r["positions"]) >= 3)
    assert f"{who}:" in person(lay, who, roster) and "sources:" in person(lay, who, roster)


def test_sources_count_statements_and_silence(layer):
    lay, _ = layer
    rows = sources([e for e in lay.events if e["family"] == "incumbent"][:50], lay.as_of)
    assert rows and sum(r["statements"] for r in rows) == 50 and all(r["first"] <= r["last"] <= lay.as_of for r in rows)
    assert rows == sorted(rows, key=lambda r: (r["last"], r["source"]), reverse=True)


def test_the_record_holds_no_html_entities():
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    bad = [e["id"] for e in corpus["events"] if "&amp;" in e["title"] or "&amp;" in (e.get("vendor") or "")]
    bad += [n["key"] for n in corpus["needs"] if "&amp;" in n["title"]]
    assert not bad, f"{len(bad)} rows carry &amp;: unescape at the source reader, not here ({bad[:3]})"
