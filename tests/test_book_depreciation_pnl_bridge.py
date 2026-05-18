"""Default-off book depreciation P&L bridge tests."""

from __future__ import annotations

from dataclasses import fields, replace

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.depreciation import (
    AssetClassConfig,
    DepreciationLedgerInput,
    DepreciationPolicy,
    build_depreciation_ledger,
)
from domain.financial_statements import assemble_financial_statements
from domain.inputs import ProjectInfo


TUHO_BOOK_DEPRECIATION_TOTAL_KEUR = 72_993.7
TUHO_TAX_DEPRECIATION_TOTAL_KEUR = 70_691.5
TUHO_BOOK_TAX_DIFFERENCE_KEUR = 2_302.2
OPERATING_PERIODS = 60


def _run_project(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _enable_book_depreciation_bridge(waterfall):
    waterfall.use_book_depreciation_for_pnl = True
    return waterfall


def _tuho_depreciation_fixture():
    return build_depreciation_ledger(
        DepreciationLedgerInput(
            asset_classes=(
                AssetClassConfig(
                    asset_class="tuho_aggregate_fixture",
                    gross_asset_basis_keur=TUHO_BOOK_DEPRECIATION_TOTAL_KEUR,
                    book_depreciable_basis_keur=TUHO_BOOK_DEPRECIATION_TOTAL_KEUR,
                    tax_depreciable_basis_keur=TUHO_TAX_DEPRECIATION_TOTAL_KEUR,
                    placed_in_service_period=0,
                    depreciation_start_period=0,
                    source_label="TUHO aggregate Dep R30/R31 fixture",
                ),
            ),
            policies={
                "tuho_aggregate_fixture": DepreciationPolicy(
                    useful_life_book_periods=OPERATING_PERIODS,
                    useful_life_tax_periods=OPERATING_PERIODS,
                    period_frequency="semiannual",
                )
            },
            period_count=OPERATING_PERIODS,
            period_frequency="semiannual",
            cod_period=0,
        )
    )


def test_book_depreciation_pnl_flag_defaults_false():
    project_info_fields = {field.name: field for field in fields(ProjectInfo)}

    assert project_info_fields["use_book_depreciation_for_pnl"].default is False
    assert create_default_tuho_wind1().info.use_book_depreciation_for_pnl is False
    assert create_default_oborovo().info.use_book_depreciation_for_pnl is False


def test_flag_off_tuho_and_oborovo_preserve_legacy_pnl_depreciation_source():
    for factory in (create_default_tuho_wind1, create_default_oborovo):
        waterfall = _run_project(factory())
        statements = assemble_financial_statements(waterfall)

        assert statements.pnl.total_for_row("R13") == pytest.approx(
            -sum(period.tax_depreciation_audit_keur for period in waterfall.periods),
            abs=0.0001,
        )
        assert getattr(waterfall, "use_book_depreciation_for_pnl", False) is False


def test_flag_on_tuho_pnl_r13_uses_book_depreciation_fixture():
    waterfall = _enable_book_depreciation_bridge(_run_project(create_default_tuho_wind1()))
    statements = assemble_financial_statements(waterfall)

    assert waterfall.project_code == "TUHO-WIND-1"
    assert statements.pnl.total_for_row("R13") == pytest.approx(
        -TUHO_BOOK_DEPRECIATION_TOTAL_KEUR,
        abs=0.1,
    )
    assert sum(period.tax_depreciation_audit_keur for period in waterfall.periods) == pytest.approx(
        TUHO_TAX_DEPRECIATION_TOTAL_KEUR,
        abs=0.1,
    )


def test_flag_on_tuho_pnl_r13_matches_aggregate_fixture_by_period():
    waterfall = _enable_book_depreciation_bridge(_run_project(create_default_tuho_wind1()))
    statements = assemble_financial_statements(waterfall)

    expected_period_depreciation = -(TUHO_BOOK_DEPRECIATION_TOTAL_KEUR / len(waterfall.periods))
    for period in statements.pnl.periods:
        assert period.depreciation_keur == pytest.approx(expected_period_depreciation, abs=0.01)


def test_offline_tax_depreciation_fixture_remains_separate_and_unchanged():
    fixture = _tuho_depreciation_fixture()

    assert fixture.total_tax_depreciation_keur == pytest.approx(
        TUHO_TAX_DEPRECIATION_TOTAL_KEUR,
        abs=0.1,
    )
    assert (
        fixture.total_book_depreciation_keur - fixture.total_tax_depreciation_keur
    ) == pytest.approx(TUHO_BOOK_TAX_DIFFERENCE_KEUR, abs=0.1)


def test_oborovo_flag_on_is_rejected():
    waterfall = _enable_book_depreciation_bridge(_run_project(create_default_oborovo()))

    with pytest.raises(ValueError, match="Book depreciation P&L bridge"):
        assemble_financial_statements(waterfall)


def test_project_factories_do_not_opt_in_book_depreciation_bridge():
    assert create_default_tuho_wind1().info.use_book_depreciation_for_pnl is False
    assert create_default_oborovo().info.use_book_depreciation_for_pnl is False


def test_book_depreciation_bridge_does_not_change_runtime_or_tax_bridge_fields():
    legacy_project = create_default_tuho_wind1()
    flag_project = replace(
        legacy_project,
        info=replace(legacy_project.info, use_book_depreciation_for_pnl=True),
    )

    legacy = _run_project(legacy_project)
    flag_on = _run_project(flag_project)
    flag_on.use_book_depreciation_for_pnl = True

    assert [period.tax_depreciation_audit_keur for period in flag_on.periods] == pytest.approx(
        [period.tax_depreciation_audit_keur for period in legacy.periods],
        abs=0.0001,
    )
    assert [period.corporate_tax_cash_keur for period in flag_on.periods] == pytest.approx(
        [period.corporate_tax_cash_keur for period in legacy.periods],
        abs=0.0001,
    )
    assert [period.r99_fcf_for_distribution_keur for period in flag_on.periods] == pytest.approx(
        [period.r99_fcf_for_distribution_keur for period in legacy.periods],
        abs=0.0001,
    )
    assert flag_project.info.use_shl_fcf_waterfall_engine is False
    assert flag_project.financing.use_tuho_r99_input_engine is False
    assert flag_on.total_revenue_keur == pytest.approx(legacy.total_revenue_keur, abs=0.0001)
    assert flag_on.total_opex_keur == pytest.approx(legacy.total_opex_keur, abs=0.0001)
    assert flag_on.total_tax_keur == pytest.approx(legacy.total_tax_keur, abs=0.0001)
