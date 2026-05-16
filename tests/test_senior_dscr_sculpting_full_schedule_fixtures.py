import json
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.senior_rate_schedule import (
    SeniorDayCountConvention,
    SeniorDebtInterestConfig,
    SeniorRateMode,
    SeniorRateSchedule,
)
from domain.senior_sculpting import SeniorSculptingConfig, SeniorSculptingMode


TENOR_PERIODS = 28
FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _run(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _senior_row(period):
    return {
        "date": period.date.isoformat(),
        "opening": period.senior_balance_keur + period.senior_principal_keur,
        "interest": period.senior_interest_keur,
        "principal": period.senior_principal_keur,
        "ds": period.senior_ds_keur,
        "closing": period.senior_balance_keur,
    }


def _first_period_start(end: date) -> date:
    if end.month == 6:
        return date(end.year, 1, 1)
    if end.month == 12:
        return date(end.year, 7, 1)
    raise ValueError(f"Unsupported semiannual end date: {end}")


def _load_excel_senior_fixture(project_key: str):
    path = FIXTURE_DIR / f"excel_{project_key}_full_model_extract.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    columns = {name: idx for idx, name in enumerate(data["period_diagnostic_columns"])}
    diagnostics = data["period_diagnostics"][:TENOR_PERIODS]

    principal_values = [
        row[columns["DS.senior_principal_keur"]]
        for row in diagnostics
    ]
    opening = sum(principal_values)
    rows = []
    previous_end = None
    balance = opening
    for idx, row in enumerate(diagnostics):
        end = date.fromisoformat(row[columns["date"]])
        start = _first_period_start(end) if previous_end is None else previous_end + timedelta(days=1)
        fraction = ((end - start).days + 1) / 360.0
        interest = row[columns["DS.senior_net_interest_keur"]]
        principal = row[columns["DS.senior_principal_keur"]]
        debt_service = -row[columns["CF.senior_debt_service_keur"]]
        annual_rate = interest / balance / fraction if balance else 0.0
        closing = max(0.0, balance - principal)
        rows.append(
            {
                "op_idx": idx,
                "date": end.isoformat(),
                "opening": balance,
                "fraction": fraction,
                "annual_rate": annual_rate,
                "interest": interest,
                "principal": principal,
                "ds": debt_service,
                "closing": closing,
            }
        )
        previous_end = end
        balance = closing

    return {
        "project_key": project_key,
        "opening": opening,
        "rows": tuple(rows),
        "total_ds": sum(row["ds"] for row in rows),
        "total_interest": sum(row["interest"] for row in rows),
        "total_principal": sum(row["principal"] for row in rows),
    }


def _rate_config(fixture):
    rows = fixture["rows"]
    return SeniorDebtInterestConfig(
        enabled=True,
        rate_schedule=SeniorRateSchedule(
            mode=SeniorRateMode.EXPLICIT_ALL_IN_SCHEDULE,
            explicit_all_in_rates=tuple(row["annual_rate"] for row in rows),
        ),
        day_count=SeniorDayCountConvention.EXPLICIT_FRACTIONS,
        explicit_period_fractions=tuple(row["fraction"] for row in rows),
    )


def _sculpting_config(fixture):
    return SeniorSculptingConfig(
        enabled=True,
        mode=SeniorSculptingMode.EXPLICIT_DEBT_SERVICE_SCHEDULE,
        explicit_debt_service_schedule=tuple(row["ds"] for row in fixture["rows"]),
    )


def _with_full_explicit_senior_fixture(project, fixture):
    return replace(
        project,
        info=replace(
            project.info,
            use_senior_rate_schedule_engine=True,
            use_senior_sculpting_basis_engine=True,
        ),
        financing=replace(
            project.financing,
            fixed_debt_keur=fixture["opening"],
            senior_debt_interest_config=_rate_config(fixture),
            senior_sculpting_config=_sculpting_config(fixture),
        ),
    )


def _assert_period_matches_excel(period, excel_row):
    actual = _senior_row(period)
    assert actual["date"] == excel_row["date"]
    assert actual["opening"] == pytest.approx(excel_row["opening"], abs=0.01)
    assert actual["interest"] == pytest.approx(excel_row["interest"], abs=0.01)
    assert actual["principal"] == pytest.approx(excel_row["principal"], abs=0.01)
    assert actual["ds"] == pytest.approx(excel_row["ds"], abs=0.01)
    assert actual["closing"] == pytest.approx(excel_row["closing"], abs=0.01)


def test_full_schedule_fixtures_do_not_enable_factories():
    assert create_default_tuho_wind1().info.use_senior_sculpting_basis_engine is False
    assert create_default_oborovo().info.use_senior_sculpting_basis_engine is False
    assert create_default_tuho_wind1().info.use_senior_rate_schedule_engine is False
    assert create_default_oborovo().info.use_senior_rate_schedule_engine is False


def test_flag_off_unchanged_with_full_fixture_configs_present():
    cases = (
        (create_default_tuho_wind1, _load_excel_senior_fixture("tuho")),
        (create_default_oborovo, _load_excel_senior_fixture("oborovo")),
    )
    for factory, fixture in cases:
        project = factory()
        baseline = _run(project)
        configured_but_flag_off = replace(
            project,
            financing=replace(
                project.financing,
                senior_debt_interest_config=_rate_config(fixture),
                senior_sculpting_config=_sculpting_config(fixture),
            ),
        )
        result = _run(configured_but_flag_off)

        assert result.total_revenue_keur == pytest.approx(baseline.total_revenue_keur, abs=0.0001)
        assert result.total_opex_keur == pytest.approx(baseline.total_opex_keur, abs=0.0001)
        assert result.total_senior_ds_keur == pytest.approx(baseline.total_senior_ds_keur, abs=0.0001)
        assert result.total_shl_service_keur == pytest.approx(baseline.total_shl_service_keur, abs=0.0001)
        assert result.total_distribution_keur == pytest.approx(baseline.total_distribution_keur, abs=0.0001)


def test_tuho_full_explicit_ds_fixture_matches_excel_senior_tenor():
    fixture = _load_excel_senior_fixture("tuho")
    result = _run(_with_full_explicit_senior_fixture(create_default_tuho_wind1(), fixture))

    assert result.total_senior_ds_keur == pytest.approx(fixture["total_ds"], abs=0.01)
    assert result.total_senior_ds_keur == pytest.approx(66_181.347, abs=0.01)
    assert result.periods[TENOR_PERIODS - 1].senior_balance_keur == pytest.approx(0.0, abs=0.01)

    for idx in (0, 1, 2, 3, TENOR_PERIODS - 1):
        _assert_period_matches_excel(result.periods[idx], fixture["rows"][idx])


def test_oborovo_full_explicit_ds_fixture_matches_excel_senior_tenor():
    fixture = _load_excel_senior_fixture("oborovo")
    result = _run(_with_full_explicit_senior_fixture(create_default_oborovo(), fixture))

    assert result.total_senior_ds_keur == pytest.approx(fixture["total_ds"], abs=0.01)
    assert result.total_senior_ds_keur == pytest.approx(62_985.358, abs=0.01)
    assert result.periods[TENOR_PERIODS - 1].senior_balance_keur == pytest.approx(0.0, abs=0.01)

    for idx in (0, 1, 2, 3, TENOR_PERIODS - 1):
        _assert_period_matches_excel(result.periods[idx], fixture["rows"][idx])


def test_opening_policy_preserved_with_full_explicit_ds_fixture():
    cases = (
        (create_default_tuho_wind1, _load_excel_senior_fixture("tuho"), 44_878.838),
        (create_default_oborovo, _load_excel_senior_fixture("oborovo"), 43_938.299),
    )
    for factory, fixture, principal_plus_idc in cases:
        result = _run(_with_full_explicit_senior_fixture(factory(), fixture))
        first = _senior_row(result.periods[0])

        assert first["opening"] == pytest.approx(fixture["opening"], abs=0.01)
        assert first["opening"] != pytest.approx(principal_plus_idc, abs=0.30)


def test_downstream_impacts_are_measured_but_not_calibrated():
    cases = (
        (create_default_tuho_wind1, _load_excel_senior_fixture("tuho"), 3_489.544, -1_127.613),
        (create_default_oborovo, _load_excel_senior_fixture("oborovo"), 0.0, 1_686.225),
    )
    for factory, fixture, expected_shl_delta, expected_distribution_delta in cases:
        baseline = _run(factory())
        explicit = _run(_with_full_explicit_senior_fixture(factory(), fixture))

        assert explicit.total_revenue_keur == pytest.approx(baseline.total_revenue_keur, abs=0.0001)
        assert explicit.total_opex_keur == pytest.approx(baseline.total_opex_keur, abs=0.0001)
        assert explicit.total_senior_ds_keur == pytest.approx(fixture["total_ds"], abs=0.01)
        assert explicit.total_shl_service_keur - baseline.total_shl_service_keur == pytest.approx(
            expected_shl_delta,
            abs=0.01,
        )
        assert explicit.total_distribution_keur - baseline.total_distribution_keur == pytest.approx(
            expected_distribution_delta,
            abs=0.01,
        )
