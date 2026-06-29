"""C2-PR24: Backend-Computed Debt Preview Stub — route-level backend tests.

Proves the FIRST backend-computed (not frontend-computed) preview
field: `compute_debt_preview()` in `app/services/model_preview.py`,
wired additively into `/model/preview`'s JSON response under a new
"debt" key.

Formula (deliberately tiny, NOT real debt sizing — see
docs/C2_PR24_BACKEND_DEBT_PREVIEW_STUB.md):

    senior_debt_preview = saved_capex_total * (saved_gearing_pct / 100.0)

using ONLY the SAVED `baseline_snapshot["total_capex_keur"]` /
`baseline_snapshot["gearing_pct"]` fields already available server-side
via `get_project_by_code()` — never any preview field from the
incoming (possibly-unsaved) request payload.

Uses fastapi.testclient.TestClient against the real `main_web.app`,
mirroring tests/test_c2_pr22_export_run_safety_guardrails.py and
tests/test_c2_pr17_opex_line_editability.py's patterns.
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


def _create_user_project(name_suffix, total_capex_keur="50000", gearing_pct="70"):
    resp = client.post(
        "/projects/create",
        data={
            "project_name": f"C2 PR24 Debt Preview {name_suffix}",
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
    assert redirect, f"expected HX-Redirect from /projects/create, got {resp.status_code} {resp.text[:200]}"
    project_code = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)["project"][0]
    return project_code


class TestExistingOperatingPreviewFieldsUnchanged:
    """Required test 1/2/3: the five existing fields + invalid-payload +
    forbidden-project behaviour are unaffected by the PR23 extraction
    and the PR24 additive debt field."""

    def test_five_existing_fields_still_echoed(self):
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
        body = resp.json()
        assert body["capex"]["capex_total_preview"] == 111.11
        assert body["revenue"]["preview"] == 222.22
        assert body["opex"]["preview"] == 333.33
        assert body["ebitda"]["preview"] == 444.44
        assert body["operating_cash_flow"]["preview"] == 555.55

    def test_invalid_payload_unchanged(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview="nope"),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert resp.status_code == 200
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"
        assert "debt" not in body

    def test_forbidden_project_unchanged(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project="bogus-project-xyz"),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "forbidden-project"
        assert "debt" not in body


class TestDebtPreviewReadyForSavedCapexAndGearing:
    def test_debt_preview_ready_with_correct_formula(self):
        project_code = _create_user_project(
            "ready", total_capex_keur="64321.00", gearing_pct="65",
        )
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is True
        debt = body["debt"]
        assert debt["status"] == "preview-ready"
        assert debt["currency"] == "EUR"
        assert debt["basis"] == "saved-capex-times-saved-gearing"
        expected = round(64321.00 * (65 / 100.0), 2)
        assert debt["senior_debt_preview"] == expected

    def test_debt_preview_unavailable_when_no_project_context(self):
        """No `project` field -> no saved project record to read from
        -> unavailable, never fabricated."""
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=None),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["debt"] == {
            "status": "preview-unavailable",
            "senior_debt_preview": None,
            "currency": "EUR",
            "basis": "saved-inputs-only",
        }


class TestDebtPreviewIsGenuinelyBackendComputed:
    """Required test 6: the key architectural proof — the debt preview
    must come from the SAVED project's capex/gearing, never from the
    frontend's (possibly wildly different) capexTotalPreview value."""

    def test_debt_preview_ignores_frontend_capex_total_preview(self):
        project_code = _create_user_project(
            "ignores-frontend", total_capex_keur="80000.00", gearing_pct="70",
        )
        resp = client.post(
            "/model/preview",
            # A deliberately tiny, unrelated frontend value. If the
            # backend were (incorrectly) using this as a debt input,
            # the result would be 1.0 * 0.70 == 0.7, not anywhere near
            # the real saved-capex-based figure.
            json=_valid_payload(project=project_code, capexTotalPreview=1.0),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["capex"]["capex_total_preview"] == 1.0  # frontend echo unaffected
        debt = body["debt"]
        assert debt["status"] == "preview-ready"
        expected = round(80000.00 * (70 / 100.0), 2)
        assert debt["senior_debt_preview"] == expected
        assert debt["senior_debt_preview"] != 0.7

    def test_debt_preview_present_even_when_capex_preview_absent(self):
        """The frontend didn't even send capexTotalPreview this flush
        (e.g. a Revenue-only edit) -- debt preview is still computed
        from saved inputs, proving it does not depend on the frontend
        payload at all."""
        project_code = _create_user_project(
            "absent-frontend-capex", total_capex_keur="12345.00", gearing_pct="40",
        )
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code, revenueTotalPreview=99.0),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "capex" not in body
        debt = body["debt"]
        assert debt["status"] == "preview-ready"
        expected = round(12345.00 * (40 / 100.0), 2)
        assert debt["senior_debt_preview"] == expected


class TestDebtPreviewUnavailableWhenSavedInputsMissingOrInvalid:
    def test_unavailable_when_gearing_pct_blank(self, monkeypatch):
        """Simulate a saved project with a missing gearing_pct by
        monkeypatching get_project_by_code's return value's
        baseline_snapshot -- there's no UI path to create a project
        with a genuinely blank gearing_pct (the create form always
        sends a value), so this directly exercises the defensive
        branch in compute_debt_preview()."""
        import app.services.model_preview as model_preview_service

        class _FakeRecord:
            baseline_snapshot = {"total_capex_keur": "50000", "gearing_pct": ""}

        result = model_preview_service.compute_debt_preview({}, _FakeRecord())
        assert result == {
            "status": "preview-unavailable",
            "senior_debt_preview": None,
            "currency": "EUR",
            "basis": "saved-inputs-only",
        }

    def test_unavailable_when_capex_total_missing_entirely(self):
        import app.services.model_preview as model_preview_service

        class _FakeRecord:
            baseline_snapshot = {"gearing_pct": "70"}

        result = model_preview_service.compute_debt_preview({}, _FakeRecord())
        assert result["status"] == "preview-unavailable"
        assert result["senior_debt_preview"] is None

    def test_unavailable_when_project_record_is_none(self):
        import app.services.model_preview as model_preview_service

        result = model_preview_service.compute_debt_preview({}, None)
        assert result["status"] == "preview-unavailable"

    def test_unavailable_when_values_non_numeric_strings(self):
        import app.services.model_preview as model_preview_service

        class _FakeRecord:
            baseline_snapshot = {"total_capex_keur": "not-a-number", "gearing_pct": "70"}

        result = model_preview_service.compute_debt_preview({}, _FakeRecord())
        assert result["status"] == "preview-unavailable"


class TestDebtPreviewNoExportLeakage:
    """Required test 4: a distinctive saved capex/gearing combo never
    appears in export output, mirroring PR22's sentinel pattern."""

    def test_distinctive_debt_value_never_appears_in_csv_export(self):
        project_code = _create_user_project(
            "export-leak-csv", total_capex_keur="91111.00", gearing_pct="77",
        )
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        senior_debt = body["debt"]["senior_debt_preview"]
        assert senior_debt == round(91111.00 * 0.77, 2)
        sentinel_digits = str(senior_debt).replace(".", "")

        export_resp = client.get(
            f"/exports/runtime-summary.csv?project={project_code}",
            cookies=_auth_cookies(),
        )
        assert export_resp.status_code == 200
        assert sentinel_digits not in export_resp.text

    def test_distinctive_debt_value_never_appears_in_xlsx_export(self):
        project_code = _create_user_project(
            "export-leak-xlsx", total_capex_keur="88888.00", gearing_pct="33",
        )
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        senior_debt = body["debt"]["senior_debt_preview"]
        sentinel_digits = str(senior_debt).replace(".", "")

        export_resp = client.get(
            f"/exports/institutional-workbook.xlsx?project={project_code}",
            cookies=_auth_cookies(),
        )
        assert export_resp.status_code == 200
        assert sentinel_digits.encode("utf-8") not in export_resp.content


class TestDebtPreviewNoDbMutationOrEngineCall:
    """Required test 5/8: no DB mutation, no financial engine call."""

    def test_no_db_mutation_from_debt_preview_request(self):
        project_code = _create_user_project("no-mutation")
        before_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else None
        before_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else None

        client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
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

        project_code = _create_user_project("no-engine-call")
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["debt"]["status"] == "preview-ready"


class TestNoDebtSculptingKeywordsInFrontendJs:
    """Required test 9: confirm no debt sculpting/DSCR/amortization
    keywords were added to recalc-preview.js, mirroring
    tests/test_c2_pr1_live_model.py's static-content-fetch pattern."""

    def test_recalc_preview_js_has_no_debt_arithmetic_keywords(self):
        resp = client.get("/static/modelling/recalc-preview.js")
        assert resp.status_code == 200
        text = resp.text.lower()
        # "sculpt"/"dscr"/"interest schedule" are genuinely new-risk
        # keywords that must never appear, since PR24 deliberately
        # implements none of debt sculpting/DSCR sizing/an interest
        # schedule in any frontend JS file.
        forbidden = ["sculpt", "dscr", "interest schedule"]
        for kw in forbidden:
            assert kw not in text, f"forbidden keyword {kw!r} found in recalc-preview.js"
        # "debt"/"amortiz" already appear pre-PR24, but ONLY inside two
        # pre-existing disclaimer phrases stating the OCF preview does
        # NOT apply any debt service/amortization — never as part of
        # actual calculation logic. Assert the count of "debt"
        # occurrences hasn't grown beyond those two known pre-existing
        # disclaimer phrases (i.e. PR24 added zero new "debt" mentions
        # to this file).
        known_pre_existing_debt_phrases = [
            "no debt/tax/depreciation/financing",
            "no debt service, no tax, no depre",
        ]
        remaining = text
        for phrase in known_pre_existing_debt_phrases:
            remaining = remaining.replace(phrase, "", 1)
        assert "debt" not in remaining, (
            "recalc-preview.js must not gain any debt-related code beyond "
            "the two pre-existing disclaimer phrases"
        )
