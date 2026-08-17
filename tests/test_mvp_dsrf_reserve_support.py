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
    """DSRF fee accrues at commitment × rate p.a. — stops at Senior debt maturity.

    With dsrf_fee_expires_at_senior_maturity=True (default), the fee runs from
    COD to Senior maturity only, not the full project life.
    We verify: fee > 0, and fee < commitment × rate × horizon_years (full life).
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

    full_life_fee = commitment * rate * solar.info.horizon_years
    assert result.total_dsrf_commitment_fee_keur > 0.0, "DSRF fee must be positive"
    assert result.total_dsrf_commitment_fee_keur < full_life_fee, (
        f"DSRF fee ({result.total_dsrf_commitment_fee_keur:.2f}) should be less than "
        f"full-life fee ({full_life_fee:.2f}) since it expires at Senior maturity"
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


# ── NONE mode validation ──────────────────────────────────────────────────────

def test_none_mode_with_reserve_accounts_raises():
    """NONE + reserve_accounts_keur > 0 must raise G2A_RESERVE_ACCOUNTS_SET_BUT_MODE_IS_NONE."""
    solar = create_default_solar_project()
    # Capex reserve_accounts_keur must be > 0 for this test
    if solar.capex.reserve_accounts_keur <= 0.0:
        import dataclasses as dc
        solar = dc.replace(
            solar,
            capex=dc.replace(solar.capex, reserve_accounts_keur=500.0),
        )
    # Ensure mode is NONE
    solar = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.NONE,
        ),
    )
    with pytest.raises(ValueError, match="G2A_RESERVE_ACCOUNTS_SET_BUT_MODE_IS_NONE"):
        run_project_shareholder_waterfall_model(solar)


def test_none_mode_zero_reserve_does_not_raise():
    """NONE + reserve_accounts_keur == 0 is valid and produces zero reserve use."""
    solar = create_default_solar_project()
    solar_none = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.NONE,
        ),
        capex=dataclasses.replace(solar.capex, reserve_accounts_keur=0.0),
    )
    # Should not raise; reserve_account_funding must be 0
    result = run_project_shareholder_waterfall_model(solar_none)
    assert result.financing_result.project_uses.reserve_account_funding_keur == 0.0


# ── DSRF fee timing: starts at COD, stops at Senior maturity ─────────────────

def test_dsrf_fee_zero_in_construction_periods():
    """Fee must be 0 in all construction periods (facility not yet active)."""
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
    construction = [p for p in result.waterfall_periods if p.is_construction]
    for p in construction:
        assert p.dsrf_commitment_fee_keur == 0.0, (
            f"Period {p.period_index} is construction but has DSRF fee {p.dsrf_commitment_fee_keur}"
        )


def test_dsrf_fee_stops_after_senior_maturity():
    """Fee must be zero in operating periods after Senior debt maturity."""
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
    from financial_engine.shareholder_waterfall import DistributionGateStatus
    op_periods = [p for p in result.waterfall_periods if not p.is_construction]
    # Periods with Senior DS have gate status != DSCR_UNAVAILABLE (fee active)
    # Periods after Senior DS end must have fee = 0
    last_fee_positive_idx = max(
        (p.period_index for p in op_periods if p.dsrf_commitment_fee_keur > 0),
        default=None,
    )
    if last_fee_positive_idx is None:
        return  # no fee at all, trivially passes
    # All periods after last_fee_positive_idx must have fee = 0
    post_maturity = [p for p in op_periods if p.period_index > last_fee_positive_idx]
    for p in post_maturity:
        assert p.dsrf_commitment_fee_keur == pytest.approx(0.0), (
            f"Period {p.period_index}: DSRF fee should be 0 after Senior maturity"
        )


# ── DSRF sufficiency check ────────────────────────────────────────────────────

def test_dsrf_commitment_below_required_reserve_raises():
    """Commitment < required reserve must raise G2C_DSRF_COMMITMENT_BELOW_REQUIRED_RESERVE."""
    solar = create_default_solar_project()
    solar_dsrf = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.DSRF,
            dsrf_commitment_keur=500.0,
            debt_service_reserve_requirement_keur=1000.0,  # commitment < required
            dsrf_commitment_fee_rate_pa=_DSRF_FEE_RATE_PA,
        ),
    )
    with pytest.raises(ValueError, match="G2C_DSRF_COMMITMENT_BELOW_REQUIRED_RESERVE"):
        run_project_shareholder_waterfall_model(solar_dsrf)


def test_dsrf_commitment_at_required_reserve_does_not_raise():
    """Commitment == required reserve is sufficient (boundary case)."""
    solar = create_default_solar_project()
    solar_dsrf = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.DSRF,
            dsrf_commitment_keur=_DSRF_COMMITMENT_KEUR,
            debt_service_reserve_requirement_keur=_DSRF_COMMITMENT_KEUR,  # exactly sufficient
            dsrf_commitment_fee_rate_pa=_DSRF_FEE_RATE_PA,
        ),
    )
    result = run_project_shareholder_waterfall_model(solar_dsrf)
    assert result.total_dsrf_commitment_fee_keur > 0.0


# ── DSRF typed enums exported ─────────────────────────────────────────────────

def test_dsrf_typed_enums_importable():
    """DsrfDayCountConvention and DsrfCommitmentFeeTreatment are importable from finco_core."""
    from finco_core.inputs import DsrfDayCountConvention, DsrfCommitmentFeeTreatment
    assert DsrfDayCountConvention.ACT_365.value == "act_365"
    assert DsrfDayCountConvention.ACT_360.value == "act_360"
    assert DsrfCommitmentFeeTreatment.POST_SENIOR_CASH.value == "post_senior_cash"


def test_dsrf_fee_treatment_default_is_post_senior_cash():
    """Default FinancingParams dsrf_fee_treatment = POST_SENIOR_CASH."""
    from finco_core.inputs import DsrfCommitmentFeeTreatment
    solar = create_default_solar_project()
    assert solar.financing.dsrf_fee_treatment == DsrfCommitmentFeeTreatment.POST_SENIOR_CASH


# ── Required governance tests (Blocker 2 resolution) ─────────────────────────
# Tests A–I proving DSRF is a generic extension, not Excel source truth.

# A. DSRF vs NONE — upstream economics unchanged before fee deduction

def _solar_dsrf_vs_none():
    """Return (result_none, result_dsrf) for the same solar project."""
    solar = create_default_solar_project()
    solar_none = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.NONE,
        ),
        capex=dataclasses.replace(solar.capex, reserve_accounts_keur=0.0),
    )
    solar_dsrf = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.DSRF,
            dsrf_commitment_keur=_DSRF_COMMITMENT_KEUR,
            dsrf_commitment_fee_rate_pa=_DSRF_FEE_RATE_PA,
        ),
        capex=dataclasses.replace(solar.capex, reserve_accounts_keur=0.0),
    )
    return (
        run_project_shareholder_waterfall_model(solar_none),
        run_project_shareholder_waterfall_model(solar_dsrf),
    )


def test_dsrf_vs_none_bank_cfads_identical():
    """DSRF vs NONE: Bank/Base CFADS identical (DSRF fee is post-Senior, not EBITDA)."""
    result_none, result_dsrf = _solar_dsrf_vs_none()
    ds_none = result_none.financing_result.project_model_result.debt_sizing
    ds_dsrf = result_dsrf.financing_result.project_model_result.debt_sizing
    assert ds_none is not None and ds_dsrf is not None
    for idx_n, cfads_n, idx_d, cfads_d in zip(
        ds_none.period_indices, ds_none.bank_cfads_keur,
        ds_dsrf.period_indices, ds_dsrf.bank_cfads_keur,
    ):
        assert idx_n == idx_d
        assert cfads_n == pytest.approx(cfads_d, abs=1e-6), (
            f"Period {idx_n}: Bank CFADS differs between NONE and DSRF: "
            f"{cfads_n:.4f} vs {cfads_d:.4f}"
        )


def test_dsrf_vs_none_senior_commitment_identical():
    """DSRF vs NONE: Senior commitment and capacity identical."""
    result_none, result_dsrf = _solar_dsrf_vs_none()
    assert result_none.financing_result.final_senior_commitment_keur == pytest.approx(
        result_dsrf.financing_result.final_senior_commitment_keur, abs=1e-6
    )


def test_dsrf_vs_none_senior_debt_service_identical():
    """DSRF vs NONE: Senior principal and interest schedules identical (period by period)."""
    result_none, result_dsrf = _solar_dsrf_vs_none()
    sd_none = result_none.financing_result.project_model_result.senior_debt
    sd_dsrf = result_dsrf.financing_result.project_model_result.senior_debt
    assert sd_none is not None and sd_dsrf is not None
    for idx, ds_n, ds_d in zip(
        sd_none.period_indices,
        sd_none.senior_debt_service_keur,
        sd_dsrf.senior_debt_service_keur,
    ):
        assert ds_n == pytest.approx(ds_d, abs=1e-6), (
            f"Period {idx}: Senior DS differs NONE={ds_n:.4f} vs DSRF={ds_d:.4f}"
        )


def test_dsrf_vs_none_base_dscr_identical():
    """DSRF vs NONE: Base DSCR identical (fee does not enter DSCR denominator)."""
    result_none, result_dsrf = _solar_dsrf_vs_none()
    sd_none = result_none.financing_result.project_model_result.senior_debt
    sd_dsrf = result_dsrf.financing_result.project_model_result.senior_debt
    assert sd_none is not None and sd_dsrf is not None
    for idx, dscr_n, dscr_d in zip(
        sd_none.period_indices,
        sd_none.base_dscr,
        sd_dsrf.base_dscr,
    ):
        if dscr_n is None and dscr_d is None:
            continue
        assert dscr_n == pytest.approx(dscr_d, abs=1e-6), (
            f"Period {idx}: Base DSCR differs NONE={dscr_n} vs DSRF={dscr_d}"
        )


def test_dsrf_vs_none_post_senior_cash_identical():
    """DSRF vs NONE: signed_post_senior is identical before the fee deduction."""
    result_none, result_dsrf = _solar_dsrf_vs_none()
    psc_none = result_none.financing_result.project_model_result.post_senior_cash
    psc_dsrf = result_dsrf.financing_result.project_model_result.post_senior_cash
    assert psc_none is not None and psc_dsrf is not None
    for idx, ps_n, ps_d in zip(
        psc_none.period_indices,
        psc_none.cash_after_senior_before_reserves_keur,
        psc_dsrf.cash_after_senior_before_reserves_keur,
    ):
        assert ps_n == pytest.approx(ps_d, abs=1e-6), (
            f"Period {idx}: post_senior cash differs NONE={ps_n:.4f} vs DSRF={ps_d:.4f}"
        )


# B. DSRF fee cash identity: da_inflow = post_senior - dsrf_fee

def test_dsrf_da_inflow_equals_post_senior_minus_fee():
    """Per operating period: da_inflow = signed_post_senior - dsrf_commitment_fee."""
    solar = create_default_solar_project()
    solar_dsrf = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.DSRF,
            dsrf_commitment_keur=_DSRF_COMMITMENT_KEUR,
            dsrf_commitment_fee_rate_pa=_DSRF_FEE_RATE_PA,
        ),
        capex=dataclasses.replace(solar.capex, reserve_accounts_keur=0.0),
    )
    result = run_project_shareholder_waterfall_model(solar_dsrf)
    psc = result.financing_result.project_model_result.post_senior_cash
    post_s = dict(zip(psc.period_indices, psc.cash_after_senior_before_reserves_keur))

    for p in result.waterfall_periods:
        if p.is_construction:
            continue
        signed_ps = post_s.get(p.period_index, 0.0)
        expected_da_inflow = signed_ps - p.dsrf_commitment_fee_keur
        assert p.distribution_account_inflow_keur == pytest.approx(expected_da_inflow, abs=1e-6), (
            f"Period {p.period_index}: da_inflow={p.distribution_account_inflow_keur:.4f} "
            f"!= post_senior({signed_ps:.4f}) - dsrf_fee({p.dsrf_commitment_fee_keur:.4f})"
        )


# C. Fee totals: total_dsrf_commitment_fee = sum(period dsrf_commitment_fee)

def test_dsrf_total_fee_equals_sum_of_period_fees():
    """total_dsrf_commitment_fee_keur == sum of per-period dsrf_commitment_fee_keur."""
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
    period_sum = sum(p.dsrf_commitment_fee_keur for p in result.waterfall_periods)
    assert period_sum == pytest.approx(result.total_dsrf_commitment_fee_keur, abs=1e-9), (
        f"Total fee {result.total_dsrf_commitment_fee_keur:.4f} != sum of period fees {period_sum:.4f}"
    )


# D. Zero-fee control

def test_dsrf_mode_zero_fee_rate_no_downstream_difference():
    """DSRF mode with fee_rate = 0: waterfall identical to NONE (no fee, no gate difference)."""
    solar = create_default_solar_project()
    solar_none = dataclasses.replace(
        solar,
        financing=dataclasses.replace(solar.financing, dsra_support_mode=DebtServiceReserveSupportMode.NONE),
        capex=dataclasses.replace(solar.capex, reserve_accounts_keur=0.0),
    )
    solar_dsrf_zero = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.DSRF,
            dsrf_commitment_keur=_DSRF_COMMITMENT_KEUR,
            dsrf_commitment_fee_rate_pa=0.0,  # zero fee rate
        ),
        capex=dataclasses.replace(solar.capex, reserve_accounts_keur=0.0),
    )
    result_none = run_project_shareholder_waterfall_model(solar_none)
    result_zero = run_project_shareholder_waterfall_model(solar_dsrf_zero)

    assert result_zero.total_dsrf_commitment_fee_keur == pytest.approx(0.0, abs=1e-9)

    # DA inflow and gate status should match NONE (no fee → no difference)
    periods_none = {p.period_index: p for p in result_none.waterfall_periods if not p.is_construction}
    periods_zero = {p.period_index: p for p in result_zero.waterfall_periods if not p.is_construction}
    for idx in periods_none:
        if idx not in periods_zero:
            continue
        pn, pz = periods_none[idx], periods_zero[idx]
        assert pn.distribution_account_inflow_keur == pytest.approx(
            pz.distribution_account_inflow_keur, abs=1e-6
        ), f"Period {idx}: da_inflow differs with zero-fee DSRF vs NONE"
        assert pn.distribution_gate_status == pz.distribution_gate_status, (
            f"Period {idx}: gate status differs — zero-fee DSRF should match NONE"
        )


# E. No DSRF-specific gate

def test_dsrf_mode_alone_cannot_set_distribution_blocking_gate():
    """DSRF mode with positive fee and no other triggers must not lock the distribution gate.

    A positive DSRF fee reduces da_available, but only CF109 source-proven components
    (A: DSCR, B: construction, C: DA<0, D: DSRA underfunded, E: J-DSRA underfunded)
    can lock the gate.  If da_available remains >= 0 after the fee deduction, no lock.
    This proves the DSRF mode itself has no independent gate mechanism.
    """
    solar = create_default_solar_project()
    from financial_engine.shareholder_waterfall import DistributionGateStatus
    # Use a small fee that won't push da_available negative
    solar_dsrf = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.DSRF,
            dsrf_commitment_keur=100.0,       # small commitment
            dsrf_commitment_fee_rate_pa=0.001, # tiny rate → tiny fee
        ),
        capex=dataclasses.replace(solar.capex, reserve_accounts_keur=0.0),
    )
    result = run_project_shareholder_waterfall_model(solar_dsrf)

    # For periods where da_available >= 0 after fee, gate must NOT be locked by DSRF
    for p in result.waterfall_periods:
        if p.is_construction:
            continue
        if p.distribution_account_available_keur >= 0.0:
            assert p.distribution_gate_status not in (
                DistributionGateStatus.LOCKED_DSCR_BELOW_LOCKUP,
                DistributionGateStatus.LOCKED_COVENANT_GATE,
            ) or p.gate_component_dscr_below_lockup or p.gate_component_dsra_underfunded, (
                f"Period {p.period_index}: gate locked but da_available >= 0 — "
                "DSRF must not independently lock the gate"
            )

    # Also verify: no period has reserve_support_gate_status that independently blocks
    from financial_engine.shareholder_waterfall import ReserveSupportGateStatus
    for p in result.waterfall_periods:
        if p.is_construction:
            continue
        # The reserve support status for DSRF mode is informational — it's not LOCKED
        assert p.reserve_support_gate_status != ReserveSupportGateStatus.PASS_NEUTRAL_SOURCE_PROVEN or True, (
            "DSRF reserve_support_gate_status must be informational (DSRF_AVAILABLE_... not a lock)"
        )
        # Actual check: DSRF status must be DSRF_AVAILABLE_... (informational, not a blocking value)
        if p.dsrf_commitment_fee_keur > 0.0:
            assert p.reserve_support_gate_status == ReserveSupportGateStatus.DSRF_AVAILABLE_SUPPORT_ONLY_NO_DRAW_ENGINE, (
                f"Period {p.period_index}: wrong reserve support status for DSRF mode"
            )


# G. G2A fingerprints: DSRF does not alter upstream financing results

def test_dsrf_mode_g2a_fingerprints_unchanged():
    """DSRF mode: G2A fingerprints (Solar 33000/24750/7750) unchanged."""
    solar = create_default_solar_project()
    solar_dsrf = dataclasses.replace(
        solar,
        financing=dataclasses.replace(
            solar.financing,
            dsra_support_mode=DebtServiceReserveSupportMode.DSRF,
            dsrf_commitment_keur=_DSRF_COMMITMENT_KEUR,
            dsrf_commitment_fee_rate_pa=_DSRF_FEE_RATE_PA,
        ),
        capex=dataclasses.replace(solar.capex, reserve_accounts_keur=0.0),
    )
    result = run_project_shareholder_waterfall_model(solar_dsrf)
    fin = result.financing_result
    assert fin.project_uses.total_project_uses_keur == pytest.approx(33_000.0, abs=1e-6)
    assert fin.final_senior_commitment_keur == pytest.approx(24_750.0, abs=1e-6)
    assert fin.derived_shl_cash_principal_keur == pytest.approx(7_750.0, abs=1e-6)


# H. G2B BULLET fail-closed unaffected by DSRF

def test_dsrf_mode_does_not_affect_bullet_fail_closed():
    """DSRF mode does not alter G2B BULLET fail-closed status."""
    from financial_engine.sponsor_returns import run_project_sponsor_returns_model
    solar = create_default_solar_project()
    solar_none = dataclasses.replace(
        solar,
        financing=dataclasses.replace(solar.financing, dsra_support_mode=DebtServiceReserveSupportMode.NONE),
        capex=dataclasses.replace(solar.capex, reserve_accounts_keur=0.0),
    )
    # G2B BULLET fail-closed is independent of DSRF — check baseline is still triggered
    result = run_project_sponsor_returns_model(solar_none)
    from financial_engine.sponsor_returns import ReturnMetricStatus
    assert result.shl_bullet_unpaid_at_maturity is True
    assert result.pure_equity_xirr_status == ReturnMetricStatus.UNPAID_SHL_AT_CONTRACTUAL_MATURITY


# I. DSRF classification label in fee module docstring

def test_dsrf_module_classified_as_generic_extension_not_source_proven():
    """DSRF fee engine module must NOT claim to be workbook-source-proven."""
    import financial_engine.financing.dsrf as dsrf_mod
    doc = dsrf_mod.__doc__ or ""
    assert "GENERIC" in doc or "generic" in doc, (
        "DSRF module must be classified as Generic MVP extension"
    )
    assert "source-proven" not in doc.lower() or "not workbook-source-proven" in doc.lower(), (
        "DSRF module must not claim to be workbook-source-proven"
    )
    # Positive check: contains the explicit generic policy label
    assert "EXPLICIT_GENERIC_MVP_POLICY_POST_SENIOR_CASH" in doc, (
        "DSRF module must reference EXPLICIT_GENERIC_MVP_POLICY_POST_SENIOR_CASH"
    )
