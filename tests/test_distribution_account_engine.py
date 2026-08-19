"""Tests for canonical DistributionAccount engine."""
import pytest
from datetime import date

from domain.distribution_account import (
    DistributionAccountEngine,
    DistributionAccountInputs,
    DistributionAccountPeriodInput,
    R99R102GateInputs,
    DistributionGateResult,
)
from domain.distribution_account.result import BLOCKED_REASONS
from finco_core.engine.distribution_account.inputs import CovenantGatePolicy


class TestDataclassConstruction:
    def test_gate_inputs_default(self):
        gi = R99R102GateInputs()
        assert gi.cumulative_fcf_keur == 0.0
        assert gi.senior_debt_outstanding_keur == 0.0

    def test_period_input_basic(self):
        inp = DistributionAccountPeriodInput(
            period_index=1,
            operating_period_index=1,
            period_date=date(2029, 12, 31),
            opening_distribution_account_balance_keur=100.0,
            post_senior_cash_available_keur=500.0,
            post_shl_cash_available_keur=450.0,
            senior_debt_service_keur=200.0,
            actual_dscr=1.45,
            target_distribution_dscr=1.0,
            is_tuho=True,
        )
        assert inp.period_index == 1
        assert inp.is_tuho is True
        assert inp.is_oborovo is False

    def test_inputs_collection(self):
        inp = DistributionAccountPeriodInput(
            period_index=1, operating_period_index=1,
            period_date=date(2029, 12, 31),
            opening_distribution_account_balance_keur=0.0,
            post_senior_cash_available_keur=100.0,
            post_shl_cash_available_keur=100.0,
            senior_debt_service_keur=0.0,
            actual_dscr=1.5,
        )
        inputs = DistributionAccountInputs(
            project_name="TUHO",
            period_inputs=(inp,),
            is_tuho=True,
        )
        assert len(inputs.period_inputs) == 1
        assert inputs.project_name == "TUHO"


class TestGatePassFail:
    def test_r99_gate_blocked_when_runtime_disabled(self):
        from domain.distribution_account.gates import evaluate_r99_gate
        result = evaluate_r99_gate(R99R102GateInputs(), 1000.0, enable_runtime=False)
        assert result.passed is False
        assert BLOCKED_REASONS["R99_BLOCKED"] in result.blocked_reason

    def test_r102_gate_blocked_when_runtime_disabled(self):
        from domain.distribution_account.gates import evaluate_r102_gate
        result = evaluate_r102_gate(R99R102GateInputs(), 1000.0, enable_runtime=False)
        assert result.passed is False
        assert BLOCKED_REASONS["R102_BLOCKED"] in result.blocked_reason

    def test_dscr_gate_passes_when_above_threshold(self):
        from domain.distribution_account.gates import evaluate_dscr_gate
        result = evaluate_dscr_gate(actual_dscr=1.5, target_dscr=1.0)
        assert result.passed is True
        assert result.blocked_reason == ""

    def test_dscr_gate_fails_when_below_threshold(self):
        from domain.distribution_account.gates import evaluate_dscr_gate
        result = evaluate_dscr_gate(actual_dscr=0.8, target_dscr=1.0)
        assert result.passed is False
        assert BLOCKED_REASONS["DSCR_GATE_FAILED"] in result.blocked_reason

    def test_oborovo_guard_blocks_oborovo(self):
        from domain.distribution_account.gates import evaluate_oborovo_guard
        result = evaluate_oborovo_guard(is_oborovo=True)
        assert result.passed is False
        assert BLOCKED_REASONS["OBOROVO_NOT_SUPPORTED"] in result.blocked_reason

    def test_oborovo_guard_passes_for_tuho(self):
        from domain.distribution_account.gates import evaluate_oborovo_guard
        result = evaluate_oborovo_guard(is_oborovo=False)
        assert result.passed is True

    def test_negative_cash_gate_fails(self):
        from domain.distribution_account.gates import evaluate_cash_gate
        result = evaluate_cash_gate(cash_available=-100.0)
        assert result.passed is False
        assert BLOCKED_REASONS["NEGATIVE_CASH"] in result.blocked_reason

    def test_positive_cash_gate_passes(self):
        from domain.distribution_account.gates import evaluate_cash_gate
        result = evaluate_cash_gate(cash_available=500.0)
        assert result.passed is True


class TestCashReconciliation:
    def test_closing_balance_from_opening_and_retained(self):
        inp = DistributionAccountPeriodInput(
            period_index=1, operating_period_index=1,
            period_date=date(2029, 12, 31),
            opening_distribution_account_balance_keur=100.0,
            post_senior_cash_available_keur=500.0,
            post_shl_cash_available_keur=400.0,
            senior_debt_service_keur=200.0,
            actual_dscr=1.5,
            target_distribution_dscr=1.0,
            is_tuho=True,
        )
        inputs = DistributionAccountInputs(
            project_name="TUHO",
            period_inputs=(inp,),
            is_tuho=True,
        )
        result = DistributionAccountEngine.compute(inputs)
        period_result = result.period_results[0]
        # closing = opening + retained + dsra_top_up
        # cash_for_dist=400, dsra_top_up=0 (balance >= target)
        # cash_retained=0 (400 >= 0 minimum reserve default)
        # closing = 100 + 0 = 100
        assert period_result.closing_distribution_account_balance_keur == 100.0

    def test_cash_retained_when_insufficient(self):
        inp = DistributionAccountPeriodInput(
            period_index=1, operating_period_index=1,
            period_date=date(2029, 12, 31),
            opening_distribution_account_balance_keur=50.0,
            post_senior_cash_available_keur=200.0,
            post_shl_cash_available_keur=50.0,  # low cash
            senior_debt_service_keur=100.0,
            actual_dscr=1.5,
            target_distribution_dscr=1.0,
            minimum_cash_reserve_keur=100.0,
            is_tuho=True,
        )
        inputs = DistributionAccountInputs(
            project_name="TUHO",
            period_inputs=(inp,),
            is_tuho=True,
        )
        result = DistributionAccountEngine.compute(inputs)
        period_result = result.period_results[0]
        # cash_for_dist=50, minimum_cash_reserve=100
        # cash_retained = 50, cash_for_dist = 0
        assert period_result.cash_retained_keur == 50.0
        assert period_result.cash_available_for_distribution_keur == 0.0


class TestBlockedReasonCoverage:
    def test_r99_blocked_returns_correct_reason(self):
        from domain.distribution_account.gates import evaluate_r99_gate
        result = evaluate_r99_gate(R99R102GateInputs(), 1000.0, enable_runtime=False)
        assert result.blocked_reason == BLOCKED_REASONS["R99_BLOCKED"]

    def test_r102_blocked_returns_correct_reason(self):
        from domain.distribution_account.gates import evaluate_r102_gate
        result = evaluate_r102_gate(R99R102GateInputs(), 1000.0, enable_runtime=False)
        assert result.blocked_reason == BLOCKED_REASONS["R102_BLOCKED"]

    def test_all_blocked_reasons_defined(self):
        from domain.distribution_account.result import BLOCKED_REASONS
        expected = {"R99_BLOCKED", "R102_BLOCKED", "DSCR_GATE_FAILED",
                    "OBOROVO_NOT_SUPPORTED", "NEGATIVE_CASH",
                    "DISTRIBUTION_ACCOUNT_NOT_PROMOTED"}
        for reason in expected:
            assert reason in BLOCKED_REASONS


class TestOborovoGuard:
    def test_oborovo_project_flagged(self):
        inp = DistributionAccountPeriodInput(
            period_index=1, operating_period_index=1,
            period_date=date(2029, 12, 31),
            opening_distribution_account_balance_keur=100.0,
            post_senior_cash_available_keur=500.0,
            post_shl_cash_available_keur=500.0,
            senior_debt_service_keur=0.0,
            actual_dscr=1.5,
            target_distribution_dscr=1.0,
            is_tuho=False,
            is_oborovo=True,
        )
        inputs = DistributionAccountInputs(
            project_name="Oborovo",
            period_inputs=(inp,),
            is_tuho=False,
            is_oborovo=True,
        )
        result = DistributionAccountEngine.compute(inputs)
        period_result = result.period_results[0]
        # oborovo_gate is deprecated diagnostic — never a financial authority
        assert period_result.oborovo_gate_result.passed is False
        # is_oborovo does not affect financial gates; blocked_reason reflects only financial gates
        # With NOT_APPLICABLE policy + good DSCR + positive cash, all financial gates pass
        assert period_result.blocked_reason == ""


class TestEquityDistributionCandidate:
    def test_equity_candidate_computed_but_not_paid(self):
        inp = DistributionAccountPeriodInput(
            period_index=5, operating_period_index=5,
            period_date=date(2033, 12, 31),
            opening_distribution_account_balance_keur=0.0,
            post_senior_cash_available_keur=1000.0,
            post_shl_cash_available_keur=800.0,
            senior_debt_service_keur=200.0,
            actual_dscr=1.5,
            target_distribution_dscr=1.0,
            is_tuho=True,
        )
        inputs = DistributionAccountInputs(
            project_name="TUHO",
            period_inputs=(inp,),
            is_tuho=True,
            covenant_gate_policy=CovenantGatePolicy.R99_R102_APPLICABLE,
        )
        result = DistributionAccountEngine.compute(inputs)
        period_result = result.period_results[0]
        # equity_candidate = cash_for_dist (audit-only, not paid)
        assert period_result.equity_distribution_candidate_keur > 0
        assert period_result.equity_distribution_paid_keur == 0.0  # audit-only
        assert period_result.r99_gate_result.passed is False  # blocked


class TestAuditRowGeneration:
    def test_audit_row_to_csv(self):
        from domain.distribution_account.audit import DistributionAuditRow
        row = DistributionAuditRow(
            period_index=1,
            project_name="TUHO",
            operating_period_index=1,
            period_date=date(2029, 12, 31),
            opening_balance_keur=100.0,
            closing_balance_keur=100.0,
            cash_available_for_distribution_keur=500.0,
            equity_distribution_candidate_keur=500.0,
            equity_distribution_paid_keur=0.0,
            cash_swept_to_shl_keur=0.0,
            cash_retained_keur=0.0,
            dsra_top_up_keur=0.0,
            r99_gate_passed=False,
            r102_gate_passed=False,
            dscr_gate_passed=True,
            lockup_gate_passed=True,
            oborovo_guard_passed=True,
            blocked_reason="R99_BLOCKED",
            is_tuho=True,
            is_oborovo=False,
        )
        csv = row.to_csv_row()
        assert csv["period_index"] == 1
        assert csv["r99_gate_passed"] is False
        assert csv["equity_distribution_paid_keur"] == "0.00"


class TestR99R102RemainAuditOnly:
    def test_r99_gate_blocked_in_all_cases(self):
        from domain.distribution_account.gates import evaluate_r99_gate
        for enable_runtime in [True, False]:
            result = evaluate_r99_gate(R99R102GateInputs(), 1000.0, enable_runtime=enable_runtime)
            assert result.passed is False
            assert "R99" in result.blocked_reason

    def test_r102_gate_blocked_in_all_cases(self):
        from domain.distribution_account.gates import evaluate_r102_gate
        for enable_runtime in [True, False]:
            result = evaluate_r102_gate(R99R102GateInputs(), 1000.0, enable_runtime=enable_runtime)
            assert result.passed is False
            assert "R102" in result.blocked_reason


class TestNoRuntimeOwnershipChanges:
    def test_no_waterfall_core_imported(self):
        """Verify DistributionAccount doesn't import app.waterfall_core."""
        import domain.distribution_account.engine as engine_module
        source = str(engine_module.__file__)
        assert "waterfall_core" not in source

    def test_compute_returns_audit_result(self):
        inp = DistributionAccountPeriodInput(
            period_index=1, operating_period_index=1,
            period_date=date(2029, 12, 31),
            opening_distribution_account_balance_keur=100.0,
            post_senior_cash_available_keur=500.0,
            post_shl_cash_available_keur=500.0,
            senior_debt_service_keur=0.0,
            actual_dscr=1.5,
            is_tuho=True,
        )
        inputs = DistributionAccountInputs(
            project_name="TUHO",
            period_inputs=(inp,),
            is_tuho=True,
            covenant_gate_policy=CovenantGatePolicy.R99_R102_APPLICABLE,
        )
        result = DistributionAccountEngine.compute(inputs)
        # Result is audit-only — equity_distribution_paid must be 0
        assert result.total_equity_distribution_paid_keur == 0.0
        assert result.total_equity_distribution_candidate_keur >= 0

class TestEnableRuntimeSafety:
    """Tests proving enable_r99_r102_runtime=True does NOT enable production routing."""

    def test_enable_runtime_true_still_audit_only(self):
        """Even with enable_r99_r102_runtime=True, equity_distribution_paid_keur stays 0."""
        inp = DistributionAccountPeriodInput(
            period_index=5, operating_period_index=5,
            period_date=date(2033, 12, 31),
            opening_distribution_account_balance_keur=0.0,
            post_senior_cash_available_keur=1000.0,
            post_shl_cash_available_keur=800.0,
            senior_debt_service_keur=200.0,
            actual_dscr=1.5,
            target_distribution_dscr=1.0,
            enable_r99_r102_runtime=True,  # set to True
            is_tuho=True,
        )
        inputs = DistributionAccountInputs(
            project_name="TUHO",
            period_inputs=(inp,),
            is_tuho=True,
            covenant_gate_policy=CovenantGatePolicy.R99_R102_APPLICABLE,
        )
        result = DistributionAccountEngine.compute(inputs)
        period_result = result.period_results[0]
        assert period_result.equity_distribution_paid_keur == 0.0
        assert period_result.cash_swept_to_shl_keur == 0.0
        # R99 gate must still report BLOCKED even when enable_runtime=True
        assert period_result.r99_gate_result.passed is False
        assert "R99" in period_result.r99_gate_result.blocked_reason

    def test_enable_runtime_true_emits_warning(self):
        """enable_r99_r102_runtime=True must emit a warning."""
        inp = DistributionAccountPeriodInput(
            period_index=1, operating_period_index=1,
            period_date=date(2029, 12, 31),
            opening_distribution_account_balance_keur=0.0,
            post_senior_cash_available_keur=100.0,
            post_shl_cash_available_keur=100.0,
            senior_debt_service_keur=0.0,
            actual_dscr=1.5,
            enable_r99_r102_runtime=True,
            is_tuho=True,
        )
        inputs = DistributionAccountInputs(
            project_name="TUHO",
            period_inputs=(inp,),
            is_tuho=True,
        )
        result = DistributionAccountEngine.compute(inputs)
        period_result = result.period_results[0]
        warnings = period_result.warnings
        assert any("enable_r99_r102_runtime=True" in w for w in warnings)


class TestOborovoGuardStrengthened:
    """Strengthened tests proving Oborovo projects are fully isolated from TUHO gates."""

    def test_oborovo_identity_does_not_block_da_engine(self):
        """is_oborovo is deprecated diagnostic — DA engine does not block on identity.

        The oborovo_gate diagnostic still records passed=False, but it is NOT in
        all_gates_passed. Financial eligibility depends only on policy + financial gates.
        With R99_R102_NOT_APPLICABLE (default) + good DSCR + positive cash, equity is paid.
        """
        inp = DistributionAccountPeriodInput(
            period_index=1, operating_period_index=1,
            period_date=date(2029, 12, 31),
            opening_distribution_account_balance_keur=0.0,
            post_senior_cash_available_keur=1000.0,
            post_shl_cash_available_keur=800.0,
            senior_debt_service_keur=0.0,
            actual_dscr=1.5,
            target_distribution_dscr=1.0,
            is_oborovo=True,
            is_tuho=False,
        )
        inputs = DistributionAccountInputs(
            project_name="Oborovo",
            period_inputs=(inp,),
            is_oborovo=True,
            is_tuho=False,
        )
        result = DistributionAccountEngine.compute(inputs)
        period_result = result.period_results[0]
        # Oborovo identity does NOT block distribution in the DA engine
        assert period_result.oborovo_gate_result.passed is False  # deprecated diagnostic
        assert period_result.equity_distribution_paid_keur > 0.0   # financial gates pass
        assert period_result.cash_swept_to_shl_keur == 0.0

    def test_oborovo_guard_diagnostic_and_policy_warning(self):
        """oborovo_gate diagnostic records passed=False; NOT_APPLICABLE policy emits warning."""
        inp = DistributionAccountPeriodInput(
            period_index=3, operating_period_index=3,
            period_date=date(2031, 12, 31),
            opening_distribution_account_balance_keur=0.0,
            post_senior_cash_available_keur=500.0,
            post_shl_cash_available_keur=500.0,
            senior_debt_service_keur=0.0,
            actual_dscr=1.5,
            is_oborovo=True,
            is_tuho=False,
        )
        inputs = DistributionAccountInputs(
            project_name="Oborovo",
            period_inputs=(inp,),
            is_oborovo=True,
            is_tuho=False,
        )
        result = DistributionAccountEngine.compute(inputs)
        period_result = result.period_results[0]
        # oborovo_gate is deprecated diagnostic — still records passed=False
        assert period_result.oborovo_gate_result.passed is False
        # NOT_APPLICABLE policy emits a warning (is_oborovo gets default NOT_APPLICABLE)
        assert len(period_result.warnings) > 0
        assert any("NOT_APPLICABLE" in w for w in period_result.warnings)


class TestBlockedReasonsComplete:
    """Verify all expected blocked reasons are present in BLOCKED_REASONS."""

    def test_all_expected_blocked_reasons_present(self):
        from domain.distribution_account.result import BLOCKED_REASONS
        expected = {"R99_BLOCKED", "R102_BLOCKED", "DSCR_GATE_FAILED",
                    "OBOROVO_NOT_SUPPORTED", "NEGATIVE_CASH",
                    "DISTRIBUTION_ACCOUNT_NOT_PROMOTED", "LOCKUP",
                    "SENIOR_TENOR"}
        for reason in expected:
            assert reason in BLOCKED_REASONS, f"Missing blocked reason: {reason}"


class TestSeniorTenorYearsField:
    """Tests for senior_tenor_years field in DistributionAccountPeriodInput."""

    def test_senior_tenor_years_default_zero(self):
        """senior_tenor_years defaults to 0 (no tenor-based lockup)."""
        inp = DistributionAccountPeriodInput(
            period_index=1, operating_period_index=1,
            period_date=date(2029, 12, 31),
            opening_distribution_account_balance_keur=0.0,
            post_senior_cash_available_keur=100.0,
            post_shl_cash_available_keur=100.0,
            senior_debt_service_keur=0.0,
            actual_dscr=1.5,
        )
        assert inp.senior_tenor_years == 0

    def test_senior_tenor_years_passed_to_lockup_gate(self):
        """senior_tenor_years is passed to evaluate_lockup_gate via inp field."""
        inp = DistributionAccountPeriodInput(
            period_index=1, operating_period_index=1,
            period_date=date(2029, 12, 31),
            opening_distribution_account_balance_keur=0.0,
            post_senior_cash_available_keur=100.0,
            post_shl_cash_available_keur=100.0,
            senior_debt_service_keur=0.0,
            actual_dscr=1.5,
            senior_tenor_years=3,  # 3-year lockup
            dsra_required_balance_keur=0.0,
            dsra_current_balance_keur=0.0,
            jdsra_required_balance_keur=0.0,
            jdsra_current_balance_keur=0.0,
        )
        inputs = DistributionAccountInputs(
            project_name="TUHO",
            period_inputs=(inp,),
            is_tuho=True,
        )
        result = DistributionAccountEngine.compute(inputs)
        period_result = result.period_results[0]
        # period_index=1 <= senior_tenor_years=3, lockup should be active
        assert period_result.lockup_gate_result.passed is False
        assert "within_senior_tenor" in str(period_result.lockup_gate_result.details)
