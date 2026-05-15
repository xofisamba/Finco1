"""Phase 7F C1d tests for audit-only TUHO R99/R102 fields."""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.inputs import SHLRepaymentMethod
from domain.waterfall.waterfall_engine import WaterfallPeriod


EXCEL_TUHO_R99_TOTAL_KEUR = 234_745.0
SELECTED_PERIODS = (0, 10, 20, 24, 28, 34, 36)


def _run_project(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(inputs=project, engine=engine).run(config)


def _excel_tuho_r99_by_op_idx() -> list[float]:
    fixture_path = Path(__file__).parent / "fixtures" / "excel_tuho_full_model_extract.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    columns = payload["period_diagnostic_columns"]
    r99_idx = columns.index("CF.free_cash_flow_for_distribution_keur")
    return [row[r99_idx] for row in payload["period_diagnostics"]]


def test_c1d_audit_fields_do_not_change_tuho_outputs():
    result = _run_project(create_default_tuho_wind1())
    last = result.periods[-1]

    assert result.total_revenue_keur == pytest.approx(420_584.525622329, abs=0.01)
    assert result.total_senior_ds_keur == pytest.approx(65_645.10809715264, abs=0.01)
    assert result.total_shl_service_keur == pytest.approx(74_521.89532152163, abs=0.01)
    assert result.total_distribution_keur == pytest.approx(174_948.3831667074, abs=0.01)
    assert last.senior_balance_keur == pytest.approx(0.0, abs=0.01)
    assert last.shl_balance_keur == pytest.approx(0.0, abs=0.01)


def test_c1d_audit_fields_do_not_change_oborovo_outputs():
    result = _run_project(create_default_oborovo())
    last = result.periods[-1]

    assert result.total_revenue_keur == pytest.approx(238_734.87159740398, abs=0.01)
    assert result.total_senior_ds_keur == pytest.approx(63_500.89456294802, abs=0.01)
    assert result.total_shl_service_keur == pytest.approx(31_791.83020273973, abs=0.01)
    assert result.total_distribution_keur == pytest.approx(104_699.4270353312, abs=0.01)
    assert last.senior_balance_keur == pytest.approx(0.0, abs=0.01)
    assert last.shl_balance_keur == pytest.approx(0.0, abs=0.01)


def test_corporate_tax_cash_field_is_explicitly_defined():
    field_map = {field.name: field for field in fields(WaterfallPeriod)}

    assert "corporate_tax_cash_keur" in field_map
    tax_field = field_map["corporate_tax_cash_keur"]
    assert tax_field.metadata["sign"] == "positive cash tax paid in the period"
    assert "H2-only cash-tax timing" in tax_field.metadata["basis"]

    result = _run_project(create_default_tuho_wind1())
    for period in result.periods:
        expected_cash_tax = period.tax_keur if period.period_in_year == 2 else 0.0
        assert period.corporate_tax_cash_keur == pytest.approx(expected_cash_tax)


def test_r69_audit_reconstructs_from_components():
    result = _run_project(create_default_tuho_wind1())

    for period in result.periods:
        expected_r69 = (
            period.revenue_keur
            - period.opex_keur
            + 0.0
            + 0.0
            - period.corporate_tax_cash_keur
        )
        assert period.r69_fcf_banks_keur == pytest.approx(expected_r69)


def test_r84_r98_r99_r102_audit_chain():
    result = _run_project(create_default_tuho_wind1())
    previous_r100 = 0.0

    for period in result.periods:
        dsra_release_or_funding = -period.dsra_contribution_keur
        expected_r84 = period.r69_fcf_banks_keur - period.senior_ds_keur + dsra_release_or_funding
        expected_r98 = expected_r84 + previous_r100

        assert period.r84_fcf_junior_keur == pytest.approx(expected_r84)
        assert period.r98_distribution_account_keur == pytest.approx(expected_r98)
        assert period.r102_fcf_for_shl_keur == pytest.approx(period.r99_fcf_for_distribution_keur)
        assert period.fcf_for_shl_keur == pytest.approx(max(0.0, period.r102_fcf_for_shl_keur))

        previous_r100 = period.r100_carryforward_keur


@pytest.mark.xfail(
    reason="C1d diagnostic: audit fields expose current R99 gap; runtime opt-in remains blocked",
    strict=False,
)
def test_r99_audit_against_excel_is_diagnostic():
    result = _run_project(create_default_tuho_wind1())
    excel_r99 = _excel_tuho_r99_by_op_idx()
    actual = [period.r99_fcf_for_distribution_keur for period in result.periods[: len(excel_r99)]]

    total_delta = sum(actual) - EXCEL_TUHO_R99_TOTAL_KEUR
    print(
        f"C1d R99 audit total={sum(actual):.1f}, "
        f"Excel={EXCEL_TUHO_R99_TOTAL_KEUR:.1f}, delta={total_delta:.1f}"
    )

    for op_idx in SELECTED_PERIODS:
        delta = actual[op_idx] - excel_r99[op_idx]
        print(
            f"op_idx={op_idx}: audit={actual[op_idx]:.1f}, "
            f"excel={excel_r99[op_idx]:.1f}, delta={delta:.1f}"
        )

    pik_delta = sum(actual[:25]) - sum(excel_r99[:25])
    sweep_delta = sum(actual[25:34]) - sum(excel_r99[25:34])
    print(f"PIK phase delta={pik_delta:.1f}, sweep phase delta={sweep_delta:.1f}")

    assert abs(total_delta) <= EXCEL_TUHO_R99_TOTAL_KEUR * 0.01
    for op_idx in SELECTED_PERIODS:
        assert abs(actual[op_idx] - excel_r99[op_idx]) <= 100.0
    assert abs(pik_delta) <= 1_000.0
    assert abs(sweep_delta) <= 1_000.0


def test_c1d_keeps_runtime_opt_in_disabled_and_no_fcf_waterfall():
    tuho = create_default_tuho_wind1()
    oborovo = create_default_oborovo()

    assert tuho.financing.use_tuho_r99_input_engine is False
    assert oborovo.financing.use_tuho_r99_input_engine is False
    assert "fcf_waterfall" not in {method.value for method in SHLRepaymentMethod}
