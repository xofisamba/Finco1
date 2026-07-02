# Stack R — Factory Configuration Fidelity

**Branch:** `stack-r-factory-configuration-fidelity`
**Base:** `main` at Stack Q squash-merge `23d624c`
**Date:** 2026-07-02

---

## Executive Summary

Stack R fixes a Critical finding from the independent Due Diligence (R3):
when a user runs TUHO or Oborovo from the UI template path, the engine
received a generic `ProjectInputs` rebuilt from only ~11 scalar values,
silently discarding ~20+ calibrated fields.  The saved-state path was
already correct.  Stack R aligns the fresh path with the saved-state path
by seeding from the project-specific factory before applying scalar
overrides.

No engine changes.  No parity numbers move.

---

## Root Cause

`_execute_template_seeded_path()` in `app/services/run_service.py`
contained two branches:

| Path | Construction method | Calibrated config? |
|------|--------------------|--------------------|
| `saved_state` | `build_projectinputs_from_snapshot(runtime_snapshot)` | ✅ preserved |
| fresh (template) | `build_schema_from_form(...)` → `build_projectinputs(schema)` | ❌ lost |

The fresh path called `_resolve_user_inputs()` in `input_adapter.py`,
which always started from `create_default_wind_project()` or
`create_default_solar_project()` (the generic type factories) and applied
only the ~11 scalar fields present in the form schema.

Fields silently discarded on every fresh TUHO/Oborovo run:

| Field | TUHO factory value | Generic default |
|-------|--------------------|-----------------|
| `financing.equity_irr_method` | `shl_plus_dividends` | `equity_only` |
| `financing.shl_repayment_method` | `pik_then_sweep` | `bullet` |
| `financing.debt_sizing_method` | `fixed` | `dscr_sculpt` |
| `financing.use_frozen_excel_senior_debt_schedule` | `True` | `False` |
| `financing.shl_amount_keur` | `29135.0` | `7750.0` |
| `financing.shl_rate` | `0.0793` | `0.08` |
| `financing.dscr_schedule` | 28-element array | `None` |
| `financing.fixed_debt_keur` | `43359.0` | `None` |
| `tax.corporate_rate` | `0.18` | `0.25` |
| `tax.prior_tax_loss_keur` | `25000.0` | `0.0` |
| `revenue.market_prices_curve` | 30-element calibrated tuple | generic curve |
| `capex.idc_keur` | `1519.56` | zeroed |
| `capex.bank_fees_keur` | `782.61` | zeroed |
| (+ CO2 schedule, balancing cost, merchant index, etc.) | calibrated | generic/absent |

---

## Implementation

### Change 1 — `app/input_adapter.py`

**`_resolve_user_inputs()`** — added `base_inputs: "ProjectInputs" = None` parameter.

- When `base_inputs` is provided, the function starts from it instead of
  calling the generic factory.
- CAPEX zeroing (`_zero_financial_capex_subfields`) is skipped on the
  seeded path unless `total_capex_keur` is also supplied, preserving the
  factory's calibrated IDC and bank-fee structure.
- All other override logic (technical, revenue, opex, financing) is
  unchanged and applies in the same order as before.

**`build_projectinputs_seeded(schema, base_inputs)`** — new public function.

Thin wrapper: calls `_resolve_user_inputs(base_inputs=base_inputs,
**_schema_to_dict(schema))`.  Used by the Stack R fresh path.  The
generic `build_projectinputs(schema)` is unchanged.

### Change 2 — `app/services/run_service.py`

**`_execute_template_seeded_path()`** — fresh-path branch updated.

```python
_seed_base = _get_seed_base_inputs(runtime_seed)
if _seed_base is not None:
    from app.input_adapter import build_projectinputs_seeded as _build_seeded
    override = _build_seeded(schema, _seed_base)
else:
    override = deps.build_projectinputs(schema)
```

**`_get_seed_base_inputs(runtime_seed)`** — new module-level helper.

```python
def _get_seed_base_inputs(runtime_seed: str):
    if runtime_seed == "tuho":
        from app.project_factories import create_default_tuho_wind1
        return create_default_tuho_wind1()
    if runtime_seed == "oborovo":
        from app.project_factories import create_default_oborovo
        return create_default_oborovo()
    return None
```

Returns `None` for any other seed; generic projects continue to use the
existing path unchanged.

---

## Files Changed

| File | Change |
|------|--------|
| `app/input_adapter.py` | `base_inputs` param on `_resolve_user_inputs`; conditional CAPEX zeroing; new `build_projectinputs_seeded` |
| `app/services/run_service.py` | Seeded path in `_execute_template_seeded_path`; new `_get_seed_base_inputs` helper |
| `tests/test_excel_parity_stack_r.py` | 61 new tests (created) |
| `docs/STACK_R_FACTORY_CONFIGURATION_FIDELITY.md` | This document (created) |

**Not changed:** `domain/`, `app/waterfall_core.py`,
`domain/waterfall/waterfall_engine.py`, `app/project_factories.py`,
all financial formulas, Golden parity values, SHA locks.

---

## Regression Strategy

- The engine receives `ProjectInputs` as a black box; it is not touched.
- The `saved_state` branch in `_execute_template_seeded_path` is not
  touched; its behaviour is identical.
- Generic Wind/Solar projects (non-TUHO/Oborovo seeds) use the existing
  `deps.build_projectinputs(schema)` path; their behaviour is identical.
- `build_projectinputs` and `build_projectinputs_from_snapshot` are
  unchanged; all callers that use them directly are unaffected.
- `_resolve_user_inputs` change is fully backwards-compatible: `base_inputs`
  defaults to `None`, which reproduces the original behaviour exactly.

---

## Golden Parity Confirmation

| Metric | Pre-Stack-R | Post-Stack-R | Change |
|--------|------------|--------------|--------|
| TUHO equity IRR | 11.59% | 11.59% | Unchanged ✅ |
| TUHO project IRR | 9.41% | 9.41% | Unchanged ✅ |
| TUHO avg DSCR | 1.3786 | 1.3786 | Unchanged ✅ |
| TUHO senior debt | 43,359 kEUR | 43,359 kEUR | Unchanged ✅ |
| Oborovo equity IRR | 10.66% | 10.66% | Unchanged ✅ |
| Oborovo project IRR | 8.09% | 8.09% | Unchanged ✅ |
| Oborovo avg DSCR | 1.179 | 1.179 | Unchanged ✅ |
| Oborovo senior debt | 42,852 kEUR | 42,852 kEUR | Unchanged ✅ |

All 183 Stack K–Q parity tests + guardrail tests pass.

---

## Acceptance Criteria

- ✅ Fresh-path TUHO equity IRR == factory-path equity IRR (exact)
- ✅ Fresh-path Oborovo equity IRR == factory-path equity IRR (exact)
- ✅ `financing.equity_irr_method == "shl_plus_dividends"` on fresh path
- ✅ `financing.shl_repayment_method == "pik_then_sweep"` on TUHO fresh path
- ✅ `financing.use_frozen_excel_senior_debt_schedule == True` on both
- ✅ `tax.prior_tax_loss_keur == 25000.0` on TUHO fresh path
- ✅ `revenue.market_prices_curve` matches factory on both projects
- ✅ `capex.idc_keur > 0` on TUHO fresh path (not zeroed by generic path)
- ✅ Scalar overrides (capacity, tariff, tenor, opex, capex total) still work
- ✅ All 183 Stack K–Q parity tests green
- ✅ 61 Stack R tests pass

---

## Guardrail Confirmation

- ✅ No changes to `domain/` (any file)
- ✅ No changes to `app/waterfall_core.py`
- ✅ No changes to `domain/waterfall/waterfall_engine.py`
- ✅ No changes to `app/project_factories.py`
- ✅ No financial formula changes
- ✅ No debt sizing changes
- ✅ No SHL mechanic changes
- ✅ No tax engine changes
- ✅ No IRR calculation changes
- ✅ No export changes
- ✅ No serialisation changes
- ✅ No Golden parity numbers moved
- ✅ SHA locks in `test_phase51f_parallel_work_guardrails.py` unchanged
