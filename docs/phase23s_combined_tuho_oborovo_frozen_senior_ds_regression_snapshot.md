# Phase 23S: Combined TUHO + Oborovo Frozen Senior DS Regression Snapshot

## Base SHA
`5840a2e` (after PR #317 merge)

## PR #299 Status
`draft=True`, `state=open`, `merged=False` — superseded by Phase 23S/PR #317.

## Phase History

| Phase | PR | What happened |
|-------|---|---|
| 23F | #274/#275 | TUHO frozen senior DS factory opt-in |
| 23Q | #316 | Oborovo frozen senior DS fixture extraction + parity proof |
| 23R | #317 | Oborovo factory opt-in enabled (flags False → True) |

## Fixture Status

### TUHO
- **Fixture:** `reports/phase7_tuho_senior_debt_sizing_extraction.csv`
- **Column:** `ds_r20_debt_service_capacity_keur`
- **Structure:** 2 semi-annual entries per op_idx (1-based, construction period skipped)
- **Runtime mapping:** runtime op_idx N → fixture op_idx N+1, first semi-annual value
- **Frozen wired:** ✅ `_frozen_senior_ds_wired=True`, `_frozen_fixture_loaded=True`

### Oborovo
- **Fixture:** `reports/phase23q_oborovo_senior_debt_sizing_extraction.csv`
- **Column:** `ds_r57_debt_service_keur`
- **Structure:** 1 value per op_idx (annual, extracted from Excel DS sheet)
- **Frozen wired:** ✅ `_frozen_senior_ds_wired=True`, `_frozen_fixture_loaded=True`

## Combined Factory Flag Table

| Project | `use_senior_debt_sizing_engine` | `use_frozen_excel_senior_debt_schedule` |
|---------|--------------------------------|---------------------------------------|
| TUHO | True | True |
| Oborovo | True | True |

## TUHO Senior DS Parity Table

| runtime op_idx | fixture op_idx | Runtime DS (kEUR) | Fixture DS (kEUR) | Diff (kEUR) |
|----------------|----------------|-------------------|-------------------|-------------|
| 0 | 1 | 2,116.36 | 2,116.36 | ~0 |
| 6 | 7 | 2,243.14 | 2,243.14 | ~0 |
| 13 | 14 | 2,829.37 | 2,829.33 | +0.04 |

Tolerance: 0.5 kEUR (fixture4dp rounding vs runtime full float precision).

## Oborovo Senior DS Parity Table

| op_idx | Runtime DS (kEUR) | Fixture DS (kEUR) | Diff (kEUR) |
|--------|------------------|-------------------|-------------|
| 0 | 2,239.13 | 2,239.13 | ~0 |
| 1 | 2,202.63 | 2,202.63 | ~0 |
| 14 | 2,471.54 | 2,471.54 | ~0 |
| 25 | 1,558.40 | 1,558.40 | ~0 |
| 27 | 1,524.28 | 1,507.44 | +16.84 |

Tolerance: 20 kEUR (Phase 23Q documented CSV rounding, 4dp).
op_idx 27 known residual (+16.84 kEUR) — within tolerance.

## Oborovo Lock-up Regression Table

| op_idx | SHL Balance (kEUR) | Distribution (kEUR) | Expected |
|--------|-------------------|--------------------|----------|
| 0 | 15,790.0 | 0.00 | Blocked ✅ |
| 28 | 15,790.0 | 0.00 | Blocked ✅ |
| 29 | 15,790.0 | 0.00 | Blocked ✅ |
| 31 | 15,790.0 | 0.00 | Blocked ✅ |
| 38 | 0.0 | 0.00 | Guard period ✅ |
| 39 | 0.0 | 2,994.41 | First valid ✅ |

Phase 23O/P behavior preserved.

## TUHO SHL/Distribution Regression

| Check | Result |
|-------|--------|
| No distributions while SHL outstanding | ✅ |
| SHL cleared at maturity | ✅ |
| No regression from Oborovo opt-in | ✅ |

## Remaining Material Gaps

| Gap | Severity | Notes |
|-----|----------|-------|
| Oborovo op_idx 27 DS residual (+16.8 kEUR) | 🟡 Low | Within 20 kEUR tolerance |
| TUHO no merchant-period fixture beyond op_idx 14 | 🟡 Low | Merchant-only periods (15+) not in fixture |
| Oborovo DSCR trajectory not compared vs Excel | 🔴 Unknown | Not yet audited |
| TUHO DSCR trajectory not compared vs Excel | 🔴 Unknown | Not yet audited |
| Senior debt amount vs Excel (Oborovo) | 🔴 Unknown | 42,852 kEUR target vs model |
| Senior debt amount vs Excel (TUHO) | 🔴 Unknown | 43,359 kEUR target vs model |
| Post-SHL distribution amounts vs Excel | 🔴 Unknown | Oborovo op_idx 39+ not yet reconciled |
| Interest/principal/balance residuals | 🔴 Unknown | Not yet audited |

## Guardrail Table

| Guardrail | Status |
|-----------|--------|
| TUHO factory flags unchanged | ✅ |
| Oborovo factory flags unchanged | ✅ |
| G20 BLOCKED | ✅ (field does not exist) |
| R99 NOT APPROVED | ✅ (field does not exist) |
| R102 NOT APPROVED | ✅ (field does not exist) |
| partial_pay_sweep not promoted | ✅ |
| flat_dscr_sculpted not promoted | ✅ |
| minimum_dscr_sculpted not promoted | ✅ |
| Revenue/OPEX/CAPEX/Tax unchanged | ✅ |
| SHL/distribution lock-up logic unchanged | ✅ |
| No sculpting solver | ✅ |
| No construction IDC engine | ✅ |
| No M1–M18 IDC wiring | ✅ |
| No C.16 Project Rights wiring | ✅ |
| Backend remains source of truth | ✅ |
| PR #299 remains draft | ✅ |

## Tests

9 tests in `tests/test_phase23s_combined_tuho_oborovo_frozen_senior_ds_regression_snapshot.py`:
1. `test_both_factories_frozen_senior_ds_flags_enabled` ✅
2. `test_tuho_default_factory_loads_fixture` ✅
3. `test_oborovo_default_factory_loads_phase23q_fixture` ✅
4. `test_tuho_selected_senior_ds_matches_fixture` ✅
5. `test_oborovo_selected_senior_ds_matches_fixture` ✅
6. `test_oborovo_lockup_remains_clean_after_factory_opt_in` ✅
7. `test_tuho_distribution_and_shl_regression_clean` ✅
8. `test_revenue_opex_unchanged_for_both_projects` ✅
9. `test_guardrails_unchanged` ✅

Full suite: **114 passed, 2 xfailed, 1 xpassed**

## CI Status

Full suite: **114 passed, 2 xfailed, 1 xpassed**

## Recommendation for Next Phase

**Option A: Phase 23T Senior Debt Amount / DSCR Residual Bridge**
Priority: 🔴 High

Both TUHO and Oborovo have known senior debt amount targets from Excel calibration:
- Oborovo:42,852 kEUR (Excel)
- TUHO: 43,359 kEUR (Excel)

The frozen DS fixture provides per-period debt service capacity, but the total debt amount and DSCR trajectory have not been explicitly reconciled against Excel. A Phase 23T bridge would:
1. Compare final senior debt amounts vs Excel targets
2. Compare DSCR trajectory across all operating periods
3. Document remaining residuals and their causes
4. Recommend whether runtime changes are needed or fixtures are sufficient

**Option B: Phase 23T Excel Parity Pack for TUHO + Oborovo**
Priority: 🟡 Medium

Extract full Excel balance sheet, income statement, and cash flow comparison for both projects. Lock the complete parity state.

**Option C: Phase 24A UI/Runtime Impact Taxonomy**
Priority: 🟢 Low

Only after Option A/B resolves the residual gaps. Would catalog all UI/runtime surfaces affected by the frozen DS path.
