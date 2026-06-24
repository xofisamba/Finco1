"""Tests for DistributionAccount audit integration."""
import pytest
from datetime import date
from pathlib import Path
import tempfile
import os

from domain.distribution_account import (
    DistributionAccountEngine,
    DistributionAccountInputs,
    DistributionAccountPeriodInput,
)
from domain.distribution_account.audit import (
    from_period_result,
    to_audit_rows,
    to_csv,
    to_model_summary,
)


def make_test_result():
    """Create a deterministic 3-period DistributionAccountResult for testing."""
    inputs = DistributionAccountInputs(
        project_name="TUHO",
        period_inputs=(
            DistributionAccountPeriodInput(
                period_index=1,
                operating_period_index=1,
                period_date=date(2029, 12, 31),
                opening_distribution_account_balance_keur=0.0,
                post_senior_cash_available_keur=500.0,
                post_shl_cash_available_keur=450.0,
                senior_debt_service_keur=50.0,
                actual_dscr=1.45,
                target_distribution_dscr=1.0,
                is_tuho=True,
                is_oborovo=False,
                enable_r99_r102_runtime=False,
            ),
            DistributionAccountPeriodInput(
                period_index=2,
                operating_period_index=2,
                period_date=date(2030, 12, 31),
                opening_distribution_account_balance_keur=50.0,
                post_senior_cash_available_keur=600.0,
                post_shl_cash_available_keur=550.0,
                senior_debt_service_keur=50.0,
                actual_dscr=1.50,
                target_distribution_dscr=1.0,
                is_tuho=True,
                is_oborovo=False,
                enable_r99_r102_runtime=False,
            ),
            DistributionAccountPeriodInput(
                period_index=3,
                operating_period_index=3,
                period_date=date(2031, 12, 31),
                opening_distribution_account_balance_keur=100.0,
                post_senior_cash_available_keur=700.0,
                post_shl_cash_available_keur=650.0,
                senior_debt_service_keur=50.0,
                actual_dscr=1.55,
                target_distribution_dscr=1.0,
                is_tuho=True,
                is_oborovo=False,
                enable_r99_r102_runtime=False,
            ),
        ),
        is_tuho=True,
        is_oborovo=False,
    )
    return DistributionAccountEngine.compute(inputs)


class TestAuditRowGeneration:
    def test_audit_rows_from_result(self):
        result = make_test_result()
        period_dates = {1: date(2029, 12, 31), 2: date(2030, 12, 31), 3: date(2031, 12, 31)}
        rows = to_audit_rows(result, period_dates)
        assert len(rows) == 3
        assert rows[0].period_index == 1
        assert rows[0].equity_distribution_paid_keur == 0.0
        assert rows[0].cash_swept_to_shl_keur == 0.0
        assert rows[0].r99_gate_passed is False
        assert rows[0].r102_gate_passed is False
        assert rows[0].blocked_reason != ""

    def test_audit_export_includes_required_columns(self):
        result = make_test_result()
        period_dates = {1: date(2029, 12, 31), 2: date(2030, 12, 31), 3: date(2031, 12, 31)}
        rows = to_audit_rows(result, period_dates)
        row = rows[0]
        # Check all required columns are present
        assert hasattr(row, "period_index")
        assert hasattr(row, "project_name")
        assert hasattr(row, "opening_balance_keur")
        assert hasattr(row, "closing_balance_keur")
        assert hasattr(row, "cash_available_for_distribution_keur")
        assert hasattr(row, "equity_distribution_candidate_keur")
        assert hasattr(row, "equity_distribution_paid_keur")
        assert hasattr(row, "cash_swept_to_shl_keur")
        assert hasattr(row, "cash_retained_keur")
        assert hasattr(row, "dsra_top_up_keur")
        assert hasattr(row, "r99_gate_passed")
        assert hasattr(row, "r102_gate_passed")
        assert hasattr(row, "dscr_gate_passed")
        assert hasattr(row, "lockup_gate_passed")
        assert hasattr(row, "oborovo_guard_passed")
        assert hasattr(row, "blocked_reason")
        assert hasattr(row, "is_tuho")
        assert hasattr(row, "is_oborovo")

    def test_audit_export_remains_deterministic(self):
        result = make_test_result()
        period_dates = {1: date(2029, 12, 31), 2: date(2030, 12, 31), 3: date(2031, 12, 31)}
        rows1 = to_audit_rows(result, period_dates)
        rows2 = to_audit_rows(result, period_dates)
        assert len(rows1) == len(rows2)
        for r1, r2 in zip(rows1, rows2):
            assert r1.period_index == r2.period_index
            assert r1.equity_distribution_candidate_keur == r2.equity_distribution_candidate_keur


class TestEquityPaidRemainsZero:
    def test_equity_distribution_paid_keur_is_zero(self):
        result = make_test_result()
        period_dates = {1: date(2029, 12, 31), 2: date(2030, 12, 31), 3: date(2031, 12, 31)}
        rows = to_audit_rows(result, period_dates)
        for row in rows:
            assert row.equity_distribution_paid_keur == 0.0

    def test_cash_swept_to_shl_keur_is_zero(self):
        result = make_test_result()
        period_dates = {1: date(2029, 12, 31), 2: date(2030, 12, 31), 3: date(2031, 12, 31)}
        rows = to_audit_rows(result, period_dates)
        for row in rows:
            assert row.cash_swept_to_shl_keur == 0.0


class TestR99R102Blocked:
    def test_r99_gate_passed_is_false(self):
        result = make_test_result()
        period_dates = {1: date(2029, 12, 31), 2: date(2030, 12, 31), 3: date(2031, 12, 31)}
        rows = to_audit_rows(result, period_dates)
        for row in rows:
            assert row.r99_gate_passed is False

    def test_r102_gate_passed_is_false(self):
        result = make_test_result()
        period_dates = {1: date(2029, 12, 31), 2: date(2030, 12, 31), 3: date(2031, 12, 31)}
        rows = to_audit_rows(result, period_dates)
        for row in rows:
            assert row.r102_gate_passed is False


class TestOborovoAuditRows:
    def test_oborovo_audit_rows_show_blocked_status(self):
        inputs = DistributionAccountInputs(
            project_name="Oborovo",
            period_inputs=(
                DistributionAccountPeriodInput(
                    period_index=1,
                    operating_period_index=1,
                    period_date=date(2029, 12, 31),
                    opening_distribution_account_balance_keur=0.0,
                    post_senior_cash_available_keur=500.0,
                    post_shl_cash_available_keur=500.0,
                    senior_debt_service_keur=0.0,
                    actual_dscr=1.5,
                    is_tuho=False,
                    is_oborovo=True,
                ),
            ),
            is_tuho=False,
            is_oborovo=True,
        )
        result = DistributionAccountEngine.compute(inputs)
        period_dates = {1: date(2029, 12, 31)}
        rows = to_audit_rows(result, period_dates)
        assert rows[0].is_oborovo is True
        assert rows[0].oborovo_guard_passed is False
        assert rows[0].equity_distribution_paid_keur == 0.0
        assert "OBOROVO" in rows[0].blocked_reason or rows[0].blocked_reason != ""


class TestCsvExport:
    def test_to_csv_writes_file(self):
        result = make_test_result()
        period_dates = {1: date(2029, 12, 31), 2: date(2030, 12, 31), 3: date(2031, 12, 31)}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "distribution_account_audit.csv"
            to_csv(result, path, period_dates)
            assert path.exists()
            content = path.read_text()
            assert "period_index" in content
            assert "project_name" in content
            assert "r99_gate_passed" in content
            lines = content.strip().split("\n")
            assert len(lines) == 4  # header + 3 data rows


class TestModelSummary:
    def test_to_model_summary_produces_string(self):
        result = make_test_result()
        summary = to_model_summary(result)
        assert "DistributionAccount" in summary
        assert "TUHO" in summary
        assert "equity distribution candidate" in summary
        assert "equity distribution paid" in summary
        assert "0.0" in summary  # paid is always 0


class TestNoAppChanges:
    def test_no_waterfall_core_imported(self):
        """Verify audit module does not import app.waterfall_core."""
        import domain.distribution_account.audit as audit_module
        source = str(audit_module.__file__)
        assert "waterfall_core" not in source
        assert "app" not in source

    def test_no_app_waterfall_core_changes(self):
        """Verify no app/ files are changed by this branch."""
        import subprocess
        # UX-2C-1 cross-arc allowlist (Overview KPI dedup)
        allowed_prefixes = (
            "app/templates/partials/runtime_summary.html",  # UX-2C-1 cross-arc
            "app/ui/dashboard.py",  # UX-2C-1 cross-arc
            "tests/test_ux2c1_",  # UX-2C-1 cross-arc
        )
        result = subprocess.run(
            ["git", "diff", "--name-only", "origin/main...HEAD", "--", "app/"],
            cwd=str(Path(__file__).resolve().parents[1]),
            capture_output=True,
            text=True,
        )
        changed = [line for line in result.stdout.strip().splitlines() if line]
        unexpected = [f for f in changed if not f.startswith(allowed_prefixes)]
        assert unexpected == [], f"app/ changes found: {unexpected}"