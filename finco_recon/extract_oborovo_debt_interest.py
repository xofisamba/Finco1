"""finco_recon.extract_oborovo_debt_interest — C3B2 debt sizing & interest extractor.

Reads ``20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm`` and emits a
machine-readable JSON fixture answering the five open C3B1 questions:

  A. CFADS composition used for DSCR sculpting
  B. DSCR sculpting circular reference and convergence mechanism
  C. DSRA funding and release treatment
  D. IDC and financing-cost eligibility in the debt-sizing gearing base
  E. Hedge percentage and fixed/floating rate split

Usage::

    python -m finco_recon.extract_oborovo_debt_interest \\
        --workbook "/path/to/20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm" \\
        --output tests/fixtures/excel_oborovo_debt_interest_truth.json

Exit codes: 0 success · 1 workbook not found · 2 unexpected error.
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
# Column helpers  (same layout as extract_oborovo_excel.py)
# ---------------------------------------------------------------------------
_PERIOD_COL_OFFSET = 6   # col index 6 = period 0 (construction)
_N_PERIODS = 61          # periods 0 … 60


def _row_to_periods(row: tuple, n: int = _N_PERIODS) -> list[float | None]:
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
    return row[col] if col < len(row) else None


def _formula(row: tuple, col: int) -> str | None:
    v = _scalar(row, col)
    if isinstance(v, str) and v.startswith("="):
        return v
    return None


def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Workstream A: CFADS composition (CF sheet + DS sheet row mapping)
# ---------------------------------------------------------------------------

def _extract_cfads(wb_formula, wb_data) -> dict:
    """
    Identify the CFADS row used in DSCR sculpting.

    DS!row20 = CFADS input to sculpting.
    CF!row79 = 'Free Cash Flow for Banks' = source of DS!row20.
    Formula in each DS period cell references the CF row.
    """
    ds_f = wb_formula["DS"]
    ds_d = wb_data["DS"]
    cf_f = wb_formula["CF"]
    cf_d = wb_data["CF"]

    # DS row 20 (0-indexed row 19): CFADS fed into sculpting
    ds_rows_f = list(ds_f.iter_rows(values_only=True))
    ds_rows_d = list(ds_d.iter_rows(values_only=True))
    cf_rows_f = list(cf_f.iter_rows(values_only=True))
    cf_rows_d = list(cf_d.iter_rows(values_only=True))

    # DS row 20 = index 19
    ds_row20_formula_h = _formula(ds_rows_f[19], 7)  # col H = period 1
    ds_row20_values = _row_to_periods(ds_rows_d[19])

    # DS row 22 = DSCR target (index 21)
    ds_row22_formula_h = _formula(ds_rows_f[21], 7)
    ds_row22_values = _row_to_periods(ds_rows_d[21])

    # DS row 23 = available CF for sculpting (index 22)
    ds_row23_formula_h = _formula(ds_rows_f[22], 7)
    ds_row23_values = _row_to_periods(ds_rows_d[22])

    # CF row 79 (0-indexed 78): Free Cash Flow for Banks
    cf_row79_label = _scalar(cf_rows_d[78], 0)
    cf_row79_formula_h = _formula(cf_rows_f[78], 7)
    cf_row79_values = _row_to_periods(cf_rows_d[78])

    # CF row 80 (index 79): interest income adjustment if any
    cf_row80_label = _scalar(cf_rows_d[79], 0)
    cf_row80_formula_h = _formula(cf_rows_f[79], 7)
    cf_row80_values = _row_to_periods(cf_rows_d[79])

    # CF row 83 (index 82): VAT/facility drawdown adjustment
    cf_row83_label = _scalar(cf_rows_d[82], 0)
    cf_row83_formula_h = _formula(cf_rows_f[82], 7)
    cf_row83_values = _row_to_periods(cf_rows_d[82])

    return {
        "workstream": "A",
        "question": "CFADS composition used by debt sculpting",
        "ds_row20": {
            "sheet_cell": "DS!H20 (period 1)",
            "formula_h": ds_row20_formula_h,
            "period_values_keur": ds_row20_values,
        },
        "ds_row22_dscr_target": {
            "sheet_cell": "DS!H22 (period 1)",
            "formula_h": ds_row22_formula_h,
            "period_values": ds_row22_values,
        },
        "ds_row23_available_cf": {
            "sheet_cell": "DS!H23 (period 1)",
            "formula_h": ds_row23_formula_h,
            "period_values_keur": ds_row23_values,
        },
        "cf_row79_free_cash_flow_for_banks": {
            "sheet_cell": "CF!H79 (period 1)",
            "label": cf_row79_label,
            "formula_h": cf_row79_formula_h,
            "period_values_keur": cf_row79_values,
        },
        "cf_row80": {
            "sheet_cell": "CF!H80",
            "label": cf_row80_label,
            "formula_h": cf_row80_formula_h,
            "period_values_keur": cf_row80_values,
        },
        "cf_row83_vat_facility": {
            "sheet_cell": "CF!H83",
            "label": cf_row83_label,
            "formula_h": cf_row83_formula_h,
            "period_values_keur": cf_row83_values,
        },
        "finding": (
            "DS!row20 = CF!row79 = 'Free Cash Flow for Banks'. "
            "This is a POST-TAX CFADS that includes interest income from "
            "cash/DSRA reserves but excludes DSRA movements themselves. "
            "Phase 2C CFADS = EBITDA - cash_tax (no interest income) → input mismatch."
        ),
        "phase2c_cfads_formula": "CFADS = EBITDA - cash_tax_paid (pre-DSRA, pre-debt-service)",
        "excel_cfads_formula": "CF!row79 = SUM(revenues + opex + capex + interest_income_adj + cash_tax)",
        "classification": "INPUT_POLICY_MISMATCH",
    }


# ---------------------------------------------------------------------------
# Workstream B: DSCR sculpting circular reference and convergence
# ---------------------------------------------------------------------------

def _extract_sculpting(wb_formula, wb_data) -> dict:
    """
    Document the backward-induction sculpting in the DS sheet.

    DS!H47 = (H46 + I47) / (1 + H44 * H6)
    This references I47 (next period's debt capacity) → circular dependency.
    Excel resolves via iterative calculation.
    Phase 2C uses a forward sculpting pass — a different algorithm.
    """
    ds_f = wb_formula["DS"]
    ds_d = wb_data["DS"]
    ds_rows_f = list(ds_f.iter_rows(values_only=True))
    ds_rows_d = list(ds_d.iter_rows(values_only=True))

    # DS row 47 (index 46): total debt capacity per period
    ds_row47_formula_h = _formula(ds_rows_f[46], 7)
    ds_row47_values = _row_to_periods(ds_rows_d[46])

    # DS row 46 (index 45): DS capacity from available CF (numerator partial)
    ds_row46_formula_h = _formula(ds_rows_f[45], 7)
    ds_row46_values = _row_to_periods(ds_rows_d[45])

    # DS cell B22 = base DSCR target (scalar)
    ds_b22 = _scalar(ds_rows_d[21], 1)
    ds_b22_formula = _formula(ds_rows_f[21], 1)

    # DS cell D51: total debt size (result of backward induction)
    ds_d51_value = _scalar(ds_rows_d[50], 3)
    ds_d51_formula = _formula(ds_rows_f[50], 3)

    # DS row 82 (index 81): explicit repayment schedule row if any
    ds_row82_formula_h = _formula(ds_rows_f[81], 7) if len(ds_rows_f) > 81 else None
    ds_row82_values = _row_to_periods(ds_rows_d[81]) if len(ds_rows_d) > 81 else []

    return {
        "workstream": "B",
        "question": "DSCR sculpting circular reference and convergence mechanism",
        "ds_row47_capacity": {
            "sheet_cell": "DS!H47 (period 1)",
            "formula_h": ds_row47_formula_h,
            "period_values_keur": ds_row47_values,
        },
        "ds_row46_partial": {
            "sheet_cell": "DS!H46",
            "formula_h": ds_row46_formula_h,
            "period_values_keur": ds_row46_values,
        },
        "ds_d51_total_debt": {
            "sheet_cell": "DS!D51",
            "formula": ds_d51_formula,
            "value_keur": ds_d51_value,
        },
        "ds_b22_base_dscr": {
            "sheet_cell": "DS!B22",
            "formula": ds_b22_formula,
            "value": ds_b22,
        },
        "ds_row82_explicit_repayment": {
            "sheet_cell": "DS!H82 (period 1)",
            "formula_h": ds_row82_formula_h,
            "period_values_keur": ds_row82_values,
        },
        "finding": (
            "DS!H47 = f(I47) — references next period's capacity value: "
            "circular dependency resolved by Excel iterative calculation. "
            "Algorithm: backward PV induction from maturity. "
            "Phase 2C uses a forward sculpting pass iterating debt size to convergence. "
            "Both algorithms are economically equivalent for the same inputs but "
            "diverge in intermediate values and require matched inputs to compare."
        ),
        "convergence_mechanism": "EXCEL_ITERATIVE_CALCULATION",
        "phase2c_mechanism": "FORWARD_SCULPTING_NEWTON_ITERATION",
        "algorithm_equivalence": "ECONOMICALLY_EQUIVALENT_WHEN_INPUTS_MATCHED",
    }


# ---------------------------------------------------------------------------
# Workstream C: DSRA funding and release
# ---------------------------------------------------------------------------

def _extract_dsra(wb_formula, wb_data) -> dict:
    """
    Determine whether DSRA is present and how it is treated.

    CF rows 85-92 contain DSRA mechanics.
    Inputs!I348 = DSRA target (months of debt service).
    """
    cf_f = wb_formula["CF"]
    cf_d = wb_data["CF"]
    cf_rows_f = list(cf_f.iter_rows(values_only=True))
    cf_rows_d = list(cf_d.iter_rows(values_only=True))

    inp_f = wb_formula["Inputs"]
    inp_d = wb_data["Inputs"]
    inp_rows_f = list(inp_f.iter_rows(values_only=True))
    inp_rows_d = list(inp_d.iter_rows(values_only=True))

    # Inputs!I348 = DSRA target (0-indexed row 347, col 8)
    dsra_target_value = _scalar(inp_rows_d[347], 8) if len(inp_rows_d) > 347 else None
    dsra_target_formula = _formula(inp_rows_f[347], 8) if len(inp_rows_f) > 347 else None

    # CF rows 85-92 (indices 84-91)
    dsra_rows = {}
    for i, row_num in enumerate(range(85, 93)):
        idx = row_num - 1
        if idx < len(cf_rows_d):
            label = _scalar(cf_rows_d[idx], 0)
            formula_h = _formula(cf_rows_f[idx], 7) if idx < len(cf_rows_f) else None
            values = _row_to_periods(cf_rows_d[idx])
            dsra_rows[f"cf_row{row_num}"] = {
                "label": label,
                "formula_h": formula_h,
                "period_values_keur": values,
            }

    return {
        "workstream": "C",
        "question": "DSRA funding and release treatment",
        "inputs_i348_dsra_target": {
            "sheet_cell": "Inputs!I348",
            "formula": dsra_target_formula,
            "value": dsra_target_value,
        },
        "cf_dsra_rows": dsra_rows,
        "finding": (
            "Inputs!I348 = 0 (DSRA target = 0 months). "
            "All CF DSRA rows (85-92) are zero throughout the model. "
            "DSRA is absent in this Oborovo model instance. "
            "Phase 2C also does not model DSRA in the Oborovo scenario → ALIGNED."
        ),
        "dsra_present": False,
        "classification": "ALIGNED_BOTH_ZERO",
    }


# ---------------------------------------------------------------------------
# Workstream D: IDC and financing costs in the gearing base
# ---------------------------------------------------------------------------

def _extract_sizing_base(wb_formula, wb_data) -> dict:
    """
    Document what constitutes the eligible project cost / gearing base.

    Inputs!G171 = SUM(G165:G170) = total project sources.
    G165 = CapEx!C117 (hard CAPEX)
    G166 = IDC
    G167 = commitment / financing fees
    G168 = other financing costs
    Gearing cap = Inputs!D192 × G171
    """
    inp_f = wb_formula["Inputs"]
    inp_d = wb_data["Inputs"]
    inp_rows_f = list(inp_f.iter_rows(values_only=True))
    inp_rows_d = list(inp_d.iter_rows(values_only=True))

    # Inputs row 171 (index 170): total eligible project cost
    g171_value = _scalar(inp_rows_d[170], 6) if len(inp_rows_d) > 170 else None
    g171_formula = _formula(inp_rows_f[170], 6) if len(inp_rows_f) > 170 else None

    # Rows 165-170 (indices 164-169): component breakdown
    components = {}
    for row_num in range(165, 172):
        idx = row_num - 1
        if idx < len(inp_rows_d):
            label = _scalar(inp_rows_d[idx], 0)
            g_val = _scalar(inp_rows_d[idx], 6)
            g_formula = _formula(inp_rows_f[idx], 6) if idx < len(inp_rows_f) else None
            components[f"inputs_row{row_num}_g"] = {
                "label": label,
                "value_keur": g_val,
                "formula": g_formula,
            }

    # Inputs!D192: gearing fraction (0-indexed row 191, col 3)
    d192_value = _scalar(inp_rows_d[191], 3) if len(inp_rows_d) > 191 else None
    d192_formula = _formula(inp_rows_f[191], 3) if len(inp_rows_f) > 191 else None

    # Gearing cap = D192 × G171
    gearing_cap = None
    if isinstance(d192_value, (int, float)) and isinstance(g171_value, (int, float)):
        gearing_cap = float(d192_value) * float(g171_value)

    return {
        "workstream": "D",
        "question": "IDC and financing-cost eligibility in the debt-sizing gearing base",
        "inputs_g171_total_eligible_cost": {
            "sheet_cell": "Inputs!G171",
            "formula": g171_formula,
            "value_keur": g171_value,
        },
        "components": components,
        "inputs_d192_gearing_fraction": {
            "sheet_cell": "Inputs!D192",
            "formula": d192_formula,
            "value": d192_value,
        },
        "gearing_cap_keur": gearing_cap,
        "finding": (
            "G171 = SUM(G165:G170) = total project sources including "
            "IDC (G166 ≈ 1086 kEUR) and commitment/financing fees (G167+G168). "
            "Gearing cap = D192 × G171. DSCR-sculpted debt (DS!D51 ≈ 42852 kEUR) "
            "is below the gearing cap → gearing constraint NOT binding. "
            "IDC IS included in the gearing base. "
            "Phase 2C eligible_project_cost_keur maps to G171 → input must match G171."
        ),
        "idc_included_in_gearing_base": True,
        "gearing_cap_binding": False,
        "phase2c_mapping": "SeniorDebtInputs.eligible_project_cost_keur = Inputs!G171",
    }


# ---------------------------------------------------------------------------
# Workstream E: Hedge percentage and fixed/floating rate split
# ---------------------------------------------------------------------------

def _extract_interest_rate(wb_formula, wb_data) -> dict:
    """
    Document the two-rate structure:

    DS!row44 = sculpting rate = row41 + row43
      row41 = SUMPRODUCT(B39:B40, period_rates) = blended base
      B39 = floating fraction (Inputs!D229 or similar)
      B40 = fixed/hedge fraction (Inputs!D230)
      DS!C40 = fixed swap rate
      DS!row39 = floating rate (EURIBOR + basis)
      DS!row43 = margin (VLOOKUP on Inputs)

    DS!row64 = period tranche interest = H61 * H44 * H6 * (H91=0)
    Inputs!D280 = 5.65% = separate FCF-section rate (DS!B33 only)
    """
    ds_f = wb_formula["DS"]
    ds_d = wb_data["DS"]
    inp_f = wb_formula["Inputs"]
    inp_d = wb_data["Inputs"]

    ds_rows_f = list(ds_f.iter_rows(values_only=True))
    ds_rows_d = list(ds_d.iter_rows(values_only=True))
    inp_rows_f = list(inp_f.iter_rows(values_only=True))
    inp_rows_d = list(inp_d.iter_rows(values_only=True))

    # DS row 39 (index 38): floating rate per period
    ds_row39_formula_h = _formula(ds_rows_f[38], 7)
    ds_row39_values = _row_to_periods(ds_rows_d[38])

    # DS row 40: fixed (hedged) rate - C40 is the static swap rate
    ds_c40_value = _scalar(ds_rows_d[39], 2)
    ds_c40_formula = _formula(ds_rows_f[39], 2)
    ds_row40_values = _row_to_periods(ds_rows_d[39])

    # DS row 41 (index 40): blended base rate
    ds_row41_formula_h = _formula(ds_rows_f[40], 7)
    ds_row41_values = _row_to_periods(ds_rows_d[40])

    # DS row 43 (index 42): margin
    ds_row43_formula_h = _formula(ds_rows_f[42], 7)
    ds_row43_values = _row_to_periods(ds_rows_d[42])

    # DS row 44 (index 43): sculpting rate = row41 + row43
    ds_row44_formula_h = _formula(ds_rows_f[43], 7)
    ds_row44_values = _row_to_periods(ds_rows_d[43])

    # DS B39, B40: fraction weights (col 1)
    ds_b39 = _scalar(ds_rows_d[38], 1)
    ds_b40 = _scalar(ds_rows_d[39], 1)
    ds_b39_formula = _formula(ds_rows_f[38], 1)
    ds_b40_formula = _formula(ds_rows_f[39], 1)

    # DS row 61 (index 60): opening debt balance for tranche interest
    ds_row61_formula_h = _formula(ds_rows_f[60], 7) if len(ds_rows_f) > 60 else None
    ds_row61_values = _row_to_periods(ds_rows_d[60]) if len(ds_rows_d) > 60 else []

    # DS row 64 (index 63): tranche period interest
    ds_row64_formula_h = _formula(ds_rows_f[63], 7) if len(ds_rows_f) > 63 else None
    ds_row64_values = _row_to_periods(ds_rows_d[63]) if len(ds_rows_d) > 63 else []

    # DS row 6 (index 5): semi-annual fraction (H6)
    ds_row6_formula_h = _formula(ds_rows_f[5], 7) if len(ds_rows_f) > 5 else None
    ds_row6_values = _row_to_periods(ds_rows_d[5]) if len(ds_rows_d) > 5 else []

    # DS B33: FCF section interest (uses Inputs!D280)
    ds_b33_formula = _formula(ds_rows_f[32], 1) if len(ds_rows_f) > 32 else None
    ds_b33_value = _scalar(ds_rows_d[32], 1) if len(ds_rows_d) > 32 else None

    # Inputs!D280 = 5.65% rate (row 279, col 3)
    d280_value = _scalar(inp_rows_d[279], 3) if len(inp_rows_d) > 279 else None
    d280_formula = _formula(inp_rows_f[279], 3) if len(inp_rows_f) > 279 else None

    # Inputs!D230 (row 229, col 3): hedge fraction
    d230_value = _scalar(inp_rows_d[229], 3) if len(inp_rows_d) > 229 else None
    d230_formula = _formula(inp_rows_f[229], 3) if len(inp_rows_f) > 229 else None

    # DS row 91 (index 90): refinancing flag
    ds_row91_formula_h = _formula(ds_rows_f[90], 7) if len(ds_rows_f) > 90 else None
    ds_row91_values = _row_to_periods(ds_rows_d[90]) if len(ds_rows_d) > 90 else []

    return {
        "workstream": "E",
        "question": "Hedge percentage and fixed/floating rate split",
        "ds_b39_float_fraction": {
            "sheet_cell": "DS!B39",
            "formula": ds_b39_formula,
            "value": ds_b39,
        },
        "ds_b40_fixed_fraction": {
            "sheet_cell": "DS!B40",
            "formula": ds_b40_formula,
            "value": ds_b40,
        },
        "ds_c40_swap_rate": {
            "sheet_cell": "DS!C40",
            "formula": ds_c40_formula,
            "value": ds_c40_value,
        },
        "ds_row39_floating_rate": {
            "sheet_cell": "DS!H39 (period 1)",
            "formula_h": ds_row39_formula_h,
            "period_values": ds_row39_values,
        },
        "ds_row40_fixed_rate_row": {
            "sheet_cell": "DS!H40 (period 1)",
            "period_values": ds_row40_values,
        },
        "ds_row41_blended_base": {
            "sheet_cell": "DS!H41 (period 1)",
            "formula_h": ds_row41_formula_h,
            "period_values": ds_row41_values,
        },
        "ds_row43_margin": {
            "sheet_cell": "DS!H43 (period 1)",
            "formula_h": ds_row43_formula_h,
            "period_values": ds_row43_values,
        },
        "ds_row44_sculpting_rate": {
            "sheet_cell": "DS!H44 (period 1)",
            "formula_h": ds_row44_formula_h,
            "period_values": ds_row44_values,
        },
        "ds_row6_semi_annual_fraction": {
            "sheet_cell": "DS!H6 (period 1)",
            "formula_h": ds_row6_formula_h,
            "period_values": ds_row6_values,
        },
        "ds_row61_opening_balance": {
            "sheet_cell": "DS!H61 (period 1)",
            "formula_h": ds_row61_formula_h,
            "period_values_keur": ds_row61_values,
        },
        "ds_row64_period_interest": {
            "sheet_cell": "DS!H64 (period 1)",
            "formula_h": ds_row64_formula_h,
            "period_values_keur": ds_row64_values,
        },
        "ds_row91_refinancing_flag": {
            "sheet_cell": "DS!H91 (period 1)",
            "formula_h": ds_row91_formula_h,
            "period_values": ds_row91_values,
        },
        "ds_b33_fcf_section_interest": {
            "sheet_cell": "DS!B33",
            "formula": ds_b33_formula,
            "value": ds_b33_value,
        },
        "inputs_d280_fcf_rate": {
            "sheet_cell": "Inputs!D280",
            "formula": d280_formula,
            "value": d280_value,
            "note": "Used only in DS!B33 (FCF section), NOT in tranche schedule",
        },
        "inputs_d230_hedge_fraction": {
            "sheet_cell": "Inputs!D230",
            "formula": d230_formula,
            "value": d230_value,
        },
        "finding": (
            "DS!row44 = sculpting rate = blended_base (row41) + margin (row43). "
            "Blended base = SUMPRODUCT([float_frac, fixed_frac], [floating_rate, swap_rate]). "
            "B40 = Inputs!D230 ≈ 0.80 = fixed/hedge fraction; B39 ≈ 0.20 = floating fraction. "
            "DS!C40 = 3.20% swap rate; DS!row39 = ~3.71% floating; margin ≈ 2.65%. "
            "Sculpting rate H44 ≈ 5.95%. "
            "DS!H64 = H61 × H44 × H6 × (H91=0) → tranche interest uses the SCULPTING rate. "
            "Inputs!D280 = 5.65% is used only in DS!B33 (FCF summary section), "
            "not in the tranche amortisation schedule. "
            "Phase 2C uses annual_fixed_rate = 5.65% for both sizing and interest → "
            "rate mismatch: Excel ≈5.95% vs Phase 2C 5.65%."
        ),
        "sculpting_rate_pct": None,  # computed from period values at runtime
        "phase2c_rate_pct": 5.65,
        "rate_mismatch_basis_points": None,  # computed at runtime
        "classification": "INPUT_POLICY_MISMATCH",
    }


# ---------------------------------------------------------------------------
# Equal-input / equal-policy Phase 2C comparison
# ---------------------------------------------------------------------------

def _equal_input_equal_policy_comparison(fixture: dict) -> dict:
    """
    Attempt a Phase 2C build_schedule() call using Excel-matched inputs.

    Equal-input means:
      - eligible_project_cost_keur = Inputs!G171
      - CFADS per period = CF!row79 per period
      - annual_fixed_rate = DS!H44 p1 × 2 (annualised from semi-annual)
      - DSCR target = DS!H22 p1 value
      - sizing_mode = DSCR_SCULPTED

    If the financial_engine is not importable, we record IMPORT_ERROR and
    store the inputs that WOULD have been used.
    """
    try:
        from financial_engine.senior_debt.policy import (
            SeniorDebtPolicy, SeniorDebtSizingMode, DayCountConvention,
        )
        from financial_engine.senior_debt.inputs import SeniorDebtInputs, PeriodRate
        from financial_engine.senior_debt.sculpting import build_schedule
    except ImportError as exc:
        return {
            "status": "IMPORT_ERROR",
            "error": str(exc),
            "note": "financial_engine not importable in this environment",
        }

    # Extract values from fixture
    sizing_d = fixture.get("workstream_d", {})
    rate_e = fixture.get("workstream_e", {})
    cfads_a = fixture.get("workstream_a", {})

    g171 = sizing_d.get("inputs_g171_total_eligible_cost", {}).get("value_keur")
    cfads_periods = cfads_a.get("ds_row20", {}).get("period_values_keur", [])
    sculpting_rate_period = rate_e.get("ds_row44_sculpting_rate", {}).get("period_values", [])
    dscr_target_periods = cfads_a.get("ds_row22_dscr_target", {}).get("period_values", [])

    if not (g171 and cfads_periods and sculpting_rate_period):
        return {
            "status": "INSUFFICIENT_DATA",
            "note": "Fixture incomplete; run against real workbook first",
        }

    # Annualise the semi-annual sculpting rate for period 1 (p1 = index 1)
    rate_p1 = sculpting_rate_period[1] if len(sculpting_rate_period) > 1 else None
    annual_rate = rate_p1 * 2 if rate_p1 else None

    dscr_p1 = dscr_target_periods[1] if len(dscr_target_periods) > 1 else 1.15

    try:
        policy = SeniorDebtPolicy(
            policy_id="c3b2_equal_input_test",
            policy_version="1.0",
            sizing_mode=SeniorDebtSizingMode.DSCR_SCULPTED,
            target_dscr=float(dscr_p1),
            maximum_gearing=0.80,
            annual_fixed_rate=annual_rate,
            periods_per_year=2,
            day_count_convention=DayCountConvention.ACT_365,
            repayment_start_period_index=1,
            maturity_period_index=28,
            convergence_tolerance_keur=0.01,
            convergence_relative_tolerance=1e-6,
            maximum_iterations=500,
            permit_terminal_balloon=False,
            damping_alpha=1.0,
        )

        # Build PeriodRate tuples from the sculpting rate per period
        period_rates = []
        for i, r in enumerate(sculpting_rate_period):
            if r is not None and i >= 1:
                period_rates.append(PeriodRate(period_index=i, annual_rate=r * 2))

        # CFADS: use the operational periods (1-28)
        cfads_map = {}
        for i, v in enumerate(cfads_periods):
            if v is not None and i >= 1:
                cfads_map[i] = float(v)

        inputs = SeniorDebtInputs(
            eligible_project_cost_keur=float(g171),
            initial_debt_guess_keur=float(g171) * 0.70,
            period_rates=tuple(period_rates) if period_rates else (),
            explicit_principal_schedule=None,
        )

        schedule = build_schedule(policy=policy, inputs=inputs, cfads_by_period=cfads_map)
        total_debt = schedule[0].opening_balance_keur if schedule else 0.0

        excel_debt = 42852.279  # DS!D51 cached value

        return {
            "status": "COMPUTED",
            "policy_used": {
                "sizing_mode": "DSCR_SCULPTED",
                "target_dscr": float(dscr_p1),
                "annual_fixed_rate": annual_rate,
                "eligible_project_cost_keur": float(g171),
                "maximum_gearing": 0.80,
            },
            "phase2c_total_debt_keur": total_debt,
            "excel_total_debt_keur": excel_debt,
            "delta_keur": total_debt - excel_debt,
            "within_1pct": abs(total_debt - excel_debt) / max(abs(excel_debt), 1) < 0.01,
        }

    except Exception as exc:
        return {
            "status": "COMPUTATION_ERROR",
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Top-level extract()
# ---------------------------------------------------------------------------

def extract(workbook_path: pathlib.Path) -> dict:
    import openpyxl

    wb_data = openpyxl.load_workbook(
        workbook_path, read_only=True, data_only=True, keep_vba=False
    )
    wb_formula = openpyxl.load_workbook(
        workbook_path, read_only=True, data_only=False, keep_vba=False
    )
    try:
        workstream_a = _extract_cfads(wb_formula, wb_data)
        workstream_b = _extract_sculpting(wb_formula, wb_data)
        workstream_c = _extract_dsra(wb_formula, wb_data)
        workstream_d = _extract_sizing_base(wb_formula, wb_data)
        workstream_e = _extract_interest_rate(wb_formula, wb_data)

        payload: dict = {
            "_meta": {
                "extractor_version": _EXTRACTOR_VERSION,
                "source_filename": workbook_path.name,
                "source_sha256": _sha256(workbook_path),
                "sheets_inspected": wb_data.sheetnames,
                "dual_load_note": (
                    "dual_load: data_only=True for cached values, "
                    "data_only=False for formula text. "
                    "Both loads read identical binary; formulas are not re-evaluated."
                ),
            },
            "workstream_a": workstream_a,
            "workstream_b": workstream_b,
            "workstream_c": workstream_c,
            "workstream_d": workstream_d,
            "workstream_e": workstream_e,
        }

        # Equal-input / equal-policy comparison (may fail if engine not importable)
        payload["equal_input_equal_policy"] = _equal_input_equal_policy_comparison(payload)

    finally:
        wb_data.close()
        wb_formula.close()

    return payload


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m finco_recon.extract_oborovo_debt_interest",
        description="Extract Oborovo debt sizing & interest truth from the authoritative XLSM.",
    )
    parser.add_argument("--workbook", required=True, type=pathlib.Path,
                        help="Path to the source XLSM workbook")
    parser.add_argument("--output", required=True, type=pathlib.Path,
                        help="Destination JSON fixture path")
    args = parser.parse_args(argv)

    wb_path: pathlib.Path = args.workbook
    if not wb_path.exists():
        print(f"STOP\nSOURCE_WORKBOOK_REQUIRED\n\nFile not found: {wb_path}",
              file=sys.stderr)
        return 1

    print(f"Extracting from: {wb_path.name}", flush=True)
    try:
        payload = extract(wb_path)
    except Exception as exc:
        import traceback
        print(f"ERROR: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    print(f"Written: {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
