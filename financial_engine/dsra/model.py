"""financial_engine.dsra.model — Canonical CASH_DSRA roll-forward engine.

Pure computation. No imports from app, legacy waterfall, project factories,
Excel fixtures, or diagnostic scripts. No project-name dispatch.

Ordering (CASH_DSRA, per operating period):
    opening  = requirement_keur at first operating period (COD handshake)
               or prior closing_balance for subsequent periods
    top_up   = min(max(0, target - opening), max(0, cash_before))
    draw     = min(opening, max(0, -cash_before))   [when cash_before < 0]
    release  = 0  [UNRESOLVED_RELEASE_POLICY]
    closing  = opening + top_up - draw - release
    cash_after = cash_before - top_up + draw + release

Cash conservation:  cash_before - top_up + draw + release == cash_after
Balance conservation: opening + top_up - draw - release == closing
"""
from __future__ import annotations

from finco_core.inputs import DebtServiceReserveSupportMode

from financial_engine.dsra.contracts import (
    CashDsraInput,
    CashDsraPeriodResult,
    CashDsraSchedules,
)
from financial_engine.results import OperatingPeriodResult, PostSeniorCashSchedules

_FLOAT_TOLERANCE = 1e-9


def run_cash_dsra_model(
    post_senior_cash: PostSeniorCashSchedules,
    dsra_input: CashDsraInput | None,
    periods: tuple[OperatingPeriodResult, ...],
) -> CashDsraSchedules:
    """Compute CASH_DSRA roll-forward from signed post-Senior cash.

    Parameters
    ----------
    post_senior_cash:
        Pre-reserve Phase 2C output. cash_after_senior_before_reserves_keur
        is the signed per-period cash BEFORE any DSRA adjustment.
    dsra_input:
        Typed reserve policy. None treated as NONE mode (neutral).
    periods:
        All model periods (construction + operating) from Phase 2B result.
        Used to identify is_construction per period_index.

    Returns
    -------
    CashDsraSchedules with per-period roll-forward and aggregate diagnostics.
    """
    if dsra_input is None:
        dsra_input = CashDsraInput(mode=DebtServiceReserveSupportMode.NONE, requirement_keur=0.0)

    mode = dsra_input.mode
    req = dsra_input.requirement_keur

    if mode == DebtServiceReserveSupportMode.NONE and req > _FLOAT_TOLERANCE:
        raise ValueError(
            "CASH_DSRA_NONE_MODE_WITH_POSITIVE_REQUIREMENT: "
            f"dsra_input.mode=NONE but requirement_keur={req}. "
            "Set requirement_keur=0.0 or change mode to CASH_DSRA."
        )

    is_constr_by_idx: dict[int, bool] = {p.period_index: p.is_construction for p in periods}
    period_indices = post_senior_cash.period_indices
    cash_before_all = post_senior_cash.cash_after_senior_before_reserves_keur

    period_results: list[CashDsraPeriodResult] = []
    total_top_up = 0.0
    total_draw = 0.0
    total_release = 0.0

    if mode in (DebtServiceReserveSupportMode.NONE, DebtServiceReserveSupportMode.DSRF):
        # Neutral pass-through for all periods — no reserve movements.
        for idx, cash_before in zip(period_indices, cash_before_all):
            is_constr = is_constr_by_idx.get(idx, False)
            period_results.append(_neutral_period(idx, is_constr, cash_before, 0.0))
    else:
        # CASH_DSRA: roll-forward for operating periods, neutral for construction.
        prev_closing = 0.0
        first_op_seen = False

        for idx, cash_before in zip(period_indices, cash_before_all):
            is_constr = is_constr_by_idx.get(idx, False)

            if is_constr:
                # Construction: reserve not yet funded; all movements zero.
                # required_balance shown as req (policy is active but funded at COD).
                period_results.append(CashDsraPeriodResult(
                    period_index=idx,
                    is_construction=True,
                    opening_balance_keur=0.0,
                    required_balance_keur=req,
                    cash_before_dsra_keur=cash_before,
                    draw_to_cover_shortfall_keur=0.0,
                    top_up_keur=0.0,
                    release_keur=0.0,
                    closing_balance_keur=0.0,
                    cash_after_dsra_keur=cash_before,
                    shortfall_keur=req,
                    target_met=req <= _FLOAT_TOLERANCE,
                ))
                continue

            # Operating period
            if not first_op_seen:
                # COD funding handshake: opening = requirement (funded at construction close).
                opening = req
                first_op_seen = True
            else:
                opening = prev_closing

            target = req

            if cash_before >= 0.0:
                top_up = min(max(0.0, target - opening), cash_before)
                draw = 0.0
            else:
                # Negative post-Senior cash: draw from reserve to cover shortfall.
                draw = min(opening, -cash_before)
                top_up = 0.0

            release = 0.0  # UNRESOLVED_RELEASE_POLICY
            closing = opening + top_up - draw - release
            cash_after = cash_before - top_up + draw + release
            shortfall = max(0.0, target - closing)
            target_met = closing >= target - _FLOAT_TOLERANCE

            total_top_up += top_up
            total_draw += draw
            prev_closing = closing

            period_results.append(CashDsraPeriodResult(
                period_index=idx,
                is_construction=False,
                opening_balance_keur=opening,
                required_balance_keur=target,
                cash_before_dsra_keur=cash_before,
                draw_to_cover_shortfall_keur=draw,
                top_up_keur=top_up,
                release_keur=release,
                closing_balance_keur=closing,
                cash_after_dsra_keur=cash_after,
                shortfall_keur=shortfall,
                target_met=target_met,
            ))

    diagnostics = _build_diagnostics(mode, req)
    final_closing = period_results[-1].closing_balance_keur if period_results else 0.0

    return CashDsraSchedules(
        mode=mode.value,
        requirement_keur=req,
        period_results=tuple(period_results),
        total_top_up_keur=total_top_up,
        total_draw_keur=total_draw,
        total_release_keur=total_release,
        final_closing_balance_keur=final_closing,
        diagnostics=tuple(diagnostics),
    )


def _neutral_period(
    period_index: int,
    is_construction: bool,
    cash_before: float,
    requirement_keur: float,
) -> CashDsraPeriodResult:
    """Return a zero-movement period result (NONE / DSRF mode or construction pass-through)."""
    return CashDsraPeriodResult(
        period_index=period_index,
        is_construction=is_construction,
        opening_balance_keur=0.0,
        required_balance_keur=0.0,
        cash_before_dsra_keur=cash_before,
        draw_to_cover_shortfall_keur=0.0,
        top_up_keur=0.0,
        release_keur=0.0,
        closing_balance_keur=0.0,
        cash_after_dsra_keur=cash_before,
        shortfall_keur=0.0,
        target_met=True,
    )


def _build_diagnostics(
    mode: DebtServiceReserveSupportMode,
    req: float,
) -> list[str]:
    diags: list[str] = []
    if mode == DebtServiceReserveSupportMode.NONE:
        diags.append("DSRA_NONE_NEUTRAL_PASS_THROUGH: all reserve movements zero")
    elif mode == DebtServiceReserveSupportMode.DSRF:
        diags.append(
            "DSRF_FEE_ENGINE_NOT_HERE: DSRF commitment fee handled by "
            "financial_engine.financing.dsrf; no DSRA draw engine added"
        )
        diags.append("CASH_DSRA_ROLL_FORWARD_NOT_APPLICABLE_FOR_DSRF_MODE: pass-through only")
    elif mode == DebtServiceReserveSupportMode.CASH_DSRA:
        diags.append(
            "UNRESOLVED_RELEASE_POLICY: release_keur=0 in PR-3; "
            "no source evidence for release timing in TUHO/Oborovo/KUPI "
            "(all have requirement_keur=0 → neutral). Retain balance."
        )
        diags.append(
            f"COD_FUNDING_HANDSHAKE: opening_balance at first operating period "
            f"= {req} kEUR = debt_service_reserve_requirement_keur "
            f"(funded as Project Use at construction close)"
        )
        diags.append(
            "CASH_DSRA_TARGET_AUTHORITY: static scalar requirement_keur. "
            "dsra_months NOT consumed — no source evidence for dynamic 6-month DS target."
        )
    return diags
