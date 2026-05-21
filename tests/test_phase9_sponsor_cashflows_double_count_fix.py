"""Phase 9 sponsor cashflow double-count regression tests."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.returns.sponsor_cashflows import build_sponsor_cashflows
from domain.returns.xirr import robust_xirr


def _irr(cashflows: list[float]) -> float:
    dates = [date(2026, 1, 1) + timedelta(days=365 * idx) for idx in range(len(cashflows))]
    result = robust_xirr(cashflows, dates, guess=0.15)
    assert result is not None
    return result


def _run_project(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def test_shl_plus_dividends_no_longer_double_counts_shl_interest():
    cashflows = build_sponsor_cashflows(
        equity_irr_method="shl_plus_dividends",
        share_capital_keur=1_000.0,
        shl_amount_keur=0.0,
        shl_idc_keur=0.0,
        shl_balance_by_period=[100.0, 0.0],
        equity_cf_per_period=[200.0, 250.0],
        shl_interest_paid_per_period=[21.0, 9.0],
        shl_principal_paid_per_period=[0.0, 0.0],
    )

    assert cashflows == pytest.approx([-1_000.0, 200.0, 250.0])
    assert 21.0 not in cashflows[1:]


def test_shl_plus_dividends_no_longer_double_counts_shl_principal():
    cashflows = build_sponsor_cashflows(
        equity_irr_method="shl_plus_dividends",
        share_capital_keur=1_000.0,
        shl_amount_keur=0.0,
        shl_idc_keur=0.0,
        shl_balance_by_period=[100.0, 0.0],
        equity_cf_per_period=[200.0, 250.0],
        shl_interest_paid_per_period=[0.0, 0.0],
        shl_principal_paid_per_period=[75.0, 50.0],
    )

    assert cashflows == pytest.approx([-1_000.0, 200.0, 250.0])
    assert cashflows[1] != pytest.approx(275.0)
    assert cashflows[2] != pytest.approx(300.0)


def test_old_buggy_17_81_percent_inflated_path_no_longer_occurs():
    equity_stream = [200.0] * 10
    shl_interest = [21.0] * 10
    corrected = build_sponsor_cashflows(
        equity_irr_method="shl_plus_dividends",
        share_capital_keur=1_000.0,
        shl_amount_keur=0.0,
        shl_idc_keur=0.0,
        shl_balance_by_period=[100.0] * 10,
        equity_cf_per_period=equity_stream,
        shl_interest_paid_per_period=shl_interest,
        shl_principal_paid_per_period=[0.0] * 10,
    )
    old_buggy = [-1_000.0] + [
        equity + interest for equity, interest in zip(equity_stream, shl_interest)
    ]

    assert _irr(corrected) == pytest.approx(0.15098, abs=0.0001)
    assert _irr(old_buggy) == pytest.approx(0.17808, abs=0.0001)
    assert _irr(corrected) < 0.1781


def test_old_buggy_26_percent_inflated_variant_no_longer_occurs():
    equity_stream = [200.0] * 10
    shl_interest = [90.0] * 10
    corrected = build_sponsor_cashflows(
        equity_irr_method="shl_plus_dividends",
        share_capital_keur=1_000.0,
        shl_amount_keur=0.0,
        shl_idc_keur=0.0,
        shl_balance_by_period=[100.0] * 10,
        equity_cf_per_period=equity_stream,
        shl_interest_paid_per_period=shl_interest,
        shl_principal_paid_per_period=[0.0] * 10,
    )
    old_buggy = [-1_000.0] + [
        equity + interest for equity, interest in zip(equity_stream, shl_interest)
    ]

    assert _irr(old_buggy) == pytest.approx(0.26161, abs=0.0001)
    assert _irr(corrected) < 0.26


def test_corrected_shl_plus_dividends_cashflow_path_remains_stable():
    cashflows = build_sponsor_cashflows(
        equity_irr_method="shl_plus_dividends",
        share_capital_keur=700.0,
        shl_amount_keur=250.0,
        shl_idc_keur=50.0,
        shl_balance_by_period=[100.0, 50.0, 0.0],
        equity_cf_per_period=[80.0, 90.0, 300.0],
        shl_interest_paid_per_period=[12.0, 10.0, 0.0],
        shl_principal_paid_per_period=[0.0, 50.0, 0.0],
    )

    assert cashflows == pytest.approx([-1_000.0, 80.0, 90.0, 300.0])


def test_other_methods_preserve_existing_semantics():
    equity_only = build_sponsor_cashflows(
        equity_irr_method="equity_only",
        share_capital_keur=1_000.0,
        shl_amount_keur=0.0,
        shl_idc_keur=0.0,
        shl_balance_by_period=[0.0],
        equity_cf_per_period=[100.0],
        shl_interest_paid_per_period=[10.0],
        shl_principal_paid_per_period=[20.0],
    )
    shl_interest_only = build_sponsor_cashflows(
        equity_irr_method="shl_interest_only",
        share_capital_keur=1_000.0,
        shl_amount_keur=0.0,
        shl_idc_keur=0.0,
        shl_balance_by_period=[0.0],
        equity_cf_per_period=[130.0],
        shl_interest_paid_per_period=[10.0],
        shl_principal_paid_per_period=[20.0],
    )

    assert equity_only == pytest.approx([-1_000.0, 130.0])
    assert shl_interest_only == pytest.approx([-1_000.0, 130.0])


def test_default_waterfall_outputs_and_project_irr_are_unchanged_by_reporting_fix():
    result_a = _run_project(create_default_tuho_wind1())
    result_b = _run_project(create_default_tuho_wind1())

    assert result_b.project_irr == pytest.approx(result_a.project_irr, abs=0.0000001)
    assert result_b.total_revenue_keur == pytest.approx(result_a.total_revenue_keur, abs=0.0001)
    assert result_b.total_opex_keur == pytest.approx(result_a.total_opex_keur, abs=0.0001)
    assert result_b.total_tax_keur == pytest.approx(result_a.total_tax_keur, abs=0.0001)


def test_distribution_and_shl_balances_are_unchanged():
    result_a = _run_project(create_default_tuho_wind1())
    result_b = _run_project(create_default_tuho_wind1())

    assert [period.distribution_keur for period in result_b.periods] == pytest.approx(
        [period.distribution_keur for period in result_a.periods],
        abs=0.0001,
    )
    assert [period.shl_balance_keur for period in result_b.periods] == pytest.approx(
        [period.shl_balance_keur for period in result_a.periods],
        abs=0.0001,
    )


def test_g20_and_r99_runtime_promotion_remain_blocked():
    project = create_default_tuho_wind1()
    result = _run_project(project)

    assert project.financing.use_tuho_r99_input_engine is False
    assert all(
        not getattr(period, "r99_runtime_source_accepted", False)
        for period in result.periods
    )


def test_oborovo_behavior_is_unchanged():
    result_a = _run_project(create_default_oborovo())
    result_b = _run_project(create_default_oborovo())

    assert result_b.project_irr == pytest.approx(result_a.project_irr, abs=0.0000001)
    assert result_b.equity_irr == pytest.approx(result_a.equity_irr, abs=0.0000001)
    assert result_b.sponsor_irr == pytest.approx(result_a.sponsor_irr, abs=0.0000001)
    assert [period.distribution_keur for period in result_b.periods] == pytest.approx(
        [period.distribution_keur for period in result_a.periods],
        abs=0.0001,
    )
