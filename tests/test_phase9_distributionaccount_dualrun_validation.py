"""Phase 9B — DistributionAccount dual-run validation tests.

DUAL-RUN VALIDATION — NO RUNTIME ROUTING.
Validates dual-run comparison logic, divergence classification, and invariants.

R99/R102: BLOCKED — no promotion in Phase B.
"""

import pytest
from datetime import date
from pathlib import Path

from domain.distribution_account.dualrun_validation import (
    DualRunPeriodResult,
    DualRunResult,
    classify_delta,
    run_dual_validation,
)
from domain.distribution_account.inputs import (
    DistributionAccountInputs,
    DistributionAccountPeriodInput,
    R99R102GateInputs,
)
from domain.distribution_account.result import BLOCKED_REASONS
from domain.distribution_account.engine import DistributionAccountEngine


# ---------------------------------------------------------------------------
# DualRunPeriodResult construction
# ---------------------------------------------------------------------------

class TestDualRunPeriodResult:
    def test_identical_zero_delta(self):
        r = DualRunPeriodResult(
            period_index=1,
            operating_period_index=1,
            runtime_distribution_keur=1000.0,
            da_paid_distribution_keur=1000.0,
            delta_keur=0.0,
            absolute_delta_keur=0.0,
            delta_pct=0.0,
            classification="IDENTICAL",
            gates_passed=True,
            r99_blocked=False,
            r102_blocked=False,
            dscr_passed=True,
            lockup_passed=True,
            cash_passed=True,
            oborovo_passed=True,
            blocked_reason="",
            runtime_authoritative=True,
        )
        assert r.runtime_distribution_keur == 1000.0
        assert r.runtime_authoritative is True

    def test_r99_blocked_classification(self):
        r = DualRunPeriodResult(
            period_index=2,
            operating_period_index=2,
            runtime_distribution_keur=500.0,
            da_paid_distribution_keur=0.0,
            delta_keur=-500.0,
            absolute_delta_keur=500.0,
            delta_pct=100.0,
            classification="EXPECTED_GATE_DIFFERENCE",
            gates_passed=False,
            r99_blocked=True,
            r102_blocked=True,
            dscr_passed=False,
            lockup_passed=True,
            cash_passed=True,
            oborovo_passed=True,
            blocked_reason=BLOCKED_REASONS["R99_BLOCKED"],
            runtime_authoritative=True,
        )
        assert r.r99_blocked is True
        assert r.classification == "EXPECTED_GATE_DIFFERENCE"


# ---------------------------------------------------------------------------
# classify_delta — divergence classification correctness
# ---------------------------------------------------------------------------

class TestClassifyDelta:
    def test_identical_exact_zero(self):
        result = classify_delta(
            delta_keur=0.0, runtime_dist=1000.0,
            gates_passed=True, r99_blocked=False, r102_blocked=False,
            dscr_passed=True, lockup_passed=True, cash_passed=True,
        )
        assert result == "IDENTICAL"

    def test_identical_near_zero(self):
        result = classify_delta(
            delta_keur=0.0001, runtime_dist=1000.0,
            gates_passed=True, r99_blocked=False, r102_blocked=False,
            dscr_passed=True, lockup_passed=True, cash_passed=True,
        )
        assert result == "IDENTICAL"

    def test_rounding_within_threshold(self):
        result = classify_delta(
            delta_keur=0.5, runtime_dist=1000.0,
            gates_passed=True, r99_blocked=False, r102_blocked=False,
            dscr_passed=True, lockup_passed=True, cash_passed=True,
        )
        assert result == "ROUNDING"

    def test_rounding_at_threshold(self):
        result = classify_delta(
            delta_keur=1.0, runtime_dist=1000.0,
            gates_passed=True, r99_blocked=False, r102_blocked=False,
            dscr_passed=True, lockup_passed=True, cash_passed=True,
        )
        assert result == "ROUNDING"

    def test_rounding_above_threshold_is_blocking(self):
        result = classify_delta(
            delta_keur=1.5, runtime_dist=1000.0,
            gates_passed=True, r99_blocked=False, r102_blocked=False,
            dscr_passed=True, lockup_passed=True, cash_passed=True,
        )
        # > 1 kEUR threshold when gates pass → BLOCKING (not UNEXPECTED)
        assert result == "BLOCKING"

    def test_expected_gate_diff_r99_blocked(self):
        result = classify_delta(
            delta_keur=-500.0, runtime_dist=500.0,
            gates_passed=False, r99_blocked=True, r102_blocked=False,
            dscr_passed=True, lockup_passed=True, cash_passed=True,
        )
        assert result == "EXPECTED_GATE_DIFFERENCE"

    def test_expected_gate_diff_r102_blocked(self):
        result = classify_delta(
            delta_keur=-500.0, runtime_dist=500.0,
            gates_passed=False, r99_blocked=False, r102_blocked=True,
            dscr_passed=True, lockup_passed=True, cash_passed=True,
        )
        assert result == "EXPECTED_GATE_DIFFERENCE"

    def test_expected_gate_diff_dscr_failed(self):
        result = classify_delta(
            delta_keur=-500.0, runtime_dist=500.0,
            gates_passed=False, r99_blocked=False, r102_blocked=False,
            dscr_passed=False, lockup_passed=True, cash_passed=True,
        )
        assert result == "EXPECTED_GATE_DIFFERENCE"

    def test_expected_gate_diff_lockup_failed(self):
        result = classify_delta(
            delta_keur=-500.0, runtime_dist=500.0,
            gates_passed=False, r99_blocked=False, r102_blocked=False,
            dscr_passed=True, lockup_passed=False, cash_passed=True,
        )
        assert result == "EXPECTED_GATE_DIFFERENCE"

    def test_expected_gate_diff_cash_failed(self):
        result = classify_delta(
            delta_keur=-500.0, runtime_dist=500.0,
            gates_passed=False, r99_blocked=False, r102_blocked=False,
            dscr_passed=True, lockup_passed=True, cash_passed=False,
        )
        assert result == "EXPECTED_GATE_DIFFERENCE"

    def test_unexpected_gates_pass_large_delta(self):
        # 5% difference when gates pass
        result = classify_delta(
            delta_keur=50.0, runtime_dist=1000.0,
            gates_passed=True, r99_blocked=False, r102_blocked=False,
            dscr_passed=True, lockup_passed=True, cash_passed=True,
        )
        assert result == "UNEXPECTED"

    def test_blocking_small_delta_above_rounding(self):
        # 0.2% difference — gates pass but >1kEUR → BLOCKING
        result = classify_delta(
            delta_keur=2.0, runtime_dist=1000.0,
            gates_passed=True, r99_blocked=False, r102_blocked=False,
            dscr_passed=True, lockup_passed=True, cash_passed=True,
        )
        assert result == "BLOCKING"


# ---------------------------------------------------------------------------
# DualRunResult construction
# ---------------------------------------------------------------------------

class TestDualRunResult:
    def test_phase_c_not_ready_with_blocking(self):
        result = DualRunResult(
            project_name="TUHO",
            period_results=(
                DualRunPeriodResult(
                    period_index=1, operating_period_index=1,
                    runtime_distribution_keur=1000.0, da_paid_distribution_keur=200.0,
                    delta_keur=-800.0, absolute_delta_keur=800.0, delta_pct=80.0,
                    classification="BLOCKING",
                    gates_passed=True, r99_blocked=False, r102_blocked=False,
                    dscr_passed=True, lockup_passed=True, cash_passed=True,
                    oborovo_passed=True, blocked_reason="", runtime_authoritative=True,
                ),
            ),
            total_runtime_distribution_keur=1000.0,
            total_da_paid_keur=200.0,
            total_delta_keur=-800.0,
            identical_periods=0,
            rounding_periods=0,
            expected_gate_diff_periods=0,
            unexpected_diff_periods=0,
            blocking_periods=1,
            all_invariants_held=False,
            runtime_unchanged=True,
            sponsor_unchanged=True,
            shl_unchanged=True,
            r99_r102_still_blocked=True,
            phase_c_ready=False,
        )
        assert result.phase_c_ready is False
        assert result.blocking_periods == 1

    def test_phase_c_ready_all_identical(self):
        result = DualRunResult(
            project_name="TUHO",
            period_results=(
                DualRunPeriodResult(
                    period_index=1, operating_period_index=1,
                    runtime_distribution_keur=1000.0, da_paid_distribution_keur=1000.0,
                    delta_keur=0.0, absolute_delta_keur=0.0, delta_pct=0.0,
                    classification="IDENTICAL",
                    gates_passed=True, r99_blocked=False, r102_blocked=False,
                    dscr_passed=True, lockup_passed=True, cash_passed=True,
                    oborovo_passed=True, blocked_reason="", runtime_authoritative=True,
                ),
            ),
            total_runtime_distribution_keur=1000.0,
            total_da_paid_keur=1000.0,
            total_delta_keur=0.0,
            identical_periods=1,
            rounding_periods=0,
            expected_gate_diff_periods=0,
            unexpected_diff_periods=0,
            blocking_periods=0,
            all_invariants_held=True,
            runtime_unchanged=True,
            sponsor_unchanged=True,
            shl_unchanged=True,
            r99_r102_still_blocked=True,
            phase_c_ready=True,
        )
        assert result.phase_c_ready is True
        assert result.all_invariants_held is True


# ---------------------------------------------------------------------------
# run_dual_validation basic structure
# ---------------------------------------------------------------------------

class TestRunDualValidationBasic:
    def test_run_dual_validation_produces_dualrun_result(self):
        from unittest.mock import MagicMock

        period_mock = MagicMock()
        period_mock.period = 1
        period_mock.operating_period_index = 1
        period_mock.distribution_keur = 1000.0

        wf_result = MagicMock()
        wf_result.periods = (period_mock,)
        wf_result.project_code = "TUHO"

        da_inp = DistributionAccountInputs(
            project_name="TUHO",
            period_inputs=(
                DistributionAccountPeriodInput(
                    period_index=1,
                    operating_period_index=1,
                    period_date=date(2029, 12, 31),
                    opening_distribution_account_balance_keur=0.0,
                    post_senior_cash_available_keur=1000.0,
                    post_shl_cash_available_keur=1000.0,
                    senior_debt_service_keur=0.0,
                    actual_dscr=1.5,
                    target_distribution_dscr=1.0,
                    is_tuho=True,
                    is_oborovo=False,
                ),
            ),
            is_tuho=True,
            is_oborovo=False,
        )

        result = run_dual_validation(wf_result, da_inp)

        assert result.project_name == "TUHO"
        assert len(result.period_results) >= 1
        assert result.runtime_unchanged is True
        assert result.sponsor_unchanged is True
        assert result.shl_unchanged is True
        assert result.r99_r102_still_blocked is True

    def test_run_dual_validation_all_invariants_true(self):
        from unittest.mock import MagicMock

        period_mock = MagicMock()
        period_mock.period = 1
        period_mock.operating_period_index = 1
        period_mock.distribution_keur = 500.0

        wf_result = MagicMock()
        wf_result.periods = (period_mock,)
        wf_result.project_code = "TUHO"

        da_inp = DistributionAccountInputs(
            project_name="TUHO",
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
                    target_distribution_dscr=1.0,
                    is_tuho=True,
                ),
            ),
            is_tuho=True,
            is_oborovo=False,
        )

        result = run_dual_validation(wf_result, da_inp)

        assert result.runtime_unchanged is True
        assert result.sponsor_unchanged is True
        assert result.shl_unchanged is True
        assert result.r99_r102_still_blocked is True


# ---------------------------------------------------------------------------
# DistributionAccount audit-only confirmation
# ---------------------------------------------------------------------------

class TestDistributionAccountAuditOnly:
    def test_da_runs_in_audit_only_mode(self):
        da_inp = DistributionAccountInputs(
            project_name="TUHO",
            period_inputs=(
                DistributionAccountPeriodInput(
                    period_index=1,
                    operating_period_index=1,
                    period_date=date(2029, 12, 31),
                    opening_distribution_account_balance_keur=0.0,
                    post_senior_cash_available_keur=1000.0,
                    post_shl_cash_available_keur=1000.0,
                    senior_debt_service_keur=0.0,
                    actual_dscr=1.5,
                    enable_r99_r102_runtime=False,
                    is_tuho=True,
                ),
            ),
            is_tuho=True,
        )
        result = DistributionAccountEngine.compute(da_inp)
        assert result.period_results[0].r99_gate_result.passed is False
        assert result.period_results[0].r102_gate_result.passed is False

    def test_da_equity_paid_is_gate_driven(self):
        # Passing gates case
        da_inp_pass = DistributionAccountInputs(
            project_name="TUHO",
            period_inputs=(
                DistributionAccountPeriodInput(
                    period_index=1,
                    operating_period_index=1,
                    period_date=date(2029, 12, 31),
                    opening_distribution_account_balance_keur=0.0,
                    post_senior_cash_available_keur=1000.0,
                    post_shl_cash_available_keur=1000.0,
                    senior_debt_service_keur=0.0,
                    actual_dscr=2.0,
                    target_distribution_dscr=1.0,
                    is_tuho=True,
                    enable_r99_r102_runtime=False,
                ),
            ),
            is_tuho=True,
        )
        result_pass = DistributionAccountEngine.compute(da_inp_pass)
        assert result_pass.period_results[0].equity_distribution_paid_keur >= 0.0

        # Failing DSCR gate case
        da_inp_fail = DistributionAccountInputs(
            project_name="TUHO",
            period_inputs=(
                DistributionAccountPeriodInput(
                    period_index=1,
                    operating_period_index=1,
                    period_date=date(2029, 12, 31),
                    opening_distribution_account_balance_keur=0.0,
                    post_senior_cash_available_keur=1000.0,
                    post_shl_cash_available_keur=1000.0,
                    senior_debt_service_keur=0.0,
                    actual_dscr=0.5,
                    target_distribution_dscr=1.0,
                    is_tuho=True,
                    enable_r99_r102_runtime=False,
                ),
            ),
            is_tuho=True,
        )
        result_fail = DistributionAccountEngine.compute(da_inp_fail)
        assert result_fail.period_results[0].equity_distribution_paid_keur == 0.0


# ---------------------------------------------------------------------------
# waterfall_core.py flag
# ---------------------------------------------------------------------------

class TestWaterfallCoreFlag:
    def test_dualrun_validation_flag_exists(self):
        import app.waterfall_core as wc
        import inspect
        sig = inspect.signature(wc.run_waterfall_v3_core)
        params = list(sig.parameters.keys())
        assert "use_dualrun_validation" in params

    def test_dualrun_validation_default_false(self):
        import app.waterfall_core as wc
        import inspect
        sig = inspect.signature(wc.run_waterfall_v3_core)
        param = sig.parameters["use_dualrun_validation"]
        assert param.default is False


# ---------------------------------------------------------------------------
# Deterministic per-period comparison
# ---------------------------------------------------------------------------

class TestDeterministicComparison:
    def test_same_inputs_produce_same_da_output(self):
        from unittest.mock import MagicMock

        period_mock = MagicMock()
        period_mock.period = 1
        period_mock.operating_period_index = 1
        period_mock.distribution_keur = 1000.0

        wf_result = MagicMock()
        wf_result.periods = (period_mock,)
        wf_result.project_code = "TUHO"

        da_inp = DistributionAccountInputs(
            project_name="TUHO",
            period_inputs=(
                DistributionAccountPeriodInput(
                    period_index=1,
                    operating_period_index=1,
                    period_date=date(2029, 12, 31),
                    opening_distribution_account_balance_keur=0.0,
                    post_senior_cash_available_keur=1000.0,
                    post_shl_cash_available_keur=1000.0,
                    senior_debt_service_keur=0.0,
                    actual_dscr=2.0,
                    target_distribution_dscr=1.0,
                    is_tuho=True,
                ),
            ),
            is_tuho=True,
        )

        result1 = run_dual_validation(wf_result, da_inp)
        result2 = run_dual_validation(wf_result, da_inp)

        assert len(result1.period_results) == len(result2.period_results)
        for p1, p2 in zip(result1.period_results, result2.period_results):
            assert p1.classification == p2.classification
            assert p1.da_paid_distribution_keur == p2.da_paid_distribution_keur


# ---------------------------------------------------------------------------
# No routing overwrite
# ---------------------------------------------------------------------------

class TestNoRoutingOverwrite:
    def test_waterfall_result_not_modified(self):
        from unittest.mock import MagicMock

        period_mock = MagicMock()
        period_mock.period = 1
        period_mock.operating_period_index = 1
        period_mock.distribution_keur = 1000.0

        wf_result = MagicMock()
        wf_result.periods = (period_mock,)
        wf_result.project_code = "TUHO"

        da_inp = DistributionAccountInputs(
            project_name="TUHO",
            period_inputs=(
                DistributionAccountPeriodInput(
                    period_index=1,
                    operating_period_index=1,
                    period_date=date(2029, 12, 31),
                    opening_distribution_account_balance_keur=0.0,
                    post_senior_cash_available_keur=1000.0,
                    post_shl_cash_available_keur=1000.0,
                    senior_debt_service_keur=0.0,
                    actual_dscr=1.5,
                    is_tuho=True,
                ),
            ),
            is_tuho=True,
        )

        result = run_dual_validation(wf_result, da_inp)

        assert result.runtime_unchanged is True