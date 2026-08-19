"""Runtime proof tests for the single-financial-flow audit (PR #943).

These tests use monkeypatching to instrument the ACTUAL runtime call graphs for
TUHO, Oborovo, and KUPI. They do NOT infer from imports — they record which
functions actually execute.

Governance:
  - No production financial formulas modified
  - No project-specific behaviour added to production code
  - No outputs fitted
  - Diagnostic only

RUNTIME_OBSERVED traces (proven below):
  TUHO:
    APP_ENTRY → LEGACY_RUNNER → LEGACY_CORE → LEGACY_WATERFALL

  Oborovo:
    APP_ENTRY → LEGACY_RUNNER → LEGACY_CORE → LEGACY_WATERFALL

  KUPI clean-engine:
    DIAGNOSTIC_ENTRY (run_p0_current_generic)
      → run_project_financing_model    [call_count >= 1, RUNTIME_OBSERVED]
      → run_operating_model            [call_count >= 1, RUNTIME_OBSERVED]
      → run_senior_debt_model          [call_count >= 1, RUNTIME_OBSERVED]
      → run_tax_cfads_model            [call_count >= 1, RUNTIME_OBSERVED]
      → compute_shareholder_loan_schedules  [call_count >= 1, RUNTIME_OBSERVED]

  KUPI private-solver diagnostic (DIAGNOSTIC_ONLY_PATH):
    kupi_true_bank_only_senior_diagnostic(p0, d0)
      → diag_mod._forward_roll         [call_count >= 1, RUNTIME_OBSERVED]
      → diag_mod._backward_dscr_capacity [call_count >= 1, RUNTIME_OBSERVED]
"""
from __future__ import annotations

import pytest
from unittest.mock import patch
from typing import List


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _CallRecorder:
    """Wraps a real function and records every call without altering behaviour."""

    def __init__(self, real_fn):
        self._real = real_fn
        self.calls: List[str] = []
        self.call_count = 0

    def __call__(self, *args, **kwargs):
        self.call_count += 1
        self.calls.append(f"called#{self.call_count}")
        return self._real(*args, **kwargs)


# ---------------------------------------------------------------------------
# TUHO runtime path proof  (RUNTIME_OBSERVED)
# ---------------------------------------------------------------------------

class TestTuhoRuntimePath:
    """Prove TUHO production flow: APP_ENTRY → LEGACY_RUNNER → LEGACY_CORE → LEGACY_WATERFALL.

    Regression contract (AUDIT SNAPSHOT GUARD):
    These tests intentionally FAIL if TUHO is promoted to the clean engine.
    That failure is the correct signal — it means this audit snapshot must
    be updated as part of the promotion PR. Moving TUHO to the clean engine
    is the TARGET state, not a regression. Do not weaken these assertions;
    update them as part of the promotion work.
    """

    def test_tuho_calls_legacy_waterfall_chain(self):
        """TUHO: run_demo_project drives the full legacy chain end-to-end."""
        import domain.waterfall.waterfall_engine as dw_mod
        import app.waterfall_runner as wr_mod

        # Patch where each symbol is USED:
        # - run_waterfall_v3_core is bound into app.waterfall_runner at module-import time
        # - run_waterfall is imported locally inside run_waterfall_v3_core from domain.waterfall.waterfall_engine
        wv3_recorder = _CallRecorder(wr_mod.run_waterfall_v3_core)
        run_wf_recorder = _CallRecorder(dw_mod.run_waterfall)

        runner_run_called = []
        _orig_runner_run = wr_mod.WaterfallRunner.run

        def _patched_runner_run(self, config):
            runner_run_called.append(True)
            return _orig_runner_run(self, config)

        with (
            patch.object(wr_mod, "run_waterfall_v3_core", wv3_recorder),
            patch.object(dw_mod, "run_waterfall", run_wf_recorder),
            patch.object(wr_mod.WaterfallRunner, "run", _patched_runner_run),
        ):
            from app.ui_runner import run_demo_project
            result = run_demo_project("TUHO")

        assert result.result is not None, (
            f"run_demo_project('TUHO') returned no result. messages={result.messages}"
        )
        assert runner_run_called, (
            "AUDIT_SNAPSHOT_GUARD: WaterfallRunner.run was NOT called for TUHO. "
            "If TUHO was promoted to the clean engine, update this snapshot."
        )
        assert wv3_recorder.call_count >= 1, (
            "AUDIT_SNAPSHOT_GUARD: run_waterfall_v3_core was NOT called for TUHO. "
            "If TUHO was promoted to the clean engine, update this snapshot."
        )
        assert run_wf_recorder.call_count >= 1, (
            "AUDIT_SNAPSHOT_GUARD: domain.waterfall.run_waterfall was NOT called for TUHO. "
            "If TUHO was promoted to the clean engine, update this snapshot."
        )

    def test_tuho_does_not_call_clean_engine_orchestrator(self):
        """TUHO: must NOT invoke the clean financial engine orchestrator.

        AUDIT_SNAPSHOT_GUARD: fails when TUHO is promoted to clean engine.
        Update as part of the promotion PR — promotion is the target state.
        """
        import financial_engine.orchestrator as orch_mod

        clean_calls = []

        def _sentinel_operating(*args, **kwargs):
            clean_calls.append("run_operating_model")
            raise AssertionError(
                "AUDIT_SNAPSHOT_GUARD: TUHO called clean run_operating_model. "
                "If this is the promotion PR, update this test."
            )

        def _sentinel_tax_cfads(*args, **kwargs):
            clean_calls.append("run_tax_cfads_model")
            raise AssertionError(
                "AUDIT_SNAPSHOT_GUARD: TUHO called clean run_tax_cfads_model."
            )

        def _sentinel_senior(*args, **kwargs):
            clean_calls.append("run_senior_debt_model")
            raise AssertionError(
                "AUDIT_SNAPSHOT_GUARD: TUHO called clean run_senior_debt_model."
            )

        with (
            patch.object(orch_mod, "run_operating_model", _sentinel_operating),
            patch.object(orch_mod, "run_tax_cfads_model", _sentinel_tax_cfads),
            patch.object(orch_mod, "run_senior_debt_model", _sentinel_senior),
        ):
            from app.ui_runner import run_demo_project
            result = run_demo_project("TUHO")

        assert not clean_calls
        assert result.result is not None

    def test_tuho_structural_trace(self):
        """Verify TUHO normalized structural trace label sequence (RUNTIME_OBSERVED)."""
        trace: List[str] = []

        import app.ui_runner as ui_mod
        import app.waterfall_runner as wr_mod
        import domain.waterfall.waterfall_engine as dw_mod

        _orig_run_waterfall = ui_mod._run_waterfall
        _orig_runner_run = wr_mod.WaterfallRunner.run
        _orig_wv3 = wr_mod.run_waterfall_v3_core
        _orig_fw = dw_mod.run_waterfall

        def _trace_app_entry(*args, **kwargs):
            trace.append("APP_ENTRY")
            return _orig_run_waterfall(*args, **kwargs)

        def _trace_legacy_runner(self, config):
            trace.append("LEGACY_RUNNER")
            return _orig_runner_run(self, config)

        def _trace_legacy_core(*args, **kwargs):
            trace.append("LEGACY_CORE")
            return _orig_wv3(*args, **kwargs)

        def _trace_legacy_waterfall(*args, **kwargs):
            trace.append("LEGACY_WATERFALL")
            return _orig_fw(*args, **kwargs)

        with (
            patch.object(ui_mod, "_run_waterfall", _trace_app_entry),
            patch.object(wr_mod.WaterfallRunner, "run", _trace_legacy_runner),
            patch.object(wr_mod, "run_waterfall_v3_core", _trace_legacy_core),
            patch.object(dw_mod, "run_waterfall", _trace_legacy_waterfall),
        ):
            from app.ui_runner import run_demo_project
            run_demo_project("TUHO")

        assert all(label in trace for label in
                   ["APP_ENTRY", "LEGACY_RUNNER", "LEGACY_CORE", "LEGACY_WATERFALL"])
        idx = {label: trace.index(label) for label in
               ["APP_ENTRY", "LEGACY_RUNNER", "LEGACY_CORE", "LEGACY_WATERFALL"]}
        assert idx["APP_ENTRY"] < idx["LEGACY_RUNNER"] < idx["LEGACY_CORE"] < idx["LEGACY_WATERFALL"], (
            f"TUHO structural trace out of order: {trace}"
        )


# ---------------------------------------------------------------------------
# Oborovo runtime path proof  (RUNTIME_OBSERVED)
# ---------------------------------------------------------------------------

class TestOborovoRuntimePath:
    """Prove Oborovo production flow: APP_ENTRY → LEGACY_RUNNER → LEGACY_CORE → LEGACY_WATERFALL.

    Regression contract (AUDIT SNAPSHOT GUARD):
    These tests intentionally FAIL if Oborovo is promoted to the clean engine.
    That failure is the correct signal — it means this audit snapshot must
    be updated as part of the promotion PR. Moving Oborovo to the clean engine
    is the TARGET state, not a regression. Do not weaken these assertions.
    """

    def test_oborovo_calls_legacy_waterfall_chain(self):
        """Oborovo: run_demo_project drives the full legacy chain end-to-end."""
        import domain.waterfall.waterfall_engine as dw_mod
        import app.waterfall_runner as wr_mod

        wv3_recorder = _CallRecorder(wr_mod.run_waterfall_v3_core)
        run_wf_recorder = _CallRecorder(dw_mod.run_waterfall)
        runner_run_called = []
        _orig_runner_run = wr_mod.WaterfallRunner.run

        def _patched_runner_run(self, config):
            runner_run_called.append(True)
            return _orig_runner_run(self, config)

        with (
            patch.object(wr_mod, "run_waterfall_v3_core", wv3_recorder),
            patch.object(dw_mod, "run_waterfall", run_wf_recorder),
            patch.object(wr_mod.WaterfallRunner, "run", _patched_runner_run),
        ):
            from app.ui_runner import run_demo_project
            result = run_demo_project("Oborovo")

        assert result.result is not None, (
            f"run_demo_project('Oborovo') returned no result. messages={result.messages}"
        )
        assert runner_run_called, "AUDIT_SNAPSHOT_GUARD: WaterfallRunner.run not called for Oborovo."
        assert wv3_recorder.call_count >= 1, "AUDIT_SNAPSHOT_GUARD: run_waterfall_v3_core not called for Oborovo."
        assert run_wf_recorder.call_count >= 1, "AUDIT_SNAPSHOT_GUARD: domain.waterfall.run_waterfall not called for Oborovo."

    def test_oborovo_does_not_call_clean_engine_orchestrator(self):
        """Oborovo: must NOT invoke the clean financial engine orchestrator.

        AUDIT_SNAPSHOT_GUARD: fails when Oborovo is promoted to clean engine.
        Update as part of the promotion PR.
        """
        import financial_engine.orchestrator as orch_mod

        clean_calls = []

        def _sentinel_operating(*args, **kwargs):
            clean_calls.append("run_operating_model")
            raise AssertionError("AUDIT_SNAPSHOT_GUARD: Oborovo called clean run_operating_model.")

        def _sentinel_tax(*args, **kwargs):
            clean_calls.append("run_tax_cfads_model")
            raise AssertionError("AUDIT_SNAPSHOT_GUARD: Oborovo called clean run_tax_cfads_model.")

        def _sentinel_senior(*args, **kwargs):
            clean_calls.append("run_senior_debt_model")
            raise AssertionError("AUDIT_SNAPSHOT_GUARD: Oborovo called clean run_senior_debt_model.")

        with (
            patch.object(orch_mod, "run_operating_model", _sentinel_operating),
            patch.object(orch_mod, "run_tax_cfads_model", _sentinel_tax),
            patch.object(orch_mod, "run_senior_debt_model", _sentinel_senior),
        ):
            from app.ui_runner import run_demo_project
            result = run_demo_project("Oborovo")

        assert not clean_calls
        assert result.result is not None

    def test_oborovo_structural_trace(self):
        """Verify Oborovo normalized structural trace label sequence (RUNTIME_OBSERVED)."""
        trace: List[str] = []

        import app.ui_runner as ui_mod
        import app.waterfall_runner as wr_mod
        import domain.waterfall.waterfall_engine as dw_mod

        _orig_run_waterfall = ui_mod._run_waterfall
        _orig_runner_run = wr_mod.WaterfallRunner.run
        _orig_wv3 = wr_mod.run_waterfall_v3_core
        _orig_fw = dw_mod.run_waterfall

        def _trace_app_entry(*args, **kwargs):
            trace.append("APP_ENTRY")
            return _orig_run_waterfall(*args, **kwargs)

        def _trace_legacy_runner(self, config):
            trace.append("LEGACY_RUNNER")
            return _orig_runner_run(self, config)

        def _trace_legacy_core(*args, **kwargs):
            trace.append("LEGACY_CORE")
            return _orig_wv3(*args, **kwargs)

        def _trace_legacy_waterfall(*args, **kwargs):
            trace.append("LEGACY_WATERFALL")
            return _orig_fw(*args, **kwargs)

        with (
            patch.object(ui_mod, "_run_waterfall", _trace_app_entry),
            patch.object(wr_mod.WaterfallRunner, "run", _trace_legacy_runner),
            patch.object(wr_mod, "run_waterfall_v3_core", _trace_legacy_core),
            patch.object(dw_mod, "run_waterfall", _trace_legacy_waterfall),
        ):
            from app.ui_runner import run_demo_project
            run_demo_project("Oborovo")

        idx = {label: trace.index(label) for label in
               ["APP_ENTRY", "LEGACY_RUNNER", "LEGACY_CORE", "LEGACY_WATERFALL"]}
        assert idx["APP_ENTRY"] < idx["LEGACY_RUNNER"] < idx["LEGACY_CORE"] < idx["LEGACY_WATERFALL"], (
            f"Oborovo structural trace out of order: {trace}"
        )


# ---------------------------------------------------------------------------
# KUPI clean-engine runtime proof  (RUNTIME_OBSERVED)
# ---------------------------------------------------------------------------

class TestKupiCleanEngineRuntimeTrace:
    """Prove the KUPI clean-engine call chain by instrumenting actual call sites.

    Patch targets use where-used (not where-defined):
    - run_project_financing_model: bound into diag_mod at module-import time
    - run_operating_model: bound into financial_engine.financing.project at module-import time
    - run_senior_debt_model: bound into financial_engine.financing.project at module-import time
    - run_tax_cfads_model: called from within financial_engine.orchestrator
    - compute_shareholder_loan_schedules: local import inside _run_senior_debt_model_with_shl
      in financial_engine.orchestrator → patch on financial_engine.shl.production

    The clean financing fixed-point calls some stages multiple times. That is expected.
    """

    def test_kupi_clean_engine_all_stages_called(self):
        """KUPI diagnostic run_p0_current_generic() invokes every clean-engine stage.

        Asserts call_count >= 1 for each stage. The actual run must complete
        without exception — no exception swallowing.
        """
        import tests.diagnostics.kupi_k0_k3_causal_grid as diag_mod
        import financial_engine.financing.project as fp_mod
        import financial_engine.orchestrator as orch_mod
        import financial_engine.shl.production as shl_prod_mod

        # Record wrappers — each calls the real function so the run completes
        pfm_recorder = _CallRecorder(diag_mod.run_project_financing_model)
        op_recorder = _CallRecorder(fp_mod.run_operating_model)
        senior_recorder = _CallRecorder(fp_mod.run_senior_debt_model)
        tax_cfads_recorder = _CallRecorder(orch_mod.run_tax_cfads_model)
        shl_recorder = _CallRecorder(shl_prod_mod.compute_shareholder_loan_schedules)

        with (
            patch.object(diag_mod, "run_project_financing_model", pfm_recorder),
            patch.object(fp_mod, "run_operating_model", op_recorder),
            patch.object(fp_mod, "run_senior_debt_model", senior_recorder),
            patch.object(orch_mod, "run_tax_cfads_model", tax_cfads_recorder),
            patch.object(shl_prod_mod, "compute_shareholder_loan_schedules", shl_recorder),
        ):
            result = diag_mod.run_p0_current_generic()

        # The run must succeed — no exception swallowed
        assert result is not None, "run_p0_current_generic() returned None"
        assert result.final_senior_commitment_keur > 0, (
            f"run_p0_current_generic() returned zero senior. Result: {result}"
        )

        # Every clean-engine stage must have been called at least once
        assert pfm_recorder.call_count >= 1, (
            "run_project_financing_model NOT called — DIAGNOSTIC_ENTRY missing"
        )
        assert op_recorder.call_count >= 1, (
            f"run_operating_model NOT called from financing.project. "
            f"call_count={op_recorder.call_count}"
        )
        assert senior_recorder.call_count >= 1, (
            f"run_senior_debt_model NOT called from financing.project. "
            f"call_count={senior_recorder.call_count}"
        )
        assert tax_cfads_recorder.call_count >= 1, (
            f"run_tax_cfads_model NOT called inside orchestrator. "
            f"call_count={tax_cfads_recorder.call_count}"
        )
        assert shl_recorder.call_count >= 1, (
            f"compute_shareholder_loan_schedules NOT called inside orchestrator. "
            f"call_count={shl_recorder.call_count}"
        )

    def test_kupi_clean_engine_call_counts_reported(self):
        """Record actual call counts per stage for audit documentation.

        The fixed-point convergence loop calls several stages multiple times.
        This test captures the observed multiplicity and ensures counts are sane.
        """
        import tests.diagnostics.kupi_k0_k3_causal_grid as diag_mod
        import financial_engine.financing.project as fp_mod
        import financial_engine.orchestrator as orch_mod
        import financial_engine.shl.production as shl_prod_mod

        pfm_recorder = _CallRecorder(diag_mod.run_project_financing_model)
        op_recorder = _CallRecorder(fp_mod.run_operating_model)
        senior_recorder = _CallRecorder(fp_mod.run_senior_debt_model)
        tax_cfads_recorder = _CallRecorder(orch_mod.run_tax_cfads_model)
        shl_recorder = _CallRecorder(shl_prod_mod.compute_shareholder_loan_schedules)

        with (
            patch.object(diag_mod, "run_project_financing_model", pfm_recorder),
            patch.object(fp_mod, "run_operating_model", op_recorder),
            patch.object(fp_mod, "run_senior_debt_model", senior_recorder),
            patch.object(orch_mod, "run_tax_cfads_model", tax_cfads_recorder),
            patch.object(shl_prod_mod, "compute_shareholder_loan_schedules", shl_recorder),
        ):
            diag_mod.run_p0_current_generic()

        # All counts must be positive; fixed-point may repeat stages
        assert pfm_recorder.call_count >= 1
        assert op_recorder.call_count >= 1
        assert senior_recorder.call_count >= 1
        assert tax_cfads_recorder.call_count >= 1
        assert shl_recorder.call_count >= 1
        # The fixed-point loop calls senior >= 1 time; shl may be called multiple times per iteration
        assert shl_recorder.call_count >= senior_recorder.call_count, (
            "SHL must be called at least as many times as senior (called per fixed-point iteration)"
        )


# ---------------------------------------------------------------------------
# KUPI app-factory exclusion proof
# ---------------------------------------------------------------------------

class TestKupiAppFactoryExclusion:
    """KUPI must not appear in the app FACTORY_MAP."""

    def test_kupi_not_in_app_factory_map(self):
        """KUPI: run_demo_project('KUPI') must return no result (unknown project type)."""
        from app.ui_runner import run_demo_project
        result = run_demo_project("KUPI")
        assert result.result is None, (
            "KUPI must not be in the FACTORY_MAP. run_demo_project('KUPI') returned a result."
        )
        assert any("unknown" in m.lower() or "kupi" in m.lower()
                   for m in result.messages), (
            f"Expected an 'unknown project type' message for KUPI. Got: {result.messages}"
        )

    def test_kupi_diagnostic_does_not_route_through_app_entry(self):
        """KUPI diagnostic must not call app._run_waterfall or WaterfallRunner.run."""
        import app.ui_runner as ui_mod
        import app.waterfall_runner as wr_mod
        import tests.diagnostics.kupi_k0_k3_causal_grid as diag_mod

        app_entry_calls = []
        runner_calls = []

        def _sentinel_run_waterfall(*args, **kwargs):
            app_entry_calls.append(True)
            raise AssertionError("KUPI diagnostic must not call app._run_waterfall")

        def _sentinel_runner_run(self, config):
            runner_calls.append(True)
            raise AssertionError("KUPI diagnostic must not call WaterfallRunner.run")

        with (
            patch.object(ui_mod, "_run_waterfall", _sentinel_run_waterfall),
            patch.object(wr_mod.WaterfallRunner, "run", _sentinel_runner_run),
        ):
            diag_mod.run_p0_current_generic()

        assert not app_entry_calls, "KUPI diagnostic incorrectly called app._run_waterfall"
        assert not runner_calls, "KUPI diagnostic incorrectly called WaterfallRunner.run"


# ---------------------------------------------------------------------------
# KUPI private-solver diagnostic proof  (DIAGNOSTIC_ONLY_RUNTIME_OBSERVED)
# ---------------------------------------------------------------------------

class TestKupiPrivateSolverDiagnostic:
    """Prove kupi_true_bank_only_senior_diagnostic calls private solvers.

    Isolation protocol:
    1. Build P0 and D0 BEFORE entering the patch context (no solver interception
       during clean-engine preparation — proves the calls originate from the
       DIAGNOSTIC_ONLY_PATH itself).
    2. Reset counters.
    3. Enter patch context on diag_mod._forward_roll and
       diag_mod._backward_dscr_capacity (where the aliases are USED, not just
       where originally defined in financial_engine.senior_debt.solver).
    4. Call ONLY kupi_true_bank_only_senior_diagnostic(p0, d0) inside that context.
    5. Assert BOTH call_count >= 1.
    """

    def test_private_solvers_called_by_diagnostic(self):
        """kupi_true_bank_only_senior_diagnostic calls _forward_roll AND
        _backward_dscr_capacity from the diagnostic module's own aliases.

        Classification: DIAGNOSTIC_ONLY_RUNTIME_OBSERVED
        """
        import tests.diagnostics.kupi_k0_k3_causal_grid as diag_mod

        # Step 1: Build P0 and D0 without any patching — clean-engine preparation
        p0 = diag_mod.run_p0_current_generic()
        d0 = diag_mod.run_d0_bank_balancing_diagnostic()

        # Step 2: Capture the module-level aliases that the diagnostic uses
        orig_forward = diag_mod._forward_roll
        orig_backward = diag_mod._backward_dscr_capacity

        # Step 3: Create recording wrappers
        forward_roll_calls = []
        backward_dscr_calls = []

        def _recording_forward(*args, **kwargs):
            forward_roll_calls.append(True)
            return orig_forward(*args, **kwargs)

        def _recording_backward(*args, **kwargs):
            backward_dscr_calls.append(True)
            return orig_backward(*args, **kwargs)

        # Step 4: Patch the module-level aliases (where USED, not just where defined)
        with (
            patch.object(diag_mod, "_forward_roll", _recording_forward),
            patch.object(diag_mod, "_backward_dscr_capacity", _recording_backward),
        ):
            # Call ONLY the bank-only diagnostic inside the patch context
            dx_result = diag_mod.kupi_true_bank_only_senior_diagnostic(p0, d0)

        # Step 5: Assert BOTH were called (AND, not OR)
        assert len(forward_roll_calls) >= 1, (
            "DIAGNOSTIC_ONLY_PATH: diag_mod._forward_roll was NOT called by "
            "kupi_true_bank_only_senior_diagnostic. "
            f"forward_roll call count: {len(forward_roll_calls)}, "
            f"backward_dscr call count: {len(backward_dscr_calls)}"
        )
        assert len(backward_dscr_calls) >= 1, (
            "DIAGNOSTIC_ONLY_PATH: diag_mod._backward_dscr_capacity was NOT called by "
            "kupi_true_bank_only_senior_diagnostic. "
            f"forward_roll call count: {len(forward_roll_calls)}, "
            f"backward_dscr call count: {len(backward_dscr_calls)}"
        )
        # Confirm the diagnostic produced a result
        assert dx_result is not None, "kupi_true_bank_only_senior_diagnostic returned None"


# ---------------------------------------------------------------------------
# Dual-engine reality regression guards  (AUDIT SNAPSHOT GUARDS)
# ---------------------------------------------------------------------------

class TestDualEngineRegressionGuards:
    """Fail-fast guards ensuring TUHO/Oborovo stay on the legacy path.

    AUDIT SNAPSHOT GUARDS — these tests intentionally fail when TUHO or Oborovo
    is promoted to the clean engine. That failure is the correct signal: the audit
    snapshot must be updated as part of the promotion PR. Moving TUHO/Oborovo to
    the clean engine is the TARGET state, not a regression. Do not weaken the
    assertions — update them during the promotion work.
    """

    @pytest.mark.parametrize("project_type", ["TUHO", "Oborovo"])
    def test_legacy_app_projects_never_call_run_project_financing_model(self, project_type):
        """TUHO and Oborovo must NEVER call run_project_financing_model (clean engine).

        AUDIT_SNAPSHOT_GUARD — update during clean-engine promotion PR.
        """
        import financial_engine.financing.project as proj_mod

        calls = []

        def _sentinel(*args, **kwargs):
            calls.append(project_type)
            raise AssertionError(
                f"AUDIT_SNAPSHOT_GUARD: {project_type} called run_project_financing_model. "
                "LEGACY_APP_PRODUCTION_FLOW must not reach CLEAN_PRE_PROMOTION_FINANCIAL_FLOW "
                "in the current architecture. Update this test in the promotion PR."
            )

        with patch.object(proj_mod, "run_project_financing_model", _sentinel):
            from app.ui_runner import run_demo_project
            result = run_demo_project(project_type)

        assert not calls, (
            f"DUAL_ENGINE REGRESSION: {project_type} called run_project_financing_model. "
            f"calls: {calls}"
        )
        assert result.result is not None, f"{project_type} run failed: {result.messages}"

    @pytest.mark.parametrize("project_type", ["TUHO", "Oborovo"])
    def test_legacy_app_projects_always_call_run_waterfall_v3_core(self, project_type):
        """TUHO and Oborovo must ALWAYS call run_waterfall_v3_core (legacy core).

        AUDIT_SNAPSHOT_GUARD — update during clean-engine promotion PR.
        If this fails after a refactor (not a promotion), it means the legacy
        core has been bypassed — treat as a breaking change requiring investigation.
        """
        import app.waterfall_runner as wr_mod

        recorder = _CallRecorder(wr_mod.run_waterfall_v3_core)

        with patch.object(wr_mod, "run_waterfall_v3_core", recorder):
            from app.ui_runner import run_demo_project
            run_demo_project(project_type)

        assert recorder.call_count >= 1, (
            f"AUDIT_SNAPSHOT_GUARD: {project_type} did not call run_waterfall_v3_core. "
            "If this is the promotion PR, update this test. "
            "If this is a refactor, investigate — legacy core has been bypassed."
        )
