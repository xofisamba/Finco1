"""Tests for domain/portfolio/inputs.py."""
import pytest
from domain.portfolio.inputs import (
    AggregationMethod,
    PortfolioInputs,
    ProjectWeight,
)


class TestProjectWeight:
    """Test suite for ProjectWeight."""

    def test_valid_weight(self):
        w = ProjectWeight(name="Solar", weight=0.6, capacity_mw=50.0)
        assert w.name == "Solar"
        assert w.weight == 0.6
        assert w.capacity_mw == 50.0

    def test_weight_default_capacity(self):
        w = ProjectWeight(name="Wind", weight=0.4)
        assert w.capacity_mw is None


class TestPortfolioInputs:
    """Test suite for PortfolioInputs validation."""

    def test_valid_two_project_portfolio(self):
        portfolio = PortfolioInputs(
            name="Test Portfolio",
            projects=(
                ProjectWeight(name="Solar", weight=0.6, capacity_mw=50.0),
                ProjectWeight(name="Wind", weight=0.4, capacity_mw=80.0),
            ),
        )
        assert portfolio.num_projects == 2
        assert portfolio.project_names == ("Solar", "Wind")

    def test_weights_must_sum_to_one(self):
        with pytest.raises(ValueError, match="weights must sum to ~1.0"):
            PortfolioInputs(
                name="Bad Portfolio",
                projects=(
                    ProjectWeight(name="Solar", weight=0.3),
                    ProjectWeight(name="Wind", weight=0.3),
                ),
            )

    def test_each_weight_must_be_positive(self):
        with pytest.raises(ValueError, match="weight must be in"):
            PortfolioInputs(
                name="Bad Portfolio",
                projects=(
                    ProjectWeight(name="Solar", weight=0.0),
                    ProjectWeight(name="Wind", weight=1.0),
                ),
            )

    def test_each_weight_must_be_at_most_one(self):
        with pytest.raises(ValueError, match="weights must sum to ~1.0"):
            PortfolioInputs(
                name="Bad Portfolio",
                projects=(
                    ProjectWeight(name="Solar", weight=1.5),
                ),
            )

    def test_total_weighted_capacity_mw(self):
        portfolio = PortfolioInputs(
            name="Test",
            projects=(
                ProjectWeight(name="Solar", weight=0.6, capacity_mw=50.0),
                ProjectWeight(name="Wind", weight=0.4, capacity_mw=80.0),
            ),
        )
        # 0.6*50 + 0.4*80 = 30 + 32 = 62
        assert portfolio.total_weighted_capacity_mw() == 62.0

    def test_total_weighted_capacity_mw_no_capacity(self):
        """When capacity is None, weight contributes weight value."""
        portfolio = PortfolioInputs(
            name="Test",
            projects=(
                ProjectWeight(name="Solar", weight=0.6, capacity_mw=50.0),
                ProjectWeight(name="Wind", weight=0.4, capacity_mw=None),
            ),
        )
        # 0.6*50 + 0.4*1 = 30 + 0.4
        assert portfolio.total_weighted_capacity_mw() == 30.4

    def test_default_aggregation_method(self):
        portfolio = PortfolioInputs(
            name="Test",
            projects=(ProjectWeight(name="Solar", weight=1.0),),
        )
        assert portfolio.aggregation_method == AggregationMethod.WEIGHTED_AVERAGE

    def test_project_names_tuple(self):
        portfolio = PortfolioInputs(
            name="Test",
            projects=(
                ProjectWeight(name="A", weight=0.5),
                ProjectWeight(name="B", weight=0.5),
            ),
        )
        assert portfolio.project_names == ("A", "B")

    def test_single_project_full_weight(self):
        portfolio = PortfolioInputs(
            name="Solo",
            projects=(ProjectWeight(name="Solo", weight=1.0),),
        )
        assert portfolio.num_projects == 1
        assert portfolio.total_weighted_capacity_mw() == 1.0  # no capacity → weight
