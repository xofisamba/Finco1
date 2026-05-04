"""Tests for entrypoint hygiene."""
import inspect
import sys
from pathlib import Path

# Add project root so streamlit_app (top-level) can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit_app as streamlit_app_module  # top-level entrypoint
from src import app as src_app_module


def test_src_app_contains_no_sandbox_path():
    src = inspect.getsource(src_app_module)
    assert "/root/.openclaw" not in src, "src/app.py must not contain sandbox paths"
    assert "sys.path.insert" not in src, "src/app.py must not manipulate sys.path"


def test_src_app_does_not_call_projectinputs_legacy_factories():
    src = inspect.getsource(src_app_module)
    assert "ProjectInputs.create_default_oborovo" not in src
    assert "ProjectInputs.create_default_tuho_wind1" not in src
    assert "create_default_oborovo" not in src
    assert "create_default_tuho_wind1" not in src


def test_streamlit_app_is_current_entrypoint():
    # streamlit_app should be importable and have st.set_page_config
    src = inspect.getsource(streamlit_app_module)
    assert "set_page_config" in src, "streamlit_app.py should be the current entrypoint"
