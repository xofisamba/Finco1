"""Phase 20M — Financial Statements + Runtime Polish tests.

Scope:
- Financial statement tabs render with fc-grid.
- Runtime summary provenance badges render.
- Scenario compare badges render.
- No regression in existing phases.
"""

import os
import re

import pytest
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def runtime_summary_template():
    path = os.path.join(PROJECT_ROOT, "app/templates/partials/runtime_summary.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def financials_template():
    path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_financials.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def compare_template():
    path = os.path.join(PROJECT_ROOT, "app/templates/partials/scenario_compare.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ─── Financial Statement Rendering Tests ──────────────────────────────────────

class TestFinancialStatementsRendering:
    """Test that financial statement tables render with fc-grid design."""

    def test_financials_template_exists(self, financials_template):
        """sheet_financials.html exists and is non-empty."""
        assert len(financials_template) > 5000

    def test_pnl_renders(self, financials_template):
        """P&L statement renders."""
        assert "Income Statement" in financials_template or "P&amp;L" in financials_template
        assert "PPA Revenue" in financials_template
        assert "Total Revenue" in financials_template

    def test_cashflow_renders(self, financials_template):
        """Cash Flow statement renders."""
        assert "Cash Flow" in financials_template
        assert "EBITDA" in financials_template
        assert "CFADS" in financials_template
        assert "Ending Cash" in financials_template

    def test_balance_sheet_renders(self, financials_template):
        """Balance Sheet renders."""
        assert "Balance Sheet" in financials_template
        assert "Net PP" in financials_template  # PP&E
        assert "Senior Debt" in financials_template
        assert "Total Equity" in financials_template

    def test_fc_grid_present(self, financials_template):
        """fc-grid class is used for statement tables."""
        assert 'class="fc-grid' in financials_template

    def test_sticky_header_row(self, financials_template):
        """Sticky header row (fc-grid-header) renders in financial tables."""
        assert "fc-grid-header" in financials_template

    def test_sticky_first_column_class(self, financials_template):
        """Sticky first column class (fc-grid-col-label) renders."""
        assert "fc-grid-col-label" in financials_template

    def test_section_bands_render(self, financials_template):
        """Section bands (fc-section-band) render for P&L groups."""
        assert "fc-section-band" in financials_template
        assert "Revenue" in financials_template
        assert "Operating Expenses" in financials_template
        assert "Assets" in financials_template
        assert "Liabilities" in financials_template
        assert "Equity" in financials_template

    def test_subtotal_rows_render(self, financials_template):
        """Subtotal rows (fc-subtotal-row) render for key metrics."""
        assert "fc-subtotal-row" in financials_template

    def test_grand_total_rows_render(self, financials_template):
        """Grand total rows (fc-grand-total) render for Net Income, Ending Cash, Total Equity."""
        assert "fc-grand-total" in financials_template
        assert "Net Income" in financials_template
        assert "Ending Cash" in financials_template
        assert "Total Equity" in financials_template

    def test_numeric_alignment_cells(self, financials_template):
        """Numeric amount cells use right-aligned fc-cell--amount class."""
        assert "fc-cell--amount" in financials_template

    def test_preview_badges_present(self, financials_template):
        """Preview badges clearly label static tables."""
        assert 'badge-preview' in financials_template
        assert "Preview" in financials_template

    def test_no_inline_style_blocks(self, financials_template):
        """No inline <style> blocks in the financials template."""
        import re
        inline_styles = re.findall(r'<style[^>]*>', financials_template, re.IGNORECASE)
        assert not inline_styles

    def test_session_storage_js_present(self, financials_template):
        """sessionStorage runtime binding JS is present."""
        assert "lastRuntimeSummary" in financials_template
        assert "_populateFSRuntimeBlock" in financials_template

    def test_three_statement_tables_present(self, financials_template):
        """All three statement tables are present."""
        assert "fs-pnl-grid" in financials_template
        assert "fs-cf-grid" in financials_template
        assert "fs-bs-grid" in financials_template


# ─── Runtime Summary Rendering Tests ─────────────────────────────────────────

class TestRuntimeSummaryRendering:
    """Test that runtime summary renders with provenance badges."""

    def test_runtime_summary_exists(self, runtime_summary_template):
        """runtime_summary.html exists and is non-empty."""
        assert len(runtime_summary_template) > 1000

    def test_provenance_banner_present(self, runtime_summary_template):
        """Provenance banner (rs-provenance-banner) renders."""
        assert "rs-provenance-banner" in runtime_summary_template

    def test_runtime_badge_present(self, runtime_summary_template):
        """Runtime badge (badge-runtime) renders in summary."""
        assert "badge-runtime" in runtime_summary_template

    def test_kpi_grid_present(self, runtime_summary_template):
        """KPI grid (rs-kpi-grid) renders."""
        assert "rs-kpi-grid" in runtime_summary_template

    def test_all_kpi_labels_present(self, runtime_summary_template):
        """All KPI labels are present: Project IRR, Equity IRR, Avg DSCR, etc."""
        assert "Project IRR" in runtime_summary_template
        assert "Equity IRR" in runtime_summary_template
        assert "Avg DSCR" in runtime_summary_template
        assert "Senior Debt" in runtime_summary_template
        assert "Total Revenue" in runtime_summary_template
        assert "EBITDA" in runtime_summary_template
        assert "Total OPEX" in runtime_summary_template
        assert "Distributions" in runtime_summary_template

    def test_runtime_notice_present(self, runtime_summary_template):
        """Runtime notice (rs-notice) renders."""
        assert "rs-notice" in runtime_summary_template

    def test_run_banner_present(self, runtime_summary_template):
        """Run banner shows status badge."""
        assert "badge-pass" in runtime_summary_template or "badge-blocked" in runtime_summary_template

    def test_no_inline_style_blocks(self, runtime_summary_template):
        """No inline <style> blocks in runtime summary."""
        import re
        inline_styles = re.findall(r'<style[^>]*>', runtime_summary_template, re.IGNORECASE)
        assert not inline_styles

    def test_runtime_summary_compiles_in_context(self):
        """runtime_summary.html references expected runtime_summary fields."""
        # Verify the template references runtime_summary object
        with open(os.path.join(PROJECT_ROOT, "app/templates/partials/runtime_summary.html")) as f:
            content = f.read()
        assert "runtime_summary.project_name" in content
        assert "runtime_summary.ran_at" in content


# ─── Scenario Compare Rendering Tests ───────────────────────────────────────

class TestScenarioCompareRendering:
    """Test that scenario compare renders with badges and provenance."""

    def test_compare_template_exists(self, compare_template):
        """scenario_compare.html exists and is non-empty."""
        assert len(compare_template) > 1000

    def test_base_vs_active_heading(self, compare_template):
        """Base vs Active compare heading uses badge styling."""
        assert "ps-compare-heading" in compare_template

    def test_provenance_cards_present(self, compare_template):
        """Provenance cards render in compare."""
        assert "ps-compare-provenance-card" in compare_template

    def test_runtime_badges_in_compare(self, compare_template):
        """Runtime badges appear for Base and Active scenarios."""
        assert "badge-runtime" in compare_template

    def test_delta_column_in_compare(self, compare_template):
        """Delta column renders in compare table."""
        assert "Delta" in compare_template or "delta" in compare_template

    def test_compare_table_rows(self, compare_template):
        """Compare rows render for metrics."""
        assert "ps-compare-row" in compare_template

    def test_empty_state_has_preview_badge(self, compare_template):
        """Empty state shows Preview badge."""
        assert "badge-preview" in compare_template

    def test_no_inline_style_blocks(self, compare_template):
        """No inline <style> blocks in compare template."""
        import re
        inline_styles = re.findall(r'<style[^>]*>', compare_template, re.IGNORECASE)
        assert not inline_styles


# ─── Phase Regression Tests ──────────────────────────────────────────────────

class TestPhase20MNoRegression:
    """Ensure Phase 20M changes do not break earlier phases."""

    def test_phase20l_still_passes(self):
        """Phase 20L Construction/IDC tests still pass."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/test_phase20l_construction_idc_ux.py", "-q", "--tb=no"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Phase 20L tests failed:\n{result.stdout}\n{result.stderr}"

    def test_phase20k_still_passes(self):
        """Phase 20K revenue grid tests still pass."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/test_phase20k_revenue_grid.py", "-q", "--tb=no"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Phase 20K tests failed:\n{result.stdout}\n{result.stderr}"

    def test_phase20j_still_passes(self):
        """Phase 20J OPEX grid tests still pass."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/test_phase20j_opex_grid.py", "-q", "--tb=no"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Phase 20J tests failed:\n{result.stdout}\n{result.stderr}"

    def test_phase20i_still_passes(self):
        """Phase 20I CAPEX grid tests still pass."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/test_phase20i_capex_grid.py", "-q", "--tb=no"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Phase 20I tests failed:\n{result.stdout}\n{result.stderr}"

    def test_phase20h_still_passes(self):
        """Phase 20H design system tests still pass."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/test_phase20h_design_system_rendering.py", "-q", "--tb=no"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Phase 20H tests failed:\n{result.stdout}\n{result.stderr}"

    def test_main_web_compiles(self):
        """main_web.py compiles without errors."""
        import main_web
        assert hasattr(main_web, "app")

    def test_templates_are_valid_html_structure(self):
        """All three templates have valid HTML structure."""
        for name in ["runtime_summary", "sheet_financials", "scenario_compare"]:
            path = os.path.join(PROJECT_ROOT, f"app/templates/partials/{name}.html")
            with open(path) as f:
                content = f.read()
            assert "<div" in content
            assert "</div>" in content
            assert not re.search(r'<style[^>]*>.*</style>', content, re.IGNORECASE), f"{name} has inline styles"
