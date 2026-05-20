"""Gate evaluation logic for DistributionAccount."""
from __future__ import annotations

from domain.distribution_account.result import (
    DistributionGateResult,
    BLOCKED_REASONS,
)
from domain.distribution_account.inputs import (
    DistributionAccountPeriodInput,
    R99R102GateInputs,
)


def evaluate_r99_gate(
    inputs: R99R102GateInputs,
    cash_available: float,
    enable_runtime: bool,
) -> DistributionGateResult:
    """Evaluate R99 gate.

    R99 is the equity distribution gate.
    Always returns BLOCKED unless enable_r99_r102_runtime=True (never in this branch).
    """
    if not enable_runtime:
        return DistributionGateResult(
            gate_name="r99_gate",
            passed=False,
            blocked_reason=BLOCKED_REASONS["R99_BLOCKED"],
        )
    # Future: evaluate cumulative FCF vs senior debt outstanding
    # For now: return blocked
    return DistributionGateResult(
        gate_name="r99_gate",
        passed=False,
        blocked_reason=BLOCKED_REASONS["R99_BLOCKED"],
    )


def evaluate_r102_gate(
    inputs: R99R102GateInputs,
    cash_available: float,
    enable_runtime: bool,
) -> DistributionGateResult:
    """Evaluate R102 gate.

    R102 is the SHL sweep gate.
    Always returns BLOCKED unless enable_r99_r102_runtime=True (never in this branch).
    """
    if not enable_runtime:
        return DistributionGateResult(
            gate_name="r102_gate",
            passed=False,
            blocked_reason=BLOCKED_REASONS["R102_BLOCKED"],
        )
    return DistributionGateResult(
        gate_name="r102_gate",
        passed=False,
        blocked_reason=BLOCKED_REASONS["R102_BLOCKED"],
    )


def evaluate_dscr_gate(
    actual_dscr: float,
    target_dscr: float,
) -> DistributionGateResult:
    """Evaluate DSCR gate for distribution eligibility."""
    if actual_dscr >= target_dscr:
        return DistributionGateResult(
            gate_name="dscr_gate",
            passed=True,
            blocked_reason="",
        )
    return DistributionGateResult(
        gate_name="dscr_gate",
        passed=False,
        blocked_reason=BLOCKED_REASONS["DSCR_GATE_FAILED"],
        details=(f"actual_dscr={actual_dscr:.4f} < target={target_dscr:.4f}",),
    )


def evaluate_lockup_gate(
    period_index: int,
    senior_tenor_years: int,
    dsra_balance: float,
    dsra_target: float,
    jdsra_balance: float,
    jdsra_target: float,
    cash: float,
) -> DistributionGateResult:
    """Evaluate lockup gate — blocks distributions during lockup periods."""
    reasons: list[str] = []
    if period_index <= senior_tenor_years:
        reasons.append(f"within_senior_tenor(period={period_index})")
    if dsra_balance < dsra_target:
        reasons.append(f"dsra_below_target({dsra_balance:.1f} < {dsra_target:.1f})")
    if jdsra_balance < jdsra_target:
        reasons.append(f"jdsra_below_target({jdsra_balance:.1f} < {jdsra_target:.1f})")
    if cash < 0:
        reasons.append(f"negative_cash({cash:.1f})")

    if reasons:
        return DistributionGateResult(
            gate_name="lockup_gate",
            passed=False,
            blocked_reason=BLOCKED_REASONS["LOCKUP"],
            details=tuple(reasons),
        )
    return DistributionGateResult(
        gate_name="lockup_gate",
        passed=True,
        blocked_reason="",
    )


def evaluate_oborovo_guard(is_oborovo: bool) -> DistributionGateResult:
    """Oborovo guard — blocks TUHO-specific gates for Oborovo project."""
    if is_oborovo:
        return DistributionGateResult(
            gate_name="oborovo_guard",
            passed=False,
            blocked_reason=BLOCKED_REASONS["OBOROVO_NOT_SUPPORTED"],
        )
    return DistributionGateResult(
        gate_name="oborovo_guard",
        passed=True,
        blocked_reason="",
    )


def evaluate_cash_gate(cash_available: float) -> DistributionGateResult:
    """Evaluate cash sufficiency gate."""
    if cash_available >= 0:
        return DistributionGateResult(gate_name="cash_sufficiency_gate", passed=True)
    return DistributionGateResult(
        gate_name="cash_sufficiency_gate",
        passed=False,
        blocked_reason=BLOCKED_REASONS["NEGATIVE_CASH"],
        details=(f"cash_available={cash_available:.1f}",),
    )