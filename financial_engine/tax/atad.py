"""financial_engine.tax.atad — Annual ATAD interest limitation.

Pure function. No imports from app, finco_core or any framework.

Implementation follows atad_engine.py (v3 logic): the 3 M EUR de-minimis
threshold is ANNUAL, not per-period. In a semi-annual model:
  - H1: interest always deductible (no prior-period accumulation in the year)
  - H2: annual check against (H1 + H2) combined
"""
from __future__ import annotations

from financial_engine.tax.models import AtadPeriodResult


def calculate_atad_schedule(
    ebitda_by_period: tuple[float, ...],
    gross_interest_by_period: tuple[float, ...],
    period_in_year_by_period: tuple[float, ...],
    atad_ebitda_limit: float,
    atad_de_minimis_threshold_keur_annual: float,
) -> tuple[AtadPeriodResult, ...]:
    """Calculate ATAD interest limitation for every model period.

    Parameters
    ----------
    ebitda_by_period : EBITDA for each model period (all periods, incl. construction)
    gross_interest_by_period : gross interest expense for each model period
    period_in_year_by_period : period_in_year for each period (1.0 = H1, 2.0 = H2)
    atad_ebitda_limit : fraction of annual EBITDA that is always deductible (0.30)
    atad_de_minimis_threshold_keur_annual : annual safe harbour in kEUR (3 000)

    Returns
    -------
    Tuple of AtadPeriodResult, one per model period.
    """
    results: list[AtadPeriodResult] = []
    h1_interest = 0.0
    h1_ebitda = 0.0

    for i, (ebitda, gross_interest, period_in_year) in enumerate(
        zip(ebitda_by_period, gross_interest_by_period, period_in_year_by_period)
    ):
        is_h1 = (period_in_year <= 1.0)

        if is_h1:
            # H1: always fully deductible; reset annual accumulators
            h1_interest = gross_interest
            h1_ebitda = ebitda
            deductible = gross_interest
            disallowed = 0.0
            annual_limit = max(
                atad_de_minimis_threshold_keur_annual,
                (h1_ebitda) * atad_ebitda_limit,
            )
            limit_type = (
                "ebitda_30pct"
                if (h1_ebitda * atad_ebitda_limit) >= atad_de_minimis_threshold_keur_annual
                else "min_threshold"
            )
        else:
            # H2: check against accumulated annual totals
            annual_ebitda = h1_ebitda + ebitda
            annual_interest = h1_interest + gross_interest
            ebitda_based = annual_ebitda * atad_ebitda_limit
            annual_limit = max(atad_de_minimis_threshold_keur_annual, ebitda_based)
            limit_type = (
                "ebitda_30pct"
                if ebitda_based >= atad_de_minimis_threshold_keur_annual
                else "min_threshold"
            )
            if annual_interest <= annual_limit:
                deductible = gross_interest
                disallowed = 0.0
            else:
                # H1 was fully deductible; only H2 carries the excess
                remaining_capacity = max(0.0, annual_limit - h1_interest)
                deductible = min(gross_interest, remaining_capacity)
                disallowed = gross_interest - deductible

            # Reset for next year
            h1_interest = 0.0
            h1_ebitda = 0.0

        results.append(AtadPeriodResult(
            period_index=i,
            gross_interest_keur=gross_interest,
            deductible_interest_keur=deductible,
            disallowed_addback_keur=disallowed,
            annual_limit_keur=annual_limit,
            limit_type=limit_type,
            is_h1=is_h1,
        ))

    return tuple(results)
