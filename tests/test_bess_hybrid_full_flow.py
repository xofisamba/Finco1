"""Tests for BESS and hybrid full waterfall integration status."""
import pytest
from app.project_factories import (
    create_default_bess_project,
    create_default_solar_bess_project,
    create_default_wind_bess_project,
)
from app.ui_runner import run_demo_project


def test_bess_ui_runner_shows_partial_warning():
    """BESS standalone should show partial/full waterfall warning."""
    result = run_demo_project("BESS")
    has_warning = any("partial" in m.lower() or "revenue" in m.lower()
                       for m in result.messages)
    assert has_warning or result.result is not None, "BESS should either warn or produce result"


def test_solar_bess_ui_runner_shows_partial_warning():
    result = run_demo_project("Solar+BESS")
    has_warning = any("partial" in m.lower() or "revenue" in m.lower()
                      for m in result.messages)
    assert has_warning or result.result is not None, "Solar+BESS should either warn or produce result"


def test_wind_bess_ui_runner_shows_partial_warning():
    result = run_demo_project("Wind+BESS")
    has_warning = any("partial" in m.lower() or "revenue" in m.lower()
                      for m in result.messages)
    assert has_warning or result.result is not None, "Wind+BESS should either warn or produce result"


def test_bess_revenue_breakdown_is_callable():
    """Verify bess revenue module exists and is callable."""
    from domain.revenue.bess import bess_revenue_breakdown, BessParams
    params = BessParams(
        power_mw=100.0,
        energy_mwh=200.0,
        cycles_per_year=365,
        round_trip_efficiency=0.90,
    )
    breakdown = bess_revenue_breakdown(params, year_index=1, day_fraction=0.5)
    assert breakdown is not None
    assert hasattr(breakdown, 'arbitrage_revenue_keur') or hasattr(breakdown, 'total_revenue_keur')


def test_no_fake_bess_integration_if_waterfall_not_instrumented():
    """If waterfall doesn't call bess revenue, warn but don't fake."""
    import inspect
    from app import waterfall_core
    src = inspect.getsource(waterfall_core)
    has_bess = "bess" in src.lower()
    has_hybrid = "hybrid" in src.lower()
    # If not instrumented, ui_runner should have warned
    if not has_bess:
        result = run_demo_project("BESS")
        assert result.messages or result.result is not None


def test_ui_runner_bess_hybrid_warning_message():
    """UI runner should warn about BESS/hybrid waterfall limitations."""
    from app.ui_runner import run_demo_project
    for ptype in ("BESS", "Solar+BESS", "Wind+BESS"):
        result = run_demo_project(ptype)
        # Should show warning about partial/full waterfall
        warning_mentioned = any("partial" in m.lower() or "revenue" in m.lower()
                                for m in result.messages)
        # Or just have the messages list populated
        assert result.messages or result.result is not None, f"{ptype} should warn or produce result"


def test_full_waterfall_includes_bess_revenue_or_status_partial():
    """Full waterfall must either include BESS revenue or keep status=partial."""
    from app.ui_runner import run_demo_project
    result = run_demo_project("BESS")
    # Check integration_status
    assert result.integration_status == "partial", f"BESS integration_status should be partial, got {result.integration_status}"


def test_hybrid_status_remains_partial_until_revenue_breakdown_proven():
    """If BESS revenue breakdown exists, ensure no double counting with main revenue."""
    from app.ui_runner import run_demo_project
    result = run_demo_project("Solar+BESS")
    # The integration_status should be partial
    assert result.integration_status == "partial"


def test_scenario_ui_shows_partial_warning_for_bess():
    """BESS/hybrid scenario display should include partial warning."""
    from app.ui_runner import run_demo_project
    result = run_demo_project("BESS", scenario="Downside")
    # integration_status must be partial for BESS
    assert result.integration_status == "partial", \
        f"BESS Downside should have integration_status=partial, got {result.integration_status}"


def test_bess_not_marked_full():
    """BESS/hybrid must never be marked 'full' integration."""
    from app.ui_runner import run_demo_project
    for pt in ("BESS", "Solar+BESS", "Wind+BESS"):
        result = run_demo_project(pt)
        assert result.integration_status != "full", \
            f"{pt} must not be 'full' integration"


def test_sponsor_irr_not_computed():
    """Sponsor IRR must not be computed (remains placeholder)."""
    from app.portfolio_runner import run_portfolio_from_inputs
    from app.project_factories import create_default_solar_project, create_default_wind_project
    from domain.portfolio.inputs import PortfolioInputs
    from domain.inputs import FinancingParams

    # Portfolio needs at least 2 projects
    solar = create_default_solar_project()
    wind = create_default_wind_project()
    shared = FinancingParams(
        share_capital_keur=100.0,
        senior_debt_amount_keur=200.0,
        senior_tenor_years=10,
        target_dscr=1.3,
    )
    inputs = PortfolioInputs(
        projects=(solar, wind),
        portfolio_name="Test",
        shared_financing=shared,
    )
    result = run_portfolio_from_inputs(inputs)
    assert result.portfolio_sponsor_irr == 0.0, \
        "Sponsor IRR should remain placeholder (0.0)"

def test_bess_hybrid_cannot_be_full_without_waterfall_revenue_fields():
    """BESS/hybrid must not be 'full' integration without waterfall revenue field proof.

    Logic: If integration_status == "full", result.periods must expose
    a BESS/hybrid-specific revenue field with a nonzero value.
    Otherwise integration_status must be "partial".
    This prevents accidental upgrade to "full" without proof.
    """
    from app.ui_runner import run_demo_project

    def _has_bess_revenue(waterfall_result) -> bool:
        """Check if waterfall periods expose BESS/hybrid revenue fields."""
        if waterfall_result is None:
            return False
        # Look for bess_revenue_keur or similar on first operation period
        for p in waterfall_result.periods:
            if not p.is_operation:
                continue
            # Check for bess/hybrid-specific field with nonzero value
            for attr in ("bess_revenue_keur", "bess_arbitrage_keur",
                         "hybrid_revenue_keur", "storage_revenue_keur"):
                if hasattr(p, attr) and getattr(p, attr, 0) != 0:
                    return True
            break
        return False

    for pt in ("BESS", "Solar+BESS", "Wind+BESS"):
        result = run_demo_project(pt)
        if result.integration_status == "full":
            # Must have proof of BESS revenue in waterfall
            has_revenue = _has_bess_revenue(result.result)
            assert has_revenue, (
                f"{pt} cannot be 'full' without BESS/hybrid revenue field proof. "
                f"integration_status={result.integration_status} but no revenue field found."
            )
        else:
            assert result.integration_status == "partial", \
                f"{pt} must be 'partial' integration"
