# Metis — Feature Backlog
# READ THIS FILE at the start of every session. Check off items as they are implemented.
# Add new requests here immediately when the user makes them — even if not building right now.
# Format: - [ ] description (requested, status, notes)

---

## NEW — From open-source AI tooling research + README/domain session 2026-05-12

- [ ] **Stop hook (auto handoff brief)** — `.claude/hooks/stop.mjs` fires at session exit; auto-calls `generate_handoff_brief()` + writes to `journal/`. (~2h)
- [ ] **PostToolUse hook (session pulse)** — logs tool name + elapsed time per call to session log. (~1h)
- [ ] **METIS_HOOK_PROFILE env var** — minimal|standard|full gate in `pre-tool-use.mjs`. (~30min)
- [ ] **Pre-compact hook** — saves state snapshot before Claude context compaction. (~1h)
- [ ] **Install profiles** — light/standard/full selectable in `setup-mcp.sh`. (~1d)
- [ ] **Domain install manifests** — per-domain `feeds.yaml` + vocabulary + agents installed selectively at setup. (~2d)
- [ ] **11 missing slash commands** — stub `.claude/skills/` files for course-builder, content-harvester, design-auditor, frontend-designer-builder, hr-talent, learning-architect, news-aggregator, rc-builder, research-architect, visualization-maker, data-analyst. (~3h)
- [ ] **Enterprise controls file** — `system/config/enterprise-controls.md` for institute deployments. (~2h)
- [ ] **Session-level injection tracking** — 3-strike counter in pre-tool-use.mjs → log to `security_events` table. (~2h)
- [ ] **.gemini/GEMINI.md** — Gemini AI interface config (google-genai already installed). (~3h)
- [ ] **Agent introspection skill** — explain routing decisions in plain language. (~3h)
- [ ] **/security-scan skill** — audit last session's tool calls against guardrails from Claude Code. (~2h)
- [ ] **Domain background packages** — social sciences, biomedical, economics, climate, psychology, law, education, nursing — each as `knowledge/domains/<field>/` package. (~1 week total, community contribution target)
- [ ] **metis-identity.json** — version, capabilities, install profile for AI interface discovery. (~1h)
- [ ] **Morning briefing richer structure** — narrative prose, 2-3 themes grouped, editor commentary, cross-references between stories (inspired by IHP newsletter model). Add feedback buttons (useful/not useful) per item. (~1d)
- [ ] **Feed source_type column** — `news_briefs` table needs `source_type` column distinguishing RSS items from scientific articles. (~30min)

---

## STRATEGIC — System-level improvements requested 2026-05-10

- [ ] **On-demand improvement scanner ("Metis Radar")** — A script/skill that Stan runs periodically to ask: "what new repos, tools, or techniques exist that could improve a specific part of Metis?" It searches GitHub + web per capability, compares with current Metis implementation, generates structured improvement proposals that flow into the existing self-improvement pipeline (same proposals table). Requested: "in the future this self-improvement needs to be present in the project on demand, a full script to question what we can find on the internet that would improve Metis." Design:
  - New skill: `/metis-scan [capability|all]` — e.g. `/metis-scan cross-pollination`
  - Reads a capabilities manifest (`system/config/capabilities-manifest.json`) listing each Metis feature + its current implementation description
  - For each capability: web search "best {capability} implementation 2026" + GitHub search → Claude compares ideal vs. current → generates proposal
  - Saves proposals to `improvement_proposals` table (same pipeline as reflexion-based proposals)
  - Can be scheduled monthly or triggered on demand
  - Stan reviews and approves/rejects each proposal
  - (~2 days to build: manifest JSON + skill + MCP tool + search integration)

---

## CRITICAL — Things the user keeps having to repeat

- [x] **Cross-pollination fires automatically after idea capture** — DONE 2026-05-06. Fixed: (1) `ideas.py` `_cross_pollinate_core` now searches `["content", "title"]` in ideas table; (2) `capture.py` INSERT uses `content` column + Archive-styled HTML; (3) `capture_modal.html` fully rewritten to Archive design with `m-drawer-top` animation class.

- [x] **Self-improvement promote actually edits skill.md on disk** — DONE 2026-05-10. `apply_proposal()` in `improvement.py` opens the agent's skill.md, backs it up as `skill.md.bak.<timestamp>`, writes the proposed content, and updates the DB row to `status='applied'`. Dashboard uses `/api/improvement/apply/{id}` endpoint. Preview diff at `/api/improvement/preview/{id}`.

- [ ] **Morning scan runs automatically at 07:00** — news radar and library scan should fire without manual click. Fix: APScheduler in FastAPI app OR Windows Task Scheduler script calling the content_scan endpoint. (asked repeatedly, ~1 day — Phase 10)

- [ ] **Inbox auto-processing** — files dropped in `inbox/` should be automatically picked up by the Librarian. Fix: inotify/watchdog watcher OR scheduled poll every 15 minutes. (asked repeatedly)

- [ ] **/metis_config rewrite for Python dashboard** — current wizard demands R + RStudio + 17 R packages. Walks through 10 wrong legacy tabs. Writes config keys no code reads. COMPLETE REWRITE needed: use actual 9 tabs, drop R requirement, add API key prompt. (asked in eval session, blocking for public release)

- [ ] **Empty states on all 9 tabs** — all tabs show "0" or blank on first use with no guidance. Each tab needs first-run copy: "Run /metis-library-setup to start" etc. (asked in eval session)

---

## HIGH — Requested, not yet built

- [x] **Meeting assistant built** — DONE 2026-05-06. Import form (paste transcript + metadata), auto-extraction of decisions/actions/follow-ups, cross-pollination on save, live assistant panel (type notes → see connections in real-time with 1.5s debounce), meeting detail view with structured sections, action items saved to meeting_actions table. Audio/Whisper transcription is NOT included (requires separate Whisper install — Phase 11 item).

- [ ] **WhatsApp mobile idea capture** — ideas from phone → Metis inbox → cross-pollinate while you sleep. webhook.py exists (Twilio stub). Needs: Cloudflare Tunnel for public URL, Twilio sandbox setup, link from capture_idea to cross_pollinate. (asked multiple sessions, ~1 day)

- [ ] **Meeting Memory cross-references projects and papers** — after a meeting transcript, Meeting Memory should auto-link action items to open projects and surface related papers. Currently: transcription only. (asked this session)

- [ ] **Connected tools panel in Metis tab** — show all registered MCP servers, their status (running/offline), tool count, last-used timestamp. (asked this session, ~1 day)

- [ ] **Automation status panel in Today tab** — show whether scheduled jobs ran today, what they found, whether any failed. (asked this session)

- [ ] **11 missing slash commands** — these agents are in CLAUDE.md routing but have no /<slug> command: course-builder, content-harvester, design-auditor, frontend-designer-builder, hr-talent, learning-architect, news-aggregator, rc-builder, research-architect, visualization-maker, data-analyst. (eval report, ~half day to generate from existing system-prompts)

- [x] **Security hook path fixes** — DONE 2026-05-10. pre-tool-use.mjs updated: patterns now use `\binbox\b`, `knowledge/library/disease-areas`, etc. matching current folder structure. Also added doi.org, crossref.org, zotero.org, ecdc.europa.eu, cdc.gov to domain allowlist.

- [x] **Inject prompt pattern lists unified** — DONE 2026-05-10. pre-tool-use.mjs now has 12 patterns aligned with guardrails.py. Both lists cover the same attack vectors. Comment in both files notes the sync requirement.

- [ ] **Personalisation config actually read** — user-config.yaml keys (news_radar.topics, data_protection.level, librarian.scan_interval) are written by wizard but no code reads them. Wire these to actual behaviour. (eval report, ~1 day)

---

## MEDIUM — Requested, partially done or deferred

- [ ] **Course builder end-to-end pipeline** — system-prompt exists, questionnaire exists, but no orchestration code and no /course-builder slash command. The Build buttons in Learning tab were fixed (now launch Claude Desktop) but the full automated build-from-scratch pipeline is not there. (asked multiple sessions)

- [ ] **Adaptive course research question input** — DONE this session (toggle panel + launchWithQuestion). But the full adaptive course flow (intake → curriculum → lessons → spaced repetition) is not automated end-to-end.

- [ ] **Statistics course Launch button** — DONE this session.

- [ ] **Zotero library gap papers import** — 59 missing HAT gambiense papers identified. DOIs provided. User needs to import them into Zotero. (provided this session)

- [ ] **Planner kanban Archive migration** — DONE previous session.

- [ ] **News surface as separate tab** — DONE previous session.

- [ ] **motion.css animations** — DONE previous session.

- [ ] **Metis desktop icon (brain)** — DONE this session.

---

## LOW — On the radar, not started

- [ ] **Perplexity MCP** — token-efficient web search, recommended in token-guardrails.md but not connected. Register: needs Perplexity API key.

- [ ] **Context7 MCP** — live documentation retrieval (`@upstash/context7-mcp`). Free. Register via `claude mcp add context7 -- npx -y @upstash/context7-mcp`.

- [ ] **Playwright MCP** — ADDED this session (registered in ~/.claude/settings.json). Gives Metis ability to browse and download papers from institutional access.

- [ ] **GitHub MCP** — ADDED this session (requires GITHUB_PERSONAL_ACCESS_TOKEN to be filled in settings.json).

- [ ] **Promote self-improvement proposal auto-commits to git** — after editing skill.md, git commit the change with a message like "Auto-improve: {agent} — {summary}". (follows from promote fix above)

- [ ] **PLANNING.md auto-update at session end** — RC Builder or Metis should write updated PLANNING.md for the active project at end of each session. Currently manual.

- [ ] **Knowledge graph edges between papers, ideas, projects** — Knowledge tab graph renders nodes but edges need cross-pollination data. (existing D3 graph needs data wiring)

- [ ] **Meeting recording 3 modes: Quick / Auto / Live** — described in workflows.md, only basic transcription exists.

- [ ] **Docker image** — README says "coming soon". Low priority for solo use.

- [ ] **Phase 12: test suite** — unit + integration + end-to-end. Zero coverage currently.

- [ ] **Rename /metis_config wizard** — rewrite for actual Python stack, actual 9 tabs, actual config keys that are read. Blocking for public release.

- [ ] **License file** — README says MIT. No LICENSE file exists yet.

- [ ] **README count fixes** — tools: 103/76 → reconcile to runtime count. Agents: 20+ → say 26. PII: 40+ → say 14. (blocking for public release)

---

## SESSION RULES

**At the start of every session: read this file. Note which items are still open.**
**When the user requests something: add it here before implementing, so it persists if the session ends.**
**When something is implemented: check it off with `- [x]` and the date.**
**When the user repeats a request: acknowledge it is on the backlog and build it before anything new.**
