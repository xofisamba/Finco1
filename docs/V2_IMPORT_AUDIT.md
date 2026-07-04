# V2 Import Audit Checklist

**Purpose**: Pre-extraction import dependency audit.  
**Status**: V2-2 inputs completed; V2-3 engine forward shims complete.  
**Baseline**: Finco1-RC2 @ `b52d39c`

---

## Overview

Before each engine module is ported into `finco_core`, its full import graph must be audited. This document provides the checklist. The audit ensures:

1. Every dependency of the ported module is either (a) already in `finco_core`, (b) stdlib, or (c) explicitly classified for resolution.
2. No hidden shell dependencies (Streamlit, session state, UI helpers) enter `finco_core`.
3. No circular import paths are created.

---

## Audit Checklist — by Module

### `domain/inputs.py` → `finco_core/inputs/` — **COMPLETED V2-2**

- [x] All imports in `domain/inputs.py` classified
- [x] `domain.senior_rate_schedule` → moved to `finco_core.inputs.senior_rate_schedule` (stdlib only)
- [x] `domain.senior_sculpting` → moved to `finco_core.inputs.senior_sculpting` (stdlib only)
- [x] `domain.revenue.bess.BessParams` → TYPE_CHECKING only; no runtime dep (V2-3 target)
- [x] No Streamlit imports
- [x] No `app/` imports
- [x] No `tests/` imports
- [x] `domain/inputs.py` is now a re-export shim; `domain.senior_rate_schedule` and `domain.senior_sculpting` are re-export shims
- [x] 104/104 extraction migration tests passing

**Remaining dependency after V2-2:**
- `finco_core.inputs._models` has a TYPE_CHECKING-only import of `domain.revenue.bess.BessParams`
- This is not a runtime dependency — resolved to `None` at runtime via string annotation
- Will be replaced with `finco_core.inputs.BessParams` when revenue module is extracted in V2-3

### `domain/waterfall/waterfall_engine.py` → `finco_core/waterfall/` — **V2-3 FORWARD SHIM COMPLETE**

- [x] V2-3 forward shim: `finco_core.waterfall` re-exports `WaterfallPeriod`, `run_waterfall`, `WaterfallResult`, `compute_waterfall`, `distribution_after_lockup`, `DSRAEngineResult`, `run_dsra_engine`, `SHLPeriodResult`, `compute_shl_period_v3`, `TaxPeriodResult`, `compute_period_tax`, `reserve_account_balances`, `dsra_funding`
- [ ] V2-4: Move authoritative code to `finco_core/waterfall/`, make `domain/waterfall/` a re-export shim

### `domain/tax/` → `finco_core/tax/` — **V2-3 FORWARD SHIM COMPLETE**

- [x] V2-3 forward shim: `finco_core.tax` re-exports all of `domain.tax` — SPVTaxEngine, LCF, ATAD, HoldCo, templates
- [x] Verified LCF: 5-year rolling, Croatian §16 treatment (domain code unchanged)
- [ ] V2-4: Move authoritative code to `finco_core/tax/`, make `domain/tax/` a re-export shim

### `domain/shl/` → `finco_core/shl/` — **V2-3 FORWARD SHIM COMPLETE**

- [x] V2-3 forward shim: `finco_core.shl` re-exports `ShlEngine`, `ShlEngineInputs`, `ShlPeriodInput`, `ShlPeriodResult`, `ShlEngineResult`, `ShlAuditRow`, `ShlTaxInterface`, `SHLFCFWaterfallPeriodResult`, `compute_shl_fcf_waterfall_period`
- [ ] V2-4: Move authoritative code to `finco_core/shl/`, make `domain/shl/` a re-export shim

### `domain/financing/` → `finco_core/debt/` — **V2-3 FORWARD SHIM COMPLETE**

- [x] V2-3 forward shim: `finco_core.debt` re-exports `AmortizationResult`, `DebtServiceResult`, sculpting functions, covenant functions, `SeniorDebtSizingEngine`
- [ ] V2-4: Move authoritative code to `finco_core/debt/`, make `domain/financing/` a re-export shim

### `domain/depreciation/` → `finco_core/depreciation/` — **V2-3 FORWARD SHIM COMPLETE**

- [x] V2-3 forward shim: `finco_core.depreciation` re-exports `DepreciationEngine`, ledger, schedule, asset config
- [ ] V2-4: Move authoritative code to `finco_core/depreciation/`, make `domain/depreciation/` a re-export shim

### `domain/sponsor/` → `finco_core/sponsor/` — **V2-3 FORWARD SHIM COMPLETE**

- [x] V2-3 forward shim: `finco_core.sponsor` re-exports xirr/xnpv, sponsor cashflows, waterfall tier schemas, preferred return calculator
- [ ] V2-4: Move authoritative code to `finco_core/sponsor/`, make `domain/sponsor/` a re-export shim

### `domain/returns/xirr.py`, `domain/returns/xnpv.py` → `finco_core/sponsor/` — **V2-3 FORWARD SHIM COMPLETE**

- [x] V2-3 forward shim in `finco_core.sponsor`: `xirr`, `xirr_bisection`, `robust_xirr`, `xnpv`, `xnpv_schedule`
- [ ] V2-4: reverse shim direction

### `domain/construction/` → `finco_core/` (TBD placement)

- [ ] List all imports
- [ ] Classify

### `domain/period_engine.py` → `finco_core/engine/` — **V2-3 FORWARD SHIM COMPLETE**

- [x] V2-3 forward shim: `finco_core.engine` re-exports `PeriodMeta`, `PeriodEngine`, `hash_engine_for_cache`
- [x] V2-3 forward shim: `finco_core.engine` re-exports full `DistributionAccountEngine` and all gate functions
- [ ] V2-4: Move authoritative code to `finco_core/engine/`, make `domain/period_engine.py` a re-export shim

### `app/waterfall_core.py` — Shell Only (NOT ported)

- [ ] Identify which functions are engine orchestration (port to `finco_core/engine/`)
- [ ] Identify which functions are shell wiring (discard)
- [ ] List all `app/waterfall_core.py` imports that are currently in `domain/`
- [ ] Confirm all identity guards are absent (Phase 0 Y3 — should be clean)

---

## Audit Categories

| Category | Action |
|----------|--------|
| **stdlib** | No action required |
| **finco_core-internal** | Import already ported or will be ported in same PR |
| **domain-internal** | Port the dependency before or in the same PR |
| **app-shell** | Must NOT enter finco_core — refactor or remove |
| **third-party (allowed)** | Add to `pyproject.toml` dependencies |
| **third-party (disallowed)** | Document and find stdlib alternative |
| **Streamlit** | Hard prohibited — must be eliminated before port |
| **tests/** | Hard prohibited — no runtime import from test tree |

---

## Shell Dependency Hunt

V2-3 verification: no shell imports found in domain/:

- [x] `grep -r "import streamlit" domain/` — empty (clean)
- [x] `grep -r "from app import" domain/` — empty (clean)
- [x] `grep -r "from tests import" domain/` — empty (clean)
- [x] `grep -r "st\." domain/` — no Streamlit widget calls
- [x] `grep -r "session_state" domain/` — empty (clean)
- [x] `grep -r "code == " app/waterfall_core.py` — identity guards absent (Phase 0 Y3)

---

## Circular Import Check

V2-3 verification: all imports succeed, no circular dependencies:

- [x] `python -c "import finco_core"` — succeeds
- [x] `python -c "import finco_core.engine"` — succeeds
- [x] `python -c "import finco_core.waterfall"` — succeeds
- [x] `python -c "import finco_core.tax"` — succeeds
- [x] `python -c "import finco_core.debt"` — succeeds
- [x] `python -c "import finco_core.depreciation"` — succeeds
- [x] `python -c "import finco_core.shl"` — succeeds
- [x] `python -c "import finco_core.sponsor"` — succeeds
- [x] `python -c "import finco_core.validation"` — succeeds
- [x] `finco_core` does not import `finco_app`
- [x] `finco_core` does not import `finco_parity`

---

## Notes

This document is a scaffold. Actual import listings will be populated during V2-3 execution. Each checklist item will be checked off and annotated with findings before the V2-3 PR is opened.

*Do not begin the import audit until V2-2 (Inputs) is merged.*

---

## V2-4 Status Update

**Status**: V2-4 authoritative engine move complete.

All V2-3 "V2-4 target" checklist items are now complete:

- [x] `finco_core/waterfall/` — authoritative (76 files copied from domain; domain shims created)
- [x] `finco_core/tax/` — authoritative
- [x] `finco_core/shl/` — authoritative
- [x] `finco_core/debt/` — authoritative
- [x] `finco_core/depreciation/` — authoritative
- [x] `finco_core/sponsor/` — authoritative
- [x] `finco_core/engine/` — authoritative (period_engine + distribution_account)
- [x] `finco_core/validation/` — authoritative

### Circular import resolution

Several `domain/` package `__init__.py` files were converted from eager star imports to lazy
`__getattr__` delegation to prevent circular imports during finco_core initialization:
- `domain/distribution_account/__init__.py`
- `domain/shl/__init__.py`
- `domain/tax/__init__.py`
- `domain/financing/__init__.py`
- `domain/depreciation/__init__.py`
- `domain/returns/__init__.py`
- `domain/waterfall/__init__.py`

### Remaining V2-5 targets

- `finco_core/` leaf files still import from `domain.*` internally (domain shim layer resolves them)
- V2-5 will rewrite those internal imports to `finco_core.*` paths, eliminating all domain shim dependencies
- `BessParams`: still TYPE_CHECKING-only in `finco_core/inputs/_models.py`
- `SponsorXirrResult`/`xirr_with_convergence`: accessible via `finco_core.sponsor.xirr_runner` (not top-level `finco_core.sponsor` due to circular; V2-5 target)
- `SeniorDebtSizingPolicy`/`SeniorDebtSizingEngine` etc.: not yet copied to `finco_core/debt/`
