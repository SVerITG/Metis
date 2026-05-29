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

import { readFileSync, writeFileSync, mkdirSync, existsSync } from "fs";
import { join } from "path";

const RC_ROOT = process.env.METIS_RC_ROOT || process.cwd();
const DASHBOARD_URL = process.env.METIS_DASHBOARD_URL || "http://127.0.0.1:8080";
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

async function touchPlanningFiles() {
  if (!RC_ROOT) return [];
  try {
    const res = await fetch(`${DASHBOARD_URL}/api/session/touch-planning`, {
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json().catch(() => ({}));
      return data?.updated || [];
    }
  } catch {
    // Dashboard not running — fall through to local fallback
  }

  // Local fallback: scan known PLANNING.md paths from RC root
  const today = now.toISOString().slice(0, 10);
  const marker = `\n\n---\n_Last Metis session: ${today}_\n`;
  const updated = [];
  try {
    const projectsActive = join(RC_ROOT, "projects", "active");
    if (existsSync(projectsActive)) {
      const { readdirSync, statSync } = await import("fs");
      for (const entry of readdirSync(projectsActive, { withFileTypes: true })) {
        if (!entry.isDirectory()) continue;
        const planningPath = join(projectsActive, entry.name, "PLANNING.md");
        if (existsSync(planningPath)) {
          const content = readFileSync(planningPath, "utf8");
          if (!content.includes(`_Last Metis session: ${today}_`)) {
            writeFileSync(planningPath, content + marker);
            updated.push(planningPath);
          }
        }
      }
    }
  } catch {
    // Silent — PLANNING.md update is best-effort
  }
  return updated;
}

async function consolidateSession() {
  // Read the AUTO-GENERATED handoff brief that lives at
  // journal/YYYY-MM-DD_session_handoff_auto.md — that's the real brief with
  // Active Projects / Open Tasks / Recent agent runs sections.
  //
  // (We used to read the stop-hook MARKER file at journal/sessions/handoff-*.md
  //  which is just a 3-line pointer and contained nothing extractable.)
  let briefContent = "";
  let briefTempFile = "";
  try {
    if (RC_ROOT) {
      const { existsSync } = await import("fs");
      const autoBriefPath = join(RC_ROOT, "journal", `${date}_session_handoff_auto.md`);
      if (existsSync(autoBriefPath)) {
        briefContent = readFileSync(autoBriefPath, "utf8");
        const sessionDir = join(RC_ROOT, "journal", "sessions");
        briefTempFile = join(sessionDir, `.brief-tmp-${date}.txt`);
        writeFileSync(briefTempFile, briefContent);
      }
    }
  } catch {
    // Cannot read brief — proceed without
  }

  // ── Try dashboard API first ────────────────────────────────────────────────
  try {
    const res = await fetch(`${DASHBOARD_URL}/api/session/consolidate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ brief_content: briefContent }),
      signal: AbortSignal.timeout(10000),
    });
    if (res.ok) {
      try { if (briefTempFile && existsSync(briefTempFile)) { const { unlinkSync } = await import("fs"); unlinkSync(briefTempFile); } } catch {}
      return await res.json().catch(() => ({}));
    }
  } catch {
    // Dashboard not running — fall through to Python fallback
  }

  // ── Python fallback: write directly to SQLite without the dashboard ────────
  try {
    const { spawnSync } = await import("child_process");
    const metisVenv = process.env.METIS_MCP_VENV
      || join(process.env.HOME || "/home", ".local", "share", "metis-mcp", ".venv");
    const python = join(metisVenv, "bin", "python3");
    const script = join(RC_ROOT, "system", "mcp-server", "src", "metis_mcp", "_consolidate_session.py");
    const args = briefTempFile ? [script, RC_ROOT, briefTempFile] : [script, RC_ROOT];
    spawnSync(python, args, { timeout: 12000 });
  } catch {
    // Python also unavailable — silent
  } finally {
    try { if (briefTempFile && existsSync(briefTempFile)) { const { unlinkSync } = await import("fs"); unlinkSync(briefTempFile); } } catch {}
  }
  return null;
}

async function notifyProjectActivity() {
  // Detect if cwd matches a registered Metis project folder and ping the dashboard.
  try {
    const cwd = process.cwd();
    const res = await fetch(`${DASHBOARD_URL}/api/project/session-end`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ cwd, stop_reason: stopReason, ts: now.toISOString() }),
      signal: AbortSignal.timeout(4000),
    });
    if (res.ok) {
      const data = await res.json().catch(() => ({}));
      if (data.project_id) {
        // Also trigger a lightweight folder scan for the active project
        fetch(`${DASHBOARD_URL}/api/project/scan/${data.project_id}`, {
          method: "POST",
          signal: AbortSignal.timeout(15000),
        }).catch(() => {});
      }
    }
  } catch {
    // Dashboard not running or project not matched — silent
  }
}

// Run async and wait briefly so the hook doesn't outlive the process
(async () => {
  const [result] = await Promise.all([
    tryDashboardHandoff(),
    touchPlanningFiles(),
    consolidateSession(),
    notifyProjectActivity(),
  ]);
  writeMarker(result);
  process.exit(0);
})();
