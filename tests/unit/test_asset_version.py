"""The cache-busting stamp, and why it must not be a number someone types.

Reported 2026-09-02: "every day I open Metis but there are still old Metis'
version open in my browsers."

`base.html` carried `styles.css?v=14` and `app.js?v=9m`, bumped by hand. A
number you have to remember to change is a number that does not change: every
edit shipped behind a stamp last touched weeks earlier, so a browser holding
`styles.css?v=14` went on serving it and the tab kept showing an old Metis no
matter how many times the dashboard restarted.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "system" / "app-py"
sys.path.insert(0, str(APP))


def test_no_template_hard_codes_an_asset_version():
    """The whole defect in one assertion."""
    offenders = []
    for tpl in (APP / "templates").rglob("*.html"):
        for m in re.finditer(r'(?:styles\.css|app\.js)\?v=([^"\'&]+)', tpl.read_text(encoding="utf-8")):
            if "asset_v" not in m.group(1):
                offenders.append(f"{tpl.relative_to(APP)}: ?v={m.group(1)}")
    assert not offenders, (
        "hand-typed asset versions — they will not be bumped, and a cached "
        f"browser will keep the old file forever: {offenders}"
    )


def test_the_stamp_follows_the_file_contents():
    """Content hash, not mtime: this repository syncs through OneDrive across
    two machines where mtimes are not trustworthy."""
    main = pytest.importorskip("main")
    css = APP / "static" / "styles.css"
    before = main._asset_version()
    original = css.read_bytes()
    try:
        css.write_bytes(original + b"\n/* test probe */\n")
        after = main._asset_version()
    finally:
        css.write_bytes(original)
    assert before != after, "the stamp did not change when an asset did"
    assert main._asset_version() == before, "the stamp is not stable for identical content"


def test_the_stamp_is_a_shared_jinja_global():
    """There are seventeen Jinja environments. A global that is only attached to
    the ones that happen to exist at import time is a global that is missing
    from whichever template is rendered by a router imported lazily."""
    main = pytest.importorskip("main")
    assert "asset_v" in main._SHARED_GLOBALS


def test_a_stale_tab_can_tell_that_it_is_stale():
    """The page-side half. Without these three the curtain never appears: the
    tab has no way to learn the dashboard restarted underneath it."""
    js = (APP / "static" / "app.js").read_text(encoding="utf-8")
    for needle, why in [
        ("BroadcastChannel", "no cross-tab claim, so two tabs both stay live"),
        ("/api/build", "no way to notice the server was updated"),
        ("visibilitychange", "the check never runs — returning to the tab is the moment it matters"),
    ]:
        assert needle in js, f"single-instance guard is missing {needle!r} — {why}"


def test_the_guard_never_pretends_it_can_close_a_tab():
    """A page cannot close a tab it did not open; every browser blocks it. A
    button promising to would fail silently, which is worse than not offering
    it. The design is takeover, and this keeps it honest."""
    js = (APP / "static" / "app.js").read_text(encoding="utf-8")
    guard = js[js.index("function metisSingleInstance"):]
    assert "window.close" not in guard, (
        "the guard calls window.close() — blocked for tabs the script did not "
        "open, so it will do nothing and the reader will think Metis is broken"
    )
