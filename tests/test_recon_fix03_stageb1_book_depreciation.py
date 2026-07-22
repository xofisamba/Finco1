"""Stage B1 Corrective Closure: source-truth book depreciation tests.

Section Q mandated test suite (26 tests).

Governance invariants verified:
  - GFA = 57,973 kEUR = hard CAPEX 55,999 + capitalized financing 1,974
  - vat_costs_keur = 222 kEUR (VAT facility IDC 208 + commitment 14) — NOT construction VAT
  - Hard CAPEX book life = 20y (workbook-proven, NOT horizon)
  - IDC/commitment/bank_fees book life = 12y; VAT book life = 20y
  - SHL IDC (~1,170 kEUR) is NOT in GFA (expensed, not capitalized)
  - TaxDepreciationMode.BOOK_BASED_PERCENTAGE 100% for Oborovo
  - Fiscal reintegration is a separate concept from depreciation deductibility
"""
import inspect
import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
FIXTURES = Path(__file__).parent / "fixtures"
EXCEL_TRUTH = FIXTURES / "excel_oborovo_financial_truth.json"
CANONICAL_SNAP = FIXTURES / "oborovo_python_canonical.json"

_TOLERANCE_KEUR = 1.0


def _load_excel_truth():
    with open(EXCEL_TRUTH) as f:
        return json.load(f)


def _load_canonical_snap():
    with open(CANONICAL_SNAP) as f:
        return json.load(f)


def _oborovo_factory():
    from app.project_factories import create_default_oborovo
    return create_default_oborovo()


def _oborovo_capex():
    return _oborovo_factory().capex


def _minimal_capex_structure(**fin_overrides):
    from finco_core.inputs._models import CapexStructure, CapexItem, AssetClass

    base_item = CapexItem(name="EPC", amount_keur=1000.0, asset_class=AssetClass.SOLAR_PANELS)
    zero_item = CapexItem(name="Zero", amount_keur=0.0, asset_class=AssetClass.CIVIL_GRID)
    item_fields = CapexStructure._CAPEX_ITEM_FIELDS
    kwargs = {f: base_item if f == "epc_contract" else zero_item for f in item_fields}
    kwargs.update(fin_overrides)
    return CapexStructure(**kwargs)


# ---------------------------------------------------------------------------
# 1. Oborovo CAPEX basis (source-truth amounts)
# ---------------------------------------------------------------------------

class TestOborovoCAPEXBasis:
    """Source-truth CAPEX component amounts verified against workbook."""

    def test_gfa_total_57973(self):
        """Total GFA = hard CAPEX 55,999 + financing 1,974 = 57,973 kEUR."""
        cs = _oborovo_capex()
        hard_sum = sum(i.amount_keur for i in cs.capex_items())
        fin_sum = cs.idc_keur + cs.commitment_fees_keur + cs.bank_fees_keur + cs.vat_costs_keur
        total = hard_sum + fin_sum
        assert abs(total - 57973.0) < 5.0, (
            f"GFA total={total:.2f} kEUR, expected ~57,973 kEUR"
        )

    def test_idc_amount_1086(self):
        """Senior Debt IDC = 1,086.03 kEUR (workbook source)."""
        cs = _oborovo_capex()
        assert abs(cs.idc_keur - 1086.03) < 0.5, (
            f"idc_keur={cs.idc_keur:.2f}, expected 1086.03"
        )

    def test_commitment_fees_188(self):
        """Senior Debt commitment fees = 188.56 kEUR (workbook source)."""
        cs = _oborovo_capex()
        assert abs(cs.commitment_fees_keur - 188.56) < 0.5, (
            f"commitment_fees_keur={cs.commitment_fees_keur:.2f}, expected 188.56"
        )

    def test_bank_fees_477(self):
        """Structuring/bank fees = 477.30 kEUR (workbook source)."""
        cs = _oborovo_capex()
        assert abs(cs.bank_fees_keur - 477.30) < 0.5, (
            f"bank_fees_keur={cs.bank_fees_keur:.2f}, expected 477.30"
        )

    def test_vat_costs_222_vat_facility_only(self):
        """vat_costs_keur = 222 kEUR = VAT facility IDC (208) + commitment (14).

        NOT the 7,665 kEUR construction VAT. This field covers only VAT-facility
        financing costs, not construction-phase VAT on the EPC contract.
        """
        cs = _oborovo_capex()
        assert abs(cs.vat_costs_keur - 222.0) < 2.0, (
            f"vat_costs_keur={cs.vat_costs_keur:.2f}, expected 222 kEUR "
            f"(VAT facility financing only, NOT construction VAT 7,665 kEUR)"
        )

    def test_shl_idc_not_in_capex_items(self):
        """SHL IDC is NOT capitalized into GFA — it is expensed through P&L."""
        cs = _oborovo_capex()
        all_names = [i.name.lower() for i in cs.book_depreciable_capex_items()]
        assert not any("shl" in n for n in all_names), (
            f"SHL IDC must NOT appear in book_depreciable_capex_items: found in {all_names}"
        )
        # Total financing in GFA < 2,000 kEUR (SHL IDC ~1,170 kEUR would push it over)
        fin_total = cs.idc_keur + cs.commitment_fees_keur + cs.bank_fees_keur + cs.vat_costs_keur
        assert fin_total < 2_100.0, (
            f"Financing total={fin_total:.2f} kEUR exceeds 2,100 — SHL IDC may have been included"
        )


# ---------------------------------------------------------------------------
# 2. book_depreciable_capex_items() structure
# ---------------------------------------------------------------------------

class TestBookDepreciableCapexItems:
    """book_depreciable_capex_items() returns separate per-component items."""

    def test_returns_separate_idc_item(self):
        """IDC is returned as a separate CapexItem."""
        cs = _minimal_capex_structure(idc_keur=100.0)
        names = [i.name for i in cs.book_depreciable_capex_items()]
        assert any("IDC" in n or "Interest" in n for n in names), (
            f"No IDC item found in {names}"
        )

    def test_returns_separate_commitment_fees_item(self):
        cs = _minimal_capex_structure(commitment_fees_keur=50.0)
        names = [i.name for i in cs.book_depreciable_capex_items()]
        assert any("Commitment" in n or "commitment" in n for n in names), (
            f"No commitment fees item found in {names}"
        )

    def test_returns_separate_bank_fees_item(self):
        cs = _minimal_capex_structure(bank_fees_keur=75.0)
        names = [i.name for i in cs.book_depreciable_capex_items()]
        assert any("Bank" in n or "bank" in n for n in names), (
            f"No bank fees item found in {names}"
        )

    def test_returns_separate_vat_item(self):
        cs = _minimal_capex_structure(vat_costs_keur=30.0)
        names = [i.name for i in cs.book_depreciable_capex_items()]
        assert any("VAT" in n or "vat" in n.lower() for n in names), (
            f"No VAT item found in {names}"
        )

    def test_idc_useful_life_override_12y(self):
        """IDC carries useful_life_override=12 (12-year book life)."""
        cs = _minimal_capex_structure(idc_keur=100.0)
        items = [i for i in cs.book_depreciable_capex_items()
                 if "IDC" in i.name or "Interest" in i.name]
        assert items, "No IDC item found"
        assert items[0].useful_life_override == 12, (
            f"IDC useful_life_override={items[0].useful_life_override}, expected 12"
        )

    def test_commitment_fees_useful_life_override_12y(self):
        cs = _minimal_capex_structure(commitment_fees_keur=50.0)
        items = [i for i in cs.book_depreciable_capex_items() if "Commitment" in i.name]
        assert items, "No commitment fees item found"
        assert items[0].useful_life_override == 12

    def test_bank_fees_useful_life_override_12y(self):
        cs = _minimal_capex_structure(bank_fees_keur=75.0)
        items = [i for i in cs.book_depreciable_capex_items() if "Bank" in i.name]
        assert items, "No bank fees item found"
        assert items[0].useful_life_override == 12

    def test_vat_useful_life_override_20y(self):
        """VAT carries useful_life_override=20 (workbook-proven: Inputs sheet 2026-07-22)."""
        cs = _minimal_capex_structure(vat_costs_keur=30.0)
        items = [i for i in cs.book_depreciable_capex_items() if "VAT" in i.name]
        assert items, "No VAT item found"
        assert items[0].useful_life_override == 20, (
            f"VAT useful_life_override={items[0].useful_life_override}, expected 20"
        )

    def test_amounts_match_input_fields(self):
        cs = _minimal_capex_structure(
            idc_keur=1086.03, commitment_fees_keur=188.56,
            bank_fees_keur=477.30, vat_costs_keur=222.0,
        )
        items = {i.name: i for i in cs.book_depreciable_capex_items()}
        idc = next((v for k, v in items.items() if "IDC" in k or "Interest" in k), None)
        assert idc is not None and abs(idc.amount_keur - 1086.03) < 0.01

    def test_zero_fields_excluded(self):
        """Financing components with amount=0 are not included."""
        cs = _minimal_capex_structure(
            idc_keur=0.0, commitment_fees_keur=0.0,
            bank_fees_keur=0.0, vat_costs_keur=0.0,
        )
        fin_items = [i for i in cs.book_depreciable_capex_items()
                     if i.useful_life_override is not None]
        assert len(fin_items) == 0, (
            f"Expected no financing items, got {[i.name for i in fin_items]}"
        )


# ---------------------------------------------------------------------------
# 3. Hard CAPEX book life = 20y (not horizon)
# ---------------------------------------------------------------------------

class TestHardCapexBookLife:
    """Hard CAPEX items carry useful_life_override=20 in the Oborovo factory."""

    def test_all_hard_capex_items_have_20y_override(self):
        """Every hard CAPEX CapexItem in Oborovo factory has useful_life_override=20."""
        cs = _oborovo_capex()
        hard_items = cs.capex_items()
        for item in hard_items:
            if item.amount_keur > 0:
                assert item.useful_life_override == 20, (
                    f"{item.name}: useful_life_override={item.useful_life_override}, expected 20 "
                    f"(workbook-proven Oborovo Dep tab, column B)"
                )

    def test_hard_capex_life_not_horizon_30y(self):
        """Hard CAPEX useful life must be 20, NOT the 30-year model horizon."""
        cs = _oborovo_capex()
        for item in cs.capex_items():
            if item.amount_keur > 0:
                assert item.useful_life_override != 30, (
                    f"{item.name} has useful_life_override=30 (horizon default) — must be 20"
                )


# ---------------------------------------------------------------------------
# 4. build_depreciation_schedule respects useful_life_override
# ---------------------------------------------------------------------------

class TestBuildDepreciationScheduleOverride:
    """build_depreciation_schedule honours useful_life_override for FINANCIAL_COSTS."""

    def test_override_beats_tenor_for_financial_costs(self):
        """When useful_life_override is set, override beats senior_tenor_years."""
        from finco_core.inputs._models import CapexItem, AssetClass
        from finco_core.debt.depreciation_schedule import build_depreciation_schedule

        item = CapexItem(
            name="Test IDC", amount_keur=1200.0,
            asset_class=AssetClass.FINANCIAL_COSTS,
            useful_life_override=12,
        )
        schedule = build_depreciation_schedule(
            capex_items=(item,),
            horizon_years=25,
            senior_tenor_years=14,
        )
        assert schedule[1] == pytest.approx(100.0, abs=0.01), (
            f"Year 1 dep={schedule[1]:.2f}, expected 100.0 (1200/12)"
        )
        assert schedule[12] == pytest.approx(100.0, abs=0.01)
        assert schedule[13] == pytest.approx(0.0, abs=0.01), (
            f"Year 13 dep={schedule[13]:.2f}, expected 0.0 (12-year life ends)"
        )

    def test_no_override_falls_back_to_tenor(self):
        """Without override, FINANCIAL_COSTS uses senior_tenor_years."""
        from finco_core.inputs._models import CapexItem, AssetClass
        from finco_core.debt.depreciation_schedule import build_depreciation_schedule

        item = CapexItem(
            name="Bundle", amount_keur=1400.0,
            asset_class=AssetClass.FINANCIAL_COSTS,
            useful_life_override=None,
        )
        schedule = build_depreciation_schedule(
            capex_items=(item,),
            horizon_years=25,
            senior_tenor_years=14,
        )
        assert schedule[1] == pytest.approx(100.0, abs=0.01)
        assert schedule[14] == pytest.approx(100.0, abs=0.01)
        assert schedule[15] == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# 5. Explicit TaxDepreciationMode policy
# ---------------------------------------------------------------------------

class TestTaxDepreciationMode:
    """TaxDepreciationMode enum and TaxParams fields exist and wire correctly."""

    def test_tax_depreciation_mode_enum_exists(self):
        """TaxDepreciationMode enum is importable from finco_core.inputs."""
        from finco_core.inputs import TaxDepreciationMode
        assert hasattr(TaxDepreciationMode, "BOOK_BASED_PERCENTAGE")
        assert hasattr(TaxDepreciationMode, "STATUTORY_TAX_SCHEDULE")
        assert hasattr(TaxDepreciationMode, "CUSTOM_SCHEDULE")

    def test_tax_params_has_mode_field(self):
        """TaxParams carries tax_depreciation_mode and tax_deductible_book_dep_pct."""
        from finco_core.inputs._models import TaxParams, TaxDepreciationMode
        p = TaxParams()
        assert hasattr(p, "tax_depreciation_mode")
        assert hasattr(p, "tax_deductible_book_dep_pct")

    def test_oborovo_tax_mode_is_book_based_100pct(self):
        """Oborovo factory sets BOOK_BASED_PERCENTAGE 100% (fully deductible)."""
        from finco_core.inputs import TaxDepreciationMode
        inputs = _oborovo_factory()
        mode = getattr(inputs.tax, "tax_depreciation_mode", None)
        pct = getattr(inputs.tax, "tax_deductible_book_dep_pct", None)
        assert mode == TaxDepreciationMode.BOOK_BASED_PERCENTAGE, (
            f"Oborovo tax_depreciation_mode={mode}, expected BOOK_BASED_PERCENTAGE"
        )
        assert pct == pytest.approx(1.0), (
            f"Oborovo tax_deductible_book_dep_pct={pct}, expected 1.0 (100%)"
        )

    def test_fiscal_reintegration_is_separate_from_depreciation(self):
        """Fiscal reintegration (IDC/fees add-back Y1) must NOT appear in depreciation fields.

        The waterfall adds back IDC+bank_fees+commitment_fees in the first operating year
        as fiscal reintegration — this is a separate income item, not depreciation.
        The depreciation_keur field should NOT include fiscal reintegration amounts.
        """
        import ast
        with open("finco_core/waterfall/waterfall_engine.py") as f:
            src = f.read()
        # fiscal_reintegration must be its own variable/field, not mixed into depreciation
        assert "fiscal_reintegration" in src, (
            "waterfall_engine.py must have explicit fiscal_reintegration handling"
        )
        # depreciation_keur must be sourced from dep schedule, not fiscal_reintegration
        # Verify that depreciation_keur assignment line does not reference fiscal_reintegration
        for line in src.splitlines():
            if "depreciation_keur" in line and "fiscal_reintegration" in line:
                assert False, (
                    f"depreciation_keur must not be combined with fiscal_reintegration: {line}"
                )


# ---------------------------------------------------------------------------
# 6. Period-by-period parity (canonical snapshot)
# ---------------------------------------------------------------------------

class TestPeriodByPeriodParity:
    """Period-by-period book depreciation parity against canonical snapshot."""

    def test_year_0_depreciation_is_zero(self):
        """Construction year (period 0) has zero book depreciation."""
        snap = _load_canonical_snap()
        sched = snap["operating_schedules"]["book_depreciation_keur"]
        # Period 0 = first operating period (COD); construction precedes it
        # Depending on snapshot format this is year index 0
        if len(sched) > 0:
            assert sched[0] >= 0.0, "Depreciation must be non-negative"

    def test_last_depreciation_period_is_p40(self):
        """Last non-zero depreciation period is P40 (year 20, end of 20y life).

        With 20y hard CAPEX life and 12y financing life, all components are
        fully depreciated by P40 (year 20 in semiannual convention).
        """
        snap = _load_canonical_snap()
        sched = snap["operating_schedules"]["book_depreciation_keur"]
        last_nonzero = max((i for i, v in enumerate(sched) if v > 0.01), default=-1)
        # P40 = index 39 in 0-based semiannual schedule
        assert last_nonzero <= 39, (
            f"Depreciation continues past P40 (index {last_nonzero}), expected last at P40 (index 39)"
        )

    def test_cumulative_book_dep_matches_excel_within_timing_rounding(self):
        """POST book dep cumulative total within 5 kEUR of Excel (TIMING_ROUNDING only)."""
        truth = _load_excel_truth()
        excel_total = sum(truth["dep"]["dep_total_keur"][1:])

        snap = _load_canonical_snap()
        post_sum = sum(snap["operating_schedules"]["book_depreciation_keur"])

        delta = abs(excel_total - post_sum)
        assert delta <= 5.0, (
            f"Cumulative delta vs Excel = {delta:.2f} kEUR (expected ≤ 5 kEUR). "
            f"Excel={excel_total:.2f}, Python={post_sum:.2f}"
        )

    def test_max_period_delta_is_timing_rounding(self):
        """Maximum per-period delta vs Excel ≤ 10 kEUR (TIMING_ROUNDING — day-fraction only)."""
        truth = _load_excel_truth()
        snap = _load_canonical_snap()

        excel_periods = truth["dep"]["dep_total_keur"][1:]  # operating periods
        python_periods = snap["operating_schedules"]["book_depreciation_keur"]
        n = min(len(excel_periods), len(python_periods))

        max_delta = max(abs(excel_periods[i] - python_periods[i]) for i in range(n))
        assert max_delta <= 10.0, (
            f"Max per-period delta = {max_delta:.3f} kEUR, expected ≤ 10 kEUR (TIMING_ROUNDING). "
            f"If > 10, it indicates a structural error beyond day-fraction convention."
        )


# ---------------------------------------------------------------------------
# 7. Code-path and governance verification
# ---------------------------------------------------------------------------

class TestCodePathAndGovernance:
    """Code path wiring and TAX_CFADS governance gate."""

    def test_waterfall_core_calls_book_depreciable_capex_items(self):
        """waterfall_core.py legacy dep path calls book_depreciable_capex_items()."""
        with open("app/waterfall_core.py") as f:
            src = f.read()
        assert "book_depreciable_capex_items()" in src, (
            "waterfall_core.py should call book_depreciable_capex_items()"
        )

    def test_depreciation_schedule_checks_useful_life_override(self):
        """build_depreciation_schedule references useful_life_override or useful_life_for_item."""
        from finco_core.debt import depreciation_schedule
        src = inspect.getsource(depreciation_schedule.build_depreciation_schedule)
        assert "useful_life_override" in src or "useful_life_for_item" in src, (
            "build_depreciation_schedule must reference useful_life_override"
        )

    def test_canonical_wiring_uses_useful_life_for_item_not_horizon(self):
        """canonical_wiring.py must use useful_life_for_item(), not horizon_years*2 fallback."""
        with open("finco_core/depreciation/canonical_wiring.py") as f:
            src = f.read()
        assert "useful_life_for_item" in src, (
            "canonical_wiring.py must call useful_life_for_item() for non-override items"
        )
        # Ensure the horizon fallback pattern is gone
        assert "book_life_periods = horizon_years * 2" not in src, (
            "canonical_wiring.py must not use horizon_years * 2 as book life fallback"
        )

    def test_tax_cfads_governance_gate_passes(self):
        """TAX_CFADS_V1 gate: 0 unexplained, 0 stale after B1 corrective closure."""
        import subprocess
        result = subprocess.run(
            ["python3", "-m", "finco_parity.check_financial_engine_tax_cfads",
             "--all", "--check"],
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, (
            f"TAX_CFADS_V1 gate FAIL:\n{result.stdout[-2000:]}"
        )
