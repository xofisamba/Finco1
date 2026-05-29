# Phase 23C — SHL / Distribution Lock-up Review with Frozen Senior Debt Schedule

## Executive Summary

Diagnostic review of TUHO downstream SHL/distribution behavior when frozen senior debt schedule is enabled. This phase makes **no runtime changes** — it is purely diagnostic and produces a recommendation.

**TUHO Lock-up Result: PASS ✅**
- No distribution while SHL principal balance > 0
- First distribution (idx=35) occurs exactly when SHL principal clears to 0
- TUHO factory opt-in **BLOCKED** — CSV fixture not wired; Phase 23C validates downstream behavior only on the current non-fixture-backed path

**Oborovo: Diagnostic-only** — no frozen schedule fixture exists; distribution leak (19 instances) remains documented, fix deferred to Phase 23D.

---

## Relationship to Prior Phases

| Phase | Description |
|---|---|
| Phase 23A | Wired frozen schedule behind `use_frozen_excel_senior_debt_schedule` + `use_senior_debt_sizing_engine` flags; **CSV fixture NOT loaded** |
| Phase 23B | Proved TUHO frozen schedule parity (DRAFT PR #299) — must also address CSV fixture loading |
| Phase 23C (this) | Validates downstream SHL/distribution behavior only on the current non-fixture-backed path; TUHO factory opt-in remains BLOCKED |

---

## Critical Finding: CSV Fixture Not Wired

The frozen schedule CSV fixture (`reports/phase7_tuho_senior_debt_sizing_extraction.csv`) is **not currently loaded** in the canonical sizing path.

In `waterfall_core.py`, `build_canonical_senior_debt_sizing_from_inputs` is called with `use_explicit_sizing_cfads=False`, meaning it derives sizing CFADS from EBITDA × (1 - tax_rate) — not from the CSV fixture's `macro_r50_sizing_cfads_keur` column.

**Result:** With current code, `frozen=ON` and `frozen=OFF` produce **identical** senior DS values.

| Mode | Senior DS at P4 (kEUR) |
|---|---|
| DEFAULT | 2,045.2 |
| FROZEN | 2,045.2 |

Phase 23B parity proof (PR #299) must address CSV fixture loading to make the frozen schedule path actually differ from the default.

---

## TUHO Downstream Diagnostic Results

### Test Summary (25 tests — all PASS)

| Check | Result |
|---|---|
| TUHO runs with both flags ON | ✅ PASS |
| Senior DS unchanged when frozen ON | ✅ PASS (CSV fixture not wired — gap identified) |
| Revenue unchanged when frozen ON | ✅ PASS |
| OPEX unchanged when frozen ON | ✅ PASS |
| SHL closing balance non-negative | ✅ PASS |
| Distribution = 0 while SHL principal > 0 | ✅ PASS (0 leak instances) |
| No distribution leak | ✅ PASS |
| First dist only after SHL principal cleared | ✅ PASS (idx=35, shl_bal→0.0 at same idx) |

### TUHO Distribution Timeline

| Period Index | is_operation | SHL Balance (kEUR) | Distribution (kEUR) |
|---|---|---|---|
| 0–24 | Yes (PPA) | Growing (PIK accrual) | 0 |
| 25–28 | Yes (Merchant) | ~38,028 (plateau) | 0 |
| 29 | Yes | 33,340 | 0 |
| 30 | Yes | 29,326 | 0 |
| 31 | Yes | 24,257 | 0 |
| 32 | Yes | 19,827 | 0 |
| 33 | Yes | 14,187 | 0 |
| 34 | Yes | 9,189 | 0 |
| **35** | **Yes** | **0.0** | **5,571.6** ← first distribution |
| 36 | Yes | 0.0 | 6,735.9 |
| 37 | Yes | 0.0 | 5,797.4 |

**TUHO uses PIK-then-sweep:** SHL balance grows via PIK capitalization during construction + PPA periods, then sweeps to zero at idx=35. Distributions begin exactly when balance clears.

### TUHO Accrued Interest Observation

At first distribution (idx=35):
- `shl_balance_keur = 0.0` ✅
- `shl_gross_accrued_interest_keur = 119.1` ⚠️ (not cleared to 0)
- `distribution_keur = 5,571.6`

**Issue:** TUHO distributes while accrued but unpaid SHL interest is still outstanding. A narrow fix in Phase 23D could add a lock: `no distribution while shl_gross_accrued_interest_keur > 0`.

---

## Oborovo Diagnostic

### Distribution Leak (Pre-existing, Documented Since Phase 20O)

| Period Index | SHL Balance (kEUR) | Distribution (kEUR) |
|---|---|---|
| 0 | 14,716.2 | 51.7 |
| 1 | 14,716.2 | 50.9 |
| 2 | 14,716.2 | 36.6 |
| 3 | 14,716.2 | 36.1 |
| 4 | 14,716.2 | 25.9 |
| ... | ... | ... |

**19 total leak instances** — Oborovo distributes while SHL principal is outstanding.

### No Frozen Schedule Fixture

No CSV fixture exists for Oborovo in `reports/`. The `use_frozen_excel_senior_debt_schedule` flag is not set in `create_default_oborovo`.

---

## Factory Opt-in Status

### TUHO Factory Opt-in BLOCKED

TUHO downstream SHL/distribution lock-up checks pass on the current non-fixture-backed path, but this does not prove fixture-backed frozen senior DS behavior. TUHO factory opt-in is BLOCKED until Phase 23B wires the CSV fixture into canonical senior debt sizing and Phase 23C is rerun with senior DS actually changing.

**Changes needed:**
1. Phase 23B: Wire `load_senior_debt_sizing_csv_fixture()` into `build_canonical_senior_debt_sizing_from_inputs` with `use_explicit_sizing_cfads=True`
2. Then: Set `use_senior_debt_sizing_engine=True` and `use_frozen_excel_senior_debt_schedule=True` in `create_default_tuho_wind1()`

---

## Guardrails Confirmed

| Guardrail | Status |
|---|---|
| No hardcoded senior DS arrays | ✅ |
| No sculpting solvers | ✅ |
| `partial_pay_sweep` remains opt-in | ✅ |
| TUHO factory opt-in BLOCKED | CSV fixture not wired — Phase 23B/23D first |
| Oborovo lock-up NOT implemented | ✅ |
| G20 BLOCKED | ✅ |
| R99/R102 NOT APPROVED | ✅ |

---

## What Changed

**No runtime changes — diagnostic only.**

- `scripts/phase23c_tuho_frozen_downstream_diagnostic.py` — diagnostic helper (committed)
- `tests/test_phase23c_shl_distribution_lockup_review_frozen_schedule.py` — 25 tests, all pass
- `docs/phase23c_shl_distribution_lockup_review_frozen_schedule.md` — this document

---

## CI / Packaging Note

This PR adds `pyproject.toml` so that `pip install -e .` works correctly in GitHub Actions. CI runs only targeted Phase 23C-related test suites because the full pytest suite has pre-existing collection/import issues (missing optional packages like bcrypt) that are outside Phase 23C scope.

Full-suite pytest cleanup should be a separate effort, not part of Phase 23C.

---

## Next Recommended Phase

**Phase 23D:** Two independent tracks:

**Track 1 (TUHO):** Enable TUHO factory opt-in (requires Phase 23B CSV fixture wiring + parity confirmation)

**Track 2 (Oborovo):** Implement narrow distribution lock-up:
```
no distribution while shl_balance_keur > 0
no distribution while shl_gross_accrued_interest_keur > 0  # narrow fix
```
(TUHO should also get the accrued-interest lock as part of Track 2)

---

## Test Results

```
tests/test_phase23c_shl_distribution_lockup_review_frozen_schedule.py  25 passed
tests/test_phase23a_frozen_excel_senior_debt_schedule_runtime_wiring.py  28 passed
tests/test_shl_waterfall_priority.py                                      6 passed
tests/test_tuho_shl_calibration.py                                       8 passed (2 xfail, 1 xpass)
tests/test_revenue.py                                                    16 passed
tests/test_opex.py                                                      15 passed
```

**Total: 98 passed, 2 xfailed, 1 xpassed** (xpass in `test_tuho_first_distribution_period_is_p36` — pre-existing calibration target)
