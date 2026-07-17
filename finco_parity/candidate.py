"""
finco_parity.candidate — Candidate snapshot provider and validation contract.

Defines the protocol for supplying a candidate snapshot (from a new engine,
fork, or refactor) for comparison against a committed baseline, along with
the validation rules a candidate must satisfy before comparison proceeds.

Import boundary
---------------
This module may only import from:
  - Python standard library
  - finco_parity.*
It must NOT import from app.*, domain.*, finco_core.*, main_web, main_api.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, runtime_checkable

from finco_parity.canonical import canonical_json_bytes
from finco_parity.manifest import (
    SNAPSHOTS_DIR,
    get_manifest_entry,
    resolve_snapshot_path,
)
from finco_parity.schema import SnapshotValidationError, validate_snapshot


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CandidateError(ValueError):
    """Base class for candidate snapshot errors."""


class CandidateFileNotFoundError(CandidateError):
    """Raised when a candidate snapshot file does not exist."""


class CandidatePathError(CandidateError):
    """Raised when a candidate snapshot path is unsafe or invalid."""


class CandidateValidationError(CandidateError):
    """Raised when a candidate snapshot fails validation."""


class CandidateIdentityMismatch(CandidateValidationError):
    """Raised when baseline_id, input_source_id, or baseline_commit_sha does not match reference."""


class CandidateSchemaMismatch(CandidateValidationError):
    """Raised when schema structural validation fails."""


class CandidateContentInvalid(CandidateValidationError):
    """Raised when candidate contains NaN/inf or non-canonical JSON."""


# ---------------------------------------------------------------------------
# BaselineReference dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BaselineReference:
    baseline_id: str
    project_type_key: str
    project_code: str
    scenario_identity: str
    input_source_id: str
    schema_version: str
    baseline_commit_sha: str
    committed_snapshot_path: Path  # absolute resolved path


# ---------------------------------------------------------------------------
# Factory: build BaselineReference from manifest
# ---------------------------------------------------------------------------

def baseline_reference_from_manifest(baseline_id: str) -> BaselineReference:
    """Build a BaselineReference from the manifest entry for *baseline_id*.

    Raises KeyError if the baseline_id is not in the manifest.
    """
    entry = get_manifest_entry(baseline_id)
    committed_path = resolve_snapshot_path(entry)
    return BaselineReference(
        baseline_id=entry["baseline_id"],
        project_type_key=entry.get("project_type_key", ""),
        project_code=entry.get("project_code", ""),
        scenario_identity=entry.get("scenario_identity", ""),
        input_source_id=entry["input_source_id"],
        schema_version=entry["schema_version"],
        baseline_commit_sha=entry["baseline_commit_sha"],
        committed_snapshot_path=committed_path,
    )


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class CandidateSnapshotProvider(Protocol):
    """Protocol for objects that can supply a candidate snapshot."""

    def capture_snapshot(
        self, baseline_id: str, reference: BaselineReference
    ) -> Mapping[str, Any]:
        """Return the candidate snapshot dict for *baseline_id*.

        Args:
            baseline_id: The baseline identifier.
            reference:   The committed baseline reference (path, identity, etc.)

        Returns:
            The raw parsed snapshot dict.

        Raises:
            CandidateFileNotFoundError: If the candidate file is missing.
            CandidatePathError: If the candidate path is unsafe.
            CandidateError: For other capture failures.
        """
        ...


# ---------------------------------------------------------------------------
# FileCandidateSnapshotProvider
# ---------------------------------------------------------------------------

class FileCandidateSnapshotProvider:
    """Reads candidate snapshots from a directory on disk.

    The candidate file path is resolved by replicating the relative path of
    the committed artifact under ``candidate_dir``.

    Security rules:
      - Absolute candidate-relative paths are rejected.
      - ``..`` components are rejected.
      - The resolved path must remain inside ``candidate_dir``.
      - Symlink escapes are detected (resolved path must start with resolved
        ``candidate_dir``).
      - Directories are rejected.
      - Missing files raise ``CandidateFileNotFoundError``.
    """

    def __init__(self, candidate_dir: Path) -> None:
        self._candidate_dir = Path(candidate_dir).resolve()

    def capture_snapshot(
        self, baseline_id: str, reference: BaselineReference
    ) -> Mapping[str, Any]:
        """Return the parsed JSON dict from the candidate file.

        Does NOT validate the snapshot; validation is the caller's
        responsibility.  Does NOT modify the file.
        """
        if baseline_id != reference.baseline_id:
            raise CandidatePathError(
                f"baseline_id mismatch: caller passed {baseline_id!r} "
                f"but reference.baseline_id is {reference.baseline_id!r}"
            )

        canonical_path = reference.committed_snapshot_path
        snapshots_root = SNAPSHOTS_DIR.resolve()

        # Derive relative path from SNAPSHOTS_DIR.
        try:
            rel = canonical_path.relative_to(snapshots_root)
        except ValueError:
            raise CandidatePathError(
                f"{baseline_id}: committed snapshot path is outside the allowed snapshot root"
            )

        # Reject absolute candidate-relative paths (rel should always be relative
        # but guard defensively).
        if rel.is_absolute():
            raise CandidatePathError(
                f"{baseline_id}: derived relative path is absolute: {rel}"
            )

        # Reject '..' components.
        if any(part == ".." for part in rel.parts):
            raise CandidatePathError(
                f"{baseline_id}: relative path contains '..' traversal: {rel}"
            )

        candidate_path = self._candidate_dir / rel

        # Resolve to detect symlink escapes.
        try:
            resolved = candidate_path.resolve()
        except Exception:
            raise CandidatePathError(
                f"{baseline_id}: candidate path could not be resolved: {rel}"
            )

        # Must remain inside candidate_dir (symlink escape check).
        try:
            resolved.relative_to(self._candidate_dir)
        except ValueError:
            raise CandidatePathError(
                f"{baseline_id}: candidate path escapes candidate directory: {rel}"
            )

        # Reject directories.
        if resolved.is_dir():
            raise CandidatePathError(
                f"{baseline_id}: candidate path is a directory: {rel}"
            )

        # Missing file.
        if not resolved.exists():
            raise CandidateFileNotFoundError(
                f"{baseline_id}: candidate snapshot not found: {rel}"
            )

        try:
            raw_bytes = resolved.read_bytes()
        except OSError as exc:
            raise CandidateError(
                f"{baseline_id}: candidate snapshot could not be read: {rel} "
                f"({type(exc).__name__}, errno={exc.errno}: {exc.strerror})"
            ) from exc
        try:
            data = json.loads(raw_bytes)
        except Exception:
            raise CandidateError(
                f"{baseline_id}: cannot parse candidate JSON: {rel}"
            )

        if not isinstance(data, dict):
            raise CandidateError(
                f"{baseline_id}: candidate snapshot must be a JSON object, "
                f"got {type(data).__name__}"
            )

        # Canonical form check: file bytes must equal canonical_json_bytes(parsed).
        try:
            expected_bytes = canonical_json_bytes(data)
        except (ValueError, TypeError) as exc:
            raise CandidateContentInvalid(
                f"{baseline_id}: candidate snapshot cannot be re-serialized "
                f"canonically: {exc}"
            )
        if raw_bytes != expected_bytes:
            raise CandidateContentInvalid(
                f"{baseline_id}: candidate snapshot is not in canonical JSON form: {rel}. "
                f"Re-serialize with canonical_json_bytes() to fix."
            )

        return data


# ---------------------------------------------------------------------------
# Candidate snapshot validation
# ---------------------------------------------------------------------------

def _check_no_nonfinite(data: Any, path: str = "") -> list[str]:
    """Recursively find all NaN/±inf numeric values; return list of error strings."""
    errors: list[str] = []
    if isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            errors.append(f"Non-finite float at {path!r}: {data!r}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            errors.extend(_check_no_nonfinite(item, f"{path}[{i}]"))
    elif isinstance(data, dict):
        for k, v in data.items():
            errors.extend(_check_no_nonfinite(v, f"{path}.{k}" if path else k))
    return errors


def validate_candidate_snapshot(
    candidate: dict,
    reference: BaselineReference,
    *,
    raw_bytes: bytes | None = None,
) -> None:
    """Validate a candidate snapshot dict against the given baseline reference.

    Checks performed (in order):
    1. schema_version must match reference → CandidateSchemaMismatch on mismatch.
    2. Identity fields (baseline_id, input_source_id, baseline_commit_sha) must
       match *reference* exactly → CandidateIdentityMismatch on any mismatch.
    3. Structural schema validation via ``validate_snapshot()`` → CandidateSchemaMismatch.
    4. No NaN or infinity in any numeric value → CandidateContentInvalid.
    5. If *raw_bytes* is provided, canonical byte equality check → CandidateContentInvalid.

    Note: ``engine_designation`` and ``run_path_id`` are intentionally NOT
    checked — they are expected provenance differences between legacy and
    candidate engines.

    Raises:
        CandidateSchemaMismatch: on schema_version mismatch or structural validation failure.
        CandidateIdentityMismatch: on identity field mismatch.
        CandidateContentInvalid: on NaN/inf or non-canonical bytes.
    """
    # 1. Schema version check → CandidateSchemaMismatch.
    if candidate.get("schema_version") != reference.schema_version:
        raise CandidateSchemaMismatch(
            f"schema_version mismatch: expected {reference.schema_version!r}, "
            f"got {candidate.get('schema_version')!r} "
            f"(baseline_id={reference.baseline_id!r})"
        )

    # 2. Identity field checks → CandidateIdentityMismatch.
    _IDENTITY_FIELDS = {
        "baseline_id": reference.baseline_id,
        "input_source_id": reference.input_source_id,
        "baseline_commit_sha": reference.baseline_commit_sha,
    }
    for field, expected in _IDENTITY_FIELDS.items():
        actual = candidate.get(field)
        if actual != expected:
            raise CandidateIdentityMismatch(
                f"Identity field mismatch for {field!r}: "
                f"expected {expected!r}, got {actual!r} "
                f"(baseline_id={reference.baseline_id!r})"
            )

    # 3. Structural schema validation → CandidateSchemaMismatch.
    try:
        validate_snapshot(candidate)
    except SnapshotValidationError as exc:
        raise CandidateSchemaMismatch(
            f"Candidate snapshot fails schema validation "
            f"(baseline_id={reference.baseline_id!r}): {exc}"
        ) from exc

    # 3. No NaN / infinity.
    nonfinite_errors = _check_no_nonfinite(candidate)
    if nonfinite_errors:
        raise CandidateContentInvalid(
            f"Candidate snapshot contains non-finite floats "
            f"(baseline_id={reference.baseline_id!r}):\n"
            + "\n".join(f"  {e}" for e in nonfinite_errors)
        )

    # 4. Optional canonical bytes check.
    if raw_bytes is not None:
        try:
            expected_bytes = canonical_json_bytes(candidate)
        except (ValueError, TypeError) as exc:
            raise CandidateContentInvalid(
                f"Cannot re-serialize candidate canonically "
                f"(baseline_id={reference.baseline_id!r}): {exc}"
            ) from exc
        if raw_bytes != expected_bytes:
            raise CandidateContentInvalid(
                f"Candidate snapshot is not in canonical JSON form "
                f"(baseline_id={reference.baseline_id!r}): "
                f"raw_bytes != canonical_json_bytes(parsed)"
            )
