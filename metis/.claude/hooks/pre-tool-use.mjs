#!/usr/bin/env node
/**
 * Metis pre-tool-use security hook
 *
 * Fires before WebFetch, WebSearch, Bash, Write, and Edit tool calls.
 * Inspects the action and warns the user when potentially sensitive operations
 * are detected. Does NOT silently block — shows a clear warning so the user
 * can make an informed decision.
 *
 * Hook input (stdin): JSON { tool_name, tool_input }
 * Hook output (stdout): JSON { decision: "allow"|"block", reason?: string }
 */

import { readFileSync } from "fs";

const RC_ROOT = process.env.METIS_RC_ROOT ||
  "C:/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/Research Cortex/metis";

// ─── Sensitive path patterns ───────────────────────────────────────────────
const SENSITIVE_PATH_PATTERNS = [
  /05_sources\/literature/i,
  /patient/i,
  /individual.level/i,
  /\.rds$/i,
  /\.RData$/i,
  /metis\.sqlite$/i,
  /00_inbox\/.+\.(csv|xlsx|xls)$/i,
];

// ─── Domain allowlist ──────────────────────────────────────────────────────
const ALLOWED_DOMAINS = [
  "pubmed.ncbi.nlm.nih.gov",
  "scholar.google.com",
  "arxiv.org",
  "biorxiv.org",
  "medrxiv.org",
  "who.int",
  "github.com",
  "raw.githubusercontent.com",
  "api.anthropic.com",
  "cran.r-project.org",
  "pypi.org",
  "rss.ncbi.nlm.nih.gov",
  "feeds.bbci.co.uk",
  "reuters.com",
  "reliefweb.int",
  "dndi.org",
  "msf.org",
];

// ─── Prompt injection patterns ─────────────────────────────────────────────
const INJECTION_PATTERNS = [
  /ignore (all |previous )?instructions/i,
  /you are now/i,
  /jailbreak/i,
  /system prompt/i,
  /act as (a |an )?(?!assistant|librarian|metis)/i,
  /forget (all |your )?previous/i,
  /\[system\]/i,
  /override (safety|constraints|rules)/i,
];

// ─── Helpers ────────────────────────────────────────────────────────────────
function extractDomain(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

function isSensitivePath(path) {
  return SENSITIVE_PATH_PATTERNS.some((p) => p.test(path));
}

function containsInjection(text) {
  return INJECTION_PATTERNS.some((p) => p.test(text));
}

function warn(message) {
  process.stderr.write(`\n⚠️  [Metis Security] ${message}\n`);
}

// ─── Main ───────────────────────────────────────────────────────────────────
let input;
try {
  const raw = readFileSync("/dev/stdin", "utf8");
  input = JSON.parse(raw);
} catch {
  // If we can't read input, allow the tool to proceed
  console.log(JSON.stringify({ decision: "allow" }));
  process.exit(0);
}

const { tool_name, tool_input } = input;
let decision = "allow";
let reason = null;

// ── WebFetch / WebSearch ───────────────────────────────────────────────────
if (tool_name === "WebFetch" || tool_name === "WebSearch") {
  const url = tool_input?.url || tool_input?.query || "";

  // Check for prompt injection in the URL/query
  if (containsInjection(url)) {
    decision = "block";
    reason = `Potential prompt injection detected in ${tool_name} input: "${url.slice(0, 80)}..."`;
    warn(`BLOCKED — prompt injection pattern in ${tool_name}: ${url.slice(0, 80)}`);
  } else if (tool_name === "WebFetch") {
    const domain = extractDomain(url);
    if (domain) {
      const allowed = ALLOWED_DOMAINS.some(
        (d) => domain === d || domain.endsWith("." + d)
      );
      if (!allowed) {
        warn(
          `Domain not on allowlist: ${domain}\n` +
          `  URL: ${url}\n` +
          `  If this is expected, you can proceed. Add to allowlist in .claude/hooks/pre-tool-use.mjs if needed.`
        );
        // Warn but allow — user can see the warning and stop if needed
      }
    }
  }
}

// ── Write / Edit — check for sensitive paths ───────────────────────────────
if (tool_name === "Write" || tool_name === "Edit") {
  const filePath = tool_input?.file_path || "";
  if (isSensitivePath(filePath)) {
    warn(
      `Writing to a potentially sensitive path: ${filePath}\n` +
      `  This path may contain patient data or protected research files.\n` +
      `  Proceeding — review the write operation carefully.`
    );
  }
}

// ── Bash — check for external network commands ─────────────────────────────
if (tool_name === "Bash") {
  const cmd = tool_input?.command || "";

  // Flag outbound network calls
  if (/\b(curl|wget|http|https|ftp)\b/.test(cmd)) {
    warn(
      `Bash command contains a network call:\n  ${cmd.slice(0, 120)}\n` +
      `  Cybersecurity review: confirm this destination is expected.`
    );
  }

  // Flag attempts to read or transmit sensitive files
  if (isSensitivePath(cmd)) {
    warn(
      `Bash command references a sensitive path:\n  ${cmd.slice(0, 120)}\n` +
      `  Data Guardian review: confirm no patient/individual-level data is being transmitted.`
    );
  }

  // Flag rm -rf or destructive ops in RC root
  if (/rm\s+-[rf]+/.test(cmd) && cmd.includes("metis")) {
    decision = "block";
    reason = `Destructive rm command targeting RC root detected: ${cmd.slice(0, 120)}`;
    warn(`BLOCKED — destructive rm in RC root: ${cmd.slice(0, 80)}`);
  }
}

// ── WebSearch — check fetched content for injection ───────────────────────
// (content scanning happens post-fetch; flag the query itself)
if (tool_name === "WebSearch") {
  const query = tool_input?.query || "";
  if (containsInjection(query)) {
    decision = "block";
    reason = `Prompt injection pattern detected in search query: "${query.slice(0, 80)}"`;
    warn(`BLOCKED — injection in WebSearch query: ${query.slice(0, 80)}`);
  }
}

// ─── Output ─────────────────────────────────────────────────────────────────
const output = { decision };
if (reason) output.reason = reason;
console.log(JSON.stringify(output));
