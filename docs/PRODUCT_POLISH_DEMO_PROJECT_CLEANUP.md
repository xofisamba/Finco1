# Product Polish Stack J — Demo Project Catalogue Cleanup

**Branch:** `product-polish-demo-project-cleanup`
**Date:** 2026-07-01

---

## Previous Project Inventory (before Stack J)

Seven projects were registered in `app/ui_runner.py` PROJECT_CONFIGS and FACTORY_MAP:

| Key | Factory | Type | Notes |
|-----|---------|------|-------|
| Solar | `create_default_solar_project` | Solar PV | Generic, "Generic Solar PV", SOLAR-001 |
| Wind | `create_default_wind_project` | Wind | Generic, "Generic Wind Farm", WIND-001 |
| BESS | `create_default_bess_project` | BESS | Partial model only |
| Solar+BESS | `create_default_solar_bess_project` | Hybrid | Partial model only |
| Wind+BESS | `create_default_wind_bess_project` | Hybrid | Partial model only |
| TUHO | `create_default_tuho_wind1` | Wind (Excel parity) | Golden reference |
| Oborovo | `create_default_oborovo` | Solar (Excel parity) | Golden reference |

Additionally, `app/demo_presets.py` held two investor-presentation presets
(`Solar_Utility_Example`, `Wind_Onshore_Example`) that were not registered in
the UI registry — these are left unchanged.

---

## Removed Projects

The following entries were **removed from the UI catalogue** (PROJECT_CONFIGS and FACTORY_MAP):

| Key | Reason |
|-----|--------|
| Solar (generic) | Replaced by "Test 1" with cleaner fictional identity |
| Wind (generic) | Replaced by "Test 2" with cleaner fictional identity |
| BESS | Partial model — BESS waterfall integration not complete; no user-facing value |
| Solar+BESS | Partial model — same rationale |
| Wind+BESS | Partial model — same rationale |

The three BESS/hybrid factory functions (`create_default_bess_project`,
`create_default_solar_bess_project`, `create_default_wind_bess_project`) were
**retained in `app/project_factories.py`** for backward-compatibility with
existing engine tests (62+ test references across 7 test files). They are no
longer exported in `__all__` as primary public API.

> **Note:** BESS, Solar+BESS, and Wind+BESS are **not deleted** and are **not
> permanently removed**. They are intentionally retained as future hybrid/BESS
> product options and hidden only from the current UI catalogue until those
> workflows are production-ready. The factory functions, related tests, and
> engine support remain intact.

---

## Retained Projects

### 1. TUHO — Golden Excel Parity (Wind)

- **Factory:** `create_default_tuho_wind1()`
- **Key:** `"TUHO"` in PROJECT_CONFIGS
- **Description:** 35 MW onshore wind farm (Croatia), 30-year horizon,
  EUR 60/MWh PPA, calibrated against `20260330_TUHO_BP_2.xlsm`.
- **Status:** UNCHANGED — not a single character was modified.

### 2. Oborovo — Golden Excel Parity (Solar)

- **Factory:** `create_default_oborovo()`
- **Key:** `"Oborovo"` in PROJECT_CONFIGS
- **Description:** 53.63 MWp solar PV (Croatia), 30-year horizon,
  EUR 57/MWh PPA, calibrated against Oborovo Excel reference model.
- **Status:** UNCHANGED — not a single character was modified.

### 3. Test 1 — Fictional Solar Project

- **Factory:** `create_default_solar_project()`
- **Key:** `"Test 1"` in PROJECT_CONFIGS
- **Display name:** `Test 1 — Solar`
- **Project code:** `TEST-SOLAR-1`
- **Company:** Fictional Solar SpA (entirely fictional)
- **Technology:** Solar PV, 50 MW
- **PPA tariff:** EUR 50/MWh, 10-year term, 2% indexation
- **Horizon:** 20 years
- **Gearing:** 75%, DSCR-sculpted senior debt
- **Note:** No real company, no real project, no Excel calibration data.

### 4. Test 2 — Fictional Wind Project

- **Factory:** `create_default_wind_project()`
- **Key:** `"Test 2"` in PROJECT_CONFIGS
- **Display name:** `Test 2 — Wind`
- **Project code:** `TEST-WIND-1`
- **Company:** Fictional Wind GmbH (entirely fictional)
- **Technology:** Onshore wind, 40 MW
- **PPA tariff:** EUR 60/MWh, 12-year term, 2% indexation
- **Horizon:** 25 years
- **Gearing:** 75%, DSCR-sculpted senior debt
- **Note:** No real company, no real project, no Excel calibration data.
  Independent from Test 1 in structure and values.

---

## TUHO / Oborovo Unchanged Confirmation

The SHA-256 pin for `app/project_factories.py` in
`tests/test_phase51f_parallel_work_guardrails.py` was updated to reflect
the new file content (Test 1/Test 2 renaming), with the old hash preserved
as a comment alongside a clear justification:

> Stack J: removed obsolete demo projects; TUHO and Oborovo factory functions unchanged.

The engine-output golden guardrails for TUHO and Oborovo continue to pin
exact model outputs (DSCR, OpEx, distributions) — these tests pass
unchanged because neither factory function was modified.

---

## Files Changed

- `app/project_factories.py` — Updated solar/wind factory display name, code, company; updated `__all__`
- `app/ui_runner.py` — PROJECT_CONFIGS and FACTORY_MAP reduced to four projects
- `tests/test_phase51f_parallel_work_guardrails.py` — SHA-256 pin updated (old hash preserved in comment)
- `tests/test_project_factories.py` — Name/capacity assertions updated to match new Test 1/Test 2 identity
- `docs/PRODUCT_POLISH_DEMO_PROJECT_CLEANUP.md` — This file
