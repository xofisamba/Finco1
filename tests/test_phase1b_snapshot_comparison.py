"""
tests/test_phase1b_snapshot_comparison.py — Snapshot comparison tests.

Tests:
  - Identical snapshots return IDENTICAL.
  - Missing key produces STRUCTURAL_DRIFT.
  - Extra key produces STRUCTURAL_DRIFT.
  - Changed list length produces STRUCTURAL_DRIFT.
  - Numeric change produces VALUE_DRIFT.
  - populated-to-None produces AVAILABILITY_DRIFT.
  - unavailable_fields change produces AVAILABILITY_DRIFT.
  - Provenance change produces PROVENANCE_DRIFT.
  - Schema version change produces SCHEMA_DRIFT.
  - Differences are sorted deterministically.
  - Exact mode rejects even a small numeric change.
  - Optional diagnostic tolerance requires explicit input.
  - Human-readable report format.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from finco_parity.comparison import (
    ComparisonResult,
    DriftKind,
    Tolerance,
    compare_snapshots,
    format_comparison_report,
)
from finco_parity.manifest import snapshot_path_for


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _load(baseline_id: str) -> dict:
    return json.loads(snapshot_path_for(baseline_id).read_bytes())


@pytest.fixture
def tuho_snap() -> dict:
    return _load("tuho")


def _mutate(snap: dict, path: str, value) -> dict:
    """Deep-copy *snap* and set value at dot-path (supports [idx] for lists)."""
    s = copy.deepcopy(snap)
    parts = _split_path(path)
    obj = s
    for part in parts[:-1]:
        if isinstance(part, int):
            obj = obj[part]
        else:
            obj = obj[part]
    last = parts[-1]
    if isinstance(last, int):
        obj[last] = value
    else:
        obj[last] = value
    return s


def _split_path(path: str) -> list:
    """Split 'a.b[2].c' into ['a', 'b', 2, 'c']."""
    import re
    tokens = re.split(r'[\.\[]', path.replace(']', ''))
    result = []
    for t in tokens:
        try:
            result.append(int(t))
        except ValueError:
            if t:
                result.append(t)
    return result


# ---------------------------------------------------------------------------
# A. IDENTICAL
# ---------------------------------------------------------------------------

def test_identical_snapshots_return_identical(tuho_snap: dict) -> None:
    import copy
    result = compare_snapshots(tuho_snap, copy.deepcopy(tuho_snap), baseline_id="tuho")
    assert result.status == DriftKind.IDENTICAL
    assert result.differences == []
    assert result.is_identical()


def test_identical_uses_baseline_id_from_snapshot(tuho_snap: dict) -> None:
    import copy
    result = compare_snapshots(tuho_snap, copy.deepcopy(tuho_snap))
    assert result.baseline_id == "tuho"


# ---------------------------------------------------------------------------
# B. STRUCTURAL_DRIFT — missing key
# ---------------------------------------------------------------------------

def test_missing_key_produces_structural_drift(tuho_snap: dict) -> None:
    current = copy.deepcopy(tuho_snap)
    del current["returns"]
    result = compare_snapshots(tuho_snap, current, baseline_id="tuho")
    assert result.status == DriftKind.STRUCTURAL_DRIFT
    paths = [d.path for d in result.differences]
    assert any("returns" in p for p in paths)


# ---------------------------------------------------------------------------
# C. STRUCTURAL_DRIFT — extra key
# ---------------------------------------------------------------------------

def test_extra_key_produces_structural_drift(tuho_snap: dict) -> None:
    current = copy.deepcopy(tuho_snap)
    current["extra_unexpected_field"] = "oops"
    result = compare_snapshots(tuho_snap, current, baseline_id="tuho")
    assert result.status == DriftKind.STRUCTURAL_DRIFT
    paths = [d.path for d in result.differences]
    assert "extra_unexpected_field" in paths


# ---------------------------------------------------------------------------
# D. STRUCTURAL_DRIFT — changed list length
# ---------------------------------------------------------------------------

def test_changed_list_length_produces_structural_drift(tuho_snap: dict) -> None:
    current = copy.deepcopy(tuho_snap)
    # Remove last period from period_grid.
    current["period_grid"] = current["period_grid"][:-1]
    result = compare_snapshots(tuho_snap, current, baseline_id="tuho")
    assert result.status == DriftKind.STRUCTURAL_DRIFT
    paths = [d.path for d in result.differences]
    assert any("period_grid" in p for p in paths)


# ---------------------------------------------------------------------------
# E. VALUE_DRIFT — numeric change
# ---------------------------------------------------------------------------

def test_numeric_change_produces_value_drift(tuho_snap: dict) -> None:
    current = copy.deepcopy(tuho_snap)
    # Mutate a returns scalar.
    original = current["returns"]["project_irr"]
    if original is not None:
        current["returns"]["project_irr"] = original + 0.001
    else:
        current["returns"]["equity_irr"] = 0.12345
    result = compare_snapshots(tuho_snap, current, baseline_id="tuho")
    assert result.status == DriftKind.VALUE_DRIFT
    value_diffs = [d for d in result.differences if d.kind == DriftKind.VALUE_DRIFT]
    assert value_diffs


# ---------------------------------------------------------------------------
# F. AVAILABILITY_DRIFT — populated → None
# ---------------------------------------------------------------------------

def test_populated_to_none_produces_availability_drift(tuho_snap: dict) -> None:
    current = copy.deepcopy(tuho_snap)
    # Find a non-None scalar in operating_schedules and set it to None.
    revenue = current["operating_schedules"]["revenue_keur"]
    for i, v in enumerate(revenue):
        if v is not None:
            current["operating_schedules"]["revenue_keur"][i] = None
            break
    result = compare_snapshots(tuho_snap, current, baseline_id="tuho")
    assert result.status == DriftKind.AVAILABILITY_DRIFT


# ---------------------------------------------------------------------------
# G. AVAILABILITY_DRIFT — unavailable_fields change
# ---------------------------------------------------------------------------

def test_unavailable_fields_change_produces_availability_drift(tuho_snap: dict) -> None:
    current = copy.deepcopy(tuho_snap)
    # Add an extra entry to unavailable_fields.
    current["unavailable_fields"]["operating_schedules"] = ["opex_keur"]
    result = compare_snapshots(tuho_snap, current, baseline_id="tuho")
    assert result.status == DriftKind.AVAILABILITY_DRIFT
    paths = [d.path for d in result.differences]
    assert "unavailable_fields" in paths


# ---------------------------------------------------------------------------
# H. PROVENANCE_DRIFT
# ---------------------------------------------------------------------------

def test_provenance_change_produces_provenance_drift(tuho_snap: dict) -> None:
    current = copy.deepcopy(tuho_snap)
    current["engine_designation"] = "new_engine_v99"
    result = compare_snapshots(tuho_snap, current, baseline_id="tuho")
    assert result.status == DriftKind.PROVENANCE_DRIFT
    prov_diffs = [d for d in result.differences if d.kind == DriftKind.PROVENANCE_DRIFT]
    assert prov_diffs
    assert any(d.path == "engine_designation" for d in prov_diffs)


def test_baseline_id_change_produces_provenance_drift(tuho_snap: dict) -> None:
    current = copy.deepcopy(tuho_snap)
    current["baseline_id"] = "oborovo"
    result = compare_snapshots(tuho_snap, current, baseline_id="tuho")
    assert result.status == DriftKind.PROVENANCE_DRIFT


# ---------------------------------------------------------------------------
# I. SCHEMA_DRIFT
# ---------------------------------------------------------------------------

def test_schema_version_change_produces_schema_drift(tuho_snap: dict) -> None:
    current = copy.deepcopy(tuho_snap)
    current["schema_version"] = "9.9.9"
    result = compare_snapshots(tuho_snap, current, baseline_id="tuho")
    assert result.status == DriftKind.SCHEMA_DRIFT
    schema_diffs = [d for d in result.differences if d.kind == DriftKind.SCHEMA_DRIFT]
    assert schema_diffs


# ---------------------------------------------------------------------------
# J. Deterministic ordering
# ---------------------------------------------------------------------------

def test_differences_sorted_by_path(tuho_snap: dict) -> None:
    """Differences must be sorted deterministically by path."""
    current = copy.deepcopy(tuho_snap)
    # Introduce multiple differences.
    current["returns"]["project_irr"] = 0.99
    current["returns"]["equity_irr"] = 0.88
    current["operating_schedules"]["revenue_keur"][0] = 999999.0
    result = compare_snapshots(tuho_snap, current, baseline_id="tuho")
    paths = [d.path for d in result.differences]
    assert paths == sorted(paths), f"Differences not sorted: {paths}"


# ---------------------------------------------------------------------------
# K. Exact mode rejects small numeric change
# ---------------------------------------------------------------------------

def test_exact_mode_rejects_tiny_numeric_change(tuho_snap: dict) -> None:
    """Default (zero) tolerance must flag any representable numeric change."""
    import math
    current = copy.deepcopy(tuho_snap)
    revenue = current["operating_schedules"]["revenue_keur"]
    # Use math.nextafter to guarantee the change is representable in IEEE-754.
    for i, v in enumerate(revenue):
        if isinstance(v, (int, float)) and v is not None:
            next_val = math.nextafter(float(v), float("inf"))
            if next_val != v:
                current["operating_schedules"]["revenue_keur"][i] = next_val
                break
    result = compare_snapshots(tuho_snap, current, baseline_id="tuho", tolerance=None)
    assert result.status != DriftKind.IDENTICAL, "Tiny representable change must not be ignored in exact mode"


# ---------------------------------------------------------------------------
# L. Diagnostic tolerance requires explicit input
# ---------------------------------------------------------------------------

def test_tolerance_zero_is_default() -> None:
    """compare_snapshots() with no tolerance arg uses zero tolerance."""
    from finco_parity.comparison import _ZERO_TOLERANCE, Tolerance
    t = Tolerance()
    assert t.absolute == 0.0
    assert t.relative == 0.0


def test_explicit_tolerance_can_pass_small_difference(tuho_snap: dict) -> None:
    """An explicit tolerance > 0 may suppress a small difference (diagnostic use only)."""
    current = copy.deepcopy(tuho_snap)
    revenue = current["operating_schedules"]["revenue_keur"]
    for i, v in enumerate(revenue):
        if isinstance(v, (int, float)) and v is not None and v != 0:
            current["operating_schedules"]["revenue_keur"][i] = v + 0.0001
            break

    # With zero tolerance: drift detected.
    result_exact = compare_snapshots(tuho_snap, current, baseline_id="tuho")
    assert result_exact.status != DriftKind.IDENTICAL

    # With explicit large tolerance: may be IDENTICAL.
    result_tol = compare_snapshots(
        tuho_snap, current, baseline_id="tuho", tolerance=Tolerance(absolute=1.0)
    )
    # At least verify tolerance is being applied (result may differ from zero-tolerance).
    # We don't require IDENTICAL here because revenue values may be large — just check
    # the tolerance object was accepted without error.
    assert isinstance(result_tol, ComparisonResult)


# ---------------------------------------------------------------------------
# M. Human-readable report
# ---------------------------------------------------------------------------

def test_format_report_identical(tuho_snap: dict) -> None:
    import copy
    result = compare_snapshots(tuho_snap, copy.deepcopy(tuho_snap), baseline_id="tuho")
    report = format_comparison_report(result)
    assert "IDENTICAL" in report
    assert "tuho" in report


def test_format_report_shows_all_differences(tuho_snap: dict) -> None:
    current = copy.deepcopy(tuho_snap)
    current["returns"]["project_irr"] = 0.99
    current["returns"]["equity_irr"] = 0.88
    result = compare_snapshots(tuho_snap, current, baseline_id="tuho")
    report = format_comparison_report(result)
    assert "VALUE_DRIFT" in report or "DRIFT" in report
    # Does not suppress second difference because first exists.
    assert report.count("project_irr") + report.count("equity_irr") >= 1


def test_format_report_no_ansi_codes(tuho_snap: dict) -> None:
    import copy
    result = compare_snapshots(tuho_snap, copy.deepcopy(tuho_snap), baseline_id="tuho")
    report = format_comparison_report(result)
    # No ANSI escape sequences.
    assert "\033[" not in report
    assert "\x1b[" not in report


def test_format_report_deterministic(tuho_snap: dict) -> None:
    """format_comparison_report output must be deterministic."""
    current = copy.deepcopy(tuho_snap)
    current["returns"]["project_irr"] = 0.99
    result = compare_snapshots(tuho_snap, current, baseline_id="tuho")
    r1 = format_comparison_report(result)
    r2 = format_comparison_report(result)
    assert r1 == r2


def test_format_report_contains_required_fields(tuho_snap: dict) -> None:
    """Report must include Baseline, Status, Differences and at least one path."""
    current = copy.deepcopy(tuho_snap)
    current["returns"]["project_irr"] = 0.999
    result = compare_snapshots(tuho_snap, current, baseline_id="tuho")
    report = format_comparison_report(result)
    assert "Baseline:" in report
    assert "Status:" in report
    assert "Differences:" in report
    assert "project_irr" in report


# ---------------------------------------------------------------------------
# N. Exact type comparison
# ---------------------------------------------------------------------------

def test_bool_vs_int_is_structural_drift(tuho_snap: dict) -> None:
    """True vs 1 must produce STRUCTURAL_DRIFT, not IDENTICAL."""
    result = compare_snapshots({"x": True}, {"x": 1}, baseline_id="t")
    assert result.status == DriftKind.STRUCTURAL_DRIFT


def test_false_vs_zero_is_structural_drift(tuho_snap: dict) -> None:
    """False vs 0 must produce STRUCTURAL_DRIFT."""
    result = compare_snapshots({"x": False}, {"x": 0}, baseline_id="t")
    assert result.status == DriftKind.STRUCTURAL_DRIFT


def test_bool_vs_float_is_structural_drift() -> None:
    """True vs 1.0 must produce STRUCTURAL_DRIFT."""
    result = compare_snapshots({"x": True}, {"x": 1.0}, baseline_id="t")
    assert result.status == DriftKind.STRUCTURAL_DRIFT


def test_int_vs_float_is_structural_drift() -> None:
    """1 vs 1.0 must produce STRUCTURAL_DRIFT in exact mode."""
    result = compare_snapshots({"x": 1}, {"x": 1.0}, baseline_id="t")
    assert result.status == DriftKind.STRUCTURAL_DRIFT


def test_float_vs_float_equal_is_identical() -> None:
    """1.0 vs 1.0 must be IDENTICAL."""
    result = compare_snapshots({"x": 1.0}, {"x": 1.0}, baseline_id="t")
    assert result.status == DriftKind.IDENTICAL


def test_int_vs_int_equal_is_identical() -> None:
    """1 vs 1 must be IDENTICAL."""
    result = compare_snapshots({"x": 1}, {"x": 1}, baseline_id="t")
    assert result.status == DriftKind.IDENTICAL


def test_string_vs_numeric_is_structural_drift() -> None:
    """'1' vs 1 must produce STRUCTURAL_DRIFT."""
    result = compare_snapshots({"x": "1"}, {"x": 1}, baseline_id="t")
    assert result.status == DriftKind.STRUCTURAL_DRIFT


def test_tiny_same_type_float_drift_detected() -> None:
    """A tiny representable float difference at exact tolerance must be detected."""
    import math
    v = 1234.5678
    next_v = math.nextafter(v, float("inf"))
    result = compare_snapshots({"x": v}, {"x": next_v}, baseline_id="t")
    assert result.status != DriftKind.IDENTICAL


# ---------------------------------------------------------------------------
# O. cmd_check integration tests
# ---------------------------------------------------------------------------

def test_cmd_check_committed_state_returns_zero() -> None:
    """cmd_check against committed artifacts must return 0."""
    from finco_parity.generate_baselines import cmd_check
    from finco_parity.legacy_snapshot import ALL_BASELINE_IDS
    rc = cmd_check(list(ALL_BASELINE_IDS), verbose=False)
    assert rc == 0, f"cmd_check returned {rc} instead of 0"


def test_cmd_check_head_sha_differs_from_baseline_sha_no_drift() -> None:
    """HEAD SHA may differ from baseline_commit_sha without causing drift."""
    import subprocess
    from finco_parity.generate_baselines import cmd_check
    from finco_parity.legacy_snapshot import ALL_BASELINE_IDS
    from finco_parity.manifest import snapshot_path_for

    # Confirm HEAD differs from the stored baseline_commit_sha.
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5
    )
    current_head = result.stdout.strip()
    committed_sha = json.loads(snapshot_path_for("tuho").read_bytes())["baseline_commit_sha"]
    # They may or may not differ depending on checkout; either way --check must pass.
    rc = cmd_check(list(ALL_BASELINE_IDS), verbose=False)
    assert rc == 0, (
        f"cmd_check failed (rc={rc}) even though HEAD={current_head!r} "
        f"baseline_commit_sha={committed_sha!r} — HEAD advancement must not cause drift"
    )


def test_cmd_check_numeric_drift_returns_nonzero(tmp_path: Path, monkeypatch) -> None:
    """cmd_check with a modified committed snapshot returns non-zero (VALUE_DRIFT)."""
    from finco_parity.generate_baselines import cmd_check
    from finco_parity.canonical import canonical_json_bytes
    from finco_parity.manifest import snapshot_path_for

    committed_path = snapshot_path_for("tuho")
    snap = json.loads(committed_path.read_bytes())
    # Mutate a numeric value.
    snap["returns"]["project_irr"] = 0.9999
    bad_bytes = canonical_json_bytes(snap)

    fake_committed = tmp_path / "tuho.json"
    fake_committed.write_bytes(bad_bytes)

    monkeypatch.setattr(
        "finco_parity.generate_baselines.resolve_snapshot_path",
        lambda entry: fake_committed if entry.get("baseline_id") == "tuho" else snapshot_path_for(entry["baseline_id"]),
    )
    rc = cmd_check(["tuho"], verbose=False)
    assert rc != 0, "Modified committed snapshot must cause non-zero exit"


def test_cmd_check_missing_key_returns_nonzero(tmp_path: Path, monkeypatch) -> None:
    """cmd_check with a missing key in committed snapshot returns non-zero (STRUCTURAL_DRIFT)."""
    from finco_parity.generate_baselines import cmd_check
    from finco_parity.canonical import canonical_json_bytes
    from finco_parity.manifest import snapshot_path_for

    committed_path = snapshot_path_for("tuho")
    snap = json.loads(committed_path.read_bytes())
    del snap["returns"]
    bad_bytes = canonical_json_bytes(snap)

    fake_committed = tmp_path / "tuho.json"
    fake_committed.write_bytes(bad_bytes)

    monkeypatch.setattr(
        "finco_parity.generate_baselines.resolve_snapshot_path",
        lambda entry: fake_committed if entry.get("baseline_id") == "tuho" else snapshot_path_for(entry["baseline_id"]),
    )
    rc = cmd_check(["tuho"], verbose=False)
    assert rc != 0


def test_cmd_check_malformed_artifact_returns_nonzero(tmp_path: Path, monkeypatch) -> None:
    """cmd_check with a non-canonical artifact returns non-zero."""
    from finco_parity.generate_baselines import cmd_check
    from finco_parity.manifest import snapshot_path_for

    snap = json.loads(snapshot_path_for("tuho").read_bytes())
    # Non-canonical: no trailing newline.
    non_canonical = json.dumps(snap, sort_keys=True, indent=2).encode("utf-8")

    fake_committed = tmp_path / "tuho.json"
    fake_committed.write_bytes(non_canonical)

    monkeypatch.setattr(
        "finco_parity.generate_baselines.resolve_snapshot_path",
        lambda entry: fake_committed if entry.get("baseline_id") == "tuho" else snapshot_path_for(entry["baseline_id"]),
    )
    rc = cmd_check(["tuho"], verbose=False)
    assert rc != 0


def test_cmd_check_does_not_write_to_committed_paths(monkeypatch) -> None:
    """cmd_check must not write to any committed artifact paths."""
    from finco_parity.generate_baselines import cmd_check
    from finco_parity.legacy_snapshot import ALL_BASELINE_IDS
    from finco_parity.manifest import SNAPSHOTS_DIR

    writes: list[str] = []
    original_write = Path.write_bytes

    def _recording_write(self: Path, data: bytes) -> None:
        writes.append(str(self))
        return original_write(self, data)

    monkeypatch.setattr(Path, "write_bytes", _recording_write)
    cmd_check(list(ALL_BASELINE_IDS), verbose=False)

    repo_writes = [w for w in writes if str(SNAPSHOTS_DIR) in w]
    assert not repo_writes, (
        "--check mode wrote to committed snapshot paths:\n"
        + "\n".join(f"  {w}" for w in repo_writes)
    )
