"""Immutable G2A Sources & Uses and financing-stack audit contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectUses:
    hard_project_capex_keur: float
    explicit_financing_cost_uses_keur: float
    reserve_account_funding_keur: float
    other_explicit_project_uses_keur: float
    total_project_uses_keur: float


@dataclass(frozen=True)
class ConstructionFundingPeriod:
    period_index: int
    project_cash_uses_keur: float
    senior_draw_keur: float
    junior_or_other_main_funding_draw_keur: float
    share_capital_draw_keur: float
    additional_equity_draw_keur: float
    shl_cash_draw_keur: float
    total_sponsor_cash_draw_keur: float
    total_sources_keur: float
    sources_uses_difference_keur: float
    cumulative_project_cash_uses_keur: float
    cumulative_senior_draw_keur: float
    cumulative_junior_or_other_main_funding_draw_keur: float
    cumulative_share_capital_draw_keur: float
    cumulative_additional_equity_draw_keur: float
    cumulative_shl_cash_draw_keur: float
    cumulative_total_sources_keur: float
    cumulative_sources_uses_difference_keur: float


@dataclass(frozen=True)
class ConstructionFundingResult:
    policy: str
    periods: tuple[ConstructionFundingPeriod, ...]
    maximum_period_difference_keur: float
    maximum_cumulative_difference_keur: float


@dataclass(frozen=True)
class ProjectFinancingResult:
    project_model_result: object
    project_uses: ProjectUses
    dscr_debt_capacity_keur: float
    gearing_basis_keur: float
    gearing_ratio: float
    gearing_debt_capacity_keur: float
    final_senior_commitment_keur: float
    binding_senior_constraint: str
    junior_or_other_main_project_funding_keur: float
    share_capital_keur: float
    additional_equity_keur: float
    derived_shl_cash_principal_keur: float
    shl_construction_pik_keur: float
    opening_operating_shl_balance_keur: float
    construction_funding: ConstructionFundingResult
    fixed_point_iteration_count: int
    fixed_point_maximum_difference_keur: float
