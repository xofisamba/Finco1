"""app.services.clean_presentation_adapter — PR-8 read-only result adapter.

Maps the canonical clean result (CovenantGatedWaterfallResult +
ProjectModelResult) onto the field names the existing read-only presentation
layer expects (output_tables builders, schedule serializers, KPI extraction).

PR-8 presentation-adapter contract:
  MAY     rename fields / format / aggregate for display / serialize;
  MAY NOT rerun any engine, reconstruct tax/CFADS/Senior/DSCR/SHL/
          distributions, repair values, or mix clean and legacy vectors.

Every mapped value is a pass-through of one clean computed vector. Legacy-only
concepts with no clean counterpart (cash balance roll-forward, LLCR, PLCR,
NPV metrics, unlevered Project IRR) surface as None plus an explicit
machine-readable unavailable-fields manifest — never a legacy value.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from finco_core.engine.period_engine import map_period_vector
from financial_engine.shareholder_waterfall.contracts import (
    DistributionGateStatus,
)

_UNAVAILABLE_FIELDS = {
    "project_irr": (
        "PR8_NOT_AVAILABLE: unlevered Project IRR is not provided by the clean "
        "G2C runtime; not reconstructed from the legacy waterfall."
    ),
    "project_npv_keur": (
        "PR8_NOT_AVAILABLE: Project NPV is not provided by the clean G2C runtime."
    ),
    "equity_npv_keur": (
        "PR8_NOT_AVAILABLE: Equity NPV is not provided by the clean G2C runtime."
    ),
    "min_llcr": (
        "PR8_NOT_AVAILABLE: LLCR framework is deferred (PR-8 scope exclusion)."
    ),
    "llcr": (
        "PR8_NOT_AVAILABLE: LLCR framework is deferred (PR-8 scope exclusion)."
    ),
    "plcr": (
        "PR8_NOT_AVAILABLE: PLCR framework is deferred (PR-8 scope exclusion)."
    ),
    "cash_balance_keur": (
        "PR8_NOT_AVAILABLE: legacy cash-balance roll-forward has no clean "
        "counterpart; post-Senior/DSRA/DA/SHL vectors are the clean authority."
    ),
    "financial_statements": (
        "PR8_NOT_AVAILABLE: financial-statements assembly over the clean "
        "runtime is deferred; schedules below are the clean authority."
    ),
    "tax_depreciation_audit_keur": (
        "PR8_NOT_AVAILABLE: legacy tax-depreciation audit bridge is not part "
        "of the clean result."
    ),
}


@dataclass
class CleanPeriodView:
    """Read-only legacy-shaped view over ONE period of the clean result."""

    period: int
    date: object | None
    year_index: int | None
    period_in_year: int | None
    is_operation: bool
    is_construction: bool
    # operating
    generation_mwh: float | None
    revenue_keur: float | None
    opex_keur: float | None
    ebitda_keur: float | None
    depreciation_keur: float | None
    taxable_profit_keur: float | None
    cash_tax_keur: float | None
    cf_after_tax_keur: float | None
    # senior
    senior_interest_keur: float | None
    senior_principal_keur: float | None
    senior_ds_keur: float | None
    senior_balance_keur: float | None
    dscr: float | None
    # reserves / waterfall
    dsra_contribution_keur: float | None
    dsra_balance_keur: float | None
    cf_after_reserves_keur: float | None
    # SHL
    shl_service_keur: float | None
    shl_interest_keur: float | None
    shl_balance_keur: float | None
    # additional read-only SHL detail (cash vs accrual distinctions preserved)
    shl_cash_interest_keur: float | None = None
    shl_gross_interest_keur: float | None = None
    shl_principal_keur: float | None = None
    shl_pik_keur: float | None = None
    # distributions
    distribution_keur: float | None = None
    lockup_active: bool = False
    distribution_source: str = "clean_g2c_cf109_gate"
    # explicitly NOT available in the clean runtime
    cash_balance_keur: float | None = None
    llcr: float | None = None
    plcr: float | None = None
    tax_keur: float | None = None
    corporate_tax_cash_keur: float | None = None
    senior_debt_service_keur: float | None = None
    senior_interest_expense_keur: float | None = None
    shl_interest_expense_keur: float | None = None
    senior_debt_balance_keur: float | None = None
    distributions_keur: float | None = None
    mra_balance_keur: float | None = None
    mra_contribution_keur: float | None = None


@dataclass
class CleanWaterfallView:
    """Read-only legacy-shaped view over the full clean result.

    Only aggregate/format fields are derived (sums, min/avg of already
    computed DSCR vectors, date labels) — allowed presentation aggregation.
    """

    periods: list
    total_revenue_keur: float | None
    total_opex_keur: float | None
    total_ebitda_keur: float | None
    total_tax_keur: float | None
    total_senior_ds_keur: float | None
    total_shl_service_keur: float | None
    total_distribution_keur: float | None
    actual_min_dscr: float | None
    actual_avg_dscr: float | None
    target_dscr: float | None
    equity_irr: float | None
    sponsor_irr: float | None
    periods_in_lockup: int
    project_irr: float | None = None
    sponsor_irr_status: str | None = None
    equity_irr_status: str | None = None
    distribution_source: str = "clean_g2c_cf109_gate"
    min_llcr: float | None = None
    project_npv: float | None = None
    equity_npv: float | None = None
    _authority_metadata: dict = field(default_factory=dict)


def _at(vector, index: int):
    try:
        value = vector[index]
    except (IndexError, TypeError, KeyError):
        return None
    return None if value is None else float(value)


def _sum_or_none(vector) -> float | None:
    if vector is None:
        return None
    try:
        return float(sum(vector))
    except TypeError:
        return None


def build_clean_waterfall_view(clean_run) -> CleanWaterfallView:
    """Adapt one CleanProductionRun into the legacy-shaped read-only view."""
    g2c = clean_run.g2c_result
    model = g2c.financing_result.project_model_result
    op = model.operating_schedules
    tax = model.tax_and_cfads
    senior = model.senior_debt

    op_by_idx = map_period_vector(
        op.period_indices,
        tuple(range(len(op.period_indices))),
        label="clean_presentation.operating",
    )
    tax_by_idx = map_period_vector(
        tax.period_indices,
        tuple(range(len(tax.period_indices))),
        label="clean_presentation.tax",
    )
    senior_by_idx = map_period_vector(
        senior.period_indices,
        tuple(range(len(senior.period_indices))),
        label="clean_presentation.senior_debt",
    )
    # The G2C waterfall grid and the model period grid use DIFFERENT
    # numbering axes (waterfall period_index is 1-based over its own
    # construction+operating axis; model schedules are 0-based). The stable
    # join key is the period END DATE (waterfall cashflow_date == model
    # period_end). Construction boundary columns that exist only on one axis
    # carry no waterfall cash event and default to no-SHL/DA activity.
    wp_by_date: dict = {}
    for w in g2c.waterfall_periods:
        cashflow_date = getattr(w, "cashflow_date", None)
        if cashflow_date in wp_by_date:
            raise ValueError(
                "PERIOD_VECTOR_DUPLICATE_DATES: clean_presentation.waterfall_periods"
            )
        wp_by_date[cashflow_date] = w

    period_views: list[CleanPeriodView] = []
    lockup_count = 0
    for mp in model.periods:
        idx = mp.period_index
        oi = op_by_idx.get(idx)
        ti = tax_by_idx.get(idx)
        si = senior_by_idx.get(idx)
        wp = wp_by_date.get(getattr(mp, "period_end", None))

        dscr = _at(senior.base_dscr, si) if si is not None else None
        cash_tax = _at(tax.corporate_tax_cash_keur, ti) if ti is not None else None
        senior_ds = _at(senior.senior_debt_service_keur, si) if si is not None else None
        senior_close = _at(senior.senior_debt_closing_keur, si) if si is not None else None
        senior_interest = _at(senior.senior_interest_keur, si) if si is not None else None
        senior_principal = _at(senior.senior_principal_keur, si) if si is not None else None

        shl_interest = getattr(wp, "shl_gross_interest_keur", None) if wp else 0.0
        shl_cash_interest = getattr(wp, "shl_cash_interest_receipt_keur", None) if wp else 0.0
        shl_principal_paid = getattr(wp, "actual_shl_principal_paid_keur", None) if wp else 0.0
        shl_close = getattr(wp, "actual_shl_closing_balance_keur", None) if wp else 0.0

        gate = getattr(wp, "distribution_gate_status", None) if wp else None
        lockup_active = gate in (
            DistributionGateStatus.LOCKED_DSCR_BELOW_LOCKUP,
            DistributionGateStatus.LOCKED_COVENANT_GATE,
        )
        if lockup_active:
            lockup_count += 1

        date = getattr(mp, "period_end", None)
        year_index = date.year if date else None
        period_in_year = (date.month + 5) // 6 if date else None

        distribution = (
            float(getattr(wp, "legal_equity_distribution_keur", 0.0) or 0.0)
            if wp
            else None
        )
        reserve_adjusted = (
            float(getattr(wp, "reserve_adjusted_cash_keur", 0.0) or 0.0)
            if wp
            else None
        )
        dsra_top_up = (
            float(getattr(wp, "dsra_top_up_keur", 0.0) or 0.0) if wp else None
        )
        dsra_close = (
            float(getattr(wp, "senior_dsra_closing_keur", 0.0) or 0.0)
            if wp
            else None
        )

        period_views.append(
            CleanPeriodView(
                period=int(idx),
                date=date,
                year_index=year_index,
                period_in_year=period_in_year,
                is_operation=not bool(getattr(mp, "is_construction", False)),
                is_construction=bool(getattr(mp, "is_construction", False)),
                generation_mwh=_at(op.production_mwh, oi),
                revenue_keur=_at(op.revenue_keur, oi),
                opex_keur=_at(op.opex_keur, oi),
                ebitda_keur=_at(op.ebitda_keur, oi),
                depreciation_keur=_at(op.book_depreciation_keur, oi),
                taxable_profit_keur=_at(tax.taxable_profit_keur, ti),
                cash_tax_keur=cash_tax,
                cf_after_tax_keur=_at(tax.cfads_keur, ti),
                senior_interest_keur=senior_interest,
                senior_principal_keur=senior_principal,
                senior_ds_keur=senior_ds,
                senior_balance_keur=senior_close,
                dscr=dscr,
                dsra_contribution_keur=dsra_top_up,
                dsra_balance_keur=dsra_close,
                cf_after_reserves_keur=reserve_adjusted,
                shl_service_keur=(
                    None
                    if (shl_cash_interest is None and shl_principal_paid is None)
                    else float(shl_cash_interest or 0.0) + float(shl_principal_paid or 0.0)
                ),
                # Legacy export semantics read shl_interest_keur as CASH interest
                # ("Cash SHL interest plus principal" — runtime_summary). The
                # gross accrual is preserved separately below.
                shl_interest_keur=(
                    None if shl_cash_interest is None else float(shl_cash_interest)
                ),
                shl_balance_keur=None if shl_close is None else float(shl_close),
                shl_cash_interest_keur=(
                    None if shl_cash_interest is None else float(shl_cash_interest)
                ),
                shl_gross_interest_keur=(
                    None if shl_interest is None else float(shl_interest)
                ),
                shl_principal_keur=(
                    None if shl_principal_paid is None else float(shl_principal_paid)
                ),
                shl_pik_keur=(
                    (float(getattr(wp, "shl_pik_keur", 0.0) or 0.0) if wp else 0.0)
                ),
                distribution_keur=distribution,
                lockup_active=lockup_active,
                distribution_source="clean_g2c_cf109_gate",
                tax_keur=cash_tax,
                corporate_tax_cash_keur=cash_tax,
                senior_debt_service_keur=senior_ds,
                senior_interest_expense_keur=senior_interest,
                shl_interest_expense_keur=(
                    None if shl_interest is None else float(shl_interest)
                ),
                senior_debt_balance_keur=senior_close,
                distributions_keur=distribution,
            )
        )

    dscr_values = [p.dscr for p in period_views if p.dscr is not None]
    target_dscr = getattr(clean_run.project_inputs.financing, "target_dscr", None)

    equity_irr = g2c.pure_equity_xirr
    equity_irr_status = g2c.pure_equity_xirr_status
    sponsor_irr = g2c.total_sponsor_xirr
    sponsor_irr_status = g2c.total_sponsor_xirr_status

    return CleanWaterfallView(
        periods=period_views,
        total_revenue_keur=_sum_or_none(op.revenue_keur),
        total_opex_keur=_sum_or_none(op.opex_keur),
        total_ebitda_keur=_sum_or_none(op.ebitda_keur),
        total_tax_keur=_sum_or_none(tax.corporate_tax_cash_keur),
        total_senior_ds_keur=_sum_or_none(senior.senior_debt_service_keur),
        total_shl_service_keur=_sum_or_none(
            [p.shl_service_keur or 0.0 for p in period_views]
        ),
        total_distribution_keur=float(g2c.total_legal_equity_distributions_keur),
        actual_min_dscr=min(dscr_values) if dscr_values else None,
        actual_avg_dscr=(
            sum(dscr_values) / len(dscr_values) if dscr_values else None
        ),
        target_dscr=target_dscr,
        equity_irr=None if equity_irr_status.value != "OK" else equity_irr,
        sponsor_irr=None if sponsor_irr_status.value != "OK" else sponsor_irr,
        equity_irr_status=str(getattr(equity_irr_status, "value", equity_irr_status)),
        sponsor_irr_status=str(getattr(sponsor_irr_status, "value", sponsor_irr_status)),
        periods_in_lockup=lockup_count,
        _authority_metadata={
            **clean_run.authority_metadata,
            "unavailable_fields": dict(_UNAVAILABLE_FIELDS),
        },
    )


def build_clean_sponsor_schedule(clean_run) -> dict:
    """Read-only sponsor schedule payload from the G2C result.

    Replaces the legacy sponsor engine (hardcoded capital structures) for
    promoted runs: every value is a pass-through of a G2C-computed vector.
    """
    g2c = clean_run.g2c_result
    periods_out = []
    for wp in g2c.waterfall_periods:
        periods_out.append(
            {
                "period": wp.period_index,
                "date": wp.cashflow_date.isoformat() if wp.cashflow_date else None,
                "share_capital_contribution_keur": wp.share_capital_contribution_keur,
                "share_premium_contribution_keur": wp.share_premium_contribution_keur,
                "other_committed_equity_contribution_keur": (
                    wp.other_committed_equity_contribution_keur
                ),
                "additional_equity_contribution_keur": (
                    wp.additional_equity_contribution_keur
                ),
                "shl_cash_interest_receipt_keur": wp.shl_cash_interest_receipt_keur,
                "shl_principal_receipt_keur": wp.actual_shl_principal_paid_keur,
                "legal_equity_distribution_keur": wp.legal_equity_distribution_keur,
            }
        )
    return {
        "periods": periods_out,
        "summary": {
            "total_legal_equity_contributed_keur": (
                g2c.total_legal_equity_contributed_keur
            ),
            "total_shl_cash_contributed_keur": g2c.total_shl_cash_contributed_keur,
            "total_sponsor_contributed_keur": g2c.total_sponsor_contributed_keur,
            "total_shl_cash_interest_received_keur": (
                g2c.total_shl_cash_interest_received_keur
            ),
            "total_shl_principal_received_keur": (
                g2c.total_shl_principal_received_keur
            ),
            "total_legal_equity_distributions_keur": (
                g2c.total_legal_equity_distributions_keur
            ),
            "total_sponsor_receipts_keur": g2c.total_sponsor_receipts_keur,
            "pure_equity_xirr": g2c.pure_equity_xirr,
            "pure_equity_xirr_status": str(getattr(g2c.pure_equity_xirr_status, "value", None)),
            "pure_equity_moic": g2c.pure_equity_moic,
            "total_sponsor_xirr": g2c.total_sponsor_xirr,
            "total_sponsor_xirr_status": str(getattr(g2c.total_sponsor_xirr_status, "value", None)),
            "total_sponsor_moic": g2c.total_sponsor_moic,
            "shl_bullet_unpaid_at_maturity": g2c.shl_bullet_unpaid_at_maturity,
        },
        "source": "CovenantGatedWaterfallResult (clean G2C production authority)",
    }


def unavailable_fields_manifest() -> dict:
    """Machine-readable manifest of fields the clean runtime does not provide."""
    return dict(_UNAVAILABLE_FIELDS)
