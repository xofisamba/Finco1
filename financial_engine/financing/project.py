"""Project-owned G2A financing fixed point over existing clean kernels."""

from __future__ import annotations

from dataclasses import replace

from finco_core.inputs import GearingBasisMode, ProjectInputs, SponsorFundingMode
from financial_engine.adapters.project_inputs import (
    build_senior_debt_model_input_from_project_inputs,
)
from domain.construction.config import FundingSourceCaps
from domain.construction.funding_allocation import allocate_source_waterfall
from financial_engine.financing.contracts import ProjectFinancingResult, ProjectUses
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
