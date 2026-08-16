"""G2C contracts — typed covenant-gated shareholder waterfall results.

Source authority: Oborovo workbook (SHA 15a621c4...), Inputs!D223
  senior_lockup_dscr = 1.10 → generic distribution_lockup_dscr parameter.

R-row mapping (Oborovo CF sheet, extracted in excel_oborovo_financial_truth.json):
  R84  free_cash_flow_for_junior_keur  → signed_post_senior (pre-DSRA; see note)
  R102 free_cash_flow_for_shl_keur     → post-SHL available for distributions
  R99  free_cash_flow_for_dividends    → covenant-gated legal_equity_distribution_keur

MVP LIMITATIONS:
  R98 (distribution account balance / carryforward) is NOT in the Oborovo
  extraction — covenant_locked_keur is tracked but NOT accumulated into a
  releasing distribution account. If and when R98 is extracted and source-proven,
  a G2C+ phase may add the accumulation/release layer.

  Post-senior cash is pre-DSRA. The clean engine explicitly marks
  cash_after_senior_before_reserves_keur as pre-reserve (DSRA ordering
  unresolved). G2C inherits this limitation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from financial_engine.financing.contracts import ProjectFinancingResult
from financial_engine.sponsor_returns.contracts import ReturnMetricStatus


class DistributionGateStatus(Enum):
    """Per-period distribution gate evaluation result.

    Source: Oborovo Inputs!D223 → generic lockup_dscr threshold.
    """
    OPEN = "open"
    LOCKED_DSCR_BELOW_LOCKUP = "locked_dscr_below_lockup"
    DSCR_UNAVAILABLE_GATE_OPEN = "dscr_unavailable_gate_open"
    CONSTRUCTION = "construction"


@dataclass(frozen=True)
class CovenantGatedWaterfallPeriod:
    """Per-period covenant-gated waterfall result.

    Extends G2B SponsorCashFlowPeriod with the DSCR covenant gate.
    """
    period_index: int
    cashflow_date: date
    is_construction: bool

    # Gate inputs
    base_dscr: float | None
    distribution_lockup_dscr: float
    distribution_gate_status: DistributionGateStatus

    # Cash waterfall (operating) — same logic as G2B
    signed_post_senior_keur: float
    signed_post_shl_keur: float

    # Actual SHL cash receipts (capped at available cash — same as G2B)
    shl_cash_interest_receipt_keur: float
    shl_principal_receipt_keur: float

    # Distribution audit trail
    pre_gate_distribution_keur: float
    legal_equity_distribution_keur: float
    covenant_locked_keur: float
    cash_shortfall_keur: float

    # Sponsor contributions (construction periods)
    share_capital_contribution_keur: float
    share_premium_contribution_keur: float
    other_committed_equity_contribution_keur: float
    additional_equity_contribution_keur: float
    shl_cash_contribution_keur: float

    # Net cashflows for return metrics
    pure_equity_net_cashflow_keur: float
    total_sponsor_net_cashflow_keur: float


@dataclass(frozen=True)
class CovenantGatedWaterfallResult:
    """Top-level G2C result — covenant-gated shareholder waterfall."""
    financing_result: ProjectFinancingResult
    distribution_lockup_dscr: float
    waterfall_periods: tuple[CovenantGatedWaterfallPeriod, ...]

    # Contribution totals
    total_share_capital_contributed_keur: float
    total_share_premium_contributed_keur: float
    total_other_committed_equity_contributed_keur: float
    total_additional_equity_contributed_keur: float
    total_legal_equity_contributed_keur: float
    total_shl_cash_contributed_keur: float
    total_sponsor_contributed_keur: float

    # Receipt totals
    total_shl_cash_interest_received_keur: float
    total_shl_principal_received_keur: float
    total_legal_equity_distributions_keur: float
    total_covenant_locked_keur: float
    total_sponsor_receipts_keur: float

    # Return metrics
    pure_equity_xirr: float | None
    pure_equity_xirr_status: ReturnMetricStatus
    pure_equity_moic: float | None
    pure_equity_moic_status: ReturnMetricStatus
    total_sponsor_xirr: float | None
    total_sponsor_xirr_status: ReturnMetricStatus
    total_sponsor_moic: float | None
    total_sponsor_moic_status: ReturnMetricStatus

    # Gate summary
    periods_locked_by_dscr: int
    total_periods_with_senior_ds: int
