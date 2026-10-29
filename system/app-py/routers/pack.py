"""The institution pack's surface — /pack.

An edition of Metis made for one institute carries a pack (packs/<id>/pack.json):
the institute's templates, the procedures behind its paperwork, and a few
actions that start from them. This surface is where a researcher meets them.

WHY THE ACTIONS HAND OVER TO CLAUDE INSTEAD OF RUNNING HERE
    Drafting an ethics letter or a deck needs a model, and the dashboard has
    none of its own unless someone pays for an API key — which most researchers
    will not have. Claude Desktop does, on their subscription. So each action
    shows the sentence to say there, with a copy button, and the same action is
    in Desktop's "Add from Metis" menu. The templates are downloadable from here
    directly, because a template needs no model at all.

Absent pack → this surface redirects home and the navbar shows nothing, so the
full build is unchanged.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

router = APIRouter()
_log = logging.getLogger("metis.pack")


def _pack() -> dict:
    try:
        from metis_mcp.edition import pack
        return pack()
    except Exception as exc:  # a broken MCP tree must not break the dashboard
        _log.warning("[pack] unavailable: %s", exc)
        return {}


def _procedure_text(pk: dict, rel: str) -> str:
    try:
        return (Path(pk["dir"]) / rel).read_text(encoding="utf-8")
    except Exception:
        return ""


@router.get("/pack", response_class=HTMLResponse)
async def pack_page(request: Request):
    pk = _pack()
    if not pk:
        return RedirectResponse(url="/", status_code=302)
    from main import templates
    by_id = {t.get("id"): t for t in pk.get("templates") or []}
    actions = []
    for a in pk.get("actions") or []:
        actions.append({
            **a,
            "template_rows": [by_id[i] for i in a.get("templates") or [] if i in by_id],
            "procedure_text": _procedure_text(pk, a["procedure"]) if a.get("procedure") else "",
        })
    seed_pack_focus()
    return templates.TemplateResponse(request, "pack.html", {
        "active_tab": "pack",
        "pk": pk,
        "actions": actions,
    })


@router.get("/pack/template/{tid}")
async def pack_template(tid: str):
    """Download one of the pack's templates, under its own file name."""
    pk = _pack()
    t = next((t for t in pk.get("templates") or [] if t.get("id") == tid), None)
    if not pk or not t:
        return HTMLResponse("No such template.", status_code=404)
    root = Path(pk["dir"]).resolve()
    f = (root / t["file"]).resolve()
    # The manifest is shipped, not typed by a user, but a path that leaves the
    # pack folder is still refused rather than served.
    if root not in f.parents or not f.is_file():
        return HTMLResponse("Template file missing.", status_code=404)
    return FileResponse(f, filename=f.name)


def seed_pack_focus() -> None:
    """Put the pack's focus on the shelf ONCE, the first time the edition runs.

    Once: a marker file records that it was offered, so a researcher who takes
    it off the shelf does not find it back the next morning. Never raises.
    """
    pk = _pack()
    spec = pk.get("focus") or {}
    if not spec.get("slug"):
        return
    try:
        from metis_mcp.config import get_root
        marker = get_root() / "system" / "config" / f".pack-focus-{pk.get('id', 'pack')}"
        if marker.exists():
            return
        from metis_mcp.tools import focus as F
        if F.get_focus(spec["slug"]):
            marker.write_text("present\n", encoding="utf-8")
            return
        links = [{"title": a.get("title"), "href": f"/pack#{a.get('id')}",
                  "note": a.get("summary", ""), "kind": "action"}
                 for a in pk.get("actions") or []]
        links += [{"title": t.get("title"), "href": f"/pack/template/{t.get('id')}",
                   "note": t.get("kind", ""), "kind": "template"}
                  for t in pk.get("templates") or []]
        import datetime
        from db import db_execute
        taken = {a.get("shelf_slot") for a in F.list_focus("active")}
        free = [s for s in range(1, F.MAX_SHELF + 1) if s not in taken]
        on_shelf = bool(free)
        db_execute(
            "INSERT INTO focus_areas (slug, title, subtitle, state, shelf_slot, keyword_groups, "
            "overview, created_at, activated_at, sections, links) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (spec["slug"], spec.get("title", spec["slug"]), spec.get("subtitle", ""),
             "active" if on_shelf else "following", free[0] if on_shelf else None,
             json.dumps(spec.get("keyword_groups") or []), spec.get("overview", ""),
             datetime.datetime.now().isoformat(timespec="seconds"),
             datetime.datetime.now().isoformat(timespec="seconds") if on_shelf else "",
             json.dumps(spec.get("sections") or []), json.dumps(links)))
        marker.write_text("seeded\n", encoding="utf-8")
    except Exception as exc:
        _log.warning("[pack] focus not seeded: %s", exc)
