"""C2-PR15: EBITDA Preview — route-level backend tests.

Covers the new additive `ebitdaPreview` request field / `ebitda`
response field. EBITDA itself is computed CLIENT-SIDE (pure arithmetic
on revenue/opex previews already computed client-side); the server's
job here is purely validate-and-echo, exactly like capex/revenue/opex.
These tests therefore verify the ROUTE's validate-and-echo behaviour,
plus (in TestEbitdaArithmeticReference) a reference check that the
arithmetic a correct client WOULD have produced is what gets echoed.

Uses fastapi.testclient.TestClient against the real `main_web.app`,
mirroring tests/test_c2_pr13_revenue_preview.py's pattern.
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
        "dirtyCells": ["revenue!a.amount", "opex!OM-01.budget"],
        "affectedGroups": ["overview-kpis"],
        "projectDirty": True,
        "reason": "manual-flush",
        "executionStatus": "stubbed",
        "project": None,
    }
    payload.update(overrides)
    return payload


class TestEbitdaPreviewAccepted:
    def test_valid_numeric_ebitda_echoed_back(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(ebitdaPreview=3889.674),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "ebitda" in body
        assert body["ebitda"]["preview"] == 3889.67
        assert body["ebitda"]["currency"] == "EUR"

    def test_zero_ebitda_is_still_rendered_not_omitted(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(ebitdaPreview=0.0),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "ebitda" in body
        assert body["ebitda"]["preview"] == 0.0

    def test_negative_ebitda_accepted(self):
        """Defensive: a real negative EBITDA (opex > revenue) is a
        legitimate value, never rejected/clamped by the route."""
        resp = client.post(
            "/model/preview",
            json=_valid_payload(ebitdaPreview=-1234.56),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "ebitda" in body
        assert body["ebitda"]["preview"] == -1234.56


class TestEbitdaArithmeticReference:
    """Reference check: revenue_preview - opex_preview, rounded to 2dp,
    is the value a correct client computes and the route is expected to
    echo verbatim under "ebitda" (the route never recomputes this
    itself — it only validates and echoes the client-supplied number)."""

    def test_revenue_minus_opex_round_trips_correctly(self):
        revenue_preview = 12345.67
        opex_preview = 8456.00
        expected_ebitda = round(revenue_preview - opex_preview, 2)

        resp = client.post(
            "/model/preview",
            json=_valid_payload(
                revenueTotalPreview=revenue_preview,
                opexTotalPreview=opex_preview,
                ebitdaPreview=expected_ebitda,
            ),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["revenue"]["preview"] == revenue_preview
        assert body["opex"]["preview"] == opex_preview
        assert body["ebitda"]["preview"] == expected_ebitda
        assert body["ebitda"]["preview"] == round(
            body["revenue"]["preview"] - body["opex"]["preview"], 2
        )


class TestEbitdaPreviewOmittedOrNull:
    def test_missing_ebitda_preview_field_omits_ebitda_key(self):
        resp = client.post(
            "/model/preview", json=_valid_payload(), cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "ebitda" not in body

    def test_null_ebitda_preview_omits_ebitda_key(self):
        """Null propagation: when either revenue or opex preview was
        unavailable client-side, the client sends ebitdaPreview: null,
        and the route correctly omits the 'ebitda' key entirely (never
        fabricates a partial/zero value)."""
        resp = client.post(
            "/model/preview",
            json=_valid_payload(
                revenueTotalPreview=12345.67,
                opexTotalPreview=None,
                ebitdaPreview=None,
            ),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "ebitda" not in body
        assert "revenue" in body
        assert "opex" not in body


class TestEbitdaPreviewRejectedSafely:
    def test_string_ebitda_preview_rejected(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(ebitdaPreview="not-a-number"),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"
        assert any("ebitdaPreview" in w for w in body["warnings"])

    def test_boolean_ebitda_preview_rejected(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(ebitdaPreview=False),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"


class TestNoFinancialEngineCallOrPersistenceMutation:
    def test_no_financial_engine_call(self, monkeypatch):
        import app.waterfall_core as waterfall_core

        def _boom(*args, **kwargs):
            raise AssertionError("waterfall_core.run_project must never be called by /model/preview")

        monkeypatch.setattr(waterfall_core, "run_project", _boom, raising=False)

        resp = client.post(
            "/model/preview",
            json=_valid_payload(ebitdaPreview=999.99),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "ebitda" in body

    def test_no_persistence_mutation(self):
        before_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else None
        before_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else None

        client.post(
            "/model/preview",
            json=_valid_payload(ebitdaPreview=42.0),
            cookies=_auth_cookies(),
        )

        after_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else None
        after_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else None
        assert before_mtime == after_mtime
        assert before_size == after_size


class TestAuthorizationRegressionUnaffected:
    def test_bogus_project_forbidden(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project="totally-bogus-project-code", ebitdaPreview=10.0),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "forbidden-project"
        assert "ebitda" not in body

    def test_unauthenticated_rejected(self):
        resp = client.post(
            "/model/preview", json=_valid_payload(ebitdaPreview=10.0),
        )
        assert resp.status_code == 401


class TestAllFivePreviewsCoexist:
    def test_capex_revenue_opex_ebitda_all_present_together(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(
                capexTotalPreview=111.11,
                revenueTotalPreview=222.22,
                opexTotalPreview=33.33,
                ebitdaPreview=188.89,
            ),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["capex"]["capex_total_preview"] == 111.11
        assert body["revenue"]["preview"] == 222.22
        assert body["opex"]["preview"] == 33.33
        assert body["ebitda"]["preview"] == 188.89
