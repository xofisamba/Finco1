"""app.services.production_waterfall_seam — PR-8 central production routing seam.

ONE shared execution seam for every user-facing financial route:

    resolve canonical ProjectInputs
        ↓
    classify_production_authority()          [single shared classifier]
        ↓
    CLEAN_PRODUCTION_READY  → run_clean_production() exactly once
                              → read-only clean view (legacy-shaped)
    explicitly BLOCKED      → explicitly classified legacy calibration run
                              (only where the route still supports legacy)

Invariants (PR-8 correction pass):
  - SAME_PROJECT_SAME_SNAPSHOT_SAME_AUTHORITY — the decision depends only on
    the typed ProjectInputs snapshot, never on which route asked;
  - NO exception-driven fallback: classification plumbing failures raise the
    typed ProductionAuthorityResolutionError and execute ZERO engines;
  - clean-ready + diagnostic-only flags (use_dualrun_validation) fail closed
    with a typed reason — never a silent return to legacy;
  - the two runtimes never both execute for one execution.

The legacy engine is referenced ONLY inside the explicitly-blocked branch.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.production_financial_authority import (
    AuthorityDecision,
    ProductionAuthorityResolutionError,
    classify_production_authority,
    run_clean_production,
)


@dataclass
class ProductionWaterfallExecution:
    """One production financial execution and its authority lineage."""

    decision: AuthorityDecision
    result: object                     # legacy-shaped view (clean) or WaterfallResult (legacy)
    project_inputs: object             # effective inputs actually executed
    clean_run: object | None = None    # CleanProductionRun when clean
    authority_metadata: dict | None = None


def classify_or_fail(project_inputs) -> AuthorityDecision:
    """Classify with fail-closed plumbing semantics.

    A classifier exception is re-raised as the typed
    ProductionAuthorityResolutionError — the caller must surface it and may
    NOT execute any engine (clean or legacy) afterwards.
    """
    try:
        return classify_production_authority(project_inputs)
    except ProductionAuthorityResolutionError:
        raise
    except Exception as exc:
        raise ProductionAuthorityResolutionError(
            reason_code="PR8_AUTHORITY_CLASSIFIER_FAILURE",
            detail=(
                f"classify_production_authority raised {type(exc).__name__}: "
                f"{exc}. Production routing fails closed — no engine executes."
            ),
        ) from exc


def execute_production_waterfall(
    project_inputs,
    *,
    project_type: str = "",
    scenario: str = "Base",
    use_dualrun_validation: bool = False,
) -> ProductionWaterfallExecution:
    """Execute ONE clean production financial calculation under the shared authority.

    Phase B1 clean-only: non-promoted projects raise CleanNotReadyError.
    There is no allow_legacy parameter — normal production surfaces must not
    carry legacy results.  Explicit calibration callers must use
    execute_calibration_waterfall() instead.
    """
    decision = classify_or_fail(project_inputs)

    if decision.promoted:
        if use_dualrun_validation:
            raise ProductionAuthorityResolutionError(
                reason_code="PR8_DUALRUN_DIAGNOSTIC_UNAVAILABLE_ON_CLEAN_ROUTE",
                detail=(
                    "use_dualrun_validation is a legacy-calibration diagnostic; "
                    "it is not available on the clean production route. The "
                    "clean-ready project fails closed rather than silently "
                    "returning to the legacy waterfall. Calibration callers "
                    "must use execute_calibration_waterfall() from this module."
                ),
            )
        clean_run = run_clean_production(
            project_inputs, scenario, project_type=project_type
        )
        from app.services.clean_presentation_adapter import (
            build_clean_waterfall_view,
        )

        view = build_clean_waterfall_view(clean_run)
        return ProductionWaterfallExecution(
            decision=decision,
            result=view,
            project_inputs=clean_run.project_inputs,
            clean_run=clean_run,
            authority_metadata=dict(view._authority_metadata),
        )

    # ── Blocked: fail closed — no legacy fallthrough on production surfaces ──
    from app.services.production_financial_authority import CleanNotReadyError

    raise CleanNotReadyError(
        classification=decision.classification.value,
        reason_code=decision.reason_code,
        detail=(
            f"{decision.detail}  "
            "(Phase B1: execute_production_waterfall is clean-only; no legacy "
            "fallthrough. Use execute_calibration_waterfall() for calibration.)"
        ),
        runtime_authority="clean_not_ready",
        calculation_count=0,
    )


def execute_calibration_waterfall(
    project_inputs,
    *,
    project_type: str = "",
    scenario: str = "Base",
) -> ProductionWaterfallExecution:
    """Execute a legacy calibration waterfall for explicitly blocked projects.

    This is the ONLY sanctioned legacy execution entry point on the seam.
    It is EXPLICIT_CALIBRATION_ONLY — callers must be aware they are using
    the legacy calibration engine, not the production clean authority.

    Promoted (clean-ready) projects are refused: callers must use
    execute_production_waterfall() for those.
    """
    decision = classify_or_fail(project_inputs)

    if decision.promoted:
        raise ProductionAuthorityResolutionError(
            reason_code="PR8_CALIBRATION_SEAM_REFUSED_CLEAN_READY_PROJECT",
            detail=(
                "execute_calibration_waterfall() is for explicitly blocked "
                "projects only. This project is CLEAN_PRODUCTION_READY — use "
                "execute_production_waterfall() instead."
            ),
        )

    effective_inputs = project_inputs
    if scenario != "Base":
        from app.scenario_manager import ScenarioManager

        mgr = ScenarioManager((project_type or "").lower())
        effective_inputs = mgr.apply_overrides(project_inputs, scenario)

    # The ONLY legacy reference in the production authority seams — reachable
    # exclusively through an explicit non-promoted classification.
    from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
    from finco_core.engine.period_engine import PeriodEngine

    engine = PeriodEngine(
        financial_close=effective_inputs.info.financial_close,
        construction_months=effective_inputs.info.construction_months,
        horizon_years=effective_inputs.info.horizon_years,
        ppa_years=effective_inputs.revenue.ppa_term_years,
        frequency=effective_inputs.info.period_frequency,
        cod_date=effective_inputs.info.cod_date,
        period_axis_convention=getattr(
            effective_inputs.info.period_axis_convention,
            "value",
            effective_inputs.info.period_axis_convention,
        ),
    )
    config = WaterfallRunConfig.from_inputs(effective_inputs, engine)
    result = WaterfallRunner(effective_inputs, engine).run(config)
    metadata = decision.to_metadata() | {
        "runtime_authority": "legacy_waterfall_calibration",
        "calculation_count": 1,
        "calibration_seam": "execute_calibration_waterfall",
    }
    return ProductionWaterfallExecution(
        decision=decision,
        result=result,
        project_inputs=effective_inputs,
        clean_run=None,
        authority_metadata=metadata,
    )


def _authority_factory_map():
    from app import project_factories as _pf

    return {
        "TUHO": _pf.create_default_tuho_wind1,
        "Oborovo": _pf.create_default_oborovo,
        "Test 1": _pf.create_default_solar_project,
        "Test 2": _pf.create_default_wind_project,
        "Solar": _pf.create_default_solar_project,
        "Wind": _pf.create_default_wind_project,
    }


def execute_production_demo(project_type: str, scenario: str = "Base",
                            project_inputs_override=None):
    """DemoResult-shaped execution under the shared production authority.

    Serves the routes that historically consumed the legacy demo funnel
    (download values-only export, CLI, Streamlit). Promoted projects get the
    clean G2C result wrapped in a DemoResult; explicitly blocked or
    unclassified types keep the exact legacy demo funnel behaviour (an
    explicitly classified legacy execution). Returns (demo, execution_meta).
    """
    inputs = None
    decision = None
    if project_inputs_override is not None:
        inputs = project_inputs_override
    else:
        factories = _authority_factory_map()
        if project_type in factories:
            inputs = factories[project_type]()

    if inputs is not None:
        decision = classify_or_fail(inputs)
        if decision.promoted:
            if scenario != "Base":
                from app.scenario_manager import ScenarioManager

                inputs = ScenarioManager(project_type.lower()).apply_overrides(
                    inputs, scenario
                )
            clean_run = run_clean_production(inputs, "Base", project_type=project_type)
            from app.services.clean_presentation_adapter import (
                build_clean_waterfall_view,
            )
            from app.ui_runner import DemoResult

            view = build_clean_waterfall_view(clean_run)
            demo = DemoResult(
                project_type=project_type,
                result=view,
                project_inputs=clean_run.project_inputs,
                messages=[],
                integration_status="full",
                integration_note=(
                    "Clean production financial authority (PR-8): single G2C "
                    "calculation, read-only presentation adapter."
                ),
            )
            return demo, dict(view._authority_metadata)

    # Phase B1: fail-closed — no legacy production fallthrough.
    # When we have a typed non-promoted decision, raise CleanNotReadyError.
    # Only truly unrecognised types (inputs is None after factory lookup) still
    # fall through; those are not named production projects.
    if decision is not None and not decision.promoted:
        from app.services.production_financial_authority import CleanNotReadyError

        raise CleanNotReadyError(
            classification=decision.classification.value,
            reason_code=decision.reason_code,
            detail=(
                f"{decision.detail}  "
                "(Phase B1: execute_production_demo is clean-only; no legacy "
                "fallthrough.  Use the legacy calibration entry point for calibration.)"
            ),
            runtime_authority="clean_not_ready",
            calculation_count=0,
        )

    # Truly unrecognised / unclassified type — Phase B1 fail-closed.
    # Unknown project types are NOT a production composition — raise typed error.
    from app.services.production_financial_authority import CleanNotReadyError

    raise CleanNotReadyError(
        classification="UNCLASSIFIED",
        reason_code="PR8_PROJECT_TYPE_NOT_RECOGNISED",
        detail=(
            f"project_type={project_type!r} is not a recognised production "
            "project type. Phase B1: execute_production_demo raises for "
            "unrecognised types — no legacy fallthrough."
        ),
        runtime_authority="clean_not_ready",
        calculation_count=0,
    )
