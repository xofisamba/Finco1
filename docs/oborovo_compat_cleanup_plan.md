# Oborovo Compatibility Shim — Cleanup Plan

## Why the Shim Exists

`ProjectInputs.create_default_oborovo()` and `ProjectInputs.create_default_tuho_wind1()` are
legacy factory methods that live on `ProjectInputs` for historical reasons.
They were used by calibration tests and old Excel-reconciliation tests.

In `industry-engine-refactor`, `app.calibration` is disabled (raises `ImportError` at module level).
The shim allows legacy tests to continue running without modifying dozens of test files.

**The shim lives in:** `app/project_factories.py` as:
```python
ProjectInputs.create_default_oborovo = staticmethod(create_default_oborovo)
ProjectInputs.create_default_tuho_wind1 = staticmethod(create_default_tuho_wind1)
```

## Where It's Used (Known Callsites)

| Category | Files/Tests | Status |
|---|---|---|
| Legacy Excel calibration | `test_pl_tax_excel_alignment.py`, `test_tuho_excel_reconciliation.py`, etc. | **SKIPPED** — `app.calibration` disabled |
| Headless calibration runners | `test_headless_calibration_runner.py`, `test_finco_gpt_headless_core.py` | **SKIPPED** via `conftest.py` |
| Regression tests | `test_regression.py` | **SKIPPED** via `conftest.py` |
| Integration / FID deck | `integration/test_fid_deck_excel.py` | **SKIPPED** via `conftest.py` |
| Active runtime tests | `test_portfolio_waterfall.py`, `test_project_factories.py`, etc. | ✅ Use `app.project_factories` directly |

**Approximate count of remaining callsites:** ~15 test files use the shim; all are legacy/skip'd.

## Migration Plan

**Target API:**
- `app.project_factories.create_default_solar_project()`
- `app.project_factories.create_default_wind_project()`
- `app.project_factories.create_default_oborovo()` — still available (not deprecated internally)

**For each remaining callsite:**
1. Replace `ProjectInputs.create_default_oborovo()` → `app.project_factories.create_default_oborovo()`
2. Replace `ProjectInputs.create_default_tuho_wind1()` → `app.project_factories.create_default_tuho_wind1()`
3. Run tests to verify

## Classification

| Class | Description | Action |
|---|---|---|
| **Active runtime tests** | Use `app.project_factories` directly | Keep as-is |
| **Legacy calibration tests** | Depend on `app.calibration` | Skip via `conftest.py` — do not migrate |
| **Obsolete** | Tests for removed features | Delete or archive |

## Removal Condition

**Shim can be removed when:**
- Zero callsites remain that use `ProjectInputs.create_default_oborovo`
- Zero callsites remain that use `ProjectInputs.create_default_tuho_wind1`

## Warning

> **Runtime model must NOT depend on Oborovo-specific factories.**
> `app.project_factories.create_default_oborovo()` exists for backward compatibility only.
> New code should use Solar/Wind factories, not Oborovo.