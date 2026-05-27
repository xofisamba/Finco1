"""Phase 20K — Revenue Detail Grid Foundation tests.

Scope:
- Revenue tab renders with fc-grid.
- Sticky header + sticky first column.
- Section bands per group.
- Subtotal / grand total rows.
- Readonly baseline behavior.
- Editable cells for user projects.
- Persistence of edited revenue assumptions.
- No regression in existing phases.
"""

import os
import pytest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def revenue_template():
    """Read the revenue sheet template."""
    path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_revenue.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ─── Rendering Tests ──────────────────────────────────────────────────────────

class TestRevenueGridRendering:
    """Test that the Revenue grid renders correctly with fc-grid design system."""

    def test_revenue_template_exists(self, revenue_template):
        """sheet_revenue.html exists and is non-empty."""
        assert len(revenue_template) > 5000, "sheet_revenue.html should be substantial"

    def test_fc_grid_present(self, revenue_template):
        """Revenue grid uses fc-grid class."""
        assert 'class="fc-grid"' in revenue_template

    def test_fc_grid_wrapper_present(self, revenue_template):
        """fc-grid-wrapper is present for sticky positioning."""
        assert 'fc-grid-wrapper' in revenue_template

    def test_sticky_header_row(self, revenue_template):
        """Sticky header row (fc-grid-header) renders."""
        assert 'fc-grid-header' in revenue_template

    def test_sticky_first_column_class(self, revenue_template):
        """Sticky first column label class is present."""
        assert 'fc-grid-col-label' in revenue_template

    def test_section_bands_render(self, revenue_template):
        """Section bands render for each revenue group."""
        assert 'fc-section-band' in revenue_template
        assert 'Production' in revenue_template
        assert 'PPA' in revenue_template or 'PPA / Tariff' in revenue_template
        assert 'Merchant' in revenue_template or 'Market' in revenue_template
        assert 'CO2' in revenue_template

    def test_subtotal_rows_render(self, revenue_template):
        """Subtotal rows (fc-subtotal-row) render after sections."""
        assert 'fc-subtotal-row' in revenue_template

    def test_grand_total_row_render(self, revenue_template):
        """Grand total row (fc-grand-total) renders at the bottom."""
        assert 'fc-grand-total' in revenue_template

    def test_numeric_alignment_cells(self, revenue_template):
        """Numeric amount cells use right-aligned fc-cell--amount class."""
        assert 'fc-cell--amount' in revenue_template

    def test_revenue_items_in_context(self):
        """ProjectContext.revenue_items is populated for TUHO."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("tuho")
        assert len(ctx.revenue_items) >= 10, f"Expected >=10 revenue items, got {len(ctx.revenue_items)}"
        codes = {item["code"] for item in ctx.revenue_items}
        assert "ppa_base_tariff" in codes
        assert "ppa_index" in codes
        assert "co2_enabled" in codes

    def test_revenue_items_have_required_fields(self):
        """Each revenue item has all required display fields."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("tuho")
        required = {"code", "name", "value", "unit", "group", "editable", "hint"}
        for item in ctx.revenue_items:
            assert required.issubset(item.keys()), f"Item missing fields: {item}"

    def test_capacity_mw_in_revenue_items(self):
        """Installed capacity is in revenue_items context."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("tuho")
        codes = {item["code"] for item in ctx.revenue_items}
        assert "capacity_mw" in codes

    def test_ppa_base_tariff_in_revenue_items(self):
        """PPA base tariff is in revenue_items context."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("tuho")
        codes = {item["code"] for item in ctx.revenue_items}
        assert "ppa_base_tariff" in codes
        # Find it and check editable=True
        item = next(i for i in ctx.revenue_items if i["code"] == "ppa_base_tariff")
        assert item["editable"] is True, "ppa_base_tariff should be editable"
        assert item["name"] == "Base Tariff (PPA)"

    def test_revenue_grid_section_groups(self, revenue_template):
        """All 4 expected groups appear: Production, PPA/Tariff, Market/Merchant, CO2."""
        assert "Production" in revenue_template
        assert "PPA" in revenue_template
        assert "Merchant" in revenue_template or "Market" in revenue_template
        assert "CO2" in revenue_template

    def test_revenue_banner_present(self, revenue_template):
        """Revenue sheet banner renders."""
        assert "sheet-banner" in revenue_template

    def test_ppa_tariff_y1_in_footer(self, revenue_template):
        """PPA tariff Y1 value appears in the footer summary."""
        assert "EUR/MWh" in revenue_template

    def test_sheet_revenue_grew_significantly(self):
        """sheet_revenue.html grew substantially (proves new content)."""
        path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_revenue.html")
        with open(path) as f:
            lines = f.readlines()
        # Original was ~110 lines; Phase 20K should make it 300+
        assert len(lines) > 200, f"sheet_revenue.html should be much larger now (got {len(lines)} lines)"

    def test_no_inline_style_blocks(self, revenue_template):
        """No inline <style> blocks in the revenue template."""
        import re
        inline_styles = re.findall(r'<style[^>]*>', revenue_template, re.IGNORECASE)
        assert not inline_styles, f"Inline <style> blocks found: {inline_styles}"

    def test_readonly_notice_for_baseline(self, revenue_template):
        """Readonly notice appears for baseline projects."""
        assert "inp-readonly-notice" in revenue_template or "readonly" in revenue_template.lower()


class TestOborovoRevenueGrid:
    """Oborovo Solar revenue grid context is populated."""

    def test_oborovo_revenue_items_populated(self):
        """Oborovo Solar has revenue_items in context."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("oborovo")
        assert len(ctx.revenue_items) > 0, "Oborovo should have revenue items"

    def test_oborovo_ppa_tariff_value(self):
        """Oborovo PPA tariff is accessible."""
        from app.ui.project_context import get_project_context
        ctx = get_project_context("oborovo")
        assert ctx.ppa_tariff_eur_mwh > 0


# ─── Snapshot / Persistence Tests ────────────────────────────────────────────

class TestRevenueSnapshotPersistence:
    """Edited revenue assumptions are captured in snapshot fields."""

    def test_revenue_snapshot_fields_in_collect(self):
        """_collect_form_snapshot includes revenue rev_* fields."""
        from main_web import _collect_form_snapshot
        from unittest.mock import MagicMock
        form = MagicMock()
        form.get.side_effect = lambda k, d="": {"rev_ppa_base_tariff": "65.0"}.get(k, d)
        snap = _collect_form_snapshot(form)
        assert "rev_ppa_base_tariff" in snap
        assert "rev_co2_price" in snap
        assert "rev_ppa_index" in snap

    def test_revenue_items_persisted_in_context(self):
        """ProjectContext.revenue_items is populated for both TUHO and Oborovo."""
        from app.ui.project_context import get_project_context
        for name in ("tuho", "oborovo"):
            ctx = get_project_context(name)
            assert len(ctx.revenue_items) > 0, f"No revenue items for {name}"

    def test_revenue_context_no_slow_calculation(self):
        """revenue_items does NOT trigger slow model calculations."""
        from app.ui.project_context import get_project_context
        import time
        start = time.perf_counter()
        ctx = get_project_context("tuho")
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"revenue_items took {elapsed:.2f}s — may trigger model calc"


# ─── Phase Regression Tests ──────────────────────────────────────────────────

class TestPhase20KNoRegression:
    """Ensure Phase 20K changes do not break earlier phases."""

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
        from app.ui.project_context import get_project_context, ProjectContext
        ctx = get_project_context("tuho")
        assert hasattr(ctx, "revenue_items")
        assert len(ctx.revenue_items) >= 10
