"""
The sample workspace new users are offered — what it promises, held to it.

It used to promise more than it did: the installer's "load demo" ran a script
that was never published, the dashboard's button switched on a "DEMO MODE"
banner over an empty database and reported success, and "Exit demo" removed the
banner while every sample row stayed mixed into the person's real workspace.
Its sample news also put invented figures in real organisations' mouths, with
links to their real websites.
"""

import importlib.util
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "system" / "install" / "seed_mockup_demo.py"
SCHEMA = ROOT / "system" / "installer" / "schema.sql"


def _demo():
    spec = importlib.util.spec_from_file_location("seed_mockup_demo", SEED)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def fresh_db(tmp_path):
    db = tmp_path / "metis.sqlite"
    con = sqlite3.connect(db)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.close()
    return db


def _counts(db, tables):
    con = sqlite3.connect(db)
    out = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    con.close()
    return out


def test_exit_demo_leaves_nothing_behind(fresh_db, tmp_path):
    demo = _demo()
    manifest = tmp_path / ".demo-rows.json"
    before = _counts(fresh_db, demo.DEMO_TABLES)
    res = demo.load(fresh_db, manifest)
    assert res["ok"] and res["rows"] > 50, res
    during = _counts(fresh_db, demo.DEMO_TABLES)
    assert sum(during.values()) > sum(before.values())
    assert demo.unload(manifest)["removed"] == res["rows"]
    assert _counts(fresh_db, demo.DEMO_TABLES) == before
    assert not manifest.exists()


def test_demo_refuses_a_workspace_in_use(fresh_db, tmp_path):
    con = sqlite3.connect(fresh_db)
    con.execute("INSERT INTO tasks (task_id, title, status) VALUES ('t1', 'my real task', 'open')")
    con.commit()
    con.close()
    res = _demo().load(fresh_db, tmp_path / ".demo-rows.json")
    assert not res["ok"] and "already has your own content" in res["error"]
    assert _counts(fresh_db, ["tasks"])["tasks"] == 1


def test_sample_news_names_no_real_source():
    src = SEED.read_text(encoding="utf-8")
    block = src[src.index("    news = ["):src.index("    ]\n", src.index("    news = ["))]
    urls = re.findall(r'"source_url": "([^"]+)"', block)
    assert urls and all(u.startswith("https://example.org/") for u in urls), urls
    titles = re.findall(r'"title": "([^"]+)"', block)
    for t in titles:
        assert t.startswith("Sample"), f"a demo news item does not say it is a sample: {t}"
        assert not re.search(r"\b(WHO|World Bank|Gavi|Global Fund|Lancet|UNICEF)\b", t), t
    # And no link anywhere in the demo leads to a real person's or project's page.
    others = re.findall(r"https?://(?!example\.org)[^\s\"']+", src)
    assert all(".local" in u for u in others), others


def test_tour_page_renders_with_and_without_the_demo(tmp_path):
    pytest.importorskip("fastapi")
    db = tmp_path / "metis.sqlite"
    con = sqlite3.connect(db)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.close()
    code = (
        "import sys; sys.path.insert(0, '.');"
        "from fastapi.testclient import TestClient; import main;"
        "c = TestClient(main.app); r = c.get('/tour');"
        "print('STATUS', r.status_code); print('HAS_DESKTOP', 'Claude Desktop' in r.text);"
        "print('STOPS', r.text.count('OPEN '))"
    )
    env = {**os.environ, "METIS_DB": str(db), "METIS_RC_ROOT": str(ROOT), "HF_HUB_OFFLINE": "1"}
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT / "system" / "app-py",
                         env=env, capture_output=True, text=True, timeout=300).stdout
    assert "STATUS 200" in out, out[-1500:]
    assert "HAS_DESKTOP True" in out
    assert re.search(r"STOPS (\d+)", out) and int(re.search(r"STOPS (\d+)", out).group(1)) >= 8
