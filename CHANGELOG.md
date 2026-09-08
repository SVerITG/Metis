# Changelog

All notable changes to Metis are documented here.

## [Unreleased]

### Added
- **Plan a run of days, on one row** — `day_plan` gained `kind='task'` + `task_id` (migration `20260906_day_plan_add_task_id`), so a single task can be planned onto a day without inventing a due date, and a multi-day commitment is one row that labels which day of the run today is. A plan is an *intention*, never a deadline: unplanning something therefore cannot edit the work, and the 61 open tasks that carry no date stay that way. Re-planning **extends** an existing run rather than skipping it — the idempotency guard used to return silently, so asking for five days when a one-day pin existed did nothing at all. `/tomorrow` preserves the span's length instead of setting `end_date = NULL`, which had silently collapsed a five-day run to a single day (Sep 6–7).
- **Today's plan strip** — `/api/partial/today/plan` plus `/api/today/plan/{add,toggle,tomorrow,remove}`. One compact line per intended item, projects and tasks together, with a picker that lists projects by open-task count. Replaces a panel that reported the past (three recently-touched projects and a paragraph each) with one that holds the day's commitments and, crucially, carries the control to add them: the planning store held **one** row while 61 tasks sat open, not because planning was unwanted but because no surface offered it. "Done" is authored by `tasks.status`, never a copy in `day_plan`, so the board and Today cannot disagree (Sep 6).
- **The Work list answers what you have actually touched** — the unfiltered view is ordered by `last_session_at`, never-opened last, and is flat rather than grouped, replacing a `display_order` nobody had ever set (so every project tied on 999 and the "order" was insertion order wearing a sort clause). Dragging is disabled there, because a drag would write an order the reader never sees take effect; manual arrangement lives on the per-category views, where it is visible (Sep 6).
- **Project categories you can own** — create, rename, merge, reorder and move projects between them, in collapsible sections that open only when something in them is alive; empty categories still get a heading, so a newly created one is not invisible (Sep 3).
- **A launcher row that reflects what a project can actually do** — the root cause was a missing write path: `external_path` was never editable after creation, so seven projects were folderless forever while the UI offered to open them (Sep 3).
- **A shelf is a reason for keeping, with a kind** — library categories carry purpose / tracking / attachment, which changes what the shelf *does* rather than labelling it; only one triage verdict may be negative (Sep 5).
- **Content-derived asset stamp, and one live tab at a time** — the cache-busting stamp was hand-typed (`styles.css?v=14`), so a stamp nobody remembered to change meant browsers kept serving the version they already had. It is now a hash of the two asset files' contents, exposed as the `asset_v` Jinja global via `_SHARED_GLOBALS` → `jinja2.defaults` (seventeen Jinja environments exist, some built lazily, so attaching to only the ones present at import time misses late-imported routers). Alongside it: the newest tab claims the session over a `BroadcastChannel` with a `localStorage` fallback, and older tabs draw a curtain offering the session back. A page cannot close a tab it did not open, so the guard never calls `window.close()` — one test asserts exactly that (Sep 2).
- **Library "Everything" window and a "Not yet decided" state** — 2,282 stored, scored, never-triaged papers were not reachable by any combination of the filters on offer. The longest window was 30 days and `catchup` collapses to nothing once a catch-up is recorded; `days == 0` is now an explicit branch, because the previous `days or 7` reads zero as absent and would have made "Everything" a silent synonym for "This week". Both filter groups became chips, and the fold opens itself when a non-default one is active, so a short list says why (Sep 1).
- **Add and remove from the surface you start on** — a one-line quick-add on Today, always present so it doubles as the empty state, plus per-row removal. Previously Today offered directions to another surface instead of a control (Sep 1).
- **Verification layer** — `verify_claim`, `verify_text_citations`, `verify_doi`, `library_coverage`, `citation_debt`, `audit_background_provenance`; deterministic Tier A (indexed source, page exists, figures and quoted strings present) and network Tier B (Crossref resolution + retraction, detected on four independent signals). No model in the path (Aug 24).
- **Artifact gate** — `tools/verify_citations.py` exits non-zero when a document cites a page that does not support its claim; conversation is annotated asynchronously instead, so the gate never slows a turn and never gets switched off (Aug 24).
- **Evidence weighing** — `weigh_evidence` (value spread, attached qualifiers, dropped caveats, omissions) and `check_for_newer_evidence`, so fact-checking covers the substance of a claim and not only its citation (Aug 24).
- **Focus areas** — `create_focus_area`, `set_focus_state`, `show_focus_areas`, `update_focus_overview`, `focus_brief`, `preview_focus_lens`. User-composed surfaces whose lens is a conjunction of keyword groups (OR within, AND across); shelf capped at 3 and refuses a fourth rather than evicting; archiving a focus leaves all notes, ideas and papers intact (Aug 24).
- **Agent decision memory** — `decisions_for`, `render_for_prompt`, `touch`, `show_agent_decisions`; `record_decision` extended with `agent_slug` as the single canonical writer. 65 standing decisions mined from past session summaries; `user_decisions` 2 → 85 rows (Aug 24).
- **33 dispatchable subagents** — every specialist registered in `.claude/agents/` with a bound model, so model assignment takes effect instead of being advisory; picker cost ~1,832 tokens (Aug 24).
- **Office bridge** — PowerPoint/Excel taskpane over HTTPS, deck round-trip into Metis honouring a user template, and a JSON API over the brain for non-Claude clients (Aug 12).
- **Backgrounds as portable packs** — see/switch/rebuild/remove a knowledge layer; layers can point at an external library; institutional PDFs via Zotero; `ph-foundations` textbook layer with curriculum-driven pack selection (Aug 13).
- **AI in Public Health course** — 16 lessons, 97 MCQs, 106 cards; plus `tools/check_course_launch.py` and `tools/audit_quiz.py` as standing gates (Aug 21).
- **Readable memory** — procedural memory is browsable rather than a count; decisions can be closed instead of restated; unified notes search; documents index on arrival (Aug 12–14).
- **Calendar planning** — day/week/month views; a course's remaining lessons can be laid into the plan (Aug 14).

### Fixed
- **172 controls rendered perfectly and could not fire** — `{{ x | tojson }}` inside a **double-quoted** HTML attribute is broken markup. `tojson` escapes `<`, `>`, `&` and `'` — deliberately not `"` — because it is designed for single-quoted attributes; in a double-quoted one the first argument terminates the attribute and the remainder becomes junk attributes. It only bites *string* values (an integer id renders bare and is harmless), which is why the identical line worked on one panel and failed on another according to the column type. 120 handlers in `work_all_tasks.html`, 48 in `work_projects.html`, 4 in `today_news_archive.html`; 17 source lines across 6 partials. Changing a project's category was impossible and mark-done/delete were dead on every task row — the backend was never involved and `move-category` worked first call when invoked directly. The July 2026 note reporting this class fixed was premature; it returned in a different disguise. Detect it on the **rendered page**, never in the template: `grep -cE 'onclick="[a-zA-Z]+\([^")]*"'` (Sep 6).
- **A panel that made nine paid API calls on its render path** — opening one surface fired nine sequential POSTs to `api.anthropic.com/v1/messages` and took 18.5s, on **every** view, against an idle control of zero calls in twenty seconds. `aggregate_reflexions()` themes reflexions with Claude Haiku whenever `ANTHROPIC_API_KEY` is set, once per agent per category. It measured as healthy in every test because a test process has no key and silently fell back to word frequency, returning in 0.01s — the defect was only reachable in the configured application. Themes now come from a machine-local cache with the model pass behind an explicit control that names its cost; render is 0.012s and makes no network call (Sep 6).
- **The promise harness reported the opposite of the truth** — it announced *"Agent run coverage: 0/33 agents have ever run — routing is broken"* while its own report, four sections earlier, counted 733 runs in 30 days. `test_agent_contracts.py` read `system/app/data/metis.sqlite`, the path retired in June 2026 when the live database moved to local disk, and `load_run_map()` degrades to `{}` on a missing file, so every agent scored zero. Three independent angles put the truth at 34 of 35 agents. Now resolved through `db.get_db_path()` — one author for the path — which also collapsed the agent warning count from 32 to 17, since most were downstream of the same dead path. Separately, `/planner` was asserted as 200 when it deliberately 302s to `/work` after the surfaces merged, failing every run for a surface behaving correctly. Floor: 60/2/3 → 62/0/4 (Sep 6).
- **Unattended recovery never ran on battery** — the scheduled task that restarts the dashboard had been installed by `register-autostart.ps1`'s fallback path, which prints a bare `schtasks /create /sc minute` for the user to run by hand. `schtasks.exe` defaults `DisallowStartIfOnBatteries` to **true** and offers no command-line switch to change it — only `/xml` can — and the fallback also drops the logon trigger. On a laptop that is no supervision for most of its life, while Task Scheduler showed Enabled / Ready / last result 0. The tell is the gap between last-run and the repetition interval (eight hours on a five-minute schedule), not any error. The fallback now generates XML: battery-safe, with logon and session-unlock triggers and an `ExecutionTimeLimit`, because `MultipleInstancesPolicy=IgnoreNew` means one wedged run otherwise blocks every later run indefinitely (Sep 6).
- **Semantic search had never worked from the dashboard** — `embed_one` applied the *document* prefix to queries and skipped normalisation, so ranking was noise presented as relevance; use `embed_query(normalize=True)`, and on unit vectors similarity is `1 - d²/2`. In the same pass, `literature_metadata` went 3,084 → 1,099 rows (64% were duplicates) and 2,282 scored-but-never-triaged papers proved unreachable from any combination of filters (Sep 2–3).
- **Two of the three Work views could never be shown** — the class that hid the inactive views is `!important`, so the view switcher had never worked and only the default had ever been reachable (Sep 3).
- **Four rival counts of one backlog** — the same quantity was computed in four places and they disagreed; 34 cancelled tasks were being drawn as live work. Reduced to one author, `db.live_task_sql()`, phrased as an exclusion so an unrecognised status surfaces as work rather than vanishing (Sep 3).
- **A write lock taken on a render path** — `CREATE TABLE IF NOT EXISTS` executed while drawing a panel takes a WAL write lock; it must never sit on a render path (Sep 3).
- **The base-shell builder published the unstripped edition after its own scrub had failed** — a `|| echo` swallowed a fatal error and defeated `set -e`, so the release proceeded with identity intact; and a branch pushed directly bypasses the scrub entirely, since it only runs when building base from `main`. Both closed. The maintainer's name was also removed from the working tree and from what two **public** repositories had already published (Sep 2–4).
- **A specialist whose runs were never recorded** — `methods-coach/skill.md` had no closing protocol at all: no `log_agent_run`, so its work left no trace on the Agents tab and it could never accumulate standing decisions, which is the only thing separating a specialist from a persona (Sep 6).
- **A short keyword was being stemmed instead of matched** — an acronym-shaped keyword matched as a substring, so a focus lens caught 23 of 4,103 briefs; short keywords now match as whole words with an optional plural (Sep 4).
- **Today said the same thing twice, and the two could disagree** — the plan strip carries "Work →" and its own add control while the panel below repeated "See everything in Work" / "Plan in Work"; worse, the strip could show a five-day commitment above a line insisting nothing was pinned, because they read different stores. The board was also titled "Tasks by status" when three of its four columns are date buckets, which made the one control that plans by horizon look misfiled (Sep 7).
- **The relevance scorer named a speciality** — the ranking model must not encode who the reader is (Sep 5).
- **Every write in the system failed for minutes after each restart** — `_scan_feeds` opened one connection, wrote, and committed once at the end, with the network fetch for every subsequent feed happening inside that transaction. In WAL mode a write transaction is exclusive, so for its duration nothing anywhere could commit — not the dashboard, not the MCP servers. The boot scan starts 25s after the dashboard, so that was the state of the system for minutes after every restart. Measured with no HTTP traffic at all: lock taken at t+40s, still held at t+300s, every write 500 from t+90s. Now committed per feed — 0 of 14 writes failed over the same window, and a scan that dies halfway keeps what it already found (Sep 1).
- **Two SQLite connection leaks** — `with sqlite3.connect(...) as conn:` is a *transaction* context manager: it commits and leaves the connection open. The scheduler's inbox job leaked one per fire, and the inbox watcher's writer skipped its `close()` on every error path, abandoning a connection mid-DDL (Sep 1).
- **Deleting a task had never worked** — `/api/task/{task_id}/delete` was typed `int` while task ids are strings, so FastAPI rejected every real id with 422 before the handler ran, and all three callers ignored the status and redrew regardless, so the row returned on the next load. Every sibling route in the file was already `str` (Sep 1).
- **The morning brief's fold now reports its own state** — it always collapsed and nothing on screen agreed; the button was gated on the server's `collapsed` flag, so it read "read the rest" while the rest was open. Clamped to three lines when closed, the panel goes 399px → 208px (Sep 1).
- **News density** — the headline pitch was 40px for a 19.5px line, because the action bar beside it set the row height; 24px buttons (still the WCAG 2.2 AA minimum target) give a 30px pitch, eight stories where six fit (Sep 1).
- **Today reordered around what the surface is for** — the dispatch was the longest panel and sat sixth of eleven, burying the boards, memory zone and health footer under a screen of news; it is now last, folded, and capped at 60vh. Cross-pollination moved to Reflection, where thinking happens. Two panels named "New in your field" showed opposite answers two inches apart, because one counted unread library items and the other the week's feed scan; the second is now named for what it is. A reset also missed a fifth counter (`news_briefs.seen_at`), so no reset could move the News rail (Aug 31 – Sep 1).
- **`.gitignore` gap on config backups** — the rule was `*.bak.20*`, but this repo's config writers produce the hyphenated form (`.bak-20260828T151953`), so two `.local.` personal-config backups sat untracked and would have been swept up by any `git add -A`. Both shapes are ignored now (Sep 2).
- **Ten faults from the two-computer split** — embedding cache treated as a search path rather than a pinned constant; stale-install detection by file contents not timestamps; one owner for the `inbox_items` DDL; `);` inside a SQL comment no longer truncates a table definition; `tools/restart-dashboard.sh` waits for the PID to change rather than for `/health` (Aug 24).
- **Redactor ran partially while reporting success** — an invalid `re.sub` replacement raised inside a `git rebase --exec … || true`, so the identity strip stopped mid-run and three files kept personal paths in committed trees. The pattern is removed as redundant, a failing substitution now aborts the whole run, and the redactor itself is unpublished (Aug 25).
- **Front-page and surface repairs** — 79 open tasks invisible behind a missing column; four blank Today panels; three Teach routes returning empty divs against 11 courses; meetings without a primary key; news briefs with NULL primary keys and raw HTML rendered as text (Aug 12).
- **Today Surface sprint** — resume card, literature discovery, learning nudge, system health monitor, deadline nudges, brief bridges, memory pulse, focus memory, session thread, and trust badge redesign (Jul 13).
- **Meeting assistant upgrade** — Whisper GPU activation with 3.5s chunks, Meetily transcript import, Voxtral cloud transcription backend (requires MISTRAL_API_KEY), speaker diarization improvements (Jul 13).
- **Memory Cortex** — unified memory gateway with `recall()` (searches all 6 memory layers with RRF fusion) and `remember()` (auto-classifies into episodic/semantic/procedural/note); multi-scope identity (agent_id, project_id, scope columns); richer session bootstrap with semantically relevant memories; Memory Health dashboard tab (Jun 18).
- **Progressive tool disclosure** — `find_tools()` / `load_tool_group()` / `list_tool_groups()` park non-core tools at startup and expose them on demand via `send_tool_list_changed()`; 196→~80 exposed, ~130 parked, nothing unreachable (Jun 17).
- **Agent-aware tool titles** — every MCP tool now shows which specialist agent owns it (e.g. "Metis · Librarian — Search Literature"); 96 tools carry agent labels (Jun 18).
- **Script Analyzer** — 4 new MCP tools (`analyze_script`, `scan_project_scripts`, `generate_profiling_script`, `ingest_profiling_output`) for the "send code, not data" pipeline; `/code-intake` skill (Jun 18).
- **Data protection hardening** — `/safe-analysis` workflow ("send code, not data"), Data Guardian with all 11 PII patterns wired through one shared `scan_content()`, pre-tool file-content guard that peeks at data file headers before Read, write-side data-authorization gate on Write/Edit for data-file extensions (Jun 4–16).
- **Cybersecurity deny-rules** — hard-deny reads/writes of `.env`/`~/.ssh`/`~/.aws`/`*.pem`/credentials at the hook; outbound network scoped to domain allowlist (Jun 16).
- **Learnable agent routing** — routing database (not hardcoded list), reaches 21 specialists (was 10), word-boundary matching, learns from user preferences via `record_routing_preference` (late Jun).
- **Personalization layer** — standing preferences and decisions (coding style, citation format, methodology defaults) applied on every request; `record_decision` / `recall_decisions` / `evaluate_against_layers` tools (late Jun).
- **Semantic relevance scoring** — content_scan ranks scanned items by closeness to user's actual corpus via local interest-profile centroid; numeric `relevance` column (Jun 5).
- **Two-button no-API brief** — "Update with Claude" opens Claude Desktop via `claude://` deep link (subscription, no API key); "Update (API)" uses existing path; saves back via shared DB (Jun 5).
- **Brainstorm upgrades** — creativity dial (Grounded/Balanced/Bold), scoped menu (This work · A topic · Mindmap · Cluster), "✦ BRAINSTORM THIS" button on Today brief, Claude Desktop deep-link hand-off (Jun 5).
- **Daily ↔ Weekly brief toggle** in brief header (Jun 5).
- **Working-loop reflexion** — three-tier generate→verify: post-tool-use.mjs syntax-checks code on the spot; `/verify-work` skill with deterministic signals + independent skeptic sub-agent; periodic `/metis-self-reflexion` (Jun 5).
- **Evaluation suite upgrades** — dashboard-up PREFLIGHT + SKIP status, deterministic floors (py_compile sweep + UI/a11y sanity), drift time-series, mandatory independent verifier on high/critical findings (Jun 5).
- **Zotero local connector** — `sync_zotero_local(db_path)` reads a local `zotero.sqlite` without API key (Jun 16).
- **Semantic Scholar source** — `search_semantic_scholar(query)` via free Graph API (Jun 16).
- **PII redaction tool** — `redact_data_file(path)` returns a masked preview with sensitive columns pseudonymised (Jun 16).
- **Output rail** — `scan_outgoing(text)` pass/block verdict + masked version before sending (Jun 16).
- **Knowledge graph markdown export** — `export_knowledge_markdown(out_dir)` generates Obsidian-style vault with `[[wikilinks]]` (Jun 16).
- **Project customization** — rename, category, colour (accent_color), multi-tag, category/tag filtering in Work tab; backend `/api/project/update/{id}` (Jun 16).
- **Desktop project-tracking** — `metis` router prompt now scaffolds tracked projects; `create_project_full()` + `create_task()` from Claude Desktop (Jun 4).
- **Dashboard autostart toggle** — Metis tab → "Startup & persistence" card; registers/removes Windows autostart task over WSL interop, no admin (Jun 22).
- **MCP prompts for Claude Desktop** — 42 prompts (1 `metis` router + one per agent + workflow prompts) in the prompt picker (Jun 2).

### Changed
- **Production stability overhaul** — live DB relocated off OneDrive to `~/.local/share/metis/metis.sqlite` (WAL-safe ext4); removed import-time DB calls (now run in lifespan); supervisor restart loop with backoff in `run.sh`; adopt-don't-kill singleton with `flock` launch-lock; `run.sh` binds `127.0.0.1` (was `0.0.0.0`); persistent rotating logs at `system/config/logs/dashboard.log` (Jun 19–22).
- **MCP server tool count** — 165→210+ registered tools (post progressive disclosure + new tool files).
- **Constitution v1.1** — added no-data-rebuild, no-credential-access, network-allowlist, prefer-safe-analysis rules (Jun 16).
- **Project listing reads registry** — `get_project_status()` now reads `projects` table (14 projects) instead of `projects/active/` folders (2); priority-sorted with task counts (Jun 6).
- **Cross-pollination expanded** — `assemble_brainstorm_context` gained `projects` + `notes` sources; keyword search also searches project titles/descriptions/next_steps (Jun 6).
- **Installer requirements** — `requires-python` capped at `<3.14` (onnxruntime/pyreadstat/pymupdf lack 3.14 wheels); installer pre-flight checks Python 3.10–3.13 + ensurepip (Jun 4).
- **requirements.txt and pyproject.toml** — corrected voice dependencies (resemblyzer, faster-whisper); added `[diarization]` extras group; regenerated pinned freeze from working venv (Jul 13).
- **README** — tool count corrected to 210+ (was 187); agent count "30+" kept; tool subset loading description updated for progressive disclosure.

### Fixed
- **Split-brain DB** — ~12 code paths hardcoded the OneDrive DB path; all routed through `get_db_path()` (Jun 19).
- **Reflected-XSS** in search; broadened PII detection (international phone formats, household-precision GPS) and prompt-injection detection (Jun).
- **File tracking recursion** — `_ensure_tracked_files()` called itself instead of running CREATE TABLE DDL; all file-tracking tools were broken since Apr 13 (Jun 4).
- **Dark mode default** and tab 500 error on `_metis_user_name` missing.
- **Orphaned tracked_files** — relabelled 3,451 orphaned entries to correct project slugs (Jun 5).
- **Prompt registration** — `register_prompts()` false failure when `_AGENTS_DIR` absent in verify subprocess; now handles missing dir gracefully (Jun 4).
- **API-key banner save** — was missing the confirm header (403) (Jul).
- **Dashboard reliability** — offline model load, brief import/log, session dedup (Jul).

## [0.2.0] — 2026-05-27

### Added
- **Live meeting voice recognition** — Speaker profiles enrolled via audio sample or browser recording. Cosine similarity matching (resemblyzer GE2E embeddings) auto-identifies enrolled speakers during transcription. Running mean across samples improves accuracy over time.
- **Speaker management UI** — Voice Profiles panel in Meetings tab: enroll, list, delete. Shows enrollment count per speaker.
- **Biostatistician agent** — R package development, simulation studies, sample size/power calculations, Monte Carlo methods, CRAN-ready package scaffolding.
- **Dashboard Engineer agent** — Restored and rewritten. Owns FastAPI + HTMX dashboard architecture, tab design, and partial rendering patterns.
- **7 new dashboard partials** — Knowledge topic coverage, teaching courses, morning brief, agent directory, and more.
- **Memory loop** — Session bootstrap, working memory, model registry, and persona discipline are now fully wired.
- **Comprehensive eval toolkit** — `tests/functional/run_metis_promises.sh` harness, promise registry, self-reflexion skill.
- **Knowledge tab** — knowledge layer browser, unified search, coverage gap analysis, recently-added strip.
- **Research timeline** — `record_research_finding()`, `query_research_timeline()`, `list_research_entities()` for tracking evolving beliefs over time.
- **Session consolidation** — `consolidate_session_memory()` distils session history into persistent episodic memory.

### Fixed
- Live meeting button non-functional when navigating to Meetings tab via HTMX (script now loaded globally in base.html).
- Dark mode default and tab 500 error on `_metis_user_name` missing.
- `prefers-color-scheme` media query removed — Metis is dark-only.
- Zotero sync, DB commit bug, `.env` cleanup.
- Setup hooks: removed hardcoded username path in stop hook.

### Changed
- MCP server bumped to **0.2.0**.
- README: MCP tool count corrected to 165+ (was 76+).
- README: Outbound services table expanded — CrossRef, HuggingFace, Google Drive, Gemini now documented.
- `requirements.txt`: `resemblyzer`, `webrtcvad-wheels`, `soundfile` added for voice recognition.
- `schema.sql`: `speakers` table added.

## [1.0.0] — 2026-05 (initial public release baseline)

### Added
- 34-agent research system with full MCP tool access.
- 9-tab dashboard (Today, Knowledge, Meetings, Learning, Work, Thinking, Planner, Teach, Metis).
- FastAPI + HTMX + SQLite stack, running fully locally.
- MCP server with 165 registered tools via FastMCP.
- Live meeting assistant with Whisper transcription and diarization.
- PDF knowledge bases (epi-methods, ph-background, hat-specialist) with vector search.
- Self-improvement loop: reflexion → proposal → approval → application.
- Data protection: PII detection, injection probes, AES-256 encryption, machine-readable constitution.
- Morning intelligence brief: papers, news, surveillance alerts, focus recommendation.
- Voice capture and transcription (faster-whisper, fully local).
- Course builder: intake → harvest → curriculum → draft → review → publish.
- Knowledge graph, brainstorm engine, research timeline.
- WSL2 + Windows installer (Inno Setup + PowerShell), macOS bash installer.
