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
from domain.portfolio.distribution_constraints.integration import (
    cash_available_by_period_from_entity_ledger,
    requested_distributions_from_entity_ledger,
    evaluate_constraints_from_entity_ledger,
    evaluate_constraints_from_portfolio_ledger,
)
from domain.portfolio.distribution_constraints.overlay import (
    SPVRetainedCashPeriod,
    SPVRetainedCashOverlay,
    build_spv_retained_cash_overlay,
    build_spv_retained_cash_overlays_from_portfolio_ledger,
)

__all__ = [
    "DistributionBlockReason",
    "DistributionConstraintConfig",
    "DistributionConstraintPeriod",
    "DistributionConstraintResult",
    "evaluate_distribution_constraints",
    "cash_available_by_period_from_entity_ledger",
    "requested_distributions_from_entity_ledger",
    "evaluate_constraints_from_entity_ledger",
    "evaluate_constraints_from_portfolio_ledger",
    "SPVRetainedCashPeriod",
    "SPVRetainedCashOverlay",
    "build_spv_retained_cash_overlay",
    "build_spv_retained_cash_overlays_from_portfolio_ledger",
]