#!/usr/bin/env node
/**
 * Metis pre-tool-use security hook
 *
 * Fires before WebFetch, WebSearch, Bash, Write, Edit, Read, and the MCP
 * read_file tool. Inspects the action and warns — or, for a file that looks
 * like it holds individual-level data, asks the user to confirm — so sensitive
 * data is not loaded into the conversation by accident.
 *
 * For Read / read_file it peeks at the file's HEADER locally (the read happens
 * on this machine, nothing leaves it) and checks the column names + a small
 * sample for sensitive patterns. Only matched column *names* (schema) and a
 * generic PII flag are ever reported — never the data values themselves.
 *
 * Hook input (stdin): JSON { tool_name, tool_input }
 * Hook output (stdout): JSON { ...permissionDecision: "allow"|"deny"|"ask" }
 */

import { readFileSync, writeFileSync, existsSync, openSync, readSync, closeSync } from "fs";

const RC_ROOT = process.env.METIS_RC_ROOT || "";

// ─── Hook profile ──────────────────────────────────────────────────────────
// Set METIS_HOOK_PROFILE=minimal for speed (domain allowlist only; no file scan).
// Set METIS_HOOK_PROFILE=full for strictest checks (adds PII-indicative filename warns).
// Default: standard — includes sensitive-data file-content scanning on Read/read_file.
const HOOK_PROFILE = (process.env.METIS_HOOK_PROFILE || "standard").toLowerCase();

// ─── Sensitive path patterns ───────────────────────────────────────────────
// Updated 2026-05-05: refer to current folder layout (knowledge/library, inbox).
const SENSITIVE_PATH_PATTERNS = [
  /knowledge\/library\/disease-areas/i,
  /knowledge\/library\/people-organizations/i,
  /\bpatient\b/i,
  /\bindividual.level\b/i,
  /\.rds$/i,
  /\.RData$/i,
  /metis\.sqlite$/i,
  /\binbox\/.+\.(csv|xlsx|xls)$/i,
  /\boutputs\/reviews\/data-guardian\//i,
];

// ─── Domain allowlist ──────────────────────────────────────────────────────
const ALLOWED_DOMAINS = [
  "pubmed.ncbi.nlm.nih.gov",
  "scholar.google.com",
  "arxiv.org",
  "biorxiv.org",
  "medrxiv.org",
  "who.int",
  "ecdc.europa.eu",
  "cdc.gov",
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
  "doi.org",
  "crossref.org",
  "zotero.org",
  "api.zotero.org",
];

// ─── Prompt injection patterns ─────────────────────────────────────────────
// Mirrors metis/system/mcp-server/src/metis_mcp/tools/guardrails.py — keep in sync.
const INJECTION_PATTERNS = [
  /ignore\s+(all\s+)?previous\s+instructions?/i,
  /disregard\s+(all\s+)?instructions?/i,
  /you\s+are\s+now\s+a\s+/i,
  /act\s+as\s+(if\s+you\s+(were|are)\s+)?a\s+/i,
  /forget\s+(everything|all)\s+/i,
  /new\s+instructions?\s*:/i,
  /system\s+prompt\s*:/i,
  /<\s*\/?system\s*>/i,
  /\[INST\]|\[\/INST\]/i,
  /print\s+your\s+(system\s+)?prompt/i,
  /reveal\s+(your\s+)?(system\s+)?instructions?/i,
  /override\s+(safety|constraints|rules)/i,
  /jailbreak/i,
];

// ─── Sensitive-data file scanning ──────────────────────────────────────────
// Mirrors metis/system/mcp-server/src/metis_mcp/tools/safety.py — keep in sync.
// Text data formats we can peek into; binary formats we flag by extension only.
const DATA_TEXT_EXT = new Set(["csv", "tsv", "tab", "psv", "txt"]);
const DATA_BINARY_EXT = new Set(["xlsx", "xls", "sav", "dta", "rds", "rdata"]);

const SENSITIVE_COLUMNS = new Set([
  "patient", "patient_id", "case_id", "diagnosis", "dob", "date_of_birth",
  "test_result", "gps_lat", "gps_lon", "nom", "prenom", "prénom", "surname",
  "firstname", "first_name", "last_name", "mrn", "record_number", "dossier",
  "passport_number", "nid", "national_id", "hat_case_id", "hat_patient_id",
]);

// Content-level PII patterns (subset of safety.py — the high-signal ones).
const PII_PATTERNS = [
  /\b(?:patient_?id|case_?id|patient\s*#)\s*[:=]?\s*\d+/i,
  /-?\d{1,3}\.\d{5,},?\s*-?\d{1,3}\.\d{5,}/,                       // high-precision GPS
  /\bhat[\s_-]?(?:case|id|patient|dossier)\s*[:=]?\s*[\dA-Z\-]{3,20}\b/i,
  /\b\d{16}\b/,                                                    // DRC national ID
  /\b(?:nom|prenom|prénom|surname|firstname|last[\s_]name)\s*[:=]\s*[A-Za-zÀ-ÿ]{2,}/i,
];

// Read only the first chunk of a file (local I/O — never sent anywhere).
function readHead(path, maxBytes = 8192) {
  let fd;
  try {
    fd = openSync(path, "r");
    const buf = Buffer.alloc(maxBytes);
    const n = readSync(fd, buf, 0, maxBytes, 0);
    return buf.subarray(0, n).toString("utf8");
  } catch {
    return null;
  } finally {
    try { if (fd !== undefined) closeSync(fd); } catch { /* ignore */ }
  }
}

// Returns { isData, isBinary, sensitiveCols:[], piiHit:bool }. Only the matched
// column NAMES (from the fixed vocabulary) and a boolean ever leave this function.
function scanDataFile(filePath) {
  const ext = (filePath.split(".").pop() || "").toLowerCase();
  if (DATA_BINARY_EXT.has(ext)) return { isData: true, isBinary: true, sensitiveCols: [], piiHit: false };
  if (!DATA_TEXT_EXT.has(ext)) return { isData: false };

  const head = readHead(filePath);
  if (!head) return { isData: true, isBinary: false, sensitiveCols: [], piiHit: false };

  const firstLine = head.split(/\r?\n/)[0] || "";
  const sensitiveCols = [];
  for (const sep of [",", "\t", ";", "|"]) {
    if (firstLine.includes(sep)) {
      for (let h of firstLine.split(sep)) {
        h = h.trim().replace(/^["']|["']$/g, "").toLowerCase();
        if (SENSITIVE_COLUMNS.has(h)) sensitiveCols.push(h);
      }
      if (sensitiveCols.length) break;
    }
  }
  const piiHit = PII_PATTERNS.some((p) => p.test(head));
  return { isData: true, isBinary: false, sensitiveCols: [...new Set(sensitiveCols)], piiHit };
}

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
  console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "allow" } }));
  process.exit(0);
}

const { tool_name, tool_input } = input;
let decision = "allow";
let reason = null;

// ── Minimal profile: domain allowlist check only, return early ─────────────
if (HOOK_PROFILE === "minimal") {
  if (tool_name === "WebFetch") {
    const domain = extractDomain(tool_input?.url || "");
    if (domain) {
      const allowed = ALLOWED_DOMAINS.some(
        (d) => domain === d || domain.endsWith("." + d)
      );
      if (!allowed) {
        warn(`Domain not on allowlist: ${domain} (minimal profile)`);
      }
    }
  }
  console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "allow" } }));
  process.exit(0);
}

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

// ── Read / read_file: scan the file's CONTENT for sensitive data ───────────
// Runs for standard + full profiles. The file is read locally (nothing leaves
// the machine); if it looks like individual-level data, we ASK before loading
// it into the conversation and point the user at /safe-analysis.
if (HOOK_PROFILE !== "minimal" && (tool_name === "Read" || /read_file$/i.test(tool_name))) {
  const filePath = tool_input?.file_path || tool_input?.path || "";
  if (filePath) {
    const r = scanDataFile(filePath);
    if (r.isData && (r.sensitiveCols.length || r.piiHit)) {
      decision = "ask";
      const cols = r.sensitiveCols.length ? ` Sensitive columns: ${r.sensitiveCols.join(", ")}.` : "";
      reason =
        `This file looks like it holds individual-level / sensitive data.${cols} ` +
        `Reading it loads that data into the conversation, which is sent to Claude. ` +
        `Prefer /safe-analysis — Metis writes a local script so only metadata ` +
        `(column names, counts, summaries) is shared. Proceed only if this file is non-identifiable.`;
      warn(
        `Sensitive data file about to be read: ${filePath}${cols}\n` +
        `  → Consider /safe-analysis (send code, not data). Confirm to proceed.`
      );
    } else if (r.isData && r.isBinary) {
      warn(
        `Reading a data file: ${filePath}\n` +
        `  Binary format — contents not scanned. If it holds identifiers, prefer /safe-analysis.`
      );
    }
  }
}

// ── Session-level injection counter ─────────────────────────────────────────
// Track how many times each pattern fires in this process lifetime.
// Stored at /tmp/metis-injection-session.json (survives across tool calls in same session).
if (HOOK_PROFILE !== "minimal") {
  const counterFile = "/tmp/metis-injection-session.json";
  const inputText = JSON.stringify(tool_input || {});
  let firedPatterns = [];
  for (const pattern of INJECTION_PATTERNS) {
    if (pattern.test(inputText)) firedPatterns.push(pattern.source);
  }
  if (firedPatterns.length > 0) {
    let counts = {};
    try {
      if (existsSync(counterFile)) {
        counts = JSON.parse(readFileSync(counterFile, "utf8"));
      }
    } catch { /* start fresh */ }
    for (const p of firedPatterns) {
      counts[p] = (counts[p] || 0) + 1;
      if (counts[p] >= 3 && decision !== "block") {
        decision = "block";
        reason = `Repeated injection pattern (${counts[p]}x in session): "${p.slice(0, 60)}"`;
        warn(`BLOCKED — repeated injection (${counts[p]}x): ${p.slice(0, 60)}`);
      }
    }
    try { writeFileSync(counterFile, JSON.stringify(counts)); } catch { /* silent */ }
  }
}

// ─── Output ─────────────────────────────────────────────────────────────────
const permissionDecision =
  decision === "block" ? "deny" : decision === "ask" ? "ask" : "allow";
const output = {
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision,
    ...(reason ? { permissionDecisionReason: reason } : {}),
  },
};
console.log(JSON.stringify(output));
process.exit(0);
