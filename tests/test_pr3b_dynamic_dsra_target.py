"""Tests for PR-3B: dynamic DSRA target schedule (DsraTargetPolicy).

Covers:
  - DsraTargetPolicy enum values
  - months_between() exact calendar arithmetic
  - build_dsra_required_balance_schedule() for FIXED_AMOUNT and FORWARD_DEBT_SERVICE_MONTHS
  - Generic time-coverage: 3m / 6m / 9m / 12m on semi-annual periods
  - Cross-verification with legacy workbook formula
  - compute_cod_dsra_funding_keur()
  - CashDsraInput.required_balance_schedule validation
  - run_cash_dsra_model() consuming dynamic schedule
  - COD funding handshake: opening = first-period dynamic target
  - NONE / DSRF parity: zero balance schedule, neutral
  - Target-rise → top_up increases; target-decline → no release (UNRESOLVED_RELEASE_POLICY)
  - Cash conservation and balance conservation per period
  - Error paths: length mismatch, duplicate indices, invalid dates, negative fixed_amount
"""
from __future__ import annotations

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
# build_dsra_required_balance_schedule — FIXED_AMOUNT
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
        ds = (500.0, 500.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
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
# Forward debt service months — 6m semi-annual (one full payment)
# ---------------------------------------------------------------------------

class TestForwardDsra6mSemiannual:
    """6m coverage on 6m periods → fraction=1.0 → target = next_payment."""

    def setup_method(self):
        self.indices, self.starts, self.ends, self.is_constr = _make_periods(0, 4)
        self.ds = (1000.0, 1100.0, 1200.0, 0.0)

    def test_first_period_covers_next(self):
        result = build_dsra_required_balance_schedule(
            period_indices=self.indices,
            period_start_dates=self.starts,
            period_end_dates=self.ends,
            is_construction=self.is_constr,
            senior_debt_service_keur=self.ds,
            coverage_months=6,
        )
        # Period 0: covers period 1 fully → 1100
        assert result[0] == pytest.approx(1100.0)

    def test_second_period(self):
        result = build_dsra_required_balance_schedule(
            period_indices=self.indices,
            period_start_dates=self.starts,
            period_end_dates=self.ends,
            is_construction=self.is_constr,
            senior_debt_service_keur=self.ds,
            coverage_months=6,
        )
        # Period 1: covers period 2 → 1200
        assert result[1] == pytest.approx(1200.0)

    def test_last_period_zero_ds_ahead(self):
        result = build_dsra_required_balance_schedule(
            period_indices=self.indices,
            period_start_dates=self.starts,
            period_end_dates=self.ends,
            is_construction=self.is_constr,
            senior_debt_service_keur=self.ds,
            coverage_months=6,
        )
        # Period 2: covers period 3 (DS=0) → 0
        assert result[2] == pytest.approx(0.0)

    def test_terminal_period_zero(self):
        result = build_dsra_required_balance_schedule(
            period_indices=self.indices,
            period_start_dates=self.starts,
            period_end_dates=self.ends,
            is_construction=self.is_constr,
            senior_debt_service_keur=self.ds,
            coverage_months=6,
        )
        # Period 3 (last): no future periods → 0
        assert result[3] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Forward — 3m coverage on 6m semi-annual periods (half payment)
# ---------------------------------------------------------------------------

class TestForwardDsra3mSemiannual:
    """3m coverage on 6m periods → fraction = 0.5 → target = 0.5 × next_payment."""

    def test_3m_is_half_of_6m(self):
        indices, starts, ends, is_constr = _make_periods(0, 3)
        ds = (1000.0, 2000.0, 2000.0)
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
        # 3m should be exactly half of 6m for each period
        for t3, t6 in zip(result_3m, result_6m):
            assert t3 == pytest.approx(t6 * 0.5)

    def test_3m_period0_value(self):
        indices, starts, ends, is_constr = _make_periods(0, 3)
        ds = (0.0, 2000.0, 1800.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=3,
        )
        # Period 0: 3m coverage, next period (1) is 6m → fraction=0.5 → 1000
        assert result[0] == pytest.approx(1000.0)


# ---------------------------------------------------------------------------
# Forward — 12m coverage on 6m semi-annual periods (sum of 2 payments)
# ---------------------------------------------------------------------------

class TestForwardDsra12mSemiannual:
    """12m coverage on 6m periods → covers next 2 payments in full."""

    def test_12m_period0(self):
        indices, starts, ends, is_constr = _make_periods(0, 4)
        ds = (0.0, 1000.0, 1100.0, 1200.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=12,
        )
        # Period 0 → period 1 (1000) + period 2 (1100) = 2100
        assert result[0] == pytest.approx(2100.0)

    def test_12m_equals_two_6m_payments_when_flat(self):
        indices, starts, ends, is_constr = _make_periods(0, 4)
        ds = (0.0, 1000.0, 1000.0, 1000.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=12,
        )
        # Flat DS: 12m = 2 × 6m payment = 2000
        assert result[0] == pytest.approx(2000.0)

    def test_12m_amortising_differs_from_2x_current(self):
        """For amortising DS, sum-of-two is more accurate than 2 × current_period."""
        indices, starts, ends, is_constr = _make_periods(0, 4)
        ds = (0.0, 1000.0, 950.0, 900.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=12,
        )
        # Period 0: 1000 + 950 = 1950 (not 2×1000=2000)
        assert result[0] == pytest.approx(1950.0)
        # Period 1: 950 + 900 = 1850
        assert result[1] == pytest.approx(1850.0)


# ---------------------------------------------------------------------------
# Forward — 9m coverage (1.5 payments semi-annual)
# ---------------------------------------------------------------------------

class TestForwardDsra9mSemiannual:
    def test_9m_period0(self):
        indices, starts, ends, is_constr = _make_periods(0, 3)
        ds = (0.0, 1000.0, 1000.0)
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=9,
        )
        # Period 0: 6m fully = 1000; 3m partial of next (1000) = 500 → 1500
        assert result[0] == pytest.approx(1500.0)


# ---------------------------------------------------------------------------
# Legacy formula cross-verification
# ---------------------------------------------------------------------------

class TestLegacyFormulaCrossVerification:
    """Cross-verify with finco_core.waterfall.dsra_engine: target = payment × periods_per_year × dsra_months/12."""

    def _legacy_target(self, payment: float, dsra_months: int, periods_per_year: int = 2) -> float:
        annual_ds = payment * periods_per_year
        return annual_ds * (dsra_months / 12)

    def test_6m_flat_ds_matches_legacy(self):
        """Flat semi-annual DS → 6m coverage → time-coverage == legacy formula."""
        indices, starts, ends, is_constr = _make_periods(0, 4)
        payment = 2239.0  # Oborovo-like value
        ds = (0.0,) + (payment,) * 3
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=6,
        )
        legacy = self._legacy_target(payment, 6)
        # First period covers next period (flat) → matches legacy
        assert result[0] == pytest.approx(legacy, rel=1e-6)

    def test_3m_flat_ds_matches_legacy(self):
        indices, starts, ends, is_constr = _make_periods(0, 4)
        payment = 2100.0  # TUHO-like value
        ds = (0.0,) + (payment,) * 3
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

    def test_12m_flat_ds_matches_legacy(self):
        indices, starts, ends, is_constr = _make_periods(0, 4)
        payment = 2239.0
        ds = (0.0,) + (payment,) * 3
        result = build_dsra_required_balance_schedule(
            period_indices=indices,
            period_start_dates=starts,
            period_end_dates=ends,
            is_construction=is_constr,
            senior_debt_service_keur=ds,
            coverage_months=12,
        )
        legacy = self._legacy_target(payment, 12)
        # Flat schedule: sum-of-two = 2 × payment = legacy
        assert result[0] == pytest.approx(legacy, rel=1e-6)


# ---------------------------------------------------------------------------
# compute_cod_dsra_funding_keur
# ---------------------------------------------------------------------------

class TestComputeCodDsraFunding:
    def test_returns_first_operating_period(self):
        schedule = (0.0, 0.0, 2239.0, 2100.0, 2000.0)
        is_constr = (True, True, False, False, False)
        result = compute_cod_dsra_funding_keur(schedule, is_constr)
        assert result == pytest.approx(2239.0)

    def test_all_construction_returns_zero(self):
        schedule = (0.0, 0.0)
        is_constr = (True, True)
        result = compute_cod_dsra_funding_keur(schedule, is_constr)
        assert result == 0.0

    def test_no_construction_returns_first(self):
        schedule = (1000.0, 900.0, 800.0)
        is_constr = (False, False, False)
        result = compute_cod_dsra_funding_keur(schedule, is_constr)
        assert result == pytest.approx(1000.0)

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="DSRA_COD_FUNDING_LENGTH_MISMATCH"):
            compute_cod_dsra_funding_keur((1000.0, 900.0), (True,))


# ---------------------------------------------------------------------------
# CashDsraInput — required_balance_schedule validation
# ---------------------------------------------------------------------------

class TestCashDsraInputScheduleValidation:
    def test_valid_schedule_accepted(self):
        inp = CashDsraInput(
            mode=DebtServiceReserveSupportMode.CASH_DSRA,
            requirement_keur=0.0,
            required_balance_schedule=(0.0, 1000.0, 900.0),
        )
        assert inp.required_balance_schedule == (0.0, 1000.0, 900.0)

    def test_none_schedule_accepted(self):
        inp = CashDsraInput(
            mode=DebtServiceReserveSupportMode.CASH_DSRA,
            requirement_keur=500.0,
        )
        assert inp.required_balance_schedule is None

    def test_negative_value_raises(self):
        with pytest.raises(ValueError, match="must be >= 0"):
            CashDsraInput(
                mode=DebtServiceReserveSupportMode.CASH_DSRA,
                requirement_keur=0.0,
                required_balance_schedule=(0.0, -100.0),
            )

    def test_nan_value_raises(self):
        with pytest.raises(ValueError, match="must be finite"):
            CashDsraInput(
                mode=DebtServiceReserveSupportMode.CASH_DSRA,
                requirement_keur=0.0,
                required_balance_schedule=(0.0, float("nan")),
            )

    def test_non_tuple_raises(self):
        with pytest.raises(ValueError, match="must be a tuple or None"):
            CashDsraInput(
                mode=DebtServiceReserveSupportMode.CASH_DSRA,
                requirement_keur=0.0,
                required_balance_schedule=[0.0, 1000.0],  # type: ignore
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
        """When target rises, top_up = target - opening (if cash available)."""
        schedule = (0.0, 1000.0, 2000.0, 2000.0)
        result = self._run([0.0, 5000.0, 5000.0, 5000.0], schedule)
        op_results = [r for r in result.period_results if not r.is_construction]
        # Period 1: opening=1000 (from closing_0=1000 after top_up), target=2000
        assert op_results[1].top_up_keur == pytest.approx(1000.0)

    def test_target_decline_no_release(self):
        """UNRESOLVED_RELEASE_POLICY: release_keur=0 even when target falls."""
        schedule = (0.0, 2000.0, 1000.0, 800.0)
        result = self._run([0.0, 5000.0, 5000.0, 5000.0], schedule)
        for r in result.period_results:
            assert r.release_keur == pytest.approx(0.0)

    def test_cash_conservation_per_period(self):
        """cash_before - top_up + draw + release == cash_after for each period."""
        schedule = (0.0, 1500.0, 2000.0, 1800.0)
        result = self._run([0.0, 800.0, 5000.0, 5000.0], schedule)
        for r in result.period_results:
            expected = r.cash_before_dsra_keur - r.top_up_keur + r.draw_to_cover_shortfall_keur + r.release_keur
            assert r.cash_after_dsra_keur == pytest.approx(expected, abs=1e-6)

    def test_balance_conservation_per_period(self):
        """opening + top_up - draw - release == closing for each period."""
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
        )
        with pytest.raises(ValueError, match="CASH_DSRA_SCHEDULE_LENGTH_MISMATCH"):
            run_cash_dsra_model(post_senior, dsra_input, op_periods)

    def test_dynamic_diagnostic_present(self):
        schedule = (0.0, 1000.0, 900.0)
        result = self._run([0.0, 5000.0, 5000.0], schedule)
        diag_text = " ".join(result.diagnostics)
        assert "FORWARD_DEBT_SERVICE_MONTHS" in diag_text

    def test_static_diagnostic_present_when_no_schedule(self):
        indices = (0, 1, 2)
        post_senior = _make_post_senior(indices, [0.0, 1000.0, 1000.0])
        op_periods = _make_op_periods(indices, (True, False, False))
        dsra_input = CashDsraInput(
            mode=DebtServiceReserveSupportMode.CASH_DSRA,
            requirement_keur=500.0,
        )
        result = run_cash_dsra_model(post_senior, dsra_input, op_periods)
        diag_text = " ".join(result.diagnostics)
        assert "FIXED_AMOUNT" in diag_text


# ---------------------------------------------------------------------------
# NONE / DSRF mode parity with dynamic schedule
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
        bad_ends = (ends[0], starts[0])  # end < start for period 1
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
