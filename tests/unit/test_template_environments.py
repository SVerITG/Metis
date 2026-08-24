"""Every Jinja environment must carry the shared globals and filters.

WHY THIS TEST EXISTS
    This app builds SEVENTEEN separate `Jinja2Templates` instances — `main.py`
    plus one per router — and each has its own `env`. A "template global" is
    therefore not global, and the two ways that bites are both silent:

      · `focus_shelf` registered only on main's environment threw
        `UndefinedError` and a **500 on /news**, which is rendered from
        routers/today.py's instance (2026-08-24).
      · `_metis_user_name` registered only on main's environment made /news serve
        `window.METIS_USER_NAME = "Researcher"` and an avatar initial of "R" while
        every other surface served "the researcher" and "S". It did not crash — base.html
        guards the call with `is defined` — so the personalisation just quietly
        fell back on exactly the pages that did not come through main.

    `main.install_shared_globals()` fixes both by walking every environment. But a
    fix that depends on someone remembering to add the next global to
    `_SHARED_GLOBALS` is the same class of defect this project keeps paying for.
    So this test asserts the invariant instead: whatever main's environment
    carries beyond stock Jinja, every other environment carries too.

    It will fail when someone adds a global or filter to one environment only —
    which is the moment worth catching, not three weeks later on one page.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).parent.parent.parent
_APP = _REPO / "system" / "app-py"
_MCP_SRC = _REPO / "system" / "mcp-server" / "src"
for _p in (str(_APP), str(_MCP_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

jinja2 = pytest.importorskip("jinja2")


@pytest.fixture(scope="module")
def envs():
    """Every distinct Jinja environment the app builds, keyed by module name."""
    try:
        import main  # noqa: F401  — importing registers every router
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"dashboard app not importable here: {exc}")

    found: dict[int, tuple[str, object]] = {}
    for name, mod in list(sys.modules.items()):
        if not (name == "main" or name.startswith("routers.")):
            continue
        for attr in ("templates", "_TEMPLATES"):
            env = getattr(getattr(mod, attr, None), "env", None)
            if env is not None:
                found.setdefault(id(env), (name, env))
    return found


def _app_added(env) -> tuple[set, set]:
    """What this environment carries beyond a stock Jinja environment."""
    std = jinja2.Environment()
    return (set(env.globals) - set(std.globals),
            set(env.filters) - set(std.filters))


def test_there_really_are_several_environments(envs):
    """Documents the surprise. If this ever drops to 1, delete this whole file."""
    assert len(envs) > 1, (
        "only one Jinja environment found — if the app was consolidated onto a "
        "single Jinja2Templates instance, this test is obsolete")


def test_every_environment_carries_mains_globals(envs):
    """The invariant. A global on one environment only is a silent per-page bug."""
    import main
    base_g, base_f = _app_added(main.templates.env)
    assert base_g, "main's environment should carry app-added globals"

    gaps = []
    for name, env in envs.values():
        missing_g = base_g - set(env.globals)
        missing_f = base_f - set(env.filters)
        if missing_g or missing_f:
            gaps.append(f"{name}: globals={sorted(missing_g)} "
                        f"filters={sorted(missing_f)}")
    assert not gaps, (
        "these environments are missing shared globals/filters, so any template "
        "they render will silently degrade or raise UndefinedError:\n  "
        + "\n  ".join(gaps)
        + "\n\nAdd the entry to main._SHARED_GLOBALS / _SHARED_FILTERS rather "
          "than to one environment.")


def test_the_two_globals_that_actually_broke_are_present_everywhere(envs):
    """Named explicitly, because these are the two that shipped broken."""
    for key in ("focus_shelf", "_metis_user_name"):
        for name, env in envs.values():
            assert key in env.globals, f"{key} missing from {name}"


def test_md_filter_is_present_everywhere(envs):
    """Focus overviews are markdown; a missing filter is an UndefinedError."""
    for name, env in envs.values():
        assert "md" in env.filters, f"md filter missing from {name}"


def test_installer_is_idempotent_and_reports_a_count(envs):
    import main
    n1 = main.install_shared_globals()
    n2 = main.install_shared_globals()
    assert n1 == n2 == len(envs)
