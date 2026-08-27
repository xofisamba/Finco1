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
