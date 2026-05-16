# Phase 7K Senior DSCR Sculpting Full Schedule Fixtures

## Purpose

This branch adds test-only full-tenor senior debt-service fixtures for TUHO and
Oborovo. The fixtures use the already-merged default-off senior rate schedule
engine and senior sculpting basis engine in `EXPLICIT_DEBT_SERVICE_SCHEDULE`
mode.

No project factory is opted in. Runtime defaults remain unchanged.

## Fixture Source

The schedules are derived from existing Excel full-model extract fixtures:

- `tests/fixtures/excel_tuho_full_model_extract.json`
- `tests/fixtures/excel_oborovo_full_model_extract.json`

For each project, the test fixture reads:

- `CF.senior_debt_service_keur`
- `DS.senior_principal_keur`
- `DS.senior_net_interest_keur`
- period dates

The test-only opening balance is reconstructed as the sum of Excel senior
principal over the 28-period senior tenor. This preserves the confirmed policy:
operating senior debt opens on principal only. Senior IDC and commitment fees
are not added to operating senior debt.

## Fixture Method

For each test-only cloned project:

```text
use_senior_rate_schedule_engine = True
senior_debt_interest_config.enabled = True
use_senior_sculpting_basis_engine = True
senior_sculpting_config.enabled = True
senior_sculpting_config.mode = EXPLICIT_DEBT_SERVICE_SCHEDULE
explicit_debt_service_schedule = full Excel senior DS schedule
```

The rate/day-count fixture is also derived from the Excel rows so that interest
matches the extracted Excel senior interest in each tenor period. The explicit
DS schedule then gives:

```text
principal[t] = explicit senior DS[t] - interest[t]
closing[t] = opening[t] - principal[t]
```

## TUHO Extracted Senior Schedule

| op_idx | date | opening | interest | principal | senior DS | closing |
|---:|---|---:|---:|---:|---:|---:|
| 0 | 2030-06-30 | 43,358.5 | 1,297.1 | 819.3 | 2,116.4 | 42,539.3 |
| 1 | 2030-12-31 | 42,539.3 | 1,293.7 | 857.8 | 2,151.4 | 41,681.5 |
| 2 | 2031-06-30 | 41,681.5 | 1,246.9 | 897.8 | 2,144.7 | 40,783.7 |
| 3 | 2031-12-31 | 40,783.7 | 1,240.3 | 940.0 | 2,180.2 | 39,843.7 |
| 4 | 2032-06-30 | 39,843.7 | 1,198.5 | 946.4 | 2,144.9 | 38,897.3 |
| 5 | 2032-12-31 | 38,897.3 | 1,182.9 | 985.6 | 2,168.5 | 37,911.8 |
| 6 | 2033-06-30 | 37,911.8 | 1,134.1 | 1,035.2 | 2,169.3 | 36,876.6 |
| 7 | 2033-12-31 | 36,876.6 | 1,121.5 | 1,083.8 | 2,205.3 | 35,792.8 |
| 8 | 2034-06-30 | 35,792.8 | 1,070.8 | 1,124.2 | 2,195.0 | 34,668.6 |
| 9 | 2034-12-31 | 34,668.6 | 1,054.3 | 1,177.1 | 2,231.4 | 33,491.5 |
| 10 | 2035-06-30 | 33,491.5 | 1,001.9 | 1,188.0 | 2,189.9 | 32,303.5 |
| 11 | 2035-12-31 | 32,303.5 | 982.4 | 1,243.8 | 2,226.2 | 31,059.7 |
| 12 | 2036-06-30 | 31,059.7 | 934.3 | 1,308.9 | 2,243.1 | 29,750.8 |
| 13 | 2036-12-31 | 29,750.8 | 904.8 | 1,363.0 | 2,267.8 | 28,387.8 |
| 14 | 2037-06-30 | 28,387.8 | 849.2 | 1,438.4 | 2,287.7 | 26,949.4 |
| 15 | 2037-12-31 | 26,949.4 | 819.6 | 1,506.0 | 2,325.6 | 25,443.3 |
| 16 | 2038-06-30 | 25,443.3 | 761.1 | 1,581.0 | 2,342.1 | 23,862.4 |
| 17 | 2038-12-31 | 23,862.4 | 725.7 | 1,655.3 | 2,380.9 | 22,207.1 |
| 18 | 2039-06-30 | 22,207.1 | 664.3 | 1,730.8 | 2,395.1 | 20,476.3 |
| 19 | 2039-12-31 | 20,476.3 | 622.7 | 1,812.1 | 2,434.8 | 18,664.2 |
| 20 | 2040-06-30 | 18,664.2 | 561.4 | 1,874.4 | 2,435.9 | 16,789.8 |
| 21 | 2040-12-31 | 16,789.8 | 510.6 | 1,952.0 | 2,462.6 | 14,837.7 |
| 22 | 2041-06-30 | 14,837.7 | 443.9 | 2,040.6 | 2,484.5 | 12,797.1 |
| 23 | 2041-12-31 | 12,797.1 | 389.2 | 2,136.5 | 2,525.6 | 10,660.7 |
| 24 | 2042-06-30 | 10,660.7 | 318.9 | 2,556.4 | 2,875.3 | 8,104.3 |
| 25 | 2042-12-31 | 8,104.3 | 246.5 | 2,676.5 | 2,923.0 | 5,427.8 |
| 26 | 2043-06-30 | 5,427.8 | 162.4 | 2,667.0 | 2,829.3 | 2,760.8 |
| 27 | 2043-12-31 | 2,760.8 | 84.0 | 2,760.8 | 2,844.8 | 0.0 |

TUHO total senior DS: `66,181.347` kEUR.

## Oborovo Extracted Senior Schedule

| op_idx | date | opening | interest | principal | senior DS | closing |
|---:|---|---:|---:|---:|---:|---:|
| 0 | 2030-12-31 | 42,852.3 | 1,303.5 | 935.7 | 2,239.1 | 41,916.6 |
| 1 | 2031-06-30 | 41,916.6 | 1,254.2 | 948.4 | 2,202.6 | 40,968.2 |
| 2 | 2031-12-31 | 40,968.2 | 1,222.5 | 1,018.0 | 2,240.5 | 39,950.2 |
| 3 | 2032-06-30 | 39,950.2 | 1,179.2 | 1,091.1 | 2,270.3 | 38,859.1 |
| 4 | 2032-12-31 | 38,859.1 | 1,150.7 | 1,142.9 | 2,293.7 | 37,716.2 |
| 5 | 2033-06-30 | 37,716.2 | 1,098.7 | 1,204.7 | 2,303.4 | 36,511.5 |
| 6 | 2033-12-31 | 36,511.5 | 1,079.4 | 1,248.8 | 2,328.2 | 35,262.7 |
| 7 | 2034-06-30 | 35,262.7 | 1,025.5 | 1,293.2 | 2,318.7 | 33,969.4 |
| 8 | 2034-12-31 | 33,969.4 | 1,005.3 | 1,358.0 | 2,363.3 | 32,611.5 |
| 9 | 2035-06-30 | 32,611.5 | 949.4 | 1,384.6 | 2,333.9 | 31,226.9 |
| 10 | 2035-12-31 | 31,226.9 | 926.2 | 1,466.0 | 2,392.3 | 29,760.9 |
| 11 | 2036-06-30 | 29,760.9 | 873.1 | 1,482.7 | 2,355.9 | 28,278.1 |
| 12 | 2036-12-31 | 28,278.1 | 841.1 | 1,593.8 | 2,434.9 | 26,684.3 |
| 13 | 2037-06-30 | 26,684.3 | 780.7 | 1,582.2 | 2,362.9 | 25,102.1 |
| 14 | 2037-12-31 | 25,102.1 | 748.5 | 1,723.0 | 2,471.5 | 23,379.1 |
| 15 | 2038-06-30 | 23,379.1 | 685.8 | 1,690.4 | 2,376.2 | 21,688.7 |
| 16 | 2038-12-31 | 21,688.7 | 648.1 | 1,860.6 | 2,508.7 | 19,828.0 |
| 17 | 2039-06-30 | 19,828.0 | 582.8 | 1,805.7 | 2,388.6 | 18,022.3 |
| 18 | 2039-12-31 | 18,022.3 | 539.5 | 2,000.0 | 2,539.5 | 16,022.2 |
| 19 | 2040-06-30 | 16,022.2 | 474.4 | 1,932.9 | 2,407.3 | 14,089.3 |
| 20 | 2040-12-31 | 14,089.3 | 422.2 | 1,992.6 | 2,414.7 | 12,096.8 |
| 21 | 2041-06-30 | 12,096.8 | 356.6 | 1,920.6 | 2,277.2 | 10,176.2 |
| 22 | 2041-12-31 | 10,176.2 | 304.9 | 2,148.7 | 2,453.6 | 8,027.4 |
| 23 | 2042-06-30 | 8,027.4 | 236.6 | 2,051.4 | 2,288.0 | 5,976.1 |
| 24 | 2042-12-31 | 5,976.1 | 178.8 | 1,509.9 | 1,688.7 | 4,466.2 |
| 25 | 2043-06-30 | 4,466.2 | 131.5 | 1,426.9 | 1,558.4 | 3,039.2 |
| 26 | 2043-12-31 | 3,039.2 | 90.7 | 1,575.0 | 1,665.8 | 1,464.2 |
| 27 | 2044-06-30 | 1,464.2 | 43.2 | 1,464.2 | 1,507.4 | 0.0 |

Oborovo total senior DS: `62,985.358` kEUR.

## Parity Result

| Project | Excel senior DS | Explicit fixture senior DS | Delta | Final balance |
|---|---:|---:|---:|---:|
| TUHO | 66,181.347 | 66,181.347 | 0.000 | 0.000 |
| Oborovo | 62,985.358 | 62,985.358 | 0.000 | 0.000 |

The first four periods and final repayment period are asserted against the
Excel extract for opening balance, interest, principal, debt service, and
closing balance.

## Downstream Impact Measurement

The explicit senior DS fixtures intentionally change senior debt service. They
are not calibrated to SHL or distributions.

| Project | Senior DS delta vs flag-off | SHL service delta | Distribution delta |
|---|---:|---:|---:|
| TUHO | +354.959 | +3,489.544 | -1,127.613 |
| Oborovo | -515.537 | 0.000 | +1,686.225 |

Revenue and OPEX remain unchanged in the test-only flag-on runs.

## Remaining Gaps

- This branch proves full-tenor explicit schedule consumption, not formula-based
  Excel sculpting.
- No project factory is opted in.
- SHL `fcf_waterfall` remains unimplemented.
- Downstream SHL and distributions still require separate calibration work.
- The explicit schedule is a parity harness and should not become the long-term
  source of truth unless the product explicitly chooses schedule-driven senior
  debt service.

## Recommendation

Next implementation choice:

1. If the objective is fast Excel parity, evaluate a controlled project-level
   opt-in to explicit senior DS schedules after review.
2. If the objective is formula transparency, proceed to a formula-based
   sculpting branch that reconstructs Excel senior DS basis rows.
3. B2 SHL `fcf_waterfall` should still wait until the R99/R102 and senior cash
   basis are deliberately selected.
