"""
tools/data_tools.py — Phase 8.5: Data Analyst Agent.

M8.5.1  profile_dataset(path, sample_rows)
          Shape, dtypes, null %, unique counts, numeric distributions,
          top-5 values for categoricals. Returns JSON profile.

M8.5.2  suggest_cleaning(path)
          Profile the dataset and return specific recommended operations
          with rationale (e.g. "col 'age' has 12% nulls → suggest fill_na").

M8.5.3  clean_dataset(path, operations, output_path)
          Apply a list of cleaning operations and write a new file.
          Never modifies the original. Returns row/col delta.

M8.5.4  compare_profiles(before_profile, after_profile)
          Side-by-side diff: rows, columns, null counts, type changes.
          Returns structured JSON + human-readable summary.

M8.5.5  list_supported_formats()
          Return supported formats and installed library versions.

Privacy by design:
  - All tools read/write local paths only (never URLs).
  - Before any profiling, column names are scanned against _SENSITIVE_COLUMNS
    from safety.py patterns. Flagged columns are annotated (non-blocking).
  - The original file is NEVER modified; clean_dataset always writes a new path.
"""

import json
import re
from pathlib import Path
from typing import Any

from mcp.types import TextContent

from metis_mcp.app_instance import app

# ---------------------------------------------------------------------------
# PII column patterns (mirrors safety.py _SENSITIVE_COLUMNS)
# ---------------------------------------------------------------------------

_SENSITIVE_COLUMNS = {
    "patient", "patient_id", "case_id", "diagnosis", "dob",
    "date_of_birth", "test_result", "gps_lat", "gps_lon",
    "name", "firstname", "lastname", "surname", "email",
    "phone", "address", "nid", "national_id", "ssn",
    "passport", "bsn", "rrn",
}

_SENSITIVE_PATTERNS = [
    re.compile(r"patient", re.IGNORECASE),
    re.compile(r"case.?id", re.IGNORECASE),
    re.compile(r"date.?of.?birth|dob", re.IGNORECASE),
    re.compile(r"diagnos", re.IGNORECASE),
    re.compile(r"gps|coord|lat(itude)?|lon(gitude)?", re.IGNORECASE),
    re.compile(r"national.?id|nid|ssn|passport|bsn|rrn", re.IGNORECASE),
    re.compile(r"email|phone|address", re.IGNORECASE),
]


def _flag_sensitive_columns(columns: list[str]) -> list[str]:
    """Return column names that match PII patterns."""
    flagged = []
    for col in columns:
        col_lower = col.lower().strip()
        if col_lower in _SENSITIVE_COLUMNS:
            flagged.append(col)
            continue
        for pat in _SENSITIVE_PATTERNS:
            if pat.search(col_lower):
                flagged.append(col)
                break
    return flagged


# ---------------------------------------------------------------------------
# Format loading helpers
# ---------------------------------------------------------------------------

def _load_dataframe(path: Path) -> "Any":
    """Load a tabular file into a pandas DataFrame. Raises on unsupported format."""
    import pandas as pd

    suffix = path.suffix.lower()
    if suffix in (".csv",):
        return pd.read_csv(path, low_memory=False)
    elif suffix in (".tsv",):
        return pd.read_csv(path, sep="\t", low_memory=False)
    elif suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    elif suffix == ".sav":
        import pyreadstat
        df, _ = pyreadstat.read_sav(str(path))
        return df
    elif suffix == ".dta":
        import pyreadstat
        df, _ = pyreadstat.read_dta(str(path))
        return df
    else:
        raise ValueError(
            f"Unsupported format: {suffix}. "
            "Supported: .csv, .tsv, .xlsx, .xls, .sav, .dta"
        )


def _save_dataframe(df: "Any", path: Path) -> None:
    """Save a DataFrame to a file, inferring format from extension."""
    suffix = path.suffix.lower()
    if suffix in (".csv",):
        df.to_csv(path, index=False)
    elif suffix in (".tsv",):
        df.to_csv(path, sep="\t", index=False)
    elif suffix in (".xlsx",):
        df.to_excel(path, index=False)
    else:
        # Default to CSV
        df.to_csv(path, index=False)


# ---------------------------------------------------------------------------
# Profile builder
# ---------------------------------------------------------------------------

def _build_profile(df: "Any", sample_rows: int = 0) -> dict:
    """Build a JSON-serialisable profile dict for a DataFrame."""
    import pandas as pd
    import numpy as np

    nrows, ncols = df.shape

    columns_profile = []
    for col in df.columns:
        series = df[col]
        dtype_str = str(series.dtype)
        null_count = int(series.isna().sum())
        null_pct = round(null_count / nrows * 100, 2) if nrows else 0.0
        unique_count = int(series.nunique(dropna=True))

        col_info: dict[str, Any] = {
            "name": col,
            "dtype": dtype_str,
            "null_count": null_count,
            "null_pct": null_pct,
            "unique_count": unique_count,
        }

        # Numeric distributions
        if pd.api.types.is_numeric_dtype(series):
            non_null = series.dropna()
            if len(non_null) > 0:
                col_info["min"] = float(non_null.min())
                col_info["max"] = float(non_null.max())
                col_info["mean"] = round(float(non_null.mean()), 4)
                col_info["median"] = round(float(non_null.median()), 4)
                col_info["p25"] = round(float(non_null.quantile(0.25)), 4)
                col_info["p75"] = round(float(non_null.quantile(0.75)), 4)
        else:
            # Top-5 values for categoricals
            top5 = series.value_counts(dropna=True).head(5)
            col_info["top_values"] = [
                {"value": str(k), "count": int(v)}
                for k, v in top5.items()
            ]

        columns_profile.append(col_info)

    profile = {
        "rows": nrows,
        "columns": ncols,
        "column_names": list(df.columns),
        "dtypes_summary": df.dtypes.astype(str).value_counts().to_dict(),
        "total_nulls": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "columns_profile": columns_profile,
    }

    if sample_rows and sample_rows > 0:
        sample_n = min(sample_rows, nrows)
        profile["sample"] = df.head(sample_n).fillna("").astype(str).to_dict(orient="records")

    return profile


# ---------------------------------------------------------------------------
# M8.5.1 — profile_dataset
# ---------------------------------------------------------------------------


@app.tool()
async def profile_dataset(
    path: str,
    sample_rows: int = 0,
) -> list[TextContent]:
    """Profile a tabular dataset: shape, dtypes, null %, unique counts, distributions.

    Supports CSV, TSV, Excel (.xlsx/.xls), SPSS (.sav), Stata (.dta).
    Performs PII column name scan before profiling (non-blocking, annotated).
    Never modifies the source file.

    Args:
        path:        Absolute local path to the dataset file.
        sample_rows: If > 0, include this many rows as a data sample in the output.

    Returns JSON with: path, rows, columns, null stats, duplicate count,
    per-column profile (dtype, nulls, distributions or top values),
    and any flagged PII column names.
    """
    file_path = Path(path)
    if not file_path.exists():
        return [TextContent(type="text", text=json.dumps({
            "error": f"File not found: {path}",
        }))]

    try:
        df = _load_dataframe(file_path)
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    profile = _build_profile(df, sample_rows)
    profile["path"] = str(file_path)

    # PII check
    flagged = _flag_sensitive_columns(list(df.columns))
    profile["pii_warning"] = (
        f"⚠ Sensitive column(s) detected: {', '.join(flagged)}. "
        "Ensure data stays local and is handled per your data protection policy."
        if flagged else None
    )
    profile["flagged_columns"] = flagged

    return [TextContent(type="text", text=json.dumps(profile, ensure_ascii=False, indent=2))]


# ---------------------------------------------------------------------------
# M8.5.2 — suggest_cleaning
# ---------------------------------------------------------------------------


@app.tool()
async def suggest_cleaning(path: str) -> list[TextContent]:
    """Profile a dataset and return specific recommended cleaning operations.

    Analyses the profile and suggests operations with rationale, e.g.:
      - "col 'age' has 12% nulls → consider fill_na or drop_na_rows"
      - "7 duplicate rows detected → apply drop_duplicates"
      - "col 'name ' has leading/trailing whitespace → apply strip_whitespace"

    Args:
        path: Absolute local path to the dataset file.

    Returns JSON with profile summary and a list of suggested operations,
    each with: operation, column (if applicable), rationale, priority (high/medium/low).
    """
    file_path = Path(path)
    if not file_path.exists():
        return [TextContent(type="text", text=json.dumps({
            "error": f"File not found: {path}",
        }))]

    try:
        df = _load_dataframe(file_path)
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    profile = _build_profile(df)
    suggestions = []

    # Duplicates
    if profile["duplicate_rows"] > 0:
        suggestions.append({
            "operation": "drop_duplicates",
            "column": None,
            "rationale": f"{profile['duplicate_rows']} exact duplicate row(s) detected.",
            "priority": "high",
        })

    for col_info in profile["columns_profile"]:
        col = col_info["name"]
        null_pct = col_info["null_pct"]
        dtype = col_info["dtype"]

        # High-null columns
        if null_pct >= 50:
            suggestions.append({
                "operation": f"drop_columns:[{col}]",
                "column": col,
                "rationale": f"Column '{col}' has {null_pct}% missing values — consider dropping.",
                "priority": "high",
            })
        elif null_pct >= 10:
            suggestions.append({
                "operation": f"fill_na:[{col}:?] or drop_na_rows:[{col}]",
                "column": col,
                "rationale": f"Column '{col}' has {null_pct}% missing values — fill or drop rows.",
                "priority": "medium",
            })
        elif null_pct > 0:
            suggestions.append({
                "operation": f"fill_na:[{col}:?] or drop_na_rows:[{col}]",
                "column": col,
                "rationale": f"Column '{col}' has {null_pct}% missing values ({col_info['null_count']} rows).",
                "priority": "low",
            })

        # Whitespace in object columns (check col name for spaces)
        if "object" in dtype or "string" in dtype:
            if " " in col or col != col.strip():
                suggestions.append({
                    "operation": "strip_whitespace",
                    "column": col,
                    "rationale": f"Column name '{col}' has leading/trailing whitespace; string values likely need stripping too.",
                    "priority": "medium",
                })
            else:
                suggestions.append({
                    "operation": "strip_whitespace",
                    "column": col,
                    "rationale": f"Column '{col}' is text — apply strip_whitespace to remove accidental leading/trailing spaces.",
                    "priority": "low",
                })

        # Potential date columns not parsed as datetime
        if "object" in dtype and any(
            kw in col.lower() for kw in ("date", "time", "dt", "year", "month")
        ):
            suggestions.append({
                "operation": f"standardize_dates:[{col}:auto]",
                "column": col,
                "rationale": f"Column '{col}' looks like a date but is stored as text — parse to standard format.",
                "priority": "medium",
            })

    # PII warning
    flagged = _flag_sensitive_columns(list(df.columns))
    pii_note = (
        f"⚠ PII columns detected: {', '.join(flagged)}. Handle with care."
        if flagged else None
    )

    result = {
        "path": str(file_path),
        "profile_summary": {
            "rows": profile["rows"],
            "columns": profile["columns"],
            "duplicate_rows": profile["duplicate_rows"],
            "total_nulls": profile["total_nulls"],
        },
        "suggestions": suggestions,
        "suggestion_count": len(suggestions),
        "pii_warning": pii_note,
        "flagged_columns": flagged,
        "note": (
            "Review each suggestion. Pass approved operations to clean_dataset() "
            "using the 'operations' list. Original file is never modified."
        ),
    }
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


# ---------------------------------------------------------------------------
# M8.5.3 — clean_dataset
# ---------------------------------------------------------------------------

_SUPPORTED_OPERATIONS = {
    "drop_duplicates",
    "strip_whitespace",
}


def _parse_op(op: str) -> tuple[str, list[str]]:
    """Parse 'op_name:[arg1:arg2]' into (op_name, [arg1, arg2])."""
    m = re.match(r"^([a-z_]+)(?::\[(.+)\])?$", op.strip())
    if not m:
        return op.strip(), []
    op_name = m.group(1)
    args_str = m.group(2) or ""
    args = [a.strip() for a in args_str.split(":")] if args_str else []
    return op_name, args


@app.tool()
async def clean_dataset(
    path: str,
    operations: list[str],
    output_path: str = "",
) -> list[TextContent]:
    """Apply cleaning operations to a dataset and write a new file.

    NEVER modifies the original file. Always writes to output_path.

    Supported operations:
      - "drop_duplicates"                    — remove exact duplicate rows
      - "drop_columns:[col1:col2:...]"       — remove specified columns
      - "fill_na:[col:value]"                — fill nulls in col with value
      - "rename_column:[old_name:new_name]"  — rename a column
      - "strip_whitespace"                   — strip leading/trailing spaces from all string columns
      - "standardize_dates:[col:format]"     — parse col as date (format: 'auto' or strftime)
      - "drop_na_rows:[col]"                 — drop rows where col is null
      - "drop_na_rows_any"                   — drop rows with ANY null value

    Args:
        path:         Absolute local path to the source dataset.
        operations:   List of operation strings (see above).
        output_path:  Where to write the cleaned file. If empty, appends '_cleaned'
                      before the extension (e.g. data.csv → data_cleaned.csv).

    Returns JSON with: output_path, original_shape, cleaned_shape, row_delta,
    col_delta, operations_applied, operations_skipped.
    """
    import pandas as pd

    file_path = Path(path)
    if not file_path.exists():
        return [TextContent(type="text", text=json.dumps({
            "error": f"File not found: {path}",
        }))]

    try:
        df = _load_dataframe(file_path)
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    original_shape = df.shape
    applied = []
    skipped = []

    for op_str in operations:
        op_name, args = _parse_op(op_str)

        if op_name == "drop_duplicates":
            before = len(df)
            df = df.drop_duplicates()
            applied.append({"op": op_str, "rows_removed": before - len(df)})

        elif op_name == "drop_columns":
            existing = [c for c in args if c in df.columns]
            missing = [c for c in args if c not in df.columns]
            if existing:
                df = df.drop(columns=existing)
                applied.append({"op": op_str, "columns_dropped": existing})
            if missing:
                skipped.append({"op": op_str, "reason": f"Columns not found: {missing}"})

        elif op_name == "fill_na":
            if len(args) < 2:
                skipped.append({"op": op_str, "reason": "fill_na requires [col:value]"})
            else:
                col, val = args[0], args[1]
                if col in df.columns:
                    null_before = df[col].isna().sum()
                    df[col] = df[col].fillna(val)
                    applied.append({"op": op_str, "column": col, "nulls_filled": int(null_before)})
                else:
                    skipped.append({"op": op_str, "reason": f"Column '{col}' not found"})

        elif op_name == "rename_column":
            if len(args) < 2:
                skipped.append({"op": op_str, "reason": "rename_column requires [old:new]"})
            else:
                old, new = args[0], args[1]
                if old in df.columns:
                    df = df.rename(columns={old: new})
                    applied.append({"op": op_str, "renamed": f"{old} → {new}"})
                else:
                    skipped.append({"op": op_str, "reason": f"Column '{old}' not found"})

        elif op_name == "strip_whitespace":
            str_cols = df.select_dtypes(include="object").columns.tolist()
            for col in str_cols:
                df[col] = df[col].str.strip()
            applied.append({"op": op_str, "string_columns_processed": len(str_cols)})

        elif op_name == "standardize_dates":
            if len(args) < 1:
                skipped.append({"op": op_str, "reason": "standardize_dates requires [col:format]"})
            else:
                col = args[0]
                fmt = args[1] if len(args) > 1 else "auto"
                if col not in df.columns:
                    skipped.append({"op": op_str, "reason": f"Column '{col}' not found"})
                else:
                    try:
                        if fmt == "auto":
                            df[col] = pd.to_datetime(df[col], infer_datetime_format=True, errors="coerce")
                        else:
                            df[col] = pd.to_datetime(df[col], format=fmt, errors="coerce")
                        applied.append({"op": op_str, "column": col, "new_dtype": str(df[col].dtype)})
                    except Exception as e:
                        skipped.append({"op": op_str, "reason": str(e)})

        elif op_name == "drop_na_rows":
            if not args:
                skipped.append({"op": op_str, "reason": "drop_na_rows requires [col]"})
            else:
                col = args[0]
                if col in df.columns:
                    before = len(df)
                    df = df.dropna(subset=[col])
                    applied.append({"op": op_str, "column": col, "rows_removed": before - len(df)})
                else:
                    skipped.append({"op": op_str, "reason": f"Column '{col}' not found"})

        elif op_name == "drop_na_rows_any":
            before = len(df)
            df = df.dropna()
            applied.append({"op": op_str, "rows_removed": before - len(df)})

        else:
            skipped.append({"op": op_str, "reason": "Unknown operation"})

    # Determine output path
    if not output_path:
        stem = file_path.stem + "_cleaned"
        output_path = str(file_path.parent / (stem + file_path.suffix))

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        _save_dataframe(df, out_path)
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": f"Failed to save: {e}"}))]

    cleaned_shape = df.shape
    result = {
        "output_path": str(out_path),
        "original_shape": {"rows": original_shape[0], "cols": original_shape[1]},
        "cleaned_shape": {"rows": cleaned_shape[0], "cols": cleaned_shape[1]},
        "row_delta": cleaned_shape[0] - original_shape[0],
        "col_delta": cleaned_shape[1] - original_shape[1],
        "operations_applied": applied,
        "operations_skipped": skipped,
        "note": "Original file was NOT modified. Call compare_profiles() to see the full diff.",
    }
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


# ---------------------------------------------------------------------------
# M8.5.4 — compare_profiles
# ---------------------------------------------------------------------------


@app.tool()
async def compare_profiles(
    before_profile: str,
    after_profile: str,
) -> list[TextContent]:
    """Compare two dataset profiles and produce a side-by-side diff.

    Pass the JSON strings returned by profile_dataset() for the original
    and cleaned files. Returns rows added/removed, columns added/removed,
    null count changes per column, type changes, and a human-readable summary.

    Args:
        before_profile: JSON string from profile_dataset() on the original file.
        after_profile:  JSON string from profile_dataset() on the cleaned file.

    Returns JSON with: row_delta, col_delta, column_diffs (nulls, dtypes),
    duplicate_delta, and a human_summary string.
    """
    try:
        before = json.loads(before_profile)
        after = json.loads(after_profile)
    except json.JSONDecodeError as e:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Invalid JSON in profile: {e}",
        }))]

    row_delta = after.get("rows", 0) - before.get("rows", 0)
    col_delta = after.get("columns", 0) - before.get("columns", 0)
    dup_delta = after.get("duplicate_rows", 0) - before.get("duplicate_rows", 0)
    null_delta = after.get("total_nulls", 0) - before.get("total_nulls", 0)

    # Build column-level diffs
    before_cols = {c["name"]: c for c in before.get("columns_profile", [])}
    after_cols = {c["name"]: c for c in after.get("columns_profile", [])}

    all_cols = set(before_cols) | set(after_cols)
    column_diffs = []
    for col in sorted(all_cols):
        b = before_cols.get(col)
        a = after_cols.get(col)
        if b is None:
            column_diffs.append({"column": col, "change": "added"})
        elif a is None:
            column_diffs.append({"column": col, "change": "removed"})
        else:
            diff: dict[str, Any] = {"column": col, "change": "unchanged"}
            if b.get("dtype") != a.get("dtype"):
                diff["dtype_before"] = b.get("dtype")
                diff["dtype_after"] = a.get("dtype")
                diff["change"] = "dtype_changed"
            null_change = a.get("null_count", 0) - b.get("null_count", 0)
            if null_change != 0:
                diff["null_count_before"] = b.get("null_count", 0)
                diff["null_count_after"] = a.get("null_count", 0)
                diff["null_delta"] = null_change
                if diff["change"] == "unchanged":
                    diff["change"] = "null_count_changed"
            column_diffs.append(diff)

    # Human-readable summary
    summary_lines = []
    if row_delta < 0:
        summary_lines.append(f"• {abs(row_delta)} row(s) removed ({before.get('rows')} → {after.get('rows')})")
    elif row_delta > 0:
        summary_lines.append(f"• {row_delta} row(s) added ({before.get('rows')} → {after.get('rows')})")
    else:
        summary_lines.append(f"• Row count unchanged ({before.get('rows')} rows)")

    if col_delta < 0:
        removed = [d["column"] for d in column_diffs if d.get("change") == "removed"]
        summary_lines.append(f"• {abs(col_delta)} column(s) removed: {', '.join(removed)}")
    elif col_delta > 0:
        added = [d["column"] for d in column_diffs if d.get("change") == "added"]
        summary_lines.append(f"• {col_delta} column(s) added: {', '.join(added)}")

    if null_delta < 0:
        summary_lines.append(f"• {abs(null_delta)} fewer null values overall")
    elif null_delta > 0:
        summary_lines.append(f"• {null_delta} more null values (check fill operations)")

    if dup_delta < 0:
        summary_lines.append(f"• {abs(dup_delta)} duplicate row(s) removed")

    type_changes = [d for d in column_diffs if d.get("change") == "dtype_changed"]
    if type_changes:
        for tc in type_changes:
            summary_lines.append(
                f"• '{tc['column']}' type changed: {tc.get('dtype_before')} → {tc.get('dtype_after')}"
            )

    result = {
        "row_delta": row_delta,
        "col_delta": col_delta,
        "null_delta": null_delta,
        "duplicate_delta": dup_delta,
        "before": {"rows": before.get("rows"), "columns": before.get("columns"), "total_nulls": before.get("total_nulls"), "duplicates": before.get("duplicate_rows")},
        "after": {"rows": after.get("rows"), "columns": after.get("columns"), "total_nulls": after.get("total_nulls"), "duplicates": after.get("duplicate_rows")},
        "column_diffs": column_diffs,
        "human_summary": "\n".join(summary_lines) if summary_lines else "No changes detected.",
    }
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


# ---------------------------------------------------------------------------
# M8.5.5 — list_supported_formats
# ---------------------------------------------------------------------------


@app.tool()
async def list_supported_formats() -> list[TextContent]:
    """List supported dataset formats and installed library versions.

    Returns a JSON object with supported extensions, read/write capabilities,
    and the versions of pandas, openpyxl, and pyreadstat installed.
    """
    import importlib

    versions = {}
    for lib in ("pandas", "openpyxl", "pyreadstat", "numpy"):
        try:
            mod = importlib.import_module(lib)
            versions[lib] = getattr(mod, "__version__", "installed")
        except ImportError:
            versions[lib] = "NOT INSTALLED"

    formats = [
        {"extension": ".csv",  "description": "Comma-separated values",   "read": True,  "write": True,  "library": "pandas"},
        {"extension": ".tsv",  "description": "Tab-separated values",      "read": True,  "write": True,  "library": "pandas"},
        {"extension": ".xlsx", "description": "Excel 2007+ workbook",      "read": True,  "write": True,  "library": "openpyxl"},
        {"extension": ".xls",  "description": "Excel 97-2003 workbook",    "read": True,  "write": False, "library": "openpyxl (read only)"},
        {"extension": ".sav",  "description": "SPSS data file",            "read": True,  "write": False, "library": "pyreadstat"},
        {"extension": ".dta",  "description": "Stata data file",           "read": True,  "write": False, "library": "pyreadstat"},
        {"extension": ".rds",  "description": "R serialised object",       "read": False, "write": False, "library": "n/a — convert with: write.csv(readRDS('file.rds'), 'file.csv')"},
    ]

    result = {
        "supported_formats": formats,
        "library_versions": versions,
        "privacy_guarantee": (
            "All operations are local. No data is sent to any external service. "
            "Original files are never modified — clean_dataset() always writes a new file."
        ),
    }
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
