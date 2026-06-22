"""Script Analyzer — extract metadata from R/Python scripts without running them.

Part of the "send code, not data" pipeline: Metis reads the code (safe) to learn
file paths, variables, and packages, generates tailored profiling scripts the user
runs locally, and builds a per-project data dictionary — all without the AI ever
seeing any data.

Four tools:
  1. analyze_script(path)             — parse one script, return structured metadata
  2. scan_project_scripts(folder_path, project_id) — walk a folder, aggregate
  3. generate_profiling_script(dataset_name, project_id, language) — safe profiler
  4. ingest_profiling_output(json_path, dataset_name, project_id)  — import results

All parsing is regex-based (no external dependencies, no AST).
"""

import datetime
import json
import os
import re
from pathlib import Path
from typing import Any

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


# ── Script extensions we handle ────────────────────────────────────────────
_SCRIPT_EXTENSIONS = {".r", ".rmd", ".qmd", ".py"}


# ── Regex patterns ─────────────────────────────────────────────────────────

# R packages
_R_LIBRARY = re.compile(
    r"""(?:library|require)\s*\(\s*["']?(\w+)["']?\s*\)""", re.IGNORECASE
)
_R_PACMAN = re.compile(
    r"""pacman::p_load\s*\(([^)]+)\)""", re.IGNORECASE
)
_R_NS_CALL = re.compile(
    r"""(\w+)::\w+""",
)

# Python imports
_PY_IMPORT = re.compile(
    r"""^\s*(?:import|from)\s+([\w.]+)""", re.MULTILINE
)

# File reads — R
_R_READS = re.compile(
    r"""(?:read\.csv|read\.csv2|read_csv|read\.delim|readRDS|read_rds|"""
    r"""readxl::read_excel|read_excel|haven::read_dta|read_dta|"""
    r"""haven::read_sav|read_sav|haven::read_sas|read_sas|"""
    r"""read\.table|fread|vroom|st_read|readOGR|raster|"""
    r"""read_sf|arrow::read_parquet|read_parquet)"""
    r"""\s*\(\s*["']([^"']+)["']""",
    re.IGNORECASE,
)

# File reads — Python
_PY_READS = re.compile(
    r"""(?:pd\.read_csv|pd\.read_excel|pd\.read_stata|pd\.read_sas|"""
    r"""pd\.read_parquet|pd\.read_spss|pd\.read_json|"""
    r"""gpd\.read_file|open)\s*\(\s*["']([^"']+)["']""",
    re.IGNORECASE,
)

# File writes — R
_R_WRITES = re.compile(
    r"""(?:write\.csv|write\.csv2|write_csv|saveRDS|save_rds|"""
    r"""ggsave|write\.table|fwrite|write_xlsx|st_write|"""
    r"""writeOGR|arrow::write_parquet|write_parquet)"""
    r"""\s*\([^,]*,\s*["']([^"']+)["']""",
    re.IGNORECASE,
)

# File writes — Python
_PY_WRITES = re.compile(
    r"""(?:\.to_csv|\.to_excel|\.to_parquet|\.to_stata|\.to_json)"""
    r"""\s*\(\s*["']([^"']+)["']""",
    re.IGNORECASE,
)

# R variables: df$column
_R_DOLLAR = re.compile(r"""\w+\$(\w+)""")

# dplyr verbs that reference column names
_R_DPLYR_VERB = re.compile(
    r"""(?:mutate|select|filter|group_by|arrange|rename|summarise|summarize|"""
    r"""count|distinct|pull|transmute|relocate|across|where|if_else|case_when)"""
    r"""\s*\(([^)]{1,500})""",
    re.IGNORECASE,
)

# ggplot2 aes() — extract variable names
_R_AES = re.compile(
    r"""aes\s*\(([^)]{1,300})""", re.IGNORECASE
)

# R source() calls
_R_SOURCE = re.compile(
    r"""source\s*\(\s*["']([^"']+)["']\s*\)""", re.IGNORECASE
)

# R assignment: capture LHS of <- or =
_R_ASSIGN = re.compile(
    r"""^\s*(\w+)\s*(?:<-|=)\s""", re.MULTILINE
)

# R joins
_R_JOINS = re.compile(
    r"""(?:left_join|right_join|inner_join|full_join|anti_join|semi_join|merge)""",
    re.IGNORECASE,
)

# R pivots
_R_PIVOTS = re.compile(
    r"""(?:pivot_longer|pivot_wider|gather|spread|melt|dcast|acast)""",
    re.IGNORECASE,
)

# R recodes
_R_RECODES = re.compile(
    r"""(?:recode|fct_recode|fct_relevel|fct_collapse|case_when|if_else|ifelse|case_match)""",
    re.IGNORECASE,
)

# R/Python pipes
_R_PIPES = re.compile(r"""%>%|\|>""")


def _extract_r_variables(code: str) -> set[str]:
    """Extract variable/column names from R code."""
    variables: set[str] = set()

    # $column access
    for m in _R_DOLLAR.finditer(code):
        variables.add(m.group(1))

    # dplyr verb arguments — extract bare names
    for m in _R_DPLYR_VERB.finditer(code):
        inner = m.group(1)
        # Extract bare names (not strings, not numbers, not operators)
        tokens = re.findall(r'\b([a-zA-Z_]\w*)\b', inner)
        # Filter out R keywords and common function names
        _skip = {
            "TRUE", "FALSE", "NULL", "NA", "NaN", "Inf",
            "c", "n", "mean", "sum", "sd", "min", "max", "median",
            "length", "nrow", "ncol", "paste", "paste0", "round",
            "as", "is", "ifelse", "if_else", "case_when", "case_match",
            "everything", "starts_with", "ends_with", "contains", "matches",
            "where", "across", "any_of", "all_of", "num_range",
        }
        for tok in tokens:
            if tok not in _skip and not tok.startswith("_"):
                variables.add(tok)

    # aes() arguments
    for m in _R_AES.finditer(code):
        inner = m.group(1)
        tokens = re.findall(r'\b([a-zA-Z_]\w*)\b', inner)
        _aes_skip = {"x", "y", "colour", "color", "fill", "size", "shape",
                      "linetype", "alpha", "group", "label", "weight",
                      "aes", "stat", "position"}
        for tok in tokens:
            if tok not in _aes_skip:
                variables.add(tok)

    return variables


def _extract_py_variables(code: str) -> set[str]:
    """Extract column names from Python/pandas code (basic heuristic)."""
    variables: set[str] = set()

    # df["column"] or df['column']
    for m in re.finditer(r"""\w+\[["'](\w+)["']\]""", code):
        variables.add(m.group(1))

    # .column access after df. (heuristic — may catch methods)
    # Skip known pandas methods
    _pd_methods = {
        "head", "tail", "describe", "info", "shape", "columns", "dtypes",
        "groupby", "merge", "join", "drop", "rename", "apply", "map",
        "fillna", "dropna", "sort_values", "reset_index", "set_index",
        "to_csv", "to_excel", "to_parquet", "copy", "astype", "value_counts",
        "nunique", "isnull", "notnull", "isna", "notna", "sum", "mean",
        "median", "std", "min", "max", "count", "agg", "transform",
        "pivot_table", "melt", "stack", "unstack", "plot", "hist",
        "str", "dt", "cat", "loc", "iloc", "iterrows", "itertuples",
        "query", "assign", "pipe", "sample", "nlargest", "nsmallest",
    }
    for m in re.finditer(r"""(?:df|data|dataset|dat)\.\b(\w+)\b""", code):
        name = m.group(1)
        if name not in _pd_methods and not name.startswith("_"):
            variables.add(name)

    return variables


def _analyze_code(code: str, filepath: str) -> dict[str, Any]:
    """Parse a script's code and return structured metadata."""
    ext = os.path.splitext(filepath)[1].lower()
    is_r = ext in (".r", ".rmd", ".qmd")
    is_py = ext == ".py"

    result: dict[str, Any] = {
        "file": filepath,
        "language": "R" if is_r else "Python" if is_py else "unknown",
        "packages": [],
        "file_reads": [],
        "file_writes": [],
        "variables": [],
        "sources": [],
        "transforms": {
            "joins": False,
            "pivots": False,
            "recodes": False,
            "pipes": False,
        },
    }

    # -- Packages --
    pkgs: set[str] = set()
    if is_r:
        for m in _R_LIBRARY.finditer(code):
            pkgs.add(m.group(1))
        for m in _R_PACMAN.finditer(code):
            for pkg in re.split(r'[,\s]+', m.group(1)):
                pkg = pkg.strip().strip('"').strip("'")
                if pkg and pkg.isidentifier():
                    pkgs.add(pkg)
        for m in _R_NS_CALL.finditer(code):
            pkgs.add(m.group(1))
    elif is_py:
        for m in _PY_IMPORT.finditer(code):
            top = m.group(1).split(".")[0]
            pkgs.add(top)
    result["packages"] = sorted(pkgs)

    # -- File reads --
    reads: set[str] = set()
    if is_r:
        for m in _R_READS.finditer(code):
            reads.add(m.group(1))
    if is_py:
        for m in _PY_READS.finditer(code):
            reads.add(m.group(1))
    result["file_reads"] = sorted(reads)

    # -- File writes --
    writes: set[str] = set()
    if is_r:
        for m in _R_WRITES.finditer(code):
            writes.add(m.group(1))
    if is_py:
        for m in _PY_WRITES.finditer(code):
            writes.add(m.group(1))
    result["file_writes"] = sorted(writes)

    # -- Variables --
    variables: set[str] = set()
    if is_r:
        variables = _extract_r_variables(code)
    elif is_py:
        variables = _extract_py_variables(code)
    result["variables"] = sorted(variables)

    # -- Sources (R source() calls) --
    if is_r:
        result["sources"] = sorted({m.group(1) for m in _R_SOURCE.finditer(code)})

    # -- Transforms --
    if is_r:
        result["transforms"]["joins"] = bool(_R_JOINS.search(code))
        result["transforms"]["pivots"] = bool(_R_PIVOTS.search(code))
        result["transforms"]["recodes"] = bool(_R_RECODES.search(code))
        result["transforms"]["pipes"] = bool(_R_PIPES.search(code))

    return result


# ── Tool 1: analyze_script ─────────────────────────────────────────────────

@app.tool()
async def analyze_script(
    path: str,
) -> list[TextContent]:
    """Parse one R or Python script and extract structured metadata.

    Returns packages, file reads/writes, variable names, source dependencies,
    and transform patterns — all from regex parsing (no execution, no AST,
    no data access).  The script's code is read but never sent to an LLM;
    only the extracted metadata is returned.

    Args:
        path: Absolute path to the script file (.R, .Rmd, .qmd, or .py).
    """
    p = Path(path)
    if not p.exists():
        return [TextContent(type="text", text=f"File not found: {path}")]
    if p.suffix.lower() not in _SCRIPT_EXTENSIONS:
        return [TextContent(type="text", text=(
            f"Unsupported extension '{p.suffix}'. "
            f"Supported: {', '.join(sorted(_SCRIPT_EXTENSIONS))}"
        ))]
    try:
        code = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [TextContent(type="text", text=f"Could not read file: {e}")]

    result = _analyze_code(code, str(p))
    result["lines"] = code.count("\n") + 1

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ── Tool 2: scan_project_scripts ──────────────────────────────────────────

def _ensure_code_tables(conn) -> None:
    """Ensure code_artifacts and data_dictionary tables exist."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS code_artifacts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  TEXT DEFAULT '',
            title       TEXT NOT NULL,
            language    TEXT DEFAULT '',
            kind        TEXT DEFAULT 'script',
            purpose     TEXT DEFAULT '',
            tags        TEXT DEFAULT '',
            code        TEXT DEFAULT '',
            file_path   TEXT DEFAULT '',
            packages    TEXT DEFAULT '',
            params      TEXT DEFAULT '',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS data_dictionary (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id    TEXT DEFAULT '',
            dataset_name  TEXT NOT NULL,
            dataset_path  TEXT DEFAULT '',
            variable_name TEXT NOT NULL,
            var_type      TEXT DEFAULT '',
            label         TEXT DEFAULT '',
            unique_values TEXT DEFAULT '',
            units         TEXT DEFAULT '',
            notes         TEXT DEFAULT '',
            created_at    TEXT NOT NULL
        )"""
    )


@app.tool()
async def scan_project_scripts(
    folder_path: str,
    project_id: str = "",
) -> list[TextContent]:
    """Walk all R/Python scripts in a folder, extract metadata, and register them.

    For each script found (.R, .Rmd, .qmd, .py):
    - Parses packages, file reads/writes, variables, and transforms
    - Auto-registers each as a code_artifact in the Code Repository
    - Aggregates variables across all scripts
    - Maps detected file paths to dataset names

    Returns a summary: N scripts, M packages, K datasets, P variables.

    Args:
        folder_path: Absolute path to the folder to scan.
        project_id:  Project ID to associate the scripts with (optional).
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        return [TextContent(type="text", text=f"Not a directory: {folder_path}")]

    # Collect all script files (non-recursive would miss R project structures)
    script_files = []
    for root, _dirs, files in os.walk(folder):
        for f in files:
            if os.path.splitext(f)[1].lower() in _SCRIPT_EXTENSIONS:
                script_files.append(os.path.join(root, f))

    if not script_files:
        return [TextContent(type="text", text=f"No R/Python scripts found in {folder_path}")]

    all_packages: set[str] = set()
    all_variables: set[str] = set()
    all_reads: set[str] = set()
    all_writes: set[str] = set()
    analyses: list[dict] = []
    registered = 0

    try:
        with connect(paths.db) as conn:
            _ensure_code_tables(conn)

            for filepath in sorted(script_files):
                try:
                    code = Path(filepath).read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                analysis = _analyze_code(code, filepath)
                analysis["lines"] = code.count("\n") + 1
                analyses.append(analysis)

                all_packages.update(analysis["packages"])
                all_variables.update(analysis["variables"])
                all_reads.update(analysis["file_reads"])
                all_writes.update(analysis["file_writes"])

                # Register as code artifact (upsert by file_path + project_id)
                fname = os.path.basename(filepath)
                lang = analysis["language"].lower()
                existing = conn.execute(
                    "SELECT id FROM code_artifacts WHERE file_path = ? AND project_id = ?",
                    (filepath, project_id),
                ).fetchone()

                if existing:
                    conn.execute(
                        """UPDATE code_artifacts
                           SET packages = ?, tags = ?, updated_at = ?
                           WHERE id = ?""",
                        (", ".join(analysis["packages"]),
                         ", ".join(analysis["variables"][:20]),
                         _now(), existing[0]),
                    )
                else:
                    conn.execute(
                        """INSERT INTO code_artifacts
                           (project_id, title, language, kind, purpose, tags,
                            code, file_path, packages, params, created_at, updated_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (project_id, fname, lang, "script",
                         f"Scanned from {folder_path}",
                         ", ".join(analysis["variables"][:20]),
                         "",  # Don't store full code — just metadata
                         filepath,
                         ", ".join(analysis["packages"]),
                         "", _now(), _now()),
                    )
                registered += 1

        # Build dataset map: filename stem as dataset name
        datasets: dict[str, str] = {}
        for read_path in sorted(all_reads):
            stem = Path(read_path).stem
            datasets[stem] = read_path

        # Summary
        lines = [
            f"## Script Scan: {folder_path}",
            f"",
            f"| Metric | Count |",
            f"|--------|-------|",
            f"| Scripts found | {len(script_files)} |",
            f"| Scripts analyzed | {len(analyses)} |",
            f"| Registered to Code Repository | {registered} |",
            f"| Unique packages | {len(all_packages)} |",
            f"| Datasets detected | {len(datasets)} |",
            f"| Variables extracted | {len(all_variables)} |",
            f"",
        ]

        if all_packages:
            lines.append(f"**Packages:** {', '.join(sorted(all_packages))}")
            lines.append("")

        if datasets:
            lines.append("**Datasets:**")
            for name, dpath in datasets.items():
                lines.append(f"- `{name}` \u2190 `{dpath}`")
            lines.append("")

        if all_variables:
            var_list = sorted(all_variables)[:50]
            lines.append(f"**Variables** ({len(all_variables)} total, showing first 50):")
            lines.append(", ".join(f"`{v}`" for v in var_list))
            lines.append("")

        # Per-script breakdown
        lines.append("### Per-script details")
        for a in analyses:
            fname = os.path.basename(a["file"])
            lines.append(
                f"- **{fname}** ({a['language']}, {a['lines']} lines): "
                f"{len(a['packages'])} pkgs, "
                f"{len(a['file_reads'])} reads, "
                f"{len(a['variables'])} vars"
            )

        if project_id:
            lines.append(f"\nAll artifacts registered under project: **{project_id}**")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Scan failed: {e}")]


# ── Tool 3: generate_profiling_script ──────────────────────────────────────

@app.tool()
async def generate_profiling_script(
    dataset_name: str,
    project_id: str = "",
    language: str = "r",
    dataset_path: str = "",
) -> list[TextContent]:
    """Generate a safe profiling script tailored to a specific dataset.

    The generated script runs on the user's machine and reports ONLY
    aggregates: variable names, types, unique counts, ranges, missingness,
    and value frequencies (capped at 30 levels).  No row-level data leaves
    the machine.  Output is structured JSON matching the register_data_dictionary
    schema, ready for ingest_profiling_output().

    If data_dictionary entries already exist for this dataset, the script
    includes checks for those specific variables.

    Args:
        dataset_name: Name of the dataset (used in filenames and DB).
        project_id:   Project ID for looking up existing variable info.
        language:     "r" or "python" (default "r").
        dataset_path: Path to the data file on disk. If empty, a placeholder is used.
    """
    lang = language.lower().strip()
    if lang not in ("r", "python", "py"):
        return [TextContent(type="text", text="Language must be 'r' or 'python'.")]
    is_r = lang == "r"

    # Check if we already know some variables for this dataset
    known_vars: list[dict] = []
    try:
        if paths.db.exists():
            with connect(paths.db) as conn:
                rows = conn.execute(
                    "SELECT variable_name, var_type, label FROM data_dictionary "
                    "WHERE dataset_name = ? AND COALESCE(project_id,'') = ? "
                    "ORDER BY variable_name",
                    (dataset_name, project_id),
                ).fetchall()
                known_vars = [
                    {"name": r[0], "type": r[1], "label": r[2]} for r in rows
                ]
    except Exception:
        pass

    path_placeholder = dataset_path or f"PATH/TO/{dataset_name}.csv"

    # Determine output path
    output_dir = paths.root / "outputs" / "scripts"
    output_dir.mkdir(parents=True, exist_ok=True)
    ext = ".R" if is_r else ".py"
    script_path = output_dir / f"{dataset_name}_profile{ext}"

    if is_r:
        script = _generate_r_profiling_script(
            dataset_name, path_placeholder, known_vars
        )
    else:
        script = _generate_py_profiling_script(
            dataset_name, path_placeholder, known_vars
        )

    # Write to disk
    try:
        script_path.write_text(script, encoding="utf-8")
    except Exception as e:
        return [TextContent(type="text", text=f"Could not write script: {e}")]

    lines = [
        f"Profiling script written to: `{script_path}`",
        "",
        "**Instructions:**",
        f"1. Open `{script_path.name}` in {'RStudio' if is_r else 'your Python IDE'}",
        f"2. Update the file path if needed (currently: `{path_placeholder}`)",
        "3. Run the script on your machine",
        f"4. It will produce `{dataset_name}_profile.json` in the same folder as the data",
        "5. Share the JSON path with me and I'll ingest it into the data dictionary",
        "",
        "**Safety:** Only aggregates are computed. No row-level data is included.",
    ]

    if known_vars:
        lines.append(f"\n_Note: {len(known_vars)} known variables included for consistency checks._")

    return [TextContent(type="text", text="\n".join(lines))]


def _generate_r_profiling_script(
    dataset_name: str, data_path: str, known_vars: list[dict]
) -> str:
    """Generate an R profiling script."""
    known_check = ""
    if known_vars:
        var_names = ", ".join(f'"{v["name"]}"' for v in known_vars)
        known_check = f"""
# Check for known variables from the data dictionary
known_vars <- c({var_names})
missing_known <- setdiff(known_vars, names(df))
if (length(missing_known) > 0) {{
  cat("WARNING: Known variables not found in data:", paste(missing_known, collapse=", "), "\\n")
}}
extra_vars <- setdiff(names(df), known_vars)
if (length(extra_vars) > 0) {{
  cat("NOTE: New variables not in dictionary:", paste(extra_vars, collapse=", "), "\\n")
}}
"""

    return f'''# ── Profiling script for: {dataset_name} ──────────────────────────────
# Generated by Metis (send code, not data).
# Only AGGREGATES leave your machine. No row-level data is included.
# Output: {dataset_name}_profile.json (structured for Metis data dictionary)

# ── 1. Read the data ──────────────────────────────────────────────────
data_path <- "{data_path}"

# Auto-detect format from extension
ext <- tolower(tools::file_ext(data_path))
df <- switch(ext,
  "csv"  = read.csv(data_path, stringsAsFactors = FALSE),
  "rds"  = readRDS(data_path),
  "dta"  = haven::read_dta(data_path),
  "sav"  = haven::read_sav(data_path),
  "sas7bdat" = haven::read_sas(data_path),
  "xlsx" = readxl::read_excel(data_path),
  "xls"  = readxl::read_excel(data_path),
  stop(paste("Unsupported format:", ext))
)

cat("Dataset:", "{dataset_name}", "\\n")
cat("Rows:", nrow(df), " Cols:", ncol(df), "\\n\\n")
{known_check}
# ── 2. Profile each variable ─────────────────────────────────────────
variables <- list()

for (v in names(df)) {{
  x <- df[[v]]
  entry <- list(
    name = v,
    type = paste(class(x), collapse = "/"),
    n_missing = sum(is.na(x)),
    pct_missing = round(100 * sum(is.na(x)) / length(x), 2),
    n_unique = length(unique(x[!is.na(x)]))
  )

  if (is.numeric(x)) {{
    vals <- x[!is.na(x)]
    entry$type <- "numeric"
    if (length(vals) > 0) {{
      entry$min <- round(min(vals), 4)
      entry$max <- round(max(vals), 4)
      entry$mean <- round(mean(vals), 4)
      entry$median <- round(median(vals), 4)
      entry$sd <- round(sd(vals), 4)
    }}
    # Check for potential categorical coded as numeric
    if (entry$n_unique <= 20 && entry$n_unique > 0) {{
      freq <- sort(table(x, useNA = "ifany"), decreasing = TRUE)
      entry$unique_values <- paste(names(freq), collapse = " | ")
      entry$notes <- "Low-cardinality numeric — may be categorical"
    }}
  }} else if (is.character(x) || is.factor(x)) {{
    entry$type <- "character"
    vals <- as.character(x[!is.na(x)])
    if (entry$n_unique <= 30) {{
      freq <- sort(table(vals, useNA = "ifany"), decreasing = TRUE)
      entry$unique_values <- paste(names(freq), collapse = " | ")
      # Check for coding inconsistencies
      lower_vals <- tolower(trimws(vals))
      if (length(unique(lower_vals)) < length(unique(vals))) {{
        entry$notes <- paste0(
          "Possible inconsistent coding: ",
          length(unique(vals)), " raw levels vs ",
          length(unique(lower_vals)), " after lowercasing"
        )
      }}
    }} else {{
      entry$unique_values <- paste0("(", entry$n_unique, " unique values — high cardinality)")
      entry$notes <- "High-cardinality — values withheld"
    }}
  }} else if (inherits(x, "Date") || inherits(x, "POSIXct") || inherits(x, "POSIXlt")) {{
    entry$type <- "date"
    vals <- x[!is.na(x)]
    if (length(vals) > 0) {{
      entry$min <- as.character(min(vals))
      entry$max <- as.character(max(vals))
      entry$unique_values <- paste0(entry$min, " to ", entry$max)
    }}
  }} else {{
    entry$type <- paste(class(x), collapse = "/")
  }}

  variables[[length(variables) + 1]] <- entry
}}

# ── 3. Write structured JSON output ──────────────────────────────────
output <- list(
  dataset_name = "{dataset_name}",
  rows = nrow(df),
  cols = ncol(df),
  profiled_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S"),
  variables = variables
)

output_path <- file.path(dirname(data_path), "{dataset_name}_profile.json")
jsonlite::write_json(output, output_path, pretty = TRUE, auto_unbox = TRUE)
cat("\\nProfile written to:", output_path, "\\n")
cat("Variables profiled:", length(variables), "\\n")
cat("\\nShare this JSON file path with Metis to register the data dictionary.\\n")
'''


def _generate_py_profiling_script(
    dataset_name: str, data_path: str, known_vars: list[dict]
) -> str:
    """Generate a Python profiling script."""
    known_check = ""
    if known_vars:
        var_names = ", ".join(f'"{v["name"]}"' for v in known_vars)
        known_check = f"""
# Check for known variables from the data dictionary
known_vars = [{var_names}]
missing_known = [v for v in known_vars if v not in df.columns]
if missing_known:
    print(f"WARNING: Known variables not found: {{', '.join(missing_known)}}")
extra_vars = [v for v in df.columns if v not in known_vars]
if extra_vars:
    print(f"NOTE: New variables not in dictionary: {{', '.join(extra_vars)}}")
"""

    return f'''"""Profiling script for: {dataset_name}

Generated by Metis (send code, not data).
Only AGGREGATES leave your machine. No row-level data is included.
Output: {dataset_name}_profile.json (structured for Metis data dictionary)
"""

import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

# ── 1. Read the data ──────────────────────────────────────────────────
data_path = "{data_path}"

ext = Path(data_path).suffix.lower()
read_funcs = {{
    ".csv": pd.read_csv,
    ".xlsx": pd.read_excel,
    ".xls": pd.read_excel,
    ".dta": pd.read_stata,
    ".sav": pd.read_spss,
    ".parquet": pd.read_parquet,
    ".json": pd.read_json,
}}

if ext not in read_funcs:
    raise ValueError(f"Unsupported format: {{ext}}")

df = read_funcs[ext](data_path)
print(f"Dataset: {dataset_name}")
print(f"Rows: {{len(df)}}  Cols: {{df.shape[1]}}")
{known_check}
# ── 2. Profile each variable ─────────────────────────────────────────
variables = []

for col in df.columns:
    s = df[col]
    entry = {{
        "name": col,
        "type": str(s.dtype),
        "n_missing": int(s.isna().sum()),
        "pct_missing": round(100 * s.isna().mean(), 2),
        "n_unique": int(s.nunique()),
    }}

    if pd.api.types.is_numeric_dtype(s):
        entry["type"] = "numeric"
        vals = s.dropna()
        if len(vals) > 0:
            entry["min"] = round(float(vals.min()), 4)
            entry["max"] = round(float(vals.max()), 4)
            entry["mean"] = round(float(vals.mean()), 4)
            entry["median"] = round(float(vals.median()), 4)
            entry["sd"] = round(float(vals.std()), 4)

        if entry["n_unique"] <= 20 and entry["n_unique"] > 0:
            freq = s.value_counts(dropna=False).head(30)
            entry["unique_values"] = " | ".join(str(v) for v in freq.index)
            entry["notes"] = "Low-cardinality numeric — may be categorical"

    elif pd.api.types.is_string_dtype(s) or pd.api.types.is_categorical_dtype(s):
        entry["type"] = "character"
        vals = s.dropna().astype(str)
        if entry["n_unique"] <= 30:
            freq = vals.value_counts().head(30)
            entry["unique_values"] = " | ".join(str(v) for v in freq.index)
            lower_vals = vals.str.lower().str.strip()
            if lower_vals.nunique() < vals.nunique():
                entry["notes"] = (
                    f"Possible inconsistent coding: "
                    f"{{vals.nunique()}} raw levels vs "
                    f"{{lower_vals.nunique()}} after lowercasing"
                )
        else:
            entry["unique_values"] = f"({{entry['n_unique']}} unique values — high cardinality)"
            entry["notes"] = "High-cardinality — values withheld"

    elif pd.api.types.is_datetime64_any_dtype(s):
        entry["type"] = "date"
        vals = s.dropna()
        if len(vals) > 0:
            entry["min"] = str(vals.min())
            entry["max"] = str(vals.max())
            entry["unique_values"] = f"{{vals.min()}} to {{vals.max()}}"

    variables.append(entry)

# ── 3. Write structured JSON output ──────────────────────────────────
output = {{
    "dataset_name": "{dataset_name}",
    "rows": len(df),
    "cols": df.shape[1],
    "profiled_at": datetime.now().isoformat(timespec="seconds"),
    "variables": variables,
}}

output_path = os.path.join(os.path.dirname(data_path), "{dataset_name}_profile.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, default=str)

print(f"\\nProfile written to: {{output_path}}")
print(f"Variables profiled: {{len(variables)}}")
print("\\nShare this JSON file path with Metis to register the data dictionary.")
'''


# ── Tool 4: ingest_profiling_output ────────────────────────────────────────

@app.tool()
async def ingest_profiling_output(
    json_path: str,
    dataset_name: str = "",
    project_id: str = "",
) -> list[TextContent]:
    """Read JSON profiling output and register it as a data dictionary.

    The user runs the profiling script locally (generated by
    generate_profiling_script), which produces a JSON file.  This tool
    reads that JSON and calls register_data_dictionary logic to insert/replace
    the variable definitions.

    Args:
        json_path:    Absolute path to the profiling JSON output file.
        dataset_name: Override the dataset name (default: read from JSON).
        project_id:   Project to associate the dictionary with.
    """
    p = Path(json_path)
    if not p.exists():
        return [TextContent(type="text", text=f"File not found: {json_path}")]

    try:
        raw = p.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return [TextContent(type="text", text=f"Invalid JSON: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Could not read file: {e}")]

    # Extract fields
    ds_name = dataset_name or data.get("dataset_name", "")
    if not ds_name:
        return [TextContent(type="text", text=(
            "No dataset_name found in JSON or provided as argument."
        ))]

    variables = data.get("variables", [])
    if not variables:
        return [TextContent(type="text", text="No variables found in the profiling output.")]

    dataset_path = data.get("dataset_path", "")
    rows = data.get("rows", 0)
    cols = data.get("cols", 0)

    # Register into data_dictionary
    stored = 0
    try:
        with connect(paths.db) as conn:
            _ensure_code_tables(conn)

            # Replace existing dictionary for this dataset (idempotent)
            conn.execute(
                "DELETE FROM data_dictionary WHERE dataset_name = ? AND COALESCE(project_id,'') = ?",
                (ds_name, project_id),
            )

            for v in variables:
                if not isinstance(v, dict) or not v.get("name"):
                    continue

                # Build unique_values summary
                uv = v.get("unique_values", "")
                if not uv:
                    parts = []
                    if v.get("min") is not None and v.get("max") is not None:
                        parts.append(f"range: {v['min']}–{v['max']}")
                    if v.get("n_unique"):
                        parts.append(f"{v['n_unique']} unique")
                    uv = "; ".join(parts) if parts else ""

                # Build notes
                notes_parts = []
                if v.get("notes"):
                    notes_parts.append(v["notes"])
                if v.get("pct_missing", 0) > 0:
                    notes_parts.append(f"{v['pct_missing']}% missing")

                conn.execute(
                    """INSERT INTO data_dictionary
                       (project_id, dataset_name, dataset_path, variable_name,
                        var_type, label, unique_values, units, notes, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (project_id, ds_name, dataset_path, str(v["name"]),
                     str(v.get("type", "")), str(v.get("label", "")),
                     str(uv), str(v.get("units", "")),
                     "; ".join(notes_parts) if notes_parts else "",
                     _now()),
                )
                stored += 1

        summary = [
            f"Ingested **{stored}** variables for dataset **{ds_name}**.",
        ]
        if project_id:
            summary.append(f"Project: {project_id}")
        if rows:
            summary.append(f"Dataset shape: {rows} rows \u00d7 {cols} columns")
        summary.append("")
        summary.append(
            "The data dictionary is now registered. Use `scaffold_script()` "
            "to write new scripts using these exact variable names and paths."
        )

        return [TextContent(type="text", text="\n".join(summary))]

    except Exception as e:
        return [TextContent(type="text", text=f"Ingestion failed: {e}")]
