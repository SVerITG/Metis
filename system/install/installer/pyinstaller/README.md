# Bundled `metis.exe` (PyInstaller) — the end-user installer runtime

This folder freezes Metis into a self-contained Windows runtime so a non-technical user
installs with **one double-click — no Python, no WSL, no venv, no pip-at-install-time**.

It is the **end-user DEFAULT** run target. The other targets (native Windows Python via
the Inno wizard, Docker, macOS/Linux `setup-mcp.sh`, WSL) are **developer** targets. See
`system/config/data-persistence-strategy.md` §6 and the Release Coordinator skill
("Run targets & installer audiences").

## What's here

| File | Role |
|---|---|
| `metis_launcher.py` | Single entry point. `metis.exe dashboard` runs the FastAPI dashboard; `metis.exe mcp` is the stdio MCP server Claude Desktop/Code spawns; `metis.exe doctor` self-checks. |
| `metis.spec` | PyInstaller spec — freezes the launcher + app-py + mcp-server + all native deps; ships `templates/` and `static/` as bundle datas. |
| `build-bundled-exe.ps1` | Windows build script: fresh venv → install deps → PyInstaller → smoke test. |

## How it differs from the existing Inno installer

The current `metis-setup.iss` **vendors an embedded Python and pip-installs at install
time** (`vendor/python-embed.zip` + `download_vendor_python.ps1` + `bootstrap_python.ps1`)
— the 5–15 minute, network-dependent path. The bundled `.exe` **replaces that runtime
layer**: PyInstaller pre-freezes Python + every compiled wheel (onnxruntime, pymupdf,
pyreadstat, tokenizers, sqlite-vec) into `dist\metis\`. Install becomes instant and offline.

What stays the same: Inno still lays down the **editable CODE tree** — `agents/`,
`.claude/skills/`, `system/config/`, etc. — so updates and personalization work without
rebuilding the exe. `METIS_RC_ROOT` points the frozen exe at that tree.

## CODE vs DATA (the contract the bundle must honor)

- The frozen exe is **CODE only**: runtime + deps + app-py/mcp-server source.
- User **DATA** (`~/.local/share/metis/metis.sqlite`, knowledge indexes, notes…) lives
  outside the bundle and is **never** packaged. An update swaps the exe and leaves data
  untouched — ships-empty + update-without-data-loss still hold.

## Building (on Windows only)

```powershell
cd "<RepoRoot>\system\install\installer\pyinstaller"
.\build-bundled-exe.ps1
```

Produces `dist\metis\metis.exe` (+ `_internal\`). Must build on Windows — a WSL/Linux
build yields a Linux binary. The script smoke-tests `--version` and `doctor` at the end.

## Wiring into the Inno installer (TODO for the bundled `DefaultType`)

The packaging step still to be added to `metis-setup.iss`:

1. Add a `bundled` value to `DefaultType`. When `bundled`, **skip** the vendor-Python /
   pip steps in `[Run]`/`bootstrap_python.ps1`.
2. `[Files]` — lay the frozen runtime down under the install dir:
   ```
   Source: "pyinstaller\dist\metis\*"; DestDir: "{app}\runtime"; \
       Flags: ignoreversion recursesubdirs createallsubdirs; Check: IsBundled
   ```
3. Register the MCP server with Claude pointing at the frozen exe instead of a venv python:
   `command = {app}\runtime\metis.exe`, `args = ["mcp"]`.
4. Dashboard shortcut / autostart → `{app}\runtime\metis.exe dashboard` (launch hidden via
   the existing `autostart-dashboard.vbs` shim).
5. Keep the data dir resolution (`~/.local/share/metis/`) — the exe handles it via
   `config.resolve_live_db`; nothing OneDrive-synced.

## Status

⏳ **Spec + launcher + build script written and syntax/dispatch-validated; the actual
`.exe` has NOT been built or run** (requires a Windows Python host). The Inno `bundled`
DefaultType wiring above is the remaining step. Backlog: `F-INSTALL-06`.

## Known build watch-points

- **onnxruntime / tokenizers / pymupdf / pyreadstat / sqlite-vec** ship native libs or
  data files — `metis.spec` uses `collect_all` for each. If one is missing at runtime,
  add it to the `collect_all` loop or as a hidden import.
- **uvicorn[standard]** protocol/loop modules are listed as hidden imports — PyInstaller
  can't see them through uvicorn's lazy `auto` loaders.
- **Antivirus false positives** — UPX is disabled in the spec for this reason. Consider
  code-signing the exe before public release.
- `console=True` because the MCP server needs a real stdio pipe; the dashboard is launched
  hidden through the VBS shim, so no terminal window flashes for the user.
