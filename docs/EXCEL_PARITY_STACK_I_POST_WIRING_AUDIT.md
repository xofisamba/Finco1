# Excel Parity Stack I — Post-Wiring Calibration Audit

**Audit date:** 2026-07-01  
**Branch:** `excel-parity-stack-i-post-wiring-audit`  
**Auditor:** Claude Code (automated static analysis)

---

## 1. Runtime Payload Inventory

The following table documents every key in the dict returned by `run_project()` in
`app/api/project_runner.py`, its source object, serializer function, the sessionStorage
key written by `run_service.py`, and the UI tab that reads it.

| Key | Source Object | Serializer | sessionStorage Key | UI Tab |
|-----|--------------|------------|--------------------|--------|
| `financial_statements` | `FinancialStatementsResult` (from `assemble_financial_statements()`) | `_serialize_financial_statements()` | `lastFinancialStatements` | Financial Statements (`sheet_financials.html`) |
| `debt_schedule` | `WaterfallResult.periods` | `_serialize_debt_schedule()` | `lastDebtSchedule` | Senior Debt (`sheet_senior_debt.html`) |
| `tax_schedule` | `WaterfallResult.periods` | `_serialize_tax_schedule()` | `lastTaxSchedule` | Tax (`sheet_tax.html`) |
| `distribution_schedule` | `WaterfallResult.periods` | `_serialize_distribution_schedule()` | `lastDistributionSchedule` | Distributions (`_sheet_distributions_partial.html`) |
| `sponsor_schedule` | `SponsorCashflowResult` + `SponsorIrrResult` + `SponsorMoicResult` | `_serialize_sponsor_schedule()` | `lastSponsorSchedule` | Sponsor/Equity (`_sheet_sponsor_partial.html`) |
| `kpis` | `WaterfallResult` + `ProjectInputs.capex` | inline dict | `lastRuntimeSummary` (via `runtime_summary_to_dict`) | Runtime block (all tabs) |
| `tables` | `WaterfallResult` via `build_*_table()` | pandas `to_dict(orient="records")` | — (not persisted to sessionStorage) | Waterfall/Revenue/Debt/Returns tables |
| `project_type` | form param | — | — | metadata |
| `scenario` | form param | — | — | metadata |
| `period_view` | form param | — | — | metadata |
| `integration_status` | `demo.integration_status` | — | — | metadata |
| `integration_note` | `demo.integration_note` | — | — | metadata |
| `messages` | `demo.messages` | — | — | UI message bar |
| `dualrun_validation` | `WaterfallResult._dualrun_validation` | — | — | dev/audit |
| `derivation_evidence` | `WaterfallResult.periods` + `ProjectInputs` | `_build_runtime_derivation_evidence()` | — | derivation audit panel |

---

## 2. TUHO Parity Status

| Module | Status | Notes |
|--------|--------|-------|
| Financial Statements (P&L, BS, PF CF Waterfall) | **PASS** | Phase D1 wired. `assemble_financial_statements()` called after waterfall; serialized to `lastFinancialStatements`; `sheet_financials.html` reads from sessionStorage. |
| Senior Debt Schedule | **PASS** | Phase E2/E5 wired. `_serialize_debt_schedule()` serializes per-period fields; `sheet_senior_debt.html` reads from `lastDebtSchedule`. |
| Tax Schedule | **PASS** | Phase F2 wired. `_serialize_tax_schedule()` serializes tax audit fields; `sheet_tax.html` reads from `lastTaxSchedule`. |
| Distribution Schedule | **PASS** | Phase G1 wired. `_serialize_distribution_schedule()` serializes distribution fields; `_sheet_distributions_partial.html` reads from `lastDistributionSchedule`. |
| Sponsor/Equity Schedule (gross level) | **PASS** | Phase H2/H3 wired. `_run_sponsor_engine()` → `_serialize_sponsor_schedule()` → `lastSponsorSchedule`. Gross IRR and gross MOIC displayed. |
| Sponsor LP/GP waterfall allocation | **GAP** | Allocated returns (LP net IRR, GP net IRR, promote) not computed or displayed. |
| Sponsor preferred return / promote | **GAP** | Hurdle rate and promote share are configured in `_SPONSOR_CAPITAL_STRUCTURES` but net IRR/MOIC after waterfall split is not wired to UI. |
| WHT (Withholding Tax) | **GAP** | `wht_rate` hard-coded to `0.0` in `_run_sponsor_engine()`. No UI input for WHT rate. |

---

## 3. Oborovo Parity Status

| Module | Status | Notes |
|--------|--------|-------|
| Financial Statements | **PASS** | Same wiring as TUHO (project-type-agnostic). |
| Senior Debt Schedule | **PASS** | Same wiring as TUHO. |
| Tax Schedule | **PASS** | Same wiring as TUHO. |
| Distribution Schedule | **PASS** | Same wiring as TUHO. |
| Sponsor Schedule (gross) | **PASS** | `_SPONSOR_CAPITAL_STRUCTURES` includes "Oborovo" entry with same LP/GP split. |
| Sponsor LP/GP allocation | **GAP** | Same as TUHO — net waterfall split not wired. |
| WHT rate | **GAP** | Same as TUHO — hard-coded `0.0`. |

---

## 4. UI Consistency Status

### sessionStorage Key → Template Mapping (verified)

| sessionStorage Key | Template | Verified |
|-------------------|----------|---------|
| `lastFinancialStatements` | `sheet_financials.html` | ✓ `sessionStorage.getItem("lastFinancialStatements")` present |
| `lastDebtSchedule` | `sheet_senior_debt.html` | ✓ `sessionStorage.getItem("lastDebtSchedule")` present |
| `lastTaxSchedule` | `sheet_tax.html` | ✓ `sessionStorage.getItem("lastTaxSchedule")` present |
| `lastDistributionSchedule` | `_sheet_distributions_partial.html` | ✓ `sessionStorage.getItem("lastDistributionSchedule")` present |
| `lastSponsorSchedule` | `_sheet_sponsor_partial.html` | ✓ `sessionStorage.getItem("lastSponsorSchedule")` present |

### Field Name Mismatches Between Serializer Output and Template JS

No mismatches found. Template JS accesses field names that match serializer dict keys.

**Notable items:**
- `_sheet_sponsor_partial.html` reads `s.gross_sponsor_irr` and `s.gross_sponsor_moic` — these match `_serialize_sponsor_schedule()` summary keys.
- Templates apply display formatting (`* 100` to convert decimal IRR to percent, `.toFixed(2)`) in JS — these are **not** financial model calculations, they are display-only transformations. The `test_i4` characterization test verifies this pattern.
- `sheet_senior_debt.html` Jinja `{{ "%.2f"|format(project_ctx.interest_rate_pct * 100) }}` — server-side Jinja formatting, not client-side calculation.

### Guardrail Import State

| File | Clean (no app/ imports) | Notes |
|------|------------------------|-------|
| `app/project_factories.py` | **YES** | Fully clean |
| `app/waterfall_core.py` | **NO (known gap)** | Has lazy `from app.opex_engine` and `from app.capex_engine` conditional imports |
| `app/input_adapter.py` | **NO (known gap)** | Has `from app.input_schema` import; lazy `from app.project_factories` |

---

## 5. Remaining Gaps (Prioritized)

| Priority | Gap | Location | Impact |
|----------|-----|----------|--------|
| P1 | **Sponsor LP/GP waterfall allocation not wired** | `_run_sponsor_engine()` in `project_runner.py` | LP net IRR, GP net IRR, and GP promote are not computed or displayed. The Sponsor sheet shows only aggregated gross-level metrics, not the economics by investor tranche. |
| P2 | **Sponsor preferred return / promote not exposed in UI** | `_SPONSOR_CAPITAL_STRUCTURES` has `hurdle_rate_pa` and `gp_promote_share` but no UI input or output display | Users cannot see or configure the LP/GP hurdle rate or promote waterfall split from the UI. |
| P3 | **Sponsor net IRR / net MOIC placeholder** | `_serialize_sponsor_schedule()` / `_sheet_sponsor_partial.html` | Gross IRR/MOIC shown; net (after-promote, after-WHT) figures not computed or displayed. Excel parity requires net IRR for LP and GP separately. |
| P4 | **WHT rate hard-coded to 0.0** | `_run_sponsor_engine()` line: `wht_rate=0.0` | No withholding tax applied to distributions. Non-zero WHT scenarios (common in cross-border structures) produce incorrect sponsor cashflows. |
| P5 | **`waterfall_core.py` / `input_adapter.py` import from app/** | `app/waterfall_core.py` (lazy imports of `opex_engine`, `capex_engine`); `app/input_adapter.py` (`input_schema`, `project_factories`) | Violates domain separation. Prevents the domain layer from being used independently of the app layer (e.g. in standalone tests or a future API refactor). |
| P6 | **`test_phase24g3_capex_sheet_readability.py` has syntax error** | `tests/test_phase24g3_capex_sheet_readability.py` line 392 | SyntaxError (f-string with backslash, Python 3.11 restriction) prevents entire test collection; all tests fail with collection error. |

---

## 6. Recommended Next 3 PRs

### PR-NEXT-1: Sponsor LP/GP Waterfall Split (Excel Parity Stack I — Close-Out)

**Scope:** Wire LP vs. GP distribution split through the sponsor engine.

- Extend `_run_sponsor_engine()` to run separate cashflow calculations for LP-1 and GP-1 (using ownership ratios in `_SPONSOR_CAPITAL_STRUCTURES`).
- Extend `_serialize_sponsor_schedule()` to include per-investor summary (LP net IRR, GP net IRR, GP promote amount).
- Update `_sheet_sponsor_partial.html` to display LP/GP split in the summary bar.
- Add characterization test verifying LP/GP keys in serializer output.

**Why first:** Closes the most visible Excel parity gap — a financial model must show investor-level returns, not just SPV-level gross metrics.

---

### PR-NEXT-2: WHT Rate Input + Sponsor Net IRR/MOIC

**Scope:** Make WHT rate configurable and compute net-of-WHT sponsor metrics.

- Add `wht_rate` to the project inputs schema and workspace snapshot.
- Thread WHT rate from form/snapshot into `_run_sponsor_engine()` instead of hard-coding `0.0`.
- Extend `_serialize_sponsor_schedule()` with `net_sponsor_irr` and `net_sponsor_moic` (gross minus WHT impact).
- Update `_sheet_sponsor_partial.html` to display net IRR/MOIC alongside gross.

**Why second:** Completes sponsor parity for international projects. Many real deals have non-zero WHT (5–15%), so hard-coding 0.0 makes the sponsor schedule incorrect for typical use cases.

---

### PR-NEXT-3: Domain Separation — Remove app/ Imports from waterfall_core.py and input_adapter.py

**Scope:** Clean up guardrail violations to enforce strict domain/app separation.

- In `app/waterfall_core.py`: extract the lazy `from app.opex_engine` / `from app.capex_engine` imports into proper dependency injection (pass callables or pre-computed values from the caller in `project_runner.py`).
- In `app/input_adapter.py`: move `from app.input_schema` import to a seam interface; pass `ProjectInputsSchema` as a parameter rather than importing the class inside `input_adapter`.
- Fix `tests/test_phase24g3_capex_sheet_readability.py` syntax error (use `\"` inside f-strings for Python 3.11 compatibility).
- Update `test_i5_guardrail_files_app_import_state` to mark all three files as clean.

**Why third:** Establishes the clean domain boundary required for isolated engine testing and future API extraction. Guardrail tests already document the current violation; this PR resolves it.

---

## Appendix: Test Suite Status at Audit Time

| Suite | Result |
|-------|--------|
| `tests/test_excel_parity_stack_i.py` (new) | **16 passed** |
| `tests/test_phase51f_parallel_work_guardrails.py` | **21 passed** |
| Full `tests/` suite | **Collection error** — `test_phase24g3_capex_sheet_readability.py` SyntaxError (Python 3.11 f-string backslash restriction) prevents collection. All other test files skipped/passed when that file is excluded. |
