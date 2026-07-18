"""financial_engine.tax.loss_ledger — Annual vintage FIFO loss-carryforward ledger.

Pure function. No imports from app, finco_core or any framework.

One TaxAnnualLedgerEntry is produced per tax year.

Rules:
  - Expiry before use: at the start of each tax year, expire vintages whose
    last_usable_tax_year < current_tax_year before applying them.
  - FIFO: oldest vintage (smallest origin_tax_year) is consumed first.
  - One new vintage is created per loss-making tax year.
  - Loss generated in tax year Y has last_usable_tax_year = Y + lcf_years
    (usable in Y+1 through Y+lcf_years, i.e., five subsequent years for HR).
  - No vintage amount can go negative.
  - No income can be over-sheltered: taxable_after_lcf >= 0.
"""
from __future__ import annotations

from financial_engine.tax.models import TaxAnnualLedgerEntry, TaxLossVintage
from financial_engine.inputs import OpeningTaxLossVintageInput


def _opening_vintages_from_inputs(
    opening_inputs: tuple[OpeningTaxLossVintageInput, ...],
    loss_carryforward_years: int,
) -> tuple[TaxLossVintage, ...]:
    """Convert OpeningTaxLossVintageInput to internal TaxLossVintage.

    last_usable_tax_year = origin_tax_year + loss_carryforward_years.
    For a loss in year -3 with 5-year window: last_usable = -3 + 5 = 2.
    """
    return tuple(
        TaxLossVintage(
            origin_tax_year=v.origin_tax_year,
            last_usable_tax_year=v.origin_tax_year + loss_carryforward_years,
            amount_keur=v.amount_keur,
            source_label=v.source_label,
        )
        for v in opening_inputs
    )


def _expire_vintages(
    vintages: tuple[TaxLossVintage, ...],
    current_tax_year: int,
) -> tuple[tuple[TaxLossVintage, ...], float]:
    """Expire vintages whose last_usable_tax_year < current_tax_year.

    Returns (active_vintages, total_expired_keur).
    Expiry is applied BEFORE use (canonical rule).
    """
    active = []
    expired_keur = 0.0
    for v in vintages:
        if v.last_usable_tax_year < current_tax_year:
            expired_keur += v.amount_keur
        else:
            active.append(v)
    return tuple(active), expired_keur


def run_annual_fifo_ledger(
    taxable_income_before_lcf: tuple[float, ...],
    tax_year_indices: tuple[int, ...],
    opening_inputs: tuple[OpeningTaxLossVintageInput, ...],
    loss_carryforward_years: int,
) -> tuple[TaxAnnualLedgerEntry, ...]:
    """Run the annual FIFO loss ledger over all tax years.

    Parameters
    ----------
    taxable_income_before_lcf : one value per tax year (signed; negative = loss)
    tax_year_indices : 0-based tax year indices (same length as above)
    opening_inputs : pre-model opening loss vintages (oldest first)
    loss_carryforward_years : e.g. 5 for Croatia

    Returns
    -------
    Tuple of TaxAnnualLedgerEntry, one per tax year.
    """
    vintages = _opening_vintages_from_inputs(opening_inputs, loss_carryforward_years)
    entries: list[TaxAnnualLedgerEntry] = []

    for tax_year, taxable_before in zip(tax_year_indices, taxable_income_before_lcf):
        # Step 1: Expire before use
        vintages, expired_keur = _expire_vintages(vintages, tax_year)
        opening_loss = sum(v.amount_keur for v in vintages)

        if taxable_before <= 0.0:
            # Loss-making or break-even year: generate a new vintage, use nothing
            generated = -taxable_before if taxable_before < 0 else 0.0
            used = 0.0
            taxable_after = 0.0
            new_vintages = list(vintages)
            if generated > 1e-12:
                new_vintages.append(TaxLossVintage(
                    origin_tax_year=tax_year,
                    last_usable_tax_year=tax_year + loss_carryforward_years,
                    amount_keur=generated,
                    source_label=f"year_{tax_year}",
                ))
            vintages = tuple(new_vintages)
        else:
            # Profit year: consume oldest vintages first (FIFO)
            remaining = taxable_before
            used = 0.0
            new_vintages = []
            for v in vintages:
                if remaining <= 0.0:
                    new_vintages.append(v)
                    continue
                consume = min(v.amount_keur, remaining)
                used += consume
                remaining -= consume
                residual = v.amount_keur - consume
                if residual > 1e-12:
                    new_vintages.append(TaxLossVintage(
                        origin_tax_year=v.origin_tax_year,
                        last_usable_tax_year=v.last_usable_tax_year,
                        amount_keur=residual,
                        source_label=v.source_label,
                    ))
            taxable_after = max(0.0, remaining)
            generated = 0.0
            vintages = tuple(new_vintages)

        closing_loss = sum(v.amount_keur for v in vintages)
        entries.append(TaxAnnualLedgerEntry(
            tax_year=tax_year,
            opening_loss_keur=opening_loss,
            loss_expired_keur=expired_keur,
            loss_used_keur=used,
            loss_generated_keur=generated,
            closing_loss_keur=closing_loss,
            taxable_income_before_lcf_keur=taxable_before,
            taxable_income_after_lcf_keur=taxable_after,
        ))

    return tuple(entries)
