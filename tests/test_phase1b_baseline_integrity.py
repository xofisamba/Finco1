"""
tests/test_phase1b_baseline_integrity.py — Manifest ↔ artifact integrity tests.

Tests:
  - Happy path: committed state passes all checks.
  - Missing required manifest field fails.
  - Missing artifact fails.
  - Orphan artifact fails.
  - Duplicate baseline_id fails.
  - Duplicate artifact path fails.
  - Incorrect SHA-256 fails.
  - Schema version mismatch fails.
  - Provenance mismatch (baseline_id, engine, commit_sha, input_source, run_path) fails.
  - Path traversal rejected.
  - Absolute snapshot_path rejected.
  - Non-canonical artifact bytes fail.
  - capture_source mismatch fails.
  - artifact_sha256 wrong format fails.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from finco_parity.canonical import canonical_json_bytes
from finco_parity.manifest import (
    ManifestIntegrityError,
    _CANONICAL_CAPTURE_SOURCE,
    load_manifest,
    resolve_snapshot_path,
    snapshot_path_for,
    validate_manifest_integrity,
)
from finco_parity.schema import SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Helpers: build a fake filesystem rooted at tmp_path
# ---------------------------------------------------------------------------

def _setup_fake_root(tmp_path: Path) -> tuple[Path, Path]:
    """Create fake REPO_ROOT and SNAPSHOTS_DIR under tmp_path."""
    fake_root = tmp_path / "repo"
    snap_dir = fake_root / "finco_parity" / "baselines" / "snapshots"
    snap_dir.mkdir(parents=True)
    return fake_root, snap_dir


def _entry(
    bid: str,
    fake_root: Path,
    *,
    artifact_sha256: str | None = None,
    extra: dict | None = None,
) -> dict:
    """Build a valid manifest entry pointing at fake_root/finco_parity/baselines/snapshots/<bid>.json."""
    snap_path = f"finco_parity/baselines/snapshots/{bid}.json"
    sha = artifact_sha256 or "a" * 64
    e: dict = {
        "baseline_id": bid,
        "project_type_key": "TUHO",
        "project_code": "TUHO-WIND-1",
        "scenario_identity": "Base",
        "engine_designation": "legacy_waterfall_v3",
        "schema_version": SCHEMA_VERSION,
        "baseline_commit_sha": "8b13a53805ea2e1e84144ccad1f2484e16fa8592",
        "input_source_id": "project_factories.create_default_tuho_wind1",
        "capture_source": _CANONICAL_CAPTURE_SOURCE,
        "run_path": "ui_runner.run_demo_project",
        "snapshot_path": snap_path,
        "artifact_sha256": sha,
    }
    if extra:
        e.update(extra)
    return e


def _write_committed_to_fake(bid: str, snap_dir: Path) -> bytes:
    """Copy the real committed artifact to fake snap_dir; return raw bytes."""
    real_path = snapshot_path_for(bid)
    raw = real_path.read_bytes()
    (snap_dir / f"{bid}.json").write_bytes(raw)
    return raw


def _patch_manifest(entries: list[dict], fake_root: Path, snap_dir: Path):
    """Context manager that patches load_manifest, _REPO_ROOT, and SNAPSHOTS_DIR."""
    manifest_data = {"manifest_version": "1.3.0", "baselines": entries}
    return (
        patch("finco_parity.manifest.load_manifest", return_value=manifest_data),
        patch("finco_parity.manifest._REPO_ROOT", fake_root),
        patch("finco_parity.manifest.SNAPSHOTS_DIR", snap_dir),
    )


def _run_with_patches(entries: list[dict], fake_root: Path, snap_dir: Path):
    """Run validate_manifest_integrity under patches."""
    p1, p2, p3 = _patch_manifest(entries, fake_root, snap_dir)
    with p1, p2, p3:
        validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_committed_state_passes_integrity() -> None:
    """The current committed manifest and artifacts pass all integrity checks."""
    validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Missing required fields
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("field", [
    "baseline_id", "project_type_key", "project_code", "scenario_identity",
    "engine_designation", "schema_version", "baseline_commit_sha",
    "input_source_id", "capture_source", "run_path", "snapshot_path",
    "artifact_sha256",
])
def test_missing_required_field_fails(field: str, tmp_path: Path) -> None:
    """A manifest entry missing any required field raises ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    raw = _write_committed_to_fake("tuho", snap_dir)
    sha = hashlib.sha256(raw).hexdigest()
    entry = _entry("tuho", fake_root, artifact_sha256=sha)
    del entry[field]

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match=field):
            validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Missing artifact
# ---------------------------------------------------------------------------

def test_missing_artifact_fails(tmp_path: Path) -> None:
    """An entry pointing to a non-existent file raises ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    # Do NOT write a file — artifact is absent.
    entry = _entry("tuho", fake_root)

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="missing"):
            validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Orphan artifact
# ---------------------------------------------------------------------------

def test_orphan_artifact_fails(tmp_path: Path) -> None:
    """A .json file in snapshots dir not referenced by any entry raises ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    raw = _write_committed_to_fake("tuho", snap_dir)
    sha = hashlib.sha256(raw).hexdigest()
    # Add an extra unreferenced file.
    (snap_dir / "orphan.json").write_bytes(b"{}")
    entry = _entry("tuho", fake_root, artifact_sha256=sha)

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="[Oo]rphan"):
            validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Duplicate baseline_id
# ---------------------------------------------------------------------------

def test_duplicate_baseline_id_fails(tmp_path: Path) -> None:
    """Two entries with the same baseline_id raise ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    raw = _write_committed_to_fake("tuho", snap_dir)
    sha = hashlib.sha256(raw).hexdigest()
    entry1 = _entry("tuho", fake_root, artifact_sha256=sha)
    entry2 = copy.deepcopy(entry1)

    p1, p2, p3 = _patch_manifest([entry1, entry2], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="[Dd]uplicate"):
            validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Duplicate artifact path (two entries with different IDs, same snapshot_path)
# ---------------------------------------------------------------------------

def test_duplicate_artifact_path_fails(tmp_path: Path) -> None:
    """Two entries declaring the same snapshot_path raise ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    raw = _write_committed_to_fake("tuho", snap_dir)
    sha = hashlib.sha256(raw).hexdigest()
    # Also write for oborovo pointing to the same physical file.
    (snap_dir / "oborovo.json").write_bytes(raw)

    entry1 = _entry("tuho", fake_root, artifact_sha256=sha)
    # entry2: different baseline_id but same snapshot_path as entry1.
    entry2 = _entry("oborovo", fake_root, artifact_sha256=sha)
    entry2["snapshot_path"] = "finco_parity/baselines/snapshots/tuho.json"

    p1, p2, p3 = _patch_manifest([entry1, entry2], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="[Dd]uplicate"):
            validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Incorrect SHA-256
# ---------------------------------------------------------------------------

def test_incorrect_sha256_fails(tmp_path: Path) -> None:
    """An entry with a wrong artifact_sha256 raises ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    _write_committed_to_fake("tuho", snap_dir)
    entry = _entry("tuho", fake_root, artifact_sha256="0" * 64)

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="[Ss][Hh][Aa]|hash|mismatch"):
            validate_manifest_integrity()


# ---------------------------------------------------------------------------
# artifact_sha256 wrong format
# ---------------------------------------------------------------------------

def test_artifact_sha256_wrong_format_fails(tmp_path: Path) -> None:
    """A sha256 that is not 64 lowercase hex chars raises ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    _write_committed_to_fake("tuho", snap_dir)
    entry = _entry("tuho", fake_root, artifact_sha256="not-a-hash")

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="sha256|hex"):
            validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Schema version mismatch
# ---------------------------------------------------------------------------

def test_schema_version_mismatch_fails(tmp_path: Path) -> None:
    """Artifact with wrong schema_version raises ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    snap = json.loads(snapshot_path_for("tuho").read_bytes())
    snap["schema_version"] = "0.0.0-wrong"
    bad_bytes = canonical_json_bytes(snap)
    (snap_dir / "tuho.json").write_bytes(bad_bytes)
    sha = hashlib.sha256(bad_bytes).hexdigest()
    entry = _entry("tuho", fake_root, artifact_sha256=sha)

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="schema_version"):
            validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Provenance mismatches
# ---------------------------------------------------------------------------

def _bad_artifact(bid: str, snap_dir: Path, mutations: dict) -> bytes:
    """Write a canonical artifact to snap_dir with *mutations* applied. Return bytes."""
    snap = json.loads(snapshot_path_for(bid).read_bytes())
    for k, v in mutations.items():
        snap[k] = v
    raw = canonical_json_bytes(snap)
    (snap_dir / f"{bid}.json").write_bytes(raw)
    return raw


def test_provenance_baseline_id_mismatch_fails(tmp_path: Path) -> None:
    """Artifact with wrong baseline_id raises ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    raw = _bad_artifact("tuho", snap_dir, {"baseline_id": "oborovo"})
    sha = hashlib.sha256(raw).hexdigest()
    entry = _entry("tuho", fake_root, artifact_sha256=sha)

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="baseline_id"):
            validate_manifest_integrity()


def test_provenance_engine_mismatch_fails(tmp_path: Path) -> None:
    """Artifact with wrong engine_designation raises ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    raw = _bad_artifact("tuho", snap_dir, {"engine_designation": "wrong_engine_v0"})
    sha = hashlib.sha256(raw).hexdigest()
    entry = _entry("tuho", fake_root, artifact_sha256=sha)

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="engine_designation"):
            validate_manifest_integrity()


def test_provenance_commit_sha_mismatch_fails(tmp_path: Path) -> None:
    """Manifest baseline_commit_sha that differs from artifact raises ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    raw = _write_committed_to_fake("tuho", snap_dir)
    sha = hashlib.sha256(raw).hexdigest()
    entry = _entry("tuho", fake_root, artifact_sha256=sha)
    entry["baseline_commit_sha"] = "0" * 40  # manifest says different SHA

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="baseline_commit_sha"):
            validate_manifest_integrity()


def test_provenance_input_source_mismatch_fails(tmp_path: Path) -> None:
    """Manifest input_source_id that differs from artifact raises ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    raw = _write_committed_to_fake("tuho", snap_dir)
    sha = hashlib.sha256(raw).hexdigest()
    entry = _entry("tuho", fake_root, artifact_sha256=sha)
    entry["input_source_id"] = "project_factories.wrong_factory"

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="input_source_id"):
            validate_manifest_integrity()


def test_provenance_run_path_mismatch_fails(tmp_path: Path) -> None:
    """Manifest run_path that differs from snapshot run_path_id raises ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    raw = _write_committed_to_fake("tuho", snap_dir)
    sha = hashlib.sha256(raw).hexdigest()
    entry = _entry("tuho", fake_root, artifact_sha256=sha)
    entry["run_path"] = "wrong.runner.run"

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="run_path"):
            validate_manifest_integrity()


# ---------------------------------------------------------------------------
# capture_source mismatch
# ---------------------------------------------------------------------------

def test_capture_source_mismatch_fails(tmp_path: Path) -> None:
    """Wrong capture_source raises ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    raw = _write_committed_to_fake("tuho", snap_dir)
    sha = hashlib.sha256(raw).hexdigest()
    entry = _entry("tuho", fake_root, artifact_sha256=sha)
    entry["capture_source"] = "some.other.function"

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="capture_source"):
            validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Non-canonical artifact bytes
# ---------------------------------------------------------------------------

def test_non_canonical_artifact_fails(tmp_path: Path) -> None:
    """An artifact whose bytes are not canonical (non-sorted, extra spaces, etc.) fails."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    snap = json.loads(snapshot_path_for("tuho").read_bytes())
    # Write without sort_keys → non-canonical.
    non_canonical = json.dumps(snap, sort_keys=False, indent=2).encode("utf-8") + b"\n"
    (snap_dir / "tuho.json").write_bytes(non_canonical)
    sha = hashlib.sha256(non_canonical).hexdigest()
    entry = _entry("tuho", fake_root, artifact_sha256=sha)

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="canonical"):
            validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Path traversal
# ---------------------------------------------------------------------------

def test_path_traversal_rejected(tmp_path: Path) -> None:
    """An entry with '../' in snapshot_path raises ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    entry = _entry("tuho", fake_root)
    entry["snapshot_path"] = "finco_parity/baselines/snapshots/../../../evil.json"

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="[Ee]scapes|traversal"):
            validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Absolute snapshot_path
# ---------------------------------------------------------------------------

def test_absolute_snapshot_path_rejected(tmp_path: Path) -> None:
    """An entry with an absolute snapshot_path raises ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    entry = _entry("tuho", fake_root)
    entry["snapshot_path"] = "/absolute/path/to/tuho.json"

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="[Rr]elative|absolute"):
            validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Explicit '..' component rejected even if normalization stays inside dir
# ---------------------------------------------------------------------------

def test_explicit_dotdot_component_rejected(tmp_path: Path) -> None:
    """An entry with an explicit '..' path component raises ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    entry = _entry("tuho", fake_root)
    # This would normalize to remain inside snapshots/ but must still be rejected.
    entry["snapshot_path"] = "finco_parity/baselines/snapshots/../snapshots/tuho.json"

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="traversal|escapes"):
            validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Directory path rejected
# ---------------------------------------------------------------------------

def test_directory_snapshot_path_rejected(tmp_path: Path) -> None:
    """An entry whose snapshot_path resolves to a directory raises ManifestIntegrityError."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    # Create a subdirectory inside snap_dir named like a baseline.
    subdir = snap_dir / "tuho"
    subdir.mkdir()
    entry = _entry("tuho", fake_root)
    entry["snapshot_path"] = "finco_parity/baselines/snapshots/tuho"

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="[Dd]irectory"):
            validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Nested orphan discovery via rglob
# ---------------------------------------------------------------------------

def test_nested_orphan_artifact_fails(tmp_path: Path) -> None:
    """A .json file in a subdirectory of snapshots not referenced by any entry fails."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    raw = _write_committed_to_fake("tuho", snap_dir)
    sha = hashlib.sha256(raw).hexdigest()
    entry = _entry("tuho", fake_root, artifact_sha256=sha)

    # Write an orphan in a nested subdirectory.
    nested = snap_dir / "v1"
    nested.mkdir()
    (nested / "orphan.json").write_bytes(b"{}")

    p1, p2, p3 = _patch_manifest([entry], fake_root, snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="[Oo]rphan"):
            validate_manifest_integrity()


# ---------------------------------------------------------------------------
# generation_environment structure validation
# ---------------------------------------------------------------------------

def test_generation_environment_missing_field_fails(tmp_path: Path) -> None:
    """A manifest with generation_environment missing a required field fails integrity."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    raw = _write_committed_to_fake("tuho", snap_dir)
    sha = hashlib.sha256(raw).hexdigest()
    entry = _entry("tuho", fake_root, artifact_sha256=sha)

    manifest_data = {
        "manifest_version": "1.3.0",
        "generation_environment": {
            "python_minor": "3.11",
            # missing constraints_file, numpy_version, pandas_version
        },
        "baselines": [entry],
    }
    p1 = patch("finco_parity.manifest.load_manifest", return_value=manifest_data)
    p2 = patch("finco_parity.manifest._REPO_ROOT", fake_root)
    p3 = patch("finco_parity.manifest.SNAPSHOTS_DIR", snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="generation_environment"):
            validate_manifest_integrity()


def test_generation_environment_not_dict_fails(tmp_path: Path) -> None:
    """A manifest with generation_environment not a dict fails integrity."""
    fake_root, snap_dir = _setup_fake_root(tmp_path)
    raw = _write_committed_to_fake("tuho", snap_dir)
    sha = hashlib.sha256(raw).hexdigest()
    entry = _entry("tuho", fake_root, artifact_sha256=sha)

    manifest_data = {
        "manifest_version": "1.3.0",
        "generation_environment": "not-a-dict",
        "baselines": [entry],
    }
    p1 = patch("finco_parity.manifest.load_manifest", return_value=manifest_data)
    p2 = patch("finco_parity.manifest._REPO_ROOT", fake_root)
    p3 = patch("finco_parity.manifest.SNAPSHOTS_DIR", snap_dir)
    with p1, p2, p3:
        with pytest.raises(ManifestIntegrityError, match="generation_environment"):
            validate_manifest_integrity()
