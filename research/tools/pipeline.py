#!/usr/bin/env python3
"""Run the agency pipeline end to end: collect, model, load, read back.

    python research/tools/pipeline.py [--db navy_proof_e] [--collect] [--from STAGE] [--only STAGE]
    python research/tools/pipeline.py --list
    python research/tools/pipeline.py --selfcheck

Every stage is one of the tools beside this file, run in the order the records depend on each
other: the sources are collected first, then modelled into the datapack and the news records,
then emitted as rows, then loaded, then read back by the checks. Nothing here holds agency
knowledge; the agency is in `research/memory/organization_seed.json`, the datapack and the saved
documents, so the same order runs for another agency once those exist
(research/docs/14_reusing_this_for_another_agency.md).

`--collect` adds the two network stages, which are skipped by default so a rebuild is
deterministic and offline. The database stage drops and recreates the named database, so it
never edits one that other work is reading.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
BUILD = ROOT / "build"
PY = sys.executable
DSN_HOST = os.environ.get("PGHOST", "127.0.0.1")
DSN_PORT = os.environ.get("PGPORT", "54322")
DSN_USER = os.environ.get("PGUSER", "postgres")

# name, what it does, whether it needs the network, and how it is run. A stage is a command, not
# a function, so each one is also runnable on its own and prints the same output either way.
STAGES = [
    ("watch", "poll the feeds for articles not yet saved", True,
     [PY, str(TOOLS / "news.py"), "watch", "--fetch"]),
    ("sweep", "one discovery query per office, and take what is new", True,
     [PY, str(TOOLS / "news.py"), "sweep", "--fetch"]),
    ("audits", "poll oversight.gov and the GAO feed for reports not yet saved", True,
     [PY, str(TOOLS / "oversight.py"), "watch", "--fetch"]),
    ("podium", "poll the speech archive and the House hearing feeds for documents not yet saved", True,
     [PY, str(TOOLS / "remarks.py"), "watch", "--fetch"]),
    ("contracts", "sweep FPDS for the base awards each contracting office signed, page by page", True,
     [PY, str(TOOLS / "fpds_sweep.py"), "sweep", "--fetch"]),
    ("solicitations", "sweep SAM.gov for every notice each contracting office posted since FY22 and harvest the new ones", True,
     [PY, str(TOOLS / "sam_notices.py"), "sweep"]),
    ("topics", "sweep the DoD SBIR/STTR portal newest first for every topic since FY2020 and keep the Navy details", True,
     [PY, str(TOOLS / "sbir.py"), "sweep", "--fetch"]),
    ("changes", "follow the FPDS history of every swept award running or ended within a year, for extensions, options and terminations", True,
     [PY, str(TOOLS / "fpds_sweep.py"), "histories", "--fetch"]),
    ("dockets", "take GAO's docket of Navy bid protests and the case page of every new or still-open case", True,
     [PY, str(TOOLS / "protests.py"), "watch", "--fetch"]),
    ("reports", "list the committee reports on govinfo and take the NDAA and defense appropriations reports not yet saved", True,
     [PY, str(TOOLS / "congress.py"), "sweep", "--fetch"]),
    ("register", "take the Department of the Navy's Federal Register documents", True,
     [PY, str(TOOLS / "fedreg.py"), "sweep", "--fetch"]),
    ("outreach", "take the Department of War's directory of small business offices and each office page it links to not yet saved", True,
     [PY, str(TOOLS / "small_business.py"), "collect"]),
    ("memory", "read the activity-wide forecast releases into the organization memory", False,
     [PY, str(TOOLS / "org_memory_lrae.py"), "build"]),
    ("datapack", "read the forecast releases into the datapack and compare them", False,
     [PY, str(TOOLS / "lrae_package.py"), "build"]),
    ("oversight", "read every saved oversight report into dated findings (cassettes replay; a new report is one agent call)", False,
     [PY, str(TOOLS / "oversight.py"), "extract"]),
    ("remarks", "read every saved speech, statement and conference page into dated events (cassettes replay)", False,
     [PY, str(TOOLS / "remarks.py"), "extract"]),
    ("budget", "read every saved budget justification book into P-1 line items with their fiscal-year amounts", False,
     [PY, str(TOOLS / "budget.py"), "extract"]),
    ("news", "model every saved article as dated observations", False,
     [PY, str(TOOLS / "news.py"), "build"]),
    ("people", "merge every point of contact, forecast POC, speaker and witness the saved sources name into people.json", False,
     [PY, str(TOOLS / "people.py"), "build"]),
    ("small_business", "the small business office of the department and each command from the saved directory and office pages, "
                       "compared with the saved file", False,
     [PY, str(TOOLS / "small_business.py"), "build", "--check"]),
    ("programs", "model every saved Navy SBIR/STTR topic as a dated programs event with the office it names", False,
     [PY, str(TOOLS / "sbir.py"), "build"]),
    ("protests", "read every saved GAO case page into a protest dated the day it was filed", False,
     [PY, str(TOOLS / "protests.py"), "build"]),
    ("directives", "read every saved committee report into the Navy directives it states", False,
     [PY, str(TOOLS / "congress.py"), "build"]),
    ("federal", "read the saved Federal Register pages into dated documents, typed where the text says what happened", False,
     [PY, str(TOOLS / "fedreg.py"), "build"]),
    ("schema", "write the loaded-table subset of the production schema", False,
     [PY, str(TOOLS / "schema_subset.py"), str(BUILD / "schema.sql")]),
    ("layers", "emit the rows: needs, assertions, evidence, organizations, brain items", False,
     [PY, str(TOOLS / "agency_layers_sql.py")]),
    ("database", "create the database and load the schema and the rows", False, None),
    ("graph", "export the organization graph as the program-office resolver reads it", False, None),
    ("revisions", "the forecast-revision alert: every forecast line whose award window or value moved between releases, into build/", False, None),
    ("backtest", "replay the outcome labels and compute the back-test from the frozen corpus into build/", False,
     [PY, str(TOOLS / "backtest.py"), "check"]),
    ("offices", "read every notice filed at a contracting office that no record places against the office pages (cassettes replay; "
                "a new notice is one model call), compared with the saved file", False,
     [PY, str(TOOLS / "office_wiki.py"), "build", "--check"]),
    ("pulse", "score every cell as of the corpus end, list the week's changes and the actions, and compare with the saved pulse", False,
     [PY, str(TOOLS / "pulse.py"), "check"]),
    ("baselines", "the bar against the dumb baselines, recall by period and the family combinations, into build/", False,
     [PY, str(TOOLS / "baselines.py"), "run"]),
    ("dna", "Buying DNA per contracting office, program office and top cell from the saved FPDS pages, compared with the saved file", False,
     [PY, str(TOOLS / "buying_dna.py"), "build", "--check"]),
    ("vendors", "vendors resolved by UEI from the saved FPDS pages, every spelling and the parent entity, compared with the saved file", False,
     [PY, str(TOOLS / "vendors.py"), "build", "--check"]),
    ("coverage", "which registered source covers each command and family, and what each source last collected, compared with the saved file", False,
     [PY, str(TOOLS / "coverage.py"), "status", "--check"]),
    ("checks", "every tool's selfcheck and the test suite", False, None),
]
NETWORK = {name for name, _, network, _ in STAGES if network}


def refreshed(db: str) -> dict[str, list[list[str]]]:
    """The stages that compare with a saved file, run instead to rewrite it from what was just collected: the corpus is
    frozen from the new database, every outcome is labelled (one labelled before replays its cassette), and the
    results, pulse, books and status follow."""
    tool = lambda name, *rest: [PY, str(TOOLS / name), *rest]
    return {"backtest": [tool("backtest.py", "freeze", "--db", db), tool("backtest.py", "label"), tool("backtest.py", "run")],
            "offices": [tool("office_wiki.py", "build")], "small_business": [tool("small_business.py", "build")], "pulse": [tool("pulse.py", "build")], "dna": [tool("buying_dna.py", "build")],
            "vendors": [tool("vendors.py", "build")], "coverage": [tool("coverage.py", "status")]}


def run(command: list[str], out: Path | None = None, env: dict | None = None) -> int:
    """Run one command, streaming to the terminal or into a file, and report the seconds it took."""
    started = time.time()
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("wb") as handle:
            done = subprocess.run(command, cwd=ROOT, stdout=handle,
                                  stderr=subprocess.PIPE, env=env or os.environ.copy())
        if done.stderr:
            (out.parent / (out.stem + ".skipped.txt")).write_bytes(done.stderr)
    else:
        done = subprocess.run(command, cwd=ROOT, env=env or os.environ.copy())
    print(f"    {time.time() - started:5.1f}s  exit {done.returncode}")
    return done.returncode


def psql_env() -> dict:
    env = os.environ.copy()
    env.setdefault("PGPASSWORD", "postgres")
    return env


def load_database(name: str) -> int:
    """Build the database from nothing: a load that cannot half-apply over an older one."""
    base = ["-h", DSN_HOST, "-p", DSN_PORT, "-U", DSN_USER]
    env = psql_env()
    for command in ([["dropdb", "--if-exists", *base, name], ["createdb", *base, name]]):
        if run(command, env=env):
            return 1
    for sql in (BUILD / "schema.sql", BUILD / "layers.sql"):
        if not sql.exists():
            print(f"    {sql.relative_to(ROOT)} is missing; run the schema and layers stages first")
            return 1
        if run(["psql", *base, "-d", name, "-v", "ON_ERROR_STOP=1", "-q", "-f", str(sql)], env=env):
            return 1
    return 0


def checks(db: str) -> int:
    """Read the tools back: each one's selfcheck, then the suite, told which database was built."""
    failures = 0
    for tool in sorted(TOOLS.glob("*.py")):
        # A tool without a selfcheck is covered by the suite, and "._name.py" is the resource fork
        # an exFAT volume leaves beside a file, not a module.
        if tool.name == "pipeline.py" or tool.name.startswith("._"):
            continue
        if "--selfcheck" not in tool.read_text(encoding="utf-8", errors="ignore"):
            print(f"    {tool.name}: no selfcheck, covered by the suite")
            continue
        probe = subprocess.run([PY, str(tool), "--selfcheck"], cwd=ROOT,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if "selfcheck ok" in probe.stdout:
            print(f"    {tool.name}: ok")
        else:
            failures += 1
            print(f"    {tool.name}: FAILED\n{probe.stdout[-800:]}")
    if run([PY, "-m", "pytest", "-q", "tests"], env={**psql_env(), "NAVY_DB": db}):
        failures += 1
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="pipeline")
    parser.add_argument("--db", default="navy_proof_e", help="the database to build from nothing")
    parser.add_argument("--collect", action="store_true", help="include the network stages")
    parser.add_argument("--refresh", action="store_true", help="rewrite the saved results from the new build instead of comparing with them")
    parser.add_argument("--from", dest="start", help="start at this stage")
    parser.add_argument("--only", help="run this stage alone")
    parser.add_argument("--list", action="store_true", help="print the stages and stop")
    args = parser.parse_args(argv)

    names = [name for name, _, _, _ in STAGES]
    if args.list:
        for name, what, network, _ in STAGES:
            print(f"  {name:9} {'(network)' if network else '         '}  {what}")
        return 0
    wanted = names
    if args.only:
        wanted = [args.only]
    elif args.start:
        wanted = names[names.index(args.start):]
    if not args.collect and not args.only:
        wanted = [n for n in wanted if n not in NETWORK]

    BUILD.mkdir(parents=True, exist_ok=True)
    rewrite, missed = refreshed(args.db) if args.refresh else {}, []
    for name, what, _, command in STAGES:
        if name not in wanted:
            continue
        print(f"\n== {name}: {what}")
        if name in rewrite:
            code = next((c for c in (run(step) for step in rewrite[name]) if c), 0)
        elif name == "database":
            code = load_database(args.db)
        elif name == "graph":
            code = run([PY, str(TOOLS / "graph_export.py"), "--db", args.db], out=BUILD / "program_office_graph.json")
        elif name == "revisions":
            dsn = f"postgresql://{DSN_USER}:postgres@{DSN_HOST}:{DSN_PORT}/{args.db}"
            code = run([PY, str(TOOLS / "monitor_forecast_revision.py"), "--dsn", dsn], out=BUILD / "forecast_revisions.txt")
        elif name == "checks":
            code = checks(args.db)
        elif name == "layers":
            code = run(command, out=BUILD / "layers.sql")
        else:
            code = run(command)
        if code and name in NETWORK:
            # A source that did not answer leaves what it saved before; the build goes on without its new pages.
            print(f"\n{name} did not finish collecting; building from what is saved")
            missed.append(name)
        elif code:
            print(f"\n{name} failed; the pipeline stops here so the next stage does not run on half a build")
            return code
    print(f"\ndone: {', '.join(n for n in names if n in wanted)}" + (f"; collection incomplete: {', '.join(missed)}" if missed else ""))
    return 1 if missed else 0


def selfcheck() -> int:
    names = [name for name, _, _, _ in STAGES]
    assert names.index("datapack") < names.index("layers") < names.index("database") < names.index("checks"), \
        "the rows are emitted before they are loaded, and read back after"
    assert names.index("news") < names.index("layers"), "articles are modelled before they are emitted"
    assert names.index("database") < names.index("revisions"), "the revision alert reads the loaded database"
    assert names.index("backtest") < names.index("offices"), "the office reads are made over the frozen corpus"
    assert NETWORK == {"watch", "sweep", "audits", "podium", "contracts", "solicitations", "topics", "changes", "dockets", "reports",
                       "register", "outreach"}, "only collection touches the network"
    assert set(refreshed("x")) <= set(names), "every refreshed stage is a stage"
    assert max(names.index(n) for n in NETWORK) < names.index("memory"), "collection runs before any build stage"
    assert all(c is None or c[0] == PY for _, _, _, c in STAGES), "every stage runs this interpreter"
    print("pipeline selfcheck ok")
    return 0


if __name__ == "__main__":
    sys.exit(selfcheck() if "--selfcheck" in sys.argv[1:] else main(sys.argv[1:]))
