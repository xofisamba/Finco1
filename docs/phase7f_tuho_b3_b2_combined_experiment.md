# Phase 7F TUHO B3/B2 Combined Experiment

Status: diagnostic only. This experiment was run locally and fully reverted. No runtime experiment code was committed.

Remote baseline at time of experiment: `01c07fdfba8b1ac58d7269a30b4f543dceab4426`

## Experiment Purpose

The local test checked whether combining the directionally correct B3 PPA-to-merchant boundary fix with the rejected B2 `fcf_waterfall` mechanics would bring TUHO distributions and SHL balances closer to Excel.

The combined hypothesis was:

- B3 moves op_idx 24 from PPA to merchant using the period end date for the TUHO PPA boundary.
- B2 adds cash-interest-first SHL `fcf_waterfall` mechanics.
- B2 uses the previously tested proxy `fcf_for_shl = cf_after_tax - senior_ds`.

No tax, R99/R102, merchant price, generation, Oborovo, or factory tuning was included beyond the temporary TUHO SHL method switch needed to run the local experiment.

## Scenario Results

Excel net dividends target: 151,709 kEUR.

| scenario | revenue | senior_ds | R99 proxy | SHL cash interest | SHL PIK | SHL principal | SHL service | SHL peak | first distribution | total distributions | gap vs Excel 151,709 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| A. PR B1 baseline | 420,584.53 | 65,645.11 | 249,600.02 | 39,081.12 | 2,737.09 | 35,440.78 | 74,521.90 | 35,440.78 | op_idx 34 / 2047-06-30 | 174,948.38 | +23,239.38 |
| B. B3-only candidate | 422,986.49 | 65,971.36 | 251,688.21 | 38,457.54 | 1,840.69 | 34,544.38 | 73,001.92 | 34,544.38 | op_idx 33 / 2046-12-31 | 180,553.91 | +28,844.91 |
| C. B2-only candidate | 420,584.53 | 65,645.11 | 249,600.02 | 39,750.95 | 3,134.42 | 35,838.11 | 75,589.06 | 35,835.06 | op_idx 34 / 2047-06-30 | 174,010.96 | +22,301.96 |
| D. B3+B2 combined | 422,986.49 | 65,971.36 | 251,688.21 | 39,163.23 | 2,103.37 | 34,807.06 | 73,970.30 | 34,590.54 | op_idx 33 / 2046-12-31 | 177,717.91 | +26,008.91 |

## Acceptance Criteria

Combined experiment acceptance gates:

| criterion | accepted range | combined result | status |
|---|---:|---:|---|
| Total distributions | 144,000 to 159,000 | 177,717.91 | Fail |
| SHL service | 78,000 to 87,000 | 73,970.30 | Fail |
| SHL peak balance | 41,000 to 47,000 | 34,590.54 | Fail |
| First distribution timing | within +/-1 period of Excel | op_idx 33 / 2046-12-31 | Fail |
| Senior DS total | 65,400 to 66,200 | 65,971.36 | Pass |
| Oborovo unchanged | within +/-0.01 kEUR | unchanged on checked totals | Pass |
| SHL balance negative | none | none | Pass |
| Principal cap violation | none | none | Pass |

Oborovo checked totals under the local combined experiment:

| metric | value |
|---|---:|
| senior_ds | 63,500.894563 |
| distribution | 104,699.427035 |
| shl_service | 31,791.830203 |

## Conclusion

B3 standalone is not accepted. The boundary fix is directionally correct, but with current SHL mechanics the additional merchant-period cash flows through to distributions and trips the standalone revert threshold.

B2 standalone is not accepted. The `fcf_waterfall` formula is mechanically clean, but the proxy `fcf_for_shl = cf_after_tax - senior_ds` does not reproduce Excel R99/R102 closely enough.

B3+B2 combined is not accepted. The combined scenario still leaves distributions materially too high, SHL service too low, and SHL peak balance too low versus Excel.

The current `fcf_for_shl` proxy remains invalid for calibration. B2 remains blocked until the R99/R102 input source is improved.

No runtime changes from this experiment should be committed.
