from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from app.project_factories import create_default_tuho_wind1
from app.services.production_financial_authority import run_clean_production


GATE_FIXTURE = Path(
    "tests/fixtures/interest_limitation/tuho_capitalisation_gate_fixture.json"
)


@pytest.fixture(scope="module")
def clean_run():
    return run_clean_production(create_default_tuho_wind1())


def test_clean_runtime_uses_typed_construction_and_derived_vat_authority(clean_run):
    financing = clean_run.g2c_result.financing_result
    construction = financing.construction_financing

    assert construction is not None
    assert len(construction.period_start_dates) == 18
    assert financing.project_uses.hard_project_capex_keur == pytest.approx(
        70_691.53944444444
    )
    assert construction.vat_commitment_mode == "DERIVED_PEAK_REQUIREMENT"
    assert construction.vat_effective_commitment_keur == pytest.approx(
        3_361.5090166666664
    )
    assert construction.vat_idc_keur == pytest.approx(122.31400101334873)
    assert construction.vat_commitment_fee_keur == pytest.approx(26.465752928759645)
    assert construction.sources_uses_residual_keur == pytest.approx(0.0, abs=1e-8)


def test_construction_shl_interest_enters_tax_once_without_capex_double_count(clean_run):
    financing = clean_run.g2c_result.financing_result
    model = financing.project_model_result
    construction = financing.construction_financing
    tax = model.tax_and_cfads

    assert construction is not None
    assert tax is not None
    construction_pik = construction.shl_construction_pik_keur
    assert sum(construction.shl_pik_accrual_keur) == pytest.approx(construction_pik)
    assert tax.shl_gross_interest_audit_keur[0] == pytest.approx(
        construction_pik, abs=2e-6
    )
    assert financing.opening_operating_shl_balance_keur == pytest.approx(
        financing.derived_shl_cash_principal_keur + construction_pik,
        abs=2e-6,
    )
    assert financing.project_uses.hard_project_capex_keur == pytest.approx(
        70_691.53944444444
    )


def test_dynamic_gate_and_deductible_interest_identity_close(clean_run):
    tax = clean_run.g2c_result.financing_result.project_model_result.tax_and_cfads
    assert tax is not None

    active = [
        index for index, enabled in enumerate(tax.capitalisation_gate_audit) if enabled
    ]
    assert active[0] == 8
    assert tax.capitalisation_ratio_audit[8] == pytest.approx(0.803290783150396)
    for gross, deductible, disallowed in zip(
        tax.shl_gross_interest_audit_keur,
        tax.shl_deductible_interest_audit_keur,
        tax.shl_disallowed_interest_audit_keur,
        strict=True,
    ):
        assert deductible + disallowed == pytest.approx(gross, abs=1e-9)


def test_clean_senior_and_shl_close_without_frozen_schedule_or_top_up(clean_run):
    financing = clean_run.g2c_result.financing_result
    model = financing.project_model_result
    shl = model.shareholder_loan

    assert shl is not None
    assert financing.binding_senior_constraint == "DSCR"
    assert financing.final_senior_commitment_keur == pytest.approx(
        43_789.92111682598
    )
    assert financing.derived_shl_cash_principal_keur == pytest.approx(
        28_741.108714531947
    )
    assert financing.opening_operating_shl_balance_keur == pytest.approx(
        32_261.52826981019
    )
    principal_periods = [
        index for index, amount in enumerate(shl.shl_principal_keur) if amount > 1e-8
    ]
    assert principal_periods[0] == 25
    assert principal_periods[-1] == 36
    assert shl.shl_closing_keur[-1] == pytest.approx(0.0, abs=1e-8)
    assert shl.diagnostics.converged is True
    assert shl.diagnostics.max_final_shl_interest_handshake_delta_keur < 1e-8
    assert shl.diagnostics.max_final_shl_closing_handshake_delta_keur < 1e-8


def test_project_identity_is_non_financial_and_target_dscr_is_causal(clean_run):
    project = create_default_tuho_wind1()
    renamed = replace(
        project,
        info=replace(project.info, name="Renamed clean wind", code="RENAMED"),
    )
    renamed_run = run_clean_production(renamed)
    baseline_senior = clean_run.g2c_result.financing_result.final_senior_commitment_keur
    assert renamed_run.g2c_result.financing_result.final_senior_commitment_keur == (
        pytest.approx(baseline_senior, abs=1e-8)
    )

    sculpting = project.financing.senior_sculpting_config
    assert sculpting is not None
    lower_target = replace(
        project,
        financing=replace(
            project.financing,
            senior_sculpting_config=replace(
                sculpting,
                target_dscr_schedule=tuple(
                    target - 0.02 for target in sculpting.target_dscr_schedule
                ),
            ),
        ),
    )
    lower_target_run = run_clean_production(lower_target)
    assert lower_target_run.g2c_result.financing_result.final_senior_commitment_keur > (
        baseline_senior
    )


def test_source_gate_fixture_is_validation_only_not_runtime_input():
    fixture = json.loads(GATE_FIXTURE.read_text(encoding="utf-8"))
    project_repr = repr(create_default_tuho_wind1())

    first_active = next(
        period["period_index"] for period in fixture["periods"] if period["gate_active"]
    )
    assert first_active == 7
    assert "first_active_period_index" not in project_repr
    assert "source_gate_vector" not in project_repr


# ---------------------------------------------------------------------------
# B3 Correction B — Construction financing / total project uses causal
# reconciliation identity tests (14 tests required by independent review).
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def b3_uses_data(clean_run):
    fr = clean_run.g2c_result.financing_result
    return fr.project_uses, fr.construction_financing


def test_b3_cbc_T1_project_uses_total_equals_cfr_final_total(b3_uses_data):
    """T1: project_uses.total == cfr.final_total_project_uses (no lag)."""
    pu, cfr = b3_uses_data
    assert pu.total_project_uses_keur == pytest.approx(
        cfr.final_total_project_uses_keur, abs=1e-8
    )


def test_b3_cbc_T2_hard_plus_financing_plus_reserve_equals_total(b3_uses_data):
    """T2: hard + explicit_financing + reserve + other_explicit == total (strict identity)."""
    pu, cfr = b3_uses_data
    recomputed = (
        pu.hard_project_capex_keur
        + pu.explicit_financing_cost_uses_keur
        + pu.reserve_account_funding_keur
        + pu.other_explicit_project_uses_keur
    )
    assert recomputed == pytest.approx(pu.total_project_uses_keur, abs=1e-8)


def test_b3_cbc_T3_capitalized_financing_consistent_with_project_uses(b3_uses_data):
    """T3: cfr.total_capitalized_financing ≈ project_uses.explicit_financing (within 1e-6 kEUR)."""
    pu, cfr = b3_uses_data
    assert cfr.total_capitalized_financing_keur == pytest.approx(
        pu.explicit_financing_cost_uses_keur, abs=1e-6
    )


def test_b3_cbc_T4_tuho_has_zero_reserve(b3_uses_data):
    """T4: TUHO clean run carries no reserve — no hidden capacity in reserve."""
    pu, cfr = b3_uses_data
    assert pu.reserve_account_funding_keur == pytest.approx(0.0, abs=1e-9)


def test_b3_cbc_T5_tuho_has_zero_other_explicit_uses(b3_uses_data):
    """T5: No other_explicit_project_uses — uses decomposition is complete."""
    pu, cfr = b3_uses_data
    assert pu.other_explicit_project_uses_keur == pytest.approx(0.0, abs=1e-9)


def test_b3_cbc_T6_idc_accrual_exceeds_capitalized_senior_idc(b3_uses_data):
    """T6: Senior IDC accrual > capitalized senior IDC component — gate disallows part.

    capitalized_senior_idc = total_cap - commit_fee - struct_fee - vat_idc - vat_commit_fee
    """
    pu, cfr = b3_uses_data
    accrual_idc = sum(cfr.senior_idc_accrual_keur)
    cap_senior_idc = (
        cfr.total_capitalized_financing_keur
        - sum(cfr.senior_commitment_fee_accrual_keur)
        - sum(cfr.structuring_fee_keur)
        - cfr.vat_idc_keur
        - cfr.vat_commitment_fee_keur
    )
    assert accrual_idc > cap_senior_idc


def test_b3_cbc_T7_gate_disallowed_idc_magnitude(b3_uses_data):
    """T7: ATAD gate disallows 217.125 kEUR of accrued IDC from capitalization."""
    pu, cfr = b3_uses_data
    accrual_idc = sum(cfr.senior_idc_accrual_keur)
    accrual_fee = sum(cfr.senior_commitment_fee_accrual_keur)
    accrual_struct = sum(cfr.structuring_fee_keur)
    capitalized_senior_idc = (
        cfr.total_capitalized_financing_keur
        - accrual_fee
        - accrual_struct
        - cfr.vat_idc_keur
        - cfr.vat_commitment_fee_keur
    )
    gate_disallowed = accrual_idc - capitalized_senior_idc
    assert gate_disallowed == pytest.approx(217.1250255375926, abs=1e-6)


def test_b3_cbc_T8_all_idc_accruals_non_negative(b3_uses_data):
    """T8: No period may carry negative IDC accrual."""
    pu, cfr = b3_uses_data
    for i, val in enumerate(cfr.senior_idc_accrual_keur):
        assert val >= -1e-10, f"Period {i}: negative IDC accrual {val}"


def test_b3_cbc_T9_outer_loop_converged(b3_uses_data):
    """T9: Outer fixed-point loop converged (residual < 1e-6 kEUR)."""
    pu, cfr = b3_uses_data
    assert cfr.outer_residual_keur == pytest.approx(0.0, abs=1e-6)


def test_b3_cbc_T10_idempotence_residual_tight(b3_uses_data):
    """T10: Final idempotence check residual < 1e-4 kEUR (no outer-loop state lag)."""
    pu, cfr = b3_uses_data
    assert cfr.final_verification_outer_residual_keur == pytest.approx(0.0, abs=1e-4)


def test_b3_cbc_T11_vat_facility_components_in_capitalized_total(b3_uses_data):
    """T11: VAT IDC + VAT commitment fee are included in total_capitalized_financing."""
    pu, cfr = b3_uses_data
    vat_total = cfr.vat_idc_keur + cfr.vat_commitment_fee_keur
    assert vat_total == pytest.approx(122.31400101334872 + 26.465752928759642, abs=1e-9)
    assert cfr.total_capitalized_financing_keur > vat_total


def test_b3_cbc_T12_structuring_fee_allocation_sums_to_capitalized(b3_uses_data):
    """T12: Sum of per-period structuring fees == scalar allocated from CapitalizedFinancingCosts."""
    pu, cfr = b3_uses_data
    struct_sum = sum(cfr.structuring_fee_keur)
    accrual_fee = sum(cfr.senior_commitment_fee_accrual_keur)
    capitalized_senior_idc = (
        cfr.total_capitalized_financing_keur
        - accrual_fee
        - struct_sum
        - cfr.vat_idc_keur
        - cfr.vat_commitment_fee_keur
    )
    assert struct_sum == pytest.approx(471.5143013349264, abs=1e-8)
    assert capitalized_senior_idc == pytest.approx(1552.229213780136, abs=1e-6)


def test_b3_cbc_T13_clean_senior_idc_accrual_exceeds_source(b3_uses_data):
    """T13: Clean Senior IDC accrual (1769.35) > source (1519.56) by ~249.79 kEUR.

    Causal bridge: clean uses typed dynamic interest limitation gate (ATAD/STL)
    and full B2 period-level accrual; source uses a frozen Excel schedule.
    The accrual divergence is the first material source/clean difference.
    """
    pu, cfr = b3_uses_data
    SOURCE_SENIOR_IDC_KEUR = 1_519.563935502677
    clean_accrual = sum(cfr.senior_idc_accrual_keur)
    divergence = clean_accrual - SOURCE_SENIOR_IDC_KEUR
    assert clean_accrual == pytest.approx(1_769.3542393177286, abs=1e-6)
    assert divergence == pytest.approx(249.79030381505163, abs=1e-4)


def test_b3_cbc_T14_construction_financing_produces_no_double_count(b3_uses_data):
    """T14: Hard CAPEX in project_uses equals hard CAPEX period vector sum.

    Confirms no double-count between hard_capex_uses and explicit_financing_cost_uses.
    """
    pu, cfr = b3_uses_data
    hard_from_vector = sum(cfr.hard_capex_uses_keur)
    assert hard_from_vector == pytest.approx(pu.hard_project_capex_keur, abs=1e-8)
    assert pu.hard_project_capex_keur == pytest.approx(70_691.53944444444, abs=1e-8)
    assert pu.explicit_financing_cost_uses_keur != pytest.approx(0.0, abs=1.0)
