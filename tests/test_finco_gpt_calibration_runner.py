"""Tests for the FincoGPT headless calibration runner."""
from __future__ import annotations

import pytest

from app.calibration import available_project_keys, debt_rate_schedule_from_engine
from app.calibration_runner import (
    CalibrationRunSpec,
    build_period_engine,
    build_run_config,
    load_project_inputs,
    run_calibration,
)


def test_available_project_keys_include_oborovo_and_tuho() -> None:
    keys = available_project_keys()
    assert "oborovo" in keys
    assert "tuho" in keys


def test_load_project_inputs_oborovo() -> None:
    inputs = load_project_inputs("oborovo")
    assert inputs.info.name
    assert inputs.capex.total_capex > 0


def test_load_project_inputs_tuho() -> None:
    inputs = load_project_inputs("tuho")
    assert inputs.info.name.lower().startswith("tuh")
    assert inputs.capex.total_capex > 70_000
    assert inputs.financing.fixed_debt_keur is not None


def test_build_period_engine_from_oborovo_inputs() -> None:
    inputs = load_project_inputs("oborovo")
    engine = build_period_engine(inputs)
    periods = engine.periods()
    assert periods
    assert any(p.is_operation for p in periods)


def test_build_period_engine_from_tuho_inputs() -> None:
    inputs = load_project_inputs("tuho")
    engine = build_period_engine(inputs)
    periods = engine.periods()
    assert periods
    assert any(p.is_operation for p in periods)


def test_build_run_config_from_oborovo_inputs() -> None:
    inputs = load_project_inputs("oborovo")
    engine = build_period_engine(inputs)
    config = build_run_config(inputs, engine)
    assert config.rate_per_period > 0
    assert config.tenor_periods == inputs.financing.senior_tenor_years * 2
    assert config.sculpt_capex_keur == inputs.capex.sculpt_capex_keur
    assert config.rate_schedule is not None
    assert len(config.rate_schedule) == config.tenor_periods
    assert config.shl_rate == inputs.financing.shl_rate


def test_build_run_config_without_engine_keeps_legacy_flat_rate_path() -> None:
    inputs = load_project_inputs("oborovo")
    config = build_run_config(inputs)
    assert config.rate_per_period > 0
    assert config.rate_schedule is None
    assert config.shl_rate == inputs.financing.shl_rate


def test_day_count_debt_rate_schedule_uses_operation_day_fractions() -> None:
    inputs = load_project_inputs("oborovo")
    engine = build_period_engine(inputs)
    config = build_run_config(inputs, engine)
    first_op = engine.operation_periods()[0]

    assert config.rate_schedule is not None
    assert abs(config.rate_schedule[0] - inputs.financing.all_in_rate * first_op.day_fraction) < 1e-12
    assert config.rate_schedule[0] != inputs.financing.all_in_rate / 2


def test_build_run_config_from_tuho_inputs() -> None:
    inputs = load_project_inputs("tuho")
    engine = build_period_engine(inputs)
    config = build_run_config(inputs, engine)
    assert config.rate_per_period > 0
    assert config.fixed_debt_keur == inputs.financing.fixed_debt_keur
    assert config.debt_sizing_method == "fixed"
    assert config.equity_irr_method == "shl_plus_dividends"
    assert config.rate_schedule is not None


def test_calibration_run_spec_defaults() -> None:
    spec = CalibrationRunSpec(project_key="oborovo")
    assert spec.engine_version == "FincoGPT"
    assert spec.calibration_source == "headless"


def test_run_calibration_oborovo_payload_shape() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="oborovo", calibration_source="pytest"))
    assert payload["project_key"] == "oborovo"
    assert payload["calibration_source"] == "pytest"
    assert payload["periods"]
    assert payload["kpis"]["senior_debt_keur"] > 0
    assert payload["revenue_decomposition"]
    assert payload["debt_decomposition"]
    assert payload["shl_decomposition"]
    assert payload["excel_full_model_shl"]["rows"]
    assert payload["sponsor_equity_shl_cash_flows"]
    assert payload["excel_full_model_sponsor_equity_shl_cash_flows"]["rows"]
    assert "sponsor_equity_shl_irr" in payload["kpis"]
    assert "excel_full_model_sponsor_equity_shl_irr" in payload["kpis"]
    assert payload["excel_full_model_project_irr"]["rows"]
    assert "excel_full_model_project_irr" in payload["kpis"]
    assert "excel_full_model_unlevered_project_irr" in payload["kpis"]


def test_run_calibration_excel_full_model_project_irr_payload_shape() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="tuho", calibration_source="pytest"))
    excel_full = payload["excel_full_model_project_irr"]

    assert excel_full["source"] == "excel_full_model_extract"
    assert excel_full["columns"] == [
        "date",
        "project_irr_cf",
        "unlevered_project_irr_cf",
        "fcf_for_banks",
    ]
    assert len(excel_full["rows"]) == 61
    assert excel_full["computed_project_irr"] == pytest.approx(excel_full["excel_project_irr"], abs=1e-8)
    assert excel_full["computed_unlevered_project_irr"] == pytest.approx(
        excel_full["excel_unlevered_project_irr"],
        abs=1e-8,
    )
    assert payload["kpis"]["excel_full_model_project_irr"] == pytest.approx(
        excel_full["computed_project_irr"],
        abs=1e-8,
    )
    assert payload["kpis"]["excel_full_model_unlevered_project_irr"] == pytest.approx(
        excel_full["computed_unlevered_project_irr"],
        abs=1e-8,
    )
    assert payload["project_cash_flows"]["source"] == "full_model_extract_bridge"
    assert payload["project_cash_flows"]["rows"] == excel_full["rows"]


def test_run_calibration_excel_full_model_shl_payload_shape() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="tuho", calibration_source="pytest"))
    excel_full = payload["excel_full_model_shl"]

    assert excel_full["source"] == "excel_full_model_extract"
    assert excel_full["columns"] == [
        "date",
        "opening",
        "closing",
        "gross_interest",
        "principal_flow",
        "paid_net_interest",
        "capitalized_interest",
        "net_dividend",
    ]
    assert len(excel_full["rows"]) == 61
    assert excel_full["first_draw_date"] == "2029-12-31"
    assert excel_full["first_principal_repayment_date"] == "2042-06-30"
    assert excel_full["first_dividend_date"] == "2047-12-31"
    assert excel_full["final_closing_balance"] == 0.0
    assert payload["shl_lifecycle_decomposition"]["source"] == "full_model_extract_bridge"
    assert len(payload["shl_lifecycle_decomposition"]["rows"]) == 61
    assert payload["shl_lifecycle_decomposition"]["rows"][0]["principal_draw_keur"] > 0


def test_run_calibration_excel_full_model_sponsor_equity_shl_payload_shape() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="tuho", calibration_source="pytest"))
    excel_full = payload["excel_full_model_sponsor_equity_shl_cash_flows"]

    assert excel_full["source"] == "excel_full_model_extract"
    assert excel_full["definition"] == (
        "shl_principal_flow_keur + paid_net_interest_keur + net_dividend_keur"
    )
    assert len(excel_full["rows"]) == 61
    assert excel_full["rows"][0]["cash_flow_keur"] < 0
    assert excel_full["computed_sponsor_equity_shl_irr"] == pytest.approx(
        payload["kpis"]["excel_full_model_sponsor_equity_shl_irr"],
        abs=1e-8,
    )
    assert payload["sponsor_equity_shl_cash_flows_full_model"]["rows"] == excel_full["rows"]
    assert payload["sponsor_equity_shl_cash_flows_financial_close"]["rows"][0]["date"] == "2028-06-30"


def test_run_calibration_payload_is_operation_only_for_period_rows() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="oborovo", calibration_source="pytest"))
    assert payload["periods"]
    assert all(row["is_operation"] for row in payload["periods"])
    assert payload["periods"][0]["date"] == "2030-12-31"


def test_run_calibration_revenue_decomposition_shape() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="oborovo", calibration_source="pytest"))
    row = next(r for r in payload["revenue_decomposition"] if r["is_operation"])
    assert row["date"]
    assert row["generation_mwh"] > 0
    assert row["ppa_tariff_eur_mwh"] > 0
    assert row["market_price_eur_mwh"] > 0
    assert "energy_revenue_keur" in row
    assert "balancing_cost_pv_keur" in row
    assert "balancing_cost_wind_keur" in row
    assert "co2_revenue_keur" in row
    assert row["revenue_keur"] == (
        row["energy_revenue_keur"]
        - row["balancing_cost_pv_keur"]
        - row["balancing_cost_wind_keur"]
        + row["co2_revenue_keur"]
    )


def test_run_calibration_debt_decomposition_shape() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="oborovo", calibration_source="pytest"))
    row = payload["debt_decomposition"][0]
    assert row["date"]
    assert row["opening_balance_keur"] >= row["closing_balance_keur"]
    assert row["senior_ds_keur"] == row["senior_interest_keur"] + row["senior_principal_keur"]
    assert row["implied_period_rate"] >= 0
    assert "dscr" in row


def test_run_calibration_shl_decomposition_shape() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="oborovo", calibration_source="pytest"))
    row = payload["shl_decomposition"][0]
    assert row["date"]
    assert row["opening_balance_keur"] >= 0
    assert row["gross_interest_keur"] >= row["cash_interest_paid_keur"]
    assert row["cash_interest_paid_keur"] >= 0
    assert row["principal_paid_keur"] >= 0
    assert row["service_paid_keur"] == row["cash_interest_paid_keur"] + row["principal_paid_keur"]
    assert row["pik_or_capitalized_interest_keur"] >= 0
    assert "cash_available_after_senior_ds_keur" in row


def test_run_calibration_sponsor_equity_shl_cash_flow_definition() -> None:
    inputs = load_project_inputs("oborovo")
    payload = run_calibration(CalibrationRunSpec(project_key="oborovo", calibration_source="pytest"))
    definition = payload["investor_cash_flow_definition"]
    first_cf = payload["sponsor_equity_shl_cash_flows"][0]
    first_period_cf = payload["sponsor_equity_shl_cash_flows"][1]
    first_period = payload["periods"][0]

    expected_initial = (
        inputs.financing.share_capital_keur
        + inputs.financing.shl_amount_keur
        + getattr(inputs.financing, "shl_idc_keur", 0.0)
    )
    assert definition["method"] == "sponsor_equity_plus_shl"
    assert definition["initial_investment_keur"] == expected_initial
    assert first_cf["date"] == inputs.info.financial_close.isoformat()
    assert first_cf["cash_flow_keur"] == -expected_initial
    assert first_period_cf["cash_flow_keur"] == (
        first_period["distribution_keur"]
        + first_period["shl_interest_keur"]
        + first_period["shl_principal_keur"]
    )
    assert first_period_cf["cash_flow_keur"] >= first_period_cf["shl_interest_keur"]


def test_run_calibration_sponsor_cash_flow_excludes_unpaid_pik_until_paid() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="oborovo", calibration_source="pytest"))
    for cf_row, period_row in zip(payload["sponsor_equity_shl_cash_flows"][1:], payload["periods"]):
        assert cf_row["cash_flow_keur"] == (
            period_row["distribution_keur"]
            + period_row["shl_interest_keur"]
            + period_row["shl_principal_keur"]
        )
        assert cf_row["cash_flow_keur"] == (
            cf_row["distribution_keur"]
            + cf_row["shl_interest_keur"]
            + cf_row["shl_principal_keur"]
        )


def test_run_calibration_applies_oborovo_first12_debt_split_anchors() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="oborovo", calibration_source="pytest"))
    first = payload["debt_decomposition"][0]
    twelfth = payload["debt_decomposition"][11]

    assert first["date"] == "2030-12-31"
    assert abs(first["senior_principal_keur"] - 935.6501310907029) < 1e-9
    assert abs(first["senior_interest_keur"] - 1303.483281763653) < 1e-9
    assert twelfth["date"] == "2036-06-30"
    assert abs(twelfth["senior_principal_keur"] - 1482.7286430265804) < 1e-9
    assert abs(twelfth["senior_interest_keur"] - 873.148013189113) < 1e-9


def test_run_calibration_applies_oborovo_first12_pl_tax_anchors() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="oborovo", calibration_source="pytest"))
    first = payload["periods"][0]
    twelfth = payload["periods"][11]

    assert first["date"] == "2030-12-31"
    assert abs(first["depreciation_keur"] - 1490.6768666010357) < 1e-9
    assert abs(first["taxable_profit_keur"] - (-219.15672358217944)) < 1e-9
    assert abs(first["tax_keur"] - 0.0) < 1e-9
    assert twelfth["date"] == "2036-06-30"
    assert abs(twelfth["depreciation_keur"] - 1470.445240085335) < 1e-9
    assert abs(twelfth["taxable_profit_keur"] - 443.8849122184448) < 1e-9
    assert abs(twelfth["tax_keur"] - 78.21556839713568) < 1e-9


def test_run_calibration_applies_oborovo_first12_shl_cash_flow_anchors() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="oborovo", calibration_source="pytest"))
    first = payload["periods"][0]
    twelfth = payload["periods"][11]
    first_shl = payload["shl_decomposition"][0]
    twelfth_shl = payload["shl_decomposition"][11]

    assert first["date"] == "2030-12-31"
    assert abs(first["shl_interest_keur"] - 335.8700119281534) < 1e-9
    assert abs(first["shl_principal_keur"] - 0.0) < 1e-9
    assert abs(first["distribution_keur"] - 0.0) < 1e-9
    assert abs(first_shl["gross_interest_keur"] - 636.8088084115645) < 1e-9
    assert abs(first_shl["pik_or_capitalized_interest_keur"] - (636.8088084115645 - 335.8700119281534)) < 1e-9

    assert twelfth["date"] == "2036-06-30"
    assert abs(twelfth["shl_interest_keur"] - 353.3859408800636) < 1e-9
    assert abs(twelfth["shl_principal_keur"] - 0.0) < 1e-9
    assert abs(twelfth["distribution_keur"] - 0.0) < 1e-9
    assert abs(twelfth_shl["gross_interest_keur"] - 785.1684339414179) < 1e-9
    assert abs(twelfth_shl["pik_or_capitalized_interest_keur"] - (785.1684339414179 - 353.3859408800636)) < 1e-9
