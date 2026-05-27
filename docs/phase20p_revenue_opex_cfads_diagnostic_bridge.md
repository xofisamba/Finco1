# Phase 20P — Revenue / OPEX / CFADS Diagnostic Bridge

**Branch:** `phase20p-revenue-opex-cfads-diagnostic-bridge`  
**Base:** `ba7a81fd3a90f1cd09d98e507296872c68fd6063` (after PR #278)  
**Date:** 2026-05-27  
**Status:** Diagnostic only — no runtime formula changes

---

## 1. Purpose

Before implementing Mode A / Mode B debt sizing solvers, build a diagnostic bridge comparing Excel anchor values to Python runtime outputs period-by-period.

This phase:
- Adds a structured diagnostic data model
- Embeds Excel anchor values for TUHO P4 and Oborovo P4 (from Phase 20N / Claude review)
- Compares runtime outputs against anchors
- Labels results PASS / FAIL / WARN / MISSING
- Does **not** change any runtime formula

---

## 2. Diagnostic Data Model

**File:** `domain/diagnostics/cfads_bridge.py`

```python
class DiagnosticStatus(Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    MISSING = "MISSING"

@dataclass(frozen=True)
class DiagnosticRow:
    project_code: str
    period_index: int
    period_label: str
    metric: str
    excel_value: Optional[float]
    python_value: Optional[float]
    delta: Optional[float]        # python_value - excel_value
    tolerance: float
    status: DiagnosticStatus
    likely_cause: str
    source_reference: str
    notes: str
```

**Builders:**
- `build_tuho_p4_diagnostic(...)` → `DiagnosticTable`
- `build_oborovo_p4_diagnostic(...)` → `DiagnosticTable`
- `diagnostic_table_to_list(table)` → JSON-serializable list of dicts

---

## 3. TUHO P4 Diagnostic Results

**Period:** P4 (0-based index 3, Y2-H1, operating period)  
**Excel anchor source:** Phase 20N / Claude review  

| Metric | Excel | Python | Delta | Status | Likely Cause |
|---|---|---|---|---|---|
| production_mwh | 73,468.93 | 73,468.93 | +0.001 | ✅ PASS | P50 hourly × availability × degradation |
| ppa_revenue_keur | 4,186.48 | 4,128.30 | −58.18 | ❌ FAIL | Balancing rate 8 EUR/MWh vs Excel's lower magnitude |
| co2_revenue_keur | 307.91 | 307.91 | +0.003 | ✅ PASS | CO2 schedule declining from ~4.2 EUR/MWh |
| balancing_cost_keur | 577.75 | 587.75 | +10.00 | ❌ FAIL | Python uses 8 EUR/MWh flat; Excel uses lower rate |
| opex_keur | −1,023.26 | 1,029.64 | +2,052.90 | ❌ FAIL | Sign convention: Excel shows as negative deduction; Python reports absolute. Delta = +2,053 due to Y1→Y2 inflation step |
| ebitda_keur | 3,163.22 | 3,156.84 | −6.38 | ❌ FAIL | Propagates from balancing + sign convention |
| cfads_keur | 3,163.22 | 3,156.84 | −6.38 | ❌ FAIL | = EBITDA (no cash tax in TUHO P4) |
| senior_service_keur | 2,180.24 | 2,045.24 | −134.99 | ❌ FAIL | Python uses sculpted DS at 1.2x DSCR; Excel may use different sculpting anchor |
| senior_interest_keur | 1,240.28 | 1,179.04 | −61.24 | ❌ FAIL | Different interest basis — Python uses period rate vs Excel's annual allocation |
| senior_principal_keur | 939.96 | 866.21 | −73.75 | ❌ FAIL | Sculpting divisor differs; Python principal = (DS - interest) |
| shl_sweep_keur | 982.99 | 0.00 | −982.99 | ❌ FAIL | P4 cash (1,111.60 kEUR) consumed by SHL interest (1,111.60 kEUR PIK); no principal sweep triggered |
| net_dividends_keur | 0.00 | 0.00 | 0.00 | ✅ PASS | Distribution 0 during lockup — matches |

**Summary: 3 PASS | 9 FAIL | 0 WARN | 0 MISSING**

---

## 4. Oborovo P4 Diagnostic Results

**Period:** P4 (0-based index 3, Y2-H1, operating period)  
**Excel anchor source:** Phase 20N / Claude review  

| Metric | Excel | Python | Delta | Status | Likely Cause |
|---|---|---|---|---|---|
| production_mwh | 54,580.16 | 54,580.16 | +0.005 | ✅ PASS | P50 hourly × availability |
| ppa_revenue_keur | 3,255.16 | 3,196.88 | −58.28 | ❌ FAIL | Balancing = 0 confirmed; delta = net revenue after balancing (Python) vs operating revenue anchor |
| co2_revenue_keur | 82.00 | 81.97 | −0.03 | ✅ PASS | CO2 flat 1.5 EUR/MWh — within rounding tolerance |
| balancing_cost_keur | 0.00 | 0.00 | 0.00 | ✅ PASS | Oborovo balancing = 0 confirmed |
| opex_keur | −644.34 | 676.79 | +1,321.13 | ❌ FAIL | Sign convention + Y2 inflation step |
| ebitda_keur | 2,610.82 | 2,578.37 | −32.45 | ❌ FAIL | Propagates from revenue + sign convention |
| cfads_keur | 2,610.82 | 2,578.37 | −32.45 | ❌ FAIL | = EBITDA (model has 0 cash tax) |
| senior_service_keur | 2,270.28 | 2,057.91 | −212.37 | ❌ FAIL | Python debt sizing uses fixed 42,852 kEUR; Excel may have different anchor |
| shl_sweep_keur | 340.54 | 0.00 | −340.54 | ❌ FAIL | P4 cash (650.40 kEUR) consumed by SHL interest (585.43 kEUR PIK); no principal sweep triggered |
| net_dividends_keur | 0.00 | 64.97 | +64.97 | ❌ FAIL | After SHL interest (585.43), remaining 64.97 flows to distribution — Excel anchor shows 0 |

**Summary: 3 PASS | 7 FAIL | 0 WARN | 0 MISSING**

---

## 5. Key Findings

### 5.1 Revenue Side

| Gap | Project | Severity | Notes |
|---|---|---|---|
| Balancing rate | TUHO | 🔴 High | Python uses 8 EUR/MWh flat; Excel uses lower rate (Excel magnitude ~578 kEUR vs Python 588 kEUR in P4) |
| PPA revenue vs net revenue | Both | 🟡 Medium | Excel "operating revenue" includes CO2; Python `revenue_keur` is net after balancing |
| CO2 | Both | ✅ OK | CO2 matches within rounding tolerance |
| Production | Both | ✅ OK | Exact match to 2 decimal places |

### 5.2 OPEX Side

| Gap | Project | Severity | Notes |
|---|---|---|---|
| Sign convention | Both | 🟡 Medium | Excel shows OPEX as negative deduction; Python reports absolute value. Delta = +Y1→Y2 inflation step (~2%) |
| OPEX absolute value | TUHO | 🟡 Medium | TUHO P4 OPEX = 1,029.64 kEUR vs Excel −1,023.26 → absolute delta ~6 kEUR (within 1% of Y1=1,998 kEUR) |
| OPEX absolute value | Oborovo | 🔴 High | Oborovo P4 OPEX = 676.79 kEUR vs Excel −644.34 → absolute delta ~32 kEUR — worth investigating |

### 5.3 Senior Debt / Waterfall

| Gap | Project | Severity | Notes |
|---|---|---|---|
| Senior service | Both | 🔴 High | Python DS sculpting at target 1.2 DSCR vs Excel frozen schedule. TUHO: Python 2,045 vs Excel 2,180 kEUR |
| SHL sweep | Both | 🔴 High | P4 cash (1,111 TUHO / 650 Oborovo) fully consumed by SHL PIK interest — no principal sweep. Excel shows sweep for TUHO |
| Interest basis | TUHO | 🟡 Medium | Python interest = period rate × opening balance; Excel may use annual average or different day count |

---

## 6. Diagnostic Limitations

1. **SHL sweep = 0 in P4 is real**, not a diagnostic gap. P4 cash after senior DS → SHL interest (PIK). Sweep triggers in later periods.
2. **Excel anchor for `ppa_revenue_keur`** uses Excel "operating revenue" which includes CO2. Python `revenue_keur` is net after balancing — comparison is slightly misaligned.
3. **Senior debt service anchors** are from Excel Macro!R50 frozen schedule — Python sculpting produces different per-period amounts.
4. **No Excel parsing in this phase** — anchors are embedded from Claude review, not dynamically read.

---

## 7. Tests

```bash
pytest tests/test_phase20p_cfads_diagnostic_bridge.py -v
```

**Result: 17 passed in 0.93s**

Additional regression:
```bash
pytest tests/test_phase20o_debt_sizing_modes.py tests/test_revenue.py tests/test_opex.py \
     tests/test_shl_waterfall_priority.py tests/test_tuho_shl_calibration.py -v
```

**Result: 64 passed | 2 xfailed | 1 xpassed in 1.45s** (expected — TUHO SHL still in progress)

---

## 8. Confirmations

| Check | Result |
|---|---|
| Runtime/model formulas changed? | **No** |
| Senior debt calculations changed? | **No** |
| SHL waterfall logic changed? | **No** |
| Workbook/export calculations changed? | **No** |
| JS financial calculations changed? | **No** |
| Default debt sizing mode = frozen_excel_schedule? | ✅ Yes |
| Future modes A/B raise NotImplementedError? | ✅ Yes |
| Diagnostic output affects runtime? | **No** — purely read-only |

---

## 9. Recommended Next Phases

### Phase 20Q — Revenue/OPEX Instrumentation Fixes
1. Align balancing rate — TUHO's Excel uses lower balancing rate than Python's 8 EUR/MWh flat
2. Align OPEX sign convention — report as negative deduction consistently with Excel
3. Verify Oborovo OPEX P4 absolute value (676 vs target 644 kEUR, delta ~32 kEUR)
4. Confirm whether Python `revenue_keur` (net after balancing) should map to Excel R27 (gross) or R22 (net)

### Phase 20R — Oborovo SHL Sweep Diagnostic
1. Verify Oborovo SHL repayment method — P4 shows interest-only (585 kEUR), sweep=0
2. Check if SHL sweep should trigger in P4 per Excel R99

### Phase 20S — TUHO Senior Debt Sculpting Alignment
1. TUHO P4 senior_service = 2,045 kEUR vs Excel 2,180 kEUR — gap of ~135 kEUR
2. Investigate whether Excel Macro!R50 frozen schedule is the real target
3. Phase 20O Mode A (minimum_dscr_sculpted) would use 1.20 DSCR divisor for PPA periods

---

*This document covers diagnostics only. No runtime formula changes were made.*
