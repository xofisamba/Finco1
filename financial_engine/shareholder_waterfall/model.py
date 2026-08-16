"""MVP G2C — Covenant-Gated Shareholder Waterfall model.

Extends G2B with a DSCR distribution lockup gate sourced from
Oborovo workbook Inputs!D223 (senior_lockup_dscr = 1.10).

Gate logic (per operating period):
  1. Compute pre_gate_distribution = max(0, signed_post_shl)
     (identical to G2B DISTRIBUTE_ALL_POST_SHL_CASH)
  2. Evaluate DSCR gate: base_dscr vs distribution_lockup_dscr
  3. If gate locked: legal_equity_distribution = 0
                     covenant_locked = pre_gate_distribution
  4. If gate open:   legal_equity_distribution = pre_gate_distribution
                     covenant_locked = 0

SHL cash receipts are NOT gated — actual SHL interest and principal are
paid regardless of DSCR lockup (gate only blocks equity distributions).

Source map:
  R84 → post_senior_cash.cash_after_senior_before_reserves_keur (signed, pre-DSRA)
  R99 → legal_equity_distribution_keur (0 when gated)
  R102 → shl receipts (interest + principal, then residual = R99)
"""
from __future__ import annotations

from datetime import date

from finco_core.inputs import ProjectInputs, SponsorFundingMode

from finco_core.sponsor.xirr import robust_xirr
from financial_engine.financing.contracts import (
    ConstructionFundingPeriod,
    ProjectFinancingResult,
)
from financial_engine.financing.project import run_project_financing_model
from financial_engine.results import ProjectModelResult
from financial_engine.sponsor_returns.contracts import ReturnMetricStatus
from financial_engine.sponsor_returns.model import _allocate_actual_shl_cash_receipts
from financial_engine.shareholder_waterfall.contracts import (
    CovenantGatedWaterfallPeriod,
    CovenantGatedWaterfallResult,
    DistributionGateStatus,
)


def _evaluate_distribution_gate(
    base_dscr: float | None,
    distribution_lockup_dscr: float,
    has_senior_ds: bool,
) -> DistributionGateStatus:
    """Evaluate the DSCR covenant distribution gate.

    Source: Oborovo Inputs!D223 → generic distribution_lockup_dscr.
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
    of the G2B SHL-gated distribution mechanics. SHL cash receipts are NOT covenant-gated.

    Source authority: Oborovo Inputs!D223 → lockup_dscr = 1.10 (generic parameter).
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

    shl_cash_interest_by_idx: dict[int, float] = {}
    shl_principal_by_idx: dict[int, float] = {}
    shl_debt_service_by_idx: dict[int, float] = {}

    if shl is not None:
        shl_cash_interest_by_idx = dict(zip(shl.period_indices, shl.shl_cash_interest_keur))
        shl_principal_by_idx = dict(zip(shl.period_indices, shl.shl_principal_keur))
        shl_debt_service_by_idx = dict(zip(shl.period_indices, shl.shl_debt_service_keur))

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

    # ── Build per-period records ───────────────────────────────────────────────
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
            signed_post_shl_keur=0.0,
            shl_cash_interest_receipt_keur=0.0,
            shl_principal_receipt_keur=0.0,
            pre_gate_distribution_keur=0.0,
            legal_equity_distribution_keur=0.0,
            covenant_locked_keur=0.0,
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

        if shl is not None:
            if idx not in shl_debt_service_by_idx:
                raise ValueError(
                    f"G2C: SHL schedule exists but operating period {idx} absent "
                    "from shl_debt_service; SHL engine output is incomplete"
                )
            scheduled_shl_service_due = shl_debt_service_by_idx[idx]
            scheduled_cash_interest = shl_cash_interest_by_idx.get(idx, 0.0)
            scheduled_principal_due = shl_principal_by_idx.get(idx, 0.0)
            actual_shl_cash_int, actual_shl_principal = _allocate_actual_shl_cash_receipts(
                signed_post_senior,
                scheduled_cash_interest,
                scheduled_principal_due,
            )
        else:
            scheduled_shl_service_due = 0.0
            actual_shl_cash_int = 0.0
            actual_shl_principal = 0.0

        # Contractual signed_post_shl drives distribution and shortfall
        signed_post_shl = signed_post_senior - scheduled_shl_service_due
        pre_gate_distribution = max(0.0, signed_post_shl)
        cash_shortfall = max(0.0, -signed_post_shl)

        # DSCR covenant gate
        dscr_val = base_dscr_by_idx.get(idx)
        has_senior_ds = senior_ds_nonzero_by_idx.get(idx, False)
        gate_status = _evaluate_distribution_gate(dscr_val, distribution_lockup_dscr, has_senior_ds)

        gate_locked = gate_status == DistributionGateStatus.LOCKED_DSCR_BELOW_LOCKUP
        distribution = 0.0 if gate_locked else pre_gate_distribution
        covenant_locked = pre_gate_distribution if gate_locked else 0.0

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
            signed_post_shl_keur=signed_post_shl,
            shl_cash_interest_receipt_keur=actual_shl_cash_int,
            shl_principal_receipt_keur=actual_shl_principal,
            pre_gate_distribution_keur=pre_gate_distribution,
            legal_equity_distribution_keur=distribution,
            covenant_locked_keur=covenant_locked,
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
    )
