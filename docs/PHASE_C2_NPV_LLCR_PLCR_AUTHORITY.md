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

One pure kernel supplies Project NPV, LLCR and PLCR audit rows. Rates, dates,
CFADS cases, metric-specific cash-flow bases and denominator authority are typed
inputs. They are never inferred from project identity, IRR, gearing, target
DSCR, or `min_llcr`.

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
- `Inputs!D207` ("Min LLCR") equals `Inputs!C160`, whose Bank Case lookup
  resolves to `1.20`. This is the source covenant threshold, not a calculated
  LLCR output and not a debt-sizing input in C2.
- `CF!G129` uses periodic `NPV`, `FCFB Senior` row 132 and
  `SUM(DS!G53, DS!G88)`. This mixes source-specific timing and potentially
  multiple debt balances. It does not prove a generic Base/Bank clean case or
  an ACT/365 coverage policy.
- No separate source-proven PLCR formula was found.

Classification: Project rate and XNPV convention are
`SOURCE_PROVEN_PROJECT_SPECIFIC`. Correction A promotes only the explicitly
typed TUHO LLCR components proven below; it does not call them generic source
parity. PLCR is `UNRESOLVED`.

### Oborovo

- `Outputs!C34` presents "discount rate 9.2%" beside Project NPV.
- The formula chain uses `Inputs!D462` and `CF!C136 = XNPV(...)`, but cached
  rate and output are `#N/A` in the reviewed workbook.
- The 9.2% label is presentation evidence, not a complete typed input bridge.
- `Inputs!D224 = Inputs!C177 = 1.15` is the source minimum LLCR threshold,
  explicitly mapped in the Oborovo factory; it is not a discount rate.
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

## Correction A source coverage trace

### TUHO formula chain

- Base/current lender cash is `CF!row69` (`Free Cash Flow for Banks`).
- Bank sizing cash is `DS!row17 = Macro!row50`; it is a distinct scenario.
- `CF!row132` is `FCFB Senior = CF!row69 * CF!row12`.
- `CF!row12 = Flags!row24`, whose formula derives a maturity-days fraction from
  the source last-repayment date and period boundaries.
- The final source ratio is `5,183.102680983 / 5,240.374533812 =
  0.9890710382513661`.
- `CF!G129 = (G81 + NPV(B129,H132:AF132)) / SUM(DS!G53,DS!G88)`.
  `B129 = Inputs!D184 = 5.95%`. Excel therefore applies the quoted 5.95%
  directly once per semiannual NPV row, with the first future cash flow at
  exponent one. It does not divide the quote by two.
- At the opening headline boundary, `G81` (DSRA) and `DS!G88` (refinancing)
  are zero, while `DS!G53` equals the first operating-period Senior opening.
- The source formula's fixed `AF` endpoint excludes the typed final maturity
  periods, including partial `AI`. C2 does not replay that inconsistent range:
  its LLCR horizon is the canonical 28-period Senior contract. This horizon
  choice is `GENERIC_FINCO_POLICY`, while the case, eligibility transform,
  periodic source convention and opening denominator are source-proven TUHO
  configuration.

Period-by-period source reconciliation (kEUR):

| P | Base | Bank | Factor | FCFB Senior | Difference |
|---:|---:|---:|---:|---:|---:|
|1|3070.175837|2539.633673|1.000000000000|3070.175837|0|
|2|3121.062730|2581.727049|1.000000000000|3121.062730|0|
|3|3111.649812|2573.630070|1.000000000000|3111.649812|0|
|4|3163.224118|2616.286922|1.000000000000|3163.224118|0|
|5|3121.136562|2573.896879|1.000000000000|3121.136562|0|
|6|3155.434766|2602.181460|1.000000000000|3155.434766|0|
|7|3156.832407|2603.173172|1.000000000000|3156.832407|0|
|8|3209.155596|2646.319689|1.000000000000|3209.155596|0|
|9|3194.776671|2633.974949|1.000000000000|3194.776671|0|
|10|3247.728770|2677.631993|1.000000000000|3247.728770|0|
|11|3200.023176|2627.901561|1.000000000000|3200.023176|0|
|12|3253.062234|2671.457940|1.000000000000|3253.062234|0|
|13|3276.606835|2691.772238|1.000000000000|3276.606835|0|
|14|3312.613503|2721.352153|1.000000000000|3312.613503|0|
|15|3340.219714|2745.189649|1.000000000000|3340.219714|0|
|16|3395.582471|2790.690030|1.000000000000|3395.582471|0|
|17|3418.120112|2810.547407|1.000000000000|3418.120112|0|
|18|3474.774037|2857.131065|1.000000000000|3474.774037|0|
|19|3494.037236|2874.133683|1.000000000000|3494.037236|0|
|20|3551.949456|2921.771258|1.000000000000|3551.949456|0|
|21|3556.829762|2923.046475|1.000000000000|3556.829762|0|
|22|3595.915803|2955.167865|1.000000000000|3595.915803|0|
|23|3626.254089|2981.359117|1.000000000000|3626.254089|0|
|24|3686.357748|3030.773909|1.000000000000|3686.357748|0|
|25|6108.935763|4061.181830|1.000000000000|6108.935763|0|
|26|6089.999805|4128.494236|1.000000000000|6089.999805|0|
|27|6094.596723|3996.774007|1.000000000000|6094.596723|0|
|28|5240.374534|4063.018880|0.989071038251|5183.102681|0|

### Oborovo formula chain

Oborovo independently proves the same three cash-flow layers:
`CF!row79` Base/current, `DS!row20 = Macro!row50` Bank sizing and
`CF!row141 = CF!row79 * CF!row13`. Its final source factor is
`0.988950276243094`. Its source `Inputs!D224 = Inputs!C177` proves and maps the
typed covenant threshold `min_llcr = 1.15`, but no LLCR formula or output was
found. Therefore no rate, case, denominator or calculation-boundary authority
is promoted for Oborovo.

| P | Base | Bank | Factor | FCFB Senior | Difference |
|---:|---:|---:|---:|---:|---:|
|1|2567.349025|2575.003425|1.000000000000|2567.349025|0|
|2|2525.490073|2533.019673|1.000000000000|2525.490073|0|
|3|2569.148051|2576.603771|1.000000000000|2569.148051|0|
|4|2603.443917|2610.818596|1.000000000000|2603.443917|0|
|5|2625.001614|2637.750489|1.000000000000|2625.001614|0|
|6|2636.335491|2648.870299|1.000000000000|2636.335491|0|
|7|2664.777640|2677.450151|1.000000000000|2664.777640|0|
|8|2654.033628|2666.493959|1.000000000000|2654.033628|0|
|9|2705.149005|2717.743626|1.000000000000|2705.149005|0|
|10|2671.648901|2684.033199|1.000000000000|2671.648901|0|
|11|2738.621200|2751.102177|1.000000000000|2738.621200|0|
|12|2696.917283|2709.258155|1.000000000000|2696.917283|0|
|13|2787.712120|2800.146254|1.000000000000|2787.712120|0|
|14|2705.117466|2717.344920|1.000000000000|2705.117466|0|
|15|2829.921351|2842.272827|1.000000000000|2829.921351|0|
|16|2720.486890|2732.633460|1.000000000000|2720.486890|0|
|17|2872.760887|2885.028051|1.000000000000|2872.760887|0|
|18|2734.787246|2746.851238|1.000000000000|2734.787246|0|
|19|2908.271905|2920.419789|1.000000000000|2908.271905|0|
|20|2756.383077|2768.396037|1.000000000000|2756.383077|0|
|21|2764.864157|2776.957605|1.000000000000|2764.864157|0|
|22|2606.877012|2618.770601|1.000000000000|2606.877012|0|
|23|2809.649381|2821.653357|1.000000000000|2809.649381|0|
|24|2619.362859|2631.168533|1.000000000000|2619.362859|0|
|25|2980.612059|2279.787087|1.000000000000|2980.612059|0|
|26|2683.078683|2103.843632|1.000000000000|2683.078683|0|
|27|2979.951695|2248.762942|1.000000000000|2979.951695|0|
|28|2656.183745|2057.780429|0.988950276243|2626.833648|0|

KUPI independently repeats the TUHO pattern: Base `CF!row69`, Bank
`DS!row17`, `FCFB Senior = Base * row12`, a final factor of
`0.988950276243094`, and periodic `NPV(6.1%, ...)` with the same fixed `AF`
endpoint inconsistency. It supports the separated contract but remains
out-of-sample and supplies no production runtime vector.

## Typed input authority

`ProjectInputs.valuation` contains optional `ValuationPolicies`:

- `ProjectValuationPolicy`: annual rate, explicit/first-cash-flow valuation
  date policy, `ACT_365_FIXED`, and an authority label.
- `DebtCoverageValuationPolicy`: quoted rate, explicit `BASE` or `BANK` CFADS,
  separate LLCR/PLCR cash-flow bases, opening-Senior denominator basis,
  first-Senior-period-opening calculation boundary, discount convention and an
  authority label.

Coverage is explicitly three-layered:

```text
BASE or BANK economic scenario CFADS
-> metric-specific RAW or SENIOR_ELIGIBLE cash-flow basis
-> typed discount convention and metric horizon
```

`SENIOR_ELIGIBLE_CFADS` reuses the typed
`SeniorSculptingConfig.debt_service_availability_schedule`; no source cash-flow
vector is replayed. `PERIODIC_COMPOUNDING` requires an explicit rate conversion,
periods/year and first-cash-flow timing. The supported source conversion is
`AS_QUOTED_PER_MODEL_PERIOD` with `END_OF_FIRST_PERIOD` timing.

The input serialization round-trips these policies. TUHO alone is configured
for Project NPV using the source-proven 6.6% rate and for source-specific LLCR.
PLCR and all Oborovo/Solar/Wind coverage remain unconfigured.

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
PV(eligible selected Base or Bank CFADS through contractual Senior maturity)
-------------------------------------------------------------------
Senior opening balance at the calculation period
```

Every row exposes raw selected CFADS, eligibility factor, eligible CFADS,
inclusion status, exponent/fraction, discount factor and discounted amount.
Post-maturity CFADS rows remain in the audit vector marked
`AFTER_SENIOR_CONTRACTUAL_MATURITY` and do not enter the numerator.

`minimum_llcr` is reported separately from calculated LLCR. Headroom is
`LLCR - minimum_llcr`; threshold status is `PASS`, `FAIL`, `NOT_CONFIGURED` or
`NOT_APPLICABLE`. It does not feed Senior sizing.

## PLCR

When configured, PLCR uses the selected lender CFADS case, calculation date,
discount policy and Senior opening denominator, but requires
`RAW_SELECTED_CFADS` and extends the numerator through the canonical final
operating period. It never inherits zero Senior availability after maturity.
It creates no terminal value. No PLCR threshold is introduced. No current
project has an approved explicit PLCR policy, so PLCR remains fail closed.

## Coverage fail-closed contract

Coverage statuses include `OK`, `NOT_APPLICABLE_NO_SENIOR`,
`DEBT_BALANCE_ZERO`, `COVERAGE_CFADS_CASE_NOT_CONFIGURED`,
`COVERAGE_CASHFLOW_BASIS_NOT_CONFIGURED`,
`COVERAGE_CASHFLOW_BASIS_UNSUPPORTED_FOR_METRIC`,
`COVERAGE_ELIGIBILITY_AUTHORITY_UNAVAILABLE`,
`COVERAGE_DISCOUNT_RATE_NOT_CONFIGURED`, `INVALID_DISCOUNT_RATE`,
`COVERAGE_DISCOUNT_CONVENTION_UNSUPPORTED`,
`COVERAGE_CALCULATION_DATE_POLICY_UNSUPPORTED`,
`COVERAGE_DENOMINATOR_AUTHORITY_UNAVAILABLE`,
`SENIOR_MATURITY_UNAVAILABLE`, `PROJECT_LIFE_HORIZON_UNAVAILABLE`,
`PERIOD_AXIS_MISMATCH`, and `NON_FINITE_RESULT`.

The engine validates unique canonical period indices and exact Base/Bank vector
alignment. It never returns zero, infinity or NaN as a valid business ratio.

Solar, Wind and Oborovo LLCR/PLCR status is
`COVERAGE_CFADS_CASE_NOT_CONFIGURED`. TUHO LLCR is configured with Base CFADS,
Senior eligibility, the source-specific periodic convention and Senior opening
denominator. TUHO PLCR remains `COVERAGE_CASHFLOW_BASIS_NOT_CONFIGURED`.

TUHO canonical Correction A output is:

- calculation date: `2029-12-31` (canonical first Senior-period opening);
- selected case/basis: `BASE / SENIOR_ELIGIBLE_CFADS`;
- quoted/effective per-period rate: `5.95% / 5.95%`;
- included periods: `28`, final factor `0.9890710382513661`;
- PV eligible CFADS: `46,321.692749 kEUR`;
- Senior opening denominator: `43,789.921117 kEUR`;
- LLCR: `1.0578163095x`;
- source covenant minimum/headroom/status:
  `1.20x / -0.1421836905x / FAIL`.

The calculated clean LLCR remains `1.0578163095x`; only its comparison against
the source-backed TUHO covenant threshold changes. `min_llcr` does not drive
Senior sizing, sculpting, debt service, CFADS, NPV or returns. The source LLCR
numerator includes a DSRA term, but that reserve is zero at TUHO's configured
headline measurement boundary. A future configured project with a non-zero
measurement-date lender reserve requires explicit typed reserve/numerator
authority and must otherwise fail closed rather than omit the reserve.

The source-vs-clean TUHO eligible-CFADS maximum difference is
`635.306687 kEUR` because C1 clean Base CFADS is the frozen upstream authority.
C2 does not tune those cash flows to the workbook. The final clean/source FCFB
values are `5,171.277926 / 5,183.102681 kEUR`; both apply the identical typed
factor to their respective Base cash-flow authorities.

## Causal and governance proofs

Focused tests prove:

- Project rate up means NPV down for the controlled positive profile.
- revenue up means NPV up; hard CAPEX, OPEX or unlevered tax up means NPV down.
- Project NPV audit amounts exactly equal C1 Project cash flows.
- selected CFADS up means LLCR/PLCR up; debt or rate up means ratios down.
- `BASE` and `BANK` policies select only their named canonical vectors.
- Senior-eligible LLCR applies the typed factor after case selection; a
  controlled final raw `100` at factor `0.50` becomes eligible `50`, while
  PLCR retains the raw project-life cash flow.
- LLCR excludes and PLCR includes valid post-loan project-life CFADS.
- unsupported date policy, denominator, cash-flow basis, discount convention
  or missing eligibility authority fail closed.
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
