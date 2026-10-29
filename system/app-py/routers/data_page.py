"""
routers/data_page.py — the Data surface: what the Data Memory knows.

Everything shown here was learnt from the researcher's analysis CODE and the
notes beside it (metis_mcp.data_memory). No route in this file opens a data
file: a file's existence is a stat(), its columns and values come from the
scripts that use it. That promise is the page's headline because it is the
reason the feature can be trusted with surveillance or patient data at all.
"""

import json
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from db import get_db_path

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _dm():
    from metis_mcp import data_memory as dm
    return dm


def _db() -> Path:
    return Path(get_db_path())


def _sources_ctx() -> dict:
    dm = _dm()
    st = dm.status(db=_db())
    sources = []
    for s in st["sources"]:
        sources.append({**s, "display": dm.to_display(s["root"]),
                        "name": Path(dm.to_display(s["root"])).name})
    return {"st": st, "sources": sources, "job": dict(dm.JOB)}


def _card(conn, key: str) -> dict | None:
    dm = _dm()
    if not conn.execute("SELECT 1 FROM dm_datasets WHERE key = ?", (key,)).fetchone():
        return None
    card = dm.dataset_card(conn, key, max_cols=120)
    card["read_by"] = [{"script": s, "name": Path(s).name, "object": o, "sheet": x}
                       for s, o, x in card["read_by"]]
    card["written_by"] = [{"script": s, "name": Path(s).name} for s in card["written_by"]]
    return card


def _page_ctx(q: str = "", file: str = "") -> dict:
    """`q` pre-fills the search; `file` (a name, path or key) opens that file's card,
    so a link from a conversation can land on the file it is about."""
    dm = _dm()
    ctx = _sources_ctx()
    with dm.open_db(_db()) as conn:
        ctx["datasets"] = dm.list_datasets(conn, q=q, limit=40)
        ctx["card"] = None
        if file:
            hit = dm.find_datasets(conn, file, limit=1)
            ctx["card"] = _card(conn, hit[0]["key"]) if hit else None
    ctx["active_tab"] = "data"
    ctx["q"] = q
    return ctx


@router.get("/data", response_class=HTMLResponse)
async def data_page(request: Request, q: str = "", file: str = ""):
    return templates.TemplateResponse(request, "data_tab.html", _page_ctx(q, file))


@router.get("/api/tab/data", response_class=HTMLResponse)
async def data_tab(request: Request):
    return templates.TemplateResponse(request, "data_tab.html", _page_ctx())


@router.get("/api/partial/data/files", response_class=HTMLResponse)
async def data_files(request: Request, q: str = "", outputs: int = 0):
    dm = _dm()
    with dm.open_db(_db()) as conn:
        rows = dm.list_datasets(conn, q=q, inputs_only=not outputs, limit=40)
    return templates.TemplateResponse(request, "partials/data_files.html",
                                      {"datasets": rows, "q": q})


@router.get("/api/partial/data/file", response_class=HTMLResponse)
async def data_file(request: Request, key: str):
    dm = _dm()
    with dm.open_db(_db()) as conn:
        card = _card(conn, key)
    return templates.TemplateResponse(request, "partials/data_file.html", {"card": card})


@router.get("/api/partial/data/sources", response_class=HTMLResponse)
async def data_sources(request: Request):
    return templates.TemplateResponse(request, "partials/data_sources.html", _sources_ctx())


@router.post("/api/data-memory/preview", response_class=JSONResponse)
async def preview(request: Request):
    """Count scripts and notes in the folders a person typed — by file name only."""
    body = await request.json()
    folders = [f for f in (body.get("folders") or []) if str(f).strip()][:20]
    return {"folders": [_dm().preview_folder(f) for f in folders]}


@router.post("/api/data-memory/folders", response_class=HTMLResponse)
async def add_folder(request: Request, folder: str = Form(""), project_id: str = Form("")):
    dm = _dm()
    ctx_msg = ""
    if folder.strip():
        try:
            p = dm.register_source(folder, project_id=project_id.strip(), db=_db())
            dm.start_background_refresh(db=_db())
            ctx_msg = f"Learning {p['scripts']} scripts from {Path(p['folder']).name}…"
        except FileNotFoundError:
            ctx_msg = f"Not found on this computer: {folder.strip()}"
    ctx = _sources_ctx()
    ctx["message"] = ctx_msg
    return templates.TemplateResponse(request, "partials/data_sources.html", ctx)


@router.post("/api/data-memory/refresh", response_class=HTMLResponse)
async def refresh(request: Request):
    _dm().start_background_refresh(db=_db())
    return templates.TemplateResponse(request, "partials/data_sources.html", _sources_ctx())


@router.post("/api/data-memory/forget", response_class=HTMLResponse)
async def forget(request: Request, folder: str = Form(...)):
    n = _dm().forget_source(folder, db=_db())
    ctx = _sources_ctx()
    ctx["message"] = f"Forgot {n} scripts from {Path(folder).name}. Nothing on disk was touched."
    return templates.TemplateResponse(request, "partials/data_sources.html", ctx)


@router.post("/api/data-memory/story", response_class=HTMLResponse)
async def add_story(request: Request, key: str = Form(...), story: str = Form(...)):
    dm = _dm()
    if story.strip():
        with dm.open_db(_db()) as conn:
            name = conn.execute("SELECT path FROM dm_datasets WHERE key = ?", (key,)).fetchone()
        if name:
            dm.add_story(name[0], story, db=_db())
    return await data_file(request, key)


@router.get("/api/data-memory/status", response_class=JSONResponse)
async def status():
    ctx = _sources_ctx()
    return json.loads(json.dumps({"status": ctx["st"], "job": ctx["job"]}, default=str))
