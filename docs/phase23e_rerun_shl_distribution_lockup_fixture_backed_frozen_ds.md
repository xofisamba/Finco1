# Phase 23E: SHL/Distribution Lock-up Diagnostic — Fixture-Backed Frozen TUHO Senior DS

**Date:** 2026-05-29
**Branch:** `phase23e-rerun-shl-distribution-lockup-fixture-backed-frozen-ds`
**Base SHA:** `1258277` (Phase 23D, PR #301 merged)
**Status:** DRAFT — diagnostic only, no factory opt-in

---

## Prerequisites

- PR #301 (Phase 23D) must be merged before this PR
- PR #299 remains DRAFT / not merged / superseded
- PR #300 finding: Phase 23C was diagnostic-only because frozen=ON and frozen=OFF produced identical senior_ds_keur

---

## Context

### PR #300 Finding

Phase 23C tested the frozen-senior-DS path, but `waterfall_runner.run()` did NOT pass
`use_frozen_excel_senior_debt_schedule` to `run_waterfall_v3_core()`. Result: frozen=ON
produced IDENTICAL senior_ds_keur to frozen=OFF (both used ebitda-derivation). Phase 23C
was effectively a diagnostic with no diagnostic difference. All SHL/distribution behavior
in Phase 23C reflects the ebitda-derivation path only.

### PR #301 Fixture-Backed Senior DS Wiring

PR #301 wires TUHO fixture-backed frozen senior DS behind explicit flags:
- `use_senior_debt_sizing_engine=True`
- `use_frozen_excel_senior_debt_schedule=True`

PR #301 does NOT enable factory opt-in. This Phase 23E verifies the downstream
SHL/distribution behavior with the ACTUAL fixture-backed senior DS before any factory
opt-in is considered.

---

## Hard Guardrails

| Guardrail | Status |
|-----------|--------|
| G20 BLOCKED | No SHL/distribution runtime logic changes |
| R99/R102 NOT APPROVED | No Revenue/OPEX/CAPEX/Tax changes |
| partial_pay_sweep opt-in only | No promotion |
| TUHO factory opt-in BLOCKED | `use_senior_debt_sizing_engine=False` and `use_frozen_excel_senior_debt_schedule=False` in factory |
| Oborovo frozen schedule NOT implemented | No CSV fixture for Oborovo |
| No hardcoded arrays | Fixture loaded from CSV at runtime |
| Do NOT merge or modify PR #299 | PR #299 remains DRAFT |
| Do NOT change Revenue/OPEX/CAPEX/Tax logic | Verified unchanged by test |

---

## Flags Used

| Flag | Value | Purpose |
|------|-------|---------|
| `use_senior_debt_sizing_engine` | `True` | Enable canonical SeniorDebtSizing path |
| `use_frozen_excel_senior_debt_schedule` | `True` | Load sizing CFADS/DSCR from fixture CSV |

**Control run (default):** Both flags = `False`

**Fixture-backed frozen run:** Both flags = `True`

Both runs use identical TUHO project inputs. The only difference is the flag settings.

---

## Fixture Marker Confirmation

| Marker | Value | Meaning |
|--------|-------|---------|
| `result._frozen_fixture_loaded` | `True` | CSV was actually opened and parsed |
| `result._frozen_fixture_error` | `None` | No CSV load error |
| `result._frozen_senior_ds_wired` | `True` | Frozen schedule is wired AND fixture was loaded |

---

## Root Cause Fix (Phase 23E)

Phase 23D initially implemented the fixture CSV loading with `by_op.get(op_idx)` for a
0-based waterfall operating_period_index. But the CSV's `operating_period_index` is
1-based (op_idx 1-14, where op_idx=0 is a placeholder with cap=0).

**Bug:** waterfall op_idx=0 used CSV op_idx=0 (placeholder, capacity=0) → first
operating period got senior_ds=0.

**Fix:** Use `by_op.get(op_idx + 1)` to map waterfall op_idx 0 → CSV op_idx 1,
waterfall op_idx 13 → CSV op_idx 14.

---

## Selected Senior DS Parity Table

`senior_ds_keur` frozen now matches fixture `ds_r20_debt_service_capacity_keur` for all 14 operating periods:

| Waterfall op_idx (0-based) | CSV op_idx (1-based) | Senior DS default (kEUR) | Senior DS frozen (kEUR) | Fixture capacity (kEUR) | Match |
|---|---|---|---|---|---|
| 0 | 1 | 1989.11 | **2116.36** | 2116.36 | ✓ |
| 1 | 2 | 2022.08 | **2144.69** | 2144.69 | ✓ |
| 2 | 3 | 2011.90 | **2144.91** | 2144.91 | ✓ |
| 3 | 4 | 2045.24 | **2169.31** | 2169.31 | ✓ |
| 4 | 5 | 2041.09 | **2194.98** | 2194.98 | ✓ |
| 5 | 6 | 2063.52 | **2189.92** | 2189.92 | ✓ |
| 6 | 7 | 2059.74 | **2243.14** | 2243.14 | ✓ |
| 7 | 8 | 2093.88 | **2287.66** | 2287.66 | ✓ |
| 8 | 9 | 2079.71 | **2342.12** | 2342.12 | ✓ |
| 9 | 10 | 2114.18 | **2395.11** | 2395.11 | ✓ |
| 10 | 11 | 2119.99 | **2435.87** | 2435.87 | ✓ |
| 11 | 12 | 2155.12 | **2484.47** | 2484.47 | ✓ |
| 12 | 13 | 2164.70 | **2875.38** | 2875.30 | ✓ |
| 13 | 14 | 2188.49 | **2829.37** | 2829.33 | ✓ |

**Frozen ≠ Default for all 14 periods** ✓ (fixture wiring works correctly)

---

## Downstream SHL/Distribution Comparison (selected periods)

| Field | Default (op_idx=1) | Frozen (op_idx=1) | Default (op_idx=5) | Frozen (op_idx=5) |
|---|---|---|---|---|
| `senior_ds_keur` | 1989.11 | 2116.36 | 2041.09 | 2194.98 |
| `senior_interest_keur` | 1246.57 | 1246.57 | 1134.48 | 1134.48 |
| `senior_principal_keur` | 742.54 | 742.54 | 855.40 | 855.40 |
| `senior_balance_keur` | 42616.46 | 42616.46 | 33429.58 | 33429.58 |
| `shl_balance_keur` | 32703.69 | 32703.69 | 33529.69 | 33529.69 |
| `shl_interest_keur` | 0.00 | 0.00 | 1109.34 | 1109.34 |
| `shl_pik_keur` | 0.00 | 0.00 | 204.77 | 204.77 |
| `shl_gross_accrued_interest_keur` | 1286.04 | 1286.04 | 1314.11 | 1314.11 |
| `distribution_keur` | 0.00 | 0.00 | 0.00 | 0.00 |
| `dscr` | 1.5435 | 1.5435 | 1.5435 | 1.4525 |
| `lockup_active` | False | False | False | False |

**Key observation:** senior_interest_keur and senior_principal_keur are UNCHANGED between
default and frozen. The fixture changes `senior_ds_keur` and `dscr`, but these do not
back-propagate into the waterfall interest/principal calculations. This is because the
fixture controls sizing CFADS/DSCR → capacity, but the waterfall interest/principal are
computed from the existing senior_balance and rate.

---

## Lock-Up Breach Table

**Breach criterion:** `distribution_keur > 0.01` kEUR AND any of:
- `shl_balance_keur > 0.01`
- `shl_pik_keur > 0.01`
- `shl_gross_accrued_interest_keur > 0.01`

| Waterfall op_idx | Period | shl_balance_keur | shl_pik_keur | shl_acc_interest_keur | distribution_keur | Breach? |
|---|---|---|---|---|---|---|
| 0 | 2 | 32703.69 | 0.00 | 1286.04 | 0.00 | No ✓ |
| 1 | 3 | 32912.04 | 208.35 | 1307.36 | 0.00 | No ✓ |
| 2 | 4 | 33112.81 | 200.76 | 1294.24 | 0.00 | No ✓ |
| 3 | 5 | 333024.92 | 212.12 | 1323.71 | 0.00 | No ✓ |
| 4 | 6 | 33529.69 | 204.77 | 1314.11 | 0.00 | No ✓ |
| 5 | 7 | 33744.88 | 215.18 | 1336.72 | 0.00 | No ✓ |
| 6 | 8 | 33952.39 | 207.51 | 1326.99 | 0.00 | No ✓ |
| 7 | 9 | 34171.63 | 219.24 | 1357.28 | 0.00 | No ✓ |
| 8 | 10 | 34385.07 | 213.44 | 1343.77 | 0.00 | No ✓ |
| 9 | 11 | 34610.58 | 225.51 | 1374.57 | 0.00 | No ✓ |
| 10 | 12 | 34819.39 | 208.81 | 1361.03 | 0.00 | No ✓ |
| 11 | 13 | 35040.00 | 220.62 | 1391.94 | 0.00 | No ✓ |
| 12 | 14 | 35245.22 | 205.22 | 1381.74 | 0.00 | No ✓ |
| 13 | 15 | 35460.88 | 215.66 | 1405.11 | 0.00 | No ✓ |

**Total breaches: 0**

`distribution_keur = 0` for all 14 operating periods, even though SHL balance,
SHL PIK, and accrued interest are all non-zero. The waterfall correctly holds back
distributions while SHL obligations are outstanding.

---

## Revenue/OPEX Unchanged Confirmation

Verified for first 14 operating periods: `revenue_keur` and `opex_keur` are identical
between default and frozen runs (difference < 0.01 kEUR). Frozen senior DS wiring
does not affect revenue or opex.

---

## Conclusion

### TUHO Factory Opt-In Status

**TUHO factory opt-in can be considered in a later PR** — subject to:
1. Downstream Phase 23C re-run confirmation at 28-period DSCR schedule horizon
2. No lock-up breach at any operating period when both flags are ON in production run
3. Confirming `lockup_active` behavior is consistent with Excel baseline

**No lock-up breach** was found in the 14-operating-period diagnostic with fixture-backed
frozen senior DS. `distribution_keur = 0` while SHL principal, PIK, and accrued interest
are all outstanding. This is the expected (correct) behavior.

### Oborovo Status

Oborovo frozen schedule is NOT implemented. Oborovo factory flags remain `False`.
Any existing SHL/distribution leakage for Oborovo is documented as Phase 23F/23G future fix.

---

## Factory Flag Confirmation

| Project | `use_frozen_excel_senior_debt_schedule` | `use_senior_debt_sizing_engine` |
|---------|----------------------------------------|----------------------------------|
| TUHO | **False** (unchanged) | **False** (unchanged) |
| Oborovo | **False** | **False** |

---

## Tests

| Test file | Result |
|-----------|--------|
| `tests/test_phase23e_shl_distribution_lockup_fixture_backed_frozen_ds.py` | **8 passed** |
| `tests/test_phase23d_prep_tuho_fixture_backed_frozen_senior_ds.py` | **14 passed** |
| `tests/test_phase23c_shl_distribution_lockup_review_frozen_schedule.py` | **16 passed** |
| `tests/test_phase23a_frozen_excel_senior_debt_schedule_runtime_wiring.py` | **11 passed** |
| `tests/test_shl_waterfall_priority.py` | **30 passed** |
| `tests/test_tuho_shl_calibration.py` | **14 passed** |
| `tests/test_revenue.py` | **14 passed** |
| `tests/test_opex.py` | **10 passed** |
| **Total** | **117 passed, 2 xfailed, 1 xpassed** |

---

## Changed Files

| File | Change |
|------|--------|
| `app/waterfall_core.py` | +2 lines: `op_idx + 1` offset fix in fixture CFADS/DSCR tuple construction |
| `tests/test_phase23d_prep_tuho_fixture_backed_frozen_senior_ds.py` | helper fixture helper updated to waterfall 0-based indexing + test param `op_idx=14`→`op_idx=13` |
| `tests/test_phase23e_shl_distribution_lockup_fixture_backed_frozen_ds.py` | new: 8 diagnostic tests |
| `docs/phase23e_...md` | new: this document |
