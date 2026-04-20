"""File tracking tools for monitoring changes in key PKM files."""

import datetime
import os
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app

# Extensions considered "project files" for connect_project_folder
_PROJECT_EXTENSIONS = {
    ".R", ".r", ".Rmd", ".rmd", ".md", ".py", ".js", ".ts",
    ".sql", ".json", ".yaml", ".yml", ".qmd", ".tex", ".csv",
}

_TRACKED_FILES_DDL = """
CREATE TABLE IF NOT EXISTS tracked_files (
    path TEXT PRIMARY KEY,
    last_modified TEXT NOT NULL,
    last_scanned TEXT NOT NULL,
    label TEXT DEFAULT '',
    watch INTEGER DEFAULT 0
)
"""


def _ensure_tracked_files(conn) -> None:
    """Create tracked_files table and apply any pending column migrations."""
    _ensure_tracked_files(conn)
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(tracked_files)").fetchall()}
    if "label" not in cols:
        conn.execute("ALTER TABLE tracked_files ADD COLUMN label TEXT DEFAULT ''")
    if "watch" not in cols:
        conn.execute("ALTER TABLE tracked_files ADD COLUMN watch INTEGER DEFAULT 0")


@app.tool()
async def scan_tracked_files() -> list[TextContent]:
    """Scan all tracked files and report which have changed since last scan.

    Reads tracked_files table, checks actual file modification times,
    and updates last_scanned timestamps.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        with connect(paths.db) as conn:
            _ensure_tracked_files(conn)
            cur = conn.execute("SELECT * FROM tracked_files WHERE watch = 1 ORDER BY path")
            rows = cur.fetchall()

            if not rows:
                return [TextContent(type="text", text="No tracked files. Use add_tracked_file to start tracking.")]

            results = []
            for row in rows:
                file_path = row["path"]
                last_modified_db = row["last_modified"]
                label = row["label"] or ""

                try:
                    stat = os.stat(file_path)
                    actual_mtime = datetime.datetime.fromtimestamp(
                        stat.st_mtime, tz=datetime.timezone.utc
                    ).isoformat()
                    changed = actual_mtime > last_modified_db
                    exists = True
                except OSError:
                    actual_mtime = ""
                    changed = False
                    exists = False

                results.append({
                    "path": file_path,
                    "label": label,
                    "exists": exists,
                    "last_modified": actual_mtime if exists else "FILE NOT FOUND",
                    "changed": changed,
                })

                # Update last_scanned and last_modified if changed
                if exists and changed:
                    conn.execute(
                        "UPDATE tracked_files SET last_scanned = ?, last_modified = ? WHERE path = ?",
                        (now, actual_mtime, file_path),
                    )
                elif exists:
                    conn.execute(
                        "UPDATE tracked_files SET last_scanned = ? WHERE path = ?",
                        (now, file_path),
                    )

            conn.commit()

            # Format output
            changed_files = [r for r in results if r["changed"]]
            missing_files = [r for r in results if not r["exists"]]

            lines = [f"**Tracked files: {len(results)} total**\n"]

            if changed_files:
                lines.append(f"**Changed ({len(changed_files)}):**")
                for r in changed_files:
                    lbl = f" [{r['label']}]" if r["label"] else ""
                    lines.append(f"- {r['path']}{lbl}")

            if missing_files:
                lines.append(f"\n**Missing ({len(missing_files)}):**")
                for r in missing_files:
                    lbl = f" [{r['label']}]" if r["label"] else ""
                    lines.append(f"- {r['path']}{lbl}")

            unchanged = len(results) - len(changed_files) - len(missing_files)
            if unchanged > 0:
                lines.append(f"\n**Unchanged:** {unchanged} files")

            return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error scanning tracked files: {e}")]


@app.tool()
async def add_tracked_file(
    path: str,
    label: str = "",
) -> list[TextContent]:
    """Add a file to the tracking list.

    Args:
        path: Absolute path to the file to track.
        label: Optional label for categorization.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        stat = os.stat(path)
        mtime = datetime.datetime.fromtimestamp(
            stat.st_mtime, tz=datetime.timezone.utc
        ).isoformat()
    except OSError:
        return [TextContent(type="text", text=f"File not found: {path}")]

    try:
        with connect(paths.db) as conn:
            _ensure_tracked_files(conn)
            conn.execute(
                """INSERT INTO tracked_files (path, last_modified, last_scanned, label, watch)
                   VALUES (?, ?, ?, ?, 1)
                   ON CONFLICT(path) DO UPDATE SET
                       last_modified = excluded.last_modified,
                       last_scanned = excluded.last_scanned,
                       label = CASE WHEN excluded.label != '' THEN excluded.label ELSE tracked_files.label END,
                       watch = 1""",
                (path, mtime, now, label),
            )
            conn.commit()

        return [TextContent(type="text", text=f"Now tracking: {path}" + (f" [{label}]" if label else ""))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error adding tracked file: {e}")]


@app.tool()
async def connect_project_folder(
    folder_path: str,
    label: str = "",
    max_files: int = 200,
) -> list[TextContent]:
    """Register all relevant files in a project folder so Metis can read them.

    Walks the folder recursively and adds every file with a recognised extension
    (.R, .Rmd, .md, .py, .js, .ts, .sql, .json, .yaml, .qmd, .tex, .csv) to
    the tracked_files table. Call this once per project; after that, use
    read_file() to read any individual file.

    Args:
        folder_path: Absolute path to the project root folder.
        label: Short label for all files from this project (e.g. "MLM Course").
        max_files: Safety limit — stop after registering this many files (default 200).
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    root = Path(folder_path)
    if not root.is_dir():
        return [TextContent(type="text", text=f"Folder not found: {folder_path}")]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    registered = []
    skipped = []

    try:
        with connect(paths.db) as conn:
            _ensure_tracked_files(conn)
            _skip_dirs = {"__pycache__", "node_modules", ".venv", "venv", ".git"}
            for dirpath, dirnames, filenames in os.walk(str(root)):
                # Prune unwanted directories in-place (faster than filtering after)
                dirnames[:] = [
                    d for d in dirnames
                    if not d.startswith(".") and d not in _skip_dirs
                ]
                for fname in filenames:
                    fp = Path(dirpath) / fname
                    if fp.suffix not in _PROJECT_EXTENSIONS:
                        continue
                    if len(registered) >= max_files:
                        skipped.append(str(fp))
                        continue

                try:
                    conn.execute(
                        """INSERT INTO tracked_files (path, last_modified, last_scanned, label, watch)
                           VALUES (?, ?, ?, ?, 0)
                           ON CONFLICT(path) DO UPDATE SET
                               last_scanned = excluded.last_scanned,
                               label = CASE WHEN excluded.label != '' THEN excluded.label ELSE tracked_files.label END""",
                        (str(fp), now, now, label),
                    )
                    registered.append(str(fp))
                except Exception:
                    pass

            conn.commit()

        lines = [
            f"**Connected project folder:** `{folder_path}`",
            f"**Label:** {label or '(none)'}",
            f"**Files registered:** {len(registered)}",
        ]
        if skipped:
            lines.append(f"**Skipped (limit {max_files} reached):** {len(skipped)} files — increase max_files if needed")
        lines.append("\nYou can now ask Metis to read any of these files using `read_file(path)`.")
        lines.append("\n**Sample files registered:**")
        for f in registered[:10]:
            lines.append(f"- `{f}`")
        if len(registered) > 10:
            lines.append(f"- … and {len(registered) - 10} more")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error connecting folder: {e}")]


@app.tool()
async def read_file(path: str, max_chars: int = 8000) -> list[TextContent]:
    """Read the content of a file and return it as text.

    Works for any text file: R scripts, markdown, Python, JSON, CSV, etc.
    The file does not need to be pre-registered in tracked_files.

    Args:
        path: Absolute path to the file to read.
        max_chars: Maximum characters to return (default 8000). For large files,
                   increase this or ask for a specific section.
    """
    fp = Path(path)
    if not fp.exists():
        return [TextContent(type="text", text=f"File not found: {path}")]
    if not fp.is_file():
        return [TextContent(type="text", text=f"Not a file: {path}")]

    # Basic safety: refuse to read binary / very large files
    try:
        size = fp.stat().st_size
    except OSError as e:
        return [TextContent(type="text", text=f"Cannot stat file: {e}")]

    if size > 5_000_000:  # 5 MB
        return [TextContent(type="text", text=f"File too large ({size:,} bytes). Please use a specific section or split the file.")]

    try:
        content = fp.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [TextContent(type="text", text=f"Error reading file: {e}")]

    truncated = len(content) > max_chars
    if truncated:
        content = content[:max_chars]

    header = f"**File:** `{path}`\n**Size:** {size:,} bytes\n\n"
    if truncated:
        header += f"*(truncated to {max_chars:,} chars — use max_chars to read more)*\n\n"

    return [TextContent(type="text", text=header + content)]


@app.tool()
async def list_folder(folder_path: str, pattern: str = "*") -> list[TextContent]:
    """List files in a folder.

    Args:
        folder_path: Absolute path to the folder.
        pattern: Glob pattern to filter files (e.g. "*.R", "*.md"). Default: all files.
    """
    root = Path(folder_path)
    if not root.exists():
        return [TextContent(type="text", text=f"Folder not found: {folder_path}")]
    if not root.is_dir():
        return [TextContent(type="text", text=f"Not a folder: {folder_path}")]

    try:
        files = sorted(root.glob(pattern))
        dirs  = [f for f in files if f.is_dir()]
        fls   = [f for f in files if f.is_file()]

        lines = [f"**Folder:** `{folder_path}`", f"**Pattern:** `{pattern}`", ""]
        if dirs:
            lines.append(f"**Subdirectories ({len(dirs)}):**")
            for d in dirs[:20]:
                lines.append(f"  📁 {d.name}/")
            if len(dirs) > 20:
                lines.append(f"  … and {len(dirs) - 20} more")

        if fls:
            lines.append(f"\n**Files ({len(fls)}):**")
            for f in fls[:50]:
                lines.append(f"  📄 {f.name}")
            if len(fls) > 50:
                lines.append(f"  … and {len(fls) - 50} more")

        if not dirs and not fls:
            lines.append("*(empty — no matches)*")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error listing folder: {e}")]


@app.tool()
async def remove_tracked_file(path: str) -> list[TextContent]:
    """Remove a file from the tracking list.

    Args:
        path: Path of the file to stop tracking.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            _ensure_tracked_files(conn)
            cur = conn.execute("DELETE FROM tracked_files WHERE path = ?", (path,))
            conn.commit()

            if cur.rowcount == 0:
                return [TextContent(type="text", text=f"File not found in tracking list: {path}")]

        return [TextContent(type="text", text=f"Stopped tracking: {path}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error removing tracked file: {e}")]
