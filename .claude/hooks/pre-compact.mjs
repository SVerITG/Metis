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
 * Hook input (stdin): JSON { session_id, transcript_path, trigger, ... }
 *
 * Claude Code passes no summary to this hook, so every snapshot used to read
 * "(no summary available)"; and the database write went, through the sqlite3
 * CLI, to system/app/data/metis.sqlite — the abandoned OneDrive copy, not the
 * live database the dashboard reads (resolve_live_db). The snapshot now carries
 * the conversation from the transcript, and the session's record is written
 * the same way the stop hook writes it.
 * This hook never blocks.
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync, unlinkSync } from "fs";
import { join } from "path";
import { spawnSync } from "child_process";
import { localStamp, readConversation, formatConversation, trackingDisabled } from "./lib/session-capture.mjs";

const RC_ROOT = process.env.METIS_RC_ROOT || process.cwd();
const DASHBOARD_URL = process.env.METIS_DASHBOARD_URL || "http://127.0.0.1:8080";
const HOOK_PROFILE = (process.env.METIS_HOOK_PROFILE || "standard").toLowerCase();

if (HOOK_PROFILE === "minimal" || trackingDisabled()) process.exit(0);

let input = {};
try {
  const raw = readFileSync("/dev/stdin", "utf8");
  if (raw.trim()) input = JSON.parse(raw);
} catch {
  // Empty or unparseable stdin — proceed with defaults
}

const conversation = readConversation(input?.transcript_path);
if (conversation?.optOut) process.exit(0);  // asked not to be tracked
const conversationText = formatConversation(conversation);

async function recordSession() {
  const payload = {
    session_id: String(input?.session_id || ""),
    conversation: conversationText,
    brief_content: "",
    enrich: true,  // a natural checkpoint: the context is about to be compressed
  };
  try {
    const res = await fetch(`${DASHBOARD_URL}/api/session/consolidate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(10000),
    });
    if (res.ok) return;
  } catch {
    // Dashboard not running — write it directly
  }
  const dir = join(RC_ROOT, "journal", "sessions");
  const payloadFile = join(dir, `.consolidate-precompact-${Date.now()}.json`);
  try {
    const metisVenv = process.env.METIS_MCP_VENV
      || join(process.env.HOME || "/home", ".local", "share", "metis-mcp", ".venv");
    const python = join(metisVenv, "bin", "python3");
    const script = join(RC_ROOT, "system", "mcp-server", "src", "metis_mcp", "_consolidate_session.py");
    writeFileSync(payloadFile, JSON.stringify(payload));
    spawnSync(python, [script, RC_ROOT, "--payload", payloadFile], { timeout: 12000 });
  } catch {
    // Python unavailable — the snapshot file is sufficient
  } finally {
    try { if (existsSync(payloadFile)) unlinkSync(payloadFile); } catch {}
  }
}

(async () => {
try {
  const now = new Date();
  const { date, time: timeSlug } = localStamp(now);

  const summary = input?.summary || input?.context_summary || conversationText || "(no summary available)";
  const turns = input?.turns || input?.turn_count || conversation?.turns || "unknown";

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

  // And the session's record in the live database.
  if (conversationText) await recordSession();
} catch {
  // Silent — hook must never crash the session
}
process.exit(0);
})();
