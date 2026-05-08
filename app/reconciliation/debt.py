"""Debt schedule reconciliation helper."""
from typing import Any


def build_debt_schedule_rows(result: Any) -> list[dict]:
    """Build debt schedule reconciliation rows from a DemoResult or WaterfallResult.

    Returns list of dicts with columns:
        period, date, opening_senior_debt, senior_interest, senior_principal,
        total_senior_ds, closing_senior_debt, cfads, dscr

    Handles DemoResult (result.waterfall_result IS the WaterfallResult) and raw WaterfallResult.
    Supports both IterativeSculptResult (field: payments) and ClosedFormSculptResult (field: payment_schedule).
    
    Opening balance: balance_sched[op_idx] = opening balance for operation period op_idx
    Closing balance: opening - principal (computed from sculpt schedule for consistency)
    
    balance_sched[t] is the opening balance at the start of operation period t (0-indexed).
    This means balance_sched[0] = initial debt (period 0/construction doesn't count).
    """
    # Unwrap DemoResult → WaterfallResult
    wf = None
    if hasattr(result, "result") and hasattr(result, "waterfall_result"):
        wf = result.waterfall_result
    elif hasattr(result, "periods"):
        wf = result

    if wf is None:
        return []

    periods = wf.periods if hasattr(wf, "periods") else []
    if not periods:
        return []

    sculpt = wf.sculpting_result if hasattr(wf, "sculpting_result") and wf.sculpting_result else None

    # Resolve sculpt schedule fields
    if sculpt:
        debt_keur = sculpt.debt_keur
        interest_sched = sculpt.interest_schedule
        principal_sched = sculpt.principal_schedule
        balance_sched = sculpt.balance_schedule
        dscr_sched = sculpt.dscr_schedule
        payment_sched = getattr(sculpt, "payments", None) or getattr(sculpt, "payment_schedule", [])
    else:
        debt_keur = 0.0
        interest_sched = principal_sched = balance_sched = dscr_sched = []
        payment_sched = []

    # Build CFADS per operation period
    op_periods = [p for p in periods if p.is_operation]
    cfads_list = [p.ebitda_keur for p in op_periods]

    rows = []
    op_idx = 0  # operation period index for sculpt schedule lookup

    for p in periods:
        if not p.is_operation:
            continue

        # Determine values from sculpt schedule (aligned to operation index)
        if sculpt and op_idx < len(interest_sched):
            si = interest_sched[op_idx]
            sp = principal_sched[op_idx]
            total_ds = payment_sched[op_idx] if op_idx < len(payment_sched) else si + sp
            dscr_val = dscr_sched[op_idx] if op_idx < len(dscr_sched) else 0.0
        else:
            si = p.senior_interest_keur
            sp = p.senior_principal_keur
            total_ds = p.senior_ds_keur
            dscr_val = p.dscr

        # Opening balance from sculpt schedule
        # balance_sched[op_idx] = opening balance for operation period op_idx
        if sculpt and op_idx < len(balance_sched):
            opening = balance_sched[op_idx]
        elif op_idx == 0:
            opening = debt_keur
        else:
            opening = p.senior_balance_keur + sp  # fallback

        # Closing balance = opening - principal (from sculpt for consistency)
        closing = opening - sp

        # Use waterfall CFADS
        cfads = p.ebitda_keur

        # Guard against inf/nan DSCR (zero payment / zero CFADS → loan repaid)
        if dscr_val == float('inf') or (isinstance(dscr_val, float) and dscr_val != dscr_val):  # NaN check
            dscr_val = 0.0  # Repaid period — no active debt service
        elif dscr_val <= 0:
            dscr_val = 0.0

        rows.append({
            "period": p.period,
            "date": p.date,
            "opening_senior_debt": round(opening, 1),
            "senior_interest": round(si, 1),
            "senior_principal": round(sp, 1),
            "total_senior_ds": round(total_ds, 1),
            "closing_senior_debt": round(closing, 1),
            "cfads": round(cfads, 1),
            "dscr": round(dscr_val, 3) if dscr_val else 0.0,
        })
        op_idx += 1

    return rows