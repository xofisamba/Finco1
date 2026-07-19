"""finco_recon.extract_oborovo_excel — Deterministic authoritative extractor.

Reads ``20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm`` and emits a
machine-readable JSON fixture containing financial-truth data for the
Excel↔Python reconciliation.

Design rules
------------
* Only cached/stored cell values are read (``data_only=True``).  Formulas
  are not re-evaluated in Python.
* Every extracted value records its source sheet, row, and column.
* The JSON payload is deterministic: the extraction timestamp is stored
  *separately* from the financial payload so repeated runs on the same
  workbook produce identical financial content.
* The workbook SHA-256 is recorded so downstream consumers can verify
  provenance.

Usage::

    python -m finco_recon.extract_oborovo_excel \\
        --workbook "/path/to/20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm" \\
        --output tests/fixtures/excel_oborovo_financial_truth.json

Exit codes:  0 success · 1 workbook not found · 2 unexpected error.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import sys
from typing import Any

_EXTRACTOR_VERSION = "1.0.0"
_EXPECTED_FILENAME = "20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm"

# ---------------------------------------------------------------------------
# Column layout helpers
# ---------------------------------------------------------------------------
# In every schedule sheet (CF, DS, P&L, Dep) the period axis is:
#   column index 6  → period 0  (construction / pre-COD)
#   column index 7  → period 1  (H2-2030, first operation semester)
#   ...
#   column index 66 → period 60 (last operation semester)
# We extract all 61 periods (0–60).
_PERIOD_COL_OFFSET = 6   # 0-based column index of period-0 column
_N_PERIODS = 61          # periods 0 … 60


def _row_to_periods(row: tuple, n: int = _N_PERIODS) -> list[float | None]:
    """Extract n consecutive period values starting at _PERIOD_COL_OFFSET."""
    out: list[float | None] = []
    for p in range(n):
        col = _PERIOD_COL_OFFSET + p
        v = row[col] if col < len(row) else None
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out.append(float(v))
        else:
            out.append(None)
    return out


def _scalar(row: tuple, col: int) -> Any:
    v = row[col] if col < len(row) else None
    return v


def _date_str(v: Any) -> str | None:
    if isinstance(v, datetime.datetime):
        return v.date().isoformat()
    return None


# ---------------------------------------------------------------------------
# Sheet readers
# ---------------------------------------------------------------------------

def _read_inputs(wb) -> dict:
    ws = wb["Inputs"]
    rows = {r: tuple(row) for r, row in enumerate(
        ws.iter_rows(max_row=350, max_col=20, values_only=True), start=1)}

    def row(r): return rows.get(r, ())
    def cell(r, c): return _scalar(row(r), c)

    def date_cell(r, c) -> str | None:
        return _date_str(cell(r, c))

    # -----------------------------------------------------------------------
    # Scalar inputs
    # -----------------------------------------------------------------------
    inputs: dict = {
        "_source": {"sheet": "Inputs", "extractor_note": "row/col are 1-based"},
        "project_name":             {"value": cell(2, 3),  "row": 2,  "col": "D"},
        "financial_close_date":     {"value": date_cell(9, 3),  "row": 9,  "col": "D"},
        "construction_months":      {"value": cell(10, 3), "row": 10, "col": "D"},
        "operation_start_date":     {"value": date_cell(11, 3), "row": 11, "col": "D"},
        "investment_horizon_years": {"value": cell(14, 3), "row": 14, "col": "D"},
        "model_period":             {"value": cell(18, 3), "row": 18, "col": "D"},
        # Technical
        "capacity_mwp":             {"value": cell(51, 3), "row": 51, "col": "D"},
        "production_scenario":      {"value": cell(52, 3), "row": 52, "col": "D"},
        "operating_hours_p50":      {"value": cell(54, 3), "row": 54, "col": "D"},
        "pv_degradation_pa":        {"value": cell(56, 3), "row": 56, "col": "D"},
        "plant_availability":       {"value": cell(58, 3), "row": 58, "col": "D"},
        "grid_availability":        {"value": cell(59, 3), "row": 59, "col": "D"},
        # Revenue
        "ppa_base_tariff_y1_eur_mwh": {"value": cell(78, 3), "row": 78, "col": "D"},
        "ppa_term_years":           {"value": cell(81, 3), "row": 81, "col": "D"},
        "ppa_index_pa":             {"value": cell(83, 3), "row": 83, "col": "D"},
        "market_price_scenario":    {"value": cell(89, 3), "row": 89, "col": "D"},
        "market_price_y1_eur_mwh":  {"value": cell(92, 3), "row": 92, "col": "D"},
        "market_price_index_pa":    {"value": cell(93, 3), "row": 93, "col": "D"},
        # Sizing
        "senior_debt_amount_keur":  {"value": cell(192, 3), "row": 192, "col": "D"},
        "senior_debt_maturity_years": {"value": cell(196, 3), "row": 196, "col": "D"},
        "senior_debt_last_repayment": {"value": date_cell(197, 3), "row": 197, "col": "D"},
        "senior_debt_base_rate":    {"value": cell(202, 3), "row": 202, "col": "D"},
        "senior_debt_margin_bps":   {"value": cell(203, 3), "row": 203, "col": "D"},
        "senior_dscr_covenant":     {"value": cell(221, 3), "row": 221, "col": "D"},
        "senior_lockup_dscr":       {"value": cell(223, 3), "row": 223, "col": "D"},
        # SHL
        "shl_amount_keur":          {"value": cell(325, 3), "row": 325, "col": "D"},
        "shl_interest_rate":        {"value": cell(328, 5), "row": 328, "col": "F"},
        # Equity
        "equity_capital_keur":      {"value": cell(312, 3), "row": 312, "col": "D"},
        # CAPEX totals
        "total_capex_keur":         {"value": cell(45, 2), "row": 45, "col": "C"},
    }

    # -----------------------------------------------------------------------
    # CAPEX line items (rows 22-44 in Inputs; individual line descriptions)
    # -----------------------------------------------------------------------
    capex_input_rows = {
        "Production Units": (23, "C.01"),
        "EPC Contract": (24, "C.02"),
        "EPC other costs": (25, "C.03"),
        "Grid connection": (26, "C.04"),
        "Investments to prepare operation phase": (27, "C.05"),
        "Insurances": (28, "C.06"),
        "Project finance costs due at closing": (30, "C.08"),
        "Construction Management": (34, "C.09"),
        "Contingencies": (35, "C.10"),
        "Project Acquisition / Project Development": (37, "C.11"),
        "Project Rights": (38, "C.12"),
        "IDCs": (39, "C.IDC"),
        "Commitment Fees": (40, "C.CF"),
        "Bank Fees": (41, "C.BF"),
        "VAT Costs": (44, "C.VAT"),
    }
    capex_items: dict = {}
    for name, (r, code) in capex_input_rows.items():
        amount = cell(r, 2)
        capex_items[code] = {
            "label": name,
            "amount_keur": float(amount) if isinstance(amount, (int, float)) else None,
            "sheet": "Inputs", "row": r, "col": "C",
        }
    inputs["capex_items_from_inputs"] = capex_items

    # -----------------------------------------------------------------------
    # OPEX annual line items (rows 146-161)
    # -----------------------------------------------------------------------
    opex_rows = [
        (146, "B.01", "Technical Management"),
        (147, "B.02", "Infrastructure Maintenance"),
        (148, "B.03", "Maintain Site"),
        (149, "B.04", "Clean Material"),
        (150, "B.05", "Security"),
        (151, "B.06", "Insurance"),
        (152, "B.07", "Lease & property Tax"),
        (153, "B.08", "Power Expenses"),
        (154, "B.09", "Fees"),
        (155, "B.10", "Audit & Accounting & Legal Fees"),
        (156, "B.11", "Bank Fees"),
        (157, "B.12", "Environmental & Social management"),
        (158, "B.13", "Contingencies"),
        (159, "B.14", "Taxes"),
        (160, "B.15", "Salary and payroll Tax"),
    ]
    opex_annual: dict = {}
    for r, code, label in opex_rows:
        y_vals = [cell(r, c) for c in range(4, 10)]  # cols 5-10 = years 1-6
        y1 = y_vals[0] if y_vals else None
        opex_annual[code] = {
            "label": label,
            "year1_keur": float(y1) if isinstance(y1, (int, float)) else None,
            "years_1_to_6_keur": [float(v) if isinstance(v, (int, float)) else None
                                   for v in y_vals],
            "sheet": "Inputs", "row": r,
        }
    inputs["opex_annual_items"] = opex_annual

    return inputs


def _read_capex_sheet(wb) -> dict:
    ws = wb["CapEx"]
    rows = {r: tuple(row) for r, row in enumerate(
        ws.iter_rows(max_row=200, max_col=30, values_only=True), start=1)}

    def cell(r, c): return _scalar(rows.get(r, ()), c)

    items: dict = {}
    code_rows = [
        ("C.01", 6,  "Production Units"),
        ("C.02", 9,  "EPC Contract"),
        ("C.03a", 13, "EPC other costs"),
        ("C.04", 18, "Grid connection"),
        ("C.03b", 24, "Other costs for construction"),
        ("C.05", 31, "Investments to prepare operation phase"),
        ("C.06", 47, "Insurances"),
        ("C.07", 54, "Lease and Property Tax"),
        ("C.08", 57, "Project finance costs due at closing"),
    ]
    for code, r, label in code_rows:
        amount = cell(r, 2)
        dep_life = cell(r, 1)
        items[code] = {
            "label": label,
            "amount_keur": float(amount) if isinstance(amount, (int, float)) else None,
            "dep_life_years": int(dep_life) if isinstance(dep_life, int) else dep_life,
            "sheet": "CapEx", "row": r,
        }

    # Total CAPEX from CapEx header row 4
    total = cell(4, 2)
    return {
        "_source": {"sheet": "CapEx"},
        "total_hard_capex_keur": float(total) if isinstance(total, (int, float)) else None,
        "items": items,
    }


def _read_schedule(wb, sheet_name: str, row_map: dict[str, int]) -> dict:
    """Generic period-schedule reader.  row_map: label → 1-based row number."""
    ws = wb[sheet_name]
    all_rows = list(ws.iter_rows(max_row=max(row_map.values()) + 2,
                                  max_col=_PERIOD_COL_OFFSET + _N_PERIODS + 1,
                                  values_only=True))
    result: dict = {"_source": {"sheet": sheet_name}}
    for label, r in row_map.items():
        row = all_rows[r - 1] if r - 1 < len(all_rows) else ()
        result[label] = _row_to_periods(row)
    return result


def _read_cf(wb) -> dict:
    row_map = {
        "bop_date": 1,
        "eop_date": 2,
        "calendar_year": 3,
        "operation_period_fraction": 7,
        "is_project_life": 6,
        "production_mwh": 21,
        "operating_revenues_keur": 23,
        "ppa_sales_keur": 24,
        "production_to_ppa_mwh": 25,
        "tariff_indexed_eur_mwh": 26,
        "operating_expenses_keur": 49,
        "ebitda_keur": 51,
        "tax_technical_management_keur": 56,
        "tax_infrastructure_maintenance_keur": 57,
        "tax_maintain_site_keur": 58,
        "tax_clean_material_keur": 59,
        "tax_security_keur": 60,
        "tax_insurance_keur": 61,
        "tax_lease_property_keur": 62,
        "tax_power_expenses_keur": 63,
        "tax_fees_keur": 64,
        "tax_audit_legal_keur": 65,
        "tax_bank_fees_keur": 66,
        "tax_env_social_keur": 67,
        "tax_contingencies_keur": 68,
        "corporate_income_tax_keur": 77,
        "fcf_for_banks_keur": 79,
        "senior_debt_service_keur": 80,
        "free_cash_flow_for_junior_keur": 94,
        "free_cash_flow_for_shl_keur": 112,
        "free_cash_flow_for_dividends_keur": 116,
    }
    ws = wb["CF"]
    all_rows = list(ws.iter_rows(max_row=max(row_map.values()) + 2,
                                  max_col=_PERIOD_COL_OFFSET + _N_PERIODS + 2,
                                  values_only=True))
    result: dict = {"_source": {"sheet": "CF"}}
    for label, r in row_map.items():
        row = all_rows[r - 1] if r - 1 < len(all_rows) else ()
        if label in ("bop_date", "eop_date"):
            vals = []
            for p in range(_N_PERIODS):
                col = _PERIOD_COL_OFFSET + p
                v = row[col] if col < len(row) else None
                vals.append(_date_str(v))
            result[label] = vals
        else:
            result[label] = _row_to_periods(row)
    # OPEX by individual item (CF rows 56-68), sign as stored (negative)
    opex_items_period: dict = {}
    item_rows = {
        "B.01": 56, "B.02": 57, "B.03": 58, "B.04": 59, "B.05": 60,
        "B.06": 61, "B.07": 62, "B.08": 63, "B.09": 64, "B.10": 65,
        "B.11": 66, "B.12": 67, "B.13": 68,
    }
    for code, r in item_rows.items():
        row_data = all_rows[r - 1] if r - 1 < len(all_rows) else ()
        vals = _row_to_periods(row_data)
        opex_items_period[code] = vals
    result["opex_items_period_keur"] = opex_items_period
    return result


def _read_ds(wb) -> dict:
    row_map = {
        "bop_date": 1,
        "eop_date": 2,
        "sd_period_fraction": 6,
        "dscr_target": 22,
        "cfads_for_sd_keur": 20,
        "sd_beginning_keur": 50,
        "sd_funding_keur": 51,
        "sd_principal_keur": 52,
        "sd_net_interest_keur": 53,
        "sd_gross_interest_keur": 55,
        "sd_ending_keur": 56,
        "sd_service_keur": 57,
        "shl_beginning_keur": 123,
        "shl_funding_keur": 124,
        "shl_net_interest_keur": 125,
        "shl_interest_capitalised_keur": 128,
        "shl_ending_keur": 129,
        "shl_service_keur": 130,
    }
    return _read_schedule(wb, "DS", row_map)


def _read_pl(wb) -> dict:
    row_map = {
        "bop_date": 1,
        "eop_date": 2,
        "total_revenues_keur": 8,
        "operating_expenses_keur": 10,
        "local_tax_keur": 11,
        "depreciation_keur": 13,
        "total_expenses_keur": 14,
        "ebit_keur": 16,
        "senior_interests_keur": 24,
        "shl_interests_keur": 27,
        "financial_earnings_keur": 30,
        "earnings_before_tax_keur": 32,
        "fiscal_reintegration_keur": 34,
        "taxable_income_keur": 35,
        "losses_carryforward_keur": 39,
        "taxable_profit_keur": 41,
        "corporate_income_tax_keur": 44,
        "net_income_keur": 46,
        "net_dividends_keur": 50,
    }
    return _read_schedule(wb, "P&L", row_map)


def _read_dep(wb) -> dict:
    row_map = {
        "bop_date": 1,
        "eop_date": 2,
        "dep_production_units_keur": 7,
        "dep_epc_contract_keur": 8,
        "dep_epc_other_keur": 9,
        "dep_grid_connection_keur": 10,
        "dep_investments_operation_keur": 11,
        "dep_insurances_keur": 12,
        "dep_project_finance_keur": 14,
        "dep_construction_mgmt_keur": 18,
        "dep_contingencies_keur": 19,
        "dep_project_acquisition_keur": 21,
        "dep_project_rights_keur": 22,
        "dep_idc_keur": 23,
        "dep_commitment_fees_keur": 24,
        "dep_bank_fees_keur": 25,
        "dep_vat_keur": 28,
        "dep_total_keur": 30,
    }
    return _read_schedule(wb, "Dep", row_map)


# ---------------------------------------------------------------------------
# SHA-256 of the workbook file
# ---------------------------------------------------------------------------

def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def extract(workbook_path: pathlib.Path) -> dict:
    import openpyxl

    wb = openpyxl.load_workbook(
        workbook_path, read_only=True, data_only=True, keep_vba=False
    )
    try:
        payload: dict = {
            "_meta": {
                "extractor_version": _EXTRACTOR_VERSION,
                "source_filename": workbook_path.name,
                "source_sha256": _sha256(workbook_path),
                "sheets_inspected": wb.sheetnames,
            },
            "inputs": _read_inputs(wb),
            "capex_sheet": _read_capex_sheet(wb),
            "cf": _read_cf(wb),
            "ds": _read_ds(wb),
            "pl": _read_pl(wb),
            "dep": _read_dep(wb),
        }
    finally:
        wb.close()
    return payload


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m finco_recon.extract_oborovo_excel",
        description="Extract Oborovo financial truth from the authoritative XLSM.",
    )
    parser.add_argument("--workbook", required=True, type=pathlib.Path,
                        help="Path to the source XLSM workbook")
    parser.add_argument("--output", required=True, type=pathlib.Path,
                        help="Output JSON fixture path")
    args = parser.parse_args(argv)

    wb_path: pathlib.Path = args.workbook
    if not wb_path.exists():
        print(f"STOP\nSOURCE_WORKBOOK_REQUIRED\n\nFile not found: {wb_path}",
              file=sys.stderr)
        return 1

    print(f"Extracting from: {wb_path.name}", flush=True)
    print(f"SHA-256: ...", flush=True)

    try:
        payload = extract(wb_path)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        import traceback; traceback.print_exc()
        return 2

    sha = payload["_meta"]["source_sha256"]
    print(f"SHA-256: {sha}", flush=True)

    # Write timestamp separately so financial payload is deterministic
    output_path: pathlib.Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    out_doc = {
        "_extraction_timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
        **payload,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(out_doc, f, indent=2, default=str)

    print(f"Written: {output_path}", flush=True)
    sheets = payload["_meta"]["sheets_inspected"]
    print(f"Sheets inspected ({len(sheets)}): {', '.join(sheets)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
