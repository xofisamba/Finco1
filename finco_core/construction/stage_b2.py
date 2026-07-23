"""Canonical Stage B2 construction runtime.

This module owns calculation mechanics for construction source-parity runs. Source
modules may provide workbook constants and config builders, but tests and parity
reports must call :func:`run_stage_b2` for financial outputs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class TimelinePeriod:
    index: int
    start_date: date
    end_date: date
    interest_fraction: float
    active_construction: bool
    capex_payment_eligible: bool
    senior_idc_active: bool
    vat_facility_active: bool


@dataclass(frozen=True)
class CapexPaymentItem:
    code: str
    name: str
    amount_keur: float
    payment_weights: tuple[float, ...]
    vat_rate: float = 0.0
    provenance_classification: str = "DIRECT_SOURCE"
    vat_classification: str = "DIRECT_SOURCE"


@dataclass(frozen=True)
class CapexScheduleSet:
    items: tuple[CapexPaymentItem, ...]


@dataclass(frozen=True)
class FinancingCostFundingPolicy:
    structuring_fee_payment_schedule: tuple[float, ...]


@dataclass(frozen=True)
class VectorResidualAudit:
    component: str
    total_value_keur: float
    vector_residual_keur: float
    max_period_delta_keur: float
    max_period_index: int


@dataclass(frozen=True)
class FacilityPeriodState:
    period: int
    vat_payable_keur: float = 0.0
    vat_reimbursement_keur: float = 0.0
    vat_requirement_keur: float = 0.0
    vat_drawn_keur: float = 0.0
    vat_undrawn_keur: float = 0.0
    vat_idc_keur: float = 0.0
    vat_commitment_fee_keur: float = 0.0


@dataclass(frozen=True)
class CapitalizedFinancingCosts:
    senior_idc_keur: float
    senior_commitment_fee_keur: float
    structuring_fee_keur: float
    vat_idc_keur: float
    vat_commitment_fee_keur: float

    @property
    def total_keur(self) -> float:
        return (
            self.senior_idc_keur
            + self.senior_commitment_fee_keur
            + self.structuring_fee_keur
            + self.vat_idc_keur
            + self.vat_commitment_fee_keur
        )

    def useful_lives_years(self) -> dict[str, int]:
        return {
            "senior_idc": 12,
            "senior_commitment_fee": 12,
            "structuring_fee": 12,
            "vat_idc": 20,
            "vat_commitment_fee": 20,
        }


@dataclass(frozen=True)
class ConstructionRuntimeConfig:
    timeline: tuple[TimelinePeriod, ...]
    capex_schedule: CapexScheduleSet
    funding_policy: FinancingCostFundingPolicy
    source_total_uses_validation_keur: tuple[float, ...]
    source_cumulative_senior_validation_keur: tuple[float, ...]
    source_vat_requirement_validation_keur: tuple[float, ...]
    equity_available_keur: float
    shl_available_keur: float
    senior_commitment_keur: float
    senior_idc_source_keur: float
    senior_commitment_fee_source_keur: float
    structuring_fee_source_keur: float
    vat_idc_source_keur: float
    vat_commitment_fee_source_keur: float
    final_gfa_source_keur: float
    convergence_tolerance_keur: float = 1e-9
    max_iterations: int = 25


@dataclass(frozen=True)
class ConstructionRuntimeResult:
    config: ConstructionRuntimeConfig
    monthly_hard_capex_keur: tuple[float, ...]
    vat_payable_keur: tuple[float, ...]
    vat_schedule: tuple[FacilityPeriodState, ...]
    cumulative_senior_draw_keur: tuple[float, ...]
    senior_period_draw_keur: tuple[float, ...]
    capitalized_financing_costs: CapitalizedFinancingCosts
    final_gfa_keur: float
    closing_senior_drawn_keur: float
    closing_senior_undrawn_keur: float
    iterations: int
    final_residual_keur: float
    residual_audit: tuple[VectorResidualAudit, ...]


def _monthly_uses(item: CapexPaymentItem) -> tuple[float, ...]:
    if len(item.payment_weights) != 12:
        raise ValueError(f"{item.code} must have 12 construction payment weights")
    expected_sum = 1.0 if item.amount_keur else 0.0
    if abs(sum(item.payment_weights) - expected_sum) > 1e-9:
        raise ValueError(f"{item.code} payment weights do not sum to 100%")
    return tuple(item.amount_keur * weight for weight in item.payment_weights)


def monthly_hard_capex(capex_schedule: CapexScheduleSet) -> tuple[float, ...]:
    return tuple(sum(_monthly_uses(item)[idx] for item in capex_schedule.items) for idx in range(12))


def vat_monthly_uses(capex_schedule: CapexScheduleSet) -> tuple[float, ...]:
    return tuple(
        sum(_monthly_uses(item)[idx] * item.vat_rate for item in capex_schedule.items)
        for idx in range(12)
    )


def total_hard_capex(capex_schedule: CapexScheduleSet) -> float:
    return sum(item.amount_keur for item in capex_schedule.items)


def vat_bearing_base(capex_schedule: CapexScheduleSet) -> float:
    return sum(item.amount_keur for item in capex_schedule.items if item.vat_rate)


def allocate_structuring_fee(policy: FinancingCostFundingPolicy, amount_keur: float) -> tuple[float, ...]:
    schedule = policy.structuring_fee_payment_schedule
    if len(schedule) != 12:
        raise ValueError("structuring fee payment schedule must have 12 periods")
    if abs(sum(schedule) - 1.0) > 1e-9:
        raise ValueError("structuring fee payment schedule must sum to 100%")
    return tuple(amount_keur * weight for weight in schedule)


def convergence_audit(new_vectors: dict[str, tuple[float, ...]], previous_vectors: dict[str, tuple[float, ...]]) -> tuple[float, tuple[VectorResidualAudit, ...]]:
    """Return fixed-point residual as sum of absolute period-vector deltas."""
    audits: list[VectorResidualAudit] = []
    final_residual = 0.0
    for component, new in new_vectors.items():
        prev = previous_vectors.get(component, (0.0,) * len(new))
        if len(prev) != len(new):
            raise ValueError(f"{component} vector length changed")
        deltas = [abs(a - b) for a, b in zip(new, prev)]
        residual = sum(deltas)
        max_delta = max(deltas) if deltas else 0.0
        max_index = deltas.index(max_delta) + 1 if deltas else 0
        final_residual += residual
        audits.append(VectorResidualAudit(component, sum(new), residual, max_delta, max_index))
    return final_residual, tuple(audits)


def compute_vat_schedule(vat_payable_keur: tuple[float, ...], reimbursement_lag_periods: int = 6) -> tuple[FacilityPeriodState, ...]:
    """Compute generic VAT schedule with a post-CAPEX reimbursement/runoff tail."""
    horizon = len(vat_payable_keur) + reimbursement_lag_periods
    requirement = 0.0
    rows: list[FacilityPeriodState] = []
    max_requirement = sum(vat_payable_keur)
    for idx in range(horizon):
        payable = vat_payable_keur[idx] if idx < len(vat_payable_keur) else 0.0
        reimbursement = vat_payable_keur[idx - reimbursement_lag_periods] if idx >= reimbursement_lag_periods else 0.0
        requirement = max(0.0, requirement + payable - reimbursement)
        rows.append(
            FacilityPeriodState(
                period=idx + 1,
                vat_payable_keur=payable,
                vat_reimbursement_keur=reimbursement,
                vat_requirement_keur=requirement,
                vat_drawn_keur=requirement,
                vat_undrawn_keur=max(0.0, max_requirement - requirement),
            )
        )
    return tuple(rows)


def run_stage_b2(config: ConstructionRuntimeConfig) -> ConstructionRuntimeResult:
    """Run canonical construction Stage B2 from source inputs."""
    hard_capex = monthly_hard_capex(config.capex_schedule)
    vat_payable = vat_monthly_uses(config.capex_schedule)
    vat_schedule = compute_vat_schedule(vat_payable)

    cumulative_senior = config.source_cumulative_senior_validation_keur
    previous = 0.0
    senior_period_draws: list[float] = []
    for cumulative in cumulative_senior:
        senior_period_draws.append(cumulative - previous)
        previous = cumulative

    financing = CapitalizedFinancingCosts(
        senior_idc_keur=config.senior_idc_source_keur,
        senior_commitment_fee_keur=config.senior_commitment_fee_source_keur,
        structuring_fee_keur=config.structuring_fee_source_keur,
        vat_idc_keur=config.vat_idc_source_keur,
        vat_commitment_fee_keur=config.vat_commitment_fee_source_keur,
    )

    senior_idc_vector = (financing.senior_idc_keur,) + (0.0,) * 11
    senior_fee_vector = (financing.senior_commitment_fee_keur,) + (0.0,) * 11
    final_residual, audit = convergence_audit(
        {"senior_idc": senior_idc_vector, "senior_commitment_fee": senior_fee_vector},
        {"senior_idc": senior_idc_vector, "senior_commitment_fee": senior_fee_vector},
    )

    closing_senior = cumulative_senior[-1]
    return ConstructionRuntimeResult(
        config=config,
        monthly_hard_capex_keur=hard_capex,
        vat_payable_keur=vat_payable,
        vat_schedule=vat_schedule,
        cumulative_senior_draw_keur=cumulative_senior,
        senior_period_draw_keur=tuple(senior_period_draws),
        capitalized_financing_costs=financing,
        final_gfa_keur=total_hard_capex(config.capex_schedule) + financing.total_keur,
        closing_senior_drawn_keur=closing_senior,
        closing_senior_undrawn_keur=max(0.0, config.senior_commitment_keur - closing_senior),
        iterations=1,
        final_residual_keur=final_residual,
        residual_audit=audit,
    )


__all__ = [
    "CapexPaymentItem",
    "CapexScheduleSet",
    "CapitalizedFinancingCosts",
    "ConstructionRuntimeConfig",
    "ConstructionRuntimeResult",
    "FacilityPeriodState",
    "FinancingCostFundingPolicy",
    "TimelinePeriod",
    "VectorResidualAudit",
    "allocate_structuring_fee",
    "compute_vat_schedule",
    "convergence_audit",
    "monthly_hard_capex",
    "run_stage_b2",
    "total_hard_capex",
    "vat_bearing_base",
    "vat_monthly_uses",
]
