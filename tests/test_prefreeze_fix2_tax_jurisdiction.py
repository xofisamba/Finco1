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
    TaxJurisdictionDefaults,
    ProjectTaxOverrides,
    ResolvedTaxAssumptions,
    resolve_tax_assumptions,
    get_profile,
    list_profiles,
    HR_GENERIC_MVP_V1,
    BA_GENERIC_MVP_V1,
    RS_GENERIC_MVP_V1,
)

# Construct KUPI locally — it is NOT in the production registry.
_KUPI_LOCAL = TaxJurisdictionProfile(
    profile_id="KUPI-BA-source-unresolved-v1",
    country_iso="BA",
    subnational_jurisdiction_code=None,
    profile_version="1.0.0",
    effective_from=None,
    effective_to=None,
    source_references=(),
    provenance=PROVENANCE_TAX_JURISDICTION_SOURCE_UNRESOLVED,
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


def test_get_profile_kupi_not_in_production_registry():
    """D2: KUPI project identity must NOT be in the production registry — fail closed."""
    with pytest.raises(KeyError):
        get_profile("KUPI-BA-source-unresolved-v1")


# ---------------------------------------------------------------------------
# Test E: Registry lookup — unknown profile_id raises KeyError (fail closed)
# ---------------------------------------------------------------------------
def test_get_profile_unknown_raises_key_error():
    """E: get_profile raises KeyError for an unregistered profile_id — fail closed."""
    with pytest.raises(KeyError):
        get_profile("non-existent-profile-xyz")


# ---------------------------------------------------------------------------
# Test F: Production registry has NO project identity (governance requirement)
# ---------------------------------------------------------------------------
def test_production_registry_has_no_project_identity():
    """F: Production registry must contain only generic profiles — no project identity."""
    profiles = list_profiles()
    project_ids = [p.profile_id for p in profiles if any(
        token in p.profile_id.upper()
        for token in ("KUPI", "TUHO", "OBOROVO")
    )]
    assert project_ids == [], f"Project identity found in production registry: {project_ids}"


def test_production_registry_has_no_source_unresolved_profiles():
    """F2: Production registry must not contain TAX_JURISDICTION_SOURCE_UNRESOLVED profiles."""
    profiles = list_profiles()
    unresolved = [p.profile_id for p in profiles
                  if p.provenance == PROVENANCE_TAX_JURISDICTION_SOURCE_UNRESOLVED]
    assert unresolved == [], f"SOURCE_UNRESOLVED profiles in production registry: {unresolved}"


# ---------------------------------------------------------------------------
# Test G: BA generic MVP profile has country_iso="BA"
# ---------------------------------------------------------------------------
def test_ba_generic_mvp_country_iso_is_ba():
    """G1: BA generic MVP country_iso = 'BA' (Bosnia and Herzegovina)."""
    assert BA_GENERIC_MVP_V1.country_iso == "BA"


def test_ba_generic_mvp_subnational_is_none():
    """G2: BA generic MVP subnational_jurisdiction_code = None (generic, not entity-specific)."""
    assert BA_GENERIC_MVP_V1.subnational_jurisdiction_code is None


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
    assert BA_GENERIC_MVP_V1.subnational_jurisdiction_code is None
    assert BA_GENERIC_MVP_V1.subnational_jurisdiction_code != ""


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


def test_list_profiles_excludes_kupi():
    """J2: list_profiles must NOT include KUPI — project identity excluded from production registry."""
    profiles = list_profiles()
    kupi_ids = [p.profile_id for p in profiles if "KUPI" in p.profile_id]
    assert kupi_ids == [], f"KUPI found in production registry: {kupi_ids}"


# ---------------------------------------------------------------------------
# Test K: KUPI (local) has TAX_JURISDICTION_SOURCE_UNRESOLVED provenance
# ---------------------------------------------------------------------------
def test_kupi_local_provenance_is_source_unresolved():
    """K: Locally-constructed KUPI has TAX_JURISDICTION_SOURCE_UNRESOLVED provenance."""
    assert _KUPI_LOCAL.provenance == PROVENANCE_TAX_JURISDICTION_SOURCE_UNRESOLVED
    assert _KUPI_LOCAL.country_iso == "BA"
    assert _KUPI_LOCAL.subnational_jurisdiction_code is None
    assert _KUPI_LOCAL.source_references == ()


# ---------------------------------------------------------------------------
# Test L: Resolution chain — TaxJurisdictionDefaults / ProjectTaxOverrides
# ---------------------------------------------------------------------------
def test_tax_jurisdiction_defaults_are_frozen():
    """L1: TaxJurisdictionDefaults is a frozen dataclass."""
    d = TaxJurisdictionDefaults(corporate_tax_rate=0.18)
    with pytest.raises(Exception):
        d.corporate_tax_rate = 0.20  # type: ignore[misc]


def test_project_tax_overrides_are_frozen():
    """L2: ProjectTaxOverrides is a frozen dataclass."""
    o = ProjectTaxOverrides(corporate_tax_rate_override=0.20)
    with pytest.raises(Exception):
        o.corporate_tax_rate_override = 0.25  # type: ignore[misc]


def test_resolve_tax_assumptions_override_wins():
    """L3: Project override takes precedence over jurisdiction default."""
    profile = HR_GENERIC_MVP_V1
    defaults = TaxJurisdictionDefaults(corporate_tax_rate=0.18)
    overrides = ProjectTaxOverrides(corporate_tax_rate_override=0.20)
    resolved = resolve_tax_assumptions(profile, defaults, overrides)
    assert resolved.corporate_tax_rate == pytest.approx(0.20)
    assert resolved.corporate_tax_rate_source == "project_override"


def test_resolve_tax_assumptions_default_used_when_no_override():
    """L4: Jurisdiction default used when no project override."""
    profile = HR_GENERIC_MVP_V1
    defaults = TaxJurisdictionDefaults(corporate_tax_rate=0.18)
    overrides = ProjectTaxOverrides()
    resolved = resolve_tax_assumptions(profile, defaults, overrides)
    assert resolved.corporate_tax_rate == pytest.approx(0.18)
    assert resolved.corporate_tax_rate_source == PROVENANCE_GENERIC_MVP_POLICY


def test_resolve_tax_assumptions_none_when_not_resolved():
    """L5: None/0/False distinct — unresolved field stays None, not 0."""
    profile = HR_GENERIC_MVP_V1
    defaults = TaxJurisdictionDefaults()
    overrides = ProjectTaxOverrides()
    resolved = resolve_tax_assumptions(profile, defaults, overrides)
    assert resolved.corporate_tax_rate is None
    assert resolved.corporate_tax_rate_source == "NOT_RESOLVED"
