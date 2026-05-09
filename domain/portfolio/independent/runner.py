"""Phase 1 MVP: Run independent SPVs through single-asset engine and aggregate.

No pooled financing, no shared debt sculpting, no cross-default.
Each SPV runs independently through the existing calibrated engine.
"""
from __future__ import annotations

from typing import Optional
from domain.portfolio.independent.inputs import IndependentPortfolioInputs, DSRFConfig
from domain.portfolio.independent.result import (
    SPVOutput,
    IndependentPortfolioResult,
    aggregate_independent_results,
)


class SPVWaterfallError(Exception):
    """Raised when an SPV waterfall run fails in strict mode.

    Attributes:
        project_code: identifier of the SPV that failed
        cause: the original exception
    """
    def __init__(self, project_code: str, cause: Exception):
        self.project_code = project_code
        self.cause = cause
        super().__init__(f"SPV '{project_code}' waterfall run failed: {cause}")


def run_independent_portfolio(
    portfolio_inputs: IndependentPortfolioInputs,
    *,
    rate_per_period: float = 0.02825,
    strict: bool = True,
    allow_partial: bool = False,
) -> IndependentPortfolioResult:
    """Run independent SPV portfolio aggregation (Phase 1 MVP).

    Each project runs through the existing single-asset waterfall engine.
    Results are preserved per-SPV and aggregated.

    NO pooled debt sculpting. NO shared financing. NO DSRF integration.

    Args:
        portfolio_inputs: IndependentPortfolioInputs with N projects
        rate_per_period: Semi-annual interest rate (default 0.02825)
        strict: If True (default), any SPV waterfall failure raises SPVWaterfallError.
                If False, failed SPVs are included with zero outputs and warnings.
        allow_partial: If False (default), all SPVs must succeed or the run fails in strict mode.
                       Irrelevant when strict=False.

    Returns:
        IndependentPortfolioResult with per-SPV outputs and aggregate summary

    Raises:
        SPVWaterfallError: when strict=True and any SPV waterfall fails
    """
    spv_outputs: list[SPVOutput] = []
    portfolio_warnings: list[str] = []
    failed_spvs: list[tuple[str, str]] = []  # (code, error_message)

    for proj in portfolio_inputs.projects:
        wf_result, spv_warnings = _run_single_spv(
            proj, rate_per_period, strict=strict
        )

        if wf_result is None:
            # SPV failed
            code = proj.info.code
            error_msg = f"SPV '{code}': waterfall run failed"
            if spv_warnings:
                error_msg = spv_warnings[0]
            failed_spvs.append((code, error_msg))
            portfolio_warnings.extend(spv_warnings)

            if strict:
                # Fail fast with the first failure
                cause_msg = error_msg
                raise SPVWaterfallError(
                    project_code=code,
                    cause=Exception(cause_msg),
                )
            # Non-strict: include zero-output placeholder
            spv_output = _build_spv_output(proj, None, spv_warnings)
            spv_outputs.append(spv_output)
        else:
            spv_output = _build_spv_output(proj, wf_result, spv_warnings)
            spv_outputs.append(spv_output)

    # Aggregate
    result = aggregate_independent_results(
        portfolio_name=portfolio_inputs.portfolio_name,
        spv_outputs=tuple(spv_outputs),
        dsrf_enabled=(portfolio_inputs.dsrf is not None and portfolio_inputs.dsrf.enabled),
    )
    return result


def _run_single_spv(project_inputs, rate_per_period: float, strict: bool):
    """Run a single SPV through the existing waterfall engine.

    Returns (WaterfallResult, list[str]) — result and any warnings.

    In strict mode, exceptions are re-raised with SPV code context.
    In non-strict mode, exceptions are caught and returned as warnings.
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

    # Pull project-level financing params
    lockup_dscr = 1.10  # default lockup
    dsra_months = 6     # default DSRA months
    tax_rate = 0.10
    shl_amount = 0.0
    shl_rate = 0.0
    shl_idc = 0.0
    shl_repay_method = "sculpt"
    shl_tenor = 0
    equity_irr_method = "xirr"
    share_capital = 0.0
    sculpt_capex = 0.0
    debt_sizing_method = "dscr_sculpt"

    if hasattr(project_inputs, 'financing'):
        fin = project_inputs.financing
        lockup_dscr = getattr(fin, 'lockup_dscr', 1.10)
        dsra_months = getattr(fin, 'dsra_months', 6)
        shl_amount = getattr(fin, 'shl_amount_keur', 0.0)
        shl_rate = getattr(fin, 'shl_rate', 0.0)
        shl_idc = getattr(fin, 'shl_idc_keur', 0.0)
        shl_repay_method = getattr(fin, 'shl_repayment_method', 'sculpt')
        shl_tenor = getattr(fin, 'shl_tenor_years', 0)
        equity_irr_method = getattr(fin, 'equity_irr_method', 'xirr')
        share_capital = getattr(fin, 'share_capital_keur', 0.0)
        sculpt_capex = getattr(project_inputs.capex, 'sculpt_capex_keur', 0.0) \
            if hasattr(project_inputs, 'capex') else 0.0
        debt_sizing_method = getattr(fin, 'debt_sizing_method', 'dscr_sculpt')

    if hasattr(project_inputs, 'tax'):
        tax_rate = getattr(project_inputs.tax, 'corporate_rate', 0.10)

    target_dscr = 1.15  # default
    if hasattr(project_inputs, 'financing') and hasattr(project_inputs.financing, 'target_dscr'):
        target_dscr = project_inputs.financing.target_dscr

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
            shl_idc_keur=shl_idc,
            shl_repayment_method=shl_repay_method,
            shl_tenor_years=shl_tenor,
            equity_irr_method=equity_irr_method,
            share_capital_keur=share_capital,
            sculpt_capex_keur=sculpt_capex,
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
        # Non-strict: return empty result with warning
        return None, [f"SPV '{code}' waterfall run failed: {e}"]


def _build_spv_output(project_inputs, wf_result, warnings: list[str]) -> SPVOutput:
    """Build SPVOutput from waterfall result."""
    code = project_inputs.info.code
    name = getattr(project_inputs.info, 'name', code)

    if wf_result is None:
        # Return empty output with warning
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

    # Extract KPIs from waterfall result
    rev = getattr(wf_result, 'total_revenue_keur', 0.0)
    ebitda = getattr(wf_result, 'total_ebitda_keur', 0.0)
    tax = getattr(wf_result, 'total_tax_keur', 0.0)
    senior_ds = getattr(wf_result, 'total_senior_ds_keur', 0.0)
    dist = getattr(wf_result, 'total_distribution_keur', 0.0)
    proj_irr = getattr(wf_result, 'project_irr', 0.0)
    eq_irr = getattr(wf_result, 'equity_irr', 0.0)
    avg_d = getattr(wf_result, 'avg_dscr', 0.0)
    min_d = getattr(wf_result, 'min_dscr', 0.0)

    return SPVOutput(
        project_code=code,
        project_name=name,
        project_irr=proj_irr,
        equity_irr=eq_irr,
        total_revenue_keur=rev,
        total_ebitda_keur=ebitda,
        total_tax_keur=tax,
        total_senior_ds_keur=senior_ds,
        total_distribution_keur=dist,
        avg_dscr=avg_d,
        min_dscr=min_d,
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
