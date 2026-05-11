"""Phase 6D.2 — Excel export from TaxAssumptionSnapshot.

Reconstructs exportable objects from snapshot dataclasses and delegates
to write_tax_assumptions_audit_sheets().

Pure function — no mutation, no active model wiring.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.tax.assumptions_snapshot import TaxAssumptionSnapshot

__all__ = ["write_tax_assumption_snapshot_sheets"]


def write_tax_assumption_snapshot_sheets(writer, snapshot: "TaxAssumptionSnapshot") -> None:
    """Write all tax assumption audit sheets from a TaxAssumptionSnapshot.

    Reconstructs TaxTemplate and override objects from snapshot dataclasses,
    then delegates to write_tax_assumptions_audit_sheets().

    Parameters
    ----------
    writer : pandas.ExcelWriter
        Open ExcelWriter (e.g., from pd.ExcelWriter(filepath)).
    snapshot : TaxAssumptionSnapshot
        Immutable snapshot artifact. Not mutated.

    Notes
    -----
    - Does NOT modify existing sheets.
    - Snapshot is a read-only audit artifact.
    """
    from app.tax_assumptions_excel_export import write_tax_assumptions_audit_sheets
    from domain.tax.templates.inputs import (
        CITTier,
        TaxDepreciationRule,
        TaxTemplate,
        TaxTemplateOverride,
    )

    # Reconstruct TaxTemplate objects from TaxTemplateSnapshot dataclasses
    templates = []
    for ts in snapshot.template_snapshots:
        # Parse cit_tiers_summary back to CITTier objects
        # cit_tiers_summary is tuple of "18%", "10%", etc.
        cit_tiers = []
        if ts.cit_structure == "None":
            pass  # empty tuple
        elif ts.cit_structure == "Flat":
            rate_str = ts.cit_tiers_summary[0].replace("%", "")
            rate = float(rate_str) / 100.0
            cit_tiers.append(CITTier(min_profit_keur=0.0, max_profit_keur=None, tax_rate=rate))
        else:  # Progressive
            for i, rate_str in enumerate(ts.cit_tiers_summary):
                rate = float(rate_str.replace("%", "")) / 100.0
                if i == 0:
                    cit_tiers.append(CITTier(min_profit_keur=0.0, max_profit_keur=500.0, tax_rate=rate))
                else:
                    cit_tiers.append(CITTier(min_profit_keur=500.0, max_profit_keur=None, tax_rate=rate))

        # Parse depreciation_rules_summary back to TaxDepreciationRule objects
        # Format: "buildings: straight_line: 20yr"
        dep_rules = []
        for rule_str in ts.depreciation_rules_summary:
            parts = rule_str.split(": ")
            if len(parts) == 3:
                asset_category = parts[0]
                method = parts[1]
                life_str = parts[2].replace("yr", "").replace("N/A", "0")
                try:
                    useful_life_years = float(life_str)
                except ValueError:
                    useful_life_years = None

                dep_rules.append(TaxDepreciationRule(
                    asset_category=asset_category,
                    method=method,
                    annual_rate=None,
                    useful_life_years=useful_life_years,
                    max_deductible_rate=None,
                    bonus_depreciation_pct=0.0,
                    deductible=True,
                    notes="",
                ))

        template = TaxTemplate(
            country_code=ts.country_code,
            template_name=ts.template_name,
            tax_year=ts.tax_year,
            cit_tiers=tuple(cit_tiers),
            depreciation_rules=tuple(dep_rules),
            withholding_tax_dividends=0.12 if ts.has_wht_dividend else 0.0,
            withholding_tax_interest=0.0,
            loss_carryforward_years=ts.loss_carryforward_years,
            thin_cap_ratio=4.0 if ts.has_interest_limitation else None,
            interest_limitation_pct_ebitda=0.30 if ts.has_interest_limitation else None,
            metadata=ts.metadata,
        )
        templates.append(template)

    # Reconstruct override objects from override snapshots
    overrides = []
    for os_ in snapshot.override_snapshots:
        override = TaxTemplateOverride(
            override_name=os_.override_name,
            field_path=os_.field_path,
            override_value=os_.override_value,
            reason=os_.reason or "",
        )
        overrides.append(override)

    # Resolved configs: not stored in snapshot, not exported for now
    resolved_configs = []

    write_tax_assumptions_audit_sheets(
        writer,
        templates=tuple(templates),
        resolved_configs=tuple(resolved_configs),
        overrides=tuple(overrides),
    )
