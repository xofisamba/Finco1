# C3B3D2B2A — Tax / SHL Causal Diagnostic Grid

**Stage**: C3B3D2B2A
**Status**: CAUSAL_GRID_READY_FOR_INDEPENDENT_REVIEW
**Base**: C3B3D2B1 main (`7cd1366c4e81a35e55c529c324a7809e9a78eef4`)
**Branch**: `stage-c3b3d2b2a-tax-shl-causal-grid`

---

## 1. Mission

Causally explain the **CURRENT_UPSTREAM_CLEAN_CASH_RESIDUAL** (~2718.02 kEUR
clean DS[40] SHL closing balance vs 0.00 kEUR source) by evaluating 12
arm combinations of source-proven workbook mechanics against the clean engine
baseline.

Evidence priority: **source fixture vectors over implementation assumptions**.
No production-engine modifications. No source fixture vectors in production paths.

---

## 2. Residual under investigation

| Item | Value |
|---|---|
| Clean DS[40] closing (GRID-0) | **2718.02 kEUR** |
| Source DS[40] closing | **0.00 kEUR** |
| Delta | **2718.02 kEUR** (CURRENT_UPSTREAM_CLEAN_CASH_RESIDUAL) |
| Label | EXPECTED_PRE_D2B2_UPSTREAM_CLEAN_CASH_RESIDUAL |

The residual is confirmed by D2B1 TestP (TestP_RealPhase2CIntegration). It is
not a formula failure — SHL arithmetic is separately source-proven via TestJ.

---

## 3. Governance constraints

| Constraint | Status |
|---|---|
| No DS25/DS40 period boundary hardcoding | ENFORCED |
| No project-name dispatch | ENFORCED |
| No approved_delta or balancing plug | ENFORCED |
| No calibration of clean engine to source | ENFORCED |
| Protected C3B2 SHA unchanged | ENFORCED |
| 13547.2 absent from clean SHL logic | ENFORCED |
| DSRA_ORDERING_UNRESOLVED | ACKNOWLEDGED — no DSRA implementation |
| CONSTRUCTION_DATE_CONVENTION_UNRESOLVED | ACKNOWLEDGED — DCF=1.0 arithmetic-implied |

---

## 4. Authoritative SHL inputs (D2A fixture)

`CLEAN_SHL_PROJECT_INPUT_AUTHORITY_HANDOFF_PENDING_D2B2`

| Parameter | Authoritative value | Source |
|---|---|---|
| draw_keur | 14,620.773894815633 kEUR | D2A fixture, Inputs!D325 |
| annual_rate | 0.08 | Inputs!F328 |
| construction PIK | 1,169.6619115852516 kEUR | derived (DCF=1.0) |
| first operating opening | 15,790.435806400885 kEUR | derived |
| day_count_convention | ACT/365 FIXED | SOURCE_PROVEN_FOR_OBOROVO |

Legacy factory value `shl_amount_keur=13547.2` is **not authoritative** and
must not appear in clean SHL logic.

---

## 5. Source-proven workbook mechanics (D2A fixture evidence)

| ID | Mechanic | Excel formula | Evidence status |
|---|---|---|---|
| **A** | SHL interest feedback (SHL→tax→CFADS→SD→SHL loop) | Non-deductible reintegration | SOURCE_PROVEN |
| **B** | H2+H1 CIT pairing | Row 43: `=MAX(SUM(F41:G41),0)*B43*(G4>0)*(MOD(G4,2)=0)` | SOURCE_PROVEN |
| **C** | EBT gate for loss utilisation | Row 37: `=IF(AND(G36<=0,G32>0),MIN(ABS(G36),G32),0)` | SOURCE_PROVEN |
| **D** | Rolling 5-period loss window | Row 36: `SUMIF(last-B36-periods TI,"<0")+cumulative_used` | SOURCE_PROVEN |
| **E** | Row-39 carriable-loss cap | Row 39: `=MIN(G38,F35*B37)` | SOURCE_PROVEN |

SHL deductibility (Arm A): P&L row 59 `C59=1.0`, `D59=True` → full SHL
non-deductibility for Oborovo. `FR=SHL` → zero net TI effect.

---

## 6. Causal attribution grid

12-arm evaluation. All metrics are diagnostic — no calibration targets.

```
Grid           Tax Δ (kEUR)   Debt-size Δ   SHL cash Δ  Final SHL closing Interpretation
----------------------------------------------------------------------------------------------------
GRID-0               -347.1       +1066.8      -2125.3            2718.02    Current clean baseline (C3B3D2B1 main)
GRID-A               -347.1       +1066.8      -2125.3            2718.02    SHL interest feedback (non-deductible: net TI=0 for Oborovo)
GRID-B               -348.1       +1067.2      -1771.6            2717.55    H2+H1 model-year CIT pairing only
GRID-C                -94.6        +948.5      -2012.0            2780.13    EBT gate for loss utilisation only
GRID-D               -121.6        +967.6      -2008.5            2767.39    Rolling 5-period loss window only
GRID-E               -169.2        +999.0      -2002.3            2746.80    Row-39 carriable-loss cap only
GRID-BC              -272.2       +1017.0      -1781.5            2750.49    H2+H1 pairing + EBT gate
GRID-BD              -300.0       +1036.1      -1777.9            2737.80    H2+H1 pairing + rolling window
GRID-CD               -94.6        +948.5      -2012.0            2780.13    EBT gate + rolling window
GRID-BCD             -272.2       +1017.0      -1781.5            2750.49    H2+H1 + EBT gate + rolling window
GRID-ABCD            -272.2       +1017.0      -1781.5            2750.49    SHL feedback + H2+H1 + EBT gate + rolling window
GRID-ABCDE           -272.2       +1017.0      -1781.5            2750.49    All source-proven mechanics including row39 cap
```

All values are `CURRENT_UPSTREAM_CLEAN_CASH_RESIDUAL`. Not calibration targets.

---

## 7. Key analytical findings

### FINDING-1: SHL_OUTSIDE_FIXED_POINT = 0 for Oborovo (GRID-A ≡ GRID-0)

SHL is **fully non-deductible** for Oborovo (P&L row 59: `C59=1.0`, `D59=True`,
`FR=SHL`). Adding gross SHL interest to `total_interest_keur` and equal amount
to `other_fiscal_reintegration` produces **net TI delta = 0**.

- GRID-A ≡ GRID-0 (delta = 0.000 kEUR, confirmed by test)
- The outer SHL→tax fixed-point loop converges in 1 iteration
- SHL feedback is **not a contributor** to the 2718.02 kEUR residual

### FINDING-2: Tax mechanics increase the residual (do not reduce it)

All workbook mechanic combinations produce DS[40] ≥ GRID-0 (2718.02 kEUR).
No arm combination closes the gap to source 0.00 kEUR.

| Arm | DS[40] | Delta vs GRID-0 | Direction |
|---|---|---|---|
| GRID-0 | 2718.02 | 0.00 | baseline |
| GRID-B | 2717.55 | -0.47 | negligible |
| GRID-C | 2780.13 | +62.11 | increases residual |
| GRID-D | 2767.39 | +49.37 | increases residual |
| GRID-E | 2746.80 | +28.78 | increases residual |
| GRID-ABCDE | 2750.49 | +32.47 | increases residual |

**Conclusion**: The CURRENT_UPSTREAM_CLEAN_CASH_RESIDUAL is **not attributable**
to any of the 5 source-proven tax / SHL mechanics tested. The causal driver lies
upstream of the tax computation.

### FINDING-3: EBT gate prevents all loss utilisation for Oborovo

Oborovo's EBT is always negative (SHL interest exceeds taxable income).
The EBT gate (Row 37) therefore prevents ALL loss carryforward utilisation.
When active, expired losses → higher CIT → lower CFADS → less cash available
for SHL → **larger** DS[40] residual. This is qualitatively confirmed by
GRID-C (+62 kEUR vs GRID-0) and GRID-BCD (+32 kEUR).

### FINDING-4: Row-39 cap does not bind for Oborovo

GRID-ABCDE = GRID-ABCD (< 0.01 kEUR difference). The carriable-loss cap
(MIN(row38, prior_TI × B37)) does not bind for Oborovo's TI profile.
The row-39 contribution to the residual is effectively zero.

### FINDING-5: Residual driver is upstream of tax — likely CFADS/waterfall ordering

Since all 5 mechanics individually and jointly fail to explain 2718 kEUR, the
primary driver must be elsewhere. Candidates for D2B2:

1. **DSRA/reserve movement ordering** (DSRA_ORDERING_UNRESOLVED): reserve
   cash movements are not yet implemented in the clean waterfall. Source may
   credit reserve releases before SHL repayment.
2. **Clean CFADS composition vs source**: the clean engine CFADS max abs delta
   vs source is 3121.16 kEUR (GRID-0 diagnostic). This exceeds the 2718 kEUR
   residual — the CFADS driver alone could explain the residual.
3. **Senior debt sizing difference**: clean debt 43,919 kEUR vs source 42,852
   kEUR (+1067 kEUR). Higher debt service reduces cash available for SHL.

---

## 8. GRID-0 baseline metrics

| Metric | Clean (GRID-0) | Source | Delta |
|---|---|---|---|
| Total CIT (kEUR) | 10,261.25 | 10,443.09 | -181.84 |
| Clean debt size (kEUR) | 43,919.03 | 42,852.28 | +1,066.75 |
| CFADS max abs delta (kEUR) | — | — | 3,121.16 |
| SHL cash signed delta (kEUR) | — | — | -2,125.29 |
| DS[40] closing (kEUR) | 2,718.02 | 0.00 | +2,718.02 |
| SHL closing max abs delta (kEUR) | — | — | 1,901.65 |

Solver convergence: achieved, iterations reported per arm.

---

## 9. Implementation notes

### LCF approximation in workbook arms (GRID-B through GRID-E)

The workbook LCF approximation in `diagnose_c3b3d2b2a_tax_shl_causal_grid.py`
uses `_compute_workbook_lcf` and `_compute_cit_by_period` — **diagnostic-only**
functions. These are NOT used in the production engine (`financial_engine/`).

The rolling-window (GRID-D) and row-39 cap (GRID-E) approximations may diverge
from the exact workbook Excel formula for edge cases. For GRID-D specifically:

- 5-period rolling SUMIF of negative TI; losses already allocated reduce the pool
- Oborovo construction loss is within 5 periods of first profitable operating period
- Result: 5-period window and 10-period window give similar results for Oborovo

For the canonical baseline (GRID-0), the exact clean engine runs via
`run_senior_debt_model()` — no approximation.

### solve_senior_debt callback contract

Workbook arms (GRID-B through GRID-E combinations) call `solve_senior_debt()`
directly with a custom `tax_cfads_fn` callback. The callback:
1. Receives `senior_interest_by_period: dict[int, float]`
2. Computes workbook TI, LCF, and CIT approximation
3. Returns `(cfads_by_period, cash_tax_by_period)` dicts

This does NOT modify the production engine. The `PeriodInterestInput.shl_interest_keur`
field exists in `financial_engine/inputs.py` (defaults 0.0) but is unused in
production paths — correctly excluded from the diagnostic per FINDING-1.

---

## 10. D2B2 recommendations

1. **Resolve DSRA ordering**: source-prove the relative ordering of DSRA/reserve
   cash movements vs SHL repayments in the workbook waterfall. This is the
   most likely explanation for the 2718 kEUR residual given FINDING-2 and FINDING-5.

2. **Trace CFADS driver at period resolution**: the 3121 kEUR max CFADS delta
   dwarfs the 2718 kEUR SHL residual. Source-prove which specific periods
   drive the CFADS difference and whether it flows from depreciation, revenue,
   or opex differences.

3. **Senior debt sizing gap**: the +1067 kEUR clean vs source debt gap increases
   debt service, reducing SHL cash. Confirm the sizing difference is fully
   accounted for by the WORKBOOK_PERIODISATION_MISMATCH identified in C3B3B.

4. **Do NOT attempt SHL feedback wiring**: FINDING-1 confirms this has zero TI
   effect for Oborovo and would complicate the engine for no analytical gain.

5. **Do NOT apply EBT gate to production**: FINDING-3 confirms EBT gate
   increases the residual and is not the driver. It must remain in the
   diagnostic-only grid.

---

## 11. Unresolved items

| Item | Status | Planned stage |
|---|---|---|
| DSRA/reserve movement ordering | DSRA_ORDERING_UNRESOLVED | D2B2 |
| Construction date convention | CONSTRUCTION_DATE_CONVENTION_UNRESOLVED | D2B2 |
| SHL input authority promotion | CLEAN_SHL_PROJECT_INPUT_AUTHORITY_HANDOFF_PENDING_D2B2 | D2B2 |
| CFADS driver period resolution | Not yet attributed | D2B2 |

---

## 12. Test suite

`tests/test_stage_c3b3d2b2a_tax_shl_causal_grid.py` — 85 test functions.

| Class | Count | Coverage |
|---|---|---|
| TestGovernanceConstants | 10 | Constants, prohibited values |
| TestSourceFixtureVectors | 5 | Fixture loading, CIT/CFADS/SD/SHL vectors |
| TestWorkbookTaxConfig | 5 | Config dataclass arms |
| TestGrid0 | 12 | D2B1 baseline reproduction |
| TestGridA | 7 | SHL_OUTSIDE_FIXED_POINT = 0 |
| TestGridB | 5 | H2+H1 arm |
| TestGridC | 5 | EBT gate arm |
| TestGridD | 4 | Rolling window arm |
| TestGridE | 4 | Row-39 cap arm |
| TestCombinationArms | 12 | BC, BD, CD, BCD, ABCD, ABCDE |
| TestCausalAttributionFindings | 9 | Key findings verification |
| TestShlInputAuthority | 3 | 14620.77 authoritative, 13547.2 absent |
| TestFormatCausalAttributionTable | 3 | Output formatter |

---

## 13. Final verdict

```
C3B3D2B2A_CAUSAL_GRID_READY_FOR_INDEPENDENT_REVIEW
```

**Evidence delivered**:
- GRID-A ≡ GRID-0: SHL_OUTSIDE_FIXED_POINT = 0 for Oborovo (CONFIRMED)
- No workbook tax mechanic combination explains the 2718.02 kEUR residual
- All 5 mechanics individually increase the residual or have negligible effect
- Residual causal driver is upstream of tax: DSRA ordering or CFADS composition
- D2B2 has a clear, bounded problem statement: waterfall ordering investigation
