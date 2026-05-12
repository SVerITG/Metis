#!/usr/bin/env node
/**
 * Metis stop hook — auto-generates a handoff brief at session end.
 *
 * Fires when Claude Code ends a session (user types /exit, hits Ctrl+C,
 * or the session ends normally). Attempts to:
 *
 *   1. Call the FastAPI handoff endpoint (if the dashboard is running).
 *   2. If that fails, write a "pending handoff" marker so the next
 *      session knows to generate a brief on startup.
 *
 * The handoff brief lands at:
 *   <RC_ROOT>/journal/sessions/handoff-<YYYY-MM-DD>-<HH-MM>.md
 *
 * Hook input (stdin): JSON { stop_reason: "end_turn"|"max_turns"|"user_interrupt" }
 * This hook never blocks — errors are silent.
 */

import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { join } from "path";

const RC_ROOT = process.env.METIS_RC_ROOT || "";
const DASHBOARD_URL = process.env.METIS_DASHBOARD_URL || "http://127.0.0.1:8000";
const HOOK_PROFILE = (process.env.METIS_HOOK_PROFILE || "standard").toLowerCase();

if (HOOK_PROFILE === "minimal") process.exit(0);

let stopReason = "end_turn";
try {
  const raw = readFileSync("/dev/stdin", "utf8");
  if (raw.trim()) {
    const input = JSON.parse(raw);
    stopReason = input?.stop_reason || input?.reason || "end_turn";
  }
} catch {
  // stdin may be empty on some stop events — that's fine
}

const now = new Date();
const date = now.toISOString().slice(0, 10);
const timeSlug = now.toISOString().slice(11, 16).replace(":", "-");

async function tryDashboardHandoff() {
  try {
    // Node 18+ has native fetch
    const res = await fetch(`${DASHBOARD_URL}/api/handoff/generate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ source: "stop-hook", stop_reason: stopReason }),
      signal: AbortSignal.timeout(8000),
    });
    if (res.ok) {
      const data = await res.json().catch(() => ({}));
      return data?.path || data?.output_path || true;
    }
  } catch {
    // Dashboard not running — fall through
  }
  return null;
}

function writeMarker(brief_path_or_flag) {
  if (!RC_ROOT) return;
  try {
    const dir = join(RC_ROOT, "journal", "sessions");
    mkdirSync(dir, { recursive: true });

    if (typeof brief_path_or_flag === "string") {
      // Dashboard succeeded and returned a path — just write a pointer
      const marker = `# Session ended ${now.toISOString()}\nHandoff brief: ${brief_path_or_flag}\nStop reason: ${stopReason}\n`;
      writeFileSync(join(dir, `handoff-${date}-${timeSlug}.md`), marker);
    } else {
      // Dashboard unavailable — write a "generate on next start" marker
      const marker = [
        `# Pending handoff — ${now.toISOString()}`,
        `Stop reason: ${stopReason}`,
        `Status: Dashboard was not running when session ended.`,
        `Action: Run /metis_handoff at the start of your next session to generate the brief.`,
        "",
      ].join("\n");
      writeFileSync(join(dir, `handoff-${date}-${timeSlug}.md`), marker);
    }
  } catch {
    // Silent
  }
}

// Run async and wait briefly so the hook doesn't outlive the process
(async () => {
  const result = await tryDashboardHandoff();
  writeMarker(result);
  process.exit(0);
})();
