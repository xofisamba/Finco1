"""Phase 7C-1 — Sponsor waterfall tier schema tests.

Schema validation tests for SponsorWaterfallTier and SponsorShare.
Deterministic. No mocking. No allocation logic.
"""
from __future__ import annotations

import math

import pytest

from domain.sponsor.sponsor_waterfall_tier import (
    TierType,
    CompoundingConvention,
    SponsorShare,
    SponsorWaterfallTier,
    WaterfallTierValidationResult,
)


# ── SponsorShare tests ─────────────────────────────────────────────────────────

class TestSponsorShareSchema:
    def test_valid_construction(self):
        s = SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.80)
        assert s.sponsor_code == "SPONSOR-1"
        assert s.allocation_percentage == 0.80
        assert s.allocation_percent == 0.80

    def test_zero_allocation_is_valid(self):
        s = SponsorShare(sponsor_code="GP-1", allocation_percentage=0.0)
        assert s.allocation_percentage == 0.0

    def test_full_allocation_is_valid(self):
        s = SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0)
        assert s.allocation_percentage == 1.0

    def test_rejects_empty_sponsor_code(self):
        with pytest.raises(ValueError, match="non-empty string"):
            SponsorShare(sponsor_code="", allocation_percentage=0.5)

    def test_rejects_whitespace_sponsor_code(self):
        with pytest.raises(ValueError, match="non-empty string"):
            SponsorShare(sponsor_code="   ", allocation_percentage=0.5)

    def test_rejects_negative_allocation(self):
        with pytest.raises(ValueError, match="must be >= 0"):
            SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=-0.1)

    def test_rejects_nan(self):
        with pytest.raises(ValueError, match="must be finite"):
            SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=float("nan"))

    def test_rejects_inf(self):
        with pytest.raises(ValueError, match="must be finite"):
            SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=float("inf"))

    def test_rejects_non_float_code(self):
        with pytest.raises(ValueError, match="non-empty string"):
            SponsorShare(sponsor_code=123, allocation_percentage=0.5)


class TestSponsorShareImmutability:
    def test_is_frozen(self):
        s = SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.8)
        with pytest.raises(Exception):  # FrozenInstanceError
            s.sponsor_code = "GP-1"

    def test_repeated_construction_identical(self):
        s1 = SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.8)
        s2 = SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.8)
        assert s1 == s2
        assert hash(s1) == hash(s2)


# ── SponsorWaterfallTier basic construction ───────────────────────────────────

class TestSponsorWaterfallTierBasic:
    def test_minimal_valid_tier(self):
        """GP_CATCH_UP tier requires no hurdle or compounding."""
        t = SponsorWaterfallTier(
            tier_index=0,
            tier_type=TierType.GP_CATCH_UP,
            sponsor_shares=(
                SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
            ),
            description="GP catch-up tier",
        )
        assert t.tier_index == 0
        assert t.tier_type == TierType.GP_CATCH_UP
        assert t.hurdle_rate_pa is None
        assert t.compounding_convention is None

    def test_pref_return_tier_requires_hurdle_and_compounding(self):
        t = SponsorWaterfallTier(
            tier_index=1,
            tier_type=TierType.PREFERRED_RETURN,
            sponsor_shares=(
                SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
            ),
            description="Sponsor preferred return",
            hurdle_rate_pa=0.08,
            compounding_convention=CompoundingConvention.ANNUAL,
        )
        assert t.hurdle_rate_pa == 0.08
        assert t.compounding_convention == CompoundingConvention.ANNUAL

    def test_return_of_capital_tier_rejects_hurdle(self):
        with pytest.raises(ValueError, match="hurdle_rate_pa is forbidden for RETURN_OF_CAPITAL"):
            SponsorWaterfallTier(
                tier_index=0,
                tier_type=TierType.RETURN_OF_CAPITAL,
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
                ),
                description="Return of capital",
                hurdle_rate_pa=0.0,
            )

    def test_return_of_capital_tier_rejects_compounding(self):
        with pytest.raises(ValueError, match="compounding_convention is forbidden for RETURN_OF_CAPITAL"):
            SponsorWaterfallTier(
                tier_index=0,
                tier_type=TierType.RETURN_OF_CAPITAL,
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
                ),
                description="Return of capital",
                compounding_convention=CompoundingConvention.ANNUAL,
            )

    def test_preferred_return_tier_requires_hurdle(self):
        with pytest.raises(ValueError, match="hurdle_rate_pa is required for PREFERRED_RETURN"):
            SponsorWaterfallTier(
                tier_index=1,
                tier_type=TierType.PREFERRED_RETURN,
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
                ),
                description="Pref",
                compounding_convention=CompoundingConvention.ANNUAL,
            )

    def test_preferred_return_tier_requires_compounding(self):
        with pytest.raises(ValueError, match="compounding_convention is required for PREFERRED_RETURN"):
            SponsorWaterfallTier(
                tier_index=1,
                tier_type=TierType.PREFERRED_RETURN,
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
                ),
                description="Pref",
                hurdle_rate_pa=0.08,
            )

    def test_gp_catch_up_rejects_hurdle(self):
        with pytest.raises(ValueError, match="hurdle_rate_pa is forbidden for GP_CATCH_UP"):
            SponsorWaterfallTier(
                tier_index=2,
                tier_type=TierType.GP_CATCH_UP,
                sponsor_shares=(
                    SponsorShare(sponsor_code="GP-1", allocation_percentage=1.0),
                ),
                description="GP catch-up",
                hurdle_rate_pa=0.08,
            )

    def test_promote_rejects_compounding(self):
        with pytest.raises(ValueError, match="compounding_convention is forbidden for PROMOTE"):
            SponsorWaterfallTier(
                tier_index=3,
                tier_type=TierType.PROMOTE,
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.80),
                    SponsorShare(sponsor_code="GP-1", allocation_percentage=0.20),
                ),
                description="Promote split",
                compounding_convention=CompoundingConvention.ANNUAL,
            )

    def test_hurdle_rate_must_be_in_range(self):
        with pytest.raises(ValueError, match="must be in \\(0, 1\\)"):
            SponsorWaterfallTier(
                tier_index=1,
                tier_type=TierType.PREFERRED_RETURN,
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
                ),
                description="Pref",
                hurdle_rate_pa=1.5,  # out of range
                compounding_convention=CompoundingConvention.ANNUAL,
            )

    def test_hurdle_rate_zero_rejected(self):
        with pytest.raises(ValueError, match="must be in \\(0, 1\\)"):
            SponsorWaterfallTier(
                tier_index=1,
                tier_type=TierType.PREFERRED_RETURN,
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
                ),
                description="Pref",
                hurdle_rate_pa=0.0,
                compounding_convention=CompoundingConvention.ANNUAL,
            )


# ── Percentage sum validation ─────────────────────────────────────────────────

class TestPercentageSumValidation:
    def test_sum_must_be_1_0(self):
        with pytest.raises(ValueError, match="must sum to 1.0"):
            SponsorWaterfallTier(
                tier_index=0,
                tier_type=TierType.RESIDUAL,
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.50),
                    SponsorShare(sponsor_code="GP-1", allocation_percentage=0.40),
                ),
                description="Bad split",
            )

    def test_sum_tolerance_1e8(self):
        """Sum = 0.90 is rejected (not 1.0)."""
        with pytest.raises(ValueError, match="must sum to 1.0"):
            SponsorWaterfallTier(
                tier_index=0,
                tier_type=TierType.RESIDUAL,
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.50),
                    SponsorShare(sponsor_code="GP-1", allocation_percentage=0.40),
                    # sum = 0.90, not 1.0 → must fail
                ),
                description="Bad split",
            )

    def test_exact_sum_passes(self):
        """0.5 + 0.5 = 1.0 exactly should pass."""
        t = SponsorWaterfallTier(
            tier_index=0,
            tier_type=TierType.RESIDUAL,
            sponsor_shares=(
                SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.5),
                SponsorShare(sponsor_code="GP-1", allocation_percentage=0.5),
            ),
            description="Sum = 1.0 exactly",
        )
        assert t is not None

    def test_single_100pct_share(self):
        """Single sponsor with 100% is valid."""
        t = SponsorWaterfallTier(
            tier_index=0,
            tier_type=TierType.RESIDUAL,
            sponsor_shares=(
                SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
            ),
            description="Single sponsor",
        )
        assert t is not None

    def test_three_way_split(self):
        """Three-way split summing to 1.0 is valid."""
        t = SponsorWaterfallTier(
            tier_index=0,
            tier_type=TierType.RESIDUAL,
            sponsor_shares=(
                SponsorShare(sponsor_code="LP-1", allocation_percentage=0.60),
                SponsorShare(sponsor_code="GP-1", allocation_percentage=0.30),
                SponsorShare(sponsor_code="ADVISOR-1", allocation_percentage=0.10),
            ),
            description="Three-way split",
        )
        assert t is not None


# ── Duplicate sponsor detection ───────────────────────────────────────────────

class TestDuplicateSponsorDetection:
    def test_rejects_duplicate_codes(self):
        with pytest.raises(ValueError, match="Duplicate sponsor_code"):
            SponsorWaterfallTier(
                tier_index=0,
                tier_type=TierType.RESIDUAL,
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.60),
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.40),
                ),
                description="Duplicate sponsor",
            )

    def test_case_sensitive_duplicates(self):
        """SPONSOR-1 and sponsor-1 are treated as distinct."""
        t = SponsorWaterfallTier(
            tier_index=0,
            tier_type=TierType.RESIDUAL,
            sponsor_shares=(
                SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.60),
                SponsorShare(sponsor_code="sponsor-1", allocation_percentage=0.40),
            ),
            description="Case-different codes",
        )
        assert t is not None


# ── Deterministic ordering ─────────────────────────────────────────────────────

class TestDeterministicOrdering:
    def test_sorted_shares_property(self):
        t = SponsorWaterfallTier(
            tier_index=0,
            tier_type=TierType.RESIDUAL,
            sponsor_shares=(
                SponsorShare(sponsor_code="GP-1", allocation_percentage=0.20),
                SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.80),
            ),
            description="Unsorted in construction",
        )
        sorted_codes = [s.sponsor_code for s in t.sorted_shares]
        assert sorted_codes == ["GP-1", "SPONSOR-1"]  # alphabetical

    def test_share_for_returns_correct(self):
        t = SponsorWaterfallTier(
            tier_index=0,
            tier_type=TierType.RESIDUAL,
            sponsor_shares=(
                SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.80),
                SponsorShare(sponsor_code="GP-1", allocation_percentage=0.20),
            ),
            description="Test share_for",
        )
        assert t.share_for("SPONSOR-1") == 0.80
        assert t.share_for("GP-1") == 0.20
        assert t.share_for("UNKNOWN") == 0.0

    def test_duplicate_construction_identical(self):
        def make_tier():
            return SponsorWaterfallTier(
                tier_index=0,
                tier_type=TierType.RESIDUAL,
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.80),
                    SponsorShare(sponsor_code="GP-1", allocation_percentage=0.20),
                ),
                description="Test",
            )
        t1 = make_tier()
        t2 = make_tier()
        assert t1 == t2
        assert hash(t1) == hash(t2)


# ── Empty / invalid inputs ────────────────────────────────────────────────────

class TestInvalidInputs:
    def test_empty_shares_rejected(self):
        with pytest.raises(ValueError, match="sponsor_shares cannot be empty"):
            SponsorWaterfallTier(
                tier_index=0,
                tier_type=TierType.RESIDUAL,
                sponsor_shares=(),
                description="Empty",
            )

    def test_negative_tier_index_rejected(self):
        with pytest.raises(ValueError, match="tier_index must be >= 0"):
            SponsorWaterfallTier(
                tier_index=-1,
                tier_type=TierType.RESIDUAL,
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
                ),
                description="Negative index",
            )

    def test_non_int_tier_index_rejected(self):
        with pytest.raises(TypeError, match="tier_index must be int"):
            SponsorWaterfallTier(
                tier_index=1.5,
                tier_type=TierType.RESIDUAL,
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
                ),
                description="Float index",
            )

    def test_non_tier_type_rejected(self):
        with pytest.raises(TypeError, match="tier_type must be TierType"):
            SponsorWaterfallTier(
                tier_index=0,
                tier_type="PREFERRED_RETURN",  # str, not TierType
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
                ),
                description="String tier",
            )

    def test_empty_description_rejected(self):
        with pytest.raises(ValueError, match="description must be a non-empty string"):
            SponsorWaterfallTier(
                tier_index=0,
                tier_type=TierType.RESIDUAL,
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
                ),
                description="   ",
            )

    def test_non_string_description_rejected(self):
        with pytest.raises(ValueError, match="description must be a non-empty string"):
            SponsorWaterfallTier(
                tier_index=0,
                tier_type=TierType.RESIDUAL,
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
                ),
                description=123,
            )


# ── Immutability tests ────────────────────────────────────────────────────────

class TestWaterfallTierImmutability:
    def test_tier_is_frozen(self):
        t = SponsorWaterfallTier(
            tier_index=0,
            tier_type=TierType.RESIDUAL,
            sponsor_shares=(
                SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
            ),
            description="Frozen test",
        )
        with pytest.raises(Exception):
            t.tier_index = 5

    def test_shares_tuple_immutable(self):
        share = SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0)
        with pytest.raises(Exception):
            share.allocation_percentage = 0.5


# ── NaN / Inf rejection ───────────────────────────────────────────────────────

class TestNaNInfRejection:
    def test_nan_hurdle_rejected(self):
        with pytest.raises(ValueError, match="must be finite"):
            SponsorWaterfallTier(
                tier_index=1,
                tier_type=TierType.PREFERRED_RETURN,
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
                ),
                description="NaN pref",
                hurdle_rate_pa=float("nan"),
                compounding_convention=CompoundingConvention.ANNUAL,
            )

    def test_inf_hurdle_rejected(self):
        with pytest.raises(ValueError, match="must be finite"):
            SponsorWaterfallTier(
                tier_index=1,
                tier_type=TierType.PREFERRED_RETURN,
                sponsor_shares=(
                    SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
                ),
                description="Inf pref",
                hurdle_rate_pa=float("inf"),
                compounding_convention=CompoundingConvention.ANNUAL,
            )


# ── Notes normalization ───────────────────────────────────────────────────────

class TestNotesNormalization:
    def test_string_note_normalized_to_tuple(self):
        t = SponsorWaterfallTier(
            tier_index=0,
            tier_type=TierType.RESIDUAL,
            sponsor_shares=(
                SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
            ),
            description="Test",
            notes="single note",
        )
        assert t.notes == ("single note",)

    def test_list_notes_normalized_to_tuple(self):
        t = SponsorWaterfallTier(
            tier_index=0,
            tier_type=TierType.RESIDUAL,
            sponsor_shares=(
                SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
            ),
            description="Test",
            notes=["note 1", "note 2"],
        )
        assert t.notes == ("note 1", "note 2")
        assert isinstance(t.notes, tuple)


# ── TierType and CompoundingConvention ───────────────────────────────────────

class TestEnums:
    def test_tier_type_values(self):
        assert TierType.RETURN_OF_CAPITAL.value == "RETURN_OF_CAPITAL"
        assert TierType.PREFERRED_RETURN.value == "PREFERRED_RETURN"
        assert TierType.GP_CATCH_UP.value == "GP_CATCH_UP"
        assert TierType.PROMOTE.value == "PROMOTE"
        assert TierType.RESIDUAL.value == "RESIDUAL"

    def test_compounding_convention_values(self):
        assert CompoundingConvention.ANNUAL.value == "ANNUAL"
        assert CompoundingConvention.SIMPLE.value == "SIMPLE"
        assert CompoundingConvention.SEMIANNUAL.value == "SEMIANNUAL"


# ── WaterfallTierValidationResult ─────────────────────────────────────────────

class TestWaterfallTierValidationResult:
    def test_ok_result(self):
        r = WaterfallTierValidationResult.ok()
        assert r.valid is True
        assert r.errors == ()
        assert r.warnings == ()
        assert bool(r) is True

    def test_error_result(self):
        r = WaterfallTierValidationResult.error("something wrong")
        assert r.valid is False
        assert r.errors == ("something wrong",)
        assert bool(r) is False

    def test_from_tier_valid(self):
        t = SponsorWaterfallTier(
            tier_index=0,
            tier_type=TierType.RESIDUAL,
            sponsor_shares=(
                SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
            ),
            description="Valid tier",
        )
        r = WaterfallTierValidationResult.from_tier(t)
        assert r.valid is True

    def test_share_tuple_persists_after_construction(self):
        """Ensure sponsor_shares is stored as tuple, not list."""
        shares = (
            SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.80),
            SponsorShare(sponsor_code="GP-1", allocation_percentage=0.20),
        )
        t = SponsorWaterfallTier(
            tier_index=0,
            tier_type=TierType.RESIDUAL,
            sponsor_shares=shares,
            description="Tuple check",
        )
        assert isinstance(t.sponsor_shares, tuple)
        assert t.sponsor_shares == shares


# ── Serialization-friendly tests ───────────────────────────────────────────────

class TestSerializationFriendly:
    def test_all_scalars_are_json_serializable(self):
        share = SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.80)
        assert isinstance(share.sponsor_code, str)
        assert isinstance(share.allocation_percentage, float)

        t = SponsorWaterfallTier(
            tier_index=0,
            tier_type=TierType.PREFERRED_RETURN,
            sponsor_shares=(
                SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=0.80),
                SponsorShare(sponsor_code="GP-1", allocation_percentage=0.20),
            ),
            description="Serialization test",
            hurdle_rate_pa=0.08,
            compounding_convention=CompoundingConvention.ANNUAL,
        )
        # All fields are JSON-serializable primitives
        assert isinstance(t.tier_index, int)
        assert isinstance(t.tier_type, TierType)
        assert isinstance(t.description, str)
        assert isinstance(t.hurdle_rate_pa, float)
        assert isinstance(t.compounding_convention, CompoundingConvention)
        assert isinstance(t.audit_note, str)
        assert isinstance(t.notes, tuple)
        assert isinstance(t.sponsor_shares, tuple)

    def test_metadata_tuple_structure(self):
        """Notes stored as tuple of strings, not something else."""
        t = SponsorWaterfallTier(
            tier_index=0,
            tier_type=TierType.RESIDUAL,
            sponsor_shares=(
                SponsorShare(sponsor_code="SPONSOR-1", allocation_percentage=1.0),
            ),
            description="Metadata test",
            notes=("audit note 1", "audit note 2"),
        )
        for note in t.notes:
            assert isinstance(note, str)