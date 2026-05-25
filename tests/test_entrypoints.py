"""Tests for current production entrypoint hygiene."""
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_systemd_service_targets_main_web_app():
    service_file = REPO_ROOT / "deploy" / "systemd" / "finco-web.service"
    content = service_file.read_text(encoding="utf-8")
    assert "gunicorn" in content
    assert "main_web:app" in content


def test_readme_quickstart_targets_fastapi_runtime():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "uvicorn main_web:app --reload" in readme
    assert "streamlit run streamlit_app.py" not in readme


def test_legacy_src_entrypoint_removed():
    assert not (REPO_ROOT / "src" / "app.py").exists()
    assert not (REPO_ROOT / "src" / "startup.sh").exists()
