"""C1-PR1: Spreadsheet Interaction Layer — GridRegistry foundation.

Static wiring checks (always run, no optional dependency):
  - static files are served
  - base.html wires the new scripts in before app.js, without
    removing app.js
  - existing pages still render unchanged (no regression to the
    workspace shell or to app.js)

The JS-execution behaviour (registry init/idempotency/lifecycle
hook) is covered separately in
tests/test_c1_pr1_grid_registry_browser.py, which intentionally
never imports main_web in-process — Playwright's sync API cannot
run inside an already-active asyncio/anyio event loop, and merely
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
    def test_grid_registry_js_is_served(self, client):
        r = client.get("/static/interaction/grid-registry.js")
        assert r.status_code == 200
        assert "FcGridRegistry" in r.text

    def test_engine_js_is_served(self, client):
        r = client.get("/static/interaction/engine.js")
        assert r.status_code == 200
        assert "FcInteractionEngine" in r.text

    def test_app_js_unchanged_and_still_served(self, client):
        r = client.get("/static/app.js")
        assert r.status_code == 200
        # The existing draft-persistence / htmx:afterSwap machinery
        # this PR must not touch is still present verbatim.
        assert "function queueWorkspaceDraftPersist" in r.text
        assert "htmx:afterSwap" in r.text
        assert "bindEditableGridInputs" in r.text

    def test_base_html_loads_engine_before_app_js_without_removing_app_js(self, client):
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "/static/vendor/htmx.min.js" in body
        assert "/static/interaction/grid-registry.js" in body
        assert "/static/interaction/engine.js" in body
        assert "/static/app.js" in body

        registry_pos = body.index("/static/interaction/grid-registry.js")
        engine_pos = body.index("/static/interaction/engine.js")
        app_js_pos = body.index('/static/app.js"')
        assert registry_pos < engine_pos < app_js_pos

    def test_existing_workspace_page_still_renders(self, client):
        """No visible regression: the main workspace shell still
        renders with its pre-existing structural anchors intact."""
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "workspace-content" in body
        assert 'id="main-form"' in body
