"""Pure C2 dated discounting, Project NPV, LLCR and PLCR calculations."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from numbers import Real

from finco_core.inputs.valuation import (
    CoverageCfadsCase,
    DebtCoverageValuationPolicy,
    DiscountConvention,
    ProjectValuationPolicy,
    ValuationDatePolicy,
)
from financial_engine.project_returns.contracts import ProjectReturnStatus
from financial_engine.valuation.contracts import (
    CoverageMetric,
    CoverageRatioResult,
    CoverageStatus,
    DecisionCompleteValuationSummary,
    DiscountAuditRow,
    LenderCoverageResult,
    LlcrThresholdStatus,
    ProjectNpvResult,
    ProjectNpvStatus,
)

_TOL = 1e-9
_MAX_RATE = 10.0
_PROJECT_CASHFLOW_AUTHORITY = "C1_PROJECT_RETURN_RESULT_CASHFLOWS_EXACT"


class _DiscountError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class _DatedAmount:
    period_index: int | None
    cashflow_date: date
    amount_keur: float
    included: bool = True
    exclusion_reason: str | None = None


def _validated_rate(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise _DiscountError("INVALID_DISCOUNT_RATE")
    rate = float(value)
    if not math.isfinite(rate) or rate <= -1.0 or rate > _MAX_RATE:
        raise _DiscountError("INVALID_DISCOUNT_RATE")
    return rate


def discount_dated_cashflows(
    *,
    valuation_date: date,
    cashflows: tuple[_DatedAmount, ...],
    annual_discount_rate: object,
    convention: DiscountConvention,
) -> tuple[tuple[DiscountAuditRow, ...], float]:
    """Discount one dated vector once; ACT/365 Fixed is the only C2 convention."""
    if convention is not DiscountConvention.ACT_365_FIXED:
        raise _DiscountError("UNSUPPORTED_DISCOUNT_CONVENTION")
    rate = _validated_rate(annual_discount_rate)
    rows: list[DiscountAuditRow] = []
    total = 0.0
    for cashflow in cashflows:
        if not cashflow.included:
            rows.append(DiscountAuditRow(
                period_index=cashflow.period_index,
                cashflow_date=cashflow.cashflow_date,
                undiscounted_cashflow_keur=cashflow.amount_keur,
                included=False,
                exclusion_reason=cashflow.exclusion_reason,
                year_fraction=None,
                discount_factor=None,
                discounted_cashflow_keur=None,
            ))
            continue
        days = (cashflow.cashflow_date - valuation_date).days
        if days < 0:
            raise _DiscountError("CASHFLOW_BEFORE_UNSUPPORTED_VALUATION_DATE")
        year_fraction = days / 365.0
        discount_factor = (1.0 + rate) ** year_fraction
        discounted = float(cashflow.amount_keur) / discount_factor
        if not all(math.isfinite(v) for v in (year_fraction, discount_factor, discounted)):
            raise _DiscountError("NON_FINITE_RESULT")
        total += discounted
        rows.append(DiscountAuditRow(
            period_index=cashflow.period_index,
            cashflow_date=cashflow.cashflow_date,
            undiscounted_cashflow_keur=float(cashflow.amount_keur),
            included=True,
            exclusion_reason=None,
            year_fraction=year_fraction,
            discount_factor=discount_factor,
            discounted_cashflow_keur=discounted,
        ))
    if not math.isfinite(total):
        raise _DiscountError("NON_FINITE_RESULT")
    return tuple(rows), total


def calculate_project_npv(project_return, policy: ProjectValuationPolicy | None) -> ProjectNpvResult:
    if policy is None:
        return ProjectNpvResult(
            status=ProjectNpvStatus.NOT_CONFIGURED,
            npv_keur=None,
            valuation_date=None,
            annual_discount_rate=None,
            discount_convention=None,
            discount_authority=None,
            cashflow_identity_authority=_PROJECT_CASHFLOW_AUTHORITY,
            periods=(),
        )
    if policy.annual_discount_rate is None:
        return ProjectNpvResult(
            status=ProjectNpvStatus.NOT_CONFIGURED,
            npv_keur=None,
            valuation_date=None,
            annual_discount_rate=None,
            discount_convention=policy.discount_convention,
            discount_authority=policy.authority_label,
            cashflow_identity_authority=_PROJECT_CASHFLOW_AUTHORITY,
            periods=(),
        )
    if project_return.project_xirr_status is not ProjectReturnStatus.OK:
        return ProjectNpvResult(
            status=ProjectNpvStatus.UPSTREAM_PROJECT_RETURN_UNAVAILABLE,
            npv_keur=None,
            valuation_date=None,
            annual_discount_rate=policy.annual_discount_rate,
            discount_convention=policy.discount_convention,
            discount_authority=policy.authority_label,
            cashflow_identity_authority=_PROJECT_CASHFLOW_AUTHORITY,
            periods=(),
            upstream_project_return_status=project_return.project_xirr_status.value,
        )
    cashflows = tuple(project_return.cashflows)
    valuation_date = (
        cashflows[0].cashflow_date
        if policy.valuation_date_policy is ValuationDatePolicy.FIRST_PROJECT_CASHFLOW_DATE
        and cashflows
        else policy.explicit_valuation_date
    )
    if valuation_date is None:
        return ProjectNpvResult(
            status=ProjectNpvStatus.VALUATION_DATE_UNAVAILABLE,
            npv_keur=None,
            valuation_date=None,
            annual_discount_rate=policy.annual_discount_rate,
            discount_convention=policy.discount_convention,
            discount_authority=policy.authority_label,
            cashflow_identity_authority=_PROJECT_CASHFLOW_AUTHORITY,
            periods=(),
        )
    dated = tuple(
        _DatedAmount(
            period_index=None,
            cashflow_date=row.cashflow_date,
            amount_keur=row.net_unlevered_project_cashflow_keur,
        )
        for row in cashflows
    )
    try:
        rows, npv = discount_dated_cashflows(
            valuation_date=valuation_date,
            cashflows=dated,
            annual_discount_rate=policy.annual_discount_rate,
            convention=policy.discount_convention,
        )
    except _DiscountError as exc:
        status = {
            "INVALID_DISCOUNT_RATE": ProjectNpvStatus.INVALID_DISCOUNT_RATE,
            "CASHFLOW_BEFORE_UNSUPPORTED_VALUATION_DATE": (
                ProjectNpvStatus.CASHFLOW_BEFORE_UNSUPPORTED_VALUATION_DATE
            ),
        }.get(exc.code, ProjectNpvStatus.NON_FINITE_RESULT)
        return ProjectNpvResult(
            status=status,
            npv_keur=None,
            valuation_date=valuation_date,
            annual_discount_rate=policy.annual_discount_rate,
            discount_convention=policy.discount_convention,
            discount_authority=policy.authority_label,
            cashflow_identity_authority=_PROJECT_CASHFLOW_AUTHORITY,
            periods=(),
        )
    return ProjectNpvResult(
        status=ProjectNpvStatus.OK,
        npv_keur=npv,
        valuation_date=valuation_date,
        annual_discount_rate=float(policy.annual_discount_rate),
        discount_convention=policy.discount_convention,
        discount_authority=policy.authority_label,
        cashflow_identity_authority=_PROJECT_CASHFLOW_AUTHORITY,
        periods=rows,
        upstream_project_return_status=project_return.project_xirr_status.value,
    )


def _coverage_failure(
    metric: CoverageMetric,
    status: CoverageStatus,
    policy: DebtCoverageValuationPolicy | None,
) -> CoverageRatioResult:
    return CoverageRatioResult(
        metric=metric,
        status=status,
        calculation_date=None,
        cfads_case=None if policy is None else policy.cfads_case,
        annual_discount_rate=None if policy is None else policy.annual_discount_rate,
        discount_convention=None if policy is None else policy.discount_convention,
        discount_authority=None if policy is None else policy.authority_label,
        debt_balance_denominator_keur=None,
        pv_cfads_numerator_keur=None,
        ratio=None,
        periods=(),
    )


def _coverage_metric(
    *,
    metric: CoverageMetric,
    model,
    senior_terminal,
    policy: DebtCoverageValuationPolicy | None,
) -> CoverageRatioResult:
    senior = model.senior_debt
    if senior is None or float(senior.debt_size_keur) <= _TOL:
        return _coverage_failure(metric, CoverageStatus.NOT_APPLICABLE_NO_SENIOR, policy)
    if policy is None or policy.cfads_case is None:
        return _coverage_failure(
            metric, CoverageStatus.COVERAGE_CFADS_CASE_NOT_CONFIGURED, policy
        )
    if policy.annual_discount_rate is None:
        return _coverage_failure(
            metric, CoverageStatus.COVERAGE_DISCOUNT_RATE_NOT_CONFIGURED, policy
        )
    if senior_terminal.contractual_maturity_period_index is None:
        return _coverage_failure(metric, CoverageStatus.SENIOR_MATURITY_UNAVAILABLE, policy)

    periods = tuple(model.periods)
    indices = tuple(period.period_index for period in periods)
    if len(indices) != len(set(indices)):
        return _coverage_failure(metric, CoverageStatus.PERIOD_AXIS_MISMATCH, policy)
    period_by_index = {period.period_index: period for period in periods}
    senior_indices = tuple(senior.period_indices)
    if len(senior_indices) != len(set(senior_indices)) or any(
        index not in period_by_index for index in senior_indices
    ):
        return _coverage_failure(metric, CoverageStatus.PERIOD_AXIS_MISMATCH, policy)
    senior_opening = dict(zip(senior_indices, senior.senior_debt_opening_keur))
    measurement_index = next(
        (index for index in senior_indices if senior_opening[index] > _TOL), None
    )
    if measurement_index is None:
        return _coverage_failure(metric, CoverageStatus.DEBT_BALANCE_ZERO, policy)
    measurement_period = period_by_index[measurement_index]
    calculation_date = measurement_period.period_start

    if policy.cfads_case is CoverageCfadsCase.BASE:
        schedules = model.tax_and_cfads
        cfads_indices = () if schedules is None else tuple(schedules.period_indices)
        cfads_values = () if schedules is None else tuple(schedules.cfads_keur)
    else:
        schedules = model.debt_sizing
        cfads_indices = () if schedules is None else tuple(schedules.period_indices)
        cfads_values = () if schedules is None else tuple(schedules.bank_cfads_keur)
    if cfads_indices != indices or len(cfads_values) != len(indices):
        return _coverage_failure(metric, CoverageStatus.PERIOD_AXIS_MISMATCH, policy)
    cfads_by_index = dict(zip(cfads_indices, cfads_values))

    operating = tuple(period for period in periods if period.is_operation)
    if not operating:
        return _coverage_failure(
            metric, CoverageStatus.PROJECT_LIFE_HORIZON_UNAVAILABLE, policy
        )
    horizon = (
        senior_terminal.contractual_maturity_period_index
        if metric is CoverageMetric.LLCR
        else operating[-1].period_index
    )
    dated: list[_DatedAmount] = []
    for period in operating:
        included = measurement_index <= period.period_index <= horizon
        reason = None
        if period.period_index < measurement_index:
            reason = "BEFORE_CALCULATION_PERIOD"
        elif period.period_index > horizon:
            reason = (
                "AFTER_SENIOR_CONTRACTUAL_MATURITY"
                if metric is CoverageMetric.LLCR
                else "AFTER_PROJECT_LIFE"
            )
        dated.append(_DatedAmount(
            period_index=period.period_index,
            cashflow_date=period.period_end,
            amount_keur=float(cfads_by_index[period.period_index]),
            included=included,
            exclusion_reason=reason,
        ))
    try:
        audit_rows, numerator = discount_dated_cashflows(
            valuation_date=calculation_date,
            cashflows=tuple(dated),
            annual_discount_rate=policy.annual_discount_rate,
            convention=policy.discount_convention,
        )
    except _DiscountError as exc:
        status = (
            CoverageStatus.INVALID_DISCOUNT_RATE
            if exc.code == "INVALID_DISCOUNT_RATE"
            else CoverageStatus.NON_FINITE_RESULT
        )
        return _coverage_failure(metric, status, policy)
    denominator = float(senior_opening[measurement_index])
    if denominator <= _TOL:
        return _coverage_failure(metric, CoverageStatus.DEBT_BALANCE_ZERO, policy)
    ratio = numerator / denominator
    if not math.isfinite(ratio):
        return _coverage_failure(metric, CoverageStatus.NON_FINITE_RESULT, policy)
    return CoverageRatioResult(
        metric=metric,
        status=CoverageStatus.OK,
        calculation_date=calculation_date,
        cfads_case=policy.cfads_case,
        annual_discount_rate=float(policy.annual_discount_rate),
        discount_convention=policy.discount_convention,
        discount_authority=policy.authority_label,
        debt_balance_denominator_keur=denominator,
        pv_cfads_numerator_keur=numerator,
        ratio=ratio,
        periods=audit_rows,
    )


def calculate_lender_coverage(
    *,
    model,
    senior_terminal,
    policy: DebtCoverageValuationPolicy | None,
    minimum_llcr: float | None,
) -> LenderCoverageResult:
    llcr = _coverage_metric(
        metric=CoverageMetric.LLCR,
        model=model,
        senior_terminal=senior_terminal,
        policy=policy,
    )
    plcr = _coverage_metric(
        metric=CoverageMetric.PLCR,
        model=model,
        senior_terminal=senior_terminal,
        policy=policy,
    )
    if llcr.status is not CoverageStatus.OK:
        threshold_status = LlcrThresholdStatus.NOT_APPLICABLE
        headroom = None
    elif minimum_llcr is None or not math.isfinite(float(minimum_llcr)):
        threshold_status = LlcrThresholdStatus.NOT_CONFIGURED
        headroom = None
    else:
        headroom = float(llcr.ratio) - float(minimum_llcr)
        threshold_status = (
            LlcrThresholdStatus.PASS if headroom >= -_TOL else LlcrThresholdStatus.FAIL
        )
    return LenderCoverageResult(
        llcr=llcr,
        plcr=plcr,
        minimum_llcr=None if minimum_llcr is None else float(minimum_llcr),
        llcr_headroom=headroom,
        llcr_threshold_status=threshold_status,
    )


def build_decision_complete_valuation_summary(
    *,
    project_inputs,
    financing,
    project_return,
    senior_terminal,
) -> DecisionCompleteValuationSummary:
    policies = project_inputs.valuation
    return DecisionCompleteValuationSummary(
        project_npv=calculate_project_npv(project_return, policies.project),
        lender_coverage=calculate_lender_coverage(
            model=financing.project_model_result,
            senior_terminal=senior_terminal,
            policy=policies.coverage,
            minimum_llcr=project_inputs.financing.min_llcr,
        ),
    )
