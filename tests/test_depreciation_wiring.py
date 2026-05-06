"""Behavioral test: advanced_capex_line_items wiring in ui_runner."""
import pytest
from app.ui_runner import run_demo_project
from app.capex_engine import build_capex_line_items_from_defaults


class TestDepreciationWiring:
    def test_advanced_capex_line_items_produces_different_tax_shield_than_legacy(self):
        demo_legacy = run_demo_project('Solar', 'Base')
        assert demo_legacy.result is not None, f"Legacy run should succeed: {demo_legacy.messages}"
        legacy_tax_shield = sum(p.tax_keur for p in demo_legacy.result.periods if p.tax_keur)

        items = build_capex_line_items_from_defaults('solar')
        assert len(items) > 0, "Should have default CAPEX line items for solar"

        demo_advanced = run_demo_project('Solar', 'Base', advanced_capex_line_items=items)
        assert demo_advanced.result is not None, f"Advanced run should succeed: {demo_advanced.messages}"
        advanced_tax_shield = sum(p.tax_keur for p in demo_advanced.result.periods if p.tax_keur)

        diff = abs(advanced_tax_shield - legacy_tax_shield)
        assert diff > 1.0, (
            f"Tax shield should differ between advanced and legacy paths. "
            f"Got legacy={legacy_tax_shield:.2f}, advanced={advanced_tax_shield:.2f}, diff={diff:.2f}. "
            f"This likely means generate_schedule() is NOT being called in the wiring."
        )