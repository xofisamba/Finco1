"""Phase P1-B + Phase S2 — Generic Driver Status Badges / Metadata helpers.

Pure read-side helper module. Provides the driver
status vocabulary, badge class names, tooltip
copy, and the field-to-status mapping for the
Generic Solar / Wind input form.

This is the UI explanation layer that follows the
Phase P1-A driver-response audit and the Phase S2
gearing-as-output rule. The helper does NOT mutate
any input, does NOT call the runtime, does NOT
change formulas.

Mapping (per PR #600 audit, branch f8ae191; refined
by Phase S2):

  METADATA_ONLY (2 fields):
    - ppa_term_years
    - construction_months

  REPORTING_DERIVED (1 field, NEW in Phase S2):
    - gearing_pct

  DSCR SCULPT DRIVER (3 fields, after S2):
    - interest_rate_pct
    - tenor_years
    - target_dscr

  WIRED (5 fields, no badge by default):
    - tariff_eur_mwh
    - p50_hours
    - capacity_mw
    - total_capex_keur
    - opex_y1_keur

  NOT_WIRED: 0 fields.

Phase S2 amendment: gearing_pct is no longer labeled
as a DSCR sculpt driver. Under DSCR sculpt, the
sizing CFADS basis sizes senior debt to hit
target_dscr. gearing_pct is the user-supplied
indicative gearing assumption; the realized
gearing_ratio is a DERIVED OUTPUT computed as
senior_debt_keur / total_capex_keur. The user-facing
label is now "Indicative (derived)" with copy that
explains the relationship.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Status vocabulary
# ---------------------------------------------------------------------------


STATUS_WIRED = "WIRED"
STATUS_WIRED_PARTIAL = "WIRED_PARTIAL"
STATUS_METADATA_ONLY = "METADATA_ONLY"
STATUS_NOT_WIRED = "NOT_WIRED"
# Phase S2: gearing_pct is now REPORTING_DERIVED
# (the realized gearing is a derived output, the
# input value is an indicative assumption).
STATUS_REPORTING_DERIVED = "REPORTING_DERIVED"

ALL_STATUSES: tuple[str, ...] = (
    STATUS_WIRED,
    STATUS_WIRED_PARTIAL,
    STATUS_METADATA_ONLY,
    STATUS_NOT_WIRED,
    STATUS_REPORTING_DERIVED,
)

# P1-B badge vocabulary (the labels we render in the UI).
BADGE_METADATA_ONLY = "Metadata only"
BADGE_DSCR_SCULPT_DRIVER = "DSCR sculpt driver"
# Phase S2: badge for gearing_pct. "Indicative (derived)"
# tells the pilot user that the input value is an
# indicative assumption and the realized gearing is
# computed as a derived output.
BADGE_REPORTING_DERIVED = "Indicative (derived)"
# Fully wired fields get no badge by default
# (the form stays uncluttered per the P1-B brief).
BADGE_NONE: Optional[str] = None

# CSS class names that the inputs_section.html
# uses to render the badge.
CSS_CLASS_METADATA = "badge-metadata"
CSS_CLASS_DSCR_SCULPT = "badge-dscr-sculpt"
# Phase S2: new CSS class for derived/reporting
# fields. Visually distinct from metadata-only
# (which is a "no effect" badge) and from
# DSCR sculpt (which is a "binds" badge).
CSS_CLASS_REPORTING = "badge-reporting"
CSS_CLASS_NONE: Optional[str] = None


# ---------------------------------------------------------------------------
# Tooltip copy (per the P1-B brief)
# ---------------------------------------------------------------------------


TOOLTIP_METADATA_ONLY: str = (
    "This field is saved/displayed for context but "
    "is not currently used by the Generic runtime "
    "calculation."
)

TOOLTIP_DSCR_SCULPT_DRIVER: str = (
    "This field affects debt / equity / DSCR outputs "
    "under the current DSCR sculpting method. "
    "Project IRR may not change."
)

# Phase S2: tooltip for the gearing_pct field.
# Honest copy: gearing is a user-supplied
# indicative assumption; the realized gearing is
# a derived output (computed as senior_debt /
# total_capex at runtime). Under DSCR sculpt, the
# senior debt amount is sized to hit target_dscr;
# the user-supplied gearing_pct is preserved as
# a reporting/derived metric but is NOT the
# binding driver of senior debt size.
TOOLTIP_REPORTING_DERIVED: str = (
    "Indicative gearing assumption. The realized "
    "gearing is shown as a derived output (senior "
    "debt / total CAPEX). Under DSCR sculpt sizing, "
    "senior debt is sized to hit target DSCR, so the "
    "user-supplied gearing_pct is preserved as a "
    "reporting metric, not as a binding senior debt "
    "sizing driver."
)


# ---------------------------------------------------------------------------
# Field-to-status mapping
# ---------------------------------------------------------------------------


METADATA_ONLY_FIELDS: tuple[str, ...] = (
    "ppa_term_years",
    "construction_months",
)

# Phase S2: gearing_pct is no longer a DSCR sculpt
# driver. It is a user-supplied indicative gearing
# assumption; the realized gearing is a derived
# output (computed as senior_debt / total_capex).
# The field maps to REPORTING_DERIVED.
REPORTING_DERIVED_FIELDS: tuple[str, ...] = (
    "gearing_pct",
)

DSCR_SCULPT_DRIVER_FIELDS: tuple[str, ...] = (
    # Phase S2: gearing_pct removed (moved to
    # REPORTING_DERIVED_FIELDS).
    "interest_rate_pct",
    "tenor_years",
    "target_dscr",
)

WIRED_FIELDS: tuple[str, ...] = (
    "tariff_eur_mwh",
    "p50_hours",
    "capacity_mw",
    "total_capex_keur",
    "opex_y1_keur",
)

NOT_WIRED_FIELDS: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Field status entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldDriverStatus:
    """A single field's UI status for the form."""

    #: The field key (e.g. "gearing_pct").
    field: str

    #: The audit status: WIRED, WIRED_PARTIAL,
    #: METADATA_ONLY, NOT_WIRED.
    status: str

    #: The badge text to render next to the field
    #: (or None for fully wired fields).
    badge_text: Optional[str]

    #: The CSS class to apply to the badge (or None).
    badge_class: Optional[str]

    #: The tooltip copy (or None for fully wired).
    badge_title: Optional[str]


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


def is_metadata_only_field(field: str) -> bool:
    """Return True if the field is in the
    METADATA_ONLY set."""
    return field in METADATA_ONLY_FIELDS


def is_reporting_derived_field(field: str) -> bool:
    """Phase S2: return True if the field is in the
    REPORTING_DERIVED set (e.g. gearing_pct)."""
    return field in REPORTING_DERIVED_FIELDS


def is_dscr_sculpt_driver_field(field: str) -> bool:
    """Return True if the field is in the DSCR
    SCULPT DRIVER set."""
    return field in DSCR_SCULPT_DRIVER_FIELDS


def is_wired_field(field: str) -> bool:
    """Return True if the field is in the WIRED set."""
    return field in WIRED_FIELDS


def get_field_status(field: str) -> str:
    """Return the audit status for a field."""
    if is_metadata_only_field(field):
        return STATUS_METADATA_ONLY
    if is_reporting_derived_field(field):
        return STATUS_REPORTING_DERIVED
    if is_dscr_sculpt_driver_field(field):
        return STATUS_WIRED_PARTIAL
    if is_wired_field(field):
        return STATUS_WIRED
    return STATUS_NOT_WIRED


def get_field_badge(field: str) -> FieldDriverStatus:
    """Return the FieldDriverStatus (status, badge
    text, badge class, tooltip) for a field.

    Fully wired fields return badge_text=None so
    the template does not render a badge."""
    if is_metadata_only_field(field):
        return FieldDriverStatus(
            field=field,
            status=STATUS_METADATA_ONLY,
            badge_text=BADGE_METADATA_ONLY,
            badge_class=CSS_CLASS_METADATA,
            badge_title=TOOLTIP_METADATA_ONLY,
        )
    # Phase S2: REPORTING_DERIVED is checked before
    # DSCR_SCULPT_DRIVER. The reporting/derived
    # status takes precedence (gearing_pct is no
    # longer a binding sculpt driver).
    if is_reporting_derived_field(field):
        return FieldDriverStatus(
            field=field,
            status=STATUS_REPORTING_DERIVED,
            badge_text=BADGE_REPORTING_DERIVED,
            badge_class=CSS_CLASS_REPORTING,
            badge_title=TOOLTIP_REPORTING_DERIVED,
        )
    if is_dscr_sculpt_driver_field(field):
        return FieldDriverStatus(
            field=field,
            status=STATUS_WIRED_PARTIAL,
            badge_text=BADGE_DSCR_SCULPT_DRIVER,
            badge_class=CSS_CLASS_DSCR_SCULPT,
            badge_title=TOOLTIP_DSCR_SCULPT_DRIVER,
        )
    if is_wired_field(field):
        return FieldDriverStatus(
            field=field,
            status=STATUS_WIRED,
            badge_text=BADGE_NONE,
            badge_class=CSS_CLASS_NONE,
            badge_title=None,
        )
    return FieldDriverStatus(
        field=field,
        status=STATUS_NOT_WIRED,
        badge_text=None,
        badge_class=None,
        badge_title=None,
    )


# ---------------------------------------------------------------------------
# Exploratory / warning copy (used by the partial)
# ---------------------------------------------------------------------------


EXPLORATORY_NOTICE_TEXT: str = (
    "This Generic project is editable for sketching "
    "scenarios, but the runtime output has not been "
    "validated against an Excel reference. Outputs are "
    "not lender-ready, audit-ready, or bank-approved. "
    "Use only for exploratory analysis."
)


__all__ = [
    "STATUS_WIRED",
    "STATUS_WIRED_PARTIAL",
    "STATUS_METADATA_ONLY",
    "STATUS_NOT_WIRED",
    "STATUS_REPORTING_DERIVED",
    "ALL_STATUSES",
    "BADGE_METADATA_ONLY",
    "BADGE_DSCR_SCULPT_DRIVER",
    "BADGE_REPORTING_DERIVED",
    "BADGE_NONE",
    "CSS_CLASS_METADATA",
    "CSS_CLASS_DSCR_SCULPT",
    "CSS_CLASS_REPORTING",
    "CSS_CLASS_NONE",
    "TOOLTIP_METADATA_ONLY",
    "TOOLTIP_DSCR_SCULPT_DRIVER",
    "TOOLTIP_REPORTING_DERIVED",
    "METADATA_ONLY_FIELDS",
    "REPORTING_DERIVED_FIELDS",
    "DSCR_SCULPT_DRIVER_FIELDS",
    "WIRED_FIELDS",
    "NOT_WIRED_FIELDS",
    "FieldDriverStatus",
    "is_metadata_only_field",
    "is_reporting_derived_field",
    "is_dscr_sculpt_driver_field",
    "is_wired_field",
    "get_field_status",
    "get_field_badge",
    "EXPLORATORY_NOTICE_TEXT",
]
