#!/usr/bin/env node
/**
 * Metis UserPromptSubmit hook — ground domain questions in the researcher's own
 * corpus BEFORE the model answers.
 *
 * WHY THIS EXISTS
 *   Metis had 220 indexed documents of the researcher's own literature and no
 *   way of guaranteeing they were ever consulted. `search_pdf_knowledge` is a
 *   tool the model may choose to call — and a capability that depends on being
 *   remembered is a convention, not a mechanism. The same failure shape as
 *   `scan_library_feeds()` having no scheduled caller: the code was fine, and
 *   nothing ran it.
 *
 *   This hook makes consultation structural. On every prompt that looks like a
 *   domain question, it searches the corpus and injects the passages as context.
 *   The model then answers with the researcher's own literature in front of it,
 *   whether or not it would have thought to look.
 *
 * WHAT IT IS CAREFUL ABOUT
 *   · SPEED. It calls the running dashboard, where the 263 MB embedding model is
 *     already warm. A Node hook shelling out to Python would reload that model on
 *     every prompt. Hard timeout, and silence if the dashboard is not up.
 *   · HONESTY. It reports how many documents were searched and what came back,
 *     and explicitly instructs that this is a top-k similarity search — never
 *     "the whole library". Overclaiming provenance is worse than none.
 *   · RELEVANCE. A score floor server-side means "nothing relevant" is a real
 *     answer. Injecting the six least-bad passages for an unrelated question
 *     makes irrelevant papers look like evidence.
 *   · PORTABILITY. Trigger terms are DERIVED from the user's profile, topics and
 *     the domains present in their own corpus — fetched from the dashboard, not
 *     hard-coded. A list naming trypanosomes would be useless to anyone else.
 *
 * Hook input  (stdin) : JSON { prompt, session_id, ... }
 * Hook output (stdout): JSON { hookSpecificOutput: { additionalContext } }
 *
 * Disable with METIS_CORPUS_HOOK=0.
 */

import { readFileSync, existsSync, writeFileSync, mkdirSync } from "fs";
import { join } from "path";

const PORT = process.env.METIS_PORT || "8080";
const BASE = `http://127.0.0.1:${PORT}`;
const RC_ROOT = process.env.METIS_RC_ROOT || process.env.CLAUDE_PROJECT_DIR || "";
const CACHE_DIR = join(RC_ROOT || "/tmp", "system", "config");
const TRIGGER_CACHE = join(CACHE_DIR, ".corpus-triggers.json");

// Budgets. The hook runs on EVERY prompt, so its worst case is what matters,
// not its average. Better to skip grounding than to make the assistant feel slow.
const TRIGGER_TIMEOUT_MS = 1500;
const SEARCH_TIMEOUT_MS  = 4000;
const TRIGGER_TTL_MS     = 6 * 60 * 60 * 1000;   // re-derive twice a day

/* Work ON Metis, recognised by vocabulary. Module scope because BOTH the
   per-prompt filter and the session-stickiness marker need it. */
const IS_SYSTEM_WORK = /\b(metis|dashboards?|mcp|subagents?|hooks?|repos?|repositor(?:y|ies)|venvs?|sqlite|backfills?|pytest|reinstalls?|reconnects?|changelogs?|claude|uvicorn|fastapi|htmx|hand[ -]?offs?|css|stylesheets?|styling|templates?|partials?|front[- ]?end|backlogs?|artifacts?|screenshots?|sparklines?|codebase|\bui\b|\bux\b)\b/;

/* ── Session stickiness ───────────────────────────────────────────────────
   the researcher, 2026-08-28: "When we are working on metis you do not have to route
   through the library if not indicated specifically."

   Word-matching a single prompt cannot implement that, because a follow-up
   inside a session about Metis carries none of the vocabulary. "Where can I
   find the seven approved patterns?" and "build me mockups for all the
   proposals" are both plainly about this repo and both contain nothing to
   match on — the first grounded in WHO guideline-development procedure, the
   second in Bayesian model comparison.

   So the session remembers. Once any prompt is recognised as work ON Metis,
   grounding stays off for the rest of that session unless a later prompt asks
   for the library in so many words. State is one small file per session id in
   /tmp, which the OS clears; a missing or unreadable file simply means "not
   sticky yet" and the hook behaves as before.
   ──────────────────────────────────────────────────────────────────────── */
const STICKY_DIR = "/tmp/metis-corpus-hook";

function stickyPath(sessionId) {
  const safe = String(sessionId || "").replace(/[^A-Za-z0-9_-]/g, "").slice(0, 64);
  return safe ? join(STICKY_DIR, `${safe}.system`) : "";
}

function isSystemSession(sessionId) {
  const f = stickyPath(sessionId);
  return !!f && existsSync(f);
}

function markSystemSession(sessionId) {
  const f = stickyPath(sessionId);
  if (!f) return;
  try {
    mkdirSync(STICKY_DIR, { recursive: true });
    writeFileSync(f, new Date().toISOString());
  } catch { /* best effort — losing the marker only restores the old behaviour */ }
}

/* An explicit request for the library overrides the sticky flag, for that one
   prompt only. This is the "if not indicated specifically" half of the rule. */
const ASKS_FOR_LIBRARY =
  /\b(?:my|the|your)\s+(?:librar|corpus|literature|papers|reading|sources)|\bsearch (?:my|the)\b|\bwhat does the (?:literature|evidence|research|corpus)\b|\bevidence (?:for|on|about)\b|\bpapers? (?:on|about)\b|\bcitations?\b|\bindexed\b|\bpubmed\b|\bsystematic review\b|\bground(?:ed)? in\b|\bcheck (?:my|the) (?:librar|corpus)\b/i;

function out(context) {
  if (context) {
    process.stdout.write(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: "UserPromptSubmit",
        additionalContext: context,
      },
    }));
  }
  process.exit(0);
}

async function getJSON(url, ms) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), ms);
  try {
    const r = await fetch(url, { signal: ctl.signal });
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;                    // dashboard down, slow, or busy — stay quiet
  } finally {
    clearTimeout(t);
  }
}

/** Trigger terms, cached on disk so most prompts cost no HTTP call at all. */
async function triggerTerms() {
  try {
    if (existsSync(TRIGGER_CACHE)) {
      const c = JSON.parse(readFileSync(TRIGGER_CACHE, "utf8"));
      if (Date.now() - (c.at || 0) < TRIGGER_TTL_MS && Array.isArray(c.terms)) {
        return c.terms;
      }
    }
  } catch { /* a corrupt cache is not worth failing over */ }

  const d = await getJSON(`${BASE}/api/library/corpus-triggers`, TRIGGER_TIMEOUT_MS);
  const terms = (d && d.terms) || [];
  // NEVER cache an empty list. If the dashboard was still starting when the
  // first prompt arrived, an empty result would be cached for six hours and the
  // hook would silently do nothing for the rest of the day — which is exactly
  // what happened on the first live test.
  if (terms.length) {
    try {
      mkdirSync(CACHE_DIR, { recursive: true });
      writeFileSync(TRIGGER_CACHE, JSON.stringify({ at: Date.now(), terms }));
    } catch { /* cache is an optimisation, never a requirement */ }
  }
  return terms;
}

/** Is this a QUESTION about the researcher's domain, rather than a work order? */
function looksLikeDomainQuestion(prompt, terms) {
  const p = prompt.toLowerCase();

  // Skip operational instructions. "fix the scheduler" mentions no domain term
  // anyway, but "add the tsetse papers to Zotero" does — and grounding that in
  // literature passages helps nobody. Coding verbs are a good negative signal.
  const OPERATIONAL = /\b(commit|push|refactor|rename|delete|install|deploy|restart|debug|stack trace|traceback|npm |pip |git |sql\b|write a script|run the)\b/;
  if (OPERATIONAL.test(p)) return false;

  // Skip work ON Metis itself. The corpus is research literature; grounding a
  // question about the dashboard, the MCP server or this repo in NTD papers
  // helps nobody. Added 2026-08-25 after "what are the decisions to take now?"
  // — a question about this session's open items — was grounded in Bayesian
  // decision analysis, because "decision" is a corpus trigger term.
  //
  // Deliberately NOT in this list: "agent", "session", "endpoint", "database",
  // "control". Each is system vocabulary here but ALSO field vocabulary for
  // this researcher — a trypanocidal agent, a screening session, a primary
  // endpoint, a DHIS2 database, vector control. Blocking them would suppress
  // grounding on real research questions, which is the costlier error.
  // PLURALS. This list was singular-only, and `\bdashboard\b` does not match
  // "dashboards" — the trailing "s" is a word character, so the closing \b
  // never lands. On 2026-08-28 the question "which are the dashboards you are
  // comparing yourself with" was therefore grounded in a DHIS2 manual. It is
  // the same defect as the news-thread alias matcher, where a one-sided \b let
  // "mali" match "malignant": a boundary written without testing the inflected
  // forms. Every term that can take an -s now says so.
  if (IS_SYSTEM_WORK.test(p)) return false;

  // "agent" is Metis vocabulary (one of the 33 specialists) AND field vocabulary
  // (a trypanocidal agent, the causative agent). The word alone settles nothing,
  // so gate on the companions that only ever accompany the Metis sense — leaving
  // "what agents are effective against gambiense HAT?" free to ground.
  const METIS_AGENT = /\bagents?\b[^.?!]*\b(registered|dispatch\w*|routing|route|slug|subagent|specialist|system prompt)\b|\b(registered|dispatch\w*|routing|slug|subagent|specialist)\b[^.?!]*\bagents?\b/;
  if (METIS_AGENT.test(p)) return false;

  // Words that are ordinary English (or generic technical vocabulary) but appear
  // in the corpus-trigger list anyway. The extractor emits raw stopwords — "what",
  // "have" and "hand" are all live triggers — so without this filter ANY question
  // grounds. That is the real defect; this is the guard until the extractor at
  // /api/library/corpus-triggers stops producing them.
  //
  // Dropping a word only means grounding needs a SECOND, more specific term before
  // it fires. A genuine research question almost always supplies one.
  const GENERIC = new Set([
    "about", "above", "activity", "after", "again", "against", "along",
    "already", "also", "although", "always", "among", "amount", "another",
    "answer", "answers", "anyone", "anything", "appear", "applied", "apply",
    "approach", "area", "areas", "around", "aside", "aspect", "available",
    "back", "based", "because", "become", "becomes", "been", "before",
    "begin", "behind", "being", "below", "best", "better", "between",
    "beyond", "both", "bring", "came", "cannot", "carry", "case", "cases",
    "certain", "change", "changes", "clear", "close", "come", "coming",
    "common", "compare", "complete", "consider", "contain", "continue",
    "control", "could", "course", "current", "deal", "decision",
    "decisions", "degree", "describe", "design", "despite", "detail",
    "determine", "develop", "development", "difference", "different",
    "difficult", "direct", "done", "down", "draw", "during", "each",
    "early", "easy", "effect", "either", "else", "enough", "entire",
    "especially", "essential", "even", "event", "ever", "every", "exactly",
    "example", "except", "exist", "expect", "explain", "fact", "fall",
    "field", "form", "forms", "further", "gave", "general", "generally",
    "getting", "give", "given", "goes", "going", "gone", "good", "great",
    "group", "half", "hand", "hands", "happen", "hard", "have", "having",
    "held", "help", "hence", "here", "high", "hold", "home", "however",
    "idea", "important", "include", "included", "includes", "including",
    "increase", "indeed", "information", "inside", "instead", "into",
    "issue", "itself", "just", "keep", "kind", "know", "known", "large",
    "last", "late", "later", "least", "leave", "left", "less", "letting",
    "level", "like", "likely", "limit", "line", "little", "long", "look",
    "made", "main", "major", "make", "making", "management", "many",
    "matter", "maybe", "mean", "means", "measure", "meet", "mention",
    "merely", "might", "model", "models", "month", "months", "more", "most",
    "move", "much", "must", "name", "near", "necessary", "need", "needed",
    "neither", "never", "next", "none", "normal", "note", "noted",
    "nothing", "notice", "number", "occur", "offer", "often", "once",
    "only", "open", "order", "other", "others", "otherwise", "ought",
    "over", "overall", "part", "particular", "particularly", "past",
    "perhaps", "place", "plan", "please", "point", "poor", "position",
    "possible", "present", "previous", "probably", "problem", "program",
    "programme", "project", "provide", "provided", "purpose", "quality",
    "quite", "rate", "rather", "reach", "real", "really", "reason",
    "receive", "recent", "refer", "regard", "relate", "related", "relevant",
    "remain", "remember", "report", "require", "required", "respect",
    "response", "responses", "rest", "result", "results", "return", "right",
    "role", "room", "round", "said", "same", "seem", "seems", "seen",
    "sense", "separate", "series", "serve", "services", "several", "shall",
    "short", "should", "show", "shown", "side", "similar", "simple",
    "simply", "since", "single", "site", "sites", "situation", "small",
    "some", "sometimes", "soon", "sort", "special", "specific", "standard",
    "start", "state", "step", "steps", "still", "stop", "strong", "subject",
    "substantial", "such", "suggest", "support", "suppose", "sure", "take",
    "taken", "tell", "tend", "term", "terms", "test", "than", "that",
    "their", "them", "then", "there", "these", "they", "thing", "things",
    "think", "third", "this", "those", "though", "thought", "three",
    "through", "throughout", "thus", "time", "today", "together", "took",
    "tool", "tools", "total", "toward", "towards", "true", "turn", "twice",
    "type", "under", "unless", "unlike", "until", "upon", "used", "useful",
    "using", "usually", "value", "values", "various", "very", "view",
    "want", "ways", "week", "weeks", "well", "went", "were", "what", "when",
    "where", "whereas", "whether", "which", "while", "whole", "whom",
    "whose", "wide", "will", "with", "within", "without", "word", "words",
    "work", "working", "world", "would", "write", "written", "wrong",
    "year", "years", "yesterday",
  ]);

  // Match on WORD BOUNDARIES, not substrings. `p.includes("cont")` is true of
  // "continue" and `p.includes("area")` of "areas we searched" — short triggers
  // were matching inside unrelated words and inflating the hit count.
  const hits = terms.filter((t) => {
    if (t.length <= 3 || GENERIC.has(t)) return false;
    const esc = t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp(`\\b${esc}\\b`).test(p);
  });
  if (hits.length === 0) return false;

  // One passing mention is not a question about the field. Either ask something
  // (a question mark or an interrogative) or mention the domain more than once.
  const INTERROGATIVE = /\b(what|why|how|which|when|does|do|is|are|can|should|compare|explain|evidence|difference|best|recommend|tell me)\b/;
  return p.includes("?") || INTERROGATIVE.test(p) || hits.length >= 2;
}


/**
 * Does this prompt ask for a QUANTITY?
 *
 * A question like "what is the specificity of CATT" needs something the passage
 * injection below cannot give: the SPREAD across sources. This corpus holds
 * specificity estimates from 59% to 100%, so six top-k passages are six samples
 * from a distribution, and an answer built from them reads as one settled number.
 *
 * Detecting this lexically and telling the model to run `weigh_evidence` keeps
 * the guarantee structural. Leaving it to be remembered is what made every other
 * control in this project decay.
 */
function asksForAQuantity(prompt) {
  const p = prompt.toLowerCase();
  const METRIC = /\b(sensitivit|specificit|ppv|npv|predictive value|accuracy|auc|likelihood ratio|prevalence|incidence|seroprevalence|coverage|uptake|completeness|odds ratio|risk ratio|hazard ratio|relative risk|efficacy|effectiveness|case fatality|mortality|incubation|attack rate)/;
  const ASKING = /\b(what|which|how (?:much|many|high|low|good)|is the|are the|typical|average|reported|range|estimate|figure|value|number)\b/;
  return METRIC.test(p) && ASKING.test(p);
}

function quantityDirective(prompt) {
  if (!asksForAQuantity(prompt)) return "";
  return (
    `\nTHIS QUESTION ASKS FOR A NUMBER — do not answer it from the passages above.\n` +
    `Those are a top-k sample, and for a quantity the corpus usually holds MANY\n` +
    `estimates that differ because the test, population or reference standard\n` +
    `differed. Run these two first:\n` +
    `  weigh_evidence(question="<the question>")        -> the spread, the\n` +
    `      qualifiers attached to each estimate, and what the sources omit\n` +
    `  check_for_newer_evidence(question="<the question>")  -> how stale the\n` +
    `      corpus is; ask before setting search_online=True\n` +
    `Report a RANGE with its qualifiers, never a single value. If you give one\n` +
    `number, say which estimate it is and why that one applies here.\n`
  );
}

async function main() {
  if (process.env.METIS_CORPUS_HOOK === "0") out(null);

  let input = "";
  try {
    input = readFileSync(0, "utf8");
  } catch { out(null); }

  let prompt = "", sessionId = "";
  try {
    const parsed = JSON.parse(input);
    prompt = (parsed.prompt || "").trim();
    sessionId = parsed.session_id || parsed.sessionId || "";
  } catch { out(null); }

  // Very short prompts ("yes", "go on") carry no query.
  if (prompt.length < 15 || prompt.length > 4000) out(null);

  // A session already established as work ON Metis stays un-grounded, unless
  // this particular prompt asks for the library by name.
  const optedIn = ASKS_FOR_LIBRARY.test(prompt);
  if (!optedIn && isSystemSession(sessionId)) out(null);

  const terms = await triggerTerms();
  if (!terms.length) out(null);

  if (!looksLikeDomainQuestion(prompt, terms)) {
    // Remember WHY it was skipped: if this prompt was about Metis itself, the
    // whole session almost certainly is, and the follow-ups will not say so.
    if (IS_SYSTEM_WORK.test(prompt.toLowerCase())) markSystemSession(sessionId);
    out(null);
  }

  const url = `${BASE}/api/library/corpus-search?q=${encodeURIComponent(prompt)}`
            + `&top_k=6&min_score=0.62`;
  const d = await getJSON(url, SEARCH_TIMEOUT_MS);
  if (!d || !d.ok) out(null);

  const n = (d.results || []).length;
  const corpus = d.corpus_documents || 0;

  if (n === 0) {
    // Say so. "I searched your library and found nothing on this" is genuinely
    // useful information about a gap — and it stops the model implying corpus
    // support it does not have.
    out(
      `<metis-corpus-grounding>\n` +
      `Metis searched the researcher's own indexed corpus (${corpus} documents) ` +
      `for this question and found NO passage above the relevance threshold.\n\n` +
      `Answer from general knowledge, and say plainly that their library has ` +
      `nothing on this — that absence is itself informative. Do not imply the ` +
      `answer is grounded in their literature.\n` +
      quantityDirective(prompt) +
      `</metis-corpus-grounding>`
    );
  }

  const body = d.results.map((r, i) =>
    `[${i + 1}] ${r.title} — ${r.domain || "unfiled"}, p.${r.page} ` +
    `(similarity ${r.score})\n    file: ${r.file}\n    "${r.snippet}"`
  ).join("\n\n");

  out(
    `<metis-corpus-grounding>\n` +
    `Metis automatically searched the researcher's OWN indexed literature before ` +
    `this prompt was answered.\n\n` +
    `Corpus searched : ${corpus} documents\n` +
    `Passages returned: ${n} (top-k semantic similarity, threshold ${d.min_score})\n\n` +
    `${body}\n\n` +
    `HOW TO USE THIS:\n` +
    `- Ground the answer in these passages where they are relevant, and cite them ` +
    `by title and page so the researcher can open the source.\n` +
    `- Open the reply with the marker 📚 and state exactly what was consulted, ` +
    `e.g. "📚 ${n} passages from ${corpus} indexed documents".\n` +
    `- NEVER claim the whole library was read or checked. This is a top-k ` +
    `similarity search, not an exhaustive review. Overstating it makes the ` +
    `grounding worthless.\n` +
    `- If these passages do not actually answer the question, say so and answer ` +
    `from general knowledge instead. A forced citation is worse than none.\n` +
    quantityDirective(prompt) +
    `</metis-corpus-grounding>`
  );
}

main().catch(() => process.exit(0));
