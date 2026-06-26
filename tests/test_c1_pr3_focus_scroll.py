"""C1-PR3: Spreadsheet Interaction Layer — Focus & Scroll Preservation.

Static wiring checks (always run, no optional dependency):
  - swap-lifecycle.js is served
  - base.html wires it in after active-cell.js and before app.js
  - existing pages still render unchanged

The JS-execution behaviour (active cell / scroll restore on swap,
safe clearing, idempotent init) is covered separately in
tests/test_c1_pr3_focus_scroll_browser.py, which intentionally never
imports main_web — Playwright's sync API cannot run inside an
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
    def test_swap_lifecycle_js_is_served(self, client):
        r = client.get("/static/interaction/swap-lifecycle.js")
        assert r.status_code == 200
        assert "FcSwapLifecycle" in r.text

    def test_grid_registry_js_still_serves_container_and_grid_ids(self, client):
        r = client.get("/static/interaction/grid-registry.js")
        assert r.status_code == 200
        assert "getGridIds" in r.text
        assert "data-fc-scroll-container" in r.text

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

    def test_base_html_loads_swap_lifecycle_after_active_cell_before_app_js(self, client):
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "/static/interaction/active-cell.js" in body
        assert "/static/interaction/swap-lifecycle.js" in body
        assert "/static/app.js" in body

        active_cell_pos = body.index("/static/interaction/active-cell.js")
        swap_lifecycle_pos = body.index("/static/interaction/swap-lifecycle.js")
        app_js_pos = body.index('/static/app.js"')
        assert active_cell_pos < swap_lifecycle_pos < app_js_pos

    def test_existing_workspace_page_still_renders(self, client):
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "workspace-content" in body
        assert 'id="main-form"' in body
