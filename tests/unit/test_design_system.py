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


def _code(f) -> str:
    """A template with its comments stripped.

    These checks scan for markup, and a comment that DESCRIBES markup is not
    markup. `_duedate.html` documents the bare `<input type="date">` it
    replaced, and the unlabelled-input check duly flagged the sentence about the
    bug as the bug. An audit that reports prose as a defect gets silenced, and a
    silenced audit protects nothing — the same lesson as the coloured-dot rule.
    """
    src = f.read_text(encoding="utf-8")
    src = re.sub(r"\{#.*?#\}", "", src, flags=re.S)     # Jinja comments
    src = re.sub(r"<!--.*?-->", "", src, flags=re.S)     # HTML comments
    return src


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
INLINE_BUDGET = 2_520  # measured 2,502


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


def test_templates_never_reference_a_token_that_does_not_exist():
    """An undefined custom property with no fallback invalidates the ENTIRE
    declaration at computed-value time — `padding: var(--d-panel) var(--s-5)`
    sets no padding at all. Two templates were left pointing at a scale that had
    been deleted an hour earlier, and both rendered without complaint."""
    css_tokens = set(re.findall(r"(--[\w-]+)\s*:", _css()))
    bad = []
    for f in _templates():
        src = f.read_text(encoding="utf-8")
        # A template may define tokens for itself in its own <style> block —
        # capture.html does, and that is legitimate scoping, not a bug.
        known = css_tokens | set(re.findall(r"(--[\w-]+)\s*:", src))
        for m in re.finditer(r"var\((--[\w-]+)\s*([,)])", src):
            if m.group(2) == ")" and m.group(1) not in known:
                bad.append(f"{f.name}: {m.group(1)}")
    assert not bad, f"templates using undefined tokens: {sorted(set(bad))}"


def test_section_headings_do_not_override_their_own_default():
    """`.sec-label` declares `margin: 0 0 16px`. Seventy-eight call sites passed
    a `style=` argument to change it by a few pixels, in eight different amounts
    — overriding a default that was already right. Section spacing is a rhythm
    or it is eighty-six separate opinions."""
    bad = []
    for f in _templates():
        for m in re.finditer(r"sec_label\([^)]*style=\"(margin-bottom:\\s*\\d+px[^\"]*)\"",
                             f.read_text(encoding="utf-8")):
            bad.append(f"{f.name}: {m.group(1)}")
    # `margin-bottom:0` alongside `pointer-events:none` is a functional
    # override, not a spacing opinion. Only pixel spacing is the smell.
    assert not bad, f"sec_label calls overriding the default margin: {bad}"


def test_panels_use_a_variant_not_a_padding():
    """113 of 155 panels carried an inline override; almost all were saying one
    of five things about padding. `.panel--sm/md/lg/tight/flush` say it in the
    class attribute, where it is greppable."""
    bad = []
    for f in _templates():
        for m in re.finditer(r'class="(panel[^"]*)"\s+style="([^"]*padding[^"]*)"',
                             f.read_text(encoding="utf-8")):
            if "panel--" not in m.group(1):
                bad.append(f"{f.name}: {m.group(2)[:40]}")
    # 63 remain, all on page-level templates not yet migrated. A ratchet, not
    # a ban: it stops the number climbing while the migration continues.
    assert len(bad) <= 65, f"panels writing raw padding: {len(bad)} — {bad[:6]}"


def test_the_empty_state_has_three_sizes():
    """One component existed and was used once, because it is a first-run HERO
    and 104 templates needed a quiet line inside a panel. The gap was the size,
    not the component."""
    src = (TPL / "partials" / "_empty.html").read_text(encoding="utf-8")
    for macro in ("quiet", "panel", "suspect", "sk_rows", "sk_cards"):
        assert f"macro {macro}(" in src, f"_empty.html is missing {macro}()"


def test_skeletons_respect_reduced_motion():
    """A sweeping gradient at list length is exactly the animation someone with
    a vestibular disorder cannot use."""
    css = _css()
    block = css[css.index("@keyframes sk-sweep"):]
    assert "prefers-reduced-motion" in css[css.index(".sk-bar"):]


# ── "what changed since I last looked" ───────────────────────────────────────
# The last item from the design audit. Today answered it; News, Library and Work
# each answered differently or not at all — while the machinery (ui_seen,
# count_since, since_label) sat in ui.py used by one surface.

def test_whats_new_is_one_component():
    src = (TPL / "partials" / "_whatsnew.html").read_text(encoding="utf-8")
    assert "macro whatsnew(" in src
    for surface in ("_news_tabstrip.html", "stack_body.html"):
        t = (TPL / "partials" / surface).read_text(encoding="utf-8")
        assert "whatsnew(" in t, f"{surface} does not use the shared strip"


def test_marking_seen_is_an_act_not_a_render():
    """A surface that stamps itself seen because you opened it can never tell
    you what you missed — the original news-rail bug, where 859 briefs showed
    the same items every visit."""
    ui_src = (ROOT / "system" / "app-py" / "ui.py").read_text(encoding="utf-8")
    body = ui_src[ui_src.index("def whats_new("):]
    assert "mark_seen" not in body, "whats_new() marks on render"
    routes = (ROOT / "system" / "app-py" / "routers" / "stack.py").read_text(encoding="utf-8")
    assert '@router.post("/api/seen/{key}"' in routes, "no explicit mark route"


def test_the_delta_leads_and_the_total_is_demoted():
    """A number that only grows stops being information past what a person can
    act on. 1,433 unread is not a call to action; 6 since Friday is."""
    src = (TPL / "partials" / "_whatsnew.html").read_text(encoding="utf-8")
    assert src.index("wn-delta") < src.index("wn-total")


def test_whats_new_counts_the_total_correctly():
    """`count_since("")` returns 0 BY DESIGN — an empty timestamp means 'no
    delta to compute', not 'count everything'. The first draft used it for the
    total, so every surface reported zero items on a first visit."""
    ui_src = (ROOT / "system" / "app-py" / "ui.py").read_text(encoding="utf-8")
    body = ui_src[ui_src.index("def whats_new("):]
    assert 'count_since(table, ts_col, "", where)' not in body
    assert "SELECT COUNT(*) FROM {table}" in body


# ── Accessibility, ratcheted ─────────────────────────────────────────────────
# Found after the inline-style count reached its floor: the remaining attributes
# were mostly single declarations already written in the design language, so the
# question became what is actually WRONG rather than what is untidy.

def test_no_template_removes_the_focus_ring():
    """Inline `outline:none` applies ALWAYS, not only on focus, and a style
    attribute cannot express `:focus-visible` — so 54 of these were removing
    keyboard focus permanently with nothing in its place."""
    bad = [f.name for f in _templates()
           if re.search(r"outline:\s*none", _code(f))]
    assert not bad, f"templates killing the focus ring: {sorted(set(bad))}"


def test_the_focus_ring_is_declared_once_for_everything():
    css = _css()
    assert ":focus-visible" in css
    assert re.search(r":where\([^)]*button[^)]*\):focus-visible", css), (
        "no blanket focus-visible rule — rings will be inconsistent again")


def test_every_input_can_be_named_by_a_screen_reader():
    """A placeholder is not a label: it disappears on focus and is not reliably
    announced. Where no honest label existed the tool REPORTED rather than
    invented one — a made-up label lies confidently."""
    bad = []
    for f in _templates():
        s = _code(f)
        for m in re.finditer(r"<input\b[^>]*>", s):
            t = m.group(0)
            if re.search(r'type="(hidden|submit|button|checkbox|radio)"', t):
                continue
            if "aria-label" in t or "aria-labelledby" in t:
                continue
            idm = re.search(r'id="([^"]+)"', t)
            if idm and f'for="{idm.group(1)}"' in s:
                continue
            bad.append(f"{f.name}: {t[:56]}")
    assert not bad, f"unlabelled inputs: {bad}"


def test_clickable_elements_have_a_keyboard_path():
    """44 divs carried an onclick and nothing else: reachable with a mouse,
    unreachable with a keyboard."""
    bad = []
    for f in _templates():
        for m in re.finditer(r"<(?:div|span)\b[^>]*\bonclick=[^>]*>", _code(f)):
            if "tabindex" not in m.group(0) and 'role="' not in m.group(0):
                bad.append(f"{f.name}: {m.group(0)[:52]}")
    assert not bad, f"mouse-only controls: {bad}"


def test_keyboard_activation_is_delegated_not_repeated():
    js = (ROOT / "system" / "app-py" / "static" / "app.js").read_text(encoding="utf-8")
    assert "role') !== 'button'" in js or 'role") !== "button"' in js, (
        "no delegated Enter/Space handler for role=button elements")


def test_external_links_do_not_hand_over_the_window():
    bad = [f.name for f in _templates()
           if re.search(r'<a\b[^>]*target="_blank"(?![^>]*rel=)[^>]*>', _code(f))]
    assert not bad, f'target="_blank" without rel="noopener": {sorted(set(bad))}'


def test_what_changed_is_answered_the_same_way_everywhere():
    """The last item from the design audit. Today answered it, News, Library and
    Work each answered differently or not at all — while `ui_seen`,
    `count_since` and `since_label` sat in ui.py used by one surface.

    The Library heading was the sharpest case: its tail READ "what has appeared
    since you last looked" as a static string. It claimed to answer the question
    and did not."""
    users = [f.name for f in _templates()
             if "whatsnew(" in f.read_text(encoding="utf-8")
             and f.name != "_whatsnew.html"]
    for surface in ("_news_tabstrip.html", "stack_body.html",
                    "library_new_literature.html"):
        assert surface in users, f"{surface} does not answer 'what changed'"
    work = (ROOT / "system" / "app-py" / "routers" / "work.py").read_text(encoding="utf-8")
    assert "whats_new(" in work, "Work does not answer 'what changed'"


def test_the_empty_state_component_is_actually_used():
    """Building the component is the easy half. `empty_state.html` existed for
    months and was used once — leaving the replacement unused too would have
    repeated the exact pathology this session was auditing."""
    users = [f.name for f in _templates()
             if "_empty.html" in f.read_text(encoding="utf-8") and f.name != "_empty.html"]
    assert len(users) >= 8, f"only {len(users)} templates use it: {users}"


def test_no_template_uses_a_legacy_colour_alias():
    """--text-muted / --text-primary are a second vocabulary for colours that
    already have names. Two names for one colour is how a palette drifts."""
    bad = [f.name for f in _templates()
           if re.search(r"var\(--text-(muted|primary|secondary)\)",
                        f.read_text(encoding="utf-8"))]
    assert not bad, f"legacy colour aliases still in use: {sorted(set(bad))}"


def test_rem_values_land_on_the_scale_too():
    """setup.html was written in rem before the px scale existed and never
    reconciled — 23 uses of 0.875rem alone. The canonical scale is itself in rem
    (--t-body is 0.9375rem), so this was a translation, not a conversion."""
    bad = []
    for f in _templates():
        for m in re.finditer(r'style="[^"]*font-size:\s*([\d.]+rem)', f.read_text(encoding="utf-8")):
            bad.append(f"{f.name}: {m.group(1)}")
    assert len(bad) <= 4, f"raw rem font sizes: {len(bad)} — {bad[:5]}"
