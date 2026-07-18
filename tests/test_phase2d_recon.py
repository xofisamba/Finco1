"""Phase 2D — Excel↔Python Reconciliation Framework Tests.

Tests cover:
  - Package import smoke test
  - Catalog integrity
  - Materiality thresholds
  - Source loading (oborovo)
  - Workbook generation (structure checks only — no financial assertions)
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
# 6. CLI entry point
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
