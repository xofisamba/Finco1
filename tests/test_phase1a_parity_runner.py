"""
Phase 1A — Tests for finco_parity.legacy_snapshot runner.

Structure:
  Section A: CLI argument parsing / error paths (no engine execution)
  Section B: capture_snapshot end-to-end for each baseline (engine execution)
  Section C: real-value assertions (non-None, non-zero schedules)
  Section D: schedule alignment and correctness
  Section E: determinism — two successive runs produce identical JSON
  Section F: CLI file-write integration
  Section G: import boundary — production modules must not import finco_parity
  Section H: source-object immutability
"""
from __future__ import annotations

import json
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
from finco_parity.schema import validate_snapshot, SCHEMA_VERSION, UNAVAILABLE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _capture(baseline_id: str) -> dict[str, Any]:
    return capture_snapshot(baseline_id, commit_sha="test-sha-phase1a", verbose=False)


def _notnone_count(series: list) -> int:
    return sum(1 for v in series if v is not None)


# ---------------------------------------------------------------------------
# Section A: CLI argument parsing / error paths
# ---------------------------------------------------------------------------

class TestCLIArgParsing:
    def test_unknown_baseline_exits_nonzero(self, tmp_path):
        with pytest.raises(SystemExit) as exc:
            main(["--baseline", "nonexistent", "--output", str(tmp_path / "out.json")])
        assert exc.value.code != 0

    def test_all_without_output_dir_exits_nonzero(self):
        with pytest.raises(SystemExit) as exc:
            main(["--all"])
        assert exc.value.code != 0

    def test_baseline_without_output_exits_nonzero(self):
        with pytest.raises(SystemExit) as exc:
            main(["--baseline", "tuho"])
        assert exc.value.code != 0

    def test_capture_invalid_baseline_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown baseline_id"):
            capture_snapshot("not_a_real_baseline")

    def test_all_baseline_ids_in_registry(self):
        for bid in ALL_BASELINE_IDS:
            assert bid in _BASELINE_REGISTRY

    def test_registry_has_four_entries(self):
        assert len(_BASELINE_REGISTRY) == 4


# ---------------------------------------------------------------------------
# Section B: end-to-end schema validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("baseline_id", ALL_BASELINE_IDS)
class TestCaptureSnapshotSchema:
    def test_returns_dict(self, baseline_id):
        snap = _capture(baseline_id)
        assert isinstance(snap, dict)

    def test_passes_schema_validation(self, baseline_id):
        snap = _capture(baseline_id)
        validate_snapshot(snap)

    def test_schema_version_correct(self, baseline_id):
        snap = _capture(baseline_id)
        assert snap["schema_version"] == SCHEMA_VERSION

    def test_baseline_id_matches(self, baseline_id):
        snap = _capture(baseline_id)
        assert snap["baseline_id"] == baseline_id

    def test_commit_sha_propagated(self, baseline_id):
        snap = _capture(baseline_id)
        assert snap["baseline_commit_sha"] == "test-sha-phase1a"

    def test_period_grid_nonempty(self, baseline_id):
        snap = _capture(baseline_id)
        assert len(snap["period_grid"]) > 0

    def test_period_grid_sorted(self, baseline_id):
        snap = _capture(baseline_id)
        indices = [r["period_index"] for r in snap["period_grid"]]
        assert indices == sorted(indices)

    def test_period_grid_indices_unique(self, baseline_id):
        snap = _capture(baseline_id)
        indices = [r["period_index"] for r in snap["period_grid"]]
        assert len(indices) == len(set(indices))

    def test_period_grid_has_date(self, baseline_id):
        snap = _capture(baseline_id)
        for row in snap["period_grid"]:
            assert "date" in row
            assert row["date"] is not None

    def test_period_grid_is_construction_unavailable(self, baseline_id):
        snap = _capture(baseline_id)
        for row in snap["period_grid"]:
            assert row["is_construction"] is None

    def test_warnings_is_list(self, baseline_id):
        snap = _capture(baseline_id)
        assert isinstance(snap["warnings"], list)

    def test_no_nan_in_json(self, baseline_id):
        snap = _capture(baseline_id)
        text = _serialize_snapshot(snap)
        assert "NaN" not in text
        assert "Infinity" not in text

    def test_json_round_trips(self, baseline_id):
        snap = _capture(baseline_id)
        text = _serialize_snapshot(snap)
        restored = json.loads(text)
        assert restored["baseline_id"] == baseline_id
        assert restored["schema_version"] == SCHEMA_VERSION

    def test_unavailable_fields_present(self, baseline_id):
        snap = _capture(baseline_id)
        assert "unavailable_fields" in snap

    def test_financing_has_llcr(self, baseline_id):
        snap = _capture(baseline_id)
        assert "llcr" in snap["financing"]["senior_debt"]

    def test_financing_llcr_is_list_not_unavailable(self, baseline_id):
        snap = _capture(baseline_id)
        llcr = snap["financing"]["senior_debt"]["llcr"]
        assert isinstance(llcr, list)

    def test_distribution_key_is_singular(self, baseline_id):
        snap = _capture(baseline_id)
        eq = snap["financing"]["equity"]
        assert "distribution_keur" in eq
        assert "distributions_keur" not in eq

    def test_returns_has_total_distribution_keur(self, baseline_id):
        snap = _capture(baseline_id)
        assert "total_distribution_keur" in snap["returns"]

    def test_returns_has_min_llcr(self, baseline_id):
        snap = _capture(baseline_id)
        assert "min_llcr" in snap["returns"]

    def test_returns_has_sponsor_irr(self, baseline_id):
        snap = _capture(baseline_id)
        assert "sponsor_irr" in snap["returns"]


# ---------------------------------------------------------------------------
# Section C: real-value assertions (non-trivial schedules)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("baseline_id", ALL_BASELINE_IDS)
class TestRealValueSchedules:
    def test_production_schedule_has_nonzero_values(self, baseline_id):
        snap = _capture(baseline_id)
        series = snap["operating_schedules"]["production_mwh"]
        assert _notnone_count(series) > 0
        assert any(v is not None and v > 0 for v in series), (
            f"{baseline_id}: production_mwh schedule is all None/zero"
        )

    def test_revenue_schedule_has_nonzero_values(self, baseline_id):
        snap = _capture(baseline_id)
        series = snap["operating_schedules"]["revenue_keur"]
        assert any(v is not None and v > 0 for v in series), (
            f"{baseline_id}: revenue_keur schedule is all None/zero"
        )

    def test_opex_schedule_has_nonzero_values(self, baseline_id):
        snap = _capture(baseline_id)
        series = snap["operating_schedules"]["opex_keur"]
        assert any(v is not None and v > 0 for v in series), (
            f"{baseline_id}: opex_keur schedule is all None/zero"
        )

    def test_ebitda_schedule_has_nonzero_values(self, baseline_id):
        snap = _capture(baseline_id)
        series = snap["operating_schedules"]["ebitda_keur"]
        assert any(v is not None and v != 0 for v in series), (
            f"{baseline_id}: ebitda_keur schedule is all None/zero"
        )

    def test_tax_depreciation_schedule_has_nonzero_values(self, baseline_id):
        snap = _capture(baseline_id)
        series = snap["operating_schedules"]["tax_depreciation_keur"]
        assert any(v is not None and v > 0 for v in series), (
            f"{baseline_id}: tax_depreciation_keur (tax_depreciation_audit_keur) is all None/zero"
        )

    def test_cfads_proxy_has_nonzero_values(self, baseline_id):
        snap = _capture(baseline_id)
        series = snap["tax_and_cfads"]["cf_after_tax_keur"]
        assert any(v is not None and v != 0 for v in series), (
            f"{baseline_id}: cf_after_tax_keur (CFADS proxy) is all None/zero"
        )

    def test_senior_debt_closing_balance_has_nonzero_values(self, baseline_id):
        snap = _capture(baseline_id)
        series = snap["financing"]["senior_debt"]["closing_keur"]
        assert any(v is not None and v > 0 for v in series), (
            f"{baseline_id}: senior_balance_keur is all None/zero"
        )

    def test_dscr_has_nonzero_values(self, baseline_id):
        snap = _capture(baseline_id)
        series = snap["financing"]["senior_debt"]["dscr"]
        assert any(v is not None and v > 0 for v in series), (
            f"{baseline_id}: dscr is all None/zero"
        )

    def test_llcr_has_nonzero_values(self, baseline_id):
        snap = _capture(baseline_id)
        series = snap["financing"]["senior_debt"]["llcr"]
        assert any(v is not None and v > 0 for v in series), (
            f"{baseline_id}: llcr is all None/zero"
        )

    def test_tax_depreciation_audit_series_populated(self, baseline_id):
        snap = _capture(baseline_id)
        series = snap["tax_and_cfads"]["tax_depreciation_audit_keur"]
        assert any(v is not None and v > 0 for v in series), (
            f"{baseline_id}: tax_and_cfads.tax_depreciation_audit_keur is all None/zero"
        )

    def test_returns_project_irr_nonzero(self, baseline_id):
        snap = _capture(baseline_id)
        irr = snap["returns"]["project_irr"]
        assert irr is not None and irr > 0, (
            f"{baseline_id}: project_irr is None or zero"
        )

    def test_returns_total_revenue_nonzero(self, baseline_id):
        snap = _capture(baseline_id)
        rev = snap["returns"]["total_revenue_keur"]
        assert rev is not None and rev > 0


# ---------------------------------------------------------------------------
# Section D: schedule alignment and aggregate consistency
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("baseline_id", ALL_BASELINE_IDS)
class TestScheduleAlignment:
    def test_all_operating_schedule_lengths_match_period_grid(self, baseline_id):
        snap = _capture(baseline_id)
        n = len(snap["period_grid"])
        for key, series in snap["operating_schedules"].items():
            if series is not None and isinstance(series, list):
                assert len(series) == n, (
                    f"{baseline_id}: operating_schedules.{key} length {len(series)} != {n}"
                )

    def test_senior_debt_series_lengths_match_period_grid(self, baseline_id):
        snap = _capture(baseline_id)
        n = len(snap["period_grid"])
        for key, series in snap["financing"]["senior_debt"].items():
            if isinstance(series, list):
                assert len(series) == n, (
                    f"{baseline_id}: financing.senior_debt.{key} length {len(series)} != {n}"
                )

    def test_distribution_series_length_matches_period_grid(self, baseline_id):
        snap = _capture(baseline_id)
        n = len(snap["period_grid"])
        dist = snap["financing"]["equity"]["distribution_keur"]
        if isinstance(dist, list):
            assert len(dist) == n

    def test_total_distribution_approximately_matches_period_sum(self, baseline_id):
        snap = _capture(baseline_id)
        dist_series = snap["financing"]["equity"]["distribution_keur"]
        if not isinstance(dist_series, list):
            pytest.skip("distribution_keur not a list")
        period_sum = sum(v for v in dist_series if v is not None)
        total = snap["returns"]["total_distribution_keur"]
        if total is None:
            pytest.skip("total_distribution_keur unavailable")
        # Allow 1% tolerance for any rounding/wiring differences
        assert abs(period_sum - total) / max(abs(total), 1.0) < 0.01, (
            f"{baseline_id}: period sum {period_sum:.2f} != total_distribution_keur {total:.2f}"
        )


# ---------------------------------------------------------------------------
# Section E: determinism
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("baseline_id", ALL_BASELINE_IDS)
class TestDeterminism:
    """All four baselines must produce identical JSON on two successive runs."""

    def test_two_runs_identical(self, baseline_id):
        sha = "determinism-test-sha-phase1a"
        snap_a = capture_snapshot(baseline_id, commit_sha=sha, verbose=False)
        snap_b = capture_snapshot(baseline_id, commit_sha=sha, verbose=False)
        json_a = _serialize_snapshot(snap_a)
        json_b = _serialize_snapshot(snap_b)
        assert json_a == json_b, (
            f"Two runs for {baseline_id!r} produced different JSON — not deterministic."
        )


# ---------------------------------------------------------------------------
# Section F: CLI file-write integration
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
            assert f.exists(), f"Missing output file for {bid!r}"
            snap = json.loads(f.read_text(encoding="utf-8"))
            assert snap["baseline_id"] == bid

    def test_pretty_flag_produces_indented_json(self, tmp_path):
        out = tmp_path / "pretty.json"
        rc = main(["--baseline", "tuho", "--output", str(out), "--quiet", "--pretty"])
        assert rc == 0
        text = out.read_text(encoding="utf-8")
        assert "\n" in text

    def test_written_json_passes_validation(self, tmp_path):
        out = tmp_path / "oborovo.json"
        rc = main(["--baseline", "oborovo", "--output", str(out), "--quiet"])
        assert rc == 0
        snap = json.loads(out.read_text(encoding="utf-8"))
        validate_snapshot(snap)


# ---------------------------------------------------------------------------
# Section G: import boundary
# ---------------------------------------------------------------------------

class TestImportBoundary:
    """Production modules must not import finco_parity."""

    @pytest.mark.parametrize("module_name", [
        "app.ui_runner",
        "app.waterfall_runner",
        "app.waterfall_core",
        "app.project_factories",
        "app.api.project_runner",
        "app.services.run_service",
    ])
    def test_production_module_does_not_import_finco_parity(self, module_name):
        import importlib
        mod = importlib.import_module(module_name)
        src_file = getattr(mod, "__file__", None)
        if src_file is None:
            pytest.skip(f"No source file for {module_name}")
        src = Path(src_file).read_text(encoding="utf-8")
        assert "finco_parity" not in src, (
            f"Production module {module_name} imports finco_parity — violates boundary"
        )


# ---------------------------------------------------------------------------
# Section H: source-object immutability
# ---------------------------------------------------------------------------

class TestSourceObjectImmutability:
    """capture_snapshot must not mutate WaterfallResult, WaterfallPeriod, or inputs."""

    def test_waterfall_result_not_mutated(self):
        from app.ui_runner import run_demo_project
        demo = run_demo_project("TUHO")
        wr = demo.result
        # Record key aggregate values
        original_irr = wr.project_irr
        original_n_periods = len(wr.periods)
        original_revenue = wr.total_revenue_keur

        # Run snapshot capture
        capture_snapshot("tuho", commit_sha="immutability-test", verbose=False)

        # Verify result unchanged
        assert wr.project_irr == original_irr
        assert len(wr.periods) == original_n_periods
        assert wr.total_revenue_keur == original_revenue

    def test_waterfall_period_not_mutated(self):
        from app.ui_runner import run_demo_project
        demo = run_demo_project("TUHO")
        wr = demo.result
        p0 = wr.periods[0]
        original_revenue = p0.revenue_keur
        original_dscr = p0.dscr

        capture_snapshot("tuho", commit_sha="immutability-test-p", verbose=False)

        assert p0.revenue_keur == original_revenue
        assert p0.dscr == original_dscr
