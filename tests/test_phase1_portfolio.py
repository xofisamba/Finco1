"""Tests for Phase 1 Independent SPV Portfolio Aggregation.

Scope: Phase 1 independent SPV aggregation (no pooled financing, no DSRF).
"""
from __future__ import annotations

import math
import pytest
from datetime import date
from unittest.mock import MagicMock

# ── Imports ──────────────────────────────────────────────────────────────────

from domain.portfolio.independent import (
    DSRFConfig,
    IndependentPortfolioInputs,
    IndependentPortfolioResult,
    SPVOutput,
    aggregate_independent_results,
    run_independent_portfolio,
    SPVWaterfallError,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_project(code: str) -> MagicMock:
    """Minimal mock project (code only, no real engine)."""
    p = MagicMock()
    p.info.code = code
    p.info.name = f"Project {code}"
    p.info.financial_close = date(2030, 1, 1)
    p.info.construction_months = 12
    p.info.horizon_years = 25
    p.revenue.ppa_term_years = 10
    return p


_NOT_SET = object()


def _mock_spv_output(
    code: str,
    project_irr: float = _NOT_SET,
    equity_irr: float = _NOT_SET,
    total_revenue_keur: float = 1000.0,
    total_ebitda_keur: float = 800.0,
    total_tax_keur: float = 100.0,
    total_senior_ds_keur: float = 500.0,
    total_distribution_keur: float = 200.0,
    avg_dscr: float = 1.3,
    min_dscr: float = 1.15,
    waterfall_result=_NOT_SET,
    warnings: tuple = (),
) -> SPVOutput:
    # When waterfall_result is None (explicit or implicit), zero out IRR values
    _wf_none = waterfall_result is None
    _proj_irr = 0.0 if _wf_none else (project_irr if project_irr is not _NOT_SET else 0.09)
    _eq_irr = 0.0 if _wf_none else (equity_irr if equity_irr is not _NOT_SET else 0.12)
    _wf = None if _wf_none else (waterfall_result if waterfall_result is not _NOT_SET else None)
    return SPVOutput(
        project_code=code,
        project_name=f"Project {code}",
        project_irr=_proj_irr,
        equity_irr=_eq_irr,
        total_revenue_keur=total_revenue_keur,
        total_ebitda_keur=total_ebitda_keur,
        total_tax_keur=total_tax_keur,
        total_senior_ds_keur=total_senior_ds_keur,
        total_distribution_keur=total_distribution_keur,
        avg_dscr=avg_dscr,
        min_dscr=min_dscr,
        waterfall_result=waterfall_result,
        warnings=warnings,
    )


# ── DSRF — disabled-only placeholder ────────────────────────────────────────

class TestDSRFConfig:
    def test_disabled_by_default(self):
        cfg = DSRFConfig()
        assert cfg.enabled is False

    def test_enabled_with_valid_params_no_raise(self):
        # New DSRFConfig raises only for invalid params, not just because enabled=True
        cfg = DSRFConfig(
            enabled=True,
            sizing_months=6,
            sizing_basis="average_debt_service",
            commitment_fee_rate_pa=0.005,
            margin_rate_pa=0.02,
            euribor_rate_pa=0.03,
            period_year_fraction=0.5,
            repayment_priority="before_distributions",
        )
        assert cfg.enabled is True
        assert cfg.sizing_months == 6

    def test_enabled_invalid_sizing_months_raises(self):
        with pytest.raises(ValueError, match="sizing_months"):
            DSRFConfig(enabled=True, sizing_months=7)

    def test_disabled_params_unchanged(self):
        cfg = DSRFConfig()
        assert cfg.sizing_months == 6
        assert cfg.sizing_basis == "average_debt_service"
        assert cfg.commitment_fee_rate_pa == 0.0
        assert cfg.margin_rate_pa == 0.0
        assert cfg.euribor_rate_pa == 0.0
        assert cfg.period_year_fraction == 0.5
        assert cfg.repayment_priority == "before_distributions"


# ── IndependentPortfolioInputs ────────────────────────────────────────────────

class TestIndependentPortfolioInputs:
    def test_requires_at_least_one_project(self):
        with pytest.raises(ValueError, match="at least 1"):
            IndependentPortfolioInputs(projects=())

    def test_rejects_duplicate_codes(self):
        p1 = _mock_project("A")
        p2 = _mock_project("A")
        with pytest.raises(ValueError, match="unique"):
            IndependentPortfolioInputs(projects=(p1, p2))

    def test_dsrf_none_by_default(self):
        p = _mock_project("X")
        inp = IndependentPortfolioInputs(projects=(p,))
        assert inp.dsrf is None


# ── IndependentPortfolioResult ────────────────────────────────────────────────

class TestIndependentPortfolioResult:
    def test_num_spvs(self):
        out = _mock_spv_output("A")
        result = _make_result([out])
        assert result.num_spvs == 1

    def test_warning_summary_empty(self):
        result = _make_result([])
        assert "No warnings" in result.warning_summary()

    def test_warning_summary_with_warnings(self):
        out = _mock_spv_output("A", warnings=("warn1",))
        result = _make_result([out])
        assert "warn1" in result.warning_summary()


# ── aggregate_independent_results ────────────────────────────────────────────

class TestAggregate:
    def test_sums_revenue(self):
        out1 = _mock_spv_output("A", total_revenue_keur=100.0)
        out2 = _mock_spv_output("B", total_revenue_keur=200.0)
        result = _make_result([out1, out2])
        assert result.total_revenue_keur == 300.0

    def test_sums_ebitda(self):
        out1 = _mock_spv_output("A", total_ebitda_keur=80.0)
        out2 = _mock_spv_output("B", total_ebitda_keur=120.0)
        result = _make_result([out1, out2])
        assert result.total_ebitda_keur == 200.0

    def test_min_dscr_conservative(self):
        out1 = _mock_spv_output("A", min_dscr=1.4)
        out2 = _mock_spv_output("B", min_dscr=1.1)
        result = _make_result([out1, out2])
        assert result.min_dscr == 1.1

    def test_avg_dscr_unweighted(self):
        out1 = _mock_spv_output("A", avg_dscr=1.2)
        out2 = _mock_spv_output("B", avg_dscr=1.4)
        result = _make_result([out1, out2])
        assert result.avg_dscr == pytest.approx(1.3)


# ── IRR averaging: all finite values included, no silent filtering ──────────

class TestIRRAveraging:
    """IRR averaging must include all finite values — 0, positive, negative.
    No silent filtering.
    """

    def test_zero_project_irr_included(self):
        out1 = _mock_spv_output("A", project_irr=0.0)
        out2 = _mock_spv_output("B", project_irr=0.10)
        result = _make_result([out1, out2])
        # Average: (0.0 + 0.10) / 2 = 0.05
        assert result.simple_avg_project_irr == 0.05

    def test_negative_project_irr_included(self):
        out1 = _mock_spv_output("A", project_irr=-0.05)
        out2 = _mock_spv_output("B", project_irr=0.10)
        result = _make_result([out1, out2])
        # Average: (-0.05 + 0.10) / 2 = 0.025
        assert result.simple_avg_project_irr == 0.025

    def test_zero_equity_irr_included(self):
        out1 = _mock_spv_output("A", equity_irr=0.0)
        out2 = _mock_spv_output("B", equity_irr=0.12)
        result = _make_result([out1, out2])
        assert result.simple_avg_equity_irr == 0.06

    def test_nan_filtered_out(self):
        out1 = _mock_spv_output("A", project_irr=float("nan"))
        out2 = _mock_spv_output("B", project_irr=0.10)
        result = _make_result([out1, out2])
        # NaN is not finite; should be excluded
        assert math.isfinite(result.simple_avg_project_irr)
        assert result.simple_avg_project_irr == 0.10

    def test_all_nan_yields_zero(self):
        out1 = _mock_spv_output("A", project_irr=float("nan"))
        out2 = _mock_spv_output("B", project_irr=float("nan"))
        result = _make_result([out1, out2])
        assert result.simple_avg_project_irr == 0.0

    def test_mixed_finite_and_nan(self):
        out1 = _mock_spv_output("A", project_irr=0.08)
        out2 = _mock_spv_output("B", project_irr=float("nan"))
        out3 = _mock_spv_output("C", project_irr=0.12)
        result = _make_result([out1, out2, out3])
        assert result.simple_avg_project_irr == 0.10  # (0.08+0.12)/2


# ── SPVOutput — None waterfall_result in non-strict mode ─────────────────────

class TestSPVOutputNoneWaterfall:
    def test_none_waterfall_result_allowed(self):
        out = _mock_spv_output("A", waterfall_result=None)
        assert out.waterfall_result is None
        assert out.project_irr == 0.0
        assert out.equity_irr == 0.0

    def test_none_waterfall_result_in_result(self):
        out1 = _mock_spv_output("A", waterfall_result=None)
        out2 = _mock_spv_output("B")
        result = _make_result([out1, out2])
        assert result.spv_outputs[0].waterfall_result is None
        assert result.spv_outputs[1].waterfall_result is not None


# ── Strict vs non-strict mode ─────────────────────────────────────────────────

class TestStrictMode:
    def test_strict_raises_on_failure(self):
        bad = _mock_project("BAD")
        # Hook: make waterfall fail
        bad.info.code = "BAD"
        bad.info.name = "Bad Project"
        bad.info.financial_close = date(2030, 1, 1)
        bad.info.construction_months = 12
        bad.info.horizon_years=25
        bad.revenue.ppa_term_years=10
        bad.financing = None
        bad.tax = None
        bad.capex = None

        portfolio = IndependentPortfolioInputs(projects=(bad,))
        with pytest.raises(SPVWaterfallError) as exc_info:
            run_independent_portfolio(portfolio, strict=True)
        assert "BAD" in str(exc_info.value)

    def test_nonstrict_includes_zero_output_with_warning(self):
        bad = _mock_project("BAD")
        bad.info.code = "BAD"
        bad.info.name = "Bad Project"
        bad.info.financial_close = date(2030, 1, 1)
        bad.info.construction_months = 12
        bad.info.horizon_years=25
        bad.revenue.ppa_term_years=10
        bad.financing = None
        bad.tax = None
        bad.capex = None

        portfolio = IndependentPortfolioInputs(projects=(bad,))
        result = run_independent_portfolio(portfolio, strict=False)

        assert result.num_spvs == 1
        assert result.spv_outputs[0].total_revenue_keur == 0.0
        assert len(result.warnings) >= 1
        assert "BAD" in result.warnings[0]


# ── Real engine integration ─────────────────────────────────────────────────

class TestRealEngineIntegration:
    @pytest.fixture(autouse=True)
    def _oborovo_shim(self):
        import app.project_factories  # noqa: F401

    def test_two_solar_spvs_run_independently(self):
        from app.project_factories import create_default_solar_project
        from dataclasses import replace

        s1 = replace(create_default_solar_project(), info=replace(
            create_default_solar_project().info,
            code="SOLAR-T1", name="Solar T1"))
        s2 = replace(create_default_solar_project(), info=replace(
            create_default_solar_project().info,
            code="SOLAR-T2", name="Solar T2"))

        portfolio = IndependentPortfolioInputs(projects=(s1, s2))
        result = run_independent_portfolio(portfolio, strict=True)

        assert result.num_spvs == 2
        assert result.total_revenue_keur > 0
        assert result.total_ebitda_keur > 0
        assert all(r > 0 for r in result.spv_project_irrs)

    def test_aggregate_revenue_equals_sum_of_children(self):
        from app.project_factories import create_default_solar_project
        from dataclasses import replace
        s1 = create_default_solar_project()
        s2 = create_default_solar_project()
        s1 = replace(s1, info=replace(s1.info, code="SR1"))
        s2 = replace(s2, info=replace(s2.info, code="SR2"))
        portfolio = IndependentPortfolioInputs(projects=(s1, s2))
        result = run_independent_portfolio(portfolio, strict=True)

        expected = sum(o.total_revenue_keur for o in result.spv_outputs)
        assert result.total_revenue_keur == pytest.approx(expected)

    def test_dsrf_none_same_as_disabled(self):
        from app.project_factories import create_default_solar_project
        from dataclasses import replace

        p = replace(create_default_solar_project(), info=replace(
            create_default_solar_project().info, code="DSRF-TEST"))

        r1 = run_independent_portfolio(
            IndependentPortfolioInputs(projects=(p,)), strict=True)

        r2 = run_independent_portfolio(
            IndependentPortfolioInputs(
                projects=(p,),
                dsrf=DSRFConfig(enabled=False),
            ),
            strict=True,
        )
        # Results must be identical (DSRF disabled has zero impact)
        assert r1.total_revenue_keur == r2.total_revenue_keur
        assert r1.total_ebitda_keur == r2.total_ebitda_keur
        assert r1.total_senior_ds_keur == r2.total_senior_ds_keur
        assert r1.num_spvs == r2.num_spvs

# ── Architectural guard ──────────────────────────────────────────────────────

class TestNoPooledDebtSculpting:
    def test_runner_does_not_call_pooled_waterfall(self):
        import inspect
        from domain.portfolio.independent import runner
        src = inspect.getsource(runner)
        assert "run_portfolio_waterfall" not in src
        assert "build_portfolio_debt_service_schedule" not in src

    def test_dsrf_enabled_with_valid_config_no_raise(self):
        # DSRFConfig(enabled=True) is allowed with valid parameters
        cfg = DSRFConfig(
            enabled=True,
            sizing_months=6,
            sizing_basis="average_debt_service",
            commitment_fee_rate_pa=0.005,
            margin_rate_pa=0.02,
            euribor_rate_pa=0.03,
        )
        assert cfg.enabled is True


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _make_result(spv_outputs: list[SPVOutput]) -> IndependentPortfolioResult:
    return aggregate_independent_results(
        portfolio_name="Test",
        spv_outputs=tuple(spv_outputs),
    )
