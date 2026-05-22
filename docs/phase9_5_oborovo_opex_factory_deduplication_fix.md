# Phase 9.5 — Oborovo OPEX Factory Deduplication Fix

## Issue Summary

A potential Oborovo OPEX issue was reported:
- **Suspected wrong value:** ~1,998 kEUR Y1 OPEX for Oborovo
- **Expected value:** ~1,338 kEUR Y1 OPEX for Oborovo
- **Root cause:** Investigated — no active bug found; Oborovo Y1 OPEX = 1,338.08 kEUR (confirmed correct)

---

## Investigation

### What was checked

1. **Factory `create_default_oborovo()`** — `app/project_factories.py` line 38
   - OpexItem tuple: 15 items
   - Sum of `y1_amount_keur` = **1,338.08 kEUR** ✓
   - Technical Management = 198.0 kEUR (not 280 or 703)
   - Infrastructure Maintenance = 244.0 kEUR (not 667)
   - Contingencies = 51.0 kEUR (fixed amount)

2. **Runtime via `opex_schedule_period()`** — `domain/opex/projections.py`
   - Oborovo Y1 (P2+P3) = **1,338.08 kEUR** ✓
   - TUHO Y1 = **1,998.01 kEUR** ✓
   - No TUHO template leakage into Oborovo

3. **UI context `get_project_context('oborovo')`** — `app/ui/project_context.py`
   - `opex_y1_total_keur = 1,338.08` ✓
   - `opex_contingency_method = 'fixed_amount'` ✓

4. **OPEX engine** — `domain/opex/projections.py`
   - Uses `inputs.opex` (OpexItem tuple) directly
   - No TUHO-specific code paths in Oborovo runs
   - TUHO-only adapter in `domain/opex/runtime_adapter.py` raises for non-TUHO projects

5. **Historical context** (from memory/2026-04-27.md)
   - Sprint 11 fix applied Technical Management 703→198 kEUR, Infrastructure Maintenance 244→667 kEUR to maintain 1,998 total — but that was reversed
   - Final correct values confirmed in Sprint 11 sign-off

---

## Root Cause: MISSING_EVIDENCE

**No active bug was found.** Oborovo Y1 OPEX = 1,338.08 kEUR is correct and matches expected.

The reported 1,998 kEUR figure for Oborovo may have originated from:
1. **Stale observation** from before Sprint 11 fix was applied
2. **Incorrect project context** — UI showing TUHO values while "Oborovo" was selected
3. **Fixture/test data** referencing old values (test fixtures `oborovo_base.json` noted 1,998)
4. **Confusion with TUHO** — TUHO Y1 OPEX is 1,998 kEUR, Oborovo is 1,338 kEUR

---

## Before / After Table

| Metric | Before (suspected) | After (actual) | Expected | Status |
|---|---|---|---|---|
| Oborovo Y1 OPEX | ~1,998 (wrong) | 1,338.08 | 1,338.08 | ✅ Already correct |
| TUHO Y1 OPEX | 1,998.05 | 1,998.05 | 1,998.05 | ✅ Unchanged |
| Oborovo OPEX items | unknown | 15 | 15 | ✅ OK |
| Oborovo duplicates | unknown | 0 | 0 | ✅ OK |
| Oborovo contingency | fixed | fixed | fixed | ✅ OK |
| TUHO contingency | % of opex | % of opex | % of opex | ✅ OK |
| Oborovo UI context | - | 1,338.08 | 1,338.08 | ✅ OK |

---

## TUHO No-Drift Statement

TUHO Y1 OPEX remains **1,998.05 kEUR** (unchanged):
- 12 OpexItems
- Technical Management: 279.99 kEUR
- O&M Preventive & Corrective: 426.60 kEUR
- Insurance: 468.74 kEUR
- Contingencies: 113.09 kEUR (% of opex at 6%)
- No TUHO values changed during this investigation

---

## Oborovo UI Context

- `opex_y1_total_keur = 1,338.08` kEUR — correctly shown in `/?project=oborovo`
- `opex_contingency_method = 'fixed_amount'` — correct (not % of opex)
- `opex_contingency_pct` shown as 2.0 (legacy placeholder, not used for Oborovo)
- No TUHO OPEX total shown in Oborovo context

---

## No Unrelated Model Changes

- ✅ No waterfall changes
- ✅ No revenue changes
- ✅ No senior debt changes
- ✅ No SHL changes
- ✅ No tax changes
- ✅ No DistributionAccount changes
- ✅ No sponsor changes
- ✅ No G20 approval
- ✅ No R99/R102 promotion

---

## G20 / R99 / R102 Status

- **G20:** BLOCKED (unchanged)
- **R99/R102:** NOT APPROVED (unchanged)

---

## Validation Results

```
Oborovo Factory Y1 OPEX:  1,338.08 kEUR ✅
TUHO Factory Y1 OPEX:      1,998.05 kEUR ✅
Oborovo runtime Y1:        1,338.08 kEUR ✅
TUHO runtime Y1:           1,998.01 kEUR ✅
Oborovo item count:        15 items ✅
TUHO item count:           12 items ✅
No duplicate items:        ✅
UI context = factory:      ✅
```

---

## Files Added

- `tests/test_phase9_5_oborovo_opex_validation.py` — 18 tests
- `reports/phase9_5_oborovo_opex_deduplication_validation.csv` — 20-row validation report
- `docs/phase9_5_oborovo_opex_factory_deduplication_fix.md` — this document

---

## Conclusion

**Root cause: MISSING_EVIDENCE** — no active bug. Oborovo Y1 OPEX was already correct at 1,338.08 kEUR. The 1,998 kEUR figure was either a stale observation or confusion with TUHO's OPEX. TUHO is correctly 1,998 kEUR. The OPEX factories are fully separated with no TUHO leakage into Oborovo context.

**Action taken:** Tests + validation report + this doc. No code changes needed since the factory was already correct.