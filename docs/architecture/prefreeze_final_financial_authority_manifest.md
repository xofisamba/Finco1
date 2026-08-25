# Pre-freeze Final Financial Authority Manifest

**Classification:** PHASE_A_FINANCIAL_AUTHORITY_FREEZE_COMPLETE
**PR:** PR-12
**Base SHA:** `101a50b93ca25a9b2dda93edee8bfc459e0c3b09` (PR-11 squash merge)
**Date:** 2026-08-25
**Scope:** Tests + Governance + Documentation. Production code unchanged.

---

## Authority Table (28 Concepts)

| # | Concept | Canonical Input Authority | Canonical Calculation Authority | Canonical Output Authority | Expected Axis | Permitted Downstream Consumers | Forbidden Alternative Authority | Freeze Status |
|---|---------|--------------------------|--------------------------------|---------------------------|---------------|-------------------------------|--------------------------------|---------------|
| 1 | **Project timeline / periods** | `OperatingModelInput.calendar` (→ `CalendarInput`) is the runtime axis input authority. `ProjectInfo.construction_months` is a persisted project-level field; it is NOT the axis runtime authority — it must not be consumed directly as a period source by the financial engine. | `PeriodEngine` in `finco_core.engine.period_engine` | `CanonicalAxisContract` (full_axis, operating_axis, senior_axis) | full_axis | `run_operating_model`, `run_tax_cfads_model`, `run_senior_debt_model`, all downstream orchestrators | `ProjectInfo.construction_months` used directly as period source in financial engine; any self-derived axis from solver output | `FROZEN_CLEAN_AUTHORITY` |
| 2 | **Revenue** | `OperatingModelInput.revenue` (→ `RevenueInput`) | `finco_core.revenue.generation.full_revenue_schedule` | `OperatingSchedules.revenue_keur` | full_axis | EBITDA calculation, CFADS derivation, tax base | Workbook-sourced revenue vectors; project-name-dispatched revenue schedules | `FROZEN_CLEAN_AUTHORITY` |
| 3 | **OPEX** | `OperatingModelInput.opex` (→ `OpexInput`) | `finco_core.opex.projections.opex_schedule_period` | `OperatingSchedules.opex_keur` | full_axis | EBITDA calculation | Workbook-derived OPEX vectors; project-name dispatch | `FROZEN_CLEAN_AUTHORITY` |
| 4 | **EBITDA** | `OperatingSchedules.{revenue_keur, opex_keur}` | `finco_core.ebitda.calculate_ebitda_keur` (signed: revenue − opex) | `OperatingSchedules.ebitda_keur` | full_axis | Tax base, canonical CFADS, DSCR sizing | Unsigned EBITDA; workbook EBITDA; any inline formula duplicating this calculation | `FROZEN_CLEAN_AUTHORITY` |
| 5 | **Construction uses** | `OperatingModelInput.depreciation` capex items; `ConstructionFinancingInput.capex_items` (when enabled) | `finco_core.construction.stage_b2.run_stage_b2` (when enabled); `_project_uses` in `financial_engine.financing.project` | `ProjectFinancingResult.uses` / `ConstructionFinancingResult` | Construction periods only | IDC calculation, gearing capacity, funding sources | Workbook capex schedules; project-level `CapexStructure` used directly as construction draw authority | `FROZEN_CLEAN_AUTHORITY` |
| 6 | **Construction equity / SHL / Senior funding** | `FinancingParams.{gearing_ratio, sponsor_funding_mode, clean_shl_principal_keur}` | `financial_engine.financing.project.run_project_financing_model` — derives funding split from total project uses × gearing | `ProjectFinancingResult.{senior_keur, shl_keur, equity_keur}` | Construction periods | IDC base, opening SHL balance, opening Senior balance | Fixed hardcoded funding amounts from workbook; any project-name-dispatched funding split | `FROZEN_CLEAN_AUTHORITY` |
| 7 | **IDC / Senior construction interest** | `ConstructionFinancingInput.senior_pricing` (flat_all_in_rate / EXPLICIT_ALL_IN_SCHEDULE / HEDGE_BLEND) | `finco_core.construction.stage_b2.run_stage_b2` outer IDC fixed point in `_run_with_construction_idc` | `ConstructionFinancingResult.capitalized_financing_costs.senior_idc_keur` | Construction periods | Total construction uses (IDC is added to uses), gearing, total capex for depreciation | Workbook IDC schedules; project-name-dispatched IDC rates | `FROZEN_CLEAN_AUTHORITY` |
| 8 | **SHL construction interest** | `FinancingParams.shl_construction_day_count_fraction` + `shl_rate` | `financial_engine.shl.construction` (SHL construction PIK) | `ShareholderLoanSchedules.shl_pik_interest_keur` for construction periods | Construction periods | Opening SHL operating balance | Any workbook SHL construction schedule | `FROZEN_CLEAN_AUTHORITY` |
| 9 | **Book depreciation** | `OperatingModelInput.depreciation.book_capex_items_for_depreciation` | `finco_core.debt.depreciation_schedule.build_depreciation_schedule + depreciation_per_period` | `OperatingSchedules.book_depreciation_keur` | full_axis | EBIT (EBITDA − book_dep), financial statements (Phase C) | Workbook depreciation vectors; project-name-dispatched useful-life tables | `FROZEN_CLEAN_AUTHORITY` |
| 10 | **Tax depreciation** | `OperatingModelInput.depreciation.tax_capex_items_for_depreciation` | Same leaf as book dep; currently identical to book in Phase 2A | `OperatingSchedules.tax_depreciation_keur` | full_axis | Taxable income calculation | Workbook tax depreciation; separate tax-vs-book dispatch currently unsupported | `FROZEN_CLEAN_AUTHORITY` |
| 11 | **Country tax policy** | `TaxCalculationInput.policy` (→ `TaxPolicy`) typed at input boundary; country isolation via `TaxParams` on `ProjectInputs` | `financial_engine.tax.engine.calculate_tax` | `TaxCalculationResult` (annual + period results) | full_axis (periods), per-tax-year for annual | CFADS (via cash_tax), taxable income, LCF ledger | Raw country-rate float injected without `TaxPolicy` wrapper; project-name tax dispatch | `FROZEN_CLEAN_AUTHORITY` |
| 12 | **Opening tax-loss vintages** | `TaxCalculationInput.opening_loss_vintages` (typed vintage tuples with `origin_tax_year`, `lcf_years`) | `financial_engine.tax.loss_ledger.run_annual_fifo_ledger` | `TaxCalculationResult.annual_results[*].{loss_opening_keur, loss_closing_keur, loss_used_keur}` | Per tax year | Taxable income after LCF | Workbook LCF opening balances injected as raw floats | `FROZEN_CLEAN_AUTHORITY` |
| 13 | **SHL interest deductibility** | `TaxPolicy.{shl_interest_tax_treatment_enabled, shl_interest_deductibility, shl_interest_deductible_pct}` and ATAD fields | `financial_engine.tax.engine.calculate_tax` (ShlInterestDeductibilityMode → deductible/disallowed split) | `TaxCalculationResult.annual_results[*].{deductible_interest_keur, disallowed_interest_keur}` | Per tax year | Base tax, Bank tax (via merged contract), CFADS | Any direct modification of SHL deductibility outside `TaxPolicy`; thin-cap mechanism (NOT implemented → `FAIL_CLOSED_UNSUPPORTED`) | `FROZEN_CLEAN_AUTHORITY` for FULLY_DEDUCTIBLE / FULLY_NON_DEDUCTIBLE / ATAD_STL path; thin-cap → `FAIL_CLOSED_UNSUPPORTED` |
| 14 | **FinancingInterestContract** | Produced by B5 fixed-point at convergence only | `financial_engine.orchestrator._run_senior_debt_model_with_shl` (convergence check with `_require_final_financing_contract`) | `FinancingInterestContract` (period_indices, senior_interest_keur, shl_gross_interest_keur, is_final=True, content_fingerprint) | full_axis (all model periods) | Base tax merge, Bank tax merge, final authority checks | Stale provisional contracts (is_final=False); any provisional contract that bypasses `_require_final_financing_contract` | `FROZEN_CLEAN_AUTHORITY` |
| 15 | **Base tax** | `TaxCalculationInput` (with final Senior + SHL interest from `FinancingInterestContract`) | `financial_engine.tax.engine.calculate_tax` (Base case: Base operating periods) | `TaxAndCfadsSchedules.{taxable_profit_keur, tax_keur, corporate_tax_cash_keur}` | full_axis | Base CFADS, Base DSCR, post-senior cash | Any replay of workbook tax output; `expected_delta` / `approved_delta` adjustments | `FROZEN_CLEAN_AUTHORITY` |
| 16 | **Base CFADS** | `TaxAndCfadsSchedules.{ebitda_keur, corporate_tax_cash_keur}` | `financial_engine.cfads.calculate_canonical_cfads` (Base EBITDA − Base cash tax) | `TaxAndCfadsSchedules.cfads_keur` | full_axis | Base DSCR numerator, post-senior cash, SHL available cash | Bank CFADS used as Base CFADS; any plug or balancing residual | `FROZEN_CLEAN_AUTHORITY` |
| 17 | **Bank tax** | `TaxCalculationInput` (Bank operating periods + Bank SHL/Senior interest via merged contract) | `financial_engine.tax.engine.calculate_tax` (Bank case: bank_phase2a_result.periods) | `DebtSizingSchedules.bank_cash_tax_keur` | Bank full_axis | Bank CFADS, DSCR sizing | Base tax reused as Bank tax; workbook bank tax schedule | `FROZEN_CLEAN_AUTHORITY` |
| 18 | **Bank CFADS** | `DebtSizingSchedules.{bank_ebitda_keur, bank_cash_tax_keur}` | `financial_engine.cfads.calculate_canonical_cfads` (Bank EBITDA − Bank cash tax) | `DebtSizingSchedules.bank_cfads_keur` | Bank full_axis | Senior DSCR constraint (sizing numerator) | Base CFADS used as sizing numerator; workbook bank CFADS | `FROZEN_CLEAN_AUTHORITY` |
| 19 | **Senior debt sizing** | `SeniorDebtPolicy` (sizing_mode, target_dscr, maximum_gearing) + `SeniorDebtInputs` (eligible_project_cost_keur) | `financial_engine.senior_debt.solver.solve_senior_debt` (DSCR-sculpted fixed point or gearing-limited) | `SeniorDebtSchedules.debt_size_keur` | senior_axis | Debt service schedule, DSCR, post-senior cash | Any gearing plug or virtual Senior insertion; workbook debt size | `FROZEN_CLEAN_AUTHORITY` |
| 20 | **Senior interest** | `SeniorDebtPolicy.annual_fixed_rate` or `SeniorDebtInputs.period_rates` | `financial_engine.senior_debt.solver.solve_senior_debt` (interest = opening_balance × period_rate) | `SeniorDebtSchedules.senior_interest_keur` | senior_axis | FinancingInterestContract, merged tax input, post-senior cash | Workbook Senior interest; any hardcoded interest schedule | `FROZEN_CLEAN_AUTHORITY` |
| 21 | **Senior principal / debt service** | Solver output after convergence | `solve_senior_debt` (DSCR-sculpted annuity or explicit schedule) | `SeniorDebtSchedules.{senior_principal_keur, senior_debt_service_keur}` | senior_axis | Post-senior cash, DSCR | Any workbook-sourced principal schedule; terminal top-up balloon | `FROZEN_CLEAN_AUTHORITY` |
| 22 | **DSCR** | Bank CFADS (sizing); Base CFADS (actual) | `solve_senior_debt` computes sizing DSCR internally; Base actual DSCR = Base CFADS / Senior DS at result layer | `SeniorDebtSchedules.base_dscr`; `DebtSizingSchedules.bank_sizing_dscr` | senior_axis | Binding constraint detection, covenant gate | Bank DSCR used as Base actual DSCR; any DSCR recomputed outside these two authorities | `FROZEN_CLEAN_AUTHORITY` |
| 23 | **Post-senior cash** | `PostSeniorCashSchedules.{base_cfads_keur, senior_debt_service_keur}` | `financial_engine.orchestrator._assemble_post_senior_cash_schedules` (Base CFADS − Senior DS, zero for construction) | `PostSeniorCashSchedules.cash_after_senior_before_reserves_keur` | full_axis | SHL available cash, distribution gate | Workbook post-senior cash; any pre-computed residual | `FROZEN_CLEAN_AUTHORITY` |
| 24 | **SHL operating interest** | `ShareholderLoanSchedules.shl_gross_interest_keur` (from B5 converged state) | `financial_engine.shl.production.compute_shareholder_loan_schedules` | `ShareholderLoanSchedules.shl_gross_interest_keur` | full_axis (SHL active periods) | FinancingInterestContract (shl_gross_interest_keur component), Bank tax merge | Workbook SHL interest schedule; any frozen historical SHL interest vector | `FROZEN_CLEAN_AUTHORITY` |
| 25 | **SHL principal repayment** | `ShlRepaymentPolicy` (BULLET / CASH_SWEEP / EXPLICIT_SCHEDULE) | `financial_engine.shl.production.compute_shareholder_loan_schedules` | `ShareholderLoanSchedules.shl_principal_keur` | full_axis (SHL active periods) | SHL closing balance, post-SHL cash | Any workbook SHL principal schedule; virtual SHL | `FROZEN_CLEAN_AUTHORITY` |
| 26 | **Reserve / distribution-gate inputs currently supported** | `CovenantGatePolicy` (lockup_dscr, lockup_llcr); DSRA inputs (dsra_months via `FinancingParams`) | `financial_engine.shareholder_waterfall.model` (covenant gate) | `ShareholderWaterfallResult.{cash_available_for_distribution_keur, locked_up_keur}` | full_axis operating subset | Shareholder waterfall, sponsor cash | DSRA not fully modelled in Phase 2C — pre-reserve label on post-senior cash is mandatory | `PHASE_C_OUTPUT_COMPLETENESS_PENDING` — DSRA ordering unresolved; distributable cash label blocked |
| 27 | **Shareholder waterfall** | `PostSeniorCashSchedules` + `ShareholderLoanSchedules` + covenant gate | `financial_engine.shareholder_waterfall.model.run_project_shareholder_waterfall_model` | `ShareholderWaterfallResult` | full_axis operating subset | Sponsor cash / returns | Any legacy `run_waterfall_v3_core` or `run_waterfall` invocation for promoted projects | `FROZEN_CLEAN_AUTHORITY` (Generic Solar/Wind promoted); TUHO/Oborovo → `PHASE_B_PRODUCTION_CUTOVER_PENDING` |
| 28 | **Sponsor cash / returns currently supported** | `ShareholderWaterfallResult.{distributions_keur, sponsor_cash_flows}` | `financial_engine.shareholder_waterfall.model` | `ProjectModelKPIs.{total_distributions_keur}` | full_axis operating subset | UI / export (Phase later) | IRR / NPV / LLCR via clean engine (NOT YET IMPLEMENTED → `PHASE_C_OUTPUT_COMPLETENESS_PENDING`) | `PHASE_C_OUTPUT_COMPLETENESS_PENDING` — IRR, NPV, LLCR not yet computed by clean engine |

---

## One-Authority Causal Graph

```
CalendarInput ──────────────────────────────────────────────────────────────────┐
                                                                                 │
                     ┌── PeriodEngine ──→ CanonicalAxisContract ────────────────┼─────────┐
                     │   (full_axis, operating_axis, senior_axis)                │         │
TechnicalInput ──────┤                                                           │         │
RevenueInput   ──────┼── full_revenue_schedule ──→ revenue_keur ────────────────┤         │
                     │                                                           │         │
OpexInput ───────────┼── opex_schedule_period ──→ opex_keur ────────────────────┤         │
                     │                                                           │         │
                     └── calculate_ebitda_keur (revenue − opex) ──→ ebitda_keur ┤         │
                                                                                 │         │
DepreciationInput ──────── build_depreciation_schedule ──→ tax_dep_keur ────────┤         │
                                                                                 │         │
TaxPolicy        ──────┐                                                         │         │
OpeningLossVintages ───┤                                                         │         │
ShlInterestFromB5 ─────┴── calculate_tax ──→ {taxable_income,                   │         │
SeniorInterestFromB5 ──┘                      cash_tax_keur} ───────────────────┤         │
                                                                                 │         │
                     ┌── calculate_canonical_cfads (EBITDA − cash_tax) ─────────┤         │
                     │   → cfads_keur (Base & Bank paths)                       │         │
SeniorDebtPolicy ────┤                                                           │         │
SeniorDebtInputs ────┤                                                           │         │
                     └── solve_senior_debt ──→ {debt_size, interest,            │         │
                                               principal, DS} ──────────────────┘         │
                                                                                           │
                         FinancingInterestContract (final, is_final=True) ────────────────┘
                         (senior_interest + shl_gross_interest; fingerprint verified)

PostSeniorCash = Base CFADS − Senior DS     [_assemble_post_senior_cash_schedules]
SHL schedules  = compute_shareholder_loan_schedules   [B5 fixed point]
Waterfall      = run_project_shareholder_waterfall_model
```

---

## Phase B / C / D Gap Register

### Phase B — Production Cutover Pending

| Item | Reason | Status |
|------|--------|--------|
| TUHO production routing | Legacy waterfall still active; reason_code=`PR8_BLOCKED_BY_TYPED_TUHO_TAX_RUNTIME_GAP` | `PHASE_B_PRODUCTION_CUTOVER_PENDING` |
| Oborovo production routing | Legacy waterfall still active; reason_code=`PR8_G2A_FINANCING_CONTRACT_FIELDS_NOT_TYPED` | `PHASE_B_PRODUCTION_CUTOVER_PENDING` |
| Thin-cap SHL limitation mechanism | `SHL_THIN_CAP_RUNTIME_NOT_IMPLEMENTED` raised by TaxPolicy when thin_cap_enabled=True | `FAIL_CLOSED_UNSUPPORTED` — NOT to be promoted in PR-12 |
| Legacy fixture/report runtime authority | workbook-derived vectors in legacy engine paths; removal blocked on TUHO/Oborovo cutover | `PHASE_B_REMOVAL_PENDING` |

### Phase C — Output Completeness Pending

| Item | Reason | Status |
|------|--------|--------|
| DSRA full modelling | Ordering unresolved; post-senior cash is labelled pre-reserve | `PHASE_C_OUTPUT_COMPLETENESS_PENDING` |
| IRR (project + equity) | Not computed by clean engine; manifest as `None` in KPI output | `PHASE_C_OUTPUT_COMPLETENESS_PENDING` |
| NPV | Not computed by clean engine | `PHASE_C_OUTPUT_COMPLETENESS_PENDING` |
| LLCR | Not computed by clean engine | `PHASE_C_OUTPUT_COMPLETENESS_PENDING` |
| Financial statements (P&L, Balance Sheet, Cash Flow) | `financial_statements` section declared unavailable | `PHASE_C_OUTPUT_COMPLETENESS_PENDING` |

### Phase D — Later Phases

| Item | Status |
|------|--------|
| KUPI production clean path | `PHASE_D_PENDING` |

### Phase E — Product / UI

| Item | Status |
|------|--------|
| Product / UI / browser / export layer | `PHASE_E_PENDING` — not in scope for Phase A/B/C/D |

### Phase F — Pilot

| Item | Status |
|------|--------|
| Pilot / partner onboarding | `PHASE_F_PENDING` — not in scope for Phase A/B/C/D/E |

---

## Freeze Status Summary

| Status | Count | Concepts |
|--------|-------|---------|
| `FROZEN_CLEAN_AUTHORITY` | 24 | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13(partial), 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27(Generic Solar/Wind) |
| `FAIL_CLOSED_UNSUPPORTED` | 1 | 13 (thin-cap path) |
| `PHASE_B_PRODUCTION_CUTOVER_PENDING` | 1 | 27 (TUHO/Oborovo routes) |
| `PHASE_C_OUTPUT_COMPLETENESS_PENDING` | 2 | 26, 28 |

---

## Governance Assertions

- **No parallel authority:** each of the 28 concepts has exactly one canonical calculation authority.
- **No project-name dispatch:** the clean engine contains no `if project.name == ...` or `if project.code == ...` financial dispatch.
- **No workbook runtime:** the clean engine path reads zero XLSM/XLSX files, zero `tests/fixtures/*.csv`, zero `reports/*.csv` at runtime.
- **No balancing plug:** no `approved_delta`, `expected_delta`, or residual insertion.
- **No virtual Senior:** no `terminal_top_up`, `virtual_debt`, or `tolerance_as_capacity` pattern.
- **FinancingInterestContract fingerprint:** content_fingerprint = `hash((period_indices, senior_interest_keur, shl_gross_interest_keur))` — memory-address-independent.
- **`financial_engine/tax/engine.py` unchanged** in PR-12 (tests + governance + docs only).

---

## Phase B Progress

### Phase B1 — Clean-Only Production Router (phaseb1-clean-only-production-router)

**Status:** PHASE_B1_CLEAN_ONLY_PRODUCTION_ROUTER_COMPLETE_CANDIDATE
**Base SHA:** `99cc51a90e98b4869d168e78aeb736861240f8a2` (PR-12 squash merge)
**PR:** #958 (OPEN, DRAFT — do not merge until independently gated)
**Date:** 2026-08-25

**Routing change (Correction B final):**
- BEFORE: non-promoted / unknown / Portfolio production run → silent legacy fallthrough
- AFTER: ALL non-promoted / unclassified / unknown types → `CleanNotReadyError` (typed, calculation_count=0)

**Production run authority table:**

| Entry point | Project type | Outcome |
|---|---|---|
| `run_project()` | Solar / Wind (promoted) | CLEAN_SUCCESS (clean G2C, clean_calls=1, legacy_calls=0) |
| `run_project()` | Oborovo / TUHO (blocked) | CleanNotReadyError (calculation_count=0) |
| `run_project()` | Unknown / Portfolio / unclassified | CleanNotReadyError (calculation_count=0) |
| `execute_production_waterfall()` | Solar / Wind | CLEAN_SUCCESS |
| `execute_production_waterfall()` | Oborovo / TUHO / unknown | CleanNotReadyError |
| `execute_production_demo()` | Solar / Wind | Clean G2C DemoResult |
| `execute_production_demo()` | Oborovo / TUHO / unknown | CleanNotReadyError |
| `run_project_legacy()` | Any | LEGACY_CALIBRATION_ONLY (explicit seam, force_legacy=True) |
| `execute_calibration_waterfall()` | Non-promoted only | LEGACY_CALIBRATION_ONLY (explicit seam) |

**`allow_legacy` parameter:** REMOVED from `execute_production_waterfall`. No production surface carries a legacy fallthrough parameter.

**Portfolio reachability:** REST API returns HTTP 501 for Portfolio at router layer (`app/api/router.py`). `run_project("Portfolio")` raises `CleanNotReadyError` (B1 test T1 enforces this). `execute_production_demo("Portfolio")` raises `CleanNotReadyError` (B1 test T2 enforces this). `portfolio_runner` / `portfolio_orchestrator` are LEGACY_EXPERIMENTAL / OFFLINE_ONLY. Caller inventory (independently inspected for B1 classification, not enforced by B1 tests): no direct import of `portfolio_runner` or `portfolio_orchestrator` found in `app/api/project_runner.py` or `app/services/production_waterfall_seam.py`; `main_web.py` reaches Portfolio only via `run_project()` which fails closed.

**Financial delta:** ZERO. FINANCIAL_FORMULA_CHANGE = ZERO. CORE_ROUTING_FINANCIAL_FINGERPRINTS_UNCHANGED (Solar/Wind KPI fingerprints match frozen PR-F1 values; py3.12 CI authority).

**B1 test suite:** 62 passed, 1 skipped on Python 3.12 (in `tests/test_phaseb1_clean_only_production_router.py`)

**Remaining Phase B work:**
- B2: Promote Oborovo — key promotion gaps include: `sponsor_funding_mode`, `gearing_basis_mode`, frozen Senior schedule removal/replacement, typed construction financing / source-evidence promotion. (Country Tax Template alone is NOT the primary prerequisite.)
- B3: Promote TUHO — key gaps include: clean cash-tax timing gap, thin-cap enabled (`FAIL_CLOSED_UNSUPPORTED`), ATAD / `SUBJECT_TO_LIMITATIONS` capability, financing / SHL / construction typed-input gaps. (Typed financing fields alone are insufficient.)

**Concept 27 status update:** TUHO/Oborovo routes now `PHASE_B2_B3_PROMOTION_PENDING` (B1 fail-closed enforced; legacy only via explicit calibration entry points `run_project_legacy` / `execute_calibration_waterfall`).
