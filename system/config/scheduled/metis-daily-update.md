# Metis daily update — one definition for every computer

Each computer's scheduled task `metis-daily-update` contains one line:
*"Follow system/config/scheduled/metis-daily-update.md in the project folder."*
**Change the routine here, never in a task** — a task's own prompt lives only on
the machine that created it, which is how the two computers drifted apart before.

The task is scheduled on BOTH computers. Step 1 makes sure only the first one to
run on a given day does the work; the other just pulls the result.

Shell commands run inside WSL from the project root:
`wsl.exe bash -lc 'cd "<project root as a /mnt/c/... path>" && <command>'`

---

## 1. Claim the day — or stand down

1. Note this computer's hostname and today's local date (`YYYY-MM-DD`).
2. Pull what the other computer has published:
   `python3 tools/metis-sync-db.py --import-only`
3. Look at `system/app/data/cloud-backups/daily-update-<date>.claim`
   (OneDrive-synced, gitignored).
   - **Exists, written by another host less than 3 hours ago, not `done`** → that
     computer is mid-run. Stop; its result arrives with the next sync.
   - **Missing, stale (>3 h, not `done`), or `done` but today's brief is NOT in
     this machine's `daily_insights` after the import** → write the claim:
     `host=<hostname> started=<ISO time> status=running` and continue. A `done`
     whose brief never arrived means the other machine did not publish; the
     researcher would otherwise open this dashboard to no brief at all.
4. If `daily_insights` already holds a row for today's date, mark the claim `done`
   and stop — the brief exists, whichever machine wrote it. This is the ONLY
   reason to stand down on a `done` claim.

## 2. Collect

Run the news and literature scans. **A scan that errors or runs past ~10 minutes
is noted and skipped, never waited on** — a stalled scan once held the whole
update for six days. Feeds failing with certificate errors are a known local
network issue: note the count, carry on.

## 3. Today boards

From the researcher's profile and active projects, web-search and fill the three
boards with `update_today_board`:
- **outbreaks** — the handful that matter now, each with place and date
- **events** — conferences and meetings in the field, with dates
- **funding** — open calls with deadlines; drop closed ones

## 4. Briefs

Each brief is two calls. `generate_daily_insight(period=...)` returns the writing
instructions, the context, and the exact save call. **Follow those instructions
to the letter** — they are the dashboard generator's own, so the brief reads the
same whichever path wrote it: continuous prose, no headers, no bullets, no date
line, no closing note. End with the `<<THREADS: ...>>` line it asks for, then
make the save call it gives. Do not write a brief from `get_news_briefs` or any
other context of your own; that is how a brief comes out in a different format.

1. Daily: `generate_daily_insight(period="daily")` → `save_daily_brief(...)`.
2. **Monday:** also `period="weekly"`.
3. **Gap:** if the latest earlier brief is more than one working day old, also
   `period="catchup"`.

## 5. Record and publish

1. `log_agent_run(agent_slug="news-radar", task_summary="Scheduled daily update on <hostname>")`
2. `save_session_summary(...)` — what was collected, what failed.
3. Publish so the other computer has it within hours, not tomorrow:
   `python3 tools/metis-sync-db.py`
4. Rewrite the claim: `status=done finished=<ISO time>`, plus any failed steps.

If any step fails outright, record it in the claim file and the session summary,
then continue with the next step. Finishing with a partial update beats stalling.
