"""G2C contracts — typed covenant-gated shareholder waterfall results.

Source authority: extracted fixture (SHA 15a621c4...), Inputs!D223
  senior_lockup_dscr = 1.10 → generic distribution_lockup_dscr parameter.

R-row mapping (CF sheet, from excel source extraction):
  R84  free_cash_flow_for_junior_keur  → signed_post_senior (pre-DSRA; see note)
  R109 free_cash_flow_for_distribution → covenant-gated FCF, gate output
  R112 free_cash_flow_for_shl_keur     → inherits R109 (CF112 = H109)
  R116 free_cash_flow_for_dividends    → legal_equity_distribution_keur

Waterfall ordering (source-proven):
  1. signed_post_senior (R84)
  2. DSCR covenant gate → fcf_for_distribution (R109)
  3. SHL service from fcf_for_distribution (R112 = R109)
  4. legal_equity_distribution = remainder (R116)

G2C_DISTRIBUTION_ACCOUNT_AUTHORITY_INCOMPLETE: R98 (distribution account
balance / carryforward) is NOT in the extracted source fixture. Per-period
locked cash is tracked but NOT accumulated into a releasing distribution
account. If R98 is extracted in a future phase, the accumulation/release
layer may be added.

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

    Source: extracted fixture Inputs!D223 → generic lockup_dscr threshold.
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

    # Cash waterfall (operating) — source-proven ordering
    signed_post_senior_keur: float          # R84: pre-gate junior FCF
    dsrf_commitment_fee_keur: float         # DSRF fee deducted before gate (0 for CASH_DSRA/NONE)
    fcf_for_distribution_keur: float        # R109: gate output (0 if locked)
    covenant_locked_keur: float             # R84 - R109 when gate locks

    # Causal SHL balance roll-forward (from compute_shl_waterfall_period)
    shl_opening_balance_keur: float          # opening SHL balance this period
    shl_gross_interest_keur: float           # gross accrued SHL interest (opening × rate × dcf)
    shl_cash_interest_receipt_keur: float    # cash interest paid from fcf_for_distribution
    shl_pik_keur: float                      # unpaid gross interest → PIK capitalised

    # Contractual vs actual principal (BULLET: contractual balloon may exceed cash)
    contractual_shl_principal_due_keur: float   # scheduler balloon or sweep amount due
    actual_shl_principal_paid_keur: float        # actual cash paid ≤ contractual_due
    unpaid_shl_principal_keur: float             # contractual - actual (0 unless BULLET shortfall)

    # Actual causal closing balance: opening + PIK - actual_paid (NOT contractual)
    actual_shl_closing_balance_keur: float

    # Legacy alias kept for backward compat; equals actual_shl_closing_balance_keur
    shl_principal_receipt_keur: float       # = actual_shl_principal_paid_keur
    shl_closing_balance_keur: float         # = actual_shl_closing_balance_keur

    # Equity distribution: residual after SHL service from fcf_for_distribution (R116)
    legal_equity_distribution_keur: float
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
    total_covenant_locked_keur: float       # sum of per-period gate-locked cash
    total_sponsor_receipts_keur: float
    total_dsrf_commitment_fee_keur: float   # total DSRF fee (0 for CASH_DSRA/NONE)

    # G2C_DISTRIBUTION_ACCOUNT_AUTHORITY_INCOMPLETE: R98 not in source extraction
    distribution_account_status: str

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

    # G2C_DEDUCTIBLE_SHL_COVENANT_FEEDBACK_NOT_YET_CLOSED when deductible SHL
    # interest + gate locks any period + PIK accumulates (feedback loop not closed).
    # None when Oborovo FULLY_NON_DEDUCTIBLE or no gate lock or no SHL.
    deductible_shl_covenant_feedback_status: str | None
