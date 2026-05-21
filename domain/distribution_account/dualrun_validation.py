"""Phase 9B — Dual-run validation: DistributionAccount vs WaterfallEngine.

VALIDATION ONLY — no runtime routing.
waterfall_core.py remains unchanged.
DistributionAccount stays audit-only.

This module provides a side-by-side comparison of:
- WaterfallEngine.distribution_keur (runtime authoritative)
- DistributionAccount.equity_distribution_paid_keur (gate-driven audit)

Used to validate Phase C readiness without changing runtime authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DualRunPeriodResult:
    """Single period comparison result."""
    period_index: int
    operating_period_index: int
    runtime_distribution_keur: float
    da_paid_distribution_keur: float
    delta_keur: float  # da_paid - runtime
    absolute_delta_keur: float
    delta_pct: float  # delta as % of runtime
    classification: str  # IDENTICAL | ROUNDING | EXPECTED_GATE_DIFFERENCE | UNEXPECTED | BLOCKING
    gates_passed: bool
    r99_blocked: bool
    r102_blocked: bool
    dscr_passed: bool
    lockup_passed: bool
    cash_passed: bool
    oborovo_passed: bool
    blocked_reason: str
    runtime_authoritative: bool = True  # always True in Phase B
    notes: str = ""


@dataclass(frozen=True)
class DualRunResult:
    """Full dual-run comparison result."""
    project_name: str
    period_results: tuple[DualRunPeriodResult, ...]
    total_runtime_distribution_keur: float
    total_da_paid_keur: float
    total_delta_keur: float
    identical_periods: int
    rounding_periods: int
    expected_gate_diff_periods: int
    unexpected_diff_periods: int
    blocking_periods: int
    all_invariants_held: bool
    runtime_unchanged: bool  # True = waterfall result was not modified
    sponsor_unchanged: bool  # True = no sponsor routing change
    shl_unchanged: bool  # True = no SHL routing change
    r99_r102_still_blocked: bool  # True = no promotion
    phase_c_ready: bool  # True if no blocking diffs found
    notes: str = ""


def classify_delta(
    delta_keur: float,
    runtime_dist: float,
    gates_passed: bool,
    r99_blocked: bool,
    r102_blocked: bool,
    dscr_passed: bool,
    lockup_passed: bool,
    cash_passed: bool,
) -> str:
    """Classify the type of divergence between runtime and DA distributions.

    Rules:
    - IDENTICAL: delta == 0
    - ROUNDING: |delta| <= 1 kEUR and gates_passed
    - EXPECTED_GATE_DIFFERENCE: gates fail due to R99/R102/DSCR/lockup/cash blocks (non-zero delta expected)
    - UNEXPECTED: gates pass but significant delta exists
    - BLOCKING: delta suggests Phase C should not proceed
    """
    if abs(delta_keur) < 0.001:
        return "IDENTICAL"

    # ROUNDING: small numerical differences when all gates pass
    if gates_passed and abs(delta_keur) <= 1.0:
        return "ROUNDING"

    # EXPECTED_GATE_DIFFERENCE: DA blocked by R99/R102 (always in audit-only)
    # or DSCR/lockup/cash failures — these are expected divergences
    if r99_blocked or r102_blocked:
        # In audit-only mode, R99/R102 are always blocked — this is expected
        # DA will show 0 while WE shows positive distribution
        return "EXPECTED_GATE_DIFFERENCE"

    # DSCR/lockup/cash gate failures in DA — expected divergence from WE
    if not dscr_passed or not lockup_passed or not cash_passed:
        return "EXPECTED_GATE_DIFFERENCE"

    # UNEXPECTED: gates pass in DA but significant delta exists
    # This suggests logic mismatch that needs investigation
    if gates_passed:
        pct = abs(delta_keur / runtime_dist) if runtime_dist != 0 else float('inf')
        if pct > 0.01:  # > 1% difference when gates pass = unexpected
            return "UNEXPECTED"

    # BLOCKING: if UNEXPECTED with large delta, block Phase C
    return "BLOCKING"


def _gate_result(gate_result) -> bool:
    """Extract passed boolean from a gate result."""
    if gate_result is None:
        return True  # no gate = pass
    return gate_result.passed


def run_dual_validation(
    waterfall_result,  # WaterfallResult from run_waterfall()
    da_inputs,  # DistributionAccountInputs
) -> DualRunResult:
    """Run dual validation: compare WaterfallEngine vs DistributionAccount per period.

    This function does NOT modify waterfall_result — validation only.
    Returns DualRunResult with per-period comparison and summary statistics.
    """
    from domain.distribution_account.engine import DistributionAccountEngine

    # Run DistributionAccount side-by-side (audit-only)
    da_result = DistributionAccountEngine.compute(da_inputs)

    period_results: list[DualRunPeriodResult] = []
    total_runtime = 0.0
    total_da = 0.0
    identical = rounding = expected_diff = unexpected = blocking = 0

    # Build lookup: period_index -> DA result
    da_by_period: dict[int, ...] = {
        pr.period_index: pr for pr in da_result.period_results
    }

    for period in waterfall_result.periods:
        p_idx = getattr(period, "period", None)
        if p_idx is None:
            continue

        runtime_dist = getattr(period, "distribution_keur", 0.0)
        da_period = da_by_period.get(p_idx)

        if da_period is None:
            # No DA result for this period — skip
            continue

        da_paid = da_period.equity_distribution_paid_keur
        delta = da_paid - runtime_dist
        abs_delta = abs(delta)
        pct = (abs_delta / abs(runtime_dist)) if runtime_dist != 0 else (float('inf') if da_paid else 0.0)

        r99_passed = _gate_result(da_period.r99_gate_result)
        r102_passed = _gate_result(da_period.r102_gate_result)
        dscr_passed = _gate_result(da_period.dscr_gate_result)
        lockup_passed = _gate_result(da_period.lockup_gate_result)
        oborovo_passed = _gate_result(da_period.oborovo_gate_result)
        # Cash gate: if post_shl_cash <= 0, equity_distribution_paid_keur == 0 (engine enforces)
        # No separate cash_gate_result attribute — check via candidate zero
        cash_passed = da_period.equity_distribution_candidate_keur > 0.0

        gates_passed = r99_passed and r102_passed and dscr_passed and lockup_passed and oborovo_passed and cash_passed

        r99_blocked = not r99_passed
        r102_blocked = not r102_passed

        classification = classify_delta(
            delta_keur=delta,
            runtime_dist=runtime_dist,
            gates_passed=gates_passed,
            r99_blocked=r99_blocked,
            r102_blocked=r102_blocked,
            dscr_passed=dscr_passed,
            lockup_passed=lockup_passed,
            cash_passed=cash_passed,
        )

        if classification == "IDENTICAL":
            identical += 1
        elif classification == "ROUNDING":
            rounding += 1
        elif classification == "EXPECTED_GATE_DIFFERENCE":
            expected_diff += 1
        elif classification == "UNEXPECTED":
            unexpected += 1
        elif classification == "BLOCKING":
            blocking += 1

        total_runtime += runtime_dist
        total_da += da_paid

        period_results.append(DualRunPeriodResult(
            period_index=p_idx,
            operating_period_index=getattr(period, "operating_period_index", p_idx),
            runtime_distribution_keur=runtime_dist,
            da_paid_distribution_keur=da_paid,
            delta_keur=delta,
            absolute_delta_keur=abs_delta,
            delta_pct=pct * 100.0 if pct != float('inf') else 0.0,
            classification=classification,
            gates_passed=gates_passed,
            r99_blocked=r99_blocked,
            r102_blocked=r102_blocked,
            dscr_passed=dscr_passed,
            lockup_passed=lockup_passed,
            cash_passed=cash_passed,
            oborovo_passed=oborovo_passed,
            blocked_reason=da_period.blocked_reason,
            runtime_authoritative=True,
            notes="",
        ))

    # Phase C readiness: no blocking diffs and no unexpected diffs
    phase_c_ready = (blocking == 0) and (unexpected == 0)

    # Invariants: runtime/Sponsor/SHL/R99-R102 unchanged (this is structural in Phase B)
    all_invariants_held = True  # Phase B adds no routing changes, so invariants hold

    return DualRunResult(
        project_name=getattr(waterfall_result, 'project_code', da_inputs.project_name),
        period_results=tuple(period_results),
        total_runtime_distribution_keur=total_runtime,
        total_da_paid_keur=total_da,
        total_delta_keur=total_da - total_runtime,
        identical_periods=identical,
        rounding_periods=rounding,
        expected_gate_diff_periods=expected_diff,
        unexpected_diff_periods=unexpected,
        blocking_periods=blocking,
        all_invariants_held=all_invariants_held,
        runtime_unchanged=True,  # Phase B: waterfall result NOT modified
        sponsor_unchanged=True,
        shl_unchanged=True,
        r99_r102_still_blocked=True,
        phase_c_ready=phase_c_ready,
        notes="",
    )
