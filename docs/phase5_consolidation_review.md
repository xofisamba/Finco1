# Phase 5 Consolidation Review

**Purpose:** Pre-external-audit consolidation and inventory of all Phase 5 work.
**Scope:** Documentation and verification only. No code changes.
**Last updated:** 2026-05-10

---

## Main State

**Current main SHA:** `0a63ee7`
**Last merge:** PR #23 — `portfolio-enforcement-simulation` (2026-05-10)

**rc1 confirmed:** present in repo history (`d0f9b56`). No Phase 5 work modified rc1.

---

## Phase 5 Inventory

### Phase 5A — Cash Ledger Foundation
- **PR:** #15 → `portfolio-distribution-constraints-foundation`  
  SHA: `7cecbf5` (merged)
- **Key modules:**
  - `domain/portfolio/cash_ledger/movements.py` — `CashMovement`, `CashMovementType`
  - `domain/portfolio/cash_ledger/adapters.py` — ledger adapters
  - `domain/portfolio/cash_ledger/orchestrator.py` — `build_cash_ledger_from_results()`
  - `domain/portfolio/distribution_constraints/inputs.py` — `DistributionBlockReason`, `DistributionConstraintConfig`
  - `domain/portfolio/distribution_constraints/result.py` — `DistributionConstraintPeriod`, `DistributionConstraintResult`
  - `domain/portfolio/distribution_constraints/runner.py` — `evaluate_distribution_constraints()`
- **Status:** Audit-only helper. Not wired into waterfall.
- **Wired to outputs:** No. Pure helper; rc1 unchanged.
- **Known limitations:** No enforcement. No constraint application.
- **Non-scope:** Tax engine, HoldCo IRR, Sponsor IRR, sponsor waterfall, monthly model.

---

### Phase 5B — Optional Cash Ledger Integration
- **PR:** #16 → `portfolio-distribution-constraints-integration`  
  SHA: `0c1aa41` (merged)
- **Key modules:**
  - `domain/portfolio/distribution_constraints/integration.py`
    - `cash_available_by_period_from_entity_ledger()`
    - `requested_distributions_from_entity_ledger()`
    - `evaluate_constraints_from_entity_ledger()`
    - `evaluate_constraints_from_portfolio_ledger()`
- **Status:** Audit-only. Reads from `EntityCashLedger` / `PortfolioCashLedger`.
- **Wired to outputs:** No. Integration helper for future Phase 5D overlays.
- **Known limitations:** No enforcement. No actual constraint application.
- **Non-scope:** Same as Phase 5A.

---

### Phase 5D.1 — SPV Retained Cash Overlay
- **PR:** #17 → `portfolio-spv-retained-cash-overlay`  
  SHA: `1ec46e1` (merged)
- **Key modules:**
  - `domain/portfolio/distribution_constraints/overlay.py`
    - `SPVRetainedCashPeriod`
    - `SPVRetainedCashOverlay`
    - `build_spv_retained_cash_overlay()`
    - `build_spv_retained_cash_overlays_from_portfolio_ledger()`
- **Status:** Audit-only. Produces read-only overlay data from SPV constraint results.
- **Wired to outputs:** No. Overlay is additive; does not mutate source data.
- **Layer:** `SPVOutput.retained_cash_overlay_keur` (added field, additive).
- **Non-scope:** Same as Phase 5A.

---

### Phase 5D.2 — HoldCo Retained Cash Overlay
- **PR:** #18 → `portfolio-holdco-retained-cash-overlay`  
  SHA: `fed3747` (merged)
- **Key modules:**
  - `domain/portfolio/distribution_constraints/holdco_overlay.py`
    - `HoldCoRetainedCashOverlay`
    - `build_holdco_retained_cash_overlay()`
    - `holdco_requested_distribution_by_period()`
    - `holdco_available_distribution_by_period()`
- **Status:** Audit-only. Mirrors SPV overlay pattern for HoldCo.
- **Wired to outputs:** No. Additive only.
- **Layer:** `HoldCoResult.retained_cash_overlay_keur` (added field, additive).
- **Ownership-adjusted:** HoldCo upstreaming respects ownership percentage.
- **Non-scope:** Same as Phase 5A.

---

### Phase 5D.5 — Distribution Enforcement Plan
- **PR:** #19 → `portfolio-distribution-enforcement-plan`  
  SHA: `eda4cd8` (merged)
- **Key modules:**
  - `docs/phase5d5_distribution_enforcement_plan.md`
- **Status:** Documentation/architecture plan only. No code implementation.
- **Phase 5G/H:** Enforcement mode schema and simulation (separate PRs, see below).
- **Non-scope:** Actual enforcement activation, SOFT_CAP/HARD_BLOCK implementation.

---

### Phase 5E — Excel Visibility Sheets
- **PR:** #20 → `portfolio-overlay-excel-export`  
  SHA: `9fe3578` (merged)
- **Key modules:**
  - `persistence/export/overlay_excel_export.py`
  - SPV and HoldCo overlay sheets written to Excel output
- **Status:** Additive export. Overlay sheets are additional tabs in Excel output.
- **Wired to outputs:** Yes — via `ExcelExporter` / `WaterfallExporter`.
- **Additive-only:** No existing sheets modified. New tabs added.
- **Non-scope:** Modifying existing Excel structure or waterfall logic.

---

### Phase 5F — UI Warning/Helpers
- **PR:** #21 → `portfolio-ui-warning-visibility`  
  SHA: `78d3139` (merged)
- **Key modules:**
  - `app/portfolio_ui_overlay.py` — overlay panel
  - `app/portfolio_ui.py` — warning display helpers
- **Status:** Additive UI layer. No enforcement.
- **Wired to outputs:** Via Streamlit app (`streamlit run app/portfolio_ui.py`).
- **Additive-only:** No underlying model behavior changed.
- **Non-scope:** Interactive constraint editing, enforcement activation.

---

### Phase 5G — Enforcement Mode Schema
- **PR:** #22 → `portfolio-enforcement-mode-schema`  
  SHA: `51befe6` (merged)
- **Key modules:**
  - `domain/portfolio/distribution_constraints/inputs.py`
    - `DistributionEnforcementMode` enum: `OFF`, `WARNING_ONLY`, `SOFT_CAP`, `HARD_BLOCK`
    - `DistributionConstraintConfig.enforcement_mode` field (default=OFF)
  - `domain/portfolio/distribution_constraints/runner.py`
    - `OFF` → `_pass_through()` (no reasons, no warnings)
    - `WARNING_ONLY` → compute reasons/warnings, allowed=requested
    - `SOFT_CAP/HARD_BLOCK` → same + "not active in Phase 5G" warning
- **Status:** Schema only. No mode reduces `allowed_distribution_keur`.
- **Wired to outputs:** No. Not connected to waterfall engine.
- **Key invariant:** `allowed_distribution_keur == requested_distribution_keur` for all modes in Phase 5G.
- **Non-scope:** Actual enforcement logic, SOFT_CAP/HARD_BLOCK activation.

---

### Phase 5H — Enforcement Simulation Report
- **PR:** #23 → `portfolio-enforcement-simulation`  
  SHA: `0a63ee7` (merged)
- **Key modules:**
  - `domain/portfolio/distribution_constraints/simulation.py`
    - `DistributionConstraintSimulationPeriod`
    - `DistributionConstraintSimulationResult`
    - `simulate_distribution_enforcement()`
    - `_safe_block_reason()`
- **Status:** Pure reporting. No mutation. No enforcement.
- **Features:**
  - `effective_allowed_by_entity_period` override for what-if simulation
  - `would_restrict_keur = requested - effective_allowed`
  - Safe block reason conversion (enum or string)
  - Safer totals validation (autofill only when all four totals are 0.0)
- **Wired to outputs:** No. Standalone helper.
- **Non-scope:** Actual enforcement activation.

---

## Output Safety Check

| Property | Status |
|---|---|
| No waterfall mutation | ✅ Confirmed — all Phase 5 modules are pure/helpers |
| No `distribution_keur` mutation | ✅ Confirmed — `allowed_distribution_keur == requested_distribution_keur` for all Phase 5G modes |
| No actual enforcement | ✅ Confirmed — all modes pass through |
| No distribution blocking | ✅ Confirmed — Phase 5G schema only |
| No tax engine | ✅ Not implemented |
| No HoldCo IRR | ✅ Not implemented |
| No Sponsor IRR | ✅ Not implemented |
| No sponsor waterfall | ✅ Not implemented |
| No monthly model | ✅ Not implemented |

### Module classification

**Pure helpers / reporting (no side effects):**
- `runner.evaluate_distribution_constraints()`
- `simulation.simulate_distribution_enforcement()`
- `integration.evaluate_constraints_from_entity_ledger()`
- `integration.evaluate_constraints_from_portfolio_ledger()`

**Future-ready but inactive:**
- `DistributionEnforcementMode.SOFT_CAP` — schema present, not enforced
- `DistributionEnforcementMode.HARD_BLOCK` — schema present, not enforced
- `DistributionConstraintConfig.enforcement_mode` — not wired to waterfall

**Additive (visible in outputs but read-only):**
- `SPVRetainedCashOverlay` — written to Excel overlay sheets (Phase 5E)
- `HoldCoRetainedCashOverlay` — written to Excel overlay sheets (Phase 5E)
- `DistributionConstraintSimulationResult` — reporting only

---

## Reconciliation / Invariants

| Invariant | Status |
|---|---|
| Overlays do not mutate source results | ✅ Immutable dataclasses; no setter mutation |
| Simulation does not mutate source results | ✅ Pure function; returns new objects |
| Excel export is additive only | ✅ New overlay sheets; no existing sheet modified |
| UI layer is additive only | ✅ Read-only overlay panel; no enforcement |
| Enforcement modes preserve `allowed = requested` | ✅ All Phase 5G modes: `allowed == requested` |
| Retained cash reconciles against effective allowed | ✅ `retained = cash_before - effective_allowed` |
| DSRF and SHL remain separate concepts | ✅ Confirmed — no shared state |
| SHL principal not treated as taxable income | ✅ Confirmed — `ShdResult` separate from tax |
| HoldCo upstreaming ownership-adjusted | ✅ `HoldCoRetainedCashOverlay` uses ownership % |

---

## Full Regression

```
1996 passed, 1 xfailed, 132 warnings
```

**No failures.** Suite passed in ~55s.

---

## Stale Branches (safe to delete)

All Phase 5 portfolio branches have been merged to main:

| Branch | Status |
|---|---|
| `portfolio-cash-ledger-integration` | ✅ Merged (PR #16) |
| `portfolio-distribution-constraints-foundation` | ✅ Merged (PR #15) |
| `portfolio-distribution-constraints-integration` | ✅ Merged (PR #16) |
| `portfolio-distribution-enforcement-plan` | ✅ Merged (PR #19) |
| `portfolio-enforcement-mode-schema` | ✅ Merged (PR #22) |
| `portfolio-enforcement-simulation` | ✅ Merged (PR #23) |
| `portfolio-holdco-retained-cash-overlay` | ✅ Merged (PR #18) |
| `portfolio-overlay-excel-export` | ✅ Merged (PR #20) |
| `portfolio-spv-retained-cash-overlay` | ✅ Merged (PR #17) |
| `portfolio-ui-warning-visibility` | ✅ Merged (PR #21) |

**Still unmerged** (pre-Phase 5 work, unrelated):
- `portfolio-retained-cash-semantics`
- `portfolio-retained-earnings-foundation`
- `portfolio-shl-collision-guard`
- `portfolio-shl-phase1`, `portfolio-shl-phase2`, `portfolio-shl-phase3`
- `portfolio-waterfall-mutability-docs`

---

## Optional Cleanup Recommendations (documentation only)

The following are noted for future consideration; **no cleanup implemented**:

1. **Stale portfolio branches** — 10 branches merged to main and not deleted. Safe to delete after review:
   ```
   git push origin --delete portfolio-cash-ledger-integration \
     portfolio-distribution-constraints-foundation \
     portfolio-distribution-constraints-integration \
     portfolio-distribution-enforcement-plan \
     portfolio-enforcement-mode-schema \
     portfolio-enforcement-simulation \
     portfolio-holdco-retained-cash-overlay \
     portfolio-overlay-excel-export \
     portfolio-spv-retained-cash-overlay \
     portfolio-ui-warning-visibility
   ```

2. **Naming consistency** — `holdco_overlay.py` uses snake_case function names while rest of package uses snake_case; already consistent. No action needed.

3. **TODO clusters** — none identified in Phase 5 modules.

4. **Dead exports** — `DistributionEnforcementMode` only used in `inputs.py` and `runner.py`; correctly exported in `__init__.py`. No dead exports.

---

## Claude Review Checklist

### 1. Architecture review targets

- [ ] `runner.evaluate_distribution_constraints()` — pass-through correctness for all 4 modes
- [ ] `simulation.simulate_distribution_enforcement()` — effective_allowed override logic
- [ ] `overlay.py` — immutable overlay construction; no source mutation
- [ ] `holdco_overlay.py` — ownership-adjusted upstreaming math
- [ ] `integration.py` — `evaluate_constraints_from_portfolio_ledger` multi-entity dispatch

### 2. Accounting/reconciliation review targets

- [ ] `retained_cash_keur == cash_before_distribution_keur - allowed_distribution_keur` holds in all periods
- [ ] Simulation `would_restrict_keur == requested - effective_allowed` math correct
- [ ] Block reason conversion works for both `DistributionBlockReason` enum and string types
- [ ] Totals validation: only autofill when all four totals are 0.0; otherwise validate each non-zero total

### 3. Enforcement semantics review

- [ ] `OFF` mode: `_pass_through()`, no reasons, no warnings
- [ ] `WARNING_ONLY`: compute reasons, `allowed == requested`
- [ ] `SOFT_CAP`: same as WARNING_ONLY + "not active" warning
- [ ] `HARD_BLOCK`: same as WARNING_ONLY + "not active" warning
- [ ] No mode reduces `allowed_distribution_keur` in Phase 5G

### 4. Overlay layering review

- [ ] `SPVRetainedCashOverlay` — additive, no existing field mutated
- [ ] `HoldCoRetainedCashOverlay` — additive, ownership-adjusted
- [ ] Both overlays: immutable dataclasses, constructed via factory functions
- [ ] Excel export: overlay sheets written before workbook close (Phase 5E fix applied)

### 5. Future tax integration readiness

- [ ] No tax engine implemented — Phase 5 preserves `TaxableIncomeCalculator` interface
- [ ] `HoldCoResult` structure intact — no tax fields pre-populated
- [ ] SHL PIK treated as separate from taxable income (confirmed)

### 6. Sponsor waterfall readiness gaps

- [ ] No `SponsorWaterfallCalculator` or equivalent
- [ ] No sponsor-level `distribution_keur` semantics
- [ ] No sponsor IRR computation
- [ ] HoldCo upstreaming: ownership-adjusted amount only (no sponsor waterfall routing)

### 7. Known intentional non-scope items

The following are explicitly **not implemented** and should be flagged if found in future reviews:
- Tax engine (`TaxableIncomeCalculator` / `CorporateTaxCalculator`)
- HoldCo IRR computation
- Sponsor IRR computation
- Sponsor waterfall (`SponsorWaterfallCalculator`)
- Monthly model (`MonthlyModel`)
- Actual enforcement (SOFT_CAP/HARD_BLOCK activation)
- Waterfall engine mutation (Phase 5 preserves `rc1` behavior)
- `distribution_keur` semantics changes

---

*This document is a pre-audit consolidation checkpoint. No code changes were made.*
