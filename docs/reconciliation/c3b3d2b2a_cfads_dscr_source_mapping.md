# C3B3D2B2A — CFADS / DSCR / Senior Debt Source Mapping

**Stage**: C3B3D2B2A (R5)
**Status**: C3B3D2B2A_R5_DIAGNOSTIC_MAPPING_READY_FOR_MERGE_REVIEW
**Authority**: Source fixture vectors; no production-engine modifications; no VBA reverse-engineering.

---

## 1. Purpose

This document is the **authoritative source mapping** for the two-layer CFADS
architecture used by the Finco financial model. It covers:

- Oborovo (primary case)
- TUHO (cross-project proof)

Evidence classification labels:

| Label | Meaning |
|---|---|
| SOURCE_PROVEN_FORMULA | Formula text extracted from workbook; exact source |
| SOURCE_PROVEN_VALUE | Cached value extracted from workbook; formula not available |
| SOURCE_DERIVED_IDENTITY | Derivable from two other SOURCE_PROVEN quantities |
| VBA_IMPLEMENTATION_NOT_VISIBLE | Password-protected VBA; formula unknown |
| BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED | VBA transforms base→bank CFADS; exact algorithm unknown |
| EARLY_P50_P90_CFADS_ALIGNMENT_REASON_UNRESOLVED | Why CF79≈Macro50 in early periods is not source-proven |
| BANK_SIZING_SCENARIO_NOT_IN_COMMITTED_OBOROVO_FIXTURES | Bank scenario not confirmed from committed source fixtures |
| BANK_SIZING_SCENARIO_P90_10Y_REVIEWER_CONFIRMED_NOT_COMMITTED | Bank-sizing scenario P90-10y asserted by reviewer; not extracted into committed fixtures |
| CURRENT_GRID0_PRODUCTION_CANDIDATE | Current runtime GRID-0 debt ≈ 43,919.03 kEUR |
| HISTORICAL_GENERIC_PHASE2C_SCALAR_DIAGNOSTIC | Historical C3B2 fixture starting point ≈ 46,053.40 kEUR (NOT current runtime) |
| SOURCE_EXCEL_SENIOR_DEBT | Source workbook debt = 42,852.279 kEUR |
| HISTORICAL_C3B2_SOURCE_REPLAY_PROOF | G0→G4 bridge from historical fixture (not current GRID-0) |
| CURRENT_GRID0_TO_SOURCE_DEBT_BRIDGE_NOT_YET_CLOSED | Current GRID-0 → source gap not yet decomposed from current baseline |

---

## 2. Production scenarios (Oborovo)

### 2.1 Base case scenario

| Item | Value | Cell | Status |
|---|---|---|---|
| Production scenario | P_50 | Inputs!D52 | SOURCE_PROVEN_VALUE |
| Market price scenario | Fixed | Inputs!D89 | SOURCE_PROVEN_VALUE |

`Inputs!D52 = "P_50"` — BASE_CASE_SCENARIO_P50_SOURCE_PROVEN

### 2.2 Bank-sizing scenario

| Item | Value | Status |
|---|---|---|
| Bank-sizing scenario cell in Oborovo fixtures | Not extracted | BANK_SIZING_SCENARIO_NOT_IN_COMMITTED_OBOROVO_FIXTURES |
| Macro!row50 output formula | VBA (not visible) | VBA_IMPLEMENTATION_NOT_VISIBLE |
| Bank-sizing scenario (asserted by reviewer) | P90-10y | BANK_SIZING_SCENARIO_P90_10Y_REVIEWER_CONFIRMED_NOT_COMMITTED |

The reviewer specification states the bank-sizing scenario is P90-10y. This is
consistent with TUHO's cross-project proof (see Section 8) where bank CFADS < base
CFADS in a way that is consistent with a more conservative production scenario.
However, the exact Oborovo Inputs/Scenarios cell confirming P90-10y has **not** been
extracted into committed fixtures. To upgrade to SOURCE_PROVEN, extract the
`Inputs/Scenarios` sheet bank-sizing scenario selector cell and commit it.

**BANK_SIZING_SCENARIO_P90_10Y_REVIEWER_CONFIRMED_NOT_COMMITTED**: reviewer-asserted
information is not SOURCE_PROVEN. Never label reviewer-supplied assertions as
SOURCE_PROVEN.

### 2.3 Why CF79 ≈ Macro50 in early periods (UNRESOLVED)

The observed source fact: CF79 ≈ Macro50 (diff < 0.01 kEUR) for operating periods
1–24 (DSCR=1.15 band), despite base = P50 and bank = P90-10y.

Potential explanations (NOT source-proven):
- Contracted/PPA revenues may be unaffected by P50/P90 — merchant/open-market
  portion small or zero for Oborovo (Fixed price scenario)
- P90 may affect only the merchant/open-market production volume
- Scenario divergence may only appear in later periods or different regime

**Classification: EARLY_P50_P90_CFADS_ALIGNMENT_REASON_UNRESOLVED**

Do NOT infer the reason solely from timing or DSCR banding.

### 2.4 Why CF79 > Macro50 in later periods (UNRESOLVED)

CF79 > Macro50 by 590–743 kEUR at periods 25–27 (DSCR=1.35 band) and by
700–1,100 kEUR post-debt-maturity. The VBA transformation from CF79 → Macro50 is
not visible.

**Classification: BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED**

Do NOT assert "backward PV constraint causes Macro50 divergence" — the flow is
CF79 → Macro49 → Macro50 → DS20 → DS23 → DS47 backward PV. DS47 cannot be
asserted as the source mechanism for generating Macro50 unless VBA/source
dependency proves that feedback direction.

---

## 3. Two-layer CFADS architecture (Oborovo)

```
CF sheet (Base / P50)             Macro sheet               DS sheet
────────────────────────────────────────────────────────────────────
CF!row79 (base CFADS)   ─────►   Macro!row49 (input)
  =SUM(H23,H49,H73,               =CF!H79
  H76,H77)+B80*(H4=0)
                                  Macro!row50 (output)  ──►  DS!row20 (bank CFADS)
                                    VBA (not visible)          =Macro!H50
                                    [Bank / P90-10y]
                                                         ──►  DS!row22 (DSCR target)
                                                                 =(B22*H15)+(H16*D22)+(H17*C22)
                                                         ──►  DS!row23 (allowed SDS)
                                                                 =(H20/H22+SUM(CF!H83:H83))
                                                                    *H9*B23
                                                         ──►  DS!row47 (backward PV)
                                                                 =(H46+I47)/
                                                                    (1+H44*(1+B54/(1-B54))*H6)
                                                                    [+ H82 refinancing]
```

### 3.1 CF!row79 — Base CFADS

| Item | Value | Status |
|---|---|---|
| Formula (period H) | `=SUM(H23,H49,H73,H76,H77)+$B$80*(H$4=0)` | SOURCE_PROVEN_FORMULA |
| Production scenario | P50 (Inputs!D52) | SOURCE_PROVEN_VALUE |
| Local taxes (CF!row73) | 0 all periods | SOURCE_PROVEN_VALUE |
| Interest income (CF!row76) | 0 all periods (DSRA absent) | SOURCE_PROVEN_VALUE |

### 3.2 Macro!row49 — Input to bank-sizing VBA

| Item | Value | Status |
|---|---|---|
| Formula (period H) | `=CF!H79` | SOURCE_PROVEN_FORMULA |
| Interpretation | Passes base CFADS to bank-sizing VBA | SOURCE_PROVEN_FORMULA |

### 3.3 Macro!row50 — Bank-sizing output

| Item | Value | Status |
|---|---|---|
| Formula | `None` (VBA, password-protected) | VBA_IMPLEMENTATION_NOT_VISIBLE |
| Production scenario | P90-10y (asserted; BANK_SIZING_SCENARIO_P90_10Y_REVIEWER_CONFIRMED_NOT_COMMITTED) | — |
| Transformation mechanism | Unknown | BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED |
| Period 1 value | 2,575.003 kEUR (≈ CF79[1]) | SOURCE_PROVEN_VALUE |
| Periods 1–24 | CF79 ≈ Macro50, diff < 0.01 kEUR | EARLY_P50_P90_CFADS_ALIGNMENT_REASON_UNRESOLVED |
| Periods 25–27 | Macro50 < CF79 by 590–743 kEUR | BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED |

### 3.4 DS!row20 — Bank CFADS entering debt service

| Item | Value | Status |
|---|---|---|
| Formula (period H) | `=Macro!H50` | SOURCE_PROVEN_FORMULA |

### 3.5 DS!row22 — DSCR target

| Item | Value | Status |
|---|---|---|
| Formula (period H) | `=($B$22*H15)+(H16*$D$22)+(H17*$C$22)` | SOURCE_PROVEN_FORMULA |
| B22 (base DSCR) | 1.15 (periods 1–24) | SOURCE_PROVEN_VALUE |
| D22 (band2 DSCR) | 1.35 (periods 25–28) | SOURCE_PROVEN_VALUE |
| Transition period | Index 25 (operating period 25) | SOURCE_PROVEN_VALUE |

### 3.6 DS!row23 — Allowed senior debt service

| Item | Value | Status |
|---|---|---|
| Formula (period H) | `=(H20/H22+SUM(CF!H83:H83))*H9*$B23` | SOURCE_PROVEN_FORMULA |
| Interpretation | `(bank_cfads/target_dscr + DSRA_adj) × ops_flag × tranche_flag` | SOURCE_PROVEN_FORMULA |
| DSRA adj (Oborovo) | = 0 (DSRA inactive) | SOURCE_PROVEN_VALUE |
| Identity (when DSRA=0) | `allowed_SDS = bank_cfads / target_DSCR` | SOURCE_DERIVED_IDENTITY |

### 3.7 DS!row47 — Backward PV debt capacity

| Item | Value | Status |
|---|---|---|
| Formula | `=SUM(IF(NOT(H7),(H46+I47)/(1+H44*(1+$B54/(1-$B$54))*H$6),0),H82)` | SOURCE_PROVEN_FORMULA |
| Simplified (WHT=0, B54=0) | `(allowed_SDS[t] + debt[t+1]) / (1 + rate[t] × dayfrac[t])` | SOURCE_DERIVED_IDENTITY |

**Important**: DS!row47 is DOWNSTREAM of DS!row20. It cannot be asserted as the mechanism
generating Macro!row50. The VBA transformation direction is CF79 → Macro49 → Macro50 → DS20.

---

## 4. Three debt baselines (must not be conflated)

| Label | Authority | Value |
|---|---|---|
| CURRENT_GRID0_PRODUCTION_CANDIDATE | Current runtime GRID-0 | **43,919.032698 kEUR** |
| HISTORICAL_GENERIC_PHASE2C_SCALAR_DIAGNOSTIC | C3B2 historical fixture | **46,053.402379 kEUR** |
| SOURCE_EXCEL_SENIOR_DEBT | Source workbook DS!D51 | **42,852.278763 kEUR** |

### 4.1 CURRENT_GRID0_PRODUCTION_CANDIDATE

The current runtime GRID-0 at the R5/R5.1 reviewed baseline produces **43,919.032698 kEUR**
senior debt. This is the relevant baseline for the DS[40] SHL residual ≈ 2,718.02 kEUR.

Delta vs source: **+1,066.754 kEUR** (CURRENT_UPSTREAM_CLEAN_CASH_RESIDUAL context)

### 4.2 HISTORICAL_GENERIC_PHASE2C_SCALAR_DIAGNOSTIC

The C3B2 phase-level fixture recorded a generic Phase2C scalar diagnostic of
**46,053.402 kEUR**. The fixture itself classifies this as:
`"GENERIC_PHASE2C_SCALAR_DIAGNOSTIC"` and explicitly `"NOT current production runtime"`.

This must not be cited as the current clean engine output.

### 4.3 SOURCE_EXCEL_SENIOR_DEBT

Source workbook: `DS!D51 = SUM(G51:DW51) = 42,852.279 kEUR` (Inputs!D192 = DS!D51).

---

## 5. Causal bridge classification

### 5.1 HISTORICAL_C3B2_SOURCE_REPLAY_PROOF (G0→G4 bridge)

The existing fixture bridge from 46,053 → 42,852.279 kEUR via four
INPUT_POLICY_MISMATCH factors is classified as:

**HISTORICAL_C3B2_SOURCE_REPLAY_PROOF**

| Step | Case | kEUR | Delta | Driver |
|---|---|---|---|---|
| G0 | HISTORICAL generic Phase2C | 46,053.402 | — | HISTORICAL_GENERIC_PHASE2C_SCALAR_DIAGNOSTIC |
| G1 | + Source sculpting rates | 45,509.595 | −543.807 | Rate: 5.65% flat vs blended 5.9514% |
| G2 | + Source bank CFADS (Macro50) | 43,591.559 | −1,918.036 | CFADS: Phase2C EBITDA-based vs Macro50 |
| G3 | + ACT/360 day-count | 43,376.955 | −214.604 | Day-count: ACT/365 vs ACT/360 |
| G3A | + Scalar backward PV | 43,368.224 | −8.732 | Terminal partial period (ops_flag) |
| G4 | + Vector DSCR banding | 42,852.279 | −515.945 | DSCR 1.35 at periods 25–28 |
| Source | Excel workbook | 42,852.279 | 0.000 | Bridge closed |

`bridge_closed_to_vector = True` — the historical bridge is internally consistent.

**This bridge does NOT prove that the current GRID-0 (43,919) gap is fully explained.**
The factors identified are directional evidence only for the current delta.

### 5.2 CURRENT_GRID0_TO_SOURCE_DEBT_BRIDGE_NOT_YET_CLOSED

| Metric | Value |
|---|---|
| Current GRID-0 debt | 43,919.032698 kEUR |
| Source debt | 42,852.278763 kEUR |
| Delta | +1,066.754 kEUR |
| Bridge status | **CURRENT_GRID0_TO_SOURCE_DEBT_BRIDGE_NOT_YET_CLOSED** |

Likely contributing factors (directional, from historical bridge evidence):
- Rate mismatch: 5.65% clean vs 5.9514% source blended → directional (negative contribution)
- Bank CFADS vs clean EBITDA-CFADS → directional (negative contribution)
- ACT/360 vs ACT/365 → directional (negative contribution)
- DSCR banding (1.35 at periods 25–28) → directional (negative contribution)

A properly built current GRID-0 bridge would require running Phase2C counterfactuals
starting from the CURRENT GRID-0 baseline, changing one factor at a time. This has
not been done in C3B3D2B2A and remains intentionally deferred. Do not substitute the historical bridge for the current one.

---

## 6. FCF-for-SHL identity (Oborovo)

The CF waterfall is:

```
CF!row79  (base CFADS / FCF for banks)
  +
CF!row80  (signed actual Senior Debt Service, negative cash outflow)
  +
CF!row92  (DSRA movement, = 0 for Oborovo since DSRA inactive)
  =
CF!row94  (FCF after senior debt service)
  → gates / junior / SHL cash  →
CF!row112 (FCF for SHL)
```

DSRA is inactive (`Inputs!I348=0`, all DSRA rows zero). Therefore CF!row92 = 0, and:

```
FCF_for_SHL ≈ CF!row79 + CF!row80
            = base_CFADS + signed_actual_SDS   (signed_actual_SDS < 0)
```

This identity holds period by period when DSRA=0.  Verified from source fixture:
`cf["fcf_for_banks_keur"][t] + cf["senior_debt_service_keur"][t] ≈ cf["free_cash_flow_for_shl_keur"][t]`
with delta < 1e-9 kEUR for all operating periods.

**Important**: Do NOT substitute DS!row23 for CF!row80 in this identity.
- **DS!row23** = `(bank_cfads / target_DSCR + DSRA_adj) × ops_flag × tranche_flag` — a POSITIVE
  allowed debt-service capacity used in sculpting. It is not the signed cash-flow SDS row.
- **CF!row80** = signed actual Senior Debt Service — a NEGATIVE cash outflow. This is the
  correct term in the FCF waterfall identity.

When DSRA=0, `|CF!row80| = DS!row23` in magnitude (because the allowed capacity is fully drawn),
but the signs differ. Using DS!row23 in place of CF!row80 would produce
`FCF_for_SHL = CF79 + positive_DS23 > CF79`, which is incorrect.

| Row | Field in fixture | Sign | Role |
|---|---|---|---|
| CF!row79 | `cf["fcf_for_banks_keur"]` | positive | Base CFADS |
| CF!row80 | `cf["senior_debt_service_keur"]` | **negative** | Signed actual SDS (CF waterfall) |
| DS!row23 | `ds["sd_service_keur"]` | **positive** | Allowed SDS capacity (sizing input) |
| CF!row112 | `cf["free_cash_flow_for_shl_keur"]` | positive | FCF for SHL |

Classification: **FCF_FOR_SHL_LINEAGE_CF79_CF80_CF92_CF94_CF112_SOURCE_PROVEN**

---

## 7. DSRA classification (Oborovo)

| Item | Value | Status |
|---|---|---|
| Inputs!I348 (DSRA target) | 0 | SOURCE_PROVEN_VALUE |
| All DSRA rows | 0 all periods | SOURCE_PROVEN_VALUE |
| Fixture classification | ALIGNED_BOTH_ZERO | SOURCE_PROVEN_VALUE |
| Causal classification | **DSRA_NOT_CAUSAL_FOR_OBOROVO_CURRENT_RESIDUAL_SOURCE_PROVEN** | — |

---

## 8. TUHO cross-project bank-sizing proof (P50 / P90-10y)

### 8.1 Architecture

TUHO CF!row69 → TUHO base CFADS (P50 scenario)
TUHO Macro/VBA → bank CFADS (P90-10y, conservative production)
bank CFADS → DS → DSCR sculpting → Senior Debt

### 8.2 First operating period (2030-06-30)

| Item | Value | Status |
|---|---|---|
| CF.free_cash_flow_for_banks_keur (P50 base) | 3,070.175837370555 kEUR | SOURCE_PROVEN_VALUE |
| CF.senior_debt_service_keur (SDS) | −2,116.361394092063 kEUR | SOURCE_PROVEN_VALUE |
| DS.senior_debt_dscr_target | 1.2 | SOURCE_PROVEN_VALUE |
| CF.average_senior_dscr_period (base actual) | 1.451 | SOURCE_PROVEN_VALUE |

### 8.3 Bank CFADS derivation (SOURCE_DERIVED_IDENTITY)

```
bank_cfads[t] = |SDS[t]| × target_DSCR[t]
              = 2,116.361394092063 × 1.2
              = 2,539.633672910476 kEUR
```

This identity holds because `allowed_SDS = bank_cfads / target_DSCR` by DS!row23.

**Important**: this derives bank CFADS from SDS × DSCR. It does NOT extract Macro50
directly — the bank CFADS value here is SOURCE_DERIVED_IDENTITY, not a direct Macro50
extraction. Presenting it as a direct Macro50 read would be incorrect.

### 8.4 MINIMUM_BASE_CASE_DSCR_IS_OUTPUT_NOT_SIZING_INPUT

```
base_actual_DSCR = CF79 / |SDS| = 3,070.176 / 2,116.361 = 1.4507 ≈ 1.451
```

The 1.451 actual DSCR is an OUTPUT of operating under bank-sized debt (sized to P90-10y
conservative production / 1.2 target). It is not a second sizing input target.

---

## 9. Row39 classification

| Item | Value | Status |
|---|---|---|
| Source formula | `=MIN(G38, F35*B37)` | SOURCE_PROVEN_FORMULA |
| Forward tax state dependency | Row39 does NOT feed rows 36/37/38/41/43 | SOURCE_PROVEN_VALUE |
| Oborovo binding | Does not bind (GRID-ABCDE = GRID-ABCD, diff < 0.01 kEUR) | SOURCE_PROVEN_VALUE |
| Classification | **ROW39_REPORTING_OR_NON_CAUSAL_FOR_TAX_STATE_SOURCE_PROVEN** | — |
| GRID-E role | WITHIN_TAX_SURROGATE_ONLY — not a causal tax-state mechanic | — |

The synthetic `cumulative_used` propagation based on the row39 cap has been removed
from the diagnostic code. The `row39_cap` config flag is retained for source-replay
fixture validation only.

---

## 10. Tax window classification

| Item | Value | Status |
|---|---|---|
| Source formula | `SUMIF(last-B36-periods TI,"<0")` with B36=5 | SOURCE_PROVEN_FORMULA |
| Model period | Semiannual | SOURCE_PROVEN_VALUE |
| B36=5 meaning | 5 model periods = 2.5 calendar years | SOURCE_PROVEN_VALUE |
| Classification | WORKBOOK_5_MODEL_PERIOD_LOSS_WINDOW_KNOWN_SOURCE_BUG | — |
| Generic Finco target | 5-year date/vintage-based loss expiry | — |

The workbook uses B36=5 model periods; with semiannual periods this is 2.5-year lookback.
Do not promote this to generic Finco policy.

Construction-origin losses are included. `CONSTRUCTION_LOSS_ENTERING_OPERATION_SOURCE_PROVEN`.

---

## 11. Residual cause status

```
CURRENT_CAUSE_UNRESOLVED
CURRENT_GRID0_TO_SOURCE_DEBT_BRIDGE_NOT_YET_CLOSED
```

Confirmed non-causes for Oborovo:
- **DSRA**: DSRA_NOT_CAUSAL_FOR_OBOROVO_CURRENT_RESIDUAL_SOURCE_PROVEN
- **SHL feedback (Arm A)**: FIXED_POINT_COLLAPSES_ANALYTICALLY_TO_IDENTITY_FOR_OBOROVO
- **Row-39**: ROW39_REPORTING_OR_NON_CAUSAL_FOR_TAX_STATE_SOURCE_PROVEN

Remaining unranked candidates (unresolved):
1. Bank CFADS vs clean EBITDA-CFADS (Macro50 VBA, BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED)
2. Senior debt sizing gap: +1,066.754 kEUR (CURRENT_GRID0_TO_SOURCE_DEBT_BRIDGE_NOT_YET_CLOSED)
3. GRID-WS0 baseline gate (pending classification)

---

## 12. Fixture authority

| Fixture | Content |
|---|---|
| `tests/fixtures/excel_oborovo_financial_truth.json` | CF79/Macro50/DS vectors, DSCR, DSRA |
| `tests/fixtures/excel_oborovo_debt_interest_truth.json` | Row formulas, historical bridge, rate mismatch |
| `tests/fixtures/excel_tuho_full_model_extract.json` | TUHO CF/DS period vectors, DSCR proof |
