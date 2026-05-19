# Phase 7 — Runtime Stack Freeze

> **Status:** READY TO MERGE  
> **Branch:** `phase7-runtime-stack-freeze`  
> **PRs merged:** #97–#110 (Phase 7 complete)  
> **R99/R102: BLOCKED** — unchanged

---

## 1. Executive Summary

Phase 7 canonical runtime stack is now frozen as a stable, default-off foundation. This document formally catalogs what exists, what is canonical vs runtime-wired vs audit-only, what flags exist and their defaults, what is blocked, and what must not be promoted without explicit design approval.

**Key freeze decisions:**
- All canonical engines (SHL, SeniorDebtSizing, Depreciation) are **default-off**
- No canonical engine is wired as runtime source of truth
- All audit paths documented
- R99/R102 gates remain BLOCKED
- DistributionAccount owns R98/R99/R102 gate logic
- SponsorEngine owns R119 final cashflow
- No further promotion without explicit design PR

---

## 2. Canonical Modules Inventory

### 2.1 SHL (Subordinated Hybrid Loan)

| Component | File | Status |
|-----------|------|--------|
| SHL Engine (canonical) | `domain/shl/runtime_adapter.py` | **audit_only** — not wired to runtime |
| SHL FCF Waterfall | `domain/shl/fcf_waterfall.py` | **audit_only** — requires `use_shl_canonical_engine=True` |
| SHL Legacy Engine | `domain/shl/engine.py` | **runtime** — active by default |
| SHL Result | `domain/shl/result.py` | **audit** — canonical result types |

**Runtime wiring:** `use_shl_canonical_engine: bool = False`  
- When `False` (default): legacy SHL path active, canonical is audit-only
- When `True`: canonical `ShlEngine.compute()` result exposed as audit

**SHL canonical result is NOT distribution source.** `cash_for_distribution_keur` from canonical `ShlEngine` is audit output only.

### 2.2 Senior Debt

| Component | File | Status |
|-----------|------|--------|
| Senior Debt Sizing Engine | `domain/senior_debt_sizing/engine.py` | **audit_only** — not wired to waterfall |
| Senior Rate Schedule Engine | `domain/senior_rate_schedule.py` | **runtime** — active by default |
| Senior Sculpting Basis Engine | `domain/senior_sculpting/` | **runtime** — active by default |

**Runtime wiring:** `use_senior_debt_sizing: bool = False` (in `SeniorDebtSizingConfig`)  
- `SeniorDebtSizingEngine` is pure domain / sizing policy
- Not wired to `app/waterfall_core.py` runtime waterfall
- Produces sizing diagnostics only

### 2.3 Depreciation

| Component | File | Status |
|-----------|------|--------|
| DepreciationEngine (canonical) | `domain/depreciation/engine.py` | **audit_only** — not wired to TaxEngine |
| DepreciationSchedule (legacy) | `app/depreciation_engine.py` | **runtime** — active by default |
| Tax Bridge Adapter | `domain/depreciation/tax_bridge.py` | **audit_only** — bridge is validation-only |

**Runtime wiring:** `use_canonical_tax_depreciation_bridge: bool = False`  
- When `False` (default): legacy `build_depreciation_schedule()` path active
- When `True`: `DepreciationEngine.compute()` tax depreciation exposed as audit

**Canonical depreciation is NOT wired to TaxEngine.** `tax_depreciation_by_period_keur` from bridge is audit output only.

### 2.4 Tax

| Component | File | Status |
|-----------|------|--------|
| TaxEngine | `domain/waterfall/tax_engine.py` | **runtime** — active by default |
| Tax Bridge (financial statements) | `domain/financial_statements/tax_bridge.py` | **audit_only** — assembles waterfall audit fields |
| R67 Cash Tax Diagnostic | `domain/waterfall/r67_diagnostic.py` | **audit_only** — R67 suppressed for TUHO years 0-12 |

**No canonical TaxEngine.** Existing `compute_period_tax()` is the runtime source.

### 2.5 Distribution / R99

| Component | File | Status |
|-----------|------|--------|
| DistributionAccount | `domain/distribution_account/` | **runtime (gate)** — owns R98/R99/R102 gate logic |
| R98 Distribution Account Balance | `app/waterfall_core.py` | **audit_only** |
| R99 FCF for Distribution Gate | `app/waterfall_core.py` | **audit_only** — BLOCKED |
| R100 Carryforward | `app/waterfall_core.py` | **audit_only** |
| R102 FCF for SHL | `app/waterfall_core.py` | **audit_only** — BLOCKED |

**R99/R102: BLOCKED.** Gate logic in `DistributionAccount.compute_tuho_r99_input_period()` is audit-only. Gate not promoted to runtime.

### 2.6 Sponsor / R119

| Component | File | Status |
|-----------|------|--------|
| SponsorEngine | `app/sponsor.py` | **runtime** — receives distributions from WaterfallEngine |
| R119 Final Dividend | `app/waterfall_core.py` | **audit_only** |

**R119 owned by SponsorEngine.** DistributionAccount does not compute R119 directly.

---

## 3. Runtime Flags Inventory

| Flag | Location | Default | Current Behavior |
|------|----------|---------|-----------------|
| `use_shl_canonical_engine` | `domain/inputs.py:96` | `False` | Legacy SHL active; canonical is audit-only |
| `use_shl_fcf_waterfall_engine` | `domain/inputs.py:95` | `False` | Legacy FCF waterfall; canonical audit-only |
| `use_senior_debt_sizing` | `SeniorDebtSizingConfig` | `False` | Not wired; pure domain sizing |
| `use_senior_rate_schedule_engine` | `domain/inputs.py:93` | `False` | Senior rate schedule inactive |
| `use_senior_sculpting_basis_engine` | `domain/inputs.py:94` | `False` | Senior sculpting basis inactive |
| `use_canonical_tax_depreciation_bridge` | `domain/inputs.py:97` | `False` | Legacy depreciation; bridge is audit-only |
| `use_tax_bridge_engine` | `domain/inputs.py:98` | `False` | Tax bridge inactive |
| `use_book_depreciation_for_pnl` | `domain/inputs.py:100` | `False` | Book depreciation bridge inactive |
| `use_shl_gross_accrued_for_pnl` | `domain/inputs.py:99` | `False` | SHL gross P&L bridge inactive |
| `use_tuho_r99_input_engine` | `app/waterfall_core.py:49` | `False` | TUHO R99 input engine C1a — leaves runtime unchanged |
| `use_construction_schedule_engine` | `domain/inputs.py:88` | `False` | Construction schedule engine inactive |
| `shl_fcf_waterfall_cash_schedule_keur` | `domain/inputs.py:57` | `()` | Empty tuple — not wired |

**All flags default to `False`.** No canonical engine is runtime-wired by default.

---

## 4. Default-Off Behavior Confirmation

**Confirmed: All canonical engines are default-off.**

```
┌─────────────────────────────────────────────────────────────┐
│  Legacy path (default)           Canonical path (flag=True) │
├─────────────────────────────────────────────────────────────┤
│  SHL: legacy compute_shl_period   SHL: ShlEngine (audit)   │
│  Senior: existing waterfall      Senior: SeniorDebtSizing  │
│  Depreciation: build_dep_schedule Depreciation: Engine      │
│  Tax: compute_period_tax         Tax: bridge (audit)        │
└─────────────────────────────────────────────────────────────┘
```

**No silent runtime behavior change.** When any flag is `False` (default), legacy path is active.

---

## 5. Audit-Only Outputs

The following are **audit-only** — they do not feed runtime cashflows:

| Output | File | Audit Field |
|--------|------|-------------|
| Canonical SHL result | `domain/shl/runtime_adapter.py` | `ShlEngine.compute()` result |
| SHL FCF waterfall | `domain/shl/fcf_waterfall.py` | `compute_shl_fcf_waterfall_period()` |
| Senior debt sizing | `domain/senior_debt_sizing/engine.py` | `SeniorDebtSizingResult` |
| Tax depreciation bridge | `domain/depreciation/tax_bridge.py` | `DepreciationTaxBridgeResult` |
| R98/R99/R100/R102 | `app/waterfall_core.py` | `period.r98/r99/r100/r102_*_keur` |
| R67 cash tax diagnostic | `domain/waterfall/r67_diagnostic.py` | `r67_*_diagnostic_keur` |
| Book depreciation bridge | `domain/financial_statements/depreciation_bridge.py` | `book_depreciation_keur` |
| SHL gross interest P&L | `domain/shl/` | `shl_gross_interest_*` |

---

## 6. Runtime Source-of-Truth Matrix

| Module | Runtime Source? | Audit Only? | Notes |
|--------|----------------|-------------|-------|
| WaterfallEngine | ✅ | ❌ | CFADS → senior → SHL → distribution |
| TaxEngine | ✅ | ❌ | `compute_period_tax()` is runtime source |
| SHL (legacy) | ✅ | ❌ | `compute_shl_period()` active by default |
| SHL (canonical) | ❌ | ✅ | Not wired to runtime |
| SeniorDebtSizingEngine | ❌ | ✅ | Not wired to runtime |
| DepreciationEngine (canonical) | ❌ | ✅ | Not wired to TaxEngine |
| DepreciationSchedule (legacy) | ✅ | ❌ | Active by default |
| DistributionAccount | ✅ | ❌ | Runtime gate owner |
| SponsorEngine | ✅ | ❌ | Receives distributions |

---

## 7. Blocked Modules / Blocked Rows

### 7.1 R99/R102 Gate — BLOCKED

**Status:** `DistributionAccount.compute_tuho_r99_input_period()` is BLOCKED.

**Why blocked:**
1. Gate logic not decoupled from audit-only path
2. No `use_r99_runtime_gate` flag
3. SHL not re-wired to receive R102
4. DSCR gate ownership not formally separated from SeniorDebtSizing
5. SponsorEngine not confirmed separate from R99 gate

**Required before promotion:** See `docs/phase7_r99_r102_source_ownership_design.md` Section 10 (6 gates).

### 7.2 R67 Cash Tax — BLOCKED

**Status:** `use_tuho_r99_input_engine` suppresses R67 for TUHO years 0-12. R67 diagnostic is audit-only.

**Why blocked:** TUHO-specific suppression, not generalized for other projects.

### 7.3 Canonical SHL → Distribution Wiring — BLOCKED

**Status:** `ShlEngine.compute()` output `cash_for_distribution_keur` is not wired to `DistributionAccount`.

**Why blocked:** Requires `use_shl_canonical_engine=True` wiring in `app/waterfall_core.py`, which is out of scope for Phase 7.

### 7.4 Deferred Tax — FORBIDDEN

**Status:** Not implemented. No deferred tax accounting in TaxEngine.

**Why forbidden:** Requires balance sheet modeling beyond current scope.

### 7.5 HoldCo Tax — FORBIDDEN

**Status:** Not implemented. HoldCo level taxes require separate modeling.

**Why forbidden:** Project-specific, not modeled in current architecture.

---

## 8. R99/R102 Status

**R99/R102: BLOCKED** — confirmed frozen.

| Row | Owner | Status |
|-----|-------|--------|
| R98 | DistributionAccount | audit_only |
| R99 | DistributionAccount | **BLOCKED** — gate not promoted |
| R100 | DistributionAccount | audit_only |
| R102 | DistributionAccount | **BLOCKED** — SHL not wired |
| R119 | SponsorEngine | audit_only |

**No R99/R102 promotion in Phase 7.** All gate logic remains in audit-only path.

**Source:** `docs/phase7_r99_r102_source_ownership_design.md`

---

## 9. Test Inventory

### 9.1 Phase 7 Test Summary

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_shl_runtime_flag.py` | 14 | SHL canonical flag default-off |
| `test_shl_engine.py` | 5 | SHL legacy engine |
| `test_shl_fcf_waterfall_runtime_flag.py` | 11 | SHL FCF waterfall flag |
| `test_shl_engine_tuho_fixture.py` | — | TUHO fixture validation |
| `test_senior_debt_sizing_policy.py` | 10 | Senior debt sizing policy |
| `test_depreciation_engine.py` | 17 | Depreciation canonical engine |
| `test_depreciation_tax_bridge.py` | 10 | Tax bridge adapter |
| `test_model_stack_validation_pack.py` | 86 | Model stack integration |
| **Total Phase 7** | **~143** | **All passing** |

### 9.2 All Tests Pass

```
============================= 110 passed in X.XXs ==============================
```

No regressions introduced in Phase 7.

---

## 10. Known Limitations

### 10.1 SHL Canonical Not Wired
- `ShlEngine.compute()` produces correct `cash_for_distribution_keur`
- Not wired to `DistributionAccount` in `app/waterfall_core.py`
- Canonical result available as audit output only

### 10.2 Depreciation Canonical Not Wired
- `DepreciationEngine.compute()` produces correct `tax_depreciation_by_period_keur`
- Not wired to `TaxEngine` in `domain/waterfall/tax_engine.py`
- Bridge result available as audit output only

### 10.3 Senior Debt Sizing Not Wired
- `SeniorDebtSizingEngine.compute()` produces correct sizing diagnostics
- Not wired to `app/waterfall_core.py`
- Result available as audit/diagnostic only

### 10.4 Aggregate Periods Returns TOTAL Row
- `DepreciationLedgerResult.aggregate_periods()` returns per-period aggregate with `asset_class='TOTAL'`
- Per-asset-class breakdown available in `ledger_result.periods`
- For single-asset-class projects (TUHO, Oborovo), TOTAL row is sufficient

### 10.5 R99 Gate Not Promoted
- Gate logic in `DistributionAccount.compute_tuho_r99_input_period()` is audit-only
- DSCR lockup check not formally separated from SeniorDebtSizing
- No `use_r99_runtime_gate` flag

### 10.6 TUHO R67 Suppression
- R67 diagnostic suppressed for TUHO years 0-12 via `use_tuho_r99_input_engine`
- TUHO-specific, not generalized for other projects

---

## 11. Promotion Readiness Checklist

Before any canonical engine can be promoted to runtime source:

- [ ] **SHL canonical:** `use_shl_canonical_engine=True` wiring in `app/waterfall_core.py`
- [ ] **SHL → Distribution wiring:** `cash_for_distribution_keur` → `DistributionAccount`
- [ ] **Depreciation canonical:** `use_canonical_tax_depreciation_bridge=True` wiring in tax path
- [ ] **Senior debt sizing:** `use_senior_debt_sizing=True` wiring in waterfall
- [ ] **R99 gate:** `use_r99_runtime_gate=True` flag + gate decoupling + DSCR separation
- [ ] **TUHO fixture regression:** All canonical promotions must pass TUHO fixture
- [ ] **Oborovo fixture regression:** All canonical promotions must pass Oborovo fixture
- [ ] **No sponsor IRR regression:** Sponsor IRR unchanged with flag=True
- [ ] **No DSCR regression:** Average/min DSCR unchanged with flag=True
- [ ] **No distribution regression:** Total distributions unchanged with flag=True

**Current status:** All items unchecked. No promotion approved.

---

## 12. Recommended Next Phase / Next Branch

### Recommended: `phase7-closeout-review`

**Purpose:** Formal Phase 7 closeout review document.

**Deliverables:**
- Consolidate all Phase 7 design docs into `docs/phase7_closeout_master.md`
- Confirm all Phase 7 PRs (#97–#110) are merged
- Update MEMORY.md with Phase 7 canonical stack status
- Prepare Phase 8 planning input (canonical engine → runtime promotion roadmap)

**Out of scope for closeout:**
- No new canonical engines
- No runtime promotion
- No R99/R102 unblocking
- No new flags

### Alternative: Phase 8 Planning Only

If user wants to pause canonical engine work:
- Document Phase 8 goals: which canonical engine to promote first
- Get explicit user approval before runtime promotion work
- Maintain Phase 7 freeze until Phase 8 approval

### Forbidden Next Steps (unless explicitly approved)
- ❌ Promoting SHL canonical to runtime without design PR
- ❌ Promoting Depreciation canonical to runtime without design PR
- ❌ Unblocking R99/R102 without 6-gate completion
- ❌ Rewriting TaxEngine or DistributionAccount
- ❌ Any app/waterfall_core.py broad refactor

---

## 13. Phase 7 PR Summary

| PR | Branch | Type | Key Output |
|---:|--------|------|-----------|
| #97 | senior-debt-dscr-source-map | DOCS | Macro!R50 hardcoded |
| #98 | shl-cash-sweep-source-map | REPORT | 100% cash sweep |
| #99 | shl-canonical-module-design | DESIGN | ShlEngine |
| #100 | senior-debt-canonical-module-design | DESIGN | SeniorDebtSizingEngine |
| #101 | shl-source-map-metric-reconciliation | FIX | Gross=53,351 |
| #102 | depreciation-canonical-module-design | DESIGN | DepreciationEngine |
| #103 | shl-engine-implementation | ENGINE | `domain/shl/` |
| #104 | senior-debt-sizing-flag | ENGINE | `domain/senior_debt_sizing/` |
| #105 | depreciation-runtime-integration | ENGINE | `domain/depreciation/engine.py` |
| #106 | model-stack-validation-pack | VALIDATION | 86 tests |
| #107/108 | shl-runtime-flag-wiring | WIRING | `use_shl_canonical_engine` |
| #109 | r99-r102-source-ownership-design | DESIGN | R98/R99/R102 ownership matrix |
| #110 | tax-runtime-bridge | BRIDGE | `domain/depreciation/tax_bridge.py` |

**Total: 14 PRs merged in Phase 7. All canonical engines are default-off.**

---

## 14. Files This Branch Adds

| File | Description |
|------|-------------|
| `reports/phase7_runtime_stack_inventory.csv` | Full component inventory CSV |
| `docs/phase7_runtime_stack_freeze.md` | This document |

**No production code changes.** This is a documentation-only freeze branch.

---

*Document version: 1.0 — 2026-05-19*