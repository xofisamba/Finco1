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
    # With scenario implemented, messages contain scenario delta summaries
    assert any("Downside" in m and "P50" in m for m in result.messages)


def test_upside_scenario_returns_inactive_notice():
    from app.ui_runner import run_demo_project
    result = run_demo_project("Solar", "Upside")
    # With scenario implemented, messages contain scenario delta summaries
    assert any("Upside" in m and ("P50" in m or "CapEx" in m or "Tariff" in m) for m in result.messages)


def test_ui_runner_reraises_when_env_flag_set():
    """FINCOGPT_RAISE_UI_ERRORS=1 must make exceptions propagate."""
    from app.ui_runner import run_demo_project
    import os, pytest
    # Use a scenario that forces an error (Portfolio with shared FinancingParams
    # that has no projects — we'll provide an override that triggers validation error)
    # Actually just test with Solar which is always valid, and verify the flag works
    # by patching _run_waterfall to raise.
    import unittest.mock as mock
    with mock.patch('app.ui_runner._run_waterfall', side_effect=RuntimeError("test error")):
        old_val = os.environ.get("FINCOGPT_RAISE_UI_ERRORS")
        try:
            os.environ["FINCOGPT_RAISE_UI_ERRORS"] = "1"
            with pytest.raises(RuntimeError, match="test error"):
                run_demo_project("Solar")
        finally:
            if old_val is not None:
                os.environ["FINCOGPT_RAISE_UI_ERRORS"] = old_val
            else:
                os.environ.pop("FINCOGPT_RAISE_UI_ERRORS", None)
    # Without the flag, RuntimeError should be caught and returned as message
    with mock.patch('app.ui_runner._run_waterfall', side_effect=RuntimeError("test error 2")):
        old_val = os.environ.get("FINCOGPT_RAISE_UI_ERRORS")
        try:
            os.environ.pop("FINCOGPT_RAISE_UI_ERRORS", None)
            result = run_demo_project("Solar")
            assert "test error 2" in result.messages[0]
        finally:
            if old_val is not None:
                os.environ["FINCOGPT_RAISE_UI_ERRORS"] = old_val


def test_ui_output_labels_bess_hybrid_partial():
    """UI must label BESS/hybrid projects as partial, not full."""
    from app.ui_runner import run_demo_project

    for project_type in ("BESS", "Solar+BESS", "Wind+BESS"):
        result = run_demo_project(project_type)
        assert result.integration_status == "partial", \
            f"{project_type} should have integration_status=partial, got {result.integration_status}"