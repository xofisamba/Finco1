"""Offline book/tax depreciation ledger."""

from domain.depreciation.asset import AssetClassConfig
from domain.depreciation.engine import (
    DepreciationEngine,
    DepreciationEngineInputs,
    DepreciationEngineResult,
    DepreciationAuditRow,
)
from domain.depreciation.ledger import DepreciationLedgerInput, build_depreciation_ledger
from domain.depreciation.result import DepreciationLedgerResult, DepreciationPeriodResult
from domain.depreciation.schedule import (
    DepreciationPolicy,
    straight_line_depreciation_for_period,
)

__all__ = [
    # Legacy
    "AssetClassConfig",
    "DepreciationLedgerInput",
    "DepreciationLedgerResult",
    "DepreciationPeriodResult",
    "DepreciationPolicy",
    "build_depreciation_ledger",
    "straight_line_depreciation_for_period",
    # Canonical engine (this branch)
    "DepreciationEngine",
    "DepreciationEngineInputs",
    "DepreciationEngineResult",
    "DepreciationAuditRow",
]
