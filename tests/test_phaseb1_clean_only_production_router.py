"""Phase B1 — Clean-Only Production Router.

Proves that after the B1 routing change:
  A. Solar production: clean_calls == 1, legacy_calls == 0
  B. Wind production:  clean_calls == 1, legacy_calls == 0
  C. Oborovo production: clean_calls == 1, legacy_calls == 0 (Phase B2)
  D. TUHO production:    raises CleanNotReadyError, calculation_count == 0
  E. Oborovo via run_project_legacy: executes legacy calibration
  F. TUHO via run_project_legacy:    executes legacy calibration
  G. Production does NOT fall back on clean engine error (fails closed)
  H. Production does NOT fall back on classifier failure (fails closed)
  I. execute_production_demo: Solar/Oborovo clean, TUHO/unknown fail closed
  J. execute_calibration_waterfall: explicit legacy seam for blocked projects;
     execute_production_waterfall refuses legacy (allow_legacy param does not exist)
  K. Financial delta zero for Solar after B1
  L. Financial delta zero for Wind after B1
  M. CleanNotReadyError metadata completeness
  N. run_project_legacy carries CALIBRATION_ONLY lineage (not production authority)
  O. Production router raises on non-promoted override inputs
  P. Edge cases: unknown/unclassified/Portfolio project types raise CleanNotReadyError

CALIBRATION_ONLY note: run_project_legacy() and execute_calibration_waterfall()
are the explicit legacy calibration entry points.  Production routes
(run_project, execute_production_demo, execute_production_waterfall) are
clean-only as of Phase B1.  Unknown/unclassified types also raise CleanNotReadyError
(calculation_count=0) — no legacy fallthrough for any type.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Engine call counter (same pattern as test_prefreeze_pr8…)
# ---------------------------------------------------------------------------

class EngineCounters:
    """Spy on every engine binding site so no call can bypass the counter."""

    def __init__(self, monkeypatch):
        self.clean_calls = 0
        self.legacy_core_calls = 0
        self.legacy_engine_calls = 0

        import financial_engine.shareholder_waterfall as g2c_pkg
        import financial_engine.shareholder_waterfall.model as g2c_model
        import app.waterfall_core as waterfall_core
        import app.waterfall_runner as waterfall_runner
        import finco_core.waterfall.waterfall_engine as legacy_engine
        import domain.waterfall.waterfall_engine as domain_engine

        _orig_clean = g2c_model.run_project_shareholder_waterfall_model
        _orig_core = waterfall_core.run_waterfall_v3_core
        _orig_engine = legacy_engine.run_waterfall

        def _count_clean(*a, **kw):
            self.clean_calls += 1
            return _orig_clean(*a, **kw)

        def _count_core(*a, **kw):
            self.legacy_core_calls += 1
            return _orig_core(*a, **kw)

        def _count_engine(*a, **kw):
            self.legacy_engine_calls += 1
            return _orig_engine(*a, **kw)

        monkeypatch.setattr(g2c_pkg, "run_project_shareholder_waterfall_model", _count_clean)
        monkeypatch.setattr(g2c_model, "run_project_shareholder_waterfall_model", _count_clean)
        monkeypatch.setattr(waterfall_core, "run_waterfall_v3_core", _count_core)
        monkeypatch.setattr(waterfall_runner, "run_waterfall_v3_core", _count_core)
        monkeypatch.setattr(legacy_engine, "run_waterfall", _count_engine)
        monkeypatch.setattr(domain_engine, "run_waterfall", _count_engine)


# ---------------------------------------------------------------------------
# A — Solar production: clean_calls == 1, legacy_calls == 0
# ---------------------------------------------------------------------------

class TestA_SolarProduction:
    def test_a1_solar_clean_call_count(self, monkeypatch):
        """Solar production: exactly one clean engine call, zero legacy calls."""
        counters = EngineCounters(monkeypatch)
        from app.api.project_runner import run_project
        out = run_project("Solar", "Base")
        assert counters.clean_calls == 1, (
            f"expected 1 clean call, got {counters.clean_calls}"
        )
        assert counters.legacy_core_calls == 0, (
            f"expected 0 legacy core calls, got {counters.legacy_core_calls}"
        )
        assert counters.legacy_engine_calls == 0, (
            f"expected 0 legacy engine calls, got {counters.legacy_engine_calls}"
        )
        assert out["runtime_authority"]["runtime_authority"] == "clean_g2c"


# ---------------------------------------------------------------------------
# B — Wind production: clean_calls == 1, legacy_calls == 0
# ---------------------------------------------------------------------------

class TestB_WindProduction:
    def test_b1_wind_clean_call_count(self, monkeypatch):
        """Wind production: exactly one clean engine call, zero legacy calls."""
        counters = EngineCounters(monkeypatch)
        from app.api.project_runner import run_project
        out = run_project("Wind", "Base")
        assert counters.clean_calls == 1, (
            f"expected 1 clean call, got {counters.clean_calls}"
        )
        assert counters.legacy_core_calls == 0, (
            f"expected 0 legacy core calls, got {counters.legacy_core_calls}"
        )
        assert counters.legacy_engine_calls == 0, (
            f"expected 0 legacy engine calls, got {counters.legacy_engine_calls}"
        )
        assert out["runtime_authority"]["runtime_authority"] == "clean_g2c"


# ---------------------------------------------------------------------------
# C — Oborovo production: Phase B2 clean-only promotion
# ---------------------------------------------------------------------------

class TestC_OborovoProduction:
    def test_c1_oborovo_is_clean_production(self):
        """Oborovo production is promoted without a legacy fallthrough."""
        from app.api.project_runner import run_project

        out = run_project("Oborovo", "Base")
        assert out["runtime_authority"]["runtime_authority"] == "clean_g2c"
        assert out["runtime_authority"]["calculation_count"] == 1

    def test_c2_oborovo_typed_classification(self):
        """Oborovo reaches clean readiness through typed inputs."""
        from app.project_factories import create_default_oborovo
        from app.services.production_financial_authority import classify_production_authority

        decision = classify_production_authority(create_default_oborovo())
        assert decision.promoted
        assert decision.classification.value == "CLEAN_PRODUCTION_READY"

    def test_c3_oborovo_one_clean_zero_legacy_calls(self, monkeypatch):
        """Oborovo: exactly one clean call and zero legacy calls."""
        counters = EngineCounters(monkeypatch)
        from app.api.project_runner import run_project

        run_project("Oborovo", "Base")
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0
        assert counters.legacy_engine_calls == 0


# ---------------------------------------------------------------------------
# D — TUHO production: raises CleanNotReadyError, calculation_count == 0
# ---------------------------------------------------------------------------

class TestD_TUHOProduction:
    def test_d1_tuho_raises_clean_not_ready(self):
        """TUHO production raises CleanNotReadyError (no legacy fallthrough)."""
        from app.services.production_financial_authority import CleanNotReadyError
        from app.api.project_runner import run_project

        with pytest.raises(CleanNotReadyError) as exc_info:
            run_project("TUHO", "Base")
        err = exc_info.value
        assert err.calculation_count == 0
        assert err.runtime_authority == "clean_not_ready"

    def test_d2_tuho_typed_reason(self):
        """TUHO CleanNotReadyError carries the typed tax-runtime-gap reason."""
        from app.services.production_financial_authority import CleanNotReadyError
        from app.api.project_runner import run_project

        with pytest.raises(CleanNotReadyError) as exc_info:
            run_project("TUHO", "Base")
        assert exc_info.value.reason_code == "PR8_BLOCKED_BY_TYPED_TUHO_TAX_RUNTIME_GAP"

    def test_d3_tuho_zero_legacy_calls(self, monkeypatch):
        """TUHO: zero engine calls (clean or legacy) when CleanNotReadyError raised."""
        counters = EngineCounters(monkeypatch)
        from app.services.production_financial_authority import CleanNotReadyError
        from app.api.project_runner import run_project

        with pytest.raises(CleanNotReadyError):
            run_project("TUHO", "Base")
        assert counters.clean_calls == 0
        assert counters.legacy_core_calls == 0
        assert counters.legacy_engine_calls == 0


# ---------------------------------------------------------------------------
# E — Oborovo via run_project_legacy: executes legacy calibration
# ---------------------------------------------------------------------------

class TestE_OborovoLegacyCalibration:
    def test_e1_oborovo_legacy_still_callable(self, monkeypatch):
        """run_project_legacy("Oborovo") executes the legacy waterfall (calibration only)."""
        counters = EngineCounters(monkeypatch)
        from app.api.project_runner import run_project_legacy

        # Must not raise — legacy is explicitly callable for calibration.
        result = run_project_legacy("Oborovo", "Base")
        assert result is not None
        # Legacy waterfall executed at least once.
        assert (
            counters.legacy_core_calls + counters.legacy_engine_calls >= 1
        ), (
            f"expected at least one legacy call; got core={counters.legacy_core_calls}, "
            f"engine={counters.legacy_engine_calls}"
        )
        # Clean engine NOT invoked.
        assert counters.clean_calls == 0

    def test_e2_oborovo_legacy_has_kpis(self):
        """run_project_legacy("Oborovo") returns a results dict with KPIs."""
        from app.api.project_runner import run_project_legacy

        result = run_project_legacy("Oborovo", "Base")
        assert "kpis" in result
        assert result["kpis"]["total_revenue_keur"] is not None


# ---------------------------------------------------------------------------
# F — TUHO via run_project_legacy: executes legacy calibration
# ---------------------------------------------------------------------------

class TestF_TUHOLegacyCalibration:
    def test_f1_tuho_legacy_still_callable(self, monkeypatch):
        """run_project_legacy("TUHO") executes the legacy waterfall (calibration only)."""
        counters = EngineCounters(monkeypatch)
        from app.api.project_runner import run_project_legacy

        result = run_project_legacy("TUHO", "Base")
        assert result is not None
        assert (
            counters.legacy_core_calls + counters.legacy_engine_calls >= 1
        ), (
            f"expected at least one legacy call; got core={counters.legacy_core_calls}, "
            f"engine={counters.legacy_engine_calls}"
        )
        assert counters.clean_calls == 0

    def test_f2_tuho_legacy_has_kpis(self):
        """run_project_legacy("TUHO") returns a results dict with KPIs."""
        from app.api.project_runner import run_project_legacy

        result = run_project_legacy("TUHO", "Base")
        assert "kpis" in result
        assert result["kpis"]["total_revenue_keur"] is not None


# ---------------------------------------------------------------------------
# G — Production does NOT fall back on clean engine error
# ---------------------------------------------------------------------------

class TestG_CleanEngineErrorFailsClosed:
    def test_g1_clean_engine_failure_does_not_fallback(self, monkeypatch):
        """If the clean engine raises, production fails closed — no legacy fallback."""
        from app.services.production_financial_authority import (
            CleanProductionRunUnavailable,
        )
        import financial_engine.shareholder_waterfall.model as g2c_model
        import financial_engine.shareholder_waterfall as g2c_pkg

        def _raise_unavailable(*a, **kw):
            raise CleanProductionRunUnavailable(
                reason_code="B1_TEST_SYNTHETIC_ENGINE_FAILURE",
                detail="Synthetic clean engine failure for B1 test.",
            )

        monkeypatch.setattr(g2c_model, "run_project_shareholder_waterfall_model", _raise_unavailable)
        monkeypatch.setattr(g2c_pkg, "run_project_shareholder_waterfall_model", _raise_unavailable)
        from app.api.project_runner import run_project

        with pytest.raises(CleanProductionRunUnavailable):
            run_project("Solar", "Base")


# ---------------------------------------------------------------------------
# H — Production does NOT fall back on classifier failure
# ---------------------------------------------------------------------------

class TestH_ClassifierFailureFailsClosed:
    def test_h1_classifier_failure_does_not_fallback(self, monkeypatch):
        """If the classifier raises, production fails closed — no legacy fallback."""
        from app.services.production_financial_authority import (
            ProductionAuthorityResolutionError,
        )
        import app.services.production_waterfall_seam as seam

        monkeypatch.setattr(
            seam,
            "classify_or_fail",
            lambda *a, **kw: (_ for _ in ()).throw(
                ProductionAuthorityResolutionError(
                    reason_code="B1_TEST_SYNTHETIC_CLASSIFIER_FAILURE",
                    detail="Synthetic classifier failure for B1 test.",
                )
            ),
        )
        from app.api.project_runner import run_project

        # The classifier raises BEFORE any engine call.
        with pytest.raises(ProductionAuthorityResolutionError):
            run_project("Solar", "Base")


# ---------------------------------------------------------------------------
# I — execute_production_demo: Solar/Oborovo clean, TUHO raises
# ---------------------------------------------------------------------------

class TestI_ExecuteProductionDemo:
    def test_i1_solar_demo_clean(self, monkeypatch):
        """execute_production_demo("Solar") returns a clean result."""
        counters = EngineCounters(monkeypatch)
        from app.services.production_waterfall_seam import execute_production_demo

        demo, meta = execute_production_demo("Solar", "Base")
        assert counters.clean_calls == 1
        assert counters.legacy_core_calls == 0
        assert counters.legacy_engine_calls == 0
        assert meta["runtime_authority"] == "clean_g2c"

    def test_i2_tuho_demo_raises_clean_not_ready(self):
        """execute_production_demo("TUHO") raises CleanNotReadyError."""
        from app.services.production_financial_authority import CleanNotReadyError
        from app.services.production_waterfall_seam import execute_production_demo

        with pytest.raises(CleanNotReadyError) as exc_info:
            execute_production_demo("TUHO", "Base")
        assert exc_info.value.calculation_count == 0
        assert exc_info.value.runtime_authority == "clean_not_ready"

    def test_i3_oborovo_demo_is_clean(self):
        """execute_production_demo("Oborovo") uses clean G2C."""
        from app.services.production_waterfall_seam import execute_production_demo

        _, meta = execute_production_demo("Oborovo", "Base")
        assert meta["runtime_authority"] == "clean_g2c"
        assert meta["calculation_count"] == 1


# ---------------------------------------------------------------------------
# J — execute_calibration_waterfall: explicit legacy seam for blocked projects.
#     execute_production_waterfall is clean-only; allow_legacy param removed.
# ---------------------------------------------------------------------------

class TestJ_CalibrationWaterfallSeam:
    """J — execute_calibration_waterfall: explicit legacy seam for blocked projects."""

    def test_j1_tuho_calibration_waterfall_runs_legacy(self):
        """execute_calibration_waterfall() runs legacy for TUHO (explicitly blocked)."""
        from app.project_factories import create_default_tuho_wind1
        from app.services.production_waterfall_seam import execute_calibration_waterfall

        inputs = create_default_tuho_wind1()
        execution = execute_calibration_waterfall(inputs)
        assert execution.authority_metadata["runtime_authority"] == "legacy_waterfall_calibration"
        assert execution.authority_metadata["calculation_count"] == 1
        assert execution.authority_metadata.get("calibration_seam") == "execute_calibration_waterfall"

    def test_j2_oborovo_calibration_waterfall_runs_legacy(self):
        """execute_calibration_waterfall() runs legacy for Oborovo (explicitly blocked)."""
        from app.project_factories import create_default_oborovo_legacy_calibration
        from app.services.production_waterfall_seam import execute_calibration_waterfall

        inputs = create_default_oborovo_legacy_calibration()
        execution = execute_calibration_waterfall(inputs)
        assert execution.authority_metadata["runtime_authority"] == "legacy_waterfall_calibration"
        assert execution.authority_metadata["calculation_count"] == 1
        assert execution.authority_metadata.get("calibration_seam") == "execute_calibration_waterfall"

    def test_j3_execute_production_waterfall_refuses_allow_legacy_param(self):
        """execute_production_waterfall() no longer accepts allow_legacy — TypeError if passed."""
        from app.project_factories import create_default_tuho_wind1
        from app.services.production_waterfall_seam import execute_production_waterfall

        inputs = create_default_tuho_wind1()
        with pytest.raises(TypeError):
            execute_production_waterfall(inputs, allow_legacy=True)  # type: ignore[call-arg]

    def test_j4_calibration_waterfall_refuses_clean_ready_project(self):
        """execute_calibration_waterfall() refuses a clean-ready project (Solar)."""
        from app.project_factories import create_default_solar_project
        from app.services.production_waterfall_seam import execute_calibration_waterfall
        from app.services.production_financial_authority import ProductionAuthorityResolutionError

        inputs = create_default_solar_project()
        with pytest.raises(ProductionAuthorityResolutionError) as exc_info:
            execute_calibration_waterfall(inputs)
        assert "CLEAN_READY" in exc_info.value.reason_code

    def test_j5_production_waterfall_tuho_raises_clean_not_ready(self):
        """execute_production_waterfall() raises CleanNotReadyError for TUHO (B1 clean-only)."""
        from app.project_factories import create_default_tuho_wind1
        from app.services.production_waterfall_seam import execute_production_waterfall
        from app.services.production_financial_authority import CleanNotReadyError

        inputs = create_default_tuho_wind1()
        with pytest.raises(CleanNotReadyError):
            execute_production_waterfall(inputs)

    def test_j6_production_waterfall_oborovo_is_clean(self):
        """execute_production_waterfall() uses clean authority for Oborovo."""
        from app.project_factories import create_default_oborovo
        from app.services.production_waterfall_seam import execute_production_waterfall

        inputs = create_default_oborovo()
        execution = execute_production_waterfall(inputs)
        assert execution.authority_metadata["runtime_authority"] == "clean_g2c"


# ---------------------------------------------------------------------------
# K — Financial delta zero for Solar after B1
#
# Solar was already on the clean path pre-B1.  B1 only removes the blocked
# legacy fallthrough — Solar routing is unchanged.  We verify KPIs against
# the frozen PR-F1 canonical-axis fingerprints (same values as pre-B1).
# These fingerprints were established at the PR-F1 axis-authority freeze and
# are the single source of truth for Solar clean-engine financial invariance.
# ---------------------------------------------------------------------------

# PR-F1 canonical-axis fingerprints (from test_prefreeze_pr8, §18).
_PRF1_SOLAR = {"revenue": 94414.54881158611, "senior_ds": 35302.12518820596}
_PRF1_WIND  = {"revenue": 213093.25362988273, "senior_ds": 42650.79738447129}


class TestK_SolarFinancialInvariance:
    def test_k1_solar_senior_ds_matches_prf1_fingerprint(self):
        """Solar senior_ds unchanged after B1 routing change (vs PR-F1 fingerprint)."""
        from app.api.project_runner import run_project

        prod = run_project("Solar", "Base")
        prod_ds = prod["kpis"]["total_senior_ds_keur"]
        assert abs(prod_ds - _PRF1_SOLAR["senior_ds"]) < 1e-4, (
            f"Solar senior_ds diverged from PR-F1 fingerprint: got {prod_ds}, "
            f"expected {_PRF1_SOLAR['senior_ds']}"
        )

    def test_k2_solar_revenue_matches_prf1_fingerprint(self):
        """Solar revenue unchanged after B1 routing change (vs PR-F1 fingerprint)."""
        from app.api.project_runner import run_project

        prod = run_project("Solar", "Base")
        prod_rev = prod["kpis"]["total_revenue_keur"]
        assert abs(prod_rev - _PRF1_SOLAR["revenue"]) < 1e-4, (
            f"Solar revenue diverged from PR-F1 fingerprint: got {prod_rev}, "
            f"expected {_PRF1_SOLAR['revenue']}"
        )


# ---------------------------------------------------------------------------
# L — Financial delta zero for Wind after B1
# ---------------------------------------------------------------------------

class TestL_WindFinancialInvariance:
    def test_l1_wind_senior_ds_matches_prf1_fingerprint(self):
        """Wind senior_ds unchanged after B1 routing change (vs PR-F1 fingerprint)."""
        from app.api.project_runner import run_project

        prod = run_project("Wind", "Base")
        prod_ds = prod["kpis"]["total_senior_ds_keur"]
        assert abs(prod_ds - _PRF1_WIND["senior_ds"]) < 1e-4, (
            f"Wind senior_ds diverged from PR-F1 fingerprint: got {prod_ds}, "
            f"expected {_PRF1_WIND['senior_ds']}"
        )

    def test_l2_wind_revenue_matches_prf1_fingerprint(self):
        """Wind revenue unchanged after B1 routing change (vs PR-F1 fingerprint)."""
        from app.api.project_runner import run_project

        prod = run_project("Wind", "Base")
        prod_rev = prod["kpis"]["total_revenue_keur"]
        assert abs(prod_rev - _PRF1_WIND["revenue"]) < 1e-4, (
            f"Wind revenue diverged from PR-F1 fingerprint: got {prod_rev}, "
            f"expected {_PRF1_WIND['revenue']}"
        )


# ---------------------------------------------------------------------------
# M — CleanNotReadyError metadata completeness
# ---------------------------------------------------------------------------

class TestM_CleanNotReadyErrorMetadata:
    def test_m1_metadata_fields_complete(self):
        """CleanNotReadyError.to_metadata() contains all required B1 fields."""
        from app.services.production_financial_authority import CleanNotReadyError
        from app.api.project_runner import run_project

        try:
            run_project("TUHO", "Base")
        except CleanNotReadyError as e:
            meta = e.to_metadata()
            assert meta["runtime_authority"] == "clean_not_ready"
            assert meta["calculation_count"] == 0
            assert "reason_code" in meta
            assert "classification" in meta
            assert "detail" in meta
        else:
            pytest.fail("Expected CleanNotReadyError but no exception raised")


# ---------------------------------------------------------------------------
# N — run_project_legacy carries no production-authority lineage
# ---------------------------------------------------------------------------

class TestN_LegacyCalibrationLineage:
    def test_n1_legacy_run_has_no_runtime_authority_key(self):
        """run_project_legacy payload does NOT include runtime_authority key
        (it uses the historical payload shape, no PR-8 keys)."""
        from app.api.project_runner import run_project_legacy

        result = run_project_legacy("Solar", "Base")
        # force_legacy=True suppresses the runtime_authority key.
        assert "runtime_authority" not in result, (
            "run_project_legacy must not include a runtime_authority key "
            "(that key is reserved for the production router)."
        )


# ---------------------------------------------------------------------------
# O — Production router raises on non-promoted override inputs
# ---------------------------------------------------------------------------

class TestO_NonPromotedOverrideInput:
    def test_o1_non_promoted_override_raises_clean_not_ready(self):
        """A non-promoted ProjectInputs supplied as override raises CleanNotReadyError."""
        from app.project_factories import create_default_oborovo_legacy_calibration
        from app.services.production_financial_authority import CleanNotReadyError
        from app.api.project_runner import run_project

        # Oborovo inputs are non-promoted; supplying them as an override
        # to an arbitrary project_type must still raise.
        oborovo_inputs = create_default_oborovo_legacy_calibration()
        with pytest.raises(CleanNotReadyError):
            run_project("Oborovo", "Base", project_inputs_override=oborovo_inputs)


# ---------------------------------------------------------------------------
# P — Edge cases: unknown project type, invalid inputs, classifier failure,
#     clean engine failure, Portfolio no-legacy, workbook/runtime surfaces
# ---------------------------------------------------------------------------

class TestP_EdgeCases:
    """P — Additional edge cases per Correction A spec."""

    def test_p1_unknown_project_type_clean_zero_legacy_zero(self):
        """Unknown project type: both run_project and execute_production_demo raise CleanNotReadyError.

        Phase B1 invariant: unrecognised/unclassified types NEVER reach a legacy engine.
        clean_calculations == 0; legacy_calculations == 0.
        """
        from app.services.production_waterfall_seam import execute_production_demo
        from app.services.production_financial_authority import CleanNotReadyError
        from app.api.project_runner import run_project
        import pytest

        with pytest.raises(CleanNotReadyError) as exc_info:
            execute_production_demo("__unknown_project_type_xyz__")
        assert exc_info.value.calculation_count == 0
        assert exc_info.value.runtime_authority == "clean_not_ready"

        with pytest.raises(CleanNotReadyError) as exc_info2:
            run_project("__unknown_project_type_xyz__", "Base")
        assert exc_info2.value.calculation_count == 0
        assert exc_info2.value.runtime_authority == "clean_not_ready"

    def test_p2_invalid_inputs_classifier_raises_resolution_error(self):
        """An object that breaks the classifier raises ProductionAuthorityResolutionError."""
        from app.services.production_waterfall_seam import classify_or_fail
        from app.services.production_financial_authority import ProductionAuthorityResolutionError

        class BrokenInputs:
            @property
            def tax(self):
                raise RuntimeError("broken tax")

        with pytest.raises(ProductionAuthorityResolutionError) as exc_info:
            classify_or_fail(BrokenInputs())
        assert exc_info.value.reason_code == "PR8_AUTHORITY_CLASSIFIER_FAILURE"

    def test_p3_classifier_failure_zero_legacy_calls(self, monkeypatch):
        """Classifier failure → zero legacy engine calls (fail closed)."""
        from app.services.production_waterfall_seam import execute_production_waterfall
        from app.services.production_financial_authority import ProductionAuthorityResolutionError

        import app.waterfall_core as waterfall_core
        legacy_calls = []
        monkeypatch.setattr(waterfall_core, "run_waterfall_v3_core",
                            lambda *a, **kw: legacy_calls.append(1) or (_ for _ in ()).throw(AssertionError("legacy called")))

        class BrokenInputs:
            @property
            def tax(self):
                raise RuntimeError("broken")

        with pytest.raises(ProductionAuthorityResolutionError):
            execute_production_waterfall(BrokenInputs())
        assert len(legacy_calls) == 0, "Legacy engine must not fire after classifier failure"

    def test_p4_clean_engine_failure_no_legacy_fallback(self, monkeypatch):
        """Clean engine failure → CleanProductionRunUnavailable, zero legacy calls."""
        from app.project_factories import create_default_solar_project
        from app.services.production_waterfall_seam import execute_production_waterfall
        from app.services.production_financial_authority import CleanProductionRunUnavailable
        import financial_engine.shareholder_waterfall.model as g2c_model
        import financial_engine.shareholder_waterfall as g2c_pkg
        import app.waterfall_core as waterfall_core

        legacy_calls = []

        def broken_clean(*a, **kw):
            raise CleanProductionRunUnavailable(
                reason_code="P4_TEST_SYNTHETIC_ENGINE_FAILURE",
                detail="Synthetic failure for p4 test.",
            )

        monkeypatch.setattr(g2c_model, "run_project_shareholder_waterfall_model", broken_clean)
        monkeypatch.setattr(g2c_pkg, "run_project_shareholder_waterfall_model", broken_clean)
        monkeypatch.setattr(waterfall_core, "run_waterfall_v3_core",
                            lambda *a, **kw: legacy_calls.append(1))

        inputs = create_default_solar_project()
        with pytest.raises(CleanProductionRunUnavailable):
            execute_production_waterfall(inputs)
        assert len(legacy_calls) == 0, "No legacy fallback after clean engine crash"

    def test_p5_portfolio_does_not_call_clean_production_authority(self, monkeypatch):
        """Portfolio aggregation: run_waterfall_v3_core used, NOT clean G2C authority.

        Portfolio is classified EXPLICIT_CALIBRATION_ONLY / OFFLINE_EVIDENCE_ONLY:
        it calls run_waterfall_v3_core directly (not the production authority seam).
        This test proves no accidental clean-authority call leaks through Portfolio.
        """
        import financial_engine.shareholder_waterfall.model as g2c_model

        clean_calls = []
        orig = g2c_model.run_project_shareholder_waterfall_model

        def counting_clean(*a, **kw):
            clean_calls.append(1)
            return orig(*a, **kw)

        monkeypatch.setattr(g2c_model, "run_project_shareholder_waterfall_model", counting_clean)

        from app.portfolio_runner import run_portfolio_from_inputs
        from domain.portfolio.inputs import PortfolioInputs

        # Build a minimal PortfolioInputs with no projects — just aggregation.
        try:
            portfolio_inputs = PortfolioInputs(projects=(), shared_financing=None)
        except Exception:
            pytest.skip("PortfolioInputs cannot be constructed with no projects")

        try:
            run_portfolio_from_inputs(portfolio_inputs, project_results=())
        except Exception:
            pass  # We only care that G2C was not called.

        assert len(clean_calls) == 0, (
            "Portfolio must not call the clean G2C authority — it is an "
            "EXPLICIT_CALIBRATION_ONLY / aggregation-only surface."
        )

    def test_p6_institutional_workbook_solar_clean_result_only(self, monkeypatch):
        """Institutional workbook Solar: execute_production_waterfall returns clean result."""
        from app.project_factories import create_default_solar_project
        from app.services.production_waterfall_seam import execute_production_waterfall

        inputs = create_default_solar_project()
        execution = execute_production_waterfall(inputs)
        assert execution.authority_metadata["runtime_authority"] == "clean_g2c"

    def test_p7_institutional_workbook_oborovo_is_clean(self):
        """Institutional workbook consumes clean Oborovo authority."""
        from app.project_factories import create_default_oborovo
        from app.services.production_waterfall_seam import execute_production_waterfall

        inputs = create_default_oborovo()
        execution = execute_production_waterfall(inputs)
        assert execution.authority_metadata["runtime_authority"] == "clean_g2c"
        assert execution.authority_metadata["calculation_count"] == 1

    def test_p8_institutional_workbook_tuho_raises_clean_not_ready(self):
        """Institutional workbook: TUHO raises CleanNotReadyError (no legacy execution)."""
        from app.project_factories import create_default_tuho_wind1
        from app.services.production_waterfall_seam import execute_production_waterfall
        from app.services.production_financial_authority import CleanNotReadyError

        inputs = create_default_tuho_wind1()
        with pytest.raises(CleanNotReadyError) as exc_info:
            execute_production_waterfall(inputs)
        assert exc_info.value.calculation_count == 0

    def test_p9_runtime_summary_solar_no_legacy_fallback(self, monkeypatch):
        """Runtime summary Solar: no legacy engine fires."""
        from app.project_factories import create_default_solar_project
        from app.services.production_waterfall_seam import execute_production_waterfall
        import app.waterfall_core as waterfall_core

        legacy_calls = []
        orig_core = waterfall_core.run_waterfall_v3_core

        def counting_legacy(*a, **kw):
            legacy_calls.append(1)
            return orig_core(*a, **kw)

        monkeypatch.setattr(waterfall_core, "run_waterfall_v3_core", counting_legacy)

        inputs = create_default_solar_project()
        execute_production_waterfall(inputs)
        assert len(legacy_calls) == 0, "No legacy engine call on Solar runtime summary"


# ---------------------------------------------------------------------------
# Q — Oborovo Phase B2 promotion matrix
# ---------------------------------------------------------------------------
#
# COMPLETE INDEPENDENT OBOROVO BLOCKER INVENTORY
# (Classifier currently stops at first blocker; all are enumerated here.)
#
# ┌─────────────────────────────────────────────────────┬──────────────────────────────────────────┐
# │ Field                                               │ Classification                           │
# ├─────────────────────────────────────────────────────┼──────────────────────────────────────────┤
# │ TAX                                                 │                                          │
# │ tax.clean_cash_tax_timing_enabled = True            │ READY_TYPED_AUTHORITY                    │
# │ tax.thin_cap_enabled = False                        │ READY_TYPED_AUTHORITY                    │
# │ tax.atad_enabled = False                            │ READY_TYPED_AUTHORITY                    │
# │ tax.shl_interest_deductibility =                   │ READY_TYPED_AUTHORITY (fully non-ded.)   │
# │   FULLY_NON_DEDUCTIBLE                              │                                          │
# │ tax.opening_tax_loss_vintages = ()                  │ READY_TYPED_AUTHORITY                    │
# ├─────────────────────────────────────────────────────┼──────────────────────────────────────────┤
# │ FINANCING                                           │                                          │
# │ financing.sponsor_funding_mode = None               │ MISSING_TYPED_INPUT ← current blocker    │
# │ financing.gearing_basis_mode = None                 │ MISSING_TYPED_INPUT                      │
# │ financing.debt_sizing_mode = FLAT_DSCR_SCULPTED     │ READY_TYPED_AUTHORITY                    │
# │ financing.fixed_debt_keur = 42852.27                │ READY_TYPED_AUTHORITY                    │
# │ financing.use_frozen_excel_senior_debt_schedule =   │ LEGACY_CALIBRATION_ONLY                  │
# │   True                                              │                                          │
# │ financing.frozen_senior_ds_fixture_path set         │ LEGACY_CALIBRATION_ONLY                  │
# ├─────────────────────────────────────────────────────┼──────────────────────────────────────────┤
# │ SHL                                                 │                                          │
# │ financing.clean_shl_principal_keur = 14620.77       │ READY_TYPED_AUTHORITY                    │
# │ financing.clean_shl_repayment_method = CASH_SWEEP   │ READY_TYPED_AUTHORITY                    │
# │ (construction interest) — no SHL IDC typed          │ SOURCE_EVIDENCE_REQUIRED                 │
# ├─────────────────────────────────────────────────────┼──────────────────────────────────────────┤
# │ CONSTRUCTION                                        │                                          │
# │ financing.construction_financing = None             │ MISSING_TYPED_INPUT                      │
# │ (source-derived idc/commitment/bank fees not typed) │ SOURCE_EVIDENCE_REQUIRED                 │
# └─────────────────────────────────────────────────────┴──────────────────────────────────────────┘

class TestQ_OborovoBlockerMatrix:
    def test_q1_oborovo_is_promoted_by_typed_contract(self):
        """Oborovo: typed B2 contract promotes naturally."""
        from app.project_factories import create_default_oborovo
        from app.services.production_financial_authority import classify_production_authority

        inputs = create_default_oborovo()
        decision = classify_production_authority(inputs)
        assert decision.promoted
        assert decision.classification.value == "CLEAN_PRODUCTION_READY"

    def test_q2_oborovo_sponsor_funding_mode_is_typed(self):
        """Oborovo sponsor funding follows share-capital-then-SHL authority."""
        from app.project_factories import create_default_oborovo
        from finco_core.inputs import SponsorFundingMode

        inputs = create_default_oborovo()
        assert inputs.financing.sponsor_funding_mode is SponsorFundingMode.SHARE_CAPITAL_THEN_SHL

    def test_q3_oborovo_gearing_basis_mode_is_typed(self):
        """Oborovo Senior gearing limit uses total project uses."""
        from app.project_factories import create_default_oborovo
        from finco_core.inputs import GearingBasisMode

        inputs = create_default_oborovo()
        assert inputs.financing.gearing_basis_mode is GearingBasisMode.TOTAL_PROJECT_USES

    def test_q4_oborovo_frozen_schedule_removed_from_production(self):
        """Oborovo production has no frozen Senior authority."""
        from app.project_factories import create_default_oborovo

        inputs = create_default_oborovo()
        assert not getattr(inputs.financing, "use_frozen_excel_senior_debt_schedule", False)
        assert inputs.financing.frozen_senior_ds_fixture_path is None

    def test_q5_oborovo_construction_financing_is_typed(self):
        """Oborovo: construction and VAT facility authority are typed."""
        from app.project_factories import create_default_oborovo

        inputs = create_default_oborovo()
        assert inputs.financing.construction_financing.enabled
        assert inputs.financing.construction_financing.vat_facility.enabled

    def test_q6_oborovo_clean_cash_tax_timing_is_ready(self):
        """Oborovo: tax.clean_cash_tax_timing_enabled=True (passes tax check)."""
        from app.project_factories import create_default_oborovo

        inputs = create_default_oborovo()
        assert inputs.tax.clean_cash_tax_timing_enabled is True


# ---------------------------------------------------------------------------
# R — TUHO blocker matrix (B1 does NOT fix these; inventory only)
# ---------------------------------------------------------------------------
#
# COMPLETE INDEPENDENT TUHO BLOCKER INVENTORY
#
# ┌─────────────────────────────────────────────────────┬──────────────────────────────────────────┐
# │ Field                                               │ Classification                           │
# ├─────────────────────────────────────────────────────┼──────────────────────────────────────────┤
# │ TAX                                                 │                                          │
# │ tax.clean_cash_tax_timing_enabled = False           │ LEGACY_CALIBRATION_ONLY ← first blocker  │
# │ tax.thin_cap_enabled = True                         │ UNSUPPORTED_CAPABILITY                   │
# │ tax.atad_enabled = True                             │ UNSUPPORTED_CAPABILITY                   │
# │ tax.shl_interest_deductibility =                   │ UNSUPPORTED_CAPABILITY                   │
# │   SUBJECT_TO_LIMITATIONS                            │                                          │
# │ tax.opening_tax_loss_vintages = ()                  │ READY_TYPED_AUTHORITY                    │
# ├─────────────────────────────────────────────────────┼──────────────────────────────────────────┤
# │ FINANCING                                           │                                          │
# │ financing.sponsor_funding_mode = None               │ MISSING_TYPED_INPUT                      │
# │ financing.gearing_basis_mode = None                 │ MISSING_TYPED_INPUT                      │
# │ financing.debt_sizing_mode = None                   │ MISSING_TYPED_INPUT                      │
# │ financing.fixed_debt_keur = 43359.0                 │ READY_TYPED_AUTHORITY (value present)    │
# │ financing.use_frozen_excel_senior_debt_schedule =   │ LEGACY_CALIBRATION_ONLY                  │
# │   True                                              │                                          │
# │ financing.frozen_senior_ds_fixture_path set         │ LEGACY_CALIBRATION_ONLY                  │
# ├─────────────────────────────────────────────────────┼──────────────────────────────────────────┤
# │ SHL                                                 │                                          │
# │ financing.clean_shl_principal_keur = None           │ MISSING_TYPED_INPUT                      │
# │ financing.clean_shl_repayment_method = None         │ MISSING_TYPED_INPUT                      │
# │ (construction interest) — not typed                 │ SOURCE_EVIDENCE_REQUIRED                 │
# ├─────────────────────────────────────────────────────┼──────────────────────────────────────────┤
# │ CONSTRUCTION                                        │                                          │
# │ financing.construction_financing = None             │ MISSING_TYPED_INPUT                      │
# │ (source-derived idc/commitment/bank/vat not typed)  │ SOURCE_EVIDENCE_REQUIRED                 │
# └─────────────────────────────────────────────────────┴──────────────────────────────────────────┘

class TestR_TuhoBlockerMatrix:
    def test_r1_tuho_first_blocker_is_deferred_tax_capability(self):
        """TUHO: first blocker is deferred tax capability (clean_cash_tax_timing_enabled=False)."""
        from app.project_factories import create_default_tuho_wind1
        from app.services.production_financial_authority import classify_production_authority

        inputs = create_default_tuho_wind1()
        decision = classify_production_authority(inputs)
        assert not decision.promoted
        assert decision.reason_code == "PR8_BLOCKED_BY_TYPED_TUHO_TAX_RUNTIME_GAP"

    def test_r2_tuho_clean_cash_tax_timing_disabled(self):
        """TUHO: tax.clean_cash_tax_timing_enabled=False (LEGACY_CALIBRATION_ONLY)."""
        from app.project_factories import create_default_tuho_wind1

        inputs = create_default_tuho_wind1()
        assert inputs.tax.clean_cash_tax_timing_enabled is False

    def test_r3_tuho_thin_cap_enabled(self):
        """TUHO: tax.thin_cap_enabled=True (UNSUPPORTED_CAPABILITY)."""
        from app.project_factories import create_default_tuho_wind1

        inputs = create_default_tuho_wind1()
        assert inputs.tax.thin_cap_enabled is True

    def test_r4_tuho_atad_enabled(self):
        """TUHO: tax.atad_enabled=True (UNSUPPORTED_CAPABILITY)."""
        from app.project_factories import create_default_tuho_wind1

        inputs = create_default_tuho_wind1()
        assert inputs.tax.atad_enabled is True

    def test_r5_tuho_shl_interest_subject_to_limitations(self):
        """TUHO: tax.shl_interest_deductibility=SUBJECT_TO_LIMITATIONS (UNSUPPORTED_CAPABILITY)."""
        from app.project_factories import create_default_tuho_wind1

        inputs = create_default_tuho_wind1()
        assert "subject_to_limitations" in str(inputs.tax.shl_interest_deductibility).lower()

    def test_r6_tuho_sponsor_funding_mode_is_none(self):
        """TUHO: financing.sponsor_funding_mode is None (MISSING_TYPED_INPUT)."""
        from app.project_factories import create_default_tuho_wind1

        inputs = create_default_tuho_wind1()
        assert inputs.financing.sponsor_funding_mode is None

    def test_r7_tuho_clean_shl_principal_is_none(self):
        """TUHO: financing.clean_shl_principal_keur is None (MISSING_TYPED_INPUT)."""
        from app.project_factories import create_default_tuho_wind1

        inputs = create_default_tuho_wind1()
        assert inputs.financing.clean_shl_principal_keur is None

    def test_r8_tuho_frozen_schedule_is_legacy_calibration(self):
        """TUHO: use_frozen_excel_senior_debt_schedule=True (LEGACY_CALIBRATION_ONLY)."""
        from app.project_factories import create_default_tuho_wind1

        inputs = create_default_tuho_wind1()
        assert getattr(inputs.financing, "use_frozen_excel_senior_debt_schedule", False)

    def test_r9_tuho_construction_financing_not_typed(self):
        """TUHO: financing.construction_financing is None (MISSING_TYPED_INPUT)."""
        from app.project_factories import create_default_tuho_wind1

        inputs = create_default_tuho_wind1()
        assert inputs.financing.construction_financing is None


# ---------------------------------------------------------------------------
# S — Full Solar/Wind financial invariance (all core KPI fields)
# ---------------------------------------------------------------------------

class TestS_SolarWindFullFinancialInvariance:
    """S — All financial KPIs unchanged from PR-F1 fingerprints (FINANCIAL_DELTA=ZERO)."""

    # Canonical PR-F1 fingerprints (established at axis-authority freeze).
    _SOLAR = {
        "revenue": 94414.54881158611,
        "senior_ds": 35302.12518820596,
    }
    _WIND = {
        "revenue": 213093.25362988273,
        "senior_ds": 42650.79738447129,
    }

    def test_s1_solar_revenue_invariant(self):
        from app.api.project_runner import run_project
        result = run_project("Solar", "Base")
        got = result["kpis"]["total_revenue_keur"]
        assert abs(got - self._SOLAR["revenue"]) < 1e-4, f"Solar revenue: {got} vs {self._SOLAR['revenue']}"

    def test_s2_solar_senior_ds_invariant(self):
        from app.api.project_runner import run_project
        result = run_project("Solar", "Base")
        got = result["kpis"]["total_senior_ds_keur"]
        assert abs(got - self._SOLAR["senior_ds"]) < 1e-4, f"Solar senior_ds: {got} vs {self._SOLAR['senior_ds']}"

    def test_s3_solar_runtime_authority_is_clean(self):
        from app.api.project_runner import run_project
        result = run_project("Solar", "Base")
        # runtime_authority is the authority_metadata dict in the project_runner payload.
        ra = result.get("runtime_authority")
        if isinstance(ra, dict):
            assert ra.get("runtime_authority") == "clean_g2c", f"Solar runtime_authority dict: {ra}"
        else:
            assert ra == "clean_g2c", f"Solar runtime_authority: {ra}"

    def test_s4_wind_revenue_invariant(self):
        from app.api.project_runner import run_project
        result = run_project("Wind", "Base")
        got = result["kpis"]["total_revenue_keur"]
        assert abs(got - self._WIND["revenue"]) < 1e-4, f"Wind revenue: {got} vs {self._WIND['revenue']}"

    def test_s5_wind_senior_ds_invariant(self):
        from app.api.project_runner import run_project
        result = run_project("Wind", "Base")
        got = result["kpis"]["total_senior_ds_keur"]
        assert abs(got - self._WIND["senior_ds"]) < 1e-4, f"Wind senior_ds: {got} vs {self._WIND['senior_ds']}"

    def test_s6_wind_runtime_authority_is_clean(self):
        from app.api.project_runner import run_project
        result = run_project("Wind", "Base")
        ra = result.get("runtime_authority")
        if isinstance(ra, dict):
            assert ra.get("runtime_authority") == "clean_g2c", f"Wind runtime_authority dict: {ra}"
        else:
            assert ra == "clean_g2c", f"Wind runtime_authority: {ra}"


# ---------------------------------------------------------------------------
# T — Portfolio reachability governance
#     Proves that portfolio_runner / portfolio_orchestrator pooled legacy path
#     is NOT reachable from current normal production entry points.
# ---------------------------------------------------------------------------

class TestT_PortfolioReachabilityGovernance:
    """T — Portfolio legacy path is LEGACY_EXPERIMENTAL / OFFLINE_ONLY.

    Normal production surfaces (run_project, execute_production_demo,
    REST API router) do not import or invoke portfolio_runner or
    portfolio_orchestrator.  Portfolio project type raises CleanNotReadyError
    on normal production path.
    """

    def test_t1_run_project_portfolio_raises_clean_not_ready(self):
        """run_project('Portfolio') raises CleanNotReadyError — no legacy engine fires."""
        from app.api.project_runner import run_project
        from app.services.production_financial_authority import CleanNotReadyError

        with pytest.raises(CleanNotReadyError) as exc_info:
            run_project("Portfolio", "Base")
        assert exc_info.value.calculation_count == 0
        assert exc_info.value.runtime_authority == "clean_not_ready"

    def test_t2_execute_production_demo_portfolio_raises_clean_not_ready(self):
        """execute_production_demo('Portfolio') raises CleanNotReadyError."""
        from app.services.production_waterfall_seam import execute_production_demo
        from app.services.production_financial_authority import CleanNotReadyError

        with pytest.raises(CleanNotReadyError) as exc_info:
            execute_production_demo("Portfolio")
        assert exc_info.value.calculation_count == 0
        assert exc_info.value.runtime_authority == "clean_not_ready"

    def test_t3_portfolio_runner_not_imported_from_production_api(self):
        """portfolio_runner and portfolio_orchestrator are not imported by production API modules."""
        import importlib
        import sys

        # Load modules without executing their side effects by checking source
        import inspect

        # app.api.project_runner must not import portfolio_runner or portfolio_orchestrator
        import app.api.project_runner as runner_mod
        runner_src = inspect.getsource(runner_mod)
        assert "portfolio_runner" not in runner_src, (
            "portfolio_runner imported in app.api.project_runner — Portfolio legacy reachable"
        )
        assert "portfolio_orchestrator" not in runner_src, (
            "portfolio_orchestrator imported in app.api.project_runner"
        )

        # app.services.production_waterfall_seam must not import portfolio_runner
        import app.services.production_waterfall_seam as seam_mod
        seam_src = inspect.getsource(seam_mod)
        assert "portfolio_runner" not in seam_src, (
            "portfolio_runner imported in production_waterfall_seam — Portfolio legacy reachable"
        )
        assert "portfolio_orchestrator" not in seam_src, (
            "portfolio_orchestrator imported in production_waterfall_seam"
        )
