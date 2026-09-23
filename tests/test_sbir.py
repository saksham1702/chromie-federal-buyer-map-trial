"""Programs family: every saved Navy SBIR/STTR topic is a dated event under an office or command
the organization memory knows, rebuilt from the saved portal pages alone, and loaded as the programs family.

NAVY_DB names the loaded database for the last test; without it that test skips."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research" / "tools"))
from sbir import COMMANDS, DEPARTMENT, OUT, PROVIDER, SINCE, detail_url  # noqa: E402

pytestmark = pytest.mark.skipif(not OUT.exists(), reason="sbir_topics.json not built")
DB = os.environ.get("NAVY_DB")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def one(sql: str) -> str:
    dsn = (f"postgresql://{os.environ.get('PGUSER', 'postgres')}:{os.environ.get('PGPASSWORD', 'postgres')}"
           f"@{os.environ.get('PGHOST', '127.0.0.1')}:{os.environ.get('PGPORT', '54322')}/{DB}")
    return subprocess.run(["psql", dsn, "-At", "-c", sql], capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture(scope="module")
def topics() -> list[dict]:
    return json.loads(OUT.read_text(encoding="utf-8"))["rows"]


def test_topics_are_navy_dated_and_inside_the_window(topics):
    assert len(topics) >= 800
    for t in topics:
        assert t["component"] == "NAVY" and re.match(r"^(N|DON)", t["code"]), t["code"]
        assert DAY.match(t["pre_release"]) and t["pre_release"] >= SINCE[:4] and t["open"] >= SINCE, (t["code"], t["pre_release"], t["open"])
        assert t["pre_release"] <= t["open"] <= t["close"], t["code"]
        assert t["url"] == detail_url(t["topic_id"]) and t["org"] in set(COMMANDS.values()) | {DEPARTMENT}


def test_offices_named_are_in_the_organization_memory(topics):
    seed = {n["id"] for n in json.loads((ROOT / "research" / "memory" / "organization_seed.json").read_text(encoding="utf-8"))["nodes"]}
    named = [t for t in topics if t["offices"]]
    assert len(named) >= 30, len(named)
    assert all(o in seed for t in named for o in t["offices"])
    # a topic that names an office is filed under it, not the command, when the loader picks the organization
    assert any(t["command"] == "NAVWAR" and t["offices"] for t in named)


def test_every_topic_keeps_its_saved_detail(topics):
    detailed = [t for t in topics if t["path"]]
    assert len(detailed) >= 0.95 * len(topics), (len(detailed), len(topics))
    for t in detailed[:50]:
        assert (ROOT / t["path"]).exists() and len(t["sha256"]) == 64 and t["retrieved_at"]
        assert t["text"], t["code"]


@pytest.mark.skipif(not DB, reason="NAVY_DB names no loaded database")
def test_topics_load_as_programs_events(topics):
    loadable = [t for t in topics if t["pre_release"] and t["code"]]
    assert one(f"select count(*) from public.agency_brain_items where source_provider='{PROVIDER}'") == str(len(loadable))
    assert one(f"select count(*) from public.agency_brain_items where source_provider='{PROVIDER}' and (published_at is null or "
               "primary_organization_id is null or event_type <> 'sbir_topic' or section <> 'mission_priorities')") == "0"
    assert int(one(f"select count(distinct primary_organization_id) from public.agency_brain_items where source_provider='{PROVIDER}'")) >= 4
    assert one(f"select count(*) from public.gov_intelligence_evidence e join public.agency_brain_items i on i.id=e.brain_item_id "
               f"where i.source_provider='{PROVIDER}' and e.source_url like 'https://www.dodsbirsttr.mil/%'") == str(len(loadable))
