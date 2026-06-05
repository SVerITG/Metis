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

const RC_ROOT = process.env.METIS_RC_ROOT || process.cwd();
const HOOK_PROFILE = (process.env.METIS_HOOK_PROFILE || "standard").toLowerCase();

// Minimal profile: skip session logging entirely
if (HOOK_PROFILE === "minimal") process.exit(0);

let input;
try {
  input = JSON.parse(readFileSync("/dev/stdin", "utf8"));
} catch {
  process.exit(0);
}

// ── Output PII scan (standard + full profiles) ──────────────────────────────
// Scan tool results for high-confidence PII patterns and log findings.
if (HOOK_PROFILE !== "minimal") {
  const toolResult = JSON.stringify(input?.tool_response || "");
  const PII_PATTERNS = [
    { label: "email",       re: /\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-z]{2,}\b/ },
    { label: "phone",       re: /\b(\+?32|0)\s?[1-9][0-9\s\-]{6,10}\b/ },
    { label: "patient-id",  re: /\b(patient|participant|case|subject)[_\s-]?[0-9]{2,8}\b/i },
    { label: "api-key",     re: /\b(sk-ant-[a-zA-Z0-9\-]{20,}|ZOTERO_API_KEY\s*=\s*\S+)\b/ },
  ];
  for (const { label, re } of PII_PATTERNS) {
    if (re.test(toolResult)) {
      process.stderr.write(
        `\n⚠️  [Metis Security] Output PII detected (${label}) in result from ${input?.tool_name || "tool"}.\n` +
        `   Run /security-scan to review. No data has been transmitted.\n`
      );
      // Log to session counter file so /security-scan can report it
      try {
        const { existsSync, readFileSync: rf, writeFileSync: wf } = await import("fs");
        const f = "/tmp/metis-injection-session.json";
        let counts = existsSync(f) ? JSON.parse(rf(f, "utf8")) : {};
        counts[`pii-${label}`] = (counts[`pii-${label}`] || 0) + 1;
        wf(f, JSON.stringify(counts));
      } catch { /* silent */ }
    }
  }
}

// ── Post-edit syntax check (standard + full) — the cheapest working-loop signal ─
// After an Edit/Write to a code file, run a fast syntax check on JUST that file and
// surface any error immediately. Non-blocking (warn only). Implements the in-the-
// moment "run the external signal, don't trust the edit" discipline — a broken edit
// should never sit silently. (Research: LLMs can't be trusted to self-judge code
// without an external signal — Huang et al. 2310.01798.)
if (HOOK_PROFILE !== "minimal" && (input?.tool_name === "Edit" || input?.tool_name === "Write")) {
  const fp = input?.tool_input?.file_path || "";
  try {
    const { execFileSync } = await import("child_process");
    const { existsSync } = await import("fs");
    const run = (cmd, args) => {
      try { execFileSync(cmd, args, { stdio: "pipe", timeout: 8000 }); return null; }
      catch (e) { return ((e.stderr && e.stderr.toString()) || e.message || "").slice(0, 400); }
    };
    let err = null, kind = null;
    if (/\.py$/.test(fp)) {
      kind = "py_compile";
      const venvPy = `${process.env.HOME || ""}/.local/share/metis-mcp/.venv/bin/python`;
      err = run(existsSync(venvPy) ? venvPy : "python3", ["-m", "py_compile", fp]);
    } else if (/\.sh$/.test(fp)) {
      kind = "bash -n"; err = run("bash", ["-n", fp]);
    } else if (/\.(mjs|js)$/.test(fp)) {
      kind = "node --check"; err = run("node", ["--check", fp]);
    }
    if (err) {
      process.stderr.write(
        `\n⚠️  [Metis Verify] ${kind} FAILED after editing ${fp}:\n${err}\n   Fix this before continuing — the edit is broken.\n`
      );
    }
  } catch { /* never block the session */ }
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
