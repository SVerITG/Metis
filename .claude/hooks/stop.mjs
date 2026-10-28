#!/usr/bin/env node
/**
 * Metis stop hook — records the session in Metis's memory.
 *
 * Claude Code fires Stop at the end of EVERY reply, not once at session end.
 * This hook used to treat each one as a session ending: a new session_summaries
 * row per reply (the same day-level text each time), a new handoff marker file
 * per minute, and — with an API key — a paid summarising call per reply. And it
 * never read the conversation, so what was actually discussed was not in it.
 *
 * Now, per reply:
 *   · the session's record is UPDATED in place (one row per session, keyed on
 *     Claude Code's session_id), and carries what was asked and where the last
 *     answer ended — read from the transcript (lib/session-capture.mjs);
 *   · the heavier work — handoff brief, PLANNING.md touch, project scan, and the
 *     AI enrichment of the record — runs on the first reply of a session and
 *     then at most every FULL_EVERY_MIN minutes.
 *
 * The researcher's rule: every conversation is tracked unless they explicitly
 * ask not to. An opted-out session records nothing.
 *
 * Hook input (stdin): JSON { session_id, transcript_path, stop_hook_active, ... }
 * This hook never blocks — errors are silent.
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync, unlinkSync, readdirSync } from "fs";
import { join } from "path";
import { localStamp, readConversation, formatConversation, trackingDisabled } from "./lib/session-capture.mjs";

const RC_ROOT = process.env.METIS_RC_ROOT || process.cwd();
const DASHBOARD_URL = process.env.METIS_DASHBOARD_URL || "http://127.0.0.1:8080";
const HOOK_PROFILE = (process.env.METIS_HOOK_PROFILE || "standard").toLowerCase();
const FULL_EVERY_MIN = 20;

if (HOOK_PROFILE === "minimal" || trackingDisabled()) process.exit(0);

let input = {};
try {
  const raw = readFileSync("/dev/stdin", "utf8");
  if (raw.trim()) input = JSON.parse(raw);
} catch {
  // stdin may be empty on some stop events — that's fine
}
const stopReason = input?.stop_reason || input?.reason || "end_turn";
const sessionId = String(input?.session_id || "");
const sid8 = (sessionId || "nosession").replace(/[^A-Za-z0-9-]/g, "").slice(0, 8) || "nosession";

const now = new Date();
const { date, time: timeSlug } = localStamp(now);
const sessionDir = join(RC_ROOT, "journal", "sessions");

const conversation = readConversation(input?.transcript_path);
if (conversation?.optOut) process.exit(0);  // asked not to be tracked
const conversationText = formatConversation(conversation);

// ── Throttle: is this a "full" run? ─────────────────────────────────────────
const STATE_FILE = join(sessionDir, ".stop-state.json");
function loadState() {
  try { return JSON.parse(readFileSync(STATE_FILE, "utf8")) || {}; } catch { return {}; }
}
const state = loadState();
const lastFull = state[sid8]?.last_full || 0;
const fullRun = now.getTime() - lastFull >= FULL_EVERY_MIN * 60 * 1000;
function saveState() {
  try {
    mkdirSync(sessionDir, { recursive: true });
    if (fullRun) state[sid8] = { last_full: now.getTime() };
    // Keep the newest 50 sessions; the file must not grow forever.
    const keys = Object.keys(state).sort((a, b) => (state[b].last_full || 0) - (state[a].last_full || 0));
    for (const k of keys.slice(50)) delete state[k];
    writeFileSync(STATE_FILE, JSON.stringify(state));
  } catch { /* best-effort */ }
}

async function tryDashboardHandoff() {
  try {
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
  // One marker per SESSION, rewritten — not one per reply.
  try {
    mkdirSync(sessionDir, { recursive: true });
    const head = typeof brief_path_or_flag === "string"
      ? [`# Session ${sid8} — last reply ${now.toISOString()}`, `Handoff brief: ${brief_path_or_flag}`]
      : [`# Session ${sid8} — last reply ${now.toISOString()}`,
         `Status: Dashboard was not running when this was written.`,
         `Action: Run /metis_handoff at the start of your next session to generate the brief.`];
    const body = [...head, `Stop reason: ${stopReason}`, "", conversationText, ""].join("\n");
    writeFileSync(join(sessionDir, `handoff-${date}-${sid8}.md`), body);
  } catch {
    // Silent
  }
}

async function touchPlanningFiles() {
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
  const marker = `\n\n---\n_Last Metis session: ${date}_\n`;
  const updated = [];
  try {
    const projectsActive = join(RC_ROOT, "projects", "active");
    if (existsSync(projectsActive)) {
      for (const entry of readdirSync(projectsActive, { withFileTypes: true })) {
        if (!entry.isDirectory()) continue;
        const planningPath = join(projectsActive, entry.name, "PLANNING.md");
        if (existsSync(planningPath)) {
          const content = readFileSync(planningPath, "utf8");
          if (!content.includes(`_Last Metis session: ${date}_`)) {
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
  // The day's auto-generated handoff brief (projects, open tasks, agent runs) —
  // context for the record. The conversation itself is the record's substance.
  let briefContent = "";
  try {
    const autoBriefPath = join(RC_ROOT, "journal", `${date}_session_handoff_auto.md`);
    if (existsSync(autoBriefPath)) briefContent = readFileSync(autoBriefPath, "utf8");
  } catch {
    // Cannot read brief — proceed without
  }
  if (!conversationText && !briefContent) return null;

  const payload = {
    session_id: sessionId,
    conversation: conversationText,
    brief_content: briefContent,
    enrich: fullRun,
  };

  // ── Try dashboard API first ────────────────────────────────────────────────
  try {
    const res = await fetch(`${DASHBOARD_URL}/api/session/consolidate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(10000),
    });
    if (res.ok) return await res.json().catch(() => ({}));
  } catch {
    // Dashboard not running — fall through to Python fallback
  }

  // ── Python fallback: write directly to SQLite without the dashboard ────────
  const payloadFile = join(sessionDir, `.consolidate-${sid8}.json`);
  try {
    const { spawnSync } = await import("child_process");
    const metisVenv = process.env.METIS_MCP_VENV
      || join(process.env.HOME || "/home", ".local", "share", "metis-mcp", ".venv");
    const python = join(metisVenv, "bin", "python3");
    const script = join(RC_ROOT, "system", "mcp-server", "src", "metis_mcp", "_consolidate_session.py");
    mkdirSync(sessionDir, { recursive: true });
    writeFileSync(payloadFile, JSON.stringify(payload));
    spawnSync(python, [script, RC_ROOT, "--payload", payloadFile], { timeout: 12000 });
  } catch {
    // Python also unavailable — silent
  } finally {
    try { if (existsSync(payloadFile)) unlinkSync(payloadFile); } catch {}
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

(async () => {
  if (fullRun) {
    // The handoff brief FIRST: consolidation reads the file it writes. Run side
    // by side, consolidation read the previous version of the brief.
    const [result] = await Promise.all([
      tryDashboardHandoff(),
      touchPlanningFiles(),
      notifyProjectActivity(),
    ]);
    writeMarker(result);
  }
  await consolidateSession();
  saveState();
  process.exit(0);
})();
