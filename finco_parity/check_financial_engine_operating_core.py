"""
finco_parity.check_financial_engine_operating_core — Phase 2A clean-engine parity CLI.

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
1  Execution error (unexpected exception).
2  Unknown baseline ID or invalid CLI args.
3  Candidate payload drift (PAYLOAD_DRIFT).
4  Manifest / baseline integrity failure.
5  Environment mismatch.
6  Candidate missing or invalid.
7  Identity or schema mismatch.
8  Live legacy drift (not checked in operating-core mode).

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
from finco_parity.comparison import (
    ComparisonResult,
    DriftKind,
    compare_snapshots,
    format_comparison_report,
)
from finco_parity.financial_engine_candidate import (
    CANDIDATE_RUN_PATH_ID,
    get_candidate_snapshot,
)
from finco_parity.manifest import (
    ManifestIntegrityError,
    load_validated_manifest_context,
    resolve_snapshot_path,
)
from finco_parity.profiles import (
    OPERATING_CORE_V1_PASS_WORDING,
    ComparisonProfile,
    project_for_profile,
)
from finco_parity.schema import SnapshotValidationError, validate_snapshot
from financial_engine.version import ENGINE_VERSION

_PROFILE = ComparisonProfile.OPERATING_CORE_V1
_ALL_BASELINE_IDS = ("tuho", "oborovo", "generic_solar", "generic_wind")


# ---------------------------------------------------------------------------
# Exit-code mapping (mirrors compare_candidate.py)
# ---------------------------------------------------------------------------

def _exit_code(drift_kind: DriftKind | None) -> int:
    if drift_kind is None or drift_kind == DriftKind.IDENTICAL:
        return 0
    return {
        DriftKind.VALUE_DRIFT: 3,
        DriftKind.AVAILABILITY_DRIFT: 3,
        DriftKind.STRUCTURAL_DRIFT: 3,
        DriftKind.PROVENANCE_DRIFT: 3,
        DriftKind.SCHEMA_DRIFT: 7,
    }.get(drift_kind, 3)


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

def _write_report(path: Path, content: bytes | str) -> str | None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return None
    except OSError as exc:
        return f"Cannot write report to {path}: {exc}"


def _format_text_report(
    baseline_id: str,
    result: ComparisonResult,
    candidate: dict[str, Any],
) -> str:
    lines = [
        f"=== OPERATING_CORE_V1 Report: {baseline_id} ===",
        f"Profile:     {_PROFILE.value}",
        f"Engine:      {ENGINE_VERSION}",
        f"Run path:    {CANDIDATE_RUN_PATH_ID}",
        f"Status:      {result.status.value}",
        f"Differences: {len(result.differences)}",
        "",
    ]
    if result.status == DriftKind.IDENTICAL:
        lines.append(OPERATING_CORE_V1_PASS_WORDING)
    else:
        lines.append(format_comparison_report(result))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Per-baseline run
# ---------------------------------------------------------------------------

def _run_one_baseline(
    baseline_id: str,
    *,
    committed_snapshot: dict[str, Any],
    quiet: bool,
) -> tuple[int, ComparisonResult | None, dict[str, Any] | None]:
    """Run OPERATING_CORE_V1 check for one baseline. Returns (exit_code, result, candidate)."""
    baseline_commit_sha: str = committed_snapshot.get("baseline_commit_sha", "")

    if not quiet:
        print(f"  [{baseline_id}] generating Phase 2A candidate ...", flush=True)

    try:
        candidate = get_candidate_snapshot(
            baseline_id,
            baseline_commit_sha=baseline_commit_sha,
        )
    except Exception as exc:
        print(
            f"  [{baseline_id}] CANDIDATE ERROR: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 6, None, None

    # Project both snapshots to OPERATING_CORE_V1 paths.
    b_proj = project_for_profile(committed_snapshot, _PROFILE)
    c_proj = project_for_profile(candidate, _PROFILE)

    result = compare_snapshots(b_proj, c_proj, baseline_id=baseline_id)

    if not quiet:
        status_str = "PASS" if result.status == DriftKind.IDENTICAL else f"FAIL ({result.status.value})"
        print(f"  [{baseline_id}] OPERATING_CORE_V1 {status_str}", flush=True)
        if result.differences and not quiet:
            for d in result.differences[:5]:
                print(f"    {d.path}: {d.kind.value}", flush=True)
            if len(result.differences) > 5:
                print(f"    ... and {len(result.differences) - 5} more", flush=True)

    exit_code = _exit_code(result.status if result.status != DriftKind.IDENTICAL else None)
    return exit_code, result, candidate


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

    overall_exit = 0
    json_records: list[dict[str, Any]] = []
    text_lines: list[str] = []

    for baseline_id in selected:
        try:
            entry = ctx.get_entry(baseline_id)
        except KeyError:
            print(f"  [{baseline_id}] UNKNOWN BASELINE", file=sys.stderr)
            overall_exit = max(overall_exit, 2)
            continue

        snapshot_path = resolve_snapshot_path(entry)
        try:
            committed_bytes = snapshot_path.read_bytes()
            committed = json.loads(committed_bytes)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"  [{baseline_id}] Cannot read committed snapshot: {exc}", file=sys.stderr)
            overall_exit = max(overall_exit, 4)
            continue

        code, result, candidate = _run_one_baseline(
            baseline_id,
            committed_snapshot=committed,
            quiet=args.quiet,
        )

        if check and code != 0:
            overall_exit = max(overall_exit, code)

        if result is not None:
            json_records.append({
                "baseline_id": baseline_id,
                "profile": _PROFILE.value,
                "engine_designation": ENGINE_VERSION,
                "status": result.status.value,
                "differences": [d.to_dict() for d in result.differences],
            })
            text_lines.append(_format_text_report(baseline_id, result, candidate or {}))
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

    # Optional report files
    if args.json_report and json_records:
        err = _write_report(
            args.json_report,
            canonical_json_bytes({"results": json_records}),
        )
        if err:
            print(err, file=sys.stderr)

    if args.text_report and text_lines:
        err = _write_report(args.text_report, "\n".join(text_lines))
        if err:
            print(err, file=sys.stderr)

    return overall_exit


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
