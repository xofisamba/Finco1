"""Default-off TUHO gross accrued SHL interest bridge tests."""

from __future__ import annotations

import json
from dataclasses import fields, replace
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.financial_statements import assemble_financial_statements
from domain.inputs import ProjectInfo


TUHO_R27_TOTAL_KUER = 49_782.18248671982
TUHO_LEGACY_SHL_INTEREST_KUER = 39_434.911711302164
FIXTURE_PATH = Path("tests/fixtures/interest_limitation/tuho_interest_limitation_fixture.json")


def _run_project(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _tuho_fixture_periods():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["periods"]


def test_shl_gross_accrued_pnl_flag_defaults_false():
    project_info_fields = {field.name: field for field in fields(ProjectInfo)}

    assert project_info_fields["use_shl_gross_accrued_for_pnl"].default is False
    assert create_default_tuho_wind1().info.use_shl_gross_accrued_for_pnl is False
    assert create_default_oborovo().info.use_shl_gross_accrued_for_pnl is False


def test_flag_off_tuho_and_oborovo_preserve_legacy_pnl_r27_source():
    for factory in (create_default_tuho_wind1, create_default_oborovo):
        project = factory()
        waterfall = _run_project(project)
        statements = assemble_financial_statements(waterfall)

        assert statements.pnl.total_for_row("R27") == pytest.approx(
            -sum(period.shl_interest_keur for period in waterfall.periods),
            abs=0.0001,
        )
        assert waterfall.use_shl_gross_accrued_for_pnl is False


def test_tuho_flag_on_pnl_r27_uses_excel_gross_accrued_fixture():
    project = create_default_tuho_wind1()
    project = replace(project, info=replace(project.info, use_shl_gross_accrued_for_pnl=True))

    waterfall = _run_project(project)
    statements = assemble_financial_statements(waterfall)

    assert waterfall.project_code == "TUHO-WIND-1"
    assert waterfall.use_shl_gross_accrued_for_pnl is True
    assert sum(period.shl_interest_keur for period in waterfall.periods) == pytest.approx(
        TUHO_LEGACY_SHL_INTEREST_KUER,
        abs=0.01,
    )
    assert sum(period.shl_gross_accrued_interest_keur for period in waterfall.periods) == pytest.approx(
        TUHO_R27_TOTAL_KUER,
        abs=0.01,
    )
    assert statements.pnl.total_for_row("R27") == pytest.approx(-TUHO_R27_TOTAL_KUER, abs=0.01)


def test_tuho_flag_on_pnl_r27_matches_excel_fixture_by_period():
    project = create_default_tuho_wind1()
    project = replace(project, info=replace(project.info, use_shl_gross_accrued_for_pnl=True))
    waterfall = _run_project(project)
    statements = assemble_financial_statements(waterfall)

    for fixture_row in _tuho_fixture_periods():
        idx = int(fixture_row["period_index"])
        expected_gross = float(fixture_row["gross_shl_interest_r27"])

        assert waterfall.periods[idx].shl_gross_accrued_interest_keur == pytest.approx(
            expected_gross,
            abs=0.5,
        )
        assert statements.pnl.periods[idx].shl_interest_expense_keur == pytest.approx(
            -expected_gross,
            abs=0.5,
        )


def test_formula_derived_gross_field_is_additive_when_flag_off():
    project = create_default_tuho_wind1()
    engine = _build_period_engine(project)
    op_periods = [period for period in engine.periods() if period.is_operation]
    waterfall = WaterfallRunner(project, engine).run(WaterfallRunConfig.from_inputs(project, engine))

    opening_balance = project.financing.shl_amount_keur + project.financing.shl_idc_keur
    first_fraction = op_periods[0].day_fraction
    expected_first = opening_balance * project.financing.shl_rate * first_fraction

    assert waterfall.periods[0].shl_gross_accrued_interest_keur == pytest.approx(
        expected_first,
        abs=0.01,
    )


def test_oborovo_flag_on_is_rejected():
    project = create_default_oborovo()
    project = replace(project, info=replace(project.info, use_shl_gross_accrued_for_pnl=True))

    with pytest.raises(ValueError, match="Gross accrued SHL P&L bridge"):
        _run_project(project)


def test_flag_on_does_not_change_shl_cash_pik_or_runtime_outputs():
    legacy_project = create_default_tuho_wind1()
    flag_project = replace(
        legacy_project,
        info=replace(legacy_project.info, use_shl_gross_accrued_for_pnl=True),
    )

    legacy = _run_project(legacy_project)
    flag_on = _run_project(flag_project)

    assert [period.shl_interest_keur for period in flag_on.periods] == pytest.approx(
        [period.shl_interest_keur for period in legacy.periods],
        abs=0.0001,
    )
    assert [period.shl_pik_keur for period in flag_on.periods] == pytest.approx(
        [period.shl_pik_keur for period in legacy.periods],
        abs=0.0001,
    )
    assert [period.shl_principal_keur for period in flag_on.periods] == pytest.approx(
        [period.shl_principal_keur for period in legacy.periods],
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
    assert flag_on.total_distribution_keur == pytest.approx(legacy.total_distribution_keur, abs=0.0001)
