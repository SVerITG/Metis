#!/usr/bin/env node
/**
 * Metis Stop hook — check the citations in the reply that was just produced.
 *
 * WHY THIS EXISTS
 *   Metis' grounding promise has two halves. `user-prompt-submit.mjs` enforces
 *   the first: the corpus IS searched before an answer, whether or not the model
 *   would have thought to look. Nothing enforced the second — that what the
 *   answer then SAYS is actually in those passages.
 *
 *   Everything on that side was a convention. `constitution.md` carries
 *   `no-hallucination` and `cite-sources`, but only as text prepended to deep and
 *   chain runs. The Critic agent has to be remembered. Six agent prompts say
 *   "do not hallucinate".
 *
 *   A control that depends on being remembered is not a control. This hook is
 *   the output-side counterpart of the prompt hook: it runs on every turn, and
 *   the model does not get to decide whether it runs.
 *
 * IT RECORDS. IT DOES NOT BLOCK.
 *   By default a verdict goes to the citation ledger and nothing interrupts the
 *   conversation. That is deliberate:
 *
 *     · a wrong claim in chat is cheap — the next sentence corrects it;
 *     · a false "unverified" warning is expensive, because it trains the reader
 *       to ignore the whole layer (the same lesson as the permanently-wrong
 *       user-config check found on 2026-08-24);
 *     · anything that visibly slows every turn gets switched off within a week,
 *       and then nothing is verified at all.
 *
 *   The expensive case — a claim written into a course, a manuscript, or
 *   outputs/ — is gated properly and separately by tools/verify_citations.py,
 *   which exits non-zero.
 *
 *   METIS_VERIFY_BLOCK=1 turns the hard failures into a block, so the model is
 *   told to fix a fabricated page reference before the researcher ever sees it. Off by
 *   default because a citation extractor is a heuristic and blocking on a
 *   heuristic is how you teach someone to disable a safety feature.
 *
 * Hook input  (stdin) : JSON { session_id, transcript_path, stop_hook_active }
 * Hook output (stdout): nothing, or a block decision.
 *
 * Disable entirely with METIS_VERIFY_HOOK=0.
 */

import { readFileSync } from "fs";

const PORT = process.env.METIS_PORT || "8080";
const BASE = `http://127.0.0.1:${PORT}`;
const TIMEOUT_MS = 3500;      // worst case is what matters — this runs every turn
const BLOCK = process.env.METIS_VERIFY_BLOCK === "1";

function quit() { process.exit(0); }

/** Only pay for the HTTP call when the reply actually contains a citation. */
function looksCitational(text) {
  if (!text || text.length < 40) return false;
  return /\b10\.\d{4,9}\//.test(text)          // a DOI
      || /\bpp?\.\s?\d{1,4}\b/.test(text);     // a page reference
}

/**
 * The last assistant message in the transcript.
 *
 * Read from the END. A long session's transcript is large, and this hook has a
 * few hundred milliseconds; parsing every line to find the last one would make
 * the cost grow with session length — exactly the kind of quiet slowdown that
 * gets a hook disabled.
 */
function lastAssistantText(transcriptPath) {
  let raw;
  try {
    raw = readFileSync(transcriptPath, "utf8");
  } catch {
    return "";
  }
  const lines = raw.split("\n");
  for (let i = lines.length - 1; i >= 0 && i > lines.length - 400; i--) {
    const line = lines[i].trim();
    if (!line) continue;
    let msg;
    try {
      msg = JSON.parse(line);
    } catch {
      continue;
    }
    const m = msg?.message ?? msg;
    if (m?.role !== "assistant") continue;
    const content = m.content;
    if (typeof content === "string") return content;
    if (Array.isArray(content)) {
      const text = content
        .filter((b) => b?.type === "text" && typeof b.text === "string")
        .map((b) => b.text)
        .join("\n");
      if (text.trim()) return text;
    }
  }
  return "";
}

async function main() {
  if (process.env.METIS_VERIFY_HOOK === "0") quit();

  let input = {};
  try {
    const raw = readFileSync(0, "utf8");
    if (raw.trim()) input = JSON.parse(raw);
  } catch {
    quit();
  }

  // Never re-enter our own block. Without this the block path can loop.
  if (input.stop_hook_active) quit();

  const transcript = input.transcript_path || "";
  if (!transcript) quit();

  const text = lastAssistantText(transcript);
  if (!looksCitational(text)) quit();

  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  let data = null;
  try {
    const r = await fetch(`${BASE}/api/verify/turn`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        text,
        session_id: input.session_id || "",
      }),
      signal: ctl.signal,
    });
    if (r.ok) data = await r.json();
  } catch {
    quit();                    // dashboard down or slow — stay silent, stay fast
  } finally {
    clearTimeout(t);
  }

  if (!data || !data.ok || !data.hard_failures) quit();

  if (!BLOCK) quit();          // recorded to the ledger; that is the default

  const bad = (data.results || []).filter((r) => r.hard).slice(0, 5);
  const detail = bad
    .map((r) => `· ${r.verdict}: ${r.source || r.doi || "?"}${r.page ? ` p.${r.page}` : ""} — ${r.detail}`)
    .join("\n");

  process.stdout.write(JSON.stringify({
    decision: "block",
    reason:
      `Citation check failed on ${data.hard_failures} citation(s) in that reply. ` +
      `These were verified deterministically against the indexed corpus — the ` +
      `cited page does not contain what was claimed:\n\n${detail}\n\n` +
      `Correct or remove those citations. If the figure is right but the page ` +
      `reference is wrong, find the real page with search_pdf_knowledge. Do not ` +
      `re-state the citation unchanged.`,
  }));
  process.exit(0);
}

main().catch(() => process.exit(0));
