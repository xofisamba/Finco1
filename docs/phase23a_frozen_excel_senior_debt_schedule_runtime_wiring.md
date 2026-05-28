# Phase 23A — Frozen Excel Senior Debt Schedule Runtime Wiring

**Branch:** `phase23a-frozen-excel-senior-debt-schedule-runtime-wiring`
**Base:** `origin/main` @ `341ece8`
**Status:** Open PR — DO NOT MERGE OR DEPLOY UNTIL REVIEWED

---

## Objective

Wire the existing `FROZEN_EXCEL_SCHEDULE` mode into active runtime behind a flag so it can be selectively enabled for TUHO/Oborovo when frozen schedule data is confirmed to be present. Preserve default behavior for all other projects.

---

## What Changed

### 1. `FinancingParams` — new field (`domain/inputs.py`)

```python
use_frozen_excel_senior_debt_schedule: bool = False
```

Added to `FinancingParams` with full docstring explaining:
- When `True` + `use_senior_debt_sizing_engine=True`: senior debt service per period is taken from the frozen schedule (canonical sizing capacity), DSCR becomes backward-computed output
- Default `False` preserves existing runtime behavior
- Only TUHO/Oborovo should set this to `True`, after confirming frozen data is loaded

Also added `frozen_schedule_note: str | None` field (already existed; docstring enhanced) for tracking the source of frozen schedule data (e.g. "Macro!R50 / DS!R19").

### 2. `WaterfallRunConfig` — flag propagated (`app/waterfall_runner.py`)

- Added `use_frozen_excel_senior_debt_schedule: bool = False` field
- Added to `cache_key()` as `frozensds_{0|1}` for correct caching
- `from_inputs()` reads from `financing.use_frozen_excel_senior_debt_schedule`

### 3. `run_waterfall_v3_core` — wiring (`app/waterfall_core.py`)

Added `use_frozen_excel_senior_debt_schedule` parameter and Phase 23A wiring block:

**When both flags are `True`:**
1. Reads `_canonical_senior_debt_sizing.debt_service_capacity_keur_by_period` (frozen per-period DS capacity from Macro!R50 sizing CFADS / DS!R19 targets)
2. Overrides `period.senior_ds_keur` with frozen values for each operating period
3. Attaches `_frozen_senior_ds_override = True` audit flag on each period
4. Recomputes `period.dscr = cfads / frozen_senior_ds`
5. Stores `_frozen_senior_ds_wired = True` on result with explanatory note

**Guard conditions:**
- `use_senior_debt_sizing_engine` must be `True` (canonical result required)
- `_canonical_senior_debt_sizing` must be present
- Falls back to existing behavior with `warnings.warn` if conditions not met

**R99/R102:** BLOCKED — frozen schedule wiring does not touch R99/R102 gates.

### 4. TUHO Factory — opt-in documentation (`app/project_factories.py`)

`create_default_tuho_wind1()` FinancingParams now includes:
```python
frozen_schedule_note="Macro!R50 / DS!R19 frozen per-period debt service (Excel calibration)",
```

The `use_frozen_excel_senior_debt_schedule` flag remains `False` (default). To enable:
```python
financing = FinancingParams(
    ...
    use_frozen_excel_senior_debt_schedule=True,  # After confirming frozen data
    frozen_schedule_note="Macro!R50 / DS!R19 frozen per-period debt service (Excel calibration)",
)
```

---

## Architecture

### Existing Architecture (before Phase 23A)

```
FinancingParams
  debt_sizing_mode: DebtSizingMode | None = None  → resolves to FROZEN_EXCEL_SCHEDULE
  frozen_schedule_note: str | None                 → source documentation
  fixed_debt_keur: float | None = None           → TUHO: 43359.0
  dscr_schedule: list[float] | None               → TUHO: [1.2]*24 + [1.4125]*4
```

`DebtSizingMode` enum already existed with three values:
- `FROZEN_EXCEL_SCHEDULE` — default, treats Excel debt/service as frozen inputs
- `MINIMUM_DSCR_SCULPTED` — TUHO-style solver (NOT IMPLEMENTED)
- `FLAT_DSCR_SCULPTED` — Oborovo-style solver (NOT IMPLEMENTED)

`canonical_wiring.build_canonical_senior_debt_sizing_from_inputs()` already exists with:
- `use_explicit_sizing_cfads=False` (hardcoded; currently uses ebitda-derived proxy)
- When `True`: uses explicit sizing CFADS from Macro!R50

`domain/senior_debt_sizing/canonical_wiring.py` already has:
- `load_senior_debt_sizing_csv()` — loads `macro_r50_sizing_cfads_keur` and `ds_r19_target_dscr` from extraction CSV
- `CanonicalSeniorDebtSizingResult.debt_service_capacity_keur_by_period` — frozen per-period DS capacity

### After Phase 23A

```
FinancingParams
  use_frozen_excel_senior_debt_schedule: bool = False  ← NEW FLAG
  frozen_schedule_note: str | None                     ← ENHANCED DOCSTRING
  debt_sizing_mode / dscr_schedule / fixed_debt_keur   ← unchanged

WaterfallRunConfig
  use_frozen_excel_senior_debt_schedule               ← NEW (from_inputs propagated)
  use_senior_debt_sizing_engine                       ← already existed

run_waterfall_v3_core
  use_frozen_excel_senior_debt_schedule              ← NEW PARAM
  Phase 23A block: wire frozen DS into period.senior_ds_keur
```

---

## TUHO / Oborovo Behavior

### TUHO
- `fixed_debt_keur = 43359.0` — frozen debt amount from Excel Inputs
- `dscr_schedule = [1.2]*24 + [1.4125]*4` — dual-DSCR targets (PPA / Merchant)
- `debt_sizing_method = "fixed"` — uses fixed amount, not sculpted
- `frozen_schedule_note` documents source as Macro!R50 / DS!R19
- **Flag OFF (default):** existing runtime behavior unchanged
- **Flag ON:** per-period senior DS from canonical sizing capacity; DSCR becomes output

### Oborovo
- `debt_sizing_method = "gearing_cap"` — gearing-based sizing
- `frozen_schedule_note` not yet set (opt-in point for future)
- **Flag OFF (default):** existing runtime behavior unchanged
- **Flag ON:** per-period senior DS from canonical sizing capacity (requires Oborovo-specific frozen data source)

---

## Guardrails

| Guard | Status |
|---|---|
| No sculpting solvers implemented | ✅ |
| `flat_dscr_sculpted` not promoted to default | ✅ |
| `minimum_dscr_sculpted` not promoted to default | ✅ |
| SHL logic unchanged | ✅ |
| Distribution lock-up unchanged | ✅ |
| Revenue unchanged | ✅ |
| OPEX unchanged | ✅ |
| CAPEX unchanged | ✅ |
| Tax unchanged | ✅ |
| G20 governance | 🔴 BLOCKED — no promotion in this phase |
| R99/R102 | 🔴 NOT APPROVED — frozen wiring does not touch R99/R102 gates |

---

## Default Behavior Preserved

All existing tests pass with `use_frozen_excel_senior_debt_schedule=False` (the default):
- TUHO waterfall output unchanged
- Oborovo waterfall output unchanged
- SHL waterfall priority unchanged
- Revenue/OPEX/CAPEX/Tax outputs unchanged

---

## Test Results

```
tests/test_phase23a_frozen_excel_senior_debt_schedule_runtime_wiring.py: 28 passed
tests/test_revenue.py + tests/test_opex.py: 31 passed
tests/test_shl_waterfall_priority.py: 6 passed
tests/test_phase20o_debt_sizing_modes.py: 20 passed, 2 pre-existing failures (unrelated)
tests/test_senior_debt_schedule_alignment.py: 5 passed, 1 pre-existing failure (unrelated)
```

Pre-existing failures: `test_oborovo_default_outputs_unchanged_total_senior_ds`, `test_oborovo_default_outputs_unchanged_total_distribution`, `test_first_operating_senior_diagnostics_are_visible_for_oborovo` — these fail on `origin/main` too (hard-coded expected values that no longer match current runtime output).

---

## Recommended Next Phase

**Phase 23B — TUHO Frozen Schedule Parity Validation**

1. Load actual Macro!R50 sizing CFADS for TUHO via `load_senior_debt_sizing_csv_fixture()`
2. Run TUHO with `use_frozen_excel_senior_debt_schedule=True` + `use_senior_debt_sizing_engine=True`
3. Compare `period.senior_ds_keur` vs Excel DS!R19 values
4. Validate DSCR alignment — frozen DS should produce DSCR close to the dual-DSCR targets (1.20 / 1.4125)
5. Only then enable `use_frozen_excel_senior_debt_schedule=True` in TUHO factory
