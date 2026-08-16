"""DSRF commitment fee engine — MVP G2C addendum.

Computes per-period DSRF commitment fee for the DSRF debt-service reserve mode.

Policy: DebtServiceReserveSupportMode.DSRF — the facility is undrawn standby;
NO initial cash Project Use. A commitment fee accrues from COD at:
    fee_keur = dsrf_commitment_keur × dsrf_commitment_fee_rate_pa × period_fraction

The commitment fee is a FINANCING/DEBT-FACILITY cost, not operational OPEX.
It is visible in the waterfall as a pre-SHL deduction from signed_post_senior
(reducing post-senior cash available for the SHL/equity waterfall).

Construction periods: fee = 0 (facility not yet active before COD).
Operating periods: fee > 0 when dsrf_commitment_keur > 0 and rate > 0.

Period fraction: uses actual/365 (ACT/365) day-count from the operating period grid.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DsrfFeeSchedule:
    """Per-period DSRF commitment fee schedule."""
    period_indices: tuple[int, ...]
    dsrf_commitment_fee_keur: tuple[float, ...]
    total_dsrf_commitment_fee_keur: float


def compute_dsrf_fee_schedule(
    period_indices: list[int],
    period_start_dates: list[date],
    period_end_dates: list[date],
    dsrf_commitment_keur: float,
    dsrf_commitment_fee_rate_pa: float,
) -> DsrfFeeSchedule:
    """Compute per-period DSRF commitment fee for operating periods.

    Args:
        period_indices: 1-based period indices (operating periods only).
        period_start_dates: Period start dates corresponding to each index.
        period_end_dates: Period end dates corresponding to each index.
        dsrf_commitment_keur: Undrawn DSRF facility size (kEUR).
        dsrf_commitment_fee_rate_pa: Annual commitment fee rate (e.g. 0.01 = 1% p.a.).

    Returns:
        DsrfFeeSchedule with per-period fees in kEUR.
    """
    fees: list[float] = []
    for start, end in zip(period_start_dates, period_end_dates):
        days = (end - start).days
        period_fraction = days / 365.0
        fee = dsrf_commitment_keur * dsrf_commitment_fee_rate_pa * period_fraction
        fees.append(fee)
    total = sum(fees)
    return DsrfFeeSchedule(
        period_indices=tuple(period_indices),
        dsrf_commitment_fee_keur=tuple(fees),
        total_dsrf_commitment_fee_keur=total,
    )
