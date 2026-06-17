# Metis v1.0 Release Checklist

Manual verification steps before tagging a release. Work through each section in order.
A CI workflow (`build-installer.yml`) runs automatically when a `v*` tag is pushed.

---

## 1. Environment

- [ ] Python 3.10+ is active (`python --version`)
- [ ] `METIS_DB` points to a valid SQLite file (`echo $METIS_DB`)
- [ ] `METIS_RC_ROOT` points to the repo root (`echo $METIS_RC_ROOT`)
- [ ] All required packages installed (`pip install -r system/app-py/requirements.txt`)
- [ ] MCP server venv exists (`ls system/mcp-server/.venv/`)

---

## 2. Test suite

Run from the repo root (WSL terminal):

```bash
pytest tests/unit/ tests/integration/ tests/red_lines/ -v
```

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All red-line tests pass
- [ ] No tests skipped due to import errors (check for "fastapi not installed" skips)

Persona workflow tests (slower — run separately):

```bash
pytest tests/personas/ -v
```

- [ ] All 10 persona clients build successfully
- [ ] All persona primary tab tests pass
- [ ] All persona partial tests pass

---

## 3. Dashboard smoke test (manual, browser)

Start the dashboard:

```bash
bash system/app-py/run.sh
# Open: http://127.0.0.1:8080
```

Walk through each tab:

- [ ] **Today** — greeting renders, no 500 errors in terminal
- [ ] **Knowledge** — library cards and literature table load
- [ ] **Meetings** — meeting list renders (empty is fine)
- [ ] **Learning** — course progress bars render
- [ ] **Work** — task list renders, priority colours visible
- [ ] **Thinking** — ideas and open questions render
- [ ] **Planner** — kanban columns visible
- [ ] **Teach** — course cards render
- [ ] **Metis** — agent run history table, system info panel

Additional:

- [ ] Capture modal opens with `Ctrl+K` (or via the toolbar button)
- [ ] Typing `i: ` prefix in capture modal shows "idea" label
- [ ] `/health` endpoint returns `{"status":"ok"}` (`curl http://127.0.0.1:8080/health`)
- [ ] Startup eval results file written (`cat system/config/eval-results.json`)

---

## 4. MCP server smoke test

In a Claude Desktop or Claude Code session with `metis-rc` registered:

- [ ] `list_tools()` returns 76+ tools (no error)
- [ ] `get_user_profile()` returns user config (or empty dict — not an error)
- [ ] `session_bootstrap()` returns a dict with `plan_status` key
- [ ] `get_memory_health()` returns a health report string

---

## 5. Windows installer (requires Windows runner)

Trigger the GitHub Actions workflow manually:

1. Go to `Actions → Build Windows Installer → Run workflow`
2. Enter version: `1.0`
3. Wait for completion

- [ ] Workflow completes without error
- [ ] Full installer artifact is available for download
- [ ] Standard installer artifact is available for download
- [ ] Minimal installer artifact is available for download
- [ ] Run `MetisSetup-full-1.0.exe` on a clean Windows machine
- [ ] Choose "Full" installation type
- [ ] Start Metis via the Start Menu shortcut
- [ ] Dashboard opens at `http://127.0.0.1:8080`

---

## 6. Documentation

- [ ] `README.md` version badge shows `v1.0`
- [ ] `README.md` agent count is accurate (34 agents)
- [ ] `README.md` MCP tool count is accurate (76+)
- [ ] `CONTRIBUTING.md` clone URL is correct
- [ ] `system/config/release-notes-v1.0.md` exists and is complete
- [ ] `CHANGELOG.md` (if present) has a v1.0 entry

---

## 7. Git and GitHub

- [ ] All changes committed (`git status` is clean)
- [ ] Branch is `main` (`git branch --show-current`)
- [ ] Local is ahead of or equal to remote (`git status` shows "up to date")
- [ ] Push to remote: `git push origin main`
- [ ] Create and push v1.0 tag:

```bash
git tag v1.0 -m "Metis Research Cortex v1.0"
git push origin v1.0
```

- [ ] GitHub Release is created automatically (or create manually via `gh release create`)
- [ ] Release notes reference all three installer variants
- [ ] Docker instructions in release notes are correct

---

## 8. Post-release

- [ ] Announce in relevant channels (if applicable)
- [ ] Update `system/config/implementation-progress.json` — mark Phase 12 complete
- [ ] Open backlog ticket for v1.1 (Phase 10 APScheduler + Docker publish)
- [ ] Archive this checklist with date: `git mv system/config/release-checklist.md system/config/release-checklists/v1.0-$(date +%Y-%m-%d).md`

---

*Checklist version: v1.0 · Last updated: 2026-05-18*
