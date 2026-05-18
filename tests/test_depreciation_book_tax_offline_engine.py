"""Tests for the offline book/tax depreciation ledger."""

from __future__ import annotations

import dataclasses

import pytest

from domain.depreciation import (
    AssetClassConfig,
    DepreciationLedgerInput,
    DepreciationPolicy,
    build_depreciation_ledger,
)


TUHO_BOOK_DEPRECIATION_TOTAL_KEUR = 72_993.7
TUHO_TAX_DEPRECIATION_TOTAL_KEUR = 70_691.5
TUHO_DEPRECIATION_DIFFERENCE_KEUR = 2_302.2
OPERATING_PERIODS = 60


def _tuho_aggregate_ledger_input() -> DepreciationLedgerInput:
    return DepreciationLedgerInput(
        asset_classes=(
            AssetClassConfig(
                asset_class="tuho_aggregate_fixture",
                gross_asset_basis_keur=TUHO_BOOK_DEPRECIATION_TOTAL_KEUR,
                book_depreciable_basis_keur=TUHO_BOOK_DEPRECIATION_TOTAL_KEUR,
                tax_depreciable_basis_keur=TUHO_TAX_DEPRECIATION_TOTAL_KEUR,
                placed_in_service_period=0,
                depreciation_start_period=0,
                source_label="TUHO aggregate Dep R30/R31 fixture",
            ),
        ),
        policies={
            "tuho_aggregate_fixture": DepreciationPolicy(
                useful_life_book_periods=OPERATING_PERIODS,
                useful_life_tax_periods=OPERATING_PERIODS,
                period_frequency="semiannual",
            )
        },
        period_count=OPERATING_PERIODS,
        period_frequency="semiannual",
        cod_period=0,
    )


def test_tuho_aggregate_fixture_reproduces_book_and_tax_totals():
    result = build_depreciation_ledger(_tuho_aggregate_ledger_input())

    assert result.total_book_depreciation_keur == pytest.approx(
        TUHO_BOOK_DEPRECIATION_TOTAL_KEUR,
        abs=0.1,
    )
    assert result.total_tax_depreciation_keur == pytest.approx(
        TUHO_TAX_DEPRECIATION_TOTAL_KEUR,
        abs=0.1,
    )
    assert (
        result.total_book_depreciation_keur - result.total_tax_depreciation_keur
    ) == pytest.approx(TUHO_DEPRECIATION_DIFFERENCE_KEUR, abs=0.1)


def test_ledger_emits_one_row_per_asset_class_per_period():
    result = build_depreciation_ledger(_tuho_aggregate_ledger_input())

    assert len(result.periods) == OPERATING_PERIODS
    assert {period.asset_class for period in result.periods} == {"tuho_aggregate_fixture"}
    assert [period.period_index for period in result.periods] == list(range(OPERATING_PERIODS))


def test_period_aggregate_helper_reports_book_tax_and_nbv():
    result = build_depreciation_ledger(_tuho_aggregate_ledger_input())

    first = result.aggregate_by_period(0)
    last = result.aggregate_by_period(OPERATING_PERIODS - 1)
    all_aggregates = result.aggregate_periods()

    assert len(all_aggregates) == OPERATING_PERIODS
    assert first.asset_class == "TOTAL"
    assert first.book_depreciation_keur == pytest.approx(
        TUHO_BOOK_DEPRECIATION_TOTAL_KEUR / OPERATING_PERIODS,
    )
    assert first.tax_depreciation_keur == pytest.approx(
        TUHO_TAX_DEPRECIATION_TOTAL_KEUR / OPERATING_PERIODS,
    )
    assert last.accumulated_book_depreciation_keur == pytest.approx(
        TUHO_BOOK_DEPRECIATION_TOTAL_KEUR,
    )
    assert last.accumulated_tax_depreciation_keur == pytest.approx(
        TUHO_TAX_DEPRECIATION_TOTAL_KEUR,
    )
    assert last.nbv_book_keur == pytest.approx(0.0, abs=0.01)
    assert last.nbv_tax_keur == pytest.approx(0.0, abs=0.01)


def test_straight_line_engine_respects_start_period_and_useful_life_end():
    ledger_input = DepreciationLedgerInput(
        asset_classes=(
            AssetClassConfig(
                asset_class="delayed",
                gross_asset_basis_keur=120.0,
                book_depreciable_basis_keur=120.0,
                tax_depreciable_basis_keur=60.0,
                placed_in_service_period=2,
                depreciation_start_period=2,
                source_label="unit fixture",
            ),
        ),
        policies={
            "delayed": DepreciationPolicy(
                useful_life_book_periods=3,
                useful_life_tax_periods=2,
                period_frequency="semiannual",
            )
        },
        period_count=6,
        period_frequency="semiannual",
        cod_period=0,
    )

    result = build_depreciation_ledger(ledger_input)
    book_by_period = [row.book_depreciation_keur for row in result.periods]
    tax_by_period = [row.tax_depreciation_keur for row in result.periods]
    nbv_book_by_period = [row.nbv_book_keur for row in result.periods]

    assert book_by_period == pytest.approx((0.0, 0.0, 40.0, 40.0, 40.0, 0.0))
    assert tax_by_period == pytest.approx((0.0, 0.0, 30.0, 30.0, 0.0, 0.0))
    assert min(nbv_book_by_period) >= 0.0
    assert result.total_book_depreciation_keur == pytest.approx(120.0)
    assert result.total_tax_depreciation_keur == pytest.approx(60.0)


def test_depreciation_result_dataclasses_are_immutable():
    result = build_depreciation_ledger(_tuho_aggregate_ledger_input())

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.periods[0].book_depreciation_keur = 0.0


def test_offline_engine_does_not_add_runtime_flags_or_wiring():
    import domain.depreciation as depreciation
    from domain.inputs import ProjectInfo

    assert depreciation.__all__
    assert not hasattr(ProjectInfo, "use_depreciation_book_tax_ledger")
    assert not hasattr(ProjectInfo, "use_book_depreciation_pnl_bridge")
