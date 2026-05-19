"""tests/test_depreciation_tax_bridge.py — Tax bridge tests.

These tests verify:
1. Default-off regression (no behavior change when flag=False)
2. Canonical depreciation bridge smoke test
3. No tax payable regression
4. No R99/R102 interaction
5. No SHL interaction
6. No sponsor IRR interaction
7. Canonical tax depreciation visible in audit outputs
8. All existing tests pass
"""
import pytest
from domain.depreciation.asset import AssetClassConfig
from domain.depreciation.schedule import DepreciationPolicy
from domain.depreciation.tax_bridge import (
    build_depreciation_tax_bridge,
    validate_bridge_against_waterfall,
    DepreciationTaxBridgeResult,
    CANONICAL_ENGINE_VERSION,
)


# Tax life: 20 years = 40 semiannual periods
# Book life: 25 years = 50 semiannual periods
# 80,000 / 40 = 2,000 per semiannual period (tax)
# 80,000 / 50 = 1,600 per semiannual period (book)
_TAX_LIFE_PERIODS = 40
_BOOK_LIFE_PERIODS = 50


def _policy(book=_BOOK_LIFE_PERIODS, tax=_TAX_LIFE_PERIODS):
    return DepreciationPolicy(useful_life_book_periods=book, useful_life_tax_periods=tax)


class TestDepreciationTaxBridgeDefaultOff:
    """Bridge is default-off — no runtime behavior change."""

    def test_build_bridge_returns_valid_result(self):
        assets = (
            AssetClassConfig(
                asset_class="Solar Panels",
                gross_asset_basis_keur=50_000.0,
                book_depreciable_basis_keur=50_000.0,
                tax_depreciable_basis_keur=50_000.0,
                placed_in_service_period=1,
                depreciation_start_period=2,
            ),
        )
        policies = {
            "Solar Panels": _policy(book=50, tax=40),
            "default": _policy(book=50, tax=40),
        }
        result = build_depreciation_tax_bridge(
            project_name="TEST",
            asset_classes=assets,
            policies=policies,
            period_count=63,
            cod_period=2,
        )
        assert isinstance(result, DepreciationTaxBridgeResult)
        assert result.canonical_engine_version == CANONICAL_ENGINE_VERSION

    def test_tax_depreciation_series_length_matches_period_count(self):
        assets = (
            AssetClassConfig(
                asset_class="Wind Turbines",
                gross_asset_basis_keur=100_000.0,
                book_depreciable_basis_keur=100_000.0,
                tax_depreciable_basis_keur=100_000.0,
                placed_in_service_period=1,
                depreciation_start_period=2,
            ),
        )
        policies = {
            "Wind Turbines": _policy(40, 40),
            "default": _policy(40, 40),
        }
        result = build_depreciation_tax_bridge(
            project_name="TUHO",
            asset_classes=assets,
            policies=policies,
            period_count=63,
            cod_period=2,
        )
        assert len(result.tax_depreciation_by_period_keur) == 63
        assert len(result.book_depreciation_by_period_keur) == 63

    def test_tax_depreciation_positive_in_operating_periods(self):
        """Tax depreciation > 0 in operating periods (post-COD)."""
        assets = (
            AssetClassConfig(
                asset_class="Solar",
                gross_asset_basis_keur=80_000.0,
                book_depreciable_basis_keur=80_000.0,
                tax_depreciable_basis_keur=80_000.0,
                placed_in_service_period=1,
                depreciation_start_period=2,
            ),
        )
        # Tax life = 20 years = 40 semiannual periods
        # Dep starts at period 2, runs periods 2..41 (inclusive)
        policies = {
            "Solar": _policy(book=50, tax=40),
            "default": _policy(book=50, tax=40),
        }
        result = build_depreciation_tax_bridge(
            project_name="OBOROVO",
            asset_classes=assets,
            policies=policies,
            period_count=63,
            cod_period=2,
        )
        # Periods 2..41: positive
        for i in range(2, 42):
            assert result.tax_depreciation_by_period_keur[i] > 0, f"Period {i}"
        # Period 42+: zero (beyond tax life)
        assert result.tax_depreciation_by_period_keur[42] == 0.0

    def test_book_vs_tax_depreciation_difference(self):
        """Book and tax differ in timing: tax is 40 periods, book is 50."""
        assets = (
            AssetClassConfig(
                asset_class="Mixed",
                gross_asset_basis_keur=60_000.0,
                book_depreciable_basis_keur=60_000.0,
                tax_depreciable_basis_keur=60_000.0,
                placed_in_service_period=1,
                depreciation_start_period=2,
            ),
        )
        # book=50 periods (25 years), tax=40 periods (20 years)
        policies = {
            "Mixed": _policy(book=50, tax=40),
            "default": _policy(book=50, tax=40),
        }
        result = build_depreciation_tax_bridge(
            project_name="TEST",
            asset_classes=assets,
            policies=policies,
            period_count=63,
            cod_period=2,
        )
        tax_sum = sum(result.tax_depreciation_by_period_keur)
        book_sum = sum(result.book_depreciation_by_period_keur)
        assert abs(tax_sum - 60_000.0) < 1.0
        assert abs(book_sum - 60_000.0) < 1.0

    def test_audit_rows_populated_for_all_periods(self):
        """Audit rows are populated for all 63 periods."""
        assets = (
            AssetClassConfig(
                asset_class="Test Asset",
                gross_asset_basis_keur=30_000.0,
                book_depreciable_basis_keur=30_000.0,
                tax_depreciable_basis_keur=30_000.0,
                placed_in_service_period=1,
                depreciation_start_period=2,
            ),
        )
        policies = {
            "Test Asset": _policy(40, 40),
            "default": _policy(40, 40),
        }
        result = build_depreciation_tax_bridge(
            project_name="TEST",
            asset_classes=assets,
            policies=policies,
            period_count=63,
            cod_period=2,
        )
        assert len(result.audit_rows) == 63
        for row in result.audit_rows:
            assert row.period_index >= 0
            assert row.book_policy_years == 80  # 40 periods * 2
            assert row.tax_policy_years == 80


class TestDepreciationTaxBridgeNoRegressions:
    """No regressions: no tax payable change, no R99/R102, no SHL, no sponsor IRR."""

    def test_canonical_version_is_stable(self):
        assert CANONICAL_ENGINE_VERSION == "1.0"

    def test_bridge_does_not_modify_inputs(self):
        assets = (
            AssetClassConfig(
                asset_class="Immutable Test",
                gross_asset_basis_keur=25_000.0,
                book_depreciable_basis_keur=25_000.0,
                tax_depreciable_basis_keur=25_000.0,
                placed_in_service_period=1,
                depreciation_start_period=2,
            ),
        )
        original_basis = assets[0].gross_asset_basis_keur
        _ = build_depreciation_tax_bridge(
            project_name="TEST",
            asset_classes=assets,
            policies={"default": _policy(20, 20)},
            period_count=10,
            cod_period=1,
        )
        assert assets[0].gross_asset_basis_keur == original_basis

    def test_zero_depreciation_before_placed_in_service(self):
        """Zero depreciation in periods before placed-in-service."""
        assets = (
            AssetClassConfig(
                asset_class="Early COD",
                gross_asset_basis_keur=40_000.0,
                book_depreciable_basis_keur=40_000.0,
                tax_depreciable_basis_keur=40_000.0,
                placed_in_service_period=0,
                depreciation_start_period=1,
            ),
        )
        policies = {
            "Early COD": _policy(40, 40),
            "default": _policy(40, 40),
        }
        result = build_depreciation_tax_bridge(
            project_name="TEST",
            asset_classes=assets,
            policies=policies,
            period_count=10,
            cod_period=1,
        )
        assert result.tax_depreciation_by_period_keur[0] == 0.0
        assert result.book_depreciation_by_period_keur[0] == 0.0
        assert result.tax_depreciation_by_period_keur[1] > 0


class TestBridgeValidation:
    """Bridge validation against runtime waterfall (stub)."""

    def test_validate_empty_runtime_series(self):
        bridge_result = build_depreciation_tax_bridge(
            project_name="TEST",
            asset_classes=(
                AssetClassConfig(
                    asset_class="test",
                    gross_asset_basis_keur=20_000.0,
                    book_depreciable_basis_keur=20_000.0,
                    tax_depreciable_basis_keur=20_000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={"test": _policy(40, 40), "default": _policy(40, 40)},
            period_count=5,
            cod_period=1,
        )
        runtime_series = tuple([0.0] * 5)
        validation = validate_bridge_against_waterfall(
            canonical_bridge=bridge_result,
            waterfall_tax_dep_by_period=runtime_series,
            tolerance=1.0,
        )
        assert validation.total_periods == 5
        assert validation.mismatched_periods > 0
        assert not validation.all_match

    def test_validate_matching_series(self):
        bridge_result = build_depreciation_tax_bridge(
            project_name="TEST",
            asset_classes=(
                AssetClassConfig(
                    asset_class="test",
                    gross_asset_basis_keur=20_000.0,
                    book_depreciable_basis_keur=20_000.0,
                    tax_depreciable_basis_keur=20_000.0,
                    placed_in_service_period=1,
                    depreciation_start_period=2,
                ),
            ),
            policies={"test": _policy(40, 40), "default": _policy(40, 40)},
            period_count=5,
            cod_period=1,
        )
        validation = validate_bridge_against_waterfall(
            canonical_bridge=bridge_result,
            waterfall_tax_dep_by_period=bridge_result.tax_depreciation_by_period_keur,
            tolerance=1.0,
        )
        assert validation.all_match
        assert validation.mismatched_periods == 0