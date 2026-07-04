# finco_core Public API Contract

**Version:** V3-1  
**Status:** Frozen — V2 Controlled Extraction Programme complete  
**Last updated:** Post V2-9

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│  app/  ·  main_web.py  ·  tests/                    │  Application Layer
│  (zero direct finco_core imports)                   │
└───────────────────┬─────────────────────────────────┘
                    │ imports
┌───────────────────▼─────────────────────────────────┐
│  domain/                                            │  Compatibility Shim Layer
│  (thin re-export stubs → finco_core)                │
└───────────────────┬─────────────────────────────────┘
                    │ star-re-exports
┌───────────────────▼─────────────────────────────────┐
│  finco_core/                                        │  Engine Layer (authoritative)
│  (zero domain.* dependencies)                       │
└─────────────────────────────────────────────────────┘
```

The `app/` layer imports exclusively from `domain.*`. `domain.*` files are
compatibility shims that re-export everything from `finco_core.*`.  
This means `app/` is decoupled from `finco_core` internals by one indirection layer.

---

## 2. Approved Public API Entry Points

The following `finco_core` packages form the **stable public API**.  
All callers (direct or via domain shims) MUST import from these paths only.

| Package | Primary symbols |
|---|---|
| `finco_core.inputs` | `ProjectInputs`, `TechnicalParams`, `CapexItem`, `OpexItem`, `FinancingParams`, `TaxParams`, `ProjectInfo`, `RevenueParams`, `BessParams`, `PeriodFrequency`, `DebtSizingMode`, `SHLRepaymentMethod`, `YieldScenario`, `AssetClass`, `hash_inputs_for_cache` |
| `finco_core.inputs.senior_rate_schedule` | `SeniorRateSchedule`, `SeniorDebtInterestConfig`, `SeniorRateMode`, `build_senior_period_rate_schedule`, `senior_period_fraction` |
| `finco_core.inputs.senior_sculpting` | `SeniorSculptingConfig`, `SeniorSculptingMode`, `validate_explicit_debt_service_schedule` |
| `finco_core.inputs.bess` | `BessParams` |
| `finco_core.engine` | `PeriodEngine` |
| `finco_core.engine.period_engine` | `PeriodEngine`, `PeriodMeta`, `hash_engine_for_cache` |
| `finco_core.engine.distribution_account` | `compute_tuho_r99_input_period`, `DistributionAccountEngine` |
| `finco_core.revenue` | `full_revenue_schedule`, `full_generation_schedule`, `revenue_decomposition_schedule` |
| `finco_core.revenue.generation` | `full_revenue_schedule`, `full_generation_schedule`, `revenue_decomposition_schedule`, `period_generation`, `annual_generation_mwh`, `period_revenue` |
| `finco_core.opex` | `opex_schedule_annual`, `opex_year` |
| `finco_core.opex.projections` | `opex_schedule_annual`, `opex_year`, `opex_item_amount_at_year`, `opex_per_mw_y1`, `opex_per_mwh_y1`, `opex_schedule_period`, `opex_breakdown_year`, `total_opex_over_horizon`, `opex_growth_rate` |
| `finco_core.waterfall` | `run_waterfall`, `WaterfallPeriod`, `WaterfallResult` |
| `finco_core.waterfall.waterfall_engine` | `run_waterfall`, `WaterfallPeriod`, `WaterfallResult`, `cached_run_waterfall` |
| `finco_core.tax` | `fiscal_reintegration` |
| `finco_core.tax.engine` | `taxable_profit`, `atad_adjustment` |
| `finco_core.tax.engine_runner` | `SPVTaxEngineInputs` (via `finco_core.tax.engine_inputs`) |
| `finco_core.tax.reintegration` | `fiscal_reintegration` |
| `finco_core.tax.loss_carryforward` | (loss carry-forward schedules) |
| `finco_core.tax.templates` | `TaxTemplate`, `ResolvedTaxConfig`, `resolve_tax_template`, `get_builtin_tax_templates` |
| `finco_core.debt` | `iterative_sculpt_debt` |
| `finco_core.debt.sculpting_iterative` | `iterative_sculpt_debt`, `closed_form_sculpt`, `dsra_rolling_target`, `dsra_update`, `cash_sweep` |
| `finco_core.debt.schedule` | `senior_debt_amount` |
| `finco_core.shl` | `ShlEngine` |
| `finco_core.shl.engine` | `ShlEngine` |
| `finco_core.shl.fcf_waterfall` | `compute_shl_fcf_waterfall_period` |
| `finco_core.sponsor` | `xirr`, `xnpv` |
| `finco_core.sponsor.xirr` | `xirr`, `xnpv`, `xirr_bisection` |
| `finco_core.sponsor.xirr_runner` | `xirr_with_convergence`, `SponsorXirrResult` |
| `finco_core.sponsor.sponsor_cashflows` | `build_sponsor_cashflows` |
| `finco_core.depreciation` | `DepreciationEngine` |
| `finco_core.depreciation.engine` | `DepreciationEngine`, `DepreciationEngineInputs` |
| `finco_core.validation` | (validation functions) |
| `finco_core.validation.validators` | (input validators) |

---

## 3. Import Classification

### 3.1 Approved — app/domain layer

The application layer currently uses `finco_core` exclusively through `domain.*` shims.

```
app/      →  domain.*  →  finco_core.*   ✓ (via shim layer)
main_web.py  →  domain.*  →  finco_core.*  ✓ (via shim layer)
```

**Direct `finco_core` imports from `app/`:** 0  
**Direct `finco_core` imports from `main_web.py`:** 0  

This is the intended architecture. The shim layer provides a stable backwards-compatible
indirection that allows `finco_core` internals to evolve without touching app code.

### 3.2 Approved — domain shim layer

All `domain.*` shims import from `finco_core.*` sub-packages (never from internal `_`-prefixed modules). Classification: **approved public API usage**.

### 3.3 Approved — tests

Test files import from public `finco_core.*` packages directly. Classification: **approved public API usage**.

### 3.4 Private / internal modules (convention)

Any `finco_core` module whose filename begins with `_` (e.g. `finco_core.inputs._models`) is **private**. No caller outside `finco_core` should import from it directly. As of V3-1, **zero private imports were found** in the codebase.

---

## 4. Stability Contract

### What is frozen

- All package paths listed in §2 are stable entry points.  
- Their signatures must not change in a backwards-incompatible way without a deprecation cycle.  
- `domain.*` shims must continue to expose the same objects (object identity guaranteed by star re-export).

### What is NOT frozen

- Internal `finco_core` module organisation (sub-file splits, private helpers).  
- `finco_core.waterfall.waterfall_engine.cached_run_waterfall` — app-layer UI cache wrapper, may be relocated to `finco_core.waterfall.cache` in V3.
- Non-extracted `domain/opex/` and `domain/revenue/` modules (non-`projections` / non-`generation` files) — these are app-layer concerns not imported by `finco_core`.

---

## 5. Enforcement

`tests/test_v3_api_boundary.py` enforces:

1. `app/` has zero direct `finco_core` imports (uses `domain.*` shim layer only).
2. `domain/*` shims import only from public (non-`_`-prefixed) `finco_core` sub-modules.
3. All approved public entry points remain importable.

`tests/test_v2_architecture_freeze.py` (V2-9) enforces:

- Zero `domain.*` imports inside `finco_core/` (runtime + static analysis).
- Object identity for all compatibility shims.

---

## 6. Deferred Cleanup (V3+)

| Item | Target | Notes |
|---|---|---|
| Formal shim deprecation | V3-2 or later | Announce removal timeline; migrate app callers from `domain.*` to `finco_core.*` directly |
| `finco_core.waterfall.cached_run_waterfall` relocation | V3-2 | Move to `finco_core.waterfall.cache`; currently in engine file |
| Extract remaining `domain/opex/` modules | On demand | `engine.py`, `runtime_adapter.py` — not needed by `finco_core` currently |
| Extract remaining `domain/revenue/` modules | On demand | `tariff.py`, `hybrid.py`, `bess.py` helpers — not needed by `finco_core` |
| `mypy --strict` typed boundary check in CI | V3-2 | Structural typing enforcement on top of runtime checks |
| Package `finco_core` as standalone installable | V3+ | `pyproject.toml` with explicit dependency pins |

---

## 7. Dependency Graph (post V2-8)

```
finco_core
 ├── inputs        ←  leaf (no internal finco_core deps)
 ├── inputs.bess   ←  leaf
 ├── engine        ←  leaf
 ├── revenue       ←  [engine, inputs]
 ├── opex          ←  [inputs]
 ├── debt          ←  [engine, inputs]
 ├── depreciation  ←  leaf (self-contained)
 ├── tax           ←  leaf (self-contained)
 ├── shl           ←  [waterfall] (TYPE_CHECKING only for WaterfallPeriod)
 ├── sponsor       ←  leaf
 ├── validation    ←  leaf
 └── waterfall     ←  [debt, engine, inputs, opex, revenue, shl, sponsor, tax]

Zero outgoing domain.* edges. ✓
```
