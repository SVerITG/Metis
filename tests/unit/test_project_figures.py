"""A figure saved from a chat lands under its project, where the dashboard lists
it; client-style paths (relative, or a Windows drive path) resolve inside Metis."""
import asyncio
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture()
def root(tmp_path, monkeypatch):
    from metis_mcp.config import paths
    db = tmp_path / "metis.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE projects (project_id TEXT PRIMARY KEY, title TEXT)")
    con.execute("INSERT INTO projects VALUES ('demo-study', 'Demo study')")
    con.commit()
    con.close()
    monkeypatch.setattr(paths, "root", tmp_path)
    monkeypatch.setattr(paths, "db", db)
    return tmp_path


def test_figure_is_saved_under_its_project(root):
    from metis_mcp.tools.authoring import save_project_figure
    out = asyncio.run(save_project_figure(
        project_id="demo-study", title="Attendance by zone",
        html="<svg></svg>", caption="Screened / census"))[0].text
    f = root / "outputs" / "figures" / "demo-study" / "attendance-by-zone.html"
    assert f.is_file() and "<svg></svg>" in f.read_text()
    assert f.with_suffix(".json").is_file()
    assert "Figures" in out


def test_title_is_escaped_when_a_fragment_is_wrapped(root):
    from metis_mcp.tools.authoring import save_project_figure
    asyncio.run(save_project_figure(project_id="demo-study", title="<b>x</b>", html="<p>y</p>"))
    text = (root / "outputs" / "figures" / "demo-study" / "b-x-b.html").read_text()
    assert "<title>&lt;b&gt;x&lt;/b&gt;</title>" in text


def test_unknown_project_is_refused(root):
    from metis_mcp.tools.authoring import save_project_figure
    out = asyncio.run(save_project_figure(project_id="nope", title="t", html="<p/>"))[0].text
    assert "No project" in out
    assert not (root / "outputs" / "figures" / "nope").exists()


def test_relative_path_means_inside_metis(root):
    from metis_mcp.tools.files import resolve_user_path
    assert resolve_user_path("inputs/a.csv") == root / "inputs" / "a.csv"


@pytest.mark.skipif(not Path("/mnt").is_dir(), reason="WSL-style mount only")
def test_windows_drive_path_is_translated(root):
    from metis_mcp.tools.files import resolve_user_path
    assert str(resolve_user_path(r"C:\Users\x\a.csv")) == "/mnt/c/Users/x/a.csv"


def test_escaping_relative_path_is_still_refused(root):
    from metis_mcp.tools.files import _path_refusal, resolve_user_path
    assert _path_refusal(resolve_user_path("../../../../etc/passwd"))
