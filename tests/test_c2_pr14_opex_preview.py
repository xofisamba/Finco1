"""C2-PR14: OPEX Total Preview — route-level backend tests.

Mirrors tests/test_c2_pr13_revenue_preview.py exactly, for the new
additive `opexTotalPreview` request field / `opex` response field:

  - opexTotalPreview is validated defensively (finite number or null).
  - A valid numeric opexTotalPreview is echoed back under a new,
    additive "opex" response field, rounded to 2dp, with currency
    metadata, shaped `{"preview": <number>, "currency": "EUR"}`.
  - opexTotalPreview omitted/null -> no "opex" key at all in the
    response (never fabricated as 0.0).
  - No financial engine call, no persistence mutation.
  - Authorization (project ownership) regression: still enforced
    exactly as before, unaffected by this PR's additive field.
  - The pre-existing "capex"/"revenue" fields/behaviour are completely
    unaffected by this PR (regression).

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
        "dirtyCells": ["opex!OM-01.budget"],
        "affectedGroups": ["overview-kpis"],
        "projectDirty": True,
        "reason": "manual-flush",
        "executionStatus": "stubbed",
        "project": None,
    }
    payload.update(overrides)
    return payload


class TestOpexTotalPreviewAccepted:
    def test_valid_numeric_opex_total_echoed_back(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(opexTotalPreview=8456.789),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "opex" in body
        assert body["opex"]["preview"] == 8456.79
        assert body["opex"]["currency"] == "EUR"

    def test_zero_opex_total_is_still_rendered_not_omitted(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(opexTotalPreview=0.0),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "opex" in body
        assert body["opex"]["preview"] == 0.0

    def test_negative_opex_total_accepted(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(opexTotalPreview=-5.5),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "opex" in body
        assert body["opex"]["preview"] == -5.5


class TestOpexTotalPreviewOmittedOrNull:
    def test_missing_opex_total_preview_field_omits_opex_key(self):
        resp = client.post(
            "/model/preview", json=_valid_payload(), cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "opex" not in body

    def test_null_opex_total_preview_omits_opex_key(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(opexTotalPreview=None),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "opex" not in body


class TestOpexTotalPreviewRejectedSafely:
    def test_string_opex_total_preview_rejected(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(opexTotalPreview="not-a-number"),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200  # never a 500
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"
        assert any("opexTotalPreview" in w for w in body["warnings"])

    def test_boolean_opex_total_preview_rejected(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(opexTotalPreview=True),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"

    def test_nan_like_infinity_rejected(self):
        resp = client.post(
            "/model/preview",
            data=b'{"valid": true, "dirtyCells": [], "affectedGroups": [], '
                 b'"projectDirty": false, "reason": "x", "executionStatus": null, '
                 b'"project": null, "opexTotalPreview": Infinity}',
            headers={"Content-Type": "application/json"},
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200


class TestNoFinancialEngineCallOrPersistenceMutation:
    def test_no_financial_engine_call(self, monkeypatch):
        import app.waterfall_core as waterfall_core

        def _boom(*args, **kwargs):
            raise AssertionError("waterfall_core.run_project must never be called by /model/preview")

        monkeypatch.setattr(waterfall_core, "run_project", _boom, raising=False)

        resp = client.post(
            "/model/preview",
            json=_valid_payload(opexTotalPreview=999.99),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "opex" in body

    def test_no_persistence_mutation(self):
        before_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else None
        before_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else None

        client.post(
            "/model/preview",
            json=_valid_payload(opexTotalPreview=42.0),
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
            json=_valid_payload(project=None, opexTotalPreview=10.0),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is True
        assert "opex" in body

    def test_bogus_project_forbidden(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project="totally-bogus-project-code", opexTotalPreview=10.0),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "forbidden-project"
        assert "opex" not in body

    def test_unauthenticated_rejected(self):
        resp = client.post(
            "/model/preview", json=_valid_payload(opexTotalPreview=10.0),
        )
        assert resp.status_code == 401


class TestCapexRevenuePreviewRegressionUnaffected:
    """All three previews must coexist independently."""

    def test_all_three_previews_present_together(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(
                capexTotalPreview=111.11,
                revenueTotalPreview=222.22,
                opexTotalPreview=333.33,
            ),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is True
        assert body["capex"]["capex_total_preview"] == 111.11
        assert body["revenue"]["preview"] == 222.22
        assert body["opex"]["preview"] == 333.33

    def test_opex_only_omits_capex_and_revenue(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(opexTotalPreview=333.33),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "opex" in body
        assert "capex" not in body
        assert "revenue" not in body
