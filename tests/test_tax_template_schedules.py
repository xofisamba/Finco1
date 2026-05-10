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
    def test_straight_line_no_cap(self):
        """Plain 5-year SL asset: book dep = tax dep = 200/year, no timing diff."""
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
        book_dep = (200.0,) * 5  # 1000 / 5 = 200/year
        schedule = build_tax_depreciation_schedule(1000.0, book_dep, rule)

        assert len(schedule.periods) == 5
        assert schedule.asset_category == "equipment"
        assert schedule.total_book_depreciation_keur == 1000.0
        assert schedule.total_tax_depreciation_keur == 1000.0
        assert schedule.total_non_deductible_depreciation_keur == 0.0
        assert schedule.periods[-1].closing_tax_basis_keur == 0.0
        assert schedule.periods[-1].accumulated_non_deductible_depreciation_keur == 0.0

    def test_me_infrastructure_2p5_cap_timing_difference_reversal(self):
        """ME infrastructure: 2.5% tax cap creates timing diff that reverses later.

        10,000 kEUR asset, 20y book depreciation (5% = 500/year), 2.5% tax cap = 250/year.

        Years 1-20: book dep 500, tax cap 250 → tax dep 250, non-ded 250/year accumulated
        Years 21-40: book dep 0, tax cap 250 but accumulated timing diff exists →
                     tax dep = min(250, remaining_basis, accumulated) → continues
                     until tax basis = 0

        After 40 years: tax dep = 10,000 total (all basis recovered), accumulated = 0.
        """
        infra_rule = next(
            (r for r in ME_INFRA_2026.depreciation_rules
             if r.asset_category == "infrastructure"),
            None,
        )
        assert infra_rule is not None

        # 20 years of book dep + 20 years of extension (40 periods total)
        book_dep_20y = (500.0,) * 20
        schedule = build_tax_depreciation_schedule(10_000.0, book_dep_20y, infra_rule)

        # Years 1-20: tax dep = 250/year (cap), non-ded = 250/year
        assert schedule.periods[0].tax_depreciation_keur == pytest.approx(250.0)
        assert schedule.periods[0].non_deductible_depreciation_keur == pytest.approx(250.0)
        assert schedule.periods[0].accumulated_non_deductible_depreciation_keur == pytest.approx(250.0)

        # At end of year 20: accumulated = 5,000 kEUR (20 × 250)
        assert schedule.periods[19].accumulated_non_deductible_depreciation_keur == pytest.approx(5000.0)
        # Tax basis after 20 years of 250/year dep = 10,000 - 5,000 = 5,000
        assert schedule.periods[19].closing_tax_basis_keur == pytest.approx(5000.0)

    def test_me_infra_extends_beyond_book_depreciation(self):
        """With 40 periods (20y book dep + 20y extension), tax basis goes to 0.

        After book dep ends (period 20), tax dep continues from accumulated pool.
        """
        infra_rule = next(
            (r for r in ME_INFRA_2026.depreciation_rules
             if r.asset_category == "infrastructure"),
            None,
        )
        # 20 years book dep at 500, then 20 years with 0 book dep
        book_dep = (500.0,) * 20 + (0.0,) * 20
        schedule = build_tax_depreciation_schedule(10_000.0, book_dep, infra_rule)

        assert len(schedule.periods) == 40

        # At period 20 (book dep just ended):
        p20 = schedule.periods[19]
        assert p20.book_depreciation_keur == 500.0
        assert p20.tax_depreciation_keur == pytest.approx(250.0)
        assert p20.accumulated_non_deductible_depreciation_keur == pytest.approx(5000.0)

        # At period 21 (book dep = 0, tax dep from accumulated pool):
        p21 = schedule.periods[20]
        assert p21.book_depreciation_keur == 0.0
        # tax_dep = min(250, 5000, 5000) = 250 → reduces accumulated
        assert p21.tax_depreciation_keur == pytest.approx(250.0)
        assert p21.accumulated_non_deductible_depreciation_keur == pytest.approx(4750.0)

        # At period 39 (last extension period):
        p39 = schedule.periods[39]
        # After 20 more years of 250/year tax dep, accumulated goes to 0
        # closing basis should be 0
        assert p39.closing_tax_basis_keur == pytest.approx(0.0)
        assert p39.accumulated_non_deductible_depreciation_keur == pytest.approx(0.0)

        # Total tax dep = 10,000 (all basis recovered)
        assert schedule.total_tax_depreciation_keur == pytest.approx(10_000.0)

    def test_me_infra_accumulated_declines_after_book_dep_ends(self):
        """After book depreciation ends, accumulated_non_deductible decreases."""
        infra_rule = next(
            (r for r in ME_INFRA_2026.depreciation_rules
             if r.asset_category == "infrastructure"),
            None,
        )
        book_dep = (500.0,) * 20 + (0.0,) * 20
        schedule = build_tax_depreciation_schedule(10_000.0, book_dep, infra_rule)

        accumulated_at_20 = schedule.periods[19].accumulated_non_deductible_depreciation_keur
        accumulated_at_21 = schedule.periods[20].accumulated_non_deductible_depreciation_keur

        # After book dep ends, accumulated starts declining
        assert accumulated_at_21 < accumulated_at_20
        # It continues declining each period until 0
        assert schedule.periods[39].accumulated_non_deductible_depreciation_keur == 0.0

    def test_tax_depreciation_never_exceeds_opening_basis(self):
        """In every period, tax dep ≤ opening tax basis."""
        infra_rule = next(
            (r for r in ME_INFRA_2026.depreciation_rules
             if r.asset_category == "infrastructure"),
            None,
        )
        book_dep = (500.0,) * 20 + (0.0,) * 20
        schedule = build_tax_depreciation_schedule(10_000.0, book_dep, infra_rule)

        for p in schedule.periods:
            assert p.tax_depreciation_keur <= p.opening_tax_basis_keur + 1e-9

    def test_non_deductible_asset_permanent_no_reversal(self):
        """Non-deductible land: tax dep always 0, never reverses.

        The accumulated_non_deductible is NOT recovered — it represents
        permanently disallowed depreciation (e.g., land in many jurisdictions).
        """
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

        # Tax dep always 0
        assert schedule.total_tax_depreciation_keur == 0.0

        # All book dep is permanently non-deductible
        assert schedule.total_non_deductible_depreciation_keur == 1000.0

        # Tax basis never changes
        assert all(p.closing_tax_basis_keur == 1000.0 for p in schedule.periods)

        # Accumulated stays at 1000 (permanent, not timing diff)
        assert schedule.periods[-1].accumulated_non_deductible_depreciation_keur == 1000.0

        # After 20 years book dep ends, land still has 1000 basis (never recovers)

    def test_totals_reconcile(self):
        """book_dep = tax_dep + non_deductible for each period."""
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
            diff = abs(p.book_depreciation_keur - p.tax_depreciation_keur - p.non_deductible_depreciation_keur)
            assert diff < 1e-9, f"period {p.period}: book={p.book_depreciation_keur}, tax={p.tax_depreciation_keur}, non_ded={p.non_deductible_depreciation_keur}"

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

    def test_closing_basis_cannot_be_negative(self):
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
        book_dep = (250.0,) * 5  # 4 years would be 1000; year 5 tries more than remains
        schedule = build_tax_depreciation_schedule(1000.0, book_dep, rule)

        for p in schedule.periods:
            assert p.closing_tax_basis_keur >= 0.0

    def test_empty_schedule(self):
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

    def test_partial_depreciation_smaller_asset(self):
        """5,000 kEUR asset with ME 2.5% cap: all basis recovered via timing diff reversal.

        5,000 kEUR asset, 20y book depreciation (5% = 250/year), 2.5% tax cap = 125/year.

        Years 1-20: book dep 250, tax cap 125 → tax dep 125, non-ded 125/year accumulated
        Years 21-40: book dep 0, tax dep continues from accumulated pool → 125/year

        After 40 years: tax dep = 5,000 (all basis), final accum = 0 (reversed).
        """
        infra_rule = next(
            (r for r in ME_INFRA_2026.depreciation_rules
             if r.asset_category == "infrastructure"),
            None,
        )
        book_dep = (250.0,) * 20 + (0.0,) * 20  # 5% of 5,000 = 250/year
        schedule = build_tax_depreciation_schedule(5_000.0, book_dep, infra_rule)

        # Total tax dep = 5,000 (all basis recovered)
        assert schedule.total_tax_depreciation_keur == pytest.approx(5_000.0)
        # Final accumulated = 0 (timing difference fully reversed)
        assert schedule.periods[-1].accumulated_non_deductible_depreciation_keur == 0.0
        # Final tax basis = 0
        assert schedule.periods[-1].closing_tax_basis_keur == 0.0

    def test_me_infra_tax_dep_continues_after_book_dep(self):
        """Verify tax dep > 0 in periods after book dep ends."""
        infra_rule = next(
            (r for r in ME_INFRA_2026.depreciation_rules
             if r.asset_category == "infrastructure"),
            None,
        )
        book_dep = (500.0,) * 20 + (0.0,) * 20
        schedule = build_tax_depreciation_schedule(10_000.0, book_dep, infra_rule)

        # Period 20 (index 20): book dep = 0, but accumulated = 5000
        p21 = schedule.periods[20]
        assert p21.book_depreciation_keur == 0.0
        # tax dep comes from accumulated pool: min(250, 5000, 5000) = 250
        assert p21.tax_depreciation_keur > 0.0

        # Period 35: still going
        p36 = schedule.periods[35]
        assert p36.book_depreciation_keur == 0.0
        assert p36.tax_depreciation_keur > 0.0

        # Period 39: last one, basis goes to 0
        p40 = schedule.periods[39]
        assert p40.closing_tax_basis_keur == 0.0
        assert p40.accumulated_non_deductible_depreciation_keur == 0.0


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
        assert schedule.periods[1].taxable_income_after_losses_keur == 0.0
        assert schedule.periods[1].closing_loss_carryforward_keur == 400.0

    def test_unlimited_carryforward_works(self):
        """None loss_carryforward_years means unlimited carryforward."""
        income = (-200.0, 50.0, 50.0, 50.0)
        schedule = build_tax_loss_carryforward_schedule(income, None)

        assert schedule.periods[0].new_loss_generated_keur == 200.0
        assert schedule.periods[0].closing_loss_carryforward_keur == 200.0

        assert schedule.periods[1].loss_used_keur == 50.0
        assert schedule.periods[1].closing_loss_carryforward_keur == 150.0

        assert schedule.periods[2].loss_used_keur == 50.0
        assert schedule.periods[2].closing_loss_carryforward_keur == 100.0

        assert schedule.periods[3].loss_used_keur == 50.0
        assert schedule.periods[3].closing_loss_carryforward_keur == 50.0

        assert schedule.loss_carryforward_years is None

    def test_finite_carryforward_accepted_no_vintage_expiry(self):
        """Finite loss_carryforward_years is stored but vintage expiry is deferred."""
        income = (-200.0, 50.0, 50.0, 50.0)
        schedule = build_tax_loss_carryforward_schedule(income, 5)

        assert schedule.periods[0].new_loss_generated_keur == 200.0
        assert schedule.loss_carryforward_years == 5

    def test_totals_reconcile(self):
        """ending_pool = opening_pool + total_new - total_used."""
        income = (-100.0, 200.0, -50.0)
        schedule = build_tax_loss_carryforward_schedule(income, None)

        expected_ending = 0.0 + 100.0 + 50.0 - 100.0
        assert schedule.ending_loss_carryforward_keur == pytest.approx(expected_ending)
        assert (schedule.total_new_loss_generated_keur
                - schedule.total_loss_used_keur) == pytest.approx(
            schedule.ending_loss_carryforward_keur
        )

    def test_empty_income_tuple_returns_empty_schedule(self):
        schedule = build_tax_loss_carryforward_schedule((), None)

        assert schedule.periods == ()
        assert schedule.total_loss_used_keur == 0.0
        assert schedule.total_new_loss_generated_keur == 0.0
        assert schedule.ending_loss_carryforward_keur == 0.0

    def test_no_mutation_of_inputs(self):
        income = (-100.0, 200.0)
        schedule = build_tax_loss_carryforward_schedule(income, 5)

        assert income == (-100.0, 200.0)
        assert schedule.loss_carryforward_years == 5

    def test_positive_income_no_loss_pool_no_new_loss(self):
        income = (100.0, 200.0)
        schedule = build_tax_loss_carryforward_schedule(income, None)

        assert all(p.loss_used_keur == 0.0 for p in schedule.periods)
        assert all(p.new_loss_generated_keur == 0.0 for p in schedule.periods)
        assert all(p.taxable_income_after_losses_keur == p.taxable_income_before_losses_keur
                   for p in schedule.periods)
        assert schedule.ending_loss_carryforward_keur == 0.0

    def test_loss_pool_not_below_zero(self):
        income = (-50.0, 200.0)
        schedule = build_tax_loss_carryforward_schedule(income, None)

        assert all(p.closing_loss_carryforward_keur >= 0.0
                   for p in schedule.periods)
        assert schedule.ending_loss_carryforward_keur == 0.0

    def test_taxable_after_losses_not_negative(self):
        income = (-100.0, 50.0)
        schedule = build_tax_loss_carryforward_schedule(income, None)

        assert schedule.periods[1].taxable_income_after_losses_keur >= 0.0