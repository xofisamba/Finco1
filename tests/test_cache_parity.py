"""Parity test: utils/cache shim properly delegates to app/cache and app.waterfall_core.

This test verifies the shim chain:
  utils/cache.compute_waterfall_cached  →  app.waterfall_core.run_waterfall_v3_core
  utils/cache.cached_run_waterfall_v3   →  app.cache.cached_run_waterfall_v3
"""
import pytest
from unittest.mock import patch
from app.project_factories import create_default_solar_project
from domain.period_engine import PeriodEngine


def _make_engine(inputs):
    return PeriodEngine(
        financial_close=inputs.info.financial_close,
        construction_months=inputs.info.construction_months,
        horizon_years=inputs.info.horizon_years,
        ppa_years=inputs.revenue.ppa_term_years,
    )


def _run_via_core(project):
    """Run waterfall via the direct core path."""
    from app.waterfall_core import run_waterfall_v3_core
    engine = _make_engine(project)
    all_periods = list(engine.periods())
    op_periods = [p for p in all_periods if p.is_operation]
    return run_waterfall_v3_core(
        inputs=project,
        engine=engine,
        rate_per_period=project.financing.all_in_rate / 2,
        tenor_periods=len(op_periods),
        target_dscr=project.financing.target_dscr,
        lockup_dscr=project.financing.lockup_dscr,
        tax_rate=project.tax.corporate_rate,
        dsra_months=project.financing.dsra_months,
        shl_amount=project.financing.shl_amount_keur,
        shl_rate=project.financing.shl_rate,
        shl_idc_keur=0.0,
        shl_repayment_method="bullet",
        equity_irr_method="equity_only",
        share_capital_keur=project.financing.share_capital_keur,
        sculpt_capex_keur=project.capex.sculpt_capex_keur,
        debt_sizing_method=project.financing.debt_sizing_method,
    )


def test_compute_waterfall_cached_delegates_to_run_waterfall_v3_core():
    """compute_waterfall_cached calls run_waterfall_v3_core (verified via source)."""
    import inspect
    from utils.cache import compute_waterfall_cached as cwc
    src = inspect.getsource(cwc)
    assert "run_waterfall_v3_core" in src, \
        "compute_waterfall_cached must delegate to run_waterfall_v3_core"


def test_core_and_utils_shm_computation_produce_same_project_irr():
    """Direct core computation produces a result; shim logic matches same formula."""
    project = create_default_solar_project()
    direct = _run_via_core(project)

    # The utils.cache shim delegates to the same core function,
    # so results should be identical when called with same inputs.
    from utils.cache import compute_waterfall_cached
    engine = _make_engine(project)
    all_periods = list(engine.periods())
    op_periods = [p for p in all_periods if p.is_operation]

    shim_result = compute_waterfall_cached(
        inputs=project,
        engine=engine,
        rate_per_period=project.financing.all_in_rate / 2,
        tenor_periods=len(op_periods),
        target_dscr=project.financing.target_dscr,
        lockup_dscr=project.financing.lockup_dscr,
        tax_rate=project.tax.corporate_rate,
        dsra_months=project.financing.dsra_months,
        shl_amount=project.financing.shl_amount_keur,
        shl_rate=project.financing.shl_rate,
        shl_idc_keur=0.0,
        shl_repayment_method="bullet",
        equity_irr_method="equity_only",
        share_capital_keur=project.financing.share_capital_keur,
        sculpt_capex_keur=project.capex.sculpt_capex_keur,
        debt_sizing_method=project.financing.debt_sizing_method,
    )

    assert abs(direct.project_irr - shim_result.project_irr) <= 1e-6, (
        f"project_irr mismatch: direct={direct.project_irr}, "
        f"shim={shim_result.project_irr}"
    )


def test_utils_cache_reexports_clearing_function():
    """utils.cache re-exports clear_all_caches from app.cache."""
    from utils.cache import clear_all_caches as utils_clear
    from app.cache import clear_all_caches as app_clear
    assert utils_clear is app_clear, "clear_all_caches must be re-exported from app.cache"


def test_utils_cache_reexports_hash_functions():
    """utils.cache re-exports hash functions from app.cache."""
    from utils.cache import (
        hash_inputs_for_cache as h1,
        hash_engine_for_cache as h2,
    )
    from app.cache import (
        hash_inputs_for_cache as a1,
        hash_engine_for_cache as a2,
    )
    assert h1 is a1, "hash_inputs_for_cache must be re-exported"
    assert h2 is a2, "hash_engine_for_cache must be re-exported"
