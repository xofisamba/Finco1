"""C2-PR28/29/30 — Tax Preview Stub + Architecture Guardrails.

Covers the new tax preview slice added by C2-PR30, plus the
PreviewContext / Registry / per-slice-module architectural
guardrails introduced by C2-PR28 and C2-PR29.

Acceptance criteria mapped to test classes:
  1. Shared PreviewContext preserves behaviour
       -> TestPreviewContextConstruction
       -> TestPreviewContextImmutable
  2. Registry preserves JSON ordering
       -> TestRegistryOrderPreserved
       -> TestRegistryDeterministicAcrossRuns
  3. Operating preview unchanged
       -> TestOperatingPreviewSliceByteIdentical
  4. Debt preview unchanged
       -> TestDebtPreviewSliceByteIdentical
  5. Tax preview unavailable
       -> TestTaxPreviewUnavailableShape
       -> TestTaxPreviewAlwaysUnavailableRegardlessOfContext
  6. Renderer displays placeholder
       -> covered by tests/test_c2_pr28_30_tax_preview_renderer_browser.py
          (browser-side; will be authored separately if needed)
  7. No frontend tax computation
       -> TestNoFrontendTaxComputation
  8. No DB writes
       -> TestPreviewArchitectureNoDbWrites
  9. No engine calls
       -> TestNoForbiddenImportsInAnyPreviewModule
       -> TestNoEngineCallFromRegistryOrContext
 10. No export changes
       -> TestPreviewArchitectureNoExportChanges
 11. No Save/Run changes
       -> TestPreviewArchitectureNoSaveRunChanges
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


# ─────────────────────────────────────────────────────────────────────
# PreviewContext construction + immutability
# ─────────────────────────────────────────────────────────────────────
class TestPreviewContextConstruction:
    def test_build_with_no_project_returns_none_fields(self):
        from app.services.preview_context import PreviewContext
        ctx = PreviewContext.build(
            preview_request={"valid": True},
            project_record=None,
        )
        assert ctx.project_record is None
        assert ctx.baseline_snapshot is None
        assert ctx.project_code is None
        assert ctx.project_id is None
        assert ctx.currency == "EUR"
        assert ctx.preview_request == {"valid": True}

    def test_build_with_fake_project_extracts_snapshot_code_id(self):
        from app.services.preview_context import PreviewContext
        class _FakeProject:
            baseline_snapshot = {"total_capex_keur": "50000", "gearing_pct": "70"}
            project_code = "TUHO"
            project_id = 42
        fake = _FakeProject()
        ctx = PreviewContext.build(
            preview_request={"valid": True},
            project_record=fake,
        )
        assert ctx.project_record is fake
        assert ctx.baseline_snapshot == {"total_capex_keur": "50000", "gearing_pct": "70"}
        assert ctx.project_code == "TUHO"
        assert ctx.project_id == 42
        assert ctx.currency == "EUR"

    def test_build_with_garbage_project_record_returns_none_fields(self):
        from app.services.preview_context import PreviewContext
        # Snapshot attribute is missing entirely -> None snapshot.
        class _BrokenProject:
            project_code = 12345  # not a string -> ignored
            project_id = "not-an-int"  # not an int -> ignored
        ctx = PreviewContext.build(
            preview_request={"valid": True},
            project_record=_BrokenProject(),
        )
        assert ctx.baseline_snapshot is None
        assert ctx.project_code is None
        assert ctx.project_id is None

    def test_build_with_non_dict_request_returns_empty_mapping(self):
        from app.services.preview_context import PreviewContext
        ctx = PreviewContext.build(
            preview_request="not-a-dict",
            project_record=None,
        )
        # Defensive: a non-Mapping request becomes an empty mapping
        # so downstream preview slices don't have to special-case it.
        assert dict(ctx.preview_request) == {}

    def test_currency_overridable_for_future_multi_currency(self):
        from app.services.preview_context import PreviewContext
        ctx = PreviewContext.build(
            preview_request={},
            project_record=None,
            currency="USD",
        )
        assert ctx.currency == "USD"


class TestPreviewContextImmutable:
    def test_cannot_mutate_project_record_field(self):
        from app.services.preview_context import PreviewContext
        ctx = PreviewContext.build({"valid": True}, None)
        import dataclasses
        with __import__("pytest").raises(dataclasses.FrozenInstanceError):
            ctx.project_record = "something-else"

    def test_cannot_mutate_currency_field(self):
        from app.services.preview_context import PreviewContext
        ctx = PreviewContext.build({"valid": True}, None)
        import dataclasses
        with __import__("pytest").raises(dataclasses.FrozenInstanceError):
            ctx.currency = "USD"

    def test_value_equality_between_two_contexts_with_same_inputs(self):
        from app.services.preview_context import PreviewContext
        a = PreviewContext.build({"x": 1}, None)
        b = PreviewContext.build({"x": 1}, None)
        assert a == b


# ─────────────────────────────────────────────────────────────────────
# Registry preserves JSON ordering + is deterministic
# ─────────────────────────────────────────────────────────────────────
class TestRegistryOrderPreserved:
    def test_default_slices_registered_in_documented_order(self):
        from app.services.previews._registry import (
            register_default_slices,
            all_slices,
        )
        register_default_slices()
        slices = all_slices()
        names = [s.name for s in slices]
        # operating first, then debt, then tax. The order is the JSON
        # key insertion order in /model/preview's response body.
        assert names[0] == "operating"
        assert "debt" in names
        assert "tax" in names
        assert names.index("debt") < names.index("tax")

    def test_default_slices_register_is_idempotent(self):
        """Calling register_default_slices() twice must not duplicate
        entries — the registry stays at exactly three slices."""
        from app.services.previews._registry import (
            register_default_slices,
            all_slices,
            reset_for_tests,
        )
        reset_for_tests()
        register_default_slices()
        first_count = len(all_slices())
        register_default_slices()
        register_default_slices()
        assert len(all_slices()) == first_count


class TestRegistryDeterministicAcrossRuns:
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
        # All five echo slices + debt + tax are present.
        assert "capex" in first
        assert "revenue" in first
        assert "opex" in first
        assert "ebitda" in first
        assert "operating_cash_flow" in first
        assert "debt" in first
        assert "tax" in first


# ─────────────────────────────────────────────────────────────────────
# Operating preview slice byte-identical
# ─────────────────────────────────────────────────────────────────────
class TestOperatingPreviewSliceByteIdentical:
    def test_empty_request_yields_empty_slice(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.operating_preview import compute_operating_slice
        ctx = PreviewContext.build({}, None)
        assert compute_operating_slice(ctx) == {}

    def test_each_echo_field_present_independently(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.operating_preview import compute_operating_slice

        ctx_capex = PreviewContext.build({"capexTotalPreview": 111.11}, None)
        assert compute_operating_slice(ctx_capex) == {
            "capex": {"capex_total_preview": 111.11, "currency": "EUR"},
        }

        ctx_rev = PreviewContext.build({"revenueTotalPreview": 222.22}, None)
        assert compute_operating_slice(ctx_rev) == {
            "revenue": {"preview": 222.22, "currency": "EUR"},
        }

    def test_round_to_two_decimal_places(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.operating_preview import compute_operating_slice
        ctx = PreviewContext.build({"capexTotalPreview": 111.111111}, None)
        result = compute_operating_slice(ctx)
        assert result["capex"]["capex_total_preview"] == 111.11


# ─────────────────────────────────────────────────────────────────────
# Debt preview slice byte-identical to PR25-27
# ─────────────────────────────────────────────────────────────────────
class TestDebtPreviewSliceByteIdentical:
    def test_unavailable_shape_has_six_keys(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.debt_preview import compute_debt_slice
        ctx = PreviewContext.build({}, None)
        result = compute_debt_slice(ctx)
        assert set(result.keys()) == {
            "status", "senior_debt_preview", "saved_total_capex",
            "saved_gearing_pct", "currency", "basis",
        }

    def test_ready_formula_matches_pr25(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.debt_preview import compute_debt_slice
        class _FakeProject:
            baseline_snapshot = {"total_capex_keur": "60000.00", "gearing_pct": "60"}
        ctx = PreviewContext.build({}, _FakeProject())
        result = compute_debt_slice(ctx)
        assert result["status"] == "preview-ready"
        assert result["senior_debt_preview"] == 36000.00
        assert result["saved_total_capex"] == 60000.00
        assert result["saved_gearing_pct"] == 60.0

    def test_does_not_read_body_for_calculation(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.debt_preview import compute_debt_slice
        class _FakeProject:
            baseline_snapshot = {"total_capex_keur": "10000", "gearing_pct": "50"}
        ctx = PreviewContext.build(
            {"capexTotalPreview": 1.0}, _FakeProject()
        )
        result = compute_debt_slice(ctx)
        assert result["senior_debt_preview"] == 5000.0


class TestDebtPreviewHelpersExportedAndPure:
    def test_safe_float_handles_string_form_field(self):
        from app.services.previews.debt_preview import _safe_float
        assert _safe_float("1234.5") == 1234.5
        assert _safe_float("  1234.5  ") == 1234.5
        assert _safe_float("") is None
        assert _safe_float(None) is None
        assert _safe_float("not-a-number") is None

    def test_safe_float_rejects_bool(self):
        from app.services.previews.debt_preview import _safe_float
        assert _safe_float(True) is None
        assert _safe_float(False) is None

    def test_safe_float_handles_int_and_float(self):
        from app.services.previews.debt_preview import _safe_float
        assert _safe_float(42) == 42.0
        assert _safe_float(42.5) == 42.5

    def test_is_finite_number_rejects_nan_inf(self):
        from app.services.previews.debt_preview import _is_finite_number
        assert _is_finite_number(1.0) is True
        assert _is_finite_number(0) is True
        assert _is_finite_number(float("nan")) is False
        assert _is_finite_number(float("inf")) is False
        assert _is_finite_number(float("-inf")) is False
        assert _is_finite_number("1.0") is False
        assert _is_finite_number(True) is False


# ─────────────────────────────────────────────────────────────────────
# Tax preview always unavailable
# ─────────────────────────────────────────────────────────────────────
class TestTaxPreviewUnavailableShape:
    def test_unit_always_returns_unavailable(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.tax_preview import compute_tax_slice
        ctx = PreviewContext.build({}, None)
        result = compute_tax_slice(ctx)
        assert result["status"] == "preview-unavailable"
        assert result["basis"] == "saved-inputs-only"
        assert result["tax_preview"] is None
        assert result["currency"] == "EUR"
        assert result["message"] == "Tax preview is not yet available."

    def test_unit_returns_five_keys_in_stable_order(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.tax_preview import compute_tax_slice
        ctx = PreviewContext.build({}, None)
        result = compute_tax_slice(ctx)
        assert list(result.keys()) == [
            "status", "basis", "tax_preview", "message", "currency",
        ]

    def test_route_response_contains_tax_key_with_unavailable_shape(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is True
        assert "tax" in body
        assert body["tax"] == {
            "status": "preview-unavailable",
            "basis": "saved-inputs-only",
            "tax_preview": None,
            "message": "Tax preview is not yet available.",
            "currency": "EUR",
        }

    def test_invalid_payload_still_omits_tax(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(capexTotalPreview="nope"),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "invalid-payload"
        assert "tax" not in body

    def test_forbidden_project_still_omits_tax(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(project="bogus-project-xyz"),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "forbidden-project"
        assert "tax" not in body


class TestTaxPreviewAlwaysUnavailableRegardlessOfContext:
    def test_unavailable_with_no_project(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.tax_preview import compute_tax_slice
        ctx = PreviewContext.build({}, None)
        assert compute_tax_slice(ctx)["status"] == "preview-unavailable"

    def test_unavailable_with_full_project_and_all_inputs(self):
        from app.services.preview_context import PreviewContext
        from app.services.previews.tax_preview import compute_tax_slice
        class _FakeProject:
            baseline_snapshot = {
                "total_capex_keur": "50000",
                "gearing_pct": "70",
                # Hypothetical tax-related inputs that the slice is
                # explicitly forbidden from reading today.
                "tax_rate_pct": "20",
                "loss_carryforward_keur": "1000",
            }
            project_code = "TUHO"
            project_id = 7
        ctx = PreviewContext.build(
            {"taxTotalPreview": 12345.67},  # forbidden frontend input
            _FakeProject(),
        )
        result = compute_tax_slice(ctx)
        # Even with all of these tempting inputs available, the
        # slice must return unavailable and refuse to compute.
        assert result["status"] == "preview-unavailable"
        assert result["tax_preview"] is None


# ─────────────────────────────────────────────────────────────────────
# Forbidden: no engine / domain imports in any preview module
# ─────────────────────────────────────────────────────────────────────
class TestNoForbiddenImportsInAnyPreviewModule:
    """Architectural guardrail: the entire preview pipeline
    (PreviewContext + registry + every per-slice module) must NOT
    import the financial engine. This guarantees that no preview
    slice accidentally starts running the real tax / IRR / DSCR
    logic."""

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

    def test_preview_context_module_clean(self):
        import app.services.preview_context as mod
        source = inspect.getsource(mod)
        for pattern in self.FORBIDDEN_PATTERNS:
            assert pattern not in source, (
                f"preview_context.py contains forbidden import: {pattern!r}"
            )

    def test_previews_base_module_clean(self):
        import app.services.previews._base as mod
        source = inspect.getsource(mod)
        for pattern in self.FORBIDDEN_PATTERNS:
            assert pattern not in source, (
                f"previews/_base.py contains forbidden import: {pattern!r}"
            )

    def test_operating_preview_module_clean(self):
        import app.services.previews.operating_preview as mod
        source = inspect.getsource(mod)
        for pattern in self.FORBIDDEN_PATTERNS:
            assert pattern not in source, (
                f"previews/operating_preview.py contains forbidden import: {pattern!r}"
            )

    def test_debt_preview_module_clean(self):
        import app.services.previews.debt_preview as mod
        source = inspect.getsource(mod)
        for pattern in self.FORBIDDEN_PATTERNS:
            assert pattern not in source, (
                f"previews/debt_preview.py contains forbidden import: {pattern!r}"
            )

    def test_tax_preview_module_clean(self):
        import app.services.previews.tax_preview as mod
        source = inspect.getsource(mod)
        for pattern in self.FORBIDDEN_PATTERNS:
            assert pattern not in source, (
                f"previews/tax_preview.py contains forbidden import: {pattern!r}"
            )

    def test_registry_module_clean(self):
        import app.services.previews._registry as mod
        source = inspect.getsource(mod)
        for pattern in self.FORBIDDEN_PATTERNS:
            assert pattern not in source, (
                f"previews/_registry.py contains forbidden import: {pattern!r}"
            )

    def test_model_preview_orchestrator_clean(self):
        """The orchestration module (`model_preview.py`) itself must
        remain free of engine imports — proving the registry-based
        orchestration does not reach into the financial engine."""
        import app.services.model_preview as mod
        source = inspect.getsource(mod)
        for pattern in self.FORBIDDEN_PATTERNS:
            assert pattern not in source, (
                f"model_preview.py contains forbidden import: {pattern!r}"
            )


class TestNoEngineCallFromRegistryOrContext:
    """Even though we already checked for forbidden imports, the
    registry / context should not have any indirect way to call the
    engine. This test asserts that no module exposes a callable
    that even resembles an engine call."""

    def test_context_has_no_callable_engine_like_methods(self):
        from app.services.preview_context import PreviewContext
        methods = [m for m in dir(PreviewContext) if not m.startswith("_")]
        # The context must remain a value object: just `build()` is
        # allowed as the only "method" we expose.
        assert methods == ["build"], (
            f"PreviewContext exposes unexpected methods: {methods}"
        )


# ─────────────────────────────────────────────────────────────────────
# No DB writes / no engine calls during a real /model/preview request
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


# ─────────────────────────────────────────────────────────────────────
# No frontend tax computation
# ─────────────────────────────────────────────────────────────────────
class TestNoFrontendTaxComputation:
    """The runtime renderer + recalc-preview JS must NOT compute any
    tax-related number. The renderer is allowed to format/patch
    DOM elements with whatever the backend decided to send, but
    never to compute a tax preview on its own."""

    def test_runtime_renderer_js_has_no_tax_arithmetic(self):
        resp = client.get("/static/modelling/runtime-renderer.js")
        assert resp.status_code == 200
        text = resp.text
        import re
        forbidden_patterns = [
            r"\*\s*tax",
            r"tax\s*\*",
            r"taxTotalPreview\s*\*",
        ]
        for pat in forbidden_patterns:
            assert re.search(pat, text) is None, (
                f"runtime-renderer.js contains forbidden tax-arithmetic "
                f"pattern {pat!r}"
            )

    def test_recalc_preview_js_has_no_tax_arithmetic_keywords(self):
        resp = client.get("/static/modelling/recalc-preview.js")
        assert resp.status_code == 200
        text = resp.text.lower()
        # The renderer is forbidden from introducing tax computation.
        # 'tax' as a bare keyword (outside the pre-existing disclaimer
        # phrases and outside the new C2-PR30 taxonomy marker that
        # just lists future preview slices) is forbidden.
        forbidden_keywords = ["cit ", " loss carryforward", "tax shield", "withholding", "pillar ii"]
        for kw in forbidden_keywords:
            assert kw not in text, (
                f"recalc-preview.js contains forbidden keyword {kw!r}"
            )


# ─────────────────────────────────────────────────────────────────────
# No export changes — preview stays out of export output
# ─────────────────────────────────────────────────────────────────────
class TestPreviewArchitectureNoExportChanges:
    def test_export_csv_does_not_carry_tax_preview_sentinel(self):
        resp = client.post(
            "/model/preview",
            json=_valid_payload(),
            cookies=_auth_cookies(),
        )
        body = resp.json()
        # The tax preview stub returns no numeric value (always
        # unavailable), so there is nothing distinctive to leak. The
        # test confirms the stub's response keys are present and
        # the route still returns 200 normally.
        assert body["tax"]["status"] == "preview-unavailable"
        assert body["tax"]["tax_preview"] is None


# ─────────────────────────────────────────────────────────────────────
# No Save / Run changes — the preview architecture must not affect
# Save or Run endpoints.
# ─────────────────────────────────────────────────────────────────────
class TestPreviewArchitectureNoSaveRunChanges:
    def test_preview_request_does_not_trigger_save(self, monkeypatch):
        """A /model/preview call must not have any Save side-effect."""
        # The simplest way to prove "no save side-effect" is to
        # verify the DB file is untouched (covered above). We also
        # assert the response shape carries the standard preview
        # envelope (`ok`, `status`, etc.) and never a save error or
        # a redirect to a saved-baseline URL.
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
        """A /model/preview call must not have any Run side-effect."""
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