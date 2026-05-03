"""Tests for app/portfolio_runner.py."""
import pytest
from unittest.mock import patch, MagicMock


def test_portfolio_runner_uses_project_sculpt_capex_not_zero():
    from app.portfolio_runner import run_portfolio_from_inputs
    from app.project_factories import create_default_solar_project, create_default_wind_project
    from domain.portfolio.inputs import PortfolioInputs
    from domain.inputs import FinancingParams

    captured_calls = []
    def capture_run(**kwargs):
        captured_calls.append(kwargs)
        mock_result = MagicMock()
        mock_result.periods = []
        return mock_result

    proj1 = create_default_solar_project()
    proj2 = create_default_wind_project()
    shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                             senior_tenor_years=10, target_dscr=1.3)
    pf = PortfolioInputs(projects=(proj1, proj2), portfolio_name="Test", shared_financing=shared)

    with patch('app.portfolio_runner.run_waterfall_v3_core', side_effect=capture_run):
        try:
            run_portfolio_from_inputs(pf)
        except Exception:
            pass  # We only care about captured calls

    # Assert exact mapping for both projects
    assert len(captured_calls) == 2
    assert captured_calls[0]["sculpt_capex_keur"] == proj1.capex.sculpt_capex_keur
    assert captured_calls[1]["sculpt_capex_keur"] == proj2.capex.sculpt_capex_keur
    assert captured_calls[0]["sculpt_capex_keur"] > 0


def test_portfolio_runner_uses_project_shl_inputs():
    from app.portfolio_runner import run_portfolio_from_inputs
    from app.project_factories import create_default_solar_project, create_default_wind_project
    from domain.portfolio.inputs import PortfolioInputs
    from domain.inputs import FinancingParams

    captured_calls = []
    def capture_run(**kwargs):
        captured_calls.append(kwargs)
        mock_result = MagicMock()
        mock_result.periods = []
        return mock_result

    proj1 = create_default_solar_project()
    proj2 = create_default_wind_project()
    shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                             senior_tenor_years=10, target_dscr=1.3)
    pf = PortfolioInputs(projects=(proj1, proj2), portfolio_name="Test", shared_financing=shared)

    with patch('app.portfolio_runner.run_waterfall_v3_core', side_effect=capture_run):
        try:
            run_portfolio_from_inputs(pf)
        except Exception:
            pass

    assert len(captured_calls) == 2
    for i, proj in enumerate([proj1, proj2]):
        assert captured_calls[i]["shl_amount"] == proj.financing.shl_amount_keur, f"shl_amount mismatch for proj {i}"
        assert captured_calls[i]["shl_rate"] == proj.financing.shl_rate, f"shl_rate mismatch for proj {i}"
        assert captured_calls[i]["shl_idc_keur"] == proj.financing.shl_idc_keur, f"shl_idc_keur mismatch for proj {i}"
        assert captured_calls[i]["shl_repayment_method"] == proj.financing.shl_repayment_method, f"shl_repayment_method mismatch for proj {i}"
        assert captured_calls[i]["shl_tenor_years"] == getattr(proj.financing, 'shl_tenor_years', 0), f"shl_tenor_years mismatch for proj {i}"


def test_portfolio_runner_uses_project_tax_rate():
    from app.portfolio_runner import run_portfolio_from_inputs
    from app.project_factories import create_default_solar_project, create_default_wind_project
    from domain.portfolio.inputs import PortfolioInputs
    from domain.inputs import FinancingParams

    captured_calls = []
    def capture_run(**kwargs):
        captured_calls.append(kwargs)
        mock_result = MagicMock()
        mock_result.periods = []
        return mock_result

    proj1 = create_default_solar_project()
    proj2 = create_default_wind_project()
    shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                             senior_tenor_years=10, target_dscr=1.3)
    pf = PortfolioInputs(projects=(proj1, proj2), portfolio_name="Test", shared_financing=shared)

    with patch('app.portfolio_runner.run_waterfall_v3_core', side_effect=capture_run):
        try:
            run_portfolio_from_inputs(pf)
        except Exception:
            pass

    assert len(captured_calls) == 2
    assert captured_calls[0]["tax_rate"] == proj1.tax.corporate_rate
    assert captured_calls[1]["tax_rate"] == proj2.tax.corporate_rate


def test_portfolio_runner_uses_shared_target_and_lockup_dscr():
    from app.portfolio_runner import run_portfolio_from_inputs
    from app.project_factories import create_default_solar_project, create_default_wind_project
    from domain.portfolio.inputs import PortfolioInputs
    from domain.inputs import FinancingParams

    captured_calls = []
    def capture_run(**kwargs):
        captured_calls.append(kwargs)
        mock_result = MagicMock()
        mock_result.periods = []
        return mock_result

    proj1 = create_default_solar_project()
    proj2 = create_default_wind_project()
    shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                             senior_tenor_years=10, target_dscr=1.35, lockup_dscr=1.20)
    pf = PortfolioInputs(projects=(proj1, proj2), portfolio_name="Test", shared_financing=shared)

    with patch('app.portfolio_runner.run_waterfall_v3_core', side_effect=capture_run):
        try:
            run_portfolio_from_inputs(pf)
        except Exception:
            pass

    # Shared financing values used for ALL project calls
    for call in captured_calls:
        assert call["target_dscr"] == 1.35, f"target_dscr mismatch: {call['target_dscr']}"
        assert call["lockup_dscr"] == 1.20, f"lockup_dscr mismatch: {call['lockup_dscr']}"


def test_portfolio_runner_uses_project_equity_and_debt_sizing_methods():
    from app.portfolio_runner import run_portfolio_from_inputs
    from app.project_factories import create_default_solar_project, create_default_wind_project
    from domain.portfolio.inputs import PortfolioInputs
    from domain.inputs import FinancingParams

    captured_calls = []
    def capture_run(**kwargs):
        captured_calls.append(kwargs)
        mock_result = MagicMock()
        mock_result.periods = []
        return mock_result

    proj1 = create_default_solar_project()
    proj2 = create_default_wind_project()
    shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                             senior_tenor_years=10, target_dscr=1.3)
    pf = PortfolioInputs(projects=(proj1, proj2), portfolio_name="Test", shared_financing=shared)

    with patch('app.portfolio_runner.run_waterfall_v3_core', side_effect=capture_run):
        try:
            run_portfolio_from_inputs(pf)
        except Exception:
            pass

    assert len(captured_calls) == 2
    for i, proj in enumerate([proj1, proj2]):
        assert captured_calls[i]["equity_irr_method"] == proj.financing.equity_irr_method
        assert captured_calls[i]["debt_sizing_method"] == proj.financing.debt_sizing_method
        assert captured_calls[i]["share_capital_keur"] == proj.financing.share_capital_keur


def test_portfolio_runner_uses_project_dsra_months():
    from app.portfolio_runner import run_portfolio_from_inputs
    from app.project_factories import create_default_solar_project, create_default_wind_project
    from domain.portfolio.inputs import PortfolioInputs
    from domain.inputs import FinancingParams

    captured_calls = []
    def capture_run(**kwargs):
        captured_calls.append(kwargs)
        mock_result = MagicMock()
        mock_result.periods = []
        return mock_result

    proj1 = create_default_solar_project()
    proj2 = create_default_wind_project()
    shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                             senior_tenor_years=10, target_dscr=1.3)
    pf = PortfolioInputs(projects=(proj1, proj2), portfolio_name="Test", shared_financing=shared)

    with patch('app.portfolio_runner.run_waterfall_v3_core', side_effect=capture_run):
        try:
            run_portfolio_from_inputs(pf)
        except Exception:
            pass

    assert len(captured_calls) == 2
    for i, proj in enumerate([proj1, proj2]):
        dsra = getattr(proj.financing, 'dsra_months', 6)
        assert captured_calls[i]["dsra_months"] == dsra


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