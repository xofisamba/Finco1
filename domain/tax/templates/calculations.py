"""Phase 6B.1 — Tax calculation primitives using TaxTemplate schema.

These are pure functions. No mutation, no side effects, no waterfall wiring.
Use Phase 6A TaxTemplate schema types (CITTier, TaxDepreciationRule).

CAVEAT: This module implements raw calculation logic only.
No ATAD interest limitation, no thin-cap adjustment, no loss carryforward,
no withholding tax — those are handled by a future tax engine layer.
"""
from __future__ import annotations

from domain.tax.templates.inputs import (
    CITTier,
    TaxDepreciationRule,
)


# ── CIT ───────────────────────────────────────────────────────────────────────

def calculate_progressive_cit(
    taxable_profit_keur: float,
    cit_tiers: tuple[CITTier, ...],
) -> float:
    """Calculate CIT for a given taxable profit using progressive bracket tiers.

    Pure function: no mutation of inputs.

    Parameters
    ----------
    taxable_profit_keur : float
        Taxable profit in thousands of EUR. Can be negative or zero.
    cit_tiers : tuple[CITTier, ...]
        CIT brackets, must be pre-validated (contiguous, no gaps,
        first starts at 0, at most one unbounded at the end).

    Returns
    -------
    float
        Total CIT liability in kEUR. Returns 0.0 when taxable_profit <= 0.

    Rules
    -----
    - taxable_profit <= 0 → tax = 0
    - Each tier is applied to the slice of profit within its bracket range.
    - Tiers must be contiguous and sorted; no gaps assumed.

    Examples
    --------
    Flat 10%: single tier (0, None, 0.10)

    Progressive 9%/15%:
      tiers = (
          CITTier(0.0, 100_000.0, 0.09),   # 0-100k → 9%
          CITTier(100_000.0, None, 0.15),  # 100k+ → 15%
      )
      calculate_progressive_cit(150_000, tiers)  # → 9_000 + 7_500 = 16_500

    Note
    ----
    This function does NOT validate cit_tiers contiguity —
    assume callers pass pre-validated tiers (TaxTemplate.__post_init__
    enforces contiguity for templates loaded via get_builtin_tax_templates).
    """
    if taxable_profit_keur <= 0.0:
        return 0.0

    if not cit_tiers:
        return 0.0

    total_tax = 0.0
    remaining_profit = taxable_profit_keur

    # Tiers must be sorted by min_profit_keur (TaxTemplate enforces this)
    for tier in cit_tiers:
        if remaining_profit <= 0.0:
            break

        tier_min = tier.min_profit_keur
        tier_max = tier.max_profit_keur  # None = unbounded

        if tier_max is None:
            # Unbounded top tier — applies to all remaining profit
            taxable_in_tier = remaining_profit
        else:
            # Bounded tier — profit in this bracket
            tier_width = tier_max - tier_min
            # Profit already above min of this tier = remaining_profit adjusted by prior tiers
            # Since tiers are contiguous and sorted:
            # remaining_profit = taxable_profit_keur - sum of all prior tier widths consumed
            # = taxable_profit_keur - tier_min (since all prior tiers consumed up to tier_min)
            # Actually, since we process in order and break when remaining <= 0:
            # the profit in this tier = min(remaining_profit, tier_width)
            taxable_in_tier = min(remaining_profit, tier_max - tier_min)

        total_tax += taxable_in_tier * tier.tax_rate

        # Reduce remaining for next tier
        if tier_max is not None:
            remaining_profit -= (tier_max - tier_min)

    return total_tax


# ── Depreciation ──────────────────────────────────────────────────────────────

def get_tax_depreciation_rate(rule: TaxDepreciationRule) -> float:
    """Compute the effective annual tax depreciation rate for a rule.

    Pure function: no mutation of rule.

    Parameters
    ----------
    rule : TaxDepreciationRule
        Depreciation rule for one asset category.

    Returns
    -------
    float
        Effective annual tax depreciation rate as a decimal
        (e.g., 0.05 = 5% per year). Returns 0.0 when
        rule.deductible is False or no rate can be derived.

    Rules (applied in order)
    ------------------------
    1. deductible=False → return 0.0 immediately
    2. max_deductible_rate is set → cap applies
    3. annual_rate is set → use it directly
    4. useful_life_years is set and > 0 → rate = 1 / useful_life_years
    5. Otherwise → return 0.0

    Effective rate = min(base_rate, max_deductible_rate) when cap exists.

    Examples
    --------
    Straight-line 20y: useful_life_years=20 → rate=0.05
    DB 25%: annual_rate=0.25 → rate=0.25
    ME infrastructure cap: base_rate=0.05, max_cap=0.025 → effective=0.025
    Non-deductible land: deductible=False → 0.0
    """
    if rule.deductible is False:
        return 0.0

    # Determine base rate
    if rule.annual_rate is not None:
        base_rate = rule.annual_rate
    elif rule.useful_life_years is not None and rule.useful_life_years > 0:
        base_rate = 1.0 / rule.useful_life_years
    else:
        # Cannot derive a rate — e.g. deductible but no rate info
        return 0.0

    # Apply cap if set
    if rule.max_deductible_rate is not None:
        return min(base_rate, rule.max_deductible_rate)

    return base_rate


def calculate_tax_depreciation_keur(
    asset_cost_keur: float,
    rule: TaxDepreciationRule,
) -> float:
    """Calculate annual tax depreciation amount for a given asset cost.

    Pure function: no mutation of rule.

    Parameters
    ----------
    asset_cost_keur : float
        Asset cost in thousands of EUR. Must be >= 0.
    rule : TaxDepreciationRule
        Depreciation rule for this asset category.

    Returns
    -------
    float
        Annual tax depreciation deduction in kEUR.
        Returns 0.0 for non-deductible assets.

    Raises
    ------
    ValueError
        If asset_cost_keur is negative.

    Notes
    -----
    bonus_depreciation_pct is not applied in this primitive —
    future extension point for year-1 bonus deduction logic.
    """
    if asset_cost_keur < 0.0:
        raise ValueError(
            f"asset_cost_keur must be >= 0, got {asset_cost_keur}"
        )

    if asset_cost_keur == 0.0:
        return 0.0

    rate = get_tax_depreciation_rate(rule)
    return asset_cost_keur * rate


# ── Taxable Income ────────────────────────────────────────────────────────────

def calculate_taxable_income_keur(
    ebitda_keur: float,
    deductible_interest_keur: float,
    tax_depreciation_keur: float,
    non_deductible_addbacks_keur: float = 0.0,
) -> float:
    """Calculate taxable income from EBITDA.

    Pure function: no side effects.

    Formula
    -------
    taxable_income = ebitda
                   - deductible_interest
                   - tax_depreciation
                   + non_deductible_addbacks

    Parameters
    ----------
    ebitda_keur : float
        EBITDA in thousands of EUR.
    deductible_interest_keur : float
        Deductible interest expense in kEUR.
    tax_depreciation_keur : float
        Annual tax depreciation deduction in kEUR.
    non_deductible_addbacks_keur : float, optional
        Non-deductible expenses to add back (e.g., entertainment,
        provisions). Default 0.0.

    Returns
    -------
    float
        Taxable income in kEUR. May be negative.

    Note
    ----
    This primitive does NOT apply:
    - ATAD EBITDA interest limitation (apply separately via tax engine)
    - Thin-cap interest adjustment
    - Loss carryforward utilisation
    - Deferred tax accounting
    """
    return (
        ebitda_keur
        - deductible_interest_keur
        - tax_depreciation_keur
        + non_deductible_addbacks_keur
    )