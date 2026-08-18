"""Project-owned G2A financing fixed point over existing clean kernels."""

from __future__ import annotations

from dataclasses import replace

from finco_core.inputs import GearingBasisMode, ProjectInputs, SponsorFundingMode
from financial_engine.adapters.project_inputs import (
    build_senior_debt_model_input_from_project_inputs,
)
from financial_engine.financing.contracts import ProjectFinancingResult, ProjectUses
from financial_engine.financing.project_uses import compute_project_uses
from financial_engine.financing.stack import (
    build_construction_funding_schedule,
    reconcile_financing_stack,
)
from financial_engine.orchestrator import run_senior_debt_model
from financial_engine.shl.construction import (
    build_shl_construction_draw_schedule,
    compute_shl_construction_schedule,
    ShlConstructionPeriodInput,
)
from finco_core.inputs._models import SponsorFundingTimingPolicy

# Construction SHL accrual semantics (Fix 3):
#
# None  → no explicit construction DCF authority. Fall back to model_result.shareholder_loan
#         (backward-compat path). Generic Solar/Wind return 0 PIK here because those projects
#         have no explicit construction SHL DCF configured.
# 0.0   → explicit zero accrual. Distinct from None — activates timing path but produces 0 PIK.
# > 0.0 → timing policy resolves construction draw schedule post-convergence.
#          Single-period consistency: for one construction period ALL_AT_FC == PRO_RATA
#          (full principal at that one period), so the post-convergence schedule is
#          identical to what the model already computed — no dual truth.
#          Full multi-period causal integration (timing inside the fixed-point loop)
#          requires Fix 4+ with the calendar-period construction schedule.


def _project_uses(project_inputs: ProjectInputs) -> ProjectUses:
    """Thin wrapper — delegates to the canonical compute_project_uses authority."""
    return compute_project_uses(project_inputs)


def run_project_financing_model(
    project_inputs: ProjectInputs,
    *,
    source_id: str = "",
    baseline_commit_sha: str = "",
    convergence_tolerance_keur: float = 1e-7,
    maximum_iterations: int = 50,
) -> ProjectFinancingResult:
    """Run the derived-SHL/Senior fixed point for an explicitly enabled project."""
    fin = project_inputs.financing
    if fin.sponsor_funding_mode is None:
        raise ValueError("G2A_SPONSOR_FUNDING_MODE_EXPLICIT_INPUT_REQUIRED")
    if fin.gearing_basis_mode != GearingBasisMode.TOTAL_PROJECT_USES:
        raise ValueError("G2A_GEARING_BASIS_EXPLICIT_INPUT_REQUIRED")

    uses = _project_uses(project_inputs)
    gearing_capacity = uses.total_project_uses_keur * fin.gearing_ratio
    # Neutral seed: the factory's legacy clean_shl_principal_keur is deliberately
    # not read. The authoritative principal must emerge from the fixed point.
    candidate_shl = 0.0

    model_result = None
    authoritative_dscr_capacity = 0.0
    maximum_difference = float("inf")
    derived_shl = candidate_shl
    additional_equity = 0.0  # derived residual; overwritten each iteration by reconcile_financing_stack
    for iteration in range(1, maximum_iterations + 1):
        capacity_inputs = replace(
            project_inputs,
            financing=replace(
                fin,
                clean_shl_principal_keur=candidate_shl,
                sponsor_funding_mode=None,
                gearing_basis_mode=None,
            ),
        )
        capacity_model_input = build_senior_debt_model_input_from_project_inputs(
            capacity_inputs,
            source_id=source_id,
            baseline_commit_sha=baseline_commit_sha,
        )
        capacity_result = run_senior_debt_model(capacity_model_input)
        if capacity_result.senior_debt is None:
            raise RuntimeError("G2A DSCR capacity result is unavailable")
        authoritative_dscr_capacity = capacity_result.senior_debt.debt_size_keur
        expected_final_senior = min(authoritative_dscr_capacity, gearing_capacity)

        funded_inputs = replace(
            project_inputs,
            financing=replace(fin, clean_shl_principal_keur=candidate_shl),
        )
        funded_model_input = build_senior_debt_model_input_from_project_inputs(
            funded_inputs,
            source_id=source_id,
            baseline_commit_sha=baseline_commit_sha,
        )
        # The adapter now correctly maps gearing_basis_mode=TOTAL_PROJECT_USES to
        # COMBINED_MINIMUM with the canonical eligible cost and maximum_gearing.
        # No downstream patch is required here.
        model_result = run_senior_debt_model(funded_model_input)
        senior = model_result.senior_debt
        if senior is None:
            raise RuntimeError("G2A Senior result is unavailable")
        diagnosed_gearing = senior.diagnostics.get("gearing_debt_capacity_keur")
        if diagnosed_gearing is None:
            raise RuntimeError("G2A Senior capacity audit fields are unavailable")
        if abs(diagnosed_gearing - gearing_capacity) > 1e-7:
            raise RuntimeError("G2A gearing capacity handshake failed")
        if abs(senior.debt_size_keur - expected_final_senior) > convergence_tolerance_keur:
            raise RuntimeError(
                "G2A_FINAL_SENIOR_DOES_NOT_MATCH_CAPACITY_MINIMUM: "
                f"expected={expected_final_senior}, actual={senior.debt_size_keur}"
            )

        derived_shl, additional_equity = reconcile_financing_stack(
            total_project_uses_keur=uses.total_project_uses_keur,
            final_senior_commitment_keur=senior.debt_size_keur,
            junior_or_other_main_project_funding_keur=fin.junior_or_other_project_funding_keur,
            share_capital_keur=fin.share_capital_keur,
            share_premium_keur=fin.share_premium_keur,
            other_equity_funding_before_shl_keur=fin.other_equity_funding_before_shl_keur,
            sponsor_funding_mode=fin.sponsor_funding_mode,
        )
        maximum_difference = abs(derived_shl - candidate_shl)
        if maximum_difference <= convergence_tolerance_keur:
            break
        candidate_shl = derived_shl
    else:
        raise RuntimeError("G2A_SHL_SENIOR_FIXED_POINT_DID_NOT_CONVERGE")

    assert model_result is not None and model_result.senior_debt is not None

    # Construction SHL schedule — see module-level comment for None/0.0/explicit-DCF semantics.
    shl_pik = 0.0
    opening_operating_shl = 0.0

    if (
        fin.shl_construction_day_count_fraction is not None
        and fin.shl_construction_day_count_fraction > 0.0
    ):
        # Explicit positive DCF: timing policy resolves construction draw schedule.
        # Post-convergence for single-period (consistent: ALL_AT_FC == PRO_RATA for 1 period).
        # Fix 4+ required for full multi-period causal loop.
        timing_policy = fin.sponsor_funding_timing_policy
        total_dcf = fin.shl_construction_day_count_fraction
        construction_periods_input = (
            ShlConstructionPeriodInput(
                draw_keur=0.0,  # placeholder, overridden by build_shl_construction_draw_schedule
                day_count_fraction=total_dcf,
                period_index=0,
            ),
        )
        draw_schedule = build_shl_construction_draw_schedule(
            shl_cash_principal_keur=derived_shl,
            construction_periods=construction_periods_input,
            policy=timing_policy,
        )
        construction_shl_schedule = compute_shl_construction_schedule(
            opening_balance_keur=0.0,
            periods=draw_schedule,
            annual_rate=fin.shl_rate,
            method=fin.shl_construction_interest_method,
        )
        shl_pik = construction_shl_schedule.total_pik_keur
        opening_operating_shl = construction_shl_schedule.opening_operating_shl_balance_keur
    elif model_result.shareholder_loan is not None:
        # Backward-compat path: no explicit construction DCF. Read from canonical model result.
        # Generic Solar/Wind return 0 PIK here (no construction SHL DCF configured).
        shl = model_result.shareholder_loan
        construction_indices = {
            period.period_index for period in model_result.periods if period.is_construction
        }
        shl_pik = sum(
            value
            for idx, value in zip(shl.period_indices, shl.shl_pik_interest_keur)
            if idx in construction_indices
        )
        first_operating_index = next(
            period.period_index for period in model_result.periods if period.is_operation
        )
        opening_operating_shl = dict(
            zip(shl.period_indices, shl.shl_opening_keur)
        ).get(first_operating_index, 0.0)

    funding = build_construction_funding_schedule(
        construction_period_count=project_inputs.info.construction_months,
        total_project_uses_keur=uses.total_project_uses_keur,
        senior_keur=model_result.senior_debt.debt_size_keur,
        junior_keur=fin.junior_or_other_project_funding_keur,
        share_capital_keur=fin.share_capital_keur,
        share_premium_keur=fin.share_premium_keur,
        other_committed_equity_keur=fin.other_equity_funding_before_shl_keur,
        additional_equity_keur=additional_equity,
        shl_cash_keur=derived_shl,
    )
    return ProjectFinancingResult(
        project_model_result=model_result,
        project_uses=uses,
        dscr_debt_capacity_keur=authoritative_dscr_capacity,
        gearing_basis_keur=uses.total_project_uses_keur,
        gearing_ratio=fin.gearing_ratio,
        gearing_debt_capacity_keur=gearing_capacity,
        final_senior_commitment_keur=model_result.senior_debt.debt_size_keur,
        binding_senior_constraint=str(model_result.senior_debt.binding_constraint),
        junior_or_other_main_project_funding_keur=fin.junior_or_other_project_funding_keur,
        share_capital_keur=fin.share_capital_keur,
        share_premium_keur=fin.share_premium_keur,
        other_equity_funding_before_shl_keur=fin.other_equity_funding_before_shl_keur,
        additional_equity_keur=additional_equity,
        derived_shl_cash_principal_keur=derived_shl,
        shl_construction_pik_keur=shl_pik,
        opening_operating_shl_balance_keur=opening_operating_shl,
        construction_funding=funding,
        fixed_point_iteration_count=iteration,
        fixed_point_maximum_difference_keur=maximum_difference,
    )
