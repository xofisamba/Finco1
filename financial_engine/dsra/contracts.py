"""financial_engine.dsra.contracts — Input/output contracts for CASH_DSRA roll-forward.

Pure typed dataclasses. No imports from app, legacy waterfall, project factories,
Excel fixtures, or diagnostic scripts. No project-name dispatch.
"""
from __future__ import annotations

from dataclasses import dataclass

from finco_core.inputs import DebtServiceReserveSupportMode


@dataclass(frozen=True)
class CashDsraInput:
    """Input contract for the clean CASH_DSRA roll-forward engine.

    mode:
        NONE      — neutral pass-through; requirement_keur must be 0.
        CASH_DSRA — canonical roll-forward; opening at first operating period = requirement_keur
                    (COD funding handshake: construction financing funds reserve as a Project Use).
        DSRF      — pass-through; DSRF fee handled by financial_engine.financing.dsrf.
                    No draw engine added here.

    requirement_keur:
        ONE unified reserve requirement (scalar, static).
        Source authority: FinancingParams.debt_service_reserve_requirement_keur.
        This is the canonical target for the CASH_DSRA roll-forward.
        NONE mode: must be 0.0 — raises if > 0.

    CASH_DSRA_TARGET_AUTHORITY:
        The static scalar requirement_keur is the canonical PR-3 target.
        dsra_months (FinancingParams) is NOT consumed here — no source evidence
        proves a dynamic 6-month forward DS schedule as the clean-engine target.
        A future typed target policy may be added only if source-required.
    """
    mode: DebtServiceReserveSupportMode
    requirement_keur: float = 0.0


@dataclass(frozen=True)
class CashDsraPeriodResult:
    """CASH_DSRA roll-forward result for one model period.

    Cash conservation identity (must hold per period):
        cash_before_dsra_keur - top_up_keur + draw_to_cover_shortfall_keur + release_keur
        == cash_after_dsra_keur

    Balance conservation identity (must hold per period):
        opening_balance_keur + top_up_keur - draw_to_cover_shortfall_keur - release_keur
        == closing_balance_keur
    """
    period_index: int
    is_construction: bool
    opening_balance_keur: float
    required_balance_keur: float
    cash_before_dsra_keur: float
    draw_to_cover_shortfall_keur: float
    top_up_keur: float
    release_keur: float
    closing_balance_keur: float
    cash_after_dsra_keur: float
    shortfall_keur: float
    target_met: bool


@dataclass(frozen=True)
class CashDsraSchedules:
    """Canonical CASH_DSRA roll-forward schedule for all model periods.

    PR-3 reserve authority. Exposes cash_after_dsra_keur per period as the
    reserve-adjusted downstream cash signal. DA / SHL routing is PR-4.

    UNRESOLVED_RELEASE_POLICY: release_keur == 0 in PR-3.
        Release timing is not proven from current source evidence (Oborovo,
        TUHO, KUPI all have requirement_keur == 0 → neutral). Retain balance
        until a typed release policy is source-authorised.

    COD_FUNDING_HANDSHAKE:
        For CASH_DSRA mode: opening_balance at first operating period == requirement_keur.
        This reconciles to the construction reserve use in project_uses.py
        (reserve_account_funding_keur == debt_service_reserve_requirement_keur at close).
    """
    mode: str
    requirement_keur: float
    period_results: tuple[CashDsraPeriodResult, ...]
    total_top_up_keur: float
    total_draw_keur: float
    total_release_keur: float
    final_closing_balance_keur: float
    diagnostics: tuple[str, ...]
