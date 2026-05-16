import json
from dataclasses import replace
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.inputs import SHLRepaymentMethod
from domain.shl_fcf_waterfall import compute_shl_fcf_waterfall_period
from tests.test_senior_dscr_sculpting_full_schedule_fixtures import (
    _load_excel_senior_fixture,
    _with_full_explicit_senior_fixture,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _run(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _tuho_r99_schedule():
    data = json.loads((FIXTURE_DIR / "excel_tuho_full_model_extract.json").read_text(encoding="utf-8"))
    columns = {name: idx for idx, name in enumerate(data["period_diagnostic_columns"])}
    operating_schedule = tuple(
        row[columns["CF.free_cash_flow_for_distribution_keur"]]
        for row in data["period_diagnostics"]
    )
    # The current runtime horizon includes terminal/stub periods beyond the 60
    # Excel operating-period rows. Keep those diagnostic-only periods unfunded.
    project = create_default_tuho_wind1()
    runtime_period_count = len(_build_period_engine(project).periods())
    return operating_schedule + (0.0,) * max(0, runtime_period_count - len(operating_schedule))


def _tuho_excel_shl_rows():
    data = json.loads((FIXTURE_DIR / "excel_tuho_full_model_extract.json").read_text(encoding="utf-8"))
    columns = {name: idx for idx, name in enumerate(data["shl_columns"])}
    rows = []
    for idx, row in enumerate(data["shl"][1:]):
        rows.append(
            {
                "op_idx": idx,
                "date": row[columns["date"]],
                "opening": row[columns["opening"]],
                "closing": row[columns["closing"]],
                "gross_interest": row[columns["gross_interest"]],
                "principal": max(0.0, row[columns["principal_flow"]]),
                "cash_interest": row[columns["paid_net_interest"]],
                "pik": row[columns["capitalized_interest"]],
                "distribution": max(0.0, row[columns["net_dividend"]]),
            }
        )
    return tuple(rows)


def _tuho_fcf_project(*, minimum_cash_retained_keur=0.0):
    project = _with_full_explicit_senior_fixture(
        create_default_tuho_wind1(),
        _load_excel_senior_fixture("tuho"),
    )
    data = json.loads((FIXTURE_DIR / "excel_tuho_full_model_extract.json").read_text(encoding="utf-8"))
    shl_columns = {name: idx for idx, name in enumerate(data["shl_columns"])}
    construction_shl_row = data["shl"][0]
    first_shl_row = _tuho_excel_shl_rows()[0]
    excel_shl_rate = first_shl_row["gross_interest"] / first_shl_row["opening"] / 0.5
    return replace(
        project,
        info=replace(project.info, use_shl_fcf_waterfall_engine=True),
        financing=replace(
            project.financing,
            shl_amount_keur=abs(construction_shl_row[shl_columns["principal_flow"]]),
            shl_idc_keur=construction_shl_row[shl_columns["capitalized_interest"]],
            shl_rate=excel_shl_rate,
            shl_repayment_method=SHLRepaymentMethod.FCF_WATERFALL.value,
            shl_fcf_waterfall_cash_schedule_keur=_tuho_r99_schedule(),
            shl_fcf_waterfall_minimum_cash_retained_keur=minimum_cash_retained_keur,
        ),
    )


def test_shl_fcf_waterfall_flag_defaults_false():
    assert create_default_tuho_wind1().info.use_shl_fcf_waterfall_engine is False
    assert create_default_oborovo().info.use_shl_fcf_waterfall_engine is False


def test_default_off_equivalence_for_tuho_and_oborovo():
    for factory in (create_default_tuho_wind1, create_default_oborovo):
        project = factory()
        baseline = _run(project)
        configured = replace(
            project,
            financing=replace(
                project.financing,
                shl_fcf_waterfall_cash_schedule_keur=(1_000.0,) * 60,
                shl_fcf_waterfall_minimum_cash_retained_keur=100.0,
            ),
        )
        flag_off = _run(configured)

        assert flag_off.total_revenue_keur == pytest.approx(baseline.total_revenue_keur, abs=0.0001)
        assert flag_off.total_opex_keur == pytest.approx(baseline.total_opex_keur, abs=0.0001)
        assert flag_off.total_senior_ds_keur == pytest.approx(baseline.total_senior_ds_keur, abs=0.0001)
        assert flag_off.total_shl_service_keur == pytest.approx(baseline.total_shl_service_keur, abs=0.0001)
        assert flag_off.total_distribution_keur == pytest.approx(baseline.total_distribution_keur, abs=0.0001)


def test_fcf_waterfall_method_rejected_when_flag_false():
    project = create_default_tuho_wind1()
    project = replace(
        project,
        financing=replace(
            project.financing,
            shl_repayment_method=SHLRepaymentMethod.FCF_WATERFALL.value,
            shl_fcf_waterfall_cash_schedule_keur=_tuho_r99_schedule(),
        ),
    )

    with pytest.raises(ValueError, match="use_shl_fcf_waterfall_engine=True"):
        _run(project)


def test_oborovo_fcf_waterfall_runtime_opt_in_rejected():
    project = create_default_oborovo()
    project = replace(
        project,
        info=replace(project.info, use_shl_fcf_waterfall_engine=True),
        financing=replace(
            project.financing,
            shl_repayment_method=SHLRepaymentMethod.FCF_WATERFALL.value,
            shl_fcf_waterfall_cash_schedule_keur=(1_000.0,) * 60,
        ),
    )

    with pytest.raises(ValueError, match="supported only for TUHO-WIND-1"):
        _run(project)


def test_tuho_fcf_waterfall_missing_cash_source_rejected():
    project = create_default_tuho_wind1()
    project = replace(
        project,
        info=replace(project.info, use_shl_fcf_waterfall_engine=True),
        financing=replace(project.financing, shl_repayment_method=SHLRepaymentMethod.FCF_WATERFALL.value),
    )

    with pytest.raises(ValueError, match="cash_schedule"):
        _run(project)


def test_tuho_fixture_backed_fcf_waterfall_matches_shl_mechanics():
    result = _run(_tuho_fcf_project())
    excel_rows = _tuho_excel_shl_rows()

    first_period = result.periods[0]
    first_excel = excel_rows[0]
    assert first_period.date.isoformat() == first_excel["date"]
    assert first_period.shl_interest_keur == pytest.approx(first_excel["cash_interest"], abs=0.01)
    assert first_period.shl_pik_keur == pytest.approx(first_excel["pik"], abs=0.01)
    assert first_period.shl_principal_keur == pytest.approx(first_excel["principal"], abs=0.01)
    assert first_period.shl_balance_keur == pytest.approx(first_excel["closing"], abs=0.01)
    assert first_period.distribution_keur == pytest.approx(first_excel["distribution"], abs=0.01)

    for idx in (10, 20, 28, 32, 35):
        period = result.periods[idx]
        assert period.date.isoformat() == excel_rows[idx]["date"]
        assert period.shl_interest_keur >= -0.0001
        assert period.shl_pik_keur >= -0.0001
        assert period.shl_principal_keur >= -0.0001
        assert period.shl_balance_keur >= -0.0001
        assert period.distribution_keur >= -0.0001

    first_distribution = next(
        idx for idx, period in enumerate(result.periods) if period.distribution_keur > 0.001
    )
    assert 35 <= first_distribution <= 37
    assert min(period.shl_balance_keur for period in result.periods) >= -0.0001
    assert all(
        period.shl_principal_keur <= period.shl_balance_keur + period.shl_principal_keur + 0.001
        for period in result.periods
    )


def test_tuho_fixture_backed_aggregate_calibration_within_acceptance_bands():
    result = _run(_tuho_fcf_project())

    assert 144_124.0 <= result.total_distribution_keur <= 159_294.0
    assert 78_000.0 <= result.total_shl_service_keur <= 87_000.0
    assert 41_000.0 <= max(period.shl_balance_keur for period in result.periods) <= 47_000.0


def test_minimum_retained_cash_buffer_reduces_distributions_and_is_respected():
    base = _run(_tuho_fcf_project(minimum_cash_retained_keur=0.0))
    buffer_50 = _run(_tuho_fcf_project(minimum_cash_retained_keur=50.0))
    buffer_100 = _run(_tuho_fcf_project(minimum_cash_retained_keur=100.0))

    assert buffer_50.total_distribution_keur < base.total_distribution_keur
    assert buffer_100.total_distribution_keur < buffer_50.total_distribution_keur

    sample = compute_shl_fcf_waterfall_period(
        opening_shl_balance_keur=10_000.0,
        shl_rate=0.08,
        day_fraction=0.5,
        fcf_for_shl_keur=1_000.0,
        withholding_tax_rate=0.0,
        minimum_cash_retained_keur=100.0,
    )
    assert sample.retained_cash_keur == pytest.approx(100.0)
    assert sample.available_cash_after_buffer_keur == pytest.approx(900.0)
    assert sample.distribution_keur >= 0.0


def test_no_non_shl_operating_drift_under_fixture_backed_run():
    senior_only = _run(
        _with_full_explicit_senior_fixture(create_default_tuho_wind1(), _load_excel_senior_fixture("tuho"))
    )
    fcf = _run(_tuho_fcf_project())

    assert fcf.total_revenue_keur == pytest.approx(senior_only.total_revenue_keur, abs=0.0001)
    assert fcf.total_opex_keur == pytest.approx(senior_only.total_opex_keur, abs=0.0001)
    assert fcf.total_senior_ds_keur == pytest.approx(senior_only.total_senior_ds_keur, abs=0.0001)
    assert getattr(fcf, "construction_schedule_diagnostic", None) == getattr(
        senior_only,
        "construction_schedule_diagnostic",
        None,
    )
