"""C1-PR2: Spreadsheet Interaction Layer — Active Cell foundation.

Static wiring checks (always run, no optional dependency):
  - active-cell.js is served
  - base.html wires it in after engine.js and before app.js
  - existing pages still render unchanged

The JS-execution behaviour (active cell set/clear/idempotent
init/htmx-swap survival) is covered separately in
tests/test_c1_pr2_active_cell_browser.py, which intentionally never
imports main_web in-process — Playwright's sync API cannot run
inside an already-active asyncio/anyio event loop, and merely
importing main_web in this process is enough to leave one running.
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
    def test_active_cell_js_is_served(self, client):
        r = client.get("/static/interaction/active-cell.js")
        assert r.status_code == 200
        assert "FcActiveCellManager" in r.text

    def test_grid_registry_js_still_serves_active_cell_api(self, client):
        r = client.get("/static/interaction/grid-registry.js")
        assert r.status_code == 200
        assert "setActiveCell" in r.text
        assert "clearActiveCell" in r.text
        assert "getActiveCell" in r.text

    def test_app_js_unchanged_and_still_served(self, client):
        r = client.get("/static/app.js")
        assert r.status_code == 200
        assert "function queueWorkspaceDraftPersist" in r.text
        assert "htmx:afterSwap" in r.text
        assert "bindEditableGridInputs" in r.text

    def test_base_html_loads_active_cell_after_engine_before_app_js(self, client):
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "/static/interaction/grid-registry.js" in body
        assert "/static/interaction/engine.js" in body
        assert "/static/interaction/active-cell.js" in body
        assert "/static/app.js" in body

        registry_pos = body.index("/static/interaction/grid-registry.js")
        engine_pos = body.index("/static/interaction/engine.js")
        active_cell_pos = body.index("/static/interaction/active-cell.js")
        app_js_pos = body.index('/static/app.js"')
        assert registry_pos < engine_pos < active_cell_pos < app_js_pos

    def test_existing_workspace_page_still_renders(self, client):
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "workspace-content" in body
        assert 'id="main-form"' in body
