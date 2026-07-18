"""
finco_parity.financial_engine_candidate — Phase 2A clean-engine candidate provider.

Loads the committed baseline project inputs, adapts them to the clean
OperatingModelInput contract, runs the clean orchestrator, and serializes an
honest Phase 2A candidate snapshot.

Project identity mapping (which factory to call for which baseline) lives
exclusively here, in finco_parity. It is forbidden inside financial_engine.

Import boundary
---------------
This module may import from:
  - Python standard library
  - finco_parity.*
  - financial_engine.*   (the clean engine)
  - app.*               (project factories only — deferred import)
  - finco_core.*        (deferred import where needed)
It must NOT import from main_web, main_api, persistence, FastAPI.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from finco_parity.manifest import (
    SNAPSHOTS_DIR,
    get_manifest_entry,
)
from finco_parity.schema import (
    SCHEMA_VERSION,
    UNAVAILABLE,
    _REQUIRED_EQUITY,
    _REQUIRED_RETURNS,
    _REQUIRED_SENIOR_DEBT,
    _REQUIRED_SHL,
    _REQUIRED_TAX_AND_CFADS,
    validate_snapshot,
)
from financial_engine.version import ENGINE_VERSION

# Candidate run-path identifier (distinct from the legacy run path).
CANDIDATE_RUN_PATH_ID = "financial_engine.orchestrator.run_operating_model"

# Maps baseline_id → (factory_module_attr, input_source_id)
_BASELINE_REGISTRY: dict[str, dict[str, str]] = {
    "tuho": {
        "factory_attr": "create_default_tuho_wind1",
        "input_source_id": "project_factories.create_default_tuho_wind1",
    },
    "oborovo": {
        "factory_attr": "create_default_oborovo",
        "input_source_id": "project_factories.create_default_oborovo",
    },
    "generic_solar": {
        "factory_attr": "create_default_solar_project",
        "input_source_id": "project_factories.create_default_solar_project",
    },
    "generic_wind": {
        "factory_attr": "create_default_wind_project",
        "input_source_id": "project_factories.create_default_wind_project",
    },
}


@dataclass(frozen=True)
class CleanEngineCandidate:
    """Serializable Phase 2A candidate produced by the clean engine."""
    baseline_id: str
    snapshot: dict[str, Any]
    engine_version: str


class FinancialEngineCandidateProvider:
    """CandidateSnapshotProvider implementation for the Phase 2A clean engine.

    Satisfies the finco_parity.candidate.CandidateSnapshotProvider protocol.
    Called exactly once per baseline by the Phase 1C dual-run orchestrator.
    """

    def capture_snapshot(
        self,
        baseline_id: str,
        reference: Any,  # BaselineReference — typed loosely to avoid circular import
    ) -> dict[str, Any]:
        """Generate and return a Phase 2A candidate snapshot.

        Uses the committed baseline_commit_sha from the reference to stamp the
        candidate snapshot identity, enabling identity validation to pass.
        """
        return generate_candidate_snapshot(
            baseline_id,
            baseline_commit_sha=reference.baseline_commit_sha,
        )


def _load_project_inputs(baseline_id: str) -> Any:
    """Load the canonical ProjectInputs for the given baseline via its factory."""
    entry = _BASELINE_REGISTRY[baseline_id]
    from app import project_factories
    factory = getattr(project_factories, entry["factory_attr"])
    return factory()


def _build_all_none_list(n: int) -> list:
    return [UNAVAILABLE] * n


def _serialize_period_grid(result: Any) -> list[dict[str, Any]]:
    """Serialize operating periods from the clean engine result.

    Only operating periods are emitted, matching the committed baseline structure.
    is_construction and start_date are emitted as null (matching baseline null values).
    """
    rows = []
    for p in result.periods:
        if not p.is_operation:
            continue
        rows.append({
            "date": p.period_end.isoformat(),
            "is_construction": UNAVAILABLE,
            "is_operation": p.is_operation,
            "period_in_year": p.period_in_year,
            "period_index": p.period_index,
            "start_date": UNAVAILABLE,
            "year_index": p.year_index,
        })
    return rows


def _serialize_operating_schedules(result: Any, n_periods: int) -> dict[str, Any]:
    """Serialize Phase 2A operating schedules from the clean engine result."""
    op_periods = [p for p in result.periods if p.is_operation]
    assert len(op_periods) == n_periods

    return {
        "production_mwh": [p.production_mwh for p in op_periods],
        "revenue_keur": [p.revenue_keur for p in op_periods],
        "opex_keur": [p.opex_keur for p in op_periods],
        "ebitda_keur": [p.ebitda_keur for p in op_periods],
        "book_depreciation_keur": [p.book_depreciation_keur for p in op_periods],
        "tax_depreciation_keur": [p.tax_depreciation_keur for p in op_periods],
    }


def _build_all_none_tax_and_cfads(n: int) -> dict[str, Any]:
    return {field: _build_all_none_list(n) for field in sorted(_REQUIRED_TAX_AND_CFADS)}


def _build_all_none_financing(n: int) -> dict[str, Any]:
    return {
        "senior_debt": {field: _build_all_none_list(n) for field in sorted(_REQUIRED_SENIOR_DEBT)},
        "shl": {field: _build_all_none_list(n) for field in sorted(_REQUIRED_SHL)},
        "equity": {field: _build_all_none_list(n) for field in sorted(_REQUIRED_EQUITY)},
    }


def _build_all_none_returns() -> dict[str, Any]:
    return {field: UNAVAILABLE for field in sorted(_REQUIRED_RETURNS)}


def _build_unavailable_fields(n_periods: int) -> dict[str, list[str]]:
    """Build the unavailable_fields declaration for a Phase 2A candidate snapshot."""
    fields: dict[str, list[str]] = {}

    # period_grid: is_construction and start_date match the baseline null values.
    # They participate in OPERATING_CORE_V1 comparison; both sides are null.
    fields["period_grid"] = sorted(["is_construction", "start_date"])

    # tax_and_cfads: all fields unavailable.
    if n_periods > 0:
        fields["tax_and_cfads"] = sorted(list(_REQUIRED_TAX_AND_CFADS))

    # financing: all sub-section fields unavailable.
    if n_periods > 0:
        fields["financing.senior_debt"] = sorted(list(_REQUIRED_SENIOR_DEBT))
        fields["financing.shl"] = sorted(list(_REQUIRED_SHL))
        fields["financing.equity"] = sorted(list(_REQUIRED_EQUITY))

    return fields


def generate_candidate_snapshot(
    baseline_id: str,
    *,
    baseline_commit_sha: str = "",
) -> dict[str, Any]:
    """Generate an honest Phase 2A candidate snapshot for the given baseline.

    Steps:
    1. Load committed baseline project inputs via the factory function.
    2. Adapt to OperatingModelInput.
    3. Run run_operating_model.
    4. Serialize an honest Phase 2A candidate snapshot.

    The snapshot passes schema validation with all unimplemented sections
    declared in unavailable_sections / unavailable_fields.
    """
    if baseline_id not in _BASELINE_REGISTRY:
        raise ValueError(
            f"Unknown baseline_id {baseline_id!r}. "
            f"Valid: {sorted(_BASELINE_REGISTRY)}"
        )

    registry_entry = _BASELINE_REGISTRY[baseline_id]
    input_source_id = registry_entry["input_source_id"]

    # Step 1: Load canonical ProjectInputs.
    project_inputs = _load_project_inputs(baseline_id)

    # Step 2: Adapt to OperatingModelInput.
    from financial_engine.adapters.project_inputs import from_project_inputs
    clean_inputs = from_project_inputs(
        project_inputs,
        source_id=input_source_id,
        baseline_commit_sha=baseline_commit_sha,
    )

    # Step 3: Run the clean operating model.
    from financial_engine.orchestrator import run_operating_model
    result = run_operating_model(clean_inputs)

    # Step 4: Serialize an honest Phase 2A candidate snapshot.
    period_grid = _serialize_period_grid(result)
    n_periods = len(period_grid)

    operating_schedules = _serialize_operating_schedules(result, n_periods)
    tax_and_cfads = _build_all_none_tax_and_cfads(n_periods)
    financing = _build_all_none_financing(n_periods)
    returns = _build_all_none_returns()
    unavailable_fields = _build_unavailable_fields(n_periods)

    # Warnings from validation (if any non-error warnings).
    warnings: list[str] = [
        f"{issue.code} {issue.path}: {issue.message}"
        for issue in result.validation_issues
        if issue.severity.value == "WARNING"
    ]

    snapshot: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "baseline_id": baseline_id,
        "engine_designation": ENGINE_VERSION,
        "baseline_commit_sha": baseline_commit_sha,
        "run_path_id": CANDIDATE_RUN_PATH_ID,
        "input_source_id": input_source_id,
        "warnings": warnings,
        "unavailable_sections": sorted(["financial_statements"]),
        "unavailable_fields": {
            k: sorted(v) for k, v in sorted(unavailable_fields.items())
        },
        "period_grid": period_grid,
        "operating_schedules": operating_schedules,
        "tax_and_cfads": tax_and_cfads,
        "financing": financing,
        "financial_statements": UNAVAILABLE,
        "returns": returns,
    }

    validate_snapshot(snapshot)
    return snapshot


def get_candidate_snapshot(baseline_id: str, *, baseline_commit_sha: str = "") -> dict[str, Any]:
    """Public entry point: generate and validate the Phase 2A candidate snapshot."""
    return generate_candidate_snapshot(
        baseline_id,
        baseline_commit_sha=baseline_commit_sha,
    )
