"""C1A — Balance Sheet invariant: A = L + E must hold to within 1 kEUR.

These tests are intentionally failing on current main.  They expose a real
financial inconsistency in the canonical balance sheet output:

  TUHO    max |A − L − E| ≈ 40,805 kEUR
  Oborovo max |A − L − E| ≈ 17,033 kEUR

Root cause (two components):
1. H1/H2 tax timing: IS deducts tax_keur (accrual) every period; cash_balance
   only reflects tax_this_period (0 in H1, double in H2).  Equity tracks
   accrual-basis NI; assets track cash-basis outflows → growing gap.
2. SHL principal notional treatment: shl_principal_keur reduces L but not A.

These tests serve as the acceptance criterion for the BS fix.  They must not
be marked xfail, skipped, or have their tolerance raised.
"""
from __future__ import annotations

import pytest

from app.ui_runner import run_demo_project
from finco_core.financial_statements.balance_sheet import generate_balance_sheet

TOLERANCE_KEUR = 1.0


def _bs_violations(project_code: str) -> list[tuple[int, float]]:
    result = run_demo_project(project_code)
    inp = result.project_inputs
    r = result.result
    bs = generate_balance_sheet(
        r.periods,
        inp.capex.total_capex,
        inp.financing.share_capital_keur,
        inp.financing.share_premium_keur,
    )
    return [
        (i, b.check_keur)
        for i, b in enumerate(bs)
        if abs(b.check_keur) >= TOLERANCE_KEUR
    ]


def test_tuho_balance_sheet_invariant():
    violations = _bs_violations("TUHO")
    if violations:
        max_gap = max(abs(v) for _, v in violations)
        pytest.fail(
            f"Balance sheet invariant A=L+E violated in {len(violations)} periods. "
            f"max |A−L−E| = {max_gap:.3f} kEUR. "
            f"First violation: period {violations[0][0]}, check_keur = {violations[0][1]:.3f}"
        )


def test_oborovo_balance_sheet_invariant():
    violations = _bs_violations("Oborovo")
    if violations:
        max_gap = max(abs(v) for _, v in violations)
        pytest.fail(
            f"Balance sheet invariant A=L+E violated in {len(violations)} periods. "
            f"max |A−L−E| = {max_gap:.3f} kEUR. "
            f"First violation: period {violations[0][0]}, check_keur = {violations[0][1]:.3f}"
        )
