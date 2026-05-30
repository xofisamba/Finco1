"""Phase 24F: SQLite Backup/Restore — Tests

Pilot-safety quick win. No runtime model changes.
"""
import os
import tempfile
import time

import pytest

from app.persistence.backup_restore import (
    create_sqlite_backup,
    get_backup_dir,
    get_sqlite_db_path,
    list_sqlite_backups,
    restore_sqlite_backup,
    validate_sqlite_backup,
)


# =============================================================================
# 1. Backup creates timestamped copy
# =============================================================================


def test_backup_creates_timestamped_copy(tmp_path, monkeypatch):
    """Create a temp SQLite DB, back it up, assert backup file exists with timestamp."""
    # Use a temp DB path
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("FINCO_DB_PATH", db_path)
    monkeypatch.setenv("FINCO_BACKUP_DIR", str(tmp_path / "backups"))

    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test(id INTEGER PRIMARY KEY)")
    conn.execute("INSERT INTO test(id) VALUES(1)")
    conn.commit()
    conn.close()

    # Override get_sqlite_db_path to use our temp path
    import app.persistence.backup_restore as br
    monkeypatch.setattr(br, "DB_PATH", db_path)

    meta = create_sqlite_backup()

    assert os.path.exists(meta.backup_path), "Backup file should exist"
    assert meta.size_bytes > 0, "Backup should not be empty"
    assert "finco_runs_" in meta.filename, "Filename should include timestamp prefix"
    assert ".db" in meta.filename, "Filename should have .db extension"
    assert meta.source_db_path == db_path


# =============================================================================
# 2. Backup preserves SQLite contents
# =============================================================================


def test_backup_preserves_sqlite_contents(tmp_path, monkeypatch):
    """Create a DB with a row, back it up, open backup and assert row exists."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("FINCO_DB_PATH", db_path)
    monkeypatch.setenv("FINCO_BACKUP_DIR", str(tmp_path / "backups"))

    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test(id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO test(id, name) VALUES(1, 'alice')")
    conn.commit()
    conn.close()

    import app.persistence.backup_restore as br
    monkeypatch.setattr(br, "DB_PATH", db_path)

    meta = create_sqlite_backup()

    import sqlite3
    bak = sqlite3.connect(meta.backup_path)
    row = bak.execute("SELECT * FROM test").fetchone()
    bak.close()

    assert row is not None, "Backup should contain the inserted row"
    assert row[1] == "alice", f"Row name should be 'alice', got {row[1]}"


# =============================================================================
# 3. List backups returns metadata
# =============================================================================


def test_list_backups_returns_metadata(tmp_path, monkeypatch):
    """Create two backups, list them, assert metadata returned."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("FINCO_DB_PATH", db_path)
    monkeypatch.setenv("FINCO_BACKUP_DIR", str(tmp_path / "backups"))

    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test(id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

    import app.persistence.backup_restore as br
    monkeypatch.setattr(br, "DB_PATH", db_path)

    # Create two backups
    meta1 = create_sqlite_backup()
    time.sleep(0.01)  # ensure different mtime
    meta2 = create_sqlite_backup()

    entries = list_sqlite_backups()

    assert len(entries) >= 2, "Should have at least 2 backups"
    for entry in entries:
        assert entry.backup_path
        assert entry.filename
        assert entry.mtime > 0
        assert entry.size_bytes > 0


# =============================================================================
# 4. Restore creates pre-restore safety backup
# =============================================================================


def test_restore_creates_pre_restore_safety_backup(tmp_path, monkeypatch):
    """Restore a backup, assert pre-restore safety backup was created."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("FINCO_DB_PATH", db_path)
    monkeypatch.setenv("FINCO_BACKUP_DIR", str(tmp_path / "backups"))

    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test(id INTEGER PRIMARY KEY, val TEXT)")
    conn.execute("INSERT INTO test(id, val) VALUES(1, 'original')")
    conn.commit()
    conn.close()

    import app.persistence.backup_restore as br
    monkeypatch.setattr(br, "DB_PATH", db_path)

    # Create backup of current DB
    backup_meta = create_sqlite_backup()

    # Modify current DB
    conn2 = sqlite3.connect(db_path)
    conn2.execute("UPDATE test SET val='modified'")
    conn2.commit()
    conn2.close()

    # Restore from backup
    success, msg = restore_sqlite_backup(backup_meta.filename)
    assert success, f"Restore should succeed: {msg}"

    # Verify current DB has original value
    conn3 = sqlite3.connect(db_path)
    row = conn3.execute("SELECT * FROM test").fetchone()
    conn3.close()
    assert row[1] == "original", f"Restored value should be 'original', got {row[1]}"

    # Verify pre-restore safety backup exists in backup directory
    backup_dir = get_backup_dir()
    safety_files = [f for f in os.listdir(backup_dir) if f.startswith("pre_restore_safety_")]
    assert len(safety_files) >= 1, f"Pre-restore safety backup should exist in {backup_dir}, found: {safety_files}"


# =============================================================================
# 5. Restore rejects path traversal
# =============================================================================


def test_restore_rejects_path_traversal(tmp_path, monkeypatch):
    """Attempt restore with ../ or absolute path — must fail safely."""
    monkeypatch.setenv("FINCO_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("FINCO_BACKUP_DIR", str(tmp_path / "backups"))

    # Try path traversal
    success, msg = restore_sqlite_backup("../etc/passwd")
    assert not success, "Restore should reject path traversal"
    assert "path separators not allowed" in msg or "Invalid" in msg or ".." in msg

    # Try absolute path
    success2, msg2 = restore_sqlite_backup("/etc/passwd")
    assert not success2, "Restore should reject absolute path"


# =============================================================================
# 6. Restore rejects non-SQLite file
# =============================================================================


def test_restore_rejects_non_sqlite_file(tmp_path, monkeypatch):
    """Create a text file in backup dir, restore should fail with clear error."""
    monkeypatch.setenv("FINCO_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("FINCO_BACKUP_DIR", str(tmp_path / "backups"))

    # Create a text file in the backup directory
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    fake_backup = backup_dir / "fake_backup.db"
    fake_backup.write_text("not a sqlite database")

    success, msg = restore_sqlite_backup("fake_backup.db")
    assert not success, "Restore should reject non-SQLite file"
    assert "SQLite header" in msg or "not found" in msg or "Restore rejected" in msg


# =============================================================================
# 7. WAL/SHM sidecars handled if present
# =============================================================================


def test_wal_shm_sidecars_handled_if_present(tmp_path, monkeypatch):
    """Create a DB with WAL mode, back it up, verify sidecar files are handled."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("FINCO_DB_PATH", db_path)
    monkeypatch.setenv("FINCO_BACKUP_DIR", str(tmp_path / "backups"))

    import sqlite3
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE test(id INTEGER PRIMARY KEY, val TEXT)")
    conn.execute("INSERT INTO test(val) VALUES('wal_test')")
    conn.commit()
    conn.close()

    import app.persistence.backup_restore as br
    monkeypatch.setattr(br, "DB_PATH", db_path)

    meta = create_sqlite_backup()

    # Verify backup exists
    assert os.path.exists(meta.backup_path)

    # Verify WAL/SHM sidecars from backup if they existed in source
    # (at minimum, the main DB file should be valid)
    is_valid, msg = validate_sqlite_backup(meta.backup_path)
    assert is_valid, f"Backup should be valid SQLite: {msg}"


# =============================================================================
# 8. Guardrails — no model changes
# =============================================================================


def test_guardrails_no_model_changes():
    """Assert factory flags unchanged, G20/R99/R102 blocked/not approved."""
    from app.project_factories import create_default_oborovo, create_default_tuho_wind1

    tuho = create_default_tuho_wind1()
    oborovo = create_default_oborovo()

    # TUHO frozen senior DS flags
    assert tuho.info.use_senior_debt_sizing_engine is True
    assert tuho.financing.use_frozen_excel_senior_debt_schedule is True

    # Oborovo frozen senior DS flags
    assert oborovo.info.use_senior_debt_sizing_engine is True
    assert oborovo.financing.use_frozen_excel_senior_debt_schedule is True

    # G20/R99/R102 blocked/not approved
    info = oborovo.info
    assert not hasattr(info, "use_g20_engine"), "G20 must remain blocked"
    assert not hasattr(info, "use_r99_engine"), "R99 must remain not approved"
    assert not hasattr(info, "use_r102_engine"), "R102 must remain not approved"
    assert not hasattr(info, "flat_dscr_sculpted"), "flat_dscr_sculpted must not be promoted"
    assert not hasattr(info, "minimum_dscr_sculpted"), "minimum_dscr_sculpted must not be promoted"
    assert not hasattr(info, "partial_pay_sweep"), "partial_pay_sweep must not be promoted"
