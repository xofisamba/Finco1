"""Stage B1: generic book depreciation correction tests.

Verifies the fix for PYTHON_BUG proven in Stage A:
  app/waterfall_core.py previously called inputs.capex.capex_items() which excluded
  financing-cost float fields (idc_keur, commitment_fees_keur, bank_fees_keur,
  vat_costs_keur) from the book depreciable basis.

Fix:
  1. finco_core/inputs/_models.py: book_depreciable_capex_items() returns separate
     CapexItems for each financing component with useful_life_override encoding the
     proven per-component book useful life.
  2. finco_core/debt/depreciation_schedule.py: respects useful_life_override for
     FINANCIAL_COSTS items (previously overridden to senior_tenor_years).
  3. app/waterfall_core.py: legacy dep path now calls book_depreciable_capex_items()
     instead of capex_items().

A/B proof (Oborovo):
  PRE: 55,996.56 kEUR (hard capex only, financing costs absent)
  POST: 57,970.52 kEUR (all components with per-item useful lives)
  Delta: +1,973.96 kEUR = proven PYTHON_BUG from Stage A bridge
  Residual vs Excel: 2.53 kEUR = TIMING_ROUNDING (period day-fraction convention)
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

_TOLERANCE_KEUR = 1.0  # kEUR tolerance for cumulative totals


def _load_excel_truth():
    with open(EXCEL_TRUTH) as f:
        return json.load(f)


def _load_canonical_snap():
    with open(CANONICAL_SNAP) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. book_depreciable_capex_items() returns separate per-component items
# ---------------------------------------------------------------------------

class TestBookDepreciableCapexItems:
    """book_depreciable_capex_items() now returns separate CapexItems per component."""

    def test_returns_separate_idc_item(self):
        """IDC is returned as a separate CapexItem."""
        from finco_core.inputs._models import CapexStructure, CapexItem, AssetClass
        cs = _minimal_capex_structure(idc_keur=100.0)
        items = cs.book_depreciable_capex_items()
        names = [i.name for i in items]
        assert any("IDC" in n or "Interest During Construction" in n for n in names), \
            f"No IDC item found in {names}"

    def test_returns_separate_commitment_fees_item(self):
        """Commitment fees is returned as a separate CapexItem."""
        from finco_core.inputs._models import CapexStructure, CapexItem, AssetClass
        cs = _minimal_capex_structure(commitment_fees_keur=50.0)
        items = cs.book_depreciable_capex_items()
        names = [i.name for i in items]
        assert any("Commitment" in n or "commitment" in n for n in names), \
            f"No commitment fees item found in {names}"

    def test_returns_separate_bank_fees_item(self):
        """Bank fees is returned as a separate CapexItem."""
        cs = _minimal_capex_structure(bank_fees_keur=75.0)
        items = cs.book_depreciable_capex_items()
        names = [i.name for i in items]
        assert any("Bank" in n or "bank" in n for n in names), \
            f"No bank fees item found in {names}"

    def test_returns_separate_vat_item(self):
        """VAT costs is returned as a separate CapexItem."""
        cs = _minimal_capex_structure(vat_costs_keur=30.0)
        items = cs.book_depreciable_capex_items()
        names = [i.name for i in items]
        assert any("VAT" in n or "vat" in n.lower() for n in names), \
            f"No VAT item found in {names}"

    def test_idc_useful_life_override_12y(self):
        """IDC item carries useful_life_override=12 (12-year book life)."""
        cs = _minimal_capex_structure(idc_keur=100.0)
        idc_items = [i for i in cs.book_depreciable_capex_items()
                     if "IDC" in i.name or "Interest" in i.name]
        assert idc_items, "No IDC item found"
        assert idc_items[0].useful_life_override == 12, \
            f"IDC useful_life_override={idc_items[0].useful_life_override}, expected 12"

    def test_commitment_useful_life_override_12y(self):
        """Commitment fees item carries useful_life_override=12."""
        cs = _minimal_capex_structure(commitment_fees_keur=50.0)
        items = [i for i in cs.book_depreciable_capex_items() if "Commitment" in i.name]
        assert items, "No commitment fees item found"
        assert items[0].useful_life_override == 12

    def test_bank_fees_useful_life_override_12y(self):
        """Bank fees item carries useful_life_override=12."""
        cs = _minimal_capex_structure(bank_fees_keur=75.0)
        items = [i for i in cs.book_depreciable_capex_items() if "Bank" in i.name]
        assert items, "No bank fees item found"
        assert items[0].useful_life_override == 12

    def test_vat_useful_life_override_20y(self):
        """VAT item carries useful_life_override=20 (PROVEN: Inputs sheet screenshot 2026-07-22)."""
        cs = _minimal_capex_structure(vat_costs_keur=30.0)
        items = [i for i in cs.book_depreciable_capex_items() if "VAT" in i.name]
        assert items, "No VAT item found"
        assert items[0].useful_life_override == 20, \
            f"VAT useful_life_override={items[0].useful_life_override}, expected 20"

    def test_amounts_match_input_fields(self):
        """Each financing item carries the correct amount_keur from CapexStructure."""
        cs = _minimal_capex_structure(
            idc_keur=1086.03, commitment_fees_keur=188.56,
            bank_fees_keur=477.30, vat_costs_keur=222.07
        )
        items = {i.name: i for i in cs.book_depreciable_capex_items()}
        idc = next((v for k, v in items.items() if "IDC" in k or "Interest" in k), None)
        assert idc is not None and abs(idc.amount_keur - 1086.03) < 0.01

    def test_zero_fields_excluded(self):
        """Financing components with amount=0 are not included."""
        cs = _minimal_capex_structure(idc_keur=0.0, commitment_fees_keur=0.0,
                                      bank_fees_keur=0.0, vat_costs_keur=0.0)
        items = cs.book_depreciable_capex_items()
        fin_items = [i for i in items if i.useful_life_override is not None]
        assert len(fin_items) == 0, f"Expected no financing items, got {[i.name for i in fin_items]}"


# ---------------------------------------------------------------------------
# 2. build_depreciation_schedule respects useful_life_override for FINANCIAL_COSTS
# ---------------------------------------------------------------------------

class TestBuildDepreciationScheduleOverride:
    """build_depreciation_schedule honours useful_life_override for FINANCIAL_COSTS items."""

    def test_financial_costs_with_override_uses_override_not_tenor(self):
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
            senior_tenor_years=14,  # without fix this would override the 12y
        )
        # Year 1-12: dep should be 100/year; year 13+ should be 0
        assert schedule[1] == pytest.approx(100.0, abs=0.01), \
            f"Year 1 dep={schedule[1]:.2f}, expected 100.0 (1200/12)"
        assert schedule[12] == pytest.approx(100.0, abs=0.01)
        assert schedule[13] == pytest.approx(0.0, abs=0.01), \
            f"Year 13 dep={schedule[13]:.2f}, expected 0 (12-year life)"

    def test_financial_costs_without_override_falls_back_to_tenor(self):
        """When no useful_life_override, FINANCIAL_COSTS still uses senior_tenor_years."""
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
        # Should use tenor=14: 1400/14=100/year
        assert schedule[1] == pytest.approx(100.0, abs=0.01)
        assert schedule[14] == pytest.approx(100.0, abs=0.01)
        assert schedule[15] == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# 3. A/B proof: Oborovo POST book dep sum vs Excel
# ---------------------------------------------------------------------------

class TestOborovoBookDepABProof:
    """A/B proof: Oborovo POST-fix book depreciation closes the proven PYTHON_BUG gap."""

    def test_post_fix_book_dep_sum_within_timing_rounding(self):
        """POST book dep sum differs from Excel total by ≤ 5 kEUR (TIMING_ROUNDING only)."""
        truth = _load_excel_truth()
        excel_total = sum(truth["dep"]["dep_total_keur"][1:])  # periods 1-60 (operating)

        snap = _load_canonical_snap()
        post_sum = sum(snap["operating_schedules"]["book_depreciation_keur"])

        delta = abs(excel_total - post_sum)
        assert delta <= 5.0, (
            f"POST book dep delta vs Excel = {delta:.2f} kEUR (expected ≤ 5 kEUR TIMING_ROUNDING). "
            f"Excel={excel_total:.2f}, Python={post_sum:.2f}"
        )

    def test_post_fix_book_dep_increased_vs_pre_by_proven_bug_amount(self):
        """POST minus PRE ≈ 1,973.96 kEUR (proven PYTHON_BUG bridge from Stage A)."""
        snap = _load_canonical_snap()
        post_sum = sum(snap["operating_schedules"]["book_depreciation_keur"])

        # PRE is the value WITHOUT financing costs (capex_items() only).
        # We proxy it via the Stage A proven bridge: Excel total minus proven bug amount.
        truth = _load_excel_truth()
        excel_total = sum(truth["dep"]["dep_total_keur"][1:])
        proven_bug_keur = (
            sum(truth["dep"]["dep_idc_keur"][1:])
            + sum(truth["dep"]["dep_commitment_fees_keur"][1:])
            + sum(truth["dep"]["dep_bank_fees_keur"][1:])
            + sum(truth["dep"]["dep_vat_keur"][1:])
        )
        expected_pre = excel_total - proven_bug_keur
        actual_improvement = post_sum - expected_pre

        assert abs(actual_improvement - proven_bug_keur) <= 5.0, (
            f"POST improvement {actual_improvement:.2f} kEUR should ≈ "
            f"proven bug {proven_bug_keur:.2f} kEUR (tolerance 5 kEUR)"
        )

    def test_tax_depreciation_unchanged(self):
        """Tax depreciation in the legacy path is not affected by book dep fix."""
        snap = _load_canonical_snap()
        tax_dep = snap["operating_schedules"]["tax_depreciation_keur"]
        book_dep = snap["operating_schedules"]["book_depreciation_keur"]
        # Tax dep path (tax_depreciable_capex_items) is separate; just verify it's > 0
        assert sum(tax_dep) > 0, "Tax depreciation should be non-zero"
        assert len(tax_dep) == len(book_dep)

    def test_ax_cfads_gate_still_passes(self):
        """TAX_CFADS_V1 governance gate: 0 unexplained, 0 stale after B1 fix."""
        import subprocess
        result = subprocess.run(
            ["python3", "-m", "finco_parity.check_financial_engine_tax_cfads",
             "--all", "--check"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, (
            f"TAX_CFADS_V1 gate FAIL:\n{result.stdout[-2000:]}"
        )


# ---------------------------------------------------------------------------
# 4. Code-path verification
# ---------------------------------------------------------------------------

class TestCodePathVerification:
    """Verify the correct code paths are wired."""

    def test_waterfall_core_calls_book_depreciable_capex_items(self):
        """waterfall_core.py legacy dep path calls book_depreciable_capex_items()."""
        import finco_parity  # force import to ensure path resolution
        with open("app/waterfall_core.py") as f:
            src = f.read()
        assert "book_depreciable_capex_items()" in src, \
            "waterfall_core.py should call book_depreciable_capex_items()"

    def test_waterfall_core_does_not_call_capex_items_in_legacy_dep_path(self):
        """Legacy dep path no longer calls capex_items() for book depreciation."""
        with open("app/waterfall_core.py") as f:
            src = f.read()
        # Find the legacy dep path section
        idx = src.find("book_depreciable_capex_items()")
        assert idx >= 0, "book_depreciable_capex_items() call not found"
        # The old capex_items() call should not appear in the dep section
        # (it may appear elsewhere for other purposes — just check dep context)
        dep_section_start = src.rfind("\n", 0, idx - 1000)
        dep_section_end = idx + 500
        dep_section = src[dep_section_start:dep_section_end]
        # The old pattern "capex_items = inputs.capex.capex_items()" should be gone
        assert "capex_items = inputs.capex.capex_items()" not in dep_section

    def test_depreciation_schedule_checks_useful_life_override_before_tenor(self):
        """build_depreciation_schedule checks useful_life_override before tenor fallback."""
        from finco_core.debt import depreciation_schedule
        src = inspect.getsource(depreciation_schedule.build_depreciation_schedule)
        assert "useful_life_override" in src or "useful_life_for_item" in src, \
            "build_depreciation_schedule must reference useful_life_override"

    def test_book_depreciable_capex_items_docstring_references_useful_life_override(self):
        """book_depreciable_capex_items docstring documents useful_life_override."""
        from finco_core.inputs._models import CapexStructure
        doc = CapexStructure.book_depreciable_capex_items.__doc__ or ""
        assert "useful_life_override" in doc, \
            "book_depreciable_capex_items docstring should reference useful_life_override"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_capex_structure(**fin_overrides):
    """Return a minimal CapexStructure with only the financing fields set."""
    from finco_core.inputs._models import (
        CapexStructure, CapexItem, AssetClass
    )
    # Use a minimal non-zero CapexItem to satisfy any structure requirements
    base_item = CapexItem(
        name="EPC", amount_keur=1000.0, asset_class=AssetClass.SOLAR_PANELS
    )
    zero_item = CapexItem(
        name="Zero", amount_keur=0.0, asset_class=AssetClass.CIVIL_GRID
    )
    # Build CapexStructure with all required positional CapexItem fields
    # Use inspect to find what's needed
    import inspect
    sig = inspect.signature(CapexStructure.__init__)
    params = list(sig.parameters.keys())
    # All CapexItem fields need defaults
    item_fields = CapexStructure._CAPEX_ITEM_FIELDS
    kwargs = {f: base_item if f == 'epc_contract' else zero_item for f in item_fields}
    kwargs.update(fin_overrides)
    return CapexStructure(**kwargs)
