"""Source-parity construction/VAT primitives for Oborovo Stage B2.

The constants in this module are reviewer-confirmed workbook evidence.  They are
not target-derived backsolves: hard-CAPEX payments drive VAT/payable uses, while
source total-uses and senior/VAT balances are validation series.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

OBOROVO_INTEREST_FRACTIONS: tuple[float, ...] = (
    2 / 360,
    31 / 360,
    31 / 360,
    30 / 360,
    31 / 360,
    30 / 360,
    31 / 360,
    31 / 360,
    28 / 360,
    31 / 360,
    30 / 360,
    31 / 360,
)

OBOROVO_ACTIVE_CONSTRUCTION_FLAGS: tuple[bool, ...] = (True,) * 12 + (False,)
OBOROVO_PERIOD_START_DATES: tuple[date, ...] = (
    date(2029, 6, 29),
    date(2029, 7, 1),
    date(2029, 8, 1),
    date(2029, 9, 1),
    date(2029, 10, 1),
    date(2029, 11, 1),
    date(2029, 12, 1),
    date(2030, 1, 1),
    date(2030, 2, 1),
    date(2030, 3, 1),
    date(2030, 4, 1),
    date(2030, 5, 1),
    date(2030, 6, 1),
)
OBOROVO_PERIOD_END_DATES: tuple[date, ...] = (
    date(2029, 6, 30),
    date(2029, 7, 31),
    date(2029, 8, 31),
    date(2029, 9, 30),
    date(2029, 10, 31),
    date(2029, 11, 30),
    date(2029, 12, 31),
    date(2030, 1, 31),
    date(2030, 2, 28),
    date(2030, 3, 31),
    date(2030, 4, 30),
    date(2030, 5, 31),
    date(2030, 6, 30),
)

SOURCE_TOTAL_USES_VALIDATION_KEUR: tuple[float, ...] = (
    16505.437,
    3671.747,
    3728.964,
    3744.590,
    3757.251,
    3775.776,
    3754.109,
    3773.506,
    3788.984,
    3805.144,
    3820.040,
    3847.494,
)

OBOROVO_SOURCE_CUMULATIVE_SENIOR_KEUR: tuple[float, ...] = (
    1384.663018,
    5056.409904,
    8785.373449,
    12529.963407,
    16287.214608,
    20062.990972,
    23817.099533,
    27590.605498,
    31379.589234,
    35184.733375,
    39004.772946,
    42852.266726,
)

OBOROVO_SOURCE_VAT_REQUIREMENT_KEUR: tuple[float, ...] = (
    2560.748278,
    3024.196612,
    3487.644945,
    3951.093278,
    4414.541612,
    4877.989945,
    2780.690000,
    2780.690000,
    2780.690000,
    2783.580000,
    2783.580000,
    2786.695590,
    2323.247257,
    1859.798923,
    1396.350590,
    930.012257,
    466.563923,
    0.0,
)

EQUAL_12 = (1 / 12,) * 12
M1_ONLY = (1.0,) + (0.0,) * 11


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
    source_classification: str = "CONFIRMED_SOURCE"
    vat_classification: str = "CONFIRMED_SOURCE"

    def monthly_uses(self) -> tuple[float, ...]:
        if len(self.payment_weights) != 12:
            raise ValueError(f"{self.code} must have 12 construction payment weights")
        if abs(sum(self.payment_weights) - (1.0 if self.amount_keur else 0.0)) > 1e-9:
            raise ValueError(f"{self.code} payment weights do not sum to 100%")
        return tuple(self.amount_keur * w for w in self.payment_weights)

    def vat_monthly_uses(self) -> tuple[float, ...]:
        return tuple(v * self.vat_rate for v in self.monthly_uses())


@dataclass(frozen=True)
class CapexScheduleSet:
    items: tuple[CapexPaymentItem, ...]

    def monthly_uses(self) -> tuple[float, ...]:
        return tuple(sum(item.monthly_uses()[i] for item in self.items) for i in range(12))

    def vat_monthly_uses(self) -> tuple[float, ...]:
        return tuple(sum(item.vat_monthly_uses()[i] for item in self.items) for i in range(12))

    @property
    def total_hard_capex_keur(self) -> float:
        return sum(item.amount_keur for item in self.items)

    @property
    def vat_bearing_base_keur(self) -> float:
        return sum(item.amount_keur for item in self.items if item.vat_rate)


@dataclass(frozen=True)
class FinancingCostFundingPolicy:
    structuring_fee_payment_schedule: tuple[float, ...] = M1_ONLY

    def allocate(self, amount_keur: float) -> tuple[float, ...]:
        if len(self.structuring_fee_payment_schedule) != 12:
            raise ValueError("structuring fee payment schedule must have 12 periods")
        if abs(sum(self.structuring_fee_payment_schedule) - 1.0) > 1e-9:
            raise ValueError("structuring fee payment schedule must sum to 100%")
        return tuple(amount_keur * w for w in self.structuring_fee_payment_schedule)


@dataclass(frozen=True)
class VectorResidualAudit:
    component: str
    total_value_keur: float
    vector_residual_keur: float
    max_period_delta_keur: float
    max_period_index: int


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


def oborovo_timeline() -> tuple[TimelinePeriod, ...]:
    periods: list[TimelinePeriod] = []
    for i in range(13):
        active = OBOROVO_ACTIVE_CONSTRUCTION_FLAGS[i]
        periods.append(TimelinePeriod(i + 1, OBOROVO_PERIOD_START_DATES[i], OBOROVO_PERIOD_END_DATES[i], OBOROVO_INTEREST_FRACTIONS[i] if i < 12 else 30/360, active, active, active, i < len(OBOROVO_SOURCE_VAT_REQUIREMENT_KEUR)))
    for i in range(13, len(OBOROVO_SOURCE_VAT_REQUIREMENT_KEUR)):
        periods.append(TimelinePeriod(i + 1, OBOROVO_PERIOD_END_DATES[-1], OBOROVO_PERIOD_END_DATES[-1], 30/360, False, False, False, True))
    return tuple(periods)


def oborovo_capex_schedule() -> CapexScheduleSet:
    vat = 0.17
    inferred_exempt = "AGGREGATE_RECONCILIATION_INFERENCE"
    return CapexScheduleSet((
        CapexPaymentItem("C.01", "Production Units", 10912.700, EQUAL_12, 0.0, vat_classification=inferred_exempt),
        CapexPaymentItem("C.02", "EPC Contract", 26430.000, EQUAL_12, vat),
        CapexPaymentItem("C.02.02", "EPC other costs", 2014.000, EQUAL_12, vat),
        CapexPaymentItem("C.03", "Grid connection", 4050.000, EQUAL_12, vat),
        CapexPaymentItem("C.04", "Investments to prepare operation phase", 150.000, EQUAL_12, vat),
        CapexPaymentItem("C.05", "Audit & Accounting & Legal Fees", 70.000, EQUAL_12, vat),
        CapexPaymentItem("C.06", "Insurances", 320.000, M1_ONLY, vat),
        CapexPaymentItem("C.07", "Project finance costs due at closing", 355.000, M1_ONLY, vat),
        CapexPaymentItem("C.08", "Construction Management", 1151.134, M1_ONLY, vat),
        CapexPaymentItem("C.09", "Contingencies", 1986.440, M1_ONLY, vat),
        CapexPaymentItem("C.16", "Project Rights", 8524.4845, M1_ONLY, vat),
        CapexPaymentItem("C.10", "Commissioning", 17.000, (0.0,)*11 + (1.0,), vat, source_classification="SOURCE_MILESTONE_CONFIRMED"),
        CapexPaymentItem("C.11", "Project Acquisition / Project Development", 18.327, M1_ONLY, vat, source_classification="SOURCE_MILESTONE_CONFIRMED"),
    ))


def compute_vat_schedule(vat_payable_keur: tuple[float, ...], reimbursement_lag_periods: int = 6) -> tuple[dict[str, float], ...]:
    """Compute generic VAT schedule with post-CAPEX reimbursement/runoff tail."""
    horizon = len(vat_payable_keur) + reimbursement_lag_periods
    req = 0.0
    out = []
    for i in range(horizon):
        payable = vat_payable_keur[i] if i < len(vat_payable_keur) else 0.0
        reimbursement = vat_payable_keur[i - reimbursement_lag_periods] if i >= reimbursement_lag_periods else 0.0
        req = max(0.0, req + payable - reimbursement)
        out.append({"period": i + 1, "vat_payable_keur": payable, "vat_reimbursement_keur": reimbursement, "vat_requirement_keur": req})
    return tuple(out)

__all__ = [name for name in globals() if name.startswith("OBOROVO") or name in {"CapexPaymentItem", "CapexScheduleSet", "FinancingCostFundingPolicy", "TimelinePeriod", "VectorResidualAudit", "convergence_audit", "compute_vat_schedule", "oborovo_capex_schedule", "oborovo_timeline"}]
