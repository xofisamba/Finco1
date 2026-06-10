"""Phase P1-B — Generic Driver Status Badges / Metadata helpers.

Pure read-side helper module. Provides the driver
status vocabulary, badge class names, tooltip
copy, and the field-to-status mapping for the
Generic Solar / Wind input form.

This is the UI explanation layer that follows the
Phase P1-A driver-response audit. The helper does
NOT mutate any input, does NOT call the runtime,
does NOT change formulas.

Mapping (per PR #600 audit, branch f8ae191):

  METADATA_ONLY (2 fields):
    - ppa_term_years
    - construction_months

  DSCR SCULPT DRIVER (4 fields):
    - gearing_pct
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

ALL_STATUSES: tuple[str, ...] = (
    STATUS_WIRED,
    STATUS_WIRED_PARTIAL,
    STATUS_METADATA_ONLY,
    STATUS_NOT_WIRED,
)

# P1-B badge vocabulary (the labels we render in the UI).
BADGE_METADATA_ONLY = "Metadata only"
BADGE_DSCR_SCULPT_DRIVER = "DSCR sculpt driver"
# Fully wired fields get no badge by default
# (the form stays uncluttered per the P1-B brief).
BADGE_NONE: Optional[str] = None

# CSS class names that the inputs_section.html
# uses to render the badge.
CSS_CLASS_METADATA = "badge-metadata"
CSS_CLASS_DSCR_SCULPT = "badge-dscr-sculpt"
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


# ---------------------------------------------------------------------------
# Field-to-status mapping
# ---------------------------------------------------------------------------


METADATA_ONLY_FIELDS: tuple[str, ...] = (
    "ppa_term_years",
    "construction_months",
)

DSCR_SCULPT_DRIVER_FIELDS: tuple[str, ...] = (
    "gearing_pct",
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
    "ALL_STATUSES",
    "BADGE_METADATA_ONLY",
    "BADGE_DSCR_SCULPT_DRIVER",
    "BADGE_NONE",
    "CSS_CLASS_METADATA",
    "CSS_CLASS_DSCR_SCULPT",
    "CSS_CLASS_NONE",
    "TOOLTIP_METADATA_ONLY",
    "TOOLTIP_DSCR_SCULPT_DRIVER",
    "METADATA_ONLY_FIELDS",
    "DSCR_SCULPT_DRIVER_FIELDS",
    "WIRED_FIELDS",
    "NOT_WIRED_FIELDS",
    "FieldDriverStatus",
    "is_metadata_only_field",
    "is_dscr_sculpt_driver_field",
    "is_wired_field",
    "get_field_status",
    "get_field_badge",
    "EXPLORATORY_NOTICE_TEXT",
]
