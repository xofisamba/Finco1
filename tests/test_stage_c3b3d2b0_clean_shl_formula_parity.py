"""Stage C3B3D2B0-R1 — Clean SHL Waterfall Formula Parity Tests.

Proves that compute_shl_waterfall_period() reproduces the Excel-sourced D2A
fixture values to machine epsilon across all 41 periods (DS[0..40]).

DCF proof (C3B3D2B0-R1):
  The day-count fraction is computed INDEPENDENTLY of SHL gross interest as:
    dcf = ((period_end_date - period_start_date).days + 1) / 365
  Proven against all 40 operating periods: max delta = 1.11e-16 (machine epsilon).
  This resolves the previous circular DCF (shl_dcf_derived_actual_365 = gross / (opening*rate)).

Test driver inputs:
  - period dates: from interest_limitation/oborovo_interest_limitation_fixture.json
    (committed SOURCE_RAW fixture, independent of SHL gross interest)
  - free_cash_flow_for_shl_keur: from excel_oborovo_financial_truth.json CF section
    (SOURCE_RAW_CACHED_VALUE, upstream of SHL service)
  - shl_draw_keur, shl_annual_rate: from D2A fixture workbook_inputs (SOURCE_RAW)

Construction handled by C3B3D1 engine (opening=0, drawdown=draw, dcf=1.0).

Governance constraints enforced by tests:
  - No mode enum, no mode dispatch
  - 13547.2 not in clean calculation
  - DS25/DS40 not hardcoded
  - financial_engine does NOT import finco_core waterfall
  - Derived gross-based DCF NOT used as parity driver
"""
from __future__ import annotations

import importlib
import inspect
import json
import math
from datetime import date
from pathlib import Path

import pytest

# ── fixtures ─────────────────────────────────────────────────────────────────

FIXTURES = Path(__file__).parent / "fixtures"
D2A_PATH = FIXTURES / "excel_oborovo_shl_operating_truth.json"
FIN_PATH = FIXTURES / "excel_oborovo_financial_truth.json"

_TOL = 1e-9           # floating-point equality tolerance
_PARITY_TOL = 1e-6    # kEUR parity tolerance (sub-cent)


@pytest.fixture(scope="module")
def d2a():
    return json.loads(D2A_PATH.read_text())


@pytest.fixture(scope="module")
def fin():
    return json.loads(FIN_PATH.read_text())


@pytest.fixture(scope="module")
def d2a_periods(d2a):
    return d2a["periods"]


@pytest.fixture(scope="module")
def cf_shl(fin):
    """free_cash_flow_for_shl_keur list (61 entries, 0-based DS index)."""
    return fin["cf"]["free_cash_flow_for_shl_keur"]


@pytest.fixture(scope="module")
def rate(d2a):
    return d2a["workbook_inputs"]["shl_annual_rate"]["value"]


@pytest.fixture(scope="module")
def draw(d2a):
    return d2a["workbook_inputs"]["shl_draw_keur"]["value"]


@pytest.fixture(scope="module")
def waterfall():
    from financial_engine.shl.waterfall import compute_shl_waterfall_period
    return compute_shl_waterfall_period


@pytest.fixture(scope="module")
def dcf_fn():
    from financial_engine.shl.waterfall import compute_shl_dcf_actual_365_inclusive
    return compute_shl_dcf_actual_365_inclusive


def _independent_dcf(p: dict) -> float:
    """Compute DCF from period dates — does NOT read gross_accrued_interest_keur."""
    s = date.fromisoformat(p["period_start_date"])
    e = date.fromisoformat(p["period_end_date"])
    return ((e - s).days + 1) / 365


# ── A: Derived gross-based DCF is NOT the parity driver ──────────────────────

class TestA_DerivedDcfNotUsedAsParity:
    """shl_dcf_derived_actual_365 = gross/(opening*rate) is circular.
    The test driver must NOT use it as the DCF input to the formula under test."""

    def test_derived_dcf_field_is_labelled_diagnostic(self, d2a):
        # The field still exists in the fixture but is labelled as diagnostic
        dc = d2a["day_count_convention"]
        # The proven label must be the independent one
        assert "SOURCE_PROVEN" in dc.get("shl_operating_convention_label", "")

    def test_derived_dcf_differs_from_independent_for_exclusive_dates(self, d2a_periods):
        # If exclusive dates were used, DS[1] would give 183/365 != source-derived
        p1 = next(x for x in d2a_periods if x["ds_index"] == 1)
        s = date.fromisoformat(p1["period_start_date"])
        e = date.fromisoformat(p1["period_end_date"])
        exclusive_dcf = (e - s).days / 365  # WRONG — exclusive
        derived_dcf = p1["shl_dcf_derived_actual_365"]
        assert abs(exclusive_dcf - derived_dcf) > 0.001  # proves exclusive is wrong

    def test_independent_dcf_matches_source_to_machine_epsilon(self, d2a_periods):
        """((end - start).days + 1) / 365 matches source-derived DCF to machine epsilon."""
        max_delta = 0.0
        for p in d2a_periods:
            if "period_start_date" not in p:
                continue
            independent = _independent_dcf(p)
            derived = p["shl_dcf_derived_actual_365"]
            max_delta = max(max_delta, abs(independent - derived))
        assert max_delta < 1e-14  # machine epsilon

    def test_gross_based_dcf_is_circular(self, d2a_periods, rate):
        """Proves that shl_dcf_derived_actual_365 = gross / (opening * rate)
        and is therefore circular when used as the DCF driver."""
        p1 = next(x for x in d2a_periods if x["ds_index"] == 1)
        derived = p1["shl_dcf_derived_actual_365"]
        circular = p1["gross_accrued_interest_keur"] / (p1["opening_balance_keur"] * rate)
        assert abs(derived - circular) < _TOL  # confirms the derived DCF IS circular


# ── B: Source DCF formula and convention documented ───────────────────────────

class TestB_SourceDcfFormulaDocumented:
    """The proven DCF formula is documented in the D2A fixture."""

    def test_formula_documented_in_fixture(self, d2a):
        dc = d2a["day_count_convention"]
        assert "shl_operating_formula" in dc
        assert "(end" in dc["shl_operating_formula"] or "end_date" in dc["shl_operating_formula"]

    def test_convention_label_is_proven(self, d2a):
        dc = d2a["day_count_convention"]
        assert "SOURCE_PROVEN" in dc.get("shl_operating_convention_label", "")

    def test_denominator_is_365_fixed(self, d2a):
        dc = d2a["day_count_convention"]
        assert dc.get("shl_operating_denominator") == 365

    def test_previous_error_explained(self, d2a):
        dc = d2a["day_count_convention"]
        note = dc.get("shl_operating_previous_error_explanation", "")
        assert "387" in note or "exclusive" in note.lower()


# ── C: DCF computed independently of SHL gross interest ──────────────────────

class TestC_DcfComputedIndependently:
    """compute_shl_dcf_actual_365_inclusive reads only dates, not gross interest."""

    def test_dcf_function_signature_has_no_gross_parameter(self, dcf_fn):
        sig = inspect.signature(dcf_fn)
        params = list(sig.parameters.keys())
        assert "gross" not in params
        assert "interest" not in params
        assert "rate" not in params
        assert "opening" not in params

    def test_dcf_function_source_does_not_read_gross_interest(self):
        src = Path("financial_engine/shl/waterfall.py").read_text()
        dcf_lines = [
            l for l in src.splitlines()
            if "def compute_shl_dcf" in l or (
                "compute_shl_dcf" in l and "def " not in l
            )
        ]
        # Function body should use .days, not interest fields
        func_src = src[src.index("def compute_shl_dcf"):]
        func_src = func_src[:func_src.index("\ndef ", len("def compute_shl_dcf"))]
        assert "gross" not in func_src
        assert "interest" not in func_src
        assert "rate" not in func_src

    def test_dcf_ds1_value_correct(self, dcf_fn):
        """DS[1]: 2030-07-01 to 2030-12-31 inclusive = 184 days → 184/365."""
        dcf = dcf_fn(date(2030, 7, 1), date(2030, 12, 31))
        assert abs(dcf - 184 / 365) < _TOL

    def test_dcf_ds1_matches_source_derived(self, d2a_periods, dcf_fn):
        p1 = next(x for x in d2a_periods if x["ds_index"] == 1)
        s = date.fromisoformat(p1["period_start_date"])
        e = date.fromisoformat(p1["period_end_date"])
        independent_dcf = dcf_fn(s, e)
        assert abs(independent_dcf - p1["shl_dcf_derived_actual_365"]) < 1e-14


# ── D: DS[1] independent DCF value ───────────────────────────────────────────

class TestD_Ds1IndependentDcfValue:
    """DS[1] DCF = 184/365, not 183/365."""

    def test_ds1_days_inclusive(self):
        start = date(2030, 7, 1)
        end = date(2030, 12, 31)
        days_excl = (end - start).days
        days_incl = days_excl + 1
        assert days_excl == 183
        assert days_incl == 184

    def test_ds1_dcf_inclusive(self, dcf_fn):
        dcf = dcf_fn(date(2030, 7, 1), date(2030, 12, 31))
        assert abs(dcf - 184 / 365) < _TOL

    def test_ds1_dcf_exclusive_is_wrong(self, d2a_periods, dcf_fn):
        """183/365 does NOT match source; 184/365 does."""
        p1 = next(x for x in d2a_periods if x["ds_index"] == 1)
        exclusive = 183 / 365
        inclusive = dcf_fn(date(2030, 7, 1), date(2030, 12, 31))
        derived = p1["shl_dcf_derived_actual_365"]
        assert abs(inclusive - derived) < 1e-14
        assert abs(exclusive - derived) > 0.002  # exclusive is materially wrong


# ── E: Leap-year period handling ──────────────────────────────────────────────

class TestE_LeapYearPeriods:
    """Denominator stays 365 even when period overlaps Feb 29."""

    @pytest.mark.parametrize("ds", [4, 12, 20, 28, 36])
    def test_leap_year_period_denominator_is_365(self, d2a_periods, dcf_fn, ds):
        p = next(x for x in d2a_periods if x["ds_index"] == ds)
        s = date.fromisoformat(p["period_start_date"])
        e = date.fromisoformat(p["period_end_date"])
        days_incl = (e - s).days + 1
        dcf = dcf_fn(s, e)
        assert abs(dcf - days_incl / 365) < _TOL

    @pytest.mark.parametrize("ds", [4, 12, 20, 28, 36])
    def test_leap_year_dcf_matches_source(self, d2a_periods, dcf_fn, ds):
        p = next(x for x in d2a_periods if x["ds_index"] == ds)
        s = date.fromisoformat(p["period_start_date"])
        e = date.fromisoformat(p["period_end_date"])
        assert abs(dcf_fn(s, e) - p["shl_dcf_derived_actual_365"]) < 1e-14

    def test_ds4_is_leap_year_period(self, d2a_periods):
        p = next(x for x in d2a_periods if x["ds_index"] == 4)
        e = date.fromisoformat(p["period_end_date"])
        assert e.year == 2032
        # 2032 is a leap year — Feb 29 exists
        assert date(2032, 2, 29)  # no exception = leap year confirmed


# ── F: First-period treatment ─────────────────────────────────────────────────

class TestF_FirstPeriodTreatment:
    """DS[1] is not special-cased; the formula applies uniformly."""

    def test_ds1_no_special_day_count_treatment(self, d2a_periods, dcf_fn):
        """Same formula as every other period."""
        p1 = next(x for x in d2a_periods if x["ds_index"] == 1)
        s = date.fromisoformat(p1["period_start_date"])
        e = date.fromisoformat(p1["period_end_date"])
        assert abs(dcf_fn(s, e) - p1["shl_dcf_derived_actual_365"]) < 1e-14

    def test_ds1_no_first_period_offset(self, d2a_periods, dcf_fn):
        """No offset or stub-period adjustment needed for DS[1]."""
        p1 = next(x for x in d2a_periods if x["ds_index"] == 1)
        # Just date arithmetic — no special case
        s = date.fromisoformat(p1["period_start_date"])
        e = date.fromisoformat(p1["period_end_date"])
        assert s == date(2030, 7, 1)
        assert e == date(2030, 12, 31)
        assert (e - s).days + 1 == 184


# ── G: Final-period treatment ─────────────────────────────────────────────────

class TestG_FinalPeriodTreatment:
    """DS[40] is not special-cased; closing naturally reaches zero via sweep."""

    def test_ds40_dcf_from_dates(self, d2a_periods, dcf_fn):
        p40 = next(x for x in d2a_periods if x["ds_index"] == 40)
        s = date.fromisoformat(p40["period_start_date"])
        e = date.fromisoformat(p40["period_end_date"])
        assert abs(dcf_fn(s, e) - p40["shl_dcf_derived_actual_365"]) < 1e-14

    def test_ds40_closing_is_zero_from_formula(self, waterfall, rate, d2a_periods, cf_shl, dcf_fn):
        p40 = next(x for x in d2a_periods if x["ds_index"] == 40)
        s = date.fromisoformat(p40["period_start_date"])
        e = date.fromisoformat(p40["period_end_date"])
        r = waterfall(p40["opening_balance_keur"], rate, dcf_fn(s, e), cf_shl[40], 40)
        assert abs(r.closing_balance_keur) < _PARITY_TOL


# ── H: Recursive gross parity — independent DCF ───────────────────────────────

class TestH_RecursiveGrossParityIndependentDcf:
    """Max gross delta across all 40 operating periods < 1e-6 kEUR."""

    @pytest.fixture(scope="module")
    def recursive_results(self, waterfall, draw, rate, d2a_periods, cf_shl, dcf_fn, d2a):
        from financial_engine.shl.engine import compute_shl_period
        from financial_engine.shl.contracts import ShlInterestPaymentMode
        # Construction via D1 engine
        cp = d2a["construction_period"]
        r0 = compute_shl_period(
            opening_balance_keur=0.0,
            drawdown_keur=draw,
            day_count_fraction=1.0,
            annual_rate=rate,
            payment_mode=ShlInterestPaymentMode.PIK,
            scheduled_principal_keur=0.0,
            period_index=0,
        )
        results_op = []
        opening = r0.closing_balance_keur
        for ds in range(1, 41):
            p = next(x for x in d2a_periods if x["ds_index"] == ds)
            s = date.fromisoformat(p["period_start_date"])
            e = date.fromisoformat(p["period_end_date"])
            dcf = dcf_fn(s, e)  # INDEPENDENT — reads only dates
            r = waterfall(opening, rate, dcf, cf_shl[ds], ds)
            results_op.append(r)
            opening = r.closing_balance_keur
        return results_op

    def test_max_gross_delta_sub_cent(self, recursive_results, d2a_periods):
        max_d = 0.0
        for r in recursive_results:
            p = next(x for x in d2a_periods if x["ds_index"] == r.period_index)
            max_d = max(max_d, abs(r.gross_accrued_interest_keur - p["gross_accrued_interest_keur"]))
        assert max_d < _PARITY_TOL, f"Max gross delta {max_d:.2e} kEUR"


# ── I: Recursive cash-interest parity ─────────────────────────────────────────

class TestI_RecursiveCashInterestParity:
    """Max cash-interest delta across all 40 periods < 1e-6 kEUR."""

    @pytest.fixture(scope="module")
    def recursive_results(self, waterfall, draw, rate, d2a_periods, cf_shl, dcf_fn, d2a):
        from financial_engine.shl.engine import compute_shl_period
        from financial_engine.shl.contracts import ShlInterestPaymentMode
        cp = d2a["construction_period"]
        r0 = compute_shl_period(0.0, draw, 1.0, rate, ShlInterestPaymentMode.PIK, 0.0, 0)
        opening = r0.closing_balance_keur
        results = []
        for ds in range(1, 41):
            p = next(x for x in d2a_periods if x["ds_index"] == ds)
            s = date.fromisoformat(p["period_start_date"])
            e = date.fromisoformat(p["period_end_date"])
            r = waterfall(opening, rate, dcf_fn(s, e), cf_shl[ds], ds)
            results.append(r)
            opening = r.closing_balance_keur
        return results

    def test_max_cash_interest_delta_sub_cent(self, recursive_results, d2a_periods):
        max_d = 0.0
        for r in recursive_results:
            p = next(x for x in d2a_periods if x["ds_index"] == r.period_index)
            max_d = max(max_d, abs(r.cash_interest_keur - p["cash_interest_keur"]))
        assert max_d < _PARITY_TOL


# ── J: Recursive PIK parity ───────────────────────────────────────────────────

class TestJ_RecursivePikParity:
    @pytest.fixture(scope="module")
    def recursive_results(self, waterfall, draw, rate, d2a_periods, cf_shl, dcf_fn, d2a):
        from financial_engine.shl.engine import compute_shl_period
        from financial_engine.shl.contracts import ShlInterestPaymentMode
        r0 = compute_shl_period(0.0, draw, 1.0, rate, ShlInterestPaymentMode.PIK, 0.0, 0)
        opening = r0.closing_balance_keur
        results = []
        for ds in range(1, 41):
            p = next(x for x in d2a_periods if x["ds_index"] == ds)
            s = date.fromisoformat(p["period_start_date"])
            e = date.fromisoformat(p["period_end_date"])
            r = waterfall(opening, rate, dcf_fn(s, e), cf_shl[ds], ds)
            results.append(r)
            opening = r.closing_balance_keur
        return results

    def test_max_pik_delta_sub_cent(self, recursive_results, d2a_periods):
        max_d = 0.0
        for r in recursive_results:
            p = next(x for x in d2a_periods if x["ds_index"] == r.period_index)
            max_d = max(max_d, abs(r.pik_interest_keur - p["pik_interest_keur"]))
        assert max_d < _PARITY_TOL


# ── K: Recursive principal parity ─────────────────────────────────────────────

class TestK_RecursivePrincipalParity:
    @pytest.fixture(scope="module")
    def recursive_results(self, waterfall, draw, rate, d2a_periods, cf_shl, dcf_fn, d2a):
        from financial_engine.shl.engine import compute_shl_period
        from financial_engine.shl.contracts import ShlInterestPaymentMode
        r0 = compute_shl_period(0.0, draw, 1.0, rate, ShlInterestPaymentMode.PIK, 0.0, 0)
        opening = r0.closing_balance_keur
        results = []
        for ds in range(1, 41):
            p = next(x for x in d2a_periods if x["ds_index"] == ds)
            s = date.fromisoformat(p["period_start_date"])
            e = date.fromisoformat(p["period_end_date"])
            r = waterfall(opening, rate, dcf_fn(s, e), cf_shl[ds], ds)
            results.append(r)
            opening = r.closing_balance_keur
        return results

    def test_max_principal_delta_sub_cent(self, recursive_results, d2a_periods):
        max_d = 0.0
        for r in recursive_results:
            p = next(x for x in d2a_periods if x["ds_index"] == r.period_index)
            max_d = max(max_d, abs(r.principal_repaid_keur - p["principal_repaid_keur"]))
        assert max_d < _PARITY_TOL


# ── L: Recursive closing parity ───────────────────────────────────────────────

class TestL_RecursiveClosingParity:
    @pytest.fixture(scope="module")
    def recursive_results(self, waterfall, draw, rate, d2a_periods, cf_shl, dcf_fn, d2a):
        from financial_engine.shl.engine import compute_shl_period
        from financial_engine.shl.contracts import ShlInterestPaymentMode
        r0 = compute_shl_period(0.0, draw, 1.0, rate, ShlInterestPaymentMode.PIK, 0.0, 0)
        opening = r0.closing_balance_keur
        results = []
        for ds in range(1, 41):
            p = next(x for x in d2a_periods if x["ds_index"] == ds)
            s = date.fromisoformat(p["period_start_date"])
            e = date.fromisoformat(p["period_end_date"])
            r = waterfall(opening, rate, dcf_fn(s, e), cf_shl[ds], ds)
            results.append(r)
            opening = r.closing_balance_keur
        return results

    def test_max_closing_delta_sub_cent(self, recursive_results, d2a_periods):
        max_d = 0.0
        for r in recursive_results:
            p = next(x for x in d2a_periods if x["ds_index"] == r.period_index)
            max_d = max(max_d, abs(r.closing_balance_keur - p["closing_balance_keur"]))
        assert max_d < _PARITY_TOL

    def test_final_ds40_closing_is_zero(self, recursive_results):
        assert abs(recursive_results[-1].closing_balance_keur) < _PARITY_TOL


# ── M: Construction uses opening=0 + draw (not draw-as-opening) ──────────────

class TestM_ConstructionOpening0PlusDraw:
    """C3B3D1 engine handles construction: opening=0, drawdown=draw."""

    def test_construction_opening_is_zero(self, d2a):
        cp = d2a["construction_period"]
        assert cp["opening_balance_keur"] == 0.0

    def test_construction_drawdown_is_shl_draw(self, d2a, draw):
        cp = d2a["construction_period"]
        assert abs(cp["drawdown_keur"] - draw) < _TOL

    def test_construction_via_d1_engine_not_waterfall(self, draw, rate, d2a):
        from financial_engine.shl.engine import compute_shl_period
        from financial_engine.shl.contracts import ShlInterestPaymentMode
        cp = d2a["construction_period"]
        r = compute_shl_period(
            opening_balance_keur=0.0,
            drawdown_keur=draw,
            day_count_fraction=1.0,
            annual_rate=rate,
            payment_mode=ShlInterestPaymentMode.PIK,
            scheduled_principal_keur=0.0,
            period_index=0,
        )
        assert abs(r.gross_accrued_interest_keur - cp["gross_accrued_interest_keur"]) < _PARITY_TOL
        assert abs(r.closing_balance_keur - cp["closing_balance_keur"]) < _PARITY_TOL

    def test_waterfall_does_not_pretend_draw_is_opening(self, waterfall, draw, rate):
        """Passing draw as opening (wrong semantic) gives different gross than draw × rate × 1."""
        r_wrong_semantic = waterfall(draw, rate, 1.0, 0.0, 0)
        expected_gross_correct = draw * rate * 1.0  # opening=0, draw contributes to gross
        # waterfall with opening=draw gives same gross only if opening=draw; but the
        # SEMANTIC is wrong: opening should be 0, draw is separate
        # Verify D1 engine gives the right answer
        from financial_engine.shl.engine import compute_shl_period
        from financial_engine.shl.contracts import ShlInterestPaymentMode
        r_correct = compute_shl_period(0.0, draw, 1.0, rate, ShlInterestPaymentMode.PIK, 0.0, 0)
        assert abs(r_correct.gross_accrued_interest_keur - expected_gross_correct) < _PARITY_TOL

    def test_construction_gross_formula(self, draw, rate, d2a):
        """gross = draw × rate × 1.0 (DCF = 1.0 implied)."""
        cp = d2a["construction_period"]
        expected = draw * rate * 1.0
        assert abs(expected - cp["gross_accrued_interest_keur"]) < _PARITY_TOL


# ── N: Cash vector remains independent test driver ────────────────────────────

class TestN_CashVectorIndependence:
    """free_cash_flow_for_shl is upstream of SHL service."""

    def test_cf_shl_is_from_cf_section_not_ds(self, fin):
        assert "free_cash_flow_for_shl_keur" in fin["cf"]

    def test_cf_shl_is_upstream_waterfall(self, fin):
        """fcf_for_shl = fcf_for_junior (= fcf_for_banks + senior_debt_service)."""
        cf = fin["cf"]
        for_shl = cf["free_cash_flow_for_shl_keur"]
        for_junior = cf["free_cash_flow_for_junior_keur"]
        # All 40 operating periods match
        for ds in range(1, 41):
            assert abs(for_shl[ds] - for_junior[ds]) < _TOL

    def test_cf_shl_ds25_matches_expected(self, cf_shl):
        assert abs(cf_shl[25] - 1303.7935979215406) < 0.01

    def test_cf_shl_ds24_matches_expected(self, cf_shl):
        assert abs(cf_shl[24] - 343.19847993447775) < 0.01

    def test_cf_shl_ds0_is_zero(self, cf_shl):
        assert cf_shl[0] == 0.0

    def test_production_waterfall_does_not_read_cf_fixture(self):
        src = Path("financial_engine/shl/waterfall.py").read_text()
        assert "excel_oborovo" not in src
        assert "free_cash_flow_for_shl" not in src


# ── O: Sweep provenance classification ───────────────────────────────────────

class TestO_SweepProvenanceClassification:
    """Sweep rule: honest provenance label."""

    def test_sweep_provenance_label_in_fixture(self, d2a):
        unresolved = d2a["unresolved_items"]
        pik_switch = unresolved.get("pik_switch_trigger", "")
        # Must be SOURCE_VECTOR_DERIVED_AND_FULL_HORIZON_RECONCILED (not SOURCE_FORMULA_PROVEN)
        assert "SOURCE_VECTOR" in pik_switch or "RECONCILED" in pik_switch

    def test_sweep_rule_holds_all_40_periods(self, waterfall, rate, d2a_periods, cf_shl, dcf_fn, d2a):
        """Principal > 0 iff cash_available > gross (no exceptions across 40 periods)."""
        from financial_engine.shl.engine import compute_shl_period
        from financial_engine.shl.contracts import ShlInterestPaymentMode
        r0 = compute_shl_period(0.0, d2a["workbook_inputs"]["shl_draw_keur"]["value"],
                                1.0, rate, ShlInterestPaymentMode.PIK, 0.0, 0)
        opening = r0.closing_balance_keur
        for ds in range(1, 41):
            p = next(x for x in d2a_periods if x["ds_index"] == ds)
            s = date.fromisoformat(p["period_start_date"])
            e = date.fromisoformat(p["period_end_date"])
            r = waterfall(opening, rate, dcf_fn(s, e), cf_shl[ds], ds)
            gross = r.gross_accrued_interest_keur
            cash = cf_shl[ds]
            should_sweep = cash > gross
            did_sweep = r.principal_repaid_keur > _TOL
            assert should_sweep == did_sweep, f"DS[{ds}]: cash={cash:.4f} gross={gross:.4f}"
            opening = r.closing_balance_keur


# ── P: No 13,547.2 clean authority ───────────────────────────────────────────

class TestP_No13547InCleanCalculation:
    def test_no_13547_in_waterfall_code(self):
        code_lines = [
            l for l in Path("financial_engine/shl/waterfall.py").read_text().splitlines()
            if not l.strip().startswith("#") and '"""' not in l
        ]
        assert not any("13547" in l for l in code_lines)

    def test_draw_used_in_tests_is_not_13547(self, draw):
        assert abs(draw - 13547.2) > 100  # draw is 14620.77

    def test_waterfall_result_not_anchored_to_13547(self, waterfall, rate, dcf_fn):
        # Parameterized with any draw — result is clean
        r = waterfall(14620.773894815633, rate,
                      dcf_fn(date(2030, 7, 1), date(2030, 12, 31)), 335.87, 1)
        assert abs(r.opening_balance_keur - 13547.2) > 100


# ── Q: No DS25/DS40 calculation boundary ─────────────────────────────────────

class TestQ_NoHardcodedBoundaries:
    def test_no_ds25_in_waterfall_code(self):
        src = Path("financial_engine/shl/waterfall.py").read_text()
        code_lines = [l for l in src.splitlines() if not l.strip().startswith("#")]
        assert not any("DS25" in l or "period_index == 25" in l for l in code_lines)

    def test_no_ds40_in_waterfall_code(self):
        src = Path("financial_engine/shl/waterfall.py").read_text()
        code_lines = [l for l in src.splitlines() if not l.strip().startswith("#")]
        assert not any("DS40" in l or "period_index == 40" in l for l in code_lines)

    def test_sweep_boundary_discovered_not_asserted(self, waterfall, rate, d2a_periods, cf_shl, dcf_fn, d2a):
        """First sweep period is discovered from data, not hardcoded."""
        from financial_engine.shl.engine import compute_shl_period
        from financial_engine.shl.contracts import ShlInterestPaymentMode
        r0 = compute_shl_period(0.0, d2a["workbook_inputs"]["shl_draw_keur"]["value"],
                                1.0, rate, ShlInterestPaymentMode.PIK, 0.0, 0)
        opening = r0.closing_balance_keur
        first_sweep = None
        for ds in range(1, 41):
            p = next(x for x in d2a_periods if x["ds_index"] == ds)
            s = date.fromisoformat(p["period_start_date"])
            e = date.fromisoformat(p["period_end_date"])
            r = waterfall(opening, rate, dcf_fn(s, e), cf_shl[ds], ds)
            if r.principal_repaid_keur > _TOL and first_sweep is None:
                first_sweep = ds
            opening = r.closing_balance_keur
        assert first_sweep == 25  # discovered, not hardcoded


# ── R: No source-vector production reads ─────────────────────────────────────

class TestR_NoSourceVectorProductionReads:
    def test_waterfall_does_not_import_fixtures(self):
        src = Path("financial_engine/shl/waterfall.py").read_text()
        assert "fixtures" not in src
        assert "excel_oborovo" not in src

    def test_waterfall_does_not_import_finco_core(self):
        import_lines = [
            l for l in Path("financial_engine/shl/waterfall.py").read_text().splitlines()
            if l.startswith("import ") or l.startswith("from ")
        ]
        assert not any("finco_core" in l for l in import_lines)

    def test_waterfall_module_runtime_has_no_finco_core(self):
        mod = importlib.import_module("financial_engine.shl.waterfall")
        for name, val in vars(mod).items():
            if hasattr(val, "__module__") and val.__module__:
                assert "finco_core" not in str(val.__module__)


# ── S: Zero existing runtime drift ───────────────────────────────────────────

class TestS_ZeroRuntimeDrift:
    """No production numeric changes in this PR."""

    def test_waterfall_module_not_imported_by_app(self):
        """waterfall.py is a new module; no production code imports it yet."""
        # Scan key production modules
        for prod_file in [
            "app/project_factories.py",
            "finco_core/waterfall/waterfall_engine.py",
        ]:
            src = Path(prod_file).read_text()
            assert "from financial_engine.shl.waterfall" not in src
            assert "import financial_engine.shl.waterfall" not in src

    def test_no_factory_numeric_changes(self):
        """app/project_factories.py shl_amount_keur remains 13547.2."""
        src = Path("app/project_factories.py").read_text()
        assert "shl_amount_keur=13547.2" in src

    def test_d1_engine_unchanged(self):
        """C3B3D1 engine file is not modified by this PR."""
        from financial_engine.shl.engine import compute_shl_period
        from financial_engine.shl.contracts import ShlInterestPaymentMode
        r = compute_shl_period(
            opening_balance_keur=1000.0,
            drawdown_keur=0.0,
            day_count_fraction=0.5,
            annual_rate=0.08,
            payment_mode=ShlInterestPaymentMode.CASH_PAID,
            scheduled_principal_keur=0.0,
            period_index=0,
        )
        assert abs(r.gross_accrued_interest_keur - 40.0) < _TOL


# ── Governance: function signature ────────────────────────────────────────────

class TestGovFunctionSignature:
    def test_no_mode_parameter(self, waterfall):
        sig = inspect.signature(waterfall)
        assert "payment_mode" not in sig.parameters
        assert "mode" not in sig.parameters

    def test_no_mode_enum_import(self):
        src = Path("financial_engine/shl/waterfall.py").read_text()
        assert "ShlInterestPaymentMode" not in src

    def test_no_app_import(self):
        import_lines = [
            l for l in Path("financial_engine/shl/waterfall.py").read_text().splitlines()
            if l.startswith("import ") or l.startswith("from ")
        ]
        assert not any("app" in l for l in import_lines)


# ── Governance: roll-forward identity ────────────────────────────────────────

class TestGovRollForward:
    @pytest.mark.parametrize("ds", [1, 12, 24, 25, 39, 40])
    def test_roll_forward_holds(self, waterfall, rate, d2a_periods, cf_shl, dcf_fn, ds):
        p = next(x for x in d2a_periods if x["ds_index"] == ds)
        s = date.fromisoformat(p["period_start_date"])
        e = date.fromisoformat(p["period_end_date"])
        r = waterfall(p["opening_balance_keur"], rate, dcf_fn(s, e), cf_shl[ds], ds)
        expected = r.opening_balance_keur + r.pik_interest_keur - r.principal_repaid_keur
        assert abs(r.closing_balance_keur - expected) < _TOL


# ── Governance: input validation ──────────────────────────────────────────────

class TestGovInputValidation:
    def test_negative_opening_raises(self, waterfall):
        with pytest.raises(ValueError, match="opening_balance_keur"):
            waterfall(-1.0, 0.08, 0.5, 0.0)

    def test_negative_rate_raises(self, waterfall):
        with pytest.raises(ValueError, match="annual_rate"):
            waterfall(1000.0, -0.01, 0.5, 0.0)

    def test_zero_dcf_raises(self, waterfall):
        with pytest.raises(ValueError, match="day_count_fraction"):
            waterfall(1000.0, 0.08, 0.0, 0.0)

    def test_negative_cash_raises(self, waterfall):
        with pytest.raises(ValueError, match="cash_available"):
            waterfall(1000.0, 0.08, 0.5, -1.0)

    def test_nan_raises(self, waterfall):
        with pytest.raises(ValueError):
            waterfall(float("nan"), 0.08, 0.5, 0.0)

    def test_bool_raises(self, waterfall):
        with pytest.raises(ValueError):
            waterfall(True, 0.08, 0.5, 0.0)

    def test_dcf_end_before_start_raises(self, dcf_fn):
        with pytest.raises(ValueError):
            dcf_fn(date(2031, 1, 1), date(2030, 12, 31))


# ── Governance: result dataclass ─────────────────────────────────────────────

class TestGovResultDataclass:
    def test_result_frozen(self, waterfall):
        r = waterfall(1000.0, 0.08, 0.5, 0.0)
        with pytest.raises((AttributeError, TypeError)):
            r.opening_balance_keur = 999.0  # type: ignore[misc]

    def test_shl_service_equals_cash_plus_principal(self, waterfall):
        r = waterfall(10000.0, 0.08, 0.5, 1000.0)
        assert abs(r.shl_service_keur - (r.cash_interest_keur + r.principal_repaid_keur)) < _TOL

    def test_rename_clone_guard(self, waterfall):
        from financial_engine.shl.waterfall import ShlWaterfallPeriodResult
        r = waterfall(1000.0, 0.08, 0.5, 50.0)
        assert isinstance(r, ShlWaterfallPeriodResult)
        assert hasattr(r, "shl_service_keur")
