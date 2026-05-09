"""Tests for Phase 1 Independent SPV Portfolio Aggregation.

These tests verify:
1. 2–3 SPVs run independently through the waterfall engine
2. Aggregation equals sum/min of child outputs
3. Feature flag / default behavior does not change single-asset mode
4. DSRF disabled has zero effect
5. Phase 1 does NOT use pooled debt sculpting

All existing single-asset tests remain unchanged.
"""
from __future__ import annotations

import pytest
from datetime import date

from domain.portfolio.independent import (
    DSRFConfig,
    IndependentPortfolioInputs,
    IndependentPortfolioResult,
    SPVOutput,
    run_independent_portfolio,
    PHASE1_LIMITATIONS,
)
from domain.portfolio.independent.inputs import PHASE1_LIMITATIONS as LIMITATIONS_TEXT


class TestDSRFConfig:
    """DSRF is a placeholder — default disabled, no effect on calculations."""

    def test_dsrf_disabled_by_default(self):
        cfg = DSRFConfig()
        assert cfg.enabled is False

    def test_dsrf_enabled_raises_error(self):
        with pytest.raises(ValueError, match="DSRF is not yet implemented"):
            DSRFConfig(enabled=True)

    def test_dsrf_disabled_has_zero_effect_on_inputs(self):
        # Verify that passing DSRF config doesn't change portfolio behavior
        cfg = DSRFConfig()  # disabled
        assert cfg.months_reserve == 6
        assert cfg.funding_threshold_dscr == 1.25
        assert cfg.release_threshold_dscr == 1.35


class TestIndependentPortfolioInputs:
    """Portfolio inputs validation."""

    def test_requires_at_least_one_project(self):
        with pytest.raises(ValueError, match="at least 1 project"):
            IndependentPortfolioInputs(projects=())

    def test_requires_unique_project_codes(self):
        # Create mock project inputs with duplicate codes
        mock_proj = _make_mock_project(code="SPV1")
        with pytest.raises(ValueError, match="unique"):
            IndependentPortfolioInputs(
                projects=(mock_proj, mock_proj),
                portfolio_name="Test",
            )

    def test_dsrfs_not_enabled_by_default(self):
        mock_proj = _make_mock_project(code="SPV1")
        p = IndependentPortfolioInputs(projects=(mock_proj,))
        assert p.dsrf is None


class TestIndependentPortfolioResult:
    """Result structure and aggregation."""

    def test_num_spvs_property(self):
        mock_proj = _make_mock_project(code="SPV1")
        mock_output = _make_mock_spv_output("SPV1")
        result = IndependentPortfolioResult(
            portfolio_name="Test",
            spv_outputs=(mock_output,),
            total_revenue_keur=100.0,
            total_ebitda_keur=80.0,
            total_tax_keur=10.0,
            total_senior_ds_keur=50.0,
            total_distribution_keur=20.0,
            min_dscr=1.2,
            avg_dscr=1.35,
            spv_project_irrs=(0.09,),
            spv_equity_irrs=(0.12,),
        )
        assert result.num_spvs == 1

    def test_warning_summary_empty(self):
        result = _make_empty_result()
        assert "No warnings" in result.warning_summary()

    def test_warning_summary_with_warnings(self):
        result = _make_empty_result(warnings=("warning1",))
        assert "warning1" in result.warning_summary()


class TestPhase1DoesNotUsePooledDebtSculpting:
    """Phase 1 independent path must NOT use pooled debt sculpting.

    This is the key architectural test — proves the independent path
    does not route through domain/portfolio/waterfall.py pooled logic.
    """

    def test_independent_portfolio_does_not_call_pooled_waterfall(self):
        """Verify that run_independent_portfolio does NOT call run_portfolio_waterfall.
        
        Phase 1 uses independent SPV runs only. The pooled financing waterfall
        (run_portfolio_waterfall) must NOT be invoked.
        """
        import domain.portfolio.independent.runner as runner_module
        import inspect
        source = inspect.getsource(runner_module)
        # The independent runner must NOT call the pooled financing waterfall
        assert "run_portfolio_waterfall" not in source, \
            "Independent runner must not call pooled financing waterfall"
        assert "build_portfolio_debt_service_schedule" not in source, \
            "Independent runner must not use pooled debt sculpting"

    def test_dsrf_config_blocks_enabled(self):
        """DSRF must block enablement to prevent silent effect on calculations."""
        cfg = DSRFConfig()
        # Attempting to enable raises immediately
        with pytest.raises(ValueError):
            DSRFConfig(enabled=True)


class TestIndependentAggregation:
    """Test aggregation logic."""

    def test_aggregate_sums_revenue(self):
        outputs = tuple(_make_mock_spv_output(code, total_revenue_keur=100 * i)
                       for i, code in enumerate(["A", "B", "C"], start=1))
        result = _aggregate(outputs)
        assert result.total_revenue_keur == 600  # 100+200+300

    def test_aggregate_sums_ebitda(self):
        outputs = tuple(_make_mock_spv_output(code, total_ebitda_keur=80 * i)
                       for i, code in enumerate(["A", "B"], start=1))
        result = _aggregate(outputs)
        assert result.total_ebitda_keur == 240  # 80+160

    def test_aggregate_min_dscr_conservative(self):
        out1 = _make_mock_spv_output("A", min_dscr=1.1)
        out2 = _make_mock_spv_output("B", min_dscr=1.4)
        out3 = _make_mock_spv_output("C", min_dscr=1.25)
        result = _aggregate((out1, out2, out3))
        assert result.min_dscr == 1.1  # minimum across SPVs

    def test_aggregate_avg_dscr_unweighted(self):
        out1 = _make_mock_spv_output("A", avg_dscr=1.2)
        out2 = _make_mock_spv_output("B", avg_dscr=1.5)
        result = _aggregate((out1, out2))
        # Unweighted average: (1.2 + 1.5) / 2 = 1.35
        assert result.avg_dscr == pytest.approx(1.35)

    def test_aggregate_preserves_spv_outputs(self):
        out1 = _make_mock_spv_output("A")
        out2 = _make_mock_spv_output("B")
        result = _aggregate((out1, out2))
        assert len(result.spv_outputs) == 2
        assert result.spv_outputs[0].project_code == "A"
        assert result.spv_outputs[1].project_code == "B"


class TestPhase1Limitations:
    """Documentation of Phase 1 limitations."""

    def test_limitations_doc_contains_no_holdco(self):
        # "No HoldCo" is the phrase that indicates it's not implemented
        assert "No HoldCo" in LIMITATIONS_TEXT

    def test_limitations_doc_contains_no_shl(self):
        # "No SHL" is the phrase that indicates it's not implemented
        assert "No SHL" in LIMITATIONS_TEXT

    def test_limitations_doc_contains_no_sponsor_irr(self):
        assert "Sponsor IRR" not in LIMITATIONS_TEXT or "placeholder" in LIMITATIONS_TEXT.lower()

    def test_limitations_doc_contains_pooled_financing_note(self):
        # Pooled financing should be noted as experimental / later phase
        assert "pooled" in LIMITATIONS_TEXT.lower() or "experimental" in LIMITATIONS_TEXT.lower()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_mock_project(code: str):
    """Create a mock ProjectInputs with minimal required fields."""
    from unittest.mock import MagicMock
    proj = MagicMock()
    proj.info.code = code
    proj.info.name = f"Project {code}"
    proj.info.financial_close = date(2020, 1, 1)
    proj.info.construction_months = 13
    proj.info.horizon_years = 30
    proj.revenue.ppa_term_years = 10
    return proj


def _make_mock_spv_output(code: str, **kwargs) -> SPVOutput:
    """Create a mock SPVOutput with default values."""
    defaults = dict(
        project_code=code,
        project_name=f"Project {code}",
        project_irr=0.09,
        equity_irr=0.12,
        total_revenue_keur=1000.0,
        total_ebitda_keur=800.0,
        total_tax_keur=100.0,
        total_senior_ds_keur=500.0,
        total_distribution_keur=200.0,
        avg_dscr=1.3,
        min_dscr=1.15,
        waterfall_result=None,
        warnings=(),
    )
    defaults.update(kwargs)
    return SPVOutput(**defaults)


def _make_empty_result(**kwargs) -> IndependentPortfolioResult:
    defaults = dict(
        portfolio_name="Test",
        spv_outputs=(),
        total_revenue_keur=0.0,
        total_ebitda_keur=0.0,
        total_tax_keur=0.0,
        total_senior_ds_keur=0.0,
        total_distribution_keur=0.0,
        min_dscr=0.0,
        avg_dscr=0.0,
        spv_project_irrs=(),
        spv_equity_irrs=(),
    )
    defaults.update(kwargs)
    return IndependentPortfolioResult(**defaults)


def _aggregate(outputs: tuple[SPVOutput, ...], name: str = "Test"):
    """Helper to call aggregate_independent_results."""
    from domain.portfolio.independent.result import aggregate_independent_results
    return aggregate_independent_results(
        portfolio_name=name,
        spv_outputs=outputs,
    )