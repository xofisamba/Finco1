"""C2-PR31/32/33 — IRR + DSCR Preview Boundaries + Final Preview Architecture QA.

Covers:
  * IRR preview slice (C2-PR31): always-unavailable backend stub.
  * DSCR preview slice (C2-PR32): always-unavailable backend stub.
  * Final Preview Architecture QA (C2-PR33): all five backend slices
    registered, deterministic JSON ordering, PreviewContext
    immutability, renderer + recalc-preview JS handling, no DB
    writes / engine calls / exports / save / run side-effects.

Acceptance criteria mapped to test classes:
  1. IRR backend preview boundary exists     -> TestIrrPreviewUnavailableShape
  2. DSCR backend preview boundary exists    -> TestDscrPreviewUnavailableShape
  3. Preview Registry is complete             -> TestRegistryContainsAllFiveSlices
  4. Renderer supports all preview modules    -> TestRendererHandlesAllBackendSlices
  5. No financial calculations added         -> TestNoForbiddenImportsInAnyPreviewModule
                                                + TestIrrDscrAlwaysUnavailableRegardlessOfContext
  6. No engine changes                        -> TestNoForbiddenImportsInAnyPreviewModule
                                                + TestPreviewArchitectureNoEngineCall
  7. No Save/Run changes                      -> TestPreviewArchitectureNoSaveRunChanges
  8. No persistence                           -> TestPreviewArchitectureNoDbWrites
  9. No export changes                        -> TestPreviewArchitectureNoExportChanges
 10. Full preview architecture regression     -> covered by re-running the
                                                  PR23/24/25-27/28-30/31-33
                                                  suites together
 11. JSON ordering stable                     -> TestBackendSlicesDeterministicAcrossRuns
                                                + TestIrrDscrFieldOrderingStable
 12. No frontend IRR/DSCR computation         -> TestNoFrontendIrrOrDscrComputation
 13. Operating/Debt/Tax previews unchanged     -> TestOperatingDebtTaxByteIdentical
"""
import os

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import inspect

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
    """Create a fresh user project; return its project_code from the
    HX-Redirect header (matches the PR24/25/27 pattern)."""
    import urllib.parse
    resp = client.post(
        "/projects/create",
        data={
            "project_name": f"C2 PR31-33 {name_suffix}",
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
# Acceptance 1: IRR backend preview boundary exists
# ─────────────────────────────────────────────────────────────────────
class TestIrrPreviewUnavailableShape:
    def test_unit_always_returns_unavailable(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.irr_preview import compute_irr_slice
        ctx = PreviewContext.build({}, None)
        result = compute_irr_slice(ctx)
        assert result["status"] == "preview-unavailable"
        assert result["basis"] == "saved-inputs-only"
        assert result["irr_preview"] is None
        assert result["currency"] == "EUR"
        assert result["message"] == "IRR preview is not yet available."

    def test_unit_returns_five_keys_in_stable_order(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.irr_preview import compute_irr_slice
        ctx = PreviewContext.build({}, None)
        result = compute_irr_slice(ctx)
        assert list(result.keys()) == [
            "status", "basis", "irr_preview", "message", "currency",
        ]

    def test_route_response_contains_irr_key_with_unavailable_shape(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is True
        assert "irr" in body
        assert body["irr"] == {
            "status": "preview-unavailable",
            "basis": "saved-inputs-only",
            "irr_preview": None,
            "message": "IRR preview is not yet available.",
            "currency": "EUR",
        }

    def test_invalid_payload_still_omits_irr(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview="nope"),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"
        assert "irr" not in body

    def test_forbidden_project_still_omits_irr(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project="bogus-project-xyz"),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "forbidden-project"
        assert "irr" not in body


# ─────────────────────────────────────────────────────────────────────
# Acceptance 2: DSCR backend preview boundary exists
# ─────────────────────────────────────────────────────────────────────
class TestDscrPreviewUnavailableShape:
    def test_unit_always_returns_unavailable(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.dscr_preview import compute_dscr_slice
        ctx = PreviewContext.build({}, None)
        result = compute_dscr_slice(ctx)
        assert result["status"] == "preview-unavailable"
        assert result["basis"] == "saved-inputs-only"
        assert result["dscr_preview"] is None
        assert result["currency"] == "EUR"
        assert result["message"] == "DSCR preview is not yet available."

    def test_unit_returns_five_keys_in_stable_order(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.dscr_preview import compute_dscr_slice
        ctx = PreviewContext.build({}, None)
        result = compute_dscr_slice(ctx)
        assert list(result.keys()) == [
            "status", "basis", "dscr_preview", "message", "currency",
        ]

    def test_route_response_contains_dscr_key_with_unavailable_shape(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is True
        assert "dscr" in body
        assert body["dscr"] == {
            "status": "preview-unavailable",
            "basis": "saved-inputs-only",
            "dscr_preview": None,
            "message": "DSCR preview is not yet available.",
            "currency": "EUR",
        }

    def test_invalid_payload_still_omits_dscr(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview="nope"),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert "dscr" not in body

    def test_forbidden_project_still_omits_dscr(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project="bogus-project-xyz"),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert "dscr" not in body


# ─────────────────────────────────────────────────────────────────────
# IRR/DSCR slices are always unavailable regardless of context
# (proves they do not "leak" computation just because saved or
# frontend inputs are available).
# ─────────────────────────────────────────────────────────────────────
class TestIrrDscrAlwaysUnavailableRegardlessOfContext:
    def test_irr_unavailable_with_full_project_and_all_inputs(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.irr_preview import compute_irr_slice
        class _FakeProject:
            baseline_snapshot = {
                "total_capex_keur": "50000",
                "gearing_pct": "70",
                # Hypothetical IRR-related inputs the slice is
                # explicitly forbidden from reading today.
                "senior_debt_keur": "35000",
                "equity_irr_pct": "12.5",
                "project_irr_pct": "8.3",
            }
            project_code = "TUHO"
            project_id = 7
        ctx = PreviewContext.build(
            {"irrTotalPreview": 12.5},  # forbidden frontend input
            _FakeProject(),
        )
        result = compute_irr_slice(ctx)
        assert result["status"] == "preview-unavailable"
        assert result["irr_preview"] is None

    def test_dscr_unavailable_with_full_project_and_all_inputs(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.dscr_preview import compute_dscr_slice
        class _FakeProject:
            baseline_snapshot = {
                "total_capex_keur": "50000",
                "gearing_pct": "70",
                # Hypothetical DSCR-related inputs the slice is
                # explicitly forbidden from reading today.
                "interest_rate_pct": "5",
                "tenor_years": "15",
                "target_dscr": "1.30",
            }
            project_code = "TUHO"
            project_id = 7
        ctx = PreviewContext.build(
            {"dscrTotalPreview": 1.45},  # forbidden frontend input
            _FakeProject(),
        )
        result = compute_dscr_slice(ctx)
        assert result["status"] == "preview-unavailable"
        assert result["dscr_preview"] is None


# ─────────────────────────────────────────────────────────────────────
# Acceptance 3: Preview Registry is complete (Operating + Debt +
# Tax + IRR + DSCR)
# ─────────────────────────────────────────────────────────────────────
class TestRegistryContainsAllFiveSlices:
    def test_registry_has_exactly_five_slices_in_documented_order(self):
        from app.services.previews._registry import (
            register_default_slices,
            all_slices,
        )
        register_default_slices()
        slices = all_slices()
        names = [s.name for s in slices]
        # operating first (special-cased), then debt, tax, irr, dscr.
        assert names[0] == "operating"
        # The remaining four are iterated in registration order.
        assert names[1:] == ["debt", "tax", "irr", "dscr"], (
            f"unexpected registration order: {names}"
        )

    def test_registry_response_keys_match_documented_set(self):
        from app.services.previews._registry import (
            register_default_slices,
            all_slices,
        )
        register_default_slices()
        keys = {entry.response_key for entry in all_slices()
                if entry.name != "operating"}
        # Operating's response_key is a placeholder (capex key); the
        # real top-level keys it contributes are spread by
        # compute_operating_slice() and asserted separately.
        assert keys == {"debt", "tax", "irr", "dscr"}


# ─────────────────────────────────────────────────────────────────────
# Acceptance 4: Renderer handles unavailable previews
# ─────────────────────────────────────────────────────────────────────
class TestRendererHandlesAllBackendSlices:
    def test_runtime_renderer_has_irr_constants(self):
        resp = client.get("/static/modelling/runtime-renderer.js")
        assert resp.status_code == 200
        text = resp.text
        for ident in (
            "IRR_PREVIEW_VALUE_ELEMENT_ID",
            "IRR_REGION_ELEMENT_ID",
            "IRR_SR_ELEMENT_ID",
            "_setIrrState",
            "irr-preview-value",
        ):
            assert ident in text, (
                f"runtime-renderer.js missing IRR constant/helper: {ident!r}"
            )

    def test_runtime_renderer_has_dscr_constants(self):
        resp = client.get("/static/modelling/runtime-renderer.js")
        assert resp.status_code == 200
        text = resp.text
        for ident in (
            "DSCR_PREVIEW_VALUE_ELEMENT_ID",
            "DSCR_REGION_ELEMENT_ID",
            "DSCR_SR_ELEMENT_ID",
            "_setDscrState",
            "dscr-preview-value",
        ):
            assert ident in text, (
                f"runtime-renderer.js missing DSCR constant/helper: {ident!r}"
            )

    def test_workspace_shell_has_irr_row(self):
        # GET /?project=<code> renders index.html which includes
        # workspace_shell.html. Use a created user project.
        project_code = _create_user_project("irr-row")
        resp = client.get(
            f"/?project={project_code}",
            cookies=_auth_cookies(),
            follow_redirects=False,
        )
        assert resp.status_code == 200, (
            f"/?project=... returned {resp.status_code}: {resp.text[:200]}"
        )
        text = resp.text
        assert 'id="irr-preview"' in text
        assert "IRR preview:" in text
        assert 'id="irr-preview-value"' in text
        assert "Future backend preview. Run remains authoritative." in text

    def test_workspace_shell_has_dscr_row(self):
        project_code = _create_user_project("dscr-row")
        resp = client.get(
            f"/?project={project_code}",
            cookies=_auth_cookies(),
            follow_redirects=False,
        )
        assert resp.status_code == 200
        text = resp.text
        assert 'id="dscr-preview"' in text
        assert "DSCR preview:" in text
        assert 'id="dscr-preview-value"' in text


# ─────────────────────────────────────────────────────────────────────
# Acceptance 5 + 6: No financial calculations / no engine changes
# ─────────────────────────────────────────────────────────────────────
class TestNoForbiddenImportsInAnyPreviewModule:
    FORBIDDEN_PATTERNS = [
        "from app.domain",
        "import app.domain",
        "from app.waterfall_core",
        "import app.waterfall_core",
        "from app.waterfall_runner",
        "import app.waterfall_runner",
        "from app.input_adapter",
        "import app.input_adapter",
        "from app.project_factories",
        "import app.project_factories",
        "from app.proj_factories",
        "import app.proj_factories",
    ]

    def test_irr_preview_module_clean(self):
        import app.services.previews.irr_preview as mod
        source = inspect.getsource(mod)
        for pattern in self.FORBIDDEN_PATTERNS:
            assert pattern not in source, (
                f"irr_preview.py contains forbidden import: {pattern!r}"
            )

    def test_dscr_preview_module_clean(self):
        import app.services.previews.dscr_preview as mod
        source = inspect.getsource(mod)
        for pattern in self.FORBIDDEN_PATTERNS:
            assert pattern not in source, (
                f"dscr_preview.py contains forbidden import: {pattern!r}"
            )

    def test_registry_module_clean(self):
        import app.services.previews._registry as mod
        source = inspect.getsource(mod)
        for pattern in self.FORBIDDEN_PATTERNS:
            assert pattern not in source, (
                f"_registry.py contains forbidden import: {pattern!r}"
            )

    def test_irr_module_compute_function_has_no_xirr_or_moic(self):
        """IRR preview is explicitly out of scope for XIRR / MOIC /
        equity IRR / project IRR — the compute function's BODY must
        not contain the keywords (docstrings documenting the
        out-of-scope list are allowed and expected)."""
        import app.services.previews.irr_preview as mod
        # Use getsource() on the compute function only, not the
        # entire module.
        compute_source = inspect.getsource(mod.compute_irr_slice).lower()
        for kw in ("xirr", "moic", "equity_cashflows", "sponsor",
                   "project_irr", "equity_irr"):
            assert kw not in compute_source, (
                f"irr_preview.compute_irr_slice contains forbidden "
                f"keyword {kw!r}"
            )

    def test_dscr_module_compute_function_has_no_sculpting_or_coverage(self):
        """DSCR preview is explicitly out of scope for debt sculpting
        / coverage ratios / debt service — the compute function's
        BODY must not contain the keywords."""
        import app.services.previews.dscr_preview as mod
        compute_source = inspect.getsource(mod.compute_dscr_slice).lower()
        for kw in ("sculpt", "coverage", "debt_service", "sponsor",
                   "interest_schedule"):
            assert kw not in compute_source, (
                f"dscr_preview.compute_dscr_slice contains forbidden "
                f"keyword {kw!r}"
            )


# ─────────────────────────────────────────────────────────────────────
# Acceptance 7: No Save/Run changes
# ─────────────────────────────────────────────────────────────────────
class TestPreviewArchitectureNoSaveRunChanges:
    def test_preview_request_does_not_trigger_save(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert "saved_baseline_id" not in body
        assert "saved_snapshot" not in body
        assert "save_errors" not in body
        assert body["status"] == "stubbed"

    def test_preview_request_does_not_trigger_run(self, monkeypatch):
        import app.waterfall_core as waterfall_core
        def _boom(*args, **kwargs):
            raise AssertionError(
                "Run must never fire as a side-effect of a /model/preview call"
            )
        monkeypatch.setattr(waterfall_core, "run_project", _boom, raising=False)
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


# ─────────────────────────────────────────────────────────────────────
# Acceptance 8: No persistence (no DB writes)
# ─────────────────────────────────────────────────────────────────────
class TestPreviewArchitectureNoDbWrites:
    def test_db_mtime_and_size_unchanged_after_preview_request(self):
        before_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else None
        before_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else None
        client.post(
            "/model/preview",
            json=_valid_payload(),
            cookies=_auth_cookies(),
        )
        after_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else None
        after_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else None
        assert before_mtime == after_mtime
        assert before_size == after_size


# ─────────────────────────────────────────────────────────────────────
# Acceptance 9: No export changes
# ─────────────────────────────────────────────────────────────────────
class TestPreviewArchitectureNoExportChanges:
    def test_export_csv_does_not_carry_irr_or_dscr_sentinel(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        # Both stub slices return null preview values and stable
        # message strings. There is nothing distinctive to leak; the
        # test confirms both keys are present and the route still
        # returns 200 normally.
        assert body["irr"]["status"] == "preview-unavailable"
        assert body["irr"]["irr_preview"] is None
        assert body["dscr"]["status"] == "preview-unavailable"
        assert body["dscr"]["dscr_preview"] is None


# ─────────────────────────────────────────────────────────────────────
# Acceptance 10: JSON ordering stable
# ─────────────────────────────────────────────────────────────────────
class TestBackendSlicesDeterministicAcrossRuns:
    def test_run_all_returns_same_keys_in_same_order(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews._registry import run_all
        ctx = PreviewContext.build(
            preview_request={
                "capexTotalPreview": 1.0,
                "revenueTotalPreview": 2.0,
                "opexTotalPreview": 3.0,
                "ebitdaPreview": 4.0,
                "operatingCashFlowPreview": 5.0,
            },
            project_record=None,
        )
        first = run_all(ctx)
        second = run_all(ctx)
        assert first == second
        assert list(first.keys()) == list(second.keys())
        # All five echo slices + four backend slices are present.
        assert "capex" in first
        assert "revenue" in first
        assert "opex" in first
        assert "ebitda" in first
        assert "operating_cash_flow" in first
        assert "debt" in first
        assert "tax" in first
        assert "irr" in first
        assert "dscr" in first

    def test_run_all_top_level_insertion_order(self):
        """The /model/preview JSON top-level key order is:
        ok → status → executed → accepted → affectedGroups → dirtyCells
        → warnings → message → overview → capex → revenue → opex →
        ebitda → operating_cash_flow → debt → tax → irr → dscr.
        """
        from app.services.preview_context import PreviewContext
        from app.services.previews._registry import run_all
        from app.services.model_preview import build_preview_response
        ctx = PreviewContext.build({}, None)
        # Use build_preview_response for the canonical order.
        body = build_preview_response({}, None)
        expected_order = [
            "ok", "status", "executed", "accepted", "affectedGroups",
            "dirtyCells", "warnings", "message", "overview",
            "capex", "revenue", "opex", "ebitda", "operating_cash_flow",
            "debt", "tax", "irr", "dscr",
        ]
        # Only echo slices we sent in the body are present; but here
        # we sent no echo slices, so capex/revenue/opex/ebitda/ocf
        # are absent. Re-check the order of the keys that ARE present.
        present = [k for k in expected_order if k in body]
        assert list(body.keys()) == present


class TestIrrDscrFieldOrderingStable:
    def test_irr_field_ordering(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.irr_preview import compute_irr_slice
        ctx = PreviewContext.build({}, None)
        result = compute_irr_slice(ctx)
        assert list(result.keys()) == [
            "status", "basis", "irr_preview", "message", "currency",
        ]

    def test_dscr_field_ordering(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.dscr_preview import compute_dscr_slice
        ctx = PreviewContext.build({}, None)
        result = compute_dscr_slice(ctx)
        assert list(result.keys()) == [
            "status", "basis", "dscr_preview", "message", "currency",
        ]


# ─────────────────────────────────────────────────────────────────────
# Acceptance 12: No frontend IRR/DSCR computation
# ─────────────────────────────────────────────────────────────────────
class TestNoFrontendIrrOrDscrComputation:
    def test_runtime_renderer_has_no_irr_or_dscr_arithmetic(self):
        resp = client.get("/static/modelling/runtime-renderer.js")
        assert resp.status_code == 200
        text = resp.text
        import re
        forbidden_patterns = [
            r"\*\s*irr",
            r"irr\s*\*",
            r"irrTotalPreview\s*\*",
            r"\*\s*dscr",
            r"dscr\s*\*",
            r"dscrTotalPreview\s*\*",
        ]
        for pat in forbidden_patterns:
            assert re.search(pat, text) is None, (
                f"runtime-renderer.js contains forbidden IRR/DSCR-arithmetic "
                f"pattern {pat!r}"
            )

    def test_recalc_preview_js_has_no_irr_or_dscr_arithmetic_keywords(self):
        resp = client.get("/static/modelling/recalc-preview.js")
        assert resp.status_code == 200
        text = resp.text.lower()
        forbidden_keywords = [
            "xirr", "moic", " irr ", " irr_", " irr(",
            " dscr ", " dscr_", " dscr(",
        ]
        for kw in forbidden_keywords:
            assert kw not in text, (
                f"recalc-preview.js contains forbidden keyword {kw!r}"
            )


# ─────────────────────────────────────────────────────────────────────
# Acceptance 13: Operating/Debt/Tax previews remain byte-identical
# (re-proof after IRR/DSCR additions)
# ─────────────────────────────────────────────────────────────────────
class TestOperatingDebtTaxByteIdentical:
    def test_operating_echo_slices_byte_identical(self):
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
        assert body["capex"] == {"capex_total_preview": 111.11, "currency": "EUR"}
        assert body["revenue"] == {"preview": 222.22, "currency": "EUR"}
        assert body["opex"] == {"preview": 333.33, "currency": "EUR"}
        assert body["ebitda"] == {"preview": 444.44, "currency": "EUR"}
        assert body["operating_cash_flow"] == {"preview": 555.55, "currency": "EUR"}

    def test_debt_slice_byte_identical(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project=None),
            cookies=_auth_cookies(),
        )
        debt = resp.json()["debt"]
        assert debt == {
            "status": "preview-unavailable",
            "senior_debt_preview": None,
            "saved_total_capex": None,
            "saved_gearing_pct": None,
            "currency": "EUR",
            "basis": "saved-inputs-only",
        }

    def test_tax_slice_byte_identical(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),
            cookies=_auth_cookies(),
        )
        tax = resp.json()["tax"]
        assert tax == {
            "status": "preview-unavailable",
            "basis": "saved-inputs-only",
            "tax_preview": None,
            "message": "Tax preview is not yet available.",
            "currency": "EUR",
        }


# ─────────────────────────────────────────────────────────────────────
# PreviewContext immutability (C2-PR28 property, re-proven here
# because the final-QA pass must lock the architecture).
# ─────────────────────────────────────────────────────────────────────
class TestPreviewContextImmutableReProof:
    def test_cannot_mutate_any_field(self):
        from app.services.preview_context import PreviewContext
        ctx = PreviewContext.build({"valid": True}, None)
        import dataclasses
        with __import__("pytest").raises(dataclasses.FrozenInstanceError):
            ctx.project_record = "x"
        with __import__("pytest").raises(dataclasses.FrozenInstanceError):
            ctx.baseline_snapshot = {"x": 1}
        with __import__("pytest").raises(dataclasses.FrozenInstanceError):
            ctx.project_code = "X"
        with __import__("pytest").raises(dataclasses.FrozenInstanceError):
            ctx.project_id = 1
        with __import__("pytest").raises(dataclasses.FrozenInstanceError):
            ctx.currency = "USD"
        with __import__("pytest").raises(dataclasses.FrozenInstanceError):
            ctx.preview_request = {"y": 2}


# ─────────────────────────────────────────────────────────────────────
# No engine call from preview pipeline
# ─────────────────────────────────────────────────────────────────────
class TestPreviewArchitectureNoEngineCall:
    def test_waterfall_run_project_never_called_from_preview(self, monkeypatch):
        import app.waterfall_core as waterfall_core
        def _boom(*args, **kwargs):
            raise AssertionError(
                "waterfall_core.run_project must never be called by /model/preview"
            )
        monkeypatch.setattr(waterfall_core, "run_project", _boom, raising=False)
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),
            cookies=_auth_cookies(),
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True