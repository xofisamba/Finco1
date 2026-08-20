from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from financial_engine.cfads import calculate_canonical_cfads
from financial_engine.inputs import TaxCalculationInput
from financial_engine.policies.tax import CashTaxTiming, TaxPolicy
from financial_engine.results import OperatingPeriodResult
from financial_engine.senior_debt.inputs import SeniorDebtInputs
from financial_engine.senior_debt.policy import (
    DayCountConvention,
    SeniorDebtPolicy,
    SeniorDebtSizingMode,
)
from financial_engine.senior_debt.solver import solve_senior_debt
from financial_engine.tax.engine import calculate_tax
from domain.senior_debt_sizing.canonical_wiring import (
    compute_canonical_senior_debt_sizing,
    derive_sizing_cfads_from_ebitda,
)
from domain.senior_debt_sizing.policy import SizingMode
from finco_core.waterfall.waterfall_engine import run_waterfall
from finco_core.ebitda import calculate_ebitda_keur
from finco_core.waterfall.waterfall_engine import compute_ebitda_schedule
from tests.pr5_ebitda_guard import assert_only_approved_pr5_waterfall_diff


ROOT = Path(__file__).resolve().parents[1]
SOURCE_LOCK = ROOT / "tests/fixtures/ebitda_source_formula_lock.json"


@pytest.mark.parametrize(
    ("model", "sha256", "cell", "formula", "local_tax_cell"),
    (
        ("tuho", "780779eba4278ccc2b8546a9411ccee24917d388f411ba60c88aa342cb5c727a", "CF!G40", "=G20+G38+G63", "CF!G63"),
        ("oborovo", "15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920", "CF!G51", "=G23+G49+G73", "CF!G73"),
        ("kupi", "111178fb21109f55df45c0cc1ea108104ac8b6ed60f010ba75b6c498795f5954", "CF!G40", "=G20+G38+G63", "CF!G63"),
    ),
)
def test_source_workbook_formula_lock(model, sha256, cell, formula, local_tax_cell):
    evidence = json.loads(SOURCE_LOCK.read_text(encoding="utf-8"))
    row = evidence["workbooks"][model]
    assert evidence["classification"] == "SOURCE_SIGNED_EBITDA"
    assert row["sha256"] == sha256
    assert row["ebitda"] == {"cell": cell, "formula": formula}
    assert row["local_tax"] == {"cell": local_tax_cell, "formula": "=Macro!G46"}
    assert row["active_local_tax_values_keur"] == [0.0]
    assert row["explicit_ebitda_floor"] is False


@pytest.mark.parametrize(
    ("revenue", "opex", "expected"),
    ((100.0, 150.0, -50.0), (150.0, 150.0, 0.0), (200.0, 150.0, 50.0)),
)
def test_canonical_ebitda_is_signed(revenue, opex, expected):
    assert calculate_ebitda_keur(revenue, opex) == expected


def _negative_operating_period() -> OperatingPeriodResult:
    ebitda = calculate_ebitda_keur(100.0, 150.0)
    return OperatingPeriodResult(
        period_index=1,
        period_start=date(2030, 1, 1),
        period_end=date(2030, 12, 31),
        year_index=1.0,
        period_in_year=1.0,
        is_construction=False,
        is_operation=True,
        is_ppa_active=True,
        days_in_period=364,
        day_fraction=364 / 365.0,
        production_mwh=0.0,
        revenue_keur=100.0,
        opex_keur=150.0,
        ebitda_keur=ebitda,
        book_depreciation_keur=0.0,
        tax_depreciation_keur=0.0,
        ebit_keur=ebitda,
    )


def _tax_policy() -> TaxPolicy:
    return TaxPolicy(
        policy_id="pr5-negative-ebitda",
        policy_version="1.0",
        corporate_rate=0.18,
        periods_per_tax_year=1,
        loss_carryforward_years=5,
        atad_enabled=False,
        atad_ebitda_limit=0.30,
        atad_de_minimis_threshold_keur_annual=3000.0,
        cash_tax_timing=CashTaxTiming.SAME_PERIOD,
    )


def test_negative_ebitda_flows_through_tax_cfads_and_senior_capacity():
    period = _negative_operating_period()
    tax_input = TaxCalculationInput(
        policy=_tax_policy(), opening_loss_vintages=(), period_interest=()
    )
    tax_result = calculate_tax((period,), tax_input)
    cfads = calculate_canonical_cfads((period,), tax_result.period_results)

    assert period.ebitda_keur == -50.0
    assert period.ebit_keur == -50.0
    assert tax_result.annual_results[0].taxable_income_before_lcf_keur == pytest.approx(-50.0)
    assert tax_result.period_results[0].cash_tax_keur == 0.0
    assert cfads[0].cfads_keur == -50.0

    policy = SeniorDebtPolicy(
        policy_id="pr5-negative-ebitda",
        policy_version="1.0",
        sizing_mode=SeniorDebtSizingMode.DSCR_SCULPTED,
        target_dscr=1.20,
        maximum_gearing=None,
        annual_fixed_rate=0.0,
        periods_per_year=1,
        day_count_convention=DayCountConvention.ACT_365,
        repayment_start_period_index=1,
        maturity_period_index=1,
        convergence_tolerance_keur=1e-9,
        convergence_relative_tolerance=1e-9,
        maximum_iterations=10,
        permit_terminal_balloon=False,
    )
    debt = solve_senior_debt(
        inputs=SeniorDebtInputs(
            eligible_project_cost_keur=1000.0,
            initial_debt_guess_keur=100.0,
            period_rates=(),
            explicit_principal_schedule=None,
        ),
        policy=policy,
        periods=(period,),
        tax_cfads_fn=lambda _interest: ({1: cfads[0].cfads_keur}, {1: 0.0}),
    )
    assert debt.debt_size_keur == 0.0
    assert debt.diagnostics.termination_reason == "NO_DEBT_CAPACITY"


class _Period:
    def __init__(self, index: int) -> None:
        self.index = index


def test_construction_neutrality_and_inactive_schedule_use_same_authority():
    periods = [_Period(1), _Period(2)]
    assert compute_ebitda_schedule({1: 0.0, 2: 100.0}, {1: 0.0, 2: 150.0}, periods) == [0.0, -50.0]


def _legacy_period(index: int) -> SimpleNamespace:
    return SimpleNamespace(
        index=index,
        is_operation=True,
        end_date=date(2030 + index, 1, 1),
        year_index=index,
        period_in_year=1,
    )


def _run_legacy_runtime(revenue: list[float], opex: list[float]):
    ebitda = [calculate_ebitda_keur(r, o) for r, o in zip(revenue, opex)]
    periods = [_legacy_period(index) for index in range(1, len(ebitda) + 1)]
    return run_waterfall(
        ebitda_schedule=ebitda,
        revenue_schedule=revenue,
        generation_schedule=[0.0] * len(ebitda),
        depreciation_schedule=[0.0] * len(ebitda),
        opex_schedule=opex,
        periods=periods,
        total_capex=1000.0,
        rate_per_period=0.05,
        tenor_periods=len(ebitda),
        target_dscr=1.20,
        lockup_dscr=1.10,
        tax_rate=0.10,
        dsra_months=0,
        financial_close=date(2030, 1, 1),
    )


def test_legacy_negative_ebitda_keeps_signed_dscr_and_non_negative_capacity():
    result = _run_legacy_runtime([100.0, 200.0, 200.0], [150.0] * 3)
    first = result.periods[0]

    assert first.ebitda_keur == -50.0
    assert first.senior_ds_keur > 0.0
    assert first.dscr == pytest.approx(-50.0 / first.senior_ds_keur)
    assert result.sculpting_result.dscr_schedule[0] == pytest.approx(
        -45.0 / first.senior_ds_keur
    )
    assert result.sculpting_result.debt_keur >= 0.0
    assert all(value >= 0.0 for value in result.sculpting_result.principal_schedule)


def test_legacy_positive_control_is_unchanged():
    result = _run_legacy_runtime([200.0] * 3, [150.0] * 3)
    first = result.periods[0]

    assert first.ebitda_keur == 50.0
    assert result.sculpting_result.debt_keur > 0.0
    assert result.sculpting_result.dscr_schedule[0] == pytest.approx(1.20)


def test_legacy_zero_control_has_no_artificial_debt_capacity():
    result = _run_legacy_runtime([150.0] * 3, [150.0] * 3)

    assert result.total_ebitda_keur == 0.0
    assert result.sculpting_result.debt_keur == 0.0
    assert all(value == 0.0 for value in result.sculpting_result.principal_schedule)


def test_domain_proxy_preserves_sign_and_capacity_boundary_is_non_negative():
    sizing_cfads = derive_sizing_cfads_from_ebitda((-50.0, 0.0, 50.0), 0.10)
    assert sizing_cfads == (-45.0, 0.0, 45.0)

    result = compute_canonical_senior_debt_sizing(
        project_name="generic-control",
        sizing_cfads_keur_by_period=sizing_cfads,
        target_dscr_by_period=(1.20, 1.20, 1.20),
        sizing_mode=SizingMode.EXPLICIT_CFADS,
    )
    assert result.sizing_cfads_keur_by_period == sizing_cfads
    assert result.debt_service_capacity_keur_by_period == (0.0, 0.0, 37.5)


def test_financially_active_ebitda_floor_inventory_is_complete():
    evidence = json.loads(SOURCE_LOCK.read_text(encoding="utf-8"))
    inventory = evidence["floor_inventory"]
    assert set(inventory.values()) <= {
        "EBITDA_AUTHORITY",
        "SIGNED_CFADS_AUTHORITY",
        "NON_NEGATIVE_DEBT_CAPACITY_BOUNDARY",
        "TAX_BOUNDARY",
        "DIAGNOSTIC_ONLY",
        "DEAD / LEGACY_QUARANTINED",
    }
    assert len(inventory) == 17
    assert evidence["unpromoted_component_gap"] == (
        "EBITDA_LOCAL_TAX_COMPONENT_MAPPING_NOT_YET_PROMOTED"
    )


def test_cross_arc_guard_rejects_unrelated_waterfall_change():
    approved = "\n".join(
        (
            "--- a/app/waterfall_core.py",
            "+++ b/app/waterfall_core.py",
            "+from finco_core.ebitda import calculate_ebitda_keur",
            "+",
            "-        ebitda = max(0, rev - opex)",
            "+        ebitda = calculate_ebitda_keur(rev, opex)",
        )
    )
    assert_only_approved_pr5_waterfall_diff(approved)
    with pytest.raises(AssertionError, match="beyond the source-approved"):
        assert_only_approved_pr5_waterfall_diff(approved + "\n+        tax_rate = 0.0")


def test_no_active_runtime_contains_conflicting_revenue_less_opex_floor():
    pattern = re.compile(r"max\(\s*0(?:\.0)?\s*,\s*(?:rev|revenue)[^\n]*-\s*opex")
    for relative in (
        "app/waterfall_core.py",
        "finco_core/waterfall/cash_flow.py",
        "finco_core/waterfall/waterfall_engine.py",
        "financial_engine/orchestrator.py",
        "domain/senior_debt_sizing/canonical_wiring.py",
    ):
        assert pattern.search((ROOT / relative).read_text(encoding="utf-8")) is None
