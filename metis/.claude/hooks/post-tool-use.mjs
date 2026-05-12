#!/usr/bin/env node
/**
 * Metis post-tool-use session pulse hook
 *
 * Fires after every tool call. Appends a JSONL entry to the session log so
 * the dashboard can show which tools were used, which agents were active, and
 * the total tool-call count for today.
 *
 * Log location: <RC_ROOT>/journal/sessions/session-<YYYY-MM-DD>.jsonl
 *
 * Hook input (stdin): JSON { tool_name, tool_input, tool_response, session_id }
 * This hook never blocks — any error silently exits 0.
 */

import { readFileSync, appendFileSync, mkdirSync } from "fs";
import { join } from "path";

const RC_ROOT = process.env.METIS_RC_ROOT || "";
const HOOK_PROFILE = (process.env.METIS_HOOK_PROFILE || "standard").toLowerCase();

// Minimal profile: skip session logging entirely
if (HOOK_PROFILE === "minimal") process.exit(0);

let input;
try {
  input = JSON.parse(readFileSync("/dev/stdin", "utf8"));
} catch {
  process.exit(0);
}

try {
  const { tool_name, tool_input, session_id } = input;

  // Skip noisy read-only meta tools that aren't useful for the pulse
  const SKIP_TOOLS = new Set(["get_user_profile", "session_bootstrap"]);
  if (SKIP_TOOLS.has(tool_name)) process.exit(0);

  const now = new Date();
  const date = now.toISOString().slice(0, 10);
  const ts = now.toISOString();

  // Infer agent slug from tool name or session context
  const agentHints = {
    search_literature: "librarian", sync_zotero_library: "librarian",
    capture_idea: "metis", cross_pollinate: "metis",
    write_reflexion: "metis", log_agent_run: "metis",
    scan_news: "news-radar", scan_literature: "librarian",
    generate_daily_insight: "metis", apply_proposal: "metis",
  };
  const agent_hint = agentHints[tool_name] || null;

  const entry = {
    ts,
    tool: tool_name,
    ...(agent_hint && { agent: agent_hint }),
    ...(session_id && { session_id }),
  };

  if (RC_ROOT) {
    const sessionDir = join(RC_ROOT, "journal", "sessions");
    mkdirSync(sessionDir, { recursive: true });
    appendFileSync(
      join(sessionDir, `session-${date}.jsonl`),
      JSON.stringify(entry) + "\n"
    );
  }
} catch {
  // Never crash — just exit silently
}

process.exit(0);
