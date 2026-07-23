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
    assert {row.component for row in result.residual_audit} == {"senior_idc", "senior_commitment_fee"}


def test_stage_b2_vector_residual_catches_same_total_different_timing():
    residual, audit = convergence_audit({"senior_idc": (150.0, 150.0)}, {"senior_idc": (100.0, 200.0)})

    assert residual == pytest.approx(100.0)
    assert audit[0].max_period_delta_keur == pytest.approx(50.0)


def test_stage_b2_initial_guess_independence_for_synthetic_case():
    base = oborovo_source_config()
    seeded = base.__class__(
        **{
            **base.__dict__,
            "initial_senior_idc_vector_keur": (10.0,) * 12,
            "initial_senior_commitment_fee_vector_keur": (3.0,) * 12,
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
