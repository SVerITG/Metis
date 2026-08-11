# Keystone P1.1 — Building the bundled Metis `.exe` (Windows only)

This is the one Keystone item that **cannot be built or verified from WSL/Linux** — PyInstaller
freezes native Windows binaries, so it must run on a **Windows machine with Python 3.10–3.13**.
Follow this on that machine. Everything else in Phase 1 (1.2–1.6) is already shipped.

Goal: a single double-click `MetisSetup-bundled-<ver>.exe` that a non-technical scientist runs with
**no Python, no WSL, no venv, no config-file editing**, and that leaves user data untouched on update.

## Prerequisites (on the Windows machine)
- [ ] Python 3.10–3.13 (`py --version`)
- [ ] `pip install pyinstaller`
- [ ] Inno Setup 6 (`ISCC.exe`) for wrapping the installer
- [ ] The repo checked out (OneDrive copy is fine)

## Step 1 — Freeze the app
```powershell
cd "...\Research Cortex\system\install\installer\pyinstaller"
.\build-bundled-exe.ps1
```
This runs `pyinstaller metis.spec` and smoke-tests `dist\metis\metis.exe`. Confirm:
- [ ] `dist\metis\metis.exe dashboard` starts the dashboard and it serves on http://127.0.0.1:8080
- [ ] `dist\metis\metis.exe mcp` starts the MCP server (stdio; it should not error on launch)
- [ ] `dist\metis\metis.exe doctor` runs

## Step 2 — Bundle the embedding model (Keystone P0.4, frozen-build variant)
The spec freezes `onnxruntime`/`tokenizers` but **not the model weights**, so a frozen exe would still
download ~200 MB on first use. Pre-bake it:
- [ ] Before/So during build, run once online: `py -c "from fastembed import TextEmbedding; TextEmbedding('nomic-ai/nomic-embed-text-v1.5-Q')"` to populate `%LOCALAPPDATA%\fastembed` (or the repo cache).
- [ ] In `metis.spec`, add the fastembed cache dir to `datas` so the model ships inside `dist\metis\`, and set `FASTEMBED_CACHE_PATH` to that bundled dir in `metis_launcher.py` (both `dashboard` and `mcp` subcommands) so search works offline from first run.
- [ ] Verify: with the machine offline, `metis.exe dashboard` → semantic search returns results.

## Step 3 — exe-based MCP registration (currently a TODO — README lines 59-60)
The bundled path has **no** MCP registration yet. Add it (native Windows, so **no `wsl -d` ambiguity**):
- [ ] Register Claude Desktop: write `%APPDATA%\Claude\claude_desktop_config.json` →
      `"metis-rc": { "command": "{app}\\runtime\\metis.exe", "args": ["mcp"], "autoApprove": ["*"] }`
      (create the `Claude` dir if Desktop was never opened — mirror Keystone P1.2 / N3).
- [ ] Register Claude Code: `claude mcp add metis-rc "{app}\runtime\metis.exe" mcp` (if the Claude CLI is present).
- [ ] Do this from the Inno `[Run]` section (a small `register-mcp.ps1`), NOT via WSL.

## Step 4 — Inno `bundled` installer type
- [ ] In `system\install\installer\metis-setup.iss`, add a `bundled` `DefaultType` that:
      skips the vendor-Python / pip steps, lays `dist\metis\` into `{app}\runtime`, runs the
      Step-3 registration, and runs the terminal/dashboard wizard.
- [ ] Honor **ships-empty + update-without-data-loss**: the installer packages CODE only; user data
      stays in `%LOCALAPPDATA%\metis` (or the configured data dir) and is never overwritten on update.

## Step 5 — Windows-only parts of Keystone P1.6 (detect/offer WSL + Desktop)
- [ ] In `install.ps1`: if WSL is absent, **offer** `wsl --install` (with a reboot note) rather than only printing it.
- [ ] If Claude Desktop is absent, offer `winget install <verified-Claude-id>` (confirm the exact winget id first) or open https://claude.ai/download.
- [ ] Reconcile the two Desktop-registration writers (Keystone N1): for the bundled/native path use the
      Step-3 native-exe registration and do NOT also write the WSL form — one writer, one final config.

## Step 6 — Compile + verify the installer
```powershell
$ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
& $ISCC "/DDefaultType=bundled" "/DMyAppVersion=1.0" "system\install\installer\metis-setup.iss"
```
Acceptance (in a clean Windows Sandbox — the real test):
- [ ] Double-click the exe → installs with no Python/WSL prompts
- [ ] Dashboard serves; the **wizard self-check (Keystone P1.3) shows all green**
- [ ] Claude Desktop lists `metis-rc` and a test question reaches Metis
- [ ] Semantic search works **offline** (model was bundled)
- [ ] Run the installer again over the top → user data still intact

## Then
Label it the **headline download** on the GitHub release (bundled = end users; Inno/Docker/sh = developer installs),
and run the **Release Gate** workflow (Keystone P0.8) before publishing. Update the Keystone Roadmap P1.1 status.
