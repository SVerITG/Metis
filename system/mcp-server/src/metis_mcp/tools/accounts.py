"""Which account (work or personal) every project uses.

Reads system/config/accounts.json — names, ids and where each login is kept,
never the credentials themselves. The same file drives the git pre-push guard
(system/release/account_guard.py), so what Metis says here is what a push or
publish is actually allowed to do.
"""

import json
import os
import socket

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths

_REGISTRY = paths.root / "system" / "config" / "accounts.json"


def _load() -> dict | None:
    try:
        return json.loads(_REGISTRY.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def _norm(p: str) -> str:
    return os.path.normcase(os.path.realpath(os.path.expanduser(p))).rstrip("/\\")


def _find(reg: dict, path: str) -> dict | None:
    target = _norm(path)
    best = None
    for proj in reg.get("projects", []):
        root = _norm(proj["path"])
        if target == root or target.startswith(root + os.sep) or target.startswith(root + "/"):
            if best is None or len(root) > len(_norm(best["path"])):
                best = proj
    return best


@app.tool()
async def which_account(path: str) -> list[TextContent]:
    """Which project a folder belongs to and which account (work or personal) it
    must use for GitHub, Netlify and Supabase. Call this before any push,
    publish, release or database change, and follow it."""
    reg = _load()
    if reg is None:
        return [TextContent(type="text", text="No accounts registry (system/config/accounts.json) on this installation.")]
    proj = _find(reg, path)
    if not proj:
        return [TextContent(type="text", text=f"No declared project covers {path}. Ask which account it belongs to and add it to accounts.json before pushing or publishing.")]
    acct = reg["accounts"][proj["account"]]
    host = socket.gethostname()
    machine = {"hostname": host, **(reg.get("machines", {}).get(host) or {"label": "unknown computer: add it to accounts.json machines"})}
    return [TextContent(type="text", text=json.dumps({"project": proj, "account": {"key": proj["account"], **acct}, "this_computer": machine}, indent=2, ensure_ascii=False))]


@app.tool()
async def list_accounts() -> list[TextContent]:
    """All accounts (work, personal), every project with the account it uses,
    and accounts or sites still to be retired."""
    reg = _load()
    if reg is None:
        return [TextContent(type="text", text="No accounts registry (system/config/accounts.json) on this installation.")]
    lines = ["| Project | Account | GitHub | Netlify | Supabase |", "|---|---|---|---|---|"]
    for p in reg.get("projects", []):
        lines.append(f"| {p['name']} | {reg['accounts'][p['account']]['label']} | {', '.join(p.get('git_remotes', [])) or '—'} "
                     f"| {(p.get('netlify') or {}).get('site', '—')} | {(p.get('supabase') or {}).get('project', '—')} |")
    machines = {k: v for k, v in (reg.get("machines") or {}).items() if not k.startswith("_")}
    if machines:
        here = socket.gethostname()
        lines += ["", "Computers:"] + [f"- {v.get('label', k)} ({k}){' ← this one' if k == here else ''}" for k, v in machines.items()]
    retire = reg.get("to_retire") or []
    if retire:
        lines += ["", "To retire:"] + [f"- {r['what']} ({r.get('status', '')})" for r in retire]
    return [TextContent(type="text", text="\n".join(lines))]
