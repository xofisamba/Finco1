# Phase C1 - Decision-Complete Returns and Maturity Authority

## Authority

Phase C1 is downstream of the single clean G2C production calculation. It adds
no financing, tax, CAPEX, distribution, or terminal-payment mutation. The
canonical result is `CovenantGatedWaterfallResult.return_summary`; API, saved-run,
and export adapters may serialize it but may not calculate it.

## Three return concepts

| Return | Cash-flow boundary | Included | Excluded | Date convention | Status authority |
|---|---|---|---|---|---|
| Project / Unlevered | Underlying project before financing | Authoritative hard-CAPEX timing; operating EBITDA; cash tax recalculated by the canonical tax engine with typed zero-financing-interest authority and hard-CAPEX-only depreciation | Senior/SHL funding and service; IDC; commitment, structuring and VAT-facility costs; financing-cost tax shields; reserves; distributions; terminal value | Typed construction dates and canonical operating `period_end` dates | `ProjectReturnStatus` |
| Legal Equity | Existing G2C legal-equity investor vector | Share capital, share premium, other/additional legal-equity contributions and legal-equity distributions | SHL contributions, interest and principal | Existing G2C `waterfall_periods[].cashflow_date` | Existing G2B/G2C status, including unpaid BULLET and feedback fail-closed states |
| Total Sponsor | Existing G2C sponsor investor vector | Legal Equity vector plus SHL cash contribution, cash interest and principal receipts | PIK as a cash receipt; unsupported terminal recovery | Existing G2C `waterfall_periods[].cashflow_date` | Existing G2B/G2C status |

Project XIRR uses actual dates and `robust_xirr`. Its complete dated series is
part of the result. The row identity is:

`net = operating inflow - project cash tax + terminal component - hard CAPEX`

The terminal component is zero. Phase C1 does not assume sale value,
liquidation proceeds, recovery value, terminal sweep, or artificial repayment.

## Project investment bridge

`ProjectUses.total_project_uses_keur` remains the Sources & Uses and financing
authority. It is deliberately not renamed or changed. Project return uses only
`ProjectUses.hard_project_capex_keur`:

| Component | Classification | Project XIRR treatment |
|---|---|---|
| Hard CAPEX | `PROJECT_ECONOMICS` | Included on authoritative construction dates |
| Senior IDC | `FINANCING_ECONOMICS` | Excluded and disclosed |
| Senior commitment/structuring fees | `FINANCING_ECONOMICS` | Excluded and disclosed |
| VAT-facility IDC/commitment fee | `FINANCING_ECONOMICS` | Excluded and disclosed |
| SHL construction/operating interest | `FINANCING_ECONOMICS` | Excluded |
| Senior operating interest/principal | `FINANCING_ECONOMICS` | Excluded |
| Cash DSRA funding | `FINANCING_ECONOMICS` | Excluded and disclosed |
| Terminal sale/liquidation/recovery | `UNRESOLVED` | Zero; not invented |

For TUHO and Oborovo, typed construction-financing hard-CAPEX vectors and dates
are authoritative. Generic Solar/Wind have no separate construction-financing
result; their construction funding uses reconcile exactly to hard CAPEX and are
dated from typed financial close. This second source is accepted only when all
project uses are hard CAPEX and no financing, reserve, other, or non-construction
use is present. If neither bridge reconciles, Project XIRR fails closed with
`PROJECT_RETURN_HARD_CAPEX_TIMING_UNAVAILABLE`; no financial-close lump is made.

Any non-zero `other_explicit_project_uses_keur` fails closed as
`UNCLASSIFIED_OTHER_PROJECT_USE` until a typed economic classification exists.

## Source methodology audit

The TUHO and Oborovo workbook extracts contain project/unlevered cash-flow rows
and are evidence, not runtime input. Repository evidence records that some
workbook-labelled Project IRR tax rows absorb actual financing interest tax
shields. That presentation is classified
`SOURCE_WORKBOOK_PRESENTATION_ONLY` for the Finco canonical unlevered metric:
financing-only tax shields cannot make underlying project economics vary with
gearing or debt pricing. KUPI remains out-of-sample methodology evidence only.

The Finco authority therefore uses the existing jurisdiction tax policy, loss
ledger, and cash-tax timing on the already-computed canonical operating periods.
`FinancingInterestContext.UNLEVERED_ZERO_FINANCING_INTEREST` truthfully declares
that the empty interest vector is complete by definition; it does not promise a
later Senior/SHL injection. Tax depreciation is rebuilt only through the existing
canonical ProjectInputs adapter and depreciation leaf, using hard project CAPEX
without capitalized financing costs. Revenue, OPEX, EBITDA, Base tax, Bank tax,
Senior, SHL, and G2C are not rerun or mutated.

Correction A found one genuine prior-C1 bug: Oborovo Project tax had inherited
depreciation on capitalized financing costs. That created a small SHL-rate
dependency. Removing that financing tax shield changes Oborovo Project XIRR from
8.532304% to 8.512247%; the other three supported Project XIRRs are unchanged.

The tax result also exposes `terminal_unpaid_tax_keur`. A non-zero amount fails
closed as `TERMINAL_PROJECT_TAX_PAYMENT_OUTSIDE_MODEL_HORIZON` until a typed
settlement date exists; it is never silently omitted or placed on model end.

## B4 current-state inventory

Captured on starting main `def823200a856cb51eb247efe4871b541c5d6c3e` before
the C1 fields were introduced. The Legal Equity and Total Sponsor values below
are unchanged existing G2C authorities.

| Project | Legal Equity XIRR / MOIC | Total Sponsor XIRR / MOIC | Senior maturity / terminal | SHL mode, maturity / terminal | DA / Senior DSRA terminal | Deductible feedback |
|---|---|---|---|---|---|---|
| Solar | undefined / undefined; `UNPAID_SHL_AT_CONTRACTUAL_MATURITY` | undefined / undefined; same status | P31 2045-12-31 / 0, repaid | BULLET P29 2044-12-31 / 6,673.871124, unpaid | DA 0 released / cash DSRA N/A | inactive |
| Wind | undefined / undefined; `UNPAID_SHL_AT_CONTRACTUAL_MATURITY` | undefined / undefined; same status | P32 2046-06-30 / 0, repaid | BULLET P25 2042-12-31 / 8,247.083172, unpaid | DA 0 released / cash DSRA N/A | inactive |
| Oborovo | 20.761484% / 123.379805x | 10.720679% / 7.174297x | P28 2044-06-30 / 0, repaid | CASH_SWEEP P40 2050-06-30 / 0, repaid | DA 0 released / cash DSRA N/A | inactive |
| TUHO | 26.307473% / 303.381923x | 11.686506% / 7.954795x | P28 2043-12-31 / 0, repaid | CASH_SWEEP P36 2047-12-31 / 0, repaid | DA 0 released / cash DSRA N/A | inactive |

The typed `G2C_DEDUCTIBLE_SHL_COVENANT_FEEDBACK_NOT_YET_CLOSED` contract remains
available for unsupported edge cases, but none of the four promoted production
projects activates it.

## C1 project returns

| Project | Project XIRR | Status |
|---|---:|---|
| Generic Solar | 7.593168% | OK |
| Generic Wind | 11.366132% | OK |
| Oborovo | 8.512247% | OK |
| TUHO | 9.477998% | OK |

These are canonical Finco unlevered returns, not fitted workbook targets.

## Terminal-state semantics

`TerminalFinancialState` reports contractual maturity period/date, balance at
contractual maturity, and model-horizon balance separately. Senior status is
classified from the canonical schedule entry at the last Senior-axis period,
never from a later model-end value.

For SHL, the maturity audit exposes opening balance, PIK/current accrual,
contractual outstanding/due, actual principal paid, unpaid amount, maturity
balance, and horizon balance. The typed SHL contract requires zero residual at
contractual maturity for BULLET and CASH_SWEEP. An underfunded maturity therefore
reports `due = paid + unpaid` and `UNPAID_AT_CONTRACTUAL_MATURITY`; the audit does
not add a top-up, sweep unavailable cash, or invent post-maturity terms.

Unsupported reserves are not invented. Distribution Account and Senior DSRA use
typed released/remaining/stranded/not-applicable statuses only where their
runtime schedules are authoritative.

## Deferred metrics and statements

Project NPV, LLCR and PLCR remain deferred. Existing inputs were inventoried:
Senior contractual maturity and the project-life axis are authoritative, but no
generic project discount-rate/WACC authority is approved. No arbitrary rate is
introduced. Full P&L, Cash Flow Statement and Balance Sheet assembly remains out
of C1; this PR only serializes the return and terminal summary through existing
clean presentation paths.

## Governance

One clean G2C calculation remains the production authority. There is no legacy
fallback, project-name/code dispatch, source-vector replay, target fitting,
`approved_delta`, `expected_delta`, balancing plug, artificial terminal payment,
hidden post-engine mutation, or UI-side financial calculation. Source workbooks
remain validation evidence only. PR #938 is untouched.
