"""Checks for the reproducible LRAE data package under datapack/.

The package is regenerated from saved bytes by research/tools/lrae_package.py. These tests read
the committed package; the regeneration check runs only when the raw spreadsheet is on disk.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "datapack" / "lrae_navwar_2025-06"
DECISIONS = {"included", "excluded", "duplicate", "unresolved"}
JOIN_TYPES = {"office", "existing_contract", "notice", "contact"}
METHODS = {"explicit", "inferred"}


def _csv(name: str) -> list[dict]:
    path = PACK / name
    if not path.exists():
        pytest.skip(f"{name} not built yet")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _source() -> dict:
    path = PACK / "SOURCE.json"
    if not path.exists():
        pytest.skip("SOURCE.json not built yet")
    return json.loads(path.read_text(encoding="utf-8"))


def test_source_names_the_bytes_and_the_outputs():
    source = _source()
    for key in ("source_url", "release_date", "retrieved_at", "sha256", "size", "sheet", "header_row", "refetch", "regenerate", "outputs"):
        assert key in source, key
    assert len(source["sha256"]) == 64
    for name, digest in source["outputs"].items():
        assert (PACK / name).exists(), name
        assert hashlib.sha256((PACK / name).read_bytes()).hexdigest() == digest, f"{name} differs from SOURCE.json"


def test_every_raw_row_has_one_decision_and_counts_reconcile():
    raw, classified = _csv("rows_raw.csv"), _csv("rows_classified.csv")
    assert len(raw) == len(classified)
    assert [r["row_number"] for r in raw] == [c["row_number"] for c in classified]
    decisions = Counter(c["include_decision"] for c in classified)
    assert set(decisions) <= DECISIONS
    assert sum(decisions.values()) == len(raw)
    assert all(c["reason"] for c in classified)
    assert all(c["office_id"] for c in classified if c["include_decision"] == "included")
    assert all(c["sheet"] and c["pid"] for c in classified)
    text = (PACK / "reconciliation.md").read_text(encoding="utf-8")
    assert f"| raw | {len(raw)} |" in text
    for decision in DECISIONS:
        assert f"| {decision} | {decisions.get(decision, 0)} |" in text


def test_pids_are_unique_unless_marked_duplicate():
    classified = _csv("rows_classified.csv")
    seen = set()
    for c in classified:
        if c["pid"] in seen:
            assert c["include_decision"] == "duplicate", c["row_number"]
        seen.add(c["pid"])


def test_joins_are_labelled_and_every_included_row_has_an_office_join():
    classified, joins = _csv("rows_classified.csv"), _csv("joins.csv")
    included = {c["row_number"] for c in classified if c["include_decision"] == "included"}
    assert {j["join_type"] for j in joins} <= JOIN_TYPES
    assert {j["method"] for j in joins} <= METHODS
    office_rows = {j["row_number"] for j in joins if j["join_type"] == "office" and j["target_id"]}
    assert included <= office_rows
    assert {j["row_number"] for j in joins} <= included, "joins exist only for included rows"
    for j in joins:
        assert j["key_used"] and j["note"], j
        if j["target_id"]:
            assert j["evidence_ref"], j
        if j["method"] == "inferred":
            assert j["target_id"].startswith(("attribution:", "sam:")), j
            assert "vehicle" in j["note"] or j["target_id"].startswith("attribution:"), j


def test_layers_reference_needs_and_evidence():
    needs = _csv("layers/needs.csv")
    evidence = {e["id"] for e in _csv("layers/evidence.csv")}
    need_ids = {n["id"] for n in needs}
    assert len(need_ids) == len(needs)
    assert all(n["evidence_id"] in evidence and n["office_id"] and n["valid_from"] for n in needs)
    for name in ("need_requirements.csv", "funding_observations.csv", "procurement_refs.csv"):
        for row in _csv(f"layers/{name}"):
            assert row["need_id"] in need_ids, (name, row)
    assert all(f["observation_type"] == "procurement_estimate" for f in _csv("layers/funding_observations.csv"))


def test_regeneration_is_byte_identical(tmp_path):
    source = _source()
    if not (ROOT / source["raw_path"]).exists():
        pytest.skip("raw spreadsheet not on this machine")
    pytest.importorskip("openpyxl")
    env = {"LRAE_PACK_DIR": str(tmp_path)}
    result = subprocess.run([sys.executable, str(ROOT / "research" / "tools" / "lrae_package.py"), "build"],
                            cwd=ROOT, env={**__import__("os").environ, **env}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    for name, digest in source["outputs"].items():
        assert hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() == digest, name
