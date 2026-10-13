"""Course lesson resolution and reader redirects.

Two defects these hold shut:
  * a deep dive "dd-01" opened lesson 01's text, because the lesson file was
    found by the trailing number of the id alone;
  * /course/<slug> for a course published as a mounted site rendered an empty
    reader instead of the site its Open button launches.
"""
import json
import sys
from pathlib import Path

import pytest

_APP_PY = Path(__file__).parent.parent.parent / "system" / "app-py"
if str(_APP_PY) not in sys.path:
    sys.path.insert(0, str(_APP_PY))

learning = pytest.importorskip("routers.learning")


@pytest.fixture()
def courses(tmp_path, monkeypatch):
    root = tmp_path / "courses"
    c = root / "demo" / "lessons"
    c.mkdir(parents=True)
    (root / "demo" / "lessons.json").write_text(json.dumps({"lessons": [
        {"id": "lesson-01", "title": "One"},
        {"id": "dd-01", "title": "Deep one", "section": "Deep dives"},
        {"id": "x", "title": "Named", "file": "zz-named.md"},
    ]}), encoding="utf-8")
    for name in ("01-one.md", "dd-01-deep.md", "zz-named.md"):
        (c / name).write_text(f"# {name}\n", encoding="utf-8")
    monkeypatch.setattr(learning, "_COURSES_DIR", root)
    return c


def test_numbered_lesson_still_resolves(courses):
    assert learning._lesson_path("demo", "lesson-01").name == "01-one.md"


def test_deep_dive_does_not_open_the_lesson_with_its_number(courses):
    assert learning._lesson_path("demo", "dd-01").name == "dd-01-deep.md"


def test_explicit_file_wins(courses):
    assert learning._lesson_path("demo", "x").name == "zz-named.md"


def test_mounted_site_redirects_from_reader(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    monkeypatch.setattr(learning, "_external_apps", lambda: {})
    monkeypatch.setattr(learning, "_mounted_sites", lambda: {"site": "/coursesite/site/"})
    app = FastAPI()
    app.include_router(learning.router)
    r = TestClient(app).get("/course/site?lesson=a", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/coursesite/site/"
