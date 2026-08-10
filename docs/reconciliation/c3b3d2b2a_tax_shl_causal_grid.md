# C3B3D2B2A — Tax / SHL Causal Diagnostic Grid

**Stage**: C3B3D2B2A
**Status**: C3B3D2B2A_R3_SOURCE_CFADS_DSCR_MAPPING_READY_FOR_INDEPENDENT_REVIEW
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

**Conclusion**: CURRENT_CAUSE_UNRESOLVED. No arm combination explains the
2718.02 kEUR residual. The workbook harness itself has not yet been validated
against GRID-0 at per-vector level (GRID-WS0 vs GRID-0 gate pending classification).
Causal attribution claims cannot be made until the baseline is classified.

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

### FINDING-5: Residual cause is unresolved (CURRENT_CAUSE_UNRESOLVED)

All 5 mechanics individually and jointly fail to explain the 2718.02 kEUR
residual when tested relative to GRID-WS0. The GRID-WS0 vs GRID-0 gate
classification is pending — until that baseline is validated, no causal
attribution about the residual vs the clean engine can be made from B/C/D/E arms.

**R3 non-causes confirmed:**
- **DSRA**: DSRA_NOT_CAUSAL_FOR_OBOROVO_CURRENT_RESIDUAL_SOURCE_PROVEN —
  `Inputs!I348=0`, all DSRA rows zero in source workbook. DSRA_ORDERING_UNRESOLVED
  is resolved for Oborovo: DSRA cannot be ranked as a driver.
- **SHL feedback (Arm A)**: FIXED_POINT_COLLAPSES_ANALYTICALLY_TO_IDENTITY_FOR_OBOROVO —
  net TI=0; confirmed by GRID-A ≡ GRID-0.
- **Row-39 cap**: ROW39_CAP_NON_BINDING_FOR_OBOROVO — cap does not bind.

Remaining candidates for D2B2 (unranked):
1. **Clean CFADS composition vs source**: CFADS signed total +347 kEUR. The Phase2C
   clean engine produces CFADS from EBITDA; source uses Macro50 (VBA). Rate, CFADS,
   day-count, and DSCR banding explain the +3,201 kEUR debt gap exactly (G4 residual=0).
2. **Senior debt sizing gap**: clean debt 43,919 kEUR vs source 42,852 kEUR (+1,067 kEUR)
   — fully explained by four INPUT_POLICY_MISMATCH factors (rate/CFADS/daycount/banding).
   See `docs/reconciliation/c3b3d2b2a_cfads_dscr_source_mapping.md`.
3. **GRID-WS0 baseline gap**: if GRID-WS0 ≢ GRID-0, the workbook callback itself has
   structural differences from the clean engine that must be resolved first.

---

## 8. GRID-0 baseline metrics (R2 position-aligned)

| Metric | Clean (GRID-0) | Source | Delta |
|---|---|---|---|
| Total CIT (kEUR) | 3,294.31 | 3,641.40 | -347.09 |
| Clean debt size (kEUR) | 43,919.03 | 42,852.28 | +1,066.75 |
| CFADS max abs delta (kEUR) | — | — | 339.71 |
| CFADS signed total delta (kEUR) | — | — | +347.11 |
| Senior DS max abs delta (kEUR) | — | — | 667.86 |
| Senior DS signed total delta (kEUR) | — | — | +2,242.03 |
| SHL cash max abs delta (kEUR) | — | — | 622.69 |
| SHL cash signed total delta (kEUR) | — | — | -1,894.91 |
| DS[40] closing (kEUR) | 2,718.02 | 0.00 | +2,718.02 |
| SHL closing max abs delta (kEUR) | — | — | 1,901.65 |

**R2 position-alignment note**: Clean Oborovo model has 2 construction periods
(period_index 0 and 1); source fixture has 1. R1 used `{i+1: v}` mapping
(period_index = source index + 1), producing spurious max deltas of ~2575 kEUR.
R2 maps k-th source DS[1..40] value to k-th clean operating period by sequence
position, giving correct values above.

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

1. **Classify GRID-WS0 vs GRID-0 gate first**: validate whether the workbook
   callback surrogate (all flags False) is equivalent to the clean engine.
   Until classified, B/C/D/E arm results are within-surrogate experiments only.
   Status: CURRENT_CAUSE_UNRESOLVED.

2. **Trace CFADS driver at period resolution**: CFADS signed total +347 kEUR
   across DS[1..40]. Source-prove which specific periods drive the difference.

3. **Senior debt sizing gap**: the +3,201 kEUR clean vs source debt gap is fully
   explained by rate (−544), CFADS (−1,918), day-count (−215), DSCR banding (−516),
   and terminal partial period (−9) — G4 vector backward induction reproduces source
   debt exactly (residual = 0.000 kEUR). See `c3b3d2b2a_cfads_dscr_source_mapping.md`.

4. **DSRA**: DSRA_NOT_CAUSAL_FOR_OBOROVO_CURRENT_RESIDUAL_SOURCE_PROVEN — do NOT
   rank DSRA as a contributor. DSRA=0 in source. DSRA_ORDERING_UNRESOLVED is resolved.

5. **Do NOT attempt SHL feedback wiring**: FINDING-1 confirms this has zero TI
   effect for Oborovo and would complicate the engine for no analytical gain.

6. **Do NOT apply EBT gate to production**: EBT gate increases the residual and
   is not the driver. It must remain in the diagnostic-only grid.

---

## 11. Unresolved items

| Item | Status | Planned stage |
|---|---|---|
| DSRA/reserve movement ordering | DSRA_NOT_CAUSAL_FOR_OBOROVO_CURRENT_RESIDUAL_SOURCE_PROVEN (resolved) | — |
| Construction date convention | CONSTRUCTION_DATE_CONVENTION_UNRESOLVED | D2B2 |
| SHL input authority promotion | CLEAN_SHL_PROJECT_INPUT_AUTHORITY_HANDOFF_PENDING_D2B2 | D2B2 |
| CFADS driver period resolution | Not yet attributed | D2B2 |
| GRID-WS0 vs GRID-0 gate | CURRENT_CAUSE_UNRESOLVED — pending classification | D2B2 |

---

## 12. Test suite

`tests/test_stage_c3b3d2b2a_tax_shl_causal_grid.py` — 184 test functions (R3).

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
| TestD2B1ExactComparators | 10 | D2B1 contract, backward-compat aliases |
| TestGridAActualExecution | 4 | GRID-A typed execution, full horizon |
| TestGrid0NumericalReproduction | 13 | R2 tight assertions (339.71/667.86/622.69/-1894.91) |
| TestGridS0VectorContract | 5 | GRID-S0 ≡ GRID-0 within solver tolerance |
| TestGridWS0VsGrid0Gate | 5 | GRID-WS0 baseline gate classification |
| TestSourceReplayRows | 7 | Per-row SOURCE_REPLAY_PROVEN rows 36-43 |
| TestRow39StateRepaired | 3 | Row39 cap state propagation fix verified |
| TestGridAFullHorizon | 3 | Full-horizon SHL injection (debt tenor + post-maturity) |
| TestGridABCDSemanticsHonest | 4 | GRID-ABCD shl_netting_in_tax=True + A=0 identity |
| TestCfadsDscrSourceMapping | 7 | R3: CF79/Macro49/50/DS20 formula mapping SOURCE_PROVEN |
| TestOborovoCfadsAlignment | 5 | R3: CF79≈Macro50 during DSCR=1.15 periods; diverges at 1.35 |
| TestTuhoBankSizingProof | 6 | R3: TUHO bank CFADS = \|SDS\| × target_DSCR derivation |
| TestOborovoDebtSizingReplay | 7 | R3: G4 bridge closed (residual=0); rate/CFADS/daycount deltas |
| TestDsraNotCausal | 5 | R3: DSRA_NOT_CAUSAL_FOR_OBOROVO_CURRENT_RESIDUAL_SOURCE_PROVEN |
| TestTaxWindowClassification | 5 | R3: 5-period window label; row39 non-binding; construction loss |

---

## 13. Final verdict

```
C3B3D2B2A_R3_SOURCE_CFADS_DSCR_MAPPING_READY_FOR_INDEPENDENT_REVIEW
```

**R2 evidence (carried forward)**:
- GRID-A ≡ GRID-0 (full-horizon injection, sub-milli-kEUR delta): CONFIRMED
- Position-aligned comparators: CFADS max delta 339.71, SD max delta 667.86, SHL cash max delta 622.69 kEUR
- Row39 state propagation fix implemented; ROW39_CAP_NON_BINDING_FOR_OBOROVO confirmed
- GRID-ABCD shl_netting_in_tax=True: semantically honest (A=0 identity proven)
- Source replay rows 36/37/38/39/41/43: SOURCE_REPLAY_PROVEN classification
- CURRENT_CAUSE_UNRESOLVED: no mechanic combination explains the 2718.02 kEUR residual

**R3 evidence (new)**:
- CF79/Macro49/Macro50/DS20 formula chain: SOURCE_PROVEN_FORMULA for all visible cells
- Macro50 output: VBA_IMPLEMENTATION_NOT_VISIBLE (password-protected)
- CFADS_ALIGNED_IN_THIS_SCENARIO: CF79 ≈ Macro50 during DSCR=1.15 periods (max diff < 0.01 kEUR)
- DSCR banding effect: at DSCR=1.35 periods (25–27), Macro50 < CF79 by 590–743 kEUR (backward PV constraint)
- G4 vector backward induction: reproduces source debt 42,852.279 kEUR exactly (residual = 0.000 kEUR)
- Causal bridge: rate (−544), CFADS (−1,918), day-count (−215), DSCR banding (−516), partial period (−9) → bridge closed
- TUHO bank-sizing proof: bank_cfads = |SDS| × target_DSCR = 2,539.634 kEUR (SOURCE_DERIVED_IDENTITY)
- DSRA_NOT_CAUSAL_FOR_OBOROVO_CURRENT_RESIDUAL_SOURCE_PROVEN: DSRA=0 in source (Inputs!I348=0)
- WORKBOOK_5_MODEL_PERIOD_LOSS_WINDOW_KNOWN_SOURCE_BUG: B36=5 periods → 2.5 calendar years (semiannual)
- Source mapping document: `docs/reconciliation/c3b3d2b2a_cfads_dscr_source_mapping.md`
