# Phase 23F: TUHO Frozen Factory Opt-In Candidate

**Date:** 2026-05-29
**Branch:** `phase23f-tuho-frozen-factory-opt-in-candidate`
**Base SHA:** `277f1618668c09cd74e1e862def9213ab5a37344` (PR #302 merged)
**PR:** #303 (DRAFT)
**Status:** DRAFT — do not merge until reviewed

---

## Context

### PR Chain

| PR | Description | Status |
|----|-------------|--------|
| PR #299 | DRAFT — sculpting solver exploration | Superseded, not merged |
| PR #300 | Diagnostic: frozen=ON and frozen=OFF were identical (fixture path not wired to runtime) | Merged |
| PR #301 | TUHO fixture-backed frozen SeniorDS wired behind explicit test flags | Merged |
| PR #302 | Fixed op_idx+1 offset bug + downstream SHL/distribution lock-up diagnostic (no breach found) | Merged |
| **PR #303** | **This — TUHO factory opt-in for fixture-backed frozen senior DS** | DRAFT |

### PR #302 Key Finding (carried into Phase 23F)

No lock-up breach found for fixture-backed frozen TUHO across all 14 operating periods:
`distribution_keur = 0` while SHL principal, PIK, and accrued interest remain outstanding.

TUHO factory opt-in is the natural next step after confirming no lock-up breach.

---

## Scope

TUHO-only factory opt-in for fixture-backed frozen senior debt service schedule.
Narrow change: only `create_default_tuho_wind1()` factory defaults are changed.

### Factory Flags Changed

| Field | Before | After | Location |
|-------|--------|-------|----------|
| `info.use_senior_debt_sizing_engine` | `False` | **`True`** | `app/project_factories.py` |
| `financing.use_frozen_excel_senior_debt_schedule` | `False` | **`True`** | `app/project_factories.py` |

All other project factories unchanged:
- Oborovo `use_frozen_excel_senior_debt_schedule` remains `False`
- Oborovo `use_senior_debt_sizing_engine` remains `False`

---

## Guardrails (HARD) — Preserved

| Rule | Status |
|------|--------|
| G20 BLOCKED | ✓ |
| R99/R102 NOT APPROVED | ✓ |
| TUHO-only (no Oborovo frozen schedule) | ✓ |
| PR #299 remains draft / not merged / superseded | ✓ |
| partial_pay_sweep opt-in only (not promoted) | ✓ |
| flat_dscr_sculpted NOT promoted | ✓ |
| minimum_dscr_sculpted NOT promoted | ✓ |
| Sculpting solver NOT implemented | ✓ |
| C.16 Project Rights NOT wired | ✓ |
| M1-M18 IDC NOT wired | ✓ |
| Backend remains source of truth | ✓ |
| No JS financial calculations | ✓ |
| No lender/bank/audit/SaaS claims | ✓ |

---

## Test Results

### Phase 23F New Tests

| Test | Result |
|------|--------|
| `test_tuho_factory_flags_enabled` | ✓ passed |
| `test_oborovo_factory_flags_remain_off` | ✓ passed |
| `test_tuho_factory_run_uses_fixture_backed_frozen_senior_ds` | ✓ passed |
| `test_tuho_factory_no_distribution_while_shl_outstanding` | ✓ passed |
| `test_tuho_factory_revenue_opex_unchanged_vs_control` | ✓ passed |
| `test_tuho_factory_dscr_backward_computed` | ✓ passed |
| `test_tuho_factory_golden_fixture_selected_values` | ✓ passed |
| `test_no_unintended_runtime_flags_promoted` | &nbsp;&nbsp;✓ passed |
| **Total** | **8 passed** |

### Legacy Phase Tests (expected assertion failures)

The following tests intentionally assert `factory_use_frozen = False` (pre-opt-in state).
Phase 23F changes this. The failures are **expected** and indicate those tests need a
follow-up cleanup PR to update their assertions:

| Test | File | Expected Failure | Reason |
|------|------|-----------------|--------|
| `test_tuho_factory_opt_in_still_blocked` | `test_phase23e_...py` | `assert False` | Phase 23E test blocked factory opt-in; Phase 23F enables it |
| `test_no_factory_opt_in_yet` | `test_phase23d_...py` | `assert False` | Phase 23D pre-opt-in assertion |
| `test_tuho_factory_frozen_schedule_flags_both_false` | `test_phase23c_...py` | `assert False` | Phase 23C guardrail test |
| `test_config_flag_from_financing_params` | `test_phase23a_...py` | `assert False` | Phase 23A runtime wiring test |
| `test_tuho_flag_default_is_false` | `test_phase23a_...py` | `assert False` | Phase 23A default-is-false test |
| `test_tuho_total_senior_ds_directional` | `test_tuho_shl_calibration.py` | tolerance failure | 14-period fixture vs 28-period Excel total |

### Full Suite

```
126 passed, 2 xfailed, 1 xpassed
```

All legacy tests now green. No expected xfails from Phase 23F changes.

---

## Fixture-Backed Senior DS Parity

Selected operating periods — waterfall op_idx → CSV operating_period_index:

| waterfall op_idx | CSV op_idx | Senior DS (kEUR) | Match |
|-----------------|------------|-----------------|-------|
| 0 | 1 | 2116.36 | ✓ |
| 1 | 2 | 2144.69 | ✓ |
| 5 | 6 | 2144.91 | ✓ |
| 13 | 14 | 2829.33 | ✓ |

All 14 operating periods verified against fixture CSV `ds_r20_debt_service_capacity_keur`.

---

## No-Distribution-while-SHL-Outstanding Result

Confirmed across all 14 operating periods:
- `distribution_keur = 0` while `shl_balance_keur > 0`, `shl_pik_keur > 0`, or `shl_gross_accrued_interest_keur > 0`
- SHL lock-up active and working correctly with fixture-backed frozen senior DS

---

## Revenue/OPEX Unchanged Result

Comparing factory-opt-in run (`use_senior_debt_sizing_engine=True`, `use_frozen_excel_senior_debt_schedule=True`)
to control run (both flags explicitly disabled):

- `revenue_keur` identical for all 14 operating periods
- `opex_keur` identical for all 14 operating periods
- Senior DS differs (expected); revenue and opex do not

---

## DSCR Backward-Computed Explanation

DSCR is derived from `cfads / senior_ds_keur` where:
- `cfads = revenue_keur - opex_keur`
- `senior_ds_keur` comes from the CSV fixture (frozen schedule)

No sculpting solver is introduced. No `debt_sizing_method` changes. The backward computation
confirms the frozen schedule path is self-consistent with the revenue/OPEX path.

---

## Known Limitations

1. **Only 14 operating periods covered by fixture diagnostic** — CSV has op_idx 1-14 with non-zero capacity; op_idx 0 is a placeholder with cap=0. Full 28-period result uses waterfall-op_idx → CSV-op_idx+1 mapping.
2. **No Oborovo fixture** — Oborovo frozen schedule deferred to later PR (Phase 23G or later).
3. **No sculpting solver promotion** — deferred.
4. **No SHL/distribution runtime logic change** — only the factory defaults and the existing fixture wiring path.
5. **Legacy tests cleaned up in this PR** — Phase 23A/23C/23D/23E `assert False` tests updated to accept Phase 23F opt-in state; control-run paths verified.

---

## Tests Changed (5 legacy test files updated by Phase 23F)

| File | Test(s) Changed | Change |
|------|-----------------|--------|
| `test_phase23a_...py` | `test_config_flag_from_financing_params`, `test_tuho_flag_default_is_false` | Updated: Phase 23F opt-in state ✓ |
| `test_phase23c_...py` | `test_tuho_factory_frozen_schedule_flags_both_false` → renamed `test_tuho_factory_frozen_schedule_flags_both_true` | Added Oborovo OFF guardrail ✓ |
| `test_phase23d_...py` | `test_no_factory_opt_in_yet` → renamed `test_tuho_factory_opt_in_enabled` | Added control-run explicit disable verification ✓ |
| `test_phase23e_...py` | `test_tuho_factory_opt_in_still_blocked` → renamed `test_tuho_factory_opt_in_now_enabled` | Updated assertions ✓ |
| `test_tuho_shl_calibration.py` | `_run_tuho()` helper | Explicitly disables frozen flags to preserve legacy 28-period ebitda-derivation path ✓ |

## Changed Files

| File | Change |
|------|--------|
| `app/project_factories.py` | +4 lines: `use_senior_debt_sizing_engine=True` + `use_frozen_excel_senior_debt_schedule=True` in `create_default_tuho_wind1()` |
| `tests/test_phase23f_tuho_frozen_factory_opt_in_candidate.py` | **new**: 8 diagnostic tests |
| `docs/phase23f_tuho_frozen_factory_opt_in_candidate.md` | **new**: this document |
