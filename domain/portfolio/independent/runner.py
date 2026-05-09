"""Phase 1 MVP: Run independent SPVs through the single-asset engine.

No pooled financing. No shared debt sculpting. No HoldCo. No SHL.
Each SPV runs its own waterfall independently; results are aggregated.
"""
from __future__ import annotations

from typing import Optional

from domain.portfolio.independent.inputs import (
    IndependentPortfolioInputs,
    DSRFConfig,
)
from domain.portfolio.independent.result import (
    SPVOutput,
    IndependentPortfolioResult,
    aggregate_independent_results,
)


class SPVWaterfallError(Exception):
    """Raised when an SPV waterfall fails and strict=True."""

    def __init__(self, project_code: str, cause: Exception):
        self.project_code = project_code
        self.cause = cause
        super().__init__(f"SPV '{project_code}' waterfall run failed: {cause}")


def run_independent_portfolio(
    portfolio_inputs: IndependentPortfolioInputs,
    *,
    rate_per_period: float = 0.02825,
    strict: bool = True,
) -> IndependentPortfolioResult:
    """Run independent SPV portfolio aggregation (Phase 1 MVP).

    Each SPV runs independently through the single-asset engine.
    Results are aggregated into portfolio KPIs.

    NO pooled debt sculpting. NO shared financing. NO DSRF integration.

    Args:
        portfolio_inputs: IndependentPortfolioInputs with N projects
        rate_per_period: Semi-annual interest rate (default 0.02825)
        strict: If True (default), any SPV waterfall failure raises SPVWaterfallError.
                If False, the failed SPV is included with zero outputs and warnings.

    Returns:
        IndependentPortfolioResult with per-SPV outputs and portfolio KPIs.

    Raises:
        SPVWaterfallError: when strict=True and any SPV waterfall fails.
    """
    spv_outputs: list[SPVOutput] = []

    for proj in portfolio_inputs.projects:
        wf_result, spv_warnings = _run_single_spv(
            proj, rate_per_period, strict=strict
        )

        if wf_result is None:
            # Failed SPV — already logged in spv_warnings
            if strict:
                code = proj.info.code
                msg = (spv_warnings[0] if spv_warnings
                       else f"SPV '{code}' waterfall run failed")
                raise SPVWaterfallError(
                    project_code=code,
                    cause=Exception(msg),
                )
            # Non-strict: include zero-output placeholder
            spv_outputs.append(_build_spv_output(proj, None, spv_warnings))
        else:
            spv_outputs.append(_build_spv_output(proj, wf_result, spv_warnings))

    return aggregate_independent_results(
        portfolio_name=portfolio_inputs.portfolio_name,
        spv_outputs=tuple(spv_outputs),
        dsrf_enabled=(
            portfolio_inputs.dsrf is not None
            and portfolio_inputs.dsrf.enabled
        ),
    )


def _run_single_spv(
    project_inputs,
    rate_per_period: float,
    strict: bool,
) -> tuple[Optional[WaterfallResult], list[str]]:
    """Run one SPV through the waterfall engine.

    Returns (result, warnings):
    - result: WaterfallResult on success, None on failure
    - warnings: list of warning strings (empty on success)
    """
    from domain.period_engine import PeriodEngine
    from app.waterfall_core import run_waterfall_v3_core

    engine = PeriodEngine(
        financial_close=project_inputs.info.financial_close,
        construction_months=project_inputs.info.construction_months,
        horizon_years=project_inputs.info.horizon_years,
        ppa_years=project_inputs.revenue.ppa_term_years,
    )
    all_periods = list(engine.periods())
    op_periods = [p for p in all_periods if p.is_operation]
    n_op = len(op_periods)

    # Pull financing params with safe fallbacks
    lockup_dscr = 1.10
    dsra_months = 6
    tax_rate = 0.10
    shl_amount = 0.0
    shl_rate = 0.0
    shl_idc_keur = 0.0
    shl_repay_method = "sculpt"
    shl_tenor = 0
    equity_irr_method = "xirr"
    share_capital_keur = 0.0
    sculpt_capex_keur = 0.0
    debt_sizing_method = "dscr_sculpt"

    if hasattr(project_inputs, "financing"):
        fin = project_inputs.financing
        lockup_dscr = getattr(fin, "lockup_dscr", 1.10)
        dsra_months = getattr(fin, "dsra_months", 6)
        shl_amount = getattr(fin, "shl_amount_keur", 0.0)
        shl_rate = getattr(fin, "shl_rate", 0.0)
        shl_idc_keur = getattr(fin, "shl_idc_keur", 0.0)
        shl_repay_method = getattr(fin, "shl_repayment_method", "sculpt")
        shl_tenor = getattr(fin, "shl_tenor_years", 0)
        equity_irr_method = getattr(fin, "equity_irr_method", "xirr")
        share_capital_keur = getattr(fin, "share_capital_keur", 0.0)
        sculpt_capex_keur = getattr(fin, "sculpt_capex_keur", 0.0)
        debt_sizing_method = getattr(fin, "debt_sizing_method", "dscr_sculpt")

    if hasattr(project_inputs, "tax"):
        tax_rate = getattr(project_inputs.tax, "corporate_rate", 0.10)

    if hasattr(project_inputs, "capex"):
        sculpt_capex_keur = getattr(
            project_inputs.capex, "sculpt_capex_keur", 0.0
        )

    target_dscr = getattr(project_inputs.financing, "target_dscr", 1.15)


    try:
        result = run_waterfall_v3_core(
            inputs=project_inputs,
            engine=engine,
            rate_per_period=rate_per_period,
            tenor_periods=n_op,
            target_dscr=target_dscr,
            lockup_dscr=lockup_dscr,
            tax_rate=tax_rate,
            dsra_months=dsra_months,
            shl_amount=shl_amount,
            shl_rate=shl_rate,
            shl_idc_keur=shl_idc_keur,
            shl_repayment_method=shl_repay_method,
            shl_tenor_years=shl_tenor,
            equity_irr_method=equity_irr_method,
            share_capital_keur=share_capital_keur,
            sculpt_capex_keur=sculpt_capex_keur,
            debt_sizing_method=debt_sizing_method,
        )
        return result, []

    except Exception as e:
        code = project_inputs.info.code
        if strict:
            raise SPVWaterfallError(
                project_code=code,
                cause=e,
            ) from e
        return None, [f"SPV '{code}' waterfall run failed: {e}"]


def _build_spv_output(
    project_inputs,
    wf_result: Optional[WaterfallResult],
    warnings: list[str],
) -> SPVOutput:
    """Build SPVOutput from a waterfall result (or zero output on failure)."""
    code = project_inputs.info.code
    name = getattr(project_inputs.info, "name", code)

    if wf_result is None:
        return SPVOutput(
            project_code=code,
            project_name=name,
            project_irr=0.0,
            equity_irr=0.0,
            total_revenue_keur=0.0,
            total_ebitda_keur=0.0,
            total_tax_keur=0.0,
            total_senior_ds_keur=0.0,
            total_distribution_keur=0.0,
            avg_dscr=0.0,
            min_dscr=0.0,
            waterfall_result=None,
            warnings=tuple(warnings),
        )

    return SPVOutput(
        project_code=code,
        project_name=name,
        project_irr=getattr(wf_result, "project_irr", 0.0),
        equity_irr=getattr(wf_result, "equity_irr", 0.0),
        total_revenue_keur=getattr(wf_result, "total_revenue_keur", 0.0),
        total_ebitda_keur=getattr(wf_result, "total_ebitda_keur", 0.0),
        total_tax_keur=getattr(wf_result, "total_tax_keur", 0.0),
        total_senior_ds_keur=getattr(wf_result, "total_senior_ds_keur", 0.0),
        total_distribution_keur=getattr(wf_result, "total_distribution_keur", 0.0),
        avg_dscr=getattr(wf_result, "avg_dscr", 0.0),
        min_dscr=getattr(wf_result, "min_dscr", 0.0),
        waterfall_result=wf_result,
        warnings=tuple(warnings),
    )


__all__ = [
    "run_independent_portfolio",
    "SPVWaterfallError",
    "IndependentPortfolioInputs",
    "IndependentPortfolioResult",
    "SPVOutput",
    "DSRFConfig",
]
