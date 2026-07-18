"""
finco_parity.financial_engine_tax_cfads_candidate — Phase 2B tax+CFADS candidate provider.

Loads the committed baseline project inputs, adapts them to TaxCfadsModelInput,
runs the Phase 2B orchestrator, and serializes an honest Phase 2B candidate snapshot.

Exogenous interest is sourced from the baseline snapshot's financing section
(senior_debt.interest_keur + shl.interest_keur per period). The candidate does NOT
use project-identity-aware tax parameters — a canonical TaxPolicy is applied.

Waterfall rows (r69, r84, r99, r102, fcf_for_shl) are declared as unavailable_fields
because they belong to Phase 2C+ and are not computed by the Phase 2B engine.

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
from pathlib import Path
from typing import Any

from finco_parity.manifest import SNAPSHOTS_DIR, get_manifest_entry
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

CANDIDATE_RUN_PATH_ID = "financial_engine.orchestrator.run_tax_cfads_model"

# Waterfall rows from the baseline schema that Phase 2B does not implement.
_WATERFALL_UNAVAILABLE: frozenset[str] = frozenset({
    "r69_fcf_banks_keur",
    "r84_fcf_junior_keur",
    "r99_fcf_for_distribution_keur",
    "r102_fcf_for_shl_keur",
    "fcf_for_shl_keur",
})

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

# Canonical Phase 2B TaxPolicy — same for all baselines.
# Project-identity-aware parameters (actual tax rates, ATAD specifics) live in
# project factories and are NOT copied here.  The canonical policy uses HR defaults.
_CANONICAL_TAX_POLICY_PARAMS: dict[str, Any] = {
    "policy_id": "canonical_phase2b_hr",
    "policy_version": "1.0",
    "corporate_rate": 0.18,
    "periods_per_tax_year": 2,
    "loss_carryforward_years": 5,
    "atad_enabled": True,
    "atad_ebitda_limit": 0.30,
    "atad_de_minimis_threshold_keur_annual": 3_000.0,
    "cash_tax_timing": "tax_year_last_period",
    "cash_tax_payment_lag_periods": 0,
}


def _load_project_inputs(baseline_id: str) -> Any:
    entry = _BASELINE_REGISTRY[baseline_id]
    from app import project_factories
    factory = getattr(project_factories, entry["factory_attr"])
    return factory()


def _load_baseline_snapshot(baseline_id: str) -> dict[str, Any]:
    """Load the committed baseline snapshot for the given baseline_id."""
    entry = get_manifest_entry(baseline_id)
    snapshot_path = SNAPSHOTS_DIR / f"{baseline_id}.json"
    with open(snapshot_path) as f:
        return json.load(f)


def _build_exogenous_interest(
    baseline_snapshot: dict[str, Any],
    operating_periods: list,
) -> tuple:
    """Extract per-period exogenous interest from the baseline snapshot financing data.

    Uses senior_debt.interest_keur + shl.interest_keur from the baseline, indexed
    positionally to the operating periods (baseline and candidate share the same grid).

    Only operating periods are used; construction periods have zero interest.
    """
    from financial_engine.inputs import PeriodInterestInput

    financing = baseline_snapshot.get("financing") or {}
    senior_debt = financing.get("senior_debt") or {}
    shl = financing.get("shl") or {}

    senior_interest_list = senior_debt.get("interest_keur") or []
    shl_interest_list = shl.get("interest_keur") or []

    interest_inputs: list[PeriodInterestInput] = []
    for i, p in enumerate(operating_periods):
        senior_keur = float(senior_interest_list[i]) if (
            i < len(senior_interest_list) and senior_interest_list[i] is not None
        ) else 0.0
        shl_keur = float(shl_interest_list[i]) if (
            i < len(shl_interest_list) and shl_interest_list[i] is not None
        ) else 0.0
        if senior_keur != 0.0 or shl_keur != 0.0:
            interest_inputs.append(PeriodInterestInput(
                period_index=p.period_index,
                senior_interest_keur=senior_keur,
                shl_interest_keur=shl_keur,
                other_interest_keur=0.0,
            ))

    return tuple(interest_inputs)


def _build_canonical_tax_policy():
    from financial_engine.policies.tax import TaxPolicy, CashTaxTiming
    p = _CANONICAL_TAX_POLICY_PARAMS
    return TaxPolicy(
        policy_id=p["policy_id"],
        policy_version=p["policy_version"],
        corporate_rate=p["corporate_rate"],
        periods_per_tax_year=p["periods_per_tax_year"],
        loss_carryforward_years=p["loss_carryforward_years"],
        atad_enabled=p["atad_enabled"],
        atad_ebitda_limit=p["atad_ebitda_limit"],
        atad_de_minimis_threshold_keur_annual=p["atad_de_minimis_threshold_keur_annual"],
        cash_tax_timing=CashTaxTiming(p["cash_tax_timing"]),
        cash_tax_payment_lag_periods=p["cash_tax_payment_lag_periods"],
    )


def _serialize_period_grid(result: Any) -> list[dict[str, Any]]:
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


def _serialize_tax_and_cfads(
    result: Any,
    op_period_indices: frozenset[int],
) -> dict[str, Any]:
    """Serialize Phase 2B tax_and_cfads, setting waterfall rows to UNAVAILABLE."""
    tc = result.tax_and_cfads
    if tc is None:
        return {field: UNAVAILABLE for field in sorted(_REQUIRED_TAX_AND_CFADS)}

    # Build index → position mapping for operating periods only
    op_period_index_ordered = [
        p.period_index for p in result.periods if p.is_operation
    ]
    pos_map: dict[int, int] = {idx: i for i, idx in enumerate(op_period_index_ordered)}
    n = len(op_period_index_ordered)

    def _reindex(values: tuple[float, ...]) -> list[float | None]:
        """Reindex from all-period ordering to operating-period ordering."""
        out: list[float | None] = [UNAVAILABLE] * n
        for period_idx_in_full, v in zip(tc.period_indices, values):
            pos = pos_map.get(period_idx_in_full)
            if pos is not None:
                out[pos] = v
        return out

    out: dict[str, Any] = {}

    out["taxable_profit_keur"] = _reindex(tc.taxable_profit_keur)
    out["taxable_income_before_losses_audit_keur"] = _reindex(
        tc.taxable_income_before_losses_audit_keur
    )
    out["taxable_profit_after_losses_audit_keur"] = _reindex(
        tc.taxable_profit_after_losses_audit_keur
    )
    out["cit_accrual_audit_keur"] = _reindex(tc.cit_accrual_audit_keur)
    out["cash_tax_current_period_audit_keur"] = _reindex(tc.corporate_tax_cash_keur)
    out["corporate_tax_cash_keur"] = _reindex(tc.corporate_tax_cash_keur)
    out["tax_keur"] = _reindex(tc.tax_keur)
    out["cash_tax_bridge_reconciliation_keur"] = _reindex(
        tc.cash_tax_bridge_reconciliation_keur
    )
    out["tax_loss_opening_audit_keur"] = _reindex(tc.tax_loss_opening_audit_keur)
    out["tax_loss_used_audit_keur"] = _reindex(tc.tax_loss_used_audit_keur)
    out["tax_loss_closing_audit_keur"] = _reindex(tc.tax_loss_closing_audit_keur)
    out["tax_depreciation_audit_keur"] = _reindex(tc.tax_depreciation_audit_keur)
    out["fiscal_reintegration_audit_keur"] = _reindex(tc.fiscal_reintegration_audit_keur)
    out["cf_after_tax_keur"] = _reindex(tc.cf_after_tax_keur)

    # Waterfall rows — not implemented in Phase 2B
    for field in sorted(_WATERFALL_UNAVAILABLE):
        out[field] = [UNAVAILABLE] * n

    return out


def _build_unavailable_fields(n_periods: int) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    fields["period_grid"] = sorted(["is_construction", "start_date"])
    if n_periods > 0:
        fields["tax_and_cfads"] = sorted(list(_WATERFALL_UNAVAILABLE))
        fields["financing.senior_debt"] = sorted(list(_REQUIRED_SENIOR_DEBT))
        fields["financing.shl"] = sorted(list(_REQUIRED_SHL))
        fields["financing.equity"] = sorted(list(_REQUIRED_EQUITY))
    return fields


def _build_all_none_list(n: int) -> list:
    return [UNAVAILABLE] * n


def _build_all_none_financing(n: int) -> dict[str, Any]:
    return {
        "senior_debt": {field: _build_all_none_list(n) for field in sorted(_REQUIRED_SENIOR_DEBT)},
        "shl": {field: _build_all_none_list(n) for field in sorted(_REQUIRED_SHL)},
        "equity": {field: _build_all_none_list(n) for field in sorted(_REQUIRED_EQUITY)},
    }


def _build_all_none_returns() -> dict[str, Any]:
    return {field: UNAVAILABLE for field in sorted(_REQUIRED_RETURNS)}


def generate_tax_cfads_candidate_snapshot(
    baseline_id: str,
    *,
    baseline_commit_sha: str = "",
) -> dict[str, Any]:
    """Generate an honest Phase 2B candidate snapshot for the given baseline.

    Steps:
    1. Load baseline snapshot to extract exogenous interest per period.
    2. Load committed baseline project inputs via the factory function.
    3. Adapt to OperatingModelInput.
    4. Build TaxCfadsModelInput with canonical TaxPolicy + exogenous interest.
    5. Run run_tax_cfads_model.
    6. Serialize an honest Phase 2B candidate snapshot.
       - Waterfall rows declared unavailable in unavailable_fields.
       - cfads_keur is a Phase 2B-only field, not compared vs baseline.
    """
    if baseline_id not in _BASELINE_REGISTRY:
        raise ValueError(
            f"Unknown baseline_id {baseline_id!r}. "
            f"Valid: {sorted(_BASELINE_REGISTRY)}"
        )

    registry_entry = _BASELINE_REGISTRY[baseline_id]
    input_source_id = registry_entry["input_source_id"]

    # Step 1: Load baseline snapshot for exogenous interest
    baseline_snapshot = _load_baseline_snapshot(baseline_id)
    if not baseline_commit_sha:
        baseline_commit_sha = baseline_snapshot.get("baseline_commit_sha", "")

    # Step 2: Load canonical ProjectInputs
    project_inputs = _load_project_inputs(baseline_id)

    # Step 3: Adapt to OperatingModelInput
    from financial_engine.adapters.project_inputs import from_project_inputs
    clean_inputs = from_project_inputs(
        project_inputs,
        source_id=input_source_id,
        baseline_commit_sha=baseline_commit_sha,
    )

    # Run Phase 2A first to get operating period indices for interest mapping
    from financial_engine.orchestrator import run_operating_model
    op_result = run_operating_model(clean_inputs)
    operating_periods = [p for p in op_result.periods if p.is_operation]

    # Step 4: Build TaxCfadsModelInput
    from financial_engine.inputs import TaxCalculationInput, TaxCfadsModelInput

    period_interest = _build_exogenous_interest(baseline_snapshot, operating_periods)
    policy = _build_canonical_tax_policy()

    tax_input = TaxCalculationInput(
        policy=policy,
        opening_loss_vintages=(),
        period_interest=period_interest,
        period_adjustments=(),
    )
    model_input = TaxCfadsModelInput(operating=clean_inputs, tax=tax_input)

    # Step 5: Run Phase 2B engine
    from financial_engine.orchestrator import run_tax_cfads_model
    result = run_tax_cfads_model(model_input)

    # Step 6: Serialize
    period_grid = _serialize_period_grid(result)
    n_periods = len(period_grid)
    op_period_indices = frozenset(row["period_index"] for row in period_grid)

    operating_schedules = _serialize_operating_schedules(result, n_periods)
    tax_and_cfads = _serialize_tax_and_cfads(result, op_period_indices)
    financing = _build_all_none_financing(n_periods)
    returns = _build_all_none_returns()
    unavailable_fields = _build_unavailable_fields(n_periods)

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


class FinancialEngineTaxCfadsCandidateProvider:
    """CandidateSnapshotProvider for the Phase 2B clean engine."""

    def capture_snapshot(
        self,
        baseline_id: str,
        reference: Any,
    ) -> dict[str, Any]:
        return generate_tax_cfads_candidate_snapshot(
            baseline_id,
            baseline_commit_sha=reference.baseline_commit_sha,
        )
