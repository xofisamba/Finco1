"""Phase 5D.1 distribution constraint data models.

Data-model-only foundation for distribution constraint evaluation.
No waterfall changes. No distribution blocking. No enforcement.

This package provides:
- DistributionBlockReason enum
- DistributionConstraintConfig dataclass
- DistributionConstraintPeriod result dataclass
- DistributionConstraintResult result dataclass
- evaluate_distribution_constraints() pure helper
"""
from __future__ import annotations

from domain.portfolio.distribution_constraints.inputs import (
    DistributionBlockReason,
    DistributionConstraintConfig,
)
from domain.portfolio.distribution_constraints.result import (
    DistributionConstraintPeriod,
    DistributionConstraintResult,
)
from domain.portfolio.distribution_constraints.runner import (
    evaluate_distribution_constraints,
)

__all__ = [
    "DistributionBlockReason",
    "DistributionConstraintConfig",
    "DistributionConstraintPeriod",
    "DistributionConstraintResult",
    "evaluate_distribution_constraints",
]