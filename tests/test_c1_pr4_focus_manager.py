"""C1-PR4: Spreadsheet Interaction Layer — DOM Focus Management.

Static wiring checks (always run, no optional dependency):
  - focus-manager.js is served
  - base.html wires it in after swap-lifecycle.js and before app.js
  - existing pages still render unchanged

The JS-execution behaviour (focus follows active cell, restores
after swap, clears safely, idempotent init) is covered separately in
tests/test_c1_pr4_focus_manager_browser.py, which intentionally
never imports main_web — Playwright's sync API cannot run inside an
already-active asyncio/anyio event loop, and merely importing
main_web in this process is enough to leave one running.
"""
import os
import sys

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from main_web import app
from app.auth import create_session_token


@pytest.fixture
def client():
    tc = TestClient(app)
    token = create_session_token()
    tc.cookies.set("finco_session", token)
    return tc


class TestStaticWiring:
    def test_focus_manager_js_is_served(self, client):
        r = client.get("/static/interaction/focus-manager.js")
        assert r.status_code == 200
        assert "FcFocusManager" in r.text

    def test_swap_lifecycle_js_unchanged_and_still_served(self, client):
        r = client.get("/static/interaction/swap-lifecycle.js")
        assert r.status_code == 200
        assert "FcSwapLifecycle" in r.text

    def test_active_cell_js_unchanged_and_still_served(self, client):
        r = client.get("/static/interaction/active-cell.js")
        assert r.status_code == 200
        assert "FcActiveCellManager" in r.text

    def test_app_js_unchanged_and_still_served(self, client):
        r = client.get("/static/app.js")
        assert r.status_code == 200
        assert "function queueWorkspaceDraftPersist" in r.text
        assert "htmx:afterSwap" in r.text
        assert "bindEditableGridInputs" in r.text

    def test_base_html_loads_focus_manager_after_swap_lifecycle_before_app_js(self, client):
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "/static/interaction/swap-lifecycle.js" in body
        assert "/static/interaction/focus-manager.js" in body
        assert "/static/app.js" in body

        swap_lifecycle_pos = body.index("/static/interaction/swap-lifecycle.js")
        focus_manager_pos = body.index("/static/interaction/focus-manager.js")
        app_js_pos = body.index('/static/app.js"')
        assert swap_lifecycle_pos < focus_manager_pos < app_js_pos

    def test_existing_workspace_page_still_renders(self, client):
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "workspace-content" in body
        assert 'id="main-form"' in body
