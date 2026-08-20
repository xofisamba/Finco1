from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

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
from finco_core.ebitda import calculate_ebitda_keur
from finco_core.waterfall.waterfall_engine import compute_ebitda_schedule


ROOT = Path(__file__).resolve().parents[1]
SOURCE_LOCK = ROOT / "tests/fixtures/ebitda_source_formula_lock.json"


@pytest.mark.parametrize(
    ("model", "sha256", "cell", "formula"),
    (
        ("tuho", "780779eba4278ccc2b8546a9411ccee24917d388f411ba60c88aa342cb5c727a", "CF!G40", "=G20+G38+G63"),
        ("oborovo", "15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920", "CF!G51", "=G23+G49+G73"),
        ("kupi", "111178fb21109f55df45c0cc1ea108104ac8b6ed60f010ba75b6c498795f5954", "CF!G40", "=G20+G38+G63"),
    ),
)
def test_source_workbook_formula_lock(model, sha256, cell, formula):
    evidence = json.loads(SOURCE_LOCK.read_text(encoding="utf-8"))
    row = evidence["workbooks"][model]
    assert evidence["classification"] == "SOURCE_SIGNED_EBITDA"
    assert row["sha256"] == sha256
    assert row["ebitda"] == {"cell": cell, "formula": formula}
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


def test_no_active_runtime_contains_conflicting_revenue_less_opex_floor():
    pattern = re.compile(r"max\(\s*0(?:\.0)?\s*,\s*(?:rev|revenue)[^\n]*-\s*opex")
    for relative in (
        "app/waterfall_core.py",
        "finco_core/waterfall/cash_flow.py",
        "finco_core/waterfall/waterfall_engine.py",
        "financial_engine/orchestrator.py",
    ):
        assert pattern.search((ROOT / relative).read_text(encoding="utf-8")) is None
