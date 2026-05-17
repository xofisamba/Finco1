"""Full-horizon Excel-extracted interest limitation fixture tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from domain.tax.interest_limitation import (
    InterestLimitationConfig,
    InterestLimitationPeriodInput,
    InterestLimitationSignConvention,
    compute_interest_limitation_period,
)


FIXTURE_DIR = Path("tests/fixtures/interest_limitation")
TUHO_R34_TARGET = -9242.7
OBOROVO_R34_TARGET = 30935.2


def _load_fixture(filename: str) -> dict:
    return json.loads((FIXTURE_DIR / filename).read_text(encoding="utf-8"))


def _config_for_fixture(fixture: dict) -> InterestLimitationConfig:
    sign_convention = InterestLimitationSignConvention[fixture["sign_convention"]]
    return InterestLimitationConfig(
        sign_convention=sign_convention,
        ratio_4to1_enabled=fixture["project"] == "Oborovo",
        ratio_4to1_denom=1.0,
        notes=f"Excel extract fixture: {fixture['source_workbook']}",
    )


def _period_input(period: dict) -> InterestLimitationPeriodInput:
    return InterestLimitationPeriodInput(
        period_index=period["period_index"],
        gross_shl_interest_keur=period["gross_shl_interest_r27"],
        ebitda_keur=period["ebitda"],
        thin_cap_active=period["thin_cap_gate_r45"],
        ratio_adjustment_keur=period["r59_ratio_adjustment"],
    )


def _assert_period_parity(fixture: dict) -> None:
    config = _config_for_fixture(fixture)
    for period in fixture["periods"]:
        result = compute_interest_limitation_period(_period_input(period), config)

        assert result.excess_absolute_cap_keur == pytest.approx(
            period["r57_absolute_cap_excess"],
            abs=0.5,
        )
        assert result.excess_ebitda_cap_keur == pytest.approx(
            period["r58_ebitda_cap_excess"],
            abs=0.5,
        )
        assert result.ratio_adjustment_keur == pytest.approx(
            period["r59_ratio_adjustment"],
            abs=0.5,
        )
        assert result.combined_non_deductible_keur == pytest.approx(
            period["r54_helper"],
            abs=0.5,
        )
        assert result.fiscal_reintegration_keur == pytest.approx(
            period["r34_fiscal_reintegration"],
            abs=0.5,
        )


def _branch_counts(fixture: dict) -> dict[str, int]:
    periods = fixture["periods"]
    return {
        "inactive_gate": sum(not period["thin_cap_gate_r45"] for period in periods),
        "r57_binds": sum(abs(period["r57_absolute_cap_excess"]) > 1e-9 for period in periods),
        "r58_binds": sum(abs(period["r58_ebitda_cap_excess"]) > 1e-9 for period in periods),
        "r59_binds": sum(abs(period["r59_ratio_adjustment"]) > 1e-9 for period in periods),
        "r34_nonzero": sum(abs(period["r34_fiscal_reintegration"]) > 1e-9 for period in periods),
    }


def test_tuho_full_horizon_excel_extract_reproduces_r34_and_r54():
    fixture = _load_fixture("tuho_interest_limitation_fixture.json")

    assert fixture["project"] == "TUHO-WIND-1"
    assert fixture["period_count"] == 60
    assert fixture["missing_periods"] == []
    assert fixture["ambiguous_periods"] == []
    assert fixture["sign_convention"] == "SUBTRACT_FROM_TI"

    _assert_period_parity(fixture)

    assert fixture["cumulative_r34_fiscal_reintegration"] == pytest.approx(
        TUHO_R34_TARGET,
        abs=0.5,
    )


def test_oborovo_full_horizon_excel_extract_reproduces_r34_and_r54():
    fixture = _load_fixture("oborovo_interest_limitation_fixture.json")

    assert fixture["project"] == "Oborovo"
    assert fixture["period_count"] == 60
    assert fixture["missing_periods"] == []
    assert fixture["ambiguous_periods"] == []
    assert fixture["sign_convention"] == "ADD_BACK"

    _assert_period_parity(fixture)

    assert fixture["cumulative_r34_fiscal_reintegration"] == pytest.approx(
        OBOROVO_R34_TARGET,
        abs=0.5,
    )


def test_branch_coverage_diagnostics_are_explicit():
    tuho = _load_fixture("tuho_interest_limitation_fixture.json")
    oborovo = _load_fixture("oborovo_interest_limitation_fixture.json")

    tuho_counts = _branch_counts(tuho)
    oborovo_counts = _branch_counts(oborovo)

    assert tuho_counts["inactive_gate"] > 0
    assert tuho_counts["r58_binds"] > 0
    assert tuho_counts["r34_nonzero"] > 0
    assert tuho_counts["r57_binds"] == 0
    assert tuho_counts["r59_binds"] == 0

    assert oborovo_counts["inactive_gate"] == 60
    assert oborovo_counts["r59_binds"] > 0
    assert oborovo_counts["r34_nonzero"] > 0
    assert oborovo_counts["r57_binds"] == 0
    assert oborovo_counts["r58_binds"] == 0


def test_fixture_metadata_preserves_source_workbooks_and_formulas():
    tuho = _load_fixture("tuho_interest_limitation_fixture.json")
    oborovo = _load_fixture("oborovo_interest_limitation_fixture.json")

    assert tuho["source_workbook"] == "20260330_TUHO_BP.xlsm"
    assert oborovo["source_workbook"] == (
        "20260414_BP_Oborovo_Sensitivity_FINAL for PPT (1).xlsm"
    )

    for fixture in (tuho, oborovo):
        assert fixture["coverage"].startswith("full operating horizon")
        assert all("formulas" in period for period in fixture["periods"])
        assert all(period["formulas"]["r34"] for period in fixture["periods"])
        assert all(period["formulas"]["r54"] for period in fixture["periods"])


def test_no_runtime_wiring_or_source_acceptance_added_by_extract_branch():
    tax_bridge_source = Path("domain/financial_statements/tax_bridge.py").read_text(
        encoding="utf-8"
    )
    inputs_source = Path("domain/inputs.py").read_text(encoding="utf-8")

    assert "interest_limitation" not in tax_bridge_source
    assert "use_interest_limitation_engine" not in inputs_source
    assert "use_tuho_r99_input_engine: bool = True" not in inputs_source
