"""app.services.production_financial_authority — PR-8 single production authority.

ONE production financial calculation authority:

    ProjectInputs snapshot
        ↓ (scenario mutation — same shared ScenarioManager concept)
    run_project_shareholder_waterfall_model()   [clean G2C, exactly once]
    ↓
    read-only presentation adapter (clean_presentation_adapter)
    ↓
    API / UI / persisted run / compare / export

Classification is typed and project-identity-free: it inspects ONLY typed
ProjectInputs contract fields. Projects whose typed contract is not yet
clean-ready are routed to the explicitly-classified legacy calibration
runtime with a machine-readable reason — never a silent fallback and never a
clean→legacy value mix (the two runtimes never both execute for one run).

Governance (PR-8):
  - zero project-name/code dispatch here;
  - no source vectors, no fixtures, no target fitting;
  - fail closed: the clean runner never catches an engine error and falls
    back — a clean-route failure raises.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ProductionAuthorityClassification(str, Enum):
    """Typed readiness classification of a ProjectInputs snapshot."""

    CLEAN_PRODUCTION_READY = "CLEAN_PRODUCTION_READY"
    BLOCKED_BY_DEFERRED_TAX_CAPABILITY = "BLOCKED_BY_DEFERRED_TAX_CAPABILITY"
    BLOCKED_BY_TYPED_INPUT_GAP = "BLOCKED_BY_TYPED_INPUT_GAP"
    LEGACY_CALIBRATION_ONLY = "LEGACY_CALIBRATION_ONLY"


_RUNTIME_AUTHORITY_BY_CLASSIFICATION = {
    ProductionAuthorityClassification.CLEAN_PRODUCTION_READY: "clean_g2c",
    ProductionAuthorityClassification.BLOCKED_BY_DEFERRED_TAX_CAPABILITY: (
        "legacy_waterfall_calibration"
    ),
    ProductionAuthorityClassification.BLOCKED_BY_TYPED_INPUT_GAP: (
        "legacy_waterfall_calibration"
    ),
    ProductionAuthorityClassification.LEGACY_CALIBRATION_ONLY: (
        "legacy_waterfall_calibration"
    ),
}


@dataclass(frozen=True)
class AuthorityDecision:
    """Typed routing decision for one ProjectInputs snapshot."""

    classification: ProductionAuthorityClassification
    reason_code: str
    detail: str

    @property
    def runtime_authority(self) -> str:
        return _RUNTIME_AUTHORITY_BY_CLASSIFICATION[self.classification]

    @property
    def promoted(self) -> bool:
        return (
            self.classification
            is ProductionAuthorityClassification.CLEAN_PRODUCTION_READY
        )

    def to_metadata(self) -> dict:
        return {
            "classification": self.classification.value,
            "reason_code": self.reason_code,
            "detail": self.detail,
            "runtime_authority": self.runtime_authority,
        }


class CleanProductionRunUnavailable(Exception):
    """Fail-closed error: the clean production route refused/could not run.

    Raised only when a CLEAN_PRODUCTION_READY-classified input fails inside
    the clean engine. NEVER caught to fall back to legacy — the caller must
    surface the typed reason.
    """

    def __init__(self, reason_code: str, detail: str):
        super().__init__(f"{reason_code}: {detail}")
        self.reason_code = reason_code
        self.detail = detail


def classify_production_authority(project_inputs) -> AuthorityDecision:
    """Classify a canonical ProjectInputs snapshot for production routing.

    Typed-field checks only; no project identity, no engine execution.
    Check order = depth of the deferred capability:
      1. clean cash-tax timing opt-in (deferred tax capability — the deep
         TUHO-class blocker, closes with Country Tax Template work);
      2. explicit G2A financing contract fields (typed-input gap);
      3. frozen-schedule fixture calibration contract (legacy calibration).
    """
    tax = project_inputs.tax
    if not bool(getattr(tax, "clean_cash_tax_timing_enabled", False)):
        return AuthorityDecision(
            classification=(
                ProductionAuthorityClassification.BLOCKED_BY_DEFERRED_TAX_CAPABILITY
            ),
            reason_code="PR8_BLOCKED_BY_TYPED_TUHO_TAX_RUNTIME_GAP",
            detail=(
                "tax.clean_cash_tax_timing_enabled is not opted in: the clean "
                "cash-tax timing contract (TAX_YEAR_LAST_PERIOD, lag=0) is not "
                "typed-verified for this project. Deferred to the Country Tax "
                "Template stage; the legacy calibration runtime serves this "
                "project until then."
            ),
        )

    financing = project_inputs.financing
    if getattr(financing, "sponsor_funding_mode", None) is None or (
        getattr(financing, "gearing_basis_mode", None) is None
    ):
        return AuthorityDecision(
            classification=ProductionAuthorityClassification.BLOCKED_BY_TYPED_INPUT_GAP,
            reason_code="PR8_G2A_FINANCING_CONTRACT_FIELDS_NOT_TYPED",
            detail=(
                "financing.sponsor_funding_mode / financing.gearing_basis_mode "
                "are not explicitly configured, so the canonical G2A financing "
                "stack contract (run_project_financing_model) fails closed "
                "(G2A_SPONSOR_FUNDING_MODE_EXPLICIT_INPUT_REQUIRED). The legacy "
                "calibration runtime serves this project until the typed fields "
                "are configured and the clean-vs-legacy migration disclosure is "
                "reviewed."
            ),
        )

    if bool(
        getattr(financing, "use_frozen_excel_senior_debt_schedule", False)
    ) or bool(getattr(financing, "use_shl_fcf_waterfall_engine", False)):
        return AuthorityDecision(
            classification=ProductionAuthorityClassification.LEGACY_CALIBRATION_ONLY,
            reason_code="PR8_FROZEN_FIXTURE_CALIBRATION_CONTRACT_ACTIVE",
            detail=(
                "the project's accepted runtime contract is the frozen-schedule "
                "Excel calibration stack (fixture-backed senior debt service / "
                "SHL FCF waterfall). Clean promotion requires a dedicated "
                "migration review of that calibration contract."
            ),
        )

    return AuthorityDecision(
        classification=ProductionAuthorityClassification.CLEAN_PRODUCTION_READY,
        reason_code="PR8_CLEAN_G2C_TYPED_CONTRACT_READY",
        detail=(
            "typed ProjectInputs satisfy the clean G2A/G2C contract; production "
            "financials are computed once by "
            "run_project_shareholder_waterfall_model."
        ),
    )


@dataclass
class CleanProductionRun:
    """One clean production calculation and its lineage metadata."""

    g2c_result: object
    project_inputs: object          # effective inputs (scenario applied)
    base_project_inputs: object     # inputs before scenario mutation
    scenario: str
    decision: AuthorityDecision
    authority_metadata: dict = field(default_factory=dict)


def run_clean_production(
    project_inputs,
    scenario: str = "Base",
    *,
    project_type: str = "",
) -> CleanProductionRun:
    """Execute the ONE clean production financial calculation.

    Applies the shared scenario mutation (same ScenarioManager authority the
    legacy runtime uses), then runs the canonical G2C entry point exactly
    once. Fail closed: engine errors propagate as CleanProductionRunUnavailable
    with a typed reason — never a legacy fallback.
    """
    decision = classify_production_authority(project_inputs)
    if not decision.promoted:
        raise CleanProductionRunUnavailable(
            reason_code=decision.reason_code,
            detail=(
                f"classification={decision.classification.value}; "
                "run_clean_production may not execute a non-promoted input "
                "(no silent legacy fallback exists at this seam)."
            ),
        )

    effective_inputs = project_inputs
    if scenario != "Base":
        from app.scenario_manager import ScenarioManager

        # Same shared scenario authority and registry key as the legacy
        # runtime (ui_runner passes project_type.lower()) — identical
        # multipliers, identical mutation semantics.
        mgr = ScenarioManager((project_type or "").lower())
        effective_inputs = mgr.apply_overrides(project_inputs, scenario)

    from financial_engine.shareholder_waterfall import (
        run_project_shareholder_waterfall_model,
    )

    try:
        g2c = run_project_shareholder_waterfall_model(
            effective_inputs, source_id="pr8_clean_production_authority"
        )
    except CleanProductionRunUnavailable:
        raise
    except Exception as exc:  # fail closed — never fall back to legacy
        raise CleanProductionRunUnavailable(
            reason_code="PR8_CLEAN_ENGINE_FAIL_CLOSED",
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc

    metadata = decision.to_metadata() | {
        "clean_entry_point": (
            "financial_engine.shareholder_waterfall."
            "run_project_shareholder_waterfall_model"
        ),
        "scenario": scenario,
        "calculation_count": 1,
    }
    return CleanProductionRun(
        g2c_result=g2c,
        project_inputs=effective_inputs,
        base_project_inputs=project_inputs,
        scenario=scenario,
        decision=decision,
        authority_metadata=metadata,
    )
