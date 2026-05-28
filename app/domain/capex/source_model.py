"""
CAPEX Source Model — isolated schema stubs.

This module defines the CAPEX source model and input schema design.
It is completely isolated from runtime model code — NOT imported by any
runtime calculation, construction, returns, or debt module.

Purpose: Provide type-safe schema definitions for CAPEX input wiring
(Phase 21E and beyond).

NOTE: Do not import this module from any runtime-capable module.
      It exists only for design/type-safe schema documentation.
"""

from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Source type classification — where does this line's value come from?
# ─────────────────────────────────────────────────────────────────────────────

class CapexSourceType:
    """Origin/source classification for a CAPEX line value."""

    EXCEL_REFERENCE = "excel_reference"
    # Taken from the Excel CapEx sheet reference.
    # Not present in the app runtime CapexStructure.

    APP_INPUT = "app_input"
    # User-specified or app-template value.
    # May or may not be wired to runtime.

    RUNTIME_COMPUTED = "runtime_computed"
    # Derived by model calculations (IDC, bank fees, commitment fees).
    # Not user-editable directly.

    USER_OVERRIDE = "user_override"
    # User-edited override that replaces the prior computed or reference value.

    IMPORTED_SCHEDULE = "imported_schedule"
    # From an imported file or schedule (e.g., project rights payment schedule).

    STATIC_REFERENCE = "static_reference"
    # Hard-coded reference value, not editable by user.


# ─────────────────────────────────────────────────────────────────────────────
# Scope classification — what does this amount mean temporally/structurally?
# ─────────────────────────────────────────────────────────────────────────────

class CapexScope:
    """Temporal/structural scope classification for a CAPEX line amount."""

    AGGREGATE_TOTAL = "aggregate_total"
    # Total across all periods/batches (e.g., total EPC contract over construction)

    COMPONENT = "component"
    # Sub-component of a larger category (a piece of the full picture)

    PAYMENT_BATCH = "payment_batch"
    # One payment in a multi-batch schedule (e.g., one of 4 EPC batches)

    MONTHLY_SCHEDULE = "monthly_schedule"
    # Monthly M1-M18 distribution of a CAPEX total (timing only)

    FEE_ONLY = "fee_only"
    # Fee or prerequisite only (e.g., GPA administrative fee), not the full scope

    PROJECT_RIGHTS = "project_rights"
    # Acquisition premium / project rights premium.
    # Deferred wiring until tax/accounting treatment is confirmed.

    FINANCING_COST = "financing_cost"
    # IDC, commitment fees, bank fees — financing overhead

    RESERVE_ACCOUNT = "reserve_account"
    # DSRA, MMRA, working capital reserve

    LAND = "land"
    # Land lease / acquisition — non-depreciable, tax-basis treatment differs

    GENERIC = "generic"
    # Default fallback — no specific scope classification


# ─────────────────────────────────────────────────────────────────────────────
# Payment schedule schema
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CapexPaymentSchedule:
    """
    Payment schedule for a CAPEX line — defines TIMING, not total amount.

    The monthly payment schedule is used to:
    1. Distribute total CAPEX across construction months forIDC capitalization
    2. Drive senior debt drawdown in proportion to spend
    3. Provide monthly cash flow timing for the construction period

    It is separate from the CAPEX line total: the same total can have
    different payment schedules depending on source and profile.
    """

    schedule_type: str
    # "excel_m1_m18"  — from imported Excel 18-month schedule
    # "app_profile"   — from app construction profile (6-mo TUHO, 12-mo Oborovo)
    # "static_reference" — hard-coded reference, not user-editable
    # "missing"        — no schedule data available

    periods: tuple[float, ...]
    # 18 fractions f₀..f₁₇ summing to 1.0.
    # Multiply total_keur by each period to get monthly spend amount.

    amounts_keur: Optional[tuple[float, ...]] = None
    # Optional explicit 18-month amounts.
    # If None: computed as [total_keur × p for p in periods].

    total_keur: float = 0.0
    # The total CAPEX amount this schedule applies to.

    source: str = ""
    # Human-readable source: "excel_capex_sheet", "app_construction_profile", etc.

    authority_status: str = ""
    # Mirrors the row authority_status for this schedule.

    notes: str = ""
    # Free-text notes about schedule source and intended use.


# ─────────────────────────────────────────────────────────────────────────────
# Line definition schema
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CapexLineDefinition:
    """
    Schema record for one CAPEX line item (C.01–C.18 child row).

    This is the design/future-wiring record type used to document:
    - Source type: where does the value come from?
    - Scope: what does the amount mean?
    - Runtime wiring: does it affect financial model calculations?
    - Tax/funding metadata: how is it treated for depreciation, tax shield, funding?

    This is NOT currently the runtime row format — it is the *schema design*
    that will guide Phase 21E wiring implementation.
    """

    code: str
    # "C", "C.02", "C.02.01" — hierarchical code in the CapEx sheet

    label: str
    # Human-readable label

    parent_code: Optional[str]
    # Parent code: "C" for top-level categories (C.01, C.02, ...),
    # "C.02" for child rows (C.02.01, C.02.02, ...), None for "C" itself.

    source_type: str
    # One of CapexSourceType values.
    # Use the constant, not the string value directly.

    scope: str
    # One of CapexScope values.
    # Use the constant, not the string value directly.

    amount_keur: Optional[float]
    # Amount in kEUR. None if not_applicable or not yet mapped.

    affects_runtime: bool
    # True if this line feeds into the financial model's CFADS or debt sizing.

    runtime_field: Optional[str]
    # e.g. "capex.epc_contract.amount_keur" — app CapexStructure field name.
    # None if source_type=EXCEL_REFERENCE or not yet wired.

    depreciation_category: Optional[str] = None
    # Depreciation category for tax/accounting purposes.
    # e.g. "plant_machinery", "land", "rights", "intangible"
    # None = not yet determined.

    tax_basis_category: Optional[str] = None
    # Tax basis treatment.
    # e.g. "tax_shield_eligible", "land_rights_excluded"
    # None = not yet determined.

    funding_category: Optional[str] = None
    # Funding source category.
    # e.g. "equity", "senior_debt", "mezzanine", "grant"
    # None = not yet determined.

    mapping_note: str = ""
    # Human-readable note: scope explanation, mismatch reason, deferred status, etc.

    monthly_schedule: Optional[CapexPaymentSchedule] = None
    # Payment schedule (M1-M18 fractions) if applicable for this line.
    # None for non-construction lines or lines without schedule data.


# ─────────────────────────────────────────────────────────────────────────────
# Schema container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CapexInputSchemaDesign:
    """
    Top-level container for a project's CAPEX input schema.

    Provides a versioned, typed container for all line definitions,
    schedules, and metadata for a given project.
    """

    project_code: str
    # e.g. "TUHO", "OBOROVO"

    lines: tuple[CapexLineDefinition, ...] = field(default_factory=tuple)
    # All C.01–C.18 line definitions for this project

    schedules: tuple[CapexPaymentSchedule, ...] = field(default_factory=tuple)
    # Payment schedules referenced by lines

    version: str = ""
    # Schema version, e.g. "2026.05.28-v1"

    notes: str = ""
    # Overall schema notes, open questions, deferred items
