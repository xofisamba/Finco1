# Stage B2 formula-lineage audit (PR #906)

Date: 2026-07-23
Branch: `claude/festive-cerf-uaq5hb`
Local head audited before this note: `228b6577629364bd5408d229d3e237e1bbf5a47f`

## Scope and non-goals

This note records the final formula-lineage audit requested after numerical Oborovo Stage B2 parity had already converged.  It intentionally does **not** tune parity, normalize workbook residuals, force the final Senior draw, add balancing plugs, alter TAX_CFADS correction records, or merge PR #906.

## Authoritative workbook availability

The audit requires the formula-preserving workbook `20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm` opened with `data_only=False`.  The workbook file is not present in the local workspace or `/root` filesystem, so raw XLSM formula extraction is blocked in this environment.

Commands run:

```bash
find /workspace /root -iname '*.xlsm' 2>/dev/null | head -50
rg -n "H57|H58|G48|OBOROVO_SENIOR_INTEREST_RATE_SCHEDULE|0\\.0596904|5\\.96904|CURRENT_CLOSING|OPENING_DRAWN" finco_core domain tests docs
```

The repository does contain prior programmatic source-inventory artifacts.  Those artifacts show that `Inputs!39` (IDCs) and `Inputs!40` (Commitment Fees) are formula rows with dependencies on `Macro, IDC`, so those rows are derived/read-only workbook formulas rather than manual primary assumptions.  They do **not** provide the raw formula text for the IDC-sheet cells needed to resolve the balance-basis conflict.

## Balance-basis conflict remains formula-blocked

The existing runtime contract says the source formula is `H57 = ($C57%/100 + H$59) × G$48 × G$6 × H$5` and interprets `G48` as the prior-period/opening Senior Debt drawn balance.  The same contract says `H58 = $C58 × (Inputs!$D$195 - G48) × G$6 × H$5` and interprets `G48` as opening drawn for commitment-fee purposes.

The current Oborovo source config uses `CURRENT_CLOSING_DRAWN` and `CURRENT_CLOSING_UNDRAWN` because that is the latest numerically reconciled implementation.  Without the formula-preserving workbook, the economic meaning of `G48` relative to the relevant interest-period column cannot be proven from formulas in this environment.  Therefore this audit does **not** overwrite the older contract and does **not** claim the latest closing-basis implementation is formula-proven.

Required next evidence before final independent review acceptance:

| Interest period | Cell(s) needed | Required raw formula proof | Status |
| --- | --- | --- | --- |
| P1 Senior IDC | IDC-sheet P1 IDC cell, prior/current Senior balance cell | Whether the referenced balance is opening or current/closing relative to P1 | BLOCKED: XLSM absent |
| P2 Senior IDC | IDC-sheet P2 IDC cell, referenced Senior balance cell | Whether the referenced balance is opening or current/closing relative to P2 | BLOCKED: XLSM absent |
| P3 Senior IDC | IDC-sheet P3 IDC cell, referenced Senior balance cell | Whether the referenced balance is opening or current/closing relative to P3 | BLOCKED: XLSM absent |
| P1 commitment fee | IDC-sheet P1 commitment-fee cell, referenced Senior balance cell | Whether undrawn basis is opening or current/closing relative to P1 | BLOCKED: XLSM absent |
| P2 commitment fee | IDC-sheet P2 commitment-fee cell, referenced Senior balance cell | Whether undrawn basis is opening or current/closing relative to P2 | BLOCKED: XLSM absent |
| P3 commitment fee | IDC-sheet P3 commitment-fee cell, referenced Senior balance cell | Whether undrawn basis is opening or current/closing relative to P3 | BLOCKED: XLSM absent |

## Senior period-rate lineage

`OBOROVO_SENIOR_INTEREST_RATE_SCHEDULE` appears in `domain/construction/source_parity.py` and is passed into `ConstructionRuntimeConfig`.  The values currently act as a source-parity rate schedule, but this audit could not prove their primitive formula lineage from margin, swap rate, swap margin, hedge coverage, external floating-rate buffer, and Euribor 1m curve because the formula-preserving XLSM is unavailable.

Until the workbook formulas are extracted, classify this vector as `SOURCE_DERIVED_FIXTURE_PENDING_FORMULA_LINEAGE`, not as a proven primitive source input.  It must not be promoted as a production calibration constant outside the source-parity config.

Required next evidence:

| Periods | Primitive source assumptions | Intermediate formula proof | Status |
| --- | --- | --- | --- |
| P1-P11 Senior IDC rate schedule | margin, swap rate, swap margin, forward swap margin, CVA, hedge coverage, floating buffer, Euribor 1m curve | Raw formulas from workbook rate rows to final all-in construction rate | BLOCKED: XLSM absent |

## Financing-cost capitalization profile lineage

The repository source inventory classifies `Inputs!39` (IDCs) and `Inputs!40` (Commitment Fees) as formula rows, derived/read-only, with dependencies on `Macro, IDC`.  That supports the reviewer warning that these spending/profile rows are derived from the IDC sheet and should not be treated as manual primary runtime inputs.  The canonical runtime should continue deriving period financing costs and applying a generic capitalization-timing policy; the formula text still needs workbook extraction to prove the exact lineage.

Current generic capitalization policy in the Oborovo config remains `NEXT_PERIOD` for Senior IDC and Senior commitment fee.  This matches the observed source pattern that calculated period-t financing costs are funded/capitalized in period t+1, but raw workbook formula extraction is still required for final formula-lineage closure.

## Anti-calibration status

The runtime config exposes one `source_total_uses_validation_keur` field for validation/diagnostic comparison.  The config does not contain monthly source IDC amounts, monthly source commitment-fee amounts, source cumulative Senior vector, source VAT requirement vector, or final GFA target as runtime calculation inputs.

Current anti-calibration classification:

| Item | Runtime calculation input? | Classification |
| --- | ---: | --- |
| Source monthly Senior IDC values | No | VALIDATION_ONLY |
| Source monthly commitment-fee values | No | VALIDATION_ONLY |
| Source cumulative Senior vector | No | VALIDATION_ONLY |
| Source VAT requirement vector | No | VALIDATION_ONLY |
| Final displayed GFA target | No | VALIDATION_ONLY |
| Senior period-rate vector | Yes, in source-parity config | SOURCE_DERIVED_FIXTURE_PENDING_FORMULA_LINEAGE |
| Approved delta / balancing plug / forced final draw | No | ABSENT |
| Project identity dispatch | No | ABSENT |

## Current parity snapshot preserved without further tuning

Using `config = oborovo_source_config()` and `result = run_stage_b2(config)` on the current branch:

| Metric | Python | Source view | Delta / residual |
| --- | ---: | ---: | ---: |
| Construction closing Senior draw | 42,852.266725757 | 42,852.266726028 | -0.000000271 |
| Displayed Senior facility | 42,852.278762563 | 42,852.278762563 | 0.000000000 |
| Senior facility minus construction closing | 0.012036806 | 0.012036535 | ~0.000000271 |
| Senior IDC allocated/capitalized total | 1,086.017354542 | 1,086.017354555 | -0.000000013 |
| Senior commitment-fee allocated/capitalized total | 188.565507949 | 188.565507947 | 0.000000002 |
| Max cumulative Senior delta | 0.000000730 | n/a | n/a |
| VAT terminal requirement | 0.000000000 | 0.000000000 | 0.000000000 |
| VAT IDC | 208.447618455 | 208.447618000 | 0.000000455 |
| VAT commitment fee | 13.621952811 | 13.621953000 | -0.000000189 |

The residual between displayed GFA / Total Uses and the construction Sources view remains classified as `SOURCE_CIRCULAR_RESIDUAL`; it is not normalized away.

## Stage B1 hard-CAPEX audit on actual code

Instantiating the actual Oborovo factory on this branch gives `hard_capex_keur = 55,997.7` and `total_capex = 57,971.668`.  Comparing factory item amounts to the authoritative Stage B2 source rows identifies the exact 1.3855 kEUR difference as decimal truncation across four rows:

| Row | Factory amount | Authoritative source amount | Delta |
| --- | ---: | ---: | ---: |
| Construction Management | 1,151.0000 | 1,151.1340 | -0.1340 |
| Contingencies | 1,986.0000 | 1,986.4400 | -0.4400 |
| Project Acquisition / Development | 18.0000 | 18.3270 | -0.3270 |
| Project Rights | 8,524.0000 | 8,524.4845 | -0.4845 |
| **Total** | | | **-1.3855** |

Conclusion: the old 55,997.7 kEUR figure is an actual factory precision defect candidate, not merely stale narrative on this branch.  This audit does not change Stage B1 economics because the requested Stage B2 formula-lineage proof is blocked pending workbook availability; any Stage B1 correction should be a separate source-proven precision fix with tests and no balancing plug.

## Generic coverage migration matrix

The old Stage B2 generic suite remains the coverage baseline.  The current branch has focused runtime/parity tests, but full migration is not complete in this pass.

| Old contract | Current status |
| --- | --- |
| MarginSchedule / fixed / floating pricing | PRESERVED in legacy file at remote head; not migrated into new focused runtime tests |
| Hedged blend / hedge coverage / hedge maturity | PRESERVED in legacy file at remote head; not migrated into new focused runtime tests |
| External curve buffer / margin steps / swap adjustments | PRESERVED in legacy file at remote head; not migrated into new focused runtime tests |
| Construction vs operational rates / Senior IDC derived-rate behavior | PARTIAL: source-parity rate schedule covered; formula lineage blocked |
| VAT facility pricing / runoff | MIGRATED in focused Stage B2 tests |
| SHL construction / governance constraints | PARTIAL: anti-calibration and no-plug guards covered; TAX_CFADS untouched |
| InterestRatePeriodState / FacilityPeriodState | PARTIAL: `FacilityPeriodState` exercised by VAT schedule tests |
| Construction solver / non-convergence failure | MIGRATED in runtime tests |
| Oborovo rate parity | PARTIAL: numerical parity covered; rate formula lineage blocked |
| CAPEX / funding / VAT / convergence runtime coverage | MIGRATED in focused runtime and source-parity tests |

Final coverage conclusion: meaningful generic coverage restoration is still incomplete because the prior broad rate/pricing contract suite has not been fully migrated into the new focused Stage B2 runtime tests.

## Final verdict of this audit

`STILL_BLOCKED` for final independent review until the formula-preserving Oborovo XLSM is available and the following raw formulas are extracted:

1. IDC-sheet Senior IDC formulas for P1-P3, including referenced balance cells and row labels.
2. IDC-sheet Senior commitment-fee formulas for P1-P3, including referenced balance cells and row labels.
3. Workbook rate-row formulas from primitive rate assumptions to P1-P11 all-in construction rates.
4. Inputs-sheet IDC and commitment-fee profile cell formulas proving formula-derived next-period capitalization lineage.

No PR merge should occur before those source-formula questions are resolved.
