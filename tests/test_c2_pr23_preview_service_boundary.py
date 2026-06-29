"""C2-PR23: Preview Service Boundary Extraction — characterization tests.

These tests are written and run FIRST against the UNMODIFIED
`/model/preview` route (the validation/echo logic still living inline
in `main_web.py`'s `_c2_pr7_validate_preview_payload()`/`model_preview()`)
to lock in CURRENT behaviour before any extraction work begins. After
the extraction into `app/services/model_preview.py`, this exact same
file must continue to pass unchanged — that is the proof of "zero
behaviour change."

Mirrors the request/response patterns already established by
tests/test_c2_pr14_opex_preview.py and
tests/test_c2_pr22_export_run_safety_guardrails.py.

Uses fastapi.testclient.TestClient against the real `main_web.app`.
"""
import os
import urllib.parse

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
        "dirtyCells": ["capex!C-01.amount"],
        "affectedGroups": ["overview-kpis"],
        "projectDirty": True,
        "reason": "manual-flush",
        "executionStatus": "stubbed",
        "project": None,
    }
    payload.update(overrides)
    return payload


def _create_user_project(name_suffix):
    resp = client.post(
        "/projects/create",
        data={
            "project_name": f"C2 PR23 Boundary {name_suffix}",
            "project_type": "Solar",
            "template_source": "generic_solar",
            "country_market": "Croatia",
            "capacity_mw": "50",
            "cod_date": "2027-01-01",
            "construction_months": "12",
            "horizon_years": "25",
            "tariff_eur_mwh": "60",
            "ppa_term_years": "15",
            "p50_hours": "1400",
            "opex_y1_keur": "1000",
            "total_capex_keur": "50000",
            "gearing_pct": "70",
            "interest_rate_pct": "5",
            "tenor_years": "15",
            "target_dscr": "1.30",
        },
        cookies=_auth_cookies(),
        follow_redirects=False,
    )
    redirect = resp.headers.get("hx-redirect")
    assert redirect, f"expected HX-Redirect from /projects/create, got {resp.status_code} {resp.text[:200]}"
    project_code = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)["project"][0]
    return project_code


class TestFullValidPayloadAllFivePreviewFields:
    """Point 1: a valid full payload with all five preview fields set."""

    def test_all_five_fields_echoed_with_exact_current_shape(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(
                capexTotalPreview=111.11,
                revenueTotalPreview=222.22,
                opexTotalPreview=333.33,
                ebitdaPreview=444.44,
                operatingCashFlowPreview=555.55,
            ),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["status"] == "stubbed"
        assert body["executed"] is False
        assert body["accepted"] is True
        assert body["warnings"] == []
        assert body["overview"] == {"runtime_status": "Preview executed", "updated": True}
        assert body["capex"] == {"capex_total_preview": 111.11, "currency": "EUR"}
        assert body["revenue"] == {"preview": 222.22, "currency": "EUR"}
        assert body["opex"] == {"preview": 333.33, "currency": "EUR"}
        assert body["ebitda"] == {"preview": 444.44, "currency": "EUR"}
        assert body["operating_cash_flow"] == {"preview": 555.55, "currency": "EUR"}


class TestMissingOptionalPreviewFieldsOmitted:
    """Point 2: missing optional preview fields -> omitted from response."""

    def test_all_five_fields_absent_omits_all_five_response_keys(self):
        resp = client.post(
            "/model/preview", json=_valid_payload(), cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is True
        for key in ("capex", "revenue", "opex", "ebitda", "operating_cash_flow"):
            assert key not in body


class TestNullPreviewFieldsOmitted:
    """Point 3: explicit null preview fields -> also omitted (current
    actual behaviour, confirmed by reading main_web.py's `is not None`
    guards on every field)."""

    def test_all_five_fields_null_omits_all_five_response_keys(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(
                capexTotalPreview=None,
                revenueTotalPreview=None,
                opexTotalPreview=None,
                ebitdaPreview=None,
                operatingCashFlowPreview=None,
            ),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is True
        for key in ("capex", "revenue", "opex", "ebitda", "operating_cash_flow"):
            assert key not in body


class TestMalformedPreviewFieldsRejectedSafely:
    """Point 4: malformed/non-numeric preview fields -> safe
    invalid-payload response, never a 500."""

    def test_string_field_rejected(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview="not-a-number"),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"
        assert isinstance(body["warnings"], list)
        assert any("capexTotalPreview" in w for w in body["warnings"])

    def test_boolean_field_rejected(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(revenueTotalPreview=True),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"

    def test_infinity_field_rejected(self):
        resp = client.post(
            "/model/preview",
            data=b'{"valid": true, "dirtyCells": [], "affectedGroups": [], '
                 b'"projectDirty": false, "reason": "x", "executionStatus": null, '
                 b'"project": null, "opexTotalPreview": Infinity}',
            headers={"Content-Type": "application/json"},
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"

    def test_completely_malformed_body_never_500s(self):
        resp = client.post(
            "/model/preview",
            data=b"not even json",
            headers={"Content-Type": "application/json"},
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"


class TestForbiddenProjectRejectedSafely:
    """Point 5: forbidden/non-owned project code -> forbidden-project."""

    def test_bogus_project_code_forbidden(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project="totally-bogus-project-code-xyz", capexTotalPreview=10.0),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "forbidden-project"
        assert "capex" not in body

    def test_owned_project_code_accepted(self):
        project_code = _create_user_project("forbidden-check")
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code, capexTotalPreview=10.0),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is True
        assert "capex" in body


class TestUnauthenticatedRejected:
    """Point 6: unauthenticated request -> 401."""

    def test_no_cookie_returns_401(self):
        resp = client.post("/model/preview", json=_valid_payload(capexTotalPreview=10.0))
        assert resp.status_code == 401
        body = resp.json()
        assert body["status"] == "unauthenticated"


class TestExportRunIsolation:
    """Point 7: mirrors test_c2_pr22's pattern — a /model/preview POST
    never mutates the DB and never calls the real financial engine."""

    def test_db_file_unchanged_after_preview_post(self):
        before_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else None
        before_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else None

        client.post(
            "/model/preview",
            json=_valid_payload(
                capexTotalPreview=987654.32,
                revenueTotalPreview=987654.32,
                opexTotalPreview=987654.32,
                ebitdaPreview=987654.32,
                operatingCashFlowPreview=987654.32,
            ),
            cookies=_auth_cookies(),
        )

        after_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else None
        after_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else None
        assert before_mtime == after_mtime
        assert before_size == after_size

    def test_no_financial_engine_call(self, monkeypatch):
        import app.waterfall_core as waterfall_core

        def _boom(*args, **kwargs):
            raise AssertionError("waterfall_core.run_project must never be called by /model/preview")

        monkeypatch.setattr(waterfall_core, "run_project", _boom, raising=False)

        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview=42.0),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
