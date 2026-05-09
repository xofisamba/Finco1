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
    # Use real project factory for a rigorous test with strict=True
    from app.project_factories import create_default_solar_project

    project = create_default_solar_project()

    # dsrf=None
    result_none = run_independent_portfolio(
        IndependentPortfolioInputs(
            projects=(project,),
            portfolio_name="Test",
            dsrf=None,
        ),
        strict=True,
    )

    # dsrf=DSRFConfig(enabled=False)
    result_disabled = run_independent_portfolio(
        IndependentPortfolioInputs(
            projects=(project,),
            portfolio_name="Test",
            dsrf=DSRFConfig(enabled=False),
        ),
        strict=True,
    )

    # Compare all key financial KPIs
    assert result_none.total_revenue_keur == result_disabled.total_revenue_keur
    assert result_none.total_ebitda_keur == result_disabled.total_ebitda_keur
    assert result_none.total_senior_ds_keur == result_disabled.total_senior_ds_keur
    assert result_none.total_distribution_keur == result_disabled.total_distribution_keur
    assert result_none.min_dscr == result_disabled.min_dscr
    assert result_none.avg_dscr == result_disabled.avg_dscr
    assert result_none.simple_avg_project_irr == result_disabled.simple_avg_project_irr
    assert result_none.simple_avg_equity_irr == result_disabled.simple_avg_equity_irr
    assert result_none.warnings == result_disabled.warnings
    assert result_disabled.dsrf_enabled is False

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

def test_dsrf_enabled_true_does_not_raise_and_adjusts_distribution():
    """DSRFConfig(enabled=True) with real project must not raise; schedule attached and distribution adjusted.

    Phase 2 Step 3: Distributions are reduced by DSRF cash costs (commitment fee + interest + repayment).
    Draw itself is NOT revenue and does NOT increase distributions.
    """
    from app.project_factories import create_default_solar_project

    project = create_default_solar_project()
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
            projects=(project,),
            portfolio_name="Test",
            dsrf=config,
        ),
        strict=False,
    )

    assert result.dsrf_enabled is True
    assert len(result.spv_outputs) >= 1
    spv = result.spv_outputs[0]
    assert spv.waterfall_result is not None
    assert spv.dsrf_facility_limit_keur >= 0
    assert isinstance(spv.dsrf_periods, tuple)
    if spv.waterfall_result and spv.waterfall_result.periods:
        op_periods = [p for p in spv.waterfall_result.periods if getattr(p, "is_operation", False)]
        if op_periods:
            assert len(spv.dsrf_periods) > 0

    # Verify distribution reduction is computed
    assert spv.dsrf_distribution_reduction_keur >= 0.0

    # Verify adjusted distribution <= original (DSRF costs cannot increase distributions)
    original_dist = spv.waterfall_result.total_distribution_keur
    adjusted_dist = spv.total_distribution_keur
    assert adjusted_dist <= original_dist + 1e-6, (
        f"DSRF-adjusted dist ({adjusted_dist}) should not exceed original ({original_dist})"
    )

    wf_periods = spv.waterfall_result.periods
    raw_wf_sum = sum(p.distribution_keur for p in wf_periods)
    adjusted_sum = sum(spv.adjusted_period_distributions_keur)
    expected_reduction = raw_wf_sum - adjusted_sum
    assert abs(spv.dsrf_distribution_reduction_keur - expected_reduction) < 1e-6, (
        f"dsrf_distribution_reduction_keur={spv.dsrf_distribution_reduction_keur} "
        f"!= raw_wf_sum - adjusted_sum = {expected_reduction}"
    )

    # Portfolio-level dsrf_distribution_reduction_keur should be >= SPV reduction
    assert result.dsrf_distribution_reduction_keur >= spv.dsrf_distribution_reduction_keur - 1e-6

    # Verify warning summary works (no DSRF warnings if schedule extracted)
    if spv.dsrf_periods:
        assert not any("DSRF" in w for w in result.warnings) or result.warnings == ()


# =============================================================================
# 5. DSRF aggregate facility_limit sums across SPVs (not only first)
# =============================================================================

def test_dsrf_aggregate_facility_limit_sums_across_spvs():
    """Portfolio DSRF facility_limit is sum of all SPV limits, not only first."""
    from domain.portfolio.independent.dsrf import DSRFResult, DSRFConfig

    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        sizing_basis="average_debt_service",
        period_year_fraction=0.5,
    )

    # Build two mock DSRF results with facility limits 1000 and 1500
    from domain.portfolio.independent.dsrf import DSRFPeriod

    p1 = DSRFPeriod(
        period=0, spv_code="A",
        facility_limit_keur=1000.0,
        drawn_start_keur=0.0, undrawn_start_keur=1000.0,
        scheduled_senior_ds_keur=500.0, cfads_available_keur=400.0,
        debt_service_shortfall_keur=100.0, draw_keur=100.0,
        drawn_after_draw_keur=100.0,
        commitment_fee_keur=2.5, drawn_interest_keur=2.5,
        repayment_keur=0.0, drawn_end_keur=100.0, undrawn_end_keur=900.0,
        senior_ds_paid_keur=500.0,
        cash_available_for_distribution_keur=0.0,
    )
    r1 = DSRFResult(
        config=config, periods=(p1,),
        total_draw_keur=100.0, total_repayment_keur=0.0,
        total_commitment_fee_keur=2.5, total_drawn_interest_keur=2.5,
        total_debt_service_support_keur=100.0,
        facility_limit_keur=1000.0, drawn_end_keur=100.0,
    )

    p2 = DSRFPeriod(
        period=0, spv_code="B",
        facility_limit_keur=1500.0,
        drawn_start_keur=0.0, undrawn_start_keur=1500.0,
        scheduled_senior_ds_keur=600.0, cfads_available_keur=500.0,
        debt_service_shortfall_keur=100.0, draw_keur=100.0,
        drawn_after_draw_keur=100.0,
        commitment_fee_keur=3.75, drawn_interest_keur=2.5,
        repayment_keur=0.0, drawn_end_keur=100.0, undrawn_end_keur=1400.0,
        senior_ds_paid_keur=600.0,
        cash_available_for_distribution_keur=0.0,
    )
    r2 = DSRFResult(
        config=config, periods=(p2,),
        total_draw_keur=100.0, total_repayment_keur=0.0,
        total_commitment_fee_keur=3.75, total_drawn_interest_keur=2.5,
        total_debt_service_support_keur=100.0,
        facility_limit_keur=1500.0, drawn_end_keur=100.0,
    )

    from domain.portfolio.independent.runner import _aggregate_dsrf_results
    agg = _aggregate_dsrf_results([r1, r2])

    assert agg is not None
    assert agg.facility_limit_keur == 2500.0  # 1000 + 1500 (sum, not only first)
    assert agg.drawn_end_keur == 200.0  # 100 + 100 (already summed)


# =============================================================================
# 6. Terminology: no prohibited terms in DSRF result field names
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

# =============================================================================
# 7. P0.1: DSRF-adjusted period distributions — real integration
# =============================================================================

def test_dsrf_adjusted_period_distributions_real_project():
    """DSRF-adjusted distributions are aligned to waterfall period count.

    Creates a real solar project with DSRF enabled, verifies:
    - adjusted_period_distributions_keur is non-empty
    - len(adjusted_period_distributions_keur) == len(waterfall_result.periods)
    - total_distribution_keur ~= sum(adjusted_period_distributions_keur)
    - HoldCo gross income uses DSRF-adjusted values (not waterfall raw)
    """
    from app.project_factories import create_default_solar_project
    from dataclasses import replace
    from domain.portfolio.independent import IndependentPortfolioInputs, DSRFConfig
    from domain.portfolio.independent.runner import run_independent_portfolio
    from domain.portfolio.holdco import HoldCoInputs, HoldCoEntity, HoldCoOpexInputs, SPVOwnership
    from domain.portfolio.holdco.runner import build_holdco_result

    project = replace(create_default_solar_project(), info=replace(
        create_default_solar_project().info,
        code="SOLAR-DSRF-TEST", name="Solar DSRF Test"))

    dsrf_config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.005,
        margin_rate_pa=0.02,
        euribor_rate_pa=0.0,
        period_year_fraction=0.5,
    )

    portfolio_inputs = IndependentPortfolioInputs(
        projects=(project,),
        dsrf=dsrf_config,
    )

    result = run_independent_portfolio(portfolio_inputs, strict=True)
    assert result.num_spvs == 1
    spv = result.spv_outputs[0]

    wf_periods = spv.waterfall_result.periods

    # Adjusted distributions must be non-empty and aligned to waterfall periods
    assert spv.adjusted_period_distributions_keur, "adjusted_period_distributions_keur must be non-empty"
    assert len(spv.adjusted_period_distributions_keur) == len(wf_periods), (
        f"len(adjusted)={len(spv.adjusted_period_distributions_keur)} != "
        f"len(wf_periods)={len(wf_periods)}"
    )

    # ── P0.1 final: verify SPVOutput distribution totals are consistent ────
    raw_waterfall_sum = sum(p.distribution_keur for p in wf_periods)
    adjusted_sum = sum(spv.adjusted_period_distributions_keur)

    # SPV total_distribution_keur equals sum(adjusted_period_distributions) when DSRF aligned
    assert spv.total_distribution_keur == pytest.approx(adjusted_sum, rel=1e-2), (
        f"total_distribution_keur={spv.total_distribution_keur} != "
        f"sum(adjusted)={adjusted_sum}"
    )

    # dsrf_distribution_reduction_keur audit trail: wf_sum - adjusted_sum
    expected_reduction = raw_waterfall_sum - adjusted_sum
    assert spv.dsrf_distribution_reduction_keur == pytest.approx(expected_reduction, rel=1e-2), (
        f"dsrf_distribution_reduction={spv.dsrf_distribution_reduction_keur} != "
        f"wf_sum-adj_sum={expected_reduction}"
    )

    # Build HoldCo and verify it uses DSRF-adjusted values
    entity = HoldCoEntity(name="HC", tax_rate_pa=0.0)
    entity.opex = HoldCoOpexInputs(annual_opex_keur=0.0)
    holdco_inputs = HoldCoInputs(
        name="HC",
        ownerships=[SPVOwnership(spv_code="SOLAR-DSRF-TEST", ownership_pct=1.0)],
        entity=entity,
    )

    holdco_result = build_holdco_result(holdco_inputs, result)

    # HoldCo gross income equals SPV adjusted sum + SHL interest (P4B: SHL interest now included)
    holdco_gross_with_shl = adjusted_sum + sum(p.shl_interest_keur for p in wf_periods)
    assert holdco_result.total_gross_income_keur == pytest.approx(holdco_gross_with_shl, rel=1e-2), (
        f"HoldCo gross={holdco_result.total_gross_income_keur} != "
        f"adjusted_sum + shl_interest = {holdco_gross_with_shl}"
    )

    # HoldCo gross income includes SHL interest (P4B: SHL interest is now included)
    # HoldCo gross = dividend (adjusted) + SHL interest. wf_total = raw wf distributions only.
    # We relax this assertion since SHL interest can exceed raw wf distributions.
    # The important invariant is: HoldCo gross = adjusted_sum + shl_interest_sum (tested above)
    assert holdco_result.total_gross_income_keur >= holdco_gross_with_shl - 1.0

    # P4B: HoldCo per-period gross = adjusted (dividend) + SHL interest per period
    # (spv.adjusted_period_distributions_keur is the dividend portion; SHL interest adds on top)
    for i in range(len(holdco_result.periods)):
        expected = spv.adjusted_period_distributions_keur[i] + getattr(wf_periods[i], 'shl_interest_keur', 0.0)
        assert holdco_result.periods[i].gross_income_keur == pytest.approx(expected, rel=1e-2), (
            f"Period {i}: HoldCo gross={holdco_result.periods[i].gross_income_keur} != "
            f"adjusted + shl_int = {expected}"
        )

    # SPV total_distribution_keur < wf sum (DSRF reduces)
    assert spv.total_distribution_keur < raw_waterfall_sum, (
        "DSRF should reduce total distribution vs raw waterfall"
    )
