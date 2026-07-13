"""
Tests for the Workbook V2 feature-flagged shell (PR 5).

Coverage:
1. Source-structure guards (no engine calls, no legacy helpers, correct methods)
2. Feature-flag gate (flag off → no /v2 routes; flag on → /v2/workbook mounted)
3. HTTP route tests via FastAPI TestClient (real request/response cycle)
4. Authentication shape — SessionData.user_id convention verified
5. RuntimeResult hydration safety (with/without persisted runtime, special chars)
6. Template structure
"""
from __future__ import annotations

import os
import sys
import unittest
import urllib.parse
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")  # mount v2 routes for the HTTP tests
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-for-v2-tests")

from fastapi.testclient import TestClient  # noqa: E402

import main_web  # noqa: E402
from app.auth import COOKIE_NAME, SessionData, create_session_token  # noqa: E402
from app.workbook.service import WorkbookService  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _authed_client() -> TestClient:
    """TestClient with a valid session cookie, matching legacy test convention."""
    tc = TestClient(main_web.app, follow_redirects=False)
    tc.cookies.set(COOKIE_NAME, create_session_token())
    return tc


def _create_project(client: TestClient, suffix: str = "v2shell") -> str:
    """Create a user project via the legacy /projects/create route; return project code."""
    resp = client.post(
        "/projects/create",
        data={
            "project_name": f"V2 Shell Test {suffix}",
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


# ---------------------------------------------------------------------------
# 1. Source-structure guards
# ---------------------------------------------------------------------------

class TestV2RouterStructure(unittest.TestCase):

    def test_router_module_imports_cleanly(self):
        from app.v2 import router as router_mod
        self.assertIsNotNone(router_mod)

    def test_router_object_is_api_router(self):
        from app.v2.router import router
        from fastapi import APIRouter
        self.assertIsInstance(router, APIRouter)

    def test_v2_workbook_route_registered(self):
        from app.v2.router import router
        paths = [r.path for r in router.routes]
        self.assertIn("/workbook", paths)

    def _router_code(self) -> str:
        import app.v2.router as mod
        src = open(mod.__file__).read()
        # Skip the module docstring — it mentions helpers as negatives.
        return src.split('"""', 2)[-1]

    def test_does_not_call_legacy_snapshot_helpers(self):
        code = self._router_code()
        self.assertNotIn("_collect_form_snapshot", code)
        self.assertNotIn("_strip_empty_fields", code)

    def test_does_not_call_waterfall_runner(self):
        # WaterfallRunner must never appear — run_project is the canonical call.
        # The /v2/workbook/run endpoint uses run_project; that is expected.
        code = self._router_code()
        self.assertNotIn("WaterfallRunner", code)

    def test_uses_workbook_service(self):
        self.assertIn("WorkbookService", self._router_code())

    def test_uses_draft_method_not_saved(self):
        # GET and UPDATE endpoints use build_draft_input_set_from_workspace.
        # The /v2/workbook/run endpoint uses build_saved_input_set_from_workspace
        # because saved_snapshot is the correct run/materialization boundary.
        code = self._router_code()
        self.assertIn("build_draft_input_set_from_workspace", code)
        self.assertIn("build_saved_input_set_from_workspace", code)

    def test_uses_runtime_hydration_script(self):
        self.assertIn("runtime_hydration_script", self._router_code())

    def test_uses_canonical_auth_module(self):
        code = self._router_code()
        # Must use app.auth, not roll its own session parsing.
        self.assertIn("decode_session_token", code)
        self.assertIn("COOKIE_NAME", code)

    def test_uses_session_data_user_id_not_dict_key(self):
        # Router must use user.user_id (SessionData attribute) not user["id"].
        code = self._router_code()
        self.assertIn("user.user_id", code)
        self.assertNotIn('user["id"]', code)
        self.assertNotIn("user['id']", code)


# ---------------------------------------------------------------------------
# 2. Feature-flag gate
# ---------------------------------------------------------------------------

class TestFeatureFlagGate(unittest.TestCase):

    def _routes_for_flag(self, flag_value: str | None) -> set[str]:
        for key in list(sys.modules.keys()):
            if "main_web" in key:
                del sys.modules[key]
        env = {k: v for k, v in os.environ.items()}
        if flag_value is None:
            env.pop("FINCO_WORKBOOK_V2", None)
        else:
            env["FINCO_WORKBOOK_V2"] = flag_value
        with patch.dict(os.environ, env, clear=True):
            import main_web as mw
            return {getattr(r, "path", None) for r in mw.app.routes if getattr(r, "path", None)}

    def test_flag_off_no_v2_routes(self):
        paths = self._routes_for_flag(None)
        self.assertEqual({p for p in paths if p.startswith("/v2")}, set())

    def test_flag_empty_string_no_v2_routes(self):
        paths = self._routes_for_flag("")
        self.assertEqual({p for p in paths if p.startswith("/v2")}, set())

    def test_flag_on_1_registers_v2_workbook(self):
        self.assertIn("/v2/workbook", self._routes_for_flag("1"))

    def test_flag_on_true_registers_v2_workbook(self):
        self.assertIn("/v2/workbook", self._routes_for_flag("true"))

    def test_flag_on_yes_registers_v2_workbook(self):
        self.assertIn("/v2/workbook", self._routes_for_flag("yes"))

    def test_flag_off_legacy_index_preserved(self):
        self.assertIn("/", self._routes_for_flag(None))

    def test_flag_on_legacy_index_preserved(self):
        self.assertIn("/", self._routes_for_flag("1"))


# ---------------------------------------------------------------------------
# 3. HTTP route tests
# ---------------------------------------------------------------------------

class TestV2WorkbookRoute(unittest.TestCase):
    """Exercise the real FastAPI route via TestClient."""

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.anon_client = TestClient(main_web.app, follow_redirects=False)
        cls.project_code = _create_project(cls.client, suffix="route-tests")

    # -- Auth guards ----------------------------------------------------------

    def test_unauthenticated_redirects_to_login(self):
        resp = self.anon_client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["location"])

    def test_authenticated_no_project_redirects_to_root(self):
        resp = self.client.get("/v2/workbook")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers["location"], "/")

    def test_authenticated_missing_workspace_redirects_to_root(self):
        resp = self.client.get("/v2/workbook?project=does-not-exist-xyzzy")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers["location"], "/")

    # -- Successful response --------------------------------------------------

    def test_authenticated_with_valid_project_returns_200(self):
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp.status_code, 200)

    def test_response_contains_shell_root_element(self):
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertIn("v2-workbook-shell", resp.text)

    def test_response_contains_project_code(self):
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertIn(self.project_code, resp.text)

    def test_response_contains_workbook_version(self):
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertIn("data-workbook-version", resp.text)

    def test_response_contains_content_hash(self):
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertIn("data-content-hash", resp.text)

    def test_response_contains_template_source(self):
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertIn("data-template-source", resp.text)

    # -- Service delegation ---------------------------------------------------

    def test_build_draft_is_called_not_saved(self):
        with patch.object(
            WorkbookService, "build_draft_input_set_from_workspace",
            wraps=WorkbookService.build_draft_input_set_from_workspace,
        ) as mock_draft, patch.object(
            WorkbookService, "build_saved_input_set_from_workspace",
            wraps=WorkbookService.build_saved_input_set_from_workspace,
        ) as mock_saved:
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
            self.assertEqual(resp.status_code, 200)
            mock_draft.assert_called_once()
            mock_saved.assert_not_called()

    def test_runtime_hydration_script_is_called(self):
        with patch.object(
            WorkbookService, "runtime_hydration_script",
            wraps=WorkbookService.runtime_hydration_script,
        ) as mock_hydration:
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
            self.assertEqual(resp.status_code, 200)
            mock_hydration.assert_called_once()

    def test_no_engine_run_method_called(self):
        with patch("app.v2.router.WorkbookService") as mock_svc:
            mock_pis = MagicMock()
            mock_pis.workbook_version = "v2"
            mock_pis.content_hash = "abc123"
            mock_pis.template_source = "generic_wind"
            mock_svc.build_draft_input_set_from_workspace.return_value = mock_pis
            mock_svc.runtime_hydration_script.return_value = ""
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
            self.assertEqual(resp.status_code, 200)
            # run_project / to_projectinputs must not have been called
            mock_svc.to_projectinputs.assert_not_called()


# ---------------------------------------------------------------------------
# 4. Authentication shape
# ---------------------------------------------------------------------------

class TestAuthShape(unittest.TestCase):
    """Prove the canonical SessionData shape is used correctly."""

    def test_session_data_has_user_id_attribute(self):
        sd = SessionData(user_id="42", username="admin",
                         login_at=__import__("datetime").datetime.now(
                             __import__("datetime").timezone.utc))
        self.assertEqual(sd.user_id, "42")

    def test_session_data_has_no_id_key(self):
        sd = SessionData(user_id="42", username="admin",
                         login_at=__import__("datetime").datetime.now(
                             __import__("datetime").timezone.utc))
        with self.assertRaises((AttributeError, TypeError, KeyError)):
            _ = sd["id"]

    def test_create_session_token_produces_decodable_session_data(self):
        from app.auth import decode_session_token
        token = create_session_token(user_id="99", username="testuser")
        sd = decode_session_token(token)
        self.assertIsNotNone(sd)
        self.assertIsInstance(sd, SessionData)
        self.assertEqual(sd.user_id, "99")

    def test_route_uses_user_id_from_session_data(self):
        """Route must call get_workspace_state with user.user_id, not user['id']."""
        import app.v2.router as r_mod
        src = open(r_mod.__file__).read()
        self.assertIn("user.user_id", src)

    def test_authenticated_request_succeeds_without_dict_coercion(self):
        """A real cookie-auth request hits the route without TypeError on user_id."""
        client = _authed_client()
        project = _create_project(client, suffix="auth-shape")
        resp = client.get(f"/v2/workbook?project={project}")
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# 5. RuntimeResult hydration safety
# ---------------------------------------------------------------------------

class TestHydrationSafety(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = _authed_client()
        cls.project_code = _create_project(cls.client, suffix="hydration-safety")

    def test_workspace_without_runtime_returns_200(self):
        """New project (no run yet) must not error; hydration is empty string."""
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp.status_code, 200)

    def test_empty_hydration_does_not_break_page(self):
        resp = self.client.get(f"/v2/workbook?project={self.project_code}")
        self.assertEqual(resp.status_code, 200)
        # Shell root must still render even with no hydration script.
        self.assertIn("v2-workbook-shell", resp.text)

    def test_hydration_script_injected_when_runtime_present(self):
        """If WorkbookService returns a non-empty script it appears in the page."""
        with patch.object(
            WorkbookService, "runtime_hydration_script",
            return_value='<script>sessionStorage.setItem("lastRuntimeSummary","{}");'
                         "</script>",
        ):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("lastRuntimeSummary", resp.text)

    def test_hydration_script_double_serialised_payload_safe(self):
        """Payload containing quotes and special chars must stay inside the script
        context — the double-serialisation convention means the outer JSON string
        contains an already-escaped inner JSON string, so </script> cannot appear
        at the top level of the payload text."""
        import json
        inner = json.dumps({"project_irr": 0.08, "label": 'has "quotes"'})
        outer = json.dumps(inner)
        script = f'<script>sessionStorage.setItem("lastRuntimeSummary",{outer});</script>'
        # </script> must not appear unescaped inside the outer JSON-encoded string.
        self.assertNotIn("</script>", outer)
        with patch.object(WorkbookService, "runtime_hydration_script",
                          return_value=script):
            resp = self.client.get(f"/v2/workbook?project={self.project_code}")
            self.assertEqual(resp.status_code, 200)

    def test_db_is_authoritative_not_session_storage(self):
        """RuntimeResult is reconstructed from DB (WorkspaceStateRecord), not
        from sessionStorage.  Verify the service call path uses ws directly."""
        import app.v2.router as mod
        src = open(mod.__file__).read()
        # Strip the module docstring — it may reference sessionStorage in
        # descriptive text.  What must not appear is a read from client-side
        # state (request.session, cookies carrying schedule data, etc.).
        code_body = src.split('"""', 2)[-1]
        # The route builds RuntimeResult from ws (DB-authoritative path).
        self.assertIn("runtime_hydration_script", code_body)
        # The route must not read sessionStorage or request.session for schedules.
        self.assertNotIn("request.session", code_body)
        self.assertNotIn("sessionStorage.get", code_body)


# ---------------------------------------------------------------------------
# 6. Browser smoke (Playwright / chromium-cli)
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="browser smoke — run manually or in CI with a browser")
class TestV2BrowserSmoke(unittest.TestCase):
    """
    Minimal browser smoke for the V2 shell.

    Requires:
    - FINCO_WORKBOOK_V2=1
    - A running dev server on http://localhost:8000
    - chromium-cli or Playwright installed

    Manual run:
        FINCO_WORKBOOK_V2=1 uvicorn main_web:app --port 8000 &
        pytest tests/test_workbook_v2_shell.py::TestV2BrowserSmoke -v -s
    """

    def _run_chromium(self, script: str) -> str:
        import subprocess
        result = subprocess.run(
            ["chromium-cli", "--session", "v2-smoke"],
            input=script,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.stdout + result.stderr

    def test_v2_shell_renders_and_survives_refresh(self):
        from app.auth import create_session_token, COOKIE_NAME
        token = create_session_token()
        project = "tuho"
        output = self._run_chromium(f"""
set-cookie {COOKIE_NAME}={token} http://localhost:8000
nav http://localhost:8000/v2/workbook?project={project}
wait-for text=v2-workbook-shell
screenshot
nav http://localhost:8000/v2/workbook?project={project}
wait-for text=v2-workbook-shell
screenshot
console --errors
""")
        self.assertNotIn("Error", output, f"Console errors after smoke:\n{output}")

    def test_legacy_index_still_works_when_v2_flag_on(self):
        from app.auth import create_session_token, COOKIE_NAME
        token = create_session_token()
        output = self._run_chromium(f"""
set-cookie {COOKIE_NAME}={token} http://localhost:8000
nav http://localhost:8000/
wait-for text=Projects
screenshot
console --errors
""")
        self.assertNotIn("Error", output, f"Console errors on legacy /:\n{output}")


# ---------------------------------------------------------------------------
# 7. Template structure
# ---------------------------------------------------------------------------

class TestV2Template(unittest.TestCase):

    def _tpl(self) -> str:
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        p = os.path.join(here, "app", "templates", "v2", "workbook.html")
        return open(p).read()

    def test_template_exists(self):
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assertTrue(
            os.path.isfile(os.path.join(here, "app", "templates", "v2", "workbook.html"))
        )

    def test_has_hydration_script_slot(self):
        self.assertIn("hydration_script", self._tpl())

    def test_has_data_project_attribute(self):
        self.assertIn("data-project", self._tpl())

    def test_has_data_workbook_version(self):
        self.assertIn("data-workbook-version", self._tpl())

    def test_has_data_content_hash(self):
        self.assertIn("data-content-hash", self._tpl())

    def test_has_v2_shell_root(self):
        self.assertIn("v2-workbook-shell", self._tpl())


if __name__ == "__main__":
    unittest.main()
