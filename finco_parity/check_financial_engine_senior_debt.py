"""
finco_parity.check_financial_engine_senior_debt — Phase 2C senior debt parity CLI.

Usage::

    python -m finco_parity.check_financial_engine_senior_debt --baseline oborovo --check

Exit codes
----------
0   All selected baselines pass.
1   Execution error (unexpected exception).
2   Unknown baseline ID or invalid CLI args.
9   One or more baselines INPUT_SOURCE_BLOCKED.

Import boundary
---------------
This module may only import from:
  - Python standard library
  - finco_parity.*
It must NOT import from app.*, domain.*, finco_core.*, main_web, main_api.
"""
from __future__ import annotations

import argparse
import sys
import traceback

from financial_engine.version import ENGINE_VERSION

_ALL_BASELINE_IDS = ("tuho", "oborovo", "generic_solar", "generic_wind")
_STATUS_BLOCKED = "INPUT_SOURCE_BLOCKED"


def _check_blocked_baselines(baseline_ids: list[str]) -> dict[str, str]:
    """Return {baseline_id: block_reason} for baselines that cannot be run.

    A blocked baseline (e.g. TUHO opening-loss unresolved) produces
    INPUT_SOURCE_BLOCKED rather than a comparison result.
    """
    from finco_parity.tax_reference_inputs import (
        TuhoOpeningLossVintageUnresolved,
        build_opening_loss_vintages,
    )
    blocked: dict[str, str] = {}
    for bid in baseline_ids:
        try:
            build_opening_loss_vintages(bid)
        except TuhoOpeningLossVintageUnresolved as exc:
            blocked[bid] = str(exc)
    return blocked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 2C clean-engine senior debt parity check."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Check all baselines.")
    group.add_argument(
        "--baseline",
        choices=list(_ALL_BASELINE_IDS),
        help="Check a single baseline.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero on any blocked baseline.",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output.")

    args = parser.parse_args(argv)
    selected_ids = list(_ALL_BASELINE_IDS) if args.all else [args.baseline]

    if not args.quiet:
        print(f"Phase 2C SENIOR_DEBT_V1 parity check — engine: {ENGINE_VERSION}")
        print(f"Baselines: {', '.join(selected_ids)}")
        print()

    try:
        blocked = _check_blocked_baselines(selected_ids)
    except Exception as exc:
        print(f"UNEXPECTED ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1

    if not args.quiet:
        for bid, reason in blocked.items():
            print(f"  [{bid}] {_STATUS_BLOCKED}: {reason[:120]}")
        for bid in selected_ids:
            if bid not in blocked:
                print(f"  [{bid}] RUNNABLE")
        print()

    if args.check and blocked:
        print(
            f"CHECK FAILED: {len(blocked)} baseline(s) INPUT_SOURCE_BLOCKED: "
            f"{', '.join(blocked)}",
            file=sys.stderr,
        )
        return 9

    return 0


if __name__ == "__main__":
    sys.exit(main())
