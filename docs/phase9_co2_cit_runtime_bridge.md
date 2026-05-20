# Phase 9 — CO2→CIT Runtime Bridge

## 1. Executive Summary

`use_co2_cit_bridge=True` wires TUHO CO2 certificate revenue directly into **taxable income** in the TaxEngine — without touching EBITDA, distributions, or R99/R102.

The flag is **default-OFF** (`False`). When `False`, behavior is **identical to legacy baseline**. When `True`, CO2 revenue is added to `taxable_before_losses` in `compute_period_tax()`, producing auditable CIT cash tax impact.

## 2. Current CO2→Tax Gap

PR #141 wired CO2 into `period.revenue_keur` and EBITDA via `use_co2_revenue_bridge`. However, `compute_period_tax()` receives `ebitda` directly from `waterfall_engine` and does **not** include CO2. The CIT chain is therefore CO2-blind.

This bridge closes that gap: when `use_co2_cit_bridge=True`, CO2 revenue is added to taxable income before ATAD and loss carryforward.

## 3. Taxable Income Bridge Design

### Narrowest possible injection

CO2 revenue is added to `taxable_before_losses` inside `compute_period_tax()`, alongside `fiscal_reintegration_keur`:

```
taxable_before_losses = (
    ebitda_keur
  + co2_revenue_keur          # ← Phase 9 CO2→CIT bridge (new)
  - depreciation_keur
  - deductible_interest
  + disallowed_interest
  + fiscal_reintegration_keur
)
```

### Parameter threading

```
waterfall_core.py: run_waterfall_v3_core()
    └── use_co2_cit_bridge: bool = False
        └── extracts co2_cit_bridge_by_period from revenue_decomposition_schedule()
            └── run_waterfall(co2_cit_bridge_by_period=...)
                └── waterfall_engine.py: run_waterfall()
                    └── compute_period_tax(co2_revenue_keur=...)
                        └── taxable_before_losses += co2_revenue_keur
```

### Flag default: False

```python
use_co2_cit_bridge: bool = False  # waterfall_core.py:62
```

### TUHO-only guard

```python
if use_co2_cit_bridge:
    if getattr(inputs.info, "code", "") != "TUHO-WIND-1":
        raise ValueError("CO2 CIT bridge supported only for TUHO-WIND-1")
```

## 4. Runtime Ownership Boundaries

| Component | With `use_co2_cit_bridge=True` |
|---|---|
| `period.revenue_keur` | **Unchanged** |
| `ebitda_schedule` | **Unchanged** (CO2 NOT added to revenue chain) |
| `compute_period_tax()` taxable income | CO2 added |
| `cash_tax` | Reflects CO2 contribution |
| `cf_after_tax` | Affected by tax delta |
| Distributions | **Unchanged** |
| R99/R102 | **BLOCKED** |
| DistributionAccount | **Unchanged** |
| Sponsor | **Unchanged** |
| SHL | **Unchanged** |
| SeniorDebt | **Unchanged** |

## 5. Depreciation Interaction

Depreciation is **unchanged**. The CO2 bridge adds to `taxable_before_losses` after depreciation is deducted. This means CO2 revenue contributes to taxable income before the depreciation deduction — which is the correct economic treatment (CO2 revenue is a revenue-item, not a depreciation item).

## 6. Tax Loss Interaction

CO2 is added to `taxable_before_losses` before loss carryforward is applied. This means:
- If TUHO has accumulated tax losses, CO2 revenue may first reduce those losses before generating CIT
- The `loss_carryforward_applied_keur` and `loss_carryforward_remaining_keur` in `TaxPeriodResult` will reflect this
- No change to loss carryforward mechanics

## 7. actual_cfads vs sizing_cfads Implications

`sizing_cfads` is used for debt sculpting and is derived from the EBITDA schedule (pre-tax). The CO2→CIT bridge does **not** modify `ebitda_schedule`, so `sizing_cfads` is unchanged.

`actual_cfads` includes cash tax. Since `compute_period_tax()` now adds CO2 to taxable income (when flag=True), `actual_cfads` will differ from `sizing_cfads` in CIT-heavy periods. This is the expected and correct behavior.

## 8. DistributionAccount Non-Participation

DistributionAccount ownership is **unchanged**. The CO2→CIT bridge does not write to `distribution_account` fields. Distributions continue to use the existing logic with no ownership changes.

## 9. R99/R102 Blocked Confirmation

R99 and R102 are **BLOCKED** for this bridge:
- R99 (sizing CFADS) uses `ebitda_schedule` which is **not modified** by `use_co2_cit_bridge`
- R102 (distribution waterfall) uses `cf_after_tax` which changes due to CIT delta, but the **distribution mechanics** (who gets paid, how much) are unchanged
- No changes to `DistributionAccount`, `Sponsor`, `SHL`, or `SeniorDebt`

## 10. Validation Results

See `reports/phase9_co2_cit_bridge_validation.csv`.

Key assertions:
- `use_co2_cit_bridge=False` → exact legacy baseline (TUHO equity IRR ≈ 11.61%)
- `use_co2_cit_bridge=True` → CO2 in taxable income, Oborovo raises `ValueError`
- No `use_co2_revenue_bridge=True` + `use_co2_cit_bridge=True` conflict (mutual exclusivity enforced)
- R99/R102, DistributionAccount, Sponsor, SHL, SeniorDebt unchanged

## 11. Known Limitations

- **CIT delta without EBITDA delta**: When `use_co2_cit_bridge=True`, cash tax changes but `ebitda_schedule` is unchanged. This means CFADS/cash available for distribution may not reflect the full CO2 benefit at the CFADS level (only at the tax level). This is by design for Phase 9.
- **TUHO-only**: Oborovo is protected but not calibrated with CO2
- **No CO2 for sizing**: The `sizing_cfads` path (debt sculpting) does not include CO2 in this branch

## 12. Recommended Next Step

`phase9-distributionaccount-runtime-design` — before any R99 runtime promotion.

## Change Table

| File | Change |
|---|---|
| `domain/waterfall/tax_engine.py` | +`co2_revenue_keur` param, +`co2_cit_bridge_keur` field in `TaxPeriodResult`, wired into `taxable_before_losses` |
| `domain/waterfall/waterfall_engine.py` | +`co2_cit_bridge_by_period` param, extracts per-period, passes to `compute_period_tax()` |
| `app/waterfall_core.py` | +`use_co2_cit_bridge` flag, TUHO guard, mutual exclusivity, extraction, audit metadata |
