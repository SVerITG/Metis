# Fix or change Metis — two easy ways

Metis can check itself and reconfigure itself **just by asking it**. You don't need to
edit any files or write code. There are two doors — pick whichever feels comfortable.

There are two things you can ask for:

| Say this | What it does |
|---|---|
| **metis-doctor** | Checks that Metis is working properly on *your* computer and tells you, in plain language, how to fix anything that isn't. |
| **metis-customize** | Walks you through changing Metis — your projects, the look of the dashboard, how Metis talks to you, or anything you describe in your own words. |

---

## Door A — Claude Desktop  (easiest, recommended for most people)

Claude Desktop is a normal app with a chat window. No terminal, no code.

1. **Install Claude Desktop** (free): https://claude.ai/download
2. Open it. Metis registers itself automatically the first time (it appears as **metis-rc**).
3. Click the **＋ / prompt menu** in the message box (where you'd attach a file). You'll see
   Metis's prompts listed.
4. Pick **“Metis Doctor — health check”** to check your install, or
   **“Metis Customize — make Metis yours”** to change something.
5. Answer Metis's questions in plain language. That's it.

> If you don't see the Metis prompts: quit Claude Desktop completely and reopen it. If they
> still don't appear, use Door B and run `/metis-doctor` — it will tell you why.

---

## Door B — Claude Code  (for the terminal, more powerful)

Claude Code runs in a terminal and can make deeper changes.

1. **Install Claude Code**: https://docs.anthropic.com/en/docs/claude-code/getting-started
2. Open it **in your Metis / Research Cortex folder** (in VS Code: open the folder, then
   `Ctrl+\`` for the terminal; or from a terminal, `cd` into the folder and run `claude`).
3. Type one of:
   - `/metis-doctor` — check the install
   - `/metis-customize` — change something
4. Follow the prompts.

---

## Which door should I use?

- **Just want to use Metis and occasionally tweak it?** → **Door A (Claude Desktop).**
- **Comfortable with a terminal, or want bigger structural changes?** → **Door B (Claude Code).**

Both reach the *same* Metis and the *same* two commands. Desktop is friendlier; Code is more
powerful. You can switch any time.

---

## A note on changing Metis

`metis-customize` will happily change small things (your projects, Metis's tone) safely and
instantly. For bigger **structural** changes (the look of the dashboard, new behaviour), Metis
will warn you first:

> *It's your Metis, so of course you can change it — but after a structural change I can't
> guarantee everything still works. I'll make the change, then you run **metis-doctor** to
> check, and we can always undo it.*

That's the deal: full freedom to make Metis yours, with a one-command safety net
(`metis-doctor`) and an undo (git) if something breaks.
