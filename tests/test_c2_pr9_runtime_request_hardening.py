"""C2-PR9: Runtime Request Hardening — backend authorization tests.

This PR adds project authorization to POST /model/preview, on top of
the C2-PR7 contract stub (tests/test_c2_pr7_backend_preview_endpoint.py)
and the C2-PR8 first-runtime-slice wiring. It implements NO new
financial calculation, persistence, or export logic — only:

  1. Project authorization (a non-null `project` field in the payload
     must belong to the authenticated user).
  2. Safe JSON (never a 500/traceback) on auth failure.
  3. No regression to the existing contract-stub behaviour for
     authorized/null-project requests.

Covers backend points 8-13 from the C2-PR9 task spec:

  8.  A user cannot preview another user's project.
  9.  Safe JSON is returned on auth failure (no 500, no traceback).
  10. No persistence occurs (DB untouched) on either success or
      auth-failure path.
  11. No financial engine call occurs.
  12. No export logic is invoked.
  13. Existing preview endpoint behaviour is unchanged for
      authorized/null-project requests (no regression vs PR8 contract).

Uses fastapi.testclient.TestClient against the real `main_web.app`,
mirroring tests/test_c2_pr7_backend_preview_endpoint.py's pattern.
"""
import os

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid

from fastapi.testclient import TestClient

from main_web import app
from app.auth import create_session_token, COOKIE_NAME
from app.persistence.db import DB_PATH
from app.persistence.repository import save_project

client = TestClient(app)


def _auth_cookies(user_id="1"):
    token = create_session_token(user_id=user_id)
    return {COOKIE_NAME: token}


def _valid_payload(**overrides):
    payload = {
        "valid": True,
        "dirtyCells": ["capex!C.01.amount", "capex!a.amount"],
        "affectedGroups": ["senior-debt", "overview-kpis"],
        "projectDirty": True,
        "reason": "manual-flush",
        "executionStatus": "stubbed",
        "project": None,
    }
    payload.update(overrides)
    return payload


def _make_owned_project(user_id):
    """Create a real, persisted project owned by `user_id`. Returns its
    project_code. This is a genuine call into the existing project
    persistence layer (not a mock), so the authorization check under
    test exercises the real `get_project_by_code` lookup."""
    project_code = f"c2pr9-{uuid.uuid4().hex[:10]}"
    save_project(
        user_id=user_id,
        project_code=project_code,
        project_name="C2-PR9 Runtime Hardening Test Project",
        source_project_template="generic_solar",
        project_type="Solar",
        project_origin="factory_template",
        template_source="generic_solar",
    )
    return project_code


class TestCrossUserProjectDenied:
    def test_user_cannot_preview_another_users_project(self):
        """Point 8: a user cannot preview another user's project — they
        get the forbidden-project response, never the other user's
        project data."""
        owner_id = f"owner-{uuid.uuid4().hex[:8]}"
        other_user_id = f"other-{uuid.uuid4().hex[:8]}"
        project_code = _make_owned_project(owner_id)

        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(user_id=other_user_id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "forbidden-project"
        assert body["accepted"] is False
        assert body["executed"] is False
        assert body["warnings"] == ["Project access denied."]
        # No project data of any kind leaked.
        assert "affectedGroups" not in body
        assert "dirtyCells" not in body
        assert "overview" not in body

    def test_nonexistent_project_also_denied(self):
        """A project_code that doesn't exist at all gets the same
        forbidden-project response as one owned by someone else — the
        endpoint never distinguishes "doesn't exist" from "not yours"."""
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project="this-project-does-not-exist"),
            cookies=_auth_cookies(user_id=user_id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "forbidden-project"

    def test_owner_can_preview_own_project(self):
        """Sanity check: the same user who owns the project IS allowed
        to preview it — the auth check is scoped correctly, not a blanket
        deny."""
        owner_id = f"owner-{uuid.uuid4().hex[:8]}"
        project_code = _make_owned_project(owner_id)

        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(user_id=owner_id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["status"] == "stubbed"


class TestSafeJsonOnAuthFailure:
    def test_safe_json_no_500_no_traceback(self):
        """Point 9: auth failure returns safe JSON, never a 500, never
        a traceback leaked in the body."""
        owner_id = f"owner-{uuid.uuid4().hex[:8]}"
        other_user_id = f"other-{uuid.uuid4().hex[:8]}"
        project_code = _make_owned_project(owner_id)

        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(user_id=other_user_id),
        )
        assert resp.status_code != 500
        assert resp.headers["content-type"].startswith("application/json")
        body = resp.json()
        text = resp.text.lower()
        assert "traceback" not in text
        assert "exception" not in text
        assert isinstance(body, dict)


class TestNoPersistenceOnEitherPath:
    def test_no_persistence_on_success_path(self):
        """Point 10 (success path): DB untouched by an authorized
        preview call."""
        owner_id = f"owner-{uuid.uuid4().hex[:8]}"
        project_code = _make_owned_project(owner_id)

        db_path = DB_PATH
        before_stat = os.stat(db_path) if os.path.exists(db_path) else None

        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(user_id=owner_id),
        )
        assert resp.status_code == 200

        after_stat = os.stat(db_path) if os.path.exists(db_path) else None
        if before_stat is not None and after_stat is not None:
            assert before_stat.st_mtime == after_stat.st_mtime
            assert before_stat.st_size == after_stat.st_size

    def test_no_persistence_on_auth_failure_path(self):
        """Point 10 (auth-failure path): DB untouched by a
        forbidden-project preview call."""
        owner_id = f"owner-{uuid.uuid4().hex[:8]}"
        other_user_id = f"other-{uuid.uuid4().hex[:8]}"
        project_code = _make_owned_project(owner_id)

        db_path = DB_PATH
        before_stat = os.stat(db_path) if os.path.exists(db_path) else None

        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(user_id=other_user_id),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "forbidden-project"

        after_stat = os.stat(db_path) if os.path.exists(db_path) else None
        if before_stat is not None and after_stat is not None:
            assert before_stat.st_mtime == after_stat.st_mtime
            assert before_stat.st_size == after_stat.st_size


class TestNoFinancialEngineCall:
    def test_no_financial_engine_call_on_success_path(self, monkeypatch):
        """Point 11 (success path)."""
        import app.waterfall_core as waterfall_core

        def _boom(*args, **kwargs):
            raise AssertionError("financial engine must never be called by /model/preview")

        if hasattr(waterfall_core, "run_project"):
            monkeypatch.setattr(waterfall_core, "run_project", _boom)

        owner_id = f"owner-{uuid.uuid4().hex[:8]}"
        project_code = _make_owned_project(owner_id)
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(user_id=owner_id),
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_no_financial_engine_call_on_auth_failure_path(self, monkeypatch):
        """Point 11 (auth-failure path)."""
        import app.waterfall_core as waterfall_core

        def _boom(*args, **kwargs):
            raise AssertionError("financial engine must never be called by /model/preview")

        if hasattr(waterfall_core, "run_project"):
            monkeypatch.setattr(waterfall_core, "run_project", _boom)

        owner_id = f"owner-{uuid.uuid4().hex[:8]}"
        other_user_id = f"other-{uuid.uuid4().hex[:8]}"
        project_code = _make_owned_project(owner_id)
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(user_id=other_user_id),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "forbidden-project"


class TestNoExportLogicInvoked:
    def test_no_export_logic_invoked(self, monkeypatch):
        """Point 12: no export-generation function is called by either
        path of this endpoint."""
        import app.excel_export as excel_export

        def _boom(*args, **kwargs):
            raise AssertionError("export logic must never be called by /model/preview")

        if hasattr(excel_export, "build_excel_export"):
            monkeypatch.setattr(excel_export, "build_excel_export", _boom)

        owner_id = f"owner-{uuid.uuid4().hex[:8]}"
        other_user_id = f"other-{uuid.uuid4().hex[:8]}"
        project_code = _make_owned_project(owner_id)

        resp_ok = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(user_id=owner_id),
        )
        assert resp_ok.status_code == 200

        resp_forbidden = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(user_id=other_user_id),
        )
        assert resp_forbidden.status_code == 200
        assert resp_forbidden.json()["status"] == "forbidden-project"


class TestNoRegressionForAuthorizedOrNullProject:
    def test_null_project_behaviour_unchanged(self):
        """Point 13 (null-project path): identical to the pre-PR9
        contract — `project: None` is never authorization-checked."""
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=None),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["status"] == "stubbed"
        assert body["executed"] is False
        assert body["accepted"] is True
        assert body["warnings"] == []
        assert body["overview"]["runtime_status"] == "Preview executed"
        assert body["overview"]["updated"] is True

    def test_authorized_project_behaviour_matches_pr8_contract(self):
        """Point 13 (authorized-project path): response shape for an
        authorized request is byte-for-byte identical to the documented
        C2-PR8 contract — PR9 adds zero new fields to the success
        response.

        C2-PR24 NOTE: a "debt" field is now unconditionally present in
        every valid-payload response (the first backend-computed
        preview field — see docs/C2_PR24_BACKEND_DEBT_PREVIEW_STUB.md).
        That is a deliberate, later, additive change unrelated to PR9's
        own claim (which is specifically that *PR9's authorization
        work* added no new fields), so it is popped before the
        exact-equality check below rather than re-asserting stale
        pre-PR24 behaviour.
        """
        owner_id = f"owner-{uuid.uuid4().hex[:8]}"
        project_code = _make_owned_project(owner_id)

        payload = _valid_payload(
            project=project_code,
            dirtyCells=["capex!b.amount", "capex!a.amount"],
            affectedGroups=["senior-debt", "overview-kpis"],
        )
        resp = client.post(
            "/model/preview", json=payload, cookies=_auth_cookies(user_id=owner_id),
        )
        assert resp.status_code == 200
        body = resp.json()
        body.pop("debt", None)
        assert body == {
            "ok": True,
            "status": "stubbed",
            "executed": False,
            "accepted": True,
            "affectedGroups": ["overview-kpis", "senior-debt"],
            "dirtyCells": ["capex!a.amount", "capex!b.amount"],
            "warnings": [],
            "message": "Preview endpoint contract accepted payload; recalculation is not implemented yet.",
            "overview": {
                "runtime_status": "Preview executed",
                "updated": True,
            },
        }

    def test_invalid_payload_path_unaffected_by_authorization(self):
        """An invalid payload is rejected on shape grounds before
        authorization is ever consulted — unchanged from PR7/PR8."""
        resp = client.post(
            "/model/preview", json={"valid": True}, cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"

    def test_unauthenticated_request_still_401(self):
        """Auth-gating (pre-existing, C2-PR7) is unchanged by this PR."""
        resp = client.post("/model/preview", json=_valid_payload())
        assert resp.status_code == 401
