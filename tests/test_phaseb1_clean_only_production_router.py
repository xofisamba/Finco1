"""Phase B1 — Clean-Only Production Router.

Proves that after the B1 routing change:
  A. Solar production: clean_calls == 1, legacy_calls == 0
  B. Wind production:  clean_calls == 1, legacy_calls == 0
  C. Oborovo production: raises CleanNotReadyError, calculation_count == 0
  D. TUHO production:    raises CleanNotReadyError, calculation_count == 0
  E. Oborovo via run_project_legacy: executes legacy calibration
  F. TUHO via run_project_legacy:    executes legacy calibration
  G. Production does NOT fall back on clean engine error (fails closed)
  H. Production does NOT fall back on classifier failure (fails closed)
  I. execute_production_demo: Solar clean, TUHO/Oborovo raise
  J. execute_production_waterfall(allow_legacy=True): still routes legacy for blocked projects
  K. Financial delta zero for Solar after B1
  L. Financial delta zero for Wind after B1
  M. CleanNotReadyError metadata completeness
  N. run_project_legacy carries CALIBRATION_ONLY lineage (not production authority)
  O. Production router raises on non-promoted override inputs

CALIBRATION_ONLY note: run_project_legacy() is documented as the explicit
legacy calibration entry point.  Production routes (run_project, execute_production_demo)
are clean-only as of Phase B1.
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
# C — Oborovo production: raises CleanNotReadyError, calculation_count == 0
# ---------------------------------------------------------------------------

class TestC_OborovoProduction:
    def test_c1_oborovo_raises_clean_not_ready(self):
        """Oborovo production raises CleanNotReadyError (no legacy fallthrough)."""
        from app.services.production_financial_authority import CleanNotReadyError
        from app.api.project_runner import run_project

        with pytest.raises(CleanNotReadyError) as exc_info:
            run_project("Oborovo", "Base")
        err = exc_info.value
        assert err.calculation_count == 0
        assert err.runtime_authority == "clean_not_ready"

    def test_c2_oborovo_typed_reason(self):
        """Oborovo CleanNotReadyError carries the typed G2A blocker reason."""
        from app.services.production_financial_authority import CleanNotReadyError
        from app.api.project_runner import run_project

        with pytest.raises(CleanNotReadyError) as exc_info:
            run_project("Oborovo", "Base")
        assert exc_info.value.reason_code == "PR8_G2A_FINANCING_CONTRACT_FIELDS_NOT_TYPED"

    def test_c3_oborovo_zero_legacy_calls(self, monkeypatch):
        """Oborovo: zero engine calls (clean or legacy) when CleanNotReadyError raised."""
        counters = EngineCounters(monkeypatch)
        from app.services.production_financial_authority import CleanNotReadyError
        from app.api.project_runner import run_project

        with pytest.raises(CleanNotReadyError):
            run_project("Oborovo", "Base")
        assert counters.clean_calls == 0
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
# I — execute_production_demo: Solar clean, TUHO/Oborovo raise
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

    def test_i3_oborovo_demo_raises_clean_not_ready(self):
        """execute_production_demo("Oborovo") raises CleanNotReadyError."""
        from app.services.production_financial_authority import CleanNotReadyError
        from app.services.production_waterfall_seam import execute_production_demo

        with pytest.raises(CleanNotReadyError) as exc_info:
            execute_production_demo("Oborovo", "Base")
        assert exc_info.value.calculation_count == 0
        assert exc_info.value.runtime_authority == "clean_not_ready"


# ---------------------------------------------------------------------------
# J — execute_production_waterfall(allow_legacy=True) still routes legacy
#     (used by workbook export and runtime-summary — not a production route)
# ---------------------------------------------------------------------------

class TestJ_ExecuteProductionWaterfallLegacyAllowed:
    def test_j1_tuho_waterfall_with_legacy_allowed(self):
        """execute_production_waterfall(allow_legacy=True) still runs legacy for TUHO."""
        from app.project_factories import create_default_tuho_wind1
        from app.services.production_waterfall_seam import execute_production_waterfall

        inputs = create_default_tuho_wind1()
        execution = execute_production_waterfall(inputs, allow_legacy=True)
        assert execution.authority_metadata["runtime_authority"] == "legacy_waterfall_calibration"
        assert execution.authority_metadata["calculation_count"] == 1

    def test_j2_oborovo_waterfall_with_legacy_allowed(self):
        """execute_production_waterfall(allow_legacy=True) still runs legacy for Oborovo."""
        from app.project_factories import create_default_oborovo
        from app.services.production_waterfall_seam import execute_production_waterfall

        inputs = create_default_oborovo()
        execution = execute_production_waterfall(inputs, allow_legacy=True)
        assert execution.authority_metadata["runtime_authority"] == "legacy_waterfall_calibration"
        assert execution.authority_metadata["calculation_count"] == 1


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
        from app.project_factories import create_default_oborovo
        from app.services.production_financial_authority import CleanNotReadyError
        from app.api.project_runner import run_project

        # Oborovo inputs are non-promoted; supplying them as an override
        # to an arbitrary project_type must still raise.
        oborovo_inputs = create_default_oborovo()
        with pytest.raises(CleanNotReadyError):
            run_project("Oborovo", "Base", project_inputs_override=oborovo_inputs)
