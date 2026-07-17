"""
tests/test_phase1c_dual_run.py — Unit tests for Phase 1C dual_run orchestration.

Tests run_candidate_provider and compare_candidate_directory with mocked
dependencies (check_generation_environment, validate_manifest_integrity,
capture_snapshot).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from finco_parity.canonical import canonical_json_bytes
from finco_parity.candidate import (
    CandidateFileNotFoundError,
    CandidateValidationError,
    FileCandidateSnapshotProvider,
    baseline_reference_from_manifest,
)
from finco_parity.dual_run import (
    AggregateRunResult,
    BaselineRunResult,
    BaselineRunStatus,
    compare_candidate_directory,
    compare_candidate_snapshot,
    run_candidate_provider,
)
from finco_parity.manifest import SNAPSHOTS_DIR

pytestmark = pytest.mark.unit

BASELINE_ID = "tuho"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tuho_committed_dict() -> dict:
    path = SNAPSHOTS_DIR / "tuho.json"
    return json.loads(path.read_bytes())


@pytest.fixture()
def tuho_candidate(tuho_committed_dict) -> dict:
    """Valid candidate: same as committed but different engine/run_path."""
    modified = dict(tuho_committed_dict)
    modified["engine_designation"] = "candidate-engine-1"
    modified["run_path_id"] = "candidate-run-1"
    return modified


@pytest.fixture()
def mock_env_ok():
    """Patch check_generation_environment to return None (no error)."""
    with patch("finco_parity.generate_baselines.check_generation_environment", return_value=None) as m:
        yield m


@pytest.fixture()
def mock_manifest_ok():
    """Patch validate_manifest_integrity to do nothing."""
    with patch("finco_parity.manifest.validate_manifest_integrity", return_value=None) as m:
        yield m


# ---------------------------------------------------------------------------
# run_candidate_provider: environment mismatch
# ---------------------------------------------------------------------------

def test_environment_mismatch(tuho_candidate):
    provider = MagicMock()
    provider.capture_snapshot.return_value = tuho_candidate

    with patch("finco_parity.generate_baselines.check_generation_environment", return_value="Python version mismatch"):
        result = run_candidate_provider(BASELINE_ID, provider, verify_legacy=False)

    assert result.status == BaselineRunStatus.ENVIRONMENT_MISMATCH
    assert result.error_message is not None
    assert "Environment" in result.error_message or "mismatch" in result.error_message.lower()


# ---------------------------------------------------------------------------
# run_candidate_provider: manifest integrity failure
# ---------------------------------------------------------------------------

def test_manifest_integrity_failure(tuho_candidate, mock_env_ok):
    provider = MagicMock()
    provider.capture_snapshot.return_value = tuho_candidate

    from finco_parity.manifest import ManifestIntegrityError
    with patch("finco_parity.dual_run.validate_manifest_integrity",
               side_effect=ManifestIntegrityError("bad manifest")):
        result = run_candidate_provider(BASELINE_ID, provider, verify_legacy=False)

    assert result.status == BaselineRunStatus.EXECUTION_ERROR
    assert "Manifest" in result.error_message or "integrity" in result.error_message.lower()


# ---------------------------------------------------------------------------
# run_candidate_provider: unknown baseline_id
# ---------------------------------------------------------------------------

def test_unknown_baseline_id(mock_env_ok, mock_manifest_ok):
    provider = MagicMock()

    result = run_candidate_provider("nonexistent_baseline_xyz", provider, verify_legacy=False)

    assert result.status == BaselineRunStatus.EXECUTION_ERROR
    assert "nonexistent_baseline_xyz" in (result.error_message or "")


# ---------------------------------------------------------------------------
# run_candidate_provider: PASS via compare_candidate_snapshot
# ---------------------------------------------------------------------------

def test_pass_via_compare_candidate_snapshot(tuho_candidate, mock_env_ok, mock_manifest_ok):
    """compare_candidate_snapshot with verify_legacy=False and valid candidate → PASS."""
    result = compare_candidate_snapshot(BASELINE_ID, tuho_candidate, verify_legacy=False)
    assert result.status == BaselineRunStatus.PASS
    assert result.difference_count == 0
    assert result.error_message is None


# ---------------------------------------------------------------------------
# run_candidate_provider: CANDIDATE_MISSING
# ---------------------------------------------------------------------------

def test_candidate_missing(mock_env_ok, mock_manifest_ok):
    provider = MagicMock()
    provider.capture_snapshot.side_effect = CandidateFileNotFoundError("file not found")

    result = run_candidate_provider(BASELINE_ID, provider, verify_legacy=False)
    assert result.status == BaselineRunStatus.CANDIDATE_MISSING


# ---------------------------------------------------------------------------
# run_candidate_provider: IDENTITY_MISMATCH
# ---------------------------------------------------------------------------

def test_identity_mismatch(tuho_candidate, mock_env_ok, mock_manifest_ok):
    """Candidate with wrong baseline_id → IDENTITY_MISMATCH."""
    bad = dict(tuho_candidate)
    bad["baseline_id"] = "wrong_id"

    provider = MagicMock()
    provider.capture_snapshot.return_value = bad

    result = run_candidate_provider(BASELINE_ID, provider, verify_legacy=False)
    assert result.status == BaselineRunStatus.IDENTITY_MISMATCH


# ---------------------------------------------------------------------------
# run_candidate_provider: PAYLOAD_DRIFT
# ---------------------------------------------------------------------------

def test_payload_drift(tuho_candidate, mock_env_ok, mock_manifest_ok):
    """Candidate with modified parity section → PAYLOAD_DRIFT."""
    bad = dict(tuho_candidate)
    # Modify a blocking parity section (financial_statements is a dict) to cause drift
    fs = bad.get("financial_statements", {})
    modified_fs = dict(fs)
    modified_fs["_injected_drift"] = "drift_value_xyz"
    bad["financial_statements"] = modified_fs

    provider = MagicMock()
    provider.capture_snapshot.return_value = bad

    result = run_candidate_provider(BASELINE_ID, provider, verify_legacy=False)
    assert result.status == BaselineRunStatus.PAYLOAD_DRIFT


# ---------------------------------------------------------------------------
# compare_candidate_directory: unknown baseline_id raises ValueError
# ---------------------------------------------------------------------------

def test_compare_candidate_directory_unknown_id(tmp_path, mock_env_ok, mock_manifest_ok):
    with pytest.raises(ValueError, match="Unknown baseline_id"):
        compare_candidate_directory(
            tmp_path,
            baseline_ids=["nonexistent_xyz"],
            verify_legacy=False,
        )


# ---------------------------------------------------------------------------
# BaselineRunResult.to_dict()
# ---------------------------------------------------------------------------

def test_baseline_run_result_to_dict():
    result = BaselineRunResult(
        baseline_id="tuho",
        status=BaselineRunStatus.PASS,
        legacy_engine_designation="legacy_v3",
        candidate_engine_designation="candidate-engine-1",
        legacy_run_path="ui_runner.run",
        candidate_run_path="candidate-run-1",
        comparison_status="IDENTICAL",
        difference_count=0,
        differences=(),
        legacy_warnings=(),
        candidate_warnings=(),
        error_message=None,
    )
    d = result.to_dict()
    assert isinstance(d, dict)
    assert d["baseline_id"] == "tuho"
    assert d["status"] == "PASS"
    assert d["difference_count"] == 0
    assert d["differences"] == []
    assert d["legacy_warnings"] == []
    assert d["candidate_warnings"] == []
    assert d["error_message"] is None


# ---------------------------------------------------------------------------
# AggregateRunResult.to_dict()
# ---------------------------------------------------------------------------

def test_aggregate_run_result_to_dict():
    run_result = BaselineRunResult(
        baseline_id="tuho",
        status=BaselineRunStatus.PASS,
        legacy_engine_designation=None,
        candidate_engine_designation=None,
        legacy_run_path=None,
        candidate_run_path=None,
        comparison_status=None,
        difference_count=0,
        differences=(),
        legacy_warnings=(),
        candidate_warnings=(),
        error_message=None,
    )
    agg = AggregateRunResult(
        selected_baselines=("tuho",),
        passed_baselines=("tuho",),
        failed_baselines=(),
        overall_status=BaselineRunStatus.PASS,
        baseline_results=(run_result,),
    )
    d = agg.to_dict()
    assert isinstance(d, dict)
    assert d["overall_status"] == "PASS"
    assert d["selected_baselines"] == ["tuho"]
    assert d["passed_baselines"] == ["tuho"]
    assert d["failed_baselines"] == []
    assert len(d["baseline_results"]) == 1
    assert isinstance(d["baseline_results"][0], dict)
