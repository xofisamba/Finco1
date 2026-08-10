# C3B3D2B1 — Production SHL Wiring + Instrument Day-Count Convention

**Status**: `C3B3D2B1_MERGED_PRODUCTION_SHL_FOUNDATION`
**Branch**: `stage-c3b3d2b1-shl-production-wiring`
**Base**: `2afdffbc1796d3b042f7b63c61c2750ec264924e` (main after C3B3D2B0 squash-merge)
**Scope boundary**: Production SHL schedule chaining + typed instrument day-count convention. Tax feedback loop (SHL→tax→CFADS→SHL) deferred to C3B3D2B2.

---

## 1. Scope

C3B3D2B1 delivers:

1. **`ShlDayCountConvention` typed enum** — instrument-level, independent of Senior Debt convention.
2. **`ShlWaterfallPolicy` dataclass** — `annual_rate` + `day_count_convention`.
3. **`compute_shl_dcf()` typed dispatch** — routes ACT_365_FIXED and ACT_360; delegates ACT_365_FIXED to governance-locked C3B3D2B0 function.
4. **`compute_shl_schedule()` production chainer** — links C3B3D1 construction (opening=0, draw, DCF=1.0, PIK) and C3B3D2B0 operating waterfall (natural formula, no mode dispatch) into a single call. Fails closed on rate mismatch between construction and operating policy, and on non-zero operating drawdown.
5. **`compute_shl_cash_from_phase2c()` seam adapter** — derives `candidate_cash_before_unresolved_reserve_adjustments` per period from Phase 2C result without reading any Excel fixture. Fails closed on missing CFADS entries and on period indices within the debt tenor that are absent from the senior debt schedule. DSRA ordering is `DSRA_ORDERING_UNRESOLVED`.
6. **125 test functions** covering conventions, parity, seam, governance, fail-closed alignment, parallel-vector length validation, rate consistency, real Phase2C integration with full deterministic diagnostic metrics (shared helper), and source vector identity.
7. **This reconciliation document**.

Not in scope: DSRA, distributions, Sponsor, R99/R102, SHL→tax fixed-point loop.

---

## 2. Source Inputs

| Input | Source | Classification |
|---|---|---|
| `shl_draw_keur` | D2A fixture workbook_inputs (Excel Inputs!D325) | SOURCE_RAW_CACHED_VALUE |
| `shl_annual_rate` | D2A fixture workbook_inputs (Excel Inputs!F328) | SOURCE_RAW_CACHED_VALUE |
| Period dates | `oborovo_interest_limitation_fixture.json` (committed) | SOURCE_RAW_CACHED_VALUE |
| `free_cash_flow_for_shl_keur` | `excel_oborovo_financial_truth.json` CF section | SOURCE_RAW_CACHED_VALUE (test oracle only) |

The `free_cash_flow_for_shl_keur` vector is used **only as a test oracle**. It is NOT a production input. The production derivation is `CFADS − senior_debt_service` via the seam adapter.

---

## 3. Day-Count Conventions

### 3.1 Instrument-Level Independence

Senior Debt and SHL are configured with **independent** typed conventions:

| Instrument | Convention | Location |
|---|---|---|
| Senior Debt | `DayCountConvention.ACT_365` / `ACT_360` | `SeniorDebtPolicy.day_count_convention` |
| SHL | `ShlDayCountConvention.ACT_365_FIXED` / `ACT_360` | `ShlWaterfallPolicy.day_count_convention` |

These are distinct Python enum types. Changing one does not affect the other. A project can simultaneously have Senior Debt = ACT/360 and SHL = ACT/365 Fixed (Oborovo).

### 3.2 Date Interval Semantics Differ

**Do NOT unify Senior Debt and SHL DCF implementations.**

| Dimension | Senior Debt | SHL |
|---|---|---|
| End-date treatment | EXCLUSIVE (= start of next period) | INCLUSIVE (= last calendar day of period) |
| Formula | `(end − start).days / denominator` | `((end − start).days + 1) / denominator` |
| DS[1] days | 183 | 184 |
| DS[1] DCF (365 basis) | 183/365 = 0.50137 | 184/365 = 0.50411 |

The D2A fixture documents this explicitly: `SHL_SOURCE_DAY_COUNT_MISMATCH` — two different day-count bases in the same Oborovo workbook. Do not unify.

### 3.3 SHL Conventions

**ACT_365_FIXED**: `SOURCE_PROVEN_FOR_OBOROVO_OPERATING_SHL`

```
day_count_fraction = ((period_end − period_start).days + 1) / 365
```

Denominator always 365, even in leap years. Proven in C3B3D2B0 across all 40 Oborovo operating periods including 5 leap-year periods (DS[4, 12, 20, 28, 36]). Max source-oracle delta: 1.11e-16 (machine epsilon).

**ACT_360**: `GENERIC_ENGINE_CAPABILITY`

```
day_count_fraction = ((period_end − period_start).days + 1) / 360
```

Same inclusive end-date semantics. Denominator 360. No Oborovo SHL source evidence. Not labelled source-proven.

---

## 4. Construction DCF Evidence Limitation

Construction `DCF = 1.0` remains:

- **ARITHMETIC_SOURCE_IMPLIED**: `gross / (draw × rate) = 1169.661912 / (14620.773895 × 0.08) = 1.0`
- **CALENDAR_CONVENTION_UNRESOLVED**: Exact calendar interval unconfirmed. Potential 2-day gap at construction/operating seam (`cf.bop_date[0]=2029-06-29`, `cf.eop_date[0]=2030-06-30`, `IL DS[1].start=2030-07-01`).

Do NOT infer ACT_365 or ACT_360 from operating periods for construction. The `ShlConstructionInput.dcf` field defaults to 1.0 and must not be overridden without calendar-date proof.

---

## 5. Production Input Lineage

### Cash Available for SHL

Production lineage:

```
Revenue
OPEX
EBITDA = Revenue − OPEX
− cash_tax                    → CFADS  (pre-debt)
− senior_interest             ↘
− senior_principal            → candidate_cash_before_unresolved_reserve_adjustments
− shl_cash_interest           ↘  [DSRA_ORDERING_UNRESOLVED — position of DSRA
− shl_principal_repayment     →   relative to SHL not source-proven in C3B3D2B1]
[DSRA — DSRA_ORDERING_UNRESOLVED, not modelled in C3B3D2B1]
[distributions — not modelled in C3B3D2B1]
```

Formula: `candidate_cash_before_unresolved_reserve_adjustments[p] = max(0, CFADS[p] − senior_debt_service[p])`

- Construction period: 0.0 (SHL is PIK)
- Post-maturity periods (senior_ds = 0): CFADS
- DSRA_ORDERING_UNRESOLVED: whether DSRA is deducted before or after SHL is not source-proven; seam output is a candidate cash figure pending resolution.

Implemented in: `financial_engine.adapters.shl_cash_seam.compute_shl_cash_from_phase2c()`

### Oborovo Verification (DS[1])

```
CFADS[1]    = 2575.00 kEUR
senior_ds[1] = 2239.13 kEUR
cash_for_shl[1] = 335.87 kEUR  ✓ (matches fixture)
```

---

## 6. Tax Interaction

SHL gross accrued interest is deductible (subject to `TaxPolicy.shl_deductibility_mode` per C3B3C contracts). The `PeriodInterestInput.shl_interest_keur` field already exists in the clean tax engine.

**In C3B3D2B1**, SHL interest is NOT fed back into the Phase 2C fixed-point loop. This approximation is documented as `SHL_OUTSIDE_FIXED_POINT`.

Approximation magnitude: `≈ shl_gross_interest × tax_rate` per period. For Oborovo DS[1]: `636.81 × 0.19 ≈ 121 kEUR` tax reduction, which reduces cash_tax by ~121 kEUR, increasing CFADS by ~121 kEUR. The senior debt fixed-point was computed without this, so the senior debt schedule is based on a CFADS that is ~121 kEUR lower than fully-correct. This approximation does not affect the SHL schedule produced in C3B3D2B1 (SHL uses the Phase 2C CFADS − senior_ds, which is already converged without SHL interest correction).

Full SHL→tax circular resolution is deferred to C3B3D2B2.

---

## 7. Fixed-Point Boundary

| What | Inside fixed point? |
|---|---|
| Senior interest → tax → CFADS → senior debt sizing | **Yes** (Phase 2C solver) |
| SHL gross interest → tax | **No** (C3B3D2B1: SHL_OUTSIDE_FIXED_POINT) |
| SHL cash service → cash_available_for_shl | **Downstream** (post-convergence) |
| DSRA → cash_available_for_shl | **Not modelled** (C3B3D2B2+) |

---

## 8. Parity Results

### Construction Period

| Field | Source | Computed | Delta |
|---|---|---|---|
| opening_balance_keur | 0.000000 | 0.000000 | 0.000000 |
| drawdown_keur | 14620.773895 | 14620.773895 | — |
| gross_accrued_interest_keur | 1169.661912 | 1169.661912 | < 1e-6 |
| pik_interest_keur | 1169.661912 | 1169.661912 | < 1e-6 |
| closing_balance_keur | 15790.435806 | 15790.435806 | < 1e-6 |

**Construction DCF = 1.0**: arithmetic-implied (calendar convention unresolved).

### Operating Periods (40 periods)

| Vector | Max delta (kEUR) |
|---|---|
| gross_accrued_interest_keur | 2.27e-13 |
| cash_interest_keur | 2.27e-13 |
| pik_interest_keur | 2.27e-13 |
| principal_repaid_keur | 3.64e-12 |
| closing_balance_keur | 3.64e-12 |

DS[40] closing balance: **0.000000 kEUR**
First principal sweep: **DS[25]** (discovered from cash > gross; not hardcoded)

---

## 9. Test Suite

**File**: `tests/test_stage_c3b3d2b1_shl_production_wiring.py`
**Count**: 125 test functions, 125 collected cases, all passing (R3)

| Class | Tests | Description |
|---|---|---|
| TestA_ShlDayCountConventionContract | 6 | Enum exists, correct values, independent of Senior Debt |
| TestB_ShlWaterfallPolicyContract | 8 | Policy dataclass, frozen, validation |
| TestC_ComputeShlDcfAct365Fixed | 5 | DS[1] value, governance-locked delegate, all 40 Oborovo DCFs |
| TestD_ComputeShlDcfAct360 | 5 | ACT/360 value, differs from ACT/365, typed convention |
| TestE_LeapYearDenominator365 | 3 | Denominator 365 in all 5 leap periods; ACT/360 uses 360 |
| TestF_InstrumentConventionIndependence | 5 | SHL and Senior Debt conventions independent; exclusive vs inclusive |
| TestG_ConstructionPeriodSemantics | 8 | opening=0, draw, PIK, DCF=1.0 arithmetic-implied |
| TestH_OperatingChainRollForward | 6 | First operating opening = construction closing; roll-forward identity |
| TestI_OborovoConstructionParity | 5 | All construction fields match D2A fixture |
| TestJ_OborovoOperatingParity (SHL_FORMULA_PARITY_WITH_SOURCE_CASH_ORACLE) | 8 | All 40 operating periods match D2A fixture < 1e-6 kEUR; source cash as oracle |
| TestK_ShlCashSeamAdapter | 7 | Cash derivation from Phase 2C result; construction=0; DS[1] lineage |
| TestK2_SeamFailClosed | 5 | Missing CFADS, duplicate indices, within-tenor gap, post-maturity 0.0 |
| TestK2 additions (R2) | +2 | Parallel-vector length mismatch (CFADS and SD) |
| TestK3_RateConsistency | 2 | Rate mismatch raises; matching rate accepted |
| TestK4_OperatingDrawdownGuard | 2 | Non-zero drawdown raises; zero accepted |
| TestL_CashWaterfallOrdering | 3 | CFADS-senior_ds in docstring; DSRA_ORDERING_UNRESOLVED; no fixture reads |
| TestM_FixedPointBoundary | 5 | SHL outside Phase 2C loop; separate vectors; tax doc |
| TestN_SeparateVectors | 5 | gross≠cash in partial periods; pik=gross-cash; service=cash+principal |
| TestO_Governance | 11 | No 13547.2; no DS25/DS40 bounds; no project dispatch; no finco_core imports |
| TestP_RealPhase2CIntegration (CURRENT_UPSTREAM_CLEAN_CASH_RESIDUAL) | 10 | Real Oborovo Phase2C → seam → SHL; deterministic upstream + SHL metrics |
| TestQ_SourceVectorIdentity (SOURCE_VECTOR_IDENTITY_FOR_OBOROVO) | 3 | CFADS−sd≈FCF_for_SHL from source fixture |
| TestR_ReproducibleResidualMetrics | 9 | Shared helper; all 5 SHL residual metrics; structural assertions only |

---

## 10. Provenance Classification

### PROVEN (SOURCE_PROVEN)

| Item | Evidence |
|---|---|
| SHL inclusive end-date: `((end-start).days + 1)` | C3B3D2B0: 40 Oborovo periods, max delta 1.11e-16 |
| ACT_365_FIXED convention for Oborovo SHL | C3B3D2B0: SOURCE_PROVEN_FOR_OBOROVO_OPERATING_SHL |
| Construction DCF=1.0 arithmetic identity | `gross / (draw × rate) = 1.0`; calendar convention UNRESOLVED |
| Oborovo construction parity | TestI: all fields < 1e-6 kEUR |
| Oborovo operating SHL formula parity | TestJ: SHL_FORMULA_PARITY_WITH_SOURCE_CASH_ORACLE (source cash as waterfall driver) |
| Source vector identity: CFADS − senior_ds = FCF_for_SHL | TestQ: SOURCE_VECTOR_IDENTITY_FOR_OBOROVO; max delta < 0.01 kEUR |

### CLEAN PRODUCTION CANDIDATE (EXPECTED_PRE_D2B2_UPSTREAM_CLEAN_CASH_RESIDUAL)

| Item | Status | Note |
|---|---|---|
| Clean engine CFADS for Oborovo | CLEAN_PRODUCTION_CANDIDATE | Differs from source by WORKBOOK_PERIODISATION_MISMATCH (C3B3B) |
| Clean engine senior_ds for Oborovo | CLEAN_PRODUCTION_CANDIDATE | Clean debt 43,919 vs source 42,852 kEUR (C3B3B) |
| Resulting clean candidate cash | CLEAN_PRODUCTION_CANDIDATE | Residual labelled EXPECTED_PRE_D2B2_UPSTREAM_CLEAN_CASH_RESIDUAL |
| Full SHL schedule from clean Phase2C | CLEAN_PRODUCTION_CANDIDATE | SHL arithmetic proven; cash driver is clean engine, not source |

#### R2 Diagnostic Metrics — Real Clean Phase2C → SHL (DS[1..40] comparison)

These residuals are **not calibration targets**. They are `CURRENT_UPSTREAM_CLEAN_CASH_RESIDUAL` —
causal attribution deferred to C3B3D2B2/DGRID. `WORKBOOK_PERIODISATION_MISMATCH` and
`SHL_OUTSIDE_FIXED_POINT` are known candidate contributors; their individual attribution is not yet proven.

```
REAL CLEAN PHASE2C → SHL DIAGNOSTIC (DS[1..40], signs normalised to positive outflow)

Upstream cash residuals:
  CFADS                         max abs delta:   339.71 kEUR    signed total: +347.11 kEUR
  Senior Debt Service           max abs delta:   667.86 kEUR    signed total: +2242.03 kEUR
  Candidate cash for SHL        max abs delta:   622.69 kEUR    signed total: -1894.91 kEUR

SHL schedule residuals (clean cash driver vs D2A source oracle):
  gross_accrued_interest        max abs delta:   139.17 kEUR
  cash_interest                 max abs delta:   366.82 kEUR
  pik_interest                  max abs delta:   401.37 kEUR
  principal_repaid              max abs delta:   790.19 kEUR
  closing_balance               max abs delta:  3508.20 kEUR

Final balance:
  clean DS[40] closing:    2718.02 kEUR   (EXPECTED_PRE_D2B2_UPSTREAM_CLEAN_CASH_RESIDUAL)
  source DS[40] closing:      0.00 kEUR
  delta:                   2718.02 kEUR
```

The non-zero final closing balance is **diagnostic evidence for D2B2/DGRID**, not a formula failure.
SHL arithmetic is separately source-proven via TestJ (SHL_FORMULA_PARITY_WITH_SOURCE_CASH_ORACLE).

### UNRESOLVED

| Item | Status |
|---|---|
| DSRA waterfall position relative to SHL | `DSRA_ORDERING_UNRESOLVED` |
| Construction calendar convention | `CALENDAR_CONVENTION_UNRESOLVED` — DCF=1.0 arithmetic-implied only |
| SHL→tax→CFADS→SHL feedback loop | `SHL_OUTSIDE_FIXED_POINT` — deferred to C3B3D2B2 |
| ACT/360 SHL convention source proof | `GENERIC_ENGINE_CAPABILITY` only; no Oborovo source evidence |

---

## 11. Unresolved Items (Deferred to C3B3D2B2+)

| Item | Status |
|---|---|
| CONSTRUCTION_DATE_CONVENTION_UNRESOLVED | DCF=1.0 arithmetic-implied; calendar proof deferred |
| SHL_OUTSIDE_FIXED_POINT | SHL→tax→CFADS→SHL circular dependency documented; resolution deferred to C3B3D2B2 |
| SHL_INTEREST_NOT_FED_INTO_TAX | PeriodInterestInput.shl_interest_keur remains 0 in Phase 2C; deferred |
| DSRA_NOT_MODELLED + DSRA_ORDERING_UNRESOLVED | DSRA position relative to SHL is not source-proven; not modelled in C3B3D2B1 |
| DISTRIBUTIONS_NOT_MODELLED | Deferred |
| ACT_360_SHL_NOT_SOURCE_PROVEN | ACT/360 for SHL is generic capability only; Oborovo uses ACT/365 Fixed |

---

## 12. D2B2 Prerequisites

A. Wire `shl_interest_keur` into `PeriodInterestInput` in the Phase 2C solver callback (adds SHL to the tax fixed-point loop).

B. Prove whether the resulting CFADS change materially affects senior debt sizing (if below convergence tolerance, document as within tolerance; otherwise expand the fixed-point to 2D).

C. Resolve construction calendar convention (is DCF=1.0 from exact 365-day interval?).

D. Resolve the source-proven ordering of DSRA/reserve movements relative to Senior Debt, SHL and distributions before wiring reserve-account cash movements into the clean waterfall.

---

## 13. SHL Input Authority Boundary

**Status**: `CLEAN_SHL_PROJECT_INPUT_AUTHORITY_HANDOFF_PENDING_D2B2`

The legacy factory `create_default_oborovo()` sets `shl_amount_keur=13547.2`. This value is a known source conflict and is **not the authoritative SHL draw for the clean engine**. The authoritative source draw is `14,620.773894815633 kEUR` (Excel Inputs!D325, cached in the D2A fixture).

The value `13,547.2` MUST NOT appear in any clean SHL calculation logic, fallbacks, or defaults in C3B3D2B2+.

The clean SHL input path (ProjectInputs → typed adapter → `ShlConstructionInput` / `ShlWaterfallPolicy`) has NOT been promoted in C3B3D2B1. Before SHL interest is wired into the Tax/CFADS fixed-point loop in C3B3D2B2, an explicit typed project-input adapter must obtain the authoritative SHL draw and rate from a source-proven path — not from the legacy `shl_amount_keur` field.

| Field | Authoritative source value | Legacy factory value (do not use) |
|---|---|---|
| `draw_keur` | 14,620.773894815633 kEUR (Inputs!D325) | 13,547.2 kEUR (`shl_amount_keur`) |
| `annual_rate` | 0.08 (Inputs!F328) | — |
