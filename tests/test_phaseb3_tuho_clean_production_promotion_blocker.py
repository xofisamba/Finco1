from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.project_factories import (
    create_default_tuho_wind1,
    create_default_tuho_wind1_legacy_calibration,
)
from app.services.production_financial_authority import (
    ProductionAuthorityClassification,
    classify_production_authority,
    run_clean_production,
)


FIXTURE = Path("tests/fixtures/interest_limitation/tuho_interest_limitation_fixture.json")
REPORT = Path("docs/phaseb3_tuho_clean_production_promotion.md")


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_tuho_clean_and_legacy_authorities_are_explicitly_separated():
    project = create_default_tuho_wind1()
    legacy = create_default_tuho_wind1_legacy_calibration()
    decision = classify_production_authority(project)

    assert decision.classification is ProductionAuthorityClassification.CLEAN_PRODUCTION_READY
    assert decision.runtime_authority == "clean_g2c"
    assert project.tax.clean_cash_tax_timing_enabled is True
    assert project.tax.prior_tax_loss_keur == 0.0
    assert project.financing.sponsor_funding_mode is not None
    assert project.financing.gearing_basis_mode is not None
    assert project.financing.use_frozen_excel_senior_debt_schedule is False
    assert legacy.tax.prior_tax_loss_keur == pytest.approx(25_000.0)
    assert legacy.financing.use_frozen_excel_senior_debt_schedule is True


def test_tuho_production_runs_once_through_clean_g2c():
    result = run_clean_production(create_default_tuho_wind1())

    assert result.authority_metadata["calculation_count"] == 1
    assert result.authority_metadata["runtime_authority"] == "clean_g2c"
    assert result.g2c_result.financing_result.final_senior_commitment_keur > 0.0


def test_source_fixture_proves_one_combined_limitation_helper_only():
    fixture = _fixture()

    assert fixture["source_workbook"] == "20260330_TUHO_BP.xlsm"
    assert fixture["period_count"] == 60
    assert fixture["missing_periods"] == []
    assert fixture["ambiguous_periods"] == []
    assert fixture["cumulative_r54_helper"] == pytest.approx(9242.742070978198)

    for period in fixture["periods"]:
        formulas = period["formulas"]
        column = period["column"]
        assert formulas["r54"] == (
            f"=MIN(MAX({column}57,{column}58)+{column}59,{column}27)"
        )
        assert formulas["thin_cap_gate_r45"] == (
            f"=IF({column}44<$B$44,FALSE,TRUE)"
        )


def test_source_fixture_does_not_claim_separate_atad_or_interest_carryforward():
    fixture = _fixture()

    forbidden_claims = {
        "thin_cap_deductible_keur",
        "atad_deductible_keur",
        "interest_carryforward_created_keur",
        "interest_carryforward_used_keur",
    }
    assert forbidden_claims.isdisjoint(fixture)
    assert all(forbidden_claims.isdisjoint(period) for period in fixture["periods"])


def test_legacy_25000_and_source_3568_are_not_collapsed_into_one_authority():
    project = create_default_tuho_wind1()
    legacy = create_default_tuho_wind1_legacy_calibration()

    assert project.tax.prior_tax_loss_keur == 0.0
    assert project.tax.opening_tax_loss_vintages == ()
    assert legacy.tax.prior_tax_loss_keur == pytest.approx(25000.0)

    report = REPORT.read_text(encoding="utf-8")
    assert "3,568.6878026481627" in report
    assert "LEGACY_CALIBRATION" in report
    assert "CLEAN_RUNTIME_RESULT" in report


def test_b3_report_records_source_and_clean_promotion_authority():
    report = REPORT.read_text(encoding="utf-8")

    required = (
        "041382760ecb6190062c887a04529efdf3fca3dda779f4db5e9404902bf09336",
        "780779eba4278ccc2b8546a9411ccee24917d388f411ba60c88aa342cb5c727a",
        "P&L!R54 = MIN(MAX(R57,R58)+R59,R27)",
        "NO_RESTRICTED_INTEREST_CARRYFORWARD_IN_SOURCE_MODEL",
        "PHASE_B3_TUHO_CLEAN_PRODUCTION_PROMOTION_PROVEN",
    )
    for text in required:
        assert text in report
