"""
finco_parity.legacy_snapshot — Offline CLI runner for legacy-engine snapshots.

Captures one deterministic snapshot per baseline project by executing the
current legacy waterfall engine through its canonical UI-runner path, then
normalizing and validating the output.

Usage
-----
Single baseline::

    python -m finco_parity.legacy_snapshot --baseline tuho --output /tmp/tuho.json

All baselines::

    python -m finco_parity.legacy_snapshot --all --output-dir /tmp/finco-snapshots

Options
-------
--baseline BASELINE_ID   One of: tuho, oborovo, generic_solar, generic_wind
--all                    Capture all four baselines
--output PATH            Output file for single-baseline mode
--output-dir DIR         Output directory for --all mode (files named <id>.json)
--commit-sha SHA         Explicit git SHA (default: auto-detected from .git/HEAD)
--pretty                 Pretty-print JSON output (indent=2)
--quiet                  Suppress progress messages

Import boundary
---------------
This module may import from:
  - Python standard library
  - finco_parity.*
  - app.* and domain.* (runtime engine — imports deferred into functions)
It must NOT be imported by production code.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import textwrap
import traceback
from pathlib import Path
from typing import Any

from finco_parity.schema import validate_snapshot, SnapshotValidationError, UNAVAILABLE
from finco_parity.normalization import normalize_snapshot, NormalizationError


# ---------------------------------------------------------------------------
# Baseline registry
# ---------------------------------------------------------------------------

ENGINE_DESIGNATION = "legacy_waterfall_v3"
RUN_PATH_ID = "ui_runner.run_demo_project"

# Maps baseline_id → (project_type key used in run_demo_project, factory function name)
_BASELINE_REGISTRY: dict[str, dict[str, str]] = {
    "tuho": {
        "project_type": "TUHO",
        "input_source_id": "project_factories.create_default_tuho_wind1",
        "display_name": "TUHO Wind 1",
    },
    "oborovo": {
        "project_type": "Oborovo",
        "input_source_id": "project_factories.create_default_oborovo",
        "display_name": "Oborovo Solar PV",
    },
    "generic_solar": {
        "project_type": "Test 1",
        "input_source_id": "project_factories.create_default_solar_project",
        "display_name": "Generic Solar (Test 1)",
    },
    "generic_wind": {
        "project_type": "Test 2",
        "input_source_id": "project_factories.create_default_wind_project",
        "display_name": "Generic Wind (Test 2)",
    },
}

ALL_BASELINE_IDS = list(_BASELINE_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Git SHA detection
# ---------------------------------------------------------------------------

def _detect_commit_sha() -> str:
    """Return the current HEAD SHA from the repository, or 'unknown'."""
    try:
        # Try via subprocess first (most accurate)
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            sha = result.stdout.strip()
            if sha:
                return sha
    except Exception:
        pass

    # Fallback: read .git/HEAD directly
    try:
        repo_root = Path(__file__).parent.parent
        head_path = repo_root / ".git" / "HEAD"
        if head_path.exists():
            ref = head_path.read_text().strip()
            if ref.startswith("ref: "):
                ref_path = repo_root / ".git" / ref[5:]
                if ref_path.exists():
                    return ref_path.read_text().strip()
            # Detached HEAD — ref is the SHA itself
            if len(ref) >= 40:
                return ref
    except Exception:
        pass

    return "unknown"


# ---------------------------------------------------------------------------
# Engine runner
# ---------------------------------------------------------------------------

def _run_engine(project_type: str) -> tuple[Any, Any, list[str]]:
    """Run the legacy engine for a given project_type and return
    (waterfall_result, financial_statements_payload, warnings).

    Deferred import keeps the production module boundary clean —
    this module is test-only and must not be imported by production code.
    """
    # Defer all production imports to runtime.  run_project is intentionally NOT
    # imported here — this runner captures via ui_runner only (legacy calc path).
    from app.ui_runner import run_demo_project  # type: ignore[import]

    warnings: list[str] = []

    # run_demo_project executes: factory → WaterfallRunner → run_waterfall_v3_core.
    # This is the legacy calculation capture path, not the full production Run path.
    # The production Run path additionally executes: run_project serializers,
    # persistence, sessionStorage, and Workbook V2 hydration.
    demo_result = run_demo_project(project_type)

    if demo_result is None:
        raise RuntimeError(f"run_demo_project({project_type!r}) returned None")

    # Extract the WaterfallResult from DemoResult.
    # DemoResult.result is the primary attribute per app/ui_runner.py.
    waterfall_result = getattr(demo_result, "result", None)
    if waterfall_result is None:
        raise RuntimeError(
            f"DemoResult.result is None for {project_type!r}. "
            f"Engine may have errored. Available attrs: "
            f"{[a for a in dir(demo_result) if not a.startswith('_')]}"
        )

    # Attempt to extract financial statements payload using the same assembly
    # function as the production runner.
    fs_payload = UNAVAILABLE
    try:
        from domain.financial_statements.assembly import (  # type: ignore[import]
            assemble_financial_statements,
        )
        fs_payload = assemble_financial_statements(waterfall_result)
    except Exception as exc:
        # Record failure type only — no absolute paths or tracebacks in warnings.
        warnings.append(
            f"financial_statements unavailable: {type(exc).__name__}"
        )

    # Collect any engine warnings from DemoResult.
    for attr in ("messages", "warnings", "engine_messages"):
        msgs = getattr(demo_result, attr, None)
        if msgs:
            for m in msgs:
                s = str(m)
                warnings.append(s)

    return waterfall_result, fs_payload, warnings


# ---------------------------------------------------------------------------
# Snapshot capture
# ---------------------------------------------------------------------------

def capture_snapshot(
    baseline_id: str,
    *,
    commit_sha: str | None = None,
    verbose: bool = True,
) -> dict[str, Any]:
    """Capture, normalize, and validate a snapshot for one baseline.

    Returns the validated snapshot dict.
    Raises RuntimeError, NormalizationError, or SnapshotValidationError on failure.
    """
    if baseline_id not in _BASELINE_REGISTRY:
        raise ValueError(
            f"Unknown baseline_id {baseline_id!r}. "
            f"Valid values: {sorted(_BASELINE_REGISTRY)}"
        )

    reg = _BASELINE_REGISTRY[baseline_id]
    project_type = reg["project_type"]
    input_source_id = reg["input_source_id"]

    if commit_sha is None:
        commit_sha = _detect_commit_sha()

    if verbose:
        print(f"  running engine for {reg['display_name']} ({project_type!r}) …", flush=True)

    waterfall_result, fs_payload, engine_warnings = _run_engine(project_type)

    if verbose and engine_warnings:
        for w in engine_warnings:
            print(f"  WARN: {w}", flush=True)

    unavailable_sections: list[str] = []
    if fs_payload is UNAVAILABLE:
        unavailable_sections.append("financial_statements")

    if verbose:
        print("  normalizing …", flush=True)

    snapshot = normalize_snapshot(
        waterfall_result,
        baseline_id=baseline_id,
        engine_designation=ENGINE_DESIGNATION,
        baseline_commit_sha=commit_sha,
        run_path_id=RUN_PATH_ID,
        input_source_id=input_source_id,
        warnings=engine_warnings,
        unavailable_sections=unavailable_sections,
        financial_statements_payload=fs_payload,
    )

    if verbose:
        print("  validating schema …", flush=True)

    validate_snapshot(snapshot)

    return snapshot


# ---------------------------------------------------------------------------
# JSON serialization
# ---------------------------------------------------------------------------

def _serialize_snapshot(snapshot: dict[str, Any], *, pretty: bool = False) -> str:
    """Serialize snapshot to deterministic UTF-8 JSON string.

    allow_nan=False enforces that no NaN or infinity survived normalization.
    """
    indent = 2 if pretty else None
    return json.dumps(
        snapshot, sort_keys=True, indent=indent, ensure_ascii=False, allow_nan=False
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m finco_parity.legacy_snapshot",
        description=textwrap.dedent("""\
            Capture legacy-engine characterization snapshots for baseline projects.

            Examples:
              python -m finco_parity.legacy_snapshot --baseline tuho --output /tmp/tuho.json
              python -m finco_parity.legacy_snapshot --all --output-dir /tmp/finco-snapshots
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--baseline",
        metavar="BASELINE_ID",
        choices=sorted(_BASELINE_REGISTRY),
        help=f"Baseline to capture. One of: {', '.join(sorted(_BASELINE_REGISTRY))}",
    )
    mode.add_argument(
        "--all",
        action="store_true",
        dest="capture_all",
        help="Capture all four baselines (requires --output-dir)",
    )
    p.add_argument(
        "--output",
        metavar="PATH",
        help="Output file path (required with --baseline)",
    )
    p.add_argument(
        "--output-dir",
        metavar="DIR",
        help="Output directory (required with --all; files named <baseline_id>.json)",
    )
    p.add_argument(
        "--commit-sha",
        metavar="SHA",
        help="Explicit git commit SHA (default: auto-detected from .git/HEAD)",
    )
    p.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output (indent=2)",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages",
    )
    return p


def _write_snapshot(snapshot: dict[str, Any], path: Path, *, pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _serialize_snapshot(snapshot, pretty=pretty)
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    verbose = not args.quiet
    commit_sha = args.commit_sha  # None = auto-detect inside capture_snapshot

    if args.capture_all:
        # --all requires --output-dir
        if not args.output_dir:
            parser.error("--all requires --output-dir")
        output_dir = Path(args.output_dir)

        failures: list[str] = []
        for baseline_id in ALL_BASELINE_IDS:
            if verbose:
                print(f"\ncapturing {baseline_id} …", flush=True)
            try:
                snapshot = capture_snapshot(
                    baseline_id,
                    commit_sha=commit_sha,
                    verbose=verbose,
                )
                dest = output_dir / f"{baseline_id}.json"
                _write_snapshot(snapshot, dest, pretty=args.pretty)
                if verbose:
                    period_count = len(snapshot.get("period_grid", []))
                    print(f"  written → {dest}  ({period_count} periods)", flush=True)
            except Exception as exc:
                msg = f"{baseline_id}: {type(exc).__name__}: {exc}"
                failures.append(msg)
                print(f"  ERROR: {msg}", file=sys.stderr, flush=True)
                if verbose:
                    traceback.print_exc()

        if failures:
            print(
                f"\n{len(failures)}/{len(ALL_BASELINE_IDS)} baseline(s) failed.",
                file=sys.stderr,
            )
            return 1

        if verbose:
            print(f"\nAll {len(ALL_BASELINE_IDS)} baselines captured successfully.", flush=True)
        return 0

    else:
        # Single baseline
        if not args.output:
            parser.error("--baseline requires --output")
        output_path = Path(args.output)

        if verbose:
            print(f"capturing {args.baseline} …", flush=True)
        try:
            snapshot = capture_snapshot(
                args.baseline,
                commit_sha=commit_sha,
                verbose=verbose,
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        except (NormalizationError, SnapshotValidationError) as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 3
        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
            if verbose:
                traceback.print_exc()
            return 1

        _write_snapshot(snapshot, output_path, pretty=args.pretty)
        if verbose:
            period_count = len(snapshot.get("period_grid", []))
            print(f"written → {output_path}  ({period_count} periods)", flush=True)
        return 0


if __name__ == "__main__":
    sys.exit(main())
