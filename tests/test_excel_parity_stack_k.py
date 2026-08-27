"""Stack K: KPI serialization tests for app/api/project_runner.py.

Verifies that K2 quick-win changes correctly expose engine-computed fields
in the run_project() response without performing any new financial calculations.
"""
from __future__ import annotations
import os
import sys
import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route


def _run(project_key: str) -> dict:
    return run_project(project_key, "Base")


# ── K2-A: Expanded KPI fields ────────────────────────────────────────────────

class TestKPIFieldsPresent:
    """All newly-added kpi fields must be present (not KeyError) for TUHO and Oborovo."""

    EXPECTED_FIELDS = [
        "total_capex_keur",
        "total_revenue_keur",
        "total_ebitda_keur",
        "total_opex_keur",
        "total_distributions_keur",
        "project_irr",
        "equity_irr",
        "sponsor_irr",
        "project_npv_keur",
        "equity_npv_keur",
        "total_senior_ds_keur",
        "total_shl_service_keur",
        "total_tax_keur",
        "target_dscr",
        "min_dscr",
        "avg_dscr",
        "min_llcr",
        "periods_in_lockup",
    ]

    @pytest.fixture(scope="class")
    def tuho_result(self):
        return _run("TUHO")

    @pytest.fixture(scope="class")
    def oborovo_result(self):
        return _run("Oborovo")

    @pytest.mark.parametrize("field", EXPECTED_FIELDS)
    def test_tuho_kpi_field_present(self, tuho_result, field):
        assert field in tuho_result["kpis"], f"Missing KPI field: {field}"

    @pytest.mark.parametrize("field", EXPECTED_FIELDS)
    def test_oborovo_kpi_field_present(self, oborovo_result, field):
        assert field in oborovo_result["kpis"], f"Missing KPI field: {field}"


class TestKPIFieldValues:
    """Spot-check KPI values are numeric and plausible."""

    @pytest.fixture(scope="class")
    def tuho_kpis(self):
        return _run("TUHO")["kpis"]

    def test_total_capex_positive(self, tuho_kpis):
        v = tuho_kpis["total_capex_keur"]
        assert v is not None and v > 0

    def test_project_irr_plausible(self, tuho_kpis):
        v = tuho_kpis["project_irr"]
        assert v is not None and 0.05 < v < 0.20, f"project_irr out of range: {v}"

    def test_equity_irr_plausible(self, tuho_kpis):
        v = tuho_kpis["equity_irr"]
        assert v is not None and 0.05 < v < 0.30, f"equity_irr out of range: {v}"

    def test_total_senior_ds_positive(self, tuho_kpis):
        v = tuho_kpis["total_senior_ds_keur"]
        assert v is not None and v > 0

    def test_target_dscr_plausible(self, tuho_kpis):
        v = tuho_kpis["target_dscr"]
        assert v is not None and 1.0 < v < 2.0, f"target_dscr out of range: {v}"

    def test_min_llcr_plausible(self, tuho_kpis):
        v = tuho_kpis["min_llcr"]
        # min_llcr may be None if engine does not compute it
        if v is not None:
            assert v > 0, f"min_llcr should be positive: {v}"

    def test_periods_in_lockup_non_negative(self, tuho_kpis):
        v = tuho_kpis["periods_in_lockup"]
        if v is not None:
            assert v >= 0, f"periods_in_lockup should be >= 0: {v}"


# ── K2-B: Debt schedule summary ──────────────────────────────────────────────

class TestDebtScheduleSummary:
    """Debt schedule summary must include min_llcr and periods_in_lockup."""

    @pytest.fixture(scope="class")
    def tuho_debt_summary(self):
        result = _run("Wind")
        return result["debt_schedule"]["summary"]

    def test_summary_has_min_llcr(self, tuho_debt_summary):
        assert "min_llcr" in tuho_debt_summary

    def test_summary_has_periods_in_lockup(self, tuho_debt_summary):
        assert "periods_in_lockup" in tuho_debt_summary

    def test_summary_total_senior_ds_positive(self, tuho_debt_summary):
        v = tuho_debt_summary["total_senior_ds_keur"]
        assert v is not None and v > 0

    def test_summary_actual_avg_dscr_positive(self, tuho_debt_summary):
        v = tuho_debt_summary["actual_avg_dscr"]
        assert v is not None and v > 1.0


# ── K2-C: Distribution source normalization ───────────────────────────────────

class TestDistributionSourceNormalization:
    """distribution_source summary label must never be an empty string."""

    @pytest.fixture(scope="class")
    def tuho_dist_summary(self):
        result = _run("Wind")
        return result["distribution_schedule"]["summary"]

    @pytest.fixture(scope="class")
    def oborovo_dist_summary(self):
        result = _run("Solar")
        return result["distribution_schedule"]["summary"]

    def test_tuho_distribution_source_not_empty(self, tuho_dist_summary):
        src = tuho_dist_summary.get("distribution_source", "")
        assert src != "", "distribution_source must not be empty string"

    def test_oborovo_distribution_source_not_empty(self, oborovo_dist_summary):
        src = oborovo_dist_summary.get("distribution_source", "")
        assert src != "", "distribution_source must not be empty string"

    def test_tuho_distribution_source_valid_value(self, tuho_dist_summary):
        src = tuho_dist_summary.get("distribution_source", "")
        assert src in ("waterfall", "none", "legacy", "da_paid"), (
            f"Unexpected distribution_source: {src!r}"
        )
