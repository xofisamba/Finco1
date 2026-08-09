"""financial_engine.adapters.shl_inputs — ProjectInputs → ShlSchedulePolicy adapter (C3B3D1).

Maps canonical ProjectInputs.financing to ShlSchedulePolicy.
Returns None if the financing params cannot be mapped cleanly (fail-closed).

IMPORTANT: This adapter is NOT wired into orchestrator.py, waterfall_engine.py,
or any existing production path. It is adapter foundation only.
Production runtime wiring is deferred to C3B3D2.

Lineage notes:
  OBOROVO_SHL_BALANCE_LINEAGE_UNRESOLVED — construction → operating opening balance
      transition cannot be proven from committed source evidence alone. The adapter
      does NOT promote Oborovo or TUHO to the canonical schedule runtime.
  TUHO_SHL_BALANCE_LINEAGE_UNRESOLVED — same boundary status as Oborovo.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from finco_core.inputs import ProjectInputs

from financial_engine.shl.contracts import (
    ShlInterestPaymentMode,
    ShlInterestRateMode,
    ShlRepaymentMode,
    ShlSchedulePolicy,
)

# SHL repayment method strings that require FCF-waterfall cash integration (D2 scope).
_FCF_WATERFALL_METHODS = frozenset({
    "fcf_waterfall",
    "cash_sweep",
    "partial_pay_sweep",
    "pik_then_sweep",
})

# SHL repayment method strings that map to BULLET.
_BULLET_METHODS = frozenset({"bullet"})

# SHL repayment method strings that map to EXPLICIT_SCHEDULE.
_EXPLICIT_SCHEDULE_METHODS = frozenset({"accrued", "pik"})


def build_shl_schedule_policy_from_project_inputs(
    project: "ProjectInputs",
) -> ShlSchedulePolicy | None:
    """Map ProjectInputs.financing to ShlSchedulePolicy.

    Parameters
    ----------
    project : ProjectInputs
        Canonical project inputs.

    Returns
    -------
    ShlSchedulePolicy or None.
        None is returned when the repayment method requires FCF-waterfall cash
        integration (C3B3D1_BLOCKED_FCF_REPAYMENT). The caller must handle None
        as "canonical SHL schedule not available for this configuration."

    Notes
    -----
    * shl_amount_keur is used only for validation/reference. The canonical
      opening balance is NOT shl_amount_keur — it comes from the construction
      output (seam deferred to C3B3D2, labelled C3B3D2_CONSTRUCTION_SEAM).
    * shl_pik_switch_period > 0 signals a future mixed PIK→cash mode. This is
      documented as DEFERRED for D2. The adapter defaults to CASH_PAID when
      shl_pik_switch_period == 0 or None.
    * No project.name or project.code dispatch. Policy is derived solely from
      financing field values.

    Raises
    ------
    NotImplementedError
        When repayment method is FCF_WATERFALL/CASH_SWEEP (C3B3D1_BLOCKED_FCF_REPAYMENT).
        This is fail-closed, not silent.
    ValueError
        When shl_rate is not finite or is negative.
    """
    financing = project.financing

    # ── annual rate ─────────────────────────────────────────────────────────
    annual_rate: float = financing.shl_rate
    # Validation is delegated to ShlSchedulePolicy.__post_init__ (raises ValueError).

    # ── repayment mode ───────────────────────────────────────────────────────
    method_raw: str = getattr(financing, "shl_repayment_method", "bullet")
    method = (method_raw or "bullet").strip().lower()

    if method in _FCF_WATERFALL_METHODS:
        raise NotImplementedError(
            f"C3B3D1_BLOCKED_FCF_REPAYMENT: shl_repayment_method={method_raw!r} "
            "requires FCF-waterfall cash integration (C3B3D2 scope). "
            "Canonical SHL schedule cannot be built for this configuration in C3B3D1."
        )
    elif method in _BULLET_METHODS:
        repayment_mode = ShlRepaymentMode.BULLET
    elif method in _EXPLICIT_SCHEDULE_METHODS:
        repayment_mode = ShlRepaymentMode.EXPLICIT_SCHEDULE
    else:
        # Unknown method — fail closed.
        raise NotImplementedError(
            f"C3B3D1_BLOCKED_UNKNOWN_REPAYMENT: shl_repayment_method={method_raw!r} "
            "is not recognised by the C3B3D1 canonical adapter. "
            "Add mapping or check FinancingParams SHLRepaymentMethod enum."
        )

    # ── interest payment mode ────────────────────────────────────────────────
    # shl_pik_switch_period == 0 or None → default CASH_PAID.
    # shl_pik_switch_period > 0 → mixed PIK→cash mode, DEFERRED to D2.
    pik_switch: int = getattr(financing, "shl_pik_switch_period", 0) or 0
    if pik_switch > 0:
        # DEFERRED: mixed mode requires period-level payment switching (D2 scope).
        # Return None so the caller skips canonical SHL schedule for this project.
        return None

    payment_mode = ShlInterestPaymentMode.CASH_PAID

    return ShlSchedulePolicy(
        annual_rate=annual_rate,
        rate_mode=ShlInterestRateMode.FIXED,
        payment_mode=payment_mode,
        repayment_mode=repayment_mode,
    )
