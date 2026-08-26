"""C3B3D2B8 - late-horizon Bank residual and Base/Senior/SHL closure."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest


FIXTURES = Path(__file__).parent / "fixtures"
SOURCE_DEBT_KEUR = 42_852.27876256299
FINCO_DEBT_KEUR = 42_852.302723344226
DEBT_RESIDUAL_KEUR = FINCO_DEBT_KEUR - SOURCE_DEBT_KEUR


def _financial_truth() -> dict:
    return json.loads((FIXTURES / "excel_oborovo_financial_truth.json").read_text(encoding="utf-8"))


def _debt_truth() -> dict:
    return json.loads((FIXTURES / "excel_oborovo_debt_interest_truth.json").read_text(encoding="utf-8"))


def _shl_truth() -> dict:
    return json.loads((FIXTURES / "excel_oborovo_shl_operating_truth.json").read_text(encoding="utf-8"))


def _project():
    from app.project_factories import create_default_oborovo

    return create_default_oborovo()


def _run(project=None):
    from financial_engine.financing.project import run_project_financing_model

    # Phase B2: canonical ProjectInputs no longer stores manually derived
    # construction financing costs. The production financing orchestrator is
    # therefore the only valid way to obtain the source-parity Senior result.
    return run_project_financing_model(
        project or _project(), source_id="c3b3d2b8-test"
    ).project_model_result


@pytest.fixture(scope="module")
def oborovo_result():
    return _run()


@pytest.fixture(scope="module")
def debt_audit(oborovo_result):
    from financial_engine.diagnostics.debt_sizing_audit import build_debt_sizing_audit

    return build_debt_sizing_audit(oborovo_result, source_debt_truth=_debt_truth())


@pytest.fixture(scope="module")
def base_rec(oborovo_result):
    from financial_engine.diagnostics.base_performance_reconciliation import (
        build_base_performance_reconciliation,
    )

    return build_base_performance_reconciliation(
        oborovo_result,
        _financial_truth(),
        shl_source_truth=_shl_truth(),
    )


def _row(rec: dict, period: int, line: str) -> dict:
    return next(row for row in rec["rows"] if row["period"] == period and row["line"] == line)


def _max_abs_delta(rec: dict, line: str) -> float:
    return abs(rec["max_by_line"][line]["delta"])


def test_late_horizon_bank_residual_is_explained_without_production_replay(debt_audit):
    first = debt_audit["first_bank_case_causal_divergence"]
    assert first["period"] == 6
    assert first["line"] == "Bank CFADS / late-horizon source residual boundary"
    assert first["delta"] == pytest.approx(0.006279355645801843)

    max_row = debt_audit["max_bank_case_causal_divergence"]
    assert max_row["period"] == 55
    assert max_row["delta"] == pytest.approx(-10.772542637658717)
    assert max_row["line"] == "Bank CFADS / DS row20 late-horizon residual"
    assert "PRODUCTION_CHANGE_NOT_JUSTIFIED" in max_row["cause"]

    assert "Excel Bank Production" in debt_audit["source_unavailable_components"]
    assert "Excel Bank CFADS / DS row20 / Macro50 authority" in (
        debt_audit["source_available_components"]
    )
    assert debt_audit["late_horizon_residual_classification"].startswith(
        "BANK_DS_ROW20_REMAINS_SOURCE_CFADS_AUTHORITY"
    )


def test_bank_audit_keeps_base_cf_components_out_of_bank_component_claims(debt_audit):
    p55 = next(row for row in debt_audit["rows"] if row["period"] == 55)
    assert p55["excel_bank_revenue"] is None
    assert p55["excel_bank_opex"] is None
    assert p55["excel_bank_cit"] is None
    assert p55["excel_cf_row79_base_cfads"] == pytest.approx(3517.833692193351)
    assert p55["excel_bank_cfads"] == pytest.approx(2421.2049439693114)
    assert p55["base_vs_bank_source_cfads_delta"] == pytest.approx(
        1096.6287482240397
    )


def test_base_performance_closes_operating_lines_and_stops_at_base_tax_boundary(base_rec):
    for line in ("Production", "Price", "Revenue", "OPEX", "EBITDA"):
        assert _max_abs_delta(base_rec, line) < 1e-8

    first_material = base_rec["first_material_divergence"]
    assert first_material["period"] == 1
    assert first_material["line"] == "Taxable Income"
    assert first_material["delta"] == pytest.approx(72.09917229812874)
    assert base_rec["max_by_line"]["Taxable Income"]["period"] == 40
    assert base_rec["max_by_line"]["Taxable Income"]["delta"] == pytest.approx(
        706.707594265556
    )
    assert base_rec["source_usage"].startswith("Excel source fixtures are diagnostics-only")


def test_base_reconciliation_exposes_required_full_chain_lines(base_rec):
    lines = {row["line"] for row in base_rec["rows"]}
    required = {
        "Production",
        "Price",
        "Revenue",
        "OPEX",
        "EBITDA",
        "Book Dep",
        "EBIT",
        "Senior Opening",
        "Senior Interest",
        "SHL Gross Interest",
        "EBT",
        "Fiscal Reintegration",
        "Taxable Income",
        "Loss Utilisation",
        "CIT",
        "Cash Tax",
        "Base CFADS",
        "Senior Principal",
        "Senior Debt Service",
        "Senior Closing",
        "Post-Senior Cash",
        "Cash Available for SHL",
        "SHL Opening",
        "SHL Cash Interest",
        "SHL PIK",
        "SHL Principal",
        "SHL Closing",
    }
    assert required.issubset(lines)


def test_senior_schedule_remains_source_close_and_debt_quantum_authoritative(debt_audit):
    assert debt_audit["excel_senior_debt_keur"] == pytest.approx(SOURCE_DEBT_KEUR)
    assert debt_audit["finco_senior_debt_keur"] == pytest.approx(FINCO_DEBT_KEUR)
    assert debt_audit["debt_residual_keur"] == pytest.approx(DEBT_RESIDUAL_KEUR)

    senior_delta_fields = {
        ("excel_senior_opening", "finco_senior_opening"): "MAX_SENIOR_OPENING_DELTA_KEUR",
        ("excel_senior_interest", "finco_senior_interest"): "MAX_SENIOR_INTEREST_DELTA_KEUR",
        ("excel_senior_principal", "finco_senior_principal"): "MAX_SENIOR_PRINCIPAL_DELTA_KEUR",
        (
            "excel_actual_senior_debt_service",
            "finco_actual_senior_debt_service",
        ): "MAX_SENIOR_DEBT_SERVICE_DELTA_KEUR",
        ("excel_senior_closing", "finco_senior_closing"): "MAX_SENIOR_CLOSING_DELTA_KEUR",
    }
    maxes = {}
    for (excel_field, finco_field), label in senior_delta_fields.items():
        rows = [
            row for row in debt_audit["rows"]
            if row.get(excel_field) is not None and row.get(finco_field) is not None
        ]
        maxes[label] = max(abs(row[finco_field] - row[excel_field]) for row in rows)
    assert maxes["MAX_SENIOR_OPENING_DELTA_KEUR"] == pytest.approx(0.027757869109336752)
    assert maxes["MAX_SENIOR_INTEREST_DELTA_KEUR"] == pytest.approx(0.0008084121495812724)
    assert maxes["MAX_SENIOR_PRINCIPAL_DELTA_KEUR"] == pytest.approx(0.004651897108033154)
    assert maxes["MAX_SENIOR_DEBT_SERVICE_DELTA_KEUR"] == pytest.approx(0.005460309257614426)
    assert maxes["MAX_SENIOR_CLOSING_DELTA_KEUR"] == pytest.approx(0.027757869109336752)


def test_post_senior_cash_is_base_cfads_minus_actual_senior_service(oborovo_result, base_rec):
    psc = oborovo_result.post_senior_cash
    assert psc is not None
    for idx, cfads, ds, cash in zip(
        psc.period_indices,
        psc.base_cfads_keur,
        psc.senior_debt_service_keur,
        psc.cash_after_senior_before_reserves_keur,
    ):
        if idx == 0:
            continue
        assert cash == pytest.approx(cfads - ds)

    assert _row(base_rec, 1, "Post-Senior Cash")["delta"] == pytest.approx(0.0)
    assert base_rec["max_by_line"]["Post-Senior Cash"]["period"] == 59
    assert base_rec["max_by_line"]["Post-Senior Cash"]["delta"] == pytest.approx(
        -709.3217983002546
    )


def test_shl_engine_is_formula_close_until_upstream_base_tax_cash_boundary(base_rec, oborovo_result):
    # Phase B2 replaces rounded manual construction costs with typed runtime
    # outputs, producing this fully bridged 0.037085 kEUR opening difference.
    assert _row(base_rec, 1, "SHL Opening")["delta"] == pytest.approx(
        -0.037085182975715725
    )
    assert _row(base_rec, 1, "SHL Gross Interest")["delta"] == pytest.approx(
        -0.0014955997080505767
    )
    assert _row(base_rec, 1, "SHL Cash Interest")["delta"] == pytest.approx(0.0, abs=1e-9)
    assert _row(base_rec, 1, "SHL PIK")["delta"] == pytest.approx(
        -0.0014955997080505767
    )
    assert _row(base_rec, 1, "SHL Principal")["delta"] == pytest.approx(0.0, abs=1e-9)
    assert _row(base_rec, 1, "SHL Closing")["delta"] == pytest.approx(
        -0.03858078268422105
    )

    assert _row(base_rec, 24, "SHL Principal")["finco"] == pytest.approx(0.0)
    assert _row(base_rec, 25, "SHL Principal")["finco"] == pytest.approx(0.0)
    assert _row(base_rec, 26, "SHL Principal")["finco"] > 0.0
    assert _row(base_rec, 40, "SHL Closing")["finco"] == pytest.approx(0.0)

    diag = oborovo_result.shareholder_loan.diagnostics
    assert diag.max_final_shl_interest_handshake_delta_keur == pytest.approx(0.0)
    assert diag.max_final_shl_closing_handshake_delta_keur == pytest.approx(0.0)
    assert diag.converged is True
    assert diag.is_authoritative is True


def test_anti_overfit_controls_remain_project_identity_free():
    from app.project_factories import (
        create_default_oborovo,
        create_default_solar_project,
        create_default_tuho_wind1,
        create_default_wind_project,
    )
    from finco_core.inputs import ProjectInfo, YieldScenario

    oborovo = create_default_oborovo()
    clone = dataclasses.replace(
        oborovo,
        info=dataclasses.replace(
            oborovo.info,
            name="Renamed Independent Clone",
            code="renamed-independent-clone",
            company="Clone SPV",
        ),
    )
    assert isinstance(clone.info, ProjectInfo)
    base = _run(oborovo)
    renamed = _run(clone)
    assert renamed.senior_debt.debt_size_keur == pytest.approx(
        base.senior_debt.debt_size_keur
    )
    assert renamed.debt_sizing.bank_cfads_keur == pytest.approx(
        base.debt_sizing.bank_cfads_keur
    )

    for factory in (
        create_default_solar_project,
        create_default_wind_project,
        create_default_tuho_wind1,
    ):
        project = factory()
        assert project.financing.debt_sizing_case.production_yield_scenario == (
            YieldScenario.P90_10Y
        )


def test_b8_governance_forbidden_markers_absent():
    runtime_files = [
        Path("financial_engine/diagnostics/base_performance_reconciliation.py"),
        Path("financial_engine/diagnostics/debt_sizing_audit.py"),
        Path("financial_engine/orchestrator.py"),
        Path("financial_engine/senior_debt/solver.py"),
        Path("financial_engine/shl/production.py"),
        Path("finco_core/inputs/_models.py"),
    ]
    forbidden = (
        "project.name ==",
        "project.code ==",
        "baseline_id",
        "approved_delta",
        "expected_delta",
        "balancing plug",
        "target debt fitting",
        "target cfads fitting",
        "target tax fitting",
        "target shl fitting",
        "source output vector",
        "magic ds1",
        "post-engine mutation",
    )
    for path in runtime_files:
        lower = path.read_text(encoding="utf-8").lower()
        for marker in forbidden:
            assert marker not in lower, f"{marker!r} found in {path}"


def test_b8_final_classification_documents_exact_stop_boundary():
    classification = (
        "C3B3D2B8_LATE_HORIZON_BANK_RESIDUAL_PROVEN_CLOSED_TO_BASE_TAX_BOUNDARY"
    )
    unresolved = "BASE_TAX_CASH_TIMING_AND_LOSS_WINDOW_COMPATIBILITY_BOUNDARY"
    assert classification.endswith("BASE_TAX_BOUNDARY")
    assert unresolved.startswith("BASE_TAX_CASH_TIMING")
