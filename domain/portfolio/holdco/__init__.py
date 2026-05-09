"""Phase 3A HoldCo domain skeleton.

Planning only. No SHL. No tax template. No cash flow calculations yet.
No Excel export. No UI. Pure dataclass + validation layer.
"""
from __future__ import annotations

from domain.portfolio.holdco.inputs import (
    HoldCoInputs,
    HoldCoEntity,
    SPVOwnership,
    HoldCoOpexInputs,
)
from domain.portfolio.holdco.result import (
    HoldCoResult,
    HoldCoPeriodResult,
    HoldCoSPVContribution,
)

__all__ = [
    "HoldCoInputs",
    "HoldCoEntity",
    "SPVOwnership",
    "HoldCoOpexInputs",
    "HoldCoResult",
    "HoldCoPeriodResult",
    "HoldCoSPVContribution",
]