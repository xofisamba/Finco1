"""
finco_parity.dual_run — Orchestration layer for candidate vs. baseline comparison.

Coordinates:
  1. Environment and manifest integrity checks.
  2. Optional live legacy re-run to verify the committed artifact is stable.
  3. Candidate snapshot acquisition via CandidateSnapshotProvider.
  4. Candidate validation (identity, schema, canonicality).
  5. Payload projection to blocking parity sections.
  6. Structural/numeric comparison via compare_snapshots().

Import boundary
---------------
This module may only import from:
  - Python standard library
  - finco_parity.*
It must NOT import from app.*, domain.*, finco_core.*, main_web, main_api.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from finco_parity.candidate import (
    BaselineReference,
    CandidateError,
    CandidateFileNotFoundError,
    CandidateSnapshotProvider,
    CandidateValidationError,
    FileCandidateSnapshotProvider,
    baseline_reference_from_manifest,
    validate_candidate_snapshot,
)
from finco_parity.comparison import (
    ComparisonResult,
    Difference,
    DriftKind,
    compare_snapshots,
    format_comparison_report,
)
from finco_parity.manifest import (
    ManifestIntegrityError,
    get_manifest_entry,
    load_manifest,
    manifest_baseline_ids,
    resolve_snapshot_path,
    validate_manifest_integrity,
)
from finco_parity.schema import SnapshotValidationError


# ---------------------------------------------------------------------------
# Status enum
# ---------------------------------------------------------------------------

class BaselineRunStatus(str, Enum):
    PASS = "PASS"
    CANDIDATE_MISSING = "CANDIDATE_MISSING"
    CANDIDATE_INVALID = "CANDIDATE_INVALID"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    PAYLOAD_DRIFT = "PAYLOAD_DRIFT"
    LEGACY_DRIFT = "LEGACY_DRIFT"
    ENVIRONMENT_MISMATCH = "ENVIRONMENT_MISMATCH"
    EXECUTION_ERROR = "EXECUTION_ERROR"


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BaselineRunResult:
    baseline_id: str
    status: BaselineRunStatus
    legacy_engine_designation: str | None
    candidate_engine_designation: str | None
    legacy_run_path: str | None
    candidate_run_path: str | None
    comparison_status: str | None   # DriftKind value or None
    difference_count: int
    differences: tuple[Difference, ...]
    legacy_warnings: tuple[str, ...]
    candidate_warnings: tuple[str, ...]
    error_message: str | None = None

    def to_dict(self) -> dict:
        return {
            "baseline_id": self.baseline_id,
            "status": self.status.value,
            "legacy_engine_designation": self.legacy_engine_designation,
            "candidate_engine_designation": self.candidate_engine_designation,
            "legacy_run_path": self.legacy_run_path,
            "candidate_run_path": self.candidate_run_path,
            "comparison_status": self.comparison_status,
            "difference_count": self.difference_count,
            "differences": [d.to_dict() for d in self.differences],
            "legacy_warnings": list(self.legacy_warnings),
            "candidate_warnings": list(self.candidate_warnings),
            "error_message": self.error_message,
        }


@dataclass(frozen=True)
class AggregateRunResult:
    selected_baselines: tuple[str, ...]
    passed_baselines: tuple[str, ...]
    failed_baselines: tuple[str, ...]
    overall_status: BaselineRunStatus   # PASS only if all pass
    baseline_results: tuple[BaselineRunResult, ...]

    def to_dict(self) -> dict:
        return {
            "selected_baselines": list(self.selected_baselines),
            "passed_baselines": list(self.passed_baselines),
            "failed_baselines": list(self.failed_baselines),
            "overall_status": self.overall_status.value,
            "baseline_results": [r.to_dict() for r in self.baseline_results],
        }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Sections that must match for parity (blocking sections).
_PARITY_SECTIONS: frozenset[str] = frozenset({
    "period_grid",
    "operating_schedules",
    "tax_and_cfads",
    "financing",
    "financial_statements",
    "returns",
    "unavailable_sections",
    "unavailable_fields",
})

_IDENTITY_FIELDS: frozenset[str] = frozenset({
    "schema_version",
    "baseline_id",
    "input_source_id",
})

_PROVENANCE_FIELDS: frozenset[str] = frozenset({
    "engine_designation",
    "run_path_id",
})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_warnings(snapshot: dict) -> tuple[str, ...]:
    """Extract warnings list from snapshot."""
    w = snapshot.get("warnings") or []
    return tuple(str(x) for x in w)


def _project_for_comparison(snapshot: dict) -> dict:
    """Return only the blocking parity payload sections."""
    return {k: v for k, v in snapshot.items() if k in _PARITY_SECTIONS}


def _error_result(
    baseline_id: str,
    status: BaselineRunStatus,
    error_message: str,
    *,
    legacy_snapshot: dict | None = None,
    candidate_snapshot: dict | None = None,
) -> BaselineRunResult:
    """Build a failed BaselineRunResult with minimal fields populated."""
    legacy_ed = legacy_snapshot.get("engine_designation") if legacy_snapshot else None
    legacy_rp = legacy_snapshot.get("run_path_id") if legacy_snapshot else None
    legacy_w = _extract_warnings(legacy_snapshot) if legacy_snapshot else ()
    cand_ed = candidate_snapshot.get("engine_designation") if candidate_snapshot else None
    cand_rp = candidate_snapshot.get("run_path_id") if candidate_snapshot else None
    cand_w = _extract_warnings(candidate_snapshot) if candidate_snapshot else ()
    return BaselineRunResult(
        baseline_id=baseline_id,
        status=status,
        legacy_engine_designation=legacy_ed,
        candidate_engine_designation=cand_ed,
        legacy_run_path=legacy_rp,
        candidate_run_path=cand_rp,
        comparison_status=None,
        difference_count=0,
        differences=(),
        legacy_warnings=legacy_w,
        candidate_warnings=cand_w,
        error_message=error_message,
    )


# ---------------------------------------------------------------------------
# Primary orchestration functions
# ---------------------------------------------------------------------------

def run_candidate_provider(
    baseline_id: str,
    provider: CandidateSnapshotProvider,
    *,
    verify_legacy: bool = True,
    max_diffs: int | None = None,
    verbose: bool = False,
) -> BaselineRunResult:
    """Orchestrate one baseline comparison.

    Steps:
    1. Environment check.
    2. Manifest integrity check.
    3. Load committed artifact.
    4. Optionally capture fresh legacy snapshot and verify against committed.
    5. Acquire candidate snapshot.
    6. Validate candidate.
    7. Project both to _PARITY_SECTIONS.
    8. Compare.
    9. Return result.
    """
    from finco_parity.generate_baselines import check_generation_environment

    # Step 1: Environment check.
    manifest = load_manifest()
    env_error = check_generation_environment(manifest)
    if env_error:
        return _error_result(
            baseline_id,
            BaselineRunStatus.ENVIRONMENT_MISMATCH,
            f"Environment mismatch: {env_error}",
        )

    # Step 2: Manifest integrity.
    try:
        validate_manifest_integrity()
    except ManifestIntegrityError as exc:
        return _error_result(
            baseline_id,
            BaselineRunStatus.EXECUTION_ERROR,
            f"Manifest integrity failure: {exc}",
        )

    # Step 3: Load committed artifact.
    try:
        entry = get_manifest_entry(baseline_id)
    except KeyError:
        return _error_result(
            baseline_id,
            BaselineRunStatus.EXECUTION_ERROR,
            f"baseline_id not found in manifest: {baseline_id!r}",
        )

    try:
        artifact_path = resolve_snapshot_path(entry)
        raw_committed = artifact_path.read_bytes()
        committed_snapshot: dict = json.loads(raw_committed)
    except Exception as exc:
        return _error_result(
            baseline_id,
            BaselineRunStatus.EXECUTION_ERROR,
            f"Failed to load committed artifact: {exc}",
        )

    # Build reference object.
    try:
        reference = baseline_reference_from_manifest(baseline_id)
    except Exception as exc:
        return _error_result(
            baseline_id,
            BaselineRunStatus.EXECUTION_ERROR,
            f"Failed to build BaselineReference: {exc}",
            legacy_snapshot=committed_snapshot,
        )

    # Step 4: Optional legacy re-run.
    if verify_legacy:
        try:
            from finco_parity.legacy_snapshot import capture_snapshot
            fresh_legacy = capture_snapshot(
                baseline_id=baseline_id,
                baseline_commit_sha=committed_snapshot.get("baseline_commit_sha", ""),
            )
        except Exception as exc:
            return _error_result(
                baseline_id,
                BaselineRunStatus.EXECUTION_ERROR,
                f"Legacy snapshot capture failed: {exc}",
                legacy_snapshot=committed_snapshot,
            )

        # Compare fresh legacy against committed artifact.
        legacy_cmp = compare_snapshots(committed_snapshot, fresh_legacy, baseline_id)
        if not legacy_cmp.is_identical():
            diffs = legacy_cmp.differences
            if max_diffs is not None:
                diffs = diffs[:max_diffs]
            return BaselineRunResult(
                baseline_id=baseline_id,
                status=BaselineRunStatus.LEGACY_DRIFT,
                legacy_engine_designation=fresh_legacy.get("engine_designation"),
                candidate_engine_designation=None,
                legacy_run_path=fresh_legacy.get("run_path_id"),
                candidate_run_path=None,
                comparison_status=legacy_cmp.status.value,
                difference_count=len(legacy_cmp.differences),
                differences=tuple(diffs),
                legacy_warnings=_extract_warnings(fresh_legacy),
                candidate_warnings=(),
                error_message=(
                    f"Live legacy snapshot differs from committed artifact "
                    f"({len(legacy_cmp.differences)} differences)"
                ),
            )

    # Step 5: Acquire candidate snapshot.
    candidate_snapshot: dict | None = None
    try:
        candidate_raw = provider.capture_snapshot(baseline_id, reference)
        candidate_snapshot = dict(candidate_raw)
    except CandidateFileNotFoundError as exc:
        return _error_result(
            baseline_id,
            BaselineRunStatus.CANDIDATE_MISSING,
            str(exc),
            legacy_snapshot=committed_snapshot,
        )
    except CandidateError as exc:
        return _error_result(
            baseline_id,
            BaselineRunStatus.CANDIDATE_INVALID,
            str(exc),
            legacy_snapshot=committed_snapshot,
        )
    except Exception as exc:
        return _error_result(
            baseline_id,
            BaselineRunStatus.EXECUTION_ERROR,
            f"Unexpected error acquiring candidate snapshot: {exc}",
            legacy_snapshot=committed_snapshot,
        )

    # Step 6: Validate candidate.
    try:
        validate_candidate_snapshot(candidate_snapshot, reference)
    except CandidateValidationError as exc:
        msg = str(exc)
        # Classify error type.
        if any(f in msg for f in ("schema_version", "baseline_id", "input_source_id")):
            status = BaselineRunStatus.IDENTITY_MISMATCH
        elif "schema validation" in msg:
            status = BaselineRunStatus.SCHEMA_MISMATCH
        else:
            status = BaselineRunStatus.CANDIDATE_INVALID
        return _error_result(
            baseline_id,
            status,
            msg,
            legacy_snapshot=committed_snapshot,
            candidate_snapshot=candidate_snapshot,
        )
    except Exception as exc:
        return _error_result(
            baseline_id,
            BaselineRunStatus.CANDIDATE_INVALID,
            f"Candidate validation error: {exc}",
            legacy_snapshot=committed_snapshot,
            candidate_snapshot=candidate_snapshot,
        )

    # Step 7: Project to parity sections.
    committed_projected = _project_for_comparison(committed_snapshot)
    candidate_projected = _project_for_comparison(candidate_snapshot)

    # Step 8: Compare.
    cmp_result = compare_snapshots(committed_projected, candidate_projected, baseline_id)

    diffs = cmp_result.differences
    if max_diffs is not None:
        diffs = diffs[:max_diffs]

    # Step 9: Determine result status.
    if cmp_result.is_identical():
        run_status = BaselineRunStatus.PASS
    else:
        run_status = BaselineRunStatus.PAYLOAD_DRIFT

    return BaselineRunResult(
        baseline_id=baseline_id,
        status=run_status,
        legacy_engine_designation=committed_snapshot.get("engine_designation"),
        candidate_engine_designation=candidate_snapshot.get("engine_designation"),
        legacy_run_path=committed_snapshot.get("run_path_id"),
        candidate_run_path=candidate_snapshot.get("run_path_id"),
        comparison_status=cmp_result.status.value,
        difference_count=len(cmp_result.differences),
        differences=tuple(diffs),
        legacy_warnings=_extract_warnings(committed_snapshot),
        candidate_warnings=_extract_warnings(candidate_snapshot),
        error_message=None,
    )


def compare_candidate_snapshot(
    baseline_id: str,
    candidate_snapshot: Mapping[str, Any],
    *,
    verify_legacy: bool = True,
    max_diffs: int | None = None,
) -> BaselineRunResult:
    """Compare a pre-loaded candidate snapshot against the committed baseline.

    This is a convenience wrapper around run_candidate_provider that accepts
    a pre-loaded snapshot dict instead of a provider object.
    """
    class _InlineProvider:
        def __init__(self, snapshot: Mapping[str, Any]) -> None:
            self._snapshot = snapshot

        def capture_snapshot(
            self, bid: str, reference: BaselineReference
        ) -> Mapping[str, Any]:
            return self._snapshot

    return run_candidate_provider(
        baseline_id,
        _InlineProvider(candidate_snapshot),
        verify_legacy=verify_legacy,
        max_diffs=max_diffs,
    )


def compare_candidate_directory(
    candidate_dir: Path,
    baseline_ids: list[str] | None = None,
    *,
    verify_legacy: bool = True,
    max_diffs: int | None = None,
    verbose: bool = False,
) -> AggregateRunResult:
    """Compare all (or selected) baselines from a candidate directory.

    Uses FileCandidateSnapshotProvider.  Returns results in manifest order.

    Args:
        candidate_dir:  Directory containing candidate snapshot files.
        baseline_ids:   Subset of baseline IDs to compare; None means all.
        verify_legacy:  Whether to capture and verify a fresh legacy snapshot.
        max_diffs:      Cap on differences reported per baseline.
        verbose:        If True, emit progress to stderr.

    Returns:
        AggregateRunResult summarizing all comparisons.
    """
    import sys

    all_ids = manifest_baseline_ids()

    if baseline_ids is not None:
        # Validate requested IDs against manifest.
        unknown = [bid for bid in baseline_ids if bid not in all_ids]
        if unknown:
            raise ValueError(
                f"Unknown baseline_id(s): {unknown!r}. "
                f"Valid IDs: {all_ids!r}"
            )
        selected = [bid for bid in all_ids if bid in baseline_ids]
    else:
        selected = list(all_ids)

    provider = FileCandidateSnapshotProvider(Path(candidate_dir))

    results: list[BaselineRunResult] = []
    for bid in selected:
        if verbose:
            print(f"Comparing {bid} ...", file=sys.stderr, flush=True)
        result = run_candidate_provider(
            bid,
            provider,
            verify_legacy=verify_legacy,
            max_diffs=max_diffs,
            verbose=verbose,
        )
        results.append(result)
        if verbose:
            print(f"  {bid}: {result.status.value}", file=sys.stderr, flush=True)

    passed = tuple(r.baseline_id for r in results if r.status == BaselineRunStatus.PASS)
    failed = tuple(r.baseline_id for r in results if r.status != BaselineRunStatus.PASS)
    overall = BaselineRunStatus.PASS if not failed else results[
        next(i for i, r in enumerate(results) if r.status != BaselineRunStatus.PASS)
    ].status

    return AggregateRunResult(
        selected_baselines=tuple(selected),
        passed_baselines=passed,
        failed_baselines=failed,
        overall_status=overall,
        baseline_results=tuple(results),
    )
