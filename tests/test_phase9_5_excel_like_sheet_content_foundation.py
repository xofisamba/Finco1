"""Phase 9.5 Sheet Content Foundation — smoke tests."""
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# /tests/ →/repo root (resolved via __file__)
PARTIALS = os.path.join(REPO_ROOT, "app/templates/partials")
DOCS = os.path.join(REPO_ROOT, "docs")
STATIC = os.path.join(REPO_ROOT, "static")


class TestTemplatePreviewLabel:
    """Every sheet partial must contain visible template-preview badges."""

    SHEETS = [
        "sheet_inputs.html",
        "sheet_construction.html",
        "sheet_production.html",
        "sheet_revenue.html",
        "sheet_opex.html",
        "sheet_capex.html",
        "sheet_senior_debt.html",
        "sheet_shl.html",
        "sheet_tax.html",
        "sheet_financials.html",
    ]

    def test_sheet_partials_exist(self):
        for sheet in self.SHEETS:
            path = os.path.join(PARTIALS, sheet)
            assert os.path.exists(path), f"{sheet} not found in partials/"

    def test_all_sheets_contain_badge_preview(self):
        for sheet in self.SHEETS:
            path = os.path.join(PARTIALS, sheet)
            content = open(path, encoding="utf-8").read()
            assert "badge-preview" in content, f"{sheet}: missing badge-preview class"

    def test_all_sheets_contain_template_preview_phrase(self):
        for sheet in self.SHEETS:
            path = os.path.join(PARTIALS, sheet)
            content = open(path, encoding="utf-8").read()
            assert "Template preview" in content, f"{sheet}: missing 'Template preview' phrase"

    def test_all_sheets_contain_static_tuho_factory_snapshot(self):
        for sheet in self.SHEETS:
            path = os.path.join(PARTIALS, sheet)
            content = open(path, encoding="utf-8").read()
            assert "TUHO factory snapshot" in content, f"{sheet}: missing 'TUHO factory snapshot' phrase"

    def test_all_sheets_contain_not_live_run_output(self):
        for sheet in self.SHEETS:
            path = os.path.join(PARTIALS, sheet)
            content = open(path, encoding="utf-8").read()
            assert "not live run output" in content, f"{sheet}: missing 'not live run output' phrase"


class TestSheetContent:
    """Key data appears in the correct sheets."""

    def test_inputs_has_tuho_project_data(self):
        path = os.path.join(PARTIALS, "sheet_inputs.html")
        content = open(path, encoding="utf-8").read()
        assert "TUHO Wind 1" in content
        assert "35" in content  # 35 MW
        assert "PPA" in content

    def test_opex_has_total_1998(self):
        path = os.path.join(PARTIALS, "sheet_opex.html")
        content = open(path, encoding="utf-8").read()
        assert "1,998" in content, "Y1 OPEX 1,998 kEUR not found"

    def test_senior_debt_has_43359_and_dscr(self):
        path = os.path.join(PARTIALS, "sheet_senior_debt.html")
        content = open(path, encoding="utf-8").read()
        assert "43,359" in content, "Senior Debt 43,359 not found"
        assert "DSCR" in content

    def test_shl_has_32704_and_pik(self):
        path = os.path.join(PARTIALS, "sheet_shl.html")
        content = open(path, encoding="utf-8").read()
        assert "32,704" in content, "SHL 32,704 not found"
        assert "PIK" in content

    def test_tax_cit_zero(self):
        path = os.path.join(PARTIALS, "sheet_tax.html")
        content = open(path, encoding="utf-8").read()
        assert "0%" in content or "CIT" in content

    def test_financials_has_pl_cf_bs_tables(self):
        # Product Gap PR6: the P&L / Cash Flow / Balance Sheet *tables*
        # were removed (they were static, not Run-backed, and the
        # Balance Sheet did not balance). The statement names still
        # appear in the honest unavailable-state copy referencing them.
        path = os.path.join(PARTIALS, "sheet_financials.html")
        content = open(path, encoding="utf-8").read()
        assert "Income Statement" in content or "P&amp;L" in content
        assert "Cash Flow" in content
        assert "Balance Sheet" in content

    def test_financials_has_preview_label(self):
        # Product Gap PR6: replaced static "TUHO illustrative schedule"
        # preview copy with an honest unavailable-state message.
        path = os.path.join(PARTIALS, "sheet_financials.html")
        content = open(path, encoding="utf-8").read()
        assert "not connected to Run outputs yet" in content, "Missing financial statements unavailable-state label"
        assert "fs-unavailable-panel" in content, "Missing unavailable-state panel"


class TestGovernanceBadges:
    """Governance badges visible in workspace shell."""

    def test_audit_tab_has_g20_blocked(self):
        path = os.path.join(PARTIALS, "workspace_shell.html")
        content = open(path, encoding="utf-8").read()
        assert "G20" in content or "BLOCKED" in content

    def test_audit_tab_has_r99_r102_not_approved(self):
        path = os.path.join(PARTIALS, "workspace_shell.html")
        content = open(path, encoding="utf-8").read()
        assert "NOT APPROVED" in content


class TestProjectSelector:
    """TUHO and Oborovo visible in project selector."""

    def test_tuho_visible(self):
        # Project names are in project_selector partial, not workspace_shell
        path = os.path.join(PARTIALS, "project_selector.html")
        content = open(path, encoding="utf-8").read()
        assert "TUHO" in content or "tuho" in content.lower()

    def test_oborovo_visible(self):
        # Project names are in project_selector partial, not workspace_shell
        path = os.path.join(PARTIALS, "project_selector.html")
        content = open(path, encoding="utf-8").read()
        assert "Oborovo" in content or "oborovo" in content.lower()


class TestNoRuntimeChanges:
    """Verify only UI/template files changed; no runtime changes."""

    ALLOWED_PREFIXES = (
        "app/templates/partials/sheet_",
        "app/templates/partials/workspace_shell",
        "app/templates/partials/workspace_tabs",
        "static/styles.css",
        "docs/phase9_5_excel_like_sheet_content",
        "tests/",
    )

    FORBIDDEN_DIRS = (
        "app/models/",
        "app/core/",
        "app/calculations/",
        "app/domain/",
        "app/project_factories.py",
        "app/ui_runner.py",
        "persistence/",
        "app/calibration",
        "app/capex",
        "app/depreciation",
        "app/waterfall",
        "app/revenue",
    )

    def test_no_forbidden_dirs_exist_in_partials(self):
        """Only partials should be in app/templates/partials/."""
        partials_dir = os.path.join(REPO_ROOT, "app/templates/partials")
        for name in os.listdir(partials_dir):
            if name.endswith(".html") and not name.startswith("sheet_"):
                path = os.path.join(partials_dir, name)
                content = open(path, encoding="utf-8").read()
                for forbidden in self.FORBIDDEN_DIRS:
                    assert forbidden not in content, f"{name} contains forbidden import: {forbidden}"


class TestCSSSheetStyles:
    """CSS contains required sheet styling classes."""

    def test_css_has_sheet_table(self):
        css = open(os.path.join(STATIC, "styles.css"), encoding="utf-8").read()
        assert ".sheet-table" in css

    def test_css_has_badge_preview(self):
        css = open(os.path.join(STATIC, "styles.css"), encoding="utf-8").read()
        assert ".badge-preview" in css

    def test_css_has_assumption_grid(self):
        css = open(os.path.join(STATIC, "styles.css"), encoding="utf-8").read()
        assert ".assumption-grid" in css

    def test_css_has_section_divider(self):
        css = open(os.path.join(STATIC, "styles.css"), encoding="utf-8").read()
        assert ".section-divider" in css

    def test_css_has_subsection_label(self):
        css = open(os.path.join(STATIC, "styles.css"), encoding="utf-8").read()
        assert ".subsection-label" in css


class TestWorkspaceShellWiring:
    """All 12 content tabs wire to sheet partials."""

    SHEET_WIRES = [
        ("panel-inputs", "sheet_inputs.html"),
        ("panel-construction", "sheet_construction.html"),
        ("panel-production", "sheet_production.html"),
        ("panel-revenue", "sheet_revenue.html"),
        ("panel-opex", "sheet_opex.html"),
        ("panel-capex", "sheet_capex.html"),
        ("panel-senior-debt", "sheet_senior_debt.html"),
        ("panel-shl", "sheet_shl.html"),
        ("panel-tax", "sheet_tax.html"),
    ]

    def test_wired_via_include(self):
        path = os.path.join(PARTIALS, "workspace_shell.html")
        content = open(path, encoding="utf-8").read()
        for panel_id, sheet_file in self.SHEET_WIRES:
            assert panel_id in content
            # Check that the sheet file is included via {% include %}
            assert sheet_file in content, f"{sheet_file} not included in workspace_shell.html"
            expected = 'include "partials/' + sheet_file + '"'
            assert expected in content, f"Missing include directive for {sheet_file}"

    def test_pl_cashflow_balance_each_wire_to_financials(self):
        path = os.path.join(PARTIALS, "workspace_shell.html")
        content = open(path, encoding="utf-8").read()
        assert 'sheet_financials.html' in content  # at least 3 times


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])