# PR-F1 Canonical Period Axis Freeze

## Authority decision

`ProjectInfo` is the persisted timeline authority. Its explicit `cod_date` is
carried into `financial_engine.inputs.CalendarInput`. Runtime validates it
against `financial_close + construction_months` and fails with
`PERIOD_AXIS_COD_MISMATCH` on disagreement. An old payload without the required
`ProjectInfo.cod_date` already fails deserialization; it cannot silently create
a different axis.

`finco_core.engine.period_engine.PeriodEngine` is the only axis producer.
`domain.period_engine` remains a compatibility re-export and contains no axis
logic. The engine creates one immutable tuple and validates it before exposing
it. Semiannual integer horizons contain exactly `horizon_years * 2` operating
periods. The final horizon date is the final scheduled semiannual boundary,
not literal `COD + horizon_years` followed by a clipped residual period.

Construction runs continuously from financial close to the operating boundary.
The explicit Oborovo convention preserves one source construction column. The
serialized default convention emits meaningful six-month segments, folds a
near-boundary remainder shorter than seven days into the preceding segment,
and never emits a zero-day placeholder. A real first operating stub remains
possible. PPA flags use period starts on this same axis and the existing typed
PPA end-date convention.

## Production authority inventory

| Surface | Axis behavior after PR-F1 |
|---|---|
| `finco_core/engine/period_engine.py` | Sole producer; immutable tuple; COD, count, continuity and phase invariants |
| `domain/period_engine.py` | Re-export only |
| `ProjectInfo` / serialization / cache | Explicit COD persisted and cached; mismatch fails closed |
| project-input adapter | Carries explicit COD and typed convention into `CalendarInput` |
| operating / revenue / OPEX | Receive the same `PeriodEngine`; returned keys must exactly equal canonical order |
| depreciation | Built from the canonical tuple; book and tax schedules must exactly equal its keys |
| tax / CFADS | Existing count, duplicate and exact-order checks retained |
| Senior debt / sizing | Explicit operating debt-active subset; full-axis result maps absent debt periods to zero |
| SHL / post-Senior cash | Full canonical tuple and strict equal-length/index mapping |
| DSRA | Existing equal-length, duplicate, positive-duration and chronological guards retained |
| Distribution Account / shareholder waterfall | Strict post-Senior, DSCR, DSRF and SHL vector maps |
| sponsor returns | Strict SHL and post-Senior vector maps |
| diagnostics / audit | Base-performance reconciliation now uses strict maps, not `dict(zip(...))` |
| presentation / exports / audit | Clean presentation uses strict vector maps and rejects duplicate waterfall dates; exports consume immutable result/audit objects with no independent axis construction |

Independent absolute-index assumptions remain prohibited. Contractual Senior
and SHL indices are resolved from the produced operation subset. Tests that
formerly assumed two construction positions now derive the expected absolute
index from the first operating position.

## Exact source anchors

| Project | Before | After |
|---|---|---|
| TUHO | 2 construction + 61 operation; zero-day construction placeholder; final one-day operation ending 2060-01-01 | 1 construction + 60 operation; first operation 2030-01-01 to 2030-06-30, 181 days; final 2059-12-31 |
| Oborovo | 1 construction + 60 operation; final 2060-06-30 | Unchanged; first operation 2030-06-30 to 2030-12-31, 184 days; final 2060-06-30 |
| Generic Solar | 2 construction + 41 operation; one-day tail ending 2051-01-01 | 2 construction + 40 operation; final 2050-12-31 |
| Generic Wind | 2 construction + 51 operation; one-day tail ending 2056-07-01 | 3 meaningful construction + 50 operation; final 2056-06-30 |

The full TUHO and Oborovo vectors are locked for indices, starts, ends, day
counts, phase flags, operating indices, operating years, half-year labels and
PPA flags. The generic matrix covers Solar, Wind, BESS, Solar+BESS, Wind+BESS,
6/12/18-month construction, leap years, Jan 1, Jun 30, Jul 1, Dec 31 and a
near-boundary COD.

## Fail-closed attacks

The axis rejects empty, duplicate, non-contiguous, out-of-order, zero/negative
duration, overlapping/gapped, invalid phase and wrong operating-count inputs.
Parallel vectors reject unequal lengths, duplicate keys and out-of-order keys
before dictionary construction. Consumer schedules reject missing, extra,
shifted and reordered keys. Fixed-point delta comparison rejects unequal vector
lengths instead of truncating with `min(len(...))`.

## Base-versus-head financial bridge

All values are kEUR except counts/dates. No formulas, tax policy, debt policy,
SHL policy, project identity routing or source-output replay changed.

| Metric | Solar delta | Wind delta | Oborovo delta |
|---|---:|---:|---:|
| operating periods | -1 | -1 | 0 |
| final date | 2051-01-01 -> 2050-12-31 | 2056-07-01 -> 2056-06-30 | unchanged |
| revenue | -16.518045387 | -31.697201897 | 0 |
| OPEX | 0 | 0 | 0 |
| EBITDA | -16.518045387 | -31.697201897 | 0 |
| depreciation | 0 | 0 | 0 |
| Senior interest / principal / service | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| SHL gross / closing | 0 / 0 | 0 / 0 | 0 / 0 |
| cash tax | -4.129511347 | -7.924300474 | 0 |
| Base CFADS | -12.388534040 | -23.772901423 | 0 |
| Bank CFADS | -11.562631771 | -21.395611281 | 0 |
| Senior debt size | 0 | 0 | 0 |
| legal equity distributions | 0 | 0 | 0 |

These Solar/Wind deltas are exactly the economics formerly booked into the
removed one-day terminal periods and their tax/CFADS consequences. Existing
PPA and day-count policy is otherwise unchanged.

For the explicit TUHO clean DSCR test contract, removal of the terminal period
and the zero-day construction placeholder changes the axis from 63 total / 61
operating / 2060-01-01 to 61 total / 60 operating / 2059-12-31. Revenue changes
by -56.124426017, EBITDA by -56.124426017, cash tax by +66.959170873, Base
CFADS by -123.083596891, Bank CFADS by -106.861295043, Senior debt size by
-402.111244838, Senior interest by -790.459648900 and Senior service by
-1,192.570893738. This is the direct full-horizon consequence of removing the
phantom period while applying the same formulas to the canonical axis. TUHO's
factory production clean-tax path remains explicitly gated, so no unsupported
G2C/returns claim is made.

## Governance

No project name/code dispatch, workbook runtime read, source-vector replay,
target fitting, approved/expected delta, balancing plug, terminal top-up,
virtual debt, post-engine stub deletion or tolerance-based economic capacity
was introduced. `financial_engine/tax/engine.py` is untouched.

## Local verification

- Final canonical-axis, G0/G2 and PR-6 through PR-10 ring: 772 passed.
- Modified-boundary, B3/B4, Phase 2C and PR-8 presentation ring: 408 passed.
- B3/B4 standalone regression: 189 passed.
- G1, PR-5 and B5/B7/B8/source-contract locks: 211 passed.
- Construction/Revenue/OPEX/depreciation selection: 233 passed before one
  base-reproduced TUHO depreciation expectation failure; the OPEX engine
  selection excluding its base-reproduced BESS UI guardrail class passed 54.

Three local legacy-suite blockers reproduce unchanged on the exact base and
were not altered: `test_revenue_formula_units.py` has a pre-existing collection
syntax error, the BESS scenario UI guardrail receives `Unknown project type:
BESS`, and one TUHO book-depreciation bridge expects 70,691.5 while both base
and head produce 72,993.71. C3B1 workbook direct-access also reaches a local
Windows permission error after its preceding tests pass; the dedicated Linux
exact-head workflow is the authoritative check for that environment-specific
surface.
