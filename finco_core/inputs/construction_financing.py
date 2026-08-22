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


class ConstructionSeniorRateMode(str):
    FLAT_ALL_IN = "FLAT_ALL_IN"
    FIXED_PLUS_MARGIN = "FIXED_PLUS_MARGIN"
    FLOATING_PLUS_MARGIN = "FLOATING_PLUS_MARGIN"
    HEDGE_BLEND = "HEDGE_BLEND"
    EXPLICIT_ALL_IN_SCHEDULE = "EXPLICIT_ALL_IN_SCHEDULE"

SENIOR_RATE_MODES = frozenset({"FLAT_ALL_IN", "FIXED_PLUS_MARGIN", "FLOATING_PLUS_MARGIN", "HEDGE_BLEND", "EXPLICIT_ALL_IN_SCHEDULE"})


@dataclass(frozen=True)
class ConstructionSeniorPricingInput:
    """Decomposed Senior construction pricing — not a single backsolved effective rate."""
    mode: str  # one of SENIOR_RATE_MODES
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
    day_count_convention: str = "ACT_360"   # ACT_360 | ACT_365 | EXPLICIT_FRACTIONS
    explicit_period_fractions: tuple[float, ...] = field(default_factory=tuple)   # when EXPLICIT_FRACTIONS


@dataclass(frozen=True)
class ConstructionCommitmentFeeInput:
    rate: float = 0.0
    balance_basis: str = "OPENING_UNDRAWN"       # OPENING_UNDRAWN | CLOSING_UNDRAWN
    capitalization_timing: str = "SAME_PERIOD"   # SAME_PERIOD | NEXT_PERIOD | PROFILE


@dataclass(frozen=True)
class ConstructionStructuringFeeInput:
    rate: float = 0.0
    basis_keur: float = 0.0
    payment_weights: tuple[float, ...] = field(default_factory=tuple)  # len = n_periods, sum to 1.0


@dataclass(frozen=True)
class ConstructionPeriodSpec:
    """One period in the variable-length construction timeline."""
    start_date: date
    end_date: date
    interest_fraction: float          # e.g. 2/360 for Oborovo P1; 30/360 for standard
    active_construction: bool = True
    capex_payment_eligible: bool = True
    senior_idc_active: bool = True
    vat_facility_active: bool = False  # VAT deferred in PR-9


@dataclass(frozen=True)
class ConstructionCapexItemInput:
    code: str
    name: str
    amount_keur: float
    payment_weights: tuple[float, ...]  # len = n_periods, sum to 1.0 (or 0.0 if amount=0)
    vat_rate: float = 0.0


@dataclass(frozen=True)
class ConstructionFinancingInput:
    """Typed construction financing authority for the clean financial engine (PR-9).

    Identity-free. Not dispatched on project name or code.
    """
    enabled: bool = False
    periods: tuple[ConstructionPeriodSpec, ...] = field(default_factory=tuple)
    capex_items: tuple[ConstructionCapexItemInput, ...] = field(default_factory=tuple)
    senior_pricing: ConstructionSeniorPricingInput | None = None
    commitment_fee: ConstructionCommitmentFeeInput | None = None
    structuring_fee: ConstructionStructuringFeeInput | None = None
    idc_balance_basis: str = "OPENING_DRAWN"         # OPENING_DRAWN | CLOSING_DRAWN
    idc_capitalization_timing: str = "SAME_PERIOD"   # SAME_PERIOD | NEXT_PERIOD | PROFILE
    convergence_tolerance_keur: float = 1e-9
    max_iterations: int = 100
    vat_deferred: bool = True  # PR9_VAT_FACILITY_DEFERRED — always True in PR-9

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("ConstructionFinancingInput.enabled must be bool")
        if not self.enabled:
            return
        n = len(self.periods)
        if n == 0:
            raise ValueError("PR9_CONSTRUCTION_ENABLED_NO_PERIODS: periods must not be empty when enabled")
        if self.senior_pricing is None:
            raise ValueError("PR9_CONSTRUCTION_ENABLED_NO_PRICING: senior_pricing required when enabled")
        if self.senior_pricing.mode not in SENIOR_RATE_MODES:
            raise ValueError(f"PR9_INVALID_SENIOR_RATE_MODE: {self.senior_pricing.mode!r}; valid={sorted(SENIOR_RATE_MODES)}")
        for i, p in enumerate(self.periods):
            if p.end_date <= p.start_date:
                raise ValueError(f"PR9_INVALID_PERIOD_DATES: periods[{i}] end <= start")
            if not math.isfinite(p.interest_fraction) or p.interest_fraction < 0:
                raise ValueError(f"PR9_INVALID_INTEREST_FRACTION: periods[{i}]={p.interest_fraction!r}")
        for i, item in enumerate(self.capex_items):
            if len(item.payment_weights) != n:
                raise ValueError(f"PR9_CAPEX_WEIGHT_LENGTH_MISMATCH: capex_items[{i}].payment_weights len={len(item.payment_weights)} != n_periods={n}")
            wt_sum = sum(item.payment_weights)
            if item.amount_keur and abs(wt_sum - 1.0) > 1e-9:
                raise ValueError(f"PR9_CAPEX_WEIGHTS_SUM: capex_items[{i}].payment_weights sum={wt_sum} != 1.0")
        if self.structuring_fee is not None and self.structuring_fee.payment_weights:
            if len(self.structuring_fee.payment_weights) != n:
                raise ValueError(f"PR9_STRUCTURING_FEE_WEIGHT_LENGTH_MISMATCH: len={len(self.structuring_fee.payment_weights)} != n_periods={n}")
        if self.idc_balance_basis not in {"OPENING_DRAWN", "CLOSING_DRAWN"}:
            raise ValueError(f"PR9_INVALID_IDC_BALANCE_BASIS: {self.idc_balance_basis!r}")
        if self.idc_capitalization_timing not in {"SAME_PERIOD", "NEXT_PERIOD", "PROFILE"}:
            raise ValueError(f"PR9_INVALID_IDC_CAPITALIZATION_TIMING: {self.idc_capitalization_timing!r}")


__all__ = [
    "ConstructionSeniorRateMode",
    "SENIOR_RATE_MODES",
    "ConstructionSeniorPricingInput",
    "ConstructionCommitmentFeeInput",
    "ConstructionStructuringFeeInput",
    "ConstructionPeriodSpec",
    "ConstructionCapexItemInput",
    "ConstructionFinancingInput",
]
