"""register_schedule.py: setup gives Claude Desktop the morning-briefing task.

The settings file belongs to Claude Desktop and holds the person's own tasks,
so what matters is what is NOT changed: other tasks, and a time the person
picked in Claude Desktop after setup.
"""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "register_schedule", ROOT / "system" / "install" / "register_schedule.py")
sched = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sched)


@pytest.fixture
def desktop(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    return tmp_path


def _signed_in(base: Path, tasks=None) -> Path:
    org = base / "Roaming" / "Claude" / "claude-code-sessions" / "acct" / "org"
    org.mkdir(parents=True)
    f = org / "scheduled-tasks.json"
    if tasks is not None:
        f.write_text(json.dumps({"scheduledTasks": tasks, "recordedSkips": {}}))
    return f


def test_not_signed_in_is_pending_and_writes_the_task_text(desktop):
    st, notes = sched.register(desktop / "Metis")
    assert st == "pending" and notes
    assert sched.skill_file().exists()
    assert "morning-briefing.md" in sched.skill_file().read_text()
    assert sched.status() == "pending"


def test_registers_beside_existing_tasks(desktop):
    other = {"id": "mine", "cronExpression": "0 9 * * *", "enabled": True}
    f = _signed_in(desktop, [other])
    st, _ = sched.register(desktop / "Metis", "07:30")
    data = json.loads(f.read_text())
    ids = [t["id"] for t in data["scheduledTasks"]]
    assert st == "registered" and ids == ["mine", sched.TASK_ID]
    entry = data["scheduledTasks"][1]
    assert entry["cronExpression"] == "30 7 * * 1-5"
    assert entry["cwd"] == str(desktop / "Metis")
    assert data["recordedSkips"] == {}
    assert sched.status() == "registered"


def test_reinstall_keeps_a_time_changed_in_desktop(desktop):
    f = _signed_in(desktop, [])
    sched.register(desktop / "Metis")
    data = json.loads(f.read_text())
    data["scheduledTasks"][0]["cronExpression"] = "15 10 * * 1-5"
    f.write_text(json.dumps(data))
    sched.register(desktop / "Metis2")
    entry = json.loads(f.read_text())["scheduledTasks"][0]
    assert entry["cronExpression"] == "15 10 * * 1-5"
    assert entry["cwd"] == str(desktop / "Metis2")
    assert len(json.loads(f.read_text())["scheduledTasks"]) == 1


def test_unreadable_file_is_left_alone(desktop):
    f = _signed_in(desktop)
    f.write_text("{not json")
    st, notes = sched.register(desktop / "Metis")
    assert st == "pending" and any("not valid JSON" in n for n in notes)
    assert f.read_text() == "{not json"


def test_remove_takes_out_only_its_own_task(desktop):
    f = _signed_in(desktop, [{"id": "mine"}])
    sched.register(desktop / "Metis")
    assert sched.remove() == 0
    assert [t["id"] for t in json.loads(f.read_text())["scheduledTasks"]] == ["mine"]
    assert not sched.skill_file().exists()
    assert sched.status() == "off"


def test_store_edition_folder_is_found(desktop):
    org = (desktop / "Local" / "Packages" / "Claude_abc" / "LocalCache" / "Roaming"
           / "Claude" / "claude-code-sessions" / "a" / "o")
    org.mkdir(parents=True)
    assert sched.register(desktop / "Metis")[0] == "registered"
    assert (org / "scheduled-tasks.json").exists()


def test_the_routine_the_task_points_at_ships():
    assert (ROOT / sched.ROUTINE).exists()
