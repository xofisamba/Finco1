"""Phase 24F: SQLite Backup/Restore

Pilot-safety quick win — reduce data-loss risk before broader pilot usage.

This module provides:
- create_sqlite_backup(): create a timestamped backup copy
- list_sqlite_backups(): list available backups with metadata
- restore_sqlite_backup(): restore from a backup (with pre-restore safety backup)
- validate_sqlite_backup(): validate a backup file looks like SQLite
- get_sqlite_db_path(): resolve current DB path
- get_backup_dir(): resolve backup directory path

Safety:
- Path traversal protection: restore only accepts files within backup directory
- Pre-restore safety backup: always creates a pre-restore safety backup before restore
- SQLite header validation before restore
- WAL/SHM sidecars handled if present
- No sensitive data logged
"""

from __future__ import annotations

import hashlib
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

# Local imports
from app.persistence.db import DB_PATH

# Backup directory — configurable via FINCO_BACKUP_DIR env var
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DEFAULT_BACKUP_DIR = os.path.join(_DATA_DIR, "backups", "sqlite")
BACKUP_DIR = os.getenv("FINCO_BACKUP_DIR", DEFAULT_BACKUP_DIR)


class BackupMetadata(NamedTuple):
    """Metadata for a single backup."""
    backup_path: str
    filename: str
    timestamp: str  # ISO format
    size_bytes: int
    checksum: str  # MD5 hex digest
    source_db_path: str


class BackupListEntry(NamedTuple):
    """Entry returned by list_sqlite_backups()."""
    backup_path: str
    filename: str
    mtime: float  # seconds since epoch
    size_bytes: int


# ─────────────────────────────────────────────────────────────────────────────
# Path resolution
# ─────────────────────────────────────────────────────────────────────────────


def get_sqlite_db_path() -> str:
    """Return the current SQLite DB path."""
    return os.path.abspath(os.path.expanduser(DB_PATH))


def get_backup_dir() -> str:
    """Return the backup directory path, creating it if needed."""
    path = os.path.abspath(os.path.expanduser(BACKUP_DIR))
    os.makedirs(path, exist_ok=True)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Backup creation
# ─────────────────────────────────────────────────────────────────────────────


def _md5_hexdigest(file_path: str) -> str:
    """Return MD5 hex digest of a file."""
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy_sqlite_with_sidecars(src_db: str, dst_db: str) -> list[str]:
    """Copy SQLite DB file plus any WAL/SHM sidecars.

    Returns list of files copied.
    """
    copied = []
    for sidecar in ("-wal", "-shm", ""):
        src_path = src_db + sidecar
        if os.path.exists(src_path):
            dst_path = dst_db + sidecar
            shutil.copy2(src_path, dst_path)
            copied.append(dst_path)
    return copied


def create_sqlite_backup() -> BackupMetadata:
    """Create a timestamped backup of the current SQLite DB.

    Returns BackupMetadata for the new backup.

    Raises:
        FileNotFoundError: if current DB does not exist.
        RuntimeError: if backup directory cannot be created.
    """
    db_path = get_sqlite_db_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"SQLite DB not found at {db_path}")

    backup_dir = get_backup_dir()
    os.makedirs(backup_dir, exist_ok=True)

    # Timestamp-based filename
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    backup_filename = f"finco_runs_{ts}.db"
    backup_path = os.path.join(backup_dir, backup_filename)

    # Copy DB + sidecars
    copied = _copy_sqlite_with_sidecars(db_path, backup_path)

    # Also copy WAL/SHM from current DB if present (they may have unflushed data)
    # For WAL mode, we should checkpoint first to get all data into the main DB file
    try:
        import sqlite3
        conn = sqlite3.connect(db_path, timeout=10.0, isolation_level=None)
        conn.execute("PRAGMA wal_checkpoint(FULL)")
        conn.close()
    except Exception:
        pass  # Best-effort checkpoint — don't fail backup if this errors

    # Re-copy sidecars after checkpoint (they may have changed)
    _copy_sqlite_with_sidecars(db_path, backup_path)

    # Ensure backup file exists and has content
    if not os.path.exists(backup_path) or os.path.getsize(backup_path) == 0:
        raise RuntimeError(f"Backup file missing or empty: {backup_path}")

    size = os.path.getsize(backup_path)
    checksum = _md5_hexdigest(backup_path)

    return BackupMetadata(
        backup_path=backup_path,
        filename=backup_filename,
        timestamp=datetime.now(timezone.utc).isoformat(),
        size_bytes=size,
        checksum=checksum,
        source_db_path=db_path,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Backup listing
# ─────────────────────────────────────────────────────────────────────────────


def list_sqlite_backups() -> list[BackupListEntry]:
    """List all available backups in the backup directory.

    Returns list of BackupListEntry sorted newest-first by mtime.
    """
    backup_dir = get_backup_dir()
    if not os.path.isdir(backup_dir):
        return []

    entries = []
    for fname in os.listdir(backup_dir):
        fpath = os.path.join(backup_dir, fname)
        if not os.path.isfile(fpath):
            continue
        if not fname.startswith("finco_runs_") or not fname.endswith(".db"):
            continue
        st = os.stat(fpath)
        entries.append(BackupListEntry(
            backup_path=fpath,
            filename=fname,
            mtime=st.st_mtime,
            size_bytes=st.st_size,
        ))

    entries.sort(key=lambda e: e.mtime, reverse=True)
    return entries


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────


def validate_sqlite_backup(backup_path: str) -> tuple[bool, str]:
    """Validate a backup file looks like a valid SQLite database.

    Returns (is_valid, message).
    """
    if not os.path.isfile(backup_path):
        return False, f"Backup file not found: {backup_path}"

    size = os.path.getsize(backup_path)
    if size == 0:
        return False, "Backup file is empty"

    # Check SQLite header
    with open(backup_path, "rb") as f:
        header = f.read(16)
    if not header.startswith(b"SQLite format 3\x00"):
        return False, "File does not have a valid SQLite header"

    return True, "Valid SQLite database"


# ─────────────────────────────────────────────────────────────────────────────
# Restore
# ─────────────────────────────────────────────────────────────────────────────


def restore_sqlite_backup(backup_filename: str) -> tuple[bool, str]:
    """Restore the SQLite DB from a backup file.

    Safety rules:
    - backup_filename must be a bare filename (no path separators)
    - file must exist in the configured backup directory
    - a pre-restore safety backup is created before restore
    - WAL/SHM sidecars are restored alongside the DB file

    Returns (success, message).
    """
    # ── Path traversal protection ──────────────────────────────────────────
    if not backup_filename or os.path.sep in backup_filename or "/" in backup_filename or "\\" in backup_filename:
        return False, "Invalid backup filename — path separators not allowed"

    if ".." in backup_filename:
        return False, "Invalid backup filename — '..' not allowed"

    backup_dir = get_backup_dir()
    backup_path = os.path.join(backup_dir, backup_filename)

    # Resolve and verify it's inside the backup directory
    resolved = os.path.abspath(backup_path)
    if not resolved.startswith(os.path.abspath(backup_dir) + os.sep):
        return False, "Restore rejected — file is outside the backup directory"

    if not os.path.exists(resolved):
        return False, f"Backup file not found: {backup_filename}"

    # ── Validate SQLite header ─────────────────────────────────────────────
    is_valid, msg = validate_sqlite_backup(resolved)
    if not is_valid:
        return False, f"Restore rejected — {msg}"

    # ── Pre-restore safety backup ───────────────────────────────────────────
    current_db = get_sqlite_db_path()
    safety_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    safety_filename = f"pre_restore_safety_{safety_ts}.db"
    safety_path = os.path.join(backup_dir, safety_filename)

    if os.path.exists(current_db):
        _copy_sqlite_with_sidecars(current_db, safety_path)

    # ── Restore ─────────────────────────────────────────────────────────────
    try:
        # Close any open connections by removing WAL lock is not possible here,
        # but we copy the backup over the current DB
        shutil.copy2(backup_path, current_db)

        # Also copy WAL/SHM sidecars for the backup
        for sidecar in ("-wal", "-shm"):
            backup_sidecar = backup_path + sidecar
            if os.path.exists(backup_sidecar):
                shutil.copy2(backup_sidecar, current_db + sidecar)

        return True, f"Restore successful from {backup_filename}"
    except Exception as e:
        return False, f"Restore failed: {e}"
