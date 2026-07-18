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
import json
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

_CORRECTIONS_PATH = Path(__file__).parent / "corrections" / "tax_cfads_v1_exact.json"

# Comparison statuses per the correction-aware contract.
_STATUS_IDENTICAL = "IDENTICAL"
_STATUS_APPROVED = "APPROVED_FINANCIAL_CORRECTION"
_STATUS_UNEXPLAINED = "UNEXPLAINED_DRIFT"


def _load_corrections() -> dict[str, set[str]]:
    """Load approved corrections ledger.

    Returns {baseline_id: set of approved field_paths}.
    Returns empty dict if the corrections file does not exist.
    """
    if not _CORRECTIONS_PATH.exists():
        return {}
    with open(_CORRECTIONS_PATH) as f:
        ledger = json.load(f)
    approved: dict[str, set[str]] = {}
    for record in ledger.get("corrections", []):
        bid = record["baseline_id"]
        if bid not in approved:
            approved[bid] = set()
        approved[bid].add(record["field_path"])
    return approved


def _correction_status_for_baseline(
    baseline_id: str,
    differences: list,
    approved: dict[str, set[str]],
) -> tuple[str, list, list]:
    """Classify each difference as APPROVED or UNEXPLAINED.

    Returns (overall_status, approved_diffs, unexplained_diffs).
    """
    if not differences:
        return _STATUS_IDENTICAL, [], []

    approved_paths = approved.get(baseline_id, set())
    unexplained = [d for d in differences if d.path not in approved_paths]
    approved_list = [d for d in differences if d.path in approved_paths]

    overall = _STATUS_UNEXPLAINED if unexplained else _STATUS_APPROVED
    return overall, approved_list, unexplained

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

    # Load corrections ledger for correction-aware status classification.
    approved = _load_corrections()
    if not args.quiet and approved:
        n_total = sum(len(v) for v in approved.values())
        print(f"Corrections ledger: {n_total} approved field paths across "
              f"{len(approved)} baseline(s)", flush=True)
    elif not args.quiet:
        print("Corrections ledger: not found — all differences will be UNEXPLAINED_DRIFT",
              flush=True)
    if not args.quiet:
        print()

    # Per-baseline correction-aware classification.
    any_unexplained = False
    baseline_correction_statuses: list[dict[str, Any]] = []
    for result in aggregate.baseline_results:
        c_status, approved_diffs, unexplained = _correction_status_for_baseline(
            result.baseline_id, result.differences, approved
        )
        if unexplained:
            any_unexplained = True
        baseline_correction_statuses.append({
            "baseline_id": result.baseline_id,
            "legacy_status": result.status.value,
            "correction_status": c_status,
            "n_approved": len(approved_diffs),
            "n_unexplained": len(unexplained),
            "unexplained_diffs": unexplained,
        })

        if not args.quiet:
            label = (
                f"{c_status} ({len(approved_diffs)} approved)"
                if c_status == _STATUS_APPROVED
                else f"{c_status} ({len(unexplained)} unexplained)"
                if c_status == _STATUS_UNEXPLAINED
                else c_status
            )
            print(f"  [{result.baseline_id}] TAX_CFADS_V1 {label}", flush=True)
            # Show unexplained diffs (worst first)
            if unexplained:
                for d in unexplained[:5]:
                    print(f"    UNEXPLAINED: {d.path}: {d.kind.value}", flush=True)
                if len(unexplained) > 5:
                    print(f"    ... and {len(unexplained) - 5} more unexplained", flush=True)

    if not args.quiet:
        print()
        if not any_unexplained:
            print("Overall: PASS (0 UNEXPLAINED_DRIFT)")
            print()
            print(TAX_CFADS_V1_PASS_WORDING)
        else:
            total_unexp = sum(s["n_unexplained"] for s in baseline_correction_statuses)
            print(f"Overall: FAIL ({total_unexp} UNEXPLAINED_DRIFT across all baselines)")

    json_records: list[dict[str, Any]] = [
        {
            "baseline_id": s["baseline_id"],
            "profile": _PROFILE.value,
            "engine_designation": ENGINE_VERSION,
            "correction_status": s["correction_status"],
            "n_approved_corrections": s["n_approved"],
            "n_unexplained_drift": s["n_unexplained"],
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
            _write_report(args.text_report, _format_text_report(aggregate))
        except OSError as exc:
            print(f"Cannot write text report: {exc.strerror}", file=sys.stderr)
            return 1

    # Exit 0 if all differences are IDENTICAL or APPROVED_FINANCIAL_CORRECTION.
    # Exit 3 only if any UNEXPLAINED_DRIFT exists.
    if any_unexplained:
        return 3
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
