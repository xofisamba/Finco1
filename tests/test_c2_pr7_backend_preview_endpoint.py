"""C2-PR7: Backend Preview Endpoint Contract Stub — route-level tests.

Covers the 9 required-behaviour points from the C2-PR7 task spec:

  1. Valid payload accepted.
  2. Invalid payload rejected safely (never a 500/unhandled exception).
  3. Response is deterministic across repeated calls.
  4. No financial engine call.
  5. No persistence mutation.
  6. No Run-endpoint behaviour (response shape clearly distinct).
  7. affectedGroups/dirtyCells preserved/sorted correctly in response.
  8. Unknown group handled safely, no throw.
  9. No side effects across N repeated calls.

Uses fastapi.testclient.TestClient against the real `main_web.app`,
mirroring tests/test_auth_lite.py's auth-cookie pattern.
"""
import os

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from main_web import app
from app.auth import create_session_token, COOKIE_NAME
from app.persistence.db import DB_PATH

client = TestClient(app)


def _auth_cookies():
    token = create_session_token()
    return {COOKIE_NAME: token}


def _valid_payload(**overrides):
    payload = {
        "valid": True,
        "dirtyCells": ["capex!C.01.amount", "capex!a.amount"],
        "affectedGroups": ["senior-debt", "overview-kpis"],
        "projectDirty": True,
        "reason": "manual-flush",
        "executionStatus": "stubbed",
        # C2-PR9: project is null by default in this contract-stub test
        # file. "demo-project" was never a real project the test user
        # owns (this file predates C2-PR9's project-authorization
        # check) — null preserves this file's original "no project
        # scoping" intent and exercises the unchanged null-project path
        # C2-PR9 explicitly guarantees a no-regression contract for.
        # Authorization itself is covered by
        # tests/test_c2_pr9_runtime_request_hardening.py.
        "project": None,
    }
    payload.update(overrides)
    return payload


class TestAuth:
    def test_unauthenticated_request_rejected(self):
        resp = client.post("/model/preview", json=_valid_payload())
        assert resp.status_code == 401
        body = resp.json()
        assert body["status"] == "unauthenticated"


class TestValidPayloadAccepted:
    def test_valid_payload_accepted(self):
        """Point 1."""
        resp = client.post(
            "/model/preview", json=_valid_payload(), cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["status"] == "stubbed"
        assert body["executed"] is False
        assert body["accepted"] is True
        assert body["warnings"] == []
        assert "message" in body


class TestInvalidPayloadRejectedSafely:
    """Point 2."""

    def test_missing_fields_rejected(self):
        resp = client.post(
            "/model/preview", json={"valid": True}, cookies=_auth_cookies(),
        )
        assert resp.status_code == 200  # never a 500
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"
        assert body["accepted"] is False
        assert body["executed"] is False
        assert isinstance(body["warnings"], list) and body["warnings"]

    def test_malformed_types_rejected(self):
        bad = _valid_payload(dirtyCells="not-an-array", projectDirty="yes")
        resp = client.post("/model/preview", json=bad, cookies=_auth_cookies())
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"

    def test_non_json_body_rejected_safely(self):
        resp = client.post(
            "/model/preview",
            data=b"not-json-at-all",
            headers={"Content-Type": "application/json"},
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"

    def test_non_object_json_body_rejected_safely(self):
        resp = client.post(
            "/model/preview", json=[1, 2, 3], cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"

    def test_empty_body_rejected_safely(self):
        resp = client.post(
            "/model/preview",
            data=b"",
            headers={"Content-Type": "application/json"},
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"


class TestDeterminism:
    def test_response_deterministic_across_repeated_calls(self):
        """Point 3."""
        payload = _valid_payload()
        responses = [
            client.post("/model/preview", json=payload, cookies=_auth_cookies()).json()
            for _ in range(5)
        ]
        assert all(r == responses[0] for r in responses)


class TestNoFinancialEngineCall:
    def test_no_financial_engine_call(self, monkeypatch):
        """Point 4. Verification approach: patch the financial engine's
        entrypoint (app.waterfall_core.run_project, used by the real
        /run route) to raise if called; the preview endpoint must never
        touch it. Also assert the response contains nothing resembling
        a computed KPI/output field.
        """
        import app.waterfall_core as waterfall_core

        def _boom(*args, **kwargs):
            raise AssertionError("financial engine must never be called by /model/preview")

        if hasattr(waterfall_core, "run_project"):
            monkeypatch.setattr(waterfall_core, "run_project", _boom)

        resp = client.post(
            "/model/preview", json=_valid_payload(), cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        # No computed financial fields anywhere in the response.
        forbidden_keys = {"kpis", "irr", "dscr", "npv", "cashflow", "run_id"}
        assert forbidden_keys.isdisjoint(body.keys())


class TestNoPersistenceMutation:
    def test_no_persistence_mutation(self):
        """Point 5. Verification approach: compare the sqlite DB
        file's mtime/size before and after hitting the endpoint
        repeatedly. The stub must never write to disk."""
        db_path = DB_PATH
        before_stat = os.stat(db_path) if os.path.exists(db_path) else None

        for _ in range(3):
            resp = client.post(
                "/model/preview", json=_valid_payload(), cookies=_auth_cookies(),
            )
            assert resp.status_code == 200

        after_stat = os.stat(db_path) if os.path.exists(db_path) else None

        if before_stat is None and after_stat is None:
            return  # DB file doesn't exist in this test env; nothing to compare.
        assert before_stat is not None and after_stat is not None
        assert before_stat.st_mtime == after_stat.st_mtime
        assert before_stat.st_size == after_stat.st_size


class TestDistinctFromRunEndpoint:
    def test_response_shape_distinct_from_run(self):
        """Point 6: the preview stub's response shape/side effects are
        clearly distinct from the real /run endpoint's behaviour (which
        renders an HTML template with rendered KPI markup, not a JSON
        no-op contract response)."""
        resp = client.post(
            "/model/preview", json=_valid_payload(), cookies=_auth_cookies(),
        )
        assert resp.headers["content-type"].startswith("application/json")
        body = resp.json()
        # The real /run route's outcome is an HTML template render
        # with KPI numbers baked into markup; this response is a flat
        # JSON contract-stub acknowledgement with `executed: False` —
        # never anything resembling rendered HTML or a run_id/output.
        assert body["executed"] is False
        assert "<html" not in resp.text.lower()


class TestEchoedFieldsSortedAndPreserved:
    def test_affected_groups_and_dirty_cells_sorted(self):
        """Point 7."""
        payload = _valid_payload(
            dirtyCells=["capex!b.amount", "capex!a.amount"],
            affectedGroups=["senior-debt", "overview-kpis"],
        )
        resp = client.post("/model/preview", json=payload, cookies=_auth_cookies())
        body = resp.json()
        assert body["dirtyCells"] == ["capex!a.amount", "capex!b.amount"]
        assert body["affectedGroups"] == ["overview-kpis", "senior-debt"]

    def test_does_not_invent_new_entries(self):
        payload = _valid_payload(dirtyCells=["capex!a.amount"], affectedGroups=["capex"])
        resp = client.post("/model/preview", json=payload, cookies=_auth_cookies())
        body = resp.json()
        assert body["dirtyCells"] == ["capex!a.amount"]
        assert body["affectedGroups"] == ["capex"]


class TestUnknownGroupHandledSafely:
    def test_unknown_group_in_affected_groups(self):
        """Point 8."""
        payload = _valid_payload(affectedGroups=["overview-kpis", "unknown"])
        resp = client.post("/model/preview", json=payload, cookies=_auth_cookies())
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "unknown" in body["affectedGroups"]


class TestNoSideEffectsAcrossRepeatedCalls:
    def test_no_cumulative_state_change(self):
        """Point 9: hitting the endpoint N times produces no cumulative
        state change (combines points 4/5/6 into one broader check)."""
        db_path = DB_PATH
        before_stat = os.stat(db_path) if os.path.exists(db_path) else None

        responses = []
        for _ in range(10):
            resp = client.post(
                "/model/preview", json=_valid_payload(), cookies=_auth_cookies(),
            )
            assert resp.status_code == 200
            responses.append(resp.json())

        after_stat = os.stat(db_path) if os.path.exists(db_path) else None

        assert all(r == responses[0] for r in responses)
        if before_stat is not None and after_stat is not None:
            assert before_stat.st_mtime == after_stat.st_mtime
            assert before_stat.st_size == after_stat.st_size
