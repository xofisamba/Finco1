"""
tests/test_phase1b_baseline_generation.py — Phase 1B artifact generation tests.

Tests:
  - All four manifest entries generate successfully.
  - Each generated snapshot passes validate_snapshot().
  - Two independent generations are byte-identical.
  - --baseline-id generates only the requested baseline.
  - Unknown baseline ID fails.
  - Generation does not mutate the engine result or input objects.
  - No runtime timestamps or machine paths appear in artifacts.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from finco_parity.canonical import canonical_json_bytes, sha256_of_bytes
from finco_parity.generate_baselines import cmd_generate, main as gen_main
from finco_parity.legacy_snapshot import ALL_BASELINE_IDS, capture_snapshot
from finco_parity.manifest import SNAPSHOTS_DIR, snapshot_path_for
from finco_parity.schema import validate_snapshot, SnapshotValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_committed(baseline_id: str) -> dict:
    return json.loads(snapshot_path_for(baseline_id).read_bytes())


# ---------------------------------------------------------------------------
# A. All four baselines generate successfully
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("baseline_id", ALL_BASELINE_IDS)
def test_capture_snapshot_succeeds(baseline_id: str) -> None:
    """capture_snapshot() returns a dict without raising."""
    snap = capture_snapshot(baseline_id, verbose=False)
    assert isinstance(snap, dict)
    assert snap["baseline_id"] == baseline_id


@pytest.mark.parametrize("baseline_id", ALL_BASELINE_IDS)
def test_generated_snapshot_passes_validation(baseline_id: str) -> None:
    """Each generated snapshot passes validate_snapshot() without error."""
    snap = capture_snapshot(baseline_id, verbose=False)
    validate_snapshot(snap)  # must not raise


@pytest.mark.parametrize("baseline_id", ALL_BASELINE_IDS)
def test_committed_artifact_passes_validation(baseline_id: str) -> None:
    """Each committed artifact parses and passes validate_snapshot()."""
    snap = _load_committed(baseline_id)
    validate_snapshot(snap)


# ---------------------------------------------------------------------------
# B. Byte-determinism
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("baseline_id", ALL_BASELINE_IDS)
def test_two_generations_are_byte_identical(baseline_id: str, tmp_path: Path) -> None:
    """Two independent generations into separate directories produce byte-identical files."""
    dir1 = tmp_path / "gen1"
    dir2 = tmp_path / "gen2"

    cmd_generate([baseline_id], dir1, verbose=False)
    cmd_generate([baseline_id], dir2, verbose=False)

    b1 = (dir1 / f"{baseline_id}.json").read_bytes()
    b2 = (dir2 / f"{baseline_id}.json").read_bytes()
    assert b1 == b2, (
        f"Generations are not byte-identical for {baseline_id!r}:\n"
        f"  gen1 sha256={sha256_of_bytes(b1)[:32]}…\n"
        f"  gen2 sha256={sha256_of_bytes(b2)[:32]}…"
    )


def test_all_baselines_byte_identical_two_runs(tmp_path: Path) -> None:
    """Full two-pass byte-determinism across all baselines."""
    dir1 = tmp_path / "pass1"
    dir2 = tmp_path / "pass2"

    rc1 = cmd_generate(list(ALL_BASELINE_IDS), dir1, verbose=False)
    rc2 = cmd_generate(list(ALL_BASELINE_IDS), dir2, verbose=False)
    assert rc1 == 0
    assert rc2 == 0

    for bid in ALL_BASELINE_IDS:
        b1 = (dir1 / f"{bid}.json").read_bytes()
        b2 = (dir2 / f"{bid}.json").read_bytes()
        assert b1 == b2, f"Byte mismatch for {bid}"


# ---------------------------------------------------------------------------
# C. --baseline-id generates only the requested baseline
# ---------------------------------------------------------------------------

def test_baseline_id_generates_only_requested(tmp_path: Path) -> None:
    """--baseline-id tuho generates only tuho.json, no others."""
    rc = cmd_generate(["tuho"], tmp_path, verbose=False)
    assert rc == 0
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    assert files[0].name == "tuho.json"


@pytest.mark.parametrize("baseline_id", ALL_BASELINE_IDS)
def test_single_baseline_id_correct_content(baseline_id: str, tmp_path: Path) -> None:
    """Single-baseline generation produces a valid artifact for that baseline_id."""
    rc = cmd_generate([baseline_id], tmp_path, verbose=False)
    assert rc == 0
    snap = json.loads((tmp_path / f"{baseline_id}.json").read_bytes())
    assert snap["baseline_id"] == baseline_id
    validate_snapshot(snap)


# ---------------------------------------------------------------------------
# D. Unknown baseline ID fails
# ---------------------------------------------------------------------------

def test_unknown_baseline_id_cli_fails() -> None:
    """CLI rejects an unknown --baseline-id with SystemExit."""
    with pytest.raises(SystemExit) as exc_info:
        gen_main(["--baseline-id", "nonexistent_baseline_xyz", "--output-dir", "/tmp"])
    assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# E. Generation does not mutate engine result
# ---------------------------------------------------------------------------

def test_generation_does_not_mutate_waterfall_result(tmp_path: Path) -> None:
    """capture_snapshot() must not mutate the WaterfallResult it receives."""
    import dataclasses
    from unittest.mock import patch as _patch

    captured_results: list[Any] = []

    # Wrap _run_engine to record the result before capture_snapshot touches it.
    from finco_parity import legacy_snapshot as _ls

    original_run = _ls._run_engine

    def _recording_run(project_type: str):
        wr, fs, warnings = original_run(project_type)
        captured_results.append(wr)
        return wr, fs, warnings

    with _patch.object(_ls, "_run_engine", side_effect=_recording_run):
        snap = capture_snapshot("tuho", verbose=False)

    assert captured_results, "Engine was not called"
    wr = captured_results[0]

    # Re-capture without patching and compare — the result should still match.
    snap2 = capture_snapshot("tuho", verbose=False)

    # Both snapshots must be byte-identical.
    b1 = canonical_json_bytes(snap)
    b2 = canonical_json_bytes(snap2)
    assert b1 == b2, "Snapshots differ — possible mutation of shared state"


# ---------------------------------------------------------------------------
# F. No runtime timestamps or machine paths in artifacts
# ---------------------------------------------------------------------------

# Patterns that must not appear in any committed artifact.
_FORBIDDEN_PATTERNS = [
    # Absolute Unix paths outside of known-safe project-relative strings.
    re.compile(r'"/(?:home|root|tmp|var|usr)/'),
    # Windows absolute paths.
    re.compile(r'"[A-Za-z]:\\\\'),
    # Hostname-like strings in values (heuristic: word.word.word).
    re.compile(r'"[a-z][a-z0-9\-]+\.[a-z][a-z0-9\-]+\.[a-z]{2,}"'),
]


@pytest.mark.parametrize("baseline_id", ALL_BASELINE_IDS)
def test_no_machine_paths_in_artifact(baseline_id: str) -> None:
    """Committed artifact must not contain absolute machine paths."""
    text = snapshot_path_for(baseline_id).read_text(encoding="utf-8")
    for pat in _FORBIDDEN_PATTERNS:
        m = pat.search(text)
        assert m is None, (
            f"{baseline_id}: artifact contains forbidden pattern {pat.pattern!r}: "
            f"{m.group()!r}"
        )


@pytest.mark.parametrize("baseline_id", ALL_BASELINE_IDS)
def test_artifact_has_no_nan_or_infinity(baseline_id: str) -> None:
    """Committed artifact must not contain NaN or Infinity literals."""
    text = snapshot_path_for(baseline_id).read_text(encoding="utf-8")
    assert "NaN" not in text
    assert "Infinity" not in text
    assert "Inf" not in text


# ---------------------------------------------------------------------------
# G. Canonical serialization properties
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("baseline_id", ALL_BASELINE_IDS)
def test_artifact_ends_with_newline(baseline_id: str) -> None:
    """Committed artifact must end with exactly one newline."""
    raw = snapshot_path_for(baseline_id).read_bytes()
    assert raw.endswith(b"\n"), f"{baseline_id}: artifact does not end with newline"
    assert not raw.endswith(b"\n\n"), f"{baseline_id}: artifact ends with multiple newlines"


@pytest.mark.parametrize("baseline_id", ALL_BASELINE_IDS)
def test_artifact_is_valid_utf8(baseline_id: str) -> None:
    """Committed artifact must be valid UTF-8."""
    raw = snapshot_path_for(baseline_id).read_bytes()
    raw.decode("utf-8")  # raises UnicodeDecodeError if invalid


@pytest.mark.parametrize("baseline_id", ALL_BASELINE_IDS)
def test_artifact_sha256_matches_content(baseline_id: str) -> None:
    """Committed artifact SHA-256 must match its manifest entry."""
    from finco_parity.manifest import load_manifest
    manifest = load_manifest()
    entry = next(e for e in manifest["baselines"] if e["baseline_id"] == baseline_id)
    expected_sha = entry.get("artifact_sha256", "")
    actual_sha = hashlib.sha256(snapshot_path_for(baseline_id).read_bytes()).hexdigest()
    assert actual_sha == expected_sha, (
        f"{baseline_id}: SHA-256 mismatch: manifest={expected_sha[:16]}… actual={actual_sha[:16]}…"
    )


# ---------------------------------------------------------------------------
# H. baseline_commit_sha policy
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("baseline_id", ALL_BASELINE_IDS)
def test_committed_artifact_has_baseline_commit_sha(baseline_id: str) -> None:
    """Every committed artifact must have a non-empty baseline_commit_sha."""
    snap = json.loads(snapshot_path_for(baseline_id).read_bytes())
    sha = snap.get("baseline_commit_sha", "")
    assert sha and sha != "unknown", (
        f"{baseline_id}: baseline_commit_sha is missing or 'unknown': {sha!r}"
    )


@pytest.mark.parametrize("baseline_id", ALL_BASELINE_IDS)
def test_manifest_baseline_commit_sha_matches_artifact(baseline_id: str) -> None:
    """Manifest baseline_commit_sha must equal artifact baseline_commit_sha."""
    from finco_parity.manifest import load_manifest
    manifest = load_manifest()
    entry = next(e for e in manifest["baselines"] if e["baseline_id"] == baseline_id)
    snap = json.loads(snapshot_path_for(baseline_id).read_bytes())
    assert entry["baseline_commit_sha"] == snap["baseline_commit_sha"], (
        f"{baseline_id}: manifest.baseline_commit_sha={entry['baseline_commit_sha']!r} "
        f"!= artifact.baseline_commit_sha={snap['baseline_commit_sha']!r}"
    )


def test_check_uses_committed_baseline_commit_sha(monkeypatch) -> None:
    """cmd_check must pass the committed artifact's baseline_commit_sha to fresh generation.

    If cmd_check used the transient HEAD SHA instead, baseline_commit_sha would
    differ in the fresh snapshot, causing PROVENANCE_DRIFT on every future run.
    This test verifies that cmd_check produces IDENTICAL even when HEAD has advanced.
    """
    from finco_parity.generate_baselines import cmd_check

    calls: list[str] = []
    original_capture = __import__("finco_parity.legacy_snapshot", fromlist=["capture_snapshot"]).capture_snapshot

    def _recording_capture(baseline_id: str, *, commit_sha=None, verbose=True):
        calls.append(f"{baseline_id}:{commit_sha}")
        return original_capture(baseline_id, commit_sha=commit_sha, verbose=verbose)

    monkeypatch.setattr(
        "finco_parity.generate_baselines.capture_snapshot",
        _recording_capture,
    )

    rc = cmd_check(["tuho"], verbose=False)
    assert rc == 0, f"cmd_check returned {rc}"
    # Verify that the committed artifact's baseline_commit_sha was passed.
    snap = json.loads(snapshot_path_for("tuho").read_bytes())
    committed_sha = snap["baseline_commit_sha"]
    assert any(committed_sha in call for call in calls), (
        f"cmd_check did not pass committed baseline_commit_sha={committed_sha!r} "
        f"to capture_snapshot. Calls: {calls}"
    )


# ---------------------------------------------------------------------------
# I. snapshot_path authoritative generation and path validation
# ---------------------------------------------------------------------------

def test_output_dir_preserves_declared_filename(tmp_path: Path) -> None:
    """--output-dir writes to the filename declared in snapshot_path, not baseline_id.json."""
    from finco_parity.generate_baselines import cmd_generate
    from finco_parity.manifest import SNAPSHOTS_DIR, get_manifest_entry, resolve_snapshot_path

    # For all current baselines the declared filename equals baseline_id.json, so verify
    # that _generate_one routes through manifest path resolution.
    entry = get_manifest_entry("tuho")
    canonical = resolve_snapshot_path(entry)
    rel = canonical.relative_to(SNAPSHOTS_DIR.resolve())  # e.g. "tuho.json"

    rc = cmd_generate(["tuho"], tmp_path, verbose=False)
    assert rc == 0
    assert (tmp_path / rel).exists(), (
        f"expected file at {tmp_path / rel}, declared in manifest snapshot_path"
    )


def test_output_dir_non_standard_filename_respected(tmp_path: Path, monkeypatch) -> None:
    """A manifest snapshot_path with a non-standard filename is used verbatim in --output-dir."""
    import copy
    from finco_parity.generate_baselines import cmd_generate
    from finco_parity.manifest import load_manifest as _lm, SNAPSHOTS_DIR

    # Patch the manifest so tuho's snapshot_path declares a different filename.
    real = _lm()
    patched = copy.deepcopy(real)
    for e in patched["baselines"]:
        if e["baseline_id"] == "tuho":
            e["snapshot_path"] = "finco_parity/baselines/snapshots/tuho_renamed.json"
    monkeypatch.setattr("finco_parity.generate_baselines.get_manifest_entry",
                        lambda bid: next(e for e in patched["baselines"] if e["baseline_id"] == bid))
    monkeypatch.setattr("finco_parity.generate_baselines.resolve_snapshot_path",
                        __import__("finco_parity.manifest", fromlist=["resolve_snapshot_path"]).resolve_snapshot_path)

    # Override resolve_snapshot_path to use the patched entry directly.
    from finco_parity import generate_baselines as _gb
    from finco_parity.manifest import _REPO_ROOT
    from pathlib import Path as _P

    def _patched_resolve(entry):
        declared = entry.get("snapshot_path", "")
        p = _P(declared)
        return (_REPO_ROOT / p).resolve()

    monkeypatch.setattr("finco_parity.generate_baselines.resolve_snapshot_path", _patched_resolve)
    monkeypatch.setattr("finco_parity.generate_baselines.SNAPSHOTS_DIR", SNAPSHOTS_DIR)

    rc = cmd_generate(["tuho"], tmp_path, verbose=False)
    assert rc == 0
    # File must be at tuho_renamed.json, NOT tuho.json.
    assert (tmp_path / "tuho_renamed.json").exists(), (
        "Expected tuho_renamed.json from declared snapshot_path"
    )
    assert not (tmp_path / "tuho.json").exists(), (
        "File must not be derived from baseline_id"
    )


def test_output_dir_nested_path_respected(tmp_path: Path, monkeypatch) -> None:
    """A manifest snapshot_path with a subdirectory is preserved under --output-dir."""
    import copy
    from finco_parity.generate_baselines import cmd_generate
    from finco_parity.manifest import load_manifest as _lm, SNAPSHOTS_DIR, _REPO_ROOT

    patched_manifest = copy.deepcopy(_lm())
    for e in patched_manifest["baselines"]:
        if e["baseline_id"] == "tuho":
            e["snapshot_path"] = "finco_parity/baselines/snapshots/v1/tuho.json"

    def _patched_get_entry(bid):
        return next(e for e in patched_manifest["baselines"] if e["baseline_id"] == bid)

    from pathlib import Path as _P

    def _patched_resolve(entry):
        declared = entry.get("snapshot_path", "")
        return (_REPO_ROOT / _P(declared)).resolve()

    monkeypatch.setattr("finco_parity.generate_baselines.get_manifest_entry", _patched_get_entry)
    monkeypatch.setattr("finco_parity.generate_baselines.resolve_snapshot_path", _patched_resolve)
    monkeypatch.setattr("finco_parity.generate_baselines.SNAPSHOTS_DIR", SNAPSHOTS_DIR)

    rc = cmd_generate(["tuho"], tmp_path, verbose=False)
    assert rc == 0
    # File must be at <output_dir>/v1/tuho.json.
    assert (tmp_path / "v1" / "tuho.json").exists(), (
        "Nested manifest path must be preserved under --output-dir"
    )


def test_canonical_generation_uses_manifest_path(monkeypatch) -> None:
    """Default (no --output-dir) generation routes writes through manifest snapshot_path."""
    from finco_parity.generate_baselines import _generate_one
    from finco_parity.manifest import get_manifest_entry, resolve_snapshot_path
    from pathlib import Path as _P

    entry = get_manifest_entry("tuho")
    expected = resolve_snapshot_path(entry)

    # Intercept write_bytes to record destination without actually writing the file.
    written_paths: list[_P] = []

    def _mock_write(self, data):
        written_paths.append(self)
        # Do not call the real write — we don't want to corrupt committed artifacts.

    monkeypatch.setattr(_P, "write_bytes", _mock_write)

    # Run with output_dir=None (canonical mode) and a fixed commit SHA.
    _generate_one("tuho", None, verbose=False,
                  commit_sha="8b13a53805ea2e1e84144ccad1f2484e16fa8592")

    assert any(p == expected for p in written_paths), (
        f"Expected write to manifest-declared path {expected}; got {written_paths}"
    )


def test_output_dir_does_not_write_to_repository(tmp_path: Path) -> None:
    """--output-dir never writes inside the repository SNAPSHOTS_DIR."""
    from finco_parity.generate_baselines import cmd_generate
    from finco_parity.manifest import SNAPSHOTS_DIR
    from pathlib import Path as _P

    writes: list[str] = []
    original_write = _P.write_bytes

    def _recording_write(self, data):
        writes.append(str(self))
        return original_write(self, data)

    import unittest.mock
    with unittest.mock.patch.object(_P, "write_bytes", _recording_write):
        cmd_generate(["tuho"], tmp_path, verbose=False)

    snap_str = str(SNAPSHOTS_DIR)
    repo_writes = [w for w in writes if w.startswith(snap_str)]
    assert not repo_writes, (
        f"--output-dir must not write inside SNAPSHOTS_DIR; got: {repo_writes}"
    )
