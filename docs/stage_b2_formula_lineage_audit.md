# Stage B2 formula-lineage audit (PR #906)

Date: 2026-07-23  
Branch: `claude/festive-cerf-uaq5hb`

## Direct Excel formula evidence incorporated

This audit records the direct workbook formula evidence supplied for the Oborovo Stage B2 Senior construction formulas. The implementation was corrected to follow formulas, not aggregate parity tuning.

## Senior IDC balance basis

Direct workbook formula example:

```excel
=($C57/100+I$59)*H$48*H$6*I$5
```

The IDC calculated in column `I` references `H48`, the immediately preceding spreadsheet debt-balance column. That referenced balance is the funded/closing balance of the preceding construction Uses period and is the balance on which the following accrual interval is calculated. In funding-period terms:

```text
FundingPeriod[t] closes debt balance[t]
FinancingAccrualInterval[t] uses closing balance[t]
CapitalizationPeriod[t+1] includes the accrued IDC Use
```

The runtime represents this explicitly as `FUNDING_PERIOD_CLOSING_DRAWN` plus `NEXT_FUNDING_PERIOD` capitalization. It is not target profile replay.

## Senior commitment-fee balance basis

Direct workbook formula example:

```excel
=$C58*(Inputs!$D$195-I48)*I$6*J$5
```

The commitment fee calculated in column `J` references `I48`, the immediately preceding spreadsheet debt-balance column. In funding-period terms, that is facility commitment less the funded/closing debt balance of the preceding construction Uses period, with the accrued commitment fee capitalized in the next funding period:

```text
FundingPeriod[t] closes debt balance[t]
FinancingAccrualInterval[t] uses facility - closing balance[t]
CapitalizationPeriod[t+1] includes the accrued commitment-fee Use
```

This resolves the earlier opening-vs-closing contradiction by naming the frame: prior spreadsheet column / following accrual interval / next funding Uses column.

## IDC / commitment profile-row semantics

Direct workbook profile formula examples:

```excel
=IF(SUM($D55;$D57)=0;0;SUM(I55;I57)/SUM($D55;$D57))
=IF(SUM($D56;$D58)=0;0;SUM(I56;I58)/SUM($D56;$D58))
```

These rows are derived from same-column period financing-cost calculations divided by their totals. They are validation/audit outputs, not independent payment-profile assumptions. The runtime therefore does not pass the derived IDC or commitment profile vectors as canonical inputs; it calculates period financing costs and applies the source-proven next-funding-period capitalization mapping.

## Period-rate formula lineage

Direct workbook evidence proves the period all-in base-rate chain:

```excel
All-in base rate[t] = $C59 + row60[t]
C59 = Inputs!$D$202 * Inputs!$D$230 + SUM(Inputs!$D$232:$D$234)/100
row60[t] = IF(Inputs!C$301>0; Inputs!C$301 * $C60; 0)
```

Source primitives:

| Primitive | Value | Runtime meaning |
| --- | ---: | --- |
| Base / swap rate | 3.00% | hedged fixed base-rate component |
| Hedge coverage | 80% | fixed-rate hedge share |
| Swap margin | 20 bps | added to hedged component |
| Forward swap margin | 0 bps | added to hedged component |
| CVA | 0 bps | added to hedged component |
| External curve buffer | 20% | uplift on unhedged floating share |
| Senior margin | 265 bps | added after all-in base rate |

The generic derivation is:

```text
hedged_component = base_rate * hedge_coverage + swap_margin + forward_swap_margin + cva
floating_weight = (1 - hedge_coverage) * (1 + external_curve_buffer)
row60[t] = euribor_1m_fixing[t] * floating_weight
period_all_in_base[t] = hedged_component + row60[t]
senior_idc_rate[t] = period_all_in_base[t] + senior_margin
```

The Oborovo source config now passes primitive rate inputs and the source Euribor 1m fixing curve. The literal effective Senior IDC rate vector remains validation evidence only and is not a runtime input.

## Anti-calibration status

| Item | Runtime calculation input? | Classification |
| --- | ---: | --- |
| Source monthly Senior IDC values | No | VALIDATION_ONLY |
| Source monthly commitment-fee values | No | VALIDATION_ONLY |
| Source cumulative Senior vector | No | VALIDATION_ONLY |
| Source VAT requirement vector | No | VALIDATION_ONLY |
| Derived IDC profile vector | No | VALIDATION_ONLY |
| Derived commitment profile vector | No | VALIDATION_ONLY |
| Literal effective Senior IDC rate vector | No | VALIDATION_ONLY |
| Euribor 1m fixing curve | Yes | SOURCE_DERIVED_RATE_FIXTURE |
| Approved delta / balancing plug / forced final draw | No | ABSENT |
| Project identity dispatch | No | ABSENT |

## Current formula-based parity snapshot

After implementing the funding-period → accrual-interval → next-capitalization-period mapping, Senior period parity returns without profile replay or literal effective-rate inputs.

| Metric | Python formula result | Source validation view | Status |
| --- | ---: | ---: | --- |
| P1 Senior draw | 1,384.663018150 | 1,384.663018410 | MATCH |
| Senior construction closing draw | 42,852.266725757 | 42,852.266726028 | MATCH / source rounding |
| Senior IDC total | 1,086.017354542 | 1,086.017354555 allocated | MATCH / source rounding |
| Senior commitment-fee total | 188.565507949 | 188.565507947 allocated | MATCH / source rounding |
| VAT terminal requirement | 0.000000000 | 0.000000000 | FROZEN_PASS |
| VAT IDC | 208.447618455 | 208.447618000 | FROZEN_PASS |
| VAT commitment fee | 13.621952811 | 13.621953000 | FROZEN_PASS |

P1 Uses exclude Senior IDC and Senior commitment fee. The first Senior financing costs are accrued after P1 Senior funding closes and are capitalized into P2 Uses.

## Stage B1 hard-CAPEX precision

The actual Oborovo factory previously carried the truncated amount `55,997.7` kEUR. The source-proven row precision correction is:

| Row | Previous factory | Exact source | Delta |
| --- | ---: | ---: | ---: |
| Construction Management | 1,151.0000 | 1,151.1340 | 0.1340 |
| Contingencies | 1,986.0000 | 1,986.4400 | 0.4400 |
| Project Acquisition / Development | 18.0000 | 18.3270 | 0.3270 |
| Project Rights | 8,524.0000 | 8,524.4845 | 0.4845 |
| **Total** | | | **1.3855** |

The factory now carries exact source row precision and no balancing plug.

## Verdict

`READY_FOR_FINAL_INDEPENDENT_REVIEW` locally for the Stage B2 formula-lineage questions, subject to the separate TAX_CFADS stale-record governance failure and remote push/PR visibility constraints.
