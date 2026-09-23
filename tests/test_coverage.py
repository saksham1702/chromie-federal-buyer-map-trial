"""Coverage matrix and source status: every command x family cell names a registered
source that has collected something or states why none does; the status names, per registered source, what was
last collected and when; a fetched host the registry does not know is listed, not hidden."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
from coverage import MATRIX, REASONS, STATUS, problems, registry, status  # noqa: E402

pytestmark = pytest.mark.skipif(not (MATRIX.exists() and STATUS.exists()), reason="coverage not built")
STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}")
# Pages fetched once by hand or by a probe from hosts no registry row owns yet; a new host here fails until it is
# registered or added on purpose.
# NIWC sites: not_started in the grid; Senate: refuses this address; eventscribe: a WEST 2026 agenda page fetched during
# the conference sweep that no event cites, so no source claims it
KNOWN_UNREGISTERED = {"www.niwcatlantic.navy.mil", "www.niwcpacific.navy.mil", "www.armed-services.senate.gov",
                      "westconference2026.eventscribe.net"}


def test_every_cell_is_covered_or_explained():
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    assert problems(matrix, status(), registry()) == []
    assert len(matrix["cells"]) == len(matrix["organizations"]) * len(matrix["families"])
    assert all(c.get("reason") in REASONS for c in matrix["cells"] if not c.get("sources"))


def test_status_covers_every_registered_source_with_dated_last_seen():
    saved = json.loads(STATUS.read_text(encoding="utf-8"))
    assert set(saved["sources"]) == set(registry())
    for key, s in saved["sources"].items():
        assert set(s) == {"events", "newest_event", "documents", "last_seen", "last_hash", "hosts"}, key
        assert (s["documents"] == 0) == (s["last_seen"] == "") == (s["last_hash"] == ""), key
        if s["documents"]:
            assert STAMP.match(s["last_seen"]) and len(s["last_hash"]) == 64, key
        if s["events"]:
            assert STAMP.match(s["newest_event"]), key
    live = {k for k, s in saved["sources"].items() if s["events"] or s["documents"]}
    assert {"sam_gov_site_api", "fpds_atom_feed", "navwar_lrae_annex25", "don_budget_justification_books", "oversight_gov_reports"} <= live


def test_unregistered_hosts_are_the_known_ones():
    saved = json.loads(STATUS.read_text(encoding="utf-8"))
    assert set(saved["unregistered_hosts"]) <= KNOWN_UNREGISTERED, saved["unregistered_hosts"]


def test_saved_status_rebuilds_from_the_files_alone():
    assert json.loads(STATUS.read_text(encoding="utf-8")) == json.loads(json.dumps(status()))
