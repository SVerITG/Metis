#!/usr/bin/env node
/**
 * Metis UserPromptSubmit hook — enter data-protected mode on a data request.
 *
 * WHY THIS EXISTS
 *   The Data Memory (`data_memory` MCP tool) knows the researcher's files,
 *   columns, values and existing scripts, learnt from code alone. A tool the
 *   model may choose to call is a convention, not a mechanism — the same lesson
 *   as the corpus-grounding hook beside this one. This hook makes the first
 *   step structural: when a prompt is about data, the model is told to consult
 *   the memory before anything else and to keep its hands off the data files.
 *
 * HOW IT DECIDES
 *   Three kinds of evidence, so that no fixed word list has to be right:
 *   · STRONG words only occur in data work (dataset, column, R script, csv…).
 *   · WEAK words are analysis words (map, chart, how many, per year, cases…),
 *     in English, Dutch and French; one alone is not enough.
 *   · The researcher's OWN data words — file, column, folder names and values
 *     their scripts test for — exported by every Data Memory scan to
 *     data-vocab.json beside the database. They make "the endemic areas
 *     (villages and health zones) for 2026" recognisable for one researcher
 *     and "stunting by district" for another, with nothing hard-coded.
 *   Measured on a labelled set (tests/unit/test_data_mode_hook.py). The first
 *   version, generic words only, missed the researcher's own first request:
 *   it began "Metis, can you…", and "metis" was on the system-work list.
 *
 * WHAT IT IS CAREFUL ABOUT
 *   · Work on Metis itself is not data work, even though it says "dashboard"
 *     and "script": technical words (MCP, hook, route, CSS…) silence it unless
 *     the prompt also names R, a data file, or two of the researcher's data words.
 *     Addressing Metis by name is not technical.
 *   · Speed: one small local file read, no network, no Python.
 *
 * Hook input  (stdin) : JSON { prompt, ... }
 * Hook output (stdout): JSON { hookSpecificOutput: { additionalContext } }
 *
 * Disable with METIS_DATA_MODE_HOOK=0.
 */

import { readFileSync, existsSync } from "fs";
import { homedir } from "os";
import { join, dirname } from "path";

const STRONG = new RegExp(
  "\\b(" + [
    "datasets?", "[\\w-]+\\.(r|rmd|qmd)", "data ?files?", "data ?bases?", "databank", "variables?", "columns?",
    "r ?scripts?", "rscript", "tidyverse", "dplyr", "ggplot2?", "data ?frames?",
    "csv", "xlsx?", "excel", "spreadsheets?", "shapefiles?", "rasters?", "geopackage",
    "rds", "stata", "spss", "line ?list", "codebook", "data ?dictionary",
    "unique values", "missing values", "denominators?",
    // Dutch / French
    "gegevens", "databestand", "kolommen?", "variabelen?", "donn[ée]es", "fichier de donn[ée]es",
    "colonnes?", "tableur",
  ].join("|") + ")\\b", "i");

const WEAK = new RegExp(
  "\\b(" + [
    "data", "analy[sz]e", "analys[ie]s", "analytic", "scripts?", "plots?", "charts?",
    "figures?", "maps?", "mapping", "tables?", "visuali[sz]\\w*", "regression", "models?",
    "merge", "join", "clean(ing)?", "recode", "aggregate", "summar(y|ies|ise|ize)",
    "dashboards?", "panels?", "trends?", "per (year|month|province|district|region|village|site|zone|area)",
    "incidence", "prevalence", "positivity", "coverage", "cases", "counts?", "rates?",
    "surveillance", "cohort", "survey", "screen(ed|ing)", "how many", "number of",
    "compare", "comparison", "distribution", "over time", "by year", "in \\d{4}", "for \\d{4}",
    "between \\d{4}", "since \\d{4}", "indicators?", "endemic", "proportion", "percentage",
    // Dutch
    "analyse", "kaart", "tabel", "grafiek", "figuur", "gevallen", "hoeveel", "per jaar",
    "aantal", "vergelijk\\w*", "verdeling", "dorpen", "bestand",
    // French
    "carte", "tableau", "graphique", "cas", "combien", "par ann[ée]e", "nombre de",
    "comparer", "r[ée]partition", "fichier", "villages",
  ].join("|") + ")\\b", "gi");

// Work on Metis itself: its server, hooks, routes and styling. "metis" alone is
// NOT here — the researcher addresses Metis by name when asking for analyses.
const SYSTEM_WORK = /\b(mcp|hooks?|fastapi|htmx|endpoint|routes?|frontend|css|javascript|node|sqlite|the wizard|installer|subagents?|tool ?calls?|pull request|commit|github|release|restyle|layout|spacing|fonts?|buttons?|cards?|navbar|sidebar|dark mode|light mode|surfaces?|briefings?|morning brief|news|feeds?|calendar|reminders?|install(ed|ing|ation)?|launch(es|ed)?|localhost|claude desktop|claude code|handoff|env\w* ?variables?|envi\w*ment\w* variables?|api ?keys?)\b/i;

// Reading, writing and presenting use the same subject words as analysis
// ("test sensitivity in a field study") without being about the data.
// They silence the hook unless the prompt also asks for an analysis product.
const OTHER_INTENT = /\b(literature|papers?|articles?|references?|citations?|cite|evidence|review|draft|paragraph|abstract|manuscript|introduction|discussion|slides?|presentation|deck|poster|email|letter|artikel|littérature|article|course|lessons?|exercises?|quiz|learners?|ideas?|strategy document)\b/i;
const ANALYSIS_ASK = /\b(how many|number of|maps?|tables?|plots?|charts?|figures?|graphs?|scripts?|counts?|compare|trends?|per year|by year|hoeveel|kaart|tabel|grafiek|combien|carte|tableau|graphique)\b/i;
const NAMES_R_OR_FILE = /\b(r ?scripts?|rscript|\.r\b|\.rmd|\.qmd|csv|xlsx?|shapefile|dataset)\b/i;

function vocab() {
  const dirs = [];
  if (process.env.METIS_DB) dirs.push(dirname(process.env.METIS_DB));
  if (process.env.METIS_DATA_DIR) dirs.push(process.env.METIS_DATA_DIR);
  dirs.push(join(homedir(), ".local", "share", "metis"));
  for (const d of dirs) {
    const f = join(d, "data-vocab.json");
    try {
      if (existsSync(f)) return new Set(JSON.parse(readFileSync(f, "utf8")).terms || []);
    } catch { /* a broken file means generic words only */ }
  }
  return new Set();
}

export function isDataWork(prompt, terms = vocab()) {
  const low = prompt.toLowerCase();
  const words = new Set(low.split(/[^a-zà-ÿ]+/).filter((w) => w.length >= 4));
  let own = 0;
  for (const w of words) if (terms.has(w)) own++;
  const strong = STRONG.test(prompt);
  const weak = new Set((prompt.match(WEAK) || []).map((w) => w.toLowerCase())).size;

  if (SYSTEM_WORK.test(prompt) && !NAMES_R_OR_FILE.test(prompt) && own < 2) return false;
  if (OTHER_INTENT.test(prompt) && !strong && !ANALYSIS_ASK.test(prompt)) return false;
  return strong || weak >= 2 || (own >= 1 && weak >= 1) || own >= 2;
}

function out(context) {
  if (context) {
    process.stdout.write(JSON.stringify({
      hookSpecificOutput: { hookEventName: "UserPromptSubmit", additionalContext: context },
    }));
  }
  process.exit(0);
}

function main() {
  if (process.env.METIS_DATA_MODE_HOOK === "0") out(null);
  let prompt = "";
  try {
    prompt = (JSON.parse(readFileSync(0, "utf8")).prompt || "").trim();
  } catch { out(null); }
  if (prompt.length < 12 || prompt.length > 6000) out(null);
  if (/^(\/direct|direct:|plain claude)/i.test(prompt)) out(null);
  if (!isDataWork(prompt)) out(null);

  // The words decide that this MAY be data work; the model decides whether it
  // is. On the researcher's real prompts a word rule tops out near 70%
  // precision ("the dashboard" is their surveillance dashboard one day and
  // Metis the next), so a false alarm must cost one sentence, not a detour.
  out(
    "<metis-data-mode>\n" +
    "This request may involve the researcher's data. If it asks for an analysis, an R script, " +
    "a figure, map or table from their data, or about what their data or their analysis code " +
    "contains or computes, work in DATA-PROTECTED MODE. If it is about Metis itself, a course, " +
    "writing or anything else, ignore this note.\n" +
    "1. Before anything else, call the Metis tool `data_memory(question=<the request>)`. " +
    "It returns the files, exact paths, columns, values tested in code, derived variables, " +
    "outputs already made, the closest existing scripts and the stories behind the data — " +
    "all learnt from the researcher's own code and notes. Then open the closest " +
    "scripts' code with `data_memory_script(path=...)` (or Read) and reuse how they " +
    "load, clean and define things.\n" +
    "2. Never open, Read, cat, head, preview or summarise a data file (csv, xlsx, rds, shp, " +
    "sav, dta, …) and never ask for rows. Reading R scripts and notes is fine.\n" +
    "3. Deliver an R script the researcher runs locally: start from the closest existing " +
    "script, reuse paths exactly as returned, follow their recorded coding conventions. " +
    "If a column or value is unknown, say so and make the script report it locally rather " +
    "than guessing.\n" +
    "4. When the researcher explains something about a dataset, keep it with " +
    "`record_data_story(target=..., story=...)`.\n" +
    "Do not announce this mode; just work this way.\n" +
    "</metis-data-mode>"
  );
}

// Run only when executed as the hook, not when imported by the tests.
if (process.argv[1] && process.argv[1].endsWith("data-mode.mjs")) main();
