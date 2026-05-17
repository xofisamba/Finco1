"""Fixture-backed interest limitation parity checks.

The discovery record currently contains representative Excel-extracted periods
rather than a committed 60-period fixture table. These tests lock the extracted
R34/R54/R57/R58/R59 mechanics and explicitly avoid runtime tax wiring.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from domain.tax.interest_limitation import (
    InterestLimitationConfig,
    InterestLimitationPeriodInput,
    InterestLimitationSignConvention,
    compute_interest_limitation_period,
    compute_interest_limitation_schedule,
)


@dataclass(frozen=True)
class InterestLimitationFixturePeriod:
    project: str
    period_index: int
    gross_shl_interest_keur: float
    ebitda_keur: float
    thin_cap_active: bool
    ratio_adjustment_keur: float | None
    expected_r57_keur: float
    expected_r58_keur: float
    expected_r59_keur: float
    expected_r54_keur: float
    expected_r34_keur: float


TUHO_CONFIG = InterestLimitationConfig(
    sign_convention=InterestLimitationSignConvention.SUBTRACT_FROM_TI,
    ratio_4to1_enabled=False,
    notes="TUHO representative Excel fiscal reintegration fixtures",
)

OBOROVO_CONFIG = InterestLimitationConfig(
    sign_convention=InterestLimitationSignConvention.ADD_BACK,
    ratio_4to1_enabled=True,
    ratio_4to1_denom=1.0,
    notes="Oborovo representative Excel fiscal reintegration fixtures",
)

TUHO_REPRESENTATIVE_FIXTURES = (
    InterestLimitationFixturePeriod(
        project="TUHO",
        period_index=0,
        gross_shl_interest_keur=1297.4,
        ebitda_keur=4060.9,
        thin_cap_active=False,
        ratio_adjustment_keur=None,
        expected_r57_keur=0.0,
        expected_r58_keur=0.0,
        expected_r59_keur=0.0,
        expected_r54_keur=0.0,
        expected_r34_keur=0.0,
    ),
    InterestLimitationFixturePeriod(
        project="TUHO",
        period_index=7,
        gross_shl_interest_keur=1425.1,
        ebitda_keur=3209.2,
        thin_cap_active=True,
        ratio_adjustment_keur=None,
        expected_r57_keur=0.0,
        expected_r58_keur=462.34,
        expected_r59_keur=0.0,
        expected_r54_keur=462.34,
        expected_r34_keur=-462.34,
    ),
)

OBOROVO_REPRESENTATIVE_FIXTURES = (
    InterestLimitationFixturePeriod(
        project="Oborovo",
        period_index=0,
        gross_shl_interest_keur=636.8,
        ebitda_keur=5000.0,
        thin_cap_active=True,
        ratio_adjustment_keur=None,
        expected_r57_keur=0.0,
        expected_r58_keur=0.0,
        expected_r59_keur=-636.8,
        expected_r54_keur=-636.8,
        expected_r34_keur=636.8,
    ),
)


def _result_for_fixture(fixture: InterestLimitationFixturePeriod):
    config = TUHO_CONFIG if fixture.project == "TUHO" else OBOROVO_CONFIG
    return compute_interest_limitation_period(
        InterestLimitationPeriodInput(
            period_index=fixture.period_index,
            gross_shl_interest_keur=fixture.gross_shl_interest_keur,
            ebitda_keur=fixture.ebitda_keur,
            thin_cap_active=fixture.thin_cap_active,
            ratio_adjustment_keur=fixture.ratio_adjustment_keur,
        ),
        config,
    )


@pytest.mark.parametrize("fixture", TUHO_REPRESENTATIVE_FIXTURES)
def test_tuho_representative_r34_matches_excel_fixture(fixture):
    result = _result_for_fixture(fixture)

    assert result.excess_absolute_cap_keur == pytest.approx(fixture.expected_r57_keur, abs=0.5)
    assert result.excess_ebitda_cap_keur == pytest.approx(fixture.expected_r58_keur, abs=0.5)
    assert result.ratio_adjustment_keur == pytest.approx(fixture.expected_r59_keur, abs=0.5)
    assert result.combined_non_deductible_keur == pytest.approx(fixture.expected_r54_keur, abs=0.5)
    assert result.fiscal_reintegration_keur == pytest.approx(fixture.expected_r34_keur, abs=0.5)


@pytest.mark.parametrize("fixture", OBOROVO_REPRESENTATIVE_FIXTURES)
def test_oborovo_representative_r34_matches_excel_fixture(fixture):
    result = _result_for_fixture(fixture)

    assert result.excess_absolute_cap_keur == pytest.approx(fixture.expected_r57_keur, abs=0.5)
    assert result.excess_ebitda_cap_keur == pytest.approx(fixture.expected_r58_keur, abs=0.5)
    assert result.ratio_adjustment_keur == pytest.approx(fixture.expected_r59_keur, abs=0.5)
    assert result.combined_non_deductible_keur == pytest.approx(fixture.expected_r54_keur, abs=0.5)
    assert result.fiscal_reintegration_keur == pytest.approx(fixture.expected_r34_keur, abs=0.5)


def test_representative_fixture_totals_are_not_presented_as_full_horizon_parity():
    tuho_result = compute_interest_limitation_schedule(
        tuple(
            InterestLimitationPeriodInput(
                fixture.period_index,
                fixture.gross_shl_interest_keur,
                fixture.ebitda_keur,
                fixture.thin_cap_active,
                fixture.ratio_adjustment_keur,
            )
            for fixture in TUHO_REPRESENTATIVE_FIXTURES
        ),
        TUHO_CONFIG,
    )
    oborovo_result = compute_interest_limitation_schedule(
        tuple(
            InterestLimitationPeriodInput(
                fixture.period_index,
                fixture.gross_shl_interest_keur,
                fixture.ebitda_keur,
                fixture.thin_cap_active,
                fixture.ratio_adjustment_keur,
            )
            for fixture in OBOROVO_REPRESENTATIVE_FIXTURES
        ),
        OBOROVO_CONFIG,
    )

    assert tuho_result.total_fiscal_reintegration_keur == pytest.approx(-462.34, abs=0.5)
    assert oborovo_result.total_fiscal_reintegration_keur == pytest.approx(636.8, abs=0.5)
    assert len(tuho_result.periods) < 60
    assert len(oborovo_result.periods) < 60


def test_absolute_cap_formula_branch_is_covered_without_claiming_excel_period():
    result = compute_interest_limitation_period(
        InterestLimitationPeriodInput(
            period_index=999,
            gross_shl_interest_keur=5000.0,
            ebitda_keur=9000.0,
            thin_cap_active=True,
            ratio_adjustment_keur=0.0,
        ),
        InterestLimitationConfig(
            sign_convention=InterestLimitationSignConvention.ADD_BACK,
            notes="Synthetic branch coverage for R57 absolute cap",
        ),
    )

    assert result.excess_absolute_cap_keur == pytest.approx(2000.0)
    assert result.excess_ebitda_cap_keur == pytest.approx(2300.0)
    assert result.combined_non_deductible_keur == pytest.approx(2300.0)
    assert result.fiscal_reintegration_keur == pytest.approx(2300.0)


def test_no_runtime_tax_bridge_wiring_or_r99_acceptance_added():
    tax_bridge_source = Path("domain/financial_statements/tax_bridge.py").read_text(
        encoding="utf-8"
    )
    inputs_source = Path("domain/inputs.py").read_text(encoding="utf-8")

    assert "interest_limitation" not in tax_bridge_source
    assert "use_interest_limitation_engine" not in inputs_source
    assert create_default_tuho_wind1().financing.use_tuho_r99_input_engine is False
    assert create_default_oborovo().financing.use_tuho_r99_input_engine is False


def test_no_shl_fcf_or_tax_bridge_runtime_opt_in():
    tuho = create_default_tuho_wind1()
    oborovo = create_default_oborovo()

    assert tuho.info.use_shl_fcf_waterfall_engine is False
    assert oborovo.info.use_shl_fcf_waterfall_engine is False
    assert tuho.info.use_tax_bridge_engine is False
    assert oborovo.info.use_tax_bridge_engine is False
