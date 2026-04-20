# Metis — Windows Distribution and Workflow Strategy

*Version 0.1 — Strategic implementation plan for shipping Metis as a frictionless Windows second brain for working researchers.*

---

## 1. Who we are designing for

The person we are designing for is not a developer. She is a forty-year-old epidemiologist at a university institute. She has R installed because her supervisor told her to install it six years ago, and she uses it for the same three analyses she learned in her first post-doc. She has a OneDrive folder called "Documents" that she has never cleaned up. She has seventeen browser tabs open right now and has not closed her laptop in three days. She knows the content of her field deeply. She has never used the terminal. She has never cloned a repository. She once tried to follow an "easy install guide" that said "just run `pip install`" and gave up when it said `pip` was not recognised.

If Metis asks her to edit a JSON file, she will close the browser tab. If Metis asks her to install Python from python.org and tick a box on page three of the installer, she will close the browser tab. If Metis asks her to "open PowerShell as administrator," she will close the browser tab. The only acceptable installation experience is one where she downloads a single file, double-clicks it, clicks Next three times, and then sees a dashboard open in her browser with her name on it.

Everything in this document is written to serve that researcher.

## 2. Guiding principles

Before getting to mechanics, there are seven principles that should govern every architectural choice downstream. They exist because each one corresponds to a way that open-source research tools historically fail their users.

**Ship everything, assume nothing.** The installer must not rely on the researcher having Python, pip, git, R, Rtools, a C compiler, Visual Studio Build Tools, or any other runtime. If Metis needs Python, we ship an embedded Python. If Metis needs SQLite, it is already included. If Metis needs anything else, we either ship it or we do not depend on it. The moment an installer prints "please install X and try again," the researcher is gone.

**Workflow first, feature second.** The Control Room of the dashboard should not be a catalog of Metis features. It should be a catalog of things the researcher wants to do. "Capture an idea." "Review a paper I just read." "Brainstorm my next article." "Prepare for my meeting tomorrow." The researcher arrives at the dashboard with a goal, and the dashboard translates that goal into the right Metis action in the right Claude client. The researcher never needs to know whether the task is best served by a skill, an MCP tool, an agent, or a slash command. The dashboard makes that decision.

**Each Claude surface is routed to on purpose.** Claude Desktop chat, Cowork, and Claude Code are not interchangeable, and pretending they are will hurt the researcher. Each surface has a job. Chat is for conversation and brainstorming. Cowork is for document work and file-centric tasks that a non-technical user can see and touch. Claude Code is for codebase work, multi-file edits, terminal-adjacent tasks, and researchers who want power. The Control Room explicitly sends each workflow to the right one.

**Progressive disclosure.** A new Metis user should be able to get ninety percent of the daily value from the dashboard alone, without ever opening a Claude client. As she matures, the dashboard invites her into the Claude surfaces: "Want to brainstorm this idea? Open it in chat." "Want to edit this article with Metis helping? Open it in Cowork." "Want to refactor this R script? Open it in Claude Code." The learning curve bends gently upward, never vertically.

**Fail soft.** Claude Desktop is not installed yet? Show a card that explains what it is and how to install it. R is not installed and the researcher clicks a workflow that needs R? Offer a one-click R install or fall back to a Python equivalent. Network is offline? News Radar gracefully skips and the rest of the system keeps working. Nothing in Metis should hard-break because of a missing sibling tool.

**Local by default, cloud by exception.** The researcher's papers, ideas, journal entries, and half-finished article drafts never leave her machine unless she explicitly approves each transfer. This is not just a privacy principle — it is also what allows Metis to work on a plane, in a field site in a country with poor connectivity, or on a university network that blocks half the internet. The only network calls Metis makes by default are the Librarian's literature searches and News Radar's RSS fetches, and both are visible, loggable, and disableable.

**Clean uninstall.** The researcher must be able to remove Metis completely from her machine in one click, including the Claude Desktop config entry we added, without leaving orphaned files, processes, or registry keys. If she trusts that removal is clean, she will trust the install more. If she cannot uninstall, she will resent the install.

## 3. Architectural decisions that follow from those principles

The principles above push us toward a specific architecture, which I'll describe here so the rest of the document has a concrete system to reason about.

**One runtime, not two.** The current architecture requires both Python (for the MCP server) and R (for the Shiny dashboard). This is a distribution killer. The FastAPI and Uvicorn packages are already dependencies of the Metis MCP server, which means the infrastructure for serving HTTP from Python already exists. The primary Metis dashboard therefore becomes a **FastAPI web application served from the same process as the MCP server**, with an HTMX or React frontend. R is demoted from "mandatory runtime" to "optional analysis engine" — researchers who have R installed can still use it for statistical work, and the Builder agent can still scaffold Shiny apps for their data, but the core Metis experience runs on Python alone.

**Embedded Python runtime.** Metis ships with Python's official embeddable distribution — a roughly 15-megabyte ZIP that contains a self-contained Python interpreter with no PATH modifications and no system-level install. This runtime lives at `<Metis>/runtime/python/` and is invoked by absolute path from every launcher script. The researcher never installs Python. Her system Python, if any, is untouched. Upgrading Python means replacing the folder. Uninstalling Python means deleting the folder.

**Single process, two faces.** The Metis backend is one long-running Python process. It exposes two interfaces simultaneously: the MCP protocol (for Claude clients to talk to it) and an HTTP API (for the dashboard to talk to it). Both interfaces read and write the same SQLite database, so an idea captured in the dashboard is immediately visible to Claude, and an idea captured through a Claude client is immediately visible in the dashboard. There is no sync layer because there is nothing to sync — everything points at the same rows.

**System tray launcher.** The backend process is launched by a small Windows tray application (built with `pystray` or similar) that lives in the notification area. Its icon is the Metis logo. Right-clicking it gives the researcher Start, Stop, Open Dashboard, Open Metis Folder, Restart, and Quit. The dashboard is not a tab she has to remember to keep open — closing the browser does not kill Metis. This is the same pattern Syncthing, Obsidian Sync, and Jupyter Desktop use, and it is the right pattern here.

**Installer built with Inno Setup.** Inno Setup is a free Windows installer toolkit that has been used by RStudio, Obsidian, and hundreds of other desktop applications researchers already trust. It produces a signed `MetisSetup.exe` that handles everything: choosing an install folder, extracting the embedded Python runtime, creating Start Menu shortcuts, writing the Claude Desktop config, registering an entry in Add/Remove Programs, and providing a proper uninstaller. Inno Setup scripts are plain text, easy to maintain, and can call arbitrary PowerShell or embedded scripts during install for the parts that need logic.

## 4. The installation experience, step by step

This section walks through exactly what the researcher sees, from the moment she clicks the download link on the Metis website to the moment she is using the system productively.

**Step one — download.** She lands on `getmetis.org` (placeholder name) and sees one button: "Download Metis for Windows". She clicks it and receives `MetisSetup.exe`, about forty megabytes. There is no "choose your platform" dropdown, no "which version" choice, no sign-up, no email required.

**Step two — run.** She double-clicks the installer. Windows SmartScreen may complain because the binary is new; this is solved with code signing through a low-cost certificate (around €200/year) so that future builds carry a verified publisher. The installer opens with a welcome screen that says "Metis is your personal research second brain. This installer will set everything up in about two minutes. You do not need Python, R, or any other software." She clicks Next.

**Step three — choose folder.** She is asked where to put her Metis data. The default is `%USERPROFILE%\Metis`, explicitly not inside OneDrive. OneDrive-inside-OneDrive sync conflicts are a real problem, and the default should protect her from them. There is a "choose another location" option for power users. She clicks Next.

**Step four — Claude Desktop detection.** The installer checks whether Claude Desktop is installed by looking at `%LOCALAPPDATA%\AnthropicClaude\` and `%APPDATA%\Claude\`. If it is installed, the screen says "Claude Desktop detected — Metis will connect to it automatically." If not, the screen says "Claude Desktop is not installed. Metis works best with Claude Desktop. Would you like to install it now? (opens browser to claude.ai/download)" with a "Skip for now" option. This is the fail-soft principle in action: the researcher can complete the Metis install without Claude Desktop and add it later.

**Step five — install.** The installer extracts the Metis folder structure, unpacks the embedded Python runtime, creates the initial SQLite database from a schema bundled in the installer, and writes Start Menu shortcuts for "Metis Dashboard", "Metis Setup Wizard", and "Open Metis Folder". It then runs the critical JSON merge step: it reads the existing `claude_desktop_config.json` (creating it if it does not exist), parses it, adds the `metis` MCP server block while preserving any other servers the researcher already has, and writes it back atomically with a `.bak` backup next to the original. This merge is done by a small Python script that ships with the installer, not by hand-crafted regex or string concatenation — JSON editing without a real parser is how config files get corrupted.

**Step six — first run.** On the final installer screen, "Finish" is pre-checked with "Launch Metis now." She clicks it. The Metis tray icon appears in the notification area. Her default browser opens to `http://localhost:3838/welcome`. The welcome page is the first-run wizard — the thirteen sections of `/metis_config` presented as a friendly web form. Her name, her research domain, her main projects, her priority PhD area, her preferred news topics, her RSS feeds, optional API keys for image generation and WhatsApp. Each section has a "Skip for now" button. Total time: five to ten minutes if she fills everything in, or ninety seconds if she clicks through on defaults. At the end of the wizard she lands on the Control Room with her name at the top and a handful of suggested next actions.

**Step seven — she uses it.** From this point forward, Metis is there. She opens the dashboard from the Start Menu or the tray icon. She talks to Metis from Claude Desktop or Claude Code or Cowork, because the MCP server is already wired in. She never touches a config file. She never types a command. She never has to remember anything technical. This is the win condition.

## 5. The runtime architecture in detail

The running Metis system consists of four collaborating components: the embedded Python runtime, the backend process, the SQLite database, and the tray launcher. They work together as follows.

The **embedded Python runtime** lives at `<Metis>/runtime/python/python.exe` and is used as the interpreter for every Metis script. Every launcher, every MCP invocation from Claude Desktop's config, every background job calls this interpreter by absolute path. The `python.exe` on the researcher's system PATH, if any, is never touched.

The **backend process** is a single long-running Python process that runs `uvicorn metis_backend:app` under the embedded runtime. `metis_backend` is a FastAPI application that mounts three routers: one for the dashboard HTTP API (at `/api/*`), one for serving dashboard static assets and HTML (at `/`), and one for the MCP protocol bridge. The MCP protocol normally uses stdio, but it can also be run over HTTP or Unix sockets; for the researcher's machine we expose it on a local TCP port so that the same process serves both the dashboard and the MCP clients. Claude Desktop's config points at a small stub that forwards stdio to the backend's local port.

The **SQLite database** lives at `<Metis>/data/metis.sqlite`. This is the single source of truth for everything: ideas, journal entries, meetings, projects, tasks, tracked files, agent runs, glossary terms, contacts, skill proposals, news items, and the thinking profile. Both the MCP server and the dashboard read and write this database directly. There is no separate sync step because there is no separate store.

The **tray launcher** is a tiny second Python process (also running under the embedded runtime) that shows an icon in the Windows notification area using `pystray`. It spawns the backend process as a child and monitors it, restarting if it crashes. Right-clicking the tray icon gives the researcher direct control: start, stop, restart, open dashboard, open Metis folder, view logs, quit. The tray launcher is the thing that starts when Windows boots (if the researcher opted in during setup).

The advantage of this architecture is that the dashboard and Claude clients are always looking at the same living state. An idea captured in Claude Chat through the MCP server appears on the dashboard the next time she refreshes. An idea typed into the dashboard's Ideas tab is instantly searchable from Claude Code. A task marked complete in Cowork updates the Control Room's task count. There is no "sync" because there is no separation.

## 6. The Control Room as a task launcher

This is the heart of the user experience, and the answer to the question that started this document: *can we put buttons in the Control Room that open Metis in Claude Code, Claude Chat, and Cowork, each labeled with what it is best for?*

The answer is yes, absolutely, and it should be the main organizing principle of the Control Room rather than a side feature. Here is how the Control Room is structured, from top to bottom.

**The greeting strip.** At the top, "Good morning, Stan" with today's date, the weather (optional), and the current PhD week count. This is a small thing but it grounds the researcher: this is her system, personalized for her, not a generic tool.

**The "What's new" panel.** Four cards showing the overnight activity: new papers the Librarian processed, new news items from News Radar, new meeting transcripts ready for review, and new ideas captured from mobile (via WhatsApp if configured). Each card has a count and a "See all" link. The researcher can see in five seconds whether anything requires her attention.

**Today's focus.** A short list (not a bullet list visually — more like a small card grid) of what actually matters today: overdue tasks, the PhD's most urgent action, any in-progress agent runs, and this week's primary goal if one has been set. This is generated by a lightweight scoring function that looks at task deadlines, PLANNING.md recency, and project priorities.

**The task launcher.** This is the central widget. It is a grid of large, clickable cards, each representing a workflow, each labeled with the Claude surface it opens. Here is the proposed card set:

*Capture an idea.* Stays in the dashboard. Opens an Ideas tab modal with a text field. Saves directly via the HTTP API. No Claude client involved. Latency: under one second. Best for: the researcher who just had a thought and needs to record it before it evaporates.

*Brainstorm with Metis.* Opens **Claude Desktop chat**, pre-loaded with the Metis MCP server and with a starter prompt primed. The primer is dropped into her clipboard with a notification saying "Brainstorm prompt copied — paste into Claude." This workaround exists because Claude Desktop does not yet accept external content via a command-line argument; as soon as it does, the paste step goes away. The card's subtitle reads "Chat is best for free-flowing conversation, asking questions, and exploring ideas out loud." Best for: early-stage thinking, vague questions, voice-style interaction.

*Write or edit a document.* Opens **Cowork** with the Metis folder mounted as the workspace. The implementation is a local launch of Claude Desktop followed by a Cowork folder-mount. The subtitle reads "Cowork is best for working on Word documents, presentations, PDFs, and spreadsheets — anything you want Metis to create, edit, or review as a file." Best for: drafting an article, revising a manuscript, making a slide deck, preparing a grant document.

*Review code or build a tool.* Opens **Claude Code** in a Windows Terminal window already cded into the Metis folder (or into a specific project folder if she launched this from a project card). The subtitle reads "Claude Code is best for editing R or Python scripts, reviewing a dashboard, running statistical analyses, or extending Metis itself." Best for: code review, debugging, building new dashboards, working with git.

*Research session.* Opens **Cowork** and drops the researcher into the Research tab equivalent — with her current tracked article pre-opened and the Research Architect agent pre-loaded. The subtitle reads "Best for working on a paper alongside its sources, with Metis tracking what you read and what has changed." Best for: the deep work session where she is writing an article and needs Metis to bring in papers, check her citations, and remember what she decided yesterday.

*Prepare for a meeting.* Stays in the dashboard but opens a Meeting Prep view that pulls from the Contacts table and from recent Meetings. Offers a "Send to Claude Chat" button that builds a briefing prompt. Best for: the twenty minutes before a supervision meeting when she needs to know what was discussed last time and what is outstanding.

*Process the inbox.* Stays in the dashboard. Shows a list of items in `00_inbox/` and a "Process with Librarian" button that triggers the Librarian agent in the background. No Claude client needed — the agent runs inside the backend. The dashboard polls for progress and shows the result. Best for: the morning triage of papers dropped in overnight.

*Journal the day.* Stays in the dashboard. Opens a Journal entry form with a few guided prompts ("What did you learn today? What is on your mind? What should tomorrow's Metis remind you about?"). The Journal agent runs cross-pollination in the background and the next morning the Control Room shows any connections it found. Best for: end-of-day reflection without having to open any Claude client at all.

Each card, in addition to its title and subtitle, has a small icon representing the Claude surface it opens: a speech bubble for Chat, a folder-and-pencil for Cowork, a terminal for Claude Code, or a dashboard glyph for "stays here." This tiny visual hint teaches the researcher, over time, which surface is best for which kind of work, without ever making her read documentation.

## 7. How the launcher buttons actually launch the clients

This is the technical heart of the Control Room, and it deserves explicit treatment because it is what makes the whole strategy feasible or not.

Every launcher button in the dashboard fires a POST request to a local FastAPI endpoint like `/api/launch/chat`, `/api/launch/cowork`, or `/api/launch/code`. The dashboard runs on `localhost:3838`, the researcher is already authenticated by being the one who started the process, and the endpoint has access to the Windows shell, the filesystem, and the researcher's PATH. The backend then launches the appropriate client using a platform-aware strategy.

**Launching Claude Desktop for chat.** The Metis backend looks up Claude Desktop's install path from the registry (`HKEY_CURRENT_USER\Software\AnthropicClaude` or a similar key), or from the known `%LOCALAPPDATA%\AnthropicClaude\` location. It calls `subprocess.Popen([claude_exe])` to launch it. Pre-seeding a conversation is the hard part, because Claude Desktop does not currently accept a prompt via command-line flag. The interim workaround is to write the starter prompt to the Windows clipboard using the `pyperclip` package and show a toast notification in the browser saying "Prompt copied — paste it into Claude." It is slightly less elegant than a deep link, but it is one keyboard shortcut away from the researcher's workflow, and it keeps working on every version of Claude Desktop. If and when Anthropic adds a `claude://chat?prompt=...` URI scheme or a command-line `--prompt` flag, we swap the implementation and the researcher sees a one-step launch. The backend logs which method it used so we can switch as soon as the deep link is available.

**Launching Cowork.** Cowork is a Claude Desktop feature and is invoked from inside the Claude Desktop application. The naive approach is the same as chat: launch Claude Desktop, rely on the researcher clicking Cowork in the sidebar. The more integrated approach, once Claude Desktop supports it, is a URI scheme like `claude://cowork?folder=<path>` that opens Cowork with the folder already mounted. Until that exists, we can help the researcher by copying the folder path to the clipboard and showing a toast: "Folder path copied — open Cowork and paste it in the folder selector." For a first release, this is acceptable; it is one paste away from a working session and does not block shipping. We revisit as Cowork's external integration matures.

**Launching Claude Code.** This is the cleanest of the three because Claude Code runs in a terminal and terminals accept command-line arguments. The backend looks for Windows Terminal (`wt.exe`) first because it is the modern Windows default; failing that, it falls back to `cmd.exe`. It calls `wt.exe -d "<folder path>" claude` (or the equivalent for cmd), which opens a new terminal tab already in the right folder with the `claude` command running. If Claude Code is not installed, the backend detects the absence (no `claude` in PATH and no known install location) and instead opens a helpful page explaining what Claude Code is and how to install it. This fail-soft path is important because many researchers will never install Claude Code, and Metis should not punish them for that.

**Launching nothing at all.** Some workflows — capture an idea, journal the day, process the inbox — should stay entirely inside the dashboard. The launcher for these workflows is not a "launcher" at all; it is a UI action that calls the HTTP API directly and shows the result inline. This is the path we want most daily interactions to take, because it is fastest and requires nothing except the browser tab.

## 8. Workflow-by-workflow mapping

This is where the abstract strategy meets concrete researcher behavior. For each of the eleven canonical Metis workflows, I want to say explicitly: what is the researcher trying to do, which Claude surface is best, how the Control Room routes her there, and what context is passed.

**Workflow one — Morning start.** The researcher opens her laptop with coffee in hand. She clicks the Metis icon in the tray, the dashboard opens to the Control Room, and the "What's new" panel shows her overnight activity: three new papers the Librarian processed, a news briefing from News Radar, one meeting transcript ready for her review, and no new ideas from mobile. This entire workflow is dashboard-only. She might spend five minutes here without ever opening a Claude client. The Librarian and News Radar ran as scheduled background tasks (configured during first-run or via `/schedule`) without any interaction. This is the canonical "stay in the dashboard" workflow, and it should feel like reading the newspaper.

**Workflow two — Idea capture (desktop).** She is reading a paper and has a thought. She clicks the Metis tray icon, "Capture an idea," types one sentence, hits Enter. The idea is saved immediately. In the background, the `cross_pollinate` function runs against her library, her meetings, and her open projects, and any connections it finds are queued for her next dashboard visit. No Claude client is involved. Latency is sub-second, which is crucial because ideas evaporate in the time it takes to open an application. If she wants to expand on the idea, the saved idea has a "Brainstorm this" button that opens Claude Chat with the idea as context.

**Workflow three — Idea capture (mobile).** She is walking to the coffee machine and an idea hits her. She opens WhatsApp, sends a message to her Metis bot, which is powered by the Twilio integration in the MCP server's FastAPI layer. The idea is saved to the database. Next time she opens the dashboard, it appears in the Ideas tab with a "Mobile" badge. This workflow requires no laptop at all, which is the point.

**Workflow four — Brainstorm session.** She has an idea she wants to develop. She clicks "Brainstorm with Metis" on an idea card. The dashboard copies a brainstorm prompt to her clipboard that includes the idea text, relevant papers from her library, recent meeting notes on related topics, and her active projects. Claude Desktop opens. She pastes the prompt into a new conversation and starts talking. Claude has the Metis MCP server attached, so during the conversation it can call `search_literature`, `get_research_context`, `capture_idea`, or any other Metis tool — all of which read and write the same database that the dashboard sees. When the conversation is productive, she tells Metis "save this thread as a note on idea X" and the MCP server's `add_journal_entry` tool writes the result back. The dashboard picks it up next refresh.

**Workflow five — Research session.** She is working on Article 1 of her PhD. She opens the dashboard, goes to Projects, clicks the Article 1 card, and clicks "Open in Cowork." The backend launches Claude Desktop (or prompts her to open Cowork and paste a folder path). Cowork mounts the article folder. Inside Cowork, the docx skill is available, the Metis MCP server is attached, and the Research Architect and Writing Partner agents can be invoked directly. She can say "read my current draft and tell me what's weak," and Cowork opens the `.docx` using the docx skill, reads it, and Writing Partner responds. When she makes edits in Cowork, they save directly to the file — no manual file juggling.

**Workflow six — Literature intake.** She drops a PDF into the `00_inbox/` folder, which is just a folder on her disk, watched by the backend. The Librarian agent processes it in the background: extracts metadata, runs an LLM pass for tags and a summary, moves it into `05_sources/literature/...`, and logs the processing to `agent_runs`. The dashboard shows "1 new paper processed" next time it refreshes, with a link to the summary and the paper itself. No Claude client needed. The researcher can optionally click "Ask Metis about this paper" which opens Claude Chat with the paper's summary as context.

**Workflow seven — Meeting.** The researcher records her supervision meeting on her phone or laptop. She drops the audio file into the dashboard's Meetings tab via drag-and-drop. The backend runs Whisper transcription and optionally speaker diarization. The Meeting Memory agent then analyzes the transcript and produces a structured note with action items, attendees, decisions, and open questions. This all happens in the background; the researcher gets a notification when done. She can open the structured note in the dashboard directly, or click "Open in Chat" to discuss it with Metis further.

**Workflow eight — Project work.** She needs to update her HAT Dashboard's R code. From the Projects tab, she clicks "Open in Claude Code." The backend opens Windows Terminal in the project folder with `claude` already running. From inside Claude Code, all Metis skills and MCP tools are available because the `.claude/skills/` folder is present in the project. She works on the code, commits changes, and the Software Engineer agent has full context on what she is trying to do.

**Workflow nine — Deep query and routing.** She has a quick question: "What did that recent preprint say about IHI calculation?" From the Control Room she clicks "Ask Metis" which opens Claude Chat with the Metis MCP attached. She types her question. Claude calls `search_literature` under the hood and answers. If the question turns into a longer conversation, it organically becomes a brainstorm; if it was really a one-shot, she gets her answer in twenty seconds and closes the tab.

**Workflow ten — End-of-day journal.** At 6pm she clicks "Journal the day" on the Control Room. A form appears with three prompts: what went well, what is on her mind, what should tomorrow remind her about. She types a short entry. The Journal agent cross-pollinates the entry against her ideas, recent meetings, and recent research activity, and any connections it finds appear on tomorrow's Control Room as "Yesterday's journal connected to..." This workflow is dashboard-only, under two minutes, and the compounding value over months is enormous.

**Workflow eleven — Build or extend Metis.** She wants to add a new agent, or modify an existing one, or scaffold a new dashboard tab. She clicks "Extend Metis" on the System tab, which opens Claude Code in the Metis folder itself. The PKM Builder agent is pre-loaded. She can describe the change she wants, and Claude Code implements it with full filesystem access. This workflow is explicitly for the more technical researchers or for the researcher once she has matured into a power user. Most researchers never touch it; that is fine.

## 9. Cross-client context sharing

A central property of this architecture is that context — what the researcher has told Metis, what Metis has done for her, what she is working on right now — flows freely between the dashboard, Claude Chat, Cowork, and Claude Code. This is not an accident; it is engineered.

The flow works like this. Every Metis client (dashboard, MCP, Claude Code with skills) reads and writes to the same SQLite database. The database schema includes an `active_context` table that tracks what the researcher is currently focused on: which project, which article, which idea, which meeting, which experiment. Whenever she interacts with Metis in any client, the context is updated. Whenever she opens any client, Metis loads the current context and presents it as the starting point.

Concretely, when she clicks "Brainstorm with Metis" from an idea card, the dashboard writes `active_context = { focus: 'idea', id: 42 }` to the database before launching Claude. When Claude Chat opens and calls `get_research_context`, the MCP server reads the active context and returns the idea, plus its cross-pollination matches, plus the relevant papers. Claude Chat starts the conversation already knowing what she is thinking about. When she switches to Cowork an hour later to draft the idea into a document, Cowork's first action via the MCP is to read the same active context and pick up where chat left off.

This is the kind of continuity that makes Metis feel like a second brain rather than a collection of tools. It is also surprisingly simple to implement because it rides on the single-source-of-truth database we already have.

## 10. Client-specific setup requirements

Here is what each Claude client needs from the installer and from the researcher, so that the Control Room buttons work reliably.

**Claude Desktop chat.** The installer writes the `metis` entry into `claude_desktop_config.json`, which is all that is needed for the MCP server to be available in any chat conversation. The researcher does not need to install Python, configure anything, or even understand what an MCP server is. She just opens Claude and starts talking, and Metis is there. The only step she might notice is that she has to fully quit and relaunch Claude Desktop once after install for the new MCP server to be picked up — the installer can trigger this automatically with her permission.

**Cowork.** Cowork discovers skills from the mounted folder's `.claude/skills/` directory. The Metis folder already has this directory populated with all the Metis skills (`/metis`, `/librarian`, `/metis_ideas`, etc.). When the researcher opens Cowork via a launcher button and mounts the Metis folder, every Metis skill becomes available as `/name` commands. The Control Room's launcher buttons will always mount the Metis folder itself (or a relevant subfolder like a specific project) so that the skills are always accessible. For researchers who mount parent folders by hand, we can provide a small "Fix this" wizard that detects the problem and offers to copy or symlink the skills up.

**Claude Code.** Claude Code reads skills from `.claude/skills/` in the current working directory, so the launcher buttons always open terminals pre-cded into the right folder. Additionally, Claude Code respects the `CLAUDE.md` file in the folder, which in Metis's case contains the agent routing guide — so the moment Claude Code opens in the Metis folder, it already knows how to route requests through Metis. The installer should also optionally install Claude Code for the researcher if she wants, by running the one-line install command and adding it to her PATH.

## 11. The first-run wizard in detail

The first-run wizard is the single most important piece of software we ship, because it is where the researcher's perception of Metis is formed. It must feel friendly, fast, and genuinely personalized — not bureaucratic.

The wizard runs as a series of web pages served from the backend at `http://localhost:3838/welcome`. It is structured as thirteen short sections, each of which has a "Skip for now" button so the researcher can get to a working Metis in under two minutes if she wants. The sections are: your name and role; your research domain; your priority project; your other active projects; your PhD status (optional); your literature sources (pre-populated with sensible defaults like PubMed and WHO); your news topics; your RSS feeds; your preferred agent team (pre-populated with all enabled); your data protection preferences (with patient data blocked by default); optional API keys for image generation and mobile capture; your Claude Desktop connection (auto-detected); and a final "Ready to go" confirmation.

Each section is a single web form. No jargon. Each field has a plain-language explanation. Where a researcher might reasonably not know the answer, there is a "What does this mean?" link. Where a field is optional, it is clearly marked optional. The wizard writes to `08_system/user-config.yaml` at the end, which is the same file `/metis_config` produces, so the wizard and the CLI command are interchangeable and the researcher can re-run the wizard any time to reconfigure.

At the end of the wizard, the researcher lands on the Control Room with a small "First steps" tutorial overlay that highlights the three most important things: the "What's new" panel, the task launcher, and the tray icon. The tutorial can be dismissed in one click.

## 12. Update and maintenance story

Metis needs to update itself gracefully over time. The strategy is as follows. The tray launcher, on startup, checks for a new version by calling a lightweight endpoint on the Metis website (`getmetis.org/version.json`). If a new version is available, the researcher sees a gentle "Metis update available" notification in the tray, never blocking her work. Clicking it opens an updater that downloads the new `MetisSetup.exe`, runs it, and the installer detects the existing install and performs an in-place upgrade — preserving her database, her config, her ideas, her papers. The upgrade process explicitly never touches `data/metis.sqlite` or her content folders.

The database schema is migrated on startup using a lightweight migration system (like `yoyo-migrations` or a custom versioning script), so that new versions of the backend can add columns, create tables, or rename fields without the researcher having to do anything. Failed migrations roll back and the backend refuses to start, showing a clear error message — this is the one place where failing loud is better than failing silent.

## 13. Fallback paths when things are missing

Metis must behave well when sibling tools are missing. Here are the degraded modes.

If Claude Desktop is not installed, the task launcher shows a card explaining what Claude Desktop is, a "Download Claude Desktop" button, and disables the launcher buttons that require it (with a tooltip "Requires Claude Desktop"). The dashboard-only workflows continue to work perfectly. The researcher can use Metis every day without ever installing Claude Desktop if she wants to — though she would be missing the conversational layer.

If Claude Code is not installed, the "Review code" launcher button is replaced with "Install Claude Code (takes 2 minutes)". Clicking it walks her through the install without requiring her to touch a terminal.

If R is not installed, all R-based features (optional statistical analyses, Shiny scaffolding via the Builder agent) show a "R not detected" banner with an "Install R" button that opens the CRAN download page. The rest of Metis works without R.

If the network is down, News Radar and Librarian's external searches show "Offline — will retry when network returns" rather than failing. All local operations continue. Ideas, journal entries, meetings, writing, and the dashboard itself work completely offline.

If the embedded Python runtime is corrupted, the tray launcher detects that `python.exe` cannot start, and offers a one-click "Repair Metis" option that redownloads the runtime.

## 14. Success metrics

How will we know this strategy is working? Four metrics matter.

First, **install-to-first-idea time**. The median researcher should go from double-clicking `MetisSetup.exe` to capturing her first idea in under ten minutes. If that number is higher, the wizard or the install is too long.

Second, **weekly active dashboard visits**. If researchers visit the Control Room at least three times a week in the first month, Metis has become part of their routine. If they visit once and never come back, the Control Room is not giving them enough reason to return.

Third, **Claude client launch rate**. If at least 50% of dashboard sessions result in clicking one of the launcher buttons to open a Claude surface, the workflow routing is working. If researchers never click the launcher buttons, they either do not understand them or they are using another workflow — and we need to find out which.

Fourth, **uninstall rate**. If more than 10% of installs are uninstalled within the first two weeks, we are failing someone at a specific point in the onboarding. We should instrument the uninstaller (with explicit consent) to ask a single optional question: "What made you uninstall?"

None of these metrics require invasive telemetry. They can all be collected locally and, if the researcher opts in, reported anonymously.

## 15. Implementation sequencing

If I were building this from the current Metis codebase, here is the order I would tackle it in, because each phase is independently shippable and each one removes a real blocker.

**Phase 1 — Python-only dashboard MVP.** Build a minimal FastAPI dashboard that serves the Control Room and three tabs: Ideas, Meetings, Planning. It reads from the existing SQLite database. It does not have launcher buttons yet. The goal is to prove we can replace the Shiny dashboard with a Python dashboard without losing any data. Time estimate: two to three weeks.

**Phase 2 — Embedded Python + Inno Setup installer.** Build the installer: embedded Python runtime, folder extraction, Claude Desktop config JSON merger, Start Menu shortcuts, basic uninstaller. At the end of Phase 2 a researcher can download `MetisSetup.exe` and end up with a working Metis MCP server in Claude Desktop. No dashboard yet. Time estimate: two weeks.

**Phase 3 — Tray launcher and full dashboard.** Build the pystray tray launcher that runs the backend process. Expand the dashboard to cover all remaining tabs. Add the "What's new" panel and Today's focus. Time estimate: three weeks.

**Phase 4 — Task launcher buttons.** Implement the launcher API endpoints (`/api/launch/chat`, `/api/launch/cowork`, `/api/launch/code`). Wire up the Control Room launcher cards. Implement the clipboard-based prompt pre-seeding for Chat. Implement `wt.exe` launching for Claude Code. Time estimate: two weeks.

**Phase 5 — First-run wizard.** Convert the thirteen sections of `/metis_config` into a web form wizard served from the backend. Polish. Time estimate: one to two weeks.

**Phase 6 — Update system, uninstaller polish, fallback paths.** Add the version checker, the in-place upgrade path, the graceful handling of missing Claude Desktop, missing Claude Code, missing R, missing network. Time estimate: two weeks.

**Phase 7 — Signing, distribution site, documentation.** Code-sign the installer. Set up `getmetis.org` with a single download button and a short "what is Metis" page aimed at researchers. Write the getting-started guide in plain language. Time estimate: two weeks.

Total time estimate: twelve to fifteen weeks to a shippable Windows release that a non-technical researcher can install, use, and love.

## 16. Closing reflection

Everything in this document exists to serve one sentence: *a researcher can offload her brain to Metis and come back to it when she wants to be productive.* The installer is in service of that sentence. The embedded Python runtime is in service of that sentence. The FastAPI dashboard is in service of that sentence. The launcher buttons that route her to the right Claude surface are in service of that sentence. The thirteen-section wizard is in service of that sentence.

The technical decisions in this document are reversible. We can change the installer tool, the runtime, the dashboard framework, the MCP transport, the tray library. What is not reversible is the principle: the researcher is the hero, and every architectural choice is judged by whether it makes her life easier or harder. When there is a choice between "elegant for us" and "frictionless for her," we pick frictionless for her. When there is a choice between "correct technically" and "obvious to her," we pick obvious to her. When there is a choice between "powerful" and "discoverable," we pick discoverable first and powerful later.

The Control Room, with its task launcher, is the single most important piece of UI in Metis because it is the place where the researcher's intention meets the machinery of the system. If the Control Room answers the question "what do you want to do right now?" correctly, and then gets her to the right tool with one click, Metis has delivered on the promise. Everything else is plumbing.

---

*This document should be revisited at the end of each implementation phase and updated based on what we learn from real researchers using real builds. Strategy is hypothesis; contact with users is evidence.*
