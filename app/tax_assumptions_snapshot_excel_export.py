"""Phase 6D.2 — Excel export for tax assumption snapshots.

Optional layer on top of app.tax_assumptions_excel_export.
All behavior delegated to write_tax_assumptions_audit_sheets().

CAVEAT: Values-only. No active model wiring. No existing excel_export.py modification.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.tax.assumptions_snapshot import TaxAssumptionSnapshot


def write_tax_snapshot_sheets(
    writer,
    snapshot: TaxAssumptionSnapshot,
) -> None:
    """Write audit sheets for a TaxAssumptionSnapshot into an open Excel workbook.

    Delegates to app.tax_assumptions_excel_export.write_tax_assumptions_audit_sheets()
    using the underlying resolved configs and overrides from the snapshot.

    Parameters
    ----------
    writer : pandas.ExcelWriter
        Open ExcelWriter (e.g., from pd.ExcelWriter(filepath)).
    snapshot : TaxAssumptionSnapshot
        Immutable snapshot artifact (not mutated).

    Notes
    -----
    - Does NOT modify existing sheets.
    - Does NOT call build_excel_export() or replace it.
    - Snapshot is a read-only audit artifact.
    """
    from app.tax_assumptions_excel_export import write_tax_assumptions_audit_sheets
    from domain.tax.templates.inputs import TaxTemplate, TaxTemplateOverride

    # Reconstruct TaxTemplate objects from snapshots (templates are immutable snapshots)
    templates = []
    overrides_list = []
    resolved_configs_list = []

    for ts in snapshot.template_snapshots:
        # templates stored as TaxTemplate — already immutable
        templates.append(ts)

    for os_ in snapshot.override_snapshots:
        override = TaxTemplateOverride(
            override_name=os_.override_name,
            field_path=os_.field_path,
            override_value=os_.override_value,
            reason=os_.reason or "",
        )
        overrides_list.append(override)

    write_tax_assumptions_audit_sheets(
        writer,
        templates=tuple(templates),
        resolved_configs=tuple(resolved_configs_list),
        overrides=tuple(overrides_list),
    )
