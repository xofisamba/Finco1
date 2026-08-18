"""financial_engine.tax.jurisdiction — TaxJurisdictionProfile contract (Fix 2 C3B3FIX2B).

Immutable, versioned contract for tax jurisdiction metadata. Separates the
jurisdiction identification layer from TaxParams field values.

Design constraints
------------------
- Catalog must NOT contain unsourced legal values.
- Workbook compatibility tax conventions must NOT become jurisdiction law.
- Source-unresolved jurisdictions carry TAX_JURISDICTION_SOURCE_UNRESOLVED until proven
  from a primary source (e.g. Bosnia and Herzegovina; exact subnational unknown).
- Provenance codes: SOURCE_PROVEN, GENERIC_MVP_POLICY,
  TAX_JURISDICTION_SOURCE_UNRESOLVED.
- No dynamic catalog pull per run. Resolved snapshots are frozen.
- None/0/False remain distinct across all fields.

TaxParams field classification (A/B/C/D)
-----------------------------------------
A — Jurisdiction default: values from country law or binding treaty.
B — Project override: explicitly set per project; not derivable from jurisdiction alone.
C — Model convention: Finco modelling choice (engine capability, not a legal rule).
D — Workbook compatibility: copied from source workbook for numerical parity;
    these are NOT jurisdiction law and must be isolated from A-class fields.

See docs/architecture/tax_field_inventory_fix2.md for the full table.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Provenance codes — classify how confident we are in each profile's values.
# ---------------------------------------------------------------------------
PROVENANCE_SOURCE_PROVEN = "SOURCE_PROVEN"
"""Values proven from primary source documents (law text, DTT text, workbook)."""

PROVENANCE_GENERIC_MVP_POLICY = "GENERIC_MVP_POLICY"
"""Reasonable MVP defaults not individually proven from primary law sources.
Used for Generic Solar/Wind placeholders where exact legal values are not needed
for the modelled computation to be correct."""

PROVENANCE_TAX_JURISDICTION_SOURCE_UNRESOLVED = "TAX_JURISDICTION_SOURCE_UNRESOLVED"
"""Jurisdiction identified but its subnational classification or specific legal
values have not been confirmed from a primary source. Values must not be used as
authoritative legal references. This is the status for projects in Bosnia and Herzegovina
where the exact subnational entity law is unresolved."""


@dataclass(frozen=True)
class TaxJurisdictionProfile:
    """Immutable, versioned tax jurisdiction identification record.

    This is the identification and provenance layer only. It does NOT store
    TaxParams field values; it classifies WHO set them and HOW confidently.

    Fields
    ------
    profile_id : str
        Unique, stable identifier for this profile (e.g. "HR-2024-v1").
    country_iso : str
        ISO 3166-1 alpha-2 country code (e.g. "HR", "BA", "RS").
    subnational_jurisdiction_code : str | None
        Subnational entity if applicable (e.g. Republika Srpska = "BA-SRP").
        None when the subnational classification is not resolved or not applicable.
    profile_version : str
        Semver-style version for this profile snapshot (e.g. "1.0.0").
    effective_from : str | None
        ISO date (YYYY-MM-DD) from which this profile applies, or None.
    effective_to : str | None
        ISO date (YYYY-MM-DD) until which this profile applies, or None = open end.
    source_references : tuple[str, ...]
        Cited primary sources that prove the A-class field values in this profile.
        Empty tuple when provenance is GENERIC_MVP_POLICY or SOURCE_UNRESOLVED.
    provenance : str
        One of the PROVENANCE_* constants defined in this module.
    """
    profile_id: str
    country_iso: str
    subnational_jurisdiction_code: str | None
    profile_version: str
    effective_from: str | None
    effective_to: str | None
    source_references: tuple[str, ...]
    provenance: str

    def __post_init__(self) -> None:
        valid_provenance = {
            PROVENANCE_SOURCE_PROVEN,
            PROVENANCE_GENERIC_MVP_POLICY,
            PROVENANCE_TAX_JURISDICTION_SOURCE_UNRESOLVED,
        }
        if self.provenance not in valid_provenance:
            raise ValueError(
                f"TaxJurisdictionProfile: unknown provenance {self.provenance!r}. "
                f"Must be one of {sorted(valid_provenance)!r}."
            )
        if not self.profile_id:
            raise ValueError("TaxJurisdictionProfile: profile_id must be non-empty.")
        if not self.country_iso:
            raise ValueError("TaxJurisdictionProfile: country_iso must be non-empty.")
        if not self.profile_version:
            raise ValueError("TaxJurisdictionProfile: profile_version must be non-empty.")


# ---------------------------------------------------------------------------
# Built-in profiles — Generic MVP policy only.
# These are Finco engine placeholders; they do NOT claim to represent country law.
# ---------------------------------------------------------------------------

HR_GENERIC_MVP_V1 = TaxJurisdictionProfile(
    profile_id="HR-generic-mvp-v1",
    country_iso="HR",
    subnational_jurisdiction_code=None,
    profile_version="1.0.0",
    effective_from=None,
    effective_to=None,
    source_references=(),
    provenance=PROVENANCE_GENERIC_MVP_POLICY,
)

BA_GENERIC_MVP_V1 = TaxJurisdictionProfile(
    profile_id="BA-generic-mvp-v1",
    country_iso="BA",
    subnational_jurisdiction_code=None,
    profile_version="1.0.0",
    effective_from=None,
    effective_to=None,
    source_references=(),
    provenance=PROVENANCE_GENERIC_MVP_POLICY,
)

RS_GENERIC_MVP_V1 = TaxJurisdictionProfile(
    profile_id="RS-generic-mvp-v1",
    country_iso="RS",
    subnational_jurisdiction_code=None,
    profile_version="1.0.0",
    effective_from=None,
    effective_to=None,
    source_references=(),
    provenance=PROVENANCE_GENERIC_MVP_POLICY,
)


# ---------------------------------------------------------------------------
# Profile registry — keyed by profile_id.
# No dynamic catalog pull. Entries are added here and frozen at import time.
# Source-unresolved profiles are NOT in the production registry.
# ---------------------------------------------------------------------------
_PROFILE_REGISTRY: dict[str, TaxJurisdictionProfile] = {
    p.profile_id: p
    for p in (
        HR_GENERIC_MVP_V1,
        BA_GENERIC_MVP_V1,
        RS_GENERIC_MVP_V1,
    )
}


# ---------------------------------------------------------------------------
# TaxJurisdictionDefaults — A-class fields (jurisdiction law / binding treaty).
# All fields are float | None = None. No invented values.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TaxJurisdictionDefaults:
    """A-class fields: values from country law or binding treaty.

    Only fields that are consumed by the current runtime tax engine (TaxParams)
    AND are genuinely jurisdiction-owned (set by jurisdiction law, not project
    choice) are retained here.

    All fields default to None. None means "not provided by this jurisdiction
    profile". None/0/False remain distinct — do not treat None as zero.

    Fields retained
    ---------------
    corporate_tax_rate : float | None
        Maps to TaxParams.corporate_rate. Country CIT rate from statute.

    FUTURE_COUNTRY_CATALOG_CAPABILITY
    ----------------------------------
    The following fields were removed because they do not map to current
    TaxParams fields consumed by the runtime tax engine. They are reserved
    for a future country catalog capability:
      - withholding_tax_rate_dividends  (future: maps to wht_sponsor_dividends)
      - withholding_tax_rate_interest   (future: maps to wht_sponsor_shl_interest)
      - vat_standard_rate               (future: maps to a VAT engine field)
    When the catalog capability is built, these fields should be re-introduced
    here alongside the TaxParams fields that consume them.
    """
    corporate_tax_rate: float | None = None


# ---------------------------------------------------------------------------
# ProjectTaxOverrides — B-class fields (explicitly set per project).
# None = not overridden (inherit from jurisdiction defaults or engine default).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ProjectTaxOverrides:
    """B-class fields: explicitly set per project; not derivable from jurisdiction alone.

    None means "not overridden — use the jurisdiction default or engine default".
    None/0/False remain distinct.
    """
    corporate_tax_rate_override: float | None = None
    withholding_tax_rate_dividends_override: float | None = None
    withholding_tax_rate_interest_override: float | None = None


# ---------------------------------------------------------------------------
# ResolvedTaxAssumptions — resolved value + provenance for each field.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResolvedTaxAssumptions:
    """Resolved tax assumptions with field-level provenance.

    Each field records the resolved value and its source (jurisdiction default,
    project override, or engine fallback). None/0/False remain distinct.
    """
    corporate_tax_rate: float | None
    corporate_tax_rate_source: str
    withholding_tax_rate_dividends: float | None
    withholding_tax_rate_dividends_source: str
    withholding_tax_rate_interest: float | None
    withholding_tax_rate_interest_source: str
    jurisdiction_profile: TaxJurisdictionProfile


def resolve_tax_assumptions(
    profile: TaxJurisdictionProfile,
    defaults: TaxJurisdictionDefaults,
    overrides: ProjectTaxOverrides,
) -> ResolvedTaxAssumptions:
    """Resolve tax assumptions from jurisdiction defaults and project overrides.

    B-class overrides take precedence over A-class jurisdiction defaults.
    None/0/False remain distinct — None means "not resolved", not zero.

    Parameters
    ----------
    profile : TaxJurisdictionProfile
        The jurisdiction profile providing identification and provenance.
    defaults : TaxJurisdictionDefaults
        A-class field values from country law or binding treaty.
    overrides : ProjectTaxOverrides
        B-class project-level overrides. None = not overridden.

    Returns
    -------
    ResolvedTaxAssumptions
        Resolved values with field-level provenance labels.
    """
    def _resolve(
        override: float | None,
        default: float | None,
        override_source: str,
        default_source: str,
    ) -> tuple[float | None, str]:
        if override is not None:
            return override, override_source
        if default is not None:
            return default, default_source
        return None, "NOT_RESOLVED"

    corp_tax, corp_tax_src = _resolve(
        overrides.corporate_tax_rate_override,
        defaults.corporate_tax_rate,
        "project_override",
        profile.provenance,
    )
    # WHT fields: TaxJurisdictionDefaults no longer carries WHT jurisdiction defaults
    # (FUTURE_COUNTRY_CATALOG_CAPABILITY). Resolution falls back to project override
    # or NOT_RESOLVED.
    wht_div, wht_div_src = _resolve(
        overrides.withholding_tax_rate_dividends_override,
        None,
        "project_override",
        profile.provenance,
    )
    wht_int, wht_int_src = _resolve(
        overrides.withholding_tax_rate_interest_override,
        None,
        "project_override",
        profile.provenance,
    )
    return ResolvedTaxAssumptions(
        corporate_tax_rate=corp_tax,
        corporate_tax_rate_source=corp_tax_src,
        withholding_tax_rate_dividends=wht_div,
        withholding_tax_rate_dividends_source=wht_div_src,
        withholding_tax_rate_interest=wht_int,
        withholding_tax_rate_interest_source=wht_int_src,
        jurisdiction_profile=profile,
    )


def get_profile(profile_id: str) -> TaxJurisdictionProfile:
    """Return the named profile from the built-in registry.

    Raises
    ------
    KeyError
        If the profile_id is not registered. Fail closed — never return an
        unrecognised profile silently.
    """
    try:
        return _PROFILE_REGISTRY[profile_id]
    except KeyError:
        raise KeyError(
            f"TaxJurisdictionProfile {profile_id!r} not found in registry. "
            f"Registered profiles: {sorted(_PROFILE_REGISTRY)!r}. "
            "Add a new profile entry to financial_engine.tax.jurisdiction rather than "
            "using an unsourced ad-hoc profile."
        ) from None


def list_profiles() -> tuple[TaxJurisdictionProfile, ...]:
    """Return all registered profiles as an immutable tuple."""
    return tuple(_PROFILE_REGISTRY.values())
