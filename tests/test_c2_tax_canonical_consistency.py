"""C2 — Canonical Tax Consistency regression tests.

Three tax concepts must remain internally consistent across every period:

  1. Displayed tax (P&L accrual)     : WaterfallPeriod.tax_keur
  2. Cash tax (timing-adjusted)      : WaterfallPeriod.corporate_tax_cash_keur
  3. Financial statement tax charge  : IncomeStatementPeriod.tax_keur

Audit aliases must equal their canonical fields:
  - cit_accrual_audit_keur           == tax_keur  (every period)
  - cash_tax_current_period_audit_keur == corporate_tax_cash_keur  (every period)
  - cash_tax_excel_style_h2_diagnostic_keur == r67_excel_style_cash_tax_diagnostic_keur

Annual invariant (H1 + H2 accrual == H2 cash outflow):
  - sum(tax_keur[H1] + tax_keur[H2]) == corporate_tax_cash_keur[H2]  per year

Financial statement consistency:
  - IS.tax_keur == WaterfallPeriod.tax_keur  every period
  - domain/financial_statements/pnl.py cit_accrual reads tax_keur (not removed audit alias)
"""
from __future__ import annotations

import pytest

from app.ui_runner import run_demo_project
from finco_core.financial_statements.income_statement import generate_income_statement


TOLERANCE = 1e-6


def _periods(project_code: str):
    result = run_demo_project(project_code)
    return result.result.periods


@pytest.mark.parametrize("project_code", ["TUHO", "Oborovo"])
def test_cit_accrual_alias_equals_tax_keur(project_code):
    """cit_accrual_audit_keur must equal tax_keur every period."""
    for i, p in enumerate(_periods(project_code)):
        assert p.cit_accrual_audit_keur == pytest.approx(p.tax_keur, abs=TOLERANCE), (
            f"{project_code} period {i}: cit_accrual_audit_keur={p.cit_accrual_audit_keur} "
            f"!= tax_keur={p.tax_keur}"
        )


@pytest.mark.parametrize("project_code", ["TUHO", "Oborovo"])
def test_cash_tax_alias_equals_corporate_tax_cash(project_code):
    """cash_tax_current_period_audit_keur must equal corporate_tax_cash_keur every period."""
    for i, p in enumerate(_periods(project_code)):
        assert p.cash_tax_current_period_audit_keur == pytest.approx(
            p.corporate_tax_cash_keur, abs=TOLERANCE
        ), (
            f"{project_code} period {i}: cash_tax_current_period_audit_keur="
            f"{p.cash_tax_current_period_audit_keur} != corporate_tax_cash_keur={p.corporate_tax_cash_keur}"
        )


@pytest.mark.parametrize("project_code", ["TUHO", "Oborovo"])
def test_r67_alias_equals_canonical(project_code):
    """cash_tax_excel_style_h2_diagnostic_keur must equal r67_excel_style_cash_tax_diagnostic_keur."""
    for i, p in enumerate(_periods(project_code)):
        assert p.cash_tax_excel_style_h2_diagnostic_keur == pytest.approx(
            p.r67_excel_style_cash_tax_diagnostic_keur, abs=TOLERANCE
        ), (
            f"{project_code} period {i}: alias mismatch "
            f"{p.cash_tax_excel_style_h2_diagnostic_keur} vs {p.r67_excel_style_cash_tax_diagnostic_keur}"
        )


@pytest.mark.parametrize("project_code", ["TUHO", "Oborovo"])
def test_annual_cash_tax_equals_sum_of_accruals(project_code):
    """H2 corporate_tax_cash_keur must equal sum of H1+H2 tax_keur accruals for each year."""
    periods = _periods(project_code)
    by_year: dict[int, list] = {}
    for p in periods:
        by_year.setdefault(p.year_index, []).append(p)

    for year, year_periods in by_year.items():
        accrual_sum = sum(p.tax_keur for p in year_periods)
        h2 = [p for p in year_periods if p.period_in_year == 2]
        if not h2:
            continue
        cash_paid = h2[0].corporate_tax_cash_keur
        assert cash_paid == pytest.approx(accrual_sum, abs=1.0), (
            f"{project_code} year {year}: cash_paid={cash_paid:.3f} != "
            f"accrual_sum={accrual_sum:.3f} (H1+H2 tax_keur)"
        )


@pytest.mark.parametrize("project_code", ["TUHO", "Oborovo"])
def test_income_statement_tax_equals_waterfall_tax(project_code):
    """IS tax_keur must equal WaterfallPeriod.tax_keur every period."""
    periods = _periods(project_code)
    is_periods = generate_income_statement(periods)
    for i, (wp, isp) in enumerate(zip(periods, is_periods)):
        assert isp.tax_keur == pytest.approx(wp.tax_keur, abs=TOLERANCE), (
            f"{project_code} period {i}: IS.tax_keur={isp.tax_keur} != wp.tax_keur={wp.tax_keur}"
        )


@pytest.mark.parametrize("project_code", ["TUHO", "Oborovo"])
def test_h1_cash_tax_is_zero(project_code):
    """Cash tax must be zero in all H1 periods (deferred to H2 settlement)."""
    for i, p in enumerate(_periods(project_code)):
        if p.period_in_year == 1:
            assert p.corporate_tax_cash_keur == pytest.approx(0.0, abs=TOLERANCE), (
                f"{project_code} period {i} (H1): corporate_tax_cash_keur={p.corporate_tax_cash_keur} != 0"
            )
