"""Tests for C3B3D2A: Oborovo SHL source-truth fixture coherence.

These tests verify internal consistency of the committed fixture
tests/fixtures/excel_oborovo_shl_operating_truth.json.
No production runtime calls. No financial drift.
"""
from __future__ import annotations

import json
import math
import pathlib

import pytest

_FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "excel_oborovo_shl_operating_truth.json"

_RATE = 0.08
_TOL = 1e-6  # kEUR tolerance for roll-forward checks


@pytest.fixture(scope="module")
def fixture_data():
    with open(_FIXTURE) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def periods(fixture_data):
    return fixture_data["periods"]


class TestC3B3D2AFixtureCoherence:
    """A: Fixture loads and has expected structure."""

    def test_a_fixture_loads(self, fixture_data):
        assert fixture_data is not None
        assert "periods" in fixture_data
        assert len(fixture_data["periods"]) == 41

    def test_b_construction_period_is_pik(self, periods):
        p = periods[0]
        assert p["ds_index"] == 0
        assert p["payment_mode"] == "PIK"
        assert p["pik_interest_keur"] == pytest.approx(p["gross_accrued_interest_keur"], abs=_TOL)
        assert p["cash_interest_keur"] == pytest.approx(0.0, abs=_TOL)

    def test_c_operating_opening_balance_matches_construction_close(self, fixture_data, periods):
        stated = fixture_data["operating_opening_balance_keur"]
        construction_close = periods[0]["closing_balance_keur"]
        operating_open = periods[1]["opening_balance_keur"]
        assert stated == pytest.approx(construction_close, abs=_TOL)
        assert stated == pytest.approx(operating_open, abs=_TOL)

    def test_d_roll_forward_identity_all_periods(self, periods):
        """end = beg + fund + cap - principal_repaid for every period."""
        for p in periods:
            expected_end = (
                p["opening_balance_keur"]
                + p["drawdown_keur"]
                + p["pik_interest_keur"]
                - p["principal_repaid_keur"]
            )
            assert p["closing_balance_keur"] == pytest.approx(expected_end, abs=_TOL), (
                f"Roll-forward failed at ds_index={p['ds_index']}: "
                f"expected {expected_end}, got {p['closing_balance_keur']}"
            )

    def test_e_sequential_balance_continuity(self, periods):
        """periods[i].close == periods[i+1].open for all adjacent pairs."""
        for i in range(len(periods) - 1):
            assert periods[i]["closing_balance_keur"] == pytest.approx(
                periods[i + 1]["opening_balance_keur"], abs=_TOL
            ), f"Balance gap between ds_index={i} and {i+1}"

    def test_f_maturity_closes_to_zero(self, periods):
        last = periods[40]
        assert last["ds_index"] == 40
        assert last["closing_balance_keur"] == pytest.approx(0.0, abs=_TOL)

    def test_g_pik_to_cash_switch_at_ds25(self, periods):
        """DS[0..24] have pik>0; DS[25..40] have pik=0."""
        for p in periods[:25]:
            assert p["pik_interest_keur"] > 0, f"Expected pik>0 at ds_index={p['ds_index']}"
        for p in periods[25:]:
            assert p["pik_interest_keur"] == pytest.approx(0.0, abs=_TOL), (
                f"Expected pik=0 at ds_index={p['ds_index']}"
            )

    def test_h_construction_idc_matches_rate_formula(self, periods):
        """Construction IDC = draw × 0.08 × 1.0 (DCF=1.0 exactly for 365-day period)."""
        p = periods[0]
        expected_idc = p["drawdown_keur"] * _RATE * 1.0
        assert p["gross_accrued_interest_keur"] == pytest.approx(expected_idc, abs=_TOL)

    def test_i_workbook_inputs_present(self, fixture_data):
        wi = fixture_data["workbook_inputs"]
        assert wi["shl_draw_keur"]["value"] == pytest.approx(14620.773894815633, abs=_TOL)
        assert wi["shl_annual_rate"]["value"] == pytest.approx(0.08, abs=1e-9)

    def test_j_no_negative_balances(self, periods):
        for p in periods:
            assert p["opening_balance_keur"] >= -_TOL, f"Negative opening at ds_index={p['ds_index']}"
            assert p["closing_balance_keur"] >= -_TOL, f"Negative closing at ds_index={p['ds_index']}"

    def test_k_cash_interest_nonnegative(self, periods):
        for p in periods:
            assert p["cash_interest_keur"] >= -_TOL, f"Negative cash_interest at ds_index={p['ds_index']}"
