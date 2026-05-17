# Phase 7L SHL FCF Waterfall Runtime Flag

## Scope

This branch adds a runtime-safe, default-off SHL FCF waterfall path for fixture-backed TUHO calibration only.

It does not globally enable the new method, does not change project factories, and does not opt Oborovo in. Revenue, OPEX, tax, construction capitalization, senior opening debt policy, R99/distribution-account logic, sponsor waterfall, cache, and UI behavior are unchanged.

## Runtime Flag Behavior

`ProjectInfo.use_shl_fcf_waterfall_engine` defaults to `False`.

`SHLRepaymentMethod.FCF_WATERFALL` is rejected unless the flag is enabled. When enabled, the runtime also requires a supported project and an explicit fixture/source cash schedule. The current supported runtime project is `TUHO-WIND-1`; Oborovo and unsupported projects raise a clear `ValueError`.

When the flag is off, existing SHL behavior remains unchanged.

## Helper Mechanics

The pure helper in `domain/shl_fcf_waterfall.py` computes each period as:

```text
gross_interest = opening * shl_rate * day_fraction
available_cash_after_buffer = max(0, fcf_for_shl - minimum_cash_retained_keur)
cash_interest_paid = min(available_cash_after_buffer, gross_interest)
pik = gross_interest - cash_interest_paid
balance_after_pik = opening + pik
remaining_after_interest = available_cash_after_buffer - cash_interest_paid
principal_paid = min(remaining_after_interest, balance_after_pik)
closing_balance = max(0, balance_after_pik - principal_paid)
distribution = max(0, remaining_after_interest - principal_paid)
shl_service = cash_interest_paid + principal_paid
```

Safety invariants are enforced by construction of the formula: no negative closing balance, no principal paid above balance after PIK, no cash interest paid above gross interest, no negative distribution, and no negative retained cash.

The runtime wiring uses the current semiannual SHL convention (`day_fraction = 0.5`) for this path. The helper itself remains explicit and accepts a period day fraction for direct tests and future fixture sources.

## Fixture-Backed Harness

The TUHO tests use:

- Excel-backed R99/R102-equivalent cash schedule from `tests/fixtures/excel_tuho_full_model_extract.json`.
- Phase 7K explicit senior DS fixture harness.
- Test-only TUHO SHL opening principal, IDC, and first-period SHL rate derived from the Excel fixture.

The live runtime R99 source is not used for SHL calibration in this branch. This is deliberate: prior diagnostics rejected `cf_after_tax - senior_ds` as an invalid runtime SHL cash source.

## TUHO Calibration Results

With `minimum_cash_retained_keur = 0.0`:

| Metric | Result |
| --- | ---: |
| SHL cash interest | 38,309.1 kEUR |
| SHL PIK | 10,525.2 kEUR |
| SHL principal | 43,229.0 kEUR |
| Total SHL service | 81,538.2 kEUR |
| SHL peak balance | 43,229.0 kEUR |
| First distribution | op_idx 35 / 2047-12-31 |
| Total distributions | 153,207.3 kEUR |

This is within the refreshed TUHO distribution acceptance band of 144,124 to 159,294 kEUR and keeps the first distribution timing around op_idx 35-37.

## Minimum Retained Cash Buffer

The retained cash buffer is a simple cash floor before SHL/distribution. It is not DSRA, working capital, or a reserve-account rewrite.

| Minimum retained cash | Total distributions | SHL service | SHL peak | First distribution |
| ---: | ---: | ---: | ---: | --- |
| 0 kEUR | 153,207.3 kEUR | 81,538.2 kEUR | 43,229.0 kEUR | op_idx 35 / 2047-12-31 |
| 50 kEUR | 148,055.2 kEUR | 83,690.3 kEUR | 45,174.9 kEUR | op_idx 36 / 2048-06-30 |
| 100 kEUR | 142,848.8 kEUR | 85,896.7 kEUR | 47,120.8 kEUR | op_idx 36 / 2048-06-30 |

The 100 kEUR buffer reduces distributions below the current acceptance band while still demonstrating the buffer mechanics.

## Unsupported Cases

The runtime raises explicit errors for:

- `fcf_waterfall` repayment method while `use_shl_fcf_waterfall_engine=False`.
- Oborovo or any unsupported project with the flag enabled.
- Missing SHL FCF cash schedule.
- Enabling the flag without selecting `fcf_waterfall`.

There is no fallback from a missing fixture/source schedule to `cf_after_tax - senior_ds`; the path fails closed until a validated R99/R102 runtime source exists.

## Remaining Blocker

The remaining blocker is still the runtime-safe R99/R102 source. This branch validates the SHL mechanics independently with an Excel-backed fixture schedule. It does not prove that the current runtime can generate the correct R99/R102 cash basis.

`cf_after_tax - senior_ds` remains rejected because prior Phase 7F diagnostics showed that it does not reproduce Excel R99/R102 period-by-period and mixes tax, reserve, and distribution-account timing differences.

## Recommended Next Branch

Recommended next branch:

`phase7l-r99-runtime-source-validation`

Suggested scope:

- Build a default-off runtime R99/R102 source harness.
- Compare fixture-backed R99/R102 against C1d audit fields and any available distribution-account diagnostics.
- Keep SHL FCF waterfall disabled by default.
- Do not opt TUHO into production behavior until R99/R102 gates pass.
