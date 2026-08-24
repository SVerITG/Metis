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

  const hits = terms.filter((t) => t.length > 3 && p.includes(t));
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

  let prompt = "";
  try {
    prompt = (JSON.parse(input).prompt || "").trim();
  } catch { out(null); }

  // Very short prompts ("yes", "go on") carry no query.
  if (prompt.length < 15 || prompt.length > 4000) out(null);

  const terms = await triggerTerms();
  if (!terms.length) out(null);
  if (!looksLikeDomainQuestion(prompt, terms)) out(null);

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
