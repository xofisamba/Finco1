"""Pre-Freeze Fix 2 Part A — SHL Construction Compounding acceptance tests.

Tests A–J as specified in C3B3FIX2A. Covers:
  A: Backward compatibility — SIMPLE default, Generic Solar/Wind unchanged
  B: Formula proof — SIMPLE and COMPOUND_PERIODIC at known parameters
  C: KUPI source-basis delta proof (+436.179 kEUR)
  D: Finco-basis delta proof (+509.413 kEUR)
  E: Zero construction fraction yields zero PIK for both methods
  F: Zero principal yields zero PIK for both methods
  G: SIMPLE is strictly less than COMPOUND_PERIODIC for positive rate and fraction > 1
  H: Unsupported method raises ValueError (fail closed)
  I: Generic Solar/Wind G2A PIK unchanged (backward compat integration)
  J: Opening operating SHL balance = principal + PIK (identity)

Source-evidence parameters (derivation record, not production inputs):
  KUPI source SHL basis : 68_152.996 kEUR
  Finco SHL basis       : 79_595.855 kEUR
  Annual rate           : 0.08 (8%)
  Construction fraction : 2.0 years
  COMPOUND − SIMPLE delta (source basis) : +436.179 kEUR  (= 68_152.996 × 0.0064)
  COMPOUND − SIMPLE delta (Finco basis)  : +509.413 kEUR  (= 79_595.855 × 0.0064)
  (1.08^2 − 1 − 0.16 = 0.0064)
"""
from __future__ import annotations

import dataclasses
import math

import pytest

from finco_core.inputs._models import ShlConstructionInterestMethod
from financial_engine.shl.construction import compute_shl_construction_pik_keur
from financial_engine.shl.production import ShlConstructionInput, compute_shl_schedule
from financial_engine.shl.contracts import ShlWaterfallPolicy, ShlDayCountConvention
from financial_engine.shl.construction import (
    compute_shl_construction_schedule,
    ShlConstructionPeriodInput,
)


# ---------------------------------------------------------------------------
# Source-evidence constants (Fix 2 derivation record)
# ---------------------------------------------------------------------------
KUPI_SHL_BASIS_KEUR = 68_152.996
FINCO_SHL_BASIS_KEUR = 79_595.855
KUPI_ANNUAL_RATE = 0.08
CONSTRUCTION_FRACTION = 2.0  # years

# (1.08)^2 - 1 = 0.1664; 0.16 SIMPLE fraction; delta factor = 0.0064
_COMPOUND_FACTOR = (1.0 + KUPI_ANNUAL_RATE) ** CONSTRUCTION_FRACTION - 1.0
_SIMPLE_FACTOR = KUPI_ANNUAL_RATE * CONSTRUCTION_FRACTION
_DELTA_FACTOR = _COMPOUND_FACTOR - _SIMPLE_FACTOR  # ≈ 0.0064

KUPI_SOURCE_BASIS_DELTA_KEUR = KUPI_SHL_BASIS_KEUR * _DELTA_FACTOR   # ≈ 436.179 kEUR
FINCO_BASIS_DELTA_KEUR = FINCO_SHL_BASIS_KEUR * _DELTA_FACTOR          # ≈ 509.413 kEUR


# ---------------------------------------------------------------------------
# Test A: Backward compatibility — ShlConstructionInterestMethod default is SIMPLE
# ---------------------------------------------------------------------------
def test_shl_construction_interest_method_default_is_simple():
    """A: ShlConstructionInterestMethod default must be SIMPLE (backward compat)."""
    from finco_core.inputs._models import FinancingParams
    fin = FinancingParams()
    assert fin.shl_construction_interest_method == ShlConstructionInterestMethod.SIMPLE


def test_simple_result_matches_linear_formula():
    """A2: SIMPLE method produces P × r × t."""
    p, r, t = 100.0, 0.08, 2.0
    result = compute_shl_construction_pik_keur(p, r, t, ShlConstructionInterestMethod.SIMPLE)
    assert result == pytest.approx(p * r * t, rel=1e-12)


# ---------------------------------------------------------------------------
# Test B: Formula proof — both methods at reference parameters
# ---------------------------------------------------------------------------
def test_simple_formula_at_kupi_parameters():
    """B1: SIMPLE formula proof at KUPI reference parameters."""
    result = compute_shl_construction_pik_keur(
        KUPI_SHL_BASIS_KEUR, KUPI_ANNUAL_RATE, CONSTRUCTION_FRACTION,
        ShlConstructionInterestMethod.SIMPLE,
    )
    expected = KUPI_SHL_BASIS_KEUR * KUPI_ANNUAL_RATE * CONSTRUCTION_FRACTION
    assert result == pytest.approx(expected, rel=1e-10)


def test_compound_formula_at_kupi_parameters():
    """B2: COMPOUND_PERIODIC formula proof at KUPI reference parameters."""
    result = compute_shl_construction_pik_keur(
        KUPI_SHL_BASIS_KEUR, KUPI_ANNUAL_RATE, CONSTRUCTION_FRACTION,
        ShlConstructionInterestMethod.COMPOUND_PERIODIC,
    )
    expected = KUPI_SHL_BASIS_KEUR * ((1.0 + KUPI_ANNUAL_RATE) ** CONSTRUCTION_FRACTION - 1.0)
    assert result == pytest.approx(expected, rel=1e-10)


# ---------------------------------------------------------------------------
# Test C: KUPI source-basis delta = +436.179 kEUR
# ---------------------------------------------------------------------------
def test_kupi_source_basis_compound_minus_simple_delta():
    """C: COMPOUND − SIMPLE delta on KUPI source SHL basis = +436.179 kEUR."""
    compound = compute_shl_construction_pik_keur(
        KUPI_SHL_BASIS_KEUR, KUPI_ANNUAL_RATE, CONSTRUCTION_FRACTION,
        ShlConstructionInterestMethod.COMPOUND_PERIODIC,
    )
    simple = compute_shl_construction_pik_keur(
        KUPI_SHL_BASIS_KEUR, KUPI_ANNUAL_RATE, CONSTRUCTION_FRACTION,
        ShlConstructionInterestMethod.SIMPLE,
    )
    delta = compound - simple
    assert delta == pytest.approx(KUPI_SOURCE_BASIS_DELTA_KEUR, rel=1e-6)
    assert delta == pytest.approx(436.179, abs=0.002)  # kEUR, source-evidence pin


# ---------------------------------------------------------------------------
# Test D: Finco-basis delta = +509.413 kEUR
# ---------------------------------------------------------------------------
def test_finco_basis_compound_minus_simple_delta():
    """D: COMPOUND − SIMPLE delta on Finco SHL basis = +509.413 kEUR."""
    compound = compute_shl_construction_pik_keur(
        FINCO_SHL_BASIS_KEUR, KUPI_ANNUAL_RATE, CONSTRUCTION_FRACTION,
        ShlConstructionInterestMethod.COMPOUND_PERIODIC,
    )
    simple = compute_shl_construction_pik_keur(
        FINCO_SHL_BASIS_KEUR, KUPI_ANNUAL_RATE, CONSTRUCTION_FRACTION,
        ShlConstructionInterestMethod.SIMPLE,
    )
    delta = compound - simple
    assert delta == pytest.approx(FINCO_BASIS_DELTA_KEUR, rel=1e-6)
    assert delta == pytest.approx(509.413, abs=0.002)  # kEUR, source-evidence pin


# ---------------------------------------------------------------------------
# Test E: Zero construction fraction → zero PIK for both methods
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("method", list(ShlConstructionInterestMethod))
def test_zero_construction_fraction_gives_zero_pik(method):
    """E: Zero construction day-count fraction → zero PIK regardless of method."""
    result = compute_shl_construction_pik_keur(10_000.0, 0.08, 0.0, method)
    assert result == 0.0


# ---------------------------------------------------------------------------
# Test F: Zero principal → zero PIK for both methods
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("method", list(ShlConstructionInterestMethod))
def test_zero_principal_gives_zero_pik(method):
    """F: Zero SHL cash principal → zero PIK regardless of method."""
    result = compute_shl_construction_pik_keur(0.0, 0.08, 2.0, method)
    assert result == 0.0


# ---------------------------------------------------------------------------
# Test G: COMPOUND > SIMPLE for t > 1 and r > 0
# ---------------------------------------------------------------------------
def test_compound_strictly_greater_than_simple_for_multi_year_construction():
    """G: For t > 1 and r > 0, COMPOUND_PERIODIC > SIMPLE (geometric > linear)."""
    compound = compute_shl_construction_pik_keur(
        100_000.0, 0.08, 2.0, ShlConstructionInterestMethod.COMPOUND_PERIODIC
    )
    simple = compute_shl_construction_pik_keur(
        100_000.0, 0.08, 2.0, ShlConstructionInterestMethod.SIMPLE
    )
    assert compound > simple


# ---------------------------------------------------------------------------
# Test H: Unsupported method raises ValueError (fail closed)
# ---------------------------------------------------------------------------
def test_unsupported_method_raises():
    """H: Passing an unrecognised method raises ValueError — fail closed."""
    with pytest.raises((ValueError, AttributeError)):
        compute_shl_construction_pik_keur(1000.0, 0.08, 2.0, "UNKNOWN_METHOD")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Test I: Generic Solar/Wind G2A — construction PIK is zero (backward compat)
# ---------------------------------------------------------------------------
def test_generic_solar_construction_pik_is_zero_both_methods():
    """I: Generic Solar/Wind have shl_construction_day_count_fraction=None → PIK=0."""
    from finco_core.inputs._models import FinancingParams
    fin = FinancingParams()
    # Generic Solar/Wind factories leave shl_construction_day_count_fraction = None
    assert fin.shl_construction_day_count_fraction is None
    # With fraction=0 or None, PIK is zero for SIMPLE
    pik_simple = compute_shl_construction_pik_keur(
        10_000.0, 0.08, 0.0, ShlConstructionInterestMethod.SIMPLE
    )
    pik_compound = compute_shl_construction_pik_keur(
        10_000.0, 0.08, 0.0, ShlConstructionInterestMethod.COMPOUND_PERIODIC
    )
    assert pik_simple == 0.0
    assert pik_compound == 0.0


# ---------------------------------------------------------------------------
# Test J: Opening operating SHL = principal + PIK (identity)
# ---------------------------------------------------------------------------
def test_opening_operating_shl_identity():
    """J: opening_operating_shl = shl_cash_principal + construction_pik."""
    principal = KUPI_SHL_BASIS_KEUR
    pik = compute_shl_construction_pik_keur(
        principal, KUPI_ANNUAL_RATE, CONSTRUCTION_FRACTION,
        ShlConstructionInterestMethod.COMPOUND_PERIODIC,
    )
    opening_operating_shl = principal + pik
    expected_opening = principal * (1.0 + KUPI_ANNUAL_RATE) ** CONSTRUCTION_FRACTION
    assert opening_operating_shl == pytest.approx(expected_opening, rel=1e-10)


# ---------------------------------------------------------------------------
# Test K: Causal compounding in ShlConstructionInput via compute_shl_schedule
# ---------------------------------------------------------------------------
def test_shl_construction_input_compound_periodic_gives_geometric_result():
    """K1: COMPOUND_PERIODIC in ShlConstructionInput produces geometric interest."""
    draw = 10_000.0
    rate = 0.08
    dcf = 2.0
    policy = ShlWaterfallPolicy(
        annual_rate=rate,
        day_count_convention=ShlDayCountConvention.ACT_365_FIXED,
    )
    constr = ShlConstructionInput(
        draw_keur=draw,
        annual_rate=rate,
        dcf=dcf,
        period_index=0,
        construction_interest_method=ShlConstructionInterestMethod.COMPOUND_PERIODIC,
    )
    result = compute_shl_schedule(constr, (), policy)
    expected_pik = draw * ((1.0 + rate) ** dcf - 1.0)
    assert result.construction.pik_interest_keur == pytest.approx(expected_pik, rel=1e-10)
    assert result.construction.closing_balance_keur == pytest.approx(draw + expected_pik, rel=1e-10)


def test_shl_construction_input_simple_gives_linear_result():
    """K2: SIMPLE (default) in ShlConstructionInput produces linear interest."""
    draw = 10_000.0
    rate = 0.08
    dcf = 2.0
    policy = ShlWaterfallPolicy(
        annual_rate=rate,
        day_count_convention=ShlDayCountConvention.ACT_365_FIXED,
    )
    constr = ShlConstructionInput(
        draw_keur=draw,
        annual_rate=rate,
        dcf=dcf,
        period_index=0,
        construction_interest_method=ShlConstructionInterestMethod.SIMPLE,
    )
    result = compute_shl_schedule(constr, (), policy)
    expected_pik = draw * rate * dcf
    assert result.construction.pik_interest_keur == pytest.approx(expected_pik, rel=1e-10)


def test_compound_produces_more_pik_than_simple_in_shl_schedule():
    """K3: COMPOUND_PERIODIC always > SIMPLE for dcf > 1, rate > 0 (geometric > linear)."""
    draw = 10_000.0
    rate = 0.08
    dcf = 2.0
    policy = ShlWaterfallPolicy(
        annual_rate=rate,
        day_count_convention=ShlDayCountConvention.ACT_365_FIXED,
    )
    compound = compute_shl_schedule(
        ShlConstructionInput(draw_keur=draw, annual_rate=rate, dcf=dcf,
                             construction_interest_method=ShlConstructionInterestMethod.COMPOUND_PERIODIC),
        (),
        policy,
    )
    simple = compute_shl_schedule(
        ShlConstructionInput(draw_keur=draw, annual_rate=rate, dcf=dcf,
                             construction_interest_method=ShlConstructionInterestMethod.SIMPLE),
        (),
        policy,
    )
    assert compound.construction.pik_interest_keur > simple.construction.pik_interest_keur
    assert compound.construction.closing_balance_keur > simple.construction.closing_balance_keur


def test_shl_construction_input_default_method_is_simple():
    """K4: ShlConstructionInput default construction_interest_method is SIMPLE (backward compat)."""
    constr = ShlConstructionInput(draw_keur=1000.0, annual_rate=0.08, dcf=1.0)
    assert constr.construction_interest_method == ShlConstructionInterestMethod.SIMPLE


# ---------------------------------------------------------------------------
# Test L: Two-period proof — SIMPLE=120, COMPOUND=121 (distinct methods)
# ---------------------------------------------------------------------------
def test_two_period_simple_no_pik_compounding():
    """L1: SIMPLE two-period (draw 100/0, r=10%, dcf=1.0 each).
    P1: basis=100, interest=10, closing=110.
    P2: basis=100 (cash only, NOT 110), interest=10, closing=120.
    Prior PIK (10) must NOT enter the P2 interest basis.
    """
    periods = (
        ShlConstructionPeriodInput(draw_keur=100.0, day_count_fraction=1.0, period_index=0),
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=1),
    )
    result = compute_shl_construction_schedule(
        opening_balance_keur=0.0,
        periods=periods,
        annual_rate=0.10,
        method=ShlConstructionInterestMethod.SIMPLE,
    )
    p1, p2 = result.periods
    assert p1.pik_interest_keur == pytest.approx(10.0, rel=1e-10)
    assert p1.closing_balance_keur == pytest.approx(110.0, rel=1e-10)
    # P2: interest basis = 100 (cash principal only, not 110)
    assert p2.pik_interest_keur == pytest.approx(10.0, rel=1e-10), (
        "SIMPLE P2 interest must be 10 (basis=100), not 11 (which would be compounding on 110)"
    )
    assert result.opening_operating_shl_balance_keur == pytest.approx(120.0, rel=1e-10)


def test_two_period_compound_pik_enters_basis():
    """L2: COMPOUND two-period (draw 100/0, r=10%, dcf=1.0 each).
    P1: basis=100, interest=10, closing=110.
    P2: basis=110 (prior closing including PIK), interest=11, closing=121.
    """
    periods = (
        ShlConstructionPeriodInput(draw_keur=100.0, day_count_fraction=1.0, period_index=0),
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=1),
    )
    result = compute_shl_construction_schedule(
        opening_balance_keur=0.0,
        periods=periods,
        annual_rate=0.10,
        method=ShlConstructionInterestMethod.COMPOUND_PERIODIC,
    )
    p1, p2 = result.periods
    assert p1.pik_interest_keur == pytest.approx(10.0, rel=1e-10)
    assert p1.closing_balance_keur == pytest.approx(110.0, rel=1e-10)
    assert p2.pik_interest_keur == pytest.approx(11.0, rel=1e-10)
    assert result.opening_operating_shl_balance_keur == pytest.approx(121.0, rel=1e-10)


def test_two_period_simple_ne_compound():
    """L3: SIMPLE final (120) != COMPOUND final (121) — methods are distinct."""
    periods = (
        ShlConstructionPeriodInput(draw_keur=100.0, day_count_fraction=1.0, period_index=0),
        ShlConstructionPeriodInput(draw_keur=0.0, day_count_fraction=1.0, period_index=1),
    )
    simple = compute_shl_construction_schedule(
        opening_balance_keur=0.0, periods=periods,
        annual_rate=0.10, method=ShlConstructionInterestMethod.SIMPLE,
    )
    compound = compute_shl_construction_schedule(
        opening_balance_keur=0.0, periods=periods,
        annual_rate=0.10, method=ShlConstructionInterestMethod.COMPOUND_PERIODIC,
    )
    assert simple.opening_operating_shl_balance_keur == pytest.approx(120.0, rel=1e-10)
    assert compound.opening_operating_shl_balance_keur == pytest.approx(121.0, rel=1e-10)
    assert simple.opening_operating_shl_balance_keur != compound.opening_operating_shl_balance_keur


# ---------------------------------------------------------------------------
# Test M: Staggered draw 50/50 — both methods
# ---------------------------------------------------------------------------
def test_staggered_draw_simple():
    """M1: Staggered draw SIMPLE: P1 draw=50, P2 draw=50, r=10%, dcf=1.0.
    P1: cash_basis=50, interest=5, accumulated_pik=5, closing=55.
    P2: cash_basis=100, interest=10, accumulated_pik=15, closing=115.
    opening_operating = 115.
    """
    periods = (
        ShlConstructionPeriodInput(draw_keur=50.0, day_count_fraction=1.0, period_index=0),
        ShlConstructionPeriodInput(draw_keur=50.0, day_count_fraction=1.0, period_index=1),
    )
    result = compute_shl_construction_schedule(
        opening_balance_keur=0.0, periods=periods,
        annual_rate=0.10, method=ShlConstructionInterestMethod.SIMPLE,
    )
    p1, p2 = result.periods
    assert p1.cash_principal_balance_keur == pytest.approx(50.0, rel=1e-10)
    assert p1.pik_interest_keur == pytest.approx(5.0, rel=1e-10)
    assert p1.closing_balance_keur == pytest.approx(55.0, rel=1e-10)
    assert p2.cash_principal_balance_keur == pytest.approx(100.0, rel=1e-10)
    assert p2.pik_interest_keur == pytest.approx(10.0, rel=1e-10)
    assert result.total_pik_keur == pytest.approx(15.0, rel=1e-10)
    assert result.opening_operating_shl_balance_keur == pytest.approx(115.0, rel=1e-10)


def test_staggered_draw_compound():
    """M2: Staggered draw COMPOUND: P1 draw=50, P2 draw=50, r=10%, dcf=1.0.
    P1: basis=50, interest=5, closing=55.
    P2: basis=55+50=105, interest=10.5, closing=115.5.
    total_pik=15.5.
    """
    periods = (
        ShlConstructionPeriodInput(draw_keur=50.0, day_count_fraction=1.0, period_index=0),
        ShlConstructionPeriodInput(draw_keur=50.0, day_count_fraction=1.0, period_index=1),
    )
    result = compute_shl_construction_schedule(
        opening_balance_keur=0.0, periods=periods,
        annual_rate=0.10, method=ShlConstructionInterestMethod.COMPOUND_PERIODIC,
    )
    p1, p2 = result.periods
    assert p1.pik_interest_keur == pytest.approx(5.0, rel=1e-10)
    assert p1.closing_balance_keur == pytest.approx(55.0, rel=1e-10)
    assert p2.pik_interest_keur == pytest.approx(10.5, rel=1e-10)
    assert result.total_pik_keur == pytest.approx(15.5, rel=1e-10)
    assert result.opening_operating_shl_balance_keur == pytest.approx(115.5, rel=1e-10)
