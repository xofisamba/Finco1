"""financial_engine.adapters.shl_cash_seam — Typed production seam for SHL cash (C3B3D2B1).

Derives cash_available_for_shl_keur per period from a Phase 2C (senior debt) result.

Production cash lineage (Oborovo-proven, generic)
-------------------------------------------------
    CFADS[p]              = EBITDA[p] - cash_tax[p]        (Phase 2B)
    senior_ds[p]          = interest[p] + principal[p]     (Phase 2C)
    cash_for_shl[p]       = CFADS[p] - senior_ds[p]        (this seam)

Waterfall ordering:
    Revenue
    OPEX
    EBITDA
    − cash_tax                     → CFADS (pre-debt)
    − senior_interest              ↘
    − senior_principal             → post-senior-debt cash = cash_for_shl
    − shl_cash_interest            ↘
    − shl_principal_repayment      → post-SHL cash
    [DSRA, distributions — downstream, not modelled in C3B3D2B1]

Construction period treatment
------------------------------
Construction periods (is_construction=True) return cash_available_for_shl = 0.0.
The construction SHL period is PIK (no cash service required).

Post-senior-maturity treatment
-------------------------------
For operating periods after senior debt maturity (senior_ds = 0), the full
CFADS is available for SHL service: cash_for_shl = CFADS.

DSRA boundary
-------------
DSRA movements are downstream of SHL and do NOT reduce cash_available_for_shl.
This seam does not model DSRA.

Tax interaction
---------------
SHL gross accrued interest SHOULD feed into PeriodInterestInput.shl_interest_keur
in the tax engine, reducing taxable income.  In C3B3D2B1, SHL interest is NOT
fed back into the Phase 2C fixed-point loop (SHL_OUTSIDE_FIXED_POINT).
The approximation magnitude is bounded by shl_interest × tax_rate and documented
in the reconciliation doc.  Full circular resolution is deferred to C3B3D2B2.

Independence
------------
This seam reads SeniorDebtSchedules and TaxAndCfadsSchedules from the Phase 2C
result.  It does NOT read SHL inputs, SHL balance, or SHL interest.
Changing Senior Debt convention (ACT/360) does NOT alter SHL convention (ACT/365).
Changing SHL convention does NOT alter Senior Debt convention.

No imports from app, finco_core waterfall, or any production runtime beyond
the clean engine result types.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from financial_engine.results import ProjectModelResult


@dataclass(frozen=True)
class ShlCashAvailableByPeriod:
    """Cash available for SHL service in one model period.

    Fields
    ------
    period_index : int
        0-based model period index.
    is_construction : bool
        True for the construction period.
    cfads_keur : float
        CFADS from Phase 2B (EBITDA - cash_tax). 0.0 for construction.
    senior_debt_service_keur : float
        Senior debt service (interest + principal) from Phase 2C.
        0.0 for construction and post-maturity periods.
    cash_available_for_shl_keur : float
        CFADS - senior_debt_service.  0.0 for construction (SHL is PIK).
    """
    period_index: int
    is_construction: bool
    cfads_keur: float
    senior_debt_service_keur: float
    cash_available_for_shl_keur: float


def compute_shl_cash_from_phase2c(
    phase2c_result: "ProjectModelResult",
) -> tuple[ShlCashAvailableByPeriod, ...]:
    """Derive cash_available_for_shl_keur from a Phase 2C result.

    Parameters
    ----------
    phase2c_result : ProjectModelResult
        A result produced by financial_engine.orchestrator.run_senior_debt_model.
        Must have tax_and_cfads and senior_debt populated.

    Returns
    -------
    tuple[ShlCashAvailableByPeriod, ...]
        One entry per model period (construction + all operating), in period order.

    Raises
    ------
    ValueError
        If tax_and_cfads or senior_debt sections are missing from the result.
    """
    tac = phase2c_result.tax_and_cfads
    sd = phase2c_result.senior_debt
    periods = phase2c_result.periods

    if tac is None:
        raise ValueError(
            "compute_shl_cash_from_phase2c: tax_and_cfads is None — "
            "Phase 2C result must include Tax/CFADS schedules"
        )
    if sd is None:
        raise ValueError(
            "compute_shl_cash_from_phase2c: senior_debt is None — "
            "Phase 2C result must include SeniorDebtSchedules"
        )

    # Build lookup maps keyed by period_index.
    cfads_by_idx: dict[int, float] = dict(zip(tac.period_indices, tac.cfads_keur))
    sd_service_by_idx: dict[int, float] = dict(
        zip(sd.period_indices, sd.senior_debt_service_keur)
    )

    results: list[ShlCashAvailableByPeriod] = []
    for p in periods:
        idx = p.period_index
        is_constr: bool = p.is_construction

        cfads = cfads_by_idx.get(idx, 0.0)
        senior_ds = sd_service_by_idx.get(idx, 0.0)

        if is_constr:
            # Construction SHL is PIK: no cash service, regardless of any
            # positive CFADS that may appear in the construction period.
            cash_for_shl = 0.0
        else:
            # Operating: cash_for_shl = CFADS - senior_debt_service.
            # senior_ds is already >= 0 (sum of interest + principal, both >= 0).
            cash_for_shl = max(0.0, cfads - senior_ds)

        results.append(ShlCashAvailableByPeriod(
            period_index=idx,
            is_construction=is_constr,
            cfads_keur=cfads,
            senior_debt_service_keur=senior_ds,
            cash_available_for_shl_keur=cash_for_shl,
        ))

    return tuple(results)
