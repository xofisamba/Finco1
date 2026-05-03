"""Tests for app/ui_runner.py DemoResult integration status and validation."""
import pytest
from app.ui_runner import run_demo_project

def test_solar_status_full():
    result = run_demo_project("Solar")
    assert result.integration_status == "full"

def test_bess_status_partial():
    result = run_demo_project("BESS")
    assert result.integration_status == "partial"

def test_solar_bess_status_partial():
    result = run_demo_project("Solar+BESS")
    assert result.integration_status == "partial"

def test_wind_bess_status_partial():
    result = run_demo_project("Wind+BESS")
    assert result.integration_status == "partial"

def test_portfolio_status_experimental():
    result = run_demo_project("Portfolio")
    assert result.integration_status == "experimental"

def test_ui_runner_returns_validation_issues_list():
    result = run_demo_project("Solar")
    assert isinstance(result.validation_issues, list)

def test_solar_has_no_error_severity_issues():
    result = run_demo_project("Solar")
    errors = [i for i in result.validation_issues if i.severity == "error"]
    assert len(errors) == 0, f"Unexpected validation errors: {errors}"

def test_wind_status_full():
    result = run_demo_project("Wind")
    assert result.integration_status == "full"

def test_wind_has_no_error_severity_issues():
    result = run_demo_project("Wind")
    errors = [i for i in result.validation_issues if i.severity == "error"]
    assert len(errors) == 0, f"Unexpected validation errors: {errors}"


def test_downside_scenario_returns_inactive_notice():
    from app.ui_runner import run_demo_project
    result = run_demo_project("Solar", "Downside")
    assert any("informational" in m.lower() or "not yet implemented" in m.lower() for m in result.messages)


def test_upside_scenario_returns_inactive_notice():
    from app.ui_runner import run_demo_project
    result = run_demo_project("Solar", "Upside")
    assert any("informational" in m.lower() or "not yet implemented" in m.lower() for m in result.messages)