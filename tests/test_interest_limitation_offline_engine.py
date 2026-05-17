"""Offline interest limitation / fiscal reintegration engine tests."""

from __future__ import annotations

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from domain.tax.interest_limitation import (
    InterestLimitationConfig,
    InterestLimitationPeriodInput,
    InterestLimitationSignConvention,
    compute_interest_limitation_period,
    compute_interest_limitation_schedule,
)


def test_tuho_r34_matches_excel_fixture_period():
    config = InterestLimitationConfig(
        sign_convention=InterestLimitationSignConvention.SUBTRACT_FROM_TI,
        ratio_4to1_enabled=False,
        notes="TUHO Excel R34/R54 fixture",
    )
    period_input = InterestLimitationPeriodInput(
        period_index=7,
        gross_shl_interest_keur=1425.1,
        ebitda_keur=3209.2,
        thin_cap_active=True,
    )

    result = compute_interest_limitation_period(period_input, config)

    assert result.excess_absolute_cap_keur == pytest.approx(0.0)
    assert result.excess_ebitda_cap_keur == pytest.approx(462.34, abs=0.01)
    assert result.ratio_adjustment_keur == pytest.approx(0.0)
    assert result.combined_non_deductible_keur == pytest.approx(462.34, abs=0.01)
    assert result.fiscal_reintegration_keur == pytest.approx(-462.4, abs=0.5)
    assert result.taxable_income_adjustment_keur == pytest.approx(-462.4, abs=0.5)


def test_oborovo_r34_matches_excel_fixture_period():
    config = InterestLimitationConfig(
        sign_convention=InterestLimitationSignConvention.ADD_BACK,
        ratio_4to1_enabled=True,
        ratio_4to1_denom=1.0,
        notes="Oborovo Excel R34/R54 fixture",
    )
    period_input = InterestLimitationPeriodInput(
        period_index=0,
        gross_shl_interest_keur=636.8,
        ebitda_keur=5000.0,
        thin_cap_active=True,
    )

    result = compute_interest_limitation_period(period_input, config)

    assert result.excess_absolute_cap_keur == pytest.approx(0.0)
    assert result.excess_ebitda_cap_keur == pytest.approx(0.0)
    assert result.ratio_adjustment_keur == pytest.approx(-636.8)
    assert result.combined_non_deductible_keur == pytest.approx(-636.8)
    assert result.fiscal_reintegration_keur == pytest.approx(636.8, abs=0.5)
    assert result.taxable_income_adjustment_keur == pytest.approx(636.8, abs=0.5)


def test_tuho_sign_convention_subtracts_from_taxable_income():
    result = compute_interest_limitation_period(
        InterestLimitationPeriodInput(
            period_index=1,
            gross_shl_interest_keur=1000.0,
            ebitda_keur=2000.0,
            thin_cap_active=True,
        ),
        InterestLimitationConfig(
            sign_convention=InterestLimitationSignConvention.SUBTRACT_FROM_TI,
        ),
    )

    assert result.combined_non_deductible_keur == pytest.approx(400.0)
    assert result.fiscal_reintegration_keur == pytest.approx(-400.0)
    assert result.taxable_income_adjustment_keur < 0.0


def test_oborovo_sign_convention_adds_back_to_taxable_income():
    result = compute_interest_limitation_period(
        InterestLimitationPeriodInput(
            period_index=1,
            gross_shl_interest_keur=1000.0,
            ebitda_keur=2000.0,
            thin_cap_active=True,
            ratio_adjustment_keur=-1000.0,
        ),
        InterestLimitationConfig(
            sign_convention=InterestLimitationSignConvention.ADD_BACK,
            ratio_4to1_enabled=True,
        ),
    )

    assert result.combined_non_deductible_keur == pytest.approx(-600.0)
    assert result.fiscal_reintegration_keur == pytest.approx(600.0)
    assert result.taxable_income_adjustment_keur > 0.0


def test_thin_cap_inactive_zeroes_r57_r58_but_keeps_explicit_ratio_audit():
    result = compute_interest_limitation_period(
        InterestLimitationPeriodInput(
            period_index=0,
            gross_shl_interest_keur=5000.0,
            ebitda_keur=1000.0,
            thin_cap_active=False,
            ratio_adjustment_keur=0.0,
        ),
        InterestLimitationConfig(),
    )

    assert result.excess_absolute_cap_keur == pytest.approx(0.0)
    assert result.excess_ebitda_cap_keur == pytest.approx(0.0)
    assert result.ratio_adjustment_keur == pytest.approx(0.0)
    assert result.combined_non_deductible_keur == pytest.approx(0.0)


def test_schedule_totals_and_audit_fields_are_exposed():
    config = InterestLimitationConfig(
        sign_convention=InterestLimitationSignConvention.SUBTRACT_FROM_TI,
    )
    result = compute_interest_limitation_schedule(
        (
            InterestLimitationPeriodInput(0, 1000.0, 2000.0, True),
            InterestLimitationPeriodInput(1, 500.0, 2000.0, False),
        ),
        config,
    )

    assert len(result.periods) == 2
    assert result.total_gross_shl_interest_keur == pytest.approx(1500.0)
    assert result.total_combined_non_deductible_keur == pytest.approx(400.0)
    assert result.total_fiscal_reintegration_keur == pytest.approx(-400.0)
    assert result.total_taxable_income_adjustment_keur == pytest.approx(-400.0)
    assert result.periods[0].excess_absolute_cap_keur == pytest.approx(0.0)
    assert result.periods[0].excess_ebitda_cap_keur == pytest.approx(400.0)
    assert result.periods[0].ratio_adjustment_keur == pytest.approx(0.0)


def test_disabled_config_returns_zero_adjustment_audit_result():
    result = compute_interest_limitation_period(
        InterestLimitationPeriodInput(
            period_index=0,
            gross_shl_interest_keur=5000.0,
            ebitda_keur=1000.0,
            thin_cap_active=True,
        ),
        InterestLimitationConfig(enabled=False),
    )

    assert result.excess_absolute_cap_keur == pytest.approx(0.0)
    assert result.excess_ebitda_cap_keur == pytest.approx(0.0)
    assert result.combined_non_deductible_keur == pytest.approx(0.0)
    assert result.fiscal_reintegration_keur == pytest.approx(0.0)


def test_offline_engine_adds_no_project_info_flag_or_runtime_opt_in():
    tuho = create_default_tuho_wind1()
    oborovo = create_default_oborovo()

    assert not hasattr(tuho.info, "use_interest_limitation_engine")
    assert not hasattr(oborovo.info, "use_interest_limitation_engine")
    assert tuho.info.use_tax_bridge_engine is False
    assert oborovo.info.use_tax_bridge_engine is False
    assert tuho.info.use_shl_fcf_waterfall_engine is False
    assert oborovo.info.use_shl_fcf_waterfall_engine is False
    assert tuho.financing.use_tuho_r99_input_engine is False
    assert oborovo.financing.use_tuho_r99_input_engine is False
