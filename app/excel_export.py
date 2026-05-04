"""Values-only Excel export — no formulas, no calibration."""
from __future__ import annotations
import pandas as pd
from io import BytesIO

import openpyxl
from openpyxl.styles import Font, numbers
from openpyxl.utils import get_column_letter


# KPI label mapping: raw key → clean display label
_DASHBOARD_LABELS = {
    "total_revenue_keur": "Total Revenue (kEUR)",
    "total_ebitda_keur": "EBITDA (kEUR)",
    "total_tax_keur": "Total Tax (kEUR)",
    "project_irr": "Project IRR (%)",
    "equity_irr": "Equity IRR (%)",
    "sponsor_irr": "Sponsor IRR (%)",
    "min_dscr": "Min DSCR",
    "avg_dscr": "Avg DSCR",
    "total_senior_ds_keur": "Senior Debt Service (kEUR)",
    "total_distribution_keur": "Distributions (kEUR)",
}


def build_excel_export(
    *,
    result=None,
    portfolio_result=None,
    project_inputs=None,
    validation_issues=None,
    integration_status: str = "full",
    integration_note: str | None = None,
    scenario: str = "Base",
    period_view: str = "Semiannual",
    warnings: list = None,
) -> bytes:
    """Build a values-only Excel workbook from waterfall results.
    
    Returns bytes suitable for st.download_button.
    """
    from app.output_tables import (
        build_dashboard_kpis,
        build_waterfall_table,
        build_revenue_table,
        build_debt_table,
        build_tax_depreciation_table,
        build_returns_table,
        build_portfolio_table,
        aggregate_period_table_annual,
    )
    from app.input_helpers import build_inputs_summary_table, build_capex_summary_table, build_capex_items_table
    
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # ── Dashboard (always first) ─────────────────────────────────────
        _write_dashboard_sheet(writer, result, portfolio_result, integration_status, integration_note, scenario)

        # ── Returns ───────────────────────────────────────────────────────
        if result is not None:
            _write_sheet(writer, "Returns", build_returns_table(result),
                         number_format={"IRR": "0.0%", "DSCR": "0.00x", "kEUR": "#,##0"})

        # ── DSCR Summary ────────────────────────────────────────────────────
        if result is not None and hasattr(result, "target_dscr"):
            rows = [
                ("Metric", "Value"),
                ("Target DSCR", f"{result.target_dscr:.3f}"),
                ("Actual Min DSCR", f"{result.actual_min_dscr:.3f}"),
                ("Actual Avg DSCR", f"{result.actual_avg_dscr:.3f}"),
                ("Deviation", f"{result.actual_min_dscr - result.target_dscr:+.3f}"),
            ]
            dscr_df = pd.DataFrame(rows[1:], columns=["Metric", "Value"])
            _write_sheet(writer, "DSCR Summary", dscr_df)

        # ── Waterfall ─────────────────────────────────────────────────────
        if result is not None:
            wf_df = build_waterfall_table(result)
            if period_view == "Annual":
                wf_df = aggregate_period_table_annual(wf_df)
            _write_sheet(writer, "Waterfall", wf_df,
                         number_format={"kEUR": "#,##0", "DSCR": "0.00x"})

        # ── Revenue ────────────────────────────────────────────────────────
        if result is not None:
            rev_df = build_revenue_table(result)
            if period_view == "Annual":
                rev_df = aggregate_period_table_annual(rev_df)
            _write_sheet(writer, "Revenue", rev_df, number_format={"kEUR": "#,##0", "MWh": "#,##0"})

        # ── Debt ──────────────────────────────────────────────────────────
        if result is not None:
            debt_df = build_debt_table(result)
            if period_view == "Annual":
                debt_df = aggregate_period_table_annual(debt_df)
            _write_sheet(writer, "Debt", debt_df,
                         number_format={"kEUR": "#,##0", "DSCR": "0.00x", "LLCR": "0.00x", "PLCR": "0.00x"})

        # ── Tax & Depreciation ─────────────────────────────────────────────
        if result is not None:
            tax_df = build_tax_depreciation_table(result)
            if period_view == "Annual":
                tax_df = aggregate_period_table_annual(tax_df)
            _write_sheet(writer, "Tax_Depreciation", tax_df, number_format={"kEUR": "#,##0"})

        # ── Notes ──────────────────────────────────────────────────────────
        _write_notes_sheet(writer, integration_status, integration_note, scenario, period_view,
                           warnings=warnings if warnings else [])

        # ── Inputs ────────────────────────────────────────────────────────
        _write_sheet(writer, "Inputs", build_inputs_summary_table(project_inputs))

        # ── CapEx ──────────────────────────────────────────────────────────
        _write_sheet(writer, "CapEx", build_capex_summary_table(project_inputs),
                     number_format={"kEUR": "#,##0"})
        _write_sheet(writer, "CapEx_Items", build_capex_items_table(project_inputs),
                     number_format={"Amount": "#,##0"})

        # ── Portfolio ──────────────────────────────────────────────────────
        if portfolio_result is not None:
            _write_sheet(writer, "Portfolio", build_portfolio_table(portfolio_result),
                         number_format={"kEUR": "#,##0", "IRR": "0.0%", "DSCR": "0.00x"})
            if portfolio_result.portfolio_cashflows:
                rows = []
                for row in portfolio_result.portfolio_cashflows:
                    date = row.get("date", "")
                    total = row.get("total_cashflow", 0.0)
                    breakdown = row.get("breakdown", {})
                    row_dict = {"Date": str(date), "Total CF (keur)": round(total, 2)}
                    for proj, contrib in breakdown.items():
                        row_dict[f"  {proj}"] = round(contrib, 2)
                    rows.append(row_dict)
                cf_df = pd.DataFrame(rows)
                _write_sheet(writer, "Portfolio CF", cf_df, number_format={"kEUR": "#,##0"})

        # ── Validation ────────────────────────────────────────────────────
        _write_validation_sheet(writer, validation_issues)
    
    output.seek(0)
    return output.read()




def _write_sheet(writer, name: str, df: pd.DataFrame,
                 number_format: dict | None = None) -> None:
    """Write a DataFrame to a sheet with bold headers, frozen row, auto-width, and number formats."""
    if df is None or df.empty:
        df = pd.DataFrame({"Note": ["No data available"]})
    df.to_excel(writer, sheet_name=name[:31], index=True)
    ws = writer.sheets[name[:31]]

    # Bold header row
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # Freeze top row
    ws.freeze_panes = "A2"

    # Ensure sheet is visible
    ws.sheet_state = "visible"

    # Auto column width based on content
    for col_idx, col in enumerate(df.columns, start=1):
        col_letter = get_column_letter(col_idx)
        max_len = len(str(col))  # header length
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=col_idx, max_col=col_idx):
            for cell in row:
                if cell.value is not None:
                    max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_len + 3, 40)

    # Apply number formats based on row labels
    if number_format:
        irr_patterns = ("irr", "project irr", "equity irr", "sponsor irr")
        dscr_patterns = ("dscr", "min dscr", "avg dscr", "llcr", "plcr")
        keur_patterns = ("keur", "revenue", "ebitda", "debt", "tax", "distribution", "capex")
        mwh_patterns = ("mwh", "generation", "capacity")

        for row_idx, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row), start=2):
            row_label_cell = ws.cell(row=row_idx, column=1)
            if row_label_cell.value:
                label_lower = str(row_label_cell.value).lower()
                for col_idx_c, cell in enumerate(row, start=1):
                    if cell.value is None:
                        continue
                    col_letter = get_column_letter(col_idx_c)
                    # IRR format
                    if any(p in label_lower for p in irr_patterns) and "format" not in label_lower:
                        cell.number_format = "0.0%"
                    # DSCR / LLCR / PLCR format
                    elif any(p in label_lower for p in dscr_patterns):
                        cell.number_format = "0.00x"
                    # kEUR format
                    elif any(p in label_lower for p in keur_patterns):
                        cell.number_format = "#,##0"
                    # MWh format
                    elif any(p in label_lower for p in mwh_patterns):
                        cell.number_format = "#,##0"


def _write_dashboard_sheet(writer, result, portfolio_result, status, note, scenario) -> None:
    """Write a Dashboard sheet with KPI summary and integration info."""
    rows = [
        ("Integration Status", status),
        ("Scenario", scenario),
    ]
    if note:
        rows.append(("Note", note))
    if result is not None:
        kpis = build_dashboard_kpis(result)
        for k, v in kpis.items():
            if v is not None and v != "n/a":
                label = _DASHBOARD_LABELS.get(k, k)
                # Format IRR values as decimals → Excel will show as %
                if "irr" in k.lower():
                    try:
                        rows.append((label, float(v) / 100))  # Store as decimal for 0.0% format
                    except (TypeError, ValueError):
                        rows.append((label, v))
                else:
                    rows.append((label, v))
    if portfolio_result is not None:
        rows.append(("Pooled Revenue (kEUR)", portfolio_result.total_revenue_keur))
        rows.append(("Pooled EBITDA (kEUR)", portfolio_result.total_ebitda_keur))
        rows.append(("Portfolio DSCR (Avg)", portfolio_result.avg_dscr))
        rows.append(("Portfolio DSCR (Min)", portfolio_result.min_dscr))

    df = pd.DataFrame(rows, columns=["Metric", "Value"])
    df.to_excel(writer, sheet_name="Dashboard", index=False)
    ws = writer.sheets["Dashboard"]
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"
    ws.sheet_state = "visible"

    # Apply number formats to Dashboard sheet
    irr_cols = []
    dscr_cols = []
    keur_cols = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row), start=2):
        label_cell = ws.cell(row=row_idx, column=1)
        if label_cell.value:
            label_lower = str(label_cell.value).lower()
            if "irr" in label_lower:
                irr_cols.append(row_idx)
            elif "dscr" in label_lower:
                dscr_cols.append(row_idx)
            elif "keur" in label_lower or "revenue" in label_lower or "ebitda" in label_lower:
                keur_cols.append(row_idx)

    for row_idx in irr_cols:
        ws.cell(row=row_idx, column=2).number_format = "0.0%"
    for row_idx in dscr_cols:
        ws.cell(row=row_idx, column=2).number_format = "0.00x"
    for row_idx in keur_cols:
        ws.cell(row=row_idx, column=2).number_format = "#,##0"


def _write_validation_sheet(writer, validation_issues) -> None:
    """Write a Validation sheet."""
    if validation_issues is None:
        df = pd.DataFrame({"severity": ["info"], "field": [""], "message": ["No validation issues."]})
    else:
        rows = [(i.severity, i.field, i.message) for i in validation_issues]
        df = pd.DataFrame(rows, columns=["severity", "field", "message"])
    df.to_excel(writer, sheet_name="Validation", index=False)
    ws = writer.sheets["Validation"]
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"
    ws.sheet_state = "visible"


def _write_notes_sheet(writer, status, note, scenario, period_view, warnings=None) -> None:
    if warnings is None:
        warnings = []
    """Write a Notes sheet."""
    rows = [
        ("Field", "Value"),
        ("Model Version", "industry-engine-refactor"),
        ("Run Timestamp", pd.Timestamp.now().strftime("%Y-%m-%d %H:%M UTC")),
        ("Integration Status", status),
        ("Scenario", scenario),
        ("Period View", period_view),
        ("Note", note if note else "n/a"),
        ("Values-only Export", "No formulas used in this workbook."),
        ("Economic LCOE", "Excludes debt service — see methodology document for details."),
    ]

    # BESS/hybrid warning
    if status == "partial":
        rows.append(("BESS/hybrid Status", "Partial integration — revenue-only shown, waterfall in progress"))

    # Model Warnings section
    if warnings:
        rows.append(("Model Warnings", "—"))
        for w in warnings:
            rows.append((w.get("code", "WARN"), w.get("message", str(w))))

    # Portfolio warning
    if status == "experimental":
        rows.append(("Portfolio Status", "Experimental — sponsor IRR is placeholder"))

    # Scenario deltas
    if scenario != "Base":
        if status == "experimental":
            rows.append(("Scenario", f"{scenario} — NOT APPLIED"))
            rows.append(("Scenario Deltas", "Base case shown — Portfolio does not support scenarios"))
        else:
            from app.scenarios import scenario_summary
            deltas = scenario_summary(scenario)
            rows.append(("Scenario Deltas", "—"))
            for row in deltas:
                rows.append((
                    f"  {row['assumption']}",
                    f"{row['change']} ({row['scenario']} vs base)",
                ))
                if row.get("note"):
                    rows.append(("  Note", row["note"]))
    else:
        rows.append(("Scenario Deltas", "Base case — no adjustments"))

    df = pd.DataFrame(rows[1:], columns=["Field", "Value"])
    df.to_excel(writer, sheet_name="Notes", index=False)
    ws = writer.sheets["Notes"]
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"
    ws.sheet_state = "visible"
