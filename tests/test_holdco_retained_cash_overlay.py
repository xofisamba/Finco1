"""Phase 5D.4 tests for HoldCo retained cash overlay."""
from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from domain.portfolio.distribution_constraints.holdco_overlay import (
    _safe_float,
    HoldCoRetainedCashOverlay,
    holdco_requested_distribution_by_period,
    holdco_available_distribution_by_period,
    build_holdco_retained_cash_overlay,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def make_holdco_result(name, periods_data):
    """Factory: mock HoldCoResult with period data.

    periods_data: list of dicts with optional 'distribution_to_sponsor_keur' key.
    """
    hc = MagicMock()
    hc.name = name
    hc.periods = []
    for idx, d in enumerate(periods_data):
        p = MagicMock()
        p.period = idx
        p.distribution_to_sponsor_keur = d.get("distribution_to_sponsor_keur", 0.0)
        hc.periods.append(p)
    return hc


# ── A. _safe_float helper ──────────────────────────────────────────────────────

class TestSafeFloat:
    def test_int_accepted(self):
        assert _safe_float(80) == 80.0

    def test_float_accepted(self):
        assert _safe_float(80.0) == 80.0

    def test_zero_accepted(self):
        assert _safe_float(0) == 0.0

    def test_bool_rejected_to_default(self):
        assert _safe_float(True) == 0.0
        assert _safe_float(False) == 0.0

    def test_none_rejected(self):
        assert _safe_float(None) == 0.0

    def test_string_rejected(self):
        assert _safe_float("80") == 0.0


# ── B. holdco_requested_distribution_by_period ─────────────────────────────────

class TestHoldcoRequestedDistribution:
    def test_empty_periods(self):
        hc = make_holdco_result("HOLDCO", [])
        assert holdco_requested_distribution_by_period(hc) == ()

    def test_distribution_to_sponsor_keur_preferred(self):
        hc = make_holdco_result("HOLDCO", [
            {"distribution_to_sponsor_keur": 500.0},
            {"distribution_to_sponsor_keur": 600.0},
        ])
        result = holdco_requested_distribution_by_period(hc)
        assert result == (500.0, 600.0)

    def test_missing_attr_fallback_to_zero(self):
        hc = MagicMock(spec=["periods"])
        p = MagicMock()
        p.distribution_to_sponsor_keur = 400.0  # real attr
        p2 = MagicMock()
        del p2.distribution_to_sponsor_keur  # missing attr
        hc.periods = [p, p2]
        result = holdco_requested_distribution_by_period(hc)
        assert result == (400.0, 0.0)

    def test_negative_dist_converted_to_zero(self):
        hc = make_holdco_result("HOLDCO", [
            {"distribution_to_sponsor_keur": -100.0},
        ])
        result = holdco_requested_distribution_by_period(hc)
        assert result == (0.0,)

    def test_int_values_accepted(self):
        hc = make_holdco_result("HOLDCO", [
            {"distribution_to_sponsor_keur": 500},   # int
        ])
        result = holdco_requested_distribution_by_period(hc)
        assert result == (500.0,)

    def test_bool_values_ignored(self):
        hc = make_holdco_result("HOLDCO", [
            {"distribution_to_sponsor_keur": True},   # bool → 0.0
        ])
        result = holdco_requested_distribution_by_period(hc)
        assert result == (0.0,)


# ── C. holdco_available_distribution_by_period ───────────────────────────────

class TestHoldcoAvailableDistribution:
    def test_retained_cash_reduces_available(self):
        hc = make_holdco_result("HOLDCO", [
            {"distribution_to_sponsor_keur": 500.0},
        ])
        result = holdco_available_distribution_by_period(hc, (200.0,))
        assert result == (300.0,)

    def test_available_never_negative(self):
        hc = make_holdco_result("HOLDCO", [
            {"distribution_to_sponsor_keur": 100.0},
        ])
        result = holdco_available_distribution_by_period(hc, (500.0,))
        assert result == (0.0,)

    def test_zero_retained_all_available(self):
        hc = make_holdco_result("HOLDCO", [
            {"distribution_to_sponsor_keur": 300.0},
        ])
        result = holdco_available_distribution_by_period(hc, (0.0,))
        assert result == (300.0,)

    def test_zero_padding_shorter_retained(self):
        hc = make_holdco_result("HOLDCO", [
            {"distribution_to_sponsor_keur": 300.0},
            {"distribution_to_sponsor_keur": 400.0},
        ])
        # retained has only 1 period
        result = holdco_available_distribution_by_period(hc, (100.0,))
        assert result == (200.0, 400.0)  # second period zero-padded

    def test_zero_padding_shorter_requested(self):
        hc = make_holdco_result("HOLDCO", [
            {"distribution_to_sponsor_keur": 300.0},
        ])
        # retained has 2 periods
        result = holdco_available_distribution_by_period(hc, (100.0, 100.0))
        assert result == (200.0, 0.0)  # second period zero-padded

    def test_no_mutation_of_holdco_result(self):
        hc = make_holdco_result("HOLDCO", [
            {"distribution_to_sponsor_keur": 500.0},
        ])
        holdco_available_distribution_by_period(hc, (100.0,))
        assert hc.periods[0].distribution_to_sponsor_keur == 500.0


# ── D. HoldCoRetainedCashOverlay validation ────────────────────────────────────

class TestHoldCoRetainedCashOverlay:
    def test_valid_construction(self):
        ov = HoldCoRetainedCashOverlay(
            entity_code="HOLDCO",
            retained_cash_by_period=(100.0, 200.0),
            requested_distribution_by_period=(500.0, 600.0),
            available_distribution_by_period=(400.0, 400.0),
        )
        assert ov.entity_code == "HOLDCO"
        assert ov.retained_cash_by_period == (100.0, 200.0)

    def test_empty_entity_code_raises(self):
        with pytest.raises(ValueError, match="entity_code must be non-empty"):
            HoldCoRetainedCashOverlay(
                entity_code="",
                retained_cash_by_period=(100.0,),
                requested_distribution_by_period=(500.0,),
                available_distribution_by_period=(400.0,),
            )

    def test_whitespace_entity_code_raises(self):
        with pytest.raises(ValueError, match="entity_code must be non-empty"):
            HoldCoRetainedCashOverlay(
                entity_code="   ",
                retained_cash_by_period=(100.0,),
                requested_distribution_by_period=(500.0,),
                available_distribution_by_period=(400.0,),
            )

    def test_negative_retained_raises(self):
        with pytest.raises(ValueError, match="retained_cash_by_period values must be >= 0"):
            HoldCoRetainedCashOverlay(
                entity_code="HOLDCO",
                retained_cash_by_period=(-50.0,),
                requested_distribution_by_period=(500.0,),
                available_distribution_by_period=(400.0,),
            )

    def test_negative_available_raises(self):
        with pytest.raises(ValueError, match="available_distribution_by_period values must be >= 0"):
            HoldCoRetainedCashOverlay(
                entity_code="HOLDCO",
                retained_cash_by_period=(100.0,),
                requested_distribution_by_period=(500.0,),
                available_distribution_by_period=(-200.0,),
            )

    def test_mismatched_length_warns(self):
        ov = HoldCoRetainedCashOverlay(
            entity_code="HOLDCO",
            retained_cash_by_period=(100.0, 200.0, 300.0),
            requested_distribution_by_period=(500.0,),  # different length
            available_distribution_by_period=(400.0, 200.0, 300.0),
        )
        warning_text = " ".join(ov.warnings)
        assert "retained_cash_by_period length" in warning_text
        assert "!= requested_distribution_by_period length" in warning_text

    def test_matched_length_no_warning(self):
        ov = HoldCoRetainedCashOverlay(
            entity_code="HOLDCO",
            retained_cash_by_period=(100.0,),
            requested_distribution_by_period=(500.0,),
            available_distribution_by_period=(400.0,),
        )
        assert ov.warnings == ()


# ── E. build_holdco_retained_cash_overlay ─────────────────────────────────────

class TestBuildHoldCoRetainedCashOverlay:
    def test_builds_correct_overlay(self):
        hc = make_holdco_result("HOLDCO", [
            {"distribution_to_sponsor_keur": 500.0},
            {"distribution_to_sponsor_keur": 600.0},
        ])
        overlay = build_holdco_retained_cash_overlay(hc, (100.0, 100.0))
        assert overlay.entity_code == "HOLDCO"
        assert overlay.requested_distribution_by_period == (500.0, 600.0)
        assert overlay.retained_cash_by_period == (100.0, 100.0)
        assert overlay.available_distribution_by_period == (400.0, 500.0)

    def test_no_mutation_of_holdco_result(self):
        hc = make_holdco_result("HOLDCO", [
            {"distribution_to_sponsor_keur": 500.0},
        ])
        build_holdco_retained_cash_overlay(hc, (100.0,))
        assert hc.periods[0].distribution_to_sponsor_keur == 500.0

    def test_fallback_when_dist_attr_missing(self):
        hc = MagicMock(spec=["periods"])
        p = MagicMock()
        del p.distribution_to_sponsor_keur  # missing
        hc.periods = [p]
        overlay = build_holdco_retained_cash_overlay(hc, (0.0,))
        assert overlay.requested_distribution_by_period == (0.0,)

    def test_empty_periods(self):
        hc = make_holdco_result("HOLDCO", [])
        overlay = build_holdco_retained_cash_overlay(hc, ())
        assert overlay.entity_code == "HOLDCO"
        assert overlay.requested_distribution_by_period == ()
        assert overlay.available_distribution_by_period == ()

    def test_missing_name_becomes_holdco(self):
        hc = MagicMock(spec=[])  # no name attribute
        hc.periods = []
        del hc.name
        overlay = build_holdco_retained_cash_overlay(hc, ())
        assert overlay.entity_code == "HOLDCO"