# Metis — Data Persistence, Ships-Empty & Learnable Routing strategy

> The organizing principle: **separate CODE from DATA.** Code ships and updates and
> is replaceable. Data is the user's, lives on their machine, and must survive every
> update. Routing rules are DATA, not CODE — which is what makes them persistent,
> customizable, and learnable.

---

## 1. The CODE / DATA boundary

| | CODE (ships, updates, replaceable) | DATA (user-owned, persists, never lost) |
|---|---|---|
| What | agents, skills, dashboard, MCP server, **routing logic**, default config | RAG/background indexes, notes, ideas, R-code repos, project tracking, sessions, all memory layers (episodic/semantic/procedural/working/reflexive), **routing rules** |
| Where | the git repo / installed package | `system/app/data/metis.sqlite`, `knowledge/` indexes, `inputs/code/`, `projects/`, `journal/`, the user's data dirs |
| On update | replaced wholesale | untouched; migrated forward, never overwritten |
| Ships | with sensible **defaults/seeds** only | **empty** of user content |

**"Ships empty"** means: a fresh install contains no user notes, no ideas, no indexed
papers, no projects — only the code and a few *default config seeds* (e.g. the routing
seed rules, default agent set). The first run creates the data layer empty and seeds
only config.

---

## 2. Update without data loss

Updating Metis = replacing the CODE while leaving the DATA layer in place.

Requirements (the contract every update must honor):
1. **Never write user data into the repo.** The `.csv`/`.sqlite`/data gitignore rules
   already enforce part of this. The data dirs live outside (or are excluded from) the
   shipped tree.
2. **Schema migrations, not drops.** When the DB schema changes, run additive
   migrations (`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE … ADD COLUMN`) that preserve
   existing rows. Never `DROP`/recreate a user table on update. (The new
   `agent_routing_rules` table follows this — `CREATE TABLE IF NOT EXISTS`, seed only
   when empty, so an update never clobbers learned rules.)
3. **A documented data-dir list** (institutional memory — see §4) that the installer /
   Release Coordinator treats as sacrosanct: back it up before an update, restore/leave
   it after.
4. **Backups before migration** — `backup.py` already snapshots the DB; an update should
   trigger an (encrypted) backup first.

> Open implementation task: an explicit `metis update` flow that (a) backs up the data
> dirs, (b) pulls new code, (c) runs additive migrations, (d) verifies the data layer is
> intact. Today this is manual; it should become one command with the data-dir list as
> its contract.

---

## 3. Routing is DATA, and it learns

The routing rules moved out of a hardcoded Python list into the **`agent_routing_rules`**
table (in the persistent DB). This is what your question asked for:

- **Seeded, not baked.** Ships empty; on first run the table is seeded from
  `_DEFAULT_ROUTING_SEED` (sensible defaults). After that it's user data.
- **Matched smartly.** Leading word-boundary matching (`paper` matches `papers` but `ui`
  never matches inside `build`), most-specific-first (low `priority`), so a broad keyword
  can't steal a specialist.
- **Learnable.** When routing is uncertain or falls to the generalist, Metis asks the
  user: *"Should I always route requests like this to <agent>, or just this once?"* The
  answer is recorded via `record_routing_preference(phrase, agent_slug, scope)`:
  - `scope="always"` → a permanent, high-priority rule (`source='user'`, beats seeds),
  - `scope="once"` → not stored.
- **Measurable.** Every decision that finds no specialist is flagged `uncovered` (routed
  to the generalist `metis`), so the un-routed rate is a visible metric, not a silent
  default. Each rule carries a `hits` counter, so popular routes and dead seeds are both
  visible.
- **Persistent.** Because the rules live in the DATA layer, they survive every CODE
  update — your routing preferences are part of institutional memory.

### The no-match strategy (explicit policy)
1. Try the DB rules (seeded + user-learned), most-specific first.
2. No match → the generalist `metis` handles it, but the turn is marked `uncovered`.
3. Over time, `uncovered` turns are the signal to either (a) ask the user to teach a new
   rule, or (b) add a seed. A future enhancement: an **LLM fallback router** for genuinely
   ambiguous phrasing the keyword table can't reach (the API is available) — keyword rules
   stay the fast, deterministic, user-owned first pass; the LLM is the backstop.

---

## 3b. The personalization layer — the decision/preference database

Metis must **grow with the user**: learn their preferences and adapt, not ask the same
thing twice. This is the `user_decisions` table (in the persistent DB) — the "decision
database":

- **What it holds:** standing preferences and decisions — coding style ("tidyverse, never
  base apply"), citation format, methodology defaults, recurring article/dataset
  references, naming conventions, workflow choices. Categorized (`preference | coding |
  citation | methodology | writing | article-ref | dataset | routing | other`).
- **How it grows:** `record_decision(decision, category, context, scope)` — called whenever
  the user states or confirms a standing preference. `scope='always'` persists; `'once'`
  is acknowledged but not stored.
- **How it's used:** `recall_decisions(category)` is pulled into context assembly on every
  request, so responses already respect the user's preferences. Personalization, not
  repetition.
- **Persistent:** part of institutional memory — survives updates, stays on the machine.

## 3c. The request lifecycle — every request passes through every layer

This is the living system: a request is not just routed, it is **threaded through all the
memory and rule layers, the answer is evaluated against them, and the result feeds back**.

```
  USER REQUEST
     │
     ▼
  1. PERSONA memory        who the user is, voice/tone contract (metis-persona.md)
     │
     ▼
  2. INSTITUTIONAL memory  notes · ideas · projects · sessions · RAG/background · reflexions
     │
     ▼
  3. DECISION/PREFERENCE   recall_decisions() — coding/citation/method/article prefs
     │
     ▼
  4. ROUTING database      agent_routing_rules — which specialist (seeded + learned)
     │
     ▼
  5. AGENT + its TOOLS     the chosen specialist executes with its tool subset
     │
     ▼
  6. EVALUATE the answer   does it respect persona · institutional facts · preferences?
     │                      (the Critic agent / a self-check before returning)
     ▼
  7. RECORD + SUGGEST      log the run + reflexion; if a new standing preference or routing
     │                      choice surfaced, ASK "always or once?" and record_decision /
     ▼                      record_routing_preference; suggest an improvement proposal
  RESPONSE  (the layers are now richer for the next request)
```

Stages 1–5 + 7 already exist in `run_metis` (pipeline stages); **3 (decision recall),
6 (evaluate-against-layers), and the active-learning prompts in 7 are the new growth.**
The goal: every request makes the next one better-personalized — Metis is something
living that grows with the user and is routed through this loop every time.

## 4. Institutional memory — the full data-dir list

Everything below is the user's, persists across updates, never leaves the machine:

- **The canonical live DB** — `~/.local/share/metis/metis.sqlite` (resolved by
  `config.resolve_live_db`). It holds ideas, notes, projects, tasks, sessions, all memory
  layers, **`agent_routing_rules`**, **`user_decisions`** (the decision database),
  agent_runs, reflexions, daily insights, consent ledger.
  ⚠ **It lives on the native filesystem on purpose — NOT on OneDrive** — because SQLite's
  WAL + OneDrive sync corrupts the DB (the 2026-06-19 outage). The copy under
  `system/app/data/metis.sqlite` is a **stale mirror**, not the source of truth.
  **Closed:** `tools/backup-canonical.py` takes a consistent **static** snapshot (no live
  WAL) and writes it to the OneDrive-synced `system/app/data/cloud-backups/` dir, so it is
  cloud-recoverable if the disk dies. **Deliberately unencrypted** — OneDrive is considered
  safe enough, and an encrypted backup whose key is lost is just unrecoverable data; a plain
  static file restores by copying it back, no key. (`tools/metis-update.sh` also snapshots
  the canonical DB before every update.) Remaining: schedule `backup-canonical.py` daily.
- `knowledge/` — indexed library, domain/background RAG corpora, courses.
- `inputs/code/`, registered R-code repositories + data dictionaries.
- `projects/`, `journal/`, `outputs/` — project cards, session handoffs, agent outputs.
- `system/config/user-config.yaml`, `user-preferences.*` — identity & preferences.
- Local PII/override files (gitignored) — institute-specific PII patterns.

**Release Coordinator** must never propagate any of these to a public remote (already in
its contract), and **update flows** must never overwrite them.

---

## 5. Status (2026-06)
- ✅ Routing moved to DB (`agent_routing_rules`), seeded, word-boundary, priority-ordered,
  21/35 agents reachable (was 10), `uncovered` flagged, `record_routing_preference()` added.
- ✅ `tests/functional/routing_eval.py` is the regression guard (10/10 covered set).
- ⏳ Expose `record_routing_preference` as an MCP tool so Metis can call it mid-conversation.
- ⏳ One-command `metis update` flow with the data-dir list as its contract + pre-update
  encrypted backup + additive migrations.
- ⏳ LLM fallback router for `uncovered` turns.

---

## 6. Run targets & installers (who runs Metis, and how)

Metis is cross-platform Python (FastAPI dashboard + MCP server); none of the stack
requires Linux. WSL is the *most fragile* Windows path (env-var invisibility,
OneDrive/DrvFs WAL corruption, path translation, interop). So Metis ships **multiple
run targets**, each with its own installer, split by audience:

| Target | Audience | Installer | Stability | Notes |
|---|---|---|---|---|
| **Bundled `.exe`** (PyInstaller) | **End users** (default) | one double-click `MetisSetup.exe` | ★★★ | No Python, no WSL, no venv. The non-technical path. **Primary user installer.** |
| **Native Windows Python** | Developers / power users on Windows | scripted venv install | ★★★ | No WSL layer → removes env-var, DrvFs/WAL, path-translation issues. |
| **Native macOS / Linux** | Developers | `setup-mcp.sh` | ★★★ | Already native; no WSL. |
| **Docker** | Developers / servers | `docker-compose` | ★★ | Reproducible; Docker Desktop itself is heavy (WSL2/Hyper-V). |
| **WSL** | Developers only (legacy) | current Windows path | ★ | Keep as dev fallback; **not** the recommended user path. |

**Direction:** the **`.exe` is the default for end users**; native Windows Python / macOS /
Linux / Docker are **developer** targets; WSL is demoted to a legacy dev fallback. Moving
the user default off WSL removes the largest class of "Metis is down" causes (all the
boundary issues this strategy documents).

Build status: the PyInstaller scaffolding for the bundled `.exe` now **exists** at
`system/install/installer/pyinstaller/` (launcher with `dashboard`/`mcp` subcommands, spec,
Windows build script, README) — syntax + dispatch validated. ⏳ The `.exe` itself is **not yet
built** (needs a Windows Python host: `build-bundled-exe.ps1`) and the Inno `bundled`
`DefaultType` wiring is the remaining step. The Inno Setup developer installer + Docker matrix
already exist. The Release Coordinator owns building/shipping these variants (see its skill).
