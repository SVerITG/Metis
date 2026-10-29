# Metis morning briefing — the routine Claude Desktop runs each weekday

Claude Desktop's scheduled task `metis-morning-briefing` contains one line:
*"Read this file and follow it."* Setup creates that task
(`system/install/register_schedule.py`). **Change the routine here, never in the
task**: this file is updated with Metis, the task is not.

Use the Metis connector (the metis-rc tools) throughout. The person is not
present: never ask a question, never wait on a step that hangs. Note it and move
on — a partial briefing beats none.

## 1. Already done today?

Call `get_daily_insight()`. If it returns a brief for today's date, stop and
reply "Today's briefing was already there."

## 2. Collect what is new

Call `scan_news()` and then `scan_literature()`. A scan that errors or runs past
about ten minutes is noted and skipped. Feeds that fail with certificate errors
are a known network issue on some institute networks: note the count, carry on.

## 3. Write the briefing

Each brief is two calls. `generate_daily_insight(period=...)` returns the writing
instructions, the context, and the exact save call. **Follow those instructions
to the letter** — they are the dashboard's own, so the brief reads the same
whichever path wrote it: continuous prose, no headers, no bullets. End with the
`<<THREADS: ...>>` line it asks for, then make the save call it gives
(`save_daily_brief`). Do not write a brief from any other context of your own.

1. Daily: `generate_daily_insight(period="daily")` → the save call.
2. **Monday:** also `period="weekly"`.
3. **After a gap:** if the most recent earlier brief is more than one working
   day old, also `period="catchup"`. Skip it when it reports no context.

## 4. Record

1. `log_agent_run(agent_slug="news-radar", task_summary="Scheduled morning briefing")`
2. Reply with one short summary: what was saved, and which steps failed.
