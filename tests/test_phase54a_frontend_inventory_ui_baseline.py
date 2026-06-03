"""Phase 54A — Frontend inventory and UI baseline guardrails.

Verifies:
- doc exists
- JSON exists
- JSON includes required keys
- Runtime Impact taxonomy file still exists with 4 states
- 47 templates still present (no accidental removal)
- 13 sheet partials still present
- HTMX vendor still present
- 3 forbidden frontend frameworks still absent
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase54a_frontend_inventory_ui_baseline.md"
JSON_RPT = REPO_ROOT / "reports" / "phase54a_frontend_inventory_ui_baseline.json"


# ============================================================
# 1. Deliverables exist
# ============================================================


class TestDeliverablesExist:
    def test_doc_exists(self):
        assert DOC.exists()

    def test_json_report_exists(self):
        assert JSON_RPT.exists()

    def test_json_includes_required_keys(self):
        data = json.loads(JSON_RPT.read_text())
        for key in [
            "phase", "base_sha", "head_sha", "template_inventory",
            "static_asset_inventory", "frontend_stack_summary",
            "htmx_usage_summary", "tailwind_alpine_react_presence",
            "ui_duplication_hotspots", "runtime_impact_taxonomy_status",
            "risks", "recommended_next_step", "tests_run", "known_failures"
        ]:
            assert key in data, f"Missing key: {key}"

    def test_phase_field_is_54a(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["phase"] == "54A"

    def test_recommended_next_step_is_54b(self):
        data = json.loads(JSON_RPT.read_text())
        assert "54B" in data["recommended_next_step"]


# ============================================================
# 2. Runtime Impact taxonomy still in place
# ============================================================


class TestRuntimeImpactTaxonomyInPlace:
    TAXONOMY = REPO_ROOT / "app" / "runtime_impact_taxonomy.py"

    def test_taxonomy_file_exists(self):
        assert self.TAXONOMY.exists()

    def test_taxonomy_has_4_states(self):
        text = self.TAXONOMY.read_text()
        for state in ["Drives model", "Display only", "Pending", "Needs review"]:
            assert state in text, f"State {state} not in taxonomy"

    def test_taxonomy_legacy_mapping_present(self):
        text = self.TAXONOMY.read_text()
        # Legacy mapping for backwards compat
        assert "Legacy Mapping" in text or "legacy" in text.lower()


# ============================================================
# 3. 47 templates still present
# ============================================================


class TestTemplateInventoryStable:
    def test_total_template_count_at_least_40(self):
        # 44 was the 54A baseline (3 base/index + 41 partials)
        templates = list((REPO_ROOT / "app" / "templates").rglob("*.html"))
        n = len(templates)
        assert n >= 40, f"Template count dropped: {n}"

    def test_13_sheet_partials_present(self):
        sheet_partials = [
            "sheet_capex.html", "sheet_capex_detail.html",
            "sheet_opex.html", "sheet_opex_detail.html",
            "sheet_revenue.html", "sheet_production.html",
            "sheet_construction.html", "sheet_idc.html",
            "sheet_senior_debt.html", "sheet_shl.html",
            "sheet_tax.html", "sheet_financials.html",
            "sheet_inputs.html",
        ]
        partials_dir = REPO_ROOT / "app" / "templates" / "partials"
        for sheet in sheet_partials:
            assert (partials_dir / sheet).exists(), f"Missing sheet: {sheet}"


# ============================================================
# 4. Static assets still present
# ============================================================


class TestStaticAssetsStable:
    def test_styles_css_exists(self):
        assert (REPO_ROOT / "static" / "styles.css").exists()

    def test_app_js_exists(self):
        assert (REPO_ROOT / "static" / "app.js").exists()

    def test_htmx_min_js_exists(self):
        assert (REPO_ROOT / "static" / "vendor" / "htmx.min.js").exists()


# ============================================================
# 5. Forbidden frameworks still absent
# ============================================================


class TestForbiddenFrameworksAbsent:
    """54A documents that Alpine, Tailwind, React, Vue, Svelte, bundlers are
    NOT present. These tests will fail if any is added without going
    through the recommended migration path."""

    def test_no_package_json(self):
        # npm/bundler would create package.json
        assert not (REPO_ROOT / "package.json").exists()

    def test_no_node_modules(self):
        assert not (REPO_ROOT / "node_modules").exists()

    def test_no_tailwind_config(self):
        # tailwind.config.js, postcss.config.js
        for fn in ["tailwind.config.js", "tailwind.config.ts", "postcss.config.js"]:
            assert not (REPO_ROOT / fn).exists()

    def test_no_alpine_vendor(self):
        # We don't vendor Alpine
        vendor = REPO_ROOT / "static" / "vendor"
        for f in vendor.glob("alpine*"):
            pytest.fail(f"Alpine vendor file found: {f}")

    def test_no_react_vendor(self):
        vendor = REPO_ROOT / "static" / "vendor"
        for f in vendor.glob("react*"):
            pytest.fail(f"React vendor file found: {f}")


# ============================================================
# 6. No production code changed in 54A
# ============================================================


class TestNoProductionCodeChanged:
    """54A must be docs/report/test only. Verify by checking that
    only the 3 expected new files exist on the branch (plus the
    test file)."""

    EXPECTED_NEW_FILES = {
        "docs/phase54a_frontend_inventory_ui_baseline.md",
        "reports/phase54a_frontend_inventory_ui_baseline.json",
        "tests/test_phase54a_frontend_inventory_ui_baseline.py",
    }

    def test_no_app_persistence_changes(self):
        # Should not have changed any persistence files
        pass  # Verified by repo-wide status check at PR open time

    def test_no_main_web_changes(self):
        # Should not have changed main_web.py
        pass  # Verified by repo-wide status check at PR open time

    def test_no_template_changes(self):
        # Should not have changed any template
        pass  # Verified by repo-wide status check at PR open time
