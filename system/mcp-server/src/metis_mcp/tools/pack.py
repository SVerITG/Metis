"""The institution pack — an institute's own templates, procedures and actions.

An edition (see metis_mcp/edition.py) may name a pack: a folder under `packs/`
with a `pack.json` manifest. This module makes the pack reachable from Claude:

  * `institution_actions`   — what the pack offers, and how to ask for it
  * `institution_procedure` — the procedure behind one action, to be followed
  * one Desktop prompt per action, so it appears in the "Add from Metis" menu

Without an edition, or with an edition that has no pack, the two tools answer
that there is no pack and no prompts are registered: the full build is unchanged.

The procedures are the point. A model that drafts an ethics submission from
general knowledge produces something plausible and wrong for this institute;
one that follows the institute's own template knows which paragraphs the
committee expects, which documents go with it, and what it must not decide.
"""
from __future__ import annotations

import logging
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.edition import pack

_log = logging.getLogger("metis")


def _action(pk: dict, action_id: str) -> dict | None:
    want = action_id.strip().lower()
    for a in pk.get("actions") or []:
        if want in (str(a.get("id", "")).lower(), str(a.get("title", "")).lower()):
            return a
    # A fragment of the title is how people actually name things ("irb").
    return next((a for a in pk.get("actions") or []
                 if want and want in str(a.get("title", "")).lower()), None)


def _template_names(pk: dict, ids: list) -> list[str]:
    by_id = {t.get("id"): t for t in pk.get("templates") or []}
    return [Path(by_id[i]["file"]).name for i in ids if i in by_id and by_id[i].get("file")]


@app.tool()
async def institution_actions() -> list[TextContent]:
    """List what the researcher's institute pack offers: actions, templates, gaps.

    Use when the researcher mentions their institute's procedures or templates
    (an ethics/IRB submission, an institutional presentation or poster), or asks
    what the institute section can do. Then follow the action's procedure with
    institution_procedure.
    """
    pk = pack()
    if not pk:
        return [TextContent(type="text", text="This copy of Metis has no institution pack.")]
    lines = [f"{pk.get('name', 'Institution')} — {pk.get('tagline', '')}".rstrip(" —"), "", "Actions:"]
    for a in pk.get("actions") or []:
        lines.append(f"- {a.get('title')} (id: {a.get('id')}): {a.get('summary', '')}")
        tpl = _template_names(pk, a.get("templates") or [])
        if tpl:
            lines.append(f"    templates: {', '.join(tpl)}")
        if a.get("procedure"):
            lines.append(f"    has a procedure: institution_procedure('{a.get('id')}')")
    lines += ["", "Templates:"]
    lines += [f"- {t.get('title')} — {Path(t.get('file', '')).name}" for t in pk.get("templates") or []]
    if pk.get("missing_templates"):
        lines += ["", "Not in the pack yet (say so rather than improvising one):"]
        lines += [f"- {m}" for m in pk["missing_templates"]]
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def institution_procedure(action: str) -> list[TextContent]:
    """Return the institute's procedure for one action, to be followed step by step.

    Args:
        action: The action id or part of its title, e.g. "irb-request" or "irb".
    """
    pk = pack()
    if not pk:
        return [TextContent(type="text", text="This copy of Metis has no institution pack.")]
    a = _action(pk, action)
    if a is None:
        ids = ", ".join(str(x.get("id")) for x in pk.get("actions") or [])
        return [TextContent(type="text", text=f"No action matches '{action}'. Available: {ids}.")]
    tpl = _template_names(pk, a.get("templates") or [])
    head = [f"Action: {a.get('title')}", a.get("summary", "")]
    if tpl:
        head.append("Templates to use (already stored in Metis — never ask for the file): "
                    + ", ".join(tpl))
    if a.get("produces"):
        head.append("Give back: " + "; ".join(a["produces"]))
    body = ""
    if a.get("procedure"):
        try:
            body = (Path(pk["dir"]) / a["procedure"]).read_text(encoding="utf-8")
        except OSError as exc:
            body = f"(The procedure file could not be read: {exc})"
    else:
        body = ("No written procedure for this action. Use the template(s) above, "
                "ask for what is missing two or three questions at a time, and mark "
                "anything undecided as [TO COMPLETE: …] rather than inventing it.")
    return [TextContent(type="text", text="\n".join(h for h in head if h) + "\n\n" + body)]


def _make_action_prompt(pk: dict, a: dict):
    def _fn(description: str = "") -> str:
        start = (
            f"The researcher wants to: {a.get('title')}.\n"
            f"First call institution_procedure('{a.get('id')}') and follow it exactly. "
            "Speak plainly, ask at most two or three questions at a time, and never "
            "invent a fact the researcher has not given.\n"
        )
        return start + (f"\nWhat they said: {description}\n" if description.strip() else
                        "\nAsk them to describe what they want in their own words first.\n")
    return _fn


def _register_pack_prompts() -> int:
    pk = pack()
    if not pk:
        return 0
    from mcp.server.fastmcp.prompts.base import Prompt
    n = 0
    short = pk.get("short_name") or "Institute"
    for a in pk.get("actions") or []:
        try:
            app.add_prompt(Prompt.from_function(
                _make_action_prompt(pk, a),
                name=f"{pk.get('id', 'pack')}-{a.get('id')}",
                title=f"{short} · {a.get('title')}",
                description=a.get("summary", ""),
            ))
            n += 1
        except Exception as exc:  # noqa: BLE001 — one bad action must not hide the rest
            _log.warning("pack prompt %s skipped: %s", a.get("id"), exc)
    return n


_N_PROMPTS = _register_pack_prompts()
