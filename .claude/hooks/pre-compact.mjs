#!/usr/bin/env node
/**
 * Metis pre-compact hook — saves a working state snapshot before context compaction.
 *
 * Claude compresses the conversation context when it gets long. This loses the
 * working thread — what was being built, what the last tool results were, what
 * decisions were just made. This hook captures a snapshot and writes it to
 * both a markdown journal file AND the session_summaries SQLite table.
 *
 * Snapshot location:
 *   <RC_ROOT>/journal/sessions/pre-compact-<YYYY-MM-DD>-<HH-MM>.md
 *
 * Hook input (stdin): JSON { summary?: string, turns?: number }
 * This hook never blocks.
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from "fs";
import { join } from "path";
import { execSync } from "child_process";

const RC_ROOT = process.env.METIS_RC_ROOT || "";
const HOOK_PROFILE = (process.env.METIS_HOOK_PROFILE || "standard").toLowerCase();

if (HOOK_PROFILE === "minimal") process.exit(0);
if (!RC_ROOT) process.exit(0);

let input = {};
try {
  const raw = readFileSync("/dev/stdin", "utf8");
  if (raw.trim()) input = JSON.parse(raw);
} catch {
  // Empty or unparseable stdin — proceed with defaults
}

try {
  const now = new Date();
  const date = now.toISOString().slice(0, 10);
  const timeSlug = now.toISOString().slice(11, 16).replace(":", "-");

  const summary = input?.summary || input?.context_summary || "(no summary available)";
  const turns = input?.turns || input?.turn_count || "unknown";

  // Build a thorough snapshot — include raw input JSON so nothing is lost
  const snapshot = [
    `# Pre-compact snapshot — ${now.toISOString()}`,
    `Turns before compaction: ${turns}`,
    ``,
    `## Context summary at compaction`,
    summary,
    ``,
    `## Raw hook input`,
    "```json",
    JSON.stringify(input, null, 2),
    "```",
    ``,
    `---`,
    `*Written automatically before Claude compressed its conversation context.*`,
    `*Read this file at session start to re-orient if context was lost.*`,
    ``,
  ].join("\n");

  const dir = join(RC_ROOT, "journal", "sessions");
  mkdirSync(dir, { recursive: true });
  const snapshotPath = join(dir, `pre-compact-${date}-${timeSlug}.md`);
  writeFileSync(snapshotPath, snapshot);

  // Also persist to SQLite session_summaries table if db is reachable
  const dbPath = join(RC_ROOT, "system", "app", "data", "metis.sqlite");
  if (existsSync(dbPath) && summary !== "(no summary available)") {
    try {
      const escapedSummary = summary.replace(/'/g, "''");
      const sql = `
        CREATE TABLE IF NOT EXISTS session_summaries (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          session_id TEXT,
          summary TEXT NOT NULL,
          key_topics TEXT,
          decisions TEXT,
          created_at TEXT NOT NULL
        );
        INSERT INTO session_summaries (session_id, summary, key_topics, decisions, created_at)
        VALUES ('pre-compact', '${escapedSummary}', '[]', '[]', '${now.toISOString()}');
      `;
      execSync(`sqlite3 "${dbPath}" "${sql.replace(/\n/g, ' ')}"`, { timeout: 5000 });
    } catch {
      // sqlite3 CLI not available or db locked — snapshot file is sufficient
    }
  }
} catch {
  // Silent — hook must never crash the session
}

process.exit(0);
