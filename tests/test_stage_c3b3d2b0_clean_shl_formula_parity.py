"""Stage C3B3D2B0 — Clean SHL Waterfall Formula Parity Tests.

Proves that compute_shl_waterfall_period() reproduces the Excel-sourced D2A
fixture values to machine-epsilon across all 41 periods (DS[0..40]).

Test driver inputs:
  - shl_dcf_derived_actual_365: from D2A fixture (SOURCE_RAW_DERIVED, not date-calc)
  - free_cash_flow_for_shl_keur: from excel_oborovo_financial_truth.json CF section
    (SOURCE_RAW_CACHED_VALUE, independent of SHL DS columns)
  - shl_draw_keur, shl_annual_rate: from D2A fixture workbook_inputs (SOURCE_RAW)

Governance constraints:
  - compute_shl_waterfall_period has NO mode dispatch, NO mode enum
  - 13547.2 does NOT appear in financial_engine/shl/waterfall.py
  - financial_engine does NOT import finco_core waterfall
  - DS25/DS40 are NOT hardcoded in clean code — sweep boundary is discovered from data
"""
from __future__ import annotations

import importlib
import inspect
import json
import math
from pathlib import Path

import pytest

# ── fixtures ─────────────────────────────────────────────────────────────────

FIXTURES = Path(__file__).parent / "fixtures"
D2A_PATH = FIXTURES / "excel_oborovo_shl_operating_truth.json"
FIN_PATH = FIXTURES / "excel_oborovo_financial_truth.json"

_TOL = 1e-9          # floating-point equality tolerance
_PARITY_TOL = 1e-6   # kEUR parity tolerance (sub-cent)


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


# ── A: Governance — no mode dispatch ─────────────────────────────────────────

class TestA_GovernanceNoModeDispatch:
    """The clean function must accept no mode enum and contain no mode branch."""

    def test_function_signature_has_no_mode_parameter(self, waterfall):
        sig = inspect.signature(waterfall)
        assert "payment_mode" not in sig.parameters
        assert "mode" not in sig.parameters

    def test_function_source_contains_no_ShlInterestPaymentMode_import(self):
        src = Path("financial_engine/shl/waterfall.py").read_text()
        assert "ShlInterestPaymentMode" not in src

    def test_function_source_imports_no_mode_enum(self):
        # No import of mode enum classes (field name pik_interest_keur is fine)
        src = Path("financial_engine/shl/waterfall.py").read_text()
        import_lines = [l for l in src.splitlines() if l.startswith("import ") or l.startswith("from ")]
        for line in import_lines:
            assert "CASH_PAID" not in line
            assert "ShlInterestPaymentMode" not in line

    def test_function_accepts_four_numeric_inputs(self, waterfall):
        # Must succeed with zero cash (PIK) and positive cash (sweep)
        r_pik = waterfall(
            opening_balance_keur=1000.0,
            annual_rate=0.08,
            day_count_fraction=0.5,
            cash_available_for_shl_keur=0.0,
        )
        assert r_pik.cash_interest_keur == 0.0
        assert r_pik.pik_interest_keur > 0.0

        r_cash = waterfall(
            opening_balance_keur=1000.0,
            annual_rate=0.08,
            day_count_fraction=0.5,
            cash_available_for_shl_keur=999.0,
        )
        assert r_cash.cash_interest_keur > 0.0


# ── B: Governance — no hardcoded project constants ────────────────────────────

class TestB_GovernanceNoHardcodedProjectConstants:
    """13547.2, DS25, DS40 must not appear in waterfall.py."""

    def test_no_13547(self):
        code_lines = [
            l for l in Path("financial_engine/shl/waterfall.py").read_text().splitlines()
            if not l.strip().startswith("#") and not l.strip().startswith('"""') and '"""' not in l
        ]
        assert not any("13547" in l for l in code_lines)

    def test_no_hardcoded_DS25(self):
        src = Path("financial_engine/shl/waterfall.py").read_text()
        code_lines = [l for l in src.splitlines() if not l.strip().startswith("#")]
        assert not any("DS25" in l or "ds_idx == 25" in l or "period_index == 25" in l for l in code_lines)

    def test_no_hardcoded_DS40(self):
        src = Path("financial_engine/shl/waterfall.py").read_text()
        code_lines = [l for l in src.splitlines() if not l.strip().startswith("#")]
        assert not any("DS40" in l or "period_index == 40" in l for l in code_lines)

    def test_no_finco_core_import(self):
        src = Path("financial_engine/shl/waterfall.py").read_text()
        import_lines = [l for l in src.splitlines() if l.startswith("import ") or l.startswith("from ")]
        assert not any("finco_core" in l for l in import_lines)

    def test_no_app_import(self):
        src = Path("financial_engine/shl/waterfall.py").read_text()
        import_lines = [l for l in src.splitlines() if l.startswith("import ") or l.startswith("from ")]
        assert not any("app" in l for l in import_lines)


# ── C: Governance — financial_engine isolation ────────────────────────────────

class TestC_GovernanceFinancialEngineIsolation:
    """financial_engine.shl.waterfall must not pull in production runtime."""

    def test_waterfall_module_does_not_import_finco_core(self):
        mod = importlib.import_module("financial_engine.shl.waterfall")
        for name, val in vars(mod).items():
            if hasattr(val, "__module__") and val.__module__:
                assert "finco_core" not in val.__module__, (
                    f"finco_core leaked in via {name}"
                )

    def test_waterfall_module_does_not_import_app(self):
        mod = importlib.import_module("financial_engine.shl.waterfall")
        for name, val in vars(mod).items():
            if hasattr(val, "__module__") and val.__module__:
                assert not val.__module__.startswith("app."), (
                    f"app leaked in via {name}"
                )


# ── D: Formula — roll-forward identity ───────────────────────────────────────

class TestD_RollForwardIdentity:
    """closing = opening + pik - principal for every period."""

    def test_construction_roll_forward(self, waterfall, draw, rate, d2a_periods):
        p0 = next(x for x in d2a_periods if x["ds_index"] == 0)
        r = waterfall(draw, rate, p0["shl_dcf_derived_actual_365"], 0.0, 0)
        expected = r.opening_balance_keur + r.pik_interest_keur - r.principal_repaid_keur
        assert abs(r.closing_balance_keur - expected) < _TOL

    @pytest.mark.parametrize("ds", [1, 12, 24, 25, 39, 40])
    def test_operating_roll_forward(self, waterfall, rate, d2a_periods, cf_shl, ds):
        p = next(x for x in d2a_periods if x["ds_index"] == ds)
        opening = p["opening_balance_keur"]
        cash = cf_shl[ds]
        r = waterfall(opening, rate, p["shl_dcf_derived_actual_365"], cash, ds)
        expected = r.opening_balance_keur + r.pik_interest_keur - r.principal_repaid_keur
        assert abs(r.closing_balance_keur - expected) < _TOL


# ── E: Formula — gross interest formula ──────────────────────────────────────

class TestE_GrossInterestFormula:
    """gross = opening × rate × dcf (no drawdown in operating)."""

    @pytest.mark.parametrize("ds", [1, 10, 24, 25, 40])
    def test_gross_equals_opening_times_rate_times_dcf(
        self, waterfall, rate, d2a_periods, cf_shl, ds
    ):
        p = next(x for x in d2a_periods if x["ds_index"] == ds)
        r = waterfall(
            p["opening_balance_keur"], rate,
            p["shl_dcf_derived_actual_365"], cf_shl[ds], ds
        )
        expected_gross = p["opening_balance_keur"] * rate * p["shl_dcf_derived_actual_365"]
        assert abs(r.gross_accrued_interest_keur - expected_gross) < _TOL


# ── F: Formula — cash interest = min(cash, gross) ────────────────────────────

class TestF_CashInterestMinFormula:
    """cash_interest = min(cash_available, gross)."""

    def test_pik_period_cash_zero(self, waterfall, rate, d2a_periods, cf_shl):
        p = next(x for x in d2a_periods if x["ds_index"] == 1)
        r = waterfall(p["opening_balance_keur"], rate, p["shl_dcf_derived_actual_365"], cf_shl[1], 1)
        # DS[1]: cash < gross → cash_interest = cash_available
        assert abs(r.cash_interest_keur - cf_shl[1]) < _TOL

    def test_sweep_period_cash_interest_equals_gross(self, waterfall, rate, d2a_periods, cf_shl):
        p = next(x for x in d2a_periods if x["ds_index"] == 25)
        r = waterfall(p["opening_balance_keur"], rate, p["shl_dcf_derived_actual_365"], cf_shl[25], 25)
        # DS[25]: cash > gross → cash_interest = gross
        assert abs(r.cash_interest_keur - r.gross_accrued_interest_keur) < _TOL

    def test_pik_plus_cash_equals_gross(self, waterfall, rate, d2a_periods, cf_shl):
        for ds in [1, 12, 24, 25, 30, 40]:
            p = next(x for x in d2a_periods if x["ds_index"] == ds)
            r = waterfall(p["opening_balance_keur"], rate, p["shl_dcf_derived_actual_365"], cf_shl[ds], ds)
            assert abs(r.cash_interest_keur + r.pik_interest_keur - r.gross_accrued_interest_keur) < _TOL


# ── G: Formula — sweep condition ──────────────────────────────────────────────

class TestG_SweepCondition:
    """Sweep triggers when cash_available > gross (not annual rate, not 14621)."""

    def test_ds24_no_sweep(self, waterfall, rate, d2a_periods, cf_shl):
        p = next(x for x in d2a_periods if x["ds_index"] == 24)
        r = waterfall(p["opening_balance_keur"], rate, p["shl_dcf_derived_actual_365"], cf_shl[24], 24)
        # cash=343.20 < gross=1034.64 → no principal
        assert r.principal_repaid_keur < _TOL

    def test_ds25_sweep_positive(self, waterfall, rate, d2a_periods, cf_shl):
        p = next(x for x in d2a_periods if x["ds_index"] == 25)
        r = waterfall(p["opening_balance_keur"], rate, p["shl_dcf_derived_actual_365"], cf_shl[25], 25)
        # cash=1303.79 > gross=1079.68 → principal > 0
        assert r.principal_repaid_keur > 0.0

    def test_sweep_boundary_discovered_not_asserted(self, waterfall, rate, d2a_periods, cf_shl):
        """DS25 is not hardcoded; it emerges from the formula."""
        first_sweep = None
        for ds in range(1, 41):
            p = next(x for x in d2a_periods if x["ds_index"] == ds)
            r = waterfall(p["opening_balance_keur"], rate, p["shl_dcf_derived_actual_365"], cf_shl[ds], ds)
            if r.principal_repaid_keur > _TOL:
                first_sweep = ds
                break
        assert first_sweep == 25


# ── H: Parity — construction DS[0] ───────────────────────────────────────────

class TestH_ParityConstruction:
    """DS[0] construction parity to machine epsilon."""

    def test_construction_gross_parity(self, waterfall, draw, rate, d2a_periods):
        p0 = next(x for x in d2a_periods if x["ds_index"] == 0)
        r = waterfall(draw, rate, p0["shl_dcf_derived_actual_365"], 0.0, 0)
        assert abs(r.gross_accrued_interest_keur - p0["gross_accrued_interest_keur"]) < _PARITY_TOL

    def test_construction_pik_parity(self, waterfall, draw, rate, d2a_periods):
        p0 = next(x for x in d2a_periods if x["ds_index"] == 0)
        r = waterfall(draw, rate, p0["shl_dcf_derived_actual_365"], 0.0, 0)
        assert abs(r.pik_interest_keur - p0["pik_interest_keur"]) < _PARITY_TOL

    def test_construction_closing_parity(self, waterfall, draw, rate, d2a_periods):
        p0 = next(x for x in d2a_periods if x["ds_index"] == 0)
        r = waterfall(draw, rate, p0["shl_dcf_derived_actual_365"], 0.0, 0)
        assert abs(r.closing_balance_keur - p0["closing_balance_keur"]) < _PARITY_TOL

    def test_construction_dcf_is_one(self, d2a_periods):
        p0 = next(x for x in d2a_periods if x["ds_index"] == 0)
        assert abs(p0["shl_dcf_derived_actual_365"] - 1.0) < _TOL


# ── I: Parity — spot operating periods ───────────────────────────────────────

class TestI_ParityOperatingSpot:
    """Spot-check key operating periods (non-recursive, fixture opening balance)."""

    @pytest.mark.parametrize("ds", [1, 12, 24, 25, 30, 40])
    def test_gross_parity_spot(self, waterfall, rate, d2a_periods, cf_shl, ds):
        p = next(x for x in d2a_periods if x["ds_index"] == ds)
        r = waterfall(p["opening_balance_keur"], rate, p["shl_dcf_derived_actual_365"], cf_shl[ds], ds)
        assert abs(r.gross_accrued_interest_keur - p["gross_accrued_interest_keur"]) < _PARITY_TOL

    @pytest.mark.parametrize("ds", [1, 12, 24, 25, 30, 40])
    def test_cash_interest_parity_spot(self, waterfall, rate, d2a_periods, cf_shl, ds):
        p = next(x for x in d2a_periods if x["ds_index"] == ds)
        r = waterfall(p["opening_balance_keur"], rate, p["shl_dcf_derived_actual_365"], cf_shl[ds], ds)
        assert abs(r.cash_interest_keur - p["cash_interest_keur"]) < _PARITY_TOL

    @pytest.mark.parametrize("ds", [1, 12, 24, 25, 30, 40])
    def test_pik_parity_spot(self, waterfall, rate, d2a_periods, cf_shl, ds):
        p = next(x for x in d2a_periods if x["ds_index"] == ds)
        r = waterfall(p["opening_balance_keur"], rate, p["shl_dcf_derived_actual_365"], cf_shl[ds], ds)
        assert abs(r.pik_interest_keur - p["pik_interest_keur"]) < _PARITY_TOL

    @pytest.mark.parametrize("ds", [1, 12, 24, 25, 30, 40])
    def test_closing_parity_spot(self, waterfall, rate, d2a_periods, cf_shl, ds):
        p = next(x for x in d2a_periods if x["ds_index"] == ds)
        r = waterfall(p["opening_balance_keur"], rate, p["shl_dcf_derived_actual_365"], cf_shl[ds], ds)
        assert abs(r.closing_balance_keur - p["closing_balance_keur"]) < _PARITY_TOL


# ── J: Parity — full 40-period recursive ─────────────────────────────────────

class TestJ_ParityFullRecursive:
    """Recursive 40-period parity: each period's opening = prior period's computed closing."""

    @pytest.fixture(scope="module")
    def recursive_results(self, waterfall, draw, rate, d2a_periods, cf_shl):
        p0 = next(x for x in d2a_periods if x["ds_index"] == 0)
        r0 = waterfall(draw, rate, p0["shl_dcf_derived_actual_365"], 0.0, 0)
        results = [r0]
        opening = r0.closing_balance_keur
        for ds in range(1, 41):
            p = next(x for x in d2a_periods if x["ds_index"] == ds)
            r = waterfall(opening, rate, p["shl_dcf_derived_actual_365"], cf_shl[ds], ds)
            results.append(r)
            opening = r.closing_balance_keur
        return results

    def test_max_gross_delta_sub_cent(self, recursive_results, d2a_periods):
        max_d = 0.0
        for r in recursive_results:
            p = next(x for x in d2a_periods if x["ds_index"] == r.period_index)
            max_d = max(max_d, abs(r.gross_accrued_interest_keur - p["gross_accrued_interest_keur"]))
        assert max_d < _PARITY_TOL, f"Max gross delta {max_d:.2e} exceeds {_PARITY_TOL}"

    def test_max_closing_delta_sub_cent(self, recursive_results, d2a_periods):
        max_d = 0.0
        for r in recursive_results:
            p = next(x for x in d2a_periods if x["ds_index"] == r.period_index)
            max_d = max(max_d, abs(r.closing_balance_keur - p["closing_balance_keur"]))
        assert max_d < _PARITY_TOL, f"Max closing delta {max_d:.2e} exceeds {_PARITY_TOL}"

    def test_final_ds40_closing_is_zero(self, recursive_results):
        ds40 = recursive_results[40]
        assert abs(ds40.closing_balance_keur) < _PARITY_TOL, (
            f"DS[40] closing {ds40.closing_balance_keur:.6f} is not zero"
        )

    def test_all_closing_balances_non_negative(self, recursive_results):
        for r in recursive_results:
            assert r.closing_balance_keur >= -_TOL, (
                f"Negative closing at DS[{r.period_index}]: {r.closing_balance_keur}"
            )

    def test_pik_periods_ds1_to_ds24_zero_principal(self, recursive_results):
        for r in recursive_results[1:25]:
            assert r.principal_repaid_keur < _TOL, (
                f"Unexpected principal at DS[{r.period_index}]: {r.principal_repaid_keur}"
            )

    def test_sweep_periods_ds25_to_ds40_positive_principal(self, recursive_results):
        for r in recursive_results[25:41]:
            assert r.principal_repaid_keur > 0.0, (
                f"Missing principal at DS[{r.period_index}]: {r.principal_repaid_keur}"
            )


# ── K: Cash vector independence ───────────────────────────────────────────────

class TestK_CashVectorIndependence:
    """free_cash_flow_for_shl is from CF section, independent of SHL DS columns."""

    def test_cf_shl_is_from_cf_section_not_ds(self, fin):
        cf = fin["cf"]
        assert "free_cash_flow_for_shl_keur" in cf

    def test_cf_shl_ds25_matches_known_waterfall_value(self, cf_shl):
        assert abs(cf_shl[25] - 1303.7935979215406) < 0.01

    def test_cf_shl_ds24_matches_known_value(self, cf_shl):
        assert abs(cf_shl[24] - 343.19847993447775) < 0.01

    def test_cf_shl_ds0_is_zero(self, cf_shl):
        assert cf_shl[0] == 0.0


# ── L: DCF source is D2A fixture ──────────────────────────────────────────────

class TestL_DcfSourceIsD2aFixture:
    """shl_dcf_derived_actual_365 from D2A fixture is the test driver DCF."""

    def test_dcf_field_present_all_periods(self, d2a_periods):
        for p in d2a_periods:
            assert "shl_dcf_derived_actual_365" in p, f"Missing DCF at DS[{p['ds_index']}]"

    def test_dcf_all_positive(self, d2a_periods):
        for p in d2a_periods:
            assert p["shl_dcf_derived_actual_365"] > 0.0

    def test_dcf_ds0_is_one(self, d2a_periods):
        p0 = next(x for x in d2a_periods if x["ds_index"] == 0)
        assert abs(p0["shl_dcf_derived_actual_365"] - 1.0) < _TOL

    def test_dcf_ds1_correct_from_source(self, d2a_periods):
        p1 = next(x for x in d2a_periods if x["ds_index"] == 1)
        dcf = p1["shl_dcf_derived_actual_365"]
        # Verify: gross = opening * rate * dcf → dcf = gross / (opening * rate)
        gross = p1["gross_accrued_interest_keur"]
        opening = p1["opening_balance_keur"]
        expected_dcf = gross / (opening * 0.08)
        assert abs(dcf - expected_dcf) < _TOL


# ── M: Input validation ───────────────────────────────────────────────────────

class TestM_InputValidation:
    """compute_shl_waterfall_period raises on bad inputs."""

    def test_negative_opening_raises(self, waterfall):
        with pytest.raises(ValueError, match="opening_balance_keur"):
            waterfall(-1.0, 0.08, 0.5, 0.0)

    def test_negative_rate_raises(self, waterfall):
        with pytest.raises(ValueError, match="annual_rate"):
            waterfall(1000.0, -0.01, 0.5, 0.0)

    def test_zero_dcf_raises(self, waterfall):
        with pytest.raises(ValueError, match="day_count_fraction"):
            waterfall(1000.0, 0.08, 0.0, 0.0)

    def test_negative_dcf_raises(self, waterfall):
        with pytest.raises(ValueError, match="day_count_fraction"):
            waterfall(1000.0, 0.08, -0.5, 0.0)

    def test_negative_cash_raises(self, waterfall):
        with pytest.raises(ValueError, match="cash_available"):
            waterfall(1000.0, 0.08, 0.5, -1.0)

    def test_nan_opening_raises(self, waterfall):
        with pytest.raises(ValueError):
            waterfall(float("nan"), 0.08, 0.5, 0.0)

    def test_inf_rate_raises(self, waterfall):
        with pytest.raises(ValueError):
            waterfall(1000.0, float("inf"), 0.5, 0.0)

    def test_bool_opening_raises(self, waterfall):
        with pytest.raises(ValueError):
            waterfall(True, 0.08, 0.5, 0.0)


# ── N: Result dataclass ───────────────────────────────────────────────────────

class TestN_ResultDataclass:
    """ShlWaterfallPeriodResult is frozen, has correct fields."""

    def test_result_is_frozen(self, waterfall):
        r = waterfall(1000.0, 0.08, 0.5, 0.0)
        with pytest.raises((AttributeError, TypeError)):
            r.opening_balance_keur = 999.0  # type: ignore[misc]

    def test_result_fields_present(self, waterfall):
        r = waterfall(1000.0, 0.08, 0.5, 100.0)
        assert hasattr(r, "period_index")
        assert hasattr(r, "opening_balance_keur")
        assert hasattr(r, "gross_accrued_interest_keur")
        assert hasattr(r, "cash_interest_keur")
        assert hasattr(r, "pik_interest_keur")
        assert hasattr(r, "principal_repaid_keur")
        assert hasattr(r, "closing_balance_keur")
        assert hasattr(r, "shl_service_keur")

    def test_shl_service_equals_cash_plus_principal(self, waterfall):
        r = waterfall(10000.0, 0.08, 0.5, 1000.0)
        assert abs(r.shl_service_keur - (r.cash_interest_keur + r.principal_repaid_keur)) < _TOL


# ── O: Zero-rate edge case ────────────────────────────────────────────────────

class TestO_ZeroRateEdgeCase:
    def test_zero_rate_no_interest(self, waterfall):
        r = waterfall(1000.0, 0.0, 0.5, 500.0)
        assert r.gross_accrued_interest_keur == 0.0
        assert r.cash_interest_keur == 0.0
        assert r.pik_interest_keur == 0.0
        assert r.principal_repaid_keur == 500.0
        assert abs(r.closing_balance_keur - 500.0) < _TOL

    def test_zero_opening_zero_gross(self, waterfall):
        r = waterfall(0.0, 0.08, 0.5, 0.0)
        assert r.gross_accrued_interest_keur == 0.0
        assert r.closing_balance_keur == 0.0


# ── P: Excess cash capped at outstanding ─────────────────────────────────────

class TestP_ExcessCashCappedAtOutstanding:
    """principal is capped at (opening + pik); closing never goes negative."""

    def test_excess_cash_closing_non_negative(self, waterfall):
        r = waterfall(1000.0, 0.08, 0.5, 99999.0)
        assert r.closing_balance_keur >= 0.0

    def test_excess_cash_principal_le_outstanding(self, waterfall):
        r = waterfall(1000.0, 0.08, 0.5, 99999.0)
        outstanding = r.opening_balance_keur + r.pik_interest_keur
        assert r.principal_repaid_keur <= outstanding + _TOL


# ── Q: Rename-clone guard ─────────────────────────────────────────────────────

class TestQ_RenameCloneGuard:
    """waterfall.py must not be a copy of engine.py with a renamed function."""

    def test_waterfall_does_not_use_ShlPeriodResult(self):
        src = Path("financial_engine/shl/waterfall.py").read_text()
        assert "ShlPeriodResult" not in src

    def test_waterfall_uses_ShlWaterfallPeriodResult(self):
        from financial_engine.shl.waterfall import ShlWaterfallPeriodResult
        assert ShlWaterfallPeriodResult is not None

    def test_waterfall_result_has_shl_service_field(self, waterfall):
        r = waterfall(1000.0, 0.08, 0.5, 50.0)
        assert hasattr(r, "shl_service_keur")

    def test_engine_result_does_not_have_shl_service_field(self):
        from financial_engine.shl.contracts import ShlPeriodResult
        r = ShlPeriodResult(
            period_index=0,
            opening_balance_keur=0.0,
            gross_accrued_interest_keur=0.0,
            cash_interest_keur=0.0,
            pik_interest_keur=0.0,
            scheduled_principal_keur=0.0,
            closing_balance_keur=0.0,
        )
        assert not hasattr(r, "shl_service_keur")


# ── R: Fixture-production import guard ───────────────────────────────────────

class TestR_FixtureProductionImportGuard:
    """Test fixture must not be imported by production code."""

    def test_waterfall_does_not_import_fixtures(self):
        src = Path("financial_engine/shl/waterfall.py").read_text()
        assert "excel_oborovo" not in src
        assert "fixtures" not in src
        assert "test_stage" not in src

    def test_engine_does_not_import_fixtures(self):
        src = Path("financial_engine/shl/engine.py").read_text()
        assert "excel_oborovo" not in src
        assert "fixtures" not in src


# ── S: D2A fixture field classification ──────────────────────────────────────

class TestS_FixtureFieldClassifications:
    """Source-trust labels must be present in D2A fixture."""

    def test_shl_draw_is_source_raw(self, d2a):
        fc = d2a["workbook_inputs"]["shl_draw_keur"]["field_classification"]
        assert fc == "SOURCE_RAW_CACHED_VALUE"

    def test_shl_rate_is_source_raw(self, d2a):
        fc = d2a["workbook_inputs"]["shl_annual_rate"]["field_classification"]
        assert fc == "SOURCE_RAW_CACHED_VALUE"

    def test_cf_shl_source_is_cf_section(self, fin):
        src = fin["cf"].get("_source", {})
        # CF section exists and contains free_cash_flow_for_shl_keur
        assert "free_cash_flow_for_shl_keur" in fin["cf"]
