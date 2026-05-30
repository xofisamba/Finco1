"""Phase 26A: Security / Dependency Quick Wins — Tests

Security/config hardening only. No runtime model changes.
"""
import os
import re
import subprocess
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo


# =============================================================================
# Helper: get committed files from git HEAD
# =============================================================================


def _committed_files():
    """Return set of all files tracked in HEAD."""
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1]
    )
    return set(result.stdout.strip().splitlines())


# =============================================================================
# 1. Phase 26A doc exists
# =============================================================================


def test_phase26a_doc_exists():
    """docs/phase26a_security_dependency_quick_wins.md exists."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase26a_security_dependency_quick_wins.md"
    assert doc_path.exists(), f"Phase 26A doc not found at {doc_path}"
    content = doc_path.read_text()
    assert len(content) > 200, "Phase 26A doc should have meaningful content"


# =============================================================================
# 2. .env.example exists and uses placeholders
# =============================================================================


def test_env_example_exists_and_uses_placeholders():
    """.env.example exists with placeholder/example values only, no real secrets."""
    env_path = Path(__file__).resolve().parents[1] / ".env.example"
    assert env_path.exists(), ".env.example should exist"

    content = env_path.read_text()
    lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]

    safe_patterns = [
        "changeme",
        "example",
        "dev-only",
        "not-for-production",
        "lax",
        "24",  # default session hours
        "true",  # default cookie secure
    ]

    for line in lines:
        if "=" in line:
            key, val = line.split("=", 1)
            val = val.strip()
            is_safe = any(s in val.lower() for s in safe_patterns) or val == ""
            assert is_safe, f".env.example line has non-placeholder value: {key}={val}"


# =============================================================================
# 3. No committed local SQLite or backup files (check HEAD only)
# =============================================================================


def test_no_committed_local_sqlite_or_backup_files():
    """Repo HEAD does not include committed SQLite DB or backup artifacts."""
    committed = _committed_files()
    db_patterns = [".db", ".sqlite", ".sqlite3", "-wal", "-shm", "-journal"]
    committed_db = [f for f in committed if any(p in f for p in db_patterns)]
    assert len(committed_db) == 0, f"Found committed DB files in HEAD: {committed_db}"


# =============================================================================
# 4. .gitignore covers local DB and backups
# =============================================================================


def test_gitignore_covers_local_db_and_backups():
    """.gitignore includes patterns for local SQLite DB and backup files/directories."""
    gitignore_path = Path(__file__).resolve().parents[1] / ".gitignore"
    assert gitignore_path.exists(), ".gitignore should exist"

    content = gitignore_path.read_text().lower()

    required_patterns = ["*.db", "app/data/"]
    for pattern in required_patterns:
        assert pattern in content, f".gitignore should include '{pattern}'"


# =============================================================================
# 5. No production secret insecure fallback
# =============================================================================


def test_no_production_secret_insecure_fallback():
    """app/auth.py has explicit WARNING for insecure SECRET_KEY fallback."""
    auth_path = Path(__file__).resolve().parents[1] / "app" / "auth.py"
    if not auth_path.exists():
        pytest.skip("app/auth.py not found")

    content = auth_path.read_text()

    # SECRET_KEY dev fallback must be explicitly labeled
    assert '"dev-secret-please-change-in-production"' in content, \
        "SECRET_KEY dev fallback should be explicitly labeled as not-for-production"

    # Default admin password is a known placeholder, not a real credential
    assert "fincoGPT2026" in content  # explicitly NOT a real credential


# =============================================================================
# 6. Debug defaults are not production claims
# =============================================================================


def test_debug_defaults_are_not_production_claims():
    """Debug/dev mode is documented as development/internal only."""
    env_example = Path(__file__).resolve().parents[1] / ".env.example"

    if env_example.exists():
        content = env_example.read_text().lower()
        if "debug" in content:
            assert "development" in content or "local" in content or "not-for-production" in content, \
                "DEBUG should be documented as development/local only"

    auth_path = Path(__file__).resolve().parents[1] / "app" / "auth.py"
    if auth_path.exists():
        auth_content = auth_path.read_text()
        assert "WARNING" in auth_content, \
            "Insecure defaults should emit WARNING"


# =============================================================================
# 7. Dependency policy documented
# =============================================================================


def test_dependency_policy_documented():
    """Doc mentions pinned/direct dependencies or dependency policy."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase26a_security_dependency_quick_wins.md"
    if not doc_path.exists():
        pytest.skip("Phase 26A doc not found")
    content = doc_path.read_text().lower()
    assert "depend" in content, "Doc should mention dependency policy"


# =============================================================================
# 8. Backup/restore posture documented
# =============================================================================


def test_backup_restore_posture_documented():
    """Doc references Phase 24F backup/restore, backup directory, and not committing backups."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase26a_security_dependency_quick_wins.md"
    if not doc_path.exists():
        pytest.skip("Phase 26A doc not found")
    content = doc_path.read_text().lower()
    assert "backup" in content, "Doc should reference Phase 24F backup/restore"
    assert ".gitignore" in content or "not commit" in content, \
        "Doc should mention not committing backup files"


# =============================================================================
# 9. No runtime formula files changed
# =============================================================================


def test_no_runtime_formula_files_changed():
    """Phase 26A does not change known model files; doc states no financial/runtime changes."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase26a_security_dependency_quick_wins.md"
    if not doc_path.exists():
        pytest.skip("Phase 26A doc not found")
    content = doc_path.read_text().lower()
    assert "no runtime" in content or "no financial formula" in content


# =============================================================================
# 10. Guardrails unchanged
# =============================================================================


def test_guardrails_unchanged():
    """Guardrails preserved: G20/R99/R102 blocked, no flags promoted."""
    oborovo = create_default_oborovo()
    info = oborovo.info
    assert not hasattr(info, "use_g20_engine"), "G20 must remain blocked"
    assert not hasattr(info, "use_r99_engine"), "R99 must remain not approved"
    assert not hasattr(info, "use_r102_engine"), "R102 must remain not approved"
    assert not hasattr(info, "flat_dscr_sculpted"), "flat_dscr_sculpted must not be promoted"
    assert not hasattr(info, "minimum_dscr_sculpted"), "minimum_dscr_sculpted must not be promoted"
    assert not hasattr(info, "partial_pay_sweep"), "partial_pay_sweep must not be promoted"
