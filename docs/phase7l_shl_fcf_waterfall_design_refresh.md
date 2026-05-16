# Phase 7L SHL FCF Waterfall Design Refresh

## Purpose

Refresh the deferred B2 SHL `fcf_waterfall` design after the Phase 7K senior
debt work stabilized the senior-debt comparison basis.

This is design-only. No runtime behavior is changed.

## Current Stable Context

The codebase now has:

- senior opening debt policy resolved as principal-only,
- senior IDC and commitment fees excluded from operating senior debt,
- default-off senior rate/day-count schedule path,
- default-off explicit senior debt-service schedule path,
- full TUHO and Oborovo senior DS parity through test-only fixtures,
- construction diagnostics,
- OPEX runtime flag,
- no SHL `fcf_waterfall` runtime method.

This means SHL calibration can now be evaluated with a known senior-debt basis
instead of mixing senior debt timing gaps with SHL mechanics gaps.

## 1. Current Runtime SHL Behavior

### Supported Runtime Methods

`SHLRepaymentMethod` currently supports:

- `bullet`
- `cash_sweep`
- `pik`
- `accrued`
- `pik_then_sweep`

There is no `fcf_waterfall` enum value or runtime branch today.

### TUHO Current Method

TUHO factory currently uses:

```text
shl_repayment_method = "pik_then_sweep"
shl_amount_keur = 29,135.0
shl_idc_keur = 3,568.69
opening SHL balance = 32,703.69 kEUR
shl_rate = 7.93%
wht_sponsor_shl_interest = 0.0%
use_senior_sweep_cash_cap_for_shl = False
```

Runtime mechanics:

1. Opening SHL balance is `shl_amount + shl_idc`.
2. First operating period is treated as a disbursement period for
   `pik_then_sweep`, so no SHL interest/service is paid in that period.
3. Gross SHL interest is `opening_shl_balance * shl_rate * day_fraction`.
4. During PIK phase, cash interest is `min(available_cash, net_interest)`.
5. Unpaid gross interest is capitalized as PIK.
6. Principal is not repaid until the sweep phase.
7. The current `_pik_trigger` is based on whether available cash exceeds a
   full-year interest proxy.
8. Distributions are separately gated by senior debt, lockup, remaining SHL
   balance, and `cf_after_reserves`.

The current TUHO path is therefore not a true cash-interest-first waterfall
against Excel R99/R102.

### Oborovo Current Method

Oborovo does not explicitly set `shl_repayment_method` in the factory, so it
uses the `FinancingParams` default:

```text
shl_repayment_method = "bullet"
shl_amount_keur = 13,547.2
shl_idc_keur = 1,169.0
opening SHL balance = 14,716.2 kEUR
shl_rate = 8.00%
wht_sponsor_shl_interest = 0.0%
```

Oborovo runtime should remain unchanged until a separate Oborovo SHL parity
branch proves the Excel behavior and required opt-in.

## 2. Excel SHL Target Behavior

### TUHO Excel Targets

From `tests/fixtures/excel_tuho_full_model_extract.json`:

| Metric | Excel value |
|---|---:|
| SHL draw | 29,135.176 |
| Construction SHL IDC | 3,568.688 |
| Opening SHL at COD | 32,703.864 |
| Gross SHL interest total | 53,350.870 |
| Cash interest paid total | 38,755.348 |
| PIK / capitalized interest total | 14,595.523 |
| Principal repaid total | 43,730.699 |
| Total SHL cash service | 82,486.047 |
| SHL peak balance | 43,730.699 |
| First positive dividend | op_idx 36 / 2047-12-31 |
| Net dividends / R119 | 151,709.394 |

Authoritative mapping from Phase 7F:

```text
R99 = R102 = cash available / fcf_for_shl input
R104 = net SHL cash outflow
R119 = official net dividends target
```

Excel SHL behavior is cash-interest-first:

```text
cash_interest = min(R99/R102 available cash, gross_interest)
PIK = gross_interest - cash_interest
principal = min(remaining cash after interest, opening balance + PIK)
distribution = residual cash after interest and principal
```

The full B2 retry must use a validated R99/R102 source, not the rejected
`cf_after_tax - senior_ds` proxy as a final input.

### Oborovo Excel Targets

From `tests/fixtures/excel_oborovo_full_model_extract.json`:

| Metric | Excel value |
|---|---:|
| SHL draw | 14,620.774 |
| Construction SHL IDC | 1,169.662 |
| Opening SHL at COD | 15,790.436 |
| Gross SHL interest total | 32,104.911 |
| Cash interest paid total | 19,953.802 |
| PIK / capitalized interest total | 12,151.109 |
| Principal repaid total | 26,771.883 |
| Total SHL cash service | 46,725.685 |
| SHL peak balance | 26,771.883 |
| First positive dividend | op_idx 40 / 2050-06-30 |
| Net dividends | 58,192.098 |

Oborovo Excel also exhibits cash interest, PIK, and principal repayment, but the
current Python Oborovo runtime remains `bullet`. Oborovo must not be opted in by
the TUHO B2 implementation branch.

## 3. Link With Senior Debt

Phase 7K gives three senior bases:

| Basis | Use in SHL design |
|---|---|
| Legacy senior DS | Default runtime baseline. Must remain flag-off behavior. |
| Explicit senior DS fixture | Best senior-debt parity harness for B2 measurement. Use in tests/diagnostics to isolate SHL mechanics. |
| Formula senior DS | Not yet proven. Do not depend on this for B2 acceptance. |

Recommended approach:

1. Implement SHL `fcf_waterfall` default-off and TUHO-only.
2. Validate it first with the Phase 7K explicit senior DS fixture to isolate
   SHL mechanics from senior timing.
3. Also run a legacy-senior comparison so reviewers can see the runtime impact
   if TUHO is later opted in without the senior DS fixture.
4. Do not globally enable the senior DS fixture or senior sculpting engine in
   factories as part of B2.

The senior fixture is a parity harness, not a production opt-in decision.

## 4. Proposed FCF Waterfall Algorithm

### New Flag

Add a default-off project/input flag:

```text
use_shl_fcf_waterfall_engine: bool = False
```

The flag must default to `False` for all projects. TUHO opt-in must be explicit
and reviewed. Oborovo remains off.

### New SHL Method

Add:

```text
SHLRepaymentMethod.FCF_WATERFALL = "fcf_waterfall"
```

Runtime should reject `fcf_waterfall` unless `use_shl_fcf_waterfall_engine=True`
to avoid accidental activation through legacy inputs.

### Period Algorithm

Inputs per period:

- opening SHL balance,
- annual SHL rate,
- period day fraction,
- R99/R102-equivalent available cash for SHL,
- WHT rate, if applicable,
- senior debt service for the period,
- reserve movements needed to produce the R99/R102 cash basis.

Algorithm:

```text
opening = max(0, opening_shl_balance)
available = max(0, fcf_for_shl)
gross_interest = opening * shl_rate * day_fraction

cash_interest_paid = min(available, gross_interest)
interest_wht = WHT on cash interest only, if applicable
pik = max(0, gross_interest - cash_interest_paid)

remaining_after_interest = available - cash_interest_paid
balance_after_pik = opening + pik

principal_paid = min(remaining_after_interest, balance_after_pik)
closing_balance = max(0, balance_after_pik - principal_paid)

distribution = max(0, remaining_after_interest - principal_paid)
shl_service = cash_interest_paid + principal_paid
```

Safety invariants:

- `closing_balance >= 0`
- `principal_paid <= opening + pik`
- `cash_interest_paid <= gross_interest`
- `pik == gross_interest - cash_interest_paid`
- `distribution == 0` while cash is still needed for interest/principal
- no WHT is capitalized into PIK

### Available Cash Source

Do not use the rejected final proxy:

```text
cf_after_tax - senior_ds
```

That proxy failed Phase 7F acceptance:

- total distributions too high,
- SHL service too low,
- SHL peak too low,
- first distribution too early.

Minimum acceptable B2 implementation:

- use a clearly named diagnostic/test input source for `fcf_for_shl`, or
- use C1d audit `r102_fcf_for_shl_keur` only if the implementation explicitly
  remains diagnostic/blocked when the R99/R102 gates fail, or
- use fixture-backed Excel R99/R102 in tests only to prove SHL mechanics before
  runtime opt-in.

Recommended design sequence:

1. Unit-test the `fcf_waterfall` period algorithm with explicit cash schedules.
2. Fixture-test TUHO SHL mechanics using Excel R99/R102 and Phase 7K explicit
   senior DS.
3. Separately test Python R99/R102 source candidates.
4. Only then permit TUHO runtime opt-in.

## 5. Acceptance Criteria

### TUHO Calibration Targets

| Metric | Excel target | Acceptance band |
|---|---:|---:|
| Net distributions / R119 | 151,709.4 | 144,124 to 159,294 (±5%) |
| SHL total cash service | 82,486.0 | 78,000 to 87,000 |
| SHL peak balance | 43,730.7 | 41,000 to 47,000 |
| First positive distribution | op_idx 36 / 2047-12-31 | op_idx 35 to 37 |
| No negative SHL balance | 0 min | required |
| Principal overpayment | none | required |

Recommended period-level checks:

- op_idx 28, 32, 36 SHL closing balance within ±5% while the balance is
  material,
- op_idx 34-36 first-distribution transition documented,
- R104 sign-adjusted SHL cash outflow within ±500 kEUR for selected periods
  once R99/R102 source is accepted,
- R119 net dividends total within band.

### Revert Triggers

Revert or block runtime opt-in if:

- distributions are outside 144,124 to 159,294 kEUR,
- SHL service is outside 78,000 to 87,000 kEUR,
- SHL peak is outside 41,000 to 47,000 kEUR,
- first positive distribution is earlier than op_idx 35 or later than op_idx 37,
- any SHL balance goes negative,
- principal paid exceeds opening plus PIK,
- Oborovo changes when the flag is false,
- revenue/OPEX/tax/senior/construction/R99/sponsor outputs move unexpectedly.

## 6. Runtime Safety

Future B2 implementation must be explicitly gated:

```text
use_shl_fcf_waterfall_engine: bool = False
```

Default false means:

- existing `pik_then_sweep`, `bullet`, `cash_sweep`, `pik`, and `accrued`
  behavior is unchanged,
- TUHO factory does not opt in until approved,
- Oborovo factory does not opt in,
- no senior debt, revenue, OPEX, tax, construction, R99, sponsor, UI, or cache
  logic changes.

Unsupported or accidental use should fail clearly:

- if method is `fcf_waterfall` but flag is false, raise `ValueError`,
- if flag is true for unsupported project/source configuration, raise
  `ValueError`,
- if no accepted `fcf_for_shl` source is available, raise `ValueError` rather
  than silently using `cf_after_tax - senior_ds`.

## 7. Recommended B2 Implementation Scope

Branch:

```text
phase7l-shl-fcf-waterfall-runtime-flag
```

Allowed scope:

- add `SHLRepaymentMethod.FCF_WATERFALL`,
- add `ProjectInfo.use_shl_fcf_waterfall_engine: bool = False`,
- add isolated SHL FCF waterfall period helper,
- wire helper behind flag only,
- add TUHO test-only fixtures for Excel R99/R102 and SHL schedule,
- add tests using Phase 7K explicit senior DS fixture to isolate SHL mechanics,
- add flag-off equivalence tests for TUHO and Oborovo,
- add unsupported/unsafe source guard tests.

Non-goals:

- no global TUHO opt-in,
- no Oborovo opt-in,
- no formula-based senior sculpting changes,
- no revenue/OPEX/tax/construction capitalization/R99/sponsor/UI/cache changes,
- no project factory changes except test-only cloned inputs.

## 8. Blockers

The main blocker remains the runtime-safe `fcf_for_shl` source:

- Excel target is R99/R102.
- `cf_after_tax - senior_ds` is rejected as a final source.
- C1d R99 audit fields remain diagnostic and outside Excel by material amount.

B2 can still proceed as a mechanics branch if it uses fixture/test-provided
R99/R102 cash schedules and keeps runtime opt-in blocked for live projects until
the R99 source is accepted.

## Merge Recommendation

Merge this design refresh as docs-only. It provides the implementation
boundary for the next B2 runtime-flag branch without changing model behavior.
