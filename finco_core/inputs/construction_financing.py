"""finco_core.inputs.construction_financing — Typed construction financing authority (PR-9).

ONE_TYPED_CONSTRUCTION_FINANCING_AND_IDC_AUTHORITY

When enabled=False (default): neutral pass-through. CapexStructure.idc_keur /
commitment_fees_keur / bank_fees_keur remain as legacy manual inputs.
Generic Solar/Wind default to disabled → bit-identical to PR-8.

When enabled=True: run_stage_b2() is wired into the G2A fixed point.
Computed Senior IDC, commitment fee, structuring fee become authoritative.
If CapexStructure.idc_keur / commitment_fees_keur / bank_fees_keur are non-zero
while construction_financing.enabled, raise PR9_MANUAL_DERIVED_CONSTRUCTION_COST_CONFLICT.

VAT Facility: PR9_VAT_FACILITY_DEFERRED — not enabled in PR-9. vat_deferred=True always.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from datetime import date

from finco_core.inputs.senior_rate_schedule import SeniorRateMode, SeniorDayCountConvention


@dataclass(frozen=True)
class ConstructionSeniorPricingInput:
    """Decomposed Senior construction pricing — not a single backsolved effective rate."""
    mode: SeniorRateMode  # canonical enum
    flat_all_in_rate: float = 0.0
    fixed_base_rate: float = 0.0          # hedged base component (swap rate)
    margin_rate: float = 0.0              # Senior margin (spread over base)
    hedge_pct: float = 0.0               # fraction of notional hedged (0.0–1.0)
    swap_margin: float = 0.0
    forward_swap_adjustment: float = 0.0
    cva: float = 0.0
    floating_curve_buffer_pct: float = 0.0
    floating_base_rate_curve: tuple[float, ...] = field(default_factory=tuple)  # per-period Euribor fixings
    explicit_all_in_schedule: tuple[float, ...] = field(default_factory=tuple)   # per-period all-in rates
    day_count: SeniorDayCountConvention = SeniorDayCountConvention.ACT_360
    explicit_period_fractions: tuple[float, ...] = field(default_factory=tuple)   # when EXPLICIT_FRACTIONS


@dataclass(frozen=True)
class ConstructionCommitmentFeeInput:
    rate: float = 0.0
    balance_basis: str = "OPENING_UNDRAWN"       # OPENING_UNDRAWN | CLOSING_UNDRAWN
    capitalization_timing: str = "SAME_PERIOD"   # SAME_PERIOD | NEXT_PERIOD


@dataclass(frozen=True)
class ConstructionStructuringFeeInput:
    rate: float = 0.0
    basis_keur: float = 0.0
    payment_weights: tuple[float, ...] = field(default_factory=tuple)  # len = n_periods, sum to 1.0


@dataclass(frozen=True)
class ConstructionPeriodSpec:
    """One period in the variable-length construction timeline.

    interest_fraction is derived by the adapter from dates + day_count convention.
    """
    start_date: date
    end_date: date
    active_construction: bool = True
    capex_payment_eligible: bool = True
    senior_idc_active: bool = True
    vat_facility_active: bool = False  # VAT deferred in PR-9


@dataclass(frozen=True)
class ConstructionCapexTimingInput:
    """Construction CAPEX timing only. Amounts come from ProjectInputs.capex by code.

    PR9_CAPEX_AUTHORITY: amount_keur lives exclusively in CapexStructure.
    This class owns TIMING only — payment_weights controls when the amount flows.
    vat_rate must be 0.0 (PR9_VAT_FACILITY_DEFERRED).
    """
    code: str           # matches a field name in CapexStructure (e.g. "epc_contract") or a code
    name: str
    payment_weights: tuple[float, ...]  # len = n_periods, sum = 1.0
    vat_rate: float = 0.0               # PR9_VAT_FACILITY_DEFERRED: must be 0.0


@dataclass(frozen=True)
class ConstructionFinancingInput:
    """Typed construction financing authority for the clean financial engine (PR-9).

    Identity-free. Not dispatched on project name or code.
    """
    enabled: bool = False
    periods: tuple[ConstructionPeriodSpec, ...] = field(default_factory=tuple)
    capex_items: tuple[ConstructionCapexTimingInput, ...] = field(default_factory=tuple)
    senior_pricing: ConstructionSeniorPricingInput | None = None
    commitment_fee: ConstructionCommitmentFeeInput | None = None
    structuring_fee: ConstructionStructuringFeeInput | None = None
    idc_balance_basis: str = "OPENING_DRAWN"         # OPENING_DRAWN | CLOSING_DRAWN
    idc_capitalization_timing: str = "SAME_PERIOD"   # SAME_PERIOD | NEXT_PERIOD
    convergence_tolerance_keur: float = 1e-9
    max_iterations: int = 100
    vat_deferred: bool = True  # PR9_VAT_FACILITY_DEFERRED — always True in PR-9

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("ConstructionFinancingInput.enabled must be bool")
        if self.vat_deferred is not True:
            raise ValueError("PR9_VAT_FACILITY_DEFERRED: vat_deferred must be True")
        if not self.enabled:
            return
        n = len(self.periods)
        if n == 0:
            raise ValueError("PR9_CONSTRUCTION_ENABLED_NO_PERIODS: periods must not be empty when enabled")
        if self.senior_pricing is None:
            raise ValueError("PR9_CONSTRUCTION_ENABLED_NO_PRICING: senior_pricing required when enabled")
        if not isinstance(self.senior_pricing.mode, SeniorRateMode):
            raise ValueError(f"PR9_INVALID_SENIOR_RATE_MODE: {self.senior_pricing.mode!r}; must be SeniorRateMode enum")
        # HEDGE_BLEND: hedge_pct in [0,1]
        if self.senior_pricing.mode == SeniorRateMode.HEDGE_BLEND:
            hp = self.senior_pricing.hedge_pct
            if not (0.0 <= hp <= 1.0):
                raise ValueError(f"PR9_HEDGE_PCT_OUT_OF_RANGE: hedge_pct={hp} must be in [0, 1]")
        # FLOATING_PLUS_MARGIN and HEDGE_BLEND: floating curve required, length = n_periods
        if self.senior_pricing.mode in (SeniorRateMode.FLOATING_PLUS_MARGIN, SeniorRateMode.HEDGE_BLEND):
            curve = self.senior_pricing.floating_base_rate_curve
            if not curve:
                raise ValueError(
                    f"PR9_FLOATING_CURVE_REQUIRED: mode={self.senior_pricing.mode.value} requires floating_base_rate_curve"
                )
            if len(curve) != n:
                raise ValueError(
                    f"PR9_FLOATING_CURVE_LENGTH: len={len(curve)} != n_periods={n}"
                )
        # EXPLICIT_ALL_IN_SCHEDULE: schedule required, length = n_periods
        if self.senior_pricing.mode == SeniorRateMode.EXPLICIT_ALL_IN_SCHEDULE:
            sched = self.senior_pricing.explicit_all_in_schedule
            if not sched:
                raise ValueError("PR9_EXPLICIT_SCHEDULE_REQUIRED: EXPLICIT_ALL_IN_SCHEDULE mode requires explicit_all_in_schedule")
            if len(sched) != n:
                raise ValueError(f"PR9_EXPLICIT_SCHEDULE_LENGTH: len={len(sched)} != n_periods={n}")
        # EXPLICIT_FRACTIONS day_count: explicit_period_fractions required, length = n_periods
        if self.senior_pricing.day_count == SeniorDayCountConvention.EXPLICIT_FRACTIONS:
            fracs = self.senior_pricing.explicit_period_fractions
            if not fracs:
                raise ValueError("PR9_EXPLICIT_FRACTIONS_REQUIRED: EXPLICIT_FRACTIONS day_count requires explicit_period_fractions")
            if len(fracs) != n:
                raise ValueError(f"PR9_EXPLICIT_FRACTIONS_LENGTH: len={len(fracs)} != n_periods={n}")
        for i, p in enumerate(self.periods):
            if p.end_date <= p.start_date:
                raise ValueError(f"PR9_INVALID_PERIOD_DATES: periods[{i}] end <= start")
        for i, item in enumerate(self.capex_items):
            # VAT fail-closed
            if item.vat_rate != 0.0:
                raise ValueError(f"PR9_VAT_FACILITY_DEFERRED: capex_items[{i}].vat_rate must be 0.0, got {item.vat_rate!r}")
            # payment_weights: non-negative, length = n_periods, sum = 1.0
            if len(item.payment_weights) != n:
                raise ValueError(f"PR9_CAPEX_WEIGHT_LENGTH_MISMATCH: capex_items[{i}].payment_weights len={len(item.payment_weights)} != n_periods={n}")
            for wi, w in enumerate(item.payment_weights):
                if w < 0.0:
                    raise ValueError(f"PR9_CAPEX_WEIGHT_NEGATIVE: capex_items[{i}].payment_weights[{wi}]={w} < 0")
            wt_sum = sum(item.payment_weights)
            if len(item.payment_weights) > 0 and abs(wt_sum - 1.0) > 1e-9:
                raise ValueError(f"PR9_CAPEX_WEIGHTS_SUM: capex_items[{i}].payment_weights sum={wt_sum} != 1.0")
        if self.structuring_fee is not None and self.structuring_fee.payment_weights:
            sf_weights = self.structuring_fee.payment_weights
            if len(sf_weights) != n:
                raise ValueError(f"PR9_STRUCTURING_FEE_WEIGHT_LENGTH_MISMATCH: len={len(sf_weights)} != n_periods={n}")
            sf_sum = sum(sf_weights)
            if abs(sf_sum - 1.0) > 1e-9:
                raise ValueError(f"PR9_STRUCTURING_FEE_WEIGHTS_SUM: sum={sf_sum} != 1.0")
        if self.idc_balance_basis not in {"OPENING_DRAWN", "CLOSING_DRAWN"}:
            raise ValueError(f"PR9_INVALID_IDC_BALANCE_BASIS: {self.idc_balance_basis!r}")
        if self.idc_capitalization_timing not in {"SAME_PERIOD", "NEXT_PERIOD"}:
            raise ValueError(
                f"PR9_INVALID_IDC_CAPITALIZATION_TIMING: {self.idc_capitalization_timing!r} — "
                "PROFILE mode removed (PR9_PROFILE_DEFERRED). Use SAME_PERIOD or NEXT_PERIOD."
            )
        if self.max_iterations <= 0:
            raise ValueError(f"PR9_INVALID_MAX_ITERATIONS: {self.max_iterations} must be > 0")
        if self.convergence_tolerance_keur <= 0:
            raise ValueError(f"PR9_INVALID_CONVERGENCE_TOLERANCE: {self.convergence_tolerance_keur} must be > 0")


__all__ = [
    "SeniorRateMode",
    "SeniorDayCountConvention",
    "ConstructionSeniorPricingInput",
    "ConstructionCommitmentFeeInput",
    "ConstructionStructuringFeeInput",
    "ConstructionPeriodSpec",
    "ConstructionCapexTimingInput",
    "ConstructionFinancingInput",
]
