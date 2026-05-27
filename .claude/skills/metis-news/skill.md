---
name: Metis News
description: "news, news briefs, latest news, news signals, global health news, AI news, what's in the news, current events, news summary, news today, news updates, news feed, news briefing, signal"
model: claude-haiku-4-5-20251001
effort: normal
complexity: quick
---

## Purpose

A curated news digest from the CLI — the Today tab's news rail without opening a browser. Shows the most recent signals from `news_briefs`, grouped by domain. Accepts an optional domain filter.

## Critical: MCP tools are always available

The `metis-rc` MCP server is registered globally. **Always call the MCP tools immediately — do not say they are unavailable without first attempting the call.** If a tool call returns an error, report that error. If it succeeds, use the data.

## What to do when invoked

**Usage:** `/metis_news` or `/metis_news [domain]`

Domain filters: use any domain tag from your `news_topics` config, or `AI` · `public-health` · `methods` · `all`

Examples:
- `/metis_news` — top 6 most recent briefs across all domains
- `/metis_news [your-domain]` — only news tagged with your domain
- `/metis_news AI` — only AI-tagged news

**Step 1 — Pull news briefs**
- No filter: `get_news_briefs(limit=6, order_by="created_at DESC")`
- With domain: `get_news_briefs(domain="{filter}", limit=8, order_by="created_at DESC")`

**Step 2 — Check last scan time**
`get_agent_runs(agent_slug IN ('news-radar','librarian','news-aggregator','content-scan'), limit=1)` — surface when news was last updated.

**Step 3 — Compose output**

Group by domain. For each brief:
- Title (truncated to 70 chars)
- Source URL (abbreviated domain only, e.g. `who.int`)
- Age (e.g. `3h`, `2d`, `1w`)
- Signal strength tag if available: `[HIGH]` / `[MEDIUM]` / `[LOW]`

**Step 4 — Suggest action**
If no briefs exist or last scan > 24h ago: suggest running `/news-radar` or clicking "Scan for content" on the dashboard.

**Step 5 — Do not log** (read-only, lightweight).

## Output format

```
─── News signals — [YYYY-MM-DD HH:MM] ─────────────────────
Last scan: [time ago] via [content-scan / news-radar]

[YOUR-DOMAIN]
  · [Title truncated to 70 chars]  (source.org · 2h) [MEDIUM]
  · [Title]  (source.org · 1d)

[AI]
  · [Title]  (anthropic.com · 3h) [HIGH]

[PUBLIC-HEALTH]
  · [Title]  (cdc.gov · 2d)

[METHODS]
  · [Title]  (wwwnc.cdc.gov · 1w)
─────────────────────────────────────────────────────────
Run /news-radar to fetch new signals · Dashboard: Today tab
```

If the news_briefs table is empty or no results match the filter, say: _"No news signals yet. Run /news-radar or click 'Scan for content' on the dashboard."_
