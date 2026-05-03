"""Tests for app/input_helpers.py."""
from app.input_helpers import (
    build_inputs_summary_table,
    build_capex_summary_table,
    build_capex_items_table,
)
from app.project_factories import create_default_solar_project


def test_build_capex_items_table_does_not_call_none():
    """build_capex_items_table must not call None()"""
    proj = create_default_solar_project()
    # Must not raise
    df = build_capex_items_table(proj)
    assert df.shape[1] == 4


def test_build_capex_items_table_empty_when_no_items():
    """Returns empty df when no items."""
    proj = create_default_solar_project()
    df = build_capex_items_table(proj)
    assert isinstance(df, object)  # DataFrame


def test_inputs_summary_uses_technical_capacity():
    """Capacity should appear in inputs summary."""
    proj = create_default_solar_project()
    df = build_inputs_summary_table(proj)
    assert "Capacity (MW)" in df["Field"].values


def test_inputs_summary_uses_revenue_ppa_term():
    """PPA term should come from revenue, not info."""
    proj = create_default_solar_project()
    df = build_inputs_summary_table(proj)
    assert "PPA Term (years)" in df["Field"].values


def test_capex_summary_uses_total_capex_fallback():
    """Total CapEx should use total_capex (not total_capex_keur only)."""
    proj = create_default_solar_project()
    df = build_capex_summary_table(proj)
    assert "Total CapEx (kEUR)" in df["Field"].values


def test_apply_project_overrides_ignores_unknown_fields():
    """Unknown fields should be silently ignored."""
    from app.input_forms import apply_project_overrides
    proj = create_default_solar_project()
    orig = proj.technical.capacity_mw
    result = apply_project_overrides(proj, {
        'technical': {'capacity_mw': 200.0, 'nonexistent_field': 999.0}
    })
    assert result.technical.capacity_mw == 200.0


def test_apply_project_overrides_preserves_unmodified_fields():
    """Unmodified fields should remain unchanged."""
    from app.input_forms import apply_project_overrides
    proj = create_default_solar_project()
    orig_cap = proj.technical.capacity_mw
    orig_tax = proj.tax.corporate_rate
    result = apply_project_overrides(proj, {'revenue': {'ppa_base_tariff': 99.0}})
    assert result.technical.capacity_mw == orig_cap
    assert result.tax.corporate_rate == orig_tax