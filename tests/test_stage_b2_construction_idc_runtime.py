"""Canonical Stage B2 construction runtime tests."""
from __future__ import annotations

import pytest

from domain.construction.source_parity import oborovo_source_config
from finco_core.construction import convergence_audit, run_stage_b2


def test_run_stage_b2_is_canonical_entrypoint_for_oborovo_financial_outputs():
    result = run_stage_b2(oborovo_source_config())

    assert result.capitalized_financing_costs.senior_idc_keur == pytest.approx(1_086.031998, abs=1e-9)
    assert result.capitalized_financing_costs.senior_commitment_fee_keur == pytest.approx(188.562901, abs=1e-9)
    assert result.capitalized_financing_costs.structuring_fee_keur == pytest.approx(477.302687, abs=1e-9)
    assert result.capitalized_financing_costs.vat_idc_keur == pytest.approx(208.447618, abs=1e-9)
    assert result.capitalized_financing_costs.vat_commitment_fee_keur == pytest.approx(13.621953, abs=1e-9)
    assert result.capitalized_financing_costs.total_keur == pytest.approx(1_973.967157, abs=1e-9)
    assert result.final_gfa_keur == pytest.approx(57_973.052657, abs=1e-9)
    assert result.closing_senior_drawn_keur == pytest.approx(42_852.266726, abs=1e-9)


def test_run_stage_b2_vat_runoff_horizon_is_canonical():
    result = run_stage_b2(oborovo_source_config())

    assert len(result.vat_schedule) == 18
    assert len(result.vat_payable_keur) == 12
    assert result.vat_schedule[12].vat_payable_keur == 0.0
    assert result.vat_schedule[-1].vat_requirement_keur == pytest.approx(0.0, abs=1e-9)


def test_run_stage_b2_reports_converged_vector_residual_audit():
    result = run_stage_b2(oborovo_source_config())

    assert result.iterations == 1
    assert result.final_residual_keur == pytest.approx(0.0, abs=1e-12)
    assert {row.component for row in result.residual_audit} == {"senior_idc", "senior_commitment_fee"}


def test_stage_b2_vector_residual_catches_same_total_different_timing():
    residual, audit = convergence_audit({"senior_idc": (150.0, 150.0)}, {"senior_idc": (100.0, 200.0)})

    assert residual == pytest.approx(100.0)
    assert audit[0].max_period_delta_keur == pytest.approx(50.0)
