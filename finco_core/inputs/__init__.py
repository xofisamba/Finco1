"""
finco_core.inputs — Typed input models for the Finco One financial engine.

V2-2 status: EXTRACTED. All primary input models are now defined here.
Legacy locations (domain/inputs.py, domain/senior_rate_schedule.py,
domain/senior_sculpting.py) re-export from this package for backward
compatibility.

Public API — re-exported from submodules:
    From finco_core.inputs._models:
        PeriodFrequency, EquityIRRMethod, DebtSizingMethod, DebtSizingMode,
        SHLRepaymentMethod, YieldScenario, AssetClass, ASSET_CLASS_USEFUL_LIFE,
        ProjectInfo, CapexItem, CapexStructure, OpexItem, TechnicalParams,
        RevenueAdjustmentSchedule, RevenueParams, FinancingParams, TaxParams,
        ProjectInputs, hash_inputs_for_cache

    From finco_core.inputs.senior_rate_schedule:
        SeniorRateMode, SeniorDayCountConvention, SeniorHedgeConfig,
        SeniorRateSchedule, SeniorDebtInterestConfig,
        build_senior_period_rate_schedule, senior_period_fraction

    From finco_core.inputs.senior_sculpting:
        SeniorSculptingMode, SeniorFinalRepaymentPolicy, SeniorPrincipalCapPolicy,
        SeniorReserveTreatment, SeniorSculptingConfig,
        validate_explicit_debt_service_schedule

    From finco_core.inputs.bess:
        BessParams
"""
from finco_core.inputs.bess import BessParams
from finco_core.inputs._models import (
    PeriodFrequency,
    EquityIRRMethod,
    DebtSizingMethod,
    DebtSizingMode,
    SHLRepaymentMethod,
    YieldScenario,
    AssetClass,
    ASSET_CLASS_USEFUL_LIFE,
    ProjectInfo,
    CapexItem,
    CapexStructure,
    OpexItem,
    TechnicalParams,
    RevenueAdjustmentSchedule,
    RevenueParams,
    FinancingParams,
    TaxParams,
    ProjectInputs,
    hash_inputs_for_cache,
)
from finco_core.inputs.senior_rate_schedule import (
    SeniorRateMode,
    SeniorDayCountConvention,
    SeniorHedgeConfig,
    SeniorRateSchedule,
    SeniorDebtInterestConfig,
    build_senior_period_rate_schedule,
    senior_period_fraction,
)
from finco_core.inputs.senior_sculpting import (
    SeniorSculptingMode,
    SeniorFinalRepaymentPolicy,
    SeniorPrincipalCapPolicy,
    SeniorReserveTreatment,
    SeniorSculptingConfig,
    validate_explicit_debt_service_schedule,
)

__all__ = [
    # Enums and constants
    "PeriodFrequency",
    "EquityIRRMethod",
    "DebtSizingMethod",
    "DebtSizingMode",
    "SHLRepaymentMethod",
    "YieldScenario",
    "AssetClass",
    "ASSET_CLASS_USEFUL_LIFE",
    # Core input dataclasses
    "ProjectInfo",
    "CapexItem",
    "CapexStructure",
    "OpexItem",
    "TechnicalParams",
    "RevenueAdjustmentSchedule",
    "RevenueParams",
    "FinancingParams",
    "TaxParams",
    "ProjectInputs",
    # BESS input model
    "BessParams",
    # Functions
    "hash_inputs_for_cache",
    # Senior rate schedule
    "SeniorRateMode",
    "SeniorDayCountConvention",
    "SeniorHedgeConfig",
    "SeniorRateSchedule",
    "SeniorDebtInterestConfig",
    "build_senior_period_rate_schedule",
    "senior_period_fraction",
    # Senior sculpting
    "SeniorSculptingMode",
    "SeniorFinalRepaymentPolicy",
    "SeniorPrincipalCapPolicy",
    "SeniorReserveTreatment",
    "SeniorSculptingConfig",
    "validate_explicit_debt_service_schedule",
]
