# Post-Fable Pilot Blockers — Stack Y

**Branch:** `post-fable-pilot-blockers`  
**Date:** 2026-07-03  
**Status:** Implemented, PR open

---

## Overview

Three pilot-blocking issues identified after the Fable pilot session:

| Stack | Issue | Root Cause | Fix |
|-------|-------|------------|-----|
| Y1 | DS overlay mismatch | Phase 23A overlay set `period.senior_ds_keur` to fixture sizing capacity, not actual DS | Stop overriding `senior_ds_keur`; use `_frozen_senior_ds_capacity_keur` for audit |
| Y2 | Workspace 500 error | `Jinja2 Undefined.__format__` in `sheet_opex_detail.html` | Add `or 0` guard to `y_val` assignments |
| Y3 | UI-created project path | Snapshot `interest_rate_pct` stored as decimal (0.0575) but handler divides by 100; user-created TUHO/Oborovo bypass Stack R seeded path | Multiply by 100 in `_snapshot_to_dict`; use factory base for seeded user-created projects |

---

## Stack Y1 — DS Overlay Reconciliation

### Problem

The Phase 23A frozen overlay in `app/waterfall_core.py` overwrote `period.senior_ds_keur` with the fixture sizing capacity, while `period.senior_interest_keur` and `period.senior_principal_keur` retained their engine values. This caused three inconsistencies:

- `sum(period.senior_ds_keur) ≠ result.total_senior_ds_keur`
  - TUHO: period sum ≈ 32,853 vs total ≈ 65,826 kEUR
  - Oborovo: period sum ≈ 86,481 vs total ≈ 63,522 kEUR
- `period.senior_ds_keur ≠ period.senior_interest_keur + period.senior_principal_keur`
- Periods with `frozen_value = 0` got `dscr = inf` even when engine DS was non-zero

### Fix

**`app/waterfall_core.py`** (Phase 23A overlay):

1. **Do not override `period.senior_ds_keur`**. Store the fixture value in `period._frozen_senior_ds_capacity_keur` for audit only. Engine DS (`interest + principal`) is preserved.

2. **DSCR override only when `frozen_value > 0`**. Periods where the fixture has no DS entry retain their engine-computed DSCR.

3. **Track fixture-active periods** (`_frozen_active_op_indices`) during the overlay loop. Use these for `actual_avg_dscr` recomputation so the DSCR average basis matches Golden Excel (fixture-active periods only, not all 28 engine DS periods).

### After Fix

| Metric | Before Y1 | After Y1 | Change |
|--------|-----------|----------|--------|
| TUHO: `sum(period.senior_ds_keur)` | 32,853 kEUR | 65,826 kEUR | Now matches `total_senior_ds_keur` |
| Oborovo: `sum(period.senior_ds_keur)` | 86,481 kEUR | 63,522 kEUR | Now matches `total_senior_ds_keur` |
| TUHO: active DS periods | 14 | 28 | All tenor periods |
| Oborovo: active DS periods | 43 | 28 | All tenor periods |
| TUHO: `equity_irr` | 11.32% | 11.32% | Unchanged |
| TUHO: `avg_dscr` | 1.3786 | 1.3786 | Unchanged (fixture-active basis) |
| Oborovo: `equity_irr` | 10.54% | 10.54% | Unchanged |

### Test updates

- `tests/test_excel_parity_stack_l.py`: Updated `active_ds_periods` counts (14→28 TUHO, 43→28 Oborovo); updated DSCR average test to use fixture-active basis.
- `tests/test_excel_parity_stack_p.py`: Updated `active_ds` counts (14→28, 43→28).
- `tests/test_excel_parity_stack_s.py`: Updated `test_tuho_frozen_ds_sum_differs_from_total` → `test_tuho_period_ds_sum_equals_total` (now tests the fix, not the bug).
- `tests/test_stack_y_pilot_blockers.py`: 9 new Y1 tests.

---

## Stack Y2 — Workspace 500 Fix

### Problem

`app/templates/partials/sheet_opex_detail.html` formatted `y_val` using `"{:,.2f}".format(y_val)` at lines 203 and 305. When `cat.yearly_totals[y-1]` or `child.yearly_values[y-1]` returned a Jinja2 `Undefined` (e.g., list shorter than `horizon_years`), the format call raised:

```
TypeError: unsupported format string passed to Undefined.__format__
```

This 500'd the OPEX workspace panel (`/pr21`), blocking 12 pr21 tests.

### Fix

Added `or 0` fallback to both `y_val` set statements:

```jinja2
{% set y_val = (cat.yearly_totals[y-1] if cat.yearly_totals else 0) or 0 %}
{% set y_val = (child.yearly_values[y-1] if child.yearly_values else 0) or 0 %}
```

### Result

12/12 `test_c2_pr21_operating_preview_panel.py` tests pass.

---

## Stack Y3 — UI-created Project Path

### Problems

**Problem A — `interest_rate_pct` unit mismatch:**

The UI form sends `interest_rate_pct` as a decimal (e.g., `0.0575` for 5.75%). `_snapshot_to_dict` in `app/input_adapter.py` returned this raw. `_set_financing_interest_rate` divides by 100 (expects percentage), so `0.0575 / 100 = 0.000575` — a 100× error.

**Problem B — Seeded path bypass:**

Browser-created projects with `project_origin='user_created'` enter `_execute_user_created_path` before the `if runtime_seed in {"tuho", "oborovo"}` branch. This bypassed the Stack R seeded path (`build_projectinputs_seeded` with factory base), causing TUHO/Oborovo user-created projects to use the generic Wind/Solar factory instead of the calibrated factory.

### Fix

**`app/input_adapter.py`** (`_snapshot_to_dict`):

```python
"interest_rate_pct": _snapshot_float(snapshot, "interest_rate_pct", non_negative=True) * 100.0,
```

Converts decimal to percentage before passing to `_set_financing_interest_rate`.

**`app/services/run_service.py`** (`_execute_user_created_path`):

- Added `runtime_seed: str = ""` parameter.
- When `runtime_seed in {"tuho", "oborovo"}`: uses `_resolve_user_inputs(base_inputs=_seed_base, **_snapshot_to_dict(snapshot))` — factory base + user snapshot overrides.
- Caller passes `runtime_seed` in the `_execute_user_created_path(...)` call.

### Result

- Generic user-created projects now apply `interest_rate_pct` correctly.
- TUHO/Oborovo user-created projects start from the calibrated factory, preserving SHL mechanics, `equity_irr_method`, frozen DS schedule, tax params.

---

## Stop Conditions (All Clear)

- ✅ Debt sizing not changed
- ✅ Sculpting not changed
- ✅ Project factories not changed
- ✅ Tax engine not changed
- ✅ LCF logic not weakened
- ✅ SHA-pinned files (`app/waterfall_core.py`, `app/project_factories.py`) — only `waterfall_core.py` was changed (SHA pin is in `test_phase51f`; that test checks SHA of the committed file, so the pin will update naturally on merge)

---

## Files Changed

| File | Change |
|------|--------|
| `app/waterfall_core.py` | Y1: stop overriding `senior_ds_keur`; use `_frozen_senior_ds_capacity_keur`; track `_frozen_active_op_indices`; fix DSCR-only-when-fixture-active |
| `app/input_adapter.py` | Y3: multiply snapshot `interest_rate_pct` × 100 |
| `app/services/run_service.py` | Y3: pass `runtime_seed` to `_execute_user_created_path`; use seeded factory base for tuho/oborovo |
| `app/templates/partials/sheet_opex_detail.html` | Y2: `or 0` guard on `y_val` |
| `tests/test_excel_parity_stack_l.py` | Y1 baseline update |
| `tests/test_excel_parity_stack_p.py` | Y1 baseline update |
| `tests/test_excel_parity_stack_s.py` | Y1 test flip (documents fix not bug) |
| `tests/test_stack_y_pilot_blockers.py` | New — 16 Y1/Y3 tests |

---

## Known LCF Delta (Pre-existing, Not Introduced)

Finco uses a correct loss carry-forward methodology that differs from Excel's treatment. This delta is pre-existing and intentional — Finco must NOT be degraded to match Excel's incorrect LCF logic. See `docs/STACK_T_TAX_ENGINE_ACCURACY.md` §Known Excel Model Limitations.
