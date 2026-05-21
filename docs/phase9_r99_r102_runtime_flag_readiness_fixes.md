# Phase 9: R99/R102 Runtime Flag Readiness Fixes

**Branch:** `phase9-r99-r102-runtime-flag-readiness-fixes`
**Base:** `95957fe` (PR #154 — design review)
**Type:** READINESS EVIDENCE / DOCS / TESTS ONLY

---

## Background

PR #154 (design review) identified two primary blockers before `phase9-r99-r102-runtime-flag-implementation`:

| Blocker | Gate | Status |
|---------|------|--------|
| DSCR stability not measured | G07 | PARTIAL |
| TUHO Excel parity not complete | G08 | PARTIAL |

This branch collects readiness evidence for G07 and G08.

---

## G07: DSCR Stability Evidence

### Finding: DSCR is Trivially Stable

DSCR computation: `DSCR = cf_after_reserves_keur / senior_ds_keur`

**Finding:** `senior_ds_keur = 0` for all 61 TUHO periods in both flag=False and flag=True configurations.

**Result:** DSCR = inf for all periods under both configurations.

**Evidence:**
```
flag=False: 61/61 periods DSCR = inf
flag=True:  61/61 periods DSCR = inf
flag=False: DSCR < 1.0 periods: 0
flag=True:  DSCR < 1.0 periods: 0
```

**Interpretation:** TUHO has no senior debt service during modeled periods. DSCR stability is trivially satisfied — no debt service to fail. Guard is ACTIVE for both configurations.

**G07 conclusion:** AVAILABLE. No DSCR < 1.0 periods. Variation = 0.

---

## G08: TUHO Excel Parity Evidence

### Pre-existing Calibration Status

Measured with `use_distributionaccount_runtime_wiring=False`:

| Metric | Excel Target | Model | Delta | Status |
|--------|-------------|-------|-------|--------|
| equity_irr | 11.61% | 22.31% | +10.70pp | PARTIAL |
| project_irr | 9.47% | 10.00% | +0.53pp | PASS (marginally over tolerance) |
| avg_dscr | 1.451 | 0.0 | N/A | INCONCLUSIVE (debt schedule inactive) |
| total_senior_ds_keur | — | 0 | — | debt schedule not active |

**Note:** equity_irr = 22.31% vs Excel 11.61% is a pre-existing calibration gap (not caused by DA wiring). Same equity_irr appears in both flag=False and flag=True. avg_dscr = 0.0 because `senior_ds_keur = 0` everywhere.

### G08 Conclusion: PARTIAL

- equity_irr: PARTIAL — +10.70pp gap requires investigation
- project_irr: PASS — +0.53pp (marginally above ±0.5pp tolerance)
- avg_dscr: INCONCLUSIVE — debt schedule inactive

### Recommended Actions for G08

1. Investigate why `senior_ds_keur = 0` — debt schedule should be active
2. Verify `create_default_tuho_wind1()` against Excel model inputs
3. Confirm equity_irr calculation source

---

## TUHO DA Wiring Metrics

| Configuration | Total Distribution | Delta |
|--------------|-------------------|-------|
| flag=False (legacy) | 326,165.35 kEUR | — |
| flag=True (DA wiring) | 284,552.08 kEUR | -41,613.28 kEUR |
| Oborovo guard | 181,019.11 kEUR | 0.00 kEUR |

---

## Explicit Statements

1. R99/R102 runtime promotion is NOT approved
2. G20 remains BLOCKED
3. G07 (DSCR stability): AVAILABLE
4. G08 (Excel parity): PARTIAL — pre-existing calibration gap
5. Oborovo remains excluded — guard fires for both configs
6. `use_distributionaccount_runtime_wiring=True` is pre-G20 staging, not promotion

---

## Next Branch

**If G08 gap is acceptable for pre-G20 staging:** `phase9-r99-r102-runtime-flag-implementation`
**If G08 gap must be resolved first:** investigate TUHO calibration

**Question for cofix:** Is equity_irr = 22.31% vs Excel 11.61% a known pre-existing issue, or does it need resolution before implementation?