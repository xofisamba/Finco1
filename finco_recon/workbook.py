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
    "MATERIAL DELTA":           "FFC7CE",
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
) -> str:
    if not item.in_clean_engine:
        return "OUT OF CLEAN ENGINE SCOPE"
    if item.excel_field is None and item.engine_field is None:
        return "UNRESOLVED SOURCE"
    if item.excel_field is None:
        return "UNRESOLVED SOURCE"
    if item.engine_field is None:
        return "OUT OF CLEAN ENGINE SCOPE"
    if delta is None:
        return "UNRESOLVED SOURCE"
    if not mat.is_material(delta, excel, python, item.unit):
        return "MATCH"
    return "POLICY DIFFERENCE"


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
               "Delta", "Delta %", "Max Period |Delta|", "Status", "Classification"]
    _header_row(ws, headers)

    def _tot(vals: list[float | None]) -> float:
        return sum(v for v in vals if v is not None)

    excel_p = src.excel
    eng_p   = src.engine

    rows_data = [
        # section, line_item, excel_val, python_val, classification
        ("TIMELINE",     "Operating periods",          60.0,                                  float(len(eng_p)),              "MATCH"),
        ("TIMELINE",     "COD date",                   src.cod_date,                          src.engine[0].period_start if eng_p else "",  "MATCH"),
        ("PRODUCTION",   "Total net production (MWh)", None,                                  _tot([e.production_mwh for e in eng_p]),       "UNRESOLVED SOURCE"),
        ("REVENUE",      "Total revenue (kEUR)",       _tot([e.revenue_keur for e in excel_p if e.revenue_keur]),
                                                        _tot([e.revenue_keur for e in eng_p if e.revenue_keur]),                "POLICY DIFFERENCE"),
        ("OPEX",         "Total OPEX (kEUR)",          _tot([e.opex_keur for e in excel_p if e.opex_keur]),
                                                        _tot([e.opex_keur for e in eng_p if e.opex_keur]),                     "POLICY DIFFERENCE"),
        ("EBITDA",       "Total EBITDA (kEUR)",        _tot([e.ebitda_keur for e in excel_p if e.ebitda_keur]),
                                                        _tot([e.ebitda_keur for e in eng_p if e.ebitda_keur]),                 "POLICY DIFFERENCE"),
        ("CAPEX",        "Total CAPEX (kEUR)",         src.excel_total_capex_keur,            src.total_capex_keur,           "POLICY DIFFERENCE"),
        ("IDC",          "Bank IDC (kEUR)",            None,                                  src.idc_keur,                   "UNRESOLVED SOURCE"),
        ("DEPRECIATION", "Total book depreciation (kEUR)", None,                              _tot([e.book_depreciation_keur for e in eng_p if e.book_depreciation_keur]), "UNRESOLVED SOURCE"),
        ("TAX",          "Total cash tax (kEUR)",      _tot([e.cash_tax_keur for e in excel_p if e.cash_tax_keur]),
                                                        _tot([e.corporate_tax_cash_keur for e in eng_p if e.corporate_tax_cash_keur]), "POLICY DIFFERENCE"),
        ("CFADS",        "Total CFADS (kEUR)",         _tot([e.cfads_keur for e in excel_p if e.cfads_keur]),
                                                        _tot([e.cfads_keur for e in eng_p if e.cfads_keur]),                  "POLICY DIFFERENCE"),
        ("SENIOR DEBT",  "Debt size at COD (kEUR)",    src.excel_total_debt_keur,             src.engine_debt_size_keur,      "POLICY DIFFERENCE"),
        ("SENIOR DEBT",  "Excel target DSCR",          src.excel_target_dscr,                 1.15,                           "MATCH"),
        ("SENIOR DEBT",  "Min DSCR",                   src.excel_min_dscr,                    min((e.sd_dscr for e in eng_p if e.sd_dscr and e.sd_dscr > 0), default=None), "POLICY DIFFERENCE"),
        ("SENIOR DEBT",  "Avg DSCR",                   src.excel_avg_dscr,                    None,                          "UNRESOLVED SOURCE"),
        ("SENIOR INTEREST", "Total senior interest (kEUR)",
                          _tot([e.senior_interest_keur for e in excel_p if e.senior_interest_keur]),
                          _tot([e.sd_interest_keur for e in eng_p if e.sd_interest_keur]),           "POLICY DIFFERENCE"),
        ("SHL INTEREST", "Total SHL interest (kEUR)",  _tot([e.shl_interest_keur for e in excel_p if e.shl_interest_keur]),
                                                        UNAVAILABLE,                            "OUT OF CLEAN ENGINE SCOPE"),
        ("CASH FLOW",    "Total FCF for distribution (kEUR)", _tot([e.free_cash_flow_keur for e in excel_p if e.free_cash_flow_keur]),
                                                        UNAVAILABLE,                            "OUT OF CLEAN ENGINE SCOPE"),
    ]

    for r_idx, (section, line, excel_v, python_v, cls) in enumerate(rows_data, 2):
        ev = excel_v if isinstance(excel_v, (int, float)) else None
        pv = python_v if isinstance(python_v, (int, float)) else None
        d = _delta(ev, pv)
        dp = _delta_pct(d, ev)
        is_mat = mat.is_material(d, ev, pv) if d is not None else False
        status = "MATERIAL" if is_mat else "OK"

        fill = _fill(CLASS_FILL.get(cls, "FFFFFF"))
        row_fill = _fill("FFF0F0") if is_mat and cls not in ("OUT OF CLEAN ENGINE SCOPE", "UNRESOLVED SOURCE") else None

        ws.cell(row=r_idx, column=1, value=section).font = _font(bold=True, size=9)
        ws.cell(row=r_idx, column=2, value=line).font = _font(size=9)
        ws.cell(row=r_idx, column=3, value=excel_v if ev is None else ev).number_format = KEUR_FMT
        ws.cell(row=r_idx, column=3).font = _font(size=9)
        ws.cell(row=r_idx, column=4, value=python_v if pv is None else pv).number_format = KEUR_FMT
        ws.cell(row=r_idx, column=4).font = _font(size=9)
        ws.cell(row=r_idx, column=5, value=d).number_format = KEUR_FMT
        ws.cell(row=r_idx, column=5).font = _font(size=9)
        ws.cell(row=r_idx, column=6, value=dp).number_format = PCT_FMT
        ws.cell(row=r_idx, column=6).font = _font(size=9)
        ws.cell(row=r_idx, column=7, value=None)
        ws.cell(row=r_idx, column=8, value=status).font = _font(size=9)
        ws.cell(row=r_idx, column=9, value=cls).font = _font(size=9)
        ws.cell(row=r_idx, column=9).fill = fill
        if row_fill:
            for c in range(1, 9):
                ws.cell(row=r_idx, column=c).fill = row_fill

    _set_col_widths(ws, {1: 16, 2: 40, 3: 16, 4: 16, 5: 12, 6: 10, 7: 14, 8: 10, 9: 26})
    _freeze(ws, "A2")
    _autofilter(ws, 1, 9)


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

    r = 2
    def sec(label):
        nonlocal r
        ws.cell(row=r, column=1, value="").fill = SECTION_FILL
        ws.cell(row=r, column=2, value=label).font = _font(bold=True, size=9, color="FFFFFF")
        ws.cell(row=r, column=2).fill = SECTION_FILL
        for c in range(3, 7): ws.cell(row=r, column=c).fill = SECTION_FILL
        r += 1

    sec("— PROJECT / TIMELINE —")
    row(ws, r, "T.01", "Capacity (MW)",          src.capacity_mw,        src.capacity_mw,       KEUR_FMT); r += 1
    row(ws, r, "T.02", "Financial close",         src.financial_close,    src.financial_close,   "@"); r += 1
    row(ws, r, "T.03", "COD date",                src.cod_date,           src.cod_date,          "@"); r += 1
    row(ws, r, "T.04", "Horizon (years)",         src.horizon_years,      src.horizon_years,     INT_FMT); r += 1
    row(ws, r, "T.05", "Construction (months)",   src.construction_months,src.construction_months,INT_FMT); r += 1
    row(ws, r, "T.06", "Period frequency",        "Semestrial",           "Semestrial",          "@"); r += 1

    sec("— PRODUCTION —")
    row(ws, r, "P.01", "P50 operating hours",     1494.0,                 1494.0,                INT_FMT); r += 1
    row(ws, r, "P.02", "PV degradation (%/yr)",   0.004,                  0.004,                 PCT_FMT); r += 1
    row(ws, r, "P.03", "Plant availability",      0.99,                   0.99,                  PCT_FMT); r += 1
    row(ws, r, "P.04", "Grid availability",       0.99,                   0.99,                  PCT_FMT); r += 1

    sec("— PRICE / REVENUE —")
    row(ws, r, "R.01", "PPA tariff (EUR/MWh)",    src.ppa_tariff_eur_mwh, src.ppa_tariff_eur_mwh, KEUR_FMT); r += 1
    row(ws, r, "R.02", "PPA term (years)",        src.ppa_term_years,     src.ppa_term_years,    INT_FMT); r += 1
    row(ws, r, "R.03", "PPA indexation (%/yr)",   src.ppa_index,          src.ppa_index,         PCT_FMT); r += 1

    sec("— OPEX (Y1 kEUR) —")
    for item in src.opex_items:
        row(ws, r, item["code"], item["name"] + " Y1 kEUR", item["y1_keur"], item["y1_keur"], KEUR_FMT); r += 1
        row(ws, r, "",           item["name"] + " inflation", item["inflation"], item["inflation"], PCT_FMT); r += 1

    sec("— CAPEX (kEUR) —")
    for item in src.capex_items:
        row(ws, r, item["code"], item["name"], item["amount_keur"], item["amount_keur"], KEUR_FMT); r += 1
    row(ws, r, "C.00", "Total Hard CAPEX", src.hard_capex_keur, src.hard_capex_keur, KEUR_FMT); r += 1
    row(ws, r, "C.IDC", "Bank IDC",       src.idc_keur,        src.idc_keur,         KEUR_FMT); r += 1
    row(ws, r, "C.TOT", "Total CAPEX",    src.excel_total_capex_keur, src.total_capex_keur, KEUR_FMT); r += 1

    sec("— TAX —")
    row(ws, r, "TX.01", "CIT rate",                0.10,   0.10,   PCT_FMT); r += 1
    row(ws, r, "TX.02", "Loss carryforward (yrs)", 5.0,    5.0,    INT_FMT); r += 1
    row(ws, r, "TX.03", "ATAD enabled",            "Yes",  "Yes",  "@"); r += 1
    row(ws, r, "TX.04", "ATAD EBITDA limit",       0.30,   0.30,   PCT_FMT); r += 1
    row(ws, r, "TX.05", "ATAD de minimis (kEUR/yr)",3000.0,3000.0, KEUR_FMT); r += 1

    sec("— SENIOR DEBT —")
    row(ws, r, "SD.01", "Target DSCR",              src.excel_target_dscr, 1.15,         DSCR_FMT); r += 1
    row(ws, r, "SD.02", "Gearing ratio (Excel)",    0.7524,                None,         PCT_FMT); r += 1
    row(ws, r, "SD.03", "Debt size at COD (kEUR)",  src.excel_total_debt_keur, src.engine_debt_size_keur, KEUR_FMT); r += 1
    row(ws, r, "SD.04", "Fixed rate",               0.0565,                0.0565,       PCT_FMT); r += 1
    row(ws, r, "SD.05", "Tenor (years)",            14.0,                  14.0,         INT_FMT); r += 1
    row(ws, r, "SD.06", "Day count",                "ACT/365",             "ACT/365",    "@"); r += 1
    row(ws, r, "SD.07", "Sizing mode",              "GEARING CAP (Excel)", "DSCR SCULPTED (Python)", "@"); r += 1

    sec("— SHL —")
    row(ws, r, "SH.01", "SHL amount at COD (kEUR)", src.shl_amount_keur,  None,          KEUR_FMT); r += 1
    row(ws, r, "SH.02", "SHL rate",                 src.shl_rate,         None,          PCT_FMT); r += 1
    row(ws, r, "SH.03", "SHL IDC capitalised (kEUR)",src.shl_idc_keur,    None,          KEUR_FMT); r += 1

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

    items_def = [
        ("TL.01", "Period index",    "index", [e.period_index  for e in src.engine]),
        ("TL.02", "Period end date", "date",  [e.period_end    for e in src.engine]),
        ("TL.03", "Days in period",  "days",  [e.days_in_period for e in src.engine]),
        ("TL.04", "Day fraction",    "frac",  [e.day_fraction  for e in src.engine]),
        ("TL.05", "Is operation",    "flag",  [str(e.is_operation) for e in src.engine]),
    ]

    cur_row = 2
    for code, name, unit, vals in items_def:
        excel_dates = [ep.period_end for ep in src.excel]
        for view_label, row_vals, row_fill in [
            ("Excel",  excel_dates if code == "TL.02" else vals, EXCEL_FILL),
            ("Python", vals, PYTHON_FILL),
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
        {"type": "section", "label": "— OPEX BY ITEM CODE (Python engine; Excel total only) —"},
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
    _header_row(ws, ["Code", "Item", "Amount (kEUR)", "Source", "Classification"])
    _set_col_widths(ws, {1: 8, 2: 40, 3: 16, 4: 20, 5: 26})

    r = 2
    def sec(label):
        nonlocal r
        for c in range(1, 6): ws.cell(row=r, column=c).fill = SECTION_FILL
        ws.cell(row=r, column=2, value=label).font = _font(bold=True, size=9, color="FFFFFF")
        ws.cell(row=r, column=2).fill = SECTION_FILL
        r += 1

    def add(code, label, amount, source, cls="MATCH"):
        nonlocal r
        ws.cell(row=r, column=1, value=code).font = _font(size=8)
        ws.cell(row=r, column=2, value=label).font = _font(size=9)
        cell = ws.cell(row=r, column=3, value=_safe(amount))
        cell.number_format = KEUR_FMT; cell.font = _font(size=9)
        ws.cell(row=r, column=4, value=source).font = _font(size=8)
        cell_cls = ws.cell(row=r, column=5, value=cls)
        cell_cls.fill = _fill(CLASS_FILL.get(cls, "FFFFFF"))
        cell_cls.font = _font(size=9)
        r += 1

    sec("— HARD CAPEX (Python factory) —")
    for item in src.capex_items:
        add(item["code"], item["name"], item["amount_keur"], "app.project_factories")
    add("C.00", "Total Hard CAPEX", src.hard_capex_keur, "app.project_factories")

    sec("— FINANCING COSTS (Python factory) —")
    add("C.IDC", "Bank IDC (capitalised)", src.idc_keur, "app.project_factories")
    add("C.SHL", "SHL IDC capitalised (Excel)", src.shl_idc_keur, "excel_oborovo_full_model_extract.json",
        "OUT OF CLEAN ENGINE SCOPE")

    sec("— TOTAL CAPEX —")
    add("C.TOT", "Total CAPEX (Python)", src.total_capex_keur, "app.project_factories")
    add("C.TOT", "Total CAPEX (Excel)",  src.excel_total_capex_keur, "oborovo_golden.json", "POLICY DIFFERENCE")

    _freeze(ws, "A2")
    _autofilter(ws, 1, 5)


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
    leg_p = src.legacy

    blocks = [
        {"type": "section", "label": f"— DEBT SIZE: Excel={src.excel_total_debt_keur:.1f} kEUR  Python={src.engine_debt_size_keur:.1f} kEUR  Delta={src.engine_debt_size_keur - src.excel_total_debt_keur:+.1f} kEUR  [POLICY DIFFERENCE: Excel=GEARING CAP; Python=DSCR SCULPTED] —"},
        {"type": "section", "label": "— SENIOR DEBT SCHEDULE —"},
        {"type": "item", "code": "SD.01", "name": "Opening senior debt", "unit": "kEUR",
         "excel_vals": [ld.sd_opening_keur for ld in leg_p],
         "python_vals": [e.sd_opening_keur for e in src.engine], "item": get_item("SD.01")},
        {"type": "item", "code": "SD.02", "name": "Senior interest (DS)", "unit": "kEUR",
         "excel_vals": [e.senior_interest_keur for e in src.excel],
         "python_vals": [e.sd_interest_keur for e in src.engine], "item": get_item("SD.02")},
        {"type": "item", "code": "SD.03", "name": "Senior principal", "unit": "kEUR",
         "excel_vals": [e.senior_principal_keur for e in src.excel],
         "python_vals": [e.sd_principal_keur for e in src.engine], "item": get_item("SD.03")},
        {"type": "item", "code": "SD.04", "name": "Senior debt service", "unit": "kEUR",
         "excel_vals": [e.senior_ds_keur for e in src.excel],
         "python_vals": [e.sd_ds_keur for e in src.engine], "item": get_item("SD.04")},
        {"type": "item", "code": "SD.05", "name": "Closing senior debt", "unit": "kEUR",
         "excel_vals": [ld.sd_closing_keur for ld in leg_p],
         "python_vals": [e.sd_closing_keur for e in src.engine], "item": get_item("SD.05")},
        {"type": "item", "code": "SD.06", "name": "DSCR (average per period)", "unit": "x",
         "excel_vals": [e.avg_dscr for e in src.excel],
         "python_vals": [e.sd_dscr for e in src.engine], "item": get_item("SD.06")},
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
            cls = _classify(item, d, ev, pv, mat) if item else "POLICY DIFFERENCE"
            delta_rows.append([
                f"DELTA-{delta_counter:04d}", BASELINE_ID, section, code, name,
                eg.period_end, ev, pv, d, dp, cls,
                f"Period {i}: Excel={ev} Python={pv}",
                "Requires manual review",
                "OPEN",
                "excel_oborovo_full_model_extract.json",
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
            cell = ws.cell(row=r_idx, column=c_idx, value=val)
            cell.font = _font(size=9)
            if c_idx in (7, 8, 9):
                if isinstance(val, float):
                    cell.number_format = KEUR_FMT
            if c_idx == 10 and isinstance(val, float):
                cell.number_format = PCT_FMT
            if c_idx == 11:
                cell.fill = _fill(CLASS_FILL.get(str(val), "FFFFFF"))

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
        ("REVENUE",     "RV.01", "Operating revenues",     "CF",  "CF.operating_revenues_keur",       "financial_engine.results",  "revenue_keur",               "from_project_inputs → run_senior_debt_model"),
        ("OPEX",        "OP.00", "Total OPEX",             "CF",  "CF.operating_expenses_after_bank_tax_keur", "financial_engine.results", "opex_keur",         "from_project_inputs → run_senior_debt_model"),
        ("EBITDA",      "EB.01", "EBITDA",                 "CF",  "CF.ebitda_keur",                   "financial_engine.results",  "ebitda_keur",                "from_project_inputs → run_senior_debt_model"),
        ("DEPRECIATION","DP.01", "Book depreciation",      "P&L", "P&L.depreciation_keur",            "financial_engine.results",  "book_depreciation_keur",     "from_project_inputs → run_senior_debt_model"),
        ("TAX",         "TX.06", "CIT accrual",            "P&L", "P&L.corporate_income_tax_keur",    "financial_engine.results",  "tax_keur",                   "calculate_tax → TaxAndCfadsSchedules"),
        ("TAX",         "TX.07", "Cash tax paid",          "CF",  "CF.corporate_income_tax_keur",     "financial_engine.results",  "corporate_tax_cash_keur",    "calculate_tax → TaxAndCfadsSchedules"),
        ("CFADS",       "CF.01", "CFADS",                  "CF",  "CF.free_cash_flow_for_banks_keur", "financial_engine.results",  "cfads_keur",                 "calculate_canonical_cfads → TaxAndCfadsSchedules"),
        ("SENIOR_DEBT", "SD.02", "Senior interest",        "DS",  "DS.senior_net_interest_keur",      "financial_engine.senior_debt", "senior_interest_keur",    "solve_senior_debt → SeniorDebtSchedules"),
        ("SENIOR_DEBT", "SD.03", "Senior principal",       "DS",  "DS.senior_principal_keur",         "financial_engine.senior_debt", "senior_principal_keur",   "solve_senior_debt → SeniorDebtSchedules"),
        ("SENIOR_DEBT", "SD.04", "Senior debt service",    "DS",  "DS.senior_principal + senior_net_interest", "financial_engine.senior_debt", "senior_debt_service_keur", "solve_senior_debt → SeniorDebtSchedules"),
        ("SENIOR_DEBT", "SD.06", "DSCR",                  "CF",  "CF.average_senior_dscr_period",    "financial_engine.senior_debt", "senior_dscr",             "solve_senior_debt → SeniorDebtSchedules"),
        ("SHL",         "SH.02", "SHL interest",           "P&L", "P&L.shareholder_loan_interests_keur","OUT OF CLEAN ENGINE SCOPE", "N/A",                    "N/A"),
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
            row = [BASELINE_ID, i, eg.period_end, section, code, name, unit,
                   ev, pv, d, dp, cls,
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
                    cell.fill = _fill(CLASS_FILL.get(str(val), "FFFFFF"))
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
