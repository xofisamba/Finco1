"""finco_core.depreciation — Depreciation engine.

V2-4: Authoritative. domain.depreciation.* are compatibility shims.

Covers: book depreciation, tax depreciation, depreciation ledger, tax bridge
integration. Book and tax schedules are maintained separately; the tax schedule
feeds the Croatian CIT taxable income formula.
"""
from finco_core.depreciation.asset import AssetClassConfig
from finco_core.depreciation.schedule import (
    DepreciationPolicy,
    straight_line_depreciation_for_period,
)
from finco_core.depreciation.result import DepreciationPeriodResult, DepreciationLedgerResult
from finco_core.depreciation.ledger import DepreciationLedgerInput, build_depreciation_ledger
from finco_core.depreciation.engine import (
    DepreciationEngineInputs,
    DepreciationEngine,
    DepreciationEngineResult,
)
from finco_core.depreciation.audit import DepreciationAuditRow

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
