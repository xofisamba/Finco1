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


# Phase 2B tax-and-CFADS fields that the clean engine computes and the baseline also has.
# Waterfall rows (r69, r84, r99, r102, fcf_for_shl) exist in the baseline but are
# NOT computed by the Phase 2B clean engine; they are declared unavailable in candidate.
_TAX_CFADS_V1_FIELDS: frozenset[str] = frozenset({
    "taxable_profit_keur",
    "taxable_income_before_losses_audit_keur",
    "taxable_profit_after_losses_audit_keur",
    "cit_accrual_audit_keur",
    "cash_tax_current_period_audit_keur",
    "corporate_tax_cash_keur",
    "tax_keur",
    "cash_tax_bridge_reconciliation_keur",
    "tax_loss_opening_audit_keur",
    "tax_loss_used_audit_keur",
    "tax_loss_closing_audit_keur",
    "tax_depreciation_audit_keur",
    "fiscal_reintegration_audit_keur",
    "cf_after_tax_keur",
})

# Waterfall rows the baseline has but the Phase 2B candidate does not implement.
_TAX_CFADS_V1_WATERFALL_UNAVAILABLE: frozenset[str] = frozenset({
    "r69_fcf_banks_keur",
    "r84_fcf_junior_keur",
    "r99_fcf_for_distribution_keur",
    "r102_fcf_for_shl_keur",
    "fcf_for_shl_keur",
})

TAX_CFADS_V1_PASS_WORDING = (
    "TAX_CFADS_V1 PASS confirms parity for Phase 2B tax schedule fields: "
    "taxable income trail, ATAD, FIFO LCF, CIT accrual, cash tax, and cf_after_tax. "
    "Waterfall rows (r69, r84, r99, r102, fcf_for_shl) and canonical CFADS are "
    "out-of-scope for baseline comparison and declared unavailable in the candidate."
)


class ComparisonProfile(str, Enum):
    """Predefined parity comparison profiles.

    FULL preserves all Phase 1C behaviour unchanged.
    OPERATING_CORE_V1 compares only the exact Phase 2A paths approved in this PR.
    TAX_CFADS_V1 compares the Phase 2B tax schedule fields (no waterfall rows).
    """
    FULL = "full"
    OPERATING_CORE_V1 = "operating-core-v1"
    TAX_CFADS_V1 = "tax-cfads-v1"


def project_for_profile(
    snapshot: dict[str, Any],
    profile: ComparisonProfile,
) -> dict[str, Any]:
    """Return a projected snapshot view for the given comparison profile.

    FULL: returns all parity sections unchanged (same as Phase 1C behaviour).
    OPERATING_CORE_V1: returns only period_grid and operating_schedules for
        the Phase 2A in-scope fields.
    TAX_CFADS_V1: returns tax_and_cfads for the Phase 2B in-scope fields only.
    """
    if profile is ComparisonProfile.FULL:
        return {k: v for k, v in snapshot.items() if k in _FULL_PARITY_SECTIONS}

    if profile is ComparisonProfile.OPERATING_CORE_V1:
        return _project_operating_core_v1(snapshot)

    if profile is ComparisonProfile.TAX_CFADS_V1:
        return _project_tax_cfads_v1(snapshot)

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


def _project_tax_cfads_v1(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Project to Phase 2B tax-and-CFADS fields for TAX_CFADS_V1 comparison."""
    tc = snapshot.get("tax_and_cfads") or {}
    projected_tc = {
        k: tc[k]
        for k in sorted(_TAX_CFADS_V1_FIELDS)
        if k in tc
    }
    return {"tax_and_cfads": projected_tc}


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
