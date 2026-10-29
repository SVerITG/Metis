"""Data Memory — what Metis knows about the researcher's data, learned from code alone.

Metis never opens a data file. Everything here is read from analysis scripts
(.R, .Rmd, .qmd) and from the prose notes that sit beside them (CLAUDE.md,
README*.md): which files exist and where, which columns the code uses, which
values the code tests for, how derived variables are built, which scripts read
and write what, and which figures and tables they make. Whether a referenced
file still exists is checked with stat(), never by opening it.

The reason the previous scanner (tools/script_analyzer.py) did not work for real
projects: it recognised a read only when the path was a literal string inside the
call. Real projects set paths once — `path_cases <- file.path(dir_data, "x.xlsx")`
in a setup script that every other script source()s — and then call
`read_excel(path_cases)`. Measured 2026-10-29 on three script trees, 1,775 of
2,504 reads went through an object. This module evaluates path-building
expressions against the strings already assigned, following source() chains.

Plain Python, no MCP import: the MCP tools (tools/data_memory.py), the install
wizard and the dashboard all call the same functions. CLI:

    python -m metis_mcp.data_memory scan "<folder>" [--project ID]
    python -m metis_mcp.data_memory refresh
    python -m metis_mcp.data_memory status
    python -m metis_mcp.data_memory context "<question>"
"""

from __future__ import annotations

import datetime
import json
import math
import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator

# ── What is skipped while walking ────────────────────────────────────────────
# Copies of a project, installed packages and archives would bury the live
# scripts: in one dashboard tree, ~900 of ~1,080 .R files were history copies
# or installed packages.
SKIP_DIR_NAMES = {
    "history", "r_libs", "renv", "packrat", ".rproj.user", "_to_delete",
    "to_delete", "node_modules", ".git", ".quarto", "site-library",
    "__pycache__", ".venv", "venv",
}
SKIP_DIR_RE = re.compile(r"(?i)(\s-\scopy\b|\bcopy\s*\(\d+\)|^old$|^_old|_old$|^archive|^backup)")
SCRIPT_EXT = {".r", ".rmd", ".qmd"}
STORY_FILE_RE = re.compile(r"(?i)^(claude\.md|readme[^/]*\.md)$")
STORY_MAX_BYTES = 200_000

# ── R functions that touch files ─────────────────────────────────────────────
# name -> index of the positional argument holding the path, and the argument
# names that may hold it instead.
READ_FUNS: dict[str, int] = {
    "read_csv": 0, "read_csv2": 0, "read_tsv": 0, "read_delim": 0,
    "read.csv": 0, "read.csv2": 0, "read.delim": 0, "read.table": 0,
    "read_excel": 0, "read_xlsx": 0, "read_xls": 0, "read.xlsx": 0,
    "readWorkbook": 0, "loadWorkbook": 0, "excel_sheets": 0,
    "readRDS": 0, "read_rds": 0, "load": 0, "fread": 0, "vroom": 0,
    "st_read": 0, "read_sf": 0, "readOGR": 0, "shapefile": 0,
    "rast": 0, "raster": 0, "read_stars": 0, "brick": 0, "stack": 0,
    "read_dta": 0, "read_sav": 0, "read_sas": 0, "read_stata": 0,
    "read_parquet": 0, "read_feather": 0, "read_json": 0, "fromJSON": 0,
    "dbConnect": 1, "import": 0,
}
WRITE_FUNS: dict[str, int] = {
    "write_csv": 1, "write_csv2": 1, "write_tsv": 1, "write_delim": 1,
    "write.csv": 1, "write.csv2": 1, "write.table": 1, "fwrite": 1,
    "saveRDS": 1, "write_rds": 1, "save": -1, "write_xlsx": 1,
    "write.xlsx": 1, "saveWorkbook": 1, "st_write": 1, "write_sf": 1,
    "writeRaster": 1, "write_parquet": 1, "write_dta": 1, "export": 1,
    "ggsave": 0, "png": 0, "pdf": 0, "svg": 0, "jpeg": 0, "tiff": 0,
    "saveWidget": 1, "tmap_save": 1, "mapshot": -1, "gtsave": 1,
    "save_as_docx": -1, "save_as_image": -1, "save_as_html": -1,
}
PATH_ARG_NAMES = ("file", "path", "filename", "dsn", "x", "fname", "file_name",
                  "description", "dbname", "url")
FUN_RE = re.compile(
    r"(?<![\w.$])(?:[A-Za-z][\w.]*::)?("
    + "|".join(re.escape(f) for f in sorted(set(READ_FUNS) | set(WRITE_FUNS), key=len, reverse=True))
    + r")\s*\("
)

# Verbs whose arguments name columns.
COLUMN_VERBS = (
    "mutate|transmute|select|filter|group_by|arrange|rename|summarise|summarize|"
    "count|tally|distinct|pull|relocate|reframe|slice_max|slice_min|drop_na|fill|"
    "separate|unite|pivot_longer|pivot_wider|aes|add_count|replace_na|"
    "left_join|right_join|inner_join|full_join|anti_join|semi_join|join_by|st_join"
)
VERB_RE = re.compile(r"(?<![\w.])(?:\w+::)?(" + COLUMN_VERBS + r")\s*\(")
DERIVING_VERBS = {"mutate", "transmute", "summarise", "summarize", "reframe"}
R_WORDS = {
    "TRUE", "FALSE", "NULL", "NA", "NaN", "Inf", "NA_character_", "NA_real_",
    "NA_integer_", "T", "F", "if", "else", "function", "in", "for", "while",
    "return", "desc", "n", "everything", "where", "across", "c", "list",
    "starts_with", "ends_with", "contains", "matches", "any_of", "all_of",
    "na", "rm", "by", "groups", "keep", "drop", "after", "before", "sep",
    "names_to", "values_to", "names_from", "values_from", "cols", "fun",
    "sort", "wt", "name", "into", "remove", "convert", "multiple", "suffix",
    "relationship", "x", "y", "fill", "colour", "color", "group", "label",
    "size", "shape", "alpha", "linetype", "weight", "geometry", "default",
    "missing", "ties", "with_ties", "prop", "order_by", "levels", "labels",
}
VALUE_EQ_RE = re.compile(r"""\b([A-Za-z_][\w.]*)\s*(?:==|!=)\s*(["'])((?:(?!\2).){1,80})\2""")
VALUE_EQ_REV_RE = re.compile(r"""(["'])((?:(?!\1).){1,80})\1\s*(?:==|!=)\s*([A-Za-z_][\w.]*)\b""")
VALUE_IN_RE = re.compile(r"""\b([A-Za-z_][\w.]*)\s*%in%\s*c\s*\(([^()]{1,1500})\)""")
VALUE_DETECT_RE = re.compile(r"""\bstr_detect\s*\(\s*([A-Za-z_][\w.]*)\s*,\s*(["'])((?:(?!\2).){1,80})\2""")
VALUE_LEVELS_RE = re.compile(r"""\b(?:factor|fct_relevel)\s*\(\s*([A-Za-z_][\w.]*)\s*,\s*(?:levels\s*=\s*)?c\s*\(([^()]{1,1500})\)""")
STRING_RE = re.compile(r""""((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'""")
IDENT_RE = re.compile(r"(?<![\w.$@])([A-Za-z][\w.]*|\.[A-Za-z_][\w.]*)")
ASSIGN_RE = re.compile(r"^\s*([A-Za-z.][\w.]*(?:\$[\w.]+)?)\s*(?:<-|<<-|=(?!=))\s*(.+)$", re.S)
RIGHT_ASSIGN_RE = re.compile(r"^(.+?)\s*->\s*([A-Za-z.][\w.]*)\s*$", re.S)
SOURCE_RE = re.compile(r"(?<![\w.])source\s*\(")
SETWD_RE = re.compile(r"(?<![\w.])setwd\s*\(")
SECTION_RE = re.compile(r"^\s*#+\s*[-=#*]*\s*(.+?)\s*[-=#*]{3,}\s*$")
GEOM_RE = re.compile(r"\bgeom_(\w+)\s*\(")
CONTINUES_RE = re.compile(r"(%>%|\|>|%\w*%|\+|-|\*|/|,|<-|=|\(|\[|&|\||~|\^)\s*$")
FIG_EXT = {".png", ".pdf", ".svg", ".jpg", ".jpeg", ".tif", ".tiff", ".html", ".emf"}
TABLE_EXT = {".docx", ".xlsx", ".csv", ".tex", ".rtf"}


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


# ── Path forms ───────────────────────────────────────────────────────────────

_ON_WSL = os.path.isdir("/mnt/c")


def to_display(p: str) -> str:
    """The path as the researcher's R sees it (C:/... on a WSL host)."""
    m = re.match(r"^/mnt/([a-z])/(.*)$", p)
    return f"{m.group(1).upper()}:/{m.group(2)}" if m else p


def to_local(p: str) -> str:
    """The path as this process can stat it."""
    m = re.match(r"^([A-Za-z]):/(.*)$", p)
    if m and _ON_WSL:
        return f"/mnt/{m.group(1).lower()}/{m.group(2)}"
    return p


def norm_path(p: str) -> str:
    p = p.replace("\\\\", "/").replace("\\", "/")
    p = re.sub(r"/{2,}", "/", p)
    m = re.match(r"^([A-Za-z]):(/.*)?$", p)
    if m:
        p = m.group(1).upper() + ":" + (m.group(2) or "/")
    parts: list[str] = []
    for seg in p.split("/"):
        if seg == "..":
            if parts and parts[-1] not in ("", ".."):
                parts.pop()
            continue
        if seg == "." :
            continue
        parts.append(seg)
    return "/".join(parts)


def is_abs(p: str) -> bool:
    return bool(re.match(r"^([A-Za-z]:[/\\]|/|~)", p))


def dataset_key(p: str) -> str:
    return norm_path(p).lower()


# ── Low-level R text handling ────────────────────────────────────────────────

def strip_comment(line: str) -> str:
    """Remove a trailing # comment, leaving # inside strings alone."""
    q = None
    i = 0
    while i < len(line):
        ch = line[i]
        if q:
            if ch == "\\":
                i += 2
                continue
            if ch == q:
                q = None
        elif ch in ("'", '"', "`"):
            q = ch
        elif ch == "#":
            return line[:i]
        i += 1
    return line


def _depth_delta(line: str) -> int:
    d = 0
    q = None
    i = 0
    while i < len(line):
        ch = line[i]
        if q:
            if ch == "\\":
                i += 2
                continue
            if ch == q:
                q = None
        elif ch in ("'", '"', "`"):
            q = ch
        elif ch in "([":
            d += 1
        elif ch in ")]":
            d -= 1
        i += 1
    return d


def r_code_of(text: str, ext: str) -> str:
    """The R code of a script; for .Rmd/.qmd, only the R chunks."""
    if ext in (".rmd", ".qmd"):
        chunks = re.findall(r"```\{r[^}]*\}\s*\n(.*?)```", text, re.S | re.I)
        return "\n".join(chunks)
    return text


def statements(code: str) -> list[tuple[int, str]]:
    """Split R code into statements: a pipe chain or a multi-line call is one.

    Braces are not counted on purpose: an `if {}` block's inner lines then
    stay separate statements, which is what attribution wants.
    """
    out: list[tuple[int, str]] = []
    buf: list[str] = []
    depth = 0
    start = 0
    for n, raw in enumerate(code.splitlines(), 1):
        line = strip_comment(raw).rstrip()
        if not line.strip() or line.strip() in ("{", "}"):
            if buf and depth <= 0 and not CONTINUES_RE.search(buf[-1]):
                out.append((start, " ".join(buf)))
                buf = []
            continue
        if not buf:
            start = n
        buf.append(line.strip().strip("{}").strip() or line.strip())
        depth += _depth_delta(line)
        if depth <= 0 and not CONTINUES_RE.search(line):
            out.append((start, " ".join(buf)))
            buf = []
            depth = 0
    if buf:
        out.append((start, " ".join(buf)))
    return out


def call_args(s: str, open_idx: int) -> tuple[str, int]:
    """Text inside the parentheses that open at s[open_idx]."""
    depth = 0
    q = None
    i = open_idx
    while i < len(s):
        ch = s[i]
        if q:
            if ch == "\\":
                i += 2
                continue
            if ch == q:
                q = None
        elif ch in ("'", '"', "`"):
            q = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                return s[open_idx + 1:i], i
        i += 1
    return s[open_idx + 1:], len(s)


def split_args(s: str) -> list[str]:
    parts, depth, q, cur = [], 0, None, []
    i = 0
    while i < len(s):
        ch = s[i]
        if q:
            cur.append(ch)
            if ch == "\\" and i + 1 < len(s):
                cur.append(s[i + 1])
                i += 2
                continue
            if ch == q:
                q = None
        elif ch in ("'", '"', "`"):
            q = ch
            cur.append(ch)
        elif ch in "([{":
            depth += 1
            cur.append(ch)
        elif ch in ")]}":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        i += 1
    if "".join(cur).strip():
        parts.append("".join(cur).strip())
    return parts


def named_arg(arg: str) -> tuple[str | None, str]:
    m = re.match(r"^([A-Za-z.][\w.]*)\s*=(?!=)\s*(.*)$", arg, re.S)
    return (m.group(1), m.group(2).strip()) if m else (None, arg.strip())


def strings_in(s: str) -> list[str]:
    return [a or b for a, b in STRING_RE.findall(s)]


def _unquote(s: str) -> str | None:
    m = re.fullmatch(r"""\s*(["'])(.*)\1\s*""", s, re.S)
    return m.group(2).replace("\\\\", "\\") if m else None


# ── A tiny evaluator for path-building expressions ───────────────────────────

class Ctx:
    """What is known at a point in a script: string values and object origins."""

    def __init__(self, script: str, rproj_root: str | None):
        self.script = script
        self.script_dir = norm_path(to_display(os.path.dirname(script)))
        self.root = norm_path(to_display(rproj_root)) if rproj_root else None
        self.wd: str | None = None
        self.env: dict[str, str] = {}
        self.objs: dict[str, set[str]] = {}
        self.assigned: set[str] = set()   # every name assigned: never a column
        # Functions that read a file named by one of their parameters:
        # name -> {"params": [...], "reads": [(param, role, detail, def_script)]}
        self.functions: dict[str, dict[str, Any]] = {}
        # Late binding: "@fn:param" -> the real dataset keys seen at call sites
        self.bindings: dict[str, set[str]] = {}
        self.binding_paths: dict[str, str] = {}

    def enter(self, script: str, rproj_root: str | None) -> tuple:
        """Run a sourced script in this (global) environment, as R's source() does."""
        saved = (self.script, self.script_dir, self.root)
        self.script = script
        self.script_dir = norm_path(to_display(os.path.dirname(script)))
        if rproj_root:
            self.root = norm_path(to_display(rproj_root))
        return saved

    def leave(self, saved: tuple) -> None:
        self.script, self.script_dir, self.root = saved


THIS_SCRIPT_RE = re.compile(
    r"(?:rstudioapi::)?(?:getSourceEditorContext|getActiveDocumentContext)\(\)\$path"
    r"|(?:this\.path::)?this\.path\(\)|sys\.frame\(\s*1\s*\)\$ofile"
)


def eval_str(expr: str, ctx: Ctx, depth: int = 0, lenient: bool = False) -> str | None:
    """Evaluate a path-building expression to a string, or None if unknowable.

    `lenient` turns an unknown variable into a `{name}` placeholder, so a file
    family written in a loop — paste0(year, ".tif") — is kept as a pattern.
    """
    expr = expr.strip()
    if depth > 8 or not expr:
        return None
    lit = _unquote(expr)
    if lit is not None:
        return lit
    if THIS_SCRIPT_RE.fullmatch(expr):
        return norm_path(to_display(ctx.script))
    if re.fullmatch(r"(?:this\.path::)?this\.dir\(\)|(?:here::)?here\(\)|getwd\(\)", expr):
        return ctx.wd or ctx.root or ctx.script_dir if "getwd" in expr else (ctx.root or ctx.script_dir)
    m = re.fullmatch(r"""([A-Za-z.][\w.]*)(?:\$([\w.]+)|\[\[\s*["']([\w.]+)["']\s*\]\])""", expr)
    if m:
        v = ctx.env.get(f"{m.group(1)}${m.group(2) or m.group(3)}")
        if v is None and lenient:
            return "{" + (m.group(2) or m.group(3)) + "}"
        return v
    if re.fullmatch(r"[A-Za-z.][\w.]*", expr):
        v = ctx.env.get(expr)
        if v is None and lenient and expr not in R_WORDS:
            return "{" + expr + "}"
        return v
    if expr.startswith("{") and expr.endswith("}"):
        return eval_str(expr[1:-1], ctx, depth + 1, lenient)
    if re.match(r"^if\s*\(", expr):
        # if (unix) "/mnt/c/…" else "C:/…": the researcher's R runs on
        # Windows, so a drive-letter branch wins; otherwise the first that resolves.
        _, close = call_args(expr, expr.index("("))
        branches = re.split(r"\belse\b", expr[close + 1:], maxsplit=1)
        vals = [eval_str(b, ctx, depth + 1, lenient) for b in branches]
        vals = [v for v in vals if v]
        win = [v for v in vals if re.match(r"^[A-Za-z]:[/\\]", v)]
        return (win or vals or [None])[0]
    m = re.match(r"^(?:[A-Za-z]\w*::)?([A-Za-z_.][\w.]*)\s*\(", expr)
    if not m:
        return None
    fn = m.group(1)
    inner, end = call_args(expr, m.end() - 1)
    if expr[end + 1:].strip():
        return None
    args = split_args(inner)
    named = [named_arg(a) for a in args]
    pos = [v for k, v in named if k is None]
    kw = {k: v for k, v in named if k}

    def ev_all(items: Iterable[str]) -> list[str] | None:
        vals = [eval_str(a, ctx, depth + 1, lenient) for a in items]
        return None if any(v is None for v in vals) else vals  # type: ignore[return-value]

    if fn in ("tryCatch", "try", "suppressWarnings", "suppressMessages", "invisible") and pos:
        return eval_str(pos[0], ctx, depth + 1, lenient)
    if fn == "Sys.getenv":
        # The researcher's own default is what the code means on their machine.
        alt = kw.get("unset") or (pos[1] if len(pos) > 1 else None)
        return eval_str(alt, ctx, depth + 1, lenient) if alt else None
    if fn in ("dirname", "basename", "path_dir", "path_file", "tools::file_path_sans_ext",
              "file_path_sans_ext") and pos:
        v = eval_str(pos[0], ctx, depth + 1, lenient)
        if v is None:
            return None
        v = v.replace("\\", "/").rstrip("/")
        if fn in ("dirname", "path_dir"):
            return v.rsplit("/", 1)[0] if "/" in v else "."
        if fn in ("basename", "path_file"):
            return v.rsplit("/", 1)[-1]
        return os.path.splitext(v)[0]
    if fn in ("file.path", "path", "fs_path"):
        vals = ev_all(pos)
        return "/".join(v.rstrip("/\\") for v in vals) if vals else None
    if fn == "paste0":
        vals = ev_all(pos)
        return "".join(vals) if vals else None
    if fn == "paste":
        vals = ev_all(pos)
        sep = _unquote(kw.get("sep", '" "')) or ""
        return sep.join(vals) if vals else None
    if fn == "here":
        vals = ev_all(pos)
        base = ctx.root or ctx.script_dir
        return "/".join([base] + vals) if vals is not None else None
    if fn in ("normalizePath", "path.expand", "path_abs", "path_norm", "file.path.expand",
              "enc2utf8", "as.character", "trimws"):
        return eval_str(pos[0], ctx, depth + 1, lenient) if pos else None
    if fn in ("glue", "str_glue"):
        tpl = _unquote(pos[0]) if pos else None
        if tpl is None:
            return None
        def sub(mm: re.Match) -> str:
            v = ctx.env.get(mm.group(1).strip())
            if v is None:
                raise KeyError
            return v
        try:
            return re.sub(r"\{([^}]+)\}", sub, tpl)
        except KeyError:
            return None
    if fn in ("sprintf",):
        if not pos:
            return None
        fmt = _unquote(pos[0])
        vals = ev_all(pos[1:])
        if fmt is None or vals is None:
            return None
        try:
            return fmt % tuple(vals)
        except Exception:
            return None
    return None


def r_home(script_display_path: str) -> str | None:
    """Where `~` points for the researcher's R.

    R on Windows sets HOME to the Documents folder (OneDrive-redirected or
    not), so `~/2. Projects/x.csv` lives under Documents. METIS_R_HOME
    overrides, for a machine where that is not true.
    """
    env = os.environ.get("METIS_R_HOME")
    if env:
        return norm_path(env)
    m = re.match(r"^(.*?/Documents)(/|$)", script_display_path)
    return m.group(1) if m else None


def resolve(p: str, ctx: Ctx) -> str:
    if re.match(r"^(https?|s3|ftp)://", p, re.I):
        return p
    p = p.replace("\\\\", "/").replace("\\", "/")
    if p.startswith("~/") or p == "~":
        home = r_home(ctx.script_dir)
        if home:
            return norm_path(home + p[1:])
    if is_abs(p):
        return norm_path(p)
    base = ctx.wd or ctx.root or ctx.script_dir
    return norm_path(f"{base}/{p}")


# ── Script analysis ──────────────────────────────────────────────────────────

_rproj_cache: dict[str, str | None] = {}


def find_rproj_root(script_local: str, stop_at: str) -> str | None:
    d = os.path.dirname(script_local)
    stop = os.path.dirname(stop_at.rstrip("/"))
    while d and d.startswith(stop) and len(d) >= len(stop):
        if d in _rproj_cache:
            return _rproj_cache[d]
        try:
            if any(f.lower().endswith(".rproj") for f in os.listdir(d)):
                _rproj_cache[d] = d
                return d
        except OSError:
            pass
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return None


def _path_arg(fn: str, args: list[str], table: dict[str, int]) -> str | None:
    named = [named_arg(a) for a in args]
    for k, v in named:
        if k in PATH_ARG_NAMES and not (fn in WRITE_FUNS and k == "x"):
            return v
    pos = [v for k, v in named if k is None]
    idx = table.get(fn, 0)
    if idx < 0:
        return None
    if fn == "ggsave" and pos:
        return pos[0]
    return pos[idx] if len(pos) > idx else None


def _sheet(args: list[str]) -> str:
    for a in args:
        k, v = named_arg(a)
        if k in ("sheet", "layer"):
            return _unquote(v) or v
    return ""


def _idents(s: str) -> set[str]:
    s = STRING_RE.sub('""', s)
    return set(IDENT_RE.findall(s))


def _column_tokens(arg_text: str, deriving: bool) -> tuple[set[str], list[tuple[str, str]]]:
    """Column-like names in a verb's arguments, and (new, expr) pairs it derives."""
    cols: set[str] = set()
    derived: list[tuple[str, str]] = []
    for arg in split_args(arg_text):
        k, v = named_arg(arg)
        if k:
            if deriving and k not in R_WORDS and not k.startswith("."):
                derived.append((k, re.sub(r"\s+", " ", v)[:240]))
                cols.add(k)
            elif k in ("by",):
                for s in strings_in(v):
                    cols.add(s)
            body = v
        else:
            body = arg
        clean = STRING_RE.sub('""', body)
        for mm in re.finditer(r"(?<![\w.$@:])([A-Za-z][\w.]*|`[^`]+`)(\s*\(|::)?", clean):
            tok, is_call = mm.group(1).strip("`"), mm.group(2)
            if is_call or tok in R_WORDS or re.fullmatch(r"[A-Z_]{1,2}", tok):
                continue
            # skip argument names (`na.rm = TRUE`)
            after = clean[mm.end():mm.end() + 3]
            if re.match(r"\s*=(?!=)", after):
                continue
            cols.add(tok)
    return cols, derived


def _values(stmt: str) -> dict[str, set[str]]:
    vals: dict[str, set[str]] = {}
    def add(col: str, v: str) -> None:
        v = v.strip()
        if v and len(v) <= 80:
            vals.setdefault(col, set()).add(v)
    for m in VALUE_EQ_RE.finditer(stmt):
        add(m.group(1), m.group(3))
    for m in VALUE_EQ_REV_RE.finditer(stmt):
        add(m.group(3), m.group(2))
    for m in VALUE_IN_RE.finditer(stmt):
        for s in strings_in(m.group(2)):
            add(m.group(1), s)
    for m in VALUE_DETECT_RE.finditer(stmt):
        add(m.group(1), f"~{m.group(3)}")
    for m in VALUE_LEVELS_RE.finditer(stmt):
        for s in strings_in(m.group(2)):
            add(m.group(1), s)
    return vals


class ScriptResult:
    def __init__(self, path: str):
        self.path = path
        self.links: list[dict[str, Any]] = []      # role, key, path, object, detail
        self.columns: dict[tuple[str, str], dict[str, Any]] = {}
        self.unresolved: list[str] = []
        self.sources: list[str] = []
        self.figures: dict[str, Any] = {"geoms": set(), "kinds": set()}
        self.ctx: Ctx | None = None
        self.subs: list["ScriptResult"] = []       # scripts it source()d, run in its environment

    def col(self, key: str, name: str) -> dict[str, Any]:
        return self.columns.setdefault((key, name), {"values": set(), "derived": ""})

    def finalise(self) -> "ScriptResult":
        """Swap function-parameter placeholders for the files bound at call sites."""
        b = self.ctx.bindings if self.ctx else {}
        paths = self.ctx.binding_paths if self.ctx else {}
        links = []
        for ln in self.links:
            if not ln["key"].startswith("@"):
                links.append(ln)
                continue
            bound = b.get(ln["key"], set())
            if not bound:
                self.unresolved.append(f"{ln['detail_fn']}({ln['key'].split(':', 1)[1]}) in {ln['key'][1:].split(':')[0]}()")
            for k in bound:
                links.append({**ln, "key": k, "path": paths.get(k, k)})
        self.links = links
        cols: dict[tuple[str, str], dict[str, Any]] = {}
        for (k, name), info in self.columns.items():
            for real in (b.get(k, set()) if k.startswith("@") else {k}):
                c = cols.setdefault((real, name), {"values": set(), "derived": ""})
                c["values"] |= info["values"]
                c["derived"] = c["derived"] or info["derived"]
        self.columns = cols
        return self

    def richness(self) -> int:
        return 3 * len(self.links) + len(self.columns)


FUNDEF_RE = re.compile(r"^\s*([A-Za-z.][\w.]*)\s*(?:<-|=)\s*function\s*\(")


def analyse_script(local_path: str, scan_root: str, _stack: tuple[str, ...] = (),
                   shared: Ctx | None = None) -> ScriptResult:
    """Read one script's code (never its data) and return what it touches.

    With `shared`, the script runs in its caller's environment, as R's
    source() does: it sees the caller's paths and objects, and what it defines
    is visible to the caller afterwards.
    """
    res = ScriptResult(local_path)
    try:
        text = Path(local_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return res
    ext = os.path.splitext(local_path)[1].lower()
    code = r_code_of(text, ext)
    root = find_rproj_root(local_path, scan_root)
    if shared is not None:
        ctx = shared
        saved = ctx.enter(local_path, root)
    else:
        ctx = Ctx(local_path, root)
        saved = None
    res.ctx = ctx
    cur_fn: str | None = None

    for _line, st in statements(code):
        fm = FUNDEF_RE.match(st)
        if fm:
            inner, _ = call_args(st, fm.end() - 1)
            params = [(named_arg(a)[0] or a).strip() for a in split_args(inner)]
            cur_fn = fm.group(1)
            ctx.functions[cur_fn] = {"params": params, "reads": []}

        # source(): run the sourced script in this environment first
        for m in SOURCE_RE.finditer(st):
            inner, _ = call_args(st, m.end() - 1)
            args = split_args(inner)
            if not args:
                continue
            target = eval_str(named_arg(args[0])[1], ctx)
            if target is None:
                continue
            cands = [resolve(target, ctx)]
            if not is_abs(target):
                cands.append(norm_path(f"{ctx.script_dir}/{target}"))
                if ctx.root:
                    cands.append(norm_path(f"{ctx.root}/{target}"))
            for c in cands:
                lp = to_local(c)
                if os.path.isfile(lp) and lp not in _stack and lp != local_path and len(_stack) < 4:
                    res.subs.append(analyse_script(lp, scan_root, _stack + (local_path,), shared=ctx))
                    res.sources.append(lp)
                    break
        for m in SETWD_RE.finditer(st):
            inner, _ = call_args(st, m.end() - 1)
            v = eval_str(inner, ctx)
            if v:
                ctx.wd = resolve(v, ctx)

        # assignment
        lhs, rhs = None, st
        am = ASSIGN_RE.match(st)
        if am and not st.lstrip().startswith(("if", "for", "while", "function")):
            lhs, rhs = am.group(1), am.group(2)
        else:
            ram = RIGHT_ASSIGN_RE.match(st)
            if ram:
                lhs, rhs = ram.group(2), ram.group(1)
        if lhs:
            ctx.assigned.add(lhs.split("$")[0])
            sval = eval_str(rhs, ctx)
            if sval is not None:
                ctx.env[lhs] = sval
            lm = re.match(r"^\s*list\s*\(", rhs)
            if lm:   # CONFIG <- list(cases_file = file.path(...), ...)
                inner, _ = call_args(rhs, lm.end() - 1)
                for a in split_args(inner):
                    k, v = named_arg(a)
                    if k:
                        val = eval_str(v, ctx)
                        if val is not None:
                            ctx.env[f"{lhs}${k}"] = val

        # file reads and writes
        stmt_keys: set[str] = set()

        # calls to a function that reads the file it is given: bind the file
        for fname, fdef in ctx.functions.items():
            if not fdef["reads"] or fname == cur_fn and fm:
                continue
            for cm in re.finditer(r"(?<![\w.$])" + re.escape(fname) + r"\s*\(", st):
                inner, _ = call_args(st, cm.end() - 1)
                named = [named_arg(a) for a in split_args(inner)]
                pos = [v for k, v in named if k is None]
                kw = {k: v for k, v in named if k}
                for param in {r[0] for r in fdef["reads"]}:
                    idx = fdef["params"].index(param)
                    arg = kw.get(param) or (pos[idx] if len(pos) > idx else None)
                    val = eval_str(arg, ctx) if arg else None
                    if not val:
                        continue
                    full = resolve(val, ctx)
                    k = dataset_key(full)
                    ctx.bindings.setdefault(f"@{fname}:{param}", set()).add(k)
                    ctx.binding_paths[k] = full
                    stmt_keys.add(k)
                    if lhs:
                        ctx.objs[lhs] = ctx.objs.get(lhs, set()) | {k}
        for m in FUN_RE.finditer(st):
            fn = m.group(1)
            if fn == "stack" and "raster" not in st and "rast" not in st:
                continue
            inner, _ = call_args(st, m.end() - 1)
            args = split_args(inner)
            is_read = fn in READ_FUNS and not (fn in WRITE_FUNS)
            table = READ_FUNS if is_read else WRITE_FUNS
            parg = _path_arg(fn, args, table)
            if fn in ("save", "mapshot") or (fn.startswith("save_as_") and parg is None):
                for a in args:
                    k, v = named_arg(a)
                    if k in ("file", "path", "filename", "target"):
                        parg = v
            if parg is None:
                continue
            raw = eval_str(parg, ctx)
            if raw is None and cur_fn and parg.strip() in ctx.functions[cur_fn]["params"]:
                # A loader function: the file arrives as a parameter. Record it
                # against a placeholder; the call site supplies the real file.
                ph = f"@{cur_fn}:{parg.strip()}"
                ctx.functions[cur_fn]["reads"].append((parg.strip(), "read" if is_read else "write", fn))
                res.links.append({"role": "read" if is_read else "write", "key": ph, "path": "",
                                  "object": lhs or "", "detail": _sheet(args) if is_read else fn,
                                  "detail_fn": fn})
                if is_read:
                    stmt_keys.add(ph)
                    if lhs:
                        ctx.objs[lhs] = {ph}
                continue
            if raw is None and not is_read and parg.strip() == "file":
                continue   # a Shiny downloadHandler(content = function(file)): the browser's file
            if raw is None:
                # A file family (one file per year, per province…) is kept as a
                # pattern, but only when its folder is known: `{f}` alone says nothing.
                pat = eval_str(parg, ctx, lenient=True)
                if pat and "{" in pat and re.search(r"[/.]", pat.split("{")[0] + pat.rsplit("}", 1)[-1]) \
                        and not pat.startswith("{"):
                    raw = pat
                else:
                    res.unresolved.append(f"{fn}({parg[:80]})")
                    continue
            if fn == "dbConnect" and not re.search(r"\.(sqlite3?|db|duckdb)$", raw, re.I):
                continue
            full = resolve(raw, ctx)
            key = dataset_key(full)
            obj = lhs if is_read else (named_arg(args[0])[1] if args and fn not in
                                       ("ggsave", "png", "pdf", "svg", "jpeg", "tiff") else "")
            res.links.append({
                "role": "read" if is_read else "write", "key": key, "path": full,
                "object": obj or "", "detail": _sheet(args) if is_read else fn,
            })
            if is_read:
                stmt_keys.add(key)
                if lhs:
                    ctx.objs[lhs] = {key}

        # object lineage: an object built from known objects inherits their files
        ids = _idents(rhs) if lhs else _idents(st)
        from_objs: set[str] = set()
        for i in ids:
            if i in ctx.objs and i != lhs:
                from_objs |= ctx.objs[i]
        if lhs and lhs in ctx.objs and lhs in ids:
            from_objs |= ctx.objs[lhs]
        if lhs and from_objs and not stmt_keys:
            ctx.objs[lhs] = set(from_objs)
        keys = stmt_keys | from_objs
        # Past two source files an object is a combined table: crediting its
        # columns to every input made each file of one dashboard claim the
        # same 541 columns. A column is credited only while its origin is clear.
        if not keys or len(keys) > 2:
            continue

        # columns and the values the code tests for
        cols: set[str] = set()
        for vm in VERB_RE.finditer(st):
            verb = vm.group(1)
            inner, _ = call_args(st, vm.end() - 1)
            c, derived = _column_tokens(inner, verb in DERIVING_VERBS)
            cols |= c
            for new, expr in derived:
                for k in keys:
                    res.col(k, new)["derived"] = expr
        for dm in re.finditer(r"([A-Za-z.][\w.]*)\$([A-Za-z.][\w.]*|`[^`]+`)", st):
            obj, col = dm.group(1), dm.group(2).strip("`")
            for k in ctx.objs.get(obj, keys if obj == lhs else set()):
                res.col(k, col)
        for dm in re.finditer(r"""\[\[\s*["']([^"']+)["']\s*\]\]""", st):
            cols.add(dm.group(1))
        known = set(ctx.env) | set(ctx.objs) | ctx.assigned
        cols = {c for c in cols if c not in known and c != lhs and not c.startswith(".")}
        vals = _values(st)
        for c in cols | set(vals):
            if c in known:
                continue
            for k in keys:
                res.col(k, c)["values"] |= vals.get(c, set())

        for g in GEOM_RE.findall(st):
            res.figures["geoms"].add(g)

    low = code
    if "ggplot(" in low:
        res.figures["kinds"].add("map" if "geom_sf" in low or "coord_sf" in low else "chart")
    if re.search(r"\btm_shape\s*\(|\bleaflet\s*\(|\bmapview\s*\(", low):
        res.figures["kinds"].add("map")
    if re.search(r"\bplot_ly\s*\(|\bggplotly\s*\(", low):
        res.figures["kinds"].add("interactive chart")
    if re.search(r"\b(gt|flextable|kable|datatable|tbl_summary|reactable)\s*\(", low):
        res.figures["kinds"].add("table")
    if re.search(r"\b(shinyApp|fluidPage|dashboardPage|page_navbar|moduleServer)\s*\(", low):
        res.figures["kinds"].add("dashboard")
    if saved is not None:
        ctx.leave(saved)
    return res


def _flatten(res: ScriptResult) -> Iterator[ScriptResult]:
    yield res
    for s in res.subs:
        yield from _flatten(s)


def script_header(text: str, ext: str) -> tuple[str, list[str]]:
    """The opening comment block (purpose) and the section titles."""
    lines = text.splitlines()
    if ext in (".rmd", ".qmd"):
        m = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", text, re.M)
        purpose = m.group(1) if m else ""
    else:
        head: list[str] = []
        for ln in lines[:40]:
            s = ln.strip()
            if not s:
                if head:
                    break
                continue
            if not s.startswith("#"):
                break
            t = s.lstrip("#'").strip(" -=*#")
            if t and not re.fullmatch(r"[-=*#_ ]+", t):
                head.append(t)
        purpose = " ".join(head[:6])
    sections = []
    for ln in lines:
        m = SECTION_RE.match(ln)
        if m and len(m.group(1)) > 2:
            sections.append(m.group(1).strip(" -=#*"))
    return purpose[:500], sections[:40]


def style_of(code: str) -> dict[str, Any]:
    return {
        "magrittr_pipes": len(re.findall(r"%>%", code)),
        "native_pipes": len(re.findall(r"\|>", code)),
        "own_functions": len(re.findall(r"<-\s*function\s*\(", code)),
        "loops": len(re.findall(r"(?<![\w.])(for|while)\s*\(", code)),
        "apply_family": len(re.findall(r"(?<![\w.])(lapply|sapply|vapply|map\w*)\s*\(", code)),
        "uses_here": bool(re.search(r"\bhere\s*\(", code)),
        "data_table": bool(re.search(r"\bdata\.table\b|\bfread\s*\(", code)),
        "themes": sorted(set(re.findall(r"\b(theme_(?!minimal|bw|classic|void|light|dark|gray|grey|linedraw)\w+)\b", code)))[:10],
    }


def packages_of(code: str) -> list[str]:
    pk = set(re.findall(r"""(?:library|require)\s*\(\s*["']?([\w.]+)["']?""", code))
    for m in re.finditer(r"p_load\s*\(([^)]*)\)", code):
        pk |= {p.strip(" '\"") for p in m.group(1).split(",") if p.strip(" '\"").replace(".", "").isalnum()}
    pk |= set(re.findall(r"\b([A-Za-z][\w.]*)::", code))
    return sorted(pk - {"base", "utils", "stats"})


# ── Storage ──────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS dm_sources (
    root TEXT PRIMARY KEY, project_id TEXT DEFAULT '', label TEXT DEFAULT '',
    added_at TEXT, last_scan TEXT, n_scripts INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS dm_scripts (
    path TEXT PRIMARY KEY, root TEXT, project_id TEXT DEFAULT '', folder TEXT DEFAULT '',
    title TEXT, purpose TEXT DEFAULT '', sections TEXT DEFAULT '[]', lines INTEGER,
    mtime REAL, size INTEGER, deps TEXT DEFAULT '{}', packages TEXT DEFAULT '[]',
    figures TEXT DEFAULT '{}', style TEXT DEFAULT '{}', unresolved TEXT DEFAULT '[]',
    scanned_at TEXT);
CREATE TABLE IF NOT EXISTS dm_datasets (
    key TEXT PRIMARY KEY, path TEXT, name TEXT, folder TEXT, format TEXT,
    on_disk INTEGER, first_seen TEXT, last_seen TEXT);
CREATE TABLE IF NOT EXISTS dm_links (
    script_path TEXT, dataset_key TEXT, role TEXT, object TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS dm_columns (
    script_path TEXT, dataset_key TEXT, column_name TEXT, vals TEXT DEFAULT '[]',
    derived TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS dm_stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT, scope TEXT, target TEXT, source TEXT,
    source_path TEXT DEFAULT '', project_id TEXT DEFAULT '', text TEXT,
    created_at TEXT, updated_at TEXT);
CREATE INDEX IF NOT EXISTS ix_dm_links_ds ON dm_links(dataset_key);
CREATE INDEX IF NOT EXISTS ix_dm_links_sc ON dm_links(script_path);
CREATE INDEX IF NOT EXISTS ix_dm_cols_ds ON dm_columns(dataset_key);
CREATE INDEX IF NOT EXISTS ix_dm_cols_sc ON dm_columns(script_path);
CREATE UNIQUE INDEX IF NOT EXISTS ux_dm_story_file ON dm_stories(source_path) WHERE source = 'notes';
"""


def default_db() -> Path:
    from metis_mcp.config import paths  # local import keeps the module importable alone
    return Path(paths.db)


@contextmanager
def open_db(db: Path | None = None) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(db or os.environ.get("METIS_DATA_MEMORY_DB") or default_db()), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=15000")
    conn.executescript(SCHEMA)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ── Scanning ─────────────────────────────────────────────────────────────────

def _skip_dir(name: str) -> bool:
    return name.lower() in SKIP_DIR_NAMES or bool(SKIP_DIR_RE.search(name))


def walk(root: str) -> tuple[list[str], list[str]]:
    scripts, notes = [], []
    for dp, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not _skip_dir(d) and not d.startswith(".")]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            full = os.path.join(dp, f)
            if ext in SCRIPT_EXT:
                scripts.append(full)
            elif STORY_FILE_RE.match(f):
                notes.append(full)
    return sorted(scripts), sorted(notes)


def strip_tool_sections(md: str) -> str:
    """Drop instructions written for an assistant (e.g. '## Metis integration').

    A project note is kept for what it says about the work and the data; the
    sections telling an assistant which tools to call are noise in a story.
    """
    out, skip, level = [], False, 0
    for ln in md.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            if skip and len(m.group(1)) <= level:
                skip = False
            if re.search(r"(?i)\b(metis|mcp|claude code|integration|tools? to use)\b", m.group(2)):
                skip, level = True, len(m.group(1))
                continue
        if not skip:
            out.append(ln)
    return "\n".join(out)


def _deps_changed(deps: dict[str, float]) -> bool:
    for p, mt in deps.items():
        try:
            if os.path.getmtime(p) != mt:
                return True
        except OSError:
            return True
    return False


def scan(root: str, project_id: str = "", label: str = "", force: bool = False,
         db: Path | None = None) -> dict[str, Any]:
    """Learn from every script under `root`. Re-reads only what changed."""
    root_local = local_folder(root)
    if not os.path.isdir(root_local):
        raise FileNotFoundError(f"Not a folder: {root}")
    scripts, notes = walk(root_local)
    stats = {"root": to_display(root_local), "scripts": len(scripts), "rescanned": 0,
             "unchanged": 0, "removed": 0, "reads": 0, "writes": 0, "unresolved": 0,
             "notes": 0}
    now = _now()
    with open_db(db) as conn:
        conn.execute(
            "INSERT INTO dm_sources(root, project_id, label, added_at, last_scan, n_scripts) "
            "VALUES (?,?,?,?,?,?) ON CONFLICT(root) DO UPDATE SET last_scan=excluded.last_scan, "
            "n_scripts=excluded.n_scripts, project_id=CASE WHEN excluded.project_id!='' "
            "THEN excluded.project_id ELSE dm_sources.project_id END, label=CASE WHEN "
            "excluded.label!='' THEN excluded.label ELSE dm_sources.label END",
            (root_local, project_id, label, now, now, len(scripts)))
        known = {r["path"]: r for r in conn.execute(
            "SELECT path, mtime, size, deps FROM dm_scripts WHERE root = ?", (root_local,))}
        present = set(scripts)
        for gone in set(known) - present:
            for t in ("dm_links", "dm_columns"):
                conn.execute(f"DELETE FROM {t} WHERE script_path = ?", (gone,))
            conn.execute("DELETE FROM dm_scripts WHERE path = ?", (gone,))
            stats["removed"] += 1

        changed: dict[str, os.stat_result] = {}
        for sp in scripts:
            try:
                st = os.stat(sp)
            except OSError:
                continue
            old = known.get(sp)
            if (not force and old and old["mtime"] == st.st_mtime and old["size"] == st.st_size
                    and not _deps_changed(json.loads(old["deps"] or "{}"))):
                stats["unchanged"] += 1
                continue
            changed[sp] = st

        # A script is seen both on its own and inside every chain that source()s
        # it. Inside the chain it knows its caller's paths and objects, so the
        # richest view of each script is the one kept.
        best: dict[str, ScriptResult] = {}
        for sp in changed:
            for r in _flatten(analyse_script(sp, root_local)):
                r.finalise()
                if r.path in changed and (r.path not in best or r.richness() > best[r.path].richness()):
                    best[r.path] = r

        for sp, st in changed.items():
            res = best.get(sp) or ScriptResult(sp)
            text = Path(sp).read_text(encoding="utf-8", errors="replace")
            ext = os.path.splitext(sp)[1].lower()
            code = r_code_of(text, ext)
            purpose, sections = script_header(text, ext)
            rel = os.path.relpath(sp, root_local)
            folder = rel.split(os.sep)[0] if os.sep in rel else ""
            deps = {}
            for d in res.sources:
                try:
                    deps[d] = os.path.getmtime(d)
                except OSError:
                    pass
            figures = {"kinds": sorted(res.figures["kinds"]), "geoms": sorted(res.figures["geoms"])}
            conn.execute("DELETE FROM dm_links WHERE script_path = ?", (sp,))
            conn.execute("DELETE FROM dm_columns WHERE script_path = ?", (sp,))
            conn.execute(
                "INSERT OR REPLACE INTO dm_scripts(path, root, project_id, folder, title, purpose, "
                "sections, lines, mtime, size, deps, packages, figures, style, unresolved, scanned_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (sp, root_local, project_id, folder, os.path.basename(sp), purpose,
                 json.dumps(sections), text.count("\n") + 1, st.st_mtime, st.st_size,
                 json.dumps(deps), json.dumps(packages_of(code)), json.dumps(figures),
                 json.dumps(style_of(code)), json.dumps(res.unresolved[:50]), now))
            seen: set[tuple] = set()
            for ln in res.links:
                sig = (ln["role"], ln["key"], ln["object"], ln["detail"])
                if sig in seen:
                    continue
                seen.add(sig)
                _upsert_dataset(conn, ln["key"], ln["path"], now)
                conn.execute(
                    "INSERT INTO dm_links(script_path, dataset_key, role, object, detail) VALUES (?,?,?,?,?)",
                    (sp, ln["key"], ln["role"], ln["object"], ln["detail"]))
                stats["reads" if ln["role"] == "read" else "writes"] += 1
            for (key, name), info in res.columns.items():
                conn.execute(
                    "INSERT INTO dm_columns(script_path, dataset_key, column_name, vals, derived) VALUES (?,?,?,?,?)",
                    (sp, key, name, json.dumps(sorted(info["values"])[:60]), info["derived"]))
            stats["unresolved"] += len(res.unresolved)
            stats["rescanned"] += 1

        for np_ in notes:
            try:
                if os.path.getsize(np_) > STORY_MAX_BYTES:
                    continue
                txt = strip_tool_sections(Path(np_).read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
            if len(txt.strip()) < 40:
                continue
            folder = to_display(os.path.dirname(np_))
            row = conn.execute("SELECT id, text FROM dm_stories WHERE source='notes' AND source_path=?",
                               (np_,)).fetchone()
            if row and row["text"] == txt:
                continue
            if row:
                conn.execute("UPDATE dm_stories SET text=?, updated_at=? WHERE id=?", (txt, now, row["id"]))
            else:
                conn.execute(
                    "INSERT INTO dm_stories(scope, target, source, source_path, project_id, text, created_at, updated_at) "
                    "VALUES ('folder', ?, 'notes', ?, ?, ?, ?, ?)", (folder, np_, project_id, txt, now, now))
            stats["notes"] += 1
        conn.commit()
    return stats


def _upsert_dataset(conn: sqlite3.Connection, key: str, path: str, now: str) -> None:
    on_disk = None
    lp = to_local(path)
    drive = re.match(r"^(/mnt/[a-z])/", lp)
    if (is_abs(path) and not path.startswith("~") and "{" not in path
            and (not drive or os.path.isdir(drive.group(1)) and os.listdir(drive.group(1)))):
        on_disk = 1 if os.path.exists(lp) else 0   # stat only; the file is never opened
    name = os.path.basename(path.rstrip("/")) or path
    ext = os.path.splitext(name)[1].lower().lstrip(".") or ("folder" if on_disk and os.path.isdir(lp) else "")
    conn.execute(
        "INSERT INTO dm_datasets(key, path, name, folder, format, on_disk, first_seen, last_seen) "
        "VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET last_seen=excluded.last_seen, "
        "on_disk=excluded.on_disk",
        (key, path, name, os.path.dirname(path), ext, on_disk, now, now))


def local_folder(folder: str) -> str:
    """A folder as typed by a person (C:\\…, "C:/…", /mnt/c/…) → a path this process can use."""
    f = folder.strip().strip('"').strip("'").strip()
    if re.match(r"^[A-Za-z]:", f):
        f = to_local(norm_path(f))
    return f.rstrip("/\\") or f


def preview_folder(folder: str) -> dict[str, Any]:
    """How many scripts and notes a folder holds — counted by name, nothing read."""
    lf = local_folder(folder)
    if not os.path.isdir(lf):
        return {"folder": folder, "exists": False, "scripts": 0, "notes": 0}
    scripts, notes = walk(lf)
    return {"folder": to_display(lf), "exists": True, "scripts": len(scripts), "notes": len(notes)}


def register_source(folder: str, project_id: str = "", label: str = "",
                    db: Path | None = None) -> dict[str, Any]:
    """Remember a script folder without reading it yet (the wizard: learn later)."""
    lf = local_folder(folder)
    if not os.path.isdir(lf):
        raise FileNotFoundError(f"Not a folder: {folder}")
    with open_db(db) as conn:
        conn.execute(
            "INSERT INTO dm_sources(root, project_id, label, added_at, last_scan, n_scripts) "
            "VALUES (?,?,?,?,NULL,0) ON CONFLICT(root) DO NOTHING", (lf, project_id, label, _now()))
    return preview_folder(lf)


def forget_source(folder: str, db: Path | None = None) -> int:
    """Stop learning a folder and drop what was learnt from its scripts."""
    lf = local_folder(folder)
    with open_db(db) as conn:
        paths = [r[0] for r in conn.execute("SELECT path FROM dm_scripts WHERE root = ?", (lf,))]
        for p in paths:
            conn.execute("DELETE FROM dm_links WHERE script_path = ?", (p,))
            conn.execute("DELETE FROM dm_columns WHERE script_path = ?", (p,))
        conn.execute("DELETE FROM dm_scripts WHERE root = ?", (lf,))
        conn.execute("DELETE FROM dm_sources WHERE root = ?", (lf,))
        # files no remaining script mentions are no longer known
        conn.execute("DELETE FROM dm_datasets WHERE key NOT IN (SELECT dataset_key FROM dm_links)")
    return len(paths)


# A scan of a few hundred scripts takes ~30 s on a synced drive: long enough
# that a web request should not wait for it. One background run at a time.
JOB: dict[str, Any] = {"running": False, "started": None, "finished": None, "result": None, "error": None}


def start_background_refresh(db: Path | None = None) -> bool:
    import threading
    if JOB["running"]:
        return False

    def run() -> None:
        JOB.update(running=True, started=_now(), finished=None, result=None, error=None)
        try:
            JOB["result"] = refresh(db=db)
        except Exception as e:   # surfaced on the page, never raised into a request
            JOB["error"] = str(e)
        finally:
            JOB.update(running=False, finished=_now())

    threading.Thread(target=run, name="data-memory-refresh", daemon=True).start()
    return True


def list_datasets(conn: sqlite3.Connection, q: str = "", inputs_only: bool = True,
                  limit: int = 60) -> list[dict[str, Any]]:
    """Files for the overview: the most-read first, or the best matches for `q`."""
    if q.strip():
        rows = find_datasets(conn, q, limit=limit)
    else:
        rows = [dict(r) for r in conn.execute(
            "SELECT d.* FROM dm_datasets d JOIN (SELECT dataset_key, count(DISTINCT script_path) n "
            "FROM dm_links WHERE role='read' GROUP BY dataset_key) r ON r.dataset_key = d.key "
            "ORDER BY r.n DESC, d.name LIMIT ?", (limit,))]
    if not rows:
        return []
    keys = [r["key"] for r in rows]
    ph = ",".join("?" * len(keys))
    reads = {r[0]: r[1] for r in conn.execute(
        f"SELECT dataset_key, count(DISTINCT script_path) FROM dm_links WHERE role='read' "
        f"AND dataset_key IN ({ph}) GROUP BY dataset_key", keys)}
    cols = {r[0]: r[1] for r in conn.execute(
        f"SELECT dataset_key, count(DISTINCT column_name) FROM dm_columns WHERE dataset_key IN ({ph}) "
        f"GROUP BY dataset_key", keys)}
    out = []
    for r in rows:
        if inputs_only and not reads.get(r["key"]):
            continue
        out.append({**r, "n_readers": reads.get(r["key"], 0), "n_columns": cols.get(r["key"], 0),
                    "n_aliases": 0})
    # A reference to a file that is not on disk, where a file of the same name
    # IS on disk, is almost always the same file reached by an old or relative
    # path: fold it into the real one. Two copies that both exist stay apart.
    on_disk_names = {r["name"].lower(): r for r in out if r["on_disk"] == 1}
    kept = []
    for r in out:
        real = on_disk_names.get(r["name"].lower())
        if r["on_disk"] != 1 and real is not None:
            real["n_aliases"] += 1
            continue
        kept.append(r)
    return kept


def refresh(max_age_hours: float = 0, db: Path | None = None) -> list[dict[str, Any]]:
    """Re-scan every registered folder whose last scan is older than max_age_hours."""
    out = []
    with open_db(db) as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM dm_sources")]
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=max_age_hours)
    for r in rows:
        last = datetime.datetime.fromisoformat(r["last_scan"]) if r["last_scan"] else None
        if max_age_hours and last and last > cutoff:
            continue
        try:
            out.append(scan(r["root"], r["project_id"], r["label"], db=db))
        except FileNotFoundError as e:
            out.append({"root": r["root"], "error": str(e)})
    return out


# ── Stories the researcher tells ─────────────────────────────────────────────

def add_story(target: str, text: str, project_id: str = "", db: Path | None = None) -> str:
    """Attach a story to a dataset (by name or path) or a folder."""
    now = _now()
    with open_db(db) as conn:
        ds = find_datasets(conn, target, limit=1)
        if ds:
            scope, tgt = "dataset", ds[0]["key"]
        else:
            scope, tgt = "folder" if ("/" in target or "\\" in target) else "topic", norm_path(target)
        conn.execute(
            "INSERT INTO dm_stories(scope, target, source, project_id, text, created_at, updated_at) "
            "VALUES (?,?, 'researcher', ?, ?, ?, ?)", (scope, tgt, project_id, text.strip(), now, now))
        conn.commit()
    return f"{scope}:{ds[0]['name'] if ds else tgt}"


# ── Retrieval ────────────────────────────────────────────────────────────────

STOP = set("""a an the and or of to in on for with from by at is are was be this that these those
it its my our your we i you me do does did can could should would will how what which who when where why
make create new write script scripts analysis analyse analyze data dataset datasets file files using use
want need some all any per about into show plot figure table map r""".split())


def _terms(q: str) -> list[str]:
    toks = re.findall(r"[A-Za-zÀ-ÿ0-9_]{3,}", q.lower())
    return [t for t in toks if t not in STOP]


def find_datasets(conn: sqlite3.Connection, query: str, limit: int = 6) -> list[dict[str, Any]]:
    q = query.strip()
    if q:
        exact = conn.execute("SELECT * FROM dm_datasets WHERE key = ? OR lower(name) = ?",
                             (dataset_key(q), q.lower())).fetchall()
        if exact:
            return [dict(r) for r in exact][:limit]
    terms = _terms(q)
    if not terms:
        return []
    scores: dict[str, float] = {}
    n_all = conn.execute("SELECT count(*) FROM dm_datasets").fetchone()[0] or 1
    for t in terms:
        like = f"%{t}%"
        # A rare word (a project's own name) says more than a common one ("health").
        df = conn.execute(
            "SELECT count(*) FROM dm_datasets d WHERE lower(d.path) LIKE ? OR EXISTS (SELECT 1 FROM "
            "dm_columns c WHERE c.dataset_key = d.key AND lower(c.column_name) LIKE ?)", (like, like)).fetchone()[0]
        w = math.log((n_all + 1) / (df + 1)) + 0.5
        def add(k: str, pts: float) -> None:
            scores[k] = scores.get(k, 0) + pts * w
        for r in conn.execute("SELECT key FROM dm_datasets WHERE lower(name) LIKE ?", (like,)):
            add(r["key"], 4)
        for r in conn.execute("SELECT key FROM dm_datasets WHERE lower(folder) LIKE ?", (like,)):
            add(r["key"], 2)
        for r in conn.execute("SELECT DISTINCT dataset_key k FROM dm_columns WHERE lower(column_name) LIKE ?", (like,)):
            add(r["k"], 1.5)
        for r in conn.execute("SELECT DISTINCT dataset_key k FROM dm_columns WHERE lower(vals) LIKE ?", (like,)):
            add(r["k"], 1)
        for r in conn.execute(
                "SELECT DISTINCT l.dataset_key k FROM dm_links l JOIN dm_scripts s ON s.path = l.script_path "
                "WHERE lower(s.path) LIKE ? OR lower(s.purpose) LIKE ?", (like, like)):
            add(r["k"], 1)
        for r in conn.execute("SELECT target FROM dm_stories WHERE scope='dataset' AND lower(text) LIKE ?", (like,)):
            add(r["target"], 3)
    if not scores:
        return []
    # read data outranks figures written by a script
    rows = {r["key"]: dict(r) for r in conn.execute(
        f"SELECT * FROM dm_datasets WHERE key IN ({','.join('?' * len(scores))})", list(scores))}
    reads = {r["k"]: r["n"] for r in conn.execute(
        f"SELECT dataset_key k, count(DISTINCT script_path) n FROM dm_links WHERE role='read' AND dataset_key IN "
        f"({','.join('?' * len(scores))}) GROUP BY dataset_key", list(scores))}
    # Files some script reads are what a new analysis starts from; a file that
    # is only ever written (a dated export, a figure) ranks below them.
    ranked = sorted(rows.values(), key=lambda d: (-(scores[d["key"]] + min(reads.get(d["key"], 0), 10) * 0.5
                                                   - (0 if reads.get(d["key"]) else 3)
                                                   - (1.5 if d["format"] in ("png", "pdf", "svg", "html") else 0)),
                                                  d["name"]))
    return ranked[:limit]


def find_scripts(conn: sqlite3.Connection, query: str, limit: int = 5) -> list[dict[str, Any]]:
    terms = _terms(query)
    if not terms:
        return []
    scores: dict[str, float] = {}
    for t in terms:
        like = f"%{t}%"
        for r in conn.execute("SELECT path FROM dm_scripts WHERE lower(title) LIKE ? OR lower(folder) LIKE ?", (like, like)):
            scores[r["path"]] = scores.get(r["path"], 0) + 3
        for r in conn.execute("SELECT path FROM dm_scripts WHERE lower(purpose) LIKE ? OR lower(sections) LIKE ?", (like, like)):
            scores[r["path"]] = scores.get(r["path"], 0) + 2
        for r in conn.execute("SELECT path FROM dm_scripts WHERE lower(path) LIKE ?", (like,)):
            scores[r["path"]] = scores.get(r["path"], 0) + 1
        for r in conn.execute("SELECT DISTINCT script_path p FROM dm_columns WHERE lower(column_name) LIKE ?", (like,)):
            scores[r["p"]] = scores.get(r["p"], 0) + 1
        for r in conn.execute("SELECT path FROM dm_scripts WHERE lower(figures) LIKE ? OR lower(packages) LIKE ?", (like, like)):
            scores[r["path"]] = scores.get(r["path"], 0) + 1
    if not scores:
        return []
    top = sorted(scores, key=lambda p: -scores[p])[:limit]
    return [dict(conn.execute("SELECT * FROM dm_scripts WHERE path = ?", (p,)).fetchone()) for p in top]


def dataset_card(conn: sqlite3.Connection, key: str, max_cols: int = 40) -> dict[str, Any]:
    d = dict(conn.execute("SELECT * FROM dm_datasets WHERE key = ?", (key,)).fetchone())
    links = [dict(r) for r in conn.execute(
        "SELECT l.*, s.title FROM dm_links l LEFT JOIN dm_scripts s ON s.path = l.script_path "
        "WHERE l.dataset_key = ?", (key,))]
    cols: dict[str, dict[str, Any]] = {}
    for r in conn.execute("SELECT column_name, vals, derived, script_path FROM dm_columns WHERE dataset_key = ?", (key,)):
        c = cols.setdefault(r["column_name"], {"values": set(), "derived": "", "scripts": set()})
        c["values"] |= set(json.loads(r["vals"] or "[]"))
        if r["derived"] and not c["derived"]:
            c["derived"] = r["derived"]
        c["scripts"].add(r["script_path"])
    ranked = sorted(cols.items(), key=lambda kv: (-len(kv[1]["scripts"]), kv[0]))[:max_cols]
    d["columns"] = [{"name": k, "values": sorted(v["values"])[:25], "derived": v["derived"],
                     "used_in": len(v["scripts"])} for k, v in ranked]
    d["n_columns"] = len(cols)
    d["read_by"] = sorted({(to_display(l["script_path"]), l["object"], l["detail"]) for l in links if l["role"] == "read"})
    d["written_by"] = sorted({to_display(l["script_path"]) for l in links if l["role"] == "write"})
    d["stories"] = stories_for(conn, key, d["path"], [l["script_path"] for l in links])
    return d


def stories_for(conn: sqlite3.Connection, key: str, path: str, script_paths: list[str]) -> list[dict[str, Any]]:
    out = [dict(r) for r in conn.execute(
        "SELECT * FROM dm_stories WHERE scope='dataset' AND target = ? ORDER BY updated_at DESC", (key,))]
    folders = {norm_path(os.path.dirname(path)).lower()} | {
        norm_path(to_display(os.path.dirname(p))).lower() for p in script_paths}
    for r in conn.execute("SELECT * FROM dm_stories WHERE scope='folder'"):
        tgt = norm_path(r["target"]).lower()
        if any(f == tgt or f.startswith(tgt + "/") for f in folders):
            out.append(dict(r))
    # nearest notes first: the deepest folder is the most specific
    out.sort(key=lambda r: (r["scope"] != "dataset", -len(r["target"] or "")))
    return out


def _excerpt(text: str, terms: list[str], width: int = 700) -> str:
    # headings inside a note would masquerade as sections of this reply
    t = re.sub(r"(?m)^#{1,6}\s*", "", text)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    if len(t) <= width:
        return t
    low = t.lower()
    hits = [low.find(x) for x in terms if low.find(x) >= 0]
    start = max(0, min(hits) - 150) if hits else 0
    return ("…" if start else "") + t[start:start + width].strip() + "…"


RULES = (
    "DATA-PROTECTED MODE. Never open, read, preview, head, glimpse or summarise a data file, "
    "and never ask for rows. What Metis knows about the data comes from the researcher's own "
    "code and notes, below. Write an R script the researcher runs on their own computer; ask "
    "only for derived, non-identifying output (aggregates, figures) if anything comes back. "
    "Reuse the paths exactly as written, start from the closest existing script, and follow the "
    "researcher's recorded coding conventions. If a column or value is not below, say so and "
    "write the script to report it locally (names(), distinct()) instead of guessing."
)


def context(question: str, project_id: str = "", db: Path | None = None,
            max_chars: int = 9000) -> str:
    """Everything Metis knows that bears on `question`, as compact markdown."""
    terms = _terms(question)
    with open_db(db) as conn:
        n_scripts = conn.execute("SELECT count(*) FROM dm_scripts").fetchone()[0]
        n_ds = conn.execute("SELECT count(*) FROM dm_datasets").fetchone()[0]
        if not n_scripts:
            return ("Data Memory is empty: no script folders have been scanned yet. Ask the "
                    "researcher which folders hold their analysis scripts, then scan them.\n\n" + RULES)
        cands = find_datasets(conn, question, limit=30)
        scripts = find_scripts(conn, question, limit=5)
        parts = [f"## Data Memory — {n_ds} files known from {n_scripts} scripts", "", RULES, ""]
        if not cands and not scripts:
            parts.append(f"Nothing in the memory matches: {', '.join(terms) or question!r}. "
                         "Say so plainly; do not guess paths or columns.")
        # One card per file name: scripts in different folders reach the same
        # file by different relative paths. The copy that exists is shown.
        read_n = {r["k"]: r["n"] for r in conn.execute(
            "SELECT dataset_key k, count(*) n FROM dm_links WHERE role='read' GROUP BY dataset_key")}
        groups: dict[str, list[dict[str, Any]]] = {}
        for d in cands:
            groups.setdefault(d["name"].lower(), []).append(d)
        inputs, outputs = [], []
        for g in groups.values():
            g.sort(key=lambda d: (d["on_disk"] != 1, -read_n.get(d["key"], 0)))
            (inputs if any(read_n.get(d["key"]) for d in g) else outputs).append(g)
        seen_story: set[int] = set()
        for g in inputs[:5]:
            d = g[0]
            card = dataset_card(conn, d["key"], max_cols=25)
            disk = {1: "on disk", 0: "NOT FOUND on disk", None: "location unchecked"}[card["on_disk"]]
            parts.append(f"### {card['name']}  ({card['format'] or 'no extension'}, {disk})")
            parts.append(f"path: `{card['path']}`" + (f"  (also referenced by {len(g) - 1} other path(s))" if len(g) > 1 else ""))
            if card["read_by"]:
                rb = "; ".join(f"{Path(s).name}" + (f" as `{o}`" if o else "") + (f" sheet {x}" if x else "")
                               for s, o, x in card["read_by"][:6])
                parts.append(f"read by: {rb}" + (f" (+{len(card['read_by']) - 6})" if len(card["read_by"]) > 6 else ""))
            if card["written_by"]:
                parts.append("written by: " + ", ".join(Path(s).name for s in card["written_by"][:4]))
            if card["columns"]:
                cl = []
                for c in card["columns"]:
                    s = f"`{c['name']}`"
                    if c["values"]:
                        s += " ∈ {" + ", ".join(c["values"][:10]) + ("…" if len(c["values"]) > 10 else "") + "}"
                    if c["derived"]:
                        s += f" := {c['derived'][:120]}"
                    cl.append(s)
                parts.append(f"columns seen in code ({card['n_columns']}): " + "; ".join(cl))
            for s in card["stories"][:2]:
                if s["id"] in seen_story:
                    continue
                seen_story.add(s["id"])
                src = "researcher" if s["source"] == "researcher" else Path(s["source_path"]).name + " in " + Path(s["target"]).name
                parts.append(f"story ({src}): {_excerpt(s['text'], terms, 500)}")
            parts.append("")
        if outputs:
            parts.append("### Already produced by existing scripts")
            for g in outputs[:8]:
                d = g[0]
                w = conn.execute("SELECT script_path FROM dm_links WHERE dataset_key=? AND role='write' LIMIT 1",
                                 (d["key"],)).fetchone()
                parts.append(f"- {d['name']}" + (f" ← {Path(w[0]).name}" if w else "") + f"  `{d['folder']}`")
            parts.append("")
        if scripts:
            parts.append("### Closest existing scripts (templates)")
            for s in scripts:
                fig = json.loads(s["figures"] or "{}").get("kinds") or []
                st = json.loads(s["style"] or "{}")
                parts.append(f"- `{to_display(s['path'])}` — {s['purpose'][:160] or 'no header comment'}"
                             + (f" · makes: {', '.join(fig)}" if fig else "")
                             + f" · pipes {'%>%' if st.get('magrittr_pipes', 0) >= st.get('native_pipes', 0) else '|>'}"
                             + (f", own functions {st['own_functions']}" if st.get("own_functions") else "")
                             + (f", loops {st['loops']}" if st.get("loops") else ""))
            parts.append("")
        # notes about the folders the question names, even with no dataset hit
        if terms:
            for r in conn.execute("SELECT * FROM dm_stories ORDER BY scope='folder', updated_at DESC"):
                if r["id"] in seen_story or len(seen_story) >= 4:
                    continue
                hay = (r["target"] + " " + r["text"][:4000]).lower()
                if sum(1 for t in terms if t in hay) >= max(1, min(2, len(terms))):
                    seen_story.add(r["id"])
                    src = "researcher" if r["source"] == "researcher" else Path(r["source_path"]).name + " in " + Path(r["target"]).name
                    parts.append(f"story ({src}): {_excerpt(r['text'], terms, 600)}")
        out = "\n".join(parts)
    return out if len(out) <= max_chars else out[:max_chars] + "\n…(truncated — ask a narrower question)"


def status(db: Path | None = None) -> dict[str, Any]:
    with open_db(db) as conn:
        q = lambda sql: conn.execute(sql).fetchone()[0]
        unresolved = 0
        for r in conn.execute("SELECT unresolved FROM dm_scripts"):
            unresolved += len(json.loads(r["unresolved"] or "[]"))
        return {
            "sources": [dict(r) for r in conn.execute("SELECT * FROM dm_sources ORDER BY root")],
            "scripts": q("SELECT count(*) FROM dm_scripts"),
            "datasets": q("SELECT count(*) FROM dm_datasets"),
            "datasets_read": q("SELECT count(DISTINCT dataset_key) FROM dm_links WHERE role='read'"),
            "datasets_missing": q("SELECT count(*) FROM dm_datasets WHERE on_disk = 0"),
            # only files some script READS: an output not yet produced is not "missing"
            "inputs_missing": q("SELECT count(DISTINCT d.key) FROM dm_datasets d JOIN dm_links l "
                                "ON l.dataset_key = d.key AND l.role = 'read' WHERE d.on_disk = 0"),
            "reads": q("SELECT count(*) FROM dm_links WHERE role='read'"),
            "writes": q("SELECT count(*) FROM dm_links WHERE role='write'"),
            "columns": q("SELECT count(DISTINCT dataset_key || '|' || column_name) FROM dm_columns"),
            "columns_with_values": q("SELECT count(DISTINCT dataset_key || '|' || column_name) FROM dm_columns WHERE vals != '[]'"),
            "derived": q("SELECT count(DISTINCT dataset_key || '|' || column_name) FROM dm_columns WHERE derived != ''"),
            "stories": q("SELECT count(*) FROM dm_stories"),
            "unresolved_reads": unresolved,
        }


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)
    cmd = args[0]
    if cmd == "scan" and len(args) >= 2:
        pid = args[args.index("--project") + 1] if "--project" in args else ""
        print(json.dumps(scan(args[1], pid, force="--force" in args), indent=1))
    elif cmd == "refresh":
        print(json.dumps(refresh(), indent=1))
    elif cmd == "status":
        print(json.dumps(status(), indent=1, default=str))
    elif cmd == "context" and len(args) >= 2:
        print(context(" ".join(args[1:])))
    else:
        print(__doc__)
