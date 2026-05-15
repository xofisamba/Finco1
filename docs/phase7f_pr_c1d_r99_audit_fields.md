# Phase 7F PR C1d - TUHO R99 Audit Fields

Status: implementation draft, not committed.

Purpose: expose period-by-period audit fields for TUHO R69/R84/R98/R99/R102 and current Python cash-tax timing without changing runtime cash routing.

## Runtime Behavior

C1d is audit-only. The new fields are populated after the existing waterfall calculations and do not feed:

- revenue
- tax formulas
- senior debt service
- SHL service
- DSRA cash routing
- distributions
- `use_tuho_r99_input_engine`

`use_tuho_r99_input_engine` remains disabled and SHL `fcf_waterfall` remains absent.

## Corporate Cash Tax Basis

`corporate_tax_cash_keur` is a true current-model period cash-tax field, not the older opaque `ebitda - cf_after_tax` proxy.

Formula:

```text
corporate_tax_cash_keur = tax_keur if period_in_year == 2 else 0.0
```

Sign convention: positive value means cash tax paid in the period.

Important limitation: this is true within the current Python tax timing convention. It does not claim parity with Excel CF R67 timing.

## Audit Field Formulas

```text
r69_fcf_banks_keur =
    revenue_keur
    - opex_keur
    + local_tax_keur
    + cash_interest_on_reserves_keur
    - corporate_tax_cash_keur
```

For C1d, `local_tax_keur = 0.0` and `cash_interest_on_reserves_keur = 0.0` because they are not currently exposed as runtime fields.

```text
dsra_release_or_funding_keur = dsra_withdrawal_keur - dsra_contribution_keur
r84_fcf_junior_keur = r69_fcf_banks_keur - senior_ds_keur + dsra_release_or_funding_keur
r98_distribution_account_keur =
    r84_fcf_junior_keur
    + junior_ds_keur
    + reserve_sweep_keur
    + previous_r100_carryforward_keur
```

For C1d, `junior_ds_keur = 0.0` and `reserve_sweep_keur = 0.0`.

```text
if diagnostic lockup is active:
    r99_fcf_for_distribution_keur = 0.0
    r100_carryforward_keur = r98_distribution_account_keur
else:
    r99_fcf_for_distribution_keur = r98_distribution_account_keur
    r100_carryforward_keur = 0.0

r102_fcf_for_shl_keur = r99_fcf_for_distribution_keur
fcf_for_shl_keur = max(0.0, r102_fcf_for_shl_keur)
```

## Diagnostic Result

Current C1d R99 audit remains outside Excel acceptance and runtime opt-in remains blocked:

- Python audit R99/R102 total: 249,600.0 kEUR
- Excel R99/R102 target: 234,745.0 kEUR
- Delta: +14,855.0 kEUR

The accepted conclusion from C1c still holds: the current Python cash-tax/R99 source remains insufficient for B2 SHL `fcf_waterfall`.
