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
0  All selected baselines pass TAX_CFADS_V1.
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
import sys
import traceback
from pathlib import Path
from typing import Any

from finco_parity.canonical import canonical_json_bytes
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

_PROFILE = ComparisonProfile.TAX_CFADS_V1
_ALL_BASELINE_IDS = ("tuho", "oborovo", "generic_solar", "generic_wind")


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

    args = parser.parse_args(argv)
    verify_legacy = True
    selected_ids = list(_ALL_BASELINE_IDS) if args.all else [args.baseline]

    if not args.quiet:
        print(f"Phase 2B TAX_CFADS_V1 parity check — engine: {ENGINE_VERSION}")
        print(f"Profile: {_PROFILE.value}")
        print(f"Baselines: {', '.join(selected_ids)}")
        print()

    try:
        aggregate = compare_candidate_provider(
            FinancialEngineTaxCfadsCandidateProvider(),
            baseline_ids=selected_ids,
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

    if not args.quiet:
        for result in aggregate.baseline_results:
            status_str = "PASS" if result.status == BaselineRunStatus.PASS else f"FAIL ({result.status.value})"
            print(f"  [{result.baseline_id}] TAX_CFADS_V1 {status_str}", flush=True)
            if result.differences:
                for d in result.differences[:5]:
                    print(f"    {d.path}: {d.kind.value}", flush=True)
                if result.difference_count > 5:
                    print(f"    ... and {result.difference_count - 5} more", flush=True)
        print()
        if aggregate.overall_status == BaselineRunStatus.PASS:
            print(f"Overall: PASS ({len(aggregate.selected_baselines)} baseline(s))")
            print()
            print(TAX_CFADS_V1_PASS_WORDING)
        else:
            code = exit_code_for_aggregate(aggregate)
            print(f"Overall: FAIL (exit {code})")

    json_records: list[dict[str, Any]] = [
        {
            "baseline_id": r.baseline_id,
            "profile": _PROFILE.value,
            "engine_designation": ENGINE_VERSION,
            "status": r.status.value,
            "differences": [d.to_dict() for d in r.differences],
        }
        for r in aggregate.baseline_results
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
            _write_report(args.text_report, _format_text_report(aggregate))
        except OSError as exc:
            print(f"Cannot write text report: {exc.strerror}", file=sys.stderr)
            return 1

    return exit_code_for_aggregate(aggregate)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
