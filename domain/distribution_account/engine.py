"""TUHO R99/R102 input-engine helpers.

This module is intentionally standalone in C1a. It validates the R99/R102 cash
input before any runtime SHL waterfall path consumes it.
"""

from __future__ import annotations

from domain.distribution_account.result import R99InputResult


def compute_tuho_r99_input_period(
    *,
    revenue_keur: float,
    opex_keur: float,
    local_tax_keur: float,
    cash_interest_on_reserves_keur: float,
    corporate_tax_cash_keur: float,
    senior_ds_keur: float,
    dsra_release_or_funding_keur: float,
    junior_ds_keur: float,
    reserve_sweep_keur: float,
    previous_r100_carryforward_keur: float,
    year_index: int,
    senior_tenor_years: int,
    dscr: float,
    lockup_dscr: float,
    dsra_balance_keur: float,
    dsra_target_keur: float,
    jdsra_balance_keur: float,
    jdsra_target_keur: float,
) -> R99InputResult:
    """Compute one TUHO Excel-style R99/R102 SHL cash input period.

    `corporate_tax_cash_keur` is the cash tax paid in this period, not accrued
    full-year tax. Positive values reduce R69.
    """

    r69 = (
        revenue_keur
        - opex_keur
        + local_tax_keur
        + cash_interest_on_reserves_keur
        - corporate_tax_cash_keur
    )
    r84 = r69 - senior_ds_keur + dsra_release_or_funding_keur
    r98 = r84 + junior_ds_keur + reserve_sweep_keur + previous_r100_carryforward_keur

    reasons: list[str] = []
    if dscr < lockup_dscr:
        reasons.append("dscr_below_lockup")
    if year_index == 0:
        reasons.append("year_zero")
    if r98 < 0:
        reasons.append("negative_r98")
    if dsra_balance_keur < dsra_target_keur:
        reasons.append("dsra_below_target")
    if jdsra_balance_keur < jdsra_target_keur:
        reasons.append("jdsra_below_target")

    locked = year_index <= senior_tenor_years and bool(reasons)

    if locked:
        r99 = 0.0
        r100 = r98
    else:
        r99 = r98
        r100 = 0.0

    r102 = r99
    fcf_for_shl = max(0.0, r102)

    return R99InputResult(
        r69_fcf_banks_keur=r69,
        r84_fcf_junior_keur=r84,
        r98_distribution_account_keur=r98,
        r99_fcf_for_distribution_keur=r99,
        r100_carryforward_keur=r100,
        r102_fcf_for_shl_keur=r102,
        fcf_for_shl_keur=fcf_for_shl,
        locked=locked,
        lockup_reasons=tuple(reasons) if locked else (),
    )
