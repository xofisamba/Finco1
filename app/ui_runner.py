"""UI runner — creates and runs demo projects for the Streamlit shell."""
from __future__ import annotations
from typing import TypedDict
from dataclasses import dataclass, field
import warnings

@dataclass
class DemoResult:
    project_inputs: object | None = None
    result: object | None = None
    portfolio_result: object | None = None
    messages: list[str] = field(default_factory=list)
    project_type: str = ""
    is_portfolio: bool = False
    validation_issues: list = field(default_factory=list)
    integration_status: str = "full"  # "full" | "partial" | "experimental"
    integration_note: str | None = None

def _run_waterfall(project_inputs, engine):
    """Run waterfall via WaterfallRunner with default config."""
    from app.waterfall_runner import WaterfallRunner
    runner = WaterfallRunner(inputs=project_inputs, engine=engine)
    return runner.run_with_defaults()


def run_demo_project(project_type: str, scenario: str = "Base", project_inputs_override=None) -> DemoResult:
    """Create and run a demo project, returning results for UI display."""
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

    result = DemoResult(project_type=project_type)
    messages = []

    try:
        if project_type == "Solar":
            proj = create_default_solar_project() if project_inputs_override is None else project_inputs_override
            engine = PeriodEngine(
                financial_close=proj.info.financial_close,
                construction_months=proj.info.construction_months,
                horizon_years=proj.info.horizon_years,
                ppa_years=proj.revenue.ppa_term_years,
            )
            result.result = _run_waterfall(proj, engine)
            result.project_inputs = proj
            result.integration_status = "full"
            result.integration_note = None
        elif project_type == "Wind":
            proj = create_default_wind_project() if project_inputs_override is None else project_inputs_override
            engine = PeriodEngine(
                financial_close=proj.info.financial_close,
                construction_months=proj.info.construction_months,
                horizon_years=proj.info.horizon_years,
                ppa_years=proj.revenue.ppa_term_years,
            )
            result.result = _run_waterfall(proj, engine)
            result.project_inputs = proj
            result.integration_status = "full"
            result.integration_note = None
        elif project_type == "BESS":
            proj = create_default_bess_project() if project_inputs_override is None else project_inputs_override
            engine = PeriodEngine(
                financial_close=proj.info.financial_close,
                construction_months=proj.info.construction_months,
                horizon_years=proj.info.horizon_years,
                ppa_years=proj.revenue.ppa_term_years,
            )
            result.result = _run_waterfall(proj, engine)
            result.project_inputs = proj
            result.integration_status = "partial"
            result.integration_note = "BESS/hybrid waterfall integration is in progress. Revenue-only shown."
        elif project_type == "Solar+BESS":
            proj = create_default_solar_bess_project() if project_inputs_override is None else project_inputs_override
            engine = PeriodEngine(
                financial_close=proj.info.financial_close,
                construction_months=proj.info.construction_months,
                horizon_years=proj.info.horizon_years,
                ppa_years=proj.revenue.ppa_term_years,
            )
            result.result = _run_waterfall(proj, engine)
            result.project_inputs = proj
            result.integration_status = "partial"
            result.integration_note = "BESS/hybrid waterfall integration is in progress. Revenue-only shown."
        elif project_type == "Wind+BESS":
            proj = create_default_wind_bess_project() if project_inputs_override is None else project_inputs_override
            engine = PeriodEngine(
                financial_close=proj.info.financial_close,
                construction_months=proj.info.construction_months,
                horizon_years=proj.info.horizon_years,
                ppa_years=proj.revenue.ppa_term_years,
            )
            result.result = _run_waterfall(proj, engine)
            result.project_inputs = proj
            result.integration_status = "partial"
            result.integration_note = "BESS/hybrid waterfall integration is in progress. Revenue-only shown."
        elif project_type == "Portfolio":
            proj_solar = create_default_solar_project()
            proj_wind = create_default_wind_project()
            shared = FinancingParams(
                share_capital_keur=50_000.0,
                senior_debt_amount_keur=100_000.0,
                senior_tenor_years=10,
                target_dscr=1.3,
            )
            pf = PortfolioInputs(
                projects=(proj_solar, proj_wind),
                portfolio_name="Demo Portfolio",
                shared_financing=shared,
            )
            result.portfolio_result = run_portfolio_from_inputs(pf)
            result.project_inputs = pf
            result.is_portfolio = True
            result.integration_status = "experimental"
            result.integration_note = "Portfolio IRR and pooling are experimental."
        else:
            messages.append(f"Unknown project type: {project_type}")

        # Scenario informational notice
        if scenario != "Base":
            messages.append(
                "Scenario selector is informational only. "
                "Downside/Upside scaling is not yet implemented."
            )

        # Validation
        if project_type in ("Solar", "Wind", "BESS", "Solar+BESS", "Wind+BESS"):
            from domain.validation import validate_project_inputs
            validation_issues = list(validate_project_inputs(proj))
            result.validation_issues = validation_issues
        elif project_type == "Portfolio":
            from domain.validation import validate_portfolio_inputs
            validation_issues = list(validate_portfolio_inputs(pf))
            result.validation_issues = validation_issues

    except Exception as e:
        messages.append(f"Error running {project_type}: {str(e)}")

    result.messages = messages
    return result