"""UI runner — creates and runs demo projects for the Streamlit shell."""
from __future__ import annotations
import logging
import os
from dataclasses import dataclass, field
from typing import TypedDict

logger = logging.getLogger(__name__)

PARTIAL_NOTE = "BESS/hybrid waterfall integration is in progress. Revenue-only shown."
PORTFOLIO_NOTE = "Portfolio IRR and pooling are experimental."

PROJECT_CONFIGS = {
    "Solar": {
        "factory": "create_default_solar_project",
        "status": "full",
        "note": None,
    },
    "Wind": {
        "factory": "create_default_wind_project",
        "status": "full",
        "note": None,
    },
    "BESS": {
        "factory": "create_default_bess_project",
        "status": "partial",
        "note": PARTIAL_NOTE,
    },
    "Solar+BESS": {
        "factory": "create_default_solar_bess_project",
        "status": "partial",
        "note": PARTIAL_NOTE,
    },
    "Wind+BESS": {
        "factory": "create_default_wind_bess_project",
        "status": "partial",
        "note": PARTIAL_NOTE,
    },
}


@dataclass
class DemoResult:
    project_inputs: object | None = None
    result: object | None = None
    portfolio_result: object | None = None
    messages: list[str] = field(default_factory=list)
    project_type: str = ""
    is_portfolio: bool = False
    validation_issues: list = field(default_factory=list)
    integration_status: str = "full"
    integration_note: str | None = None


def _build_period_engine(project_inputs):
    from domain.period_engine import PeriodEngine
    return PeriodEngine(
        financial_close=project_inputs.info.financial_close,
        construction_months=project_inputs.info.construction_months,
        horizon_years=project_inputs.info.horizon_years,
        ppa_years=project_inputs.revenue.ppa_term_years,
    )


def _run_waterfall(project_inputs, engine):
    """Run waterfall using config derived from project inputs."""
    from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
    runner = WaterfallRunner(inputs=project_inputs, engine=engine)
    config = WaterfallRunConfig.from_inputs(project_inputs, engine)
    return runner.run(config)


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

    FACTORY_MAP = {
        "Solar": create_default_solar_project,
        "Wind": create_default_wind_project,
        "BESS": create_default_bess_project,
        "Solar+BESS": create_default_solar_bess_project,
        "Wind+BESS": create_default_wind_bess_project,
    }

    result = DemoResult(project_type=project_type)
    messages = []

    # Validate overrides before running
    if project_inputs_override is not None:
        from domain.validation import validate_project_inputs
        issues = list(validate_project_inputs(project_inputs_override))
        error_issues = [i for i in issues if i.severity == "error"]
        if error_issues:
            return DemoResult(
                project_inputs=project_inputs_override,
                result=None,
                portfolio_result=None,
                messages=["Edited inputs contain validation errors; model was not run."] + [i.message for i in error_issues],
                integration_status="full",
                integration_note=None,
                validation_issues=issues,
            )

    try:
        if project_type == "Portfolio":
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
            result.integration_note = PORTFOLIO_NOTE
        elif project_type in FACTORY_MAP:
            factory = FACTORY_MAP[project_type]
            proj = project_inputs_override if project_inputs_override is not None else factory()

            # BESS scenario guardrail — partial model, block scenarios
            BESS_TYPES = {"BESS", "Solar+BESS", "Wind+BESS"}
            if scenario != "Base" and project_type in BESS_TYPES:
                messages.append(
                    f"⚠️ Scenarios not supported for {project_type} — showing Base case."
                )
                scenario = "Base"

            # Apply scenario if not Base
            if scenario != "Base":
                from app.scenarios import apply_scenario
                proj = apply_scenario(proj, scenario)

            engine = _build_period_engine(proj)
            result.result = _run_waterfall(proj, engine)
            result.project_inputs = proj

            # Surface model warnings to user
            from domain.validation import warn_model_unrealistic
            warnings = warn_model_unrealistic(result.result, proj)
            for w in warnings:
                messages.append(f"⚠️ {w.code}: {w.message}")

            cfg = PROJECT_CONFIGS[project_type]
            result.integration_status = cfg["status"]
            result.integration_note = cfg["note"]
        else:
            messages.append(f"Unknown project type: {project_type}")

        if scenario != "Base":
            if project_type == "Portfolio":
                # Scenario NOT applied to portfolio — show explicit warning
                messages.append(
                    f"⚠️ Scenario '{scenario}' is not supported for Portfolio. "
                    f"Results shown are Base case. Portfolio scenarios not yet implemented."
                )
            else:
                from app.scenarios import scenario_summary
                rows = scenario_summary(scenario)
                for row in rows:
                    messages.append(
                        f"Scenario: {scenario} — {row['assumption']} {row['change']}"
                    )

        # Validation for non-portfolio projects
        if project_type in FACTORY_MAP:
            from domain.validation import validate_project_inputs
            validation_issues = list(validate_project_inputs(proj))
            result.validation_issues = validation_issues
        elif project_type == "Portfolio":
            from domain.validation import validate_portfolio_inputs
            validation_issues = list(validate_portfolio_inputs(pf))
            result.validation_issues = validation_issues

    except Exception as e:
        logger.exception("Error running %s", project_type)
        if os.getenv("FINCOGPT_RAISE_UI_ERRORS") == "1":
            raise
        messages.append(f"Error running {project_type}: {type(e).__name__}: {e}")

    result.messages = messages
    return result