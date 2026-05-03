"""Tests for domain/portfolio/waterfall.py."""
import pytest
from domain.portfolio.inputs import (
    AggregationMethod,
    PortfolioInputs,
    ProjectWeight,
)
from domain.portfolio.waterfall import (
    PortfolioResult,
    run_portfolio_waterfall,
)


class TestRunPortfolioWaterfall:
    """Test suite for run_portfolio_waterfall aggregation."""

    @pytest.fixture
    def two_project_portfolio(self):
        return PortfolioInputs(
            name="Two-Project Portfolio",
            projects=(
                ProjectWeight(name="Solar", weight=0.6, capacity_mw=50.0),
                ProjectWeight(name="Wind", weight=0.4, capacity_mw=80.0),
            ),
        )

    @pytest.fixture
    def two_project_results(self):
        return {
            "Solar": {
                "revenue_keur": 10_000.0,
                "ebitda_keur": 8_000.0,
                "tax_keur": 500.0,
                "project_irr": 0.08,
                "equity_irr": 0.12,
                "sponsor_irr": 0.10,
                "project_npv": 1_500.0,
            },
            "Wind": {
                "revenue_keur": 15_000.0,
                "ebitda_keur": 12_000.0,
                "tax_keur": 800.0,
                "project_irr": 0.10,
                "equity_irr": 0.15,
                "sponsor_irr": 0.13,
                "project_npv": 2_000.0,
            },
        }

    def test_total_revenue_summed(self, two_project_portfolio, two_project_results):
        result = run_portfolio_waterfall(two_project_portfolio, two_project_results)
        assert result.total_revenue_keur == 25_000.0  # 10k + 15k

    def test_total_ebitda_summed(self, two_project_portfolio, two_project_results):
        result = run_portfolio_waterfall(two_project_portfolio, two_project_results)
        assert result.total_ebitda_keur == 20_000.0  # 8k + 12k

    def test_total_tax_summed(self, two_project_portfolio, two_project_results):
        result = run_portfolio_waterfall(two_project_portfolio, two_project_results)
        assert result.total_tax_keur == 1_300.0  # 500 + 800

    def test_avg_irr_weighted(self, two_project_portfolio, two_project_results):
        result = run_portfolio_waterfall(two_project_portfolio, two_project_results)
        # 0.6*0.08 + 0.4*0.10 = 0.048 + 0.04 = 0.088
        assert abs(result.avg_project_irr - 0.088) < 1e-9

    def test_min_max_irr(self, two_project_portfolio, two_project_results):
        result = run_portfolio_waterfall(two_project_portfolio, two_project_results)
        assert result.min_project_irr == 0.08
        assert result.max_project_irr == 0.10

    def test_project_revenues_keur_dict(self, two_project_portfolio, two_project_results):
        result = run_portfolio_waterfall(two_project_portfolio, two_project_results)
        assert result.project_revenues_keur["Solar"] == 10_000.0
        assert result.project_revenues_keur["Wind"] == 15_000.0

    def test_single_project(self):
        portfolio = PortfolioInputs(
            name="Single",
            projects=(ProjectWeight(name="Solar", weight=1.0, capacity_mw=50.0),),
        )
        results = {
            "Solar": {
                "revenue_keur": 8_000.0, "ebitda_keur": 6_000.0,
                "tax_keur": 400.0, "project_irr": 0.09,
                "equity_irr": 0.14, "sponsor_irr": 0.11, "project_npv": 1_200.0,
            },
        }
        result = run_portfolio_waterfall(portfolio, results)
        assert result.total_revenue_keur == 8_000.0
        assert result.avg_project_irr == 0.09
        assert result.min_project_irr == result.max_project_irr == 0.09

    def test_missing_project_in_results(self):
        """Missing project is skipped (not error)."""
        portfolio = PortfolioInputs(
            name="Test",
            projects=(
                ProjectWeight(name="Solar", weight=0.7),
                ProjectWeight(name="Wind", weight=0.3),
            ),
        )
        results = {
            "Solar": {
                "revenue_keur": 10_000.0, "ebitda_keur": 8_000.0,
                "tax_keur": 500.0, "project_irr": 0.08,
                "equity_irr": 0.12, "sponsor_irr": 0.10, "project_npv": 1_500.0,
            },
            # Wind missing
        }
        result = run_portfolio_waterfall(portfolio, results)
        assert result.total_revenue_keur == 10_000.0
        # IRR falls back to Solar only (weight 0.7/0.7 = 1.0)
        assert result.avg_project_irr == 0.08

    def test_zero_irr_skipped_from_min_max(self):
        """A project with 0 IRR is included in results but skipped for min/max."""
        portfolio = PortfolioInputs(
            name="Test",
            projects=(
                ProjectWeight(name="A", weight=0.5),
                ProjectWeight(name="B", weight=0.5),
            ),
        )
        results = {
            "A": {"revenue_keur": 1000, "ebitda_keur": 800, "tax_keur": 50,
                  "project_irr": 0.10, "equity_irr": 0.0, "sponsor_irr": 0.0, "project_npv": 0},
            "B": {"revenue_keur": 1000, "ebitda_keur": 800, "tax_keur": 50,
                  "project_irr": 0.08, "equity_irr": 0.0, "sponsor_irr": 0.0, "project_npv": 0},
        }
        result = run_portfolio_waterfall(portfolio, results)
        assert result.min_project_irr == 0.08
        assert result.max_project_irr == 0.10

    def test_empty_project_results(self):
        portfolio = PortfolioInputs(
            name="Empty",
            projects=(ProjectWeight(name="Solar", weight=1.0),),
        )
        result = run_portfolio_waterfall(portfolio, {})  # no results
        assert result.total_revenue_keur == 0.0
        assert result.avg_project_irr == 0.0


class TestPortfolioResult:
    """Test suite for PortfolioResult dataclass."""

    def test_portfolio_result_has_required_fields(self):
        result = PortfolioResult(
            project_revenues_keur={"A": 100.0},
            project_ebitdas_keur={"A": 80.0},
            project_irr={"A": 0.08},
            project_npv={"A": 50.0},
            total_revenue_keur=100.0,
            total_ebitda_keur=80.0,
            total_tax_keur=10.0,
            avg_project_irr=0.08,
            min_project_irr=0.08,
            max_project_irr=0.08,
            equity_irr=0.0,
            sponsor_irr=0.0,
            capacity_weighted_irr=0.08,
        )
        assert result.avg_project_irr == 0.08
        assert result.capacity_weighted_irr == 0.08
