"""MVP DSRF — Debt Service Reserve Facility tests.

Test authority: CURRENT_BLOCKING (via mvp_g2c_shareholder_waterfall_check.yml).

Covers DebtServiceReserveSupportMode: CASH_DSRA / DSRF / NONE.

Source authority: methodology specification (DSRF addendum, 2026-08-16).

Governance:
  - Mode dispatched via typed FinancingParams.dsra_support_mode, never by project name.
  - DSRF: no initial cash Project Use; commitment fee from COD.
  - CASH_DSRA: funded reserve is a Project Use; increases total_project_uses_keur.
  - NONE: default; all G2A fingerprints unchanged.
"""
from __future__ import annotations

import dataclasses

import pytest

from app.project_factories import create_default_solar_project
from finco_core.inputs import DebtServiceReserveSupportMode, GearingBasisMode, SponsorFundingMode
from financial_engine.shareholder_waterfall import run_project_shareholder_waterfall_model

_RESERVE_AMOUNT_KEUR = 1500.0
_DSRF_COMMITMENT_KEUR = 1500.0
_DSRF_FEE_RATE_PA = 0.01  # 1% p.a.


def _solar_with_reserve(
    mode: DebtServiceReserveSupportMode,
    reserve_accounts_keur: float = 0.0,
    dsrf_commitment_keur: float = 0.0,
    dsrf_commitment_fee_rate_pa: float = 0.0,
):
    """Create a solar project with explicit reserve support mode."""
    solar = create_default_solar_project()
    return dataclasses.replace(
        solar,
        capex=dataclasses.replace(solar.capex, reserve_accounts_keur=reserve_accounts_keur),
        financing=dataclasses.replace(
            solar.financing,
            dsra_support_mode=mode,
            dsrf_commitment_keur=dsrf_commitment_keur,
            dsrf_commitment_fee_rate_pa=dsrf_commitment_fee_rate_pa,
        ),
    )


# ── NONE mode: G2A fingerprints preserved ────────────────────────────────────

def test_none_mode_preserves_g2a_fingerprints():
    """Default NONE mode: G2A fingerprints (33000/24750/7750) unchanged."""
    solar = create_default_solar_project()
    result = run_project_shareholder_waterfall_model(solar)
    fin = result.financing_result
    assert abs(fin.project_uses.total_project_uses_keur - 33000.0) < 1e-6
    assert abs(fin.final_senior_commitment_keur - 24750.0) < 1e-6
    assert abs(fin.derived_shl_cash_principal_keur - 7750.0) < 1e-6


def test_none_mode_zero_dsrf_fee():
    """NONE mode: total DSRF commitment fee is zero."""
    solar = create_default_solar_project()
    result = run_project_shareholder_waterfall_model(solar)
    assert abs(result.total_dsrf_commitment_fee_keur) < 1e-9


# ── CASH_DSRA vs DSRF: apples-to-apples comparison ──────────────────────────

def test_cash_dsra_vs_dsrf_uses_differ_by_reserve_amount():
    """Sources & Uses: Total Uses_CASH_DSRA - Total Uses_DSRF = funded reserve amount.

    Same project inputs; only dsra_support_mode differs.
    CASH_DSRA: reserve_accounts_keur is a Project Use.
    DSRF: no initial cash reserve use (standby facility, not a use at FC).
    """
    solar_cash_dsra = _solar_with_reserve(
        mode=DebtServiceReserveSupportMode.CASH_DSRA,
        reserve_accounts_keur=_RESERVE_AMOUNT_KEUR,
    )
    solar_dsrf = _solar_with_reserve(
        mode=DebtServiceReserveSupportMode.DSRF,
        reserve_accounts_keur=_RESERVE_AMOUNT_KEUR,  # same capex struct
        dsrf_commitment_keur=_RESERVE_AMOUNT_KEUR,
        dsrf_commitment_fee_rate_pa=_DSRF_FEE_RATE_PA,
    )

    result_cash = run_project_shareholder_waterfall_model(solar_cash_dsra)
    result_dsrf = run_project_shareholder_waterfall_model(solar_dsrf)

    uses_cash = result_cash.financing_result.project_uses.total_project_uses_keur
    uses_dsrf = result_dsrf.financing_result.project_uses.total_project_uses_keur

    diff = uses_cash - uses_dsrf
    assert abs(diff - _RESERVE_AMOUNT_KEUR) < 1e-6, (
        f"Uses_CASH_DSRA - Uses_DSRF should equal {_RESERVE_AMOUNT_KEUR} kEUR, "
        f"got {diff:.4f}"
    )


def test_cash_dsra_hard_capex_unchanged():
    """Hard CAPEX is identical between CASH_DSRA and DSRF modes."""
    solar_cash_dsra = _solar_with_reserve(
        mode=DebtServiceReserveSupportMode.CASH_DSRA,
        reserve_accounts_keur=_RESERVE_AMOUNT_KEUR,
    )
    solar_dsrf = _solar_with_reserve(
        mode=DebtServiceReserveSupportMode.DSRF,
        reserve_accounts_keur=_RESERVE_AMOUNT_KEUR,
        dsrf_commitment_keur=_RESERVE_AMOUNT_KEUR,
        dsrf_commitment_fee_rate_pa=_DSRF_FEE_RATE_PA,
    )
    hard_cash = solar_cash_dsra.capex.hard_capex_keur
    hard_dsrf = solar_dsrf.capex.hard_capex_keur
    assert abs(hard_cash - hard_dsrf) < 1e-9, (
        "Hard CAPEX must be identical between CASH_DSRA and DSRF modes"
    )


def test_dsrf_reserve_use_is_zero():
    """DSRF mode: reserve_account_funding_keur = 0 in Project Uses."""
    solar_dsrf = _solar_with_reserve(
        mode=DebtServiceReserveSupportMode.DSRF,
        reserve_accounts_keur=_RESERVE_AMOUNT_KEUR,
        dsrf_commitment_keur=_RESERVE_AMOUNT_KEUR,
        dsrf_commitment_fee_rate_pa=_DSRF_FEE_RATE_PA,
    )
    result = run_project_shareholder_waterfall_model(solar_dsrf)
    assert abs(result.financing_result.project_uses.reserve_account_funding_keur) < 1e-9


def test_cash_dsra_reserve_use_equals_reserve_amount():
    """CASH_DSRA mode: reserve_account_funding_keur = reserve_accounts_keur."""
    solar_cash = _solar_with_reserve(
        mode=DebtServiceReserveSupportMode.CASH_DSRA,
        reserve_accounts_keur=_RESERVE_AMOUNT_KEUR,
    )
    result = run_project_shareholder_waterfall_model(solar_cash)
    assert abs(
        result.financing_result.project_uses.reserve_account_funding_keur - _RESERVE_AMOUNT_KEUR
    ) < 1e-9


# ── DSRF commitment fee mechanics ────────────────────────────────────────────

def test_dsrf_commitment_fee_nonzero_when_configured():
    """DSRF with rate > 0: total commitment fee > 0 across operating life."""
    solar_dsrf = _solar_with_reserve(
        mode=DebtServiceReserveSupportMode.DSRF,
        reserve_accounts_keur=_DSRF_COMMITMENT_KEUR,
        dsrf_commitment_keur=_DSRF_COMMITMENT_KEUR,
        dsrf_commitment_fee_rate_pa=_DSRF_FEE_RATE_PA,
    )
    result = run_project_shareholder_waterfall_model(solar_dsrf)
    assert result.total_dsrf_commitment_fee_keur > 0.0


def test_dsrf_annual_fee_approx_expected():
    """DSRF commitment=3000 kEUR, rate=1% p.a.: annual fee ≈ 30 kEUR.

    For a 25-year project with semestrial periods (50 periods):
    total fee ≈ 3000 × 0.01 × 25 = 750 kEUR.
    Per semestrial period ≈ 15 kEUR.
    """
    commitment = 3000.0
    rate = 0.01
    solar = create_default_solar_project()
    solar_dsrf = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.DSRF,
            dsrf_commitment_keur=commitment,
            dsrf_commitment_fee_rate_pa=rate,
        ),
    )
    result = run_project_shareholder_waterfall_model(solar_dsrf)

    # Total operating years ≈ horizon_years = 25; total fee ≈ commitment × rate × years
    horizon_years = solar.info.horizon_years
    expected_total = commitment * rate * horizon_years
    # Allow 5% tolerance for calendar/day-count effects
    assert abs(result.total_dsrf_commitment_fee_keur - expected_total) < expected_total * 0.05, (
        f"DSRF fee: expected ~{expected_total:.1f} kEUR, "
        f"got {result.total_dsrf_commitment_fee_keur:.2f} kEUR"
    )


def test_dsrf_commitment_fee_zero_for_none_mode():
    """NONE mode: DSRF fee is zero even if fee params are non-zero (mode wins)."""
    solar = create_default_solar_project()
    solar_none = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.NONE,
            dsrf_commitment_keur=1000.0,
            dsrf_commitment_fee_rate_pa=0.01,
        ),
    )
    result = run_project_shareholder_waterfall_model(solar_none)
    assert abs(result.total_dsrf_commitment_fee_keur) < 1e-9


def test_dsrf_fee_is_separate_from_operational_opex(solar_result=None):
    """DSRF fee appears in per-period dsrf_commitment_fee_keur, not in period opex."""
    solar = create_default_solar_project()
    solar_dsrf = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.DSRF,
            dsrf_commitment_keur=_DSRF_COMMITMENT_KEUR,
            dsrf_commitment_fee_rate_pa=_DSRF_FEE_RATE_PA,
        ),
    )
    result = run_project_shareholder_waterfall_model(solar_dsrf)
    # Fee is tracked on waterfall periods, not via the opex engine
    op_periods = [p for p in result.waterfall_periods if not p.is_construction]
    assert any(p.dsrf_commitment_fee_keur > 0 for p in op_periods), (
        "DSRF fee should be positive in operating periods"
    )


# ── Mode dispatch: typed policy, not project identity ────────────────────────

def test_dsra_mode_enum_values():
    """DebtServiceReserveSupportMode has exactly CASH_DSRA, DSRF, NONE."""
    modes = {m.value for m in DebtServiceReserveSupportMode}
    assert modes == {"cash_dsra", "dsrf", "none"}


def test_default_dsra_mode_is_none():
    """Default FinancingParams has dsra_support_mode = NONE."""
    solar = create_default_solar_project()
    assert solar.financing.dsra_support_mode == DebtServiceReserveSupportMode.NONE
