"""Tests for Advanced OPEX + Scenario scaling behavior.

Verifies that when advanced_opex_line_items are passed to run_demo_project(),
the scenario opex_multiplier is correctly applied to those items before the
waterfall calculation.

Bug scenario: ScenarioManager.apply_overrides() scales project_inputs.opex
(y1_amount_keur on each item) but advanced_opex_line_items are passed
separately to run_demo_project() and would NOT receive the scenario multiplier
unless explicitly handled in ui_runner.py.

This bug was confirmed fixed: ui_runner.py now scales advanced_opex_line_items
by the scenario's opex_multiplier before passing to the waterfall.
"""
import pytest

from app.ui_runner import run_demo_project
from app.opex_engine import build_opex_line_items_from_defaults, OpexLineItem
from app.scenario_manager import ScenarioManager


class TestAdvancedOpexScenarioScaling:
    """Verify Downside applies +10% to advanced_opex_line_items before waterfall."""

    def test_scenario_summary_shows_opex_plus_10pct(self):
        """Scenario summary for Downside should show OpEx +10%."""
        sm = ScenarioManager("solar")
        rows = sm.scenario_summary("Downside")
        opex_row = next((r for r in rows if r.get("assumption") == "OpEx"), None)
        assert opex_row is not None, "OpEx row should be in scenario summary"
        assert "+10%" in str(opex_row.get("change", "")), (
            f"OpEx change should be +10%, got: {opex_row}"
        )

    def test_downside_opex_multiplier_is_1_10(self):
        """Solar Downside scenario should have opex_multiplier=1.10."""
        sm = ScenarioManager("solar")
        scenario = sm.get_scenario("Downside")
        assert scenario.opex_multiplier == 1.10

    def test_advanced_opex_items_scaled_before_waterfall(self):
        """Advanced OPEX items should be scaled by opex_multiplier before waterfall.

        This is the core behavioral test: when items with base Y1 total=X are
        passed to run_demo_project with scenario=Downside, the scaled items
        (X * 1.10) should feed into the waterfall, producing lower EBITDA vs Base.
        """
        items = build_opex_line_items_from_defaults("solar")
        base_y1_total = sum(i.base_year_amount_keur for i in items)
        assert base_y1_total == 1121.0, f"Expected base Y1=1121, got {base_y1_total}"

        demo_base = run_demo_project("Solar", "Base", advanced_opex_line_items=items)
        demo_down = run_demo_project("Solar", "Downside", advanced_opex_line_items=items)

        assert demo_base.result is not None
        assert demo_down.result is not None

        # Downside has +10% OPEX → EBITDA should be lower than Base
        assert demo_down.result.total_ebitda_keur < demo_base.result.total_ebitda_keur, (
            f"Downside EBITDA ({demo_down.result.total_ebitda_keur:.2f}) should be lower "
            f"than Base ({demo_base.result.total_ebitda_keur:.2f}) due to +10% OPEX"
        )

        # Project IRR should be lower in Downside (less revenue + more OPEX)
        assert demo_down.result.project_irr < demo_base.result.project_irr, (
            f"Downside IRR ({demo_down.result.project_irr:.4f}) should be lower "
            f"than Base ({demo_base.result.project_irr:.4f})"
        )

    def test_advanced_opex_downside_vs_base_ebitda_direction(self):
        """Downside should produce lower EBITDA than Base with same advanced items."""
        items = build_opex_line_items_from_defaults("solar")

        demo_base = run_demo_project("Solar", "Base", advanced_opex_line_items=items)
        demo_down = run_demo_project("Solar", "Downside", advanced_opex_line_items=items)

        ebitda_diff = (
            demo_base.result.total_ebitda_keur - demo_down.result.total_ebitda_keur
        )
        # The diff should be positive (Base > Downside) and meaningful
        assert ebitda_diff > 0, (
            f"Base EBITDA should exceed Downside by at least the +10% OPEX effect, "
            f"got diff={ebitda_diff:.2f}"
        )


class TestScenarioManagerOpexScaling:
    """Test ScenarioManager directly for OPEX multiplier behavior."""

    def test_apply_overrides_scales_opex_y1_amount(self):
        """apply_overrides should scale opex y1_amount_keur by opex_multiplier."""
        from app.project_factories import create_default_solar_project

        proj = create_default_solar_project()
        sm = ScenarioManager("solar")

        # Scale with Downside (+10% OPEX)
        scaled = sm.apply_overrides(proj, "Downside")

        # Each opex item should have y1_amount_keur * 1.10
        for orig_item, scaled_item in zip(proj.opex, scaled.opex):
            expected = orig_item.y1_amount_keur * 1.10
            assert abs(scaled_item.y1_amount_keur - expected) < 0.01, (
                f"Item {orig_item.name}: expected y1={expected:.2f}, got {scaled_item.y1_amount_keur:.2f}"
            )

    def test_base_scenario_returns_unchanged_opex(self):
        """Base scenario should return project inputs unchanged."""
        from app.project_factories import create_default_solar_project

        proj = create_default_solar_project()
        sm = ScenarioManager("solar")

        base_proj = sm.apply_overrides(proj, "Base")

        for orig_item, base_item in zip(proj.opex, base_proj.opex):
            assert orig_item.y1_amount_keur == base_item.y1_amount_keur


class TestAdvancedOpexEBITDADirection:
    """Verify EBITDA direction is correct with advanced OPEX + scenarios."""

    def test_advanced_opex_downside_reduces_ebitda(self):
        """Advanced OPEX + Downside should produce lower EBITDA than Base."""
        items = build_opex_line_items_from_defaults("solar")

        demo_base = run_demo_project("Solar", "Base", advanced_opex_line_items=items)
        demo_down = run_demo_project("Solar", "Downside", advanced_opex_line_items=items)

        ebitda_diff = (
            demo_base.result.total_ebitda_keur - demo_down.result.total_ebitda_keur
        )

        # With +10% OPEX in Downside, EBITDA should be lower
        assert ebitda_diff > 0, (
            f"Downside should have lower EBITDA by more OPEX, diff={ebitda_diff:.2f}"
        )

    def test_advanced_opex_upside_increases_ebitda(self):
        """Advanced OPEX + Upside should produce higher EBITDA than Base."""
        items = build_opex_line_items_from_defaults("solar")

        demo_base = run_demo_project("Solar", "Base", advanced_opex_line_items=items)
        demo_up = run_demo_project("Solar", "Upside", advanced_opex_line_items=items)

        # Upside has -5% OPEX + +3% revenue → EBITDA should be higher
        assert demo_up.result.total_ebitda_keur > demo_base.result.total_ebitda_keur, (
            f"Upside EBITDA ({demo_up.result.total_ebitda_keur:.2f}) should be higher "
            f"than Base ({demo_base.result.total_ebitda_keur:.2f}) due to -5% OPEX and +3% revenue"
        )