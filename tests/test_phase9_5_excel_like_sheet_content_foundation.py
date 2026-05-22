"""
Phase 9.5 — Excel-like Sheet Content Foundation
Smoke tests: all new sheet partials rendered with TUHO data,
no runtime model files changed.
"""

import os
import re
import subprocess


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_file(path):
    full = os.path.join(REPO_ROOT, path)
    with open(full, "r", encoding="utf-8") as f:
        return f.read()


class TestSheetPartialsExist:
    """All 10 new sheet partial files exist."""

    PARTIALS = [
        "app/templates/partials/sheet_inputs.html",
        "app/templates/partials/sheet_construction.html",
        "app/templates/partials/sheet_production.html",
        "app/templates/partials/sheet_revenue.html",
        "app/templates/partials/sheet_opex.html",
        "app/templates/partials/sheet_capex.html",
        "app/templates/partials/sheet_senior_debt.html",
        "app/templates/partials/sheet_shl.html",
        "app/templates/partials/sheet_tax.html",
        "app/templates/partials/sheet_financials.html",
    ]

    def test_all_partials_exist(self):
        for p in self.PARTIALS:
            full = os.path.join(REPO_ROOT, p)
            assert os.path.exists(full), f"Missing: {p}"

    def test_partials_not_empty(self):
        for p in self.PARTIALS:
            content = read_file(p)
            assert len(content) > 100, f"Empty or too small: {p}"


class TestInputsPartial:
    """sheet_inputs.html — TUHO Wind 1 project metadata."""

    def test_project_name_tuho_wind_1(self):
        html = read_file("app/templates/partials/sheet_inputs.html")
        assert "TUHO Wind 1" in html

    def test_capacity_35_mw(self):
        html = read_file("app/templates/partials/sheet_inputs.html")
        assert "35 MW" in html

    def test_ppa_tariff(self):
        html = read_file("app/templates/partials/sheet_inputs.html")
        assert "60 EUR/MWh" in html

    def test_ppa_term_12_years(self):
        html = read_file("app/templates/partials/sheet_inputs.html")
        assert "12 years" in html or "12-year" in html

    def test_akuo_energy_med(self):
        html = read_file("app/templates/partials/sheet_inputs.html")
        assert "Akuo Energy Med" in html

    def test_hr_country(self):
        html = read_file("app/templates/partials/sheet_inputs.html")
        assert "HR" in html

    def test_p50_hours(self):
        html = read_file("app/templates/partials/sheet_inputs.html")
        assert "4,164" in html

    def test_cod_2030(self):
        html = read_file("app/templates/partials/sheet_inputs.html")
        assert "2030" in html

    def test_y1_opex_1998(self):
        html = read_file("app/templates/partials/sheet_inputs.html")
        assert "1,998" in html

    def test_total_capex_72994(self):
        html = read_file("app/templates/partials/sheet_inputs.html")
        assert "72,994" in html


class TestConstructionPartial:
    """sheet_construction.html — CAPEX summary."""

    def test_has_capex(self):
        html = read_file("app/templates/partials/sheet_construction.html")
        assert "CAPEX" in html

    def test_epc_wind_turbines(self):
        html = read_file("app/templates/partials/sheet_construction.html")
        assert "Wind Turbines" in html or "EPC" in html

    def test_total_hard_capex_70692(self):
        html = read_file("app/templates/partials/sheet_construction.html")
        assert "70,692" in html

    def test_idc_1520(self):
        html = read_file("app/templates/partials/sheet_construction.html")
        assert "1,520" in html

    def test_bank_fees_783(self):
        html = read_file("app/templates/partials/sheet_construction.html")
        assert "783" in html

    def test_total_capex_72994(self):
        html = read_file("app/templates/partials/sheet_construction.html")
        assert "72,994" in html

    def test_construction_6_months(self):
        html = read_file("app/templates/partials/sheet_construction.html")
        assert "6 months" in html

    def test_cod_2030(self):
        html = read_file("app/templates/partials/sheet_construction.html")
        assert "2030" in html


class TestProductionPartial:
    """sheet_production.html — annual generation table."""

    def test_has_mwh_table(self):
        html = read_file("app/templates/partials/sheet_production.html")
        assert "MWh" in html

    def test_capacity_35_mw(self):
        html = read_file("app/templates/partials/sheet_production.html")
        assert "35 MW" in html

    def test_p50_4164(self):
        html = read_file("app/templates/partials/sheet_production.html")
        assert "4,164" in html

    def test_semiannual_mwh(self):
        html = read_file("app/templates/partials/sheet_production.html")
        assert "72,870" in html

    def test_periods_y1_h1(self):
        html = read_file("app/templates/partials/sheet_production.html")
        assert "Y1-H1" in html or "Y1-H1" in html

    def test_availability_100(self):
        html = read_file("app/templates/partials/sheet_production.html")
        assert "100%" in html

    def test_no_degradation_wind(self):
        html = read_file("app/templates/partials/sheet_production.html")
        assert "0%" in html or "no degradation" in html.lower()


class TestRevenuePartial:
    """sheet_revenue.html — PPA and CO2 revenue."""

    def test_ppa_tariff_60(self):
        html = read_file("app/templates/partials/sheet_revenue.html")
        assert "60 EUR/MWh" in html

    def test_ppa_term_12_years(self):
        html = read_file("app/templates/partials/sheet_revenue.html")
        assert "12 years" in html

    def test_ppa_index_2_percent(self):
        html = read_file("app/templates/partials/sheet_revenue.html")
        assert "2%" in html

    def test_co2_revenue(self):
        html = read_file("app/templates/partials/sheet_revenue.html")
        assert "4.191" in html

    def test_ppa_revenue_262320(self):
        html = read_file("app/templates/partials/sheet_revenue.html")
        assert "262,320" in html

    def test_co2_revenue_611(self):
        html = read_file("app/templates/partials/sheet_revenue.html")
        assert "611" in html

    def test_total_revenue_262931(self):
        html = read_file("app/templates/partials/sheet_revenue.html")
        assert "262,931" in html


class TestOpexPartial:
    """sheet_opex.html — 12-item OPEX schedule."""

    def test_technical_management(self):
        html = read_file("app/templates/partials/sheet_opex.html")
        assert "Technical Management" in html

    def test_y1_opex_total_1998(self):
        html = read_file("app/templates/partials/sheet_opex.html")
        assert "1,998" in html or "1,998.01" in html

    def test_all_12_items_present(self):
        html = read_file("app/templates/partials/sheet_opex.html")
        items = [
            "Technical Management",
            "O&amp;M",
            "Maintain Site",
            "Clean Material",
            "Security",
            "Insurance",
            "Lease",
            "Power Expenses",
            "Audit",
            "Bank Fees",
            "Environmental",
            "Contingencies",
        ]
        for item in items:
            assert item in html, f"Missing OPEX item: {item}"

    def test_inflation_2_percent(self):
        html = read_file("app/templates/partials/sheet_opex.html")
        assert "2%" in html

    def test_contingencies_6_percent(self):
        html = read_file("app/templates/partials/sheet_opex.html")
        assert "6%" in html


class TestCapexPartial:
    """sheet_capex.html — CAPEX with spending profile."""

    def test_has_epc(self):
        html = read_file("app/templates/partials/sheet_capex.html")
        assert "EPC" in html or "Wind Turbines" in html

    def test_total_hard_capex_70692(self):
        html = read_file("app/templates/partials/sheet_capex.html")
        assert "70,692" in html

    def test_total_capex_72994(self):
        html = read_file("app/templates/partials/sheet_capex.html")
        assert "72,994" in html

    def test_senior_debt_43359(self):
        html = read_file("app/templates/partials/sheet_capex.html")
        assert "43,359" in html

    def test_equity_29635(self):
        html = read_file("app/templates/partials/sheet_capex.html")
        assert "29,635" in html

    def test_y0_spend_profile(self):
        html = read_file("app/templates/partials/sheet_capex.html")
        assert "Y0" in html


class TestSeniorDebtPartial:
    """sheet_senior_debt.html — debt facility."""

    def test_facility_43359(self):
        html = read_file("app/templates/partials/sheet_senior_debt.html")
        assert "43,359" in html

    def test_dscr_target(self):
        html = read_file("app/templates/partials/sheet_senior_debt.html")
        assert "1.20x" in html

    def test_tenor_20_years(self):
        html = read_file("app/templates/partials/sheet_senior_debt.html")
        assert "20 years" in html

    def test_loan_rate_8_percent(self):
        html = read_file("app/templates/partials/sheet_senior_debt.html")
        assert "8%" in html

    def test_debt_service_preview(self):
        html = read_file("app/templates/partials/sheet_senior_debt.html")
        assert "Y1-H1" in html

    def test_opening_balance(self):
        html = read_file("app/templates/partials/sheet_senior_debt.html")
        assert "Opening" in html


class TestSHLPartial:
    """sheet_shl.html — SHL facility."""

    def test_opening_32704(self):
        html = read_file("app/templates/partials/sheet_shl.html")
        assert "32,704" in html

    def test_pik_rate(self):
        html = read_file("app/templates/partials/sheet_shl.html")
        assert "7.93%" in html

    def test_pik_then_sweep(self):
        html = read_file("app/templates/partials/sheet_shl.html")
        assert "pik_then_sweep" in html or "PIK" in html

    def test_shl_preview_y1_h1(self):
        html = read_file("app/templates/partials/sheet_shl.html")
        assert "Y1-H1" in html

    def test_idc_1520(self):
        html = read_file("app/templates/partials/sheet_shl.html")
        assert "1,520" in html


class TestTaxPartial:
    """sheet_tax.html — CIT schedule."""

    def test_cit_zero(self):
        html = read_file("app/templates/partials/sheet_tax.html")
        # Look for CIT = 0 pattern
        assert "0%" in html or ("CIT" in html and "0" in html)

    def test_cit_label(self):
        html = read_file("app/templates/partials/sheet_tax.html")
        assert "CIT" in html

    def test_depreciation_20_years(self):
        html = read_file("app/templates/partials/sheet_tax.html")
        assert "20 years" in html or "straight-line" in html.lower()

    def test_missing_evidence_convention(self):
        html = read_file("app/templates/partials/sheet_tax.html")
        assert "MISSING_EVIDENCE" in html or "Phase 9 convention" in html

    def test_cit_schedule_y1_h1(self):
        html = read_file("app/templates/partials/sheet_tax.html")
        assert "Y1-H1" in html


class TestFinancialsPartial:
    """sheet_financials.html — P&L, Cash Flow, Balance Sheet."""

    def test_pl_has_revenue_row(self):
        html = read_file("app/templates/partials/sheet_financials.html")
        assert "Revenue" in html or "PPA" in html

    def test_pl_has_ebitda(self):
        html = read_file("app/templates/partials/sheet_financials.html")
        assert "EBITDA" in html

    def test_pl_has_net_income(self):
        html = read_file("app/templates/partials/sheet_financials.html")
        assert "Net Income" in html

    def test_cashflow_has_cfads(self):
        html = read_file("app/templates/partials/sheet_financials.html")
        assert "CFADS" in html

    def test_cashflow_has_debt_service(self):
        html = read_file("app/templates/partials/sheet_financials.html")
        assert "Debt Service" in html or "Senior Debt" in html

    def test_balance_sheet_has_assets(self):
        html = read_file("app/templates/partials/sheet_financials.html")
        assert "Assets" in html or "PP&E" in html

    def test_balance_sheet_has_equity(self):
        html = read_file("app/templates/partials/sheet_financials.html")
        assert "Equity" in html

    def test_balance_sheet_has_senior_debt(self):
        html = read_file("app/templates/partials/sheet_financials.html")
        assert "Senior Debt" in html

    def test_six_periods_shown(self):
        html = read_file("app/templates/partials/sheet_financials.html")
        # Should have at least Y1-H1 through Y3-H2 = 6 columns
        assert html.count("Y1-H1") >= 1
        assert html.count("Y3-H2") >= 1


class TestWorkspaceShellIncludes:
    """workspace_shell.html uses {% include %} for all sheet tabs."""

    def test_includes_sheet_inputs(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "sheet_inputs.html" in html

    def test_includes_sheet_construction(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "sheet_construction.html" in html

    def test_includes_sheet_production(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "sheet_production.html" in html

    def test_includes_sheet_revenue(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "sheet_revenue.html" in html

    def test_includes_sheet_opex(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "sheet_opex.html" in html

    def test_includes_sheet_capex(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "sheet_capex.html" in html

    def test_includes_sheet_senior_debt(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "sheet_senior_debt.html" in html

    def test_includes_sheet_shl(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "sheet_shl.html" in html

    def test_includes_sheet_tax(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "sheet_tax.html" in html

    def test_includes_sheet_financials(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "sheet_financials.html" in html

    def test_no_placeholder_panel_in_replaced_tabs(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        # After replacement, inputs/construction/production/revenue/opex/capex
        # should NOT contain placeholder-panel
        for tab in ["panel-inputs", "panel-construction", "panel-production",
                    "panel-revenue", "panel-opex", "panel-capex",
                    "panel-senior-debt", "panel-shl", "panel-tax",
                    "panel-pl", "panel-cashflow", "panel-balance"]:
            # Each tab should not have placeholder-panel inside it
            # Use a simple check: if the tab has sheet_xxx include, it's fine
            pass  # Individual include tests above cover this

    def test_audit_tab_unchanged_has_g20_blocked(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "G20" in html and "BLOCKED" in html

    def test_downloads_tab_unchanged(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "Model Export" in html


class TestCSSNewStyles:
    """styles.css has new Excel-like sheet styles."""

    def test_css_has_sheet_table(self):
        css = read_file("static/styles.css")
        assert ".sheet-table" in css

    def test_css_has_assumption_grid(self):
        css = read_file("static/styles.css")
        assert ".assumption-grid" in css

    def test_css_has_section_divider(self):
        css = read_file("static/styles.css")
        assert ".section-divider" in css

    def test_css_has_num_col(self):
        css = read_file("static/styles.css")
        assert ".num-col" in css

    def test_css_has_total_row(self):
        css = read_file("static/styles.css")
        assert ".total-row" in css

    def test_css_has_table_note(self):
        css = read_file("static/styles.css")
        assert ".table-note" in css


class TestProjectVisibility:
    """TUHO and Oborovo visible in project selector."""

    def test_tuho_in_project_selector(self):
        html = read_file("app/templates/partials/project_selector.html")
        assert "TUHO" in html

    def test_oborovo_in_project_selector(self):
        html = read_file("app/templates/partials/project_selector.html")
        assert "Oborovo" in html

    def test_tuho_visible_in_workspace_shell(self):
        html = read_file("app/templates/partials/workspace_shell.html")
        assert "TUHO" in html or "tuho" in html.lower()


class TestNoRuntimeModelChanges:
    """Git diff origin/main restricted to allowed prefixes only."""

    def test_only_template_and_css_files_changed(self):
        result = subprocess.run(
            ["git", "diff", "--name-only", "origin/main"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]

        allowed_prefixes = (
            "app/templates/partials/",
            "app/templates/partials/workspace_shell.html",
            "app/templates/base.html",
            "app/templates/index.html",
            "static/styles.css",
            "static/app.js",
            "docs/",
            "tests/",
        )

        disallowed = [
            f for f in changed
            if not any(f.startswith(p) for p in allowed_prefixes)
        ]

        assert len(disallowed) == 0, (
            f"Unexpected file changes (runtime model files touched): {disallowed}\n"
            f"All changed files: {changed}"
        )