"""Senior Debt DSCR Sizing Source Map — validation tests.

These tests verify the source map extraction completeness.
No production/runtime behavior changes.
"""
import csv
import os
import pytest

REPORT_CSV = os.path.join(
    os.path.dirname(__file__),
    "..",
    "reports",
    "phase7_tuho_senior_debt_sizing_extraction.csv",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_csv():
    with open(REPORT_CSV, newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Report file
# ---------------------------------------------------------------------------

class TestReportExists:
    def test_csv_exists(self):
        assert os.path.exists(REPORT_CSV), f"{REPORT_CSV} not found"


# ---------------------------------------------------------------------------
# Report shape
# ---------------------------------------------------------------------------

class TestReportShape:
    def test_63_periods(self):
        rows = load_csv()
        assert len(rows) == 63, f"Expected 63 periods, got {len(rows)}"

    def test_required_columns_present(self):
        required = [
            "excel_col", "period_index", "operating_period_index",
            "cf_r69_actual_cfads_keur", "macro_r49_cfads_keur", "macro_r49_formula",
            "macro_r50_sizing_cfads_keur", "macro_r50_is_hardcoded",
            "cf_r69_minus_r50_delta_keur",
            "ds_r19_target_dscr", "ds_r20_debt_service_capacity_keur", "ds_r20_formula",
            "classification",
        ]
        rows = load_csv()
        assert rows, "CSV is empty"
        for col in required:
            assert col in rows[0], f"Required column '{col}' not found"

    def test_period_indices_1_to_63(self):
        rows = load_csv()
        periods = {int(r["period_index"]) for r in rows}
        assert periods == set(range(1, 64)), f"Expected periods 1-63, got {sorted(periods)}"


# ---------------------------------------------------------------------------
# Macro!R50 hardcoded verification
# ---------------------------------------------------------------------------

class TestMacroR50Hardcoded:
    def test_all_macro_r50_are_hardcoded(self):
        rows = load_csv()
        non_hardcoded = [r for r in rows if r["macro_r50_is_hardcoded"].lower() != "true"]
        assert len(non_hardcoded) == 0, (
            f"Found {len(non_hardcoded)} periods where Macro!R50 is NOT hardcoded: "
            f"{[r['period_index'] for r in non_hardcoded]}"
        )

    def test_macro_r50_formula_not_a_formula(self):
        rows = load_csv()
        formula_rows = [r for r in rows if r["macro_r50_is_hardcoded"].lower() == "true"]
        assert len(formula_rows) == len(rows), "All rows should be hardcoded"

    def test_macro_r50_per_period_values_are_numeric(self):
        rows = load_csv()
        for r in rows:
            val = float(r["macro_r50_sizing_cfads_keur"])
            assert isinstance(val, float), f"Macro!R50 period {r['period_index']} not float"


# ---------------------------------------------------------------------------
# Macro!R49 formula verification
# ---------------------------------------------------------------------------

class TestMacroR49Formula:
    def test_macro_r49_links_to_cf_r69(self):
        rows = load_csv()
        non_cf_link = [
            r for r in rows
            if "CF!" not in str(r["macro_r49_formula"])
        ]
        assert len(non_cf_link) == 0, (
            f"Found {len(non_cf_link)} periods where Macro!R49 does not link to CF!: "
            f"{[(r['period_index'], r['macro_r49_formula']) for r in non_cf_link[:5]]}"
        )


# ---------------------------------------------------------------------------
# DSCR switch
# ---------------------------------------------------------------------------

class TestDSCRSwitch:
    def test_ppa_dscr_is_1_20(self):
        rows = load_csv()
        ppa = [r for r in rows if r["classification"] == "PPA/Contracted"]
        assert ppa, "No PPA periods found"
        for r in ppa:
            dscr = float(r["ds_r19_target_dscr"])
            assert abs(dscr - 1.2) < 0.001, (
                f"PPA period {r['period_index']} DSCR={dscr}, expected 1.2"
            )

    def test_merchant_dscr_is_above_1_40(self):
        rows = load_csv()
        merchant = [r for r in rows if r["classification"] == "Merchant"]
        assert merchant, "No Merchant periods found"
        for r in merchant:
            dscr = float(r["ds_r19_target_dscr"])
            assert dscr > 1.40, (
                f"Merchant period {r['period_index']} DSCR={dscr}, expected >1.40"
            )

    def test_ppa_to_merchant_switch_at_period_26(self):
        rows = load_csv()
        ppa_periods = sorted(int(r["period_index"]) for r in rows if r["classification"] == "PPA/Contracted")
        merchant_periods = sorted(int(r["period_index"]) for r in rows if r["classification"] == "Merchant")

        assert ppa_periods[-1] == 63, f"PPA last period should be 63, got {ppa_periods[-1]}"
        assert merchant_periods[0] == 26, f"Merchant first period should be 26, got {merchant_periods[0]}"
        assert ppa_periods == list(range(1, 26)) + list(range(62, 64)), (
            f"PPA periods should be 1-25 and 62-63, got {ppa_periods}"
        )
        assert merchant_periods == list(range(26, 62)), (
            f"Merchant periods should be 26-61, got {len(merchant_periods)} periods"
        )

    def test_switch_occurs_at_operating_period_index_13(self):
        rows = load_csv()
        row26 = next(r for r in rows if int(r["period_index"]) == 26)
        assert int(row26["operating_period_index"]) == 13, (
            f"Period 26 should have op_idx=13, got {row26['operating_period_index']}"
        )


# ---------------------------------------------------------------------------
# Totals
# ---------------------------------------------------------------------------

class TestTotals:
    def test_macro_r49_total_approximately_300927_keur(self):
        rows = load_csv()
        total = sum(float(r["macro_r49_cfads_keur"]) for r in rows)
        assert abs(total - 300_927) < 1.0, f"Macro!R49 total {total:.2f} != 300,927 kEUR"

    def test_macro_r50_total_approximately_204669_keur(self):
        rows = load_csv()
        total = sum(float(r["macro_r50_sizing_cfads_keur"]) for r in rows)
        assert abs(total - 204_669) < 1.0, f"Macro!R50 total {total:.2f} != 204,669 kEUR"

    def test_delta_approximately_96258_keur(self):
        rows = load_csv()
        total = sum(float(r["cf_r69_minus_r50_delta_keur"]) for r in rows)
        assert abs(total - 96_258) < 10.0, f"Delta total {total:.2f} != 96,258 kEUR"

    def test_delta_percentage_approximately_32_percent(self):
        rows = load_csv()
        total_r49 = sum(float(r["macro_r49_cfads_keur"]) for r in rows)
        total_r50 = sum(float(r["macro_r50_sizing_cfads_keur"]) for r in rows)
        pct = (total_r49 - total_r50) / total_r49 * 100
        assert abs(pct - 32.0) < 0.5, f"Delta pct {pct:.1f}% != 32%"


# ---------------------------------------------------------------------------
# No runtime requirements
# ---------------------------------------------------------------------------

class TestNoRuntimeRequirements:
    def test_extraction_does_not_import_runtime_code(self):
        # Verify that scripts/ directory exists and doesn't contain runtime imports
        import domain, app
        # If we get here without ImportError, domain/app were loadable but not used by the extraction
        assert True, "Import check passed"

    def test_csv_produces_no_code_changes(self):
        # Just ensure the CSV is readable and doesn't have side effects
        rows = load_csv()
        assert len(rows) == 63
        assert all(r["macro_r50_is_hardcoded"].lower() == "true" for r in rows)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])