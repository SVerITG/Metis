"""Data Memory tools — the data-protected analysis mode.

Thin MCP wrappers over metis_mcp.data_memory, which learns the researcher's
datasets from their analysis code and notes and never opens a data file.

  data_memory(question)            — what is known that bears on a data question; call FIRST
  data_memory_dataset(name)        — the full card for one file
  data_memory_scan(folder)         — learn (or re-learn) a folder of scripts
  data_memory_status()             — what is known, from which folders, what is unresolved
  record_data_story(target, story) — keep what the researcher says about a dataset
"""

import datetime

from mcp.types import TextContent

from metis_mcp import data_memory as dm
from metis_mcp.app_instance import app

# A question refreshes folders whose last scan is older than this, so edited
# scripts are learnt without anyone asking. Unchanged scripts cost one stat().
_REFRESH_HOURS = 6


def _t(s: str) -> list[TextContent]:
    return [TextContent(type="text", text=s)]


@app.tool()
async def data_memory(question: str, project_id: str = "") -> list[TextContent]:
    """Data-protected mode: what Metis knows about the researcher's data for this request.

    Call this FIRST whenever a request involves data — a new analysis, an R
    script, a figure, a map, a dashboard panel, cleaning, merging, a variable,
    "what do I have on X". It returns, from the researcher's own code and notes
    only: the files involved (exact paths, format, whether they exist), the
    columns the code uses with the values it tests for and how derived
    variables are built, which scripts read and write each file, outputs
    already produced, the closest existing scripts to start from, and the
    stories recorded about the data.

    Then write an R script the researcher runs locally. Never open, preview or
    summarise a data file and never ask for rows: that is the contract of this
    mode, and it also holds for files the researcher names directly.

    Args:
        question: the request in the researcher's words.
        project_id: optional Metis project to favour.
    """
    try:
        dm.refresh(max_age_hours=_REFRESH_HOURS)
    except Exception:
        pass   # a stale memory still answers; a failed refresh must not block
    return _t(dm.context(question, project_id=project_id))


@app.tool()
async def data_memory_dataset(name_or_path: str) -> list[TextContent]:
    """Everything known about one data file: paths, readers, writers, columns, values, stories.

    Args:
        name_or_path: a file name (survey_results.xlsx) or a full path.
    """
    with dm.open_db() as conn:
        hits = dm.find_datasets(conn, name_or_path, limit=3)
        if not hits:
            return _t(f"No file matching {name_or_path!r} is known from the scanned scripts.")
        card = dm.dataset_card(conn, hits[0]["key"], max_cols=200)
    lines = [f"## {card['name']}", f"path: `{card['path']}`",
             f"format: {card['format']} · on disk: {card['on_disk']}", ""]
    if card["read_by"]:
        lines.append("**Read by**")
        lines += [f"- {s}" + (f" as `{o}`" if o else "") + (f" (sheet {x})" if x else "")
                  for s, o, x in card["read_by"]]
    if card["written_by"]:
        lines.append("**Written by**")
        lines += [f"- {s}" for s in card["written_by"]]
    if card["columns"]:
        lines.append(f"\n**Columns seen in code ({card['n_columns']})**")
        for c in card["columns"]:
            s = f"- `{c['name']}` (used in {c['used_in']} script(s))"
            if c["values"]:
                s += " values: " + ", ".join(c["values"])
            if c["derived"]:
                s += f"\n  built as: `{c['derived']}`"
            lines.append(s)
    for s in card["stories"][:4]:
        src = "told by the researcher" if s["source"] == "researcher" else s["source_path"]
        lines.append(f"\n**Story** ({src}, {s['updated_at'][:10]})\n{s['text'][:2500]}")
    if len(hits) > 1:
        lines.append("\nOther matches: " + ", ".join(h["path"] for h in hits[1:]))
    return _t("\n".join(lines))


@app.tool()
async def data_memory_scan(folder: str = "", project_id: str = "", label: str = "",
                           force: bool = False) -> list[TextContent]:
    """Learn a folder of analysis scripts, or refresh every folder already known.

    Reads .R/.Rmd/.qmd code and CLAUDE.md/README notes only. Copies are skipped
    (History/, r_libs/, renv/, '- Copy', _to_delete). Unchanged scripts are not
    re-read. With no folder, every registered folder is refreshed.

    Args:
        folder: absolute path (C:/… or /mnt/c/…). Empty = refresh all.
        project_id: Metis project these scripts belong to (optional).
        label: a short name for the folder (optional).
        force: re-read every script even if unchanged.
    """
    try:
        runs = [dm.scan(folder, project_id, label, force=force)] if folder else dm.refresh()
    except FileNotFoundError as e:
        return _t(str(e))
    if not runs:
        return _t("No script folders are registered yet. Give me a folder that holds analysis scripts.")
    st = dm.status()
    lines = ["| Folder | Scripts | Re-read | Reads | Outputs | Unresolved |", "|---|---|---|---|---|---|"]
    for r in runs:
        if "error" in r:
            lines.append(f"| {r['root']} | — | — | — | — | {r['error']} |")
            continue
        lines.append(f"| {r['root']} | {r['scripts']} | {r['rescanned']} | {r['reads']} | "
                     f"{r['writes']} | {r['unresolved']} |")
    lines.append(f"\nMemory now: {st['datasets_read']} input files, {st['columns']} columns "
                 f"({st['columns_with_values']} with values from code, {st['derived']} derived), "
                 f"{st['stories']} notes, from {st['scripts']} scripts.")
    return _t("\n".join(lines))


@app.tool()
async def data_memory_status() -> list[TextContent]:
    """What the Data Memory holds, which folders feed it, and when they were last read."""
    st = dm.status()
    lines = ["## Data Memory", ""]
    for s in st["sources"]:
        lines.append(f"- `{dm.to_display(s['root'])}` — {s['n_scripts']} scripts, last read {s['last_scan']}"
                     + (f" · project {s['project_id']}" if s["project_id"] else ""))
    lines.append("")
    lines.append(f"{st['scripts']} scripts · {st['datasets_read']} input files ({st['inputs_missing']} referenced "
                 f"but not on disk) · {st['reads']} reads · {st['writes']} outputs · {st['columns']} columns "
                 f"({st['columns_with_values']} with values, {st['derived']} derived) · {st['stories']} notes · "
                 f"{st['unresolved_reads']} file references that could not be resolved from code alone.")
    return _t("\n".join(lines))


@app.tool()
async def record_data_story(target: str, story: str, project_id: str = "") -> list[TextContent]:
    """Keep what the researcher says about a dataset: its origin, quirks, caveats, history.

    Use whenever they explain a dataset ("the 2019 extract double-counts one
    district", "lab results are joined on the sample barcode", "this list is
    fixed and correct"). It is attached to the file and returned with it from then on.
    Never put data values from rows in a story — only what the researcher
    says about the data.

    Args:
        target: the file name or path, or a folder, or a topic word.
        story: the researcher's account, in their words where possible.
        project_id: optional Metis project.
    """
    where = dm.add_story(target, story, project_id)
    return _t(f"Kept with {where} ({datetime.date.today().isoformat()}).")
