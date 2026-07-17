"""
tests/test_phase1b_baseline_integrity.py — Manifest ↔ artifact integrity tests.

Tests:
  - Missing artifact fails.
  - Orphan artifact fails.
  - Duplicate baseline_id fails.
  - Duplicate artifact path fails.
  - Incorrect SHA-256 fails.
  - Schema version mismatch fails.
  - Provenance mismatch fails.
  - Path traversal rejected.
  - Artifact outside baseline directory rejected.
  - Happy-path: committed state passes all checks.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from finco_parity.manifest import (
    SNAPSHOTS_DIR,
    ManifestIntegrityError,
    load_manifest,
    snapshot_path_for,
    validate_manifest_integrity,
)
from finco_parity.schema import SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_committed_state_passes_integrity() -> None:
    """The current committed manifest and artifacts pass all integrity checks."""
    validate_manifest_integrity()  # must not raise


# ---------------------------------------------------------------------------
# Helpers — patching manifest and SNAPSHOTS_DIR without touching real files
# ---------------------------------------------------------------------------

def _manifest_with(entries: list[dict]) -> dict:
    """Return a minimal manifest dict with the given entries."""
    return {"manifest_version": "1.2.0", "baselines": entries}


def _good_entry(baseline_id: str = "tuho") -> dict:
    """Return a valid manifest entry pointing at the real committed artifact."""
    manifest = load_manifest()
    return next(e for e in manifest["baselines"] if e["baseline_id"] == baseline_id)


def _with_mock_manifest(entries: list[dict], monkeypatch, tmp_snapshots: Path):
    """Patch load_manifest and SNAPSHOTS_DIR for one test."""
    monkeypatch.setattr(
        "finco_parity.manifest.load_manifest",
        lambda: _manifest_with(entries),
    )
    monkeypatch.setattr("finco_parity.manifest.SNAPSHOTS_DIR", tmp_snapshots)


# ---------------------------------------------------------------------------
# Missing artifact
# ---------------------------------------------------------------------------

def test_missing_artifact_fails(tmp_path: Path) -> None:
    """An entry pointing to a non-existent file raises ManifestIntegrityError."""
    entry = {
        "baseline_id": "tuho",
        "engine_designation": "legacy_waterfall_v3",
        "factory_function": "app.project_factories.create_default_tuho_wind1",
        "artifact_sha256": "aabbcc",
    }
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    # Don't copy any file — artifact is absent.

    with patch("finco_parity.manifest.load_manifest", return_value=_manifest_with([entry])):
        with patch("finco_parity.manifest.SNAPSHOTS_DIR", snap_dir):
            with pytest.raises(ManifestIntegrityError, match="missing"):
                validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Orphan artifact
# ---------------------------------------------------------------------------

def test_orphan_artifact_fails(tmp_path: Path) -> None:
    """A .json file in snapshots dir not referenced by any entry raises ManifestIntegrityError."""
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()

    # Copy one real artifact.
    shutil.copy(snapshot_path_for("tuho"), snap_dir / "tuho.json")
    # Add an extra unreferenced file.
    (snap_dir / "orphan.json").write_text("{}", encoding="utf-8")

    real_entry = _good_entry("tuho")

    with patch("finco_parity.manifest.load_manifest", return_value=_manifest_with([real_entry])):
        with patch("finco_parity.manifest.SNAPSHOTS_DIR", snap_dir):
            with pytest.raises(ManifestIntegrityError, match="[Oo]rphan"):
                validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Duplicate baseline_id
# ---------------------------------------------------------------------------

def test_duplicate_baseline_id_fails(tmp_path: Path) -> None:
    """Two entries with the same baseline_id raise ManifestIntegrityError."""
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    shutil.copy(snapshot_path_for("tuho"), snap_dir / "tuho.json")

    entry = _good_entry("tuho")
    entry2 = copy.deepcopy(entry)

    with patch("finco_parity.manifest.load_manifest", return_value=_manifest_with([entry, entry2])):
        with patch("finco_parity.manifest.SNAPSHOTS_DIR", snap_dir):
            with pytest.raises(ManifestIntegrityError, match="[Dd]uplicate"):
                validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Duplicate artifact path (two entries pointing to same file)
# ---------------------------------------------------------------------------

def test_duplicate_artifact_path_fails(tmp_path: Path) -> None:
    """Two entries pointing to the same artifact file raise ManifestIntegrityError."""
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    shutil.copy(snapshot_path_for("tuho"), snap_dir / "tuho.json")

    entry1 = _good_entry("tuho")
    entry2 = copy.deepcopy(entry1)
    entry2["baseline_id"] = "tuho_copy"  # different id, same snapshot_path

    with patch("finco_parity.manifest.load_manifest", return_value=_manifest_with([entry1, entry2])):
        with patch("finco_parity.manifest.SNAPSHOTS_DIR", snap_dir):
            with pytest.raises(ManifestIntegrityError, match="[Dd]uplicate"):
                validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Incorrect SHA-256
# ---------------------------------------------------------------------------

def test_incorrect_sha256_fails(tmp_path: Path) -> None:
    """An entry with a wrong artifact_sha256 raises ManifestIntegrityError."""
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    shutil.copy(snapshot_path_for("tuho"), snap_dir / "tuho.json")

    entry = _good_entry("tuho")
    entry = dict(entry)
    entry["artifact_sha256"] = "0" * 64  # wrong hash

    with patch("finco_parity.manifest.load_manifest", return_value=_manifest_with([entry])):
        with patch("finco_parity.manifest.SNAPSHOTS_DIR", snap_dir):
            with pytest.raises(ManifestIntegrityError, match="[Ss][Hh][Aa]|hash|mismatch"):
                validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Schema version mismatch
# ---------------------------------------------------------------------------

def test_schema_version_mismatch_fails(tmp_path: Path) -> None:
    """Artifact with wrong schema_version raises ManifestIntegrityError."""
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()

    # Build a modified artifact with a different schema_version.
    snap = json.loads(snapshot_path_for("tuho").read_bytes())
    snap["schema_version"] = "0.0.0-wrong"
    bad_bytes = json.dumps(snap, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    (snap_dir / "tuho.json").write_bytes(bad_bytes)

    entry = _good_entry("tuho")
    entry = dict(entry)
    entry["artifact_sha256"] = hashlib.sha256(bad_bytes).hexdigest()

    with patch("finco_parity.manifest.load_manifest", return_value=_manifest_with([entry])):
        with patch("finco_parity.manifest.SNAPSHOTS_DIR", snap_dir):
            with pytest.raises(ManifestIntegrityError, match="schema_version"):
                validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Provenance mismatch (baseline_id in snapshot != manifest)
# ---------------------------------------------------------------------------

def test_provenance_baseline_id_mismatch_fails(tmp_path: Path) -> None:
    """Artifact whose baseline_id != manifest entry raises ManifestIntegrityError."""
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()

    snap = json.loads(snapshot_path_for("tuho").read_bytes())
    snap["baseline_id"] = "oborovo"  # wrong id
    bad_bytes = json.dumps(snap, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    (snap_dir / "tuho.json").write_bytes(bad_bytes)

    entry = _good_entry("tuho")
    entry = dict(entry)
    entry["artifact_sha256"] = hashlib.sha256(bad_bytes).hexdigest()

    with patch("finco_parity.manifest.load_manifest", return_value=_manifest_with([entry])):
        with patch("finco_parity.manifest.SNAPSHOTS_DIR", snap_dir):
            with pytest.raises(ManifestIntegrityError, match="baseline_id"):
                validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Path traversal rejected
# ---------------------------------------------------------------------------

def test_path_traversal_rejected(tmp_path: Path) -> None:
    """An entry whose baseline_id would resolve to '../outside' raises ManifestIntegrityError."""
    # Create a snapshots dir and place a file one level above it.
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    # We cannot actually set baseline_id to "../something" because snapshot_path_for
    # just does SNAPSHOTS_DIR / f"{baseline_id}.json".
    # Craft a fake that resolves outside SNAPSHOTS_DIR by patching snapshot_path_for.
    outside_file = tmp_path / "outside.json"
    outside_file.write_bytes(b"{}")

    entry = {"baseline_id": "../outside", "engine_designation": "legacy_waterfall_v3"}

    with patch("finco_parity.manifest.load_manifest", return_value=_manifest_with([entry])):
        with patch("finco_parity.manifest.SNAPSHOTS_DIR", snap_dir):
            # snapshot_path_for("../outside") → snap_dir / "../outside.json" → tmp_path/outside.json
            with pytest.raises(ManifestIntegrityError, match="[Ee]scapes|traversal|outside"):
                validate_manifest_integrity()


# ---------------------------------------------------------------------------
# Artifact outside baseline directory
# ---------------------------------------------------------------------------

def test_artifact_outside_baselines_dir_rejected(tmp_path: Path) -> None:
    """snapshot_path_for an id that resolves outside SNAPSHOTS_DIR must be rejected."""
    # Same test as path traversal from a different angle.
    snap_dir = tmp_path / "snapshots"
    snap_dir.mkdir()
    outside = tmp_path / "evil.json"
    outside.write_bytes(b"{}")

    entry = {"baseline_id": "../evil", "engine_designation": "legacy_waterfall_v3"}
    with patch("finco_parity.manifest.load_manifest", return_value=_manifest_with([entry])):
        with patch("finco_parity.manifest.SNAPSHOTS_DIR", snap_dir):
            with pytest.raises(ManifestIntegrityError):
                validate_manifest_integrity()
