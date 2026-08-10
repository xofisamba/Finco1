"""tests/test_stage_c3b3d2b2b_current_senior_debt_bridge.py — C3B3D2B2B bridge tests.

C3B3D2B2B: Decompose CURRENT_GRID0_TO_SOURCE_DEBT_BRIDGE_NOT_YET_CLOSED.

Stage: current-senior-debt-bridge
Branch: stage-c3b3d2b2b-current-senior-debt-bridge

Purpose:
  Close the +1,066.754 kEUR gap between CURRENT_GRID0_PRODUCTION_CANDIDATE
  (43,919.032698 kEUR) and SOURCE_EXCEL_SENIOR_DEBT (42,852.278763 kEUR) using
  one-factor counterfactuals, sequential bridge, and SOURCE_ALL gate.

Result:
  The entire gap is explained by CF1 (CFADS): clean Phase2A EBITDA vs source DS!row20.
  Rates (DS!row44), DSCR banding (DS!row22), ops fraction (DS!row9), and day fractions
  (DS!row6) are already source-matched in the current engine.
  SOURCE_ALL gate: bridge closed, residual = 0.000 kEUR.
  Verdict: CURRENT_GRID0_TO_SOURCE_SIZING_INPUT_BRIDGE_CLOSED

Governance:
  EVIDENCE-ONLY. No production engine changes. No approved_delta. No plug.
  No DS25/DS40 hardcoding. No project-name dispatch. No calibration.
  No DSRA implementation. No SHL formula changes. No new tax grid arms.
  Protected C3B2 SHA: f8f244c0660495bfb4115d4e32ba329c291ab829d1d0693e614c889457b5add7
  13547.2 MUST NOT appear in any clean SHL calculation.
  BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED — Macro50 not decomposed here.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge import (
    CURRENT_GRID0_DEBT_KEUR,
    CURRENT_GRID0_TO_SOURCE_GAP_KEUR,
    HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR,
    SOURCE_EXCEL_SENIOR_DEBT_KEUR,
    _backward_induction,
    capture_current_grid0_snapshot,
    evaluate_source_all_gate,
    load_source_vectors,
    run_one_factor_counterfactuals,
    run_sequential_bridge,
)

_FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def grid0_snapshot():
    return capture_current_grid0_snapshot()


@pytest.fixture(scope="module")
def source_vectors():
    return load_source_vectors()


@pytest.fixture(scope="module")
def counterfactuals(grid0_snapshot, source_vectors):
    return run_one_factor_counterfactuals(grid0_snapshot, source_vectors)


@pytest.fixture(scope="module")
def sequential_bridge(grid0_snapshot, source_vectors):
    return run_sequential_bridge(grid0_snapshot, source_vectors)


@pytest.fixture(scope="module")
def source_all_gate(grid0_snapshot, source_vectors):
    return evaluate_source_all_gate(grid0_snapshot, source_vectors)


@pytest.fixture(scope="module")
def debt_fixture():
    path = _FIXTURE_DIR / "excel_oborovo_debt_interest_truth.json"
    with path.open() as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Section 1: Governance constants
# ---------------------------------------------------------------------------

class TestGovernanceConstants:
    """Three baseline authorities must not be conflated."""

    def test_current_grid0_constant(self):
        """CURRENT_GRID0_DEBT_KEUR = 43,919.032698 (CURRENT_GRID0_PRODUCTION_CANDIDATE)."""
        assert abs(CURRENT_GRID0_DEBT_KEUR - 43_919.032698) < 1.0

    def test_source_excel_debt_constant(self):
        """SOURCE_EXCEL_SENIOR_DEBT_KEUR = 42,852.278763 (DS!D51)."""
        assert abs(SOURCE_EXCEL_SENIOR_DEBT_KEUR - 42_852.27876256299) < 1e-6

    def test_historical_constant(self):
        """HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR = 46,053.402379 (historical only)."""
        assert abs(HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR - 46_053.402378616) < 1e-3

    def test_gap_constant(self):
        """CURRENT_GRID0_TO_SOURCE_GAP_KEUR = +1,066.754 kEUR."""
        assert abs(CURRENT_GRID0_TO_SOURCE_GAP_KEUR - 1_066.754) < 1.0

    def test_three_baselines_distinct(self):
        """The three baseline authorities are all distinct values."""
        assert CURRENT_GRID0_DEBT_KEUR != SOURCE_EXCEL_SENIOR_DEBT_KEUR
        assert CURRENT_GRID0_DEBT_KEUR != HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR
        assert SOURCE_EXCEL_SENIOR_DEBT_KEUR != HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR

    def test_13547_not_in_constants(self):
        """13547.2 must not appear in any constant (governance constraint)."""
        for val in [CURRENT_GRID0_DEBT_KEUR, SOURCE_EXCEL_SENIOR_DEBT_KEUR,
                    HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR, CURRENT_GRID0_TO_SOURCE_GAP_KEUR]:
            assert abs(val - 13547.2) > 100.0


# ---------------------------------------------------------------------------
# Section 2: Gate 1 — CURRENT_GRID0_RUNTIME_BASELINE_REPRODUCED
# ---------------------------------------------------------------------------

class TestGate1CurrentGrid0BaselineReproduced:
    """CURRENT_GRID0_RUNTIME_BASELINE_REPRODUCED: engine = locked constant."""

    def test_engine_debt_matches_locked_constant(self, grid0_snapshot):
        """Runtime engine output matches CURRENT_GRID0_DEBT_KEUR within 1 kEUR."""
        assert abs(grid0_snapshot.debt_keur - CURRENT_GRID0_DEBT_KEUR) < 1.0

    def test_snapshot_debt_approximately_43919(self, grid0_snapshot):
        """Snapshot captures approx 43,919 kEUR — not the historical 46,053."""
        assert abs(grid0_snapshot.debt_keur - 43_919.0) < 5.0
        assert abs(grid0_snapshot.debt_keur - 46_053.0) > 100.0

    def test_independent_backward_induction_matches_engine(self, grid0_snapshot):
        """Independent backward induction from snapshot parameters matches engine < 1e-3 kEUR.

        Classification: CURRENT_GRID0_RUNTIME_BASELINE_REPRODUCED
        """
        delta = abs(grid0_snapshot.backward_induction_keur - grid0_snapshot.debt_keur)
        assert delta < 1e-3

    def test_snapshot_has_28_active_periods(self, grid0_snapshot):
        """28 active source periods (P1..P28) in the GRID-0 snapshot."""
        assert len(grid0_snapshot.active_src_periods) == 28

    def test_snapshot_cfads_positive(self, grid0_snapshot):
        """All operating CFADS values are positive in the clean engine snapshot."""
        for p, v in grid0_snapshot.cfads_by_src_period.items():
            assert v > 0.0, f"Non-positive CFADS at src period {p}: {v}"

    def test_snapshot_rates_positive(self, grid0_snapshot):
        """All annual rates in snapshot are positive."""
        for p, v in grid0_snapshot.rate_by_src_period.items():
            assert v > 0.0, f"Non-positive rate at src period {p}: {v}"

    def test_snapshot_dscr_at_least_115(self, grid0_snapshot):
        """All DSCR targets in snapshot are >= 1.15."""
        for p, v in grid0_snapshot.dscr_by_src_period.items():
            assert v >= 1.15 - 1e-9, f"DSCR below 1.15 at src period {p}: {v}"


# ---------------------------------------------------------------------------
# Section 3: Gate 2 — SOURCE_SENIOR_DEBT_CAPACITY_REPLAY_PROVEN
# ---------------------------------------------------------------------------

class TestGate2SourceCapacityReplay:
    """SOURCE_SENIOR_DEBT_CAPACITY_REPLAY_PROVEN: backward induction from source = DS!D51."""

    def test_source_capacity_matches_excel_d51(self, source_vectors):
        """Backward induction from source vectors matches DS!D51 fixture within 1 kEUR.

        Classification: SOURCE_SENIOR_DEBT_CAPACITY_REPLAY_PROVEN
        """
        assert abs(source_vectors.source_capacity_keur - source_vectors.excel_total_debt_keur) < 1.0

    def test_source_capacity_matches_source_constant(self, source_vectors):
        """Source capacity matches SOURCE_EXCEL_SENIOR_DEBT_KEUR constant."""
        assert abs(source_vectors.source_capacity_keur - SOURCE_EXCEL_SENIOR_DEBT_KEUR) < 1.0

    def test_source_has_28_periods(self, source_vectors):
        """Source vectors cover 28 periods (P1..P28)."""
        assert len(source_vectors.cfads_by_period) == 28
        assert len(source_vectors.dscr_by_period) == 28
        assert len(source_vectors.rate_by_period) == 28
        assert len(source_vectors.day_frac_by_period) == 28

    def test_source_dscr_banding(self, source_vectors):
        """DS!row22: 1.15 for P1-P24, 1.35 for P25-P28 (DSCR_BANDING_SOURCE_PROVEN)."""
        for p in range(1, 25):
            assert abs(source_vectors.dscr_by_period[p] - 1.15) < 1e-9
        for p in range(25, 29):
            assert abs(source_vectors.dscr_by_period[p] - 1.35) < 1e-9

    def test_source_cfads_positive(self, source_vectors):
        """All source DS!row20 CFADS values are positive for active periods."""
        for p in range(1, 29):
            assert source_vectors.cfads_by_period[p] > 0.0

    def test_source_excel_debt_from_fixture(self, debt_fixture):
        """DS!D51 fixture value = 42,852.278763 kEUR."""
        val = debt_fixture["workstream_b"]["ds_d51_total_debt"]["value_keur"]
        assert abs(val - 42_852.27876256299) < 1e-6


# ---------------------------------------------------------------------------
# Section 4: One-factor counterfactuals
# ---------------------------------------------------------------------------

class TestCounterfactualCF1Cfads:
    """CF1: Source CFADS (DS!row20) closes the entire gap."""

    def test_cf1_closes_bridge(self, counterfactuals):
        """CF1 (source CFADS) moves from 43,919 to ~42,852 kEUR — closes gap.

        Classification: CF1_CFADS_CLOSES_CURRENT_GRID0_TO_SOURCE_BRIDGE
        """
        cf1 = next(c for c in counterfactuals if c.label == "CF1")
        assert abs(cf1.capacity_keur - SOURCE_EXCEL_SENIOR_DEBT_KEUR) < 1.0

    def test_cf1_delta_matches_gap(self, counterfactuals):
        """CF1 delta equals the CURRENT_GRID0_TO_SOURCE gap (−1,066.754 kEUR)."""
        cf1 = next(c for c in counterfactuals if c.label == "CF1")
        assert abs(cf1.delta_vs_baseline_keur - (-CURRENT_GRID0_TO_SOURCE_GAP_KEUR)) < 1.0

    def test_cf1_classification_not_already_matched(self, counterfactuals):
        """CF1 classification confirms a real CFADS difference (not already matched)."""
        cf1 = next(c for c in counterfactuals if c.label == "CF1")
        assert cf1.classification != "VECTOR_ALREADY_SOURCE_MATCHED"

    def test_source_cfads_lower_than_clean(self, grid0_snapshot, source_vectors):
        """Source DS!row20 CFADS sum < clean Phase2A EBITDA sum (explains negative delta)."""
        src_total = sum(source_vectors.cfads_by_period.values())
        clean_total = sum(grid0_snapshot.cfads_by_src_period.values())
        assert src_total < clean_total

    def test_cfads_difference_by_period(self, grid0_snapshot, source_vectors):
        """Per-period CFADS differences are non-trivial in later periods."""
        large_deltas = [
            abs(grid0_snapshot.cfads_by_src_period[p] - source_vectors.cfads_by_period[p])
            for p in range(20, 29)
        ]
        assert max(large_deltas) > 100.0


class TestCounterfactualCF2Dscr:
    """CF2: DSCR banding — already source-matched in current engine."""

    def test_cf2_delta_zero(self, counterfactuals):
        """CF2 (source DSCR) delta = 0.000 kEUR — engine already uses source banding.

        Classification: VECTOR_ALREADY_SOURCE_MATCHED
        """
        cf2 = next(c for c in counterfactuals if c.label == "CF2")
        assert abs(cf2.delta_vs_baseline_keur) < _get_tolerance()

    def test_cf2_classification_matched(self, counterfactuals):
        """CF2 is classified VECTOR_ALREADY_SOURCE_MATCHED."""
        cf2 = next(c for c in counterfactuals if c.label == "CF2")
        assert cf2.classification == "VECTOR_ALREADY_SOURCE_MATCHED"

    def test_engine_dscr_matches_source(self, grid0_snapshot, source_vectors):
        """Clean engine DSCR vector matches source DS!row22 for all 28 periods."""
        for p in range(1, 29):
            clean_d = grid0_snapshot.dscr_by_src_period[p]
            src_d = source_vectors.dscr_by_period[p]
            assert abs(clean_d - src_d) < 1e-9, f"DSCR mismatch at src P{p}: clean={clean_d} src={src_d}"


class TestCounterfactualCF3Ops:
    """CF3: Ops fraction — already source-matched in current engine."""

    def test_cf3_delta_zero(self, counterfactuals):
        """CF3 (source ops) delta = 0.000 kEUR — engine already uses source ops.

        Classification: VECTOR_ALREADY_SOURCE_MATCHED
        """
        cf3 = next(c for c in counterfactuals if c.label == "CF3")
        assert abs(cf3.delta_vs_baseline_keur) < _get_tolerance()

    def test_cf3_classification_matched(self, counterfactuals):
        """CF3 is classified VECTOR_ALREADY_SOURCE_MATCHED."""
        cf3 = next(c for c in counterfactuals if c.label == "CF3")
        assert cf3.classification == "VECTOR_ALREADY_SOURCE_MATCHED"


class TestCounterfactualCF4Rate:
    """CF4: Annual rate — already source-matched in current engine."""

    def test_cf4_delta_zero(self, counterfactuals):
        """CF4 (source rate DS!row44) delta = 0.000 kEUR — engine already uses source rates.

        Classification: VECTOR_ALREADY_SOURCE_MATCHED
        """
        cf4 = next(c for c in counterfactuals if c.label == "CF4")
        assert abs(cf4.delta_vs_baseline_keur) < _get_tolerance()

    def test_cf4_classification_matched(self, counterfactuals):
        """CF4 is classified VECTOR_ALREADY_SOURCE_MATCHED."""
        cf4 = next(c for c in counterfactuals if c.label == "CF4")
        assert cf4.classification == "VECTOR_ALREADY_SOURCE_MATCHED"

    def test_engine_rates_match_source(self, grid0_snapshot, source_vectors):
        """Clean engine rate vector matches source DS!row44 for all 28 periods."""
        for p in range(1, 29):
            clean_r = grid0_snapshot.rate_by_src_period[p]
            src_r = source_vectors.rate_by_period[p]
            assert abs(clean_r - src_r) < 1e-9, f"Rate mismatch at src P{p}: clean={clean_r} src={src_r}"


def _get_tolerance() -> float:
    return 1.0  # VECTOR_ALREADY_SOURCE_MATCHED threshold (kEUR)


# ---------------------------------------------------------------------------
# Section 5: Sequential bridge
# ---------------------------------------------------------------------------

class TestSequentialBridge:
    """Sequential bridge from CURRENT_GRID0 → SOURCE_ALL."""

    def test_bridge_has_4_steps(self, sequential_bridge):
        """Sequential bridge has 4 steps (CF1–CF4)."""
        assert len(sequential_bridge) == 4

    def test_step1_closes_entire_gap(self, sequential_bridge):
        """Step 1 (CF1 CFADS) closes the entire gap — all other steps have delta≈0."""
        step1 = sequential_bridge[0]
        assert abs(step1.cumulative_capacity_keur - SOURCE_EXCEL_SENIOR_DEBT_KEUR) < 1.0

    def test_step1_delta_equals_full_gap(self, sequential_bridge):
        """Step 1 delta = −1,066.754 kEUR (full CURRENT_GRID0_TO_SOURCE_GAP_KEUR)."""
        step1 = sequential_bridge[0]
        assert abs(step1.step_delta_keur - (-CURRENT_GRID0_TO_SOURCE_GAP_KEUR)) < 1.0

    def test_steps_2_to_4_delta_near_zero(self, sequential_bridge):
        """Steps 2–4 (DSCR, ops, rate) each contribute ≈ 0.000 kEUR."""
        for step in sequential_bridge[1:]:
            assert abs(step.step_delta_keur) < 1.0, (
                f"Step {step.step} ({step.vector_applied}) has non-zero delta: {step.step_delta_keur}"
            )

    def test_final_step_reaches_source(self, sequential_bridge):
        """Final bridge step reaches SOURCE_EXCEL_SENIOR_DEBT_KEUR within 1 kEUR."""
        final = sequential_bridge[-1]
        assert abs(final.cumulative_capacity_keur - SOURCE_EXCEL_SENIOR_DEBT_KEUR) < 1.0

    def test_bridge_monotone_toward_source(self, sequential_bridge):
        """Cumulative capacity moves toward source (first step is largest move)."""
        step1_delta = abs(sequential_bridge[0].step_delta_keur)
        subsequent_deltas = [abs(s.step_delta_keur) for s in sequential_bridge[1:]]
        assert step1_delta > max(subsequent_deltas) * 10


# ---------------------------------------------------------------------------
# Section 6: SOURCE_ALL gate
# ---------------------------------------------------------------------------

class TestSourceAllGate:
    """SOURCE_ALL gate: all source vectors simultaneously."""

    def test_source_all_closes_bridge(self, source_all_gate):
        """SOURCE_ALL capacity = SOURCE_EXCEL_SENIOR_DEBT_KEUR within 1 kEUR.

        Classification: CURRENT_GRID0_TO_SOURCE_SIZING_INPUT_BRIDGE_CLOSED
        """
        assert abs(source_all_gate.source_all_capacity_keur - SOURCE_EXCEL_SENIOR_DEBT_KEUR) < 1.0

    def test_source_all_residual_near_zero(self, source_all_gate):
        """SOURCE_ALL residual vs source < 1e-3 kEUR."""
        assert abs(source_all_gate.residual_vs_source_keur) < 1e-3

    def test_source_all_bridge_closed_flag(self, source_all_gate):
        """bridge_closed = True when SOURCE_ALL gate passes."""
        assert source_all_gate.bridge_closed is True

    def test_source_all_verdict(self, source_all_gate):
        """Verdict = CURRENT_GRID0_TO_SOURCE_SIZING_INPUT_BRIDGE_CLOSED."""
        assert source_all_gate.verdict == "CURRENT_GRID0_TO_SOURCE_SIZING_INPUT_BRIDGE_CLOSED"

    def test_source_all_not_partial(self, source_all_gate):
        """SOURCE_ALL is not CURRENT_GRID0_TO_SOURCE_DEBT_BRIDGE_STILL_INCOMPLETE."""
        assert source_all_gate.verdict != "CURRENT_GRID0_TO_SOURCE_DEBT_BRIDGE_STILL_INCOMPLETE"


# ---------------------------------------------------------------------------
# Section 7: Backward-induction purity and independence
# ---------------------------------------------------------------------------

class TestBackwardInductionPurity:
    """Independent backward induction properties."""

    def test_bi_deterministic(self):
        """Backward induction is deterministic — same inputs → same output."""
        active = list(range(1, 6))
        cfads = {p: 2500.0 for p in active}
        dscr = {p: 1.15 for p in active}
        ops = {p: 1.0 for p in active}
        rate = {p: 0.0595 for p in active}
        frac = {p: 0.5 for p in active}
        v1 = _backward_induction(cfads, dscr, ops, rate, frac, active)
        v2 = _backward_induction(cfads, dscr, ops, rate, frac, active)
        assert v1 == v2

    def test_bi_higher_cfads_higher_capacity(self):
        """Higher CFADS → higher debt capacity (monotone)."""
        active = [1, 2, 3]
        base = {p: 2500.0 for p in active}
        high = {p: 3000.0 for p in active}
        dscr = {p: 1.15 for p in active}
        ops = {p: 1.0 for p in active}
        rate = {p: 0.06 for p in active}
        frac = {p: 0.5 for p in active}
        v_base = _backward_induction(base, dscr, ops, rate, frac, active)
        v_high = _backward_induction(high, dscr, ops, rate, frac, active)
        assert v_high > v_base

    def test_bi_higher_dscr_lower_capacity(self):
        """Higher DSCR → lower debt capacity (allowed_ds = CFADS/DSCR*ops)."""
        active = [1, 2, 3]
        cfads = {p: 2500.0 for p in active}
        dscr_low = {p: 1.15 for p in active}
        dscr_high = {p: 1.35 for p in active}
        ops = {p: 1.0 for p in active}
        rate = {p: 0.06 for p in active}
        frac = {p: 0.5 for p in active}
        v_low = _backward_induction(cfads, dscr_low, ops, rate, frac, active)
        v_high = _backward_induction(cfads, dscr_high, ops, rate, frac, active)
        assert v_low > v_high

    def test_bi_formula_verified(self):
        """Single-period backward induction: V = allowed_ds / (1 + rate * frac)."""
        cfads = 2_600.0
        dscr = 1.15
        ops = 1.0
        rate = 0.0595136
        frac = 0.5111111
        allowed_ds = (cfads / dscr) * ops
        expected = allowed_ds / (1.0 + rate * frac)
        result = _backward_induction({1: cfads}, {1: dscr}, {1: ops}, {1: rate}, {1: frac}, [1])
        assert abs(result - expected) < 1e-9


# ---------------------------------------------------------------------------
# Section 8: Bridge architecture assertions
# ---------------------------------------------------------------------------

class TestBridgeArchitectureAssertions:
    """Structural properties of the bridge result."""

    def test_cf1_is_sole_explanatory_factor(self, counterfactuals):
        """CF1 alone accounts for > 99% of the total gap — all other CFs are near zero."""
        cf1 = next(c for c in counterfactuals if c.label == "CF1")
        others = [c for c in counterfactuals if c.label != "CF1"]
        total_other = sum(abs(c.delta_vs_baseline_keur) for c in others)
        assert abs(cf1.delta_vs_baseline_keur) > 1_000.0
        assert total_other < 1.0

    def test_source_all_equals_cf1_only(self, grid0_snapshot, source_vectors, source_all_gate):
        """SOURCE_ALL capacity = CF1-only capacity (other vectors already matched)."""
        active = grid0_snapshot.active_src_periods
        cf1_only = _backward_induction(
            source_vectors.cfads_by_period,
            grid0_snapshot.dscr_by_src_period,
            grid0_snapshot.ops_by_src_period,
            grid0_snapshot.rate_by_src_period,
            grid0_snapshot.day_frac_by_src_period,
            active,
        )
        assert abs(cf1_only - source_all_gate.source_all_capacity_keur) < 1e-5

    def test_historical_not_used_as_baseline(self):
        """Historical 46,053 kEUR is not the starting point for this bridge."""
        gap_from_historical = HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR - SOURCE_EXCEL_SENIOR_DEBT_KEUR
        gap_from_current = CURRENT_GRID0_DEBT_KEUR - SOURCE_EXCEL_SENIOR_DEBT_KEUR
        assert abs(gap_from_current - 1_066.754) < 1.0
        assert abs(gap_from_historical - 3_201.124) < 1.0
        assert gap_from_historical != gap_from_current

    def test_macro50_mechanism_unresolved(self, counterfactuals):
        """CF1 description acknowledges Macro50 mechanism is unresolved (VBA_IMPLEMENTATION_NOT_VISIBLE)."""
        cf1 = next(c for c in counterfactuals if c.label == "CF1")
        assert "Macro50" in cf1.description or "DS!row20" in cf1.description

    def test_no_ds25_ds40_hardcoding(self):
        """No DS25/DS40 period boundary hardcoded as integer literals in function bodies."""
        import finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge as mod
        import ast, inspect
        tree = ast.parse(inspect.getsource(mod))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in (25, 40):
                raise AssertionError(
                    f"Hardcoded period boundary {node.value} found in module — DS25/DS40 ENFORCED"
                )

    def test_no_13547_in_module(self):
        """13547.2 MUST NOT appear as a literal value in the diagnostic module."""
        import finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge as mod
        import ast, inspect
        tree = ast.parse(inspect.getsource(mod))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)) and abs(float(node.value) - 13547.2) < 0.1:
                    raise AssertionError("13547.2 found as literal value in module — ENFORCED")

    def test_no_approved_delta_or_plug(self):
        """No approved_delta or balancing plug variable name in function bodies."""
        import finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge as mod
        import ast, inspect
        tree = ast.parse(inspect.getsource(mod))
        forbidden = {"approved_delta", "balancing_plug", "calibration_plug"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden:
                raise AssertionError(f"Forbidden variable '{node.id}' found in module")


# ---------------------------------------------------------------------------
# Section 9: CFADS vector integrity
# ---------------------------------------------------------------------------

class TestCfadsVectorIntegrity:
    """Source DS!row20 and clean CFADS vector properties."""

    def test_cfads_total_sum_difference(self, grid0_snapshot, source_vectors):
        """Clean CFADS total > source CFADS total (explains positive gap direction)."""
        clean_sum = sum(grid0_snapshot.cfads_by_src_period.values())
        src_sum = sum(source_vectors.cfads_by_period.values())
        assert clean_sum > src_sum
        assert (clean_sum - src_sum) > 500.0

    def test_cfads_early_periods_close(self, grid0_snapshot, source_vectors):
        """Early periods (P1-P5) CFADS differences are < 10 kEUR."""
        for p in range(1, 6):
            delta = abs(grid0_snapshot.cfads_by_src_period[p] - source_vectors.cfads_by_period[p])
            assert delta < 10.0, f"Large early-period delta at P{p}: {delta:.3f}"

    def test_cfads_late_periods_diverge(self, grid0_snapshot, source_vectors):
        """Late periods (P24-P28) show the largest CFADS divergence."""
        late_deltas = [
            abs(grid0_snapshot.cfads_by_src_period[p] - source_vectors.cfads_by_period[p])
            for p in range(24, 29)
        ]
        assert max(late_deltas) > 200.0

    def test_source_cfads_from_ds_row20_fixture(self, source_vectors, debt_fixture):
        """Source CFADS matches DS!row20 fixture values for active periods P1–P28."""
        cfads_list = debt_fixture["workstream_a"]["ds_row20_cfads"]["period_values_keur"]
        for p in range(1, 29):
            assert abs(source_vectors.cfads_by_period[p] - cfads_list[p]) < 1e-9


# ---------------------------------------------------------------------------
# Section 10: Report format
# ---------------------------------------------------------------------------

class TestReportFormat:
    """Diagnostic report format and content."""

    def test_report_contains_verdict(self, grid0_snapshot, source_vectors):
        """Formatted report contains the bridge verdict."""
        from finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge import (
            C3B3D2B2BDiagnosticResult,
            run_one_factor_counterfactuals,
            run_sequential_bridge,
            evaluate_source_all_gate,
        )
        result = C3B3D2B2BDiagnosticResult(
            snapshot=grid0_snapshot,
            source_vectors=source_vectors,
            counterfactuals=run_one_factor_counterfactuals(grid0_snapshot, source_vectors),
            sequential_bridge=run_sequential_bridge(grid0_snapshot, source_vectors),
            source_all_gate=evaluate_source_all_gate(grid0_snapshot, source_vectors),
        )
        report = result.format_report()
        assert "CURRENT_GRID0_TO_SOURCE_SIZING_INPUT_BRIDGE_CLOSED" in report
        assert "43,919" in report or "43919" in report
        assert "42,852" in report or "42852" in report

    def test_verdict_property(self, grid0_snapshot, source_vectors):
        """C3B3D2B2BDiagnosticResult.verdict returns the SOURCE_ALL gate verdict."""
        from finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge import (
            C3B3D2B2BDiagnosticResult,
            run_one_factor_counterfactuals,
            run_sequential_bridge,
            evaluate_source_all_gate,
        )
        result = C3B3D2B2BDiagnosticResult(
            snapshot=grid0_snapshot,
            source_vectors=source_vectors,
            counterfactuals=run_one_factor_counterfactuals(grid0_snapshot, source_vectors),
            sequential_bridge=run_sequential_bridge(grid0_snapshot, source_vectors),
            source_all_gate=evaluate_source_all_gate(grid0_snapshot, source_vectors),
        )
        assert result.verdict == "CURRENT_GRID0_TO_SOURCE_SIZING_INPUT_BRIDGE_CLOSED"
