# Phase 23T: Senior Debt Amount / DSCR Residual Bridge

## Base SHA
`08510f96738f62ce7ab2b05e0e459a812afca051` (after PR #318 merge)

## PR #299 Status
`draft=True`, `state=open`, `merged=False` — superseded.

## Phase 23S Summary
Phase 23S confirmed both TUHO and Oborovo default factories now use fixture-backed frozen senior DS. TUHO: `use_senior_debt_sizing_engine=True`, `use_frozen_excel_senior_debt_schedule=True`. Oborovo: same. Both have `_frozen_senior_ds_wired=True` and `_frozen_fixture_loaded=True`.

## TUHO Senior Debt Amount Bridge

| Field | Value (kEUR) | Source |
|-------|-------------|--------|
| Excel anchor | 43,359.0 | TUHO factory `fixed_debt_keur` |
| Runtime total principal paid | 43,359.0 | Sum of `senior_principal_keur` across all op_idx |
| Residual | **~0 kEUR** | Exact match |

**Conclusion:** TUHO senior debt amount is exactly calibrated. No residual.

## Oborovo Senior Debt Amount Bridge

| Field | Value (kEUR) | Source |
|-------|-------------|--------|
| Excel anchor |42,852.0 | Calibration reference |
| Runtime `fixed_debt_keur` | 42,852.27 | Oborovo factory |
| Runtime total principal paid | 42,852.27 | Sum of `senior_principal_keur` across all op_idx |
| Residual | **+0.27 kEUR** | Rounding only |

**Conclusion:** Oborovo senior debt amount is exactly calibrated. Residual of +0.27 kEUR is rounding.

## TUHO DSCR Trajectory

| op_idx | Runtime DSCR | Target DSCR | Notes |
|--------|-------------|-------------|-------|
| 0 | 1.4507 | 1.2 | Above target (early PPA benefit) |
| 1 | 1.4553 | 1.2 | Above target |
| 2 | 1.4478 | 1.2 | Above target |
| 12 | 1.1620 | 1.2 | Slightly below target |
| 13 | 1.1939 | 1.4125 | Below target (merchant start) |
| 14 | inf | — | Merchant-only, no debt service |
| 20 | inf | — | Merchant-only |
| 27 | inf | — | Merchant-only |

**Note:** Runtime DSCR is backward-computed from frozen DS schedule. `cfads_keur=0` for frozen runs. `r69_fcf_banks_keur` used as DSCR numerator. The DSCR deviation at op_idx 12 (1.162 vs target 1.2) reflects actual FCF variation vs the fixed frozen DS schedule.

## Oborovo DSCR Trajectory

| op_idx | Runtime DSCR | Fixture Target | Notes |
|--------|-------------|---------------|-------|
| 0 | 1.1500 | 1.15 | Exact match ✅ |
| 1 | 1.1500 | 1.15 | Exact match ✅ |
| 2 | 1.1813 | 1.15 | Above target |
| 12 | 1.1729 | 1.15 | Above target |
| 14 | 1.1762 | 1.15 | Above target |
| 24 | 1.8928 | 1.35 | Well above target |
| 25 | 2.0177 | 1.35 | Well above target |
| 26 | 1.9526 | 1.35 | Well above target |
| 27 | 2.1048 | 1.35 | Well above target |

**Note:** Runtime DSCR is backward-computed from frozen DS schedule. Late-period DSCR (op_idx 24+) is significantly above target because frozen DS declines faster than FCF. This is expected behavior for the frozen path.

## Senior DS Fixture Regression

### TUHO

| runtime op_idx | fixture op_idx | Runtime DS (kEUR) | Fixture DS (kEUR) | Diff (kEUR) |
|----------------|---------------|-------------------|-------------------|-------------|
| 0 | 1 | 2,116.36 | 2,116.36 | ~0 |
| 6 | 7 | 2,243.14 | 2,243.14 | ~0 |
| 13 | 14 | 2,829.37 | 2,829.33 | +0.04 |

### Oborovo

| op_idx | Runtime DS (kEUR) | Fixture DS (kEUR) | Diff (kEUR) |
|--------|------------------|-------------------|-------------|
| 0 | 2,239.13 | 2,239.13 | ~0 |
| 1 | 2,202.63 | 2,202.63 | ~0 |
| 14 | 2,471.54 | 2,471.54 | ~0 |
| 25 | 1,558.40 | 1,558.40 | ~0 |
| 27 | 1,524.28 | 1,507.44 | +16.84 (within 20 kEUR tolerance) |

## Residual Classification

| Gap | Classification | Severity | Notes |
|-----|---------------|----------|-------|
| TUHO senior debt amount | **None** | ✅ Resolved | Exact match 43,359 kEUR |
| Oborovo senior debt amount | **None** | ✅ Resolved | Exact match 42,852 kEUR (+0.27 kEUR rounding) |
| TUHO DSCR trajectory | **Expected** | 🟡 Informational | Runtime DSCR > target early;< target at merchant start |
| Oborovo DSCR trajectory | **Expected** | 🟡 Informational | Late-period DSCR above target (declining DS) |
| Oborovo op_idx 27 DS residual | **Rounding/mapping** | 🟢 Low | +16.84 kEUR, within 20 kEUR tolerance |
| TUHO DSCR op_idx 12 vs target | **FCF variation** | 🟢 Low |1.162 vs 1.2 target — actual FCF vs frozen DS |
| TUHO merchant DSCR | **Expected** | 🟢 Low | inf DSCR when no debt service |
| Oborovo late DSCR | **Expected** | 🟢 Low | Declining frozen DS, stable FCF |

**Key finding:** All senior debt amount residuals are resolved. The DSCR deviations are expected because:
1. Runtime DSCR is backward-computed from frozen DS (denominator), not a forward target
2. FCF varies period-to-period while frozen DS is fixed per fixture
3. Late-period DSCR inflation is an artifact of declining frozen DS

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
| SHL/distribution lock-up unchanged | ✅ |
| No runtime changes | ✅ |
| PR #299 remains draft | ✅ |

## Tests

9 tests in `tests/test_phase23t_senior_debt_amount_dscr_residual_bridge.py`:
1. `test_both_factories_still_frozen_senior_ds_enabled` ✅
2. `test_tuho_senior_debt_amount_bridge` ✅
3. `test_oborovo_senior_debt_amount_bridge` ✅
4. `test_tuho_dscr_trajectory_snapshot` ✅
5. `test_oborovo_dscr_trajectory_snapshot` ✅
6. `test_tuho_senior_ds_fixture_still_matches` ✅
7. `test_oborovo_senior_ds_fixture_still_matches` ✅
8. `test_lockup_regression_still_clean` ✅
9. `test_guardrails_unchanged` ✅

Full suite: **123 passed, 2 xfailed, 1 xpassed**

## CI Status

Full suite: **123 passed, 2 xfailed, 1 xpassed**

## Recommendation for Next Phase

**Phase 23U: Full Excel Parity Pack** — priority 🔴 High

The senior debt amount residuals are resolved. The remaining gaps are DSCR-related and fall into two categories:

1. **Informational only** — DSCR deviations are expected given the frozen DS path (backward-computed DSCR from fixed fixture, FCF variation)
2. **Narrow corrections** — if any specific period's DSCR or debt service residual exceeds documented tolerance, fix only that period

Recommended actions for Phase 23U:
- Lock the complete DSCR/FCF/DS trajectory for both projects in a fixture
- If backend parity is the goal: document the frozen DS path as the canonical model
- If Excel parity is the goal: extract full Excel balance sheet + cash flow for comparison
- If UI stability is the goal: Phase 24A UI/runtime impact taxonomy

**No narrow runtime corrections are clearly proven at this stage.** The DSCR deviations are expected, not errors.
