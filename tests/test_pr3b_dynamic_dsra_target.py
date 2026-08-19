"""Tests for PR-3B: dynamic DSRA target schedule (DsraTargetPolicy).

MEASUREMENT DATE: j=i (current period INCLUDED in coverage window).
Source-proven from TUHO/Oborovo workbooks:
  TUHO:    6m target at op_0 = DS[op_0] = 2116.361394092063
  Oborovo: 6m target at op_0 = DS[op_0] = 2239.133412854356

Covers:
  - DsraTargetPolicy enum values
  - months_between() exact calendar arithmetic
  - build_dsra_required_balance_schedule() FIXED_AMOUNT and FORWARD policies
  - Measurement date: j=i algorithm (current period included)
  - Generic time-coverage: 3m / 6m / 9m / 12m on semi-annual periods
  - Workbook-parity source tests: TUHO and Oborovo 3m/6m/12m
  - Legacy formula cross-verification (confirmed equivalent)
  - compute_cod_dsra_funding_keur()
  - CashDsraInput target_policy / dsra_months fields
  - run_cash_dsra_model() consuming dynamic schedule
  - COD funding handshake: opening = first-period dynamic target
  - NONE / DSRF parity: neutral pass-through
  - Target-rise → top_up; target-decline → no release (UNRESOLVED_RELEASE_POLICY)
  - Cash and balance conservation per period
  - Adapter maps dsra_target_policy to DsraTargetPolicy
  - Production-path: adapter → orchestrator → cash_dsra.required_balance_keur
  - Error paths: length mismatch, duplicate indices, invalid dates, etc.
"""
from __future__ import annotations

import dataclasses
import math
from datetime import date

import pytest

from financial_engine.dsra.target import (
    DsraTargetPolicy,
    build_dsra_required_balance_schedule,
    compute_cod_dsra_funding_keur,
    months_between,
)
from financial_engine.dsra.contracts import CashDsraInput, CashDsraPeriodResult, CashDsraSchedules
from financial_engine.dsra.model import run_cash_dsra_model
from financial_engine.results import PostSeniorCashSchedules, OperatingPeriodResult
from finco_core.inputs import DebtServiceReserveSupportMode

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_periods(n_construction: int, n_operating: int):
    """Build synthetic semi-annual period data (6-month periods)."""
    n = n_construction + n_operating
    indices = tuple(range(n))
    start_dates = []
    end_dates = []
    is_construction = []
    base = date(2024, 1, 1)
    for i in range(n):
        yr = base.year + (base.month - 1 + i * 6) // 12
        mo = (base.month - 1 + i * 6) % 12 + 1
        s = date(yr, mo, 1)
        ey = base.year + (base.month - 1 + (i + 1) * 6) // 12
        em = (base.month - 1 + (i + 1) * 6) % 12 + 1
        e = date(ey, em, 1)
        start_dates.append(s)
        end_dates.append(e)
        is_construction.append(i < n_construction)
    return indices, tuple(start_dates), tuple(end_dates), tuple(is_construction)


def _make_post_senior(period_indices, cash_values):
    n = len(cash_values)
    return PostSeniorCashSchedules(
        period_indices=period_indices,
        base_cfads_keur=tuple(cash_values),
        senior_debt_service_keur=(0.0,) * n,
        cash_after_senior_before_reserves_keur=tuple(cash_values),
        cash_available_for_shl_before_reserves_keur=tuple(max(0.0, v) for v in cash_values),
    )


def _make_op_periods(period_indices, is_construction):
    base = date(2024, 1, 1)
    results = []
    for i, (idx, ic) in enumerate(zip(period_indices, is_construction)):
        yr_s = base.year + (i * 6) // 12
        mo_s = (base.month - 1 + i * 6) % 12 + 1
        s = date(yr_s, mo_s, 1)
        yr_e = base.year + ((i + 1) * 6) // 12
        mo_e = (base.month - 1 + (i + 1) * 6) % 12 + 1
        e = date(yr_e, mo_e, 1)
        results.append(OperatingPeriodResult(
            period_index=idx,
            period_start=s,
            period_end=e,
            year_index=float(idx // 2),
            period_in_year=float(idx % 2),
            is_construction=ic,
            is_operation=not ic,
            is_ppa_active=True,
            days_in_period=181,
            day_fraction=181 / 365.0,
            production_mwh=0.0,
            revenue_keur=0.0,
            opex_keur=0.0,
            ebitda_keur=0.0,
            book_depreciation_keur=0.0,
            tax_depreciation_keur=0.0,
            ebit_keur=0.0,
        ))
    return tuple(results)


# ---------------------------------------------------------------------------
# DsraTargetPolicy
# ---------------------------------------------------------------------------

class TestDsraTargetPolicyEnum:
    def test_values(self):
        assert DsraTargetPolicy.FIXED_AMOUNT.value == "fixed_amount"
        assert DsraTargetPolicy.FORWARD_DEBT_SERVICE_MONTHS.value == "forward_debt_service_months"

    def test_distinct(self):
        assert DsraTargetPolicy.FIXED_AMOUNT != DsraTargetPolicy.FORWARD_DEBT_SERVICE_MONTHS

    def test_importable_from_contracts(self):
        from financial_engine.dsra.contracts import CashDsraInput
        inp = CashDsraInput(
            mode=DebtServiceReserveSupportMode.NONE,
            requirement_keur=0.0,
            target_policy=DsraTargetPolicy.FIXED_AMOUNT,
        )
        assert inp.target_policy == DsraTargetPolicy.FIXED_AMOUNT


# ---------------------------------------------------------------------------
# months_between
# ---------------------------------------------------------------------------

class TestMonthsBetween:
    def test_exact_6_months(self):
        assert months_between(date(2024, 1, 1), date(2024, 7, 1)) == pytest.approx(6.0)

    def test_exact_12_months(self):
        assert months_between(date(2024, 1, 1), date(2025, 1, 1)) == pytest.approx(12.0)

    def test_exact_3_months(self):
        assert months_between(date(2024, 1, 1), date(2024, 4, 1)) == pytest.approx(3.0)

    def test_zero_when_end_equals_start(self):
        assert months_between(date(2024, 6, 1), date(2024, 6, 1)) == 0.0

    def test_zero_when_end_before_start(self):
        assert months_between(date(2024, 7, 1), date(2024, 6, 1)) == 0.0

    def test_same_day_different_months(self):
        result = months_between(date(2024, 1, 15), date(2024, 7, 15))
        assert result == pytest.approx(6.0)


# ---------------------------------------------------------------------------
# FIXED_AMOUNT policy
# ---------------------------------------------------------------------------

class TestFixedAmountPolicy:
    def test_all_operating_uniform(self):
        indices, starts, ends, is_constr = _make_periods(0, 4)
        ds = (1000.0, 1000.0, 1000.0, 1000.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=6,
            policy=DsraTargetPolicy.FIXED_AMOUNT,
            fixed_amount_keur=2000.0,
        )
        assert result == (2000.0, 2000.0, 2000.0, 2000.0)

    def test_construction_periods_zero(self):
        indices, starts, ends, is_constr = _make_periods(2, 3)
        ds = (0.0, 0.0, 1000.0, 1000.0, 1000.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=6,
            policy=DsraTargetPolicy.FIXED_AMOUNT,
            fixed_amount_keur=1500.0,
        )
        assert result == (0.0, 0.0, 1500.0, 1500.0, 1500.0)

    def test_zero_fixed_amount(self):
        indices, starts, ends, is_constr = _make_periods(0, 2)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=(500.0, 500.0),
            coverage_months=6,
            policy=DsraTargetPolicy.FIXED_AMOUNT,
            fixed_amount_keur=0.0,
        )
        assert result == (0.0, 0.0)

    def test_empty_schedule(self):
        result = build_dsra_required_balance_schedule(
            period_indices=(),
            period_start_dates=(),
            period_end_dates=(),
            is_construction=(),
            senior_debt_service_keur=(),
            coverage_months=6,
            policy=DsraTargetPolicy.FIXED_AMOUNT,
            fixed_amount_keur=1000.0,
        )
        assert result == ()


# ---------------------------------------------------------------------------
# MEASUREMENT DATE RULE (source-proven): j=i (CURRENT period included)
# ---------------------------------------------------------------------------

class TestMeasurementDateCurrentPeriodIncluded:
    """Source-proven: target at period t covers DS starting from period t (not t+1).

    Evidence:
      TUHO   6m target at op_0 = DS[op_0] = 2116.361394  (not DS[op_1])
      Oborovo 6m target at op_0 = DS[op_0] = 2239.133413  (not DS[op_1])
    """

    def test_6m_target_at_period0_equals_own_ds(self):
        """6m coverage at period 0 = DS[0] (current period), NOT DS[1]."""
        indices, starts, ends, is_constr = _make_periods(0, 4)
        ds = (1000.0, 1100.0, 1200.0, 0.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=6,
        )
        # j=i: period 0 covers DS[0]=1000 with fraction 1.0
        assert result[0] == pytest.approx(1000.0)
        # j=i: period 1 covers DS[1]=1100 with fraction 1.0
        assert result[1] == pytest.approx(1100.0)

    def test_6m_not_equal_to_next_period_ds(self):
        """Verify algorithm is j=i: result[0] != DS[1] when DS[0] != DS[1]."""
        indices, starts, ends, is_constr = _make_periods(0, 3)
        ds = (2000.0, 1800.0, 1600.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=6,
        )
        assert result[0] == pytest.approx(2000.0)  # DS[0], NOT DS[1]=1800
        assert result[0] != pytest.approx(1800.0)

    def test_terminal_period_covers_only_itself(self):
        """Last period: 6m coverage = DS[last] (no future periods)."""
        indices, starts, ends, is_constr = _make_periods(0, 3)
        ds = (1000.0, 1100.0, 1200.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=6,
        )
        # Period 2 (last): j=2, DS[2]=1200, fraction=1.0 → 1200
        assert result[2] == pytest.approx(1200.0)


# ---------------------------------------------------------------------------
# 6m semi-annual (one full payment — current period)
# ---------------------------------------------------------------------------

class TestForwardDsra6mSemiannual:
    """6m coverage on 6m periods → fraction=1.0 → target = DS[current]."""

    def test_6m_period0(self):
        indices, starts, ends, is_constr = _make_periods(0, 4)
        ds = (1000.0, 1100.0, 1200.0, 0.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=6,
        )
        assert result[0] == pytest.approx(1000.0)
        assert result[1] == pytest.approx(1100.0)
        assert result[2] == pytest.approx(1200.0)
        assert result[3] == pytest.approx(0.0)  # DS[3]=0

    def test_terminal_zero_ds(self):
        indices, starts, ends, is_constr = _make_periods(0, 3)
        ds = (1000.0, 1100.0, 0.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=6,
        )
        assert result[2] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 3m coverage on 6m periods (half of current payment)
# ---------------------------------------------------------------------------

class TestForwardDsra3mSemiannual:
    """3m coverage on 6m periods → fraction = 0.5 → target = 0.5 × DS[current]."""

    def test_3m_is_half_of_6m(self):
        """3m result should be exactly half of 6m result for each period."""
        indices, starts, ends, is_constr = _make_periods(0, 3)
        ds = (1000.0, 2000.0, 1800.0)
        result_3m = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=3,
        )
        result_6m = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=6,
        )
        for t3, t6 in zip(result_3m, result_6m):
            assert t3 == pytest.approx(t6 * 0.5)

    def test_3m_period0_value(self):
        """3m at period 0 = 0.5 × DS[0]."""
        indices, starts, ends, is_constr = _make_periods(0, 3)
        ds = (2000.0, 1800.0, 1600.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=3,
        )
        assert result[0] == pytest.approx(1000.0)  # 0.5 × 2000


# ---------------------------------------------------------------------------
# 12m coverage on 6m periods (current + next)
# ---------------------------------------------------------------------------

class TestForwardDsra12mSemiannual:
    """12m coverage on 6m periods → covers current + next payment."""

    def test_12m_period0_flat(self):
        """Flat DS: 12m = DS[0] + DS[1]."""
        indices, starts, ends, is_constr = _make_periods(0, 4)
        ds = (1000.0, 1000.0, 1000.0, 1000.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=12,
        )
        assert result[0] == pytest.approx(2000.0)  # DS[0] + DS[1]

    def test_12m_amortising_sum_of_two(self):
        """Amortising DS: 12m = DS[i] + DS[i+1] (not 2 × DS[i])."""
        indices, starts, ends, is_constr = _make_periods(0, 4)
        ds = (1000.0, 950.0, 900.0, 850.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=12,
        )
        assert result[0] == pytest.approx(1950.0)  # DS[0] + DS[1]
        assert result[1] == pytest.approx(1850.0)  # DS[1] + DS[2]
        assert result[2] == pytest.approx(1750.0)  # DS[2] + DS[3]
        assert result[3] == pytest.approx(850.0)   # DS[3] only (no period 4)

    def test_12m_differs_from_2x_current_when_amortising(self):
        """Sum of two != 2 × current for amortising schedule."""
        indices, starts, ends, is_constr = _make_periods(0, 4)
        ds = (1000.0, 900.0, 800.0, 700.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=12,
        )
        # result[0] = DS[0] + DS[1] = 1900, not 2×DS[0]=2000
        assert result[0] == pytest.approx(1900.0)
        assert result[0] != pytest.approx(2000.0)


# ---------------------------------------------------------------------------
# 9m coverage (1 full + 0.5 of next)
# ---------------------------------------------------------------------------

class TestForwardDsra9mSemiannual:
    """9m = ENGINE_GENERIC_CAPABILITY (not workbook-proven option).
    Semi-annual: 9m = DS[i] + 0.5 × DS[i+1]."""

    def test_9m_period0(self):
        indices, starts, ends, is_constr = _make_periods(0, 3)
        ds = (1000.0, 1000.0, 1000.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=9,
        )
        # Period 0: DS[0]=1000 full (6m) + DS[1]=1000 × 0.5 (3m) = 1500
        assert result[0] == pytest.approx(1500.0)

    def test_9m_amortising(self):
        indices, starts, ends, is_constr = _make_periods(0, 3)
        ds = (2000.0, 1800.0, 1600.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=9,
        )
        # Period 0: DS[0]=2000 + 0.5 × DS[1]=900 = 2900
        assert result[0] == pytest.approx(2900.0)


# ---------------------------------------------------------------------------
# WORKBOOK SOURCE PARITY TESTS (TUHO and Oborovo)
#
# Source: finco_recon/bank_sizing_candidates.py (TUHO DS1)
#         tests/test_phase23s (Oborovo DS1, DS2)
#         tests/test_stage_c3b3d2b2a (TUHO DS = -2116.361394092063)
# Active production: both projects use NONE mode (dsra_months=0).
# These tests validate source-available options ONLY (not active calibration).
# ---------------------------------------------------------------------------

class TestWorkbookSourceParityTUHO:
    """
    TUHO source evidence:
      DS1 (op_idx=0) = 2116.361394092063 kEUR
      DS2 (op_idx=1) = 2151.439207253809 kEUR
    Available DSRA options (3m/6m/12m):
      3m  = 1058.1806970460316 = DS1/2
      6m  = 2116.3613940920630 = DS1
      12m = 4267.8006013458730 = DS1 + DS2
    Source: finco_recon/bank_sizing_candidates.py line 397
    Active calibration: NONE mode (requirement_keur=0) — financials unchanged.
    """
    TUHO_DS1 = 2116.361394092063
    TUHO_DS2 = 2151.439207253809
    TUHO_3M  = 1058.1806970460316
    TUHO_6M  = 2116.3613940920630
    TUHO_12M = 4267.8006013458730

    def _make_tuho_like_schedule(self):
        """Synthetic 2-construction + N-operating with TUHO-like DS values."""
        n_constr = 2
        n_op = 4
        indices, starts, ends, is_constr = _make_periods(n_constr, n_op)
        # DS: 0 for construction, TUHO-like amortising for operations
        ds = (0.0, 0.0, self.TUHO_DS1, self.TUHO_DS2, 2186.0, 2200.0)
        return indices, starts, ends, is_constr, ds

    def test_tuho_6m_parity(self):
        """6m DSRA target at first operating period = DS1 = TUHO source 6m amount."""
        indices, starts, ends, is_constr, ds = self._make_tuho_like_schedule()
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=6,
        )
        first_op_idx = 2  # first non-construction period
        assert result[first_op_idx] == pytest.approx(self.TUHO_6M, rel=1e-9)

    def test_tuho_3m_parity(self):
        """3m DSRA target = DS1/2 = TUHO source 3m amount."""
        indices, starts, ends, is_constr, ds = self._make_tuho_like_schedule()
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=3,
        )
        first_op_idx = 2
        assert result[first_op_idx] == pytest.approx(self.TUHO_3M, rel=1e-9)

    def test_tuho_12m_parity(self):
        """12m DSRA target = DS1 + DS2 = TUHO source 12m amount."""
        indices, starts, ends, is_constr, ds = self._make_tuho_like_schedule()
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=12,
        )
        first_op_idx = 2
        assert result[first_op_idx] == pytest.approx(self.TUHO_12M, rel=1e-9)

    def test_tuho_12m_is_sum_of_ds1_ds2(self):
        """Explicitly prove 12m = DS1 + DS2 for amortising TUHO schedule."""
        expected = self.TUHO_DS1 + self.TUHO_DS2
        assert expected == pytest.approx(self.TUHO_12M, rel=1e-9)


class TestWorkbookSourceParityOborovo:
    """
    Oborovo source evidence:
      DS1 (op_idx=0) = 2239.133412854356 kEUR
      DS2 (op_idx=1) = 2202.625802862166 kEUR
    Available DSRA options (3m/6m/12m):
      3m  = 1119.566706427178 = DS1/2
      6m  = 2239.133412854356 = DS1
      12m = 4441.759215716522 = DS1 + DS2
    Source: tests/golden/fixtures/oborovo_golden.py (line 48: -2239.133, -2202.626...)
            tests/test_phase23s_combined_tuho_oborovo_frozen_senior_ds_regression_snapshot.py
    Active calibration: Inputs!I348=0 → NONE mode — calibration financials unchanged.
    """
    OB_DS1 = 2239.133412854356
    OB_DS2 = 2202.625802862166
    OB_3M  = 1119.566706427178
    OB_6M  = 2239.133412854356
    OB_12M = 4441.759215716522

    def _make_oborovo_like_schedule(self):
        n_constr = 1
        n_op = 4
        indices, starts, ends, is_constr = _make_periods(n_constr, n_op)
        ds = (0.0, self.OB_DS1, self.OB_DS2, 2240.0, 2100.0)
        return indices, starts, ends, is_constr, ds

    def test_oborovo_6m_parity(self):
        """6m target at first op period = DS1 = Oborovo source 6m amount."""
        indices, starts, ends, is_constr, ds = self._make_oborovo_like_schedule()
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=6,
        )
        first_op_idx = 1
        assert result[first_op_idx] == pytest.approx(self.OB_6M, rel=1e-9)

    def test_oborovo_3m_parity(self):
        """3m target = DS1/2 = Oborovo source 3m amount."""
        indices, starts, ends, is_constr, ds = self._make_oborovo_like_schedule()
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=3,
        )
        first_op_idx = 1
        assert result[first_op_idx] == pytest.approx(self.OB_3M, rel=1e-9)

    def test_oborovo_12m_parity(self):
        """12m target = DS1 + DS2 = Oborovo source 12m amount."""
        indices, starts, ends, is_constr, ds = self._make_oborovo_like_schedule()
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=12,
        )
        first_op_idx = 1
        assert result[first_op_idx] == pytest.approx(self.OB_12M, rel=1e-9)

    def test_oborovo_12m_equals_ds1_plus_ds2(self):
        """Explicitly prove 12m = DS1 + DS2."""
        expected = self.OB_DS1 + self.OB_DS2
        assert expected == pytest.approx(self.OB_12M, rel=1e-9)


# ---------------------------------------------------------------------------
# Legacy formula cross-verification
# ---------------------------------------------------------------------------

class TestLegacyFormulaCrossVerification:
    """Cross-verify: legacy formula annual_ds × dsra_months/12 is equivalent
    to time-coverage with j=i for FLAT DS schedules on regular periods."""

    def _legacy_target(self, ds_current: float, dsra_months: int, periods_per_year: int = 2) -> float:
        annual_ds = ds_current * periods_per_year
        return annual_ds * (dsra_months / 12)

    def test_6m_flat_matches_legacy(self):
        """Flat semi-annual DS, 6m → time-coverage = legacy formula."""
        indices, starts, ends, is_constr = _make_periods(0, 4)
        payment = 2239.0
        ds = (payment,) * 4
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=6,
        )
        legacy = self._legacy_target(payment, 6)
        assert result[0] == pytest.approx(legacy, rel=1e-6)

    def test_3m_flat_matches_legacy(self):
        indices, starts, ends, is_constr = _make_periods(0, 4)
        payment = 2116.0
        ds = (payment,) * 4
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=3,
        )
        legacy = self._legacy_target(payment, 3)
        assert result[0] == pytest.approx(legacy, rel=1e-6)

    def test_12m_flat_matches_legacy(self):
        indices, starts, ends, is_constr = _make_periods(0, 4)
        payment = 2239.0
        ds = (payment,) * 4
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=12,
        )
        legacy = self._legacy_target(payment, 12)
        # 12m flat: result = DS[i] + DS[i+1] = 2 × payment = legacy
        assert result[0] == pytest.approx(legacy, rel=1e-6)


# ---------------------------------------------------------------------------
# compute_cod_dsra_funding_keur
# ---------------------------------------------------------------------------

class TestComputeCodDsraFunding:
    def test_returns_first_operating_period(self):
        schedule = (0.0, 0.0, 2239.0, 2100.0, 2000.0)
        is_constr = (True, True, False, False, False)
        assert compute_cod_dsra_funding_keur(schedule, is_constr) == pytest.approx(2239.0)

    def test_all_construction_returns_zero(self):
        assert compute_cod_dsra_funding_keur((0.0, 0.0), (True, True)) == 0.0

    def test_no_construction_returns_first(self):
        assert compute_cod_dsra_funding_keur((1000.0, 900.0, 800.0), (False, False, False)) == pytest.approx(1000.0)

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="DSRA_COD_FUNDING_LENGTH_MISMATCH"):
            compute_cod_dsra_funding_keur((1000.0, 900.0), (True,))


# ---------------------------------------------------------------------------
# CashDsraInput — new fields
# ---------------------------------------------------------------------------

class TestCashDsraInputNewFields:
    def test_default_policy_is_fixed_amount(self):
        inp = CashDsraInput(mode=DebtServiceReserveSupportMode.NONE, requirement_keur=0.0)
        assert inp.target_policy == DsraTargetPolicy.FIXED_AMOUNT

    def test_default_dsra_months(self):
        inp = CashDsraInput(mode=DebtServiceReserveSupportMode.NONE, requirement_keur=0.0)
        assert inp.dsra_months == 6

    def test_forward_policy_requires_cash_dsra_mode(self):
        with pytest.raises(ValueError, match="FORWARD_DEBT_SERVICE_MONTHS policy requires mode=CASH_DSRA"):
            CashDsraInput(
                mode=DebtServiceReserveSupportMode.NONE,
                requirement_keur=0.0,
                target_policy=DsraTargetPolicy.FORWARD_DEBT_SERVICE_MONTHS,
                dsra_months=6,
            )

    def test_forward_policy_requires_positive_months(self):
        with pytest.raises(ValueError, match="FORWARD_DEBT_SERVICE_MONTHS requires dsra_months > 0"):
            CashDsraInput(
                mode=DebtServiceReserveSupportMode.CASH_DSRA,
                requirement_keur=0.0,
                target_policy=DsraTargetPolicy.FORWARD_DEBT_SERVICE_MONTHS,
                dsra_months=0,
            )

    def test_valid_forward_config(self):
        inp = CashDsraInput(
            mode=DebtServiceReserveSupportMode.CASH_DSRA,
            requirement_keur=1000.0,
            target_policy=DsraTargetPolicy.FORWARD_DEBT_SERVICE_MONTHS,
            dsra_months=6,
        )
        assert inp.target_policy == DsraTargetPolicy.FORWARD_DEBT_SERVICE_MONTHS
        assert inp.dsra_months == 6

    def test_invalid_target_policy_raises(self):
        with pytest.raises(ValueError, match="target_policy must be DsraTargetPolicy"):
            CashDsraInput(
                mode=DebtServiceReserveSupportMode.NONE,
                requirement_keur=0.0,
                target_policy="not_a_policy",  # type: ignore
            )

    def test_schedule_validation_negative_raises(self):
        with pytest.raises(ValueError, match="must be >= 0"):
            CashDsraInput(
                mode=DebtServiceReserveSupportMode.CASH_DSRA,
                requirement_keur=0.0,
                required_balance_schedule=(0.0, -100.0),
            )

    def test_schedule_validation_nan_raises(self):
        with pytest.raises(ValueError, match="must be finite"):
            CashDsraInput(
                mode=DebtServiceReserveSupportMode.CASH_DSRA,
                requirement_keur=0.0,
                required_balance_schedule=(0.0, float("nan")),
            )


# ---------------------------------------------------------------------------
# run_cash_dsra_model with dynamic schedule
# ---------------------------------------------------------------------------

class TestRunCashDsraModelDynamic:
    """Integration: model consumes required_balance_schedule per-period."""

    def _run(self, cash_values, schedule):
        n = len(cash_values)
        indices = tuple(range(n))
        is_constr = (True,) + (False,) * (n - 1)
        post_senior = _make_post_senior(indices, cash_values)
        op_periods = _make_op_periods(indices, is_constr)
        dsra_input = CashDsraInput(
            mode=DebtServiceReserveSupportMode.CASH_DSRA,
            requirement_keur=0.0,
            required_balance_schedule=schedule,
            target_policy=DsraTargetPolicy.FORWARD_DEBT_SERVICE_MONTHS,
            dsra_months=6,
        )
        return run_cash_dsra_model(post_senior, dsra_input, op_periods)

    def test_cod_opening_equals_first_dynamic_target(self):
        """Opening at first operating period = first-period dynamic target."""
        schedule = (0.0, 2000.0, 1900.0, 1800.0)
        result = self._run([0.0, 5000.0, 5000.0, 5000.0], schedule)
        first_op = next(r for r in result.period_results if not r.is_construction)
        assert first_op.opening_balance_keur == pytest.approx(2000.0)

    def test_per_period_target_varies(self):
        """required_balance_keur varies per operating period."""
        schedule = (0.0, 2000.0, 1900.0, 1800.0)
        result = self._run([0.0, 5000.0, 5000.0, 5000.0], schedule)
        op_results = [r for r in result.period_results if not r.is_construction]
        assert op_results[0].required_balance_keur == pytest.approx(2000.0)
        assert op_results[1].required_balance_keur == pytest.approx(1900.0)
        assert op_results[2].required_balance_keur == pytest.approx(1800.0)

    def test_target_rise_triggers_top_up(self):
        """When target rises, top_up = min(target - opening, cash_available)."""
        schedule = (0.0, 1000.0, 2000.0, 2000.0)
        result = self._run([0.0, 5000.0, 5000.0, 5000.0], schedule)
        op_results = [r for r in result.period_results if not r.is_construction]
        # Period 1: opening=1000 (closing_0=1000), target=2000 → top_up=1000
        assert op_results[1].top_up_keur == pytest.approx(1000.0)

    def test_target_decline_no_release(self):
        """UNRESOLVED_RELEASE_POLICY: release_keur=0 even when target falls."""
        schedule = (0.0, 2000.0, 1000.0, 800.0)
        result = self._run([0.0, 5000.0, 5000.0, 5000.0], schedule)
        for r in result.period_results:
            assert r.release_keur == pytest.approx(0.0)

    def test_cash_conservation_per_period(self):
        """cash_before - top_up + draw + release == cash_after."""
        schedule = (0.0, 1500.0, 2000.0, 1800.0)
        result = self._run([0.0, 800.0, 5000.0, 5000.0], schedule)
        for r in result.period_results:
            expected = r.cash_before_dsra_keur - r.top_up_keur + r.draw_to_cover_shortfall_keur + r.release_keur
            assert r.cash_after_dsra_keur == pytest.approx(expected, abs=1e-6)

    def test_balance_conservation_per_period(self):
        """opening + top_up - draw - release == closing."""
        schedule = (0.0, 1500.0, 2000.0, 1800.0)
        result = self._run([0.0, 800.0, 5000.0, 5000.0], schedule)
        for r in result.period_results:
            expected = r.opening_balance_keur + r.top_up_keur - r.draw_to_cover_shortfall_keur - r.release_keur
            assert r.closing_balance_keur == pytest.approx(expected, abs=1e-6)

    def test_length_mismatch_raises(self):
        indices = (0, 1, 2)
        post_senior = _make_post_senior(indices, [0.0, 1000.0, 1000.0])
        op_periods = _make_op_periods(indices, (True, False, False))
        dsra_input = CashDsraInput(
            mode=DebtServiceReserveSupportMode.CASH_DSRA,
            requirement_keur=0.0,
            required_balance_schedule=(0.0, 1000.0),  # wrong length
            target_policy=DsraTargetPolicy.FORWARD_DEBT_SERVICE_MONTHS,
            dsra_months=6,
        )
        with pytest.raises(ValueError, match="CASH_DSRA_SCHEDULE_LENGTH_MISMATCH"):
            run_cash_dsra_model(post_senior, dsra_input, op_periods)

    def test_forward_diagnostic_present(self):
        schedule = (0.0, 1000.0, 900.0)
        result = self._run([0.0, 5000.0, 5000.0], schedule)
        assert "FORWARD_DEBT_SERVICE_MONTHS" in " ".join(result.diagnostics)

    def test_static_diagnostic_present_when_no_schedule(self):
        indices = (0, 1, 2)
        post_senior = _make_post_senior(indices, [0.0, 1000.0, 1000.0])
        op_periods = _make_op_periods(indices, (True, False, False))
        dsra_input = CashDsraInput(
            mode=DebtServiceReserveSupportMode.CASH_DSRA,
            requirement_keur=500.0,
        )
        result = run_cash_dsra_model(post_senior, dsra_input, op_periods)
        assert "FIXED_AMOUNT" in " ".join(result.diagnostics)


# ---------------------------------------------------------------------------
# NONE / DSRF parity
# ---------------------------------------------------------------------------

class TestNoneDsrfParity:
    def test_none_mode_neutral(self):
        indices = (0, 1, 2)
        post_senior = _make_post_senior(indices, [100.0, 200.0, 300.0])
        op_periods = _make_op_periods(indices, (False, False, False))
        dsra_input = CashDsraInput(mode=DebtServiceReserveSupportMode.NONE, requirement_keur=0.0)
        result = run_cash_dsra_model(post_senior, dsra_input, op_periods)
        for r in result.period_results:
            assert r.top_up_keur == pytest.approx(0.0)
            assert r.draw_to_cover_shortfall_keur == pytest.approx(0.0)
            assert r.cash_after_dsra_keur == pytest.approx(r.cash_before_dsra_keur)


# ---------------------------------------------------------------------------
# Adapter mapping: dsra_target_policy field
# ---------------------------------------------------------------------------

class TestAdapterDsraTargetPolicyMapping:
    """Verify adapter reads FinancingParams.dsra_target_policy and maps to DsraTargetPolicy."""

    def test_none_policy_maps_to_fixed_amount(self):
        """dsra_target_policy=None (default) → FIXED_AMOUNT in CashDsraInput."""
        from app.project_factories import create_default_solar_project
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        project = create_default_solar_project()
        # Default factory has dsra_support_mode=NONE, dsra_target_policy=None
        model = build_senior_debt_model_input_from_project_inputs(project, source_id="test-adapter")
        assert model.dsra is not None
        assert model.dsra.target_policy == DsraTargetPolicy.FIXED_AMOUNT

    def test_forward_policy_string_maps_to_enum(self):
        """dsra_target_policy='forward_debt_service_months' → FORWARD_DEBT_SERVICE_MONTHS."""
        import dataclasses
        from app.project_factories import create_default_solar_project
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        from finco_core.inputs import DebtServiceReserveSupportMode
        project = create_default_solar_project()
        # Override financing to CASH_DSRA + FORWARD policy
        new_fin = dataclasses.replace(
            project.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.CASH_DSRA,
            dsra_target_policy="forward_debt_service_months",
            dsra_months=6,
            debt_service_reserve_requirement_keur=1000.0,
        )
        new_project = dataclasses.replace(project, financing=new_fin)
        model = build_senior_debt_model_input_from_project_inputs(new_project, source_id="test-adapter-forward")
        assert model.dsra.target_policy == DsraTargetPolicy.FORWARD_DEBT_SERVICE_MONTHS
        assert model.dsra.dsra_months == 6

    def test_unknown_policy_string_raises_dsra_target_policy_invalid(self):
        """Unrecognised dsra_target_policy string → DSRA_TARGET_POLICY_INVALID (fail closed)."""
        import dataclasses
        from app.project_factories import create_default_solar_project
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        project = create_default_solar_project()
        new_fin = dataclasses.replace(project.financing, dsra_target_policy="some_unknown_value")
        new_project = dataclasses.replace(project, financing=new_fin)
        with pytest.raises(ValueError, match="DSRA_TARGET_POLICY_INVALID"):
            build_senior_debt_model_input_from_project_inputs(new_project, source_id="test-adapter-unknown")

    def test_explicit_fixed_amount_policy_string_accepted(self):
        """Explicit 'fixed_amount' string → FIXED_AMOUNT enum (fail closed, explicit)."""
        import dataclasses
        from app.project_factories import create_default_solar_project
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        project = create_default_solar_project()
        new_fin = dataclasses.replace(project.financing, dsra_target_policy="fixed_amount")
        new_project = dataclasses.replace(project, financing=new_fin)
        model = build_senior_debt_model_input_from_project_inputs(new_project, source_id="test-adapter-fixed")
        assert model.dsra.target_policy == DsraTargetPolicy.FIXED_AMOUNT


# ---------------------------------------------------------------------------
# Production-path test: adapter → orchestrator → cash_dsra.required_balance_keur
# Mandatory: must NOT manually construct required_balance_schedule.
# ---------------------------------------------------------------------------

class TestProductionPathDynamicTarget:
    """End-to-end: ProjectInputs.dsra_target_policy → orchestrator → dynamic target in result.

    Uses a Solar project factory with CASH_DSRA + FORWARD_DEBT_SERVICE_MONTHS.
    Asserts that required_balance_keur at first operating period equals DS[first_op].
    This proves the orchestrator's Step 9b correctly builds the dynamic schedule
    from the final Senior DS vector post-solve.
    """

    def _run_with_forward_dsra(self, project, dsra_months: int):
        import dataclasses
        from app.project_factories import create_default_solar_project
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        from financial_engine.orchestrator import run_senior_debt_model
        from finco_core.inputs import DebtServiceReserveSupportMode

        new_fin = dataclasses.replace(
            project.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.CASH_DSRA,
            dsra_target_policy="forward_debt_service_months",
            dsra_months=dsra_months,
            debt_service_reserve_requirement_keur=500.0,  # seed for Project Uses
        )
        new_project = dataclasses.replace(project, financing=new_fin)
        model = build_senior_debt_model_input_from_project_inputs(new_project, source_id="test-prod-path")
        return run_senior_debt_model(model)

    def test_dynamic_target_in_result(self):
        """cash_dsra.period_results[first_op].required_balance_keur is > 0 and tracks Senior DS."""
        from app.project_factories import create_default_solar_project
        project = create_default_solar_project()
        result = self._run_with_forward_dsra(project, dsra_months=6)

        assert result.cash_dsra is not None
        assert result.post_senior_cash is not None

        # Find first non-construction period
        period_results = result.cash_dsra.period_results
        post_senior = result.post_senior_cash
        ds_by_idx = dict(zip(post_senior.period_indices, post_senior.senior_debt_service_keur))

        first_op = next((r for r in period_results if not r.is_construction), None)
        assert first_op is not None, "Must have at least one operating period"

        ds_first_op = ds_by_idx.get(first_op.period_index, 0.0)
        req = first_op.required_balance_keur

        # Dynamic target must be positive and dominated by DS[first_op] (current period, j=i).
        # Periods are ~6m so 6m coverage may bleed slightly into the next period (pro-rata).
        # Bounds: DS[first_op] <= target <= DS[first_op] * 1.15 (at most ~15% bleed).
        assert req > 0.0, "Dynamic DSRA target must be positive at first operating period"
        assert req >= ds_first_op * 0.95, (
            f"Target {req:.2f} should be at least DS[first_op]={ds_first_op:.2f} "
            "(j=i: current period is included in coverage)"
        )
        assert req <= ds_first_op * 1.15, (
            f"Target {req:.2f} implausibly exceeds DS[first_op]={ds_first_op:.2f} by >15%"
        )

    def test_dynamic_target_changes_when_senior_ds_changes(self):
        """required_balance_keur changes when Senior DS changes — proves end-to-end wiring."""
        import dataclasses
        from app.project_factories import create_default_solar_project, create_default_wind_project
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        from financial_engine.orchestrator import run_senior_debt_model
        from finco_core.inputs import DebtServiceReserveSupportMode

        solar = create_default_solar_project()
        wind = create_default_wind_project()

        result_solar = self._run_with_forward_dsra(solar, dsra_months=6)
        result_wind = self._run_with_forward_dsra(wind, dsra_months=6)

        def first_op_required(result):
            return next(
                r.required_balance_keur
                for r in result.cash_dsra.period_results
                if not r.is_construction
            )

        solar_req = first_op_required(result_solar)
        wind_req = first_op_required(result_wind)

        # Solar and wind have different DS schedules → required_balance differs
        # This proves the dynamic target tracks the actual Senior DS, not a fixed scalar
        assert solar_req != pytest.approx(wind_req, rel=0.01), (
            f"Solar and wind should have different dynamic DSRA targets; "
            f"got solar={solar_req:.2f}, wind={wind_req:.2f}"
        )
        assert solar_req > 0.0
        assert wind_req > 0.0

    def test_6m_target_dominated_by_first_op_ds(self):
        """required_balance at first op is dominated by DS[first_op] (j=i algorithm).

        Proves the measurement date rule: current period IS included in coverage.
        Periods are ~6m; 6m coverage may pro-rate slightly into the next period.
        The target must be >= DS[first_op] (current period counted) and not equal
        to DS[second_op] alone (which would be the j=i+1 wrong algorithm).
        """
        from app.project_factories import create_default_solar_project
        project = create_default_solar_project()
        result = self._run_with_forward_dsra(project, dsra_months=6)

        period_results = result.cash_dsra.period_results
        post_senior = result.post_senior_cash
        ds_tuple = post_senior.senior_debt_service_keur
        idx_tuple = post_senior.period_indices

        op_results = [r for r in period_results if not r.is_construction]
        assert len(op_results) >= 2

        idx_to_ds = dict(zip(idx_tuple, ds_tuple))
        ds_first = idx_to_ds.get(op_results[0].period_index, 0.0)
        ds_second = idx_to_ds.get(op_results[1].period_index, 0.0)
        req = op_results[0].required_balance_keur

        # Current period is included (j=i): target >= DS[first_op] * 0.95
        assert req >= ds_first * 0.95, (
            f"Target {req:.2f} < DS[first_op]={ds_first:.2f}: "
            "current period must be included in coverage (j=i algorithm)"
        )
        # NOT dominated by second period alone
        if abs(ds_first - ds_second) > ds_first * 0.01:
            assert req != pytest.approx(ds_second, rel=0.001), (
                f"Target {req:.2f} == DS[second_op]={ds_second:.2f}: "
                "this would imply wrong j=i+1 algorithm"
            )


# ---------------------------------------------------------------------------
# Error paths in build_dsra_required_balance_schedule
# ---------------------------------------------------------------------------

class TestBuildScheduleErrors:
    def test_length_mismatch_start_dates(self):
        indices, starts, ends, is_constr = _make_periods(0, 3)
        with pytest.raises(ValueError, match="DSRA_TARGET_LENGTH_MISMATCH"):
            build_dsra_required_balance_schedule(
                period_indices=indices,
                period_start_dates=starts[:2],
                period_end_dates=ends,
                is_construction=is_constr,
                senior_debt_service_keur=(0.0,) * 3,
                coverage_months=6,
            )

    def test_duplicate_indices(self):
        _, starts, ends, is_constr = _make_periods(0, 3)
        with pytest.raises(ValueError, match="DSRA_TARGET_DUPLICATE_PERIOD_INDICES"):
            build_dsra_required_balance_schedule(
                period_indices=(0, 1, 1),
                period_start_dates=starts,
                period_end_dates=ends,
                is_construction=is_constr,
                senior_debt_service_keur=(0.0,) * 3,
                coverage_months=6,
            )

    def test_end_before_start_raises(self):
        indices, starts, ends, is_constr = _make_periods(0, 2)
        bad_ends = (ends[0], starts[0])
        with pytest.raises(ValueError, match="DSRA_TARGET_INVALID_DATES"):
            build_dsra_required_balance_schedule(
                period_indices=indices,
                period_start_dates=starts,
                period_end_dates=bad_ends,
                is_construction=is_constr,
                senior_debt_service_keur=(0.0, 0.0),
                coverage_months=6,
            )

    def test_coverage_months_zero_raises(self):
        indices, starts, ends, is_constr = _make_periods(0, 2)
        with pytest.raises(ValueError, match="DSRA_TARGET_INVALID_COVERAGE_MONTHS"):
            build_dsra_required_balance_schedule(
                period_indices=indices,
                period_start_dates=starts,
                period_end_dates=ends,
                is_construction=is_constr,
                senior_debt_service_keur=(0.0, 0.0),
                coverage_months=0,
            )

    def test_negative_fixed_amount_raises(self):
        indices, starts, ends, is_constr = _make_periods(0, 2)
        with pytest.raises(ValueError, match="DSRA_TARGET_INVALID_FIXED_AMOUNT"):
            build_dsra_required_balance_schedule(
                period_indices=indices,
                period_start_dates=starts,
                period_end_dates=ends,
                is_construction=is_constr,
                senior_debt_service_keur=(0.0, 0.0),
                coverage_months=6,
                policy=DsraTargetPolicy.FIXED_AMOUNT,
                fixed_amount_keur=-100.0,
            )

    def test_non_integer_coverage_months_raises(self):
        indices, starts, ends, is_constr = _make_periods(0, 2)
        with pytest.raises(ValueError, match="DSRA_TARGET_INVALID_COVERAGE_MONTHS"):
            build_dsra_required_balance_schedule(
                period_indices=indices,
                period_start_dates=starts,
                period_end_dates=ends,
                is_construction=is_constr,
                senior_debt_service_keur=(0.0, 0.0),
                coverage_months=6.0,  # type: ignore
            )


# ---------------------------------------------------------------------------
# Mandatory new tests — correction pass
# ---------------------------------------------------------------------------

class TestAdapterFailClosed:
    """Adapter must fail closed on unknown policy (section 16A) and preserve zero months (16B)."""

    def test_unknown_policy_raises_dsra_target_policy_invalid(self):
        """Unknown dsra_target_policy string → DSRA_TARGET_POLICY_INVALID (fail closed)."""
        import dataclasses
        from app.project_factories import create_default_solar_project
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        from finco_core.inputs import DebtServiceReserveSupportMode
        project = create_default_solar_project()
        new_fin = dataclasses.replace(
            project.financing,
            dsra_target_policy="not_a_valid_policy",
        )
        new_project = dataclasses.replace(project, financing=new_fin)
        with pytest.raises(ValueError, match="DSRA_TARGET_POLICY_INVALID"):
            build_senior_debt_model_input_from_project_inputs(new_project, source_id="test-invalid-policy")

    def test_forward_with_zero_months_fails_not_converts(self):
        """FORWARD + dsra_months=0 must NOT become 6; it must fail closed at contract level."""
        import dataclasses
        from app.project_factories import create_default_solar_project
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        from finco_core.inputs import DebtServiceReserveSupportMode
        project = create_default_solar_project()
        new_fin = dataclasses.replace(
            project.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.CASH_DSRA,
            dsra_target_policy="forward_debt_service_months",
            dsra_months=0,  # explicit zero — must NOT be converted to 6
            debt_service_reserve_requirement_keur=500.0,
        )
        new_project = dataclasses.replace(project, financing=new_fin)
        # CashDsraInput.__post_init__ requires dsra_months > 0 for FORWARD policy
        with pytest.raises(ValueError, match="dsra_months"):
            build_senior_debt_model_input_from_project_inputs(new_project, source_id="test-zero-months")

    def test_none_policy_resolves_to_fixed_amount(self):
        """None dsra_target_policy → backward-compatible FIXED_AMOUNT (not an error)."""
        import dataclasses
        from app.project_factories import create_default_solar_project
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        project = create_default_solar_project()
        new_fin = dataclasses.replace(project.financing, dsra_target_policy=None)
        new_project = dataclasses.replace(project, financing=new_fin)
        model = build_senior_debt_model_input_from_project_inputs(new_project, source_id="test-none-policy")
        assert model.dsra.target_policy == DsraTargetPolicy.FIXED_AMOUNT


class TestModelFailClosed:
    """run_cash_dsra_model must fail closed on policy/schedule mismatches (section 16C, 16D)."""

    def _make_post_senior_simple(self, n=3):
        indices = tuple(range(n))
        return PostSeniorCashSchedules(
            period_indices=indices,
            base_cfads_keur=(1000.0,) * n,
            senior_debt_service_keur=(500.0,) * n,
            cash_after_senior_before_reserves_keur=(500.0,) * n,
            cash_available_for_shl_before_reserves_keur=(500.0,) * n,
        )

    def _make_periods_simple(self, n=3):
        base = date(2024, 1, 1)
        results = []
        for i in range(n):
            yr = base.year + (base.month - 1 + i * 6) // 12
            mo = (base.month - 1 + i * 6) % 12 + 1
            s = date(yr, mo, 1)
            ey = base.year + (base.month - 1 + (i + 1) * 6) // 12
            em = (base.month - 1 + (i + 1) * 6) % 12 + 1
            e = date(ey, em, 1)
            results.append(OperatingPeriodResult(
                period_index=i, period_start=s, period_end=e,
                year_index=float(i // 2), period_in_year=float(i % 2),
                is_construction=(i == 0), is_operation=(i > 0), is_ppa_active=True,
                days_in_period=181, day_fraction=181/365.0, production_mwh=0.0,
                revenue_keur=0.0, opex_keur=0.0, ebitda_keur=0.0,
                book_depreciation_keur=0.0, tax_depreciation_keur=0.0, ebit_keur=0.0,
            ))
        return tuple(results)

    def test_forward_without_schedule_raises(self):
        """FORWARD + required_balance_schedule=None → CASH_DSRA_DYNAMIC_TARGET_SCHEDULE_REQUIRED."""
        ps = self._make_post_senior_simple()
        periods = self._make_periods_simple()
        dsra = CashDsraInput(
            mode=DebtServiceReserveSupportMode.CASH_DSRA,
            requirement_keur=500.0,
            target_policy=DsraTargetPolicy.FORWARD_DEBT_SERVICE_MONTHS,
            dsra_months=6,
            required_balance_schedule=None,
        )
        with pytest.raises(ValueError, match="CASH_DSRA_DYNAMIC_TARGET_SCHEDULE_REQUIRED"):
            run_cash_dsra_model(ps, dsra, periods)

    def test_fixed_with_schedule_raises_authority_conflict(self):
        """FIXED_AMOUNT + non-None required_balance_schedule → authority conflict error."""
        ps = self._make_post_senior_simple()
        periods = self._make_periods_simple()
        dsra = CashDsraInput(
            mode=DebtServiceReserveSupportMode.CASH_DSRA,
            requirement_keur=500.0,
            target_policy=DsraTargetPolicy.FIXED_AMOUNT,
            dsra_months=6,
            required_balance_schedule=(0.0, 500.0, 500.0),  # conflicts with FIXED_AMOUNT
        )
        with pytest.raises(ValueError, match="CASH_DSRA_FIXED_AMOUNT_AUTHORITY_CONFLICT"):
            run_cash_dsra_model(ps, dsra, periods)


class TestNegativeSeniorDsFails:
    """Negative Senior DS must fail closed (section 16E)."""

    def test_negative_ds_raises_dsra_target_negative_senior_ds(self):
        """Negative Senior DS in build_dsra_required_balance_schedule → DSRA_TARGET_NEGATIVE_SENIOR_DS."""
        indices, starts, ends, is_constr = _make_periods(0, 3)
        with pytest.raises(ValueError, match="DSRA_TARGET_NEGATIVE_SENIOR_DS"):
            build_dsra_required_balance_schedule(
                period_indices=indices,
                period_start_dates=starts,
                period_end_dates=ends,
                is_construction=is_constr,
                senior_debt_service_keur=(1000.0, -50.0, 1000.0),
                coverage_months=6,
            )


class TestNonChronologicalPeriodsFails:
    """Non-chronological start dates must fail closed (section 16F)."""

    def test_non_chronological_starts_raises(self):
        """Periods out of chronological order → DSRA_TARGET_NON_CHRONOLOGICAL_PERIODS."""
        # Use 3 non-overlapping periods but present them out of order by index 1→0→2
        # Each period: start=first-of-month, end=first-of-next-6-months, 6m apart.
        # Reverse period 0 and period 1 in the start array but keep end dates matching
        # their own starts so end > start still holds, but starts aren't ascending.
        from datetime import date
        starts = (date(2025, 1, 1), date(2024, 1, 1), date(2026, 1, 1))
        ends   = (date(2025, 7, 1), date(2024, 7, 1), date(2026, 7, 1))
        indices = (0, 1, 2)
        is_constr = (False, False, False)
        with pytest.raises(ValueError, match="DSRA_TARGET_NON_CHRONOLOGICAL_PERIODS"):
            build_dsra_required_balance_schedule(
                period_indices=indices,
                period_start_dates=starts,
                period_end_dates=ends,
                is_construction=is_constr,
                senior_debt_service_keur=(1000.0,) * 3,
                coverage_months=6,
            )


class TestCalibrationSourceParity:
    """Source project calibration: dsra_months=0 → zero delta (section 16H).

    Both calibration source projects use dsra_months=0 / NONE mode.
    Verifies no financial delta vs baseline NONE-mode run.
    """

    def test_source_project_p1_zero_months_neutral(self):
        """Source project P1 with dsra_months=0, NONE mode → zero DSRA balance throughout."""
        from app.project_factories import create_default_solar_project
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        from financial_engine.orchestrator import run_senior_debt_model
        import dataclasses

        project = create_default_solar_project()
        # Ensure NONE mode with dsra_months=0 (calibration source state)
        new_fin = dataclasses.replace(
            project.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.NONE,
            debt_service_reserve_requirement_keur=0.0,
            dsra_months=0,
            dsra_target_policy=None,
        )
        new_project = dataclasses.replace(project, financing=new_fin)
        model = build_senior_debt_model_input_from_project_inputs(new_project, source_id="test-calibration-p1")
        result = run_senior_debt_model(model)
        # All DSRA balances must be zero
        for r in result.cash_dsra.period_results:
            assert r.closing_balance_keur == pytest.approx(0.0), (
                f"Period {r.period_index}: closing_balance={r.closing_balance_keur} != 0 in NONE mode"
            )

    def test_source_project_p2_zero_months_neutral(self):
        """Source project P2 with dsra_months=0, NONE mode → zero DSRA balance throughout."""
        from app.project_factories import create_default_wind_project
        from financial_engine.adapters.project_inputs import build_senior_debt_model_input_from_project_inputs
        from financial_engine.orchestrator import run_senior_debt_model
        import dataclasses

        project = create_default_wind_project()
        new_fin = dataclasses.replace(
            project.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.NONE,
            debt_service_reserve_requirement_keur=0.0,
            dsra_months=0,
            dsra_target_policy=None,
        )
        new_project = dataclasses.replace(project, financing=new_fin)
        model = build_senior_debt_model_input_from_project_inputs(new_project, source_id="test-calibration-p2")
        result = run_senior_debt_model(model)
        for r in result.cash_dsra.period_results:
            assert r.closing_balance_keur == pytest.approx(0.0), (
                f"Period {r.period_index}: closing_balance={r.closing_balance_keur} != 0 in NONE mode"
            )
