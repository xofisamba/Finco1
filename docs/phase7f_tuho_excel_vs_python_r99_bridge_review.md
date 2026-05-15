# Phase 7F TUHO Excel vs Python R99 Bridge Review

## Scope

This is a focused review of `phase7f_tuho_excel_vs_python_r99_bridge.xlsx`.
It excludes cumulative opening/closing balance total rows when ranking actionable model gaps.

No runtime behavior was changed. `use_tuho_r99_input_engine` remains disabled, SHL `fcf_waterfall` remains unimplemented, and tax/revenue/OPEX engines remain untouched.

## Top 5 Actionable Gaps

| Rank | Gap | Evidence | Classification | Why it matters |
|---:|---|---:|---|---|
| 1 | R119 Net dividends too high | Python 174,893.8 vs Excel 151,709.4; delta **+23,184.4 kEUR** | SHL mechanics issue; R99 input issue | This is the official calibration target. Python distributes too much because SHL cash service is too low and the R99/R102 input remains too high. |
| 2 | R106 FCF for dividends too high | Python 174,893.8 vs Excel 152,259.4; delta **+22,634.4 kEUR** | SHL mechanics issue; missing Python field/proxy issue | Python lacks a separate gross-dividend-before-WHT field, so R106 is proxied with `distribution_keur`; still, directionally it shows excess post-SHL cash. |
| 3 | R67 CorpTax under-deducted on cash-flow basis | Python -19,936.6 vs Excel -38,240.9; delta **+18,304.3 kEUR** | Tax timing issue | This is the largest full-horizon R69 driver. Python cash-tax comparable under-deducts tax versus Excel R67, inflating R69/R99 after senior debt. |
| 4 | R99/R102 FCF for SHL input too high | Python 249,545.4 vs Excel 234,745.4; delta **+14,800.0 kEUR** | R99 input issue; tax timing issue; period mapping issue | This blocks C1b and B2. The full-horizon gap is mostly R69/tax, while op_idx 24 is a revenue/PPA transition problem. |
| 5 | R104 Net SHL cash outflow too low | Python -71,784.8 vs Excel -82,486.0; delta **+10,701.2 kEUR** | SHL mechanics issue | Python underpays SHL cash service versus Excel. This directly explains much of the excess dividends and earlier SHL payoff behavior. |

## Transition Focus: op_idx 24-27

| Row | op_idx 24 | op_idx 25 | op_idx 26 | op_idx 27 | Classification |
|---|---:|---:|---:|---:|---|
| R20 Revenue delta | **-2,214.4** | +190.7 | +194.2 | +197.4 | Excel/Python period mapping issue; cash-flow input issue |
| R69 FCF Banks delta | **-2,183.1** | -550.6 | +215.0 | +250.6 | Revenue/PPA timing plus tax timing |
| R70 Senior DS delta | **+750.1** | -559.2 | -586.2 | -627.4 | Senior debt timing issue |
| R99/R102 delta | **-1,432.9** | -1,109.9 | -371.2 | -376.8 | Combined R69 and senior DS timing issue |
| R104 Net SHL cash outflow delta | **+1,840.0** | +1,750.3 | +371.2 | +1,038.8 | SHL mechanics issue |

At op_idx 24 / 2042-06-30, the core issue is not tax. Excel revenue jumps to merchant economics while Python remains much lower:

- Excel R20: 7,438.6 kEUR
- Python R20: 5,224.2 kEUR
- Delta: **-2,214.4 kEUR**

That is the clearest evidence that the PPA-to-merchant boundary remains one of the next hard blockers. Senior DS partly offsets the R69 shortfall at op_idx 24, but then reverses in op_idx 25-27, where Python senior DS is too high.

## SHL Divergence Around 2040-2047

The excluded cumulative balance rows are still diagnostically important:

- SHL opening balance total delta: **-156,613.4 kEUR**
- SHL closing balance total delta: **-156,613.2 kEUR**
- Largest balance deltas cluster from 2040 to 2047.

Actionable SHL rows show the mechanics:

| SHL row | Excel total | Python total | Delta |
|---|---:|---:|---:|
| SHL gross interest | 49,782.2 | 43,110.2 | **-6,672.0** |
| SHL cash interest paid | 38,755.3 | 36,344.0 | **-2,411.3** |
| SHL PIK / capitalized interest | 11,026.8 | 2,737.1 | **-8,289.7** |
| SHL principal repayment | 43,730.7 | 35,440.8 | **-8,289.9** |
| SHL total cash service | 82,486.0 | 71,784.8 | **-10,701.2** |

The SHL gap is not a small display/sign issue. Excel accumulates materially more PIK and then repays materially more principal. Current Python `pik_then_sweep` does not reproduce Excel's continuous cash-interest-first waterfall.

## R67 CorpTax Timing

R67 is the largest full-horizon cash-flow input gap:

- Excel R67: **-38,240.9 kEUR**
- Python comparable R67: **-19,936.6 kEUR**
- Delta: **+18,304.3 kEUR**

This inflates R69 and later-period R99/R102. The biggest individual period deltas are late H2 periods, for example:

- 2058-12-31: +1,788.6 kEUR
- 2059-12-31: +1,786.2 kEUR
- 2057-12-31: +1,770.7 kEUR

The C1b source refinement showed that switching to another existing tax field can improve total R99 but fails selected periods. So tax timing is a major blocker, but not a single-field swap.

## R99/R102 Input Gap

R99/R102 total remains too high:

- Excel R99/R102: **234,745.4 kEUR**
- Python simple proxy: **249,545.4 kEUR**
- Delta: **+14,800.0 kEUR**

The most important period deltas are mixed:

- op_idx 24 / 2042-06-30: **-1,432.9 kEUR**, mainly revenue/PPA transition and senior DS timing.
- late post-SHL H2 periods: positive R69/R99 deltas, mainly tax timing.

This confirms that C1b cannot be safely enabled before fixing the inputs feeding R99.

## R104 SHL Cash Outflow Gap

R104 is underpaid in Python:

- Excel R104: **-82,486.0 kEUR**
- Python R104 comparable: **-71,784.8 kEUR**
- Delta: **+10,701.2 kEUR**

Largest period deltas:

- 2047-12-31: +4,629.0 kEUR
- 2047-06-30: +3,768.8 kEUR
- 2042-06-30: +1,840.0 kEUR
- 2042-12-31: +1,750.3 kEUR

The late 2047 deltas show Python has already depleted SHL earlier than Excel, causing dividends to begin too early/high. The 2042 deltas show Excel starts sweeping principal earlier and more consistently than current Python.

## R119 Net Dividend Gap

Python net dividends exceed Excel by **+23,184.4 kEUR**. The largest period deltas occur exactly when Python begins distributing while Excel is still using cash for SHL:

- 2047-06-30: +6,556.9 kEUR
- 2047-12-31: +5,347.3 kEUR
- Later H2 years also show positive deltas from inflated R69/tax timing.

R119 is therefore a downstream symptom of two upstream blockers:

1. R99/R102 input is not calibrated.
2. SHL mechanics still differ from Excel.

## Recommendation

### Is the next implementation PR senior timing, tax timing, R99 input, or SHL mechanics?

The next implementation PR should be **revenue/PPA period-boundary plus senior transition diagnostic/fix**, not SHL mechanics yet.

Reason: op_idx 24-27 is where the R99 selected-period acceptance fails most visibly. At op_idx 24, revenue is **-2,214.4 kEUR** below Excel and senior DS is **+750.1 kEUR** less negative than Excel. That transition error corrupts R99 exactly where SHL repayment timing begins to matter.

After that, tax timing needs a focused diagnostic/fix. Full-horizon R99 cannot pass while R67 is **+18,304.3 kEUR** under-deducted in Python comparable cash tax.

### Can any single small PR unlock B2?

No. A single small PR is unlikely to unlock B2 safely.

- Senior timing alone will not fix the **+18.3m kEUR** R67 tax gap.
- Tax timing alone will not fix op_idx 24 revenue/PPA boundary or senior transition.
- SHL `fcf_waterfall` alone already failed because the R99 input was wrong.
- R99 input helper opt-in is blocked because no existing tax source variant passes both total and selected-period gates.

### Should we accept PR B1 as the only mergeable fix and defer full TUHO calibration?

Yes. PR B1 remains the only clean mergeable runtime fix from this phase so far.

Recommended sequence:

1. Merge/accept PR B1 as the senior dual-DSCR correction.
2. Defer B2 runtime SHL `fcf_waterfall`.
3. Next diagnostic/fix should target op_idx 24-27 PPA/merchant boundary and senior transition alignment.
4. Then address tax cash timing / R67.
5. Only after R99/R102 is within tolerance should B2 SHL mechanics be retried.

In short: **do not try to unlock B2 with SHL code yet. The next meaningful work is upstream R99 input quality, starting with period-boundary/senior transition and then tax timing.**
