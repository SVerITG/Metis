/**
 * What a Claude Code session was ABOUT — read from its own transcript.
 *
 * The session hooks used to record the dashboard's view of the day (projects,
 * tasks, tool counts) and never what was discussed: Claude Code hands every
 * hook a `transcript_path`, and nothing read it. So "what did we decide about
 * X?" could only be answered when the model had remembered to log the session
 * itself. This module turns the transcript into a short, plain record: what
 * the researcher asked, and where the last answer landed.
 *
 * It also honours the researcher's standing rule — every conversation is
 * tracked unless they explicitly say not to. A prompt such as "don't track
 * this" or "off the record" marks the session opted out, and nothing of it is
 * recorded. METIS_TRACK_SESSIONS=0 turns capture off entirely.
 */

import { readFileSync, existsSync } from "fs";

const MAX_PROMPTS = 12;
const PROMPT_CHARS = 300;
const REPLY_CHARS = 1500;

// Narrow on purpose: a false match silently drops a session from memory, so
// "don't log it to the console" or "untracked files" must not count.
const OPT_OUT = [
  /\b(?:don['’]?t|do not|please don['’]?t|no need to)\s+(?:track|record)\s+(?:this|me|(?:this|the|our)\s+(?:conversation|chat|session))\b/i,
  /\b(?:don['’]?t|do not)\s+(?:track|record|log)\s+(?:this|the|our)\s+(?:conversation|chat|session)\b/i,
  /\boff the record\b/i,
  /\b(?:dit|deze)\s+(?:gesprek|sessie|chat)\s+niet\s+(?:bijhouden|opslaan|loggen|tracken)\b/i,
  /\bniet\s+(?:bijhouden|tracken)\b/i,
];

/** Local calendar date and HH-MM, matching the dashboard's datetime.date.today(). */
export function localStamp(d = new Date()) {
  const p = (n) => String(n).padStart(2, "0");
  return {
    date: `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`,
    time: `${p(d.getHours())}-${p(d.getMinutes())}`,
    iso: `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`,
  };
}

export function trackingDisabled() {
  return (process.env.METIS_TRACK_SESSIONS || "1") === "0";
}

function textOf(content) {
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  return content
    .filter((b) => b && b.type === "text" && typeof b.text === "string")
    .map((b) => b.text)
    .join("\n");
}

function clip(s, n) {
  const t = s.replace(/\s+/g, " ").trim();
  return t.length > n ? t.slice(0, n - 1) + "…" : t;
}

/**
 * Read a transcript. Returns { prompts, lastReply, optOut, turns } — or null
 * when there is no readable transcript.
 */
export function readConversation(transcriptPath) {
  if (!transcriptPath || !existsSync(transcriptPath)) return null;
  let raw;
  try {
    raw = readFileSync(transcriptPath, "utf8");
  } catch {
    return null;
  }
  const prompts = [];
  let lastReply = "";
  let optOut = false;
  let turns = 0;
  for (const line of raw.split("\n")) {
    if (!line.trim()) continue;
    let ev;
    try {
      ev = JSON.parse(line);
    } catch {
      continue;
    }
    if (ev.isMeta || ev.isSidechain) continue;
    const msg = ev.message || {};
    if (ev.type === "user") {
      const text = textOf(msg.content).trim();
      // Tool results, slash-command wrappers and system notices are not prompts.
      if (!text || text.startsWith("<")) continue;
      turns += 1;
      if (OPT_OUT.some((re) => re.test(text))) optOut = true;
      prompts.push(text);
    } else if (ev.type === "assistant") {
      const text = textOf(msg.content).trim();
      if (text) lastReply = text;
    }
  }
  return {
    prompts: prompts.slice(-MAX_PROMPTS).map((p) => clip(p, PROMPT_CHARS)),
    firstPrompt: prompts.length ? clip(prompts[0], PROMPT_CHARS) : "",
    lastReply: clip(lastReply, REPLY_CHARS),
    optOut,
    turns,
  };
}

/** The conversation as a short markdown record for session memory. */
export function formatConversation(conv) {
  if (!conv || !conv.turns) return "";
  const lines = [`## What was discussed (${conv.turns} message${conv.turns === 1 ? "" : "s"})`];
  const shown = conv.prompts;
  if (conv.turns > shown.length && conv.firstPrompt) {
    lines.push(`- Started with: ${conv.firstPrompt}`);
    lines.push(`- …`);
  }
  for (const p of shown) lines.push(`- ${p}`);
  if (conv.lastReply) {
    lines.push("", "## Where it ended", conv.lastReply);
  }
  return lines.join("\n");
}
