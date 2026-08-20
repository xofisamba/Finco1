"""PR-6 typed SHL repayment authority and source-first acceptance."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from finco_core.inputs import SHLRepaymentMethod
from financial_engine.shl.contracts import (
    ShlRepaymentMode,
    ShlSchedulePolicy,
)
from financial_engine.shl.waterfall import compute_shl_waterfall_period


FIXTURE = Path(__file__).parent / "fixtures" / "prefreeze_pr6_shl_repayment_source_lock.json"
EXPECTED_HASHES = {
    "TUHO": "780779eba4278ccc2b8546a9411ccee24917d388f411ba60c88aa342cb5c727a",
    "OBOROVO": "15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920",
    "KUPI": "111178fb21109f55df45c0cc1ea108104ac8b6ed60f010ba75b6c498795f5954",
}


@pytest.fixture(scope="module")
def source_truth() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_source_fixture_is_validation_only_and_hash_locked(source_truth):
    assert source_truth["_meta"]["classification"] == "SOURCE_TYPED_SHL_CASH_SWEEP_AUTHORITY"
    assert source_truth["_meta"]["runtime_use"] == "FORBIDDEN_TEST_EVIDENCE_ONLY"
    for project, expected_hash in EXPECTED_HASHES.items():
        evidence = source_truth["projects"][project]
        assert evidence["workbook_sha256"] == expected_hash
        assert evidence["repayment_mode"] == "CASH_SWEEP"
        assert evidence["annual_rate"] == pytest.approx(0.08)
        assert evidence["formula_lock"]


@pytest.mark.parametrize(
    ("project", "expected_start", "expected_maturity"),
    (("TUHO", 25, 36), ("OBOROVO", 25, 40), ("KUPI", 1, 20)),
)
def test_source_cash_oracle_proves_one_natural_cash_sweep(
    source_truth, project, expected_start, expected_maturity
):
    evidence = source_truth["projects"][project]
    assert evidence["repayment_start_period_index"] == expected_start
    assert evidence["maturity_period_index"] == expected_maturity

    periods = evidence["periods"]
    opening = periods[0]["closing_balance_keur"]
    maxima = {name: 0.0 for name in ("opening", "gross", "cash", "pik", "principal", "closing")}
    first_divergence = None
    for period in periods[1:]:
        result = compute_shl_waterfall_period(
            opening_balance_keur=opening,
            annual_rate=evidence["annual_rate"],
            day_count_fraction=period["day_count_fraction"],
            cash_available_for_shl_keur=period["cash_available_for_shl_keur"],
            period_index=period["period_index"],
            repayment_mode=ShlRepaymentMode.CASH_SWEEP,
        )
        comparisons = {
            "opening": (result.opening_balance_keur, period["opening_balance_keur"]),
            "gross": (result.gross_accrued_interest_keur, period["gross_interest_keur"]),
            "cash": (result.cash_interest_keur, period["cash_interest_keur"]),
            "pik": (result.pik_interest_keur, period["pik_interest_keur"]),
            "principal": (result.principal_repaid_keur, period["principal_keur"]),
            "closing": (result.closing_balance_keur, period["closing_balance_keur"]),
        }
        for name, (actual, expected) in comparisons.items():
            delta = abs(actual - expected)
            maxima[name] = max(maxima[name], delta)
            if first_divergence is None and delta > 1e-9:
                first_divergence = (period["period_index"], name, actual, expected)
        opening = result.closing_balance_keur

    assert first_divergence is None
    assert max(maxima.values()) < 1e-9
    assert opening == pytest.approx(0.0, abs=1e-9)


def test_source_formula_cells_lock_cash_and_repayment_lineage(source_truth):
    tuho = source_truth["projects"]["TUHO"]["formula_lock"]
    oborovo = source_truth["projects"]["OBOROVO"]["formula_lock"]
    kupi = source_truth["projects"]["KUPI"]["formula_lock"]
    assert tuho["CF!H102"] == "=H99"
    assert tuho["DS!AF124"] == "=AF137+AF148+AF159"
    assert oborovo["CF!H112"] == "=H109"
    assert oborovo["DS!AF127"] == "=AF140+AF151+AF162"
    assert kupi["CF!H102"] == "=H99"
    assert kupi["DS!H124"] == "=H137+H148+H159"


@pytest.mark.parametrize(
    ("cash", "expected_cash_interest", "expected_pik", "expected_principal", "expected_closing"),
    (
        (0.0, 0.0, 80.0, 0.0, 1080.0),
        (40.0, 40.0, 40.0, 0.0, 1040.0),
        (100.0, 80.0, 0.0, 20.0, 980.0),
        (2000.0, 80.0, 0.0, 1000.0, 0.0),
    ),
)
def test_cash_sweep_synthetic_discrimination(
    cash, expected_cash_interest, expected_pik, expected_principal, expected_closing
):
    result = compute_shl_waterfall_period(
        opening_balance_keur=1000.0,
        annual_rate=0.08,
        day_count_fraction=1.0,
        cash_available_for_shl_keur=cash,
        repayment_mode=ShlRepaymentMode.CASH_SWEEP,
    )
    assert result.cash_interest_keur == pytest.approx(expected_cash_interest)
    assert result.pik_interest_keur == pytest.approx(expected_pik)
    assert result.principal_repaid_keur == pytest.approx(expected_principal)
    assert result.closing_balance_keur == pytest.approx(expected_closing)


def test_bullet_discrimination_has_no_pre_maturity_sweep():
    before = compute_shl_waterfall_period(
        1000.0, 0.08, 1.0, 2000.0,
        repayment_mode=ShlRepaymentMode.BULLET,
        is_maturity_period=False,
    )
    maturity = compute_shl_waterfall_period(
        1000.0, 0.08, 1.0, 2000.0,
        repayment_mode=ShlRepaymentMode.BULLET,
        is_maturity_period=True,
    )
    assert before.principal_repaid_keur == 0.0
    assert maturity.principal_repaid_keur == pytest.approx(1000.0)


def test_factories_emit_typed_clean_policy_without_source_aliases():
    from app.project_factories import (
        create_default_oborovo,
        create_default_solar_project,
        create_default_wind_project,
    )
    from tests.diagnostics.kupi_k0_k3_causal_grid import build_kupi_project_inputs

    assert create_default_oborovo().financing.clean_shl_repayment_method is SHLRepaymentMethod.CASH_SWEEP
    assert create_default_solar_project().financing.clean_shl_repayment_method is SHLRepaymentMethod.BULLET
    assert create_default_wind_project().financing.clean_shl_repayment_method is SHLRepaymentMethod.BULLET
    assert build_kupi_project_inputs().financing.clean_shl_repayment_method is SHLRepaymentMethod.CASH_SWEEP


def test_typed_policy_round_trips_and_unknown_serialized_value_fails_closed():
    from app.project_factories import create_default_oborovo
    from finco_core.inputs.serialization import project_inputs_from_dict, project_inputs_to_dict

    payload = project_inputs_to_dict(create_default_oborovo())
    assert payload["financing"]["clean_shl_repayment_method"] == "cash_sweep"
    restored = project_inputs_from_dict(payload)
    assert restored.financing.clean_shl_repayment_method is SHLRepaymentMethod.CASH_SWEEP
    payload["financing"]["clean_shl_repayment_method"] = "unknown"
    with pytest.raises(ValueError, match="'unknown' is not a valid SHLRepaymentMethod"):
        project_inputs_from_dict(payload)


@pytest.fixture(scope="module")
def solar_bullet_result():
    from app.project_factories import create_default_solar_project
    from financial_engine.shareholder_waterfall.model import run_project_shareholder_waterfall_model

    project = create_default_solar_project()
    project = dataclasses.replace(
        project,
        tax=dataclasses.replace(project.tax, corporate_rate=0.0),
    )
    return run_project_shareholder_waterfall_model(project)


@pytest.fixture(scope="module")
def solar_sweep_result():
    from app.project_factories import create_default_solar_project
    from financial_engine.shareholder_waterfall.model import run_project_shareholder_waterfall_model

    project = create_default_solar_project()
    project = dataclasses.replace(
        project,
        tax=dataclasses.replace(project.tax, corporate_rate=0.0),
        financing=dataclasses.replace(
            project.financing,
            clean_shl_repayment_method=SHLRepaymentMethod.CASH_SWEEP,
            shl_principal_eligibility_start_period=2,
            shl_maturity_period_index=42,
        ),
    )
    return run_project_shareholder_waterfall_model(project)


def test_real_production_mode_mutation_changes_only_shl_principal_timing(
    solar_bullet_result, solar_sweep_result
):
    bullet = [p for p in solar_bullet_result.waterfall_periods if not p.is_construction]
    sweep = [p for p in solar_sweep_result.waterfall_periods if not p.is_construction]
    assert [p.signed_post_senior_keur for p in bullet] == pytest.approx(
        [p.signed_post_senior_keur for p in sweep]
    )
    assert [p.senior_dsra_target_keur for p in bullet] == pytest.approx(
        [p.senior_dsra_target_keur for p in sweep]
    )
    bullet_first = next(p.period_index for p in bullet if p.shl_principal_receipt_keur > 1e-9)
    sweep_first = next(p.period_index for p in sweep if p.shl_principal_receipt_keur > 1e-9)
    assert sweep_first < bullet_first


def test_real_bullet_actual_payment_never_manufactures_cash(solar_bullet_result):
    maturity = next(
        p for p in solar_bullet_result.waterfall_periods
        if p.contractual_shl_principal_due_keur > 0.0
    )
    available_after_interest = max(
        0.0, maturity.shl_cash_input_keur - maturity.shl_cash_interest_receipt_keur
    )
    assert maturity.actual_shl_principal_paid_keur == pytest.approx(available_after_interest)
    assert maturity.actual_shl_principal_paid_keur < maturity.contractual_shl_principal_due_keur
    assert maturity.unpaid_shl_principal_keur > 0.0
    assert maturity.actual_shl_closing_balance_keur > 0.0


def test_project_identity_mutation_cannot_change_typed_shl_output():
    from app.project_factories import create_default_solar_project
    from financial_engine.shareholder_waterfall.model import run_project_shareholder_waterfall_model

    project = create_default_solar_project()
    renamed = dataclasses.replace(
        project,
        info=dataclasses.replace(project.info, name="Renamed", code="RENAMED"),
    )
    original_result = run_project_shareholder_waterfall_model(project)
    renamed_result = run_project_shareholder_waterfall_model(renamed)
    original = [
        (p.shl_cash_interest_receipt_keur, p.shl_pik_keur, p.shl_principal_receipt_keur,
         p.shl_closing_balance_keur)
        for p in original_result.waterfall_periods
    ]
    changed = [
        (p.shl_cash_interest_receipt_keur, p.shl_pik_keur, p.shl_principal_receipt_keur,
         p.shl_closing_balance_keur)
        for p in renamed_result.waterfall_periods
    ]
    for changed_period, original_period in zip(changed, original):
        assert changed_period == pytest.approx(original_period)


def test_clean_adapter_has_no_identity_dispatch_or_silent_string_fallback():
    source = Path("financial_engine/adapters/project_inputs.py").read_text(encoding="utf-8")
    for forbidden in ("project.name", "project.code", '"TUHO"', '"Oborovo"', '"KUPI"'):
        assert forbidden not in source
    assert "or getattr(financing, \"shl_repayment_method\"" not in source
    assert "_CLEAN_SHL_REPAYMENT_MODE_MAP" in source


def test_explicit_schedule_remains_lower_level_generic_capability_only():
    from financial_engine.shl.contracts import ShlPeriodInput
    from financial_engine.shl.schedule import run_shl_schedule

    policy = ShlSchedulePolicy(
        annual_rate=0.0,
        repayment_mode=ShlRepaymentMode.EXPLICIT_SCHEDULE,
    )
    result = run_shl_schedule(
        1000.0,
        (ShlPeriodInput(0, 1.0, scheduled_principal_keur=400.0),),
        policy,
    )
    assert result[0].scheduled_principal_keur == pytest.approx(400.0)
    assert result[0].closing_balance_keur == pytest.approx(600.0)
    with pytest.raises(ValueError, match="scheduled_principal_keur"):
        run_shl_schedule(
            1000.0,
            (ShlPeriodInput(0, 1.0, scheduled_principal_keur=1001.0),),
            policy,
        )


def test_forbidden_calibration_mechanisms_absent_from_pr6_runtime_changes():
    sources = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            "financial_engine/adapters/project_inputs.py",
            "finco_core/inputs/_models.py",
        )
    ).lower()
    for forbidden in (
        "approved_delta", "expected_delta", "balancing plug", "terminal top-up",
        "forced principal", "target fitting", "post-engine mutation",
    ):
        assert forbidden not in sources
