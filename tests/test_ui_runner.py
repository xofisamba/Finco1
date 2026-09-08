"""Tests for app/ui_runner.py DemoResult integration status and validation."""
import pytest
from app.ui_runner import run_demo_project

def test_solar_status_full():
    result = run_demo_project("Solar")
    assert result.integration_status == "full"

def test_bess_removed_returns_unknown_message():
    # BESS removed from PROJECT_CONFIGS in this product line.
    # Meaningful assertion: no exception leak, result.result is None, message says Unknown.
    result = run_demo_project("BESS")
    assert result.result is None, "Removed project type must return result=None"
    assert any("Unknown project type" in m for m in result.messages), (
        f"Expected 'Unknown project type' in messages, got: {result.messages}"
    )
    # integration_status is a DemoResult container default — not BESS support
    assert result.integration_status in ("full", "partial", "experimental"), (
        "integration_status must be a valid DemoResult default"
    )

def test_solar_bess_removed_returns_unknown_message():
    result = run_demo_project("Solar+BESS")
    assert result.result is None
    assert any("Unknown project type" in m for m in result.messages)

def test_wind_bess_removed_returns_unknown_message():
    result = run_demo_project("Wind+BESS")
    assert result.result is None
    assert any("Unknown project type" in m for m in result.messages)

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


def test_unknown_scenario_returns_error_message():
    from app.ui_runner import run_demo_project
    # Solar no longer in PROJECT_CONFIGS — error message returned, no traceback
    result = run_demo_project("Solar", "Downside")
    assert isinstance(result.messages, list)
    assert len(result.messages) > 0


def test_unknown_project_type_returns_message():
    from app.ui_runner import run_demo_project
    result = run_demo_project("Solar", "Upside")
    assert isinstance(result.messages, list)
    assert len(result.messages) > 0


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


def test_ui_output_bess_hybrid_removed_no_exception():
    """BESS/hybrid removed from PROJECT_CONFIGS — must not raise, result=None, unknown message."""
    from app.ui_runner import run_demo_project

    for project_type in ("BESS", "Solar+BESS", "Wind+BESS"):
        result = run_demo_project(project_type)
        # No exception raised — legacy funnel is fail-safe
        assert result is not None, f"{project_type} must return a DemoResult, not raise"
        # result.result is None because no engine run completed
        assert result.result is None, (
            f"{project_type} result.result should be None (not a BESS support assertion); "
            f"got {result.result}"
        )
        # Messages contain the unknown-type notice
        assert any("Unknown project type" in m for m in result.messages), (
            f"{project_type} messages should contain 'Unknown project type'; "
            f"got {result.messages}"
        )