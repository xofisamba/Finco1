"""Phase 6B.2/6B.3 — Tax depreciation schedule and tax loss carryforward schedule.

These are pure functions. No mutation, no side effects, no waterfall wiring.

CAVEAT: This module implements raw schedule logic only.
No tax payable calculation, no deferred tax, no ATAD interest limitation,
no withholding tax — those are handled by a future tax engine layer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from domain.tax.templates.inputs import TaxDepreciationRule
from domain.tax.templates.calculations import get_tax_depreciation_rate


# ── Tax Depreciation Schedule ────────────────────────────────────────────────

@dataclass(frozen=True)
class TaxDepreciationPeriod:
    """Single period in a tax depreciation schedule.

    Tracks the difference between book depreciation (for financial statements)
    and tax depreciation (for tax return) for one asset category.

    The ``non_deductible_depreciation_keur`` field captures the excess of
    book depreciation over tax depreciation in the current period
    (e.g., when an ME infrastructure asset has 5% book rate but tax law caps
    deductible depreciation at 2.5%).

    ``accumulated_non_deductible_depreciation_keur`` is the running sum of
    all non-deductible depreciation to date — a deferred tax timing difference.
    """
    period: int
    asset_category: str
    opening_tax_basis_keur: float
    book_depreciation_keur: float
    tax_depreciation_keur: float
    non_deductible_depreciation_keur: float
    closing_tax_basis_keur: float
    accumulated_non_deductible_depreciation_keur: float


@dataclass(frozen=True)
class TaxDepreciationSchedule:
    """Immutable tax depreciation schedule for one asset category.

    Produced by ``build_tax_depreciation_schedule()``.
    ``total_non_deductible_depreciation_keur`` at the last period equals the
    accumulated deferred tax timing difference for this asset.
    """
    asset_category: str
    periods: tuple[TaxDepreciationPeriod, ...]
    total_book_depreciation_keur: float
    total_tax_depreciation_keur: float
    total_non_deductible_depreciation_keur: float


def build_tax_depreciation_schedule(
    asset_cost_keur: float,
    book_depreciation_by_period: tuple[float, ...],
    rule: TaxDepreciationRule,
) -> TaxDepreciationSchedule:
    """Build a per-period tax depreciation schedule for one asset.

    Pure function: no mutation of inputs.

    Parameters
    ----------
    asset_cost_keur : float
        Original asset cost in thousands of EUR. Must be >= 0.
    book_depreciation_by_period : tuple[float, ...]
        Book depreciation charge (for financial statements) per period in kEUR.
        Must be non-negative. The sum of these should equal asset_cost_keur for
        a fully-depreciated asset under the accounting depreciation method.
    rule : TaxDepreciationRule
        Tax depreciation rule for this asset category.

    Returns
    -------
    TaxDepreciationSchedule
        Per-period breakdown of book vs tax depreciation and remaining tax basis.

    Notes
    -----
    - ``non_deductible_depreciation_keur`` = max(0, book_dep - tax_dep)
      This is the timing difference created when tax law caps deductible
      depreciation below the accounting rate (e.g., ME infrastructure 2.5% cap).
    - ``closing_tax_basis`` = max(0, opening - tax_dep) — cannot go negative.
    - ``accumulated_non_deductible_depreciation_keur`` tracks the running total
      of timing differences — future deferred tax asset recognition point.
    - ``bonus_depreciation_pct`` not applied in this primitive.
    """
    if asset_cost_keur < 0.0:
        raise ValueError(
            f"asset_cost_keur must be >= 0, got {asset_cost_keur}"
        )

    if any(d < 0.0 for d in book_depreciation_by_period):
        raise ValueError(
            f"book_depreciation_by_period must be non-negative, "
            f"got {book_depreciation_by_period}"
        )

    tax_rate = get_tax_depreciation_rate(rule)
    is_deductible = rule.deductible

    periods: list[TaxDepreciationPeriod] = []
    opening_basis = float(asset_cost_keur)
    accumulated_non_deductible = 0.0

    for period_idx, book_dep in enumerate(book_depreciation_by_period):
        opening_tax_basis_keur = opening_basis

        if not is_deductible:
            # Non-deductible: no tax deduction, all book dep is timing diff
            tax_dep = 0.0
            non_ded = float(book_dep)
            # Tax basis unchanged (no deduction taken)
            closing_basis = opening_basis
        else:
            # Tax depreciation = min(effective_rate × cost, remaining_basis, book_dep)
            # effective_rate comes from get_tax_depreciation_rate() with cap applied
            max_tax_dep = tax_rate * asset_cost_keur if tax_rate else 0.0
            raw_tax_dep = min(max_tax_dep, opening_basis, book_dep)

            # Cap at remaining opening basis (no negative basis)
            tax_dep = max(0.0, min(raw_tax_dep, opening_basis))
            tax_dep = round(tax_dep, 10)  # guard against float drift

            # Non-deductible = book dep beyond what tax allows
            non_ded = max(0.0, book_dep - tax_dep)

            # Closing tax basis
            closing_basis = max(0.0, opening_basis - tax_dep)

        accumulated_non_deductible += non_ded

        period = TaxDepreciationPeriod(
            period=period_idx,
            asset_category=rule.asset_category,
            opening_tax_basis_keur=round(opening_basis, 10),
            book_depreciation_keur=book_dep,
            tax_depreciation_keur=tax_dep,
            non_deductible_depreciation_keur=round(non_ded, 10),
            closing_tax_basis_keur=round(closing_basis, 10),
            accumulated_non_deductible_depreciation_keur=round(accumulated_non_deductible, 10),
        )
        periods.append(period)

        # Advance opening basis for next period
        opening_basis = closing_basis

    total_book = sum(p.book_depreciation_keur for p in periods)
    total_tax = sum(p.tax_depreciation_keur for p in periods)
    total_non_ded = sum(p.non_deductible_depreciation_keur for p in periods)

    return TaxDepreciationSchedule(
        asset_category=rule.asset_category,
        periods=tuple(periods),
        total_book_depreciation_keur=round(total_book, 10),
        total_tax_depreciation_keur=round(total_tax, 10),
        total_non_deductible_depreciation_keur=round(total_non_ded, 10),
    )


# ── Tax Loss Carryforward Schedule ──────────────────────────────────────────

@dataclass(frozen=True)
class TaxLossPeriod:
    """Single period in a tax loss carryforward schedule.

    Tracks how taxable income interacts with brought-forward tax losses.
    ``taxable_income_after_losses`` is the income subject to CIT after applying
    available losses. When positive, CIT is payable; when negative, a new loss
    is generated (carried forward to future periods).

    Note: This primitive does NOT compute tax payable — that requires
    ``calculate_progressive_cit()`` and is deferred to a tax engine layer.
    """
    period: int
    taxable_income_before_losses_keur: float
    opening_loss_carryforward_keur: float
    loss_used_keur: float
    new_loss_generated_keur: float
    taxable_income_after_losses_keur: float
    closing_loss_carryforward_keur: float


@dataclass(frozen=True)
class TaxLossCarryforwardSchedule:
    """Immutable tax loss carryforward schedule.

    Produced by ``build_tax_loss_carryforward_schedule()``.
    ``ending_loss_carryforward_keur`` is the pool of losses remaining at the
    end of the schedule — may be usable in future tax years depending on
    jurisdiction carryforward rules.

    WARNING: Phase 6B.3 does NOT implement vintage-based expiry (e.g., "losses
    created in year 1 expire after 5 years"). The ``loss_carryforward_years``
    parameter is accepted and stored but used only to indicate finite vs unlimited
    carryforward intent. A future phase will implement vintage tracking.
    """
    periods: tuple[TaxLossPeriod, ...]
    total_loss_used_keur: float
    total_new_loss_generated_keur: float
    ending_loss_carryforward_keur: float
    # Metadata: None = unlimited, int = intended limit (vintage expiry deferred)
    loss_carryforward_years: Optional[int]


def build_tax_loss_carryforward_schedule(
    taxable_income_by_period_keur: tuple[float, ...],
    loss_carryforward_years: Optional[int],
) -> TaxLossCarryforwardSchedule:
    """Build a per-period tax loss carryforward schedule.

    Pure function: no mutation.

    Parameters
    ----------
    taxable_income_by_period_keur : tuple[float, ...]
        Taxable income (after EBITDA adjustments, before loss utilisation) per period.
        Negative values represent tax losses; positive values represent taxable profits.
    loss_carryforward_years : int | None
        Loss carryforward limit in years.
        None = unlimited carryforward (subject to anti-abuse rules in tax engine).
        int = finite carryforward. Phase 6B.3 accepts this parameter but does NOT
        implement vintage-based expiry — losses are tracked as a single pool.

    Returns
    -------
    TaxLossCarryforwardSchedule
        Per-period breakdown of loss generation and utilisation.

    Rules
    -----
    - taxable_income_before_losses < 0 → new loss generated = abs(negative income)
    - taxable_income_before_losses > 0 → use carryforward losses up to taxable income
      - loss_used = min(opening_carryforward, taxable_income)
      - taxable_income_after_losses = taxable_income - loss_used  (never negative)
      - new_loss_generated = 0
    - closing_loss_carryforward = opening + new_loss - loss_used
    - closing cannot go negative (pool depletes but not below 0)
    - No tax payable calculation in this primitive.

    Note
    ----
    When ``loss_carryforward_years`` is an int, the implementation tracks a
    single loss pool without vintage distinction. A future phase will add
    per-vintage tracking and expiry enforcement.
    """
    periods: list[TaxLossPeriod] = []
    opening_pool = 0.0
    total_used = 0.0
    total_new = 0.0

    for period_idx, taxable_income in enumerate(taxable_income_by_period_keur):
        opening_loss_carryforward_keur = opening_pool

        if taxable_income < 0.0:
            # Negative income: generate new loss, no utilisation
            loss_used = 0.0
            new_loss = abs(taxable_income)
            taxable_after = 0.0  # income fully absorbed by loss generation
            closing_pool = opening_pool + new_loss
        else:
            # Positive income: use carryforward losses
            loss_used = min(opening_pool, taxable_income)
            new_loss = 0.0
            taxable_after = taxable_income - loss_used
            # Pool reduces by amount used (cannot go negative)
            closing_pool = max(0.0, opening_pool - loss_used)

        total_used += loss_used
        total_new += new_loss

        period = TaxLossPeriod(
            period=period_idx,
            taxable_income_before_losses_keur=taxable_income,
            opening_loss_carryforward_keur=opening_pool,
            loss_used_keur=loss_used,
            new_loss_generated_keur=new_loss,
            taxable_income_after_losses_keur=taxable_after,
            closing_loss_carryforward_keur=closing_pool,
        )
        periods.append(period)

        opening_pool = closing_pool

    return TaxLossCarryforwardSchedule(
        periods=tuple(periods),
        total_loss_used_keur=round(total_used, 10),
        total_new_loss_generated_keur=round(total_new, 10),
        ending_loss_carryforward_keur=round(opening_pool, 10),
        loss_carryforward_years=loss_carryforward_years,
    )