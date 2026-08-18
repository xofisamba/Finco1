"""SHL construction period engine — multi-period draw schedule (Fix 3 architecture).

This module provides the non-production multi-period construction engine.
Production single-period construction is in production.py::compute_shl_schedule.

FULL_PRINCIPAL_AT_FC_COMPOUND_COUNTERFACTUAL diagnostic functions are
provided for testing and comparison only — they assume all SHL principal
exists at financial close and are NOT used in production calculations.

SIMPLE multi-period semantics (Fix 2 closeout)
-----------------------------------------------
SIMPLE interest must NOT compound: accumulated PIK from prior periods must
never enter the interest basis of a subsequent period.

  cash_principal_balance[t] = cash_principal_balance[t-1] + draw[t]
  interest[t] = cash_principal_balance[t] * annual_rate * dcf[t]
  accumulated_pik[t] = accumulated_pik[t-1] + interest[t]
  closing_total_shl[t] = cash_principal_balance[t] + accumulated_pik[t]

The cash-principal balance is tracked separately and exposed via
ShlConstructionPeriodResult.cash_principal_balance_keur.

COMPOUND_PERIODIC multi-period semantics
-----------------------------------------
Prior closing total (including accumulated PIK) enters the next period's
interest basis:

  balance_for_interest[t] = prior_closing_total_shl[t-1] + draw[t]
  interest[t] = balance_for_interest[t] * ((1+rate)^dcf[t] - 1)
  closing_total_shl[t] = balance_for_interest[t] + interest[t]
"""
from __future__ import annotations

from dataclasses import dataclass
from finco_core.inputs._models import ShlConstructionInterestMethod


@dataclass(frozen=True)
class ShlConstructionPeriodInput:
    """One construction draw period for the multi-period engine."""
    draw_keur: float
    day_count_fraction: float
    period_index: int = 0


@dataclass(frozen=True)
class ShlConstructionPeriodResult:
    """Result for one construction draw period.

    For SIMPLE: opening_balance_keur reflects cash draws only (no prior PIK).
    For COMPOUND_PERIODIC: opening_balance_keur includes prior PIK.
    cash_principal_balance_keur is the cumulative cash draw balance (SIMPLE path only;
    equals closing_balance_keur for COMPOUND_PERIODIC).
    """
    period_index: int
    opening_balance_keur: float
    draw_keur: float
    pik_interest_keur: float
    closing_balance_keur: float
    cash_principal_balance_keur: float = 0.0


@dataclass(frozen=True)
class ShlConstructionScheduleResult:
    """Result of compute_shl_construction_schedule."""
    periods: tuple[ShlConstructionPeriodResult, ...]
    total_pik_keur: float
    opening_operating_shl_balance_keur: float
    method: ShlConstructionInterestMethod
    interest_rate: float


def compute_shl_construction_schedule(
    opening_balance_keur: float,
    periods: tuple[ShlConstructionPeriodInput, ...],
    annual_rate: float,
    method: ShlConstructionInterestMethod,
) -> ShlConstructionScheduleResult:
    """Multi-period SHL construction engine for Fix 3 architecture.

    SIMPLE: interest basis = cash principal draws only (no PIK compounding).
      interest[t] = cash_principal_balance[t] * rate * dcf[t]
      PIK does NOT re-enter the interest basis in subsequent periods.

    COMPOUND_PERIODIC: prior closing total (including PIK) enters next period.
      interest[t] = (prior_closing + draw[t]) * ((1+rate)^dcf[t] - 1)

    Production single-draw boundary:
      For a single-period draw at financial close with dcf covering the full
      construction period, SIMPLE = P*r*t and COMPOUND = P*((1+r)^t - 1),
      matching compute_shl_construction_pik_keur in this module and the
      production.py single-draw path. Both are documented in CLAUDE.md
      source-evidence constants (KUPI delta +436.179 kEUR, Finco +509.413 kEUR).
    """
    results: list[ShlConstructionPeriodResult] = []

    if method == ShlConstructionInterestMethod.SIMPLE:
        # SIMPLE: track cash principal balance and accumulated PIK separately.
        # Interest basis = cash principal only; PIK never re-enters the basis.
        cash_principal = opening_balance_keur
        accumulated_pik = 0.0
        for p in periods:
            cash_principal = cash_principal + p.draw_keur
            if p.day_count_fraction == 0.0 or cash_principal == 0.0:
                interest = 0.0
            else:
                interest = cash_principal * annual_rate * p.day_count_fraction
            accumulated_pik = accumulated_pik + interest
            closing_total = cash_principal + accumulated_pik
            # opening_balance_keur for SIMPLE = cash principal before this draw
            opening_cash = cash_principal - p.draw_keur
            results.append(ShlConstructionPeriodResult(
                period_index=p.period_index,
                opening_balance_keur=opening_cash,
                draw_keur=p.draw_keur,
                pik_interest_keur=interest,
                closing_balance_keur=closing_total,
                cash_principal_balance_keur=cash_principal,
            ))
        total_pik = sum(r.pik_interest_keur for r in results)
        final_closing = results[-1].closing_balance_keur if results else opening_balance_keur
        return ShlConstructionScheduleResult(
            periods=tuple(results),
            total_pik_keur=total_pik,
            opening_operating_shl_balance_keur=final_closing,
            method=method,
            interest_rate=annual_rate,
        )
    else:
        # COMPOUND_PERIODIC: prior closing total (including PIK) is the next
        # period's opening balance for interest accrual.
        balance = opening_balance_keur
        for p in periods:
            balance_after_draw = balance + p.draw_keur
            if p.day_count_fraction == 0.0 or balance_after_draw == 0.0:
                interest = 0.0
            else:
                interest = balance_after_draw * (
                    (1.0 + annual_rate) ** p.day_count_fraction - 1.0
                )
            closing = balance_after_draw + interest
            results.append(ShlConstructionPeriodResult(
                period_index=p.period_index,
                opening_balance_keur=balance,
                draw_keur=p.draw_keur,
                pik_interest_keur=interest,
                closing_balance_keur=closing,
                cash_principal_balance_keur=closing,
            ))
            balance = closing
        total_pik = sum(r.pik_interest_keur for r in results)
        return ShlConstructionScheduleResult(
            periods=tuple(results),
            total_pik_keur=total_pik,
            opening_operating_shl_balance_keur=balance,
            method=method,
            interest_rate=annual_rate,
        )


def compute_shl_construction_pik_keur(
    shl_cash_principal_keur: float,
    annual_rate: float,
    construction_day_count_fraction: float,
    method: ShlConstructionInterestMethod,
) -> float:
    """FULL_PRINCIPAL_AT_FC diagnostic: PIK under the assumption all SHL drawn at FC.

    SIMPLE: P * r * t
    COMPOUND_PERIODIC: P * ((1+r)^t - 1)

    This function assumes the FULL principal exists at financial close.
    It is valid for diagnostic delta computation (source basis ~436.179 kEUR,
    Finco basis ~509.413 kEUR) but is NOT used in production calculations.
    Production uses compute_shl_schedule() in production.py.
    """
    if construction_day_count_fraction == 0.0 or shl_cash_principal_keur == 0.0:
        return 0.0
    if method == ShlConstructionInterestMethod.COMPOUND_PERIODIC:
        return shl_cash_principal_keur * (
            (1.0 + annual_rate) ** construction_day_count_fraction - 1.0
        )
    elif method == ShlConstructionInterestMethod.SIMPLE:
        return shl_cash_principal_keur * annual_rate * construction_day_count_fraction
    else:
        raise ValueError(
            f"compute_shl_construction_pik_keur: unsupported method {method!r}"
        )


def compute_full_principal_at_fc_compound_counterfactual(
    full_principal_keur: float,
    annual_rate: float,
    total_construction_dcf: float,
) -> float:
    """DIAGNOSTIC ONLY: full-at-FC compound formula P*((1+r)^T - 1).

    FULL_PRINCIPAL_AT_FC_COMPOUND_COUNTERFACTUAL: assumes entire SHL principal
    drawn at financial close. Not used in production. Valid only for comparison
    diagnostics (source-basis delta ~436.179 kEUR, Finco delta ~509.413 kEUR).
    """
    if total_construction_dcf == 0.0 or full_principal_keur == 0.0:
        return 0.0
    return full_principal_keur * ((1.0 + annual_rate) ** total_construction_dcf - 1.0)
