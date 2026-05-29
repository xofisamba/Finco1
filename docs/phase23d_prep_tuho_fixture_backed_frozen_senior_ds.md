# Phase 23D: TUHO Fixture-Backed Frozen Senior Debt Sizing — Wiring Only

**Date:** 2026-05-29
**Branch:** `phase23d-tuho-fixture-backed-frozen-senior-debt-sizing`
**Base SHA:** `a08324e` (Phase 23C, PR #300 merged)
**Status:** DRAFT — wiring only, no factory opt-in

---

## Prerequisites

- PR #300 (Phase 23C) must be merged before this PR
- PR #299 remains DRAFT / not merged — superseded by this wiring path

---

## Root Cause (Phase 23C Blocker)

`waterfall_runner.run()` called `run_waterfall_v3_core(...)` but did NOT pass
`use_frozen_excel_senior_debt_schedule` to it. The Phase 8 canonical SeniorDebtSizing
block inside `waterfall_core` reads the flag internally, but the call was missing entirely.

Result: `use_frozen_excel_senior_debt_schedule=True` was set in the config, but the
flag never reached `waterfall_core` → CSV fixture was never loaded → frozen=ON produced
IDENTICAL senior_ds_keur to frozen=OFF (both paths used ebitda-derivation).

---

## Implementation Summary

### Fixture Path

**Anchor:** `Path(__file__).resolve().parents[1] / "reports" / "phase7_tuho_senior_debt_sizing_extraction.csv"`

The fixture path is anchored to the repository root (parent of `app/`), not the current
working directory. This means fixture loading works regardless of what directory the
process is running from.

### Changes (5 files, +597 lines, -17 lines)

**`app/waterfall_runner.py`** (+1 line):
```python
use_frozen_excel_senior_debt_schedule=config.use_frozen_excel_senior_debt_schedule,
```
Added to the `run_waterfall_v3_core(...)` call. This was the missing link.

**`app/waterfall_core.py`** (+67 lines):

Phase 8 block now checks `use_fixture = use_frozen_excel_senior_debt_schedule and code=='TUHO-WIND-1'`.
If True, loads CSV by `operating_period_index`, builds explicit sizing CFADS from `macro_r50_sizing_cfads_keur`
and DSCR schedule from `ds_r19_target_dscr`, then passes `use_explicit_sizing_cfads=True`.

**`tests/test_phase23d_prep_tuho_fixture_backed_frozen_senior_ds.py`** (new):
11 tests covering fixture wiring, path robustness, fallback behavior, and audit marker semantics.

**`tests/test_phase23c_shl_distribution_lockup_review_frozen_schedule.py`** (+38/-17):
Updated 2 blocker tests (`test_tuho_senior_ds_unchanged_when_frozen_on` → `test_tuho_senior_ds_differs_when_frozen_on`,
`test_tuho_frozen_path_is_not_fixture_backed_yet` → `test_tuho_frozen_path_is_fixture_backed`)
to confirm Phase 23D resolves the PR #300 blocker.

---

## Fallback and Warning Behavior

When the fixture CSV cannot be loaded (file missing, parse error, etc.):

1. `result._frozen_fixture_loaded = False`
2. `result._frozen_fixture_error = str(exc) or type(exc).__name__`
3. `result._frozen_fixture_note` is set to a descriptive warning message
4. A `warnings.warn(...)` is emitted with full context including the resolved CSV path
5. `explicit_sizing_cfads = None` → falls back to EBITDA-derived sizing
6. `result._frozen_senior_ds_wired = False` (fixture path was not fully used)

**Important:** Flags ON alone is NOT sufficient to set `_frozen_fixture_loaded=True`.
The CSV must actually be opened and parsed successfully.

---

## Audit Marker Semantics

| Marker | Set when | Not set when |
|--------|----------|--------------|
| `result._frozen_fixture_loaded` | CSV was actually loaded and parsed | Fixture missing/parse error, or flags OFF |
| `result._frozen_fixture_error` | CSV load failed (error string) | CSV loaded successfully |
| `result._frozen_fixture_note` | Always set (success or failure description) | Never |
| `result._frozen_senior_ds_wired` | `True` only when frozen schedule is wired AND fixture was loaded | Frozen OFF, or fixture load failed |
| `result._frozen_senior_ds_note` | Always set when frozen schedule wired | Frozen OFF |

**Key invariant:** `_frozen_senior_ds_wired=True` implies `_frozen_fixture_loaded=True`.
The converse is not required — if the fixture path was requested but loading failed,
`_frozen_senior_ds_wired` is `False` (fallback ebitda-derivation was used).

---

## Fixture Source

**File:** `reports/phase7_tuho_senior_debt_sizing_extraction.csv`

**Key columns used:**

| Column | Description |
|--------|-------------|
| `operating_period_index` | op_idx (0-based within operating periods) — used as dict key |
| `macro_r50_sizing_cfads_keur` | Sizing CFADS for canonical wiring (Macro!R50) |
| `ds_r19_target_dscr` | Per-period DSCR target (DS!R19) |
| `ds_r20_debt_service_capacity_keur` | = sizing_cfads / dscr (canonical capacity result) |

**CSV loading rules:**
- Keep first (lowest period_index) row per op_idx with capacity > 0
- op_idx maps directly to position in operating periods tuple
- Entries with capacity = 0 are skipped (not yet operating)

---

## Fixture Period Parity Table

| op_idx | period_index | DS!R19 dscr | Macro!R50 sizing_cfads | DS!R20 capacity |
|--------|-------------|-------------|------------------------|-----------------|
| 1 | 2 | 1.2000 | 2539.63 | **2116.36** |
| 2 | 4 | 1.2000 | 2573.63 | **2144.69** |
| 3 | 6 | 1.2000 | 2573.90 | **2144.91** |
| 4 | 8 | 1.2000 | 2603.17 | **2169.31** |
| 5 | 10 | 1.2000 | 2633.97 | **2194.98** |
| 6 | 12 | 1.2000 | 2627.90 | **2189.92** |
| 7 | 14 | 1.2000 | 2691.77 | **2243.14** |
| 8 | 16 | 1.2000 | 2745.19 | **2287.66** |
| 9 | 18 | 1.2000 | 2810.55 | **2342.12** |
| 10 | 20 | 1.2000 | 2874.13 | **2395.11** |
| 11 | 22 | 1.2000 | 2923.05 | **2435.87** |
| 12 | 24 | 1.2000 | 2981.36 | **2484.47** |
| 13 | 26 | 1.4124 | 4061.18 | **2875.30** |
| 14 | 28 | 1.4126 | 3996.77 | **2829.33** |

---

## Frozen ON vs OFF Runtime Difference Table

| op_idx | period_index | frozen=OFF (kEUR) | frozen=ON (kEUR) | diff (kEUR) | fixture capacity (kEUR) |
|--------|-------------|-----------------|-----------------|-------------|------------------------|
| 1 | 1 | 2022.08 | 2116.36 | +94.29 | 2116.36 ✓ |
| 2 | 2 | 2011.90 | 2144.69 | +132.79 | 2144.69 ✓ |
| 3 | 3 | 2045.24 | 2144.91 | +99.67 | 2144.91 ✓ |
| 4 | 4 | 2041.09 | 2169.31 | +128.22 | 2169.31 ✓ |
| 5 | 5 | 2063.52 | 2194.98 | +131.46 | 2194.98 ✓ |
| 10 | 10 | 2119.99 | 2395.11 | +275.13 | 2395.11 ✓ |
| 14 | 14 | 2200.57 | 2829.37 | +628.80 | 2829.33 ✓ |

---

## Audit Markers

| Marker | Set when | Type |
|--------|----------|------|
| `result._frozen_fixture_loaded` | CSV fixture was actually loaded | `bool` |
| `result._frozen_fixture_note` | Fixture loaded → human-readable description | `str` |
| `result._frozen_senior_ds_wired` | Fixture-backed schedule was actually used | `bool` |

**Important:** `_frozen_fixture_loaded=True` is ONLY set when the CSV was opened and parsed successfully. Flags ON alone is NOT sufficient — if the CSV file is missing or corrupted, the flag stays False and the ebitda-derivation path is used as fallback.

---

## Guardrails

| Guardrail | Status |
|-----------|--------|
| G20 BLOCKED | No SHL/distribution runtime logic changes |
| R99/R102 NOT APPROVED | No Revenue/OPEX/CAPEX/Tax changes |
| TUHO factory opt-in BLOCKED | `use_frozen_excel_senior_debt_schedule=False` in factory |
| Oborovo frozen schedule NOT implemented | No CSV fixture for Oborovo |
| No hardcoded senior DS arrays | Fixture loaded from CSV at runtime |
| `_frozen_fixture_loaded` requires actual CSV load | Not triggered by flags alone |
| PR #299 remains DRAFT | Superseded by this wiring path |

---

## Factory Flag Confirmation

| Project | `use_frozen_excel_senior_debt_schedule` | `use_senior_debt_sizing_engine` |
|---------|----------------------------------------|----------------------------------|
| TUHO | **False** (factory default, not changed) | **False** (factory default, not changed) |
| Oborovo | **False** | **False** |

This PR wires the capability behind the flags but does NOT enable the flags in the factory. TUHO factory opt-in remains BLOCKED pending downstream Phase 23C rerun.

---

## Downstream Requirement

After this PR is merged, Phase 23C must be **rerun downstream** before any TUHO factory opt-in is considered. The Phase 23C SHL/distribution lock-up diagnostic must confirm that the fixture-backed frozen schedule produces acceptable SHL/distribution behavior for all 14 operating periods.

---

## Tests

| Test file | Result |
|-----------|--------|
| `tests/test_phase23d_prep_tuho_fixture_backed_frozen_senior_ds.py` | 10 passed |
| `tests/test_phase23c_shl_distribution_lockup_review_frozen_schedule.py` | 23 passed (2 xfailed, 1 xpassed) |
| `tests/test_tuho_shl_calibration.py` | 7 passed |
| **Total** | **40 passed, 2 xfailed, 1 xpassed** |

---

## Changed Files

| File | Change |
|------|--------|
| `app/waterfall_core.py` | +67 lines: Phase 23D fixture wiring in canonical SeniorDebtSizing |
| `app/waterfall_runner.py` | +1 line: pass `use_frozen_excel_senior_debt_schedule` to waterfall_core |
| `tests/test_phase23c_shl_distribution_lockup_review_frozen_schedule.py` | +38/-17: updated blocker tests to fixed state |
| `tests/test_phase23d_prep_tuho_fixture_backed_frozen_senior_ds.py` | New: 10 tests for fixture wiring verification |