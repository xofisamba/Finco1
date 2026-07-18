"""financial_engine.tax.loss_ledger — Vintage FIFO loss-carryforward ledger.

Pure function. No imports from app, finco_core or any framework.

One TaxLossLedgerYear is produced per model period. The ledger:
  - Tracks one LossCarryforwardBucket per vintage
  - Applies expiry BEFORE use when expire_losses_before_use=True
  - Consumes oldest bucket first (FIFO)
  - Generates a new bucket for each period that produces a loss
"""
from __future__ import annotations

from financial_engine.tax.models import TaxLossLedgerYear, TaxLossVintage


def _apply_fifo_ledger_period(
    taxable_before: float,
    buckets: tuple[TaxLossVintage, ...],
    period_index: int,
    duration_periods: int,
    expire_before_use: bool,
) -> tuple[TaxLossLedgerYear, tuple[TaxLossVintage, ...]]:
    """Process one period through the FIFO ledger.

    Returns (period result, next_period_opening_buckets).
    """
    # Expire buckets whose life has run out
    expired_keur = 0.0
    active: list[TaxLossVintage] = []
    for b in buckets:
        if b.periods_remaining <= 0 and expire_before_use:
            expired_keur += b.amount_keur
        elif b.periods_remaining <= 0:
            expired_keur += b.amount_keur
        else:
            active.append(b)

    opening_loss = sum(b.amount_keur for b in active)
    losses_used = 0.0
    generated = 0.0
    retained: list[TaxLossVintage] = []

    if taxable_before > 0:
        remaining = taxable_before
        for b in active:
            use = min(b.amount_keur, remaining)
            losses_used += use
            remaining -= use
            residual = b.amount_keur - use
            if residual > 1e-9:
                retained.append(TaxLossVintage(
                    amount_keur=residual,
                    periods_remaining=b.periods_remaining,
                    source_period_index=b.source_period_index,
                    source_label=b.source_label,
                ))
        taxable_after = max(0.0, remaining)
    else:
        retained.extend(active)
        taxable_after = 0.0
        generated = -taxable_before  # taxable_before < 0 means a loss

    # Age surviving buckets
    aged: list[TaxLossVintage] = []
    for b in retained:
        new_remaining = b.periods_remaining - 1
        if new_remaining >= 0:
            aged.append(TaxLossVintage(
                amount_keur=b.amount_keur,
                periods_remaining=new_remaining,
                source_period_index=b.source_period_index,
                source_label=b.source_label,
            ))
        else:
            expired_keur += b.amount_keur

    # Add new vintage for this period's loss
    if generated > 1e-9:
        aged.append(TaxLossVintage(
            amount_keur=generated,
            periods_remaining=duration_periods,
            source_period_index=period_index,
            source_label=f"period_{period_index}",
        ))

    closing_loss = sum(b.amount_keur for b in aged)

    return (
        TaxLossLedgerYear(
            period_index=period_index,
            opening_loss_keur=opening_loss,
            loss_used_keur=losses_used,
            loss_generated_keur=generated,
            loss_expired_keur=expired_keur,
            closing_loss_keur=closing_loss,
            taxable_income_before_losses_keur=taxable_before,
            taxable_profit_after_losses_keur=taxable_after,
        ),
        tuple(aged),
    )


def run_fifo_loss_ledger(
    taxable_income_before_losses: tuple[float, ...],
    opening_vintages: tuple[TaxLossVintage, ...],
    loss_carryforward_years: int,
    periods_per_tax_year: int,
    expire_losses_before_use: bool,
) -> tuple[TaxLossLedgerYear, ...]:
    """Run the full FIFO loss ledger over all model periods.

    Parameters
    ----------
    taxable_income_before_losses : one value per model period (signed; negative = loss)
    opening_vintages : pre-model opening loss vintages (oldest first)
    loss_carryforward_years : e.g. 5 for Croatia
    periods_per_tax_year : e.g. 2 for semi-annual
    expire_losses_before_use : True = Excel-compatible expiry-before-use mode
    """
    duration_periods = loss_carryforward_years * periods_per_tax_year
    buckets = opening_vintages
    period_results: list[TaxLossLedgerYear] = []

    for i, taxable_before in enumerate(taxable_income_before_losses):
        ledger_year, buckets = _apply_fifo_ledger_period(
            taxable_before=taxable_before,
            buckets=buckets,
            period_index=i,
            duration_periods=duration_periods,
            expire_before_use=expire_losses_before_use,
        )
        period_results.append(ledger_year)

    return tuple(period_results)
