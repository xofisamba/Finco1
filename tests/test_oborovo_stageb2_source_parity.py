"""Oborovo Stage B2 source-parity guardrails."""
from __future__ import annotations

import pytest

from domain.construction.source_parity import (
    FinancingCostFundingPolicy,
    OBOROVO_INTEREST_FRACTIONS,
    OBOROVO_SOURCE_CUMULATIVE_SENIOR_KEUR,
    OBOROVO_SOURCE_VAT_REQUIREMENT_KEUR,
    SOURCE_TOTAL_USES_VALIDATION_KEUR,
    convergence_audit,
    compute_vat_schedule,
    oborovo_capex_schedule,
    oborovo_timeline,
)


def test_oborovo_p1_is_two_day_stub_and_receives_m1_capex():
    timeline = oborovo_timeline()
    hard_capex = oborovo_capex_schedule().monthly_uses()

    assert timeline[0].interest_fraction == pytest.approx(2 / 360, abs=1e-15)
    assert timeline[0].active_construction is True
    assert timeline[0].capex_payment_eligible is True
    assert hard_capex[0] == pytest.approx(15_990.943833333335, abs=1e-9)
    assert hard_capex[0] > hard_capex[1]


def test_oborovo_has_twelve_active_construction_periods_and_period_13_inactive():
    timeline = oborovo_timeline()

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
    source_total_uses_p1 = SOURCE_TOTAL_USES_VALIDATION_KEUR[0]
    senior_draw = source_total_uses_p1 - 500.0 - 14_620.773895

    assert senior_draw == pytest.approx(OBOROVO_SOURCE_CUMULATIVE_SENIOR_KEUR[0], abs=0.001)


def test_oborovo_per_item_capex_total_and_vat_base_parity():
    schedule = oborovo_capex_schedule()

    assert schedule.total_hard_capex_keur == pytest.approx(55_999.0855, abs=1e-9)
    assert schedule.vat_bearing_base_keur == pytest.approx(45_086.3855, abs=1e-9)
    assert sum(schedule.vat_monthly_uses()) == pytest.approx(7_664.685535, abs=1e-9)
    c01 = next(item for item in schedule.items if item.code == "C.01")
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


def test_vat_schedule_continues_after_capex_and_reaches_zero():
    vat_payable = oborovo_capex_schedule().vat_monthly_uses()
    vat_schedule = compute_vat_schedule(vat_payable, reimbursement_lag_periods=6)

    assert len(vat_schedule) == 18
    assert vat_schedule[12]["vat_payable_keur"] == 0.0
    assert vat_schedule[-1]["vat_requirement_keur"] == pytest.approx(0.0, abs=1e-9)
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


def test_structuring_fee_funding_timing_is_configurable():
    policy = FinancingCostFundingPolicy(structuring_fee_payment_schedule=(0.25, 0.75) + (0.0,) * 10)

    assert policy.allocate(100.0) == pytest.approx((25.0, 75.0) + (0.0,) * 10)
