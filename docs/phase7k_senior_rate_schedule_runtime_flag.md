# Phase 7K Senior Rate Schedule Runtime Flag

## Purpose

This change adds a default-off path for building senior debt period interest
rates from explicit rate and day-count schedules. It uses the existing
`rate_schedule` input already consumed by the waterfall engine, so it does not
rewrite senior debt sculpting or repayment mechanics.

## Flag Behavior

`ProjectInfo.use_senior_rate_schedule_engine` defaults to `False`.

When the flag is `False`, senior interest uses the existing legacy behavior:

```text
period_rate = financing.all_in_rate / 2
```

When the flag is `True`, `FinancingParams.senior_debt_interest_config` must be
enabled. The runner builds:

```text
period_rate[t] = annual_all_in_rate[t] * period_fraction[t]
```

and passes that schedule into the existing waterfall `rate_schedule` path.

## Configuration Model

The model is defined in `domain/senior_rate_schedule.py`:

- `SeniorRateMode`
- `SeniorDayCountConvention`
- `SeniorHedgeConfig`
- `SeniorRateSchedule`
- `SeniorDebtInterestConfig`

Supported annual-rate modes:

- flat all-in rate
- fixed base plus margin
- floating base plus margin
- hedge blend
- explicit all-in schedule

Supported day-count conventions:

- fixed semiannual 0.5
- ACT/360
- ACT/365
- explicit period fractions

## First-Period Parity Checks

The flag-on tests prove the first-period senior interest calculation can
reproduce the Excel rate/day-count evidence without changing opening debt.

TUHO:

```text
43,359.0 kEUR opening debt * 5.9500% * 181 / 360 = about 1,297.1 kEUR
```

Oborovo:

```text
42,852.267 kEUR opening debt * 5.95136% * 184 / 360 = about 1,303.5 kEUR
```

## Opening Balance Policy

The senior opening balance policy is unchanged. Operating senior debt remains
principal-only:

- senior IDC is not capitalized into operating senior debt
- commitment fees are not capitalized into operating senior debt
- construction diagnostics remain separate

## Known Remaining Gaps

This branch only introduces the runtime-safe rate/day-count path. It does not:

- opt in TUHO or Oborovo factories
- change DSCR sculpting inputs
- change repayment formulas
- change SHL mechanics
- change revenue, OPEX, tax, R99, sponsor waterfall, or construction
  capitalization

Future parity work still needs full-period Excel schedule evidence before any
project factory opt-in.

## Next Branch Recommendation

Use a small follow-up branch to add fixture-backed TUHO and Oborovo full-senior
rate schedules and assess full-period senior debt service parity:

```text
phase7k-senior-rate-schedule-project-opt-in
```
