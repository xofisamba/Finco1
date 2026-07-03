# Phase 0 — Pre-Extraction Hotfix

**Branch**: `phase0-pre-extraction-hotfix`  
**Base**: `main` @ `5a82b99` (Post-AC Architecture Stabilization Baseline)  
**Purpose**: Minimum hotfixes required to stabilise the current application before v2 engine extraction. Three issues resolved.

---

## Summary

| ID | Name | Files Changed | KPI Impact |
|----|------|--------------|------------|
| Y3 | Remove runtime identity dependencies | `app/waterfall_core.py`, `app/waterfall_runner.py` | None |
| Z1 | Fix tax bridge formula to Croatian CIT basis | `app/waterfall_core.py` | TUHO total_tax 45,835 → 35,414 kEUR |
| Z2 | Bridge cash tax is reconciliation-only (Option B) | `app/waterfall_core.py`, `domain/waterfall/waterfall_engine.py` | None |

---

## HOTFIX Y3 — Remove Runtime Identity Dependencies

### Problem

After Stack AC, frozen DS fixture loading was moved to config (`frozen_senior_ds_fixture_path`). However, four identity guards remained in `app/waterfall_core.py` and one duplicate remained in `app/waterfall_runner.py`:

**`app/waterfall_core.py` (removed):**
- Line 115–116: `use_tax_bridge_engine` → raise if `code != "TUHO-WIND-1"`
- Line 117–118: `use_shl_gross_accrued_for_pnl` → raise if `code != "TUHO-WIND-1"`
- Line 119–120: `use_tuho_shl_repayment_alignment` → raise if `code != "TUHO-WIND-1"`
- Lines 140–143: `use_co2_revenue_bridge` → raise if `code != "TUHO-WIND-1"`
- Lines 159–163: `use_co2_cit_bridge` → raise if `code != "TUHO-WIND-1"`

**`app/waterfall_runner.py` (removed):**
- Lines 362–366: `use_tuho_shl_repayment_alignment` → raise if `code != "TUHO-WIND-1"` (duplicate; Stack AB oversight)

### Fix

Identity guards removed. Capability flags in `ProjectInfo` and `FinancingParams` are the sole dispatch mechanism per the Configuration Over Identity principle established in Stack AC.

Factories remain responsible for setting the correct flags. Oborovo factory sets `use_tax_bridge_engine=False`, `use_shl_gross_accrued_for_pnl=False` — these are factory decisions, not runtime guards.

### Consequence

A TUHO clone (same `FinancingParams`, different `code`) now runs without error. The identity guard tests from Stacks AB and Z that asserted `ValueError` were converted to tests asserting the factory sets the correct flag.

---

## HOTFIX Z1 — Tax Bridge Formula Correction

### Problem

`_tax_bridge_taxable_income_before_losses()` in `app/waterfall_core.py` computed taxable income using an incorrect formula:

**Old (incorrect):**
```
taxable = EBITDA − book_dep − deductible_interest + disallowed_interest + tax_dep + fiscal_reintegration
```

This formula double-counts the depreciation by: (1) starting from EBIT (EBITDA − book_dep) and (2) adding tax_dep as a positive adjustment rather than replacing book_dep with tax_dep. The result over-states taxable income by `2 × tax_dep − book_dep` per period relative to the correct Croatian CIT formula.

**For TUHO (disallowed_interest = 0 since total_interest ≈ 2,533 kEUR < 3,000 kEUR floor):**
- Per-period over-statement = 2 × 1,178.19 − 1,216.56 = +1,139.82 kEUR
- Lifetime impact: +10,422 kEUR excess tax accrual

### Fix

**New (correct — Croatian CIT §16 basis):**
```
taxable = EBITDA − tax_dep − deductible_interest + fiscal_reintegration
```

This is the standard derivation: Revenue − OPEX − tax_depreciation − deductible_interest + fiscal_reintegrations. The `book_depreciation_keur` parameter is accepted (for future reference) but unused in the formula.

### KPI Impact

| KPI | Before | After | Change |
|-----|--------|-------|--------|
| TUHO equity_irr | 11.32% | 11.32% | None (bridge is post-waterfall) |
| TUHO actual_avg_dscr | 1.3786 | 1.3786 | None |
| TUHO total_distributions | 165,471 kEUR | 165,471 kEUR | None |
| TUHO total_tax (accrued) | 45,835 kEUR | 35,414 kEUR | −10,421 kEUR |
| TUHO cash CIT (R67) | 43,512 kEUR | 35,404 kEUR | −8,108 kEUR |
| Oborovo total_tax | 8,874 kEUR | 8,874 kEUR | None (bridge disabled) |

The tax change does not propagate to distributions or IRR because the bridge is a post-waterfall mutator; equity_irr and distribution_keur are computed pre-bridge.

### Parity Targets Updated

All test files asserting `total_tax_keur ≈ 45,835` updated to `≈ 35,414` with ±500 kEUR tolerance.

### Loss Carryforward

The LCF methodology (5-year rolling, Croatian §16, `expire_before_use=True`) is **unchanged**. This hotfix corrects the taxable income formula, not the LCF treatment.

---

## HOTFIX Z2 — Bridge Cash Tax as Reconciliation-Only (Option B)

### Problem

`_apply_tuho_tax_bridge_runtime_cash_tax()` overrode `period.cf_after_tax_keur` with:
```python
period.cf_after_tax_keur = period.ebitda_keur - tax_cash
```

This created an internal inconsistency: `cf_after_tax_keur` was modified post-bridge, but `distribution_keur` and `equity_irr` were computed pre-bridge from the waterfall and were not recomputed. The bridge value was visible in some outputs but not others.

### Fix (Option B — Reconciliation-Only)

The `cf_after_tax_keur` override was removed. The bridge-adjusted cashflow is now available as:
```python
period.cash_tax_bridge_reconciliation_keur = period.ebitda_keur - tax_cash
```

This field is audit/export only. It does not feed into distributions, SHL repayment, or IRR computation.

`cf_after_tax_keur` retains its waterfall-computed value throughout.

### New Field

`WaterfallPeriod.cash_tax_bridge_reconciliation_keur: float = 0.0` added to `domain/waterfall/waterfall_engine.py`.

---

## Tests

New test file: `tests/test_phase0_pre_extraction_hotfix.py` (17 tests)

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestY3IdentityGuardsRemoved` | 6 | Clone runs, no guards in source, factory flags correct |
| `TestZ1TaxFormula` | 8 | Formula correctness, known inputs, book_dep invariance, KPI checks |
| `TestZ2BridgeReconciliationOnly` | 3 | cf_after_tax not overridden, reconciliation field populated |

Existing tests updated: `test_stack_ab_engine_architecture_cleanup.py`, `test_stack_ac_runtime_identity_phase1.py`, `test_stack_z_tax_depreciation_runtime.py`, `test_excel_parity_stack_t.py`, `test_excel_parity_stack_p.py`, `test_tax_bridge_runtime_flag.py`, `test_phase51f_parallel_work_guardrails.py`.

---

## Engineering Decisions

**Identity guards removed (Y3):** Flags in `ProjectInfo` / `FinancingParams` are the sole dispatch mechanism. If a feature requires project-specific constants, those constants belong in the config (as `FinancingParams` fields), not in runtime guards.

**Formula corrected (Z1):** The old formula was calibrated to the Golden Excel model, which coincidentally produced similar outputs because TUHO's interest is below the ATAD floor (disallowed_interest = 0). The formula correction changes the absolute tax amount but does not affect distributions or IRR. The correct mathematical treatment takes precedence.

**Bridge is reconciliation-only (Z2):** Overriding `cf_after_tax_keur` mid-waterfall without recomputing downstream values creates silent inconsistencies. Option B (audit field only) is the minimum-change approach that eliminates the inconsistency without restructuring the waterfall pipeline.

---

## Guardrail SHA Update

`tests/test_phase51f_parallel_work_guardrails.py` — `app/waterfall_core.py` pin updated:

| Event | SHA |
|-------|-----|
| Stack AC | `effae3ea5e8cf3fe9cd36fe9b959211ebf137fd7ff94d3d380730c9b21ef895d` |
| Phase 0 | `b839df14a697be51102015bae0b45c589dec0d9f89515b240ed683cfa1373079` |

---

*Phase 0 complete. Do not begin v2 extraction until this PR is reviewed and merged.*
