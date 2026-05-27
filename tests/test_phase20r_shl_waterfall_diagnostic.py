"""Phase 20R: SHL waterfall partial-pay / PIK / sweep investigation — diagnostics only."""
from __future__ import annotations

import pytest

from app.project_factories import create_default_tuho_wind1, create_default_oborovo
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.diagnostics.shl_waterfall import (
    ShlWaterfallDiagnosticRow,
    ShlWaterfallDiagnosticReport,
    build_shl_diagnostic_row,
)
from domain.waterfall.shl_engine import compute_shl_period_v3


def _run_tuho():
    tuho = create_default_tuho_wind1()
    eng = _build_period_engine(tuho)
    r = WaterfallRunner(inputs=tuho, engine=eng).run(WaterfallRunConfig.from_inputs(tuho, eng))
    return tuho, eng, r


def _run_oborovo():
    obor = create_default_oborovo()
    eng = _build_period_engine(obor)
    r = WaterfallRunner(inputs=obor, engine=eng).run(WaterfallRunConfig.from_inputs(obor, eng))
    return obor, eng, r


class TestShlWaterfallDiagnostics:
    """Verify SHL waterfall diagnostics capture all required fields and flag gaps."""

    def test_tuho_p4_has_all_required_fields(self):
        """TUHO P4 diagnostic row contains all 22 required fields."""
        tuho, eng, r = _run_tuho()
        wp = r.periods[3]
        meta = eng.periods()[3]
        period_rate = tuho.financing.shl_rate * meta.day_fraction
        annual_rate = tuho.financing.shl_rate
        wht = getattr(tuho.financing, "shl_wht_rate", 0.0)
        annual_threshold = wp.shl_balance_keur * annual_rate

        row = build_shl_diagnostic_row(
            project_code="TUHO",
            period_index=3,
            opening_balance=wp.shl_balance_keur,
            period_rate=period_rate,
            cf_for_shl=wp.fcf_for_shl_keur,
            wht_rate=wht,
            shl_interest_keur=wp.shl_interest_keur,
            shl_principal_keur=wp.shl_principal_keur,
            distribution_keur=wp.distribution_keur,
            pik_switch_triggered=wp.fcf_for_shl_keur > annual_threshold,
            annual_shl_rate=annual_rate,
            excel_principal_sweep_keur=982.99,
        )

        required_fields = [
            "project_code", "period_index", "cash_before_shl_keur",
            "opening_shl_balance_keur", "shl_interest_due_gross_keur",
            "shl_interest_due_net_keur", "wht_on_shl_interest_keur",
            "interest_paid_cash_keur", "unpaid_interest_keur",
            "pik_interest_keur", "cash_after_interest_keur",
            "principal_sweep_keur", "closing_shl_balance_keur",
            "net_shl_cashflow_keur", "fcf_for_dividends_keur",
            "distribution_keur", "pik_switch_triggered",
            "trigger_used_explanation", "likely_cause",
            "excel_principal_sweep_keur", "excel_distribution_keur",
            "excel_available_cash",
        ]
        row_attrs = list(ShlWaterfallDiagnosticRow.__annotations__.keys())
        for field in required_fields:
            assert field in row_attrs, f"Missing field: {field}"

        assert row.status == "FAIL"

    def test_oborovo_p4_has_all_required_fields(self):
        """Oborovo P4 diagnostic row contains all 22 required fields."""
        obor, eng, r = _run_oborovo()
        wp = r.periods[3]
        meta = eng.periods()[3]
        period_rate = obor.financing.shl_rate * meta.day_fraction
        annual_rate = obor.financing.shl_rate
        annual_threshold = wp.shl_balance_keur * annual_rate

        row = build_shl_diagnostic_row(
            project_code="Oborovo",
            period_index=3,
            opening_balance=wp.shl_balance_keur,
            period_rate=period_rate,
            cf_for_shl=wp.fcf_for_shl_keur,
            wht_rate=0.0,
            shl_interest_keur=wp.shl_interest_keur,
            shl_principal_keur=wp.shl_principal_keur,
            distribution_keur=wp.distribution_keur,
            pik_switch_triggered=wp.fcf_for_shl_keur > annual_threshold,
            annual_shl_rate=annual_rate,
        )

        assert row.status == "FAIL"  # sweep=0 vs 340.54, dist=64.97 vs 0

    def test_tuho_p4_flags_sweep_gap(self):
        """TUHO P4: Python sweep=0, Excel sweep≈982.99 → FAIL."""
        tuho, eng, r = _run_tuho()
        wp = r.periods[3]
        meta = eng.periods()[3]
        period_rate = tuho.financing.shl_rate * meta.day_fraction
        annual_rate = tuho.financing.shl_rate
        annual_threshold = wp.shl_balance_keur * annual_rate

        row = build_shl_diagnostic_row(
            project_code="TUHO",
            period_index=3,
            opening_balance=wp.shl_balance_keur,
            period_rate=period_rate,
            cf_for_shl=wp.fcf_for_shl_keur,
            wht_rate=getattr(tuho.financing, "shl_wht_rate", 0.0),
            shl_interest_keur=wp.shl_interest_keur,
            shl_principal_keur=wp.shl_principal_keur,
            distribution_keur=wp.distribution_keur,
            pik_switch_triggered=wp.fcf_for_shl_keur > annual_threshold,
            annual_shl_rate=annual_rate,
            excel_principal_sweep_keur=982.99,
        )

        assert row.principal_sweep_keur == 0.0
        assert row.excel_principal_sweep_keur == 982.99
        assert abs(row.principal_sweep_keur - row.excel_principal_sweep_keur) > 1.0
        assert row.status == "FAIL"

    def test_oborovo_p4_flags_distribution_leakage(self):
        """Oborovo P4: Python dist≈64.97, Excel dist=0 → distribution leakage → FAIL."""
        obor, eng, r = _run_oborovo()
        wp = r.periods[3]
        meta = eng.periods()[3]
        period_rate = obor.financing.shl_rate * meta.day_fraction
        annual_rate = obor.financing.shl_rate
        annual_threshold = wp.shl_balance_keur * annual_rate

        row = build_shl_diagnostic_row(
            project_code="Oborovo",
            period_index=3,
            opening_balance=wp.shl_balance_keur,
            period_rate=period_rate,
            cf_for_shl=wp.fcf_for_shl_keur,
            wht_rate=0.0,
            shl_interest_keur=wp.shl_interest_keur,
            shl_principal_keur=wp.shl_principal_keur,
            distribution_keur=wp.distribution_keur,
            pik_switch_triggered=wp.fcf_for_shl_keur > annual_threshold,
            annual_shl_rate=annual_rate,
            excel_principal_sweep_keur=340.54,
            excel_distribution_keur=0.0,
        )

        assert abs(row.distribution_keur - 64.97) < 1.0
        assert row.excel_distribution_keur == 0.0
        assert row.status == "FAIL"

    def test_oborovo_p4_partial_pay_reconciles(self):
        """Oborovo P4 partial-pay interest_paid = min(net_int, cf_for_shl) reconciles."""
        obor, eng, r = _run_oborovo()
        wp = r.periods[3]
        meta = eng.periods()[3]
        period_rate = obor.financing.shl_rate * meta.day_fraction
        shl_bal = wp.shl_balance_keur
        cf = wp.fcf_for_shl_keur
        gross_int = shl_bal * period_rate
        net_int = gross_int

        interest_paid = min(net_int, cf)
        assert abs(interest_paid - 583.81) < 1.0, f"Expected ~583.81, got {interest_paid:.2f}"
        remaining = cf - interest_paid
        assert remaining > 0, "Oborovo P4 has residual cash after interest"
        # Residual (66.59) should theoretically sweep SHL if Excel route was used

    def test_tuho_p4_trigger_is_false_annual_threshold(self):
        """Confirm TUHO P4 pik_switch_triggered=False using annual threshold."""
        tuho, eng, r = _run_tuho()
        wp = r.periods[3]
        annual_threshold = wp.shl_balance_keur * tuho.financing.shl_rate

        assert not (wp.fcf_for_shl_keur > annual_threshold), \
            f"Expected trigger False: cf({wp.fcf_for_shl_keur:.2f}) > annual_threshold({annual_threshold:.2f})"
        assert wp.fcf_for_shl_keur < annual_threshold
        assert wp.shl_principal_keur == 0.0

    def test_shl_engine_partial_pay_is_properly_implemented(self):
        """SHL engine v3 correctly uses gross interest for PIK = gross - cash_paid."""
        shl_engine = compute_shl_period_v3

        # When available CF < net interest, partial payment triggers PIK
        # Test: balance=1000, rate=0.10 (period), cf=50, net_int=100
        # interest_paid = min(100, 50) = 50
        # pik = gross_int - interest_paid = 100 - 50 = 50  ← CORRECT (not net-int - cash)
        # wrong approach: pik = net_int - cash_paid = 100 - 50 = 50  ← coincides but conceptually wrong
        res = shl_engine(
            shl_balance=1000.0,
            shl_rate_per_period=0.10,
            cf_available=50.0,
            method="pik_then_sweep",
            wht_rate=0.0,
            pik_switch_triggered=False,
            is_final_period=False,
        )
        assert res.interest_paid_keur == 50.0
        assert res.pik_addition_keur == 50.0  # gross - cash_paid = 100 - 50 = 50
        assert res.principal_keur == 0.0
        assert res.new_balance_keur == 1000.0 + 50.0

    def test_shl_engine_sweep_cutoff_is_correct(self):
        """SHL engine SWEEP phase principal is capped at remaining CF after interest."""
        shl_engine = compute_shl_period_v3

        # In SWEEP phase: available CF should first pay interest, then principal
        # balance=1000, rate=0.10, cf=150 (more than period interest, less than full)
        # interest_paid = min(100, 150) = 100
        # remaining = 150 - 100 = 50
        # principal = min(50, 1000) = 50
        # pik = gross - interest_paid = 0 (since cash covers full interest)
        res = shl_engine(
            shl_balance=1000.0,
            shl_rate_per_period=0.10,
            cf_available=150.0,
            method="pik_then_sweep",
            wht_rate=0.0,
            pik_switch_triggered=True,
            is_final_period=False,
        )
        assert res.interest_paid_keur == 100.0
        assert res.pik_addition_keur == 0.0
        assert res.principal_keur == 50.0

    def test_tuho_first_dividend_period_is_35(self):
        """TUHO first non-zero distribution at period 35 (P35) when SHL balance→0."""
        tuho, eng, r = _run_tuho()
        for i, wp in enumerate(r.periods):
            if wp.distribution_keur > 1.0:
                assert i == 35, f"Expected first dividend at P35, found P{i}"
                break
        else:
            pytest.fail("No non-zero distribution found for TUHO")

    def test_oborovo_sweep_and_distribution_pattern(self):
        """Oborovo: distribution appears in P0 while SHL is alive — indicates routing gap."""
        obor, eng, r = _run_oborovo()

        # Distribution present while SHL balance > 0
        wp0 = r.periods[0]
        assert wp0.shl_balance_keur > 0.01, "Oborovo SHL should be alive in P0"
        assert wp0.distribution_keur > 1.0, "Oborovo P0 has non-zero distribution while SHL alive"

        # SWEEP is 0 for all periods
        for i, wp in enumerate(r.periods):
            if wp.shl_balance_keur > 0.01:
                assert wp.shl_principal_keur == 0.0, f"Oborovo P{i}: sweep should be 0"

    def test_report_failed_rows(self):
        """ShlWaterfallDiagnosticReport.failed_rows() returns FAIL rows only."""
        tuho, eng, r = _run_tuho()
        wp3 = r.periods[3]
        meta = eng.periods()[3]
        period_rate = tuho.financing.shl_rate * meta.day_fraction
        annual = tuho.financing.shl_rate
        annual_threshold = wp3.shl_balance_keur * annual

        row3 = build_shl_diagnostic_row(
            project_code="TUHO", period_index=3,
            opening_balance=wp3.shl_balance_keur,
            period_rate=period_rate,
            cf_for_shl=wp3.fcf_for_shl_keur,
            wht_rate=getattr(tuho.financing, "shl_wht_rate", 0.0),
            shl_interest_keur=wp3.shl_interest_keur,
            shl_principal_keur=wp3.shl_principal_keur,
            distribution_keur=wp3.distribution_keur,
            pik_switch_triggered=wp3.fcf_for_shl_keur > annual_threshold,
            annual_shl_rate=annual,
            excel_principal_sweep_keur=982.99,
            excel_available_cash=2094.59,  # estimated from Excel CF
        )

        report = ShlWaterfallDiagnosticReport(project_code="TUHO", rows=[row3])
        assert len(report.failed_rows()) == 1
        assert report.period_row(3) is not None
        assert report.period_row(99) is None

    def test_trigger_all_or_nothing_identified_as_likely_cause(self):
        """Diagnostic 'likely_cause' field mentions the annual-threshold trigger issue."""
        tuho, eng, r = _run_tuho()
        wp3 = r.periods[3]
        meta = eng.periods()[3]
        period_rate = tuho.financing.shl_rate * meta.day_fraction

        row = build_shl_diagnostic_row(
            project_code="TUHO", period_index=3,
            opening_balance=wp3.shl_balance_keur,
            period_rate=period_rate,
            cf_for_shl=wp3.fcf_for_shl_keur,
            wht_rate=0.0,
            shl_interest_keur=wp3.shl_interest_keur,
            shl_principal_keur=wp3.shl_principal_keur,
            distribution_keur=wp3.distribution_keur,
            pik_switch_triggered=wp3.fcf_for_shl_keur > (wp3.shl_balance_keur * tuho.financing.shl_rate),
            annual_shl_rate=tuho.financing.shl_rate,
        )

        cause = row.likely_cause.lower()
        assert "trigger" in cause or "threshold" in cause or "annual" in cause

    def test_runtime_no_changes_in_phase20r_diagnostic(self):
        """Confirm no runtime formula changes are introduced in Phase 20R diagnostics."""
        tuho, eng, r = _run_tuho()
        obor, eng_o, r_o = _run_oborovo()

        # TUHO P4: sweep should be 0, interest should be unchanged
        wp_t = r.periods[3]
        assert wp_t.shl_principal_keur == 0.0  # no principal in P4

        # Oborovo P4: sweep should be 0
        wp_o = r_o.periods[3]
        assert wp_o.shl_principal_keur == 0.0

        # Verify distributions unchanged from Phase 20Q baseline
        assert abs(wp_t.distribution_keur - 0.0) < 1.0  # TUHO P4 dist = 0
        assert abs(wp_o.distribution_keur - 64.97) < 1.0  # Oborovo P4 dist ≈ 64.97
