"""app.services.production_waterfall_seam — PR-8 central production routing seam.

ONE shared execution seam for every user-facing financial route:

    resolve canonical ProjectInputs
        ↓
    classify_production_authority()          [single shared classifier]
        ↓
    CLEAN_PRODUCTION_READY  → run_clean_production() exactly once
                              → read-only clean view (legacy-shaped)
    explicitly BLOCKED      → typed fail-closed CleanNotReadyError
                              (zero calculations, no legacy execution)

Invariants (Phase B4):
  - SAME_PROJECT_SAME_SNAPSHOT_SAME_AUTHORITY — the decision depends only on
    the typed ProjectInputs snapshot, never on which route asked;
  - NO exception-driven fallback: classification plumbing failures raise the
    typed ProductionAuthorityResolutionError and execute ZERO engines;
  - clean-ready + diagnostic-only flags (use_dualrun_validation) fail closed
    with a typed reason;
  - blocked / unclassified inputs fail closed (CleanNotReadyError, zero
    calculations) — there is NO legacy financial execution seam in this
    module or anywhere else in the production app surface. Historical
    calibration execution lives OFFLINE in tests/helpers/offline_calibration.py.
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
    result: object                     # read-only legacy-shaped view over the clean result
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
    carry legacy results.
    """
    decision = classify_or_fail(project_inputs)

    if decision.promoted:
        if use_dualrun_validation:
            raise ProductionAuthorityResolutionError(
                reason_code="PR8_DUALRUN_DIAGNOSTIC_UNAVAILABLE_ON_CLEAN_ROUTE",
                detail=(
                    "use_dualrun_validation is a historical diagnostic; "
                    "it is not available on the clean production route. The "
                    "clean-ready project fails closed rather than executing "
                    "an unregistered runtime contract."
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
            "(Phase B4: execute_production_waterfall is clean-only; this "
            "contract is not registered for production execution. Historical "
            "calibration evidence is available offline only.)"
        ),
        runtime_authority="clean_not_ready",
        calculation_count=0,
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
    clean G2C result wrapped in a DemoResult; blocked or unrecognised types
    fail closed with a typed CleanNotReadyError (zero calculations - there
    is no legacy production engine). Returns (demo, execution_meta).
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
            from app.demo_result import DemoResult

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
                "(Phase B4: execute_production_demo is clean-only; this "
                "contract is not registered for production execution.)"
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
            "project type. Phase B4: the production financial authority is "
            "clean-only; unrecognised types are not a production composition."
        ),
        runtime_authority="clean_not_ready",
        calculation_count=0,
    )
