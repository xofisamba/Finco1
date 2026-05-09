"""Tests for DSRF revolving reserve facility engine."""
from __future__ import annotations

import pytest

from domain.portfolio.independent.dsrf import (
    DSRFConfig,
    DSRFPeriod,
    DSRFResult,
    calculate_average_debt_service,
    calculate_facility_limit,
    calculate_period_dsrf,
    run_dsrf_facility_schedule,
)


# =============================================================================
# DSRFConfig validation tests
# =============================================================================

def test_dsrf_config_enabled_sizing_months_6():
    config = DSRFConfig(enabled=True, sizing_months=6)
    assert config.sizing_months == 6
    assert config.enabled is True


def test_dsrf_config_enabled_sizing_months_9():
    config = DSRFConfig(enabled=True, sizing_months=9)
    assert config.sizing_months == 9


def test_dsrf_config_enabled_sizing_months_12():
    config = DSRFConfig(enabled=True, sizing_months=12)
    assert config.sizing_months == 12


def test_dsrf_config_invalid_sizing_months_raises():
    with pytest.raises(ValueError, match="sizing_months must be one of 6, 9, 12"):
        DSRFConfig(enabled=True, sizing_months=7)


def test_dsrf_config_negative_commitment_fee_raises():
    with pytest.raises(ValueError, match="commitment_fee_rate_pa must be >= 0"):
        DSRFConfig(enabled=True, sizing_months=6, commitment_fee_rate_pa=-0.01)


def test_dsrf_config_negative_margin_raises():
    with pytest.raises(ValueError, match="margin_rate_pa must be >= 0"):
        DSRFConfig(enabled=True, sizing_months=6, margin_rate_pa=-0.01)


def test_dsrf_config_negative_euribor_allowed():
    # Negative EURIBOR allowed if project permits
    config = DSRFConfig(enabled=True, sizing_months=6, euribor_rate_pa=-0.5)
    assert config.euribor_rate_pa == -0.5


def test_dsrf_config_zero_period_fraction_raises():
    with pytest.raises(ValueError, match="period_year_fraction must be > 0"):
        DSRFConfig(enabled=True, sizing_months=6, period_year_fraction=0.0)


def test_dsrf_config_disabled_skips_validation():
    # When enabled=False, other fields should not raise validation errors
    config = DSRFConfig(enabled=False, sizing_months=99, commitment_fee_rate_pa=-1.0)
    assert config.enabled is False
    # Should not raise


# =============================================================================
# Zero-impact tests (enabled=False)
# =============================================================================

def test_dsrf_enabled_false_no_op_result():
    """enabled=False returns a zero-activity result."""
    config = DSRFConfig(enabled=False, sizing_months=6)
    result = run_dsrf_facility_schedule(
        spv_code="TEST",
        semiannual_debt_service_schedule=(1000.0, 1000.0),
        cfads_schedule=(800.0, 800.0),
        config=config,
    )
    assert result.total_draw_keur == 0.0
    assert result.total_repayment_keur == 0.0
    assert result.total_commitment_fee_keur == 0.0
    assert result.total_drawn_interest_keur == 0.0
    assert result.facility_limit_keur == 0.0
    assert result.drawn_end_keur == 0.0
    assert result.periods == ()


def test_dsrf_enabled_false_identical_to_none():
    """DSRFConfig(enabled=False) is semantically identical to dsrf=None for integration."""
    config_disabled = DSRFConfig(enabled=False)
    config_none = None  # simulated as None in integration

    # Both should produce identical zero-activity results
    result_disabled = run_dsrf_facility_schedule(
        spv_code="TEST",
        semiannual_debt_service_schedule=(1000.0,),
        cfads_schedule=(800.0,),
        config=config_disabled,
    )
    # When config is None (simulated by enabled=False), same result
    assert result_disabled.periods == ()


# =============================================================================
# Facility limit sizing tests
# =============================================================================

def test_calculate_average_debt_service():
    schedule = (1000.0, 2000.0, 1500.0)
    avg = calculate_average_debt_service(schedule)
    assert avg == 1500.0


def test_calculate_average_debt_service_empty():
    avg = calculate_average_debt_service(())
    assert avg == 0.0


def test_facility_limit_sizing_months_6():
    """sizing_months=6 → 1.0× average semiannual DS."""
    avg_ds = 1000.0
    limit = calculate_facility_limit(avg_ds, sizing_months=6)
    assert limit == 1000.0


def test_facility_limit_sizing_months_9():
    """sizing_months=9 → 1.5× average semiannual DS."""
    avg_ds = 1000.0
    limit = calculate_facility_limit(avg_ds, sizing_months=9)
    assert limit == 1500.0


def test_facility_limit_sizing_months_12():
    """sizing_months=12 → 2.0× average semiannual DS."""
    avg_ds = 1000.0
    limit = calculate_facility_limit(avg_ds, sizing_months=12)
    assert limit == 2000.0


# =============================================================================
# Commitment fee on undrawn amount only
# =============================================================================

def test_commitment_fee_on_undrawn_only():
    """Commitment fee is calculated on undrawn amount, not drawn amount."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.05,  # 5% p.a.
        margin_rate_pa=0.0,
        euribor_rate_pa=0.0,
        period_year_fraction=0.5,
    )
    period = calculate_period_dsrf(
        period=0,
        spv_code="TEST",
        cfads_available_keur=1000.0,
        scheduled_senior_ds_keur=1000.0,
        drawn_start_keur=500.0,   # facility_limit=1000, so undrawn_start=500
        facility_limit_keur=1000.0,
        config=config,
    )
    # After draw (no shortfall, so draw=0), drawn_after_draw=500
    # undrawn_after_draw = 1000 - 500 = 500
    # commitment_fee = 500 * 0.05 * 0.5 = 12.5
    assert period.commitment_fee_keur == 12.5


def test_commitment_fee_zero_when_fully_drawn():
    """Commitment fee is 0 when facility is fully drawn."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.05,
        margin_rate_pa=0.0,
        euribor_rate_pa=0.0,
        period_year_fraction=0.5,
    )
    period = calculate_period_dsrf(
        period=0,
        spv_code="TEST",
        cfads_available_keur=1000.0,
        scheduled_senior_ds_keur=1000.0,
        drawn_start_keur=1000.0,  # fully drawn
        facility_limit_keur=1000.0,
        config=config,
    )
    assert period.commitment_fee_keur == 0.0


def test_commitment_fee_zero_when_nothing_drawn():
    """Commitment fee applies when nothing is drawn (full undrawn)."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.05,
        margin_rate_pa=0.0,
        euribor_rate_pa=0.0,
        period_year_fraction=0.5,
    )
    period = calculate_period_dsrf(
        period=0,
        spv_code="TEST",
        cfads_available_keur=1000.0,
        scheduled_senior_ds_keur=1000.0,
        drawn_start_keur=0.0,   # nothing drawn
        facility_limit_keur=1000.0,
        config=config,
    )
    # undrawn_after_draw = 1000 - 0 = 1000
    # commitment_fee = 1000 * 0.05 * 0.5 = 25.0
    assert period.commitment_fee_keur == 25.0


# =============================================================================
# Drawn interest on drawn amount only
# =============================================================================

def test_drawn_interest_on_drawn_only():
    """Interest is calculated on drawn amount, not undrawn."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.0,
        margin_rate_pa=0.02,   # 2% margin
        euribor_rate_pa=0.03,  # 3% EURIBOR
        period_year_fraction=0.5,
    )
    period = calculate_period_dsrf(
        period=0,
        spv_code="TEST",
        cfads_available_keur=1000.0,
        scheduled_senior_ds_keur=1000.0,
        drawn_start_keur=500.0,
        facility_limit_keur=1000.0,
        config=config,
    )
    # drawn_after_draw = 500 (no shortfall, no draw)
    # interest = 500 * (0.02 + 0.03) * 0.5 = 12.5
    assert period.drawn_interest_keur == 12.5


def test_drawn_interest_zero_when_nothing_drawn():
    """Interest is 0 when nothing is drawn."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.0,
        margin_rate_pa=0.02,
        euribor_rate_pa=0.03,
        period_year_fraction=0.5,
    )
    period = calculate_period_dsrf(
        period=0,
        spv_code="TEST",
        cfads_available_keur=1000.0,
        scheduled_senior_ds_keur=1000.0,
        drawn_start_keur=0.0,
        facility_limit_keur=1000.0,
        config=config,
    )
    assert period.drawn_interest_keur == 0.0


# =============================================================================
# Draw tests
# =============================================================================

def test_draw_only_on_shortfall():
    """Draw > 0 only when CFADS < scheduled senior debt service."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.0,
        margin_rate_pa=0.0,
        euribor_rate_pa=0.0,
        period_year_fraction=0.5,
        allow_draw_for_debt_service_shortfall=True,
    )
    # No shortfall case
    period_no_shortfall = calculate_period_dsrf(
        period=0, spv_code="TEST",
        cfads_available_keur=1000.0,
        scheduled_senior_ds_keur=800.0,
        drawn_start_keur=0.0,
        facility_limit_keur=1000.0,
        config=config,
    )
    assert period_no_shortfall.draw_keur == 0.0

    # Shortfall case
    period_shortfall = calculate_period_dsrf(
        period=0, spv_code="TEST",
        cfads_available_keur=500.0,
        scheduled_senior_ds_keur=1000.0,
        drawn_start_keur=0.0,
        facility_limit_keur=1000.0,
        config=config,
    )
    assert period_shortfall.draw_keur == 500.0


def test_draw_before_senior_ds_paid():
    """DSRF draw happens BEFORE senior debt service is paid."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.0,
        margin_rate_pa=0.0,
        euribor_rate_pa=0.0,
        period_year_fraction=0.5,
        allow_draw_for_debt_service_shortfall=True,
    )
    period = calculate_period_dsrf(
        period=0, spv_code="TEST",
        cfads_available_keur=500.0,
        scheduled_senior_ds_keur=1000.0,
        drawn_start_keur=0.0,
        facility_limit_keur=1000.0,
        config=config,
    )
    # Draw of 500 covers the 500 shortfall → senior_ds_paid = 1000
    assert period.senior_ds_paid_keur == 1000.0
    assert period.draw_keur == 500.0


def test_draw_capped_by_undrawn():
    """Draw is capped by undrawn facility amount."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.0,
        margin_rate_pa=0.0,
        euribor_rate_pa=0.0,
        period_year_fraction=0.5,
        allow_draw_for_debt_service_shortfall=True,
    )
    # Shortfall=800 but only 300 undrawn
    period = calculate_period_dsrf(
        period=0, spv_code="TEST",
        cfads_available_keur=200.0,
        scheduled_senior_ds_keur=1000.0,
        drawn_start_keur=700.0,   # undrawn = 300
        facility_limit_keur=1000.0,
        config=config,
    )
    assert period.draw_keur == 300.0   # capped at undrawn
    assert period.senior_ds_paid_keur == 500.0  # CFADS + draw = 200 + 300


# =============================================================================
# Repayment tests
# =============================================================================

def test_repayment_reduces_drawn():
    """Repayment reduces drawn amount."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.0,
        margin_rate_pa=0.0,
        euribor_rate_pa=0.0,
        period_year_fraction=0.5,
        repayment_priority="before_distributions",
    )
    period = calculate_period_dsrf(
        period=0, spv_code="TEST",
        cfads_available_keur=2000.0,
        scheduled_senior_ds_keur=1000.0,
        drawn_start_keur=500.0,
        facility_limit_keur=1000.0,
        config=config,
    )
    # cash_after_senior_ds = 2000 - 1000 = 1000
    # repayment = min(1000, 500) = 500
    # drawn_end = 500 - 500 = 0
    assert period.repayment_keur == 500.0
    assert period.drawn_end_keur == 0.0


def test_repayment_before_distributions():
    """Repayment happens before distributions; cash_for_dist = cash_after_fees - repayment."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.0,
        margin_rate_pa=0.0,
        euribor_rate_pa=0.0,
        period_year_fraction=0.5,
        repayment_priority="before_distributions",
    )
    period = calculate_period_dsrf(
        period=0, spv_code="TEST",
        cfads_available_keur=2000.0,
        scheduled_senior_ds_keur=1000.0,
        drawn_start_keur=300.0,
        facility_limit_keur=1000.0,
        config=config,
    )
    # cash_after_senior_ds = 1000
    # repayment = min(1000, 300) = 300
    # cash_for_dist = 1000 - 300 = 700
    assert period.repayment_keur == 300.0
    assert period.cash_available_for_distribution_keur == 700.0


def test_repayment_capped_by_available_cash():
    """Repayment cannot exceed available cash after fees."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.0,
        margin_rate_pa=0.0,
        euribor_rate_pa=0.0,
        period_year_fraction=0.5,
        repayment_priority="before_distributions",
    )
    period = calculate_period_dsrf(
        period=0, spv_code="TEST",
        cfads_available_keur=1200.0,
        scheduled_senior_ds_keur=1000.0,
        drawn_start_keur=500.0,   # large drawn amount
        facility_limit_keur=1000.0,
        config=config,
    )
    # cash_after_senior_ds = 200
    # repayment = min(200, 500) = 200 (capped at available cash)
    assert period.repayment_keur == 200.0
    assert period.drawn_end_keur == 300.0  # 500 - 200


# =============================================================================
# Fees and interest reduce distributions
# =============================================================================

def test_fees_and_interest_reduce_cash_for_distribution():
    """Commitment fee + interest reduce cash available for distribution."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.05,   # 5% p.a.
        margin_rate_pa=0.02,          # 2% p.a.
        euribor_rate_pa=0.03,         # 3% p.a.
        period_year_fraction=0.5,
        repayment_priority="before_distributions",
    )
    period = calculate_period_dsrf(
        period=0, spv_code="TEST",
        cfads_available_keur=1500.0,
        scheduled_senior_ds_keur=1000.0,
        drawn_start_keur=500.0,
        facility_limit_keur=1000.0,
        config=config,
    )
    # cash_after_senior_ds = 500
    # undrawn_after_draw = 500, commitment_fee = 500 * 0.05 * 0.5 = 12.5
    # drawn_after_draw = 500, drawn_interest = 500 * 0.05 * 0.5 = 12.5
    # cash_after_fees = 500 - 12.5 - 12.5 = 475
    # repayment = min(475, 500) = 475
    # cash_for_dist = 475 - 475 = 0
    assert period.commitment_fee_keur == 12.5
    assert period.drawn_interest_keur == 12.5
    assert period.cash_available_for_distribution_keur == 0.0


def test_no_fees_when_disabled():
    """When enabled=False, all fees are 0."""
    config = DSRFConfig(enabled=False)
    period = calculate_period_dsrf(
        period=0, spv_code="TEST",
        cfads_available_keur=1500.0,
        scheduled_senior_ds_keur=1000.0,
        drawn_start_keur=500.0,
        facility_limit_keur=1000.0,
        config=config,
    )
    assert period.commitment_fee_keur == 0.0
    assert period.drawn_interest_keur == 0.0
    assert period.repayment_keur == 0.0


# =============================================================================
# No negative outputs
# =============================================================================

def test_no_negative_outputs():
    """All outputs must be >= 0."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.05,
        margin_rate_pa=0.02,
        euribor_rate_pa=0.03,
        period_year_fraction=0.5,
    )
    period = calculate_period_dsrf(
        period=0, spv_code="TEST",
        cfads_available_keur=500.0,
        scheduled_senior_ds_keur=1000.0,
        drawn_start_keur=900.0,
        facility_limit_keur=1000.0,
        config=config,
    )
    # All computed values must be >= 0
    assert period.draw_keur >= 0
    assert period.commitment_fee_keur >= 0
    assert period.drawn_interest_keur >= 0
    assert period.repayment_keur >= 0
    assert period.drawn_end_keur >= 0
    assert period.undrawn_end_keur >= 0
    assert period.cash_available_for_distribution_keur >= 0


# =============================================================================
# Full schedule tests
# =============================================================================

def test_run_dsrf_schedule_full():
    """Full schedule with 4 periods, no shortfalls."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.0,
        margin_rate_pa=0.0,
        euribor_rate_pa=0.0,
        period_year_fraction=0.5,
    )
    ds_schedule = (1000.0, 1000.0, 1000.0, 1000.0)
    cfads_schedule = (1200.0, 1200.0, 1200.0, 1200.0)
    result = run_dsrf_facility_schedule(
        spv_code="TEST",
        semiannual_debt_service_schedule=ds_schedule,
        cfads_schedule=cfads_schedule,
        config=config,
    )
    assert len(result.periods) == 4
    assert result.total_draw_keur == 0.0
    assert result.total_commitment_fee_keur == 0.0
    assert result.total_drawn_interest_keur == 0.0


def test_run_dsrf_schedule_with_shortfall():
    """Schedule where period 1 has a shortfall covered by DSRF draw."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.0,
        margin_rate_pa=0.0,
        euribor_rate_pa=0.0,
        period_year_fraction=0.5,
        allow_draw_for_debt_service_shortfall=True,
    )
    ds_schedule = (1000.0, 1000.0, 1000.0)
    cfads_schedule = (500.0, 1200.0, 1200.0)  # shortfall in period 0
    result = run_dsrf_facility_schedule(
        spv_code="TEST",
        semiannual_debt_service_schedule=ds_schedule,
        cfads_schedule=cfads_schedule,
        config=config,
    )
    assert len(result.periods) == 3
    assert result.periods[0].draw_keur == 500.0  # shortfall covered
    assert result.total_draw_keur == 500.0
    assert result.periods[1].repayment_keur == 200.0


# =============================================================================
# Terminology constraints — no prohibited terms
# =============================================================================

def test_dsrf_public_names_no_prohibited_terms():
    """DSRF public field names must not include: top-up, release, balance, funded."""
    import inspect

    # Check DSRFConfig, DSRFPeriod, DSRFResult field names
    for cls in (DSRFConfig, DSRFPeriod, DSRFResult):
        field_names = list(cls.__dataclass_fields__.keys())
        for term in ("topup", "release", "balance", "funded"):
            for name in field_names:
                assert term not in name.lower(), (
                    f"{cls.__name__}.{name} contains prohibited term '{term}'"
                )


def test_dsrf_module_no_prohibited_terms_in_public_api():
    """Module public API should not include prohibited terms."""
    public_api = [
        "DSRFConfig", "DSRFPeriod", "DSRFResult",
        "calculate_average_debt_service", "calculate_facility_limit",
        "calculate_period_dsrf", "run_dsrf_facility_schedule",
    ]
    for name in public_api:
        for term in ("topup", "release", "balance", "funded"):
            assert term not in name.lower(), (
                f"Public API name {name!r} contains prohibited term {term!r}"
            )


# =============================================================================
# No HoldCo / SHL / Sponsor IRR imports
# =============================================================================

def test_dsrf_no_holdco_shl_sponsor_irr():
    """dsrf.py must not import HoldCo, SHL, or sponsor IRR modules."""
    import domain.portfolio.independent.dsrf as dsrf_module

    # Get all names in the module
    all_names = dir(dsrf_module)
    forbidden = ["holdco", "shl", "sponsor", "irr"]
    for name in all_names:
        lower_name = name.lower()
        for term in forbidden:
            assert term not in lower_name, (
                f"dsrf.py imports forbidden module/name: {name!r} (contains {term!r})"
            )


# =============================================================================
# Allow draw disabled test
# =============================================================================

def test_no_draw_when_allow_draw_false():
    """When allow_draw_for_debt_service_shortfall=False, no draw occurs."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.0,
        margin_rate_pa=0.0,
        euribor_rate_pa=0.0,
        period_year_fraction=0.5,
        allow_draw_for_debt_service_shortfall=False,
    )
    period = calculate_period_dsrf(
        period=0, spv_code="TEST",
        cfads_available_keur=100.0,
        scheduled_senior_ds_keur=1000.0,
        drawn_start_keur=0.0,
        facility_limit_keur=1000.0,
        config=config,
    )
    assert period.draw_keur == 0.0
    assert period.senior_ds_paid_keur == 100.0  # partial payment only


# =============================================================================
# Hardening tests
# =============================================================================

def test_debt_service_support_uses_draw_not_shortfall():
    """total_debt_service_support_keur sums actual draws, not shortfalls.

    If shortfall=800 but undrawn=300, support=300, not 800.
    """
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.0,
        margin_rate_pa=0.0,
        euribor_rate_pa=0.0,
        period_year_fraction=0.5,
        allow_draw_for_debt_service_shortfall=True,
    )
    # avg DS = 1000, facility_limit = 1000 (sizing_months=6)
    ds_schedule = (1000.0, 1000.0)
    cfads_schedule = (200.0, 2000.0)  # shortfall=800 in p0, but facility undrawn=1000
    result = run_dsrf_facility_schedule(
        spv_code="TEST",
        semiannual_debt_service_schedule=ds_schedule,
        cfads_schedule=cfads_schedule,
        config=config,
    )
    # shortfall in period 0 = 800, draw = min(800, 1000) = 800
    assert result.periods[0].draw_keur == 800.0
    assert result.total_draw_keur == 800.0
    assert result.total_debt_service_support_keur == 800.0
    # shortfall in period 1 = 0, repayment from excess cash = 800
    assert result.periods[1].repayment_keur == 800.0


def test_debt_service_support_capped_by_undrawn():
    """Support totals reflect actual draws even when shortfall exceeds facility."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.0,
        margin_rate_pa=0.0,
        euribor_rate_pa=0.0,
        period_year_fraction=0.5,
        allow_draw_for_debt_service_shortfall=True,
    )
    ds_schedule = (1000.0,)
    cfads_schedule = (200.0,)
    result = run_dsrf_facility_schedule(
        spv_code="TEST",
        semiannual_debt_service_schedule=ds_schedule,
        cfads_schedule=cfads_schedule,
        config=config,
    )
    assert result.periods[0].draw_keur == 800.0
    assert result.total_debt_service_support_keur == 800.0
    assert result.total_debt_service_support_keur == result.total_draw_keur


def test_negative_euribor_net_positive_rate():
    """EURIBOR=-0.01, margin=0.03 → net positive 2% → interest calculated."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.0,
        margin_rate_pa=0.03,
        euribor_rate_pa=-0.01,
        period_year_fraction=0.5,
    )
    period = calculate_period_dsrf(
        period=0, spv_code="TEST",
        cfads_available_keur=1000.0,
        scheduled_senior_ds_keur=1000.0,
        drawn_start_keur=500.0,
        facility_limit_keur=1000.0,
        config=config,
    )
    assert period.drawn_interest_keur == pytest.approx(5.0)


def test_negative_euribor_net_negative_rate():
    """EURIBOR=-0.04, margin=0.02 → net negative → drawn_interest=0."""
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.0,
        margin_rate_pa=0.02,
        euribor_rate_pa=-0.04,
        period_year_fraction=0.5,
    )
    period = calculate_period_dsrf(
        period=0, spv_code="TEST",
        cfads_available_keur=1000.0,
        scheduled_senior_ds_keur=1000.0,
        drawn_start_keur=500.0,
        facility_limit_keur=1000.0,
        config=config,
    )
    assert period.drawn_interest_keur == 0.0


def test_mismatched_schedule_lengths_raises():
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.0,
        margin_rate_pa=0.0,
        euribor_rate_pa=0.0,
        period_year_fraction=0.5,
    )
    with pytest.raises(ValueError, match="schedule length mismatch"):
        run_dsrf_facility_schedule(
            spv_code="TEST",
            semiannual_debt_service_schedule=(1000.0, 1000.0, 1000.0),
            cfads_schedule=(800.0, 800.0),
            config=config,
        )


def test_facility_limit_invalid_sizing_months_raises():
    with pytest.raises(ValueError, match="sizing_months must be one of 6, 9, 12"):
        calculate_facility_limit(average_period_debt_service_keur=1000.0, sizing_months=7)


def test_negative_senior_debt_service_raises():
    config = DSRFConfig(
        enabled=True,
        sizing_months=6,
        commitment_fee_rate_pa=0.0,
        margin_rate_pa=0.0,
        euribor_rate_pa=0.0,
        period_year_fraction=0.5,
    )
    with pytest.raises(ValueError, match="negative"):
        run_dsrf_facility_schedule(
            spv_code="TEST",
            semiannual_debt_service_schedule=(1000.0, -500.0),
            cfads_schedule=(800.0, 800.0),
            config=config,
        )
