from dataclasses import replace

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.senior_sculpting import SeniorSculptingConfig, SeniorSculptingMode
from tests.test_senior_rate_schedule_project_opt_in import (
    OBOROVO_EXCEL_SENIOR,
    TUHO_EXCEL_SENIOR,
    build_oborovo_senior_rate_config_fixture,
    build_tuho_senior_rate_config_fixture,
)


def _run(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _senior_row(period):
    return {
        "date": period.date.isoformat(),
        "opening": period.senior_balance_keur + period.senior_principal_keur,
        "interest": period.senior_interest_keur,
        "principal": period.senior_principal_keur,
        "ds": period.senior_ds_keur,
        "closing": period.senior_balance_keur,
    }


def _explicit_ds_config(excel_rows):
    schedule = [0.0] * 28
    for idx, row in excel_rows.items():
        schedule[idx] = row["ds"]
    return SeniorSculptingConfig(
        enabled=True,
        mode=SeniorSculptingMode.EXPLICIT_DEBT_SERVICE_SCHEDULE,
        explicit_debt_service_schedule=tuple(schedule),
    )


def _with_senior_flags(project, rate_config, sculpting_config):
    return replace(
        project,
        info=replace(
            project.info,
            use_senior_rate_schedule_engine=True,
            use_senior_sculpting_basis_engine=True,
        ),
        financing=replace(
            project.financing,
            senior_debt_interest_config=rate_config,
            senior_sculpting_config=sculpting_config,
        ),
    )


def _tuho_explicit_project():
    project = create_default_tuho_wind1()
    rate_config = build_tuho_senior_rate_config_fixture()
    return _with_senior_flags(project, rate_config, _explicit_ds_config(TUHO_EXCEL_SENIOR))


def _oborovo_explicit_project():
    project = create_default_oborovo()
    rate_config = build_oborovo_senior_rate_config_fixture()
    return _with_senior_flags(project, rate_config, _explicit_ds_config(OBOROVO_EXCEL_SENIOR))


def test_senior_sculpting_basis_flag_defaults_false():
    assert create_default_tuho_wind1().info.use_senior_sculpting_basis_engine is False
    assert create_default_oborovo().info.use_senior_sculpting_basis_engine is False
    assert create_default_tuho_wind1().financing.senior_sculpting_config.enabled is False


def test_legacy_flag_off_equivalence_with_sculpting_config_present():
    for factory in (create_default_tuho_wind1, create_default_oborovo):
        project = factory()
        baseline = _run(project)
        configured = replace(
            project,
            financing=replace(
                project.financing,
                senior_sculpting_config=SeniorSculptingConfig(
                    enabled=True,
                    mode=SeniorSculptingMode.EXPLICIT_DEBT_SERVICE_SCHEDULE,
                    explicit_debt_service_schedule=(2_000.0,) * 28,
                ),
            ),
        )
        flag_off = _run(configured)

        assert flag_off.total_revenue_keur == pytest.approx(baseline.total_revenue_keur, abs=0.0001)
        assert flag_off.total_opex_keur == pytest.approx(baseline.total_opex_keur, abs=0.0001)
        assert flag_off.total_senior_ds_keur == pytest.approx(baseline.total_senior_ds_keur, abs=0.0001)
        assert flag_off.total_shl_service_keur == pytest.approx(baseline.total_shl_service_keur, abs=0.0001)
        assert flag_off.total_distribution_keur == pytest.approx(baseline.total_distribution_keur, abs=0.0001)


def test_opening_policy_preserved_with_explicit_ds_mode():
    cases = (
        (_tuho_explicit_project, 43_359.0, 44_878.838),
        (_oborovo_explicit_project, 42_852.267, 43_938.299),
    )
    for project_factory, principal_only, principal_plus_idc in cases:
        first = _senior_row(_run(project_factory()).periods[0])

        assert first["opening"] == pytest.approx(principal_only, abs=0.30)
        assert first["opening"] != pytest.approx(principal_plus_idc, abs=0.30)


def test_tuho_explicit_debt_service_schedule_uses_mapped_periods():
    result = _run(_tuho_explicit_project())
    first = _senior_row(result.periods[0])
    final = _senior_row(result.periods[27])

    assert first["interest"] == pytest.approx(TUHO_EXCEL_SENIOR[0]["interest"], abs=0.10)
    assert first["ds"] == pytest.approx(TUHO_EXCEL_SENIOR[0]["ds"], abs=0.001)
    assert first["principal"] == pytest.approx(first["ds"] - first["interest"], abs=0.001)
    assert first["principal"] == pytest.approx(819.265, abs=0.10)

    assert final["ds"] == pytest.approx(TUHO_EXCEL_SENIOR[27]["ds"], abs=0.001)
    assert final["principal"] == pytest.approx(final["ds"] - final["interest"], abs=0.001)
    assert final["closing"] >= -0.0001


def test_oborovo_explicit_debt_service_schedule_uses_mapped_periods():
    result = _run(_oborovo_explicit_project())
    first = _senior_row(result.periods[0])
    final = _senior_row(result.periods[27])

    assert first["interest"] == pytest.approx(OBOROVO_EXCEL_SENIOR[0]["interest"], abs=0.10)
    assert first["ds"] == pytest.approx(OBOROVO_EXCEL_SENIOR[0]["ds"], abs=0.001)
    assert first["principal"] == pytest.approx(first["ds"] - first["interest"], abs=0.001)
    assert first["principal"] == pytest.approx(935.650, abs=0.10)

    assert final["ds"] == pytest.approx(OBOROVO_EXCEL_SENIOR[27]["ds"], abs=0.001)
    assert final["principal"] == pytest.approx(final["ds"] - final["interest"], abs=0.001)
    assert final["closing"] >= -0.0001


def test_unsupported_formula_based_sculpting_mode_raises_clear_error():
    project = create_default_tuho_wind1()
    project = replace(
        project,
        info=replace(project.info, use_senior_sculpting_basis_engine=True),
        financing=replace(
            project.financing,
            senior_sculpting_config=SeniorSculptingConfig(
                enabled=True,
                mode=SeniorSculptingMode.EXCEL_AVAILABLE_CFADS,
            ),
        ),
    )

    with pytest.raises(ValueError, match="not implemented"):
        _run(project)
