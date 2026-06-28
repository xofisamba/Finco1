"""C2-PR10: CAPEX Total Preview — route-level backend tests.

Covers the backend/server-side portion of the C2-PR10 task spec:

  - capexTotalPreview is validated defensively (finite number or null).
  - A valid numeric capexTotalPreview is echoed back under a new,
    additive "capex" response field, rounded to 2dp, with currency
    metadata.
  - capexTotalPreview omitted/null -> no "capex" key at all in the
    response (never fabricated as 0.0).
  - No financial engine call, no persistence mutation (reusing the
    exact verification pattern tests/test_c2_pr7_backend_preview_endpoint.py
    already established).
  - Authorization (project ownership) regression: still enforced
    exactly as C2-PR9 left it, unaffected by this PR's additive field.

Uses fastapi.testclient.TestClient against the real `main_web.app`,
mirroring tests/test_c2_pr7_backend_preview_endpoint.py's pattern.
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
        "project": None,
    }
    payload.update(overrides)
    return payload


class TestCapexTotalPreviewAccepted:
    def test_valid_numeric_capex_total_echoed_back(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview=12345.678),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "capex" in body
        assert body["capex"]["capex_total_preview"] == 12345.68
        assert body["capex"]["currency"] == "EUR"

    def test_zero_capex_total_is_still_rendered_not_omitted(self):
        """A real zero sum (e.g. all CAPEX cells emptied) must still
        produce a 'capex' field — only an absent/None value omits it."""
        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview=0.0),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "capex" in body
        assert body["capex"]["capex_total_preview"] == 0.0

    def test_negative_capex_total_accepted(self):
        """Defensive: the route never second-guesses the client's sum
        (e.g. rejecting negative numbers) — it only checks finiteness."""
        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview=-5.5),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "capex" in body
        assert body["capex"]["capex_total_preview"] == -5.5


class TestCapexTotalPreviewOmittedOrNull:
    def test_missing_capex_total_preview_field_omits_capex_key(self):
        resp = client.post(
            "/model/preview", json=_valid_payload(), cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "capex" not in body

    def test_null_capex_total_preview_omits_capex_key(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview=None),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "capex" not in body


class TestCapexTotalPreviewRejectedSafely:
    def test_string_capex_total_preview_rejected(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview="not-a-number"),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200  # never a 500
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"
        assert any("capexTotalPreview" in w for w in body["warnings"])

    def test_boolean_capex_total_preview_rejected(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview=True),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"

    def test_nan_like_inputs_never_500(self):
        """JSON itself can't carry NaN/Infinity, but a defensive route
        must never 500 even if a non-standard client sends a malformed
        body — covered generally by the existing non-JSON-body test in
        test_c2_pr7_backend_preview_endpoint.py; this re-confirms the
        capexTotalPreview branch specifically doesn't introduce a crash
        path for an empty body."""
        resp = client.post(
            "/model/preview",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200


class TestNoFinancialEngineCallOrPersistenceMutation:
    """Mirrors test_c2_pr7_backend_preview_endpoint.py's verification
    approach: this PR's additive capexTotalPreview handling must not
    introduce any financial-engine call or persistence write."""

    def test_no_financial_engine_call(self, monkeypatch):
        import app.waterfall_core as waterfall_core

        def _boom(*args, **kwargs):
            raise AssertionError("waterfall_core.run_project must never be called by /model/preview")

        monkeypatch.setattr(waterfall_core, "run_project", _boom, raising=False)

        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview=999.99),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "capex" in body

    def test_no_persistence_mutation(self):
        before_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else None
        before_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else None

        client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview=42.0),
            cookies=_auth_cookies(),
        )

        after_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else None
        after_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else None
        assert before_mtime == after_mtime
        assert before_size == after_size


class TestAuthorizationRegressionUnaffected:
    """Point 8 of the task spec: the C2-PR9 authorization checks must
    remain green, unweakened, with this PR's additive field present."""

    def test_null_project_unaffected(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=None, capexTotalPreview=10.0),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is True
        assert "capex" in body

    def test_bogus_project_forbidden(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project="totally-bogus-project-code", capexTotalPreview=10.0),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "forbidden-project"
        assert "capex" not in body

    def test_unauthenticated_rejected(self):
        resp = client.post(
            "/model/preview", json=_valid_payload(capexTotalPreview=10.0),
        )
        assert resp.status_code == 401
