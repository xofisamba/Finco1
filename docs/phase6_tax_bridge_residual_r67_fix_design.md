# Phase 6 Tax Bridge Residual R67 Fix Design

## Executive Summary

The current TUHO tax bridge has closed most of the R67 gap:

| Measure | Total kEUR |
| --- | ---: |
| Excel R67 target | -38,240.9 |
| Legacy runtime cash tax | -20,140.2 |
| TUHO flag-on with R34 + rolling losses | -36,091.6 |
| Remaining residual | +2,149.3 |

The residual is not a simple H1/H2 cash-tax timing issue and not a scalar plug.
It changes sign by period cluster:

| Period band | Delta kEUR | Meaning |
| --- | ---: | --- |
| op_idx 24-37 | -2,181.6 | Python overpays tax versus Excel. |
| op_idx 38-56 | +3,381.7 | Python underpays tax versus Excel. |
| op_idx 57-59 | +949.2 | Late-horizon underpayment persists. |

Recommendation: **B. Fix opening loss aging plus minor tax-basis rows before
R99/R102 runtime source promotion.**

R99 is not ready for runtime-source acceptance yet because 18 periods still have
absolute R67 deltas above 100 kEUR and the sign-flipping clusters would flow
straight into SHL and distribution timing.

## 1. Construction-Period Tax-Loss Aging

The current rolling loss engine treats TUHO opening tax losses as a single COD
bucket available for a full 5-year operating window. Excel appears more likely
to age losses from their original construction-period generation dates because
early taxable periods show Python overpayment followed by mid/late underpayment.

Current known facts:

- Python opening loss at first operating period: 25,000.0 kEUR.
- Python rolling bucket starts at COD and expires after 10 semiannual operating
  periods.
- Excel R67 remains lower than Python in early taxable periods, then higher in
  later periods.
- That pattern is consistent with different loss-bucket age and taxable-basis
  timing, not a pure payment-date mismatch.

The branch should not assume exact construction loss ages until Excel loss rows
are extracted for construction periods. The safest design is to support explicit
opening buckets first.

| Loss bucket | Excel generation period | Python generation period | Excel expiry | Python expiry | Estimated R67 impact |
| --- | --- | --- | --- | --- | ---: |
| Opening construction losses | Pre-COD construction P&L periods, exact split not yet extracted | Single bucket at COD / op_idx 0 | Likely earlier than Python for at least part of the loss pool | op_idx 9 under current full 5-year operating assumption | Primary driver of op_idx 24-37 overpayment and op_idx 38-59 underpayment pattern |
| Current operating losses | Period generated | Period generated | 5 years after generation | 5 years after generation | Lower risk; current engine behavior is auditable |
| Residual tax-basis differences | Not a loss bucket | Not a loss bucket | n/a | n/a | Explains remaining mid/late sign changes after bucket aging |

### Investigation Questions

Before implementation, extract from Excel:

- construction-period taxable losses by period
- loss generation date / column
- row equivalent of Losses N-1, Allocated losses, Losses N before COD
- whether Excel uses years or semiannual periods for expiry
- whether construction-period losses are consolidated into a single opening
  balance or retained by vintage

## 2. Opening Bucket Reconstruction Strategy

| Option | Description | Complexity | Auditability | Runtime safety | Expected parity improvement | Scalability |
| --- | --- | --- | --- | --- | --- | --- |
| A. Explicit opening bucket age fixture | Add a TUHO test/runtime-flag fixture of opening loss buckets by amount and remaining life | Low to medium | High if sourced from Excel rows | High, default-off and TUHO-only | High for timing residual if Excel buckets are extracted | Medium |
| B. Reconstruct historical pre-COD periods | Run construction-period tax bridge before COD and generate buckets naturally | High | High, but more moving parts | Medium; broader formula surface | Highest long-term | High |
| C. Approximate weighted average age | Convert the 25,000 kEUR opening loss into one weighted remaining-life bucket | Low | Medium-low; approximation requires policy | Medium | Medium, may reduce cumulative residual but can distort periods | Low |
| D. Document as accepted limitation | Keep current COD bucket assumption | Very low | High because no hidden behavior | High | None | Medium |

Recommended implementation sequence:

1. Implement Option A first as a default-off TUHO fixture-backed calibration.
2. Use the fixture to prove whether opening bucket age reduces material period
   count and cumulative residual.
3. Only then consider Option B for a fully formula-owned construction-period tax
   bridge.

Avoid Option C unless Excel data cannot be extracted. It is too easy to overfit
the cumulative R67 total while hiding period-level sign changes.

## 3. Remaining Tax-Basis Rows

The residual is unlikely to be solved by loss age alone. The current bridge does
not formally own all Excel tax-basis and cash-tax contributors.

| Excel row / component | Current owner | Missing owner | Estimated impact | Recommended module |
| --- | --- | --- | ---: | --- |
| CF R63 local tax | PF cash waterfall audit placeholder / not tax-owned | local tax policy and cash-flow ownership | Small to medium | `domain/financial_statements/pf_cash_waterfall.py` then tax bridge config |
| CF R66 reserve interest / cash interest on reserves | distribution-account audit placeholder | reserve-interest calculation and tax/cash classification | Small, prior diagnostics around 55 kEUR total | reserve / PF cash waterfall bridge |
| CF R67 corporate tax | tax bridge runtime flag | remaining tax-basis rows and opening loss bucket ages | 2,149.3 kEUR residual | tax bridge + loss carryforward |
| P&L WHT / minor tax rows | not formally mapped into tax bridge | row ownership and sign convention | Unknown, likely small but can affect clusters | tax bridge diagnostics |
| VAT facility financing effects | not in current tax bridge | VAT facility / financing module | Unknown | future VAT facility workstream |
| Book/tax timing adjustments | partial through depreciation and R34 | explicit bridge between book depreciation, tax depreciation, and taxable basis | Medium | depreciation ledger + tax bridge |
| Construction-period opening losses | single runtime opening loss bucket | vintage-level opening buckets | High for timing | loss carryforward fixture/config |

## 4. Residual Materiality Policy

Before accepting R99/R102 as runtime source, require all gates below:

| Gate | Proposed threshold | Current status |
| --- | ---: | --- |
| Cumulative R67 delta | within +/-1.0% of Excel R67, about +/-382 kEUR | Fail: +2,149.3 kEUR / 5.6% |
| Material period count | no more than 5 periods above 100 kEUR absolute delta | Fail: 18 periods |
| Single-period materiality | no unexplained period above 250 kEUR absolute delta | Fail: several periods exceed this |
| Sign-flipping clusters | no unresolved cluster switching from overpayment to underpayment | Fail: early overpayment, mid/late underpayment |
| R99 downstream impact | measured but not accepted until R67 gates pass | Pass as audit-only, fail for runtime source |

These gates should apply before:

- R99 runtime-source acceptance
- SHL runtime consumption
- sponsor distribution reliance
- TUHO factory opt-in

## 5. Recommended Final Calibration Strategy

Recommendation: **B. Fix opening loss aging + minor tax rows.**

Rationale:

- Opening loss aging is the most likely structural driver of the sign-changing
  residual.
- Minor tax / reserve-interest rows are small individually, but R99 is sensitive
  to period-level cash timing.
- Accepting the residual now would make the R99 source appear calibrated on a
  cumulative basis while still moving SHL and dividend timing in material
  periods.
- A deeper tax-basis rewrite is not warranted before the narrower opening-bucket
  and minor-row tests are exhausted.

Rejected strategies:

- **A only:** may reduce the largest timing issue but does not account for known
  unmapped rows.
- **C accept residual:** current residual fails the proposed cumulative and
  material-period gates.
- **D block for full tax-basis parity:** too broad for the next branch; the next
  safe step is targeted calibration, not a full tax-engine rewrite.

## 6. Proposed Final Calibration Branch

Branch:

`phase6-tax-bridge-residual-r67-final-calibration`

Allowed scope:

- Add optional TUHO tax bridge opening loss bucket fixture/config behind
  `use_tax_bridge_engine=True`.
- Add diagnostics for local tax, WHT, reserve-interest rows if values are
  available from existing fixtures.
- Add tests comparing R67 period bridge before and after calibration.
- Keep R99/R102 audit-only.
- Keep factories flag-off.

Forbidden scope:

- no R99/R102 runtime source acceptance
- no SHL FCF opt-in
- no factory opt-in
- no revenue/OPEX/senior/SHL/construction formula changes
- no broad depreciation rewrite
- no UI/cache/persistence changes

Expected target after calibration:

- cumulative R67 residual below +/-500 kEUR
- fewer than 8 periods above 100 kEUR absolute delta
- no unexplained period above 300 kEUR
- clear explanation for any remaining sign-flip clusters

If those targets fail, R99 runtime-source work should remain blocked.

## 7. R99 Readiness Assessment

Current answer:

**NO, requires final calibration first.**

Quantitative basis:

- cumulative residual: +2,149.3 kEUR, about 5.6% of Excel R67
- 18 material periods above 100 kEUR absolute delta
- residual changes sign by cluster
- R99/R102 would inherit the tax timing error directly

The model is close enough to design the R99 source path, but not close enough to
accept R99/R102 as runtime source or feed SHL FCF from runtime values.

## 8. Updated Roadmap

Completed:

- interest limitation engine
- full-horizon interest limitation fixtures
- rolling 5-year FIFO loss engine
- tax bridge consumes interest limitation
- tax bridge consumes rolling losses
- residual R67 diagnostic

Remaining:

1. `phase6-tax-bridge-residual-r67-final-calibration`
2. `phase6-r99-runtime-source-from-tax-bridge`
3. TUHO factory opt-in only after R99 and SHL gates pass
4. depreciation/book balance-sheet workstreams
5. VAT facility workstreams
6. Oborovo diagnostic parity path

## Scope Confirmation

This design branch is docs-only. It does not change runtime formulas, tax
calculations, loss engine behavior, depreciation behavior, R99/R102 source
status, SHL FCF status, project factories, UI, cache, or persistence.
