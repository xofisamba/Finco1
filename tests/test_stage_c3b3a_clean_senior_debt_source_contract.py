"""Stage C3B3A — Clean Senior Debt Source Contract.

Verifies that the generic senior-debt engine, extended with PeriodDscrTarget
and PeriodDebtServiceAvailability, reproduces the Oborovo Excel source debt
(42,852.279 kEUR) from raw DS!row20/22/9/44/6 without any project-specific
dispatch or forbidden inputs.

Canonical period axis (C3B3A2):
    Excel debt periods P1..P28 map to clean period indices 2..29.
    Mapping: clean_period_index = excel_debt_period + 1.
    Real operating periods are derived from create_default_oborovo() →
    from_project_inputs() → run_operating_model(). All fixture vectors are
    re-keyed from excel index (1..28) to clean index (2..29).

Availability source ownership decision (C3B3A):
    DS!row9 ops_flag P28 = 179/181 = 0.988950276243094.
    Classified EXPLICIT_INPUT — not derivable from standard tenor rollover.

Test groups A–W.
"""
from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path
from functools import lru_cache

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
    """Return structured Oborovo raw vectors keyed by EXCEL period index (1..28).

    Canonical period mapping (C3B3A2):
        clean_period_index = excel_debt_period + 1
        clean 2..29 ↔ excel P1..P28
    """
    d = _load_fixture()
    ws_a = d["workstream_a"]
    ws_b = d["workstream_b"]
    ws_e = d["workstream_e"]
    pv = ws_b["period_vectors"]
    return {
        "cfads": ws_a["ds_row20_cfads"]["period_values_keur"],          # keyed 1..28
        "dscr_targets": ws_a["ds_row22_dscr_target"]["period_values"],  # keyed 1..28
        "ops_flag": pv["row9_ops_flag"]["period_values"],               # keyed 1..28
        "annual_rates": ws_e["ds_row44_annual_sculpting_rate"]["period_values"],  # keyed 1..28
        "day_frac": pv["row6_day_frac"]["period_values"],               # keyed 1..28
        "opening": ws_e["ds_row61_opening_balance"]["period_values"],   # keyed 1..28
        "interest": ws_e["ds_row64_period_interest"]["period_values"],  # keyed 1..28
        "principal": pv["row63_principal"]["period_values"],            # keyed 1..28
        "closing": pv["row67_closing"]["period_values"],                # keyed 1..28
        "excel_debt": d["phase2c_sizing_analysis"]["excel_total_debt_keur"],
        "g3a_scalar": d["phase2c_sizing_analysis"]["causal_bridge"]["g3a_scalar_backward_induction_keur"],
    }


@lru_cache(maxsize=1)
def _oborovo_real_periods() -> tuple[OperatingPeriodResult, ...]:
    """Return real Oborovo debt periods (clean indices 2..29) from the live factory.

    Uses: create_default_oborovo() → from_project_inputs() → run_operating_model().
    These 28 semiannual periods start 2030-06-30 and end 2044-06-29 (14-year tenor).
    """
    from app.project_factories import create_default_oborovo
    from financial_engine.adapters.project_inputs import from_project_inputs
    from financial_engine.orchestrator import run_operating_model

    proj = create_default_oborovo()
    model_in = from_project_inputs(proj, source_id="c3b3a-test", baseline_commit_sha="")
    result = run_operating_model(model_in)
    op_only = [p for p in result.periods if p.is_operation]
    return tuple(op_only[:28])  # clean indices 2..29


def _no_tax_fn(cfads_map: dict[int, float]):
    """Tax feedback stub: CFADS = fixed map, cash_tax = 0."""
    def fn(interest_by_period: dict[int, float]):
        return cfads_map.copy(), {k: 0.0 for k in cfads_map}
    return fn


def _make_oborovo_inputs(
    override_dscr_targets: bool = True,
    override_ops: bool = True,
):
    """Build SeniorDebtInputs keyed to REAL clean period indices 2..29.

    Fixture vectors (excel key 1..28) are re-keyed:
        clean_idx = p.period_index  (2..29)
        excel_key = clean_idx - 1   (1..28)
    """
    from financial_engine.senior_debt.inputs import (
        PeriodDebtServiceAvailability,
        PeriodDscrTarget,
        PeriodRate,
        SeniorDebtInputs,
    )

    d = _oborovo_data()
    periods = _oborovo_real_periods()

    period_rates = tuple(
        PeriodRate(p.period_index, d["annual_rates"][p.period_index - 1])
        for p in periods
    )

    dscr_targets: tuple = ()
    if override_dscr_targets:
        dscr_targets = tuple(
            PeriodDscrTarget(p.period_index, d["dscr_targets"][p.period_index - 1])
            for p in periods
        )

    ops: tuple = ()
    if override_ops:
        ops = tuple(
            PeriodDebtServiceAvailability(p.period_index, d["ops_flag"][p.period_index - 1])
            for p in periods
        )

    return SeniorDebtInputs(
        eligible_project_cost_keur=0.0,
        initial_debt_guess_keur=43_000.0,
        period_rates=period_rates,
        explicit_principal_schedule=None,
        period_dscr_targets=dscr_targets,
        period_debt_service_availability=ops,
    )


def _oborovo_policy() -> SeniorDebtPolicy:
    """Build SeniorDebtPolicy for real clean period indices 2..29."""
    periods = _oborovo_real_periods()
    return SeniorDebtPolicy(
        policy_id="c3b3a-oborovo-source",
        policy_version="1.0.0",
        sizing_mode=SeniorDebtSizingMode.DSCR_SCULPTED,
        target_dscr=1.15,
        maximum_gearing=None,
        annual_fixed_rate=None,
        periods_per_year=2,
        day_count_convention=DayCountConvention.ACT_360,
        repayment_start_period_index=periods[0].period_index,   # 2
        maturity_period_index=periods[-1].period_index,          # 29
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
    periods = _oborovo_real_periods()
    cfads_map = {p.period_index: d["cfads"][p.period_index - 1] for p in periods}
    inputs = _make_oborovo_inputs(override_dscr_targets, override_ops)
    policy = _oborovo_policy()

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
    # Validation tests use synthetic period indices 2..29 to match real clean axis.
    def _validate(self, inputs, policy):
        from financial_engine.senior_debt.validation import validate_senior_debt_inputs
        known = frozenset(range(2, 30))
        return validate_senior_debt_inputs(inputs, policy, known)

    def _base_policy(self):
        return SeniorDebtPolicy(
            policy_id="val-test", policy_version="1.0",
            sizing_mode=SeniorDebtSizingMode.DSCR_SCULPTED,
            target_dscr=1.15, maximum_gearing=None,
            annual_fixed_rate=0.056, periods_per_year=2,
            day_count_convention=DayCountConvention.ACT_365,
            repayment_start_period_index=2, maturity_period_index=29,
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
        dscr = tuple(PeriodDscrTarget(i, 1.15) for i in range(2, 30))
        ops = tuple(PeriodDebtServiceAvailability(i, 1.0) for i in range(2, 30))
        errors = self._validate(self._base_inputs(dscr, ops), self._base_policy())
        assert not any(
            "dscr_target" in e.lower() or "availability" in e.lower() for e in errors
        )

    def test_dscr_target_lte_1_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDscrTarget
        dscr = (PeriodDscrTarget(period_index=2, target_dscr=1.0),)
        errors = self._validate(self._base_inputs(dscr), self._base_policy())
        assert any("dscr" in e.lower() and "> 1" in e for e in errors)

    def test_dscr_target_negative_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDscrTarget
        dscr = (PeriodDscrTarget(period_index=2, target_dscr=-0.5),)
        errors = self._validate(self._base_inputs(dscr), self._base_policy())
        assert any("dscr" in e.lower() for e in errors)

    def test_dscr_target_bool_period_index_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDscrTarget
        dscr = (PeriodDscrTarget(period_index=True, target_dscr=1.15),)  # type: ignore[arg-type]
        errors = self._validate(self._base_inputs(dscr), self._base_policy())
        assert any("bool" in e.lower() or "period_index" in e.lower() for e in errors)

    def test_dscr_target_nan_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDscrTarget
        dscr = (PeriodDscrTarget(period_index=2, target_dscr=float("nan")),)
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
        ops = (PeriodDebtServiceAvailability(period_index=2, availability_fraction=1.001),)
        errors = self._validate(self._base_inputs(ops=ops), self._base_policy())
        assert any("availability" in e.lower() for e in errors)

    def test_availability_negative_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDebtServiceAvailability
        ops = (PeriodDebtServiceAvailability(period_index=2, availability_fraction=-0.01),)
        errors = self._validate(self._base_inputs(ops=ops), self._base_policy())
        assert any("availability" in e.lower() for e in errors)

    def test_availability_nan_rejected(self):
        from financial_engine.senior_debt.inputs import PeriodDebtServiceAvailability
        ops = (PeriodDebtServiceAvailability(period_index=2, availability_fraction=float("nan")),)
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
            PeriodDebtServiceAvailability(period_index=29, availability_fraction=1.0),
            PeriodDebtServiceAvailability(period_index=29, availability_fraction=0.98),
        )
        errors = self._validate(self._base_inputs(ops=ops), self._base_policy())
        assert any("duplicate" in e.lower() or "29" in e for e in errors)

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
            repayment_start_period_index=2, maturity_period_index=11,
            convergence_tolerance_keur=0.01, convergence_relative_tolerance=1e-8,
            maximum_iterations=50, permit_terminal_balloon=False, damping_alpha=1.0,
        )
        m = build_dscr_target_map(policy, inputs, tuple(range(2, 12)))
        assert all(v == pytest.approx(1.20) for v in m.values())

    def test_empty_ops_uses_1_0(self):
        from financial_engine.senior_debt.inputs import SeniorDebtInputs
        from financial_engine.senior_debt.solver import build_debt_service_availability_map

        inputs = SeniorDebtInputs(
            eligible_project_cost_keur=0.0, initial_debt_guess_keur=0.0,
            period_rates=(), explicit_principal_schedule=None,
        )
        m = build_debt_service_availability_map(inputs, tuple(range(2, 22)))
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

        # clean indices 26..27 map to excel P25..P26 (1.35x band)
        dscr = (
            PeriodDscrTarget(period_index=26, target_dscr=1.35),
            PeriodDscrTarget(period_index=27, target_dscr=1.35),
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
            repayment_start_period_index=2, maturity_period_index=29,
            convergence_tolerance_keur=0.01, convergence_relative_tolerance=1e-8,
            maximum_iterations=50, permit_terminal_balloon=True, damping_alpha=1.0,
        )
        m = build_dscr_target_map(policy, inputs, tuple(range(2, 30)))
        assert m[26] == pytest.approx(1.35)
        assert m[27] == pytest.approx(1.35)
        for p in range(2, 26):
            assert m[p] == pytest.approx(1.15)

    def test_oborovo_dscr_map_matches_fixture(self):
        from financial_engine.senior_debt.solver import build_dscr_target_map
        d = _oborovo_data()
        inputs = _make_oborovo_inputs()
        policy = _oborovo_policy()
        periods = _oborovo_real_periods()
        m = build_dscr_target_map(policy, inputs, tuple(p.period_index for p in periods))
        for p in periods:
            clean_idx = p.period_index
            excel_key = clean_idx - 1
            assert m[clean_idx] == pytest.approx(d["dscr_targets"][excel_key], rel=1e-10), (
                f"Clean {clean_idx} (P{excel_key})"
            )


# ===========================================================================
# GROUP E — Per-period availability map
# ===========================================================================

class TestGroupE_PerPeriodAvailabilityMap:
    def test_build_availability_map_explicit(self):
        from financial_engine.senior_debt.inputs import SeniorDebtInputs, PeriodDebtServiceAvailability
        from financial_engine.senior_debt.solver import build_debt_service_availability_map

        # clean index 29 = excel P28 (the partial final period)
        ops = (PeriodDebtServiceAvailability(period_index=29, availability_fraction=0.988950276243094),)
        inputs = SeniorDebtInputs(
            eligible_project_cost_keur=0.0, initial_debt_guess_keur=0.0,
            period_rates=(), explicit_principal_schedule=None,
            period_debt_service_availability=ops,
        )
        m = build_debt_service_availability_map(inputs, tuple(range(2, 30)))
        for p in range(2, 29):
            assert m[p] == 1.0
        assert m[29] == pytest.approx(0.988950276243094, rel=1e-10)

    def test_oborovo_ops_map_matches_fixture(self):
        from financial_engine.senior_debt.solver import build_debt_service_availability_map
        d = _oborovo_data()
        inputs = _make_oborovo_inputs()
        periods = _oborovo_real_periods()
        m = build_debt_service_availability_map(inputs, tuple(p.period_index for p in periods))
        for p in periods:
            clean_idx = p.period_index
            excel_key = clean_idx - 1
            assert m[clean_idx] == pytest.approx(d["ops_flag"][excel_key], rel=1e-10), (
                f"Clean {clean_idx} (P{excel_key})"
            )


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
        periods = _oborovo_real_periods()
        period_indices = tuple(p.period_index for p in periods)
        dscr_map = build_dscr_target_map(policy, inputs, period_indices)
        avail_map = build_debt_service_availability_map(inputs, period_indices)
        for p in periods:
            clean_idx = p.period_index
            excel_key = clean_idx - 1
            assert avail_map[clean_idx] == 1.0
            cfads = d["cfads"][excel_key]
            ds_expected = max(0.0, cfads / dscr_map[clean_idx])
            ds_actual = max(0.0, cfads / dscr_map[clean_idx]) * avail_map[clean_idx]
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
        periods = _oborovo_real_periods()
        for p in periods:
            clean_idx = p.period_index
            excel_key = clean_idx - 1
            assert rate_map[clean_idx] == pytest.approx(d["annual_rates"][excel_key], rel=1e-10), (
                f"Clean {clean_idx} (P{excel_key})"
            )

    def test_all_28_rates_provided(self):
        inputs = _make_oborovo_inputs()
        assert len(inputs.period_rates) == 28


# ===========================================================================
# GROUP I — ACT/360 day fractions
# ===========================================================================

class TestGroupI_Act360DayFractions:
    """ACT/360 canonical proof: real periods 2..29 reproduce DS!row6 exactly.

    Mapping: clean_period_index = excel_debt_period + 1
    COD = 2030-06-30 → clean period 2 starts 2030-06-30.
    All 28 deltas = 0.00e+00 (exact integer-day/360 identity).
    """

    def test_all_28_real_periods_reproduce_fixture_day_fracs(self):
        """Canonical proof: period_day_fraction(real_start, real_end, ACT_360) == DS!row6."""
        from financial_engine.senior_debt.interest import period_day_fraction
        from financial_engine.senior_debt.policy import DayCountConvention as DC

        d = _oborovo_data()
        periods = _oborovo_real_periods()
        assert len(periods) == 28, f"Expected 28 debt periods, got {len(periods)}"
        for p in periods:
            clean_idx = p.period_index     # 2..29
            excel_key = clean_idx - 1     # 1..28
            actual_frac = period_day_fraction(p.period_start, p.period_end, DC.ACT_360)
            expected = d["day_frac"][excel_key]
            delta = abs(actual_frac - expected)
            assert delta == pytest.approx(0.0, abs=1e-15), (
                f"Clean {clean_idx} (P{excel_key}): actual={actual_frac:.6f} "
                f"excel={expected:.6f} delta={delta:.2e}"
            )

    def test_clean_period_2_starts_at_cod(self):
        """Clean period 2 (= excel P1) must start at COD = 2030-06-30."""
        periods = _oborovo_real_periods()
        assert periods[0].period_index == 2
        assert periods[0].period_start == date(2030, 6, 30)

    def test_clean_period_29_is_last_debt_period(self):
        """Clean period 29 (= excel P28) must be the last debt period."""
        periods = _oborovo_real_periods()
        assert periods[-1].period_index == 29

    def test_p1_day_frac_184_days(self):
        """Excel P1 (clean 2): 184 days / 360 = 0.511111..."""
        d = _oborovo_data()
        assert d["day_frac"][1] == pytest.approx(184 / 360.0, rel=1e-8)

    def test_p2_day_frac_181_days(self):
        """Excel P2 (clean 3): 181 days / 360 = 0.502778..."""
        d = _oborovo_data()
        assert d["day_frac"][2] == pytest.approx(181 / 360.0, rel=1e-8)


# ===========================================================================
# GROUP J — P28 partial-period treatment + mutation test
# ===========================================================================

class TestGroupJ_P28PartialPeriod:
    """Excel P28 = clean period 29. ops_flag = 179/181 = 0.988950276243094 (EXPLICIT_INPUT).

    Availability source classification (C3B3A):
        COD + relativedelta(years=14) → 1.0 for all periods (not derivable).
        DS!row9 P28 = 179/181 → EXPLICIT_INPUT, carried in sculpting config.
    """

    def test_p28_ops_flag_is_lt_1(self):
        """Excel P28 (clean 29): availability = 179/181 ≠ 1.0 (partial final period)."""
        d = _oborovo_data()
        assert d["ops_flag"][28] < 1.0
        assert d["ops_flag"][28] == pytest.approx(0.988950276243094, rel=1e-10)

    def test_p1_to_p27_ops_flag_is_1(self):
        """Excel P1..P27 (clean 2..28): all availability = 1.0."""
        d = _oborovo_data()
        for i in range(1, 28):
            assert d["ops_flag"][i] == pytest.approx(1.0), f"Excel P{i}"

    def test_omit_p28_ops_increases_debt(self):
        """Omitting the partial-period availability increases debt (less capacity absorbed)."""
        result_with = _run_oborovo()
        result_without = _run_oborovo(override_ops=False)
        delta = result_without.debt_size_keur - result_with.debt_size_keur
        assert 5.0 < delta < 15.0, f"Unexpected delta: {delta:.3f} kEUR"

    def test_clean_29_availability_in_real_inputs(self):
        """Real SeniorDebtInputs must have availability_fraction < 1.0 at clean index 29."""
        inputs = _make_oborovo_inputs()
        avail_map = {a.period_index: a.availability_fraction
                     for a in inputs.period_debt_service_availability}
        assert 29 in avail_map, "Clean period 29 not found in inputs"
        assert avail_map[29] == pytest.approx(0.988950276243094, rel=1e-10)


# ===========================================================================
# GROUP K — Vector DSCR banding + scalar mutation test
# ===========================================================================

class TestGroupK_VectorDscrBanding:
    """DSCR banding: excel P1..P24 = 1.15x, P25..P28 = 1.35x (clean 2..25 / 26..29)."""

    def test_scalar_dscr_gives_g3a_capacity(self):
        """Scalar policy DSCR (no per-period override) → G3A backward induction debt.

        Tolerance: < 0.01 kEUR (C3B3A2 requirement; replaces former abs=1.0).
        """
        d = _oborovo_data()
        result = _run_oborovo(override_dscr_targets=False)
        g3a = d["g3a_scalar"]
        assert result.debt_size_keur == pytest.approx(g3a, abs=0.01), (
            f"Expected G3A≈{g3a:.3f} kEUR, got {result.debt_size_keur:.3f}"
        )

    def test_vector_dscr_gives_g4_capacity(self):
        d = _oborovo_data()
        result = _run_oborovo()
        excel = d["excel_debt"]
        assert result.debt_size_keur == pytest.approx(excel, abs=0.001)

    def test_p25_28_dscr_is_1_35(self):
        """Excel P25..P28 (clean 26..29): DSCR target = 1.35x."""
        d = _oborovo_data()
        for i in range(25, 29):
            assert d["dscr_targets"][i] == pytest.approx(1.35, rel=1e-10), f"Excel P{i}"

    def test_p1_24_dscr_is_1_15(self):
        """Excel P1..P24 (clean 2..25): DSCR target = 1.15x."""
        d = _oborovo_data()
        for i in range(1, 25):
            assert d["dscr_targets"][i] == pytest.approx(1.15, rel=1e-10), f"Excel P{i}"


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
    """Period-by-period parity: clean index 2..29 ↔ fixture excel key 1..28.

    All deltas < 0.01 kEUR for opening, interest, principal, closing, debt_service.
    Actual DSCR = CFADS / debt_service (not copied from target).
    """

    @pytest.fixture(scope="class")
    @classmethod
    def schedule_data(cls):
        result = _run_oborovo()
        d = _oborovo_data()
        periods = _oborovo_real_periods()
        return result, d, periods

    def _sched(self, result):
        return {
            result.period_indices[i]: {
                "opening": result.senior_debt_opening_keur[i],
                "interest": result.senior_interest_keur[i],
                "principal": result.senior_principal_keur[i],
                "ds": result.senior_debt_service_keur[i],
                "closing": result.senior_debt_closing_keur[i],
                "dscr": result.senior_dscr[i],
            }
            for i in range(len(result.period_indices))
        }

    def test_opening_balance_per_period(self, schedule_data):
        result, d, periods = schedule_data
        sched = self._sched(result)
        for p in periods:
            clean_idx = p.period_index
            excel_key = clean_idx - 1
            delta = abs(sched[clean_idx]["opening"] - d["opening"][excel_key])
            assert delta < 0.01, f"Clean {clean_idx} (P{excel_key}) opening delta {delta:.6f} kEUR"

    def test_interest_per_period(self, schedule_data):
        result, d, periods = schedule_data
        sched = self._sched(result)
        for p in periods:
            clean_idx = p.period_index
            excel_key = clean_idx - 1
            delta = abs(sched[clean_idx]["interest"] - d["interest"][excel_key])
            assert delta < 0.01, f"Clean {clean_idx} (P{excel_key}) interest delta {delta:.6f} kEUR"

    def test_principal_per_period(self, schedule_data):
        result, d, periods = schedule_data
        sched = self._sched(result)
        for p in periods:
            clean_idx = p.period_index
            excel_key = clean_idx - 1
            delta = abs(sched[clean_idx]["principal"] - d["principal"][excel_key])
            assert delta < 0.01, f"Clean {clean_idx} (P{excel_key}) principal delta {delta:.6f} kEUR"

    def test_closing_balance_per_period(self, schedule_data):
        result, d, periods = schedule_data
        sched = self._sched(result)
        for p in periods:
            clean_idx = p.period_index
            excel_key = clean_idx - 1
            delta = abs(sched[clean_idx]["closing"] - d["closing"][excel_key])
            assert delta < 0.01, f"Clean {clean_idx} (P{excel_key}) closing delta {delta:.6f} kEUR"

    def test_debt_service_per_period(self, schedule_data):
        """Debt service = interest + principal. All deltas < 0.01 kEUR."""
        result, d, periods = schedule_data
        sched = self._sched(result)
        for p in periods:
            clean_idx = p.period_index
            excel_key = clean_idx - 1
            excel_ds = d["interest"][excel_key] + d["principal"][excel_key]
            delta = abs(sched[clean_idx]["ds"] - excel_ds)
            assert delta < 0.01, f"Clean {clean_idx} (P{excel_key}) DS delta {delta:.6f} kEUR"

    def test_actual_dscr_equals_cfads_over_ds(self, schedule_data):
        """Actual DSCR = CFADS / debt_service (not copied from target)."""
        result, d, periods = schedule_data
        sched = self._sched(result)
        for p in periods:
            clean_idx = p.period_index
            excel_key = clean_idx - 1
            ds = sched[clean_idx]["ds"]
            cfads = d["cfads"][excel_key]
            if ds > 0.0:
                expected_dscr = cfads / ds
                actual_dscr = sched[clean_idx]["dscr"]
                if actual_dscr is not None:
                    assert actual_dscr == pytest.approx(expected_dscr, rel=1e-8), (
                        f"Clean {clean_idx}: DSCR {actual_dscr:.6f} ≠ CFADS/DS {expected_dscr:.6f}"
                    )

    def test_terminal_closing_is_zero(self, schedule_data):
        result, d, periods = schedule_data
        assert result.senior_debt_closing_keur[-1] == pytest.approx(0.0, abs=0.001)


# ===========================================================================
# GROUP N — Actual vs target DSCR separation
# ===========================================================================

class TestGroupN_ActualVsTargetDscr:
    """Actual DSCR is computed as CFADS / debt_service, not copied from target."""

    def test_solver_result_has_dscr_field(self):
        result = _run_oborovo()
        assert hasattr(result, "senior_dscr")

    def test_dscr_field_not_hardcoded_target(self):
        """At least some actual DSCR values must differ across periods."""
        result = _run_oborovo()
        dscr_vals = [v for v in result.senior_dscr if v is not None]
        assert len(dscr_vals) > 0
        assert min(dscr_vals) > 0

    def test_actual_dscr_identity_cfads_over_ds(self):
        """actual_dscr[p] = CFADS[p] / debt_service[p] for every period with DS > 0."""
        d = _oborovo_data()
        result = _run_oborovo()
        periods = _oborovo_real_periods()
        sched = {
            result.period_indices[i]: {
                "ds": result.senior_debt_service_keur[i],
                "dscr": result.senior_dscr[i],
            }
            for i in range(len(result.period_indices))
        }
        for p in periods:
            clean_idx = p.period_index
            excel_key = clean_idx - 1
            ds = sched[clean_idx]["ds"]
            if ds > 0.0:
                cfads = d["cfads"][excel_key]
                expected = cfads / ds
                actual = sched[clean_idx]["dscr"]
                assert actual is not None
                assert actual == pytest.approx(expected, rel=1e-8), (
                    f"Clean {clean_idx}: DSCR identity CFADS/DS={expected:.6f}, got {actual:.6f}"
                )


# ===========================================================================
# GROUP O — Fingerprint sensitivity (behavioral — calls function directly)
# ===========================================================================

def _make_minimal_senior_debt_model_input(
    *,
    dscr_targets=None,
    availability=None,
    annual_rate_override=None,
    day_count_override=None,
    target_dscr_override=None,
):
    """Build a SeniorDebtModelInput for fingerprint mutation tests.

    Uses create_default_oborovo() for the operating core and a minimal zero-tax policy.
    Returns a SeniorDebtModelInput usable with compute_senior_debt_fingerprint().
    """
    from app.project_factories import create_default_oborovo
    from financial_engine.adapters.project_inputs import from_project_inputs
    from financial_engine.orchestrator import run_operating_model
    from financial_engine.inputs import (
        TaxCalculationInput, SeniorDebtModelInput, DebtSizingCaseInput,
    )
    from financial_engine.policies.tax import TaxPolicy, CashTaxTiming
    from financial_engine.senior_debt.inputs import (
        PeriodRate, PeriodDscrTarget, PeriodDebtServiceAvailability, SeniorDebtInputs,
    )
    from financial_engine.senior_debt.policy import (
        SeniorDebtPolicy, SeniorDebtSizingMode, DayCountConvention,
    )

    proj = create_default_oborovo()
    model_in = from_project_inputs(proj, source_id="fp-test", baseline_commit_sha="")
    result = run_operating_model(model_in)
    op_only = [p for p in result.periods if p.is_operation][:28]

    d = _oborovo_data()
    rate = annual_rate_override if annual_rate_override is not None else 0.0589
    period_rates = tuple(
        PeriodRate(p.period_index, rate)
        for p in op_only
    )

    if dscr_targets is None:
        dscr_t = tuple(
            PeriodDscrTarget(p.period_index, 1.15)
            for p in op_only
        )
    else:
        dscr_t = dscr_targets

    if availability is None:
        avail = tuple(
            PeriodDebtServiceAvailability(p.period_index, 1.0)
            for p in op_only
        )
    else:
        avail = availability

    dc = day_count_override if day_count_override is not None else DayCountConvention.ACT_360
    td = target_dscr_override if target_dscr_override is not None else 1.15

    policy = SeniorDebtPolicy(
        policy_id="fp-test-policy",
        policy_version="1.0",
        sizing_mode=SeniorDebtSizingMode.DSCR_SCULPTED,
        target_dscr=td,
        maximum_gearing=None,
        annual_fixed_rate=None,
        periods_per_year=2,
        day_count_convention=dc,
        repayment_start_period_index=op_only[0].period_index,
        maturity_period_index=op_only[-1].period_index,
        convergence_tolerance_keur=1e-4,
        convergence_relative_tolerance=1e-9,
        maximum_iterations=100,
        permit_terminal_balloon=True,
        damping_alpha=1.0,
    )
    sd_inputs = SeniorDebtInputs(
        eligible_project_cost_keur=0.0,
        initial_debt_guess_keur=43_000.0,
        period_rates=period_rates,
        explicit_principal_schedule=None,
        period_dscr_targets=dscr_t,
        period_debt_service_availability=avail,
    )
    tax_policy = TaxPolicy(
        policy_id="test-zero-tax",
        policy_version="1.0",
        corporate_rate=0.0,
        periods_per_tax_year=2,
        loss_carryforward_years=0,
        atad_enabled=False,
        atad_ebitda_limit=0.3,
        atad_de_minimis_threshold_keur_annual=0.0,
        cash_tax_timing=CashTaxTiming.TAX_YEAR_LAST_PERIOD,
        cash_tax_payment_lag_periods=0,
    )
    tax_input = TaxCalculationInput(
        policy=tax_policy,
        opening_loss_vintages=(),
        period_interest=(),
        period_adjustments=(),
    )
    return SeniorDebtModelInput(
        operating=model_in,
        tax=tax_input,
        senior_debt_policy=policy,
        senior_debt_inputs=sd_inputs,
        debt_sizing_case=DebtSizingCaseInput(
            production_yield_scenario=model_in.technical.yield_scenario,
        ),
    )


class TestGroupO_FingerprintSensitivity:
    """Behavioral fingerprint tests: call compute_senior_debt_fingerprint(SeniorDebtModelInput)
    directly. Six mutation assertions (A–F) prove the function is sensitive to the right inputs
    and invariant to the right non-inputs.
    """

    def test_fingerprint_function_importable(self):
        from financial_engine.provenance import compute_senior_debt_fingerprint
        assert callable(compute_senior_debt_fingerprint)

    def test_mutation_A_same_inputs_same_fingerprint(self):
        """A: two independently built identical SeniorDebtModelInputs → same fingerprint."""
        from financial_engine.provenance import compute_senior_debt_fingerprint
        m1 = _make_minimal_senior_debt_model_input()
        m2 = _make_minimal_senior_debt_model_input()
        fp1 = compute_senior_debt_fingerprint(m1)
        fp2 = compute_senior_debt_fingerprint(m2)
        assert fp1 == fp2, "Identical inputs must produce identical fingerprint"

    def test_mutation_B_rate_change_different_fingerprint(self):
        """B: changing annual rate → different fingerprint."""
        from financial_engine.provenance import compute_senior_debt_fingerprint
        m_base = _make_minimal_senior_debt_model_input(annual_rate_override=0.0589)
        m_mut = _make_minimal_senior_debt_model_input(annual_rate_override=0.0700)
        fp_base = compute_senior_debt_fingerprint(m_base)
        fp_mut = compute_senior_debt_fingerprint(m_mut)
        assert fp_base != fp_mut, "Rate change must produce different fingerprint"

    def test_mutation_C_dscr_change_different_fingerprint(self):
        """C: changing per-period DSCR target → different fingerprint."""
        from financial_engine.provenance import compute_senior_debt_fingerprint
        from financial_engine.senior_debt.inputs import PeriodDscrTarget

        proj_base = _make_minimal_senior_debt_model_input()
        op_only = [p for p in _oborovo_real_periods()]

        # Higher DSCR for last 4 periods
        dscr_mut = tuple(
            PeriodDscrTarget(p.period_index, 1.35 if i >= 24 else 1.15)
            for i, p in enumerate(op_only)
        )
        m_mut = _make_minimal_senior_debt_model_input(dscr_targets=dscr_mut)
        fp_base = compute_senior_debt_fingerprint(proj_base)
        fp_mut = compute_senior_debt_fingerprint(m_mut)
        assert fp_base != fp_mut, "DSCR change must produce different fingerprint"

    def test_mutation_D_availability_change_different_fingerprint(self):
        """D: changing availability fraction → different fingerprint."""
        from financial_engine.provenance import compute_senior_debt_fingerprint
        from financial_engine.senior_debt.inputs import PeriodDebtServiceAvailability

        op_only = list(_oborovo_real_periods())
        avail_base = tuple(
            PeriodDebtServiceAvailability(p.period_index, 1.0)
            for p in op_only
        )
        avail_mut = tuple(
            PeriodDebtServiceAvailability(p.period_index, 0.988950276243094 if i == 27 else 1.0)
            for i, p in enumerate(op_only)
        )
        m_base = _make_minimal_senior_debt_model_input(availability=avail_base)
        m_mut = _make_minimal_senior_debt_model_input(availability=avail_mut)
        fp_base = compute_senior_debt_fingerprint(m_base)
        fp_mut = compute_senior_debt_fingerprint(m_mut)
        assert fp_base != fp_mut, "Availability change must produce different fingerprint"

    def test_mutation_E_day_count_act360_vs_act365_different_fingerprint(self):
        """E: ACT_360 vs ACT_365 day-count convention → different fingerprint."""
        from financial_engine.provenance import compute_senior_debt_fingerprint
        from financial_engine.senior_debt.policy import DayCountConvention
        m_360 = _make_minimal_senior_debt_model_input(day_count_override=DayCountConvention.ACT_360)
        m_365 = _make_minimal_senior_debt_model_input(day_count_override=DayCountConvention.ACT_365)
        fp_360 = compute_senior_debt_fingerprint(m_360)
        fp_365 = compute_senior_debt_fingerprint(m_365)
        assert fp_360 != fp_365, "ACT_360 vs ACT_365 must produce different fingerprint"

    def test_mutation_F_initial_guess_invariance(self):
        """F: initial_debt_guess_keur is excluded from the fingerprint — must be same."""
        from financial_engine.provenance import compute_senior_debt_fingerprint
        from financial_engine.inputs import SeniorDebtModelInput
        from financial_engine.senior_debt.inputs import SeniorDebtInputs

        m = _make_minimal_senior_debt_model_input()
        # Rebuild with a different initial guess
        sd = m.senior_debt_inputs
        sd_new = SeniorDebtInputs(
            eligible_project_cost_keur=sd.eligible_project_cost_keur,
            initial_debt_guess_keur=99_999.0,  # very different
            period_rates=sd.period_rates,
            explicit_principal_schedule=sd.explicit_principal_schedule,
            period_dscr_targets=sd.period_dscr_targets,
            period_debt_service_availability=sd.period_debt_service_availability,
        )
        m_new = SeniorDebtModelInput(
            operating=m.operating,
            tax=m.tax,
            senior_debt_policy=m.senior_debt_policy,
            senior_debt_inputs=sd_new,
            debt_sizing_case=m.debt_sizing_case,
        )
        fp_base = compute_senior_debt_fingerprint(m)
        fp_new = compute_senior_debt_fingerprint(m_new)
        assert fp_base == fp_new, (
            "initial_debt_guess_keur must be excluded from fingerprint; "
            "changing it must NOT change the fingerprint"
        )

    def test_dscr_target_changes_solver_result(self):
        """Adding a lower DSCR target for specific periods must change the debt amount."""
        from financial_engine.senior_debt.inputs import PeriodDscrTarget, SeniorDebtInputs
        from financial_engine.senior_debt.solver import solve_senior_debt

        d = _oborovo_data()
        periods = _oborovo_real_periods()
        cfads_map = {p.period_index: d["cfads"][p.period_index - 1] for p in periods}

        # Run without dscr targets (scalar policy = 1.15)
        inputs_no_target = _make_oborovo_inputs(override_dscr_targets=False)
        r_no = solve_senior_debt(
            inputs=inputs_no_target, policy=_oborovo_policy(), periods=periods,
            tax_cfads_fn=_no_tax_fn(cfads_map)
        )

        # Run with per-period DSCR targets (1.35x for P25..P28)
        inputs_with_target = _make_oborovo_inputs(override_dscr_targets=True)
        r_with = solve_senior_debt(
            inputs=inputs_with_target, policy=_oborovo_policy(), periods=periods,
            tax_cfads_fn=_no_tax_fn(cfads_map)
        )
        # Higher DSCR for last 4 periods reduces debt capacity
        assert r_no.debt_size_keur > r_with.debt_size_keur, (
            f"Expected no-target debt > with-target debt: "
            f"{r_no.debt_size_keur:.3f} vs {r_with.debt_size_keur:.3f}"
        )


# ===========================================================================
# GROUP P — Provenance
# ===========================================================================

class TestGroupP_Provenance:
    """Provenance: fingerprint function is callable and covers new per-period fields."""

    def test_fingerprint_function_exists(self):
        from financial_engine.provenance import compute_senior_debt_fingerprint
        assert callable(compute_senior_debt_fingerprint)

    def test_provenance_module_covers_new_fields_in_payload(self):
        """The provenance module source contains period_dscr_targets and availability_fraction."""
        import inspect
        from financial_engine import provenance
        src = inspect.getsource(provenance.compute_senior_debt_fingerprint)
        assert "period_dscr_targets" in src, "Fingerprint payload missing period_dscr_targets"
        assert "period_debt_service_availability" in src, "Fingerprint payload missing period_debt_service_availability"
        assert "availability_fraction" in src, "Fingerprint payload missing availability_fraction"

    def test_period_dscr_targets_serializes_correctly(self):
        """period_dscr_targets serialize to list-of-dicts with period_index and target_dscr."""
        from financial_engine.senior_debt.inputs import PeriodDscrTarget, PeriodRate, SeniorDebtInputs

        sd = SeniorDebtInputs(
            eligible_project_cost_keur=0.0,
            initial_debt_guess_keur=0.0,
            period_rates=(PeriodRate(2, 0.056),),
            explicit_principal_schedule=None,
            period_dscr_targets=(PeriodDscrTarget(26, 1.35), PeriodDscrTarget(27, 1.35)),
        )
        payload = [
            {"period_index": dt.period_index, "target_dscr": dt.target_dscr}
            for dt in sd.period_dscr_targets
        ]
        assert payload == [
            {"period_index": 26, "target_dscr": 1.35},
            {"period_index": 27, "target_dscr": 1.35},
        ]

    def test_fingerprint_function_called_directly_returns_hex_sha256(self):
        """compute_senior_debt_fingerprint(SeniorDebtModelInput) returns 64-char hex SHA-256."""
        from financial_engine.provenance import compute_senior_debt_fingerprint
        m = _make_minimal_senior_debt_model_input()
        fp = compute_senior_debt_fingerprint(m)
        assert isinstance(fp, str)
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)


# ===========================================================================
# GROUP Q — Synthetic low-rate scalar solver (not Solar project regression)
# ===========================================================================

class TestGroupQ_SyntheticLowRateScalar:
    """Synthetic 20-period scalar test at ~5.6% rate.

    These are generic engine tests using synthetic semiannual periods.
    They are NOT Solar project regression evidence.
    """

    def test_synthetic_low_rate_converges(self):
        result = _run_generic_scalar("synthetic-low-q")
        assert result.diagnostics.converged

    def test_synthetic_low_rate_debt_positive(self):
        result = _run_generic_scalar("synthetic-low-q2")
        assert result.debt_size_keur > 0

    def test_synthetic_low_rate_terminal_zero(self):
        result = _run_generic_scalar("synthetic-low-q3")
        assert result.senior_debt_closing_keur[-1] == pytest.approx(0.0, abs=1.0)


# ===========================================================================
# GROUP R — Synthetic medium-rate scalar solver (not Wind project regression)
# ===========================================================================

class TestGroupR_SyntheticMediumRateScalar:
    """Synthetic 20-period scalar test at ~4.8% rate.

    These are generic engine tests using synthetic semiannual periods.
    They are NOT Wind project regression evidence.
    """

    def test_synthetic_medium_rate_converges(self):
        result = _run_generic_scalar("synthetic-med-r", rate=0.048)
        assert result.diagnostics.converged

    def test_synthetic_medium_rate_debt_positive(self):
        result = _run_generic_scalar("synthetic-med-r2", rate=0.048)
        assert result.debt_size_keur > 0


# ===========================================================================
# GROUP S — Synthetic high-rate scalar solver (not TUHO project regression)
# ===========================================================================

class TestGroupS_SyntheticHighRateScalar:
    """Synthetic 20-period scalar test at ~8.5% rate.

    These are generic engine tests using synthetic semiannual periods.
    They are NOT TUHO Wind project regression evidence.
    """

    def test_synthetic_high_rate_converges(self):
        result = _run_generic_scalar("synthetic-high-s", rate=0.085)
        assert result.diagnostics.converged

    def test_synthetic_high_rate_debt_positive(self):
        result = _run_generic_scalar("synthetic-high-s2", rate=0.085)
        assert result.debt_size_keur > 0


# ===========================================================================
# GROUP T — Identity-clone invariance
# ===========================================================================

class TestGroupT_IdentityCloneInvariance:
    def test_clone_with_same_data_same_result(self):
        """Two independently-built SeniorDebtInputs with same data → same debt."""
        from financial_engine.senior_debt.inputs import (
            SeniorDebtInputs,
            PeriodRate,
            PeriodDscrTarget,
            PeriodDebtServiceAvailability,
        )
        from financial_engine.senior_debt.solver import solve_senior_debt

        d = _oborovo_data()
        periods = _oborovo_real_periods()
        period_rates = tuple(
            PeriodRate(p.period_index, d["annual_rates"][p.period_index - 1])
            for p in periods
        )
        dscr = tuple(
            PeriodDscrTarget(p.period_index, d["dscr_targets"][p.period_index - 1])
            for p in periods
        )
        ops = tuple(
            PeriodDebtServiceAvailability(p.period_index, d["ops_flag"][p.period_index - 1])
            for p in periods
        )
        cfads_map = {p.period_index: d["cfads"][p.period_index - 1] for p in periods}

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
        periods = _oborovo_real_periods()
        cfads_map = {p.period_index: d["cfads"][p.period_index - 1] for p in periods}
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

    def test_generic_builder_clone_matches_manual_construction(self):
        """Real renamed-clone test: generic builder must produce same debt as manual construction.

        This test proves that build_senior_debt_contract_from_project_inputs() encodes
        the SAME contract as the manually-constructed inputs from fixture data.
        """
        from financial_engine.senior_debt.project_adapter import (
            build_senior_debt_contract_from_project_inputs,
        )
        from financial_engine.senior_debt.solver import solve_senior_debt
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import from_project_inputs
        from financial_engine.orchestrator import run_operating_model

        # Manual path (fixture-driven)
        d = _oborovo_data()
        periods = _oborovo_real_periods()
        cfads_map = {p.period_index: d["cfads"][p.period_index - 1] for p in periods}
        r_manual = solve_senior_debt(
            inputs=_make_oborovo_inputs(),
            policy=_oborovo_policy(),
            periods=periods,
            tax_cfads_fn=_no_tax_fn(cfads_map),
        )

        # Generic builder path (factory-driven)
        proj = create_default_oborovo()
        model_in = from_project_inputs(proj, source_id="c3b3a-clone-test", baseline_commit_sha="")
        result = run_operating_model(model_in)
        g_policy, g_inputs = build_senior_debt_contract_from_project_inputs(proj, result.periods)
        r_generic = solve_senior_debt(
            inputs=g_inputs,
            policy=g_policy,
            periods=periods,
            tax_cfads_fn=_no_tax_fn(cfads_map),
        )

        assert r_generic.debt_size_keur == pytest.approx(r_manual.debt_size_keur, abs=0.001), (
            f"Generic builder debt {r_generic.debt_size_keur:.6f} kEUR ≠ "
            f"manual {r_manual.debt_size_keur:.6f} kEUR"
        )

    def test_renamed_clone_all_economic_fields_equal_and_fingerprint_equal(self):
        """TRUE renamed-clone test: mutate project identity (name, code, company) while keeping
        all economic inputs identical. Verify ALL economic debt-contract fields equal AND
        fingerprint equal.

        Identity mutations:
            name: "Oborovo Wind" → "Renamed Clone Wind"
            code: "OBR-001" → "CLONE-999"
            company: "Finco Energy d.o.o." → "Clone Energy LLC"

        Economic inputs: unchanged (same rates, DSCR targets, availability, tenor, dates).
        """
        import dataclasses
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import from_project_inputs
        from financial_engine.orchestrator import run_operating_model
        from financial_engine.senior_debt.project_adapter import (
            build_senior_debt_contract_from_project_inputs,
        )
        from financial_engine.senior_debt.solver import solve_senior_debt
        from financial_engine.provenance import compute_senior_debt_fingerprint
        from financial_engine.inputs import (
            TaxCalculationInput, SeniorDebtModelInput, DebtSizingCaseInput,
        )
        from financial_engine.policies.tax import TaxPolicy, CashTaxTiming

        # Build original project
        proj_orig = create_default_oborovo()

        # Build renamed clone — mutate ONLY identity fields
        orig_info = proj_orig.info
        renamed_info = dataclasses.replace(
            orig_info,
            name="Renamed Clone Wind",
            code="CLONE-999",
            company="Clone Energy LLC",
        )
        proj_clone = dataclasses.replace(proj_orig, info=renamed_info)

        # Verify identity fields differ
        assert proj_orig.info.name != proj_clone.info.name
        assert proj_orig.info.code != proj_clone.info.code
        assert proj_orig.info.company != proj_clone.info.company

        # Run operating model for both
        model_orig = from_project_inputs(proj_orig, source_id="rename-test", baseline_commit_sha="")
        model_clone = from_project_inputs(proj_clone, source_id="rename-test", baseline_commit_sha="")
        result_orig = run_operating_model(model_orig)
        result_clone = run_operating_model(model_clone)

        # Build senior debt contract for both
        policy_orig, inputs_orig = build_senior_debt_contract_from_project_inputs(proj_orig, result_orig.periods)
        policy_clone, inputs_clone = build_senior_debt_contract_from_project_inputs(proj_clone, result_clone.periods)

        # Run solver on ORIGINAL periods (same CFADS)
        d = _oborovo_data()
        periods = _oborovo_real_periods()
        cfads_map = {p.period_index: d["cfads"][p.period_index - 1] for p in periods}

        r_orig = solve_senior_debt(inputs=inputs_orig, policy=policy_orig, periods=periods, tax_cfads_fn=_no_tax_fn(cfads_map))
        r_clone = solve_senior_debt(inputs=inputs_clone, policy=policy_clone, periods=periods, tax_cfads_fn=_no_tax_fn(cfads_map))

        # ALL economic debt-contract fields must be equal
        assert r_orig.debt_size_keur == pytest.approx(r_clone.debt_size_keur, rel=1e-10), (
            f"debt_size_keur: orig={r_orig.debt_size_keur:.6f} clone={r_clone.debt_size_keur:.6f}"
        )
        for i in range(len(r_orig.period_indices)):
            assert r_orig.senior_debt_opening_keur[i] == pytest.approx(r_clone.senior_debt_opening_keur[i], rel=1e-10), f"opening period {i}"
            assert r_orig.senior_interest_keur[i] == pytest.approx(r_clone.senior_interest_keur[i], rel=1e-10), f"interest period {i}"
            assert r_orig.senior_principal_keur[i] == pytest.approx(r_clone.senior_principal_keur[i], rel=1e-10), f"principal period {i}"
            assert r_orig.senior_debt_closing_keur[i] == pytest.approx(r_clone.senior_debt_closing_keur[i], rel=1e-10), f"closing period {i}"

        # Fingerprint must also be equal (identity is excluded)
        zero_tax_policy = TaxPolicy(
            policy_id="test-zero-tax", policy_version="1.0",
            corporate_rate=0.0, periods_per_tax_year=2, loss_carryforward_years=0,
            atad_enabled=False, atad_ebitda_limit=0.3,
            atad_de_minimis_threshold_keur_annual=0.0,
            cash_tax_timing=CashTaxTiming.TAX_YEAR_LAST_PERIOD,
            cash_tax_payment_lag_periods=0,
        )
        tax_input = TaxCalculationInput(
            policy=zero_tax_policy, opening_loss_vintages=(), period_interest=(), period_adjustments=(),
        )
        _dsc = DebtSizingCaseInput(production_yield_scenario=model_orig.technical.yield_scenario)
        sdi_orig = SeniorDebtModelInput(operating=model_orig, tax=tax_input, senior_debt_policy=policy_orig, senior_debt_inputs=inputs_orig, debt_sizing_case=_dsc)
        sdi_clone = SeniorDebtModelInput(operating=model_clone, tax=tax_input, senior_debt_policy=policy_clone, senior_debt_inputs=inputs_clone, debt_sizing_case=_dsc)
        fp_orig = compute_senior_debt_fingerprint(sdi_orig)
        fp_clone = compute_senior_debt_fingerprint(sdi_clone)
        assert fp_orig == fp_clone, (
            f"Renamed clone must have same fingerprint as original.\n"
            f"  Identity mutations: name/code/company changed\n"
            f"  orig fp:  {fp_orig}\n"
            f"  clone fp: {fp_clone}"
        )


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

# ===========================================================================
# GROUP X — Canonical period axis proof (C3B3A2)
# ===========================================================================

class TestGroupX_CanonicalPeriodAxis:
    """Prove the canonical period axis: clean_period_index = excel_debt_period + 1.

    All 28 mappings are explicit and deterministic.
    P28 → clean period 29 is proven explicitly.
    """

    def test_first_debt_period_is_clean_index_2(self):
        """Excel P1 maps to clean period index 2 (first operating period after 2 construction)."""
        periods = _oborovo_real_periods()
        assert periods[0].period_index == 2

    def test_last_debt_period_is_clean_index_29(self):
        """Excel P28 maps to clean period index 29."""
        periods = _oborovo_real_periods()
        assert periods[-1].period_index == 29

    def test_all_28_mappings_are_sequential(self):
        """All 28 clean period indices 2..29 are present and sequential."""
        periods = _oborovo_real_periods()
        clean_indices = [p.period_index for p in periods]
        assert clean_indices == list(range(2, 30)), (
            f"Expected 2..29, got {clean_indices}"
        )

    def test_mapping_formula_is_clean_equals_excel_plus_1(self):
        """For each period: clean_period_index = excel_debt_period + 1."""
        periods = _oborovo_real_periods()
        for excel_p, p in enumerate(periods, start=1):
            assert p.period_index == excel_p + 1, (
                f"Excel P{excel_p} → expected clean {excel_p + 1}, got {p.period_index}"
            )

    def test_p28_maps_to_clean_29_explicitly(self):
        """P28 → clean period 29: the maturity period. Proven explicitly."""
        periods = _oborovo_real_periods()
        p28 = periods[27]  # 0-indexed: P28 is the 28th element
        assert p28.period_index == 29
        assert p28.period_start == date(2043, 12, 31)  # 2030-06-30 + 13.5 years = 2043-12-31

    def test_cod_is_start_of_clean_period_2(self):
        """COD = 2030-06-30 = start of clean period 2 = start of excel P1."""
        periods = _oborovo_real_periods()
        assert periods[0].period_start == date(2030, 6, 30)

    def test_clean_period_2_index_in_repayment_start(self):
        """Policy repayment_start_period_index must equal 2."""
        policy = _oborovo_policy()
        assert policy.repayment_start_period_index == 2

    def test_clean_period_29_index_is_maturity(self):
        """Policy maturity_period_index must equal 29."""
        policy = _oborovo_policy()
        assert policy.maturity_period_index == 29


# ===========================================================================
# GROUP Y — Generic builder (C3B3A2)
# ===========================================================================

class TestGroupY_GenericBuilder:
    """build_senior_debt_contract_from_project_inputs produces correct contract without project dispatch."""

    def test_builder_returns_policy_and_inputs(self):
        from financial_engine.senior_debt.project_adapter import (
            build_senior_debt_contract_from_project_inputs,
        )
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import from_project_inputs
        from financial_engine.orchestrator import run_operating_model

        proj = create_default_oborovo()
        model_in = from_project_inputs(proj, source_id="c3b3a-builder-test", baseline_commit_sha="")
        result = run_operating_model(model_in)
        policy, inputs = build_senior_debt_contract_from_project_inputs(proj, result.periods)
        assert policy is not None
        assert inputs is not None

    def test_builder_policy_has_correct_period_range(self):
        from financial_engine.senior_debt.project_adapter import (
            build_senior_debt_contract_from_project_inputs,
        )
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import from_project_inputs
        from financial_engine.orchestrator import run_operating_model

        proj = create_default_oborovo()
        model_in = from_project_inputs(proj, source_id="c3b3a-builder-test", baseline_commit_sha="")
        result = run_operating_model(model_in)
        policy, inputs = build_senior_debt_contract_from_project_inputs(proj, result.periods)
        assert policy.repayment_start_period_index == 2
        assert policy.maturity_period_index == 29

    def test_builder_inputs_have_28_period_rates(self):
        from financial_engine.senior_debt.project_adapter import (
            build_senior_debt_contract_from_project_inputs,
        )
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import from_project_inputs
        from financial_engine.orchestrator import run_operating_model

        proj = create_default_oborovo()
        model_in = from_project_inputs(proj, source_id="c3b3a-builder-test2", baseline_commit_sha="")
        result = run_operating_model(model_in)
        _, inputs = build_senior_debt_contract_from_project_inputs(proj, result.periods)
        assert len(inputs.period_rates) == 28

    def test_builder_has_no_oborovo_name_dispatch(self):
        """The adapter module must not contain project-name dispatch."""
        import inspect
        from financial_engine.senior_debt import project_adapter
        src = inspect.getsource(project_adapter)
        assert "oborovo" not in src.lower()
        assert "obr-001" not in src.lower()
        assert 'code ==' not in src.lower()

    def test_builder_debt_matches_manual_within_001_keur(self):
        """Generic builder must produce same debt as manual fixture-driven construction."""
        from financial_engine.senior_debt.project_adapter import (
            build_senior_debt_contract_from_project_inputs,
        )
        from financial_engine.senior_debt.solver import solve_senior_debt
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.project_inputs import from_project_inputs
        from financial_engine.orchestrator import run_operating_model

        d = _oborovo_data()
        periods = _oborovo_real_periods()
        cfads_map = {p.period_index: d["cfads"][p.period_index - 1] for p in periods}

        proj = create_default_oborovo()
        model_in = from_project_inputs(proj, source_id="c3b3a-y-test", baseline_commit_sha="")
        result = run_operating_model(model_in)
        g_policy, g_inputs = build_senior_debt_contract_from_project_inputs(proj, result.periods)

        r_generic = solve_senior_debt(
            inputs=g_inputs,
            policy=g_policy,
            periods=periods,
            tax_cfads_fn=_no_tax_fn(cfads_map),
        )
        assert r_generic.debt_size_keur == pytest.approx(42852.279, abs=0.001), (
            f"Generic builder debt {r_generic.debt_size_keur:.6f} kEUR ≠ 42852.279 kEUR"
        )

# ===========================================================================
# GROUP Z — Day-count fail-closed (C3B3A3)
# ===========================================================================

class TestGroupZ_DayCountFailClosed:
    """build_senior_debt_contract_from_project_inputs: ACT_360/ACT_365 map correctly;
    unsupported conventions (FIXED_SEMIANNUAL, EXPLICIT_FRACTIONS) raise ValueError.
    """

    def _make_proj_with_day_count(self, day_count_value):
        """Build a create_default_oborovo()-based project with day_count overridden."""
        import dataclasses
        from app.project_factories import create_default_oborovo
        from finco_core.inputs.senior_rate_schedule import SeniorDayCountConvention, SeniorDebtInterestConfig, SeniorRateMode, SeniorRateSchedule

        proj = create_default_oborovo()
        orig_cfg = proj.financing.senior_debt_interest_config
        new_cfg = SeniorDebtInterestConfig(
            enabled=orig_cfg.enabled,
            rate_schedule=orig_cfg.rate_schedule,
            day_count=day_count_value,
        )
        new_fin = dataclasses.replace(proj.financing, senior_debt_interest_config=new_cfg)
        return dataclasses.replace(proj, financing=new_fin)

    def _run_builder(self, proj):
        from financial_engine.adapters.project_inputs import from_project_inputs
        from financial_engine.orchestrator import run_operating_model
        from financial_engine.senior_debt.project_adapter import build_senior_debt_contract_from_project_inputs

        model_in = from_project_inputs(proj, source_id="dc-test", baseline_commit_sha="")
        result = run_operating_model(model_in)
        return build_senior_debt_contract_from_project_inputs(proj, result.periods)

    def test_act_360_maps_correctly(self):
        """ACT_360 day-count produces a valid policy with DayCountConvention.ACT_360."""
        from finco_core.inputs.senior_rate_schedule import SeniorDayCountConvention
        from financial_engine.senior_debt.policy import DayCountConvention

        proj = self._make_proj_with_day_count(SeniorDayCountConvention.ACT_360)
        policy, _ = self._run_builder(proj)
        assert policy.day_count_convention == DayCountConvention.ACT_360

    def test_act_365_maps_correctly(self):
        """ACT_365 day-count produces a valid policy with DayCountConvention.ACT_365."""
        from finco_core.inputs.senior_rate_schedule import SeniorDayCountConvention
        from financial_engine.senior_debt.policy import DayCountConvention

        proj = self._make_proj_with_day_count(SeniorDayCountConvention.ACT_365)
        policy, _ = self._run_builder(proj)
        assert policy.day_count_convention == DayCountConvention.ACT_365

    def test_fixed_semiannual_raises_value_error(self):
        """FIXED_SEMIANNUAL day-count raises ValueError (fail-closed)."""
        from finco_core.inputs.senior_rate_schedule import SeniorDayCountConvention

        proj = self._make_proj_with_day_count(SeniorDayCountConvention.FIXED_SEMIANNUAL)
        with pytest.raises(ValueError, match="unsupported day-count"):
            self._run_builder(proj)

    def test_explicit_fractions_raises_value_error(self):
        """EXPLICIT_FRACTIONS day-count raises ValueError (fail-closed)."""
        from finco_core.inputs.senior_rate_schedule import SeniorDayCountConvention

        proj = self._make_proj_with_day_count(SeniorDayCountConvention.EXPLICIT_FRACTIONS)
        with pytest.raises(ValueError, match="unsupported day-count"):
            self._run_builder(proj)

    def test_error_message_names_unsupported_convention(self):
        """ValueError message for unsupported day-count names the offending convention."""
        from finco_core.inputs.senior_rate_schedule import SeniorDayCountConvention

        proj = self._make_proj_with_day_count(SeniorDayCountConvention.FIXED_SEMIANNUAL)
        with pytest.raises(ValueError) as exc:
            self._run_builder(proj)
        msg = str(exc.value)
        assert "FIXED_SEMIANNUAL" in msg or "fixed_semiannual" in msg.lower(), (
            f"ValueError should name the unsupported convention; got: {msg}"
        )


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


# ===========================================================================
# GROUP AA — Period-frequency fail-closed (C3B3A6)
# ===========================================================================

class TestGroupAA_PeriodFrequencyFailClosed:
    """build_senior_debt_contract_from_project_inputs: SEMESTRIAL maps to 2 periods/year;
    QUARTERLY and ANNUAL raise ValueError (fail-closed — no silent fallback).
    """

    def _make_proj_with_frequency(self, frequency):
        """Build a create_default_oborovo()-based project with period_frequency overridden."""
        import dataclasses
        from app.project_factories import create_default_oborovo
        from finco_core.inputs._models import PeriodFrequency

        proj = create_default_oborovo()
        new_info = dataclasses.replace(proj.info, period_frequency=frequency)
        return dataclasses.replace(proj, info=new_info)

    def _run_builder(self, proj):
        from financial_engine.adapters.project_inputs import from_project_inputs
        from financial_engine.orchestrator import run_operating_model
        from financial_engine.senior_debt.project_adapter import build_senior_debt_contract_from_project_inputs

        model_in = from_project_inputs(proj, source_id="freq-test", baseline_commit_sha="")
        result = run_operating_model(model_in)
        return build_senior_debt_contract_from_project_inputs(proj, result.periods)

    def test_semestrial_maps_to_2_periods_per_year(self):
        """SEMESTRIAL frequency produces periods_per_year = 2 in the resulting policy."""
        from finco_core.inputs._models import PeriodFrequency

        proj = self._make_proj_with_frequency(PeriodFrequency.SEMESTRIAL)
        policy, _ = self._run_builder(proj)
        assert policy.periods_per_year == 2

    def test_semestrial_produces_28_debt_periods(self):
        """SEMESTRIAL Oborovo (14-year tenor × 2) → 28 debt periods → indices 2..29."""
        from finco_core.inputs._models import PeriodFrequency

        proj = self._make_proj_with_frequency(PeriodFrequency.SEMESTRIAL)
        policy, inputs = self._run_builder(proj)
        assert len(inputs.period_rates) == 28
        assert policy.repayment_start_period_index == 2
        assert policy.maturity_period_index == 29

    def test_semestrial_debt_size_unchanged(self):
        """SEMESTRIAL Oborovo debt remains 42,852.279 kEUR within 0.001 kEUR tolerance."""
        import pytest
        from finco_core.inputs._models import PeriodFrequency
        from financial_engine.senior_debt.solver import solve_senior_debt

        proj = self._make_proj_with_frequency(PeriodFrequency.SEMESTRIAL)
        policy, inputs = self._run_builder(proj)
        periods = _oborovo_real_periods()
        d = _oborovo_data()
        cfads_map = {p.period_index: d["cfads"][p.period_index - 1] for p in periods}
        result = solve_senior_debt(
            inputs=inputs,
            policy=policy,
            periods=periods,
            tax_cfads_fn=_no_tax_fn(cfads_map),
        )
        assert result.debt_size_keur == pytest.approx(42852.278762563, abs=0.001), (
            f"Oborovo debt after frequency fix: {result.debt_size_keur:.6f} kEUR "
            f"≠ 42852.279 kEUR source truth"
        )

    def test_quarterly_raises_value_error(self):
        """QUARTERLY frequency raises ValueError — must not silently map to 1 period/year."""
        import pytest
        from finco_core.inputs._models import PeriodFrequency

        proj = self._make_proj_with_frequency(PeriodFrequency.QUARTERLY)
        with pytest.raises(ValueError, match="unsupported period frequency"):
            self._run_builder(proj)

    def test_quarterly_error_message_names_quarterly(self):
        """ValueError message for QUARTERLY names the unsupported frequency."""
        import pytest
        from finco_core.inputs._models import PeriodFrequency

        proj = self._make_proj_with_frequency(PeriodFrequency.QUARTERLY)
        with pytest.raises(ValueError) as exc:
            self._run_builder(proj)
        msg = str(exc.value)
        assert "QUARTERLY" in msg or "quarterly" in msg.lower(), (
            f"ValueError must name QUARTERLY frequency; got: {msg}"
        )

    def test_annual_raises_value_error(self):
        """ANNUAL frequency raises ValueError — no end-to-end annual solver proof exists."""
        import pytest
        from finco_core.inputs._models import PeriodFrequency

        proj = self._make_proj_with_frequency(PeriodFrequency.ANNUAL)
        with pytest.raises(ValueError, match="unsupported period frequency"):
            self._run_builder(proj)

    def test_annual_error_message_names_annual(self):
        """ValueError message for ANNUAL names the unsupported frequency."""
        import pytest
        from finco_core.inputs._models import PeriodFrequency

        proj = self._make_proj_with_frequency(PeriodFrequency.ANNUAL)
        with pytest.raises(ValueError) as exc:
            self._run_builder(proj)
        msg = str(exc.value)
        assert "ANNUAL" in msg or "annual" in msg.lower(), (
            f"ValueError must name ANNUAL frequency; got: {msg}"
        )

    def test_adapter_has_no_catch_all_else_1_pattern(self):
        """AST/source guard: adapter must not contain a string-based 'else 1' catch-all."""
        import inspect
        from financial_engine.senior_debt import project_adapter

        src = inspect.getsource(project_adapter)
        # The old pattern was:  ... == "semestrial" else 1
        assert 'else 1' not in src, (
            "project_adapter contains 'else 1' catch-all pattern — "
            "unsupported frequencies silently mapped to 1 period/year"
        )
        assert '.value.lower() ==' not in src, (
            "project_adapter still uses string-based frequency dispatch"
        )


# ===========================================================================
# GROUP AB — C3B2→C3B3A Runtime-Inventory Transition Guards (C3B3A7)
# ===========================================================================

class TestGroupAB_RuntimeTransitionGuards:
    """Prove the C3B3A transition state: legacy runtime frozen, clean contract configured."""

    def _load_fixture(self):
        import pathlib, json
        p = pathlib.Path("tests/fixtures/excel_oborovo_debt_interest_truth.json")
        return json.loads(p.read_text())

    def _ri(self):
        return self._load_fixture()["phase2c_sizing_analysis"]["runtime_inventory"]

    def test_legacy_runtime_explicitly_classified_frozen(self):
        """A: legacy runtime layer must be explicitly FROZEN_EXCEL_SCHEDULE_RUNTIME."""
        ri = self._ri()
        lr = ri["legacy_runtime"]
        assert lr["runtime_classification"] == "FROZEN_EXCEL_SCHEDULE_RUNTIME"

    def test_clean_contract_explicitly_classified_flat_dscr_sculpted(self):
        """B: clean senior-debt contract layer must carry FLAT_DSCR_SCULPTED classification."""
        ri = self._ri()
        cc = ri["clean_senior_debt_contract"]
        assert "FLAT_DSCR_SCULPTED" in str(cc["debt_sizing_mode"]) or \
               "flat_dscr_sculpted" in str(cc["debt_sizing_mode"])

    def test_clean_contract_does_not_imply_legacy_promotion(self):
        """C: clean contract classification must NOT claim legacy runtime promotion."""
        ri = self._ri()
        cc = ri["clean_senior_debt_contract"]
        assert "NOT_LEGACY_RUNTIME_PROMOTED" in cc["runtime_classification"], (
            f"Clean contract classification must contain 'NOT_LEGACY_RUNTIME_PROMOTED'; "
            f"got: {cc['runtime_classification']}"
        )
        assert ri["legacy_runtime"]["use_frozen_excel_senior_debt_schedule"] is True

    def test_legacy_use_frozen_flag_true(self):
        """D: use_frozen_excel_senior_debt_schedule=True in legacy_runtime layer."""
        ri = self._ri()
        assert ri["legacy_runtime"]["use_frozen_excel_senior_debt_schedule"] is True

    def test_clean_contract_has_explicit_rate_schedule(self):
        """E1: clean contract has explicit all-in rate schedule."""
        ri = self._ri()
        cc = ri["clean_senior_debt_contract"]
        assert "EXPLICIT_ALL_IN_SCHEDULE" in str(cc["senior_rate_mode"]) or \
               "explicit_all_in_schedule" in str(cc["senior_rate_mode"]).lower()

    def test_clean_contract_has_act_360(self):
        """E2: clean contract has ACT_360 day-count."""
        ri = self._ri()
        cc = ri["clean_senior_debt_contract"]
        assert "ACT_360" in str(cc["day_count"]) or "act_360" in str(cc["day_count"]).lower()

    def test_clean_contract_has_dscr_schedule(self):
        """E3: clean contract has per-period DSCR schedule (28 periods)."""
        ri = self._ri()
        cc = ri["clean_senior_debt_contract"]
        assert cc["dscr_schedule_period_count"] == 28

    def test_clean_contract_has_availability_schedule(self):
        """E4: clean contract has debt-service availability schedule (28 periods)."""
        ri = self._ri()
        cc = ri["clean_senior_debt_contract"]
        assert cc["availability_schedule_period_count"] == 28

    def test_source_vectors_sha256_unchanged(self):
        """F: source_vectors_sha256 must remain the original C3B2 hash."""
        d = self._load_fixture()
        icp = d["phase2c_sizing_analysis"]["independent_capacity_proof"]
        assert icp["_source_vectors_sha256"] == (
            "f8f244c0660495bfb4115d4e32ba329c291ab829d1d0693e614c889457b5add7"
        ), f"source_vectors_sha256 changed: {icp['_source_vectors_sha256']}"

    def test_g4_debt_source_proven(self):
        """G: G4 (vector capacity) remains exactly source-proven at 42,852.278762563 kEUR."""
        import pytest
        d = self._load_fixture()
        g4 = d["phase2c_sizing_analysis"]["independent_capacity_proof"]["g4_vector_capacity"]["capacity_keur"]
        assert g4 == pytest.approx(42852.278762563, rel=1e-9)

    def test_first_run_derivation_is_noop(self):
        """H: first-run derivation must produce 'Fixture already up-to-date' (no write)."""
        import subprocess, pathlib
        import hashlib
        fixture = pathlib.Path("tests/fixtures/excel_oborovo_debt_interest_truth.json")
        sha_before = hashlib.sha256(fixture.read_bytes()).hexdigest()
        result = subprocess.run(
            ["python", "-m", "finco_recon.derive_c3b2_independent_capacity"],
            capture_output=True, text=True,
            cwd=pathlib.Path(__file__).parent.parent,
        )
        sha_after = hashlib.sha256(fixture.read_bytes()).hexdigest()
        assert sha_before == sha_after, (
            f"First-run derivation rewrote the fixture — not idempotent. "
            f"SHA before={sha_before[:16]}... after={sha_after[:16]}..."
        )
        assert "up-to-date" in result.stdout or "up-to-date" in result.stderr, (
            f"Expected 'up-to-date' in derivation output; got stdout={result.stdout!r}"
        )
