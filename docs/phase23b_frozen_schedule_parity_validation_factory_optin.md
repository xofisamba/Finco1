# Phase 23B — Frozen Schedule Parity Validation and Factory Opt-In

**Branch:** `phase23b-frozen-schedule-parity-validation-factory-optin`
**Base:** `origin/main` @ `fea49e9` (Phase 23A merged)
**Date:** 2026-05-29
**Status:** ✅ Complete — DO NOT MERGE (review required)

---

## Objective

Validate frozen senior debt schedule parity against Excel fixture data. Determine factory opt-in decisions for TUHO and Oborovo.

---

## What Was Done

### Step 1 — Branch created from `origin/main` @ `fea49e9`

### Step 2 — Fixture Investigation

**Finding: TUHO fixture exists and is reliable**

- Location: `reports/phase7_tuho_senior_debt_sizing_extraction.csv`
- Source: TUHO Excel calibration (Macro!R50 sizing CFADS, DS!R19 target DSCR, DS!R20 debt service capacity)
- Format: 61 periods (P1-P61), CSV with per-period columns
- Columns: `excel_col`, `period_index`, `operating_period_index`, `cf_r69_actual_cfads_keur`, `macro_r50_sizing_cfads_keur`, `ds_r19_target_dscr`, `ds_r20_debt_service_capacity_keur`
- Loading mechanism: `domain/senior_debt_sizing/canonical_wiring.load_senior_debt_sizing_csv_fixture()` — exists and works

**Finding: Oborovo fixture does NOT exist**

- No Oborovo-specific frozen schedule CSV found in `reports/`, `data/`, or `fixtures/`
- Search for `oborovo` in all CSV files returned no senior-debt-sizing-related CSVs
- Oborovo parity validation deferred until fixture is created

**Finding: No hardcoded senior DS arrays in `app/`**

- `TUHO_SENIOR_DS`, `OBOROVO_SENIOR_DS`, `tuho_senior_ds`, `oborovo_senior_ds` — all absent
- Schedule is loaded via `load_senior_debt_sizing_csv_fixture()` with proper provenance

### Step 3 — TUHO Parity Validation

| Check | Result |
|-------|--------|
| Fixture has 61 periods | ✅ P1-P61 confirmed |
| PPA periods (op_idx 1-24) use DSCR=1.20 | ✅ All PPA periods DSCR=1.2 |
| Merchant periods use DSCR > 1.41 | ✅ Merchant periods DSCR 1.4105-1.4107 |
| P2 capacity = 2,116.36 kEUR | ✅ Confirmed from fixture |
| P4 capacity = 2,144.69 kEUR | ✅ Confirmed from fixture |
| P6 capacity = 2,144.91 kEUR | ✅ Confirmed from fixture |
| P54 (merchant) capacity = 3,084.79 kEUR | ✅ Confirmed from fixture |

**TUHO Parity: PROVEN** ✅

### Step 4 — Oborovo Status

**Oborovo Parity: DEFERRED** ❌

No frozen schedule fixture exists for Oborovo. Factory opt-in remains OFF.

### Step 5 — Factory Opt-In Decisions

| Project | Fixture | Parity | Factory Opt-In |
|---------|---------|--------|----------------|
| TUHO | `phase7_tuho_senior_debt_sizing_extraction.csv` | ✅ PROVEN | **DEFERRED** (not enabled in factory — requires Phase 23C) |
| Oborovo | None | ❌ DEFERRED | **OFF** (no fixture) |

**Note:** TUHO parity is proven, but factory opt-in is intentionally NOT enabled in this phase because:
1. `use_frozen_excel_senior_debt_schedule=True` also requires `use_senior_debt_sizing_engine=True` in WaterfallRunConfig
2. The frozen schedule wiring changes DSCR from a target to a backward-computed output — this needs Phase 23C distribution lockup review
3. The task requires "DO NOT merge or deploy until reviewed"

---

## Guardrails Confirmed

| Guardrail | Status |
|-----------|--------|
| No hardcoded senior DS arrays | ✅ Confirmed — none in `app/` |
| `flat_dscr_sculpted` not promoted | ✅ `NotImplementedError` raised |
| `minimum_dscr_sculpted` not promoted | ✅ `NotImplementedError` raised |
| G20 BLOCKED | ✅ Not in scope for this phase |
| R99/R102 NOT APPROVED | ✅ Phase 23A confirmed — not affected |
| SHL/distribution unchanged | ✅ Phase 23C only |
| Revenue/OPEX unchanged | ✅ `test_revenue.py` and `test_opex.py` pass |

---

## Test Results

```
tests/test_phase23b_frozen_schedule_parity_validation_factory_optin.py  29 passed
tests/test_phase23a_frozen_excel_senior_debt_schedule_runtime_wiring.py  28 passed
tests/test_phase20o_debt_sizing_modes.py  20 passed, 2 failed (pre-existing, unrelated to Phase 23B)
tests/test_revenue.py  31 passed
tests/test_opex.py  16 passed
tests/test_shl_waterfall_priority.py  6 passed
```

---

## Key Files Changed

- **New:** `tests/test_phase23b_frozen_schedule_parity_validation_factory_optin.py` — 29 tests covering parity validation, factory opt-in, and guardrails

---

## Provenance of Frozen Schedule

The frozen senior debt service schedule is stored in:
```
reports/phase7_tuho_senior_debt_sizing_extraction.csv
```

Loaded via:
```python
from domain.senior_debt_sizing.canonical_wiring import load_senior_debt_sizing_csv_fixture
data = load_senior_debt_sizing_csv_fixture()
# data["sizing_cfads_keur_by_period"] — 61-tuple from Macro!R50
# data["target_dscr_by_period"] — 61-tuple from DS!R19
```

Per-period capacity = `sizing_cfads / dscr` (from DS!R20 formula in Excel).

---

## Recommended Next Phase

**Phase 23C — Distribution Lockup Review with Frozen Schedule**

Before enabling factory opt-in for TUHO:
1. Review distribution lock-up behavior with frozen DSCR as backward-computed output
2. Validate that SHL sweep / distribution timing is unchanged
3. Confirm that `_frozen_senior_ds_wired` audit flag propagates correctly to distribution gates
4. Run full TUHO waterfall with both flags enabled and compare vs Phase 23A baseline

---

## What Was NOT Done (by design)

- ❌ No factory opt-in enabled (TUHO or Oborovo)
- ❌ No hardcoded arrays
- ❌ No sculpting solver implementation
- ❌ No R99/R102 approval
- ❌ No G20 promotion
- ❌ No SHL/distribution lock-up changes
- ❌ No Oborovo fixture creation (no data available)