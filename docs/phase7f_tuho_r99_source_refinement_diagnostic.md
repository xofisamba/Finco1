# Phase 7F TUHO R99 Source Refinement Diagnostic

## Purpose

This is a diagnostic-only C1b measurement. It tests alternative cash-tax sources for the TUHO R69/R99 helper to see whether any existing Python field can reproduce Excel R99/R102 closely enough for a future runtime opt-in.

No runtime behavior is changed. `use_tuho_r99_input_engine` remains disabled, SHL `fcf_waterfall` is not implemented, tax/revenue/OPEX engines are unchanged, and Oborovo behavior is untouched.

## Sources

- Excel fixture: `tests/fixtures/excel_tuho_full_model_extract.json`
- Excel R69 target total: **300,926.8 kEUR**
- Excel R99/R102 target total: **234,745.0 kEUR**
- Selected Excel R99/R102 periods: op_idx **0, 10, 20, 24, 28, 34, 36**
- Python model: current PR B1 TUHO run
- Helper: C1a `compute_tuho_r99_input_period`

## Variants Tested

| Variant | Cash-tax source |
|---|---|
| A | `max(0, ebitda_keur - cf_after_tax_keur)` |
| B | `max(0, period.tax_keur)` |
| C | `max(0, period.tax_keur)` only when `period_in_year == 2`, otherwise 0 |
| D | Annual H1+H2 `period.tax_keur` deducted in H2 only |
| E | `max(0, taxable_profit_keur * tax_rate)` |

Variant E is the only loss/taxable-income candidate exposed by existing Python fields. The current runtime does not expose a full tax-loss carryforward ledger suitable for an Excel-like payable timing candidate without changing the tax engine, which is out of scope for this diagnostic.

## Summary Table

| variant | R69 total | R69 delta | R99 total | R99 delta | selected MAE | PIK phase delta | sweep phase delta | post-SHL delta | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A current C1a | 315,190.5 | +14,263.7 | 249,545.4 | +14,800.4 | 338.7 | +2,999.5 | +274.4 | +10,722.5 | Fails total high; best tied selected MAE but op_idx 24 fails badly. |
| B full period tax | 296,039.0 | -4,887.8 | 230,393.9 | -4,351.1 | 714.2 | +1,793.2 | -3,490.4 | -1,460.6 | Total is closer than A but still outside +/-1%; selected periods worsen. |
| C H2-only tax | 315,190.5 | +14,263.7 | 249,545.4 | +14,800.4 | 338.7 | +2,999.5 | +274.4 | +10,722.5 | Same as A in this run because tax is already concentrated in H2 for relevant periods. |
| D annual paired H2 tax | 296,039.0 | -4,887.8 | 230,393.9 | -4,351.1 | 338.7 | +2,229.5 | -3,926.7 | -2,468.7 | Total matches B, selected MAE ties A, but phase timing is worse. |
| E taxable profit * tax rate | 298,187.4 | -2,739.4 | 232,542.3 | -2,202.7 | 625.6 | +2,256.5 | -1,824.5 | -1,460.6 | Best total, within +/-1%, but selected periods fail. |

Acceptance test:

- Total R99 within +/-1% of 234,745.0 means approximately **232,397.6 to 237,092.5 kEUR**.
- Selected periods must be within +/-100 kEUR each.

Only Variant E passes the total band. No variant passes selected-period tolerance.

## Selected Period Detail

| variant | op_idx | date | Excel R99 | Python R99 | delta | Python R69 |
|---|---:|---|---:|---:|---:|---:|
| A | 0 | 2030-06-30 | 953.8 | 1,107.8 | +153.9 | 3,053.2 |
| A | 10 | 2035-06-30 | 1,010.1 | 1,235.5 | +225.4 | 3,405.3 |
| A | 20 | 2040-06-30 | 1,121.0 | 1,371.9 | +250.9 | 3,781.2 |
| A | 24 | 2042-06-30 | 3,233.6 | 1,800.7 | -1,432.9 | 3,925.9 |
| A | 28 | 2044-06-30 | 6,191.8 | 6,414.6 | +222.7 | 6,414.6 |
| A | 34 | 2047-06-30 | 6,585.9 | 6,663.5 | +77.6 | 6,663.5 |
| A | 36 | 2048-06-30 | 6,765.1 | 6,772.8 | +7.7 | 6,772.8 |
| B | 0 | 2030-06-30 | 953.8 | 1,107.8 | +153.9 | 3,053.2 |
| B | 10 | 2035-06-30 | 1,010.1 | 1,235.5 | +225.4 | 3,405.3 |
| B | 20 | 2040-06-30 | 1,121.0 | 1,002.9 | -118.0 | 3,412.3 |
| B | 24 | 2042-06-30 | 3,233.6 | 1,364.4 | -1,869.3 | 3,489.5 |
| B | 28 | 2044-06-30 | 6,191.8 | 5,470.9 | -721.0 | 5,470.9 |
| B | 34 | 2047-06-30 | 6,585.9 | 5,674.4 | -911.5 | 5,674.4 |
| B | 36 | 2048-06-30 | 6,765.1 | 5,764.6 | -1,000.5 | 5,764.6 |
| C | 0 | 2030-06-30 | 953.8 | 1,107.8 | +153.9 | 3,053.2 |
| C | 10 | 2035-06-30 | 1,010.1 | 1,235.5 | +225.4 | 3,405.3 |
| C | 20 | 2040-06-30 | 1,121.0 | 1,371.9 | +250.9 | 3,781.2 |
| C | 24 | 2042-06-30 | 3,233.6 | 1,800.7 | -1,432.9 | 3,925.9 |
| C | 28 | 2044-06-30 | 6,191.8 | 6,414.6 | +222.7 | 6,414.6 |
| C | 34 | 2047-06-30 | 6,585.9 | 6,663.5 | +77.6 | 6,663.5 |
| C | 36 | 2048-06-30 | 6,765.1 | 6,772.8 | +7.7 | 6,772.8 |
| D | 0 | 2030-06-30 | 953.8 | 1,107.8 | +153.9 | 3,053.2 |
| D | 10 | 2035-06-30 | 1,010.1 | 1,235.5 | +225.4 | 3,405.3 |
| D | 20 | 2040-06-30 | 1,121.0 | 1,371.9 | +250.9 | 3,781.2 |
| D | 24 | 2042-06-30 | 3,233.6 | 1,800.7 | -1,432.9 | 3,925.9 |
| D | 28 | 2044-06-30 | 6,191.8 | 6,414.6 | +222.7 | 6,414.6 |
| D | 34 | 2047-06-30 | 6,585.9 | 6,663.5 | +77.6 | 6,663.5 |
| D | 36 | 2048-06-30 | 6,765.1 | 6,772.8 | +7.7 | 6,772.8 |
| E | 0 | 2030-06-30 | 953.8 | 991.7 | +37.9 | 2,937.2 |
| E | 10 | 2035-06-30 | 1,010.1 | 1,232.2 | +222.1 | 3,402.0 |
| E | 20 | 2040-06-30 | 1,121.0 | 1,249.0 | +128.0 | 3,658.3 |
| E | 24 | 2042-06-30 | 3,233.6 | 1,615.2 | -1,618.4 | 3,740.4 |
| E | 28 | 2044-06-30 | 6,191.8 | 5,711.8 | -480.1 | 5,711.8 |
| E | 34 | 2047-06-30 | 6,585.9 | 5,693.6 | -892.4 | 5,693.6 |
| E | 36 | 2048-06-30 | 6,765.1 | 5,764.6 | -1,000.5 | 5,764.6 |

## Field Totals

| Field | Total |
|---|---:|
| Excel R67 absolute corporate tax | 38,240.9 |
| Python `max(0, ebitda - cf_after_tax)` | 19,936.6 |
| Python `period.tax_keur` | 39,088.1 |
| Python `taxable_profit_keur * tax_rate` | 36,939.7 |

`period.tax_keur` is closest to Excel R67 in total, but using it directly pushes selected merchant/post-SHL periods too low. `taxable_profit_keur * tax_rate` is closest on total R99, but also fails selected-period timing.

## Answers

1. **Which tax source variant best matches Excel R99 total?**  
   Variant E, `taxable_profit_keur * tax_rate`, is best on total: **232,542.3 kEUR**, or **-2,202.7 kEUR** versus Excel. It is within +/-1% of the Excel R99/R102 total.

2. **Which variant best matches selected periods?**  
   Variants A, C, and D tie on selected MAE at **338.7 kEUR**, but all fail because op_idx 24 is **-1,432.9 kEUR** versus Excel. Variant E improves op_idx 0 but worsens later selected periods.

3. **Does any variant satisfy total R99 within +/-1% and selected periods within +/-100 kEUR?**  
   No. Variant E passes total only. No variant passes selected-period tolerance.

4. **If no variant passes, which component remains dominant?**  
   For total R99, the dominant component remains R69 tax source/timing. For selected-period failure, the dominant issue is not tax alone: op_idx 24 is still dominated by the known PPA-to-merchant boundary and senior DS transition mismatch.

5. **Is the remaining error tax timing, revenue/PPA timing, senior DS timing, or missing R98/R100 carry-forward?**  
   It is mixed:

   - Full-horizon total is mainly tax timing/source.
   - op_idx 24 is mainly revenue/PPA timing plus senior DS transition timing.
   - Sweep and post-SHL errors indicate tax timing and H1/H2 merchant period mapping remain important.
   - The fixture does not expose R98/R100 independently, so missing carry-forward cannot be ruled out, but no tested variant shows evidence that carry-forward alone would solve the selected-period errors.

6. **Is C1b runtime opt-in still blocked?**  
   Yes. No variant meets both acceptance criteria, so `use_tuho_r99_input_engine` must remain disabled.

7. **What is the smallest safe implementation after this diagnostic?**  
   The next safe implementation is not R99 runtime opt-in. The smallest safe next PR is a diagnostic/measurement enhancement that exposes a clean cash-tax payable field and traces revenue/PPA boundary timing at op_idx 24, without changing runtime outputs. Once revenue/PPA timing and tax payable timing are measured separately, a small TUHO-only R99 helper can be retried under a disabled flag.

## Recommendation

- Do not tune constants or introduce scaling factors.
- Do not enable C1b runtime R99 input.
- Do not restart B2 SHL `fcf_waterfall`.
- Next diagnostic should split op_idx 24 into revenue boundary, senior DS, and tax payable timing components.
