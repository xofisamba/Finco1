"""Phase 16 checks for Streamlit decouple and legacy pruning."""
from __future__ import annotations

import csv
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_blocked_streamlit_import(target: str) -> subprocess.CompletedProcess[str]:
    code = f"""
import builtins
real_import = builtins.__import__
def blocked(name, *args, **kwargs):
    if name == "streamlit" or name.startswith("streamlit."):
        raise ModuleNotFoundError("No module named 'streamlit'")
    return real_import(name, *args, **kwargs)
builtins.__import__ = blocked
import {target}
print("ok")
"""
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )


def test_app_cache_and_main_web_import_without_streamlit():
    cache_result = _run_blocked_streamlit_import("app.cache")
    assert cache_result.returncode == 0, cache_result.stderr
    assert "ok" in cache_result.stdout

    main_web_source = (REPO_ROOT / "main_web.py").read_text(encoding="utf-8")
    assert "streamlit" not in main_web_source.lower()

    if importlib.util.find_spec("fastapi") is None:
        pytest.skip("fastapi is not installed in this interpreter; app.cache decouple verified directly")

    main_web_result = _run_blocked_streamlit_import("main_web")
    assert main_web_result.returncode == 0, main_web_result.stderr
    assert "ok" in main_web_result.stdout


def test_production_entrypoint_and_requirements_are_streamlit_free():
    requirements = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "streamlit" not in requirements

    service = (REPO_ROOT / "deploy" / "systemd" / "finco-web.service").read_text(encoding="utf-8")
    assert "main_web:app" in service
    assert "streamlit run" not in service


def test_legacy_inventory_and_live_runtime_expectations():
    inventory_path = REPO_ROOT / "reports" / "phase16_streamlit_legacy_inventory.csv"
    rows = list(csv.DictReader(inventory_path.open(encoding="utf-8", newline="")))
    assert rows

    files_by_path = {row["file_path"]: row for row in rows}
    assert files_by_path["app/cache.py"]["classification"] == "ACTIVE_PRODUCTION_RISK"
    assert files_by_path["src/app.py"]["action_taken"] == "Deleted"
    assert files_by_path["src/startup.sh"]["action_taken"] == "Deleted"

    assert not (REPO_ROOT / "src" / "app.py").exists()
    assert not (REPO_ROOT / "src" / "startup.sh").exists()

    for runtime_file in [
        "app/ui_runner.py",
        "app/waterfall_runner.py",
        "app/waterfall_core.py",
        "app/output_tables.py",
    ]:
        assert (REPO_ROOT / runtime_file).exists(), f"Live runtime module removed: {runtime_file}"
