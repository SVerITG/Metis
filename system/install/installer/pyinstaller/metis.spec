# -*- mode: python ; coding: utf-8 -*-
"""
metis.spec — PyInstaller spec for the bundled end-user `metis.exe`.

Build (on Windows, in a venv that has the project deps installed):
    pyinstaller --noconfirm --clean system\\install\\installer\\pyinstaller\\metis.spec

Produces an ONEDIR bundle at dist\\metis\\ — metis.exe plus an _internal\\ folder
holding the frozen Python runtime and all dependencies. Inno Setup then lays this
whole folder down at {app}\\runtime\\ and the editable CODE tree alongside it.

This MUST be built on Windows (it freezes the Windows Python + Windows wheels of
onnxruntime / pymupdf / pyreadstat). Building on Linux/WSL produces a Linux binary,
which is useless for a Windows user.
"""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

# ── Paths ─────────────────────────────────────────────────────────────────────
# SPECPATH is the dir containing this spec: repo/system/install/installer/pyinstaller
REPO = Path(SPECPATH).parents[3]          # noqa: F821 (SPECPATH injected by PyInstaller)
APP_PY = REPO / "system" / "app-py"
MCP_SRC = REPO / "system" / "mcp-server" / "src"
LAUNCHER = REPO / "system" / "install" / "installer" / "pyinstaller" / "metis_launcher.py"
ICON = REPO / "system" / "install" / "windows" / "metis.ico"

# ── Data files: templates + static go to the bundle ROOT (frozen main.py reads
#    sys._MEIPASS / "templates" and / "static"). ──────────────────────────────
datas = [
    (str(APP_PY / "templates"), "templates"),
    (str(APP_PY / "static"), "static"),
]

# ── Hidden imports: things PyInstaller's static analysis can miss ─────────────
hiddenimports = [
    # uvicorn[standard] runtime pieces
    "uvicorn.logging", "uvicorn.loops.auto", "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto", "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.auto", "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan.on", "uvicorn.lifespan.off",
    "websockets", "httptools", "h11", "anyio", "sniffio",
    # template engine + multipart form handling
    "jinja2", "multipart", "python_multipart",
]
# The dashboard does `from routers import (...)` and the MCP server registers tools
# dynamically — pull both packages in wholesale so nothing is missed.
hiddenimports += collect_submodules("routers", on_error="ignore") if (APP_PY / "routers").is_dir() else []
hiddenimports += collect_submodules("metis_mcp", on_error="ignore")

binaries = []

# ── Heavy / native deps that ship data files or shared libs. collect_all is the
#    safe hammer; each is wrapped so a missing optional package can't break the build.
for pkg in [
    "onnxruntime",     # ONNX runtime for local embeddings — native .dll/.pyd + headers
    "tokenizers",      # Rust extension
    "fitz",            # PyMuPDF — native libs (imported as `fitz`)
    "pymupdf",
    "sqlite_vec",      # loadable SQLite extension shipped as a data file
    "pyreadstat",      # SPSS/Stata reader — native lib
    "sklearn",         # scikit-learn
    "pandas",
    "openpyxl",
    "feedparser",
    "pyzotero",
    "anthropic",
    "cryptography",
    "mcp",
]:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as exc:  # noqa: BLE001 — optional dep absent at build time
        print(f"[metis.spec] skip {pkg}: {exc}")

# Optional integrations — include only if installed.
for opt in ["google.genai", "twilio"]:
    try:
        hiddenimports += collect_submodules(opt, on_error="ignore")
    except Exception:
        pass

block_cipher = None

a = Analysis(
    [str(LAUNCHER)],
    pathex=[str(APP_PY), str(MCP_SRC)],   # so `import main` and `import metis_mcp` resolve
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # trim weight the dashboard/MCP never use
        "tkinter", "matplotlib", "PyQt5", "PyQt6", "PySide6", "IPython", "jupyter",
        "pytest", "notebook",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="metis",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                  # UPX often trips Windows AV false positives — keep off
    console=True,               # MCP server needs a real stdio console; dashboard runs hidden via a VBS shim
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON) if ICON.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="metis",               # → dist/metis/  (onedir)
)
