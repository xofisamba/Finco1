"""Phase 9 TUHO SHL repayment trigger alignment implementation tests."""

from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "phase9_tuho_shl_repayment_trigger_alignment_implementation.md"
RUNTIME_REPORT = ROOT / "reports" / "phase9_tuho_shl_repayment_alignment_runtime_validation.csv"
PERIOD_BRIDGE = ROOT / "reports" / "phase9_tuho_shl_repayment_alignment_period_bridge.csv"
ALIGNMENT_START_PERIOD = 25


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _run_tuho(*, alignment_enabled: bool = False, explicit_off_start: bool = False):
    project = create_default_tuho_wind1()
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    if alignment_enabled:
        config = replace(
            config,
            use_tuho_shl_repayment_alignment=True,
            tuho_shl_principal_eligibility_start_period=ALIGNMENT_START_PERIOD,
        )
    elif explicit_off_start:
        config = replace(
            config,
            use_tuho_shl_repayment_alignment=False,
            tuho_shl_principal_eligibility_start_period=ALIGNMENT_START_PERIOD,
        )
    return project, WaterfallRunner(project, engine).run(config)


def _run_oborovo_default():
    project = create_default_oborovo()
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return project, engine, config, WaterfallRunner(project, engine).run(config)


def _first_principal_period(result) -> int:
    return next(
        idx
        for idx, period in enumerate(result.periods, start=1)
        if period.shl_principal_keur > 1e-6
    )


def _period_values(result, attr: str) -> list[float]:
    return [getattr(period, attr) for period in result.periods]


def test_artifacts_exist_and_reports_have_required_columns() -> None:
    assert DOC.exists()
    assert RUNTIME_REPORT.exists()
    assert PERIOD_BRIDGE.exists()

    runtime_rows = _rows(RUNTIME_REPORT)
    assert {
        "scenario",
        "alignment_enabled",
        "first_principal_period",
        "first_principal_date",
        "total_principal_repaid_keur",
        "equity_irr",
        "project_irr",
        "avg_dscr",
        "distribution_keur",
        "runtime_drift_detected",
        "notes",
    }.issubset(runtime_rows[0])
    assert {
        "TUHO baseline",
        "TUHO alignment OFF",
        "TUHO alignment ON",
        "Oborovo baseline",
        "Oborovo alignment attempt blocked",
    }.issubset({row["scenario"] for row in runtime_rows})

    bridge_rows = _rows(PERIOD_BRIDGE)
    assert len(bridge_rows) == 60
    assert {
        "period",
        "date",
        "excel_shl_principal_keur",
        "model_before_alignment_keur",
        "model_after_alignment_keur",
        "delta_before_keur",
        "delta_after_keur",
        "senior_ds_keur",
        "shl_interest_keur",
        "repayment_allowed_before",
        "repayment_allowed_after",
        "notes",
    }.issubset(bridge_rows[0])


def test_default_behavior_and_alignment_off_are_unchanged() -> None:
    project, baseline = _run_tuho()
    _, explicit_off = _run_tuho(explicit_off_start=True)

    assert project.financing.use_tuho_shl_repayment_alignment is False
    assert _first_principal_period(baseline) == 29
    assert _first_principal_period(explicit_off) == 29
    assert _period_values(explicit_off, "shl_principal_keur") == pytest.approx(
        _period_values(baseline, "shl_principal_keur"),
        abs=0.0001,
    )
    assert _period_values(explicit_off, "shl_balance_keur") == pytest.approx(
        _period_values(baseline, "shl_balance_keur"),
        abs=0.0001,
    )
    assert explicit_off.equity_irr == pytest.approx(baseline.equity_irr, abs=1e-10)
    assert explicit_off.project_irr == pytest.approx(baseline.project_irr, abs=1e-10)


def test_tuho_alignment_on_moves_first_principal_to_excel_p25() -> None:
    _, baseline = _run_tuho()
    _, aligned = _run_tuho(alignment_enabled=True)

    assert _first_principal_period(baseline) == 29
    assert _first_principal_period(aligned) == 25
    assert aligned.periods[24].date.isoformat() == "2042-06-30"
    assert aligned.periods[24].shl_principal_keur > 0.0
    assert aligned.equity_irr > baseline.equity_irr


def test_oborovo_is_guarded_and_default_oborovo_is_unchanged() -> None:
    _, engine, config, baseline = _run_oborovo_default()
    project = create_default_oborovo()
    runner = WaterfallRunner(project, engine)

    with pytest.raises(ValueError, match="TUHO SHL repayment alignment"):
        runner.run(
            replace(
                config,
                use_tuho_shl_repayment_alignment=True,
                tuho_shl_principal_eligibility_start_period=ALIGNMENT_START_PERIOD,
            )
        )

    _, _, _, repeat = _run_oborovo_default()
    assert repeat.project_irr == pytest.approx(baseline.project_irr, abs=1e-10)
    assert repeat.equity_irr == pytest.approx(baseline.equity_irr, abs=1e-10)
    assert _period_values(repeat, "shl_principal_keur") == pytest.approx(
        _period_values(baseline, "shl_principal_keur"),
        abs=0.0001,
    )


def test_no_unexpected_senior_debt_dscr_project_irr_or_r99_drift() -> None:
    _, baseline = _run_tuho()
    _, aligned = _run_tuho(alignment_enabled=True)

    assert aligned.project_irr == pytest.approx(baseline.project_irr, abs=1e-10)
    assert _period_values(aligned, "dscr") == pytest.approx(
        _period_values(baseline, "dscr"),
        abs=0.0001,
    )
    for attr in ("senior_interest_keur", "senior_principal_keur", "senior_ds_keur"):
        assert _period_values(aligned, attr) == pytest.approx(
            _period_values(baseline, attr),
            abs=0.0001,
        )
    for attr in ("r99_fcf_for_distribution_keur", "r102_fcf_for_shl_keur"):
        assert _period_values(aligned, attr) == pytest.approx(
            _period_values(baseline, attr),
            abs=0.0001,
        )
    assert all(
        not getattr(period, "r99_runtime_source_accepted", False)
        for period in aligned.periods
    )


def test_shl_interest_and_pik_formula_scope_is_preserved() -> None:
    _, baseline = _run_tuho()
    _, aligned = _run_tuho(alignment_enabled=True)

    assert _period_values(aligned, "shl_pik_keur")[:24] == pytest.approx(
        _period_values(baseline, "shl_pik_keur")[:24],
        abs=0.0001,
    )
    assert _period_values(aligned, "shl_gross_accrued_interest_keur")[:24] == pytest.approx(
        _period_values(baseline, "shl_gross_accrued_interest_keur")[:24],
        abs=0.0001,
    )
    assert all(period.shl_interest_keur >= 0.0 for period in aligned.periods)
    assert all(period.shl_pik_keur >= 0.0 for period in aligned.periods)


def test_docs_preserve_governance_status() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "G20 remains BLOCKED" in text
    assert "R99/R102 runtime promotion remains NOT approved" in text
    assert "default-off" in text or "off by default" in text
    assert "Oborovo Guard" in text
