"""FP-order sensitivity diagnostics.

Verifies that 2 consecutive run_demo_project('Solar', 'Base') calls
produce identical IRR values (±1bps), catching regressions.
"""
import pytest
from app.ui_runner import run_demo_project


def test_solar_base_determinism_irr():
    """IRR must be identical across 2 consecutive Solar Base runs (±1bps)."""
    r1 = run_demo_project("Solar", "Base").result
    r2 = run_demo_project("Solar", "Base").result
    diff_bps = abs(r1.project_irr - r2.project_irr) * 10_000
    assert diff_bps <= 1.0, f"IRR drift detected: {diff_bps:.2f} bps"


def test_solar_base_determinism_min_dscr():
    """Min DSCR must be identical across 2 consecutive Solar Base runs."""
    r1 = run_demo_project("Solar", "Base").result
    r2 = run_demo_project("Solar", "Base").result
    assert abs(r1.actual_min_dscr - r2.actual_min_dscr) < 1e-6


def test_solar_base_determinism_equity_irr():
    """Equity IRR must be identical across 2 consecutive Solar Base runs (±1bps)."""
    r1 = run_demo_project("Solar", "Base").result
    r2 = run_demo_project("Solar", "Base").result
    diff_bps = abs(r1.equity_irr - r2.equity_irr) * 10_000
    assert diff_bps <= 1.0, f"Equity IRR drift detected: {diff_bps:.2f} bps"


def test_wind_base_determinism_irr():
    """IRR must be identical across 2 consecutive Wind Base runs (±1bps)."""
    r1 = run_demo_project("Wind", "Base").result
    r2 = run_demo_project("Wind", "Base").result
    diff_bps = abs(r1.project_irr - r2.project_irr) * 10_000
    assert diff_bps <= 1.0, f"IRR drift detected: {diff_bps:.2f} bps"
