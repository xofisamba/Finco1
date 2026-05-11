# Phase 6 Tax Consolidation Review

**Repository:** xofisamba/Finco1
**Branch:** `phase6e-tax-consolidation-review`
**Date:** 2026-05-11
**Purpose:** Architecture + audit checkpoint before Phase 7 (sponsor economics)

---

## 1. Current Main State

| Item | Value |
|------|-------|
| Main SHA | `559874c231403a7fa3189c89447ace471eadcc63` |
| RC1 SHA | `b425a0708719eaa5e1d922b1008e5609758e0ad4` |
| RC1 touched | ❌ No — rc1 is a separate public branch, never merged into main during Phase 6 |
| Phase 6 PRs merged | 10 (PRs #26–#39, excluding #32 which is a plan-only merge) |
| Active tax branches | 0 (all merged, branch cleanup recommended post-review) |

### Merged Phase 6 PRs

| PR | Phase | SHA | Description |
|----|-------|-----|-------------|
| #26 | 6A | `4a1a421` | Phase 6A tax architecture foundation |
| #27 | 6B.1 | `75a873f` | Phase 6B.1 tax calculation foundation |
| #28 | 6B.2 | `737467f` | Phase 6B.2 tax schedules foundation |
| #29 | 6B.3 | `f90dcb9` | Phase 6B.3 SPV tax engine foundation |
| #32 | 6B.7 | `56f4293` | Phase 6B.7 tax waterfall integration plan (plan only, no code) |
| #34 | 6B-E | `f524b89` | Phase 6B.4+ audit/export integration |
| #37 | 6C | `edf1ade` | Phase 6C HoldCo tax export integration |
| #38 | 6D.1 | `872ef20` | Phase 6D.1 tax assumptions UI foundation |
| #39 | 6D.2 | `559874c` | Phase 6D.2 tax assumptions snapshot export |

### Active / Open Tax Branches

| Branch | Status | Notes |
|--------|--------|-------|
| `origin/phase6e-tax-consolidation-review` | **This branch** | Docs only — consolidation review |
| All other phase6* branches | Merged to main | Should be pruned after review |

---

## 2. Phase 6 Inventory

| Phase | PR | SHA | Status | Description |
|-------|-----|-----|--------|-------------|
| 6A foundation | #26 | `4a1a421` | ✅ Merged | Schema, templates, primitives, initial docs |
| 6B.1 primitives | #27 | `75a873f` | ✅ Merged | `domain/tax/tax_calculation.py` pure functions |
| 6B.2 schedules | #28 | `737467f` | ✅ Merged | `domain/tax/tax_schedules.py` SPV tax schedule builder |
| 6B.3 SPV engine | #29 | `f90dcb9` | ✅ Merged | `domain/tax/engine_runner.py` + inputs + schema |
| 6B.4 audit | #34 | `f524b89` | ✅ Merged | `app/tax_excel_export.py` SPV audit sheets |
| 6B.7 plan | #32 | `56f4293` | ✅ Merged | `docs/tax_waterfall_integration_plan.md` — design only |
| 6B.5+ integration | #34 | `f524b89` | ✅ Merged | `app/excel_export.py` optional tax_results hook |
| 6C schema | — | — | ✅ Merged | `domain/tax/schema.py` HoldCo tax schema |
| 6C.1 primitives | — | — | ✅ Merged | HoldCo withholding tax primitives |
| 6C.2 calculations | — | — | ✅ Merged | HoldCo CIT calculation (audit-only, no enforcement) |
| 6C.3 runner | — | — | ✅ Merged | `run_holdco_tax_engine()` audit-only |
| 6C.5 audit | #37 | `edf1ade` | ✅ Merged | `app/holdco_tax_excel_export.py` HoldCo audit sheets |
| 6C export int. | #37 | `edf1ade` | ✅ Merged | `app/excel_export.py` optional holdco_tax_results hook |
| 6D.1 UI | #38 | `872ef20` | ✅ Merged | `app/tax_assumptions_ui.py` 6 helper functions |
| 6D.1 export | #38 | `872ef20` | ✅ Merged | `app/tax_assumptions_excel_export.py` audit sheets |
| 6D.2 snapshot | #39 | `559874c` | ✅ Merged | `domain/tax/assumptions_snapshot.py` immutable dataclasses |
| 6D.2 export | #39 | `559874c` | ✅ Merged | `app/tax_assumptions_snapshot_excel_export.py` direct export |

---

## 3. Architecture Review

### Layering

```
templates.inputs
    │
    ▼
tax_calculation.py (pure primitives, no side effects)
    │
    ▼
tax_schedules.py (schedule builder, stateless)
    │
    ▼
engine_inputs.py (schema / validation)
    │
    ▼
engine_runner.py (state machine, no waterfall mutation)
    │
    ▼
holdco_runner.py (separate schema, no waterfall mutation)
    │
    ▼
excel_export.py (optional hook, no waterfall mutation)
    │
    ▼
tax_assumptions_ui.py (pure helpers, no side effects)
    │
    ▼
assumptions_snapshot.py (immutable dataclasses)
    │
    ▼
tax_assumptions_snapshot_excel_export.py (direct snapshot export)
```

### Separation from Waterfall

**✅ Confirmed — no circular dependencies**

- `domain/tax/` never imports `app.waterfall_core` or `domain.portfolio.waterfall`
- `app/excel_export.py` only reads tax engine outputs; waterfall is unaffected
- `app/waterfall_core.py` never imports `domain/tax/`
- Optional hooks use `if tax_results is not None` guards — zero mandatory coupling
- HoldCo overlay in `domain/portfolio/` reads from cash ledger, not tax engine

**✅ No mutation of waterfall state**

- `run_spv_tax_engine()` returns results as immutable dataclasses
- `run_holdco_tax_engine()` returns results as immutable dataclasses
- `TaxAssumptionSnapshot` is frozen (all fields immutable)
- No `DistributionConstraint` or `DistributionResult` is modified during tax operations

**✅ Optional export isolation**

- `build_excel_export(tax_results=None, holdco_tax_results=None, tax_assumption_snapshot=None)`
- Default `None` preserves existing export behavior exactly
- Snapshot export creates separate "Tax Snapshot *" sheets, no overlap with existing sheets
- Sheet names sanitized to 31-char Excel limit, deduplicated

**✅ Immutable snapshot architecture**

- `TaxAssumptionSnapshot`, `TaxTemplateSnapshot`, `TaxOverrideSnapshot`, `ResolvedTaxConfigSnapshot` are all `@dataclass(frozen=True)`
- Normalization in `__post_init__` converts lists/dicts → tuples
- Snapshot stores only snapshot dataclasses, no original mutable objects
- Builders accept original objects as input but emit only snapshot dataclasses

---

## 4. Tax Semantics Review

### Progressive CIT Handling
- CIT tiers sorted by `min_profit_keur`; unbounded tier must be last
- Only one unbounded tier allowed per template
- First tier must start at 0.0 kEUR
- No overlapping ranges; contiguous required
- Tier boundaries are configurable per template (not hardcoded)
- Audit export captures tiers as summary strings ("10%", "15%") — no reinterpretation

### Tax Depreciation vs Accounting Depreciation
- `tax_schedules.py` builds **tax book** depreciation (accelerated where applicable)
- `app/output_tables.py` builds **accounting book** depreciation (straight-line or asset-life based)
- Two separate schedules are kept distinct throughout
- `Tax_Depreciation` sheet in Excel = tax book only (audit export)
- `Debt` sheet uses accounting book values for interest deduction calculations

### Deductible vs Non-Deductible Depreciation
- `TaxDepreciationRule.deductible` boolean field per asset category
- Non-deductible depreciation included in tax book but flagged
- Audit export captures `Deductible` column per rule
- Tax engine inputs include `deductible_interest_by_period_keur` (separate from book dep)

### SHL Interest vs Principal
- `domain/tax/tax_calculation.py`: `exclude_shl_principal_from_taxable_income()` returns 0 (principal excluded)
- `calculate_holdco_taxable_income()` adds interest income, excludes principal
- **Confirmed**: SHL principal is never included in taxable income
- WHT on SHL interest is visible in audit sheets; WHT on SHL principal = 0

### HoldCo vs SPV Separation
- SPV: `domain/tax/engine_runner.py` — computes SPV CIT payable
- HoldCo: `domain/tax/holdco_runner.py` — computes HoldCo CIT on intercompany income
- HoldCo does **not** deduct SPV-level taxes (SPV and HoldCo are separate legal entities)
- HoldCo intercompany schema: dividend income + SHL interest income - HoldCo OpEx = taxable income
- SPV and HoldCo tax are computed independently, never chained

### WHT Visibility
- WHT rates stored in `TaxTemplate.withholding_tax_dividends` / `withholding_tax_interest`
- Audit export shows WHT as "Has WHT Dividend" / "Has WHT Interest" booleans
- WHT calculation (`calculate_withholding_tax_keur()`) is implemented in `holdco_calculations.py`
- **Audit-only**: WHT is computed but not remitted or reflected in cash flows
- HoldCo audit sheets show WHT amounts per period per entity

### Audit-Only Constraints

| Constraint | Status |
|------------|--------|
| No cash tax timing | ✅ Confirmed — tax is computed but no cash flow integration |
| No deferred tax | ✅ Confirmed — no deferred tax asset/liability tracking |
| No tax cashflow integration | ✅ Confirmed — `tax_results` is output-only |
| No sponsor IRR integration | ✅ Confirmed — waterfall untouched |

---

## 5. Governance / Snapshot Review

### Immutable Snapshot Strategy
- Snapshot captures a point-in-time view of tax configuration
- Frozen dataclasses ensure snapshot cannot be retroactively edited
- `created_at` timestamp records when snapshot was taken
- `snapshot_label` field allows human-readable naming (e.g., "FY2026 v1", "Pre-sponsor review")
- Audit note in every snapshot row: "AUDIT-ONLY: read-only governance artifact"

### Override Visibility
- `TaxOverrideSnapshot` captures: `override_name`, `field_path`, `override_value`, `reason`
- Override summary shown in `ResolvedTaxConfigSnapshot.overrides_summary`
- Override audit note on every override row
- No active enforcement of overrides — visibility only

### Resolved Config Visibility
- `ResolvedTaxConfigSnapshot` shows effective CIT structure after overrides
- Override count and per-override summary visible in snapshot
- `resolved_metadata` field captures metadata after overrides applied
- Resolved config snapshot created via `build_resolved_tax_config_snapshot()`

### Audit Note Strategy
- Every snapshot dataclass field carries an `audit_note` field
- Every Excel sheet starts with row 1 = audit-only disclaimer
- Excel export helpers include `AUDIT-ONLY` prefix in first cell of every sheet
- Audit notes propagated from builder → snapshot → Excel

### Future Approval Workflow Readiness
- Snapshot + override metadata provides full audit trail
- Override count and details captured for review
- Audit sheet isolation means workflow engine can approve/reject snapshots
- No editable persistence yet — but schema is ready for it

### Future Persistence Readiness
- Frozen snapshot dataclasses are serializable to JSON
- `snapshot_label` + `created_at` provide natural unique keys for storage
- Override and resolved config snapshots can be stored independently
- No database schema yet — but domain layer has no persistence coupling

---

## 6. Excel / UI Review

### Audit-Only Sheets

| Sheet | Source | Row 1 |
|-------|--------|-------|
| Tax Summary | `tax_excel_export.py` | AUDIT-ONLY |
| Tax_{EntityCode} | `tax_excel_export.py` | AUDIT-ONLY |
| HoldCo Tax Summary | `holdco_tax_excel_export.py` | AUDIT-ONLY |
| HoldCo Tax_{EntityCode} | `holdco_tax_excel_export.py` | AUDIT-ONLY |
| Tax Templates | `tax_assumptions_excel_export.py` | AUDIT-ONLY |
| Tax Tiers | `tax_assumptions_excel_export.py` | AUDIT-ONLY |
| Tax Dep Rules | `tax_assumptions_excel_export.py` | AUDIT-ONLY |
| Tax Overrides | `tax_assumptions_excel_export.py` | AUDIT-ONLY |
| Resolved Tax Config | `tax_assumptions_excel_export.py` | AUDIT-ONLY |
| Tax Snapshot Templates | `tax_assumptions_snapshot_excel_export.py` | AUDIT-ONLY |
| Tax Snapshot Overrides | `tax_assumptions_snapshot_excel_export.py` | AUDIT-ONLY |
| Tax Snapshot Resolved | `tax_assumptions_snapshot_excel_export.py` | AUDIT-ONLY |

### Optional Integration
- All tax sheets are **opt-in** via parameters:
  - `build_excel_export(tax_results=None, holdco_tax_results=None, tax_assumption_snapshot=None)`
- Default `None` produces identical output to pre-tax state
- No mandatory tax coupling to any existing workflow

### Sheet Naming
- Names sanitized: `/\*?[]:` replaced with `_`
- 31-character Excel limit enforced
- Deduplication: base → base_2 → base_3 if name collision
- "Tax Snapshot *" prefix distinguishes from existing "Tax Summary" / "Tax_*" sheets

### Export Isolation
- `write_tax_assumptions_audit_sheets()` only writes new sheets, never modifies existing
- `write_tax_assumption_snapshot_sheets()` creates "Tax Snapshot *" prefix sheets
- Separate helper (`app/tax_assumptions_snapshot_excel_export.py`) for snapshot export
- No shared sheet names between export helpers

### Helper-Only UI Philosophy
- `app/tax_assumptions_ui.py`: pure functions returning `pd.DataFrame`
- No Streamlit rendering (not in scope)
- No editable persistence (not in scope)
- No role system (not in scope)
- All helpers have docstrings and type annotations
- Pure functions: no mutation of inputs, no side effects

---

## 7. Risk Register

### HIGH

| Risk | Affected Modules | Why It Matters | Mitigation | Blocker? |
|------|-----------------|----------------|------------|----------|
| **Tax timing circularity** | `engine_runner.py`, `tax_calculation.py` | SPV CIT depends on EBITDA, which includes interest deductions that depend on debt schedule, which may depend on tax attributes | Tax engine reads `ebitda_by_period_keur` as input; circular reference prevented by feeding exogenous EBITDA | ❌ No — inputs are pre-computed |
| **Future sponsor waterfall integration** | `excel_export.py`, waterfall | Sponsor IRR/MOIC downstream may depend on tax results; integration path not yet designed | Phase 6B.7 integration plan documented; integration must be explicit + reviewed | ❌ Not yet — plan only |
| **Multi-jurisdiction complexity** | `templates.inputs`, `engine_runner.py` | Cross-border SHL, treaty WHT, thin-cap rules not modeled | Templates are per-country; multi-jurisdiction consolidation not in scope | ❌ Not yet |

### MEDIUM

| Risk | Affected Modules | Why It Matters | Mitigation | Blocker? |
|------|-----------------|----------------|------------|----------|
| **WHT timing / remittance** | `holdco_calculations.py`, `holdco_runner.py` | WHT is computed but not remitted; no cash flow or payment scheduling | Phase 6 scope = visibility only; cash integration deferred | ❌ Not yet |
| **Thin-cap enforcement** | `holdco_calculations.py` | ATAD-style thin-cap limit stored but not enforced against actual debt schedule | Config stored in template; enforcement is Phase 7+ | ❌ Not yet |
| **Progressive CIT edge cases** | `tax_calculation.py` | Complex multi-tier with loss carryforward interactions not tested end-to-end | Tier validation in `TaxTemplate.__post_init__`; edge case tests needed | ❌ Partial — validation exists but no full model integration |
| **Future persistence governance** | snapshot layer | Snapshots will need storage, versioning, access control | Schema designed for serialization; governance TBD | ❌ Not yet |

### LOW

| Risk | Affected Modules | Why It Matters | Mitigation | Blocker? |
|------|-----------------|----------------|------------|----------|
| **Deprecated datetime.utcnow()** | `persistence/repository.py`, `assumptions_snapshot.py` | Python 3.12+ deprecation warnings | No impact on functionality; future cleanup | ❌ No |
| **FutureWarning: pd.concat empty/all-NA** | `tax_assumptions_excel_export.py` | Deprecation warning from pandas about empty frame concat | harmless in current pandas; future fix when pandas removes behavior | ❌ No |
| **Audit note string duplication** | all export helpers | `AUDIT-ONLY` note repeated across helpers | Future refactor: single constant; not a correctness issue | ❌ No |

---

## 8. Explicit Non-Scope

The following were explicitly excluded from Phase 6 and must not be added without new requirements:

| Item | Status | Reason |
|------|--------|--------|
| Deferred tax | ❌ Not implemented | Requires monthly model / P&L integration |
| Tax cashflow timing | ❌ Not implemented | No cash flow hooks in waterfall |
| Monthly model | ❌ Not implemented | Semiannual model only |
| Sponsor waterfall | ❌ Not implemented | Phase 7 topic |
| Sponsor IRR / MOIC | ❌ Not implemented | Phase 7 topic |
| Promote waterfall | ❌ Not implemented | Not in sponsor economics scope |
| Approval workflow | ❌ Not implemented | Governance layer deferred |
| Editable persistence | ❌ Not implemented | Storage layer deferred |
| Role system | ❌ Not implemented | Access control deferred |
| Real enforcement | ❌ Not implemented | Tax engine is computation-only |
| Tax payment scheduling | ❌ Not implemented | Cash management not in scope |
| Multi-jurisdiction consolidation | ❌ Not implemented | Single-jurisdiction templates only |
| Treaty engine | ❌ Not implemented | Cross-border treaty WHT not modeled |
| Tax audit representation | ❌ Not implemented | Legal/tax counsel not engaged |
| RC1 modification | ❌ Not implemented | Rate card untouched throughout Phase 6 |

---

## 9. Phase 7 Readiness

### Is Phase 6 Safe to Freeze?

**✅ Yes — with conditions**

Phase 6 is a stable, well-tested audit/export layer. The following must be reviewed before Phase 7 begins:

1. **Tax engine inputs contract** — `SPVTaxEngineInputs` and `HoldCoTaxEngineInputs` schemas are stable; changes require migration plan
2. **Override resolution** — `ResolvedTaxConfig` schema is stable; adding new fields requires versioning
3. **Excel sheet naming** — "Tax Snapshot *" prefix is deliberate; do not rename without migration plan for existing exports
4. **rc1 integration path** — `DistributionConstraint` and `rc1` are untouched by tax engine; Phase 7 must not mutate rc1 via tax outputs without explicit review

### Can Sponsor Economics Begin?

**⚠️ Partial — sponsor waterfall not ready**

- Sponsor IRR / MOIC / promote waterfall are Phase 7 topics
- Tax audit sheets are available for sponsor due diligence
- Immutable snapshot layer provides governance audit trail
- `tax_results` and `holdco_tax_results` are computed but NOT fed into sponsor waterfall
- Distribution constraints (`rc1`) are independent of tax engine

### What Should Be Reviewed Before Phase 7

1. **SPV CIT engine correctness** — Does computed CIT match manual calculations for known scenarios?
2. **HoldCo WHT computation** — Are WHT amounts on SHL interest correctly computed?
3. **Override resolution** — Do resolved configs correctly reflect override application?
4. **Excel sheet governance** — Who has access to audit sheets? Are they labeled clearly?
5. **rc1 stability** — Are distribution constraints robust to tax engine results being introduced?
6. **Progressive CIT edge cases** — Loss carryforward interaction with multi-tier progressive CIT not fully tested

### Expected Integration Risks with Sponsor Waterfall

| Risk | Likelihood | Impact |
|------|-----------|--------|
| Tax results fed into sponsor waterfall before rc1 stabilization | Medium | Incorrect distribution priority |
| Circular reference: debt schedule ↔ tax interest deduction | Medium | Non-convergence in iterative solves |
| WHT timing mismatch: SHL repayment vs WHT remittance | Low | Small cash discrepancy |
| Progressive CIT tier boundary changes on sponsor economics | Low | Minor sponsor IRR shift |
| HoldCo CIT not deducted from SPV distributions (by design) | Known | No impact — intentional separation |

---

## 10. Claude Review Checklist

Use this checklist during architecture review sessions.

### Architecture
- [ ] No circular dependencies between `domain/tax/` and `app/waterfall_core.py` / `domain/portfolio/`
- [ ] All tax engine functions are pure (no mutation, deterministic output)
- [ ] All schema classes are frozen (`@dataclass(frozen=True)`)
- [ ] Snapshot dataclasses are immutable and normalize all list/dict inputs to tuples
- [ ] Optional integration guards (`if x is not None`) prevent mandatory coupling
- [ ] No `rc1` references in `domain/tax/` or `app/tax_assumptions*.py`

### Tax Semantics
- [ ] Progressive CIT tiers: sorted, non-overlapping, unbounded last, first starts at 0
- [ ] Tax depreciation vs accounting depreciation: two separate schedules, never conflated
- [ ] `TaxDepreciationRule.deductible` correctly propagated to engine inputs
- [ ] SHL principal excluded from taxable income (never added to `gross_income`)
- [ ] SHL interest included in taxable income at applicable WHT rate
- [ ] WHT calculation: `calculate_withholding_tax_keur(gross, rate)` is correct
- [ ] HoldCo does not deduct SPV-level taxes (separate legal entities)

### SHL Treatment
- [ ] `exclude_shl_principal_from_taxable_income()` returns 0 always
- [ ] `calculate_holdco_taxable_income()` adds SHL interest, excludes SHL principal
- [ ] Audit export shows WHT on SHL interest separately from WHT on dividends
- [ ] `has_wht_interest` boolean captured in `TaxTemplateSnapshot`
- [ ] No SHL principal in `holdco_overlay.py` taxable income computation

### WHT Treatment
- [ ] `withholding_tax_dividends` and `withholding_tax_interest` stored in `TaxTemplate`
- [ ] WHT is computed but NOT remitted (audit-only)
- [ ] `calculate_withholding_tax_keur()` returns correct amount
- [ ] WHT rate applied correctly per country/template
- [ ] Audit sheets show WHT amounts per entity per period

### Layering
- [ ] `templates.inputs` → `tax_calculation` → `tax_schedules` → `engine_inputs` → `engine_runner` → `holdco_runner` → `excel_export`
- [ ] No layer skips another or imports downstream modules
- [ ] `excel_export.py` hooks are optional and additive (no sheet modification)
- [ ] Snapshot layer sits above all others (read-only, no downward imports)

### Immutability
- [ ] `TaxAssumptionSnapshot` is frozen with no mutable fields
- [ ] `TaxTemplateSnapshot`, `TaxOverrideSnapshot`, `ResolvedTaxConfigSnapshot` all frozen
- [ ] Builder functions accept objects as input but emit only immutable snapshots
- [ ] No `__post_init__` mutation after field assignment (except tuple normalization)
- [ ] `created_at` timestamps are non-nullable in snapshot dataclasses

### Export Isolation
- [ ] All tax sheets use "AUDIT-ONLY" prefix in row 1
- [ ] Sheet names sanitized for Excel (`/\*?[]:` → `_`, 31-char limit)
- [ ] Deduplication strategy: base → base_2 → base_3
- [ ] Snapshot sheets use "Tax Snapshot *" prefix (distinct from "Tax Summary" / "Tax_*")
- [ ] No existing sheets are modified by any tax export helper
- [ ] Default `None` parameters preserve pre-tax export behavior

### Sponsor-Readiness
- [ ] Tax engine outputs do not automatically flow into sponsor waterfall
- [ ] rc1 distribution constraints are independent of tax engine results
- [ ] Immutable snapshots provide audit trail for due diligence
- [ ] No sponsor IRR / MOIC / promote waterfall in Phase 6 scope
- [ ] HoldCo/SPV separation confirmed (HoldCo does not deduct SPV taxes)

### Future Persistence / Workflow
- [ ] Snapshot schemas are JSON-serializable (all tuple fields, primitive values)
- [ ] `snapshot_label` + `created_at` provide natural unique identifiers
- [ ] Override metadata captured for governance review
- [ ] No database coupling in `domain/tax/` (persistence layer deferred)
- [ ] Approval workflow schema not defined (readiness only)

### Circularity Risks
- [ ] Tax engine reads `ebitda_by_period_keur` as pre-computed input (no circular reference)
- [ ] `SPVTaxEngineInputs.ebitda_by_period_keur` is fed from waterfall, not computed in tax engine
- [ ] `holdco_overlay.py` reads from cash ledger, not from tax engine outputs
- [ ] No `domain/tax/` → `app/waterfall_core` imports found

### Progressive CIT Correctness
- [ ] Tiers sorted by `min_profit_keur` in `TaxTemplate.__post_init__`
- [ ] No overlapping ranges enforced (value error if violated)
- [ ] Contiguous ranges enforced (next.min == current.max)
- [ ] Exactly one unbounded tier allowed (must be last)
- [ ] First tier must start at 0.0 (enforced in validation)
- [ ] Audit export captures tier structure as summary strings (not reinterpreted)

---

## Appendix: Test Results (Pre-Commit)

```
tests/:                                  2413 passed, 1 skipped, 1 xfailed, 133 warnings
tests/test_tax_assumptions_snapshot.py:    17 passed
tests/test_tax_assumptions_ui.py:          19 passed
tests/test_tax_assumptions_excel_export.py: 19 passed
tests/test_excel_export.py:               78 passed
tests/test_holdco_tax_*.py:             155 passed
```

### Key Observations
- **No test failures** across full suite
- **1 xfailed** (expected failure — intentional)
- **1 skipped** (platform/environment specific, not tax-related)
- **133 warnings** — all deprecation warnings (datetime.utcnow, compute_waterfall_cached); zero correctness issues

---

*End of Phase 6 Tax Consolidation Review*
*Prepared for Claude architecture review*
*Phase 6E / branch: phase6e-tax-consolidation-review*
