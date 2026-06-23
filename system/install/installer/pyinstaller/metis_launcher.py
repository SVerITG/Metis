"""
metis_launcher.py — single entry point for the bundled `metis.exe` (PyInstaller).

One frozen executable serves BOTH Metis processes, chosen by the first argument:

    metis.exe dashboard       # FastAPI + HTMX dashboard (uvicorn) on 127.0.0.1:<port>
    metis.exe mcp             # stdio MCP server — what Claude Desktop / Code spawns
    metis.exe doctor          # quick self-check (paths, DB, key) and exit
    metis.exe --version       # print version and exit

Why one exe with subcommands (not two exes): PyInstaller would otherwise freeze the
Python runtime + heavy deps (pandas, onnxruntime, pymupdf, anthropic) twice. One binary,
dispatched on argv[1], keeps the install small and the two roles in lockstep.

CODE vs DATA contract (see system/config/data-persistence-strategy.md):
  - This frozen exe is CODE only — Python runtime + deps + the app-py / mcp-server source.
  - The editable tree (agents/, .claude/skills/, system/config/, templates/) is laid down
    on disk by the Inno installer and pointed to by METIS_RC_ROOT, so updates and
    personalization still work without rebuilding the exe.
  - User DATA lives in ~/.local/share/metis/ (resolved by config.resolve_live_db) and is
    NEVER inside the bundle — an update replaces the exe and leaves the data untouched.
"""

import os
import sys
from pathlib import Path


def _bundle_root() -> Path:
    """Directory the frozen exe lives in (onedir) or the temp extract dir (onefile)."""
    if getattr(sys, "frozen", False):
        # sys.executable = .../metis.exe ; its parent is the install dir for onedir builds.
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _resolve_rc_root() -> Path:
    """Find the laid-down CODE tree (agents/, system/, .claude/).

    Priority: explicit env → the install dir the exe sits in → two levels up (dev run).
    The Inno installer places metis.exe at {app}\\ alongside agents/ and system/, so the
    bundle root IS the RC root for a normal install.
    """
    env = os.environ.get("METIS_RC_ROOT") or os.environ.get("METIS_PKM_ROOT")
    if env and Path(env).exists():
        return Path(env).resolve()

    root = _bundle_root()
    # Walk up a few levels looking for the marker dirs, so a dev `python metis_launcher.py`
    # from the source tree also works.
    for cand in [root, *root.parents][:6]:
        if (cand / "agents").is_dir() and (cand / "system").is_dir():
            return cand
    return root


def _prepare_environment() -> Path:
    """Set METIS_RC_ROOT and make the bundled app-py / mcp-server importable."""
    rc_root = _resolve_rc_root()
    os.environ.setdefault("METIS_RC_ROOT", str(rc_root))

    # The frozen bundle carries the app-py and mcp-server sources as data dirs so their
    # modules import cleanly whether frozen or run from source.
    base = _bundle_root() if getattr(sys, "frozen", False) else rc_root
    app_py = base / "app_py" if getattr(sys, "frozen", False) else rc_root / "system" / "app-py"
    mcp_src = base / "mcp_src" if getattr(sys, "frozen", False) else rc_root / "system" / "mcp-server" / "src"
    for p in (str(app_py), str(mcp_src)):
        if p not in sys.path and Path(p).exists():
            sys.path.insert(0, p)

    # Load ANTHROPIC_API_KEY from system/.env if not already set (mirrors run.sh).
    if not os.environ.get("ANTHROPIC_API_KEY"):
        env_file = rc_root / "system" / ".env"
        if env_file.is_file():
            for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    val = line.split("=", 1)[1].strip()
                    if val:
                        os.environ["ANTHROPIC_API_KEY"] = val
                    break
    return rc_root


def _run_dashboard(argv) -> int:
    """Start the FastAPI dashboard. Port: --port N, else METIS_PORT, else 8080."""
    import uvicorn

    port = 8080
    if "--port" in argv:
        try:
            port = int(argv[argv.index("--port") + 1])
        except (ValueError, IndexError):
            pass
    elif os.environ.get("METIS_PORT"):
        try:
            port = int(os.environ["METIS_PORT"])
        except ValueError:
            pass

    host = os.environ.get("METIS_HOST", "127.0.0.1")
    # Import the app object directly (string "main:app" + reload doesn't survive freezing).
    import main as dashboard_main
    uvicorn.run(dashboard_main.app, host=host, port=port, reload=False, log_level="info")
    return 0


def _run_mcp() -> int:
    """Start the stdio MCP server (blocks, serving over stdin/stdout)."""
    from metis_mcp.server import run as mcp_run
    mcp_run()
    return 0


def _run_doctor() -> int:
    rc_root = os.environ.get("METIS_RC_ROOT", "(unset)")
    print("Metis bundled launcher — self-check")
    print(f"  frozen          : {bool(getattr(sys, 'frozen', False))}")
    print(f"  bundle root     : {_bundle_root()}")
    print(f"  METIS_RC_ROOT   : {rc_root}")
    print(f"  API key present : {bool(os.environ.get('ANTHROPIC_API_KEY'))}")
    try:
        from metis_mcp.config import paths
        print(f"  live DB         : {paths.db}")
        print(f"  DB exists       : {Path(paths.db).exists()}")
    except Exception as exc:  # pragma: no cover - diagnostic only
        print(f"  config import   : FAILED ({type(exc).__name__}: {exc})")
        return 1
    return 0


_USAGE = "usage: metis [dashboard [--port N] | mcp | doctor | --version]"


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0].lower() if argv else "dashboard"  # default role = dashboard (double-click)

    if cmd in ("--version", "-v", "version"):
        print("Metis bundled 1.0")
        return 0
    if cmd in ("-h", "--help", "help"):
        print(_USAGE)
        return 0

    _prepare_environment()

    if cmd == "dashboard":
        return _run_dashboard(argv[1:])
    if cmd == "mcp":
        return _run_mcp()
    if cmd == "doctor":
        return _run_doctor()

    sys.stderr.write(f"unknown command: {cmd}\n{_USAGE}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
