"""Project-owned G2A financing fixed point over existing clean kernels."""

from __future__ import annotations

from dataclasses import replace

from finco_core.inputs import GearingBasisMode, ProjectInputs, SponsorFundingMode
from financial_engine.adapters.project_inputs import (
    build_senior_debt_model_input_from_project_inputs,
)
from domain.construction.config import FundingSourceCaps
from domain.construction.funding_allocation import allocate_source_waterfall
from financial_engine.financing.contracts import (
    ConstructionFinancingResult,
    ProjectFinancingResult,
    ProjectUses,
)
from financial_engine.financing.project_uses import compute_project_uses
from financial_engine.financing.stack import (
    build_construction_funding_schedule,
    reconcile_financing_stack,
)
from financial_engine.adapters.project_inputs import from_project_inputs
from financial_engine.orchestrator import run_operating_model, run_senior_debt_model
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
# > 0.0 → timing policy resolves construction draw schedule per-period inside the fixed-point loop.
#          Multi-period causal integration: per-period DCFs are derived from the operating model
#          (run once pre-loop, calendar-derived, timing-policy-independent).
#          ALL_AT_FC vs PRO_RATA produce different opening SHL and hence different DSCR capacity.
#          Backward compat: None/0.0 DCF path unchanged (Solar PIK=0, Wind PIK=0).


def _project_uses(project_inputs: ProjectInputs) -> ProjectUses:
    """Thin wrapper — delegates to the canonical compute_project_uses authority."""
    return compute_project_uses(project_inputs)


def _run_with_construction_idc(
    *,
    project_inputs: ProjectInputs,
    source_id: str,
    baseline_commit_sha: str,
    outer_tolerance_keur: float,
    outer_max_iterations: int,
) -> "ProjectFinancingResult":
    """Outer G2A / construction IDC fixed point for construction_financing.enabled=True.

    Each outer iteration:
      1. Derives canonical construction CAPEX amounts from ProjectInputs.capex.
      2. Runs Stage B2 (with current Senior/SHL estimates) to compute IDC, commitment
         fee, and structuring fee.
      3. Applies those costs IMMUTABLY to the original base CapexStructure (never
         accumulates across iterations).
      4. Recomputes Total Project Uses on the updated CapexStructure.
      5. Calls the inner SHL/Senior fixed point (run_project_financing_model without
         construction gate) on the updated project inputs.
      6. Checks outer convergence: max(|ΔSenior|, |ΔSHL|, |ΔProjectUses|, |ΔIDC|, |Δfee|).
      7. After convergence: one final verification iteration confirms idempotence.

    On convergence: builds ConstructionFinancingResult and returns full ProjectFinancingResult.
    """
    from finco_core.construction.stage_b2 import (
        apply_capitalized_financing_costs,
        run_stage_b2,
        CapitalizedFinancingCosts,
    )
    from financial_engine.construction.adapter import (
        build_construction_runtime_config,
    )

    fin = project_inputs.financing
    cf = fin.construction_financing  # guaranteed non-None and enabled

    # Validate: fail if manual IDC/fees already set (would create dual authority)
    orig_capex = project_inputs.capex
    if (
        getattr(orig_capex, "idc_keur", 0.0) != 0.0
        or getattr(orig_capex, "commitment_fees_keur", 0.0) != 0.0
        or getattr(orig_capex, "bank_fees_keur", 0.0) != 0.0
    ):
        raise ValueError(
            "PR9_MANUAL_DERIVED_CONSTRUCTION_COST_CONFLICT: "
            "construction_financing.enabled=True but CapexStructure already contains "
            "non-zero idc_keur/commitment_fees_keur/bank_fees_keur. "
            "Clear those fields when using typed construction authority."
        )

    # VAT facility fail-closed: any VAT inputs raise immediately.
    if any(getattr(p, "vat_facility_active", False) for p in cf.periods):
        raise ValueError(
            "PR9_VAT_FACILITY_DEFERRED: one or more ConstructionPeriodSpec has vat_facility_active=True. "
            "VAT facility is not supported in PR-9."
        )
    if getattr(orig_capex, "vat_costs_keur", 0.0) != 0:
        raise ValueError(
            f"PR9_VAT_FACILITY_DEFERRED: orig_capex.vat_costs_keur={getattr(orig_capex, 'vat_costs_keur', 0.0)} != 0. "
            "VAT facility is not supported in PR-9."
        )
    if getattr(orig_capex, "vat_facility_idc_keur", 0.0) != 0:
        raise ValueError(
            f"PR9_VAT_FACILITY_DEFERRED: orig_capex.vat_facility_idc_keur={getattr(orig_capex, 'vat_facility_idc_keur', 0.0)} != 0. "
            "VAT facility is not supported in PR-9."
        )
    if getattr(orig_capex, "vat_facility_commitment_fee_keur", 0.0) != 0:
        raise ValueError(
            f"PR9_VAT_FACILITY_DEFERRED: orig_capex.vat_facility_commitment_fee_keur={getattr(orig_capex, 'vat_facility_commitment_fee_keur', 0.0)} != 0. "
            "VAT facility is not supported in PR-9."
        )

    # Resolve CAPEX amounts from canonical CapexStructure.
    # Construction timing inputs own payment_weights; amounts come from ProjectInputs.capex.
    capex_amounts: dict[str, float] = {}
    for item in cf.capex_items:
        val = getattr(orig_capex, item.code, None)
        if val is None:
            raise ValueError(
                f"PR9_CONSTRUCTION_CAPEX_AUTHORITY_MISMATCH: "
                f"construction capex_item.code='{item.code}' not found in ProjectInputs.capex"
            )
        capex_amounts[item.code] = float(getattr(val, "amount_keur", val))

    # Fix 1: validate CAPEX authority using the correct property name.
    canonical_hard_capex = orig_capex.hard_capex_keur

    # Validate: no duplicate codes
    codes_seen: list[str] = [item.code for item in cf.capex_items]
    if len(codes_seen) != len(set(codes_seen)):
        from collections import Counter
        dupes = [c for c, n in Counter(codes_seen).items() if n > 1]
        raise ValueError(
            f"PR9_CONSTRUCTION_CAPEX_AUTHORITY_MISMATCH: "
            f"duplicate capex_item codes: {dupes}"
        )

    # Validate: no omitted non-zero canonical CAPEX fields
    capex_item_fields = getattr(orig_capex, "_CAPEX_ITEM_FIELDS", ())
    for field_code in capex_item_fields:
        field_val = getattr(orig_capex, field_code, None)
        if field_val is None:
            continue
        field_amount = float(getattr(field_val, "amount_keur", 0.0))
        if field_amount > outer_tolerance_keur and field_code not in capex_amounts:
            raise ValueError(
                f"PR9_CONSTRUCTION_CAPEX_AUTHORITY_MISMATCH: "
                f"non-zero canonical CAPEX field '{field_code}' (amount={field_amount:.6f} kEUR) "
                f"not present in construction capex_items"
            )

    # Validate: empty capex_items when canonical hard CAPEX > 0
    if not cf.capex_items and canonical_hard_capex > outer_tolerance_keur:
        raise ValueError(
            f"PR9_CONSTRUCTION_CAPEX_AUTHORITY_MISMATCH: "
            f"capex_items is empty but canonical hard CAPEX = {canonical_hard_capex:.6f} kEUR"
        )

    # Validate: totals match canonical hard_capex_keur
    construction_total = sum(capex_amounts.values())
    if abs(construction_total - canonical_hard_capex) > outer_tolerance_keur:
        raise ValueError(
            f"PR9_CONSTRUCTION_CAPEX_AUTHORITY_MISMATCH: "
            f"construction items total {construction_total:.6f} kEUR != "
            f"canonical hard CAPEX {canonical_hard_capex:.6f} kEUR"
        )

    # PR9_SHL_TIMELINE_AUTHORITY: when typed construction financing is enabled,
    # legacy construction_period_uses_keur must not independently set a different timeline.
    if (
        getattr(project_inputs.financing, "construction_period_uses_keur", None)
        and project_inputs.financing.construction_period_uses_keur
    ):
        raise ValueError(
            "PR9_DUAL_CONSTRUCTION_TIMELINE: typed construction_financing.periods is active "
            "but legacy construction_period_uses_keur is also set. "
            "Remove construction_period_uses_keur when using typed PR-9 construction financing."
        )

    # Outer state — all start at zero (neutral seed)
    prev_idc = 0.0
    prev_fee = 0.0
    prev_struct = 0.0
    prev_senior = 0.0
    prev_shl = 0.0
    prev_pik = 0.0
    prev_uses = 0.0
    outer_residual = float("inf")
    outer_iteration = 0
    working_inputs = project_inputs  # updated immutably each iteration

    # Seed step 1: run inner model once on original capex (zero IDC) to get
    # initial Senior/SHL/equity estimates.
    _seed_fin = replace(project_inputs.financing, construction_financing=None)
    _seed_inputs = replace(project_inputs, financing=_seed_fin)
    inner_result = run_project_financing_model(
        _seed_inputs,
        source_id=source_id,
        baseline_commit_sha=baseline_commit_sha,
        convergence_tolerance_keur=outer_tolerance_keur,
        maximum_iterations=outer_max_iterations,
    )

    # Enhanced seed step 2: run Stage B2 once (max_iterations=1) with seed Senior/SHL
    # to get an initial IDC + structuring estimate. Then re-run inner G2A with those
    # costs so Senior_1 is sized to include IDC+structuring before the outer loop starts.
    # This avoids needing senior_draw_ceiling_keur in the outer loop.
    # Inflate seed Senior to cover structuring fee and estimated IDC so Stage B2
    # can converge in the enhanced seed pass. Rough upper bound: seed_senior + 10% of CAPEX.
    # After enhanced seed G2A re-run, the outer loop gets properly-sized Senior_1.
    _struct_fee_estimate = 0.0
    if cf.structuring_fee is not None:
        _struct_fee_estimate = cf.structuring_fee.rate * cf.structuring_fee.basis_keur
    _idc_headroom_estimate = sum(capex_amounts.values()) * 0.10  # generous IDC upper bound
    _eseed_senior = inner_result.final_senior_commitment_keur + _struct_fee_estimate + _idc_headroom_estimate

    _eseed_runtime = build_construction_runtime_config(
        construction=cf,
        senior_commitment_keur=_eseed_senior,
        equity_available_keur=inner_result.share_capital_keur,
        shl_available_keur=inner_result.derived_shl_cash_principal_keur,
        capex_amounts_keur=capex_amounts,
        share_premium_keur=inner_result.share_premium_keur,
        other_committed_equity_keur=inner_result.other_equity_funding_before_shl_keur,
        additional_equity_keur=inner_result.additional_equity_keur,
        junior_keur=inner_result.junior_or_other_main_project_funding_keur,
    )
    # Use max_iterations=100 to get a fully-converged IDC estimate.
    # The inflated senior ceiling ensures structuring fee is covered.
    try:
        _eseed_b2 = run_stage_b2(_eseed_runtime)
        _eseed_capex = apply_capitalized_financing_costs(orig_capex, _eseed_b2.capitalized_financing_costs)
        _eseed_inputs2 = replace(project_inputs, capex=_eseed_capex)
        _eseed_fin2 = replace(_eseed_inputs2.financing, construction_financing=None)
        _eseed_inputs2 = replace(_eseed_inputs2, financing=_eseed_fin2)
        inner_result = run_project_financing_model(
            _eseed_inputs2,
            source_id=source_id,
            baseline_commit_sha=baseline_commit_sha,
            convergence_tolerance_keur=outer_tolerance_keur,
            maximum_iterations=outer_max_iterations,
        )
    except Exception:
        # If enhanced seed fails (e.g. convergence issue), fall back to seed-only Senior.
        pass

    stage_b2_result = None

    for outer_iteration in range(1, outer_max_iterations + 1):
        uses = _project_uses(working_inputs)
        working_fin = working_inputs.financing

        # Build equity/SHL/Senior estimates from previous inner result (full breakdown).
        shl_avail = inner_result.derived_shl_cash_principal_keur
        senior_estimate = inner_result.final_senior_commitment_keur

        # Run Stage B2 with full source breakdown from current inner result.
        # senior_commitment_keur = actual candidate Senior (correct commitment fee basis).
        # equity_available_keur = sum of all equity components as Stage B2 share_capital pool.
        # No senior_draw_ceiling: Senior is sized correctly via enhanced seed + iterative convergence.
        # We pass total_equity as equity_available_keur so that Stage B2 absorbs ALL equity first.
        _total_equity_for_b2 = (
            inner_result.share_capital_keur
            + inner_result.share_premium_keur
            + inner_result.other_equity_funding_before_shl_keur
            + inner_result.additional_equity_keur
        )
        runtime_cfg = build_construction_runtime_config(
            construction=cf,
            senior_commitment_keur=senior_estimate,
            equity_available_keur=_total_equity_for_b2,
            shl_available_keur=shl_avail,
            capex_amounts_keur=capex_amounts,
            # Pass zeros for breakdown fields since equity is aggregated above.
            share_premium_keur=0.0,
            other_committed_equity_keur=0.0,
            additional_equity_keur=0.0,
            junior_keur=inner_result.junior_or_other_main_project_funding_keur,
        )
        stage_b2_result = run_stage_b2(runtime_cfg)
        new_financing = stage_b2_result.capitalized_financing_costs

        # Apply costs IMMUTABLY from original base CapexStructure (not working_inputs.capex).
        updated_capex = apply_capitalized_financing_costs(orig_capex, new_financing)
        working_inputs = replace(project_inputs, capex=updated_capex)

        # Run inner SHL/Senior fixed point on updated inputs (construction gate disabled).
        # Temporarily clear construction_financing to avoid re-entering this function.
        inner_fin = replace(working_inputs.financing, construction_financing=None)
        inner_inputs = replace(working_inputs, financing=inner_fin)
        inner_result = run_project_financing_model(
            inner_inputs,
            source_id=source_id,
            baseline_commit_sha=baseline_commit_sha,
            convergence_tolerance_keur=outer_tolerance_keur,
            maximum_iterations=outer_max_iterations,
        )

        # Check outer convergence across all material state components (Section 12).
        d_idc = abs(new_financing.senior_idc_keur - prev_idc)
        d_fee = abs(new_financing.senior_commitment_fee_keur - prev_fee)
        d_struct = abs(new_financing.structuring_fee_keur - prev_struct)
        d_senior = abs(inner_result.final_senior_commitment_keur - prev_senior)
        d_shl = abs(inner_result.derived_shl_cash_principal_keur - prev_shl)
        d_pik = abs(inner_result.shl_construction_pik_keur - prev_pik)
        d_uses = abs(inner_result.project_uses.total_project_uses_keur - prev_uses)
        outer_residual = max(d_idc, d_fee, d_struct, d_senior, d_shl, d_pik, d_uses)
        prev_idc = new_financing.senior_idc_keur
        prev_fee = new_financing.senior_commitment_fee_keur
        prev_struct = new_financing.structuring_fee_keur
        prev_senior = inner_result.final_senior_commitment_keur
        prev_shl = inner_result.derived_shl_cash_principal_keur
        prev_pik = inner_result.shl_construction_pik_keur
        prev_uses = inner_result.project_uses.total_project_uses_keur

        if outer_residual <= outer_tolerance_keur:
            break
    else:
        raise RuntimeError(
            f"PR9_OUTER_G2A_CONSTRUCTION_FIXED_POINT_DID_NOT_CONVERGE: "
            f"outer_residual={outer_residual:.12f} kEUR after {outer_max_iterations} iterations"
        )

    assert inner_result is not None and stage_b2_result is not None

    # Final idempotence verification: one full outer transition from converged state must
    # produce identical outputs (Section 14 — true outer transition idempotence).
    _verify_b2_cfg = build_construction_runtime_config(
        construction=cf,
        senior_commitment_keur=inner_result.final_senior_commitment_keur,
        equity_available_keur=inner_result.share_capital_keur,
        shl_available_keur=inner_result.derived_shl_cash_principal_keur,
        capex_amounts_keur=capex_amounts,
        share_premium_keur=inner_result.share_premium_keur,
        other_committed_equity_keur=inner_result.other_equity_funding_before_shl_keur,
        additional_equity_keur=inner_result.additional_equity_keur,
        junior_keur=inner_result.junior_or_other_main_project_funding_keur,
    )
    _verify_b2 = run_stage_b2(_verify_b2_cfg)
    _verify_capex = apply_capitalized_financing_costs(orig_capex, _verify_b2.capitalized_financing_costs)
    _verify_inputs = replace(project_inputs, capex=_verify_capex)
    _verify_fin = replace(_verify_inputs.financing, construction_financing=None)
    _verify_inputs = replace(_verify_inputs, financing=_verify_fin)
    _verify_result = run_project_financing_model(
        _verify_inputs,
        source_id=source_id,
        baseline_commit_sha=baseline_commit_sha,
        convergence_tolerance_keur=outer_tolerance_keur,
        maximum_iterations=outer_max_iterations,
    )
    _idempotence_residual = max(
        abs(_verify_result.final_senior_commitment_keur - inner_result.final_senior_commitment_keur),
        abs(_verify_result.derived_shl_cash_principal_keur - inner_result.derived_shl_cash_principal_keur),
        abs(_verify_result.project_uses.total_project_uses_keur - inner_result.project_uses.total_project_uses_keur),
        abs(_verify_b2.capitalized_financing_costs.senior_idc_keur - stage_b2_result.capitalized_financing_costs.senior_idc_keur),
        abs(_verify_b2.capitalized_financing_costs.senior_commitment_fee_keur - stage_b2_result.capitalized_financing_costs.senior_commitment_fee_keur),
        abs(_verify_b2.capitalized_financing_costs.structuring_fee_keur - stage_b2_result.capitalized_financing_costs.structuring_fee_keur),
    )
    if _idempotence_residual > outer_tolerance_keur * 10:
        raise RuntimeError(
            f"PR9_OUTER_G2A_IDEMPOTENCE_FAILED: residual={_idempotence_residual:.12f} kEUR"
        )

    # Build typed ConstructionFinancingResult from final converged state.
    b2 = stage_b2_result
    b2_idc = b2.senior_idc_accrual_keur
    b2_fee = b2.senior_commitment_fee_accrual_keur
    b2_draws = b2.senior_period_draw_keur
    b2_cumul = b2.cumulative_senior_draw_keur
    b2_uses = b2.total_permanent_uses_keur
    b2_hard = b2.monthly_hard_capex_keur
    n = len(b2_draws)

    # Fix 3: SHL allocation via canonical allocator (not uses-minus-senior, which includes equity).
    from finco_core.construction.allocator import allocate_construction_sources_per_period
    derived_shl = inner_result.derived_shl_cash_principal_keur
    if n > 0 and b2_uses:
        _canonical_alloc = allocate_construction_sources_per_period(
            period_uses=b2_uses,
            share_capital_keur=inner_result.share_capital_keur,
            share_premium_keur=inner_result.share_premium_keur,
            other_committed_equity_keur=inner_result.other_equity_funding_before_shl_keur,
            additional_equity_keur=inner_result.additional_equity_keur,
            shl_cash_keur=derived_shl,
            junior_keur=inner_result.junior_or_other_main_project_funding_keur,
            senior_commitment_keur=inner_result.final_senior_commitment_keur,
        )
        shl_alloc = tuple(a.shl_draw_keur for a in _canonical_alloc)
        _share_capital_draws = tuple(a.share_capital_draw_keur for a in _canonical_alloc)
        _share_premium_draws = tuple(a.share_premium_draw_keur for a in _canonical_alloc)
        _other_committed_draws = tuple(a.other_committed_equity_draw_keur for a in _canonical_alloc)
        _additional_equity_draws = tuple(a.additional_equity_draw_keur for a in _canonical_alloc)
        _junior_draws = tuple(a.junior_draw_keur for a in _canonical_alloc)
        _period_residuals = tuple(a.residual_keur for a in _canonical_alloc)
        _cumul_residuals = tuple(
            sum(_period_residuals[:i+1]) for i in range(len(_period_residuals))
        )
        _max_period_residual = max(abs(r) for r in _period_residuals) if _period_residuals else 0.0
        _max_cumul_residual = max(abs(c) for c in _cumul_residuals) if _cumul_residuals else 0.0
    else:
        shl_alloc = ()
        _share_capital_draws = ()
        _share_premium_draws = ()
        _other_committed_draws = ()
        _additional_equity_draws = ()
        _junior_draws = ()
        _period_residuals = ()
        _max_period_residual = 0.0
        _max_cumul_residual = 0.0

    # Build the canonical ConstructionFundingResult from the exact converged allocations.
    # This is the single Layer-A authority: the same canonical_alloc tuple is passed to
    # build_construction_funding_schedule so ConstructionFundingResult == ConstructionFinancingResult
    # for every source class (identity holds within 1e-9 kEUR).
    if n > 0 and b2_uses and _canonical_alloc:
        _pr9_period_dates: "tuple | None" = tuple(
            (p.start_date, p.end_date, None) for p in cf.periods[:n]
        )
        _pr9_construction_funding = build_construction_funding_schedule(
            construction_period_count=n,
            total_project_uses_keur=inner_result.project_uses.total_project_uses_keur,
            senior_keur=inner_result.final_senior_commitment_keur,
            junior_keur=inner_result.junior_or_other_main_project_funding_keur,
            share_capital_keur=inner_result.share_capital_keur,
            share_premium_keur=inner_result.share_premium_keur,
            other_committed_equity_keur=inner_result.other_equity_funding_before_shl_keur,
            additional_equity_keur=inner_result.additional_equity_keur,
            shl_cash_keur=derived_shl,
            period_dates=_pr9_period_dates,
            canonical_economic_allocations=_canonical_alloc,
        )
    else:
        _pr9_construction_funding = inner_result.construction_funding

    # Period dates from construction financing spec
    period_starts = tuple(p.start_date for p in cf.periods[:n])
    period_ends = tuple(p.end_date for p in cf.periods[:n])

    # Structuring fee per period
    from finco_core.construction.stage_b2 import allocate_structuring_fee
    struct_per_period = allocate_structuring_fee(
        b2.config.funding_policy,
        b2.capitalized_financing_costs.structuring_fee_keur,
    )

    final_uses = inner_result.project_uses.total_project_uses_keur
    final_senior = inner_result.final_senior_commitment_keur
    sources_uses_diff = sum(_pr9_construction_funding.periods[i].sources_uses_difference_keur
                            for i in range(len(_pr9_construction_funding.periods))) if _pr9_construction_funding.periods else 0.0

    construction_result = ConstructionFinancingResult(
        period_start_dates=period_starts,
        period_end_dates=period_ends,
        hard_capex_uses_keur=b2_hard,
        total_period_uses_keur=b2_uses,
        senior_draws_keur=b2_draws,
        cumulative_senior_keur=b2_cumul,
        senior_idc_accrual_keur=b2_idc,
        senior_commitment_fee_accrual_keur=b2_fee,
        structuring_fee_keur=struct_per_period,
        shl_allocation_keur=shl_alloc,
        shl_cash_contribution_keur=shl_alloc,  # PRO_RATA: allocation == contribution
        share_capital_draws_keur=_share_capital_draws,
        share_premium_draws_keur=_share_premium_draws,
        other_committed_equity_draws_keur=_other_committed_draws,
        additional_equity_draws_keur=_additional_equity_draws,
        junior_draws_keur=_junior_draws,
        period_sources_uses_residual_keur=_period_residuals,
        maximum_period_residual_keur=_max_period_residual,
        maximum_cumulative_residual_keur=_max_cumul_residual,
        total_capitalized_financing_keur=b2.capitalized_financing_costs.total_keur,
        shl_construction_pik_keur=inner_result.shl_construction_pik_keur,
        opening_operating_shl_keur=inner_result.opening_operating_shl_balance_keur,
        final_total_project_uses_keur=final_uses,
        final_senior_commitment_keur=final_senior,
        sources_uses_residual_keur=sources_uses_diff,
        outer_iterations=outer_iteration,
        outer_residual_keur=outer_residual,
        stage_b2_iterations=b2.iterations,
        stage_b2_residual_keur=b2.final_residual_keur,
        outer_idc_residual_keur=d_idc,
        outer_fee_residual_keur=d_fee,
        outer_struct_residual_keur=d_struct,
        outer_senior_residual_keur=d_senior,
        outer_shl_residual_keur=d_shl,
        outer_pik_residual_keur=d_pik,
        outer_uses_residual_keur=d_uses,
        final_verification_outer_residual_keur=_idempotence_residual,
    )

    return ProjectFinancingResult(
        project_model_result=inner_result.project_model_result,
        project_uses=inner_result.project_uses,
        dscr_debt_capacity_keur=inner_result.dscr_debt_capacity_keur,
        gearing_basis_keur=inner_result.gearing_basis_keur,
        gearing_ratio=inner_result.gearing_ratio,
        gearing_debt_capacity_keur=inner_result.gearing_debt_capacity_keur,
        final_senior_commitment_keur=inner_result.final_senior_commitment_keur,
        binding_senior_constraint=inner_result.binding_senior_constraint,
        junior_or_other_main_project_funding_keur=inner_result.junior_or_other_main_project_funding_keur,
        share_capital_keur=inner_result.share_capital_keur,
        share_premium_keur=inner_result.share_premium_keur,
        other_equity_funding_before_shl_keur=inner_result.other_equity_funding_before_shl_keur,
        additional_equity_keur=inner_result.additional_equity_keur,
        derived_shl_cash_principal_keur=inner_result.derived_shl_cash_principal_keur,
        shl_construction_pik_keur=inner_result.shl_construction_pik_keur,
        opening_operating_shl_balance_keur=inner_result.opening_operating_shl_balance_keur,
        construction_funding=_pr9_construction_funding,
        fixed_point_iteration_count=inner_result.fixed_point_iteration_count,
        fixed_point_maximum_difference_keur=inner_result.fixed_point_maximum_difference_keur,
        construction_financing=construction_result,
    )


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

    # PR-9 construction IDC outer fixed point — gated; disabled path is structurally frozen.
    # When construction_financing is None or enabled=False this block is never entered.
    _construction_result: ConstructionFinancingResult | None = None
    if fin.construction_financing is not None and fin.construction_financing.enabled:
        result = _run_with_construction_idc(
            project_inputs=project_inputs,
            source_id=source_id,
            baseline_commit_sha=baseline_commit_sha,
            outer_tolerance_keur=convergence_tolerance_keur,
            outer_max_iterations=maximum_iterations,
        )
        return result

    uses = _project_uses(project_inputs)
    gearing_capacity = uses.total_project_uses_keur * fin.gearing_ratio

    # Fix 3: pre-compute construction period template for timing-resolved SHL.
    # Run the operating model once (calendar-only, timing-policy-independent) to get
    # per-period DCFs for construction periods. Used inside the fixed-point loop to
    # compute timing-resolved opening SHL for each candidate_shl.
    _construction_period_template: tuple[ShlConstructionPeriodInput, ...] | None = None
    # BLOCKER C: canonical period dates from model periods, populated below when template built.
    _model_period_dates: "tuple[tuple, ...] | None" = None  # (period_start, period_end, cashflow_date)
    if (
        fin.shl_construction_day_count_fraction is not None
        and fin.shl_construction_day_count_fraction > 0.0
    ):
        _operating_for_periods = from_project_inputs(
            project_inputs, source_id=source_id, baseline_commit_sha=baseline_commit_sha
        )
        _op_periods = run_operating_model(_operating_for_periods).periods
        _construction_periods_raw = [p for p in _op_periods if p.is_construction]
        if _construction_periods_raw:
            _total_period_dcf = sum(p.day_fraction for p in _construction_periods_raw)
            _total_shl_dcf = fin.shl_construction_day_count_fraction
            # Scale per-period DCFs so they sum to total_shl_construction_dcf.
            _scale = _total_shl_dcf / _total_period_dcf if _total_period_dcf > 0.0 else 1.0
            _construction_period_template = tuple(
                ShlConstructionPeriodInput(
                    draw_keur=0.0,  # draw computed by build_shl_construction_draw_schedule
                    day_count_fraction=p.day_fraction * _scale,
                    period_index=i,
                )
                for i, p in enumerate(_construction_periods_raw)
            )
            # BLOCKER C: capture canonical dates from model periods.
            # cashflow_date = period_end (standard project-finance convention).
            _model_period_dates = tuple(
                (p.period_start, p.period_end, p.period_end)
                for p in _construction_periods_raw
            )
            # GAP 3: fail closed for multi-period PRO_RATA without explicit Uses vector.
            # PRO_RATA with DCF>0 and >1 construction period REQUIRES construction_period_uses_keur.
            # Single-period exception: timing is unambiguous (no split needed).
            # Legacy Solar/Wind paths with None/0.0 DCF are unaffected (gate above prevents reaching here).
            _n_template_periods = len(_construction_period_template)
            if (
                fin.sponsor_funding_timing_policy == SponsorFundingTimingPolicy.PRO_RATA_CONSTRUCTION
                and _n_template_periods > 1
                and not fin.construction_period_uses_keur
            ):
                raise ValueError(
                    "PRO_RATA_CONSTRUCTION with multi-period construction requires "
                    "explicit construction_period_uses_keur"
                )

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
        # Fix 3: compute timing-resolved construction draw schedule for this candidate_shl.
        # Uses the pre-computed per-period construction DCFs (_construction_period_template).
        # PRO_RATA vs ALL_AT_FC produce different draws per period → different PIK → different
        # opening SHL → different operating interest → different CFADS → different DSCR capacity.
        # Fix 3 canonical (BLOCKER B): pass construction_periods_override to SHL model so that
        # model construction PIK == ProjectFinancingResult.shl_construction_pik_keur.
        _iter_draw_schedule: "tuple[ShlConstructionPeriodInput, ...] | None" = None
        if (
            _construction_period_template is not None
            and candidate_shl > 0.0
        ):
            _timing_policy = fin.sponsor_funding_timing_policy
            # BLOCKER A: use actual construction Uses for PRO_RATA when provided.
            _uses = getattr(fin, "construction_period_uses_keur", ())
            if _uses:
                from finco_core.inputs._models import SponsorFundingTimingPolicy as _Policy
                # Layer A — cumulative SPONSOR_FIRST_RESIDUAL_SENIOR waterfall.
                # Equity cap = all fixed equity sources + additional_equity from previous iteration
                # (additional_equity starts at 0.0 and converges each iteration).
                # Senior cap set to total_project_uses to guarantee waterfall coverage;
                # the waterfall fills senior last so per-period SHL draws are unaffected by
                # how much senior is allocated.
                _equity_cap = (
                    fin.share_capital_keur
                    + fin.share_premium_keur
                    + fin.other_equity_funding_before_shl_keur
                    + additional_equity
                )
                _waterfall_caps = FundingSourceCaps(
                    equity_shares_keur=_equity_cap,
                    shl_keur=candidate_shl,
                    junior_keur=fin.junior_or_other_project_funding_keur,
                    senior_debt_keur=uses.total_project_uses_keur,  # generous cap; senior is residual
                )
                _waterfall_entries = allocate_source_waterfall(tuple(_uses), _waterfall_caps)
                _waterfall_shl_per_period = tuple(e.shl_draw_keur for e in _waterfall_entries)

                # Layer B — SHL cash timing policy (orthogonal to Layer A allocation).
                if _timing_policy == _Policy.PRO_RATA_CONSTRUCTION:
                    _shl_cash_per_period = _waterfall_shl_per_period
                else:  # ALL_AT_FC
                    _shl_cash_per_period = tuple(
                        candidate_shl if i == 0 else 0.0 for i in range(len(_uses))
                    )
                _iter_draw_schedule = tuple(
                    ShlConstructionPeriodInput(
                        draw_keur=d,
                        day_count_fraction=p.day_count_fraction,
                        period_index=p.period_index,
                    )
                    for d, p in zip(_shl_cash_per_period, _construction_period_template)
                )
            else:
                _iter_draw_schedule = build_shl_construction_draw_schedule(
                    shl_cash_principal_keur=candidate_shl,
                    construction_periods=_construction_period_template,
                    policy=_timing_policy,
                )

        capacity_model_input = build_senior_debt_model_input_from_project_inputs(
            capacity_inputs,
            source_id=source_id,
            baseline_commit_sha=baseline_commit_sha,
        )
        # Fix 3 canonical: inject construction_periods_override into capacity model input.
        # This causes the SHL model to compute canonical per-period construction PIK,
        # eliminating the dual truth (model PIK=0 vs result PIK>0).
        if _iter_draw_schedule is not None and capacity_model_input.shareholder_loan is not None:
            capacity_model_input = replace(
                capacity_model_input,
                shareholder_loan=replace(
                    capacity_model_input.shareholder_loan,
                    construction_periods_override=_iter_draw_schedule,
                ),
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
        # Fix 3 canonical: inject construction_periods_override into funded model input.
        if _iter_draw_schedule is not None and funded_model_input.shareholder_loan is not None:
            funded_model_input = replace(
                funded_model_input,
                shareholder_loan=replace(
                    funded_model_input.shareholder_loan,
                    construction_periods_override=_iter_draw_schedule,
                ),
            )
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
    # Fix 3 canonical (BLOCKER B): PIK now comes from canonical model result because the model
    # received construction_periods_override. Direct reading from model result is authoritative.
    shl_pik = 0.0
    opening_operating_shl = 0.0
    _final_draw_schedule: "tuple[ShlConstructionPeriodInput, ...] | None" = None
    # GAP 1 & 2: initialized here; populated inside the explicit-DCF block below.
    _post_uses_vector: "tuple[float, ...] | None" = None
    _post_waterfall_shl: "tuple[float, ...] | None" = None

    if _construction_period_template is not None:
        # Explicit positive DCF: compute final post-convergence draw schedule.
        timing_policy = fin.sponsor_funding_timing_policy
        _uses = getattr(fin, "construction_period_uses_keur", ())
        if _uses:
            from finco_core.inputs._models import SponsorFundingTimingPolicy as _Policy
            # Post-convergence: Layer A waterfall with authoritative final values.
            _final_equity_cap = (
                fin.share_capital_keur
                + fin.share_premium_keur
                + fin.other_equity_funding_before_shl_keur
                + additional_equity
            )
            _final_caps = FundingSourceCaps(
                equity_shares_keur=_final_equity_cap,
                shl_keur=derived_shl,
                junior_keur=fin.junior_or_other_project_funding_keur,
                senior_debt_keur=uses.total_project_uses_keur,
            )
            _final_waterfall = allocate_source_waterfall(tuple(_uses), _final_caps)
            _final_waterfall_shl = tuple(e.shl_draw_keur for e in _final_waterfall)
            # GAP 1 & 2: capture for funding schedule bridge computation below.
            _post_uses_vector = tuple(_uses)
            _post_waterfall_shl = _final_waterfall_shl
            if timing_policy == _Policy.PRO_RATA_CONSTRUCTION:
                _final_shl_cash = _final_waterfall_shl
            else:  # ALL_AT_FC
                _final_shl_cash = tuple(
                    derived_shl if i == 0 else 0.0 for i in range(len(_uses))
                )
            _final_draw_schedule = tuple(
                ShlConstructionPeriodInput(
                    draw_keur=d,
                    day_count_fraction=p.day_count_fraction,
                    period_index=p.period_index,
                )
                for d, p in zip(_final_shl_cash, _construction_period_template)
            )
        else:
            _final_draw_schedule = build_shl_construction_draw_schedule(
                shl_cash_principal_keur=derived_shl,
                construction_periods=_construction_period_template,
                policy=timing_policy,
            )
        construction_shl_schedule = compute_shl_construction_schedule(
            opening_balance_keur=0.0,
            periods=_final_draw_schedule,
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

    # BLOCKER C resolved: use model construction periods (same axis as SHL/tax) as the single
    # source of truth for G2A/G2B. _final_draw_schedule is indexed by model periods.
    # BLOCKER B resolved: if explicit timing is provided, always use it (no len() fallback).
    _model_construction_period_count = len(_construction_period_template) if _construction_period_template is not None else project_inputs.info.construction_months
    _shl_draws_per_period: tuple[float, ...] | None = None
    if _final_draw_schedule is not None:
        if len(_final_draw_schedule) != _model_construction_period_count:
            raise ValueError(
                f"G2B_PERIOD_COUNT_MISMATCH: draw schedule length {len(_final_draw_schedule)} "
                f"!= model construction period count {_model_construction_period_count}"
            )
        _shl_draws_per_period = tuple(p.draw_keur for p in _final_draw_schedule)
    # GAP 1: pass explicit period Uses vector to funding schedule (single source of truth).
    # GAP 2: pass waterfall allocation vector for prefunding bridge computation.
    # Both are None in the legacy path (no explicit uses vector provided).
    funding = build_construction_funding_schedule(
        construction_period_count=_model_construction_period_count,
        total_project_uses_keur=uses.total_project_uses_keur,
        senior_keur=model_result.senior_debt.debt_size_keur,
        junior_keur=fin.junior_or_other_project_funding_keur,
        share_capital_keur=fin.share_capital_keur,
        share_premium_keur=fin.share_premium_keur,
        other_committed_equity_keur=fin.other_equity_funding_before_shl_keur,
        additional_equity_keur=additional_equity,
        shl_cash_keur=derived_shl,
        shl_cash_per_period_keur=_shl_draws_per_period,
        # BLOCKER C: pass canonical period dates when available from model periods.
        period_dates=_model_period_dates,
        # GAP 1: explicit per-period Uses vector (overrides linear total/n).
        period_uses_keur=_post_uses_vector,
        # GAP 2: waterfall SHL allocation-to-Uses (Layer A), distinct from cash contribution (Layer B).
        shl_allocation_per_period_keur=_post_waterfall_shl,
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
