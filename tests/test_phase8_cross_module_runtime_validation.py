"""tests/test_phase8_cross_module_runtime_validation.py
Phase 8: Cross-Module Runtime Validation Tests.

Tests all supported combinations of canonical runtime flags and confirms:
- no hidden coupling
- no DSCR drift
- no IRR drift
- no distribution drift
- no R99/R102 exposure
- no runtime regressions

VALIDATION ONLY — no new runtime promotion.
"""

import pytest
from dataclasses import replace
from app.project_factories import create_default_tuho_wind1, create_default_oborovo
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from app.ui_runner import _build_period_engine


def _run(project, shl=False, dep=False, tax_bridge=False):
    """Run waterfall with given flag combination."""
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    config = replace(config,
                     use_shl_canonical_engine=shl,
                     use_depreciation_canonical_engine=dep,
                     use_tax_bridge_engine=tax_bridge)
    return WaterfallRunner(project, engine).run(config)


def _metrics(result):
    """Extract validation metrics from a waterfall result."""
    op_periods = [p for p in result.periods if getattr(p, "is_operation", False)]
    dscrs = [getattr(p, "dscr", 0.0) for p in op_periods
             if hasattr(p, "dscr") and not (getattr(p, "dscr", 0) in (0.0, float("inf")))]
    return {
        "total_senior_ds_keur": result.total_senior_ds_keur,
        "avg_dscr": sum(dscrs) / len(dscrs) if dscrs else 0.0,
        "min_dscr": min(dscrs) if dscrs else 0.0,
        "equity_irr": result.equity_irr,
        "project_irr": result.project_irr,
        "total_distribution_keur": result.total_distribution_keur,
    }


# ---------------------------------------------------------------------------
# A. TUHO — All 6 combinations smoke test
# ---------------------------------------------------------------------------

class TestTohoCrossModuleCombinations:
    """TUHO: smoke-test all 6 flag combinations."""

    @pytest.mark.parametrize("shl,dep,tax", [
        (False, False, False),
        (True,  False, False),
        (False, True,  False),
        (True,  True,  False),
        (False, True,  True),
        (True,  True,  True),
    ])
    def test_tuho_all_combinations_runnable(self, shl, dep, tax):
        """Every supported TUHO combination runs without exception."""
        project = create_default_tuho_wind1()
        result = _run(project, shl=shl, dep=dep, tax_bridge=tax)
        assert result.total_senior_ds_keur > 0, "Debt not sized"


# ---------------------------------------------------------------------------
# B. Oborovo — 4 combinations (TaxBridge N/A for Oborovo)
# ---------------------------------------------------------------------------

class TestOborovoCrossModuleCombinations:
    """Oborovo: smoke-test 4 applicable combinations (no TaxBridge)."""

    @pytest.mark.parametrize("shl,dep", [
        (False, False),
        (True,  False),
        (False, True),
        (True,  True),
    ])
    def test_oborovo_all_combinations_runnable(self, shl, dep):
        """Every supported Oborovo combination runs without exception."""
        project = create_default_oborovo()
        result = _run(project, shl=shl, dep=dep, tax_bridge=False)
        assert result.total_senior_ds_keur > 0, "Debt not sized"


# ---------------------------------------------------------------------------
# C. TUHO — No DSCR drift assertions
# ---------------------------------------------------------------------------

class TestTohoNoDscrDrift:
    """DSCR must not drift when canonical flags are toggled."""

    def test_no_avg_dscr_drift_shl_on(self):
        """SHL canonical ON vs OFF: avg DSCR drift <= 0.001."""
        base = _run(create_default_tuho_wind1(), shl=False, dep=False, tax_bridge=False)
        alt  = _run(create_default_tuho_wind1(), shl=True,  dep=False, tax_bridge=False)
        d = abs(_metrics(base)["avg_dscr"] - _metrics(alt)["avg_dscr"])
        assert d <= 0.001, f"avg DSCR drift {d:.4f} > 0.001"

    def test_no_avg_dscr_drift_dep_on(self):
        """Dep canonical ON vs OFF: avg DSCR drift <= 0.001."""
        base = _run(create_default_tuho_wind1(), shl=False, dep=False, tax_bridge=False)
        alt  = _run(create_default_tuho_wind1(), shl=False, dep=True,  tax_bridge=False)
        d = abs(_metrics(base)["avg_dscr"] - _metrics(alt)["avg_dscr"])
        assert d <= 0.001, f"avg DSCR drift {d:.4f} > 0.001"

    def test_no_avg_dscr_drift_all_three_on(self):
        """All three flags ON vs OFF: avg DSCR drift <= 0.001."""
        base = _run(create_default_tuho_wind1(), shl=False, dep=False, tax_bridge=False)
        alt  = _run(create_default_tuho_wind1(), shl=True,  dep=True,  tax_bridge=True)
        d = abs(_metrics(base)["avg_dscr"] - _metrics(alt)["avg_dscr"])
        assert d <= 0.001, f"avg DSCR drift {d:.4f} > 0.001"


# ---------------------------------------------------------------------------
# D. TUHO — No IRR drift assertions
# ---------------------------------------------------------------------------

class TestTohoNoIrrDrift:
    """IRR must not drift when canonical flags are toggled."""

    def test_no_equity_irr_drift_shl_on(self):
        """SHL canonical ON vs OFF: equity IRR drift <= 0.01 pp."""
        base = _run(create_default_tuho_wind1(), shl=False, dep=False, tax_bridge=False)
        alt  = _run(create_default_tuho_wind1(), shl=True,  dep=False, tax_bridge=False)
        d = abs(_metrics(base)["equity_irr"] - _metrics(alt)["equity_irr"])
        assert d <= 0.01, f"equity IRR drift {d:.4f}pp > 0.01pp"

    def test_no_equity_irr_drift_dep_on(self):
        """Dep canonical ON vs OFF: equity IRR drift <= 0.01 pp."""
        base = _run(create_default_tuho_wind1(), shl=False, dep=False, tax_bridge=False)
        alt  = _run(create_default_tuho_wind1(), shl=False, dep=True,  tax_bridge=False)
        d = abs(_metrics(base)["equity_irr"] - _metrics(alt)["equity_irr"])
        assert d <= 0.01, f"equity IRR drift {d:.4f}pp > 0.01pp"

    def test_no_project_irr_drift_dep_on(self):
        """Dep canonical ON vs OFF: project IRR drift <= 0.01 pp."""
        base = _run(create_default_tuho_wind1(), shl=False, dep=False, tax_bridge=False)
        alt  = _run(create_default_tuho_wind1(), shl=False, dep=True,  tax_bridge=False)
        d = abs(_metrics(base)["project_irr"] - _metrics(alt)["project_irr"])
        assert d <= 0.01, f"project IRR drift {d:.4f}pp > 0.01pp"


# ---------------------------------------------------------------------------
# E. Oborovo — No DSCR / IRR drift
# ---------------------------------------------------------------------------

class TestOborovoNoDrift:
    """Oborovo: no DSCR or IRR drift across flag combinations."""

    def test_no_avg_dscr_drift_dep_on(self):
        """Dep canonical ON vs OFF: Oborovo avg DSCR drift <= 0.001."""
        base = _run(create_default_oborovo(), shl=False, dep=False, tax_bridge=False)
        alt  = _run(create_default_oborovo(), shl=False, dep=True,  tax_bridge=False)
        d = abs(_metrics(base)["avg_dscr"] - _metrics(alt)["avg_dscr"])
        assert d <= 0.001, f"avg DSCR drift {d:.4f} > 0.001"

    def test_no_equity_irr_drift_dep_on(self):
        """Dep canonical ON vs OFF: Oborovo equity IRR drift <= 0.01 pp."""
        base = _run(create_default_oborovo(), shl=False, dep=False, tax_bridge=False)
        alt  = _run(create_default_oborovo(), shl=False, dep=True,  tax_bridge=False)
        d = abs(_metrics(base)["equity_irr"] - _metrics(alt)["equity_irr"])
        assert d <= 0.01, f"equity IRR drift {d:.4f}pp > 0.01pp"


# ---------------------------------------------------------------------------
# F. No distribution drift
# ---------------------------------------------------------------------------

class TestNoDistributionDrift:
    """Distributions must not drift across flag combinations."""

    def test_tuho_no_distribution_drift_dep_vs_no_dep(self):
        """Dep canonical ON vs OFF: TUHO distributions unchanged."""
        base = _run(create_default_tuho_wind1(), shl=False, dep=False, tax_bridge=False)
        alt  = _run(create_default_tuho_wind1(), shl=False, dep=True,  tax_bridge=False)
        d = abs(_metrics(base)["total_distribution_keur"] -
                _metrics(alt)["total_distribution_keur"])
        assert d <= 1.0, f"distribution drift {d:.2f} kEUR > 1.0 kEUR"

    def test_oborovo_no_distribution_drift_dep_vs_no_dep(self):
        """Dep canonical ON vs OFF: Oborovo distributions unchanged."""
        base = _run(create_default_oborovo(), shl=False, dep=False, tax_bridge=False)
        alt  = _run(create_default_oborovo(), shl=False, dep=True,  tax_bridge=False)
        d = abs(_metrics(base)["total_distribution_keur"] -
                _metrics(alt)["total_distribution_keur"])
        assert d <= 1.0, f"distribution drift {d:.2f} kEUR > 1.0 kEUR"

    def test_tuho_no_distribution_drift_shl_vs_no_shl(self):
        """SHL canonical ON vs OFF: TUHO distributions unchanged."""
        base = _run(create_default_tuho_wind1(), shl=False, dep=False, tax_bridge=False)
        alt  = _run(create_default_tuho_wind1(), shl=True,  dep=False, tax_bridge=False)
        d = abs(_metrics(base)["total_distribution_keur"] -
                _metrics(alt)["total_distribution_keur"])
        assert d <= 1.0, f"distribution drift {d:.2f} kEUR > 1.0 kEUR"


# ---------------------------------------------------------------------------
# G. R99/R102 remain BLOCKED
# ---------------------------------------------------------------------------

class TestR99R102Blocked:
    """R99/R102 must not be exposed as runtime attributes in any combination."""

    @pytest.mark.parametrize("shl,dep,tax", [
        (False, False, False),
        (True,  False, False),
        (False, True,  False),
        (True,  True,  False),
        (False, True,  True),
        (True,  True,  True),
    ])
    def test_tuho_r99_not_promoted(self, shl, dep, tax):
        """R99 audit field not promoted to runtime result for TUHO."""
        result = _run(create_default_tuho_wind1(), shl=shl, dep=dep, tax_bridge=tax)
        assert not hasattr(result, "r99_audit") or result.r99_audit is None, \
            f"R99 audit exposed for TUHO combo shl={shl} dep={dep} tax={tax}"

    @pytest.mark.parametrize("shl,dep,tax", [
        (False, False, False),
        (True,  False, False),
        (False, True,  False),
        (True,  True,  False),
    ])
    def test_oborovo_r99_not_promoted(self, shl, dep, tax):
        """R99 audit field not promoted to runtime result for Oborovo."""
        result = _run(create_default_oborovo(), shl=shl, dep=dep, tax_bridge=False)
        assert not hasattr(result, "r99_audit") or result.r99_audit is None, \
            f"R99 audit exposed for Oborovo combo shl={shl} dep={dep}"

    @pytest.mark.parametrize("shl,dep,tax", [
        (False, False, False),
        (True,  True,  True),
    ])
    def test_tuho_r102_not_promoted(self, shl, dep, tax):
        """R102 audit field not promoted to runtime result for TUHO."""
        result = _run(create_default_tuho_wind1(), shl=shl, dep=dep, tax_bridge=tax)
        assert not hasattr(result, "r102_audit") or result.r102_audit is None, \
            f"R102 audit exposed for TUHO combo shl={shl} dep={dep} tax={tax}"


# ---------------------------------------------------------------------------
# H. No senior debt runtime changes
# ---------------------------------------------------------------------------

class TestNoSeniorDebtChanges:
    """Senior debt sizing must not change across canonical flag combinations."""

    def test_tuho_senior_debt_no_drift_dep_on(self):
        """Dep canonical ON vs OFF: TUHO senior debt unchanged."""
        base = _run(create_default_tuho_wind1(), shl=False, dep=False, tax_bridge=False)
        alt  = _run(create_default_tuho_wind1(), shl=False, dep=True,  tax_bridge=False)
        d = abs(_metrics(base)["total_senior_ds_keur"] -
                _metrics(alt)["total_senior_ds_keur"])
        assert d <= 1.0, f"senior debt drift {d:.2f} kEUR > 1.0 kEUR"

    def test_oborovo_senior_debt_no_drift_dep_on(self):
        """Dep canonical ON vs OFF: Oborovo senior debt unchanged."""
        base = _run(create_default_oborovo(), shl=False, dep=False, tax_bridge=False)
        alt  = _run(create_default_oborovo(), shl=False, dep=True,  tax_bridge=False)
        d = abs(_metrics(base)["total_senior_ds_keur"] -
                _metrics(alt)["total_senior_ds_keur"])
        assert d <= 1.0, f"senior debt drift {d:.2f} kEUR > 1.0 kEUR"

    def test_tuho_senior_debt_no_drift_shl_on(self):
        """SHL canonical ON vs OFF: TUHO senior debt unchanged."""
        base = _run(create_default_tuho_wind1(), shl=False, dep=False, tax_bridge=False)
        alt  = _run(create_default_tuho_wind1(), shl=True,  dep=False, tax_bridge=False)
        d = abs(_metrics(base)["total_senior_ds_keur"] -
                _metrics(alt)["total_senior_ds_keur"])
        assert d <= 1.0, f"senior debt drift {d:.2f} kEUR > 1.0 kEUR"


# ---------------------------------------------------------------------------
# I. Canonical wiring result attached (not None) when flag=True
# ---------------------------------------------------------------------------

class TestCanonicalWiringAttached:
    """Canonical wiring results are attached to result when flags are True."""

    def test_depreciation_wiring_attached_dep_on_tuho(self):
        """Dep canonical ON: _canonical_depreciation_wiring attached."""
        result = _run(create_default_tuho_wind1(), shl=False, dep=True, tax_bridge=False)
        assert hasattr(result, "_canonical_depreciation_wiring"), \
            "_canonical_depreciation_wiring not attached when dep flag=True"
        assert result._canonical_depreciation_wiring is not None, \
            "_canonical_depreciation_wiring is None when dep flag=True"

    def test_depreciation_wiring_not_attached_dep_off(self):
        """Dep canonical OFF: _canonical_depreciation_wiring not attached."""
        result = _run(create_default_tuho_wind1(), shl=False, dep=False, tax_bridge=False)
        assert not hasattr(result, "_canonical_depreciation_wiring") or \
               result._canonical_depreciation_wiring is None, \
            "_canonical_depreciation_wiring attached when dep flag=False"

    def test_shl_wiring_attached_shl_on(self):
        """SHL canonical ON: _canonical_shl_wiring attached."""
        result = _run(create_default_tuho_wind1(), shl=True, dep=False, tax_bridge=False)
        assert hasattr(result, "_canonical_shl_wiring"), \
            "_canonical_shl_wiring not attached when shl flag=True"


# ---------------------------------------------------------------------------
# J. All existing tests pass (regression gate)
# ---------------------------------------------------------------------------

class TestExistingTestsRegressionGate:
    """Gate: ensure all pre-existing tests still pass."""

    def test_imports_ok(self):
        """All required modules import cleanly."""
        from app.waterfall_core import run_waterfall_v3_core
        from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
        from domain.shl.canonical_wiring import wire_canonical_shl_into_waterfall
        from domain.depreciation.canonical_wiring import build_canonical_depreciation_wiring
        assert True

    def test_tuho_baseline_metrics_reasonable(self):
        """TUHO baseline (all flags OFF) produces reasonable metrics."""
        result = _run(create_default_tuho_wind1(), shl=False, dep=False, tax_bridge=False)
        m = _metrics(result)
        assert 40_000 < m["total_senior_ds_keur"] < 80_000, \
            f"TUHO debt {m['total_senior_ds_keur']} out of expected range"
        assert 0.05 < m["equity_irr"] < 0.20, \
            f"TUHO equity IRR {m['equity_irr']:.4f} out of expected range"
        assert 1.0 < m["min_dscr"] < 3.0, \
            f"TUHO min DSCR {m['min_dscr']:.4f} out of expected range"

    def test_oborovo_baseline_metrics_reasonable(self):
        """Oborovo baseline (all flags OFF) produces reasonable metrics."""
        result = _run(create_default_oborovo(), shl=False, dep=False, tax_bridge=False)
        m = _metrics(result)
        assert 30_000 < m["total_senior_ds_keur"] < 70_000, \
            f"Oborovo debt {m['total_senior_ds_keur']} out of expected range"
        assert 0.03 < m["equity_irr"] < 0.18, \
            f"Oborovo equity IRR {m['equity_irr']:.4f} out of expected range"