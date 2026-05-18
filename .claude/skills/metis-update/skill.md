---
name: metis-update
description: "update metis, refresh metis, scan news, scan literature, check inbox, sync files, what's new, update knowledge base, run scans, metis refresh, pull latest"
model: claude-haiku-4-5-20251001
---

## Purpose

Run all Metis update scans and surface what changed. No LLM-heavy analysis — this is a fast data refresh.

## What to do

1. Call `full_scan()` — runs news, literature, inbox, and tracked files in one shot
2. Present the results clearly
3. If inbox has items, suggest routing them: "You have N inbox items — run `/metis-inbox` to process them"
4. If changed files include PLANNING.md for an active project, flag it: "PLANNING.md changed in [project] — read it before continuing"
5. If news items were added, offer: "N new news items added — run `/metis-news` to see a briefing"

## Output format

Show the full_scan output as-is, then add a one-line action prompt for anything that needs attention. Keep it under 10 lines total.

## When invoked with an argument

- `/metis-update news` → call `scan_news()` only
- `/metis-update literature` → call `scan_literature()` only  
- `/metis-update inbox` → call `scan_inbox()` only
- `/metis-update files` → call `scan_tracked_files()` only
- `/metis-update` (no argument) → call `full_scan()`
