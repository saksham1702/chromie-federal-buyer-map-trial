"""One check for the research package: every artifact parses and carries its evidence.

Each test skips while its artifact has not been written yet and enforces the rules once it
exists, so the suite stays green through the phases without weakening the rules.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

EVIDENCE_CLASSES = {"directly_documented", "inferred", "ambiguous", "unresolved"}
VERIFICATION_STATUSES = {"verified", "not_inspected", "blocked", "restricted", "stale"}
ACCESS_MODES = {"api", "export", "webpage", "pdf", "spreadsheet", "manual"}
FETCH_METHODS = {"direct", "wayback", "browserbase", "manual"}
REGISTRY_REQUIRED = {
    "source_key", "provider_name", "official_url", "responsible_org", "lifecycle_stages",
    "fields_and_identifiers", "historical_coverage", "publication_frequency", "reporting_lag",
    "access_mode", "access_restrictions", "extraction_difficulty", "answers", "cannot_answer",
    "proposed_monitor_frequency", "inspected_example", "verification_status", "last_verified_at",
}


def _load(name: str):
    path = RESEARCH / name
    if not path.exists():
        pytest.skip(f"{name} not written yet")
    return json.loads(path.read_text(encoding="utf-8"))


def _dated(value) -> bool:
    return isinstance(value, str) and bool(DATE_RE.match(value))


def _has_evidence(items) -> bool:
    return bool(items) and all(
        isinstance(e, dict) and e.get("source_url") and _dated(e.get("observed_at")) for e in items
    )


def test_source_registry_rows_are_complete_and_inspected() -> None:
    rows = _load("source_registry.json")
    keys = [row["source_key"] for row in rows]
    assert len(keys) == len(set(keys)), "duplicate source_key"
    for row in rows:
        missing = REGISTRY_REQUIRED - set(row)
        assert not missing, f"{row.get('source_key')}: missing {sorted(missing)}"
        assert row["access_mode"] in ACCESS_MODES, row["source_key"]
        assert row["verification_status"] in VERIFICATION_STATUSES, row["source_key"]
        assert _dated(row["last_verified_at"]), row["source_key"]
        if row["verification_status"] == "verified":
            example = row["inspected_example"]
            assert example.get("url") and _dated(example.get("retrieved_at")), row["source_key"]
            assert example.get("method") in FETCH_METHODS, row["source_key"]


def test_organization_seed_nodes_and_edges_carry_evidence() -> None:
    graph = _load("organization_seed.json")
    ids = [node["id"] for node in graph["nodes"]]
    assert len(ids) == len(set(ids)), "duplicate node id"
    for node in graph["nodes"]:
        assert node.get("type") and node.get("name"), node["id"]
        assert _has_evidence(node.get("evidence")), f"{node['id']} lacks dated evidence"
        if node.get("valid_from") and node.get("valid_to"):
            assert node["valid_from"] <= node["valid_to"], node["id"]
    for edge in graph["edges"]:
        assert edge["from"] in ids and edge["to"] in ids, f"dangling edge {edge}"
        assert edge.get("type"), edge
        assert _has_evidence(edge.get("evidence")), f"edge {edge['from']}->{edge['to']} lacks evidence"
        if edge.get("valid_from") and edge.get("valid_to"):
            assert edge["valid_from"] <= edge["valid_to"], edge


def test_attribution_examples_are_classified_and_evidenced() -> None:
    examples = _load("attribution_examples.json")
    ids = [ex["id"] for ex in examples]
    assert len(ids) == len(set(ids)), "duplicate example id"
    for ex in examples:
        assert ex.get("identifier"), ex["id"]
        assert ex["evidence_class"] in EVIDENCE_CLASSES, ex["id"]
        assert "contracting_office" in ex and "funding_organization" in ex, ex["id"]
        assert isinstance(ex.get("program_offices"), list), ex["id"]
        assert _has_evidence(ex.get("evidence")), f"{ex['id']} lacks dated evidence with a source URL"
        if ex["evidence_class"] == "directly_documented":
            assert ex["program_offices"], f"{ex['id']} documented but names no office"
            assert any(e.get("passage") for e in ex["evidence"]), f"{ex['id']} has no quoted passage"
        if ex["evidence_class"] in ("inferred", "ambiguous"):
            assert ex.get("counterevidence") is not None, f"{ex['id']} must state counterevidence or 'none'"
        if ex["evidence_class"] == "unresolved":
            assert ex.get("why_unresolved"), ex["id"]


def test_backtests_never_use_evidence_after_the_cutoff() -> None:
    tests = _load("backtests.json")
    for bt in tests:
        cutoff = bt["cutoff_date"]
        assert _dated(cutoff), bt["id"]
        assert bt["actual_event"]["date"] > cutoff, f"{bt['id']} cutoff is not before the event"
        assert bt.get("evidence"), f"{bt['id']} has no pre-cutoff evidence"
        for item in bt["evidence"]:
            assert _dated(item.get("available_by")), f"{bt['id']} evidence lacks available_by"
            assert item["available_by"] <= cutoff, f"{bt['id']} uses evidence dated after cutoff"
            assert item.get("source_url"), bt["id"]


def test_documents_manifest_rows_are_hashed_and_dated() -> None:
    path = RESEARCH / "documents_manifest.jsonl"
    if not path.exists():
        pytest.skip("documents_manifest.jsonl not written yet")
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        assert row.get("url") and _dated(row.get("retrieved_at")), row
        assert row.get("method") in FETCH_METHODS, row
        if row.get("status") == 200:
            assert SHA256_RE.match(row.get("sha256") or ""), row
        else:
            assert row.get("error") or row.get("status"), row


def test_manual_requests_say_why() -> None:
    rows = _load("manual_pdf_requests.json")
    for row in rows:
        assert row.get("url") and row.get("reason"), row


def test_every_cited_evidence_url_has_a_fetched_manifest_row() -> None:
    path = RESEARCH / "documents_manifest.jsonl"
    if not path.exists():
        pytest.skip("documents_manifest.jsonl not written yet")
    fetched = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("status") == 200 and row.get("sha256") and row.get("content_status") != "rejected_stub":
            fetched.add(row["url"].replace("%5B", "[").replace("%5D", "]"))
    cited = set()
    for name in ("attribution_examples.json", "backtests.json", "organization_seed.json"):
        p = RESEARCH / name
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        items = data["nodes"] + data["edges"] if isinstance(data, dict) else data
        for item in items:
            for e in item.get("evidence", []):
                cited.add(e["source_url"])
            for key in ("actual_event", "post_cutoff_check"):
                if key in item:
                    cited.add(item[key]["source_url"])
    missing = sorted(u for u in cited if u.replace("%5B", "[").replace("%5D", "]") not in fetched)
    assert not missing, f"cited evidence without a fetched manifest row: {missing[:5]}"


def test_code_families_compile_and_carry_examples() -> None:
    data = _load("org_code_families.json")
    seen = set()
    for family in data["families"]:
        assert family["family"] not in seen, f"duplicate family {family['family']}"
        seen.add(family["family"])
        re.compile(family["pattern"])
        for key in ("org_type", "era", "parent_hint", "where_seen", "normalize"):
            assert family.get(key), f"{family['family']} lacks {key}"
        for example in family.get("examples", []):
            assert re.search(family["pattern"], example), f"{family['family']}: example {example!r} does not match its own pattern"


def test_contact_candidates_are_public_sourced_and_dated() -> None:
    rows = _load("contact_candidates.json")
    for row in rows:
        assert row.get("office") and row.get("role_type"), row
        assert row.get("name") or row.get("channel"), row
        assert row.get("source_url") and _dated(row.get("observed_at")), f"contact without a dated public source: {row.get('name') or row.get('channel')}"
        assert row.get("confidence") in {"high", "medium", "low"}, row
        assert row.get("basis"), row
