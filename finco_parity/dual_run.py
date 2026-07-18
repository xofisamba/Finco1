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
from collections.abc import Sequence
from typing import Any, Mapping

from finco_parity.candidate import (
    BaselineReference,
    CandidateContentInvalid,
    CandidateError,
    CandidateFileNotFoundError,
    CandidateIdentityMismatch,
    CandidateSchemaMismatch,
    CandidateSnapshotProvider,
    CandidateValidationError,
    FileCandidateSnapshotProvider,
    baseline_reference_from_entry,
    baseline_reference_from_manifest,
    validate_candidate_snapshot,
)
from finco_parity.profiles import ComparisonProfile, project_for_profile
from finco_parity.comparison import (
    ComparisonResult,
    Difference,
    DriftKind,
    compare_snapshots,
    format_comparison_report,
)
from finco_parity.manifest import (
    ManifestIntegrityError,
    ValidatedManifestContext,
    load_validated_manifest_context,
    resolve_snapshot_path,
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
    MANIFEST_INTEGRITY_FAILURE = "MANIFEST_INTEGRITY_FAILURE"
    UNKNOWN_BASELINE = "UNKNOWN_BASELINE"


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

_AGGREGATE_SEVERITY: dict[BaselineRunStatus, int] = {
    BaselineRunStatus.MANIFEST_INTEGRITY_FAILURE: 9,
    BaselineRunStatus.ENVIRONMENT_MISMATCH: 8,
    BaselineRunStatus.LEGACY_DRIFT: 7,
    BaselineRunStatus.EXECUTION_ERROR: 6,
    BaselineRunStatus.SCHEMA_MISMATCH: 5,
    BaselineRunStatus.IDENTITY_MISMATCH: 4,
    BaselineRunStatus.CANDIDATE_INVALID: 3,
    BaselineRunStatus.CANDIDATE_MISSING: 2,
    BaselineRunStatus.UNKNOWN_BASELINE: 2,
    BaselineRunStatus.PAYLOAD_DRIFT: 1,
    BaselineRunStatus.PASS: 0,
}


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

def _run_candidate_with_context(
    baseline_id: str,
    provider: CandidateSnapshotProvider,
    ctx: ValidatedManifestContext,
    *,
    verify_legacy: bool = True,
    max_diffs: int | None = None,
    verbose: bool = False,
    comparison_profile: ComparisonProfile = ComparisonProfile.FULL,
) -> BaselineRunResult:
    """Internal: run one baseline comparison using an already-validated context.

    Does NOT reload the manifest; uses the provided ValidatedManifestContext.
    comparison_profile alters payload projection only — not identity, schema, or
    legacy verification.
    """
    from finco_parity.generate_baselines import check_generation_environment

    if max_diffs is not None and max_diffs < 0:
        raise ValueError(f"max_diffs must be >= 0, got {max_diffs!r}")

    # Baseline ID lookup inside validated context (no manifest reload).
    if baseline_id not in ctx.baseline_ids:
        return _error_result(
            baseline_id,
            BaselineRunStatus.UNKNOWN_BASELINE,
            f"baseline_id not found in manifest: {baseline_id!r}",
        )

    # Environment check.
    env_error = check_generation_environment(ctx.manifest)
    if env_error:
        return _error_result(
            baseline_id,
            BaselineRunStatus.ENVIRONMENT_MISMATCH,
            f"Environment mismatch: {env_error}",
        )

    # Load committed artifact from context (no manifest reload).
    try:
        entry = ctx.get_entry(baseline_id)
    except KeyError:
        return _error_result(
            baseline_id,
            BaselineRunStatus.MANIFEST_INTEGRITY_FAILURE,
            f"baseline_id not in validated context: {baseline_id!r}",
        )

    try:
        artifact_path = resolve_snapshot_path(entry)
        raw_committed = artifact_path.read_bytes()
        committed_snapshot: dict = json.loads(raw_committed)
    except (ManifestIntegrityError, OSError, json.JSONDecodeError, ValueError) as exc:
        return _error_result(
            baseline_id,
            BaselineRunStatus.MANIFEST_INTEGRITY_FAILURE,
            f"Failed to load committed artifact for {baseline_id!r}: {type(exc).__name__}",
        )
    except Exception as exc:
        return _error_result(
            baseline_id,
            BaselineRunStatus.EXECUTION_ERROR,
            f"Failed to load committed artifact: {type(exc).__name__}",
        )

    # Build reference from entry (no manifest reload).
    try:
        reference = baseline_reference_from_entry(entry)
    except Exception as exc:
        return _error_result(
            baseline_id,
            BaselineRunStatus.EXECUTION_ERROR,
            f"Failed to build BaselineReference: {type(exc).__name__}",
            legacy_snapshot=committed_snapshot,
        )

    # Optional legacy re-run.
    if verify_legacy:
        try:
            from finco_parity.legacy_snapshot import capture_snapshot
            fresh_legacy = capture_snapshot(
                baseline_id=baseline_id,
                commit_sha=committed_snapshot.get("baseline_commit_sha", ""),
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

    # Acquire candidate snapshot.
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

    # Validate candidate.
    try:
        validate_candidate_snapshot(candidate_snapshot, reference)
    except CandidateIdentityMismatch as exc:
        return _error_result(
            baseline_id,
            BaselineRunStatus.IDENTITY_MISMATCH,
            str(exc),
            legacy_snapshot=committed_snapshot,
            candidate_snapshot=candidate_snapshot,
        )
    except CandidateSchemaMismatch as exc:
        return _error_result(
            baseline_id,
            BaselineRunStatus.SCHEMA_MISMATCH,
            str(exc),
            legacy_snapshot=committed_snapshot,
            candidate_snapshot=candidate_snapshot,
        )
    except CandidateValidationError as exc:
        return _error_result(
            baseline_id,
            BaselineRunStatus.CANDIDATE_INVALID,
            str(exc),
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

    # Project to parity sections using the comparison profile.
    # FULL: standard _PARITY_SECTIONS projection (Phase 1C behaviour unchanged).
    # OPERATING_CORE_V1: project_for_profile narrows to Phase 2A paths only.
    if comparison_profile is ComparisonProfile.FULL:
        committed_projected = _project_for_comparison(committed_snapshot)
        candidate_projected = _project_for_comparison(candidate_snapshot)
    else:
        committed_projected = project_for_profile(committed_snapshot, comparison_profile)
        candidate_projected = project_for_profile(candidate_snapshot, comparison_profile)

    # Compare.
    cmp_result = compare_snapshots(committed_projected, candidate_projected, baseline_id)

    diffs = cmp_result.differences
    if max_diffs is not None:
        diffs = diffs[:max_diffs]

    # Determine result status.
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


def run_candidate_provider(
    baseline_id: str,
    provider: CandidateSnapshotProvider,
    *,
    verify_legacy: bool = True,
    max_diffs: int | None = None,
    verbose: bool = False,
    comparison_profile: ComparisonProfile = ComparisonProfile.FULL,
) -> BaselineRunResult:
    """Orchestrate one baseline comparison. Loads manifest exactly once.

    comparison_profile alters payload projection only — not identity, schema, or
    legacy verification.
    """
    if max_diffs is not None and max_diffs < 0:
        raise ValueError(f"max_diffs must be >= 0, got {max_diffs!r}")

    # Single manifest load and validation.
    try:
        ctx = load_validated_manifest_context()
    except ManifestIntegrityError as exc:
        return _error_result(
            baseline_id,
            BaselineRunStatus.MANIFEST_INTEGRITY_FAILURE,
            f"Manifest integrity failure: {exc}",
        )

    return _run_candidate_with_context(
        baseline_id,
        provider,
        ctx,
        verify_legacy=verify_legacy,
        max_diffs=max_diffs,
        verbose=verbose,
        comparison_profile=comparison_profile,
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
    if max_diffs is not None and max_diffs < 0:
        raise ValueError(f"max_diffs must be >= 0, got {max_diffs!r}")

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


# ---------------------------------------------------------------------------
# Shared aggregate exit-code mapping (single source of truth)
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


def exit_code_for_aggregate(result: AggregateRunResult) -> int:
    """Return the CLI exit code for an AggregateRunResult.

    Derived from overall_status using _AGGREGATE_SEVERITY ordering.
    Shared by all Phase 1C and Phase 2A CLIs.
    """
    return _STATUS_EXIT_CODE.get(result.overall_status, 1)


def _build_aggregate(
    selected: list[str],
    results: list[BaselineRunResult],
) -> AggregateRunResult:
    """Assemble an AggregateRunResult from a list of per-baseline results.

    overall_status uses _AGGREGATE_SEVERITY; does not aggregate by exit-code order.
    """
    passed = tuple(r.baseline_id for r in results if r.status == BaselineRunStatus.PASS)
    failed = tuple(r.baseline_id for r in results if r.status != BaselineRunStatus.PASS)
    if not failed:
        overall = BaselineRunStatus.PASS
    else:
        overall = max(
            (r.status for r in results if r.status != BaselineRunStatus.PASS),
            key=lambda s: _AGGREGATE_SEVERITY.get(s, 0),
        )
    return AggregateRunResult(
        selected_baselines=tuple(selected),
        passed_baselines=passed,
        failed_baselines=failed,
        overall_status=overall,
        baseline_results=tuple(results),
    )


# ---------------------------------------------------------------------------
# Public provider-aggregate API
# ---------------------------------------------------------------------------

def compare_candidate_provider(
    provider: CandidateSnapshotProvider,
    *,
    baseline_ids: Sequence[str] | None = None,
    comparison_profile: ComparisonProfile = ComparisonProfile.FULL,
    verify_legacy: bool = True,
    max_diffs: int | None = None,
    verbose: bool = False,
) -> AggregateRunResult:
    """Orchestrate comparison for all (or selected) baselines using a provider.

    1. Loads one ValidatedManifestContext.
    2. Validates selected IDs.
    3. Preserves manifest order.
    4. Reuses the same context for every baseline.
    5. Calls the provider exactly once per selected baseline.
    6. Uses _run_candidate_with_context() internally.
    7. Selects overall_status using _AGGREGATE_SEVERITY.
    8. Returns AggregateRunResult.

    ComparisonProfile.FULL is the default (Phase 1C behaviour unchanged).
    """
    if max_diffs is not None and max_diffs < 0:
        raise ValueError(f"max_diffs must be >= 0, got {max_diffs!r}")

    try:
        ctx = load_validated_manifest_context()
    except ManifestIntegrityError:
        raise

    all_ids = list(ctx.baseline_ids)

    if baseline_ids is not None:
        unknown = [bid for bid in baseline_ids if bid not in all_ids]
        if unknown:
            raise ValueError(
                f"Unknown baseline_id(s): {unknown!r}. Valid IDs: {all_ids!r}"
            )
        selected = [bid for bid in all_ids if bid in set(baseline_ids)]
    else:
        selected = list(all_ids)

    results: list[BaselineRunResult] = []
    for bid in selected:
        result = _run_candidate_with_context(
            bid,
            provider,
            ctx,
            verify_legacy=verify_legacy,
            max_diffs=max_diffs,
            verbose=verbose,
            comparison_profile=comparison_profile,
        )
        results.append(result)

    return _build_aggregate(selected, results)


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

    if max_diffs is not None and max_diffs < 0:
        raise ValueError(f"max_diffs must be >= 0, got {max_diffs!r}")

    try:
        ctx = load_validated_manifest_context()
    except ManifestIntegrityError:
        raise  # propagate to caller

    all_ids = list(ctx.baseline_ids)

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
        result = _run_candidate_with_context(
            bid,
            provider,
            ctx,  # same context for every baseline — no re-validation
            verify_legacy=verify_legacy,
            max_diffs=max_diffs,
            verbose=verbose,
        )
        results.append(result)
        if verbose:
            print(f"  {bid}: {result.status.value}", file=sys.stderr, flush=True)

    return _build_aggregate(selected, results)
