# Phase 7K Senior DSCR Sculpting Runtime Flag

## Purpose

This branch adds a runtime-safe, default-off senior sculpting basis engine with
only one supported non-legacy mode:

```text
EXPLICIT_DEBT_SERVICE_SCHEDULE
```

It is a parity harness, not a formula-based Excel sculpting implementation.

## Flag Behavior

`ProjectInfo.use_senior_sculpting_basis_engine` defaults to `False`.

When false, the existing senior debt schedule path is unchanged.

When true, `FinancingParams.senior_sculpting_config` must be enabled. The only
implemented runtime mode is `EXPLICIT_DEBT_SERVICE_SCHEDULE`.

Unsupported modes raise a clear `ValueError`:

- `EXPLICIT_PRINCIPAL_SCHEDULE`
- `EXCEL_AVAILABLE_CFADS`

## Explicit Debt-Service Schedule Semantics

For each senior tenor period:

```text
interest[t] = opening_balance[t] * period_rate[t]
principal[t] = min(opening_balance[t], max(0, explicit_ds[t] - interest[t]))
senior_ds[t] = interest[t] + principal[t]
closing_balance[t] = opening_balance[t] - principal[t]
```

The schedule never makes senior debt negative. Senior opening debt remains
principal-only.

## Opening Balance Policy

Unchanged:

- senior IDC is not capitalized into operating senior debt,
- commitment fees are not capitalized into operating senior debt,
- construction capitalization is not changed.

## TUHO Test-Only Result

The tests clone TUHO inputs and opt in both:

- senior rate/day-count fixture,
- senior explicit debt-service schedule fixture.

Mapped periods use Excel debt service values for the first four periods and the
final repayment period. First period:

| Metric | Result |
|---|---:|
| Opening senior debt | 43,359.0 kEUR |
| Interest | about 1,297.1 kEUR |
| Explicit senior DS | 2,116.361 kEUR |
| Principal | senior DS minus interest, about 819.3 kEUR |

## Oborovo Test-Only Result

The same test-only pattern is used for Oborovo. First period:

| Metric | Result |
|---|---:|
| Opening senior debt | 42,852.267 kEUR |
| Interest | about 1,303.5 kEUR |
| Explicit senior DS | 2,239.133 kEUR |
| Principal | senior DS minus interest, about 935.7 kEUR |

## Known Limitations

- No project factory is globally opted in.
- Only mapped periods are asserted where Excel evidence exists.
- Formula-based Excel sculpting is not implemented.
- SHL `fcf_waterfall` is not implemented.
- Revenue, OPEX, tax, construction capitalization, R99, sponsor waterfall, UI,
  and cache logic are not changed.
- Downstream SHL/distribution effects from changed senior DS are intentionally
  not calibrated in this branch.

## Next Recommendation

Next branch:

```text
phase7k-senior-dscr-sculpting-full-schedule-fixtures
```

Goal:

- extract full TUHO and Oborovo senior debt-service schedules,
- use explicit schedule mode for full-tenor parity,
- measure downstream cash effects,
- still avoid formula-based sculpting and SHL `fcf_waterfall`.
