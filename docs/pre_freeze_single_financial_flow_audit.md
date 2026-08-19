# Pre-Freeze Single Financial Flow Audit
## Finco1 — August 2026

**Base `main` SHA after #942 merge:** `a53cc28a8bb6ab7eb68b47831676d971583cc2a4`
**Audit branch:** `prefreeze-single-financial-flow-audit`
**Production files changed:** NO — audit/diagnostic document only.

---

## 1. Executive Summary

**Single-engine verdict: NO — MULTIPLE MATERIAL FINANCIAL FLOWS**

Runtime-instrumented proof (see §3-A) confirms TUHO and Oborovo exclusively execute
the `LEGACY_APP_PRODUCTION_FLOW` and never enter the clean-engine orchestrator. The
clean engine (`CLEAN_PRE_PROMOTION_FINANCIAL_FLOW`) is a fully independent financial
authority — computing EBITDA, tax, CFADS, Senior debt, SHL and sponsor waterfall
through different owners and different formulas. These two flows are not one core with
parallel wiring; they are two materially distinct financial engines serving different
project populations. Promotion of the clean engine to production requires eliminating
all duplicate financial authority before go-live.

Three findings dominate:

**Finding 1 (P0): Two completely separate financial engines exist in parallel.** The production app (API + Streamlit) runs TUHO and Oborovo exclusively through the **legacy engine** (`app.waterfall_core.run_waterfall_v3_core` → `domain.waterfall.waterfall_engine.run_waterfall`). The **clean engine** (`financial_engine/orchestrator.py::run_operating_model / run_tax_cfads_model / run_senior_debt_model / run_project_financing_model`) is called only by parity scripts (`finco_parity/`), reconciliation scripts (`finco_recon/`), and tests. KUPI does not exist in the production app — it exists only in `tests/diagnostics/kupi_k0_k3_causal_grid.py` and its companion test, where it calls the clean engine exclusively.

**Finding 2 (P0 — `MISSING_ADAPTER_PROPAGATION`): `tax_loss_utilisation_gate` is NOT forwarded by the clean engine's tax adapter.** This is NOT a missing tax engine implementation — `calculate_tax()` in `financial_engine/tax/engine.py` already handles `EBT_POSITIVE` correctly. The gap is solely in the adapter layer: `financial_engine/adapters/tax_inputs.py::build_tax_contract_from_project_inputs()` does not read `TaxParams.tax_loss_utilisation_gate` when constructing `TaxPolicy`. `TaxPolicy.loss_utilisation_gate` always defaults to `TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE` (line 82 of `financial_engine/policies/tax.py`). Any project configured with `EBT_POSITIVE` gate would silently receive `TAXABLE_INCOME_POSITIVE` instead. Fix: one line in the adapter constructor.

**Finding 3 (P0): Project-identity dispatch exists in the legacy engine and in the distribution account.** `app/waterfall_core.py` branches on `inputs.info.code == "TUHO-WIND-1"` (lines 223, 254, 130, 309) and passes TUHO-specific flags (`use_tuho_shl_repayment_alignment`, `tuho_shl_principal_eligibility_start_period`, `use_co2_revenue_bridge`, etc.) that alter financial results. `finco_core/engine/distribution_account/inputs.py` has `is_tuho: bool` and `is_oborovo: bool` flags. `evaluate_oborovo_guard(is_oborovo)` in `gates.py` (line 166) blocks TUHO-specific gates for Oborovo — project-identity dispatch modifying financial logic.

---

## 2. Methodology

All findings are derived from static code analysis of `/home/user/Finco1/` combined with
**runtime monkeypatching instrumentation** (see §3-A). The runtime proof runs via pytest
and instruments actual execution — it does NOT infer from imports. Production files were
not modified.

Static investigation sequence:
1. Mapped directory structure and located both financial engines
2. Read the clean engine orchestrator in full (`financial_engine/orchestrator.py`)
3. Read the legacy engine entry point (`app/waterfall_core.py`)
4. Traced the production app dispatch chain: `app/ui_runner.py` → `app/waterfall_runner.py` → `app/waterfall_core.py` → `domain/waterfall/waterfall_engine.py`
5. Read the clean engine adapters (`financial_engine/adapters/tax_inputs.py`, `financial_engine/adapters/project_inputs.py`)
6. Read tax policy files (`financial_engine/policies/tax.py`, `finco_core/inputs/_models.py`)
7. Searched for project-identity dispatch across all production modules
8. Read the distribution account engine and gates
9. Read the KUPI diagnostic and its test
10. Read the parity and recon modules

Runtime instrumentation sequence:
11. Wrote `tests/test_pre_freeze_single_financial_flow_audit.py` (15 tests, all green)
12. Confirmed TUHO/Oborovo runtime traces via `patch.object` on real module attributes (RUNTIME_OBSERVED)
13. Confirmed KUPI factory exclusion via `run_demo_project("KUPI")` returning no result (RUNTIME_OBSERVED)
14. Confirmed KUPI diagnostic calls `run_project_financing_model` → `run_operating_model` → `run_senior_debt_model` → `run_tax_cfads_model` → `compute_shareholder_loan_schedules` by patching each where-used (RUNTIME_OBSERVED)
15. Confirmed `kupi_true_bank_only_senior_diagnostic` calls `diag_mod._forward_roll` AND `diag_mod._backward_dscr_capacity` — P0/D0 built BEFORE patch context, proving calls originate from the diagnostic path itself (DIAGNOSTIC_ONLY_RUNTIME_OBSERVED)

---

## 3-A. Runtime Proof: Instrumented Call-Graph Evidence

**Test module:** `tests/test_pre_freeze_single_financial_flow_audit.py`
**Test count:** 15 green / 0 failed
**Execution:** `python -m pytest tests/test_pre_freeze_single_financial_flow_audit.py -q` → `15 passed`

Evidence labels:
- **RUNTIME_OBSERVED** — call recorded by patch.object instrumentation during actual execution
- **STATIC_CALL_GRAPH_CONFIRMED** — verified by source inspection of import and call sites
- **DIAGNOSTIC_ONLY_RUNTIME_OBSERVED** — call recorded with P0/D0 built outside patch context, proving origin is the diagnostic path itself

### Normalized Observed Traces

```
TUHO (RUNTIME_OBSERVED):
  APP_ENTRY   [app.ui_runner._run_waterfall]
    → LEGACY_RUNNER    [app.waterfall_runner.WaterfallRunner.run]
      → LEGACY_CORE    [app.waterfall_runner.run_waterfall_v3_core]
        → LEGACY_WATERFALL  [domain.waterfall.waterfall_engine.run_waterfall]

Oborovo (RUNTIME_OBSERVED):
  APP_ENTRY   [app.ui_runner._run_waterfall]
    → LEGACY_RUNNER    [app.waterfall_runner.WaterfallRunner.run]
      → LEGACY_CORE    [app.waterfall_runner.run_waterfall_v3_core]
        → LEGACY_WATERFALL  [domain.waterfall.waterfall_engine.run_waterfall]

KUPI factory: NOT IN FACTORY_MAP (RUNTIME_OBSERVED)
  run_demo_project("KUPI") → result.result is None,
                              messages contain "Unknown project type"

KUPI clean-engine (RUNTIME_OBSERVED):
  DIAGNOSTIC_ENTRY [diag_mod.run_p0_current_generic]
    → run_project_financing_model           [call_count >= 1, RUNTIME_OBSERVED]
    → run_operating_model                   [call_count >= 1, RUNTIME_OBSERVED]
      (patched at financial_engine.financing.project.run_operating_model)
    → run_senior_debt_model                 [call_count >= 1, RUNTIME_OBSERVED]
      (patched at financial_engine.financing.project.run_senior_debt_model)
    → run_tax_cfads_model                   [call_count >= 1, RUNTIME_OBSERVED]
      (patched at financial_engine.orchestrator.run_tax_cfads_model)
    → compute_shareholder_loan_schedules    [call_count >= senior_count, RUNTIME_OBSERVED]
      (patched at financial_engine.shl.production.compute_shareholder_loan_schedules)

  Note: the fixed-point convergence loop calls several stages multiple times.
  run_tax_cfads_model → run_operating_model edges are
  STATIC_CALL_GRAPH_CONFIRMED (orchestrator.py line 655, 989).

KUPI bank-only diagnostic (DIAGNOSTIC_ONLY_RUNTIME_OBSERVED):
  [P0 and D0 built BEFORE patch context — no solver interception during preparation]
  kupi_true_bank_only_senior_diagnostic(p0, d0)
    → diag_mod._forward_roll            [call_count >= 1, DIAGNOSTIC_ONLY_RUNTIME_OBSERVED]
    → diag_mod._backward_dscr_capacity  [call_count >= 1, DIAGNOSTIC_ONLY_RUNTIME_OBSERVED]
    — does NOT route through run_project_financing_model or WaterfallRunner.run
```

### Key Observations

| Observation | Evidence label | Test name | Result |
|---|---|---|---|
| TUHO calls `WaterfallRunner.run` | RUNTIME_OBSERVED | `test_tuho_calls_legacy_waterfall_chain` | CONFIRMED |
| TUHO calls `run_waterfall_v3_core` | RUNTIME_OBSERVED | `test_tuho_calls_legacy_waterfall_chain` | CONFIRMED |
| TUHO calls `domain.waterfall.run_waterfall` | RUNTIME_OBSERVED | `test_tuho_calls_legacy_waterfall_chain` | CONFIRMED |
| TUHO does NOT call `run_operating_model` | RUNTIME_OBSERVED | `test_tuho_does_not_call_clean_engine_orchestrator` | CONFIRMED |
| TUHO structural trace in order | RUNTIME_OBSERVED | `test_tuho_structural_trace` | CONFIRMED |
| Oborovo calls full legacy chain | RUNTIME_OBSERVED | `test_oborovo_calls_legacy_waterfall_chain` | CONFIRMED |
| Oborovo does NOT call clean orchestrator | RUNTIME_OBSERVED | `test_oborovo_does_not_call_clean_engine_orchestrator` | CONFIRMED |
| Oborovo structural trace in order | RUNTIME_OBSERVED | `test_oborovo_structural_trace` | CONFIRMED |
| KUPI absent from `FACTORY_MAP` | RUNTIME_OBSERVED | `test_kupi_not_in_app_factory_map` | CONFIRMED |
| KUPI diagnostic calls `run_project_financing_model` | RUNTIME_OBSERVED | `test_kupi_clean_engine_all_stages_called` | CONFIRMED |
| KUPI diagnostic calls `run_operating_model` | RUNTIME_OBSERVED | `test_kupi_clean_engine_all_stages_called` | CONFIRMED |
| KUPI diagnostic calls `run_senior_debt_model` | RUNTIME_OBSERVED | `test_kupi_clean_engine_all_stages_called` | CONFIRMED |
| KUPI diagnostic calls `run_tax_cfads_model` | RUNTIME_OBSERVED | `test_kupi_clean_engine_all_stages_called` | CONFIRMED |
| KUPI diagnostic calls `compute_shareholder_loan_schedules` | RUNTIME_OBSERVED | `test_kupi_clean_engine_all_stages_called` | CONFIRMED |
| KUPI diagnostic does NOT route through app entry | RUNTIME_OBSERVED | `test_kupi_diagnostic_does_not_route_through_app_entry` | CONFIRMED |
| `kupi_true_bank_only_senior_diagnostic` calls `diag_mod._forward_roll` | DIAGNOSTIC_ONLY_RUNTIME_OBSERVED | `test_private_solvers_called_by_diagnostic` | CONFIRMED |
| `kupi_true_bank_only_senior_diagnostic` calls `diag_mod._backward_dscr_capacity` | DIAGNOSTIC_ONLY_RUNTIME_OBSERVED | `test_private_solvers_called_by_diagnostic` | CONFIRMED |
| TUHO/Oborovo NEVER call `run_project_financing_model` | RUNTIME_OBSERVED | `test_legacy_app_projects_never_call_run_project_financing_model[TUHO/Oborovo]` | CONFIRMED |
| TUHO/Oborovo ALWAYS call `run_waterfall_v3_core` | RUNTIME_OBSERVED | `test_legacy_app_projects_always_call_run_waterfall_v3_core[TUHO/Oborovo]` | CONFIRMED |

### Terminology

- **`LEGACY_APP_PRODUCTION_FLOW`**: `app.ui_runner._run_waterfall` → `WaterfallRunner.run` → `run_waterfall_v3_core` → `domain.waterfall.run_waterfall`. This is the ONLY path used by TUHO and Oborovo in production.
- **`CLEAN_PRE_PROMOTION_FINANCIAL_FLOW`**: `run_project_financing_model` → `run_operating_model` / `run_tax_cfads_model` / `run_senior_debt_model` / `run_shl_model`. Used exclusively by KUPI diagnostics and parity scripts.
- **`DIAGNOSTIC_ONLY_PATH`**: `kupi_true_bank_only_senior_diagnostic` via private `_forward_roll` / `_backward_dscr_capacity`. Not callable through any public interface.

---

## 3. Codebase Map

### Key modules

```
financial_engine/
  orchestrator.py          — Clean engine: run_operating_model, run_tax_cfads_model,
                             run_senior_debt_model (Phases 2A/2B/2C)
  adapters/
    project_inputs.py      — ProjectInputs → OperatingModelInput adapter
    tax_inputs.py          — ProjectInputs → TaxCalculationInput adapter (P0 gap: missing loss_utilisation_gate)
    shl_inputs.py          — SHL adapter
    shl_cash_seam.py
  policies/tax.py          — TaxPolicy dataclass
  tax/engine.py            — calculate_tax()
  cfads.py                 — calculate_canonical_cfads()
  senior_debt/solver.py    — solve_senior_debt(), _backward_dscr_capacity(), _forward_roll()
  shl/production.py        — compute_shareholder_loan_schedules()
  shareholder_waterfall/model.py  — G2C Covenant-Gated Shareholder Waterfall (implemented, not wired)
  financing/project.py     — run_project_financing_model() (G2A fixed point)
  sponsor_returns/model.py — G2B sponsor returns (IRR)
  results.py               — ProjectModelResult, PostSeniorCashSchedules, etc.

app/
  waterfall_core.py        — LEGACY: run_waterfall_v3_core() — production path for TUHO/Oborovo
  waterfall_runner.py      — WaterfallRunner, WaterfallRunConfig — reads project flags
  ui_runner.py             — run_demo_project() → _run_waterfall() [legacy path]
  project_factories.py     — create_default_tuho_wind1, create_default_oborovo
  api/project_runner.py    — API entry point → run_demo_project → legacy path

finco_core/
  waterfall/waterfall_engine.py   — run_waterfall() — actual legacy math
  engine/distribution_account/    — DA engine with is_tuho/is_oborovo flags (P0-4)
  opex/oborovo_config.py          — Oborovo hierarchical OPEX model
  shl/engine.py                   — Legacy SHL engine
  inputs/_models.py               — ProjectInputs, TaxParams, DebtSizingCaseConfig

finco_parity/              — Parity check scripts (non-production)
finco_recon/               — Reconciliation scripts (non-production)
tests/
  diagnostics/kupi_k0_k3_causal_grid.py  — KUPI diagnostic (non-production)
  test_kupi_k0_k3_causal_grid.py         — 97 tests (merged in #942)
```

---

## 4. Runtime Call-Graph Comparison

### TUHO (production runtime — RUNTIME_OBSERVED)
```
API POST /api/v1/run  [STATIC_CALL_GRAPH_CONFIRMED: app/api/router.py line 115]
  → app/api/project_runner.py: run_demo_project(...)  [STATIC_CALL_GRAPH_CONFIRMED]
  → app/ui_runner.py line 222: _run_waterfall(proj, engine)  [RUNTIME_OBSERVED: APP_ENTRY]
  → app/waterfall_runner.py: WaterfallRunner.run()  [RUNTIME_OBSERVED: LEGACY_RUNNER]
  → app/waterfall_runner.py: run_waterfall_v3_core()  [RUNTIME_OBSERVED: LEGACY_CORE]
  → domain/waterfall/waterfall_engine.py: run_waterfall()  [RUNTIME_OBSERVED: LEGACY_WATERFALL]
    [Also: finco_core/revenue/generation.py, domain/opex/projections.py,
     domain/financing/depreciation_schedule.py, finco_core/shl/engine.py
     — STATIC_CALL_GRAPH_CONFIRMED within run_waterfall body]
```

### Oborovo (production runtime — RUNTIME_OBSERVED)
Identical observed trace: `run_demo_project("Oborovo")` → `_run_waterfall()` [APP_ENTRY] → `WaterfallRunner.run()` [LEGACY_RUNNER] → `run_waterfall_v3_core()` [LEGACY_CORE] → `run_waterfall()` [LEGACY_WATERFALL]

### KUPI (test/diagnostic only — NOT in production app)
KUPI has no factory in `app/project_factories.py` and is not in the `FACTORY_MAP` in `app/ui_runner.py` (lines 129–137) — **RUNTIME_OBSERVED**: `run_demo_project("KUPI")` returns `result.result is None`. KUPI exists only in diagnostics:
```
tests/diagnostics/kupi_k0_k3_causal_grid.py:
  run_p0_current_generic()                              [RUNTIME_OBSERVED: DIAGNOSTIC_ENTRY]
    → diag_mod.run_project_financing_model()            [RUNTIME_OBSERVED: call_count >= 1]
      → financial_engine.financing.project:
        run_operating_model()                           [RUNTIME_OBSERVED: call_count >= 1]
        run_senior_debt_model()                         [RUNTIME_OBSERVED: call_count >= 1]
          → (inside orchestrator, fixed-point loop):
            run_tax_cfads_model()                       [RUNTIME_OBSERVED: call_count >= 1]
            compute_shareholder_loan_schedules()        [RUNTIME_OBSERVED: call_count >= senior_count]
```
`kupi_true_bank_only_senior_diagnostic(p0, d0)` (line 1657) calls `diag_mod._forward_roll` and `diag_mod._backward_dscr_capacity` — **DIAGNOSTIC_ONLY_RUNTIME_OBSERVED** with P0/D0 pre-built before patch context. The calls originate from the diagnostic path itself, not from clean-engine preparation.

**Summary: TUHO and Oborovo do NOT flow through the clean engine in production (RUNTIME_OBSERVED). KUPI is not a production project (RUNTIME_OBSERVED).**

---

## 5. Financial Authority Matrix

| Financial concept | Canonical input authority | Canonical calculation owner | Canonical result authority | TUHO path | Oborovo path | KUPI path | Duplicate? | Severity | Recommended action |
|---|---|---|---|---|---|---|---|---|---|
| Project inputs | `finco_core.inputs._models.ProjectInputs` | Factory / build function | `ProjectInputs` dataclass | `create_default_tuho_wind1()` | `create_default_oborovo()` | `build_kupi_project_inputs()` | NO — same model | P3 | — |
| Period generation | `OperatingModelInput.calendar` | `finco_core.engine.period_engine.PeriodEngine` | `tuple[OperatingPeriodResult]` | Same PeriodEngine via legacy | Same | Same PeriodEngine via clean | NO | P2 | Confirm identical args |
| Production / yield | `TechnicalParams` | `finco_core.revenue.generation.full_generation_schedule` | `dict[int, float]` mwh | Same leaf function | Same | Same leaf function | NO | P2 | — |
| Revenue | `RevenueParams` | `finco_core.revenue.generation.full_revenue_schedule` | `dict[int, float]` kEUR | Same leaf (+ `use_co2_revenue_bridge` project-dispatch, line 130) | Same | Same leaf | NO for basic; P0 for CO2 bridge | P0 | Replace CO2 bridge project-dispatch with typed revenue capability |
| OPEX | `OpexItem` | `finco_core.opex.projections.opex_schedule_period` | `dict[int, float]` | Same leaf | Same + hierarchical (`oborovo_config.py`) typed capability | Same leaf | NO for basic; PRODUCTION_PATH_WITH_DIFFERENT_TYPED_POLICY for Oborovo | P2 | Typed capability already exists; clean engine supports it |
| EBITDA | revenue − opex | `max(0, rev−opex)` legacy / `rev−opex` clean | `dict[int, float]` | Legacy: **clips at zero** (waterfall_core.py line 226) | Same legacy clip | Clean: **no floor** (orchestrator.py line 424) | YES — DIVERGENT FORMULA | P0 | Decide floor rule; apply consistently |
| Tax depreciation | `DepreciationInput` | `finco_core.debt.depreciation_schedule.build_depreciation_schedule` | `dict[int, float]` | Legacy: `BOOK_BASED_PERCENTAGE` only | Same legacy | Clean: separate book/tax schedules | PRODUCTION_PATH_WITH_DIFFERENT_TYPED_POLICY | P1 | Clean engine is superset; legacy falls back to single mode |
| Taxable income | `TaxCalculationInput` | `calculate_tax()` (clean) / inline `run_waterfall` (legacy) | Annual tax result | Legacy inline | Same legacy | `calculate_tax()` clean | DUPLICATE_FINANCIAL_AUTHORITY | P0 | Consolidate to `calculate_tax()` |
| Tax losses / LCF | `TaxPolicy.loss_carryforward_years` | FIFO vintage ledger (clean) / scalar (legacy) | Annual LCF roll | Legacy: scalar `prior_tax_loss_keur` — no vintage dating | Same legacy | Clean: `loss_ledger.run_annual_fifo_ledger()` | DUPLICATE_FINANCIAL_AUTHORITY | P0 | — |
| `loss_utilisation_gate` | `TaxParams.tax_loss_utilisation_gate` | `TaxPolicy.loss_utilisation_gate` | Gate on LCF use | **NOT FORWARDED** in adapter | **NOT FORWARDED** | **NOT FORWARDED** | MISSING FIELD PROPAGATION | P0 | Forward in `build_tax_contract_from_project_inputs()` — one line fix |
| Cash tax | `TaxPolicy.cash_tax_timing` | `calculate_tax().period_results[].cash_tax_keur` (clean) | `tuple[float]` | Legacy per-period inline | Same legacy | Clean: `TAX_YEAR_LAST_PERIOD` timing | DUPLICATE_FINANCIAL_AUTHORITY | P0 | — |
| Base CFADS | EBITDA − cash_tax | `calculate_canonical_cfads()` (clean) / inline (legacy) | `tuple[float]` | Legacy inline in `run_waterfall` | Same | `calculate_canonical_cfads()` | DUPLICATE_FINANCIAL_AUTHORITY | P0 | — |
| Bank CFADS | Bank EBITDA − bank tax | `derive_debt_sizing_operating_input()` + `calculate_canonical_cfads()` | `tuple[float]` | MISSING_TYPED_BANK_CASE_POLICY — no typed case config in legacy | Same — MISSING | Clean `DebtSizingCaseInput` typed | STRUCTURAL GAP in legacy | P0 | Implement `DebtSizingCaseInput` for TUHO/Oborovo |
| Senior commitment | `eligible_cost × max_gearing` | `solve_senior_debt()` (clean) / inline sculpting (legacy) | `debt_size_keur` | Legacy inline in `run_waterfall` | Same legacy | `solve_senior_debt()` clean | DUPLICATE_FINANCIAL_AUTHORITY | P0 | — |
| Senior IDC | Construction interest on facility | `finco_core.debt.idc` (legacy) | `float` kEUR | Legacy inline | Same | Clean construction module | DUPLICATE | P1 | — |
| Senior schedule | Period-by-period debt service | `_forward_roll()` inside `solve_senior_debt()` | `SeniorDebtSchedules` | Legacy sculpting in `run_waterfall` | Same | `solve_senior_debt()` → `_forward_roll()` | DUPLICATE_FINANCIAL_AUTHORITY | P0 | — |
| Senior interest | `opening × rate × day_frac` | `financial_engine.senior_debt.interest.period_interest` | `tuple[float]` | Legacy inline | Same | Clean module | DUPLICATE_FINANCIAL_AUTHORITY | P0 | — |
| Senior principal | DSCR-sculpted per period | `sculpting.build_schedule` inside `_forward_roll()` | `tuple[float]` | Legacy inline | Same | Clean module | DUPLICATE_FINANCIAL_AUTHORITY | P0 | — |
| Post-senior cash | Base CFADS − senior DS | `_assemble_post_senior_cash_schedules()` (clean) / inline (legacy) | `PostSeniorCashSchedules` | Legacy inline | Same | Clean `PostSeniorCashSchedules` | DUPLICATE_FINANCIAL_AUTHORITY | P0 | — |
| DSRA / reserve layer | DSRA balance, target | NOT_IMPLEMENTED in clean engine | None | Legacy: `dsra_months` scalar | Same legacy | NOT_IMPLEMENTED | NOT_IMPLEMENTED in clean | P1 | Must implement before clean engine promotion |
| Distribution Account | DA roll-forward with CF109 5-component gate | `financial_engine.shareholder_waterfall.model` (clean, not wired) / `finco_core.engine.distribution_account` (legacy, wired) | DA result | Legacy with `is_tuho=True` — project-identity dispatch | Legacy with `is_oborovo=True` — `evaluate_oborovo_guard` | NOT wired in diagnostic | DUPLICATE_FINANCIAL_AUTHORITY + project-identity dispatch | P0 | Replace `is_tuho`/`is_oborovo` with typed `CovenantGatePolicy` |
| Covenant / distribution gate | DSCR lockup, DSRA balance | `evaluate_dscr_gate`, `evaluate_lockup_gate` in `finco_core.engine.distribution_account.gates` | `DistributionGateResult` | Legacy with TUHO-specific gate | Legacy with Oborovo guard | NOT_IMPLEMENTED | DUPLICATE | P0 | — |
| SHL construction funding | Per-period draw schedule | `build_shl_construction_draw_schedule()` + `compute_shl_construction_schedule()` | `ShlConstructionSchedule` | Legacy: scalar `shl_idc_keur` | Same legacy scalar | Clean: per-period with timing policy | DUPLICATE_FINANCIAL_AUTHORITY | P1 | — |
| SHL PIK | Compound periodic PIK | `compute_shl_construction_schedule()` per period | `pik_keur` per period | Legacy: flat scalar `shl_idc_keur` | Same | Clean: per-period DCF × rate | PRODUCTION_PATH_WITH_DIFFERENT_TYPED_POLICY | P1 | — |
| COD opening SHL | cash_SHL + PIK | `reconcile_financing_stack()` → fixed point in `run_project_financing_model()` | `shl_opening_at_cod_keur` | Legacy: `clean_shl_principal_keur` read from factory (not derived) | Same | Derived by fixed point | DUPLICATE_FINANCIAL_AUTHORITY | P0 | — |
| Operating SHL interest | `opening × rate × day_frac` | `compute_shareholder_loan_schedules()` (clean) / `finco_core.shl.engine` (legacy) | `shl_gross_interest_keur` | Legacy `finco_core/shl/engine.py` with `use_tuho_shl_repayment_alignment` flag | Same legacy | Clean `financial_engine.shl.production` | DUPLICATE_FINANCIAL_AUTHORITY + project-identity dispatch | P0 | — |
| SHL principal repayment / sweep | Cash sweep from `cash_available_for_shl` | `compute_shareholder_loan_schedules()` sweep logic | `shl_cash_principal_keur` | Legacy with `use_tuho_shl_repayment_alignment` + `tuho_shl_principal_eligibility_start_period` flags | Same legacy | Clean, no project dispatch | DUPLICATE_FINANCIAL_AUTHORITY + project-identity dispatch | P0 | Replace with typed `ShlRepaymentPolicy` |
| Dividends / sponsor equity cash | `fcf_for_distribution` post-SHL | Inline in legacy `run_waterfall` (legacy) / G2C model (clean, not wired) | `distribution_keur` | Legacy inline | Same | NOT fully wired (G2C exists but not wired to G2A in diagnostic) | DUPLICATE_FINANCIAL_AUTHORITY | P0 | Wire DA gate into clean engine SHL path |
| Equity IRR | Sponsor perspective cash flows | `finco_core.sponsor.xirr.robust_xirr` | `float` | Legacy: `discount_rate_equity` XIRR in `run_waterfall` | Same | `financial_engine.sponsor_returns.model` (G2B) | DUPLICATE_FINANCIAL_AUTHORITY | P1 | IRR does not independently reconstruct econ model — lower risk |
| Project IRR | Pre-financing project cash flows | XIRR on `(capex, CFADS)` | `float` | Legacy: inline in `run_waterfall` | Same | G2B sponsor returns | DUPLICATE_FINANCIAL_AUTHORITY | P1 | — |
| Final persisted outputs | `WaterfallResult` (legacy) / `ProjectFinancingResult` (clean) | Assembled by orchestrator | Result object | `WaterfallResult` — surfaced to API and UI | Same `WaterfallResult` | `ProjectFinancingResult` — surfaced to tests only | DUPLICATE_FINANCIAL_AUTHORITY | P0 | — |

---

## 6. Detailed Findings by Layer

### Layers 1–4: Inputs, Periods, Yield, Revenue
All three projects use the same `ProjectInputs` dataclass (`finco_core/inputs/_models.py`). Period engine (`finco_core.engine.period_engine.PeriodEngine`), generation schedule (`finco_core.revenue.generation`), and revenue schedule are called from both engines. Classification: `SAME_CANONICAL_PRODUCTION_PATH` for the leaf functions.

**Exception (P0):** TUHO uses `use_co2_revenue_bridge=True`, gated by a project-code check at `waterfall_core.py` line 130. This is project-identity dispatch adding CO2 certificate revenue to the revenue dict before EBITDA aggregation. Should be a typed revenue capability.

### Layer 5: OPEX
Both engines call `finco_core.opex.projections.opex_schedule_period()`. Oborovo additionally uses `finco_core.opex.oborovo_config.build_oborovo_opex_capability()` — a typed `HierarchicalOpexCapability`. The clean engine also supports this (orchestrator.py line 181). Classification: `SAME_CANONICAL_PRODUCTION_PATH` for basic; `PRODUCTION_PATH_WITH_DIFFERENT_TYPED_POLICY` for Oborovo hierarchical (acceptable).

### Layer 6: EBITDA (P0)
- **Legacy** (`waterfall_core.py` line 226): `ebitda = max(0, rev - opex)` — negative EBITDA clipped to zero.
- **Clean engine** (`orchestrator.py` line 424): `ebitda_by_idx = {idx: revenue - opex for idx in ...}` — no floor.
- Material financial difference: projects with loss-making periods have different taxable income, CFADS, Senior capacity, and SHL balances depending on engine. Classification: `DUPLICATE_FINANCIAL_AUTHORITY` with divergent formula.

### Layer 7: Tax depreciation
- Legacy: `BOOK_BASED_PERCENTAGE` mode only (`waterfall_core.py` lines 239–247). Falls back closed on other modes.
- Clean: supports separate `book_capex_items_for_depreciation` and `tax_capex_items_for_depreciation` via `build_depreciation_schedule()`. Superset.
- Classification: `PRODUCTION_PATH_WITH_DIFFERENT_TYPED_POLICY` — clean is more capable, not yet production-wired for TUHO/Oborovo.

### Layers 8–10: Tax (P0)
- Legacy: inline taxable income, per-period CIT, scalar LCF in `domain/waterfall/waterfall_engine.py`.
- Clean: `calculate_tax()` with FIFO vintage ledger, annual periodisation, typed LCF gate.
- **Critical gap**: `TaxParams.tax_loss_utilisation_gate` (`finco_core/inputs/_models.py` line 1146) is NOT forwarded in `financial_engine/adapters/tax_inputs.py`. The adapter builds `TaxPolicy` without this field. `TaxPolicy.loss_utilisation_gate` always defaults to `TAXABLE_INCOME_POSITIVE` (`financial_engine/policies/tax.py` line 82). This is a silent misclassification for any project using `EBT_POSITIVE` gate — **including KUPI as configured in the diagnostic**.
- Classification: `DUPLICATE_FINANCIAL_AUTHORITY` + `MISSING_FIELD_PROPAGATION` (P0).

### Layers 11–12: CFADS and Bank CFADS (P0)
- Legacy: inline `cf_after_tax_keur` in `run_waterfall`. No typed Bank Case separation.
- Clean: `calculate_canonical_cfads()` from `financial_engine/cfads.py`. `DebtSizingCaseInput` provides typed Bank vs Base separation with explicit `production_yield_scenario` and merchant price overrides.
- For TUHO/Oborovo in legacy: `MISSING_TYPED_BANK_CASE_POLICY`. For KUPI in clean: `GENERIC_DEBT_SIZING_CASE_IS_EXPLICIT_AND_PROJECT_IDENTITY_FREE`.

### Layers 13–16: Senior (P0)
- Legacy: inline sculpting in `run_waterfall` with scalar `target_dscr`, `gearing_ratio`, `tenor_periods`, `rate_per_period`.
- Clean: `SeniorDebtPolicy` + `SeniorDebtInputs` → `solve_senior_debt()` → `_forward_roll()` + `_backward_dscr_capacity()`.
- Note: The KUPI diagnostic calls `_forward_roll()` / `_backward_dscr_capacity()` directly (line 1769 of `kupi_k0_k3_causal_grid.py`) for causal decomposition. This is `DIAGNOSTIC_ONLY_PATH` — acceptable. Production uses `solve_senior_debt()`.
- Classification: `DUPLICATE_FINANCIAL_AUTHORITY`.

### Layer 17: Post-senior cash + DA covenant gap (P0)
- Clean engine (`orchestrator.py` line 1649): `cash_available_for_shl_before_reserves_keur = max(0, base_cfads - senior_service)`. Note reads: `DSRA_NOT_IMPLEMENTED: pre-reserve figures; DSRA ordering unresolved`.
- This pre-reserve value is passed **directly** to `compute_shareholder_loan_schedules()`. The CF109 Distribution Account gate (which should sit between post-senior cash and SHL allocation) is **not invoked** in `run_senior_debt_model`.
- This is the seam identified as `PRE_RESERVE_SHL_CASH_AUTHORITY_GAP` in the KUPI diagnostic: Finco exposes pre-reserve, pre-gate cash as SHL-eligible, while the source workbook uses post-covenant-release DA cash.
- Classification: `DUPLICATE_FINANCIAL_AUTHORITY` + `DSRA_NOT_IMPLEMENTED`.

### Layer 18: DSRA (P1)
- Clean engine: `NOT_IMPLEMENTED`. Comment at `financial_engine/shl/production.py` lines 45–46: `DSRA_ORDERING_UNRESOLVED`.
- Legacy: `dsra_months` scalar parameter to `run_waterfall`.
- Classification: `NOT_IMPLEMENTED` in clean engine.

### Layers 19–20: Distribution Account and Covenant Gate (P0)
- **Legacy DA** (`finco_core/engine/distribution_account/`): `inputs.py` lines 36–37, 59–60 expose `is_tuho: bool` and `is_oborovo: bool`. `gates.py` line 166: `evaluate_oborovo_guard(is_oborovo)` blocks TUHO-specific R99/R102 gates for Oborovo.
- **Clean G2C model** (`financial_engine/shareholder_waterfall/model.py`): Implemented with CF109 5-component gate; no project flags; not wired to `run_senior_debt_model`.
- Classification: `DUPLICATE_FINANCIAL_AUTHORITY` for DA + **project-identity dispatch** in legacy DA inputs.

### Layers 21–24: SHL Construction, PIK, Operating, Sweep (P0/P1)
- Legacy: scalar `shl_idc_keur` for construction; `finco_core/shl/engine.py` for operating; `use_tuho_shl_repayment_alignment` + `tuho_shl_principal_eligibility_start_period` flags in `finco_core/waterfall/waterfall_engine.py` lines 322–323.
- Clean: `financial_engine.shl.construction` (per-period, typed timing policy), `financial_engine.shl.production` (no project flags), `run_project_financing_model()` fixed point.
- Classification: `DUPLICATE_FINANCIAL_AUTHORITY` + project-identity dispatch in legacy SHL.

### Layers 25–27: Dividends, IRR (P0/P1)
- Legacy DA `equity_distribution_paid_keur` optionally wired via `use_distributionaccount_runtime_wiring` flag; XIRR inline.
- Clean G2C not wired to G2A; G2B sponsor returns only reachable via `run_project_financing_model` path.
- IRR does not independently reconstruct an economic model — it consumes outputs. Dual IRR is a completeness gap (P1), not a dual-truth risk.

### Layer 28: Final outputs
- Legacy: `WaterfallResult` surfaced to API and UI.
- Clean: `ProjectFinancingResult` surfaced to tests only.
- Classification: `DUPLICATE_FINANCIAL_AUTHORITY`.

---

## 7. Duplicate / Legacy / Diagnostic Seam Inventory

### Confirmed duplicate financial authorities

| # | Seam | Legacy side | Clean side |
|---|---|---|---|
| 1 | Full financial calculation stack | `run_waterfall_v3_core` → `run_waterfall` | `run_operating_model` → `run_tax_cfads_model` → `run_senior_debt_model` |
| 2 | SHL interest / sweep | `finco_core.shl.engine` | `financial_engine.shl.production` |
| 3 | Distribution Account gate | `finco_core.engine.distribution_account` | `financial_engine.shareholder_waterfall.model` |
| 4 | EBITDA floor | `max(0, rev−opex)` | `rev−opex` uncapped |
| 5 | Tax engine | Inline in `run_waterfall` | `calculate_tax()` |
| 6 | Post-senior → SHL seam | DA gate → `equity_distribution` | `cash_available_for_shl_before_reserves_keur` (pre-gate) |

### Project-identity dispatch (all prohibited)

| # | File | Location | Dispatch |
|---|---|---|---|
| 1 | `app/waterfall_core.py` | line 223 | `if getattr(inputs.info, "code", "") != "TUHO-WIND-1"` |
| 2 | `app/waterfall_core.py` | line 254 | `if use_shl_canonical_engine and ... not in ("TUHO-WIND-1", "OBOROVO-SOLAR-1")` |
| 3 | `app/waterfall_core.py` | line 130 | `use_co2_revenue_bridge` (TUHO-only semantically) |
| 4 | `app/waterfall_core.py` | line 439 | `if 'phase7_tuho' in _configured_fixture_path` |
| 5 | `finco_core/engine/distribution_account/inputs.py` | lines 36–37, 59–60 | `is_tuho: bool`, `is_oborovo: bool` |
| 6 | `finco_core/engine/distribution_account/gates.py` | line 166 | `evaluate_oborovo_guard(is_oborovo)` |
| 7 | `finco_core/waterfall/waterfall_engine.py` | lines 322–323 | `use_tuho_shl_repayment_alignment`, `tuho_shl_principal_eligibility_start_period` |
| 8 | `finco_core/shl/runtime_adapter.py` | line 181 | `project_name="TUHO"` default |
| 9 | `finco_core/shl/canonical_wiring.py` | line 187 | `project_name="TUHO"` default |

### Frozen / calibration paths

- `app/waterfall_core.py` lines 436–502: `use_frozen_excel_senior_debt_schedule` + fixture path check for `phase7_tuho` stem. When active, loads a CSV fixture for sizing CFADS instead of computing from EBITDA. Classification: `WORKBOOK_FROZEN / CALIBRATION_ONLY`. A workbook-locked compatibility path.

### Diagnostic paths

- `tests/diagnostics/kupi_k0_k3_causal_grid.py` lines 536–644 (grid run functions): Call `run_project_financing_model()`. **Canonical production path** — acceptable diagnostic use that calls the real engine and observes results.
- `tests/diagnostics/kupi_k0_k3_causal_grid.py` lines ~1769–1872 (`kupi_true_bank_only_senior_diagnostic`): Calls `_backward_dscr_capacity()` and `_forward_roll()` directly. Also implements a simplified inline tax shadow (paired H1+H2 periodisation, `EBT_POSITIVE` gate, `LCF_MODEL_PERIODS=5` hardcoded) that diverges from `calculate_tax()`. Classification: `DIAGNOSTIC_ONLY_PATH`. **Not production-equivalent and not parity evidence.** Engineers reading this code must not mistake the inline tax shadow for proof that `calculate_tax()` matches the source workbook.

---

## 8. P0 / P1 / P2 / P3 Findings (Ranked)

### P0 — Architecture blockers (can produce different financial truth depending on path)

**P0-1: Two production financial engines exist simultaneously.**
TUHO and Oborovo run the legacy `run_waterfall` engine; the clean engine is parity/test only. No single canonical production truth.
Files: `app/waterfall_core.py`, `financial_engine/orchestrator.py`.
**P0-1 closure condition:** TUHO and Oborovo production runtime no longer uses `LEGACY_APP_PRODUCTION_FLOW` as financial authority. This requires PRs 1–7 to remove all blocking semantic, policy, and waterfall gaps, PLUS **PR-8** to perform the actual production authority migration. P0-1 is NOT closed until PR-8 is complete and the audit-snapshot regression tests are updated to reflect the promoted call graph.

**P0-2 (`MISSING_ADAPTER_PROPAGATION`): `tax_loss_utilisation_gate` not forwarded by the clean engine tax adapter.**
Classification: `MISSING_ADAPTER_PROPAGATION`. This is NOT `MISSING_TAX_ENGINE_IMPLEMENTATION` — `calculate_tax()` in `financial_engine/tax/engine.py` already handles `EBT_POSITIVE` correctly. The gap is solely in the adapter: `financial_engine/adapters/tax_inputs.py::build_tax_contract_from_project_inputs()` does not read `TaxParams.tax_loss_utilisation_gate` when constructing `TaxPolicy`. `TaxPolicy.loss_utilisation_gate` always defaults to `TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE` (line 82 of `financial_engine/policies/tax.py`). KUPI configured with `EBT_POSITIVE` silently receives `TAXABLE_INCOME_POSITIVE`.
File: `financial_engine/adapters/tax_inputs.py`.
Fix: one line — `loss_utilisation_gate=TaxLossUtilisationGate(tax.tax_loss_utilisation_gate.value)` in the `TaxPolicy` constructor call.

**P0-3: EBITDA floor divergence.**
Legacy `waterfall_core.py` line 226: `ebitda = max(0, rev - opex)`.
Clean engine `orchestrator.py` line 424: no floor.
Impact: taxable income, CFADS, Senior capacity, and SHL balances differ in loss-making periods.

**P0-4: Project-identity dispatch in Distribution Account.**
`is_tuho` and `is_oborovo` boolean flags in `finco_core/engine/distribution_account/inputs.py` (lines 36–37, 59–60) cause different gate logic. `evaluate_oborovo_guard` (`gates.py` line 166) blocks TUHO-specific R99/R102 gates for Oborovo.

**P0-5: No typed Bank Case policy for TUHO/Oborovo.**
Legacy has no `DebtSizingCaseInput`. Bank-case yield scenario and merchant prices are not representable independently from base. KUPI in clean engine has a full typed `DebtSizingCaseInput`. TUHO/Oborovo in legacy: `MISSING_TYPED_BANK_CASE_POLICY`.

**P0-6: SHL sweep project-identity dispatch.**
`use_tuho_shl_repayment_alignment` and `tuho_shl_principal_eligibility_start_period` flags in `finco_core/waterfall/waterfall_engine.py` lines 322–323 control SHL principal eligibility on a project-named basis.

**P0-7: Covenant gate does not intercept SHL cash in clean engine.**
`compute_shareholder_loan_schedules()` receives `cash_available_for_shl_before_reserves_keur` directly (pre-DSRA, pre-DA-gate). The CF109 DA gate is not invoked in the clean engine's `run_senior_debt_model`. Clean engine and legacy produce different sponsor cash flows.

**P0-8: CO2 revenue bridge is project-identity dispatch.**
`use_co2_revenue_bridge` in `waterfall_core.py` line 130 is semantically TUHO-only (guarded by project code check). Should be a typed revenue capability flag.

### P1 — Mandatory pre-freeze consolidation

**P1-1: DSRA not implemented in clean engine.**
`financial_engine/shl/production.py` lines 45–46: `DSRA_ORDERING_UNRESOLVED`. Clean engine computes post-senior cash without DSRA deduction. Required before clean engine can be promoted for TUHO/Oborovo.

**P1-2: SHL construction PIK is per-period in clean engine, scalar in legacy.**
Clean: `compute_shl_construction_schedule()` produces per-period PIK. Legacy: flat `shl_idc_keur` scalar. Different COD opening SHL balances.

**P1-3: TUHO opening SHL read from factory, not derived.**
The production factory sets `clean_shl_principal_keur` directly. The clean `run_project_financing_model()` derives SHL from a fixed point. These must be verified to agree before promotion.

### P2 — Debt/sponsor feature completeness

**P2-1: IRR not wired to a single authoritative cash flow reconstruction.**
G2B sponsor returns module only reachable via clean engine path. IRR for TUHO/Oborovo in production comes from legacy inline XIRR. Completeness gap, not dual-truth risk (IRR does not reconstruct independent economics).

**P2-2: ATAD interest limitation not production-wired.**
`build_tax_contract_from_project_inputs()` raises `NotImplementedError` for `atad_enabled=True`. Guard is correct; ATAD is not yet production-wired.

### P3 — Cleanup / ergonomics

**P3-1:** `finco_core/shl/runtime_adapter.py` line 181 and `finco_core/shl/canonical_wiring.py` line 187 default `project_name="TUHO"`. Non-functional for clean engine, misleading defaults.

**P3-2:** `finco_core/opex/oborovo_config.py` is a project-named module containing a valid typed capability. No financial correctness impact.

---

## 9. Project Identity Dispatch Audit Results

The **clean engine** (`financial_engine/`) contains **zero** project-identity dispatch. The orchestrator's `derive_debt_sizing_operating_input()` is explicitly `GENERIC_DEBT_SIZING_CASE_IS_EXPLICIT_AND_PROJECT_IDENTITY_FREE`. The SHL production module has no project checks.

The **legacy engine** (`app/waterfall_core.py`, `finco_core/waterfall/waterfall_engine.py`, `finco_core/engine/distribution_account/`) contains **9 confirmed project-identity dispatch sites** (enumerated in Section 7 above).

The **KUPI diagnostic** is structured to avoid project-identity dispatch in the engine. The direct calls to `_backward_dscr_capacity` / `_forward_roll` are causal analysis tools, not engine substitutes.

---

## 10. Diagnostic vs Production Separation Findings

| Code location | Calls | Classification |
|---|---|---|
| `kupi_k0_k3_causal_grid.py` lines 536–644 (grid run functions) | `run_project_financing_model()` | DIAGNOSTIC calling CANONICAL PRODUCTION ENGINE — acceptable |
| `kupi_k0_k3_causal_grid.py` lines ~1769–1872 (`kupi_true_bank_only_senior_diagnostic`) | `_backward_dscr_capacity()`, `_forward_roll()` directly + inline tax shadow | DIAGNOSTIC_ONLY_PATH — NOT production-equivalent |
| `tests/test_kupi_k0_k3_causal_grid.py` | Consumes diagnostic outputs via pytest | DIAGNOSTIC_ONLY_PATH (test harness) |
| `finco_parity/` | Calls clean engine, compares to legacy | DIAGNOSTIC_ONLY_PATH |
| `finco_recon/` | Calls clean engine, compares to legacy | DIAGNOSTIC_ONLY_PATH |

**Key risk:** The inline tax shadow in the diagnostic (`kupi_true_bank_only_senior_diagnostic`) implements a parallel financial calculation (paired H1+H2 periodisation, `EBT_POSITIVE` gate, `LCF_MODEL_PERIODS=5`) that diverges from `calculate_tax()`. It is labelled diagnostic-only and must not be read as parity evidence for the production tax engine.

---

## 11. Single-Engine Verdict

### A. Do we currently have one financial engine?

**NO — MULTIPLE MATERIAL FINANCIAL FLOWS**

Runtime instrumentation (§3-A, 14 tests green) confirms two completely separate financial
flows exist and execute independently:

- **`LEGACY_APP_PRODUCTION_FLOW`**: TUHO and Oborovo exclusively. Does NOT call clean engine orchestrator. Computes EBITDA (with zero-floor), tax (inline, scalar LCF), CFADS (inline), Senior (sculpting solver), SHL (legacy engine), DA (with `is_tuho`/`is_oborovo` dispatch) through the legacy waterfall math.
- **`CLEAN_PRE_PROMOTION_FINANCIAL_FLOW`**: KUPI diagnostics and parity scripts exclusively. Computes EBITDA (no floor), tax (FIFO vintage LCF, typed policy), CFADS (canonical), Senior (fixed-point solver), SHL (typed policy) through the clean engine. DSRA and DA gate are NOT wired in this path.

These are not "one core with parallel wiring" — they are two materially distinct financial engines with different formulas, different LCF models, different EBITDA floors, and different SHL/DA gates. Every financial layer below revenue is a `DUPLICATE_FINANCIAL_AUTHORITY`.

Promotion of the clean engine to production requires eliminating all P0 findings before go-live.

### B. Which items must be fixed before touching the next major feature? (dependency order)

See §13 (P0-to-PR Mapping) and §14 (Consolidation PR Sequence) for full detail.

1. **PR-1**: Fix `loss_utilisation_gate` adapter propagation (`MISSING_ADAPTER_PROPAGATION`). One line. P0-2.
2. **PR-2**: Replace `is_tuho`/`is_oborovo` DA dispatch with typed `CovenantGatePolicy`; remove CO2 identity dispatch. P0-4, P0-8.
3. **PR-3**: Implement DSRA roll-forward in clean engine. P1-1. (requires PR-2)
4. **PR-4**: Wire DA covenant gate into clean engine SHL path — closes `PRE_RESERVE_SHL_CASH_AUTHORITY_GAP`. P0-7. (requires PR-2, PR-3)
5. **PR-5**: Resolve EBITDA floor rule (decision required). P0-3.
6. **PR-6**: Replace SHL repayment-alignment flags with typed `ShlRepaymentPolicy`. P0-6. (requires PR-4)
7. **PR-7**: Implement typed `DebtSizingCaseInput` (`MISSING_TYPED_BANK_CASE_POLICY` — Base vs Bank separation). P0-5. (requires PRs 1–6)
8. **PR-8**: TUHO + Oborovo clean-engine production promotion and `LEGACY_APP_PRODUCTION_FLOW` authority retirement. (requires PRs 1–7)
   - Route TUHO and Oborovo production app execution through the canonical clean financial engine
   - Preserve typed project policies only; eliminate project-named financial logic
   - Update audit-snapshot regression tests (`test_legacy_app_projects_*`) as part of this PR
   - Prove both projects execute the same canonical production call graph via runtime instrumentation
   - Retain legacy path only if temporarily required for explicit migration diagnostics, never as competing production financial authority
   - **P0-1 is closed when this PR merges**

### C. Which major implementation should come first after consolidation?

**`CASH_DSRA + Sponsor Waterfall / Distribution Covenant + SHL repayment promotion`**

Evidence:
- The clean engine's senior + SHL fixed-point solver (`_run_senior_debt_model_with_shl`) is complete and convergence-verified. The only missing components before a complete post-senior waterfall are DSRA and the DA gate.
- The G2C shareholder waterfall model (`financial_engine/shareholder_waterfall/model.py`) is already implemented and source-proven from Oborovo + TUHO workbooks (docstring cites `CF!G108`–`CF!G116`). It only needs to be invoked inside `run_senior_debt_model`.
- The `cash_available_for_shl_before_reserves_keur` field already exists in `PostSeniorCashSchedules` — the seam is named and allocated. Wiring the DA gate into this seam is a contained change.
- The `loss_utilisation_gate` fix (P0-2) is a one-liner pre-requisite that can go in the same PR.
- Construction Runtime Promotion has a blocking dependency: `construction_period_uses_keur` for multi-period PRO_RATA projects is flagged `GAP 3` in `financial_engine/financing/project.py` lines 99–112. The DSRA/waterfall work has no such blocking dependency.
- Sponsor Waterfall (PRs 1–6) is the first major consolidation implementation block. It does NOT by itself produce a single production engine — it removes the blocking semantic/policy/waterfall gaps.
- Single-engine status is only achieved after **PR-7** (typed Bank Case / Base-vs-Bank separation) + **PR-8** (TUHO/Oborovo production authority migration). Construction Runtime then proceeds on a clean single-engine foundation.

---

## 12. P0-to-PR Mapping

| P0 finding | Classification | Financial risk | Required before clean-engine promotion? | Proposed PR |
|---|---|---|---|---|
| P0-1: Dual engines (legacy vs clean) | `DUPLICATE_FINANCIAL_AUTHORITY` | Every financial layer below revenue produces different truth depending on project path | YES — NOT CLOSED until PR-8 | PRs 1–7 remove blocking gaps; **PR-8 performs production authority migration. P0-1 closure condition: TUHO and Oborovo production runtime no longer uses LEGACY_APP_PRODUCTION_FLOW as financial authority.** |
| P0-2: `tax_loss_utilisation_gate` not forwarded | `MISSING_ADAPTER_PROPAGATION` (NOT `MISSING_TAX_ENGINE_IMPLEMENTATION` — engine already handles `EBT_POSITIVE`) | Silent wrong gate applied to any project using `EBT_POSITIVE`; affects LCF use and tax cash timing | YES | PR-1 |
| P0-3: EBITDA floor divergence | `DUPLICATE_FINANCIAL_AUTHORITY` | Legacy clips EBITDA at zero in loss years → lower tax, different CFADS, different Senior capacity vs clean | YES | PR-5 (decision required: keep floor or remove) |
| P0-4: `is_tuho`/`is_oborovo` DA dispatch | `DUPLICATE_FINANCIAL_AUTHORITY` | Different gate logic per project name → different Sponsor-eligible cash in legacy DA | YES — blocks typed promotion | PR-2 |
| P0-5: `MISSING_TYPED_BANK_CASE_POLICY` | `NOT_IMPLEMENTED` | No independent Bank-case yield/price scenario for TUHO/Oborovo; lenders cannot stress-test independently | YES — required before Bank presentation | PR-7 |
| P0-6: SHL repayment-alignment flags | `DUPLICATE_FINANCIAL_AUTHORITY` | TUHO SHL principal eligibility period differs from generic rule; project-named flag controls financial output | YES | PR-6 |
| P0-7: DA/covenant gate missing in clean SHL path | `NOT_IMPLEMENTED` | `compute_shareholder_loan_schedules` receives pre-DSRA, pre-DA-gate cash; Sponsor receives too much in clean engine | YES | PR-4 (wires DA gate after PR-3 DSRA) |
| P0-8: CO2 revenue bridge project-identity dispatch | `DUPLICATE_FINANCIAL_AUTHORITY` | CO2 revenue modelled as project-code branch not typed capability; can't be disabled independently | YES | Part of PR-2 cleanup / separate CO2 capability PR |

---

## 13. Minimum Consolidation PR Sequence (Dependency Order)

Dependency ordering from runtime evidence and static analysis:

```
PR-1 (tax adapter)  ──────────────────────────────────────────── independent
PR-2 (typed DA / CO2 dispatch removal) ─── independent ─────────────────────
   │
   ├── PR-3 (DSRA in clean engine) ── requires PR-2 DA structure
   │      │
   │      └── PR-4 (wire DA covenant gate into SHL path) ── requires PR-2 + PR-3
   │             │
   │             └── PR-6 (typed ShlRepaymentPolicy) ─── requires PR-4
   │
   └── PR-5 (EBITDA floor alignment decision) ─── independent but cross-engine

PR-7 (typed Bank Case policy) ─── requires PRs 1–6 complete
   │
   └── PR-8 (TUHO/Oborovo production promotion + legacy retirement) ─── requires PR-7
          │
          └── Construction Runtime Promotion ─── requires PR-8
```

| # | PR | Files | Pre-requisites | Risk |
|---|---|---|---|---|
| PR-1 | Fix `loss_utilisation_gate` adapter propagation (`MISSING_ADAPTER_PROPAGATION`) | `financial_engine/adapters/tax_inputs.py` single line | None | Minimal |
| PR-2 | Replace `is_tuho`/`is_oborovo` DA dispatch with typed `CovenantGatePolicy`; remove CO2 identity-dispatch | `finco_core/engine/distribution_account/inputs.py`, `gates.py`, `engine.py`; `app/waterfall_core.py` CO2 branch | None | Medium — DA inputs touched across callers |
| PR-3 | Implement DSRA roll-forward in clean engine | `financial_engine/orchestrator.py`, new `financial_engine/dsra/` | PR-2 (DA gate structure) | Medium |
| PR-4 | Wire DA covenant gate into clean engine SHL path | `financial_engine/orchestrator.py::_run_senior_debt_model_with_shl` | PR-2, PR-3 | Medium — changes SHL-eligible cash routing |
| PR-5 | Resolve EBITDA floor rule (decision: keep `max(0,·)` or remove) | `app/waterfall_core.py` or `financial_engine/orchestrator.py` | Decision required | Low-medium |
| PR-6 | Replace TUHO/Oborovo SHL repayment-alignment flags with typed `ShlRepaymentPolicy` | `finco_core/waterfall/waterfall_engine.py`, `finco_core/shl/engine.py` | PR-4 | Medium |
| PR-7 | Implement typed `DebtSizingCaseInput` (`MISSING_TYPED_BANK_CASE_POLICY` — Base vs Bank separation) | `finco_core/inputs/_models.py`, adapters, clean engine orchestrator | PRs 1–6 | High |
| PR-8 | TUHO + Oborovo clean-engine production promotion; `LEGACY_APP_PRODUCTION_FLOW` authority retirement | `app/ui_runner.py`, `app/waterfall_runner.py`, `app/waterfall_core.py`, runtime-proof tests | PR-7 | Very High — closes P0-1 |

**Note:** PRs 1 and 2 have no mutual dependency and can be developed in parallel. PR-3 must follow PR-2. PR-4 must follow both PR-2 and PR-3. PR-5 can be developed in parallel with PR-3/4 but must be resolved before PR-8. **Single-engine status is only achieved when PR-8 merges.** Construction Runtime Promotion follows after PR-8.

---

## 14. Sponsor Cash Waterfall — Boundary Classification

Each post-senior cash boundary in the current clean engine, classified by authority status:

| Boundary | Clean engine status | Classification |
|---|---|---|
| Base CFADS = EBITDA − cash_tax | Computed by `calculate_canonical_cfads()` | IMPLEMENTED (with EBITDA floor divergence — see P0-3) |
| Senior DS = interest + scheduled principal | Computed by `solve_senior_debt()` fixed point | IMPLEMENTED |
| Post-senior cash = CFADS − Senior DS | Computed in `_run_senior_debt_model_with_shl` as `post_senior_cash` | IMPLEMENTED |
| DSRA reserve deduction | NOT computed; `DSRA_ORDERING_UNRESOLVED` comment at `financial_engine/shl/production.py` lines 45–46 | NOT_IMPLEMENTED (P1-1) |
| DA covenant gate | NOT invoked in clean engine SHL path; `cash_available_for_shl_before_reserves_keur` is pre-DSRA and pre-gate | NOT_IMPLEMENTED (P0-7 `PRE_RESERVE_SHL_CASH_AUTHORITY_GAP`) |
| Sponsor-eligible cash after DA | Incorrectly equals `post_senior_cash` (no DSRA or DA gate applied) | DUPLICATE_FINANCIAL_AUTHORITY — clean engine overstates vs legacy |
| SHL interest accrual | Computed by `compute_shareholder_loan_schedules()` | IMPLEMENTED |
| SHL principal sweep | Computed; uses typed `ShlRepaymentPolicy` | IMPLEMENTED — but receives wrong (too large) input cash due to missing DSRA/DA gate |
| Dividend / residual | Not explicitly computed; implied residual after SHL | NOT_IMPLEMENTED |

---

## 15. Recommendation: Sponsor Waterfall First or Construction Runtime First

**Recommendation: CASH_DSRA + Sponsor Waterfall / Distribution Covenant + SHL repayment promotion FIRST.**

| Factor | Sponsor Waterfall | Construction Runtime |
|---|---|---|
| Clean engine completeness | Senior + SHL fixed point complete; only DA gate + DSRA missing | PRO_RATA construction timing has open `GAP 3` dependency |
| G2C model status | Implemented, source-proven, not wired | Partially implemented |
| Blocking dependency | None beyond PR-1 fix | `construction_period_uses_keur` multi-period gap |
| Project-identity dispatch eliminated | Yes — removes `is_tuho`/`is_oborovo` DA flags and TUHO SHL flags | No |
| Single-engine status | Sponsor Waterfall (PRs 1–6) removes blocking gaps. Single-engine status is achieved only after PR-7 (typed Bank Case) + PR-8 (production promotion). | No — legacy still needed for pre-COD periods; blocked until after PR-8 |
| `PRE_RESERVE_SHL_CASH_AUTHORITY_GAP` resolved | Yes — DA gate wiring (PR-4) closes this seam (identified in KUPI diagnostic) | No |

**Sponsor Waterfall (PRs 1–6) is the first major consolidation implementation block.** It removes the blocking semantic, policy, and waterfall gaps — but does NOT by itself produce a single production engine. Single-engine status is only achieved after:

1. **PR-7**: typed Bank Case / Base-vs-Bank separation (prerequisite for promotion)
2. **PR-8**: TUHO + Oborovo production authority migration to the clean engine

Construction Runtime Promotion then follows PR-8 on a clean single-engine foundation.

---

*Audit produced: 2026-08-19. Base main SHA: `a53cc28a8bb6ab7eb68b47831676d971583cc2a4`. No production files modified.*
