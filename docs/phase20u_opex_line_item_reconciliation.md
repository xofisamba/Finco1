# Phase 20U-A — OPEX Line-Item Reconciliation Workbook

**Branch:** `phase20u-opex-line-item-reconciliation-workbook`
**Base:** `1b85406` (Phase 20T merge — Oborovo DSCR/Cash Base Diagnostic)
**Date:** 2026-05-28
**Status:** Diagnostic only — no runtime formula changes

---

## 1. Purpose

Create a diagnostic OPEX reconciliation workbook comparing Excel vs Python model output for TUHO Wind and Oborovo Solar.

The goal is to identify exactly which OPEX line items and sub-items create the period-by-period differences, particularly the Oborovo P4 delta identified in Phase 20T.

**This phase does NOT change any OPEX formulas.** It is purely diagnostic.

---

## 2. Method

### 2.1 Excel Extraction

**Critical limitation:** The workspace does NOT contain a raw Oborovo Excel workbook with per-period OpEx line-item values (B.01/B.02/B.12). Therefore:

- Excel line-item rows = **MISSING_SOURCE** (do not fabricate)
- Excel aggregate rows = **available** (from phase10 calibration anchors)
- Excel period-by-period values = **NOT available** (no source)

For TUHO, the TUHO Excel file was used to extract aggregate OPEX anchors.

### 2.2 Python Extraction

Python runtime OPEX extracted from:
- `domain/inputs.py :: OpexItem` (line-item data)
- `app/project_factories.py :: create_default_tuho_wind1()` and `create_default_oborovo()`
- `domain/opex/projections.py` (period schedule helpers)
- `app/ui_runner.py :: run_demo_project()` (full waterfall runtime)

Python-side provides:
- Full OpexItem list (15 items for Oborovo, 12 items for TUHO) with annual amounts by year
- Period-level OPEX = annual × day_fraction (from WaterfallResult.periods)

### 2.3 Period Mapping

Semiannual periods P1–P6 mapped to operating years:
- P1 = Y1_OP (operating year 1)
- P2 = Y2_OP
- P3 = Y3_OP
- P4 = Y4_OP
- P5 = Y5_OP
- P6 = Y6_OP

Construction periods (pre-COD) have 0 OPEX.

For Oborovo: COD = 2027-12-31, so P1–P6 are all operational.
For TUHO: COD = 2029-12-30, so P1–P4 may be partial construction.

---

## 3. Excel Extraction Assumptions

| Data | Status | Source |
|------|--------|--------|
| Oborovo aggregate OPEX by period | Available | phase10 calibration anchors |
| Oborovo B.01/B.02/B.12 line-item by period | **MISSING_SOURCE** | No raw Oborovo Excel in workspace |
| TUHO aggregate OPEX by period | Available | TUHO Excel data file |
| TUHO B-code line-item by period | **MISSING_SOURCE** | TUHO Excel has aggregate only |

The phase10 calibration workbook has aggregate OPEX anchors but not line-item detail.

---

## 4. Python Extraction Assumptions

| Data | Status | Source |
|------|--------|--------|
| Oborovo OpexItem list (15 items) | Available | `create_default_oborovo()` |
| Oborovo period-level OPEX | Available | Runtime via `run_demo_project()` |
| TUHO OpexItem list (12 items) | Available | `create_default_tuho_wind1()` |
| TUHO period-level OPEX | Available | Runtime via `run_demo_project()` |

Python-side line-item detail is complete and runtime-authoritative.

---

## 5. Oborovo P4 OPEX Delta — Confirmed

**Key finding from Phase 20T (confirmed):**

| Metric | Value | Source |
|--------|-------|--------|
| Excel aggregate P4 | 644.34 kEUR | oborovo_comparison.xlsx anchor |
| Current Python runtime P4 | 676.79 kEUR | Current model run (authoritative) |
| **Delta (Python − Excel)** | **+32.45 kEUR** | |
| Stale workbook P4 | 659.88 kEUR | comparison workbook (older run) |

⚠️ **The comparison workbook value (659.88 kEUR) is stale.** Current Python runtime (676.79) is authoritative.

---

## 6. TUHO Findings

TUHO OPEX calibration status (from Phase 21):
- Debt = 43,359 kEUR ✅ (within ±1%)
- Equity IRR = 11.61% ✅ (within ±1.0pp with CO2)
- Project IRR = 10.46% ⚠️ (within ±0.5pp)
- Avg DSCR = 1.682 ⚠️ (within ±0.05)

TUHO OPEX is substantially calibrated. The workbook will display TUHO line items for completeness.

---

## 7. Oborovo Findings

### 7.1 P4 Delta

Oborovo P4 OPEX delta = +32.45 kEUR (Python > Excel).

Root cause cannot be confirmed without raw Oborovo Excel OpEx sheet.

**Primary suspects:**
1. B.01 Technical Management — model uses aggregate value; Excel may split into sub-items
2. B.02 Infrastructure Maintenance — model may aggregate differently than Excel
3. B.12 Environmental & Social — step change handling may differ

### 7.2 Double-Count Issue

Phase 20N concluded that the historical double-count concern (model giving Y1=1,998 vs Excel=1,338) was resolved by using Y1 column values (pre-aggregated) rather than Budget column values (which sum sub-items).

However, the P4 delta suggests there may still be period-level aggregation differences between Excel and Python.

**Cannot confirm without line-item source data.**

---

## 8. B.01/B.02/B.12 Oborovo Finding

Based on Phase 20N:
- B.01 = 198 kEUR Y1
- B.02 = 244 kEUR Y1
- B.12 = 32 kEUR Y1 (step Y3 → 5.2 kEUR)

The model treats these as single line items. Excel may have sub-item detail beneath these codes.

**Cannot verify period-level aggregation without raw Excel OpEx sheet.**

---

## 9. Python OPEX Runtime vs Presentation

The `domain/opex/engine.py` is an **offline** annual-first engine. It does not wire results into runtime cash flows directly.

The runtime OPEX for waterfall comes from:
1. `domain/opex/projections.py` (annual OPEX schedule)
2. `app/ui_runner.py` (full WaterfallResult via `run_demo_project()`)

The OPEX displayed in UI pages (Streamlit pages) is:
- Presentation layer (from WaterfallResult)
- NOT the same as the `compute_annual_opex()` offline engine output

**OPEX grid is runtime-authoritative** (from WaterfallResult.periods), not presentation-only.

The `OpexItem` code field is not yet implemented (recommendation from Phase 20N).

---

## 10. Recommended Targeted Fixes

Cannot recommend specific formula changes without line-item source data.

**Required next step:** Import actual Oborovo Excel workbook with detailed OpEx sheet.

Once imported, the following will be possible:
1. Per-B-code period-level Python vs Excel delta
2. Identification of whether B.01/B.02/B.12 aggregate or split in Excel
3. Exact inflation/start-period differences per line item

---

## 11. Tests Run

```bash
pytest tests/test_phase20u_opex_line_item_reconciliation.py -v
pytest tests/test_opex.py -v
pytest tests/test_revenue.py -v
python -c "import main_web"
```

---

## 12. Guardrails

✅ **Did NOT change:**
- OPEX runtime formulas
- Revenue formulas
- Tax formulas
- Senior debt formulas
- SHL formulas
- Workbook export calculations
- JS financial calculations
- Default runtime behavior
- `partial_pay_sweep` promotion

✅ **Confirmed:**
- G20 BLOCKED (not approved)
- R99/R102 NOT APPROVED (governance blockers active)

---

## 13. Delta Table Flags

| Flag | Meaning |
|------|---------|
| PASS | abs(delta) ≤ 1 kEUR or ≤ 0.5% |
| WARN | small timing/rounding issue |
| FAIL | material mismatch > 5 kEUR |
| MISSING_SOURCE | Excel line-item not available (workspace lacks raw Excel) |
| MISSING_PYTHON | Python doesn't expose this row |
| NOT_COMPARABLE | Cannot compare line-item delta (no Excel source) |
| STALE_WORKBOOK | Workbook has older/stale run value |

---

## 14. Files Changed

Expected on this branch:
- `scripts/export_phase20u_opex_reconciliation_workbook.py` (new)
- `reports/phase20u_opex_line_item_reconciliation.xlsx` (generated)
- `docs/phase20u_opex_line_item_reconciliation.md` (new)
- `tests/test_phase20u_opex_line_item_reconciliation.py` (new)

No domain runtime files changed.

---

## 15. Conclusion

The Phase 20U-A workbook has been generated with clear limitation flags:

- **Excel line-item rows = MISSING_SOURCE** (no raw Oborovo OpEx sheet in workspace)
- **Python line-item rows = available** (runtime OpexItem detail)
- **Delta (line-item) = NOT_COMPARABLE** (no Excel source)
- **Delta (aggregate) = valid** (Python aggregate vs Excel aggregate)

**Oborovo P4 OPEX delta confirmed: +32.45 kEUR (Python 676.79 vs Excel 644.34).**

**Exact line-item cause cannot be proven until raw Oborovo OpEx sheet is imported.**

Recommended next action: Request/import the actual Oborovo Excel workbook with detailed OpEx sheet, then rerun Phase 20U-A as true line-by-line reconciliation.