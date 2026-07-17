"""
Phase 1A — Tests for finco_parity.legacy_snapshot runner.

Structure:
  Section A: CLI argument parsing / error paths (no engine execution)
  Section B: capture_snapshot end-to-end for each baseline (engine execution)
  Section C: determinism — two successive runs for one baseline produce identical JSON
  Section D: JSON round-trip
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from finco_parity.legacy_snapshot import (
    ALL_BASELINE_IDS,
    _BASELINE_REGISTRY,
    _serialize_snapshot,
    capture_snapshot,
    main,
)
from finco_parity.schema import validate_snapshot, SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Section A: argument-parsing / error paths (no engine)
# ---------------------------------------------------------------------------

class TestCLIArgParsing:
    def test_unknown_baseline_raises_or_returns_nonzero(self, tmp_path):
        # argparse calls sys.exit(2) for unknown choices — catch SystemExit
        with pytest.raises(SystemExit) as exc_info:
            main(["--baseline", "nonexistent", "--output", str(tmp_path / "out.json")])
        assert exc_info.value.code != 0

    def test_all_without_output_dir_returns_nonzero(self, capsys):
        # argparse error path → SystemExit(2)
        with pytest.raises(SystemExit) as exc_info:
            main(["--all"])
        assert exc_info.value.code != 0

    def test_baseline_without_output_returns_nonzero(self, capsys):
        # argparse error path → SystemExit(2)
        with pytest.raises(SystemExit) as exc_info:
            main(["--baseline", "tuho"])
        assert exc_info.value.code != 0

    def test_capture_snapshot_invalid_baseline_raises(self):
        with pytest.raises(ValueError, match="Unknown baseline_id"):
            capture_snapshot("not_a_real_baseline")

    def test_all_baseline_ids_in_registry(self):
        for bid in ALL_BASELINE_IDS:
            assert bid in _BASELINE_REGISTRY

    def test_registry_has_four_entries(self):
        assert len(_BASELINE_REGISTRY) == 4


# ---------------------------------------------------------------------------
# Section B: end-to-end engine capture
# ---------------------------------------------------------------------------

def _run_capture(baseline_id: str) -> dict[str, Any]:
    return capture_snapshot(baseline_id, commit_sha="test-sha-abc123", verbose=False)


@pytest.mark.parametrize("baseline_id", ALL_BASELINE_IDS)
class TestCaptureSnapshot:
    def test_returns_dict(self, baseline_id):
        snap = _run_capture(baseline_id)
        assert isinstance(snap, dict)

    def test_passes_schema_validation(self, baseline_id):
        snap = _run_capture(baseline_id)
        validate_snapshot(snap)  # must not raise

    def test_schema_version_correct(self, baseline_id):
        snap = _run_capture(baseline_id)
        assert snap["schema_version"] == SCHEMA_VERSION

    def test_baseline_id_matches(self, baseline_id):
        snap = _run_capture(baseline_id)
        assert snap["baseline_id"] == baseline_id

    def test_commit_sha_propagated(self, baseline_id):
        snap = _run_capture(baseline_id)
        assert snap["baseline_commit_sha"] == "test-sha-abc123"

    def test_period_grid_nonempty(self, baseline_id):
        snap = _run_capture(baseline_id)
        assert len(snap["period_grid"]) > 0

    def test_period_grid_sorted(self, baseline_id):
        snap = _run_capture(baseline_id)
        indices = [r["period_index"] for r in snap["period_grid"]]
        assert indices == sorted(indices)

    def test_period_grid_rows_have_period_index(self, baseline_id):
        snap = _run_capture(baseline_id)
        for row in snap["period_grid"]:
            assert "period_index" in row

    def test_operating_schedules_present(self, baseline_id):
        snap = _run_capture(baseline_id)
        assert isinstance(snap["operating_schedules"], dict)

    def test_financing_present(self, baseline_id):
        snap = _run_capture(baseline_id)
        assert isinstance(snap["financing"], dict)
        assert "senior_debt" in snap["financing"]

    def test_returns_present(self, baseline_id):
        snap = _run_capture(baseline_id)
        assert isinstance(snap["returns"], dict)

    def test_warnings_is_list(self, baseline_id):
        snap = _run_capture(baseline_id)
        assert isinstance(snap["warnings"], list)

    def test_no_nan_in_json(self, baseline_id):
        # JSON serialized output must not contain NaN (not valid JSON)
        snap = _run_capture(baseline_id)
        text = _serialize_snapshot(snap)
        assert "NaN" not in text
        assert "Infinity" not in text

    def test_json_round_trips(self, baseline_id):
        snap = _run_capture(baseline_id)
        text = _serialize_snapshot(snap)
        restored = json.loads(text)
        assert restored["baseline_id"] == baseline_id
        assert restored["schema_version"] == SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Section C: determinism
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("baseline_id", ["tuho", "oborovo"])
class TestDeterminism:
    """Two successive runs for frozen-fixture baselines must produce identical JSON."""

    def test_two_runs_identical(self, baseline_id):
        sha = "determinism-test-sha"
        snap_a = capture_snapshot(baseline_id, commit_sha=sha, verbose=False)
        snap_b = capture_snapshot(baseline_id, commit_sha=sha, verbose=False)
        json_a = _serialize_snapshot(snap_a)
        json_b = _serialize_snapshot(snap_b)
        assert json_a == json_b, (
            f"Two runs for {baseline_id!r} produced different JSON. "
            "The snapshot is not deterministic."
        )


# ---------------------------------------------------------------------------
# Section D: CLI file-write integration
# ---------------------------------------------------------------------------

class TestCLIFileWrite:
    def test_single_baseline_writes_file(self, tmp_path):
        out = tmp_path / "tuho.json"
        rc = main(["--baseline", "tuho", "--output", str(out), "--quiet"])
        assert rc == 0
        assert out.exists()
        snap = json.loads(out.read_text(encoding="utf-8"))
        assert snap["baseline_id"] == "tuho"

    def test_all_baselines_write_files(self, tmp_path):
        rc = main(["--all", "--output-dir", str(tmp_path), "--quiet"])
        assert rc == 0
        for bid in ALL_BASELINE_IDS:
            f = tmp_path / f"{bid}.json"
            assert f.exists(), f"Missing output file for baseline {bid!r}"
            snap = json.loads(f.read_text(encoding="utf-8"))
            assert snap["baseline_id"] == bid

    def test_pretty_flag_produces_indented_json(self, tmp_path):
        out = tmp_path / "pretty.json"
        rc = main(["--baseline", "tuho", "--output", str(out), "--quiet", "--pretty"])
        assert rc == 0
        text = out.read_text(encoding="utf-8")
        # Pretty-printed JSON has newlines and indent
        assert "\n" in text
