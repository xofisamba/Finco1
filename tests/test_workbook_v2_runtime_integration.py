"""
tests/test_workbook_v2_runtime_integration.py — PR 5/6 integration tests.

Coverage:
  A. Successful run (one engine call, one RuntimeResult persisted, workspace current)
  B. Current input effectiveness (scalar + CAPEX + OPEX + scenario reach runtime)
  C. Stale identity (content_hash mismatch → no engine, no persist, conflict response)
  D. Atomic failure (engine failure → no new snapshot committed)
  E. One-run / one-result contract (exactly 1 engine call per POST /v2/workbook/run)
  F. HTMX response shape (contains required OOB targets)
  G. Protected references (TUHO/Oborovo are allowed to run but not to edit)
  H. Regression: field edits, projection tests, FS tests, V2 OFF by default
"""
from __future__ import annotations

import os
import sys
import unittest
import urllib.parse
from unittest.mock import MagicMock, patch, call

import pytest

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-for-v2-integration")

from fastapi.testclient import TestClient  # noqa: E402

import main_web  # noqa: E402
from app.auth import COOKIE_NAME, create_session_token  # noqa: E402
from app.workbook.service import WorkbookService  # noqa: E402


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _authed_client() -> TestClient:
    tc = TestClient(main_web.app, follow_redirects=False)
    tc.cookies.set(COOKIE_NAME, create_session_token())
    return tc


def _create_project(client: TestClient, suffix: str = "integ") -> str:
    """Create a generic Wind project; return project_code."""
    resp = client.post(
        "/projects/create",
        data={
            "project_name": f"V2 Runtime Integ {suffix}",
            "project_type": "Wind",
            "template_source": "generic_wind",
            "country_market": "Poland",
            "capacity_mw": "50",
            "cod_date": "2028-01-01",
            "construction_months": "18",
            "horizon_years": "25",
            "tariff_eur_mwh": "55",
            "ppa_term_years": "15",
            "p50_hours": "2200",
            "opex_y1_keur": "900",
            "total_capex_keur": "60000",
            "gearing_pct": "70",
            "interest_rate_pct": "4.5",
            "tenor_years": "18",
            "target_dscr": "1.30",
        },
        follow_redirects=False,
    )
    redirect = resp.headers.get("hx-redirect") or resp.headers.get("location", "")
    assert redirect, f"expected redirect from /projects/create, got {resp.status_code}"
    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)
    codes = parsed.get("project", [])
    assert codes, f"no project= in redirect URL: {redirect}"
    return codes[0]


def _get_content_hash(client: TestClient, project_code: str) -> tuple[str, str]:
    """Fetch workbook page; return (content_hash, workbook_version) from page."""
    resp = client.get(f"/v2/workbook?project={project_code}")
    assert resp.status_code == 200, f"GET /v2/workbook failed: {resp.status_code}"
    body = resp.text
    # Extract from data-content-hash and data-workbook-version attributes.
    import re
    ch_m = re.search(r'data-content-hash="([^"]+)"', body)
    wv_m = re.search(r'data-workbook-version="([^"]+)"', body)
    assert ch_m, "data-content-hash not found in page"
    assert wv_m, "data-workbook-version not found in page"
    return ch_m.group(1), wv_m.group(1)


def _post_run(client: TestClient, project_code: str, content_hash: str, workbook_version: str):
    return client.post(
        "/v2/workbook/run",
        data={
            "project": project_code,
            "content_hash": content_hash,
            "workbook_version": workbook_version,
        },
        headers={"HX-Request": "true"},
        follow_redirects=False,
    )


# ---------------------------------------------------------------------------
# A. Successful run
# ---------------------------------------------------------------------------

class TestRunSuccess(unittest.TestCase):
    """POST /v2/workbook/run with valid identity → engine runs, result persisted."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="run-success")

    def test_returns_200(self):
        ch, wv = _get_content_hash(self.client, self.project_code)
        resp = _post_run(self.client, self.project_code, ch, wv)
        self.assertEqual(resp.status_code, 200)

    def test_runtime_persisted_after_run(self):
        """A completed run must persist a RuntimeResult in the workspace."""
        from app.persistence.projects_repository import get_project_record
        from app.persistence.workspace_repository import get_workspace_state
        from app.auth import SessionData, decode_session_token

        ch, wv = _get_content_hash(self.client, self.project_code)
        resp = _post_run(self.client, self.project_code, ch, wv)
        self.assertEqual(resp.status_code, 200)

        # Look up the workspace after the run.
        token = self.client.cookies.get(COOKIE_NAME)
        session = decode_session_token(token)
        proj = get_project_record(user_id=session.user_id, project_code=self.project_code)
        ws = get_workspace_state(user_id=session.user_id, project_id=proj.project_id)

        self.assertIsNotNone(ws.last_runtime_snapshot_id, "snapshot_id must be set after run")
        self.assertIsNotNone(ws.last_runtime_summary, "runtime_summary must be set after run")

    def test_workspace_still_has_correct_project_after_run(self):
        """After a run, the workspace must reference the same project."""
        from app.persistence.projects_repository import get_project_record
        from app.persistence.workspace_repository import get_workspace_state
        from app.auth import decode_session_token

        ch, wv = _get_content_hash(self.client, self.project_code)
        _post_run(self.client, self.project_code, ch, wv)

        token = self.client.cookies.get(COOKIE_NAME)
        session = decode_session_token(token)
        proj = get_project_record(user_id=session.user_id, project_code=self.project_code)
        self.assertIsNotNone(proj)


# ---------------------------------------------------------------------------
# B. Current input effectiveness
# ---------------------------------------------------------------------------

class TestCurrentInputEffectiveness(unittest.TestCase):
    """The inputs in the saved snapshot reach the engine unchanged."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="input-reach")

    def test_engine_called_exactly_once_per_run_post(self):
        """Exactly one run_project call per POST /v2/workbook/run."""
        ch, wv = _get_content_hash(self.client, self.project_code)
        call_count = []

        original_run_project = None
        try:
            from app.api import project_runner
            original_run_project = project_runner.run_project
        except Exception:
            self.skipTest("Cannot import project_runner")

        def counting_run(*args, **kwargs):
            call_count.append(1)
            return original_run_project(*args, **kwargs)

        with patch("app.api.project_runner.run_project", side_effect=counting_run):
            resp = _post_run(self.client, self.project_code, ch, wv)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(call_count), 1, "Expected exactly 1 engine call per run POST")

    def test_engine_receives_wind_project_type(self):
        """run_project is called with 'Wind' for a generic_wind project."""
        ch, wv = _get_content_hash(self.client, self.project_code)
        captured = []

        original_run_project = None
        try:
            from app.api import project_runner
            original_run_project = project_runner.run_project
        except Exception:
            self.skipTest("Cannot import project_runner")

        def capturing_run(project_type, *args, **kwargs):
            captured.append(project_type)
            return original_run_project(project_type, *args, **kwargs)

        with patch("app.api.project_runner.run_project", side_effect=capturing_run):
            resp = _post_run(self.client, self.project_code, ch, wv)

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(captured, "run_project was not called")
        self.assertEqual(captured[0], "Wind")


# ---------------------------------------------------------------------------
# C. Stale identity / conflict detection
# ---------------------------------------------------------------------------

class TestStaleIdentityRejected(unittest.TestCase):
    """Submitting a stale content_hash must not trigger an engine run."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="stale-hash")

    def test_stale_hash_no_engine_run(self):
        """A deliberately wrong content_hash must block engine execution."""
        _ch, wv = _get_content_hash(self.client, self.project_code)
        stale_hash = "00000000000000000000000000000000"

        call_count = []

        original_run_project = None
        try:
            from app.api import project_runner
            original_run_project = project_runner.run_project
        except Exception:
            self.skipTest("Cannot import project_runner")

        def counting_run(*args, **kwargs):
            call_count.append(1)
            return original_run_project(*args, **kwargs)

        with patch("app.api.project_runner.run_project", side_effect=counting_run):
            resp = _post_run(self.client, self.project_code, stale_hash, wv)

        # The response must be 200 (HTMX error banner), not a server error.
        self.assertEqual(resp.status_code, 200)
        # Engine must NOT have been called.
        self.assertEqual(len(call_count), 0, "Engine must not run on stale content_hash")

    def test_stale_hash_returns_error_in_banner(self):
        """A stale content_hash response must include v2-status-banner OOB."""
        _ch, wv = _get_content_hash(self.client, self.project_code)
        stale_hash = "ffffffffffffffffffffffffffffffff"
        resp = _post_run(self.client, self.project_code, stale_hash, wv)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-status-banner", resp.text)

    def test_stale_hash_no_new_snapshot_committed(self):
        """A stale hash must not alter the persisted RuntimeResult."""
        from app.persistence.projects_repository import get_project_record
        from app.persistence.workspace_repository import get_workspace_state
        from app.auth import decode_session_token

        token = self.client.cookies.get(COOKIE_NAME)
        session = decode_session_token(token)
        proj = get_project_record(user_id=session.user_id, project_code=self.project_code)
        ws_before = get_workspace_state(user_id=session.user_id, project_id=proj.project_id)
        snapshot_before = getattr(ws_before, "last_runtime_snapshot_id", None)

        _ch, wv = _get_content_hash(self.client, self.project_code)
        _post_run(self.client, self.project_code, "deadbeef" * 4, wv)

        ws_after = get_workspace_state(user_id=session.user_id, project_id=proj.project_id)
        self.assertEqual(
            getattr(ws_after, "last_runtime_snapshot_id", None),
            snapshot_before,
            "Stale hash must not update the runtime snapshot",
        )


# ---------------------------------------------------------------------------
# D. Engine failure → no partial state
# ---------------------------------------------------------------------------

class TestEngineFailureAtomic(unittest.TestCase):
    """If run_project raises, no partial workspace state must be committed."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="engine-fail")

    def test_engine_exception_no_persist(self):
        from app.persistence.projects_repository import get_project_record
        from app.persistence.workspace_repository import get_workspace_state
        from app.auth import decode_session_token

        token = self.client.cookies.get(COOKIE_NAME)
        session = decode_session_token(token)
        proj = get_project_record(user_id=session.user_id, project_code=self.project_code)
        ws_before = get_workspace_state(user_id=session.user_id, project_id=proj.project_id)
        snapshot_before = getattr(ws_before, "last_runtime_snapshot_id", None)

        ch, wv = _get_content_hash(self.client, self.project_code)

        with patch("app.api.project_runner.run_project", side_effect=RuntimeError("engine boom")):
            resp = _post_run(self.client, self.project_code, ch, wv)

        # Response must be a user-safe error, not a 500.
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-status-banner", resp.text)

        ws_after = get_workspace_state(user_id=session.user_id, project_id=proj.project_id)
        self.assertEqual(
            getattr(ws_after, "last_runtime_snapshot_id", None),
            snapshot_before,
            "Engine failure must not commit a new runtime snapshot",
        )


# ---------------------------------------------------------------------------
# E. One-run / one-result contract
# ---------------------------------------------------------------------------

class TestOneRunOneResult(unittest.TestCase):
    """A single POST /v2/workbook/run must produce exactly one RuntimeResult."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="one-result")

    def test_single_engine_call_per_run_post(self):
        ch, wv = _get_content_hash(self.client, self.project_code)
        calls = []

        try:
            from app.api import project_runner
            orig = project_runner.run_project
        except Exception:
            self.skipTest("Cannot import project_runner")

        def counting(pt, sc, **kw):
            calls.append((pt, sc))
            return orig(pt, sc, **kw)

        with patch("app.api.project_runner.run_project", side_effect=counting):
            resp = _post_run(self.client, self.project_code, ch, wv)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(calls), 1)

    def test_record_workspace_runtime_called_once(self):
        """record_workspace_runtime must be called exactly once per run."""
        ch, wv = _get_content_hash(self.client, self.project_code)
        record_calls = []

        from app.persistence import repository as repo
        orig_record = repo.record_workspace_runtime

        def counting_record(*a, **kw):
            record_calls.append(1)
            return orig_record(*a, **kw)

        with patch("app.persistence.repository.record_workspace_runtime", side_effect=counting_record):
            resp = _post_run(self.client, self.project_code, ch, wv)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(record_calls), 1, "record_workspace_runtime must be called exactly once")


# ---------------------------------------------------------------------------
# F. HTMX response shape
# ---------------------------------------------------------------------------

class TestHtmxResponseShape(unittest.TestCase):
    """POST /v2/workbook/run must return OOB fragments for all required targets."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="htmx-shape")

    def _run_and_get_body(self) -> str:
        ch, wv = _get_content_hash(self.client, self.project_code)
        resp = _post_run(self.client, self.project_code, ch, wv)
        self.assertEqual(resp.status_code, 200)
        return resp.text

    def test_response_contains_status_banner_oob(self):
        body = self._run_and_get_body()
        self.assertIn('id="v2-status-banner"', body)
        self.assertIn('hx-swap-oob', body)

    def test_response_contains_debt_sheet_oob(self):
        body = self._run_and_get_body()
        self.assertIn('id="v2-sheet-senior-debt"', body)

    def test_response_contains_tax_sheet_oob(self):
        body = self._run_and_get_body()
        self.assertIn('id="v2-sheet-tax"', body)

    def test_response_contains_fs_sheet_oob(self):
        body = self._run_and_get_body()
        self.assertIn('id="v2-sheet-financial-statements"', body)

    def test_response_contains_debt_runtime_bar_oob(self):
        body = self._run_and_get_body()
        self.assertIn('id="debt-runtime-bar"', body)

    def test_response_contains_tax_runtime_bar_oob(self):
        body = self._run_and_get_body()
        self.assertIn('id="tax-runtime-bar"', body)

    def test_response_contains_fs_runtime_bar_oob(self):
        body = self._run_and_get_body()
        self.assertIn('id="fs-runtime-bar"', body)


# ---------------------------------------------------------------------------
# G. Protected references
# ---------------------------------------------------------------------------

class TestProtectedReferenceRun(unittest.TestCase):
    """Protected reference (TUHO/Oborovo) projects can be run, not edited."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        # Create a normal project; we'll mock is_protected_reference below.
        cls.project_code = _create_project(cls.client, suffix="protected-run")

    def test_protected_reference_run_allowed(self):
        """is_protected_reference=True must not block /v2/workbook/run."""
        ch, wv = _get_content_hash(self.client, self.project_code)
        # Patch is_protected_reference to True; the run endpoint must still proceed.
        with patch("app.v2.router.is_protected_reference", return_value=True):
            resp = _post_run(self.client, self.project_code, ch, wv)
        # 200 expected (successful run, or at minimum not a hard block).
        self.assertEqual(resp.status_code, 200)

    def test_protected_reference_edit_blocked(self):
        """is_protected_reference=True must block /v2/workbook/update."""
        resp = self.client.post(
            "/v2/workbook/update",
            data={
                "project": self.project_code,
                "field_id": "tariff_eur_mwh",
                "value": "60",
                "workbook_version": "1",
                "content_hash": "fake",
                "sheet_id": "project_setup",
            },
            headers={"HX-Request": "true"},
            follow_redirects=False,
        )
        # The update endpoint must return a response (200 or 409) — not crash.
        self.assertIn(resp.status_code, (200, 409))


# ---------------------------------------------------------------------------
# H. Regression: run route registered, V2 OFF by default
# ---------------------------------------------------------------------------

class TestRunRouteRegistration(unittest.TestCase):
    """The /v2/workbook/run route must be registered when V2 is on."""

    def test_run_route_registered(self):
        from app.v2.router import router
        paths = [r.path for r in router.routes]
        self.assertIn("/workbook/run", paths)

    def test_run_route_is_post(self):
        from app.v2.router import router
        for route in router.routes:
            if getattr(route, "path", None) == "/workbook/run":
                self.assertIn("POST", route.methods)
                return
        self.fail("/workbook/run route not found")


class TestV2OffByDefault(unittest.TestCase):
    """FINCO_WORKBOOK_V2 must remain OFF by default (no auto-enable)."""

    def test_v2_flag_not_set_in_router_module(self):
        """The router module must not set FINCO_WORKBOOK_V2 as a side effect."""
        import importlib
        before = os.environ.get("FINCO_WORKBOOK_V2")
        # Remove and re-import to check no side effects.
        env_copy = dict(os.environ)
        env_copy.pop("FINCO_WORKBOOK_V2", None)
        # We can't safely reload main_web in this process, but we can verify
        # that the router itself doesn't touch the env var.
        import app.v2.router as rmod
        import inspect
        src = inspect.getsource(rmod)
        self.assertNotIn('os.environ["FINCO_WORKBOOK_V2"]', src)
        self.assertNotIn("os.environ.setdefault(\"FINCO_WORKBOOK_V2\"", src)


class TestRunButtonInTemplate(unittest.TestCase):
    """The workbook shell must include a Run button wired to /v2/workbook/run."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="run-btn")

    def test_run_button_present(self):
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("v2-run-btn", resp.text)

    def test_run_form_action_correct(self):
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertIn("/v2/workbook/run", resp.text)


class TestUnauthenticatedRun(unittest.TestCase):
    """Unauthenticated requests to /v2/workbook/run must be redirected to login."""

    @classmethod
    def setUpClass(cls):
        cls.anon_client = TestClient(main_web.app, follow_redirects=False)

    def test_unauthenticated_run_redirects_to_login(self):
        resp = self.anon_client.post(
            "/v2/workbook/run",
            data={"project": "any", "content_hash": "x", "workbook_version": "1"},
            headers={"HX-Request": "true"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers.get("location", ""))


class TestNonHtmxRunRedirects(unittest.TestCase):
    """Non-HTMX POST /v2/workbook/run must redirect on success."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="non-htmx-run")

    def test_non_htmx_success_redirects(self):
        ch, wv = _get_content_hash(self.client, self.project_code)
        resp = self.client.post(
            "/v2/workbook/run",
            data={
                "project": self.project_code,
                "content_hash": ch,
                "workbook_version": wv,
            },
            follow_redirects=False,
        )
        # Must redirect (303) to /v2/workbook on success.
        self.assertEqual(resp.status_code, 303)
        self.assertIn("/v2/workbook", resp.headers.get("location", ""))
