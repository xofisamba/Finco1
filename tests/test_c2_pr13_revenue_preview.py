"""C2-PR13: Revenue Total Preview — route-level backend tests.

Mirrors tests/test_c2_pr10_capex_total_preview.py exactly, for the new
additive `revenueTotalPreview` request field / `revenue` response field:

  - revenueTotalPreview is validated defensively (finite number or null).
  - A valid numeric revenueTotalPreview is echoed back under a new,
    additive "revenue" response field, rounded to 2dp, with currency
    metadata, shaped `{"preview": <number>, "currency": "EUR"}`.
  - revenueTotalPreview omitted/null -> no "revenue" key at all in the
    response (never fabricated as 0.0).
  - No financial engine call, no persistence mutation.
  - Authorization (project ownership) regression: still enforced
    exactly as before, unaffected by this PR's additive field.
  - The pre-existing "capex" field/behaviour is completely unaffected
    by this PR (regression).

Uses fastapi.testclient.TestClient against the real `main_web.app`,
mirroring tests/test_c2_pr10_capex_total_preview.py's pattern.
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
        "dirtyCells": ["revenue!ppa_tariff_eur_mwh", "revenue!a.amount"],
        "affectedGroups": ["overview-kpis"],
        "projectDirty": True,
        "reason": "manual-flush",
        "executionStatus": "stubbed",
        "project": None,
    }
    payload.update(overrides)
    return payload


class TestRevenueTotalPreviewAccepted:
    def test_valid_numeric_revenue_total_echoed_back(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(revenueTotalPreview=98765.432),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "revenue" in body
        assert body["revenue"]["preview"] == 98765.43
        assert body["revenue"]["currency"] == "EUR"

    def test_zero_revenue_total_is_still_rendered_not_omitted(self):
        """A real zero sum (e.g. all Revenue cells emptied) must still
        produce a 'revenue' field — only an absent/None value omits it."""
        resp = client.post(
            "/model/preview",
            json=_valid_payload(revenueTotalPreview=0.0),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "revenue" in body
        assert body["revenue"]["preview"] == 0.0

    def test_negative_revenue_total_accepted(self):
        """Defensive: the route never second-guesses the client's sum
        (e.g. rejecting negative numbers) — it only checks finiteness."""
        resp = client.post(
            "/model/preview",
            json=_valid_payload(revenueTotalPreview=-5.5),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "revenue" in body
        assert body["revenue"]["preview"] == -5.5


class TestRevenueTotalPreviewOmittedOrNull:
    def test_missing_revenue_total_preview_field_omits_revenue_key(self):
        resp = client.post(
            "/model/preview", json=_valid_payload(), cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "revenue" not in body

    def test_null_revenue_total_preview_omits_revenue_key(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(revenueTotalPreview=None),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "revenue" not in body


class TestRevenueTotalPreviewRejectedSafely:
    def test_string_revenue_total_preview_rejected(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(revenueTotalPreview="not-a-number"),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200  # never a 500
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"
        assert any("revenueTotalPreview" in w for w in body["warnings"])

    def test_boolean_revenue_total_preview_rejected(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(revenueTotalPreview=True),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"

    def test_empty_body_never_500(self):
        resp = client.post(
            "/model/preview",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200


class TestNoFinancialEngineCallOrPersistenceMutation:
    """Mirrors test_c2_pr10_capex_total_preview.py's verification
    approach: this PR's additive revenueTotalPreview handling must not
    introduce any financial-engine call or persistence write."""

    def test_no_financial_engine_call(self, monkeypatch):
        import app.waterfall_core as waterfall_core

        def _boom(*args, **kwargs):
            raise AssertionError("waterfall_core.run_project must never be called by /model/preview")

        monkeypatch.setattr(waterfall_core, "run_project", _boom, raising=False)

        resp = client.post(
            "/model/preview",
            json=_valid_payload(revenueTotalPreview=999.99),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "revenue" in body

    def test_no_persistence_mutation(self):
        before_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else None
        before_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else None

        client.post(
            "/model/preview",
            json=_valid_payload(revenueTotalPreview=42.0),
            cookies=_auth_cookies(),
        )

        after_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else None
        after_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else None
        assert before_mtime == after_mtime
        assert before_size == after_size


class TestAuthorizationRegressionUnaffected:
    def test_null_project_unaffected(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=None, revenueTotalPreview=10.0),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is True
        assert "revenue" in body

    def test_bogus_project_forbidden(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project="totally-bogus-project-code", revenueTotalPreview=10.0),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "forbidden-project"
        assert "revenue" not in body

    def test_unauthenticated_rejected(self):
        resp = client.post(
            "/model/preview", json=_valid_payload(revenueTotalPreview=10.0),
        )
        assert resp.status_code == 401


class TestCapexPreviewRegressionUnaffected:
    """Both previews must coexist independently — sending both fields
    in the same request must echo both response fields, neither
    blocking the other."""

    def test_both_capex_and_revenue_preview_present_together(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview=111.11, revenueTotalPreview=222.22),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is True
        assert body["capex"]["capex_total_preview"] == 111.11
        assert body["revenue"]["preview"] == 222.22

    def test_capex_only_omits_revenue(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview=111.11),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "capex" in body
        assert "revenue" not in body

    def test_revenue_only_omits_capex(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(revenueTotalPreview=222.22),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "revenue" in body
        assert "capex" not in body
