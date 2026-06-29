"""C2-PR25/26/27 — Debt Preview v2 + UI Safety + Safety Tests.

Stacked on top of C2-PR24 (Backend-Computed Debt Preview Stub).
Extends the C2-PR24 single-number placeholder into a small
saved-inputs breakdown (`senior_debt_preview`, `saved_total_capex`,
`saved_gearing_pct`), makes the UI copy explicitly non-authoritative,
and pins the 12-point guardrail suite before any real debt-sizing
work is allowed to land.

Acceptance criteria mapped to test classes:
  1. Debt preview uses saved CAPEX/gearing only
       -> TestDebtPreviewUsesSavedCapexAndGearingOnly
  2. Debt preview ignores frontend capexTotalPreview
       -> TestDebtPreviewIgnoresFrontendCapexTotalPreview
  3. Debt preview ignores frontend OPEX/Revenue/EBITDA/OCF
       -> TestDebtPreviewIgnoresFrontendOpexRevenueEbitdaOcf
  4. Debt preview does not call waterfall_core.py
       -> TestDebtPreviewDoesNotCallWaterfall
  5. Debt preview does not touch domain/*
       -> TestDebtPreviewDoesNotTouchDomain
  6. Debt preview does not mutate DB
       -> TestDebtPreviewDoesNotMutateDb
  7. Debt preview does not affect exports
       -> TestDebtPreviewDoesNotAffectExports
  8. Debt preview does not affect Run
       -> TestDebtPreviewDoesNotAffectRun
  9. Debt preview response is deterministic
       -> TestDebtPreviewResponseIsDeterministic
 10. Frontend has no debt formula
       -> TestFrontendHasNoDebtFormula
 11. UI copy clearly says saved inputs only / not sculpted / Run authoritative
       -> TestUiCopySaysSavedInputsNotSculptedRunAuthoritative
 12. Operating preview stack remains unchanged
       -> TestOperatingPreviewStackUnchanged
"""
import os
import re
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
            "project_name": f"C2 PR25-27 {name_suffix}",
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
    return urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)["project"][0]


# ─────────────────────────────────────────────────────────────────────
# Acceptance 1: Debt preview uses saved CAPEX/gearing only.
# ─────────────────────────────────────────────────────────────────────
class TestDebtPreviewUsesSavedCapexAndGearingOnly:
    def test_ready_response_carries_saved_total_capex_and_saved_gearing_pct(self):
        project_code = _create_user_project(
            "ready-with-breakdown", total_capex_keur="60000.00", gearing_pct="60",
        )
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        debt = body["debt"]
        assert debt["status"] == "preview-ready"
        assert debt["currency"] == "EUR"
        # The new C2-PR25 breakdown fields must be present and finite.
        assert debt["saved_total_capex"] == 60000.00
        assert debt["saved_gearing_pct"] == 60.0
        assert debt["basis"] == "saved-inputs-only"

    def test_breakdown_values_round_trip_from_baseline_snapshot(self):
        """The breakdown fields must reflect what the SAVED project
        actually has stored — i.e. they're pulled from
        baseline_snapshot, not echoed from the request payload."""
        project_code = _create_user_project(
            "roundtrip", total_capex_keur="12345.67", gearing_pct="55",
        )
        # Send a wildly different frontend CAPEX preview.
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code, capexTotalPreview=1.0),
            cookies=_auth_cookies(),
        )
        debt = resp.json()["debt"]
        # Both breakdown fields must match the SAVED values, not the
        # 1.0 sentinel the frontend sent.
        assert debt["saved_total_capex"] == 12345.67
        assert debt["saved_gearing_pct"] == 55.0

    def test_unavailable_response_has_null_breakdown_fields(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=None),
            cookies=_auth_cookies(),
        )
        debt = resp.json()["debt"]
        assert debt["status"] == "preview-unavailable"
        assert debt["senior_debt_preview"] is None
        assert debt["saved_total_capex"] is None
        assert debt["saved_gearing_pct"] is None


# ─────────────────────────────────────────────────────────────────────
# Acceptance 2: Debt preview ignores frontend capexTotalPreview.
# ─────────────────────────────────────────────────────────────────────
class TestDebtPreviewIgnoresFrontendCapexTotalPreview:
    def test_sentinel_frontend_capex_does_not_change_senior_debt(self):
        project_code = _create_user_project(
            "sentinel-frontend", total_capex_keur="80000.00", gearing_pct="70",
        )
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code, capexTotalPreview=1.0),
            cookies=_auth_cookies(),
        )
        debt = resp.json()["debt"]
        expected = round(80000.00 * (70 / 100.0), 2)
        assert debt["senior_debt_preview"] == expected
        assert debt["senior_debt_preview"] != 0.7
        assert debt["saved_total_capex"] == 80000.00


# ─────────────────────────────────────────────────────────────────────
# Acceptance 3: Debt preview ignores frontend OPEX/Revenue/EBITDA/OCF.
# ─────────────────────────────────────────────────────────────────────
class TestDebtPreviewIgnoresFrontendOpexRevenueEbitdaOcf:
    def test_frontend_revenue_preview_does_not_change_senior_debt(self):
        project_code = _create_user_project(
            "revenue-no-effect", total_capex_keur="45000.00", gearing_pct="65",
        )
        resp = client.post(
            "/model/preview",
            json=_valid_payload(
                project=project_code,
                revenueTotalPreview=99999999.99,
            ),
            cookies=_auth_cookies(),
        )
        debt = resp.json()["debt"]
        expected = round(45000.00 * (65 / 100.0), 2)
        assert debt["senior_debt_preview"] == expected

    def test_frontend_opex_preview_does_not_change_senior_debt(self):
        project_code = _create_user_project(
            "opex-no-effect", total_capex_keur="45000.00", gearing_pct="65",
        )
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code, opexTotalPreview=99999999.99),
            cookies=_auth_cookies(),
        )
        debt = resp.json()["debt"]
        expected = round(45000.00 * (65 / 100.0), 2)
        assert debt["senior_debt_preview"] == expected

    def test_frontend_ebitda_and_ocf_previews_do_not_change_senior_debt(self):
        project_code = _create_user_project(
            "ebitda-ocf-no-effect", total_capex_keur="45000.00", gearing_pct="65",
        )
        resp = client.post(
            "/model/preview",
            json=_valid_payload(
                project=project_code,
                ebitdaPreview=99999999.99,
                operatingCashFlowPreview=99999999.99,
            ),
            cookies=_auth_cookies(),
        )
        debt = resp.json()["debt"]
        expected = round(45000.00 * (65 / 100.0), 2)
        assert debt["senior_debt_preview"] == expected


# ─────────────────────────────────────────────────────────────────────
# Acceptance 4: Debt preview does not call waterfall_core.py.
# ─────────────────────────────────────────────────────────────────────
class TestDebtPreviewDoesNotCallWaterfall:
    def test_waterfall_run_project_never_invoked(self, monkeypatch):
        import app.waterfall_core as waterfall_core

        def _boom(*args, **kwargs):
            raise AssertionError("waterfall_core.run_project must never be called by /model/preview")

        monkeypatch.setattr(waterfall_core, "run_project", _boom, raising=False)
        project_code = _create_user_project("no-waterfall-call")
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        assert resp.json()["debt"]["status"] == "preview-ready"


# ─────────────────────────────────────────────────────────────────────
# Acceptance 5: Debt preview does not touch domain/*.
# ─────────────────────────────────────────────────────────────────────
class TestDebtPreviewDoesNotTouchDomain:
    def test_model_preview_module_does_not_import_domain(self):
        import inspect
        import app.services.model_preview as model_preview_service
        source = inspect.getsource(model_preview_service)
        # The service module is forbidden from importing anything from
        # app.domain.* (the financial-engine package). C2-PR25
        # deliberately keeps the function as a small pure-Python
        # multiplier over already-saved snapshot fields.
        assert "from app.domain" not in source
        assert "import app.domain" not in source

    def test_route_does_not_call_domain_for_debt(self, monkeypatch):
        import app.domain as domain_module
        original_attrs = {
            name: getattr(domain_module, name)
            for name in dir(domain_module)
            if not name.startswith("_")
        }
        called_attrs = []

        class _ExplodingProxy:
            def __getattr__(self, name):
                if name in original_attrs:
                    called_attrs.append(name)
                    raise AssertionError(
                        f"domain.{name} must not be called from /model/preview"
                    )
                raise AttributeError(name)

        # Monkeypatch only the callables we care about; the rest stay
        # the same so the rest of the test app keeps working.
        for name in list(original_attrs.keys()):
            value = original_attrs[name]
            if callable(value):
                monkeypatch.setattr(domain_module, name, _ExplodingProxy(), raising=False)
        project_code = _create_user_project("no-domain-touch")
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        assert resp.json()["debt"]["status"] == "preview-ready"
        assert called_attrs == [], (
            f"domain callables were reached: {called_attrs}"
        )


# ─────────────────────────────────────────────────────────────────────
# Acceptance 6: Debt preview does not mutate DB.
# ─────────────────────────────────────────────────────────────────────
class TestDebtPreviewDoesNotMutateDb:
    def test_db_mtime_and_size_unchanged_after_debt_preview_request(self):
        project_code = _create_user_project("no-mutation-pr25")
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


# ─────────────────────────────────────────────────────────────────────
# Acceptance 7: Debt preview does not affect exports.
# ─────────────────────────────────────────────────────────────────────
class TestDebtPreviewDoesNotAffectExports:
    def test_csv_export_does_not_carry_debt_preview_sentinel(self):
        project_code = _create_user_project(
            "csv-sentinel-pr25", total_capex_keur="91111.00", gearing_pct="77",
        )
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(),
        )
        senior_debt = resp.json()["debt"]["senior_debt_preview"]
        sentinel = str(senior_debt).replace(".", "")
        export_resp = client.get(
            f"/exports/runtime-summary.csv?project={project_code}",
            cookies=_auth_cookies(),
        )
        assert export_resp.status_code == 200
        assert sentinel not in export_resp.text

    def test_xlsx_export_does_not_carry_debt_preview_sentinel(self):
        project_code = _create_user_project(
            "xlsx-sentinel-pr25", total_capex_keur="88888.00", gearing_pct="33",
        )
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(),
        )
        senior_debt = resp.json()["debt"]["senior_debt_preview"]
        sentinel = str(senior_debt).replace(".", "")
        export_resp = client.get(
            f"/exports/institutional-workbook.xlsx?project={project_code}",
            cookies=_auth_cookies(),
        )
        assert export_resp.status_code == 200
        assert sentinel.encode("utf-8") not in export_resp.content


# ─────────────────────────────────────────────────────────────────────
# Acceptance 8: Debt preview does not affect Run.
# ─────────────────────────────────────────────────────────────────────
class TestDebtPreviewDoesNotAffectRun:
    def test_debt_preview_request_does_not_trigger_run(self, monkeypatch):
        import app.waterfall_core as waterfall_core

        def _boom(*args, **kwargs):
            raise AssertionError(
                "Run must never fire as a side-effect of a /model/preview call"
            )

        monkeypatch.setattr(waterfall_core, "run_project", _boom, raising=False)
        project_code = _create_user_project("no-run-side-effect")
        # Multiple consecutive previews must all stay preview-only.
        for _ in range(3):
            resp = client.post(
                "/model/preview",
                json=_valid_payload(project=project_code),
                cookies=_auth_cookies(),
            )
            assert resp.status_code == 200
            assert resp.json()["debt"]["status"] == "preview-ready"


# ─────────────────────────────────────────────────────────────────────
# Acceptance 9: Debt preview response is deterministic.
# ─────────────────────────────────────────────────────────────────────
class TestDebtPreviewResponseIsDeterministic:
    def test_two_requests_with_same_inputs_return_identical_debt_block(self):
        project_code = _create_user_project(
            "deterministic", total_capex_keur="60000.00", gearing_pct="60",
        )
        r1 = client.post(
            "/model/preview", json=_valid_payload(project=project_code),
            cookies=_auth_cookies(),
        )
        r2 = client.post(
            "/model/preview", json=_valid_payload(project=project_code),
            cookies=_auth_cookies(),
        )
        assert r1.json()["debt"] == r2.json()["debt"]

    def test_unit_compute_is_pure_function(self):
        """Direct unit test of compute_debt_preview() — same inputs
        always produce the same output (no time/random/IO coupling)."""
        import app.services.model_preview as mp

        class _FakeRecord:
            baseline_snapshot = {"total_capex_keur": "54321.00", "gearing_pct": "62"}

        first = mp.compute_debt_preview({}, _FakeRecord())
        second = mp.compute_debt_preview({}, _FakeRecord())
        assert first == second
        assert first["status"] == "preview-ready"
        assert first["senior_debt_preview"] == round(54321.00 * 0.62, 2)
        assert first["saved_total_capex"] == 54321.00
        assert first["saved_gearing_pct"] == 62.0


# ─────────────────────────────────────────────────────────────────────
# Acceptance 10: Frontend has no debt formula.
# ─────────────────────────────────────────────────────────────────────
class TestFrontendHasNoDebtFormula:
    def test_runtime_renderer_has_no_debt_arithmetic(self):
        resp = client.get("/static/modelling/runtime-renderer.js")
        assert resp.status_code == 200
        text = resp.text
        # The renderer is forbidden from computing debt sizing of any
        # kind. The only allowed use of the word "debt" is as a
        # property accessor (`body.debt.*`) or a literal label string
        # ("Debt preview ..." / "debt-preview-*"). We grep for the
        # multiplication patterns explicitly.
        forbidden_patterns = [
            # a debt-relevant multiplier: `something * something` where
            # something is debt-flavoured. We approximate by looking
            # for `* capex` / `* gearing` / `gearing *` in non-comment
            # lines.
            r"\*\s*capex",
            r"\*\s*gearing",
            r"gearing\s*\*",
            r"capex\s*\*",
            r"capexTotalPreview\s*\*",
            r"saved_total_capex\s*\*",
            r"saved_gearing_pct\s*\*",
        ]
        for pat in forbidden_patterns:
            assert re.search(pat, text) is None, (
                f"runtime-renderer.js contains forbidden debt-arithmetic "
                f"pattern {pat!r}"
            )

    def test_recalc_preview_js_has_no_debt_arithmetic_keywords(self):
        resp = client.get("/static/modelling/recalc-preview.js")
        assert resp.status_code == 200
        text = resp.text.lower()
        forbidden = ["sculpt", "dscr", "interest schedule"]
        for kw in forbidden:
            assert kw not in text, f"forbidden keyword {kw!r} found in recalc-preview.js"
        # 'amortiz' is allowed ONLY inside the pre-existing disclaimer
        # phrase "no debt service, no tax, no depreciation/amortization,
        # no working"; strip that exact phrase out and assert no other
        # occurrence remains.
        known_disclaimer_phrases = [
            "no debt/tax/depreciation/financing",
            "no debt service, no tax, no depreciation/amortization, no working",
        ]
        remaining = text
        for phrase in known_disclaimer_phrases:
            remaining = remaining.replace(phrase, "", 1)
        assert "amortiz" not in remaining, (
            "'amortiz' must only appear inside the pre-existing disclaimer "
            "phrase in recalc-preview.js"
        )
        assert "debt" not in remaining, (
            "recalc-preview.js must not gain any debt-related code beyond "
            "the two pre-existing disclaimer phrases"
        )


# ─────────────────────────────────────────────────────────────────────
# Acceptance 11: UI copy clearly says saved inputs only / not
# sculpted / Run authoritative.
# ─────────────────────────────────────────────────────────────────────
class TestUiCopySaysSavedInputsNotSculptedRunAuthoritative:
    def _fetch_workspace_text(self):
        """Fetch the rendered workspace for an authenticated user.
        ``GET /?project=<code>`` renders ``index.html`` which includes
        ``partials/workspace_shell.html`` — that's where the debt-
        preview markup lives."""
        project_code = _create_user_project("ui-copy")
        resp = client.get(
            f"/?project={project_code}",
            cookies=_auth_cookies(),
            follow_redirects=False,
        )
        assert resp.status_code == 200, (
            f"/?project=... returned {resp.status_code}: {resp.text[:200]}"
        )
        return resp.text, project_code

    def test_workspace_shell_template_carries_safety_copy(self):
        text, _ = self._fetch_workspace_text()
        # Required phrases (case-sensitive; the visible label uses
        # parentheses + colon exactly as in the brief).
        required_phrases = [
            "Debt preview (saved inputs only):",
            "Saved CAPEX used:",
            "Saved gearing used:",
            "Uses saved CAPEX and saved gearing only. Not sculpted. Run remains authoritative.",
        ]
        for phrase in required_phrases:
            assert phrase in text, (
                f"workspace_shell.html rendered output is missing safety copy: {phrase!r}"
            )

    def test_workspace_shell_does_not_use_internal_jargon_in_label(self):
        text, _ = self._fetch_workspace_text()
        # The visible label must NOT contain internal jargon like
        # "C1", "C2", "PR25", "PR26", "PR27", "backend", "frontend",
        # "stub", or "placeholder" — those would be scare/internal
        # wording to a user reading the UI.
        # The `data-c2pr*-*` attributes used by tests are an exception
        # (they are not visible to users), so we check only the visible
        # label region.
        # We find the visible label (inside the runtime-status-indicator
        # span) and assert the jargon is absent there.
        label_match = re.search(
            r'class="runtime-status-indicator__label"[^>]*>([^<]+)<',
            text,
        )
        assert label_match, "Could not find the visible debt-preview label"
        visible_label = label_match.group(1)
        for jargon in ["C1", "C2", "PR25", "PR26", "PR27", "backend", "frontend", "stub", "placeholder"]:
            assert jargon.lower() not in visible_label.lower(), (
                f"Visible label must not contain jargon {jargon!r}: {visible_label!r}"
            )

    def test_data_attributes_only_used_for_test_bookkeeping(self):
        text, _ = self._fetch_workspace_text()
        # The breakdown sub-line carries a `data-c2pr25-debt-basis`
        # attribute. The same id (`#debt-preview-basis`) is the seam
        # the JS renderer uses to update the basis row. The visible
        # user copy is the title attribute + label text only.
        assert 'id="debt-preview-basis"' in text
        assert 'id="debt-preview-saved-capex"' in text
        assert 'id="debt-preview-saved-gearing"' in text
        # Title attribute (tooltip) carries the safety copy.
        assert 'title="Uses saved CAPEX and saved gearing only. Not sculpted. Run remains authoritative."' in text


# ─────────────────────────────────────────────────────────────────────
# Acceptance 12: Operating preview stack remains unchanged.
# ─────────────────────────────────────────────────────────────────────
class TestOperatingPreviewStackUnchanged:
    def test_five_existing_preview_fields_still_echoed(self):
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

    def test_invalid_payload_still_returns_invalid_status(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview="nope"),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert resp.status_code == 200
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"

    def test_forbidden_project_still_returns_forbidden_status(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project="bogus-project-xyz"),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "forbidden-project"

    def test_response_top_level_keys_unchanged(self):
        """Top-level keys for a valid payload must remain exactly the
        16 keys PR25/26/27 shipped PLUS the new 'tax' top-level key
        introduced by C2-PR28/29/30 (PreviewContext + Registry +
        Tax preview stub). PR25 must not have changed any of the
        other 16 keys."""
        project_code = _create_user_project("top-level-keys")
        resp = client.post(
            "/model/preview",
            json=_valid_payload(
                project=project_code,
                capexTotalPreview=1.0,
                revenueTotalPreview=2.0,
                opexTotalPreview=3.0,
                ebitdaPreview=4.0,
                operatingCashFlowPreview=5.0,
            ),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        # The 'tax' top-level key was added by C2-PR28/29/30; the
        # 16 keys PR25/26/27 shipped are preserved unchanged.
        expected_keys = {
            "ok", "status", "executed", "accepted", "affectedGroups",
            "dirtyCells", "warnings", "message", "overview",
            "capex", "revenue", "opex", "ebitda", "operating_cash_flow",
            "debt",
            # C2-PR28/29/30 additive:
            "tax",
            # C2-PR31/32/33 additive:
            "irr",
            "dscr",
        }
        assert set(body.keys()) == expected_keys

    def test_debt_block_keys_unavailable_shape(self):
        """Unavailable debt block must have EXACTLY these 6 keys, in
        any order: status, senior_debt_preview, saved_total_capex,
        saved_gearing_pct, currency, basis."""
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=None),
            cookies=_auth_cookies(),
        )
        debt = resp.json()["debt"]
        assert set(debt.keys()) == {
            "status", "senior_debt_preview", "saved_total_capex",
            "saved_gearing_pct", "currency", "basis",
        }

    def test_debt_block_keys_ready_shape(self):
        """Ready debt block must have EXACTLY these 6 keys."""
        project_code = _create_user_project("ready-shape", total_capex_keur="50000.00", gearing_pct="70")
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=project_code),
            cookies=_auth_cookies(),
        )
        debt = resp.json()["debt"]
        assert set(debt.keys()) == {
            "status", "senior_debt_preview", "saved_total_capex",
            "saved_gearing_pct", "currency", "basis",
        }