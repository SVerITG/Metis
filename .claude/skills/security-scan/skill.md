---
name: security-scan
description: Audit the current session for security and data-safety issues
type: skill
---

# /security-scan — Session Security Audit

Run this skill after any session involving external data (RSS feeds, web fetch, uploaded files, 
meeting transcripts) or when you want to verify the session is clean before ending.

## What the scan checks

1. **Tool-use audit** — reads today's session log from `journal/sessions/session-YYYY-MM-DD.jsonl`
   and lists every tool called, how many times, and any agent hints.

2. **Injection pattern hits** — reads the session injection counter at
   `/tmp/metis-injection-session.json` and reports whether any patterns fired and how many times.
   Three or more hits from the same pattern in a session are elevated to HIGH severity.

3. **File read safety** — for every Read/WebFetch call in the session log, check if the file path
   or URL matches the sensitive path list in `pre-tool-use.mjs`.

4. **Output PII check** — scan the last 20 entries in `journal/sessions/session-YYYY-MM-DD.jsonl`
   for any tool results containing email addresses, phone numbers, patient IDs, or Belgian NIDs.

5. **API key exposure** — grep the session log for strings that match API key patterns
   (`sk-ant-...`, `ZOTERO_API_KEY`, `.env`). Flag any that appear in a response context.

## How to run

```
/security-scan
```

No arguments. The skill reads the current date and finds today's log automatically.

## Output format

Pass/fail summary followed by any findings:

```
SECURITY SCAN — 2026-05-12
────────────────────────────
✅ Tool use: 14 calls across 4 tools. No unusual patterns.
✅ Injection counter: 0 patterns fired this session.
✅ File reads: 3 files read — none match sensitive path list.
⚠️  Output PII: 1 result contained a potential email address (tool: WebFetch, ts: 14:32)
✅ API key exposure: none detected.

Summary: 1 warning, 0 blocks. Session is clean for handoff.
```

## Steps

1. Read `journal/sessions/session-YYYY-MM-DD.jsonl` (today's date).
2. Parse each line. Build tool counts and extract any `tool` entries that are Read/WebFetch.
3. Read `/tmp/metis-injection-session.json` if it exists. Report counts per pattern.
4. For each file/URL in tool log: check against `SENSITIVE_PATH_PATTERNS` from `pre-tool-use.mjs`.
5. For each tool result in log: run lightweight regex for email / phone / patient ID patterns.
6. Grep tool results for API key format strings.
7. Print the formatted summary.
8. If severity HIGH (3+ injection hits, or sensitive data in output): recommend running
   `/metis-handoff` immediately and reviewing outputs before the next session.
