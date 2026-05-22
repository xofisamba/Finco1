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
    # Phase 9.5 — named project bindings
    "TUHO": {
        "factory": "create_default_tuho_wind1",
        "status": "full",
        "note": None,
    },
    "Oborovo": {
        "factory": "create_default_oborovo",
        "status": "full",
        "note": None,
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


def _run_waterfall(project_inputs, engine, advanced_opex_line_items=None, advanced_capex_line_items=None, project_type="solar", use_dualrun_validation: bool = False):
    """Run waterfall using config derived from project inputs."""
    from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
    runner = WaterfallRunner(inputs=project_inputs, engine=engine)
    config = WaterfallRunConfig.from_inputs(project_inputs, engine)
    # Pass advanced OPEX and CAPEX line items through the config if provided
    from dataclasses import replace
    updates = {}
    if advanced_opex_line_items is not None:
        updates["advanced_opex_line_items"] = advanced_opex_line_items
    if advanced_capex_line_items is not None:
        from app.depreciation_bankable import build_bankable_waterfall_schedule
        # Generate bankable depreciation schedule from CapexLineItems
        horizon_years = project_inputs.info.horizon_years
        depr_schedule = build_bankable_waterfall_schedule(
            list(advanced_capex_line_items),
            profile_name=f"{project_type.lower()}_croatia_ibl",
            total_periods=horizon_years,
            project_type=project_type,
        )
        updates["advanced_capex_depreciation_schedule"] = depr_schedule
        updates["advanced_capex_line_items"] = advanced_capex_line_items
    if use_dualrun_validation:
        updates["use_dualrun_validation"] = True
    if updates:
        config = replace(config, **updates)
    return runner.run(config)


def _advanced_opex_warnings(line_items) -> list[str]:
    """Return warning messages if any line items have manual/hardcoded values.

    Triggers on any of:
    - item.source == OpexSource.MANUAL
    - item.is_hardcoded is True
    - item.has_manual_overrides() is True
    """
    from app.opex_engine import OpexSource
    if not line_items:
        return []
    has_manual = any(item.source == OpexSource.MANUAL for item in line_items)
    has_hardcoded = any(item.is_hardcoded for item in line_items)
    has_overrides = any(item.has_manual_overrides() for item in line_items)
    if has_manual or has_hardcoded or has_overrides:
        return ["Advanced OPEX contains manual or hardcoded values. Review override notes."]
    return []


def run_demo_project(project_type: str, scenario: str = "Base",
                   project_inputs_override=None,
                   advanced_opex_line_items=None,
                   advanced_capex_line_items=None,
                   use_dualrun_validation: bool = False) -> DemoResult:
    """Create and run a demo project, returning results for UI display."""
    from app.project_factories import (
        create_default_solar_project,
        create_default_wind_project,
        create_default_bess_project,
        create_default_solar_bess_project,
        create_default_wind_bess_project,
        create_default_tuho_wind1,
        create_default_oborovo,
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
        # Phase 9.5 — named project bindings
        "TUHO": create_default_tuho_wind1,
        "Oborovo": create_default_oborovo,
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
                from app.scenario_manager import ScenarioManager
                mgr = ScenarioManager(project_type.lower())
                proj = mgr.apply_overrides(proj, scenario)
                # Scale advanced OPEX line items by scenario opex_multiplier
                if advanced_opex_line_items:
                    from dataclasses import replace as dc_replace
                    opex_mult = mgr.get_scenario(scenario).opex_multiplier
                    if opex_mult != 1.0:
                        def _scale_item(item):
                            return dc_replace(item, base_year_amount_keur=item.base_year_amount_keur * opex_mult)
                        advanced_opex_line_items = tuple(_scale_item(i) for i in advanced_opex_line_items)

            engine = _build_period_engine(proj)
            result.result = _run_waterfall(proj, engine, advanced_opex_line_items, advanced_capex_line_items, project_type, use_dualrun_validation)
            result.project_inputs = proj

            # Surface model warnings to user
            from domain.validation import warn_model_unrealistic
            warnings = warn_model_unrealistic(result.result, proj)
            for w in warnings:
                messages.append(f"⚠️ {w.code}: {w.message}")

            # Surface advanced OPEX manual/hardcoded warnings
            for w in _advanced_opex_warnings(advanced_opex_line_items):
                messages.append(w)

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
                from app.scenario_manager import ScenarioManager
                sm = ScenarioManager(project_type)
                rows = sm.scenario_summary(scenario)
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

def run_independent_portfolio_ui(
    portfolio_inputs,
    holdco_inputs=None,
    strict: bool = False,
):
    """Run independent portfolio via the orchestrator (Phase 1+ path).

    This is the thin UI wrapper around run_portfolio_orchestrated(mode="independent").
    """
    from app.portfolio_orchestrator import run_portfolio_orchestrated, PortfolioMode

    return run_portfolio_orchestrated(
        portfolio_inputs=portfolio_inputs,
        mode=PortfolioMode.INDEPENDENT,
        holdco_inputs=holdco_inputs,
        strict=strict,
    )
