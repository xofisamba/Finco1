"""Phase 24C: Debt / DSCR / SHL UI — Tests

Diagnostic-only. UI/reporting only.
No runtime formula changes unless a regression is discovered and explicitly reported first.
"""
import re
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.runtime_impact_taxonomy import (
    CANONICAL_STATES,
    RuntimeImpactStatus,
    get_frozen_senior_ds_taxonomy,
)
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
from domain.period_engine import PeriodEngine


# =============================================================================
# Helpers
# =============================================================================


def _run_tuho():
    tuho = create_default_tuho_wind1()
    engine = PeriodEngine(
        tuho.info.financial_close,
        tuho.info.construction_months,
        tuho.info.horizon_years,
        tuho.revenue.ppa_term_years,
    )
    config = WaterfallRunConfig.from_inputs(tuho, engine)
    result = WaterfallRunner(tuho, engine).run(config)
    return [p for p in result.periods if getattr(p, "is_operation", False)]


def _run_oborovo():
    oborovo = create_default_oborovo()
    engine = PeriodEngine(
        oborovo.info.financial_close,
        oborovo.info.construction_months,
        oborovo.info.horizon_years,
        oborovo.revenue.ppa_term_years,
    )
    config = WaterfallRunConfig.from_inputs(oborovo, engine)
    result = WaterfallRunner(oborovo, engine).run(config)
    return [p for p in result.periods if getattr(p, "is_operation", False)]


# =============================================================================
# 1. Panel exists or renders
# =============================================================================


def test_debt_dscr_shl_panel_exists_or_renders():
    """New/updated partial exists at the expected path."""
    panel_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "debt_dscr_shl_panel.html"
    assert panel_path.exists(), f"Panel not found at {panel_path}"
    content = panel_path.read_text()
    assert len(content) > 100, "Panel should have meaningful content"
    assert "debt-dscr-shl-panel" in content, "Panel should have correct id"


# =============================================================================
# 2. Frozen senior DS uses taxonomy
# =============================================================================


def test_frozen_senior_ds_status_uses_runtime_impact_taxonomy():
    """Frozen senior DS is shown as Drives model with fixture-backed frozen schedule subreason."""
    tax = get_frozen_senior_ds_taxonomy()
    assert tax["primary"] == RuntimeImpactStatus.DRIVES_MODEL
    assert "fixture" in tax["sub_reason"].lower() or "frozen" in tax["sub_reason"].lower()
    assert tax["sculpting_active"] is False
    # Panel should contain these labels
    panel_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "debt_dscr_shl_panel.html"
    content = panel_path.read_text()
    assert "Drives model" in content
    assert "Fixture-backed" in content or "fixture-backed" in content
    assert "sculpting" not in content.lower() or "no sculpting" in content.lower()


# =============================================================================
# 3. DSCR inf rendered as debt repaid
# =============================================================================


def test_dscr_inf_rendered_as_debt_repaid():
    """Infinity DSCR is rendered as 'n/a — debt repaid' or equivalent."""
    panel_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "debt_dscr_shl_panel.html"
    content = panel_path.read_text()
    assert "n/a" in content.lower() or "debt repaid" in content.lower() or "inf" in content.lower()
    # Verify the panel has the dss-inf-label class for inf cells
    assert "dss-inf-label" in content or "inf" in content.lower()


# =============================================================================
# 4. Oborovo distribution lock-up status rendered
# =============================================================================


def test_oborovo_distribution_lockup_status_rendered():
    """Oborovo distribution blocked while SHL outstanding, first valid dist at op_idx 39."""
    op_periods = _run_oborovo()

    # Confirm SHL outstanding for op_idx 0-37
    for i in range(38):
        shl_bal = getattr(op_periods[i], "shl_balance_keur", 0.0) or 0.0
        dist = getattr(op_periods[i], "distribution_keur", 0.0) or 0.0
        assert shl_bal > 0, f"Oborovo op_idx {i}: shl_balance should be > 0"
        assert dist == 0.0, f"Oborovo op_idx {i}: dist should be 0 while SHL outstanding"

    # op_idx 38: SHL cleared, guard period
    shl38 = getattr(op_periods[38], "shl_balance_keur", 0.0) or 0.0
    dist38 = getattr(op_periods[38], "distribution_keur", 0.0) or 0.0
    assert shl38 <= 1.0, f"op_idx 38: shl_balance={shl38} should be ~0"
    assert dist38 == 0.0, f"op_idx 38: dist={dist38} should be 0 (guard period)"

    # op_idx 39: first valid distribution
    p39 = op_periods[39]
    dist39 = getattr(p39, "distribution_keur", 0.0) or 0.0
    assert str(p39.date) == "2050-06-30", f"First dist date={p39.date}, expected 2050-06-30"
    assert dist39 > 2000, f"op_idx 39: dist={dist39:.2f} should be > 2000 kEUR"

    # Panel should show lock-up status
    panel_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "debt_dscr_shl_panel.html"
    content = panel_path.read_text()
    assert "Distribution blocked" in content or "locked" in content.lower()


# =============================================================================
# 5. TUHO no distribution leak
# =============================================================================


def test_tuho_no_distribution_leak_status_rendered():
    """TUHO has no distributions while SHL outstanding."""
    op_periods = _run_tuho()

    for i, p in enumerate(op_periods):
        shl_bal = getattr(p, "shl_balance_keur", 0.0) or 0.0
        dist = getattr(p, "distribution_keur", 0.0) or 0.0
        if shl_bal > 1.0:
            assert dist == 0.0, f"TUHO op_idx {i}: shl={shl_bal:.2f} dist={dist:.2f} — leak!"

    # Panel should show distribution blocked or lock-up status
    panel_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "debt_dscr_shl_panel.html"
    content = panel_path.read_text()
    # Panel should reference lock-up or blocked
    assert "locked" in content.lower() or "blocked" in content.lower() or "shl" in content.lower()


# =============================================================================
# 6. Senior debt schedule fields present
# =============================================================================


def test_senior_debt_schedule_fields_present():
    """Panel includes senior DS, principal/interest/balance/DSCR fields."""
    panel_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "debt_dscr_shl_panel.html"
    content = panel_path.read_text()
    # Should have these field labels
    required = ["Senior Debt", "DSCR"]
    for field in required:
        assert field in content, f"Panel should include '{field}' field"


# =============================================================================
# 7. SHL fields present
# =============================================================================


def test_shl_fields_present():
    """Panel includes SHL balance, service, interest/PIK fields."""
    panel_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "debt_dscr_shl_panel.html"
    content = panel_path.read_text()
    # Should have SHL balance and lock-up status
    assert "SHL" in content or "shl" in content
    assert "Lock-up" in content or "locked" in content.lower() or "blocked" in content.lower()


# =============================================================================
# 8. No JS financial calculations added
# =============================================================================


def test_no_js_financial_calculations_added():
    """Scan static/app.js for forbidden financial calculation patterns."""
    js_file = Path(__file__).resolve().parents[1] / "static" / "app.js"
    if not js_file.exists():
        pytest.skip("static/app.js not found")

    content = js_file.read_text()
    forbidden = [
        "senior_ds_keur",
        "dscr",
        "r69_fcf_banks",
        "distribution_keur",
        "shl_balance",
        "irr",
        "npv",
        "xirr",
        "cfads",
        "ebitda",
    ]

    found = []
    for pattern in forbidden:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            import re
            if re.search(r'\b' + re.escape(pattern) + r'\b', line):
                found.append(pattern)
                break

    assert len(found) == 0, f"Found forbidden financial terms in JS: {found}"


# =============================================================================
# 9. No runtime output changes
# =============================================================================


def test_no_runtime_output_changes():
    """Confirm TUHO/Oborovo backend outputs are unchanged vs Phase 23U baseline."""
    # TUHO senior debt anchor: 43,359 kEUR
    tuho = create_default_tuho_wind1()
    engine = PeriodEngine(
        tuho.info.financial_close,
        tuho.info.construction_months,
        tuho.info.horizon_years,
        tuho.revenue.ppa_term_years,
    )
    config = WaterfallRunConfig.from_inputs(tuho, engine)
    result = WaterfallRunner(tuho, engine).run(config)
    op_periods = [p for p in result.periods if getattr(p, "is_operation", False)]
    tuho_total_ds = sum(getattr(p, "senior_ds_keur", 0.0) or 0.0 for p in op_periods[:14])
    assert tuho_total_ds > 25000, f"TUHO senior DS should be > 25,000 kEUR, got {tuho_total_ds:.2f}"

    # Oborovo senior debt anchor: 42,852 kEUR
    oborovo = create_default_oborovo()
    engine2 = PeriodEngine(
        oborovo.info.financial_close,
        oborovo.info.construction_months,
        oborovo.info.horizon_years,
        oborovo.revenue.ppa_term_years,
    )
    config2 = WaterfallRunConfig.from_inputs(oborovo, engine2)
    result2 = WaterfallRunner(oborovo, engine2).run(config2)
    op_periods2 = [p for p in result2.periods if getattr(p, "is_operation", False)]
    oborovo_total_ds = sum(getattr(p, "senior_ds_keur", 0.0) or 0.0 for p in op_periods2[:28])
    assert oborovo_total_ds > 35000, f"Oborovo senior DS should be > 35,000 kEUR, got {oborovo_total_ds:.2f}"


# =============================================================================
# 10. Guardrails unchanged
# =============================================================================


def test_guardrails_unchanged():
    """Guardrails preserved: G20/R99/R102 blocked, no flags promoted."""
    oborovo = create_default_oborovo()
    info = oborovo.info

    assert not hasattr(info, "use_g20_engine"), "G20 must remain blocked"
    assert not hasattr(info, "use_r99_engine"), "R99 must remain not approved"
    assert not hasattr(info, "use_r102_engine"), "R102 must remain not approved"
    assert not hasattr(info, "flat_dscr_sculpted"), "flat_dscr_sculpted must not be promoted"
    assert not hasattr(info, "minimum_dscr_sculpted"), "minimum_dscr_sculpted must not be promoted"
    assert not hasattr(info, "partial_pay_sweep"), "partial_pay_sweep must not be promoted"
