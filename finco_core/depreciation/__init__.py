"""
finco_core.depreciation — Depreciation engine.

Extraction target (V2-3): book depreciation, tax depreciation, depreciation
ledger, tax bridge integration. Book and tax schedules are maintained
separately; the tax schedule feeds the Croatian CIT taxable income formula.

Source: domain/depreciation/, domain/depreciation_offline/

V2-3: Forward shims to domain depreciation modules.
"""
from domain.depreciation import (
    AssetClassConfig,
    DepreciationLedgerInput,
    DepreciationLedgerResult,
    DepreciationPeriodResult,
    DepreciationPolicy,
    build_depreciation_ledger,
    straight_line_depreciation_for_period,
    DepreciationEngine,
    DepreciationEngineInputs,
    DepreciationEngineResult,
    DepreciationAuditRow,
)

__all__ = [
    "AssetClassConfig",
    "DepreciationPolicy",
    "straight_line_depreciation_for_period",
    "DepreciationPeriodResult",
    "DepreciationLedgerResult",
    "DepreciationLedgerInput",
    "build_depreciation_ledger",
    "DepreciationEngineInputs",
    "DepreciationEngine",
    "DepreciationEngineResult",
    "DepreciationAuditRow",
]
