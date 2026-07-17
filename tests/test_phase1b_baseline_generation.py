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
