"""
Every dashboard panel, on the database a fresh install actually gets.

A query that names a missing table or column does not fail: db.py degrades it to
an empty default and logs "query degraded to its default". On a long-running
database those tables and columns had been added over months by whichever module
first wrote to them, so nothing showed; on a brand-new install 32 panel queries
came back empty — a Work board whose categories could not be saved among them.

The route test next to this one builds its own hand-written schema, and that
schema had `tasks.id` and `brainstorm_sessions.id`, which the real one never had.
It passed against the very bugs it should have caught. This test uses
system/installer/schema.sql — the file the installers use — and nothing else.

It runs in a fresh interpreter. Several routers add columns when they are
imported, and inside a test session they were imported earlier against another
test's database — so in-process, the result depended on test order. A clean
process is also exactly what a real start-up is. Outbound network is pointed at
a dead proxy: rendering Today otherwise asks the Anthropic API for a brief.
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP_PY = ROOT / "system" / "app-py"
SCHEMA = ROOT / "system" / "installer" / "schema.sql"

pytest.importorskip("fastapi")


def _columns(db: Path) -> dict[str, set[str]]:
    con = sqlite3.connect(db)
    out = {}
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' "
                            "AND sql NOT LIKE '%VIRTUAL%'"):
        out[t] = {r[1] for r in con.execute(f'PRAGMA table_info("{t}")')}
    con.close()
    return out


def _crawl(db: str) -> dict:
    """Runs in the child process: import the app, open every tab and panel."""
    import logging

    sys.path.insert(0, str(APP_PY))
    degraded: set[str] = set()

    class _Catch(logging.Handler):
        def emit(self, rec):
            msg = rec.getMessage()
            if "degraded to its default" in msg and "locked" not in msg:
                degraded.add(msg.split(" | SQL")[0])

    logging.getLogger("metis.db").addHandler(_Catch(level=logging.ERROR))

    from fastapi.testclient import TestClient
    import main
    import routers.today as today
    today._get_api_key = lambda: ""  # never generate a brief with a real key

    # No `with`: the lifespan (scheduler, feed scans) stays off.
    client = TestClient(main.app)
    root = client.get("/")
    nav = re.findall(r'(?:href|hx-get)="(/[^"#?{]*)"', root.text)
    paths, seen = [], set()
    for tab in sorted({p for p in nav if not p.startswith(("/static", "/coursesite"))}):
        for p in [tab, *re.findall(r'hx-get="(/[^"{]*)"', client.get(tab).text)]:
            if p not in seen:
                seen.add(p)
                paths.append(p)
    errors = []
    for p in paths:
        r = client.get(p)
        if r.status_code >= 500:
            errors.append(f"{r.status_code} {p}")
    return {"root": root.status_code, "paths": len(paths),
            "errors": errors, "degraded": sorted(degraded)}


@pytest.fixture(scope="module")
def crawl(tmp_path_factory):
    db = tmp_path_factory.mktemp("fresh") / "metis.sqlite"
    con = sqlite3.connect(db)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.close()
    declared = _columns(db)

    dead = "http://127.0.0.1:9"
    env = {**os.environ, "METIS_DB": str(db), "METIS_RC_ROOT": str(ROOT),
           "HF_HUB_OFFLINE": "1", "ANTHROPIC_API_KEY": "",
           "HTTP_PROXY": dead, "HTTPS_PROXY": dead, "http_proxy": dead,
           "https_proxy": dead, "NO_PROXY": "127.0.0.1,localhost,testserver",
           "no_proxy": "127.0.0.1,localhost,testserver"}
    code = (f"import json, sys; sys.path.insert(0, {str(Path(__file__).parent)!r}); "
            f"import test_fresh_install_panels as t; "
            f"print('CRAWL=' + json.dumps(t._crawl({str(db)!r})))")
    proc = subprocess.run([sys.executable, "-c", code], cwd=APP_PY, env=env,
                          capture_output=True, text=True, timeout=600)
    line = next((ln for ln in proc.stdout.splitlines() if ln.startswith("CRAWL=")), None)
    assert line, f"crawl did not finish:\n{proc.stdout[-2000:]}\n{proc.stderr[-3000:]}"
    result = json.loads(line[len("CRAWL="):])
    result["declared"] = declared
    result["after"] = _columns(db)
    return result


def test_every_panel_renders_on_a_fresh_database(crawl):
    assert crawl["root"] == 200
    # A crawl that found nothing proves nothing.
    assert crawl["paths"] > 100, f"only {crawl['paths']} paths found — the crawl is broken"
    assert not crawl["errors"], "server errors on a fresh install:\n" + "\n".join(crawl["errors"])


def test_no_panel_query_degrades_on_a_fresh_database(crawl):
    assert not crawl["degraded"], (
        "queries that silently return an empty default on a fresh install — add "
        "the table/column to system/installer/schema.sql, or fix the query:\n  "
        + "\n  ".join(crawl["degraded"])
    )


def test_schema_sql_declares_what_the_dashboard_adds_at_start(crawl):
    """A column only an import-time ALTER creates exists on a fresh install by luck
    of start-up order, and on no database the MCP server creates first."""
    added = sorted(f"{t}.{c}"
                   for t, cols in crawl["after"].items()
                   for c in cols - crawl["declared"].get(t, set()))
    assert not added, (
        "columns or tables the dashboard creates at start-up that schema.sql does "
        "not declare:\n  " + "\n  ".join(added)
    )
