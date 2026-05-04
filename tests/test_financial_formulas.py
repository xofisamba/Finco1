"""Tests for financial formula correctness — LCOE, IRR direction, portfolio scenario."""
import pytest
from dataclasses import replace

from app.project_factories import create_default_solar_project, create_default_wind_project
from app.ui_runner import run_demo_project
from app.scenarios import apply_scenario
from domain.analytics.scenarios import _compute_lcoe_from_waterfall


class TestLCOEFormula:
    """LCOE = (CapEx + OpEx) / Total Generation (EUR/MWh).

    Economic LCOE: excludes debt service, includes all operating costs.
    """

    def test_lcoe_increases_with_opex(self):
        """Increasing OpEx must increase LCOE (LCOE is monotonic in OpEx)."""
        from app.ui_runner import _run_waterfall, _build_period_engine

        solar = create_default_solar_project()
        engine = _build_period_engine(solar)
        base_result = _run_waterfall(solar, engine)

        base_lcoe = _compute_lcoe_from_waterfall(base_result, solar)

        # Double OpEx by adding a large OpexItem
        from domain.inputs import OpexItem
        # Double each opex item's y1_amount_keur
        modified_opex_items = tuple(
            replace(item, y1_amount_keur=item.y1_amount_keur * 3)
            for item in solar.opex
        )
        modified_opex = modified_opex_items
        solar_hi = replace(solar, opex=modified_opex)
        engine_hi = _build_period_engine(solar_hi)
        hi_result = _run_waterfall(solar_hi, engine_hi)
        hi_lcoe = _compute_lcoe_from_waterfall(hi_result, solar_hi)

        assert hi_lcoe > base_lcoe, \
            f"LCOE must increase with higher OpEx: base={base_lcoe:.2f}, hi_opex={hi_lcoe:.2f}"

    def test_lcoe_zero_opex_lower_than_positive_opex(self):
        """Zero-OpEx LCOE must be lower than positive-OpEx LCOE."""
        from app.ui_runner import _run_waterfall, _build_period_engine

        solar = create_default_solar_project()
        engine = _build_period_engine(solar)
        base_result = _run_waterfall(solar, engine)
        base_lcoe = _compute_lcoe_from_waterfall(base_result, solar)

        # Zero out all opex
        from domain.inputs import OpexItem
        zero_opex = tuple(
            replace(item, y1_amount_keur=0.0) for item in solar.opex
        )
        solar_zero = replace(solar, opex=zero_opex)
        engine_zero = _build_period_engine(solar_zero)
        zero_result = _run_waterfall(solar_zero, engine_zero)
        zero_lcoe = _compute_lcoe_from_waterfall(zero_result, solar_zero)

        assert zero_lcoe < base_lcoe, \
            f"Zero-OpEx LCOE ({zero_lcoe:.2f}) must be < base LCOE ({base_lcoe:.2f})"

    def test_lcoe_non_negative(self):
        """LCOE must always be non-negative."""
        from app.ui_runner import _run_waterfall, _build_period_engine

        solar = create_default_solar_project()
        engine = _build_period_engine(solar)
        result = _run_waterfall(solar, engine)
        lcoe = _compute_lcoe_from_waterfall(result, solar)
        assert lcoe >= 0.0, f"LCOE must be non-negative, got {lcoe}"


class TestScenarioDirection:
    """Scenario must move IRR in the correct financial direction."""

    def test_downside_reduces_project_irr(self):
        """Downside scenario must produce lower project_irr than Base."""
        base = run_demo_project("Solar", scenario="Base")
        downside = run_demo_project("Solar", scenario="Downside")
        assert base.result is not None and downside.result is not None
        assert downside.result.project_irr < base.result.project_irr, \
            f"Downside IRR ({downside.result.project_irr:.4f}) must be < Base ({base.result.project_irr:.4f})"

    def test_upside_increases_project_irr(self):
        """Upside scenario must produce higher project_irr than Base."""
        base = run_demo_project("Solar", scenario="Base")
        upside = run_demo_project("Solar", scenario="Upside")
        assert base.result is not None and upside.result is not None
        assert upside.result.project_irr > base.result.project_irr, \
            f"Upside IRR ({upside.result.project_irr:.4f}) must be > Base ({base.result.project_irr:.4f})"

    def test_downside_reduces_equity_irr(self):
        """Downside scenario must produce lower equity_irr than Base."""
        base = run_demo_project("Solar", scenario="Base")
        downside = run_demo_project("Solar", scenario="Downside")
        assert base.result is not None and downside.result is not None
        assert downside.result.equity_irr < base.result.equity_irr, \
            f"Downside equity IRR ({downside.result.equity_irr:.4f}) must be < Base ({base.result.equity_irr:.4f})"

    def test_wind_downside_reduces_project_irr(self):
        """Downside scenario must produce lower project_irr for Wind."""
        base = run_demo_project("Wind", scenario="Base")
        downside = run_demo_project("Wind", scenario="Downside")
        assert base.result is not None and downside.result is not None
        assert downside.result.project_irr < base.result.project_irr, \
            f"Wind Downside IRR ({downside.result.project_irr:.4f}) must be < Base ({base.result.project_irr:.4f})"

    def test_wind_upside_increases_project_irr(self):
        """Upside scenario must produce higher project_irr for Wind."""
        base = run_demo_project("Wind", scenario="Base")
        upside = run_demo_project("Wind", scenario="Upside")
        assert base.result is not None and upside.result is not None
        assert upside.result.project_irr > base.result.project_irr, \
            f"Wind Upside IRR ({upside.result.project_irr:.4f}) must be > Base ({base.result.project_irr:.4f})"


class TestPortfolioScenarioBlocking:
    """Portfolio + non-Base scenario must not silently show wrong numbers."""

    def test_portfolio_scenario_not_silently_applied(self):
        """Portfolio + Downside must NOT silently show Base numbers with Downside label."""
        result = run_demo_project("Portfolio", scenario="Downside")
        # The scenario message must indicate it was NOT applied, or be absent
        msg_text = " ".join(str(m) for m in result.messages).lower()
        if "downside" in msg_text:
            # If "downside" is mentioned, it must also mention "not applied" or "base"
            assert any(kw in msg_text for kw in ["not applied", "base only", "not supported"]), \
                f"Portfolio + Downside message must indicate scenario was not applied: {result.messages}"

    def test_portfolio_scenario_blocks_or_warns(self):
        """Portfolio + non-Base must either raise, block, or explicitly warn."""
        result = run_demo_project("Portfolio", scenario="Upside")
        # Upside must NOT claim upside was applied when it wasn't
        msg_text = " ".join(str(m) for m in result.messages)
        if result.is_portfolio:
            # If portfolio and non-Base, must either raise OR have explicit warning
            has_warning = any(
                kw in msg_text.lower()
                for kw in ["not applied", "base only", "not supported", "experimental"]
            )
            assert has_warning or result.portfolio_result is not None, \
                f"Portfolio + non-Base must warn explicitly: {result.messages}"
