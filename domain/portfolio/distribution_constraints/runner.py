"""Phase 5D.1 distribution constraint evaluation runner.

Pure helper functions. No mutation of source objects.
Not wired into waterfall — this phase is data-model only.
"""
from __future__ import annotations

from typing import Optional

from domain.portfolio.distribution_constraints.inputs import (
    DistributionBlockReason,
    DistributionConstraintConfig,
)
from domain.portfolio.distribution_constraints.result import (
    DistributionConstraintPeriod,
    DistributionConstraintResult,
)


def evaluate_distribution_constraints(
    entity_code: str,
    cash_available_by_period: tuple[float, ...],
    requested_distributions_by_period: tuple[float, ...],
    config: Optional[DistributionConstraintConfig] = None,
) -> DistributionConstraintResult:
    """Evaluate distribution constraints for one entity across periods.

    This is a **pure helper**: it returns a new result object and does not
    mutate any input. It is not wired into the waterfall engine.

    Constraint application order per period:
      1. If config is None or config.enabled is False → pass through unchanged
      2. Apply manual lockup → allowed = 0, reason = MANUAL_LOCKUP
      3. Apply minimum cash reserve → allowed <= cash - minimum_reserve
      4. Check negative cash → add NEGATIVE_CASH reason if cash < 0

    Parameters
    ----------
    entity_code : str
        SPV or HoldCo entity code
    cash_available_by_period : tuple[float, ...]
        Cash available for distribution per period (kEUR).
        Typically: opening_cash + CFADS - senior_debt - DSRF - tax - SHL - ...
    requested_distributions_by_period : tuple[float, ...]
        Requested distribution per period from waterfall (kEUR).
        This is the distribution_keur or adjusted_period_distributions_keur.
    config : DistributionConstraintConfig | None
        Constraint configuration. If None or enabled=False, all
        distributions pass through unchanged.

    Returns
    -------
    DistributionConstraintResult
        Per-period constraint evaluation results with allowed amounts,
        retained cash, and block reasons.

    Notes
    -----
    - allowed_distribution <= requested_distribution always holds
    - retained_cash_keur = cash_before - allowed_distribution
    - When config.enabled=False (default): this function is a pass-through
    """
    if config is None or not config.enabled:
        return _pass_through(
            entity_code, cash_available_by_period, requested_distributions_by_period
        )

    lockup_set = set(config.manual_lockup_periods)
    min_reserve = config.minimum_cash_reserve_keur
    allow_neg = config.allow_negative_cash

    periods: list[DistributionConstraintPeriod] = []
    all_warnings: list[str] = []

    n = max(len(cash_available_by_period), len(requested_distributions_by_period))

    for i in range(n):
        cash = cash_available_by_period[i] if i < len(cash_available_by_period) else 0.0
        requested = (
            requested_distributions_by_period[i]
            if i < len(requested_distributions_by_period)
            else 0.0
        )

        reasons: list[DistributionBlockReason] = []
        warnings: list[str] = []
        allowed = requested

        # 1. Manual lockup
        if i in lockup_set:
            allowed = 0.0
            reasons.append(DistributionBlockReason.MANUAL_LOCKUP)

        # 2. Minimum cash reserve
        if allowed > 0:
            max_allowed_after_reserve = max(0.0, cash - min_reserve)
            if max_allowed_after_reserve < allowed:
                allowed = max_allowed_after_reserve
                if DistributionBlockReason.MANUAL_LOCKUP not in reasons:
                    reasons.append(DistributionBlockReason.MINIMUM_CASH_RESERVE)

        # 3. Negative cash
        if cash < 0 and not allow_neg:
            reasons.append(DistributionBlockReason.NEGATIVE_CASH)
            warnings.append(
                f"Period {i}: negative cash {cash:.1f} kEUR — "
                f"distribution allowed but cash is negative"
            )

        retained = cash - allowed

        periods.append(DistributionConstraintPeriod(
            period=i,
            entity_code=entity_code,
            cash_before_distribution_keur=cash,
            requested_distribution_keur=requested,
            allowed_distribution_keur=allowed,
            retained_cash_keur=retained,
            block_reasons=tuple(reasons),
            warnings=tuple(warnings),
        ))
        all_warnings.extend(warnings)

    return DistributionConstraintResult(
        entity_code=entity_code,
        periods=tuple(periods),
        total_requested_distribution_keur=sum(p.requested_distribution_keur for p in periods),
        total_allowed_distribution_keur=sum(p.allowed_distribution_keur for p in periods),
        total_retained_cash_keur=sum(p.retained_cash_keur for p in periods),
        warnings=tuple(all_warnings),
    )


def _pass_through(
    entity_code: str,
    cash_available_by_period: tuple[float, ...],
    requested_distributions_by_period: tuple[float, ...],
) -> DistributionConstraintResult:
    """No constraints applied — pass everything through unchanged."""
    n = max(len(cash_available_by_period), len(requested_distributions_by_period))
    periods: list[DistributionConstraintPeriod] = []

    for i in range(n):
        cash = cash_available_by_period[i] if i < len(cash_available_by_period) else 0.0
        requested = (
            requested_distributions_by_period[i]
            if i < len(requested_distributions_by_period)
            else 0.0
        )
        periods.append(DistributionConstraintPeriod(
            period=i,
            entity_code=entity_code,
            cash_before_distribution_keur=cash,
            requested_distribution_keur=requested,
            allowed_distribution_keur=requested,
            retained_cash_keur=cash - requested,
            block_reasons=(),
            warnings=(),
        ))

    return DistributionConstraintResult(
        entity_code=entity_code,
        periods=tuple(periods),
        total_requested_distribution_keur=sum(p.requested_distribution_keur for p in periods),
        total_allowed_distribution_keur=sum(p.allowed_distribution_keur for p in periods),
        total_retained_cash_keur=sum(p.retained_cash_keur for p in periods),
        warnings=(),
    )