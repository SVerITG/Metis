"""The design system, and the ratchet that stops it eroding.

A measured audit on 2026-08-26 found 3,171 inline `style=` attributes across 191
templates carrying 12,041 hand-written declarations — 53 distinct font sizes, 222
paddings, 78 colours, 60 button class combinations, nine shapes for "a thing in a
list". The colour tokens were never the problem; there was simply nothing to
reach for between a token and a whole page, so every panel invented its own.

These tests defend three properties:
  1. There is ONE of each scale. The failure that motivated this file was
     committed by its own author: a second --t-* scale added later in the
     stylesheet silently overrode the first, shrinking every --t-body from 15px
     to 13.5px.
  2. Values on the surfaces already migrated stay on the scales.
  3. The total does not climb back. A budget, checked, so the next feature
     cannot quietly add three hundred more.
"""
import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CSS = ROOT / "system" / "app-py" / "static" / "styles.css"
TPL = ROOT / "system" / "app-py" / "templates"


def _css():
    return re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)


def _templates():
    return sorted(TPL.rglob("*.html"))


# ── 1. one of each scale ─────────────────────────────────────────────────────

@pytest.mark.parametrize("token", [
    "--t-display", "--t-h1", "--t-h2", "--t-h3", "--t-h4",
    "--t-body", "--t-small", "--t-meta", "--t-micro",
    "--m-space-1", "--m-space-2", "--m-space-3", "--m-space-4",
    "--m-space-5", "--m-space-6",
    "--m-radius", "--m-radius-sm", "--m-radius-pill",
])
def test_every_scale_token_is_defined_exactly_once(token):
    """Redefining a token later in the file silently wins. That is how --t-body
    went from 15px to 13.5px without anyone touching a component."""
    n = len(re.findall(rf"{re.escape(token)}\s*:", _css()))
    assert n == 1, f"{token} defined {n} times — a later one silently overrides"


def test_no_token_is_referenced_without_being_defined():
    """An undefined custom property with no fallback makes the declaration
    invalid at computed-value time: the property INHERITS instead. Silent, and
    it looks exactly like a specificity bug."""
    css = _css()
    defined = set(re.findall(r"(--[\w-]+)\s*:", css))
    # A token used ONLY with a fallback is a deliberate override hook —
    # `gap: var(--u-gap, var(--m-space-2))` lets one class serve every gap
    # without a class per value. Undefined is the point; it is set per instance.
    hooks = set(re.findall(r"var\((--[\w-]+),", css))
    used = set(re.findall(r"var\((--[\w-]+)", css))
    missing = used - defined - hooks
    assert not missing, f"undefined and never given a fallback: {sorted(missing)}"


def test_no_redundant_fallbacks():
    """`var(--token, fallback)` where the token exists is dead code that can only
    ever mask a typo. One of them carried a DIFFERENT red than --m-alert and
    would have overridden the dark theme."""
    css = _css()
    defined = set(re.findall(r"(--[\w-]+)\s*:", css))
    bad = [t for t in re.findall(r"var\((--[\w-]+),", css) if t in defined]
    assert not bad, (
        f"redundant fallbacks: {sorted(set(bad))} — the token is defined, so the "
        f"fallback can only ever mask a typo")


# ── 2. the components exist and are shared ───────────────────────────────────

@pytest.mark.parametrize("cls", [
    "item", "item-body", "item-actions", "acts", "act", "badge", "seg",
    "toolbar", "u-label", "u-row", "u-grow", "u-rule", "u-ed", "panel--sm",
])
def test_the_component_layer_is_defined(cls):
    assert re.search(rf"\.{re.escape(cls)}\b[^{{]*\{{", _css()), f".{cls} missing"


def test_density_shifts_every_row_token_at_once():
    """Density is one axis on <html>, not a setting each component reads."""
    css = _css()
    for t in ("--d-row-y", "--d-row-gap", "--d-stack", "--d-panel"):
        assert f"{t}:" in css.replace(" ", ""), f"{t} missing"
    assert '[data-density="compact"]' in css
    assert '[data-density="spacious"]' in css


# ── 3. the ratchet ───────────────────────────────────────────────────────────
# A budget, not a ban. The 2,709 that remain are real work still to do; what
# this stops is the next feature quietly adding three hundred more.
INLINE_BUDGET = 2_750


def test_inline_styling_does_not_climb_back():
    total = sum(f.read_text(encoding="utf-8", errors="replace").count('style="')
                for f in _templates())
    assert total <= INLINE_BUDGET, (
        f"{total} inline style attributes, budget {INLINE_BUDGET}. "
        f"Use the idiom classes (.u-label, .u-row, .u-grow, .panel--*) or, if a "
        f"genuinely new pattern has appeared, name it in styles.css and raise "
        f"this budget deliberately."
    )


def test_the_migrated_surfaces_stay_on_the_scales():
    """News and the reading stack are fully migrated. Anything that lands there
    with a raw pixel font-size is a regression, not a leftover."""
    offenders = []
    for name in ("news_tab.html", "stack_body.html", "_news_tabstrip.html",
                 "_item.html"):
        f = TPL / "partials" / name
        for m in re.finditer(r"font-size:\s*(\d[\d.]*px)", f.read_text(encoding="utf-8")):
            offenders.append(f"{name}: {m.group(1)}")
    assert not offenders, f"raw font sizes on migrated surfaces: {offenders}"


def test_the_migration_tool_is_idempotent():
    """Running it twice must change nothing the second time — otherwise it is
    rewriting its own output and the diff can never settle."""
    import subprocess
    import sys
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "migrate_inline_styles.py"), "--check"],
        capture_output=True, text=True, cwd=ROOT, timeout=180)
    assert out.returncode == 0, out.stderr[-500:]
    m = re.search(r"(\d[\d,]*)\s+total substitutions", out.stdout)
    n = int(m.group(1).replace(",", "")) if m else 0
    assert n == 0, f"a second run would change {n} more things — not settled"
