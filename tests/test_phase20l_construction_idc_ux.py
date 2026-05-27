"""Phase 20L — Construction / IDC Workbook UX Foundation tests.

Scope:
- Construction tab renders with fc-grid.
- IDC tab renders with fc-grid.
- Monthly drawdown rows (audit/preview).
- Funding summary rows.
- Section bands.
- Grand total rows.
- Readonly baseline behavior.
- No regression in existing phases.
"""

import os
import pytest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def construction_template():
    path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_construction.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def idc_template():
    path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_idc.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ─── Construction Rendering Tests ───────────────────────────────────────────

class TestConstructionGridRendering:
    """Test that the Construction grid renders correctly with fc-grid."""

    def test_construction_template_exists(self, construction_template):
        """sheet_construction.html exists and is non-empty."""
        assert len(construction_template) > 2000, "sheet_construction.html should be substantial"

    def test_fc_grid_present(self, construction_template):
        """Construction grid uses fc-grid class."""
        assert 'class="fc-grid"' in construction_template

    def test_fc_grid_wrapper_present(self, construction_template):
        """fc-grid-wrapper is present for sticky/scroll positioning."""
        assert 'fc-grid-wrapper' in construction_template

    def test_sticky_header_row(self, construction_template):
        """Sticky header row (fc-grid-header) renders."""
        assert 'fc-grid-header' in construction_template

    def test_sticky_first_column_class(self, construction_template):
        """Sticky first column label class is present."""
        assert 'fc-grid-col-label' in construction_template

    def test_section_bands_render(self, construction_template):
        """Section bands render in construction grid."""
        assert 'fc-section-band' in construction_template

    def test_monthly_drawdown_audit_badge(self, construction_template):
        """Monthly drawdown section shows audit/preview badge."""
        assert 'Audit' in construction_template or 'audit' in construction_template
        assert 'badge-preview' in construction_template

    def test_construction_summary_cards(self, construction_template):
        """Construction summary section has key metric cards."""
        assert 'Financial Close' in construction_template
        assert 'COD' in construction_template
        assert 'Construction Period' in construction_template
        assert 'Total CAPEX' in construction_template

    def test_construction_context_populated(self):
        """ProjectContext.construction_items is populated for TUHO."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("tuho")
        assert len(ctx.construction_items) > 0, "TUHO should have construction items"
        types = {item.get("type") for item in ctx.construction_items}
        assert "monthly" in types
        assert "summary" in types

    def test_monthly_construction_rows_have_required_fields(self):
        """Monthly construction rows have all required drawdown fields."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("tuho")
        monthly = [i for i in ctx.construction_items if i.get("type") == "monthly"]
        assert len(monthly) > 0, "Should have monthly construction rows"
        required = {"month_index", "equity_draw_keur", "shl_draw_keur",
                    "senior_draw_keur", "total_draw_keur", "cumulative_uses_keur"}
        for row in monthly:
            assert required.issubset(row.keys()), f"Monthly row missing fields: {row}"

    def test_summary_construction_rows(self):
        """Construction summary rows include equity, SHL, senior, total."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("tuho")
        summary = [i for i in ctx.construction_items if i.get("type") == "summary"]
        labels = {i["label"] for i in summary}
        assert "Total Equity Draw" in labels
        assert "Total SHL Principal Draw" in labels
        assert "Total Senior Principal Draw" in labels
        assert "Total Uses (CAPEX)" in labels

    def test_construction_month_count(self):
        """TUHO has monthly construction rows (actual count from engine)."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("tuho")
        monthly = [i for i in ctx.construction_items if i.get("type") == "monthly"]
        # The offline construction engine generates the actual monthly schedule;
        # ProjectContext.construction_months is a summary field, not the engine count.
        assert len(monthly) > 0, f"Expected monthly construction rows, got {len(monthly)}"
        # Monthly rows should be consecutive from month 1
        indices = sorted([r["month_index"] for r in monthly])
        assert indices == list(range(1, len(indices) + 1)), f"Month indices not consecutive: {indices}"

    def test_oborovo_construction_context_populated(self):
        """Oborovo Solar also has construction_items."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("oborovo")
        assert len(ctx.construction_items) > 0, "Oborovo should have construction items"

    def test_no_inline_style_blocks(self, construction_template):
        """No inline <style> blocks in the construction template."""
        import re
        inline_styles = re.findall(r'<style[^>]*>', construction_template, re.IGNORECASE)
        assert not inline_styles, f"Inline <style> blocks found: {inline_styles}"

    def test_readonly_notice_for_baseline(self, construction_template):
        """Readonly notice appears for baseline projects."""
        assert "inp-readonly-notice" in construction_template or "readonly" in construction_template.lower()


# ─── IDC Rendering Tests ────────────────────────────────────────────────────

class TestIDCSGridRendering:
    """Test that the IDC grid renders correctly."""

    def test_idc_template_exists(self, idc_template):
        """sheet_idc.html exists and is non-empty."""
        assert len(idc_template) > 2000, "sheet_idc.html should be substantial"

    def test_fc_grid_present(self, idc_template):
        """IDC grid uses fc-grid class."""
        assert 'class="fc-grid"' in idc_template

    def test_fc_grid_wrapper_present(self, idc_template):
        """fc-grid-wrapper is present."""
        assert 'fc-grid-wrapper' in idc_template

    def test_sticky_header_row(self, idc_template):
        """Sticky header row (fc-grid-header) renders."""
        assert 'fc-grid-header' in idc_template

    def test_sticky_first_column_class(self, idc_template):
        """Sticky first column label class is present."""
        assert 'fc-grid-col-label' in idc_template

    def test_section_bands_render(self, idc_template):
        """Section bands render for Senior Debt, SHL, IDC Summary."""
        assert 'fc-section-band' in idc_template
        assert 'Senior Debt' in idc_template
        assert 'SHL' in idc_template

    def test_grand_total_row_render(self, idc_template):
        """Grand total row renders at bottom of IDC summary."""
        assert 'fc-grand-total' in idc_template

    def test_idc_items_in_context(self):
        """ProjectContext.idc_items is populated for TUHO."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("tuho")
        assert len(ctx.idc_items) > 0, "TUHO should have IDC items"
        codes = {item["code"] for item in ctx.idc_items if "code" in item}
        assert "senior_idc" in codes
        assert "shl_idc" in codes
        assert "total_idc" in codes

    def test_idc_items_have_required_fields(self):
        """Each IDC item has all required display fields."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("tuho")
        summary_items = [i for i in ctx.idc_items if "code" in i]
        required = {"code", "name", "value", "unit", "group", "editable", "hint"}
        for item in summary_items:
            assert required.issubset(item.keys()), f"IDC item missing fields: {item}"

    def test_senior_idc_value_positive(self):
        """Senior IDC is positive for TUHO."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("tuho")
        senior = next((i for i in ctx.idc_items if i.get("code") == "senior_idc"), None)
        assert senior is not None
        assert senior["value"] > 0, "Senior IDC should be positive"

    def test_shl_idc_value_positive(self):
        """SHL IDC is positive for TUHO."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("tuho")
        shl = next((i for i in ctx.idc_items if i.get("code") == "shl_idc"), None)
        assert shl is not None
        assert shl["value"] > 0, "SHL IDC should be positive"

    def test_total_idc_equals_senior_plus_shl(self):
        """Total IDC = Senior IDC + SHL IDC."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("tuho")
        senior = next((i for i in ctx.idc_items if i.get("code") == "senior_idc"), None)
        shl = next((i for i in ctx.idc_items if i.get("code") == "shl_idc"), None)
        total = next((i for i in ctx.idc_items if i.get("code") == "total_idc"), None)
        assert total is not None
        assert abs(total["value"] - (senior["value"] + shl["value"])) < 0.01

    def test_oborovo_idc_context_populated(self):
        """Oborovo Solar also has idc_items."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("oborovo")
        assert len(ctx.idc_items) > 0, "Oborovo should have IDC items"

    def test_monthly_idc_entries_present(self):
        """IDC items include monthly_idc entries (audit)."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("tuho")
        monthly = [i for i in ctx.idc_items if i.get("type") == "monthly_idc"]
        assert len(monthly) > 0, "Should have monthly IDC entries"

    def test_no_inline_style_blocks(self, idc_template):
        """No inline <style> blocks in the IDC template."""
        import re
        inline_styles = re.findall(r'<style[^>]*>', idc_template, re.IGNORECASE)
        assert not inline_styles, f"Inline <style> blocks found: {inline_styles}"

    def test_readonly_notice_for_baseline(self, idc_template):
        """Readonly notice appears for baseline projects."""
        assert "inp-readonly-notice" in idc_template or "readonly" in idc_template.lower()


# ─── Phase Regression Tests ──────────────────────────────────────────────────

class TestPhase20LNoRegression:
    """Ensure Phase 20L changes do not break earlier phases."""

    def test_phase20k_revenue_still_passes(self):
        """Phase 20K revenue grid tests still pass."""
        import subprocess
        result = subprocess.run(
            [".venv/bin/python", "-m", "pytest",
             "tests/test_phase20k_revenue_grid.py", "-q", "--tb=no"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Phase 20K tests failed:\n{result.stdout}\n{result.stderr}"

    def test_phase20j_opex_still_passes(self):
        """Phase 20J OPEX grid tests still pass."""
        import subprocess
        result = subprocess.run(
            [".venv/bin/python", "-m", "pytest",
             "tests/test_phase20j_opex_grid.py", "-q", "--tb=no"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Phase 20J tests failed:\n{result.stdout}\n{result.stderr}"

    def test_phase20i_capex_still_passes(self):
        """Phase 20I CAPEX grid tests still pass."""
        import subprocess
        result = subprocess.run(
            [".venv/bin/python", "-m", "pytest",
             "tests/test_phase20i_capex_grid.py", "-q", "--tb=no"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Phase 20I tests failed:\n{result.stdout}\n{result.stderr}"

    def test_phase20h_design_system_still_passes(self):
        """Phase 20H design system tests still pass."""
        import subprocess
        result = subprocess.run(
            [".venv/bin/python", "-m", "pytest",
             "tests/test_phase20h_design_system_rendering.py", "-q", "--tb=no"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Phase 20H tests failed:\n{result.stdout}\n{result.stderr}"

    def test_main_web_compiles(self):
        """main_web.py compiles without errors."""
        import main_web
        assert hasattr(main_web, "app")
        assert hasattr(main_web, "_collect_form_snapshot")

    def test_project_context_compiles(self):
        """project_context.py compiles and exports."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("tuho")
        assert hasattr(ctx, "construction_items")
        assert hasattr(ctx, "idc_items")
        assert len(ctx.construction_items) > 0
        assert len(ctx.idc_items) > 0
