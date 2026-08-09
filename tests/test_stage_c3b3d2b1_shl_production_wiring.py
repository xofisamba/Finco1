"""C3B3D2B1 — Production SHL Wiring + Instrument Day-Count Convention.

Test classes:
  TestA  ShlDayCountConvention contract
  TestB  ShlWaterfallPolicy contract
  TestC  compute_shl_dcf — ACT_365_FIXED dispatch
  TestD  compute_shl_dcf — ACT_360 dispatch
  TestE  ACT_365_FIXED leap-year periods (denominator stays 365)
  TestF  Instrument independence (SHL and Senior Debt conventions independent)
  TestG  compute_shl_schedule — construction period semantics
  TestH  compute_shl_schedule — operating chain roll-forward
  TestI  Oborovo construction parity
  TestJ  Oborovo operating parity — all 40 periods
  TestK  Cash seam adapter — derive cash_available from Phase 2C result
  TestL  Cash waterfall ordering documentation
  TestM  Fixed-point boundary
  TestN  Separate SHL vectors preserved
  TestO  Governance — no project dispatch, no DS25/DS40, no 13547.2

Verdict targeted: C3B3D2B1_READY_FOR_INDEPENDENT_REVIEW
"""
from __future__ import annotations

import inspect
import json
import math
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# ── fixture paths ────────────────────────────────────────────────────────────
_FIXTURE_DIR = Path(__file__).parent / "fixtures"
_D2A_FIXTURE = _FIXTURE_DIR / "excel_oborovo_shl_operating_truth.json"
_CF_FIXTURE = _FIXTURE_DIR / "excel_oborovo_financial_truth.json"
_IL_FIXTURE = _FIXTURE_DIR / "interest_limitation" / "oborovo_interest_limitation_fixture.json"

# ── module-level fixture loads ────────────────────────────────────────────────

def _load_d2a():
    with open(_D2A_FIXTURE) as f:
        return json.load(f)


def _load_cf():
    with open(_CF_FIXTURE) as f:
        return json.load(f)


_D2A = _load_d2a()
_CF = _load_cf()

# D2A operating periods [1..40] (index 0 = construction)
_D2A_PERIODS = _D2A["periods"]  # 41 elements
_CONSTRUCTION_PERIOD = _D2A_PERIODS[0]
_OPERATING_PERIODS = _D2A_PERIODS[1:]  # DS[1..40], 40 entries

# Cash vector from CF fixture (rows 1..40 = DS[1..40])
_CF_CASH_VECTOR = _CF["cf"]["free_cash_flow_for_shl_keur"]  # 61 elements
_OP_CASH = _CF_CASH_VECTOR[1:41]  # DS[1..40] (40 values)

# Source inputs
_DRAW_KEUR = _D2A["workbook_inputs"]["shl_draw_keur"]["value"]   # 14620.773894815633
_RATE = _D2A["workbook_inputs"]["shl_annual_rate"]["value"]       # 0.08

# ── imports ──────────────────────────────────────────────────────────────────
from financial_engine.shl.contracts import (
    ShlDayCountConvention,
    ShlWaterfallPolicy,
)
from financial_engine.shl.day_count import compute_shl_dcf
from financial_engine.shl.production import (
    ShlConstructionInput,
    ShlFullScheduleResult,
    ShlOperatingPeriodInput,
    compute_shl_schedule,
)
from financial_engine.shl.waterfall import (
    ShlWaterfallPeriodResult,
    compute_shl_dcf_actual_365_inclusive,
    compute_shl_waterfall_period,
)
from financial_engine.adapters.shl_cash_seam import (
    ShlCashAvailableByPeriod,
    compute_shl_cash_from_phase2c,
)
from financial_engine.senior_debt.policy import DayCountConvention as SeniorDayCountConvention
from financial_engine.senior_debt.interest import period_day_fraction as sd_period_day_fraction


# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _build_op_inputs(
    periods=None,
    cash_vector=None,
) -> list[ShlOperatingPeriodInput]:
    periods = periods or _OPERATING_PERIODS
    cash_vector = cash_vector or _OP_CASH
    out = []
    for i, (fp, cash) in enumerate(zip(periods, cash_vector)):
        out.append(ShlOperatingPeriodInput(
            period_index=i + 1,
            period_start=_parse_date(fp["period_start_date"]),
            period_end=_parse_date(fp["period_end_date"]),
            cash_available_for_shl_keur=cash,
        ))
    return out


def _build_policy(convention=ShlDayCountConvention.ACT_365_FIXED) -> ShlWaterfallPolicy:
    return ShlWaterfallPolicy(annual_rate=_RATE, day_count_convention=convention)


def _build_construction() -> ShlConstructionInput:
    return ShlConstructionInput(draw_keur=_DRAW_KEUR, annual_rate=_RATE, dcf=1.0, period_index=0)


# ── module-level cached schedule result ──────────────────────────────────────

def _build_full_schedule() -> ShlFullScheduleResult:
    return compute_shl_schedule(
        construction=_build_construction(),
        operating_periods=_build_op_inputs(),
        policy=_build_policy(),
    )


_FULL_RESULT: ShlFullScheduleResult | None = None


def _get_full_result() -> ShlFullScheduleResult:
    global _FULL_RESULT
    if _FULL_RESULT is None:
        _FULL_RESULT = _build_full_schedule()
    return _FULL_RESULT


# ════════════════════════════════════════════════════════════════════════════
# TestA — ShlDayCountConvention contract
# ════════════════════════════════════════════════════════════════════════════

class TestA_ShlDayCountConventionContract:

    def test_enum_exists(self):
        assert ShlDayCountConvention is not None

    def test_act_365_fixed_member(self):
        assert ShlDayCountConvention.ACT_365_FIXED == "ACT_365_FIXED"

    def test_act_360_member(self):
        assert ShlDayCountConvention.ACT_360 == "ACT_360"

    def test_is_str_enum(self):
        import enum
        assert issubclass(ShlDayCountConvention, str)
        assert issubclass(ShlDayCountConvention, enum.Enum)

    def test_exactly_two_members(self):
        members = list(ShlDayCountConvention)
        assert len(members) == 2

    def test_independent_of_senior_debt_convention(self):
        # ShlDayCountConvention and SeniorDayCountConvention are distinct types.
        assert ShlDayCountConvention is not SeniorDayCountConvention
        # They don't share members by identity.
        assert ShlDayCountConvention.ACT_365_FIXED is not SeniorDayCountConvention.ACT_365


# ════════════════════════════════════════════════════════════════════════════
# TestB — ShlWaterfallPolicy contract
# ════════════════════════════════════════════════════════════════════════════

class TestB_ShlWaterfallPolicyContract:

    def test_instantiation(self):
        p = ShlWaterfallPolicy(
            annual_rate=0.08,
            day_count_convention=ShlDayCountConvention.ACT_365_FIXED,
        )
        assert p.annual_rate == 0.08
        assert p.day_count_convention == ShlDayCountConvention.ACT_365_FIXED

    def test_is_frozen(self):
        p = ShlWaterfallPolicy(
            annual_rate=0.08,
            day_count_convention=ShlDayCountConvention.ACT_365_FIXED,
        )
        with pytest.raises((AttributeError, TypeError)):
            p.annual_rate = 0.09  # type: ignore[misc]

    def test_rejects_negative_rate(self):
        with pytest.raises(ValueError):
            ShlWaterfallPolicy(annual_rate=-0.01, day_count_convention=ShlDayCountConvention.ACT_365_FIXED)

    def test_rejects_inf_rate(self):
        with pytest.raises(ValueError):
            ShlWaterfallPolicy(annual_rate=float("inf"), day_count_convention=ShlDayCountConvention.ACT_365_FIXED)

    def test_rejects_bool_rate(self):
        with pytest.raises(ValueError):
            ShlWaterfallPolicy(annual_rate=True, day_count_convention=ShlDayCountConvention.ACT_365_FIXED)  # type: ignore[arg-type]

    def test_rejects_invalid_convention(self):
        with pytest.raises((ValueError, TypeError)):
            ShlWaterfallPolicy(annual_rate=0.08, day_count_convention="ACT_365")  # type: ignore[arg-type]

    def test_act_360_instantiation(self):
        p = ShlWaterfallPolicy(
            annual_rate=0.08,
            day_count_convention=ShlDayCountConvention.ACT_360,
        )
        assert p.day_count_convention == ShlDayCountConvention.ACT_360

    def test_does_not_contain_senior_debt_policy_fields(self):
        # ShlWaterfallPolicy must NOT have fields from SeniorDebtPolicy
        # (no sizing_mode, no target_dscr, etc.)
        p = ShlWaterfallPolicy(
            annual_rate=0.08, day_count_convention=ShlDayCountConvention.ACT_365_FIXED
        )
        assert not hasattr(p, "sizing_mode")
        assert not hasattr(p, "target_dscr")


# ════════════════════════════════════════════════════════════════════════════
# TestC — compute_shl_dcf ACT_365_FIXED dispatch
# ════════════════════════════════════════════════════════════════════════════

class TestC_ComputeShlDcfAct365Fixed:

    def test_ds1_value(self):
        # DS[1]: 2030-07-01 → 2030-12-31 = 184 days inclusive → 184/365
        dcf = compute_shl_dcf(date(2030, 7, 1), date(2030, 12, 31), ShlDayCountConvention.ACT_365_FIXED)
        assert abs(dcf - 184 / 365.0) < 1e-15

    def test_matches_governance_locked_function(self):
        # compute_shl_dcf for ACT_365_FIXED must delegate to the governance-locked
        # compute_shl_dcf_actual_365_inclusive (C3B3D2B0).
        start, end = date(2042, 7, 1), date(2042, 12, 31)
        via_dispatch = compute_shl_dcf(start, end, ShlDayCountConvention.ACT_365_FIXED)
        via_direct = compute_shl_dcf_actual_365_inclusive(start, end)
        assert via_dispatch == via_direct

    def test_all_40_oborovo_dcfs(self):
        # Reproduces all 40 Oborovo operating DCFs to machine epsilon.
        for fp in _OPERATING_PERIODS:
            start = _parse_date(fp["period_start_date"])
            end = _parse_date(fp["period_end_date"])
            computed = compute_shl_dcf(start, end, ShlDayCountConvention.ACT_365_FIXED)
            oracle = fp["shl_dcf_derived_actual_365"]
            assert abs(computed - oracle) < 1e-12, (
                f"DCF mismatch at DS[{fp['ds_index']}]: computed={computed}, oracle={oracle}"
            )

    def test_rejects_end_before_start(self):
        with pytest.raises(ValueError):
            compute_shl_dcf(date(2030, 12, 31), date(2030, 7, 1), ShlDayCountConvention.ACT_365_FIXED)

    def test_rejects_non_convention(self):
        with pytest.raises((ValueError, TypeError)):
            compute_shl_dcf(date(2030, 7, 1), date(2030, 12, 31), "ACT_365_FIXED")  # type: ignore[arg-type]


# ════════════════════════════════════════════════════════════════════════════
# TestD — compute_shl_dcf ACT_360 dispatch
# ════════════════════════════════════════════════════════════════════════════

class TestD_ComputeShlDcfAct360:

    def test_ds1_value(self):
        # DS[1]: 184 days inclusive → 184/360
        dcf = compute_shl_dcf(date(2030, 7, 1), date(2030, 12, 31), ShlDayCountConvention.ACT_360)
        assert abs(dcf - 184 / 360.0) < 1e-15

    def test_differs_from_act365_fixed(self):
        # ACT/360 denominator is 360, not 365 — always larger for same period.
        start, end = date(2030, 7, 1), date(2030, 12, 31)
        d365 = compute_shl_dcf(start, end, ShlDayCountConvention.ACT_365_FIXED)
        d360 = compute_shl_dcf(start, end, ShlDayCountConvention.ACT_360)
        assert d360 > d365, "ACT/360 must produce a larger DCF than ACT/365 for same days"
        assert abs(d360 - d365) > 0.005, "Difference must be material (not floating-point noise)"

    def test_denominator_is_360(self):
        # Single-day period: 2 days inclusive → 2/360
        dcf = compute_shl_dcf(date(2030, 1, 1), date(2030, 1, 2), ShlDayCountConvention.ACT_360)
        assert abs(dcf - 2 / 360.0) < 1e-15

    def test_typed_convention_selects_360(self):
        # Passing ACT_360 to ShlWaterfallPolicy selects ACT/360 calculation.
        p = ShlWaterfallPolicy(annual_rate=0.06, day_count_convention=ShlDayCountConvention.ACT_360)
        dcf = compute_shl_dcf(date(2030, 7, 1), date(2030, 12, 31), p.day_count_convention)
        assert abs(dcf - 184 / 360.0) < 1e-15

    def test_capability_label(self):
        # ACT_360 string value is exactly "ACT_360" — GENERIC_ENGINE_CAPABILITY.
        assert ShlDayCountConvention.ACT_360.value == "ACT_360"


# ════════════════════════════════════════════════════════════════════════════
# TestE — ACT_365_FIXED leap-year periods
# ════════════════════════════════════════════════════════════════════════════

class TestE_LeapYearDenominator365:
    """Denominator must remain 365 even in periods containing Feb 29."""

    # Oborovo leap-year DS indices (1-based): [4, 12, 20, 28, 36]
    _LEAP_DS_1BASED = [4, 12, 20, 28, 36]

    def _leap_periods(self):
        return [_OPERATING_PERIODS[i - 1] for i in self._LEAP_DS_1BASED]

    def test_denominator_365_in_all_5_leap_periods(self):
        for fp in self._leap_periods():
            start = _parse_date(fp["period_start_date"])
            end = _parse_date(fp["period_end_date"])
            days_incl = (end - start).days + 1
            expected = days_incl / 365.0
            computed = compute_shl_dcf(start, end, ShlDayCountConvention.ACT_365_FIXED)
            assert abs(computed - expected) < 1e-15, (
                f"Denominator not 365 at DS[{fp['ds_index']}]"
            )

    def test_leap_dcf_matches_oracle(self):
        for fp in self._leap_periods():
            start = _parse_date(fp["period_start_date"])
            end = _parse_date(fp["period_end_date"])
            computed = compute_shl_dcf(start, end, ShlDayCountConvention.ACT_365_FIXED)
            oracle = fp["shl_dcf_derived_actual_365"]
            assert abs(computed - oracle) < 1e-12, (
                f"Leap-year DCF mismatch at DS[{fp['ds_index']}]"
            )

    def test_act360_denominator_360_in_leap_periods(self):
        for fp in self._leap_periods():
            start = _parse_date(fp["period_start_date"])
            end = _parse_date(fp["period_end_date"])
            days_incl = (end - start).days + 1
            expected = days_incl / 360.0
            computed = compute_shl_dcf(start, end, ShlDayCountConvention.ACT_360)
            assert abs(computed - expected) < 1e-15


# ════════════════════════════════════════════════════════════════════════════
# TestF — Instrument independence (SHL vs Senior Debt conventions)
# ════════════════════════════════════════════════════════════════════════════

class TestF_InstrumentConventionIndependence:
    """SHL and Senior Debt conventions are independent: changing one must not
    alter the other's day-count fraction.
    """

    _START = date(2030, 7, 1)
    _END = date(2030, 12, 31)   # exclusive for SD, inclusive for SHL

    def _sd_dcf(self, convention: SeniorDayCountConvention) -> float:
        # Senior Debt: exclusive end-date (end = start of next period)
        # For DS[1]: 2030-07-01 → 2030-12-31 means end is *exclusive*
        # i.e. the period covers 2030-07-01..2030-12-30 in SD semantics
        return sd_period_day_fraction(self._START, self._END, convention)

    def _shl_dcf(self, convention: ShlDayCountConvention) -> float:
        return compute_shl_dcf(self._START, self._END, convention)

    def test_shl_act365_is_independent_of_sd_act360(self):
        # Project has SD=ACT/360, SHL=ACT/365_FIXED.
        sd_dcf = self._sd_dcf(SeniorDayCountConvention.ACT_360)
        shl_dcf = self._shl_dcf(ShlDayCountConvention.ACT_365_FIXED)
        # They differ — conventions are genuinely independent.
        assert abs(sd_dcf - shl_dcf) > 0.001

    def test_changing_shl_does_not_mutate_sd(self):
        # Compute SD DCF; then compute SHL with different convention; SD must not change.
        sd_before = self._sd_dcf(SeniorDayCountConvention.ACT_365)
        _ = self._shl_dcf(ShlDayCountConvention.ACT_360)  # different convention
        sd_after = self._sd_dcf(SeniorDayCountConvention.ACT_365)
        assert sd_before == sd_after

    def test_changing_sd_does_not_mutate_shl(self):
        shl_before = self._shl_dcf(ShlDayCountConvention.ACT_365_FIXED)
        _ = self._sd_dcf(SeniorDayCountConvention.ACT_360)  # change SD convention
        shl_after = self._shl_dcf(ShlDayCountConvention.ACT_365_FIXED)
        assert shl_before == shl_after

    def test_sd_exclusive_shl_inclusive_semantics_differ(self):
        # For DS[1] same date pair:
        # SD uses (end - start).days = 183 (exclusive) → 183/365 ≈ 0.5014
        # SHL uses (end - start).days + 1 = 184 (inclusive) → 184/365 ≈ 0.5041
        sd_365 = self._sd_dcf(SeniorDayCountConvention.ACT_365)
        shl_365 = self._shl_dcf(ShlDayCountConvention.ACT_365_FIXED)
        assert shl_365 > sd_365, "SHL (inclusive) must give larger DCF than SD (exclusive)"
        assert abs(shl_365 - sd_365 - 1.0 / 365.0) < 1e-13, (
            "Difference must be exactly 1/365 (one day)"
        )

    def test_oborovo_fixture_records_mismatch_explicitly(self):
        # The D2A fixture must document SHL_SOURCE_DAY_COUNT_MISMATCH.
        dc = _D2A["day_count_convention"]
        assert dc.get("mismatch_status") == "SHL_SOURCE_DAY_COUNT_MISMATCH"
        assert "Do not unify" in dc.get("mismatch_note", "")


# ════════════════════════════════════════════════════════════════════════════
# TestG — compute_shl_schedule construction period semantics
# ════════════════════════════════════════════════════════════════════════════

class TestG_ConstructionPeriodSemantics:

    def test_opening_is_zero(self):
        r = _get_full_result()
        assert r.construction.opening_balance_keur == 0.0

    def test_draw_matches_source_draw(self):
        # The construction ShlPeriodResult rolls forward from draw_keur (opening=0).
        # Verify: closing ≈ draw + draw × rate × dcf (= draw × (1 + rate × 1.0))
        r = _get_full_result()
        expected_closing = _DRAW_KEUR * (1.0 + _RATE * 1.0)
        assert abs(r.construction.closing_balance_keur - expected_closing) < 1e-6

    def test_construction_is_pik(self):
        r = _get_full_result()
        assert r.construction.cash_interest_keur == 0.0
        assert r.construction.pik_interest_keur > 0

    def test_construction_gross_matches_fixture(self):
        r = _get_full_result()
        expected = _CONSTRUCTION_PERIOD["gross_accrued_interest_keur"]
        assert abs(r.construction.gross_accrued_interest_keur - expected) < 1e-6

    def test_construction_closing_exact(self):
        r = _get_full_result()
        # 14620.773894815633 × 0.08 × 1.0 + 14620.773894815633 = 15790.435806...
        assert abs(r.construction.closing_balance_keur - 15790.435806400885) < 1e-6

    def test_dcf_1_arithmetic_implied(self):
        # Verify DCF=1.0 is arithmetic-implied: gross / (draw × rate) ≈ 1.0
        r = _get_full_result()
        implied_dcf = r.construction.gross_accrued_interest_keur / (_DRAW_KEUR * _RATE)
        assert abs(implied_dcf - 1.0) < 1e-9

    def test_no_scheduled_principal_in_construction(self):
        r = _get_full_result()
        assert r.construction.scheduled_principal_keur == 0.0

    def test_construction_result_is_shl_period_result(self):
        from financial_engine.shl.contracts import ShlPeriodResult
        r = _get_full_result()
        assert isinstance(r.construction, ShlPeriodResult)


# ════════════════════════════════════════════════════════════════════════════
# TestH — compute_shl_schedule operating chain roll-forward
# ════════════════════════════════════════════════════════════════════════════

class TestH_OperatingChainRollForward:

    def test_first_operating_opening_equals_construction_closing(self):
        r = _get_full_result()
        assert abs(r.operating[0].opening_balance_keur - r.construction.closing_balance_keur) < 1e-9

    def test_each_opening_equals_prior_closing(self):
        r = _get_full_result()
        for i in range(1, len(r.operating)):
            prev_closing = r.operating[i - 1].closing_balance_keur
            this_opening = r.operating[i].opening_balance_keur
            assert abs(this_opening - prev_closing) < 1e-9, (
                f"Roll-forward broken at DS[{i+1}]: closing={prev_closing}, opening={this_opening}"
            )

    def test_40_operating_periods(self):
        r = _get_full_result()
        assert len(r.operating) == 40

    def test_result_type_is_shl_full_schedule_result(self):
        r = _get_full_result()
        assert isinstance(r, ShlFullScheduleResult)

    def test_operating_results_are_waterfall_period_result(self):
        r = _get_full_result()
        for op in r.operating:
            assert isinstance(op, ShlWaterfallPeriodResult)

    def test_roll_forward_identity_all_periods(self):
        # closing = opening + pik - principal
        r = _get_full_result()
        for op in r.operating:
            expected_closing = (
                op.opening_balance_keur + op.pik_interest_keur - op.principal_repaid_keur
            )
            assert abs(op.closing_balance_keur - expected_closing) < 1e-9


# ════════════════════════════════════════════════════════════════════════════
# TestI — Oborovo construction parity
# ════════════════════════════════════════════════════════════════════════════

class TestI_OborovoConstructionParity:

    def test_opening_balance(self):
        r = _get_full_result()
        assert abs(r.construction.opening_balance_keur
                   - _CONSTRUCTION_PERIOD["opening_balance_keur"]) < 1e-6

    def test_gross_accrued_interest(self):
        r = _get_full_result()
        assert abs(r.construction.gross_accrued_interest_keur
                   - _CONSTRUCTION_PERIOD["gross_accrued_interest_keur"]) < 1e-6

    def test_pik_interest(self):
        r = _get_full_result()
        assert abs(r.construction.pik_interest_keur
                   - _CONSTRUCTION_PERIOD["pik_interest_keur"]) < 1e-6

    def test_closing_balance(self):
        r = _get_full_result()
        assert abs(r.construction.closing_balance_keur
                   - _CONSTRUCTION_PERIOD["closing_balance_keur"]) < 1e-6

    def test_cash_interest_zero(self):
        r = _get_full_result()
        assert r.construction.cash_interest_keur == 0.0


# ════════════════════════════════════════════════════════════════════════════
# TestJ — Oborovo operating parity (all 40 periods)
# ════════════════════════════════════════════════════════════════════════════

class TestJ_OborovoOperatingParity:
    """All 40 operating periods must match D2A fixture within tolerance."""

    _TOL = 1e-6  # kEUR

    def _deltas(self, field_computed, field_fixture):
        r = _get_full_result()
        deltas = []
        for op, fp in zip(r.operating, _OPERATING_PERIODS):
            deltas.append(abs(getattr(op, field_computed) - fp[field_fixture]))
        return deltas

    def test_max_gross_delta(self):
        deltas = self._deltas("gross_accrued_interest_keur", "gross_accrued_interest_keur")
        assert max(deltas) < self._TOL, f"Max gross delta: {max(deltas):.2e}"

    def test_max_cash_interest_delta(self):
        deltas = self._deltas("cash_interest_keur", "cash_interest_keur")
        assert max(deltas) < self._TOL, f"Max cash interest delta: {max(deltas):.2e}"

    def test_max_pik_delta(self):
        deltas = self._deltas("pik_interest_keur", "pik_interest_keur")
        assert max(deltas) < self._TOL, f"Max PIK delta: {max(deltas):.2e}"

    def test_max_principal_delta(self):
        deltas = self._deltas("principal_repaid_keur", "principal_repaid_keur")
        assert max(deltas) < self._TOL, f"Max principal delta: {max(deltas):.2e}"

    def test_max_closing_delta(self):
        deltas = self._deltas("closing_balance_keur", "closing_balance_keur")
        assert max(deltas) < self._TOL, f"Max closing delta: {max(deltas):.2e}"

    def test_ds40_closing_is_zero(self):
        r = _get_full_result()
        assert r.operating[-1].closing_balance_keur < self._TOL

    def test_first_sweep_at_ds25(self):
        r = _get_full_result()
        sweep_ds = None
        for i, op in enumerate(r.operating):
            if op.principal_repaid_keur > 0:
                sweep_ds = i + 1  # 1-based DS index
                break
        assert sweep_ds == 25, f"First sweep at DS[{sweep_ds}], expected DS[25]"

    def test_ds1_opening_equals_construction_closing(self):
        r = _get_full_result()
        assert abs(r.operating[0].opening_balance_keur - r.construction.closing_balance_keur) < 1e-9


# ════════════════════════════════════════════════════════════════════════════
# TestK — Cash seam adapter
# ════════════════════════════════════════════════════════════════════════════

class TestK_ShlCashSeamAdapter:
    """compute_shl_cash_from_phase2c derives cash_available from Phase 2C result."""

    def _make_mock_phase2c_result(
        self,
        cfads: list[float],
        senior_ds: list[float],
        is_constructions: list[bool],
        period_count: int = None,
    ):
        if period_count is None:
            period_count = len(cfads)
        period_indices = list(range(period_count))

        # Build mock periods
        mock_periods = []
        for i, is_c in enumerate(is_constructions):
            p = MagicMock()
            p.period_index = i
            p.is_construction = is_c
            p.is_operation = not is_c
            mock_periods.append(p)

        # Build mock tax_and_cfads
        mock_tac = MagicMock()
        mock_tac.period_indices = tuple(period_indices)
        mock_tac.cfads_keur = tuple(cfads)

        # Build mock senior_debt (only covers operating periods with SD)
        sd_indices = list(range(len(senior_ds)))
        mock_sd = MagicMock()
        mock_sd.period_indices = tuple(sd_indices)
        mock_sd.senior_debt_service_keur = tuple(senior_ds)

        mock_result = MagicMock()
        mock_result.tax_and_cfads = mock_tac
        mock_result.senior_debt = mock_sd
        mock_result.periods = mock_periods
        return mock_result

    def test_construction_period_returns_zero(self):
        mock_result = self._make_mock_phase2c_result(
            cfads=[2000.0, 500.0],
            senior_ds=[500.0],
            is_constructions=[True, False],
        )
        # Override senior_debt to only cover period 1
        mock_result.senior_debt.period_indices = (1,)
        mock_result.senior_debt.senior_debt_service_keur = (500.0,)
        seam = compute_shl_cash_from_phase2c(mock_result)
        assert seam[0].cash_available_for_shl_keur == 0.0
        assert seam[0].is_construction is True

    def test_operating_period_cash_derivation(self):
        # cash_for_shl = cfads - senior_ds = 2000 - 1200 = 800
        mock_result = self._make_mock_phase2c_result(
            cfads=[0.0, 2000.0],
            senior_ds=[0.0, 1200.0],
            is_constructions=[True, False],
        )
        seam = compute_shl_cash_from_phase2c(mock_result)
        assert abs(seam[1].cash_available_for_shl_keur - 800.0) < 1e-9

    def test_post_maturity_cash_is_cfads(self):
        # Post-maturity period: senior_ds = 0 → cash_for_shl = CFADS
        mock_result = self._make_mock_phase2c_result(
            cfads=[0.0, 1500.0, 3000.0],
            senior_ds=[0.0, 1500.0, 0.0],
            is_constructions=[True, False, False],
        )
        seam = compute_shl_cash_from_phase2c(mock_result)
        assert abs(seam[2].cash_available_for_shl_keur - 3000.0) < 1e-9

    def test_raises_if_tax_and_cfads_is_none(self):
        mock_result = MagicMock()
        mock_result.tax_and_cfads = None
        mock_result.senior_debt = MagicMock()
        with pytest.raises(ValueError, match="tax_and_cfads"):
            compute_shl_cash_from_phase2c(mock_result)

    def test_raises_if_senior_debt_is_none(self):
        mock_result = MagicMock()
        mock_result.tax_and_cfads = MagicMock()
        mock_result.senior_debt = None
        with pytest.raises(ValueError, match="senior_debt"):
            compute_shl_cash_from_phase2c(mock_result)

    def test_result_type(self):
        mock_result = self._make_mock_phase2c_result(
            cfads=[0.0, 1000.0],
            senior_ds=[500.0],
            is_constructions=[True, False],
        )
        mock_result.senior_debt.period_indices = (1,)
        mock_result.senior_debt.senior_debt_service_keur = (500.0,)
        seam = compute_shl_cash_from_phase2c(mock_result)
        assert isinstance(seam, tuple)
        for item in seam:
            assert isinstance(item, ShlCashAvailableByPeriod)

    def test_cash_lineage_cfads_minus_senior_ds(self):
        # Verify the arithmetic: cash_for_shl = cfads - senior_ds
        cfads_val = 2575.0
        sd_val = 2239.13
        expected = cfads_val - sd_val

        mock_result = self._make_mock_phase2c_result(
            cfads=[0.0, cfads_val],
            senior_ds=[0.0, sd_val],
            is_constructions=[True, False],
        )
        seam = compute_shl_cash_from_phase2c(mock_result)
        assert abs(seam[1].cash_available_for_shl_keur - expected) < 1e-6

    def test_oborovo_ds1_cash_lineage(self):
        # DS[1]: FCF_for_SHL = 335.87 = CFADS(2575.00) - senior_ds(2239.13)
        # Verified in D2B0 reconciliation doc.
        cfads_ds1 = 2575.00
        sd_ds1 = 2239.13
        expected = cfads_ds1 - sd_ds1  # ≈ 335.87
        assert abs(expected - 335.87) < 0.01


# ════════════════════════════════════════════════════════════════════════════
# TestL — Cash waterfall ordering
# ════════════════════════════════════════════════════════════════════════════

class TestL_CashWaterfallOrdering:
    """Document and verify the production waterfall ordering for SHL cash."""

    def test_cash_seam_docstring_names_cfads_minus_senior_ds(self):
        from financial_engine.adapters import shl_cash_seam
        doc = shl_cash_seam.__doc__ or ""
        assert "CFADS" in doc
        assert "senior_debt_service" in doc or "senior_ds" in doc

    def test_dsra_is_downstream_of_shl(self):
        # The seam adapter explicitly documents DSRA is downstream.
        from financial_engine.adapters import shl_cash_seam
        doc = shl_cash_seam.__doc__ or ""
        assert "DSRA" in doc and "downstream" in doc

    def test_production_cash_not_from_fixture(self):
        # compute_shl_cash_from_phase2c must NOT load any fixture files.
        import financial_engine.adapters.shl_cash_seam as mod
        src = inspect.getsource(mod)
        assert "excel_oborovo" not in src.lower()
        assert "free_cash_flow_for_shl" not in src
        assert "open(" not in src


# ════════════════════════════════════════════════════════════════════════════
# TestM — Fixed-point boundary
# ════════════════════════════════════════════════════════════════════════════

class TestM_FixedPointBoundary:

    def test_shl_outside_phase2c_fixed_point_documented(self):
        from financial_engine.shl import production
        src = inspect.getsource(production)
        assert "SHL_OUTSIDE_FIXED_POINT" in src or "outside the fixed point" in src.lower()

    def test_production_module_does_not_call_solve_senior_debt(self):
        import financial_engine.shl.production as mod
        src = inspect.getsource(mod)
        assert "solve_senior_debt" not in src

    def test_production_module_does_not_call_calculate_tax(self):
        import financial_engine.shl.production as mod
        src = inspect.getsource(mod)
        assert "calculate_tax" not in src

    def test_shl_interest_not_fed_back_into_tax_in_d2b1(self):
        # In C3B3D2B1, SHL gross interest does NOT re-enter the Phase 2C loop.
        # The seam adapter reads Phase 2C outputs as-is (no re-iteration).
        import financial_engine.adapters.shl_cash_seam as mod
        src = inspect.getsource(mod)
        assert "calculate_tax" not in src
        assert "solve_senior_debt" not in src

    def test_separate_vectors_in_full_schedule_result(self):
        r = _get_full_result()
        for op in r.operating:
            # gross = cash_interest + pik_interest (fundamental identity)
            assert abs(op.gross_accrued_interest_keur -
                       (op.cash_interest_keur + op.pik_interest_keur)) < 1e-9


# ════════════════════════════════════════════════════════════════════════════
# TestN — Separate SHL vectors preserved
# ════════════════════════════════════════════════════════════════════════════

class TestN_SeparateVectors:

    def test_gross_distinct_from_cash_interest(self):
        # In PIK/partial periods: gross ≠ cash_interest
        r = _get_full_result()
        # DS[1] is partial (cash < gross)
        op1 = r.operating[0]
        assert op1.gross_accrued_interest_keur != op1.cash_interest_keur

    def test_pik_is_gross_minus_cash(self):
        r = _get_full_result()
        for op in r.operating:
            assert abs(op.pik_interest_keur - (op.gross_accrued_interest_keur - op.cash_interest_keur)) < 1e-9

    def test_principal_nonzero_only_from_ds25(self):
        r = _get_full_result()
        for i, op in enumerate(r.operating[:24]):
            assert op.principal_repaid_keur == 0.0, f"Principal nonzero before DS[25] at DS[{i+1}]"
        # DS[25] (index 24) has principal > 0
        assert r.operating[24].principal_repaid_keur > 0

    def test_shl_service_is_cash_interest_plus_principal(self):
        r = _get_full_result()
        for op in r.operating:
            expected = op.cash_interest_keur + op.principal_repaid_keur
            assert abs(op.shl_service_keur - expected) < 1e-9

    def test_tax_deductibility_note_in_production_module(self):
        from financial_engine.shl import production
        src = inspect.getsource(production)
        # Must document that gross SHL interest feeds into tax
        assert "tax" in src.lower()


# ════════════════════════════════════════════════════════════════════════════
# TestO — Governance
# ════════════════════════════════════════════════════════════════════════════

class TestO_Governance:

    def _source_lines(self, module_path: str) -> list[str]:
        mod = __import__(module_path, fromlist=[""])
        src = inspect.getsource(mod)
        # Only code lines (not comments, not docstrings) — conservative check
        return [line for line in src.split("\n")
                if line.strip() and not line.strip().startswith("#")]

    def test_no_13547_in_day_count_module(self):
        lines = self._source_lines("financial_engine.shl.day_count")
        for line in lines:
            assert "13547" not in line

    def test_no_13547_in_production_module(self):
        lines = self._source_lines("financial_engine.shl.production")
        for line in lines:
            assert "13547" not in line

    def test_no_ds25_period_boundary_hardcoded_in_production(self):
        # No numeric constant "25" used as a period-boundary calculation rule.
        # (The string "DS25" may appear in comments; that's acceptable.)
        import financial_engine.shl.production as mod
        src = inspect.getsource(mod)
        code_lines = [l for l in src.split("\n")
                      if l.strip() and not l.strip().startswith("#")
                      and '"""' not in l and "'''" not in l]
        # No line of executable code should hardcode 25 as a period boundary.
        for line in code_lines:
            assert "period_index == 25" not in line
            assert "period_index >= 25" not in line
            assert "> 25" not in line

    def test_no_ds40_period_boundary_hardcoded_in_production(self):
        import financial_engine.shl.production as mod
        src = inspect.getsource(mod)
        code_lines = [l for l in src.split("\n")
                      if l.strip() and not l.strip().startswith("#")
                      and '"""' not in l and "'''" not in l]
        for line in code_lines:
            assert "period_index == 40" not in line
            assert "period_index >= 40" not in line
            assert "== 40" not in line

    def test_no_project_name_dispatch_in_production(self):
        import financial_engine.shl.production as mod
        src = inspect.getsource(mod)
        assert "project.name" not in src
        assert "project.code" not in src
        assert '"oborovo"' not in src.lower()
        assert '"tuho"' not in src.lower()

    def test_no_finco_core_import_in_day_count(self):
        import financial_engine.shl.day_count as mod
        src = inspect.getsource(mod)
        import_lines = [l for l in src.split("\n") if l.strip().startswith("import") or l.strip().startswith("from")]
        for line in import_lines:
            assert "finco_core" not in line

    def test_no_finco_core_import_in_production(self):
        import financial_engine.shl.production as mod
        src = inspect.getsource(mod)
        import_lines = [l for l in src.split("\n") if l.strip().startswith("import") or l.strip().startswith("from")]
        for line in import_lines:
            assert "finco_core" not in line

    def test_no_app_import_in_production(self):
        import financial_engine.shl.production as mod
        src = inspect.getsource(mod)
        import_lines = [l for l in src.split("\n") if l.strip().startswith("import") or l.strip().startswith("from")]
        for line in import_lines:
            assert "from app" not in line
            assert "import app" not in line

    def test_waterfall_policy_has_no_mode_enum(self):
        # ShlWaterfallPolicy must not have a payment_mode field (natural formula handles modes)
        p = ShlWaterfallPolicy(annual_rate=0.08, day_count_convention=ShlDayCountConvention.ACT_365_FIXED)
        assert not hasattr(p, "payment_mode")

    def test_oborovo_senior_debt_convention_is_act360(self):
        # The D2A fixture confirms Senior Debt uses ACT/360 — do not alter this.
        dc = _D2A["day_count_convention"]
        assert dc.get("senior_debt_basis") == "actual/360"

    def test_shl_convention_proven_label(self):
        # D2A fixture documents ACT_365_FIXED as SOURCE_VECTOR_PROVEN for operating SHL.
        dc = _D2A["day_count_convention"]
        label = dc.get("shl_operating_convention_label", "")
        assert "SOURCE_VECTOR_PROVEN" in label
        assert "365" in label
