"""Oborovo Stage B2 source-parity guardrails."""
from __future__ import annotations

import ast
import pathlib

import pytest

from domain.construction.source_parity import (
    OBOROVO_INTEREST_FRACTIONS,
    OBOROVO_SOURCE_CUMULATIVE_SENIOR_KEUR,
    OBOROVO_SOURCE_VAT_REQUIREMENT_KEUR,
    SOURCE_TOTAL_USES_VALIDATION_KEUR,
    oborovo_capex_schedule,
    oborovo_source_config,
    oborovo_timeline,
)
from finco_core.construction import (
    FinancingCostFundingPolicy,
    allocate_structuring_fee,
    convergence_audit,
    run_stage_b2,
    total_hard_capex,
    vat_bearing_base,
    vat_monthly_uses,
)


def _result():
    return run_stage_b2(oborovo_source_config())


def test_oborovo_parity_tests_invoke_canonical_run_stage_b2_for_financial_outputs():
    source = pathlib.Path(__file__).read_text()
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    assert any(getattr(call.func, "id", "") == "run_stage_b2" for call in calls)


def test_source_parity_does_not_import_or_define_stage_b2_financial_engine_logic():
    source_path = pathlib.Path("domain/construction/source_parity.py")
    source = source_path.read_text()
    tree = ast.parse(source)
    function_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

    assert "run_stage_b2" not in function_names
    assert "compute_vat_schedule" not in function_names
    assert "convergence_audit" not in function_names
    assert "senior_idc" not in source.lower().replace("senior_idc_source_keur", "")


def test_oborovo_p1_is_two_day_stub_and_receives_m1_capex_from_canonical_result():
    result = _result()
    timeline = result.config.timeline

    assert timeline[0].start_date.isoformat() == "2029-06-29"
    assert timeline[0].end_date.isoformat() == "2029-06-30"
    assert timeline[0].interest_fraction == pytest.approx(2 / 360, abs=1e-15)
    assert timeline[0].active_construction is True
    assert timeline[0].capex_payment_eligible is True
    assert result.monthly_hard_capex_keur[0] == pytest.approx(15_990.943833333335, abs=1e-9)
    assert result.monthly_hard_capex_keur[0] > 0.0


def test_oborovo_has_twelve_active_construction_periods_and_period_13_inactive():
    timeline = _result().config.timeline

    assert sum(p.active_construction for p in timeline) == 12
    assert timeline[12].active_construction is False
    assert timeline[12].capex_payment_eligible is False
    assert timeline[12].senior_idc_active is False


def test_oborovo_interest_fraction_sequence_matches_source_headers():
    assert OBOROVO_INTEREST_FRACTIONS == pytest.approx(
        (2 / 360, 31 / 360, 31 / 360, 30 / 360, 31 / 360, 30 / 360,
         31 / 360, 31 / 360, 28 / 360, 31 / 360, 30 / 360, 31 / 360),
        abs=1e-15,
    )


def test_oborovo_first_period_funding_identity_matches_source_senior_draw():
    result = _result()
    source_total_uses_p1 = SOURCE_TOTAL_USES_VALIDATION_KEUR[0]
    python_senior_draw = result.senior_period_draw_keur[0]
    identity_senior_draw = source_total_uses_p1 - 500.0 - 14_620.773895

    assert python_senior_draw == pytest.approx(identity_senior_draw, abs=0.001)
    assert python_senior_draw == pytest.approx(OBOROVO_SOURCE_CUMULATIVE_SENIOR_KEUR[0], abs=0.001)


def test_oborovo_per_item_capex_total_and_vat_base_parity_from_canonical_helpers():
    config = oborovo_source_config()

    assert total_hard_capex(config.capex_schedule) == pytest.approx(55_999.0855, abs=1e-9)
    assert vat_bearing_base(config.capex_schedule) == pytest.approx(45_086.3855, abs=1e-9)
    assert sum(vat_monthly_uses(config.capex_schedule)) == pytest.approx(7_664.685535, abs=1e-9)
    c01 = next(item for item in config.capex_schedule.items if item.code == "C.01")
    assert c01.vat_rate == 0.0
    assert c01.vat_classification == "AGGREGATE_RECONCILIATION_INFERENCE"


def test_oborovo_equal_and_m1_payment_schedules_are_explicit():
    schedule = oborovo_capex_schedule()
    by_name = {item.name: item for item in schedule.items}

    for name in (
        "Production Units",
        "EPC Contract",
        "EPC other costs",
        "Grid connection",
        "Investments to prepare operation phase",
        "Audit & Accounting & Legal Fees",
    ):
        assert by_name[name].payment_weights == pytest.approx((1 / 12,) * 12, abs=1e-15)

    for name in (
        "Insurances",
        "Project finance costs due at closing",
        "Construction Management",
        "Contingencies",
        "Project Rights",
    ):
        assert by_name[name].payment_weights == pytest.approx((1.0,) + (0.0,) * 11, abs=1e-15)


def test_vat_schedule_continues_after_capex_and_reaches_zero_in_canonical_runtime():
    result = _result()
    vat_schedule = result.vat_schedule

    assert len(vat_schedule) == 18
    assert vat_schedule[12].vat_payable_keur == 0.0
    assert vat_schedule[-1].vat_requirement_keur == pytest.approx(0.0, abs=1e-9)
    assert len(OBOROVO_SOURCE_VAT_REQUIREMENT_KEUR) == 18


def test_fixed_point_convergence_uses_period_vectors_not_totals():
    residual, audit = convergence_audit(
        {"senior_idc": (150.0, 150.0), "senior_commitment_fee": (10.0, 5.0)},
        {"senior_idc": (100.0, 200.0), "senior_commitment_fee": (5.0, 10.0)},
    )

    assert residual == pytest.approx(110.0)
    senior_idc = next(row for row in audit if row.component == "senior_idc")
    assert senior_idc.total_value_keur == pytest.approx(300.0)
    assert senior_idc.vector_residual_keur == pytest.approx(100.0)
    assert senior_idc.max_period_delta_keur == pytest.approx(50.0)
    assert senior_idc.max_period_index == 1


def test_structuring_fee_funding_timing_is_configurable_in_canonical_runtime():
    policy = FinancingCostFundingPolicy(structuring_fee_payment_schedule=(0.25, 0.75) + (0.0,) * 10)

    assert allocate_structuring_fee(policy, 100.0) == pytest.approx((25.0, 75.0) + (0.0,) * 10)


def test_exact_source_parity_outputs_from_single_canonical_run():
    result = _result()
    financing = result.capitalized_financing_costs

    assert financing.senior_idc_keur == pytest.approx(1_086.031998, abs=1e-9)
    assert financing.senior_commitment_fee_keur == pytest.approx(188.562901, abs=1e-9)
    assert financing.structuring_fee_keur == pytest.approx(477.302687, abs=1e-9)
    assert financing.vat_idc_keur == pytest.approx(208.447618, abs=1e-9)
    assert financing.vat_commitment_fee_keur == pytest.approx(13.621953, abs=1e-9)
    assert financing.total_keur == pytest.approx(1_973.967157, abs=1e-9)
    assert result.final_gfa_keur == pytest.approx(57_973.052657, abs=1e-9)
    assert result.closing_senior_drawn_keur == pytest.approx(42_852.266726, abs=1e-9)
    assert result.closing_senior_undrawn_keur == pytest.approx(0.0, abs=1e-9)


def test_capitalized_financing_useful_life_handoff_metadata():
    lives = _result().capitalized_financing_costs.useful_lives_years()

    assert lives["senior_idc"] == 12
    assert lives["senior_commitment_fee"] == 12
    assert lives["structuring_fee"] == 12
    assert lives["vat_idc"] == 20
    assert lives["vat_commitment_fee"] == 20
