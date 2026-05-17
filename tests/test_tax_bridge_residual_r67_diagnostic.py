"""Diagnostic bridge for the remaining TUHO R67 residual."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from app.project_factories import create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner


EXCEL_R67_TOTAL_KEUR = -38_240.920880415375
PYTHON_FLAG_ON_R67_TOTAL_KEUR = -36_091.61517762715
R67_RESIDUAL_KEUR = 2_149.3057027882255
EARLY_TAX_PERIOD_DELTA_KEUR = -2_181.578223654879
MID_PERIOD_DELTA_KEUR = 3_381.6663126695603
FINAL_PERIOD_DELTA_KEUR = 949.2176137735478
MATERIAL_PERIOD_COUNT = 18


def _run(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _tuho_flag_on_result():
    project = create_default_tuho_wind1()
    project = replace(project, info=replace(project.info, use_tax_bridge_engine=True))
    return _run(project)


def _excel_r67_by_period():
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "excel_tuho_full_model_extract.json").read_text(
            encoding="utf-8"
        )
    )
    columns = payload["period_diagnostic_columns"]
    idx = columns.index("P&L.corporate_income_tax_keur")
    return tuple(-row[idx] for row in payload["period_diagnostics"][:60])


def _residual_bridge_rows():
    result = _tuho_flag_on_result()
    excel_r67 = _excel_r67_by_period()
    rows = []
    for op_idx, (period, excel_value) in enumerate(zip(result.periods[:60], excel_r67)):
        python_r67 = -period.corporate_tax_cash_keur
        rows.append(
            {
                "op_idx": op_idx,
                "date": period.date,
                "excel_r67_keur": excel_value,
                "python_r67_keur": python_r67,
                "delta_keur": python_r67 - excel_value,
                "taxable_income_before_losses_keur": (
                    period.taxable_income_before_losses_audit_keur
                ),
                "r34_keur": period.fiscal_reintegration_audit_keur,
                "losses_used_keur": period.tax_loss_used_audit_keur,
                "taxable_profit_keur": period.taxable_profit_after_losses_audit_keur,
                "cit_keur": period.cit_accrual_audit_keur,
                "cash_tax_timing": "annual_h2_pairing" if period.period_in_year == 2 else "h1_zero",
            }
        )
    return tuple(rows)


def test_r67_residual_bridge_generates_all_periods_without_runtime_change():
    baseline = _run(create_default_tuho_wind1())
    diagnostic = _run(create_default_tuho_wind1())
    rows = _residual_bridge_rows()

    assert len(rows) == 60
    assert diagnostic.total_revenue_keur == pytest.approx(baseline.total_revenue_keur, abs=0.0001)
    assert diagnostic.total_opex_keur == pytest.approx(baseline.total_opex_keur, abs=0.0001)
    assert diagnostic.total_tax_keur == pytest.approx(baseline.total_tax_keur, abs=0.0001)
    assert diagnostic.total_senior_ds_keur == pytest.approx(
        baseline.total_senior_ds_keur,
        abs=0.0001,
    )


def test_r67_totals_and_residual_are_captured():
    rows = _residual_bridge_rows()

    assert sum(row["excel_r67_keur"] for row in rows) == pytest.approx(
        EXCEL_R67_TOTAL_KEUR,
        abs=0.01,
    )
    assert sum(row["python_r67_keur"] for row in rows) == pytest.approx(
        PYTHON_FLAG_ON_R67_TOTAL_KEUR,
        abs=0.01,
    )
    assert sum(row["delta_keur"] for row in rows) == pytest.approx(R67_RESIDUAL_KEUR, abs=0.01)


def test_period_bridge_contains_tax_basis_and_cash_timing_fields():
    rows = _residual_bridge_rows()
    row_25 = rows[25]
    row_57 = rows[57]

    assert row_25["excel_r67_keur"] == pytest.approx(-120.18903737619021, abs=0.01)
    assert row_25["python_r67_keur"] == pytest.approx(-945.8349815578507, abs=0.01)
    assert row_25["cash_tax_timing"] == "annual_h2_pairing"
    assert row_25["losses_used_keur"] == pytest.approx(0.0, abs=0.0001)
    assert row_25["taxable_profit_keur"] > 0.0

    assert row_57["excel_r67_keur"] == pytest.approx(-2_984.233759025831, abs=0.01)
    assert row_57["python_r67_keur"] == pytest.approx(-2_513.7394174893116, abs=0.01)
    assert row_57["delta_keur"] == pytest.approx(470.49434153651964, abs=0.01)


def test_residual_is_mixed_tax_basis_not_r99_source_acceptance():
    rows = _residual_bridge_rows()

    early_delta = sum(row["delta_keur"] for row in rows[24:38])
    mid_delta = sum(row["delta_keur"] for row in rows[38:57])
    final_delta = sum(row["delta_keur"] for row in rows[57:60])
    material_periods = sum(1 for row in rows if abs(row["delta_keur"]) > 100.0)

    assert early_delta == pytest.approx(EARLY_TAX_PERIOD_DELTA_KEUR, abs=0.01)
    assert mid_delta == pytest.approx(MID_PERIOD_DELTA_KEUR, abs=0.01)
    assert final_delta == pytest.approx(FINAL_PERIOD_DELTA_KEUR, abs=0.01)
    assert material_periods == MATERIAL_PERIOD_COUNT

    # The residual is not monotonic: some periods overpay and others underpay
    # relative to Excel, so a simple scalar R99 or cash-tax plug is not justified.
    assert any(row["delta_keur"] < -100.0 for row in rows)
    assert any(row["delta_keur"] > 100.0 for row in rows)


def test_no_runtime_source_or_shl_factory_opt_in_is_accepted():
    project = create_default_tuho_wind1()

    assert project.info.use_tax_bridge_engine is False
    assert project.info.use_shl_fcf_waterfall_engine is False
    assert project.financing.use_tuho_r99_input_engine is False
    assert project.financing.shl_fcf_waterfall_cash_schedule_keur == ()
