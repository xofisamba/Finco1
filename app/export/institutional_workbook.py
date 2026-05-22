"""Institutional workbook skeleton export for Phase 10.

This is a reporting/export foundation only. It uses existing runtime outputs
and governance labels without changing model logic or authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import csv
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from app.export.runtime_summary import build_runtime_summary_rows


@dataclass(frozen=True)
class WorkbookSheetDefinition:
    sheet_order: int
    sheet_name: str
    implemented_level: str
    runtime_or_preview: str
    governance_sensitive: bool
    notes: str


INSTITUTIONAL_SHEET_DEFINITIONS = (
    WorkbookSheetDefinition(1, "Cover", "implemented", "review", True, "Institutional cover sheet with provenance."),
    WorkbookSheetDefinition(2, "Governance", "implemented", "review", True, "Governance metadata and approval status."),
    WorkbookSheetDefinition(3, "Runtime Summary", "implemented", "runtime", True, "Existing runtime summary values only."),
    WorkbookSheetDefinition(4, "Inputs", "placeholder", "preview", True, "Phase 10 placeholder - runtime binding pending."),
    WorkbookSheetDefinition(5, "Construction", "placeholder", "preview", True, "Phase 10 placeholder - runtime binding pending."),
    WorkbookSheetDefinition(6, "OPEX", "placeholder", "preview", True, "Phase 10 placeholder - runtime binding pending."),
    WorkbookSheetDefinition(7, "CAPEX", "placeholder", "preview", True, "Phase 10 placeholder - runtime binding pending."),
    WorkbookSheetDefinition(8, "Revenue", "placeholder", "preview", True, "Phase 10 placeholder - runtime binding pending."),
    WorkbookSheetDefinition(9, "Senior Debt", "placeholder", "preview", True, "Phase 10 placeholder - runtime binding pending."),
    WorkbookSheetDefinition(10, "SHL", "placeholder", "preview", True, "Phase 10 placeholder - runtime binding pending."),
    WorkbookSheetDefinition(11, "Tax", "placeholder", "preview", True, "Phase 10 placeholder - runtime binding pending."),
    WorkbookSheetDefinition(12, "P&L", "placeholder", "preview", True, "Phase 10 placeholder - runtime binding pending."),
    WorkbookSheetDefinition(13, "Cash Flow", "placeholder", "preview", True, "Phase 10 placeholder - runtime binding pending."),
    WorkbookSheetDefinition(14, "Balance Sheet", "placeholder", "preview", True, "Phase 10 placeholder - runtime binding pending."),
    WorkbookSheetDefinition(15, "Audit", "placeholder", "review", True, "Phase 10 placeholder - audit binding pending."),
    WorkbookSheetDefinition(16, "Gap Register", "placeholder", "review", True, "Phase 10 placeholder - gap workflow pending."),
)


THIN_BORDER = Border(
    left=Side(style="thin", color="D5D9E2"),
    right=Side(style="thin", color="D5D9E2"),
    top=Side(style="thin", color="D5D9E2"),
    bottom=Side(style="thin", color="D5D9E2"),
)
TITLE_FILL = PatternFill("solid", fgColor="0F274A")
SECTION_FILL = PatternFill("solid", fgColor="DCE6F2")
META_FILL = PatternFill("solid", fgColor="EEF3F8")
PLACEHOLDER_FILL = PatternFill("solid", fgColor="FFF4D6")
STATUS_BLOCKED_FILL = PatternFill("solid", fgColor="FCE4E4")
STATUS_NOT_APPROVED_FILL = PatternFill("solid", fgColor="FDEBD0")
WHITE_FONT = Font(color="FFFFFF", bold=True, size=14, name="Calibri")
HEADER_FONT = Font(bold=True, size=11, name="Calibri")
K_EUR_FORMAT = '#,##0.0;[Red](#,##0.0);"-"'
RATIO_FORMAT = "0.00%"
MULTIPLE_FORMAT = "0.000x"


RUNTIME_SUMMARY_LABELS = {
    "active_project": ("Active project", ""),
    "project_irr": ("Project IRR", RATIO_FORMAT),
    "equity_irr": ("Equity IRR", RATIO_FORMAT),
    "total_revenue_keur": ("Total revenue", K_EUR_FORMAT),
    "total_ebitda_keur": ("Total EBITDA", K_EUR_FORMAT),
    "total_opex_keur": ("Total OPEX", K_EUR_FORMAT),
    "avg_dscr": ("Average DSCR", MULTIPLE_FORMAT),
    "min_dscr": ("Minimum DSCR", MULTIPLE_FORMAT),
    "total_distributions_keur": ("Total distributions", K_EUR_FORMAT),
    "total_shl_service_keur": ("Total SHL service", K_EUR_FORMAT),
    "g20_status": ("G20 status", ""),
    "r99_r102_status": ("R99/R102 status", ""),
}


def export_institutional_workbook_skeleton(project: str) -> bytes:
    project_key = (project or "tuho").strip().lower()
    runtime_rows = build_runtime_summary_rows(project_key)
    generated_at = runtime_rows[0]["generated_at"]
    branch = runtime_rows[0]["source_branch"]
    project_name = runtime_rows[0]["project"]

    workbook = Workbook()
    cover = workbook.active
    cover.title = "Cover"
    _write_cover_sheet(cover, project_name, generated_at, branch)

    governance = workbook.create_sheet("Governance")
    _write_governance_sheet(governance, runtime_rows, project_name, generated_at, branch)

    runtime = workbook.create_sheet("Runtime Summary")
    _write_runtime_summary_sheet(runtime, runtime_rows, project_name, generated_at, branch)

    for definition in INSTITUTIONAL_SHEET_DEFINITIONS[3:]:
        sheet = workbook.create_sheet(definition.sheet_name)
        _write_placeholder_sheet(sheet, definition, project_name, generated_at, branch)

    for sheet in workbook.worksheets:
        _format_sheet(sheet)

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def write_institutional_workbook_skeleton(
    project: str,
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(export_institutional_workbook_skeleton(project))
    return path


def write_workbook_sheet_map_csv(path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "sheet_order",
                "sheet_name",
                "implemented_level",
                "runtime_or_preview",
                "governance_sensitive",
                "notes",
            ],
        )
        writer.writeheader()
        for definition in INSTITUTIONAL_SHEET_DEFINITIONS:
            writer.writerow(
                {
                    "sheet_order": definition.sheet_order,
                    "sheet_name": definition.sheet_name,
                    "implemented_level": definition.implemented_level,
                    "runtime_or_preview": definition.runtime_or_preview,
                    "governance_sensitive": "yes" if definition.governance_sensitive else "no",
                    "notes": definition.notes,
                }
            )
    return output_path


def _source_branch() -> str:
    return os.getenv("GIT_BRANCH") or os.getenv("BRANCH_NAME") or "unknown"


def _write_cover_sheet(sheet, project_name: str, generated_at: str, branch: str) -> None:
    sheet["A1"] = "Phase 10 Institutional Workbook Skeleton"
    sheet["A1"].fill = TITLE_FILL
    sheet["A1"].font = WHITE_FONT
    sheet["A3"] = "Project"
    sheet["B3"] = project_name
    sheet["A4"] = "Export type"
    sheet["B4"] = "institutional_workbook_skeleton"
    sheet["A5"] = "Generated at"
    sheet["B5"] = generated_at
    sheet["A6"] = "Source branch"
    sheet["B6"] = branch or _source_branch()
    sheet["A7"] = "Runtime / preview"
    sheet["B7"] = "runtime summary + structured placeholders"
    sheet["A9"] = "Purpose"
    sheet["B9"] = (
        "Standardized institutional workbook order for lender, audit, parity, "
        "and governance review workflows."
    )
    sheet["A11"] = "Status"
    sheet["B11"] = "Phase 10 foundation only - not final bankability"


def _write_governance_sheet(sheet, runtime_rows: list[dict[str, str]], project_name: str, generated_at: str, branch: str) -> None:
    _write_metadata_block(sheet, project_name, generated_at, branch, "Governance review")
    sheet["A6"] = "Governance Field"
    sheet["B6"] = "Value"
    sheet["C6"] = "Notes"
    for cell in sheet[6]:
        cell.fill = SECTION_FILL
        cell.font = HEADER_FONT

    rows = [
        ("Governance status", runtime_rows[0]["governance_status"], "Export foundation label only."),
        ("G20 status", runtime_rows[0]["g20_status"], "Remains blocked in this branch."),
        ("R99/R102 status", runtime_rows[0]["r99_r102_status"], "Runtime promotion remains not approved."),
        ("Export type", runtime_rows[0]["export_type"], "Workbook skeleton using existing runtime summary."),
        ("Source branch", branch or _source_branch(), "Branch captured for institutional review provenance."),
        ("Generated at", generated_at, "UTC timestamp from runtime export builder."),
    ]
    for row_idx, row in enumerate(rows, start=7):
        for col_idx, value in enumerate(row, start=1):
            sheet.cell(row=row_idx, column=col_idx, value=value)
        if row[1] == "BLOCKED":
            sheet.cell(row=row_idx, column=2).fill = STATUS_BLOCKED_FILL
        if row[1] == "NOT APPROVED":
            sheet.cell(row=row_idx, column=2).fill = STATUS_NOT_APPROVED_FILL


def _write_runtime_summary_sheet(sheet, runtime_rows: list[dict[str, str]], project_name: str, generated_at: str, branch: str) -> None:
    _write_metadata_block(sheet, project_name, generated_at, branch, "Runtime summary")
    sheet["A6"] = "Metric"
    sheet["B6"] = "Value"
    sheet["C6"] = "Unit"
    sheet["D6"] = "Notes"
    for cell in sheet[6]:
        cell.fill = SECTION_FILL
        cell.font = HEADER_FONT

    row_idx = 7
    for runtime_row in runtime_rows:
        metric = runtime_row["metric"]
        if metric not in RUNTIME_SUMMARY_LABELS:
            continue
        label, number_format = RUNTIME_SUMMARY_LABELS[metric]
        value = _coerce_value(runtime_row["value"], number_format)
        sheet.cell(row=row_idx, column=1, value=label)
        value_cell = sheet.cell(row=row_idx, column=2, value=value)
        sheet.cell(row=row_idx, column=3, value=runtime_row["unit"])
        sheet.cell(row=row_idx, column=4, value=runtime_row["notes"])
        if number_format:
            value_cell.number_format = number_format
        row_idx += 1


def _write_placeholder_sheet(sheet, definition: WorkbookSheetDefinition, project_name: str, generated_at: str, branch: str) -> None:
    _write_metadata_block(sheet, project_name, generated_at, branch, definition.runtime_or_preview)
    sheet["A6"] = definition.sheet_name
    sheet["A6"].font = Font(bold=True, size=12, name="Calibri")
    sheet["A8"] = "Phase 10 placeholder - runtime binding pending"
    sheet["A8"].fill = PLACEHOLDER_FILL
    sheet["A8"].font = Font(bold=True, name="Calibri")
    sheet["A9"] = definition.notes
    sheet["A11"] = "Governance sensitivity"
    sheet["B11"] = "yes" if definition.governance_sensitive else "no"
    sheet["A12"] = "Status"
    sheet["B12"] = definition.implemented_level


def _write_metadata_block(sheet, project_name: str, generated_at: str, branch: str, marker: str) -> None:
    metadata = (
        ("Project", project_name),
        ("Generated at", generated_at),
        ("Export type", "institutional_workbook_skeleton"),
        ("Runtime / preview", marker),
        ("Source branch", branch or _source_branch()),
    )
    for row_idx, (label, value) in enumerate(metadata, start=1):
        sheet.cell(row=row_idx, column=1, value=label)
        sheet.cell(row=row_idx, column=2, value=value)
        sheet.cell(row=row_idx, column=1).fill = META_FILL
        sheet.cell(row=row_idx, column=1).font = HEADER_FONT


def _format_sheet(sheet) -> None:
    sheet.freeze_panes = "A6"
    sheet.sheet_view.showGridLines = False
    sheet.column_dimensions["A"].width = 24
    sheet.column_dimensions["B"].width = 28
    sheet.column_dimensions["C"].width = 18
    sheet.column_dimensions["D"].width = 72
    for row in sheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = THIN_BORDER


def _coerce_value(value: str, number_format: str) -> object:
    if not number_format:
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return value
