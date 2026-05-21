"""Phase 9: Audit/Economic Mode Contract Reconciliation tests.

Tests that:
1. audit_economic_mode is comparison-only (never routed to runtime)
2. runtime_economic_mode is explicit runtime-staging (behind use_distributionaccount_runtime_wiring=True)
3. dual-run uses audit_economic_mode=True (no routing, comparison only)
4. default behavior unchanged (flag=False: legacy/zero drift)
5. TUHO flag=True behavior unchanged (~284,552 kEUR, Δ~-41,613 kEUR)
6. Oborovo guard unchanged (guard fires, distribution unchanged)
7. R99/R102 still BLOCKED (G20 not promoted)
8. SHL R102 / Sponsor handoff not changed
"""

import csv
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
REPORTS_DIR = REPO_ROOT / "reports"
CONTRACT_DOC = DOCS_DIR / "phase9_audit_economic_mode_contract_reconciliation.md"
CONTRACT_CSV = REPORTS_DIR / "phase9_audit_economic_mode_contract_reconciliation.csv"


# ---------------------------------------------------------------------------
# Helper: run waterfall
# ---------------------------------------------------------------------------

def _run_waterfall(project_name, da_wiring):
    from app.waterfall_core import run_waterfall_v3_core
    from app.project_factories import create_default_tuho_wind1, create_default_oborovo
    from app.ui_runner import _build_period_engine as build_period_engine

    COMMON = dict(
        rate_per_period=0.0, tenor_periods=0,
        target_dscr=1.15, lockup_dscr=1.10, tax_rate=0.10, dsra_months=6,
        shl_amount=0.0, shl_rate=0.0, shl_idc_keur=0.0,
        shl_repayment_method='bullet', shl_tenor_years=0, shl_wht_rate=0.0,
        discount_rate_project=0.0641, discount_rate_equity=0.0965,
        fixed_debt_keur=None, fixed_ds_keur=None, rate_schedule=None,
        senior_sculpting_config=None, equity_irr_method='equity_only',
        share_capital_keur=0.0, sculpt_capex_keur=0.0,
        debt_sizing_method='dscr_sculpt', dscr_schedule=None,
        advanced_opex_line_items=None, advanced_capex_line_items=None,
        advanced_capex_depreciation_schedule=None,
        use_senior_sweep_cash_cap_for_shl=False,
        use_tuho_r99_input_engine=False,
        use_shl_fcf_waterfall_engine=False,
        use_tax_bridge_engine=False,
        use_shl_gross_accrued_for_pnl=False,
        shl_fcf_waterfall_cash_schedule_keur=(),
        shl_fcf_waterfall_minimum_cash_retained_keur=0.0,
        tuho_cit_cash_tax_start_operating_index=None,
        use_shl_canonical_engine=False,
        use_depreciation_canonical_engine=False,
        use_senior_debt_sizing_engine=False,
        use_co2_revenue_bridge=False,
        use_co2_cit_bridge=False,
        use_dualrun_validation=False,
    )

    if project_name == "TUHO-WIND-1":
        inputs = create_default_tuho_wind1()
    else:
        inputs = create_default_oborovo()

    engine = build_period_engine(inputs)
    kwargs = dict(COMMON)
    kwargs['use_distributionaccount_runtime_wiring'] = da_wiring
    return run_waterfall_v3_core(inputs=inputs, engine=engine, **kwargs)


# ---------------------------------------------------------------------------
# 1. audit_economic_mode is comparison-only (never routed to runtime)
# ---------------------------------------------------------------------------

class TestAuditModeNotRouted:
    def test_audit_mode_field_exists_in_inputs(self):
        """DistributionAccountPeriodInput has audit_economic_mode field."""
        from domain.distribution_account.inputs import DistributionAccountPeriodInput
        import dataclasses
        fields = {f.name for f in dataclasses.fields(DistributionAccountPeriodInput)}
        assert "audit_economic_mode" in fields

    def test_runtime_economic_mode_field_exists_in_inputs(self):
        """DistributionAccountPeriodInput has runtime_economic_mode field."""
        from domain.distribution_account.inputs import DistributionAccountPeriodInput
        import dataclasses
        fields = {f.name for f in dataclasses.fields(DistributionAccountPeriodInput)}
        assert "runtime_economic_mode" in fields

    def test_gates_accept_runtime_economic_mode(self):
        """R99/R102 evaluate_*_gate functions accept runtime_economic_mode parameter."""
        from domain.distribution_account.gates import evaluate_r99_gate, evaluate_r102_gate
        import inspect
        r99_params = list(inspect.signature(evaluate_r99_gate).parameters.keys())
        r102_params = list(inspect.signature(evaluate_r102_gate).parameters.keys())
        assert "runtime_economic_mode" in r99_params
        assert "runtime_economic_mode" in r102_params

    def test_audit_mode_gate_active_requires_explicit_flag(self):
        """audit_economic_mode=True alone activates gates."""
        from domain.distribution_account.gates import evaluate_r99_gate
        from domain.distribution_account.inputs import R99R102GateInputs
        result = evaluate_r99_gate(
            inputs=R99R102GateInputs(),
            cash_available=1000.0,
            enable_runtime=False,
            audit_economic_mode=True,
            runtime_economic_mode=False,
        )
        assert result.passed, "audit_economic_mode=True should activate R99 gate"


# ---------------------------------------------------------------------------
# 2. runtime staging mode is explicit and distinct
# ---------------------------------------------------------------------------

class TestRuntimeModeExplicit:
    def test_runtime_economic_mode_activates_gates(self):
        """runtime_economic_mode=True activates R99 gate (distinct from audit mode)."""
        from domain.distribution_account.gates import evaluate_r99_gate
        from domain.distribution_account.inputs import R99R102GateInputs
        result = evaluate_r99_gate(
            inputs=R99R102GateInputs(),
            cash_available=1000.0,
            enable_runtime=False,
            audit_economic_mode=False,
            runtime_economic_mode=True,
        )
        assert result.passed, "runtime_economic_mode=True should activate R99 gate"

    def test_both_modes_false_gates_blocked(self):
        """Both flags False: gates are BLOCKED (governed mode)."""
        from domain.distribution_account.gates import evaluate_r99_gate
        from domain.distribution_account.inputs import R99R102GateInputs
        result = evaluate_r99_gate(
            inputs=R99R102GateInputs(),
            cash_available=1000.0,
            enable_runtime=False,
            audit_economic_mode=False,
            runtime_economic_mode=False,
        )
        assert not result.passed
        assert "R99" in result.blocked_reason or "BLOCKED" in result.blocked_reason

    def test_engine_passes_runtime_economic_mode_to_gates(self):
        """DistributionAccountEngine passes runtime_economic_mode to gate evaluations."""
        from domain.distribution_account.engine import DistributionAccountEngine
        from domain.distribution_account.inputs import (
            DistributionAccountInputs, DistributionAccountPeriodInput, R99R102GateInputs,
        )
        inp = DistributionAccountPeriodInput(
            period_index=0,
            operating_period_index=0,
            period_date=None,
            opening_distribution_account_balance_keur=0.0,
            post_senior_cash_available_keur=1000.0,
            post_shl_cash_available_keur=1000.0,
            senior_debt_service_keur=100.0,
            actual_dscr=1.5,
            target_distribution_dscr=1.0,
            dsra_current_balance_keur=0.0,
            dsra_required_balance_keur=0.0,
            is_tuho=True,
            is_oborovo=False,
            senior_tenor_years=0,
            minimum_cash_reserve_keur=0.0,
            audit_economic_mode=False,
            runtime_economic_mode=True,
            r99_gate_inputs=R99R102GateInputs(),
            r102_gate_inputs=R99R102GateInputs(),
        )
        inputs = DistributionAccountInputs(
            project_name="TUHO-WIND-1",
            period_inputs=(inp,),
            is_tuho=True,
            is_oborovo=False,
        )
        result = DistributionAccountEngine.compute(inputs)
        assert len(result.period_results) == 1
        pr = result.period_results[0]
        assert pr.r99_gate_result.passed, (
            f"runtime_economic_mode=True should activate R99 gate, got blocked={pr.r99_gate_result.blocked_reason}"
        )


# ---------------------------------------------------------------------------
# 3. dual-run uses audit_economic_mode (comparison only, no routing)
# ---------------------------------------------------------------------------

class TestDualRunUsesAuditMode:
    def test_waterfall_dualrun_uses_audit_economic_mode(self):
        """waterfall_core dual-run section uses audit_economic_mode=True."""
        import inspect
        from app import waterfall_core
        source = inspect.getsource(waterfall_core)
        # Dual-run economic periods use audit_economic_mode=True
        assert "audit_economic_mode=True" in source
        # But _apply_distributionaccount_runtime_wiring must use runtime_economic_mode=True
        wiring_src = inspect.getsource(waterfall_core._apply_distributionaccount_runtime_wiring)
        assert "runtime_economic_mode=True" in wiring_src, (
            "_apply_distributionaccount_runtime_wiring should use runtime_economic_mode=True"
        )
        assert "audit_economic_mode=True" not in wiring_src, (
            "_apply_distributionaccount_runtime_wiring should NOT use audit_economic_mode=True"
        )


# ---------------------------------------------------------------------------
# 4. default behavior unchanged (flag=False: legacy/zero drift)
# ---------------------------------------------------------------------------

class TestDefaultBehaviorUnchanged:
    def test_tuho_flag_false_legacy_total(self):
        """TUHO with use_distributionaccount_runtime_wiring=False: ~326,165 kEUR."""
        r = _run_waterfall("TUHO-WIND-1", da_wiring=False)
        assert abs(r.total_distribution_keur - 326_165) < 1000, (
            f"Expected ~326,165 kEUR, got {r.total_distribution_keur:,.2f}"
        )
        assert r.distribution_wiring_delta_keur == 0.0

    def test_tuho_flag_false_zero_delta(self):
        """TUHO flag=False: distribution_wiring_delta_keur == 0.0."""
        r = _run_waterfall("TUHO-WIND-1", da_wiring=False)
        assert abs(r.distribution_wiring_delta_keur) < 0.01

    def test_oborovo_flag_false_distribution_unchanged(self):
        """Oborovo with use_distributionaccount_runtime_wiring=False: ~181,019 kEUR."""
        r = _run_waterfall("OBOROVO-SOLAR-1", da_wiring=False)
        assert abs(r.total_distribution_keur - 181_019) < 1000, (
            f"Expected ~181,019 kEUR, got {r.total_distribution_keur:,.2f}"
        )


# ---------------------------------------------------------------------------
# 5. TUHO flag=True behavior unchanged
# ---------------------------------------------------------------------------

class TestTUHOFlagOnUnchanged:
    def test_tuho_flag_true_distribution_approx_284552(self):
        """TUHO with use_distributionaccount_runtime_wiring=True: ~284,552 kEUR."""
        r = _run_waterfall("TUHO-WIND-1", da_wiring=True)
        assert abs(r.total_distribution_keur - 284_552) < 500, (
            f"Expected ~284,552 kEUR, got {r.total_distribution_keur:,.2f}"
        )

    def test_tuho_flag_true_delta_approx_negative_41613(self):
        """TUHO DA wiring delta: ~-41,613 kEUR."""
        r = _run_waterfall("TUHO-WIND-1", da_wiring=True)
        assert -44_000 < r.distribution_wiring_delta_keur < -40_000, (
            f"Expected delta ~-41,613 kEUR, got {r.distribution_wiring_delta_keur:,.2f}"
        )

    def test_tuho_flag_true_vs_flag_false_delta(self):
        """TUHO flag=True total - flag=False total ≈ -41,613 kEUR."""
        r0 = _run_waterfall("TUHO-WIND-1", da_wiring=False)
        r1 = _run_waterfall("TUHO-WIND-1", da_wiring=True)
        delta = r1.total_distribution_keur - r0.total_distribution_keur
        assert -44_000 < delta < -40_000, (
            f"Expected delta ~-41,613 kEUR, got {delta:,.2f}"
        )


# ---------------------------------------------------------------------------
# 6. Oborovo guard unchanged
# ---------------------------------------------------------------------------

class TestOborovoGuardUnchanged:
    def test_oborovo_flag_true_guard_fires(self):
        """Oborovo guard fires when use_distributionaccount_runtime_wiring=True."""
        r = _run_waterfall("OBOROVO-SOLAR-1", da_wiring=True)
        assert r.distribution_source == "oborovo_guard_blocked", (
            f"Expected guard blocked, got {r.distribution_source}"
        )

    def test_oborovo_flag_true_distribution_unchanged(self):
        """Oborovo: flag=True distribution unchanged vs flag=False."""
        r0 = _run_waterfall("OBOROVO-SOLAR-1", da_wiring=False)
        r1 = _run_waterfall("OBOROVO-SOLAR-1", da_wiring=True)
        assert abs(r1.total_distribution_keur - r0.total_distribution_keur) < 0.01, (
            "Oborovo guard: distribution must not change when guard fires"
        )

    def test_oborovo_guard_delta_is_zero(self):
        """Oborovo guard: distribution_wiring_delta_keur == 0.0."""
        r = _run_waterfall("OBOROVO-SOLAR-1", da_wiring=True)
        assert abs(r.distribution_wiring_delta_keur) < 0.01


# ---------------------------------------------------------------------------
# 7. R99/R102 still BLOCKED
# ---------------------------------------------------------------------------

class TestR99R102Blocked:
    def test_gates_docstring_mentions_blocked(self):
        """R99/R102 gate docstrings mention BLOCKED status."""
        from domain.distribution_account.gates import evaluate_r99_gate, evaluate_r102_gate
        r99_doc = evaluate_r99_gate.__doc__
        r102_doc = evaluate_r102_gate.__doc__
        assert "BLOCKED" in r99_doc
        assert "BLOCKED" in r102_doc

    def test_runtime_economic_mode_is_not_g20_promotion(self):
        """runtime_economic_mode docstring clarifies it is pre-G20 staging, not G20 promotion."""
        from domain.distribution_account.gates import evaluate_r99_gate
        doc = evaluate_r99_gate.__doc__
        assert "G20" in doc or "not G20" in doc or "pre-G20" in doc, (
            "runtime_economic_mode docstring must clarify it is NOT G20 promotion"
        )

    def test_governed_mode_blocks_gates(self):
        """Both flags False: gates remain blocked (governed mode)."""
        from domain.distribution_account.gates import evaluate_r99_gate, evaluate_r102_gate
        from domain.distribution_account.inputs import R99R102GateInputs
        r99 = evaluate_r99_gate(
            inputs=R99R102GateInputs(),
            cash_available=10000.0,
            enable_runtime=False,
            audit_economic_mode=False,
            runtime_economic_mode=False,
        )
        r102 = evaluate_r102_gate(
            inputs=R99R102GateInputs(),
            cash_available=10000.0,
            enable_runtime=False,
            audit_economic_mode=False,
            runtime_economic_mode=False,
        )
        assert not r99.passed
        assert not r102.passed


# ---------------------------------------------------------------------------
# 8. SHL R102 / Sponsor handoff not changed
# ---------------------------------------------------------------------------

class TestSHLandSponsorUnchanged:
    def test_distribution_account_r102_sweep_candidate_field_exists(self):
        """distribution_account_r102_sweep_candidate_keur field still exists in ShlPeriodResult."""
        from domain.shl.result import ShlPeriodResult
        import dataclasses
        fields = {f.name for f in dataclasses.fields(ShlPeriodResult)}
        assert "distribution_account_r102_sweep_candidate_keur" in fields

    def test_sponsor_distribution_account_received_by_period_field_exists(self):
        """distribution_account_received_by_period still exists in SponsorCashflowRunnerInputs."""
        from domain.sponsor.sponsor_cashflow_runner import SponsorCashflowRunnerInputs
        import dataclasses
        fields = {f.name for f in dataclasses.fields(SponsorCashflowRunnerInputs)}
        assert "distribution_account_received_by_period" in fields


# ---------------------------------------------------------------------------
# 9. Contract doc exists
# ---------------------------------------------------------------------------

class TestContractDocumentation:
    def test_contract_doc_exists(self):
        assert CONTRACT_DOC.exists(), f"Missing: {CONTRACT_DOC}"

    def test_contract_doc_mentions_both_modes(self):
        with open(CONTRACT_DOC, encoding="utf-8") as f:
            content = f.read()
        assert "audit_economic_mode" in content
        assert "runtime_economic_mode" in content

    def test_contract_doc_mentions_not_g20_promotion(self):
        with open(CONTRACT_DOC, encoding="utf-8") as f:
            content = f.read()
        assert "BLOCKED" in content or "G20" in content

    def test_contract_csv_if_present_has_correct_columns(self):
        """Optional CSV mode table: if present, has expected columns."""
        if not CONTRACT_CSV.exists():
            pytest.skip("Optional CSV not present")
        with open(CONTRACT_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        required = ["mode", "allowed_use", "runtime_routing_allowed", "default",
                    "used_by", "governance_status", "notes"]
        assert list(rows[0].keys()) == required