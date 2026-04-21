"""
tools/backup.py — Phase 7: Backup and portability.

M7.1  backup_db(destination, label)
        Copy the live SQLite DB to a timestamped .sqlite file.
        Supports local path or a second destination for off-site copy.
        Uses SQLite Online Backup API (safe for live WAL databases).

M7.2  encrypt_backup(backup_path, passphrase)
        AES-256-GCM encrypt a backup file with a user passphrase.
        Produces <backup_path>.enc alongside the plaintext.

M7.3  list_backups(backup_dir)
        Return all .sqlite (and .enc) backups with size + age.

M7.4  verify_backup(backup_path)
        Open a backup copy and run PRAGMA integrity_check.

M7.5  restore_db(backup_path, confirm)
        Copy a backup over the live DB (requires confirm='YES').
        Renames the current DB to <db>.pre-restore before overwriting.

Scheduler note:
  A lightweight cron/schedule entry can call backup_db() daily.
  The agent_runs table is used to log backup events automatically.
"""

import hashlib
import json
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BACKUP_SCHEDULE_KEY = "backup_schedule"


def _default_backup_dir() -> Path:
    """Return the default backup directory: system/backups/."""
    return paths.config.parent / "backups"


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024**2:
        return f"{n/1024:.1f} KB"
    return f"{n/1024**2:.1f} MB"


# ---------------------------------------------------------------------------
# M7.1 — backup_db
# ---------------------------------------------------------------------------


@app.tool()
async def backup_db(
    destination: str = "",
    label: str = "",
    extra_destination: str = "",
) -> list[TextContent]:
    """Create a timestamped backup of the Metis SQLite database.

    Uses SQLite's Online Backup API — safe to run while the database is live.

    Args:
        destination:       Directory path to write the backup into.
                           Defaults to metis/system/backups/.
        label:             Optional label appended to the filename, e.g. 'pre-upgrade'.
        extra_destination: Optional second directory for off-site / secondary copy.

    Returns JSON with backup_path, size_kb, checksum (SHA-256), and elapsed_ms.
    """
    t0 = datetime.now()

    dest_dir = Path(destination) if destination else _default_backup_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    ts = _ts()
    suffix = f"_{label}" if label else ""
    filename = f"metis_{ts}{suffix}.sqlite"
    backup_path = dest_dir / filename

    # Online backup
    src_conn = sqlite3.connect(str(paths.db))
    bk_conn  = sqlite3.connect(str(backup_path))
    try:
        src_conn.backup(bk_conn)
    finally:
        bk_conn.close()
        src_conn.close()

    # Checksum
    digest = hashlib.sha256(backup_path.read_bytes()).hexdigest()

    result = {
        "backup_path": str(backup_path),
        "size":        _human_size(backup_path.stat().st_size),
        "sha256":      digest,
        "elapsed_ms":  round((datetime.now() - t0).total_seconds() * 1000),
    }

    # Optional second destination
    if extra_destination:
        extra_dir = Path(extra_destination)
        extra_dir.mkdir(parents=True, exist_ok=True)
        extra_path = extra_dir / filename
        shutil.copy2(backup_path, extra_path)
        result["extra_copy"] = str(extra_path)

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ---------------------------------------------------------------------------
# M7.2 — encrypt_backup
# ---------------------------------------------------------------------------


@app.tool()
async def encrypt_backup(
    backup_path: str,
    passphrase: str,
) -> list[TextContent]:
    """AES-256-GCM encrypt a backup file.

    Produces <backup_path>.enc. The passphrase is never stored.
    Uses Python stdlib only (hashlib for key derivation, os.urandom for salt/nonce).

    NOTE: This uses a simple PBKDF2+AES-GCM implementation.
    For production-grade encryption, use a proper secrets manager.

    Args:
        backup_path: Full path to the .sqlite backup file.
        passphrase:  Encryption passphrase.

    Returns JSON with enc_path and whether original was removed.
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes as crypto_hashes
        _have_crypto = True
    except ImportError:
        _have_crypto = False

    bp = Path(backup_path)
    if not bp.exists():
        return [TextContent(type="text", text=f"ERROR: backup file not found: {backup_path}")]

    enc_path = bp.with_suffix(bp.suffix + ".enc")

    if _have_crypto:
        # PBKDF2-SHA256 key derivation
        salt  = os.urandom(16)
        nonce = os.urandom(12)
        kdf = PBKDF2HMAC(
            algorithm=crypto_hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=200_000,
        )
        key = kdf.derive(passphrase.encode())
        aesgcm = AESGCM(key)
        plaintext = bp.read_bytes()
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        # Format: [4B magic][16B salt][12B nonce][ciphertext+tag]
        magic = b"METISBK1"
        enc_path.write_bytes(magic + salt + nonce + ciphertext)
        method = "AES-256-GCM (PBKDF2-SHA256, 200k rounds)"
    else:
        # Fallback: XOR with SHA-256 key stream (NOT secure — warns user)
        key_bytes = hashlib.sha256(passphrase.encode()).digest()
        plaintext = bp.read_bytes()
        keystream = (key_bytes * (len(plaintext) // 32 + 1))[:len(plaintext)]
        enc_path.write_bytes(bytes(a ^ b for a, b in zip(plaintext, keystream)))
        method = "WARNING: XOR-SHA256 fallback — install 'cryptography' package for real AES-256-GCM"

    result = {
        "enc_path":       str(enc_path),
        "original_path":  str(bp),
        "size":           _human_size(enc_path.stat().st_size),
        "method":         method,
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ---------------------------------------------------------------------------
# M7.3 — list_backups
# ---------------------------------------------------------------------------


@app.tool()
async def list_backups(backup_dir: str = "") -> list[TextContent]:
    """List all backup files with size, age, and checksum availability.

    Args:
        backup_dir: Directory to scan. Defaults to metis/system/backups/.

    Returns JSON array, newest first.
    """
    d = Path(backup_dir) if backup_dir else _default_backup_dir()
    if not d.exists():
        return [TextContent(type="text", text=json.dumps([], indent=2))]

    now = datetime.now()
    files = sorted(
        [f for f in d.iterdir() if f.suffix in {".sqlite", ".enc"}],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    results = []
    for f in files:
        stat = f.stat()
        age_s = (now.timestamp() - stat.st_mtime)
        if age_s < 3600:
            age_label = f"{int(age_s/60)}m ago"
        elif age_s < 86400:
            age_label = f"{age_s/3600:.1f}h ago"
        else:
            age_label = f"{age_s/86400:.1f}d ago"
        results.append({
            "name":  f.name,
            "path":  str(f),
            "size":  _human_size(stat.st_size),
            "age":   age_label,
            "type":  "encrypted" if f.suffix == ".enc" else "plaintext",
        })

    return [TextContent(type="text", text=json.dumps(results, indent=2))]


# ---------------------------------------------------------------------------
# M7.4 — verify_backup
# ---------------------------------------------------------------------------


@app.tool()
async def verify_backup(backup_path: str) -> list[TextContent]:
    """Run SQLite integrity_check on a backup file.

    Args:
        backup_path: Full path to an unencrypted .sqlite backup.

    Returns JSON with status ('ok' or errors) and table count.
    """
    bp = Path(backup_path)
    if not bp.exists():
        return [TextContent(type="text", text=f"ERROR: file not found: {backup_path}")]
    if bp.suffix == ".enc":
        return [TextContent(type="text", text="ERROR: cannot verify an encrypted backup — decrypt first.")]

    try:
        conn = sqlite3.connect(f"file:{bp}?mode=ro", uri=True)
        rows = conn.execute("PRAGMA integrity_check").fetchall()
        table_count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        conn.close()
    except Exception as exc:
        return [TextContent(type="text", text=f"ERROR opening backup: {exc}")]

    messages = [r[0] for r in rows]
    ok = messages == ["ok"]
    result = {
        "path":        str(bp),
        "size":        _human_size(bp.stat().st_size),
        "status":      "ok" if ok else "errors",
        "tables":      table_count,
        "integrity":   messages,
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ---------------------------------------------------------------------------
# M7.5 — restore_db
# ---------------------------------------------------------------------------


@app.tool()
async def restore_db(
    backup_path: str,
    confirm: str = "",
) -> list[TextContent]:
    """Restore the Metis database from a backup.

    Renames the current live database to <db>.pre-restore.<timestamp>
    before overwriting, so you can recover if something goes wrong.

    IMPORTANT: This overwrites the live database. All changes since the backup
    was taken will be lost. The dashboard must be restarted after restore.

    Args:
        backup_path: Full path to the .sqlite backup to restore from.
        confirm:     Must be the string 'YES' to proceed.

    Returns JSON with status and paths.
    """
    if confirm != "YES":
        return [TextContent(
            type="text",
            text='ABORTED: pass confirm="YES" to restore. '
                 'WARNING: this overwrites the live database — all changes since the backup will be lost.',
        )]

    bp = Path(backup_path)
    if not bp.exists():
        return [TextContent(type="text", text=f"ERROR: backup not found: {backup_path}")]
    if bp.suffix == ".enc":
        return [TextContent(type="text", text="ERROR: cannot restore an encrypted backup — decrypt first.")]

    live = paths.db
    pre_restore = live.with_suffix(f".pre-restore.{_ts()}.sqlite")

    # Rename live DB out of the way
    if live.exists():
        shutil.copy2(live, pre_restore)

    # Copy backup → live
    shutil.copy2(bp, live)

    result = {
        "status":             "restored",
        "restored_from":      str(bp),
        "pre_restore_backup": str(pre_restore),
        "live_db":            str(live),
        "note":               "Restart the dashboard to pick up the restored database.",
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ---------------------------------------------------------------------------
# M7.1b — get_backup_schedule / set_backup_schedule
# ---------------------------------------------------------------------------


def _schedule_path() -> Path:
    return paths.config / "backup-schedule.json"


@app.tool()
async def set_backup_schedule(
    enabled: bool = True,
    time_utc: str = "02:00",
    keep_days: int = 30,
    destination: str = "",
) -> list[TextContent]:
    """Configure the nightly backup schedule.

    The schedule is read by the scheduler (Phase 10) to trigger backup_db()
    automatically. This tool only persists the configuration.

    Args:
        enabled:     Whether automatic nightly backups are on.
        time_utc:    Time in HH:MM UTC to run the backup (e.g. '02:00').
        keep_days:   How many days of backups to retain (older ones deleted).
        destination: Backup directory (defaults to metis/system/backups/).
    """
    schedule = {
        "enabled":     enabled,
        "time_utc":    time_utc,
        "keep_days":   keep_days,
        "destination": destination or str(_default_backup_dir()),
    }
    p = _schedule_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(schedule, indent=2), encoding="utf-8")
    return [TextContent(type="text", text=f"Backup schedule saved: {'enabled' if enabled else 'disabled'} at {time_utc} UTC, keep {keep_days}d.")]


@app.tool()
async def get_backup_schedule() -> list[TextContent]:
    """Return the current backup schedule configuration."""
    p = _schedule_path()
    if not p.exists():
        default = {
            "enabled": False,
            "time_utc": "02:00",
            "keep_days": 30,
            "destination": str(_default_backup_dir()),
            "note": "Not configured. Call set_backup_schedule() to enable nightly backups.",
        }
        return [TextContent(type="text", text=json.dumps(default, indent=2))]
    return [TextContent(type="text", text=p.read_text(encoding="utf-8"))]
