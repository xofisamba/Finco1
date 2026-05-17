"""Offline PF Cash Waterfall assembly tests."""

from __future__ import annotations

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.financial_statements import assemble_financial_statements


def _run_project(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def test_pf_cash_waterfall_periods_generated_for_tuho_and_oborovo():
    for factory in (create_default_tuho_wind1, create_default_oborovo):
        waterfall = _run_project(factory())
        statements = assemble_financial_statements(waterfall)

        assert len(statements.pf_cash_waterfall.periods) == len(waterfall.periods)


def test_pf_cash_waterfall_uses_existing_c1d_audit_fields():
    waterfall = _run_project(create_default_tuho_wind1())
    statements = assemble_financial_statements(waterfall)

    for source, cf_period in zip(waterfall.periods, statements.pf_cash_waterfall.periods):
        assert cf_period.revenue_cash_keur == pytest.approx(source.revenue_keur)
        assert cf_period.opex_cash_keur == pytest.approx(-source.opex_keur)
        assert cf_period.ebitda_cash_keur == pytest.approx(source.ebitda_keur)
        assert cf_period.cash_tax_keur == pytest.approx(-source.corporate_tax_cash_keur)
        assert cf_period.fcf_banks_keur == pytest.approx(source.r69_fcf_banks_keur)
        assert cf_period.fcf_junior_keur == pytest.approx(source.r84_fcf_junior_keur)
        assert cf_period.distribution_account_pre_lockup_keur == pytest.approx(
            source.r98_distribution_account_keur
        )
        assert cf_period.fcf_for_distribution_keur == pytest.approx(
            source.r99_fcf_for_distribution_keur
        )
        assert cf_period.distribution_account_carryforward_keur == pytest.approx(
            source.r100_carryforward_keur
        )
        assert cf_period.fcf_for_shl_keur == pytest.approx(source.r102_fcf_for_shl_keur)


def test_pf_cash_waterfall_r99_r102_identity_and_dividends_match_runtime():
    waterfall = _run_project(create_default_tuho_wind1())
    statements = assemble_financial_statements(waterfall)

    assert statements.pf_cash_waterfall.r99_r102_identity_holds is True
    for source, cf_period in zip(waterfall.periods, statements.pf_cash_waterfall.periods):
        assert cf_period.fcf_for_distribution_keur == pytest.approx(cf_period.fcf_for_shl_keur)
        assert cf_period.net_dividends_keur == pytest.approx(source.distribution_keur)
        assert cf_period.r99_runtime_source_accepted is False


def test_pf_cash_waterfall_does_not_accept_r99_or_enable_shl_fcf():
    project = create_default_tuho_wind1()
    waterfall = _run_project(project)
    statements = assemble_financial_statements(waterfall)

    assert project.financing.use_tuho_r99_input_engine is False
    assert project.info.use_shl_fcf_waterfall_engine is False
    assert all(
        period.r99_runtime_source_accepted is False
        for period in statements.pf_cash_waterfall.periods
    )


def test_pf_cash_waterfall_preserves_runtime_totals():
    waterfall = _run_project(create_default_oborovo())
    before = (
        waterfall.total_revenue_keur,
        waterfall.total_opex_keur,
        waterfall.total_tax_keur,
        waterfall.total_senior_ds_keur,
        waterfall.total_distribution_keur,
    )

    assemble_financial_statements(waterfall)

    after = (
        waterfall.total_revenue_keur,
        waterfall.total_opex_keur,
        waterfall.total_tax_keur,
        waterfall.total_senior_ds_keur,
        waterfall.total_distribution_keur,
    )
    assert after == pytest.approx(before)
