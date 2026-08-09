"""financial_engine.shl.waterfall — Clean SHL waterfall period formula (C3B3D2B0).

Single pure function. No mode enum, no mode dispatch.

Natural waterfall formula (handles all settlement modes by arithmetic):
    gross          = opening × annual_rate × day_count_fraction
    cash_interest  = min(cash_available, gross)
    capitalised    = gross - cash_interest
    remaining_cash = cash_available - cash_interest
    principal      = max(0, min(remaining_cash, opening + capitalised))
    closing        = opening + capitalised - principal

When cash_available = 0: full capitalisation.
When 0 < cash_available < gross: partial cash, partial capitalisation.
When cash_available >= gross: full cash interest; surplus sweeps principal.

No drawdown parameter: construction draw is modelled as the opening balance
(period 0, cash=0). Operating periods have zero drawdown.

No hardcoded period boundaries or project-specific constants.
No imports from app, finco_core waterfall, or any production runtime.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ShlWaterfallPeriodResult:
    """Result of one SHL waterfall period.

    Balance roll-forward identity:
        closing_balance_keur = opening_balance_keur + capitalised_interest_keur
                               - principal_repaid_keur

    Fields
    ------
    period_index : int
        0-based period index.
    opening_balance_keur : float
        SHL balance at period start.
    gross_accrued_interest_keur : float
        opening × annual_rate × day_count_fraction.
    cash_interest_keur : float
        Interest settled in cash = min(cash_available, gross).
    pik_interest_keur : float
        Interest capitalised into balance = gross - cash_interest.
    principal_repaid_keur : float
        Principal swept from remaining cash after interest, capped at outstanding.
    closing_balance_keur : float
        opening + capitalised - principal.
    shl_service_keur : float
        Total cash outflow = cash_interest + principal_repaid.
    """
    period_index: int
    opening_balance_keur: float
    gross_accrued_interest_keur: float
    cash_interest_keur: float
    pik_interest_keur: float
    principal_repaid_keur: float
    closing_balance_keur: float
    shl_service_keur: float


def compute_shl_waterfall_period(
    opening_balance_keur: float,
    annual_rate: float,
    day_count_fraction: float,
    cash_available_for_shl_keur: float,
    period_index: int = 0,
) -> ShlWaterfallPeriodResult:
    """Compute one SHL waterfall period using the natural surplus-over-interest formula.

    Parameters
    ----------
    opening_balance_keur : float
        SHL balance at period start. Must be >= 0.
    annual_rate : float
        Annual simple interest rate (e.g. 0.08). Must be >= 0 and finite.
    day_count_fraction : float
        Day-count fraction for this period. Must be > 0 and finite.
    cash_available_for_shl_keur : float
        Cash available for SHL service this period (from the FCF waterfall above SHL).
        0.0 for full-capitalisation periods. Must be >= 0 and finite.
    period_index : int
        0-based period index (for labelling only). Default 0.

    Returns
    -------
    ShlWaterfallPeriodResult

    Raises
    ------
    ValueError
        Any input is non-finite, or opening/rate/cash is negative, or dcf <= 0.
    """
    _check_finite("opening_balance_keur", opening_balance_keur)
    _check_finite("annual_rate", annual_rate)
    _check_finite("day_count_fraction", day_count_fraction)
    _check_finite("cash_available_for_shl_keur", cash_available_for_shl_keur)

    if opening_balance_keur < 0:
        raise ValueError(
            f"opening_balance_keur must be >= 0, got {opening_balance_keur!r} "
            f"(period_index={period_index})"
        )
    if annual_rate < 0:
        raise ValueError(
            f"annual_rate must be >= 0, got {annual_rate!r} "
            f"(period_index={period_index})"
        )
    if day_count_fraction <= 0:
        raise ValueError(
            f"day_count_fraction must be > 0, got {day_count_fraction!r} "
            f"(period_index={period_index})"
        )
    if cash_available_for_shl_keur < 0:
        raise ValueError(
            f"cash_available_for_shl_keur must be >= 0, got {cash_available_for_shl_keur!r} "
            f"(period_index={period_index})"
        )

    gross = opening_balance_keur * annual_rate * day_count_fraction
    cash_interest = min(cash_available_for_shl_keur, gross)
    capitalised = gross - cash_interest
    remaining_cash = cash_available_for_shl_keur - cash_interest
    outstanding = opening_balance_keur + capitalised
    principal = max(0.0, min(remaining_cash, outstanding))
    closing = max(outstanding - principal, 0.0)  # absorb floating-point dust

    return ShlWaterfallPeriodResult(
        period_index=period_index,
        opening_balance_keur=opening_balance_keur,
        gross_accrued_interest_keur=gross,
        cash_interest_keur=cash_interest,
        pik_interest_keur=capitalised,
        principal_repaid_keur=principal,
        closing_balance_keur=closing,
        shl_service_keur=cash_interest + principal,
    )


def _check_finite(name: str, value: object) -> None:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a float, not bool: {value!r}")
    if not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric, got {type(value).__name__}")
    if not math.isfinite(value):  # type: ignore[arg-type]
        raise ValueError(f"{name} must be finite, got {value!r}")
