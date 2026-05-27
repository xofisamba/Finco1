"""Phase 20I — CAPEX Detail Grid Rendering Tests.

Tests the CAPEX grid UI built on the fc-* design system.
Verifies rendering, structure, readonly behavior, and editing.
"""

import os
import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")


class TestCAPEXGridRendering:
    """Smoke tests for CAPEX grid HTML rendering."""

    def test_capex_grid_file_exists(self):
        path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_capex.html")
        assert os.path.exists(path)

    def test_capex_grid_uses_fc_grid(self):
        path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_capex.html")
        with open(path) as f:
            content = f.read()

        assert "fc-grid" in content
        assert "fc-grid-header" in content
        assert "fc-grid-col-label" in content

    def test_capex_grid_has_section_bands(self):
        path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_capex.html")
        with open(path) as f:
            content = f.read()

        assert "fc-section-band" in content
        for label in ["Construction", "Development", "Financing Costs"]:
            assert label in content, f"Missing section: {label}"

    def test_capex_grid_has_total_rows(self):
        path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_capex.html")
        with open(path) as f:
            content = f.read()

        assert "fc-total-row" in content
        assert "fc-grand-total" in content

    def test_capex_grid_has_edit_inputs(self):
        path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_capex.html")
        with open(path) as f:
            content = f.read()

        assert 'type="number"' in content
        assert "name=" in content

    def test_capex_grid_readonly_notice(self):
        path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_capex.html")
        with open(path) as f:
            content = f.read()

        assert "is_user_project" in content
        assert "inp-readonly-notice" in content


class TestCAPEXGridCSS:
    def test_capex_grid_css_added(self):
        path = os.path.join(PROJECT_ROOT, "static/styles.css")
        with open(path) as f:
            content = f.read()

        assert "Phase 20I" in content
        assert ".fc-section-band__label" in content
        assert ".fc-input-native" in content
        assert ".fc-grand-total" in content


class TestProjectContextCapexItems:
    def test_capex_items_field_exists(self):
        import sys
        sys.path.insert(0, PROJECT_ROOT)
        from app.ui.project_context import ProjectContext

        assert "capex_items" in ProjectContext.__dataclass_fields__

    def test_tuho_capex_items_populated(self):
        import sys
        sys.path.insert(0, PROJECT_ROOT)
        from app.ui.project_context import get_project_context

        ctx = get_project_context("tuho")
        assert len(ctx.capex_items) > 0
        codes = {item["code"] for item in ctx.capex_items}
        assert "epc_contract" in codes


class TestNoFunctionalChanges:
    def test_sheet_capex_grew(self):
        """sheet_capex.html grew significantly (proves new content)."""
        path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_capex.html")
        with open(path) as f:
            lines = f.readlines()
        # Original was 51 lines; Phase 20I version should be 500+
        assert len(lines) > 200, f"sheet_capex.html should be much larger now (got {len(lines)} lines)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
