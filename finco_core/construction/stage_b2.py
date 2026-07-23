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
    equity_available_keur: float
    shl_available_keur: float
    senior_commitment_keur: float
    senior_interest_rate: float
    senior_commitment_fee_rate: float
    senior_interest_rate_schedule: tuple[float, ...] = field(default_factory=tuple)
    base_rate: float = 0.0
    hedge_coverage: float = 0.0
    swap_margin: float = 0.0
    forward_swap_margin: float = 0.0
    cva: float = 0.0
    external_curve_buffer: float = 0.0
    euribor_1m_fixings: tuple[float, ...] = field(default_factory=tuple)
    senior_idc_balance_basis: str = "OPENING_DRAWN"
    senior_commitment_fee_balance_basis: str = "OPENING_UNDRAWN"
    senior_idc_capitalization_timing: str = "PROFILE"
    senior_commitment_fee_capitalization_timing: str = "PROFILE"
    structuring_fee_rate: float = 0.0
    structuring_fee_basis_keur: float = 0.0
    vat_facility_interest_rate: float = 0.0
    vat_facility_commitment_fee_rate: float = 0.0
    vat_facility_commitment_keur: float = 0.0
    vat_interest_period_fractions: tuple[float, ...] = field(default_factory=tuple)
    vat_commitment_fee_active_periods: int = 12
    senior_idc_spending_profile: tuple[float, ...] = field(default_factory=tuple)
    senior_commitment_fee_spending_profile: tuple[float, ...] = field(default_factory=tuple)
    vat_financing_cost_spending_profile: tuple[float, ...] = field(default_factory=tuple)
    initial_senior_idc_funded_uses_keur: tuple[float, ...] = field(default_factory=tuple)
    initial_senior_commitment_fee_funded_uses_keur: tuple[float, ...] = field(default_factory=tuple)
    initial_vat_financing_funded_uses_keur: tuple[float, ...] = field(default_factory=tuple)
    convergence_tolerance_keur: float = 1e-9
    max_iterations: int = 100


@dataclass(frozen=True)
class ConstructionRuntimeResult:
    config: ConstructionRuntimeConfig
    monthly_hard_capex_keur: tuple[float, ...]
    vat_payable_keur: tuple[float, ...]
    vat_schedule: tuple[FacilityPeriodState, ...]
    cumulative_senior_draw_keur: tuple[float, ...]
    senior_period_draw_keur: tuple[float, ...]
    total_permanent_uses_keur: tuple[float, ...]
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


def _pad_12(values: tuple[float, ...]) -> tuple[float, ...]:
    if not values:
        return (0.0,) * 12
    if len(values) != 12:
        raise ValueError("circular vectors must have 12 periods")
    return values


def _profile_12(values: tuple[float, ...], *, default_period: int | None = None) -> tuple[float, ...]:
    if not values:
        if default_period is None:
            return (0.0,) * 12
        return tuple(1.0 if idx == default_period else 0.0 for idx in range(12))
    if len(values) != 12:
        raise ValueError("financing-cost spending profiles must have 12 periods")
    if abs(sum(values) - 1.0) > 1e-9:
        raise ValueError("financing-cost spending profiles must sum to 100%")
    return values


def _period_rates(config: ConstructionRuntimeConfig) -> tuple[float, ...]:
    if config.euribor_1m_fixings:
        if len(config.euribor_1m_fixings) != 12:
            raise ValueError("Euribor 1m fixing schedule must have 12 periods")
        hedged_component = (
            config.base_rate * config.hedge_coverage
            + config.swap_margin
            + config.forward_swap_margin
            + config.cva
        )
        floating_weight = (1.0 - config.hedge_coverage) * (1.0 + config.external_curve_buffer)
        return tuple(
            hedged_component + fixing * floating_weight + config.senior_interest_rate
            for fixing in config.euribor_1m_fixings
        )
    if config.senior_interest_rate_schedule:
        if len(config.senior_interest_rate_schedule) != 12:
            raise ValueError("Senior interest-rate schedule must have 12 periods")
        return config.senior_interest_rate_schedule
    return (config.senior_interest_rate,) * 12


def _next_period_capitalized_uses(calculated: tuple[float, ...]) -> tuple[float, ...]:
    if len(calculated) != 12:
        raise ValueError("calculated financing vectors must have 12 periods")
    return (0.0,) + calculated[:11]


def _capitalized_uses(total: float, profile: tuple[float, ...], calculated: tuple[float, ...], timing: str) -> tuple[float, ...]:
    if timing in {"NEXT_PERIOD", "NEXT_FUNDING_PERIOD"}:
        return _next_period_capitalized_uses(calculated)
    if timing == "PROFILE":
        return tuple(total * weight for weight in profile)
    if timing == "SAME_PERIOD":
        return calculated
    raise ValueError(f"Unsupported capitalization timing: {timing}")


def _vat_fractions(config: ConstructionRuntimeConfig, horizon: int) -> tuple[float, ...]:
    if config.vat_interest_period_fractions:
        if len(config.vat_interest_period_fractions) != horizon:
            raise ValueError("VAT interest-period fraction vector must match VAT horizon")
        return config.vat_interest_period_fractions
    return tuple((config.timeline[idx].interest_fraction if idx < len(config.timeline) else 30 / 360) for idx in range(horizon))


def _waterfall_senior_draws(period_uses: tuple[float, ...], equity: float, shl: float) -> tuple[float, ...]:
    remaining_equity = equity
    remaining_shl = shl
    senior_draws: list[float] = []
    for uses in period_uses:
        equity_draw = min(remaining_equity, uses)
        remaining_equity -= equity_draw
        after_equity = uses - equity_draw
        shl_draw = min(remaining_shl, after_equity)
        remaining_shl -= shl_draw
        senior_draws.append(after_equity - shl_draw)
    return tuple(senior_draws)


def run_stage_b2(config: ConstructionRuntimeConfig) -> ConstructionRuntimeResult:
    """Run canonical iterative construction Stage B2 from source inputs.

    Circular Senior IDC and commitment fees are seeded, funded as period uses,
    recalculated from opening drawn/undrawn balances, and iterated until period
    vectors converge.  Validation/output targets are intentionally absent from
    ConstructionRuntimeConfig and are not used here.
    """
    hard_capex = monthly_hard_capex(config.capex_schedule)
    vat_payable = vat_monthly_uses(config.capex_schedule)
    vat_schedule = compute_vat_schedule(vat_payable)
    structuring = allocate_structuring_fee(
        config.funding_policy,
        config.structuring_fee_rate * config.structuring_fee_basis_keur,
    )

    idc_profile = _profile_12(config.senior_idc_spending_profile)
    fee_profile = _profile_12(config.senior_commitment_fee_spending_profile)
    vat_financing_profile = _profile_12(config.vat_financing_cost_spending_profile)
    senior_rates = _period_rates(config)
    senior_idc_uses = _pad_12(config.initial_senior_idc_funded_uses_keur)
    senior_fee_uses = _pad_12(config.initial_senior_commitment_fee_funded_uses_keur)
    vat_financing_uses = _pad_12(config.initial_vat_financing_funded_uses_keur)
    residual = float("inf")
    audit: tuple[VectorResidualAudit, ...] = ()
    senior_period_draws = (0.0,) * 12
    senior_idc_total = 0.0
    senior_fee_total = 0.0
    vat_idc = 0.0
    vat_fee = 0.0

    for iteration in range(1, config.max_iterations + 1):
        period_uses = tuple(
            hard_capex[idx] + structuring[idx] + senior_idc_uses[idx] + senior_fee_uses[idx] + vat_financing_uses[idx]
            for idx in range(12)
        )
        senior_period_draws = _waterfall_senior_draws(
            period_uses, config.equity_available_keur, config.shl_available_keur
        )

        idc_calc: list[float] = []
        fee_calc: list[float] = []
        opening_senior = 0.0
        for idx, draw in enumerate(senior_period_draws):
            closing_senior = opening_senior + draw
            if config.senior_idc_balance_basis in {"CURRENT_CLOSING_DRAWN", "FUNDING_PERIOD_CLOSING_DRAWN"}:
                idc_basis = closing_senior
            elif config.senior_idc_balance_basis == "OPENING_DRAWN":
                idc_basis = opening_senior
            else:
                raise ValueError(f"Unsupported Senior IDC balance basis: {config.senior_idc_balance_basis}")

            if config.senior_commitment_fee_balance_basis in {"CURRENT_CLOSING_UNDRAWN", "FUNDING_PERIOD_CLOSING_UNDRAWN"}:
                fee_drawn_basis = closing_senior
            elif config.senior_commitment_fee_balance_basis == "OPENING_UNDRAWN":
                fee_drawn_basis = opening_senior
            else:
                raise ValueError(
                    f"Unsupported Senior commitment-fee balance basis: {config.senior_commitment_fee_balance_basis}"
                )
            fee_undrawn_basis = max(0.0, config.senior_commitment_keur - fee_drawn_basis)
            fraction = config.timeline[idx].interest_fraction
            if config.timeline[idx].senior_idc_active:
                idc_calc.append(idc_basis * senior_rates[idx] * fraction)
                fee_calc.append(fee_undrawn_basis * config.senior_commitment_fee_rate * fraction)
            else:
                idc_calc.append(0.0)
                fee_calc.append(0.0)
            opening_senior = closing_senior

        senior_idc_total = sum(idc_calc)
        senior_fee_total = sum(fee_calc)
        vat_fractions = _vat_fractions(config, len(vat_schedule))
        vat_idc = sum(
            row.vat_requirement_keur * config.vat_facility_interest_rate * vat_fractions[idx]
            for idx, row in enumerate(vat_schedule)
        )
        vat_fee = sum(
            max(0.0, config.vat_facility_commitment_keur - row.vat_requirement_keur)
            * config.vat_facility_commitment_fee_rate
            * vat_fractions[idx]
            for idx, row in enumerate(vat_schedule[: config.vat_commitment_fee_active_periods])
        )

        new_idc_uses = _capitalized_uses(
            senior_idc_total, idc_profile, tuple(idc_calc), config.senior_idc_capitalization_timing
        )
        new_fee_uses = _capitalized_uses(
            senior_fee_total, fee_profile, tuple(fee_calc), config.senior_commitment_fee_capitalization_timing
        )
        new_vat_financing_uses = tuple((vat_idc + vat_fee) * weight for weight in vat_financing_profile)
        residual, audit = convergence_audit(
            {
                "senior_idc": new_idc_uses,
                "senior_commitment_fee": new_fee_uses,
                "vat_financing_costs": new_vat_financing_uses,
            },
            {
                "senior_idc": senior_idc_uses,
                "senior_commitment_fee": senior_fee_uses,
                "vat_financing_costs": vat_financing_uses,
            },
        )
        senior_idc_uses = new_idc_uses
        senior_fee_uses = new_fee_uses
        vat_financing_uses = new_vat_financing_uses
        if residual <= config.convergence_tolerance_keur:
            break
    else:
        raise RuntimeError(
            f"Stage B2 circular financing did not converge after {config.max_iterations} iterations; "
            f"final residual={residual:.12f} kEUR"
        )

    period_uses = tuple(
        hard_capex[idx] + structuring[idx] + senior_idc_uses[idx] + senior_fee_uses[idx] + vat_financing_uses[idx]
        for idx in range(12)
    )
    senior_period_draws = _waterfall_senior_draws(
        period_uses, config.equity_available_keur, config.shl_available_keur
    )
    cumulative_senior: list[float] = []
    running = 0.0
    for draw in senior_period_draws:
        running += draw
        cumulative_senior.append(running)

    financing = CapitalizedFinancingCosts(
        senior_idc_keur=sum(senior_idc_uses),
        senior_commitment_fee_keur=sum(senior_fee_uses),
        structuring_fee_keur=sum(structuring),
        vat_idc_keur=vat_idc,
        vat_commitment_fee_keur=vat_fee,
    )
    closing_senior = cumulative_senior[-1]
    return ConstructionRuntimeResult(
        config=config,
        monthly_hard_capex_keur=hard_capex,
        vat_payable_keur=vat_payable,
        vat_schedule=vat_schedule,
        cumulative_senior_draw_keur=tuple(cumulative_senior),
        senior_period_draw_keur=senior_period_draws,
        total_permanent_uses_keur=period_uses,
        capitalized_financing_costs=financing,
        final_gfa_keur=total_hard_capex(config.capex_schedule) + financing.total_keur,
        closing_senior_drawn_keur=closing_senior,
        closing_senior_undrawn_keur=max(0.0, config.senior_commitment_keur - closing_senior),
        iterations=iteration,
        final_residual_keur=residual,
        residual_audit=audit,
    )


def apply_capitalized_financing_costs(capex_structure, financing: CapitalizedFinancingCosts):
    """Return a CapexStructure carrying canonical Stage B2 financing outputs.

    The adapter is generic and immutable: it maps Stage B2 financing components to
    the existing CapexStructure financing fields consumed by
    book_depreciable_capex_items().
    """
    from dataclasses import replace

    vat_costs = financing.vat_idc_keur + financing.vat_commitment_fee_keur
    return replace(
        capex_structure,
        idc_keur=financing.senior_idc_keur,
        commitment_fees_keur=financing.senior_commitment_fee_keur,
        bank_fees_keur=financing.structuring_fee_keur,
        vat_costs_keur=vat_costs,
        vat_facility_idc_keur=financing.vat_idc_keur,
        vat_facility_commitment_fee_keur=financing.vat_commitment_fee_keur,
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
    "apply_capitalized_financing_costs",
    "compute_vat_schedule",
    "convergence_audit",
    "monthly_hard_capex",
    "run_stage_b2",
    "total_hard_capex",
    "vat_bearing_base",
    "vat_monthly_uses",
]
