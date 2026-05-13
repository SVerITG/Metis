#!/usr/bin/env node
/**
 * Metis pre-compact hook — saves a working state snapshot before context compaction.
 *
 * Claude compresses the conversation context when it gets long. This loses the
 * working thread — what was being built, what the last tool results were, what
 * decisions were just made. This hook captures a lightweight snapshot so the
 * next turn can start oriented.
 *
 * Snapshot location:
 *   <RC_ROOT>/journal/sessions/pre-compact-<YYYY-MM-DD>-<HH-MM>.md
 *
 * Hook input (stdin): JSON { summary?: string, turns?: number }
 * This hook never blocks.
 */

import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { join } from "path";

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

  const snapshot = [
    `# Pre-compact snapshot — ${now.toISOString()}`,
    `Turns before compaction: ${turns}`,
    ``,
    `## Context summary at compaction`,
    summary,
    ``,
    `---`,
    `*This file was written automatically before Claude compressed its conversation context.*`,
    `*If the session continues and context was lost, read this file to re-orient.*`,
    ``,
  ].join("\n");

  const dir = join(RC_ROOT, "journal", "sessions");
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, `pre-compact-${date}-${timeSlug}.md`), snapshot);
} catch {
  // Silent
}

process.exit(0);
