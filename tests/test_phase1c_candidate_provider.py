"""
tests/test_phase1c_candidate_provider.py — Unit tests for Phase 1C candidate provider contract.

Covers:
- BaselineReference construction from manifest
- FileCandidateSnapshotProvider happy path
- Path security: '..' component, symlink escape, directory at path
- Missing file, non-canonical bytes, non-dict JSON, invalid JSON
- validate_candidate_snapshot: identity field mismatches, NaN, inf, valid, raw_bytes mismatch
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import pytest

from finco_parity.candidate import (
    BaselineReference,
    CandidateContentInvalid,
    CandidateError,
    CandidateFileNotFoundError,
    CandidateIdentityMismatch,
    CandidatePathError,
    CandidateSchemaMismatch,
    CandidateValidationError,
    FileCandidateSnapshotProvider,
    baseline_reference_from_manifest,
    validate_candidate_snapshot,
)
from finco_parity.canonical import canonical_json_bytes
from finco_parity.manifest import SNAPSHOTS_DIR, resolve_snapshot_path, get_manifest_entry

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BASELINE_ID = "tuho"


@pytest.fixture()
def tuho_committed_bytes() -> bytes:
    """Return the raw committed bytes for the 'tuho' baseline."""
    path = SNAPSHOTS_DIR / "tuho.json"
    return path.read_bytes()


@pytest.fixture()
def tuho_committed_dict(tuho_committed_bytes) -> dict:
    return json.loads(tuho_committed_bytes)


@pytest.fixture()
def tuho_reference() -> BaselineReference:
    return baseline_reference_from_manifest(BASELINE_ID)


@pytest.fixture()
def candidate_snapshot(tuho_committed_dict) -> dict:
    """A valid candidate: same as committed but with different engine/run_path."""
    modified = dict(tuho_committed_dict)
    modified["engine_designation"] = "candidate-engine-1"
    modified["run_path_id"] = "candidate-run-1"
    return modified


@pytest.fixture()
def candidate_dir_with_tuho(tmp_path, candidate_snapshot) -> Path:
    """tmp_path populated with a canonical candidate file for 'tuho'."""
    data_bytes = canonical_json_bytes(candidate_snapshot)
    out_file = tmp_path / "tuho.json"
    out_file.write_bytes(data_bytes)
    return tmp_path


# ---------------------------------------------------------------------------
# BaselineReference from manifest
# ---------------------------------------------------------------------------

def test_baseline_reference_from_manifest_fields():
    ref = baseline_reference_from_manifest(BASELINE_ID)
    assert ref.baseline_id == BASELINE_ID
    assert ref.schema_version == "1.0.0"
    assert ref.input_source_id == "project_factories.create_default_tuho_wind1"
    assert ref.committed_snapshot_path.exists()


def test_baseline_reference_from_manifest_unknown():
    with pytest.raises(KeyError):
        baseline_reference_from_manifest("nonexistent_baseline_xyz")


# ---------------------------------------------------------------------------
# FileCandidateSnapshotProvider — happy path
# ---------------------------------------------------------------------------

def test_file_candidate_provider_happy_path(candidate_dir_with_tuho, tuho_reference):
    provider = FileCandidateSnapshotProvider(candidate_dir_with_tuho)
    result = provider.capture_snapshot(BASELINE_ID, tuho_reference)
    assert isinstance(result, dict)
    assert result["baseline_id"] == BASELINE_ID
    assert result["engine_designation"] == "candidate-engine-1"
    assert result["run_path_id"] == "candidate-run-1"


# ---------------------------------------------------------------------------
# Path security: '..' component
# ---------------------------------------------------------------------------

def test_file_candidate_provider_dotdot_escape(tmp_path, tuho_committed_dict):
    """A BaselineReference whose committed path has a '..' component raises CandidatePathError."""
    # Build a fake reference where the committed path includes '..'
    # We need committed_snapshot_path to be something like:
    #   <snapshots_root>/subdir/../tuho.json  (resolves to tuho.json but has ..)
    # Actually, SNAPSHOTS_DIR.resolve() / "sub" / ".." / "tuho.json" — after
    # relative_to(), rel will be "sub/../tuho.json" which has '..' in parts.
    # We build a path that does NOT resolve but has '..' parts.
    snapshots_root = SNAPSHOTS_DIR.resolve()
    # Force a path with '..' by constructing it without resolving
    fake_committed = snapshots_root / "subdir" / ".." / "tuho.json"

    ref = BaselineReference(
        baseline_id=BASELINE_ID,
        project_type_key="wind",
        project_code="tuho",
        scenario_identity="base",
        input_source_id="project_factories.create_default_tuho_wind1",
        schema_version="1.0.0",
        baseline_commit_sha="abc123",
        committed_snapshot_path=fake_committed,
    )

    provider = FileCandidateSnapshotProvider(tmp_path)
    with pytest.raises(CandidatePathError, match=r"\.\.|traversal"):
        provider.capture_snapshot(BASELINE_ID, ref)


# ---------------------------------------------------------------------------
# Path security: symlink escape
# ---------------------------------------------------------------------------

def test_file_candidate_provider_symlink_escape(tmp_path, tuho_reference):
    """A symlink inside candidate_dir pointing outside raises CandidatePathError."""
    # Create an actual target file outside the candidate dir
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    real_file = outside_dir / "secret.json"
    real_file.write_bytes(canonical_json_bytes({"x": 1}))

    # Create candidate_dir as a sub-dir so outside_dir is truly outside
    candidate_dir = tmp_path / "candidates"
    candidate_dir.mkdir()

    # Create symlink inside candidate_dir pointing to the outside file
    # The candidate file name must match the relative path from SNAPSHOTS_DIR
    symlink_target = candidate_dir / "tuho.json"
    os.symlink(real_file, symlink_target)

    provider = FileCandidateSnapshotProvider(candidate_dir)
    with pytest.raises(CandidatePathError):
        provider.capture_snapshot(BASELINE_ID, tuho_reference)


# ---------------------------------------------------------------------------
# Path security: directory at path
# ---------------------------------------------------------------------------

def test_file_candidate_provider_directory_at_path(tmp_path, tuho_reference):
    """If the candidate path is a directory, raises CandidatePathError."""
    # Create a directory where the file should be
    dir_path = tmp_path / "tuho.json"
    dir_path.mkdir()

    provider = FileCandidateSnapshotProvider(tmp_path)
    with pytest.raises(CandidatePathError, match="directory"):
        provider.capture_snapshot(BASELINE_ID, tuho_reference)


# ---------------------------------------------------------------------------
# Missing file
# ---------------------------------------------------------------------------

def test_file_candidate_provider_missing_file(tmp_path, tuho_reference):
    """Missing candidate file raises CandidateFileNotFoundError."""
    provider = FileCandidateSnapshotProvider(tmp_path)
    with pytest.raises(CandidateFileNotFoundError):
        provider.capture_snapshot(BASELINE_ID, tuho_reference)


# ---------------------------------------------------------------------------
# Non-canonical bytes
# ---------------------------------------------------------------------------

def test_file_candidate_provider_non_canonical(tmp_path, tuho_reference, candidate_snapshot):
    """File bytes not in canonical form raises CandidateValidationError."""
    # Write with non-canonical formatting (extra whitespace)
    non_canonical = json.dumps(candidate_snapshot, indent=4).encode()
    (tmp_path / "tuho.json").write_bytes(non_canonical)

    provider = FileCandidateSnapshotProvider(tmp_path)
    with pytest.raises(CandidateValidationError, match="canonical"):
        provider.capture_snapshot(BASELINE_ID, tuho_reference)


# ---------------------------------------------------------------------------
# Non-dict JSON
# ---------------------------------------------------------------------------

def test_file_candidate_provider_non_dict_json(tmp_path, tuho_reference):
    """JSON array (not object) raises CandidateError."""
    raw = canonical_json_bytes([1, 2, 3])
    (tmp_path / "tuho.json").write_bytes(raw)

    provider = FileCandidateSnapshotProvider(tmp_path)
    with pytest.raises(CandidateError):
        provider.capture_snapshot(BASELINE_ID, tuho_reference)


# ---------------------------------------------------------------------------
# Invalid JSON
# ---------------------------------------------------------------------------

def test_file_candidate_provider_invalid_json(tmp_path, tuho_reference):
    """Invalid JSON raises CandidateError."""
    (tmp_path / "tuho.json").write_bytes(b"{not valid json}")

    provider = FileCandidateSnapshotProvider(tmp_path)
    with pytest.raises(CandidateError):
        provider.capture_snapshot(BASELINE_ID, tuho_reference)


# ---------------------------------------------------------------------------
# validate_candidate_snapshot — identity field mismatches
# ---------------------------------------------------------------------------

def test_validate_schema_version_mismatch(candidate_snapshot, tuho_reference):
    bad = dict(candidate_snapshot)
    bad["schema_version"] = "9.9.9"
    with pytest.raises(CandidateValidationError, match="schema_version"):
        validate_candidate_snapshot(bad, tuho_reference)


def test_validate_baseline_id_mismatch(candidate_snapshot, tuho_reference):
    bad = dict(candidate_snapshot)
    bad["baseline_id"] = "wrong_baseline"
    with pytest.raises(CandidateValidationError, match="baseline_id"):
        validate_candidate_snapshot(bad, tuho_reference)


def test_validate_input_source_id_mismatch(candidate_snapshot, tuho_reference):
    bad = dict(candidate_snapshot)
    bad["input_source_id"] = "wrong_input_source"
    with pytest.raises(CandidateValidationError, match="input_source_id"):
        validate_candidate_snapshot(bad, tuho_reference)


# ---------------------------------------------------------------------------
# validate_candidate_snapshot — NaN and inf
# ---------------------------------------------------------------------------

def test_validate_nan_value(candidate_snapshot, tuho_reference):
    bad = dict(candidate_snapshot)
    bad["_test_nan"] = float("nan")
    with pytest.raises(CandidateValidationError, match="[Nn]on-finite|NaN|nan"):
        validate_candidate_snapshot(bad, tuho_reference)


def test_validate_inf_value(candidate_snapshot, tuho_reference):
    bad = dict(candidate_snapshot)
    bad["_test_inf"] = float("inf")
    with pytest.raises(CandidateValidationError, match="[Nn]on-finite|[Ii]nf"):
        validate_candidate_snapshot(bad, tuho_reference)


# ---------------------------------------------------------------------------
# validate_candidate_snapshot — valid candidate passes
# ---------------------------------------------------------------------------

def test_validate_valid_candidate_passes(candidate_snapshot, tuho_reference):
    """A valid candidate snapshot (correct identity, no NaN/inf) passes without exception."""
    validate_candidate_snapshot(candidate_snapshot, tuho_reference)


# ---------------------------------------------------------------------------
# validate_candidate_snapshot — raw_bytes mismatch
# ---------------------------------------------------------------------------

def test_validate_raw_bytes_mismatch(candidate_snapshot, tuho_reference):
    """Passing wrong raw_bytes raises CandidateValidationError."""
    raw = canonical_json_bytes(candidate_snapshot)
    wrong_bytes = raw + b" "  # corrupt the bytes
    with pytest.raises(CandidateValidationError, match="canonical|raw_bytes"):
        validate_candidate_snapshot(candidate_snapshot, tuho_reference, raw_bytes=wrong_bytes)


def test_validate_raw_bytes_correct_passes(candidate_snapshot, tuho_reference):
    """Passing correct raw_bytes passes without exception."""
    raw = canonical_json_bytes(candidate_snapshot)
    validate_candidate_snapshot(candidate_snapshot, tuho_reference, raw_bytes=raw)


# ---------------------------------------------------------------------------
# Typed exception subclasses: identity mismatches → CandidateIdentityMismatch
# ---------------------------------------------------------------------------

def test_validate_schema_version_mismatch_typed(candidate_snapshot, tuho_reference):
    """schema_version mismatch raises CandidateIdentityMismatch (not just CandidateValidationError)."""
    bad = dict(candidate_snapshot)
    bad["schema_version"] = "9.9.9"
    with pytest.raises(CandidateIdentityMismatch):
        validate_candidate_snapshot(bad, tuho_reference)


def test_validate_baseline_id_mismatch_typed(candidate_snapshot, tuho_reference):
    """baseline_id mismatch raises CandidateIdentityMismatch."""
    bad = dict(candidate_snapshot)
    bad["baseline_id"] = "wrong_baseline"
    with pytest.raises(CandidateIdentityMismatch):
        validate_candidate_snapshot(bad, tuho_reference)


def test_validate_input_source_id_mismatch_typed(candidate_snapshot, tuho_reference):
    """input_source_id mismatch raises CandidateIdentityMismatch."""
    bad = dict(candidate_snapshot)
    bad["input_source_id"] = "wrong_input_source"
    with pytest.raises(CandidateIdentityMismatch):
        validate_candidate_snapshot(bad, tuho_reference)


# ---------------------------------------------------------------------------
# Typed exception subclasses: schema validation failure → CandidateSchemaMismatch
# ---------------------------------------------------------------------------

def test_validate_schema_failure_typed(candidate_snapshot, tuho_reference):
    """A snapshot that fails schema validation raises CandidateSchemaMismatch."""
    from unittest.mock import patch
    from finco_parity.schema import SnapshotValidationError

    bad = dict(candidate_snapshot)
    with patch("finco_parity.candidate.validate_snapshot",
               side_effect=SnapshotValidationError("bad schema")):
        with pytest.raises(CandidateSchemaMismatch):
            validate_candidate_snapshot(bad, tuho_reference)


# ---------------------------------------------------------------------------
# Typed exception subclasses: NaN/inf → CandidateContentInvalid
# ---------------------------------------------------------------------------

def test_validate_nan_raises_content_invalid(candidate_snapshot, tuho_reference):
    """NaN in candidate raises CandidateContentInvalid."""
    bad = dict(candidate_snapshot)
    bad["_test_nan"] = float("nan")
    with pytest.raises(CandidateContentInvalid):
        validate_candidate_snapshot(bad, tuho_reference)


def test_validate_inf_raises_content_invalid(candidate_snapshot, tuho_reference):
    """inf in candidate raises CandidateContentInvalid."""
    bad = dict(candidate_snapshot)
    bad["_test_inf"] = float("inf")
    with pytest.raises(CandidateContentInvalid):
        validate_candidate_snapshot(bad, tuho_reference)


# ---------------------------------------------------------------------------
# Typed exception subclasses: raw_bytes mismatch → CandidateContentInvalid
# ---------------------------------------------------------------------------

def test_validate_raw_bytes_mismatch_typed(candidate_snapshot, tuho_reference):
    """raw_bytes mismatch raises CandidateContentInvalid."""
    raw = canonical_json_bytes(candidate_snapshot)
    wrong_bytes = raw + b" "
    with pytest.raises(CandidateContentInvalid):
        validate_candidate_snapshot(candidate_snapshot, tuho_reference, raw_bytes=wrong_bytes)


# ---------------------------------------------------------------------------
# FileCandidateSnapshotProvider: non-canonical file bytes → CandidateContentInvalid
# ---------------------------------------------------------------------------

def test_file_provider_non_canonical_raises_content_invalid(tmp_path, tuho_reference, candidate_snapshot):
    """Non-canonical file bytes raises CandidateContentInvalid (typed subclass)."""
    non_canonical = json.dumps(candidate_snapshot, indent=4).encode()
    (tmp_path / "tuho.json").write_bytes(non_canonical)
    provider = FileCandidateSnapshotProvider(tmp_path)
    with pytest.raises(CandidateContentInvalid):
        provider.capture_snapshot(BASELINE_ID, tuho_reference)


# ---------------------------------------------------------------------------
# FileCandidateSnapshotProvider: baseline_id mismatch → CandidatePathError
# ---------------------------------------------------------------------------

def test_file_provider_baseline_id_mismatch_raises_path_error(candidate_dir_with_tuho, tuho_reference):
    """Calling capture_snapshot with mismatched baseline_id raises CandidatePathError."""
    provider = FileCandidateSnapshotProvider(candidate_dir_with_tuho)
    with pytest.raises(CandidatePathError, match="baseline_id mismatch"):
        provider.capture_snapshot("wrong_baseline_id", tuho_reference)
