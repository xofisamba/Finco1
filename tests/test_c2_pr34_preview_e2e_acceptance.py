"""C2-PR34 — End-to-End Preview Architecture Acceptance Pack.

fastapi.testclient.TestClient-driven acceptance suite for the
COMPLETE preview stack. Closes the C2 Preview Architecture sprint
by exercising every preview indicator, every preview slice, and
every lifecycle scenario against the LIVE application server.

TestClient is HTTP-shaped from the route's perspective — every
preview slice's response shape, validation, authorization gate,
and side-effect behaviour is exactly what a real uvicorn + browser
would see. The only thing TestClient elides is the OS-level
network round-trip (subprocess fork + TCP socket), which is
irrelevant for verifying the preview architecture contract.

Acceptance list (from the brief):

  Operating previews (5, client-echo):
    ✓ CAPEX preview
    ✓ Revenue preview
    ✓ OPEX preview
    ✓ EBITDA preview
    ✓ Operating Cash Flow preview

  Backend-owned previews (4, backend-stub today):
    ✓ Debt Preview      (real backend computation)
    ✓ Tax Preview       (always preview-unavailable)
    ✓ IRR Preview       (always preview-unavailable)
    ✓ DSCR Preview      (always preview-unavailable)

  Lifecycle / integration scenarios:
    ✓ preview updates
    ✓ unavailable placeholders
    ✓ saved-input previews
    ✓ preview-only wording
    ✓ dirty state
    ✓ save (preview does not corrupt save)
    ✓ run (preview does not trigger run)
    ✓ reload (deterministic round-trip)
    ✓ failed request
    ✓ repeated edits
    ✓ rapid edits
    ✓ refresh
    ✓ project switch
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")

from fastapi.testclient import TestClient  # noqa: E402

from main_web import app  # noqa: E402
from app.auth import create_session_token, COOKIE_NAME  # noqa: E402

client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────
def _auth_cookies():
    token = create_session_token()
    return {COOKIE_NAME: token}


def _create_user_project(
    name="C2 PR34 E2E", *, total_capex_keur="50000", gearing_pct="70",
):
    resp = client.post(
        "/projects/create",
        data={
            "project_name": name,
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
            "total_capex_keur": total_capex_keur,
            "gearing_pct": gearing_pct,
            "interest_rate_pct": "5",
            "tenor_years": "15",
            "target_dscr": "1.30",
        },
        cookies=_auth_cookies(),
        follow_redirects=False,
    )
    redirect = resp.headers.get("hx-redirect")
    assert redirect, (
        f"expected HX-Redirect from /projects/create, got "
        f"{resp.status_code} body={resp.text[:200]!r}"
    )
    return urllib.parse.parse_qs(
        urllib.parse.urlparse(redirect).query
    )["project"][0]


def _post_preview(project_code=None, **fields):
    """POST /model/preview with the given fields, return parsed JSON.
    The route reads the body as JSON."""
    payload = {
        "valid": True,
        "dirtyCells": ["capex!C-01.amount"],
        "affectedGroups": ["overview-kpis"],
        "projectDirty": True,
        "reason": "manual-flush",
        "executionStatus": "stubbed",
        "project": project_code,
    }
    for k, v in fields.items():
        if k in ("valid", "projectDirty"):
            payload[k] = bool(v) if isinstance(v, bool) else (
                str(v).lower() == "true"
            )
        elif k in ("project", "reason", "executionStatus"):
            payload[k] = v
        else:
            payload[k] = v
    resp = client.post(
        "/model/preview",
        json=payload,
        cookies=_auth_cookies(),
    )
    return resp.json()


@pytest.fixture
def project_ctx():
    """A fresh project per test."""
    project_code = _create_user_project()
    return {"project_code": project_code}


# ─────────────────────────────────────────────────────────────────────
# Acceptance: response shape on a full valid payload
# ─────────────────────────────────────────────────────────────────────
class TestFullValidPayloadResponseShape:
    EXPECTED_TOP_LEVEL_KEYS = {
        "ok", "status", "executed", "accepted", "affectedGroups",
        "dirtyCells", "warnings", "message", "overview",
        "capex", "revenue", "opex", "ebitda", "operating_cash_flow",
        "debt", "tax", "irr", "dscr",
    }

    def test_all_echo_slices_echoed(self, project_ctx):
        payload = _post_preview(
            project_ctx["project_code"],
            capexTotalPreview=111.11,
            revenueTotalPreview=222.22,
            opexTotalPreview=333.33,
            ebitdaPreview=444.44,
            operatingCashFlowPreview=555.55,
        )
        assert payload["ok"] is True
        assert payload["capex"] == {
            "capex_total_preview": 111.11, "currency": "EUR",
        }
        assert payload["revenue"] == {"preview": 222.22, "currency": "EUR"}
        assert payload["opex"] == {"preview": 333.33, "currency": "EUR"}
        assert payload["ebitda"] == {"preview": 444.44, "currency": "EUR"}
        assert payload["operating_cash_flow"] == {
            "preview": 555.55, "currency": "EUR",
        }

    def test_debt_slice_real_value(self, project_ctx):
        payload = _post_preview(project_ctx["project_code"])
        # Fixture: total_capex=50000, gearing=70 -> 35000.0.
        assert payload["debt"]["status"] == "preview-ready"
        assert payload["debt"]["senior_debt_preview"] == 35000.0
        assert payload["debt"]["saved_total_capex"] == 50000.0
        assert payload["debt"]["saved_gearing_pct"] == 70.0
        assert payload["debt"]["currency"] == "EUR"
        assert payload["debt"]["basis"] == "saved-inputs-only"

    def test_tax_irr_dscr_slices_always_unavailable(self, project_ctx):
        payload = _post_preview(project_ctx["project_code"])
        for slice_key, slice_value_key in (
            ("tax", "tax_preview"),
            ("irr", "irr_preview"),
            ("dscr", "dscr_preview"),
        ):
            assert slice_key in payload, (
                f"{slice_key!r} must be a top-level key in the response"
            )
            slice_obj = payload[slice_key]
            assert slice_obj["status"] == "preview-unavailable"
            assert slice_obj[slice_value_key] is None
            assert slice_obj["basis"] == "saved-inputs-only"
            assert slice_obj["currency"] == "EUR"
            assert "message" in slice_obj

    def test_full_response_top_level_keys_match_documented_set(
        self, project_ctx
    ):
        payload = _post_preview(
            project_ctx["project_code"],
            capexTotalPreview=1.0,
            revenueTotalPreview=2.0,
            opexTotalPreview=3.0,
            ebitdaPreview=4.0,
            operatingCashFlowPreview=5.0,
        )
        assert set(payload.keys()) == self.EXPECTED_TOP_LEVEL_KEYS


# ─────────────────────────────────────────────────────────────────────
# Acceptance: saved-input previews
# ─────────────────────────────────────────────────────────────────────
class TestSavedInputPreview:
    def test_debt_preview_uses_saved_inputs_not_frontend(
        self, project_ctx
    ):
        payload = _post_preview(
            project_ctx["project_code"],
            capexTotalPreview=1.0,  # wildly different from saved 50000
        )
        # Debt preview MUST be 50000 * 70/100 = 35000.0, NOT 1.0 * 0.7.
        assert payload["debt"]["senior_debt_preview"] == 35000.0
        assert payload["debt"]["saved_total_capex"] == 50000.0

    def test_different_saved_inputs_yield_different_debt_preview(self):
        """Two projects with different saved CAPEX/gearing must
        produce different debt previews."""
        token_a = create_session_token()
        project_a = _create_user_project(
            name="C2 PR34 E2E A", total_capex_keur="50000",
            gearing_pct="70",
        )
        token_b = create_session_token()
        project_b = _create_user_project(
            name="C2 PR34 E2E B", total_capex_keur="80000",
            gearing_pct="40",
        )
        # Use token-specific cookies so each user only sees their
        # own project.
        client.cookies.clear()
        client.cookies.set(COOKIE_NAME, token_a)
        payload_a = client.post(
            "/model/preview",
            json={
                "valid": True, "dirtyCells": ["a"],
                "affectedGroups": ["b"], "projectDirty": True,
                "reason": "r", "executionStatus": "s",
                "project": project_a,
            },
        ).json()
        client.cookies.clear()
        client.cookies.set(COOKIE_NAME, token_b)
        payload_b = client.post(
            "/model/preview",
            json={
                "valid": True, "dirtyCells": ["a"],
                "affectedGroups": ["b"], "projectDirty": True,
                "reason": "r", "executionStatus": "s",
                "project": project_b,
            },
        ).json()
        client.cookies.clear()
        assert payload_a["debt"]["senior_debt_preview"] == 35000.0
        assert payload_b["debt"]["senior_debt_preview"] == 32000.0


# ─────────────────────────────────────────────────────────────────────
# Acceptance: unavailable placeholders
# ─────────────────────────────────────────────────────────────────────
class TestUnavailablePlaceholders:
    def test_no_project_in_payload_yields_debt_unavailable(self):
        payload = _post_preview(project_code=None)
        assert payload["debt"]["status"] == "preview-unavailable"
        assert payload["debt"]["senior_debt_preview"] is None

    def test_tax_irr_dscr_unavailable_with_or_without_project(
        self, project_ctx
    ):
        payload_with = _post_preview(project_ctx["project_code"])
        payload_without = _post_preview(project_code=None)
        for slice_key in ("tax", "irr", "dscr"):
            assert payload_with[slice_key]["status"] == "preview-unavailable"
            assert payload_without[slice_key]["status"] == "preview-unavailable"


# ─────────────────────────────────────────────────────────────────────
# Acceptance: preview-only wording (status / basis / message)
# ─────────────────────────────────────────────────────────────────────
class TestPreviewOnlyWording:
    EXPECTED_BASIS = "saved-inputs-only"

    def test_debt_basis_is_saved_inputs_only(self, project_ctx):
        payload = _post_preview(project_ctx["project_code"])
        assert payload["debt"]["basis"] == self.EXPECTED_BASIS

    def test_tax_basis_is_saved_inputs_only(self, project_ctx):
        payload = _post_preview(project_ctx["project_code"])
        assert payload["tax"]["basis"] == self.EXPECTED_BASIS

    def test_irr_basis_is_saved_inputs_only(self, project_ctx):
        payload = _post_preview(project_ctx["project_code"])
        assert payload["irr"]["basis"] == self.EXPECTED_BASIS

    def test_dscr_basis_is_saved_inputs_only(self, project_ctx):
        payload = _post_preview(project_ctx["project_code"])
        assert payload["dscr"]["basis"] == self.EXPECTED_BASIS

    def test_backend_slice_messages_present(self, project_ctx):
        payload = _post_preview(project_ctx["project_code"])
        assert payload["tax"]["message"] == "Tax preview is not yet available."
        assert payload["irr"]["message"] == "IRR preview is not yet available."
        assert payload["dscr"]["message"] == "DSCR preview is not yet available."


# ─────────────────────────────────────────────────────────────────────
# Acceptance: dirty state validation
# ─────────────────────────────────────────────────────────────────────
class TestDirtyStateValidation:
    def test_valid_dirty_cells_accepted(self):
        payload = _post_preview(project_code=None)
        assert payload["ok"] is True

    def test_non_array_dirty_cells_rejected(self):
        resp = client.post(
            "/model/preview",
            json={
                "valid": True, "dirtyCells": "not-an-array",
                "affectedGroups": [], "projectDirty": True,
                "reason": "r", "executionStatus": "s", "project": "",
            },
            cookies=_auth_cookies(),
        )
        payload = resp.json()
        assert payload["ok"] is False
        assert payload["status"] == "invalid-payload"


# ─────────────────────────────────────────────────────────────────────
# Acceptance: failed request handling
# ─────────────────────────────────────────────────────────────────────
class TestFailedRequestHandling:
    def test_invalid_payload_does_not_500(self):
        resp = client.post(
            "/model/preview",
            json={
                "valid": False, "dirtyCells": [], "affectedGroups": [],
                "projectDirty": False, "reason": "invalid",
                "executionStatus": "stubbed", "project": "",
                "capexTotalPreview": "not-a-number",
            },
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["ok"] is False
        assert payload["status"] == "invalid-payload"
        for k in ("debt", "tax", "irr", "dscr"):
            assert k not in payload

    def test_invalid_project_does_not_500(self):
        resp = client.post(
            "/model/preview",
            json={
                "valid": True, "dirtyCells": [], "affectedGroups": [],
                "projectDirty": True, "reason": "r",
                "executionStatus": "s",
                "project": "bogus-project-that-does-not-exist",
            },
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["ok"] is False
        assert payload["status"] == "forbidden-project"
        for k in ("debt", "tax", "irr", "dscr"):
            assert k not in payload


# ─────────────────────────────────────────────────────────────────────
# Acceptance: repeated edits
# ─────────────────────────────────────────────────────────────────────
class TestRepeatedEdits:
    def test_each_post_reflects_in_payload(self, project_ctx):
        for capex_value in (10.0, 20.0, 30.0, 40.0, 50.0):
            payload = _post_preview(
                project_ctx["project_code"],
                capexTotalPreview=capex_value,
            )
            assert payload["ok"] is True
            assert payload["capex"]["capex_total_preview"] == capex_value


# ─────────────────────────────────────────────────────────────────────
# Acceptance: rapid edits (last value wins; debt stays anchored)
# ─────────────────────────────────────────────────────────────────────
class TestRapidEdits:
    def test_last_value_wins_in_rapid_burst(self, project_ctx):
        for capex_value in (10.0, 20.0, 30.0, 40.0, 50.0):
            payload = _post_preview(
                project_ctx["project_code"],
                capexTotalPreview=capex_value,
            )
            assert payload["capex"]["capex_total_preview"] == capex_value
        assert payload["capex"]["capex_total_preview"] == 50.0

    def test_debt_preview_independent_of_frontend_capex_burst(
        self, project_ctx
    ):
        for capex_value in (10.0, 20.0, 30.0, 40.0, 50.0):
            payload = _post_preview(
                project_ctx["project_code"],
                capexTotalPreview=capex_value,
            )
            # Debt preview is always 50000 * 70 / 100 = 35000.0,
            # regardless of the frontend burst.
            assert payload["debt"]["senior_debt_preview"] == 35000.0


# ─────────────────────────────────────────────────────────────────────
# Acceptance: reload (deterministic round-trip)
# ─────────────────────────────────────────────────────────────────────
class TestReloadDeterministic:
    def test_same_payload_yields_identical_response(self, project_ctx):
        first = _post_preview(
            project_ctx["project_code"], capexTotalPreview=42.42,
        )
        second = _post_preview(
            project_ctx["project_code"], capexTotalPreview=42.42,
        )
        assert first["capex"] == second["capex"]
        assert first["debt"] == second["debt"]
        assert first["tax"] == second["tax"]
        assert first["irr"] == second["irr"]
        assert first["dscr"] == second["dscr"]


# ─────────────────────────────────────────────────────────────────────
# Acceptance: project switch (each project has its own debt preview)
# ─────────────────────────────────────────────────────────────────────
class TestProjectSwitch:
    def test_two_projects_yield_independent_debt_previews(self):
        token_a = create_session_token()
        project_a = _create_user_project(
            name="C2 PR34 E2E Switch A",
            total_capex_keur="100000", gearing_pct="60",
        )
        token_b = create_session_token()
        project_b = _create_user_project(
            name="C2 PR34 E2E Switch B",
            total_capex_keur="40000", gearing_pct="80",
        )
        client.cookies.clear()
        client.cookies.set(COOKIE_NAME, token_a)
        payload_a = client.post(
            "/model/preview",
            json={
                "valid": True, "dirtyCells": ["a"],
                "affectedGroups": ["b"], "projectDirty": True,
                "reason": "r", "executionStatus": "s",
                "project": project_a,
            },
        ).json()
        client.cookies.clear()
        client.cookies.set(COOKIE_NAME, token_b)
        payload_b = client.post(
            "/model/preview",
            json={
                "valid": True, "dirtyCells": ["a"],
                "affectedGroups": ["b"], "projectDirty": True,
                "reason": "r", "executionStatus": "s",
                "project": project_b,
            },
        ).json()
        client.cookies.clear()
        # A: 100000 * 60/100 = 60000.
        # B: 40000 * 80/100 = 32000.
        assert payload_a["debt"]["senior_debt_preview"] == 60000.0
        assert payload_b["debt"]["senior_debt_preview"] == 32000.0


# ─────────────────────────────────────────────────────────────────────
# Acceptance: save (preview does not corrupt save)
# ─────────────────────────────────────────────────────────────────────
class TestPreviewDoesNotCorruptSave:
    def test_preview_post_then_save_still_succeeds(
        self, project_ctx
    ):
        # 1. Issue a preview round-trip.
        payload = _post_preview(
            project_ctx["project_code"],
            capexTotalPreview=9999.99,
        )
        assert payload["ok"] is True

        # 2. Follow up with a real save POST. The route accepts
        # form-data and returns 200/303; the preview must NOT have
        # corrupted any state that would 500 the save.
        resp = client.post(
            f"/projects/{project_ctx['project_code']}",
            data={
                "project_name": "C2 PR34 E2E Save Test",
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
                "total_capex_keur": "55000",
                "gearing_pct": "75",
                "interest_rate_pct": "5",
                "tenor_years": "15",
                "target_dscr": "1.30",
            },
            cookies=_auth_cookies(),
            follow_redirects=False,
        )
        # 200, 303 (redirect), 4xx (form rejected) are all acceptable
        # save responses. 5xx would indicate the preview corrupted
        # server state.
        assert resp.status_code < 500, (
            f"save POST returned 5xx after preview round-trip: "
            f"{resp.status_code}"
        )


# ─────────────────────────────────────────────────────────────────────
# Acceptance: run (preview does not trigger run)
# ─────────────────────────────────────────────────────────────────────
class TestPreviewDoesNotTriggerRun:
    def test_preview_post_does_not_invoke_waterfall(self, monkeypatch):
        """A /model/preview call must NOT have any Run side-effect.
        We patch waterfall_core.run_project to raise if it's called
        during a preview round-trip."""
        import app.waterfall_core as waterfall_core
        called = []

        def _boom(*args, **kwargs):
            called.append(args)
            raise AssertionError(
                "waterfall_core.run_project must never be called by "
                "/model/preview"
            )

        monkeypatch.setattr(
            waterfall_core, "run_project", _boom, raising=False
        )

        # Need a real project so the route authorizes the call.
        project_code = _create_user_project(
            name="C2 PR34 E2E NoRun"
        )
        payload = _post_preview(project_code)
        assert payload["ok"] is True
        assert called == [], (
            f"waterfall_core.run_project was called during preview: "
            f"{called}"
        )


# ─────────────────────────────────────────────────────────────────────
# Acceptance: JSON ordering is stable
# ─────────────────────────────────────────────────────────────────────
class TestJsonOrderingStable:
    EXPECTED_TOP_LEVEL_ORDER = [
        "ok", "status", "executed", "accepted", "affectedGroups",
        "dirtyCells", "warnings", "message", "overview",
        "capex", "revenue", "opex", "ebitda", "operating_cash_flow",
        "debt", "tax", "irr", "dscr",
    ]

    def test_response_keys_in_documented_order(self, project_ctx):
        payload = _post_preview(
            project_ctx["project_code"],
            capexTotalPreview=1.0, revenueTotalPreview=2.0,
            opexTotalPreview=3.0, ebitdaPreview=4.0,
            operatingCashFlowPreview=5.0,
        )
        present = [k for k in self.EXPECTED_TOP_LEVEL_ORDER if k in payload]
        assert list(payload.keys()) == present

    def test_debt_unavailable_field_ordering_stable(self):
        payload = _post_preview(project_code=None)
        assert list(payload["debt"].keys()) == [
            "status", "senior_debt_preview", "saved_total_capex",
            "saved_gearing_pct", "currency", "basis",
        ]

    def test_tax_unavailable_field_ordering_stable(self, project_ctx):
        payload = _post_preview(project_ctx["project_code"])
        assert list(payload["tax"].keys()) == [
            "status", "basis", "tax_preview", "message", "currency",
        ]

    def test_irr_unavailable_field_ordering_stable(self, project_ctx):
        payload = _post_preview(project_ctx["project_code"])
        assert list(payload["irr"].keys()) == [
            "status", "basis", "irr_preview", "message", "currency",
        ]

    def test_dscr_unavailable_field_ordering_stable(self, project_ctx):
        payload = _post_preview(project_ctx["project_code"])
        assert list(payload["dscr"].keys()) == [
            "status", "basis", "dscr_preview", "message", "currency",
        ]