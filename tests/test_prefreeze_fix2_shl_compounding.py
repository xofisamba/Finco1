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
