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

The IDC calculated in column `I` references `H48`, the immediately preceding Senior Debt balance column. Economically, that is prior-period closing drawn balance, i.e. current-period opening drawn balance. Therefore the source-proven runtime policy is:

```text
Senior_IDC[t] = opening_drawn[t] * senior_idc_rate[t] * day_fraction[t] * active_flag[t]
```

The prior local `CURRENT_CLOSING_DRAWN` Oborovo setting was formula-inconsistent and has been removed from the Oborovo source config.

## Senior commitment-fee balance basis

Direct workbook formula example:

```excel
=$C58*(Inputs!$D$195-I48)*I$6*J$5
```

The commitment fee calculated in column `J` references `I48`, the immediately preceding Senior Debt balance column. Economically, the undrawn balance is facility commitment less current-period opening drawn balance. Therefore the source-proven runtime policy is:

```text
Senior_Commitment_Fee[t] = opening_undrawn[t] * commitment_fee_rate * day_fraction[t] * active_flag[t]
```

The prior local `CURRENT_CLOSING_UNDRAWN` Oborovo setting was formula-inconsistent and has been removed from the Oborovo source config.

## IDC / commitment profile-row semantics

Direct workbook profile formula examples:

```excel
=IF(SUM($D55;$D57)=0;0;SUM(I55;I57)/SUM($D55;$D57))
=IF(SUM($D56;$D58)=0;0;SUM(I56;I58)/SUM($D56;$D58))
```

These rows are derived from same-column period financing-cost calculations divided by their totals. They are validation/audit outputs, not independent payment-profile assumptions. The runtime therefore does not pass the derived IDC or commitment profile vectors as canonical inputs. Senior IDC and Senior commitment fees are capitalized as same-period financing-cost Uses.

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

After reverting to source-proven opening balances and same-period financing-cost capitalization, Senior period parity no longer matches the prior target-fitting snapshot. That is expected and is not corrected by reverting to closing-basis formulas.

| Metric | Python formula result | Source validation view | Status |
| --- | ---: | ---: | --- |
| Senior construction closing draw | 42,699.515819945 | 42,852.266726028 | formula residual remains |
| Senior IDC total | 900.175830222 | 1,086.017354555 allocated | formula residual remains |
| Senior commitment-fee total | 221.656126458 | 188.565507947 allocated | formula residual remains |
| VAT terminal requirement | 0.000000000 | 0.000000000 | FROZEN_PASS |
| VAT IDC | 208.447618455 | 208.447618000 | FROZEN_PASS |
| VAT commitment fee | 13.621952811 | 13.621953000 | FROZEN_PASS |

First remaining Senior mismatch is P1: opening-basis commitment fee is `2.499716261` kEUR, so Python P1 Senior draw is `1,387.162734411` kEUR versus source cumulative Senior P1 `1,384.663018410` kEUR. Further investigation must focus on source formula column alignment / facility basis / sizing residual, not on reintroducing closing-basis or profile replay.

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

`STILL_BLOCKED` for final independent review because source-formula implementation is now corrected, but Senior aggregate/period parity no longer closes. The remaining mismatch must be resolved from formula lineage (column alignment, sizing scalar, and source circular residual), not by target-derived effective-rate/profile/balance-basis replay.
