"""Pre-Freeze Fix 2 Part B — Tax Jurisdiction Foundation acceptance tests.

Tests A–J as specified in C3B3FIX2B. Covers:
  A: TaxJurisdictionProfile is immutable (frozen dataclass)
  B: Profile validation — empty profile_id raises ValueError
  C: Profile validation — invalid provenance raises ValueError
  D: Registry lookup — get_profile returns correct record
  E: Registry lookup — unknown profile_id raises KeyError (fail closed)
  F: KUPI profile has TAX_JURISDICTION_SOURCE_UNRESOLVED provenance
  G: KUPI profile has country_iso="BA" and subnational_jurisdiction_code=None
  H: Generic MVP profiles have GENERIC_MVP_POLICY provenance
  I: None/0/False distinctness — subnational_jurisdiction_code=None ≠ empty string
  J: list_profiles returns all registered profiles without duplication

Governance constraints enforced:
  - KUPI = TAX_JURISDICTION_SOURCE_UNRESOLVED (Bosnia and Herzegovina, subnational unresolved)
  - Workbook compat conventions must NOT become jurisdiction law
  - Tax field classification table (A/B/C/D) is in docs/architecture/tax_field_inventory_fix2.md
"""
from __future__ import annotations

import pytest

from financial_engine.tax.jurisdiction import (
    PROVENANCE_GENERIC_MVP_POLICY,
    PROVENANCE_SOURCE_PROVEN,
    PROVENANCE_TAX_JURISDICTION_SOURCE_UNRESOLVED,
    TaxJurisdictionProfile,
    get_profile,
    list_profiles,
    KUPI_BA_SOURCE_UNRESOLVED_V1,
    HR_GENERIC_MVP_V1,
    BA_GENERIC_MVP_V1,
    RS_GENERIC_MVP_V1,
)


# ---------------------------------------------------------------------------
# Test A: TaxJurisdictionProfile is immutable
# ---------------------------------------------------------------------------
def test_tax_jurisdiction_profile_is_frozen():
    """A: TaxJurisdictionProfile is a frozen dataclass — direct attribute assignment raises."""
    profile = HR_GENERIC_MVP_V1
    with pytest.raises(Exception):  # dataclasses.FrozenInstanceError or AttributeError
        profile.country_iso = "XX"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Test B: Validation — empty profile_id raises ValueError
# ---------------------------------------------------------------------------
def test_profile_empty_profile_id_raises():
    """B: TaxJurisdictionProfile with empty profile_id raises ValueError."""
    with pytest.raises(ValueError, match="profile_id"):
        TaxJurisdictionProfile(
            profile_id="",
            country_iso="HR",
            subnational_jurisdiction_code=None,
            profile_version="1.0.0",
            effective_from=None,
            effective_to=None,
            source_references=(),
            provenance=PROVENANCE_GENERIC_MVP_POLICY,
        )


# ---------------------------------------------------------------------------
# Test C: Validation — invalid provenance raises ValueError
# ---------------------------------------------------------------------------
def test_profile_invalid_provenance_raises():
    """C: TaxJurisdictionProfile with an unrecognised provenance raises ValueError."""
    with pytest.raises(ValueError, match="provenance"):
        TaxJurisdictionProfile(
            profile_id="test-invalid",
            country_iso="HR",
            subnational_jurisdiction_code=None,
            profile_version="1.0.0",
            effective_from=None,
            effective_to=None,
            source_references=(),
            provenance="MADE_UP_PROVENANCE",
        )


# ---------------------------------------------------------------------------
# Test D: Registry lookup — get_profile returns the correct record
# ---------------------------------------------------------------------------
def test_get_profile_returns_correct_record():
    """D: get_profile('HR-generic-mvp-v1') returns the HR generic MVP profile."""
    profile = get_profile("HR-generic-mvp-v1")
    assert profile.profile_id == "HR-generic-mvp-v1"
    assert profile.country_iso == "HR"
    assert profile.provenance == PROVENANCE_GENERIC_MVP_POLICY


def test_get_profile_kupi_returns_correct_record():
    """D2: get_profile('KUPI-BA-source-unresolved-v1') returns KUPI profile."""
    profile = get_profile("KUPI-BA-source-unresolved-v1")
    assert profile is KUPI_BA_SOURCE_UNRESOLVED_V1


# ---------------------------------------------------------------------------
# Test E: Registry lookup — unknown profile_id raises KeyError (fail closed)
# ---------------------------------------------------------------------------
def test_get_profile_unknown_raises_key_error():
    """E: get_profile raises KeyError for an unregistered profile_id — fail closed."""
    with pytest.raises(KeyError):
        get_profile("non-existent-profile-xyz")


# ---------------------------------------------------------------------------
# Test F: KUPI has TAX_JURISDICTION_SOURCE_UNRESOLVED provenance
# ---------------------------------------------------------------------------
def test_kupi_profile_provenance_is_source_unresolved():
    """F: KUPI profile provenance = TAX_JURISDICTION_SOURCE_UNRESOLVED (governance requirement)."""
    assert KUPI_BA_SOURCE_UNRESOLVED_V1.provenance == PROVENANCE_TAX_JURISDICTION_SOURCE_UNRESOLVED


def test_kupi_profile_source_references_are_empty():
    """F2: KUPI source_references is empty — no primary source citation exists yet."""
    assert KUPI_BA_SOURCE_UNRESOLVED_V1.source_references == ()


# ---------------------------------------------------------------------------
# Test G: KUPI has country_iso="BA" and subnational_jurisdiction_code=None
# ---------------------------------------------------------------------------
def test_kupi_country_iso_is_ba():
    """G1: KUPI country_iso = 'BA' (Bosnia and Herzegovina)."""
    assert KUPI_BA_SOURCE_UNRESOLVED_V1.country_iso == "BA"


def test_kupi_subnational_is_none():
    """G2: KUPI subnational_jurisdiction_code = None (exact entity unresolved)."""
    assert KUPI_BA_SOURCE_UNRESOLVED_V1.subnational_jurisdiction_code is None


# ---------------------------------------------------------------------------
# Test H: Generic MVP profiles have GENERIC_MVP_POLICY provenance
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("profile", [HR_GENERIC_MVP_V1, BA_GENERIC_MVP_V1, RS_GENERIC_MVP_V1])
def test_generic_mvp_profiles_have_correct_provenance(profile):
    """H: All generic MVP profiles carry GENERIC_MVP_POLICY provenance."""
    assert profile.provenance == PROVENANCE_GENERIC_MVP_POLICY


# ---------------------------------------------------------------------------
# Test I: None/0/False distinctness
# ---------------------------------------------------------------------------
def test_none_subnational_is_not_empty_string():
    """I: subnational_jurisdiction_code=None is distinct from '' — None/0/False are separate."""
    assert KUPI_BA_SOURCE_UNRESOLVED_V1.subnational_jurisdiction_code is None
    assert KUPI_BA_SOURCE_UNRESOLVED_V1.subnational_jurisdiction_code != ""


def test_source_proven_profile_can_have_nonempty_source_references():
    """I2: A SOURCE_PROVEN profile can have non-empty source_references (None ≠ empty tuple)."""
    proven = TaxJurisdictionProfile(
        profile_id="test-proven",
        country_iso="HR",
        subnational_jurisdiction_code=None,
        profile_version="1.0.0",
        effective_from="2024-01-01",
        effective_to=None,
        source_references=("Official Gazette HR 2024", "DTT HR-AT 2007"),
        provenance=PROVENANCE_SOURCE_PROVEN,
    )
    assert len(proven.source_references) == 2
    assert proven.effective_to is None  # open-ended — distinct from ""


# ---------------------------------------------------------------------------
# Test J: list_profiles returns all registered profiles without duplication
# ---------------------------------------------------------------------------
def test_list_profiles_no_duplicates():
    """J: list_profiles returns each profile exactly once (no duplicates by profile_id)."""
    profiles = list_profiles()
    ids = [p.profile_id for p in profiles]
    assert len(ids) == len(set(ids)), "Duplicate profile_ids in registry"


def test_list_profiles_includes_kupi():
    """J2: list_profiles includes the KUPI unresolved profile."""
    profiles = list_profiles()
    kupi_ids = [p.profile_id for p in profiles if "KUPI" in p.profile_id]
    assert len(kupi_ids) == 1
    assert kupi_ids[0] == "KUPI-BA-source-unresolved-v1"
