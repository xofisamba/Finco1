"""Phase 6B.2/6B.3 tests for tax depreciation and loss carryforward schedules."""
from __future__ import annotations

import pytest

from domain.tax.templates.inputs import TaxDepreciationRule, CITTier
from domain.tax.templates.schedules import (
    TaxDepreciationPeriod,
    TaxDepreciationSchedule,
    build_tax_depreciation_schedule,
    TaxLossPeriod,
    TaxLossCarryforwardSchedule,
    build_tax_loss_carryforward_schedule,
)
from domain.tax.templates.registry import ME_INFRA_2026


# ── build_tax_depreciation_schedule ──────────────────────────────────────────

class TestBuildTaxDepreciationSchedule:
    def test_straight_line_tax_depreciation(self):
        """Plain 5-year straight-line asset: book dep = tax dep = 200/year."""
        rule = TaxDepreciationRule(
            asset_category="equipment",
            method="straight_line",
            annual_rate=None,
            useful_life_years=5.0,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="5-year SL",
        )
        book_dep = (200.0,) * 5  # 1000 cost / 5 years = 200/year
        schedule = build_tax_depreciation_schedule(1000.0, book_dep, rule)

        assert len(schedule.periods) == 5
        assert schedule.asset_category == "equipment"
        assert schedule.total_book_depreciation_keur == 1000.0
        assert schedule.total_tax_depreciation_keur == 1000.0
        assert schedule.total_non_deductible_depreciation_keur == 0.0

        # Check closing tax basis goes to 0
        assert schedule.periods[-1].closing_tax_basis_keur == 0.0

    def test_me_infrastructure_2p5_cap_creates_non_deductible(self):
        """ME infrastructure: book rate 5% (20y SL) but tax capped at 2.5%/year.

        For a 10,000 kEUR asset:
        - book dep/year = 500 kEUR (5%)
        - tax dep/year = 250 kEUR (2.5% cap)
        - non-deductible/year = 250 kEUR
        """
        infra_rule = next(
            (r for r in ME_INFRA_2026.depreciation_rules
             if r.asset_category == "infrastructure"),
            None,
        )
        assert infra_rule is not None

        # 10,000 kEUR asset, 20 years of book depreciation
        book_dep = (500.0,) * 20  # 5% of 10,000 = 500/year
        schedule = build_tax_depreciation_schedule(10_000.0, book_dep, infra_rule)

        assert len(schedule.periods) == 20
        # Tax depreciation capped at 2.5% × 10,000 = 250/year
        assert schedule.total_tax_depreciation_keur == pytest.approx(250.0 * 20)
        # Non-deductible = book dep - tax dep = (500 - 250) × 20 = 5,000 kEUR total
        assert schedule.total_non_deductible_depreciation_keur == pytest.approx(250.0 * 20)
        # Accumulated non-deductible at end = 5,000 kEUR
        assert schedule.periods[-1].accumulated_non_deductible_depreciation_keur == pytest.approx(250.0 * 20)
        # Closing tax basis after 20 years = 10,000 - 5,000 = 5,000
        # (tax dep only = 2.5%/year × 20 = 5,000 total; accounting dep fully depletes)
        assert schedule.periods[-1].closing_tax_basis_keur == pytest.approx(5000.0)
        # Accumulated non-deductible at end = 5,000 kEUR
        assert schedule.periods[-1].accumulated_non_deductible_depreciation_keur == pytest.approx(250.0 * 20)

    def test_non_deductible_asset_zero_tax_depreciation(self):
        """Land: non-deductible → tax dep = 0, all book dep is non-deductible."""
        land_rule = TaxDepreciationRule(
            asset_category="land",
            method="straight_line",
            annual_rate=0.0,
            useful_life_years=None,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=False,
            notes="non-deductible land",
        )
        book_dep = (50.0,) * 20  # 1,000 total book dep over 20 years
        schedule = build_tax_depreciation_schedule(1000.0, book_dep, land_rule)

        assert schedule.total_tax_depreciation_keur == 0.0
        assert schedule.total_non_deductible_depreciation_keur == 1000.0
        # Tax basis never changes (no deduction ever taken)
        assert all(p.closing_tax_basis_keur == 1000.0 for p in schedule.periods)

    def test_tax_depreciation_never_exceeds_remaining_basis(self):
        """Tax dep in any period cannot exceed the opening tax basis."""
        rule = TaxDepreciationRule(
            asset_category="equipment",
            method="straight_line",
            annual_rate=None,
            useful_life_years=5.0,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="",
        )
        # Large single-period depreciation (more than remaining basis)
        book_dep = (1000.0,) * 1  # single period, dep = full cost
        schedule = build_tax_depreciation_schedule(1000.0, book_dep, rule)

        # Tax dep/year = min(base_rate × cost, opening_basis) = min(200, 1000) = 200
        # closing_basis = 1000 - 200 = 800 (tax dep capped at 200, not 1000)
        assert schedule.periods[0].tax_depreciation_keur <= 1000.0
        assert schedule.periods[0].closing_tax_basis_keur == pytest.approx(800.0)

    def test_negative_asset_cost_raises(self):
        rule = TaxDepreciationRule(
            asset_category="equipment", method="straight_line",
            annual_rate=0.20, useful_life_years=None,
            max_deductible_rate=None, bonus_depreciation_pct=0.0,
            deductible=True, notes="",
        )
        with pytest.raises(ValueError, match="asset_cost_keur must be >= 0"):
            build_tax_depreciation_schedule(-100.0, (100.0,), rule)

    def test_negative_book_depreciation_raises(self):
        rule = TaxDepreciationRule(
            asset_category="equipment", method="straight_line",
            annual_rate=0.20, useful_life_years=None,
            max_deductible_rate=None, bonus_depreciation_pct=0.0,
            deductible=True, notes="",
        )
        with pytest.raises(ValueError, match="book_depreciation_by_period must be non-negative"):
            build_tax_depreciation_schedule(1000.0, (100.0, -50.0), rule)

    def test_totals_reconcile(self):
        """Book dep = tax dep + non-deductible for each period."""
        rule = TaxDepreciationRule(
            asset_category="equipment",
            method="straight_line",
            annual_rate=None,
            useful_life_years=5.0,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="",
        )
        book_dep = (200.0,) * 5
        schedule = build_tax_depreciation_schedule(1000.0, book_dep, rule)

        for p in schedule.periods:
            assert (p.book_depreciation_keur - p.tax_depreciation_keur
                    - p.non_deductible_depreciation_keur) == pytest.approx(0.0, abs=1e-9)

    def test_closing_basis_cannot_be_negative(self):
        """Closing tax basis should never go below zero."""
        rule = TaxDepreciationRule(
            asset_category="equipment",
            method="straight_line",
            annual_rate=0.25,
            useful_life_years=None,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="",
        )
        # 4 years × 250 = 1000; year 5 tries to deduct more than remains
        book_dep = (250.0,) * 5
        schedule = build_tax_depreciation_schedule(1000.0, book_dep, rule)

        for p in schedule.periods:
            assert p.closing_tax_basis_keur >= 0.0

    def test_empty_schedule(self):
        """Zero periods — empty book depreciation tuple."""
        rule = TaxDepreciationRule(
            asset_category="equipment",
            method="straight_line",
            annual_rate=0.20,
            useful_life_years=None,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="",
        )
        schedule = build_tax_depreciation_schedule(1000.0, (), rule)
        assert schedule.periods == ()
        assert schedule.total_book_depreciation_keur == 0.0
        assert schedule.total_tax_depreciation_keur == 0.0

    def test_no_mutation_of_rule(self):
        """Rule object should not be modified."""
        rule = TaxDepreciationRule(
            asset_category="equipment",
            method="straight_line",
            annual_rate=0.20,
            useful_life_years=None,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="original",
        )
        build_tax_depreciation_schedule(1000.0, (200.0,), rule)
        assert rule.asset_category == "equipment"

    def test_me_infra_cap_partial_depreciation(self):
        """Large asset with ME 2.5% cap: tax dep much lower than book dep.

        5,000 kEUR asset, 20-year life, 2.5% cap:
        - book dep/year = 250 kEUR (5% of 5,000)
        - tax dep/year = 125 kEUR (2.5% of 5,000)
        - non-ded/year = 125 kEUR
        """
        infra_rule = next(
            (r for r in ME_INFRA_2026.depreciation_rules
             if r.asset_category == "infrastructure"),
            None,
        )
        book_dep = (250.0,) * 20  # 5% of 5,000
        schedule = build_tax_depreciation_schedule(5_000.0, book_dep, infra_rule)

        assert schedule.total_tax_depreciation_keur == pytest.approx(125.0 * 20)
        assert schedule.total_non_deductible_depreciation_keur == pytest.approx(125.0 * 20)


# ── build_tax_loss_carryforward_schedule ─────────────────────────────────────

class TestBuildTaxLossCarryforwardSchedule:
    def test_loss_generated_in_negative_income_period(self):
        """Period with negative taxable income generates a new loss."""
        income = (-100.0, 200.0, -50.0)
        schedule = build_tax_loss_carryforward_schedule(income, None)

        # Period 0: loss of 100 generated
        assert schedule.periods[0].new_loss_generated_keur == 100.0
        assert schedule.periods[0].loss_used_keur == 0.0
        assert schedule.periods[0].taxable_income_after_losses_keur == 0.0

    def test_loss_used_in_later_positive_period(self):
        """Positive income in a later period uses the accumulated loss pool."""
        income = (-100.0, 200.0, -50.0)
        schedule = build_tax_loss_carryforward_schedule(income, None)

        # Period 1: income=200, opening=100, use 100, taxable_after=100
        assert schedule.periods[1].loss_used_keur == 100.0
        assert schedule.periods[1].taxable_income_after_losses_keur == 100.0
        assert schedule.periods[1].new_loss_generated_keur == 0.0

        # Period 2: income=-50, opening=0, generate new loss
        assert schedule.periods[2].loss_used_keur == 0.0
        assert schedule.periods[2].new_loss_generated_keur == 50.0

    def test_loss_use_capped_at_taxable_income(self):
        """Loss used cannot exceed the positive taxable income available."""
        income = (-500.0, 100.0)  # pool = 500, income = 100
        schedule = build_tax_loss_carryforward_schedule(income, None)

        # Period 1: can only use 100 (income), not full 500
        assert schedule.periods[1].loss_used_keur == 100.0
        assert schedule.periods[1].taxable_income_after_losses_keur == 0.0  # income fully offset
        assert schedule.periods[1].closing_loss_carryforward_keur == 400.0  # 500 - 100

    def test_unlimited_carryforward_works(self):
        """None loss_carryforward_years means unlimited carryforward."""
        income = (-200.0, 50.0, 50.0, 50.0)  # pool builds to 200, then used over 3 periods
        schedule = build_tax_loss_carryforward_schedule(income, None)

        # Period 1: 200 loss generated
        assert schedule.periods[0].new_loss_generated_keur == 200.0
        assert schedule.periods[0].closing_loss_carryforward_keur == 200.0

        # Period 2: use 50, remaining 150
        assert schedule.periods[1].loss_used_keur == 50.0
        assert schedule.periods[1].closing_loss_carryforward_keur == 150.0

        # Period 3: use 50, remaining 100
        assert schedule.periods[2].loss_used_keur == 50.0
        assert schedule.periods[2].closing_loss_carryforward_keur == 100.0

        # Period 4: use 50, remaining 50
        assert schedule.periods[3].loss_used_keur == 50.0
        assert schedule.periods[3].closing_loss_carryforward_keur == 50.0

        assert schedule.loss_carryforward_years is None

    def test_finite_carryforward_accepted_no_vintage_expiry(self):
        """Finite loss_carryforward_years is stored but vintage expiry is deferred."""
        income = (-200.0, 50.0, 50.0, 50.0)
        schedule = build_tax_loss_carryforward_schedule(income, 5)

        # Pool still tracked the same way (vintage expiry deferred)
        assert schedule.periods[0].new_loss_generated_keur == 200.0
        assert schedule.loss_carryforward_years == 5

    def test_totals_reconcile(self):
        """ending_pool = opening_pool + total_new - total_used."""
        income = (-100.0, 200.0, -50.0)
        schedule = build_tax_loss_carryforward_schedule(income, None)

        expected_ending = 0.0 + 100.0 + 50.0 - 100.0  # opening(0) + new(150) - used(100)
        assert schedule.ending_loss_carryforward_keur == pytest.approx(expected_ending)
        assert (schedule.total_new_loss_generated_keur
                - schedule.total_loss_used_keur) == pytest.approx(
            schedule.ending_loss_carryforward_keur
        )

    def test_empty_income_tuple_returns_empty_schedule(self):
        """No periods when income tuple is empty."""
        schedule = build_tax_loss_carryforward_schedule((), None)

        assert schedule.periods == ()
        assert schedule.total_loss_used_keur == 0.0
        assert schedule.total_new_loss_generated_keur == 0.0
        assert schedule.ending_loss_carryforward_keur == 0.0

    def test_no_mutation_of_inputs(self):
        """Verify inputs are not modified."""
        income = (-100.0, 200.0)
        schedule = build_tax_loss_carryforward_schedule(income, 5)

        # Income tuple unchanged
        assert income == (-100.0, 200.0)
        # Schedule's loss_carryforward_years unchanged
        assert schedule.loss_carryforward_years == 5

    def test_positive_income_no_loss_pool_no_new_loss(self):
        """When no pool and income is positive: no loss used, no new loss."""
        income = (100.0, 200.0)
        schedule = build_tax_loss_carryforward_schedule(income, None)

        assert all(p.loss_used_keur == 0.0 for p in schedule.periods)
        assert all(p.new_loss_generated_keur == 0.0 for p in schedule.periods)
        assert all(p.taxable_income_after_losses_keur == p.taxable_income_before_losses_keur
                   for p in schedule.periods)
        assert schedule.ending_loss_carryforward_keur == 0.0

    def test_loss_pool_not_below_zero(self):
        """Closing pool never goes negative."""
        income = (-50.0, 200.0)  # pool = 50, then use 50, then excess income
        schedule = build_tax_loss_carryforward_schedule(income, None)

        assert all(p.closing_loss_carryforward_keur >= 0.0
                   for p in schedule.periods)
        assert schedule.ending_loss_carryforward_keur == 0.0

    def test_taxable_after_losses_not_negative(self):
        """When income is positive, taxable_income_after_losses >= 0."""
        income = (-100.0, 50.0)
        schedule = build_tax_loss_carryforward_schedule(income, None)

        # Period 1: taxable_after = max(0, 50 - 100) = 0
        assert schedule.periods[1].taxable_income_after_losses_keur >= 0.0