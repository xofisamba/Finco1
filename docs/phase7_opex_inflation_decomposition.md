# Phase 7 — OPEX Inflation Decomposition

## Purpose

Explain **why TUHO OPEX changes over time** for each line item. This is audit/explainability work — not calibration. OPEX totals are unchanged.

## Scope

- TUHO-WIND-1 only (51 line items × 30 years = 1,530 annual rows)
- Oborovo: future note only (no template exists yet)
- R99/R102: BLOCKED

## What Changed

No production/runtime behavior changes. Added reporting-only decomposition.

## Driver Taxonomy

| Driver | Description | Example Items |
|--------|-------------|---------------|
| `INFLATION` | Annual price escalation at documented rate | B.01.x (2% pa), B.04.x |
| `EXPLICIT_SCHEDULE` | Item-driven step changes from defined schedule | B.02.1 (O&M, steps at Y3/Y11/Y16/Y21/Y26) |
| `ACTIVE_FLAG` | Items that turn off after defined operating year | B.11.1 (Agency Fee, inactive Y15+) |
| `CONTINGENCY_PCT` | % of selected other groups | B.13.1 (6% of B.01–B.12, excl. B.13) |
| `ZERO_LINE` | Inactive or zero-amount item | B.09.x (telecom, inactive Y1+), B.11.1 Y15+ |
| `FIXED` | No inflation, no steps, no flags | (none in TUHO template) |
| `MANUAL_OVERRIDE` | One-off override value | (none in current TUHO template) |
| `MIXED` | Multiple drivers (should not occur in TUHO) | (none — clean taxonomy) |

## Key Examples

### B.01 Technical Management — INFLATION
- **Y1 base:** 138.0 kEUR
- **Rate:** 2% per annum (group-level)
- **Y30 amount:** 182.09 kEUR
- **Movement:** pure inflation escalation, no step changes

### B.02.1 O&M Preventive/Corrective — EXPLICIT_SCHEDULE
- **Y1 base:** 385.6 kEUR (from schedule array)
- **Schedule steps:** 385.6 → 465.6 (Y3) → 588.0 (Y6) → 628.0 (Y11) → 676.0 (Y16) → 756.0 (Y21) → 828.0 (Y26)
- **Rate:** 0% (inflation not applied to explicit_schedule basis)
- **Movement:** explicit schedule steps only

### B.11.1 Agency Fee — ACTIVE_FLAG
- **Y1–Y14:** 20.0 kEUR (active, INFLATION at 2%)
- **Y15+:** 0.0 kEUR (inactive, ZERO_LINE)
- **Movement:** active flag deactivation at Y15

### B.13.1 Contingencies — CONTINGENCY_PCT
- **Rate:** 6% of selected groups (B.01–B.12, excl. B.13)
- **Y1 base:** 113.10 kEUR (= 6% × sum of B.01–B.12 Y1)
- **Y30:** 154.80 kEUR (6% × inflated selected groups)
- **Movement:** contingency % applied to inflated group totals

## Validation

| Check | Result |
|-------|--------|
| Decomposition rows | 1,530 (51 items × 30 years) |
| Horizon total | 84,674.78 kEUR (exact match `compute_annual_opex`) |
| Max annual delta | 0.00000000 kEUR |
| Max reconciliation delta | 0.00000000 kEUR |
| Driver distribution | INFLATION: 1140, ZERO_LINE: 316, EXPLICIT_SCHEDULE: 30, ACTIVE_FLAG: 14, CONTINGENCY_PCT: 30 |
| MIXED items | 0 (clean taxonomy) |

## Reconciliation Logic

Each row's components sum to `resulting_amount_keur` within floating-point tolerance:

```
base_component
+ inflation_component
+ volume_component
+ step_change_component
+ active_flag_component
+ contingency_component
+ manual_override_component
= resulting_amount_keur  (±0.00 kEUR)
```

## Output File

- `reports/phase7_opex_inflation_decomposition.csv` — 26 columns, 1,530 rows

## Known Limitations

1. **B.02.1 step changes classified as step_change_component** — the step value IS the amount (no base). The step_change is the difference from Y1 base value.
2. **Contingency base not tracked per-item** — the `% of selected groups` base is the sum of those groups, not tracked as a single "contingency_base_keur" per row.
3. **Oborovo not supported** — future work.
4. **R99/R102 remain BLOCKED** — no SHL FCF runtime source.

## No Production Changes

- No waterfall changes
- No runtime flag changes
- No tax/debt/SHL changes
- No factory opt-in changes
- Default behavior unchanged

## Recommended Next Branch

`phase7-model-stack-blueprint` — consolidate Phase 6/7 OPEX + tax architecture into a single readable model-stack documentation for onboarding.