"""
finco_parity.check_financial_engine_tax_cfads — Phase 2B tax+CFADS parity CLI.

Thin wrapper: parse args → instantiate FinancialEngineTaxCfadsCandidateProvider →
call compare_candidate_provider() → format AggregateRunResult → return exit code.

Usage::

    python -m finco_parity.check_financial_engine_tax_cfads --all --check

    python -m finco_parity.check_financial_engine_tax_cfads \\
        --baseline tuho \\
        [--check] \\
        [--json-report PATH] \\
        [--text-report PATH] \\
        [--quiet]

Exit codes
----------
0   All selected baselines pass TAX_CFADS_V1.
1   Execution error (unexpected exception or report write failure).
2   Unknown baseline ID or invalid CLI args.
3   UNEXPLAINED_DRIFT or stale correction records (--check mode only).
4   Manifest / baseline integrity failure.
5   Environment mismatch.
6   Candidate missing or invalid.
7   Identity or schema mismatch.
8   Live legacy drift.
9   One or more baselines INPUT_SOURCE_BLOCKED (--check mode; use --allow-input-source-blocked for diagnostic).
10  Approved corrections ledger missing or invalid — mandatory governance failure.

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
from pathlib import Path
from typing import Any

from finco_parity.canonical import canonical_json_bytes
from finco_parity.correction_matcher import (
    LedgerValidationError,
    MatchResult,
    load_and_validate_ledger,
    match_differences,
)
from finco_parity.dual_run import (
    AggregateRunResult,
    BaselineRunStatus,
    compare_candidate_provider,
    exit_code_for_aggregate,
)
from finco_parity.financial_engine_tax_cfads_candidate import (
    CANDIDATE_RUN_PATH_ID,
    FinancialEngineTaxCfadsCandidateProvider,
)
from finco_parity.manifest import ManifestIntegrityError
from finco_parity.profiles import (
    TAX_CFADS_V1_PASS_WORDING,
    ComparisonProfile,
)
from financial_engine.version import ENGINE_VERSION

_CORRECTIONS_PATH = Path(__file__).parent / "corrections" / "tax_cfads_v1_exact.json"

# Comparison statuses per the correction-aware contract.
_STATUS_IDENTICAL = "IDENTICAL"
_STATUS_APPROVED = "APPROVED_FINANCIAL_CORRECTION"
_STATUS_UNEXPLAINED = "UNEXPLAINED_DRIFT"

_PROFILE = ComparisonProfile.TAX_CFADS_V1
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


def _write_report(path: Path, content: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        text = content.rstrip("\n") + "\n"
        path.write_text(text, encoding="utf-8")


def _format_text_report(aggregate: AggregateRunResult) -> str:
    lines = [
        "=== TAX_CFADS_V1 Report ===",
        f"Profile:    {_PROFILE.value}",
        f"Engine:     {ENGINE_VERSION}",
        f"Run path:   {CANDIDATE_RUN_PATH_ID}",
        f"Status:     {aggregate.overall_status.value}",
        f"Selected:   {len(aggregate.selected_baselines)}",
        f"Passed:     {len(aggregate.passed_baselines)}",
        f"Failed:     {len(aggregate.failed_baselines)}",
        "",
    ]
    for result in aggregate.baseline_results:
        lines.append(f"  [{result.baseline_id}] {result.status.value} "
                     f"({result.difference_count} diffs)")
        if result.error_message:
            lines.append(f"    Error: {result.error_message}")
        for d in result.differences[:5]:
            lines.append(f"    {d.path}: {d.kind.value}")
        if result.difference_count > 5:
            lines.append(f"    ... and {result.difference_count - 5} more")
    lines.append("")
    if aggregate.overall_status == BaselineRunStatus.PASS:
        lines.append(TAX_CFADS_V1_PASS_WORDING)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 2B clean-engine TAX_CFADS_V1 parity check."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Check all four baselines.")
    group.add_argument(
        "--baseline",
        choices=list(_ALL_BASELINE_IDS),
        help="Check a single baseline.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero on any drift.",
    )
    parser.add_argument(
        "--json-report",
        type=Path,
        metavar="PATH",
        help="Write JSON comparison report to PATH.",
    )
    parser.add_argument(
        "--text-report",
        type=Path,
        metavar="PATH",
        help="Write text comparison report to PATH.",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output.")
    parser.add_argument(
        "--allow-input-source-blocked",
        action="store_true",
        help=(
            "Diagnostic flag: treat INPUT_SOURCE_BLOCKED baselines as non-fatal "
            "and exit 0 if all runnable baselines pass. "
            "NOT for CI use — CI step 13 must assert zero blocked baselines."
        ),
    )

    args = parser.parse_args(argv)
    verify_legacy = True
    selected_ids = list(_ALL_BASELINE_IDS) if args.all else [args.baseline]

    if not args.quiet:
        print(f"Phase 2B TAX_CFADS_V1 parity check — engine: {ENGINE_VERSION}")
        print(f"Profile: {_PROFILE.value}")
        print(f"Baselines: {', '.join(selected_ids)}")
        print()

    # Detect baselines blocked by unresolved input sources (e.g. TUHO opening loss).
    blocked_baselines = _check_blocked_baselines(selected_ids)
    runnable_ids = [bid for bid in selected_ids if bid not in blocked_baselines]

    if not args.quiet and blocked_baselines:
        for bid, reason in blocked_baselines.items():
            print(f"  [{bid}] {_STATUS_BLOCKED}: {reason[:120]}", flush=True)
        print()

    if runnable_ids:
        try:
            aggregate = compare_candidate_provider(
                FinancialEngineTaxCfadsCandidateProvider(),
                baseline_ids=runnable_ids,
                comparison_profile=_PROFILE,
                verify_legacy=verify_legacy,
            )
        except ManifestIntegrityError as exc:
            print(f"MANIFEST INTEGRITY FAILURE: {exc}", file=sys.stderr)
            return 4
        except ValueError as exc:
            print(f"UNKNOWN BASELINE: {exc}", file=sys.stderr)
            return 2
        except Exception as exc:
            print(f"UNEXPECTED ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
            traceback.print_exc()
            return 1
    else:
        # All selected baselines are blocked; nothing to compare.
        aggregate = None

    # Load corrections ledger (exact matching — all financially relevant fields).
    # A missing or invalid ledger is a hard governance failure (exit 10).
    try:
        ledger = load_and_validate_ledger(_CORRECTIONS_PATH)
        n_total = sum(len(v) for v in ledger.values())
        if not args.quiet:
            print(f"Corrections ledger: {n_total} approved records across "
                  f"{len(ledger)} baseline(s)", flush=True)
    except FileNotFoundError as exc:
        print(
            f"GOVERNANCE FAILURE: approved corrections ledger is mandatory and not found.\n"
            f"  {exc}",
            file=sys.stderr,
        )
        return 10
    except LedgerValidationError as exc:
        print(f"GOVERNANCE FAILURE: ledger validation failed:\n{exc}", file=sys.stderr)
        return 10
    if not args.quiet:
        print()

    # Per-baseline correction-aware classification.
    any_unexplained = False
    any_stale = False
    match_results: list[MatchResult] = []
    baseline_correction_statuses: list[dict[str, Any]] = []

    # Blocked baselines — report INPUT_SOURCE_BLOCKED (not a drift, not an error).
    for bid, reason in blocked_baselines.items():
        baseline_correction_statuses.append({
            "baseline_id": bid,
            "legacy_status": _STATUS_BLOCKED,
            "correction_status": _STATUS_BLOCKED,
            "n_approved": 0,
            "n_unexplained": 0,
            "n_stale": 0,
            "unexplained_diffs": [],
            "block_reason": reason[:120],
        })

    for result in (aggregate.baseline_results if aggregate is not None else []):
        mr = match_differences(result.baseline_id, result.differences, ledger)
        match_results.append(mr)
        if mr.unexplained:
            any_unexplained = True
        if mr.stale_records:
            any_stale = True
        c_status = mr.status
        baseline_correction_statuses.append({
            "baseline_id": result.baseline_id,
            "legacy_status": result.status.value,
            "correction_status": c_status,
            "n_approved": len(mr.approved),
            "n_unexplained": len(mr.unexplained),
            "n_stale": len(mr.stale_records),
            "unexplained_diffs": mr.unexplained,
        })

        if not args.quiet:
            if c_status == _STATUS_APPROVED:
                label = f"{c_status} ({len(mr.approved)} approved)"
            elif c_status == _STATUS_UNEXPLAINED:
                parts = []
                if mr.unexplained:
                    parts.append(f"{len(mr.unexplained)} unexplained")
                if mr.stale_records:
                    parts.append(f"{len(mr.stale_records)} stale")
                label = f"{c_status} ({', '.join(parts)})"
            else:
                label = c_status
            print(f"  [{result.baseline_id}] TAX_CFADS_V1 {label}", flush=True)
            for d in mr.unexplained[:5]:
                print(f"    UNEXPLAINED: {d.path}: {d.kind.value}", flush=True)
            if len(mr.unexplained) > 5:
                print(f"    ... and {len(mr.unexplained) - 5} more unexplained", flush=True)
            for rec in mr.stale_records[:3]:
                print(f"    STALE_RECORD: {rec.field_path} (correction_id={rec.correction_id})",
                      flush=True)
            if len(mr.stale_records) > 3:
                print(f"    ... and {len(mr.stale_records) - 3} more stale records", flush=True)

    n_selected = len(selected_ids)
    n_runnable = len(runnable_ids)
    n_identical = sum(1 for s in baseline_correction_statuses if s["correction_status"] == _STATUS_IDENTICAL)
    n_approved = sum(1 for s in baseline_correction_statuses if s["correction_status"] == _STATUS_APPROVED)
    n_blocked = len(blocked_baselines)
    n_unexplained = sum(s["n_unexplained"] for s in baseline_correction_statuses)
    n_stale = sum(s["n_stale"] for s in baseline_correction_statuses)

    if not args.quiet:
        print()
        print(f"Selected:              {n_selected}")
        print(f"Runnable:              {n_runnable}")
        print(f"Identical:             {n_identical}")
        print(f"Approved corrections:  {n_approved}")
        print(f"Input-source blocked:  {n_blocked}")
        print(f"Unexplained drift:     {n_unexplained}")
        print(f"Stale correction recs: {n_stale}")
        print()
        has_failures = any_unexplained or any_stale or (n_blocked > 0 and not args.allow_input_source_blocked)
        if not has_failures:
            if n_blocked > 0:
                # --allow-input-source-blocked in effect
                print(f"Overall: PASS (runnable baselines clean; {n_blocked} INPUT_SOURCE_BLOCKED)")
            else:
                print("Overall: PASS (0 UNEXPLAINED_DRIFT, 0 stale records)")
            print()
            print(TAX_CFADS_V1_PASS_WORDING)
        else:
            items = []
            if n_unexplained:
                items.append(f"{n_unexplained} UNEXPLAINED_DRIFT")
            if n_stale:
                items.append(f"{n_stale} stale correction records")
            if n_blocked and not args.allow_input_source_blocked:
                items.append(f"{n_blocked} INPUT_SOURCE_BLOCKED")
            print(f"Overall: FAIL ({'; '.join(items)})")

    json_records: list[dict[str, Any]] = [
        {
            "baseline_id": s["baseline_id"],
            "profile": _PROFILE.value,
            "engine_designation": ENGINE_VERSION,
            "correction_status": s["correction_status"],
            "n_approved_corrections": s["n_approved"],
            "n_unexplained_drift": s["n_unexplained"],
            "n_stale_records": s["n_stale"],
            "unexplained_differences": [d.to_dict() for d in s["unexplained_diffs"]],
        }
        for s in baseline_correction_statuses
    ]

    if args.json_report:
        try:
            _write_report(
                args.json_report,
                canonical_json_bytes({"results": json_records}),
            )
        except OSError as exc:
            print(f"Cannot write JSON report: {exc.strerror}", file=sys.stderr)
            return 1

    if args.text_report:
        try:
            if aggregate is not None:
                _write_report(args.text_report, _format_text_report(aggregate))
            else:
                lines = [
                    "=== TAX_CFADS_V1 Report ===",
                    f"Profile:    {_PROFILE.value}",
                    f"Engine:     {ENGINE_VERSION}",
                    "",
                ]
                for bid, reason in blocked_baselines.items():
                    lines.append(f"  [{bid}] {_STATUS_BLOCKED}: {reason[:120]}")
                lines.append("")
                _write_report(args.text_report, "\n".join(lines))
        except OSError as exc:
            print(f"Cannot write text report: {exc.strerror}", file=sys.stderr)
            return 1

    # Exit codes:
    #  10 — ledger missing or invalid (always; returned above before reaching here)
    #   3 — UNEXPLAINED_DRIFT or stale correction records (--check mode)
    #   9 — INPUT_SOURCE_BLOCKED and --allow-input-source-blocked not set (--check mode)
    #   0 — clean (or informational run without --check)
    if args.check:
        if any_unexplained or any_stale:
            return 3
        if n_blocked > 0 and not args.allow_input_source_blocked:
            return 9
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
