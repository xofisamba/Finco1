# Finco One v2 — Controlled Extraction Plan

**Document type**: Engineering Blueprint (Planning Only)  
**Base branch**: `main` @ `4787207f8de356369dfc4f1592b92af1a0403912`  
**Date**: 2026-07-04  
**Status**: For review — no implementation authorised until ratified

---

## Part 1 — Executive Summary

### What is Controlled Extraction?

Controlled Extraction is the process of lifting the proven financial engine out of the current application shell — preserving every validated formula, every parity result, and every invariant — while replacing the surrounding architecture with a clean, independently deployable structure.

It is not a rewrite. The core mathematical objects (`domain/waterfall/`, `domain/tax/`, `domain/shl/`, `domain/financing/`, `domain/revenue/`, `domain/inputs.py`) are moved, not reimplemented. Their behaviour is proven. They travel with their tests.

It is not a continuation of the current shell. The current shell has served its purpose: it produced two production-calibrated projects, a canonical formula registry, 58 passing invariant tests, and a complete parity programme. Its architecture — a Streamlit monolith with mixed financial and UI responsibilities — is unsuitable for production SaaS.

### Why not a rewrite?

A rewrite discards proven behaviour and restarts the parity clock from zero. The financial engine in this codebase has been calibrated against Excel Golden Models for two production projects (TUHO Wind 1, Oborovo Solar) over a structured programme of 20+ stacks. That calibration work took months. Recreating it from scratch for a rewritten engine is the single highest-risk action available.

The controlled extraction preserves:
- every verified financial formula (frozen per Stack W)
- both Golden Parity baselines (Phase 51F)
- 58 engine invariant tests (Stack X)
- the Phase 0-stabilised runtime capability architecture

### Why not continue the current shell?

The current shell mixes financial engine, persistence, export, UI, and session state concerns in ways that block independent evolution. Specific blockers:

- `app/waterfall_core.py` (1,317 lines) mixes engine orchestration with runtime configuration, post-engine mutation, and audit wiring
- `app/export/calibration_reconciliation.py` (3,409 lines) duplicates financial calculations present in the engine
- `streamlit_app.py` is a direct-render UI that cannot be replaced without restructuring the engine API
- ~400 SQLite `.db` files from phase development persist in the working tree
- The application shell has no stable API contract; the engine and the UI are directly coupled

### Expected engineering outcome

A v2 extraction produces:
- `finco_core/` — a standalone Python package containing the financial engine, input model, and parity fixtures; no Streamlit dependency; no FastAPI dependency; no SQLite dependency
- `finco_app/` — a thin application layer that orchestrates the engine, persists results, and exposes an API
- `finco_ui/` — a UI layer that depends only on the API contract, not on the engine
- A green parity harness that runs against `finco_core` in isolation
- A CI pipeline that fails fast on any parity drift

---

## Part 2 — Legacy Baseline

### Reference

| Field | Value |
|-------|-------|
| Main HEAD SHA | `4787207f8de356369dfc4f1592b92af1a0403912` |
| Date | 2026-07-04 |
| Phase 0 status | Complete (PR #781) |
| Engineering freeze | Active (post Stack AC, post Phase 0) |
| Parity guardrails | GREEN (21/21) |
| Engine invariants | GREEN (58/58) |
| Canonical formulas | Frozen (Stack W, 18 tests) |
| Identity dispatch | Eliminated (Stack AC + Phase 0 Y3) |

### Phase 0 completion record

Phase 0 (PR #781) resolved three pre-extraction blockers:

- **Y3** — Runtime identity guards removed from engine; capability flags are now the sole dispatch mechanism
- **Z1** — Tax bridge taxable income formula corrected to Croatian CIT mathematical basis; TUHO total_tax baseline updated from 45,835 → 35,414 kEUR
- **Z2** — Bridge cash tax moved to reconciliation-only field; `cf_after_tax_keur` inconsistency eliminated

### Purpose of the Legacy Engine Baseline

This SHA is the permanent reference for all v2 extraction work. Every milestone PR must demonstrate:
1. identical engine outputs to this baseline for both reference projects
2. all parity guardrail tests passing
3. all engine invariant tests passing

The Legacy Engine Baseline is not modified during extraction. It is the ground truth.

---

## Part 3 — Repository Inventory

The repository contains approximately 80,000 lines of Python across `app/`, `domain/`, `tests/`, and supporting directories. Classification below uses five categories:

- **Direct Port** — move as-is; test suite travels with it
- **Port With Cleanup** — move with targeted improvements; no formula changes
- **Reference Only** — read during extraction; do not move
- **Archive** — preserve in git history; exclude from v2 working tree
- **Remove** — delete; has no v2 value

### `domain/` — Financial Kernel (Direct Port)

The `domain/` tree is the most valuable asset in the repository. It contains the mathematical engine, validated domain models, and supporting financial calculations.

| Module | Classification | Notes |
|--------|---------------|-------|
| `domain/inputs.py` | Direct Port | ProjectInputs, FinancingParams, ProjectInfo — the canonical config schema |
| `domain/waterfall/waterfall_engine.py` | Direct Port | WaterfallPeriod, WaterfallResult, run_waterfall — the innermost engine |
| `domain/tax/` | Direct Port | TaxEngine, LossCarryforward, holdco calculations — mathematically correct |
| `domain/shl/` | Direct Port | SHL engine, canonical wiring, audit — clean module boundary |
| `domain/financing/` | Direct Port | Sculpting, depreciation schedule, covenants |
| `domain/revenue/` | Direct Port | Revenue generation, tariff, BESS revenue |
| `domain/opex/` | Direct Port | OPEX engine, line items, projections |
| `domain/senior_debt_sizing/` | Direct Port | Canonical debt sizing engine |
| `domain/depreciation/` | Direct Port | Depreciation engine, ledger, tax bridge |
| `domain/returns/xirr.py` | Direct Port | XIRR implementation — frozen formula |
| `domain/returns/xnpv.py` | Direct Port | XNPV implementation — frozen formula |
| `domain/period_engine.py` | Direct Port | Period generation |
| `domain/constants.py` | Direct Port | Financial constants |
| `domain/construction/` | Direct Port | Construction schedule engine |
| `domain/distribution_account/` | Direct Port | DA engine (governance decision pending but engine is correct) |
| `domain/portfolio/independent/` | Direct Port | Independent project portfolio runner |
| `domain/portfolio/holdco/` | Direct Port | Holdco portfolio runner |
| `domain/portfolio/cash_ledger/` | Direct Port | Cash ledger |
| `domain/portfolio/shl/` | Direct Port | Portfolio SHL |
| `domain/portfolio/distribution_constraints/` | Direct Port | Distribution constraints |
| `domain/sponsor/` | Direct Port | Sponsor cashflow, multi-investor waterfall |
| `domain/financial_statements/` | Direct Port | PnL, balance sheet, retained earnings, tax bridge |
| `domain/analytics/` | Direct Port | Sensitivity, scenario analytics, LCOE |
| `domain/finance/sensitivity.py` | Direct Port | Sensitivity analysis |
| `domain/regulatory/` | Direct Port | Regulatory parameters |
| `domain/technology/config.py` | Direct Port | Technology configuration |
| `domain/presets.py` | Port With Cleanup | Remove legacy/hardcoded presets; migrate to factory pattern |
| `domain/models.py` | Port With Cleanup | Review for redundancy with inputs.py |
| `domain/model_state.py` | Port With Cleanup | Evaluate against v2 RunConfiguration design |
| `domain/senior_rate_schedule.py` | Direct Port | Senior rate schedule |
| `domain/senior_sculpting.py` | Direct Port | Senior sculpting |
| `domain/shl_fcf_waterfall.py` | Direct Port | SHL FCF waterfall (legacy path) |
| `domain/debt/debt_config.py` | Direct Port | Debt configuration |
| `domain/diagnostics/` | Reference Only | Diagnostic helpers; not part of engine contract |
| `domain/depreciation_offline/` | Port With Cleanup | Offline depreciation engine; evaluate consolidation with main depreciation module |
| `domain/validation.py` | Port With Cleanup | Input validation — wire into v2 validation layer |
| `domain/reporting/financial_statements.py` | Port With Cleanup | Financial statements reporting layer |

### `app/` — Application Shell (Mixed)

| Module | Classification | Notes |
|--------|---------------|-------|
| `app/waterfall_core.py` | Port With Cleanup | Core engine orchestrator — move to `finco_core/engine/`; the remaining identity guards (AD/AE/AF) are tracked debt |
| `app/waterfall_runner.py` | Port With Cleanup | WaterfallRunner, WaterfallRunConfig — move to `finco_core/engine/`; remove remaining shell coupling |
| `app/project_factories.py` | Port With Cleanup | Move to `finco_core/`; rename TUHO-specific flags (Stack AF deferred work) |
| `app/ui_runner.py` | Reference Only | Legacy Streamlit runner — interface used by tests; superseded in v2 by engine runner |
| `app/period_engine_runner.py` | Port With Cleanup | Move to `finco_core/engine/` |
| `app/input_adapter.py` | Port With Cleanup | Input adaptation layer |
| `app/validation_framework.py` | Port With Cleanup | Move to `finco_core/validation/` |
| `app/validation_status.py` | Port With Cleanup | Move to `finco_core/validation/` |
| `app/services/run_service.py` | Port With Cleanup | Core service — move to `finco_app/services/`; review for engine coupling |
| `app/services/download_service.py` | Port With Cleanup | Move to `finco_app/services/` |
| `app/services/construction_runtime_seam.py` | Port With Cleanup | Move to `finco_app/services/` |
| `app/persistence/` | Port With Cleanup | SQLite repositories — good structure; move to `finco_app/persistence/` |
| `app/api/project_runner.py` | Port With Cleanup | API routes — refactor against clean engine API |
| `app/excel_export.py` | Port With Cleanup | Consolidate with institutional workbook; remove duplicated calculations |
| `app/export/institutional_workbook.py` | Port With Cleanup | Move to `finco_app/exports/` |
| `app/export/calibration_reconciliation.py` | Reference Only | 3,409 lines of calibration helpers; not suitable for v2 as-is; extract the clean export contracts only |
| `app/auth.py` | Port With Cleanup | Move to `finco_app/` |
| `app/cache.py` | Port With Cleanup | Move to `finco_app/` |
| `app/scenario_manager.py` | Port With Cleanup | Move to `finco_app/services/` |
| `app/depreciation_bankable.py` | Port With Cleanup | Move to `finco_core/depreciation/` |
| `app/depreciation_engine.py` | Port With Cleanup | Move to `finco_core/depreciation/` |
| `app/depreciation_audit_visibility.py` | Port With Cleanup | Move to `finco_core/depreciation/` |
| `app/capex_engine.py` | Port With Cleanup | Move to `finco_core/capex/` |
| `app/run_metadata.py` | Port With Cleanup | Move to `finco_app/` |
| `app/portfolio_runner.py` | Port With Cleanup | Move to `finco_core/portfolio/` |
| `app/portfolio_orchestrator.py` | Port With Cleanup | Move to `finco_app/services/` |
| `app/sponsor_runner.py` | Port With Cleanup | Move to `finco_core/sponsor/` |
| `app/input_schema.py` | Port With Cleanup | Move to `finco_core/inputs/` |
| `app/calibration.py` | Reference Only | Calibration helpers — superseded by Phase 51F guardrails |
| `app/calibration_runner.py` | Reference Only | Same |
| `app/demo_presets.py` | Reference Only | Superseded by project factories |
| `app/streamlit_compat.py` | Archive | Streamlit compatibility shim — not needed in v2 |
| `app/output_tables.py` | Archive | UI-specific output formatting |
| `app/input_forms.py` | Archive | Streamlit input forms |
| `app/input_helpers.py` | Archive | Streamlit helpers |
| `app/session_state.py` | Archive | Streamlit session state |
| `app/tax_ui.py` | Archive | Streamlit tax UI |
| `app/holdco_tax_ui.py` | Archive | Streamlit holdco UI |
| `app/portfolio_ui.py` | Archive | Streamlit portfolio UI |
| `app/portfolio_ui_overlay.py` | Archive | Streamlit portfolio overlay |
| `app/ui/` | Archive | C-series spreadsheet-native UI components (separate evolution track) |
| `app/tax_excel_export.py` | Port With Cleanup | Move to `finco_app/exports/` |
| `app/tax_assumptions_excel_export.py` | Port With Cleanup | Move to `finco_app/exports/` |
| `app/sponsor_waterfall_excel_export.py` | Port With Cleanup | Move to `finco_app/exports/` |
| `app/holdco_tax_excel_export.py` | Port With Cleanup | Move to `finco_app/exports/` |
| `app/export_metadata.py` | Port With Cleanup | Move to `finco_app/exports/` |
| `app/merchant_curves.py` | Port With Cleanup | Move to `finco_core/revenue/` |
| `app/opex_engine.py` | Port With Cleanup | Move to `finco_core/opex/` |
| `app/sponsor_project_adapter.py` | Port With Cleanup | Move to `finco_core/sponsor/` |
| `app/runtime_impact_taxonomy.py` | Port With Cleanup | Move to `finco_core/` |
| `app/logging_config.py` | Port With Cleanup | Move to `finco_app/` |
| `app/observability.py` | Port With Cleanup | Move to `finco_app/` |

### `tests/` — Test Suite

See Part 8 for full test migration plan.

### `docs/` — Documentation

| Document | Classification | Notes |
|----------|---------------|-------|
| `CANONICAL_FORMULA_REGISTRY.md` | Direct Port | First-class asset; travels to v2 |
| `POST_AC_ARCHITECTURE_STABILIZATION_BASELINE.md` | Direct Port | Permanent engineering reference |
| `PHASE0_PRE_EXTRACTION_HOTFIX.md` | Direct Port | Pre-extraction record |
| `STACK_AB_ENGINE_ARCHITECTURE_CLEANUP.md` | Direct Port | Identity guard inventory |
| `STACK_AC_RUNTIME_IDENTITY_PHASE1.md` | Direct Port | Config-over-identity record |
| `STACK_Z_TAX_DEPRECIATION_RUNTIME.md` | Direct Port | Tax depreciation record |
| `STACK_T_TAX_ARCHITECTURE_DECISION.md` | Direct Port | Tax architecture decision |
| `TEST_SUITE_RATIONALIZATION.md` | Direct Port | Stack AA census |
| `EXCEL_PARITY_STACK_P_FINAL_AUDIT.md` | Direct Port | Parity final audit |
| `EXCEL_PARITY_STACK_Q_OBOROVO_DSCR_CFADS.md` | Direct Port | Oborovo parity record |
| `EXCEL_PARITY_GAP_INVENTORY.md` | Direct Port | Known parity gaps |
| `ARCHITECTURE.md` | Reference Only | Current architecture overview |
| `C1_*.md`, `C2_*.md` | Archive | UI-series implementation notes (UI concern, separate track) |
| `EXCEL_PARITY_STACK_D/E/F/G/H/I.md` | Archive | Superseded by golden parity programme |
| `STACK_R/S/U/V.md` | Reference Only | Audit/export records |

### `scripts/` — Calibration Scripts

| Module | Classification | Notes |
|--------|---------------|-------|
| `scripts/export_phase10_*.py` | Archive | Phase 10 calibration scripts |
| `scripts/export_phase*.py` | Archive | Historical phase exports |
| `scripts/extract_generic_golden*.py` | Reference Only | Golden extraction helpers |
| `scripts/run_calibration.py` | Reference Only | Calibration runner |
| `scripts/validate_publish_package.py` | Port With Cleanup | Package validation |

### `reporting/` — Legacy Export Layer

| Module | Classification | Notes |
|--------|---------------|-------|
| `reporting/excel_export.py` | Reference Only | Legacy Excel export; superseded by app/export/ |
| `reporting/fid_deck.py` | Reference Only | FID deck generator |
| `reporting/pdf_export.py` | Reference Only | PDF export |

### `reports/` — Generated Artifacts

| Item | Classification | Notes |
|------|---------------|-------|
| `reports/phase7_tuho_*.csv` | Direct Port | Golden fixture — parity-locked |
| `reports/phase23q_oborovo_*.csv` | Direct Port | Golden fixture — parity-locked |
| All other `reports/` CSVs | Archive | Calibration artifacts; not needed in v2 |
| `reports/*.xlsx` | Archive | Generated Excel workbooks |

### Root-level `.db` files

| Item | Classification | Notes |
|------|---------------|-------|
| `phase15_e2e_*.db`, `phase17d_*.db`, `phase20f_*.db`, etc. (~400 files) | Remove | Phase development SQLite artifacts; no v2 value; clutter the working tree |
| `data.db`, `finco.db` | Reference Only | May contain reference data; inspect before removing |

### `utils/`, `tools/`, `validation/`, `static/`

| Module | Classification | Notes |
|--------|---------------|-------|
| `utils/export.py` | Port With Cleanup | Move to `finco_app/exports/` |
| `utils/` other | Port With Cleanup | Evaluate per-file |
| `tools/` | Reference Only | Development tooling |
| `validation/` | Port With Cleanup | Move to `finco_core/validation/` |
| `static/` | Archive | Streamlit static assets |

---

## Part 4 — Target v2 Architecture

```
finco_core/                          # Standalone Python package — no web dependencies
    inputs/
        project_inputs.py            # ProjectInputs, FinancingParams, ProjectInfo
        financing_params.py          # FinancingParams
        validation.py                # Input validation
    engine/
        waterfall_core.py            # run_waterfall_v3_core (renamed: run_waterfall)
        waterfall_runner.py          # WaterfallRunner, RunConfiguration
        period_engine.py             # Period generation
        result.py                    # WaterfallResult, WaterfallPeriod (from domain/waterfall/)
    revenue/
        generation.py
        tariff.py
        bess.py
        hybrid.py
    opex/
        engine.py
        line_items.py
        projections.py
    capex/
        engine.py
        breakdown.py
        schedule.py
        idc.py
    construction/
        engine.py
        schedule.py
        opening_bridge.py
    debt/
        senior_debt_sizing/
        sculpting/
        schedule.py
        covenants.py
    depreciation/
        engine.py
        schedule.py
        tax_bridge.py
        bankable.py
    tax/
        engine.py
        loss_carryforward.py
        holdco.py
        templates/
    shl/
        engine.py
        canonical_wiring.py
        audit.py
    waterfall/
        engine.py                    # Inner waterfall (domain/waterfall/waterfall_engine.py)
        distribution_account.py
    sponsor/
        cashflow_runner.py
        multi_investor_waterfall.py
    portfolio/
        independent/
        holdco/
        cash_ledger/
        distribution_constraints/
    analytics/
        sensitivity.py
        scenarios.py
        monte_carlo.py
        lcoe.py
    returns/
        xirr.py
        xnpv.py
    audit/
        field_registry.py            # Typed audit field definitions
        reconciliation.py            # Reconciliation-only calculations
    exports/
        contracts.py                 # Typed export contracts (no financial logic)
    factories/
        tuho_wind1.py                # create_default_tuho_wind1()
        oborovo_solar.py             # create_default_oborovo()
    constants.py

finco_app/                           # Application layer — FastAPI + persistence
    api/
        projects.py
        scenarios.py
        runs.py
        exports.py
        auth.py
    services/
        run_service.py
        scenario_service.py
        download_service.py
        construction_seam.py
    persistence/
        projects_repository.py
        scenarios_repository.py
        runs_repository.py
        exports_repository.py
        capex_sub_lines.py
    exports/
        excel/
            institutional_workbook.py
            tax_assumptions.py
            sponsor_waterfall.py
            holdco_tax.py
        pdf/
    auth.py
    cache.py
    observability.py
    logging_config.py

parity/                              # Golden parity harness — runs against finco_core in isolation
    fixtures/
        tuho/
            phase7_tuho_senior_debt_sizing_extraction.csv  # parity-locked
        oborovo/
            phase23q_oborovo_senior_debt_sizing_extraction.csv  # parity-locked
    golden/
        tuho_golden.py               # TUHO parity targets and tolerances
        oborovo_golden.py            # Oborovo parity targets and tolerances
    regression/
        test_phase51f_guardrails.py  # SHA-pinned parity guardrail (from test_phase51f_*)
        test_engine_invariants.py    # 58 invariant tests (from test_stack_x_*)
        test_canonical_formulas.py   # Formula registry tests (from test_stack_w_*)

finco_ui/                            # UI layer — depends only on finco_app API
    (C-series spreadsheet-native UI or replacement)
    (Separate evolution track — not in scope for extraction milestones V2-1 through V2-6)
```

**Rationale for this structure:**

`finco_core` has zero web dependencies. `pip install finco-core` should work in a Python environment with no FastAPI, no Streamlit, no SQLite. This enables:
- engine tests that run in 2 seconds on a laptop
- independent versioning of the engine
- embedding in downstream tools without the full application stack

`parity/` is a first-class top-level package, not a subdirectory of tests. This reflects its status as a contractual guarantee: parity fixtures are assets, not test helpers.

`finco_ui` is scoped separately. The C-series spreadsheet-native UI work is an independent track and is not blocked by or blocking extraction. The API contract (Part 11) is what connects them.

---

## Part 5 — Runtime Architecture

### Canonical execution pipeline

```
ProjectInputs (finco_core/inputs/)
    │  Validated configuration object — frozen dataclass
    │  No identity dispatch; all behaviour controlled by capability flags
    ▼
RunConfiguration (finco_core/engine/waterfall_runner.py)
    │  WaterfallRunConfig — frozen dataclass, capability-driven
    │  Built from ProjectInputs via from_inputs()
    │  No project_code field; no project_name field
    ▼
FinancialEngine (finco_core/engine/waterfall_core.py)
    │  run_waterfall() — pure function
    │  Input: ProjectInputs + PeriodEngine + RunConfiguration
    │  Output: WaterfallResult
    │  No side effects; no file I/O; no database access; no UI coupling
    ▼
WaterfallResult (finco_core/engine/result.py)
    │  Typed, immutable result object
    │  All financial outputs accessible as named attributes
    │  No post-engine mutation permitted
    ▼
Audit Layer (finco_core/audit/)
    │  Reads WaterfallResult fields
    │  Produces AuditSnapshot — typed, serialisable
    │  Reconciliation calculations classified as audit-only
    │  (cash_tax_bridge_reconciliation_keur is the pattern)
    ▼
Export Layer (finco_app/exports/)
    │  Reads AuditSnapshot and WaterfallResult
    │  No financial calculations
    │  All exported values traced to engine outputs
    ▼
API Layer (finco_app/api/)
    │  Orchestrates: receive request → load inputs → run engine → persist → return result
    │  Serialises WaterfallResult to JSON response
    │  No financial logic in API layer
    ▼
UI Layer (finco_ui/)
    │  Reads API responses
    │  Displays, edits, launches
    │  No financial calculations
```

### Requirements

**No identity dispatch.** The engine must not branch on project name, code, seed, or any string identity. Capability flags in `ProjectInfo` and `FinancingParams` are the only routing mechanism. This is enforced by Phase 0 Y3 and Stack AC and must be preserved permanently.

**No post-engine mutation.** `WaterfallResult` must be immutable after the engine returns. Any supplementary calculation (e.g. bridge reconciliation) produces a new typed object, not a mutation of the result. The Z2 pattern (`cash_tax_bridge_reconciliation_keur` as a separate audit field) is the model.

**No runtime reads from `tests/`.** The engine must not load fixtures from the test tree at runtime. Golden fixtures (`phase7_tuho_*.csv`, `phase23q_oborovo_*.csv`) travel to `parity/fixtures/` and are referenced via `FinancingParams.frozen_senior_ds_fixture_path`. The engine reads from config, not from test paths.

**Typed result objects.** `WaterfallResult` and `WaterfallPeriod` are typed dataclasses. All downstream consumers receive typed objects, not raw dicts or untyped float arrays.

**One execution path.** There is one entry point to the engine: `run_waterfall(inputs, engine, config)`. There is no `run_waterfall_v1`, `run_waterfall_v2`, `run_waterfall_legacy`. Version transitions are stack-level decisions, not branch points in the runtime.

---

## Part 6 — Financial Engine

### Immutable financial kernels

The following are mathematically frozen. They must not change without a formal architecture decision, a new stack, and updated parity targets:

| Kernel | Location | Frozen Since |
|--------|----------|-------------|
| XIRR/XNPV | `domain/returns/xirr.py`, `xnpv.py` | Stack L |
| DSCR formula | `domain/waterfall/waterfall_engine.py` | Stack K |
| LCF engine (5-year rolling, Croatian §16) | `domain/tax/loss_carryforward.py` | Stack T |
| Senior debt sizing (DS!R57 basis) | `domain/senior_debt_sizing/` | Stack K |
| SHL balance, accrual, PIK-then-sweep | `domain/shl/` | Stack M/N |
| Distribution waterfall, DA gate | `domain/waterfall/waterfall_engine.py` | Stack Q |
| Tax bridge formula (EBITDA − tax_dep − deductible + fiscal) | `app/waterfall_core.py` | Phase 0 Z1 |

### Configurable policies

The following are engine behaviours controlled by capability flags. They can be enabled or disabled per project via `ProjectInfo` or `FinancingParams`:

| Policy | Flag | Default |
|--------|------|---------|
| Tax depreciation bridge | `use_tax_bridge_engine` | False |
| Frozen senior DS fixture | `use_frozen_excel_senior_debt_schedule` + `frozen_senior_ds_fixture_path` | False / None |
| Senior debt sizing engine | `use_senior_debt_sizing_engine` | False |
| SHL gross accrued P&L | `use_shl_gross_accrued_for_pnl` | False |
| SHL repayment alignment | `use_tuho_shl_repayment_alignment` | False |
| R99 input engine | `use_tuho_r99_input_engine` | False |
| CO2 revenue bridge | `use_co2_revenue_bridge` | False |
| CO2 CIT bridge | `use_co2_cit_bridge` | False |
| Construction schedule engine | `use_construction_schedule_engine` | False |
| OPEX line item engine | `use_opex_line_item_engine` | False |

In v2, TUHO-specific flag names (`use_tuho_*`) are renamed to generic equivalents per Stack AF. The renaming is mechanical and does not affect financial behaviour.

### Runtime capabilities

`WaterfallRunConfig` carries the resolved capability set for a single run. It is a frozen dataclass built from `ProjectInputs` via `from_inputs()`. It contains no project identity fields. It is deterministic: same inputs → same config.

### Reconciliation-only calculations

Some calculations appear in the engine output but are not inputs to any financial computation. They exist for audit and Excel reconciliation purposes:

| Field | Classification |
|-------|---------------|
| `cash_tax_bridge_reconciliation_keur` | Reconciliation-only (Phase 0 Z2) |
| `r67_excel_style_cash_tax_diagnostic_keur` | Reconciliation-only diagnostic |
| `r69_fcf_banks_keur`, `r84_fcf_junior_keur` | Audit-only (R99 engine) |
| `cit_accrual_audit_keur` | Audit-only |

These fields travel to `finco_core/audit/` and are clearly labelled. They must not be used as inputs to IRR, DSCR, distribution, or tax computations.

### Financial logic vs presentation logic

The distinction is structural, not just philosophical:

**Financial logic** (lives in `finco_core`):
- Any calculation that affects IRR, DSCR, total_tax, total_distributions, equity_irr, or project_irr
- Any calculation that feeds into another financial calculation
- Any formula that appears in the canonical formula registry

**Presentation logic** (lives in `finco_app` or `finco_ui`):
- Formatting numbers for display
- Generating Excel cell labels
- Selecting which fields to show in a UI panel
- Computing UI-only aggregates (e.g. "total for display purposes")
- Export column ordering

The failure mode to avoid: financial calculations embedded in `app/export/` or `app/ui/` that are not in the engine. These create silent divergence between what the engine computed and what the user sees.

---

## Part 7 — Parity Strategy

### Golden fixtures

Two projects are parity-locked. Their fixtures travel from `reports/` to `parity/fixtures/`:

**TUHO Wind 1** (Croatian onshore wind, 30-year, semiannual):
- Fixture: `parity/fixtures/tuho/phase7_tuho_senior_debt_sizing_extraction.csv`
- Referenced via: `FinancingParams.frozen_senior_ds_fixture_path`

**Oborovo Solar PV** (Croatian solar, 30-year, semiannual):
- Fixture: `parity/fixtures/oborovo/phase23q_oborovo_senior_debt_sizing_extraction.csv`
- Referenced via: `FinancingParams.frozen_senior_ds_fixture_path`

### Parity targets (Phase 0 Z1 baseline)

| Project | KPI | Target | Tolerance |
|---------|-----|--------|-----------|
| TUHO Wind 1 | Equity IRR | 11.32% | ±0.05% |
| TUHO Wind 1 | Actual avg DSCR | 1.3786 | ±0.001 |
| TUHO Wind 1 | Total tax | 35,414 kEUR | ±500 kEUR |
| TUHO Wind 1 | Total distributions | 165,471 kEUR | ±200 kEUR |
| Oborovo Solar | Equity IRR | 10.54% | ±0.05% |
| Oborovo Solar | Actual avg DSCR | 1.179 | ±0.005 |
| Oborovo Solar | Total tax | 8,874 kEUR | ±100 kEUR |

Note: Total tax targets reflect the Phase 0 Z1 formula correction. The Pre-Phase-0 values (45,835 / 8,874) are no longer valid baselines.

### Tolerance policy

Parity tolerances are set per-KPI and are not negotiable without a stack-level decision. Any extraction milestone that moves a KPI outside tolerance is a regression, regardless of how small the change. The Phase 51F guardrail test file is the enforcement mechanism.

### Regression testing

`parity/regression/test_phase51f_guardrails.py` (ported from `tests/test_phase51f_parallel_work_guardrails.py`) must:
- run against `finco_core` in isolation (no app layer required)
- SHA-pin `finco_core/engine/waterfall_core.py` and `finco_core/factories/`
- fail immediately on any change to parity-sensitive files without a documented changelog entry

### Versioning

Parity baselines are versioned by SHA, not by semantic version. When a formula changes (Stack-level decision), the relevant SHA pin is updated with a changelog entry recording:
- why the formula changed
- what the old and new values are
- which stacks the change relates to

### Intentional divergence from Excel

The following differences between Finco and Excel are permanent engineering decisions:

**Croatian 5-year Loss Carryforward (Finco correct; Excel wrong)**
- Finco: 5-year rolling window, semiannual periods, `expire_before_use=True` (Croatian §16 correct)
- Excel: perpetual LCF (legally incorrect)
- Effect: −5,271 kEUR residual in TUHO lifetime cash CIT vs Excel
- Position: Do not calibrate to Excel's mistake. This divergence is documented and intentional.

**Tax Depreciation Basis (corrected in Phase 0 Z1)**
- Finco: `EBITDA − tax_dep − deductible_interest + fiscal_reintegration` (Croatian CIT correct)
- Previous Finco: used book_dep incorrectly (Phase 0 Z1 fix)
- The Excel Golden Model's tax computation aligns with the corrected formula

**General principle**: Where Excel and Finco differ because Excel is methodologically wrong, Finco keeps the correct treatment, documents the residual, and does not calibrate to the Excel mistake. This is a permanent engineering position established during the K–Q parity programme.

---

## Part 8 — Test Migration

### Categories

| Category | Count (approx) | Action |
|----------|---------------|--------|
| Engine invariants (`test_stack_x_*`) | 58 tests / 1 file | **Immediate Port** → `parity/regression/test_engine_invariants.py` |
| Parity guardrails (`test_phase51f_*`) | 21 tests / 1 file | **Immediate Port** → `parity/regression/test_phase51f_guardrails.py` |
| Canonical formulas (`test_stack_w_*`) | 18 tests / 1 file | **Immediate Port** → `parity/regression/test_canonical_formulas.py` |
| Phase 0 tests (`test_phase0_*`) | 17 tests / 1 file | **Immediate Port** → `parity/regression/test_phase0_hotfixes.py` |
| Stack AB/AC tests | ~63 tests / 2 files | **Immediate Port** → `parity/regression/` |
| Stack Z tests | ~30 tests / 1 file | **Immediate Port** → `parity/regression/` |
| Golden parity (Stack P, Q, T) | ~70 tests | **Immediate Port** → `parity/regression/` |
| Core engine unit tests | ~200 tests | **Immediate Port** → `finco_core/tests/` |
| Domain module tests (tax, SHL, debt, LCF, etc.) | ~400 tests | **Immediate Port** → per-module `tests/` |
| API tests (`test_api.py`) | ~30 tests | **Rewrite** → against v2 API contracts |
| Auth tests (`test_auth_lite.py`) | ~20 tests | **Rewrite** → against v2 auth layer |
| C1-series tests (spreadsheet grid) | ~180 tests | **UI-only** → `finco_ui/tests/` (separate track) |
| C1-series browser tests (`*_browser.py`) | ~90 tests | **Browser-only** → `finco_ui/tests/browser/` |
| C2-series tests (preview architecture) | ~150 tests | **UI-only** → `finco_ui/tests/` (separate track) |
| C2-series browser tests | ~60 tests | **Browser-only** → `finco_ui/tests/browser/` |
| Portfolio tests | ~80 tests | **Immediate Port** → `finco_core/portfolio/tests/` |
| BESS tests | ~30 tests | **Rewrite** (BESS pre-existing failure) |
| Phase development tests (Stack D/E/F/G/H/I) | ~100 tests | **Archive** → superseded by golden parity |
| Legacy/disabled tests | ~50 tests | **Delete** |
| `tests/reconciliation_helpers.py` | 1 file | **Port With Cleanup** |

### CI pipeline design

```
CI Pipeline (v2)

┌─────────────────────────────────────────────────────┐
│  Stage 1: finco_core unit tests (~2 seconds)        │
│  - No web server; no database; no fixtures          │
│  - Engine unit tests, formula tests, domain tests   │
└────────────────────────┬────────────────────────────┘
                         │ pass
┌────────────────────────▼────────────────────────────┐
│  Stage 2: parity regression (~10 seconds)           │
│  - test_phase51f_guardrails.py                      │
│  - test_engine_invariants.py                        │
│  - test_canonical_formulas.py                       │
│  - Runs against finco_core only                     │
│  - FAILS FAST on any parity drift                   │
└────────────────────────┬────────────────────────────┘
                         │ pass
┌────────────────────────▼────────────────────────────┐
│  Stage 3: app integration tests (~30 seconds)       │
│  - API tests, service tests, persistence tests      │
│  - Requires running finco_app                       │
└────────────────────────┬────────────────────────────┘
                         │ pass
┌────────────────────────▼────────────────────────────┐
│  Stage 4: UI tests (~2 minutes)                     │
│  - Playwright browser tests for finco_ui            │
│  - Runs last; slowest; optional on feature branches │
└─────────────────────────────────────────────────────┘
```

---

## Part 9 — Export Architecture

### Principle

Every exported value must be traceable to a named attribute of `WaterfallResult` or `WaterfallPeriod`. No export file may contain financial calculations not already present in the engine result.

### Three tiers of export data

**Economic values** — directly from engine outputs:
- `equity_irr`, `project_irr`, `actual_avg_dscr`
- `total_distribution_keur`, `total_tax_keur`, `total_senior_ds_keur`
- Per-period: `revenue_keur`, `opex_keur`, `ebitda_keur`, `tax_keur`, `distribution_keur`

**Reconciliation values** — audit fields computed alongside the engine:
- `cash_tax_bridge_reconciliation_keur` (bridge cash tax, Phase 0 Z2)
- `r67_excel_style_cash_tax_diagnostic_keur`
- `r69_fcf_banks_keur`, `r98_distribution_account_keur`
- All `*_audit_keur` fields

**Audit values** — structural and metadata fields:
- Period dates, indices, period-in-year flags
- Fixture wiring state (`_frozen_senior_ds_wired`)
- Run metadata (SHA, timestamp, configuration)

### Export contract

```python
# finco_core/exports/contracts.py (v2 design)

@dataclass(frozen=True)
class EconomicSummary:
    equity_irr: float
    project_irr: float
    actual_avg_dscr: float
    total_distribution_keur: float
    total_tax_keur: float
    total_senior_ds_keur: float

@dataclass(frozen=True)
class PeriodExportRow:
    period: int
    date: date
    revenue_keur: float
    opex_keur: float
    ebitda_keur: float
    tax_keur: float
    dscr: float
    distribution_keur: float
    # ... all other engine period fields

@dataclass(frozen=True)
class AuditExportRow:
    period: int
    # reconciliation and audit fields only
    cash_tax_bridge_reconciliation_keur: float
    r67_excel_style_cash_tax_diagnostic_keur: float
    # ...
```

The export layer reads these contracts. It does not read `WaterfallResult` directly.

### Consolidation

The current codebase has at least five partially overlapping export pipelines:
- `app/excel_export.py` (1,448 lines)
- `app/export/calibration_reconciliation.py` (3,409 lines)
- `app/export/institutional_workbook.py` (1,225 lines)
- `reporting/excel_export.py`
- Various `app/tax_*_excel_export.py`

In v2, these collapse to a single `finco_app/exports/` pipeline driven by typed contracts from `finco_core`. The calibration reconciliation helpers are Reference Only and are not ported — only the export contracts that serve production use cases travel.

---

## Part 10 — Persistence

### Minimum persistence model

Six entities. No premature complexity.

```sql
-- Project: a named financial model
CREATE TABLE projects (
    id          TEXT PRIMARY KEY,       -- UUID
    name        TEXT NOT NULL,
    code        TEXT,
    created_at  TIMESTAMP NOT NULL,
    updated_at  TIMESTAMP NOT NULL,
    inputs_json JSONB NOT NULL          -- serialised ProjectInputs
);

-- Scenario: a named variant of project inputs
CREATE TABLE scenarios (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(id),
    name        TEXT NOT NULL,
    created_at  TIMESTAMP NOT NULL,
    delta_json  JSONB NOT NULL          -- serialised delta from base inputs
);

-- Run: a completed engine execution
CREATE TABLE runs (
    id            TEXT PRIMARY KEY,
    scenario_id   TEXT NOT NULL REFERENCES scenarios(id),
    ran_at        TIMESTAMP NOT NULL,
    engine_sha    TEXT NOT NULL,        -- waterfall_core.py SHA at run time
    inputs_sha    TEXT NOT NULL,        -- SHA of the inputs used
    result_json   JSONB NOT NULL        -- serialised WaterfallResult (economic fields)
);

-- AuditSnapshot: full period-level audit trail for a run
CREATE TABLE audit_snapshots (
    id      TEXT PRIMARY KEY,
    run_id  TEXT NOT NULL REFERENCES runs(id),
    data    JSONB NOT NULL             -- serialised list[AuditExportRow]
);

-- Export: a generated export file
CREATE TABLE exports (
    id         TEXT PRIMARY KEY,
    run_id     TEXT NOT NULL REFERENCES runs(id),
    type       TEXT NOT NULL,          -- "excel_economic", "excel_audit", "pdf", etc.
    created_at TIMESTAMP NOT NULL,
    file_path  TEXT NOT NULL
);

-- User: minimal auth
CREATE TABLE users (
    id            TEXT PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMP NOT NULL,
    last_login    TIMESTAMP
);
```

### Notes

- `inputs_json` stores the full `ProjectInputs` as a serialised JSON blob. No column-per-field schema: the input model evolves faster than a normalised schema can track.
- `delta_json` in scenarios stores only the changed fields relative to the base project; the full inputs are reconstructed at run time.
- `result_json` in runs stores the economic summary fields only (IRR, DSCR, distributions, tax). Full period-level data lives in `audit_snapshots`.
- `engine_sha` pins the engine version at run time. If the engine is subsequently updated, the run can be flagged as produced by a different engine version.

---

## Part 11 — UI/API Boundary

### API responsibilities

The API layer (`finco_app/api/`) owns:
- **Orchestration**: receive request → validate inputs → build RunConfiguration → call engine → persist result → return response
- **Input validation**: validate `ProjectInputs` before passing to engine
- **Serialisation**: convert typed engine results to JSON responses; convert JSON requests to typed input objects
- **Auth**: authenticate requests; enforce rate limits
- **Error handling**: translate engine exceptions to structured API errors

The API does not:
- calculate financial values
- format numbers for display
- make assumptions about UI rendering

### UI responsibilities

The UI layer (`finco_ui/`) owns:
- **Display**: render API responses as visual components
- **Input editing**: collect user edits and submit to API
- **Run initiation**: call the run endpoint; display progress; show results when complete
- **Export download**: request export files via API; trigger browser download

The UI does not:
- calculate finance
- mutate engine results
- perform parity logic
- format financial values independently of the API response

### API contract (minimal v2 shape)

```
POST   /api/projects                     → create project
GET    /api/projects/{id}                → get project inputs
PUT    /api/projects/{id}                → update project inputs
POST   /api/projects/{id}/scenarios      → create scenario
POST   /api/scenarios/{id}/run           → run engine → RunResponse
GET    /api/runs/{id}                    → get run result
GET    /api/runs/{id}/audit              → get audit snapshot
POST   /api/runs/{id}/export/{type}      → generate export
GET    /api/exports/{id}                 → download export
```

`RunResponse` contains `EconomicSummary` + run metadata. It does not contain the full period-level data (that is in the audit snapshot).

---

## Part 12 — Migration Roadmap

Each milestone is one PR. PRs are independent: V2-1 does not break the legacy application. The legacy application continues to run from the Legacy Engine Baseline until V2-7 (minimal UI shell) is complete.

---

### V2-1 — Core Package Skeleton

**Branch**: `v2-1-core-package-skeleton`  
**Objective**: Create the `finco_core/` Python package with correct directory structure, `pyproject.toml`, and empty `__init__.py` files. No logic moved yet.

**Expected files**:
- `finco_core/__init__.py`
- `finco_core/inputs/__init__.py`
- `finco_core/engine/__init__.py`
- `finco_core/tax/__init__.py`
- `finco_core/shl/__init__.py`
- `finco_core/waterfall/__init__.py`
- `finco_core/exports/contracts.py` (typed export contract stubs)
- `finco_core/audit/__init__.py`
- `finco_core/factories/__init__.py`
- `finco_core/pyproject.toml` (or top-level `pyproject.toml` with workspace support)
- `parity/__init__.py`
- `parity/fixtures/tuho/` (copy of `reports/phase7_tuho_*.csv`)
- `parity/fixtures/oborovo/` (copy of `reports/phase23q_oborovo_*.csv`)

**Risks**: None. Empty package creation.

**Acceptance criteria**:
- `pip install -e finco_core/` succeeds
- `import finco_core` succeeds
- Parity fixtures present in `parity/fixtures/` with SHA verified against legacy baseline
- All existing tests continue to pass (no files moved yet)

**Rollback**: Delete the new directories.

---

### V2-2 — Input Model Extraction

**Branch**: `v2-2-input-model-extraction`  
**Objective**: Copy `domain/inputs.py` to `finco_core/inputs/project_inputs.py`. Add import alias so existing code (`from domain.inputs import ProjectInputs`) continues to work.

**Expected files**:
- `finco_core/inputs/project_inputs.py` (copy of `domain/inputs.py`)
- `finco_core/inputs/__init__.py` (re-export `ProjectInputs`, `FinancingParams`, `ProjectInfo`)
- `domain/inputs.py` modified to re-export from `finco_core.inputs` (backwards compatibility shim)

**Risks**: Import cycle if `domain/inputs.py` imports from `finco_core` which imports from `domain`. Mitigate by making `finco_core/inputs/` entirely self-contained — no back-references to `domain/`.

**Acceptance criteria**:
- `from finco_core.inputs import ProjectInputs` works
- `from domain.inputs import ProjectInputs` still works (via shim)
- All existing tests pass
- Parity guardrails pass

**Rollback**: Revert `domain/inputs.py` to original; delete `finco_core/inputs/`.

---

### V2-3 — Financial Engine Extraction

**Branch**: `v2-3-financial-engine-extraction`  
**Objective**: Copy the financial engine kernel to `finco_core/engine/`. This is the most critical milestone.

**Expected files**:
- `finco_core/engine/waterfall_core.py` (copy of `app/waterfall_core.py`)
- `finco_core/engine/waterfall_runner.py` (copy of `app/waterfall_runner.py`)
- `finco_core/engine/result.py` (copy of `domain/waterfall/waterfall_engine.py` — WaterfallResult, WaterfallPeriod, run_waterfall)
- `finco_core/engine/period_engine.py` (copy of `domain/period_engine.py`)
- Copies of all `domain/` engine dependencies (`tax/`, `shl/`, `financing/`, `revenue/`, `opex/`, `depreciation/`, `senior_debt_sizing/`, `returns/`)
- `finco_core/factories/tuho_wind1.py` (copy of TUHO factory from `app/project_factories.py`)
- `finco_core/factories/oborovo_solar.py` (copy of Oborovo factory)
- Import shims in `app/waterfall_core.py`, `app/waterfall_runner.py`, `domain/waterfall/` pointing to `finco_core`

**Risks**:
- Circular import: `finco_core.engine.waterfall_core` must not import from `app/`. Audit all imports before copying.
- Hidden `app/` dependency in `domain/` code: check every `from app import` in `domain/`.
- Test fixtures path: engine reads `frozen_senior_ds_fixture_path` which currently resolves relative to `app/`. In `finco_core`, this path must resolve relative to `parity/fixtures/`.

**Acceptance criteria**:
- Engine can be invoked via `from finco_core.engine import run_waterfall` with no `app/` in import path
- Parity guardrails pass against `finco_core` in isolation
- All 58 invariant tests pass
- All 18 canonical formula tests pass
- Legacy application (`streamlit_app.py`) continues to work via shims

**Rollback**: Revert all shims; delete `finco_core/engine/` and `finco_core/factories/`.

---

### V2-4 — Parity Harness

**Branch**: `v2-4-parity-harness`  
**Objective**: Port the parity test suite to run against `finco_core` in isolation. This is the v2 parity contract.

**Expected files**:
- `parity/regression/test_phase51f_guardrails.py` (port from `tests/test_phase51f_parallel_work_guardrails.py`)
- `parity/regression/test_engine_invariants.py` (port from `tests/test_stack_x_engine_invariants.py`)
- `parity/regression/test_canonical_formulas.py` (port from `tests/test_stack_w_canonical_formulas.py`)
- `parity/regression/test_phase0_hotfixes.py` (port from `tests/test_phase0_pre_extraction_hotfix.py`)
- `parity/regression/test_golden_regression.py` (TUHO + Oborovo golden regression, importing from `finco_core` only)
- `parity/pytest.ini` or `parity/pyproject.toml` for standalone test runner
- CI configuration update: Stage 1 (finco_core unit) + Stage 2 (parity) run independently

**Risks**: Test imports currently assume `app/` paths. All parity test imports must be re-pointed to `finco_core.engine`, `finco_core.factories`, etc.

**Acceptance criteria**:
- `cd parity && pytest regression/` passes with zero failures and zero app/ imports
- Parity harness runs in under 15 seconds
- SHA pins in guardrail test updated to `finco_core/engine/waterfall_core.py`

**Rollback**: Delete `parity/regression/`; the existing `tests/` suite is unaffected.

---

### V2-5 — Audit/Export Contracts

**Branch**: `v2-5-audit-export-contracts`  
**Objective**: Define typed export contracts in `finco_core/exports/contracts.py`. Implement one reference export (the 7-column audit CSV from Stack V) driven purely by contracts.

**Expected files**:
- `finco_core/exports/contracts.py` (EconomicSummary, PeriodExportRow, AuditExportRow dataclasses)
- `finco_core/audit/field_registry.py` (typed audit field definitions)
- `finco_core/audit/assembler.py` (assembles AuditSnapshot from WaterfallResult — no financial calculations)
- `finco_app/exports/audit_csv.py` (reference implementation: Stack V 7-column CSV)
- Tests: `tests/test_v2_export_contracts.py` — verify every exported field traces to a WaterfallResult attribute

**Risks**: Discovering that current export code contains financial calculations not in the engine. If found, those calculations must either be moved to the engine (financial logic) or removed (if they were errors).

**Acceptance criteria**:
- `EconomicSummary` and `PeriodExportRow` constructed from `WaterfallResult` without any arithmetic
- 7-column audit CSV matches Stack V reference output
- All exported values traceable to named engine fields (test enforces this)

**Rollback**: Delete `finco_core/exports/contracts.py` and `finco_core/audit/`; the existing export pipeline is unaffected.

---

### V2-6 — Minimal API

**Branch**: `v2-6-minimal-api`  
**Objective**: Implement the minimal production API: create project, run engine, return result. Uses `finco_core` exclusively for financial computation.

**Expected files**:
- `finco_app/api/projects.py` (POST/GET/PUT /api/projects)
- `finco_app/api/runs.py` (POST /api/scenarios/{id}/run, GET /api/runs/{id})
- `finco_app/services/run_service.py` (orchestrates engine call, persists result)
- `finco_app/persistence/` (projects, scenarios, runs repositories — port from `app/persistence/`)
- `finco_app/auth.py` (port from `app/auth.py`)
- Integration tests for the run endpoint: inputs in → result out → matches parity baseline

**Risks**: `app/services/run_service.py` (952 lines) may contain logic beyond orchestration. Audit before porting.

**Acceptance criteria**:
- `POST /api/scenarios/{id}/run` returns `EconomicSummary` with values matching parity baseline (±tolerance)
- No financial logic in API layer (lint rule enforced)
- Auth rate limiting functional
- Parity harness (Stage 2) still passes

**Rollback**: The legacy Streamlit + legacy API continue running; V2-6 is an addition, not a replacement.

---

### V2-7 — Minimal UI Shell

**Branch**: `v2-7-minimal-ui-shell`  
**Objective**: A minimal UI that calls the V2-6 API: load project, run engine, display EconomicSummary. Not the full spreadsheet-native C-series UI — just enough to prove the API contract end-to-end.

**Expected files**:
- `finco_ui/` (new top-level package)
- A single page showing TUHO and Oborovo reference results via the API
- No financial calculations in UI code (enforced by test)

**Risks**: Scope creep. This milestone is deliberately minimal — it proves the pipeline, it is not the production UI.

**Acceptance criteria**:
- TUHO and Oborovo results displayed via V2-6 API
- No `import finco_core` anywhere in `finco_ui/`
- No financial calculations in UI layer

**Rollback**: The legacy Streamlit UI continues running.

---

### V2-8 — Scenario Layer

**Branch**: `v2-8-scenario-layer`  
**Objective**: Full scenario management: create scenarios, run variants, compare results.

**Expected files**:
- `finco_app/api/scenarios.py` (full scenario CRUD)
- `finco_app/services/scenario_service.py`
- `finco_core/analytics/scenarios.py` (port from `domain/analytics/scenarios.py`)
- Scenario comparison in UI

**Risks**: Scenario delta serialisation must round-trip through ProjectInputs validation cleanly.

**Acceptance criteria**:
- Scenarios produce deterministic, repeatable results
- Parity harness continues to pass
- Sensitivity analysis functional for TUHO reference project

**Rollback**: Remove scenario endpoints; base run functionality is unaffected.

---

### V2-9 — Persistence

**Branch**: `v2-9-persistence`  
**Objective**: Production-grade persistence: full audit snapshots, export storage, run history.

**Expected files**:
- `finco_app/persistence/audit_snapshots_repository.py`
- `finco_app/persistence/exports_repository.py`
- Database migration scripts
- Export download endpoints wired to `finco_app/exports/`

**Risks**: The current `app/persistence/` has 4,600+ lines across 5 files. Port selectively — keep what is needed, remove calibration-specific persistence logic.

**Acceptance criteria**:
- Full run history queryable
- Audit snapshot downloadable as CSV/Excel
- Export files served via API

---

### V2-10 — Commercial Beta Baseline

**Branch**: `v2-10-commercial-beta-baseline`  
**Objective**: All previous milestones integrated and green. Legacy application shell deprecated (but preserved in git history). Documentation updated. v2 is the production baseline.

**Expected files**:
- `docs/FINCO_V2_BASELINE.md` (equivalent of POST_AC_ARCHITECTURE_STABILIZATION_BASELINE.md for v2)
- Parity targets confirmed against v2 `finco_core`
- Legacy `app/`, `domain/` (old paths), `streamlit_app.py`, `scripts/` deprecated with removal instructions
- Root-level `.db` files removed (tracked in `.gitignore`)
- CI pipeline running all four stages on every PR

**Acceptance criteria**:
- Both reference projects produce parity-passing results via v2 pipeline
- Parity harness runs in isolation (`cd parity && pytest`)
- `finco_core` has zero dependencies on `app/`, `streamlit_app.py`, or `scripts/`
- All critical and high risks from the risk register resolved

---

## Part 13 — Risk Register

### Critical

**C1 — Hidden `app/` imports in `domain/` code**  
Engine code in `domain/` may import from `app/` (adapter functions, session state). If present, `finco_core` cannot be extracted without those dependencies following.  
*Mitigation*: Audit all `from app import` statements in `domain/` before V2-3. Move any engine-relevant logic to `domain/` first; isolate any shell-relevant logic to `app/`.

**C2 — Fixture path resolution breaks after move**  
`FinancingParams.frozen_senior_ds_fixture_path` currently resolves relative to the application root. After engine extraction to `finco_core/`, the path must resolve to `parity/fixtures/`.  
*Mitigation*: In V2-3, update `frozen_senior_ds_fixture_path` to accept absolute paths or paths relative to a configurable base. The parity harness (V2-4) will catch any regression immediately.

**C3 — Parity drift during engine copy**  
Copying engine files introduces risk of line-ending, encoding, or whitespace differences that change the SHA but not the logic.  
*Mitigation*: SHA-pin the copied files against the legacy baseline SHA. The parity guardrail test will detect any content change. Run both the legacy test suite and the new parity harness in parallel during V2-3 and V2-4.

### High

**H1 — Export logic contains financial calculations not in engine**  
`app/export/calibration_reconciliation.py` (3,409 lines) may contain financial calculations that are not present in `WaterfallResult`. If so, those values would be silently absent from v2 exports.  
*Mitigation*: In V2-5, audit every financial value in the current exports against `WaterfallResult`. Any calculation not present in the engine must either be added to the engine (if it is financially significant) or removed (if it is a calibration artefact).

**H2 — Test suite has hidden runtime dependencies on `app/`**  
Some domain tests may import from `app/` (factories, runners, UI runner). If so, `finco_core` unit tests cannot run without the full app stack.  
*Mitigation*: In V2-3, create a compatibility shim in `app/ui_runner.py` that forwards to `finco_core`. Audit test imports in V2-4 and isolate parity tests from app imports.

**H3 — TUHO/Oborovo flag names (Stack AF debt)**  
`use_tuho_r99_input_engine`, `use_tuho_shl_repayment_alignment`, `tuho_cit_cash_tax_start_operating_index`, `tuho_shl_principal_eligibility_start_period` are TUHO-named capability flags in `ProjectInfo`. These are not blocking, but they are confusing in a generic input model.  
*Mitigation*: Rename in V2-2 (input model extraction) when touching `ProjectInfo`. This is mechanical — no financial behaviour changes.

**H4 — `app/waterfall_core.py` remaining identity guards (Stack AD/AE)**  
Lines 776 and 1274 contain `is_tuho`/`is_oborovo` checks in DA wiring (only active when `use_distributionaccount_runtime_wiring=True`). These are deferred from Phase 0.  
*Mitigation*: Resolve as part of V2-3 engine extraction. Apply the Stack AC pattern: parameterise the DA wiring via a config field in `FinancingParams`.

**H5 — Tax bridge constants remain hardcoded (Stack AD)**  
`TUHO_BOOK_TOTAL=72,993.7 kEUR` and `TUHO_TAX_TOTAL=70,691.5 kEUR` are hardcoded in `waterfall_core.py`. This is tracked architectural debt.  
*Mitigation*: In V2-3, move constants to `FinancingParams.tax_book_depreciation_total_keur` and `FinancingParams.tax_depreciation_total_keur`. Update TUHO factory to set these values. Update parity guardrail SHA.

### Medium

**M1 — ~400 SQLite `.db` files in working tree**  
These files are phase development artefacts that clutter the repository and slow `git status`.  
*Mitigation*: In V2-1, add `*.db` to `.gitignore`. Remove existing files in a cleanup commit. Preserve `data.db` and `finco.db` if they contain reference data.

**M2 — `domain/depreciation_offline/` duplicates `domain/depreciation/`**  
Two depreciation engines exist with overlapping concerns.  
*Mitigation*: Review in V2-3. If the offline engine is a strict subset of the main engine, consolidate. If it serves a distinct purpose (offline pre-computation), port as a separate module.

**M3 — Reporting layer (`reporting/`) is superseded but not removed**  
`reporting/excel_export.py`, `reporting/fid_deck.py`, `reporting/pdf_export.py` are legacy export paths that may still be referenced.  
*Mitigation*: Audit imports before V2-5. If unreferenced, archive in V2-5.

**M4 — BESS tests have pre-existing failures**  
`tests/test_bess_hybrid_full_flow.py` has 8 pre-existing failures on main.  
*Mitigation*: Excluded from CI explicitly. Rewrite BESS tests in V2-8 when scenario layer is stable.

**M5 — Portfolio layer complexity**  
`domain/portfolio/` has 15+ modules including holdco, distribution constraints, SHL integration, cash ledger. These are Direct Port but are complex to verify in isolation.  
*Mitigation*: Port portfolio modules in V2-3 but add a dedicated portfolio parity test to the V2-4 parity harness before proceeding to V2-5.

### Low

**L1 — `domain/presets.py` has hardcoded project assumptions**  
*Mitigation*: Review in V2-2. Migrate to factory pattern in V2-2 or V2-3.

**L2 — `scripts/` contains calibration helpers that may be cited in docs**  
*Mitigation*: Archive in V2-10. Preserve in git history.

**L3 — Multiple `main_*.py` entry points at root level**  
`main_api.py` (9 lines), `main_web.py`, `streamlit_app.py` all exist.  
*Mitigation*: Consolidate to `finco_app/main.py` in V2-6. Legacy entry points archived in V2-10.

---

## Part 14 — Stop Conditions

Extraction must pause and receive a formal review if any of the following are observed:

**S1 — Parity drift**  
Any parity KPI moves outside tolerance at any milestone. This is a hard stop: the milestone PR must not merge until the drift is explained and either accepted (with updated targets and documentation) or corrected.

**S2 — Hidden dependency on legacy shell**  
`finco_core` is found to import from `app/`, `streamlit_app.py`, or any web framework. This indicates the extraction boundary was drawn incorrectly and must be revisited.

**S3 — Engine non-determinism**  
Running the same inputs twice produces different results. This would indicate a hidden side effect or global state in the engine.

**S4 — Fixture provenance lost**  
The SHA of `parity/fixtures/tuho/phase7_tuho_*.csv` or `parity/fixtures/oborovo/phase23q_oborovo_*.csv` diverges from the legacy baseline without a documented explanation. This means the golden fixtures have been modified without authorisation.

**S5 — Test coverage regression**  
Engine invariant tests (58) or canonical formula tests (18) drop below their current count without explicit deletion decisions documented in the PR.

**S6 — Export/engine divergence**  
A value appears in an export that cannot be traced to a named `WaterfallResult` or `WaterfallPeriod` field. This indicates export-only financial logic, which is prohibited.

**S7 — API layer financial logic**  
A financial calculation is found in `finco_app/api/` or `finco_ui/`. This is an architectural boundary violation.

---

## Part 15 — Success Criteria

A v2 extraction is successful when:

**Engine fidelity**
- Both reference projects produce results within parity tolerance when run via `finco_core` in isolation
- All 58 invariant tests pass
- All 18 canonical formula tests pass
- Parity guardrail test (21 tests) passes on `finco_core/engine/waterfall_core.py`

**Architectural cleanliness**
- `finco_core` has zero imports from `app/`, `streamlit_app.py`, any UI framework, or any web framework
- No identity dispatch anywhere in `finco_core` (no `if code == "TUHO-WIND-1"` branches)
- No post-engine mutation of `WaterfallResult`
- No runtime reads from `tests/` directory
- All exported values traceable to named engine fields

**Operational**
- `pip install finco_core` works in a minimal Python environment
- `cd parity && pytest regression/` passes in under 15 seconds
- CI pipeline runs in under 5 minutes total
- Legacy application continues to function until V2-7 is complete (no regression for users)

**Simplicity**
- Fewer total lines of code in `finco_core` than in `domain/` + relevant `app/` files combined (extraction removes cruft, not just moves it)
- Package boundaries are clear: a new engineer can identify which package owns a given concern without reading more than one `__init__.py`

**SaaS readiness**
- Authentication present
- Rate limiting present
- Persistence model stable
- Export contracts stable and typed
- API contract documented and versioned

---

## Part 16 — First Implementation PR

### Recommended first PR: V2-1 — Core Package Skeleton

**Branch**: `v2-1-core-package-skeleton`  
**Scope**: Create the `finco_core/` and `parity/` directory structure; copy golden fixtures; write empty `__init__.py` files; define export contract stubs.

**Files**:
```
finco_core/
    __init__.py
    inputs/__init__.py
    engine/__init__.py
    tax/__init__.py
    shl/__init__.py
    waterfall/__init__.py
    returns/__init__.py
    audit/__init__.py
    factories/__init__.py
    exports/
        __init__.py
        contracts.py          # Stub dataclasses: EconomicSummary, PeriodExportRow, AuditExportRow
    constants.py              # Copy of domain/constants.py (no engine logic)
    pyproject.toml            # Package metadata; declares no dependencies on app/

parity/
    __init__.py
    fixtures/
        tuho/
            phase7_tuho_senior_debt_sizing_extraction.csv   (copy from reports/)
        oborovo/
            phase23q_oborovo_senior_debt_sizing_extraction.csv  (copy from reports/)
    regression/
        __init__.py
        conftest.py
    golden/
        __init__.py
        tuho_targets.py       # TUHO parity targets as named constants
        oborovo_targets.py    # Oborovo parity targets as named constants
```

**Expected LOC**: ~200 lines (mostly stubs and constants).

**Tests**:
- One test: `test_finco_core_has_no_app_imports.py` — asserts that no Python file in `finco_core/` contains `from app import` or `import app`
- One test: `test_parity_fixtures_sha.py` — asserts that golden fixture SHAs match the legacy baseline

**Acceptance criteria**:
- `pip install -e .` with `[finco_core]` extra succeeds
- `import finco_core` succeeds
- `from finco_core.exports.contracts import EconomicSummary` succeeds
- Parity fixture SHAs match `reports/phase7_tuho_*.csv` and `reports/phase23q_oborovo_*.csv`
- `test_finco_core_has_no_app_imports` passes
- All existing tests continue to pass (nothing moved yet)

**Why this PR first**: It establishes the target directory layout, proves the package tooling works, copies the parity-locked fixtures to their permanent home, and gives the team a concrete structure to review before any code moves. The cost of getting the structure wrong at this stage is near-zero (no logic); the cost of getting it wrong in V2-3 (after the engine is copied) is high.

---

*Document ends. No implementation is authorised until this plan is reviewed and the first PR (V2-1) is explicitly approved.*
