"""
finco_parity.generate_baselines — Deterministic baseline generation CLI.

Generates canonical snapshot JSON artifacts for every Phase 1A manifest entry,
or checks that committed artifacts match a fresh generation.

Usage
-----
Regenerate all artifacts into the canonical repository location::

    python -m finco_parity.generate_baselines

Generate one baseline::

    python -m finco_parity.generate_baselines --baseline-id tuho

Generate into a separate directory (does not modify committed artifacts)::

    python -m finco_parity.generate_baselines --output-dir /tmp/snapshots

Check mode (no file writes — fails on any drift)::

    python -m finco_parity.generate_baselines --check

Exit codes
----------
0  All baselines match (check mode) or written successfully (default mode).
1  Generation, normalization, or validation failure.
2  Unknown baseline ID.
3  Drift detected in --check mode.
4  Manifest integrity failure.

Import boundary
---------------
This module may only import from:
  - Python standard library
  - finco_parity.*
Deferred imports of app.* / domain.* happen inside finco_parity.legacy_snapshot.
This module must NOT be imported by production code.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import textwrap
import traceback
from pathlib import Path
from typing import Any

from finco_parity.canonical import canonical_json_bytes, sha256_of_bytes, sha256_of_file, write_canonical_json
from finco_parity.legacy_snapshot import ALL_BASELINE_IDS, capture_snapshot
from finco_parity.manifest import (
    BASELINES_DIR,
    SNAPSHOTS_DIR,
    load_manifest,
    manifest_baseline_ids,
    snapshot_path_for,
    validate_manifest_integrity,
)
from finco_parity.schema import SnapshotValidationError
from finco_parity.normalization import NormalizationError


def _generate_one(
    baseline_id: str,
    output_dir: Path,
    *,
    verbose: bool = True,
    commit_sha: str | None = None,
) -> tuple[Path, bytes]:
    """Capture, validate and serialize one baseline into *output_dir*.

    Returns (dest_path, raw_bytes).
    """
    if verbose:
        print(f"  generating {baseline_id} …", flush=True)

    snapshot = capture_snapshot(baseline_id, commit_sha=commit_sha, verbose=verbose)

    raw = canonical_json_bytes(snapshot)
    dest = output_dir / f"{baseline_id}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)

    sha = sha256_of_bytes(raw)
    if verbose:
        periods = len(snapshot.get("period_grid", []))
        print(f"  written → {dest}  ({periods} periods, sha256={sha[:16]}…)", flush=True)

    return dest, raw


def cmd_generate(
    baseline_ids: list[str],
    output_dir: Path,
    *,
    verbose: bool = True,
    commit_sha: str | None = None,
) -> int:
    """Generate baselines into *output_dir*.  Returns exit code."""
    failures: list[str] = []
    for bid in baseline_ids:
        if verbose:
            print(f"\ncapturing {bid} …", flush=True)
        try:
            _generate_one(bid, output_dir, verbose=verbose, commit_sha=commit_sha)
        except Exception as exc:
            msg = f"{bid}: {type(exc).__name__}: {exc}"
            failures.append(msg)
            print(f"  ERROR: {msg}", file=sys.stderr, flush=True)
            if verbose:
                traceback.print_exc()

    if failures:
        print(f"\n{len(failures)}/{len(baseline_ids)} baseline(s) failed.", file=sys.stderr)
        return 1

    if verbose:
        print(f"\nAll {len(baseline_ids)} baseline(s) generated successfully.", flush=True)
    return 0


def cmd_check(
    baseline_ids: list[str],
    *,
    verbose: bool = True,
) -> int:
    """Check mode: generate fresh in temp dir and compare against committed artifacts.

    Returns 0 if all match, 3 if any drift, 1 if generation failure, 4 if manifest
    integrity failure.
    """
    # Validate manifest integrity first.
    try:
        validate_manifest_integrity()
    except Exception as exc:
        print(f"MANIFEST INTEGRITY FAILURE: {exc}", file=sys.stderr)
        return 4

    with tempfile.TemporaryDirectory(prefix="finco_parity_check_") as tmp:
        tmp_dir = Path(tmp)
        failures: list[str] = []
        drifts: list[str] = []

        for bid in baseline_ids:
            if verbose:
                print(f"\nchecking {bid} …", flush=True)

            committed_path = snapshot_path_for(bid)
            if not committed_path.exists():
                msg = f"{bid}: committed artifact missing: {committed_path}"
                drifts.append(msg)
                print(f"  DRIFT: {msg}", file=sys.stderr, flush=True)
                continue

            try:
                _, fresh_bytes = _generate_one(bid, tmp_dir, verbose=verbose)
            except Exception as exc:
                msg = f"{bid}: {type(exc).__name__}: {exc}"
                failures.append(msg)
                print(f"  ERROR: {msg}", file=sys.stderr, flush=True)
                if verbose:
                    traceback.print_exc()
                continue

            committed_bytes = committed_path.read_bytes()
            if fresh_bytes != committed_bytes:
                msg = (
                    f"{bid}: content differs from committed artifact "
                    f"(committed sha256={sha256_of_bytes(committed_bytes)[:16]}…, "
                    f"fresh sha256={sha256_of_bytes(fresh_bytes)[:16]}…)"
                )
                drifts.append(msg)
                print(f"  DRIFT: {msg}", file=sys.stderr, flush=True)
            else:
                if verbose:
                    print(f"  OK: {bid} matches committed artifact", flush=True)

        # Check for unreferenced artifacts.
        manifest = load_manifest()
        referenced = {
            snapshot_path_for(entry["baseline_id"])
            for entry in manifest["baselines"]
        }
        if SNAPSHOTS_DIR.exists():
            for p in SNAPSHOTS_DIR.glob("*.json"):
                if p not in referenced:
                    msg = f"unreferenced artifact: {p}"
                    drifts.append(msg)
                    print(f"  DRIFT: {msg}", file=sys.stderr, flush=True)

    if failures:
        print(f"\n{len(failures)} generation failure(s).", file=sys.stderr)
        return 1
    if drifts:
        print(f"\n{len(drifts)} drift(s) detected.", file=sys.stderr)
        return 3
    if verbose:
        print(f"\nAll {len(baseline_ids)} baseline(s) match committed artifacts.", flush=True)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m finco_parity.generate_baselines",
        description=textwrap.dedent("""\
            Generate or check legacy-engine characterization baseline snapshots.

            Examples:
              python -m finco_parity.generate_baselines
              python -m finco_parity.generate_baselines --baseline-id tuho
              python -m finco_parity.generate_baselines --output-dir /tmp/snapshots
              python -m finco_parity.generate_baselines --check
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--baseline-id",
        metavar="ID",
        choices=ALL_BASELINE_IDS,
        help=f"Generate only one baseline. One of: {', '.join(sorted(ALL_BASELINE_IDS))}",
    )
    p.add_argument(
        "--output-dir",
        metavar="DIR",
        help="Write artifacts here instead of the canonical repository location.",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="Check mode: generate fresh copies in a temp dir and fail on any drift.",
    )
    p.add_argument(
        "--commit-sha",
        metavar="SHA",
        help="Explicit git commit SHA (default: auto-detected).",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    verbose = not args.quiet

    # Resolve baseline IDs.
    if args.baseline_id:
        baseline_ids = [args.baseline_id]
    else:
        baseline_ids = list(ALL_BASELINE_IDS)

    if args.check:
        if args.output_dir:
            parser.error("--check and --output-dir are mutually exclusive.")
        return cmd_check(baseline_ids, verbose=verbose)

    # Default / --output-dir mode.
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = SNAPSHOTS_DIR

    return cmd_generate(
        baseline_ids,
        output_dir,
        verbose=verbose,
        commit_sha=args.commit_sha,
    )


if __name__ == "__main__":
    sys.exit(main())
