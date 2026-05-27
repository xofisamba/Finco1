"""Phase 20P — Revenue / OPEX / CFADS Diagnostic Bridge tests.

These tests verify:
1. Diagnostic table contains all required metrics for TUHO P4
2. Diagnostic table contains all required metrics for Oborovo P4
3. Deltas are calculated correctly
4. Missing metrics are reported as MISSING, not crash
5. No formulas are changed (regression)
6. Default debt sizing mode remains frozen_excel_schedule
7. Future modes still raise NotImplementedError
"""
import pytest
from app.project_factories import create_default_tuho_wind1, create_default_oborovo
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.revenue.generation import revenue_decomposition_schedule
from domain.diagnostics.cfads_bridge import (
    build_tuho_p4_diagnostic,
    build_oborovo_p4_diagnostic,
    diagnostic_table_to_list,
    DiagnosticStatus,
    TUHO_P4_ANCHORS,
    OBOROVO_P4_ANCHORS,
)
from domain.inputs import DebtSizingMode, FinancingParams


# ─────────────────────────────────────────────────────────────────────────────
# TUHO P4 — all required metrics present
# ─────────────────────────────────────────────────────────────────────────────

def test_tuho_p4_diagnostic_has_all_required_metrics():
    """TUHO P4 diagnostic must have entries for all required metric names."""
    tuho = create_default_tuho_wind1()
    eng = _build_period_engine(tuho)
    r = WaterfallRunner(inputs=tuho, engine=eng).run(WaterfallRunConfig.from_inputs(tuho, eng))
    p4 = r.periods[3]
    rev_dec = revenue_decomposition_schedule(tuho, eng)[3]

    table = build_tuho_p4_diagnostic(
        python_generation_mwh=p4.generation_mwh,
        python_ppa_revenue_keur=p4.revenue_keur,
        python_co2_revenue_keur=rev_dec["co2_certificate_revenue_keur"],
        python_balancing_keur=rev_dec["balancing_cost_keur"],
        python_net_revenue_keur=rev_dec["net_revenue_after_balancing_keur"],
        python_opex_keur=p4.opex_keur,
        python_ebitda_keur=p4.ebitda_keur,
        python_cfads_keur=p4.cf_after_tax_keur,
        python_senior_ds_keur=p4.senior_ds_keur,
        python_senior_interest_keur=p4.senior_interest_keur,
        python_senior_principal_keur=p4.senior_principal_keur,
        python_shl_sweep_keur=p4.shl_principal_keur,
        python_distribution_keur=p4.distribution_keur,
    )

    required_metrics = {
        "production_mwh", "ppa_revenue_keur", "co2_revenue_keur",
        "balancing_cost_keur", "opex_keur", "ebitda_keur", "cfads_keur",
        "senior_service_keur", "senior_interest_keur", "senior_principal_keur",
        "shl_sweep_keur", "net_dividends_keur",
    }
    found_metrics = {row.metric for row in table.rows}
    assert required_metrics == found_metrics, (
        f"Missing metrics: {required_metrics - found_metrics}"
    )


def test_tuho_p4_production_mwh_pass():
    """TUHO P4 generation_mwh should match Excel anchor within 0.5 MWh tolerance."""
    tuho = create_default_tuho_wind1()
    eng = _build_period_engine(tuho)
    r = WaterfallRunner(inputs=tuho, engine=eng).run(WaterfallRunConfig.from_inputs(tuho, eng))
    p4 = r.periods[3]

    table = build_tuho_p4_diagnostic(
        python_generation_mwh=p4.generation_mwh,
        python_ppa_revenue_keur=p4.revenue_keur,
        python_co2_revenue_keur=0.0,
        python_balancing_keur=0.0,
        python_net_revenue_keur=0.0,
        python_opex_keur=0.0,
        python_ebitda_keur=0.0,
        python_cfads_keur=0.0,
        python_senior_ds_keur=0.0,
        python_senior_interest_keur=0.0,
        python_senior_principal_keur=0.0,
        python_shl_sweep_keur=0.0,
        python_distribution_keur=0.0,
    )
    row = next(r for r in table.rows if r.metric == "production_mwh")
    assert row.status == DiagnosticStatus.PASS, f"production_mwh FAIL: delta={row.delta}"


# ─────────────────────────────────────────────────────────────────────────────
# Oborovo P4 — all required metrics present
# ─────────────────────────────────────────────────────────────────────────────

def test_oborovo_p4_diagnostic_has_all_required_metrics():
    """Oborovo P4 diagnostic must have entries for all required metric names."""
    obor = create_default_oborovo()
    eng = _build_period_engine(obor)
    r = WaterfallRunner(inputs=obor, engine=eng).run(WaterfallRunConfig.from_inputs(obor, eng))
    p4 = r.periods[3]
    rev_dec = revenue_decomposition_schedule(obor, eng)[3]

    table = build_oborovo_p4_diagnostic(
        python_generation_mwh=p4.generation_mwh,
        python_ppa_revenue_keur=p4.revenue_keur,
        python_co2_revenue_keur=rev_dec["co2_certificate_revenue_keur"],
        python_balancing_keur=rev_dec["balancing_cost_keur"],
        python_net_revenue_keur=rev_dec["net_revenue_after_balancing_keur"],
        python_opex_keur=p4.opex_keur,
        python_ebitda_keur=p4.ebitda_keur,
        python_cfads_keur=p4.cf_after_tax_keur,
        python_senior_ds_keur=p4.senior_ds_keur,
        python_shl_sweep_keur=p4.shl_principal_keur,
        python_distribution_keur=p4.distribution_keur,
    )

    required_metrics = {
        "production_mwh", "ppa_revenue_keur", "co2_revenue_keur",
        "balancing_cost_keur", "opex_keur", "ebitda_keur", "cfads_keur",
        "senior_service_keur", "shl_sweep_keur", "net_dividends_keur",
    }
    found_metrics = {row.metric for row in table.rows}
    assert required_metrics == found_metrics


def test_oborovo_p4_production_mwh_pass():
    """Oborovo P4 generation_mwh should match Excel anchor within 0.5 MWh tolerance."""
    obor = create_default_oborovo()
    eng = _build_period_engine(obor)
    r = WaterfallRunner(inputs=obor, engine=eng).run(WaterfallRunConfig.from_inputs(obor, eng))
    p4 = r.periods[3]

    table = build_oborovo_p4_diagnostic(
        python_generation_mwh=p4.generation_mwh,
        python_ppa_revenue_keur=0.0,
        python_co2_revenue_keur=0.0,
        python_balancing_keur=0.0,
        python_net_revenue_keur=0.0,
        python_opex_keur=0.0,
        python_ebitda_keur=0.0,
        python_cfads_keur=0.0,
        python_senior_ds_keur=0.0,
        python_shl_sweep_keur=0.0,
        python_distribution_keur=0.0,
    )
    row = next(r for r in table.rows if r.metric == "production_mwh")
    assert row.status == DiagnosticStatus.PASS


# ─────────────────────────────────────────────────────────────────────────────
# Delta calculation
# ─────────────────────────────────────────────────────────────────────────────

def test_delta_calculation_correct_for_passing_row():
    """Delta = python_value - excel_value; PASS when abs(delta) <= tolerance."""
    from domain.diagnostics.cfads_bridge import make_row, DiagnosticStatus
    row = make_row(
        project_code="TEST", period_index=0, period_label="P1",
        metric="test_metric", excel_value=100.0, python_value=102.0,
        tolerance=5.0,
    )
    assert row.delta == 2.0
    assert row.status == DiagnosticStatus.PASS


def test_delta_calculation_correct_for_failing_row():
    """Delta = python_value - excel_value; FAIL when abs(delta) > tolerance."""
    from domain.diagnostics.cfads_bridge import make_row, DiagnosticStatus
    row = make_row(
        project_code="TEST", period_index=0, period_label="P1",
        metric="test_metric", excel_value=100.0, python_value=110.0,
        tolerance=5.0,
    )
    assert row.delta == 10.0
    assert row.status == DiagnosticStatus.FAIL


def test_delta_is_none_when_python_value_is_none():
    """MISSING when python_value is None (not a crash)."""
    from domain.diagnostics.cfads_bridge import make_row, DiagnosticStatus
    row = make_row(
        project_code="TEST", period_index=0, period_label="P1",
        metric="test_metric", excel_value=100.0, python_value=None,
        tolerance=5.0,
    )
    assert row.delta is None
    assert row.status == DiagnosticStatus.MISSING


def test_delta_is_none_when_excel_value_is_none():
    """MISSING when excel_value is None."""
    from domain.diagnostics.cfads_bridge import make_row, DiagnosticStatus
    row = make_row(
        project_code="TEST", period_index=0, period_label="P1",
        metric="test_metric", excel_value=None, python_value=100.0,
        tolerance=5.0,
    )
    assert row.delta is None
    assert row.status == DiagnosticStatus.MISSING


# ─────────────────────────────────────────────────────────────────────────────
# Missing metrics handled gracefully
# ─────────────────────────────────────────────────────────────────────────────

def test_missing_metric_does_not_crash():
    """Calling build with None for all values should return MISSING rows, not crash."""
    table = build_tuho_p4_diagnostic(
        python_generation_mwh=None,
        python_ppa_revenue_keur=None,
        python_co2_revenue_keur=None,
        python_balancing_keur=None,
        python_net_revenue_keur=None,
        python_opex_keur=None,
        python_ebitda_keur=None,
        python_cfads_keur=None,
        python_senior_ds_keur=None,
        python_senior_interest_keur=None,
        python_senior_principal_keur=None,
        python_shl_sweep_keur=None,
        python_distribution_keur=None,
    )
    # All rows should be MISSING, not crashed
    assert all(r.status == DiagnosticStatus.MISSING for r in table.rows)
    assert table.missing_count() == len(table.rows)


# ─────────────────────────────────────────────────────────────────────────────
# No runtime formula changes (regression)
# ─────────────────────────────────────────────────────────────────────────────

def test_tuho_default_outputs_unchanged_after_diagnostic_import():
    """TUHO total_senior_ds_keur and equity_irr remain at baseline after diagnostic import."""
    tuho = create_default_tuho_wind1()
    eng = _build_period_engine(tuho)
    cfg = WaterfallRunConfig.from_inputs(tuho, eng)
    result = WaterfallRunner(inputs=tuho, engine=eng).run(cfg)
    assert abs(result.total_senior_ds_keur - 65_826) < 1
    assert abs(result.equity_irr - 0.1115) < 0.002


def test_oborovo_default_outputs_unchanged_after_diagnostic_import():
    """Oborovo total_senior_ds_keur and equity_irr remain at baseline."""
    obor = create_default_oborovo()
    eng = _build_period_engine(obor)
    cfg = WaterfallRunConfig.from_inputs(obor, eng)
    result = WaterfallRunner(inputs=obor, engine=eng).run(cfg)
    assert abs(result.total_senior_ds_keur - 63_501) < 1
    assert abs(result.equity_irr - 0.0917) < 0.002


# ─────────────────────────────────────────────────────────────────────────────
# Debt sizing mode unchanged
# ─────────────────────────────────────────────────────────────────────────────

def test_default_debt_sizing_mode_is_frozen_excel_schedule():
    """FinancingParams.debt_sizing_mode still defaults to None → FROZEN_EXCEL_SCHEDULE."""
    fp = FinancingParams()
    assert fp.debt_sizing_mode is None
    assert fp.resolved_debt_sizing_mode() == DebtSizingMode.FROZEN_EXCEL_SCHEDULE


def test_future_mode_minimum_dscr_raises_not_implemented_error():
    """MINIMUM_DSCR_SCULPTED still raises NotImplementedError."""
    fp = FinancingParams(debt_sizing_mode=DebtSizingMode.MINIMUM_DSCR_SCULPTED)
    with pytest.raises(NotImplementedError):
        fp.resolved_debt_sizing_mode()


def test_future_mode_flat_dscr_raises_not_implemented_error():
    """FLAT_DSCR_SCULPTED still raises NotImplementedError."""
    fp = FinancingParams(debt_sizing_mode=DebtSizingMode.FLAT_DSCR_SCULPTED)
    with pytest.raises(NotImplementedError):
        fp.resolved_debt_sizing_mode()


# ─────────────────────────────────────────────────────────────────────────────
# Diagnostic output / export
# ─────────────────────────────────────────────────────────────────────────────

def test_diagnostic_table_to_list_returns_serializable_dicts():
    """diagnostic_table_to_list produces JSON-serializable list of dicts."""
    tuho = create_default_tuho_wind1()
    eng = _build_period_engine(tuho)
    r = WaterfallRunner(inputs=tuho, engine=eng).run(WaterfallRunConfig.from_inputs(tuho, eng))
    p4 = r.periods[3]
    rev_dec = revenue_decomposition_schedule(tuho, eng)[3]

    table = build_tuho_p4_diagnostic(
        python_generation_mwh=p4.generation_mwh,
        python_ppa_revenue_keur=p4.revenue_keur,
        python_co2_revenue_keur=rev_dec["co2_certificate_revenue_keur"],
        python_balancing_keur=rev_dec["balancing_cost_keur"],
        python_net_revenue_keur=rev_dec["net_revenue_after_balancing_keur"],
        python_opex_keur=p4.opex_keur,
        python_ebitda_keur=p4.ebitda_keur,
        python_cfads_keur=p4.cf_after_tax_keur,
        python_senior_ds_keur=p4.senior_ds_keur,
        python_senior_interest_keur=p4.senior_interest_keur,
        python_senior_principal_keur=p4.senior_principal_keur,
        python_shl_sweep_keur=p4.shl_principal_keur,
        python_distribution_keur=p4.distribution_keur,
    )

    rows = diagnostic_table_to_list(table)
    assert isinstance(rows, list)
    assert all(isinstance(r, dict) for r in rows)
    assert all("metric" in r and "status" in r and "delta" in r for r in rows)
    # JSON serializable
    import json
    json.dumps(rows)


def test_diagnostic_summary_contains_pass_fail_counts():
    """DiagnosticTable.summary() returns pass/fail/missing/warn counts."""
    tuho = create_default_tuho_wind1()
    eng = _build_period_engine(tuho)
    r = WaterfallRunner(inputs=tuho, engine=eng).run(WaterfallRunConfig.from_inputs(tuho, eng))
    p4 = r.periods[3]
    rev_dec = revenue_decomposition_schedule(tuho, eng)[3]

    table = build_tuho_p4_diagnostic(
        python_generation_mwh=p4.generation_mwh,
        python_ppa_revenue_keur=p4.revenue_keur,
        python_co2_revenue_keur=rev_dec["co2_certificate_revenue_keur"],
        python_balancing_keur=rev_dec["balancing_cost_keur"],
        python_net_revenue_keur=rev_dec["net_revenue_after_balancing_keur"],
        python_opex_keur=p4.opex_keur,
        python_ebitda_keur=p4.ebitda_keur,
        python_cfads_keur=p4.cf_after_tax_keur,
        python_senior_ds_keur=p4.senior_ds_keur,
        python_senior_interest_keur=p4.senior_interest_keur,
        python_senior_principal_keur=p4.senior_principal_keur,
        python_shl_sweep_keur=p4.shl_principal_keur,
        python_distribution_keur=p4.distribution_keur,
    )

    s = table.summary()
    assert "pass" in s and "fail" in s and "missing" in s and "warn" in s
    assert s["pass"] + s["fail"] + s["missing"] + s["warn"] == s["total"]


# ─────────────────────────────────────────────────────────────────────────────
# Diagnostic stability — running the diagnostic does not mutate state
# ─────────────────────────────────────────────────────────────────────────────

def test_running_diagnostic_does_not_change_waterfall_result():
    """Re-running waterfall after diagnostic produces same result (no mutation)."""
    tuho = create_default_tuho_wind1()
    eng = _build_period_engine(tuho)
    cfg = WaterfallRunConfig.from_inputs(tuho, eng)

    r1 = WaterfallRunner(inputs=tuho, engine=eng).run(cfg)
    p4_before = r1.periods[3].senior_ds_keur

    # Run diagnostic
    rev_dec = revenue_decomposition_schedule(tuho, eng)
    _ = build_tuho_p4_diagnostic(
        python_generation_mwh=73468.93, python_ppa_revenue_keur=4186.48,
        python_co2_revenue_keur=307.91, python_balancing_keur=587.75,
        python_net_revenue_keur=4128.30, python_opex_keur=1029.64,
        python_ebitda_keur=3156.84, python_cfads_keur=3156.84,
        python_senior_ds_keur=2045.24, python_senior_interest_keur=1179.04,
        python_senior_principal_keur=866.21, python_shl_sweep_keur=0.0,
        python_distribution_keur=0.0,
    )

    # Re-run waterfall
    r2 = WaterfallRunner(inputs=tuho, engine=eng).run(cfg)
    p4_after = r2.periods[3].senior_ds_keur
    assert abs(p4_before - p4_after) < 0.001
