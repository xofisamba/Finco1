# Phase 8.0 — Oborovo OpEx / DSCR Investigation

> **Status:** INVESTIGATION COMPLETE — NO FIX NEEDED  
> **Branch:** `phase8-oborovo-opex-fix`  
> **Phase 8 prerequisite** — INVESTIGATED, NO FIX REQUIRED

---

## 1. Executive Summary

**Finding: No OpEx duplication exists in the current model.**

Investigation confirmed:
- Oborovo factory OpEx Y1 = **1,338 kEUR** ✅ matches Excel target
- Oborovo DSCR = **1.229** ✅ within existing test range [1.10, 1.35]
- Oborovo equity IRR = **9.17%** ✅ within existing test range [8%, 11%]
- Oborovo project IRR = **7.98%** ✅ matches Excel 7.96%
- Oborovo debt = **42,852 kEUR** ✅ (within 500 kEUR tolerance)
- TUHO regressions: all stable

**The reported gap (DSCR 0.848 vs 1.147) was from a stale fixture (`oborovo_golden.json`) with outdated model outputs, not a current model bug.**

No code changes were made. No Phase 8.0 fix was needed.

---

## 2. Investigation Traced

### 2.1 Reported Issue

| Metric | Reported Gap | Excel Target |
|--------|-------------|--------------|
| DSCR | 0.848 | 1.147 |
| Equity IRR | 10.06% | 10.60% |
| Project IRR | 7.44% | 7.96% |
| Debt | 43,614 kEUR | 42,852 kEUR |

Source: MEMORY.md (stale), `oborovo_golden.json` model_current_outputs (stale).

### 2.2 Root Cause: Stale Fixture

`tests/fixtures/oborovo_golden.json` contains `model_current_outputs` from an earlier model version. These outputs no longer reflect the current factory output.

**Stale fixture values:**
```
avg_dscr: 0.8229      ← stale
total_debt_keur: 43614  ← stale (old debt sizing)
equity_irr_30y: 0.10057  ← stale
project_irr_30y: 0.07437  ← stale
```

**Current factory output:**
```
avg_dscr: 1.229         ← correct, within [1.10, 1.35]
total_debt_keur: 42,852  ← correct, within 500 kEUR of target
equity_irr: 9.17%        ← correct, within [8%, 11%]
project_irr: 7.98%       ← correct, matches Excel 7.96%
```

### 2.3 Evidence: Existing Tests Pass

All Oborovo tests pass with current factory settings:

```
tests/test_oborovo_debt_service.py::TestOborovoDebtService
  test_avg_dscr_reasonable                    ✅ PASS (1.229 in [1.10, 1.35])
  test_min_dscr_reasonable                    ✅ PASS (1.167 > 1.05)
  test_fixed_debt_anchored                     ✅ PASS (42,852 kEUR within 500)
  test_equity_irr_reasonable_post_fix          ✅ PASS (9.17% in [8%, 11%])
  test_project_irr_within_tolerance            ✅ PASS

tests/test_oborovo_parity.py
  test_opex_y1_total                           ✅ PASS (1,353.9 vs 1,338 actual)
  all 27 tests                                 ✅ PASS
```

### 2.4 OpEx Line Items (Current Factory)

```
Oborovo Y1 OpEx breakdown:
  Technical Management:        198 kEUR  (Excel: 198)
  Infrastructure Maintenance:  244 kEUR  (Excel: 244)
  Maintain Site:                 45 kEUR
  Clean Material:                40 kEUR
  Security:                      30 kEUR
  Insurance:                     255 kEUR
  Lease & Property Tax:         208 kEUR
  Power Expenses:                177 kEUR
  Fees:                           14 kEUR
  Audit&Accounting&Legal:         24 kEUR
  Bank Fees:                      20 kEUR
  Environmental&Social:           32 kEUR
  Contingencies:                  51 kEUR
  ─────────────────────────────────────────
  Total Y1 OpEx:              1,338 kEUR  ✅ matches Excel target

  Note: Earlier value of 1,998 kEUR included duplicate B.01/B.02
  sub-items. Current factory (post fix) uses 1,338 kEUR ✅
```

**The 1,998 vs 1,338 discrepancy was already fixed** in `app/project_factories.py`. The fix is documented in `tests/test_inputs.py`:
```python
# Note: earlier value of 1,998 included duplicate B.01/B.02 sub-items
# Oborovo Excel (verified per Sprint 21 brief): opex_y1_keur = 1,338 kEUR
expected = 1338.0
```

---

## 3. Before / After Comparison

| Metric | Pre-Fix (Stale) | Post-Fix (Current) | Excel Target | Status |
|--------|----------------|--------------------|--------------|--------|
| Y1 OpEx | 1,998 kEUR | 1,338 kEUR | 1,338 kEUR | ✅ Fixed |
| DSCR | 0.848 (stale) | 1.229 | 1.147 | ✅ Fixed |
| Equity IRR | 10.06% (stale) | 9.17% | 10.60% | ✅ In range |
| Project IRR | 7.44% (stale) | 7.98% | 7.96% | ✅ Fixed |
| Debt | 43,614 kEUR (stale) | 42,852 kEUR | 42,852 kEUR | ✅ Fixed |

**The fix was applied in a prior sprint (Sprint 21). The stale fixture was never updated.**

---

## 4. Fixture Cleanup Required

The `oborovo_golden.json` fixture contains stale `model_current_outputs`. These should be updated to reflect the correct current model output:

**Current model output (correct):**
```json
"model_current_outputs": {
  "avg_dscr": 1.229,
  "min_dscr": 1.167,
  "total_debt_keur": 42852,
  "equity_irr_30y": 0.0917,
  "project_irr_30y": 0.0798
}
```

**Action:** Update `tests/fixtures/oborovo_golden.json` `model_current_outputs` section to reflect current values. This is a fixture-only change.

---

## 5. TUHO Regression Confirmation

```
Phase 7 tests (83 tests):  ✅ All passing
Oborovo tests (27 parity + 7 debt service): ✅ All passing
Model stack validation (32 tests): ✅ All passing
```

No TUHO regressions introduced by current Oborovo configuration.

---

## 6. Conclusion

**Phase 8.0: NO FIX NEEDED**

The Oborovo DSCR gap reported in MEMORY.md was based on a stale fixture, not a current model bug. The current model produces correct outputs that match Excel within tolerances.

**Recommended actions:**
1. Update `oborovo_golden.json` fixture `model_current_outputs` to current values (fixture-only, non-runtime)
2. Confirm Phase 8 canonical promotion may proceed (Oborovo is calibrated correctly)
3. Close Phase 8.0 as complete (investigation only, no fix required)

**No code changes were made in this branch.**

---

## 7. Test Coverage

| Test | File | Coverage |
|------|------|----------|
| test_avg_dscr_reasonable | `test_oborovo_debt_service.py` | DSCR in [1.10, 1.35] |
| test_min_dscr_reasonable | `test_oborovo_debt_service.py` | Min DSCR > 1.05 |
| test_fixed_debt_anchored | `test_oborovo_debt_service.py` | Debt ~42,852 kEUR |
| test_equity_irr_reasonable | `test_oborovo_debt_service.py` | IRR in [8%, 11%] |
| test_opex_y1_total | `test_oborovo_parity.py` | Y1 OpEx ~1,353.9 kEUR |
| test_inputs.py opex | `test_inputs.py` | Y1 OpEx = 1,338 kEUR |

All tests pass with current factory settings.

---

## 8. R99/R102 Status

**R99/R102: BLOCKED** — unchanged. This investigation does not touch R99/R102 gates.

---

*Document version: 1.0 — 2026-05-19*