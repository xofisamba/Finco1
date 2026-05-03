"""Tests for app/input_forms.py."""
import pytest
from app.input_forms import apply_project_overrides
from app.project_factories import create_default_solar_project


def test_apply_project_overrides_changes_capacity():
    proj = create_default_solar_project()
    overrides = {'technical': {'capacity_mw': 100.0}}
    result = apply_project_overrides(proj, overrides)
    assert result.technical.capacity_mw == 100.0


def test_apply_project_overrides_changes_tariff():
    proj = create_default_solar_project()
    overrides = {'revenue': {'ppa_base_tariff': 75.0}}
    result = apply_project_overrides(proj, overrides)
    assert result.revenue.ppa_base_tariff == 75.0


def test_apply_project_overrides_changes_target_dscr():
    proj = create_default_solar_project()
    overrides = {'financing': {'target_dscr': 1.30}}
    result = apply_project_overrides(proj, overrides)
    assert result.financing.target_dscr == 1.30


def test_apply_project_overrides_preserves_unmodified_fields():
    proj = create_default_solar_project()
    orig_cap = proj.technical.capacity_mw
    orig_tax = proj.tax.corporate_rate
    overrides = {'revenue': {'ppa_base_tariff': 99.0}}
    result = apply_project_overrides(proj, overrides)
    assert result.technical.capacity_mw == orig_cap
    assert result.tax.corporate_rate == orig_tax


def test_ui_runner_uses_project_inputs_override_for_solar():
    from app.ui_runner import run_demo_project
    proj = create_default_solar_project()
    override = apply_project_overrides(proj, {'technical': {'capacity_mw': 250.0}})
    result = run_demo_project("Solar", project_inputs_override=override)
    assert result.result is not None


def test_ui_runner_uses_project_inputs_override_for_wind():
    from app.ui_runner import run_demo_project
    from app.project_factories import create_default_wind_project
    proj = create_default_wind_project()
    override = apply_project_overrides(proj, {'technical': {'capacity_mw': 150.0}})
    result = run_demo_project("Wind", project_inputs_override=override)
    assert result.result is not None
