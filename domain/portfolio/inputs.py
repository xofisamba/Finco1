"""Portfolio inputs — multiple projects with weighting and aggregation."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AggregationMethod(Enum):
    """How to aggregate metrics across portfolio projects."""
    WEIGHTED_AVERAGE = "weighted_average"
    SUM = "sum"
    MEDIAN = "median"


@dataclass(frozen=True)
class ProjectWeight:
    """Weight and metadata for a single project in a portfolio."""
    name: str
    weight: float  # 0.0 to 1.0 (weights should sum to 1.0 across portfolio)
    capacity_mw: Optional[float] = None  # used for capacity-weighted aggregation


@dataclass(frozen=True)
class PortfolioInputs:
    """Root immutable portfolio input object.

    A portfolio aggregates multiple project scenarios or asset classes.
    """
    name: str
    projects: tuple[ProjectWeight, ...]
    aggregation_method: AggregationMethod = AggregationMethod.WEIGHTED_AVERAGE
    # Portfolio-level revenue assumptions (applied before project-specific)
    portfolio_ppa_base_tariff_eur_mwh: float = 0.0
    portfolio_ppa_escalation: float = 0.02
    # Optional portfolio-level BESS aggregation
    aggregate_bess: bool = False

    def __post_init__(self):
        """Validate weights sum to ~1.0."""
        total = sum(p.weight for p in self.projects)
        if not (0.99 <= total <= 1.01):
            raise ValueError(
                f"Portfolio weights must sum to ~1.0, got {total:.4f} "
                f"(projects: {[p.name for p in self.projects]})"
            )
        for p in self.projects:
            if not (0.0 < p.weight <= 1.0):
                raise ValueError(
                    f"Each project weight must be in (0, 1], got {p.weight} for {p.name}"
                )

    def total_weighted_capacity_mw(self) -> float:
        """Weighted sum of capacities across projects."""
        total = 0.0
        for proj in self.projects:
            if proj.capacity_mw is not None:
                total += proj.weight * proj.capacity_mw
            else:
                # If no capacity given, treat as equal weight for this project
                total += proj.weight
        return total

    @property
    def project_names(self) -> tuple[str, ...]:
        return tuple(p.name for p in self.projects)

    @property
    def num_projects(self) -> int:
        return len(self.projects)


__all__ = [
    "AggregationMethod",
    "ProjectWeight",
    "PortfolioInputs",
]
