"""Targeted cleanup dependency-isolation coverage."""

from __future__ import annotations

import importlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_non_auth_contract_test_collects_without_real_bcrypt():
    env = os.environ.copy()
    env.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "tests/test_phase9_audit_economic_mode_contract.py",
            "-q",
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "test_phase9_audit_economic_mode_contract.py" in result.stdout or "13 tests collected" in result.stdout


def test_app_auth_import_isolated_for_non_auth_test_collection():
    auth = importlib.import_module("app.auth")
    assert hasattr(auth, "verify_login")
    bcrypt_module = sys.modules.get("bcrypt")
    assert bcrypt_module is not None
    assert hasattr(bcrypt_module, "checkpw")


def test_production_auth_behavior_is_not_rewritten_in_conftest():
    conftest_text = (ROOT / "tests" / "conftest.py").read_text(encoding="utf-8")
    auth_text = (ROOT / "app" / "auth.py").read_text(encoding="utf-8")

    assert "_install_test_bcrypt_stub" in conftest_text
    assert "import bcrypt" in auth_text
    assert "bcrypt.checkpw" in auth_text
