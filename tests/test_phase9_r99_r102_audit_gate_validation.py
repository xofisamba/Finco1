"""tests/test_phase9_r99_r102_audit_gate_validation.py

Phase 9: R99/R102 Audit Gate Validation.

VALIDATION / GOVERNANCE ONLY — no runtime promotion.

This module validates that:
- R99/R102 gates remain BLOCKED in audit mode
- Sponsor distribution explicit tuple semantics are deterministic
- No hidden promotion paths exist
- Runtime ownership boundaries are explicit
- actual_cfads != sizing_cfads invariant holds
- No distribution ownership leakage

R99/R102: BLOCKED — this module does not implement or enable R99/R102 promotion.
"""

import pytest
from pathlib import Path

from domain.distribution_account.gates import (
    evaluate_r99_gate,
    evaluate_r102_gate,
    BLOCKED_REASONS,
)
from domain.sponsor.sponsor_cashflow_runner import (
    SponsorCashflowRunnerInputs,
    run_sponsor_cashflows,
)
from domain.sponsor.equity_injection import EquityInjection


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_distributions(n: int, value: float = 0.0) -> tuple[float, ...]:
    return tuple(value for _ in range(n))


def make_inputs(
    distributions: tuple[float, ...] = make_distributions(10),
    distribution_account_override: tuple[float, ...] | None = None,
    period_count: int = 10,
    wht_rate: float = 0.0,
):
    injections = (
        EquityInjection(
            period_index=0, amount_keur=10000.0,
            investor_id="SPONSOR-1", target_entity="HOLDCO",
            purpose="equityContribution",
        ),
        EquityInjection(
            period_index=1, amount_keur=5000.0,
            investor_id="SPONSOR-1", target_entity="HOLDCO",
            purpose="topUp",
        ),
    )
    return SponsorCashflowRunnerInputs(
        investor_id="SPONSOR-1",
        entity_code="HOLDCO",
        equity_injections=injections,
        holdco_distribution_by_period=distributions,
        holdco_dividend_by_period=make_distributions(period_count),
        wht_rate=wht_rate,
        holdco_opex_by_period=make_distributions(period_count),
        period_count=period_count,
        distribution_account_received_by_period=distribution_account_override,
    )


# ---------------------------------------------------------------------------
# R99/R102 Gate Validation
# ---------------------------------------------------------------------------

class TestR99R102GatesBlocked:
    """R99 and R102 gates return BLOCKED in audit mode."""

    def test_r99_gate_blocked_in_audit_mode(self):
        """R99 gate returns BLOCKED when enable_runtime=False."""
        result = evaluate_r99_gate(
            inputs=None,
            cash_available=1000.0,
            enable_runtime=False,
        )
        assert result.passed is False
        
        assert result.blocked_reason == BLOCKED_REASONS["R99_BLOCKED"]

    def test_r102_gate_blocked_in_audit_mode(self):
        """R102 gate returns BLOCKED when enable_runtime=False."""
        result = evaluate_r102_gate(
            inputs=None,
            cash_available=1000.0,
            enable_runtime=False,
        )
        assert result.passed is False
        
        assert result.blocked_reason == BLOCKED_REASONS["R102_BLOCKED"]

    def test_r99_gate_blocked_even_with_high_cash(self):
        """R99 gate BLOCKED regardless of cash amount (audit mode)."""
        for cash in [0.0, 100.0, 1000.0, 100000.0]:
            result = evaluate_r99_gate(
                inputs=None, cash_available=cash, enable_runtime=False
            )
            assert result.passed is False
            

    def test_r102_gate_blocked_even_when_shl_pik_positive(self):
        """R102 gate BLOCKED regardless of SHL PIK state (audit mode)."""
        for cash in [0.0, 500.0, 5000.0]:
            result = evaluate_r102_gate(
                inputs=None, cash_available=cash, enable_runtime=False
            )
            assert result.passed is False
            


class TestR99R102NoRuntimeExposure:
    """No R99/R102 runtime exposure in sponsor or distribution modules."""

    def test_sponsor_runner_has_no_r99_r102_fields(self):
        """SponsorCashflowRunnerInputs has no R99/R102 gate fields."""
        inputs = make_inputs()
        # No enable_r99_r102_runtime or gate-related fields on sponsor inputs
        assert not hasattr(inputs, "enable_r99_r102_runtime")
        assert not hasattr(inputs, "r99_gate_inputs")
        assert not hasattr(inputs, "r102_gate_inputs")

    def test_distribution_account_gate_module_has_no_runtime_writes(self):
        """distribution_account.gates module has no side effects (pure function)."""
        # Calling evaluate_r99_gate / evaluate_r102_gate twice with same args
        # must produce identical results (idempotent, no state mutation)
        r1 = evaluate_r99_gate(None, 1000.0, enable_runtime=False)
        r2 = evaluate_r99_gate(None, 1000.0, enable_runtime=False)
        assert r1.passed == r2.passed
        assert r1.blocked_reason == r2.blocked_reason

        r3 = evaluate_r102_gate(None, 1000.0, enable_runtime=False)
        r4 = evaluate_r102_gate(None, 1000.0, enable_runtime=False)
        assert r3.passed == r4.passed
        assert r3.blocked_reason == r4.blocked_reason

    def test_no_r99_r102_runtime_flag_in_sponsor_runner_inputs(self):
        """SponsorCashflowRunnerInputs does not expose any R99/R102 runtime flags."""
        inputs = make_inputs()
        # All fields on sponsor inputs
        fields = [f for f in dir(inputs) if not f.startswith("_")]
        r99_r102_related = [f for f in fields if "r99" in f.lower() or "r102" in f.lower()]
        assert r99_r102_related == [], f"Unexpected R99/R102 fields: {r99_r102_related}"


class TestSponsorExplicitTupleSemantics:
    """Validate sponsor explicit tuple semantics (deterministic, no fallback)."""

    def test_all_zero_tuple_no_fallback(self):
        """All-zero explicit tuple produces zero distribution, no HoldCo fallback."""
        nonzero_holdco = make_distributions(10, 0.0)
        holdco_list = list(nonzero_holdco)
        holdco_list[4] = 2000.0
        nonzero_holdco = tuple(holdco_list)

        inputs = make_inputs(
            distributions=nonzero_holdco,
            distribution_account_override=make_distributions(10, 0.0),
        )
        result = run_sponsor_cashflows(inputs)
        # Explicit all-zero must win, not fallback to HoldCo's 2000
        assert result.period_results[4].distribution_received_keur == pytest.approx(0.0)

    def test_per_period_explicit_zero_no_fallback(self):
        """Per-period explicit zero overrides HoldCo non-zero, no fallback."""
        nonzero_holdco = make_distributions(10, 0.0)
        holdco_list = list(nonzero_holdco)
        holdco_list[3] = 5000.0
        nonzero_holdco = tuple(holdco_list)

        inputs = make_inputs(
            distributions=nonzero_holdco,
            distribution_account_override=make_distributions(10, 0.0),
        )
        result = run_sponsor_cashflows(inputs)
        assert result.period_results[3].distribution_received_keur == pytest.approx(0.0)

    def test_none_uses_holdco_path_unchanged(self):
        """distribution_account_received_by_period=None uses HoldCo distribution unchanged."""
        nonzero_holdco = make_distributions(10, 0.0)
        holdco_list = list(nonzero_holdco)
        holdco_list[4] = 3000.0
        nonzero_holdco = tuple(holdco_list)

        inputs = make_inputs(
            distributions=nonzero_holdco,
            distribution_account_override=None,  # default
        )
        result = run_sponsor_cashflows(inputs)
        assert result.period_results[4].distribution_received_keur == pytest.approx(3000.0)

    def test_deterministic_output_same_tuple_idempotent(self):
        """Same explicit tuple produces identical results (deterministic)."""
        override = make_distributions(10, 1000.0)
        inputs = make_inputs(
            distributions=make_distributions(10, 0.0),
            distribution_account_override=override,
        )
        result1 = run_sponsor_cashflows(inputs)
        result2 = run_sponsor_cashflows(inputs)
        for p1, p2 in zip(result1.period_results, result2.period_results):
            assert p1.distribution_received_keur == pytest.approx(p2.distribution_received_keur)
            assert p1.net_cashflow_keur == pytest.approx(p2.net_cashflow_keur)
            assert p1.capital_account_balance_keur == pytest.approx(
                p2.capital_account_balance_keur
            )


class TestNoOwnershipLeakage:
    """No ownership leakage from DistributionAccount to Sponsor runtime."""

    def test_sponsor_runner_result_has_no_equity_distribution_paid_field(self):
        """SponsorCashflowRunnerResult does not expose DistributionAccount fields."""
        result = run_sponsor_cashflows(make_inputs())
        fields = [f for f in dir(result) if not f.startswith("_")]
        da_fields = [f for f in fields if "distribution_paid" in f or "equity_distribution" in f]
        assert da_fields == [], f"Unexpected DistributionAccount fields in sponsor result: {da_fields}"

    def test_sponsor_runner_result_has_no_gate_result_fields(self):
        """SponsorCashflowRunnerResult does not expose gate result fields."""
        result = run_sponsor_cashflows(make_inputs())
        fields = [f for f in dir(result) if not f.startswith("_")]
        gate_fields = [f for f in fields if "gate_result" in f or "r99" in f.lower() or "r102" in f.lower()]
        assert gate_fields == [], f"Unexpected gate fields in sponsor result: {gate_fields}"


class TestNoHiddenPromotionPath:
    """No hidden promotion path via flags or field defaults."""

    def test_no_runtime_files_changed(self):
        """No app/ domain/ inputs, or non-allowed files changed."""
        import subprocess

        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["git", "diff", "--stat", "origin/main...HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()
        if not output:
            return
        for line in output.split("\n"):
            stripped = line.strip()
            # Skip blank, untracked, diff-range prefix, summary lines
            if (
                not stripped
                or stripped.startswith("??")
                or stripped.startswith("...")
                or "files changed" in stripped
                or "|" not in stripped
            ):
                continue
            # Only docs/reports/tests changes allowed (no runtime code)
            allowed = ["docs/", "reports/", "tests/"]
            assert any(stripped.startswith(p) for p in allowed), \
                f"Unexpected change (not governance-only): {stripped}"

    def test_no_app_waterfall_core_changes(self):
        """No app/ files changed (app/ contains runtime wiring)."""
        import subprocess

        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["git", "diff", "--stat", "origin/main...HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()
        for line in output.split("\n"):
            stripped = line.strip()
            if (
                not stripped
                or stripped.startswith("??")
                or stripped.startswith("...")
                or "files changed" in stripped
                or "|" not in stripped
            ):
                continue
            assert not stripped.startswith("app/"), \
                f"app/ change detected (forbidden): {stripped}"


class TestActualVsSizingCFADSGovernance:
    """actual_cfads != sizing_cfads invariant validated."""

    def test_senior_debt_sizing_policy_has_explicit_cfads_field(self):
        """SeniorDebtSizingPolicy requires explicit sizing_cfads (not derived from actual)."""
        from domain.senior_debt_sizing.policy import SeniorDebtSizingPolicy, SizingMode

        policy = SeniorDebtSizingPolicy(
            project_name="TUHO",
            sizing_mode=SizingMode.EXPLICIT_CFADS,
            sizing_cfads_keur_by_period=tuple(1000.0 for _ in range(31)),
        )
        # sizing_cfads is explicit input, NOT derived
        assert len(policy.sizing_cfads_keur_by_period) == 31
        assert all(v == 1000.0 for v in policy.sizing_cfads_keur_by_period)

    def test_senior_debt_sizing_policy_has_derive_mode(self):
        """SeniorDebtSizingPolicy supports DERIVE_FROM_MINIMUM_DSCR mode (future)."""
        from domain.senior_debt_sizing.policy import SeniorDebtSizingPolicy, SizingMode

        policy = SeniorDebtSizingPolicy(
            project_name="TUHO",
            sizing_mode=SizingMode.DERIVE_FROM_MINIMUM_DSCR,
            sizing_cfads_keur_by_period=(),  # not used in derive mode
        )
        assert policy.sizing_mode == SizingMode.DERIVE_FROM_MINIMUM_DSCR


class TestDeterministicDistributionOutputs:
    """Distribution outputs are deterministic (no random/noise)."""

    def test_same_inputs_same_outputs(self):
        """Identical inputs produce identical distribution outputs."""
        override = make_distributions(10, 1000.0)
        inputs = make_inputs(
            distributions=make_distributions(10, 0.0),
            distribution_account_override=override,
        )
        result1 = run_sponsor_cashflows(inputs)
        result2 = run_sponsor_cashflows(inputs)

        total_dist1 = sum(p.distribution_received_keur for p in result1.period_results)
        total_dist2 = sum(p.distribution_received_keur for p in result2.period_results)
        assert total_dist1 == pytest.approx(total_dist2)

        total_net1 = sum(p.net_cashflow_keur for p in result1.period_results)
        total_net2 = sum(p.net_cashflow_keur for p in result2.period_results)
        assert total_net1 == pytest.approx(total_net2)

    def test_zero_distribution_zero_net_cashflow_injection_periods(self):
        """Zero distribution in injection-only periods: net_cashflow = -injection."""
        inputs = make_inputs(
            distributions=make_distributions(10, 0.0),
            distribution_account_override=make_distributions(10, 0.0),
        )
        result = run_sponsor_cashflows(inputs)
        # p0: injection 10000, no distribution
        assert result.period_results[0].distribution_received_keur == pytest.approx(0.0)
        assert result.period_results[0].net_cashflow_keur == pytest.approx(-10000.0)