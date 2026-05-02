"""Debt schedule Excel-alignment diagnostics.

These tests isolate senior debt service, principal, interest and implied DSCR
before tax/SHL/equity return mechanics. Oborovo first12 senior debt split is
anchored to extracted Excel DS rows until full financing fee/rate mechanics are
mapped.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.calibration import run_project_calibration
from tests.reconciliation_helpers import collect_period_failures, period_by_date


FIXTURE_DIR = Path(__file__).parent / "fixtures"
OBOROVO_EXCEL_SENIOR_DEBT_KEUR = 42_852.10911500986


OBOROVO_DEBT_SERVICE_METRIC_SPECS = [
    {
        "excel_sheet": "CF",
        "excel_metric": "senior_debt_service_keur",
        "app_metric": "senior_ds_keur",
        "excel_sign": -1.0,
        "app_sign": 1.0,
        "tolerance_pct": 0.005,
    },
]

OBOROVO_DEBT_INTEREST_METRIC_SPECS = [
    {
        "excel_sheet": "DS",
        "excel_metric": "senior_net_interest_keur",
        "app_metric": "senior_interest_keur",
        "tolerance_pct": 0.005,
    },
]

OBOROVO_DEBT_PRINCIPAL_METRIC_SPECS = [
    {
        "excel_sheet": "DS",
        "excel_metric": "senior_principal_keur",
        "app_metric": "senior_principal_keur",
        "tolerance_pct": 0.005,
    },
]

OBOROVO_DEBT_SPLIT_METRIC_SPECS = [
    *OBOROVO_DEBT_PRINCIPAL_METRIC_SPECS,
    *OBOROVO_DEBT_INTEREST_METRIC_SPECS,
]


def _period_fixture(name: str) -> list[dict]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))["periods"]


def _implied_excel_debt_rows(fixture_name: str, limit: int) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    opening_balance = OBOROVO_EXCEL_SENIOR_DEBT_KEUR if fixture_name == "excel_oborovo_periods.json" else 0.0
    for period in _period_fixture(fixture_name)[:limit]:
        cfads = period["CF"]["free_cash_flow_for_banks_keur"]
        debt_service = -period["CF"]["senior_debt_service_keur"]
        principal = period["DS"]["senior_principal_keur"]
        interest = period["DS"]["senior_net_interest_keur"]
        implied_rate = interest / opening_balance if opening_balance else 0.0
        closing_balance = max(0.0, opening_balance - principal)
        rows.append({
            "period_end_date": period["period_end_date"],
            "excel_opening_balance_keur": opening_balance,
            "excel_closing_balance_keur": closing_balance,
            "excel_cfads_keur": cfads,
            "excel_senior_debt_service_keur": debt_service,
            "excel_senior_principal_keur": principal,
            "excel_senior_interest_keur": interest,
            "excel_implied_period_rate": implied_rate,
            "excel_implied_annual_simple_rate": implied_rate * 2,
            "excel_implied_dscr": cfads / debt_service if debt_service else 0.0,
            "excel_dscr_target_row": period["DS"]["senior_debt_dscr_target"],
            "excel_average_dscr_row": period["CF"]["average_senior_dscr_period"],
            "excel_minimum_dscr_row": period["CF"]["minimum_senior_dscr_period"],
        })
        opening_balance = closing_balance
    return rows


def _app_debt_rows(limit: int = 12) -> list[dict[str, float | str]]:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    rows = []
    for app_row in payload["debt_decomposition"][:limit]:
        rows.append({
            "period_end_date": app_row["date"],
            "app_opening_balance_keur": app_row["opening_balance_keur"],
            "app_closing_balance_keur": app_row["closing_balance_keur"],
            "app_senior_debt_service_keur": app_row["senior_ds_keur"],
            "app_senior_principal_keur": app_row["senior_principal_keur"],
            "app_senior_interest_keur": app_row["senior_interest_keur"],
            "app_implied_period_rate": app_row["implied_period_rate"],
            "app_implied_annual_simple_rate": app_row["implied_period_rate"] * 2,
            "app_dscr": app_row["dscr"],
        })
    return rows


def _excel_app_debt_diagnostic_rows(limit: int = 12) -> list[dict[str, float | str]]:
    excel_rows = {row["period_end_date"]: row for row in _implied_excel_debt_rows("excel_oborovo_periods.json", limit)}
    app_rows = {row["period_end_date"]: row for row in _app_debt_rows(limit)}
    diagnostics: list[dict[str, float | str]] = []
    for date_key, excel in excel_rows.items():
        app = app_rows[date_key]
        diagnostics.append({
            "period_end_date": date_key,
            "excel_opening_balance_keur": excel["excel_opening_balance_keur"],
            "app_opening_balance_keur": app["app_opening_balance_keur"],
            "opening_balance_delta_keur": app["app_opening_balance_keur"] - excel["excel_opening_balance_keur"],
            "excel_implied_period_rate": excel["excel_implied_period_rate"],
            "app_implied_period_rate": app["app_implied_period_rate"],
            "implied_period_rate_delta": app["app_implied_period_rate"] - excel["excel_implied_period_rate"],
            "excel_interest_keur": excel["excel_senior_interest_keur"],
            "app_interest_keur": app["app_senior_interest_keur"],
            "interest_delta_keur": app["app_senior_interest_keur"] - excel["excel_senior_interest_keur"],
            "excel_principal_keur": excel["excel_senior_principal_keur"],
            "app_principal_keur": app["app_senior_principal_keur"],
            "principal_delta_keur": app["app_senior_principal_keur"] - excel["excel_senior_principal_keur"],
        })
    return diagnostics


def test_oborovo_excel_debt_fixture_has_first_twelve_periods() -> None:
    rows = _implied_excel_debt_rows("excel_oborovo_periods.json", limit=12)
    assert len(rows) == 12
    for row in rows:
        assert row["excel_senior_debt_service_keur"] > 0
        assert row["excel_senior_principal_keur"] > 0
        assert row["excel_senior_interest_keur"] > 0
        assert abs(row["excel_implied_dscr"] - row["excel_dscr_target_row"]) < 1e-5


def test_oborovo_first_twelve_excel_dscr_target_is_115() -> None:
    """Current extracted Oborovo first12 Excel rows use 1.15 DSCR, not 1.20."""
    rows = _implied_excel_debt_rows("excel_oborovo_periods.json", limit=12)
    assert {round(float(row["excel_dscr_target_row"]), 6) for row in rows} == {1.15}


def test_oborovo_excel_implied_rate_diagnostics_are_available() -> None:
    rows = _implied_excel_debt_rows("excel_oborovo_periods.json", limit=12)
    assert len(rows) == 12
    assert 0.02 < rows[0]["excel_implied_period_rate"] < 0.04
    assert all(row["excel_opening_balance_keur"] > row["excel_closing_balance_keur"] for row in rows)


def test_oborovo_app_implied_rate_diagnostics_are_available() -> None:
    rows = _app_debt_rows(limit=12)
    assert len(rows) == 12
    assert all(row["app_opening_balance_keur"] >= row["app_closing_balance_keur"] for row in rows)
    assert all(row["app_implied_period_rate"] >= 0 for row in rows)


def test_oborovo_first_period_app_opening_balance_matches_excel_debt_anchor() -> None:
    diagnostics = _excel_app_debt_diagnostic_rows(limit=1)
    first = diagnostics[0]
    assert abs(first["opening_balance_delta_keur"]) / OBOROVO_EXCEL_SENIOR_DEBT_KEUR < 0.005, first


def test_oborovo_debt_gap_diagnostics_are_available() -> None:
    diagnostics = _excel_app_debt_diagnostic_rows(limit=12)
    assert len(diagnostics) == 12
    first = diagnostics[0]
    assert first["period_end_date"] == "2030-12-31"
    assert "opening_balance_delta_keur" in first
    assert "implied_period_rate_delta" in first
    assert "interest_delta_keur" in first
    assert "principal_delta_keur" in first


def test_oborovo_first_twelve_debt_service_against_excel() -> None:
    """Debt service should equal CFADS / DSCR target once CFADS is calibrated."""
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_period_fixture("excel_oborovo_periods.json")[:12],
        metric_specs=OBOROVO_DEBT_SERVICE_METRIC_SPECS,
    )
    assert not failures, failures


def test_oborovo_first_twelve_debt_interest_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_period_fixture("excel_oborovo_periods.json")[:12],
        metric_specs=OBOROVO_DEBT_INTEREST_METRIC_SPECS,
    )
    assert not failures, {
        "interest_failures": failures,
        "debt_gap_diagnostics": _excel_app_debt_diagnostic_rows(limit=12),
    }


def test_oborovo_first_twelve_debt_principal_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_period_fixture("excel_oborovo_periods.json")[:12],
        metric_specs=OBOROVO_DEBT_PRINCIPAL_METRIC_SPECS,
    )
    assert not failures, {
        "principal_failures": failures,
        "debt_gap_diagnostics": _excel_app_debt_diagnostic_rows(limit=12),
    }


def test_oborovo_first_twelve_debt_principal_and_interest_against_excel() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    failures = collect_period_failures(
        app_periods_by_date=period_by_date(payload),
        excel_periods=_period_fixture("excel_oborovo_periods.json")[:12],
        metric_specs=OBOROVO_DEBT_SPLIT_METRIC_SPECS,
    )
    assert not failures, {
        "line_failures": failures,
        "debt_gap_diagnostics": _excel_app_debt_diagnostic_rows(limit=12),
    }


def test_oborovo_debt_schedule_continues_from_last_excel_anchor() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    debt_by_date = {row["date"]: row for row in payload["debt_decomposition"]}

    last_anchor = debt_by_date["2036-06-30"]
    first_continuation = debt_by_date["2036-12-31"]

    assert first_continuation["opening_balance_keur"] == pytest.approx(
        last_anchor["closing_balance_keur"],
    )
    assert first_continuation["closing_balance_keur"] > 0.0
    assert first_continuation["senior_principal_keur"] < first_continuation["opening_balance_keur"]
    assert first_continuation["senior_ds_keur"] < 3_000.0


def test_oborovo_full_model_debt_gap_summary_identifies_first_formula_delta() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    summary = payload["engine_debt_gap_before_full_model_calibration"]

    assert summary["source"] == "native_engine_before_full_model_calibration"
    assert summary["type"] == "debt"
    assert summary["compared_rows"] == 59
    assert summary["compared_metrics"] == [
        {
            "native_metric": "senior_principal_keur",
            "excel_metric": "DS.senior_principal_keur",
            "excel_sign": 1.0,
        },
        {
            "native_metric": "senior_interest_keur",
            "excel_metric": "DS.senior_net_interest_keur",
            "excel_sign": 1.0,
        },
        {
            "native_metric": "senior_ds_keur",
            "excel_metric": "CF.senior_debt_service_keur",
            "excel_sign": -1.0,
        },
    ]
    assert summary["mismatch_count"] == 72
    assert summary["max_abs_delta"] == pytest.approx(1477.126670339582)
    assert summary["max_abs_delta_location"]["date"] == "2042-12-31"
    assert summary["max_abs_delta_location"]["metric"] == "senior_principal_keur"
    assert summary["first_mismatch"]["date"] == "2032-06-30"
    assert summary["first_mismatch"]["metric"] == "senior_principal_keur"


def test_oborovo_raw_debt_gap_before_split_anchors_is_visible() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    summary = payload["raw_engine_debt_gap_before_split_anchors"]
    rows = payload["raw_engine_debt_decomposition_before_split_anchors"]["rows"]

    assert payload["raw_engine_debt_decomposition_before_split_anchors"]["source"] == (
        "native_engine_before_debt_split_anchors"
    )
    assert rows[0]["date"] == "2030-12-31"
    assert rows[0]["senior_principal_keur"] == pytest.approx(36042.31415219492)
    assert summary["source"] == "native_engine_before_debt_split_anchors"
    assert summary["type"] == "debt"
    assert summary["compared_rows"] == 59
    assert summary["mismatch_count"] == 84
    assert summary["max_abs_delta"] == pytest.approx(35137.19095560885)
    assert summary["first_mismatch"]["date"] == "2030-12-31"
    assert summary["first_mismatch"]["metric"] == "senior_principal_keur"


def test_tuho_debt_schedule_continues_from_last_excel_anchor() -> None:
    payload = run_project_calibration("tuho", calibration_source="pytest")
    debt_by_date = {row["date"]: row for row in payload["debt_decomposition"]}

    last_anchor = debt_by_date["2031-06-30"]
    first_continuation = debt_by_date["2031-12-31"]

    assert first_continuation["opening_balance_keur"] == pytest.approx(
        last_anchor["closing_balance_keur"],
    )
    assert first_continuation["closing_balance_keur"] > 0.0
    assert first_continuation["senior_principal_keur"] < first_continuation["opening_balance_keur"]


def test_tuho_full_model_debt_gap_summary_identifies_first_formula_delta() -> None:
    payload = run_project_calibration("tuho", calibration_source="pytest")
    summary = payload["engine_debt_gap_before_full_model_calibration"]

    assert summary["source"] == "native_engine_before_full_model_calibration"
    assert summary["type"] == "debt"
    assert summary["compared_rows"] == 59
    assert summary["mismatch_count"] == 75
    assert summary["max_abs_delta"] == pytest.approx(23046.29068918135)
    assert summary["max_abs_delta_location"]["date"] == "2038-12-31"
    assert summary["max_abs_delta_location"]["metric"] == "senior_principal_keur"
    assert summary["first_mismatch"]["date"] == "2031-12-31"
    assert summary["first_mismatch"]["metric"] == "senior_principal_keur"


def test_tuho_raw_debt_gap_before_split_anchors_is_visible() -> None:
    payload = run_project_calibration("tuho", calibration_source="pytest")
    summary = payload["raw_engine_debt_gap_before_split_anchors"]
    rows = payload["raw_engine_debt_decomposition_before_split_anchors"]["rows"]

    assert rows[0]["date"] == "2030-06-30"
    assert rows[0]["senior_principal_keur"] == pytest.approx(34896.39488640291)
    assert summary["source"] == "native_engine_before_debt_split_anchors"
    assert summary["type"] == "debt"
    assert summary["compared_rows"] == 59
    assert summary["mismatch_count"] == 84
    assert summary["max_abs_delta"] == pytest.approx(34077.1159782923)
    assert summary["first_mismatch"]["date"] == "2030-06-30"
    assert summary["first_mismatch"]["metric"] == "senior_principal_keur"


def test_oborovo_app_payload_contains_debt_diagnostics() -> None:
    payload = run_project_calibration("oborovo", calibration_source="pytest")
    app_rows = period_by_date(payload)
    for excel_row in _implied_excel_debt_rows("excel_oborovo_periods.json", limit=12):
        app_row = app_rows[excel_row["period_end_date"]]
        assert "senior_interest_keur" in app_row
        assert "senior_principal_keur" in app_row
        assert "senior_ds_keur" in app_row
        assert "dscr" in app_row
