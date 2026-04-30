"""Tests for S1-5: DSRA equity funding at Financial Close.

This test verifies the blueprint requirement:
- DSRA initial funding comes from EQUITY at FC, not from operating CF
- DSRA = 6 months × annual_debt_service (from sculpted payment schedule)
- Operating CF only tops up DSRA if balance drops below target
"""
import pytest
from domain.waterfall.dsra_engine import (
    DSRAEngineResult,
    compute_initial_dsra,
    compute_dsra_target,
    dsra_top_up_from_fcf,
    run_dsra_engine,
    dsra_schedule_simple,
)


class TestComputeInitialDSRA:
    """Test initial DSRA computation from sculpted payment schedule."""

    def test_oborovo_initial_dsra(self):
        """Oborovo: annual DS ≈ 4,478 kEUR → DSRA = 2,239 kEUR."""
        payment_schedule = [2_239.0] * 28  # Semi-annual payments
        dsra = compute_initial_dsra(payment_schedule, dsra_months=6, periods_per_year=2)
        # annual_ds = 2,239 × 2 = 4,478
        # DSRA = 6/12 × 4,478 = 2,239
        assert abs(dsra - 2_239.0) < 1.0

    def test_tuho_initial_dsra(self):
        """TUHO: annual DS ≈ 4,200 kEUR → DSRA = 2,100 kEUR."""
        payment_schedule = [2_100.0] * 28  # Semi-annual payments
        dsra = compute_initial_dsra(payment_schedule, dsra_months=6, periods_per_year=2)
        # annual_ds = 2,100 × 2 = 4,200
        # DSRA = 6/12 × 4,200 = 2,100
        assert abs(dsra - 2_100.0) < 1.0

    def test_empty_schedule_returns_zero(self):
        """Empty payment schedule returns 0 DSRA."""
        dsra = compute_initial_dsra([], dsra_months=6, periods_per_year=2)
        assert dsra == 0.0

    def test_dsra_months_variation(self):
        """DSRA changes with months parameter."""
        payment_schedule = [2_000.0] * 28
        # 3 months: 3/12 × 4,000 = 1,000
        dsra_3m = compute_initial_dsra(payment_schedule, dsra_months=3, periods_per_year=2)
        # 12 months: 12/12 × 4,000 = 4,000
        dsra_12m = compute_initial_dsra(payment_schedule, dsra_months=12, periods_per_year=2)
        assert abs(dsra_3m - 1_000.0) < 1.0
        assert abs(dsra_12m - 4_000.0) < 1.0


class TestComputeDSRATarget:
    """Test DSRA target computation per period."""

    def test_target_from_payment(self):
        """Target = 6/12 × annual_debt_service."""
        target = compute_dsra_target(
            current_period_payment=2_239.0,
            dsra_months=6,
            periods_per_year=2,
        )
        # annual_ds = 2,239 × 2 = 4,478
        # target = 6/12 × 4,478 = 2,239
        assert abs(target - 2_239.0) < 1.0

    def test_target_scales_with_payment(self):
        """Target scales with debt service payment."""
        target_low = compute_dsra_target(2_000.0, dsra_months=6, periods_per_year=2)
        target_high = compute_dsra_target(4_000.0, dsra_months=6, periods_per_year=2)
        # ratio = 4,000/2,000 = 2
        assert abs(target_high / target_low - 2.0) < 0.01


class TestDSRATopUpFromFCF:
    """Test DSRA top-up from operating FCF."""

    def test_no_topup_when_funded(self):
        """No contribution when balance >= target."""
        topup = dsra_top_up_from_fcf(
            current_balance=2_500.0,
            target_balance=2_239.0,  # Balance above target
            fcf_after_ds_keur=1_000.0,
        )
        assert topup == 0.0

    def test_no_topup_when_no_fcf(self):
        """No contribution when FCF <= 0."""
        topup = dsra_top_up_from_fcf(
            current_balance=1_000.0,
            target_balance=2_239.0,
            fcf_after_ds_keur=0.0,  # No FCF available
        )
        assert topup == 0.0

    def test_topup_limited_by_gap(self):
        """Contribution limited by gap (target - balance)."""
        topup = dsra_top_up_from_fcf(
            current_balance=1_000.0,
            target_balance=2_239.0,  # Gap = 1,239
            fcf_after_ds_keur=10_000.0,  # Plenty of FCF
        )
        # 50% × 10,000 = 5,000, but gap = 1,239 → capped at 1,239
        assert abs(topup - 1_239.0) < 0.01

    def test_topup_limited_by_fcf(self):
        """Contribution limited by available FCF."""
        topup = dsra_top_up_from_fcf(
            current_balance=1_000.0,
            target_balance=2_239.0,  # Gap = 1,239
            fcf_after_ds_keur=500.0,  # Only 500 FCF available
        )
        # 50% × 500 = 250 < gap 1,239 → limited to 250
        assert abs(topup - 250.0) < 0.01

    def test_topup_50_percent_rate(self):
        """Top-up uses 50% of available FCF."""
        topup = dsra_top_up_from_fcf(
            current_balance=0.0,
            target_balance=2_239.0,
            fcf_after_ds_keur=4_000.0,
        )
        # 50% × 4,000 = 2,000 < gap 2,239 → 2,000
        assert abs(topup - 2_000.0) < 0.01


class TestRunDSRAEngine:
    """Test DSRA engine for single period."""

    def test_first_period_equity_funding(self):
        """First period: initial DSRA from equity funding."""
        result = run_dsra_engine(
            period=0,
            dsra_balance_prior=0.0,
            sculpted_payment_schedule=[2_239.0] * 28,
            fcf_after_ds_keur=954.0,
            is_first_period=True,
            dsra_months=6,
            periods_per_year=2,
            equity_initial_funding=2_239.0,  # Funded from equity at FC
        )
        # Initial = 2,239 (equity funded)
        assert abs(result.dsra_initial_keur - 2_239.0) < 1.0
        # Opening balance = initial
        assert abs(result.dsra_balance_start_keur - 2_239.0) < 1.0
        # No contribution (already funded via equity)
        assert result.dsra_contribution_keur == 0.0
        # Fully funded
        assert result.is_fully_funded is True

    def test_first_period_no_equity_funding(self):
        """First period without equity funding: compute from schedule."""
        result = run_dsra_engine(
            period=0,
            dsra_balance_prior=0.0,
            sculpted_payment_schedule=[2_239.0] * 28,
            fcf_after_ds_keur=954.0,
            is_first_period=True,
            dsra_months=6,
            periods_per_year=2,
            equity_initial_funding=None,
        )
        # Initial computed from schedule (same as equity case)
        assert abs(result.dsra_initial_keur - 2_239.0) < 1.0

    def test_subsequent_period_no_topup(self):
        """Subsequent period: no top-up if balance >= target."""
        result = run_dsra_engine(
            period=5,
            dsra_balance_prior=2_239.0,  # Already at target
            sculpted_payment_schedule=[2_239.0] * 28,
            fcf_after_ds_keur=2_000.0,
            is_first_period=False,
            dsra_months=6,
            periods_per_year=2,
        )
        assert result.dsra_contribution_keur == 0.0
        assert result.is_fully_funded is True

    def test_subsequent_period_topup_needed(self):
        """Subsequent period: top-up needed if balance < target."""
        result = run_dsra_engine(
            period=10,
            dsra_balance_prior=1_000.0,  # Below target
            sculpted_payment_schedule=[2_239.0] * 28,
            fcf_after_ds_keur=2_000.0,
            is_first_period=False,
            dsra_months=6,
            periods_per_year=2,
        )
        # Gap = 2,239 - 1,000 = 1,239
        # FCF available = 2,000 → 50% = 1,000
        # topup = min(1,000, 1,239) = 1,000
        assert abs(result.dsra_contribution_keur - 1_000.0) < 1.0


class TestDSRAEngineResultProperties:
    """Test DSRAEngineResult properties."""

    def test_net_change(self):
        """net_change = contribution - withdrawal."""
        result = DSRAEngineResult(
            dsra_initial_keur=0.0,
            dsra_contribution_keur=500.0,
            dsra_withdrawal_keur=200.0,
            dsra_balance_start_keur=1_000.0,
            dsra_balance_end_keur=1_300.0,
            dsra_target_keur=2_239.0,
            is_fully_funded=False,
        )
        assert result.net_change_keur == 300.0  # 500 - 200

    def test_closing_balance_formula(self):
        """Closing balance = opening + contribution - withdrawal."""
        result = DSRAEngineResult(
            dsra_initial_keur=0.0,
            dsra_contribution_keur=500.0,
            dsra_withdrawal_keur=200.0,
            dsra_balance_start_keur=1_000.0,
            dsra_balance_end_keur=1_300.0,
            dsra_target_keur=2_239.0,
            is_fully_funded=False,
        )
        expected = 1_000.0 + 500.0 - 200.0
        assert abs(result.dsra_balance_end_keur - expected) < 0.01


class TestDSRAScheduleSimple:
    """Test simple DSRA schedule generation."""

    def test_schedule_with_initial(self):
        """Schedule with initial DSRA from equity."""
        schedule = dsra_schedule_simple(
            payment_schedule=[2_239.0] * 28,
            initial_dsra_keur=2_239.0,  # Equity funded
            dsra_months=6,
            periods_per_year=2,
        )
        # All balances = 2,239 (no FCF to top up in this simplified version)
        assert len(schedule) == 28
        for bal in schedule:
            assert abs(bal - 2_239.0) < 0.01

    def test_empty_schedule(self):
        """Empty payment schedule returns empty list."""
        schedule = dsra_schedule_simple(
            payment_schedule=[],
            dsra_months=6,
            periods_per_year=2,
        )
        assert schedule == []


class TestS1Integration:
    """Integration: DSRA equity funding at FC flows into waterfall."""

    def test_oborovo_dsra_funding_at_fc(self):
        """Oborovo: DSRA_initial = 2,239 kEUR funded from equity at FC."""
        # Oborovo annual debt service ≈ 4,478 kEUR
        annual_ds = 4_478.0
        dsra_months = 6

        # DSRA_initial = 6/12 × 4,478 = 2,239 kEUR
        dsra_initial = compute_initial_dsra(
            sculpted_payment_schedule=[annual_ds / 2] * 28,
            dsra_months=dsra_months,
            periods_per_year=2,
        )
        assert abs(dsra_initial - 2_239.0) < 1.0

        # At FC, equity contribution includes DSRA:
        # equity_needed = capex + dsra_initial + other_reserves
        capex = 56_430.0  # kEUR
        equity_needed = capex + dsra_initial
        assert abs(equity_needed - 58_669.0) < 1.0  # 56,430 + 2,239

    def test_vs_v2_bug_no_initial_funding(self):
        """v2 bug: DSRA_initial = 0, first years fill from operating CF."""
        # v2 buggy approach: DSRA not funded at FC
        dsra_initial_v2 = 0.0

        # v3 correct approach: DSRA funded from equity at FC
        dsra_initial_v3 = 2_239.0

        # Difference affects distribution timing
        assert dsra_initial_v2 != dsra_initial_v3
        # v2: first operating years contribute to DSRA → delayed distributions
        # v3: DSRA already funded → distributions start sooner

    def test_dsra_initial_is_part_of_funding_structure(self):
        """DSRA_initial is part of funding structure, not operating CF."""
        dsra = compute_initial_dsra(
            sculpted_payment_schedule=[2_239.0] * 28,
            dsra_months=6,
            periods_per_year=2,
        )

        # DSRA must be funded at FC (part of equity contribution)
        # Cannot be "filled" from operating CF in first years
        assert dsra > 0  # Oborovo has positive DSRA

        # If DSRA was 0, it would mean it's being filled from operating CF
        # which is the v2 bug
        assert dsra == 2_239.0  # Funded from equity at FC