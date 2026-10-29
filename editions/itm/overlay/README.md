# Metis for ITM

A research companion for researchers at the **Institute of Tropical Medicine
Antwerp**. Metis gives every conversation with Claude a memory of your subject,
your papers, your projects and your decisions, and it brings the institute's own
templates and procedures with it.

It starts empty. The installer asks what you work on, which methods you use and
what you want followed in the news, and everything Metis shows — the morning
briefing, the literature it surfaces, the specialists it brings in — is built
from those answers and from your own documents. Nothing about anyone else's
research is pre-loaded.

## Install

1. Install [Claude Desktop](https://claude.ai/download) and sign in.
2. Download **MetisSetup-ITM** from
   [Releases](https://github.com/SVerITG/Metis_ITM/releases/latest) and run it.
   No administrator rights are needed.
3. Answer the questions (about two minutes). When setup finishes, open Claude
   Desktop: Metis is connected.

If Windows SmartScreen warns about an unknown publisher, choose
*More info → Run anyway* (the installer is not code-signed yet).

## What you get

| | |
|---|---|
| **ITM** | The institute's section, at the top of the dashboard: prepare an IRB submission, make an ITM presentation or poster, download the templates |
| **Today** | Your morning briefing, what is new in your field, what needs you today |
| **News** | The world, filtered by the topics you chose |
| **Library** | Your own papers, searchable by meaning, with citations back to the page |
| **Work** | Projects and tasks |
| **Meetings** | Notes turned into decisions and actions |
| **Reflection** | Ideas and notes, connected to your work |
| **Statistics course** | The online course, one click from the sidebar |

In Claude Desktop, Metis brings in the right specialist for a request — a
librarian, a methods coach, an epidemiologist, a writing partner, a data
guardian and others — and remembers what was decided.

## Your data

Your files and the Metis database stay on your computer. What you type or share
in a conversation is processed by Anthropic's Claude service. If you paste rows
about individual people, Metis checks them first and offers a script you run on
your own computer instead.

## Testing it without installing

A test image installs the same software as a new colleague and checks every
surface and the ITM pack:

```bash
docker compose -f docker/docker-compose.yml run --rm test          # smoke test
docker compose -f docker/docker-compose.yml up --build dashboard   # http://localhost:8080
```

On Windows, `system/install/installer/metis-sandbox.wsb` opens a disposable
Windows Sandbox for trying the real installer.

## Something not working?

Say *"check that everything works"* to Metis in Claude Desktop, or use
**Run health check** on the dashboard's Metis tab. It checks the installation
and repairs what it can.
