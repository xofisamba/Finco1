"""finco_recon.workbook — Build the Oborovo Excel↔Python reconciliation workbook.

Generates a 16-sheet audit-grade workbook using openpyxl.
All model periods run horizontally. No financial formulas are modified.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

from finco_recon.catalog import CATALOG, LineItem, get_catalog_by_section, get_item
from finco_recon.materiality import MaterialitySettings, DEFAULT_MATERIALITY
from finco_recon.sources import OborovoSources, ExcelData, EngineData, LegacyData

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASELINE_ID = "oborovo"
UNAVAILABLE = "UNAVAILABLE"
OUT_OF_SCOPE = "OUT OF CLEAN ENGINE SCOPE"

# Classification → fill colour (hex, no #)
CLASS_FILL = {
    "MATCH":                    "C6EFCE",
    "PYTHON BUG":               "FF9999",
    "EXCEL BUG":                "FFD966",
    "POLICY DIFFERENCE":        "BDD7EE",
    "UNRESOLVED SOURCE":        "E2EFDA",
    "TIMING / ROUNDING":        "FFFFCC",
    "OUT OF CLEAN ENGINE SCOPE":"D9D9D9",
    # blank = OPEN — ROOT CAUSE REQUIRED (no fill — white)
    "":                         "FFFFFF",
}

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def _font(bold: bool = False, size: int = 9, color: str = "000000") -> Font:
    return Font(name="Calibri", bold=bold, size=size, color=color)

def _fill(hex_color: str) -> PatternFill:
    return PatternFill("solid", fgColor=hex_color)

def _align(h: str = "left", v: str = "center", wrap: bool = False) -> Alignment:
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)

def _thin_border() -> Border:
    s = Side(style="thin", color="CCCCCC")
    return Border(left=s, right=s, top=s, bottom=s)

HEADER_FILL  = _fill("2F4F6F")  # dark navy
SECTION_FILL = _fill("4472C4")  # blue
EXCEL_FILL   = _fill("EAF0FB")  # light blue
PYTHON_FILL  = _fill("EBF7EE")  # light green
DELTA_FILL   = _fill("FFF9E6")  # light amber
DPCT_FILL    = _fill("FFF3CD")  # lighter amber
GREY_FILL    = _fill("F2F2F2")

KEUR_FMT  = '#,##0.0'
INT_FMT   = '#,##0'
PCT_FMT   = '0.00%'
DSCR_FMT  = '0.000'
DATE_FMT  = 'DD-MMM-YY'
FRAC_FMT  = '0.0000'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe(val: Any) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _delta(excel: float | None, python: float | None) -> float | None:
    if excel is None or python is None:
        return None
    return python - excel


def _delta_pct(delta: float | None, excel: float | None) -> float | None:
    if delta is None or excel is None:
        return None
    ref = abs(excel)
    if ref < 1e-9:
        return None
    return delta / ref


def _classify(
    item: LineItem,
    delta: float | None,
    excel: float | None,
    python: float | None,
    mat: MaterialitySettings,
    documented_cls: str | None = None,
) -> str:
    """Classify a delta. Only assigns a non-blank classification when evidence exists.

    A material delta without a documented root cause returns "" (blank),
    meaning OPEN — ROOT CAUSE REQUIRED. This is never auto-assigned to
    POLICY DIFFERENCE based on magnitude alone.
    """
    if not item.in_clean_engine:
        return "OUT OF CLEAN ENGINE SCOPE"
    if excel is None and python is None:
        return "UNRESOLVED SOURCE"
    if excel is None:
        return "UNRESOLVED SOURCE"
    if python is None:
        return "OUT OF CLEAN ENGINE SCOPE"
    if delta is None:
        return "UNRESOLVED SOURCE"
    if not mat.is_material(delta, excel, python, item.unit):
        return "MATCH"
    # Material delta: return documented classification only if evidence exists
    if documented_cls:
        return documented_cls
    # No root cause established yet → blank = OPEN
    return ""


def _num_fmt(unit: str) -> str:
    if unit in ("kEUR",):
        return KEUR_FMT
    if unit in ("%",):
        return PCT_FMT
    if unit in ("x",):
        return DSCR_FMT
    if unit == "MWh":
        return INT_FMT
    if unit == "frac":
        return FRAC_FMT
    if unit == "days":
        return INT_FMT
    if unit == "MW":
        return KEUR_FMT
    return KEUR_FMT


def _set_cell(ws, row: int, col: int, value: Any, *, bold: bool = False,
              fill: PatternFill | None = None, fmt: str | None = None,
              align: str = "left", font_color: str = "000000",
              font_size: int = 9) -> None:
    cell = ws.cell(row=row, column=col, value=value)
    cell.font = _font(bold=bold, size=font_size, color=font_color)
    if fill:
        cell.fill = fill
    if fmt:
        cell.number_format = fmt
    cell.alignment = _align(h=align, v="center")


def _header_row(ws, values: list, row: int = 1, fill: PatternFill | None = None) -> None:
    f = fill or HEADER_FILL
    for col, val in enumerate(values, 1):
        cell = ws.cell(row=row, column=col, value=val)
        cell.font = _font(bold=True, size=9, color="FFFFFF")
        cell.fill = f
        cell.alignment = _align(h="center", v="center")


def _set_col_widths(ws, widths: dict[int, float]) -> None:
    for col, w in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = w


def _freeze(ws, cell: str) -> None:
    ws.freeze_panes = cell


def _autofilter(ws, first_row: int, last_col: int) -> None:
    ws.auto_filter.ref = f"A{first_row}:{get_column_letter(last_col)}{first_row}"


def _write_period_headers(ws, engine_periods: list[EngineData], header_row: int, start_col: int) -> None:
    for i, ep in enumerate(engine_periods):
        col = start_col + i
        cell = ws.cell(row=header_row, column=col, value=ep.period_end)
        cell.font = _font(bold=True, size=8, color="FFFFFF")
        cell.fill = HEADER_FILL
        cell.alignment = _align(h="center", v="center")
        cell.number_format = DATE_FMT
        ws.column_dimensions[get_column_letter(col)].width = 10.5


def _section_header(ws, row: int, label: str, n_cols: int) -> None:
    for c in range(1, n_cols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = SECTION_FILL
        cell.font = _font(bold=True, size=9, color="FFFFFF")
    ws.cell(row=row, column=2, value=label)
    ws.cell(row=row, column=2).alignment = _align(h="left", v="center")


def _write_recon_block(
    ws,
    label: str,
    code: str,
    unit: str,
    excel_vals: list[float | None],
    python_vals: list[float | None],
    start_row: int,
    data_col: int,
    mat: MaterialitySettings,
    item: LineItem | None = None,
    classification: str | None = None,
) -> int:
    """Write Excel / Python / Delta / Delta% rows for one line item.

    Returns next available row.
    """
    fmt = _num_fmt(unit)
    n = len(excel_vals)

    for view_idx, (view_label, vals, row_fill) in enumerate([
        ("Excel",   excel_vals,  EXCEL_FILL),
        ("Python",  python_vals, PYTHON_FILL),
    ]):
        r = start_row + view_idx
        ws.cell(row=r, column=1, value=code if view_idx == 0 else "").font = _font(size=8)
        ws.cell(row=r, column=1).value = code if view_idx == 0 else ""
        ws.cell(row=r, column=2, value=label if view_idx == 0 else "").font = _font(bold=(view_idx == 0), size=9)
        ws.cell(row=r, column=2).value = label if view_idx == 0 else ""
        ws.cell(row=r, column=3, value=view_label).font = _font(size=8)
        ws.cell(row=r, column=3).fill = row_fill
        ws.cell(row=r, column=4, value=unit).font = _font(size=8)
        for ci in range(n):
            v = vals[ci]
            cell = ws.cell(row=r, column=data_col + ci)
            if v is None:
                cell.value = None
            elif isinstance(v, str):
                cell.value = v
            else:
                cell.value = v
                cell.number_format = fmt
            cell.fill = row_fill
            cell.font = _font(size=8)
            cell.alignment = _align(h="right", v="center")

    # Delta row
    r_delta = start_row + 2
    ws.cell(row=r_delta, column=2, value="").font = _font(size=8)
    ws.cell(row=r_delta, column=3, value="Delta").font = _font(bold=True, size=8)
    ws.cell(row=r_delta, column=3).fill = DELTA_FILL
    ws.cell(row=r_delta, column=4, value=unit).font = _font(size=8)
    for ci in range(n):
        ev = excel_vals[ci]
        pv = python_vals[ci]
        d = _delta(ev if isinstance(ev, (int, float)) else None,
                   pv if isinstance(pv, (int, float)) else None)
        cell = ws.cell(row=r_delta, column=data_col + ci)
        if d is None:
            cell.value = None
        else:
            cell.value = d
            cell.number_format = fmt
            # Colour: red if material and negative, green if material and positive
            if item and mat.is_material(d, ev, pv, unit):
                if d < 0:
                    cell.fill = _fill("FF9999")
                elif d > 0:
                    cell.fill = _fill("C6EFCE")
                else:
                    cell.fill = DELTA_FILL
            else:
                cell.fill = DELTA_FILL
        cell.font = _font(size=8)
        cell.alignment = _align(h="right", v="center")

    # Delta% row
    r_dpct = start_row + 3
    ws.cell(row=r_dpct, column=3, value="Delta %").font = _font(size=8)
    ws.cell(row=r_dpct, column=3).fill = DPCT_FILL
    ws.cell(row=r_dpct, column=4, value="%").font = _font(size=8)
    for ci in range(n):
        ev = excel_vals[ci]
        pv = python_vals[ci]
        d = _delta(ev if isinstance(ev, (int, float)) else None,
                   pv if isinstance(pv, (int, float)) else None)
        dp = _delta_pct(d, ev if isinstance(ev, (int, float)) else None)
        cell = ws.cell(row=r_dpct, column=data_col + ci)
        if dp is None:
            cell.value = None
        else:
            cell.value = dp
            cell.number_format = PCT_FMT
        cell.fill = DPCT_FILL
        cell.font = _font(size=8)
        cell.alignment = _align(h="right", v="center")

    return start_row + 4


# ---------------------------------------------------------------------------
# Sheet builders
# ---------------------------------------------------------------------------

def _build_exec_recon(wb: Workbook, src: OborovoSources, mat: MaterialitySettings) -> None:
    ws = wb.create_sheet("00_EXEC_RECON")
    ws.sheet_view.showGridLines = False

    headers = ["Section", "Line Item", "Excel Value", "Python Value",
               "Delta", "Delta %", "Max Period |Delta|", "Status", "Classification",
               "Notes / Root Cause"]
    _header_row(ws, headers)

    def _tot(vals: list) -> float | None:
        filtered = [v for v in vals if v is not None]
        return sum(filtered) if filtered else None

    def _max_abs_delta(excel_list: list, python_list: list) -> float | None:
        deltas = []
        for ev, pv in zip(excel_list, python_list):
            d = _delta(_safe(ev), _safe(pv))
            if d is not None:
                deltas.append(abs(d))
        return max(deltas) if deltas else None

    excel_p = src.excel
    eng_p   = src.engine

    # Period-level lists for max-delta calculation
    xl_rev   = [e.revenue_keur for e in excel_p]
    py_rev   = [e.revenue_keur for e in eng_p]
    xl_opex  = [e.opex_keur for e in excel_p]
    py_opex  = [e.opex_keur for e in eng_p]
    xl_ebitda = [e.ebitda_keur for e in excel_p]
    py_ebitda = [e.ebitda_keur for e in eng_p]
    xl_ctax  = [e.cash_tax_keur for e in excel_p]
    py_ctax  = [e.corporate_tax_cash_keur for e in eng_p]
    xl_cfads = [e.cfads_keur for e in excel_p]
    py_cfads = [e.cfads_keur for e in eng_p]
    xl_sint  = [e.senior_interest_keur for e in excel_p]
    py_sint  = [e.sd_interest_keur for e in eng_p]
    xl_dep   = [e.depreciation_keur for e in excel_p]
    py_dep   = [e.book_depreciation_keur for e in eng_p]

    # Excel EBITDA identity: Revenue - OPEX should equal EBITDA in the CF sheet
    xl_rev_tot   = _tot(xl_rev)
    xl_opex_tot  = _tot(xl_opex)
    xl_ebitda_tot = _tot(xl_ebitda)
    xl_ebitda_computed = (xl_rev_tot - xl_opex_tot) if (xl_rev_tot is not None and xl_opex_tot is not None) else None

    py_rev_tot   = _tot(py_rev)
    py_opex_tot  = _tot(py_opex)
    py_ebitda_tot = _tot(py_ebitda)

    # Python average DSCR: mean over periods with active debt service (sd_dscr > 0)
    dscr_vals = [e.sd_dscr for e in eng_p if e.sd_dscr is not None and e.sd_dscr > 0]
    py_avg_dscr = sum(dscr_vals) / len(dscr_vals) if dscr_vals else None
    py_min_dscr = min(dscr_vals) if dscr_vals else None

    # COD date: Excel from golden (2030-06-29), Python from engine period_start
    py_cod = src.engine[0].period_start if eng_p else None
    cod_match = src.cod_date == py_cod
    cod_cls = "MATCH" if cod_match else ""

    rows_data = [
        # (section, line_item, excel_val, python_val, max_period_delta, classification, notes)
        ("TIMELINE",     "Operating periods",
         float(len(excel_p)), float(len(eng_p)), None, "MATCH", ""),
        ("TIMELINE",     "COD date (Excel vs engine period start)",
         src.cod_date, py_cod, None, cod_cls,
         "Excel COD from oborovo_golden.json; Python from engine first period_start" if not cod_match else ""),
        ("PRODUCTION",   "Total net production (MWh)",
         None, _tot([e.production_mwh for e in eng_p]), None, "UNRESOLVED SOURCE",
         "Production not available in excel_oborovo_full_model_extract.json"),
        ("PRODUCTION",   "Price (EUR/MWh)",
         None, None, None, "UNRESOLVED SOURCE",
         "Revenue price not available in Excel fixture; requires separate extraction"),
        ("REVENUE",      "Total operating revenue CF (kEUR)",
         xl_rev_tot, py_rev_tot, _max_abs_delta(xl_rev, py_rev), None,
         "Excel: CF.operating_revenues_keur; Python: engine revenue_keur"),
        ("OPEX",         "Total OPEX (kEUR)",
         xl_opex_tot, py_opex_tot, _max_abs_delta(xl_opex, py_opex), None,
         "Excel: abs(CF.operating_expenses_after_bank_tax_keur); Python: engine opex_keur"),
        ("EBITDA",       "Total EBITDA CF (kEUR) — direct",
         xl_ebitda_tot, py_ebitda_tot, _max_abs_delta(xl_ebitda, py_ebitda), None,
         "Excel: CF.ebitda_keur; Python: engine ebitda_keur"),
        ("EBITDA",       "Excel EBITDA identity: Revenue - OPEX (kEUR)",
         xl_ebitda_computed, xl_ebitda_tot, None,
         "MATCH" if (xl_ebitda_computed is not None and xl_ebitda_tot is not None and abs(xl_ebitda_computed - xl_ebitda_tot) < 1.0) else ("" if xl_ebitda_computed is not None else "UNRESOLVED SOURCE"),
         f"Computed={xl_ebitda_computed:.1f} vs Direct={xl_ebitda_tot:.1f}" if (xl_ebitda_computed is not None and xl_ebitda_tot is not None) else "Cannot verify — missing data"),
        ("CAPEX",        "Total CAPEX (kEUR)",
         src.excel_total_capex_keur or None, src.total_capex_keur, None, "POLICY DIFFERENCE",
         "Excel: oborovo_golden.json total_capex_keur; Python: factory total_capex. Difference = SHL IDC capitalised in Excel only"),
        ("IDC",          "Bank IDC (kEUR)",
         None, src.idc_keur, None, "UNRESOLVED SOURCE",
         "Excel IDC not separately extracted in fixture; Python from factory idc_keur"),
        ("DEPRECIATION", "Total book depreciation (kEUR)",
         _tot(xl_dep), _tot(py_dep), _max_abs_delta(xl_dep, py_dep), None,
         "Excel: P&L.depreciation_keur; Python: engine book_depreciation_keur"),
        ("TAX",          "Total cash tax (kEUR)",
         _tot(xl_ctax), _tot(py_ctax), _max_abs_delta(xl_ctax, py_ctax), None,
         "Excel: abs(CF.corporate_income_tax_keur); Python: engine corporate_tax_cash_keur"),
        ("CFADS",        "Total CFADS (kEUR)",
         _tot(xl_cfads), _tot(py_cfads), _max_abs_delta(xl_cfads, py_cfads), None,
         "Excel: CF.free_cash_flow_for_banks_keur; Python: engine cfads_keur"),
        ("SENIOR DEBT",  "Debt size at COD (kEUR)",
         src.excel_total_debt_keur or None, src.engine_debt_size_keur, None, "POLICY DIFFERENCE",
         "Excel uses GEARING CAP (75.24% × CAPEX); Python uses DSCR SCULPTED at 1.15x"),
        ("SENIOR DEBT",  "Target DSCR",
         src.excel_target_dscr or None, 1.15, None, "MATCH",
         "Excel: DS.senior_debt_dscr_target; Python: SeniorDebtPolicy.target_dscr=1.15"),
        ("SENIOR DEBT",  "Min DSCR",
         src.excel_min_dscr or None, py_min_dscr, None, None,
         "Excel: CF.minimum_senior_dscr_period min; Python: min of engine sd_dscr (active DS periods)"),
        ("SENIOR DEBT",  "Avg DSCR (active DS periods)",
         src.excel_avg_dscr or None, py_avg_dscr, None, None,
         "Excel: average of CF.average_senior_dscr_period; Python: mean of engine sd_dscr (sd_dscr>0)"),
        ("SENIOR INTEREST", "Total senior interest (kEUR)",
         _tot(xl_sint), _tot(py_sint), _max_abs_delta(xl_sint, py_sint), None,
         "Excel: DS.senior_net_interest_keur; Python: engine sd_interest_keur"),
        ("SHL INTEREST", "Total SHL interest (kEUR)",
         _tot([e.shl_interest_keur for e in excel_p]), UNAVAILABLE, None,
         "OUT OF CLEAN ENGINE SCOPE",
         "Excel: P&L.shareholder_loan_interests_keur; Python: not modelled in clean engine"),
        ("CASH FLOW",    "Total FCF for distribution (kEUR)",
         _tot([e.free_cash_flow_keur for e in excel_p]), UNAVAILABLE, None,
         "OUT OF CLEAN ENGINE SCOPE",
         "Excel: CF.free_cash_flow_for_distribution_keur; Python: not modelled in clean engine"),
    ]

    for r_idx, row_tuple in enumerate(rows_data, 2):
        section, line, excel_v, python_v, max_d, cls_override, notes = row_tuple
        ev = _safe(excel_v) if not isinstance(excel_v, str) else None
        pv = _safe(python_v) if not isinstance(python_v, str) else None
        d = _delta(ev, pv)
        dp = _delta_pct(d, ev)
        is_mat = mat.is_material(d, ev, pv) if d is not None else False

        # Determine classification
        if cls_override is not None:
            cls = cls_override
        elif ev is None:
            cls = "UNRESOLVED SOURCE"
        elif pv is None:
            cls = "OUT OF CLEAN ENGINE SCOPE"
        elif d is not None and not is_mat:
            cls = "MATCH"
        else:
            cls = ""  # OPEN — ROOT CAUSE REQUIRED

        status = "OPEN" if (cls == "" and is_mat) else ("MATERIAL" if is_mat else "OK")

        fill = _fill(CLASS_FILL.get(cls, "FFFFFF"))
        row_fill = _fill("FFF0F0") if (is_mat and cls == "") else None

        ws.cell(row=r_idx, column=1, value=section).font = _font(bold=True, size=9)
        ws.cell(row=r_idx, column=2, value=line).font = _font(size=9)
        c3 = ws.cell(row=r_idx, column=3, value=ev if ev is not None else (excel_v if isinstance(excel_v, str) else None))
        c3.font = _font(size=9)
        if ev is not None: c3.number_format = KEUR_FMT
        c4 = ws.cell(row=r_idx, column=4, value=pv if pv is not None else (python_v if isinstance(python_v, str) else None))
        c4.font = _font(size=9)
        if pv is not None: c4.number_format = KEUR_FMT
        c5 = ws.cell(row=r_idx, column=5, value=d)
        c5.font = _font(size=9)
        if d is not None: c5.number_format = KEUR_FMT
        c6 = ws.cell(row=r_idx, column=6, value=dp)
        c6.font = _font(size=9)
        if dp is not None: c6.number_format = PCT_FMT
        c7 = ws.cell(row=r_idx, column=7, value=max_d)
        c7.font = _font(size=9)
        if max_d is not None: c7.number_format = KEUR_FMT
        ws.cell(row=r_idx, column=8, value=status).font = _font(size=9)
        cls_cell = ws.cell(row=r_idx, column=9, value=cls if cls else "OPEN — ROOT CAUSE REQUIRED")
        cls_cell.font = _font(size=9)
        cls_cell.fill = fill
        ws.cell(row=r_idx, column=10, value=notes).font = _font(size=8)
        if row_fill:
            for c in range(1, 9):
                ws.cell(row=r_idx, column=c).fill = row_fill

    _set_col_widths(ws, {1: 16, 2: 44, 3: 16, 4: 16, 5: 12, 6: 10, 7: 14, 8: 10, 9: 28, 10: 60})
    _freeze(ws, "A2")
    _autofilter(ws, 1, 10)


def _build_inputs_recon(wb: Workbook, src: OborovoSources, mat: MaterialitySettings) -> None:
    ws = wb.create_sheet("01_INPUTS_RECON")
    ws.sheet_view.showGridLines = False
    _header_row(ws, ["Code", "Input", "Excel", "Python", "Delta", "Status"])

    def row(ws, r, code, label, excel_v, python_v, fmt=KEUR_FMT):
        ev = _safe(excel_v)
        pv = _safe(python_v)
        d = _delta(ev, pv)
        is_mat = mat.is_material(d, ev, pv) if d is not None else False
        status = "MATERIAL" if is_mat else "MATCH" if d is not None and abs(d) < 1e-6 else "REVIEW"
        ws.cell(row=r, column=1, value=code).font = _font(size=8)
        ws.cell(row=r, column=2, value=label).font = _font(size=9)
        c3 = ws.cell(row=r, column=3, value=ev if ev is not None else excel_v)
        c3.font = _font(size=9); c3.number_format = fmt if ev is not None else "@"
        c4 = ws.cell(row=r, column=4, value=pv if pv is not None else python_v)
        c4.font = _font(size=9); c4.number_format = fmt if pv is not None else "@"
        c5 = ws.cell(row=r, column=5, value=d); c5.font = _font(size=9)
        if d is not None: c5.number_format = fmt
        ws.cell(row=r, column=6, value=status).font = _font(size=9)
        if is_mat:
            for c in range(1, 7): ws.cell(row=r, column=c).fill = _fill("FFC7CE")

    UNRES = "UNRESOLVED — not in Excel fixture"

    r = 2
    def sec(label):
        nonlocal r
        ws.cell(row=r, column=1, value="").fill = SECTION_FILL
        ws.cell(row=r, column=2, value=label).font = _font(bold=True, size=9, color="FFFFFF")
        ws.cell(row=r, column=2).fill = SECTION_FILL
        for c in range(3, 7): ws.cell(row=r, column=c).fill = SECTION_FILL
        r += 1

    # Excel-provenance: oborovo_golden.json was extracted from the source Excel workbook.
    # Python-provenance: app.project_factories (factory config / engine policy).
    # Where both come from the same golden JSON, the Python side is also golden-derived.
    # Where only golden exists (no independent factory check), mark UNRESOLVED SOURCE.

    sec("— PROJECT / TIMELINE (Excel: oborovo_golden.json) —")
    row(ws, r, "T.01", "Capacity (MW)",        src.capacity_mw,         src.capacity_mw,         KEUR_FMT); r += 1
    row(ws, r, "T.02", "Financial close",       src.financial_close,     src.financial_close,     "@"); r += 1
    row(ws, r, "T.03", "COD date",              src.cod_date,            src.engine[0].period_start if src.engine else src.cod_date, "@"); r += 1
    row(ws, r, "T.04", "Horizon (years)",       src.horizon_years,       src.horizon_years,       INT_FMT); r += 1
    row(ws, r, "T.05", "Construction (months)", src.construction_months, src.construction_months, INT_FMT); r += 1
    row(ws, r, "T.06", "Period frequency",      "Semestrial",            "Semestrial",            "@"); r += 1

    sec("— PRODUCTION (no Excel fixture source) —")
    row(ws, r, "P.01", "P50 operating hours [UNRESOLVED]",  UNRES, 1494.0, "@"); r += 1
    row(ws, r, "P.02", "PV degradation (%/yr) [UNRESOLVED]",UNRES, 0.004,  "@"); r += 1
    row(ws, r, "P.03", "Plant availability [UNRESOLVED]",   UNRES, 0.99,   "@"); r += 1
    row(ws, r, "P.04", "Grid availability [UNRESOLVED]",    UNRES, 0.99,   "@"); r += 1

    sec("— PRICE / REVENUE (Excel: oborovo_golden.json) —")
    row(ws, r, "R.01", "PPA tariff (EUR/MWh)",  src.ppa_tariff_eur_mwh, src.ppa_tariff_eur_mwh, KEUR_FMT); r += 1
    row(ws, r, "R.02", "PPA term (years)",       src.ppa_term_years,     src.ppa_term_years,     INT_FMT); r += 1
    row(ws, r, "R.03", "PPA indexation (%/yr)",  src.ppa_index,          src.ppa_index,          PCT_FMT); r += 1
    row(ws, r, "R.04", "Effective price (EUR/MWh) [UNRESOLVED]", UNRES, UNRES, "@"); r += 1

    sec("— OPEX (Y1 kEUR) — Excel: not in fixture; Python: app.project_factories —")
    for item in src.opex_items:
        row(ws, r, item["code"], item["name"] + " Y1 kEUR [UNRESOLVED Excel]", UNRES, item["y1_keur"], KEUR_FMT); r += 1
        row(ws, r, "",           item["name"] + " inflation [UNRESOLVED Excel]", UNRES, item["inflation"], "@"); r += 1

    sec("— CAPEX (kEUR) — Excel: golden total only; per-item from Python factory —")
    for item in src.capex_items:
        row(ws, r, item["code"], item["name"] + " [UNRESOLVED Excel]", UNRES, item["amount_keur"], KEUR_FMT); r += 1
    row(ws, r, "C.00", "Total Hard CAPEX [UNRESOLVED Excel]", UNRES, src.hard_capex_keur, KEUR_FMT); r += 1
    row(ws, r, "C.IDC", "Bank IDC [UNRESOLVED Excel]",        UNRES, src.idc_keur,        KEUR_FMT); r += 1
    row(ws, r, "C.TOT", "Total CAPEX (Excel golden vs Python factory)",
        src.excel_total_capex_keur, src.total_capex_keur, KEUR_FMT); r += 1

    sec("— TAX — Excel: not in fixture; Python: tax_reference_inputs —")
    row(ws, r, "TX.01", "CIT rate [UNRESOLVED Excel]",               UNRES, 0.10,    "@"); r += 1
    row(ws, r, "TX.02", "Loss carryforward (yrs) [UNRESOLVED Excel]",UNRES, 5.0,    "@"); r += 1
    row(ws, r, "TX.03", "ATAD enabled [UNRESOLVED Excel]",           UNRES, "Yes",  "@"); r += 1
    row(ws, r, "TX.04", "ATAD EBITDA limit [UNRESOLVED Excel]",      UNRES, 0.30,   "@"); r += 1
    row(ws, r, "TX.05", "ATAD de minimis kEUR/yr [UNRESOLVED Excel]",UNRES, 3000.0, "@"); r += 1

    sec("— SENIOR DEBT (Excel: oborovo_golden.json; Python: SeniorDebtPolicy) —")
    row(ws, r, "SD.01", "Target DSCR",              src.excel_target_dscr, 1.15,         DSCR_FMT); r += 1
    row(ws, r, "SD.02", "Gearing ratio (Excel only)", 0.7524,               UNRES,        PCT_FMT); r += 1
    row(ws, r, "SD.03", "Debt size at COD (kEUR)",  src.excel_total_debt_keur, src.engine_debt_size_keur, KEUR_FMT); r += 1
    row(ws, r, "SD.04", "Fixed rate [UNRESOLVED Excel]",  UNRES, 0.0565,   "@"); r += 1
    row(ws, r, "SD.05", "Tenor (years) [UNRESOLVED Excel]", UNRES, 14.0,   "@"); r += 1
    row(ws, r, "SD.06", "Day count [UNRESOLVED Excel]",   UNRES, "ACT/365", "@"); r += 1
    row(ws, r, "SD.07", "Sizing mode",              "GEARING CAP (Excel)", "DSCR SCULPTED (Python)", "@"); r += 1

    sec("— SHL (Excel: oborovo_golden.json / SHL fixture) —")
    row(ws, r, "SH.01", "SHL amount at COD (kEUR)", src.shl_amount_keur,  UNRES, KEUR_FMT); r += 1
    row(ws, r, "SH.02", "SHL rate",                 src.shl_rate,         UNRES, PCT_FMT); r += 1
    row(ws, r, "SH.03", "SHL IDC capitalised (kEUR)",src.shl_idc_keur,    UNRES, KEUR_FMT); r += 1

    _set_col_widths(ws, {1: 8, 2: 40, 3: 18, 4: 18, 5: 14, 6: 12})
    _freeze(ws, "A2")
    _autofilter(ws, 1, 6)


def _build_horizontal_sheet(
    wb: Workbook,
    sheet_name: str,
    src: OborovoSources,
    mat: MaterialitySettings,
    blocks: list[dict],
) -> None:
    """Generic builder for all period-horizontal sheets.

    blocks = list of dicts:
        type: "section" | "item"
        For section: label: str
        For item: code, name, unit, excel_vals, python_vals, item (LineItem)
    """
    ws = wb.create_sheet(sheet_name)
    ws.sheet_view.showGridLines = False

    n = len(src.engine)
    HDR_ROW = 1
    DATA_START_COL = 5  # A=code B=name C=view D=unit E+...

    # Row 1: fixed headers
    for c, label in enumerate(["Code", "Line Item", "View", "Unit"], 1):
        cell = ws.cell(row=HDR_ROW, column=c, value=label)
        cell.font = _font(bold=True, size=9, color="FFFFFF")
        cell.fill = HEADER_FILL
        cell.alignment = _align(h="center", v="center")
    # Period date headers
    _write_period_headers(ws, src.engine, HDR_ROW, DATA_START_COL)

    # Fixed column widths
    _set_col_widths(ws, {1: 7, 2: 32, 3: 8, 4: 7})

    cur_row = 2
    for block in blocks:
        if block["type"] == "section":
            n_cols = DATA_START_COL + n
            for c in range(1, n_cols + 1):
                cell = ws.cell(row=cur_row, column=c)
                cell.fill = SECTION_FILL
                cell.font = _font(bold=True, size=9, color="FFFFFF")
            ws.cell(row=cur_row, column=2, value=block["label"])
            ws.cell(row=cur_row, column=2).alignment = _align(h="left", v="center")
            cur_row += 1
        else:
            excel_vals = block.get("excel_vals", [None] * n)
            python_vals = block.get("python_vals", [None] * n)
            item = block.get("item")
            cur_row = _write_recon_block(
                ws=ws,
                label=block["name"],
                code=block["code"],
                unit=block["unit"],
                excel_vals=excel_vals,
                python_vals=python_vals,
                start_row=cur_row,
                data_col=DATA_START_COL,
                mat=mat,
                item=item,
            )

    # Freeze first 4 cols + header row
    _freeze(ws, f"{get_column_letter(DATA_START_COL)}2")
    _autofilter(ws, HDR_ROW, DATA_START_COL - 1)


def _build_timeline_recon(wb: Workbook, src: OborovoSources, mat: MaterialitySettings) -> None:
    ws = wb.create_sheet("02_TIMELINE_RECON")
    ws.sheet_view.showGridLines = False

    n = len(src.engine)
    DATA_COL = 5
    _header_row(ws, ["Code", "Line Item", "View", "Unit"])
    _write_period_headers(ws, src.engine, 1, DATA_COL)
    _set_col_widths(ws, {1: 7, 2: 32, 3: 8, 4: 7})

    n = len(src.engine)
    none_n = [None] * n

    # TL.02 period-end date: available from Excel fixture (date column).
    # TL.01, TL.03, TL.04, TL.05: NOT in period_diagnostic_columns → UNRESOLVED SOURCE.
    items_def = [
        ("TL.01", "Period index",    "index",
         none_n,                                  [e.period_index for e in src.engine]),
        ("TL.02", "Period end date", "date",
         [ep.period_end for ep in src.excel],     [e.period_end for e in src.engine]),
        ("TL.03", "Days in period",  "days",
         none_n,                                  [e.days_in_period for e in src.engine]),
        ("TL.04", "Day fraction",    "frac",
         none_n,                                  [e.day_fraction for e in src.engine]),
        ("TL.05", "Is operation",    "flag",
         none_n,                                  [str(e.is_operation) for e in src.engine]),
    ]

    cur_row = 2
    for code, name, unit, excel_vals, python_vals in items_def:
        for view_label, row_vals, row_fill in [
            ("Excel",  excel_vals, EXCEL_FILL),
            ("Python", python_vals, PYTHON_FILL),
        ]:
            ws.cell(row=cur_row, column=1, value=code if view_label == "Excel" else "")
            ws.cell(row=cur_row, column=2, value=name if view_label == "Excel" else "")
            ws.cell(row=cur_row, column=3, value=view_label).fill = row_fill
            ws.cell(row=cur_row, column=4, value=unit)
            for ci, v in enumerate(row_vals[:n]):
                cell = ws.cell(row=cur_row, column=DATA_COL + ci, value=v)
                cell.fill = row_fill
                cell.font = _font(size=8)
                cell.alignment = _align(h="center", v="center")
                if unit == "days" and isinstance(v, (int, float)):
                    cell.number_format = INT_FMT
                elif unit == "frac" and isinstance(v, (int, float)):
                    cell.number_format = FRAC_FMT
            cur_row += 1

    _freeze(ws, f"{get_column_letter(DATA_COL)}2")


def _build_prod_rev_recon(wb: Workbook, src: OborovoSources, mat: MaterialitySettings) -> None:
    n = len(src.engine)
    none_row = [None] * n
    blocks = [
        {"type": "section", "label": "— PRODUCTION —"},
        {"type": "item", "code": "PR.01", "name": "Net production (engine)", "unit": "MWh",
         "excel_vals": none_row, "python_vals": [e.production_mwh for e in src.engine],
         "item": get_item("PR.01")},
        {"type": "section", "label": "— REVENUE —"},
        {"type": "item", "code": "RV.01", "name": "Operating revenues (CF)", "unit": "kEUR",
         "excel_vals": [e.revenue_keur for e in src.excel],
         "python_vals": [e.revenue_keur for e in src.engine],
         "item": get_item("RV.01")},
        {"type": "item", "code": "RV.02", "name": "P&L total revenues", "unit": "kEUR",
         "excel_vals": [e.pl_revenue_keur for e in src.excel],
         "python_vals": [e.revenue_keur for e in src.engine],
         "item": get_item("RV.02")},
        {"type": "section", "label": "— SHL INTEREST (P&L) —"},
        {"type": "item", "code": "SH.02", "name": "SHL gross interest (P&L)", "unit": "kEUR",
         "excel_vals": [e.shl_interest_keur for e in src.excel],
         "python_vals": [UNAVAILABLE] * n,
         "item": get_item("SH.02")},
    ]
    _build_horizontal_sheet(wb, "03_PROD_REV_RECON", src, mat, blocks)


def _build_opex_recon(wb: Workbook, src: OborovoSources, mat: MaterialitySettings) -> None:
    n = len(src.engine)
    none_row = [None] * n

    opex_field_map = [
        "opex_b01_keur", "opex_b02_keur", "opex_b03_keur", "opex_b04_keur",
        "opex_b05_keur", "opex_b06_keur", "opex_b07_keur", "opex_b08_keur",
        "opex_b09_keur", "opex_b10_keur", "opex_b11_keur", "opex_b12_keur",
        "opex_b13_keur", "opex_b14_keur", "opex_b15_keur",
    ]

    blocks = [
        {"type": "section", "label": "— TOTAL OPEX —"},
        {"type": "item", "code": "OP.00", "name": "Total OPEX", "unit": "kEUR",
         "excel_vals": [e.opex_keur for e in src.excel],
         "python_vals": [e.opex_keur for e in src.engine],
         "item": get_item("OP.00")},
        {"type": "section", "label": "— OPEX BY ITEM CODE: Excel source NOT AVAILABLE in fixture (Excel fixture contains total OPEX only). Python values shown for reference. Classification = UNRESOLVED SOURCE. —"},
    ]
    for i, (opex_item, field) in enumerate(zip(src.opex_items, opex_field_map)):
        code = opex_item["code"]
        name = opex_item["name"]
        blocks.append({
            "type": "item",
            "code": code,
            "name": name,
            "unit": "kEUR",
            "excel_vals": none_row,
            "python_vals": [getattr(e, field) for e in src.engine],
            "item": get_item(f"OP.{i+1:02d}"),
        })

    _build_horizontal_sheet(wb, "04_OPEX_RECON", src, mat, blocks)


def _build_pnl_recon(wb: Workbook, src: OborovoSources, mat: MaterialitySettings) -> None:
    n = len(src.engine)
    unav = [UNAVAILABLE] * n
    none_row = [None] * n

    blocks = [
        {"type": "section", "label": "— P&L RECONSTRUCTION —"},
        {"type": "item", "code": "RV.02", "name": "Total revenues", "unit": "kEUR",
         "excel_vals": [e.pl_revenue_keur for e in src.excel],
         "python_vals": [e.revenue_keur for e in src.engine], "item": get_item("RV.02")},
        {"type": "item", "code": "OP.00", "name": "Total OPEX", "unit": "kEUR",
         "excel_vals": [e.opex_keur for e in src.excel],
         "python_vals": [e.opex_keur for e in src.engine], "item": get_item("OP.00")},
        {"type": "item", "code": "EB.01", "name": "EBITDA", "unit": "kEUR",
         "excel_vals": [e.ebitda_keur for e in src.excel],
         "python_vals": [e.ebitda_keur for e in src.engine], "item": get_item("EB.01")},
        {"type": "item", "code": "DP.01", "name": "Book depreciation", "unit": "kEUR",
         "excel_vals": [e.depreciation_keur for e in src.excel],
         "python_vals": [e.book_depreciation_keur for e in src.engine], "item": get_item("DP.01")},
        {"type": "item", "code": "EBIT", "name": "EBIT (OUT OF SCOPE)", "unit": "kEUR",
         "excel_vals": none_row, "python_vals": unav, "item": None},
        {"type": "section", "label": "— FINANCIAL ITEMS —"},
        {"type": "item", "code": "SD.07", "name": "Senior interest (P&L)", "unit": "kEUR",
         "excel_vals": [e.pl_senior_interest_keur for e in src.excel],
         "python_vals": [e.sd_interest_keur for e in src.engine], "item": get_item("SD.07")},
        {"type": "item", "code": "SH.02", "name": "SHL interest (P&L)", "unit": "kEUR",
         "excel_vals": [e.shl_interest_keur for e in src.excel],
         "python_vals": unav, "item": get_item("SH.02")},
        {"type": "item", "code": "CF.02", "name": "Earnings before tax (P&L)", "unit": "kEUR",
         "excel_vals": [e.earnings_before_tax_keur for e in src.excel],
         "python_vals": unav, "item": get_item("CF.02")},
        {"type": "section", "label": "— TAX —"},
        {"type": "item", "code": "TX.02", "name": "Taxable income (P&L)", "unit": "kEUR",
         "excel_vals": [e.taxable_income_keur for e in src.excel],
         "python_vals": [e.taxable_profit_keur for e in src.engine], "item": get_item("TX.02")},
        {"type": "item", "code": "TX.06", "name": "CIT accrual (P&L)", "unit": "kEUR",
         "excel_vals": [e.pl_cit_keur for e in src.excel],
         "python_vals": [e.tax_keur for e in src.engine], "item": get_item("TX.06")},
        {"type": "item", "code": "NET", "name": "Net income (OUT OF SCOPE)", "unit": "kEUR",
         "excel_vals": none_row, "python_vals": unav, "item": None},
    ]
    _build_horizontal_sheet(wb, "05_PNL_RECON", src, mat, blocks)


def _build_capex_recon(wb: Workbook, src: OborovoSources, mat: MaterialitySettings) -> None:
    ws = wb.create_sheet("06_CAPEX_IDC_RECON")
    ws.sheet_view.showGridLines = False
    headers = ["Code", "Item", "Excel (kEUR)", "Python (kEUR)", "Delta (kEUR)",
               "Excel Source", "Python Source", "Classification", "Notes"]
    _header_row(ws, headers)
    _set_col_widths(ws, {1: 8, 2: 40, 3: 16, 4: 16, 5: 12, 6: 28, 7: 28, 8: 26, 9: 50})

    r = 2
    UNRES_STR = "UNRESOLVED — not in Excel fixture"

    def sec(label):
        nonlocal r
        for c in range(1, len(headers) + 1): ws.cell(row=r, column=c).fill = SECTION_FILL
        ws.cell(row=r, column=2, value=label).font = _font(bold=True, size=9, color="FFFFFF")
        ws.cell(row=r, column=2).fill = SECTION_FILL
        r += 1

    def add(code, label, ev, pv, excel_src, python_src, cls=None, note=""):
        nonlocal r
        ev_f = _safe(ev) if not isinstance(ev, str) else None
        pv_f = _safe(pv) if not isinstance(pv, str) else None
        d = _delta(ev_f, pv_f)
        # Classification: only assign if we have both sides or documented reason
        if cls is None:
            if ev_f is None:
                cls = "UNRESOLVED SOURCE"
            elif pv_f is None:
                cls = "UNRESOLVED SOURCE"
            elif d is not None and not mat.is_material(d, ev_f, pv_f):
                cls = "MATCH"
            else:
                cls = ""  # OPEN
        ws.cell(row=r, column=1, value=code).font = _font(size=8)
        ws.cell(row=r, column=2, value=label).font = _font(size=9)
        c3 = ws.cell(row=r, column=3, value=ev_f if ev_f is not None else (ev if isinstance(ev, str) else None))
        c3.font = _font(size=9); c3.fill = EXCEL_FILL
        if ev_f is not None: c3.number_format = KEUR_FMT
        c4 = ws.cell(row=r, column=4, value=pv_f if pv_f is not None else (pv if isinstance(pv, str) else None))
        c4.font = _font(size=9); c4.fill = PYTHON_FILL
        if pv_f is not None: c4.number_format = KEUR_FMT
        c5 = ws.cell(row=r, column=5, value=d)
        c5.font = _font(size=9)
        if d is not None: c5.number_format = KEUR_FMT
        ws.cell(row=r, column=6, value=excel_src).font = _font(size=8)
        ws.cell(row=r, column=7, value=python_src).font = _font(size=8)
        display_cls = cls if cls else "OPEN — ROOT CAUSE REQUIRED"
        cls_cell = ws.cell(row=r, column=8, value=display_cls)
        cls_cell.fill = _fill(CLASS_FILL.get(cls, "FFFFFF"))
        cls_cell.font = _font(size=9)
        ws.cell(row=r, column=9, value=note).font = _font(size=8)
        r += 1

    sec("— HARD CAPEX: per-item (Excel: not in fixture — UNRESOLVED SOURCE) —")
    for item in src.capex_items:
        add(item["code"], item["name"],
            UNRES_STR, item["amount_keur"],
            "UNRESOLVED — period_diagnostics has no per-item CAPEX", "app.project_factories",
            "UNRESOLVED SOURCE")
    add("C.00", "Total Hard CAPEX",
        UNRES_STR, src.hard_capex_keur,
        "UNRESOLVED", "app.project_factories (sum of capex_items)",
        "UNRESOLVED SOURCE")

    sec("— FINANCING COSTS —")
    add("C.IDC", "Bank IDC (capitalised)",
        UNRES_STR, src.idc_keur,
        "UNRESOLVED — not separately in fixture", "app.project_factories",
        "UNRESOLVED SOURCE", "IDC included in Excel total_capex_keur but not extracted separately")
    add("C.SHL", "SHL IDC capitalised",
        src.shl_idc_keur, None,
        "excel_oborovo_full_model_extract.json → shl[0].capitalized_interest", "OUT OF CLEAN ENGINE SCOPE",
        "OUT OF CLEAN ENGINE SCOPE", "Excel SHL IDC = abs(construction period capitalized_interest)")

    sec("— TOTAL PROJECT COST —")
    add("C.TOT", "Total CAPEX (Hard + IDC)",
        src.excel_total_capex_keur, src.total_capex_keur,
        "oborovo_golden.json → outputs.total_capex_keur", "app.project_factories total_capex",
        "POLICY DIFFERENCE",
        f"Excel={src.excel_total_capex_keur:.1f} includes SHL IDC; Python={src.total_capex_keur:.1f} excludes SHL IDC")

    _freeze(ws, "A2")
    _autofilter(ws, 1, len(headers))


def _build_depreciation_recon(wb: Workbook, src: OborovoSources, mat: MaterialitySettings) -> None:
    n = len(src.engine)
    blocks = [
        {"type": "section", "label": "— BOOK DEPRECIATION —"},
        {"type": "item", "code": "DP.01", "name": "Book depreciation", "unit": "kEUR",
         "excel_vals": [e.depreciation_keur for e in src.excel],
         "python_vals": [e.book_depreciation_keur for e in src.engine], "item": get_item("DP.01")},
        {"type": "section", "label": "— TAX DEPRECIATION —"},
        {"type": "item", "code": "DP.02", "name": "Tax depreciation (Python only)", "unit": "kEUR",
         "excel_vals": [None] * n,
         "python_vals": [e.tax_depreciation_keur for e in src.engine], "item": get_item("DP.02")},
        {"type": "section", "label": "— CUMULATED DEPRECIATION —"},
        {"type": "item", "code": "DP.03", "name": "Cumulated depreciation (Excel Dep sheet)", "unit": "kEUR",
         "excel_vals": [e.dep_cumulated_keur for e in src.excel],
         "python_vals": [None] * n, "item": get_item("DP.03")},
    ]
    _build_horizontal_sheet(wb, "07_DEPRECIATION_RECON", src, mat, blocks)


def _build_tax_recon(wb: Workbook, src: OborovoSources, mat: MaterialitySettings) -> None:
    n = len(src.engine)
    none_row = [None] * n
    blocks = [
        {"type": "section", "label": "— TAX BRIDGE —"},
        {"type": "item", "code": "EB.01", "name": "EBITDA", "unit": "kEUR",
         "excel_vals": [e.ebitda_keur for e in src.excel],
         "python_vals": [e.ebitda_keur for e in src.engine], "item": get_item("EB.01")},
        {"type": "item", "code": "SD.07", "name": "Senior interest deductible", "unit": "kEUR",
         "excel_vals": [e.pl_senior_interest_keur for e in src.excel],
         "python_vals": [e.sd_interest_keur for e in src.engine], "item": get_item("SD.07")},
        {"type": "item", "code": "TX.01", "name": "Taxable profit (before losses)", "unit": "kEUR",
         "excel_vals": none_row,
         "python_vals": [e.taxable_profit_keur for e in src.engine], "item": get_item("TX.01")},
        {"type": "section", "label": "— LOSS LEDGER —"},
        {"type": "item", "code": "TX.03", "name": "Tax loss opening", "unit": "kEUR",
         "excel_vals": none_row,
         "python_vals": [e.tax_loss_opening_keur for e in src.engine], "item": get_item("TX.03")},
        {"type": "item", "code": "TX.04", "name": "Tax loss used", "unit": "kEUR",
         "excel_vals": none_row,
         "python_vals": [e.tax_loss_used_keur for e in src.engine], "item": get_item("TX.04")},
        {"type": "item", "code": "TX.05", "name": "Tax loss closing", "unit": "kEUR",
         "excel_vals": none_row,
         "python_vals": [e.tax_loss_closing_keur for e in src.engine], "item": get_item("TX.05")},
        {"type": "section", "label": "— CIT —"},
        {"type": "item", "code": "TX.06", "name": "CIT accrual", "unit": "kEUR",
         "excel_vals": [e.pl_cit_keur for e in src.excel],
         "python_vals": [e.tax_keur for e in src.engine], "item": get_item("TX.06")},
        {"type": "item", "code": "TX.07", "name": "Cash tax paid", "unit": "kEUR",
         "excel_vals": [e.cash_tax_keur for e in src.excel],
         "python_vals": [e.corporate_tax_cash_keur for e in src.engine], "item": get_item("TX.07")},
    ]
    _build_horizontal_sheet(wb, "08_TAX_RECON", src, mat, blocks)


def _build_cfads_recon(wb: Workbook, src: OborovoSources, mat: MaterialitySettings) -> None:
    n = len(src.engine)
    unav = [UNAVAILABLE] * n
    blocks = [
        {"type": "section", "label": "— CFADS BRIDGE —"},
        {"type": "item", "code": "RV.01", "name": "Revenue", "unit": "kEUR",
         "excel_vals": [e.revenue_keur for e in src.excel],
         "python_vals": [e.revenue_keur for e in src.engine], "item": get_item("RV.01")},
        {"type": "item", "code": "OP.00", "name": "OPEX", "unit": "kEUR",
         "excel_vals": [e.opex_keur for e in src.excel],
         "python_vals": [e.opex_keur for e in src.engine], "item": get_item("OP.00")},
        {"type": "item", "code": "EB.01", "name": "EBITDA", "unit": "kEUR",
         "excel_vals": [e.ebitda_keur for e in src.excel],
         "python_vals": [e.ebitda_keur for e in src.engine], "item": get_item("EB.01")},
        {"type": "item", "code": "TX.07", "name": "Cash tax paid", "unit": "kEUR",
         "excel_vals": [e.cash_tax_keur for e in src.excel],
         "python_vals": [e.corporate_tax_cash_keur for e in src.engine], "item": get_item("TX.07")},
        {"type": "item", "code": "CF.01", "name": "CFADS", "unit": "kEUR",
         "excel_vals": [e.cfads_keur for e in src.excel],
         "python_vals": [e.cfads_keur for e in src.engine], "item": get_item("CF.01")},
        {"type": "section", "label": "— SENIOR DEBT SERVICE —"},
        {"type": "item", "code": "SD.04", "name": "Senior debt service", "unit": "kEUR",
         "excel_vals": [e.senior_ds_keur for e in src.excel],
         "python_vals": [e.sd_ds_keur for e in src.engine], "item": get_item("SD.04")},
        {"type": "item", "code": "FC.01", "name": "FCF for distribution (OUT OF SCOPE)", "unit": "kEUR",
         "excel_vals": [e.free_cash_flow_keur for e in src.excel],
         "python_vals": unav, "item": get_item("FC.01")},
        {"type": "section", "label": "— OUT OF CLEAN ENGINE SCOPE —"},
        {"type": "item", "code": "FC.03", "name": "DSRA contribution (OUT OF SCOPE)", "unit": "kEUR",
         "excel_vals": [None] * n, "python_vals": unav, "item": get_item("FC.03")},
    ]
    _build_horizontal_sheet(wb, "09_CFADS_RECON", src, mat, blocks)


def _build_senior_debt_recon(wb: Workbook, src: OborovoSources, mat: MaterialitySettings) -> None:
    n = len(src.engine)
    debt_delta = src.engine_debt_size_keur - src.excel_total_debt_keur

    blocks = [
        {"type": "section", "label": (
            f"— DEBT SIZE: Excel={src.excel_total_debt_keur:.1f} kEUR "
            f"(GEARING CAP 75.24% × CAPEX)  |  "
            f"Python={src.engine_debt_size_keur:.1f} kEUR "
            f"(DSCR SCULPTED 1.15×)  |  "
            f"Delta={debt_delta:+.1f} kEUR  → POLICY DIFFERENCE —"
        )},
        {"type": "section", "label": (
            "— SD.01 / SD.05 Opening/Closing: Excel reconstructed from golden opening "
            "balance + DS.senior_principal_keur (genuine Excel provenance, NOT legacy snapshot) —"
        )},
        {"type": "item", "code": "SD.01", "name": "Opening senior debt", "unit": "kEUR",
         "excel_vals": src.excel_sd_opening_keur,
         "python_vals": [e.sd_opening_keur for e in src.engine], "item": get_item("SD.01")},
        {"type": "item", "code": "SD.02", "name": "Senior interest (DS sheet)", "unit": "kEUR",
         "excel_vals": [e.senior_interest_keur for e in src.excel],
         "python_vals": [e.sd_interest_keur for e in src.engine], "item": get_item("SD.02")},
        {"type": "item", "code": "SD.03", "name": "Senior principal (DS sheet)", "unit": "kEUR",
         "excel_vals": [e.senior_principal_keur for e in src.excel],
         "python_vals": [e.sd_principal_keur for e in src.engine], "item": get_item("SD.03")},
        {"type": "item", "code": "SD.04", "name": "Senior debt service (CF sheet)", "unit": "kEUR",
         "excel_vals": [e.senior_ds_keur for e in src.excel],
         "python_vals": [e.sd_ds_keur for e in src.engine], "item": get_item("SD.04")},
        {"type": "item", "code": "SD.05", "name": "Closing senior debt (reconstructed)", "unit": "kEUR",
         "excel_vals": src.excel_sd_closing_keur,
         "python_vals": [e.sd_closing_keur for e in src.engine], "item": get_item("SD.05")},
        {"type": "item", "code": "SD.06", "name": "DSCR — average per period (CF sheet)", "unit": "x",
         "excel_vals": [e.avg_dscr for e in src.excel],
         "python_vals": [e.sd_dscr for e in src.engine], "item": get_item("SD.06")},
        {"type": "item", "code": "SD.07", "name": "Senior interest P&L (cross-check)", "unit": "kEUR",
         "excel_vals": [e.pl_senior_interest_keur for e in src.excel],
         "python_vals": [e.sd_interest_keur for e in src.engine], "item": get_item("SD.07")},
    ]
    _build_horizontal_sheet(wb, "10_SENIOR_DEBT_RECON", src, mat, blocks)


def _build_shl_recon(wb: Workbook, src: OborovoSources, mat: MaterialitySettings) -> None:
    ws = wb.create_sheet("11_SHL_RECON")
    ws.sheet_view.showGridLines = False

    headers = ["Period", "Date", "Opening (kEUR)", "Closing (kEUR)", "Gross Interest (kEUR)",
               "Principal Flow (kEUR)", "Cash Interest Paid (kEUR)", "Capitalised Interest (kEUR)",
               "Net Dividend (kEUR)", "Source", "Python Status"]
    _header_row(ws, headers)
    _set_col_widths(ws, {c: 16 for c in range(1, 12)})
    _set_col_widths(ws, {1: 8, 2: 12})

    for r_idx, row in enumerate(src.excel_shl, 2):
        period_label = "Construction" if r_idx == 2 else f"Op.{r_idx - 2}"
        ws.cell(row=r_idx, column=1, value=period_label)
        for c, key in enumerate(["date", "opening", "closing", "gross_interest",
                                   "principal_flow", "paid_net_interest",
                                   "capitalized_interest", "net_dividend"], 2):
            val = row.get(key)
            cell = ws.cell(row=r_idx, column=c, value=_safe(val) if isinstance(val, (int, float)) else val)
            if isinstance(val, (int, float)):
                cell.number_format = KEUR_FMT
            cell.fill = EXCEL_FILL
            cell.font = _font(size=9)
        ws.cell(row=r_idx, column=10, value="excel_oborovo_full_model_extract.json").font = _font(size=8)
        cls_cell = ws.cell(row=r_idx, column=11, value="OUT OF CLEAN ENGINE SCOPE")
        cls_cell.fill = _fill(CLASS_FILL["OUT OF CLEAN ENGINE SCOPE"])
        cls_cell.font = _font(size=9)

    _freeze(ws, "A2")
    _autofilter(ws, 1, 11)


def _build_opening_balances(wb: Workbook, src: OborovoSources, mat: MaterialitySettings) -> None:
    ws = wb.create_sheet("12_OPENING_BALANCES")
    ws.sheet_view.showGridLines = False
    _header_row(ws, ["Code", "Item", "Excel", "Python", "Delta", "Source", "Classification"])
    _set_col_widths(ws, {1: 8, 2: 40, 3: 16, 4: 16, 5: 12, 6: 36, 7: 26})

    r = 2
    def add(code, label, ev, pv, source, cls="MATCH"):
        nonlocal r
        ev_f = _safe(ev)
        pv_f = _safe(pv)
        d = _delta(ev_f, pv_f)
        ws.cell(row=r, column=1, value=code).font = _font(size=8)
        ws.cell(row=r, column=2, value=label).font = _font(size=9)
        c3 = ws.cell(row=r, column=3, value=ev_f if ev_f is not None else ev)
        c3.font = _font(size=9)
        if ev_f is not None: c3.number_format = KEUR_FMT
        c4 = ws.cell(row=r, column=4, value=pv_f if pv_f is not None else pv)
        c4.font = _font(size=9)
        if pv_f is not None: c4.number_format = KEUR_FMT
        c5 = ws.cell(row=r, column=5, value=d)
        c5.font = _font(size=9)
        if d is not None: c5.number_format = KEUR_FMT
        ws.cell(row=r, column=6, value=source).font = _font(size=8)
        cl = ws.cell(row=r, column=7, value=cls)
        cl.fill = _fill(CLASS_FILL.get(cls, "FFFFFF"))
        cl.font = _font(size=9)
        r += 1

    leg0 = src.legacy[0] if src.legacy else None

    add("OB.01", "Opening senior debt (at COD)",   src.excel_total_debt_keur,  src.engine_debt_size_keur,  "golden / engine",  "POLICY DIFFERENCE")
    add("OB.02", "Opening SHL",                    src.shl_amount_keur,         None,                       "oborovo_golden.json", "OUT OF CLEAN ENGINE SCOPE")
    add("OB.03", "Opening tax losses",             0.0,                          0.0,                        "tax_reference_inputs", "MATCH")
    add("OB.04", "Opening DSRA balance",           None,                         None,                       "UNRESOLVED SOURCE",    "UNRESOLVED SOURCE")
    add("OB.05", "Gross asset basis at COD (kEUR)",src.excel_total_capex_keur,   src.total_capex_keur,       "golden / factory",     "POLICY DIFFERENCE")
    add("OB.06", "Senior debt at COD (legacy)",    leg0.sd_opening_keur if leg0 else None, src.engine_debt_size_keur, "legacy_snapshot / engine", "POLICY DIFFERENCE")

    _freeze(ws, "A2")
    _autofilter(ws, 1, 7)


def _build_delta_register(wb: Workbook, src: OborovoSources, mat: MaterialitySettings) -> None:
    ws = wb.create_sheet("13_DELTA_REGISTER")
    ws.sheet_view.showGridLines = False
    headers = [
        "delta_id", "baseline_id", "section", "code", "line_item", "period",
        "excel_value", "python_value", "absolute_delta", "relative_delta",
        "classification", "root_cause", "financial_judgment", "decision",
        "excel_source", "python_source", "status",
    ]
    _header_row(ws, headers)
    _set_col_widths(ws, {c: 14 for c in range(1, len(headers) + 1)})
    _set_col_widths(ws, {1: 12, 4: 8, 5: 36, 11: 26, 12: 36, 13: 36})

    delta_rows = []
    n = len(src.engine)

    # Check per-period, per-item deltas
    per_period_checks = [
        # (item_code, section, name, excel_getter, python_getter, unit)
        ("RV.01", "REVENUE", "Operating revenues", lambda ep, eg: ep.revenue_keur, lambda ep, eg: eg.revenue_keur, "kEUR"),
        ("OP.00", "OPEX",    "Total OPEX",         lambda ep, eg: ep.opex_keur,    lambda ep, eg: eg.opex_keur,    "kEUR"),
        ("EB.01", "EBITDA",  "EBITDA",             lambda ep, eg: ep.ebitda_keur,  lambda ep, eg: eg.ebitda_keur,  "kEUR"),
        ("TX.06", "TAX",     "CIT accrual",        lambda ep, eg: ep.pl_cit_keur,  lambda ep, eg: eg.tax_keur,     "kEUR"),
        ("TX.07", "TAX",     "Cash tax",           lambda ep, eg: ep.cash_tax_keur,lambda ep, eg: eg.corporate_tax_cash_keur, "kEUR"),
        ("CF.01", "CFADS",   "CFADS",              lambda ep, eg: ep.cfads_keur,   lambda ep, eg: eg.cfads_keur,   "kEUR"),
        ("SD.02", "SENIOR_DEBT","Senior interest", lambda ep, eg: ep.senior_interest_keur, lambda ep, eg: eg.sd_interest_keur, "kEUR"),
        ("SD.03", "SENIOR_DEBT","Senior principal",lambda ep, eg: ep.senior_principal_keur,lambda ep, eg: eg.sd_principal_keur,"kEUR"),
        ("SD.04", "SENIOR_DEBT","Senior DS",       lambda ep, eg: ep.senior_ds_keur, lambda ep, eg: eg.sd_ds_keur, "kEUR"),
        ("SD.06", "SENIOR_DEBT","DSCR",            lambda ep, eg: ep.avg_dscr,     lambda ep, eg: eg.sd_dscr,      "x"),
        ("DP.01", "DEPRECIATION","Book depreciation",lambda ep, eg: ep.depreciation_keur, lambda ep, eg: eg.book_depreciation_keur, "kEUR"),
    ]

    # Root-cause notes per line item (upstream-to-downstream order).
    # Material deltas without root cause get blank classification + OPEN status.
    ITEM_EXCEL_SOURCE = {
        "RV.01": "CF.operating_revenues_keur",
        "OP.00": "abs(CF.operating_expenses_after_bank_tax_keur)",
        "EB.01": "CF.ebitda_keur",
        "TX.06": "abs(P&L.corporate_income_tax_keur)",
        "TX.07": "abs(CF.corporate_income_tax_keur)",
        "CF.01": "CF.free_cash_flow_for_banks_keur",
        "SD.02": "DS.senior_net_interest_keur",
        "SD.03": "DS.senior_principal_keur",
        "SD.04": "abs(CF.senior_debt_service_keur)",
        "SD.06": "CF.average_senior_dscr_period",
        "DP.01": "abs(P&L.depreciation_keur)",
    }
    ITEM_ROOT_CAUSE_HINT = {
        "RV.01": "OPEN — ROOT CAUSE REQUIRED. Trace: production match? → price match? → which revenue component diverges?",
        "OP.00": "OPEN — ROOT CAUSE REQUIRED. Trace: which B.xx item drives the OPEX delta? Check Excel total vs sum(B.01..B.15).",
        "EB.01": "OPEN — ROOT CAUSE REQUIRED. EBITDA = Revenue - OPEX; diagnose upstream first (RV.01, OP.00).",
        "TX.06": "OPEN — ROOT CAUSE REQUIRED. CIT accrual: check taxable income alignment (TX.02 vs TX.01), then rate application.",
        "TX.07": "OPEN — ROOT CAUSE REQUIRED. Cash tax timing: lag vs accrual? Check CIT accrual delta first.",
        "CF.01": "OPEN — ROOT CAUSE REQUIRED. CFADS = EBITDA - cash_tax; diagnose EBITDA and tax deltas first.",
        "SD.02": "OPEN — ROOT CAUSE REQUIRED. Interest = opening_balance × rate × day_fraction. Check debt-size delta (POLICY DIFFERENCE) as upstream cause.",
        "SD.03": "OPEN — ROOT CAUSE REQUIRED. Principal driven by CFADS sculpting vs gearing schedule; debt-size POLICY DIFFERENCE is primary upstream cause.",
        "SD.04": "OPEN — ROOT CAUSE REQUIRED. DS = interest + principal; diagnose SD.02, SD.03 first.",
        "SD.06": "OPEN — ROOT CAUSE REQUIRED. DSCR = CFADS / DS; debt-size POLICY DIFFERENCE affects denominator directly.",
        "DP.01": "OPEN — ROOT CAUSE REQUIRED. Check: same depreciable base (CAPEX)? Same useful life? Same method (straight-line)?",
    }

    delta_counter = 0
    for code, section, name, ef, pf, unit in per_period_checks:
        item = get_item(code)
        for i, (ep, eg) in enumerate(zip(src.excel, src.engine)):
            ev = _safe(ef(ep, eg))
            pv = _safe(pf(ep, eg))
            d = _delta(ev, pv)
            if d is None:
                continue
            if not mat.is_material(d, ev, pv, unit):
                continue
            delta_counter += 1
            dp = _delta_pct(d, ev)
            cls = _classify(item, d, ev, pv, mat) if item else ""
            root_cause = ITEM_ROOT_CAUSE_HINT.get(code, "OPEN — ROOT CAUSE REQUIRED")
            excel_src = ITEM_EXCEL_SOURCE.get(code, "excel_oborovo_full_model_extract.json")
            delta_rows.append([
                f"DELTA-{delta_counter:04d}", BASELINE_ID, section, code, name,
                eg.period_end, ev, pv, d, dp,
                cls if cls else "",
                root_cause,
                "Manual financial review required",
                "OPEN",
                excel_src,
                "run_senior_debt_model(oborovo)",
                "OPEN",
            ])

    # Add scalar delta for debt size
    ev_ds = src.excel_total_debt_keur
    pv_ds = src.engine_debt_size_keur
    d_ds = _delta(ev_ds, pv_ds)
    if d_ds and mat.is_material(d_ds, ev_ds, pv_ds):
        delta_counter += 1
        delta_rows.append([
            f"DELTA-{delta_counter:04d}", BASELINE_ID, "SENIOR_DEBT", "SD.00", "Debt size at COD",
            "COD", ev_ds, pv_ds, d_ds, _delta_pct(d_ds, ev_ds),
            "POLICY DIFFERENCE",
            "Excel uses GEARING CAP sizing; Python uses DSCR SCULPTED sizing",
            "Different sizing methodologies. Excel debt = 75.24% × CAPEX; Python debt = DSCR-sculpted at 1.15x",
            "OPEN — methodology choice requires decision",
            "oborovo_golden.json", "run_senior_debt_model(oborovo)", "OPEN",
        ])

    for r_idx, row in enumerate(delta_rows, 2):
        for c_idx, val in enumerate(row, 1):
            display_val = val
            if c_idx == 11 and val == "":
                display_val = "OPEN — ROOT CAUSE REQUIRED"
            cell = ws.cell(row=r_idx, column=c_idx, value=display_val)
            cell.font = _font(size=9)
            if c_idx in (7, 8, 9):
                if isinstance(val, float):
                    cell.number_format = KEUR_FMT
            if c_idx == 10 and isinstance(val, float):
                cell.number_format = PCT_FMT
            if c_idx == 11:
                raw_cls = str(val) if val else ""
                cell.fill = _fill(CLASS_FILL.get(raw_cls, "FFFFFF"))

    _freeze(ws, "A2")
    _autofilter(ws, 1, len(headers))


def _build_source_map(wb: Workbook, src: OborovoSources, mat: MaterialitySettings) -> None:
    ws = wb.create_sheet("14_SOURCE_MAP")
    ws.sheet_view.showGridLines = False
    headers = ["section", "code", "line_item", "excel_sheet", "excel_field",
               "python_module", "python_field", "python_function"]
    _header_row(ws, headers)
    _set_col_widths(ws, {1: 14, 2: 8, 3: 36, 4: 12, 5: 40, 6: 30, 7: 30, 8: 40})

    source_map = [
        # section, code, line_item, excel_sheet, excel_field, python_module, python_field, python_function
        # TIMELINE
        ("TIMELINE",    "TL.02", "Period end date",         "period_diagnostics", "date col",                 "financial_engine.results", "period_end",                 "run_senior_debt_model → OperatingPeriodResult"),
        ("TIMELINE",    "TL.01", "Period index",            "UNRESOLVED",         "not in fixture",           "financial_engine.results", "period_index",               "run_senior_debt_model → OperatingPeriodResult"),
        ("TIMELINE",    "TL.03", "Days in period",          "UNRESOLVED",         "not in fixture",           "financial_engine.results", "days_in_period",             "run_senior_debt_model → OperatingPeriodResult"),
        ("TIMELINE",    "TL.04", "Day fraction",            "UNRESOLVED",         "not in fixture",           "financial_engine.results", "day_fraction",               "run_senior_debt_model → OperatingPeriodResult"),
        ("TIMELINE",    "TL.05", "Is operation",            "UNRESOLVED",         "not in fixture",           "financial_engine.results", "is_operation",               "run_senior_debt_model → OperatingPeriodResult"),
        # PRODUCTION
        ("PRODUCTION",  "PR.01", "Net production (engine)", "UNRESOLVED",         "not in fixture",           "financial_engine.results", "production_mwh",             "from_project_inputs → run_senior_debt_model"),
        # REVENUE
        ("REVENUE",     "RV.01", "Operating revenues (CF)", "CF",                 "CF.operating_revenues_keur","financial_engine.results", "revenue_keur",              "from_project_inputs → run_senior_debt_model"),
        ("REVENUE",     "RV.02", "Total revenues (P&L)",    "P&L",                "P&L.total_revenues_keur",  "financial_engine.results", "revenue_keur (same field)",  "from_project_inputs → run_senior_debt_model"),
        # OPEX
        ("OPEX",        "OP.00", "Total OPEX",              "CF",                 "CF.operating_expenses_after_bank_tax_keur","financial_engine.results","opex_keur","from_project_inputs → run_senior_debt_model"),
        ("OPEX",        "OP.01–OP.15","OPEX by item B.xx", "UNRESOLVED",          "not in fixture (total only)","app.project_factories",  "opex_b01..15_keur",         "OpexItem.amount_at_year(year_index)"),
        # EBITDA
        ("EBITDA",      "EB.01", "EBITDA",                  "CF",                 "CF.ebitda_keur",           "financial_engine.results", "ebitda_keur",                "from_project_inputs → run_senior_debt_model"),
        # CAPEX
        ("CAPEX",       "CA.00–CA.15","Hard CAPEX per item","UNRESOLVED",         "not in fixture",           "app.project_factories",    "capex_items[].amount_keur",  "CapexStructure.capex_items()"),
        ("CAPEX",       "C.TOT", "Total CAPEX",             "oborovo_golden.json","outputs.total_capex_keur", "app.project_factories",    "total_capex",                "CapexStructure.total_capex"),
        ("CAPEX",       "C.SHL", "SHL IDC capitalised",     "SHL fixture",        "shl[0].capitalized_interest","OUT OF CLEAN ENGINE SCOPE","N/A",                    "N/A — SHL not in clean engine"),
        # DEPRECIATION
        ("DEPRECIATION","DP.01", "Book depreciation",       "P&L",                "P&L.depreciation_keur",   "financial_engine.results", "book_depreciation_keur",     "from_project_inputs → run_senior_debt_model"),
        ("DEPRECIATION","DP.02", "Tax depreciation",        "UNRESOLVED",         "not in fixture",           "financial_engine.results", "tax_depreciation_keur",      "calculate_tax → TaxAndCfadsSchedules"),
        ("DEPRECIATION","DP.03", "Cumulated depreciation",  "Dep",                "Dep.cumulated_depreciation_keur","UNRESOLVED",         "N/A — no Python equivalent", "N/A"),
        # TAX
        ("TAX",         "TX.01", "Taxable profit (EBITDA basis)","UNRESOLVED",    "not in fixture",           "financial_engine.results", "taxable_profit_keur",        "calculate_tax → TaxAndCfadsSchedules"),
        ("TAX",         "TX.02", "P&L taxable income",      "P&L",                "P&L.taxable_income_keur",  "financial_engine.results", "taxable_profit_keur",        "calculate_tax → TaxAndCfadsSchedules"),
        ("TAX",         "TX.03", "Tax loss opening",        "UNRESOLVED",         "not in fixture",           "financial_engine.results", "tax_loss_opening_keur",      "calculate_tax → TaxAndCfadsSchedules"),
        ("TAX",         "TX.04", "Tax loss used",           "UNRESOLVED",         "not in fixture",           "financial_engine.results", "tax_loss_used_keur",         "calculate_tax → TaxAndCfadsSchedules"),
        ("TAX",         "TX.05", "Tax loss closing",        "UNRESOLVED",         "not in fixture",           "financial_engine.results", "tax_loss_closing_keur",      "calculate_tax → TaxAndCfadsSchedules"),
        ("TAX",         "TX.06", "CIT accrual (P&L)",       "P&L",                "P&L.corporate_income_tax_keur","financial_engine.results","tax_keur",              "calculate_tax → TaxAndCfadsSchedules"),
        ("TAX",         "TX.07", "Cash tax paid",           "CF",                 "CF.corporate_income_tax_keur","financial_engine.results","corporate_tax_cash_keur", "calculate_tax → TaxAndCfadsSchedules"),
        # CFADS
        ("CFADS",       "CF.01", "CFADS",                   "CF",                 "CF.free_cash_flow_for_banks_keur","financial_engine.results","cfads_keur",          "calculate_canonical_cfads → TaxAndCfadsSchedules"),
        ("CFADS",       "CF.02", "Earnings before tax",     "P&L",                "P&L.earnings_before_tax_keur","OUT OF CLEAN ENGINE SCOPE","N/A",                  "N/A — EBT not in clean engine output"),
        # SENIOR DEBT
        ("SENIOR_DEBT", "SD.01", "Opening senior debt",     "Reconstructed",      "opening = excel_total_debt_keur; roll: closing[t-1]","financial_engine.senior_debt","sd_opening_keur","solve_senior_debt → SeniorDebtSchedules"),
        ("SENIOR_DEBT", "SD.02", "Senior interest",         "DS",                 "DS.senior_net_interest_keur","financial_engine.senior_debt","sd_interest_keur",   "solve_senior_debt → SeniorDebtSchedules"),
        ("SENIOR_DEBT", "SD.03", "Senior principal",        "DS",                 "DS.senior_principal_keur", "financial_engine.senior_debt","sd_principal_keur",   "solve_senior_debt → SeniorDebtSchedules"),
        ("SENIOR_DEBT", "SD.04", "Senior debt service",     "CF",                 "abs(CF.senior_debt_service_keur)","financial_engine.senior_debt","sd_ds_keur",    "solve_senior_debt → SeniorDebtSchedules"),
        ("SENIOR_DEBT", "SD.05", "Closing senior debt",     "Reconstructed",      "closing = opening - principal (DS sheet)","financial_engine.senior_debt","sd_closing_keur","solve_senior_debt → SeniorDebtSchedules"),
        ("SENIOR_DEBT", "SD.06", "DSCR (period average)",   "CF",                 "CF.average_senior_dscr_period","financial_engine.senior_debt","sd_dscr",         "solve_senior_debt → SeniorDebtSchedules"),
        ("SENIOR_DEBT", "SD.07", "Senior interest (P&L)",   "P&L",                "abs(P&L.senior_interests_keur)","financial_engine.senior_debt","sd_interest_keur","solve_senior_debt → SeniorDebtSchedules"),
        # SHL
        ("SHL",         "SH.01", "Opening SHL",             "SHL fixture",        "shl[n].opening",           "OUT OF CLEAN ENGINE SCOPE","N/A",                    "N/A"),
        ("SHL",         "SH.02", "SHL gross interest",      "P&L",                "abs(P&L.shareholder_loan_interests_keur)","OUT OF CLEAN ENGINE SCOPE","N/A",     "N/A"),
        ("SHL",         "SH.03", "Closing SHL",             "SHL fixture",        "shl[n].closing",           "OUT OF CLEAN ENGINE SCOPE","N/A",                    "N/A"),
        # CASHFLOW
        ("CASHFLOW",    "FC.01", "Free cash flow",          "CF",                 "CF.free_cash_flow_for_distribution_keur","OUT OF CLEAN ENGINE SCOPE","N/A",      "N/A"),
        ("CASHFLOW",    "FC.02", "Net dividends",           "P&L",                "P&L.net_dividends_keur",   "OUT OF CLEAN ENGINE SCOPE","N/A",                    "N/A"),
        ("CASHFLOW",    "FC.03", "DSRA contribution",       "UNRESOLVED",         "not in fixture",           "OUT OF CLEAN ENGINE SCOPE","N/A",                    "N/A"),
    ]

    for r_idx, row in enumerate(source_map, 2):
        for c_idx, val in enumerate(row, 1):
            ws.cell(row=r_idx, column=c_idx, value=val).font = _font(size=9)

    _freeze(ws, "A2")
    _autofilter(ws, 1, 8)


def _build_raw_recon(wb: Workbook, src: OborovoSources, mat: MaterialitySettings) -> None:
    ws = wb.create_sheet("15_RAW_RECON")
    ws.sheet_view.showGridLines = False
    headers = [
        "baseline_id", "period_index", "period_end", "section", "code", "line_item",
        "unit", "excel_value", "python_value", "delta", "delta_pct",
        "classification", "excel_source", "python_source",
    ]
    _header_row(ws, headers)
    _set_col_widths(ws, {c: 14 for c in range(1, len(headers) + 1)})
    _set_col_widths(ws, {5: 8, 6: 36, 12: 26})

    per_period_checks = [
        ("REVENUE",     "RV.01", "Operating revenues",   "kEUR", lambda ep: ep.revenue_keur,       lambda eg: eg.revenue_keur),
        ("OPEX",        "OP.00", "Total OPEX",           "kEUR", lambda ep: ep.opex_keur,           lambda eg: eg.opex_keur),
        ("EBITDA",      "EB.01", "EBITDA",               "kEUR", lambda ep: ep.ebitda_keur,         lambda eg: eg.ebitda_keur),
        ("TAX",         "TX.06", "CIT accrual",          "kEUR", lambda ep: ep.pl_cit_keur,         lambda eg: eg.tax_keur),
        ("TAX",         "TX.07", "Cash tax paid",        "kEUR", lambda ep: ep.cash_tax_keur,       lambda eg: eg.corporate_tax_cash_keur),
        ("CFADS",       "CF.01", "CFADS",                "kEUR", lambda ep: ep.cfads_keur,          lambda eg: eg.cfads_keur),
        ("SENIOR_DEBT", "SD.02", "Senior interest",      "kEUR", lambda ep: ep.senior_interest_keur,lambda eg: eg.sd_interest_keur),
        ("SENIOR_DEBT", "SD.03", "Senior principal",     "kEUR", lambda ep: ep.senior_principal_keur,lambda eg: eg.sd_principal_keur),
        ("SENIOR_DEBT", "SD.04", "Senior DS",            "kEUR", lambda ep: ep.senior_ds_keur,      lambda eg: eg.sd_ds_keur),
        ("SENIOR_DEBT", "SD.06", "DSCR",                 "x",    lambda ep: ep.avg_dscr,            lambda eg: eg.sd_dscr),
        ("DEPRECIATION","DP.01", "Book depreciation",    "kEUR", lambda ep: ep.depreciation_keur,   lambda eg: eg.book_depreciation_keur),
        ("PRODUCTION",  "PR.01", "Net production",       "MWh",  lambda ep: None,                   lambda eg: eg.production_mwh),
    ]

    r_idx = 2
    for section, code, name, unit, ef, pf in per_period_checks:
        item = get_item(code)
        for i, (ep, eg) in enumerate(zip(src.excel, src.engine)):
            ev = _safe(ef(ep))
            pv = _safe(pf(eg))
            d = _delta(ev, pv)
            dp = _delta_pct(d, ev)
            cls = _classify(item, d, ev, pv, mat) if item else "UNRESOLVED SOURCE"
            display_cls = cls if cls else "OPEN — ROOT CAUSE REQUIRED"
            row = [BASELINE_ID, i, eg.period_end, section, code, name, unit,
                   ev, pv, d, dp, display_cls,
                   "excel_oborovo_full_model_extract.json",
                   "run_senior_debt_model(oborovo)"]
            for c_idx, val in enumerate(row, 1):
                cell = ws.cell(row=r_idx, column=c_idx, value=val)
                cell.font = _font(size=8)
                if c_idx in (8, 9, 10) and isinstance(val, float):
                    cell.number_format = KEUR_FMT
                if c_idx == 11 and isinstance(val, float):
                    cell.number_format = PCT_FMT
                if c_idx == 12:
                    raw_cls = cls if cls else ""
                    cell.fill = _fill(CLASS_FILL.get(raw_cls, "FFFFFF"))
            r_idx += 1

    _freeze(ws, "A2")
    _autofilter(ws, 1, len(headers))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_workbook(
    sources: OborovoSources,
    output_path: str,
    materiality: MaterialitySettings = DEFAULT_MATERIALITY,
) -> Workbook:
    """Build the reconciliation workbook and save to output_path. Returns the Workbook."""
    wb = Workbook()
    # Remove default sheet
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    _build_exec_recon(wb, sources, materiality)
    _build_inputs_recon(wb, sources, materiality)
    _build_timeline_recon(wb, sources, materiality)
    _build_prod_rev_recon(wb, sources, materiality)
    _build_opex_recon(wb, sources, materiality)
    _build_pnl_recon(wb, sources, materiality)
    _build_capex_recon(wb, sources, materiality)
    _build_depreciation_recon(wb, sources, materiality)
    _build_tax_recon(wb, sources, materiality)
    _build_cfads_recon(wb, sources, materiality)
    _build_senior_debt_recon(wb, sources, materiality)
    _build_shl_recon(wb, sources, materiality)
    _build_opening_balances(wb, sources, materiality)
    _build_delta_register(wb, sources, materiality)
    _build_source_map(wb, sources, materiality)
    _build_raw_recon(wb, sources, materiality)

    wb.save(output_path)
    return wb
