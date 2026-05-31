# Phase 31B — CFADS Bridge Anchor Sign Fix

**Branch:** `phase31b-cfads-bridge-anchor-sign-fix`
**Base SHA:** `c84778518f8c9c6e18b6045dc41ea7e5e6e960b8` (after PR #341 Phase 31)
**Date:** 2026-05-31
**Status:** 1-line diagnostic data-quality fix — no runtime formula changes

---

## Scope

Fix the Oborovo CFADS bridge diagnostic anchor sign typo identified in Phase 31.

---

## Exact Anchor Correction

**File:** `domain/diagnostics/cfads_bridge.py` line 147

```python
# BEFORE:
"opex_keur": -644.34,

# AFTER:
"opex_keur":  644.34,    # positive — half-year P4 value; sign corrected from Phase 31B
```

---

## Why This Is Diagnostic-Only

`OBOROVO_P4_ANCHORS["opex_keur"]` is a **diagnostic anchor value** used only in the CFADS bridge diagnostic table (`build_oborovo_p4_diagnostic()`). It is not used in any runtime financial calculation. The anchor compares Python runtime output against an expected Excel reference value.

The `-644.34` was a **sign/data-entry error** — likely a typographic dash accidentally interpreted as a minus sign. OpEx is a cost and cannot be negative. The correct half-year P4 anchor is `+644.34` kEUR (half of full-year Y1 OpEx ≈ 1,338 kEUR).

---

## Phase 31 False-Alarm Finding — Unchanged

Phase 31 confirmed:
- **Oborovo Y1 OpEx runtime = 1,338.56 kEUR** ✅
- **Excel target = 1,338 kEUR** ✅
- **No runtime bug found** ✅
- **No B.01/B.02 double-count** ✅
- **Oborovo OpEx gap was a false alarm** ✅

This fix does not change any of those findings. It only corrects the diagnostic anchor sign.

---

## No Runtime Formula Changes

- ❌ No change to `domain/opex/projections.py`
- ❌ No change to `app/waterfall_core.py`
- ❌ No change to `app/project_factories.py`
- ❌ No change to revenue/CAPEX/tax formulas
- ❌ No change to senior debt sizing logic
- ❌ No change to SHL/distribution logic
- ✅ Only `domain/diagnostics/cfads_bridge.py` anchor value changed

---

## No Fixture CSV Changes

No fixture CSV files were modified in this phase.

---

## Guardrails

- ✅ G20 BLOCKED (field unchanged)
- ✅ R99/R102 NOT APPROVED (field unchanged)
- ✅ partial_pay_sweep not promoted
- ✅ flat/min DSCR sculpting not promoted
- ✅ Backend remains source of truth
- ✅ No lender/bank/audit/SaaS/certification claims

---

## Recommended Next Phase

**Phase 31C** — Oborovo Equity IRR / SHL Sweep Timing Investigation

Separate from OpEx (which is validated and correct):
- Oborovo equity IRR = 6.24% vs expected ~9.88% (separate from OpEx)
- PPA revenue P4 delta: -58.28 kEUR
- SHL sweep P4 delta: -340.54 kEUR

These are independent issues unrelated to the OpEx false alarm resolved in Phase 31.

---

## Confirmation

| Item | Status |
|------|--------|
| Anchor corrected | ✅ `-644.34` → `+644.34` |
| Diagnostic-only | ✅ No runtime formula changes |
| Phase 31 finding intact | ✅ OpEx false alarm confirmed |
| No fixture CSVs changed | ✅ |
| No model files changed | ✅ Only diagnostic anchor file |
| PR #299 state | ✅ Still draft, not merged |