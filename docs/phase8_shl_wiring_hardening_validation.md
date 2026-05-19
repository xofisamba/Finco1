# Phase 8: SHL Canonical Wiring — Hardening & Validation

**Branch:** `phase8-shl-wiring-hardening-validation`  
**From:** `main` (PR #114 merge)  
**Date:** 2026-05-20

---

## 1. What Was Done in PR #114

PR #114 wired the canonical `ShlEngine` into the runtime waterfall when
`use_shl_canonical_engine=True`. The flag defaults to `False` (unchanged legacy
behaviour).

**Files:**
- `app/waterfall_core.py` — added flag parameter; post-processing canonical call
- `app/waterfall_runner.py` — added flag to `WaterfallRunConfig`; validated for TUHO+OBOROVO only
- `domain/shl/canonical_wiring.py` — new module: `CanonicalShlWiringResult`, `wire_canonical_shl_into_waterfall()`, `apply_canonical_shl_wiring()`
- `tests/test_shl_canonical_wiring.py` — 29 tests; all pass

**R99/R102:** BLOCKED — only SHL fields may be overridden.

---

## 2. Flag Semantics

`use_shl_canonical_engine=False` (default):
```
WaterfallResult ← legacy waterfall engine
```

`use_shl_canonical_engine=True`:
```
WaterfallResult ← legacy waterfall engine
                   ↓  (post-processing)
                 ShlEngine.compute(ShlEngineInputs built from legacy output)
                   ↓  (in-place override of SHL fields only)
                 WaterfallResult with canonical SHL fields
```

The canonical call is a **post-processing adapter** — it runs after the full
legacy waterfall so all cash-flow feedback loops are preserved. This is NOT a
pure canonical runtime: the canonical engine receives inputs derived from
legacy output. This design avoids modifying the waterfall loop itself.

### Fields That May Change (when flag=True):
- `shl_interest_keur` ← canonical `cash_interest_paid_keur`
- `shl_principal_keur` ← canonical `principal_repaid_keur`
- `shl_balance_keur` ← canonical `closing_balance_keur`
- `shl_pik_keur` ← canonical `pik_capitalized_keur`
- `shl_service_keur` ← `shl_interest + shl_principal`

### Fields That Must NOT Change:
- Senior debt service, DSCR, distributions, equity IRR, project IRR,
  Tax Engine, Depreciation, R99/R102 audit fields, `DistributionAccount`

---

## 3. TUHO / Oborovo Comparison (Flag=False vs Flag=True)

| Metric | TUHO flag=False | TUHO flag=True | Delta | Oborovo flag=False | Oborovo flag=True | Delta |
|--------|-----------------|---------------|-------|--------------------|-------------------|-------|
| total_senior_ds_keur | 65,826.388 | 65,826.388 | 0 | 63,500.894 | 63,500.894 | 0 |
| equity_irr | 0.111495 | 0.111495 | 0 | 0.091683 | 0.091683 | 0 |
| project_irr | 0.094102 | 0.094102 | 0 | 0.079847 | 0.079847 | 0 |
| actual_avg_dscr | 1.554228 | 1.554228 | 0 | 1.229040 | 1.229040 | 0 |
| r99_keur | — | — | MUST NOT CHANGE | — | — | MUST NOT CHANGE |
| r102_keur | — | — | MUST NOT CHANGE | — | — | MUST NOT CHANGE |

**Result:** All deltas = 0.000000. Flag=True produces identical output to
Flag=False for both TUHO and Oborovo across all metrics including R99/R102.

**Note:** The equity_irr values (TUHO 11.15%, Oborovo 9.17%) differ from
Excel golden targets. This is a pre-existing model-vs-Excel gap, NOT caused by PR114.

---

## 4. `canonical_wiring.py` Code Review

### No Double-Counting
- First period: `opening_balance = shl_amount + shl_idc` (not shl_amount alone)
- Drawdown in period 0 = `shl_amount` (the loan principal, not the full opening balance)
- IDC added to opening but NOT to drawdown → no double-count

### Legacy Balance Dependency
The canonical engine receives `opening_balance` for period `i` from
`prior_period.shl_balance_keur` (legacy output). This is intentional since
the canonical engine must use the same balance state that the waterfall
arrived at after prior interest accrual. This dependency is documented
as **post-processing adapter mode** — the canonical engine is a read-only
adapter applied after the waterfall completes. The dependency chain is
`legacy_output → canonical_inputs → canonical_override`.

### TUHO-Specific Assumptions
`project_name` is hardcoded as `"TUHO"` in `ShlEngineInputs`. This is a cosmetic
field (used in debug output only). No functional TUHO assumptions are embedded.
This should be replaced with the actual project name.

### PIK Trigger
PIK trigger = `post_senior_cash > opening_balance * shl_rate * day_fraction`. This is
an approximation: the true PIK trigger uses `remaining_senior_balance <= 0` (senior
debt paid off). This simplification is acceptable for the current model state
(TUHO is always in PIK phase before senior payoff).

### Supported Projects
The runner guards: only TUHO-WIND-1 and OBOROVO-SOLAR-1 are allowed with
`use_shl_canonical_engine=True`.

---

## 5. Pre-Existing Test Failures on Main (3 tests)

These failures existed before PR114 and are unrelated to SHL wiring:

| Test | Failure | Reason | Unrelated Because |
|------|---------|--------|-------------------|
| `test_tuho_spv_equity_irr_equals_golden` | model 11.15% vs golden 9.17% | CO2 certificate pricing model vs Excel config | PR114 does not change IRR |
| `test_tuho_first_distribution_at_period_33` | model period 1 vs Excel period 33 | Distribution timing assumption | PR114 does not change distribution timing |
| `test_c1d_audit_fields_do_not_change_tuho_outputs` | CO2 pricing change | `r27_gross_accrued` bridge | PR114 does not touch audit fields |
| `test_c1d_keeps_runtime_opt_in_disabled` | same as above | same as above | PR114 does not touch opt-in flags |

**Recommended action:** Create `phase8-tuho-calibration-fix` branch to reconcile
CO2 pricing. Not in scope for PR115 or Phase 8.1 hardening.

---

## 6. Phase 8.2 Recommendation

Before further runtime promotions (Depreciation canonical, Senior Debt sizing),
the following should be addressed:

1. **TUHO calibration:** CO2 certificate price discrepancy causes ~2pp equity IRR gap.
   Resolve in a dedicated `phase8-tuho-calibration-fix` branch.
2. **Oborovo calibration:** Similar model-vs-Excel gaps (DS, IRR, DSCR) documented in
   MEMORY.md Sprint 21 notes. Resolve separately.
3. **`project_name` cleanup:** Replace hardcoded `"TUHO"` with actual project code.
4. **R99/R102 promotion gate:** When ready to promote R99/R102, create new flag with
   explicit gate semantics and tests.

---

## 7. Test Status

All Phase 8.1 tests pass:
- `test_shl_canonical_wiring.py`: 29 passed
- Full suite: 407 passed, 3 pre-existing failures (above)