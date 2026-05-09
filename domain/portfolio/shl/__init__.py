"""Phase 4A SHL (Subordinated HoldCo Loan) domain — data model and engine.

No sculpting. No capitalization. No circular funding. No tax optimization.
Pure architectural foundation for intercompany loan upstreaming.
"""
from __future__ import annotations

from domain.portfolio.shl.inputs import (
    SHLFacility,
    SHLPortfolioInputs,
)
from domain.portfolio.shl.result import (
    SHLPeriodResult,
    SHLFacilityResult,
    SHLPortfolioResult,
)
from domain.portfolio.shl.runner import (
    run_shl_facility,
    run_shl_portfolio,
)

__all__ = [
    "SHLFacility",
    "SHLPortfolioInputs",
    "SHLPeriodResult",
    "SHLFacilityResult",
    "SHLPortfolioResult",
    "run_shl_facility",
    "run_shl_portfolio",
]