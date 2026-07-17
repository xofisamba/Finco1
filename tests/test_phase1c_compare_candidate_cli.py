"""
tests/test_phase1c_compare_candidate_cli.py — Unit tests for compare_candidate CLI.

Tests the CLI argument parsing, exit codes, and report writing.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from finco_parity.compare_candidate import main as cli_main
from finco_parity.dual_run import (
    AggregateRunResult,
    BaselineRunResult,
    BaselineRunStatus,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run_result(baseline_id: str, status: BaselineRunStatus) -> BaselineRunResult:
    return BaselineRunResult(
        baseline_id=baseline_id,
        status=status,
        legacy_engine_designation="legacy_v3",
        candidate_engine_designation="candidate-1",
        legacy_run_path="ui_runner",
        candidate_run_path="candidate-run",
        comparison_status=None,
        difference_count=0,
        differences=(),
        legacy_warnings=(),
        candidate_warnings=(),
        error_message=None if status == BaselineRunStatus.PASS else f"{status.value} error",
    )


def _make_aggregate(status: BaselineRunStatus, baseline_id: str = "tuho") -> AggregateRunResult:
    run_result = _make_run_result(baseline_id, status)
    passed = (baseline_id,) if status == BaselineRunStatus.PASS else ()
    failed = () if status == BaselineRunStatus.PASS else (baseline_id,)
    return AggregateRunResult(
        selected_baselines=(baseline_id,),
        passed_baselines=passed,
        failed_baselines=failed,
        overall_status=status,
        baseline_results=(run_result,),
    )


# ---------------------------------------------------------------------------
# Missing --candidate-dir
# ---------------------------------------------------------------------------

def test_missing_candidate_dir_exits_2():
    with pytest.raises(SystemExit) as exc_info:
        cli_main(["--all"])
    assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# --candidate-dir does not exist
# ---------------------------------------------------------------------------

def test_nonexistent_candidate_dir_exits_2(tmp_path):
    nonexistent = tmp_path / "does_not_exist"
    result = cli_main(["--candidate-dir", str(nonexistent), "--all"])
    assert result == 2


# ---------------------------------------------------------------------------
# Neither --baseline-id nor --all
# ---------------------------------------------------------------------------

def test_neither_baseline_id_nor_all_exits_2(tmp_path):
    with pytest.raises(SystemExit) as exc_info:
        cli_main(["--candidate-dir", str(tmp_path)])
    assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# Both --baseline-id and --all
# ---------------------------------------------------------------------------

def test_both_baseline_id_and_all_exits_2(tmp_path):
    with pytest.raises(SystemExit) as exc_info:
        cli_main(["--candidate-dir", str(tmp_path), "--baseline-id", "tuho", "--all"])
    assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# Unknown --baseline-id
# ---------------------------------------------------------------------------

def test_unknown_baseline_id_exits_2(tmp_path):
    result = cli_main(["--candidate-dir", str(tmp_path), "--baseline-id", "nonexistent_xyz"])
    assert result == 2


# ---------------------------------------------------------------------------
# PASS → exit 0
# ---------------------------------------------------------------------------

def test_all_pass_exits_0(tmp_path):
    agg = _make_aggregate(BaselineRunStatus.PASS)
    with patch("finco_parity.compare_candidate.compare_candidate_directory", return_value=agg):
        result = cli_main(["--candidate-dir", str(tmp_path), "--all", "--quiet"])
    assert result == 0


# ---------------------------------------------------------------------------
# PAYLOAD_DRIFT → exit 3
# ---------------------------------------------------------------------------

def test_payload_drift_exits_3(tmp_path):
    agg = _make_aggregate(BaselineRunStatus.PAYLOAD_DRIFT)
    with patch("finco_parity.compare_candidate.compare_candidate_directory", return_value=agg):
        result = cli_main(["--candidate-dir", str(tmp_path), "--all", "--quiet"])
    assert result == 3


# ---------------------------------------------------------------------------
# CANDIDATE_MISSING → exit 6
# ---------------------------------------------------------------------------

def test_candidate_missing_exits_6(tmp_path):
    agg = _make_aggregate(BaselineRunStatus.CANDIDATE_MISSING)
    with patch("finco_parity.compare_candidate.compare_candidate_directory", return_value=agg):
        result = cli_main(["--candidate-dir", str(tmp_path), "--all", "--quiet"])
    assert result == 6


# ---------------------------------------------------------------------------
# IDENTITY_MISMATCH → exit 7
# ---------------------------------------------------------------------------

def test_identity_mismatch_exits_7(tmp_path):
    agg = _make_aggregate(BaselineRunStatus.IDENTITY_MISMATCH)
    with patch("finco_parity.compare_candidate.compare_candidate_directory", return_value=agg):
        result = cli_main(["--candidate-dir", str(tmp_path), "--all", "--quiet"])
    assert result == 7


# ---------------------------------------------------------------------------
# LEGACY_DRIFT → exit 8
# ---------------------------------------------------------------------------

def test_legacy_drift_exits_8(tmp_path):
    agg = _make_aggregate(BaselineRunStatus.LEGACY_DRIFT)
    with patch("finco_parity.compare_candidate.compare_candidate_directory", return_value=agg):
        result = cli_main(["--candidate-dir", str(tmp_path), "--all", "--quiet"])
    assert result == 8


# ---------------------------------------------------------------------------
# --json-report writes a file
# ---------------------------------------------------------------------------

def test_json_report_written(tmp_path):
    agg = _make_aggregate(BaselineRunStatus.PASS)
    report_path = tmp_path / "report.json"
    with patch("finco_parity.compare_candidate.compare_candidate_directory", return_value=agg):
        cli_main([
            "--candidate-dir", str(tmp_path),
            "--all",
            "--quiet",
            "--json-report", str(report_path),
        ])
    assert report_path.exists()
    data = json.loads(report_path.read_bytes())
    assert "overall_status" in data


# ---------------------------------------------------------------------------
# --text-report writes a file
# ---------------------------------------------------------------------------

def test_text_report_written(tmp_path):
    agg = _make_aggregate(BaselineRunStatus.PASS)
    report_path = tmp_path / "report.txt"
    with patch("finco_parity.compare_candidate.compare_candidate_directory", return_value=agg):
        cli_main([
            "--candidate-dir", str(tmp_path),
            "--all",
            "--quiet",
            "--text-report", str(report_path),
        ])
    assert report_path.exists()
    text = report_path.read_text(encoding="utf-8")
    assert "PASS" in text


# ---------------------------------------------------------------------------
# --check forces verify_legacy=True
# ---------------------------------------------------------------------------

def test_check_forces_verify_legacy(tmp_path):
    """--check mode must pass verify_legacy=True to compare_candidate_directory."""
    agg = _make_aggregate(BaselineRunStatus.PASS)
    captured_kwargs = {}

    def fake_compare(candidate_dir, baseline_ids=None, verify_legacy=True, **kwargs):
        captured_kwargs["verify_legacy"] = verify_legacy
        return agg

    with patch("finco_parity.compare_candidate.compare_candidate_directory", side_effect=fake_compare):
        cli_main([
            "--candidate-dir", str(tmp_path),
            "--all",
            "--quiet",
            "--check",
            "--no-verify-legacy",  # explicitly say no-verify; --check should override
        ])

    assert captured_kwargs.get("verify_legacy") is True
