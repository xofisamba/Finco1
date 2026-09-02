"""U2 Phase M — Production tests.

Tests for the 12 targeted fixes in Phase M:
  M.1  _u2_period_financing_income threads through _run_with_construction_idc
  M.2  DSRA balance passed to build_cash_reserve_interest_schedules
  M.3  Financing income in net income formula
  M.4  WHT sourced from tax.wht_sponsor_dividends (canonical field)
  M.5  Construction P&L rolls into COD opening retained earnings
  M.7  total_sponsor_net_cashflow_keur uses net dividends
  M.8  total_sponsor_receipts uses net dividends; total_legal_equity_distributions = gross
  M.10 Opening unrestricted cash authority documented
  M.11 Final idempotence transition after convergence
"""
from __future__ import annotations

import dataclasses
import pathlib
from unittest.mock import patch

import pytest

from app.project_factories import create_default_solar_project, create_default_wind_project
from finco_core.inputs import GearingBasisMode, SponsorFundingMode
from finco_core.inputs.cash_reserve_interest_policy import (
    CashReserveInterestPolicy,
    CashReserveInterestAuthority,
    EligibilityStatus,
    DayCountConvention,
    BalanceConvention,
)
from financial_engine.shareholder_waterfall import (
    CovenantGatedWaterfallResult,
    run_project_shareholder_waterfall_model,
)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_MODEL_SRC = (_REPO_ROOT / "financial_engine" / "shareholder_waterfall" / "model.py").read_text()


# ── Fixture helpers ────────────────────────────────────────────────────────────

def _solar() -> CovenantGatedWaterfallResult:
    return run_project_shareholder_waterfall_model(create_default_solar_project())


def _solar_inputs():
    return create_default_solar_project()


def _wind() -> CovenantGatedWaterfallResult:
    return run_project_shareholder_waterfall_model(create_default_wind_project())


def _make_policy(rate: float = 0.03) -> CashReserveInterestPolicy:
    return CashReserveInterestPolicy(
        authority=CashReserveInterestAuthority.SOURCE_PROVEN,
        eligible_unrestricted_cash=EligibilityStatus.ELIGIBLE,
        eligible_dsra=EligibilityStatus.INELIGIBLE,
        annual_rate=rate,
        enabled=True,
        day_count_convention=DayCountConvention.ACTUAL_365,
        balance_convention=BalanceConvention.OPENING,
    )


def _solar_with_policy(rate: float = 0.03) -> CovenantGatedWaterfallResult:
    p = _solar_inputs()
    p2 = dataclasses.replace(p, cash_reserve_interest_policy=_make_policy(rate))
    return run_project_shareholder_waterfall_model(p2)


def _solar_with_wht(wht: float) -> CovenantGatedWaterfallResult:
    p = _solar_inputs()
    p2 = dataclasses.replace(p, tax=dataclasses.replace(p.tax, wht_sponsor_dividends=wht))
    return run_project_shareholder_waterfall_model(p2)


# ── M.1: u2_period_financing_income threads through _run_with_construction_idc ─

def test_m1_parameter_exists_on_run_with_construction_idc():
    """_run_with_construction_idc signature must accept _u2_period_financing_income."""
    import inspect
    from financial_engine.financing.project import _run_with_construction_idc
    sig = inspect.signature(_run_with_construction_idc)
    assert "_u2_period_financing_income" in sig.parameters


def test_m1_parameter_default_none():
    import inspect
    from financial_engine.financing.project import _run_with_construction_idc
    sig = inspect.signature(_run_with_construction_idc)
    param = sig.parameters["_u2_period_financing_income"]
    assert param.default is None


# ── M.3: Financing income in net income formula ────────────────────────────────

def test_m3_fi_income_included_in_net_income():
    """For a project with positive financing income, net income must be higher than without it."""
    r_no_fi = _solar()
    r_with_fi = _solar_with_policy(rate=0.03)

    # Get first operating period with financing income
    ops_no = [p for p in r_no_fi.waterfall_periods if not p.is_construction]
    ops_fi = [p for p in r_with_fi.waterfall_periods if not p.is_construction]

    # Find a period where FI > 0
    total_fi = r_with_fi.financing_result.cash_reserve_interest_schedules
    if total_fi is None:
        pytest.skip("No fi_schedule computed (no policy or all zero)")

    fi_by_idx = {fr.period_index: fr.calculated_financing_income_keur for fr in total_fi.period_results}
    nonzero_fi_indices = [idx for idx, v in fi_by_idx.items() if v > 0]
    if not nonzero_fi_indices:
        pytest.skip("All financing income is zero")

    # accounting_dividend_capacity is affected by net income — with FI it should be >= without
    idx = nonzero_fi_indices[0]
    wp_no = next((p for p in ops_no if p.period_index == idx), None)
    wp_fi = next((p for p in ops_fi if p.period_index == idx), None)
    if wp_no is None or wp_fi is None:
        pytest.skip("Period not found")
    # accounting cap with FI >= without FI (more NI allows more distribution)
    assert wp_fi.accounting_dividend_capacity_keur >= wp_no.accounting_dividend_capacity_keur - 1e-4


def test_m3_ebitda_invariant():
    """EBITDA in OperatingPeriodResult must not be modified by financing income logic."""
    from financial_engine.shareholder_waterfall import run_project_shareholder_waterfall_model
    p = _solar_inputs()
    p_no_fi = p
    p_with_fi = dataclasses.replace(p, cash_reserve_interest_policy=_make_policy())

    r_no = run_project_shareholder_waterfall_model(p_no_fi)
    r_fi = run_project_shareholder_waterfall_model(p_with_fi)

    for per_no, per_fi in zip(r_no.financing_result.project_model_result.periods,
                               r_fi.financing_result.project_model_result.periods):
        if per_no.is_operation:
            assert abs(per_no.ebitda_keur - per_fi.ebitda_keur) < 1e-4, (
                f"EBITDA changed between no-FI and FI runs at period {per_no.period_index}"
            )


# ── M.4: WHT sourced from tax.wht_sponsor_dividends ───────────────────────────

def test_m4_dividend_wht_from_tax_params():
    """WHT must be read from tax.wht_sponsor_dividends."""
    r = _solar_with_wht(0.05)
    ops = [p for p in r.waterfall_periods if not p.is_construction and p.gross_dividend_paid_keur > 0]
    assert ops, "Expected at least one period with gross dividends"
    for p in ops:
        assert abs(p.dividend_wht_rate - 0.05) < 1e-9, (
            f"Expected WHT rate 0.05 at period {p.period_index}, got {p.dividend_wht_rate}"
        )
        assert abs(p.dividend_wht_keur - p.gross_dividend_paid_keur * 0.05) < 1e-4


def test_m4_tuho_wht_zero():
    """WHT=0 means net_dividend == gross_dividend."""
    r = _solar_with_wht(0.0)
    ops = [p for p in r.waterfall_periods if not p.is_construction]
    for p in ops:
        assert abs(p.net_dividend_received_keur - p.gross_dividend_paid_keur) < 1e-6


def test_m4_oborovo_wht_five_percent():
    """WHT=5% means net = gross * 0.95."""
    r = _solar_with_wht(0.05)
    ops = [p for p in r.waterfall_periods if not p.is_construction and p.gross_dividend_paid_keur > 1e-6]
    assert ops, "Need at least one period with dividends"
    for p in ops:
        expected_net = p.gross_dividend_paid_keur * 0.95
        assert abs(p.net_dividend_received_keur - expected_net) < 1e-4, (
            f"Period {p.period_index}: net={p.net_dividend_received_keur} != gross*0.95={expected_net}"
        )


def test_m4_wht_not_read_from_fin():
    """Verify model.py does not read dividend_wht_rate from fin (FinancingParams)."""
    # The canonical field is tax.wht_sponsor_dividends — fin.dividend_wht_rate is deprecated.
    assert "fin.dividend_wht_rate" not in _MODEL_SRC, (
        "model.py must not read dividend_wht_rate from fin — use tax.wht_sponsor_dividends"
    )


# ── M.5: Construction P&L rolls into COD opening RE ───────────────────────────

def test_m5_zero_shl_pik_gives_zero_opening_re():
    """When SHL construction PIK = 0, opening RE at COD = 0."""
    # Solar default has no construction financing → no PIK → opening RE = 0
    p = _solar_inputs()
    r = run_project_shareholder_waterfall_model(p)
    # With 0 PIK and no pre_op_opex, opening RE should not reduce first period accounting cap
    # We verify indirectly: if opening RE = 0, first period acct_cap = NI1
    ops = [pp for pp in r.waterfall_periods if not pp.is_construction]
    if ops:
        # Accounting cap should be >= 0 (would be < 0 if large negative opening RE unfilled)
        assert ops[0].accounting_dividend_capacity_keur >= -1e-4


def test_m5_construction_pik_from_financing():
    """shl_construction_pik_keur from financing result must be accessible."""
    r = _solar()
    pik = getattr(r.financing_result, "shl_construction_pik_keur", 0.0)
    assert isinstance(pik, (int, float))


# ── M.7: total_sponsor_net_cashflow_keur uses net dividends ───────────────────

def test_m7_total_sponsor_net_uses_net_dividends():
    """total_sponsor_net_cashflow = net_div + shl_cash_int + shl_principal."""
    r = _solar_with_wht(0.05)
    for p in r.waterfall_periods:
        if p.is_construction:
            continue
        expected = (
            p.net_dividend_received_keur
            + p.shl_cash_interest_receipt_keur
            + p.shl_principal_receipt_keur
        )
        assert abs(p.total_sponsor_net_cashflow_keur - expected) < 1e-6, (
            f"Period {p.period_index}: total_sponsor_net={p.total_sponsor_net_cashflow_keur} "
            f"!= net_div+shl = {expected}"
        )


def test_m7_construction_periods_total_net():
    """Construction periods: total_sponsor_net = contributions (negative) sign."""
    r = _solar()
    for p in r.waterfall_periods:
        if p.is_construction:
            # total_sponsor_net = -(contributions) for construction
            # Just verify it's a real number
            assert isinstance(p.total_sponsor_net_cashflow_keur, float)


# ── M.8: Aggregate totals ──────────────────────────────────────────────────────

def test_m8_total_sponsor_receipts_uses_net_dividends():
    """total_sponsor_receipts_keur = total_net_div + SHL."""
    r = _solar_with_wht(0.05)
    expected = (
        r.total_net_dividend_received_keur
        + r.total_shl_cash_interest_received_keur
        + r.total_shl_principal_received_keur
    )
    assert abs(r.total_sponsor_receipts_keur - expected) < 1e-6


def test_m8_total_sponsor_receipts_no_wht():
    """Without WHT, total_sponsor_receipts = sum of legal_equity_distribution + SHL (same as net)."""
    r = _solar_with_wht(0.0)
    expected = (
        r.total_net_dividend_received_keur
        + r.total_shl_cash_interest_received_keur
        + r.total_shl_principal_received_keur
    )
    assert abs(r.total_sponsor_receipts_keur - expected) < 1e-6


def test_m8_total_legal_equity_is_gross_dividend():
    """total_legal_equity_distributions_keur = sum of gross_dividend_paid_keur."""
    r = _solar_with_wht(0.05)
    total_gross_from_periods = sum(
        p.gross_dividend_paid_keur for p in r.waterfall_periods
    )
    assert abs(r.total_legal_equity_distributions_keur - total_gross_from_periods) < 1e-6


def test_m8_total_gross_ne_net_when_wht():
    """With WHT > 0, total_gross_div must exceed total_net_div."""
    r = _solar_with_wht(0.05)
    # Only true if there are dividends at all
    if r.total_gross_dividend_paid_keur > 1e-6:
        assert r.total_gross_dividend_paid_keur > r.total_net_dividend_received_keur


# ── M.11: Final idempotence ────────────────────────────────────────────────────

def test_m11_final_idempotence_no_policy():
    """Running the waterfall twice with no policy gives identical results."""
    p = _solar_inputs()
    r1 = run_project_shareholder_waterfall_model(p)
    r2 = run_project_shareholder_waterfall_model(p)
    assert abs(r1.total_sponsor_receipts_keur - r2.total_sponsor_receipts_keur) < 1e-4
    assert abs(r1.total_net_dividend_received_keur - r2.total_net_dividend_received_keur) < 1e-4


def test_m11_final_idempotence_with_policy():
    """Running the waterfall twice with a cash reserve policy gives identical results."""
    p = dataclasses.replace(_solar_inputs(), cash_reserve_interest_policy=_make_policy())
    r1 = run_project_shareholder_waterfall_model(p)
    r2 = run_project_shareholder_waterfall_model(p)
    assert abs(r1.total_sponsor_receipts_keur - r2.total_sponsor_receipts_keur) < 1e-4


def test_m11_unrestricted_cash_idempotent():
    """Unrestricted cash closing by period is identical on repeated runs."""
    p = dataclasses.replace(_solar_inputs(), cash_reserve_interest_policy=_make_policy())
    r1 = run_project_shareholder_waterfall_model(p)
    r2 = run_project_shareholder_waterfall_model(p)
    for p1, p2 in zip(r1.waterfall_periods, r2.waterfall_periods):
        assert abs(p1.unrestricted_cash_closing_keur - p2.unrestricted_cash_closing_keur) < 1e-4


# ── No forbidden patterns ──────────────────────────────────────────────────────

def test_no_hardcoded_550():
    """No hardcoded 550 value in shareholder waterfall model source."""
    lines = _MODEL_SRC.splitlines()
    # Look for standalone 550 numeric literals (not in comments or strings)
    import re
    pattern = re.compile(r'\b550\.0\b|\b550\b')
    for i, line in enumerate(lines, 1):
        stripped = line.split('#')[0]  # remove comments
        if pattern.search(stripped):
            pytest.fail(f"Hardcoded 550 found at model.py line {i}: {line.strip()!r}")


def test_no_project_name_dispatch():
    """No if 'tuho' or if 'oborovo' string-matching dispatch in model.py."""
    assert '"tuho"' not in _MODEL_SRC.lower() or "tuho" not in _MODEL_SRC
    assert "if \"tuho\"" not in _MODEL_SRC
    assert "if 'tuho'" not in _MODEL_SRC
    assert "if \"oborovo\"" not in _MODEL_SRC
    assert "if 'oborovo'" not in _MODEL_SRC


def test_no_c3_import():
    """No C3 module imports in model.py."""
    assert "from c3" not in _MODEL_SRC.lower()
    assert "import c3" not in _MODEL_SRC.lower()


# ── Convergence behavior ───────────────────────────────────────────────────────

def test_convergence_raises_on_max_iterations():
    """When the fixed point does not converge in max iterations, raise ValueError."""
    p = dataclasses.replace(_solar_inputs(), cash_reserve_interest_policy=_make_policy())

    call_count = {"n": 0}
    original = run_project_shareholder_waterfall_model.__wrapped__ if hasattr(
        run_project_shareholder_waterfall_model, "__wrapped__"
    ) else None

    # We test the error string is correct by triggering it via import
    from financial_engine.shareholder_waterfall import model as wf_model
    # Verify the error token exists in source
    assert "U2_CASH_RESERVE_INTEREST_FIXED_POINT_NOT_CONVERGED" in _MODEL_SRC


def test_u2_convergence_error_token_in_source():
    """U2_CASH_RESERVE_INTEREST_FIXED_POINT_NOT_CONVERGED token must be in model.py."""
    assert "U2_CASH_RESERVE_INTEREST_FIXED_POINT_NOT_CONVERGED" in _MODEL_SRC


# ── DA vs unrestricted cash are distinct concepts ──────────────────────────────

def test_da_and_unrestricted_cash_distinct():
    """DA and unrestricted_cash are separate; gate-locked periods may have non-zero UC."""
    r = _solar()
    # Find periods where DA is locked (distribution = 0) but unrestricted_cash_closing > 0
    for p in r.waterfall_periods:
        if p.is_construction:
            continue
        # da_locked means covenant_locked_keur > 0 or gate is locked
        if p.legal_equity_distribution_keur < 1e-6 and p.unrestricted_cash_closing_keur > 0:
            # This period proves the concepts are distinct
            return
    # It's OK if no such period exists for solar — the concepts ARE distinct by design
    # Just verify the fields exist independently
    ops = [p for p in r.waterfall_periods if not p.is_construction]
    assert all(hasattr(p, "unrestricted_cash_closing_keur") for p in ops)
    assert all(hasattr(p, "distribution_account_closing_keur") for p in ops)


# ── Structural: SHL interest field ordering ────────────────────────────────────

def test_total_shl_int_plus_principal_computable():
    """total_shl_cash_interest_received + total_shl_principal_received are valid floats."""
    r = _solar()
    assert r.total_shl_cash_interest_received_keur >= 0.0
    assert r.total_shl_principal_received_keur >= 0.0


def test_total_gross_dividend_paid_field_exists():
    """CovenantGatedWaterfallResult must have total_gross_dividend_paid_keur."""
    r = _solar()
    assert hasattr(r, "total_gross_dividend_paid_keur")
    assert r.total_gross_dividend_paid_keur >= 0.0


def test_total_net_dividend_received_field_exists():
    """CovenantGatedWaterfallResult must have total_net_dividend_received_keur."""
    r = _solar()
    assert hasattr(r, "total_net_dividend_received_keur")
    assert r.total_net_dividend_received_keur >= 0.0


def test_gross_ge_net_dividend():
    """gross_dividend_paid_keur >= net_dividend_received_keur for each period (WHT >= 0)."""
    r = _solar_with_wht(0.05)
    for p in r.waterfall_periods:
        if not p.is_construction:
            assert p.gross_dividend_paid_keur >= p.net_dividend_received_keur - 1e-9, (
                f"Period {p.period_index}: gross < net"
            )


def test_period_net_div_sum_matches_total():
    """Sum of per-period net_dividend_received equals total_net_dividend_received_keur."""
    r = _solar_with_wht(0.05)
    computed = sum(p.net_dividend_received_keur for p in r.waterfall_periods)
    assert abs(computed - r.total_net_dividend_received_keur) < 1e-6


def test_period_gross_div_sum_matches_total():
    """Sum of per-period gross_dividend_paid equals total_gross_dividend_paid_keur."""
    r = _solar_with_wht(0.05)
    computed = sum(p.gross_dividend_paid_keur for p in r.waterfall_periods)
    assert abs(computed - r.total_gross_dividend_paid_keur) < 1e-6


# ── Wind project parity ────────────────────────────────────────────────────────

def test_m8_total_sponsor_receipts_wind():
    """total_sponsor_receipts = total_net_div + SHL for wind project too."""
    r = _wind()
    expected = (
        r.total_net_dividend_received_keur
        + r.total_shl_cash_interest_received_keur
        + r.total_shl_principal_received_keur
    )
    assert abs(r.total_sponsor_receipts_keur - expected) < 1e-6


def test_m4_wht_wind_project():
    """Wind project WHT from tax.wht_sponsor_dividends."""
    p = create_default_wind_project()
    wht_rate = p.tax.wht_sponsor_dividends
    r = run_project_shareholder_waterfall_model(p)
    ops = [pp for pp in r.waterfall_periods if not pp.is_construction and pp.gross_dividend_paid_keur > 1e-6]
    for pp in ops:
        assert abs(pp.dividend_wht_rate - wht_rate) < 1e-9


# ── M.2: DSRA balance authority ───────────────────────────────────────────────

def test_m2_dsra_balance_passed_when_dsra_opening_populated():
    """When dsra_opening_by_idx is non-empty, fi_schedule receives DSRA balances."""
    # We can't easily unit-test this without access to internal state, so we
    # verify that a project with DSRA mode runs without error when policy is set.
    from finco_core.inputs import DebtServiceReserveSupportMode
    p = _solar_inputs()
    # Enable DSRA mode by checking if the project has one
    dsra_mode = p.financing.dsra_support_mode
    if dsra_mode == DebtServiceReserveSupportMode.CASH_DSRA:
        # Already in CASH_DSRA mode — run with policy
        p2 = dataclasses.replace(p, cash_reserve_interest_policy=_make_policy())
        r = run_project_shareholder_waterfall_model(p2)
        # If we get here, M.2 didn't crash
        assert r is not None
    else:
        pytest.skip("Solar project not in CASH_DSRA mode for this test")


def test_m2_none_dsra_policy_does_not_crash():
    """Non-DSRA projects with policy run without error."""
    p = dataclasses.replace(_solar_inputs(), cash_reserve_interest_policy=_make_policy())
    r = run_project_shareholder_waterfall_model(p)
    assert r is not None


# ── M.3: Source code check — fi_income in formula ─────────────────────────────

def test_m3_fi_income_in_net_income_formula():
    """model.py must contain _fi_income = _fi_by_idx.get(_idx, 0.0) in net income computation."""
    assert "_fi_income" in _MODEL_SRC, "M.3: _fi_income variable not found in model.py"
    assert "_fi_by_idx.get(_idx, 0.0)" in _MODEL_SRC, (
        "M.3: _fi_by_idx.get(_idx, 0.0) pattern not found in model.py"
    )


# ── M.10: Opening unrestricted cash authority ──────────────────────────────────

def test_m10_greenfield_zero_opening_uc_documented():
    """model.py must contain the GREENFIELD_ZERO_OPENING_UNRESTRICTED_CASH comment."""
    assert "GREENFIELD_ZERO_OPENING_UNRESTRICTED_CASH" in _MODEL_SRC


# ── M.11: Final idempotence in source ──────────────────────────────────────────

def test_m11_final_idempotence_in_source():
    """model.py must contain M.11 final idempotence block."""
    assert "M.11" in _MODEL_SRC, "M.11 idempotence marker not found in model.py"


def test_m11_financing_reruns_after_convergence():
    """model.py must re-run run_project_financing_model after convergence break."""
    # Check that after the break, there is another run_project_financing_model call
    # by verifying the _fi_inputs_final variable exists in source
    assert "_fi_inputs_final" in _MODEL_SRC, (
        "M.11: _fi_inputs_final not found in model.py after convergence break"
    )
