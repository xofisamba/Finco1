"""Phase 6 Depreciation Offline Engine — domain/depreciation_offline package."""

from domain.depreciation_offline.config import DepreciationConfig, DepreciationTemplate
from domain.depreciation_offline.categories import AssetCategoryRule
from domain.depreciation_offline.result import DepreciationScheduleEntry, DepreciationScheduleResult
from domain.depreciation_offline.engine import DepreciationEngine, aggregate

__all__ = [
    "DepreciationConfig",
    "DepreciationTemplate",
    "AssetCategoryRule",
    "DepreciationScheduleEntry",
    "DepreciationScheduleResult",
    "DepreciationEngine",
    "aggregate",
]