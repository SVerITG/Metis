# The Metis Keystone Roadmap

> **Reference name:** "the Keystone plan" / "Keystone Roadmap". A keystone is the stone that
> makes an arch hold together — this plan's job is to turn Metis's many strong-but-separate
> pieces into one coherent, professional, always-works whole. Built section by section across
> sessions; cite a phase number (e.g. "Keystone P0.1") when picking up work.

**Authored:** 2026-08-10, from a senior-engineer review of the whole system.
**Method:** eight parallel deep-dive analysis agents (stability, install, backgrounds, settings/updates,
memory/agents/cross-pollination, stack/Office, README-vs-reality completeness, self-reflexion) +
direct code reading, cross-checked against the README's promises, the feature-backlog, conversation
memory, and the owner's stated evaluation philosophy.
**Companion docs:** `data-persistence-strategy.md` (CODE/DATA contract), `metis-self-reflexion-prompt.md`
(the audit doctrine), `feature-backlog.md` (raw request log). Full gap register in Appendix A.
**Merged in (2026-08-12):** the senior-engineer surface review that ran as "Phase S" is now folded in
here (see **PHASE S**) and its old plan file is superseded — this roadmap is the single source of truth.

---

## Latest status — 2026-08-12 (session 2) — read this first

**M1 IS SHIPPED.** The memory write-backs now run on the dispatch chokepoint, not the pipeline.
Commits (local): `7dc0d2e` hooks · `a242c26` decorator drift · `eec122f` **M1**.

**What changed.** `middleware.py` already wraps `FastMCP.call_tool` for security; memory continuity
now rides the same wrapper via the new `ambient.py`. Four things became structural: the **session
registry** (first tool call resumes/opens a client-tagged session), **session events** (every call
leaves a breadcrumb), **session-id injection** (`log_agent_run`/`write_reflexion`/`save_session_summary`
get the session id the model never passes), and **agent liveness** (`get_agent_context` opens the
'running' row). Breadcrumbs write on a background thread: inline cost +15.9 ms/call, queued +0.6 ms.
Verified end-to-end against the installed server with no pipeline in the test —
`session_events` went from **0 (all-time) → live rows**, and a `log_agent_run` with no `session_id`
closed the running agent row.

- **M1 ✅ DONE** · **M3 ✅ DONE** (client-tagged registry revived; `detect_client()` reads it from the
  process environment — Code launches the server under `claude` with `CLAUDE_CODE_SESSION_ID`, Desktop
  goes through the WSL Relay chain) · **P6 · B6.1** and **P3 · 3.3** now genuinely reachable, since the
  code that was correct-but-unreached is now on the always-hit path.
- **Two tools had silently lost registration** to decorator drift — `session_bootstrap` (broken by
  yesterday's S.6 commit) and `kg_index_notes`. The tool *count* was unchanged both times, so the
  count-based smoke check missed both. It now asserts names, plus "no private helper may be a tool."
- **Hook fix:** the "hook cancelled" error on exit was the SessionEnd hook doing a blocking `git push`
  while Claude Code was quitting. The push is now detached; failures surface at the next session start.
  Explicit timeouts pinned on the three slow hooks.

**⚠️ CORRECTION to Appendix C.4 — the `decisions` finding was wrong.** The table is **not** absent; it
is named **`user_decisions`** and the census grepped for `decisions`. It exists, holds 1 row, last
written 2026-06-22. **M5 is therefore not "create the table" but "capture is thin"** — the same
convention problem as everything else, at much lower severity. (`routing_preferences` likewise does not
exist under that name; the real table is `agent_routing_rules`, 127 rows.)

**Still open:** rotate the exposed Anthropic API key (C10) — owner is doing this via the dashboard's
own settings UI, deliberately, as a first-run UX test. M2, M4, M6, M7 untouched. P1.1 bundled `.exe`,
P2.3/2.4/2.6, P4, and the 3.0 architectural decision all unchanged.

---

## Status — 2026-08-12 (session 1)

**Where we stand at a glance:** P0 ✅ · P1 ~85% (bundled `.exe` is the one big gap) · P2 🟡 advanced ·
P3 ✅ except two architectural pieces · P4 ⬜ · P5 ⬜ · P6 🟡 (caching/compaction/tiering left) ·
**PHASE S ✅ shipped today**.

**Shipped this session (2026-08-12) — the Metis Systems surface overhaul + memory checks.** Three
commits on `main`, **local only, not pushed yet**: `af7ddc2` (surface reshape), `31ed255` (live
monitoring + honest tokens + Desktop learning loop), `c911818` (Sessions panel + Health Check + doctor
checks). Full detail in **PHASE S** below. This also advanced existing Keystone items:
- **P6 · B6.1 → COMPLETE** — the dispatch-write that sets `agent_runs.status='running'` now exists, so
  live "who's working" is real end-to-end (was "display-ready").
- **P3 · 3.3 → PARTIAL** — the MCP-server-side learning loop (aggregate→consolidate→draft, throttled
  once/~20h in `session_bootstrap`) now runs, so Desktop-only users get the loop. *Caveat below.*
- **P2 · 2.1/2.2 → substantially done** — the two named incoherences (theme dual-write/single-read;
  model "selected" hardcoded to Sonnet) are fixed; the duplicate Memory surface is merged; scattered
  settings collapsed into one Appearance & Settings section.
- **New:** a one-click **Health Check** (runs the full doctor in plain language, no terminal) and a
  **Sessions panel** — plus two new doctor checks (session-memory-active, projects-registered).

**Honest caveat (from the memory evaluation, Appendix C):** S.2 and S.6 live inside
`run_metis`/`session_bootstrap`, and the DB shows that pipeline is **barely exercised** (`session_events`
= 0; `sessions` registry frozen since May). So these hooks are correct but only pay off once the
pipeline is actually invoked — the same P3 "convention → construction / is `run_metis` even called?"
gap. **Full memory-system evaluation is Appendix C.**

**Do-next housekeeping:** (1) `/mcp` reconnect to load the server-side pieces; (2) push the three
commits to `metis-ph` + regenerate the `origin` base via the Release Coordinator; (3) still open:
rotate the Anthropic API key printed to a transcript (C10).

---

## 0. Executive verdict (the honest headline)

Metis is **not** amateur software. The runtime supervision, the CODE/DATA boundary, the resilient
MCP tool-loading, the local-embeddings RAG, and the reliability test-suite are genuinely mature,
incident-driven engineering. A senior engineer's real concerns are **not** the architecture — they
are concentrated in five places:

1. **Fresh-machine / first-run edges** — a silent empty-DB data-loss bug (N9), embedding model not
   pre-fetched (RAG silently off), install-automation bugs (multi-distro `wsl -d`, racing Desktop
   registration), and a wizard that declares success without proving anything works.
2. **The "seamless, non-technical" promise** — the one true double-click installer (bundled `.exe`)
   is **scaffolded but never built**; today every path still assumes some technical setup.
3. **The "ambient second brain" promise** — ingestion-side cross-pollination is real and near
   state-of-the-art, but **recall** into new requests is shallow (recency + substring, bypassing the
   768-d vector layers) and the **self-improvement loop is scaffolded but open** (reflexion capture
   is unenforced; proposal-drafting isn't scheduled; an applied skill edit may not reach the runtime
   that serves the agent).
4. **Coherence** — settings are scattered across the Metis tab, the wizard, and ~40 hand-edited
   config files, with real duplications (theme, persona, preferences); there is no single Settings
   pane and no in-app update button.
5. **Backgrounds are not plug-ins yet** — the layer *data model* is solid, but there is no
   install/enable/disable/update/delete of a **portable** background pack; a working lifecycle for
   exactly this already exists in the `content_packs` (courses) subsystem and should be generalized.

**MCP verdict (the re-evaluation you asked for):** MCP was the **right** choice for the Claude-facing
backbone — keep it. It is stdio/Claude-only by nature, so Office (PowerPoint/Excel) integration
attaches via an **additive local HTTP layer over the same SQLite brain**, not a replacement. The
Office groundwork is further along than expected: PPTX generation, Excel I/O, and a file-watcher
skeleton already exist.

**Bottom line:** the gap between what Metis *is* and what a professional team would ship is real but
**closable** — it is mostly hardening edges, finishing the installer, and closing two loops (recall,
self-improvement), not rebuilding. This roadmap sequences that work so each phase leaves Metis
demonstrably more "it just works."

---

## 1. Guiding principles (how we build, not just what)

- **Workflow-first, not status-code-first.** "A 200 is not a passing workflow." Every item below has an
  acceptance test phrased as *what a scientist can now do end-to-end*, verified against the running
  system (curl/click/render), not by reading code. (Owner's standing evaluation rule.)
- **Truth by construction, not by convention.** Where a promise currently depends on the LLM
  *choosing* to do something (recall, reflexion), make it architectural. Convention is where drift hides.
- **CODE/DATA boundary is sacred.** Code ships and updates; user data persists untouched. Every change
  honors `data-persistence-strategy.md` (ships-empty, additive migrations, data-dir list).
- **Declutter via progressive disclosure — the update-menu pattern.** The update-button→popover we
  built (`partials/_update_menu.html`) is the template: collapse scattered always-visible controls into
  one clear action that reveals choices on demand, with honest labels ("no API tokens" vs "uses
  credit"). Apply this pattern to settings and every crowded surface.
- **Non-technical by default, powerful underneath.** No feature is "done" if using it requires editing
  a file. Power users keep file/JSON access; scientists get a button.
- **Continuous, visible self-evaluation.** Bake the owner's audit doctrine in: a weekly deterministic
  harness (pass/hard-fail/partial) + a drift heatmap, surfaced in the UI, so "have we lost what we
  built?" becomes a live indicator, not a manual investigation.
- **Every phase ends green.** Zero hard-fails on the promise harness, persona linter clean, and the
  phase's own acceptance tests pass, before moving on.

---

## 2. The roadmap

Effort: S (hours) · M (1–3 days) · L (1–2 weeks) · XL (multi-week). Impact: ★–★★★.

### PHASE 0 — Stability & data-integrity hardening ("never lose data, never fail to start")
*The foundation is strong; these are the sharp edges that betray it on a fresh or unlucky machine.*

> **Status: ✅ COMPLETE (2026-08-11)** — all items built + verified against real failure
> scenarios, on `metis-ph`: `e2f7ed2` (P0.1/0.2 DB guard + graceful degrade), `7cccacb` (P0.3/0.5/0.7
> handshake, migrator busy_timeout, port-exhaustion), `e3fe09d` (P0.6/0.4 MCP rotating log +
> embedding pre-cache), `20691d8` (P0.6b/0.8 live-health badge + release-gate workflow). MCP server
> reinstalled + smoke HEALTHY. `origin` (base) pending its next generated-shell push.

| # | Item | Why / evidence | Files | Size·Impact |
|---|---|---|---|---|
| 0.1 | **Fix the silent empty-DB bug (N9)** | `db.py` (dashboard) picks the DB with plain `.exists()`; `config.py` (MCP) was hardened with `_is_usable_db()`. A 0-byte OneDrive artifact → dashboard migrates an empty DB → "everything gone." | `system/app-py/db.py:100`; mirror of `mcp .../config.py:60-88,167-170` — extract ONE shared resolver both import | S·★★★ |
| 0.2 | **Make startup un-crashable (N1/N2)** | `run_migrations()` is the one unguarded lifespan step; `get_db_path().mkdir` raises on read-only/full disk → 8 restarts → give-up. DB helpers catch `OperationalError` but not `DatabaseError` (corruption) → every panel 500s. | `system/app-py/main.py:44`; `db.py:104,132,151` | S·★★★ |
| 0.3 | **Get the diagnostic doctor off the MCP handshake path (N3)** | `run_doctor()` + `filecmp` over every source file + DrvFs globs run synchronously before `app.run()` → Claude Desktop can hit its MCP `initialize` timeout and mark `metis-rc` failed. | `mcp .../server.py:210`; `doctor.py:279-284,406-423`; `metis-preflight.sh:170` | M·★★★ |
| 0.4 | **Pre-fetch the embedding model at install (N4)** | Setup never warms the model; dashboard forces `HF_HUB_OFFLINE=1` → on a new machine semantic search is silently off until some online MCP embed happens first. | `setup-mcp.sh` (add warm-up); `run.sh:31-32`; `embeddings.py` | M·★★ |
| 0.5 | **One schema owner + busy_timeout on the MCP migrator (N6)** | Two uncoordinated migration runners on one DB; `migrations.py` opens with no busy_timeout → "database is locked" skips ALTERs. | `system/app-py/db.py:193`; `mcp .../migrations.py:121` | M·★★ |
| 0.6 | **Surface real MCP health + real logs (N11/N12/R3)** | `mcp-health.json` (the serving process's `FAILED_MODULES`) is written but never read; MCP has no logging config so INFO health lines vanish. Dashboard `/api/doctor` runs a *fresh* doctor in the *dashboard* process — it can't see what failed in the live server. | `mcp .../server.py:131-189`; surface on `base.html` badge; add rotating file log | M·★★ |
| 0.7 | **Port-exhaustion + foreign-holder clarity (N5)** | 8080–8090 all busy → prints 8080 anyway → bind fails → crash-loop → give-up, no explanation. | `system/app-py/run.sh:266,318,331` | S·★ |
| 0.8 | **Release gate** | Run `tests/reliability` + the container smoke matrix + promise harness on every release; add a minimal frozen-exe smoke (import + `/health` 200) (R4). | `tests/reliability/`, release-coordinator `test-containers`, CI | M·★★ |

**Phase 0 acceptance:** on a read-only-`$HOME` VM and on a 0-byte-artifact restore, the dashboard
starts and shows a clear message instead of crash-looping or coming up empty; a corrupt DB degrades
gracefully; Claude Desktop connects to `metis-rc` within its timeout on a cold start; a fresh machine
has working semantic search after install with no online step; the dashboard health badge shows the
live server's failed-module count.

### PHASE 1 — Seamless install & first-run ("works on my computer, no technical steps")
*The single biggest gap versus "a scientist just runs it."*

> **Status (2026-08-11): 1.2 ✅ · 1.3 ✅ · 1.4 ✅ · 1.5 ✅ · 1.6 ✅ (WSL side) shipped to metis-ph.**
> `2d6a84d` (1.2 correct Claude Desktop registration incl. multi-distro `-d`; 1.4 wizard writes the
> truth — model fallback, populated projects, live-DB path, port docs, empty-topics YAML fix),
> `2695100` (1.3 wizard self-verification gate: `/api/setup/verify` + green-checks finish),
> `9f1eafa` (1.5 one-click "adapt Metis to my work" claude:// deep link; 1.6 offer to open the Claude
> Desktop download). Dashboard route changes (1.3) need a dashboard restart to go live.
> **Remaining — Windows host only:** 1.1 bundled `.exe` + the winget/WSL-install + native-exe MCP
> registration parts of 1.6. Step-by-step in `system/install/installer/pyinstaller/BUILD-CHECKLIST.md`.

| # | Item | Why / evidence | Files | Size·Impact |
|---|---|---|---|---|
| 1.1 | **Build & ship the bundled `.exe`** | The only truly non-technical installer; scaffolded, never built. Must bundle the embedding model and register MCP pointing at the frozen exe. Needs a Windows Python host. | `system/install/installer/pyinstaller/` (spec, launcher, build ps1, README:59-60); Inno `bundled` DefaultType | L·★★★ |
| 1.2 | **Fix MCP auto-registration bugs** | Auto-registration EXISTS (setup-mcp.sh/install.ps1) but: two rival Desktop strategies race (N1); the WSL writer omits `-d <distro>`/`wsl.exe`/`bash` — the exact multi-distro bug memory warns of (N2); registration skipped if Desktop never opened (N3); an ineffective `"projects"` writer risks corrupting the config (N4). | `setup-mcp.sh:561-587`; `windows/install.ps1:254-318`; `project_tracker.py:420-441` | M·★★★ |
| 1.3 | **Wizard self-verification gate** | Wizard declares "configured" with zero proof. `run_doctor()` (15 checks incl. Desktop link) exists at `GET /api/doctor` but the wizard never calls it. Turn finish into a green-checks panel with one-click Fix/Retry. | `templates/setup.html:627-659`; `routers/setup.py:87-119`; reuse `doctor.py:426-445` | M·★★★ |
| 1.4 | **Fix the wizard's own truthfulness bugs** | Empty `projects: []` always written (N5) so "projects" never shows complete; DB-path split-brain — wizard writes to `app-py/data` while server reads the off-OneDrive live DB (N6); stale `claude-opus-4-7` model id silently degrades the persona generator (N7); docs say `:8000`, app is `:8080` (N8). | `process_wizard_answers.py:135,310,331`; `claude-project-wizard.md:44` | S·★★ |
| 1.5 | **One-click "Adapt Metis to my work"** | The building blocks exist (`claude://` deep links; `detect_projects`, `connect_project_folder`, `scan_project_scripts`, `analyze_script`, profiling tools) but the wizard only does a shallow folder scan. Net-new = one button + an orchestration prompt that opens Claude to run detect→connect→scan over the user's folders and writes back profile+projects. | `tools/projects.py:477`, `files.py:258`, `script_analyzer.py:365`; `app.js:1065` | M·★★★ |
| 1.6 | **Installer detects/offers Claude Desktop + WSL** | Today WSL absence only prints instructions; Desktop is assumed present (download URL only). Detect and guide/inline-install. | `windows/install.ps1:312-318`; `setup-mcp.sh:500-513` | M·★★ |

**Phase 1 acceptance:** on a clean Windows VM, a non-technical user double-clicks one installer,
never edits a file, sees green self-test checks, Claude Desktop lists `metis-rc` (correct on a
multi-distro machine), and can click "Adapt to my work" to auto-populate projects from their folders.

### PHASE 2 — Coherence & declutter ("one calm, professional surface")
*Apply the update-menu principle broadly; end file-editing for settings; make updates a button.*

> **Status (2026-08-12): 2.2 ✅ · 2.1 partially done** via the Metis Systems surface overhaul (see
> PHASE S). Fixed: theme dual-write/single-read (now reflects saved), model "selected" hardcoded to
> Sonnet (now reflects saved), merged the duplicate Memory surface, collapsed scattered controls
> (feature-tips, autostart) into one Appearance & Settings section, deleted dead routes. **Remaining:**
> the fuller single Settings pane spanning the wizard too (2.1), generalize the update-menu pattern
> (2.3), the in-app "Update now" button (2.4), file-only-settings-as-UI (2.5), self-host CDN assets (2.6).

| # | Item | Why / evidence | Files | Size·Impact |
|---|---|---|---|---|
| 2.1 | **A single Settings surface** | Settings are spread across the Metis tab (12 sections), the wizard (13 sections), ~40 config files, and a chat layer. Consolidate into one coherent, searchable pane; keep chat + file access for power users. | `routers/metis_tab.py`, `setup.py`, `templates/metis_tab.html` | L·★★ |
| 2.2 | **Fix settings incoherences** | Theme dual-write/single-read (server copy dead); persona split across `user-config.yaml` + `user-preferences.json` with overlay drift; duplicate preference files; model "selected" hardcoded to Sonnet; the `/metis-update` (data) vs `metis-update.sh` (code) name collision. | `metis_tab.py:399-423,1131`; `base.html:39-45,571`; `metis_tab.html:320` | M·★★ |
| 2.3 | **Generalize the update-menu declutter pattern** | Reuse `partials/_update_menu.html` to collapse crowded control clusters across surfaces into one action + on-demand popover with honest labels. Inventory every button first. | `partials/_update_menu.html`; all surface templates | M·★★ |
| 2.4 | ~~**In-app one-command update (safe)**~~ **✅ SHIPPED 2026-08-12** (`2e9dd13`) — `tools/metis_update.py`: record commit + row counts for 16 guarded tables → SQLite-backup-API snapshot (WAL-safe) → pull → reinstall + additive migrate → verify by re-counting → **automatic rollback** (restore commit, restore DB, reinstall) if any table shrank or the health check fails. Refuses on a dirty tree, because rollback does `git reset --hard` and a tool promising "it can always undo itself" must decline the one case where it cannot. Dashboard: Update section with Check-only / Update, detached with status polling. |  `tools/metis-update.sh` exists but is terminal-only (non-tech user can't update), backs up only the DB (not the full data-dir list), doesn't run full migrations, and has no rollback/atomicity. Make it a dashboard "Update now" button: backup all data dirs → pull → additive migrate → verify → auto-rollback on failure. | `tools/metis-update.sh`; `backup-canonical.py`; `data-persistence-strategy.md:§2,§4` | M·★★★ |
| 2.5 | **Expose file-only settings as UI or accept as power-user-only** | `network-policy.json`, `models.yaml`, `tool-subsets.json`, `agent-registry.json`, governance docs are hand-edited. Decide per item: promote to UI (non-tech) or label explicitly power-user. | `system/config/*.json` | M·★ |
| 2.6 | ~~**Self-host CDN assets (A11/C19)**~~ **✅ SHIPPED 2026-08-12.** Bootstrap CSS, the Bootstrap JS bundle, Bootstrap Icons and D3 now serve from `/static/vendor/`, icon font files included (vendoring the icons CSS alone would have left every icon broken — it resolves `fonts/` relative to itself). `integrity`/`crossorigin` stripped: an SRI hash on a same-origin file is meaningless and can block it. The persona linter skips `/static/vendor/` — a 230 KB single-line minified bundle made its per-line pass slow enough to time out the commit. Verified: rendered HTML of `/`, `/knowledge`, `/work` contains no external asset reference. | `templates/base.html`, `course_reader.html`, `partials/knowledge_graph.html`, `static/vendor/` | S·★★ |

**Phase 2 acceptance:** a scientist changes any setting from one pane without editing a file; theme/
persona/model persist consistently across machines; "Update now" is a button that backs up, updates,
verifies, and rolls back on failure; the app loads fully offline.

### PHASE 3 — The ambient second brain ("nothing lost; it gets sharper on its own")
*Close the two open loops so the flagship promise is true by construction.*

> **Status (2026-08-11): 3.1 ✅ · 3.4 ✅ · 3.9 ✅ · 3.10 ✅ shipped to metis-ph.**
> `9bea309` (3.1 — pipeline Stage 7 runs question-conditioned hybrid vector+keyword recall over the
> real corpus, by construction), `807ada4` (3.10 — shared `_embed_episodic`; dashboard-captured ideas
> vector-indexed like chat), `2d17f9d` (3.9 — `cross_pollination_links` persisted at ingestion so the
> graph accrues), `e119249` (3.4 — `get_agent_context` now reads `skill.md`, so an applied
> self-improvement actually reaches the runtime). All verified live.
> Also shipped: `20ce01a` (3.7 — semantic fallback router, score-floor + margin, zero mis-routes),
> `ac725ee` (3.6 — token-budgeted context, ~1800-char ceiling, prefs-first), `85ade45` (3.2 — enforce
> reflexion write-back on uncovered turns + fix uncovered semantics for semantic-routed turns).
> **9 of ~10 Phase-3 items shipped & verified** (3.1/3.2/3.3/3.4/3.5/3.6/3.7/3.9/3.10). MCP smoke HEALTHY.
> ✅ **3.0 — RAG grounding slice SHIPPED** (`f250ede`): `run_metis` now actually calls
> `search_pdf_knowledge` over the library/backgrounds for research/substantive turns and injects the
> top cited chunks BY CONSTRUCTION (gated so quick chatter stays fast; verified live — a literature
> question and a deep "methods" request both get real cited chunks; trivial chit-chat does not).
> ✅ **3.0 — hand-off slice SHIPPED** (`39d8729`): `run_metis` inlines the routed specialist's
> system-prompt ("Adopt this specialist's approach (<slug>)") by construction (real specialists only;
> verified live). **So the pipeline now GROUNDS in the library AND ADOPTS the specialist by
> construction — the two deepest convention→construction gaps are closed.**
> **Architectural boundary (honest finding):** the last two 3.0 pieces — **binding model-tiering** and
> **true conversation compaction** — cannot be done in the current stdio-MCP model because the MCP
> server does NOT make the answer's model call (the calling Claude client does). Delivering them
> requires a foundational decision: either move primary answer generation server-side (the server
> calls the API, applies the budget model, compacts) or adopt the client's compaction API. That's a
> strategic architecture choice, not more wiring — scope it deliberately.
> ✅ **3.8 SHIPPED** (`0f9bf6a`): weekly `job_promise_harness` records the harness score to
> `promise-trend.jsonl`; a "Promise drift" strip on the Metis tab shows the latest pass/fail/warn +
> a per-run green/red history — "have we lost what we built?" is now a live indicator.
> ✅ **3.3 second half closed (2026-08-12, `31ed255`)**: the "trigger consolidation opportunistically
> from the MCP server so Desktop-only users get the loop" gap is now filled — `session_bootstrap` runs
> aggregate→consolidate→draft once per ~20h (throttled via `learning_loop_state`). ~~*Caveat: gated on `session_bootstrap` actually being called.*~~ **Caveat RESOLVED by M1**: `ambient._start_learning_loop_once()` fires the loop on the first tool call of any server process, so it no longer depends on the pipeline being reached at all.
> **Phase 3 is COMPLETE.** The two architecturally-bounded 3.0 pieces (binding model-tiering, true
> compaction) were resolved by DECISION rather than by code: **owner chose Option B on
> 2026-08-12 — accept the limit, keep tiering advisory, and be honest about it.**
> Rationale: Option A (move primary answer generation server-side so Metis makes the model call,
> applies the budget and compacts) is a foundational change to what Metis is and changes the cost
> model, for a benefit felt mainly on very long sessions. Everything else on the roadmap delivers
> more per hour of work. Recorded in `models.py:model_for` at the source, so the next reader meets
> the limit where they would otherwise assume enforcement. **Do not re-litigate without new
> reasons** — revisit only if Metis gains its own answer-generation path for another reason.

| # | Item | Why / evidence | Files | Size·Impact |
|---|---|---|---|---|
| 3.1 | **Automatic rich recall in context assembly** | Stage-7 auto-recall injects only recency + `LIKE '%first 60 chars%'` over `memory_entries`, bypassing the 768-d vector layers. Replace with the existing `recall()` RRF hybrid + recent reflexion lessons for the routed agent. Converts "ambient recall" from convention to guarantee. | `pipeline.py:746-794`; reuse `memory_gateway.recall`, `vector_memory.semantic_search` | M·★★★ |
| 3.2 | **Enforce reflexion capture server-side** | `write_reflexion` fires only if the model remembers; `run_metis` just prints a reminder → the loop starves. Auto-write a lightweight reflexion from the session_events trace at result time. | `pipeline.py:1046-1069`, `save_session_event`; `self_improvement.py:263` | M·★★★ |
| 3.3 | **Schedule proposal drafting + move consolidation off the dashboard** | `draft_self_improvement_proposal` is never scheduled; consolidation/"dreaming" only runs under the dashboard scheduler (Desktop-only users get none). Schedule drafting beside evening reflexion; trigger consolidation opportunistically from the MCP server. | `scheduler.py:423-464`; `improvement.py:253,343` | M·★★ |
| 3.4 | **Make an applied improvement actually reach the runtime** | Three divergent `_skill_path` resolvers; `get_agent_context()` reads only `agents/<slug>/system-prompt.md`, not the `.claude/skills/.../skill.md` a proposal may rewrite → "applied" ≠ "in effect." Unify; add a test: apply proposal → next `get_agent_context` contains the new text. | `self_improvement.py:51`, `improvement.py:75`, `agents.py:47` | M·★★ |
| 3.5 | **Surface the loop + startup eval in the UI** | `startup_eval.py` writes `eval-results.json` read by nothing; the self-improvement surface should show reflexions captured, themes past the ≥3 gate, pending drafts, applied learnings — one-click approve/reject with a visible backup + revert. | `startup_eval.py`; `metis_tab.py:543`; new health strip | M·★★ |
| 3.6 | **Token-budgeted retrieval** | Injected context is unbounded/uncounted (5×120 chars arbitrary); `_allocate_budget` only sets the model. Add importance/recency-decay ranking to a token budget. | `pipeline.py:739-771` | M·★ |
| 3.7 | **Semantic/LLM fallback router for `uncovered` turns** | Lexical rules reach ~21/35 agents; the rest are unreachable. Add an embedding fallback over agent descriptions (local embeddings already present) behind the fast deterministic first pass. | `pipeline.py:504-559`; `data-persistence-strategy.md:80` | M·★★ |
| 3.8 | **Continuous self-eval harness + drift heatmap (visible)** | Bake in the owner's doctrine: run the promise harness + clickthrough/orchestration/routing/probes weekly; chart `promise-trend.jsonl` (30/22/5 → 54/0/3 → 63/0/3 …) so regressions surface between quarterly audits. | `tests/functional/`, `metis-self-reflexion` skill; new dashboard trend strip | M·★★★ |

**Phase 3 acceptance:** a fresh session that references prior work has relevant memory surface with no
explicit recall call; running a work agent leaves a reflexion without being told to; a theme recurring
≥3× auto-produces a pending proposal in the UI; approving it provably changes what the agent serves;
the dashboard shows a live "promises green/red" trend.

### PHASE 4 — Backgrounds as plug-ins ("enable the domains you want; update them")

> **Status (2026-08-12): slices 1 and 2 SHIPPED** (`556d154`, `56ccd57`). Owner asked directly
> whether the PH background was ready, whether questions can run through one or several backgrounds,
> and how backgrounds get updated. Honest answers at the time: all four layers **were** built and
> indexed (ph-background 57 docs / 9,593 chunks; epi-methods 19 / 5,479; ntd 7 / 970; hat-specialist
> 221 / 7,973), and multi-layer questions **did** work from chat and ranked correctly by relevance
> (cost-effectiveness → PH background; sampling design → epi-methods; post-elimination → HAT). But
> there was **no dashboard UI whatsoever** — not one route referenced `knowledge_databases` — no
> enable/disable, and **no update path at all**: dropping a PDF into a folder did nothing, forever.
>
> - **Slice 1 ✅** — `enabled` column (additive, DEFAULT 1), `set_knowledge_layer_enabled` tool,
>   `pending_pdf_count` staleness measure, and a Library-surface panel: every layer with documents,
>   passages, build date, papers waiting, plus ON/OFF and Rebuild. *The filter fix mattered more than
>   the column:* with no layers named, the search left `db_filter_ids` as None — no filter — and only
>   built a display-name map, so disabling a layer removed its NAME while its chunks were still
>   searched and returned as `db:1`. The first test "passed" by checking for the absent label.
> - **Slice 2 ✅** — `job_background_index` at 09:07 indexes papers added since the last build, right
>   after the library scan. Registered in JOB_FUNCS, JOB_LABELS **and JOB_DEFAULTS** — a job with no
>   schedule entry would exist, look complete, and never run.
> - **Slice 3 ✅ SHIPPED 2026-08-12** (`e833d60`, `c8ecce1`) — packs are real.
>   `list_background_packs` / `install_background_pack` (preview by default, confirm to fetch) /
>   `export_background_pack`, plus `delete_knowledge_database` (P4.4) so the lifecycle closes.
>   **Downloads are verified against the %PDF- magic bytes** — the first real install exposed why:
>   both WHO IRIS links returned a 755-byte DSpace *HTML page* with a 200 status, and the only check
>   was "size > 0", so they were saved as `.pdf` and reported as "2 downloaded". Indexing those would
>   have filled a layer with website markup that answers could cite. An install where nothing
>   downloaded no longer registers a layer. Ships one real pack (WHO HAT elimination monitoring, 4
>   open-access PLOS NTDs papers): install → nightly index → a query on case counts returns Table 1
>   of the 2017 paper. Manifest ships; PDFs are gitignored.
>   *(Historical note on slice 3's original framing:)* Today a background is a DB
>   row plus *local folder paths*; there is nothing to hand anyone. **Owner's decision (2026-08-12):
>   bundle a curated pack in the Metis repo** — a manifest of open-access sources, where installing
>   fetches and indexes locally. Keeps the repo small, avoids redistributing copyrighted PDFs, and
>   works for the published base edition. Follow the `content_packs` (courses) lifecycle, which
>   already does install/enable/update for this exact shape.
*The data model is sound; generalize the existing `content_packs` lifecycle to knowledge layers.*

| # | Item | Why / evidence | Files | Size·Impact |
|---|---|---|---|---|
| 4.1 | **Generalize `content_packs` → `pack_type='background'`** | A full enable/disable/install/remove lifecycle + UI already exists for courses — clone it for knowledge layers instead of building new. | `metis_tab.py:1606-1706`; `partials/metis_content_packs.html`; `schema.sql:503-511` | M·★★★ |
| 4.2 | **Add lifecycle columns + honor them** | `knowledge_databases` has no `enabled`/`version`/`embedding_model`/`embedding_dim`/`checksum`/`origin`; `search_pdf_knowledge` can't exclude disabled layers. | `knowledge_db.py:79-147,653-782`; `schema.sql:665-676` | M·★★ |
| 4.3 | **Per-background export + import (portable pack)** | Export is monolithic (all layers, no registry rows), and there is **no importer** — packs are always rebuilt from local PDFs, so prebuilt vectors never ship. Build a per-slug export (row + chunks + vec shadow + `manifest.json`) and a matching import with an embedding-model/dim compatibility gate + atomic install/rollback. | `export_knowledge_db.py:141-174` (no caller); new importer | L·★★★ |
| 4.4 | **Delete/archive a background** | No `delete_knowledge_database` — a custom layer is permanent. Add coherent removal (row + chunks + vectors + index-state). | `knowledge_db.py` (ends :927) | S·★★ |
| 4.5 | **Fix the post-ANN filter (scaling landmine)** | Search does global ANN then Python `db_id` filter → a narrow layer is starved as more backgrounds coexist. Move to metadata-filtered / per-layer ANN. | `knowledge_db.py:724-749` | M·★★ |
| 4.6 | **Base genuinely ships zero backgrounds** | `_seed_builtin_databases` unconditionally seeds 3 PH-flavored slugs even on base; `build-base-shell.sh` ignores knowledge entirely. Make seeding edition-aware. | `knowledge_db.py:79-147,183-196`; `build-base-shell.sh` | S·★★ |
| 4.7 | **Fix the `app/` vs `app-py/` DB path split-brain** | Exporter/wizard/server use three different DB path conventions — will bite import/export. Route everything through one resolver (see 0.1). | `export_knowledge_db.py:36-40`; `process_wizard_answers.py:331` | S·★★ |

**Phase 4 acceptance:** on a clean base (zero backgrounds), a scientist installs a background pack from
a file, sees it as an enabled card, toggles it off (excluded from search) and on, updates it to a newer
version without touching their data, and deletes it cleanly; a narrow-layer search returns its own
results even alongside large layers.

### PHASE 5 — Integrations & the second brain everywhere ("connected to what I actually use")
*Additive to MCP; the dashboard localhost HTTP service is the attach point.*

| # | Item | Why / evidence | Files | Size·Impact |
|---|---|---|---|---|
| 5.1 | **A JSON API layer on the dashboard** | The dashboard is already the only always-on local HTTP server over the brain (Origin-hardened, already serves `.pptx`), but most endpoints return HTML partials. Add a small JSON API + an add-in origin allowance. This is the non-Claude attach point (MCP stdio can't serve Office). | `system/app-py/main.py`, `routers/*`; pattern proven by `webhook.py` | M·★★ |
| 5.2 | **PPTX ingestion + template-aware generation** | Metis→PowerPoint already works (`_build_pptx`), but read-back doesn't exist and generation uses a blank layout. Add a pptx reader + ingestion tool; open a user template via `Presentation(template.pptx)`. | `routers/teach.py:482-502`; `python-pptx` already pinned | M·★★ |
| 5.3 | **Bidirectional file-watcher for Office artifacts** | The lowest-friction "flows back" trigger; the `inbox_watcher`/`scheduler` skeleton already classifies dropped files (but not `.pptx`). Extend to `.pptx/.xlsx` round-trip with provenance. | `inbox_watcher.py`; `scheduler.py:401` | M·★★ |
| 5.4 | **Office.js add-in (in-app UX, later)** | Taskpane calling the dashboard JSON API. Note the real friction: Office add-ins load over HTTPS in a webview → calling `http://localhost` is mixed-content/blocked → needs an HTTPS-localhost cert + manifest + CORS. | new add-in project; dashboard CORS | L·★★ |

**Phase 5 acceptance:** a PowerPoint template edited via Claude appears in Metis; changing that template
in PowerPoint updates Metis; every artifact carries provenance back to its source.

### PHASE 6 — Token efficiency, monitoring & agent transparency (added 2026-08-11, on owner request)
*Evaluation-first: prove the efficiency strategy actually works now that routing is real, confirm
monitoring is truthful in the dashboard, and make the agents' work visible to the user. Benchmark
against current best practice — run a WebSearch for up-to-date strategies before building (model
cascades / small-model routing, prompt caching, context compaction/summarisation with retention,
speculative/cascade routing, per-agent token attribution).*

> **Honest precondition:** today an "agent" is persona role-play by the top-level model given
> `get_agent_context`, not a separate model call — so per-agent token attribution and "who did what"
> depend on `log_agent_run` being called, and true per-agent model tiering only becomes real with
> **3.0** (pipeline executes/【hands off to】 agents). Phase 6 must state this honestly, not imply
> isolated sub-agent billing that doesn't exist yet.

**Evaluations (do FIRST, workflow-first, with evidence):**
- **E6.1 — Token-efficiency strategy actually holds.** Verify: (a) `_allocate_budget` really assigns
  lighter models by complexity (quick→Haiku, standard→Sonnet, deep/chain→Opus) and this reaches the
  actual call; (b) conversation **compaction** happens regularly *with retention of essentials*
  (max_turns guard + 80% auto-handoff brief `handoff.generate_handoff_brief`; session summaries;
  `job_memory_consolidation`) — measure what's kept vs dropped; (c) context is **surgical** (P3.6
  budget, P3.1 recall bounded, P3.7 routing avoids over-escalation). Produce a real before/after
  token/cost measurement on representative prompts, and a gap list vs the best-practice benchmark.
- **E6.2 — Monitoring is truthful + visible.** `routers/metis_tab.py::metis_token_monitor`
  (`/api/partial/metis/token-monitor`, `partials/metis_token_monitor.html`) exists — verify it shows
  REAL usage (from `agent_runs.input_tokens/output_tokens`, `token_footer`) and is not a stub or
  estimate; confirm it's reachable and accurate on the dashboard. Flag any place tokens are logged as
  0 / never written (the review found `log_agent_run` is behavioral — if agents don't call it, the
  monitor undercounts). Make token capture reliable (server-side) so the monitor reflects reality.

**EVALUATION RESULTS (run 2026-08-11, code trace + web benchmark):**

*Token efficiency (E6.1):*
- **Model tiering is real in DATA but ADVISORY in practice.** `_BUDGET_MAP`/`_allocate_budget`
  (`pipeline.py:802-812`) + `models.yaml:50-57` correctly map quick→Haiku, standard→Sonnet,
  deep/chain→Opus — but `run_metis` only PRINTS the model (`pipeline.py:1148-1153`) and returns an
  instruction sheet; there is no `messages.create` in the pipeline, so the calling Claude client isn't
  bound to it. Peripheral synthesis routers (briefs/news/slides/paperqa) DO use cheap models — but
  statically per-feature, decoupled from the complexity tier.
- **"Compaction with retention" is overstated — there is NO conversation summarization.** The
  `max_turns` guard truncates ("start a new session", `pipeline.py:1055-1086`); the 80% auto-handoff
  is a **DB-state card**, not a conversation summary (`handoff.py:117-216`); session summaries are
  voluntary. Raw turns are dropped, not summarized. This is the biggest gap vs best practice
  (Anthropic's Compaction API / anchored iterative summarization).
- **Prompt caching is ~1 of 7 call sites; `cache_helpers.py` (build_system_with_cache /
  build_agent_system) is DEAD CODE** — never imported. `token-guardrails.md` mandates caching but the
  code doesn't follow its own policy. Agent system prompts (the biggest stable blocks) are never cached.
- **Good by construction:** surgical context budget (`_BUDGET=1800`, P3.6) and efficient routing (P3.7).

*Monitoring & transparency (E6.2):*
- **Token monitor is real SQL over `agent_runs` but STRUCTURALLY UNDERCOUNTS to ~0.** `log_agent_run`
  defaults tokens to 0 (`agents.py:101-111`) and **no caller ever passes real counts** — the template
  even has an `all_tokens_zero` fallback to run-counts (`metis_token_monitor.html:30,38-56`). It
  measures *runs* reliably, *tokens* only cosmetically. Real token numbers exist only in the demo seed.
- **Agent-activity views exist** (runs, agents directory) but **`agent_spans` is dead instrumentation**
  — `start_span/log_span/end_span` (`observability.py:72-155`) are never called, so the trace
  waterfall is always empty. `session_events` ARE written but **no dashboard router reads them**.
- **Live "who's working now": NONE** — `agent_runs.status='running'` is never set (template ready at
  `metis_runs.html:29-30`); no active-session poll. **Per-answer "who did what": no surface.**
- **Agent voices exist** (`agents/<slug>/system-prompt.md`) but are deliberately hidden per the MCP
  server instructions ("never say 'routing to agent X'").

**Prioritized work (evidence-based; sources in the eval run):**
1. **Prompt caching everywhere stable** — wire the already-written-but-dead `cache_helpers` into every
   real API call (meetings/learning/teach/improvement/paperqa + agent system prompts). ~50-90% off
   cached prefixes; highest-leverage, lowest-effort. *(Anthropic prompt caching.)*
2. **True conversation compaction with retention** — at ~60-70% context, sliding-window/anchored
   iterative summarization into a persistent state + prune raw events; adopt Anthropic's Compaction API
   rather than the turn-cap-and-abandon today. *(Anthropic context-engineering.)*
3. **Fix token capture (B6.3 precondition)** — capture real input/output tokens + model at every
   `log_agent_run` site (or from the API response) so the monitor stops reading ~0. Without this, all
   token monitoring and per-agent cost is cosmetic.
4. **Make model tiering binding OR reframe the claim honestly** — either apply `_BUDGET_MAP` to a real
   call, or document that the client controls the model and stop implying enforced tiering.
5. **Quality-evaluator cascade** instead of the `word_count>40→deep` heuristic (`pipeline.py:619`):
   cheap model first, escalate only on a failed check.

**BUILD STATUS (2026-08-11):** ✅ **B6.2 shipped** (`dd9e8a6` — "who did what" strip on the Metis
Overview, reads `agent_runs` per session, refreshes 30s). ✅ **B6.3 done** (`50b13ca`+`cc40798`+`9b60927` — real token capture wired into 6 call sites: morning
brief, session-consolidation, meeting extraction, flashcard gen, slide gen, and MCP-side reflexion
themes. Only PaperQA is deferred — its usage is internal to the PaperQA library, not a plain response).
The token monitor now reflects real spend across the dashboard + the MCP self-improvement call.
✅ **B6.1 COMPLETE (2026-08-12, `31ed255`)** — `run_metis` now dispatch-writes an `agent_runs`
row with `status='running'` for the routed agent, and `log_agent_run` completes that row in place
(matched on session_id, dispatch model preserved) instead of duplicating; a 15-min stale-guard on the
dashboard stops a perpetual "working…". *Caveat: only fires when `run_metis` is actually invoked — see
Appendix C.* ✅ **E6.2 honesty** (`31ed255`) — the token panel now states plainly that per-run token
counts aren't captured (the LLM can't self-report) rather than showing misleading zeros. ⏳ Prompt
caching (wire the dead `cache_helpers`), true compaction, and binding model-tiering remain (compaction
+ tiering pair with 3.0).

**Builds (after the evaluation shows the gaps):**
- **B6.1 — Live "who's working now":** write a `'running'` `agent_runs` row / `agent_start`
  session_event at dispatch + a polled `/api/partial/metis/active` partial keyed on the live session.
- **B6.2 — Per-answer "who did what":** a `/api/partial/metis/session/{id}` view grouping the
  already-written `session_events` (`"[agent_slug] summary"` results) into a contributor timeline;
  optionally revive `agent_spans` by actually calling the span tools from the pipeline.
- **B6.3 — Per-agent token attribution:** depends on #3 above (plumbing + by-agent query ready at
  `metis_tab.py:828-849`; only real counts are missing).
- **B6.1 — Live "who's working now."** Surface, in real time, which agent(s) a prompt is being routed
  to / handled by — in the dashboard (and, where possible, echoed in the chat via the `run_metis`
  return). Reuse the routing decision (`_parse_intent_stage`) + `session_events` classification rows.
- **B6.2 — Per-answer "who did what" overview.** After an answer, a compact summary of which agents
  contributed and what each did (each agent has its own voice/label) — proving the agents actually
  worked. Reuse `agent_runs` + `session_events`; render on the Today/Metis surface and offer it in the
  `run_metis` output contract.
- **B6.3 — Reliable per-agent token attribution.** Ensure each routed agent's token use is captured
  (tie to B6.2) so E6.2's monitor can show per-agent cost, not just a global number.

**Phase 6 acceptance:** a representative set of prompts shows (measured) lighter models on simple
tasks and heavier only when warranted; the dashboard token monitor matches an independent count; the
user can see which agents are working during a prompt and a truthful "who did what" summary after —
and none of it overstates isolated sub-agent execution that 3.0 hasn't delivered yet.

---

### PHASE S — Metis Systems surface overhaul ("an operator's console") — ✅ SHIPPED 2026-08-12
*Merged in from the senior-engineer surface review. Reshaped the Systems surface (the `metis` tab) from
an engineer's endpoint list into a console a non-technical scientist can read at a glance. Overlaps and
advances P2 (coherence), P3 (learning loop), and P6 (monitoring) — cross-referenced there.*

> **Status: ✅ SHIPPED (commits `af7ddc2`, `31ed255`, `c911818` on `main` — local only, not pushed).**
> All items S.0–S.6 built + verified (in-process TestClient for endpoints; hermetic temp-DB tests for
> the log_agent_run update-vs-insert and the learning-loop throttle; MCP smoke HEALTHY). MCP server
> rebuilt offline — needs a `/mcp` reconnect to load the server-side pieces.

**The problems it fixed (audit finding):** the surface opened on a static how-to instead of a
state-of-things view; had no single "is Metis healthy right now?" answer; scattered two cards
(feature-tips, autostart) into the page header so they showed on *every* section (the reported "bug");
duplicated Memory (a section here **and** a standalone surface that under-reported by ~300× — 67 vs
~19k across 8 layers); and several panels promised live data their producers never filled.

| # | Item | Status | Notes |
|---|---|---|---|
| S.0a | Move feature-tips + startup cards out of the global header | ✅ | now in Appearance & Settings — fixes the "on every section" bug |
| S.0b | Model selector + theme swatches reflect the **saved** value | ✅ | server-rendered via `_surface_ctx`; was hardcoded Sonnet/Archive (P2.2) |
| S.0c | Memory overview counts all **8 layers**, not just `memory_entries` | ✅ | ~19k not 67 |
| S.0d | Delete dead routes/templates (`metis/agents`, `metis/traces`, `content-packs`) | ✅ | producers never existed |
| S.1 | Restructure 12 sections → **9**: Dashboard (new, first) → Activity → Memory → Agents → Learning → Persona & Model → Appearance & Settings → Integration & Keys → **Manual & FAQ** (last, with a real FAQ) | ✅ | opens on state, ends on help (P2.1) |
| S.2 | Live agent monitoring: dispatch-write `status='running'` + complete-in-place + session linkage | ✅ | **= P6 B6.1.** Caveat: fires only when `run_metis` is invoked (App. C) |
| S.3 | Live **MCP health check** (server importable + registered in Desktop/Code) on Dashboard + Integration | ✅ | the thing users most want confirmed; was absent |
| S.4 | Merge the standalone Memory Health surface into the Memory section; `/memory` → redirect | ✅ | one canonical Memory home |
| S.5 | Honest token panel (states usage isn't captured vs misleading zeros) | ✅ | **= P6 E6.2 honesty**; real capture still needs the pipeline |
| S.6 | Desktop-only learning loop in `session_bootstrap` (throttled once/~20h) | ✅ | **= P3 3.3 second half.** Caveat: gated on `session_bootstrap` being called |
| S.+ | **Health Check** button (full doctor inline, plain language, no terminal) + **Sessions panel** (recorded-session count, memory-active status, open each to read it) + two new doctor checks (session-memory-active, projects-registered) | ✅ | serves 1.3/3.5 spirit; answers "is everything recorded?" |

**Phase S acceptance (met):** the surface opens on a Dashboard with a truthful health readout; the
tips/startup cards appear only in Settings; model + theme show the saved values after reload; Memory
appears in one place with the full 8-layer count; the token panel no longer shows misleading zeros;
Manual & FAQ sits last. **Follow-up surfaced:** the client-tagged `sessions` registry is dormant, so a
reliable Claude-Code-vs-Desktop session split needs it revived (client tagging added to
`save_session_summary` going forward as a first step).

### CROSS-CUTTING — Engineering hygiene (runs alongside every phase)
*What a senior engineer notices immediately; do opportunistically within the phase that touches each area.*

- **Split the monoliths** — `today.py` is ~180 KB in one module (also `knowledge.py` 92 KB, `metis_tab.py`
  68 KB); hard to test/review. Refactor as their phases touch them.
- **Add lint/type/format + CI matrix** — no ruff/black/mypy/isort/pre-commit anywhere; CI runs one Python
  version and no lint/type job. This is the most visible professionalism gap.
- **Unify dependency pinning** — MCP `requirements.txt` is exactly pinned; dashboard uses loose `>=`;
  `pyproject` uses `>=`. Shared libs can resolve differently across the two tiers.
- **De-duplicate the copy-pasted DB resolver** (see 0.1) and the two migration systems (0.5).
- **Reconcile the backlog** — several 📋 OPEN items are actually shipped (changelog says so) but never
  closed out; the register (Appendix A) marks these "reconcile" — close them so the backlog is trustworthy.
- **Fix doc/impl drift** — `RAG-ARCHITECTURE.md` batch size / score formula / layer numbers disagree with
  code; count claims ("210+ tools", "65 tables") need a fresh check before release.

---

## 2.5 Runtime Data-Flow & Integration Review (added 2026-08-10)

A separate trace of what actually happens **at runtime** when you use Metis — data in → saved →
retrieved → used — from three deep agents (write/save integrity, conversation-routing reality,
cross-surface + connectors). This is the "does the machine really work when you use it" review.

### The load-bearing finding: the conversation lifecycle is CONVENTION, not construction
When you ask a question, it does **not**, by construction, flow through routing → agents → memory →
library chunks → PH backgrounds. `run_metis` (`tools/pipeline.py:884`) runs real code for
**safety (Stage 3/4 Guardian/Cyber — can hard-block), keyword routing (Stage 5), and a shallow
context peek (Stage 7)** — but it then **returns a text instruction sheet** telling Claude which
persona to adopt and which tools to call. It never calls `get_agent_context`, never executes a
sub-agent (specialization is persona role-play by instruction — there is no real sub-agent
execution), and **never calls any RAG tool**. And all of that only runs *if the model chooses to
call `run_metis` at all* — nothing forces it. The dashboard has **no** question-answering pipeline.

| For a normal question | Desktop | Code | Dashboard |
|---|---|---|---|
| Safety block (Guardian/Cyber) | CODE *iff* run_metis called | same | N/A |
| Routing | convention (keyword code, only if run_metis called) | convention | none |
| Agent specialization | convention (persona role-play; no real sub-agent) | convention | none |
| Memory recall | convention; shallow (recency+`LIKE` on `memory_entries`, **no vector table**); vector recall only at *new-session bootstrap*, keyed on profile not the question | same | none |
| Library-chunk RAG (`search_pdf_knowledge`) | convention; **never auto** | same | none |
| PH-background RAG (`ask_library` scope=`ph_library`) | convention, deepest opt-in (research-mode prompt + pre-built index) | same | none |

→ This is the deepest intent-vs-reality gap and **reshapes Phase 3**: the headline fix is to make
`run_metis` *actually execute* recall + RAG + (optionally) real agent hand-off, so grounding and
memory happen by construction. New roadmap item **3.0 (now the top of Phase 3):** "the pipeline
executes the lifecycle instead of instructing it."

### Save/persistence integrity — what's saved, what's only shown
DB target is now consistent (single live `~/.local/share/metis/metis.sqlite`, WAL; the historical
`app`/`app-py` split-brain is archived/guarded — N9 is a fresh/restore *edge*, not an everyday bug).
But several things are **displayed but never stored**, or **saved but not retrievable**:

| Finding | Evidence | Fix → phase |
|---|---|---|
| **Cross-pollination links are never persisted** — recomputed & shown each time; `idea_links`/`memory_relations` are written only by the demo seed / explicit `link_memories`. Connections never accrue. | `ideas.py:117` `_cross_pollinate_core`; `capture.py:155`, meetings imports = display-only; `schema.sql:161` only writer is `seed_mockup_demo.py` | **P3 (new 3.9):** persist connections so the graph grows |
| **Dashboard-captured ideas skip vector indexing** — chat `capture_idea` writes `episodic_memory`+`vec_episodic`; the dashboard modal writes only `ideas`. Same content, different retrievability. | `ideas.py:270-295` vs `capture.py:147` | **P3 (new 3.10):** one capture core; always embed |
| **Two disjoint "notes" systems** — dashboard `personal_notes` (SQL) vs `search_notes` (greps `.md` files). A modal note is invisible to `search_notes` and vice-versa. | `capture.py:135` vs `tools/notes.py` | **P2/P3:** unify notes |
| **RAG is decoupled from library ingest** — adding a paper (Zotero/scan/dashboard) writes metadata only; it's searchable in RAG only after a manual `build_pdf_knowledge_db` AND the PDF sits under `knowledge/library/`. | `knowledge_db.py:525`, `_collect_pdfs_for_db`; `zotero.py`, `content_scan.py:491` | **P4 (new 4.8):** auto-index new papers into RAG |
| **`library_seeded` is read-only at runtime** — no runtime writer; populated only at install/seed. | grep: no INSERT in `system/` | note for P4 pack model |
| **Meeting cross-refs persist only via explicit `enrich_meeting_with_crossrefs`** — dashboard import shows them but doesn't save them. | `meetings.py:128` vs import paths (display-only) | **P3:** persist on import |
| **Memory continuity depends on the model calling the save tools** — `sessions`/`session_events` auto-write via `run_metis`, but `agent_runs`, `reflexion_log`, `session_summaries`, decisions, and most `episodic/semantic` writes are behavioral (stages 10-11 are instructions). A plain chat that skips `run_metis` records nothing. | `pipeline.py:1046-1069` | **P3.2** (enforce write-back) |

### Cross-surface flow & connectors (summary)
- **Genuine links via shared tables:** idea→Thinking/Today, paper→Library/Today+RAG, project→Work/
  Planner/Today(+cross-poll seed), news→Today. **But** the connections strip is embedded on only
  **3 surfaces** (Today, Library, Work) though the engine reads all domains; and **meeting action-items
  stay siloed until the user manually clicks "create tasks."** → **P2/P3 (new):** wire the connections
  strip on the remaining surfaces; auto-promote/surface meeting actions.
- **Connectors:** Zotero read ✓ / write **403-blocked**; PubMed ✓, OpenAlex ✓, DHIS2 ✓ (configurable),
  WhatsApp webhook ✓ (separate process); Anthropic API optional; **calendar & email absent** (the
  "Metis OS" gap). MCP is stdio; fresh connection sees the `core` subset (~80 tools) + on-demand
  `find_tools`/`load_tool_group`; ~45 Desktop prompts route into the same machinery.

### Net runtime verdict
The **storage layer is sound and consistent**; the **surfaces are genuinely linked** where they share
tables. The gap is that the **intelligence layer is advertised as automatic but is opt-in**: recall,
RAG grounding, agent specialization, connection-persistence, and memory write-back all depend on the
model choosing to act, and cross-pollination is never saved. Phase 3 (now led by 3.0) is therefore the
highest-leverage work for the "ambient second brain / grounded-in-your-library / nothing-lost" promise.

---

## 3. Sequencing & how we build it across sessions

- **P0 first, always** — it's small, high-impact, and prevents data loss / start failures. Do it before
  anything ships. (0.1 and 0.2 are the two must-dos.)
- **P1 next** — it's what makes Metis *installable* by the target user. 1.1 (bundled exe) needs a Windows
  host; the rest (1.2–1.6) can proceed on WSL/Linux.
- **P2 and P3 in parallel-ish** — P2 is UX/coherence, P3 is the backbone; they touch different areas.
- **P4 then P5** — backgrounds before Office, since both build on the same "additive layer over the brain"
  thinking and P4 fixes the shared DB-resolver split-brain P5 would also hit.
- Each phase is one-to-a-few sessions. Cite the item number ("Keystone P3.1") to resume. Every session
  ends by updating this file's status column and the promise harness score.

---

## Appendix A — Consolidated gap register (nothing forgotten)

Cross-checked against the README's promises, the backlog, and conversation memory. Bucketed; each mapped
to the phase that resolves it. (Full evidence in the source review; this is the durable checklist.)

**(A) Promised in README but not (fully) built** → mostly P0/P1/P3:
A1 automated overnight brief needs a reliable scheduler+key (P0/P3) · A2 bundled `.exe` unbuilt (P1.1) ·
A3 installer auto-registers MCP — partly true, buggy (P1.2) · A4 injection-probe not wired at ingestion
(security, P0/cross-cut) · A5 output/egress PII rail has no caller (security) · A6 Data-Guardian pre-tool
hook is Claude-Code-only, not Desktop (security) · A7 self-improvement "writes approved changes to disk" —
skill-file path may not reach runtime (P3.4) · A8 Course Builder end-to-end thin (later) · A9
cross-pollination "automatic everywhere" — real at ingestion, thin on flagship Thinking tab (P3) · A10
live-meeting extraction — largely built · A11 CDN assets break "all local" (P2.6) · A12 count claims need
a fresh check (cross-cut) · A13 domain layer has named content gaps (P4/content).

**(B) Requested / backlog, not built** → P1/P2/P4/P5 + content:
Bundled exe + Inno wiring (P1.1) · post-install smoke + retire dead launchers (P0.8/cross-cut) · Linux/mac
autostart parity · reproducibility "send code not data" toolkit (SCD1-3) · write-side data-auth gate
(reconcile — may be shipped) · always-on tracking everywhere (Stop hook/Desktop checkpoint/git-hook/unified
timeline) · project de-dup + Project Capsule export · paper-qa install + citation graph + structured
extraction + PDF annotation + calendar OAuth + Anki export + diarization token · knowledge paper-detail /
screening view · news/brief presentation redesign (relevance %match cards) · Ollama local-model provider +
OCR fallback · parallel/nested subagents pilot · `metis-doctor` "adapted to this computer?" · wizard polish ·
Frontend Design Studio · test coverage for backup/voice/pipeline/observability/subset_loader/reflexion chain.

**(C) Flagged in memory/docs as open or broken** → P0/P1/P2/P3:
LLM fallback router (P3.7) · one-command `metis update` (P2.4) · schedule `backup-canonical.py` daily
(P0/P2) · output PII rail caller + injection-probe middleware + decimal-GPS pattern (security) ·
cross-model verifier for reflexion (P3.8) · 52 DOM-only buttons untested (P0.8) · procedural/working memory
empty / cold loop harvests 0 (P3.2) · **ROTATE the Anthropic API key printed to a transcript 2026-07-14**
(do now) · Zotero WRITE key 403/read-only · two-computer DB divergence, no reconcile tool (P0/P2) · ambient
recall auto-injection (P3.1) · backgrounds-as-plugins (P4) · wizard self-verification (P1.3) · Windows
supervision parity + visible health (P0.6) · zero cross-surface links historically (P3) · Teach tab thin ·
Events/Funding web-search 429s on low API tier · brain-icon licensing check before publication · expose
`record_routing_preference` as MCP tool · MCP-reconnect debt for record_decision/recall_decisions.

**(D) Intent-vs-reality tensions to make honest** → resolved as the phases land:
"ambient second brain" (P3) · "local-first" wording + CDN assets (P2.6; keep honest scope — reasoning is the
Claude cloud API) · "no prompt, every morning" needs scheduler+key (P0/P3) · "sharper every week"
self-improvement loop (P3) · "always works" (P0 — reality has largely caught up) · "nothing lost" one-command
safe update + DB divergence (P0/P2) · "routes to 30+ specialists" reaches 21/35 (P3.7) · "six security
layers … held back before it reaches the AI" — currently advisory/scattered, make enforced/central
(security thread) · grounding needs a populated library (onboarding) · "Metis OS" calendar/email — future,
self-flagged.

**Immediate (not a phase — do promptly):** rotate the exposed Anthropic API key (C10); confirm the brain
icon licensing before any public release (C22).

---

## Appendix B — MCP-vs-alternatives verdict (the re-evaluation, on the record)

- **Keep MCP** as the Claude Desktop/Code backbone. It is the correct, standard, low-attack-surface choice;
  FastMCP + stdio + progressive tool disclosure + resilient import + local embeddings is well-built.
- **MCP cannot serve non-Claude clients** (stdio, request/response). Do **not** try to make Office talk to
  the MCP server.
- **The dashboard (localhost FastAPI) is the integration attach point** — already always-on over the same
  SQLite brain, Origin-hardened, already emits `.pptx`. Add a JSON API (P5.1). A sibling service (like the
  existing `webhook.py`) is the proven pattern if isolation is wanted.
- **Office** = dashboard JSON API + file-watcher (lowest friction) now, Office.js add-in (HTTPS-localhost
  cert needed) later. PPTX/XLSX/DOCX libraries are already installed and partially used.

---

## Appendix C — Memory System Evaluation (2026-08-12)

*Full comprehensive evaluation of Metis's memory, on owner request. Method: live-DB scan of every
layer (counts + last-write recency) via the MCP server's own connection, cross-read against the recall/
consolidation code and the runtime data-flow review (§2.5). Numbers are from the live DB
`~/.local/share/metis/metis.sqlite`.*

### C.1 The layers, by liveness (the honest census)

| Layer | Table | Rows | Last write | Verdict |
|---|---|---|---|---|
| Memory Palace (curated) | `memory_entries` | 67 | 2026-08-11 | ✅ active |
| Episodic (events) | `episodic_memory` | 2,018 | 2026-08-11 | ✅ **strong** — auto-extracted from agent runs |
| Semantic (concepts) | `semantic_memory` | 52 | 2026-08-10 | ✅ active — consolidation writes here |
| Procedural (how-to) | `procedural_memory` | 1 | 2026-05-23 | ⚠️ **effectively dead** |
| Working memory | `working_memory` | 0 | — | ⚠️ **empty** |
| Session summaries | `session_summaries` | 687 | 2026-08-12 | ✅ **strong & current** — the real continuity layer |
| Session registry | `sessions` | 5 | 2026-05-27 | ✅ **FIXED (M1)** — was dormant since May; now opens on the first tool call, client-tagged |
| Session events | `session_events` | 0 | — | ✅ **FIXED (M1)** — was empty all-time; now written by every tool call |
| Reflexions | `reflexion_log` | 36 | 2026-08-12 | ✅ active (incl. today) |
| Improvement proposals | `skill_improvement_proposals` | 2 | 2026-06-04 | ⚠️ stale — drafting produces nothing new |
| Ideas | `ideas` | 8 | 2026-06-18 | ⚠️ low/stale |
| Idea links | `idea_links` | 0 | — | 🔴 empty |
| Cross-pollination links | `cross_pollination_links` | 0 | — | 🔴 empty despite 3.9 "persist at ingestion" |
| Decisions (standing prefs) | `user_decisions` | 1 | 2026-06-22 | ⚠️ thin — *(the original row said "table absent"; that was a wrong table name, see the C.4 correction)* |
| Dashboard notes | `personal_notes` | 0 | — | ⚠️ empty; also split from `.md` notes |
| Topic memory | `user_topics` | 5 | 2026-06-11 | ⚠️ small |
| Library chunks (RAG) | `pdf_chunks` | 16,500 | 2026-07-14 | ✅ substantial; not re-indexed since July |

### C.2 The load-bearing finding: two memory systems — one alive, one dormant

Continuity that **works** flows through **direct tool calls**: `save_session_summary` (687, today),
`log_agent_run → _auto_extract_memory` (episodic 2,018), `write_reflexion` (36, today). These are
healthy and current.

The **pipeline-written** layer is **dormant**: `session_events` = 0 and the `sessions` registry has
not grown since May. That means **`run_metis` / `session_bootstrap` are barely invoked in normal use** —
so everything gated on them is empty. This is the DB confirming §2.5's "the lifecycle is convention,
not construction," and it has a direct bearing on **today's Phase S backend**: the S.2 dispatch-write
and the S.6 learning loop live *inside* that pipeline, so they are correct but only pay off once the
pipeline is actually called. **This is the #1 memory issue and it reframes the remaining P3 priority:**
the highest-leverage work is not more recall wiring — it's ensuring the lifecycle is actually invoked,
or moving the session/decision/reflexion write-backs onto the always-hit direct-tool path.

### C.3 Retrieval quality

Recall is now a hybrid **vector + keyword** path (P3.1 shipped, RRF over the 768-d layers); episodic is
embedded. On paper this is near state-of-the-art and the merged Memory section now exposes a live
retrieval tester. **But** rich recall into a new request still depends on either the model choosing to
call `recall()` or `run_metis` running its Stage-7 auto-recall — and §C.2 shows the pipeline isn't in
the hot path. So the *capability* is strong; its *guaranteed presence in every answer* is not. (The
`vec0` extension loads fine in the live server per the smoke test; a subprocess scan failing to load it
is not a defect signal.)

### C.4 Specific gaps (each mapped to a phase)

- **Procedural + working memory never accumulate** (1 / 0) — the "how things are done here" layer is
  inert; the cold loop harvests 0. Decide: feed it, or drop the claim. → P3.
- **Cross-pollination + idea links = 0** despite 3.9 shipping "persist at ingestion" — verify the
  writer fires in normal (non-pipeline) use; the connection graph is not growing. → P3 (3.9 follow-through).
- ~~**`decisions` table absent**~~ — **CORRECTED 2026-08-12 (session 2): this finding was wrong.** The
  table exists as **`user_decisions`** (1 row, last written 2026-06-22); the census grepped for the
  name `decisions`. `record_decision` and `recall_decisions` are both registered tools and have run.
  The real gap is that capture is *thin*, not absent — standing preferences are recorded only when the
  model chooses to record one. Same convention problem, far lower severity. → P3.2, downgraded.
  (Likewise `routing_preferences` does not exist under that name: the real table is
  `agent_routing_rules`, 127 rows.) *Lesson: "the table is missing" was inferred from a name lookup,
  not from the schema — verify a table's real name before concluding a feature never ran.*
- **New library items aren't auto-indexed into RAG** — `pdf_chunks` last grew 2026-07-14; adding a
  paper writes metadata only. → P4 (new 4.8).
- **Two notes systems** — `personal_notes` (SQL, empty) vs `search_notes` (greps `.md`). → P2/P3.
- **Improvement proposals stale** (2, since June) — thin reflexion input + the 14-day theme window
  mean drafting rarely fires; S.6 helps volume but the window still hides history. → P3.5.
- **Session identity is messy** — `session_summaries.session_id` is a mix of dates/empty/UUIDs; a real
  registry (revived `sessions`, now client-tagged going forward) would give clean continuity + the
  Code-vs-Desktop split. → follow-up.

### C.5 What is genuinely strong (keep)

Episodic auto-extraction from every logged run (2,018), session-summary continuity with content-hash
dedup (687), reflexion capture (36, current), semantic consolidation (52), fully-local 768-d
embeddings + sqlite-vec, the coherent 8-layer model, and — new today — one visible Memory home + a
Health Check that surfaces all of this in plain language.

### C.6 Prioritized memory fixes

1. ~~**M1 (highest) — put the write-backs on the always-hit path.**~~ **✅ SHIPPED 2026-08-12** (`eec122f`).
   Neither of the two options in the original framing was taken. Forcing `run_metis` to be invoked
   would have been another convention, and moving writes onto "the direct-tool path" begs the question
   of which tools those are. Instead the writes moved to the **dispatch chokepoint** — the wrapper
   around `FastMCP.call_tool` that the security guard already owns — so *every* tool call, present and
   future, carries session identity. See `ambient.py`. S.2 and S.6 are no longer latent.
2. ~~**M2 — make connection persistence real in normal use**~~ **✅ SHIPPED 2026-08-12** (`a0de36e`).
   The premise was wrong again: `_persist_connections` fires correctly on both capture paths — there
   simply had been no capture since 3.9 landed (last idea 18 June). One capture took the table 0 → 5.
   The *real* defect only surfaced by running it: both paths wrote and embedded the idea and **then**
   searched, so every capture matched itself at rank 1 / score 1.0 — burning the top slot of five,
   persisting a self-edge, and showing the user their own idea back as a "connection".
   Cross-pollination now runs **before** the write on both paths, plus a self-edge backstop in
   `_persist_connections`. Verified on chat capture and a real `POST /api/capture`.
3. ~~**M3 — revive the client-tagged `sessions` registry**~~ **✅ SHIPPED 2026-08-12**, as a consequence
   of M1. Sessions now open on the first tool call, tagged by `ambient.detect_client()`, and reuse
   Claude Code's own `CLAUDE_CODE_SESSION_ID` as the session id where available — so a transcript and
   its memory rows finally share one identifier. The Code-vs-Desktop split fills in going forward.
4. ~~**M4 — decide procedural/working memory's fate**~~ **✅ DECIDED + SEEDED 2026-08-12.** The item
   conflated two different things:
   - **`working_memory` is not a promise.** It is never advertised on any surface; its docstring calls
     it an ephemeral scratchpad for "state that agents need mid-pipeline", and both halves
     (`set_working_memory` / `get_working_memory`) exist. It is empty because the pipeline is not the
     hot path. **No action** — it is unused internal plumbing, not a broken feature.
   - **`procedural_memory` IS advertised** on the Memory surface ("PRACTICE · How things are done
     here") and showed 1. Owner's call: **keep it and seed it**, since he described real content for
     it. Seeded with 5 genuine procedures drawn from documented practice (apply an MCP code change ·
     ship to both repos · handle sensitive data · diagnose "Metis is down" · verify a change actually
     works). Retrieval verified 5/5 on natural-language questions.

   **The layer's defining test, for future entries:** procedural memory answers *"when situation X
   arises, do these steps"* — it needs a `trigger_context` AND `steps`. A fact you know is **semantic**
   memory; a standing preference is **`user_decisions`**. Same topic can split across all three.

   **Known follow-up:** with `layers` left at its default, episodic's 2,018 rows drown procedural's 6
   under RRF, so procedures reliably surface only when the layer is targeted. Layer-imbalance in
   ranking is logged in the backlog.
5. **M5 — capture standing preferences reliably** (the table exists — see the C.4 correction; it is
   capture that is thin, 1 row since June). Downgraded from "create the table". (P3.2)
   **Mechanism SHIPPED 2026-08-12** (`4d8b02b`) for the procedural case: when Metis volunteers a
   recorded procedure it asks whether to apply it automatically in future and records the reply via
   `record_decision(category='procedure')` — "always" becomes a standing instruction that stops
   asking, "never" silences it. **Offer → record → honour**, verified end-to-end over the real
   protocol. *Remaining M5 work is to generalise that same loop to every recurring choice* (use RAG?
   which knowledge layer? complement from the web?), which is logged in the backlog. That
   generalisation is what finally makes `user_decisions` a live layer instead of a 1-row table.

   Two enabling fixes landed with it, both instances of Appendix D's pattern:
   - **Recall was layer-biased by tie-order, not relevance.** RRF is rank-based, so the best hit in
     every layer scores identically; a flat sort plus Python's *stable* sort meant ties kept
     insertion order (episodic, semantic, procedural). Episodic won because it was appended first
     and had 2,018 rows to fill `top_k` before the 7-row procedural layer was reached. Layers are
     now ranked internally and interleaved.
   - **`_texts_of` found nothing at all.** FastMCP's `call_tool` returns a 2-tuple
     `(list[ContentBlock], dict)` and the helper walked only the top level — so the **egress PII
     rail scanned nothing, on every call, with no error**. This morning's dispatch fix made the
     guard *run*; this made it able to *see*. Found only because a feature built on top failed
     loudly enough to investigate.
6. **M6 — auto-index new library items into RAG.** (P4.8) — **the blocking half is fixed** (`?`, this
   session): a knowledge layer could only ever index folders under `knowledge/library`, and said
   nothing when a collection lived elsewhere. That hid the owner's **primary research collection** —
   211 sleeping-sickness papers in `inputs/literature/sleeping-sickness`, zero overlap with what was
   indexed — while the dashboard showed `hat-specialist` as present because it held 10 books from a
   different folder. A HAT question could quote the books and the general background, never the papers.
   Folders now fall back to the RC root; `_relative_source` replaces three `relative_to(lib_root)`
   calls that would otherwise raise on an outside path (indexing would have aborted on file 1, and the
   resume check would have crashed rather than skipping). `hat-specialist` repointed → 221 PDFs; full
   index run **COMPLETE: all 211 sleeping-sickness papers indexed, 24,015 chunks.** Verified by
   asking real questions — "passive screening sensitivity for gambiense HAT" now returns Checchi 2018
   and Simarro 2014 with page numbers and quoted passages, from the owner's own collection, for the
   first time. **Still to do:** the *automatic* half — indexing on ingest, so a newly added paper does
   not wait for a manual build.
7. ~~**M7 — unify the two notes systems.**~~ **✅ SHIPPED 2026-08-12.** `search_notes` now searches
   the dashboard's `personal_notes` rows as well as the `.md` files on disk — no migration, the two
   stores stay put but one question reaches both. Verification also exposed a matching weakness in
   *both* stores: "tiny targets re-costing" missed a note reading "tiny targets NEEDS re-costing",
   because substring matching breaks on any word in between — exactly how someone half-remembers
   their own note. Both sides now fall back to all-words-present matching after trying the exact
   phrase.

**Acceptance (memory is "well"):** a new session references prior work and relevant memory surfaces
without an explicit call; running any agent leaves an episodic entry *and* a reflexion; capturing an
idea grows the connection graph (links > 0); a stated preference is recalled next session; the census
above shows no unexpectedly-empty layer for a feature that's advertised as working.

---

## Appendix D — "Looks structural but isn't" register (2026-08-12)

*Owner asked for a systematic sweep after four defects in one session turned out to share
one shape. Method: `tools/audit-structural.py` (new, permanent, wired into `test-mcp.sh`
as a WARN) + manual verification of every hit. The detector exists because reading the
code cannot find these — in all four cases the code looked correct.*

**The pattern.** A control or feature is correctly written, visibly present, and never
reached. Nothing errors. Tests can pass while testing the wrong path. The only reliable
questions are *"what has no caller, no writer, or no rows?"*

### D.1 Found and FIXED this session

| # | What | Why it was invisible |
|---|---|---|
| 1 | **Tool guard never on the request path** — `install()` reassigned `app.call_tool`, but FastMCP captured the bound method at construction. Every real MCP request bypassed the path deny + PII rail. | `tool_guard_log` had 3 rows, all from the day it was written. Our test called `app.call_tool()` directly — the one path that *did* reach the wrapper. |
| 2 | **`session_bootstrap` de-registered** by a helper inserted under its `@app.tool()`. | Tool **count** unchanged (214 either way) — one name simply swapped for another, so the count-based check passed. |
| 3 | **`kg_index_notes` de-registered**, same cause, much older. | Nobody was looking for it. |
| 4 | **Memory write-backs behind `run_metis`**, which is almost never called. | `session_events` had 0 rows for its entire existence. |
| 5 | **`_check_output_stage`** — the output red-line scan — defined, called by nothing. | Could not be wired to `run_metis`: that returns an instruction sheet, not an answer. Now runs inside `evaluate_against_layers`, the only function receiving a drafted answer. |
| 6 | **Cross-pollination searched after writing**, so every capture linked to itself at rank 1. | The table was empty for a different reason (no captures since it shipped), which masked it. |

### D.2 Found, still OPEN — decisions for the owner

**Frozen fossils** — created in `system/installer/schema.sql`, read by the dashboard,
written by **no code anywhere in the repo**. Four still hold rows from a tool since removed,
so the dashboard renders real-looking numbers that can never change again:

| Table | Rows | Consequence |
|---|---|---|
| `library_inventory` | 221 | **Worst one.** It is how the library browser resolves a paper to its PDF on disk. Every paper added from now on is invisible to that lookup. Same wound as M6, different organ. |
| `knowledge_links` | 93 | Explicit knowledge links frozen; the graph cannot grow. |
| `library_duplicates` | 23 | The dashboard's duplicate count can never update. |
| `learning_competencies` | 8 | Teach-tab competencies frozen. |
| `research_milestones` | 0 | Read in one place, never written — the feature does not exist. |

**Silent layers** — a writer exists, but the table is empty, i.e. the tool is never invoked
(the `run_metis` disease). Most are simply unused features; these three are not:
- `discovery_shown` = 0 → **the discovery-tips feature in CLAUDE.md has never fired once**, in any session.
- `agent_spans` = 0 → the observability waterfall the dashboard renders has never had a trace.
- `meeting_actions` = 0 → confirms §2.5: meeting action items are shown but never persisted.

**Hollow routes** — registered, return 200, body is a placeholder:
`/api/partial/teach/active-draft`, `/courses-list`, `/suggested` — all return `<div></div>`.
This is the UI dialect of the same disease and confirms the long-standing "Teach tab thin" note.

### D.3 The rule this yields

> **A control that has never written a row has never run.** Prefer evidence of execution
> (an audit row, an event, a non-empty table) over evidence of correctness (it reads fine,
> the test passes). When adding a guarantee, ask what would be *observably different* if it
> silently stopped working — and if the answer is "nothing", that is the defect.

---

*End of the Keystone Roadmap. Update the status of items here as they are built; keep the promise-harness
score and drift heatmap as the objective "are we there yet" signal.*
