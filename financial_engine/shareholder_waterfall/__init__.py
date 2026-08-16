"""MVP G2C — Covenant-Gated Shareholder Waterfall.

Adds a DSCR distribution lockup gate on top of G2A/G2B mechanics.

Source authority: extracted fixture (SHA 15a621c4...), Inputs!D223.
  senior_lockup_dscr = 1.10 → generic `distribution_lockup_dscr` parameter.

Gate: if base_dscr < distribution_lockup_dscr → legal_equity_distribution = 0.

G2C_DISTRIBUTION_ACCOUNT_AUTHORITY_INCOMPLETE: The distribution account
(R98 / CF!H108) is not in the extracted source fixture. Per-period locked cash
is tracked but NOT accumulated into a releasing balance. If R98 is extracted
in a future phase, the accumulation/release layer may be added.
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
