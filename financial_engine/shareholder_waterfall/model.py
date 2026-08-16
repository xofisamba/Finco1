"""MVP G2C — Covenant-Gated Shareholder Waterfall model.

Extends G2B with a DSCR distribution lockup gate sourced from
extracted fixture Inputs!D223 (senior_lockup_dscr = 1.10).

Source-proven waterfall ordering:
  1. signed_post_senior = R84 (pre-gate junior FCF from clean engine)
  2. DSCR covenant gate applied → fcf_for_distribution = R109
       if gate LOCKED: fcf_for_distribution = 0, covenant_locked = R84
       if gate OPEN:   fcf_for_distribution = R84, covenant_locked = 0
  3. SHL cash service drawn from fcf_for_distribution (R112 = R109)
       via project-owned compute_shareholder_loan_schedules() — respects
       project-owned repayment mode, day-count, eligibility start, maturity.
  4. legal_equity_distribution = max(0, fcf_for_distribution - SHL_service) = R116

SHL POLICY AUTHORITY:
  G2C does NOT hardcode a repayment mode or day-count convention.
  These come from project-owned FinancingParams (clean_shl_repayment_method,
  shl_day_count_convention, shl_principal_eligibility_start_period,
  shl_maturity_period_index). The production SHL scheduler
  (compute_shareholder_loan_schedules) is the only SHL computation kernel.

DEDUCTIBLE SHL COVENANT FEEDBACK:
  If SHL interest is tax-deductible and the gate locks in any period,
  the resulting PIK accumulation would increase future SHL gross interest,
  affecting taxable income → CFADS → DSCR → gate — a feedback loop not
  yet closed in G2C. For such cases the status
  G2C_DEDUCTIBLE_SHL_COVENANT_FEEDBACK_NOT_YET_CLOSED is set.

G2C_DISTRIBUTION_ACCOUNT_AUTHORITY_INCOMPLETE: R98 (distribution account
balance / carryforward) is NOT in the extracted source fixture. Locked cash
is tracked per-period but NOT accumulated into a releasing balance.

Source map:
  R84  → signed_post_senior (pre-DSRA, pre-gate)
  R109 → fcf_for_distribution (gate output)
  R112 → SHL service input (= R109 per source formula CF112=H109)
  R116 → legal_equity_distribution_keur
"""
from __future__ import annotations

import dataclasses
from datetime import date

from finco_core.inputs import DebtServiceReserveSupportMode, ProjectInputs, SponsorFundingMode
from finco_core.inputs._models import ShlInterestDeductibilityMode

from financial_engine.adapters.project_inputs import (
    _build_shareholder_loan_model_input_from_project_inputs,
)
from financial_engine.financing.contracts import (
    ConstructionFundingPeriod,
    ProjectFinancingResult,
)
from financial_engine.financing.project import run_project_financing_model
from financial_engine.financing.dsrf import compute_dsrf_fee_schedule
from financial_engine.results import ProjectModelResult
from financial_engine.shl.production import compute_shareholder_loan_schedules
from financial_engine.shareholder_waterfall.contracts import (
    CovenantGatedWaterfallPeriod,
    CovenantGatedWaterfallResult,
    DistributionGateStatus,
)
from financial_engine.sponsor_returns.model import compute_gated_sponsor_return_metrics

_G2C_DA_STATUS = "G2C_DISTRIBUTION_ACCOUNT_AUTHORITY_INCOMPLETE"
_G2C_DEDUCTIBLE_FEEDBACK_STATUS = "G2C_DEDUCTIBLE_SHL_COVENANT_FEEDBACK_NOT_YET_CLOSED"
_DSRF_NO_DRAW_STATUS = "DSRF_AVAILABLE_SUPPORT_ONLY_NO_DRAW_ENGINE"


def _evaluate_distribution_gate(
    base_dscr: float | None,
    distribution_lockup_dscr: float,
    has_senior_ds: bool,
) -> DistributionGateStatus:
    """Evaluate the DSCR covenant distribution gate.

    Source: extracted fixture Inputs!D223 → generic distribution_lockup_dscr.
    Gate: if base_dscr < distribution_lockup_dscr → locked.
    Periods with no Senior DS have no DSCR → gate open (no debt to covenant).
    """
    if base_dscr is None or not has_senior_ds:
        return DistributionGateStatus.DSCR_UNAVAILABLE_GATE_OPEN
    if base_dscr < distribution_lockup_dscr:
        return DistributionGateStatus.LOCKED_DSCR_BELOW_LOCKUP
    return DistributionGateStatus.OPEN


def _add_months(d: date, months: int) -> date:
    import calendar
    month = d.month + months
    year = d.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _construction_period_date(financial_close: date, period_index: int) -> date:
    return _add_months(financial_close, period_index - 1)


def run_project_shareholder_waterfall_model(
    project_inputs: ProjectInputs,
    *,
    source_id: str = "",
    baseline_commit_sha: str = "",
) -> CovenantGatedWaterfallResult:
    """Compute G2C covenant-gated shareholder waterfall from G2A financing results.

    Adds DSCR distribution lockup gate (project_inputs.financing.lockup_dscr) on top
    of the G2B SHL-gated distribution mechanics.

    Source-proven ordering: gate is UPSTREAM of SHL service. The gate filters
    signed_post_senior into fcf_for_distribution; SHL receipts and equity
    distributions are drawn from fcf_for_distribution, not from raw post-Senior cash.

    Source authority: extracted fixture Inputs!D223 → lockup_dscr = 1.10 (generic parameter).

    SHL policy: project-owned (clean_shl_repayment_method, shl_day_count_convention,
    shl_principal_eligibility_start_period, shl_maturity_period_index). No G2C override.

    Sponsor Returns: return metrics delegated to compute_gated_sponsor_return_metrics().
    G2C does not compute XIRR/MOIC directly.
    """
    financing: ProjectFinancingResult = run_project_financing_model(
        project_inputs,
        source_id=source_id,
        baseline_commit_sha=baseline_commit_sha,
    )

    model_result: ProjectModelResult = financing.project_model_result  # type: ignore[assignment]
    fin = project_inputs.financing
    info = project_inputs.info
    tax = project_inputs.tax

    distribution_lockup_dscr: float = fin.lockup_dscr
    financial_close: date = info.financial_close

    # ── Build lookup maps ─────────────────────────────────────────────────────
    construction_periods_by_index: dict[int, ConstructionFundingPeriod] = {
        p.period_index: p for p in financing.construction_funding.periods
    }

    if model_result.post_senior_cash is None:
        raise ValueError("G2C requires post_senior_cash; clean engine did not produce it")

    signed_post_senior_by_idx: dict[int, float] = dict(
        zip(
            model_result.post_senior_cash.period_indices,
            model_result.post_senior_cash.cash_after_senior_before_reserves_keur,
        )
    )

    # DSCR lookup — None where no Senior DS
    base_dscr_by_idx: dict[int, float | None] = {}
    senior_ds_nonzero_by_idx: dict[int, bool] = {}
    senior_last_period_index: int | None = None
    if model_result.senior_debt is not None:
        sd = model_result.senior_debt
        ds_arr = sd.senior_debt_service_keur
        for idx, dscr, ds in zip(sd.period_indices, sd.base_dscr, ds_arr):
            base_dscr_by_idx[idx] = dscr
            senior_ds_nonzero_by_idx[idx] = ds > 0.0
        nonzero_ds = [i for i, ds in zip(sd.period_indices, ds_arr) if ds > 0.0]
        if nonzero_ds:
            senior_last_period_index = max(nonzero_ds)

    period_date_by_idx: dict[int, date] = {
        p.period_index: p.period_end for p in model_result.periods
    }
    period_start_by_idx: dict[int, date] = {
        p.period_index: p.period_start for p in model_result.periods
    }

    # ── DSRF commitment fee schedule ──────────────────────────────────────────
    dsra_mode = fin.dsra_support_mode
    dsrf_fee_by_idx: dict[int, float] = {}
    if dsra_mode == DebtServiceReserveSupportMode.DSRF:
        dsrf_req = getattr(fin, "debt_service_reserve_requirement_keur", 0.0) or 0.0
        if dsrf_req > 0.0 and fin.dsrf_commitment_keur < dsrf_req:
            raise ValueError(
                f"G2C_DSRF_COMMITMENT_BELOW_REQUIRED_RESERVE: "
                f"commitment={fin.dsrf_commitment_keur} < required={dsrf_req}"
            )
        if fin.dsrf_commitment_keur > 0 and fin.dsrf_commitment_fee_rate_pa > 0.0:
            op_indices = [p.period_index for p in model_result.periods if p.is_operation]
            op_starts = [period_start_by_idx[i] for i in op_indices]
            op_ends = [period_date_by_idx[i] for i in op_indices]
            dsrf_schedule = compute_dsrf_fee_schedule(
                op_indices, op_starts, op_ends,
                fin.dsrf_commitment_keur,
                fin.dsrf_commitment_fee_rate_pa,
                senior_last_period_index=senior_last_period_index if fin.dsrf_fee_expires_at_senior_maturity else None,
                day_count_convention=fin.dsrf_day_count,
            )
            dsrf_fee_by_idx = dict(zip(dsrf_schedule.period_indices, dsrf_schedule.dsrf_commitment_fee_keur))

    # ── Phase 1: Gate pass — compute fcf_for_distribution per operating period ─
    # Accumulate gated cash vector (indexed same as model_result.periods) for SHL.
    gate_info_by_idx: dict[int, tuple] = {}  # idx → (gate_status, fcf, locked, dsrf_fee, signed_ps, shortfall)
    gated_cash_all_periods: list[float] = []  # 0 for construction, fcf_for_dist for operating

    for period in model_result.periods:
        idx = period.period_index
        if period.is_construction:
            gated_cash_all_periods.append(0.0)
            continue

        if idx not in signed_post_senior_by_idx:
            raise ValueError(
                f"G2C: operating period {idx} absent from post_senior_cash schedule"
            )
        signed_post_senior = signed_post_senior_by_idx[idx]
        dsrf_fee = dsrf_fee_by_idx.get(idx, 0.0)
        post_senior_after_dsrf = signed_post_senior - dsrf_fee

        dscr_val = base_dscr_by_idx.get(idx)
        has_senior_ds = senior_ds_nonzero_by_idx.get(idx, False)
        gate_status = _evaluate_distribution_gate(dscr_val, distribution_lockup_dscr, has_senior_ds)
        gate_locked = gate_status == DistributionGateStatus.LOCKED_DSCR_BELOW_LOCKUP

        pre_gate = max(0.0, post_senior_after_dsrf)
        if gate_locked:
            fcf_for_distribution = 0.0
            covenant_locked = pre_gate
        else:
            fcf_for_distribution = pre_gate
            covenant_locked = 0.0

        cash_shortfall = max(0.0, -post_senior_after_dsrf)
        gate_info_by_idx[idx] = (gate_status, fcf_for_distribution, covenant_locked, dsrf_fee, signed_post_senior, cash_shortfall)
        gated_cash_all_periods.append(fcf_for_distribution)

    # ── Phase 2: SHL schedule using project-owned policy ─────────────────────
    # Passes gated FCF vector to the canonical production SHL scheduler.
    # Respects: repayment mode, day-count, eligibility start, maturity.
    # No G2C override of any SHL policy parameter.
    shl_opening_by_idx: dict[int, float] = {}
    shl_gross_by_idx: dict[int, float] = {}
    shl_cash_int_by_idx: dict[int, float] = {}
    shl_pik_by_idx: dict[int, float] = {}
    shl_principal_by_idx: dict[int, float] = {}
    shl_closing_by_idx: dict[int, float] = {}

    has_shl = financing.derived_shl_cash_principal_keur > 0.0
    if has_shl:
        shl_model_input = _build_shareholder_loan_model_input_from_project_inputs(
            project_inputs,
            model_result.periods,
            senior_debt_maturity_period_index=senior_last_period_index,
        )
        if shl_model_input is not None:
            # Use G2A's derived (sized) principal — may differ from clean_shl_principal_keur
            # if the fixed-point converged to a different value.
            if abs(shl_model_input.initial_principal_keur - financing.derived_shl_cash_principal_keur) > 1e-4:
                shl_model_input = dataclasses.replace(
                    shl_model_input,
                    initial_principal_keur=financing.derived_shl_cash_principal_keur,
                )

            gated_shl_schedule = compute_shareholder_loan_schedules(
                model_result.periods,
                shl_model_input,
                gated_cash_all_periods,
                diagnostics=None,
            )
            shl_opening_by_idx = dict(zip(gated_shl_schedule.period_indices, gated_shl_schedule.shl_opening_keur))
            shl_gross_by_idx = dict(zip(gated_shl_schedule.period_indices, gated_shl_schedule.shl_gross_interest_keur))
            shl_cash_int_by_idx = dict(zip(gated_shl_schedule.period_indices, gated_shl_schedule.shl_cash_interest_keur))
            shl_pik_by_idx = dict(zip(gated_shl_schedule.period_indices, gated_shl_schedule.shl_pik_interest_keur))
            shl_principal_by_idx = dict(zip(gated_shl_schedule.period_indices, gated_shl_schedule.shl_principal_keur))
            shl_closing_by_idx = dict(zip(gated_shl_schedule.period_indices, gated_shl_schedule.shl_closing_keur))

    # ── Phase 3: Deductible SHL feedback check ───────────────────────────────
    # If SHL interest is tax-deductible AND the gate locks any period,
    # PIK accumulation changes future gross interest → DSCR feedback not yet closed.
    shl_deductible = (
        getattr(tax, "shl_interest_deductibility", ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE)
        != ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE
    )
    gate_locks_any = any(
        info[0] == DistributionGateStatus.LOCKED_DSCR_BELOW_LOCKUP
        for info in gate_info_by_idx.values()
    )
    shl_pik_differs_from_g2a = has_shl and gate_locks_any and any(
        shl_pik_by_idx.get(idx, 0.0) > 0.0 for idx in gate_info_by_idx
    )
    deductible_feedback_active = shl_deductible and shl_pik_differs_from_g2a

    # ── Phase 4: Assemble per-period records ──────────────────────────────────
    waterfall_periods: list[CovenantGatedWaterfallPeriod] = []

    # --- Construction periods ---
    for k in sorted(construction_periods_by_index.keys()):
        cp = construction_periods_by_index[k]
        cf_date = _construction_period_date(financial_close, k)

        share_cap = cp.share_capital_draw_keur
        share_prem = cp.share_premium_draw_keur
        other_committed = cp.other_committed_equity_draw_keur
        add_eq = cp.additional_equity_draw_keur
        shl_draw = cp.shl_cash_draw_keur

        pure_equity_net = -(share_cap + share_prem + other_committed + add_eq)
        total_sponsor_net = pure_equity_net - shl_draw

        waterfall_periods.append(CovenantGatedWaterfallPeriod(
            period_index=k,
            cashflow_date=cf_date,
            is_construction=True,
            base_dscr=None,
            distribution_lockup_dscr=distribution_lockup_dscr,
            distribution_gate_status=DistributionGateStatus.CONSTRUCTION,
            signed_post_senior_keur=0.0,
            dsrf_commitment_fee_keur=0.0,
            fcf_for_distribution_keur=0.0,
            covenant_locked_keur=0.0,
            shl_opening_balance_keur=0.0,
            shl_gross_interest_keur=0.0,
            shl_cash_interest_receipt_keur=0.0,
            shl_pik_keur=0.0,
            shl_principal_receipt_keur=0.0,
            shl_closing_balance_keur=0.0,
            legal_equity_distribution_keur=0.0,
            cash_shortfall_keur=0.0,
            share_capital_contribution_keur=share_cap,
            share_premium_contribution_keur=share_prem,
            other_committed_equity_contribution_keur=other_committed,
            additional_equity_contribution_keur=add_eq,
            shl_cash_contribution_keur=shl_draw,
            pure_equity_net_cashflow_keur=pure_equity_net,
            total_sponsor_net_cashflow_keur=total_sponsor_net,
        ))

    # --- Operating periods ---
    for period in model_result.periods:
        if not period.is_operation:
            continue
        idx = period.period_index
        cf_date = period_date_by_idx[idx]

        gate_status, fcf_for_distribution, covenant_locked, dsrf_fee, signed_post_senior, cash_shortfall = gate_info_by_idx[idx]

        # SHL values from project-owned gated schedule.
        # For BULLET mode at maturity, shl_principal_keur = full outstanding (contractual
        # balloon), which may exceed a single period's fcf_for_distribution. Cap actual
        # cash receipts at available cash so sponsor return accounting is correct.
        shl_opening = shl_opening_by_idx.get(idx, 0.0)
        shl_gross = shl_gross_by_idx.get(idx, 0.0)
        actual_shl_cash_int = shl_cash_int_by_idx.get(idx, 0.0)
        shl_pik = shl_pik_by_idx.get(idx, 0.0)
        contractual_shl_principal = shl_principal_by_idx.get(idx, 0.0)
        actual_shl_principal = min(
            contractual_shl_principal,
            max(0.0, fcf_for_distribution - actual_shl_cash_int),
        )
        shl_closing = shl_closing_by_idx.get(idx, 0.0)

        # Equity distribution = fcf_for_distribution residual (R116)
        shl_service_actual = actual_shl_cash_int + actual_shl_principal
        distribution = max(0.0, fcf_for_distribution - shl_service_actual)

        pure_equity_net = distribution
        total_sponsor_net = pure_equity_net + actual_shl_cash_int + actual_shl_principal

        waterfall_periods.append(CovenantGatedWaterfallPeriod(
            period_index=idx,
            cashflow_date=cf_date,
            is_construction=False,
            base_dscr=base_dscr_by_idx.get(idx),
            distribution_lockup_dscr=distribution_lockup_dscr,
            distribution_gate_status=gate_status,
            signed_post_senior_keur=signed_post_senior,
            dsrf_commitment_fee_keur=dsrf_fee,
            fcf_for_distribution_keur=fcf_for_distribution,
            covenant_locked_keur=covenant_locked,
            shl_opening_balance_keur=shl_opening,
            shl_gross_interest_keur=shl_gross,
            shl_cash_interest_receipt_keur=actual_shl_cash_int,
            shl_pik_keur=shl_pik,
            shl_principal_receipt_keur=actual_shl_principal,
            shl_closing_balance_keur=shl_closing,
            legal_equity_distribution_keur=distribution,
            cash_shortfall_keur=cash_shortfall,
            share_capital_contribution_keur=0.0,
            share_premium_contribution_keur=0.0,
            other_committed_equity_contribution_keur=0.0,
            additional_equity_contribution_keur=0.0,
            shl_cash_contribution_keur=0.0,
            pure_equity_net_cashflow_keur=pure_equity_net,
            total_sponsor_net_cashflow_keur=total_sponsor_net,
        ))

    # ── Aggregate totals ──────────────────────────────────────────────────────
    total_sc = sum(p.share_capital_contribution_keur for p in waterfall_periods)
    total_sp = sum(p.share_premium_contribution_keur for p in waterfall_periods)
    total_oce = sum(p.other_committed_equity_contribution_keur for p in waterfall_periods)
    total_ae = sum(p.additional_equity_contribution_keur for p in waterfall_periods)
    total_le = total_sc + total_sp + total_oce + total_ae
    total_shl_contrib = sum(p.shl_cash_contribution_keur for p in waterfall_periods)
    total_sponsor_contrib = total_le + total_shl_contrib

    total_shl_int_recd = sum(p.shl_cash_interest_receipt_keur for p in waterfall_periods)
    total_shl_prin_recd = sum(p.shl_principal_receipt_keur for p in waterfall_periods)
    total_distributions = sum(p.legal_equity_distribution_keur for p in waterfall_periods)
    total_covenant_locked = sum(p.covenant_locked_keur for p in waterfall_periods)
    total_sponsor_receipts = total_distributions + total_shl_int_recd + total_shl_prin_recd
    total_dsrf_fee = sum(p.dsrf_commitment_fee_keur for p in waterfall_periods)

    # Gate summary
    operating_with_ds = [
        p for p in waterfall_periods
        if not p.is_construction and p.distribution_gate_status != DistributionGateStatus.DSCR_UNAVAILABLE_GATE_OPEN
    ]
    periods_locked = sum(
        1 for p in waterfall_periods
        if p.distribution_gate_status == DistributionGateStatus.LOCKED_DSCR_BELOW_LOCKUP
    )
    periods_with_ds = len(operating_with_ds)

    # ── Return metrics — delegated to G2B authority ───────────────────────────
    # G2C does not compute XIRR/MOIC directly. Return metrics come from
    # compute_gated_sponsor_return_metrics() in financial_engine.sponsor_returns.
    pe_cfs = [p.pure_equity_net_cashflow_keur for p in waterfall_periods]
    pe_dates = [p.cashflow_date for p in waterfall_periods]
    ts_cfs = [p.total_sponsor_net_cashflow_keur for p in waterfall_periods]

    (
        pe_xirr, pe_xirr_status,
        pe_moic, pe_moic_status,
        ts_xirr, ts_xirr_status,
        ts_moic, ts_moic_status,
    ) = compute_gated_sponsor_return_metrics(
        cashflow_dates=pe_dates,
        pure_equity_cashflows=pe_cfs,
        total_sponsor_cashflows=ts_cfs,
        total_legal_equity_contributed_keur=total_le,
        total_sponsor_contributed_keur=total_sponsor_contrib,
    )

    return CovenantGatedWaterfallResult(
        financing_result=financing,
        distribution_lockup_dscr=distribution_lockup_dscr,
        waterfall_periods=tuple(waterfall_periods),
        total_share_capital_contributed_keur=total_sc,
        total_share_premium_contributed_keur=total_sp,
        total_other_committed_equity_contributed_keur=total_oce,
        total_additional_equity_contributed_keur=total_ae,
        total_legal_equity_contributed_keur=total_le,
        total_shl_cash_contributed_keur=total_shl_contrib,
        total_sponsor_contributed_keur=total_sponsor_contrib,
        total_shl_cash_interest_received_keur=total_shl_int_recd,
        total_shl_principal_received_keur=total_shl_prin_recd,
        total_legal_equity_distributions_keur=total_distributions,
        total_covenant_locked_keur=total_covenant_locked,
        total_sponsor_receipts_keur=total_sponsor_receipts,
        pure_equity_xirr=pe_xirr,
        pure_equity_xirr_status=pe_xirr_status,
        pure_equity_moic=pe_moic,
        pure_equity_moic_status=pe_moic_status,
        total_sponsor_xirr=ts_xirr,
        total_sponsor_xirr_status=ts_xirr_status,
        total_sponsor_moic=ts_moic,
        total_sponsor_moic_status=ts_moic_status,
        periods_locked_by_dscr=periods_locked,
        total_periods_with_senior_ds=periods_with_ds,
        total_dsrf_commitment_fee_keur=total_dsrf_fee,
        distribution_account_status=_G2C_DA_STATUS,
        deductible_shl_covenant_feedback_status=(
            _G2C_DEDUCTIBLE_FEEDBACK_STATUS if deductible_feedback_active else None
        ),
    )
