"""Phase 7 — OPEX Semiannual Projection Audit tests (Stage 2).

Validates that Python's annual OPEX engine correctly projects to semiannual
periods matching Excel CF!R38. Uses actual-day / day-count convention.
This is an audit/test-only branch — no runtime flag activation.
"""
import csv
import os
import pytest

from collections import defaultdict

from domain.opex.templates.tuho import build_tuho_opex_template
from domain.opex.engine import compute_annual_opex

REPORT_PATH = "reports/phase7_opex_semiannual_projection_audit.csv"


def _build_year_annual():
    """Build year -> annual OPEX total from offline engine."""
    groups = build_tuho_opex_template()
    annual = compute_annual_opex(groups, years=30)
    year_annual = defaultdict(float)
    for g_result in annual.group_results:
        year_annual[g_result.year_index] += g_result.group_total_keur
    return year_annual


def _is_leap_year(year_idx):
    actual_year = 2030 + year_idx - 1
    return (actual_year % 4 == 0 and actual_year % 100 != 0) or (actual_year % 400 == 0)


def _day_fracs(year_idx):
    leap = _is_leap_year(year_idx)
    if leap:
        return (182 / 365, 183 / 365)
    else:
        return (181 / 365, 184 / 365)


class TestReportExists:
    """CSV report must exist."""

    def test_csv_exists(self):
        assert os.path.exists(REPORT_PATH), f"{REPORT_PATH} not found"


class TestPeriodCompleteness:
    """All 60 operating periods must be present."""

    @pytest.fixture
    def rows(self):
        with open(REPORT_PATH, newline="") as f:
            return list(csv.DictReader(f))

    @pytest.fixture
    def year_annual(self):
        return _build_year_annual()

    def test_60_periods_present(self, rows):
        assert len(rows) == 60, f"Expected 60 periods, got {len(rows)}"

    def test_p01_p60_labels_present(self, rows):
        labels = [r["period_label"] for r in rows]
        assert "Y01-H1" in labels, "Y01-H1 not found"
        assert "Y30-H2" in labels, "Y30-H2 not found"

    def test_all_year_indices_1_to_30(self, rows):
        year_indices = sorted(set(int(r["year_index"]) for r in rows))
        assert year_indices == list(range(1, 31)), f"Expected years 1-30, got {year_indices}"

    def test_all_half_years_1_and_2(self, rows):
        half_years = sorted(set(int(r["half_year"]) for r in rows))
        assert half_years == [1, 2], f"Expected halves [1, 2], got {half_years}"


class TestHorizonTotals:
    """Excel and Python annual totals must match known calibration values."""

    @pytest.fixture
    def year_annual(self):
        return _build_year_annual()

    @pytest.fixture
    def rows(self):
        with open(REPORT_PATH, newline="") as f:
            return list(csv.DictReader(f))

    def test_excel_horizon_total(self, rows):
        excel_total = sum(float(r["excel_cf_r38_keur"]) for r in rows)
        assert abs(excel_total - 84674.78) < 1.0, (
            f"Excel CF!R38 horizon total should be ~84,674.78 kEUR, got {excel_total:.2f}"
        )

    def test_python_annual_engine_total(self, year_annual):
        total = sum(year_annual.values())
        assert abs(total - 84674.78) < 1.0, (
            f"Python annual engine total should be ~84,674.78 kEUR, got {total:.2f}"
        )


class TestProjectionMethodPerformance:
    """Actual-day must outperform flat split and pass thresholds."""

    @pytest.fixture
    def rows(self):
        with open(REPORT_PATH, newline="") as f:
            return list(csv.DictReader(f))

    @pytest.fixture
    def year_annual(self):
        return _build_year_annual()

    def _deltas(self, rows, col_key):
        return [float(r[col_key]) for r in rows]

    def _max_abs(self, deltas):
        return max(abs(d) for d in deltas)

    def _sum(self, deltas):
        return sum(deltas)

    def test_actual_day_beats_flat_split(self, rows):
        """Actual-day max abs delta must be smaller than flat split."""
        flat_deltas = self._deltas(rows, "delta_flat_keur")
        actual_deltas = self._deltas(rows, "delta_actual_day_keur")

        flat_max = self._max_abs(flat_deltas)
        actual_max = self._max_abs(actual_deltas)

        assert actual_max < flat_max, (
            f"Actual-day should beat flat split: actual_max={actual_max:.4f} vs flat_max={flat_max:.4f}"
        )

    def test_actual_day_max_delta_under_10k(self, rows):
        """Actual-day max per-period delta must be ≤ 10 kEUR."""
        actual_deltas = self._deltas(rows, "delta_actual_day_keur")
        max_delta = self._max_abs(actual_deltas)
        assert max_delta <= 10.0, f"Actual-day max delta should be ≤ 10 kEUR, got {max_delta:.4f}"

    def test_actual_day_max_delta_under_5k(self, rows):
        """Actual-day max per-period delta should be ≤ 5 kEUR (strict threshold)."""
        actual_deltas = self._deltas(rows, "delta_actual_day_keur")
        max_delta = self._max_abs(actual_deltas)
        assert max_delta <= 5.0, f"Actual-day max delta should be ≤ 5 kEUR strict, got {max_delta:.4f}"

    def test_actual_day_horizon_delta_under_100k(self, rows):
        """Actual-day horizon delta must be ≤ 100 kEUR."""
        actual_deltas = self._deltas(rows, "delta_actual_day_keur")
        horizon = abs(self._sum(actual_deltas))
        assert horizon <= 100.0, f"Actual-day horizon delta should be ≤ 100 kEUR, got {horizon:.4f}"

    def test_flat_split_horizon_delta_under_100k(self, rows):
        """Flat split horizon delta must be ≤ 100 kEUR (horizon always cancels)."""
        flat_deltas = self._deltas(rows, "delta_flat_keur")
        horizon = abs(self._sum(flat_deltas))
        assert horizon <= 100.0, f"Flat split horizon delta should be ≤ 100 kEUR, got {horizon:.4f}"

    def test_actual_day_is_best_for_all_periods(self, rows):
        """Actual-day must be selected as best method for all 60 periods."""
        best_methods = [r["best_method"] for r in rows]
        actual_day_count = best_methods.count("ACTUAL_DAY")
        flat_count = best_methods.count("FLAT")
        assert actual_day_count == 60, (
            f"Actual-day should be best for all periods: ACTUAL_DAY={actual_day_count}, FLAT={flat_count}"
        )


class TestCurrentProjectionConvention:
    """Current projections.py uses actual-day fractions and passes thresholds."""

    @pytest.fixture
    def rows(self):
        with open(REPORT_PATH, newline="") as f:
            return list(csv.DictReader(f))

    def test_current_projection_matches_actual_day(self, rows):
        """Current projection (col 10) must equal actual-day (col 9) for all periods."""
        for r in rows:
            current = float(r["python_current_projection_keur"])
            actual = float(r["python_actual_day_keur"])
            assert abs(current - actual) < 0.0001, (
                f"P{r['period_index']}: current={current} vs actual={actual}"
            )

    def test_current_max_delta_under_10k(self, rows):
        current_deltas = [float(r["delta_current_projection_keur"]) for r in rows]
        max_delta = max(abs(d) for d in current_deltas)
        assert max_delta <= 10.0, f"Current projection max delta should be ≤ 10 kEUR, got {max_delta:.4f}"

    def test_current_max_delta_under_5k(self, rows):
        current_deltas = [float(r["delta_current_projection_keur"]) for r in rows]
        max_delta = max(abs(d) for d in current_deltas)
        assert max_delta <= 5.0, f"Current projection max delta should be ≤ 5 kEUR strict, got {max_delta:.4f}"


class TestStage3RuntimeFlagEligibility:
    """Stage 3 runtime flag is allowed if actual-day passes thresholds."""

    @pytest.fixture
    def rows(self):
        with open(REPORT_PATH, newline="") as f:
            return list(csv.DictReader(f))

    def test_stage3_allowed_per_period_5k(self, rows):
        """Per strict threshold (5 kEUR), Stage 3 runtime flag is allowed."""
        actual_deltas = [float(r["delta_actual_day_keur"]) for r in rows]
        max_delta = max(abs(d) for d in actual_deltas)
        assert max_delta <= 5.0, (
            f"Stage 3 allowed only if actual-day max delta ≤ 5 kEUR strict: got {max_delta:.4f}"
        )

    def test_stage3_allowed_horizon_100k(self, rows):
        """Horizon threshold (100 kEUR), Stage 3 runtime flag is allowed."""
        actual_deltas = [float(r["delta_actual_day_keur"]) for r in rows]
        horizon = abs(sum(actual_deltas))
        assert horizon <= 100.0, (
            f"Stage 3 allowed only if actual-day horizon delta ≤ 100 kEUR: got {horizon:.4f}"
        )