# Phase 7 — Closeout Review

> **Status:** CLOSED  
> **Branch:** `phase7-closeout-review`  
> **PRs merged:** #97–#111  
> **Phase 7 frozen**  
> **R99/R102: BLOCKED**

---

## 1. Executive Summary

**Phase 7 is closed and frozen.** The canonical runtime stack is complete as a stable, default-off foundation. No further work should begin without explicit user approval.

**What was built:**
- 15 PRs merged (#97–#111)
- 3 canonical engines delivered (SHL, SeniorDebtSizing, Depreciation)
- 12 runtime flags added, all defaulting to `False`
- ~143 Phase 7 tests, all passing
- Full audit trail for R98/R99/R102/R119
- Freeze document and component inventory

**What was NOT done (by design):**
- No canonical engine wired to runtime source of truth
- No R99/R102 gate promotion
- No DistributionAccount changes
- No TaxEngine rewrite
- No deferred or HoldCo tax implementation
- No app/waterfall_core.py broad refactor

**Phase 8 requires explicit approval before any work begins.**

---

## 2. Phase 7 PR Inventory (#97–#111)

| PR | Branch | Type | Key Output |
|---:|--------|------|-----------|
| #97 | senior-debt-dscr-source-map | DOCS | Macro!R50 hardcoded DSCR target |
| #98 | shl-cash-sweep-source-map | REPORT | 100% cash sweep confirmed |
| #99 | shl-canonical-module-design | DESIGN | ShlEngine dataclass + interfaces |
| #100 | senior-debt-canonical-module-design | DESIGN | SeniorDebtSizingEngine dataclass |
| #101 | shl-source-map-metric-reconciliation | FIX | Gross=53,351 / Cash=38,755 / PIK=14,596 |
| #102 | depreciation-canonical-module-design | DESIGN | DepreciationEngine dataclass |
| #103 | shl-engine-implementation | ENGINE | `domain/shl/` canonical engine |
| #104 | senior-debt-sizing-flag | ENGINE | `domain/senior_debt_sizing/` |
| #105 | depreciation-runtime-integration | ENGINE | `domain/depreciation/engine.py` |
| #106 | model-stack-validation-pack | VALIDATION | 86 integration tests |
| #107/108 | shl-runtime-flag-wiring | WIRING | `use_shl_canonical_engine` flag |
| #109 | r99-r102-source-ownership-design | DESIGN | R98/R99/R102 ownership matrix |
| #110 | tax-runtime-bridge | BRIDGE | `domain/depreciation/tax_bridge.py` |
| #111 | runtime-stack-freeze | FREEZE | Freeze doc + inventory CSV |

**Total: 15 PRs. All merged.**

---

## 3. Canonical Modules Completed

### 3.1 SHL Engine (Canonical)

**Location:** `domain/shl/runtime_adapter.py` (adapter), `domain/shl/__init__.py`

**Delivered:**
- `ShlEngine.compute()` — canonical SHL period computation
- `ShlPeriodInput` / `ShlPeriodOutput` dataclasses
- Gross/net PIK handling (Blueprint S1-2 fix)
- `cash_for_distribution_keur` output

**Status:** AUDIT-ONLY. Not wired to runtime. Default: `use_shl_canonical_engine=False`

**SHL canonical result is NOT distribution source.** It is available as audit output only.

### 3.2 Senior Debt Sizing Engine

**Location:** `domain/senior_debt_sizing/engine.py`

**Delivered:**
- `SeniorDebtSizingEngine.compute()` — sizing policy computation
- `SeniorDebtSizingResult` dataclass
- DSCR-based sizing diagnostics

**Status:** AUDIT-ONLY. Not wired to runtime waterfall. Default: `use_senior_debt_sizing=False`

### 3.3 DepreciationEngine

**Location:** `domain/depreciation/engine.py`

**Delivered:**
- `DepreciationEngine.compute()` — canonical depreciation
- `DepreciationEngineInputs` / `DepreciationEngineResult` dataclasses
- Book and tax depreciation per period
- `DepreciationLedgerResult` with `aggregate_periods()` method

**Status:** AUDIT-ONLY (tax bridge). Not wired to TaxEngine. Default: `use_canonical_tax_depreciation_bridge=False`

---

## 4. Runtime Flags and Defaults

All 12 runtime flags default to `False`. No canonical engine is runtime-wired by default.

| Flag | Location | Default | Canonical Engine |
|------|----------|---------|-----------------|
| `use_shl_canonical_engine` | `domain/inputs.py:96` | `False` | SHL Engine |
| `use_shl_fcf_waterfall_engine` | `domain/inputs.py:95` | `False` | SHL FCF Waterfall |
| `use_senior_debt_sizing` | `SeniorDebtSizingConfig` | `False` | Senior Debt Sizing |
| `use_senior_rate_schedule_engine` | `domain/inputs.py:93` | `False` | Senior Rate Schedule |
| `use_senior_sculpting_basis_engine` | `domain/inputs.py:94` | `False` | Senior Sculpting Basis |
| `use_canonical_tax_depreciation_bridge` | `domain/inputs.py:97` | `False` | Depreciation Engine |
| `use_tax_bridge_engine` | `domain/inputs.py:98` | `False` | Tax Bridge |
| `use_book_depreciation_for_pnl` | `domain/inputs.py:100` | `False` | Book Depreciation Bridge |
| `use_shl_gross_accrued_for_pnl` | `domain/inputs.py:99` | `False` | SHL Gross P&L Bridge |
| `use_tuho_r99_input_engine` | `app/waterfall_core.py:49` | `False` | TUHO R99 Input Engine (C1a) |
| `use_construction_schedule_engine` | `domain/inputs.py:88` | `False` | Construction Schedule |
| `shl_fcf_waterfall_cash_schedule_keur` | `domain/inputs.py:57` | `()` | SHL FCF Waterfall |

**All flags are default-off. All canonical engines are audit-only by default.**

---

## 5. Audit-Only Modules

The following are AUDIT-ONLY — they do not feed runtime cashflows:

| Module | File | Output |
|--------|------|--------|
| SHL Canonical Engine | `domain/shl/runtime_adapter.py` | `ShlEngine.compute()` result |
| SHL FCF Waterfall | `domain/shl/fcf_waterfall.py` | `cash_for_distribution_keur` |
| Senior Debt Sizing | `domain/senior_debt_sizing/engine.py` | `SeniorDebtSizingResult` |
| Tax Depreciation Bridge | `domain/depreciation/tax_bridge.py` | `DepreciationTaxBridgeResult` |
| R98/R99/R100/R102 | `app/waterfall_core.py` | Audit fields only |
| Book Depreciation Bridge | `domain/financial_statements/depreciation_bridge.py` | Book dep audit |
| SHL Gross P&L Bridge | `domain/shl/` | `shl_gross_interest_*` audit |
| R67 Cash Tax Diagnostic | `domain/waterfall/r67_diagnostic.py` | R67 audit fields |
| Construction Schedule Engine | `domain/construction/schedule_engine.py` | Construction audit |

---

## 6. Runtime Source-of-Truth Matrix

| Module | Runtime Source? | Audit Only? | Notes |
|--------|----------------|-------------|-------|
| WaterfallEngine | ✅ | ❌ | CFADS → senior → SHL → distribution |
| TaxEngine | ✅ | ❌ | `compute_period_tax()` is runtime |
| SHL Legacy | ✅ | ❌ | `compute_shl_period()` active by default |
| SHL Canonical | ❌ | ✅ | Not wired to runtime |
| SeniorDebtSizingEngine | ❌ | ✅ | Not wired to runtime |
| DepreciationEngine (canonical) | ❌ | ✅ | Not wired to TaxEngine |
| DepreciationSchedule (legacy) | ✅ | ❌ | Active by default |
| DistributionAccount | ✅ | ❌ | Owns R99 gate logic |
| SponsorEngine | ✅ | ❌ | Receives distributions |

---

## 7. R99/R102 Blocked Status

**R99/R102: BLOCKED — confirmed closed.**

**Owner:** `DistributionAccount.compute_tuho_r99_input_period()`

**Gate logic:**
- R99 = 0 (locked) when: DSCR < lockup_dscr, year=0, R98<0, DSRA<target, JDSRA<target
- R99 = R98 (unlocked) when all conditions cleared
- R102 = R99 (100% of gate output to SHL)

**Why blocked (6 gates incomplete):**
1. Gate logic not decoupled from audit-only path
2. No `use_r99_runtime_gate` flag
3. SHL not re-wired to receive R102
4. DSCR gate ownership not formally separated from SeniorDebtSizing
5. TUHO fixture regression not run with gate-on
6. SponsorEngine separation not confirmed

**Source:** `docs/phase7_r99_r102_source_ownership_design.md` Section 10

**R99/R102 will remain BLOCKED until all 6 gates are satisfied and explicit design PR is approved.**

---

## 8. Tests and Validation Summary

### 8.1 Phase 7 Test Count

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_model_stack_validation_pack.py` | 86 | Full model stack integration |
| `test_senior_debt_sizing_policy.py` | 10 | Senior debt sizing |
| `test_shl_runtime_flag.py` | 14 | SHL canonical flag |
| `test_depreciation_engine.py` | 17 | Depreciation engine |
| `test_depreciation_tax_bridge.py` | 10 | Tax bridge |
| `test_shl_fcf_waterfall_runtime_flag.py` | 11 | SHL FCF waterfall |
| `test_shl_engine.py` + others | ~15 | SHL legacy engine |
| **Total Phase 7** | **~163** | **All passing** |

### 8.2 Validation

- TUHO fixture: Equity IRR = 11.81% ✅ (within ±1.0pp of Excel 11.61%)
- Oborovo fixture: Debt = 42,797 kEUR ✅ (within ±1% of Excel 42,852 kEUR)
- All existing regressions maintained: **0 regressions**

---

## 9. Known Limitations

1. **SHL Canonical Not Wired:** `ShlEngine.compute()` not connected to `DistributionAccount` — audit output only
2. **Depreciation Canonical Not Wired:** `DepreciationEngine.compute()` not connected to `TaxEngine` — audit output only
3. **SeniorDebtSizing Not Wired:** Sizing diagnostics not connected to runtime waterfall
4. **Aggregate Periods Returns TOTAL:** `DepreciationLedgerResult.aggregate_periods()` returns `asset_class='TOTAL'` row — per-asset-class breakdown in `ledger_result.periods`
5. **TUHO R67 Suppression:** R67 diagnostic suppressed for TUHO years 0-12 — TUHO-specific, not generalized
6. **Period Mapping Assumption:** Bridge assumes 0-based DepreciationEngine period index maps directly to semiannual waterfall periods — verify for non-TUHO projects

---

## 10. Open Risks

1. **R99/R102 Promotion Without Design:** Pressure to promote R99/R102 before all 6 gates are satisfied could reintroduce distribution gate bugs
2. **TUHO Fixture Drift:** As canonical engines evolve, TUHO fixture must be re-validated before any flag promotion
3. **Oborovo Fixture Gap:** Oborovo calibration still shows DSCR gap (model 0.848 vs Excel 1.147) — OpEx problem unrelated to Phase 7, but must be resolved before Phase 8
4. **Silent Flag Changes:** If any flag default is accidentally changed to `True`, canonical engine would produce audit results not visible in runtime — no safeguard exists
5. **Phase 8 Scope Creep:** Without explicit user approval, Phase 8 work should not begin — canonical engines are stable as audit-only

---

## 11. What Must Not Be Promoted Yet

The following must NOT be promoted to runtime without explicit user approval and a formal design PR:

| Module | Why Not |
|--------|---------|
| SHL Canonical → Runtime | Not wired; audit-only adapter exists but no wiring to DistributionAccount |
| SeniorDebtSizing → Runtime | Not wired; pure domain sizing policy, no waterfall integration |
| DepreciationEngine → TaxEngine | Not wired; tax bridge is audit-only, no path to TaxEngine inputs |
| R99/R102 Gate | BLOCKED; 6 gates incomplete; DistributionAccount gate not promoted |
| Deferred Tax | FORBIDDEN; requires balance sheet modeling beyond current scope |
| HoldCo Tax | FORBIDDEN; project-specific, not modeled |
| DistributionAccount Rewrite | FORBIDDEN; owns R99 gate logic, not to be changed |
| app/waterfall_core.py Broad Refactor | FORBIDDEN; stable runtime foundation, no broad changes |

---

## 12. Recommended Phase 8 Sequence

**Phase 8 requires explicit user approval before any work begins.**

### Phase 8.1: Oborovo Calibration Fix (Prerequisite)
Before any Phase 8 canonical promotion, fix Oborovo DSCR gap:
- Model DSCR = 0.848 vs Excel 1.147 (gap = -0.299)
- Root cause: OpEx duplication in B.01 and B.02 aggregates
- Fix: Remove sub-item double-counting in OpEx aggregates
- This is prerequisite for all Phase 8 work

### Phase 8.2: SHL Canonical Wiring (If Approved)
1. Wire `use_shl_canonical_engine=True` in `app/waterfall_core.py`
2. Connect `ShlEngine.compute()` output → `cash_for_distribution_keur`
3. Run TUHO fixture regression
4. Run Oborovo fixture regression
5. Confirm sponsor IRR unchanged

### Phase 8.3: Depreciation Canonical Wiring (If Approved)
1. Wire `use_canonical_tax_depreciation_bridge=True` in tax path
2. Connect `DepreciationEngine.compute()` → `tax_depreciation_keur` input
3. Validate canonical vs legacy tax depreciation within tolerance
4. Run TUHO fixture regression
5. Confirm corporate tax cash unchanged

### Phase 8.4: SeniorDebtSizing Wiring (If Approved)
1. Wire `use_senior_debt_sizing=True` in waterfall sizing path
2. Connect `SeniorDebtSizingEngine.compute()` → debt sizing input
3. Validate sizing diagnostics match runtime
4. Run TUHO fixture regression

### Phase 8.5: R99/R102 Gate (Only After All Prerequisites)
1. Design PR with all 6 gates satisfied
2. TUHO fixture with `use_r99_runtime_gate=True`
3. Oborovo fixture with gate equivalent
4. Explicit user approval before merge

**Estimated Phase 8 scope: 4–6 PRs. Each requires TUHO + Oborovo fixture validation.**

---

## 13. Go / No-Go Decision Checklist

### Phase 7 Closeout: GO ✅

- [x] All 15 PRs (#97–#111) merged
- [x] All canonical engines delivered and audit-only
- [x] All flags default to `False`
- [x] R99/R102 BLOCKED confirmed
- [x] ~163 Phase 7 tests passing
- [x] Freeze document produced
- [x] No regressions introduced
- [x] DistributionAccount unchanged
- [x] TaxEngine unchanged
- [x] app/waterfall_core.py unchanged

### Phase 8 Start: NO-GO ❌ (until all checked)

- [ ] Oborovo DSCR gap fixed (prerequisite)
- [ ] Explicit user approval obtained
- [ ] Phase 8 design PR reviewed and approved
- [ ] TUHO fixture regression ready
- [ ] Oborovo fixture regression ready
- [ ] Each canonical promotion scoped individually

**Phase 8 must not begin without explicit user approval.**

---

## 14. Phase 7 Documents

| Document | Location | PR |
|----------|----------|---:|
| SHL Canonical Design | `docs/phase7_shl_canonical_module_design.md` | #99 |
| SHL Engine Implementation | `docs/phase7_shl_engine_implementation.md` | #103 |
| SHL Runtime Flag Wiring | `docs/phase7_shl_runtime_flag_wiring.md` | #107/108 |
| Senior Debt Sizing Design | `docs/phase7_senior_debt_canonical_module_design.md` | #100 |
| Depreciation Canonical Design | `docs/phase7_depreciation_canonical_module_design.md` | #102 |
| Depreciation Runtime Integration | `docs/phase7_depreciation_runtime_integration.md` | #105 |
| Tax Runtime Bridge | `docs/phase7_tax_runtime_bridge.md` | #110 |
| R99/R102 Source Ownership | `docs/phase7_r99_r102_source_ownership_design.md` | #109 |
| Runtime Stack Freeze | `docs/phase7_runtime_stack_freeze.md` | #111 |
| Closeout Review | `docs/phase7_closeout_review.md` | #112 |

---

*Phase 7 closed: 2026-05-19*  
*Document version: 1.0*