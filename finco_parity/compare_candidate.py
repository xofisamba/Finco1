"""
finco_parity.compare_candidate — CLI for candidate vs. baseline comparison.

Usage::

    python -m finco_parity.compare_candidate \\
        --candidate-dir /path/to/candidate/snapshots \\
        --all \\
        [--check] \\
        [--verify-legacy | --no-verify-legacy] \\
        [--json-report PATH] \\
        [--text-report PATH] \\
        [--max-diffs N] \\
        [--quiet]

Exit codes
----------
0  All baselines pass.
1  Execution error (engine failure, manifest error, unexpected exception).
2  Unknown baseline ID or invalid CLI args.
3  Candidate payload drift.
4  Manifest / baseline integrity failure.
5  Environment mismatch.
6  Candidate missing or invalid.
7  Identity or schema mismatch.
8  Live legacy drift.

Import boundary
---------------
This module may only import from:
  - Python standard library
  - finco_parity.*
It must NOT import from app.*, domain.*, finco_core.*, main_web, main_api.
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import NoReturn

from finco_parity.canonical import canonical_json_bytes
from finco_parity.comparison import format_comparison_report, ComparisonResult, DriftKind
from finco_parity.dual_run import (
    AggregateRunResult,
    BaselineRunResult,
    BaselineRunStatus,
    compare_candidate_directory,
)
from finco_parity.manifest import manifest_baseline_ids, ManifestIntegrityError


# ---------------------------------------------------------------------------
# Exit code mapping
# ---------------------------------------------------------------------------

_STATUS_EXIT_CODE: dict[BaselineRunStatus, int] = {
    BaselineRunStatus.PASS: 0,
    BaselineRunStatus.EXECUTION_ERROR: 1,
    BaselineRunStatus.ENVIRONMENT_MISMATCH: 5,
    BaselineRunStatus.PAYLOAD_DRIFT: 3,
    BaselineRunStatus.LEGACY_DRIFT: 8,
    BaselineRunStatus.CANDIDATE_MISSING: 6,
    BaselineRunStatus.CANDIDATE_INVALID: 6,
    BaselineRunStatus.IDENTITY_MISMATCH: 7,
    BaselineRunStatus.SCHEMA_MISMATCH: 7,
}


def _exit_code_for_aggregate(result: AggregateRunResult) -> int:
    """Return the most-severe exit code across all baseline results."""
    if result.overall_status == BaselineRunStatus.PASS:
        return 0
    # Return the highest (most-severe) exit code among failed baselines.
    max_code = 0
    for r in result.baseline_results:
        code = _STATUS_EXIT_CODE.get(r.status, 1)
        if code > max_code:
            max_code = code
    return max_code


# ---------------------------------------------------------------------------
# Report formatters
# ---------------------------------------------------------------------------

def _format_text_report(result: AggregateRunResult, *, max_diffs: int = 50) -> str:
    """Produce a deterministic, human-readable text report."""
    lines: list[str] = [
        "=" * 72,
        "Finco1 Parity — Candidate Comparison Report",
        "=" * 72,
        f"Overall status : {result.overall_status.value}",
        f"Selected       : {len(result.selected_baselines)} baseline(s)",
        f"Passed         : {len(result.passed_baselines)}",
        f"Failed         : {len(result.failed_baselines)}",
        "",
    ]

    for r in result.baseline_results:
        lines.append("-" * 72)
        lines.append(f"Baseline : {r.baseline_id}")
        lines.append(f"Status   : {r.status.value}")
        if r.error_message:
            lines.append(f"Error    : {r.error_message}")
        if r.legacy_engine_designation:
            lines.append(f"Legacy engine   : {r.legacy_engine_designation}")
        if r.candidate_engine_designation:
            lines.append(f"Candidate engine: {r.candidate_engine_designation}")
        if r.comparison_status:
            lines.append(f"Comparison      : {r.comparison_status}")
        lines.append(f"Differences     : {r.difference_count}")
        if r.legacy_warnings:
            lines.append(f"Legacy warnings : {list(r.legacy_warnings)!r}")
        if r.candidate_warnings:
            lines.append(f"Candidate warnings: {list(r.candidate_warnings)!r}")
        if r.differences:
            lines.append("")
            # Build a minimal ComparisonResult-like display.
            shown = r.differences[:max_diffs]
            for i, diff in enumerate(shown, 1):
                lines.append(f"  {i}. {diff.path}")
                lines.append(f"     kind     : {diff.kind.value}")
                lines.append(f"     baseline : {diff.baseline_value!r}")
                lines.append(f"     candidate: {diff.current_value!r}")
                if diff.absolute_delta is not None:
                    lines.append(f"     abs delta: {diff.absolute_delta}")
                if diff.relative_delta is not None:
                    lines.append(f"     rel delta: {diff.relative_delta:.6%}")
                lines.append("")
            if len(r.differences) > max_diffs:
                lines.append(
                    f"  ... {len(r.differences) - max_diffs} additional differences not shown."
                )
        lines.append("")

    lines.append("=" * 72)
    return "\n".join(lines)


def _format_json_report(result: AggregateRunResult) -> bytes:
    """Produce canonical JSON report bytes."""
    return canonical_json_bytes(result.to_dict())


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m finco_parity.compare_candidate",
        description="Compare candidate snapshots against committed baselines.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--candidate-dir",
        metavar="DIR",
        required=True,
        help="Directory containing candidate snapshot files.",
    )

    # Mutually exclusive: --baseline-id or --all (at least one required).
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        "--baseline-id",
        metavar="ID",
        help="Compare a single baseline by ID.",
    )
    target_group.add_argument(
        "--all",
        action="store_true",
        default=False,
        help="Compare all baselines declared in the manifest.",
    )

    parser.add_argument(
        "--check",
        action="store_true",
        default=False,
        help=(
            "Zero-tolerance check mode: verify legacy, no repo writes, "
            "exit non-zero unless all pass."
        ),
    )

    verify_group = parser.add_mutually_exclusive_group()
    verify_group.add_argument(
        "--verify-legacy",
        dest="verify_legacy",
        action="store_true",
        default=True,
        help="Capture a fresh legacy snapshot and verify it matches the committed artifact (default).",
    )
    verify_group.add_argument(
        "--no-verify-legacy",
        dest="verify_legacy",
        action="store_false",
        help="Skip fresh legacy snapshot verification.",
    )

    parser.add_argument(
        "--json-report",
        metavar="PATH",
        help="Write a canonical JSON report to PATH.",
    )
    parser.add_argument(
        "--text-report",
        metavar="PATH",
        help="Write a text report to PATH.",
    )
    parser.add_argument(
        "--max-diffs",
        metavar="N",
        type=int,
        default=None,
        help="Maximum number of differences to report per baseline.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress progress output.",
    )
    return parser


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Run the compare_candidate CLI.  Returns an exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    candidate_dir = Path(args.candidate_dir)
    if not candidate_dir.is_dir():
        print(
            f"ERROR: --candidate-dir {candidate_dir!r} is not an existing directory.",
            file=sys.stderr,
        )
        return 2

    # Determine target baseline IDs.
    if args.all:
        try:
            baseline_ids = None  # means all
        except Exception as exc:
            print(f"ERROR: Failed to load manifest: {exc}", file=sys.stderr)
            return 4
    else:
        # Single baseline.
        try:
            all_ids = manifest_baseline_ids()
        except Exception as exc:
            print(f"ERROR: Failed to load manifest: {exc}", file=sys.stderr)
            return 4
        if args.baseline_id not in all_ids:
            print(
                f"ERROR: Unknown baseline_id {args.baseline_id!r}. "
                f"Valid IDs: {all_ids!r}",
                file=sys.stderr,
            )
            return 2
        baseline_ids = [args.baseline_id]

    # In --check mode, force verify_legacy=True.
    verify_legacy = args.verify_legacy
    if args.check:
        verify_legacy = True

    verbose = not args.quiet

    # Run comparison.
    try:
        result = compare_candidate_directory(
            candidate_dir,
            baseline_ids=baseline_ids,
            verify_legacy=verify_legacy,
            max_diffs=args.max_diffs,
            verbose=verbose,
        )
    except ValueError as exc:
        # Unknown baseline IDs surfaced here.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except ManifestIntegrityError as exc:
        print(f"ERROR: Manifest integrity failure: {exc}", file=sys.stderr)
        return 4
    except Exception as exc:
        print(f"ERROR: Unexpected error during comparison: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1

    # Write reports.
    if args.json_report:
        json_path = Path(args.json_report)
        json_bytes = _format_json_report(result)
        json_path.write_bytes(json_bytes)
        if verbose:
            print(f"JSON report written to {json_path}", file=sys.stderr)

    max_diffs_for_text = args.max_diffs if args.max_diffs is not None else 50
    text_report = _format_text_report(result, max_diffs=max_diffs_for_text)

    if args.text_report:
        text_path = Path(args.text_report)
        text_path.write_text(text_report, encoding="utf-8")
        if verbose:
            print(f"Text report written to {text_path}", file=sys.stderr)

    if not args.quiet:
        print(text_report)

    return _exit_code_for_aggregate(result)


if __name__ == "__main__":
    sys.exit(main())
