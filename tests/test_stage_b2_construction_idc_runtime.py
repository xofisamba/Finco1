"""Canonical Stage B2 construction runtime tests."""
from __future__ import annotations

import pytest

from domain.construction.source_parity import oborovo_source_config
import finco_core.construction as construction_api
from finco_core.construction import convergence_audit, run_stage_b2
from finco_core.construction import stage_b2


def test_public_run_stage_b2_is_stage_b2_single_callable():
    assert construction_api.run_stage_b2 is stage_b2.run_stage_b2


def test_run_stage_b2_is_canonical_entrypoint_for_oborovo_financial_outputs():
    result = run_stage_b2(oborovo_source_config())

    assert result.capitalized_financing_costs.senior_idc_keur > 0.0
    assert result.capitalized_financing_costs.senior_commitment_fee_keur > 0.0
    assert result.capitalized_financing_costs.structuring_fee_keur == pytest.approx(477.302687, abs=1e-9)
    assert result.final_gfa_keur > 55_999.0855
    assert result.closing_senior_drawn_keur > 0.0


def test_run_stage_b2_vat_runoff_horizon_is_canonical():
    result = run_stage_b2(oborovo_source_config())

    assert len(result.vat_schedule) == 18
    assert len(result.vat_payable_keur) == 12
    assert result.vat_schedule[12].vat_payable_keur == 0.0
    assert result.vat_schedule[-1].vat_requirement_keur == pytest.approx(0.0, abs=1e-9)


def test_run_stage_b2_reports_converged_vector_residual_audit():
    result = run_stage_b2(oborovo_source_config())

    assert result.iterations > 1
    assert result.final_residual_keur == pytest.approx(0.0, abs=1e-8)
    assert {row.component for row in result.residual_audit} == {"senior_idc", "senior_commitment_fee", "vat_financing_costs"}


def test_stage_b2_vector_residual_catches_same_total_different_timing():
    residual, audit = convergence_audit({"senior_idc": (150.0, 150.0)}, {"senior_idc": (100.0, 200.0)})

    assert residual == pytest.approx(100.0)
    assert audit[0].max_period_delta_keur == pytest.approx(50.0)


def test_stage_b2_initial_guess_independence_for_synthetic_case():
    base = oborovo_source_config()
    seeded = base.__class__(
        **{
            **base.__dict__,
            "initial_senior_idc_funded_uses_keur": (10.0,) * 12,
            "initial_senior_commitment_fee_funded_uses_keur": (3.0,) * 12,
            "initial_vat_financing_funded_uses_keur": (2.0,) * 12,
        }
    )

    a = run_stage_b2(base)
    b = run_stage_b2(seeded)

    assert a.capitalized_financing_costs.senior_idc_keur == pytest.approx(b.capitalized_financing_costs.senior_idc_keur, abs=1e-7)
    assert a.capitalized_financing_costs.senior_commitment_fee_keur == pytest.approx(b.capitalized_financing_costs.senior_commitment_fee_keur, abs=1e-7)
    assert a.closing_senior_drawn_keur == pytest.approx(b.closing_senior_drawn_keur, abs=1e-7)
    assert a.final_gfa_keur == pytest.approx(b.final_gfa_keur, abs=1e-7)


def test_capitalized_financing_adapter_populates_real_capex_structure_fields():
    from finco_core.construction import apply_capitalized_financing_costs
    from finco_core.inputs import CapexItem, CapexStructure

    zero = CapexItem("zero", 0.0)
    hard = CapexItem("hard", 100.0)
    capex = CapexStructure(
        epc_contract=hard,
        production_units=zero,
        epc_other=zero,
        grid_connection=zero,
        ops_prep=zero,
        insurances=zero,
        lease_tax=zero,
        construction_mgmt_a=zero,
        commissioning=zero,
        audit_legal=zero,
        construction_mgmt_b=zero,
        contingencies=zero,
        taxes=zero,
        project_acquisition=zero,
        project_rights=zero,
    )
    result = run_stage_b2(oborovo_source_config())
    updated = apply_capitalized_financing_costs(capex, result.capitalized_financing_costs)

    assert updated.idc_keur == pytest.approx(result.capitalized_financing_costs.senior_idc_keur)
    assert updated.commitment_fees_keur == pytest.approx(result.capitalized_financing_costs.senior_commitment_fee_keur)
    assert updated.bank_fees_keur == pytest.approx(result.capitalized_financing_costs.structuring_fee_keur)
    assert updated.vat_costs_keur == pytest.approx(
        result.capitalized_financing_costs.vat_idc_keur
        + result.capitalized_financing_costs.vat_commitment_fee_keur
    )
    names = {item.name: item for item in updated.book_depreciable_capex_items()}
    assert names["IDC (Interest During Construction)"].useful_life_override == 12
    assert names["Commitment Fees"].useful_life_override == 12
    assert names["Bank Fees"].useful_life_override == 12
    assert names["VAT Costs"].useful_life_override == 20


def _synthetic_config(**overrides):
    cfg = oborovo_source_config()
    return cfg.__class__(
        **{
            **cfg.__dict__,
            "capex_schedule": stage_b2.CapexScheduleSet((
                stage_b2.CapexPaymentItem("A", "Asset", 1_200.0, (1 / 12,) * 12, 0.0),
            )),
            "funding_policy": stage_b2.FinancingCostFundingPolicy((1.0,) + (0.0,) * 11),
            "source_total_uses_validation_keur": (),
            "equity_available_keur": 0.0,
            "shl_available_keur": 0.0,
            "senior_commitment_keur": 2_000.0,
            "senior_interest_rate": 0.06,
            "senior_commitment_fee_rate": 0.012,
            "senior_interest_rate_schedule": (),
            "base_rate": 0.0,
            "hedge_coverage": 0.0,
            "swap_margin": 0.0,
            "forward_swap_margin": 0.0,
            "cva": 0.0,
            "external_curve_buffer": 0.0,
            "euribor_1m_fixings": (),
            "senior_idc_balance_basis": "OPENING_DRAWN",
            "senior_commitment_fee_balance_basis": "OPENING_UNDRAWN",
            "senior_idc_capitalization_timing": "SAME_PERIOD",
            "senior_commitment_fee_capitalization_timing": "SAME_PERIOD",
            "structuring_fee_rate": 0.0,
            "structuring_fee_basis_keur": 0.0,
            "vat_facility_interest_rate": 0.0,
            "vat_facility_commitment_fee_rate": 0.0,
            "vat_facility_commitment_keur": 0.0,
            "vat_financing_cost_spending_profile": (),
            **overrides,
        }
    )


def test_opening_basis_and_same_period_capitalization_are_runtime_policies():
    result = run_stage_b2(_synthetic_config(max_iterations=200))

    assert result.capitalized_financing_costs.senior_idc_keur > 0.0
    assert result.capitalized_financing_costs.senior_commitment_fee_keur > 0.0
    # First period IDC uses zero opening drawn balance and is therefore zero.
    assert result.total_permanent_uses_keur[0] == pytest.approx(100.0 + 2_000.0 * 0.012 * (2 / 360), abs=1e-9)


def test_period_rate_schedule_can_be_derived_from_hedge_and_euribor_primitives():
    cfg = _synthetic_config(
        senior_interest_rate=0.0265,
        base_rate=0.03,
        hedge_coverage=0.80,
        swap_margin=0.002,
        external_curve_buffer=0.20,
        euribor_1m_fixings=(0.02996,) * 12,
    )
    result = run_stage_b2(cfg)
    first_period_fee = 2_000.0 * 0.012 * (2 / 360)
    second_opening = 100.0 + first_period_fee
    expected_rate = 0.03 * 0.80 + 0.002 + 0.02996 * 0.24 + 0.0265
    expected_p2_idc = second_opening * expected_rate * (31 / 360)

    assert result.total_permanent_uses_keur[1] == pytest.approx(100.0 + expected_p2_idc + (2_000.0 - second_opening) * 0.012 * (31 / 360), abs=1e-6)
