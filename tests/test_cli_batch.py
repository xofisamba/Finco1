"""Tests for CLI batch runner."""
import json
import subprocess
import tempfile
from pathlib import Path


def test_batch_runs_multiple_projects():
    """Batch JSON with multiple projects runs successfully."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump([
            {"project_type": "Solar", "scenario": "Base"},
            {"project_type": "Wind", "scenario": "Base"},
        ], f)
        input_path = f.name

    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        output_path = f.name

    try:
        result = subprocess.run(
            ['python3', '-m', 'app.cli', 'batch', '--input', input_path, '--output', output_path],
            capture_output=True, text=True, timeout=120
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        with open(output_path) as f:
            data = json.load(f)

        assert len(data) == 2
        assert data[0]["status"] == "success"
        assert data[1]["status"] == "success"
    finally:
        Path(input_path).unlink(missing_ok=True)
        Path(output_path).unlink(missing_ok=True)


def test_batch_invalid_project_continues():
    """Invalid project does not crash batch (fail_fast=False)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump([
            {"project_type": "Solar", "scenario": "Base"},
            {"project_type": "InvalidType", "scenario": "Base"},
        ], f)
        input_path = f.name

    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        output_path = f.name

    try:
        result = subprocess.run(
            ['python3', '-m', 'app.cli', 'batch', '--input', input_path, '--output', output_path],
            capture_output=True, text=True, timeout=120
        )
        # Should not crash
        assert result.returncode == 0

        with open(output_path) as f:
            data = json.load(f)

        assert data[0]["status"] == "success"
        assert data[1]["status"] == "failed"
        assert "error" in data[1]
    finally:
        Path(input_path).unlink(missing_ok=True)
        Path(output_path).unlink(missing_ok=True)


def test_batch_single_run_unchanged():
    """Existing single-run CLI still works."""
    result = subprocess.run(
        ['python3', '-m', 'app.cli', 'run', '--project', 'Solar', '--scenario', 'Base'],
        capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0
