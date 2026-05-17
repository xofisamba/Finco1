"""Phase 7M distribution-account bridge for TUHO R99/R102.

The workbook inspection showed that TUHO operating R84, R98, R99, and R102
are equal, and R100 carry-forward is zero. The remaining R99/R102 delta is
therefore upstream of distribution-account carry-forward.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.project_factories import create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from tests.test_senior_dscr_sculpting_full_schedule_fixtures import (
    _load_excel_senior_fixture,
    _with_full_explicit_senior_fixture,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "excel_tuho_full_model_extract.json"
EXCEL_R99_TOTAL_KEUR = 234_745.44009403558

EXCEL_COMPONENT_TOTALS = {
    "r20_revenue": 423_787.5,
    "r38_opex": -84_674.8,
    "r66_reserve_interest": 55.0,
    "r67_corp_tax": -38_240.9,
    "r69_fcf_banks": 300_926.8,
    "r70_senior_ds": -66_181.3,
    "r82_dsra": 0.0,
    "r84_fcf_junior": 234_745.4,
    "r98_distribution_account": 234_745.4,
    "r99_fcf_distribution": 234_745.4,
    "r100_carryforward": 0.0,
    "r102_fcf_shl": 234_745.4,
}


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


def _explicit_senior_result():
    project = _with_full_explicit_senior_fixture(
        create_default_tuho_wind1(),
        _load_excel_senior_fixture("tuho"),
    )
    return _run_project(project)


def test_r99_distribution_bridge_does_not_change_default_runtime_outputs():
    baseline = _run_project(create_default_tuho_wind1())
    diagnostic = _run_project(create_default_tuho_wind1())

    assert diagnostic.total_revenue_keur == pytest.approx(baseline.total_revenue_keur, abs=0.0001)
    assert diagnostic.total_opex_keur == pytest.approx(baseline.total_opex_keur, abs=0.0001)
    assert diagnostic.total_senior_ds_keur == pytest.approx(baseline.total_senior_ds_keur, abs=0.0001)
    assert diagnostic.total_shl_service_keur == pytest.approx(baseline.total_shl_service_keur, abs=0.0001)
    assert diagnostic.total_distribution_keur == pytest.approx(baseline.total_distribution_keur, abs=0.0001)


def test_excel_distribution_account_rows_collapse_to_r84_without_carryforward():
    assert EXCEL_COMPONENT_TOTALS["r84_fcf_junior"] == pytest.approx(EXCEL_R99_TOTAL_KEUR, abs=0.1)
    assert EXCEL_COMPONENT_TOTALS["r98_distribution_account"] == pytest.approx(EXCEL_R99_TOTAL_KEUR, abs=0.1)
    assert EXCEL_COMPONENT_TOTALS["r99_fcf_distribution"] == pytest.approx(EXCEL_R99_TOTAL_KEUR, abs=0.1)
    assert EXCEL_COMPONENT_TOTALS["r102_fcf_shl"] == pytest.approx(EXCEL_R99_TOTAL_KEUR, abs=0.1)
    assert EXCEL_COMPONENT_TOTALS["r100_carryforward"] == pytest.approx(0.0)


def test_current_best_candidate_still_fails_acceptance():
    result = _explicit_senior_result()
    excel = _excel_r99_schedule()
    candidate = tuple(p.r99_fcf_for_distribution_keur for p in result.periods[: len(excel)])
    total_delta = sum(candidate) - sum(excel)
    material_within = sum(
        abs(value - expected) <= max(100.0, abs(expected) * 0.02)
        for value, expected in zip(candidate, excel)
    )

    assert sum(candidate) == pytest.approx(252_140.1205918025, abs=0.01)
    assert total_delta == pytest.approx(17_394.68049776691, abs=0.01)
    assert material_within == 41
    assert material_within < len(excel)


def test_component_deltas_show_gap_is_upstream_of_distribution_account():
    result = _explicit_senior_result()
    periods = result.periods[:60]
    python_totals = {
        "r20_revenue": sum(p.revenue_keur for p in periods),
        "r38_opex": sum(-p.opex_keur for p in periods),
        "r67_corp_tax": sum(-p.corporate_tax_cash_keur for p in periods),
        "r69_fcf_banks": sum(p.r69_fcf_banks_keur for p in periods),
        "r70_senior_ds": sum(-p.senior_ds_keur for p in periods),
        "r82_dsra": sum(-p.dsra_contribution_keur for p in periods),
        "r84_fcf_junior": sum(p.r84_fcf_junior_keur for p in periods),
    }

    assert python_totals["r20_revenue"] - EXCEL_COMPONENT_TOTALS["r20_revenue"] == pytest.approx(0.0, abs=0.1)
    assert python_totals["r70_senior_ds"] - EXCEL_COMPONENT_TOTALS["r70_senior_ds"] == pytest.approx(0.0, abs=0.1)
    assert python_totals["r82_dsra"] - EXCEL_COMPONENT_TOTALS["r82_dsra"] == pytest.approx(0.0, abs=0.1)

    opex_delta = python_totals["r38_opex"] - EXCEL_COMPONENT_TOTALS["r38_opex"]
    tax_delta = python_totals["r67_corp_tax"] - EXCEL_COMPONENT_TOTALS["r67_corp_tax"]
    r69_delta = python_totals["r69_fcf_banks"] - EXCEL_COMPONENT_TOTALS["r69_fcf_banks"]
    r84_delta = python_totals["r84_fcf_junior"] - EXCEL_COMPONENT_TOTALS["r84_fcf_junior"]

    assert opex_delta == pytest.approx(-733.5, abs=0.1)
    assert tax_delta == pytest.approx(18_183.2, abs=0.1)
    assert r69_delta == pytest.approx(17_394.7, abs=0.1)
    assert r84_delta == pytest.approx(r69_delta, abs=0.1)
    assert opex_delta + tax_delta == pytest.approx(r84_delta, abs=100.0)


def test_selected_period_bridge_identifies_h2_cash_tax_timing_pattern():
    result = _explicit_senior_result()
    excel = _excel_r99_schedule()
    periods = result.periods[: len(excel)]

    selected = {
        0: 0.0,
        24: 31.3,
        25: -713.3,
        28: -4.0,
        35: 640.6,
        37: 769.2,
        57: 1_587.2,
        59: 1_576.1,
    }
    for op_idx, expected_delta in selected.items():
        delta = periods[op_idx].r99_fcf_for_distribution_keur - excel[op_idx]
        assert delta == pytest.approx(expected_delta, abs=0.2)


def test_no_runtime_r99_source_accepted_and_no_shl_factory_opt_in():
    tuho = create_default_tuho_wind1()

    assert tuho.info.use_shl_fcf_waterfall_engine is False
    assert tuho.financing.use_tuho_r99_input_engine is False
    assert tuho.financing.shl_fcf_waterfall_cash_schedule_keur == ()
