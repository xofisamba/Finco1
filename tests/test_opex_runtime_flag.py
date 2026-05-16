from dataclasses import replace

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine, _run_waterfall
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.opex.projections import opex_schedule_period


def _run_project(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _with_opex_flag(project, enabled):
    return replace(project, info=replace(project.info, use_opex_line_item_engine=enabled))


def test_opex_line_item_engine_flag_defaults_false():
    assert create_default_tuho_wind1().info.use_opex_line_item_engine is False
    assert create_default_oborovo().info.use_opex_line_item_engine is False


def test_tuho_flag_false_keeps_legacy_opex_total():
    project = create_default_tuho_wind1()
    engine = _build_period_engine(project)
    result = _run_waterfall(project, engine, project_type="tuho")

    assert result.total_opex_keur == pytest.approx(sum(opex_schedule_period(project, engine).values()))
    assert result.total_opex_keur == pytest.approx(85_408.274134, abs=0.01)


def test_oborovo_flag_false_keeps_legacy_opex_total():
    project = create_default_oborovo()
    engine = _build_period_engine(project)
    result = _run_waterfall(project, engine, project_type="oborovo")

    assert result.total_opex_keur == pytest.approx(sum(opex_schedule_period(project, engine).values()))
    assert result.total_opex_keur == pytest.approx(51_220.761293, abs=0.01)


def test_tuho_flag_true_uses_line_item_engine():
    project = _with_opex_flag(create_default_tuho_wind1(), True)

    result = _run_project(project)

    assert result.total_opex_keur == pytest.approx(84_674.78, abs=0.01)


def test_oborovo_flag_true_is_rejected():
    project = _with_opex_flag(create_default_oborovo(), True)

    with pytest.raises(ValueError, match="TUHO-WIND-1"):
        _run_project(project)
