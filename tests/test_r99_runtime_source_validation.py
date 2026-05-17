"""Phase 7M tests for TUHO R99/R102 runtime source validation.

These tests are diagnostic guardrails. They intentionally do not accept any
runtime R99/R102 source yet.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.inputs import SHLRepaymentMethod
from tests.test_senior_dscr_sculpting_full_schedule_fixtures import (
    _load_excel_senior_fixture,
    _with_full_explicit_senior_fixture,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "excel_tuho_full_model_extract.json"
EXCEL_R99_TOTAL_KEUR = 234_745.44009403558
MATERIAL_TOLERANCE_PCT = 0.02
MATERIAL_FLOOR_KEUR = 100.0


def _run_project(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _excel_r99_schedule() -> tuple[float, ...]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    columns = {name: idx for idx, name in enumerate(payload["period_diagnostic_columns"])}
    return tuple(
        row[columns["CF.free_cash_flow_for_distribution_keur"]]
        for row in payload["period_diagnostics"]
    )


def _candidate_sources(result, horizon: int) -> dict[str, tuple[float, ...]]:
    periods = result.periods[:horizon]
    return {
        "c1d_r99_audit": tuple(p.r99_fcf_for_distribution_keur for p in periods),
        "c1d_r102_audit": tuple(p.r102_fcf_for_shl_keur for p in periods),
        "c1d_fcf_for_shl": tuple(p.fcf_for_shl_keur for p in periods),
        "r98_distribution_account": tuple(p.r98_distribution_account_keur for p in periods),
        "r84_fcf_junior": tuple(p.r84_fcf_junior_keur for p in periods),
        "cf_after_tax": tuple(p.cf_after_tax_keur for p in periods),
        "cf_after_tax_minus_senior_ds": tuple(
            p.cf_after_tax_keur - p.senior_ds_keur for p in periods
        ),
        "cf_after_reserves": tuple(p.cf_after_reserves_keur for p in periods),
    }


def _stats(values: tuple[float, ...], excel: tuple[float, ...]) -> dict[str, float]:
    deltas = tuple(value - expected for value, expected in zip(values, excel))
    material = [
        abs(delta) <= max(MATERIAL_FLOOR_KEUR, abs(expected) * MATERIAL_TOLERANCE_PCT)
        for delta, expected in zip(deltas, excel)
        if abs(expected) > MATERIAL_FLOOR_KEUR
    ]
    return {
        "total": sum(values),
        "total_delta": sum(deltas),
        "mae": sum(abs(delta) for delta in deltas) / len(deltas),
        "max_abs_delta": max(abs(delta) for delta in deltas),
        "material_periods": len(material),
        "material_periods_within_tolerance": sum(material),
    }


def _is_accepted(values: tuple[float, ...], excel: tuple[float, ...]) -> bool:
    stats = _stats(values, excel)
    if abs(stats["total_delta"]) > EXCEL_R99_TOTAL_KEUR * 0.01:
        return False
    return stats["material_periods_within_tolerance"] == stats["material_periods"]


def test_r99_source_validation_does_not_change_default_runtime_outputs():
    baseline = _run_project(create_default_tuho_wind1())
    candidate_run = _run_project(create_default_tuho_wind1())

    assert candidate_run.total_revenue_keur == pytest.approx(baseline.total_revenue_keur, abs=0.0001)
    assert candidate_run.total_opex_keur == pytest.approx(baseline.total_opex_keur, abs=0.0001)
    assert candidate_run.total_senior_ds_keur == pytest.approx(baseline.total_senior_ds_keur, abs=0.0001)
    assert candidate_run.total_shl_service_keur == pytest.approx(baseline.total_shl_service_keur, abs=0.0001)
    assert candidate_run.total_distribution_keur == pytest.approx(baseline.total_distribution_keur, abs=0.0001)


def test_excel_fixture_remains_r99_source_of_truth_for_shl_mechanics():
    excel = _excel_r99_schedule()

    assert len(excel) == 60
    assert sum(excel) == pytest.approx(EXCEL_R99_TOTAL_KEUR, abs=0.01)
    assert excel[0] == pytest.approx(953.814443278492, abs=0.0001)
    assert excel[35] == pytest.approx(5_050.1749166752115, abs=0.0001)


def test_candidate_fields_are_exposed_and_compared_period_by_period():
    result = _run_project(create_default_tuho_wind1())
    excel = _excel_r99_schedule()
    candidates = _candidate_sources(result, len(excel))

    expected_names = {
        "c1d_r99_audit",
        "c1d_r102_audit",
        "c1d_fcf_for_shl",
        "r98_distribution_account",
        "r84_fcf_junior",
        "cf_after_tax",
        "cf_after_tax_minus_senior_ds",
        "cf_after_reserves",
    }
    assert set(candidates) == expected_names
    for values in candidates.values():
        assert len(values) == len(excel)


def test_cf_after_tax_minus_senior_ds_remains_rejected_benchmark():
    result = _run_project(create_default_tuho_wind1())
    excel = _excel_r99_schedule()
    proxy = _candidate_sources(result, len(excel))["cf_after_tax_minus_senior_ds"]
    stats = _stats(proxy, excel)

    assert stats["total_delta"] == pytest.approx(17_667.16029956119, abs=0.01)
    assert stats["material_periods_within_tolerance"] < stats["material_periods"]
    assert _is_accepted(proxy, excel) is False


def test_no_existing_runtime_candidate_is_accepted_against_excel_r99():
    excel = _excel_r99_schedule()
    default_result = _run_project(create_default_tuho_wind1())
    explicit_senior_project = _with_full_explicit_senior_fixture(
        create_default_tuho_wind1(),
        _load_excel_senior_fixture("tuho"),
    )
    explicit_senior_result = _run_project(explicit_senior_project)

    default_candidates = _candidate_sources(default_result, len(excel))
    explicit_senior_candidates = _candidate_sources(explicit_senior_result, len(excel))
    all_candidates = {
        **{f"default:{name}": values for name, values in default_candidates.items()},
        **{f"explicit_senior:{name}": values for name, values in explicit_senior_candidates.items()},
    }

    accepted = [name for name, values in all_candidates.items() if _is_accepted(values, excel)]
    best_name, best_values = min(
        all_candidates.items(),
        key=lambda item: _stats(item[1], excel)["mae"],
    )
    best_stats = _stats(best_values, excel)

    assert accepted == []
    assert best_name == "explicit_senior:c1d_r99_audit"
    assert best_stats["total_delta"] == pytest.approx(17_394.68049776691, abs=0.01)
    assert best_stats["mae"] == pytest.approx(360.1101983329339, abs=0.01)
    assert best_stats["material_periods_within_tolerance"] == 41
    assert best_stats["material_periods"] == 60


def test_shl_fcf_waterfall_factories_remain_disabled_and_fail_closed_without_fixture_source():
    tuho = create_default_tuho_wind1()
    oborovo = create_default_oborovo()

    assert tuho.info.use_shl_fcf_waterfall_engine is False
    assert oborovo.info.use_shl_fcf_waterfall_engine is False
    assert tuho.financing.shl_repayment_method != SHLRepaymentMethod.FCF_WATERFALL.value
    assert oborovo.financing.shl_repayment_method != SHLRepaymentMethod.FCF_WATERFALL.value

    tuho_fcf_without_source = replace(
        tuho,
        info=replace(tuho.info, use_shl_fcf_waterfall_engine=True),
        financing=replace(tuho.financing, shl_repayment_method=SHLRepaymentMethod.FCF_WATERFALL.value),
    )
    with pytest.raises(ValueError, match="cash_schedule"):
        _run_project(tuho_fcf_without_source)
