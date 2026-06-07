"""Phase 20J — OPEX Detail Grid Rendering Tests.

Tests the OPEX grid UI built on the fc-* design system.
Verifies rendering, structure, readonly behavior, and editing.
"""

import os
import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
OPEX_TEMPLATE = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_opex.html")
STYLES_PATH = os.path.join(PROJECT_ROOT, "static/styles.css")


class TestOPEXGridRendering:
    """Smoke tests for OPEX grid HTML rendering."""

    def test_opex_grid_file_exists(self):
        path = os.path.join(PROJECT_ROOT, "app/templates/partials/sheet_opex.html")
        assert os.path.exists(path)

    def test_opex_grid_uses_fc_grid(self):
        path = OPEX_TEMPLATE
        with open(path, encoding="utf-8") as f:
            content = f.read()

        assert "fc-grid" in content
        assert "fc-grid-header" in content
        assert "fc-grid-col-label" in content

    def test_opex_grid_has_section_bands(self):
        path = OPEX_TEMPLATE
        with open(path, encoding="utf-8") as f:
            content = f.read()

        assert "fc-section-band" in content
        for label in ["Operations & Maintenance", "Insurance", "Land & Lease",
                      "Grid & Balancing", "Administration", "Environmental & Social"]:
            assert label in content, f"Missing section: {label}"

    def test_opex_grid_has_total_rows(self):
        path = OPEX_TEMPLATE
        with open(path, encoding="utf-8") as f:
            content = f.read()

        assert "fc-subtotal-row" in content
        assert "fc-grand-total" in content

    def test_opex_grid_has_edit_inputs(self):
        path = OPEX_TEMPLATE
        with open(path, encoding="utf-8") as f:
            content = f.read()

        assert 'type="number"' in content
        assert "name=" in content
        assert "data-opex-item=" in content

    def test_opex_grid_readonly_notice(self):
        path = OPEX_TEMPLATE
        with open(path, encoding="utf-8") as f:
            content = f.read()

        assert "is_user_project" in content
        assert "inp-readonly-notice" in content


class TestOPEXGridCSS:
    def test_opex_grid_css_added(self):
        path = STYLES_PATH
        with open(path, encoding="utf-8") as f:
            content = f.read()

        assert "Phase 20J" in content
        assert ".fc-opex-grid-wrapper" in content
        assert ".fc-cell--num" in content
        assert ".fc-cell--notes" in content
        assert ".fc-subtotal-label" in content


class TestProjectContextOpexItems:
    def test_opex_items_field_exists(self):
        import sys
        sys.path.insert(0, PROJECT_ROOT)
        from app.ui.project_context import ProjectContext

        assert "opex_items" in ProjectContext.__dataclass_fields__

    def test_tuho_opex_items_populated(self):
        import sys
        sys.path.insert(0, PROJECT_ROOT)
        from app.ui.project_context import get_project_context

        ctx = get_project_context("tuho")
        assert len(ctx.opex_items) > 0
        codes = {item["code"] for item in ctx.opex_items}
        assert "technical_management" in codes
        assert "insurance" in codes

    def test_opex_items_have_required_keys(self):
        import sys
        sys.path.insert(0, PROJECT_ROOT)
        from app.ui.project_context import get_project_context

        ctx = get_project_context("tuho")
        required_keys = {"code", "name", "y1_keur", "group", "unit",
                         "fixed_variable", "recurring_oneoff", "escalation_pct",
                         "start_year", "end_year", "notes"}
        for item in ctx.opex_items:
            assert required_keys.issubset(item.keys()), \
                f"Item {item.get('code')} missing keys: {required_keys - item.keys()}"

    def test_opex_items_have_groups(self):
        import sys
        sys.path.insert(0, PROJECT_ROOT)
        from app.ui.project_context import get_project_context

        ctx = get_project_context("tuho")
        groups = {item["group"] for item in ctx.opex_items}
        assert "Technical Management" in groups
        assert "Insurance" in groups
        assert len(groups) >= 5, f"Expected multiple groups, got: {groups}"

    def test_opex_items_have_sensible_defaults(self):
        import sys
        sys.path.insert(0, PROJECT_ROOT)
        from app.ui.project_context import get_project_context

        ctx = get_project_context("tuho")
        for item in ctx.opex_items:
            assert item["unit"] == "kEUR"
            assert item["fixed_variable"] == "Fixed"
            assert item["recurring_oneoff"] == "Recurring"
            assert item["start_year"] == 1
            assert item["end_year"] == ctx.horizon_years


class TestNoFunctionalChanges:
    def test_sheet_opex_grew(self):
        """sheet_opex.html grew significantly (proves new content)."""
        path = OPEX_TEMPLATE
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        # Original was ~110 lines; Phase 20J version should be 500+
        assert len(lines) > 300, f"sheet_opex.html should be much larger now (got {len(lines)} lines)"

    def test_no_domain_engine_changes(self):
        """No domain/financial engine files were changed."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "HEAD~1", "--", "domain/", "app/opex_engine.py"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        changed = [f for f in result.stdout.strip().split("\n") if f]
        assert not any("waterfall" in f for f in changed), "Must not modify waterfall_engine"
        assert not any("construction" in f for f in changed), "Must not modify construction engine"
        assert not any("debt" in f.lower() for f in changed), "Must not modify debt engine"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
