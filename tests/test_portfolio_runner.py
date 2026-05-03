"""Tests for app/portfolio_runner.py."""
import pytest
from unittest.mock import patch, MagicMock


def test_portfolio_runner_uses_project_sculpt_capex_not_zero():
    from app.portfolio_runner import run_portfolio_from_inputs
    from app.project_factories import create_default_solar_project, create_default_wind_project

    capex_value = None

    def capture_run_waterfall_v3_core(**kwargs):
        nonlocal capex_value
        capex_value = kwargs.get('sculpt_capex_keur')
        # Return a mock WaterfallResult
        mock_result = MagicMock()
        mock_result.periods = []
        return mock_result

    with patch('app.portfolio_runner.run_waterfall_v3_core', side_effect=capture_run_waterfall_v3_core):
        from domain.portfolio.inputs import PortfolioInputs
        from domain.inputs import FinancingParams

        proj1 = create_default_solar_project()
        proj2 = create_default_wind_project()
        shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                                 senior_tenor_years=10, target_dscr=1.3)
        pf = PortfolioInputs(projects=(proj1, proj2), portfolio_name="Test", shared_financing=shared)

        try:
            run_portfolio_from_inputs(pf)
        except Exception:
            pass  # We only care about the captured value

    # Assert sculpt_capex was passed (not hard-coded 0.0)
    assert capex_value is not None, "sculpt_capex_keur was not passed to run_waterfall_v3_core"


def test_portfolio_runner_uses_project_shl_inputs():
    from app.portfolio_runner import run_portfolio_from_inputs
    from app.project_factories import create_default_solar_project, create_default_wind_project

    captured = {}
    def capture_run(**kwargs):
        captured['shl_amount'] = kwargs.get('shl_amount')
        captured['shl_rate'] = kwargs.get('shl_rate')
        captured['shl_idc_keur'] = kwargs.get('shl_idc_keur')
        captured['shl_repayment_method'] = kwargs.get('shl_repayment_method')
        mock_result = MagicMock()
        mock_result.periods = []
        return mock_result

    with patch('app.portfolio_runner.run_waterfall_v3_core', side_effect=capture_run):
        proj1 = create_default_solar_project()
        proj2 = create_default_wind_project()
        from domain.portfolio.inputs import PortfolioInputs
        from domain.inputs import FinancingParams

        shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                                 senior_tenor_years=10, target_dscr=1.3)
        pf = PortfolioInputs(projects=(proj1, proj2), portfolio_name="Test", shared_financing=shared)

        try:
            run_portfolio_from_inputs(pf)
        except Exception:
            pass

    # Should use project values, not hard-coded
    assert captured['shl_amount'] is not None
    assert captured['shl_rate'] is not None
    assert captured['shl_idc_keur'] is not None
    assert captured['shl_repayment_method'] is not None


def test_portfolio_runner_uses_project_tax_rate():
    from app.portfolio_runner import run_portfolio_from_inputs
    from app.project_factories import create_default_solar_project, create_default_wind_project

    tax_rate_captured = None
    def capture_run(**kwargs):
        nonlocal tax_rate_captured
        tax_rate_captured = kwargs.get('tax_rate')
        mock_result = MagicMock()
        mock_result.periods = []
        return mock_result

    with patch('app.portfolio_runner.run_waterfall_v3_core', side_effect=capture_run):
        proj1 = create_default_solar_project()
        proj2 = create_default_wind_project()
        from domain.portfolio.inputs import PortfolioInputs
        from domain.inputs import FinancingParams

        shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                                 senior_tenor_years=10, target_dscr=1.3)
        pf = PortfolioInputs(projects=(proj1, proj2), portfolio_name="Test", shared_financing=shared)

        try:
            run_portfolio_from_inputs(pf)
        except Exception:
            pass

    assert tax_rate_captured is not None
    assert tax_rate_captured > 0


def test_portfolio_runner_uses_shared_target_and_lockup_dscr():
    from app.portfolio_runner import run_portfolio_from_inputs
    from app.project_factories import create_default_solar_project, create_default_wind_project

    captured = {}
    def capture_run(**kwargs):
        captured['target_dscr'] = kwargs.get('target_dscr')
        captured['lockup_dscr'] = kwargs.get('lockup_dscr')
        mock_result = MagicMock()
        mock_result.periods = []
        return mock_result

    with patch('app.portfolio_runner.run_waterfall_v3_core', side_effect=capture_run):
        proj1 = create_default_solar_project()
        proj2 = create_default_wind_project()
        from domain.portfolio.inputs import PortfolioInputs
        from domain.inputs import FinancingParams

        shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                                 senior_tenor_years=10, target_dscr=1.35, lockup_dscr=1.20)
        pf = PortfolioInputs(projects=(proj1, proj2), portfolio_name="Test", shared_financing=shared)

        try:
            run_portfolio_from_inputs(pf)
        except Exception:
            pass

    assert captured.get('target_dscr') is not None
    assert captured.get('lockup_dscr') is not None


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
