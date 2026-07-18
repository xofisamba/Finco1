"""
finco_parity.profiles — Fixed comparison profile contract.

Profiles are predefined, immutable, and incapable of being changed
by user arguments or field selection. Zero tolerance is enforced by all profiles.

Import boundary
---------------
This module may only import from:
  - Python standard library
  - finco_parity.*
It must NOT import from app.*, domain.*, finco_core.*, main_web, main_api.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

# Phase 2A operating-schedule fields that the clean engine populates.
_OPERATING_CORE_V1_OS_FIELDS: frozenset[str] = frozenset({
    "production_mwh",
    "revenue_keur",
    "opex_keur",
    "ebitda_keur",
    "book_depreciation_keur",
    "tax_depreciation_keur",
})

# Period-grid fields the clean engine populates.
_OPERATING_CORE_V1_PG_FIELDS: frozenset[str] = frozenset({
    "period_index",
    "date",
    "year_index",
    "period_in_year",
    "is_operation",
    "is_construction",
    "start_date",
})

OPERATING_CORE_V1_PASS_WORDING = (
    "OPERATING_CORE_V1 PASS confirms parity only for the Phase 2A period, "
    "production, revenue, OPEX, EBITDA and depreciation scope. "
    "Tax, CFADS, financing, waterfall, statements and returns remain unimplemented."
)


class ComparisonProfile(str, Enum):
    """Predefined parity comparison profiles.

    FULL preserves all Phase 1C behaviour unchanged.
    OPERATING_CORE_V1 compares only the exact Phase 2A paths approved in this PR.
    """
    FULL = "full"
    OPERATING_CORE_V1 = "operating-core-v1"


def project_for_profile(
    snapshot: dict[str, Any],
    profile: ComparisonProfile,
) -> dict[str, Any]:
    """Return a projected snapshot view for the given comparison profile.

    FULL: returns all parity sections unchanged (same as Phase 1C behaviour).
    OPERATING_CORE_V1: returns only period_grid and operating_schedules for
        the Phase 2A in-scope fields.
    """
    if profile is ComparisonProfile.FULL:
        return {k: v for k, v in snapshot.items() if k in _FULL_PARITY_SECTIONS}

    if profile is ComparisonProfile.OPERATING_CORE_V1:
        return _project_operating_core_v1(snapshot)

    raise ValueError(f"Unknown profile: {profile!r}")  # pragma: no cover


_FULL_PARITY_SECTIONS: frozenset[str] = frozenset({
    "period_grid",
    "operating_schedules",
    "tax_and_cfads",
    "financing",
    "financial_statements",
    "returns",
    "unavailable_sections",
    "unavailable_fields",
})


def _project_operating_core_v1(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Project to Phase 2A operating-core paths for OPERATING_CORE_V1 comparison."""
    pg = snapshot.get("period_grid") or []
    projected_pg = [
        {k: row.get(k) for k in sorted(_OPERATING_CORE_V1_PG_FIELDS)}
        for row in pg
    ]

    os_ = snapshot.get("operating_schedules") or {}
    projected_os = {
        k: os_[k]
        for k in sorted(_OPERATING_CORE_V1_OS_FIELDS)
        if k in os_
    }

    return {
        "period_grid": projected_pg,
        "operating_schedules": projected_os,
    }
