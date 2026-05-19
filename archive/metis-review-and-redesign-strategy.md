# Metis — Review and Redesign Strategy

*Version 0.1 — A full audit of the current Metis dashboard, agent layer, data protection model, and workflow coverage, with concrete recommendations for the redesign that positions Metis as an AI gateway for researchers.*

---

## 1. The core insight that should drive everything else

Before I review anything specific, I want to name what I believe is the single most important framing shift for Metis, because every recommendation in this document follows from it.

Right now Metis is built like a personal productivity system for one researcher who happens to understand AI. The language in the README, the assumptions in the CLAUDE.md, the structure of the dashboard tabs, and the way the agents announce their routing all presume a user who already knows what an MCP server is, what a skill is, why you would pick Sonnet over Opus, and what "cross-pollination" means. That user exists — he is sitting at this keyboard right now — but he is not the person Metis needs to serve if this is going to be open source and genuinely useful to researchers.

The researcher who will download Metis has a different problem. She is paralyzed by AI. She knows AI is supposed to help her, she has tried ChatGPT and Claude a few times, and every time she hit the same three walls: she did not know what to ask, she did not know how to give it context, and she was afraid to paste her research data into a browser window owned by a company. She closed the tab each time and went back to her old workflow. The productivity gap is not that she lacks information about AI — the productivity gap is that AI feels like a tool designed for someone else.

**Metis is the answer to that paralysis.** It is the AI gateway that removes the three walls. It knows what to ask because you tell it what you are doing and it picks the right agent. It knows the context because it has already cataloged your papers, your meetings, your ideas, and your projects. And it protects your data because the red lines are not a feature you opt into — they are the floor beneath every single call. You do not have to learn prompting. You do not have to learn agents. You do not have to learn what an MCP is. You point, click, talk, and Metis handles the rest.

Every recommendation that follows — every tab that should be collapsed, every workflow that should be added, every piece of the interaction pipeline — exists to make that framing real. A researcher should be able to install Metis and, within twenty minutes, feel that she has safely asked an AI to do something useful with her research, without knowing any of the words that AI practitioners use.

## 2. What is wrong with the current dashboard

I want to be direct here because the honest answer is the useful one. The current dashboard is impressively engineered and clearly the product of a lot of thoughtful work, but it suffers from three problems that compound each other, and the combination is why it does not feel visually pleasing or professional even though the individual pieces are fine.

**Problem one: there are too many top-level tabs.** Twelve tabs is beyond the working memory of a non-technical user. The current nav bar has Control Room, Library, Research, Projects, Meetings, Notes, Ideas, Planner, News, Learning, Dropzone, and System. After the fourth tab a researcher stops reading labels and starts guessing. She cannot build a mental model of where things live. Notes and Ideas are conceptually one thing; Projects and Planner overlap heavily; Library and Research are two views on the same underlying literature; Dropzone is a single action that does not need a whole tab; News is a feed that belongs inside Control Room; Learning is a tab she will visit twice a year; System is configuration and should hide behind a gear icon. The sum of all this is that a researcher opens the dashboard and immediately feels the cognitive cost of choice. That cost is the opposite of what we want to deliver.

**Problem two: the Control Room is itself crowded.** I counted eleven separate visual panels on the Control Room view: project quick-launch, morning brief, KPI strip with four tiles, GitHub status, system snapshot, today's insight, new publications, latest news brief, project boards, recent files table, and all open tasks table. That is not a command center — that is a status page from an observability dashboard. A researcher arriving in the morning should see one greeting, one short brief, and one clear next action. Everything else is noise until she asks for it. The discipline of a good morning view is subtraction, not addition.

**Problem three: the visual language is fighting itself.** The CSS is genuinely well-written — the macOS-inspired design tokens, the blur effects, the color palette are all tasteful. But the density of content on each page fights the style. When you pack eleven panels into a view, even the most elegant CSS starts to look cluttered, because the panels butt against each other and there is nowhere for the eye to rest. The fix is not to rewrite the CSS. The fix is to give each page fewer things to say, with more space around each one. Good visual design is about silence between elements, not the elements themselves.

There are smaller issues beyond these three — empty states probably look broken on a fresh install because there is no sample data, the data loading is synchronous so first paint is slow on bigger databases, the font sizes are all slightly too small for older eyes, the GitHub card assumes the user has git projects which most researchers will not. But those are fixable once the structural problems are solved. The structural problems are what needs to be decided first.

## 3. Proposed dashboard redesign

Here is the redesign I recommend. It collapses twelve tabs down to a smaller, more focused set, reorganizes the Control Room around a single principle (what do you want to do right now), and introduces a persistent quick-capture shortcut that removes the need to navigate for the most common action.

> **Superseded by Section 28.** The six-tab proposal below was the starting point for the Plan Mode review. After the tab-by-tab discussion, the final architecture is **eight tabs**: Today · Knowledge · Thinking · Planner · Work · Meetings · Learning · Metis. Planner was split back out from Work as a standalone convergent-mode tab; Learning was promoted to its own tab because courses deserve first-class space. See **Section 28** for the final, locked-in design of every tab including layouts, launcher buttons, cross-tab contracts, and decision rationale. The descriptions in 3.1 below remain as design-history context.

### 3.1 The (initial) six-tab proposal — superseded by Section 28

**Today.** This is the Control Room renamed and radically simplified. It is the home screen, the place every session begins. It has exactly four sections arranged vertically with generous spacing: a greeting strip with her name and today's date; a "What's new overnight" summary (one line per thing — three new papers, one news brief, two overnight WhatsApp ideas, one meeting ready for review); a "What do you want to do right now?" task launcher with six large cards (described in section 4); and a "Today's focus" card showing the one thing the PhD most needs this week. That is everything. No KPI strip. No system snapshot. No GitHub card (moved to Projects). No open tasks table (moved to Projects). No recent files table (moved to Knowledge). Four sections. Breathable layout. Total vertical scroll: under one screen on a 1080p laptop.

**Knowledge.** This is the merged view of the current Library, Research, and Dropzone tabs. The reasoning is that all three are about literature — reading it, tracking it, managing it. Having them split creates a false distinction the researcher does not care about. Knowledge has three sub-views accessed via a segmented control at the top: **All papers** (the current Library view, searchable and filterable), **In progress** (papers she is actively working with, linked to articles or projects), and **Drop new**, a drag-and-drop area that replaces the Dropzone tab entirely. A "Sources" sub-view lists RSS feeds, journal sources, and repositories. Everything literature-related lives here.

**Thinking.** This is the merged view of Ideas, Notes, and the Journal. All three are places where the researcher writes down what is in her head, and splitting them has been a source of friction. Thinking has a single capture box at the top ("What's on your mind?") that auto-tags the entry based on its content: "idea" if it's a new thought worth developing, "note" if it's a quick observation, "journal" if it's a daily reflection. The researcher does not have to choose; she just writes, and Metis routes. Below the capture box is a timeline of her thinking, filterable by type, with cross-pollination connections attached to each entry. This is where the second-brain feeling of Metis becomes visceral: she writes something, and within seconds Metis shows her "this relates to the paper you read last Tuesday and the meeting with your supervisor three weeks ago."

**Work.** This is the merged view of Projects and Planner. A researcher's work is organized around projects — an article she's writing, a dashboard she's building, a course she's developing — and each project has a plan and tasks. Splitting Projects from Planner asks her to track the same work in two places, which she will stop doing within a week. Work presents each project as a card with its health, its current focus, its open tasks, and a launcher button for its external IDE (VS Code, RStudio, Word). Clicking into a project reveals the full plan, the PLANNING.md contents, recent activity, and a "Continue in Claude" button that uses the task router described in section 4.

**Meetings.** Kept as its own tab because meetings are big, structured, time-bounded, and benefit from a dedicated interface. The current Meetings tab stays mostly as-is, with three capture modes (quick, auto, live) and a list of past meetings with their transcripts, action items, and cross-links. One addition: a "Prep for upcoming meeting" view that pulls from the calendar (when we add calendar integration) and assembles a briefing for the next supervision, seminar, or collaboration call.

**Metis.** This is the settings and self-management tab, replacing System, Learning, and the News feed configuration. It has four sub-views: **My profile** (thinking profile, research domain, active projects, the values driving routing decisions); **Agents** (the team roster, each agent's recent runs, any pending skill-improvement proposals, and the ability to pause or retire an agent); **Memory** (every Claude session that touched Metis, searchable, with a resume button per session); and **Settings** (API keys, automated task schedule, data protection preferences, model assignments, RSS feeds, news topics). This is also where the self-improvement queue lives, where the researcher reviews and approves changes her agents want to make to themselves.

### 3.2 The persistent quick-capture shortcut

Above the tabs in the nav bar (eight tabs as finalized in Section 28), I want to add a single persistent button that reads "+ Capture" with a keyboard shortcut `Ctrl+K` (or `Cmd+K` on Mac, but we are Windows-first). Clicking it or pressing the shortcut from anywhere in the dashboard opens a modal with a text field and a single "Save" button. Whatever she types is saved as a thinking entry, auto-classified, and cross-pollinated. She never has to navigate to a tab to capture a thought. This one-key-away capture is the single highest-value piece of UI in a personal knowledge system, because ideas that take more than five seconds to record are ideas that get lost. Obsidian has this. Notion has this. Roam has this. Metis should have this.

### 3.3 Visual and density fixes

Beyond the structural changes, here are the visual adjustments that will make each page feel professional rather than crowded. Use more whitespace between cards — a minimum of 24 pixels, not 16. Use larger font sizes for body text (1rem, not 0.9375rem). Give each page a clear single-column layout by default with optional two-column only when two cards are logically paired. Never put more than four primary cards above the fold. Use muted backgrounds for secondary content and reserve full color for primary actions. Add a subtle animated transition when tabs change so the interface feels alive. Add skeleton loaders instead of blank states during data fetch. Write proper empty states with friendly language and a clear next action (e.g., "No ideas yet. Press Ctrl+K to capture your first one."). Add a dark mode toggle in Metis → Settings.

## 4. The task launcher on the Today tab

This is the single most important UI component in the redesign because it is where the researcher's intention meets the Claude clients. Building on the reflection we did in the Windows distribution strategy, here are the six launcher cards that belong on the Today tab and exactly what each one does.

**Capture an idea.** Stays in the dashboard. Opens the quick-capture modal pre-filled with the "idea" category. This is included on the launcher even though the Ctrl+K shortcut exists, because a visible button teaches the shortcut's existence to new users.

**Brainstorm something out loud.** Opens Claude Desktop chat with the Metis MCP server attached and a brainstorm prompt pre-copied to the clipboard. Subtitle: "Chat is for thinking with Metis — free-flowing conversation, exploring an idea, asking questions." This is where the researcher goes when she needs a thought partner, not a tool.

**Work on a document.** Opens Cowork in the Metis folder (or a specific project folder if launched from within a project). Subtitle: "Cowork is for writing — drafting articles, editing papers, building slide decks, reviewing Word documents. You can see the file as Metis edits it." This is where she goes when she has a document in hand that needs attention.

**Review code or build a tool.** Opens Claude Code in a terminal already cded into the relevant project folder. Subtitle: "Claude Code is for the technical side — editing R scripts, debugging, refactoring, building a new dashboard." This is where power users go, and where the researcher goes when she wants to extend Metis itself.

**Prep for a meeting.** Stays in the dashboard. Opens the Meetings tab's Prep view with the next scheduled meeting pre-loaded (or a manual "who are you meeting with?" prompt if calendar integration is not set up). Pulls relevant context, assembles a briefing, and offers to open Claude Chat with the briefing as the starter prompt.

**Process the inbox.** Stays in the dashboard. Runs the Librarian agent over any PDFs in `00_inbox/`, shows progress, and presents the results. No Claude client needed because this is a background agent run.

Each card has: a title, a one-line subtitle that says what the target client is best for, an icon representing the target client (Chat, Cowork, Claude Code, or the dashboard), and a secondary hover state with more detail. The grid is three across on desktop, one per row on narrow screens. The visual weight is equal across all cards so the researcher does not feel pushed toward one option — the subtitles teach her which is best for each situation.

## 5. The master /metis interaction pipeline

This is the heart of the "AI gateway" positioning, and it is the piece that currently does not exist as a unified pipeline even though most of its components are implemented in pieces. I want to describe what needs to happen every single time any Claude client invokes `/metis` or calls any Metis MCP tool, in order, so that the data protection, the cybersecurity, the session memory, the token efficiency, and the self-improvement all happen automatically without the researcher having to configure anything.

The pipeline has eleven stages and runs on every single call, whether it is a dashboard click, a Chat conversation, a Cowork session, or a Claude Code command. I will walk through each stage because each one corresponds to a promise we are making to the researcher.

**Stage 1: Session bootstrap.** When Metis is invoked, it first checks whether there is an active session for the current researcher. A session is identified by a combination of the researcher's local user ID (not a cloud account, just the Windows user) and a conversation context. If an active session exists, its accumulated memory is loaded — the recent turns, the active focus, the tools already used, the context already assembled. If no session exists, a new one is created with a unique ID and linked to whichever Claude client is calling. This is where the promise of memory across sessions begins: the moment the researcher calls `/metis`, she is resumed, not started.

**Stage 2: Request classification.** Metis looks at the incoming request and classifies it along three axes. First, what is the content class — public (sharing is fine), internal (process locally but API is okay), confidential (warn and confirm before any external call), or sensitive (block any external processing completely). Second, what is the task type — simple lookup, brainstorm, file edit, code change, data analysis, routing decision. Third, what is the estimated cognitive load — quick, standard, deep, or chain (matching the existing complexity tiers). This classification happens in microseconds using pattern matching and determines the entire downstream pipeline.

**Stage 3: Data guardian intercept.** The Data Guardian agent runs before anything else leaves the local machine. It scans the content of the request for any patient identifiers (IDs, names, dates-of-birth combined with locations), any GPS coordinates that look like individual cases, any rows from sensitive databases, any unpublished research drafts, any personal information about contacts. If it finds anything SENSITIVE, it blocks the call completely — no override, no "are you sure," just a clear message to the researcher saying what was blocked and why. If it finds anything CONFIDENTIAL, it pauses and asks the researcher whether she wants to proceed, showing exactly what will be sent. If it finds only INTERNAL or PUBLIC content, it proceeds silently. This guardian is the floor of data protection — everything else builds on top of it.

**Stage 4: Cybersecurity intercept.** The Cybersecurity agent runs in parallel with the Data Guardian. It scans the request for any URLs that will be fetched, any domains on the blocklist, any patterns that look like prompt injection attempts (embedded system prompts, attempts to redefine agent roles, emergency or urgency language that might be manipulating the agent), any attempts to modify the red lines or the system files. If it finds anything suspicious, it pauses and surfaces the specific threat to the researcher in plain language: "The document you're asking me to read contains hidden text that looks like it's trying to give me new instructions. Do you still want me to read it?" This is the cybersecurity floor.

**Stage 5: Intent parsing.** Now that the request is classified and cleared, Metis parses the actual intent. What does the researcher want? Is this a request to find information, to edit something, to brainstorm, to analyze data, to make a decision, to build something? Intent parsing uses a small Sonnet call with a cached system prompt (the routing contract) and returns a structured decision: which agent(s) should handle this, in what order, with what context, and at what complexity level. This decision is logged before any agent runs, so that we have a record of Metis's reasoning even if the downstream call fails.

**Stage 6: Token budget allocation.** Metis checks the token budget for the current session and selects a model for each chosen agent based on the token guardrails policy. A "find me this paper" request routes to Librarian at Haiku; a "critique my methodology" request routes to Epidemiologist at Opus; a "summarize this meeting" request routes to Meeting Memory at Haiku. The researcher never chooses a model. Metis chooses for her, transparently, and logs the choice so the dashboard can show her how her tokens were spent.

**Stage 7: Surgical context assembly.** Metis assembles the minimum context the chosen agent needs. It does not dump the full library, it does not load the entire thesis, it does not attach every recent meeting. It uses the MCP tools (`search_notes`, `search_literature`, `get_research_context`) to retrieve only the relevant slices. This is where the 5 Agent Commandments from the token guardrails become enforceable policy rather than best-effort guidance — context is assembled by the pipeline, not by the agent's free will. An agent that loads 50 files is a bug, and the pipeline prevents it.

**Stage 8: Execution with incremental save.** The agent executes its task. Every tool call, every file write, every partial output is saved to a `session_events` table in SQLite as it happens. This is the critical auto-save guarantee: if the Claude client crashes mid-conversation, if the researcher's battery dies, if the token budget is exhausted halfway through, the session is recoverable. The researcher can open a new Claude client, invoke `/metis_handoff`, and pick up exactly where she left off, with every decision, every tool result, and every partial output available. This is what "memory over every session, no matter the account used" means mechanically.

**Stage 9: Output through red lines.** Before the agent's output is returned to the Claude client, it runs through the red lines post-check. Did the output accidentally include any sensitive content? Does it try to trigger any destructive action without confirmation? Does it propose any network call that was not authorized? If any red line is touched, the output is modified or blocked and the researcher is informed. This closes the loop — protection happens at the input (Stage 3/4) and at the output (Stage 9).

**Stage 10: Logging and metrics.** The full run is logged to the `agent_runs` table with timestamp, agent slug, task summary, input path, output path, token counts, model used, session ID, and classification. This is not optional — Red Line 3 requires it. The dashboard reads this log to show the researcher what agents have been doing on her behalf, what they cost in tokens, and what outputs they produced.

**Stage 11: Self-improvement capture.** After the run, the agent writes a brief self-critique to the `reflexion_log` table. The self-critique is a small entry: what went well, what could be better, what context was missing, what tool was awkward to use, what the agent wishes it had. These critiques accumulate over time. On a weekly schedule, a meta-agent reviews them and proposes skill improvements to the agents that have recurring complaints, and the proposals appear in the Metis tab for the researcher to approve. This is how every agent self-improves, not just the main Metis agent.

The entire pipeline runs in hundreds of milliseconds for simple calls and a few seconds for deep ones. Most of it is invisible to the researcher — she calls `/metis`, something useful happens, the result appears. But every single call is protected, logged, memorized, and improved upon. The researcher does not have to trust the system on faith; she can open the Metis tab and see exactly what happened, what was blocked, what was spent, and what was learned.

## 6. Session memory architecture

The user asked for something specific and important: memory that persists across every session, across every Claude client, across every Claude account, incremental, auto-saved, and resumable. I want to spell out the concrete architecture for this because it is technically interesting and because it is the thing that makes Metis feel like a second brain rather than a stateless tool.

The memory lives in the local SQLite database in three related tables. The `sessions` table records every distinct conversation that has touched Metis, with a session ID, the Claude client that started it (Chat, Cowork, Code, dashboard), the time it started, the time it last received activity, and a free-text summary that is updated after every few turns. The `session_events` table records every atomic event within a session: each turn the researcher sent, each tool call Metis made, each tool result, each file write, each red-line check, each classification decision. The `session_context` table records the persistent focus of a session: which project, which article, which idea, which meeting is currently being worked on — the "active context" that gets carried across client switches.

The critical property of this architecture is that it is write-through, not write-behind. Every single event is persisted to SQLite before Metis returns control to the Claude client. There is no "save" step because there is no transient in-memory state to lose. If the client crashes, if the network drops, if the battery dies, the session is whole up to the last completed event. The researcher can open a new Claude client the next morning, say "continue the thing I was working on yesterday," and Metis loads the last session, inspects its active context, and presents a resume card: "Yesterday at 4 PM you were drafting the methodology section of Article 1 with Writing Partner. You stopped after 12 turns. Here's a summary of what was decided. Do you want to pick up where you left off?" That continuity is the product.

The cross-account property is worth calling out specifically. When the researcher moves from her personal Claude account to her university Claude account — perhaps because she is at the office using the institutional license — Metis does not care. The session memory is tied to the Windows user, not to the Claude account, because it lives in the local database. A new Claude Desktop conversation under a different account still connects to the same local MCP server, which still has the same session memory. The researcher can finish a thought she started three days ago at home from her office chair without any transfer, any export, any handoff. This is a superpower for researchers who work across multiple devices or multiple accounts.

The handoff mechanic is for the case when the researcher wants to continue in a different Claude client explicitly — for example, switching from a Chat conversation to a Cowork session because she now needs to edit a document. She invokes `/metis_handoff`, Metis compresses the current session into a portable briefing (the active context, the key decisions, the next intended step), and writes it to a handoff slot. When she opens the new client and says "continue," Metis reads the handoff slot and bootstraps the new session from it. The researcher experiences this as "I clicked a button and my work moved with me," but mechanically it is a deliberate summarization step that keeps the new session's context window small.

There is one subtle issue that needs handling: token-limit resume. When a long session approaches the conversation's token ceiling, Metis needs to compress without losing work. The solution is a tiered compression: every ten turns, Metis writes a mini-summary of the last ten turns to the session_events table. When the token ceiling is approaching, Metis loads only the summaries of old turns plus the full text of the recent turns. The researcher does not notice anything except that long conversations somehow keep working. If the compression causes any loss of precision (e.g., a specific decision that was made 30 turns ago is no longer in context), Metis can refetch the full text from session_events on demand via a "remember when I said X" query.

## 7. Data protection redesigned for researchers

The existing red-lines.md is good, and it is the foundation. What needs to change is not the red lines themselves but how they are exposed to the researcher — how they become a visible trust signal rather than a policy document that nobody reads. Here are the concrete changes I recommend.

**The trust badge.** In the top-right corner of the dashboard, always visible, there is a small green shield icon that says "Local-first". Hovering over it reveals a summary: "Everything in Metis lives on your computer. No data has been sent to any AI service in this session" (or "2 calls have been sent to Claude — review what was shared"). Clicking it opens a drawer showing every external call in the current session, what was sent, and what was classified. This is the single most important UI element for trust: the researcher can see, at any moment, whether her data has left the machine. That visibility is what lets her stop worrying.

**The anonymization function.** This is a new feature that the current Metis does not have. Before any CONFIDENTIAL content is sent externally, the pipeline offers to anonymize it. The anonymization function runs a small Python script that: replaces any names it finds (using NER) with placeholders like "Collaborator A", "Patient X"; replaces any dates with coarser intervals ("January 2025" instead of "15 January 2025"); replaces any GPS coordinates with health zone names; removes any identifiers that match a configured pattern list (patient IDs, case numbers, accession numbers). The researcher sees a diff of the anonymized content before it is sent, with the original on the left and the anonymized version on the right, and clicks "Send anonymized" or "Cancel". This one feature is worth its weight in gold for researchers working with human subjects data, because it lets them ask Metis about their work without ever exposing their subjects.

**The consent ledger.** Every time the researcher approves an external call, the approval is logged to a `consent_ledger` table with timestamp, what was sent, what classification, and how long the approval lasts (single use, session, indefinite). She can review and revoke approvals at any time from Metis → Settings → Data Protection. This is not just compliance theatre — it is the thing that builds trust over time, because she can literally see that nothing has happened without her explicit approval.

**The network gate.** Metis has a configurable network policy that starts in "strict mode" by default for a new install. In strict mode, no external call happens without explicit consent per call. After the researcher uses Metis for a week and approves repeatedly, the dashboard offers to relax to "normal mode", in which routine agent calls happen without per-call confirmation but the consent ledger still records them. A "airplane mode" setting takes Metis fully offline — all agents still work locally, external searches return "offline" gracefully, and nothing leaves the machine. This progression from strict to normal to airplane gives the researcher complete agency over how she wants Metis to behave.

**Proactive prompt injection defense.** The Cybersecurity agent already exists and runs as part of the pipeline (stage 4), but it needs a visible surface. When it catches a prompt injection attempt — hidden text in a PDF, suspicious content in an email attachment, an HTML page with hidden instructions — the researcher should see a clear, plain-language notification: "I noticed this PDF has hidden text that might be trying to trick me. I'm ignoring it. Here's what it said so you know." This is a surprisingly powerful trust signal because it turns a scary topic (prompt injection) into a concrete, visible thing Metis is protecting her from.

## 8. Self-improvement for Metis and every agent

The current self-improvement mechanism is good in concept but only applies to individual skill files via the `propose_skill_improvement` MCP tool. What is missing is a systematic loop that runs for every agent, captures what they struggled with, and surfaces improvements for human approval on a regular rhythm. Here is the redesign.

Every agent run produces, at minimum, two outputs. The first is the primary task output (the paper summary, the code review, the meeting analysis). The second is a small reflexion entry — typically one to three sentences — that the agent writes about its own experience. "This task was harder than it should have been because I did not have access to the most recent meeting notes." "I am repeatedly asked to do cite-checking and do not have a tool for it." "The researcher seemed dissatisfied with my last response — I should ask a clarifying question next time." These reflexion entries are stored in a `reflexion_log` table alongside the agent_runs entries.

On a weekly schedule (every Sunday evening at 22:00), a meta-agent called the Coach runs through the reflexion log for the past week. The Coach is a single Sonnet call with a cached prompt that says: "Here is the reflexion log for every agent this week. For each agent with more than three related complaints, propose a specific, small, scoped change to their skill file that would address the pattern. Do not propose broad rewrites. Propose one change per pattern." The Coach writes proposals to the `skill_proposals` table. The researcher opens the Metis tab on Monday morning and sees a short list of proposals with "Approve" / "Reject" / "Modify" buttons. Approving a proposal applies the edit to the agent's skill file and reloads the agent. The researcher never writes a prompt by hand.

There is a second, more ambitious loop for Metis itself — the routing agent. Metis's job is to decide which agent to use for each request, and those decisions are logged. The Coach also reviews the routing decisions: was the right agent picked? Was the complexity level right? Was the token budget appropriate? When the Coach sees a pattern — "Metis consistently over-estimates the complexity of literature search queries" — it proposes a change to Metis's own routing contract. This is the self-improvement applied to the router, not just the workers, and it is how Metis becomes more efficient over time without the researcher tuning anything.

Crucially, the self-improvement loop is bounded. No proposal is ever applied without human approval. No agent can rewrite itself without going through the queue. No routing rule can change without the researcher clicking Approve. This is the "bounded Reflexion" pattern from the research literature, and it is the right balance between adaptivity and safety.

## 9. Automated daily tasks and scheduling

The current Metis has a `/schedule` skill that sets up scheduled tasks via Windows Task Scheduler, which is the right mechanism but too manual. Here is the automated default schedule I recommend, which should be installed and enabled automatically by the first-run wizard so the researcher does not have to configure anything to get the daily rhythm working.

Every morning at 07:00 (researcher's local time, detected from the system), News Radar runs. It fetches the configured RSS feeds, summarizes the high-signal items, and writes a news brief to the database. Cost: a few cents per day at Haiku pricing.

At 07:15, the Librarian runs the inbox scan. Any PDFs that appeared in `00_inbox/` overnight are processed: metadata extracted, tags assigned, cross-links created, and moved to `05_sources/literature/`. Cost: a few cents per paper, nothing if the inbox is empty.

At 07:30, the Morning Brief assembler runs. It composes a brief for the Today tab combining: news items from News Radar, new papers from the Librarian, overnight ideas from WhatsApp, any meeting transcripts ready for review, overdue tasks, and today's PhD focus. The brief is written to a `morning_briefs` table and surfaced when the researcher opens the dashboard. Cost: one Sonnet call, a few cents.

Every evening at 19:00, an optional "Journal nudge" notification appears on the dashboard if the researcher has not yet written a journal entry that day. The nudge is subtle — a small card saying "Write a short reflection?" — and dismissable. No Claude calls are made for the nudge itself.

Every night at 23:00, the Cross-Pollinator runs a pass over the day's new content. It takes every new idea, note, paper, and meeting from the last 24 hours and runs cross-pollination against the full knowledge base. New connections are added to the database and surfaced on the next morning's Today tab as "Yesterday's thinking connected to...". Cost: one Sonnet call for the batch.

Every Sunday at 22:00, the Coach runs the self-improvement review as described in section 8. It reads the week's reflexion log, proposes skill improvements, and writes them to the queue. Cost: one Sonnet call with a large cached system prompt.

Every Monday at 07:30, the Weekly Summary assembler runs. It produces a short summary of the previous week: ideas captured, papers read, meetings held, articles worked on, progress against PhD milestones. This becomes the content of the `/metis_weekly` skill and appears on the dashboard as a card. Cost: one Sonnet call.

The researcher sees a single "Automated tasks" section on the Metis → Settings page where she can enable, disable, or reschedule any of these. The defaults are chosen so that Metis feels alive even if she never touches the settings. The total cost of the automated schedule at current Anthropic pricing is roughly a few euros per month per researcher — well below any meaningful threshold.

## 10. Token efficiency made visible

The token-guardrails.md document is excellent and should not change. What should change is the visibility of token spending and savings in the dashboard, so that the researcher sees the efficiency discipline paying off and feels good about it.

On the Metis tab, the researcher sees a "This month" widget showing: total input tokens, total output tokens, total cost, breakdown by agent, breakdown by model. She sees how much was saved by prompt caching (the Coach writes the delta to a metric each run). She sees which agent is the most expensive and what it is being used for. If she is on a paid API plan, she sees her projected monthly cost and can set an alert.

More importantly, she sees the efficiency stats without having to ask for them. On the Today tab, a small footer line reads: "Metis spent 12,400 tokens yesterday (€0.06) across 8 agent runs. Cache hits: 78%." That one-line summary is enough to build confidence that Metis is not wasting her money, and it makes the token discipline visible without being nagging.

The token budget can be configured in Metis → Settings → Budget with a simple slider: "How much do you want to spend on Metis per month? €0–€50". The default is €10, which is comfortable for most researchers. If the current pace is going to exceed the budget, the dashboard warns her five days before the overage and offers to either increase the budget or throttle non-essential automated tasks.

## 11. The complete workflow catalog

The existing workflows.md documents eleven workflows. The researcher will actually have dozens of ways she uses Metis, and each one should be a first-class citizen of the design. Here is a more complete catalog — I count thirty distinct workflows — written as a reference so we can verify that every tab and every launcher button serves at least one workflow and that every important workflow is served by something.

**Morning routine (1–3).** One: open the dashboard and read the Today tab brief. Two: process any overnight WhatsApp ideas via the Thinking tab. Three: glance at the trust badge to confirm nothing unexpected happened overnight.

**Idea capture (4–7).** Four: desktop quick capture via Ctrl+K. Five: mobile capture via WhatsApp. Six: voice memo capture via a mobile recording that is dropped into the inbox and transcribed by Meeting Memory, then routed to Thinking. Seven: capture a thought while reading a paper by clicking the "this gives me an idea" button on the paper's card.

**Thinking and reflection (8–11).** Eight: write a journal entry at end of day via Thinking → Journal. Nine: revisit an old idea by searching Thinking for keywords. Ten: brainstorm an idea with full cross-pollination context by clicking "Brainstorm this" on an idea card (opens Chat). Eleven: convert an idea into a project by clicking "Promote to project" (creates a card in Work).

**Literature work (12–15).** Twelve: drop a PDF into `00_inbox/` and let the Librarian process it automatically. Thirteen: search the library for papers on a topic via Knowledge tab search. Fourteen: read a paper in the Knowledge tab with a side panel showing related ideas and meetings. Fifteen: ask a question about a paper by clicking "Ask Metis about this" (opens Chat with the paper's summary as context).

**Meeting work (16–19).** Sixteen: record a meeting via the Meetings tab. Seventeen: import a transcript from a third-party tool (Otter, Fireflies) via the Meetings tab. Eighteen: prepare for an upcoming meeting via Meetings → Prep. Nineteen: convert meeting action items into tasks on the Work tab with one click.

**Article and writing work (20–24).** Twenty: open an article draft in Cowork from the Work tab. Twenty-one: ask Writing Partner to review a draft for prose quality. Twenty-two: ask Epidemiologist to critique the methodology. Twenty-three: run a cite-check across every reference in a manuscript (new workflow worth adding). Twenty-four: update the PLANNING.md for an article from within Cowork with a single prompt.

**Analysis and code work (25–28).** Twenty-five: review an R script in Claude Code. Twenty-six: debug an error from an R session by pasting the error and getting a diagnosis. Twenty-seven: scaffold a new Shiny dashboard from tabular data via the Builder agent. Twenty-eight: run a statistical analysis on a dataset via Methods Coach.

**Meta and self-improvement (29–30).** Twenty-nine: review pending skill proposals in Metis → Agents on Monday morning. Thirty: resume a session from a different Claude client via `/metis_handoff`.

This catalog is not exhaustive — I can think of more (preparing a conference poster, reviewing a submitted peer review, tracking a grant deadline, learning a new statistical method) — but it is complete enough that every workflow maps to at least one of the eight tabs (see Section 28 for the final tab list) and one of the launcher buttons. When we implement each tab, we should explicitly check: which of these thirty workflows does this tab serve, and how does it serve them?

## 12. Tab interconnections

A common failing of tabbed interfaces is that the tabs feel like silos — each tab has its own data, its own view, and there is no way to move between them except by clicking the nav bar. Metis needs to feel like a connected web, not a file cabinet. Here are the specific interconnections that need to exist between the six redesigned tabs.

From **Today**, the task launcher cards link to Thinking (capture), Chat (brainstorm), Cowork (write), Claude Code (review), Meetings (prep), and Knowledge (process inbox). The "What's new overnight" summary has deep links to the specific new items in Knowledge, Meetings, and Thinking. The "Today's focus" card has a deep link into the specific project in Work.

From **Knowledge**, every paper card links to: the Thinking entries that reference it, the Meetings that mentioned it, the Projects that cite it, and a "Brainstorm about this paper" button that opens Chat. Every paper can be pinned to a project in Work, and every paper can become the seed of a new Thinking entry via "This gave me an idea".

From **Thinking**, every entry links to: the papers in Knowledge that cross-pollinated with it, the meetings it connects to, the projects it might belong to, and a "Develop this idea" button that opens Chat or Cowork depending on whether the entry is pre-draft or post-draft. Journal entries can reference contacts (linking to the contacts table) and glossary terms (linking to the glossary).

From **Work**, every project card links to: the papers in Knowledge that support it, the meetings that are relevant to it, the ideas in Thinking that are related, and launcher buttons for Chat (discuss), Cowork (edit docs), and Claude Code (edit code). Tasks within a project link to the meeting they were generated from, if any.

From **Meetings**, every meeting links to: the projects it was about, the papers mentioned during it, the ideas it generated, the contacts who attended, and a "Convert to tasks" button that creates task entries in the relevant project. Action items are first-class citizens that live in the meeting and in the project simultaneously.

From **Metis**, the agents and sessions are linked to every other tab by logs — clicking on any agent run in the log takes the researcher to the output that run produced (a paper summary in Knowledge, a meeting analysis in Meetings, a draft in Work). The memory view lets her replay any past session from any other tab.

The principle is that nothing is an island. Every piece of content should be reachable from every other piece of content that is semantically related to it, with a single click. Cross-pollination is not just a feature of the Thinking tab — it is the connective tissue that runs through the whole interface.

## 13. What about researchers who do not want to read all this

Everything in this document is for the person designing Metis. None of it is for the researcher installing it. The researcher needs to feel that Metis is three things: safe, useful, and not complicated. Every design decision should be testable against those three words. Is this safe? Yes — the red lines and the anonymization and the trust badge say so. Is this useful? Yes — the capture, the cross-pollination, the automated brief give her things she could not do alone. Is this not complicated? Yes — the eight tabs (finalized in Section 28), the task launcher, and the first-run wizard remove all the choices she does not want to make.

The test I would apply to every new feature is the mother-in-law test: could I explain this feature to a researcher who has never used an AI tool, in one sentence, without using any jargon, and have her say "oh, I would use that"? If the answer is no, the feature is either not necessary or not yet well enough designed. The current Metis would fail this test on most of its tabs. The redesigned Metis should pass on all of them.

## 14. What needs to change first

Because this document describes a lot of changes, the sequencing matters. Here is the order I recommend for the next 6–8 weeks of work, prioritized by impact on the researcher's first-install experience.

First, the dashboard consolidation. Collapse twelve tabs into the final eight (see Section 28 for the locked list). This is mostly deletion and merging, not new code. It can be done in one to two weeks and it alone will improve the feel of Metis dramatically. Second, the Today tab redesign with the task launcher. Strip the Control Room down to its locked layout (greeting strip, Morning Brief hero, launcher row, conditional focus row, sticky capture footer), build the four launcher buttons, wire them up to copy prompts to clipboard for Chat and Cowork (deep links come later). This is two weeks. Third, the quick-capture Ctrl+K shortcut, global across all eight tabs. This is three days of work and it changes how the researcher uses Metis forever.

Fourth, the master /metis pipeline. This is the biggest piece because it touches the MCP server, the database schema, and every agent. But it is the piece that makes the rest work, so it should be prioritized over further UI polish. Budget three to four weeks. Fifth, the session memory tables and the cross-client resume mechanic. This is two weeks once the pipeline is in place. Sixth, the anonymization function and the trust badge. This is two weeks and gives Metis its marketing story.

After those, the rest can come in any order: the self-improvement loop, the automated daily tasks, the token visibility, the sample data for empty states, the dark mode, the first-run wizard. Each of those is a nice-to-have that improves Metis but does not fundamentally change what it is. The first six items above are what turn Metis from "a personal productivity system" into "an AI gateway for researchers".

## 15. Closing thoughts

I want to close with one observation about what makes this project different from other open-source second brains. There are already many second-brain tools — Obsidian, Logseq, Roam, Notion. They all do a reasonable job of capture, linking, and search. None of them position themselves as an AI gateway, and none of them bake AI safety, agent coordination, and cross-session memory into the fabric of the product. That gap is where Metis can win. It is not enough to be another note-taking app with a sprinkle of AI. The promise has to be bigger: "I will protect your research, remember everything, and make AI actually useful for the work you already do — and I will do it without asking you to learn anything new."

Every change in this document exists to deliver on that promise. The tab consolidation (finalized at eight tabs in Section 28) makes it not-complicated. The task launcher makes it useful. The master pipeline, the session memory, and the trust badge make it safe. The self-improvement loop and the automated daily tasks make it alive. The first-run wizard and the zero-install distribution make it accessible to the researcher who has never touched a terminal.

If we get all of that right, Metis becomes the default way researchers use AI. Not because it is the most powerful tool (Claude itself is the most powerful tool), but because it is the most trusted one — the one a researcher will actually open in the morning, the one she will actually type her ideas into, the one she will actually let see her data. And that trust is what multiplies everything else.

---

## 16. Port management and failsafes for localhost conflicts

You raised a concrete concern that is easy to overlook until it bites you: port 3838 is already used by another Shiny dashboard on your machine, and a naive Metis install would simply fail to start or, worse, collide silently with the other app and leave you debugging why neither dashboard works. This is the kind of papercut that turns a researcher away from the product in the first five minutes, so the port strategy needs to be engineered, not assumed.

Here is the failsafe I recommend. On first launch, the Metis tray launcher runs a port-selection routine before binding to anything. It tries a ranked list of candidate ports starting with a "preferred" value (3838 for familiarity with the R Shiny convention, then 3839, 3840, and so on up to 3860). For each candidate, it attempts a `bind()` on `127.0.0.1:<port>` with `SO_REUSEADDR` disabled, immediately releases the socket if the bind succeeds, and records that port as "available." If every port in the range is taken, it falls back to requesting a random high port from the operating system (any unused port above 49152). The first available port is chosen.

Once a port is chosen, it is written to a small file at `<Metis>/data/runtime-port.json` along with the process ID of the backend and a timestamp. Every piece of Metis that needs to reach the dashboard reads this file: the tray launcher's "Open Dashboard" action, the Start Menu shortcut (which points to a tiny launcher script that reads the port and opens the browser), the launch buttons in the Control Room (which build their URLs dynamically), and the MCP server's self-introspection endpoint. Nothing in Metis hardcodes `localhost:3838`. Every URL is computed at runtime from the chosen port.

There is also a manual override. In Metis → Settings → Advanced, there is a field labeled "Dashboard port" with the current value shown and a small helper text: "Metis will try to use this port on next start. If it is busy, Metis will pick the next free one automatically." The researcher who knows what she is doing (you, in this case) can pin Metis to a specific port; the researcher who does not care can leave it on auto and Metis will quietly do the right thing. In both cases the dashboard will never fail to start because of a port collision.

The same logic applies to any secondary ports the backend might expose. If we later add a WhatsApp webhook endpoint on FastAPI, or an MCP HTTP bridge, or a live-update websocket, each one goes through the same port-selection routine with its own preferred range, and each one writes its chosen value to the `runtime-port.json` file. The file becomes the single source of truth for "what is running where" on this machine, and the dashboard's System tab shows the current bindings in plain text so debugging a collision takes ten seconds instead of an afternoon.

One more failsafe: when Metis starts, if it detects that the `runtime-port.json` file exists from a previous run but the process ID listed in it is still alive and responding, Metis assumes an existing Metis is already running and refuses to start a second instance. It opens the existing dashboard in the browser instead. This prevents the common beginner error of double-clicking the tray launcher three times and ending up with three competing backend processes.

## 17. Inno Setup dependency bundling — what we know and what we test

Your question was a good one: can we be sure Inno Setup will install every dependency the researcher needs? The honest answer is yes, but with a specific approach that sidesteps Inno Setup's weaker points.

Inno Setup itself is a file-copying and registry-writing engine. It does not understand Python, does not run pip, and does not know about Visual C++ redistributables on its own. What it does do extraordinarily well is copy files from a bundled payload to a destination folder, run arbitrary executables during install, edit registry keys, write shortcuts, and produce a proper Add/Remove Programs entry. That is all we need, provided we structure the payload correctly.

The structure I recommend is fully offline, zero-internet-at-install-time. The Metis installer payload contains five things. First, the Python embeddable distribution — a roughly 15 MB ZIP that we extract into `<Metis>/runtime/python/`. This is the official Python.org embeddable build and it works on every 64-bit Windows 10+ machine without any prerequisite runtime. No Visual C++ redistributable. No admin rights. No PATH modification. Second, a `vendor/` folder containing every Python wheel (`.whl` file) that Metis depends on, pre-downloaded for the Python version we bundle and the Windows platform. This includes FastAPI, Uvicorn, the MCP package, pyyaml, requests, sqlite-vec, the sentence-transformers weights, pystray, pillow, pyperclip, and every transitive dependency. Building this vendor folder is a one-time step on the developer's machine via `pip download --platform win_amd64 --only-binary=:all: --python-version 3.12 -r requirements.txt -d vendor/`. Third, the Metis source code itself — the `.py` files for the backend, the MCP server, the agents' skill files, the database schema, and the default configuration. Fourth, the initial SQLite database seeded with the schema but empty of content. Fifth, the small bootstrap scripts that the installer runs during install and that the tray launcher runs at startup.

At install time, Inno Setup does four things in order. It copies the entire payload to the chosen install folder. It runs a PowerShell one-liner that invokes the embedded Python with `python.exe -m pip install --no-index --find-links=vendor/ --target=site-packages/ <list of requirements>`, which installs every dependency from local wheels without touching the internet. It runs the JSON config merger to register Metis in Claude Desktop. It creates the Start Menu shortcuts and the Add/Remove Programs entry. Total install time on a typical machine: under two minutes.

The reason this approach works is that we have traded disk space (the installer is about 40 MB because it ships all the wheels) for install reliability (it cannot fail because of a broken PyPI mirror, a corporate firewall, or a dependency conflict). For researchers on university networks that block outbound pip traffic, this is the difference between "it worked" and "it did not work and I do not know why." The extra 40 MB is a trivial cost.

The things Inno Setup cannot do, and that we therefore do not ask it to do, are: install R (we do not need it because the dashboard moved to Python), install Visual C++ redistributables (we do not need them because the embeddable Python does not link them), install .NET runtime (we do not use it), modify Windows Defender exclusions (we do not need any), or require admin privileges (we deliberately install to `%LOCALAPPDATA%` or `%USERPROFILE%` which a standard user can write to without UAC). The installer runs as the current user, asks for no elevation, and touches nothing outside its own install folder and the researcher's Claude Desktop config file.

One test I would build into the CI pipeline before every release: spin up a clean Windows virtual machine (there are free Microsoft-provided Windows VMs for development testing), copy the new `MetisSetup.exe`, run it in silent mode, then run a smoke test that starts the dashboard, hits the `/api/health` endpoint, calls three MCP tools, and verifies the tray icon appears. If any step fails, the build does not ship. This catches packaging regressions before they reach a researcher.

## 18. Implementation progress tracking — the "resume where we left off" system

You raised a concern that I think is deeply important and rarely handled well: when we start implementing this strategy, the conversation will cross many sessions and many Claude accounts, and tokens will run out mid-task. We need a way to resume exactly where we left off without losing context. This is the same problem Metis solves for the researcher, and we should eat our own dog food — use the Metis session memory architecture to track our own implementation work.

Here is the concrete mechanism. At the root of the Metis folder, we keep a file called `08_system/implementation-progress.json` that is the single source of truth for "how far along are we." It is a structured JSON file with one entry per implementation milestone, each containing: a milestone ID, a human-readable name, a status (`pending`, `in_progress`, `blocked`, `done`), a start timestamp, a completion timestamp, the session ID that last worked on it, a short human-readable notes field, and a list of files that were created or modified during that milestone. Every time Claude (in any surface) touches the Metis codebase, the first thing it does is read this file, and the last thing it does before ending the session is update this file. The PKM Builder agent's system prompt is updated to enforce this: "Before making any changes, read `08_system/implementation-progress.json`. After making any changes, update the matching milestone entry with what was done and what remains."

Alongside the JSON file, we keep a plain-text append-only log at `08_system/implementation-log.md` where each session writes a short entry at the end — two or three sentences saying what was accomplished, any decisions made, and what the next logical step is. This log is intended for human reading; the JSON is intended for machine reading. A new session begins with two reads (JSON for state, log for recent context) and ends with two writes (JSON update, log append). The cost is maybe 200 tokens per session for the read/write overhead, and the benefit is that no work is ever lost to context exhaustion.

The milestone list itself is generated from the phased implementation plan in this document and the Windows distribution strategy. Each phase (dashboard consolidation, Today tab redesign, Ctrl+K shortcut, master pipeline, session memory, anonymization, etc.) gets a set of granular milestones — typically five to fifteen per phase. When tokens run out mid-milestone, the milestone status is `in_progress` and the notes field captures what specifically has been done and what is left. The next session reads the file, sees "milestone 4.2: implementing session_events table writes — schema done, wiring to MCP pipeline remaining", and picks up exactly there.

To make this work in practice, we add one more convention. Every time Claude begins work on a new milestone, it writes the milestone ID to the tray launcher's status file so the researcher can see "Metis is currently working on milestone 4.2" in her tray tooltip. And every git commit (once we put Metis on git) includes the milestone ID in the commit message prefix: `[M4.2] Add session_events schema and write path`. This makes the history browsable by milestone and lets us reconstruct any phase of the build from git log alone.

This progress tracking system should itself be the first thing we build, before any of the other work, because every other piece of work will depend on it being there. It is a one-day task and it pays for itself on day two.

## 19. The "Scan for changes" button and the Dropzone–Document bridge

You identified two connections that need to be wired explicitly, and they are both pieces of the same puzzle: how does Metis know when something on disk has changed, and how does dropping a file connect to editing a document?

**Scan for changes** belongs on the Today tab as a visible button, next to the morning brief. Clicking it runs a scan across three classes of tracked content: git repositories (detect uncommitted changes, unpushed commits, modified files in tracked directories), article and document files (detect `.docx`, `.md`, `.tex` files that have changed since the last scan, using modification time plus a content hash), and PLANNING.md files across all active projects (detect any changes, parse the diff, surface the decisions or new tasks that were added). The scan uses the `tracked_files` table that already exists in the Metis schema — any file with `watch=1` is included. The result is a short "Changes detected" card that appears below the scan button showing what changed, organized by project, with a "Log this in Metis" button that creates a brief note entry linking the change to the relevant project. This closes the loop between work done externally (in Word, RStudio, VS Code) and Metis's knowledge of what is happening.

The scan is fast because it does not compare full file contents — it compares modification times against a stored baseline in SQLite, and only hashes files whose mtime changed. A typical scan across 500 tracked files completes in under a second. The scan is also cheap because it does not call any LLM; it is pure filesystem introspection.

**The Dropzone–Document bridge** is the connection between "I just dropped a file on Metis" and "I want to edit or discuss this file with Metis." The current Dropzone is a standalone tab whose only job is file intake, which creates a dead end — the researcher drops a file and has to navigate elsewhere to do anything with it. In the redesign, Dropzone becomes a section of the Knowledge tab (not its own tab), and every file dropped there gets three immediate buttons: "Process as literature" (runs the Librarian), "Open with Metis in Cowork" (launches Cowork with this file as the focus), and "Ask Metis about this" (opens Chat with the file as context). The file drop becomes a decision point, not a dead end.

The Cowork launch path is worth spelling out because it ties together the launcher infrastructure and the file-handling workflow. When the researcher drops a `.docx` file and clicks "Open with Metis in Cowork", the following happens. Metis copies the file to a working folder inside the Metis structure (preserving the original in Dropzone). Metis writes a small handoff file at `<Metis>/data/cowork-handoff.json` containing the file path and a suggested starter prompt like "I just dropped this document in Metis and want help editing it. Please read it first and then ask me what I want to do with it." The Metis backend launches Cowork with the Metis folder mounted. On first launch, Cowork reads the handoff file, loads the document using the docx skill, and starts the conversation. From the researcher's perspective, she dropped a file and a conversation about that file opened — seamless.

The same pattern works for `.pdf` (uses the pdf skill), `.xlsx` (uses the xlsx skill), and `.pptx` (uses the pptx skill). Each drop becomes a conversation with the right skill pre-loaded. The Dropzone section of the Knowledge tab shows recent drops with their status (processed, in progress, dismissed) so the researcher can resume any drop she did not immediately act on.

## 20. Persistent memory — the state-of-the-art architecture

You asked specifically for "the most recent and best evaluated ways" to create persistent memory for Metis, with structured multi-layered retrieval. This is an area that has moved fast in 2025, and the best answer is a specific architecture drawn from what the memory research and agent memory frameworks have converged on. I will describe it in enough detail that it can be implemented directly.

Metis's memory is organized into five layers, each with a different shape, lifetime, and retrieval pattern. This is the model that cognitive science calls "multi-store memory" and that recent agent frameworks (MemGPT/LettaAI, Mem0, Zep) have translated into software. The layers are **episodic**, **semantic**, **procedural**, **working**, and **reflexive**. Each one has its own table in the Metis SQLite database and its own retrieval entry point.

**Episodic memory** is the record of what happened — every turn of every conversation, every tool call, every file write, every decision. It lives in the `session_events` table with columns for session ID, timestamp, event type (`user_turn`, `assistant_turn`, `tool_call`, `tool_result`, `file_write`, `classification_decision`, `red_line_block`, `self_critique`), content (the actual text or JSON payload), and an embedding vector. The table is indexed with both FTS5 (for keyword search) and sqlite-vec (for semantic search). Episodic memory is the most voluminous and therefore the most heavily summarized over time: events older than one week get compressed into weekly digests, events older than three months get compressed into monthly digests, and raw events beyond six months are archived to the external backup (see next section). This matches the "ephemeral → short-term → long-term" compression cascade that LettaAI introduced and that has become the default pattern.

**Semantic memory** is the structured knowledge Metis has about entities and their relationships — who are the researchers she works with, what papers exist and what they say, what projects are active, what topics matter, what terms mean. It lives in two tables: `entities` (rows for people, papers, projects, topics, glossary terms, organizations) and `edges` (rows representing typed relationships between entities — "paper A cites paper B", "Sara collaborated on project X", "idea Y relates to topic Z"). This is a property graph inside SQLite, which is much simpler than running a separate graph database (Neo4j or similar) and plenty performant for the sizes researchers deal with (tens of thousands of entities, at most). Semantic memory is retrieved by graph traversal: given an entity, find all entities within N hops that match some type and rank by edge weight. It is also retrieved by embedding search on entity descriptions, for "fuzzy" lookups when the researcher does not know the exact name.

**Procedural memory** is how Metis does things — the agent skill files, the routing rules, the scheduled task definitions, the learned preferences for which agent handles which kind of request. It lives mostly as plain files (the markdown skill files in `02_agents/`) supplemented by a `procedural_log` table that records, for each skill, how often it is invoked, how often it succeeds, and what the user's satisfaction signals have been (thumbs up, thumbs down, or implicit signals like "she promoted the output to a task"). Procedural memory is what the self-improvement loop operates on: the Coach agent reads the procedural log weekly and proposes skill updates based on the patterns it sees.

**Working memory** is the small, hot context for whatever the researcher is currently doing. It lives in the `session_context` table with columns for the session ID, the active project, the active article, the active idea, the active meeting, and a JSON blob of recent focus changes. It is the shortest-lived layer (cleared at session end unless explicitly pinned), the smallest (a few kilobytes per session), and the most frequently read (every agent call reads it first). It is the "what am I doing right now" that makes Metis feel present rather than amnesiac.

**Reflexive memory** is what Metis knows about itself and about the researcher. It lives in two files plus one table: `thinking-profile.yaml` (the researcher's patterns — which connections she follows, which ideas she promotes, which agents she uses most), `agent-registry.json` (which agents are active, their model assignments, their skill file versions), and the `reflexion_log` table (self-critiques from every agent run, used by the Coach for improvement proposals). Reflexive memory is read during routing (to personalize decisions) and during self-improvement (to identify what is not working).

The **retrieval pipeline** ties all five layers together. When any agent needs context for a query, the pipeline runs the following steps in order, each returning a ranked list that is merged at the end. Step one: lexical search across `session_events` (FTS5, BM25-style scoring) — fast, precise for exact terms. Step two: vector search across `session_events` embeddings (sqlite-vec, cosine similarity) — captures semantic similarity. Step three: graph traversal on `entities` starting from any entity the query mentions — surfaces structural relationships. Step four: working memory read — returns whatever is currently in focus. Step five: reciprocal rank fusion combines the four result lists into a single ranked list. Step six: a small reranker (BGE-reranker-base, runs locally in about 10ms per candidate) reorders the top 20 candidates for final relevance. Step seven: red-line filter removes any results that contain sensitive content flagged by the Data Guardian. Step eight: return the top 5–10 results with provenance (which layer each came from, so the agent can cite its sources).

This multi-layered retrieval is the current state of the art for local agent memory — it is what Zep, Mem0, and LettaAI all converge on in different forms — and it is implementable entirely within SQLite plus two small extensions (sqlite-vec for vectors, and the sentence-transformers Python package for embedding generation). No separate vector database, no external service, no API key. The embedding model (BGE-M3 or all-MiniLM-L6-v2) runs locally on CPU in a few tens of milliseconds per query. Total memory footprint of the memory layer: under 200 MB of disk for a researcher with two years of activity, and well under 1 GB of RAM when running.

Two important properties of this architecture deserve emphasis. The **provenance** property means every piece of retrieved context knows where it came from — which session, which event, which entity. When an agent uses it in a response, the response can cite "according to your journal entry from 12 February 2026" rather than making a confident claim from nowhere. This is the single biggest trust signal for a researcher, because it lets her verify Metis's claims against her own records. The **forgetting** property means memory is not a bucket that fills up forever. The compression cascade (daily → weekly → monthly → archive) keeps the hot layers small and performant, while the old memories stay accessible via the external backup. Metis does not become slower the longer you use it, and it does not start hallucinating about its own past because the context window filled up.

## 21. External backup and portability — the "safe space outside Metis"

You asked for something specific and important: everything Metis records should also be stored outside Metis in a safe place, updated daily, so that if the computer breaks or the researcher switches machines or uninstalls and reinstalls Metis, everything can be restored. This is a real requirement and the design is straightforward once we commit to it.

Every night at 23:30, a backup job runs inside the Metis backend. It does the following. First, it runs `VACUUM INTO` on the SQLite database to produce a compacted copy at `<Metis>/data/backup/metis-YYYY-MM-DD.sqlite`. Second, it bundles this copy together with the user configuration files (`08_system/user-config.yaml`, `08_system/thinking-profile.yaml`, `08_system/agent-registry.json`), the skill files (the entire `02_agents/` folder), the implementation progress tracker (`08_system/implementation-progress.json`), and the last seven days of session logs (`session_log.md` and the reflexion logs). Third, it compresses the bundle to a single ZIP file. Fourth, it encrypts the ZIP with AES-256 using a key derived from a passphrase the researcher set during first-run (with a sensible default derived from her machine ID if she skipped the passphrase step). Fifth, it writes the encrypted archive to every configured backup destination.

The destinations are configured in Metis → Settings → Backup and the researcher can enable zero, one, or several of them. The default destinations offered on first-run are: **OneDrive** (if detected on the machine, writing to `<OneDrive>/Metis/Backups/`), **a local folder on an external drive** (useful for researchers with a fixed USB stick), **a Git repository** (for the technically-inclined researcher who already uses GitHub and wants version history of her backups), and **Dropbox or Google Drive** (if the respective desktop clients are detected). Each destination is treated independently — a backup is considered successful if at least one destination succeeds, and failures are logged but do not block the researcher's work.

The archive naming is date-stamped so each destination ends up with a rolling set of backups. A retention policy keeps: the last 7 daily backups, the last 4 weekly backups (one per week), the last 12 monthly backups (one per month), and all yearly backups indefinitely. This gives a researcher the ability to restore from any of the last seven days with daily precision, any of the last four weeks with weekly precision, and so on back in time — matching the principle that recent history needs high resolution and old history only needs coarse milestones.

On a **fresh install** (new computer, broken computer repaired, uninstall-and-reinstall, version upgrade), the first-run wizard asks one question near the beginning: "Do you already have a Metis backup somewhere?" If the researcher says yes, the wizard offers three options: point to a local folder, point to a OneDrive path, or paste a Git repo URL. Metis then searches the chosen location for archive files, shows the list of available backups (with dates and sizes), and lets the researcher pick which one to restore from. The restore decrypts the archive (prompting for the passphrase if one was set), extracts the SQLite database, configuration files, skill files, and logs to the new install's folders, and runs a schema migration to bring the restored database up to the current version. Total restore time for a typical researcher: under a minute.

The **passphrase** question deserves attention because it is where most backup systems lose people. The default is to use a machine-ID-derived passphrase that "just works" on the same machine — the researcher does not have to remember anything to restore on the same computer. For cross-machine restore (the "broken laptop, new laptop" scenario), she needs the passphrase she set during first-run. The first-run wizard makes this explicit: "Set a backup passphrase. You will need this if you ever restore on a different computer. We will show it to you once; write it down." The passphrase is then displayed and the wizard asks her to confirm she has written it down before proceeding. If she declines to set one, a default passphrase is generated and emailed to her (if she provided an email) or displayed on a "recovery info" page she can print. The friction here is deliberate because the alternative — silent backup with no recovery path — is worse than a minute of setup friction.

One more important property: the backup is **idempotent and verifiable**. Every archive includes a manifest file listing every item it contains with its SHA-256 hash. A "verify backup" button in Metis → Settings → Backup downloads the most recent archive from each destination, checks the manifest, and confirms integrity. This catches silent corruption (disk errors, OneDrive sync bugs) before the researcher needs the backup to recover, which is exactly when corruption is most painful to discover.

## 22. Tab-by-tab deep design

> **Superseded by Section 28 for all layout, launcher, and decision specifics.** This section was the first draft of the tab-by-tab design and assumed a six-tab structure (Today · Knowledge · Thinking · Work · Meetings · Metis). The Plan Mode review in Section 28 reworked this into the final eight-tab architecture (Today · Knowledge · Thinking · Planner · Work · Meetings · Learning · Metis), with Planner split out from Work and Learning promoted from a subsection of Metis to its own tab. Read Section 22 as design-history and rationale; read **Section 28** for the locked-in layouts, launcher rows, decisions, cross-tab contracts, and implementation targets. Where the two sections disagree, Section 28 wins.

This is the biggest section of the document because it is where the strategy becomes concrete UI. For each of the six redesigned tabs (as they were proposed at the start of the review), I walk through the header row, the main content, the productivity enhancements I recommend, the cross-tab links, and the launcher buttons that belong in that tab (beyond the simplified versions in the Control Room). The principle is that each tab has its topic at the center and a richer set of actions for that topic than the Control Room shows.

### 22.1 Today — the home screen

**Topic:** orientation, overview, next action. This is where the researcher lands and where she decides what to do.

**Header row.** Left side: the greeting strip ("Good morning, Stan — Friday 10 April 2026"). Right side: the trust badge (green shield, "Local-first, 2 external calls today") and the Ctrl+K quick-capture button. These two elements never move; they follow the researcher into every tab so she can capture or check trust status from anywhere.

**Main content — four sections vertically.** Section one: **What's new overnight** — one-line summary of each category of new activity (papers, news, ideas from mobile, meetings ready for review, agent outputs), each line clickable to deep-link into the relevant tab. Section two: **Today's focus** — a single card showing the one thing the PhD most needs this week, with a "Start working on this" button that opens the relevant project in Work. Section three: **What do you want to do right now?** — the six launcher cards (described in section 4 of this doc). Section four: **Scan for changes** — the button and its result area (described in section 19), collapsed by default and expanding when clicked.

**Productivity enhancements.** A small "Yesterday at a glance" drawer, collapsed by default, that expands to show yesterday's captures, meetings, and agent activity — a way to orient herself if she has been away for a day. A "This week" metric showing: ideas captured, papers read, meetings held, agent runs, tokens spent — one line, subtle, to make the rhythm of her work visible. A "Next scheduled run" line showing when the next automated task will fire ("News Radar runs in 2 hours at 07:00"). None of these add clutter because they are all one-liners in a small footer area.

**Cross-tab links.** Every item in "What's new" links to its home tab. "Today's focus" links to the project in Work. The launcher cards open the external clients. Nothing in Today stays in Today — it is a router.

**Launcher buttons here vs. in specific tabs.** Today shows the six simplified launchers. The equivalent tabs (Thinking, Knowledge, Work, Meetings) show richer versions of the same launchers with more options, as described in the subsections below. Duplicating the simple versions on Today is intentional: it is the fastest path to action from the home screen, and it teaches the launcher pattern.

### 22.2 Knowledge — all literature, all sources, all drops

**Topic:** everything the researcher has read, is reading, or just put in front of Metis. Papers, articles, reports, dropped files, tracked sources.

**Header row.** A segmented control with three views: **All papers** (the searchable library), **In progress** (currently active literature), **Drop new** (the old Dropzone merged in). Plus a search box that is always visible. Plus a "+ Add source" button for adding RSS feeds or repositories.

**Main content — adapts by view.** In **All papers**, a filterable table with columns for title, authors, year, tags, project, and read status, with a side panel showing the selected paper's abstract, cross-links, and action buttons. In **In progress**, a smaller list focused on papers the researcher has actively engaged with in the last 30 days, sorted by last touch, with richer metadata (her notes, the project it supports, what she last asked Metis about it). In **Drop new**, a large drag-and-drop area, a button for "Browse files", and a list of recent drops with their status.

**Launcher buttons — Knowledge-specific versions.** The "Ask Metis about this paper" button (opens Chat with the paper's summary as context) is richer here than on Today: it offers sub-options for "Critique its methodology" (routes to Epidemiologist), "Summarize for a lay audience" (routes to Writing Partner), "Extract data tables" (routes to the docx/pdf/xlsx skills as appropriate), and "Find related papers in my library" (runs a semantic search). The "Open with Metis in Cowork" button (for dropped documents) has sub-options for "Review this draft", "Edit for clarity", "Check citations", and "Generate a summary". The "Process with Librarian" button has sub-options for "Standard processing" (metadata + tags + summary) and "Deep processing" (adds methodology extraction, key findings, critique — uses more tokens but produces a richer record).

**Productivity enhancements.** A **"My reading queue"** panel that shows papers the researcher has added but not yet read, sorted by priority (based on how many active projects reference the paper's topic). A **"Recently cited in your drafts"** panel that cross-references the bibliography of her active article drafts with the library, so she can see at a glance which papers her current writing is leaning on. A **"Dormant"** panel that highlights papers she tagged as important but has not touched in 90+ days — a gentle nudge to revisit. A **"Cite-check this manuscript"** button that takes an article draft and verifies every reference against the library, flagging any that are missing, broken, or misattributed.

**Cross-tab links.** Every paper links to: the Thinking entries that mention it, the Meetings where it was discussed, the Projects that cite it, the Agents that have worked with it. The Drop new view feeds into Cowork (for editing) and Chat (for discussing).

### 22.3 Thinking — ideas, notes, journal, and mindmaps

**Topic:** everything the researcher writes down from her own head. Ideas, quick notes, daily reflections, brainstorm outputs. This is where the second-brain feeling is most visceral.

**Header row.** The **big capture box** — a multi-line text area with placeholder text "What's on your mind?" and a Save button. Auto-classification runs when she clicks Save (idea, note, journal) but she can override via a dropdown. Below the capture box, a row of view-switchers: **Timeline** (chronological list), **Ideas only**, **Journal only**, **Mindmap** (new), **Tags** (tag cloud).

**Main content — adapts by view.** In **Timeline**, a reverse-chronological list with each entry showing its type badge, date, content, and a small row of cross-pollination chips (linked papers, meetings, projects, other ideas). Each entry is expandable to show the full cross-pollination report. In **Ideas only**, a grid of idea cards with "Brainstorm this", "Promote to project", "Link to paper", and "Archive" buttons on each. In **Journal only**, a calendar heatmap showing which days have entries, below it a reverse-chronological list of the actual entries. In **Mindmap**, an interactive node-link visualization (using a library like Cytoscape.js or D3) where nodes are ideas/notes/journals and edges are the cross-pollination connections, navigable by panning and zooming. In **Tags**, a tag cloud where clicking a tag filters the timeline below.

**Launcher buttons — Thinking-specific versions.** The "Brainstorm this" button is the big one here and it deserves its own treatment because you asked specifically for it to work in Plan Mode — see section 23 below for the full spec. The "Promote to project" button opens a small dialog asking "Which project should this join?" with a dropdown of existing projects and a "+ New project" option. The "Link to paper" button opens a search-and-select modal over the Knowledge library. The "Archive" button marks the entry as inactive without deleting it. All of these keep the researcher in the dashboard — they are fast actions for managing her own thoughts.

**Productivity enhancements — the mindmap view specifically.** This is worth calling out because you mentioned it. The mindmap should not be a toy — it should be the best way to see the shape of the researcher's thinking. It shows ideas as nodes, colored by age (recent = bright, old = faded), sized by cross-pollination count (well-connected ideas are bigger). Edges are colored by relationship type (idea→paper, idea→meeting, idea→project). Clicking a node centers the graph on it and dims everything more than two hops away. A filter bar lets her show only ideas related to a specific project, or from a specific time window, or tagged with a specific term. The mindmap is also where the "uncharted territory" insight surfaces: ideas that have few or no cross-pollination links are visually obvious and can be clicked to open a brainstorm session specifically designed to connect them.

A second productivity enhancement is **idea thread view**. When an idea has been developed over multiple sessions (capture → brainstorm → refinement → promotion to project), those sessions are grouped as a "thread" and shown in chronological order, so the researcher can see how an idea evolved. This is easy to implement because the session memory is already linked to the originating idea — it is just a query and a visualization.

A third is the **"Stale ideas" nudge**: ideas that were captured but never developed, shown as a small weekly digest on Mondays. "You captured 4 ideas last month that you haven't revisited. Want to brainstorm one?" This turns forgotten captures back into active thinking, which is the entire point of capturing them.

**Cross-tab links.** Every thinking entry links to its cross-pollination targets (papers, meetings, projects, ideas) and is reachable from the inverse direction (a paper card in Knowledge shows which thinking entries reference it). Thinking entries that get promoted to projects create a link in the project's card.

### 22.4 Work — projects, plans, tasks, PLANNING.md files

**Topic:** the researcher's active work, organized into projects. Each project is a container for goals, plans, tasks, files, and external launchers.

**Header row.** A row of project cards across the top, scrollable horizontally, each showing the project name, health indicator (green/amber/red based on task freshness and deadline pressure), and a single primary action button. Below this, a "+ New project" button and a segmented control: **Active** (default) / **Paused** / **Archived**.

**Main content — when a project is selected.** The selected project expands into a detail view with four horizontal sections. Section one: **Plan** — the contents of the project's PLANNING.md file, rendered as markdown, editable inline. Changes here write back to the PLANNING.md file on disk. Section two: **Tasks** — a list of open tasks for this project, with priority, due date, and source (manual / meeting / agent). Each task has quick actions to mark done, reschedule, or assign to a sub-project. Section three: **Files** — the tracked files for this project (the ones with `watch=1`) with their modification status from the last scan. Clicking a file opens the project's launcher to that file. Section four: **Activity** — a reverse-chronological log of everything that has happened in this project: meetings discussed, ideas captured, agent runs, git commits, document changes.

**Launcher buttons — Work-specific versions.** The project card's primary launcher button is context-aware: for a code project it says "Open in Claude Code", for a document project it says "Open in Cowork", for a slide deck it says "Edit in Cowork", for a data project it says "Analyze with Methods Coach". Under each primary button, a dropdown menu offers alternative launchers: "Discuss in Chat", "Open folder in Explorer", "Open in Git client", "Run tests", "Generate report". The researcher picks the right tool for the moment.

**Productivity enhancements.** A **"What's blocked"** view that filters across all projects to show just the tasks that are waiting on something (another person, another deadline, a piece of data) — reduces the "what should I work on now?" decision to a single glance. A **"Weekly commitment"** section at the top of each project card showing what the researcher committed to do this week (pulled from her Monday morning planning session, written by her to herself). A **"PLANNING.md diff"** view that shows what changed in the plan since the last session, so returning to a project starts with reading the delta rather than the whole plan. A **"Project handoff brief"** button that generates a single-page summary of the project suitable for pasting into a Claude Chat to resume work elsewhere — the same mechanic as the session handoff, applied at the project level.

**Cross-tab links.** Every project links to its papers in Knowledge, its meetings in Meetings, its ideas in Thinking, and its agent activity in Metis. Every task in a project can be traced back to its source (the meeting where it was created, the idea that spawned it, the scan that found it).

### 22.5 Meetings — record, transcribe, analyze, prepare

**Topic:** meetings in all their forms — one-on-ones, group meetings, seminars, conference talks. Record, import, review, and extract action items.

**Header row.** Primary action buttons: "Record new meeting" (opens the three-mode recorder: quick, auto, live), "Import transcript" (paste or upload from Otter, Fireflies, etc.), and "Prep for meeting" (opens the prep view). Plus a search box that searches across all meeting transcripts.

**Main content.** A list of past meetings sorted by date, each showing title, attendees, duration, and status (raw transcript / analyzed / action items extracted). Clicking a meeting opens a detail view with the transcript, the structured analysis from Meeting Memory (attendees, key decisions, open questions, action items, related topics), and a row of buttons: "Create tasks from action items", "Link to project", "Send brief to Chat", "Add follow-up journal".

**Launcher buttons — Meeting-specific versions.** The "Prep for meeting" launcher is the richest version here. Clicking it opens a form asking: who are you meeting with, what is the meeting about, what do you want Metis to include in the brief. Metis then assembles the brief by pulling from contacts (what was discussed in previous meetings with these people), from projects (which projects are relevant), from ideas (which ideas need to be discussed), from the reading queue (which papers to mention), and from the research diary (what has the researcher been thinking about related to this). The result is a one-page prep document rendered inline, with a "Copy to Chat" button that opens Claude Chat with the brief pre-loaded. The "Send brief to Chat" launcher on a past meeting is similar but scoped to that specific meeting's content.

**Productivity enhancements.** A **"Meeting debt"** view showing meetings that were recorded or imported but never analyzed, so the researcher does not let transcripts accumulate unreviewed. A **"Decisions log"** view that extracts every decision from every meeting and shows them chronologically — useful for tracking "when did we decide X?" without scrolling through individual meetings. A **"Repeat topics"** view that clusters meetings by topic and surfaces when the same issue has come up multiple times ("You've discussed the cluster analysis approach in 4 meetings over the last 3 months"). A **"Quiet people"** insight that highlights contacts the researcher used to meet with frequently but has not talked to recently — useful for maintaining collaborations.

**Cross-tab links.** Every meeting links to its contacts, its projects, the ideas it generated, the papers it mentioned. Action items from a meeting appear as tasks in the relevant project. The "brief to Chat" launcher opens Claude Chat with the meeting summary as context.

### 22.6 Metis — agents, memory, settings, self-improvement

**Topic:** the system itself. Agents, sessions, memory, settings, the things that make Metis work.

**Header row.** Four sub-tabs: **Profile** (the researcher's thinking profile and configuration), **Agents** (the team roster and self-improvement queue), **Memory** (session history and retrieval debugging), **Settings** (everything else, from API keys to backup destinations).

**Main content — adapts by sub-tab.** In **Profile**, a rendered view of `thinking-profile.yaml` showing what Metis has learned about the researcher — which connections she follows up on, which agents she uses most, which types of ideas she promotes. She can edit any of this manually. In **Agents**, a grid of agent cards showing name, model, recent run count, recent success rate, and a "pending proposals" badge if the Coach has suggested changes. Each agent card opens a detail view with the skill file, the run history, the reflexion log, and the proposal queue. In **Memory**, a searchable view of all sessions with filters by date, Claude client, project, and content. Clicking a session opens a detail view with every event in that session. A "retrieval debugger" box at the top lets the researcher type a query and see which memory layers returned which results — invaluable for understanding why Metis gave a particular answer. In **Settings**, everything else: API keys, backup destinations and schedule, automated task schedule, model assignments, network policy (strict/normal/airplane), red line configuration, data protection preferences, dashboard port override, theme (light/dark), and a "diagnose" button that runs a full system health check.

**Productivity enhancements.** The **retrieval debugger** is worth emphasizing. It is a small box where the researcher types a question and sees what Metis would retrieve, layer by layer, for that question. This is what researchers need to build trust in the memory system: they can see that when they ask "what did Sara say about post-elimination surveillance last month?", Metis correctly pulls from the semantic layer (Sara the entity), the episodic layer (meetings with Sara), and the vector layer (semantically similar passages). The transparency turns the memory from a black box into a tool. A **"memory health"** widget shows the size of each memory layer, the number of entries, the last compression run, and the disk size — so she can see the system is being maintained. A **"token ledger"** shows cost per agent and per day with the cache hit rate, making token efficiency visible.

**Cross-tab links.** Every agent's run history links to the outputs that run produced (in whichever tab they belong). Every session in Memory links to the entities it touched across all other tabs. The settings page has links to the red-lines.md and token-guardrails.md source files for full transparency.

## 23. The Brainstorm Plan Mode

You asked specifically that the brainstorm function work in "Plan Mode" — where Claude actively asks questions to enrich the conversation, the user can steer at any time, and the user can cross-pollinate at any point in the conversation. This is a specific interaction pattern that deserves its own specification because it is different from how brainstorming usually works in chat interfaces.

The core of Plan Mode brainstorming is that Claude is not a passive responder but an active interviewer. When the researcher launches a brainstorm from an idea, Metis does not open a blank chat. It opens a conversation that begins with Metis speaking first, having already done three pieces of work: loaded the idea and its cross-pollination context, read the researcher's thinking profile to understand her preferences, and drafted an opening move that is a clarifying question, not a summary. Something like: "You captured this idea yesterday: 'Use movement data to refine HAT risk mapping.' I see you've been thinking about both movement data and risk mapping separately for months. Before I go looking for connections in your library, I want to understand what kind of movement data you have in mind — cellular mobility, transport corridors, livestock migration, or something else?"

The researcher answers. Metis takes her answer and does one of three things. It asks another targeted clarifying question if the answer opened a new thread ("Livestock migration. Does that mean you're thinking about tsetse–host dynamics, or about human–livestock co-travel?"). It performs a specific cross-pollination and surfaces the results ("Since you said cellular mobility, here are three papers in your library that use mobile phone records for disease mapping, and one meeting where Dr. K mentioned a similar approach"). Or it asks the researcher to steer ("I have two possible directions to take this — would you rather explore the data you'd need, or explore how the analysis would work?"). Every turn Metis takes either deepens the context or offers a fork in the road.

**The steering mechanism.** At every turn, alongside whatever Metis says, there is a small persistent UI element — a row of four buttons below Metis's message — labeled "Continue this thread", "Change direction", "Cross-pollinate now", and "End and save". "Continue this thread" is the default and happens if the researcher just types a reply. "Change direction" opens a small prompt where she can redirect the conversation ("Stop exploring data sources, let's talk about what the finished analysis would look like"). "Cross-pollinate now" triggers a cross-pollination pass on the conversation so far, surfaces any new connections, and hands control back to Metis to respond to them. "End and save" wraps the conversation into a structured output (a short summary, the key decisions, any new questions raised, links to cross-pollinated items) and saves it to Thinking as a new journal entry linked to the original idea.

**The cross-pollinate anytime feature** is the important one for the second-brain promise. At any point in the conversation — even ten turns in — the researcher can click "Cross-pollinate now" and Metis takes whatever has been discussed so far and runs it through the full retrieval pipeline (all five memory layers) looking for connections she did not explicitly bring up. The results appear as a side panel of cards: "This conversation relates to a paper you read in November", "Similar to a meeting with Dr. M last spring", "This idea cluster is underdeveloped in your library — here are three adjacent topics you haven't explored". The researcher can click any card to bring that context into the conversation, or dismiss them to keep the current thread clean. This turns the brainstorm from a linear conversation into a branching exploration where Metis is constantly offering new doors.

**The underlying mechanic** is that Plan Mode brainstorms run against a specialized MCP tool set: the standard Metis tools plus a dedicated `brainstorm_turn` tool that wraps Claude's response with the decision about what to do next (clarify, cross-pollinate, fork, continue). Claude is prompted with a system message that says "You are Metis in Plan Mode. Your job is to enrich the conversation through targeted questions and timely cross-pollination. Always prefer one good question over three statements." This keeps Claude's responses short, focused, and Socratic.

**The output** is structured by default. When the researcher clicks "End and save", Metis produces a document with five sections: the original idea, the clarifying questions that were asked and answered, the key decisions or directions that emerged, the cross-pollination discoveries, and the next action (usually a concrete follow-up: "schedule time to read papers X and Y" or "draft a short methodology sketch" or "talk to Dr. K about this"). This document becomes a new entry in Thinking and is linked back to the original idea as a "brainstorm thread."

## 24. Self-improvement embedded at every layer

You asked for the self-improvement to be embedded in every step of the project, and I agree strongly — this is the property that makes Metis a living system rather than a static tool. Here is how self-improvement is woven through every layer, from the individual agent up to the installer itself.

At the **agent layer**, every agent writes a self-critique at the end of every run, as described in section 8. The critique is a structured small object: what went well, what was hard, what was missing, what the user's implicit feedback was. These accumulate in the reflexion_log and are reviewed weekly by the Coach. This loop already exists in pieces; it needs to be made uniform across all 21 agents via a shared contract in the agent template.

At the **routing layer**, Metis itself writes a decision log: for each incoming request, which agent was chosen, which complexity was picked, which model was assigned, and what the outcome was. The Coach reviews this log and identifies routing patterns that are systematically wrong (over-complexity, under-complexity, wrong agent for a type of request). Proposed routing changes appear in the same proposal queue as agent skill changes.

At the **retrieval layer**, the memory system logs which results were actually used by agents versus which were retrieved but ignored. If a certain kind of query consistently retrieves results that are not used, the retrieval pipeline needs tuning. The Coach reviews these logs weekly and proposes changes to the retrieval ranking weights or the reranker prompts.

At the **dashboard layer**, the researcher's implicit feedback (clicks, promotions, dismissals, time spent on each view) is logged as anonymous event counts. Patterns emerge: "the researcher almost never opens the News sub-view" → the News sub-view can be collapsed by default to reduce clutter. "The researcher always clicks the same three launcher buttons" → those three should move to the top. The Coach proposes UI layout changes based on usage patterns.

At the **installer layer**, the installer includes an optional post-install survey (truly optional, dismissible in one click) that asks: "How did the install go? Any issues?" Responses are logged locally and optionally uploaded anonymously to help improve the next installer. Every install failure writes a diagnostic log that the researcher can inspect and share if she wants to report a bug.

At the **implementation layer** — this is the recursive piece — the implementation-progress.json file tracks what we built and records which steps were hard, which needed rework, which introduced bugs. When we start a new session of implementation work, Claude reads the recent progress entries and notes any recurring themes ("we keep forgetting to update the schema migration file when we add tables — add a checklist item"). This is Metis improving its own construction process.

The principle across all layers is the same: every action produces a signal, the signal is logged, the logs are reviewed on a schedule, improvements are proposed, and improvements are applied only after human approval. No layer is exempt. No improvement is silent. And the proposal queue is always visible to the researcher in Metis → Agents so she can see the system learning.

## 25. Testing strategy — standardized tests and manual checklists

You asked for tests we can run, both standardized (automated) and manual (human-driven). Here is the full testing pyramid for Metis, organized by layer.

**Unit tests** live in `<Metis>/tests/unit/` and test individual functions in isolation. Python backend tests use pytest. They cover: the port-selection routine (does it correctly fall back through the range and pick a random port if all are busy?), the JSON config merger (does it preserve existing MCP servers when adding Metis?), the anonymization function (does it redact names, dates, GPS correctly?), the red-line classifier (does it correctly identify SENSITIVE vs. CONFIDENTIAL content?), the retrieval pipeline (does each layer return expected results for known inputs?), and the session memory compression (does weekly compression preserve key decisions while reducing size?). Target: 80% code coverage on the backend. Runs in under 30 seconds.

**Integration tests** live in `<Metis>/tests/integration/` and test multi-component flows. They cover: the full /metis pipeline (send a request, verify it flows through all 11 stages and produces expected logs), the backup and restore cycle (create data, back up, wipe, restore, verify byte-identical), the JSON config merge in realistic conditions (existing Claude Desktop config with 3 other MCP servers, merge Metis, verify all 4 are present), the scheduled task execution (run News Radar programmatically, verify the morning_briefs table has the expected entry), and the cross-client session handoff (start a session via MCP, save handoff, resume via different client ID, verify context is preserved). Runs in under 5 minutes.

**End-to-end tests** use Playwright (for the dashboard) and the MCP test client (for the MCP server). They cover the five critical user flows, each scripted as a single test. Flow one: install Metis in a clean Windows VM, verify the dashboard opens on the chosen port, verify the tray icon appears. Flow two: capture an idea via Ctrl+K, verify it appears in Thinking, verify cross-pollination ran. Flow three: drop a PDF, verify the Librarian processes it, verify it appears in Knowledge. Flow four: brainstorm an idea in Plan Mode (mocked Claude responses), verify the conversation structure and the steering buttons work. Flow five: run a backup, wipe the database, restore from backup, verify all data is intact. Runs in about 10 minutes.

**Smoke tests** run on every commit in CI. They are a subset of the e2e tests that run in under 2 minutes and catch regressions. They verify: the backend starts, the dashboard responds on the port, the MCP server responds to a `list_tools` call, the database schema is current, and the core agents can be loaded.

**Manual test checklists** are for you, the researcher, to run after each phase of implementation to verify things feel right in addition to working correctly. Here is the checklist for the dashboard redesign phase, as an example:

- Open the dashboard. Does the Today tab fit in one screen without scrolling on a 1080p laptop? If not, something is too dense.
- Count the tabs in the nav bar. Is it exactly six? If there are more, we forgot to consolidate.
- Press Ctrl+K from anywhere in the dashboard. Does the quick-capture modal open immediately? Type "test idea", press Save, and verify it appears in Thinking within 3 seconds.
- Click each of the six launcher cards on Today. For the three that launch Claude clients, verify the browser/terminal opens. For the three that stay in the dashboard, verify the correct view loads.
- Drop a PDF into the Knowledge → Drop new view. Verify the three post-drop buttons appear (Process, Open in Cowork, Ask Metis).
- In Thinking, switch to the Mindmap view. Verify it renders, verify panning and zooming work, verify clicking a node centers the graph.
- In Work, select a project. Verify the four sections (Plan, Tasks, Files, Activity) are present and populated. Click the launcher button. Verify the right Claude client opens.
- In Meetings, click "Prep for meeting". Verify the form appears, fill it in, and verify the assembled brief shows cross-links to the expected sources.
- In Metis → Memory, use the retrieval debugger. Type a query you know has relevant content. Verify results appear labeled by which layer they came from.
- In Metis → Settings → Backup, click "Run backup now". Verify a new archive appears in the configured destinations within a minute. Click "Verify backup" and verify it reports integrity.

Each checklist item is short, concrete, and verifiable in under a minute. A full manual test run for a given phase takes about 15–20 minutes.

**Red-line tests** are a special category because they are the safety guarantees. These are hard-coded tests that must always pass before any release ships. They include: attempt to send patient data via the MCP → verify it is blocked with the correct error. Attempt to send a file with sensitive columns → verify it is blocked. Attempt a prompt injection via a file with hidden instructions → verify it is detected and the researcher is warned. Attempt to bypass the data guardian via an "urgent" framing → verify the urgency language does not override the guardian. These tests are ugly but essential. They run on every build.

## 26. The implementation checklist — the big board

This final section is the living plan that ties everything in this document together. It is the set of milestones the implementation-progress.json file will track. I list them here so that you and I both have a single place to look at the whole plan, and so that future sessions can pick up by scanning this section.

**Phase 0 — Foundations (days 1–3).** M0.1 Create the implementation-progress.json file and the implementation-log.md. M0.2 Update the PKM Builder agent's system prompt to enforce reading/writing the progress tracker. M0.3 Create a dev testing VM and verify a clean Windows 11 machine is ready for install testing. M0.4 Set up the git repository for Metis if not already present, with a clear branch strategy.

**Phase 1 — Dashboard consolidation (week 1–2).** M1.1 Audit the current 12 tabs and decide which code modules will be merged or removed. M1.2 Create the new 8-tab structure in app.R (Today · Knowledge · Thinking · Planner · Work · Meetings · Learning · Metis — see Section 28) with stub modules for each tab. M1.3 Move Library + Research code into the new Knowledge module (News Radar becomes the bottom band of Knowledge, not a tab). M1.4 Move Ideas + Notes + Journal code into the new Thinking module with the frictionless-capture classifier. M1.5 Keep Planner as its own tab (do NOT merge with Projects as earlier drafts suggested). Move the existing Planner code into the standalone Planner module. M1.6 Move Projects code into the new Work module with the card-grid layout. M1.7 Keep Meetings as a standalone tab with its existing code as a baseline. M1.8 Promote Learning from a System sub-section to its own tab — seed with the course registry schema and a manifest reader. M1.9 Move System + News config + Coach surface into the new Metis module with five memory sub-views. M1.10 Dissolve Dropzone as a tab and implement the floating drag-and-drop affordance available from every tab. M1.11 Delete the old modules once the consolidated versions are working. M1.12 Visual audit: confirm each tab fits one screen, has clear hierarchy, and uses the whitespace principles.

**Phase 2 — Today tab redesign (week 2).** M2.1 Strip the Control Room down to four sections. M2.2 Build the six launcher cards with the Today-level simplified actions. M2.3 Build the "What's new overnight" summary. M2.4 Build the "Today's focus" card. M2.5 Build the "Scan for changes" button and its result area. M2.6 Wire the trust badge into the header.

**Phase 3 — Quick capture (week 2 parallel).** M3.1 Build the Ctrl+K shortcut handler. M3.2 Build the capture modal with auto-classification. M3.3 Wire the modal to the capture_idea MCP tool.

**Phase 4 — Master pipeline (weeks 3–5).** M4.1 Design the session_events and session_context schemas. M4.2 Implement the session bootstrap stage. M4.3 Implement the Data Guardian intercept stage. M4.4 Implement the Cybersecurity intercept stage. M4.5 Implement the intent parsing stage. M4.6 Implement the token budget allocation stage. M4.7 Implement the surgical context assembly stage. M4.8 Implement the execution with incremental save stage. M4.9 Implement the output red-line post-check. M4.10 Implement the logging stage. M4.11 Implement the self-improvement capture stage. M4.12 Wire all stages together and run the end-to-end pipeline tests.

**Phase 5 — Multi-layered memory (weeks 6–7).** M5.1 Install sqlite-vec and set up the vector tables. M5.2 Install sentence-transformers and pick an embedding model. M5.3 Implement the episodic memory layer. M5.4 Implement the semantic memory graph. M5.5 Implement the procedural memory tracker. M5.6 Implement the working memory. M5.7 Implement the reflexive memory (already partly exists). M5.8 Build the retrieval pipeline with RRF fusion and reranking. M5.9 Build the retrieval debugger UI in Metis → Memory.

**Phase 6 — Anonymization and trust UI (week 8).** M6.1 Build the anonymization function (Python + NER). M6.2 Build the diff view for anonymized content. M6.3 Build the trust badge in the dashboard header. M6.4 Build the consent ledger table and UI. M6.5 Build the network policy switcher (strict/normal/airplane).

**Phase 7 — Backup and portability (week 9).** M7.1 Build the nightly backup job. M7.2 Build the encryption layer. M7.3 Build the multi-destination writer. M7.4 Build the restore wizard. M7.5 Build the backup verification. M7.6 Test a full wipe-and-restore cycle.

**Phase 8 — Brainstorm Plan Mode (week 10).** M8.1 Build the brainstorm_turn MCP tool. M8.2 Build the Plan Mode system prompt. M8.3 Build the steering buttons UI in the Thinking tab. M8.4 Build the cross-pollinate-anytime side panel. M8.5 Build the structured output format for saved brainstorms.

**Phase 9 — Self-improvement loop (week 11).** M9.1 Extend every agent's contract to require reflexion output. M9.2 Build the Coach agent. M9.3 Build the weekly Coach run schedule. M9.4 Build the proposal queue UI. M9.5 Build the approval/rejection flow.

**Phase 10 — Automated daily tasks (week 12).** M10.1 Build the scheduler in the backend. M10.2 Register the default schedule (News Radar, Librarian, Morning Brief, Cross-Pollinator, Coach, Weekly Summary). M10.3 Build the schedule UI in Metis → Settings.

**Phase 11 — Installer and distribution (weeks 13–14).** M11.1 Build the vendor wheel download script. M11.2 Write the Inno Setup script. M11.3 Build the JSON config merger. M11.4 Build the embedded Python bootstrap. M11.5 Build the tray launcher. M11.6 Build the port-selection routine. M11.7 Run the full install test in a clean VM. M11.8 Get code-signing certificate and sign the installer.

**Phase 12 — Testing, polish, documentation (week 15).** M12.1 Write the unit test suite. M12.2 Write the integration test suite. M12.3 Write the e2e test suite in Playwright. M12.4 Write the red-line test suite. M12.5 Run the manual test checklist end-to-end. M12.6 Write the researcher-facing getting-started guide. M12.7 Set up getmetis.org with the download page. M12.8 Ship v1.0.

That is 75 numbered milestones across 12 phases spanning roughly 15 weeks. Each milestone is small enough to complete in a single Claude session of reasonable length. The progress tracker records the status of each as we move through them, so no matter when we stop or what token budget we have, the next session can start by reading the tracker and picking up at the next pending milestone.

## 27. Final closing thoughts

I want to end this document the same way it began: by reminding both of us who we are building for. The researcher is paralyzed by AI today because AI feels like someone else's tool. Every milestone above, every memory layer, every port failsafe, every launcher button exists to remove a single piece of that paralysis. When she downloads Metis and installs it without hitting a single error, paralysis drops. When she drops her first PDF and sees Metis process it safely, paralysis drops. When she captures her first idea and sees three cross-pollinations she did not expect, paralysis drops. When she brainstorms in Plan Mode and Metis asks her exactly the right question, paralysis drops. When she wipes her machine and restores from backup in under a minute, paralysis drops. The cumulative effect of all those small drops is a researcher who trusts AI enough to let it into the deepest parts of her work.

That is the goal. The 75 milestones are the path. The two strategy documents in `08_system/` are the map. The implementation-progress.json file is the odometer. Let's build.

---

---

## Section 28 — Plan Mode Decisions Log

This section records locked-in decisions from the tab-by-tab Plan Mode review. Each entry is timestamped. Decisions here override earlier recommendations in section 22 when they conflict.

### 2026-04-10 — Today tab

- **Morning Brief cadence:** Regenerate once at 06:00 local. Static for the day. Manual "Regenerate" button available in the card header for on-demand refresh. Rationale: honors token guardrails, avoids burning tokens on dashboard opens.
- **"Where you left off" source:** Fuse three sources — reflexive memory from last session, last git commit across tracked projects, last file edited via Cowork. Rank by recency, surface the top hit, expose the other two behind a "More" link in the card.
- **Ctrl+K quick capture:** Global shortcut across all eight tabs. Pops a floating capture sheet from anywhere in the dashboard. Prefix routing (`i:` idea, `n:` note, `q:` ask Metis, `t:` task, no prefix → idea). The sticky footer on Today is the always-visible affordance; Ctrl+K is the keyboard path.
- **Today layout locked:** (1) greeting + status strip, (2) Morning Brief hero card, (3) 4-button launcher row including Scan for changes, (4) conditional focus row (tasks / meetings / follow-ups), (5) sticky quick capture footer. All 11 legacy Control Room panels redistributed per section 22.

### 2026-04-10 — Knowledge tab

- **Knowledge absorbs** Library + Research + News into a single tab with three horizontal bands (Your library · Active reading · News radar), not three sub-tabs.
- **Launcher row (5 buttons):** Ask the Librarian (Chat) · Deep research (Cowork) · Add to library (Dropzone + Librarian) · Scan news now · Build a reading list (Chat).
- **Hybrid search default:** FTS5 lexical + sqlite-vec semantic + RRF fusion + BGE reranker. A "Fast search" toggle falls back to lexical-only for known exact terms.
- **News Radar dismissal learning:** Passive — each dismissal contributes to a per-project "dismissal embedding centroid" used to downrank similar items in future runs. No popup prompts. A weekly digest in the Metis tab narrates filter adjustments ("I dropped X-type items because you dismissed Y of them this week").
- **"Why it matters to you" notes:** Generated once at library ingestion (Librarian writes them), refreshed weekly during Coach's run so relevance tracks evolving projects. Never generated on render, never per-hover.
- **Cross-tab contracts:** library card → right-click → Link to project / Link to idea / Cite in current document. News item → "Ask Metis about this" opens Chat with item as pre-loaded context. Active reading item → "Start brainstorm from this paper" opens Plan Mode brainstorm with abstract + highlights as seed context.

### 2026-04-10 — Tab count revised: 7 tabs, not 6

Planner is kept as its own tab rather than being absorbed into Thinking. Rationale: Thinking is divergent (capture, connect, explore), Planner is convergent (commit, sequence, deliver). Mixing them dilutes both modes. Final tab list: **Today · Knowledge · Thinking · Planner · Work · Meetings · Metis**. Section 22 of this document is superseded on this point.

### 2026-04-10 — Thinking tab

- **Thinking absorbs** Notes + Ideas into a single unified capture surface. Journal entries also live here. Planner does NOT merge in.
- **Launcher row (4 buttons — "Plan the week" moved to Planner tab):** Start a brainstorm (Chat, Plan Mode) · Capture an idea (floating sheet) · Journal now (editor pane) · Cross-pollinate (Metis retrieval across all Thinking + library + projects, returns 5 unexpected connections).
- **Three view modes:** List (default, unified stream with type icons and link counts) · Mindmap (D3 force graph, nodes = items, edges = manual + implicit semantic links, threshold slider, sparse default) · Timeline (chronological by week, sparkline of capture volume).
- **Frictionless capture:** No type required at capture time. Everything starts as a generic "Thought." A lightweight classifier runs on a 15-minute delay to assign idea / note / journal. User can override any auto-classification with one click.
- **Mindmap default:** Sparse threshold — only strong manual links plus high-confidence semantic links (~5-10 edges per node). Slider lets users go denser for exploration; density is never the default.
- **Brainstorm as first-class item type:** Brainstorm outputs are saved as a new item type "Brainstorm" with its own icon and filter, containing the transcript, steering events, questions explored, insights, open threads, and action items. Brainstorms link to ideas, notes, and projects through the same linking model as other items.
- **Link model (three kinds):** Manual links (explicit `[[title]]` or link picker) · Suggested links (Coach proposes weekly, user accepts/rejects in Metis tab proposal queue) · Implicit links (computed live in mindmap view only, never stored, never shown in list view). Accepting a Suggested link promotes it to Manual and feeds Coach's self-improvement signal.
- **Brainstorm Plan Mode card:** Always-visible bottom card explaining the flow, with a "Start a brainstorm" button and chips for the 3 most recent brainstorm sessions (resumable via reflexive memory).

### 2026-04-10 — Planner tab (standalone)

- **Purpose:** Convergent mode — where intent meets time. Synthesizes commitments across projects, deadlines, journaled intents, and (later) external calendar. Distinct from Thinking (divergent) and Work (execution).
- **Launcher row (5 buttons):** Plan my week (Cowork, Planner agent) · Plan my day (Chat, Planner agent) · Review the week (Chat, Friday reflection) · Set a deadline (quick form) · Time-box a task (Pomodoro/custom timer with elapsed time logging).
- **Three stacked sections:** (1) This week at a glance — 7-day strip with fixed commitments, deep-work blocks, deadlines, capacity indicator (green/yellow/red); (2) Active deadlines — ranked list sorted by urgency × weight with color coding (red/amber/blue/grey); (3) Intent tracker — open intents extracted from journals, brainstorms, and morning briefs with Do now / Reschedule / Drop actions.
- **Calendar integration:** DEFERRED to v1.1. No Google or Outlook connection shipped at v1. Reserve the architectural hook and schema columns so integration can plug in later without a redesign. UI shows a soft "Connect calendar (coming soon)" affordance in the 7-day strip header. Planner remains fully functional with manual deadlines and deep-work blocks.
- **Weekly plan generation:** ALWAYS a proposal. The Planner agent drafts the week in a side panel; the user explicitly accepts before anything hits the 7-day strip. Never auto-commits. Consistent with the proposal-review pattern used for Suggested links and skill improvements.
- **Intent extraction:** Nightly batch pass. Intents from journal entries, brainstorms, and morning briefs are extracted overnight by a lightweight NLP pass (bundled into a single LLM call for token efficiency). New intents appear in the next morning's Morning Brief. Gentle nagging on intents older than 3 days. Dropped intents with reason contribute a self-improvement signal to the extractor.
- **Cross-tab contracts:** Planner reads from Work (projects, tasks, deadlines), Thinking (journal intents, brainstorm action items), Meetings (once connected), Knowledge (reading commitments). Planner writes to Work (time-boxed task blocks), Today (feeds Morning Brief with today's plan), Metis (logs planning sessions for Coach review).

### 2026-04-10 — Work tab

- **Purpose:** Execution surface for deliverables — manuscripts, dashboards, scripts, analyses, chapters. The tab a researcher opens to *do the work*, not plan or think about it.
- **Launcher row (5 buttons):** Open current project in Cowork · Write or edit a document (Writer/Editor agent, auto-detects file type) · Start a new project (form with name, type, linked ideas/reading, folder init) · Run an analysis (Analyst agent, scoped to project) · Ship it (checklist flow: tests, red-lines, backup, version, changelog, commit/export).
- **Active project detection:** Hybrid model. A manually pinned project always wins. Falls back to most-recent file activity when nothing is pinned. The "Open current project" button displays which mode is active — "Pinned: HAT clustering" vs "Inferred: HAT dashboard" — so ambiguity is zero.
- **"Ship it" checklist strictness:** Warns loudly on failed items (red-lines, backup freshness, tests) but allows override with a typed confirmation. Never hard-blocks. Rationale: a hard block makes researchers route around Metis under pressure, which is the worst outcome. Warnings preserve trust while still flagging risk.
- **Project status auto-summary:** Event-driven. Any tracked file change, git commit, or agent session on a project triggers a tiny Haiku re-summary of its 1-line status. Always fresh, never wasted — cheap because Haiku is inexpensive and projects don't change constantly.
- **Active projects board:** Card grid (not Kanban — too rigid for research). Each card shows project name, type icon, 1-line auto-summary status, last touched, next milestone from Planner, progress ring, three mini-buttons (Open · Scan · More). Pinned "currently working on" section on top. Filters: All · Manuscripts · Analyses · Dashboards · Courses · Archived.
- **Recent work stream:** Chronological stream at the bottom — file edits, commits, exports, analyses, agent sessions — grouped by day, collapsible. Serves "what did I actually do yesterday?" and end-of-week reviews.
- **Dropzone dissolved as a tab:** The top-level Dropzone tab is removed. Its function becomes a floating drag-and-drop affordance available from any tab. Drop a file → small modal asks "What should I do with this?" with options: Add to library · Attach to project · Review and edit · Extract data · Just store it. Dropzone-as-verb, everywhere, not Dropzone-as-destination.
- **Cross-tab contracts:** Work reads from Planner (deadlines, time-boxed blocks), Thinking (linked ideas), Knowledge (linked reading), Meetings (project-related meetings). Work writes to Planner (task completion), Today (recent activity → "where you left off"), Metis (all agent sessions logged).

### 2026-04-10 — Meetings tab (standalone, no external integrations)

- **Purpose:** Memory and follow-through for research meetings — supervision, committees, WHO working groups, seminars, external collaborators. Value is in the past (what was said and decided), not the future (scheduling).
- **No calendar or email integration, ever until explicitly requested.** Meetings are entered manually. Upcoming meetings are a simple user-entered list (title, date/time, participants, optional agenda, optional linked project). No OAuth, no external APIs, no "coming soon" affordance.
- **Launcher row (5 buttons):** Record a meeting (local audio capture + live sidecar) · Upload a recording (post-hoc pipeline) · Start meeting notes (Cowork, Notetaker agent) · Prep for a meeting (Chat, Meeting-prep agent) · Follow up on decisions (Chat, walk through open action items).
- **Section 1 — Timeline of recent meetings:** Horizontal scrolling timeline of past meetings with cards hanging from a line. Type icon, participants, duration, 3-bullet summary. Click to expand inline with full notes, action items, decisions, transcript access. Upcoming manually-entered meetings appear as pill chips above the timeline with "Prep for this" buttons.
- **Section 2 — Decisions & action items stream:** Unified stream from all meetings. Filters: Mine · Owed to me · Decided · Open. Per-item actions: Mark done · Reschedule · Convert to task (creates Work task) · Link to idea (creates/links Thinking item).
- **Section 3 — Meeting memory search:** Hybrid retrieval (FTS5 + vec + RRF + reranker) scoped to meeting transcripts and notes. Returns snippets with speaker labels, timestamps, links to full meetings.
- **Whisper model choice:** Per-meeting selection. Default is local Whisper base. "Use cloud Whisper" toggle is exposed only when a meeting is flagged non-confidential. CONFIDENTIAL meetings (default) stay fully local.
- **Diarization:** Always on for any recording made inside Metis. Speaker labels attached to every transcript segment.
- **Action item extraction — three categories:** Explicit ("Sarah will send the dataset by Friday") · Implied ("we should probably look into this") · Open questions. Implied and questions are flagged "needs review" so the user confirms or drops them. Drops with reason feed the extractor's self-improvement signal.

### 2026-04-10 — Live cross-link feedback during recording (novel feature)

- **What it is:** During an active recording, Metis runs a hybrid retrieval pass once per minute against the rolling transcript buffer and surfaces relevant cross-links to the user in a non-blocking sidecar panel next to the recording widget.
- **Cadence:** Exactly once per minute. Rationale — a minute is the natural unit of a conversational turn (enough content to be meaningful, short enough to be actionable), it keeps retrieval cost bounded and predictable, and it avoids the flicker effect of continuous re-retrieval.
- **Input window:** The last ~60 seconds of diarized partial transcript (~150-200 words). Earlier portions are weighted lower so the sidecar tracks the conversation's *current* direction.
- **Card types (all four surfaced by a single retrieval query):**
  - Paper match — "Reminds me of Büscher 2017, which you read and highlighted 3 months ago." One-click opens paper in Knowledge drawer.
  - Past meeting match — "You discussed something similar with Epco on 2025-11-12." One-click shows prior transcript snippet.
  - Idea match — "Your idea #142 connects to what's being said now." One-click opens idea.
  - Project match — "Sounds related to HAT clustering. Flag this minute as a decision point?" One-click drops a timestamped bookmark.
- **Real-time action item detection** runs alongside the retrieval pass. Detected commitments surface as a fifth card type: "I heard a commitment: '...'. Confirm and save?"
- **UX principles:** Sidecar is quiet, non-auditory, non-popping, collapsible. Never interrupts attention. Cards accumulate if ignored; user reviews at meeting end. Collapsing the sidecar with one click hides everything until reopened.
- **Privacy:** Retrieval, embedding, partial transcription are all local. Nothing leaves the device during the recording. Only if the user explicitly consents to cloud summarization at meeting end does any data move off-machine.
- **Persistence:** Card history is saved as part of the meeting record. The full notes view shows a "Live cross-links" section with every card timestamped to the minute it appeared. Users can promote any card to a real link, feeding Coach a self-improvement signal about which cross-links they value.

### 2026-04-10 — Multi-provider architecture (two-tier model)

- **Rationale:** Researchers outside Anthropic's orbit live with ChatGPT Enterprise, Gemini via institutional Google Workspace, or local Ollama setups driven by privacy policies. A second brain that is only Anthropic-facing will be rejected by half its intended audience. At the same time, Metis is deeply designed around Claude (skills, MCP, Cowork, Plan Mode) and pretending all providers are equal would be dishonest. Answer: two-tier honesty.
- **Tier 1 — Native Anthropic surface (recommended default):** Full Metis experience. `/metis`, slash-commands, MCP server, Cowork integration, Plan Mode brainstorm, skill-based document generation, Coach self-improvement, Patterns-as-agents. This is what Metis is *designed around*.
- **Tier 2 — Portable surface (OpenAI, Google, Ollama):** Reduced Metis that still delivers real value. Works via standard mechanisms every provider supports (plain chat, function calling, structured output, JSON mode). The dashboard, patterns, retrieval, backup, CLI all function identically. What doesn't work on Tier 2: MCP slash-commands, Cowork-style orchestration, Plan Mode brainstorm. A researcher using ChatGPT Enterprise can still run the Librarian, do deep research, use Meeting-prep, write documents — just via a different chat UI.
- **Interface:** An internal `LLMProvider` abstract interface with `chat()`, `chat_structured()`, `embed()`. Concrete implementations: `AnthropicProvider`, `OpenAIProvider`, `GoogleProvider`, `OllamaProvider` (local). Agents call patterns; patterns produce messages; messages route through whichever provider the user has selected. Agents never know which provider is active.
- **Settings UX:** Settings → Providers lets the user choose the active provider with a clear notice: "Anthropic is the recommended provider and delivers the full Metis experience. Other providers work but some features are unavailable." Per-agent provider override is allowed (e.g., Librarian on Ollama for confidential content, Writer on Anthropic for quality).
- **Dashboard chat escape hatch:** For Tier 2 users who don't have Claude Desktop, the Thinking tab exposes a launcher button "Chat with Metis via [selected provider]" that opens a web-based chat panel inside the dashboard and routes through their API key. Keeps the Metis workflow available regardless of which client app they have installed.
- **Red-lines apply identically across providers.** Anonymization runs before any cloud call, regardless of whether the cloud is Anthropic, OpenAI, or Google. The policy is provider-agnostic by design.
- **v1 scope:** Ship Anthropic fully. Ship the `LLMProvider` interface and a stub `OpenAIProvider` that proves the boundary works. Do NOT ship full OpenAI/Google/Ollama experiences in v1 — it would split testing effort. Tier 2 is a v1.1 milestone. But the architecture is honest about the boundary from day one, so v1.1 is additive, not a rewrite.

### 2026-04-10 — Tab count revised again: 8 tabs, not 7

Learning is added as its own tab. Rationale: courses are substantial artifacts and learning is a distinct cognitive mode that researchers choose to enter (not a subsection of Metis-about-Metis). The MLM statistics course and future courses deserve first-class space. Final tab list: **Today · Knowledge · Thinking · Planner · Work · Meetings · Learning · Metis**.

### 2026-04-10 — Learning Hub tab

- **Model:** Learning Hub is a **launcher and status aggregator**, not a content container. Courses live in their own folders or on their own servers. The Hub registers links to them and retrieves live status via a standard interface. Course *building* happens in Work as a project type, not in Learning.
- **Spaced repetition:** SM-2 algorithm for v1. Battle-tested, open-source implementations exist, upgrade path to FSRS preserved.
- **Storage (hybrid):** Course metadata + progress cached in SQLite for fast queries; course content lives in its own folders (or on a server) and is owned by the course itself, not by Metis.
- **Launcher row (5 buttons):** Resume learning (opens most recent course in browser at current lesson) · Register a course (form for name/location/cover/tags) · Build a new course (deep-links to Work, creates a Course-type project with the MLM pedagogic pattern pre-loaded) · What connects to my research? (retrieval pass against active projects, returns relevant modules with one-click open) · Ask the Tutor (Chat scoped to selected course).
- **Section 1 — Registered courses grid:** Cards with cover image, type icon, title, live-pulled status (XP, % complete, current module, next lesson, time spent, last accessed), a "Research relevance" chip (green if a module matches an active project), and buttons: Open in browser · View status · Settings.
- **Section 2 — Unified progress timeline:** Calendar heatmap across all registered courses showing study intensity per day. Click a day to see which courses you touched. Streak counter and weekly average at the habit level, not per course.
- **Section 3 — Research-relevance bridge:** List of active projects, each row showing which course modules are relevant (matched via topic similarity), with a "Suggest a study block" button that schedules a 50-minute block in Planner. Turns learning from a side activity into a research-aligned action.
- **Course status interface (two paths, one schema):**
  - *Local-folder courses:* A `metis-course.json` manifest at the course root. Metis reads it on demand. Schema: `name`, `type`, `cover_image`, `pedagogic_tags`, `current_module`, `current_lesson`, `xp`, `time_spent_minutes`, `last_accessed`, `modules[]` (each with name, slug, status, topics), `entry_point_url`. The course's own tooling writes this file whenever progress changes.
  - *Networked courses (ITG LAN / localhost / private VPS):* An HTTP `GET /metis-status` endpoint returning the same JSON schema. Polled with a 2-second timeout, falls back to "offline" if unreachable. Auth via per-course token stored in Metis settings. LAN-only unless the user explicitly trusts an external URL.
- **Manifest refresh strategy:** Filesystem watch on the manifest file (instant updates, event-driven, zero polling cost) with fallback to on-open polling if the watcher isn't available. Networked courses use HTTP polling with a configurable interval (default 5 minutes).
- **Research-relevance matching:** Hybrid — exact-tag matching first (fast, literal: "HAT" in project tags matches "HAT" in module topics), fallback to semantic matching via embeddings (catches "sleeping sickness" ↔ "trypanosomiasis"). Same hybrid approach used in Knowledge search so the code is reused.
- **Course-building cross-tab flow:** "Build a new course" from Learning → deep-links to Work → creates a new Course-type project → invokes the Course-builder agent configured with the **MLM pedagogic principles pattern** (a reusable skill file encoding section length, exercise density, visualization conventions, tone, progression style). When the project ships, user returns to Learning and clicks "Register a course" pointing to the new folder.
- **MLM course migration:** No migration. The MLM course stays in its own folder as it is today. To make it visible in Learning Hub, add a small hook to the MLM course's existing state tracking that writes/updates `metis-course.json` whenever progress changes. Five-lines-of-code work on the course side, zero data movement. The MLM course appears as the first card the moment v1 ships.
- **Future-proofing for LAN hosting:** The HTTP endpoint path handles this transparently. When MLM moves from "static files on your laptop" to "service running on ITG LAN," you update the registered location from a filesystem path to `http://itg-learning.local/mlm/status` in the Hub settings. The rest of the Learning tab behavior is unchanged.
- **Cross-tab contracts:** Learning reads from the course status interface (file or HTTP), Work (active projects for relevance matching), Knowledge (papers linked from course modules if the course emits them). Learning writes to Planner (scheduled study blocks), Thinking (promoted lesson notes become ideas), Today (current course status appears in Morning Brief when study habits slip).

### 2026-04-10 — Metis tab (self-view, memory-centric)

- **Purpose:** The system's self-view. Where trust is built by making Metis transparent about what it's doing, what it's remembering, what it's proposing to learn, and whether everything is healthy. Replaces the old System tab entirely and absorbs scattered observability from Control Room and Library.
- **Launcher row (5 buttons):** Run a health check · Review Coach proposals · Back up now · Restore from backup · Open Metis settings.
- **Band 1 — System health strip:** Six dots (MCP · Database · Retrieval index · Backup age · Red-lines · Token budget this week). Same strip that appears thin on Today is here expanded with per-component diagnostic drawers.
- **Band 2 — Memory & History (the new hero — promoted from a small section to the main surface of the Metis tab):** Five sub-views switched by a top-of-band toggle.

#### Sub-view 1: Sessions
- Lifetime / year / month / week / today counters
- 90-day time-series of sessions per day
- Filters: Surface (MCP / Cowork / Chat / Dashboard / CLI / Scheduled) · Agent · Date range · Has error · Session length · Red-line status
- Sortable table with columns: Timestamp · Session name · Surface · Primary agent · Agents used · Duration · Turns · Tokens in / out · Cost · Red-line status · 1-line summary
- **Click-to-drill session detail drawer** showing: header with "Reopen in [surface]" action · context panel (retrieval passes, memory layers queried, contexts injected, patterns loaded) · full turn-by-turn transcript with per-turn expandable internals (pattern used, model called, per-turn tokens, red-line checks, tool calls) · artifacts produced with links to home tabs · memory impact (before/after on each layer for this session) · export (Markdown / JSON) · redact / delete with red-line-enforced confirmation

#### Sub-view 2: Agents
- Count of registered agents (currently 21)
- Leaderboard of most-used agents over selected period
- Stacked time-series of per-agent invocations
- Agent table: Name · Invocations (total/month/week/today) · Primary-in count · Participated-in count · Total tokens in/out · Total cost · Avg tokens per invocation · Avg duration · Model tier · Red-line incidents · Self-improvement proposals accepted/rejected
- **Click-to-drill agent detail drawer:** recent sessions for this agent · token usage chart · active patterns list (links to Pattern browser) · read-only system prompt with "Propose edit" button (routes through proposal queue) · performance trend chart (override/reject rate over time as honest feedback) · "Run a self-test" button invoking a canned test suite

#### Sub-view 3: Tokens
- Total tokens this week / month / year with EUR cost
- Weekly budget indicator bar (green / amber / red)
- Stacked daily token bars split by agent
- Pie chart by model tier (Haiku / Sonnet / Opus) with cost annotations
- 7-day moving-average cost time-series
- Sortable agent × day table with tokens in, tokens out, cost, invocations (CSV export for expense reports)
- Configurable budget alerts: soft warnings ("this week exceeds 2M tokens") and soft blocks ("stop Opus calls after 20 EUR this week") — all overridable with confirmation, never hard-locked

#### Sub-view 4: Memory Layers
- One card per layer (Episodic · Semantic · Procedural · Working · Reflexive) showing counts, size, last update, compression status, and a "Browse [layer]" drill-in
- *Episodic:* paginated raw transcript list, keyword search
- *Semantic:* concept graph/list, top 20 by reference count, each linking to source episodic entries and current associations
- *Procedural:* learned pattern list with confidence scores, edit/reject/lock per pattern
- *Working:* current working memory contents with "Clear working memory" action
- *Reflexive:* chronological self-summaries (one per session), expandable, searchable
- **Retrieval pipeline status:** active embedding model, reranker, index size, avg retrieval latency (last 100 queries), hit rate
- **Compression cascade status:** last run per layer, what was archived, what was dropped, rationale visible for review
- **Memory settings button:** per-layer retention policies, compression schedules, max capacities, embedding model selection, reranker toggle

#### Sub-view 5: Memory Timeline (new, per decision today)
- A single chronological view interleaving sessions + memory updates + proposals + backups into one narrative stream
- Example render: "2026-04-09 10:15 — session `brainstorm-hat-clustering` ran (Librarian + Brainstorm agent, 14k tokens, 7 turns) · 10:17 — wrote 3 episodic entries, updated 2 semantic concepts (HAT, clustering) · 11:30 — nightly backup completed (OneDrive, ext-drive) · 18:00 — Coach proposed 1 skill edit based on this session"
- Filters: event type · date range · related agent · related project
- Serves "what has been the life of my second brain over the past week/month?" — a single narrative instead of four siloed sub-views
- Click any event to expand to its detail (session → session drawer, memory update → layer browse, proposal → proposal card, backup → backup manifest)

- **Band 3 — Proposal queue:** Coach's weekly proposals (skill improvements, suggested link promotions, news filter adjustments, agent routing changes, pattern edits, dismissal signals). Each proposal has type, rationale, diff view, Approve / Reject with reason / Defer buttons. Weekly batch (Sunday night generation → Monday morning review). Pattern edits by the user also enter this queue (per earlier decision — user reviews their own edits as proposals before they apply; applied edits still commit to git and appear in audit log).
- **Band 4 — Agent activity log:** Chronological stream at call-level granularity (complements the session-level Sessions sub-view). Every `/metis` call, every tool invocation, every agent dispatch. 90-day full detail retention, archived summary beyond. Filters by agent · surface · date · status · session. Red-line columns visible for ethics-board export.
- **Band 5 — Pattern browser:** Searchable list of every pattern (skill) used by every agent, grouped by agent. Each pattern shows name, owning agent, recommended model tier, last modified, "View" button. Clicking opens a Markdown editor. Edits are routed through the proposal queue (user reviews own edits as proposals), applied edits commit to git, rollback available via git revert button. This is the transparency-through-browsability surface — no hidden prompts anywhere in Metis.
- **Cross-tab contract:** Metis tab reads from everywhere, writes only to its own internal state (proposal queue decisions, memory settings, backup configuration). It is a mirror of the rest of the dashboard, not a parallel workspace.

### 2026-04-13 — Rename sweep: "Metis" removed, "PKM" → "RC"

#### "Metis" removal
"Metis" was an earlier name for the routing agent that was replaced by Metis. It survives as stale references in **30 files** and one review folder (`07_outputs/reviews/metis/`). Directive for implementation:

- Delete the folder `07_outputs/reviews/metis/` (its single file is a stale smoke test, not referenced).
- In all 30 files: replace "Metis" / "metis" with "Metis" / "metis" everywhere it refers to the routing agent. Where "Metis" refers to a historical version name in changelogs or session notes, replace with "Metis (formerly Metis)" on first mention in each file, then "Metis" thereafter.
- Key files requiring code-level changes (function names, comments, module references): `07_outputs/apps/metis-dashboard/inst/scripts/seed_projects.R`, `07_outputs/apps/metis-dashboard/inst/scripts/fetch_news_feeds.R`, `07_outputs/apps/metis-dashboard/inst/scripts/cleanup_failed_tasks.R`, `07_outputs/apps/metis-dashboard/check_setup.R`, `01_control-room/handoff-instructions.md`, `01_control-room/implementation-plan-v7.md`.
- All History/session/version files are retrospective documentation — update them with "(formerly Metis)" on first mention but do not rewrite their entire text, they are historical records.

#### "PKM" → "RC" (Research Cortex)
"PKM" (Personal Knowledge Management) appears in **51 files** including deeply embedded locations. The rename scope:

**Code-level renames (critical, must be done atomically to avoid breaking the MCP server):**
- Agent folder: `02_agents/pkm-builder/` → `02_agents/rc-builder/`
- Agent slug in `08_system/agent-registry.json`: `"slug": "pkm-builder"` → `"slug": "rc-builder"` (and all references in `allowed_paths`, routing rules, etc.)
- MCP Python package: `08_system/mcp-server/src/metis_mcp/` — the package name `metis_mcp` is fine (Metis stays as the system name). But internal references to "PKM" in docstrings, variable names, comments in `server.py`, `agents.py`, `projects.py`, `files.py`, `images.py`, `library.py`, `notes.py`, `research.py`, `reviews.py` all become "RC".
- `pyproject.toml` line 4: `"MCP server for the Metis Research Context"` — already says "Research Context" so this is close; change to `"MCP server for the Metis Research Cortex"`.
- `.claude/skills/metis-config/skill.md` — update any "PKM" references to "RC".
- `.claude/hooks/pre-tool-use.mjs` — update any "PKM" references.
- `08_system/security/data-guardian-hook.py` — update references.
- The `.venv/` files (`activate`, `pip`, etc.) contain "PKM" as path fragments from the virtual environment setup — these will self-correct when the venv is rebuilt during installation. Do NOT manually edit venv files.

**Documentation renames (important but non-breaking):**
- `README.md` — all "PKM" → "Research Cortex" or "RC"
- `CLAUDE.md` — all "PKM" → "RC"
- `08_system/SETUP.md`, `08_system/build-history.md`, `08_system/session-log.md`, `08_system/workflows.md`
- `08_system/mcp-server/README.md`, `08_system/mcp-server/run_mcp_server.sh`, `08_system/mcp-server/setup.sh`
- All files in `01_control-room/` — these are implementation plans and session handoffs; update on first mention with "(PKM → now called Research Cortex)" and "RC" thereafter
- All files in `07_outputs/reviews/` — update similarly

**Database column or table names:**
- `metis.sqlite` — run `PRAGMA table_info(...)` on all tables during M0.1. If any column or table name contains "pkm", add an ALTER TABLE rename to the Phase 0 migration script. (The MCP server references like `mcp__metis-pkm__*` tool names are external-facing and may need a deprecation alias → new `mcp__metis-rc__*` names.)

**Guiding principle:** "PKM" is a generic term that makes Metis sound like any note-taking tool. "Research Cortex" is the product name. The rename reinforces the positioning. In all user-facing text, use "Research Cortex" in full on first mention and "RC" after. In code identifiers, use `rc` (lowercase) as the prefix: `rc-builder`, `rc_base_path`, etc.

### 2026-04-13 — Folder structure audit and implementation fitness

#### Current folder tree (annotated with redesign fitness assessment)

```
metis/
├── .claude/                      # Claude Code skills and hooks — KEEP, will expand with patterns
│   ├── hooks/                    # Pre-tool-use hook for red-lines — KEEP
│   └── skills/                   # Agent-specific skill files — KEEP, promote patterns here
├── 00_inbox/                     # Unprocessed incoming items — KEEP as the Dropzone landing zone
├── 01_control-room/              # ⚠️ RESTRUCTURE — see notes below
│   └── memory/                   # Current session/topic/idea memory store — MOVE to new memory system
├── 02_agents/                    # Agent folders with contract.md + skill.md — KEEP, rename pkm-builder
├── 03_domains/                   # Domain knowledge areas — KEEP
├── 04_projects/                  # Active/incubating/someday projects — KEEP
│   ├── active/
│   ├── incubating/
│   └── someday/
├── 05_sources/                   # Raw source material — KEEP
│   ├── code/
│   ├── datasets/
│   ├── literature/
│   ├── meetings/                 # Meeting recordings + transcripts — KEEP, feeds Meetings tab
│   ├── news/
│   └── web-clips/
├── 06_library/                   # Curated knowledge base — KEEP
│   ├── concepts/
│   ├── courses/                  # ⚠️ This is where courses live now; Learning Hub reads from here
│   ├── disease-areas/
│   ├── methods/
│   ├── people-organizations/
│   └── reading-lists/
├── 07_outputs/                   # All produced artifacts — KEEP
│   ├── apps/
│   │   └── metis-dashboard/      # R Shiny dashboard — ⚠️ REPLACE with FastAPI dashboard
│   ├── articles/
│   ├── dashboards/
│   ├── presentations/
│   └── reviews/                  # Per-agent review logs — KEEP, delete metis/ subfolder
├── 08_system/                    # System config, MCP server, security — KEEP, expand heavily
│   ├── logs/
│   ├── mcp-server/               # The MCP Python server — KEEP, this IS the backend
│   ├── ontology/
│   ├── prompts/                  # ⚠️ Should become the patterns/ folder (user-editable prompts)
│   ├── security/
│   ├── templates/
│   └── workflows/
├── 09_archive/                   # Retired items — KEEP
├── metis.sqlite                  # Main database — KEEP, add new tables for memory layers
├── CLAUDE.md                     # Agent routing instructions — KEEP, update
└── README.md                     # Project README — KEEP, update
```

#### What needs to change

**1. `01_control-room/` — obsolete as a folder concept.**
The dashboard's "Control Room" becomes the "Today" tab, which is purely a UI surface, not a filesystem path. The current contents of `01_control-room/` are all planning documents and session handoffs from the early build phase (pre-redesign). They're historical and don't belong in the production folder structure.

**Recommendation:** Rename `01_control-room/` → `01_journal/`. This folder becomes the filesystem backing for the Thinking tab's journal entries, session handoffs, and the reflexive memory layer. The `memory/` subfolder inside it already has `sessions/`, `topics/`, and `ideas/` — that's close to what the Thinking tab needs. The old planning docs (`implementation-plan-v7.md`, `execution-roadmap.md`, `handoff-instructions.md`, etc.) move to `09_archive/planning-history/` since they're superseded by the Section 28 strategy.

**2. `01_journal/memory/` → `01_journal/` directly.**
The extra `memory/` nesting is unnecessary. `01_journal/sessions/`, `01_journal/ideas/`, `01_journal/topics/` should be direct children. Add `01_journal/notes/` and `01_journal/brainstorms/` as new item-type folders for the Thinking tab's frictionless capture.

**3. `07_outputs/apps/metis-dashboard/` — the R Shiny app.**
The Windows distribution strategy already decided to replace R Shiny with FastAPI. The current R code stays as reference during implementation but the new dashboard goes into a new location.

**Recommendation:** Create `07_outputs/apps/rc-dashboard/` as the new FastAPI + Jinja2 (or React) dashboard project folder. Keep `07_outputs/apps/metis-dashboard/` as-is during implementation (reference), move it to `09_archive/metis-dashboard-r-shiny/` when the new dashboard is functional.

**4. `08_system/prompts/` → `08_system/patterns/`.**
This is where user-editable prompt templates live. Renaming to `patterns/` aligns with the Section 28 decision for the Pattern browser in the Metis tab. Each pattern file is Markdown, each is grouped by agent.

**5. New folders needed:**

- `08_system/backup/` — backup configuration, encryption keys (gitignored), destination configs, restore manifests
- `08_system/memory/` — memory layer schemas, compression cascade config, embedding model config. (The actual memory *data* stays in `metis.sqlite`; this folder holds the *configuration* for how memory is processed.)
- `08_system/installer/` — Inno Setup script, embedded Python config, bundled wheels manifest, first-run wizard assets
- `08_system/tests/` — pytest suite, Playwright e2e tests, red-line test fixtures, manual checklist templates
- `07_outputs/apps/rc-dashboard/` — the new FastAPI dashboard (as noted above)

**6. Database changes.**
`metis.sqlite` currently stores sessions, memory entries, and meetings (based on the MCP server tools). The new memory architecture (Section 28, sub-view 4) adds five memory layer tables, a retrieval index metadata table, a compression log table, a proposals table, an agent runs table (for the Agents sub-view), and a token accounting table. These are additive — no existing tables need deletion. Schema migration script goes in `08_system/mcp-server/migrations/`.

**7. No top-level folder rename needed.**
The folder is called `metis/` inside `Research Cortex/`. "Metis" is the system name, "Research Cortex" is the product name. This is fine — the folder holds the Metis engine that powers the Research Cortex. No rename.

#### Summary: the folder structure facilitates the implementation with five adjustments

| # | Change | Risk | When |
|---|--------|------|------|
| 1 | Rename `01_control-room/` → `01_journal/`, flatten `memory/` one level, add `notes/` + `brainstorms/` subfolders, archive old planning docs | Low — only filesystem, no code references except the MCP server's `PKM_BASE` path | Phase 0 (M0.3 — new milestone) |
| 2 | Rename `02_agents/pkm-builder/` → `02_agents/rc-builder/` + update agent-registry.json + all code references | Medium — must be atomic with MCP server code changes | Phase 0 (M0.4) |
| 3 | Create `07_outputs/apps/rc-dashboard/` for the new FastAPI dashboard | Zero — additive only | Phase 1 (M1.2) |
| 4 | Rename `08_system/prompts/` → `08_system/patterns/` | Low — no code references to this folder yet | Phase 0 (M0.5) |
| 5 | Create `08_system/backup/`, `08_system/memory/`, `08_system/installer/`, `08_system/tests/` | Zero — additive only | Phases 5, 7, 11, 12 respectively |

### 2026-04-13 — Per-agent provider routing (multi-AI with Claude as trust anchor)

#### User modes — two options, user chooses in Settings → Providers

**Mode 1 — Claude Only (default).** Every agent, every task, every verification call uses Anthropic models exclusively. Model tier per agent follows `agent-registry.json` (Haiku / Sonnet / Opus). No external API keys needed beyond Anthropic. This is the simplest, most private, and most trusted configuration. Recommended for researchers who have an Anthropic plan and don't want to manage multiple API accounts.

**Mode 2 — Mixed AI (efficiency mode).** Claude remains the orchestrator and trust anchor, but specific agents delegate their bulk work to cheaper or specialized providers (Gemini, OpenAI, Ollama/local). Claude verifies every non-Claude output before it reaches the user or is stored in memory. This mode requires additional API key setup (see below). Recommended for researchers who process high volumes (large libraries, frequent news scans, heavy meeting transcription) and want to cut costs by 50-70%.

The user can switch between modes at any time. Switching to Claude Only from Mixed simply stops routing to external providers — no data loss, no reconfiguration needed. Switching to Mixed from Claude Only requires the one-time provider setup flow.

#### Provider setup flow (first-time Mixed AI configuration)

When the user enables Mixed AI mode for the first time, a guided setup wizard walks them through:

1. **Which providers do you want to use?** Checkboxes for: OpenAI · Google (Gemini) · Local (Ollama). Each has a one-line explanation: "OpenAI — good for text generation, GPT-4o-mini is very cheap" / "Google — good for web search and large-context tasks, Gemini Flash is very cheap" / "Local — free, fully private, requires Ollama installed on your machine."
2. **API key entry.** For each selected provider: a secure input field for the API key, a "Test connection" button that makes a trivial API call to verify the key works, and a green checkmark or red error on result. Keys are stored encrypted in `08_system/security/provider-keys.enc` (AES-256, same encryption as backup keys, decrypted only at runtime, never written to logs or sent externally).
3. **Budget limits per provider.** Optional fields: "Monthly budget for OpenAI: €___" / "Monthly budget for Google: €___". When a provider's budget is exhausted, all agents assigned to that provider automatically fall back to Claude (see fallback chain below). Default: no limit (user can add later in Settings).
4. **Review the routing table.** A summary screen showing which agent uses which provider: "Librarian → Gemini Flash / News Radar → Gemini Flash / Writer draft → GPT-4o-mini / All verification → Claude Haiku / Everything else → Claude Sonnet." The user can adjust any assignment before confirming.
5. **Done.** "You can change any of this in Settings → Providers at any time."

The wizard runs once. After that, provider management lives in Settings → Providers with the same fields, plus a live dashboard showing per-provider token usage and budget remaining.

#### Routing table in agent-registry.json

Each agent entry gains three new fields (only active in Mixed AI mode; ignored in Claude Only mode):

```json
{
  "slug": "librarian",
  "name": "Librarian",
  "primary_provider": "gemini-flash",
  "verification_provider": "anthropic-haiku",
  "fallback_provider": "anthropic-sonnet",
  ...
}
```

- **`primary_provider`** — the model that does the bulk work for this agent. Chosen for cost/speed. In Claude Only mode, this field is ignored and all work goes to the agent's `model_tier` (Haiku/Sonnet/Opus) on Anthropic.
- **`verification_provider`** — always an Anthropic model (Haiku by default). Every response from a non-Claude primary provider passes through this verification call before being stored or shown to the user. The verification prompt checks: red-line compliance, factual coherence with the user's corpus, output format conformance, and a simple "would I be comfortable showing this to the user?" gate. Cost is ~5% of the delegated call (small input: just the output + red-line rules).
- **`fallback_provider`** — used when the primary provider is unavailable (API down, rate-limited, budget exhausted, authentication expired). Always an Anthropic model. Ensures the user never gets a dead agent — if Gemini is down, the Librarian seamlessly falls back to Claude Sonnet and the user sees a small notice: "Librarian is using Claude instead of Gemini (Gemini budget reached). Adjust in Settings → Providers."

#### Fallback chain (critical for uninterrupted experience)

The fallback is automatic and silent except for a small status indicator:

```
primary_provider (e.g. Gemini Flash)
  ↓ if unavailable, rate-limited, auth expired, or budget exhausted
fallback_provider (e.g. Claude Sonnet)
  ↓ if Anthropic is also down (extremely rare)
error message to user: "All providers are currently unavailable. Check Settings → Providers."
```

**Budget exhaustion fallback is the most common case.** When a provider's monthly budget hits the limit, ALL agents assigned to that provider switch to their fallback_provider for the remainder of the month. The user is notified once ("Gemini budget reached for this month. All Gemini agents are now using Claude until [date]. You can increase the budget in Settings → Providers.") and not nagged again. On the first day of the next month, routing automatically resets to primary_provider.

**Authentication expiry fallback.** If an API key expires or is revoked, the agent falls back immediately and the user gets a Settings notification: "Your OpenAI API key is no longer valid. [Fix in Settings]." The agent keeps working on Claude until the key is fixed.

#### Recommended default routing table (for Mixed AI mode)

| Agent | Primary | Verification | Fallback | Rationale |
|-------|---------|-------------|----------|-----------|
| Librarian | Gemini Flash | Haiku | Sonnet | High-volume indexing, classification, "why it matters" notes. Gemini Flash is 10x cheaper than Sonnet for this. |
| News Radar | Gemini Flash | Haiku | Sonnet | Bulk RSS scanning, relevance scoring. Same rationale. |
| Meeting summary | GPT-4o-mini | Haiku | Sonnet | Transcript summarization is a commodity task. GPT-4o-mini is very cheap. |
| Intent extractor | Gemini Flash | Haiku | Haiku | Nightly batch, lightweight NLP, no creativity needed. |
| Writer (draft) | GPT-4o | Haiku | Sonnet | Good prose quality at lower cost than Sonnet for first drafts. |
| Writer (final) | Sonnet | — | Opus | Final pass stays on Claude for quality and trust. No external verification needed. |
| Researcher | Sonnet | — | Opus | Research synthesis is high-judgment work. Stays on Claude. |
| Coach | Sonnet | — | Opus | Self-improvement proposals are trust-critical. Stays on Claude. |
| Metis orchestrator | Sonnet | — | Opus | The routing agent itself always runs on Claude. Non-negotiable. |
| Red-line checker | Haiku | — | Sonnet | Security checks always run on Claude. Non-negotiable. |
| Embeddings | Local (Ollama) | — | Anthropic embed | Free if Ollama is installed. Falls back to Anthropic's embedding API. |
| Brainstorm | Opus | — | Sonnet | Interactive, creative, user-facing. Stays on Claude for quality. |

The user can modify any row in Settings → Providers → Routing table. The table above is the recommended default, pre-populated when Mixed AI mode is enabled.

#### What stays on Claude no matter what (non-negotiable)

Even in Mixed AI mode, four functions NEVER leave Anthropic:
1. **The Metis orchestrator** — routing decisions, session management, memory writes. This is the trust anchor.
2. **Red-line checks** — data protection, anonymization, security verification. These run on Claude because the red-line policy is designed for Claude's behavior. Running them on GPT or Gemini would require re-validating the entire policy.
3. **The verification step** — every non-Claude output is verified by Claude Haiku before storage or display. This is the quality gate that makes Mixed AI trustworthy.
4. **User-facing synthesis** — the final response the user sees in Chat/Cowork always comes from Claude. External models do background work; Claude presents the result.

#### Implementation scope

- **v1:** Ship Claude Only mode fully. Ship the `LLMProvider` interface with `AnthropicProvider` implemented and `OpenAIProvider` + `GoogleProvider` + `OllamaProvider` as stubs that return "not yet configured" errors. The routing table fields exist in `agent-registry.json` but are ignored. The Settings → Providers page shows Mode 1 (Claude Only) as the only active option with a "Mixed AI (coming in v1.1)" toggle that's greyed out.
- **v1.1:** Enable Mixed AI mode. Implement the provider setup wizard, the routing logic in the MCP server, the verification pipeline, the fallback chain, the budget tracking, and the per-provider token accounting in the Metis tab's Tokens sub-view. Add the three stub providers as working implementations. Add the recommended default routing table.
- **v1.2:** Add per-task routing (not just per-agent). Example: the Librarian uses Gemini Flash for bulk classification but Claude Sonnet for the single paper the user is reading right now. This is a refinement of v1.1, not a redesign.

### 2026-04-10 — Today tab amendment: "What Metis has learned about me" card

- A new card on the Today tab, rendered between the Morning Brief hero and the launcher row.
- Weekly refresh (Sunday night during Coach run). 3 bullets max. Examples of tone: "I noticed you read papers in the morning and write in the afternoon." · "Your HAT clustering project has been idle for 6 days — open it?" · "You rejected 3 of my suggested links last week, so I've adjusted the similarity threshold."
- Purpose: externalize Metis's learning in a way the user sees without opening the Metis tab. Trust through visibility. Complements (does not replace) the Metis tab's memory layers view, which is the deep inspection surface.
- Click-through on any bullet opens the relevant Metis tab sub-view scoped to that signal (e.g., "rejected 3 suggested links" → Metis tab → Proposal queue filtered to rejected last week).
- Suppressible: user can collapse the card from Today and it hides until the next Sunday refresh.

---

*This document should be read alongside `windows-distribution-strategy.md` (the how-to-ship story) and `red-lines.md` + `token-guardrails.md` (the existing policy foundations). It proposes changes to the dashboard structure, the MCP pipeline, the database schema, the agent coordination model, and the first-run experience. None of its recommendations are final — they are a starting point for a conversation about what Metis becomes next. Progress against the implementation checklist in section 26 is tracked in `implementation-progress.json` and narrated in `implementation-log.md`.*
