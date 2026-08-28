"""Golden value tests — fail if KPIs drift materially from known good outputs."""
import pytest
from tests.helpers.offline_calibration import run_project_legacy as run_project  # Phase B4: offline characterization route  # PR-8: legacy characterization route


GOLDEN = {
    ("Solar", "Base"): dict(
        project_irr=0.0896, equity_irr=0.1358,
        min_dscr=1.4421, avg_dscr=1.6502,
        total_revenue_keur=119531.69, total_ebitda_keur=107361.21,
    ),
    ("Solar", "Downside"): dict(
        project_irr=0.0694, equity_irr=0.0897,
        min_dscr=1.3302, avg_dscr=1.5182,
        total_revenue_keur=104754.20, total_ebitda_keur=91366.68,
    ),
    ("Solar", "Upside"): dict(
        project_irr=0.1012, equity_irr=0.1440,
        min_dscr=1.6083, avg_dscr=1.8400,
        total_revenue_keur=127561.16, total_ebitda_keur=115999.21,
    ),
    ("Wind", "Base"): dict(
        project_irr=0.1412, equity_irr=0.1574,
        min_dscr=2.3553, avg_dscr=2.7237,
        total_revenue_keur=265485.88, total_ebitda_keur=247869.62,
    ),
    ("Wind", "Downside"): dict(
        project_irr=0.1172, equity_irr=0.1445,
        min_dscr=1.9061, avg_dscr=2.2064,
        total_revenue_keur=233500.25, total_ebitda_keur=214122.36,
    ),
    ("Wind", "Upside"): dict(
        project_irr=0.1551, equity_irr=0.1654,
        min_dscr=2.6304, avg_dscr=3.0407,
        total_revenue_keur=282566.11, total_ebitda_keur=265830.66,
    ),
}


class TestGoldenValues:
    """Regression tests for KPI drift detection."""

    @pytest.mark.parametrize("project_type,scenario", list(GOLDEN.keys()))
    def test_project_irr_within_tolerance(self, project_type, scenario):
        r = run_project(project_type, scenario)
        expected = GOLDEN[(project_type, scenario)]["project_irr"]
        actual = r["kpis"]["project_irr"]
        diff_bps = abs(actual - expected) * 10000
        assert diff_bps <= 50, (
            f"{project_type} {scenario} project_irr drift: {diff_bps:.0f} bps "
            f"(expected={expected:.4f}, actual={actual:.4f})"
        )

    @pytest.mark.parametrize("project_type,scenario", list(GOLDEN.keys()))
    def test_equity_irr_within_tolerance(self, project_type, scenario):
        r = run_project(project_type, scenario)
        expected = GOLDEN[(project_type, scenario)]["equity_irr"]
        actual = r["kpis"]["equity_irr"]
        diff_bps = abs(actual - expected) * 10000
        assert diff_bps <= 50, (
            f"{project_type} {scenario} equity_irr drift: {diff_bps:.0f} bps "
            f"(expected={expected:.4f}, actual={actual:.4f})"
        )

    @pytest.mark.parametrize("project_type,scenario", list(GOLDEN.keys()))
    def test_min_dscr_within_tolerance(self, project_type, scenario):
        r = run_project(project_type, scenario)
        expected = GOLDEN[(project_type, scenario)]["min_dscr"]
        actual = r["kpis"]["min_dscr"]
        diff = abs(actual - expected)
        assert diff <= 0.15, (
            f"{project_type} {scenario} min_dscr drift: {diff:.4f} "
            f"(expected={expected:.4f}, actual={actual:.4f})"
        )

    @pytest.mark.parametrize("project_type,scenario", list(GOLDEN.keys()))
    def test_avg_dscr_within_tolerance(self, project_type, scenario):
        r = run_project(project_type, scenario)
        expected = GOLDEN[(project_type, scenario)]["avg_dscr"]
        actual = r["kpis"]["avg_dscr"]
        diff = abs(actual - expected)
        assert diff <= 0.15, (
            f"{project_type} {scenario} avg_dscr drift: {diff:.4f} "
            f"(expected={expected:.4f}, actual={actual:.4f})"
        )

    @pytest.mark.parametrize("project_type,scenario", list(GOLDEN.keys()))
    def test_total_revenue_within_tolerance(self, project_type, scenario):
        r = run_project(project_type, scenario)
        expected = GOLDEN[(project_type, scenario)]["total_revenue_keur"]
        actual = r["kpis"]["total_revenue_keur"]
        pct = abs(actual - expected) / expected * 100
        assert pct <= 5.0, (
            f"{project_type} {scenario} total_revenue_keur drift: {pct:.2f}% "
            f"(expected={expected:.2f}, actual={actual:.2f})"
        )

    @pytest.mark.parametrize("project_type,scenario", list(GOLDEN.keys()))
    def test_total_ebitda_within_tolerance(self, project_type, scenario):
        r = run_project(project_type, scenario)
        expected = GOLDEN[(project_type, scenario)]["total_ebitda_keur"]
        actual = r["kpis"]["total_ebitda_keur"]
        pct = abs(actual - expected) / expected * 100
        assert pct <= 5.0, (
            f"{project_type} {scenario} total_ebitda_keur drift: {pct:.2f}% "
            f"(expected={expected:.2f}, actual={actual:.2f})"
        )