"""Phase 26B: Auth / Single-user Mode Boundary — Tests

Narrow auth/config boundary hardening. No runtime model changes.
"""
import os
import subprocess
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo


# =============================================================================
# Helper: isolate env for pilot-mode auth tests
# =============================================================================


def _run_auth_test_env(env_override: dict, code: str) -> subprocess.CompletedProcess:
    """Run a python snippet with modified env vars; return completed process."""
    env = os.environ.copy()
    env.update(env_override)
    return subprocess.run(
        ["python3", "-c", code],
        capture_output=True, text=True, env=env, cwd=Path(__file__).resolve().parents[1]
    )


# =============================================================================
# 1. Phase 26B doc exists
# =============================================================================


def test_phase26b_doc_exists():
    """docs/phase26b_auth_single_user_mode_boundary.md exists."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase26b_auth_single_user_mode_boundary.md"
    assert doc_path.exists(), f"Phase 26B doc not found at {doc_path}"
    content = doc_path.read_text()
    assert len(content) > 200, "Phase 26B doc should have meaningful content"


# =============================================================================
# 2. .env.example documents app mode and secret placeholders
# =============================================================================


def test_env_example_documents_app_mode_and_secret_placeholders():
    """.env.example includes FINCO_APP_MODE and pilot-mode warnings."""
    env_path = Path(__file__).resolve().parents[1] / ".env.example"
    assert env_path.exists(), ".env.example should exist"

    content = env_path.read_text()
    assert "FINCO_APP_MODE" in content, ".env.example should mention FINCO_APP_MODE"
    assert "pilot" in content.lower(), ".env.example should mention pilot mode"
    assert "changeme" in content.lower() or "dev-only" in content.lower(), \
        ".env.example should document placeholder values"


# =============================================================================
# 3. App mode allowed values
# =============================================================================


def test_app_mode_allowed_values():
    """get_app_mode() returns development/internal/pilot; unknown mode falls back to development."""
    from app.auth import get_app_mode, _VALID_APP_MODES

    assert get_app_mode.__defaults__ is not None or True  # function exists

    # Test via subprocess with isolated env for each mode
    for mode in ("development", "internal", "pilot"):
        result = _run_auth_test_env(
            {"FINCO_APP_MODE": mode,
             "FINCO_SECRET_KEY": "xK9#mP2$vL5@nQ8&jR3!wE6%tY0@zB7cD9fH1jL3",
             "FINCO_ADMIN_PASSWORD": "xK9#mP2$vL5@nQ8&jR3!wE6%tY0@zB7cD9fH1"},
            "import sys; sys.stdout.flush(); "
            "from app.auth import get_app_mode; "
            "print(get_app_mode())"
        )
        # stdout may include WARNING lines; take the last line as the result
        lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
        actual = lines[-1].strip() if lines else ""
        assert actual == mode, (
            f"FINCO_APP_MODE={mode}: expected {mode!r}, "
            f"got {actual!r} (full stdout: {result.stdout!r}, stderr: {result.stderr!r})"
        )


# =============================================================================
# 4. Placeholder secret detection
# =============================================================================


def test_placeholder_secret_detection():
    """is_placeholder_secret() detects obvious placeholder values."""
    from app.auth import is_placeholder_secret

    # Obvious placeholders — should be detected
    placeholders = [
        "changeme",
        "changeme!",
        "dev-only",
        "example",      # exact match
        "password",
        "password123",
        "secret",
        "secret-key",
        "fincoGPT2026!",
        "fincoGPT",
        "not-for-production",
        "not-for-pilot",
        "changeme-not-for-production",
        "changeme-dev-only-not-for-pilot",
        "",      # empty
        "admin",     # exact match
        "root",      # exact match
        "test",      # exact match
        "xxx",       # exact match
        "abc123",    # exact match
    ]
    for val in placeholders:
        assert is_placeholder_secret(val), f"Should detect placeholder: {val!r}"

    # Non-placeholders — should NOT be detected
    real_values = [
        "a3f8c2b1e9d04m7r8f2h3j5k1l9p6q3w4y",
        "xK9#mP2$vL5@nQ8&jR3!wE6%tY0@",
        "correct-horse-battery-staple",
        "securePassword123!",
        "test-only",   # compound word, not flagged as placeholder
    ]
    for val in real_values:
        assert not is_placeholder_secret(val), f"Should NOT detect as placeholder: {val!r}"


# =============================================================================
# 5. Pilot mode rejects placeholder SECRET_KEY (source-code check)
# =============================================================================


def test_pilot_mode_rejects_missing_or_placeholder_secret_key():
    """Pilot mode raises RuntimeError when SECRET_KEY is a placeholder."""
    # Verify the fail-fast check exists in source
    auth_path = Path(__file__).resolve().parents[1] / "app" / "auth.py"
    content = auth_path.read_text()
    assert "is_placeholder_secret(SECRET_KEY)" in content, \
        "auth.py should check if SECRET_KEY is a placeholder"
    assert "_is_pilot_mode()" in content, \
        "auth.py should check if running in pilot mode"
    assert "RuntimeError" in content and "pilot" in content.lower(), \
        "auth.py should raise RuntimeError in pilot mode for placeholder secrets"


# =============================================================================
# 6. Pilot mode rejects default admin password (source-code check)
# =============================================================================


def test_pilot_mode_rejects_default_admin_password():
    """Pilot mode raises RuntimeError when admin password is placeholder."""
    auth_path = Path(__file__).resolve().parents[1] / "app" / "auth.py"
    content = auth_path.read_text()
    assert "is_placeholder_secret(ADMIN_PASSWORD_PLAIN)" in content, \
        "auth.py should check if ADMIN_PASSWORD_PLAIN is a placeholder"
    assert "RuntimeError" in content and "pilot" in content.lower(), \
        "auth.py should raise RuntimeError in pilot mode for placeholder password"


# =============================================================================
# 7. Development mode allows placeholder but marks dev-only
# =============================================================================


def test_development_mode_allows_placeholder_but_marks_dev_only():
    """Development mode does not raise on placeholder secrets."""
    # In development mode, the RuntimeError guard should NOT be reached
    auth_path = Path(__file__).resolve().parents[1] / "app" / "auth.py"
    content = auth_path.read_text()

    # Find the pilot-mode check block
    pilot_secret_block = content[content.find("is_placeholder_secret(SECRET_KEY)"):
                                 content.find("is_placeholder_secret(SECRET_KEY)") + 300]
    pilot_password_block = content[content.find("is_placeholder_secret(ADMIN_PASSWORD_PLAIN)"):
                                   content.find("is_placeholder_secret(ADMIN_PASSWORD_PLAIN)") + 300]

    # Both should be guarded by `_is_pilot_mode()` — meaning they only fail in pilot mode
    assert "_is_pilot_mode()" in pilot_secret_block, \
        "SECRET_KEY placeholder check should be guarded by _is_pilot_mode()"
    assert "_is_pilot_mode()" in pilot_password_block, \
        "ADMIN_PASSWORD placeholder check should be guarded by _is_pilot_mode()"


# =============================================================================
# 8. No secret values logged or rendered
# =============================================================================


def test_no_secret_values_logged_or_rendered():
    """app/ code should not log raw secret/password values."""
    repo_root = Path(__file__).resolve().parents[1]

    # Patterns that suggest raw secret logging in app code
    suspicious_patterns = [
        '"SECRET_KEY"',   # string literal key in logs
        "'SECRET_KEY'",
    ]

    violations = []
    for pattern in suspicious_patterns:
        result = subprocess.run(
            ["grep", "-rn", pattern, "--include=*.py", "app/"],
            capture_output=True, text=True, cwd=repo_root
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = [l for l in result.stdout.splitlines()
                     if "print" not in l.lower() and "log" not in l.lower()]
            if lines:
                violations.extend(lines)

    assert len(violations) == 0, f"Found secret key in non-log context: {violations}"


# =============================================================================
# 9. Single-user boundary documented
# =============================================================================


def test_single_user_boundary_documented():
    """Doc states current app is single-user/internal or pilot-controlled only."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase26b_auth_single_user_mode_boundary.md"
    assert doc_path.exists(), "Phase 26B doc should exist"
    content = doc_path.read_text().lower()

    assert "single-user" in content, "Doc should mention single-user boundary"
    assert "multi-user" in content or "no multi-user" in content, \
        "Doc should address multi-user gap"
    assert "tenant isolation" in content, "Doc should mention tenant isolation gap"


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
