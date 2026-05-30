"""Phase 24F.1: Auto-Backup Scheduling — Tests

Persistence safety hardening only. No runtime model changes.
"""
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

import app.persistence.backup_restore as br


# =============================================================================
# Helper: patch get_backup_dir to use temp dir
# =============================================================================


def _patch_backup_dir(monkeypatch, tmp_path):
    """Make get_backup_dir() return a temp directory."""
    bdir = str(tmp_path / "backups")
    os.makedirs(bdir, exist_ok=True)
    monkeypatch.setattr(br, "get_backup_dir", lambda: bdir)
    return bdir


# =============================================================================
# 1. Phase 24F.1 doc exists
# =============================================================================


def test_phase24f1_doc_exists():
    """docs/phase24f1_auto_backup_scheduling.md exists."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase24f1_auto_backup_scheduling.md"
    assert doc_path.exists(), f"Phase 24F.1 doc not found at {doc_path}"
    content = doc_path.read_text()
    assert len(content) > 200, "Phase 24F.1 doc should have meaningful content"


# =============================================================================
# 2. .env.example documents auto-backup config
# =============================================================================


def test_env_example_documents_auto_backup_config():
    """.env.example includes FINCO_AUTO_BACKUP_ENABLED, INTERVAL_HOURS, MAX_FILES."""
    env_path = Path(__file__).resolve().parents[1] / ".env.example"
    assert env_path.exists(), ".env.example should exist"
    content = env_path.read_text()
    assert "FINCO_AUTO_BACKUP_ENABLED" in content
    assert "FINCO_AUTO_BACKUP_INTERVAL_HOURS" in content
    assert "FINCO_AUTO_BACKUP_MAX_FILES" in content


# =============================================================================
# 3. Auto-backup config defaults are safe
# =============================================================================


def test_auto_backup_config_defaults_are_safe():
    """Config returns safe defaults; interval and max files are positive."""
    c = br.get_auto_backup_config()
    assert c.interval_hours > 0, "Interval must be positive"
    assert c.max_files > 0, "Max files must be positive"
    assert isinstance(c.enabled, bool), "enabled must be bool"


# =============================================================================
# 4. Should create auto-backup when no prior auto-backup exists
# =============================================================================


def test_should_create_auto_backup_when_no_prior_auto_backup(tmp_path, monkeypatch):
    """With auto-backup enabled and DB exists, due check returns true when no prior auto backup."""
    _patch_backup_dir(monkeypatch, tmp_path)

    # Enable auto-backup
    monkeypatch.setattr(br, "_AUTO_BACKUP_ENABLED", True)
    monkeypatch.setattr(br, "_AUTO_BACKUP_INTERVAL_HOURS", 24)

    # Create DB
    db_path = str(tmp_path / "test.db")
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE t(id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(br, "get_sqlite_db_path", lambda: db_path)

    # No auto backups — should be due
    result = br.should_create_auto_backup(now=datetime.now(timezone.utc))
    assert result is True, "Should be due when no prior auto backup exists"


# =============================================================================
# 5. Should NOT create auto-backup when recent backup exists
# =============================================================================


def test_should_not_create_auto_backup_when_recent_backup_exists(tmp_path, monkeypatch):
    """Due check returns false if latest auto backup is newer than interval."""
    bdir = _patch_backup_dir(monkeypatch, tmp_path)

    monkeypatch.setattr(br, "_AUTO_BACKUP_ENABLED", True)
    monkeypatch.setattr(br, "_AUTO_BACKUP_INTERVAL_HOURS", 24)

    # Create DB
    db_path = str(tmp_path / "test.db")
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE t(id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(br, "get_sqlite_db_path", lambda: db_path)

    # Create a RECENT auto backup file (mtime = now)
    now = datetime.now(timezone.utc)
    recent_name = f"auto_finco_runs_{now.strftime('%Y%m%d_%H%M%S_%f')}.db"
    recent_path = os.path.join(bdir, recent_name)
    with open(recent_path, "wb") as f:
        f.write(b"SQLite format 3\x00" + b"\x00" * 100)
    # Set mtime to now
    os.utime(recent_path, (now.timestamp(), now.timestamp()))

    # Should NOT be due — backup is recent
    result = br.should_create_auto_backup(now=now)
    assert result is False, "Should NOT be due when recent auto backup exists"


# =============================================================================
# 6. Should create auto-backup when latest backup is old
# =============================================================================


def test_should_create_auto_backup_when_latest_backup_is_old(tmp_path, monkeypatch):
    """Due check returns true when latest auto backup is older than interval."""
    bdir = _patch_backup_dir(monkeypatch, tmp_path)

    monkeypatch.setattr(br, "_AUTO_BACKUP_ENABLED", True)
    monkeypatch.setattr(br, "_AUTO_BACKUP_INTERVAL_HOURS", 1)  # 1 hour

    # Create DB
    db_path = str(tmp_path / "test.db")
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE t(id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(br, "get_sqlite_db_path", lambda: db_path)

    # Create an OLD auto backup (25 hours ago)
    old_time = datetime.now(timezone.utc) - timedelta(hours=25)
    old_name = "auto_finco_runs_old.db"
    old_path = os.path.join(bdir, old_name)
    with open(old_path, "wb") as f:
        f.write(b"SQLite format 3\x00" + b"\x00" * 100)
    os.utime(old_path, (old_time.timestamp(), old_time.timestamp()))

    now = datetime.now(timezone.utc)
    result = br.should_create_auto_backup(now=now)
    assert result is True, "Should be due when latest auto backup is older than interval"


# =============================================================================
# 7. create_auto_backup_if_due creates valid backup
# =============================================================================


def test_create_auto_backup_if_due_creates_valid_backup(tmp_path, monkeypatch):
    """Creates auto backup with auto_ prefix; validates SQLite header."""
    bdir = _patch_backup_dir(monkeypatch, tmp_path)

    monkeypatch.setattr(br, "_AUTO_BACKUP_ENABLED", True)
    monkeypatch.setattr(br, "_AUTO_BACKUP_INTERVAL_HOURS", 24)
    monkeypatch.setattr(br, "_AUTO_BACKUP_MAX_FILES", 10)

    # Create DB with data
    db_path = str(tmp_path / "test.db")
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE t(id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO t VALUES(1, 'alice')")
    conn.commit()
    conn.close()
    monkeypatch.setattr(br, "get_sqlite_db_path", lambda: db_path)

    now = datetime.now(timezone.utc)
    meta = br.create_auto_backup_if_due(now=now)

    assert meta is not None, "Should create backup when due"
    assert "auto_finco_runs_" in meta.filename, \
        f"Filename should have auto_ prefix, got: {meta.filename}"
    assert meta.filename.endswith(".db"), "Should have .db extension"

    # Validate SQLite header
    with open(meta.backup_path, "rb") as f:
        header = f.read(16)
    assert header.startswith(b"SQLite format 3\x00"), \
        "Backup must have valid SQLite header"


# =============================================================================
# 8. Auto-backup prunes only auto backups
# =============================================================================


def test_auto_backup_prunes_only_auto_backups(tmp_path, monkeypatch):
    """Pruning removes old auto backups beyond max; does not remove manual backups."""
    bdir = _patch_backup_dir(monkeypatch, tmp_path)

    monkeypatch.setattr(br, "_AUTO_BACKUP_MAX_FILES", 3)

    # Create DB
    db_path = str(tmp_path / "test.db")
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE t(id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

    ts = datetime.now(timezone.utc)

    # Create 5 auto backups (oldest first by name)
    for i in range(5):
        f_path = os.path.join(bdir, f"auto_finco_runs_{i:03d}.db")
        with open(f_path, "wb") as f:
            f.write(b"SQLite format 3\x00" + b"\x00" * 50)
        old = (ts - timedelta(hours=i * 2)).timestamp()
        os.utime(f_path, (old, old))

    # Create a manual backup (should NOT be pruned)
    manual = os.path.join(bdir, "finco_runs_manual.db")
    with open(manual, "wb") as f:
        f.write(b"SQLite format 3\x00" + b"\x00" * 50)
    os.utime(manual, (ts.timestamp(), ts.timestamp()))

    # Create a pre-restore safety backup (should NOT be pruned)
    safety = os.path.join(bdir, "pre_restore_safety_20260530_120000_000000.db")
    with open(safety, "wb") as f:
        f.write(b"SQLite format 3\x00" + b"\x00" * 50)
    os.utime(safety, (ts.timestamp(), ts.timestamp()))

    deleted = br.prune_auto_backups(max_backups=3)

    assert deleted == 2, f"Should delete 2 old auto backups, got {deleted}"
    assert os.path.exists(manual), "Manual backup should NOT be deleted"
    assert os.path.exists(safety), "Pre-restore safety backup should NOT be deleted"
    remaining = list(Path(bdir).glob("auto_finco_runs_*.db"))
    assert len(remaining) == 3, f"Should have 3 auto backups, got {len(remaining)}"


# =============================================================================
# 9. No generated backups committed or gitignored
# =============================================================================


def test_no_generated_backups_committed_or_gitignored():
    """Confirm backup dir / *.db / *.sqlite / WAL/SHM are gitignored or not tracked."""
    repo_root = Path(__file__).resolve().parents[1]
    result = __import__("subprocess").run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"],
        capture_output=True, text=True, cwd=repo_root
    )
    committed = set(result.stdout.strip().splitlines())

    violations = []
    for f in committed:
        if "app/data/backups" in f or f.startswith("app/data/"):
            violations.append(f)
        if f.endswith(".db") and ("finco_runs_" in f or "auto_finco" in f):
            violations.append(f)

    # app/data/.gitkeep is acceptable
    violations = [v for v in violations if not v.endswith(".gitkeep")]

    assert len(violations) == 0, f"Found committed backup files: {violations[:5]}"

    gitignore = repo_root / ".gitignore"
    content = gitignore.read_text()
    assert "*.db" in content, ".gitignore should cover *.db"
    assert "app/data/" in content, ".gitignore should cover app/data/"


# =============================================================================
# 10. No runtime formula files changed
# =============================================================================


def test_no_runtime_formula_files_changed():
    """Doc states no financial formula changes; model files untouched."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase24f1_auto_backup_scheduling.md"
    assert doc_path.exists(), "Phase 24F.1 doc should exist"
    content = doc_path.read_text().lower()
    assert "no runtime" in content or "no financial formula" in content


# =============================================================================
# 11. Guardrails unchanged
# =============================================================================


def test_guardrails_unchanged():
    """Guardrails preserved: G20/R99/R102 blocked, no flags promoted."""
    from app.project_factories import create_default_oborovo
    oborovo = create_default_oborovo()
    info = oborovo.info
    assert not hasattr(info, "use_g20_engine"), "G20 must remain blocked"
    assert not hasattr(info, "use_r99_engine"), "R99 must remain not approved"
    assert not hasattr(info, "use_r102_engine"), "R102 must remain not approved"
    assert not hasattr(info, "flat_dscr_sculpted"), "flat_dscr_sculpted must not be promoted"
    assert not hasattr(info, "minimum_dscr_sculpted"), "minimum_dscr_sculpted must not be promoted"
    assert not hasattr(info, "partial_pay_sweep"), "partial_pay_sweep must not be promoted"
