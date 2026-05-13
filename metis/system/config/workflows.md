# Metis Workflows

Metis is **workflow-defined**: the features exist to serve specific ways of working. These are the primary workflows.

---

## Workflow map

| # | Workflow | Entry point(s) | Core agents |
|---|----------|---------------|-------------|
| 1 | **Morning start** | Metis dashboard → Control Room | News Radar, Librarian |
| 2 | **Idea capture (mobile)** | WhatsApp → Twilio → MCP | capture_idea |
| 3 | **Idea capture (desktop)** | Ideas tab → "+ New idea" | capture_idea, cross_pollinate |
| 4 | **Brainstorm session** | Ideas tab → context selector → start session | Metis, domain agents |
| 5 | **Research session** | Research tab → open article → work in Word → "Scan for updates" | Research Architect, Writing Partner |
| 6 | **Literature intake** | Drop PDF in inbox OR Dropzone tab | Librarian |
| 7 | **Meeting** | Meetings tab → record (3 modes) or import transcript | Meeting Memory |
| 8 | **Project work** | Projects tab → launcher button → work in IDE | RC Builder (for Metis work) |
| 9 | **Deep query / routing** | Claude Desktop or Claude Code via MCP | Metis → any agent |
| 10 | **End-of-day journal** | Ideas tab → "Journal entry" | Journal + cross_pollinate |
| 11 | **Build / extend Metis** | Claude Code → `/metis` or RC Builder | RC Builder |

---

## Workflow 1 — Morning start

**Trigger:** Open Metis dashboard  
**Steps:**
1. Control Room loads — checks if News Radar and Librarian ran today
2. If yes: shows morning brief (news items, new literature, WhatsApp ideas from overnight)
3. If not: shows [Run News Radar] and [Run Librarian] buttons
4. User reviews priorities, open tasks, and inbox items

---

## Workflow 2 — Idea capture (mobile)

**Trigger:** WhatsApp message to Metis number  
**Steps:**
1. Twilio webhook receives message → calls `capture_idea(content, source="whatsapp")`
2. Idea stored in SQLite with auto-extracted tags
3. Cross-pollination runs: surfaces connections to library, meetings, recent news
4. Next time dashboard opens: idea visible in Ideas tab with connections

---

## Workflow 3 — Idea capture (desktop)

**Trigger:** Ideas tab → "+ New idea" button  
**Steps:**
1. User types idea
2. `capture_idea()` saves to SQLite
3. `cross_pollinate()` finds connections
4. Connections displayed in right panel
5. Optional: launch brainstorm session from this idea

---

## Workflow 4 — Brainstorm session

**Trigger:** Ideas tab → Brainstorm mode  
**Steps:**
1. Select context sources (multi-select): scientific library, recent literature, meetings, journal, research articles, projects, past ideas, news, contacts, drop file
2. Enter topic or question
3. Click [Launch brainstorm]
4. Metis assembles context → routes to appropriate domain agent(s)
5. Chat interface opens — user thinks out loud, Metis cross-pollinates in real time
6. Session saved with: topic, context sources used, output summary, linked idea IDs

---

## Workflow 5 — Research session

**Trigger:** Research tab or direct file work  
**Steps:**
1. Open article from Research tab ("Open in Word" button)
2. Work in Word / external tool
3. Return to Research tab → click [Scan for updates]
4. Dashboard shows which tracked files changed and when
5. Optional: "Add a session note?" → saved as journal entry linked to that article

---

## Workflow 6 — Literature intake

**Trigger:** Drop PDF in `inbox/` OR Dropzone tab  
**Steps:**
1. File appears in Dropzone tab intake form (or `inbox/`)
2. Librarian agent analyzes: metadata, methods, findings, relevance
3. Entry added to `library_seeded` table with tags
4. Cross-links created to related ideas, meetings, projects

---

## Workflow 7 — Meeting

**Trigger:** Meetings tab  
**Modes:**
- **Quick:** Record audio → stop → add metadata → transcript saved
- **Auto:** Record → stop → Meeting Memory auto-analyzes → metadata prompt
- **Live:** Record + real-time cross-pollination panel showing connections as you talk

---

## Workflow 8 — Project work

**Trigger:** Projects tab → launcher button  
**Steps:**
1. Select project from list
2. Click launcher (VS Code, RStudio, Word, Explorer — based on project type)
3. Work externally
4. Return to Metis: check tasks, log progress notes, update status

---

## Workflow 9 — Deep query / routing

**Trigger:** Any Claude interface with MCP connected  
**Steps:**
1. User sends request to `/metis`
2. Metis analyzes intent, selects agent(s), announces routing decision
3. Agent(s) execute, write output to `outputs/reviews/{agent}/`
4. Run logged to `agent_runs` table
5. Summary returned to user

---

## Workflow 10 — End-of-day journal

**Trigger:** Ideas tab → "Journal entry"  
**Steps:**
1. User writes free-form reflection
2. Mood and energy auto-extracted or manually tagged
3. Contacts mentioned → auto-linked to contact cards
4. Glossary terms highlighted
5. Cross-pollination: surfaces connections to today's work, ideas, library items

---

## Workflow 11 — Build / extend Metis

**Trigger:** Claude Code → `/rc-builder` or any Metis build request  
**Steps:**
1. RC Builder agent loads architecture context (config.py, app.R, token-guardrails.md, red-lines.md)
2. Plans change, confirms scope with user
3. Implements: MCP tool / R module / agent skill / migration
4. Writes session report to `outputs/reviews/implementation/YYYY-MM-DD_[task].md`
5. Lists: completed, skipped, issues found, how to verify

---

*See also: `system/red-lines.md`, `system/token-guardrails.md`*
