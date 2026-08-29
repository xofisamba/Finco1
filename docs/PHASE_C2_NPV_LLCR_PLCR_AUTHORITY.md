# Phase C2 - Project NPV and lender coverage authority

## Decision

Phase C2 is an immutable downstream layer over the clean production result.
It does not rebuild or mutate Project cash flows, Base or Bank CFADS, Senior
debt, tax, SHL, distributions, or construction financing.

The implemented discount convention is `ACT_365_FIXED`:

```text
year_fraction = (cashflow_date - valuation_date).days / 365
discount_factor = (1 + annual_rate) ** year_fraction
present_value = cashflow / discount_factor
```

One pure kernel supplies Project NPV, LLCR and PLCR audit rows. Rates, dates and
CFADS cases are typed inputs. They are never inferred from project identity,
IRR, gearing, Senior pricing, target DSCR, or `min_llcr`.

## Pre-C2 inventory

| Concept | Existing clean authority before C2 | C2 treatment |
|---|---|---|
| Project cash-flow vector and XIRR | `ProjectReturnResult.cashflows` / `project_xirr` | consumed unchanged |
| Base CFADS | `TaxAndCfadsSchedules.cfads_keur` | selectable only by typed `BASE` policy |
| Bank CFADS | `DebtSizingSchedules.bank_cfads_keur` | selectable only by typed `BANK` policy |
| Senior balances and maturity | `SeniorDebtSchedules` and C1 terminal state | denominator and LLCR horizon authority |
| project life | canonical operating-period axis | PLCR horizon authority |
| `FinancingParams.min_llcr` | covenant threshold | comparison only; never a rate |
| Project discount rate | no generic authority | optional typed policy; otherwise `NOT_CONFIGURED` |
| coverage discount rate | no generic authority | optional typed policy; otherwise fail closed |
| coverage CFADS case | no generic authority | optional typed `BASE`/`BANK`; otherwise fail closed |
| PLCR threshold | absent | not introduced |

Legacy `finco_core.waterfall` NPV/LLCR/PLCR fields are not clean production
authority and are not called by C2.

## Source-model audit

The workbooks were inspected formula-first with cached values used only as
evidence. No workbook vector is loaded by production.

### TUHO

- `Inputs!D452 = 6.6%` is an explicit hardcoded "Discount rate Project NPV".
- `CF!C125 = XNPV(Inputs!D452, CF!G125:BO125, CF!G124:BO124)`.
- The workbook's row 125 cash-flow basis is not the C1 boundary. C2 therefore
  uses the source-proven 6.6% configuration and XNPV timing convention, but
  discounts the exact C1 cash-flow vector.
- `CF!B129 = Inputs!D184 = 5.95%`; `Inputs!D184` is Senior pricing.
- `CF!G129` uses periodic `NPV`, `FCFB Senior` row 132 and
  `SUM(DS!G53, DS!G88)`. This mixes source-specific timing and potentially
  multiple debt balances. It does not prove a generic Base/Bank clean case or
  an ACT/365 coverage policy.
- No separate source-proven PLCR formula was found.

Classification: Project rate and XNPV convention are
`SOURCE_PROVEN_PROJECT_SPECIFIC`. LLCR mechanics are project-specific and not
promoted. PLCR is `UNRESOLVED`.

### Oborovo

- `Outputs!C34` presents "discount rate 9.2%" beside Project NPV.
- The formula chain uses `Inputs!D462` and `CF!C136 = XNPV(...)`, but cached
  rate and output are `#N/A` in the reviewed workbook.
- The 9.2% label is presentation evidence, not a complete typed input bridge.
- `Inputs!D224 = 1.15` is the minimum LLCR threshold, not a discount rate.
- No complete source-proven clean Base/Bank LLCR or PLCR contract was found.

Classification: Project rate is `SOURCE_PRESENTATION_ONLY`; Project NPV,
LLCR and PLCR runtime authorities remain `UNRESOLVED`.

### KUPI

- `Inputs!D452 = 10.5%` is an explicit Project NPV rate.
- The workbook contains XNPV Project formulas, but cached outputs are `#N/A`.
- LLCR follows the same project-specific periodic pattern as TUHO with
  `Inputs!D184 = 6.1%`; no separate PLCR contract was found.
- KUPI remains out-of-sample and is not promoted to production.

Classification: useful methodology/configuration evidence only.

### Generic Solar and Wind

No source-backed Project discount rate, coverage discount rate or coverage
CFADS case exists. All three metrics therefore fail closed rather than using a
professional-looking invented number.

## Typed input authority

`ProjectInputs.valuation` contains optional `ValuationPolicies`:

- `ProjectValuationPolicy`: annual rate, explicit/first-cash-flow valuation
  date policy, `ACT_365_FIXED`, and an authority label.
- `DebtCoverageValuationPolicy`: annual rate, explicit `BASE` or `BANK` CFADS,
  first-Senior-period-opening calculation boundary, `ACT_365_FIXED`, and an
  authority label.

The input serialization round-trips these policies. TUHO alone is configured
for Project NPV using the source-proven 6.6% rate. Coverage is not configured
for any current production project.

## Project NPV

Project NPV consumes `ProjectReturnResult.cashflows` exactly. It uses each
row's `net_unlevered_project_cashflow_keur`; there is no second Project-return
builder, financing tax shield or terminal value.

Every result exposes valuation date, annual rate, convention, authority label,
each dated undiscounted cash flow, year fraction, discount factor, discounted
cash flow and total NPV.

Statuses are `OK`, `NOT_CONFIGURED`, `INVALID_DISCOUNT_RATE`,
`VALUATION_DATE_UNAVAILABLE`, `UPSTREAM_PROJECT_RETURN_UNAVAILABLE`,
`CASHFLOW_BEFORE_UNSUPPORTED_VALUATION_DATE`, and `NON_FINITE_RESULT`.

Current production result:

| Project | Rate | Valuation date | NPV kEUR | Status |
|---|---:|---|---:|---|
| Generic Solar | - | - | - | `NOT_CONFIGURED` |
| Generic Wind | - | - | - | `NOT_CONFIGURED` |
| Oborovo | - | - | - | `NOT_CONFIGURED` |
| TUHO | 6.6% | 2028-06-30 | 29,291.167288 | `OK` |

The TUHO amount is a clean C1-cash-flow NPV, not a replay or target match to
the workbook's differently defined row 125.

## LLCR

When configured, LLCR is measured at the opening of the first Senior period:

```text
PV(selected Base or Bank CFADS through contractual Senior maturity)
-------------------------------------------------------------------
Senior opening balance at the calculation period
```

Post-maturity CFADS rows remain in the audit vector marked
`AFTER_SENIOR_CONTRACTUAL_MATURITY` and do not enter the numerator.

`minimum_llcr` is reported separately from calculated LLCR. Headroom is
`LLCR - minimum_llcr`; threshold status is `PASS`, `FAIL`, `NOT_CONFIGURED` or
`NOT_APPLICABLE`. It does not feed Senior sizing.

## PLCR

When configured, PLCR uses the same selected lender CFADS case, calculation
date, discount policy and Senior opening denominator as LLCR, but extends the
numerator through the canonical final operating period. It creates no terminal
value. No PLCR threshold is introduced.

## Coverage fail-closed contract

Coverage statuses include `OK`, `NOT_APPLICABLE_NO_SENIOR`,
`DEBT_BALANCE_ZERO`, `COVERAGE_CFADS_CASE_NOT_CONFIGURED`,
`COVERAGE_DISCOUNT_RATE_NOT_CONFIGURED`, `INVALID_DISCOUNT_RATE`,
`SENIOR_MATURITY_UNAVAILABLE`, `PROJECT_LIFE_HORIZON_UNAVAILABLE`,
`PERIOD_AXIS_MISMATCH`, and `NON_FINITE_RESULT`.

The engine validates unique canonical period indices and exact Base/Bank vector
alignment. It never returns zero, infinity or NaN as a valid business ratio.

Current Solar, Wind, Oborovo and TUHO LLCR/PLCR status is
`COVERAGE_CFADS_CASE_NOT_CONFIGURED`. This is intentional: source evidence has
not resolved a generic clean Base/Bank case and coverage discount convention.

## Causal and governance proofs

Focused tests prove:

- Project rate up means NPV down for the controlled positive profile.
- revenue up means NPV up; hard CAPEX, OPEX or unlevered tax up means NPV down.
- Project NPV audit amounts exactly equal C1 Project cash flows.
- selected CFADS up means LLCR/PLCR up; debt or rate up means ratios down.
- `BASE` and `BANK` policies select only their named canonical vectors.
- LLCR excludes and PLCR includes valid post-loan project-life CFADS.
- missing policy, rate, maturity or aligned axes fail closed.
- project name, code and company do not dispatch C2 behavior.

Production contains no workbook replay, project-identity dispatch, target
fitting, delta allowance, balancing plug, artificial terminal cash, UI-side
calculation, or post-engine mutation.

## C1 non-regression

The approved C1 Project XIRRs remain unchanged:

- Generic Solar: `7.593168077588568%`
- Generic Wind: `11.366132007429408%`
- Oborovo: `8.512246818013307%`
- TUHO: `9.477998283668464%`

C2 reads the frozen C1 and financing outputs only after those calculations are
complete.
