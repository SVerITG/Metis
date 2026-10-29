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
 * WHAT IT IS CAREFUL ABOUT
 *   · No hard-coded subject vocabulary. Detection uses words for DATA WORK
 *     (dataset, column, R script, merge, map…), never a disease or a country,
 *     so it works for any researcher who installs Metis.
 *   · Work on Metis itself is not data work, even though it says "dashboard"
 *     and "script". A prompt about the system's own code stays silent unless it
 *     also names R or a data file.
 *   · Speed. It only emits a directive: no network, no Python, no file reads.
 *
 * Hook input  (stdin) : JSON { prompt, ... }
 * Hook output (stdout): JSON { hookSpecificOutput: { additionalContext } }
 *
 * Disable with METIS_DATA_MODE_HOOK=0.
 */

import { readFileSync } from "fs";

// Words that only occur when the work is about data.
const STRONG = new RegExp(
  "\\b(" + [
    "datasets?", "data ?files?", "data ?bases?", "databank", "variables?", "columns?",
    "r ?scripts?", "rscript", "tidyverse", "dplyr", "ggplot2?", "data ?frames?",
    "csv", "xlsx?", "excel", "spreadsheets?", "shapefiles?", "rasters?", "geopackage",
    "rds", "stata", "spss", "line ?list", "codebook", "data ?dictionary",
    "unique values", "missing values", "denominators?", "indicators?",
  ].join("|") + ")\\b", "i");

// Words for analysis work; they count when paired with a second signal.
const WEAK = new RegExp(
  "\\b(" + [
    "data", "analy[sz]e", "analys[ie]s", "analytic", "scripts?", "plots?", "charts?",
    "figures?", "maps?", "mapping", "tables?", "visuali[sz]\\w*", "regression", "models?",
    "merge", "join", "clean(ing)?", "recode", "aggregate", "summar(y|ies|ise|ize)",
    "dashboards?", "panels?", "trend", "per (year|province|district|region|village|site)",
    "incidence", "prevalence", "positivity", "coverage", "cases", "counts?", "rates?",
    "surveillance", "cohort", "survey", "screen(ed|ing)",
  ].join("|") + ")\\b", "gi");

// Work on Metis itself: its server, hooks, routes and styling.
const SYSTEM_WORK = /\b(metis|mcp|hooks?|fastapi|htmx|endpoint|routes?|frontend|css|python|javascript|node|sqlite|the wizard|installer|agent)\b/i;
const NAMES_R_OR_FILE = /\b(r ?scripts?|rscript|\.r\b|\.rmd|\.qmd|csv|xlsx?|shapefile|dataset)\b/i;

function out(context) {
  if (context) {
    process.stdout.write(JSON.stringify({
      hookSpecificOutput: { hookEventName: "UserPromptSubmit", additionalContext: context },
    }));
  }
  process.exit(0);
}

function isDataWork(prompt) {
  if (SYSTEM_WORK.test(prompt) && !NAMES_R_OR_FILE.test(prompt)) return false;
  if (STRONG.test(prompt)) return true;
  const weak = new Set((prompt.match(WEAK) || []).map((w) => w.toLowerCase()));
  return weak.size >= 2;
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

  out(
    "<metis-data-mode>\n" +
    "This request is about the researcher's data. Work in DATA-PROTECTED MODE:\n" +
    "1. Before anything else, call the Metis tool `data_memory(question=<the request>)`. " +
    "It returns the files, exact paths, columns, values tested in code, derived variables, " +
    "outputs already made, the closest existing scripts and the stories behind the data — " +
    "all learnt from the researcher's own code and notes.\n" +
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

main();
