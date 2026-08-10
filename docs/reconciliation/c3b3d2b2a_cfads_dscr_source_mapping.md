# C3B3D2B2A — CFADS / DSCR / Senior Debt Source Mapping

**Stage**: C3B3D2B2A (R3)
**Status**: C3B3D2B2A_R3_SOURCE_CFADS_DSCR_MAPPING_READY_FOR_INDEPENDENT_REVIEW
**Authority**: Source fixture vectors; no production-engine modifications; no VBA reverse-engineering.

---

## 1. Purpose

This document is the **authoritative source mapping** for the two-layer CFADS
architecture used by the Finco financial model. It covers:

- Oborovo (primary case)
- TUHO (cross-project proof)

Evidence is classified per cell formula status:

| Label | Meaning |
|---|---|
| SOURCE_PROVEN_FORMULA | Formula text extracted from workbook; exact source |
| SOURCE_PROVEN_VALUE | Cached value extracted from workbook; formula not available |
| SOURCE_DERIVED_IDENTITY | Derivable from two other SOURCE_PROVEN quantities |
| VBA_IMPLEMENTATION_NOT_VISIBLE | Password-protected VBA; formula unknown |
| CFADS_ALIGNED_IN_THIS_SCENARIO | CF79 ≈ Macro50 within a specific scenario and DSCR band |
| TUHO_FORMULA_NOT_IN_CURRENT_FIXTURES | TUHO workbook row not yet extracted |

---

## 2. Two-layer CFADS architecture (Oborovo)

```
CF sheet                    Macro sheet               DS sheet
──────────────────────────────────────────────────────────────
CF!row79 (base CFADS)  ──►  Macro!row49 (input)
  =SUM(H23,H49,H73,         =CF!H79
  H76,H77)+B80*(H4=0)
                            Macro!row50 (output)  ──►  DS!row20 (bank CFADS)
                              VBA (not visible)          =Macro!H50

                                                   ──►  DS!row22 (DSCR target)
                                                           =(B22*H15)+(H16*D22)+(H17*C22)

                                                   ──►  DS!row23 (allowed SDS)
                                                           =(H20/H22+SUM(CF!H83:H83))
                                                              *H9*B23

                                                   ──►  DS!row47 (backward PV capacity)
                                                           =(H46+I47)/
                                                              (1+H44*(1+B54/(1-B54))*H6)
                                                              [+ H82 refinancing]
```

### 2.1 CF!row79 — Base CFADS (free cash flow for banks)

| Item | Value | Status |
|---|---|---|
| Formula (period H) | `=SUM(H23,H49,H73,H76,H77)+$B$80*(H$4=0)` | SOURCE_PROVEN_FORMULA |
| Components | H23=revenues, H49=opex, H73=local taxes, H76=interest income, H77=CIT | SOURCE_PROVEN_FORMULA |
| Local taxes in Oborovo | CF!row73=0 all operational periods | SOURCE_PROVEN_VALUE |
| Interest income in Oborovo | CF!row76=0 all periods (DSRA absent) | SOURCE_PROVEN_VALUE |
| Construction period adj | `$B$80*(H$4=0)`: adds B80 in construction (H4=0) | SOURCE_PROVEN_FORMULA |

### 2.2 Macro!row49 — Input to bank-sizing VBA

| Item | Value | Status |
|---|---|---|
| Formula (period H) | `=CF!H79` | SOURCE_PROVEN_FORMULA |
| Interpretation | Macro row 49 formula-links to base CFADS | SOURCE_PROVEN_FORMULA |

### 2.3 Macro!row50 — Output of bank-sizing VBA

| Item | Value | Status |
|---|---|---|
| Formula | `None` (password-protected VBA) | VBA_IMPLEMENTATION_NOT_VISIBLE |
| Interpretation | Bank-sizing CFADS; VBA takes CF79 and applies sculpting constraints | VBA_IMPLEMENTATION_NOT_VISIBLE |
| Alignment in DSCR=1.15 periods | CF79 ≈ Macro50, max diff < 0.01 kEUR (periods 1–24) | CFADS_ALIGNED_IN_THIS_SCENARIO |
| Divergence in DSCR=1.35 periods | CF79 > Macro50 by 590–743 kEUR (periods 25–27); backward PV constraint binds | SOURCE_PROVEN_VALUE |
| Classification | CFADS_ALIGNED_IN_THIS_SCENARIO for DSCR=1.15 band | — |

**CFADS_ALIGNED_IN_THIS_SCENARIO** applies to periods 1–24 (DSCR=1.15 band),
where CF79 and Macro50 differ by < 0.01 kEUR. This holds because: CF!row73=0,
CF!row76=0, DSRA=0, production scenario = P50 for both base and bank sizing.
At DSCR=1.35 periods (25–27), the backward PV sculpting constrains bank CFADS
below CF79.

### 2.4 DS!row20 — Bank CFADS entering debt service

| Item | Value | Status |
|---|---|---|
| Formula (period H) | `=Macro!H50` | SOURCE_PROVEN_FORMULA |
| Interpretation | DS row 20 sources from Macro row 50 output | SOURCE_PROVEN_FORMULA |

### 2.5 DS!row22 — DSCR target

| Item | Value | Status |
|---|---|---|
| Formula (period H) | `=($B$22*H15)+(H16*$D$22)+(H17*$C$22)` | SOURCE_PROVEN_FORMULA |
| Interpretation | Weighted sum: base DSCR (B22), band2 (D22), band3 (C22) by flag cells | SOURCE_PROVEN_FORMULA |
| B22 (base DSCR) | 1.15 (periods 1–24) | SOURCE_PROVEN_VALUE |
| D22 (band2 DSCR) | 1.35 (periods 25–28) | SOURCE_PROVEN_VALUE |
| Transition | Period 25 (index 25 in 0-based fixture) | SOURCE_PROVEN_VALUE |

### 2.6 DS!row23 — Allowed senior debt service

| Item | Value | Status |
|---|---|---|
| Formula (period H) | `=(H20/H22+SUM(CF!H83:H83))*H9*$B23` | SOURCE_PROVEN_FORMULA |
| Interpretation | `(bank_cfads/target_dscr + DSRA_adj) × ops_flag × tranche_flag` | SOURCE_PROVEN_FORMULA |
| DSRA adj for Oborovo | SUM(CF!H83:H83)=0 (DSRA inactive) | SOURCE_PROVEN_VALUE |
| Identity | `allowed_SDS = bank_cfads / target_DSCR` (when DSRA=0, ops_flag=1) | SOURCE_DERIVED_IDENTITY |

### 2.7 DS!row47 — Backward PV debt capacity

| Item | Value | Status |
|---|---|---|
| Formula (period H) | `=SUM(IF(NOT(H7),(H46+I47)/(1+H44*(1+$B54/(1-$B$54))*H$6),0),H82)` | SOURCE_PROVEN_FORMULA |
| Simplified (WHT=0, no refinancing) | `(allowed_SDS[t] + debt[t+1]) / (1 + rate[t] × dayfrac[t])` | SOURCE_DERIVED_IDENTITY |
| B54 (WHT) | 0 (Inputs confirmed) | SOURCE_PROVEN_VALUE |

---

## 3. Oborovo initial debt sizing

| Item | Value | Status |
|---|---|---|
| Source total senior debt | 42,852.279 kEUR | SOURCE_PROVEN_VALUE |
| Backward PV capacity (G4 vector) | 42,852.279 kEUR | SOURCE_DERIVED_IDENTITY |
| Residual (G4 − source) | 0.000 kEUR | SOURCE_DERIVED_IDENTITY |

### 3.1 Causal bridge: Phase2C clean → source debt

The Phase2C clean engine produces 46,053.402 kEUR (vs source 42,852.279 kEUR,
delta = +3,201.124 kEUR). The full gap is explained by four source-proven
INPUT_POLICY_MISMATCH factors:

| Step | Case | kEUR | Delta | Driver |
|---|---|---|---|---|
| G0 | Phase2C clean engine | 46,053.402 | — | Baseline |
| G1 | + Excel sculpting rates | 45,509.595 | −543.807 | Rate: 5.65% flat vs blended 5.9514% |
| G2 | + Excel bank CFADS (Macro50) | 43,591.559 | −1,918.036 | CFADS: Phase2C EBITDA-based vs Macro50 |
| G3 | + ACT/360 day-count | 43,376.955 | −214.604 | Day-count: ACT/365 vs ACT/360 |
| G3A | + Scalar backward PV | 43,368.224 | −8.732 | Terminal partial period (ops_flag effect) |
| G4 | + Vector DSCR banding | 42,852.279 | −515.945 | DSCR 1.35 at periods 25–28 |
| Source | Excel workbook | 42,852.279 | 0.000 | Bridge closed |

`bridge_closed_to_vector = True` — G4 vector backward induction reproduces source debt exactly (residual = 0.000 kEUR).

**Rate mismatch detail** (DS!row44, period 1):
- Source: blended annual sculpting rate ≈ 5.9514% (`float × 0.20 + fixed × 0.80 + margin`)
- Phase2C: 5.65% flat
- Classification: INPUT_POLICY_MISMATCH — the clean engine uses a different rate assumption

---

## 4. FCF-for-SHL identity proof (Oborovo)

DSRA is inactive for Oborovo (`Inputs!I348=0`, all DS DSRA rows = 0). Therefore:

```
FCF_for_SHL = base_FCF_for_banks + signed_SDS
            = CF!row79 + DS!row23
```

where `signed_SDS < 0` (cash outflow from project). This identity is exact when
DSRA=0 and holds period by period.

---

## 5. DSRA classification (Oborovo)

| Item | Value | Status |
|---|---|---|
| Inputs!I348 (DSRA target) | 0 | SOURCE_PROVEN_VALUE |
| All DSRA rows (CF!H83:H83) | 0.000 for all periods | SOURCE_PROVEN_VALUE |
| target_is_zero | True | SOURCE_PROVEN_VALUE |
| Fixture classification | ALIGNED_BOTH_ZERO | SOURCE_PROVEN_VALUE |
| Causal classification | **DSRA_NOT_CAUSAL_FOR_OBOROVO_CURRENT_RESIDUAL_SOURCE_PROVEN** | — |

DSRA is not a candidate for explaining the CURRENT_UPSTREAM_CLEAN_CASH_RESIDUAL
for Oborovo. Both the target and actual DSRA are zero in the source workbook.
DSRA_ORDERING_UNRESOLVED is therefore resolved for Oborovo and cannot be cited
as a contributor.

---

## 6. TUHO cross-project bank-sizing proof

TUHO uses a two-scenario approach: P50 (base) for CF79 and P90-10y (conservative)
for bank sizing. This produces an observable DSCR spread.

### 6.1 First operating period (period index 0 in TUHO fixture, date 2030-06-30)

| Item | Value | Status |
|---|---|---|
| CF.free_cash_flow_for_banks_keur (base/P50) | 3,070.175837370555 kEUR | SOURCE_PROVEN_VALUE |
| CF.senior_debt_service_keur (SDS) | −2,116.361394092063 kEUR | SOURCE_PROVEN_VALUE |
| DS.senior_debt_dscr_target | 1.2 | SOURCE_PROVEN_VALUE |
| CF.average_senior_dscr_period (base actual DSCR) | 1.451 | SOURCE_PROVEN_VALUE |

### 6.2 Bank CFADS derivation (SOURCE_DERIVED_IDENTITY)

```
bank_cfads[t] = |SDS[t]| × target_DSCR[t]
              = 2,116.361394092063 × 1.2
              = 2,539.633672910476 kEUR
```

### 6.3 Base actual DSCR verification

```
base_actual_DSCR[t] = CF79[t] / |SDS[t]|
                    = 3,070.175837370555 / 2,116.361394092063
                    = 1.4507 (≈ 1.451 source)
```

### 6.4 Interpretation

The base actual DSCR (1.451) > target bank DSCR (1.2) because:
- Bank sizing uses conservative P90-10y CFADS (bank_cfads ≈ 2,539.634 kEUR)
- Base monitoring uses P50 CFADS (3,070.176 kEUR, higher production)
- MINIMUM_BASE_CASE_DSCR_IS_OUTPUT_NOT_SIZING_INPUT: the 1.451 is an output
  of operating under bank-sized debt, not a second input target

---

## 7. Tax window classification

### 7.1 5-period rolling loss window (D mechanic)

| Item | Value | Status |
|---|---|---|
| Source formula | `SUMIF(last-B36-periods TI,"<0")` with B36=5 | SOURCE_PROVEN_FORMULA |
| Model period | Semestrial (semiannual) | SOURCE_PROVEN_VALUE |
| B36=5 meaning | 5 **model periods** = 2.5 calendar years | SOURCE_PROVEN_VALUE |
| Classification | WORKBOOK_5_MODEL_PERIOD_LOSS_WINDOW_KNOWN_SOURCE_BUG | — |

The source workbook uses B36=5 model periods for the rolling loss window. With
semiannual periods, this means a 2.5-year lookback, not a 5-year lookback as
might be intended. This is a known source model characteristic, not a clean-engine
defect.

### 7.2 Row-39 carriable-loss cap

| Item | Value | Status |
|---|---|---|
| Source formula | `=MIN(G38,F35*B37)` | SOURCE_PROVEN_FORMULA |
| Oborovo result | Cap does not bind (GRID-ABCDE = GRID-ABCD, diff < 0.01 kEUR) | SOURCE_PROVEN_VALUE |
| Classification | ROW39_CAP_NON_BINDING_FOR_OBOROVO | — |

### 7.3 Construction loss entering operation

| Item | Value | Status |
|---|---|---|
| Mechanic | Construction-period TI loss carried to first operating period | SOURCE_PROVEN_FORMULA |
| Effect | Reduces first-operating-period CIT, affecting CFADS | SOURCE_DERIVED_IDENTITY |
| Classification | CONSTRUCTION_LOSS_ENTERING_OPERATION_SOURCE_PROVEN | — |

---

## 8. Residual cause status

```
CURRENT_CAUSE_UNRESOLVED
```

The CURRENT_UPSTREAM_CLEAN_CASH_RESIDUAL (2,718.02 kEUR DS[40]) is not yet
causally attributed. Confirmed non-causes for Oborovo:

- **DSRA**: DSRA_NOT_CAUSAL_FOR_OBOROVO_CURRENT_RESIDUAL_SOURCE_PROVEN (DSRA=0)
- **SHL feedback (Arm A)**: FIXED_POINT_COLLAPSES_ANALYTICALLY_TO_IDENTITY_FOR_OBOROVO (net TI=0)
- **Row-39 cap**: ROW39_CAP_NON_BINDING_FOR_OBOROVO (cap does not bind)

Remaining unranked candidates:
1. CFADS composition (clean engine EBITDA-based vs Macro50 VBA)
2. Senior debt sizing gap (+1,067 kEUR clean vs source)
3. GRID-WS0 baseline gate (pending classification)

---

## 9. Fixture authority

| Fixture | Version | Content |
|---|---|---|
| `tests/fixtures/excel_oborovo_financial_truth.json` | extractor 3.4.0 | CF79/Macro50/DS vectors, DSCR, DSRA |
| `tests/fixtures/excel_oborovo_debt_interest_truth.json` | workstream A–E | Row formulas, causal bridge, rate mismatch |
| `tests/fixtures/excel_tuho_full_model_extract.json` | period_diagnostics | TUHO CF/DS period vectors, DSCR proof |
