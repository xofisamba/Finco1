"""Phase 26C: Dependency Pinning / CI / Config Hardening — Tests

Dependency/config/CI hardening only. No runtime model changes.
"""
import subprocess
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo


# =============================================================================
# 1. Phase 26C doc exists
# =============================================================================


def test_phase26c_doc_exists():
    """docs/phase26c_dependency_pinning_ci_config_hardening.md exists."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase26c_dependency_pinning_ci_config_hardening.md"
    assert doc_path.exists(), f"Phase 26C doc not found at {doc_path}"
    content = doc_path.read_text()
    assert len(content) > 200, "Phase 26C doc should have meaningful content"


# =============================================================================
# 2. Dependency lock or pin strategy exists
# =============================================================================


def test_dependency_lock_or_pin_strategy_exists():
    """constraints.txt exists with pinned direct dependencies OR requirements.txt is pinned."""
    repo_root = Path(__file__).resolve().parents[1]

    constraints = repo_root / "constraints.txt"
    requirements = repo_root / "requirements.txt"

    if constraints.exists():
        content = constraints.read_text()
        # Should have == pins
        pin_lines = [l for l in content.splitlines()
                     if l.strip() and not l.strip().startswith("#") and "==" in l]
        assert len(pin_lines) >= 8, f"constraints.txt should have at least 8 pinned packages, got {len(pin_lines)}"
    elif requirements.exists():
        content = requirements.read_text()
        # requirements.txt should have == pins (Option A)
        pin_lines = [l for l in content.splitlines()
                     if l.strip() and not l.strip().startswith("#") and "==" in l]
        assert len(pin_lines) >= 8, "requirements.txt should be fully pinned if used as strategy"
    else:
        pytest.fail("Neither constraints.txt nor pinned requirements.txt found")


# =============================================================================
# 3. Dependency policy documented
# =============================================================================


def test_dependency_policy_documented():
    """Doc explains chosen strategy and why broad upgrades were avoided."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase26c_dependency_pinning_ci_config_hardening.md"
    if not doc_path.exists():
        pytest.skip("Phase 26C doc not found")
    content = doc_path.read_text().lower()
    assert "upgrade" in content or "upgrade" in content, "Doc should mention upgrade policy"
    assert "broad" in content or "intentional" in content, \
        "Doc should explain why broad upgrades were avoided"


# =============================================================================
# 4. Reproducible install documented
# =============================================================================


def test_reproducible_install_documented():
    """Doc includes install command using pinned/locked strategy."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase26c_dependency_pinning_ci_config_hardening.md"
    if not doc_path.exists():
        pytest.skip("Phase 26C doc not found")
    content = doc_path.read_text()
    # Should mention pip install with -c or constraints
    assert "-c constraints.txt" in content or "constraints.txt" in content, \
        "Doc should document install using constraints.txt"


# =============================================================================
# 5. CI uses pinned/locked dependencies if workflow changed
# =============================================================================


def test_ci_uses_pinned_or_locked_dependencies():
    """If CI workflow is changed, it must use pinned/locked dependencies."""
    repo_root = Path(__file__).resolve().parents[1]
    workflow_path = repo_root / ".github" / "workflows" / "ci.yml"

    assert workflow_path.exists(), "CI workflow should exist"

    content = workflow_path.read_text()

    # CI must use constraints or have pinned deps
    uses_constraints = "constraints.txt" in content or "-c " in content
    has_pinned_pytest = "pytest==" in content or "pytest >" in content

    assert uses_constraints or has_pinned_pytest, \
        "CI workflow should use constraints.txt or pinned pytest"


# =============================================================================
# 6. App mode config expectations documented
# =============================================================================


def test_app_mode_config_expectations_documented():
    """Doc mentions FINCO_APP_MODE development/internal/pilot and pilot required env vars."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase26c_dependency_pinning_ci_config_hardening.md"
    if not doc_path.exists():
        pytest.skip("Phase 26C doc not found")
    content = doc_path.read_text().lower()

    assert "finco_app_mode" in content, "Doc should mention FINCO_APP_MODE"
    assert "pilot" in content, "Doc should mention pilot mode"
    assert "development" in content and "internal" in content, \
        "Doc should mention development and internal modes"


# =============================================================================
# 7. No committed local DB or .env files
# =============================================================================


def test_no_committed_local_db_or_env_files():
    """Ensure no .env, local SQLite DB, WAL/SHM/journal, or backup DB files are tracked."""
    repo_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"],
        capture_output=True, text=True, cwd=repo_root
    )
    committed = set(result.stdout.strip().splitlines())

    violations = []
    for f in committed:
        # .env files: skip .env.example (legitimate placeholder documentation)
        if (f.startswith(".env") or f == ".env") and f != ".env.example":
            violations.append(f)
        if ".db" in f or ".sqlite" in f or "-wal" in f or "-shm" in f or "-journal" in f:
            violations.append(f)
        if "backups" in f.lower() and (".db" in f or ".sqlite" in f):
            violations.append(f)

    assert len(violations) == 0, f"Found committed files that should be gitignored: {violations[:5]}"


# =============================================================================
# 8. No broad dependency upgrade claims
# =============================================================================


def test_no_broad_dependency_upgrade_claims():
    """Doc states no broad dependency upgrades were performed."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase26c_dependency_pinning_ci_config_hardening.md"
    if not doc_path.exists():
        pytest.skip("Phase 26C doc not found")
    content = doc_path.read_text().lower()
    # Doc should explicitly say no broad upgrades
    assert "broad" in content or "no automatic" in content or "intentional" in content, \
        "Doc should address the no-broad-upgrade policy"


# =============================================================================
# 9. No runtime formula files changed
# =============================================================================


def test_no_runtime_formula_files_changed():
    """Doc states no financial formula changes; model files untouched."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase26c_dependency_pinning_ci_config_hardening.md"
    if not doc_path.exists():
        pytest.skip("Phase 26C doc not found")
    content = doc_path.read_text().lower()
    assert "no runtime" in content or "no financial formula" in content, \
        "Doc should state no runtime/financial formula changes"


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
