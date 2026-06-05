"""Code Repository — a reproducibility + code-reuse layer.

Captures *how you code* so any script can be reproduced or rebuilt from previous
work: scripts/snippets/functions (any language), per-dataset data dictionaries
(variable names, types, labels, unique values/levels, units), and dataset
treatments (the cleaning/lineage steps). From any project you can then scaffold
a new script that reuses prior code, variable names, paths and conventions.

Three tables (self-creating):
  code_artifacts     — scripts, snippets, reusable functions
  data_dictionary    — one row per variable, per dataset
  dataset_treatments — ordered cleaning/transform steps (lineage)
"""

import datetime
import json

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _ensure_tables(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS code_artifacts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  TEXT DEFAULT '',
            title       TEXT NOT NULL,
            language    TEXT DEFAULT '',
            kind        TEXT DEFAULT 'script',   -- script | snippet | function | template
            purpose     TEXT DEFAULT '',
            tags        TEXT DEFAULT '',
            code        TEXT DEFAULT '',
            file_path   TEXT DEFAULT '',
            packages    TEXT DEFAULT '',         -- deps / env (e.g. R pkgs + versions)
            params      TEXT DEFAULT '',         -- seeds, thresholds, hyperparameters
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
            unique_values TEXT DEFAULT '',        -- factor levels / range / example values
            units         TEXT DEFAULT '',
            notes         TEXT DEFAULT '',
            created_at    TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS dataset_treatments (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id     TEXT DEFAULT '',
            dataset_name   TEXT NOT NULL,
            step_order     INTEGER DEFAULT 0,
            step_type      TEXT DEFAULT '',        -- recode | filter | join | derive | clean | other
            description    TEXT DEFAULT '',
            code           TEXT DEFAULT '',
            input_dataset  TEXT DEFAULT '',
            output_dataset TEXT DEFAULT '',
            created_at     TEXT NOT NULL
        )"""
    )


@app.tool()
async def register_code_artifact(
    title: str,
    code: str,
    language: str = "",
    project_id: str = "",
    kind: str = "script",
    purpose: str = "",
    tags: str = "",
    file_path: str = "",
    packages: str = "",
    params: str = "",
) -> list[TextContent]:
    """Save a script, snippet, reusable function or template to the Code Repository.

    Use this whenever the user writes or shares code worth reusing, so it can be
    found and rebuilt later. Capture as much reproducibility context as you can.

    Args:
        title: Short descriptive name (e.g. "INLA BYM2 spatial model setup").
        code: The actual code.
        language: r | python | sql | stata | shell | … (lowercase).
        project_id: The project this belongs to (links it for reuse). Optional.
        kind: script | snippet | function | template.
        purpose: One line on what it does / when to use it.
        tags: Comma-separated tags (e.g. "spatial,INLA,mapping").
        file_path: Where the script lives on disk, if any.
        packages: Dependencies / environment (e.g. "INLA 24.9, sf, dplyr").
        params: Seeds, thresholds, hyperparameters used (for exact reproduction).
    """
    if not paths.db.exists():
        return [TextContent(type="text", text="No database found.")]
    try:
        with connect(paths.db) as conn:
            _ensure_tables(conn)
            cur = conn.execute(
                """INSERT INTO code_artifacts
                   (project_id, title, language, kind, purpose, tags, code,
                    file_path, packages, params, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (project_id, title, language.lower(), kind, purpose, tags, code,
                 file_path, packages, params, _now(), _now()),
            )
            new_id = cur.lastrowid
        return [TextContent(type="text", text=(
            f"✓ Saved code artifact #{new_id}: **{title}** "
            f"({language or 'unknown'}{', ' + project_id if project_id else ''}). "
            "Reuse it later with search_code_repository or scaffold_script."
        ))]
    except Exception as e:
        return [TextContent(type="text", text=f"Could not save code artifact: {e}")]


@app.tool()
async def register_data_dictionary(
    dataset_name: str,
    variables: list,
    project_id: str = "",
    dataset_path: str = "",
) -> list[TextContent]:
    """Record a dataset's data dictionary — one entry per variable.

    Captures the variable names, types, labels, **unique values / factor levels**
    and units, so future scripts use the exact same names and treatments.

    Args:
        dataset_name: Name of the dataset (e.g. "hat_cases_2015_2023").
        variables: List of variable entries. Each is an object with any of:
            name (required), type, label, unique_values, units, notes.
        project_id: Project this dataset belongs to. Optional.
        dataset_path: Where the dataset lives on disk. Optional.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text="No database found.")]
    if not variables:
        return [TextContent(type="text", text="No variables provided.")]
    stored = 0
    try:
        with connect(paths.db) as conn:
            _ensure_tables(conn)
            # replace any existing dictionary for this dataset (idempotent re-register)
            conn.execute(
                "DELETE FROM data_dictionary WHERE dataset_name = ? AND COALESCE(project_id,'') = ?",
                (dataset_name, project_id),
            )
            for v in variables:
                if isinstance(v, str):
                    v = {"name": v}
                if not isinstance(v, dict) or not v.get("name"):
                    continue
                conn.execute(
                    """INSERT INTO data_dictionary
                       (project_id, dataset_name, dataset_path, variable_name,
                        var_type, label, unique_values, units, notes, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (project_id, dataset_name, dataset_path, str(v.get("name")),
                     str(v.get("type", "")), str(v.get("label", "")),
                     str(v.get("unique_values", "")), str(v.get("units", "")),
                     str(v.get("notes", "")), _now()),
                )
                stored += 1
        return [TextContent(type="text", text=(
            f"✓ Recorded {stored} variable(s) for dataset **{dataset_name}**"
            f"{' (' + project_id + ')' if project_id else ''}."
        ))]
    except Exception as e:
        return [TextContent(type="text", text=f"Could not save data dictionary: {e}")]


@app.tool()
async def record_dataset_treatment(
    dataset_name: str,
    description: str,
    project_id: str = "",
    step_type: str = "",
    code: str = "",
    input_dataset: str = "",
    output_dataset: str = "",
) -> list[TextContent]:
    """Record one cleaning/transformation step for a dataset (its lineage).

    Build a traceable chain raw → cleaned → analysis dataset, so any result can
    be reproduced. Call once per step (recode, filter, join, derive, …).

    Args:
        dataset_name: The dataset being transformed.
        description: What this step does (e.g. "drop records with missing age").
        project_id: Project this belongs to. Optional.
        step_type: recode | filter | join | derive | clean | other.
        code: The code for this step, if any.
        input_dataset: Dataset(s) this step consumes.
        output_dataset: Dataset this step produces.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text="No database found.")]
    try:
        with connect(paths.db) as conn:
            _ensure_tables(conn)
            nxt = conn.execute(
                "SELECT COALESCE(MAX(step_order),0)+1 FROM dataset_treatments "
                "WHERE dataset_name = ? AND COALESCE(project_id,'') = ?",
                (dataset_name, project_id),
            ).fetchone()[0]
            conn.execute(
                """INSERT INTO dataset_treatments
                   (project_id, dataset_name, step_order, step_type, description,
                    code, input_dataset, output_dataset, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (project_id, dataset_name, nxt, step_type, description, code,
                 input_dataset, output_dataset, _now()),
            )
        return [TextContent(type="text", text=(
            f"✓ Recorded treatment step {nxt} for **{dataset_name}**: {description[:80]}"
        ))]
    except Exception as e:
        return [TextContent(type="text", text=f"Could not record treatment: {e}")]


def _kw(query: str) -> list[str]:
    import re
    words = re.findall(r"[a-zA-Z0-9_]{3,}", (query or "").lower())
    stop = {"the", "and", "for", "with", "from", "make", "script", "code", "use"}
    return [w for w in words if w not in stop][:8]


@app.tool()
async def search_code_repository(
    query: str,
    project_id: str = "",
    language: str = "",
) -> list[TextContent]:
    """Search the Code Repository for prior code, variables and treatments.

    Finds reusable scripts/functions, dataset variables and cleaning steps that
    match a query — e.g. "Poisson model offset" or "catastrophic expenditure".

    Args:
        query: What you're looking for.
        project_id: Restrict to one project. Optional.
        language: Restrict to a language (r, python, …). Optional.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text="No database found.")]
    kws = _kw(query)
    if not kws:
        return [TextContent(type="text", text="Please give a more specific query.")]
    try:
        with connect(paths.db) as conn:
            _ensure_tables(conn)

            def like(cols):
                return " OR ".join(f"{c} LIKE ?" for c in cols for _ in kws)

            def params(cols):
                return [f"%{k}%" for _ in cols for k in kws]

            out = []
            # code artifacts
            cols = ["title", "purpose", "tags", "code"]
            sql = f"SELECT id, title, language, project_id, purpose FROM code_artifacts WHERE ({like(cols)})"
            p = params(cols)
            if project_id:
                sql += " AND project_id = ?"; p.append(project_id)
            if language:
                sql += " AND language = ?"; p.append(language.lower())
            sql += " ORDER BY updated_at DESC LIMIT 12"
            rows = conn.execute(sql, p).fetchall()
            if rows:
                out.append("## Code artifacts")
                for r in rows:
                    out.append(f"- **#{r[0]} {r[1]}** ({r[2] or '?'}{', ' + r[3] if r[3] else ''}) — {r[4] or ''}")

            # data dictionary variables
            cols = ["variable_name", "label", "unique_values", "dataset_name"]
            sql = f"SELECT dataset_name, variable_name, var_type, label FROM data_dictionary WHERE ({like(cols)})"
            p = params(cols)
            if project_id:
                sql += " AND project_id = ?"; p.append(project_id)
            sql += " LIMIT 15"
            rows = conn.execute(sql, p).fetchall()
            if rows:
                out.append("\n## Variables")
                for r in rows:
                    out.append(f"- `{r[1]}` ({r[2] or '?'}) in **{r[0]}** — {r[3] or ''}")

            # treatments
            cols = ["description", "dataset_name", "code"]
            sql = f"SELECT dataset_name, step_type, description FROM dataset_treatments WHERE ({like(cols)})"
            p = params(cols)
            if project_id:
                sql += " AND project_id = ?"; p.append(project_id)
            sql += " ORDER BY step_order LIMIT 12"
            rows = conn.execute(sql, p).fetchall()
            if rows:
                out.append("\n## Dataset treatments")
                for r in rows:
                    out.append(f"- **{r[0]}** [{r[1] or 'step'}] — {r[2] or ''}")

        if not out:
            return [TextContent(type="text", text=f"No matches for '{query}' in the Code Repository yet.")]
        return [TextContent(type="text", text="\n".join(out))]
    except Exception as e:
        return [TextContent(type="text", text=f"Search failed: {e}")]


@app.tool()
async def scaffold_script(
    goal: str,
    project_id: str = "",
    language: str = "r",
) -> list[TextContent]:
    """Assemble the raw material to write a NEW script from previous work.

    Pulls the most relevant prior code, the project's dataset variables/paths,
    and the cleaning steps — so you can write a new script in the user's own
    conventions (same names, paths, packages). Call this, then write the script.

    Args:
        goal: What the new script should do.
        project_id: The project to scaffold for (prioritised, then cross-project).
        language: Target language (r, python, …).
    """
    if not paths.db.exists():
        return [TextContent(type="text", text="No database found.")]
    kws = _kw(goal)
    try:
        with connect(paths.db) as conn:
            _ensure_tables(conn)
            parts = [f"# Scaffold material for: {goal}",
                     f"_Target language: {language}{' · project: ' + project_id if project_id else ''}_\n"]

            # 1) Relevant prior code — project first, then anywhere
            like = " OR ".join("title LIKE ? OR purpose LIKE ? OR tags LIKE ? OR code LIKE ?" for _ in kws) or "1=1"
            p = [f"%{k}%" for k in kws for _ in range(4)]
            order = "ORDER BY (project_id = ?) DESC, updated_at DESC" if project_id else "ORDER BY updated_at DESC"
            if project_id:
                p.append(project_id)
            rows = conn.execute(
                f"SELECT title, language, code, packages, params, file_path, project_id "
                f"FROM code_artifacts WHERE ({like}) {order} LIMIT 4", p
            ).fetchall()
            if rows:
                parts.append("## Reuse this prior code")
                for r in rows:
                    parts.append(f"### {r[0]}  ({r[1] or '?'}{', ' + r[6] if r[6] else ''})")
                    if r[3]:
                        parts.append(f"_packages:_ {r[3]}")
                    if r[4]:
                        parts.append(f"_params/seeds:_ {r[4]}")
                    if r[5]:
                        parts.append(f"_path:_ `{r[5]}`")
                    parts.append("```\n" + (r[2] or "")[:1500] + "\n```")
            else:
                parts.append("_No closely matching prior code — write fresh, then register it._")

            # 2) Project datasets + variable names/paths
            if project_id:
                drows = conn.execute(
                    "SELECT DISTINCT dataset_name, dataset_path FROM data_dictionary WHERE project_id = ? LIMIT 6",
                    (project_id,)).fetchall()
                for ds, dpath in drows:
                    vrows = conn.execute(
                        "SELECT variable_name, var_type, label FROM data_dictionary "
                        "WHERE project_id = ? AND dataset_name = ? LIMIT 40",
                        (project_id, ds)).fetchall()
                    parts.append(f"\n## Dataset `{ds}`" + (f"  ·  `{dpath}`" if dpath else ""))
                    parts.append("Use these exact variable names:")
                    parts.append(", ".join(f"`{v[0]}`" + (f" ({v[1]})" if v[1] else "") for v in vrows) or "_(no variables recorded)_")

                # 3) Treatments for those datasets
                trows = conn.execute(
                    "SELECT dataset_name, step_order, step_type, description FROM dataset_treatments "
                    "WHERE project_id = ? ORDER BY dataset_name, step_order LIMIT 20",
                    (project_id,)).fetchall()
                if trows:
                    parts.append("\n## Apply the same dataset treatments")
                    for t in trows:
                        parts.append(f"- {t[0]} · step {t[1]} [{t[2] or 'step'}]: {t[3]}")

            parts.append("\n---\nNow write the new script in the user's conventions, reusing the names, "
                         "paths, packages and treatments above. When done, save it with register_code_artifact.")
        return [TextContent(type="text", text="\n".join(parts))]
    except Exception as e:
        return [TextContent(type="text", text=f"Could not scaffold: {e}")]
