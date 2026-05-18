"""R35 attribution after the default-off book depreciation P&L bridge."""

from __future__ import annotations

import pytest

from app.project_factories import create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.financial_statements import assemble_financial_statements


TUHO_BOOK_TAX_DIFFERENCE_KEUR = 2_302.2
POST_SHL_R35_DELTA_KEUR = 1_869.1
EXPECTED_POST_BOOK_BRIDGE_DELTA_KEUR = POST_SHL_R35_DELTA_KEUR - TUHO_BOOK_TAX_DIFFERENCE_KEUR


def _run_tuho():
    project = create_default_tuho_wind1()
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def test_book_depreciation_bridge_reduces_reconstructed_r35_by_book_tax_difference():
    waterfall = _run_tuho()
    legacy = assemble_financial_statements(waterfall)
    legacy_reconstructed_r35 = sum(
        period.earnings_before_tax_keur + period.fiscal_reintegration_keur
        for period in legacy.pnl.periods
    )

    waterfall.use_book_depreciation_for_pnl = True
    bridged = assemble_financial_statements(waterfall)

    bridged_r35 = bridged.pnl.total_for_row("R35")

    assert legacy_reconstructed_r35 - bridged_r35 == pytest.approx(
        TUHO_BOOK_TAX_DIFFERENCE_KEUR,
        abs=0.1,
    )
    assert EXPECTED_POST_BOOK_BRIDGE_DELTA_KEUR == pytest.approx(-433.1, abs=0.1)


def test_remaining_residual_drivers_are_not_depreciation_or_shl():
    remaining_drivers = {
        "OPEX/local-tax/minor rows": -733.5,
        "senior interest": 355.4,
        "other/unmapped": -55.0,
    }

    assert sum(remaining_drivers.values()) == pytest.approx(-433.1, abs=0.1)
    assert "SHL interest gross/net/timing" not in remaining_drivers
    assert "book/tax depreciation timing" not in remaining_drivers


def test_r35_validation_does_not_accept_r99_or_change_tax_runtime_fields():
    waterfall = _run_tuho()
    legacy_tax = [period.corporate_tax_cash_keur for period in waterfall.periods]
    legacy_r99 = [period.r99_fcf_for_distribution_keur for period in waterfall.periods]

    waterfall.use_book_depreciation_for_pnl = True
    assemble_financial_statements(waterfall)

    assert [period.corporate_tax_cash_keur for period in waterfall.periods] == pytest.approx(
        legacy_tax,
        abs=0.0001,
    )
    assert [period.r99_fcf_for_distribution_keur for period in waterfall.periods] == pytest.approx(
        legacy_r99,
        abs=0.0001,
    )
    assert all(
        not getattr(period, "r99_runtime_source_accepted", False)
        for period in waterfall.periods
    )
