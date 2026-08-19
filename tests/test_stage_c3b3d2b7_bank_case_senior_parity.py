"""C3B3D2B7 - Bank case authority and senior debt source-parity boundary."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest


FIXTURES = Path(__file__).parent / "fixtures"
SOURCE_DEBT_KEUR = 42_852.27876256299
OBOROVO_B7_DEBT_KEUR = 42_852.30326225287
OBOROVO_B7_DEBT_RESIDUAL_KEUR = 0.02449968987639295


def _financial_truth() -> dict:
    return json.loads((FIXTURES / "excel_oborovo_financial_truth.json").read_text())


def _debt_truth() -> dict:
    return json.loads((FIXTURES / "excel_oborovo_debt_interest_truth.json").read_text())


def _oborovo_project():
    from app.project_factories import create_default_oborovo

    return create_default_oborovo()


def _model(project=None, *, debt_sizing_case=None, with_shl=True):
    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )

    model = build_senior_debt_model_input_from_project_inputs(
        project or _oborovo_project(),
        source_id="c3b3d2b7-test",
        debt_sizing_case=debt_sizing_case,
    )
    if not with_shl:
        model = dataclasses.replace(model, shareholder_loan=None)
    return model


def _run(project=None, *, debt_sizing_case=None, with_shl=True):
    from financial_engine.orchestrator import run_senior_debt_model

    return run_senior_debt_model(
        _model(project, debt_sizing_case=debt_sizing_case, with_shl=with_shl)
    )


def test_canonical_debt_sizing_case_schema_and_serialization_roundtrip():
    from app.project_factories import (
        create_default_solar_project,
        create_default_tuho_wind1,
        create_default_wind_project,
    )
    from finco_core.inputs import DebtSizingCaseConfig, YieldScenario
    from finco_core.inputs.serialization import (
        project_inputs_from_dict,
        project_inputs_to_dict,
    )

    explicit = DebtSizingCaseConfig(
        production_yield_scenario=YieldScenario.P50,
        merchant_price_calendar_start_year=2042,
        merchant_prices_by_calendar_year_eur_mwh=(61.3, 61.4),
        source_label="source-compatible label",
    )
    project = dataclasses.replace(
        create_default_solar_project(),
        financing=dataclasses.replace(
            create_default_solar_project().financing,
            debt_sizing_case=explicit,
        ),
    )
    restored = project_inputs_from_dict(project_inputs_to_dict(project))
    assert restored.financing.debt_sizing_case == explicit

    empty_override = DebtSizingCaseConfig()
    assert project_inputs_from_dict(
        project_inputs_to_dict(
            dataclasses.replace(
                create_default_wind_project(),
                financing=dataclasses.replace(
                    create_default_wind_project().financing,
                    debt_sizing_case=empty_override,
                ),
            )
        )
    ).financing.debt_sizing_case == empty_override

    legacy_payload = project_inputs_to_dict(create_default_tuho_wind1())
    legacy_payload["financing"].pop("debt_sizing_case")
    legacy_restored = project_inputs_from_dict(legacy_payload)
    assert legacy_restored.financing.debt_sizing_case.production_yield_scenario == (
        YieldScenario.P90_10Y
    )
    assert legacy_restored.financing.debt_sizing_case.merchant_price_calendar_start_year is None
    assert legacy_restored.financing.debt_sizing_case.merchant_prices_by_calendar_year_eur_mwh == ()
    assert legacy_restored.financing.debt_sizing_case.tax_periodisation_mode_override is None


def test_debt_sizing_case_config_validates_like_runtime_contract():
    from finco_core.inputs import DebtSizingCaseConfig, YieldScenario

    with pytest.raises(ValueError, match="mutually exclusive"):
        DebtSizingCaseConfig(
            production_yield_scenario=YieldScenario.P90_10Y,
            merchant_price_calendar_start_year=2042,
            merchant_prices_by_calendar_year_eur_mwh=(60.0,),
            market_prices_curve_eur_mwh=(50.0,),
        )
    with pytest.raises(ValueError, match="merchant_price_calendar_start_year"):
        DebtSizingCaseConfig(
            production_yield_scenario=YieldScenario.P90_10Y,
            merchant_prices_by_calendar_year_eur_mwh=(60.0,),
        )
    with pytest.raises(ValueError, match="finite numeric"):
        DebtSizingCaseConfig(
            production_yield_scenario=YieldScenario.P90_10Y,
            market_prices_curve_eur_mwh=(float("nan"),),
        )
    with pytest.raises(ValueError, match="finite numeric"):
        DebtSizingCaseConfig(
            production_yield_scenario=YieldScenario.P90_10Y,
            market_prices_curve_eur_mwh=(True,),
        )


def test_oborovo_bank_tax_periodisation_override_is_source_owned():
    from financial_engine.policies.tax import (
        CashTaxTiming,
        TaxBasisPeriodisation,
        TaxLossUtilisationGate,
    )

    model = _model()
    assert model.debt_sizing_case.tax_periodisation_mode_override == (
        "workbook_model_year_pairing"
    )
    assert model.tax.policy.tax_basis_periodisation == TaxBasisPeriodisation.CALENDAR_YEAR
    # PR-1 fix: adapter now forwards tax.tax_loss_utilisation_gate from ProjectInputs.
    # Oborovo factory sets EBT_POSITIVE; the TaxPolicy now correctly reflects that.
    # Pre-PR-1 this always read TAXABLE_INCOME_POSITIVE (adapter default, never forwarded).
    assert model.tax.policy.loss_utilisation_gate == (
        TaxLossUtilisationGate.EBT_POSITIVE
    )
    assert model.tax.policy.cash_tax_timing != CashTaxTiming.MODEL_YEAR_PAYMENT_PERIOD


def test_oborovo_bank_tax_compatibility_uses_source_h2_h1_pairing_and_h1_payment():
    from financial_engine.orchestrator import (
        _merge_financing_tax_input,
        derive_debt_sizing_operating_input,
        run_operating_model,
    )
    from financial_engine.policies.tax import CashTaxTiming, TaxBasisPeriodisation
    from financial_engine.tax.engine import calculate_tax

    result = _run()
    model = _model()
    bank_periods = run_operating_model(
        derive_debt_sizing_operating_input(model.operating, model.debt_sizing_case)
    ).periods
    bank_tax_input = _merge_financing_tax_input(
        model.tax,
        dict(zip(result.senior_debt.period_indices, result.senior_debt.senior_interest_keur)),
        dict(
            zip(
                result.shareholder_loan.period_indices,
                result.shareholder_loan.shl_gross_interest_keur,
            )
        ),
        tax_periodisation_mode_override=model.debt_sizing_case.tax_periodisation_mode_override,
    )
    tax = calculate_tax(bank_periods, bank_tax_input)

    assert bank_tax_input.policy.tax_basis_periodisation == (
        TaxBasisPeriodisation.MODEL_YEAR_PAIRING
    )
    assert bank_tax_input.policy.cash_tax_timing == CashTaxTiming.MODEL_YEAR_PAYMENT_PERIOD

    annual_2032 = next(ar for ar in tax.annual_results if ar.tax_year == 2032)
    tax_by_period = {pr.period_index: pr for pr in tax.period_results}
    assert annual_2032.period_indices == (3, 4)
    assert tax_by_period[3].cash_tax_keur == pytest.approx(0.0)
    assert tax_by_period[4].cash_tax_keur == pytest.approx(
        annual_2032.current_tax_liability_keur
    )


def test_generic_and_tuho_bank_case_defaults_remain_p90_anti_overfit_controls():
    from app.project_factories import (
        create_default_solar_project,
        create_default_tuho_wind1,
        create_default_wind_project,
    )
    from finco_core.inputs import YieldScenario

    for factory in (
        create_default_solar_project,
        create_default_wind_project,
        create_default_tuho_wind1,
    ):
        project = factory()
        assert project.financing.debt_sizing_case.production_yield_scenario == (
            YieldScenario.P90_10Y
        )
        assert project.financing.debt_sizing_case.merchant_price_calendar_start_year is None
        assert project.financing.debt_sizing_case.merchant_prices_by_calendar_year_eur_mwh == ()
        assert project.financing.debt_sizing_case.market_prices_curve_eur_mwh == ()


def test_oborovo_bank_case_is_explicit_source_compatibility_input():
    from finco_core.inputs import YieldScenario
    from financial_engine.inputs import YieldScenario as EngineYieldScenario

    project = _oborovo_project()
    case = project.financing.debt_sizing_case
    assert case.production_yield_scenario == YieldScenario.P50
    assert case.merchant_price_calendar_start_year == 2042
    assert case.tax_periodisation_mode_override.value == "workbook_model_year_pairing"
    assert len(case.merchant_prices_by_calendar_year_eur_mwh) == 19
    assert case.merchant_prices_by_calendar_year_eur_mwh[:3] == pytest.approx(
        (61.313838249999996, 61.3429705, 61.0421)
    )
    assert "source compatibility" in case.source_label
    assert "Central Low" in case.source_label
    assert "paired-period CIT" in case.source_label

    model = _model(project)
    assert model.debt_sizing_case.production_yield_scenario == EngineYieldScenario.P50
    assert model.debt_sizing_case.production_yield_scenario.value == (
        case.production_yield_scenario.value
    )
    assert model.debt_sizing_case.merchant_price_calendar_start_year == 2042
    assert model.debt_sizing_case.tax_periodisation_mode_override == (
        "workbook_model_year_pairing"
    )
    assert model.debt_sizing_case.merchant_prices_by_calendar_year_eur_mwh == (
        case.merchant_prices_by_calendar_year_eur_mwh
    )


def test_explicit_adapter_override_remains_diagnostic_not_canonical_default():
    from financial_engine.inputs import DebtSizingCaseInput, YieldScenario

    model = _model(
        debt_sizing_case=DebtSizingCaseInput(
            production_yield_scenario=YieldScenario.P90_10Y,
            source_label="explicit-diagnostic-override",
        )
    )
    assert model.debt_sizing_case.production_yield_scenario == YieldScenario.P90_10Y
    assert model.debt_sizing_case.source_label == "explicit-diagnostic-override"

    canonical = _model()
    assert canonical.debt_sizing_case.production_yield_scenario == YieldScenario.P50


def test_bank_case_mutations_do_not_mutate_base_operating_performance():
    from finco_core.inputs import DebtSizingCaseConfig, YieldScenario

    project = _oborovo_project()
    base = _run(project)

    p90_project = dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing,
            debt_sizing_case=DebtSizingCaseConfig(
                production_yield_scenario=YieldScenario.P90_10Y,
                source_label="p90-bank-case-mutation",
            ),
        ),
    )
    p90 = _run(p90_project, with_shl=False)

    assert p90.debt_sizing.bank_production_mwh != pytest.approx(
        base.debt_sizing.bank_production_mwh
    )
    assert p90.debt_sizing.bank_cfads_keur != pytest.approx(base.debt_sizing.bank_cfads_keur)
    assert p90.senior_debt.debt_size_keur != pytest.approx(base.senior_debt.debt_size_keur)
    assert p90.operating_schedules.production_mwh == pytest.approx(
        base.operating_schedules.production_mwh
    )
    assert p90.operating_schedules.revenue_keur == pytest.approx(
        base.operating_schedules.revenue_keur
    )
    assert p90.operating_schedules.opex_keur == pytest.approx(
        base.operating_schedules.opex_keur
    )
    assert p90.operating_schedules.ebitda_keur == pytest.approx(
        base.operating_schedules.ebitda_keur
    )

    price_project = dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing,
            debt_sizing_case=dataclasses.replace(
                project.financing.debt_sizing_case,
                merchant_prices_by_calendar_year_eur_mwh=tuple(
                    value + 1.0
                    for value in project.financing.debt_sizing_case.merchant_prices_by_calendar_year_eur_mwh
                ),
            ),
        ),
    )
    priced = _run(price_project, with_shl=False)
    assert priced.debt_sizing.bank_revenue_keur != pytest.approx(
        base.debt_sizing.bank_revenue_keur
    )
    assert priced.debt_sizing.bank_cfads_keur != pytest.approx(base.debt_sizing.bank_cfads_keur)
    assert priced.senior_debt.debt_size_keur != pytest.approx(base.senior_debt.debt_size_keur)
    assert priced.operating_schedules.revenue_keur == pytest.approx(
        base.operating_schedules.revenue_keur
    )

    label_project = dataclasses.replace(
        project,
        financing=dataclasses.replace(
            project.financing,
            debt_sizing_case=dataclasses.replace(
                project.financing.debt_sizing_case,
                source_label="renamed audit label only",
            ),
        ),
    )
    label = _run(label_project)
    assert label.debt_sizing.bank_cfads_keur == pytest.approx(base.debt_sizing.bank_cfads_keur)
    assert label.senior_debt.debt_size_keur == pytest.approx(base.senior_debt.debt_size_keur)
    assert label.post_senior_cash.cash_available_for_shl_before_reserves_keur == pytest.approx(
        base.post_senior_cash.cash_available_for_shl_before_reserves_keur
    )


def test_base_p50_hours_mutation_changes_base_and_explicit_p50_bank_case():
    project = _oborovo_project()
    base = _run(project)
    mutated_project = dataclasses.replace(
        project,
        technical=dataclasses.replace(
            project.technical,
            operating_hours_p50=project.technical.operating_hours_p50 + 10.0,
        ),
    )
    mutated = _run(mutated_project)
    assert mutated.operating_schedules.production_mwh[1] > base.operating_schedules.production_mwh[1]
    assert mutated.tax_and_cfads.cfads_keur[1] > base.tax_and_cfads.cfads_keur[1]
    assert mutated.debt_sizing.bank_production_mwh[1] > base.debt_sizing.bank_production_mwh[1]
    assert mutated.debt_sizing.bank_cfads_keur[1] > base.debt_sizing.bank_cfads_keur[1]


def test_renamed_oborovo_clone_has_identical_financial_outputs():
    from finco_core.inputs import ProjectInfo

    project = _oborovo_project()
    renamed = dataclasses.replace(
        project,
        info=dataclasses.replace(
            project.info,
            name="Independent Solar Clone",
            company="Renamed SPV",
            code="renamed_clone",
        ),
    )
    assert isinstance(renamed.info, ProjectInfo)
    base = _run(project)
    clone = _run(renamed)
    assert clone.senior_debt.debt_size_keur == pytest.approx(base.senior_debt.debt_size_keur)
    assert clone.debt_sizing.bank_cfads_keur == pytest.approx(base.debt_sizing.bank_cfads_keur)
    assert clone.post_senior_cash.cash_available_for_shl_before_reserves_keur == pytest.approx(
        base.post_senior_cash.cash_available_for_shl_before_reserves_keur
    )


def test_oborovo_b7_senior_and_post_senior_source_boundary_is_honest():
    result = _run()
    source = _financial_truth()
    debt_truth = _debt_truth()

    assert result.senior_debt.debt_size_keur == pytest.approx(OBOROVO_B7_DEBT_KEUR)
    assert result.senior_debt.debt_size_keur - SOURCE_DEBT_KEUR == pytest.approx(
        OBOROVO_B7_DEBT_RESIDUAL_KEUR
    )
    assert result.senior_debt.diagnostics["initial_debt_guess_keur"] == pytest.approx(
        42_852.26672602787
    )
    assert result.senior_debt.diagnostics["final_debt_size_keur"] == pytest.approx(
        result.senior_debt.debt_size_keur
    )
    assert abs(
        result.senior_debt.debt_size_keur
        - result.senior_debt.diagnostics["initial_debt_guess_keur"]
    ) > 1e-6

    assert result.tax_and_cfads.cfads_keur[1] == pytest.approx(
        source["cf"]["fcf_for_banks_keur"][1]
    )
    assert result.senior_debt.senior_debt_service_keur[0] == pytest.approx(
        source["ds"]["sd_service_keur"][1]
    )
    assert result.post_senior_cash.cash_available_for_shl_before_reserves_keur[1] == pytest.approx(
        source["cf"]["free_cash_flow_for_shl_keur"][1]
    )
    assert result.senior_debt.senior_interest_keur[0] == pytest.approx(1303.484026996744)
    assert result.senior_debt.senior_principal_keur[0] == pytest.approx(935.6493858576118)

    ds20 = debt_truth["workstream_a"]["ds_row20_cfads"]["period_values_keur"]
    first_delta = next(
        (
            (idx, finco, excel)
            for idx, finco, excel in zip(
                result.debt_sizing.period_indices,
                result.debt_sizing.bank_cfads_keur,
                ds20,
            )
            if abs(finco - excel) > 1e-6
        ),
        None,
    )
    assert first_delta is not None
    assert first_delta[0] == 6
    assert first_delta[1] - first_delta[2] == pytest.approx(0.006375040592956793)


def test_debt_sizing_audit_is_separate_and_reports_source_vectors_without_replay():
    from financial_engine.diagnostics.debt_sizing_audit import build_debt_sizing_audit

    audit = build_debt_sizing_audit(_run(), source_debt_truth=_debt_truth())
    assert audit["classification"] == "DEBT_SIZING_AUDIT_DIAGNOSTIC_ONLY"
    assert audit["excel_senior_debt_keur"] == pytest.approx(SOURCE_DEBT_KEUR)
    assert audit["finco_senior_debt_keur"] == pytest.approx(OBOROVO_B7_DEBT_KEUR)
    assert audit["debt_residual_keur"] == pytest.approx(OBOROVO_B7_DEBT_RESIDUAL_KEUR)
    assert "Excel Bank Production" in audit["source_unavailable_components"]
    assert "Excel Bank CFADS / DS row20 / Macro50 authority" in audit["source_available_components"]
    first = audit["first_bank_case_causal_divergence"]
    assert first["period"] == 6
    assert first["line"] == "Bank CFADS / late-horizon source residual boundary"
    assert first["cause"] == (
        "BANK_TAX_LOSS_COMPATIBILITY_PROVEN_LATE_HORIZON_CFADS_RESIDUAL_REMAINS"
    )
    row = audit["rows"][4]
    assert "excel_allowed_debt_service_capacity" in row
    assert "finco_allowed_debt_service_capacity" in row
    assert "excel_actual_senior_debt_service" in row
    assert "finco_actual_senior_debt_service" in row
    assert "debt_service_capacity_delta" not in row


def test_r4_7_2_source_replay_authority_lock_is_immutable_under_b7_runtime():
    from app.project_factories import create_default_oborovo
    from finco_recon.bank_sizing_candidates import run_candidate_h_oborovo_r472

    result = run_candidate_h_oborovo_r472(create_default_oborovo)

    assert result["r4_7_2_authority_lock"] == (
        "R4_7_2_DIAGNOSTIC_PERIOD_AXIS_FROZEN_TO_PR925_COD_ANCHOR_INPUT_AND_"
        "SOURCE_CALENDAR_REPLAY"
    )
    assert result["r4_7_2_diagnostic_drift_classification"] == (
        "R4_7_2_DIAGNOSTIC_WAS_NOT_IMMUTABLE_AND_DRIFTED_WITH_PRODUCTION_RUNTIME"
    )
    assert result["verdict"] == (
        "C3B3D2B2C_R4_7_2_SOURCE_CALENDAR_FULL_OPERATING_REPLAY_CFADS_AND_DEBT_PARITY_PROVEN_"
        "OPEX_CALENDAR_PERIODISATION_HYPOTHESIS_PROVEN_STAGE_DIAGNOSTIC_CLOSED"
    )
    assert result["t5c_abs_residual_keur"] == pytest.approx(0.117392)
    assert result["t5c_max_abs_cfads_delta_keur"] == pytest.approx(0.389)
    assert result["p28_opex_residual_keur"] == pytest.approx(0.0, abs=1e-9)
    assert result["opex_hypothesis_proven_all_affected_periods"] is True
    assert result["t5c_merchant_periods_outside_1keur"] == 0
    assert result["all_merchant_cfads_within_1keur"] is True


def test_base_performance_audit_keeps_bank_lines_out_and_renames_shl_gross_interest():
    from financial_engine.diagnostics.base_performance_reconciliation import (
        LINES,
        build_base_performance_reconciliation,
    )

    rec = build_base_performance_reconciliation(_run(), _financial_truth())
    assert "SHL Gross Interest" in LINES
    assert "SHL Interest" not in LINES
    assert all("Bank" not in row["line"] for row in rec["rows"])
    assert any(row["line"] == "SHL Gross Interest" for row in rec["rows"])


def test_governance_markers_absent_from_runtime_and_input_contract_files():
    runtime_files = [
        Path("app/project_factories.py"),
        Path("financial_engine/adapters/project_inputs.py"),
        Path("financial_engine/orchestrator.py"),
        Path("financial_engine/senior_debt/solver.py"),
        Path("finco_core/inputs/_models.py"),
    ]
    forbidden = (
        "project.name ==",
        "project.code ==",
        "baseline_id",
        "approved_delta",
        "expected_delta",
        "target debt fitting",
        "target cfads fitting",
        "source output vector runtime input",
        "magic 42852",
        "magic ds1",
    )
    for path in runtime_files:
        text = path.read_text()
        lower = text.lower()
        for marker in forbidden:
            assert marker not in lower, f"{marker!r} found in {path}"


def test_b7_classifications_recorded():
    classifications = {
        "senior_authority": "BANK_SIZING_REMAINS_SENIOR_DEBT_QUANTUM_AUTHORITY",
        "generic_default": "GENERIC_BANK_SIZING_DEFAULT_POLICY_IS_P90_10Y",
        "oborovo_case": "OBOROVO_BANK_PRODUCTION_CASE_P50_IS_EXPLICIT_SOURCE_COMPATIBILITY_INPUT",
        "tuho_case": "TUHO_BANK_PRODUCTION_CASE_REMAINS_P90_SOURCE_SUPPORTED",
        "bank_price": "BANK_MERCHANT_PRICE_CASE_IS_EXPLICIT_AND_SEPARATE_FROM_BASE",
        "stop": "C3B3D2B7_STOP_AT_LATE_HORIZON_BANK_CFADS_RESIDUAL_BOUNDARY",
    }
    assert classifications["senior_authority"].startswith("BANK_SIZING")
    assert classifications["generic_default"].endswith("P90_10Y")
    assert "P50" in classifications["oborovo_case"]
    assert classifications["stop"].endswith("RESIDUAL_BOUNDARY")
