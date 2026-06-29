"""C2-PR16: Operating Cash Flow Preview — route-level backend tests.

NOT AUTHORITATIVE OPERATING CASH FLOW. Operating Cash Flow Preview is
defined, in full, as a verbatim passthrough of C2-PR15's EBITDA Preview
value (no debt/tax/depreciation/working-capital adjustment of any
kind). The server's job here is purely validate-and-echo, exactly like
capex/revenue/opex/ebitda. These tests verify the ROUTE's
validate-and-echo behaviour, plus a chaining-correctness reference
check (the OCF value echoed must equal the EBITDA value supplied,
verbatim).

Uses fastapi.testclient.TestClient against the real `main_web.app`,
mirroring tests/test_c2_pr15_ebitda_preview.py's pattern.
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


class TestOcfPreviewAccepted:
    def test_valid_numeric_ocf_echoed_back(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(operatingCashFlowPreview=3889.674),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "operating_cash_flow" in body
        assert body["operating_cash_flow"]["preview"] == 3889.67
        assert body["operating_cash_flow"]["currency"] == "EUR"

    def test_zero_ocf_is_still_rendered_not_omitted(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(operatingCashFlowPreview=0.0),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "operating_cash_flow" in body
        assert body["operating_cash_flow"]["preview"] == 0.0

    def test_negative_ocf_accepted(self):
        """Defensive: a real negative EBITDA (opex > revenue) passes
        through as a negative OCF preview, never rejected/clamped."""
        resp = client.post(
            "/model/preview",
            json=_valid_payload(operatingCashFlowPreview=-1234.56),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "operating_cash_flow" in body
        assert body["operating_cash_flow"]["preview"] == -1234.56


class TestOcfChainingReference:
    """Reference check: Operating Cash Flow preview is a verbatim
    passthrough of EBITDA preview — the route never recomputes it, it
    only validates and echoes the client-supplied number, which a
    correct client always sets equal to ebitdaPreview."""

    def test_ocf_equals_ebitda_verbatim(self):
        ebitda_preview = 3889.67
        resp = client.post(
            "/model/preview",
            json=_valid_payload(
                revenueTotalPreview=12345.67,
                opexTotalPreview=8456.00,
                ebitdaPreview=ebitda_preview,
                operatingCashFlowPreview=ebitda_preview,
            ),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ebitda"]["preview"] == ebitda_preview
        assert body["operating_cash_flow"]["preview"] == ebitda_preview
        assert body["operating_cash_flow"]["preview"] == body["ebitda"]["preview"]


class TestOcfPreviewOmittedOrNull:
    def test_missing_ocf_preview_field_omits_key(self):
        resp = client.post(
            "/model/preview", json=_valid_payload(), cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "operating_cash_flow" not in body

    def test_null_ocf_preview_omits_key_when_ebitda_unavailable(self):
        """Null propagation: when EBITDA preview was null this flush
        (e.g. only one of Revenue/OPEX was edited), the client sends
        operatingCashFlowPreview: null, and the route omits the
        'operating_cash_flow' key entirely (never fabricates a value)."""
        resp = client.post(
            "/model/preview",
            json=_valid_payload(
                revenueTotalPreview=12345.67,
                opexTotalPreview=None,
                ebitdaPreview=None,
                operatingCashFlowPreview=None,
            ),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "operating_cash_flow" not in body
        assert "ebitda" not in body
        assert "revenue" in body


class TestOcfPreviewRejectedSafely:
    def test_string_ocf_preview_rejected(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(operatingCashFlowPreview="not-a-number"),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"
        assert any("operatingCashFlowPreview" in w for w in body["warnings"])

    def test_boolean_ocf_preview_rejected(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(operatingCashFlowPreview=True),
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
            json=_valid_payload(operatingCashFlowPreview=999.99),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "operating_cash_flow" in body

    def test_no_persistence_mutation(self):
        before_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else None
        before_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else None

        client.post(
            "/model/preview",
            json=_valid_payload(operatingCashFlowPreview=42.0),
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
            json=_valid_payload(project="totally-bogus-project-code", operatingCashFlowPreview=10.0),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "forbidden-project"
        assert "operating_cash_flow" not in body

    def test_unauthenticated_rejected(self):
        resp = client.post(
            "/model/preview", json=_valid_payload(operatingCashFlowPreview=10.0),
        )
        assert resp.status_code == 401


class TestAllFivePreviewsCoexist:
    def test_capex_revenue_opex_ebitda_ocf_all_present_together(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(
                capexTotalPreview=111.11,
                revenueTotalPreview=222.22,
                opexTotalPreview=33.33,
                ebitdaPreview=188.89,
                operatingCashFlowPreview=188.89,
            ),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["capex"]["capex_total_preview"] == 111.11
        assert body["revenue"]["preview"] == 222.22
        assert body["opex"]["preview"] == 33.33
        assert body["ebitda"]["preview"] == 188.89
        assert body["operating_cash_flow"]["preview"] == 188.89
