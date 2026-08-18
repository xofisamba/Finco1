"""
finco_core.inputs — Typed input models for the Finco One financial engine.

V2-2 status: EXTRACTED. All primary input models are now defined here.
Legacy locations (domain/inputs.py, domain/senior_rate_schedule.py,
domain/senior_sculpting.py) re-export from this package for backward
compatibility.

Public API — re-exported from submodules:
    From finco_core.inputs._models:
        PeriodFrequency, EquityIRRMethod, DebtSizingMethod, DebtSizingMode,
        PeriodAxisConvention, SHLRepaymentMethod, YieldScenario, AssetClass,
        ASSET_CLASS_USEFUL_LIFE,
        ProjectInfo, CapexItem, CapexStructure, OpexItem, TechnicalParams,
        RevenueAdjustmentSchedule, RevenueParams, DebtSizingCaseConfig,
        FinancingParams, TaxParams, ProjectInputs, hash_inputs_for_cache

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

    From finco_core.inputs.serialization (V3-6):
        project_inputs_to_dict, project_inputs_from_dict
"""
from finco_core.inputs.bess import BessParams
from finco_core.inputs.serialization import project_inputs_to_dict, project_inputs_from_dict
from finco_core.inputs._models import (
    PeriodFrequency,
    PeriodAxisConvention,
    EquityIRRMethod,
    DebtSizingMethod,
    DebtSizingMode,
    SponsorFundingMode,
    GearingBasisMode,
    DebtServiceReserveSupportMode,
    DsrfDayCountConvention,
    DsrfCommitmentFeeTreatment,
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
    DebtSizingCaseConfig,
    FinancingParams,
    TaxParams,
    TaxDepreciationMode,
    ShlInterestDeductibilityMode,
    TaxLossUtilisationGate,
    TaxPeriodisationMode,
    ShlAccountingTreatment,
    ShlPaymentMethod,
    ShlConstructionInterestMethod,
    ProjectInputs,
    hash_inputs_for_cache,
    DsrfDayCountConvention,
    DsrfCommitmentFeeTreatment,
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
    "PeriodAxisConvention",
    "EquityIRRMethod",
    "DebtSizingMethod",
    "DebtSizingMode",
    "SponsorFundingMode",
    "GearingBasisMode",
    "DebtServiceReserveSupportMode",
    "DsrfDayCountConvention",
    "DsrfCommitmentFeeTreatment",
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
    "DebtSizingCaseConfig",
    "FinancingParams",
    "TaxParams",
    "TaxDepreciationMode",
    "ShlInterestDeductibilityMode",
    "TaxLossUtilisationGate",
    "TaxPeriodisationMode",
    "ShlAccountingTreatment",
    "ShlPaymentMethod",
    "ShlConstructionInterestMethod",
    "ProjectInputs",
    # BESS input model
    "BessParams",
    # Serialization (V3-6)
    "project_inputs_to_dict",
    "project_inputs_from_dict",
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
    # DSRF
    "DsrfDayCountConvention",
    "DsrfCommitmentFeeTreatment",
]
