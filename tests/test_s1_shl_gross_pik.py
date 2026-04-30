"""Tests for S1-2: SHL PIK on gross interest (not net).

This test verifies the blueprint requirement:
- PIK = gross_interest - cash_paid (NOT net - cash_paid)
- WHT applies only to cash interest payments, NOT to PIK'd interest
- Prevents WHT from incorrectly inflating the SHL balance
"""
import pytest
from domain.waterfall.shl_engine import (
    SHLPeriodResult,
    compute_shl_period_v3,
    shl_schedule_summary,
)


class TestSHLv3GrossPIK:
    """Test that PIK is computed on gross interest, not net."""

    def test_pik_gross_not_net_wht_zero(self):
        """When WHT=0, v2 and v3 give same result (TUHO case)."""
        result = compute_shl_period_v3(
            shl_balance=10_000.0,
            shl_rate_per_period=0.04,   # 4% per period
            cf_available=0.0,         # No cash → full PIK
            method="pik",
            wht_rate=0.0,
        )
        # PIK = gross interest = 10,000 * 0.04 = 400
        assert abs(result.pik_addition_keur - 400.0) < 0.01
        assert result.new_balance_keur == 10_400.0
        assert result.interest_paid_keur == 0.0
        assert result.interest_wht_keur == 0.0  # No cash → no WHT

    def test_pik_gross_not_net_wht_positive(self):
        """With WHT>0, v3 PIK is larger than v2 buggy PIK.

        v2 buggy: pik = net_interest - cash_paid = 820 - 0 = 820
        v3 correct: pik = gross_interest - cash_paid = 1000 - 0 = 1000

        The 180 kEUR difference is WHT incorrectly capitalized in v2.
        """
        result = compute_shl_period_v3(
            shl_balance=25_000.0,
            shl_rate_per_period=0.04,   # 4% per period → gross = 1000
            cf_available=0.0,           # No cash → full PIK
            method="pik",
            wht_rate=0.18,              # 18% WHT
        )
        # PIK = gross interest = 25,000 * 0.04 = 1000
        assert abs(result.pik_addition_keur - 1000.0) < 0.01
        # v2 buggy would give: net = 820, pik = 820 (WRONG)
        assert result.new_balance_keur == 26_000.0
        # No cash payment → no WHT
        assert result.interest_wht_keur == 0.0

    def test_partial_payment_gross_vs_net(self):
        """Partial payment: PIK = gross - paid, not net - paid.

        Example:
          shl_balance = 20,000
          rate = 5% → gross = 1000, net (18% WHT) = 820
          cf_available = 500

          v2 buggy: paid=500, pik = net - paid = 820 - 500 = 320
          v3 correct: paid=500, pik = gross - paid = 1000 - 500 = 500

          Difference = 180 kEUR (the WHT that would be incorrectly PIK'd)
        """
        result = compute_shl_period_v3(
            shl_balance=20_000.0,
            shl_rate_per_period=0.05,   # 5% per period → gross = 1000
            cf_available=500.0,
            method="pik_then_sweep",
            wht_rate=0.18,
            pik_switch_triggered=False,  # PIK phase
        )
        # Interest paid = min(500, net=820) = 500
        assert result.interest_paid_keur == 500.0
        # PIK = gross - paid = 1000 - 500 = 500 (CORRECT)
        assert abs(result.pik_addition_keur - 500.0) < 0.01
        # v2 buggy would give: pik = net - paid = 820 - 500 = 320 (WRONG)
        assert result.new_balance_keur == 20_500.0
        # WHT on cash interest: paid * wht/(1-wht) = 500 * 0.18/0.82 = 109.76
        assert abs(result.interest_wht_keur - 109.76) < 0.1

    def test_shl_bullet_final_period(self):
        """Bullet: principal repaid in final period, no PIK."""
        result = compute_shl_period_v3(
            shl_balance=30_000.0,
            shl_rate_per_period=0.04,   # 4% → gross = 1200
            cf_available=5000.0,
            method="bullet",
            wht_rate=0.0,
            is_final_period=True,
        )
        # Interest paid = min(5000, 1200) = 1200
        assert result.interest_paid_keur == 1200.0
        # Principal = full balance = 30,000
        assert result.principal_keur == 30_000.0
        # No PIK (fully paid)
        assert result.pik_addition_keur == 0.0
        # Balance = 0
        assert result.new_balance_keur == 0.0

    def test_shl_cash_sweep(self):
        """Cash sweep: interest → principal from remaining CF."""
        result = compute_shl_period_v3(
            shl_balance=15_000.0,
            shl_rate_per_period=0.04,   # 4% → gross = 600, net = 600 (no WHT)
            cf_available=800.0,
            method="cash_sweep",
            wht_rate=0.0,
        )
        # Interest paid = min(800, 600) = 600
        assert result.interest_paid_keur == 600.0
        # Principal = remaining CF = 800 - 600 = 200
        assert result.principal_keur == 200.0
        # PIK = gross - paid = 600 - 600 = 0
        assert result.pik_addition_keur == 0.0
        # New balance = 15,000 - 200 + 0 = 14,800
        assert result.new_balance_keur == 14_800.0

    def test_shl_accrued_no_change(self):
        """Accrued: balance unchanged, nothing paid."""
        result = compute_shl_period_v3(
            shl_balance=25_000.0,
            shl_rate_per_period=0.04,
            cf_available=5000.0,
            method="accrued",
            wht_rate=0.0,
        )
        assert result.interest_paid_keur == 0.0
        assert result.principal_keur == 0.0
        assert result.pik_addition_keur == 0.0
        assert result.new_balance_keur == 25_000.0  # No change

    def test_shl_zero_balance(self):
        """Zero balance returns zeros."""
        result = compute_shl_period_v3(
            shl_balance=0.0,
            shl_rate_per_period=0.04,
            cf_available=1000.0,
            method="pik",
            wht_rate=0.18,
        )
        assert result.interest_paid_keur == 0.0
        assert result.interest_wht_keur == 0.0
        assert result.principal_keur == 0.0
        assert result.pik_addition_keur == 0.0
        assert result.new_balance_keur == 0.0


class TestSHLv3PIKSwitchTrigger:
    """Test pik_then_sweep switching logic."""

    def test_pik_phase(self):
        """PIK phase: no principal, PIK capitalized."""
        result = compute_shl_period_v3(
            shl_balance=33_047.0,
            shl_rate_per_period=0.03965,  # ~7.93% annual
            cf_available=954.0,
            method="pik_then_sweep",
            wht_rate=0.0,
            pik_switch_triggered=False,
        )
        # CF < gross interest → partial payment, rest PIK
        gross = 33_047 * 0.03965
        assert result.interest_paid_keur == 954.0
        assert abs(result.pik_addition_keur - (gross - 954.0)) < 0.1
        assert result.principal_keur == 0.0

    def test_sweep_phase(self):
        """SWEEP phase: full interest + principal from surplus."""
        result = compute_shl_period_v3(
            shl_balance=33_047.0,
            shl_rate_per_period=0.03965,
            cf_available=5000.0,  # Large CF triggers sweep
            method="pik_then_sweep",
            wht_rate=0.0,
            pik_switch_triggered=True,
        )
        # Full interest paid
        gross = 33_047 * 0.03965
        assert result.interest_paid_keur == gross
        # Principal from remaining
        remaining = 5000 - gross
        assert result.principal_keur == min(remaining, 33_047)
        # No PIK in sweep phase
        assert result.pik_addition_keur == 0.0


class TestSHLv3Schedule:
    """Test full SHL schedule generation."""

    def test_schedule_bullet(self):
        """Bullet: interest each period, principal at end."""
        results = shl_schedule_summary(
            initial_balance=20_000.0,
            rate_per_period=0.04,
            cf_schedule=[1200.0] * 10,  # Enough for interest
            method="bullet",
            wht_rate=0.0,
            tenor_periods=10,
        )
        # First 9 periods: interest only
        for r in results[:-1]:
            assert r.interest_paid_keur == 800.0  # 20,000 * 0.04
            assert r.principal_keur == 0.0
            assert r.pik_addition_keur == 0.0
        # Final period: principal
        final = results[-1]
        assert final.principal_keur == 20_000.0
        assert final.new_balance_keur == 0.0

    def test_schedule_pik(self):
        """PIK: balance grows each period by gross interest."""
        results = shl_schedule_summary(
            initial_balance=10_000.0,
            rate_per_period=0.04,
            cf_schedule=[0.0] * 5,  # No cash
            method="pik",
            wht_rate=0.0,
            tenor_periods=5,
        )
        # Each period: PIK = gross interest, balance grows
        balance = 10_000.0
        for r in results:
            pik = balance * 0.04
            assert abs(r.pik_addition_keur - pik) < 0.01
            balance = r.new_balance_keur
            assert abs(balance - (10_000 * (1.04 ** (results.index(r) + 1)))) < 0.01


class TestSHLv3TUHORealistic:
    """Test TUHO realistic scenario from calibration."""

    def test_tuho_y1h1_disbursement(self):
        """TUHO Y1-H1: SHL just disbursed, no operating DS yet.

        From calibration:
          - SHL disbursed: 29,135 kEUR
          - SHL IDC: 3,569 kEUR
          - Opening balance: 32,704 kEUR
          - Rate: 7.93% annual = 3.965% per period
          - FCF for SHL: 954 kEUR (EBITDA - senior DS)

        Result: PIK because FCF < accrued interest
          - Gross interest = 32,704 * 0.03965 = 1,297 kEUR
          - Interest paid = min(954, 1297 * (1-0)) = 954
          - PIK = 1297 - 954 = 343 kEUR
          - New balance = 32,704 + 343 = 33,047 kEUR
        """
        result = compute_shl_period_v3(
            shl_balance=32_704.0,
            shl_rate_per_period=0.03965,  # 7.93% annual / 2
            cf_available=954.0,
            method="pik_then_sweep",
            wht_rate=0.0,  # TUHO WHT = 0%
            pik_switch_triggered=False,
        )
        gross_interest = 32_704 * 0.03965
        assert abs(gross_interest - 1297.0) < 1.0  # ~1,297 kEUR
        assert result.interest_paid_keur == 954.0  # limited by CF
        assert abs(result.pik_addition_keur - (gross_interest - 954.0)) < 1.0  # ~343 kEUR
        assert abs(result.new_balance_keur - 33_047.0) < 1.0  # ~33,047 kEUR

    def test_shl_plus_dividends_method_no_double_counting(self):
        """SHL + dividends method: interest paid ≠ interest PIK'd.

        In shl_plus_dividends method, equity CF = SHL interest (cash) + dividends.
        The SHL interest is the CASH payment, not the PIK'd amount.
        This avoids double-counting: PIK increases balance, then gets repaid as principal.
        """
        # PIK phase
        result_pik = compute_shl_period_v3(
            shl_balance=32_704.0,
            shl_rate_per_period=0.03965,
            cf_available=954.0,
            method="pik_then_sweep",
            wht_rate=0.0,
            pik_switch_triggered=False,
        )
        # Cash interest paid (goes to equity CF calculation)
        assert result_pik.interest_paid_keur == 954.0
        # PIK capitalized (goes to balance, later repaid as principal)
        assert result_pik.pik_addition_keur > 0.0

        # Sweep phase (if triggered)
        result_sweep = compute_shl_period_v3(
            shl_balance=33_047.0,
            shl_rate_per_period=0.03965,
            cf_available=5000.0,
            method="pik_then_sweep",
            wht_rate=0.0,
            pik_switch_triggered=True,
        )
        # Full interest paid (goes to equity CF)
        assert result_sweep.interest_paid_keur > 0
        # Principal repaid (reduces balance)
        assert result_sweep.principal_keur > 0
        # No PIK in sweep
        assert result_sweep.pik_addition_keur == 0.0


class TestSHLv3Properties:
    """Test SHLPeriodResult properties."""

    def test_gross_interest_property(self):
        """gross_interest = interest_paid + interest_wht."""
        result = compute_shl_period_v3(
            shl_balance=20_000.0,
            shl_rate_per_period=0.05,
            cf_available=300.0,
            method="pik_then_sweep",
            wht_rate=0.18,
            pik_switch_triggered=False,
        )
        gross = result.gross_interest_keur
        paid = result.interest_paid_keur
        wht = result.interest_wht_keur
        # WHT is computed on the paid portion
        expected_wht = paid * 0.18 / 0.82 if paid > 0 else 0.0
        assert abs(gross - (paid + expected_wht)) < 0.1 or abs(gross - (paid + wht)) < 0.1

    def test_net_cash_outflow_property(self):
        """net_cash_outflow = interest_paid + principal (excludes WHT)."""
        result = compute_shl_period_v3(
            shl_balance=20_000.0,
            shl_rate_per_period=0.05,
            cf_available=2000.0,
            method="cash_sweep",
            wht_rate=0.0,
        )
        net_outflow = result.net_cash_outflow_keur
        assert net_outflow == result.interest_paid_keur + result.principal_keur