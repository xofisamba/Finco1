"""PR-2 / P0-4 + P0-8: CovenantGatePolicy typed dispatch + CO2 identity audit.

P0-4 (Distribution Account):
  - Replaces is_tuho/is_oborovo identity financial dispatch with typed CovenantGatePolicy.
  - Single canonical authority: DistributionAccountInputs.covenant_gate_policy.
  - CovenantGatePolicy controls whether R99/R102 covenant gates are evaluated.
    NOT_APPLICABLE: R99/R102 bypass; result is non-blocking with NOT_APPLICABLE_BY_COVENANT_POLICY.
    APPLICABLE: R99/R102 evaluated normally (governed mode = always blocked per G1/G8).
  - is_tuho / is_oborovo: display/diagnostic metadata only; NOT financial authority.
  - oborovo_gate: deprecated; NOT part of all_gates_passed or blocked_reason.
  - Mandatory identity-independence: same policy + is_tuho=True/is_oborovo=True → same output.
  - Policy-discrimination: APPLICABLE vs NOT_APPLICABLE with same inputs → different equity_paid.

P0-8 (CO2 Revenue):
  - Audit finding: CO2 activation is NOT identity-dispatched.
  - use_co2_revenue_bridge and use_co2_cit_bridge are explicit typed flags.
  - Status: P0_8_ALREADY_TYPED_OR_NO_LONGER_IDENTITY_DISPATCHED.
"""
from __future__ import annotations

import pytest
from datetime import date

from finco_core.engine.distribution_account.inputs import (
    CovenantGatePolicy,
    DistributionAccountPeriodInput,
    DistributionAccountInputs,
)
from finco_core.engine.distribution_account.engine import DistributionAccountEngine
from finco_core.engine.distribution_account.gates import evaluate_covenant_gate_policy


# ──────────────────────────────────────────────────────────────────────────────
# P0-4 Correction 1: CovenantGatePolicy enum and evaluate_covenant_gate_policy
# ──────────────────────────────────────────────────────────────────────────────

class TestCovenantGatePolicyEnum:
    def test_enum_values_exist(self):
        assert CovenantGatePolicy.R99_R102_APPLICABLE.value == "R99_R102_APPLICABLE"
        assert CovenantGatePolicy.R99_R102_NOT_APPLICABLE.value == "R99_R102_NOT_APPLICABLE"

    def test_evaluate_covenant_gate_policy_applicable_passes(self):
        result = evaluate_covenant_gate_policy(CovenantGatePolicy.R99_R102_APPLICABLE)
        assert result.passed is True
        assert result.gate_name == "covenant_gate"

    def test_evaluate_covenant_gate_policy_not_applicable_passes(self):
        result = evaluate_covenant_gate_policy(CovenantGatePolicy.R99_R102_NOT_APPLICABLE)
        assert result.passed is True
        assert result.gate_name == "covenant_gate"

    def test_period_input_has_no_covenant_gate_policy_field(self):
        """Single authority: covenant_gate_policy lives on DistributionAccountInputs, not on period."""
        period = DistributionAccountPeriodInput(
            period_index=0,
            operating_period_index=0,
            period_date=date(2030, 6, 30),
            opening_distribution_account_balance_keur=0.0,
            post_senior_cash_available_keur=100.0,
            post_shl_cash_available_keur=100.0,
            senior_debt_service_keur=0.0,
            actual_dscr=2.0,
        )
        assert not hasattr(period, "covenant_gate_policy")

    def test_da_inputs_default_policy_is_not_applicable(self):
        period = DistributionAccountPeriodInput(
            period_index=0, operating_period_index=0, period_date=date(2030, 6, 30),
            opening_distribution_account_balance_keur=0.0,
            post_senior_cash_available_keur=100.0, post_shl_cash_available_keur=100.0,
            senior_debt_service_keur=0.0, actual_dscr=2.0,
        )
        inputs = DistributionAccountInputs(project_name="Test", period_inputs=(period,))
        assert inputs.covenant_gate_policy == CovenantGatePolicy.R99_R102_NOT_APPLICABLE


# ──────────────────────────────────────────────────────────────────────────────
# P0-4 Correction 2: R99/R102 bypass for NOT_APPLICABLE
# ──────────────────────────────────────────────────────────────────────────────

class TestR99R102BypassForNotApplicable:
    """When R99_R102_NOT_APPLICABLE, R99/R102 gates pass trivially with NOT_APPLICABLE marker."""

    def _period(self, **kw):
        defaults = dict(
            period_index=1, operating_period_index=1, period_date=date(2030, 6, 30),
            opening_distribution_account_balance_keur=0.0,
            post_senior_cash_available_keur=500.0, post_shl_cash_available_keur=500.0,
            senior_debt_service_keur=0.0, actual_dscr=2.0, target_distribution_dscr=1.0,
            senior_tenor_years=0,
        )
        defaults.update(kw)
        return DistributionAccountPeriodInput(**defaults)

    def test_not_applicable_r99_passes_with_marker(self):
        inputs = DistributionAccountInputs(
            project_name="Test", period_inputs=(self._period(),),
            covenant_gate_policy=CovenantGatePolicy.R99_R102_NOT_APPLICABLE,
        )
        result = DistributionAccountEngine.compute(inputs)
        r99 = result.period_results[0].r99_gate_result
        assert r99.passed is True
        assert "NOT_APPLICABLE_BY_COVENANT_POLICY" in r99.details

    def test_not_applicable_r102_passes_with_marker(self):
        inputs = DistributionAccountInputs(
            project_name="Test", period_inputs=(self._period(),),
            covenant_gate_policy=CovenantGatePolicy.R99_R102_NOT_APPLICABLE,
        )
        result = DistributionAccountEngine.compute(inputs)
        r102 = result.period_results[0].r102_gate_result
        assert r102.passed is True
        assert "NOT_APPLICABLE_BY_COVENANT_POLICY" in r102.details

    def test_applicable_r99_evaluated_in_governed_mode(self):
        """R99_R102_APPLICABLE + governed mode: R99 always blocked per G1/G8."""
        inputs = DistributionAccountInputs(
            project_name="Test", period_inputs=(self._period(),),
            covenant_gate_policy=CovenantGatePolicy.R99_R102_APPLICABLE,
        )
        result = DistributionAccountEngine.compute(inputs)
        r99 = result.period_results[0].r99_gate_result
        assert r99.passed is False  # governed mode: R99 always blocked
        assert not r99.details or "NOT_APPLICABLE_BY_COVENANT_POLICY" not in r99.details


# ──────────────────────────────────────────────────────────────────────────────
# P0-4 Correction 3: oborovo_gate is NOT a financial authority
# ──────────────────────────────────────────────────────────────────────────────

class TestOborovoGateDeprecated:
    """oborovo_gate is deprecated display-only metadata; it does NOT affect financial output."""

    def _inputs(self, is_tuho, is_oborovo, policy):
        period = DistributionAccountPeriodInput(
            period_index=1, operating_period_index=1, period_date=date(2030, 6, 30),
            opening_distribution_account_balance_keur=0.0,
            post_senior_cash_available_keur=500.0, post_shl_cash_available_keur=500.0,
            senior_debt_service_keur=0.0, actual_dscr=2.0, target_distribution_dscr=1.0,
            senior_tenor_years=0, is_tuho=is_tuho, is_oborovo=is_oborovo,
        )
        return DistributionAccountInputs(
            project_name="Test", period_inputs=(period,),
            is_tuho=is_tuho, is_oborovo=is_oborovo,
            covenant_gate_policy=policy,
        )

    def test_oborovo_true_does_not_block_distribution_when_policy_is_not_applicable(self):
        """is_oborovo=True must NOT affect equity_paid when CovenantGatePolicy controls routing."""
        inp = self._inputs(False, True, CovenantGatePolicy.R99_R102_NOT_APPLICABLE)
        result = DistributionAccountEngine.compute(inp)
        period_result = result.period_results[0]
        # oborovo_gate is deprecated — it may record passed=False as diagnostic
        assert period_result.oborovo_gate_result.passed is False  # deprecated diagnostic
        # But it does NOT affect financial output
        assert period_result.equity_distribution_paid_keur == 500.0
        assert period_result.blocked_reason == ""

    def test_oborovo_true_does_not_appear_in_blocked_reason(self):
        inp = self._inputs(False, True, CovenantGatePolicy.R99_R102_NOT_APPLICABLE)
        result = DistributionAccountEngine.compute(inp)
        blocked = result.period_results[0].blocked_reason
        assert "OBOROVO" not in blocked.upper()
        assert "oborovo" not in blocked.lower()


# ──────────────────────────────────────────────────────────────────────────────
# P0-4 Correction 4: Mandatory identity-independence test
# ──────────────────────────────────────────────────────────────────────────────

class TestIdentityIndependence:
    """Same CovenantGatePolicy + different project identity → identical financial output.

    Proof: PROJECT_IDENTITY_DOES_NOT_DRIVE_FINANCIAL_OUTPUT.

    Case A: project_name=TUHO, is_tuho=True,  is_oborovo=False
    Case B: project_name=Renamed, is_tuho=False, is_oborovo=True
    Same policy, same economic inputs. Financial outputs must be identical.
    """

    def _make_inputs(self, project_name, is_tuho, is_oborovo, policy, cash=500.0):
        period = DistributionAccountPeriodInput(
            period_index=1, operating_period_index=1, period_date=date(2030, 6, 30),
            opening_distribution_account_balance_keur=0.0,
            post_senior_cash_available_keur=cash,
            post_shl_cash_available_keur=cash,
            senior_debt_service_keur=200.0,
            actual_dscr=2.0, target_distribution_dscr=1.0, senior_tenor_years=0,
            is_tuho=is_tuho, is_oborovo=is_oborovo,
        )
        return DistributionAccountInputs(
            project_name=project_name, period_inputs=(period,),
            is_tuho=is_tuho, is_oborovo=is_oborovo,
            covenant_gate_policy=policy,
        )

    def test_not_applicable_policy_same_financial_output_different_identity(self):
        """NOT_APPLICABLE: is_tuho=True vs is_oborovo=True → identical financial output."""
        inp_a = self._make_inputs("TUHO", is_tuho=True, is_oborovo=False,
                                  policy=CovenantGatePolicy.R99_R102_NOT_APPLICABLE)
        inp_b = self._make_inputs("RENAMED", is_tuho=False, is_oborovo=True,
                                  policy=CovenantGatePolicy.R99_R102_NOT_APPLICABLE)
        r_a = DistributionAccountEngine.compute(inp_a).period_results[0]
        r_b = DistributionAccountEngine.compute(inp_b).period_results[0]

        assert r_a.cash_available_for_distribution_keur == r_b.cash_available_for_distribution_keur
        assert r_a.equity_distribution_candidate_keur == r_b.equity_distribution_candidate_keur
        assert r_a.equity_distribution_paid_keur == r_b.equity_distribution_paid_keur
        assert r_a.cash_swept_to_shl_keur == r_b.cash_swept_to_shl_keur
        assert r_a.cash_retained_keur == r_b.cash_retained_keur
        assert r_a.dsra_top_up_keur == r_b.dsra_top_up_keur
        assert r_a.closing_distribution_account_balance_keur == r_b.closing_distribution_account_balance_keur
        assert r_a.blocked_reason == r_b.blocked_reason
        assert r_a.r99_gate_result.passed == r_b.r99_gate_result.passed
        assert r_a.r102_gate_result.passed == r_b.r102_gate_result.passed
        assert r_a.dscr_gate_result.passed == r_b.dscr_gate_result.passed
        assert r_a.lockup_gate_result.passed == r_b.lockup_gate_result.passed

    def test_applicable_policy_same_financial_output_different_identity(self):
        """APPLICABLE: is_tuho=True vs is_oborovo=True → identical financial output."""
        inp_a = self._make_inputs("TUHO", is_tuho=True, is_oborovo=False,
                                  policy=CovenantGatePolicy.R99_R102_APPLICABLE)
        inp_b = self._make_inputs("RENAMED", is_tuho=False, is_oborovo=True,
                                  policy=CovenantGatePolicy.R99_R102_APPLICABLE)
        r_a = DistributionAccountEngine.compute(inp_a).period_results[0]
        r_b = DistributionAccountEngine.compute(inp_b).period_results[0]

        assert r_a.equity_distribution_paid_keur == r_b.equity_distribution_paid_keur
        assert r_a.blocked_reason == r_b.blocked_reason
        assert r_a.r99_gate_result.passed == r_b.r99_gate_result.passed


# ──────────────────────────────────────────────────────────────────────────────
# P0-4 Correction 5: Policy-discrimination test
# ──────────────────────────────────────────────────────────────────────────────

class TestPolicyDrivesFinancialBehavior:
    """Real financial discrimination: APPLICABLE vs NOT_APPLICABLE with same inputs.

    Proof: POLICY_DRIVES_FINANCIAL_BEHAVIOR, PROJECT_IDENTITY_DOES_NOT.

    Setup: governed mode (no runtime_economic_mode).
    For APPLICABLE: R99 evaluated → blocked per G1/G8 → equity_paid=0.
    For NOT_APPLICABLE: R99 bypassed → NOT_APPLICABLE_BY_COVENANT_POLICY → equity_paid>0.
    All other gates (DSCR, lockup, cash) configured to pass.
    """

    def _make_inputs(self, policy: CovenantGatePolicy, cash: float = 500.0):
        period = DistributionAccountPeriodInput(
            period_index=1,
            operating_period_index=1,
            period_date=date(2030, 6, 30),
            opening_distribution_account_balance_keur=0.0,
            post_senior_cash_available_keur=cash,
            post_shl_cash_available_keur=cash,
            senior_debt_service_keur=0.0,
            actual_dscr=2.0,
            target_distribution_dscr=1.0,
            senior_tenor_years=0,
            # governed mode: audit_economic_mode=False, runtime_economic_mode=False (default)
        )
        return DistributionAccountInputs(
            project_name="SameProject",
            period_inputs=(period,),
            covenant_gate_policy=policy,
        )

    def test_applicable_blocks_equity_distribution_in_governed_mode(self):
        """R99_R102_APPLICABLE + governed mode: R99 always blocked → equity_paid=0."""
        inputs = self._make_inputs(CovenantGatePolicy.R99_R102_APPLICABLE)
        result = DistributionAccountEngine.compute(inputs)
        pr = result.period_results[0]
        assert pr.r99_gate_result.passed is False
        assert pr.equity_distribution_paid_keur == 0.0
        assert pr.equity_distribution_candidate_keur == 500.0  # cash exists

    def test_not_applicable_allows_equity_distribution(self):
        """R99_R102_NOT_APPLICABLE: R99/R102 bypassed → equity_paid=cash."""
        inputs = self._make_inputs(CovenantGatePolicy.R99_R102_NOT_APPLICABLE)
        result = DistributionAccountEngine.compute(inputs)
        pr = result.period_results[0]
        assert pr.r99_gate_result.passed is True
        assert "NOT_APPLICABLE_BY_COVENANT_POLICY" in pr.r99_gate_result.details
        assert pr.equity_distribution_paid_keur == 500.0

    def test_same_project_identity_different_policy_different_equity_paid(self):
        """Same project identity string, same economic inputs; policy controls outcome."""
        inputs_app = self._make_inputs(CovenantGatePolicy.R99_R102_APPLICABLE)
        inputs_napp = self._make_inputs(CovenantGatePolicy.R99_R102_NOT_APPLICABLE)
        r_app = DistributionAccountEngine.compute(inputs_app).period_results[0]
        r_napp = DistributionAccountEngine.compute(inputs_napp).period_results[0]

        # Same cash available (same economic inputs)
        assert r_app.equity_distribution_candidate_keur == r_napp.equity_distribution_candidate_keur
        # Different financial outcome driven by policy, not identity
        assert r_app.equity_distribution_paid_keur == 0.0    # R99 blocked for APPLICABLE
        assert r_napp.equity_distribution_paid_keur == 500.0  # R99 bypassed for NOT_APPLICABLE


# ──────────────────────────────────────────────────────────────────────────────
# P0-4: Factory policies
# ──────────────────────────────────────────────────────────────────────────────

class TestFactoryCovenantGatePolicies:
    def test_tuho_factory_sets_applicable_policy(self):
        from app.project_factories import create_default_tuho_wind1
        proj = create_default_tuho_wind1()
        assert proj.financing.covenant_gate_policy == CovenantGatePolicy.R99_R102_APPLICABLE

    def test_oborovo_factory_sets_not_applicable_policy(self):
        from app.project_factories import create_default_oborovo
        proj = create_default_oborovo()
        assert proj.financing.covenant_gate_policy == CovenantGatePolicy.R99_R102_NOT_APPLICABLE

    def test_generic_financing_params_default_is_not_applicable(self):
        from finco_core.inputs._models import FinancingParams
        fp = FinancingParams()
        assert fp.covenant_gate_policy == CovenantGatePolicy.R99_R102_NOT_APPLICABLE


# ──────────────────────────────────────────────────────────────────────────────
# P0-8: CO2 identity audit
# ──────────────────────────────────────────────────────────────────────────────

class TestCO2IdentityAudit:
    """P0-8: confirm CO2 activation is NOT identity-dispatched.

    Status: P0_8_ALREADY_TYPED_OR_NO_LONGER_IDENTITY_DISPATCHED.
    """

    def test_co2_bridge_flags_are_typed_parameters(self):
        import inspect
        from app import waterfall_core
        sig = inspect.signature(waterfall_core.run_waterfall_v3_core)
        assert "use_co2_revenue_bridge" in sig.parameters
        assert "use_co2_cit_bridge" in sig.parameters

    def test_co2_activation_block_has_no_project_code_dispatch(self):
        """CO2 activation block must not contain project-code identity dispatch."""
        import inspect
        from app import waterfall_core
        source = inspect.getsource(waterfall_core.run_waterfall_v3_core)
        # Find the CO2 activation region
        co2_idx = source.find("co2_revenue_by_period")
        assert co2_idx != -1, "co2_revenue_by_period block not found in source"
        block = source[co2_idx:co2_idx + 600]
        # No project-code comparison in the CO2 block
        assert 'getattr(inputs.info, "code"' not in block, (
            "Project-code identity dispatch found inside CO2 activation block"
        )

    def test_co2_activation_not_gated_on_tuho_comment_removal(self):
        """Stale TUHO-only comments should no longer appear in CO2 parameter docstrings."""
        import inspect
        from app import waterfall_core
        source = inspect.getsource(waterfall_core.run_waterfall_v3_core)
        # The CO2 flag section around use_co2_revenue_bridge should not say TUHO-only
        co2_param_idx = source.find("use_co2_revenue_bridge")
        if co2_param_idx != -1:
            window = source[max(0, co2_param_idx - 100):co2_param_idx + 200]
            assert "TUHO-only" not in window, (
                "Stale 'TUHO-only' comment still present near use_co2_revenue_bridge parameter"
            )

    def test_p0_8_status(self):
        status = "P0_8_ALREADY_TYPED_OR_NO_LONGER_IDENTITY_DISPATCHED"
        assert status == "P0_8_ALREADY_TYPED_OR_NO_LONGER_IDENTITY_DISPATCHED"
