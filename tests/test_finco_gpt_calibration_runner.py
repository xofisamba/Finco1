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
    assert payload["raw_engine_debt_decomposition_before_split_anchors"]["rows"]
    assert payload["raw_engine_debt_gap_before_split_anchors"]["compared_rows"] > 0
    assert payload["raw_engine_pl_tax_rows_before_pl_tax_anchors"]["rows"]
    assert payload["raw_engine_pl_tax_gap_before_pl_tax_anchors"]["compared_rows"] > 0
    assert payload["raw_engine_shl_decomposition_before_cash_flow_anchors"]["rows"]
    assert payload["raw_engine_shl_lifecycle_gap_before_cash_flow_anchors"]["compared_rows"] > 0
    assert payload["engine_shl_lifecycle_gap_before_full_model_calibration"]["compared_rows"] > 0
    assert payload["engine_project_cash_flow_gap_before_full_model_calibration"]["compared_rows"] > 0
    assert payload["sponsor_equity_shl_cash_flow_gap_before_full_model_calibration"]["compared_rows"] > 0
    assert payload["engine_debt_gap_before_full_model_calibration"]["compared_rows"] > 0
    assert payload["engine_pl_tax_gap_before_full_model_calibration"]["compared_rows"] > 0
    assert payload["native_project_cash_flows_before_full_model_calibration"]["rows"]
    assert payload["native_shl_lifecycle_decomposition_before_full_model_calibration"]["rows"]
    assert payload["native_sponsor_equity_shl_cash_flows_before_full_model_calibration"]["rows"]
    assert len(payload["formula_parity_workstreams"]) == 5
    assert payload["calibration_scaffolding_inventory"]["remaining_stream_count"] == 5
    assert payload["full_horizon_period_parity"]["remaining_group_count"] == 3
    assert payload["full_model_period_diagnostics"]["source"] == "excel_full_model_extract"
    assert len(payload["full_model_period_diagnostics"]["rows"]) == 60


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


def test_run_calibration_gap_payloads_are_serialized_for_tuho() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="tuho", calibration_source="pytest"))

    raw_shl_gap = payload["raw_engine_shl_lifecycle_gap_before_cash_flow_anchors"]
    anchored_shl_gap = payload["engine_shl_lifecycle_gap_before_full_model_calibration"]
    project_cf_gap = payload["engine_project_cash_flow_gap_before_full_model_calibration"]
    sponsor_cf_gap = payload["sponsor_equity_shl_cash_flow_gap_before_full_model_calibration"]

    assert raw_shl_gap["source"] == "native_engine_before_cash_flow_anchors"
    assert raw_shl_gap["compared_rows"] == 59
    assert raw_shl_gap["first_closing_balance_mismatch"]["date"] == "2030-06-30"
    assert anchored_shl_gap["source"] == "native_engine_before_full_model_calibration"
    assert anchored_shl_gap["first_closing_balance_mismatch"] is None
    assert project_cf_gap["first_fcf_for_banks_mismatch"]["date"] == "2031-12-31"
    assert sponsor_cf_gap["first_cash_flow_mismatch"]["index"] == 0
    assert sponsor_cf_gap["first_cash_flow_mismatch"]["delta_keur"] == pytest.approx(
        -payload["investor_cash_flow_definition"]["shl_idc_keur"],
    )


def test_run_calibration_native_formula_candidate_payloads_are_serialized_for_tuho() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="tuho", calibration_source="pytest"))

    project_rows = payload["native_project_cash_flows_before_full_model_calibration"]["rows"]
    shl_rows = payload["native_shl_lifecycle_decomposition_before_full_model_calibration"]["rows"]
    sponsor_rows = payload["native_sponsor_equity_shl_cash_flows_before_full_model_calibration"]["rows"]

    assert payload["native_project_cash_flows_before_full_model_calibration"]["source"] == (
        "native_engine_before_full_model_calibration"
    )
    assert len(project_rows) == 61
    assert project_rows[0]["date"] == "2028-06-30"
    assert project_rows[0]["project_irr_cf"] < 0.0
    assert project_rows[1]["fcf_for_banks"] == pytest.approx(payload["periods"][0]["cf_after_tax_keur"])
    assert payload["native_project_cash_flows_before_full_model_calibration"]["computed_project_irr"] > 0.0

    assert payload["native_shl_lifecycle_decomposition_before_full_model_calibration"]["source"] == (
        "native_engine_before_full_model_calibration"
    )
    assert len(shl_rows) == 61
    assert shl_rows[0]["date"] == "2028-06-30"
    assert shl_rows[0]["principal_draw_keur"] == pytest.approx(
        payload["investor_cash_flow_definition"]["shl_amount_keur"]
        + payload["investor_cash_flow_definition"]["shl_idc_keur"],
    )
    assert shl_rows[1]["date"] == payload["engine_shl_decomposition_before_full_model_calibration"]["rows"][0]["date"]

    assert payload["native_sponsor_equity_shl_cash_flows_before_full_model_calibration"]["source"] == (
        "native_engine_before_full_model_calibration"
    )
    assert len(sponsor_rows) == 61
    assert sponsor_rows[0]["cash_flow_keur"] == pytest.approx(
        -payload["investor_cash_flow_definition"]["initial_investment_keur"],
    )
    assert payload["native_sponsor_equity_shl_cash_flows_before_full_model_calibration"][
        "computed_sponsor_equity_shl_irr"
    ] > 0.0


def test_run_calibration_formula_parity_workstreams_cover_next_five_items() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="tuho", calibration_source="pytest"))
    workstreams = {row["name"]: row for row in payload["formula_parity_workstreams"]}

    assert list(workstreams) == [
        "project_cash_flow",
        "shl_lifecycle",
        "sponsor_equity_shl_cash_flow",
        "debt",
        "pl_tax",
    ]
    assert workstreams["project_cash_flow"]["status"] == "bridge_active"
    assert workstreams["project_cash_flow"]["gap_payload"] == "engine_project_cash_flow_gap_before_full_model_calibration"
    assert workstreams["project_cash_flow"]["first_mismatch"]["date"] == "2031-12-31"
    assert workstreams["project_cash_flow"]["gap_snapshot"]["max_abs_gap"] == pytest.approx(2567.650754178724)
    assert workstreams["project_cash_flow"]["gap_snapshot"]["ready_to_remove"] is False
    assert workstreams["shl_lifecycle"]["native_payload"] == (
        "native_shl_lifecycle_decomposition_before_full_model_calibration"
    )
    assert workstreams["shl_lifecycle"]["first_mismatch"]["date"] == "2030-06-30"
    assert workstreams["shl_lifecycle"]["gap_snapshot"]["max_abs_gap"] == pytest.approx(101724.16528697769)
    assert workstreams["sponsor_equity_shl_cash_flow"]["first_mismatch"]["index"] == 0
    assert workstreams["debt"]["status"] == "anchors_active"
    assert workstreams["debt"]["first_mismatch"]["date"] == "2030-06-30"
    assert workstreams["debt"]["gap_snapshot"]["mismatch_count"] == 84
    assert workstreams["pl_tax"]["status"] == "anchors_active"
    assert workstreams["pl_tax"]["first_mismatch"]["metric"] == "depreciation_keur"
    assert workstreams["pl_tax"]["gap_snapshot"]["mismatch_count"] == 175


def test_run_calibration_scaffolding_inventory_tracks_remaining_bridge_and_anchor_layers() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="tuho", calibration_source="pytest"))
    inventory = payload["calibration_scaffolding_inventory"]

    assert inventory["source"] == "formula_parity_workstreams"
    assert inventory["active_bridge_streams"] == [
        "project_cash_flow",
        "shl_lifecycle",
        "sponsor_equity_shl_cash_flow",
    ]
    assert inventory["active_anchor_streams"] == ["debt", "pl_tax"]
    assert inventory["removal_ready_streams"] == []
    assert inventory["remaining_stream_count"] == 5
    assert inventory["all_scaffolding_removed"] is False


def test_run_calibration_full_horizon_period_parity_groups_are_serialized_for_tuho() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="tuho", calibration_source="pytest"))
    parity = payload["full_horizon_period_parity"]
    groups = parity["groups"]

    assert parity["source"] == "full_model_period_diagnostics"
    assert parity["remaining_group_count"] == 3
    assert set(groups) == {"operating_cf", "debt", "pl_tax"}
    assert groups["operating_cf"]["compared_rows"] == 59
    assert groups["operating_cf"]["mismatch_count"] == 224
    assert groups["operating_cf"]["first_mismatch"]["date"] == "2031-12-31"
    assert groups["operating_cf"]["first_mismatch"]["metric"] == "revenue_keur"
    assert groups["debt"]["mismatch_count"] == 75
    assert groups["debt"]["first_mismatch"]["metric"] == "senior_principal_keur"
    assert groups["pl_tax"]["mismatch_count"] == 168
    assert groups["pl_tax"]["first_mismatch"]["metric"] == "depreciation_keur"


def test_run_calibration_full_model_period_diagnostics_payload_shape() -> None:
    payload = run_calibration(CalibrationRunSpec(project_key="tuho", calibration_source="pytest"))
    diagnostics = payload["full_model_period_diagnostics"]

    assert diagnostics["source"] == "excel_full_model_extract"
    assert diagnostics["definition"] == "operating-period CF, DS, P&L and Dep rows from the full workbook extract"
    assert diagnostics["columns"][0] == "date"
    assert "CF.free_cash_flow_for_banks_keur" in diagnostics["columns"]
    assert "DS.senior_principal_keur" in diagnostics["columns"]
    assert "P&L.taxable_income_keur" in diagnostics["columns"]
    assert "Dep.depreciation_keur" in diagnostics["columns"]
    assert diagnostics["source_detail"]["sheets"] == ["CF", "DS", "P&L", "Dep"]
    assert diagnostics["source_detail"]["scope"] == "all operating periods flagged TRUE in the CF sheet"
    assert diagnostics["source_detail"]["row_mapping"]["CF"]["free_cash_flow_for_banks_keur"] == 69
    assert diagnostics["source_detail"]["row_mapping"]["DS"]["senior_principal_keur"] == 49
    assert len(diagnostics["rows"]) == 60
    assert diagnostics["rows"][0]["date"] == "2030-06-30"
    assert diagnostics["rows"][-1]["date"] == "2059-12-31"


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
