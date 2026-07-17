"""
tests/test_phase2a_engine_inputs.py — Phase 2A immutable input contract tests.

Covers:
- OperatingModelInput frozen dataclass hierarchy
- from_project_inputs adapter (generic, no-mutation, idempotent)
- validate_operating_model_input issue codes
- compute_input_fingerprint determinism
- Source immutability: adapter must not mutate ProjectInputs
"""
from __future__ import annotations

import dataclasses
import math
from datetime import date

import pytest

from financial_engine.inputs import (
    AssetInput,
    CalendarInput,
    DepreciationInput,
    InputProvenance,
    OpexInput,
    OpexLineInput,
    OperatingModelInput,
    RevenueInput,
    TechnicalInput,
    YieldScenario,
)
from financial_engine.provenance import compute_input_fingerprint
from financial_engine.validation import (
    ValidationSeverity,
    has_errors,
    validate_operating_model_input,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _minimal_valid_inputs(**overrides) -> OperatingModelInput:
    cal = CalendarInput(
        financial_close=date(2030, 1, 1),
        construction_months=12,
        horizon_years=20,
        ppa_years=10.0,
    )
    tech = TechnicalInput(
        capacity_mw=50.0,
        yield_scenario=YieldScenario.P50,
        operating_hours_p50=2000.0,
        operating_hours_p90_10y=1800.0,
        pv_degradation=0.004,
        plant_availability=0.99,
        grid_availability=0.99,
    )
    rev = RevenueInput(
        ppa_base_tariff_eur_mwh=60.0,
        ppa_term_years=10.0,
        ppa_index=0.02,
        ppa_production_share=1.0,
        market_prices_curve_eur_mwh=(80.0, 82.0),
        market_inflation=0.02,
        balancing_cost_pv_fraction=0.025,
        balancing_cost_wind_eur_mwh=0.0,
        co2_enabled=False,
        co2_price_eur_mwh=1.5,
    )
    opex = OpexInput(items=(
        OpexLineInput(
            name="O&M",
            y1_amount_keur=500.0,
            annual_inflation=0.025,
            step_changes=(),
            percentage_of_opex=0.0,
        ),
    ))
    dep = DepreciationInput(assets=(), period_count=41, cod_period=2)
    src = InputProvenance(source_id="test", baseline_commit_sha="abc")
    base = OperatingModelInput(
        calendar=cal, technical=tech, revenue=rev,
        opex=opex, depreciation=dep, source=src,
    )
    if not overrides:
        return base
    d = dataclasses.asdict(base)
    d.update(overrides)
    return OperatingModelInput(**{
        k: v for k, v in d.items()
        if k in {f.name for f in dataclasses.fields(OperatingModelInput)}
    })


# ---------------------------------------------------------------------------
# Frozen dataclass tests
# ---------------------------------------------------------------------------

def test_operating_model_input_is_frozen():
    inputs = _minimal_valid_inputs()
    with pytest.raises((dataclasses.FrozenInstanceError, TypeError)):
        inputs.calendar = inputs.calendar  # type: ignore[misc]


def test_calendar_input_is_frozen():
    cal = CalendarInput(
        financial_close=date(2030, 1, 1),
        construction_months=6,
        horizon_years=20,
        ppa_years=10.0,
    )
    with pytest.raises((dataclasses.FrozenInstanceError, TypeError)):
        cal.horizon_years = 25  # type: ignore[misc]


def test_opex_items_are_tuples():
    inputs = _minimal_valid_inputs()
    assert isinstance(inputs.opex.items, tuple)


def test_depreciation_assets_are_tuples():
    inputs = _minimal_valid_inputs()
    assert isinstance(inputs.depreciation.assets, tuple)


def test_market_prices_curve_is_tuple():
    inputs = _minimal_valid_inputs()
    assert isinstance(inputs.revenue.market_prices_curve_eur_mwh, tuple)


# ---------------------------------------------------------------------------
# Adapter tests
# ---------------------------------------------------------------------------

def test_adapter_does_not_mutate_project_inputs():
    """Adapting must not mutate the source ProjectInputs."""
    from app.project_factories import create_default_tuho_wind1
    from financial_engine.adapters.project_inputs import from_project_inputs

    original = create_default_tuho_wind1()
    original_capacity = original.technical.capacity_mw
    original_tariff = original.revenue.ppa_base_tariff
    original_opex_count = len(original.opex)

    from_project_inputs(
        original,
        depreciation_period_count=61,
        depreciation_cod_period=2,
    )

    assert original.technical.capacity_mw == original_capacity
    assert original.revenue.ppa_base_tariff == original_tariff
    assert len(original.opex) == original_opex_count


def test_adapter_is_idempotent():
    """Same ProjectInputs always produces the same OperatingModelInput."""
    from app.project_factories import create_default_tuho_wind1
    from financial_engine.adapters.project_inputs import from_project_inputs

    p = create_default_tuho_wind1()
    r1 = from_project_inputs(p, depreciation_period_count=61, depreciation_cod_period=2)
    r2 = from_project_inputs(p, depreciation_period_count=61, depreciation_cod_period=2)
    assert r1 == r2


def test_adapter_preserves_capacity():
    from app.project_factories import create_default_tuho_wind1
    from financial_engine.adapters.project_inputs import from_project_inputs

    p = create_default_tuho_wind1()
    adapted = from_project_inputs(p, depreciation_period_count=61, depreciation_cod_period=2)
    assert adapted.technical.capacity_mw == p.technical.capacity_mw


def test_adapter_preserves_tariff():
    from app.project_factories import create_default_tuho_wind1
    from financial_engine.adapters.project_inputs import from_project_inputs

    p = create_default_tuho_wind1()
    adapted = from_project_inputs(p, depreciation_period_count=61, depreciation_cod_period=2)
    assert adapted.revenue.ppa_base_tariff_eur_mwh == p.revenue.ppa_base_tariff


def test_adapter_preserves_opex_items():
    from app.project_factories import create_default_tuho_wind1
    from financial_engine.adapters.project_inputs import from_project_inputs

    p = create_default_tuho_wind1()
    adapted = from_project_inputs(p, depreciation_period_count=61, depreciation_cod_period=2)
    assert len(adapted.opex.items) == len(p.opex)
    for clean_item, orig_item in zip(adapted.opex.items, p.opex):
        assert clean_item.name == orig_item.name
        assert clean_item.y1_amount_keur == orig_item.y1_amount_keur


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

def test_valid_inputs_produce_no_errors():
    inputs = _minimal_valid_inputs()
    issues = validate_operating_model_input(inputs)
    assert not has_errors(issues)


def test_cal001_financial_close_required():
    """CAL001: financial_close is required."""
    cal = CalendarInput(
        financial_close=None,  # type: ignore[arg-type]
        construction_months=6,
        horizon_years=20,
        ppa_years=10.0,
    )
    inputs = _minimal_valid_inputs()
    # Rebuild with bad calendar
    inputs2 = OperatingModelInput(
        calendar=cal,
        technical=inputs.technical,
        revenue=inputs.revenue,
        opex=inputs.opex,
        depreciation=inputs.depreciation,
        source=inputs.source,
    )
    issues = validate_operating_model_input(inputs2)
    codes = {i.code for i in issues}
    assert "CAL001" in codes
    assert has_errors(issues)


def test_cal003_horizon_must_be_positive():
    inputs = _minimal_valid_inputs()
    cal = dataclasses.replace(inputs.calendar, horizon_years=0)
    inputs2 = dataclasses.replace(inputs, calendar=cal)
    issues = validate_operating_model_input(inputs2)
    assert any(i.code == "CAL003" for i in issues)
    assert has_errors(issues)


def test_tech001_capacity_must_be_non_negative():
    inputs = _minimal_valid_inputs()
    tech = dataclasses.replace(inputs.technical, capacity_mw=-1.0)
    inputs2 = dataclasses.replace(inputs, technical=tech)
    issues = validate_operating_model_input(inputs2)
    assert any(i.code == "TECH001" for i in issues)
    assert has_errors(issues)


def test_tech006_plant_availability_out_of_range():
    inputs = _minimal_valid_inputs()
    tech = dataclasses.replace(inputs.technical, plant_availability=1.5)
    inputs2 = dataclasses.replace(inputs, technical=tech)
    issues = validate_operating_model_input(inputs2)
    assert any(i.code == "TECH006" for i in issues)
    assert has_errors(issues)


def test_rev001_nan_tariff_is_error():
    inputs = _minimal_valid_inputs()
    rev = dataclasses.replace(inputs.revenue, ppa_base_tariff_eur_mwh=float("nan"))
    inputs2 = dataclasses.replace(inputs, revenue=rev)
    issues = validate_operating_model_input(inputs2)
    assert any(i.code == "REV001" for i in issues)
    assert has_errors(issues)


def test_cal005_ppa_exceeds_horizon_is_warning():
    inputs = _minimal_valid_inputs()
    cal = dataclasses.replace(inputs.calendar, ppa_years=25.0, horizon_years=20)
    inputs2 = dataclasses.replace(inputs, calendar=cal)
    issues = validate_operating_model_input(inputs2)
    assert any(i.code == "CAL005" and i.severity == ValidationSeverity.WARNING for i in issues)
    assert not has_errors(issues)


def test_dep004_asset_life_must_be_positive():
    asset = AssetInput(
        asset_class="civil",
        gross_asset_basis_keur=10000.0,
        book_depreciable_basis_keur=10000.0,
        tax_depreciable_basis_keur=10000.0,
        placed_in_service_period=2,
        book_useful_life_years=0,  # invalid
        tax_useful_life_years=20,
    )
    inputs = _minimal_valid_inputs()
    dep = dataclasses.replace(
        inputs.depreciation,
        assets=(asset,),
        period_count=41,
        cod_period=2,
    )
    inputs2 = dataclasses.replace(inputs, depreciation=dep)
    issues = validate_operating_model_input(inputs2)
    assert any(i.code == "DEP004" for i in issues)
    assert has_errors(issues)


def test_run_operating_model_refuses_on_errors():
    """run_operating_model must raise ValueError when validation produces ERRORs."""
    from financial_engine.orchestrator import run_operating_model
    inputs = _minimal_valid_inputs()
    cal = dataclasses.replace(inputs.calendar, horizon_years=0)
    inputs2 = dataclasses.replace(inputs, calendar=cal)
    with pytest.raises(ValueError, match="validation failed"):
        run_operating_model(inputs2)


# ---------------------------------------------------------------------------
# Fingerprint tests
# ---------------------------------------------------------------------------

def test_fingerprint_is_deterministic():
    inputs = _minimal_valid_inputs()
    assert compute_input_fingerprint(inputs) == compute_input_fingerprint(inputs)


def test_fingerprint_changes_on_capacity_change():
    inputs = _minimal_valid_inputs()
    tech2 = dataclasses.replace(inputs.technical, capacity_mw=51.0)
    inputs2 = dataclasses.replace(inputs, technical=tech2)
    assert compute_input_fingerprint(inputs) != compute_input_fingerprint(inputs2)


def test_fingerprint_changes_on_tariff_change():
    inputs = _minimal_valid_inputs()
    rev2 = dataclasses.replace(inputs.revenue, ppa_base_tariff_eur_mwh=61.0)
    inputs2 = dataclasses.replace(inputs, revenue=rev2)
    assert compute_input_fingerprint(inputs) != compute_input_fingerprint(inputs2)


def test_fingerprint_is_hex_sha256():
    inputs = _minimal_valid_inputs()
    fp = compute_input_fingerprint(inputs)
    assert len(fp) == 64
    int(fp, 16)  # must be valid hex
