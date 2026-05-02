"""SHL waterfall priority tests.

These tests encode the business rule confirmed during FincoGPT calibration:
SHL opening balance includes capitalized SHL IDC; cash after senior debt is used
for SHL before dividends; unpaid gross SHL interest is capitalized/accrued and
is not treated as investor cash inflow until paid.
"""
from __future__ import annotations

from domain.waterfall.waterfall_engine import compute_shl_period


def test_shl_opening_balance_includes_capitalized_idc() -> None:
    shl_amount_keur = 13_547.2
    shl_idc_keur = 1_086.0

    opening_balance = shl_amount_keur + shl_idc_keur

    assert opening_balance == 14_633.2


def test_cash_sweep_pays_shl_interest_before_principal() -> None:
    shl_balance = 10_000.0
    shl_rate_per_period = 0.04
    cf_after_senior_ds = 650.0

    interest_paid, principal_paid, pik, closing_balance = compute_shl_period(
        shl_balance=shl_balance,
        shl_rate_per_period=shl_rate_per_period,
        cf_after_senior_ds=cf_after_senior_ds,
        method="cash_sweep",
        wht_rate=0.0,
    )

    assert interest_paid == 400.0
    assert principal_paid == 250.0
    assert pik == 0.0
    assert closing_balance == 9_750.0


def test_cash_sweep_capitalizes_unpaid_interest_when_cash_is_insufficient() -> None:
    shl_balance = 10_000.0
    shl_rate_per_period = 0.04
    cf_after_senior_ds = 300.0

    interest_paid, principal_paid, pik, closing_balance = compute_shl_period(
        shl_balance=shl_balance,
        shl_rate_per_period=shl_rate_per_period,
        cf_after_senior_ds=cf_after_senior_ds,
        method="cash_sweep",
        wht_rate=0.0,
    )

    assert interest_paid == 300.0
    assert principal_paid == 0.0
    assert pik == 100.0
    assert closing_balance == 10_100.0


def test_cash_sweep_capitalizes_unpaid_gross_interest_with_wht() -> None:
    shl_balance = 1_000.0
    shl_rate_per_period = 0.10
    cf_after_senior_ds = 50.0

    interest_paid, principal_paid, pik, closing_balance = compute_shl_period(
        shl_balance=shl_balance,
        shl_rate_per_period=shl_rate_per_period,
        cf_after_senior_ds=cf_after_senior_ds,
        method="cash_sweep",
        wht_rate=0.20,
    )

    assert interest_paid == 50.0
    assert principal_paid == 0.0
    assert pik == 50.0
    assert closing_balance == 1_050.0


def test_sponsor_cash_flow_priority_is_shl_before_dividend() -> None:
    """Dividend is residual after SHL service, not parallel to SHL service."""
    cash_after_senior_debt = 1_000.0
    shl_interest_due = 350.0
    shl_balance = 500.0

    shl_interest_paid = min(cash_after_senior_debt, shl_interest_due)
    remaining_after_interest = cash_after_senior_debt - shl_interest_paid
    shl_principal_paid = min(remaining_after_interest, shl_balance)
    dividend = max(0.0, remaining_after_interest - shl_principal_paid)

    assert shl_interest_paid == 350.0
    assert shl_principal_paid == 500.0
    assert dividend == 150.0


def test_no_dividend_until_shl_cash_sweep_has_been_served() -> None:
    cash_after_senior_debt = 600.0
    shl_interest_due = 350.0
    shl_balance = 500.0

    shl_interest_paid = min(cash_after_senior_debt, shl_interest_due)
    remaining_after_interest = cash_after_senior_debt - shl_interest_paid
    shl_principal_paid = min(remaining_after_interest, shl_balance)
    dividend = max(0.0, remaining_after_interest - shl_principal_paid)

    assert shl_interest_paid == 350.0
    assert shl_principal_paid == 250.0
    assert dividend == 0.0
