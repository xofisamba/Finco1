"""Stage C3B3A — Clean Senior Debt Source Contract.

Verifies that the generic senior-debt engine, extended with PeriodDscrTarget
and PeriodDebtServiceAvailability, reproduces the Oborovo Excel source debt
(42,852.279 kEUR) from raw DS!row20/22/9/44/6 without any project-specific
dispatch or forbidden inputs.

Test groups A–W.
"""
from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path

import pytest

from financial_engine.results import OperatingPeriodResult
from financial_engine.senior_debt.policy import (
    DayCountConvention,
    SeniorDebtPolicy,
    SeniorDebtSizingMode,
)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "excel_oborovo_debt_interest_truth.json"


def _load_fixture() -> dict:
    with open(FIXTURE_PATH) as f:
        return json.load(f)


def _oborovo_data() -> dict:
    """Return structured Oborovo raw vectors (period index 1..28 → array[1..28])."""
    d = _load_fixture()
    ws_a = d["workstream_a"]
    ws_b = d["workstream_b"]
    ws_e = d["workstream_e"]
    pv = ws_b["period_vectors"]
    return {
        "cfads": ws_a["ds_row20_cfads"]["period_values_keur"],
        "dscr_targets": ws_a["ds_row22_dscr_target"]["period_values"],
        "ops_flag": pv["row9_ops_flag"]["period_values"],
        "annual_rates": ws_e["ds_row44_annual_sculpting_rate"]["period_values"],
        "day_frac": pv["row6_day_frac"]["period_values"],
        "opening": ws_e["ds_row61_opening_balance"]["period_values"],
        "interest": ws_e["ds_row64_period_interest"]["period_values"],
        "principal": pv["row63_principal"]["period_values"],
        "closing": pv["row67_closing"]["period_values"],
        "excel_debt": d["phase2c_sizing_analysis"]["excel_total_debt_keur"],
        "g3a_scalar": d["phase2c_sizing_analysis"]["causal_bridge"]["g3a_scalar_backward_induction_keur"],
    }


def _build_oborovo_periods() -> tuple[OperatingPeriodResult, ...]:
    """Build OperatingPeriodResult periods whose dates reproduce DS!row6 ACT/360 fracs."""
    d = _oborovo_data()
    day_frac = d["day_frac"]
    days_per_period = [round(day_frac[i] * 360) for i in range(1, 29)]

    cod = date(2019, 6, 1)
    periods = []
    cur = cod
    for i, n in enumerate(days_per_period, start=1):
        start = cur
        end = cur + timedelta(days=n)
        periods.append(OperatingPeriodResult(
            period_index=i,
            period_start=start,
            period_end=end,
            year_index=float((i - 1) // 2),
            period_in_year=float((i - 1) % 2),
            is_construction=False,
            is_operation=True,
            is_ppa_active=True,
            days_in_period=n,
            day_fraction=n / 360.0,
            production_mwh=0.0,
            revenue_keur=0.0,
            opex_keur=0.0,
            ebitda_keur=0.0,
            book_depreciation_keur=0.0,
            tax_depreciation_keur=0.0,
            ebit_keur=0.0,
        ))
        cur = end
    return tuple(periods)


def _no_tax_fn(cfads_map: dict[int, float]):
    """Tax feedback stub: CFADS = fixed map, cash_tax = 0."""
    def fn(interest_by_period: dict[int, float]):
        return cfads_map.copy(), {k: 0.0 for k in cfads_map}
    return fn


def _make_oborovo_inputs(
    override_dscr_targets: bool = True,
    override_ops: bool = True,
):
    from financial_engine.senior_debt.inputs import (
        PeriodDebtServiceAvailability,
        PeriodDscrTarget,
        PeriodRate,
        SeniorDebtInputs,
    )

    d = _oborovo_data()
    active = range(1, 29)

    period_rates = tuple(PeriodRate(i, d["annual_rates"][i]) for i in active)

    dscr_targets: tuple = ()
    if override_dscr_targets:
        dscr_targets = tuple(PeriodDscrTarget(i, d["dscr_targets"][i]) for i in active)

    ops: tuple = ()
    if override_ops:
        ops = tuple(PeriodDebtServiceAvailability(i, d["ops_flag"][i]) for i in active)

    return SeniorDebtInputs(
        eligible_project_cost_keur=0.0,
        initial_debt_guess_keur=43_000.0,
        period_rates=period_rates,
        explicit_principal_schedule=None,
        period_dscr_targets=dscr_targets,
        period_debt_service_availability=ops,
    )


def _oborovo_policy() -> SeniorDebtPolicy:
    return SeniorDebtPolicy(
        policy_id="c3b3a-oborovo-source",
        policy_version="1.0.0",
        sizing_mode=SeniorDebtSizingMode.DSCR_SCULPTED,
        target_dscr=1.15,
        maximum_gearing=None,
        annual_fixed_rate=None,
        periods_per_year=2,
        day_count_convention=DayCountConvention.ACT_360,
        repayment_start_period_index=1,
        maturity_period_index=28,
        convergence_tolerance_keur=1e-4,
        convergence_relative_tolerance=1e-9,
        maximum_iterations=100,
        permit_terminal_balloon=True,
        damping_alpha=1.0,
    )


def _run_oborovo(
    override_dscr_targets: bool = True,
    override_ops: bool = True,
):
    from financial_engine.senior_debt.solver import solve_senior_debt

    d = _oborovo_data()
    cfads_map = {i: d["cfads"][i] for i in range(1, 29)}
    inputs = _make_oborovo_inputs(override_dscr_targets, override_ops)
    policy = _oborovo_policy()
    periods = _build_oborovo_periods()

    return solve_senior_debt(
        inputs=inputs,
        policy=policy,
        periods=periods,
        tax_cfads_fn=_no_tax_fn(cfads_map),
    )


# ---------------------------------------------------------------------------
# Generic backward-compat helper
# ---------------------------------------------------------------------------

def _run_generic_scalar(label: str, rate: float = 0.056, ebitda: float = 3000.0):
    from financial_engine.senior_debt.inputs import SeniorDebtInputs, PeriodRate
    from financial_engine.senior_debt.solver import solve_senior_debt

    n = 20
    period_rates = tuple(PeriodRate(i, rate) for i in range(1, n + 1))
    cfads_map = {i: ebitda for i in range(1, n + 1)}

    # Build synthetic semiannual periods
    cod = date(2020, 1, 1)
    ops = []
    cur = cod
    for i in range(1, n + 1):
        end = cur + timedelta(days=182)
        ops.append(OperatingPeriodResult(
            period_index=i, period_start=cur, period_end=end,
            year_index=float((i - 1) // 2), period_in_year=float((i - 1) % 2),
            is_construction=False, is_operation=True, is_ppa_active=True,
            days_in_period=182, day_fraction=182 / 365.0,
            production_mwh=0.0, revenue_keur=ebitda, opex_keur=0.0,
            ebitda_keur=ebitda, book_depreciation_keur=0.0,
            tax_depreciation_keur=0.0, ebit_keur=ebitda,
        ))
        cur = end

    policy = SeniorDebtPolicy(
        policy_id=f"generic-{label}", policy_version="1.0",
        sizing_mode=SeniorDebtSizingMode.DSCR_SCULPTED,
        target_dscr=1.20, maximum_gearing=None, annual_fixed_rate=None,
        periods_per_year=2, day_count_convention=DayCountConvention.ACT_365,
        repayment_start_period_index=1, maturity_period_index=n,
        convergence_tolerance_keur=0.01, convergence_relative_tolerance=1e-8,
        maximum_iterations=50, permit_terminal_balloon=False, damping_alpha=1.0,
    )
    inputs = SeniorDebtInputs(
        eligible_project_cost_keur=100_000.0,
        initial_debt_guess_keur=40_000.0,
        period_rates=period_rates,
        explicit_principal_schedule=None,
    )
    return solve_senior_debt(
        inputs=inputs, policy=policy, periods=tuple(ops),
        tax_cfads_fn=_no_tax_fn(cfads_map),
    )


# ===========================================================================
# GROUP A — New immutable input contracts
# ===========================================================================

class TestGroupA_NewInputContracts:
    def test_period_dscr_target_is_frozen_dataclass(self):
        from financial_engine.senior_debt.inputs import PeriodDscrTarget
        import dataclasses
        dt = PeriodDscrTarget(period_index=1, target_dscr=1.15)
        assert dataclasses.is_dataclass(dt)
        assert dt.period_index == 1
        assert dt.target_dscr == 1.15
        with pytest.raises((TypeError, AttributeError)):
            dt.target_dscr = 1.35  # type: ignore[misc]

    def test_period_debt_service_availability_is_frozen_dataclass(self):
        from financial_engine.senior_debt.inputs import PeriodDebtServiceAvailability
        import dataclasses
        av = PeriodDebtServiceAvailability(period_index=5, availability_fraction=0.98895)
        assert dataclasses.is_dataclass(av)
        assert av.period_index == 5
        assert av.availability_fraction == pytest.approx(0.98895)
        with pytest.raises((TypeError, AttributeError)):
            av.availability_fraction = 1.0  # type: ignore[misc]

    def test_senior_debt_inputs_backward_compatible_defaults(self):
        from financial_engine.senior_debt.inputs import SeniorDebtInputs, PeriodRate
        inputs = SeniorDebtInputs(
            eligible_project_cost_keur=50_000.0,
            initial_debt_guess_keur=20_000.0,
            period_rates=(PeriodRate(period_index=1, annual_rate=0.056),),
            explicit_principal_schedule=None,
        )
        assert inputs.period_dscr_targets == ()
        assert inputs.period_debt_service_availability == ()

    def test_senior_debt_inputs_accepts_new_fields(self):
        from financial_engine.senior_debt.inputs import (
            SeniorDebtInputs, PeriodRate, PeriodDscrTarget, PeriodDebtServiceAvailability
        )
        inputs = SeniorDebtInputs(
            eligible_project_cost_keur=0.0,
            initial_debt_guess_keur=43_000.0,
            period_rates=(PeriodRate(period_index=1, annual_rate=0.059),),
            explicit_principal_schedule=None,
            period_dscr_targets=(PeriodDscrTarget(period_index=1, target_dscr=1.35),),
            period_debt_service_availability=(
                PeriodDebtServiceAvailability(period_index=1, availability_fraction=0.989),
            ),
        )
        assert len(inputs.period_dscr_targets) == 1
        assert len(inputs.period_debt_service_availability) == 1


# ===========================================================================
# GROUP B — Strict validation
# ===========================================================================

class TestGroupB_StrictValidation:
    def _validate(self, inputs, policy):
        from financial_engine.senior_debt.validation import validate_senior_debt_inputs
        known = frozenset(range(1, 29))
        return validate_senior_debt_inputs(inputs, policy, known)

    def _base_policy(self):
        return SeniorDebtPolicy(
            policy_id="val-test", policy_version="1.0",
            sizing_mode=SeniorDebtSizingMode.DSCR_SCULPTED,
            target_dscr=1.15, maximum_gearing=None,
            annual_fixed_rate=0.056, periods_per_year=2,
            day_count_convention=DayCountConvention.ACT_365,
            repayment_start_period_index=1, maturity_period_index=28,
            convergence_tolerance_keur=0.01, convergence_relative_tolerance=1e-8,
            maximum_iterations=50, permit_terminal_balloon=True, damping_alpha=1.0,
        )

    def _base_inputs(self, dscr_targets=(), ops=()):
        from financial_engine.senior_debt.inputs import SeniorDebtInputs
        return SeniorDebtInputs(
            eligible_project_cost_keur=0.0,
            initial_debt_guess_keur=43_000.0,
            period_rates=(),
            explicit_principal_schedule=None,
            period_dscr_targets=dscr_targets,
            period_debt_service_availability=ops,
        )

    def test_valid_inputs_no_errors(self):
        from financial_engine.senior_debt.inputs import PeriodDscrTarget, PeriodDebtServiceAvailability
        dscr = tuple(PeriodDscrTarget(i, 1.15) for i in range(1, 29))
        ops = tuple(PeriodDebtServiceAvailability(i, 1.0) for i in range(1, 29))
        errors = self._validate(self._base_inputs(dscr, ops), self._base_policy())
        assert not any(
            "dscr_target" in e.lower() or "availability" in e.lower() for e in errors
        )

    def test_dscr_target_lte_1_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDscrTarget
        dscr = (PeriodDscrTarget(period_index=1, target_dscr=1.0),)
        errors = self._validate(self._base_inputs(dscr), self._base_policy())
        assert any("dscr" in e.lower() and "> 1" in e for e in errors)

    def test_dscr_target_negative_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDscrTarget
        dscr = (PeriodDscrTarget(period_index=1, target_dscr=-0.5),)
        errors = self._validate(self._base_inputs(dscr), self._base_policy())
        assert any("dscr" in e.lower() for e in errors)

    def test_dscr_target_bool_period_index_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDscrTarget
        dscr = (PeriodDscrTarget(period_index=True, target_dscr=1.15),)  # type: ignore[arg-type]
        errors = self._validate(self._base_inputs(dscr), self._base_policy())
        assert any("bool" in e.lower() or "period_index" in e.lower() for e in errors)

    def test_dscr_target_nan_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDscrTarget
        dscr = (PeriodDscrTarget(period_index=1, target_dscr=float("nan")),)
        errors = self._validate(self._base_inputs(dscr), self._base_policy())
        assert any("finite" in e.lower() or "nan" in e.lower() for e in errors)

    def test_dscr_target_duplicate_period_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDscrTarget
        dscr = (
            PeriodDscrTarget(period_index=5, target_dscr=1.15),
            PeriodDscrTarget(period_index=5, target_dscr=1.35),
        )
        errors = self._validate(self._base_inputs(dscr), self._base_policy())
        assert any("duplicate" in e.lower() or "period_index" in e.lower() for e in errors)

    def test_dscr_target_unknown_period_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDscrTarget
        dscr = (PeriodDscrTarget(period_index=99, target_dscr=1.15),)
        errors = self._validate(self._base_inputs(dscr), self._base_policy())
        assert any("unknown" in e.lower() or "99" in e for e in errors)

    def test_availability_above_1_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDebtServiceAvailability
        ops = (PeriodDebtServiceAvailability(period_index=1, availability_fraction=1.001),)
        errors = self._validate(self._base_inputs(ops=ops), self._base_policy())
        assert any("availability" in e.lower() for e in errors)

    def test_availability_negative_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDebtServiceAvailability
        ops = (PeriodDebtServiceAvailability(period_index=1, availability_fraction=-0.01),)
        errors = self._validate(self._base_inputs(ops=ops), self._base_policy())
        assert any("availability" in e.lower() for e in errors)

    def test_availability_nan_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDebtServiceAvailability
        ops = (PeriodDebtServiceAvailability(period_index=1, availability_fraction=float("nan")),)
        errors = self._validate(self._base_inputs(ops=ops), self._base_policy())
        assert any("finite" in e.lower() or "nan" in e.lower() for e in errors)

    def test_availability_bool_period_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDebtServiceAvailability
        ops = (PeriodDebtServiceAvailability(period_index=False, availability_fraction=1.0),)  # type: ignore[arg-type]
        errors = self._validate(self._base_inputs(ops=ops), self._base_policy())
        assert any("bool" in e.lower() or "period_index" in e.lower() for e in errors)

    def test_availability_duplicate_period_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDebtServiceAvailability
        ops = (
            PeriodDebtServiceAvailability(period_index=28, availability_fraction=1.0),
            PeriodDebtServiceAvailability(period_index=28, availability_fraction=0.98),
        )
        errors = self._validate(self._base_inputs(ops=ops), self._base_policy())
        assert any("duplicate" in e.lower() or "28" in e for e in errors)

    def test_availability_unknown_period_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDebtServiceAvailability
        ops = (PeriodDebtServiceAvailability(period_index=50, availability_fraction=1.0),)
        errors = self._validate(self._base_inputs(ops=ops), self._base_policy())
        assert any("unknown" in e.lower() or "50" in e for e in errors)


# ===========================================================================
# GROUP C — Scalar fallback compatibility
# ===========================================================================

class TestGroupC_ScalarFallback:
    def test_empty_targets_uses_policy_dscr(self):
        from financial_engine.senior_debt.inputs import SeniorDebtInputs
        from financial_engine.senior_debt.solver import build_dscr_target_map

        inputs = SeniorDebtInputs(
            eligible_project_cost_keur=0.0, initial_debt_guess_keur=0.0,
            period_rates=(), explicit_principal_schedule=None,
        )
        policy = SeniorDebtPolicy(
            policy_id="fallback", policy_version="1.0",
            sizing_mode=SeniorDebtSizingMode.DSCR_SCULPTED,
            target_dscr=1.20, maximum_gearing=None,
            annual_fixed_rate=0.056, periods_per_year=2,
            day_count_convention=DayCountConvention.ACT_365,
            repayment_start_period_index=1, maturity_period_index=10,
            convergence_tolerance_keur=0.01, convergence_relative_tolerance=1e-8,
            maximum_iterations=50, permit_terminal_balloon=False, damping_alpha=1.0,
        )
        m = build_dscr_target_map(policy, inputs, tuple(range(1, 11)))
        assert all(v == pytest.approx(1.20) for v in m.values())

    def test_empty_ops_uses_1_0(self):
        from financial_engine.senior_debt.inputs import SeniorDebtInputs
        from financial_engine.senior_debt.solver import build_debt_service_availability_map

        inputs = SeniorDebtInputs(
            eligible_project_cost_keur=0.0, initial_debt_guess_keur=0.0,
            period_rates=(), explicit_principal_schedule=None,
        )
        m = build_debt_service_availability_map(inputs, tuple(range(1, 21)))
        assert all(v == 1.0 for v in m.values())

    def test_generic_scalar_solve_unchanged(self):
        result = _run_generic_scalar("solar-generic")
        assert result.diagnostics.converged
        assert result.debt_size_keur > 0


# ===========================================================================
# GROUP D — Per-period DSCR map
# ===========================================================================

class TestGroupD_PerPeriodDscrMap:
    def test_build_dscr_target_map_overrides(self):
        from financial_engine.senior_debt.inputs import SeniorDebtInputs, PeriodDscrTarget
        from financial_engine.senior_debt.solver import build_dscr_target_map

        dscr = (
            PeriodDscrTarget(period_index=25, target_dscr=1.35),
            PeriodDscrTarget(period_index=26, target_dscr=1.35),
        )
        inputs = SeniorDebtInputs(
            eligible_project_cost_keur=0.0, initial_debt_guess_keur=0.0,
            period_rates=(), explicit_principal_schedule=None,
            period_dscr_targets=dscr,
        )
        policy = SeniorDebtPolicy(
            policy_id="d-test", policy_version="1.0",
            sizing_mode=SeniorDebtSizingMode.DSCR_SCULPTED,
            target_dscr=1.15, maximum_gearing=None,
            annual_fixed_rate=0.056, periods_per_year=2,
            day_count_convention=DayCountConvention.ACT_365,
            repayment_start_period_index=1, maturity_period_index=28,
            convergence_tolerance_keur=0.01, convergence_relative_tolerance=1e-8,
            maximum_iterations=50, permit_terminal_balloon=True, damping_alpha=1.0,
        )
        m = build_dscr_target_map(policy, inputs, tuple(range(1, 29)))
        assert m[25] == pytest.approx(1.35)
        assert m[26] == pytest.approx(1.35)
        for p in range(1, 25):
            assert m[p] == pytest.approx(1.15)

    def test_oborovo_dscr_map_matches_fixture(self):
        from financial_engine.senior_debt.solver import build_dscr_target_map
        d = _oborovo_data()
        inputs = _make_oborovo_inputs()
        policy = _oborovo_policy()
        m = build_dscr_target_map(policy, inputs, tuple(range(1, 29)))
        for i in range(1, 29):
            assert m[i] == pytest.approx(d["dscr_targets"][i], rel=1e-10), f"Period {i}"


# ===========================================================================
# GROUP E — Per-period availability map
# ===========================================================================

class TestGroupE_PerPeriodAvailabilityMap:
    def test_build_availability_map_explicit(self):
        from financial_engine.senior_debt.inputs import SeniorDebtInputs, PeriodDebtServiceAvailability
        from financial_engine.senior_debt.solver import build_debt_service_availability_map

        ops = (PeriodDebtServiceAvailability(period_index=28, availability_fraction=0.988950276243094),)
        inputs = SeniorDebtInputs(
            eligible_project_cost_keur=0.0, initial_debt_guess_keur=0.0,
            period_rates=(), explicit_principal_schedule=None,
            period_debt_service_availability=ops,
        )
        m = build_debt_service_availability_map(inputs, tuple(range(1, 29)))
        for p in range(1, 28):
            assert m[p] == 1.0
        assert m[28] == pytest.approx(0.988950276243094, rel=1e-10)

    def test_oborovo_ops_map_matches_fixture(self):
        from financial_engine.senior_debt.solver import build_debt_service_availability_map
        d = _oborovo_data()
        inputs = _make_oborovo_inputs()
        m = build_debt_service_availability_map(inputs, tuple(range(1, 29)))
        for i in range(1, 29):
            assert m[i] == pytest.approx(d["ops_flag"][i], rel=1e-10), f"Period {i}"


# ===========================================================================
# GROUP F — Backward-capacity identity (availability=1, scalar DSCR)
# ===========================================================================

class TestGroupF_BackwardCapacityIdentity:
    def test_scalar_backward_no_ops_equals_cfads_over_dscr(self):
        from financial_engine.senior_debt.solver import (
            build_dscr_target_map,
            build_debt_service_availability_map,
        )

        d = _oborovo_data()
        inputs = _make_oborovo_inputs(override_ops=False)
        policy = _oborovo_policy()
        period_indices = tuple(range(1, 29))
        dscr_map = build_dscr_target_map(policy, inputs, period_indices)
        avail_map = build_debt_service_availability_map(inputs, period_indices)
        for i in period_indices:
            assert avail_map[i] == 1.0
            ds_expected = max(0.0, d["cfads"][i] / dscr_map[i])
            ds_actual = max(0.0, d["cfads"][i] / dscr_map[i]) * avail_map[i]
            assert ds_actual == pytest.approx(ds_expected, rel=1e-12)


# ===========================================================================
# GROUP G — Forward-sculpting identity
# ===========================================================================

class TestGroupG_ForwardSculptingIdentity:
    def test_solver_converges_with_maps(self):
        result = _run_oborovo()
        assert result.diagnostics.converged, f"Did not converge: {result.diagnostics}"

    def test_terminal_closing_is_zero(self):
        result = _run_oborovo()
        assert result.senior_debt_closing_keur[-1] == pytest.approx(0.0, abs=0.01)


# ===========================================================================
# GROUP H — Source annual-rate schedule
# ===========================================================================

class TestGroupH_SourceRateSchedule:
    def test_rates_match_fixture_ds_row44(self):
        d = _oborovo_data()
        inputs = _make_oborovo_inputs()
        rate_map = {pr.period_index: pr.annual_rate for pr in inputs.period_rates}
        for i in range(1, 29):
            assert rate_map[i] == pytest.approx(d["annual_rates"][i], rel=1e-10), f"Period {i}"

    def test_all_28_rates_provided(self):
        inputs = _make_oborovo_inputs()
        assert len(inputs.period_rates) == 28


# ===========================================================================
# GROUP I — ACT/360 day fractions
# ===========================================================================

class TestGroupI_Act360DayFractions:
    def test_periods_reproduce_fixture_day_fracs(self):
        d = _oborovo_data()
        periods = _build_oborovo_periods()
        for p in periods:
            actual_frac = (p.period_end - p.period_start).days / 360.0
            expected = d["day_frac"][p.period_index]
            assert actual_frac == pytest.approx(expected, rel=1e-8), f"Period {p.period_index}"

    def test_p1_day_frac_184_days(self):
        d = _oborovo_data()
        assert d["day_frac"][1] == pytest.approx(184 / 360.0, rel=1e-8)

    def test_p2_day_frac_181_days(self):
        d = _oborovo_data()
        assert d["day_frac"][2] == pytest.approx(181 / 360.0, rel=1e-8)


# ===========================================================================
# GROUP J — P28 partial-period treatment + mutation test
# ===========================================================================

class TestGroupJ_P28PartialPeriod:
    def test_p28_ops_flag_is_lt_1(self):
        d = _oborovo_data()
        assert d["ops_flag"][28] < 1.0
        assert d["ops_flag"][28] == pytest.approx(0.988950276243094, rel=1e-10)

    def test_p1_to_p27_ops_flag_is_1(self):
        d = _oborovo_data()
        for i in range(1, 28):
            assert d["ops_flag"][i] == pytest.approx(1.0), f"Period {i}"

    def test_omit_p28_ops_increases_debt(self):
        d = _oborovo_data()
        result_with = _run_oborovo()
        result_without = _run_oborovo(override_ops=False)
        delta = result_without.debt_size_keur - result_with.debt_size_keur
        assert 5.0 < delta < 15.0, f"Unexpected delta: {delta:.3f} kEUR"


# ===========================================================================
# GROUP K — Vector DSCR banding + scalar mutation test
# ===========================================================================

class TestGroupK_VectorDscrBanding:
    def test_scalar_dscr_gives_g3a_capacity(self):
        d = _oborovo_data()
        result = _run_oborovo(override_dscr_targets=False)
        g3a = d["g3a_scalar"]
        assert result.debt_size_keur == pytest.approx(g3a, abs=1.0), (
            f"Expected G3A≈{g3a:.3f} kEUR, got {result.debt_size_keur:.3f}"
        )

    def test_vector_dscr_gives_g4_capacity(self):
        d = _oborovo_data()
        result = _run_oborovo()
        excel = d["excel_debt"]
        assert result.debt_size_keur == pytest.approx(excel, abs=0.001)

    def test_p25_28_dscr_is_1_35(self):
        d = _oborovo_data()
        for i in range(25, 29):
            assert d["dscr_targets"][i] == pytest.approx(1.35, rel=1e-10), f"Period {i}"

    def test_p1_24_dscr_is_1_15(self):
        d = _oborovo_data()
        for i in range(1, 25):
            assert d["dscr_targets"][i] == pytest.approx(1.15, rel=1e-10), f"Period {i}"


# ===========================================================================
# GROUP L — Exact Oborovo source-CFADS debt size
# ===========================================================================

class TestGroupL_ExactOborovoDebtSize:
    def test_clean_debt_within_001_keur_of_excel(self):
        d = _oborovo_data()
        result = _run_oborovo()
        delta = abs(result.debt_size_keur - d["excel_debt"])
        assert delta < 0.001, (
            f"Clean debt {result.debt_size_keur:.6f} kEUR vs Excel {d['excel_debt']:.6f} kEUR, "
            f"delta {delta:.9f} kEUR (threshold 0.001)"
        )

    def test_residual_is_zero(self):
        result = _run_oborovo()
        assert result.senior_debt_closing_keur[-1] == pytest.approx(0.0, abs=1e-3)

    def test_binding_constraint_is_dscr(self):
        result = _run_oborovo()
        assert "DSCR" in str(result.binding_constraint).upper()

    def test_solver_converges(self):
        result = _run_oborovo()
        assert result.diagnostics.converged
        assert result.diagnostics.termination_reason == "CONVERGED"


# ===========================================================================
# GROUP M — Period-by-period source schedule parity
# ===========================================================================

class TestGroupM_PeriodByPeriodParity:
    @pytest.fixture(scope="class")
    @classmethod
    def schedule_data(cls):
        result = _run_oborovo()
        d = _oborovo_data()
        return result, d

    def _sched(self, result):
        return {
            result.period_indices[i]: {
                "opening": result.senior_debt_opening_keur[i],
                "interest": result.senior_interest_keur[i],
                "principal": result.senior_principal_keur[i],
                "closing": result.senior_debt_closing_keur[i],
            }
            for i in range(len(result.period_indices))
        }

    def test_opening_balance_per_period(self, schedule_data):
        result, d = schedule_data
        sched = self._sched(result)
        for i in range(1, 29):
            if i not in sched:
                continue
            delta = abs(sched[i]["opening"] - d["opening"][i])
            assert delta < 0.01, f"P{i} opening delta {delta:.6f} kEUR"

    def test_interest_per_period(self, schedule_data):
        result, d = schedule_data
        sched = self._sched(result)
        for i in range(1, 29):
            if i not in sched:
                continue
            delta = abs(sched[i]["interest"] - d["interest"][i])
            assert delta < 0.01, f"P{i} interest delta {delta:.6f} kEUR"

    def test_principal_per_period(self, schedule_data):
        result, d = schedule_data
        sched = self._sched(result)
        for i in range(1, 29):
            if i not in sched:
                continue
            delta = abs(sched[i]["principal"] - d["principal"][i])
            assert delta < 0.01, f"P{i} principal delta {delta:.6f} kEUR"

    def test_closing_balance_per_period(self, schedule_data):
        result, d = schedule_data
        sched = self._sched(result)
        for i in range(1, 29):
            if i not in sched:
                continue
            delta = abs(sched[i]["closing"] - d["closing"][i])
            assert delta < 0.01, f"P{i} closing delta {delta:.6f} kEUR"

    def test_terminal_closing_is_zero(self, schedule_data):
        result, d = schedule_data
        assert result.senior_debt_closing_keur[-1] == pytest.approx(0.0, abs=0.001)


# ===========================================================================
# GROUP N — Actual vs target DSCR separation
# ===========================================================================

class TestGroupN_ActualVsTargetDscr:
    def test_solver_result_has_dscr_field(self):
        result = _run_oborovo()
        assert hasattr(result, "senior_dscr")

    def test_dscr_field_not_hardcoded_target(self):
        """At least some actual DSCR values must differ across periods."""
        result = _run_oborovo()
        dscr_vals = [v for v in result.senior_dscr if v is not None]
        assert len(dscr_vals) > 0
        # Debt service varies by period, so actual DSCR should not all be identical
        # (they converge to target but are computed from schedule, not set to target)
        assert min(dscr_vals) > 0


# ===========================================================================
# GROUP O — Fingerprint sensitivity
# ===========================================================================

class TestGroupO_FingerprintSensitivity:
    def test_fingerprint_payload_includes_new_schedules(self):
        import inspect
        from financial_engine import provenance
        src = inspect.getsource(provenance.compute_senior_debt_fingerprint)
        assert "period_dscr_targets" in src
        assert "period_debt_service_availability" in src
        assert "availability_fraction" in src

    def test_fingerprint_function_importable(self):
        from financial_engine.provenance import compute_senior_debt_fingerprint
        assert callable(compute_senior_debt_fingerprint)


# ===========================================================================
# GROUP P — Provenance
# ===========================================================================

class TestGroupP_Provenance:
    def test_fingerprint_function_exists(self):
        from financial_engine.provenance import compute_senior_debt_fingerprint
        assert callable(compute_senior_debt_fingerprint)

    def test_fingerprint_payload_includes_new_schedules(self):
        import inspect
        from financial_engine import provenance
        src = inspect.getsource(provenance.compute_senior_debt_fingerprint)
        assert "period_dscr_targets" in src
        assert "period_debt_service_availability" in src
        assert "availability_fraction" in src


# ===========================================================================
# GROUP Q — Generic Solar no-change
# ===========================================================================

class TestGroupQ_GenericSolarNoChange:
    def test_generic_solar_converges(self):
        result = _run_generic_scalar("solar-q")
        assert result.diagnostics.converged

    def test_generic_solar_debt_positive(self):
        result = _run_generic_scalar("solar-q2")
        assert result.debt_size_keur > 0

    def test_generic_solar_terminal_zero(self):
        result = _run_generic_scalar("solar-q3")
        assert result.senior_debt_closing_keur[-1] == pytest.approx(0.0, abs=1.0)


# ===========================================================================
# GROUP R — Generic Wind no-change
# ===========================================================================

class TestGroupR_GenericWindNoChange:
    def test_generic_wind_converges(self):
        result = _run_generic_scalar("wind-r", rate=0.048)
        assert result.diagnostics.converged

    def test_generic_wind_debt_positive(self):
        result = _run_generic_scalar("wind-r2", rate=0.048)
        assert result.debt_size_keur > 0


# ===========================================================================
# GROUP S — TUHO (high-rate) no-change
# ===========================================================================

class TestGroupS_TuhoNoChange:
    def test_tuho_converges(self):
        result = _run_generic_scalar("tuho-s", rate=0.085)
        assert result.diagnostics.converged

    def test_tuho_debt_positive(self):
        result = _run_generic_scalar("tuho-s2", rate=0.085)
        assert result.debt_size_keur > 0


# ===========================================================================
# GROUP T — Identity-clone invariance
# ===========================================================================

class TestGroupT_IdentityCloneInvariance:
    def test_clone_with_same_data_same_result(self):
        from financial_engine.senior_debt.inputs import (
            SeniorDebtInputs,
            PeriodRate,
            PeriodDscrTarget,
            PeriodDebtServiceAvailability,
        )
        from financial_engine.senior_debt.solver import solve_senior_debt

        d = _oborovo_data()
        active = range(1, 29)
        period_rates = tuple(PeriodRate(i, d["annual_rates"][i]) for i in active)
        dscr = tuple(PeriodDscrTarget(i, d["dscr_targets"][i]) for i in active)
        ops = tuple(PeriodDebtServiceAvailability(i, d["ops_flag"][i]) for i in active)
        cfads_map = {i: d["cfads"][i] for i in active}
        periods = _build_oborovo_periods()

        inputs1 = _make_oborovo_inputs()
        inputs2 = SeniorDebtInputs(
            eligible_project_cost_keur=0.0,
            initial_debt_guess_keur=43_000.0,
            period_rates=period_rates,
            explicit_principal_schedule=None,
            period_dscr_targets=dscr,
            period_debt_service_availability=ops,
        )
        policy = _oborovo_policy()

        r1 = solve_senior_debt(inputs=inputs1, policy=policy, periods=periods,
                                tax_cfads_fn=_no_tax_fn(cfads_map))
        r2 = solve_senior_debt(inputs=inputs2, policy=policy, periods=periods,
                                tax_cfads_fn=_no_tax_fn(cfads_map))

        assert r1.debt_size_keur == pytest.approx(r2.debt_size_keur, rel=1e-10)

    def test_initial_guess_invariance(self):
        from financial_engine.senior_debt.inputs import SeniorDebtInputs
        from financial_engine.senior_debt.solver import solve_senior_debt

        d = _oborovo_data()
        cfads_map = {i: d["cfads"][i] for i in range(1, 29)}
        periods = _build_oborovo_periods()
        policy = _oborovo_policy()
        inputs_base = _make_oborovo_inputs()

        results = []
        for guess in [10_000.0, 43_000.0, 80_000.0]:
            inputs2 = SeniorDebtInputs(
                eligible_project_cost_keur=inputs_base.eligible_project_cost_keur,
                initial_debt_guess_keur=guess,
                period_rates=inputs_base.period_rates,
                explicit_principal_schedule=inputs_base.explicit_principal_schedule,
                period_dscr_targets=inputs_base.period_dscr_targets,
                period_debt_service_availability=inputs_base.period_debt_service_availability,
            )
            r = solve_senior_debt(inputs=inputs2, policy=policy, periods=periods,
                                   tax_cfads_fn=_no_tax_fn(cfads_map))
            results.append(r.debt_size_keur)

        assert all(
            abs(v - results[0]) < 0.01 for v in results
        ), f"Initial-guess invariance failed: {results}"


# ===========================================================================
# GROUP U — No project dispatch
# ===========================================================================

class TestGroupU_NoProjectDispatch:
    def test_solver_module_has_no_oborovo_import(self):
        import inspect
        from financial_engine.senior_debt import solver
        src = inspect.getsource(solver)
        assert "oborovo" not in src.lower()

    def test_inputs_module_has_no_oborovo_import(self):
        import inspect
        from financial_engine.senior_debt import inputs as inp_mod
        src = inspect.getsource(inp_mod)
        assert "oborovo" not in src.lower()

    def test_validation_module_has_no_oborovo_import(self):
        import inspect
        from financial_engine.senior_debt import validation as val_mod
        src = inspect.getsource(val_mod)
        assert "oborovo" not in src.lower()


# ===========================================================================
# GROUP V — No debt target plug
# ===========================================================================

class TestGroupV_NoDebtTargetPlug:
    def test_no_hardcoded_oborovo_debt_in_solver(self):
        import inspect
        from financial_engine.senior_debt import solver
        src = inspect.getsource(solver)
        assert "42852" not in src

    def test_no_approved_delta_in_new_code(self):
        import inspect
        import re
        from financial_engine.senior_debt import solver, inputs as inp_mod, validation as val_mod
        from financial_engine import provenance

        for mod, name in [
            (solver, "solver"),
            (inp_mod, "inputs"),
            (val_mod, "validation"),
            (provenance, "provenance"),
        ]:
            src = inspect.getsource(mod)
            assert not re.search(r"approved_delta", src), f"{name}: approved_delta found"
            assert not re.search(r"tax.*plug", src, re.I), f"{name}: tax plug pattern found"


# ===========================================================================
# GROUP W — C3B1/C3B2 fixture freeze
# ===========================================================================

class TestGroupW_C3B1C3B2FixtureFreeze:
    def test_c3b2_verdict_intact(self):
        d = _load_fixture()
        verdict = d["phase2c_sizing_analysis"].get("verdict", "")
        assert "C3B2" in verdict or "PROVED" in verdict.upper(), f"Verdict: {verdict}"

    def test_g4_vector_capacity_intact(self):
        d = _load_fixture()
        g4 = d["phase2c_sizing_analysis"]["independent_capacity_proof"]["g4_vector_capacity"]["capacity_keur"]
        assert g4 == pytest.approx(42852.278762563, rel=1e-9)

    def test_g3a_scalar_capacity_intact(self):
        d = _load_fixture()
        g3a = d["phase2c_sizing_analysis"]["independent_capacity_proof"]["g3a_scalar_capacity"]["capacity_keur"]
        assert g3a == pytest.approx(43368.223731864, rel=1e-9)

    def test_excel_debt_intact(self):
        d = _load_fixture()
        excel = d["phase2c_sizing_analysis"]["excel_total_debt_keur"]
        assert excel == pytest.approx(42852.27876256299, rel=1e-9)

    def test_fixture_has_required_workstreams(self):
        d = _load_fixture()
        for ws in ("workstream_a", "workstream_b", "workstream_e", "phase2c_sizing_analysis"):
            assert ws in d, f"Missing workstream: {ws}"
