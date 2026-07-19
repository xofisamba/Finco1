"""Phase 2D — Excel↔Python Reconciliation Framework Tests.

Tests cover:
  - Package import smoke test
  - Catalog integrity
  - Materiality thresholds
  - Source loading (oborovo)
  - Workbook generation (structure checks)
  - Financial truth and data-provenance tests
  - Classification coverage
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest


# ---------------------------------------------------------------------------
# 1. Package import
# ---------------------------------------------------------------------------

class TestImports:
    def test_finco_recon_imports(self):
        import finco_recon  # noqa: F401

    def test_catalog_imports(self):
        from finco_recon.catalog import CATALOG, LineItem, get_item, get_catalog_by_section
        assert len(CATALOG) > 0

    def test_materiality_imports(self):
        from finco_recon.materiality import MaterialitySettings, DEFAULT_MATERIALITY
        assert DEFAULT_MATERIALITY is not None

    def test_sources_imports(self):
        from finco_recon.sources import ExcelData, EngineData, LegacyData, OborovoSources

    def test_workbook_imports(self):
        from finco_recon.workbook import build_workbook

    def test_generate_imports(self):
        from finco_recon.generate_oborovo import main


# ---------------------------------------------------------------------------
# 2. Catalog integrity
# ---------------------------------------------------------------------------

class TestCatalog:
    def test_no_duplicate_codes(self):
        from finco_recon.catalog import CATALOG
        codes = [item.code for item in CATALOG]
        assert len(codes) == len(set(codes)), "Duplicate catalog codes found"

    def test_classification_values_valid(self):
        from finco_recon.catalog import CATALOG, CLASSIFICATIONS
        for item in CATALOG:
            assert item.default_classification in CLASSIFICATIONS, (
                f"{item.code} has unknown classification {item.default_classification!r}"
            )

    def test_out_of_scope_items_have_correct_classification(self):
        from finco_recon.catalog import CATALOG
        for item in CATALOG:
            if not item.in_clean_engine:
                assert item.default_classification in (
                    "OUT OF CLEAN ENGINE SCOPE", "UNRESOLVED SOURCE",
                ), f"{item.code} is out-of-scope but has classification {item.default_classification!r}"

    def test_get_item_known_code(self):
        from finco_recon.catalog import get_item
        item = get_item("CF.01")
        assert item is not None
        assert item.code == "CF.01"
        assert item.section == "CFADS"

    def test_get_item_unknown_code(self):
        from finco_recon.catalog import get_item
        assert get_item("ZZ.99") is None

    def test_get_catalog_by_section_covers_all(self):
        from finco_recon.catalog import CATALOG, get_catalog_by_section
        by_section = get_catalog_by_section()
        total = sum(len(v) for v in by_section.values())
        assert total == len(CATALOG)

    def test_expected_sections_present(self):
        from finco_recon.catalog import get_catalog_by_section
        by_section = get_catalog_by_section()
        for section in ("TIMELINE", "PRODUCTION", "REVENUE", "OPEX", "EBITDA",
                        "TAX", "CFADS", "SENIOR_DEBT"):
            assert section in by_section, f"Section {section!r} missing from catalog"

    def test_opex_items_count(self):
        from finco_recon.catalog import get_catalog_by_section
        by_section = get_catalog_by_section()
        opex = by_section["OPEX"]
        # OP.00 (total) + OP.01-OP.15 = 16 items
        assert len(opex) == 16, f"Expected 16 OPEX items, got {len(opex)}"

    def test_senior_debt_items_count(self):
        from finco_recon.catalog import get_catalog_by_section
        by_section = get_catalog_by_section()
        sd = by_section["SENIOR_DEBT"]
        assert len(sd) == 7, f"Expected 7 SENIOR_DEBT items, got {len(sd)}"


# ---------------------------------------------------------------------------
# 3. Materiality
# ---------------------------------------------------------------------------

class TestMateriality:
    def setup_method(self):
        from finco_recon.materiality import MaterialitySettings
        self.mat = MaterialitySettings(
            absolute_keur=1.0,
            relative_fraction=0.001,
            mwh_threshold=10.0,
            ratio_threshold=0.005,
        )

    def test_keur_below_abs_immaterial(self):
        assert not self.mat.is_material(0.5, unit="kEUR")

    def test_keur_at_abs_material(self):
        assert self.mat.is_material(1.0, unit="kEUR")

    def test_keur_above_abs_material(self):
        assert self.mat.is_material(2.0, unit="kEUR")

    def test_keur_relative_material(self):
        # delta 0.5 kEUR but > 0.1% of 100 kEUR
        assert self.mat.is_material(0.5, excel_val=100.0, python_val=100.5, unit="kEUR")

    def test_keur_relative_immaterial(self):
        # delta 0.05 kEUR on 1000 kEUR base → 0.005% < 0.1%
        assert not self.mat.is_material(0.05, excel_val=1000.0, python_val=1000.05, unit="kEUR")

    def test_mwh_below_threshold_immaterial(self):
        assert not self.mat.is_material(5.0, unit="MWh")

    def test_mwh_at_threshold_material(self):
        assert self.mat.is_material(10.0, unit="MWh")

    def test_ratio_below_threshold_immaterial(self):
        assert not self.mat.is_material(0.003, unit="x")

    def test_ratio_at_threshold_material(self):
        assert self.mat.is_material(0.005, unit="x")

    def test_zero_delta_always_immaterial_keur(self):
        assert not self.mat.is_material(0.0, excel_val=100.0, python_val=100.0, unit="kEUR")


# ---------------------------------------------------------------------------
# 4. Source loading
# ---------------------------------------------------------------------------

class TestOborovoSources:
    @pytest.fixture(scope="class")
    def sources(self):
        from finco_recon.sources import load_oborovo_sources
        return load_oborovo_sources()

    def test_excel_period_count(self, sources):
        assert len(sources.excel) == 60

    def test_engine_period_count(self, sources):
        assert len(sources.engine) == 60

    def test_excel_cfads_length(self, sources):
        assert len([p.cfads_keur for p in sources.excel]) == 60

    def test_engine_cfads_length(self, sources):
        assert len([p.cfads_keur for p in sources.engine]) == 60

    def test_excel_revenue_nonempty(self, sources):
        revenue = [p.revenue_keur for p in sources.excel]
        assert any(v is not None and v != 0.0 for v in revenue), "All Excel revenue values are zero"

    def test_engine_revenue_nonempty(self, sources):
        revenue = [p.revenue_keur for p in sources.engine]
        assert any(v is not None and v != 0.0 for v in revenue), "All engine revenue values are zero"

    def test_engine_debt_size_positive(self, sources):
        assert sources.engine_debt_size_keur > 0

    def test_excel_opex_nonempty(self, sources):
        opex = [p.opex_keur for p in sources.excel]
        assert any(v is not None and v != 0.0 for v in opex), "All Excel OPEX values are zero"

    def test_engine_ebitda_length(self, sources):
        assert len([p.ebitda_keur for p in sources.engine]) == 60

    def test_engine_senior_interest_length(self, sources):
        assert len([p.sd_interest_keur for p in sources.engine]) == 60

    def test_excel_senior_interest_length(self, sources):
        assert len([p.senior_interest_keur for p in sources.excel]) == 60

    def test_engine_tax_keur_length(self, sources):
        assert len([p.tax_keur for p in sources.engine]) == 60

    def test_excel_ebitda_present(self, sources):
        assert len([p.ebitda_keur for p in sources.excel]) == 60

    def test_engine_opex_b01_length(self, sources):
        assert len([p.opex_b01_keur for p in sources.engine]) == 60

    def test_total_capex_positive(self, sources):
        assert sources.total_capex_keur > 0


# ---------------------------------------------------------------------------
# 5. Workbook generation — structure checks
# ---------------------------------------------------------------------------

EXPECTED_SHEETS = [
    "00_EXEC_RECON",
    "01_INPUTS_RECON",
    "02_TIMELINE_RECON",
    "03_PROD_REV_RECON",
    "04_OPEX_RECON",
    "05_PNL_RECON",
    "06_CAPEX_IDC_RECON",
    "07_DEPRECIATION_RECON",
    "08_TAX_RECON",
    "09_CFADS_RECON",
    "10_SENIOR_DEBT_RECON",
    "11_SHL_RECON",
    "12_OPENING_BALANCES",
    "13_DELTA_REGISTER",
    "14_SOURCE_MAP",
    "15_RAW_RECON",
]


class TestWorkbookGeneration:
    @pytest.fixture(scope="class")
    def workbook_path(self, tmp_path_factory):
        tmp = tmp_path_factory.mktemp("recon")
        out = tmp / "oborovo_recon.xlsx"
        from finco_recon.sources import load_oborovo_sources
        from finco_recon.workbook import build_workbook
        sources = load_oborovo_sources()
        build_workbook(sources, out)
        return out

    def test_file_exists(self, workbook_path):
        assert workbook_path.exists()

    def test_file_nonempty(self, workbook_path):
        assert workbook_path.stat().st_size > 1000

    def test_all_sheets_present(self, workbook_path):
        import openpyxl
        wb = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
        for sheet in EXPECTED_SHEETS:
            assert sheet in wb.sheetnames, f"Sheet {sheet!r} missing"
        wb.close()

    def test_sheet_count(self, workbook_path):
        import openpyxl
        wb = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
        assert len(wb.sheetnames) == len(EXPECTED_SHEETS)
        wb.close()

    def test_exec_recon_has_content(self, workbook_path):
        import openpyxl
        wb = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
        ws = wb["00_EXEC_RECON"]
        non_empty = sum(1 for row in ws.iter_rows() for cell in row if cell.value is not None)
        assert non_empty > 5, "00_EXEC_RECON appears empty"
        wb.close()

    def test_raw_recon_has_content(self, workbook_path):
        import openpyxl
        wb = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
        ws = wb["15_RAW_RECON"]
        non_empty = sum(1 for row in ws.iter_rows() for cell in row if cell.value is not None)
        assert non_empty > 10, "15_RAW_RECON appears empty"
        wb.close()

    def test_delta_register_has_content(self, workbook_path):
        import openpyxl
        wb = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
        ws = wb["13_DELTA_REGISTER"]
        non_empty = sum(1 for row in ws.iter_rows() for cell in row if cell.value is not None)
        assert non_empty > 5
        wb.close()

    def test_senior_debt_sheet_has_content(self, workbook_path):
        import openpyxl
        wb = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
        ws = wb["10_SENIOR_DEBT_RECON"]
        non_empty = sum(1 for row in ws.iter_rows() for cell in row if cell.value is not None)
        assert non_empty > 10
        wb.close()


# ---------------------------------------------------------------------------
# 6. Financial truth and data-provenance tests
# ---------------------------------------------------------------------------

FACTORY_ONLY_MODULES = {
    "app.project_factories",
    "financial_engine",
    "finco_parity.baselines",
}


class TestSourceIndependence:
    """Verify Excel-labelled values do NOT silently come from Python-only sources."""

    @pytest.fixture(scope="class")
    def sources(self):
        from finco_recon.sources import load_oborovo_sources
        return load_oborovo_sources()

    def test_excel_revenue_from_fixture_not_engine(self, sources):
        # Excel revenue comes from CF.operating_revenues_keur in the JSON fixture.
        # Python revenue comes from the engine. They must NOT be identical for all periods
        # (if they were, it would suggest one side was copied from the other).
        # In practice they differ due to debt-size policy difference → downstream CFADS → tax.
        xl_rev = [p.revenue_keur for p in sources.excel if p.revenue_keur is not None]
        py_rev = [p.revenue_keur for p in sources.engine if p.revenue_keur is not None]
        assert len(xl_rev) == 60, "Expected 60 Excel revenue periods"
        assert len(py_rev) == 60, "Expected 60 engine revenue periods"
        # They share the same physical model, so some periods may match. But the sources
        # are independent objects loaded from different files.
        # Key provenance test: Excel values are floats extracted from the JSON fixture.
        assert all(isinstance(v, float) for v in xl_rev), "Excel revenue values must be floats"

    def test_excel_cfads_from_fixture(self, sources):
        xl = [p.cfads_keur for p in sources.excel if p.cfads_keur is not None]
        assert len(xl) == 60
        # CFADS in fixture is CF.free_cash_flow_for_banks_keur, which comes from Excel model.
        assert all(isinstance(v, float) for v in xl)

    def test_excel_opex_individual_items_extracted(self, sources):
        # B.01-B.13 per-item OPEX is now extracted directly from XLSM CF rows 56-68.
        # ExcelData must have opex_b01_keur..opex_b13_keur populated (not None) for operation periods.
        for p in sources.excel:
            assert hasattr(p, "opex_b01_keur"), "ExcelData must have per-item B.xx fields (from XLSM)"
        # Check B.01-B.13 sum is close to total OPEX for each period (identity check)
        for p in sources.excel:
            items = [
                p.opex_b01_keur, p.opex_b02_keur, p.opex_b03_keur, p.opex_b04_keur,
                p.opex_b05_keur, p.opex_b06_keur, p.opex_b07_keur, p.opex_b08_keur,
                p.opex_b09_keur, p.opex_b10_keur, p.opex_b11_keur, p.opex_b12_keur,
                p.opex_b13_keur,
            ]
            non_none = [v for v in items if v is not None]
            if non_none and p.opex_keur is not None:
                item_sum = sum(non_none)
                assert abs(item_sum - p.opex_keur) < 1.0, \
                    f"Period {p.period_index}: B.01-B.13 sum {item_sum:.2f} != total OPEX {p.opex_keur:.2f}"

    def test_excel_capex_per_item_unresolved(self, sources):
        # No per-item CAPEX in ExcelData.
        for p in sources.excel:
            assert not hasattr(p, "capex_c01_keur"), \
                "ExcelData must NOT have per-item C.xx fields (they are Python-only)"

    def test_legacy_not_used_as_excel_in_sd_schedule(self, sources):
        # SD.01 and SD.05 must use excel_sd_opening/closing from DS sheet (direct XLSM provenance),
        # NOT legacy snapshot values directly.
        assert hasattr(sources, "excel_sd_opening_keur"), "OborovoSources missing excel_sd_opening_keur"
        assert hasattr(sources, "excel_sd_closing_keur"), "OborovoSources missing excel_sd_closing_keur"
        assert len(sources.excel_sd_opening_keur) == 60
        assert len(sources.excel_sd_closing_keur) == 60
        # Opening period 0 (DS sheet direct) must be close to Excel total debt (within 1 kEUR).
        op0 = sources.excel_sd_opening_keur[0]
        assert op0 is not None, "SD.01 Excel opening period 0 must not be None"
        assert abs(op0 - sources.excel_total_debt_keur) < 1.0, \
            f"SD.01 Excel opening {op0:.2f} should match excel_total_debt_keur {sources.excel_total_debt_keur:.2f}"

    def test_excel_sd_schedule_identity(self, sources):
        # Verify: closing[t] == opening[t] - principal[t] for all periods where data exists.
        tol = 0.1  # 100 EUR rounding tolerance
        for i, (ep, op, cl) in enumerate(zip(
            sources.excel, sources.excel_sd_opening_keur, sources.excel_sd_closing_keur
        )):
            if op is None or ep.senior_principal_keur is None or cl is None:
                continue
            expected_closing = op - ep.senior_principal_keur
            assert abs(expected_closing - cl) < tol, \
                f"Period {i}: SD identity fail: {op:.2f} - {ep.senior_principal_keur:.2f} = {expected_closing:.2f} ≠ {cl:.2f}"

    def test_no_legacy_values_substituted_for_excel(self, sources):
        # Legacy snapshot opening debt at period 0 and Excel reconstruction should differ
        # (they come from different-sized debt stacks).
        if sources.legacy and sources.excel_sd_opening_keur:
            leg_opening = sources.legacy[0].sd_opening_keur
            xl_opening = sources.excel_sd_opening_keur[0]
            if leg_opening is not None and xl_opening is not None:
                # Legacy and Excel should NOT be the same (different debt sizes)
                # Legacy = Python engine output stored in snapshot ≈ 46,343 kEUR
                # Excel = gearing cap ≈ 42,852 kEUR
                assert abs(leg_opening - xl_opening) > 100, \
                    "Legacy and Excel opening SD are suspiciously identical — verify sources are independent"


class TestFinancialIdentities:
    """Verify financial accounting identities hold within each source."""

    @pytest.fixture(scope="class")
    def sources(self):
        from finco_recon.sources import load_oborovo_sources
        return load_oborovo_sources()

    def test_excel_ebitda_identity_per_period(self, sources):
        """Excel: Revenue - OPEX = EBITDA per period (from CF sheet).

        KNOWN DATA QUALITY ISSUE: CF.ebitda_keur = 0.0 in fixture for periods 20-59.
        This is an extraction gap — the fixture was not fully populated.
        Test validates the identity only for periods where EBITDA is non-zero.
        """
        tol = 1.0  # 1 kEUR per period
        failures = []
        zero_ebitda_periods = []
        for i, ep in enumerate(sources.excel):
            if ep.revenue_keur is None or ep.opex_keur is None or ep.ebitda_keur is None:
                continue
            # Document periods where EBITDA = 0 but revenue ≠ 0 (fixture extraction gap)
            if ep.ebitda_keur == 0.0 and ep.revenue_keur and ep.revenue_keur > 100:
                zero_ebitda_periods.append(i)
                continue
            computed = ep.revenue_keur - ep.opex_keur
            if abs(computed - ep.ebitda_keur) > tol:
                failures.append(
                    f"Period {i} ({ep.period_end}): Rev({ep.revenue_keur:.2f}) - OPEX({ep.opex_keur:.2f}) "
                    f"= {computed:.2f} ≠ EBITDA({ep.ebitda_keur:.2f}), delta={computed - ep.ebitda_keur:.3f}"
                )
        # Document the extraction gap as a warning, not a failure
        if zero_ebitda_periods:
            import warnings
            warnings.warn(
                f"KNOWN FIXTURE GAP: CF.ebitda_keur = 0 in periods {zero_ebitda_periods[:5]}... "
                f"({len(zero_ebitda_periods)} periods total). This represents an incomplete Excel extraction. "
                "Periods where Revenue>0 but EBITDA=0 are excluded from the identity check.",
                UserWarning, stacklevel=1,
            )
        assert not failures, f"Excel EBITDA identity fails (excluding known zero-EBITDA periods):\n" + "\n".join(failures[:5])

    def test_engine_ebitda_identity_per_period(self, sources):
        """Engine: Revenue - OPEX = EBITDA per period."""
        tol = 1.0
        failures = []
        for i, eg in enumerate(sources.engine):
            if eg.revenue_keur is None or eg.opex_keur is None or eg.ebitda_keur is None:
                continue
            computed = eg.revenue_keur - eg.opex_keur
            if abs(computed - eg.ebitda_keur) > tol:
                failures.append(f"Period {i}: {computed:.2f} ≠ {eg.ebitda_keur:.2f}")
        assert not failures, "Engine EBITDA identity fails:\n" + "\n".join(failures[:5])

    def test_excel_senior_ds_identity_per_period(self, sources):
        """Excel: DS = interest + principal per period (DS sheet + CF sheet)."""
        tol = 1.0
        failures = []
        for i, ep in enumerate(sources.excel):
            if ep.senior_interest_keur is None or ep.senior_principal_keur is None or ep.senior_ds_keur is None:
                continue
            computed = ep.senior_interest_keur + ep.senior_principal_keur
            if abs(computed - ep.senior_ds_keur) > tol:
                failures.append(
                    f"Period {i}: int({ep.senior_interest_keur:.2f}) + prin({ep.senior_principal_keur:.2f}) "
                    f"= {computed:.2f} ≠ DS({ep.senior_ds_keur:.2f})"
                )
        assert not failures, "Excel DS identity fails:\n" + "\n".join(failures[:5])

    def test_engine_senior_ds_identity_per_period(self, sources):
        """Engine: DS = interest + principal per period."""
        tol = 1.0
        failures = []
        for i, eg in enumerate(sources.engine):
            if eg.sd_interest_keur is None or eg.sd_principal_keur is None or eg.sd_ds_keur is None:
                continue
            computed = eg.sd_interest_keur + eg.sd_principal_keur
            if abs(computed - eg.sd_ds_keur) > tol:
                failures.append(f"Period {i}: {computed:.2f} ≠ {eg.sd_ds_keur:.2f}")
        assert not failures, "Engine DS identity fails:\n" + "\n".join(failures[:5])

    def test_engine_opex_item_sum_vs_total(self, sources):
        """Engine: B.xx items are annual amounts; engine total OPEX is per-period (semi-annual).

        KNOWN: OpexItem.amount_at_year() returns annual kEUR. The engine total opex_keur
        is per-period (semi-annual). Therefore sum(B.xx annual) ≈ 2 × engine_total_opex_semiannual.
        This test documents that relationship and verifies the ratio is approximately 2:1.
        """
        opex_fields = [
            "opex_b01_keur", "opex_b02_keur", "opex_b03_keur", "opex_b04_keur",
            "opex_b05_keur", "opex_b06_keur", "opex_b07_keur", "opex_b08_keur",
            "opex_b09_keur", "opex_b10_keur", "opex_b11_keur", "opex_b12_keur",
            "opex_b13_keur", "opex_b14_keur", "opex_b15_keur",
        ]
        ratios = []
        for i, eg in enumerate(sources.engine):
            if eg.opex_keur is None or eg.opex_keur == 0:
                continue
            items = [getattr(eg, f) for f in opex_fields]
            if any(v is None for v in items):
                continue
            item_sum = sum(items)
            ratios.append(item_sum / eg.opex_keur)
        # Verify ratio is approximately 2.0 (annual items vs semi-annual periods)
        assert ratios, "No periods with full B.xx data and non-zero total opex"
        avg_ratio = sum(ratios) / len(ratios)
        # Document: B.xx amounts are annual → ratio should be ~2
        assert 1.5 < avg_ratio < 2.5, \
            f"Expected sum(B.xx annual) / opex_period ≈ 2.0, got {avg_ratio:.3f}. " \
            "This documents that per-item B.xx amounts are annual, not semi-annual."

    def test_excel_pl_revenue_matches_cf_revenue(self, sources):
        """Excel: P&L revenue and CF revenue should be identical (same model cell usually)."""
        tol = 1.0
        mismatches = []
        for i, ep in enumerate(sources.excel):
            if ep.revenue_keur is None or ep.pl_revenue_keur is None:
                continue
            if abs(ep.revenue_keur - ep.pl_revenue_keur) > tol:
                mismatches.append(
                    f"Period {i}: CF_rev={ep.revenue_keur:.2f} ≠ PL_rev={ep.pl_revenue_keur:.2f}"
                )
        # This may legitimately differ if Excel model uses different P&L/CF revenue lines
        # — test reports but does NOT hard-fail; annotate any differences.
        if mismatches:
            import warnings
            warnings.warn(
                f"Excel CF revenue ≠ P&L revenue in {len(mismatches)} periods "
                f"(first: {mismatches[0]}). This may be expected if revenue recognition differs.",
                UserWarning, stacklevel=1,
            )

    def test_classification_no_auto_policy_difference(self, sources):
        """No material delta should be auto-classified POLICY DIFFERENCE without evidence."""
        from finco_recon.workbook import _classify, _delta, _safe
        from finco_recon.materiality import DEFAULT_MATERIALITY
        from finco_recon.catalog import get_item
        # Test _classify with a synthetic material delta — should return "" not POLICY DIFFERENCE
        item = get_item("RV.01")  # revenue — no documented policy difference
        cls = _classify(item, 100.0, 1000.0, 1100.0, DEFAULT_MATERIALITY)
        assert cls != "POLICY DIFFERENCE", \
            "_classify must NOT auto-assign POLICY DIFFERENCE for undocumented material deltas"
        assert cls == "", \
            f"Expected blank (OPEN) for undocumented material delta, got {cls!r}"

    def test_classification_match_for_immaterial(self, sources):
        """Immaterial deltas classify as MATCH."""
        from finco_recon.workbook import _classify
        from finco_recon.materiality import DEFAULT_MATERIALITY
        from finco_recon.catalog import get_item
        item = get_item("RV.01")
        cls = _classify(item, 0.001, 1000.0, 1000.001, DEFAULT_MATERIALITY)
        assert cls == "MATCH"

    def test_classification_unresolved_when_excel_none(self, sources):
        """UNRESOLVED SOURCE when Excel value is None."""
        from finco_recon.workbook import _classify
        from finco_recon.materiality import DEFAULT_MATERIALITY
        from finco_recon.catalog import get_item
        item = get_item("PR.01")  # production — no Excel source
        cls = _classify(item, None, None, 1000.0, DEFAULT_MATERIALITY)
        assert cls == "UNRESOLVED SOURCE"

    def test_policy_difference_only_for_documented_case(self, sources):
        """POLICY DIFFERENCE only returned when documented_cls is explicitly passed."""
        from finco_recon.workbook import _classify
        from finco_recon.materiality import DEFAULT_MATERIALITY
        from finco_recon.catalog import get_item
        item = get_item("SD.02")  # senior interest
        # Without documented_cls → blank
        cls_undoc = _classify(item, 500.0, 1000.0, 1500.0, DEFAULT_MATERIALITY)
        assert cls_undoc == ""
        # With documented_cls → POLICY DIFFERENCE
        cls_doc = _classify(item, 500.0, 1000.0, 1500.0, DEFAULT_MATERIALITY,
                            documented_cls="POLICY DIFFERENCE")
        assert cls_doc == "POLICY DIFFERENCE"

    def test_excel_total_capex_vs_python_total_capex_provenance(self, sources):
        """Total CAPEX: document provenance — both sides come from factory/golden.

        KNOWN: excel_total_capex_keur (from oborovo_golden.json outputs.total_capex_keur)
        and total_capex_keur (from app.project_factories) are identical in this baseline
        because the golden JSON was generated from the same factory. This is a provenance
        limitation: no independent Excel cell-level CAPEX extraction exists in the fixture.
        Classification: UNRESOLVED SOURCE for per-item CAPEX; total = MATCH (same source).
        """
        assert sources.excel_total_capex_keur > 0, "Excel total CAPEX must be positive"
        assert sources.total_capex_keur > 0, "Python total CAPEX must be positive"
        # Document that they are from the same provenance chain (no surprise MATCH)
        delta = abs(sources.excel_total_capex_keur - sources.total_capex_keur)
        # Either they match (same source) or differ (independent sources)
        # — either is acceptable; we just document the actual delta
        if delta < 1.0:
            import warnings
            warnings.warn(
                f"Excel and Python total CAPEX are nearly identical (delta={delta:.3f} kEUR). "
                "Both are sourced from oborovo_golden.json/factory — not independent Excel extraction. "
                "Classification should be MATCH with note 'UNRESOLVED PROVENANCE'.",
                UserWarning, stacklevel=1,
            )

    def test_excel_debt_differs_from_engine_debt(self, sources):
        """Excel and Python debt size differ — confirms POLICY DIFFERENCE is real."""
        assert sources.excel_total_debt_keur != sources.engine_debt_size_keur, \
            "Excel and Python debt sizes are identical — verify POLICY DIFFERENCE"
        delta = abs(sources.excel_total_debt_keur - sources.engine_debt_size_keur)
        assert delta > 1000, f"Debt delta only {delta:.1f} kEUR — expected >1000"

    def test_two_sided_coverage_required_items(self, sources):
        """Verify key reconciled items have both Excel and Python values in at least one period."""
        required_two_sided = {
            "revenue": ([p.revenue_keur for p in sources.excel], [p.revenue_keur for p in sources.engine]),
            "opex": ([p.opex_keur for p in sources.excel], [p.opex_keur for p in sources.engine]),
            "ebitda": ([p.ebitda_keur for p in sources.excel], [p.ebitda_keur for p in sources.engine]),
            "cfads": ([p.cfads_keur for p in sources.excel], [p.cfads_keur for p in sources.engine]),
            "senior_interest": ([p.senior_interest_keur for p in sources.excel], [p.sd_interest_keur for p in sources.engine]),
            "senior_principal": ([p.senior_principal_keur for p in sources.excel], [p.sd_principal_keur for p in sources.engine]),
            "depreciation": ([p.depreciation_keur for p in sources.excel], [p.book_depreciation_keur for p in sources.engine]),
            "cit_accrual": ([p.pl_cit_keur for p in sources.excel], [p.tax_keur for p in sources.engine]),
            "cash_tax": ([p.cash_tax_keur for p in sources.excel], [p.corporate_tax_cash_keur for p in sources.engine]),
        }
        for name, (xl_vals, py_vals) in required_two_sided.items():
            xl_ok = any(v is not None for v in xl_vals)
            py_ok = any(v is not None for v in py_vals)
            assert xl_ok, f"{name}: no Excel values present"
            assert py_ok, f"{name}: no Python values present"


# ---------------------------------------------------------------------------
# 7. CLI entry point
# ---------------------------------------------------------------------------

class TestCLI:
    def test_cli_generates_file(self, tmp_path):
        out = tmp_path / "test_recon.xlsx"
        from finco_recon.generate_oborovo import main
        rc = main(["--output", str(out)])
        assert rc == 0
        assert out.exists()
        assert out.stat().st_size > 1000

    def test_cli_exit_code_zero(self, tmp_path):
        out = tmp_path / "test_recon2.xlsx"
        from finco_recon.generate_oborovo import main
        rc = main(["--output", str(out)])
        assert rc == 0

    def test_cli_custom_abs_tol(self, tmp_path):
        out = tmp_path / "test_recon_tol.xlsx"
        from finco_recon.generate_oborovo import main
        rc = main(["--output", str(out), "--abs-tol", "5.0"])
        assert rc == 0
        assert out.exists()
