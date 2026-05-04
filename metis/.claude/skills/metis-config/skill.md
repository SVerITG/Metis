---
name: Metis Config
description: "metis config, setup metis, configure metis, first time setup, onboard, reconfigure, setup wizard, initial configuration, personalise metis, set up agents"
model: claude-sonnet-4-6
effort: thorough
complexity: chain
---

## Purpose

This is the Metis setup wizard. It configures the entire system to the user's context, projects, and preferences. It can be run at any time — for first-time setup, to reconfigure, or to add new context.

**This wizard is specifically designed for first-time users who have never used a CLI or Claude Code.** Every step must include plain-English explanations, analogies where helpful, and reassurance. Never assume prior knowledge of AI, MCP, or RC concepts.

---

## Opening message

Show this before any questions:

> "Welcome to Metis setup. I'm going to ask you a series of questions so I can configure your personal knowledge assistant exactly the way you work. This will take about 10–15 minutes. You can stop and resume at any time — your answers are saved as you go. Nothing will be changed on your system until you confirm at the end."

Read `08_system/user-config.yaml` if it exists — pre-fill answers where already set, and show them to the user so they can update or confirm.

---

## Section 0 — Environment Check (always run first)

**Show this explanation before running anything:**
> "Before we configure Metis, I need to check that the software it depends on is installed on your machine. This is a one-time check. I'll tell you exactly what to install if anything is missing — you don't need to know what any of it is, just follow the steps I give you."

Run the following checks in order. **Stop and give the user clear instructions if any check fails — do not proceed to the next section until the issue is resolved.**

---

### 0.1 — Check R

Run in bash:
```bash
Rscript --version 2>/dev/null || echo "NOT FOUND"
```

**If NOT FOUND:**
> "R is the statistical software that powers the Metis dashboard. You need to install it before anything else will work.
>
> 1. Go to **https://cran.r-project.org/** and click 'Download R for Windows'
> 2. Click the first link ('install R for the first time')
> 3. Download and run the installer — accept all defaults
> 4. When it finishes, come back here and type 'done'"
>
> After they confirm, re-run the check. If still not found, check that R is in `C:\Program Files\R\` and that `Rscript.exe` exists there.

**If found:** note the version. If below 4.3, recommend updating (same link above).

---

### 0.2 — Check RStudio

Check if RStudio exists:
```bash
ls "/mnt/c/Program Files/RStudio/bin/rstudio.exe" 2>/dev/null || \
ls "/mnt/c/Program Files/Posit/RStudio/bin/rstudio.exe" 2>/dev/null || \
echo "NOT FOUND"
```

**If NOT FOUND:**
> "RStudio is the editor that makes working with R much easier. It's free.
>
> 1. Go to **https://posit.co/download/rstudio-desktop/**
> 2. Click 'Download RStudio Desktop' (the free version)
> 3. Run the installer — accept all defaults
> 4. Come back here and type 'done'"

**If found:** confirm with a checkmark, continue.

---

### 0.3 — Install R packages

**Show this explanation:**
> "Metis's dashboard is built in R and needs several add-on packages to run. I'm going to install them now. This takes about 5–10 minutes and only needs to happen once."

Find the Rscript path:
```bash
RSCRIPT=$(for d in /mnt/c/Program\ Files/R/R-*/bin; do echo "$d/Rscript.exe"; done | tail -1)
echo $RSCRIPT
```

Run the package installation:
```bash
"$RSCRIPT" -e "
  pkgs <- c(
    'shiny', 'bslib', 'shinyBS',
    'DBI', 'RSQLite',
    'dplyr', 'tidyr', 'lubridate',
    'plotly', 'ggplot2',
    'httr', 'rvest', 'jsonlite', 'xml2',
    'DT', 'htmltools', 'visNetwork'
  )
  missing <- pkgs[!pkgs %in% installed.packages()[,'Package']]
  if (length(missing) == 0) {
    cat('All packages already installed.\n')
  } else {
    cat('Installing:', paste(missing, collapse=', '), '\n')
    install.packages(missing, repos='https://cloud.r-project.org/')
    cat('Done.\n')
  }
"
```

Show the user the output as it runs. If any package fails to install, note it and continue — non-critical packages can be added later.

After completion, tell the user:
> "R packages are installed. This won't need to happen again on this machine."

---

### 0.4 — Check Python

```bash
python3 --version 2>/dev/null || python --version 2>/dev/null || echo "NOT FOUND"
```

**If NOT FOUND:**
> "Python is needed for Metis's background intelligence layer (the MCP server that connects Claude to your data).
>
> 1. Go to **https://www.python.org/downloads/**
> 2. Click 'Download Python 3.12.x' (the yellow button)
> 3. Run the installer — **tick 'Add python.exe to PATH'** before clicking Install
> 4. Come back here and type 'done'"

**If found:** confirm version. If below 3.10, recommend update.

---

### 0.5 — Check WSL (Windows Subsystem for Linux)

```bash
wsl --version 2>/dev/null || echo "NOT FOUND"
```

**If NOT FOUND:**
> "WSL (Windows Subsystem for Linux) is needed for Metis's MCP server. It's a built-in Windows feature.
>
> 1. Open the **Start Menu**, search for **PowerShell**, right-click it, choose **'Run as administrator'**
> 2. Type this command and press Enter:
>    ```
>    wsl --install
>    ```
> 3. Wait for it to finish, then **restart your computer**
> 4. After restart, open the Start Menu and search for **Ubuntu** — let it finish its first-time setup (creates a username and password)
> 5. Come back here and type 'done'"

**If found:** confirm, continue.

---

### 0.6 — Check Claude Desktop

```bash
ls "/mnt/c/Users/$(whoami)/AppData/Local/AnthropicClaude/claude.exe" 2>/dev/null || \
ls "/mnt/c/Users/$(whoami)/AppData/Local/Programs/claude/claude.exe" 2>/dev/null || \
echo "NOT FOUND"
```

**If NOT FOUND:**
> "Claude Desktop is the AI interface you'll use to talk to Metis. You're probably using it already, but let me check.
>
> 1. Go to **https://claude.ai/download**
> 2. Click 'Download for Windows'
> 3. Run the installer
> 4. Sign in with your Anthropic account
> 5. Come back here and type 'done'"

---

### 0.7 — Summary of environment check

After all checks pass, show:
```
✓ R [version] — installed
✓ RStudio — installed
✓ R packages — all installed
✓ Python [version] — installed
✓ WSL — installed
✓ Claude Desktop — installed
```

Then say:
> "Your environment is ready. Now let's configure Metis for the way you work."

Proceed to Section 1.

---

## Section 1 — Identity

**Show this explanation first:**
> "This becomes context for all of Metis's agents. When Metis or any specialist agent works on a task, they will know who they are working for and what matters to you. Think of it as writing a one-paragraph bio for your AI team."

**Ask:** "Tell me about yourself: your role, your area of expertise, and the research or work domain you operate in."

After they answer, also ask: "What language do you primarily work in? (English, French, Dutch, etc.)"

**Show after they answer:**
> "Your general context is always active. You can add specialist contexts later as your work evolves — for example if you start developing dashboards as a side project, you can add 'Epidemiological dashboard development' as a specialist context and Metis will include it when routing relevant tasks."

**Output block in user-config.yaml:**
```yaml
user:
  name: ""
  role: ""
  general_context: ""
  language: ""
  specialist_contexts: []
  active_contexts: ["general"]
```

---

## Section 2 — Your projects (staging folder scan)

**Ask:** "Do you have a folder where you keep your important working documents — articles, scripts, notes, guidelines? If yes, what is the path?"

**Show this explanation:**
> "Metis can scan this folder and help you organise it into your RC. Don't worry — nothing will be moved or deleted without your confirmation."

If they provide a path:
- List the top-level subfolders
- For each subfolder, ask: "Is '[folder_name]' a project? If yes, what does it do in one sentence?"
- For each confirmed project, create a project entry: `name`, `description`, `launcher_type` (infer from file types found), `path`

If no staging folder: "No problem — you can point Metis to folders later from the Projects tab."

For each confirmed project, insert a row into the `projects` SQLite table at `07_outputs/apps/metis-dashboard/data/metis.sqlite`.

---

## Section 3 — News Radar interests

**Show this explanation:**
> "News Radar runs every morning at 7am and compiles a briefing on the topics you care about. It pulls from RSS feeds, academic preprint servers, and news sources. You can always add or remove topics later.
>
> Important: these same topics also feed the **New publications alert** — every morning, the Librarian scans for newly published academic articles matching these topics and adds them to your notification queue in the Library tab and Control Room. So the topics you set here do double duty: morning news briefing AND literature monitoring."

**Ask:** "What topics should your News Radar follow? (e.g., your research domain, public health surveillance, AI developments)"

**Follow-up:** "Do you have any specific RSS feeds or websites you want to include? (optional — just paste URLs)"

**Output in user-config.yaml:**
```yaml
news_radar:
  topics: []
  rss_feeds: []
  scan_interval: "daily_morning"
```

Also insert each topic as a row in the `user_topics` SQLite table.

---

## Section 4 — Data protection level

**Show this explanation first:**
> "Metis handles your personal research, documents, and notes. You can choose how tightly it controls what leaves your machine and goes to the internet (including to AI APIs). Here are the options:"

Present as a numbered menu:
```
1. Light      — Metis works freely. No prompts for confirmation before sending
               content to AI. You trust the system to handle data sensibly.

2. Standard   — Metis warns you when personal or potentially sensitive content
               is about to be sent externally, and asks for confirmation.
               (Recommended for most users)

3. Strict     — Metis asks for explicit permission before every outbound call.
               More interruptions, maximum control.

4. Very tight — Everything is logged and gated. No content leaves your machine
               without your explicit approval. Metis will explain exactly what
               it intends to send before every action.
               (Best for sensitive research contexts)
```

**Output in user-config.yaml:**
```yaml
data_protection:
  level: "standard"   # light | standard | strict | very_tight
```

---

## Section 5 — Cybersecurity level

**Show this explanation:**
> "Metis agents can browse the web, fetch articles, and pull news feeds. Cybersecurity controls how carefully those external connections are validated."

Present the same 1–4 scale as Section 4, adapted for internet-facing operations (not data classification). Default: standard.

**Output in user-config.yaml:**
```yaml
cybersecurity:
  level: "standard"
```

---

## Section 6 — RC structure walkthrough

**Show this explanation:**
> "Metis organises your knowledge into a specific folder structure. Here's a quick tour:"

Walk through each folder with a plain-English one-sentence explanation:
- `00_inbox/` — "Drop anything here. Metis's Librarian will process it automatically each morning."
- `01_capture/` — "Rough notes, quick ideas, voice transcripts — raw material before it's organised."
- `02_agents/` — "Metis's team lives here. Each agent has a skill file that defines how they think."
- `03_domains/` — "Your knowledge domains — research areas, projects, interests. Think of these as your filing cabinet."
- `05_sources/` — "Processed papers, books, references — everything the Librarian has catalogued."
- `07_outputs/` — "Everything Metis produces: reviews, reports, session outputs, your dashboard."
- `08_system/` — "Metis's configuration and rules. Normally you won't need to touch this."

Also explain: "The Dropzone tab in the dashboard is a visual inbox — drag files there and the Librarian picks them up."

**Ask:** "Does this structure make sense for how you work? Any folders you'd like to rename or reorder?"

If they want customisations, write overrides to `user-config.yaml` under a `folder_overrides:` key. Do not rename the actual folders without explicit confirmation.

---

## Section 7 — Meet your team

**Show this explanation:**
> "Metis is not a single AI — it is a team. Metis is the team leader: she receives your requests, decides which specialist to call, and assembles the final answer."

Present each agent with a plain-English two-sentence description:

- **Metis** (team lead) — routes requests, coordinates agents, maintains context. Your default entry point for everything.
- **Librarian** — processes papers, catalogues literature, answers "what have I read about X?"
- **Research Architect** — tracks your research progress, article drafts, methodology questions.
- **Writing Partner** — helps draft, edit, and improve written work.
- **News Radar** — compiles your morning briefing from topics and feeds you specify.
- **Meeting Memory** — transcribes and analyses meetings, surfaces connections to your knowledge.
- **Methods Coach** — epidemiological methods, statistics, sampling, R methodology.
- **Epidemiologist** — domain specialist; challenges your study design and assumptions.
- **Learning Coach** — tracks your courses and skills, identifies gaps.
- **Career Coach** — reflects on career direction, opportunities, and development.
- **Presentation Maker** — builds slide decks from your content and ideas.
- **Data Guardian** — silently protects your data; intervenes before anything sensitive leaves your machine.
- **Cybersecurity** — validates every internet-facing action before it happens.
- **RC Builder** — builds and extends Metis itself; the agent to call when you want a new feature.
- **HR/Talent Spotter** — identifies when a new specialist agent is needed.
- **Educational Expert** — ensures any course content you create follows consistent standards.

**Explain about self-improvement (feature prominently):**
> "This is one of Metis's most important features: **agents learn from your feedback and propose their own improvements — but you always approve.** After completing tasks, each agent writes a brief self-critique. When you rate an output poorly or flag an issue, the relevant agent reads its own skill file and the failed output, then proposes a specific change. That proposal sits in a queue until you review and approve it. No agent can rewrite itself without your permission. This keeps Metis improving without losing your trust."

No output needed for this section — it is informational only.

---

## Section 8 — Librarian configuration

**Show this explanation:**
> "Your Librarian automatically processes papers and documents you drop into the inbox. She catalogues them, extracts key concepts, and makes them searchable. If she needs you to download a paper manually, she will tell you exactly what to fetch and where to put it."

**Ask 1:** "Are there specific journals, authors, or topics the Librarian should actively look for?" (optional)

**Ask 2:** "How often should the Librarian scan your inbox?"
```
1. Every morning at 7:30am (default — recommended)
2. Every 2 hours
3. Manually only — I'll trigger it myself from the dashboard
```

**Output in user-config.yaml:**
```yaml
librarian:
  active_search: []    # journals, authors, or topics to actively monitor
  scan_interval: "daily_morning"   # daily_morning | every_2h | manual
```

---

## Section 9 — News Radar scan interval

(Skip if already answered in Section 3.)

**Ask:** "How often should News Radar run?"
```
1. Every morning at 7am (default)
2. Twice daily — 7am and 5pm
3. Manually only
```

**Output:** updates `news_radar.scan_interval` in user-config.yaml.

---

## Section 10 — Dashboard tour and tab questions

**Show this explanation:**
> "Your Metis dashboard has 10 tabs. Let me explain each one and ask a quick question about how you work."

For each tab, show the name + one sentence explanation + ask the question below:

- **Control Room** — "Your morning hub: overnight agent summary, morning briefing, quick-launch buttons." → No question.
- **Ideas** — "Capture ideas on the fly, write daily journal entries, and see how your ideas connect to your research." → Ask: "Do you keep a regular journal? (Daily / occasionally / not currently)"
- **Research** — "Tracks your active research articles and PhD or main research project." → Ask: "What is your main research project or PhD topic called?"
- **Dropzone** — "A visual inbox: drag files here to have the Librarian process them." → No question.
- **Meetings** — "Records, transcribes, and analyses your meetings in three modes." → Ask: "Do you record meetings regularly? And do you prefer recording from your microphone or importing transcripts?"
- **Projects** — "Tracks all your projects with status, tasks, and one-click launchers." → Ask: "What tools do you use most for project work? (e.g., VS Code, RStudio, Word, Excel)"
- **Learning** — "Tracks courses you're working on and identifies skill gaps from your recent work." → Ask: "Which courses are you actively working on right now? (name + rough % complete)"
- **News** — "Your morning briefing — domain news, AI news, and RSS feeds filtered to your topics." → No question.
- **System** — "Shows every agent, every rule, token usage, and any pending self-improvement proposals." → No question.
- **Dropzone** — Already covered above.

Store answers in user-config.yaml under a `dashboard:` key.

---

## Section 11 — Dashboard launcher and MCP connection

### 11a — MCP server setup (connects Claude to your data)

**Show this explanation:**
> "The MCP server is the bridge between Claude Desktop and your Metis data. Without it, Claude can see your messages but can't look up your projects, tasks, or tracked files. This is a one-time setup."

Run:
```bash
cd "/mnt/c/Users/$(whoami)/[path-to-research-cortex]/metis/08_system/mcp-server"
python3 -m venv .venv
source .venv/bin/activate
pip install -e . -q
echo "MCP server installed"
```

Then check if `claude_desktop_config.json` already has the metis-rc entry:
```bash
CONFIG="$(wslpath -u "$APPDATA")/Claude/claude_desktop_config.json"
grep -l "metis-rc" "$CONFIG" 2>/dev/null && echo "ALREADY CONFIGURED" || echo "NEEDS CONFIG"
```

**If NEEDS CONFIG**, write the config:
```bash
USERNAME=$(whoami | sed 's|/mnt/c/Users/||')
# Detect actual Windows username
WIN_USER=$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r')
```

Then write `claude_desktop_config.json` with the correct paths for this user. Show the user:
> "I'm going to update your Claude Desktop config file. You'll need to restart Claude Desktop after this step."

After writing the config, instruct:
> "Please quit Claude Desktop completely (right-click the icon in the system tray → Quit), then reopen it."

---

### 11b — Dashboard shortcut

**Ask:** "Would you like to create a desktop shortcut or Start Menu entry to launch Metis with one click?"
```
1. Desktop shortcut
2. Start Menu entry
3. Both (recommended)
4. Neither — I'll launch from the terminal
```

If they choose 1, 2, or 3:
- Check if `launch_metis.bat` exists at `07_outputs/apps/metis-dashboard/launch_metis.bat`
- If yes, run the shortcut creator:
  ```bash
  powershell.exe -ExecutionPolicy Bypass -File \
    "$(wslpath -w "/mnt/c/Users/$(whoami)/[path-to-research-cortex]/metis/07_outputs/apps/metis-dashboard/create_shortcut.ps1")"
  ```
- Confirm with the user that the shortcut appeared.

Then tell them:
> "You can now launch Metis from your desktop or Start Menu — search for 'Metis Dashboard'. Click it once to start, then open http://localhost:3939 in your browser."

---

## Section 12 — Dashboard theme

**Ask:** "Which dashboard theme do you prefer?"
```
1. Light (macOS-style, default)
2. Dark
3. System default (follows your OS setting)
```

**Output in user-config.yaml:**
```yaml
dashboard:
  theme: "light"   # light | dark | system
```

Note: Dark theme and system-follow are on the roadmap. For now, store the preference — the config wizard will apply it when CSS theming is extended.

---

## Section 13 — Active courses

(Skip if already captured in Section 10.)

**Ask:** "Which courses are you actively working on right now? For each, tell me the name and roughly how far through you are. (This is different from completed courses — Metis tracks active learning separately.)"

**Output in user-config.yaml:**
```yaml
learning:
  active_courses:
    - name: ""
      progress_pct: 0
      added: ""
```

Also seed into the `course_progress` SQLite table.

---

## Closing summary

After all sections, display a clean summary of everything collected:

```
─────────────────────────────────────────
  Metis Configuration Summary
─────────────────────────────────────────
Name:              [name]
Role:              [role]
Language:          [language]
Context:           [general_context]

Projects found:    [N]
News topics:       [list]
Data protection:   [level]
Cybersecurity:     [level]

Librarian scan:    [interval]
News Radar scan:   [interval]

Active courses:    [list or "none"]
─────────────────────────────────────────
```

**Ask:** "Does this look correct? Type 'confirm' to save and apply, or tell me what to change."

On confirm:
1. Write `08_system/user-config.yaml` with full structured config
2. Insert any new projects into the `projects` SQLite table
3. Insert news topics into the `user_topics` SQLite table
4. Insert courses into `course_progress` SQLite table

Then display:

> "Metis is configured. Here's what happens next:
> - Your Projects tab has been seeded with [N] projects
> - News Radar will run at [interval] on topics: [list]
> - The Librarian will scan at [interval]
> - Your data protection level is set to [level]
> - Open your dashboard: run `launch_metis.bat` or use your new shortcut
> - To change any setting, just run `/metis_config` again"

---

## Output file

`08_system/user-config.yaml` — full structured config. Used by the dashboard (System tab), agents (as context), and scheduled jobs (scan intervals, topics).

## Edge cases

- User quits mid-wizard: save partial state to `user-config.yaml` under `wizard_progress: {last_section: N}`. On next run, offer to resume from where they left off.
- user-config.yaml already exists: show existing values and ask "update or keep?" for each section. Never silently overwrite existing config.
- User says "I don't know" to a required question: use the most conservative default (standard protection, daily scanning) and note it can be changed later.
- SQLite DB doesn't exist yet: call `ensure_db_schema(paths)` by running `source("07_outputs/apps/metis-dashboard/R/data_store.R")` or instruct the user to launch the dashboard once first.
