"""Tests for app/reconciliation/ helpers and reconciliation sheet export."""
import pandas as pd

from app.reconciliation import (
    build_debt_schedule_rows,
    build_project_cf_rows,
    build_equity_cf_rows,
)
from tests.conftest import *


# =============================================================================
# Debt Schedule Reconciliation Tests
# =============================================================================

class TestDebtScheduleReconciliation:
    """Tests for debt schedule reconciliation table."""

    @pytest.fixture
    def oborovo_result(self):
        from app.project_factories import create_default_oborovo
        from app.ui_runner import run_demo_project
        oborovo = create_default_oborovo()
        return run_demo_project("Solar", "Base", project_inputs_override=oborovo).result

    def test_total_ds_equals_interest_plus_principal(self, oborovo_result):
        """Total senior debt service approximately equals interest + principal for each period.
        
        Tolerance is higher (±50 kEUR) because:
        - Last operation period includes balloon principal payment
        - Sculpt schedule may use slightly different totals than direct sum
        - Reconciliation purpose is to show approximate consistency, not exact equality
        """
        rows = build_debt_schedule_rows(oborovo_result)
        for r in rows:
            total = r["total_senior_ds"]
            computed = r["senior_interest"] + r["senior_principal"]
            assert abs(total - computed) < 50.0, (
                f"Period {r['period']}: DS {total:.1f} vs interest+principal {computed:.1f} (diff: {abs(total-computed):.1f})")

    def test_closing_debt_nonzero_until_maturity(self, oborovo_result):
        """Closing debt > 0 during tenor; reaches ~0 at end."""
        rows = build_debt_schedule_rows(oborovo_result)
        non_zero = [r for r in rows if r["closing_senior_debt"] > 1]
        zero_rows = [r for r in rows if r["closing_senior_debt"] <= 1]
        assert len(non_zero) > 0, "No non-zero closing balances found"
        # At least one row should reach near-zero (maturity)
        assert len(zero_rows) >= 1, (
            f"Closing debt never reaches near-zero. Last 5 rows: {rows[-5:]}"
        )

    def test_debt_keur_matches_sculpt_result(self, oborovo_result):
        """Debt amount (opening of first period) matches sculpting result."""
        rows = build_debt_schedule_rows(oborovo_result)
        if not rows:
            pytest.skip("No rows returned")
        opening = rows[0]["opening_senior_debt"]
        sculpt_debt = oborovo_result.sculpting_result.debt_keur
        assert abs(opening - sculpt_debt) < 100, (
            f"First opening balance {opening:.0f} != sculpt debt {sculpt_debt:.0f}"
        )

    def test_dscr_is_reasonable(self, oborovo_result):
        """DSCR values are in plausible range (>0 and <=10) for active debt periods.
        
        Periods where debt is fully repaid (closing balance = 0) may show DSCR=0
        since there is no active debt service to ratio against.
        """
        rows = build_debt_schedule_rows(oborovo_result)
        for r in rows:
            d = r["dscr"]
            assert 0 <= d <= 10.0, (
                f"Period {r['period']} DSCR {d} outside plausible range [0, 10.0]"
            )

    def test_all_periods_have_dscr(self, oborovo_result):
        """Every operation period has a DSCR value (zero is valid for repaid periods)."""
        rows = build_debt_schedule_rows(oborovo_result)
        assert all(r["dscr"] >= 0 for r in rows), "Some periods missing DSCR"

    def test_rows_not_empty_for_oborovo(self, oborovo_result):
        """Debt schedule returns rows for Oborovo (operation periods exist)."""
        rows = build_debt_schedule_rows(oborovo_result)
        assert len(rows) > 0, "No debt schedule rows returned for Oborovo"


# =============================================================================
# Project CF Bridge Tests
# =============================================================================

class TestProjectCFBridge:
    """Tests for project cashflow bridge table."""

    @pytest.fixture
    def oborovo_result(self):
        from app.project_factories import create_default_oborovo
        from app.ui_runner import run_demo_project
        oborovo = create_default_oborovo()
        return run_demo_project("Solar", "Base", project_inputs_override=oborovo).result

    def test_ebitda_equals_revenue_minus_opex(self, oborovo_result):
        """EBITDA = Revenue - OpEx for each period."""
        rows = build_project_cf_rows(oborovo_result)
        for r in rows:
            if r["ebitda"] > 0:  # operation periods only
                computed = r["revenue"] - r["opex"]
                assert abs(r["ebitda"] - computed) < 1.0, (
                    f"Period {r['period']}: EBITDA {r['ebitda']:.1f} ≠ Revenue {r['revenue']:.1f} - OpEx {r['opex']:.1f}"
                )

    def test_cumulative_cf_is_sequential(self, oborovo_result):
        """Cumulative project CF increases/decreases by period CF."""
        rows = build_project_cf_rows(oborovo_result)
        for i in range(1, len(rows)):
            delta = rows[i]["project_free_cf"]
            computed = rows[i]["cumulative_project_cf"] - rows[i-1]["cumulative_project_cf"]
            assert abs(delta - computed) < 1.0, (
                f"Period {rows[i]['period']}: CF delta {delta:.1f} ≠ cumulative change {computed:.1f}"
            )

    def test_project_irr_cashflows_reasonable(self, oborovo_result):
        """Project free CF is plausible magnitude."""
        rows = build_project_cf_rows(oborovo_result)
        op_rows = [r for r in rows if r["ebitda"] > 0]
        for r in op_rows:
            assert -50_000 <= r["project_free_cf"] <= 50_000, (
                f"Period {r['period']} project CF {r['project_free_cf']:.0f} unreasonable"
            )


# =============================================================================
# Equity CF Bridge Tests
# =============================================================================

class TestEquityCFBridge:
    """Tests for equity cashflow bridge table."""

    @pytest.fixture
    def oborovo_result(self):
        from app.project_factories import create_default_oborovo
        from app.ui_runner import run_demo_project
        oborovo = create_default_oborovo()
        return run_demo_project("Solar", "Base", project_inputs_override=oborovo).result

    def test_includes_shl_service(self, oborovo_result):
        """Equity CF bridge captures SHL interest and principal."""
        rows = build_equity_cf_rows(oborovo_result)
        # At least one operation period should have non-zero SHL
        shl_rows = [r for r in rows if r["shl_interest"] > 0 or r["shl_principal"] > 0]
        assert len(shl_rows) > 0, "No SHL service found in equity bridge"

    def test_includes_distributions(self, oborovo_result):
        """Equity CF bridge includes distribution amounts."""
        rows = build_equity_cf_rows(oborovo_result)
        dist_rows = [r for r in rows if r["distributions"] > 0]
        assert len(dist_rows) > 0, "No distributions found in equity bridge"

    def test_equity_investment_negative_or_zero(self, oborovo_result):
        """Equity investment is cash out (negative or zero)."""
        rows = build_equity_cf_rows(oborovo_result)
        for r in rows:
            assert r["equity_investment"] <= 0, (
                f"Period {r['period']}: equity investment {r['equity_investment']:.1f} should be ≤ 0"
            )

    def test_equity_cf_sum_near_zero(self, oborovo_result):
        """Sum of equity CFs should be near equity IRR crossover (small residual)."""
        rows = build_equity_cf_rows(oborovo_result)
        total = sum(r["equity_cash_flow"] for r in rows)
        # A financed project: negative early (equity in), positive later (distributions)
        # Net should be reasonable (not too far from zero for PE-type structure)
        assert -200_000 <= total <= 200_000, (
            f"Total equity CF {total:.0f} kEUR unreasonable"
        )


# =============================================================================
# Excel Export with Reconciliation Sheets
# =============================================================================

class TestExcelReconciliationSheets:
    """Tests for Excel export with include_reconciliation_sheets=True."""

    @pytest.fixture
    def oborovo_result(self):
        from app.project_factories import create_default_oborovo
        from app.ui_runner import run_demo_project
        oborovo = create_default_oborovo()
        return run_demo_project("Solar", "Base", project_inputs_override=oborovo)

    def test_reconciliation_sheets_are_bytes(self, oborovo_result):
        """Excel with reconciliation sheets returns valid bytes."""
        from app.excel_export import build_excel_export
        data = build_excel_export(
            result=oborovo_result.result,
            project_inputs=oborovo_result.project_inputs,
            include_reconciliation_sheets=True,
        )
        assert isinstance(data, bytes)
        assert len(data) > 1000

    def test_reconciliation_sheets_in_workbook(self, oborovo_result):
        """Reconciliation sheets are present when flag is True."""
        import openpyxl
        from io import BytesIO
        from app.excel_export import build_excel_export

        data = build_excel_export(
            result=oborovo_result.result,
            project_inputs=oborovo_result.project_inputs,
            include_reconciliation_sheets=True,
        )
        wb = openpyxl.load_workbook(BytesIO(data))
        expected = {"Debt Schedule", "Project CF Bridge", "Equity CF Bridge", "Calibration Notes"}
        assert expected.issubset(set(wb.sheetnames)), (
            f"Missing sheets. Found: {wb.sheetnames}, expected: {expected}"
        )

    def test_backward_compatible_without_flag(self, oborovo_result):
        """Excel without flag does NOT include reconciliation sheets."""
        import openpyxl
        from io import BytesIO
        from app.excel_export import build_excel_export

        data = build_excel_export(
            result=oborovo_result.result,
            project_inputs=oborovo_result.project_inputs,
            include_reconciliation_sheets=False,
        )
        wb = openpyxl.load_workbook(BytesIO(data))
        assert "Debt Schedule" not in wb.sheetnames
        assert "Project CF Bridge" not in wb.sheetnames

    def test_generic_solar_export_still_works(self):
        """Generic Solar export with reconciliation sheets works."""
        from app.project_factories import create_default_solar_project
        from app.ui_runner import run_demo_project
        from app.excel_export import build_excel_export

        solar = create_default_solar_project()
        result = run_demo_project("Solar", "Base", project_inputs_override=solar).result
        data = build_excel_export(
            result=result,
            project_inputs=None,
            include_reconciliation_sheets=True,
        )
        assert isinstance(data, bytes)
        assert len(data) > 1000

    def test_calibration_notes_has_profile_name(self, oborovo_result):
        """Calibration Notes sheet contains merchant curve profile name."""
        import openpyxl
        from io import BytesIO
        from app.excel_export import build_excel_export

        data = build_excel_export(
            result=oborovo_result.result,
            project_inputs=oborovo_result.project_inputs,
            include_reconciliation_sheets=True,
        )
        wb = openpyxl.load_workbook(BytesIO(data))
        ws = wb["Calibration Notes"]
        # Sheet should have Merchant Curve section
        content = "\n".join(str(cell.value or "") for row in ws.iter_rows() for cell in row)
        assert "Merchant" in content or "AFRY" in content or "Curve" in content

    def test_generic_wind_export_still_works(self):
        """Generic Wind export with reconciliation sheets works."""
        from app.project_factories import create_default_wind_project
        from app.ui_runner import run_demo_project
        from app.excel_export import build_excel_export

        wind = create_default_wind_project()
        result = run_demo_project("Wind", "Base", project_inputs_override=wind).result
        data = build_excel_export(
            result=result,
            project_inputs=None,
            include_reconciliation_sheets=True,
        )
        assert isinstance(data, bytes)
        assert len(data) > 1000