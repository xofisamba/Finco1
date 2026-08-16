"""MVP G2C — Covenant-Gated Shareholder Waterfall.

Adds a DSCR distribution lockup gate on top of G2A/G2B mechanics.

Source authority: Oborovo workbook (SHA 15a621c4...), Inputs!D223.
  senior_lockup_dscr = 1.10 → generic `distribution_lockup_dscr` parameter.

Gate: if base_dscr < distribution_lockup_dscr → legal_equity_distribution = 0.
Locked cash tracked as covenant_locked_keur (MVP: no R98 distribution account
accumulation — R98 not in Oborovo extraction).
"""
from financial_engine.shareholder_waterfall.contracts import (
    CovenantGatedWaterfallPeriod,
    CovenantGatedWaterfallResult,
    DistributionGateStatus,
)
from financial_engine.shareholder_waterfall.model import (
    run_project_shareholder_waterfall_model,
)

__all__ = [
    "CovenantGatedWaterfallPeriod",
    "CovenantGatedWaterfallResult",
    "DistributionGateStatus",
    "run_project_shareholder_waterfall_model",
]
