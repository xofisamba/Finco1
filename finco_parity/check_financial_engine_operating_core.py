"""
finco_parity.check_financial_engine_operating_core — Phase 2A clean-engine parity CLI.

Thin wrapper around Phase 1C dual-run orchestration with OPERATING_CORE_V1 profile.
Uses FinancialEngineCandidateProvider (exactly once per baseline) via run_candidate_provider.

Usage::

    python -m finco_parity.check_financial_engine_operating_core --all --check

    python -m finco_parity.check_financial_engine_operating_core \\
        --baseline tuho \\
        [--check] \\
        [--json-report PATH] \\
        [--text-report PATH] \\
        [--quiet]

Exit codes
----------
0  All selected baselines pass OPERATING_CORE_V1.
1  Execution error (unexpected exception or report write failure).
2  Unknown baseline ID or invalid CLI args.
3  Candidate payload drift (PAYLOAD_DRIFT).
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
from typing import Any

from finco_parity.canonical import canonical_json_bytes
from finco_parity.comparison import format_comparison_report
from finco_parity.dual_run import (
    AggregateRunResult,
    BaselineRunResult,
    BaselineRunStatus,
    run_candidate_provider,
    _run_candidate_with_context,
)
from finco_parity.financial_engine_candidate import (
    CANDIDATE_RUN_PATH_ID,
    FinancialEngineCandidateProvider,
)
from finco_parity.manifest import (
    ManifestIntegrityError,
    load_validated_manifest_context,
)
from finco_parity.profiles import (
    OPERATING_CORE_V1_PASS_WORDING,
    ComparisonProfile,
)
from financial_engine.version import ENGINE_VERSION

_PROFILE = ComparisonProfile.OPERATING_CORE_V1
_ALL_BASELINE_IDS = ("tuho", "oborovo", "generic_solar", "generic_wind")


# ---------------------------------------------------------------------------
# Exit-code mapping (matches compare_candidate.py)
# ---------------------------------------------------------------------------

_STATUS_EXIT_CODE: dict[BaselineRunStatus, int] = {
    BaselineRunStatus.PASS: 0,
    BaselineRunStatus.EXECUTION_ERROR: 1,
    BaselineRunStatus.UNKNOWN_BASELINE: 2,
    BaselineRunStatus.PAYLOAD_DRIFT: 3,
    BaselineRunStatus.MANIFEST_INTEGRITY_FAILURE: 4,
    BaselineRunStatus.ENVIRONMENT_MISMATCH: 5,
    BaselineRunStatus.CANDIDATE_MISSING: 6,
    BaselineRunStatus.CANDIDATE_INVALID: 6,
    BaselineRunStatus.IDENTITY_MISMATCH: 7,
    BaselineRunStatus.SCHEMA_MISMATCH: 7,
    BaselineRunStatus.LEGACY_DRIFT: 8,
}


def _exit_code(result: BaselineRunResult) -> int:
    return _STATUS_EXIT_CODE.get(result.status, 1)


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

def _write_report(path: Path, content: bytes | str) -> None:
    """Write report to path. Raises OSError on failure (caller exits 1)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def _format_text_report(baseline_id: str, result: BaselineRunResult) -> str:
    lines = [
        f"=== OPERATING_CORE_V1 Report: {baseline_id} ===",
        f"Profile:     {_PROFILE.value}",
        f"Engine:      {ENGINE_VERSION}",
        f"Run path:    {CANDIDATE_RUN_PATH_ID}",
        f"Status:      {result.status.value}",
        f"Differences: {result.difference_count}",
        "",
    ]
    if result.status == BaselineRunStatus.PASS:
        lines.append(OPERATING_CORE_V1_PASS_WORDING)
    elif result.error_message:
        lines.append(f"Error: {result.error_message}")
    elif result.differences:
        # Format using comparison report helper.
        from finco_parity.comparison import ComparisonResult, DriftKind, Difference
        # Build a minimal ComparisonResult from the BaselineRunResult differences.
        fake_result = ComparisonResult(
            status=DriftKind(result.comparison_status or "VALUE_DRIFT"),
            differences=result.differences,
        )
        lines.append(format_comparison_report(fake_result))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 2A clean-engine OPERATING_CORE_V1 parity check."
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
        help="Exit non-zero on any drift (default when --all).",
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

    args = parser.parse_args(argv)
    check: bool = args.check or args.all

    selected = list(_ALL_BASELINE_IDS) if args.all else [args.baseline]

    if not args.quiet:
        print(f"Phase 2A OPERATING_CORE_V1 parity check — engine: {ENGINE_VERSION}")
        print(f"Profile: {_PROFILE.value}")
        print(f"Baselines: {', '.join(selected)}")
        print()

    try:
        ctx = load_validated_manifest_context()
    except ManifestIntegrityError as exc:
        print(f"MANIFEST INTEGRITY FAILURE: {exc}", file=sys.stderr)
        return 4
    except Exception as exc:
        print(f"UNEXPECTED ERROR loading manifest: {exc}", file=sys.stderr)
        return 1

    provider = FinancialEngineCandidateProvider()
    overall_exit = 0
    json_records: list[dict[str, Any]] = []
    text_lines: list[str] = []

    for baseline_id in selected:
        if baseline_id not in ctx.baseline_ids:
            print(f"  [{baseline_id}] UNKNOWN BASELINE", file=sys.stderr)
            overall_exit = max(overall_exit, 2)
            continue

        if not args.quiet:
            print(f"  [{baseline_id}] generating Phase 2A candidate ...", flush=True)

        # Provider is called exactly once per baseline by _run_candidate_with_context.
        result = _run_candidate_with_context(
            baseline_id,
            provider,
            ctx,
            verify_legacy=True,
            comparison_profile=_PROFILE,
        )

        if not args.quiet:
            status_str = "PASS" if result.status == BaselineRunStatus.PASS else f"FAIL ({result.status.value})"
            print(f"  [{baseline_id}] OPERATING_CORE_V1 {status_str}", flush=True)
            if result.differences:
                for d in result.differences[:5]:
                    print(f"    {d.path}: {d.kind.value}", flush=True)
                if result.difference_count > 5:
                    print(f"    ... and {result.difference_count - 5} more", flush=True)

        code = _exit_code(result)
        if check and code != 0:
            overall_exit = max(overall_exit, code)

        json_records.append({
            "baseline_id": baseline_id,
            "profile": _PROFILE.value,
            "engine_designation": ENGINE_VERSION,
            "status": result.status.value,
            "differences": [d.to_dict() for d in result.differences],
        })
        text_lines.append(_format_text_report(baseline_id, result))
        text_lines.append("")

    # Summary
    if not args.quiet:
        print()
        if overall_exit == 0:
            print(f"Overall: PASS ({len(selected)} baseline(s))")
            print()
            print(OPERATING_CORE_V1_PASS_WORDING)
        else:
            print(f"Overall: FAIL (exit {overall_exit})")

    # Optional report files — OSError → exit 1
    if args.json_report and json_records:
        try:
            _write_report(
                args.json_report,
                canonical_json_bytes({"results": json_records}),
            )
        except OSError as exc:
            print(f"Cannot write JSON report: {exc.strerror}", file=sys.stderr)
            return 1

    if args.text_report and text_lines:
        try:
            _write_report(args.text_report, "\n".join(text_lines))
        except OSError as exc:
            print(f"Cannot write text report: {exc.strerror}", file=sys.stderr)
            return 1

    return overall_exit


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
