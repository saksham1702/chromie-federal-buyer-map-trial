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
from agency import KEY  # noqa: E402
from coverage import MATRIX, REASONS, STATUS, problems, registry, status  # noqa: E402

pytestmark = pytest.mark.skipif(not (MATRIX.exists() and STATUS.exists()), reason="coverage not built")
STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}")
# Pages fetched once by hand or by a probe from hosts no registry row owns yet; a new host here fails until it is
# registered or added on purpose. The ledger is shared by every agency layer, so the set holds for each profile;
# a host another layer's registry owns is that layer's document and is not listed (coverage.other_agency_hosts).
# NIWC sites: not_started in the grid; eventscribe: a WEST 2026 agenda page fetched during
# the conference sweep that no event cites, so no source claims it
KNOWN_UNREGISTERED = {"www.niwcatlantic.navy.mil", "www.niwcpacific.navy.mil", "westconference2026.eventscribe.net"}
# Onboarding-route pages (SBA, GSA, NASA, NSA, NOAA, acquisition.gov, the APEX site) fetched for
# research/memory/onboarding_routes.json on 2026-09-24; they document how a company enters federal selling, not a
# source of the Navy layer, so they are listed here rather than registered (DECISIONS.md, 2026-09-24)
KNOWN_UNREGISTERED |= {"www.sba.gov", "dsbs.sba.gov", "www.gsa.gov", "www.nasa.gov", "www.nsa.gov", "research.noaa.gov",
                       "www.acquisition.gov", "www.apexaccelerators.us"}
# DARPA's pages and the Senate committee sites were fetched on 2026-09-24 for the Navy-versus-DARPA comparison
# (research/docs/19_navy_versus_darpa.md) and belong to the DARPA layer's registry (research/agencies/darpa/sources).
# The sources each layer must have collected from before its status is read as live.
LIVE = {"navy": {"sam_gov_site_api", "fpds_atom_feed", "navwar_lrae_annex25", "don_budget_justification_books", "oversight_gov_reports"},
        "darpa": {"sam_gov_site_api", "fpds_atom_feed", "darpa_site", "darpa_staff_listing", "dod_comptroller_budget_materials",
                  "oversight_gov_reports", "federal_register", "sbir_sttr_topics"}}


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
    assert LIVE[KEY] <= live


def test_unregistered_hosts_are_the_known_ones():
    saved = json.loads(STATUS.read_text(encoding="utf-8"))
    assert set(saved["unregistered_hosts"]) <= KNOWN_UNREGISTERED, saved["unregistered_hosts"]


def test_saved_status_rebuilds_from_the_files_alone():
    assert json.loads(STATUS.read_text(encoding="utf-8")) == json.loads(json.dumps(status()))
