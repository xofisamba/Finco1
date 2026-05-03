"""Tests for validation blocking in ui_runner."""
import pytest
from app.ui_runner import run_demo_project
from app.input_forms import apply_project_overrides
from app.project_factories import create_default_solar_project


def test_ui_runner_blocks_invalid_override_capacity():
    """Invalid capacity (0 or negative) should be blocked."""
    proj = create_default_solar_project()
    override = apply_project_overrides(proj, {'technical': {'capacity_mw': 0.0}})
    result = run_demo_project("Solar", project_inputs_override=override)
    # Should not run — result should be None
    assert result.result is None
    assert any("error" in m.lower() or "validation" in m.lower() for m in result.messages)


def test_ui_runner_returns_validation_issues_for_invalid_override():
    """Invalid override should return validation issues."""
    proj = create_default_solar_project()
    override = apply_project_overrides(proj, {'technical': {'capacity_mw': -10.0}})
    result = run_demo_project("Solar", project_inputs_override=override)
    assert result.validation_issues is not None
    assert len(result.validation_issues) > 0