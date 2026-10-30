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
    "read_fst": 0, "read.fst": 0, "qread": 0, "read_qs": 0,
    # a whole folder: the files it lists are read in a loop or a map()
    "list.files": 0, "dir_ls": 0,
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
    "write_fst": 1, "write.fst": 1, "qsave": 1, "write_qs": 1, "write_feather": 1,
}
PATH_ARG_NAMES = ("file", "path", "filename", "dsn", "x", "fname", "file_name",
                  "description", "dbname", "url")
LISTING_FUNS = {"list.files", "dir_ls"}


def _listing_suffix(args: list[str]) -> str:
    """'/**/*.<ext>' for list.files(dir, pattern = "\\.<ext>$", recursive = TRUE)."""
    named = [named_arg(a) for a in args]
    kw = {k: v for k, v in named if k}
    pos = [v for k, v in named if k is None]
    pat = _unquote(kw.get("pattern") or kw.get("regexp") or kw.get("glob")
                   or (pos[1] if len(pos) > 1 else '""')) or ""
    rec = (kw.get("recursive") or "").strip() in ("TRUE", "T")
    ext = re.search(r"\.\(?(?:\?i\))?([A-Za-z0-9|]+)", pat.replace("\\", ""))
    name = f"*.{ext.group(1)}" if ext else (f"[{pat}]" if pat else "*")
    return ("/**/" if rec else "/") + name


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


def scan_lines(code: str) -> list[dict[str, Any]]:
    """One pass over the whole file, aware of strings that span lines.

    For each physical line: its code without comments, the change in ( [
    depth outside strings, the { } depth at its start, and whether a string is
    still open at its end. Done per line, a JavaScript snippet inside
    HTML("…") over thirty lines once swallowed the rest of a helper file —
    and with it every function defined below it.
    """
    out: list[dict[str, Any]] = []
    q = None
    braces = 0
    for raw in code.split("\n"):
        info = {"text": "", "paren": 0, "brace": braces, "open": False}
        buf: list[str] = []
        i = 0
        while i < len(raw):
            ch = raw[i]
            if q:
                buf.append(ch)
                if ch == "\\" and i + 1 < len(raw):
                    buf.append(raw[i + 1])
                    i += 2
                    continue
                if ch == q:
                    q = None
            elif ch == "#":
                break
            else:
                if ch in ("'", '"', "`"):
                    q = ch
                elif ch in "([":
                    info["paren"] += 1
                elif ch in ")]":
                    info["paren"] -= 1
                elif ch == "{":
                    braces += 1
                elif ch == "}":
                    braces = max(0, braces - 1)
                buf.append(ch)
            i += 1
        info["text"] = "".join(buf).rstrip()
        info["open"] = q is not None
        out.append(info)
    return out


def statements(code: str) -> list[tuple[int, str]]:
    """Split R code into statements: a pipe chain or a multi-line call is one.

    Braces are not counted on purpose: an `if {}` block's inner lines then
    stay separate statements, which is what attribution wants. A string that
    spans lines keeps its statement open.
    """
    out: list[tuple[int, str]] = []
    buf: list[str] = []
    depth = 0
    start = 0
    for n, li in enumerate(scan_lines(code), 1):
        line = li["text"]
        if not li["open"] and (not line.strip() or line.strip() in ("{", "}")):
            if buf and depth <= 0 and not CONTINUES_RE.search(buf[-1]):
                out.append((start, " ".join(buf)))
                buf = []
            continue
        if not buf:
            start = n
        buf.append(line.strip().strip("{}").strip() or line.strip())
        depth += li["paren"]
        if depth <= 0 and not li["open"] and not CONTINUES_RE.search(line):
            out.append((start, " ".join(buf)))
            buf = []
            depth = 0
    if buf:
        out.append((start, " ".join(buf)))
    return out


def brace_depths(code: str) -> list[int]:
    """The { } depth at the start of each line, outside strings and comments."""
    return [li["brace"] for li in scan_lines(code)]


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
        # The running function's own variables. They never reach the global
        # environment: a `path <- ...` inside one helper once resolved another
        # helper's write to the wrong file.
        self.fn_env: dict[str, str] = {}
        # Functions that read a file named by one of their parameters:
        # name -> {"params": [...], "reads": [(param, role, detail, def_script)]}
        self.functions: dict[str, dict[str, Any]] = {}
        # Late binding: "@fn:param" -> the real dataset keys seen at call sites
        self.bindings: dict[str, set[str]] = {}
        self.binding_paths: dict[str, str] = {}
        self.binding_src: dict[str, set[str]] = {}     # a file a wrapper wrote -> what it saved
        self.key_paths: dict[str, str] = {}            # dataset key -> path as resolved
        # name -> (names, values) of a character vector: a column dictionary or a value list
        self.vectors: dict[str, tuple[list[str], list[str]]] = {}
        # in-code tables: key -> (name, script, source keys)
        self.tables: dict[str, tuple[str, str, set[str]]] = {}

    def lookup(self, name: str) -> str | None:
        v = self.fn_env.get(name)
        return v if v is not None else self.env.get(name)

    def child(self, bound: dict[str, str]) -> "Ctx":
        """A function's own environment at one call: its arguments bound by name.

        An argument that names a list (config = CONFIG) brings that list's
        entries along, so config$cache_folder resolves inside the helper.
        """
        c = Ctx.__new__(Ctx)
        c.__dict__.update(self.__dict__)
        c.env = {**self.env, **self.fn_env}
        c.fn_env = {}
        for p_, arg in bound.items():
            a = arg.strip()
            if re.fullmatch(r"[A-Za-z.][\w.]*", a) and any(k.startswith(a + "$") for k in self.env):
                for k, v in self.env.items():
                    if k.startswith(a + "$"):
                        c.env[p_ + k[len(a):]] = v
            v = eval_str(a, self)
            if v is not None:
                c.env[p_] = v
        return c

    def fn_regex(self) -> "re.Pattern | None":
        if getattr(self, "_fn_re_n", -1) != len(self.functions):
            names = sorted(self.functions, key=len, reverse=True)
            self._fn_re = re.compile(r"(?<![\w.$])(" + "|".join(map(re.escape, names)) + r")\s*\(") if names else None
            self._fn_re_n = len(self.functions)
        return self._fn_re

    def enter(self, script: str, rproj_root: str | None) -> tuple:
        """Run a sourced script in this (global) environment, as R's source() does."""
        saved = (self.script, self.script_dir, self.root, self.fn_env)
        self.fn_env = {}
        self.script = script
        self.script_dir = norm_path(to_display(os.path.dirname(script)))
        if rproj_root:
            self.root = norm_path(to_display(rproj_root))
        return saved

    def leave(self, saved: tuple) -> None:
        self.script, self.script_dir, self.root, self.fn_env = saved


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
    m = re.fullmatch(r"""([A-Za-z.][\w.]*)((?:\$[\w.]+|\[\[\s*["'][\w.]+["']\s*\]\])+)""", expr)
    if m:
        # CONFIG$files$cases or CONFIG[["files"]][["cases"]], any depth
        parts = re.findall(r"""\$([\w.]+)|\[\[\s*["']([\w.]+)["']\s*\]\]""", m.group(2))
        names = [a or b for a, b in parts]
        v = ctx.lookup(m.group(1) + "".join("$" + n for n in names))
        if v is None and lenient:
            return "{" + names[-1] + "}"
        return v
    if re.fullmatch(r"[A-Za-z.][\w.]*", expr):
        v = ctx.lookup(expr)
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

    fdef = ctx.functions.get(fn) if hasattr(ctx, "functions") else None
    if fdef and fdef.get("returns") and depth < 6:
        # cache_path("dm_x", config): bind the arguments, replay the function's
        # own assignments, and evaluate what it returns
        bound: dict[str, str] = {}
        for i_, p_ in enumerate(fdef["params"]):
            a_ = kw.get(p_) or (pos[i_] if i_ < len(pos) else fdef["defaults"].get(p_))
            if a_:
                bound[p_] = a_
        child = ctx.child(bound)
        for lv, rv in fdef["locals"]:
            v_ = eval_str(rv, child, depth + 1)
            if v_ is not None:
                child.env[lv] = v_
        return eval_str(fdef["returns"], child, depth + 1, lenient)
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
            v = ctx.lookup(mm.group(1).strip())
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


def _list_env(prefix: str, rhs: str, ctx: Ctx, depth: int = 0) -> None:
    """Record every string in a (nested) list under prefix$name$name…"""
    lm = re.match(r"^\s*list\s*\(", rhs)
    if not lm or depth > 4:
        return
    inner, _ = call_args(rhs, lm.end() - 1)
    for a in split_args(inner):
        k, v = named_arg(a)
        if not k:
            continue
        if re.match(r"^\s*list\s*\(", v):
            _list_env(f"{prefix}${k}", v, ctx, depth + 1)
            continue
        val = eval_str(v, ctx)
        if val is not None:
            ctx.env[f"{prefix}${k}"] = val


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
            if ln["role"] == "write" and bound:
                continue   # already credited to each calling script
            if not bound:
                self.unresolved.append(f"{ln['detail_fn']}({ln['key'].split(':', 1)[1]}) in {ln['key'][1:].split(':')[0]}()")
            for k in bound:
                src = self.ctx.binding_src.get(k, set()) if self.ctx else set()
                links.append({**ln, "key": k, "path": paths.get(k, k), "src": sorted(src)})
        for ln in links:   # a source named by placeholder becomes the files it was bound to
            ln["src"] = sorted({r for s_ in ln.get("src") or []
                                for r in (b.get(s_, set()) if s_.startswith("@") else {s_})})
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


def _call_link(role: str, key: str, full: str, lhs: str | None, pos: list[str],
               fname: str, handed: set[str]) -> dict[str, Any]:
    """The file a helper reads or writes, credited to the script that called it."""
    obj = lhs if role == "read" else next((a.strip() for a in pos
                                            if re.fullmatch(r"[A-Za-z.][\w.]*", a.strip())), "")
    return {"role": role, "key": key, "path": full, "object": obj or "",
            "detail": f"via {fname}()", "src": sorted(handed - {key}) if role == "write" else []}


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
    depths = brace_depths(code)
    fn_stack: list[tuple[str, int]] = []

    for _line, st in statements(code):
        depth = depths[_line - 1] if 0 < _line <= len(depths) else 0
        # a statement back at (or above) a function's own level: that body has ended
        while fn_stack and depth <= fn_stack[-1][1]:
            fn_stack.pop()
            ctx.fn_env = {}
        cur_fn = fn_stack[-1][0] if fn_stack else None
        fm = FUNDEF_RE.match(st)
        if fm:
            fn_stack.append((fm.group(1), depth))
            ctx.fn_env = {}
            inner, _ = call_args(st, fm.end() - 1)
            named_params = [named_arg(a) for a in split_args(inner)]
            params = [(k or v).strip() for k, v in named_params]
            cur_fn = fm.group(1)
            ctx.functions[cur_fn] = {"params": params, "reads": [], "templates": [], "locals": [],
                                     "defaults": {k: v for k, v in named_params if k}}
            # A data frame handed to the function is whatever the caller passes:
            # columns used on it inside are bound to that table at each call.
            for p_ in params:
                if p_ and p_ != "..." and re.fullmatch(r"[A-Za-z.][\w.]*", p_):
                    ctx.objs[p_] = {f"@{cur_fn}:{p_}"}
            # A definition is not an assignment: `f <- function(x)` must not make
            # `f` an object built from its own arguments. A one-line body is its
            # return value.
            ctx.objs.pop(cur_fn, None)
            body = st[call_args(st, fm.end() - 1)[1] + 1:].strip()
            if body:
                ctx.functions[cur_fn]["returns"] = body
            continue

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
        if lhs and cur_fn and not fm and len(ctx.functions[cur_fn]["locals"]) < 80:
            ctx.functions[cur_fn]["locals"].append((lhs, rhs))
        if cur_fn and not fm and not lhs:
            rm = re.match(r"^\s*return\s*\(", st)
            if rm:
                ctx.functions[cur_fn]["returns"] = call_args(st, rm.end() - 1)[0]
            elif not re.match(r"^\s*(if|else|for|while|repeat|message|warning|stop|cat|print|invisible|on\.exit|stopifnot)\b", st):
                ctx.functions[cur_fn]["returns"] = st
        if lhs:
            ctx.assigned.add(lhs.split("$")[0])
            sval = eval_str(rhs, ctx)
            if sval is not None:
                (ctx.fn_env if cur_fn and not fm else ctx.env)[lhs] = sval
            if re.match(r"^\s*list\s*\(", rhs):   # CONFIG <- list(files = list(cases = ...))
                _list_env(lhs, rhs, ctx)
            cm_ = re.match(r"^\s*c\s*\(", rhs)
            if cm_:   # VARS <- c(province = "prov_name", ...): a column dictionary or value list
                inner, _ = call_args(rhs, cm_.end() - 1)
                named = [named_arg(a) for a in split_args(inner)]
                strs = [_unquote(v) for _, v in named]
                if named and all(s_ is not None for s_ in strs):
                    ctx.vectors[lhs] = ([k for k, _ in named if k], [s_ for s_ in strs if s_])

        # file reads and writes
        stmt_keys: set[str] = set()

        # A loop or map() over a list of files hands each file to its reader:
        # `for (f in files)` and `lapply(files, read_csv)` read what `files` lists.
        fl = re.match(r"^\s*for\s*\(\s*([A-Za-z.][\w.]*)\s+in\s+(.+)\)\s*$", st)
        if fl:
            loop_keys = set().union(*[ctx.objs.get(i, set()) for i in _idents(fl.group(2))] or [set()])
            if loop_keys:
                ctx.objs[fl.group(1)] = loop_keys
        iter_keys: set[str] = set()
        for mm in re.finditer(r"(?<![\w.])(?:purrr::)?(?:lapply|sapply|vapply|map\w*|walk\w*|Map)\s*\(\s*([A-Za-z.][\w.]*)", st):
            iter_keys |= ctx.objs.get(mm.group(1), set())

        # calls to the researcher's own functions: bind what they are given
        fre = ctx.fn_regex()
        for cm in (fre.finditer(st) if fre else ()):
                fname = cm.group(1)
                fdef = ctx.functions.get(fname)
                if not fdef or (fm and fname == cur_fn):
                    continue
                inner, _ = call_args(st, cm.end() - 1)
                named = [named_arg(a) for a in split_args(inner)]
                pos = [v for k, v in named if k is None]
                kw = {k: v for k, v in named if k}
                bound_args: dict[str, str] = {}
                for i_, p_ in enumerate(fdef["params"]):
                    a_ = kw.get(p_) or (pos[i_] if i_ < len(pos) else fdef["defaults"].get(p_))
                    if a_:
                        bound_args[p_] = a_
                # objects handed to the call: what a writer saves
                handed = set().union(*[ctx.objs.get(v.strip(), set()) for v in pos + list(kw.values())
                                       if re.fullmatch(r"[A-Za-z.][\w.]*", v.strip())] or [set()])
                # a data frame argument: the function's placeholder is that table
                for p_, a_ in bound_args.items():
                    a_ = a_.strip()
                    if re.fullmatch(r"[A-Za-z.][\w.]*", a_) and ctx.objs.get(a_):
                        real = {k for k in ctx.objs[a_] if not k.startswith(f"@{fname}:")}
                        if real:
                            ctx.bindings.setdefault(f"@{fname}:{p_}", set()).update(real)
                # a path built inside the helper from its arguments: run the recipe
                for t in fdef["templates"]:
                    child = ctx.child(bound_args)
                    for lv, rv in t["locals"]:
                        v_ = eval_str(rv, child)
                        if v_ is not None:
                            child.env[lv] = v_
                    val = eval_str(t["expr"], child)
                    if not val:
                        continue
                    full = resolve(val, ctx)
                    if t["suffix"]:
                        full = full.rstrip("/") + t["suffix"]
                    k = dataset_key(full)
                    ctx.bindings.setdefault(t["ph"], set()).add(k)
                    ctx.binding_paths[k] = full
                    res.links.append(_call_link(t["role"], k, full, lhs, pos, fname, handed))
                    if t["role"] == "write":
                        ctx.binding_src.setdefault(k, set()).update(handed - {k})
                    else:
                        stmt_keys.add(k)
                        if lhs:
                            ctx.objs[lhs] = ctx.objs.get(lhs, set()) | {k}
                for param, role, _fn, suffix in {r for r in fdef["reads"]}:
                    arg = bound_args.get(param)
                    val = eval_str(arg, ctx) if arg else None
                    if not val:
                        continue
                    full = resolve(val, ctx)
                    if suffix:
                        full = full.rstrip("/") + suffix
                    k = dataset_key(full)
                    ctx.bindings.setdefault(f"@{fname}:{param}", set()).add(k)
                    ctx.binding_paths[k] = full
                    res.links.append(_call_link(role, k, full, lhs, pos, fname, handed))
                    if role == "write":
                        ctx.binding_src.setdefault(k, set()).update(handed - {k})
                        continue
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
            tmpl = False
            if cur_fn and parg.strip() not in ctx.functions[cur_fn]["params"]:
                fdef_ = ctx.functions[cur_fn]
                deps = _idents(parg)
                for _ in range(4):   # follow the recipe back through the function's own variables
                    for lv, rv in fdef_["locals"]:
                        if lv in deps:
                            deps |= _idents(rv)
                tmpl = bool(deps & set(fdef_["params"]))
            raw = None if tmpl else eval_str(parg, ctx)
            if tmpl:
                    ph = f"@{cur_fn}:#{len(fdef_['templates'])}"
                    fdef_["templates"].append({"expr": parg, "role": "read" if is_read else "write", "ph": ph,
                                               "locals": list(fdef_["locals"]),
                                               "suffix": _listing_suffix(args) if fn in LISTING_FUNS else ""})
                    res.links.append({"role": "read" if is_read else "write", "key": ph, "path": "",
                                      "object": lhs or "", "detail": _sheet(args) if is_read else fn,
                                      "detail_fn": fn})
                    if is_read:
                        stmt_keys.add(ph)
                        if lhs:
                            ctx.objs[lhs] = {ph}
                    continue
            if raw is None and cur_fn and parg.strip() in ctx.functions[cur_fn]["params"]:
                # A loader function: the file arrives as a parameter. Record it
                # against a placeholder; the call site supplies the real file.
                ph = f"@{cur_fn}:{parg.strip()}"
                suffix = _listing_suffix(args) if fn in LISTING_FUNS else ""
                ctx.functions[cur_fn]["reads"].append((parg.strip(), "read" if is_read else "write", fn, suffix))
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
            if raw is None and re.fullmatch(r"[A-Za-z.][\w.]*", parg.strip()):
                via = ctx.objs.get(parg.strip()) or iter_keys
                if via and is_read:
                    for k in via:
                        res.links.append({"role": "read", "key": k, "path": ctx.key_paths.get(k, ""),
                                          "object": lhs or "", "detail": _sheet(args), "detail_fn": fn})
                    stmt_keys |= via
                    if lhs:
                        ctx.objs[lhs] = set(via)
                    continue
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
            if fn in LISTING_FUNS:
                full = full.rstrip("/") + _listing_suffix(args)
            key = dataset_key(full)
            ctx.key_paths[key] = full
            obj = lhs if is_read else (named_arg(args[0])[1] if args and fn not in
                                       ("ggsave", "png", "pdf", "svg", "jpeg", "tiff") else "")
            res.links.append({
                "role": "read" if is_read else "write", "key": key, "path": full,
                "object": obj or "", "detail": _sheet(args) if is_read else fn,
                "src": sorted(ctx.objs.get(obj.strip(), set()) - {key}) if not is_read and obj else [],
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
        # Past two source files an object is a combined table. Crediting its
        # columns to every input made each file of one dashboard claim the
        # same 541 columns, and dropping them lost the dashboard's case table
        # altogether. So the combined object becomes a table of its own,
        # remembered with the files it was built from.
        # Argument placeholders are not files: they never make a table.
        real_keys = {k for k in keys if not k.startswith("@")}
        if len(real_keys) > 2 and lhs and "$" not in lhs:
            tkey = f"table:{norm_path(to_display(ctx.script)).lower()}::{lhs}"
            if tkey not in ctx.tables:
                ctx.tables[tkey] = (lhs, ctx.script, set())
                res.links.append({"role": "build", "key": tkey,
                                  "path": f"{norm_path(to_display(ctx.script))} :: {lhs}",
                                  "object": lhs, "detail": "", "src": []})
            ctx.tables[tkey][2].update(k for k in keys if k != tkey)
            ctx.objs[lhs] = {tkey}
            keys = {tkey}
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
        for mm in re.finditer(r"(?<![\w.])(?:all_of|any_of)\s*\(\s*([A-Za-z.][\w.]*)\s*\)", st):
            names_, values_ = ctx.vectors.get(mm.group(1), ([], []))
            cols |= set(names_) | set(values_)
        for mm in re.finditer(r"\bstr_detect\s*\(\s*([A-Za-z_][\w.]*)\s*,\s*([A-Za-z.][\w.]*)\s*[,)]", st):
            if ctx.lookup(mm.group(2)) is not None:
                vals.setdefault(mm.group(1), set()).add("~" + ctx.lookup(mm.group(2))[:80])
        for mm in re.finditer(r"\b([A-Za-z_][\w.]*)\s*%in%\s*([A-Za-z.][\w.]*)\b", st):
            for v_ in ctx.vectors.get(mm.group(2), ([], []))[1][:60]:
                vals.setdefault(mm.group(1), set()).add(v_)
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
    # 2026-10-30: a written file remembers the in-code table it was saved from
    if "src" not in {r[1] for r in conn.execute("PRAGMA table_info(dm_links)")}:
        conn.execute("ALTER TABLE dm_links ADD COLUMN src TEXT DEFAULT '[]'")
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


DEF_HEAD_RE = re.compile(r"(?i)^\s*#+.*\bdefinition")
DEF_LINE_RE = re.compile(r"^\s*#+'?\s*(?:DEFINITIONS?\s*:\s*)?([A-Z][A-Za-z /_-]{1,30}?)\s*(?:=|:=|:)\s+(\S.{8,})$")


def definitions_in(text: str) -> list[str]:
    """Agreed definitions written as comments ("ENDEMIC = at least one case…").

    Taken from a comment block headed by a line mentioning "definition", and
    from any comment line that starts "DEFINITION:". Continuation lines of a
    definition are joined to it.
    """
    out: list[str] = []
    in_block = False
    for ln in text.splitlines():
        st = ln.strip()
        if not st.startswith("#"):
            in_block = False
            continue
        if DEF_HEAD_RE.match(st) and not re.search(r"(?i)definition\s*:", st):
            in_block = True
            continue
        m = DEF_LINE_RE.match(st)
        body = st.lstrip("#' ").strip()
        if (in_block or re.match(r"(?i)^#+'?\s*definitions?\s*:", st)) and m:
            out.append(f"{m.group(1).strip()} = {m.group(2).strip()}")
        elif in_block and out and body and not re.match(r"^[-=#*]{3,}", body):
            out[-1] += " " + body
        elif in_block and not body:
            in_block = False
    return [d[:300] for d in out[:20]]


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
                _upsert_dataset(conn, ln["key"], ln["path"], now, obj=ln["object"])
                src = ln.get("src") or []
                if ln["role"] == "build" and res.ctx and ln["key"] in res.ctx.tables:
                    bnd = res.ctx.bindings
                    src = sorted({r for k_ in res.ctx.tables[ln["key"]][2]
                                  for r in (bnd.get(k_, set()) if k_.startswith("@") else {k_})})
                conn.execute(
                    "INSERT INTO dm_links(script_path, dataset_key, role, object, detail, src) VALUES (?,?,?,?,?,?)",
                    (sp, ln["key"], ln["role"], ln["object"], ln["detail"], json.dumps(src[:40])))
                stats[{"read": "reads", "write": "writes"}.get(ln["role"], "tables")] = \
                    stats.get({"read": "reads", "write": "writes"}.get(ln["role"], "tables"), 0) + 1
            for (key, name), info in res.columns.items():
                conn.execute(
                    "INSERT INTO dm_columns(script_path, dataset_key, column_name, vals, derived) VALUES (?,?,?,?,?)",
                    (sp, key, name, json.dumps(sorted(info["values"])[:60]), info["derived"]))
            stats["unresolved"] += len(res.unresolved)
            stats["rescanned"] += 1
            # Definitions written in the code's own comments are part of the story.
            conn.execute("DELETE FROM dm_stories WHERE source='code' AND source_path=?", (sp,))
            defs = definitions_in(text)
            if defs:
                conn.execute(
                    "INSERT INTO dm_stories(scope, target, source, source_path, project_id, text, created_at, updated_at) "
                    "VALUES ('folder', ?, 'code', ?, ?, ?, ?, ?)",
                    (to_display(os.path.dirname(sp)), sp, project_id,
                     f"Definitions in {os.path.basename(sp)}:\n" + "\n".join(defs), now, now))

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
    try:
        stats["vocab"] = export_vocab(db)
    except OSError:
        pass   # the hook then falls back to its generic words
    return stats


def _upsert_dataset(conn: sqlite3.Connection, key: str, path: str, now: str, obj: str = "") -> None:
    if key.startswith("table:"):
        # a table that exists only while a script runs: named by its object
        script = path.split(" :: ")[0]
        conn.execute(
            "INSERT INTO dm_datasets(key, path, name, folder, format, on_disk, first_seen, last_seen) "
            "VALUES (?,?,?,?,?,NULL,?,?) ON CONFLICT(key) DO UPDATE SET last_seen=excluded.last_seen",
            (key, path, obj or path.rsplit(" :: ", 1)[-1], os.path.dirname(script), "table in code", now, now))
        return
    fam = re.match(r"^(.*?)/(\*\*/)?(\*[^/]*|\[[^/]*\])$", path)
    if fam:
        # every file a folder listing returns: the folder is stat()ed, its files are not
        folder, pattern = fam.group(1), (fam.group(2) or "") + fam.group(3)
        lf = to_local(folder)
        on_disk = (1 if os.path.isdir(lf) else 0) if is_abs(folder) else None
        conn.execute(
            "INSERT INTO dm_datasets(key, path, name, folder, format, on_disk, first_seen, last_seen) "
            "VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET last_seen=excluded.last_seen, "
            "on_disk=excluded.on_disk",
            (key, path, f"{os.path.basename(folder)}/{pattern}", folder, "folder of files", on_disk, now, now))
        return
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


# ── The researcher's data vocabulary, for the prompt hook ────────────────────
# The hook that switches a session into data-protected mode cannot query the
# database in the few milliseconds it has, and a fixed keyword list is wrong
# for anyone but its author. So each scan writes the words of the researcher's
# own data — file, table, column and folder names, values the code tests for —
# to a small local file the hook reads. Measured 2026-10-30: with only generic
# keywords the hook missed "the endemic areas (villages and health zones) for
# 2026" and "how many villages had a case in 2025".

VOCAB_FILE = "data-vocab.json"
VOCAB_MIN_KINDS = 3
VOCAB_SKIP = set("""
data file files final copy version results result output outputs input inputs table tables
script scripts analysis analyse clean cleaned raw temp test tests archive backup draft new old
users onedrive documents desktop downloads program projects project scientific
xlsx xls csv rds rda shp gpkg fst tif tiff json txt docx pptx pdf png html sheet sheets folder
true false none null value values name names type types count total number list summary
from with into this that them they their there what when where which while have will would
year years date dates month months week weeks
today open create example examples solution solutions code nature skeleton classes class points
dashboard main help helpers utils config setup function functions index other others with without
make made show plot plots chart charts figure figures report reports check checks start end part
first second third last next previous before after above below more less only also just like
""".split()) | set("""
about again against almost along already always among another answer anything around away back
became because become been being best better between both bring build built call came cannot care
case change close come could course cover current days does done down each early easy either else
enough even ever every face fact feel find fine five follow form found four free full gave general
give given goes going good great group half hand hard head hear here high hold home however idea
important keep kind knew know large later lead leave left less life light line little live long look
lose lost made major many mean might mind miss most move much must near need never news nice night
note nothing often once open order over page paper past people perhaps place plan play point
possible power quite rather read real really right room round said same seem seen self sent several
shall short should side since small some something soon sort sound space speak stand state still
stop such sure take taken tell than thank thanks then thing things think those though thought three
through time together told took toward true turn under until upon used useful using very view want
well went were whole whose wide will wish within word words work works world would write wrong yes
young your yourself better best good great nice page pages look looks layout style colour color
""".split())


def vocab_path(db: Path | None = None) -> Path:
    return Path(db or os.environ.get("METIS_DATA_MEMORY_DB") or default_db()).parent / VOCAB_FILE


def _words(text: str) -> list[str]:
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)   # camelCase → camel Case
    return [w for w in re.split(r"[^A-Za-zÀ-ÿ]+", text.lower()) if len(w) >= 4 and w not in VOCAB_SKIP]


def export_vocab(db: Path | None = None, limit: int = 3000) -> int:
    """Write the researcher's data words to data-vocab.json beside the database.

    A word is kept only when it turns up in at least VOCAB_MIN_KINDS different
    kinds of place — file names, folders, columns, values, script titles. The
    subject of the data ("endemic", a region, a test) is everywhere; a word that
    only one folder or one file name carries ("claude", "server", "surface") is
    not about the data. Measured on 621 real prompts: counting every word made
    the hook fire on 39% of them, mostly work on the software itself.
    """
    counts: dict[str, int] = {}
    kinds: dict[str, set[str]] = {}

    def add(kind: str, text: str) -> None:
        for w in set(_words(text or "")):
            counts[w] = counts.get(w, 0) + 1
            kinds.setdefault(w, set()).add(kind)

    with open_db(db) as conn:
        for r in conn.execute("SELECT name, folder FROM dm_datasets"):
            add("file", r["name"])
            add("folder", "/".join((r["folder"] or "").split("/")[-3:]))   # nearest folders only
        for r in conn.execute("SELECT DISTINCT column_name, vals FROM dm_columns"):
            add("column", r["column_name"])
            for v in json.loads(r["vals"] or "[]")[:20]:
                add("value", v.lstrip("~"))
        for r in conn.execute("SELECT title, folder FROM dm_scripts"):
            add("title", r["title"])
            add("script_folder", r["folder"])
        # The path down to each script folder (user name, cloud drive,
        # organisation) is on every file and says nothing about the data.
        above = {w for r in conn.execute("SELECT root FROM dm_sources") for w in _words(r["root"])}
    keep = [w for w in counts if len(kinds[w]) >= VOCAB_MIN_KINDS and w not in above]
    terms = sorted(keep, key=lambda w: (-counts[w], w))[:limit]
    path = vocab_path(db)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"updated": _now(), "terms": terms}, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
    return len(terms)


# ── Is this a data request? (the same rules as .claude/hooks/data-mode.mjs) ──
# Claude Desktop runs no hooks, so the server makes the same judgement on the
# text of the first Metis tool a conversation calls and attaches the data-mode
# instruction there. tests/unit/test_data_mode_hook.py holds the two in step.

_STRONG = re.compile(r"\b(" + "|".join([
    "datasets?", r"[\w-]+\.(r|rmd|qmd)", "data ?files?", "data ?bases?", "databank", "variables?", "columns?",
    "r ?scripts?", "rscript", "tidyverse", "dplyr", "ggplot2?", "data ?frames?",
    "csv", "xlsx?", "excel", "spreadsheets?", "shapefiles?", "rasters?", "geopackage",
    "rds", "stata", "spss", "line ?list", "codebook", "data ?dictionary",
    "unique values", "missing values", "denominators?",
    "gegevens", "databestand", "kolommen?", "variabelen?", r"donn[ée]es", r"fichier de donn[ée]es",
    "colonnes?", "tableur"]) + r")\b", re.I)
_WEAK = re.compile(r"\b(" + "|".join([
    "data", "analy[sz]e", "analys[ie]s", "analytic", "scripts?", "plots?", "charts?",
    "figures?", "maps?", "mapping", "tables?", r"visuali[sz]\w*", "regression", "models?",
    "merge", "join", "clean(ing)?", "recode", "aggregate", "summar(y|ies|ise|ize)",
    "dashboards?", "panels?", "trends?", "per (year|month|province|district|region|village|site|zone|area)",
    "incidence", "prevalence", "positivity", "coverage", "cases", "counts?", "rates?",
    "surveillance", "cohort", "survey", "screen(ed|ing)", "how many", "number of",
    "compare", "comparison", "distribution", "over time", "by year", r"in \d{4}", r"for \d{4}",
    r"between \d{4}", r"since \d{4}", "indicators?", "endemic", "proportion", "percentage",
    "analyse", "kaart", "tabel", "grafiek", "figuur", "gevallen", "hoeveel", "per jaar",
    "aantal", r"vergelijk\w*", "verdeling", "dorpen", "bestand",
    "carte", "tableau", "graphique", "cas", "combien", r"par ann[ée]e", "nombre de",
    "comparer", r"r[ée]partition", "fichier", "villages"]) + r")\b", re.I)
_SYSTEM_WORK = re.compile(r"\b(mcp|hooks?|fastapi|htmx|endpoint|routes?|frontend|css|javascript|node|sqlite|the wizard|installer|subagents?|tool ?calls?|pull request|commit|github|release|restyle|layout|spacing|fonts?|buttons?|cards?|navbar|sidebar|dark mode|light mode|surfaces?|briefings?|morning brief|news|feeds?|calendar|reminders?|install(ed|ing|ation)?|launch(es|ed)?|localhost|claude desktop|claude code|handoff|env\w* ?variables?|envi\w*ment\w* variables?|api ?keys?)\b", re.I)
_NAMES_R_OR_FILE = re.compile(r"\b(r ?scripts?|rscript|\.r\b|\.rmd|\.qmd|csv|xlsx?|shapefile|dataset)\b", re.I)
_OTHER_INTENT = re.compile(r"\b(literature|papers?|articles?|references?|citations?|cite|evidence|review|draft|paragraph|abstract|manuscript|introduction|discussion|slides?|presentation|deck|poster|email|letter|artikel|littérature|article|course|lessons?|exercises?|quiz|learners?|ideas?|strategy document)\b", re.I)
_ANALYSIS_ASK = re.compile(r"\b(how many|number of|maps?|tables?|plots?|charts?|figures?|graphs?|scripts?|counts?|compare|trends?|per year|by year|hoeveel|kaart|tabel|grafiek|combien|carte|tableau|graphique)\b", re.I)


def load_vocab(db: Path | None = None) -> set[str]:
    try:
        return set(json.loads(vocab_path(db).read_text(encoding="utf-8")).get("terms") or [])
    except (OSError, ValueError):
        return set()


def is_data_request(text: str, terms: set[str] | None = None) -> bool:
    """Does this prompt ask for work on the researcher's data?"""
    terms = load_vocab() if terms is None else terms
    words = {w for w in re.split(r"[^a-zà-ÿ]+", text.lower()) if len(w) >= 4}
    own = len(words & terms)
    strong = bool(_STRONG.search(text))
    weak = len({m.group(0).lower() for m in _WEAK.finditer(text)})
    if _SYSTEM_WORK.search(text) and not _NAMES_R_OR_FILE.search(text) and own < 2:
        return False
    if _OTHER_INTENT.search(text) and not strong and not _ANALYSIS_ASK.search(text):
        return False
    return strong or weak >= 2 or (own >= 1 and weak >= 1) or own >= 2


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
    # A word that names a folder on the file's path ("…the cases are in the
    # dashboard") says WHERE to look: it scales the score instead of adding a
    # little to it, so it can outweigh a file that merely shares more words.
    for d in rows.values():
        folder = (d["folder"] or "").lower()
        hits = sum(1 for t in terms if re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", folder))
        if hits:
            scores[d["key"]] *= 1 + 0.6 * hits
    # Files some script reads are what a new analysis starts from; a file that
    # is only ever written (a dated export, a figure) ranks below them.
    ranked = sorted(rows.values(), key=lambda d: (-(scores[d["key"]] + min(reads.get(d["key"], 0), 10) * 0.5
                                                   - (0 if reads.get(d["key"]) or d["format"] in PROCESSED_FORMATS else 3)
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
    # A file written from an in-code table carries that table's columns; a
    # table shows the files it was built from. One hop, so nothing cycles.
    saved_from = sorted({k for l in links if l["role"] == "write"
                         for k in json.loads(l.get("src") or "[]") if k != key and not k.startswith("@")})
    built_from = sorted({k for l in links if l["role"] == "build"
                         for k in json.loads(l.get("src") or "[]") if k != key and not k.startswith("@")})
    col_keys = [key] + saved_from
    cols: dict[str, dict[str, Any]] = {}
    for r in conn.execute(
            f"SELECT column_name, vals, derived, script_path FROM dm_columns WHERE dataset_key IN "
            f"({','.join('?' * len(col_keys))})", col_keys):
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

    def names(keys: list[str]) -> list[str]:
        if not keys:
            return []
        rows = conn.execute(f"SELECT key, name FROM dm_datasets WHERE key IN ({','.join('?' * len(keys))})", keys)
        got = {r["key"]: r["name"] for r in rows}
        return [got.get(k, k.rsplit("/", 1)[-1]) for k in keys]

    d["saved_from"] = names(saved_from)
    d["built_from"] = names(built_from)
    d["built_from_files"] = [k for k in built_from if not k.startswith(("table:", "@"))]
    d["built_in"] = sorted({to_display(l["script_path"]) for l in links if l["role"] == "build"})
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


# Machine formats a pipeline saves for the next step: a processed table to
# start from, unlike a figure or a report table, which is an end product.
PROCESSED_FORMATS = {"fst", "rds", "rda", "rdata", "qs", "parquet", "feather", "arrow", "sqlite", "duckdb"}

GENERIC_OBJECT_NAMES = {
    "values", "rv", "session", "input", "output", "res", "out", "result", "results", "df", "d",
    "x", "y", "data", "dat", "tmp", "temp", "tbl", "tab", "raw", "obj", "all", "combined", "merged",
}

RULES = (
    "DATA-PROTECTED MODE. Never open, read, preview, head, glimpse or summarise a data file, "
    "and never ask for rows. What Metis knows about the data comes from the researcher's own "
    "code and notes, below. Write an R script the researcher runs on their own computer; ask "
    "only for derived, non-identifying output (aggregates, figures) if anything comes back. "
    "Reuse the paths exactly as written, start from the closest existing script, and follow the "
    "researcher's recorded coding conventions. If an existing pipeline already saves a processed "
    "table that answers the question, read that file instead of rebuilding from raw data. If a "
    "column or value is not below, open the template scripts first; only if it is still unknown, "
    "write the script to report it locally (names(), distinct()) instead of guessing."
)


# A file someone duplicated by hand is not a source to start from.
COPY_NAME = re.compile(r" - copy\b|\(copy\)|_copy\b|_old\b|_to_delete", re.I)


def _recorded_work(conn: sqlite3.Connection, terms: list[str], limit: int = 3) -> list[str]:
    """Pipelines and code patterns recorded with the researcher in earlier sessions.

    Metis kept these before the Data Memory existed (dataset_treatments,
    code_artifacts): the steps that build a derived dataset, in the researcher's
    words, and the reusable code that does it. Data values never enter them —
    only what was done and how. A missing table (a new install) yields nothing.
    """
    if not terms:
        return []
    need = 1 if len(terms) == 1 else 2

    def score(text: str) -> int:
        low = (text or "").lower()
        return sum(1 for t in terms if t in low)

    out: list[str] = []
    try:
        steps: dict[tuple[str, str], list[sqlite3.Row]] = {}
        for r in conn.execute("SELECT * FROM dataset_treatments ORDER BY step_order"):
            steps.setdefault((r["project_id"] or "", r["dataset_name"]), []).append(r)
        ranked = sorted(((score(k[1] + " " + " ".join(s["description"] or "" for s in v)), k, v)
                         for k, v in steps.items()), key=lambda x: -x[0])
        seen_names: set[str] = set()
        pipes = []
        # Only the close matches: a pipeline that shares one word ("village")
        # with the question is not the one it is about.
        floor = max(need, int(ranked[0][0] * 0.7)) if ranked else need
        for sc, (proj, name), rows in ranked:
            if sc < floor or len(pipes) >= limit or name in seen_names:
                continue
            seen_names.add(name)
            pipes.append(f"**{name}**" + (f" (project {proj})" if proj else "") + "\n"
                         + "\n".join(f"  {s['step_order']}. {s['step_type']}: {(s['description'] or '')[:260]}"
                                     for s in rows[:6]))
        if pipes:
            out += ["### How you build these (recorded with you earlier)"] + pipes + [""]
    except sqlite3.Error:
        pass
    try:
        arts = []
        for r in conn.execute("SELECT id, title, kind, purpose, tags FROM code_artifacts ORDER BY updated_at DESC"):
            sc = score(f"{r['title']} {r['purpose']} {r['tags']}")
            if sc >= need:
                arts.append((sc, r))
        arts.sort(key=lambda x: -x[0])   # stable: the newest version first within a score
        arts = [a for a in arts if a[0] >= int(arts[0][0] * 0.7)] if arts else arts
        seen_titles: set[str] = set()
        lines = []
        for _, r in arts:
            base = re.sub(r"\s*\(v\d.*\)$", "", r["title"])
            if base in seen_titles or len(lines) >= limit:
                continue
            seen_titles.add(base)
            lines.append(f"- [{r['kind']}] {r['title']} — {(r['purpose'] or '')[:200]}"
                         f"  → data_memory_script(path=\"artifact:{r['id']}\")")
        if lines:
            out += ["### Code you saved in Metis for this"] + lines + [""]
    except sqlite3.Error:
        pass
    return out


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
        # Sections are assembled in order of use, and a long answer loses its
        # least useful tail: templates and what the researcher recorded come
        # before the file cards, because a cut-off template list is how a
        # request was once answered with guessed column names.
        tpl: list[str] = []
        cards: list[list[str]] = []
        proc: list[str] = []
        made: list[str] = []
        notes: list[str] = []
        recorded = _recorded_work(conn, terms)
        if not cands and not scripts:
            parts.append(f"Nothing in the memory matches: {', '.join(terms) or question!r}. "
                         "Say so plainly; do not guess paths or columns.")
        # One card per file name: scripts in different folders reach the same
        # file by different relative paths. The copy that exists is shown.
        read_n = {r["k"]: r["n"] for r in conn.execute(
            "SELECT dataset_key k, count(*) n FROM dm_links WHERE role IN ('read', 'build') GROUP BY dataset_key")}
        groups: dict[str, list[dict[str, Any]]] = {}
        for d in cands:
            groups.setdefault(d["name"].lower(), []).append(d)
        inputs, outputs = [], []
        for g in groups.values():
            g.sort(key=lambda d: (d["on_disk"] != 1, -read_n.get(d["key"], 0)))
            is_input = any(read_n.get(d["key"]) for d in g) or any(
                d["format"] in PROCESSED_FORMATS and d["on_disk"] == 1 for d in g)
            (inputs if is_input else outputs).append(g)
        seen_story: set[int] = set()
        shown = 0
        for g in inputs:
            if shown >= 5:
                break
            d = g[0]
            if COPY_NAME.search(d["name"]):
                continue
            card = dataset_card(conn, d["key"], max_cols=25)
            # A table in code earns a place only when it says something: named for
            # what it holds, with columns, built from at least one real file.
            if card["format"] == "table in code" and (
                    not card["columns"] or not card["built_from_files"]
                    or d["name"].lower() in GENERIC_OBJECT_NAMES):
                continue
            shown += 1
            cur: list[str] = []
            cards.append(cur)
            disk = {1: "on disk", 0: "NOT FOUND on disk", None: "location unchecked"}[card["on_disk"]]
            cur.append(f"### {card['name']}  ({card['format'] or 'no extension'}, {disk})")
            cur.append(f"path: `{card['path']}`" + (f"  (also referenced by {len(g) - 1} other path(s))" if len(g) > 1 else ""))
            if card["read_by"]:
                rb = "; ".join(f"{Path(s).name}" + (f" as `{o}`" if o else "") + (f" sheet {x}" if x else "")
                               for s, o, x in card["read_by"][:6])
                cur.append(f"read by: {rb}" + (f" (+{len(card['read_by']) - 6})" if len(card["read_by"]) > 6 else ""))
            if card["written_by"]:
                cur.append("written by: " + ", ".join(Path(s).name for s in card["written_by"][:4]))
            if card["saved_from"]:
                cur.append("saved from the in-code table: " + ", ".join(card["saved_from"][:3])
                             + " — reading this file reuses that pipeline's cleaning")
            if card["built_in"]:
                cur.append("built in: " + ", ".join(Path(s).name for s in card["built_in"][:3])
                             + f" · from {len(card['built_from'])} file(s): "
                             + ", ".join(card["built_from"][:8]) + ("…" if len(card["built_from"]) > 8 else ""))
            if card["columns"]:
                cl = []
                for c in card["columns"]:
                    s = f"`{c['name']}`"
                    if c["values"]:
                        s += " ∈ {" + ", ".join(c["values"][:10]) + ("…" if len(c["values"]) > 10 else "") + "}"
                    if c["derived"]:
                        s += f" := {c['derived'][:120]}"
                    cl.append(s)
                cur.append(f"columns seen in code ({card['n_columns']}): " + "; ".join(cl))
            for s in card["stories"][:2]:
                if s["id"] in seen_story:
                    continue
                seen_story.add(s["id"])
                src = "researcher" if s["source"] == "researcher" else Path(s["source_path"]).name + " in " + Path(s["target"]).name
                cur.append(f"story ({src}): {_excerpt(s['text'], terms, 500)}")
            cur.append("")
        # A ready-made table a pipeline saves is the best place to start, so it
        # is named even when the cards above were taken by closer word matches.
        shown_keys = {g[0]["key"] for g in inputs[:shown + 3]}
        processed = [g[0] for g in inputs if g[0]["key"] not in shown_keys
                     and g[0]["format"] in PROCESSED_FORMATS and g[0]["on_disk"] == 1][:5]
        if processed:
            proc.append("### Processed tables your pipelines already save")
            for d in processed:
                w = conn.execute("SELECT script_path FROM dm_links WHERE dataset_key=? AND role='write' LIMIT 1",
                                 (d["key"],)).fetchone()
                proc.append(f"- `{d['path']}`" + (f" ← {Path(w[0]).name}" if w else "")
                             + " — open its writer with data_memory_script to see its columns")
            proc.append("")
        if outputs:
            made.append("### Already produced by existing scripts")
            for g in outputs[:8]:
                d = g[0]
                w = conn.execute("SELECT script_path FROM dm_links WHERE dataset_key=? AND role='write' LIMIT 1",
                                 (d["key"],)).fetchone()
                made.append(f"- {d['name']}" + (f" ← {Path(w[0]).name}" if w else "") + f"  `{d['folder']}`")
            made.append("")
        if scripts:
            tpl.append("### Closest existing scripts (templates)")
            for s in scripts:
                fig = json.loads(s["figures"] or "{}").get("kinds") or []
                st = json.loads(s["style"] or "{}")
                tpl.append(f"- `{to_display(s['path'])}` — {s['purpose'][:160] or 'no header comment'}"
                             + (f" · makes: {', '.join(fig)}" if fig else "")
                             + f" · pipes {'%>%' if st.get('magrittr_pipes', 0) >= st.get('native_pipes', 0) else '|>'}"
                             + (f", own functions {st['own_functions']}" if st.get("own_functions") else "")
                             + (f", loops {st['loops']}" if st.get("loops") else ""))
                reads = conn.execute(
                    "SELECT DISTINCT d.name, l.object FROM dm_links l JOIN dm_datasets d ON d.key = l.dataset_key "
                    "WHERE l.script_path = ? AND l.role = 'read' LIMIT 6", (s["path"],)).fetchall()
                if reads:
                    tpl.append("    reads: " + "; ".join(r["name"] + (f" as `{r['object']}`" if r["object"] else "")
                                                       for r in reads))
            tpl.append("Open a template's code with `data_memory_script(path=...)` before writing, "
                         "and reuse its loading, cleaning and definitions.")
            tpl.append("")
        # notes about the folders the question names, even with no dataset hit
        if terms:
            for r in conn.execute("SELECT * FROM dm_stories ORDER BY scope='folder', updated_at DESC"):
                if r["id"] in seen_story or len(seen_story) >= 4:
                    continue
                hay = (r["target"] + " " + r["text"][:4000]).lower()
                if sum(1 for t in terms if t in hay) >= max(1, min(2, len(terms))):
                    seen_story.add(r["id"])
                    src = "researcher" if r["source"] == "researcher" else Path(r["source_path"]).name + " in " + Path(r["target"]).name
                    notes.append(f"story ({src}): {_excerpt(r['text'], terms, 600)}")
        if notes:
            notes.append("")

        def assemble(n_cards: int, with_made: bool) -> str:
            sec = parts + recorded + tpl + [l for c in cards[:n_cards] for l in c] + proc + notes
            return "\n".join(sec + (made if with_made else []))

        out = assemble(len(cards), True)
        if len(out) > max_chars:
            out = assemble(len(cards), False)
        n = len(cards)
        while len(out) > max_chars and n > 1:
            n -= 1
            out = assemble(n, False)
        if n < len(cards):
            out += f"\n({len(cards) - n} more file card(s) left out for length — data_memory_dataset(name) shows any file in full)"
    return out if len(out) <= max_chars else out[:max_chars] + "\n…(truncated — ask a narrower question)"


SCRIPT_READ_MAX = 120_000


def read_script(path: str, db: Path | None = None) -> tuple[str | None, str]:
    """The code of one analysis script, for writing a new one from it.

    Claude Desktop cannot open files outside its workspace, so without this a
    template the memory names is a title it cannot read — which is how a
    request was once answered with guessed column names while a script that
    already answered it sat in the list. Only R/Python/Quarto/R Markdown
    files inside a registered folder are served: code, never data.
    """
    raw = path.strip().strip('"').strip("'")
    m = re.match(r"^artifact:(\d+)$", raw)
    if m:   # code the researcher saved in Metis (code_artifacts): code, never data
        with open_db(db) as conn:
            try:
                r = conn.execute("SELECT title, code FROM code_artifacts WHERE id = ?", (int(m.group(1)),)).fetchone()
            except sqlite3.Error:
                r = None
        if not r or not r["code"]:
            return None, f"No saved code with id {m.group(1)}."
        return r["code"][:SCRIPT_READ_MAX], f"saved code: {r['title']}"
    lp = local_folder(raw) if re.match(r"^[A-Za-z]:", raw) else raw
    ext = os.path.splitext(lp)[1].lower()
    if ext not in SCRIPT_EXT | {".py"}:
        return None, f"Only analysis scripts can be opened this way (.R, .Rmd, .qmd, .py) — not {ext or 'this file'}."
    real = os.path.realpath(lp)
    with open_db(db) as conn:
        roots = [os.path.realpath(r[0]) for r in conn.execute("SELECT root FROM dm_sources")]
        if not os.path.isfile(real):
            hit = conn.execute("SELECT path FROM dm_scripts WHERE lower(title) = ? ORDER BY scanned_at DESC LIMIT 1",
                               (os.path.basename(raw).lower(),)).fetchone()
            if hit:
                real = os.path.realpath(hit[0])
    if not any(real == r or real.startswith(r.rstrip("/") + "/") for r in roots):
        return None, "That script is not inside a folder Metis learns from. Add its folder on the Data page first."
    if not os.path.isfile(real):
        return None, f"No such script: {path}"
    text = Path(real).read_text(encoding="utf-8", errors="replace")
    if len(text) > SCRIPT_READ_MAX:
        text = text[:SCRIPT_READ_MAX] + f"\n# … truncated at {SCRIPT_READ_MAX:,} characters"
    return text, to_display(real)


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
