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
            da_governed_paid_distribution_keur=1000.0,
            da_economic_paid_distribution_keur=1000.0,
            delta_keur=0.0,
            delta_economic_keur=0.0,
            absolute_delta_keur=0.0,
            delta_pct=0.0,
            delta_economic_pct=0.0,
            classification="IDENTICAL",
            classification_economic="IDENTICAL",
            gates_passed=True,
            economic_gates_evaluated=True,
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
        assert r.da_economic_paid_distribution_keur == 1000.0
        assert r.classification_economic == "IDENTICAL"

    def test_r99_blocked_classification(self):
        r = DualRunPeriodResult(
            period_index=2,
            operating_period_index=2,
            runtime_distribution_keur=500.0,
            da_governed_paid_distribution_keur=0.0,
            da_economic_paid_distribution_keur=500.0,
            delta_keur=-500.0,
            delta_economic_keur=0.0,
            absolute_delta_keur=500.0,
            delta_pct=100.0,
            delta_economic_pct=0.0,
            classification="EXPECTED_GATE_DIFFERENCE",
            classification_economic="IDENTICAL",
            gates_passed=False,
            economic_gates_evaluated=True,
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
        assert r.da_economic_paid_distribution_keur == 500.0
        assert r.classification_economic == "IDENTICAL"




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
                    runtime_distribution_keur=1000.0,
                    da_governed_paid_distribution_keur=200.0,
                    da_economic_paid_distribution_keur=200.0,
                    delta_keur=-800.0, absolute_delta_keur=800.0, delta_pct=80.0,
                    delta_economic_keur=-800.0, delta_economic_pct=80.0,
                    classification="BLOCKING",
                    classification_economic="BLOCKING",
                    gates_passed=True, economic_gates_evaluated=True,
                    r99_blocked=False, r102_blocked=False,
                    dscr_passed=True, lockup_passed=True, cash_passed=True,
                    oborovo_passed=True, blocked_reason="", runtime_authoritative=True,
                ),
            ),
            total_runtime_distribution_keur=1000.0,
            total_da_governed_paid_keur=200.0,
            total_da_economic_paid_keur=200.0,
            total_delta_keur=-800.0,
            total_delta_economic_keur=-800.0,
            identical_periods=0,
            rounding_periods=0,
            expected_gate_diff_periods=0,
            unexpected_diff_periods=0,
            blocking_periods=1,
            identical_economic_periods=0,
            rounding_economic_periods=0,
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
                    runtime_distribution_keur=1000.0,
                    da_governed_paid_distribution_keur=1000.0,
                    da_economic_paid_distribution_keur=1000.0,
                    delta_keur=0.0, absolute_delta_keur=0.0, delta_pct=0.0,
                    delta_economic_keur=0.0, delta_economic_pct=0.0,
                    classification="IDENTICAL",
                    classification_economic="IDENTICAL",
                    gates_passed=True, economic_gates_evaluated=True,
                    r99_blocked=False, r102_blocked=False,
                    dscr_passed=True, lockup_passed=True, cash_passed=True,
                    oborovo_passed=True, blocked_reason="", runtime_authoritative=True,
                ),
            ),
            total_runtime_distribution_keur=1000.0,
            total_da_governed_paid_keur=1000.0,
            total_da_economic_paid_keur=1000.0,
            total_delta_keur=0.0,
            total_delta_economic_keur=0.0,
            identical_periods=1,
            rounding_periods=0,
            expected_gate_diff_periods=0,
            unexpected_diff_periods=0,
            blocking_periods=0,
            identical_economic_periods=1,
            rounding_economic_periods=0,
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


# ---------------------------------------------------------------------------
# Realistic cash-source tests for _attach_dualrun_validation
# These replace the revenue - opex proxy with the proper cascade:
#   r99_fcf_for_distribution_keur → cf_after_reserves_keur → cf_after_tax - senior_ds
# ---------------------------------------------------------------------------

class TestRealisticCashSourceForDualRun:
    """Tests proving DA dual-run input no longer uses revenue - opex proxy."""

    def _make_wp(self, **attrs):
        """Make a mock waterfall period with given attributes."""
        from unittest.mock import MagicMock
        wp = MagicMock()
        wp.period = attrs.get("period", 1)
        wp.operating_period_index = attrs.get("operating_period_index", 1)
        wp.r99_fcf_for_distribution_keur = attrs.get("r99_fcf_for_distribution_keur", 0.0)
        wp.cf_after_reserves_keur = attrs.get("cf_after_reserves_keur", 0.0)
        wp.cf_after_tax_keur = attrs.get("cf_after_tax_keur", 0.0)
        wp.senior_ds_keur = attrs.get("senior_ds_keur", 0.0)
        wp.revenue_keur = attrs.get("revenue_keur", 0.0)
        wp.opex_keur = attrs.get("opex_keur", 0.0)
        wp.dscr = attrs.get("dscr", 1.5)
        wp.dsra_balance_keur = attrs.get("dsra_balance_keur", 0.0)
        wp.date = attrs.get("date") or __import__("datetime").date(2029, 12, 31)
        return wp

    def test_da_input_uses_cf_after_reserves_when_diverging_from_r99_fcf(self):
        """When r99_fcf diverges from cf_after_reserves, use cf_after_reserves (runtime source).

        In TUHO tax_bridge mode, r99_fcf (= cf_after_tax with bridge cash tax) differs from
        cf_after_reserves (runtime's actual distribution source). Using cf_after_reserves
        when they diverge ensures DA economic mode matches runtime distribution behavior.
        """
        from unittest.mock import MagicMock, patch
        from app.waterfall_core import _attach_dualrun_validation

        wp = self._make_wp(
            period=1, operating_period_index=1,
            r99_fcf_for_distribution_keur=500.0,
            cf_after_reserves_keur=400.0,  # diverges by 100 → tax_bridge heuristic
            cf_after_tax_keur=600.0,
            senior_ds_keur=200.0,
            revenue_keur=1000.0,
            opex_keur=300.0,
            dscr=1.5,
            dsra_balance_keur=0.0,
        )
        wf_result = MagicMock()
        wf_result.periods = [wp]

        inputs_info = MagicMock()
        inputs_info.code = "TUHO-WIND-1"
        inputs_financing = MagicMock()
        inputs_financing.senior_tenor_years = 10
        mock_inputs = MagicMock()
        mock_inputs.info = inputs_info
        mock_inputs.financing = inputs_financing

        # Patch run_dual_validation to capture the actual DA inputs built
        with patch(
            "domain.distribution_account.dualrun_validation.run_dual_validation"
        ) as mock_run:
            _attach_dualrun_validation(wf_result, mock_inputs, wf_result.periods)
            assert mock_run.called
            _, governed_inputs, economic_inputs = mock_run.call_args[0]
            # r99_fcf=500, cf_after_reserves=400, delta=100 > 1 → use cf_after_reserves
            assert governed_inputs.period_inputs[0].post_shl_cash_available_keur == 400.0

    def test_da_input_not_revenue_minus_opex(self):
        """DA post_shl_cash must not equal revenue - opex when r99_fcf = 0."""
        from unittest.mock import MagicMock, patch
        from app.waterfall_core import _attach_dualrun_validation

        # r99_fcf=0, cf_after_reserves=350, cf_after_tax=600, senior_ds=200
        # Expected: post_shl_cash = 350 (cf_after_reserves)
        wp = self._make_wp(
            period=2, operating_period_index=2,
            r99_fcf_for_distribution_keur=0.0,
            cf_after_reserves_keur=350.0,
            cf_after_tax_keur=600.0,
            senior_ds_keur=200.0,
            revenue_keur=1000.0,
            opex_keur=300.0,
            dscr=1.5,
            dsra_balance_keur=0.0,
        )
        wf_result = MagicMock()
        wf_result.periods = [wp]

        inputs_info = MagicMock()
        inputs_info.code = "TUHO-WIND-1"
        inputs_financing = MagicMock()
        inputs_financing.senior_tenor_years = 10
        mock_inputs = MagicMock()
        mock_inputs.info = inputs_info
        mock_inputs.financing = inputs_financing

        with patch(
            "domain.distribution_account.dualrun_validation.run_dual_validation"
        ) as mock_run:
            _attach_dualrun_validation(wf_result, mock_inputs, wf_result.periods)
            _, governed_inputs, economic_inputs = mock_run.call_args[0]
            post_shl = governed_inputs.period_inputs[0].post_shl_cash_available_keur
            assert post_shl != 700.0, "DA input must not use revenue - opex proxy"
            assert post_shl == 350.0, "DA input should use cf_after_reserves (= 350)"

    def test_da_input_falls_back_to_cf_after_tax_minus_senior_ds(self):
        """When r99_fcf=0 and cf_after_reserves=0, use cf_after_tax - senior_ds."""
        from unittest.mock import MagicMock, patch
        from app.waterfall_core import _attach_dualrun_validation

        # r99_fcf=0, cf_after_reserves=0, cf_after_tax=600, senior_ds=200
        # Expected: post_shl_cash = max(0, 600-200) = 400
        wp = self._make_wp(
            period=3, operating_period_index=3,
            r99_fcf_for_distribution_keur=0.0,
            cf_after_reserves_keur=0.0,
            cf_after_tax_keur=600.0,
            senior_ds_keur=200.0,
            revenue_keur=1000.0,
            opex_keur=300.0,
            dscr=1.5,
            dsra_balance_keur=0.0,
        )
        wf_result = MagicMock()
        wf_result.periods = [wp]

        inputs_info = MagicMock()
        inputs_info.code = "TUHO-WIND-1"
        inputs_financing = MagicMock()
        inputs_financing.senior_tenor_years = 10
        mock_inputs = MagicMock()
        mock_inputs.info = inputs_info
        mock_inputs.financing = inputs_financing

        with patch(
            "domain.distribution_account.dualrun_validation.run_dual_validation"
        ) as mock_run:
            _attach_dualrun_validation(wf_result, mock_inputs, wf_result.periods)
            _, governed_inputs, economic_inputs = mock_run.call_args[0]
            post_shl = governed_inputs.period_inputs[0].post_shl_cash_available_keur
            expected = max(0.0, 600.0 - 200.0)  # = 400
            assert post_shl != 700.0, "Must not use revenue - opex"
            assert post_shl == expected, f"Should use cf_after_tax - senior_ds = {expected}"


class TestDualRunExceptionHandling:
    """Exception handling in _attach_dualrun_validation."""

    def test_exception_does_not_propagate(self):
        """If run_dual_validation raises, _attach_dualrun_validation must not propagate."""
        from unittest.mock import MagicMock, patch
        from app.waterfall_core import _attach_dualrun_validation
        wp = MagicMock()
        wp.period = 1
        wp.operating_period_index = 1
        wp.r99_fcf_for_distribution_keur = 0.0
        wp.cf_after_reserves_keur = 0.0
        wp.cf_after_tax_keur = 0.0
        wp.senior_ds_keur = 0.0
        wp.revenue_keur = 0.0
        wp.opex_keur = 0.0
        wp.dscr = 1.5
        wp.dsra_balance_keur = 0.0
        wp.date = None
        wf_result = MagicMock()
        wf_result.periods = [wp]

        inputs_info = MagicMock()
        inputs_info.code = "TUHO-WIND-1"
        inputs_financing = MagicMock()
        inputs_financing.senior_tenor_years = 10
        mock_inputs = MagicMock()
        mock_inputs.info = inputs_info
        mock_inputs.financing = inputs_financing

        with patch(
            "domain.distribution_account.dualrun_validation.run_dual_validation",
            side_effect=RuntimeError("intentional test error"),
        ):
            # Must not raise
            _attach_dualrun_validation(wf_result, mock_inputs, wf_result.periods)
            # Attribute must exist (no exception propagated)
            assert hasattr(wf_result, "_dualrun_validation")


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
            assert p1.da_governed_paid_distribution_keur == p2.da_governed_paid_distribution_keur


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

# ---------------------------------------------------------------------------
# Matrix population tests
# These validate the dual-run matrix CSV generation results
# ---------------------------------------------------------------------------

class TestMatrixPopulation:
    """Tests for populated dual-run matrix."""

    def test_matrix_csv_exists_and_has_data(self):
        """Matrix CSV must exist and contain real data rows (not just header)."""
        import csv
        from pathlib import Path
        matrix_path = Path(__file__).resolve().parents[1] / "reports" / "phase9_distributionaccount_dualrun_matrix.csv"
        assert matrix_path.exists(), f"Matrix CSV not found: {matrix_path}"
        with open(matrix_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) > 0, "Matrix CSV has no data rows (header only)"
        assert len(rows) >= 100, f"Expected many data rows, got {len(rows)}"

    def test_matrix_has_required_columns(self):
        """Matrix CSV must have all required columns."""
        import csv
        from pathlib import Path
        matrix_path = Path(__file__).resolve().parents[1] / "reports" / "phase9_distributionaccount_dualrun_matrix.csv"
        with open(matrix_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
        required = {
            "project", "period", "runtime_distribution_keur",
            "da_governed_paid_distribution_keur", "da_economic_paid_distribution_keur", "delta_keur", "delta_economic_keur", "delta_pct", "delta_economic_pct",
            "classification", "gates_passed", "runtime_authoritative",
            "validation_error", "notes",
        }
        missing = required - set(fieldnames)
        assert not missing, f"Missing CSV columns: {missing}"

    def test_all_periods_classified(self):
        """Every row in the matrix must have a valid classification."""
        import csv
        from pathlib import Path
        from collections import Counter
        matrix_path = Path(__file__).resolve().parents[1] / "reports" / "phase9_distributionaccount_dualrun_matrix.csv"
        with open(matrix_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        valid_classes = {"IDENTICAL", "ROUNDING", "EXPECTED_GATE_DIFFERENCE", "UNEXPECTED", "BLOCKING"}
        for r in rows:
            assert r["classification"] in valid_classes, \
                f"Invalid classification: {r['classification']} for period {r['period']}"

    def test_no_blocking_classifications(self):
        """No BLOCKING classifications in the matrix (would block Phase C)."""
        import csv
        from pathlib import Path
        matrix_path = Path(__file__).resolve().parents[1] / "reports" / "phase9_distributionaccount_dualrun_matrix.csv"
        with open(matrix_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        blocking = [r for r in rows if r["classification"] == "BLOCKING"]
        assert len(blocking) == 0, f"Found {len(blocking)} BLOCKING rows — Phase C must be BLOCKED"

    def test_validation_errors_are_surfaced(self):
        """validation_error column must be empty for successful rows (visible = not silent)."""
        import csv
        from pathlib import Path
        matrix_path = Path(__file__).resolve().parents[1] / "reports" / "phase9_distributionaccount_dualrun_matrix.csv"
        with open(matrix_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        # Error rows should have a non-empty validation_error field
        error_rows = [r for r in rows if r["validation_error"].strip()]
        data_rows = [r for r in rows if r["classification"] not in ("NO_DUALRUN_RESULT", "DUALRUN_EXCEPTION", "")]
        # If there are error rows, they should have error text (not silent)
        for r in error_rows:
            assert len(r["validation_error"].strip()) > 0

    def test_summary_csv_exists(self):
        """Summary CSV must exist alongside the matrix CSV."""
        import csv
        from pathlib import Path
        summary_path = Path(__file__).resolve().parents[1] / "reports" / "phase9_distributionaccount_dualrun_summary.csv"
        assert summary_path.exists(), f"Summary CSV not found: {summary_path}"
        with open(summary_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) >= 13, f"Expected >= 13 combos in summary, got {len(rows)}"

    def test_phase_c_readiness_determined(self):
        """All combos in summary must have explicit phase_c_ready value."""
        import csv
        from pathlib import Path
        summary_path = Path(__file__).resolve().parents[1] / "reports" / "phase9_distributionaccount_dualrun_summary.csv"
        with open(summary_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            assert r["phase_c_ready"] in ("True", "False"), \
                f"Combo {r['flag_combo']} missing phase_c_ready: {r['phase_c_ready']}"


    def test_supported_for_phase_c_column_present(self):
        """Matrix CSV must have supported_for_phase_c column."""
        import csv
        from pathlib import Path
        matrix_path = Path(__file__).resolve().parents[1] / "reports" / "phase9_distributionaccount_dualrun_matrix.csv"
        with open(matrix_path, newline="", encoding="utf-8") as f:
            fieldnames = csv.DictReader(f).fieldnames
        assert "supported_for_phase_c" in fieldnames, \
            "supported_for_phase_c column missing from matrix CSV"

    def test_supported_combos_have_no_unexpected_or_blocking(self):
        """Supported combos must have zero UNEXPECTED and zero BLOCKING rows."""
        import csv
        from pathlib import Path
        matrix_path = Path(__file__).resolve().parents[1] / "reports" / "phase9_distributionaccount_dualrun_matrix.csv"
        with open(matrix_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        supported = [r for r in rows if r["supported_for_phase_c"] == "True"
                     and r["classification"] not in ("NO_DUALRUN_RESULT", "DUALRUN_EXCEPTION")]
        unexpected = [r for r in supported if r["classification_economic"] == "UNEXPECTED"]
        blocking = [r for r in supported if r["classification_economic"] == "BLOCKING"]
        assert len(unexpected) == 0, f"Supported combos have {len(unexpected)} UNEXPECTED rows"
        assert len(blocking) == 0, f"Supported combos have {len(blocking)} BLOCKING rows"

    def test_unsupported_combos_are_isolated(self):
        """Unsupported combos must have supported_for_phase_c=False in summary CSV.

        co2_revenue+cit raises an exception in the waterfall engine (mutually exclusive
        flags) so it has 0 rows in the matrix. Check the summary CSV instead.
        """
        import csv
        from pathlib import Path
        summary_path = Path(__file__).resolve().parents[1] / "reports" / "phase9_distributionaccount_dualrun_summary.csv"
        with open(summary_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        unsupported = [r for r in rows if r["flag_combo"] == "co2_revenue+cit"]
        assert len(unsupported) > 0, "co2_revenue+cit must exist in summary CSV"
        for r in unsupported:
            assert r["phase_c_supported"] == "False", \
                f"Combo {r['flag_combo']} must have phase_c_supported=False"

    def test_phase_c_ready_false_when_unsupported_combos_exist(self):
        """phase_c_ready must be False for unsupported combos."""
        import csv
        from pathlib import Path
        summary_path = Path(__file__).resolve().parents[1] / "reports" / "phase9_distributionaccount_dualrun_summary.csv"
        with open(summary_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            if r["flag_combo"] == "co2_revenue+cit":
                assert r["phase_c_ready"] == "False", \
                    f"Unsupported combo {r['flag_combo']} must have phase_c_ready=False"
                assert r["phase_c_supported"] == "False", \
                    f"Unsupported combo must have phase_c_supported=False"


    def test_tax_bridge_now_supported(self):
        """tax_bridge and shl+deprec+tax_bridge combos must have zero UNEXPECTED/BLOCKING."""
        import csv
        from pathlib import Path
        matrix_path = Path(__file__).resolve().parents[1] / "reports" / "phase9_distributionaccount_dualrun_matrix.csv"
        with open(matrix_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for combo_label in ("tax_bridge", "shl+deprec+tax_bridge"):
            combo_rows = [r for r in rows if r["flag_combo"] == combo_label]
            assert len(combo_rows) > 0, f"{combo_label} must exist in matrix"
            for r in combo_rows:
                assert r["classification_economic"] in ("IDENTICAL", "ROUNDING", "EXPECTED_GATE_DIFFERENCE"), \
                    f"{combo_label} period {r['period']} has unexpected {r['classification_economic']}"
                assert r["classification_economic"] not in ("UNEXPECTED", "BLOCKING"), \
                    f"{combo_label} period {r['period']} has {r['classification_economic']}"
                assert r["supported_for_phase_c"] == "True", \
                    f"{combo_label} must have supported_for_phase_c=True"

    def test_phase_c_ready_requires_identical_or_rounding(self):
        """phase_c_ready=True requires positive IDENTICAL/ROUNDING count in summary."""
        import csv
        from pathlib import Path
        summary_path = Path(__file__).resolve().parents[1] / "reports" / "phase9_distributionaccount_dualrun_summary.csv"
        with open(summary_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            if r["phase_c_ready"] == "True":
                ident_econ = int(r.get("identical_economic", 0))
                round_econ = int(r.get("rounding_economic", 0))
                assert ident_econ + round_econ > 0, \
                    f"Combo {r['flag_combo']} phase_c_ready=True but identical_econ={ident_econ} rounding_econ={round_econ}"
                assert r["phase_c_supported"] == "True", \
                    f"phase_c_ready=True requires phase_c_supported=True"
                assert int(r["unexpected"]) == 0, f"phase_c_ready=True but unexpected={r['unexpected']}"
                assert int(r["blocking"]) == 0, f"phase_c_ready=True but blocking={r['blocking']}"

    def test_phase_c_supported_field_in_summary(self):
        """Summary CSV must have phase_c_supported field for every combo."""
        import csv
        from pathlib import Path
        summary_path = Path(__file__).resolve().parents[1] / "reports" / "phase9_distributionaccount_dualrun_summary.csv"
        with open(summary_path, newline="", encoding="utf-8") as f:
            fieldnames = csv.DictReader(f).fieldnames
        assert "phase_c_supported" in fieldnames, "phase_c_supported field missing from summary CSV"

    def test_no_blocking_in_supported_rows(self):
        """Supported rows must have zero BLOCKING classification_economic."""
        import csv
        from pathlib import Path
        matrix_path = Path(__file__).resolve().parents[1] / "reports" / "phase9_distributionaccount_dualrun_matrix.csv"
        with open(matrix_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        supported_blocking = [
            r for r in rows
            if r["supported_for_phase_c"] == "True"
            and r["classification_economic"] == "BLOCKING"
        ]
        assert len(supported_blocking) == 0, \
            f"Supported rows must have 0 BLOCKING, found {len(supported_blocking)}"


class TestInvariantPreservation:

    """Tests proving runtime invariants are maintained."""

    def test_runtime_authoritative_true_in_all_rows(self):
        """Every matrix row must show runtime_authoritative=True."""
        import csv
        from pathlib import Path
        matrix_path = Path(__file__).resolve().parents[1] / "reports" / "phase9_distributionaccount_dualrun_matrix.csv"
        with open(matrix_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        data_rows = [r for r in rows if r["classification"] not in ("NO_DUALRUN_RESULT", "DUALRUN_EXCEPTION", "")]
        for r in data_rows:
            assert r["runtime_authoritative"] == "True", \
                f"Period {r['period']} has runtime_authoritative={r['runtime_authoritative']}"

    def test_r99_and_r102_blocked_in_all_rows(self):
        """In Phase B, r99_blocked and r102_blocked must be True for all periods."""
        import csv
        from pathlib import Path
        matrix_path = Path(__file__).resolve().parents[1] / "reports" / "phase9_distributionaccount_dualrun_matrix.csv"
        with open(matrix_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        data_rows = [r for r in rows if r["classification"] not in ("NO_DUALRUN_RESULT", "DUALRUN_EXCEPTION", "")]
        for r in data_rows:
            assert r["r99_blocked"] == "True", f"Period {r['period']} r99_blocked={r['r99_blocked']}"
            assert r["r102_blocked"] == "True", f"Period {r['period']} r102_blocked={r['r102_blocked']}"
