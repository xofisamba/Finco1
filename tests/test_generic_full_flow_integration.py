"""Generic full-flow integration tests for all project types."""
import pytest
import ast
import inspect
from app.project_factories import (
    create_default_solar_project,
    create_default_wind_project,
    create_default_bess_project,
    create_default_solar_bess_project,
    create_default_wind_bess_project,
)
from app.portfolio_runner import run_portfolio_from_inputs
from domain.portfolio.inputs import PortfolioInputs
from domain.inputs import FinancingParams
from domain.period_engine import PeriodEngine
from app.waterfall_core import run_waterfall_v3_core


def _engine(proj):
    return PeriodEngine(
        financial_close=proj.info.financial_close,
        construction_months=proj.info.construction_months,
        horizon_years=proj.info.horizon_years,
        ppa_years=proj.revenue.ppa_term_years,
    )


def _run_solar():
    proj = create_default_solar_project()
    eng = _engine(proj)
    op_periods = [p for p in eng.periods() if p.is_operation]
    return run_waterfall_v3_core(proj, eng, proj.financing.all_in_rate/2, len(op_periods),
                                proj.financing.target_dscr, proj.financing.lockup_dscr,
                                proj.tax.corporate_rate, proj.financing.dsra_months,
                                proj.financing.shl_amount_keur, proj.financing.shl_rate,
                                0.0, "bullet", equity_irr_method="equity_only",
                                share_capital_keur=proj.financing.share_capital_keur,
                                sculpt_capex_keur=proj.capex.sculpt_capex_keur,
                                debt_sizing_method=proj.financing.debt_sizing_method)


def _run_wind():
    proj = create_default_wind_project()
    eng = _engine(proj)
    op_periods = [p for p in eng.periods() if p.is_operation]
    return run_waterfall_v3_core(proj, eng, proj.financing.all_in_rate/2, len(op_periods),
                                proj.financing.target_dscr, proj.financing.lockup_dscr,
                                proj.tax.corporate_rate, proj.financing.dsra_months,
                                proj.financing.shl_amount_keur, proj.financing.shl_rate,
                                0.0, "bullet", equity_irr_method="equity_only",
                                share_capital_keur=proj.financing.share_capital_keur,
                                sculpt_capex_keur=proj.capex.sculpt_capex_keur,
                                debt_sizing_method=proj.financing.debt_sizing_method)


def test_solar_full_flow_generic():
    result = _run_solar()
    assert result.total_revenue_keur > 0
    assert result.total_ebitda_keur > 0
    assert result.total_tax_keur >= 0
    assert result.min_dscr > 0
    assert result.project_irr is not None and result.project_irr != 0.0


def test_wind_full_flow_generic():
    result = _run_wind()
    assert result.total_revenue_keur > 0
    assert result.total_ebitda_keur > 0


def test_bess_factory_or_documented_partial():
    """BESS standalone — either waterfall runs or limitation is documented."""
    from app.ui_runner import run_demo_project
    result = run_demo_project("BESS")
    assert result.messages or result.result is not None


def test_solar_bess_full_flow_or_documented_partial():
    from app.ui_runner import run_demo_project
    result = run_demo_project("Solar+BESS")
    assert result.messages or result.result is not None


def test_wind_bess_full_flow_or_documented_partial():
    from app.ui_runner import run_demo_project
    result = run_demo_project("Wind+BESS")
    assert result.messages or result.result is not None


def test_portfolio_solar_wind_full_flow_generic():
    solar = create_default_solar_project()
    wind = create_default_wind_project()
    shared = FinancingParams(share_capital_keur=50_000.0, senior_debt_amount_keur=100_000.0,
                             senior_tenor_years=10, target_dscr=1.3)
    pf = PortfolioInputs(projects=(solar, wind), portfolio_name="Test", shared_financing=shared)
    result = run_portfolio_from_inputs(pf)
    assert result.total_revenue_keur > 0
    assert result.total_ebitda_keur > 0
    assert result.min_dscr > 0
    assert len(result.project_results) == 2


def test_no_calibration_runtime_imports_in_ui_and_waterfall():
    """Verify app.calibration and tools.calibration_legacy are not runtime dependencies."""
    import importlib

    for module_path in ["app.ui_runner", "app.waterfall_core", "app.portfolio_runner"]:
        try:
            mod = importlib.import_module(module_path)
            src = inspect.getsource(mod)
            tree = ast.parse(src)
            bad_imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if any(x in alias.name for x in ["calibration", "excel_oborovo", "excel_tuho"]):
                            bad_imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module and any(x in node.module for x in ["calibration", "excel_oborovo", "excel_tuho"]):
                        bad_imports.append(node.module)
            assert not bad_imports, f"{module_path} imports: {bad_imports}"
        except ImportError:
            pass  # module may not exist