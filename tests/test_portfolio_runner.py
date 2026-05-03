"""Tests for app/portfolio_runner.py."""
import pytest


def test_portfolio_runner_runs_from_precomputed_results():
    """When project_results are provided, portfolio_runner passes them through."""
    from app.portfolio_runner import run_portfolio_from_inputs
    from domain.portfolio.inputs import PortfolioInputs
    from domain.portfolio.waterfall import run_portfolio_waterfall, PortfolioPeriod
    from domain.waterfall.waterfall_engine import WaterfallResult, WaterfallPeriod
    from datetime import date
    from domain.inputs import FinancingParams
    from app.project_factories import create_default_solar_project, create_default_wind_project

    shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                             senior_tenor_years=10, target_dscr=1.3)
    portfolio = PortfolioInputs(
        projects=(create_default_solar_project(), create_default_wind_project()),
        portfolio_name="Test",
        shared_financing=shared,
    )

    wf_result = WaterfallResult(
        periods=[WaterfallPeriod(
            period=1, date=date(2030, 6, 30), year_index=1, period_in_year=2,
            is_operation=True,
            generation_mwh=1000.0,
            revenue_keur=1000.0, opex_keur=200.0, ebitda_keur=800.0,
            depreciation_keur=100.0,
            interest_senior_keur=80.0, interest_shl_keur=0.0,
            taxable_profit_keur=620.0, tax_keur=50.0,
            cf_after_tax_keur=750.0,
            senior_interest_keur=80.0, senior_principal_keur=20.0, senior_ds_keur=100.0,
            shl_interest_keur=0.0, shl_principal_keur=0.0, shl_service_keur=0.0,
            dsra_contribution_keur=0.0, dsra_balance_keur=0.0,
            mra_contribution_keur=0.0, mra_balance_keur=0.0,
            cf_after_reserves_keur=750.0,
            dscr=1.5, llcr=1.8, plcr=1.5,
            lockup_active=False,
            distribution_keur=600.0, cash_sweep_keur=0.0,
            cum_distribution_keur=600.0,
            cash_balance_keur=150.0,
            shl_balance_keur=0.0, shl_pik_keur=0.0,
            senior_balance_keur=900.0,
        )],
        total_revenue_keur=1000.0, total_opex_keur=200.0,
        total_ebitda_keur=800.0, total_tax_keur=50.0,
        total_senior_ds_keur=100.0, total_shl_service_keur=0.0,
        total_distribution_keur=600.0,
        avg_dscr=1.5, min_dscr=1.5, max_dscr=1.5,
        min_llcr=1.8, min_plcr=1.5, periods_in_lockup=0,
        project_irr=0.08, equity_irr=0.0, sponsor_irr=0.0,
        project_npv=0.0, equity_npv=0.0,
    )

    project_results = (("SOLAR-001", wf_result),)
    result = run_portfolio_from_inputs(portfolio, project_results=project_results)
    assert len(result.periods) == 1
    assert result.total_ebitda_keur == 800.0


def test_portfolio_runner_accepts_explicit_debt_schedule():
    """Explicit portfolio_debt_service_schedule is passed through."""
    from app.portfolio_runner import run_portfolio_from_inputs
    from domain.portfolio.inputs import PortfolioInputs
    from domain.waterfall.waterfall_engine import WaterfallResult, WaterfallPeriod
    from datetime import date
    from domain.inputs import FinancingParams
    from app.project_factories import create_default_solar_project, create_default_wind_project

    shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                             senior_tenor_years=10, target_dscr=1.3)
    portfolio = PortfolioInputs(
        projects=(create_default_solar_project(), create_default_wind_project()),
        portfolio_name="Test2",
        shared_financing=shared,
    )

    wf_result = WaterfallResult(
        periods=[WaterfallPeriod(
            period=1, date=date(2030, 6, 30), year_index=1, period_in_year=2,
            is_operation=True,
            generation_mwh=1000.0,
            revenue_keur=1000.0, opex_keur=200.0, ebitda_keur=800.0,
            depreciation_keur=100.0,
            interest_senior_keur=80.0, interest_shl_keur=0.0,
            taxable_profit_keur=620.0, tax_keur=50.0,
            cf_after_tax_keur=750.0,
            senior_interest_keur=80.0, senior_principal_keur=20.0, senior_ds_keur=100.0,
            shl_interest_keur=0.0, shl_principal_keur=0.0, shl_service_keur=0.0,
            dsra_contribution_keur=0.0, dsra_balance_keur=0.0,
            mra_contribution_keur=0.0, mra_balance_keur=0.0,
            cf_after_reserves_keur=750.0,
            dscr=1.5, llcr=1.8, plcr=1.5,
            lockup_active=False,
            distribution_keur=600.0, cash_sweep_keur=0.0,
            cum_distribution_keur=600.0,
            cash_balance_keur=150.0,
            shl_balance_keur=0.0, shl_pik_keur=0.0,
            senior_balance_keur=900.0,
        )],
        total_revenue_keur=1000.0, total_opex_keur=200.0,
        total_ebitda_keur=800.0, total_tax_keur=50.0,
        total_senior_ds_keur=100.0, total_shl_service_keur=0.0,
        total_distribution_keur=600.0,
        avg_dscr=1.5, min_dscr=1.5, max_dscr=1.5,
        min_llcr=1.8, min_plcr=1.5, periods_in_lockup=0,
        project_irr=0.08, equity_irr=0.0, sponsor_irr=0.0,
        project_npv=0.0, equity_npv=0.0,
    )

    project_results = (("SOLAR-001", wf_result),)
    ds_schedule = (200.0,)
    result = run_portfolio_from_inputs(
        portfolio, project_results=project_results,
        portfolio_debt_service_schedule=ds_schedule,
    )
    assert result.portfolio_debt_service_schedule == ds_schedule
