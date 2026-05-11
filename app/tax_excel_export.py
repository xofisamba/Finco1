"""Phase 6B.5 — Excel export helper for SPV tax engine audit results.

Pure function — no mutation, no model integration.

CAVEAT: Values-only export. No formulas. No existing excel_export.py modification.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.tax import SPVTaxResult

__all__ = ["write_spv_tax_audit_sheets"]


def write_spv_tax_audit_sheets(
    writer,
    tax_results: tuple[SPVTaxResult, ...],
) -> None:
    """Write SPV tax audit sheets into an open Excel workbook.

    Parameters
    ----------
    writer : pandas.ExcelWriter
        Open ExcelWriter (e.g., from pd.ExcelWriter(filepath)).
        Sheet "Tax Summary" is created/overwritten.
        Per-SPV sheets are named "Tax_{entity_code}" (max 31 chars).
    tax_results : tuple[SPVTaxResult, ...]
        Tuple of SPVTaxResult objects. Empty tuple → no-op.

    Behavior
    --------
    - If tax_results is empty, does nothing.
    - Writes "Tax Summary" sheet with one row per SPV (summary table).
    - Writes one detail sheet per SPV: "Tax_{entity_code}" truncated to 31 chars.
    - First row of each sheet is the audit-only note.
    - All values, no formulas.

    Notes
    -----
    - Does NOT modify existing sheets (e.g., dashboard, waterfall).
    - Does NOT call build_excel_export() or replace it.
    - Sheet name truncation uses Excel's 31-char sheet name limit.
    """
    if not tax_results:
        return

    import pandas as pd
    from app.tax_ui import (
        build_spv_tax_summary_table,
        build_spv_tax_period_table,
        build_tax_audit_note,
    )

    audit_note = build_tax_audit_note()

    # ── Tax Summary sheet ────────────────────────────────────────────
    summary_frames = []
    for result in tax_results:
        summary_frames.append(build_spv_tax_summary_table(result))

    if summary_frames:
        summary_df = pd.concat(summary_frames, ignore_index=True)

    # Write Tax Summary sheet
    summary_sheet_name = "Tax Summary"
    summary_df.to_excel(writer, sheet_name=summary_sheet_name, index=False)

    # ── Per-SPV detail sheets ───────────────────────────────────────
    for result in tax_results:
        entity_code = result.entity_code

        # Truncate to Excel 31-char limit and make safe
        safe_name = entity_code.replace("/", "_").replace("\\", "_").replace("*", "_").replace("?", "_").replace("[", "_").replace("]", "_")
        raw_sheet_name = f"Tax_{safe_name}"
        if len(raw_sheet_name) > 31:
            sheet_name = raw_sheet_name[:31]
        else:
            sheet_name = raw_sheet_name

        period_df = build_spv_tax_period_table(result)

        # Prepend audit note as first row (handled via index=False and audit row)
        # Actually, we insert the audit note as a header row above data
        audit_row_df = pd.DataFrame([[audit_note] + [""] * (len(period_df.columns) - 1)],
                                     columns=period_df.columns)

        combined = pd.concat([audit_row_df, period_df], ignore_index=True)
        combined.to_excel(writer, sheet_name=sheet_name, index=False)