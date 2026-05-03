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

def run_demo_project(project_type: str, scenario: str = "Base") -> DemoResult:
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

    result = DemoResult(project_type=project_type)
    messages = []

    try:
        if project_type == "Solar":
            proj = create_default_solar_project()
            from app.waterfall_runner import run_waterfall_from_inputs
            result.result = run_waterfall_from_inputs(proj)
            result.project_inputs = proj
        elif project_type == "Wind":
            proj = create_default_wind_project()
            from app.waterfall_runner import run_waterfall_from_inputs
            result.result = run_waterfall_from_inputs(proj)
            result.project_inputs = proj
        elif project_type == "BESS":
            proj = create_default_bess_project()
            from app.waterfall_runner import run_waterfall_from_inputs
            result.result = run_waterfall_from_inputs(proj)
            result.project_inputs = proj
        elif project_type == "Solar+BESS":
            proj = create_default_solar_bess_project()
            from app.waterfall_runner import run_waterfall_from_inputs
            result.result = run_waterfall_from_inputs(proj)
            result.project_inputs = proj
        elif project_type == "Wind+BESS":
            proj = create_default_wind_bess_project()
            from app.waterfall_runner import run_waterfall_from_inputs
            result.result = run_waterfall_from_inputs(proj)
            result.project_inputs = proj
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
        else:
            messages.append(f"Unknown project type: {project_type}")
    except Exception as e:
        messages.append(f"Error running {project_type}: {str(e)}")

    result.messages = messages
    return result