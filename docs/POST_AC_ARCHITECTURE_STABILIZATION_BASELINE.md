# Post-AC Architecture Stabilization Baseline

**Date**: 2026-07-03  
**Main HEAD SHA**: `d3ca68d693635ff031f039054380fe8c32f3042b`  
**Purpose**: Formal engineering reference point for Finco One following the completion of the Stack K–AC implementation programme. No further financial engine development should occur from this main until the next architecture decision is ratified.

---

## 1. Baseline

| Field | Value |
|-------|-------|
| Date | 2026-07-03 |
| Main HEAD SHA | `d3ca68d693635ff031f039054380fe8c32f3042b` |
| Merged stacks | K, L, M, N, O, P, Q, R, S, T, T0, U, V, W, X, Y, Z, AA, AB, AC |
| Open stacks | None |
| Tag | None (this document is the canonical reference) |

This baseline marks the completion of the structured implementation programme that began with Stack K (Golden Model Calibration) and concluded with Stack AC (Runtime Identity Elimination Phase 1). The codebase is stable, parity-verified, and architecturally audited.

---

## 2. Financial Engine Status

### Golden Parity

Both production projects (TUHO Wind 1 and Oborovo Solar) are calibrated against their respective Golden Excel models. All parity targets are within tolerance and SHA-pinned by the Phase 51F guardrails.

| Project | KPI | Target | Tolerance | Status |
|---------|-----|--------|-----------|--------|
| TUHO Wind 1 | Equity IRR | 11.32% | ±0.05% | PASS |
| TUHO Wind 1 | Actual avg DSCR | 1.3786 | ±0.001 | PASS |
| TUHO Wind 1 | Total tax | 45,835 kEUR | ±500 kEUR | PASS |
| TUHO Wind 1 | Total distributions | 165,471 kEUR | ±200 kEUR | PASS |
| Oborovo Solar | Equity IRR | 10.54% | ±0.05% | PASS |
| Oborovo Solar | Actual avg DSCR | 1.179 | ±0.005 | PASS |
| Oborovo Solar | Total tax | 8,874 kEUR | ±100 kEUR | PASS |

### TUHO Wind 1 (Croatian onshore wind, 30-year, semiannual)

- Senior debt: fixture-backed frozen DS schedule via `phase7_tuho_senior_debt_sizing_extraction.csv`
- Tax bridge: `use_tax_bridge_engine=True`; applies runtime tax depreciation bridge (Stack Z)
- SHL: PIK phase Y1–Y14, sweep phase Y15+; gross accrued SHL P&L wired
- LCF: 5-year rolling Croatian §16 — correct; −5,271 kEUR residual vs Excel (Excel uses perpetual LCF incorrectly; Finco behaviour preserved)
- DSCR: backward-computed from frozen fixture; `_frozen_senior_ds_wired=True`

### Oborovo Solar PV (Croatian solar, 30-year, semiannual)

- Senior debt: fixture-backed frozen DS schedule via `phase23q_oborovo_senior_debt_sizing_extraction.csv`
- Tax bridge: disabled (`use_tax_bridge_engine=False`)
- SHL: 20-year bullet; SHL P&L gross accrued wiring disabled
- LCF: 5-year rolling Croatian §16
- DSCR: backward-computed from frozen fixture using DS!R57 basis

### Debt Sizing

- Canonical senior debt sizing engine active for both projects (`use_senior_debt_sizing_engine=True`)
- Sizing CFADS loaded from fixture CSV; target DSCR per-period from fixture
- Debt service capacity = sizing_cfads / target_dscr (exact match to Excel DS!R57)

### SHL (Shareholder Loan)

- TUHO: PIK then sweep, SHL IDC 3,568.69 kEUR, gross accrued P&L bridge active
- Oborovo: bullet, 20-year tenor, SHL IDC 1,169 kEUR
- SHL repayment priority correctly ordered before equity distributions in both projects

### Distributions

- Both projects use DA (Distribution Account) waterfall with DSCR lockup gate
- Lockup threshold: 1.10; distribution gate: 1.15
- R99/R102 Distribution Account: audit-only, not wired to distribution gate (intentional governance deferral)

### Tax Bridge

- TUHO: runtime cash tax bridge applies `TUHO_BOOK_TOTAL=72,993.7 kEUR` (book depreciation) and `TUHO_TAX_TOTAL=70,691.5 kEUR` (tax depreciation) over 60 semiannual periods
- Net depreciation effect per period: `tax_dep − book_dep = −38.37 kEUR` (reduces taxable income)
- Bridge formula: `taxable = EBITDA − book_dep − deductible_interest + disallowed_interest + tax_dep + fiscal_reintegration`
- Bridge constants are still hardcoded — parameterization deferred to Stack AD

### Exports

- Audit CSV export: all 7 required columns present (Stack V)
- Column labels reconciled with Excel sheet headers
- Download route tested at both TUHO and Oborovo

### Runtime

- Waterfall engine: `run_waterfall_v3_core()` in `app/waterfall_core.py`
- Period engine: `app/period_engine_runner.py` via `_build_period_engine()`
- Runner: `WaterfallRunner` + `WaterfallRunConfig` (frozen dataclass, capability-driven)
- UI: Streamlit; `app/ui_runner.py` exposes `run_demo_project()` and `_build_period_engine()`

---

## 3. Architecture Status

### Completed

**Golden Parity Programme (Stacks K–Q)**  
Systematic calibration of TUHO and Oborovo against Excel Golden Models. Each stack addressed a specific KPI gap: DSCR denominator (K), equity IRR method (L, M, N, O), final parity audit (P), Oborovo CFADS basis (Q). Phase 51F guardrails SHA-pin all parity-sensitive files.

**Audit Exports (Stacks R, S, V)**  
Factory configuration fidelity restored (R); debt service export columns reconciled with Excel headers (S); audit CSV completeness and formula source map (V).

**Tax Engine (Stack T)**  
SHL interest deductibility fix; H1 CIT settlement timing corrected. Tax architecture decision documented (T0).

**Canonical Formula Registry (Stack W)**  
51 financial formulas documented across 7 sections: equity IRR, project IRR, DSCR, SHL, LCF, depreciation, ATAD. Executable formula tests with numerical validation. Formula definitions are frozen.

**Engine Invariants (Stack X)**  
58 invariant tests across 9 classes: balance sheet closure, cash conservation, SHL conservation, tax non-negativity, distribution gates, DSCR monotonicity, LCF bounds, IRR bounds, period continuity. All 58 passing.

**Pilot Stabilization (Stack Y)**  
DS reconciliation, Workspace 500 guard, UI-path seeding for external pilot.

**Tax Depreciation Runtime (Stack Z)**  
`use_tax_bridge_engine=True` wired in TUHO factory. Tax bridge runtime applies existing bridge logic; no new computation. Parity maintained.

**Test Suite Census (Stack AA)**  
879 test files / 19,562 tests collected. Classified into 11 categories (core engine, parity/golden, phase development, browser/Playwright, UI component, integration, legacy/disabled). CI strategy documented in `docs/TEST_SUITE_RATIONALIZATION.md`.

**Identity Guard Audit (Stack AB)**  
27 identity guard occurrences inventoried. 3 duplicate runner-layer guards removed. 11 post-engine mutation blocks documented. AB finding: frozen DS fixture identity-dispatched on project code (tracked as highest-priority item; resolved in AC).

**Runtime Identity Elimination Phase 1 (Stack AC)**  
`FinancingParams.frozen_senior_ds_fixture_path` added. Frozen DS fixture loading now reads from config field, not `inputs.info.code`. Renaming TUHO or Oborovo no longer changes any financial output. Previously xfailed AB test now passes.

### Remaining (Deferred)

**Identity Cleanup — Phase 2 (Stack AD)**  
Core identity guards at `waterfall_core.py` lines 115/117/119 protect hardcoded tax bridge constants (`TUHO_BOOK_TOTAL=72,993.7`, `TUHO_TAX_TOTAL=70,691.5`). These cannot be removed without parameterizing the constants first. Tracked for Stack AD.

**Identity Cleanup — DA Wiring (Stack AE)**  
`is_tuho` / `is_oborovo` flags at lines 776/1274 drive Distribution Account wiring. Tracked for Stack AE once DA governance decision is taken.

**TUHO-named Flags (Stack AF)**  
`use_tuho_r99_input_engine`, `use_tuho_shl_repayment_alignment`, `tuho_cit_cash_tax_start_operating_index`, `tuho_shl_principal_eligibility_start_period` are capability flags with TUHO-specific names that should be renamed to generic equivalents. Tracked for Stack AF.

**Runtime Configuration Evolution**  
`WaterfallRunConfig` is capability-driven but still carries some fields that could be further genericised. No blocking issues identified; future evolution should follow the same config-not-identity principle established in AC.

**R99/R102 Distribution Account**  
Audit-only. Governance decision required before wiring to distribution gate.

**UI/UX Redesign**  
Spreadsheet-native UI (C-series branches). Not part of the financial engine baseline.

**SaaS Architecture**  
Multi-tenant, authentication, rate limiting, deployment. Separate concern from the engine.

**Security Hardening**  
Auth rate limiting exists (`app.auth._rate_limit_store`). Full security audit deferred.

---

## 4. Known Decisions

The following decisions have been made and are recorded as permanent engineering positions:

**Croatian 5-Year Loss Carryforward (Finco Correct; Excel Wrong)**  
Finco One implements the legally correct Croatian §16 LCF: 5-year rolling window, semiannual periods, `expire_before_use=True`. The Excel Golden Model uses perpetual LCF, which is legally incorrect. Finco intentionally does not replicate the Excel error. The resulting −5,271 kEUR residual in TUHO total tax is authentic and documented. This position must not be reversed.

**Golden Parity as Calibration Target, Not Bug Reproduction**  
Golden Parity (Phase 51F) calibrates financial outputs to the Excel Golden Model within defined tolerances. Where Excel is incorrect (e.g. perpetual LCF, certain timing conventions), Finco keeps the correct treatment, documents the known residual, and does not calibrate to the Excel mistake.

**Configuration Over Identity**  
Runtime engine behaviour must be controlled by capability flags in `ProjectInfo` and `FinancingParams`, not by project name, project code, or runtime seed. This principle was established during the Stack AB/AC work and applies to all future engine development.

**Financial Equations Are Frozen**  
The mathematical formulae used to compute IRR, DSCR, taxable income, LCF, SHL balance, distributions, and all other financial outputs are frozen at this baseline. No formula changes should occur without a formal architecture decision and new stack.

**Tax Bridge Constants Are Hardcoded (Intentionally Temporary)**  
`TUHO_BOOK_TOTAL=72,993.7 kEUR` and `TUHO_TAX_TOTAL=70,691.5 kEUR` are hardcoded in `waterfall_core.py`. This is a known architectural debt, not an oversight. Parameterization is tracked for Stack AD and requires a deliberate decision about where these values should live (e.g. `FinancingParams`, a separate depreciation schedule config, or an external fixture).

**AB xfail Test Converted to Passing (AC Fix Confirmed)**  
The Stack AB test `test_tuho_full_output_identical_after_rename_xfail` was a strict xfail documenting the identity dispatch finding. After Stack AC it was converted to `test_tuho_full_output_identical_after_rename` and passes. This confirms the fix is real, not masked.

---

## 5. Engineering Freeze

**No further financial engine development should occur from this baseline until the next architecture decision is ratified.**

Specifically, the following activities require a formal architecture decision before proceeding:

- Parameterizing tax bridge constants (Stack AD)
- Changing any financial formula (IRR, DSCR, tax, LCF, SHL, distributions)
- Wiring R99/R102 Distribution Account to the distribution gate
- Adding new project types or new capability flags to `ProjectInfo`/`FinancingParams`
- Modifying `WaterfallRunConfig` fields

Activities that do not require a formal decision before starting:
- Refactoring identity guards (Stack AD–AF) — these are routing changes, not formula changes
- Test additions or improvements
- UI/UX work (C-series branches) — separate concern
- Documentation

---

## 6. Recommended Next Phase

**Independent strategic architecture review (Fable)**

Before committing to any of the three evolutionary paths below, an independent review of the full Finco One codebase is recommended. The reviewer should have full access to:

- This baseline document
- `docs/STACK_AB_ENGINE_ARCHITECTURE_CLEANUP.md` (identity guard inventory)
- `docs/TEST_SUITE_RATIONALIZATION.md` (test census)
- `app/waterfall_core.py` (primary engine)
- `domain/inputs.py` (full configuration schema)

The review should recommend one of three paths:

### Path A — Continued Evolution
Continue the Stack AD, AE, AF programme. Parameterize tax bridge constants, rename TUHO-specific flags, eliminate remaining identity guards. Maintain the current architecture; improve incrementally. Lowest risk; highest continuity.

### Path B — Controlled v2 Extraction
Extract the financial engine into a standalone, dependency-free Python library. `waterfall_core.py` → `finco_engine` package. Retain Streamlit UI as a thin host. Enable independent versioning of the engine vs the UI. Medium complexity; cleanest separation.

### Path C — Full Rewrite
Re-implement from the domain model upward with a clean configuration schema, no identity dispatch anywhere, parameterized constants, and a proper multi-project architecture. Highest quality outcome; highest cost and risk.

**The choice between these paths is an architecture decision that should not be made unilaterally from within the implementation programme.** The Fable review exists for exactly this purpose.

---

## 7. Repository State at Freeze

| Item | Value |
|------|-------|
| Main HEAD SHA | `d3ca68d693635ff031f039054380fe8c32f3042b` |
| Total tests collected | 19,562 |
| Parity guardrail tests | 21 (Phase 51F) |
| Engine invariant tests | 58 (Stack X) |
| Canonical formula tests | 18 (Stack W) |
| Stack tests (Z + AB + AC) | 84 |
| Open PRs | 0 (all stacks merged) |
| Git tags | None |
| Parity guardrails | GREEN |
| CI (core-model-tests) | GREEN |
| Frozen DS identity dispatch | ELIMINATED (Stack AC) |
| Golden Parity targets | ALL PASS |

---

*This document is the permanent engineering reference for Finco One as of 2026-07-03. Future development begins from SHA `d3ca68d693635ff031f039054380fe8c32f3042b`.*
