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
from dataclasses import dataclass, field
from datetime import date

from finco_core._numeric import require_bool, require_finite_real, require_positive_int
from finco_core.inputs.senior_rate_schedule import SeniorRateMode, SeniorDayCountConvention


_SCHEDULE_TOLERANCE = 1e-9
_NUMERIC_ERROR = "PR9_INVALID_TYPED_CONSTRUCTION_NUMERIC"


def _validate_weights(name: str, values: tuple[float, ...]) -> None:
    for index, value in enumerate(values):
        require_finite_real(
            f"{name}[{index}]", value, minimum=0.0, error_code=_NUMERIC_ERROR
        )


def _require_non_negative_all_in(name: str, value: float) -> None:
    resolved = require_finite_real(
        name, value, error_code="PR9_INVALID_SENIOR_ALL_IN_RATE"
    )
    if resolved < 0.0:
        raise ValueError(f"PR9_INVALID_SENIOR_ALL_IN_RATE: {name}={value!r} must be >= 0")


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

    def __post_init__(self) -> None:
        if not isinstance(self.mode, SeniorRateMode):
            raise ValueError(f"PR9_INVALID_SENIOR_RATE_MODE: {self.mode!r}")
        if not isinstance(self.day_count, SeniorDayCountConvention):
            raise ValueError(f"PR9_INVALID_SENIOR_DAY_COUNT: {self.day_count!r}")

        scalar_names = (
            "flat_all_in_rate",
            "fixed_base_rate",
            "margin_rate",
            "hedge_pct",
            "swap_margin",
            "forward_swap_adjustment",
            "cva",
            "floating_curve_buffer_pct",
        )
        for name in scalar_names:
            require_finite_real(name, getattr(self, name), error_code=_NUMERIC_ERROR)
        require_finite_real(
            "margin_rate", self.margin_rate, minimum=0.0, error_code=_NUMERIC_ERROR
        )
        if not 0.0 <= self.hedge_pct <= 1.0:
            raise ValueError(
                f"PR9_HEDGE_PCT_OUT_OF_RANGE: hedge_pct={self.hedge_pct!r} must be in [0, 1]"
            )
        for index, value in enumerate(self.floating_base_rate_curve):
            require_finite_real(
                f"floating_base_rate_curve[{index}]", value, error_code=_NUMERIC_ERROR
            )
        for index, value in enumerate(self.explicit_all_in_schedule):
            resolved = require_finite_real(
                f"explicit_all_in_schedule[{index}]", value, error_code=_NUMERIC_ERROR
            )
            _require_non_negative_all_in(
                f"explicit_all_in_schedule[{index}]", resolved
            )
        _validate_weights("explicit_period_fractions", self.explicit_period_fractions)

        if self.mode == SeniorRateMode.FLAT_ALL_IN:
            _require_non_negative_all_in("flat_all_in_rate", self.flat_all_in_rate)
        elif self.mode == SeniorRateMode.FIXED_PLUS_MARGIN:
            _require_non_negative_all_in(
                "fixed_base_rate + margin_rate",
                self.fixed_base_rate + self.margin_rate,
            )
        elif self.mode == SeniorRateMode.FLOATING_PLUS_MARGIN:
            for index, reference_rate in enumerate(self.floating_base_rate_curve):
                _require_non_negative_all_in(
                    f"floating all-in rate[{index}]",
                    reference_rate * (1.0 + self.floating_curve_buffer_pct)
                    + self.margin_rate,
                )
        elif self.mode == SeniorRateMode.HEDGE_BLEND:
            fixed_component = (
                self.fixed_base_rate * self.hedge_pct
                + self.swap_margin
                + self.forward_swap_adjustment
                + self.cva
            )
            floating_weight = (1.0 - self.hedge_pct) * (
                1.0 + self.floating_curve_buffer_pct
            )
            for index, reference_rate in enumerate(self.floating_base_rate_curve):
                _require_non_negative_all_in(
                    f"hedge-blend all-in rate[{index}]",
                    fixed_component
                    + reference_rate * floating_weight
                    + self.margin_rate,
                )


@dataclass(frozen=True)
class ConstructionCommitmentFeeInput:
    rate: float = 0.0
    balance_basis: str = "OPENING_UNDRAWN"       # OPENING_UNDRAWN | CLOSING_UNDRAWN
    capitalization_timing: str = "SAME_PERIOD"   # SAME_PERIOD | NEXT_PERIOD

    def __post_init__(self) -> None:
        require_finite_real(
            "commitment_fee.rate",
            self.rate,
            minimum=0.0,
            error_code=_NUMERIC_ERROR,
        )
        if self.balance_basis not in {"OPENING_UNDRAWN", "CLOSING_UNDRAWN"}:
            raise ValueError(
                f"PR9_INVALID_COMMITMENT_FEE_BALANCE_BASIS: {self.balance_basis!r}"
            )
        if self.capitalization_timing not in {"SAME_PERIOD", "NEXT_PERIOD"}:
            raise ValueError(
                "PR9_INVALID_COMMITMENT_FEE_CAPITALIZATION_TIMING: "
                f"{self.capitalization_timing!r}"
            )


@dataclass(frozen=True)
class ConstructionStructuringFeeInput:
    rate: float = 0.0
    basis_keur: float = 0.0
    payment_weights: tuple[float, ...] = field(default_factory=tuple)  # len = n_periods, sum to 1.0

    def __post_init__(self) -> None:
        require_finite_real(
            "structuring_fee.rate",
            self.rate,
            minimum=0.0,
            error_code=_NUMERIC_ERROR,
        )
        require_finite_real(
            "structuring_fee.basis_keur",
            self.basis_keur,
            minimum=0.0,
            error_code=_NUMERIC_ERROR,
        )
        _validate_weights("structuring_fee.payment_weights", self.payment_weights)


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

    def __post_init__(self) -> None:
        if not isinstance(self.start_date, date) or not isinstance(self.end_date, date):
            raise ValueError("PR9_INVALID_PERIOD_DATES: start_date and end_date must be date")
        if self.end_date <= self.start_date:
            raise ValueError("PR9_INVALID_PERIOD_DATES: end_date must be after start_date")
        for name in (
            "active_construction",
            "capex_payment_eligible",
            "senior_idc_active",
            "vat_facility_active",
        ):
            require_bool(name, getattr(self, name), error_code="PR9_INVALID_PERIOD_FLAG")


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

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("PR9_INVALID_CAPEX_CODE: code must be a non-empty string")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("PR9_INVALID_CAPEX_NAME: name must be a non-empty string")
        _validate_weights(f"capex_items[{self.code}].payment_weights", self.payment_weights)
        vat_rate = require_finite_real(
            f"capex_items[{self.code}].vat_rate",
            self.vat_rate,
            error_code=_NUMERIC_ERROR,
        )
        if vat_rate != 0.0:
            raise ValueError(
                "PR9_VAT_FACILITY_DEFERRED: "
                f"capex_items[{self.code}].vat_rate must be exactly 0.0, got {self.vat_rate!r}"
            )


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
        require_bool("enabled", self.enabled, error_code="PR9_INVALID_ENABLED_FLAG")
        if self.vat_deferred is not True:
            raise ValueError("PR9_VAT_FACILITY_DEFERRED: vat_deferred must be True")
        require_finite_real(
            "convergence_tolerance_keur",
            self.convergence_tolerance_keur,
            minimum=0.0,
            strictly_greater=True,
            error_code=_NUMERIC_ERROR,
        )
        require_positive_int(
            "max_iterations", self.max_iterations, error_code="PR9_INVALID_MAX_ITERATIONS"
        )
        if self.idc_balance_basis not in {"OPENING_DRAWN", "CLOSING_DRAWN"}:
            raise ValueError(f"PR9_INVALID_IDC_BALANCE_BASIS: {self.idc_balance_basis!r}")
        if self.idc_capitalization_timing not in {"SAME_PERIOD", "NEXT_PERIOD"}:
            raise ValueError(
                f"PR9_INVALID_IDC_CAPITALIZATION_TIMING: {self.idc_capitalization_timing!r} — "
                "PROFILE mode removed (PR9_PROFILE_DEFERRED). Use SAME_PERIOD or NEXT_PERIOD."
            )
        if not self.enabled:
            return
        n = len(self.periods)
        if n == 0:
            raise ValueError("PR9_CONSTRUCTION_ENABLED_NO_PERIODS: periods must not be empty when enabled")
        if self.senior_pricing is None:
            raise ValueError("PR9_CONSTRUCTION_ENABLED_NO_PRICING: senior_pricing required when enabled")
        if not isinstance(self.senior_pricing, ConstructionSeniorPricingInput):
            raise ValueError("PR9_INVALID_SENIOR_PRICING_TYPE")
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
            if not isinstance(p, ConstructionPeriodSpec):
                raise ValueError(f"PR9_INVALID_PERIOD_TYPE: periods[{i}]={p!r}")
        codes: set[str] = set()
        for i, item in enumerate(self.capex_items):
            if not isinstance(item, ConstructionCapexTimingInput):
                raise ValueError(f"PR9_INVALID_CAPEX_ITEM_TYPE: capex_items[{i}]={item!r}")
            if item.code in codes:
                raise ValueError(f"PR9_DUPLICATE_CAPEX_CODE: {item.code!r}")
            codes.add(item.code)
            # payment_weights: non-negative, length = n_periods, sum = 1.0
            if len(item.payment_weights) != n:
                raise ValueError(f"PR9_CAPEX_WEIGHT_LENGTH_MISMATCH: capex_items[{i}].payment_weights len={len(item.payment_weights)} != n_periods={n}")
            wt_sum = sum(item.payment_weights)
            if len(item.payment_weights) > 0 and abs(wt_sum - 1.0) > _SCHEDULE_TOLERANCE:
                raise ValueError(f"PR9_CAPEX_WEIGHTS_SUM: capex_items[{i}].payment_weights sum={wt_sum} != 1.0")
        if self.commitment_fee is not None:
            if not isinstance(self.commitment_fee, ConstructionCommitmentFeeInput):
                raise ValueError("PR9_INVALID_COMMITMENT_FEE_TYPE")
        if self.structuring_fee is not None:
            if not isinstance(self.structuring_fee, ConstructionStructuringFeeInput):
                raise ValueError("PR9_INVALID_STRUCTURING_FEE_TYPE")
        # Periods in chronological order (consecutive non-overlapping)
        for i in range(1, len(self.periods)):
            if self.periods[i].start_date != self.periods[i - 1].end_date:
                raise ValueError(
                    f"PR9_PERIODS_NOT_CONSECUTIVE: periods[{i-1}].end_date={self.periods[i-1].end_date} "
                    f"!= periods[{i}].start_date={self.periods[i].start_date}"
                )
        if self.structuring_fee is not None and self.structuring_fee.payment_weights:
            sf_weights = self.structuring_fee.payment_weights
            if len(sf_weights) != n:
                raise ValueError(f"PR9_STRUCTURING_FEE_WEIGHT_LENGTH_MISMATCH: len={len(sf_weights)} != n_periods={n}")
            sf_sum = sum(sf_weights)
            if abs(sf_sum - 1.0) > _SCHEDULE_TOLERANCE:
                raise ValueError(f"PR9_STRUCTURING_FEE_WEIGHTS_SUM: sum={sf_sum} != 1.0")
        if self.structuring_fee is not None:
            fee_amount = self.structuring_fee.rate * self.structuring_fee.basis_keur
            if fee_amount > 0.0 and not self.structuring_fee.payment_weights:
                raise ValueError(
                    "PR9_STRUCTURING_FEE_TIMING_REQUIRED: a non-zero structuring fee "
                    "requires explicit payment_weights"
                )


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
