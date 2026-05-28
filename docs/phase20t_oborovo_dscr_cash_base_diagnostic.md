# Phase 20T — Oborovo DSCR / Cash Base Diagnostic

**Branch:** `phase20t-oborovo-dscr-cash-base-diagnostic`  
**Base SHA:** `7abcd894fdfaf08785fe6f03300f593de8758d80`  
**Head SHA:** *(current branch head)*  
**Status:** Diagnostic only — no runtime changes

---

## 1. Executive Summary

After Phase 20S (partial_pay_sweep SHL method), the remaining Oborovo deltas are:

| Metric | Excel | Python | Delta | Cause |
|--------|-------|--------|-------|-------|
| OPEX | 644.34 kEUR | 676.79 kEUR | +32.45 kEUR | Upstream |
| EBITDA | 2,610.82 kEUR | 2,578.37 kEUR | −32.45 kEUR | Driven by OPEX |
| Senior Service | 2,270.28 kEUR | 2,057.91 kEUR | −212.37 kEUR | Upstream |
| Cash After Senior | 340.54 kEUR | 520.46 kEUR | +179.92 kEUR | Driven by senior DS gap |
| SHL Sweep (default) | 340.54 kEUR | 0.00 kEUR | — | SHL scope |
| SHL Sweep (opt-in) | 340.54 kEUR | 66.59 kEUR | −273.95 kEUR | SHL scope |
| Distribution (default) | 0.00 kEUR | 64.97 kEUR | +64.97 kEUR | SHL scope |

**Root causes:**
- **Upstream of SHL:** OPEX gap (+32.45 kEUR) and Senior Service gap (−212.37 kEUR)
- **Inside SHL:** Distribution leakage fixed by partial_pay_sweep opt-in; sweep magnitude gap persists

---

## 2. Oborovo P4 Diagnostic Table

| Metric | Excel | Python | Delta | Status | Upstream? |
|--------|-------|--------|-------|--------|-----------|
| production_mwh | 54,580.16 | 54,580.16 | 0.00 | ✅ PASS | Yes |
| operating_revenue_keur | 3,255.16 | 3,255.16 | 0.00 | ✅ PASS | Yes |
| opex_keur | 644.34 | 676.79 | +32.45 | ❌ FAIL | Yes |
| ebitda_keur | 2,610.82 | 2,578.37 | −32.45 | ❌ FAIL | Yes |
| cfads_keur | 2,610.82 | 2,578.37 | −32.45 | ❌ FAIL | Yes |
| senior_service_keur | 2,270.28 | 2,057.91 | −212.37 | ❌ FAIL | Yes |
| senior_interest_keur | — | 1,137.03 | — | MISSING | Yes |
| senior_principal_keur | — | 920.87 | — | MISSING | Yes |
| dscr | 1.147 (avg) | 1.2529 (P4) | +0.106 | ❌ FAIL | Yes |
| cash_after_senior_keur | 340.54 | 520.46 | +179.92 | ❌ FAIL | Yes |
| shl_sweep_keur (default) | 340.54 | 0.00 | — | ❌ FAIL | No |
| shl_sweep_keur (opt-in) | 340.54 | 66.59 | −273.95 | ❌ FAIL | No |
| distribution_keur (default) | 0.00 | 64.97 | +64.97 | ❌ FAIL | No |
| distribution_keur (opt-in) | 0.00 | 0.00 | 0.00 | ✅ PASS | No |
| cash_for_shl_keur | 340.54 | 520.46 | +179.92 | ❌ FAIL | No |

---

## 3. OPEX Line-Level Delta

**P4 OPEX Gap:** Python 676.79 vs Excel 644.34 = +32.45 kEUR (Python too high)

Python P4 OPEX = 676.79 kEUR absolute value.

Known Python OPEX breakdown (from Phase 20N):
- B.01 Technical Management: Python 280 vs Excel 198 (+82)
- B.02 Infrastructure Maintenance: Python 667 vs Excel 244 (+423) ← largest single gap
- B.12 Environmental & Social: Python 200 vs Excel 32 (+168)
- B.04 Clean Material: Python 5 vs Excel 40 (−35)
- B.08 Power Expenses: Python 94 vs Excel 177 (−83)

**Root cause hypothesis (per Phase 20N):** B.01, B.02, B.12 aggregate lines include sub-stavke that are also summed separately, causing double-counting. This inflates the Y1 OPEX base which then propagates to P4 via inflation escalation.

**Not a period-fraction or day-count issue** — the P4 values are already period-proportioned.

---

## 4. Senior Debt / DSCR Delta

**P4 Senior Service:** Python 2,057.91 vs Excel 2,270.28 = −212.37 kEUR (Python too low)

This means Python senior interest + principal is 212.37 kEUR less than Excel per period.

**Contributing factors:**
1. **Frozen schedule is input-constrained:** Python avg DSCR = 1.15 (exactly matches the target, because the frozen schedule was calibrated to produce avg DSCR = 1.15)
2. **Individual period differences:** P4 DSCR = 1.2529 (Python) vs implied Excel P4 DSCR = 2,610.82 / 2,270.28 = 1.150. Python has higher P4 DSCR, meaning relatively lower senior service relative to CFADS.
3. **Senior opening balance:** Python P4 opening = 39,328 kEUR. Excel opening balance unknown — needs verification.
4. **Interest rate basis:** Python uses period rate derived from annual rate. Excel may use a different day-count or period fraction.

**DSCR paradox:** Python avg DSCR = 1.15 matches Excel avg DSCR = 1.147 (close), but individual period DSCRs differ significantly. This is because the frozen schedule is sculpted to produce the correct average, but the period-by-period allocation differs from Excel.

**Key finding:** The senior debt frozen schedule alignment (interest rate basis, opening balance, period fractions) is the primary upstream cause of the SHL sweep magnitude gap.

---

## 5. DSRA Routing / Distribution Leakage

**Default:** Python distributes 64.97 kEUR in P4 while Excel distributes 0.

**Root cause:** Default SHL method does not block distributions when SHL balance > 0.

**Partial_pay_sweep opt-in fixes this** — distributions = 0 while SHL is alive.

This is an SHL-scope issue (inside waterfall), not an upstream cash base issue.

---

## 6. CO2 Flat-vs-Curve Conclusion

| | Status |
|---|---|
| Excel CO2 | **UNRESOLVED** |
| Python CO2 | **FLAT** at 1.5 EUR/MWh |

**Evidence:**
- Python CO2 rate: constant 1.50 EUR/MWh across all Oborovo operating periods
- Phase 20S report claimed "Excel has actual declining curve" — this is **unverified**
- Phase 20P anchor shows `co2_revenue_keur: 82.0` for P4, which matches flat 1.5 EUR/MWh × 54,580 MWh / 1000 = 81.87 kEUR ≈ 82 kEUR
- No Excel source reference confirms a declining CO2 curve for Oborovo

**Resolution required:** Verify against actual Oborovo Excel CO2 schedule (CO2 sheet, rows by period).

**If Excel is flat:** Python CO2 is correct.
**If Excel declines:** Python needs the CO2 price curve wired in.

---

## 7. Upstream vs SHL Scope

### Upstream of SHL (must fix before SHL calibration is meaningful):
1. **OPEX** — +32.45 kEUR gap in P4; double-counting in B.01/B.02/B.12 aggregates
2. **Senior debt service** — −212.37 kEUR gap in P4; frozen schedule alignment needed
3. **EBITDA/CFADS** — driven by OPEX gap

### Inside SHL waterfall:
1. **SHL sweep magnitude** — even with partial_pay_sweep, sweep = 66.59 vs Excel 340.54; this is downstream of the upstream cash base differences
2. **Distribution leakage** — fixed by partial_pay_sweep opt-in (no leakage when SHL alive)

---

## 8. Recommended Implementation Order

### Phase 20U-A: OPEX Fix
Fix the B.01/B.02/B.12 aggregation double-counting to reduce OPEX by ~32 kEUR in P4.

### Phase 20U-B: Senior Debt Frozen Schedule Alignment
Investigate and align the senior debt frozen schedule:
- Verify Excel opening balance for Oborovo P4 (Excel sheet, senior debt row)
- Verify interest rate basis (annual rate vs period rate, day-count)
- Verify period fractions for P4 (Excel uses actual/365 or 182/365?)

This will align senior service → cash_after_senior → SHL sweep routing.

### Phase 20U-C: CO2 Verification
Resolve CO2 flat vs curve by checking Excel source. Wire curve if confirmed.

---

## 9. Guardrail Confirmations

- No senior debt sizing changes ✅
- No senior debt interest basis changes ✅
- No OPEX formula changes ✅
- No revenue formula changes ✅
- No CO2 formula changes ✅
- No SHL default method changes ✅
- partial_pay_sweep remains opt-in ✅
- No workbook/export changes ✅
- No JS financial calculations ✅
- Backend remains source of truth ✅
- G20 BLOCKED ✅
- R99/R102 NOT APPROVED ✅
- No lender-ready/audit-certified/SaaS-ready claims ✅

---

## 10. Files Changed

| File | Change |
|------|--------|
| `domain/diagnostics/oborovo_cash_base.py` | New — Oborovo cash base diagnostic helpers |
| `tests/test_phase20t_oborovo_cash_base_diagnostic.py` | New — 11 diagnostic tests |
| `docs/phase20t_oborovo_dscr_cash_base_diagnostic.md` | New — this document |

**No runtime/model files changed.**

---

## 11. Tests Run

| Suite | Result |
|-------|--------|
| `test_phase20t_oborovo_cash_base_diagnostic.py` (11 tests) | ✅ 11 passed |
| `test_phase20s_shl_partial_pay_sweep.py` (16 tests) | ✅ 16 passed |
| `test_phase20r_shl_waterfall_diagnostic.py` (13 tests) | ✅ 13 passed |
| `test_phase20q + test_phase20p` (36 tests) | ✅ 36 passed |
| `test_revenue.py + test_opex.py` (31 tests) | ✅ 31 passed |
| `test_shl_waterfall_priority + test_tuho_shl_calibration` (14 tests) | ✅ 11 passed, 2 xfail, 1 xpass |
| `import main_web` | ✅ OK |

---

## 12. Recommended Next Phase

**Phase 20U-A** — Oborovo OPEX fix (B.01/B.02/B.12 aggregation), followed by **Phase 20U-B** — Senior debt frozen schedule alignment. Only after both upstream fixes should SHL sweep magnitude be recalibrated.
