"""C3B3D2B6 - Base performance and post-senior cash reconciliation."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest


FIXTURES = Path(__file__).parent / "fixtures"


def _source():
    return json.loads((FIXTURES / "excel_oborovo_financial_truth.json").read_text())


def _project():
    from app.project_factories import create_default_oborovo

    return create_default_oborovo()


def _run_project(project=None, *, source_id="c3b3d2b6-test", bank_case=None, with_shl=True):
    import dataclasses

    from financial_engine.adapters.project_inputs import (
        build_senior_debt_model_input_from_project_inputs,
    )
    from financial_engine.orchestrator import run_senior_debt_model

    model = build_senior_debt_model_input_from_project_inputs(
        project or _project(),
        source_id=source_id,
        debt_sizing_case=bank_case,
    )
    if not with_shl:
        model = dataclasses.replace(model, shareholder_loan=None)
    return run_senior_debt_model(model)


def _reconciliation(result=None):
    from financial_engine.diagnostics.base_performance_reconciliation import (
        build_base_performance_reconciliation,
    )

    return build_base_performance_reconciliation(result or _run_project(), _source())


def _row(rec, period, line):
    return next(
        row for row in rec["rows"]
        if row["period"] == period and row["line"] == line
    )


def _operating_value(result, vector_name, period_index):
    position = result.operating_schedules.period_indices.index(period_index)
    return getattr(result.operating_schedules, vector_name)[position]


def test_oborovo_base_ds1_reports_bank_sizing_debt_authority_boundary():
    result = _run_project()
    source = _source()
    rec = _reconciliation(result)

    assert _row(rec, 1, "Production")["delta"] == pytest.approx(0.0, abs=1e-9)
    assert _row(rec, 1, "Revenue")["delta"] == pytest.approx(0.0, abs=1e-9)
    assert _row(rec, 1, "OPEX")["delta"] == pytest.approx(0.0, abs=1e-9)
    assert _row(rec, 1, "EBITDA")["delta"] == pytest.approx(0.0, abs=1e-9)
    assert _row(rec, 1, "Base CFADS")["finco"] == pytest.approx(
        source["cf"]["fcf_for_banks_keur"][1]
    )
    assert _row(rec, 1, "Senior Interest")["finco"] == pytest.approx(
        1303.484026996744
    )
    assert _row(rec, 1, "Senior Interest")["excel"] == pytest.approx(
        source["ds"]["sd_gross_interest_keur"][1]
    )
    assert _row(rec, 1, "Senior Principal")["finco"] == pytest.approx(
        935.6493858576118
    )
    assert _row(rec, 1, "Senior Principal")["excel"] == pytest.approx(
        source["ds"]["sd_principal_keur"][1]
    )
    assert _row(rec, 1, "Senior Debt Service")["finco"] == pytest.approx(
        source["ds"]["sd_service_keur"][1]
    )
    assert _row(rec, 1, "Senior Debt Service")["excel"] == pytest.approx(
        source["ds"]["sd_service_keur"][1]
    )
    assert _row(rec, 1, "Post-Senior Cash")["finco"] == pytest.approx(
        source["cf"]["free_cash_flow_for_shl_keur"][1]
    )
    assert _row(rec, 1, "Post-Senior Cash")["excel"] == pytest.approx(
        source["cf"]["fcf_for_banks_keur"][1]
        + source["cf"]["senior_debt_service_keur"][1]
    )
    assert _row(rec, 1, "Cash Available for SHL")["finco"] == pytest.approx(
        source["cf"]["free_cash_flow_for_shl_keur"][1]
    )
    assert result.post_senior_cash.cash_after_senior_before_reserves_keur[1] == pytest.approx(
        result.tax_and_cfads.cfads_keur[1]
        - result.senior_debt.senior_debt_service_keur[0]
    )
    assert result.senior_debt.debt_size_keur == pytest.approx(42_852.30326225287)
    assert result.senior_debt.binding_constraint == "DSCR"
    assert result.senior_debt.diagnostics["initial_debt_guess_keur"] == pytest.approx(
        42_852.26672602787
    )
    assert result.senior_debt.diagnostics["final_debt_size_keur"] == pytest.approx(
        result.senior_debt.debt_size_keur
    )


def test_operating_calendar_source_denominator_and_terminal_horizon_are_wired():
    result = _run_project()
    by_idx = {p.period_index: p for p in result.periods}

    assert by_idx[26].period_end.isoformat() == "2043-06-30"
    assert by_idx[26].days_in_period == 181
    assert by_idx[26].day_fraction == pytest.approx(181 / 365)

    assert by_idx[27].period_end.isoformat() == "2043-12-31"
    assert by_idx[27].days_in_period == 184
    assert by_idx[27].day_fraction == pytest.approx(184 / 366)

    assert by_idx[28].period_end.isoformat() == "2044-06-30"
    assert by_idx[28].days_in_period == 182
    assert by_idx[28].day_fraction == pytest.approx(182 / 366)

    assert by_idx[60].period_end.isoformat() == "2060-06-30"
    assert by_idx[60].day_fraction == pytest.approx(182 / 366)


def test_period_axis_convention_is_explicit_and_not_global():
    from app.project_factories import (
        create_default_oborovo,
        create_default_solar_project,
        create_default_tuho_wind1,
        create_default_wind_project,
    )
    from financial_engine.adapters.project_inputs import from_project_inputs
    from financial_engine.orchestrator import run_operating_model
    from finco_core.inputs import PeriodAxisConvention, project_inputs_from_dict, project_inputs_to_dict

    oborovo = create_default_oborovo()
    assert oborovo.info.period_axis_convention == (
        PeriodAxisConvention.OPERATING_BOUNDARY_SINGLE_CONSTRUCTION_COLUMN
    )
    restored = project_inputs_from_dict(project_inputs_to_dict(oborovo))
    assert restored.info.period_axis_convention == oborovo.info.period_axis_convention

    oborovo_result = run_operating_model(from_project_inputs(oborovo))
    assert sum(1 for p in oborovo_result.periods if p.is_construction) == 1
    assert oborovo_result.periods[1].period_start.isoformat() == "2030-06-30"

    for factory in (
        create_default_solar_project,
        create_default_wind_project,
        create_default_tuho_wind1,
    ):
        project = factory()
        assert project.info.period_axis_convention == (
            PeriodAxisConvention.COD_ANCHOR_TWO_CONSTRUCTION_COLUMNS
        )
        result = run_operating_model(from_project_inputs(project))
        assert sum(1 for p in result.periods if p.is_construction) == 2


def test_base_performance_reconciliation_closes_to_tax_boundary():
    rec = _reconciliation()

    for line in ("Production", "Price", "Revenue", "OPEX", "EBITDA"):
        assert abs(rec["max_by_line"][line]["delta"]) < 1e-8

    assert _row(rec, 1, "Senior Debt Service")["delta"] == pytest.approx(0.0)
    assert _row(rec, 1, "Cash Available for SHL")["delta"] == pytest.approx(0.0)
    assert _row(rec, 4, "Senior Debt Service")["delta"] == pytest.approx(0.0, abs=1e-9)
    assert _row(rec, 4, "Cash Available for SHL")["delta"] == pytest.approx(0.0, abs=1e-9)

    first_material = next(row for row in rec["rows"] if abs(row["delta"]) > 0.1)
    assert first_material["period"] == 1
    assert first_material["line"] == "Taxable Income"
    assert rec["max_by_line"]["Cash Tax"]["period"] == 59
    assert rec["max_by_line"]["Cash Tax"]["delta"] == pytest.approx(706.5567709778473)


def test_base_mutations_are_causal_and_source_labels_are_non_financial():
    project = _project()
    base = _run_project(project, source_id="label-a")
    label_b = _run_project(project, source_id="label-b")
    assert base.post_senior_cash.cash_available_for_shl_before_reserves_keur == pytest.approx(
        label_b.post_senior_cash.cash_available_for_shl_before_reserves_keur
    )
    assert base.senior_debt.senior_debt_service_keur == pytest.approx(
        label_b.senior_debt.senior_debt_service_keur
    )

    hours_project = dataclasses.replace(
        project,
        technical=dataclasses.replace(
            project.technical,
            operating_hours_p50=project.technical.operating_hours_p50 + 10.0,
        ),
    )
    hours = _run_project(hours_project)
    assert _operating_value(hours, "production_mwh", 1) > _operating_value(
        base, "production_mwh", 1
    )
    assert _operating_value(hours, "revenue_keur", 1) > _operating_value(
        base, "revenue_keur", 1
    )
    assert hours.tax_and_cfads.cfads_keur[1] > base.tax_and_cfads.cfads_keur[1]

    price_project = dataclasses.replace(
        project,
        revenue=dataclasses.replace(
            project.revenue,
            ppa_base_tariff=project.revenue.ppa_base_tariff + 1.0,
        ),
    )
    priced = _run_project(price_project)
    assert _operating_value(priced, "production_mwh", 1) == pytest.approx(
        _operating_value(base, "production_mwh", 1)
    )
    assert _operating_value(priced, "revenue_keur", 1) > _operating_value(
        base, "revenue_keur", 1
    )
    assert priced.tax_and_cfads.cfads_keur[1] > base.tax_and_cfads.cfads_keur[1]

    hcap = project.hierarchical_opex_capability
    categories = list(hcap.opex_model.categories)
    first_category = categories[0]
    subitems = list(first_category.subitems)
    subitems[0] = dataclasses.replace(
        subitems[0],
        base_amount_keur=subitems[0].base_amount_keur + 10.0,
    )
    categories[0] = dataclasses.replace(first_category, subitems=tuple(subitems))
    opex_project = dataclasses.replace(
        project,
        hierarchical_opex_capability=dataclasses.replace(
            hcap,
            opex_model=dataclasses.replace(hcap.opex_model, categories=tuple(categories)),
        ),
    )
    opex = _run_project(opex_project)
    assert _operating_value(opex, "ebitda_keur", 1) < _operating_value(
        base, "ebitda_keur", 1
    )
    assert opex.tax_and_cfads.cfads_keur[1] < base.tax_and_cfads.cfads_keur[1]


def test_bank_sizing_case_does_not_directly_mutate_base_post_senior_cash():
    from financial_engine.inputs import DebtSizingCaseInput, YieldScenario

    p50 = _run_project(
        bank_case=DebtSizingCaseInput(
            production_yield_scenario=YieldScenario.P50,
            source_label="p50-bank-audit-only",
        ),
        with_shl=False,
    )
    p90 = _run_project(
        bank_case=DebtSizingCaseInput(
            production_yield_scenario=YieldScenario.P90_10Y,
            source_label="p90-bank-audit-only",
        ),
        with_shl=False,
    )

    assert p50.debt_sizing.bank_cfads_keur != p90.debt_sizing.bank_cfads_keur
    assert p50.operating_schedules.production_mwh == pytest.approx(
        p90.operating_schedules.production_mwh
    )
    assert p50.operating_schedules.revenue_keur == pytest.approx(
        p90.operating_schedules.revenue_keur
    )
    assert p50.senior_debt.debt_size_keur != pytest.approx(p90.senior_debt.debt_size_keur)
    assert p50.post_senior_cash.cash_available_for_shl_before_reserves_keur != pytest.approx(
        p90.post_senior_cash.cash_available_for_shl_before_reserves_keur
    )


def test_no_identity_dispatch_or_source_replay_markers_in_b6_runtime_files():
    runtime_files = [
        Path("finco_core/engine/period_engine.py"),
        Path("financial_engine/orchestrator.py"),
        Path("financial_engine/senior_debt/project_adapter.py"),
        Path("financial_engine/senior_debt/solver.py"),
        Path("financial_engine/shl/production.py"),
    ]
    forbidden = (
        "create_default_oborovo",
        "create_default_tuho",
        "project.code",
        "project.name",
        "baseline_id",
        "approved_delta",
        "expected_delta",
        "balancing plug",
        "target fitting",
        "source-vector runtime input",
    )
    for path in runtime_files:
        text = path.read_text()
        lower = text.lower()
        for marker in forbidden:
            assert marker not in lower
