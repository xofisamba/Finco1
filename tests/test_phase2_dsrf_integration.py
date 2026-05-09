"""Tests for Phase 2 DSRF integration into portfolio runner and result model."""
from __future__ import annotations

import pytest

from domain.portfolio.independent import IndependentPortfolioInputs, DSRFConfig
from domain.portfolio.independent.inputs import DSRFConfig as InputsDSRFConfig
from domain.portfolio.independent.dsrf import DSRFConfig as DsrfDSRFConfig
from domain.portfolio.independent.runner import run_independent_portfolio
from domain.portfolio.independent.result import SPVOutput, IndependentPortfolioResult


# =============================================================================
# 1. DSRFConfig import/backward compatibility
# =============================================================================

def test_dsrf_config_same_class():
    """DSRFConfig from inputs.py and dsrf.py must be the same class."""
    assert DSRFConfig is InputsDSRFConfig
    assert DSRFConfig is DsrfDSRFConfig


def test_dsrf_config_enabled_false_safe():
    """DSRFConfig(enabled=False) must not raise."""
    config = DSRFConfig(enabled=False)
    assert config.enabled is False


def test_dsrf_config_enabled_true_valid():
    """DSRFConfig(enabled=True) with valid args must not raise."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        sizing_basis="average_debt_service",
        commitment_fee_rate_pa=0.005,
        margin_rate_pa=0.02,
        euribor_rate_pa=0.03,
        period_year_fraction=0.5,
        repayment_priority="before_distributions",
    )
    assert config.enabled is True
    assert config.sizing_months == 6


def test_dsrf_config_enabled_true_invalid_sizing_months():
    with pytest.raises(ValueError, match="sizing_months"):
        DSRFConfig(enabled=True, sizing_months=7)


def test_dsrf_config_enabled_true_invalid_sizing_basis():
    with pytest.raises(ValueError, match="sizing_basis"):
        DSRFConfig(enabled=True, sizing_months=6, sizing_basis="invalid")


def test_dsrf_config_enabled_true_invalid_repayment_priority():
    with pytest.raises(ValueError, match="repayment_priority"):
        DSRFConfig(enabled=True, sizing_months=6, repayment_priority="after_distributions")


# =============================================================================
# 2. Result model has DSRF fields
# =============================================================================

def test_spv_output_has_dsrf_fields():
    """SPVOutput must have DSRF facility fields with correct defaults."""
    fields = SPVOutput.__dataclass_fields__
    assert "dsrf_facility_limit_keur" in fields
    assert "dsrf_total_draw_keur" in fields
    assert "dsrf_total_repayment_keur" in fields
    assert "dsrf_commitment_fee_keur" in fields
    assert "dsrf_drawn_interest_keur" in fields
    assert "dsrf_debt_service_support_keur" in fields
    assert "dsrf_drawn_end_keur" in fields
    assert "dsrf_periods" in fields
    # Defaults
    spv = SPVOutput(
        project_code="X", project_name="X", project_irr=0.0, equity_irr=0.0,
        total_revenue_keur=0.0, total_ebitda_keur=0.0, total_tax_keur=0.0,
        total_senior_ds_keur=0.0, total_distribution_keur=0.0, avg_dscr=0.0, min_dscr=0.0,
        waterfall_result=None,
    )
    assert spv.dsrf_facility_limit_keur == 0.0
    assert spv.dsrf_total_draw_keur == 0.0
    assert spv.dsrf_periods == ()


def test_portfolio_result_has_dsrf_fields():
    """IndependentPortfolioResult must have DSRF aggregate fields."""
    fields = IndependentPortfolioResult.__dataclass_fields__
    assert "dsrf_enabled" in fields
    assert "dsrf_facility_limit_keur" in fields
    assert "dsrf_total_draw_keur" in fields
    assert "dsrf_total_repayment_keur" in fields
    assert "dsrf_commitment_fee_keur" in fields
    assert "dsrf_drawn_interest_keur" in fields
    assert "dsrf_debt_service_support_keur" in fields
    assert "dsrf_drawn_end_keur" in fields
    assert "dsrf_periods" in fields
    assert fields["dsrf_enabled"].default is False


def test_portfolio_result_dsrf_fields_default_to_zero():
    """DSRF fields default to 0.0 / () when not set."""
    result = IndependentPortfolioResult(
        portfolio_name="Test",
        spv_outputs=(),
        total_revenue_keur=0.0, total_ebitda_keur=0.0, total_tax_keur=0.0,
        total_senior_ds_keur=0.0, total_distribution_keur=0.0,
        min_dscr=0.0, avg_dscr=0.0,
        spv_project_irrs=(), spv_equity_irrs=(),
    )
    assert result.dsrf_enabled is False
    assert result.dsrf_facility_limit_keur == 0.0
    assert result.dsrf_total_draw_keur == 0.0
    assert result.dsrf_periods == ()


# =============================================================================
# 3. enabled=False zero impact on real portfolio run
# =============================================================================

def _make_mock_project(code: str):
    """Minimal mock project for testing."""
    from unittest.mock import MagicMock
    from datetime import date
    p = MagicMock()
    p.info.code = code
    p.info.name = f"Project {code}"
    p.info.financial_close = date(2030, 1, 1)
    p.info.construction_months = 12
    p.info.horizon_years = 25
    p.revenue.ppa_term_years = 10
    return p


def test_dsrf_disabled_none_vs_config_none():
    """dsrf=None and dsrf=DSRFConfig(enabled=False) must produce identical outputs."""
    projects = tuple(_make_mock_project(code) for code in ("A", "B", "C"))

    # dsrf=None
    result_none = run_independent_portfolio(
        IndependentPortfolioInputs(
            projects=projects,
            portfolio_name="Test",
            dsrf=None,
        ),
        strict=False,
    )

    # dsrf=DSRFConfig(enabled=False)
    result_disabled = run_independent_portfolio(
        IndependentPortfolioInputs(
            projects=projects,
            portfolio_name="Test",
            dsrf=DSRFConfig(enabled=False),
        ),
        strict=False,
    )

    # Compare key totals
    assert result_none.total_revenue_keur == result_disabled.total_revenue_keur
    assert result_none.total_ebitda_keur == result_disabled.total_ebitda_keur
    assert result_none.total_senior_ds_keur == result_disabled.total_senior_ds_keur
    assert result_none.total_distribution_keur == result_disabled.total_distribution_keur
    assert result_none.min_dscr == result_disabled.min_dscr
    assert result_none.avg_dscr == result_disabled.avg_dscr
    assert result_none.simple_avg_project_irr == result_disabled.simple_avg_project_irr
    assert result_none.simple_avg_equity_irr == result_disabled.simple_avg_equity_irr

    # No extra warnings
    assert len(result_disabled.warnings) == len(result_none.warnings)
    assert result_disabled.dsrf_enabled is False


# =============================================================================
# 4. enabled=True accepted — schedule attached only, no financial change yet
# =============================================================================

def test_dsrf_enabled_true_does_not_raise():
    """DSRFConfig(enabled=True) must not raise when run through portfolio."""
    projects = tuple(_make_mock_project(code) for code in ("A", "B"))

    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        sizing_basis="average_debt_service",
        commitment_fee_rate_pa=0.005,
        margin_rate_pa=0.02,
        euribor_rate_pa=0.03,
        period_year_fraction=0.5,
        repayment_priority="before_distributions",
    )

    result = run_independent_portfolio(
        IndependentPortfolioInputs(
            projects=projects,
            portfolio_name="Test",
            dsrf=config,
        ),
        strict=False,
    )

    # DSRF fields exist and are populated
    assert result.dsrf_enabled is True
    # Financial totals should still be present (no distribution change yet)
    assert result.total_distribution_keur >= 0


# =============================================================================
# 5. Terminology: no prohibited terms in DSRF result field names
# =============================================================================

def test_dsrf_result_fields_no_prohibited_terms():
    """Public DSRF result field names must not include: top-up, release, balance, funded."""
    for cls in (SPVOutput, IndependentPortfolioResult):
        field_names = list(cls.__dataclass_fields__.keys())
        dsrf_fields = [n for n in field_names if n.startswith("dsrf")]
        for name in dsrf_fields:
            for term in ("topup", "release", "balance", "funded"):
                assert term not in name.lower(), (
                    f"{cls.__name__}.{name} contains prohibited term '{term}'"
                )


def test_dsrf_result_fields_use_facility_terminology():
    """DSRF fields use draw, repayment, drawn, undrawn, facility limit, commitment fee."""
    for cls in (SPVOutput, IndependentPortfolioResult):
        field_names = list(cls.__dataclass_fields__.keys())
        dsrf_fields = [n for n in field_names if n.startswith("dsrf")]
        # Should have fields like dsrf_total_draw_keur, dsrf_total_repayment_keur, etc.
        assert any("draw" in f for f in dsrf_fields), f"{cls} missing draw fields"
        assert any("repayment" in f for f in dsrf_fields), f"{cls} missing repayment fields"


# =============================================================================
# 6. No scope creep: no HoldCo, SHL, Sponsor IRR, monthly, pooled financing
# =============================================================================

def test_runner_exports_no_holdco():
    """Runner module must not export HoldCo-related names."""
    from domain.portfolio.independent import runner
    public = runner.__all__
    for name in public:
        assert "holdco" not in name.lower(), f"holdco found in runner export: {name}"
        assert "shl" not in name.lower() or name == "SHL", f"shl found in runner export: {name}"


def test_result_model_no_sponsor_irr_in_dsrf_fields():
    """DSRF fields must not include sponsor_irr."""
    fields = list(IndependentPortfolioResult.__dataclass_fields__.keys())
    dsrf_fields = [f for f in fields if f.startswith("dsrf")]
    for f in dsrf_fields:
        assert "sponsor" not in f.lower(), f"DSRF field contains sponsor: {f}"