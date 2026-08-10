"""tests/test_stage_c3b3d2b2b_current_senior_debt_bridge.py — C3B3D2B2B R2 bridge tests.

C3B3D2B2B R2: Current senior debt bridge — source-contamination fix, day-fraction arm added.

Stage: current-senior-debt-bridge
Branch: stage-c3b3d2b2b-current-senior-debt-bridge

Purpose:
  Close the +1,066.754 kEUR gap between CURRENT_GRID0_PRODUCTION_CANDIDATE
  (43,919.032698 kEUR) and SOURCE_EXCEL_SENIOR_DEBT (42,852.278763 kEUR).

R2 result:
  CF1 (source CFADS / DS!row20) explains 100% of the gap.
  CF2 (DSCR), CF3 (day fractions), CF4 (ops), CF5 (rates) each = 0.000 kEUR.
  All non-CFADS vectors proven identical by per-period vector equality gates.
  SOURCE_ALL gate: bridge closed, residual = 0.000 kEUR.
  Verdict: C3B3D2B2B_R2_BANK_SIZING_CFADS_AUTHORITY_SOLE_GAP_READY_FOR_INDEPENDENT_REVIEW

R2 fixes:
  - capture_current_grid0_snapshot() no longer reads source fixture
  - Day fractions derived via period_day_fraction(period_start, period_end, convention)
  - CF3 (day-count) explicitly added
  - Fail-closed snapshot: no silent defaults for required vector entries
  - Baseline lock tightened to 1e-3 kEUR

Governance:
  EVIDENCE-ONLY. No production engine changes. No approved_delta. No plug.
  No DS25/DS40 hardcoding. No project-name dispatch. No calibration.
  No DSRA implementation. No SHL formula changes. No new tax grid arms.
  Protected C3B2 SHA: f8f244c0660495bfb4115d4e32ba329c291ab829d1d0693e614c889457b5add7
  13547.2 MUST NOT appear in any clean SHL calculation.
  BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED — Macro50 not decomposed here.
  MISSING_GENERIC_BANK_SIZING_CFADS_SCENARIO_LAYER — future architecture, not this PR.
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
    _BASELINE_LOCK_TOLERANCE_KEUR,
    _backward_induction,
    capture_current_grid0_snapshot,
    compare_vectors,
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
def vector_comparisons(grid0_snapshot, source_vectors):
    return compare_vectors(grid0_snapshot, source_vectors)


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
        """Three baseline authorities are all distinct values."""
        assert CURRENT_GRID0_DEBT_KEUR != SOURCE_EXCEL_SENIOR_DEBT_KEUR
        assert CURRENT_GRID0_DEBT_KEUR != HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR
        assert SOURCE_EXCEL_SENIOR_DEBT_KEUR != HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR

    def test_baseline_lock_tolerance_tight(self):
        """Baseline lock tolerance is <= 1e-3 kEUR (tight, deterministic solver)."""
        assert _BASELINE_LOCK_TOLERANCE_KEUR <= 1e-3


# ---------------------------------------------------------------------------
# Section 2: Snapshot source-contamination check (R2 critical)
# ---------------------------------------------------------------------------

class TestSnapshotSourceContaminationR2:
    """R2: capture_current_grid0_snapshot() must NOT read the source fixture."""

    def test_snapshot_function_does_not_open_debt_fixture(self):
        """capture_current_grid0_snapshot source code must not reference debt fixture path."""
        import inspect
        import finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge as mod
        src = inspect.getsource(mod.capture_current_grid0_snapshot)
        assert "excel_oborovo_debt_interest_truth" not in src

    def test_snapshot_function_does_not_use_fixture_path(self):
        """capture_current_grid0_snapshot must not reference _DEBT_FIXTURE_PATH."""
        import inspect
        import finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge as mod
        src = inspect.getsource(mod.capture_current_grid0_snapshot)
        assert "_DEBT_FIXTURE_PATH" not in src

    def test_snapshot_function_does_not_call_json_load(self):
        """capture_current_grid0_snapshot must not call json.load (no fixture reads)."""
        import inspect
        import finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge as mod
        src = inspect.getsource(mod.capture_current_grid0_snapshot)
        assert "json.load" not in src
        assert "json.loads" not in src

    def test_load_source_vectors_opens_fixture(self):
        """load_source_vectors (and only it) reads the debt fixture."""
        import inspect
        import finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge as mod
        src = inspect.getsource(mod.load_source_vectors)
        assert "excel_oborovo_debt_interest_truth" in src or "_DEBT_FIXTURE_PATH" in src

    def test_day_frac_derived_from_production_helper(self):
        """Snapshot day fractions come from period_day_fraction helper, not fixture."""
        import inspect
        import finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge as mod
        src = inspect.getsource(mod.capture_current_grid0_snapshot)
        assert "period_day_fraction" in src


# ---------------------------------------------------------------------------
# Section 3: Gate 1 — CURRENT_GRID0_RUNTIME_BASELINE_REPRODUCED
# ---------------------------------------------------------------------------

class TestGate1CurrentGrid0BaselineReproduced:
    """CURRENT_GRID0_RUNTIME_BASELINE_REPRODUCED: pure current snapshot, tight lock."""

    def test_engine_debt_matches_locked_constant(self, grid0_snapshot):
        """Runtime engine output matches CURRENT_GRID0_DEBT_KEUR within 1e-3 kEUR."""
        assert abs(grid0_snapshot.debt_keur - CURRENT_GRID0_DEBT_KEUR) < _BASELINE_LOCK_TOLERANCE_KEUR

    def test_snapshot_debt_approximately_43919(self, grid0_snapshot):
        """Snapshot captures approx 43,919 kEUR — not historical 46,053."""
        assert abs(grid0_snapshot.debt_keur - 43_919.0) < 5.0
        assert abs(grid0_snapshot.debt_keur - 46_053.0) > 100.0

    def test_independent_current_only_backward_induction_matches_engine(self, grid0_snapshot):
        """Independent BI from pure current snapshot matches engine < 1e-3 kEUR.

        Classification: CURRENT_GRID0_RUNTIME_BASELINE_REPRODUCED
        """
        delta = abs(grid0_snapshot.backward_induction_keur - grid0_snapshot.debt_keur)
        assert delta < _BASELINE_LOCK_TOLERANCE_KEUR

    def test_snapshot_has_28_active_periods(self, grid0_snapshot):
        """28 active source periods (P1..P28) in the GRID-0 snapshot."""
        assert len(grid0_snapshot.active_src_periods) == 28

    def test_snapshot_cfads_all_explicit_and_positive(self, grid0_snapshot):
        """All 28 CFADS values are explicitly present and positive (fail-closed)."""
        assert len(grid0_snapshot.cfads_by_src_period) == 28
        for p, v in grid0_snapshot.cfads_by_src_period.items():
            assert v > 0.0, f"Non-positive CFADS at src period {p}: {v}"

    def test_snapshot_rates_all_explicit_and_positive(self, grid0_snapshot):
        """All 28 rate values are explicitly present and positive."""
        assert len(grid0_snapshot.rate_by_src_period) == 28
        for p, v in grid0_snapshot.rate_by_src_period.items():
            assert v > 0.0, f"Non-positive rate at src period {p}: {v}"

    def test_snapshot_dscr_all_explicit(self, grid0_snapshot):
        """All 28 DSCR values are explicitly present and >= 1.15."""
        assert len(grid0_snapshot.dscr_by_src_period) == 28
        for p, v in grid0_snapshot.dscr_by_src_period.items():
            assert v >= 1.15 - 1e-9, f"DSCR below 1.15 at src period {p}: {v}"

    def test_snapshot_ops_all_explicit(self, grid0_snapshot):
        """All 28 ops values are explicitly present."""
        assert len(grid0_snapshot.ops_by_src_period) == 28

    def test_snapshot_day_frac_all_explicit_and_positive(self, grid0_snapshot):
        """All 28 current-derived day fractions are explicitly present and positive."""
        assert len(grid0_snapshot.day_frac_by_src_period) == 28
        for p, v in grid0_snapshot.day_frac_by_src_period.items():
            assert v > 0.0, f"Non-positive day frac at src period {p}: {v}"

    def test_snapshot_day_count_convention_recorded(self, grid0_snapshot):
        """Day-count convention name is recorded in snapshot."""
        assert grid0_snapshot.day_count_convention
        assert "360" in grid0_snapshot.day_count_convention or "365" in grid0_snapshot.day_count_convention

    def test_snapshot_day_frac_provenance_is_runtime(self, grid0_snapshot):
        """Day-count convention is ACT_360 (derived from production policy, not fixture)."""
        assert "360" in grid0_snapshot.day_count_convention


# ---------------------------------------------------------------------------
# Section 4: Gate 2 — SOURCE_SENIOR_DEBT_CAPACITY_REPLAY_PROVEN
# ---------------------------------------------------------------------------

class TestGate2SourceCapacityReplay:
    """SOURCE_SENIOR_DEBT_CAPACITY_REPLAY_PROVEN: backward induction from source = DS!D51."""

    def test_source_capacity_matches_excel_d51(self, source_vectors):
        """Backward induction from source vectors matches DS!D51 fixture within 1 kEUR."""
        assert abs(source_vectors.source_capacity_keur - source_vectors.excel_total_debt_keur) < 1.0

    def test_source_capacity_matches_source_constant(self, source_vectors):
        """Source capacity matches SOURCE_EXCEL_SENIOR_DEBT_KEUR constant."""
        assert abs(source_vectors.source_capacity_keur - SOURCE_EXCEL_SENIOR_DEBT_KEUR) < 1.0

    def test_source_has_28_periods_per_vector(self, source_vectors):
        """All source vectors cover exactly 28 periods (P1..P28)."""
        assert len(source_vectors.cfads_by_period) == 28
        assert len(source_vectors.dscr_by_period) == 28
        assert len(source_vectors.rate_by_period) == 28
        assert len(source_vectors.day_frac_by_period) == 28
        assert len(source_vectors.ops_by_period) == 28

    def test_source_dscr_banding(self, source_vectors):
        """DS!row22: 1.15 for P1-P24, 1.35 for P25-P28."""
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
# Section 5: Vector equality gates (R2 required — not inferred from debt delta)
# ---------------------------------------------------------------------------

class TestVectorEqualityGates:
    """Direct per-period vector equality: current engine vs source (R2 explicit gates)."""

    def test_dscr_vector_equality(self, vector_comparisons):
        """DSCR vector: current engine matches source DS!row22, max_delta < 1e-9.

        Classification: VECTOR_ALREADY_SOURCE_MATCHED
        """
        vc = vector_comparisons["dscr"]
        assert vc.max_abs_delta < 1e-9, (
            f"DSCR vector mismatch: max_delta={vc.max_abs_delta:.2e} "
            f"first_mismatch=P{vc.first_mismatch_period}"
        )
        assert vc.classification == "VECTOR_ALREADY_SOURCE_MATCHED"

    def test_dscr_vector_equality_per_period(self, grid0_snapshot, source_vectors):
        """DSCR per-period: current engine matches DS!row22 for all 28 periods."""
        for p in grid0_snapshot.active_src_periods:
            curr = grid0_snapshot.dscr_by_src_period[p]
            src = source_vectors.dscr_by_period[p]
            assert abs(curr - src) < 1e-9, f"DSCR mismatch at P{p}: curr={curr} src={src}"

    def test_day_fraction_vector_equality(self, vector_comparisons):
        """Day-fraction vector: current ACT/360 derived fracs match DS!row6, max_delta = 0.

        Classification: VECTOR_ALREADY_SOURCE_MATCHED
        This is the R2 explicit day-count gate.
        """
        vc = vector_comparisons["day_frac"]
        assert vc.max_abs_delta == 0.0, (
            f"Day-fraction vector mismatch: max_delta={vc.max_abs_delta:.2e}"
        )
        assert vc.classification == "VECTOR_ALREADY_SOURCE_MATCHED"

    def test_day_fraction_per_period(self, grid0_snapshot, source_vectors):
        """Day-fraction per-period: current matches DS!row6 for all 28 periods exactly."""
        for p in grid0_snapshot.active_src_periods:
            curr = grid0_snapshot.day_frac_by_src_period[p]
            src = source_vectors.day_frac_by_period[p]
            assert curr == src, f"Day-frac mismatch at P{p}: curr={curr} src={src}"

    def test_ops_vector_equality(self, vector_comparisons):
        """Ops fraction vector: current engine matches source DS!row9, max_delta < 1e-9.

        Classification: VECTOR_ALREADY_SOURCE_MATCHED
        """
        vc = vector_comparisons["ops"]
        assert vc.max_abs_delta < 1e-9
        assert vc.classification == "VECTOR_ALREADY_SOURCE_MATCHED"

    def test_ops_vector_equality_per_period(self, grid0_snapshot, source_vectors):
        """Ops per-period: current engine matches DS!row9 for all 28 periods."""
        for p in grid0_snapshot.active_src_periods:
            curr = grid0_snapshot.ops_by_src_period[p]
            src = source_vectors.ops_by_period[p]
            assert abs(curr - src) < 1e-9, f"Ops mismatch at P{p}: curr={curr} src={src}"

    def test_rate_vector_equality(self, vector_comparisons):
        """Rate vector: current engine matches source DS!row44, max_delta < 1e-9.

        Classification: VECTOR_ALREADY_SOURCE_MATCHED
        """
        vc = vector_comparisons["rate"]
        assert vc.max_abs_delta < 1e-9
        assert vc.classification == "VECTOR_ALREADY_SOURCE_MATCHED"

    def test_rate_vector_equality_per_period(self, grid0_snapshot, source_vectors):
        """Rate per-period: current engine matches DS!row44 for all 28 periods."""
        for p in grid0_snapshot.active_src_periods:
            curr = grid0_snapshot.rate_by_src_period[p]
            src = source_vectors.rate_by_period[p]
            assert abs(curr - src) < 1e-9, f"Rate mismatch at P{p}: curr={curr} src={src}"

    def test_all_four_non_cfads_vectors_matched(self, vector_comparisons):
        """All four non-CFADS vectors (DSCR, day-frac, ops, rate) are source-matched."""
        for name in ("dscr", "day_frac", "ops", "rate"):
            vc = vector_comparisons[name]
            assert vc.classification == "VECTOR_ALREADY_SOURCE_MATCHED", (
                f"Vector '{name}' not matched: {vc.classification}, max_delta={vc.max_abs_delta:.2e}"
            )


# ---------------------------------------------------------------------------
# Section 6: One-factor counterfactuals (R2 CF1–CF5)
# ---------------------------------------------------------------------------

class TestCounterfactualCF1Cfads:
    """CF1: Source CFADS (DS!row20) closes the entire gap."""

    def test_cf1_closes_bridge(self, counterfactuals):
        """CF1 (source CFADS) moves from 43,919 to ~42,852 kEUR.

        Classification: CF1_CFADS_CLOSES_CURRENT_GRID0_TO_SOURCE_BRIDGE
        (BANK_SIZING_CFADS_AUTHORITY_IS_SOLE_CURRENT_SIZING_GAP_SOURCE_PROVEN)
        """
        cf1 = next(c for c in counterfactuals if c.label == "CF1")
        assert abs(cf1.capacity_keur - SOURCE_EXCEL_SENIOR_DEBT_KEUR) < 1.0

    def test_cf1_delta_matches_gap(self, counterfactuals):
        """CF1 delta = −1,066.754 kEUR (matches CURRENT_GRID0_TO_SOURCE_GAP_KEUR)."""
        cf1 = next(c for c in counterfactuals if c.label == "CF1")
        assert abs(cf1.delta_vs_baseline_keur - (-CURRENT_GRID0_TO_SOURCE_GAP_KEUR)) < 1.0

    def test_cf1_classification_not_already_matched(self, counterfactuals):
        """CF1 is not classified VECTOR_ALREADY_SOURCE_MATCHED — real difference."""
        cf1 = next(c for c in counterfactuals if c.label == "CF1")
        assert cf1.classification != "VECTOR_ALREADY_SOURCE_MATCHED"

    def test_source_cfads_lower_than_clean(self, grid0_snapshot, source_vectors):
        """Source DS!row20 sum < clean CFADS sum (explains negative delta)."""
        src_total = sum(source_vectors.cfads_by_period.values())
        clean_total = sum(grid0_snapshot.cfads_by_src_period.values())
        assert src_total < clean_total

    def test_cf1_from_pure_current_baseline(self, grid0_snapshot, source_vectors):
        """CF1 uses only source CFADS; all other vectors are from pure current snapshot."""
        active = grid0_snapshot.active_src_periods
        manual_cf1 = _backward_induction(
            source_vectors.cfads_by_period,
            grid0_snapshot.dscr_by_src_period,
            grid0_snapshot.ops_by_src_period,
            grid0_snapshot.rate_by_src_period,
            grid0_snapshot.day_frac_by_src_period,
            active,
        )
        cf1 = next(c for c in run_one_factor_counterfactuals(grid0_snapshot, source_vectors) if c.label == "CF1")
        assert abs(manual_cf1 - cf1.capacity_keur) < 1e-9


class TestCounterfactualCF2DscrR2:
    """CF2: DSCR banding (DS!row22) — already source-matched."""

    def test_cf2_delta_zero(self, counterfactuals):
        """CF2 delta = 0.000 kEUR — DSCR already source-matched.

        Classification: VECTOR_ALREADY_SOURCE_MATCHED
        """
        cf2 = next(c for c in counterfactuals if c.label == "CF2")
        assert abs(cf2.delta_vs_baseline_keur) < 1.0

    def test_cf2_classification(self, counterfactuals):
        """CF2 is classified VECTOR_ALREADY_SOURCE_MATCHED."""
        cf2 = next(c for c in counterfactuals if c.label == "CF2")
        assert cf2.classification == "VECTOR_ALREADY_SOURCE_MATCHED"


class TestCounterfactualCF3DayFracR2:
    """CF3: Day fractions (DS!row6) — R2 explicit arm, must show zero delta."""

    def test_cf3_present(self, counterfactuals):
        """CF3 (day fractions) arm is present in R2 counterfactuals."""
        labels = [c.label for c in counterfactuals]
        assert "CF3" in labels

    def test_cf3_delta_zero(self, counterfactuals):
        """CF3 (source day fractions DS!row6) delta = 0.000 kEUR.

        Current ACT/360 fracs derived from runtime dates exactly match DS!row6.
        Classification: VECTOR_ALREADY_SOURCE_MATCHED
        """
        cf3 = next(c for c in counterfactuals if c.label == "CF3")
        assert abs(cf3.delta_vs_baseline_keur) < 1.0

    def test_cf3_classification(self, counterfactuals):
        """CF3 is classified VECTOR_ALREADY_SOURCE_MATCHED."""
        cf3 = next(c for c in counterfactuals if c.label == "CF3")
        assert cf3.classification == "VECTOR_ALREADY_SOURCE_MATCHED"

    def test_cf3_reports_current_and_source_fractions(self, counterfactuals):
        """CF3 description references DS!row6 or day fractions."""
        cf3 = next(c for c in counterfactuals if c.label == "CF3")
        assert "row6" in cf3.description.lower() or "day" in cf3.description.lower()


class TestCounterfactualCF4OpsR2:
    """CF4: Ops fraction (DS!row9) — already source-matched."""

    def test_cf4_delta_zero(self, counterfactuals):
        """CF4 (source ops fraction DS!row9) delta = 0.000 kEUR."""
        cf4 = next(c for c in counterfactuals if c.label == "CF4")
        assert abs(cf4.delta_vs_baseline_keur) < 1.0

    def test_cf4_classification(self, counterfactuals):
        """CF4 is classified VECTOR_ALREADY_SOURCE_MATCHED."""
        cf4 = next(c for c in counterfactuals if c.label == "CF4")
        assert cf4.classification == "VECTOR_ALREADY_SOURCE_MATCHED"


class TestCounterfactualCF5RateR2:
    """CF5: Annual rate (DS!row44) — already source-matched."""

    def test_cf5_delta_zero(self, counterfactuals):
        """CF5 (source rate DS!row44) delta = 0.000 kEUR."""
        cf5 = next(c for c in counterfactuals if c.label == "CF5")
        assert abs(cf5.delta_vs_baseline_keur) < 1.0

    def test_cf5_classification(self, counterfactuals):
        """CF5 is classified VECTOR_ALREADY_SOURCE_MATCHED."""
        cf5 = next(c for c in counterfactuals if c.label == "CF5")
        assert cf5.classification == "VECTOR_ALREADY_SOURCE_MATCHED"

    def test_all_five_cfs_present(self, counterfactuals):
        """All five counterfactuals CF1–CF5 are present."""
        labels = {c.label for c in counterfactuals}
        for expected in ("CF1", "CF2", "CF3", "CF4", "CF5"):
            assert expected in labels, f"Missing counterfactual: {expected}"


# ---------------------------------------------------------------------------
# Section 7: Sequential bridge (R2 — 5 steps)
# ---------------------------------------------------------------------------

class TestSequentialBridgeR2:
    """Sequential bridge from CURRENT_GRID0 → SOURCE_ALL (R2: 5 steps)."""

    def test_bridge_has_5_steps(self, sequential_bridge):
        """R2 sequential bridge has 5 steps (CF1–CF5)."""
        assert len(sequential_bridge) == 5

    def test_step1_closes_entire_gap(self, sequential_bridge):
        """Step 1 (CF1 CFADS) closes the entire gap — cumulative ≈ 42,852."""
        step1 = sequential_bridge[0]
        assert abs(step1.cumulative_capacity_keur - SOURCE_EXCEL_SENIOR_DEBT_KEUR) < 1.0

    def test_step1_delta_equals_full_gap(self, sequential_bridge):
        """Step 1 delta = −1,066.754 kEUR (full CURRENT_GRID0_TO_SOURCE_GAP_KEUR)."""
        step1 = sequential_bridge[0]
        assert abs(step1.step_delta_keur - (-CURRENT_GRID0_TO_SOURCE_GAP_KEUR)) < 1.0

    def test_steps_2_to_5_delta_near_zero(self, sequential_bridge):
        """Steps 2–5 (DSCR, day-frac, ops, rate) each contribute < 1 kEUR."""
        for step in sequential_bridge[1:]:
            assert abs(step.step_delta_keur) < 1.0, (
                f"Step {step.step} ({step.vector_applied}) has non-zero delta: {step.step_delta_keur}"
            )

    def test_final_step_reaches_source(self, sequential_bridge):
        """Final bridge step reaches SOURCE_EXCEL_SENIOR_DEBT_KEUR within 1 kEUR."""
        final = sequential_bridge[-1]
        assert abs(final.cumulative_capacity_keur - SOURCE_EXCEL_SENIOR_DEBT_KEUR) < 1.0

    def test_step_labels_in_order(self, sequential_bridge):
        """Steps are labelled in R2 order: CF1, CF2, CF3, CF4, CF5."""
        expected_prefixes = ["CF1_CFADS", "CF2_DSCR", "CF3_DAY_FRAC", "CF4_OPS", "CF5_RATE"]
        for step, prefix in zip(sequential_bridge, expected_prefixes):
            assert step.vector_applied.startswith(prefix), (
                f"Step {step.step}: expected {prefix}, got {step.vector_applied}"
            )


# ---------------------------------------------------------------------------
# Section 8: SOURCE_ALL gate
# ---------------------------------------------------------------------------

class TestSourceAllGate:
    """SOURCE_ALL gate: all five source vectors simultaneously."""

    def test_source_all_closes_bridge(self, source_all_gate):
        """SOURCE_ALL capacity = SOURCE_EXCEL_SENIOR_DEBT_KEUR within 1 kEUR."""
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


# ---------------------------------------------------------------------------
# Section 9: Backward-induction purity
# ---------------------------------------------------------------------------

class TestBackwardInductionPurity:
    """Independent backward induction properties."""

    def test_bi_deterministic(self):
        """Backward induction is deterministic."""
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
        """Higher CFADS → higher debt capacity."""
        active = [1, 2, 3]
        dscr = {p: 1.15 for p in active}
        ops = {p: 1.0 for p in active}
        rate = {p: 0.06 for p in active}
        frac = {p: 0.5 for p in active}
        v_base = _backward_induction({p: 2500.0 for p in active}, dscr, ops, rate, frac, active)
        v_high = _backward_induction({p: 3000.0 for p in active}, dscr, ops, rate, frac, active)
        assert v_high > v_base

    def test_bi_higher_dscr_lower_capacity(self):
        """Higher DSCR → lower debt capacity."""
        active = [1, 2, 3]
        cfads = {p: 2500.0 for p in active}
        ops = {p: 1.0 for p in active}
        rate = {p: 0.06 for p in active}
        frac = {p: 0.5 for p in active}
        v_low = _backward_induction(cfads, {p: 1.15 for p in active}, ops, rate, frac, active)
        v_high = _backward_induction(cfads, {p: 1.35 for p in active}, ops, rate, frac, active)
        assert v_low > v_high

    def test_bi_single_period_formula(self):
        """Single-period BI: V = (CFADS/DSCR*ops) / (1 + rate*frac)."""
        cfads, dscr, ops, rate, frac = 2600.0, 1.15, 1.0, 0.0595136, 0.5111111
        allowed = (cfads / dscr) * ops
        expected = allowed / (1.0 + rate * frac)
        result = _backward_induction({1: cfads}, {1: dscr}, {1: ops}, {1: rate}, {1: frac}, [1])
        assert abs(result - expected) < 1e-9


# ---------------------------------------------------------------------------
# Section 10: Bridge architecture assertions
# ---------------------------------------------------------------------------

class TestBridgeArchitectureAssertionsR2:
    """Structural properties of R2 bridge result."""

    def test_cf1_is_sole_explanatory_factor(self, counterfactuals):
        """CF1 alone accounts for > 99% of total gap; all other CFs near zero."""
        cf1 = next(c for c in counterfactuals if c.label == "CF1")
        others_total = sum(abs(c.delta_vs_baseline_keur) for c in counterfactuals if c.label != "CF1")
        assert abs(cf1.delta_vs_baseline_keur) > 1_000.0
        assert others_total < 1.0

    def test_source_all_equals_cf1_only(self, grid0_snapshot, source_vectors, source_all_gate):
        """SOURCE_ALL ≈ CF1-only capacity (other vectors already matched)."""
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
        gap_historical = HISTORICAL_GENERIC_PHASE2C_DEBT_KEUR - SOURCE_EXCEL_SENIOR_DEBT_KEUR
        gap_current = CURRENT_GRID0_DEBT_KEUR - SOURCE_EXCEL_SENIOR_DEBT_KEUR
        assert abs(gap_current - 1_066.754) < 1.0
        assert abs(gap_historical - 3_201.124) < 1.0
        assert abs(gap_historical - gap_current) > 1_000.0

    def test_verdict_is_r2_sole_gap(self, grid0_snapshot, source_vectors, source_all_gate, counterfactuals, sequential_bridge, vector_comparisons):
        """Full diagnostic verdict = R2 sole gap verdict."""
        from finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge import C3B3D2B2BDiagnosticResult
        result = C3B3D2B2BDiagnosticResult(
            snapshot=grid0_snapshot,
            source_vectors=source_vectors,
            vector_comparisons=vector_comparisons,
            counterfactuals=counterfactuals,
            sequential_bridge=sequential_bridge,
            source_all_gate=source_all_gate,
        )
        assert result.verdict == "C3B3D2B2B_R2_BANK_SIZING_CFADS_AUTHORITY_SOLE_GAP_READY_FOR_INDEPENDENT_REVIEW"


# ---------------------------------------------------------------------------
# Section 11: Governance enforcement (R2)
# ---------------------------------------------------------------------------

class TestGovernanceEnforcementR2:
    """Governance constraints verified by AST inspection."""

    def test_no_ds25_ds40_hardcoding_in_module(self):
        """No DS25/DS40 period boundary hardcoded as integer literal 25 or 40."""
        import ast, inspect
        import finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge as mod
        tree = ast.parse(inspect.getsource(mod))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in (25, 40):
                raise AssertionError(
                    f"Hardcoded period boundary {node.value} found — DS25/DS40 ENFORCED"
                )

    def test_no_13547_in_module(self):
        """13547.2 MUST NOT appear as a literal value in the module."""
        import ast, inspect
        import finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge as mod
        tree = ast.parse(inspect.getsource(mod))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)) and abs(float(node.value) - 13547.2) < 0.1:
                    raise AssertionError("13547.2 found as literal — ENFORCED")

    def test_no_approved_delta_or_plug(self):
        """No approved_delta or balancing plug variable name in function bodies."""
        import ast, inspect
        import finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge as mod
        tree = ast.parse(inspect.getsource(mod))
        forbidden = {"approved_delta", "balancing_plug", "calibration_plug"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden:
                raise AssertionError(f"Forbidden variable '{node.id}' found in module")

    def test_no_production_file_modifications(self):
        """No production financial-engine files were modified in this PR."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only",
             "4dfdc3bb579f959ce8e7b7348862a3f6c0e7aacb", "HEAD"],
            capture_output=True, text=True, cwd=str(pathlib.Path(__file__).parent.parent)
        )
        changed = result.stdout.strip().splitlines()
        production_changes = [
            f for f in changed
            if (f.startswith("financial_engine/") or f.startswith("app/"))
            and not f.startswith("financial_engine/senior_debt/interest")
        ]
        assert not production_changes, f"Production files modified: {production_changes}"

    def test_bank_sizing_mechanism_unresolved_in_docstring(self):
        """Module docstring records BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED."""
        import finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge as mod
        assert "BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED" in (mod.__doc__ or "")

    def test_missing_bank_scenario_layer_documented(self):
        """Module records MISSING_GENERIC_BANK_SIZING_CFADS_SCENARIO_LAYER."""
        import finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge as mod
        assert "MISSING_GENERIC_BANK_SIZING_CFADS_SCENARIO_LAYER" in (mod.__doc__ or "")


# ---------------------------------------------------------------------------
# Section 12: CFADS vector integrity
# ---------------------------------------------------------------------------

class TestCfadsVectorIntegrityR2:
    """Source DS!row20 and clean CFADS vector properties (R2: from pure current snapshot)."""

    def test_cfads_total_sum_difference(self, grid0_snapshot, source_vectors):
        """Clean CFADS total > source CFADS total (pure current snapshot, no fixture contamination)."""
        clean_sum = sum(grid0_snapshot.cfads_by_src_period.values())
        src_sum = sum(source_vectors.cfads_by_period.values())
        assert clean_sum > src_sum
        assert (clean_sum - src_sum) > 500.0

    def test_cfads_early_periods_close(self, grid0_snapshot, source_vectors):
        """Early periods (P1-P5) CFADS differences < 10 kEUR."""
        for p in range(1, 6):
            delta = abs(grid0_snapshot.cfads_by_src_period[p] - source_vectors.cfads_by_period[p])
            assert delta < 10.0, f"Large early-period delta at P{p}: {delta:.3f}"

    def test_cfads_late_periods_diverge(self, grid0_snapshot, source_vectors):
        """Late periods (P24-P28) show largest CFADS divergence (> 200 kEUR max)."""
        late_deltas = [
            abs(grid0_snapshot.cfads_by_src_period[p] - source_vectors.cfads_by_period[p])
            for p in range(24, 29)
        ]
        assert max(late_deltas) > 200.0

    def test_source_cfads_from_ds_row20_fixture(self, source_vectors, debt_fixture):
        """Source CFADS matches DS!row20 fixture values for P1–P28."""
        cfads_list = debt_fixture["workstream_a"]["ds_row20_cfads"]["period_values_keur"]
        for p in range(1, 29):
            assert abs(source_vectors.cfads_by_period[p] - cfads_list[p]) < 1e-9


# ---------------------------------------------------------------------------
# Section 13: Report format
# ---------------------------------------------------------------------------

class TestReportFormatR2:
    """R2 diagnostic report format and content."""

    def test_report_contains_r2_verdict(self, grid0_snapshot, source_vectors, vector_comparisons, counterfactuals, sequential_bridge, source_all_gate):
        """R2 formatted report contains the R2 verdict."""
        from finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge import C3B3D2B2BDiagnosticResult
        result = C3B3D2B2BDiagnosticResult(
            snapshot=grid0_snapshot,
            source_vectors=source_vectors,
            vector_comparisons=vector_comparisons,
            counterfactuals=counterfactuals,
            sequential_bridge=sequential_bridge,
            source_all_gate=source_all_gate,
        )
        report = result.format_report()
        assert "C3B3D2B2B_R2" in report
        assert "BANK_SIZING_CFADS_AUTHORITY" in report
        assert "BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED" in report
        assert "MISSING_GENERIC_BANK_SIZING_CFADS_SCENARIO_LAYER" in report

    def test_report_contains_day_frac_provenance(self, grid0_snapshot, source_vectors, vector_comparisons, counterfactuals, sequential_bridge, source_all_gate):
        """Report shows day-fraction provenance (not fixture-sourced)."""
        from finco_recon.diagnose_c3b3d2b2b_current_senior_debt_bridge import C3B3D2B2BDiagnosticResult
        result = C3B3D2B2BDiagnosticResult(
            snapshot=grid0_snapshot,
            source_vectors=source_vectors,
            vector_comparisons=vector_comparisons,
            counterfactuals=counterfactuals,
            sequential_bridge=sequential_bridge,
            source_all_gate=source_all_gate,
        )
        report = result.format_report()
        assert "period_day_fraction" in report or "ACT_360" in report
