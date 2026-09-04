"""One class name, one owner.

Written 2026-09-04 after making the same mistake three times in one session. A
new component gets a short class prefix, the prefix is already taken by an
unrelated component, and the two blocks fight in a 283,000-byte stylesheet where
whichever sits later silently wins:

  * `nf-` was given to a news overview grid. It already belonged to the card grid
    on the other news tabs — SEVEN duplicated selectors.
  * `nb-` was given to the briefing editions. It already belonged to the
    NOTEBOOK, and the notebook's italic serif body leaked into every briefing
    description — TEN duplicated selectors, and the visible symptom was
    body copy in the wrong face.
  * a third was avoided only because an unrelated edit failed first.

None of the three produced an error. CSS has no collision diagnostic: the second
`.nb-body` is simply applied after the first, so the bug arrives as a font that
looks slightly wrong on one panel.

The rule this asserts is narrow and cheap: a component selector must not be
DECLARED twice in the stylesheet. Declaring one twice is occasionally deliberate
— a media query, a theme override, a state — so the check ignores rules inside
`@media`/`@supports` blocks and rules whose selector carries a state
(`:hover`, `[data-theme]`, `.is-`), and it holds a small allowlist for the
duplicates that predate it.
"""
import re
from pathlib import Path

CSS = Path(__file__).resolve().parents[2] / "system" / "app-py" / "static" / "styles.css"

# Duplicates that existed before this test. They are NOT approved — they are
# recorded so the test can start passing without a refactor, and the list must
# only ever get shorter. Adding to it is the thing this test exists to prevent.
GRANDFATHERED = {
    ".acts",
    ".badge",
    ".board-box",
    ".board-box-foot",
    ".board-box-icon",
    ".btn",
    ".course-card",
    ".empty-row",
    ".feed-row",
    ".ft-entry",
    ".ledger-n",
    ".mrow",
    ".nav-item",
    ".ov-item",
    ".ov-link",
    ".ov-single",
    ".ov-thread",
    ".ov-thread-items",
    ".page",
    ".panel",
    ".project-card",
    ".row-hit",
    ".scroll",
    ".sk",
    ".sk-bar",
    ".sk-card",
    ".skeleton",
    ".stk-counts",
    ".th-row",
    ".today-news-rail",
    ".u-clamp-2",
    ".u-clamp-3",
    ".ui-zone-head",
}


def _strip_at_blocks(css: str) -> str:
    """Remove @media/@supports bodies — a redefinition there is the point of them."""
    out, i, depth, skipping = [], 0, 0, False
    while i < len(css):
        if not skipping and css.startswith("@", i):
            head = css[i:i + 200]
            if re.match(r"@(media|supports|container)\b", head):
                skipping, depth = True, 0
        ch = css[i]
        if skipping:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    skipping = False
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def _component_rules(css: str) -> dict[str, int]:
    """Count declarations of each bare single-class selector."""
    counts: dict[str, int] = {}
    for m in re.finditer(r"(^|\})\s*([^{}@]+?)\{", css, re.M):
        for sel in m.group(2).split(","):
            sel = " ".join(sel.split())
            # Only a bare, single, unqualified class — that is what a component
            # prefix collision looks like. Anything with a state, a descendant
            # or an attribute is a deliberate refinement.
            if re.fullmatch(r"\.[a-z][\w-]*", sel) and not re.search(r"\.is-|--", sel):
                counts[sel] = counts.get(sel, 0) + 1
    return counts


def test_no_component_class_is_declared_twice():
    css = _strip_at_blocks(re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S))
    dupes = {s: n for s, n in _component_rules(css).items()
             if n > 1 and s not in GRANDFATHERED}
    assert not dupes, (
        "these class selectors are declared more than once, so two components "
        "are fighting and the one later in the file wins silently:\n  "
        + "\n  ".join(f"{s}  ×{n}" for s, n in sorted(dupes.items()))
        + "\n\nGive the newer component its own prefix. Check first with:\n"
          "  grep -c 'yourprefix-' system/app-py/static/styles.css"
    )


def test_the_grandfathered_list_only_shrinks():
    """A pre-existing duplicate that has been fixed must leave the list.

    Otherwise the allowlist becomes the place collisions go to be forgotten,
    which is worse than not having the test.
    """
    css = _strip_at_blocks(re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S))
    counts = _component_rules(css)
    stale = sorted(s for s in GRANDFATHERED if counts.get(s, 0) <= 1)
    assert not stale, (
        "these are no longer duplicated and should be removed from "
        f"GRANDFATHERED: {stale}"
    )
