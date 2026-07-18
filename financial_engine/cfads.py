"""financial_engine.cfads — Canonical CFADS calculation.

Phase 2B definition:
    CFADS = EBITDA - cash_tax_paid

This is the pre-debt-service, pre-DSRA CFADS. Debt service, DSRA movements,
and distributions are out of Phase 2B scope.

Pure function. No imports from app, finco_core or any framework.
"""
from __future__ import annotations

from dataclasses import dataclass

from financial_engine.tax.models import PeriodTaxResult


@dataclass(frozen=True)
class PeriodCfadsResult:
    """Canonical CFADS for one model period."""
    period_index: int
    ebitda_keur: float
    cash_tax_keur: float
    cfads_keur: float


def calculate_canonical_cfads(
    periods: tuple[object, ...],  # tuple[OperatingPeriodResult]
    tax_results: tuple[PeriodTaxResult, ...],
) -> tuple[PeriodCfadsResult, ...]:
    """Calculate CFADS = EBITDA − cash_tax_paid for every model period.

    Parameters
    ----------
    periods : OperatingPeriodResult tuple from the Phase 2A orchestrator
    tax_results : PeriodTaxResult tuple from calculate_tax()

    Returns
    -------
    tuple[PeriodCfadsResult] — one entry per model period
    """
    results: list[PeriodCfadsResult] = []
    for period, tax in zip(periods, tax_results):
        ebitda = period.ebitda_keur  # type: ignore[attr-defined]
        cash_tax = tax.cash_tax_keur
        results.append(PeriodCfadsResult(
            period_index=period.period_index,  # type: ignore[attr-defined]
            ebitda_keur=ebitda,
            cash_tax_keur=cash_tax,
            cfads_keur=ebitda - cash_tax,
        ))
    return tuple(results)
