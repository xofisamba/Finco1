"""MVP G2C — Covenant-Gated Shareholder Waterfall model.

Extends G2B with a DSCR distribution lockup gate sourced from
extracted fixture Inputs!D223 (senior_lockup_dscr = 1.10).

Source-proven waterfall ordering:
  1. signed_post_senior = R84 (pre-gate junior FCF from clean engine)
  2. DSCR covenant gate applied → fcf_for_distribution = R109
       if gate LOCKED: fcf_for_distribution = 0, covenant_locked = R84
       if gate OPEN:   fcf_for_distribution = R84, covenant_locked = 0
  3. SHL cash service drawn from fcf_for_distribution (R112 = R109)
       actual_shl_int, actual_shl_prin = allocate(fcf_for_distribution, ...)
  4. legal_equity_distribution = max(0, fcf_for_distribution - SHL_service) = R116

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

from datetime import date

from finco_core.inputs import DebtServiceReserveSupportMode, ProjectInputs, SponsorFundingMode

from finco_core.sponsor.xirr import robust_xirr
from financial_engine.financing.contracts import (
    ConstructionFundingPeriod,
    ProjectFinancingResult,
)
from financial_engine.financing.project import run_project_financing_model
from financial_engine.results import ProjectModelResult
from financial_engine.sponsor_returns.contracts import ReturnMetricStatus
from financial_engine.financing.dsrf import compute_dsrf_fee_schedule
from financial_engine.shl.contracts import ShlRepaymentMode
from financial_engine.shl.waterfall import (
    compute_shl_dcf_actual_365_inclusive,
    compute_shl_waterfall_period,
)
from financial_engine.shareholder_waterfall.contracts import (
    CovenantGatedWaterfallPeriod,
    CovenantGatedWaterfallResult,
    DistributionGateStatus,
)

_G2C_DA_STATUS = "G2C_DISTRIBUTION_ACCOUNT_AUTHORITY_INCOMPLETE"


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


def _xirr_status(cash_flows: list[float], rate: float | None) -> ReturnMetricStatus:
    has_neg = any(cf < 0 for cf in cash_flows)
    has_pos = any(cf > 0 for cf in cash_flows)
    if not has_neg:
        return ReturnMetricStatus.NO_NEGATIVE_CASHFLOW
    if not has_pos:
        return ReturnMetricStatus.NO_POSITIVE_CASHFLOW
    if rate is None:
        return ReturnMetricStatus.NON_CONVERGENT
    return ReturnMetricStatus.OK


def _moic_status(
    total_contributions: float,
    moic: float | None,
) -> ReturnMetricStatus:
    if total_contributions <= 0.0:
        return ReturnMetricStatus.ZERO_CONTRIBUTION
    if moic is None:
        return ReturnMetricStatus.UNDEFINED
    return ReturnMetricStatus.OK


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
    """
    financing: ProjectFinancingResult = run_project_financing_model(
        project_inputs,
        source_id=source_id,
        baseline_commit_sha=baseline_commit_sha,
    )

    model_result: ProjectModelResult = financing.project_model_result  # type: ignore[assignment]
    fin = project_inputs.financing
    info = project_inputs.info

    distribution_lockup_dscr: float = fin.lockup_dscr
    financial_close: date = info.financial_close

    # ── Build lookup maps ─────────────────────────────────────────────────────
    construction_periods_by_index: dict[int, ConstructionFundingPeriod] = {
        p.period_index: p for p in financing.construction_funding.periods
    }

    shl = model_result.shareholder_loan


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
    if model_result.senior_debt is not None:
        sd = model_result.senior_debt
        ds_arr = sd.senior_debt_service_keur
        for idx, dscr, ds in zip(sd.period_indices, sd.base_dscr, ds_arr):
            base_dscr_by_idx[idx] = dscr
            senior_ds_nonzero_by_idx[idx] = ds > 0.0

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
        # Sufficiency check: commitment must cover required reserve
        if fin.dsrf_required_reserve_keur > 0.0 and fin.dsrf_commitment_keur < fin.dsrf_required_reserve_keur:
            raise ValueError(
                f"G2C_DSRF_COMMITMENT_BELOW_REQUIRED_RESERVE: "
                f"commitment={fin.dsrf_commitment_keur} < required={fin.dsrf_required_reserve_keur}"
            )
        if fin.dsrf_commitment_keur > 0 and fin.dsrf_commitment_fee_rate_pa > 0.0:
            op_indices = [p.period_index for p in model_result.periods if p.is_operation]
            op_starts = [period_start_by_idx[i] for i in op_indices]
            op_ends = [period_date_by_idx[i] for i in op_indices]
            # Fee expires at Senior debt maturity if configured
            senior_last_idx: int | None = None
            if fin.dsrf_fee_expires_at_senior_maturity and model_result.senior_debt is not None:
                sd = model_result.senior_debt
                # Last period with non-zero debt service = maturity period
                ds_by_idx = dict(zip(sd.period_indices, sd.senior_debt_service_keur))
                op_set = set(op_indices)
                nonzero_ds_op = [i for i in sd.period_indices if i in op_set and ds_by_idx[i] > 0.0]
                if nonzero_ds_op:
                    senior_last_idx = max(nonzero_ds_op)
            dsrf_schedule = compute_dsrf_fee_schedule(
                op_indices, op_starts, op_ends,
                fin.dsrf_commitment_keur,
                fin.dsrf_commitment_fee_rate_pa,
                senior_last_period_index=senior_last_idx,
                day_count_convention=fin.dsrf_day_count,
            )
            dsrf_fee_by_idx = dict(zip(dsrf_schedule.period_indices, dsrf_schedule.dsrf_commitment_fee_keur))

    # ── Build per-period records ───────────────────────────────────────────────
    waterfall_periods: list[CovenantGatedWaterfallPeriod] = []

    # Causal SHL opening balance — carries forward across operating periods
    opening_shl_balance: float = financing.opening_operating_shl_balance_keur

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

        if idx not in signed_post_senior_by_idx:
            raise ValueError(
                f"G2C: operating period {idx} absent from post_senior_cash schedule; "
                "clean engine output is incomplete"
            )
        signed_post_senior = signed_post_senior_by_idx[idx]

        # ── DSRF commitment fee (financing cost, deducted before gate) ────────
        dsrf_fee = dsrf_fee_by_idx.get(idx, 0.0)
        # Net post-senior after DSRF fee (cannot go below 0 for gate input)
        post_senior_after_dsrf = signed_post_senior - dsrf_fee

        # ── Step 1: DSCR covenant gate (upstream of SHL service) ──────────────
        dscr_val = base_dscr_by_idx.get(idx)
        has_senior_ds = senior_ds_nonzero_by_idx.get(idx, False)
        gate_status = _evaluate_distribution_gate(dscr_val, distribution_lockup_dscr, has_senior_ds)

        gate_locked = gate_status == DistributionGateStatus.LOCKED_DSCR_BELOW_LOCKUP

        # Gate output: fcf_for_distribution (R109) — 0 when locked
        pre_gate = max(0.0, post_senior_after_dsrf)
        if gate_locked:
            fcf_for_distribution = 0.0
            covenant_locked = pre_gate
        else:
            fcf_for_distribution = pre_gate
            covenant_locked = 0.0

        # ── Step 2: Causal SHL service from fcf_for_distribution (R112 = R109) ─
        # Uses compute_shl_waterfall_period — the canonical SHL kernel.
        # Gate output is the ONLY cash eligible to reach SHL; gate failure
        # causes PIK accumulation which carries forward into future periods.
        period_start = period_start_by_idx[idx]
        if opening_shl_balance > 0.0 and fin.shl_rate > 0.0:
            dcf = compute_shl_dcf_actual_365_inclusive(period_start, cf_date)
            shl_result = compute_shl_waterfall_period(
                opening_balance_keur=opening_shl_balance,
                annual_rate=fin.shl_rate,
                day_count_fraction=dcf,
                cash_available_for_shl_keur=fcf_for_distribution,
                period_index=idx,
                repayment_mode=ShlRepaymentMode.CASH_SWEEP,
            )
            shl_opening = shl_result.opening_balance_keur
            shl_gross_interest = shl_result.gross_accrued_interest_keur
            actual_shl_cash_int = shl_result.cash_interest_keur
            shl_pik = shl_result.pik_interest_keur
            actual_shl_principal = shl_result.principal_repaid_keur
            shl_closing = shl_result.closing_balance_keur
        else:
            shl_opening = opening_shl_balance
            shl_gross_interest = 0.0
            actual_shl_cash_int = 0.0
            shl_pik = 0.0
            actual_shl_principal = 0.0
            shl_closing = opening_shl_balance

        # Carry closing SHL balance forward as next period's opening
        opening_shl_balance = shl_closing

        # ── Step 3: Equity distribution = fcf_for_distribution residual (R116) ─
        shl_service_actual = actual_shl_cash_int + actual_shl_principal
        distribution = max(0.0, fcf_for_distribution - shl_service_actual)

        # Cash shortfall: post-senior after DSRF fee negative
        cash_shortfall = max(0.0, -post_senior_after_dsrf)

        pure_equity_net = distribution
        total_sponsor_net = pure_equity_net + actual_shl_cash_int + actual_shl_principal

        waterfall_periods.append(CovenantGatedWaterfallPeriod(
            period_index=idx,
            cashflow_date=cf_date,
            is_construction=False,
            base_dscr=dscr_val,
            distribution_lockup_dscr=distribution_lockup_dscr,
            distribution_gate_status=gate_status,
            signed_post_senior_keur=signed_post_senior,
            dsrf_commitment_fee_keur=dsrf_fee,
            fcf_for_distribution_keur=fcf_for_distribution,
            covenant_locked_keur=covenant_locked,
            shl_opening_balance_keur=shl_opening,
            shl_gross_interest_keur=shl_gross_interest,
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

    # ── Return metrics ────────────────────────────────────────────────────────
    pe_cfs = [p.pure_equity_net_cashflow_keur for p in waterfall_periods]
    pe_dates = [p.cashflow_date for p in waterfall_periods]

    pe_xirr = robust_xirr(pe_cfs, pe_dates)
    pe_xirr_status = _xirr_status(pe_cfs, pe_xirr)

    pe_moic: float | None = None
    if total_le > 0.0:
        pos_pe = sum(cf for cf in pe_cfs if cf > 0)
        pe_moic = pos_pe / total_le
        pe_moic_status = ReturnMetricStatus.OK
    else:
        pe_moic_status = ReturnMetricStatus.ZERO_CONTRIBUTION

    ts_cfs = [p.total_sponsor_net_cashflow_keur for p in waterfall_periods]
    ts_xirr = robust_xirr(ts_cfs, pe_dates)
    ts_xirr_status = _xirr_status(ts_cfs, ts_xirr)

    ts_moic: float | None = None
    if total_sponsor_contrib > 0.0:
        pos_ts = sum(cf for cf in ts_cfs if cf > 0)
        ts_moic = pos_ts / total_sponsor_contrib
        ts_moic_status = ReturnMetricStatus.OK
    else:
        ts_moic_status = ReturnMetricStatus.ZERO_CONTRIBUTION

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
    )
