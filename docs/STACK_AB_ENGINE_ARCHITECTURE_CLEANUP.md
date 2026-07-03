# Stack AB — Engine Architecture Cleanup

**Date:** 2026-07-03  
**Branch:** `stack-ab-engine-architecture-cleanup`  
**Status:** Architecture documentation and targeted cleanup — no financial equations changed

---

## Executive Summary

An independent review identified two recurring implementation patterns that repeatedly create regressions:

1. **Identity-based engine behaviour** — engine logic gated on project name or code string
2. **Result mutation after engine execution** — post-run overwrites to computed financial outputs

This document provides the complete inventory of both patterns, classifies each occurrence, documents what was changed and what remains, and provides recommendations for future stacks.

**The financial engine is otherwise correct.** The architecture patterns documented here are the cause of maintenance friction, not computational errors.

---

## Guiding Principle

> The financial engine should operate based on **configuration and capabilities**, never on project identity.

```python
# Bad — identity-based
if project_code == "TUHO-WIND-1":
    apply_tax_bridge()

# Good — capability-driven
if inputs.use_tax_bridge_engine:
    apply_tax_bridge()
```

The problem is not the capability flags themselves. The problem is that the underlying implementations still contain hardcoded TUHO-specific constants, which forces the guards to check project identity as a proxy for "has this been calibrated?"

---

## AB1 — Identity Guard Inventory

### Production Engine Guards

#### `app/waterfall_core.py`

| Line | Guard | Classification |
|------|-------|----------------|
| 115 | `if use_tax_bridge_engine and code != "TUHO-WIND-1": raise` | **Technical debt** — Cannot remove until `TUHO_BOOK_TOTAL=72993.7` and `TUHO_TAX_TOTAL=70691.5` are replaced with configurable inputs. See §AB5. |
| 117 | `if use_shl_gross_accrued_for_pnl and code != "TUHO-WIND-1": raise` | **Technical debt** — SHL gross accrued bridge reads TUHO-specific R27 fixture. Guard is correct until fixture is parameterized. |
| 119 | `if use_tuho_shl_repayment_alignment and code != "TUHO-WIND-1": raise` | **Technical debt** — Flag name encodes project identity. Should be renamed `use_shl_matched_repayment_alignment` and guard removed after validating for all projects. |
| 140 | `if use_co2_revenue_bridge and code != "TUHO-WIND-1": raise` | **Technical debt** — CO2 revenue bridge uses TUHO-specific decomposition data. Acceptable guard until parameterized. |
| 159 | `if use_co2_cit_bridge and code != "TUHO-WIND-1": raise` | **Technical debt** — Same as CO2 revenue bridge. |
| 623–733 | Frozen senior DS fixture loaded by `project_code` lookup | **Identity dispatch / Technical debt** — **AB test finding.** Renaming TUHO to any other code causes `_frozen_senior_ds_wired=False` and changes `actual_avg_dscr` from 1.3786 to 1.5004. The fixture registry dispatches on project code string rather than a configured fixture path. Fix: add `frozen_senior_ds_fixture_path` to `FinancingParams` and read from there instead of project code. |
| 772 | `is_oborovo = (code == "OBOROVO-SOLAR-1")` | **Technical debt** — DA wiring uses `is_tuho` / `is_oborovo` as routing flags. Both should become config fields once DA engine supports both projects. |
| 1270 | `is_oborovo = (code == "OBOROVO-SOLAR-1")` | **Technical debt** — Same DA inner loop occurrence. |

**Summary:** 7 identity guard occurrences in `waterfall_core.py`. **None removed in this stack** because all are protecting against hardcoded constants or unvalidated code paths. Each requires parameter changes before the guard can be dropped.

#### `app/waterfall_runner.py` — Runner Layer

| Line (pre-AB) | Guard | Action |
|------|-------|--------|
| ~~231~~ | `if use_tax_bridge_engine and code != "TUHO-WIND-1": raise` | **✅ REMOVED** — Exact duplicate of core line 115. Core still enforces the guard. |
| ~~241~~ | `if use_shl_gross_accrued_for_pnl and code != "TUHO-WIND-1": raise` | **✅ REMOVED** — Exact duplicate of core line 117. Core still enforces the guard. |
| ~~248~~ | `if use_tuho_shl_repayment_alignment and code != "TUHO-WIND-1": raise` | **✅ REMOVED** — Exact duplicate of core line 119. Core still enforces the guard. |
| 222 | `if shl_fcf_waterfall and code != "TUHO-WIND-1": raise` | **Retained** — Not duplicated in core. Protects fixture-backed FCF schedule that only TUHO has. |
| 256 | `if use_shl_canonical_engine and code not in (...): raise` | **Retained** — Not duplicated in core. Guards untested code path on unknown projects. |
| 367 | `if config.use_tuho_shl_repayment_alignment and code != "TUHO-WIND-1":` | **Retained** — This is in the `run()` method, separate from `from_inputs()`. Has distinct runtime routing purpose. |

**Net change:** 3 duplicate identity guards removed from runner layer.

#### `domain/financial_statements/pnl.py`

| Line | Guard | Classification |
|------|-------|----------------|
| 131 | `if use_shl_gross_accrued_for_pnl and project_code != "TUHO-WIND-1": raise` | **Technical debt** — Duplicate of core guard (different layer). Retained: P&L domain should validate its own inputs independently. |
| 138 | `if use_book_depreciation_for_pnl and project_code != "TUHO-WIND-1": raise` | **Technical debt** — Book depreciation P&L bridge has TUHO-specific constants. |

#### `domain/construction/runtime_adapter.py`

| Pattern | Classification |
|---------|----------------|
| `if project_code == "TUHO-WIND-1": config = build_tuho_construction_config()` | **Technical debt / Requires redesign** — This is pure data dispatch masquerading as a capability guard. `build_tuho_construction_config()` and `build_oborovo_construction_config()` return the same `ConstructionConfig` type with different values. The correct fix is to add a `ConstructionInputs` sub-object to `ProjectInputs` and populate it in each factory. This is a schema change (out of scope for this stack). |
| `SUPPORTED_PROJECT_CODES = {"TUHO-WIND-1", "Oborovo", "OBR-001"}` | **Technical debt** — Hardcoded set. Should become a capability check. |

#### `domain/opex/runtime_adapter.py`

| Pattern | Classification |
|---------|----------------|
| `if project_code not in SUPPORTED_TUHO_CODES: raise ValueError(...)` | **Technical debt / Requires redesign** — OPEX adapter is TUHO-only. `domain/opex/templates/oborovo.py` exists but is never called. The fix is identical to construction: wire Oborovo template into the adapter once `use_opex_line_item_engine` is enabled for Oborovo. Currently Oborovo factory has `use_opex_line_item_engine=False` so this code path is never hit for Oborovo. |

### Service Layer Identity Patterns

These are **acceptable** — service code routing by user intent (`runtime_seed`) is an appropriate pattern at the service boundary. It is not engine-level identity gating.

| File | Pattern | Classification |
|------|---------|----------------|
| `app/services/run_service.py` | `if runtime_seed in {"tuho", "oborovo"}:` | **Acceptable** — Seed-based project factory selection. Correct boundary. |
| `app/services/save_run_service.py` | `if runtime_seed == "tuho": project_key = "TUHO"` | **Acceptable** — Service routing. |
| `app/services/download_service.py` | Same | **Acceptable** |
| `app/services/compare_service.py` | Same | **Acceptable** |
| `app/ui/project_context.py` | `get_project_context()` fallback to `"tuho"` | **Technical debt** — Hardcoded fallback to TUHO. Should be configurable or use a neutral default. |

### Diagnostic Code

| File | Pattern | Classification |
|------|---------|----------------|
| `domain/diagnostics/cfads_bridge.py` | `project_code="TUHO"` and `project_code="Oborovo"` hardcoded | **Acceptable** — Diagnostic-only, not production engine. These are label strings for human-readable output. |

---

## AB2 — Removed Identity Guards

### Changes made in `app/waterfall_runner.py`

**Before (3 duplicate guards):**
```python
use_tax_bridge_engine = getattr(inputs.info, "use_tax_bridge_engine", False)
if use_tax_bridge_engine and getattr(inputs.info, "code", "") != "TUHO-WIND-1":
    raise ValueError("Tax bridge runtime engine is currently supported only for TUHO-WIND-1")
...
if use_shl_gross_accrued_for_pnl and getattr(inputs.info, "code", "") != "TUHO-WIND-1":
    raise ValueError("Gross accrued SHL P&L bridge is currently supported only for TUHO-WIND-1")
...
if use_tuho_shl_repayment_alignment and getattr(inputs.info, "code", "") != "TUHO-WIND-1":
    raise ValueError("TUHO SHL repayment alignment is currently supported only for TUHO-WIND-1")
```

**After (3 comments documenting where protection lives):**
```python
use_tax_bridge_engine = getattr(inputs.info, "use_tax_bridge_engine", False)
# Stack AB: duplicate identity guard removed — waterfall_core enforces same guard at line 115.
...
# Stack AB: duplicate identity guard removed — waterfall_core enforces same guard at line 117.
...
# Stack AB: duplicate identity guard removed — waterfall_core enforces same guard at line 119.
```

**Why safe:** The runner's `from_inputs()` runs before `run_waterfall_v3_core()`. If a flag is set incorrectly, the core raises the identical error. The runner guards were defense-in-depth duplicates; removing them does not change any error message or behavior for any currently configured project.

**Test confirmation:** `TestZ1FactoryOptIn.test_oborovo_flag_on_is_still_guarded` continues to pass — the core guard at line 115 fires as before.

---

## AB3 — Result Mutation Inventory

### `app/waterfall_core.py` post-run mutations

All post-engine mutations occur in `run_waterfall_v3_core()` after the main `run_waterfall()` call.

| Mutation block | What it writes | Classification |
|---------------|----------------|----------------|
| `result.project_code = ...` (line 303) | Project code string metadata | **Should move into engine** — Simple metadata; belongs on the engine's return type. |
| CO2 revenue bridge annotation (lines 307–319) | `period.co2_revenue_bridge_keur`, `result._co2_revenue_bridge` | **Required (audit)** — Values pre-computed before waterfall; annotation doesn't change computation. |
| CO2 CIT bridge annotation (lines 323–335) | `period.co2_cit_bridge_keur`, `result._co2_cit_bridge` | **Required (audit)** — Same pattern as CO2 revenue. |
| `result.use_shl_gross_accrued_for_pnl` (line 336) | Config propagation | **Should move into engine** — Config should be carried through result, not attached post-run. |
| `_apply_tuho_shl_gross_accrued_interest_bridge` (line 337) | `period.shl_gross_accrued_interest_keur` | **Temporary** — Fixture injection from Excel R27 extract. Belongs upstream or in SHL engine once calibrated. |
| `_apply_tuho_tax_bridge_runtime_cash_tax` (lines 339–343) | 14 period fields + `result.total_tax_keur` | **Required for TUHO correctness / Should move into engine** — This is the largest mutation. It re-runs tax computation post-waterfall. Architecturally belongs inside the engine as a first-class tax mode. See §AB5. |
| Construction schedule diagnostic (lines 344–345) | `result.construction_schedule_diagnostic` | **Required (audit-only)** — Correct pattern; engine has no knowledge of construction. |
| Canonical SHL wiring (lines 348–361) | SHL-specific period fields | **Temporary** — Phase 8.1 bridging. Should move into engine. |
| Canonical depreciation wiring (lines 367–388) | `period.depreciation_keur`, `period.tax_depreciation_audit_keur` | **Temporary / Inconsistency risk** — Overwrites `depreciation_keur` AFTER engine used it for DSCR sculpting. Creates reporting/computation gap. |
| Canonical senior debt sizing audit (lines 394–608) | Private `_canonical_*` attributes | **Required (audit-only)** — No computation changed. |
| Frozen senior DS schedule (lines 623–733) | `period.dscr`, `result.actual_avg_dscr`, `result.actual_min_dscr` | **Temporary** — Overrides primary engine outputs. Phase Y bridging. Belongs in engine. |
| Dualrun validation (line 739) | `result._dualrun_validation` | **Required (audit-only)** — Explicitly diagnostic. |
| Distribution account wiring (lines 745–858) | `wp.distribution_keur`, `result.total_distribution_keur` | **Temporary / Identity-gated** — Uses `is_tuho` / `is_oborovo` checks internally; overrides primary distribution output. Phase 9C bridging. Belongs in engine. |

### Mutation classification summary

| Classification | Count |
|---------------|-------|
| Required (audit-only) | 4 |
| Should move into engine (config/metadata) | 2 |
| Temporary — belongs in engine, not yet safe to move | 4 |
| Required for correctness AND should move into engine | 1 |

**Net removed in this stack: 0 mutations.** All identified mutations are either genuinely required, or their removal would change financial output (stop condition). They are documented here for future stacks.

---

## AB4 — Mutation Architecture Note

The pattern of post-engine mutations exists because the engine was grown incrementally. Each new capability (SHL gross accrued, tax bridge, frozen DS, distribution account) was added as a post-processing pass rather than integrated into the engine core. This is a pragmatic choice that avoids touching the core engine while the new capability is validated.

The consequence is a layered computation:

```
run_waterfall()           ← primary computation
  ↓
_apply_shl_gross_accrued  ← SHL fixture injection
  ↓
_apply_tax_bridge         ← tax re-computation (overwrites tax fields, CF chain)
  ↓
_apply_frozen_ds          ← DS override (overwrites DSCR)
  ↓
_apply_distribution_account ← distribution override (overwrites distribution)
```

Each downstream mutation overwrites fields computed by an upstream step. This creates implicit ordering dependencies and makes it difficult to reason about which computation is the "source of truth" for any given field.

**Recommendation for future stacks:**
1. Convert each post-processing pass into an explicit engine "mode" flag
2. Move the computation inside the main engine loop
3. Remove the mutation pass once the engine mode produces identical outputs

The tax bridge (§AB5) is the most mature candidate for this treatment.

---

## AB5 — Tax Bridge Architecture

### Question: Should the tax bridge live inside the engine or as a post-processing layer?

**Current state:** Post-processing layer (`_apply_tuho_tax_bridge_runtime_cash_tax`). It is gated by `use_tax_bridge_engine=True` and runs after the main waterfall computation, overwriting 14 period fields and `result.total_tax_keur`.

**Option A: Move inside main engine**

Pros:
- Single computation pass
- No field overwrites
- Source of truth is clear

Cons:
- The current bridge has hardcoded TUHO constants (`TUHO_BOOK_TOTAL=72993.7`, `TUHO_TAX_TOTAL=70691.5`)
- Moving it inside the engine while keeping hardcoded constants would not help architecturally
- Would require parameterizing the constants first (math change)

**Option B: Retain as post-processing layer, but parameterize constants**

Pros:
- Lower-risk incremental improvement
- No engine core changes needed
- Bridge can be validated independently

Cons:
- Still two computation passes
- Ordering dependency between waterfall and bridge remains

**Recommendation: Option B (parameterize first, move second)**

The bridge should remain as a post-processing layer in the next stack but with constants extracted to project inputs:

```python
# Next stack: move from hardcoded to configured
book_total_keur = inputs.tax.book_depreciation_total_keur  # was: TUHO_BOOK_TOTAL = 72993.7
tax_total_keur = inputs.tax.tax_depreciation_total_keur    # was: TUHO_TAX_TOTAL = 70691.5
```

Once the constants are configurable:
1. The identity guard in `waterfall_core.py` at line 115 becomes unnecessary (any project with these values set can use the bridge)
2. Oborovo can opt in by setting its own values in its tax inputs
3. The move-inside-engine (Option A) becomes a safe refactor in a subsequent stack

**Why this stack does not implement Option B:**
Moving constants to `inputs.tax` requires:
- Adding fields to `TaxParams` or `ProjectInputs`
- Updating both factories
- Updating all tests that instantiate these types
- Validating that TUHO parity is preserved with the extracted values

This is a math-adjacent change that deserves its own stack with full parity verification.

---

## AB6 — WaterfallRunConfig Review

### Fields with identity-encoded names

The following `WaterfallRunConfig` fields have TUHO-specific names that encode project identity:

| Field | Should be renamed to | Impact |
|-------|---------------------|--------|
| `use_tuho_r99_input_engine` | `use_r99_input_engine` | 155 file occurrences — high rename risk |
| `use_tuho_shl_repayment_alignment` | `use_shl_matched_repayment_alignment` | 35 file occurrences |
| `tuho_shl_principal_eligibility_start_period` | `shl_principal_eligibility_start_period` | 25 file occurrences |
| `tuho_cit_cash_tax_start_operating_index` | `cit_cash_tax_start_operating_index` | 45 file occurrences |

**Not renamed in this stack.** The rename scope touches too many phase test files to safely batch into this stack. The risk of silent test breakage (tests that construct `WaterfallRunConfig` explicitly) outweighs the naming benefit at this time.

**Recommendation:** Rename in a dedicated cleanup stack where each rename can be verified independently. The `use_tuho_r99_input_engine` rename alone touches 155 files — it warrants its own stack.

### from_inputs() assessment

`WaterfallRunConfig.from_inputs()` reads all flag values from project `inputs.info` and `inputs.financing` (capability-driven). The identity checks are validation guards, not routing logic. The guard pattern `if flag and code != "TUHO-WIND-1": raise` is the correct pattern for protecting unvalidated code paths — it is the hardcoded constants in the bridge implementations that are the root cause.

### Fields that ARE correctly capability-driven

These are correct and should be preserved:
- `use_senior_rate_schedule_engine` — reads `inputs.info.use_senior_rate_schedule_engine`
- `use_senior_sculpting_basis_engine` — reads from project config
- `use_depreciation_canonical_engine` — reads from project config
- `use_senior_debt_sizing_engine` — reads from project config
- `use_frozen_excel_senior_debt_schedule` — reads from financing config
- `use_tax_bridge_engine` — reads from project config (capability-driven ✅; guard is identity-driven ❌)

---

## Summary of Changes

### Changed in this stack

| File | Change | Rationale |
|------|--------|-----------|
| `app/waterfall_runner.py` | Removed 3 duplicate identity guards (lines 231, 241, 248 pre-AB) | Guards were exact duplicates of `waterfall_core.py` lines 115, 117, 119. Core still enforces them. |
| `docs/STACK_AB_ENGINE_ARCHITECTURE_CLEANUP.md` | Created (this document) | Complete inventory and roadmap |
| `tests/test_stack_ab_engine_architecture_cleanup.py` | Created (new) | Tests proving config-driven behavior and no identity-based routing in WaterfallRunConfig |

### Not changed in this stack (with rationale)

| Item | Why not changed |
|------|----------------|
| Core identity guards (waterfall_core.py lines 115–159) | Protect against hardcoded TUHO constants; removing without parameterizing would allow silent wrong results |
| Tax bridge constants (`TUHO_BOOK_TOTAL`, `TUHO_TAX_TOTAL`) | Requires adding fields to `TaxParams`/`ProjectInputs` — math-adjacent schema change; own stack |
| Construction runtime_adapter dispatch | Requires `ConstructionInputs` schema addition to `ProjectInputs`; own stack |
| OPEX runtime_adapter dispatch | Requires factory changes; wire Oborovo template; own stack |
| Flag renames (`use_tuho_*`, `tuho_*`) | 155–25 file touches; high phase-test breakage risk; own stack |
| Post-engine mutations | All either required or math-changing to remove; documented for future stacks |
| `WaterfallRunConfig` restructuring | Requires parameterizing bridge constants first |
| Distribution account `is_tuho`/`is_oborovo` | Phase 9C wiring in progress; removal requires DA engine generalization |

---

## Confirmed Guardrails

- ✅ No financial equations changed
- ✅ No parity targets changed
- ✅ No debt sizing changes
- ✅ No SHL algorithm changes
- ✅ No IRR algorithm changes
- ✅ No tax bridge mathematics changed
- ✅ No LCF changes
- ✅ No ATAD changes
- ✅ No depreciation bridge changes
- ✅ All CI jobs green

---

## Recommendations for Future Stacks

### Stack AC (recommended next)
**Parameterize tax bridge constants.**
- Add `book_depreciation_total_keur` and `tax_depreciation_total_keur` to `TaxParams`
- Populate from TUHO factory (same values as current hardcoded)
- Update bridge to read from inputs rather than constants
- Remove identity guard at waterfall_core.py line 115
- Enable Oborovo to opt-in by setting its own values

### Stack AD
**Rename TUHO-named flags.**
- `use_tuho_r99_input_engine` → `use_r99_input_engine`
- `use_tuho_shl_repayment_alignment` → `use_shl_matched_repayment_alignment`
- `tuho_shl_principal_eligibility_start_period` → `shl_principal_eligibility_start_period`
- `tuho_cit_cash_tax_start_operating_index` → `cit_cash_tax_start_operating_index`
- Use a systematic sed-style rename; verify all parity tests pass

### Stack AE
**Wire construction and OPEX adapters as data-driven lookups.**
- Add `ConstructionScheduleParams` to `ProjectInputs`
- Wire `build_oborovo_opex_template()` for Oborovo in OPEX adapter
- Eliminate project_code dispatch in both adapters

### Stack AF (longer term)
**Move tax bridge inside the engine.**
- Prerequisite: AC complete (parameterized constants)
- Move `_apply_tuho_tax_bridge_runtime_cash_tax` logic into the main waterfall loop
- Remove post-engine mutation pass
- Single source of truth for all tax computation
