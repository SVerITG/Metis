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

| # | Item | Why / evidence | Files | Size·Impact |
|---|---|---|---|---|
| 2.1 | **A single Settings surface** | Settings are spread across the Metis tab (12 sections), the wizard (13 sections), ~40 config files, and a chat layer. Consolidate into one coherent, searchable pane; keep chat + file access for power users. | `routers/metis_tab.py`, `setup.py`, `templates/metis_tab.html` | L·★★ |
| 2.2 | **Fix settings incoherences** | Theme dual-write/single-read (server copy dead); persona split across `user-config.yaml` + `user-preferences.json` with overlay drift; duplicate preference files; model "selected" hardcoded to Sonnet; the `/metis-update` (data) vs `metis-update.sh` (code) name collision. | `metis_tab.py:399-423,1131`; `base.html:39-45,571`; `metis_tab.html:320` | M·★★ |
| 2.3 | **Generalize the update-menu declutter pattern** | Reuse `partials/_update_menu.html` to collapse crowded control clusters across surfaces into one action + on-demand popover with honest labels. Inventory every button first. | `partials/_update_menu.html`; all surface templates | M·★★ |
| 2.4 | **In-app one-command update (safe)** | `tools/metis-update.sh` exists but is terminal-only (non-tech user can't update), backs up only the DB (not the full data-dir list), doesn't run full migrations, and has no rollback/atomicity. Make it a dashboard "Update now" button: backup all data dirs → pull → additive migrate → verify → auto-rollback on failure. | `tools/metis-update.sh`; `backup-canonical.py`; `data-persistence-strategy.md:§2,§4` | M·★★★ |
| 2.5 | **Expose file-only settings as UI or accept as power-user-only** | `network-policy.json`, `models.yaml`, `tool-subsets.json`, `agent-registry.json`, governance docs are hand-edited. Decide per item: promote to UI (non-tech) or label explicitly power-user. | `system/config/*.json` | M·★ |
| 2.6 | **Self-host CDN assets (A11/C19)** | Bootstrap + fonts (+ any D3) load from a CDN, breaking the offline/local promise. Vendor them locally. | `templates/base.html` | S·★★ |

**Phase 2 acceptance:** a scientist changes any setting from one pane without editing a file; theme/
persona/model persist consistently across machines; "Update now" is a button that backs up, updates,
verifies, and rolls back on failure; the app loads fully offline.

### PHASE 3 — The ambient second brain ("nothing lost; it gets sharper on its own")
*Close the two open loops so the flagship promise is true by construction.*

> **Status (2026-08-11): 3.1 ✅ · 3.10 ✅ shipped to metis-ph.** `9bea309` (3.1 — pipeline Stage 7
> now runs question-conditioned hybrid vector+keyword recall over the real corpus, injected by
> construction; verified live: real papers/news/agent-runs surface for a research question),
> `807ada4` (3.10 — shared `_embed_episodic`; dashboard-captured ideas are now vector-indexed like
> chat ones; verified live embed→recall→cleanup). **Remaining:** 3.0 (pipeline EXECUTES RAG + agent
> hand-off, not just injects recall), 3.2 enforce reflexion write-back, 3.3 schedule drafting + move
> consolidation off the dashboard, 3.4 unify `_skill_path` so applied improvements reach the runtime,
> 3.5 surface the loop in UI, 3.6 token-budgeted retrieval, 3.7 semantic fallback router, 3.8
> continuous self-eval + drift heatmap, 3.9 persist cross-pollination links.

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

*End of the Keystone Roadmap. Update the status of items here as they are built; keep the promise-harness
score and drift heatmap as the objective "are we there yet" signal.*
