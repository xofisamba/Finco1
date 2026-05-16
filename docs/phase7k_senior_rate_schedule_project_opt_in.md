# Phase 7K Senior Rate Schedule Project Opt-In

## Purpose

This branch evaluates project-specific senior rate/day-count opt-in behavior
using explicit fixture schedules for TUHO and Oborovo. It does not enable the
new senior rate schedule engine globally and does not change project factories.

The runtime default remains unchanged:

```text
ProjectInfo.use_senior_rate_schedule_engine = False
```

## Scope

Changed behavior is limited to test-only cloned inputs with:

```text
use_senior_rate_schedule_engine = True
senior_debt_interest_config.enabled = True
```

No runtime formula, SHL, revenue, OPEX, tax, construction capitalization, R99,
sponsor, UI, or cache logic is changed.

## Fixture Inputs

### TUHO

The TUHO fixture uses explicit annual all-in rates and period fractions for the
first four senior periods and the final repayment period based on the Excel
bridge:

| op_idx | annual all-in rate | period fraction | Excel evidence |
|---:|---:|---:|---|
| 0 | 5.9500% | 181 / 360 | First operating period |
| 1 | 5.9500% | 184 / 360 | Second operating period |
| 2 | 5.9500% | 181 / 360 | Third operating period |
| 3 | 5.9500% | 184 / 360 | Fourth operating period |
| 27 | 5.9500% | 184 / 360 | Final senior repayment period |

Unmapped periods keep the legacy annual rate and fixed semiannual fraction in
the fixture so this remains an evaluation, not a full parity claim.

### Oborovo

The Oborovo fixture uses explicit annual all-in rates and period fractions for
the same bridge periods:

| op_idx | annual all-in rate | period fraction | Excel evidence |
|---:|---:|---:|---|
| 0 | 5.95136% | 184 / 360 | First operating period |
| 1 | 5.95136% | 181 / 360 | Second operating period |
| 2 | 5.83832% | 184 / 360 | Third operating period |
| 3 | 5.83832% | 182 / 360 | Fourth operating period |
| 27 | 5.84072% | 182 / 360 | Final senior repayment period |

Unmapped periods keep the legacy annual rate and fixed semiannual fraction.

## TUHO Flag-Off vs Flag-On Bridge

| Metric | Flag-off Python | Flag-on fixture | Excel | Comment |
|---|---:|---:|---:|---|
| Total senior DS | 65,826.4 | 66,167.2 | 66,181.3 | Total moves toward Excel by +340.8 kEUR. |
| op_idx 0 interest | 1,246.6 | 1,297.1 | 1,297.1 | First-period interest parity achieved. |
| op_idx 0 principal | 742.5 | 702.3 | 819.3 | Principal/sculpting gap remains. |
| op_idx 0 DS | 1,989.1 | 1,999.4 | 2,116.4 | DS gap remains after interest parity. |
| op_idx 0 closing | 42,616.5 | 42,656.7 | 42,539.3 | Balance remains high because principal is low. |
| op_idx 27 DS | 3,421.8 | 3,439.5 | 2,844.8 | Final-period repayment gap remains. |

## Oborovo Flag-Off vs Flag-On Bridge

| Metric | Flag-off Python | Flag-on fixture | Excel | Comment |
|---|---:|---:|---:|---|
| Total senior DS | 63,500.9 | 63,893.0 | n/a | Total increases by +392.1 kEUR. |
| op_idx 0 interest | 1,210.6 | 1,303.5 | 1,303.5 | First-period interest parity achieved. |
| op_idx 0 principal | 844.9 | 764.7 | 935.7 | Principal/sculpting gap remains. |
| op_idx 0 DS | 2,055.5 | 2,068.2 | 2,239.1 | DS gap remains after interest parity. |
| op_idx 0 closing | 42,007.4 | 42,087.6 | 41,916.6 | Balance remains high because principal is low. |
| op_idx 27 DS | 2,530.2 | 2,545.8 | 1,507.4 | Final-period repayment gap remains. |

## Interpretation

The project-specific opt-in confirms the rate/day-count engine can reproduce
first-period Excel senior interest for both TUHO and Oborovo when explicit
fixture inputs are provided.

Full-period senior debt service parity is not achieved by rate/day-count alone.
The remaining gaps are primarily principal and sculpting mechanics:

- debt service remains too low in early periods after interest parity,
- closing balances remain too high,
- final-period principal remains materially different,
- full-schedule parity still needs the Excel DSCR/sculpting basis and repayment
  timing to be mapped.

## Opening Balance Policy

The senior opening balance policy is preserved:

- operating senior debt opens principal-only,
- senior IDC is not added to operating senior debt,
- commitment fees are not added to operating senior debt.

## Recommendation

Do not globally enable the senior rate schedule engine yet.

Next branch should focus on the principal / sculpting basis now that
rate/day-count parity is isolated:

```text
phase7k-senior-dscr-sculpting-basis-bridge
```

Non-goals remain unchanged:

- no SHL `fcf_waterfall`,
- no senior opening balance policy change,
- no revenue, OPEX, tax, construction capitalization, R99, sponsor, UI, or
  cache changes.
