"""Phase 3B HoldCo aggregation runner.

Linear passthrough aggregation only.
No SHL. No tax template engine. No HoldCo IRR. No monthly model.
No pooled financing. No retained earnings. No cash sweep.

Inputs:
  - HoldCoInputs (SPV codes, ownership %, HoldCo entity config)
  - IndependentPortfolioResult (SPV outputs with per-period waterfall results)

Output:
  - HoldCoResult with per-period HoldCoSPVContribution and sponsor distribution
"""
from __future__ import annotations

import warnings
from dataclasses import replace
from typing import Optional

from domain.portfolio.holdco import (
    HoldCoInputs,
    HoldCoResult,
    HoldCoPeriodResult,
    HoldCoSPVContribution,
    HoldCoEntity,
)
from domain.portfolio.independent import IndependentPortfolioResult
from domain.portfolio.independent.result import SPVOutput


def build_holdco_result(
    holdco_inputs: HoldCoInputs,
    portfolio_result: IndependentPortfolioResult,
) -> HoldCoResult:
    """Build HoldCoResult from HoldCoInputs and IndependentPortfolioResult.

    Aggregation is linear:
      1. For each period: read per-SPV distributions from waterfall_result.periods
      2. Apply ownership % → holdco_share per SPV
      3. Sum holdco_shares → gross_income
      4. Deduct HoldCo opex → taxable_income = max(0, gross_income - opex)
      5. Apply flat tax rate → tax = taxable_income * tax_rate_pa
      6. Compute sponsor distribution = max(0, taxable_income - tax)

    Warnings emitted for:
      - SPV in HoldCoInputs not found in portfolio_result
      - period count mismatch between SPVs

    Parameters
    ----------
    holdco_inputs : HoldCoInputs
        HoldCo configuration (SPV codes, ownership %, entity config)
    portfolio_result : IndependentPortfolioResult
        IndependentPortfolioResult from the portfolio runner

    Returns
    -------
    HoldCoResult
        Per-period aggregation with sponsor distributions (holdco_irr=None)
    """
    # ── Step 1: validate alignment ────────────────────────────────────────
    align_warnings = _validate_holdco_alignment(holdco_inputs, portfolio_result)

    # Build lookup: spv_code → SPVOutput
    spv_map: dict[str, SPVOutput] = {spv.project_code: spv for spv in portfolio_result.spv_outputs}

    # ── Step 2: collect per-period data from each SPV ─────────────────────
    # Determine period range based on first SPV that has waterfall_result
    first_valid_spv = None
    for spv in portfolio_result.spv_outputs:
        if spv.waterfall_result is not None and spv.waterfall_result.periods:
            first_valid_spv = spv
            break

    if first_valid_spv is None or first_valid_spv.waterfall_result is None:
        # No waterfall data — return empty result with alignment warnings
        return HoldCoResult(
            name=holdco_inputs.name,
            periods=[],
            warnings=tuple(align_warnings),
            spv_codes=holdco_inputs.spv_codes,
        )

    num_periods = len(first_valid_spv.waterfall_result.periods)

    # ── Step 3: build ownership lookup ─────────────────────────────────────
    ownership_map: dict[str, float] = {
        o.spv_code: o.ownership_pct for o in holdco_inputs.ownerships
    }

    entity: HoldCoEntity = holdco_inputs.entity or HoldCoEntity(name=holdco_inputs.name)
    tax_rate = entity.tax_rate_pa
    opex_keur = entity.opex.annual_opex_keur

    # Determine number of periods per year from the waterfall structure.
    # If the first SPV has semiannual periods (2 per year), we split opex accordingly.
    # Annual opex is deducted evenly across all periods in a year.
    if first_valid_spv is not None and first_valid_spv.waterfall_result is not None:
        first_periods = first_valid_spv.waterfall_result.periods
        # Semiannual model: period_in_year is 1 (H1) or 2 (H2)
        # If any period has period_in_year=2, model is semiannual
        periods_in_year = 2 if any(
            p.period_in_year == 2 for p in first_periods if hasattr(p, 'period_in_year')
        ) else 1
    else:
        periods_in_year = 1
    opex_per_period = opex_keur / periods_in_year

    # ── Step 4: aggregate per period ──────────────────────────────────────
    periods: list[HoldCoPeriodResult] = []
    total_spv_distributions = 0.0
    total_gross_income = 0.0
    total_opex = 0.0
    total_tax = 0.0
    total_sponsor_dist = 0.0

    for period_idx in range(num_periods):
        contributions: list[HoldCoSPVContribution] = []
        period_gross = 0.0
        period_spv_dist = 0.0

        for ownership in holdco_inputs.ownerships:
            spv_code = ownership.spv_code
            ownership_pct = ownership.ownership_pct

            spv = spv_map.get(spv_code)
            if spv is None:
                # SPV not found in portfolio result — contributed 0 this period
                contributions.append(HoldCoSPVContribution(
                    period=period_idx,
                    spv_code=spv_code,
                    ownership_pct=ownership_pct,
                    spv_distribution_keur=0.0,
                    holdco_share_keur=0.0,
                ))
                continue

            # Get per-period distribution from waterfall
            if spv.waterfall_result is not None and spv.waterfall_result.periods:
                periods_data = spv.waterfall_result.periods
                if period_idx < len(periods_data):
                    # P0.1: HoldCo must consume DSRF-adjusted period distributions
                    # to avoid overstating upstream cash.
                    if spv.adjusted_period_distributions_keur and period_idx < len(spv.adjusted_period_distributions_keur):
                        spv_dist = spv.adjusted_period_distributions_keur[period_idx]
                    else:
                        spv_dist = periods_data[period_idx].distribution_keur
                else:
                    spv_dist = 0.0
            else:
                spv_dist = 0.0

            holdco_share = spv_dist * ownership_pct
            period_gross += holdco_share
            period_spv_dist += spv_dist

            contributions.append(HoldCoSPVContribution(
                period=period_idx,
                spv_code=spv_code,
                ownership_pct=ownership_pct,
                spv_distribution_keur=spv_dist,
                holdco_share_keur=holdco_share,
            ))

        # Apply OpEx (per-period), tax, compute sponsor distribution
        taxable = max(0.0, period_gross - opex_per_period)
        tax = taxable * tax_rate
        sponsor_dist = max(0.0, taxable - tax)

        periods.append(HoldCoPeriodResult(
            period=period_idx,
            contributions=contributions,
            gross_income_keur=period_gross,
            holdco_opex_keur=opex_per_period,
            taxable_income_keur=taxable,
            tax_keur=tax,
            distribution_to_sponsor_keur=sponsor_dist,
            holdco_irr=None,
        ))

        total_spv_distributions += period_spv_dist
        total_gross_income += period_gross
        total_opex += opex_per_period
        total_tax += tax
        total_sponsor_dist += sponsor_dist

    result = HoldCoResult(
        name=holdco_inputs.name,
        periods=periods,
        total_spv_distributions_keur=total_spv_distributions,
        total_gross_income_keur=total_gross_income,
        total_opex_keur=total_opex,
        total_tax_keur=total_tax,
        total_distribution_to_sponsor_keur=total_sponsor_dist,
        holdco_irr=None,
        spv_codes=holdco_inputs.spv_codes,
        warnings=tuple(align_warnings),
    )

    # is_placeholder = False since aggregation actually ran
    return replace(result)  # immutable copy


def _validate_holdco_alignment(
    holdco_inputs: HoldCoInputs,
    portfolio_result: IndependentPortfolioResult,
) -> list[str]:
    """Validate alignment between HoldCoInputs and IndependentPortfolioResult.

    Emits warnings (not errors) for:
      - SPV code in HoldCoInputs not found in portfolio_result.spv_outputs
      - Period count mismatch between SPVs (uses shortest with warning)
    """
    warnings_list: list[str] = []

    # Check SPV codes
    portfolio_spv_codes = {spv.project_code for spv in portfolio_result.spv_outputs}
    for ownership in holdco_inputs.ownerships:
        if ownership.spv_code not in portfolio_spv_codes:
            warnings_list.append(
                f"HoldCoInputs references SPV '{ownership.spv_code}' "
                f"which is not in portfolio_result"
            )

    # Check period alignment — warn if SPVs have different period counts
    period_counts: dict[str, int] = {}
    for spv in portfolio_result.spv_outputs:
        if spv.waterfall_result is not None and spv.waterfall_result.periods:
            period_counts[spv.project_code] = len(spv.waterfall_result.periods)

    if period_counts:
        unique_counts = set(period_counts.values())
        if len(unique_counts) > 1:
            min_count = min(unique_counts)
            max_count = max(unique_counts)
            warnings_list.append(
                f"Period count mismatch across SPVs: "
                f"min={min_count}, max={max_count}. "
                f"Using shortest ({min_count} periods)."
            )

    return warnings_list


def aggregate_holdco_periods(
    holdco_inputs: HoldCoInputs,
    portfolio_result: IndependentPortfolioResult,
) -> list[HoldCoPeriodResult]:
    """Alias for build_holdco_result — returns the period list.

    Provided for API symmetry with the planned aggregation interface.
    """
    return build_holdco_result(holdco_inputs, portfolio_result).periods


def validate_holdco_alignment(
    holdco_inputs: HoldCoInputs,
    portfolio_result: IndependentPortfolioResult,
) -> list[str]:
    """Validate HoldCoInputs alignment against IndependentPortfolioResult.

    Returns list of warning strings (empty = aligned).
    """
    return _validate_holdco_alignment(holdco_inputs, portfolio_result)