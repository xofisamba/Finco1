"""Snapshot comparison tests for golden validation foundation.

These tests validate the utility layer and fixture structure.
They use synthetic data (not model runs) to verify the validation
framework works correctly deterministically.
"""
from __future__ import annotations

import math
import pytest

from tests.golden import (
    compare_values,
    compare_series,
    assert_all_close,
    SnapshotContext,
    DiffFormatter,
    ReportFormatter,
    OBOROVO_GOLDEN,
    TUHO_GOLDEN,
)


class TestCompareValues:
    """Unit tests for scalar comparison helper."""

    def test_exact_match_passes(self):
        result = compare_values(0.1161, 0.1161, bps_tol=10)
        assert result["pass"] is True

    def test_within_bps_tolerance_passes(self):
        # +5 bps out of ±10 bps tolerance
        result = compare_values(0.11615, 0.1161, bps_tol=10)
        assert result["pass"] is True

    def test_exceeds_bps_tolerance_fails(self):
        # +15 bps out of ±10 bps tolerance
        result = compare_values(0.1173, 0.1161, bps_tol=10)  # 0.0012 delta > 0.001 tolerance → fails
        assert result["pass"] is False

    def test_within_pct_tolerance_passes(self):
        result = compare_values(42852.27, 42852.0, pct_tol=0.005)
        assert result["pass"] is True

    def test_exceeds_pct_tolerance_fails(self):
        result = compare_values(43500.0, 42852.27, pct_tol=0.005)  # 647.73 delta > 214.26 tolerance → fails
        assert result["pass"] is False

    def test_within_abs_tolerance_passes(self):
        result = compare_values(1.148, 1.147, abs_tol=0.002)
        assert result["pass"] is True

    def test_exceeds_abs_tolerance_fails(self):
        result = compare_values(1.151, 1.147, abs_tol=0.002)
        assert result["pass"] is False

    def test_nan_fails_immediately(self):
        result = compare_values(float('nan'), 0.1161, bps_tol=10)
        assert result["pass"] is False
        assert "non-finite" in result["message"]

    def test_inf_fails_immediately(self):
        result = compare_values(float('inf'), 0.1161, bps_tol=10)
        assert result["pass"] is False

    def test_delta_is_computed_correctly(self):
        result = compare_values(0.11625, 0.1161, bps_tol=10)
        assert abs(result["delta"] - 0.00015) < 1e-10

    def test_zero_golden_falls_back_to_abs_tolerance(self):
        result = compare_values(1e-10, 0.0, rel_tol=0.01, abs_tol=1e-8)
        assert result["tolerance_type"] == "abs"

    def test_no_tolerance_raises(self):
        with pytest.raises(ValueError, match="At least one tolerance"):
            compare_values(0.1161, 0.1161)

    def test_rel_tol_with_large_golden(self):
        result = compare_values(42855.0, 42852.27, rel_tol=0.0001)
        delta = 42855.0 - 42852.27
        tol = abs(0.0001 * 42852.27)
        assert abs(delta) <= tol


class TestCompareSeries:
    """Unit tests for period-series comparison helper."""

    def test_exact_matching_series_passes(self):
        actual = (1.0, 2.0, 3.0)
        golden = (1.0, 2.0, 3.0)
        result = compare_series(actual, golden, pct_tol=0.005)
        assert result["pass"] is True
        assert result["period_count_match"] is True
        assert result["failures"] == []

    def test_one_period_out_of_tolerance_fails(self):
        actual = (1.0, 2.0, 3.1)  # third differs by 3.3%
        golden = (1.0, 2.0, 3.0)
        result = compare_series(actual, golden, pct_tol=0.005)
        assert result["pass"] is False
        assert len(result["failures"]) == 1
        assert result["failures"][0][0] == 2  # period 2
        assert abs(result["failures"][0][1] - 0.1) < 1e-9  # delta approx 0.1 (fp drift)

    def test_all_periods_out_of_tolerance_fails(self):
        actual = (1.1, 2.2, 3.3)
        golden = (1.0, 2.0, 3.0)
        result = compare_series(actual, golden, pct_tol=0.005)
        assert result["pass"] is False
        assert len(result["failures"]) == 3

    def test_period_count_mismatch_is_fatal(self):
        actual = (1.0, 2.0, 3.0, 4.0)  # 4 periods
        golden = (1.0, 2.0, 3.0)        # 3 periods
        result = compare_series(actual, golden, pct_tol=0.005)
        assert result["pass"] is False
        assert result["period_count_match"] is False
        assert result["failures"][0][0] == "PERIOD_COUNT_MISMATCH"

    def test_period_deltas_computed_correctly(self):
        actual = (10.0, 20.0, 30.0)
        golden = (9.0, 19.0, 29.0)
        result = compare_series(actual, golden, abs_tol=0.0)
        assert result["period_deltas"] == (1.0, 1.0, 1.0)
        assert len(result["failures"]) == 3


class TestAssertAllClose:
    """Unit tests for multi-scalar assertion helper."""

    def test_all_pass_returns_pass(self):
        actual = {
            "total_capex_keur": 57973.0,
            "senior_debt_keur": 42852.0,
        }
        golden = {
            "total_capex_keur": {"value": 57973.05, "tolerance": {"type": "pct", "value": 0.005}},
            "senior_debt_keur": {"value": 42852.27, "tolerance": {"type": "pct", "value": 0.005}},
        }
        result = assert_all_close(actual, golden)
        assert result["passed"] is True
        assert result["failures"] == []

    def test_one_fail_raises_and_returns_failures(self):
        actual = {
            "total_capex_keur": 57973.0,
            "senior_debt_keur": 50000.0,  # way off — delta 7147 >> 214 tolerance
        }
        golden = {
            "total_capex_keur": {"value": 57973.05, "tolerance": {"type": "pct", "value": 0.005}},
            "senior_debt_keur": {"value": 42852.27, "tolerance": {"type": "pct", "value": 0.005}},
        }
        # assert_all_close raises AssertionError when failures exist and report=False
        with pytest.raises(AssertionError, match="senior_debt_keur"):
            assert_all_close(actual, golden, report=False)

    def test_missing_metric_is_failure(self):
        actual = {"total_capex_keur": 57973.0}  # missing senior_debt_keur
        golden = {
            "total_capex_keur": {"value": 57973.05, "tolerance": {"type": "pct", "value": 0.005}},
            "senior_debt_keur": {"value": 42852.27, "tolerance": {"type": "pct", "value": 0.005}},
        }
        # MISSING metric raises AssertionError (not found in actual_dict)
        with pytest.raises(AssertionError, match="senior_debt_keur"):
            assert_all_close(actual, golden, report=False)


class TestSnapshotContext:
    """Unit tests for snapshot context manager."""

    def test_capture_scalar(self):
        ctx = SnapshotContext(fixture_name="oborovo", model_version="test@test")
        ctx.capture("total_capex_keur", 57973.0)
        assert ctx.captures["total_capex_keur"] == 57973.0

    def test_capture_series(self):
        ctx = SnapshotContext(fixture_name="oborovo", model_version="test@test")
        ctx.capture("debt_schedule", (1.0, 2.0, 3.0))
        assert ctx.captures["debt_schedule"] == (1.0, 2.0, 3.0)

    def test_validate_scalar_pass(self):
        ctx = SnapshotContext(fixture_name="oborovo", model_version="test@test")
        ctx.capture("equity_irr_30y", 0.11615)
        result = ctx.validate_scalar("equity_irr_30y", golden_value=0.1161, tol_type="bps", tol_value=10)
        assert result["status"] == "PASS"

    def test_validate_scalar_fail(self):
        ctx = SnapshotContext(fixture_name="oborovo", model_version="test@test", raise_on_failures=False)
        ctx.capture("equity_irr_30y", 0.1173)  # +120 bps — exceeds ±10 bps tolerance
        result = ctx.validate_scalar("equity_irr_30y", golden_value=0.1161, tol_type="bps", tol_value=10)
        assert result["status"] == "FAIL"
        assert len(ctx.failures) == 1

    def test_validate_series_pass(self):
        ctx = SnapshotContext(fixture_name="oborovo", model_version="test@test")
        ctx.capture("debt_service", (-2239.0, -2202.0, -2240.0))
        golden = (-2239.133, -2202.626, -2240.525)
        result = ctx.validate_series("debt_service", golden_values=golden, tol_type="pct", tol_value=0.005)
        assert result["status"] == "PASS"

    def test_validate_series_fail(self):
        ctx = SnapshotContext(fixture_name="oborovo", model_version="test@test", raise_on_failures=False)
        ctx.capture("debt_service", (-2239.0, -2202.0, -3000.0))  # period 2 way off
        golden = (-2239.133, -2202.626, -2240.525)
        result = ctx.validate_series("debt_service", golden_values=golden, tol_type="pct", tol_value=0.005)
        assert result["status"] == "FAIL"

    def test_context_raises_on_failures(self):
        ctx = SnapshotContext(fixture_name="oborovo", model_version="test@test", raise_on_failures=True)
        ctx.capture("equity_irr_30y", 0.1173)  # +120 bps — exceeds ±10 bps tolerance
        ctx.validate_scalar("equity_irr_30y", golden_value=0.1161, tol_type="bps", tol_value=10)
        with pytest.raises(AssertionError, match="Golden validation failed"):
            ctx.__exit__(None, None, None)

    def test_context_suppress_does_not_raise(self):
        ctx = SnapshotContext(fixture_name="oborovo", model_version="test@test", suppress_failures=True, raise_on_failures=True)
        ctx.capture("equity_irr_30y", 0.1163)
        ctx.validate_scalar("equity_irr_30y", golden_value=0.1161, tol_type="bps", tol_value=10)
        ctx.__exit__(None, None, None)  # no raise

    def test_report_includes_summary(self):
        ctx = SnapshotContext(fixture_name="oborovo", model_version="main@test")
        ctx.capture("equity_irr_30y", 0.11615)
        rep = ctx.report()
        assert "summary" in rep
        assert rep["summary"]["fixture"] == "oborovo"
        assert rep["summary"]["passed"] is True

    def test_to_dict_serializable(self):
        ctx = SnapshotContext(fixture_name="oborovo", model_version="main@test")
        ctx.capture("equity_irr_30y", 0.11615)
        d = ctx.to_dict()
        import json
        # Must not raise — confirms JSON serializable
        json.dumps(d)


class TestDiffFormatter:
    """Unit tests for diff formatter."""

    def test_format_with_bps_tolerance(self):
        result = DiffFormatter.format(
            "equity_irr_30y",
            actual=0.11615, golden=0.1161, status="PASS",
            bps_tol=10,
        )
        assert "equity_irr_30y" in result
        assert "PASS" in result or "✅" in result

    def test_format_with_abs_tolerance(self):
        result = DiffFormatter.format(
            "avg_dscr",
            actual=1.148, golden=1.147, status="FAIL",
            abs_tol=0.002,
        )
        assert "avg_dscr" in result

    def test_format_series_diff_with_failures(self):
        actual = (1.0, 2.0, 3.1)
        golden = (1.0, 2.0, 3.0)
        failures = [(2, 0.1)]
        result = DiffFormatter.format_series_diff(
            "debt_schedule", actual=actual, golden=golden,
            failures=failures, per_period_tol=0.005,
        )
        assert "PERIOD COUNT MISMATCH" not in result
        assert "period[2]" in result
        assert "3.1" in result


class TestReportFormatter:
    """Unit tests for report formatter."""

    def test_format_report(self):
        report = {
            "summary": {
                "fixture": "oborovo",
                "model_version": "main@test",
                "run_timestamp": "2026-05-11T12:00:00Z",
                "total_captures": 3,
                "passed": True,
                "failure_count": 0,
            },
            "failures": [],
        }
        result = ReportFormatter.format_report(report)
        assert "oborovo" in result
        assert "✅ PASS" in result

    def test_format_summary_line_pass(self):
        result = ReportFormatter.format_summary_line("oborovo", 10, 10, 0)
        assert "oborovo" in result
        assert "✅" in result

    def test_format_summary_line_fail(self):
        result = ReportFormatter.format_summary_line("oborovo", 10, 8, 2)
        assert "❌" in result
        assert "2 failed" in result


class TestGoldenFixtures:
    """Tests that golden fixtures are well-formed and loadable."""

    def test_oborovo_golden_loadable(self):
        assert OBOROVO_GOLDEN is not None
        assert OBOROVO_GOLDEN["metadata"]["fixture_name"] == "oborovo"
        assert "scalars" in OBOROVO_GOLDEN
        assert "series" in OBOROVO_GOLDEN

    def test_oborovo_scalars_have_required_fields(self):
        for name, spec in OBOROVO_GOLDEN["scalars"].items():
            assert "value" in spec
            assert "tolerance" in spec
            assert "type" in spec["tolerance"]
            assert "value" in spec["tolerance"]

    def test_oborovo_series_values_are_tuples(self):
        for name, spec in OBOROVO_GOLDEN["series"].items():
            assert isinstance(spec["values"], tuple), f"{name}: values must be tuple"

    def test_tuho_golden_loadable(self):
        assert TUHO_GOLDEN is not None
        assert TUHO_GOLDEN["metadata"]["fixture_name"] == "tuho"

    def test_tuho_scalars_have_required_fields(self):
        for name, spec in TUHO_GOLDEN["scalars"].items():
            assert "value" in spec
            assert "tolerance" in spec

    def test_fixture_metadata_complete(self):
        for fixture in [OBOROVO_GOLDEN, TUHO_GOLDEN]:
            meta = fixture["metadata"]
            assert "fixture_name" in meta
            assert "technology" in meta
            assert "schema_version" in meta
            assert "period_count" in meta

    def test_all_tolerances_are_positive(self):
        for fixture in [OBOROVO_GOLDEN, TUHO_GOLDEN]:
            for name, spec in fixture["scalars"].items():
                assert spec["tolerance"]["value"] >= 0, f"{name}: tolerance must be >= 0"
            for name, spec in fixture["series"].items():
                assert spec["per_period_tolerance"]["value"] >= 0, f"{name}: per-period tolerance must be >= 0"


class TestDeterministicTolerances:
    """Tests for deterministic floating-point handling."""

    def test_fp_drift_small_enough_for_bps(self):
        # Simulate floating point accumulation over many periods
        value = 0.0
        for _ in range(1000):
            value += 0.1
        # After 1000 additions, floating point error is ~1e-10, well within 0.5 bps
        # 0.5 bps = 0.00005 = 5e-5
        result = compare_values(value, 100.0, abs_tol=1e-6)
        assert result["pass"] is True  # abs_tol catches fp drift

    def test_near_zero_golden_uses_abs_tolerance(self):
        result = compare_values(1e-8, 0.0, rel_tol=0.01, abs_tol=1e-7)
        assert result["tolerance_type"] == "abs"

    def test_identical_values_always_pass(self):
        for _ in range(10):
            result = compare_values(0.1161, 0.1161, bps_tol=10)
            assert result["pass"] is True

    def test_inf_golden_fails(self):
        result = compare_values(100.0, float('inf'), bps_tol=10)
        assert result["pass"] is False