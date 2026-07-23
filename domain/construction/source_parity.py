"""Source-parity construction/VAT primitives for Oborovo Stage B2.

The constants in this module are reviewer-confirmed workbook evidence.  They are
not target-derived backsolves: hard-CAPEX payments drive VAT/payable uses, while
source total-uses and senior/VAT balances are validation series.
"""
from __future__ import annotations

from datetime import date

from finco_core.construction import (
    CapexPaymentItem,
    CapexScheduleSet,
    ConstructionRuntimeConfig,
    FinancingCostFundingPolicy,
    TimelinePeriod,
)

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


OBOROVO_SOURCE_VAT_PAYABLE_KEUR: tuple[float, ...] = (
    2560.7482783333344,
    463.44833333333344,
    463.44833333333344,
    463.44833333333344,
    463.44833333333344,
    463.44833333333344,
    463.44833333333344,
    463.44833333333344,
    463.44833333333344,
    466.3383333333334,
    463.44833333333344,
    466.56392333333343,
)

VAT_COSTS_SPENDING_PROFILE: tuple[float, ...] = (0.25, 0.15, 0.15, 0.15, 0.15, 0.15, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
VAT_INTEREST_FRACTIONS: tuple[float, ...] = (
    2 / 360, 31 / 360, 31 / 360, 30 / 360, 31 / 360, 30 / 360,
    31 / 360, 31 / 360, 28 / 360, 31 / 360, 30 / 360, 31 / 360,
    30 / 360, 31 / 360, 31 / 360, 30 / 360, 31 / 360, 30 / 360,
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
        CapexPaymentItem("C.10", "Commissioning", 17.000, (0.0,)*9 + (1.0,) + (0.0,)*2, vat, provenance_classification="DIRECT_SOURCE"),
        CapexPaymentItem("C.11", "Project Acquisition / Project Development", 18.327, (0.0,)*11 + (1.0,), vat, provenance_classification="DIRECT_SOURCE"),
    ))


def oborovo_source_config() -> ConstructionRuntimeConfig:
    """Build the Oborovo config consumed by canonical finco_core.construction.run_stage_b2()."""
    return ConstructionRuntimeConfig(
        timeline=oborovo_timeline(),
        capex_schedule=oborovo_capex_schedule(),
        funding_policy=FinancingCostFundingPolicy(structuring_fee_payment_schedule=M1_ONLY),
        source_total_uses_validation_keur=SOURCE_TOTAL_USES_VALIDATION_KEUR,
        equity_available_keur=500.0,
        shl_available_keur=14_620.773895,
        senior_commitment_keur=42_852.266726,
        senior_interest_rate=0.05169,
        senior_commitment_fee_rate=0.0105,
        structuring_fee_rate=0.01,
        structuring_fee_basis_keur=47_730.2687,
        vat_facility_interest_rate=0.0565,
        vat_facility_commitment_fee_rate=0.009275,
        vat_facility_commitment_keur=4_877.989945,
        vat_interest_period_fractions=VAT_INTEREST_FRACTIONS,
        vat_commitment_fee_active_periods=12,
        senior_idc_spending_profile=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0),
        senior_commitment_fee_spending_profile=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0),
        vat_financing_cost_spending_profile=VAT_COSTS_SPENDING_PROFILE,
    )


__all__ = [name for name in globals() if name.startswith("OBOROVO") or name in {"SOURCE_TOTAL_USES_VALIDATION_KEUR", "OBOROVO_SOURCE_VAT_PAYABLE_KEUR", "VAT_COSTS_SPENDING_PROFILE", "VAT_INTEREST_FRACTIONS", "EQUAL_12", "M1_ONLY", "oborovo_capex_schedule", "oborovo_source_config", "oborovo_timeline"}]
