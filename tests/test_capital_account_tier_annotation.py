"""Phase 7C-4 — Capital account tier annotation tests.

Comprehensive tests for TierAnnotation, TierAnnotatedCapitalAccountEntry,
TierAnnotatedSponsorCapitalAccount, and from_waterfall_allocation_result.
"""
from __future__ import annotations

import pytest

from domain.sponsor.sponsor_waterfall_tier import TierType, TierType
from domain.sponsor.sponsor_capital_account import CapitalAccountEntry
from domain.sponsor.capital_account_tier_annotation import (
    TierAnnotation,
    TierAnnotatedCapitalAccountEntry,
    TierAnnotatedSponsorCapitalAccount,
    from_waterfall_allocation_result,
)
from domain.sponsor.waterfall_allocation_result import (
    TierAllocationEntry,
    PeriodWaterfallResult,
    WaterfallAllocationResult,
)
from domain.sponsor.preferred_return_result import PreferredReturnResult


# ── Fixtures ─────────────────────────────────────────────────────────────────

def make_tier_annotation(**kwargs) -> TierAnnotation:
    defaults = dict(
        tier_index=0,
        tier_type=TierType.RETURN_OF_CAPITAL,
        sponsor_code="SPONSOR-1",
        allocated_amount_keur=1000.0,
        source_note="return_of_capital",
    )
    defaults.update(kwargs)
    return TierAnnotation(**defaults)


def make_base_entry(**kwargs) -> CapitalAccountEntry:
    defaults = dict(
        entry_type="distribution",
        period_index=0,
        amount_keur=500.0,
        running_balance_keur=-500.0,
        investor_id="SPONSOR-1",
        source="return_of_capital",
    )
    defaults.update(kwargs)
    return CapitalAccountEntry(**defaults)


def make_annotated_entry(**kwargs) -> TierAnnotatedCapitalAccountEntry:
    defaults = dict(
        entry=make_base_entry(),
        annotation=TierAnnotation(),
    )
    defaults.update(kwargs)
    return TierAnnotatedCapitalAccountEntry(**defaults)


def make_waterfall_result(periods=3, sponsor_codes=("SPONSOR-1", "LP-1")) -> WaterfallAllocationResult:
    """Build a simple waterfall result for testing."""
    period_results = []
    for p in range(periods):
        # Each sponsor gets 5000/len(sponsor_codes) per period
        per_sp = 5000.0 / len(sponsor_codes)
        tier_entries = [
            TierAllocationEntry(
                tier_index=0,
                tier_type=TierType.RETURN_OF_CAPITAL,
                available_cash_before_tier_keur=5000.0,
                allocated_amount_keur=5000.0,
                allocated_per_sponsor_keur=tuple((s, per_sp) for s in sponsor_codes),
                remaining_cash_after_tier_keur=0.0,
            ),
        ]
        period_results.append(
            PeriodWaterfallResult(
                period_index=p,
                available_cash_keur=5000.0,
                tier_entries=tuple(tier_entries),
                total_allocated_keur=5000.0,
                total_remaining_cash_keur=0.0,
                cumulative_distributions_by_sponsor_keur=tuple(
                    (s, (p + 1) * 2500.0) for s in sponsor_codes
                ),
            )
        )
    return WaterfallAllocationResult(
        investor_id="WATERFALL",
        period_results=tuple(period_results),
        total_allocated_keur=5000.0 * periods,
        total_distributions_by_sponsor_keur=tuple(
            (s, periods * 2500.0) for s in sponsor_codes
        ),
    )


# ── TierAnnotation tests ─────────────────────────────────────────────────────

class TestTierAnnotation:
    def test_empty(self):
        ann = TierAnnotation.empty()
        assert ann.tier_index is None
        assert ann.tier_type is None
        assert ann.sponsor_code is None
        assert ann.allocated_amount_keur is None
        assert ann.source_note == ""

    def test_full_construction(self):
        ann = make_tier_annotation()
        assert ann.tier_index == 0
        assert ann.tier_type == TierType.RETURN_OF_CAPITAL
        assert ann.sponsor_code == "SPONSOR-1"
        assert ann.allocated_amount_keur == 1000.0
        assert ann.source_note == "return_of_capital"

    def test_is_empty_true_for_empty(self):
        assert TierAnnotation.empty().is_empty is True

    def test_is_empty_false_when_filled(self):
        ann = make_tier_annotation()
        assert ann.is_empty is False

    def test_rejects_negative_tier_index(self):
        with pytest.raises(ValueError, match="tier_index must be >= 0"):
            TierAnnotation(tier_index=-1)

    def test_rejects_non_int_tier_index(self):
        with pytest.raises(TypeError, match="tier_index must be int or None"):
            TierAnnotation(tier_index=1.5)

    def test_rejects_invalid_tier_type(self):
        with pytest.raises(TypeError, match="tier_type must be TierType or None"):
            TierAnnotation(tier_type="RETURN_OF_CAPITAL")

    def test_rejects_nan_allocated_amount(self):
        with pytest.raises(ValueError, match="allocated_amount_keur must be finite"):
            TierAnnotation(allocated_amount_keur=float("nan"))

    def test_rejects_inf_allocated_amount(self):
        with pytest.raises(ValueError, match="allocated_amount_keur must be finite"):
            TierAnnotation(allocated_amount_keur=float("inf"))

    def test_rejects_negative_allocated_amount(self):
        with pytest.raises(ValueError, match="allocated_amount_keur must be >= 0"):
            TierAnnotation(allocated_amount_keur=-100.0)

    def test_rejects_non_float_allocated_amount(self):
        with pytest.raises(TypeError):
            TierAnnotation(allocated_amount_keur="1000")


# ── TierAnnotatedCapitalAccountEntry tests ───────────────────────────────────

class TestTierAnnotatedCapitalAccountEntry:
    def test_construction(self):
        base = make_base_entry()
        ann = TierAnnotation()
        e = TierAnnotatedCapitalAccountEntry(entry=base, annotation=ann)
        assert e.entry is base
        assert e.annotation is ann

    def test_default_annotation_is_empty(self):
        base = make_base_entry()
        e = TierAnnotatedCapitalAccountEntry(entry=base)
        assert e.annotation.is_empty is True

    def test_is_tier_annotated_true(self):
        ann = make_tier_annotation()
        base = make_base_entry()
        e = TierAnnotatedCapitalAccountEntry(entry=base, annotation=ann)
        assert e.is_tier_annotated is True

    def test_is_tier_annotated_false_for_empty(self):
        base = make_base_entry()
        e = TierAnnotatedCapitalAccountEntry(entry=base)
        assert e.is_tier_annotated is False

    def test_rejects_non_capital_account_entry(self):
        with pytest.raises(TypeError, match="entry must be CapitalAccountEntry"):
            TierAnnotatedCapitalAccountEntry(
                entry="not_an_entry",
                annotation=TierAnnotation(),
            )

    def test_rejects_non_tier_annotation(self):
        base = make_base_entry()
        with pytest.raises(TypeError, match="annotation must be TierAnnotation"):
            TierAnnotatedCapitalAccountEntry(
                entry=base,
                annotation={"tier_index": 0},
            )

    def test_frozen_immutable(self):
        ann = make_tier_annotation()
        base = make_base_entry()
        e = TierAnnotatedCapitalAccountEntry(entry=base, annotation=ann)
        with pytest.raises(Exception):
            e.annotation = TierAnnotation()  # type: ignore

    def test_frozen_base_entry_still_frozen(self):
        base = make_base_entry()
        ann = TierAnnotation()
        e = TierAnnotatedCapitalAccountEntry(entry=base, annotation=ann)
        with pytest.raises(Exception):
            e.entry.amount_keur = 999.0  # type: ignore

    def test_audit_note(self):
        e = TierAnnotatedCapitalAccountEntry(
            entry=make_base_entry(),
            annotation=TierAnnotation(),
        )
        assert "AUDIT-ONLY" in e.audit_note


# ── TierAnnotatedSponsorCapitalAccount tests ──────────────────────────────────

class TestTierAnnotatedSponsorCapitalAccount:
    def test_construction(self):
        base = make_base_entry(period_index=0, amount_keur=1000.0)
        ann = TierAnnotation(tier_index=0, tier_type=TierType.RETURN_OF_CAPITAL)
        ae = TierAnnotatedCapitalAccountEntry(entry=base, annotation=ann)
        cap = TierAnnotatedSponsorCapitalAccount(
            investor_id="SPONSOR-1",
            entity_code="HOLDCO",
            entries=(ae,),
            total_contributed_keur=0.0,
            total_distributions_keur=1000.0,
            net_contributed_keur=-1000.0,
        )
        assert cap.investor_id == "SPONSOR-1"
        assert cap.entity_code == "HOLDCO"
        assert len(cap.entries) == 1
        assert cap.entry_count == 1
        assert cap.final_balance_keur is None

    def test_rejects_empty_entries(self):
        with pytest.raises(ValueError, match="entries cannot be empty"):
            TierAnnotatedSponsorCapitalAccount(
                investor_id="SPONSOR-1",
                entity_code="HOLDCO",
                entries=(),
                total_contributed_keur=0.0,
                total_distributions_keur=0.0,
                net_contributed_keur=0.0,
            )

    def test_rejects_empty_investor_id(self):
        base = make_base_entry()
        ae = TierAnnotatedCapitalAccountEntry(entry=base)
        with pytest.raises(ValueError, match="investor_id must be non-empty"):
            TierAnnotatedSponsorCapitalAccount(
                investor_id="",
                entity_code="HOLDCO",
                entries=(ae,),
                total_contributed_keur=0.0,
                total_distributions_keur=0.0,
                net_contributed_keur=0.0,
            )

    def test_totals_reconciliation(self):
        base = make_base_entry(amount_keur=500.0)
        ae = TierAnnotatedCapitalAccountEntry(entry=base, annotation=TierAnnotation())
        with pytest.raises(ValueError, match="does not reconcile"):
            TierAnnotatedSponsorCapitalAccount(
                investor_id="SPONSOR-1",
                entity_code="HOLDCO",
                entries=(ae,),
                total_contributed_keur=0.0,
                total_distributions_keur=1000.0,  # wrong — should be 500
                net_contributed_keur=-500.0,
            )

    def test_negative_balance_allowed(self):
        """Negative final_balance_keur is allowed (return phase)."""
        base = make_base_entry(amount_keur=5000.0)
        ae = TierAnnotatedCapitalAccountEntry(entry=base, annotation=TierAnnotation())
        cap = TierAnnotatedSponsorCapitalAccount(
            investor_id="SPONSOR-1",
            entity_code="HOLDCO",
            entries=(ae,),
            total_contributed_keur=0.0,
            total_distributions_keur=5000.0,
            net_contributed_keur=-5000.0,
            final_balance_keur=-5000.0,
        )
        assert cap.final_balance_keur == -5000.0

    def test_frozen_immutable(self):
        base = make_base_entry(amount_keur=500.0)
        ae = TierAnnotatedCapitalAccountEntry(entry=base)
        cap = TierAnnotatedSponsorCapitalAccount(
            investor_id="SPONSOR-1",
            entity_code="HOLDCO",
            entries=(ae,),
            total_contributed_keur=0.0,
            total_distributions_keur=500.0,
            net_contributed_keur=-500.0,
        )
        with pytest.raises(Exception):
            cap.investor_id = "OTHER"  # type: ignore

    def test_audit_note(self):
        base = make_base_entry(amount_keur=500.0)
        ae = TierAnnotatedCapitalAccountEntry(entry=base)
        cap = TierAnnotatedSponsorCapitalAccount(
            investor_id="SPONSOR-1",
            entity_code="HOLDCO",
            entries=(ae,),
            total_contributed_keur=0.0,
            total_distributions_keur=500.0,
            net_contributed_keur=-500.0,
        )
        assert "AUDIT-ONLY" in cap.audit_note


# ── from_waterfall_allocation_result tests ───────────────────────────────────

class TestFromWaterfallAllocationResult:
    def test_basic_conversion(self):
        result = make_waterfall_result(periods=2, sponsor_codes=("SPONSOR-1",))
        cap = from_waterfall_allocation_result(result, "SPONSOR-1")
        assert cap.investor_id == "SPONSOR-1"
        assert cap.entity_code == "HOLDCO"
        assert cap.entry_count == 2  # one per period
        assert cap.total_distributions_keur == pytest.approx(10000.0)  # 5000 * 2

    def test_all_periods_included(self):
        result = make_waterfall_result(periods=3, sponsor_codes=("SPONSOR-1",))
        cap = from_waterfall_allocation_result(result, "SPONSOR-1")
        periods = [e.entry.period_index for e in cap.entries]
        assert periods == [0, 1, 2]

    def test_sorted_by_period_and_tier(self):
        result = make_waterfall_result(periods=2, sponsor_codes=("SPONSOR-1",))
        cap = from_waterfall_allocation_result(result, "SPONSOR-1")
        for i, e in enumerate(cap.entries):
            assert e.entry.period_index == i

    def test_annotation_carries_tier_info(self):
        result = make_waterfall_result(periods=1, sponsor_codes=("SPONSOR-1",))
        cap = from_waterfall_allocation_result(result, "SPONSOR-1")
        entry = cap.entries[0]
        assert entry.annotation.tier_index == 0
        assert entry.annotation.tier_type == TierType.RETURN_OF_CAPITAL
        assert entry.annotation.sponsor_code == "SPONSOR-1"
        assert entry.annotation.allocated_amount_keur == pytest.approx(5000.0)

    def test_annotated_entry_is_tier_annotated(self):
        result = make_waterfall_result(periods=1, sponsor_codes=("SPONSOR-1",))
        cap = from_waterfall_allocation_result(result, "SPONSOR-1")
        assert cap.entries[0].is_tier_annotated is True

    def test_no_allocation_skipped(self):
        """Sponsors with zero allocation in a period have no entry for that period."""
        result = make_waterfall_result(periods=2, sponsor_codes=("SPONSOR-1",))
        cap = from_waterfall_allocation_result(result, "SPONSOR-1")
        assert cap.entry_count == 2  # only periods where SPONSOR-1 got allocation

    def test_deterministic_ordering(self):
        result = make_waterfall_result(periods=3, sponsor_codes=("SPONSOR-1",))
        cap1 = from_waterfall_allocation_result(result, "SPONSOR-1")
        cap2 = from_waterfall_allocation_result(result, "SPONSOR-1")
        assert cap1.total_distributions_keur == cap2.total_distributions_keur
        for e1, e2 in zip(cap1.entries, cap2.entries):
            assert e1.entry.period_index == e2.entry.period_index
            assert e1.annotation.tier_index == e2.annotation.tier_index

    def test_rejects_non_waterfall_result(self):
        with pytest.raises(TypeError, match="must be WaterfallAllocationResult"):
            from_waterfall_allocation_result("not a result", "SPONSOR-1")

    def test_source_note_per_tier_type(self):
        from domain.sponsor.capital_account_tier_annotation import _source_note_for_tier
        assert _source_note_for_tier(TierType.RETURN_OF_CAPITAL) == "return_of_capital"
        assert _source_note_for_tier(TierType.PREFERRED_RETURN) == "preferred_return_allocation"
        assert _source_note_for_tier(TierType.GP_CATCH_UP) == "gp_catch_up_allocation"
        assert _source_note_for_tier(TierType.PROMOTE) == "promote_split"
        assert _source_note_for_tier(TierType.RESIDUAL) == "residual_split"

    def test_running_balance_negative(self):
        """Running balance is negative because distributions exceed contributions."""
        result = make_waterfall_result(periods=1, sponsor_codes=("SPONSOR-1",))
        cap = from_waterfall_allocation_result(result, "SPONSOR-1")
        assert cap.final_balance_keur < 0.0

    def test_result_not_mutated(self):
        """The input WaterfallAllocationResult is not mutated."""
        result = make_waterfall_result(periods=2, sponsor_codes=("SPONSOR-1",))
        original_str = str(result)
        from_waterfall_allocation_result(result, "SPONSOR-1")
        assert str(result) == original_str
