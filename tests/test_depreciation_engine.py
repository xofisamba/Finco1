"""Phase 7 — Depreciation Engine tests."""
import pytest

from domain.depreciation.asset import AssetClassConfig
from domain.depreciation.engine import (
    DepreciationEngine,
    DepreciationEngineInputs,
    DepreciationEngineResult,
)
from domain.depreciation.schedule import DepreciationPolicy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_engine_inputs(
    project_name="TUHO",
    asset_classes=None,
    policies=None,
    period_count=63,
    period_frequency="semiannual",
    cod_period=2,
):
    if asset_classes is None:
        asset_classes = (
            AssetClassConfig(
                asset_class="Wind Turbine",
                gross_asset_basis_keur=8000.0,
                book_depreciable_basis_keur=8000.0,
                tax_depreciable_basis_keur=8000.0,
                placed_in_service_period=1,  # period 1 = col G = construction
                depreciation_start_period=2,  # starts at period 2 (COD)
            ),
        )
    if policies is None:
        policies = {
            "default": DepreciationPolicy(
                method="straight_line",
                useful_life_book_periods=40,  # 20 years × 2 semiannual periods
                useful_life_tax_periods=40,
                period_frequency="semiannual",
            ),
        }

    return DepreciationEngineInputs(
        project_name=project_name,
        asset_classes=asset_classes,
        policies=policies,
        period_count=period_count,
        period_frequency=period_frequency,
        cod_period=cod_period,
    )


# ---------------------------------------------------------------------------
# Straight-line semiannual depreciation
# ---------------------------------------------------------------------------

class TestStraightLineSemiannual:
    def test_semiannual_depreciation_rate(self):
        """8% annual rate, semiannual → 4% per period."""
        inputs = make_engine_inputs(
            asset_classes=(
                AssetClassConfig(
                    asset_class="Wind Turbine",
                    gross_asset_basis_keur=10000.0,
                    book_depreciable_basis_keur=10000.0,
                    tax_depreciable_basis_keur=10000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(
                    method="straight_line",
                    useful_life_book_periods=40,
                    useful_life_tax_periods=40,
                    period_frequency="semiannual",
                ),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)

        # Per period: 10000 / 40 = 250 kEUR
        # Period 2 (first depreciation) = 250
        period_2_rows = result.ledger_result.periods_for_index(2)
        assert len(period_2_rows) == 1
        assert period_2_rows[0].book_depreciation_keur == pytest.approx(250.0, rel=1e-9)
        # Period 3 = 250, etc.
        period_3_rows = result.ledger_result.periods_for_index(3)
        assert period_3_rows[0].book_depreciation_keur == pytest.approx(250.0, rel=1e-9)

    def test_depreciation_sums_to_basis(self):
        """Total depreciation over life = depreciable basis."""
        inputs = make_engine_inputs(
            asset_classes=(
                AssetClassConfig(
                    asset_class="Turbine",
                    gross_asset_basis_keur=10000.0,
                    book_depreciable_basis_keur=10000.0,
                    tax_depreciable_basis_keur=10000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(
                    useful_life_book_periods=40,
                    useful_life_tax_periods=40,
                ),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)
        assert result.total_book_depreciation_keur == pytest.approx(10000.0, rel=1e-6)


# ---------------------------------------------------------------------------
# Book vs tax useful-life separation
# ---------------------------------------------------------------------------

class TestBookTaxSeparation:
    def test_book_and_tax_useful_lives_diverge(self):
        """Book 20yr (40 periods), tax 12yr (24 periods) → different depreciation."""
        inputs = make_engine_inputs(
            asset_classes=(
                AssetClassConfig(
                    asset_class="Wind Turbine",
                    gross_asset_basis_keur=12000.0,
                    book_depreciable_basis_keur=12000.0,
                    tax_depreciable_basis_keur=12000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(
                    useful_life_book_periods=40,   # 20 years
                    useful_life_tax_periods=24,     # 12 years
                    period_frequency="semiannual",
                ),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)

        # Tax: 12000/24 = 500/period for first 24 periods
        # Book: 12000/40 = 300/period for first 40 periods
        period_5 = result.ledger_result.periods_for_index(5)[0]
        assert period_5.book_depreciation_keur == pytest.approx(300.0, rel=1e-9)
        assert period_5.tax_depreciation_keur == pytest.approx(500.0, rel=1e-9)

        # After tax life ends (period > 25), tax = 0, book continues
        period_30 = result.ledger_result.periods_for_index(30)[0]
        assert period_30.book_depreciation_keur == pytest.approx(300.0, rel=1e-9)
        assert period_30.tax_depreciation_keur == pytest.approx(0.0, abs=0.01)

        # Total book: 300 * 40 = 12000
        # Total tax: 500 * 24 = 12000
        assert result.total_book_depreciation_keur == pytest.approx(12000.0, rel=1e-6)
        assert result.total_tax_depreciation_keur == pytest.approx(12000.0, rel=1e-6)


# ---------------------------------------------------------------------------
# Land non-depreciable
# ---------------------------------------------------------------------------

class TestLandNonDepreciable:
    def test_land_has_zero_depreciation(self):
        """Land is non-depreciable by default."""
        inputs = make_engine_inputs(
            asset_classes=(
                AssetClassConfig(
                    asset_class="Land",
                    gross_asset_basis_keur=500.0,
                    book_depreciable_basis_keur=0.0,  # land = not depreciable
                    tax_depreciable_basis_keur=0.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(
                    useful_life_book_periods=40,
                    useful_life_tax_periods=40,
                ),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)
        # All periods should show 0 depreciation for land
        land_rows = [r for r in result.ledger_result.periods if r.asset_class == "Land"]
        assert len(land_rows) > 0
        for row in land_rows:
            assert row.book_depreciation_keur == pytest.approx(0.0, abs=1e-9)
            assert row.tax_depreciation_keur == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Financing costs 12-year policy
# ---------------------------------------------------------------------------

class TestFinancingCostsPolicy:
    def test_financing_costs_use_12_year_policy(self):
        """Financing costs depreciated over 12 years (24 semiannual periods)."""
        inputs = make_engine_inputs(
            asset_classes=(
                AssetClassConfig(
                    asset_class="Financing Costs",
                    gross_asset_basis_keur=2000.0,
                    book_depreciable_basis_keur=2000.0,
                    tax_depreciable_basis_keur=2000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(
                    useful_life_book_periods=40,
                    useful_life_tax_periods=40,
                ),
                "Financing Costs": DepreciationPolicy(
                    useful_life_book_periods=24,  # 12 years
                    useful_life_tax_periods=24,
                ),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)

        period_5 = result.ledger_result.periods_for_index(5)[0]
        # 2000/24 ≈ 83.33 per period
        assert period_5.book_depreciation_keur == pytest.approx(83.33, rel=1e-2)
        # Tax same as book for financing costs
        assert period_5.tax_depreciation_keur == pytest.approx(83.33, rel=1e-2)


# ---------------------------------------------------------------------------
# Construction / placed-in-service timing
# ---------------------------------------------------------------------------

class TestConstructionTiming:
    def test_no_depreciation_before_cod(self):
        """No depreciation in construction period (before placed-in-service)."""
        inputs = make_engine_inputs(
            asset_classes=(
                AssetClassConfig(
                    asset_class="Turbine",
                    gross_asset_basis_keur=10000.0,
                    book_depreciable_basis_keur=10000.0,
                    tax_depreciable_basis_keur=10000.0,
                    placed_in_service_period=1,   # construction period = col G = period 1
                    depreciation_start_period=2,  # starts at COD = period 2
                ),
            ),
            policies={
                "default": DepreciationPolicy(useful_life_book_periods=40, useful_life_tax_periods=40),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)

        # Period 1 (construction): no depreciation
        period_1_rows = result.ledger_result.periods_for_index(1)
        assert len(period_1_rows) == 1
        assert period_1_rows[0].book_depreciation_keur == pytest.approx(0.0, abs=1e-9)

        # Period 2 (COD): depreciation starts
        period_2_rows = result.ledger_result.periods_for_index(2)
        assert period_2_rows[0].book_depreciation_keur > 0

    def test_gross_basis_zero_before_placed_in_service(self):
        """Gross basis is 0 before placed_in_service_period."""
        inputs = make_engine_inputs(
            asset_classes=(
                AssetClassConfig(
                    asset_class="Turbine",
                    gross_asset_basis_keur=10000.0,
                    book_depreciable_basis_keur=10000.0,
                    tax_depreciable_basis_keur=10000.0,
                    placed_in_service_period=3,  # first appears at period 3
                    depreciation_start_period=3,
                ),
            ),
            policies={
                "default": DepreciationPolicy(useful_life_book_periods=40, useful_life_tax_periods=40),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)

        # Period 1, 2: gross_basis = 0
        for idx in [1, 2]:
            rows = result.ledger_result.periods_for_index(idx)
            if rows:
                assert rows[0].gross_asset_basis_keur == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Accumulated depreciation and NBV roll-forward
# ---------------------------------------------------------------------------

class TestAccumulatedDepreciation:
    def test_accumulated_book_increases(self):
        """Accumulated book depreciation increases each period."""
        inputs = make_engine_inputs(
            asset_classes=(
                AssetClassConfig(
                    asset_class="Turbine",
                    gross_asset_basis_keur=10000.0,
                    book_depreciable_basis_keur=10000.0,
                    tax_depreciable_basis_keur=10000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(useful_life_book_periods=40, useful_life_tax_periods=40),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)

        period_5 = result.ledger_result.periods_for_index(5)[0]
        period_10 = result.ledger_result.periods_for_index(10)[0]

        # Accumulated grows over time
        assert period_10.accumulated_book_depreciation_keur > period_5.accumulated_book_depreciation_keur

    def test_nbv_decreases_to_zero(self):
        """NBV decreases to zero at end of depreciation life."""
        inputs = make_engine_inputs(
            asset_classes=(
                AssetClassConfig(
                    asset_class="Turbine",
                    gross_asset_basis_keur=10000.0,
                    book_depreciable_basis_keur=10000.0,
                    tax_depreciable_basis_keur=10000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(useful_life_book_periods=40, useful_life_tax_periods=40),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)

        # At period 41 (end of life): NBV should be 0
        last_depr_period = result.ledger_result.periods_for_index(41)
        if last_depr_period:
            assert last_depr_period[0].nbv_book_keur == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Unsupported method raises error
# ---------------------------------------------------------------------------

class TestUnsupportedMethod:
    def test_unsupported_method_raises(self):
        """DepreciationPolicy with unsupported method raises ValueError."""
        with pytest.raises(ValueError, match="Only straight_line"):
            DepreciationPolicy(method="declining_balance")


# ---------------------------------------------------------------------------
# Audit rows
# ---------------------------------------------------------------------------

class TestAuditRows:
    def test_audit_rows_populated(self):
        """Audit rows are populated for all periods and asset classes."""
        inputs = make_engine_inputs(
            asset_classes=(
                AssetClassConfig(
                    asset_class="Turbine",
                    gross_asset_basis_keur=10000.0,
                    book_depreciable_basis_keur=10000.0,
                    tax_depreciable_basis_keur=10000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(useful_life_book_periods=40, useful_life_tax_periods=40),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)

        assert len(result.audit_rows) > 0
        first_row = result.audit_rows[0]
        assert hasattr(first_row, "period_index")
        assert hasattr(first_row, "asset_class")
        assert hasattr(first_row, "book_depreciation_keur")
        assert hasattr(first_row, "nbv_book_keur")
        assert hasattr(first_row, "is_land")
        assert hasattr(first_row, "is_depreciable")
        assert hasattr(first_row, "warnings")


# ---------------------------------------------------------------------------
# R99/R102 not touched
# ---------------------------------------------------------------------------

class TestNoR99:
    def test_engine_does_not_compute_distribution(self):
        """DepreciationEngine does not compute R99/R102 or distribution gates."""
        inputs = make_engine_inputs(period_count=5)
        result = DepreciationEngine.compute(inputs)
        # Result has no distribution-related fields
        assert not hasattr(result, "cash_for_distribution")
        assert not hasattr(result, "distribution_gate")
        assert not hasattr(result, "r99_triggered")


# ---------------------------------------------------------------------------
# Total non-depreciable basis
# ---------------------------------------------------------------------------

class TestNonDepreciableBasis:
    def test_land_counted_in_non_depreciable(self):
        """Land basis is counted in total_non_depreciable_basis."""
        inputs = make_engine_inputs(
            asset_classes=(
                AssetClassConfig(
                    asset_class="Land",
                    gross_asset_basis_keur=500.0,
                    book_depreciable_basis_keur=0.0,
                    tax_depreciable_basis_keur=0.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
                AssetClassConfig(
                    asset_class="Turbine",
                    gross_asset_basis_keur=10000.0,
                    book_depreciable_basis_keur=10000.0,
                    tax_depreciable_basis_keur=10000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(useful_life_book_periods=40, useful_life_tax_periods=40),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)
        # Non-depreciable should be counted
        assert result.total_non_depreciable_basis_keur > 0


# ---------------------------------------------------------------------------
# Default policy fallback
# ---------------------------------------------------------------------------

class TestDefaultPolicy:
    def test_unknown_asset_class_uses_default_policy(self):
        """Asset class without explicit policy uses 'default' policy."""
        inputs = make_engine_inputs(
            asset_classes=(
                AssetClassConfig(
                    asset_class="Unknown Asset",
                    gross_asset_basis_keur=5000.0,
                    book_depreciable_basis_keur=5000.0,
                    tax_depreciable_basis_keur=5000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(
                    useful_life_book_periods=40,
                    useful_life_tax_periods=40,
                ),
            },
            period_count=63,
        )
        # Should not raise — uses default policy
        result = DepreciationEngine.compute(inputs)
        assert result.total_book_depreciation_keur > 0


# ---------------------------------------------------------------------------
# Croatia renewable fallback useful life policy
# ---------------------------------------------------------------------------

class TestCroatiaRenewableFallback:
    def test_main_renewable_20_year_fallback(self):
        """Main renewable CAPEX → 20 years (40 semiannual periods)."""
        inputs = make_engine_inputs(
            asset_classes=(
                AssetClassConfig(
                    asset_class="Wind Turbine",
                    gross_asset_basis_keur=8000.0,
                    book_depreciable_basis_keur=8000.0,
                    tax_depreciable_basis_keur=8000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(
                    useful_life_book_periods=40,  # 20 years semiannual
                    useful_life_tax_periods=40,
                ),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)
        period_depr = result.ledger_result.periods_for_index(5)[0]
        assert period_depr.book_depreciation_keur == pytest.approx(200.0, rel=1e-9)  # 8000/40

    def test_vat_20_year_if_basis_eligible(self):
        """VAT capitalized → 20 years if basis-eligible."""
        inputs = make_engine_inputs(
            asset_classes=(
                AssetClassConfig(
                    asset_class="VAT Recovered",
                    gross_asset_basis_keur=1600.0,
                    book_depreciable_basis_keur=1600.0,
                    tax_depreciable_basis_keur=1600.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={
                "default": DepreciationPolicy(
                    useful_life_book_periods=40,  # 20 years
                    useful_life_tax_periods=40,
                ),
            },
            period_count=63,
        )
        result = DepreciationEngine.compute(inputs)
        period_depr = result.ledger_result.periods_for_index(5)[0]
        assert period_depr.book_depreciation_keur == pytest.approx(40.0, rel=1e-9)  # 1600/40


if __name__ == "__main__":
    pytest.main([__file__, "-v"])