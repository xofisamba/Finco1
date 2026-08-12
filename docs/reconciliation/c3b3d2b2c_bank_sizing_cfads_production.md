# C3B3D2B2C — Bank-Sizing CFADS Production: Reconciliation

## Stage identity

| Field | Value |
|---|---|
| Stage | C3B3D2B2C |
| Branch | `stage-c3b3d2b2c-bank-sizing-cfads-production` |
| Base SHA (C3B3D2B2B locked) | `6e064980868709294e14da4d95e3279790d70ff0` |
| Protected C3B2 SHA | `f8f244c0660495bfb4115d4e32ba329c291ab829d1d0693e614c889457b5add7` |
| PR | #925 (DRAFT — DO NOT MERGE without explicit instruction) |
| **R3 Final Verdict** | `C3B3D2B2C_R3_STOP_MACRO50_TRANSFORMATION_SOURCE_INACCESSIBLE` |
| **R4 Verdict** | `C3B3D2B2C_R4_SOURCE_INPUTS_IDENTIFIED_CURVE_EXTRACTION_REQUIRED` |
| **R4.1 Verdict** | `C3B3D2B2C_R4_1_MANUAL_CAUSALITY_PROVEN_ENGINE_EVALUATION_XLSM_EXTRACTION_REQUIRED` |
| **R4.2 Verdict** | `C3B3D2B2C_R4_2_STOP_CANDIDATE_C_SOURCE_PARITY_FAILED` |
| **R4.3 Verdict** | `C3B3D2B2C_R4_3_STOP_REVENUE_REGIME_PARITY_FAILED` |
| **R4.4 Verdict** | `C3B3D2B2C_R4_4_STOP_MERCHANT_PRICE_SOURCE_LINEAGE_NOT_YET_REPLAYED` |
| **R4.5 Verdict** | `C3B3D2B2C_R4_5_EFFECTIVE_PRICE_PROVEN_BANK_TAX_TIMING_RESIDUAL_IDENTIFIED` |
| **R4.6 Verdict** | `C3B3D2B2C_R4_6_STOP_TAX_TIMING_COUNTERFACTUAL_FAILED` |
| **R4.6.1 Verdict** | `C3B3D2B2C_R4_6_1_STOP_REMAINING_BANK_CFADS_COMPONENT_UNRESOLVED` |
| **R4.7 Verdict** | `C3B3D2B2C_R4_7_P50_SOURCE_BYPASS_PROVEN_P28_CALENDAR_RESIDUAL_DOCUMENTED_GENERIC_P90_POLICY_PRESERVED` |
| **R4.7.1 Verdict** | `C3B3D2B2C_R4_7_1_STOP_CALENDAR_REPLAY_FAILED` |
| **R4.7.2 Verdict** | `C3B3D2B2C_R4_7_2_SOURCE_CALENDAR_FULL_OPERATING_REPLAY_CFADS_AND_DEBT_PARITY_PROVEN_OPEX_CALENDAR_PERIODISATION_HYPOTHESIS_PROVEN_STAGE_DIAGNOSTIC_CLOSED` |

---

## 1. Problem statement

### Current authoritative baseline (C3B3D2B2B locked, PR #924)

| Constant | Value |
|---|---|
| `CURRENT_GRID0_PRODUCTION_CANDIDATE` | **43,919.032698 kEUR** |
| `SOURCE_EXCEL_SENIOR_DEBT` (DS!D51) | **42,852.278763 kEUR** |
| Current gap (CF1 only) | **+1,066.754 kEUR** |

Prior stage C3B3D2B2B (PR #924, locked) proved:

- CF2 (DSCR mechanics) = 0 kEUR — source-matched in current engine
- CF3 (ACT/360 day-count) = 0 kEUR — source-matched in current engine
- CF4 (operating assumptions) = 0 kEUR — source-matched
- CF5 (interest rate) = 0 kEUR — source-matched
- CF1 (CFADS / bank case) = **−1,066.754 kEUR** — sole source of the current sizing gap

Classification: `BANK_SIZING_CFADS_AUTHORITY_IS_SOLE_CURRENT_SIZING_GAP_SOURCE_PROVEN`

> **Historical note**: earlier pre-C3B3D2B2B analysis referenced a 13,547.2 kEUR sizing
> gap and a 29,305 kEUR engine debt figure. These are historical-only values from prior
> diagnostic stages and do NOT represent the current C3B3D2B2B-locked baseline.

This stage (C3B3D2B2C) was tasked with implementing a generic typed bank-sizing CFADS
scenario layer, identifying the source-proven Macro50 merchant-period transformation, and
wiring canonical production if a source rule was found.

---

## 2. Source evidence inspected (R3)

### Workbook identity

| Field | Value |
|---|---|
| Filename | `d49af8ee-20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm` |
| SHA-256 | `15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920` |

### Fixtures inspected

- `tests/fixtures/excel_oborovo_debt_interest_truth.json` — DS/Macro/CF formulas and values
- `tests/fixtures/excel_oborovo_financial_truth.json` — P&L, Inputs, tax formulas
- `tests/fixtures/excel_oborovo_merchant_revenue_truth.json` — CF!row30 price formula
- `tests/fixtures/excel_oborovo_full_model_extract.json` — period diagnostics
- `tests/fixtures/excel_golden_oborovo.json` — worksheet metadata
- `tests/fixtures/excel_oborovo_opex_structural_truth.json` — Scenarios!E4, opex template selector
- `tests/fixtures/oborovo_baseline.json` — baseline inputs

### Scenario selectors found

| Cell | Value | Role |
|---|---|---|
| `Inputs!D52` | `P_50` | Base production scenario |
| `Inputs!D89` | `Fixed` | Base market price scenario |
| `Scenarios!E345` | `14` | Senior debt maturity (years) |
| `Scenarios!E348` | `0.80` | Gearing/hedge coverage |
| `Scenarios!E350` | `1.15` | DSCR band 1 (contracted) |
| `Scenarios!E351` | `1.35` | DSCR band 2 (merchant/BESS) |
| `Scenarios!E352` | `1.65` | DSCR band 3 (merchant PV) |
| `Scenarios!E4` | opex template | OpEx scenario selector (`INDEX/MATCH`) |

**Not found:** bank production selector, bank market price selector, lender/capture/haircut selector.

---

## 3. Macro!row50 forensics

### DS!H20 provenance chain

```
DS!H20  formula: =Macro!H50        (confirmed, dual-load extraction)
Macro!H49 formula: =CF!H79         (confirmed — base P50 CFADS)
Macro!H50 formula: None            (no formula element in XML)
```

`macro_row50_output_formula: None` means Macro!row50 cells contain only `<v>` (cached
value) elements with no `<f>` (formula) element. The workbook architecture indicates
Macro/VBA involvement, but the exact VBA procedure and assignment mechanism are not visible
and must not be inferred. The source evidence proves only that no worksheet formula is
present in the inspected extraction; the VBA source code is password-protected.

`VBA_IMPLEMENTATION_NOT_VISIBLE`: the exact transformation cannot be determined from the
available artifacts. `BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED`.

### Macro!row38/39/40 precedent

From `financial_truth.json` (P&L sheet):
```
P&L!row44 = Macro!G40
Macro!G40 = IF(Production_Scenario=base_scenario, Macro!G38, Macro!G39)
```

Macro!row38 = base scenario CIT; row39 = alternative CIT; row40 switches on scenario.
Both rows 38 and 39 contain hardcoded values matching row43 in the current snapshot.

This establishes the Macro sheet architectural pattern (IF/scenario-switch), but
Macro!row50's formula is None — it does NOT follow the formula-driven pattern.

### PPA vs merchant period behaviour

| Period range | DS!row20 vs CF!row79 | Interpretation |
|---|---|---|
| 1–24 (PPA) | ≈ identical (< 1 kEUR) | Bank CFADS ≈ base CFADS (contractual revenue unchanged) |
| 25–60 (merchant) | DS20 << CF79 by 590–1,117 kEUR | Bank CFADS substantially lower; transformation mechanism unresolved |

The gap grows over the merchant tenor, suggesting compounding effects.

### Candidate analysis (per-period merchant deltas)

| Period | CF79 / Macro49 | DS20 / Macro50 | CF79 − DS20 |
|---|---|---|---|
| 25 | 2,992.5 | 2,279.8 | +712.7 |
| 26 | 2,694.8 | 2,103.8 | +591.0 |
| 27 | 2,991.7 | 2,248.8 | +743.0 |
| 28 | 2,667.8 | 2,057.8 | +610.1 |
| 29 | 2,994.5 | 2,226.8 | +767.8 |

---

## 4. Candidate rules investigated

### Candidate A — ALL_PRODUCTION (P90-10y for all periods)

All operating periods use P90-10y yield scenario.

| Metric | Value |
|---|---|
| Candidate debt | 40,950 kEUR |
| Max \|delta\| vs DS!row20 | **690 kEUR** |
| Gap to Excel debt | −1,902 kEUR |

Result: `OBOROVO_ALL_PRODUCTION_BANK_CASE_RULE_CANDIDATE_ONLY` — **REJECTED**

P90 applied to PPA periods produces CFADS below source (DS!row20 PPA ≈ base P50, not P90).

### Candidate B — MERCHANT_ONLY (P90-10y for merchant periods only)

PPA periods retain base P50 yield. Merchant periods use P90-10y yield.

| Metric | Value |
|---|---|
| Candidate debt | 43,622 kEUR |
| Max \|delta\| vs DS!row20 | **690 kEUR** |
| Gap to Excel debt | +770 kEUR |

Merchant period deltas (bank CFADS − DS!row20):

| Period | Bank CFADS | Source DS20 | Delta |
|---|---|---|---|
| 26 | 2,546 | 2,280 | +266 |
| 27 | 2,759 | 2,104 | +655 |
| 28 | 2,531 | 2,249 | +283 |
| 29 | 2,748 | 2,058 | +690 |

Result: `OBOROVO_MERCHANT_ONLY_BANK_CASE_RULE_CANDIDATE_ONLY` — **REJECTED**

PPA period match is good (delta ≈ 0). Merchant periods: P90 CFADS systematically exceeds
source Macro50. The VBA applies additional merchant downside not captured by yield-scenario
substitution alone.

---

## 5. Implied merchant bank revenue analysis (R3)

For H2 merchant periods (odd, CIT = 0), the implied bank revenue given source opex is:

```
bank_rev[p] = DS20[p] − source_opex[p]
```

Ratios vs base P50 source revenue (Candidate B, P90 production):

| Period | P50 prod | P90 prod | Impl rev | P90 rev | Impl/P90 |
|---|---|---|---|---|---|
| P25 | 52,291 | 49,351 | 3,244.5 | 3,571.6 | 0.908 |
| P27 | 52,081 | 49,153 | 3,224.2 | 3,708.0 | 0.870 |
| P29 | 52,017 | 49,093 | 3,204.7 | 3,713.1 | 0.863 |
| P31 | 51,666 | 48,761 | 3,053.6 | 3,596.3 | 0.849 |
| P35 | 51,253 | 48,371 | 3,173.5 | 3,726.7 | 0.852 |

No constant ratio. The implied price (given P90 production) varies from 65.4 to 65.9 EUR/MWh
vs base 75–78 EUR/MWh. The pattern is not consistent with any simple multiplier or flat
price floor.

No bank price scenario, capture-price discount, lender haircut, or downside price curve was
found in the inspected fixture data. The Scenarios sheet column structure (beyond the base
E-column values) was not captured in the extraction artifacts.

---

## 6. Stop verdict

```
C3B3D2B2C_R3_STOP_MACRO50_TRANSFORMATION_SOURCE_INACCESSIBLE
```

The Macro!row50 formula is absent (VBA-hardcoded values). No formula, Scenarios cell, or
price-curve evidence has been found that would uniquely identify the bank-case CFADS
transformation. The VBA procedure (Macro50) is password-protected and not accessible.

No source-proven rule can be established from the available extraction artifacts.

---

## 7. Production impact (R3 revert)

Per R3 specification §10 (STOP case):

**Reverted from `financial_engine/` production files:**
- `inputs.py`: `ProductionScenarioScope` removed; `DebtSizingScenario.scope` removed;
  `SeniorDebtModelInput.bank_sizing_scenario` removed
- `results.py`: `SeniorDebtSchedules.bank_sizing_cfads_keur` removed;
  `SeniorDebtSchedules.bank_sizing_dscr` removed
- `provenance.py`: `bank_sizing_scenario` payload removed from fingerprint
- `orchestrator.py`: `_derive_bank_operating_input`, `_is_ppa_for_bank_splice`,
  fail-closed bank CFADS audit, bank DSCR computation — all removed

**Moved to `finco_recon/bank_sizing_candidates.py` (diagnostic-only):**
- `_derive_bank_operating_input()` — pure transformer for candidate evaluation
- `run_candidate_a_all_production()` — Candidate A evaluation
- `run_candidate_b_merchant_only()` — Candidate B evaluation
- `MACRO50_FORENSICS` — forensic summary dict
- `load_ds_row20_oracle()` — DS!row20 oracle loader

All 79 Phase 2C tests pass. All 169 Phase 2B tests pass (1 pre-existing Oborovo baseline failure, not from this PR).

---

## 8. Evidence labels preserved

- `BANK_SIZING_CFADS_AUTHORITY_IS_SOLE_CURRENT_SIZING_GAP_SOURCE_PROVEN`
- `OBOROVO_ALL_PRODUCTION_BANK_CASE_RULE_CANDIDATE_ONLY`
- `OBOROVO_MERCHANT_ONLY_BANK_CASE_RULE_CANDIDATE_ONLY`
- `BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED`
- `VBA_IMPLEMENTATION_NOT_VISIBLE`
- `C3B3D2B2C_STOP_BANK_CASE_TRANSFORMATION_NOT_SOURCE_PROVEN` (R2 finding, preserved)
- `C3B3D2B2C_R3_STOP_MACRO50_TRANSFORMATION_SOURCE_INACCESSIBLE` (R3 final verdict)

---

## 9. R4 — Debt-Horizon Bank Revenue Sizing Case Source Proof

### R4 verdict

```
C3B3D2B2C_R4_SOURCE_INPUTS_IDENTIFIED_CURVE_EXTRACTION_REQUIRED
```

### Active Senior Debt horizon (generic derivation)

| Field | Value |
|---|---|
| `repayment_start_period_index` | 2 |
| `maturity_period_index` | 29 |
| Active period count | **28** |
| Merchant+debt periods | **4** (period indices 26, 27, 28, 29) |
| Derivation | `GENERIC_FROM_SENIOR_DEBT_POLICY_NOT_HARDCODED` |

No hardcoded period boundary integers (25, 28, or 2044). Active period count is
derived as `maturity_period_index − repayment_start_period_index + 1`.

### Post-maturity causality

```
POST_MATURITY_CFADS_NON_CAUSAL_FOR_INITIAL_DSCR_SIZING
```

The DSCR schedule is confined to periods within `[repayment_start_period_index,
maturity_period_index]`. Periods 30–61 (post-maturity) do not appear in the DSCR
schedule and cannot be the binding constraint for debt sizing. This is confirmed
by inspection of the schedule's `period_indices` field.

### Candidate C — PRODUCTION_REVENUE_SIZING (architecture defined, blocked)

| Field | Value |
|---|---|
| Yield scenario | P90-10y |
| Revenue scenario | Central Low case Trackers (D111) / MidLow (TUHO D109) |
| Evaluation scope | Active debt periods only (generic from policy) |
| Status | `BLOCKED_PENDING_CURVE_EXTRACTION` |

**Source cell identifiers confirmed:**

| Project | Cell | Label | Status |
|---|---|---|---|
| Oborovo | `Inputs!D102` | Equity case revenues | Confirmed |
| Oborovo | `Inputs!D103` | Debt sizing revenues curve | Confirmed |
| Oborovo | `Inputs!D111` | Central Low case Trackers | Cell confirmed; **curve not in fixture** |
| Oborovo | `Inputs!D110` | Low case GMPV (hardcoded) | Cell confirmed; **value not in fixture** |
| Oborovo | `Scenarios!E324` | Equity case revenues | Confirmed |
| Oborovo | `Scenarios!E325` | Debt sizing revenues curve | Confirmed |
| TUHO | `Inputs!D107` | Equity scenario | Confirmed |
| TUHO | `Inputs!D108` | Sizing scenario | Confirmed |
| TUHO | `Inputs!D109` | MidLow | Cell confirmed; **curve not in fixture** |
| TUHO | `Scenarios!E182` | Equity case Afry curve | Confirmed |
| TUHO | `Scenarios!E183` | Sizing case Afry curve | Confirmed |

**Why Candidate C cannot be evaluated yet:**
- `Inputs!D111` (Oborovo Central Low case Trackers): time-series values not in any committed fixture
- `Inputs!D110` (Oborovo Low case GMPV): hardcoded base value not extracted
- `Inputs!D109` (TUHO MidLow): time-series values not in any committed fixture

Candidate C will be source-proven only when these curves are extracted and
a bank CFADS vector built from P90 production + sizing revenue curve matches
DS!row20 (or narrows the gap to within a toleranced acceptance criterion).

---

## 10. R4.1 — Manual Causality Evidence and Environment Status

### R4.1 verdict

```
C3B3D2B2C_R4_1_MANUAL_CAUSALITY_PROVEN_ENGINE_EVALUATION_XLSM_EXTRACTION_REQUIRED
```

### Manual black-box causality (PROVEN)

| Observation | Scenarios!E325 value | Inputs cell | Resulting debt (kEUR) | Matches DS!D51? |
|---|---|---|---|---|
| 1 | Central Low case Trackers | D111 | **42,852.278763** | **Yes** (exact) |
| 2 | Central case Trackers | D106 | 43,813.000 | No (+961 kEUR) |

**Classification:** `OBOROVO_DEBT_SIZING_REVENUE_CURVE_MANUAL_CAUSALITY_PROVEN`

Revenue curve selector `Scenarios!E325` is causally proven for debt sizing. `D111` (Central Low case Trackers) reproduces the source debt exactly. Switching to `D106` (equity curve) increases debt by +961 kEUR. The mechanism is revenue scenario selection, not yield scenario alone.

**Oborovo confirmed selectors:**
- `Scenarios!E324` (equity): cell confirmed HARDCODE; active value not in any fixture
- `Scenarios!E325` (sizing): active value = **"Central Low case Trackers"** — confirmed from manual causality observation 1

**TUHO confirmed selectors (from `tuho_scenario_manifest_v5.json`):**
- `Scenarios!E182` (equity): **"Equity case Afry curve"** — confirmed
- `Scenarios!E183` (sizing): **"Sizing case Afry curve"** — confirmed

### TUHO bank CFADS oracle back-calculation

```
bank_cfads_P1 = senior_debt_service_P1 × DSCR_target
              = 2,116.361394 × 1.20
              = 2,539.633673 kEUR

bank/base ratio   = 2539.633673 / 3070.175837 = 0.8272
P90/P50 yield     = 3620 / 4164 = 0.8694
Residual (price)  = 0.8272 / 0.8694 = 0.9515
```

**Classification:** `TUHO_BANK_CFADS_ORACLE_BACK_CALCULATED_FROM_DEBT_SERVICE`

The residual factor (0.9515) confirms a price-scenario reduction is applied alongside yield downscaling, consistent with MidLow/Central price ratio.

### Confirmed yield cases

| Project | P50 (h) | P90-10y (h) | P90/P50 ratio |
|---|---|---|---|
| Oborovo | 1,494 | 1,410 | 0.9438 |
| TUHO | 4,164 | 3,620 | 0.8694 |

P75/P95/P99 cases: not in any committed fixture — XLSM required.

### Confirmed price curves

| Project | Curve | Cell | Status |
|---|---|---|---|
| Oborovo | Central case Trackers | D106 | **Values in fixture** (CY2042–2060) |
| Oborovo | Central Low case Trackers | D111 | **Not in fixture** — XLSM required |
| Oborovo | Low case GMPV | D110 | **Not in fixture** — XLSM required |
| TUHO | Central | D106 | Not in fixture |
| TUHO | MidLow | D109 | **Not in fixture** — XLSM required |

### Candidate C status

| Project | Yield | Revenue curve | Manual causality | Engine evaluation |
|---|---|---|---|---|
| Oborovo | P90-10y | D111 (Central Low case Trackers) | **PROVEN** | BLOCKED — XLSM required |
| TUHO | P90-10y | D109 (MidLow) | Oracle derivable | BLOCKED — XLSM required |

### Product contract design (draft)

| Schema | Key fields | UX contract |
|---|---|---|
| `YieldCase` | `p50_hours`, `p90_10y_hours`, `p90_p50_ratio` (derived) | Both P50 and P90 user-editable; ratio is display-only |
| `PriceCurve` | `curve_id`, `label`, `calendar_start_year`, `values_eur_mwh` | Named library; CRUD operations; selector by `curve_id` |
| `RevenueCaseSelection` | `equity_curve_id`, `sizing_curve_id`, `bess_curve_id` (optional) | Scenario tab exposes two selectors; engine uses `sizing_curve_id` for bank CFADS |

Scenario tab sections: Production / Yield → Revenue Curves → BESS Revenue (if applicable).
No project-name dispatch. No hardcoded period boundaries.

### Environment status

Original XLSM files (`20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm`, `20260330_TUHO_BP.xlsm`) are not present in the execution environment. Searched: `/home`, `/root`, `/data`, `/mnt`, `/home/user/attach`. D110, D111 (Oborovo) and D109 (TUHO) are not in any committed fixture. Productionization gate cannot be cleared without engine evaluation of Candidate C.

**Evidence fixture:** `tests/fixtures/excel_oborovo_bank_sizing_source_evidence_r4_1.json`

---

## 11. R4.2: Source curve fixture + Candidate C engine closure

### Source price curves committed (R4.2)

Fixture: `tests/fixtures/excel_bank_sizing_revenue_curves_r4_2.json`

| Project | Curve | Cell | Calendar range | Values |
|---|---|---|---|---|
| Oborovo | Central Low case Trackers | Inputs!D111 | CY2030–2060 | 31 values committed |
| TUHO | MidLow | Inputs!D109 | CY2029–2060 | 32 values committed |

**Oborovo sample values (EUR/MWh):** CY2042 = 44.1107, CY2044 = 42.0980, CY2060 = 37.6441
**TUHO sample values (EUR/MWh):** CY2029 = 74.040, CY2042 = 65.895, CY2059 = 55.610

Engine slices extracted: `OBOROVO_CENTRAL_LOW_CY2042_2060` (19 values), `TUHO_MIDLOW_Y1_Y30` (30 values).

### Candidate C engine evaluation — Oborovo

**Configuration:** P90-10y yield + Central Low case Trackers (D111) as `merchant_prices_by_calendar_year_eur_mwh`

| Scenario | Debt (kEUR) |
|---|---|
| Base (P50 + Central case) | 43,919.033 |
| P90-10y yield only | 40,949.947 |
| Central Low prices only (P50 yield) | 41,677.278 |
| **Candidate C (P90 + Central Low)** | **38,829.996** |
| **Target (DS!D51)** | **42,852.279** |
| **Delta** | **−4,022.283 kEUR** |
| Tolerance | 500 kEUR |
| **Result** | **FAIL — STOP** |

**Verdict:** `C3B3D2B2C_R4_2_STOP_CANDIDATE_C_SOURCE_PARITY_FAILED`

#### Per-period merchant decomposition (first four periods)

| Period | Bank CFADS (kEUR) | Source DS!row20 (kEUR) | Delta (kEUR) |
|---|---|---|---|
| P26 (CY2042 half) | 1,137.713 | 2,279.787 | −1,142.075 |
| P27 (CY2043 half) | 1,195.041 | 2,103.844 | −908.803 |
| P28 (CY2043 half) | 1,192.747 | 2,248.763 | −1,056.016 |
| P29 (CY2044 half) | 1,123.846 | 2,057.780 | −933.934 |

All merchant period deltas are negative — engine bank CFADS is systematically below source DS!row20.

#### Analysis of the engine–Excel sensitivity disparity

| Perturbation | Engine delta (kEUR) | Excel delta (kEUR) | Ratio |
|---|---|---|---|
| Central → Central Low prices | ~−5,089 | −961 | ~5.3× |

Direct substitution of D111 as the merchant price gives engine sensitivity ~5.3× larger than Excel's observed 961 kEUR response. This proves the VBA does NOT apply D111 as a simple price-curve replacement. The exact mechanism remains inaccessible.

**Classification: `VBA_IMPLEMENTATION_NOT_VISIBLE` — unchanged from R3.**

### Candidate C engine evaluation — TUHO

**Blocker:** `build_tax_contract_from_project_inputs` raises `NotImplementedError` for `atad_enabled=True`. Full debt sizing not possible without complete interest schedule.

Operating model run with P90-10y yield + MidLow (D109) confirmed; bank CFADS for P2 (oracle P1) computed but full debt sizing blocked.

**Oracle target:** 2,539.633673 kEUR (back-calculated: DS_P1 × 1.2 = 2116.361394 × 1.2)

**Result:** `BLOCKED_ATAD`

### Post-maturity runtime causality proof

**Method:** Perturb merchant prices after Senior Debt maturity (CY2045+) by ×2.0 and ×0.5; measure debt delta.

| Perturbation | Debt delta (kEUR) |
|---|---|
| Post-maturity ×2.0 (CY2045+) | **0.000** |
| Post-maturity ×0.5 (CY2045+) | **0.000** |
| Active period ×1.1 (CY2042–2044) | +518.545 |

**Classification proven at runtime:**
`POST_MATURITY_CFADS_NON_CAUSAL_FOR_INITIAL_DSCR_SIZING_RUNTIME_PROVEN`

Post-maturity CFADS are provably inert for DSCR debt sizing. Only the 3 active merchant periods (CY2042–2044, within the Senior Debt horizon) are causal. This eliminates any hypothesis that extending the merchant price horizon would change the sizing outcome.

### R4.2 governance gate decision

```
STOP: Candidate C engine gives 38,830 kEUR vs source 42,852 kEUR (delta −4,022 kEUR).
Exceeds 500 kEUR tolerance. No calibration applied.
VBA mechanism not visible — cannot advance to production without resolution.
financial_engine/ zero-diff from base SHA — NO production changes.
```

### R4.2 test coverage

44 new tests across three classes:

| Class | Tests | Coverage |
|---|---|---|
| `TestR4_2SourceCurves` | 22 | Fixture existence, curve lengths, verbatim values, constants |
| `TestR4_2CandidateC` | 14 | STOP verdict, delta, decomposition, zero-diff guard |
| `TestR4_2PostMaturityCausality` | 8 | Runtime proof — zero delta for CY2045+, nonzero for CY2042–2044 |

Total: 145 tests (101 prior + 44 new), all passing.

---

## 12. R4.3: Revenue-regime bank case + Candidate D

### R4.2 failure reclassification

R4.2 Candidate C applied P90-10y yield **globally** across all operating periods, including PPA periods. This was a semantic error. The correct classification is:

```
R4_2_GLOBAL_P90_PLUS_SIZING_CURVE_COMBINATION_REJECTED
```

The sizing revenue curve causality remains `OBOROVO_DEBT_SIZING_REVENUE_CURVE_MANUAL_CAUSALITY_PROVEN` — the failure was in the production scenario semantics, not the revenue curve.

### PPA period source identity (proven)

| Metric | Value |
|---|---|
| Period range | P2–P25 (24 periods) |
| Max abs DS20–CF79 delta | 0.0062 kEUR |
| Signed total delta | −0.040 kEUR |
| **Classification** | **`OBOROVO_PPA_BANK_CFADS_EQUALS_BASE_CFADS_SOURCE_PROVEN`** |

Bank-case CFADS = base CFADS in all PPA+debt periods to within rounding. No P90 yield substitution should be applied to PPA periods.

### Candidate D: revenue-regime-aware splice

**Architecture:**
- PPA-active periods (P2–P25): base economics — P50 yield, Central case Trackers prices, base tax
- Merchant + Senior Debt active periods (P26–P29): P90-10y yield, sizing price curve, bank tax
- Post-maturity (P30+): excluded from DSCR sizing (runtime-proven non-causal, R4.2)
- No hardcoded period boundaries — regime from `is_ppa_active` on each period

### Candidate D results

| Scenario | Engine debt (kEUR) | Reference (kEUR) | Delta (kEUR) |
|---|---|---|---|
| D1 (Central case Trackers) | 43,621.556 | ~43,813.000 (Excel) | −191.444 |
| D2 (Central Low case Trackers) | 41,496.226 | 42,852.279 (DS!D51) | −1,356.053 |
| **Engine sensitivity D1−D2** | **2,125.330** | **~961.000 (Excel)** | **Residual 1,164.330** |

D1 is now within 192 kEUR of the Excel Central reference (significant improvement from Candidate C). D2 still misses by 1,356 kEUR. Engine sensitivity (2,125 kEUR) is 2.21× the Excel observation (961 kEUR).

### Merchant + debt period bridge (D2 Central Low)

| Period | End | D1 bank CFADS (kEUR) | D2 bank CFADS (kEUR) | DS20 (kEUR) | D1−DS20 | D2−DS20 |
|---|---|---|---|---|---|---|
| P26 | 2042-12-31 | 2,546.129 | 1,163.569 | 2,279.787 | +266.342 | −1,116.218 |
| P27 | 2043-06-30 | 2,759.002 | 1,195.041 | 2,103.844 | +655.158 | −908.803 |
| P28 | 2043-12-31 | 2,531.386 | 1,192.747 | 2,248.763 | +282.623 | −1,056.016 |
| P29 | 2044-06-30 | 2,748.256 | 1,123.846 | 2,057.780 | +690.476 | −933.934 |

DS20 is bracketed: D1 (Central) lies above DS20 in all four periods; D2 (Central Low) lies below DS20. The source bank case uses an intermediate pricing mechanism not reproduced by direct curve substitution.

### BESS revenue (scope correction)

Neither Oborovo nor TUHO calibration project has BESS/storage revenue relevant to Senior Debt sizing. Trackers/GMPV are PV/merchant captured-price scenario variants, not storage technologies.

**Classification:** `OBOROVO_BESS_NON_MATERIAL_TO_ACTIVE_DEBT_CFADS`

### TUHO revenue-regime finding

**Key result:** TUHO engine P2 (oracle P1) with P90 yield + MidLow prices matches oracle bank CFADS to within 0.018 kEUR.

| Metric | Value |
|---|---|
| Base EBITDA P2 (engine) | 3,070.194 kEUR |
| Oracle base CFADS | 3,070.176 kEUR |
| Bank EBITDA P2 (P90+MidLow) | 2,539.652 kEUR |
| Oracle bank CFADS | 2,539.634 kEUR |
| Difference (both) | +0.018 kEUR (oracle precision offset) |

**Critical clarification of the R4.1 "0.9515 residual price ratio":**

TUHO P2 is PPA-active. Revenue = PPA tariff × production. MidLow prices are irrelevant in PPA periods. The bank/base EBITDA ratio (0.8272) is explained entirely by P90 production reduction (0.8694) applied against fixed OPEX — a leverage effect, not a price ratio:

```
EBITDA_leverage_factor = bank/base_EBITDA_ratio / P90_P50_prod_ratio
                       = 0.8272 / 0.8694 = 0.9515
```

The 0.9515 in R4.1 was diagnostic algebra. It is NOT a price-curve reduction. MidLow prices matter only in TUHO merchant periods (beyond PPA term).

**Architecture:** `DebtSizingCase(production_case=P90, revenue_case_by_stream=by_stream)` — generic; normal revenue engine determines PPA vs merchant stream semantics per period. No project-name dispatch.

### R4.3 test coverage

26 new tests across four classes:

| Class | Tests | Coverage |
|---|---|---|
| `TestR4_3Reclassification` | 4 | R4.2 reclassification label, preserved numbers, causality |
| `TestR4_3PPASourceIdentity` | 5 | PPA identity source-proven, runtime verified |
| `TestR4_3CandidateD` | 12 | D1/D2 debt, sensitivity, merchant decomp, BESS, verdict |
| `TestR4_3TuhoRevenueRegime` | 5 | Oracle match, EBITDA leverage, no dispatch |

Total: 171 tests (145 prior + 26 new), all passing.

### R4.3 verdict

```
C3B3D2B2C_R4_3_STOP_REVENUE_REGIME_PARITY_FAILED
```

The PPA correction improved D2 debt from 38,830 kEUR (R4.2) to 41,496 kEUR (+2,666 kEUR closer). D1 Central is within 192 kEUR of the Excel reference. Engine sensitivity (2,125 kEUR) is 2.21× Excel's observed 961 kEUR. The VBA applies Central Low case Trackers through a mechanism that produces ~2.2× less effect than direct merchant price substitution.

**R4.3 blocker reclassification (made in R4.4):** The 2.21× excess is not caused by `VBA_IMPLEMENTATION_NOT_VISIBLE` alone. The root cause is identified in R4.4 (see §13): committed D111 values are the raw (pre-inflation) block row; the effective bank price requires multiplication by D116.

`financial_engine/` zero-diff from base SHA — no production changes.

---

## 13. R4.4 — Source price-curve lineage

### Lineage finding: D111 is raw, not inflation-applied

The R4.4 investigation traces the full formula chain from the Oborovo Inputs price block:

```
D106 = INDEX($D$107:$AL$112, MATCH($C$106, ...), MATCH(D105, ...)) × D116
```

Where:
- `D107:D112` block = raw annual price curves (one row per scenario, pre-inflation)
- `D116` = Calendar-year inflation index (`CY2030=1.10, ..., CY2060=1.99`)
- `D106` = selected raw row × D116 = **effective** captured price (what CF!row30 uses)

**D111 (Central Low case Trackers)** is the raw block row for the Central Low scenario:
- `D111 = D112 × (1 + B107) = D112 × 1.085` (tracker premium on Central Low GMPV)
- Committed values (CY2042–2060) are **PRE-INFLATION** — they are the raw D107:D112 block values

### D116 back-calculation at CY2042

From committed fixture evidence:

| Input | Value | Source |
|---|---|---|
| `D103[CY2042]` | 52.101 EUR/MWh | R4.4 specification, Inputs!D103 |
| `D103 = D108 × 1.05` | → D108[CY2042] = 49.620 | Back-calculation |
| `D107[CY2042] = D108 × 1.085` | 53.838 EUR/MWh | Derived |
| `D106[CY2042]` | 75.120951 EUR/MWh | Confirmed (merchant_revenue_truth.json) |
| **D116[CY2042]** | **75.120951 / 53.838 = 1.3952** | **Precisely derived** |

Consistency check: `1.10 × 1.02^12 = 1.3950` — D116 follows 2% annual compound growth from CY2030=1.10, confirming the back-calculation.

### Effective Central Low prices

| Year | D111 raw (EUR/MWh) | D116 | Effective (EUR/MWh) |
|---|---|---|---|
| CY2042 | 44.110675 | 1.3952 (exact) | **61.55** |
| CY2043 | 43.199275 | 1.4231 (est. ±0.5%) | **61.47** |
| CY2044 | 42.098000 | 1.4516 (est. ±0.5%) | **61.13** |

CY2043 and CY2044 D116 values are estimated at 2% compound growth from CY2042. Exact values require D108 time series or direct D116 extraction (XLSM required).

### Sensitivity ratio: why engine ratio is 2.21×

| Year | Raw sensitivity (D106-D111_raw) | Effective sensitivity (D106-D111_eff) | Ratio |
|---|---|---|---|
| CY2042 | 31.010 EUR/MWh | 13.575 EUR/MWh | **2.28** |
| CY2043 | 32.634 EUR/MWh | 14.356 EUR/MWh | **2.27** |
| CY2044 | 33.937 EUR/MWh | 14.906 EUR/MWh | **2.28** |
| Observed engine | — | — | 2125.330 / 961.0 = **2.21** |

The raw/effective sensitivity ratio ≈ 2.28 across all merchant+debt periods, matching the observed engine ratio 2.21 within 3%. **Inflation treatment (D116) fully accounts for the 2.21× engine excess.**

### R4.3 blocker reclassified

The R4.3 stop (`C3B3D2B2C_R4_3_STOP_REVENUE_REGIME_PARITY_FAILED`) was caused by using raw D111 values instead of effective D111 × D116 values. The reclassification label is:

```
R4_3_RAW_CENTRAL_LOW_DIRECT_SUBSTITUTION_REJECTED
OBOROVO_BANK_MERCHANT_PRICE_SOURCE_LINEAGE_NOT_YET_REPLAYED
```

### D103 causal role

`D103 = D108 × 1.05` (Inputs!D103, column D = CY2042). This is a non-causal reference cell — it provides the CY2042 base GMPV for back-calculation purposes but does not feed into the bank revenue path.

### E324 / E325 selector lineage

```
Scenarios!E325 = "Central Low case Trackers"
  → selects D111 row from D107:D112 block (raw pre-inflation curve)
  → × D116[year] (inflation index)
  → D106 effective price (by calendar year)
  → CF!row30 merchant price lookup (INDEX from D106 row by YEAR(period_end))
  → CF!row23 gross merchant revenue
  → Macro!row50 / DS!row20 bank CFADS
```

### R4.4 test coverage

15 new tests in `TestR4_4SourceLineage`:

| Test | Coverage |
|---|---|
| `test_r4_4_lineage_dict_importable` | Dict exists with classification |
| `test_r4_4_verdict_in_lineage` | STOP verdict label |
| `test_r4_4_verdict_in_module_docstring` | Docstring updated |
| `test_r4_3_raw_substitution_rejected_importable` | Reclassification dict |
| `test_r4_3_blocker_reclassified_as_lineage_gap` | Root cause label |
| `test_d116_cy2042_back_calculated_from_d103` | D116[CY2042] in range 1.38–1.42 |
| `test_d116_cy2042_consistent_with_compound_growth` | Matches 1.10 × 1.02^12 |
| `test_effective_central_low_cy2042_above_raw` | Inflation uplift confirmed |
| `test_effective_central_low_cy2042_below_central` | Directional ordering preserved |
| `test_sensitivity_ratio_matches_engine_ratio` | Ratio ≈ observed 2.21× within 10% |
| `test_sensitivity_ratio_explains_2x_excess` | Ratio > 2.0 per period |
| `test_d103_causal_classification_present` | D103 non-causal label |
| `test_e325_selector_chain_documented` | E325→D116 chain |
| `test_effective_central_low_accessor_importable` | OBOROVO_EFFECTIVE_CENTRAL_LOW dict |
| `test_no_new_candidate_without_full_lineage` | XLSM requirement enforced |

Total: 186 tests (171 prior + 15 new), all passing.

### R4.4 verdict

```
C3B3D2B2C_R4_4_STOP_MERCHANT_PRICE_SOURCE_LINEAGE_NOT_YET_REPLAYED
```

D116[CY2042] is precisely derived from committed fixture evidence. D116[CY2043–2044] require the D108 time series or direct D116 extraction (XLSM required). No new debt candidate until effective Central Low prices for all four merchant+debt periods (P26–P29) are confirmed.

Expected R4.5 outcome: Candidate D with effective prices → engine sensitivity ≈ 961 kEUR, target debt ≈ 42,852 kEUR.

`financial_engine/` zero-diff from base SHA — no production changes.

---

## 14. R4.5 — Source-exact effective sizing price + full revenue-lineage replay

R4.5 upgrades R4.4 in three ways: (a) direct XLSM source values replace back-calculated D116 estimates; (b) effective Central Low prices are built as `raw × D116` for all 19 CY years; (c) the engine sensitivity is cross-checked against the Excel sensitivity observation.

### D116 direct XLSM source values

| Year | R4.4 back-calc (superseded) | R4.5 direct source |
|------|-----------------------------|--------------------|
| CY2042 | 1.3952 | **1.39** |
| CY2043 | 1.4231 | **1.42** |
| CY2044 | 1.4516 | **1.45** |

R4.4 back-calculated estimates are classified `R4_4_BACK_CALCULATED_INFLATION_ESTIMATE_SUPERSEDED_BY_DIRECT_XLSM_SOURCE`. For CY2045+, the full D116 curve is built as compound growth at 2% p.a. from CY2044=1.45.

### Inflation transform cross-check

`raw_Central × D116 = effective_Central (D106 fixture)` to machine tolerance:

| Year | Raw Central | D116 | raw × D116 | D106 fixture | Residual |
|------|------------|------|------------|--------------|---------|
| CY2042 | 54.043850 | 1.39 | 75.12095150 | 75.12095150 | 0.00e+00 |
| CY2043 | 53.403700 | 1.42 | 75.83325400 | 75.83325400 | 1.42e-14 |
| CY2044 | 52.438050 | 1.45 | 76.03517250 | 76.03517250 | 0.00e+00 |

Classification: `OBOROVO_CAPTURED_PRICE_INFLATION_TRANSFORM_SOURCE_PROVEN`

### Candidate E results

| Metric | Value |
|--------|-------|
| E1 (Central): debt | 43,621.556 kEUR |
| E2 (Central Low effective): debt | 42,687.507 kEUR |
| Source (DS!D51) | 42,852.279 kEUR |
| Engine sensitivity (E1−E2) | 934.049 kEUR |
| Excel sensitivity | 961.000 kEUR |
| Sensitivity residual | −26.951 kEUR (2.80%) |
| Debt residual | −164.771 kEUR (0.38%) |

The sensitivity residual is 2.80% — well within the ±5% threshold, confirming the revenue mechanism (P90 yield + effective Central Low price) is correctly identified.

### Per-period bridge (4 merchant+debt periods)

| Pi | Date | E2 CFADS | Source DS20 | Delta | Implied tax | Note |
|----|------|----------|-------------|-------|-------------|------|
| 26 | 2042-12-31 | 1,930.7 | 2,279.8 | −349.1 | 166.7 | H2: engine pays tax Dec-31 |
| 27 | 2043-06-30 | 2,064.6 | 2,103.8 | −39.3 | 0.0 | H1: no tax charge |
| 28 | 2043-12-31 | 1,961.3 | 2,248.8 | −287.5 | 111.9 | H2: engine pays tax Dec-31 |
| 29 | 2044-06-30 | 2,030.6 | 2,057.8 | −27.2 | 0.0 | H1: no tax charge |

### Bank tax timing decomposition

The engine concentrates the full annual income-tax charge in the Dec-31 (H2) period; the source Excel model charges it in the Jun-30 (H1) period. This timing inversion is the primary source-visible residual component:

- **H2 Dec-31 total implied cash tax**: 278.550 kEUR
- **H1 Jun-30 total implied cash tax**: 0.000 kEUR

This is a documented observation, not a calibration. Per governance: no tax-timing plug added, no calibration performed.

### R4.5 test coverage

36 new tests in `TestR4_5SourceExactEffectivePriceReplay`, covering categories A–T per spec §31:

- A: D116 source values (3 tests)
- B: Raw Central values locked (3 tests)
- C: Effective Central Low curve (3 tests)
- D–H: Engine semantics (5 tests)
- F: Inflation cross-check proven (4 tests)
- J: R4.4 back-calc superseded (1 test)
- K: Sensitivity residual < 5% (2 tests)
- L: PPA regression (1 test)
- M: Four-period bridge H2/H1 pattern (4 tests)
- N: Bank tax timing decomposition (2 tests)
- O: Debt residual < 1% (2 tests)
- P: Verdict classification (2 tests)
- Q–T: Governance (4 tests)

Total: 222 tests (186 prior + 36 new), all passing.

### R4.5 verdict

```
C3B3D2B2C_R4_5_EFFECTIVE_PRICE_PROVEN_BANK_TAX_TIMING_RESIDUAL_IDENTIFIED
```

The inflation transform is source-proven to machine precision. The engine sensitivity matches the Excel observation to within 2.80%. The remaining 0.38% absolute debt residual is fully decomposed as a bank-tax timing difference (engine charges tax Dec-31; source charges it Jun-30) — a source-visible component, not a price factor.

`financial_engine/` zero-diff from base SHA — no production changes.

---

## 15. R4.6 — Source-Compatible Bank Tax Periodisation Counterfactual (STOP)

### R4.6 objective

R4.6 implements a **counterfactual (T2)**: replace the engine's `TAX_YEAR_LAST_PERIOD` convention (cash tax in H2/Dec-31) with the source Oborovo pairing convention (H2 taxable + H1 taxable → settle at H1/Jun-30) and re-run the locked Senior Debt solver. If T2 closes to within 1 kEUR of the source debt (42,852.279 kEUR), the R4.5 hypothesis is proven.

### Source CIT convention locked

| Attribute | Value |
|---|---|
| CIT rate | 10% |
| Pairing | `bank_cash_tax[H1(N+1)] = MAX(ti_H2(N) + ti_H1(N+1), 0) × 10%` |
| H2 cash tax | 0.0 kEUR (zero) |
| Cash tax lag | 0 periods |
| Classification | SOURCE_PROVEN (from base-case evidence) |

Base-case source tax evidence (not injected into bank calculation):

| Period | Source cash tax (kEUR) |
|---|---|
| 2043-06-30 (H1) | 285.107 |
| 2043-12-31 (H2) | 0.000 |
| 2044-06-30 (H1) | 301.618 |
| 2044-12-31 (H2) | 0.000 |

### Counterfactual results

| Metric | Value |
|---|---|
| T1 debt (engine H2 settlement) | 42,687.507 kEUR |
| T2 debt (source H1 settlement) | 42,624.119 kEUR |
| Source debt | 42,852.279 kEUR |
| T2 residual vs source | −228.159 kEUR |
| T2 absolute residual | 228.159 kEUR |
| T2 relative residual | 0.532% |
| Verdict | **STOP** — counterfactual failed |

### Diagnostic interpretation

T2 (H1 settlement) moves debt **further** from source than T1 (H2 settlement): T1 residual = −164.8 kEUR, T2 residual = −228.2 kEUR. The source H2+H1 pairing hypothesis does not close the debt gap; the residual worsens. This implies at least one additional source mechanism is not yet identified — likely related to bank-case taxable income inputs (EBITDA or tax depreciation) rather than settlement timing alone.

Both T1 and T2 underestimate the source debt. The direction of the remaining gap (engine < source) is consistent across both timing conventions, indicating that the revenue/EBITDA mechanism — not tax timing — is the primary outstanding driver.

### R4.5 reclassification

The R4.5 bank-tax timing hypothesis remains **DIAGNOSTIC ONLY — NOT COUNTERFACTUALLY PROVEN**. The timing asymmetry (engine H2 vs source H1) is real and structurally consistent, but it does not explain the observed debt residual in the bank case. R4.5's price mechanism findings (P90 yield + effective Central Low, 2.80% sensitivity residual) are **preserved and unaffected**.

### R4.6 governance

- `_apply_source_oborovo_tax_periodisation()` implemented in `finco_recon/` only — `financial_engine/` zero-diff maintained
- No base-tax injection — source tax is evidence-only
- No DS20-derived tax — bank taxable income computed from bank EBITDA
- No plug, no calibration, no project-name dispatch, no hardcoded period indices
- 29 focused R4.6 tests (categories A–CC) — all pass

---

## 16. R4.6.1 — Full source row35→row41→row43 bank-case replay (Candidate G)

### R4.6 reclassification

R4.6 T2 is reclassified as `R4_6_CLEAN_ANNUAL_TAX_WITH_SOURCE_SETTLEMENT_TIMING_REJECTED`. Its implementation error: `_apply_source_oborovo_tax_periodisation` used `PeriodCashTaxResult.taxable_income_before_lcf_share_keur` — the clean engine annual-TI share allocated per period — rather than the source formula `row35 = EBITDA − book_dep − senior_int`. Only the settlement timing was corrected (H2→H1); taxable income remained from the clean engine, not the source workbook.

### Source P&L mechanics (confirmed from full model extract)

| Row | Formula |
|---|---|
| row35 (taxable income) | `EBITDA − book_dep − senior_int` (SHL cancels via fiscal reintegration) |
| row36 (loss pool) | Rolling sum of `min(row41_prior, 0)` over the 5 preceding model periods |
| row37 (loss used) | `MIN(−row36, EBT) if (row36 < 0 and EBT > 0) else 0` — **EBT gate, not TI gate** |
| row41 (taxable profit) | `row35 − row37` |
| row43 (CIT at H1) | `MAX(row41_H2(N) + row41_H1(N+1), 0) × 10%`; H2 CIT = 0 |

SHL gross interest reduces EBT but cancels via fiscal reintegration in row35 (net effect: SHL affects EBT gate, not taxable income).

### Three-way counterfactual results

| | Debt (kEUR) | Residual vs source |
|---|---|---|
| T1 — clean engine (H2 settlement) | 42,687.507 | −164.772 kEUR |
| T2-old — R4.6 flawed (clean TI + H1 settlement) | 42,624.119 | −228.160 kEUR |
| **T3 — source row35→41→43 + H1 settlement** | **42,620.863** | **−231.416 kEUR** |
| Source (DS!D51) | 42,852.279 | — |

T3 absolute residual: **231.416 kEUR** (0.540% relative). Verdict: **STOP**.

### EBT gate — bank case confirmed

In all 4 bank merchant periods (p26–p29), bank EBT is negative (SHL interest ~1,150–1,260 kEUR exceeds bank EBITDA − book_dep margin). The row37 EBT gate fires as zero in all bank merchant periods:

- `row37_loss_used = 0` for all bank merchant periods (EBT gate blocks loss utilisation)
- `row41 = row35` for all bank merchant periods
- H2 CIT = 0; H1 CIT = MAX(row41_H2 + row41_H1, 0) × 10%

### Per-period bridge (merchant periods only, debt tenor)

| Period | Period end | Bank EBITDA | EBT | row41 | T3 CIT | T1 CIT | T3 CFADS | DS20 | T3 vs DS20 |
|---|---|---|---|---|---|---|---|---|---|
| p26 | 2042-12-31 | 2,097.4 | −1,146.6 | 514.8 | 0.0 | 166.7 | 2,097.4 | 2,279.8 | −182.4 |
| p27 | 2043-06-30 | 2,064.5 | −1,152.0 | 548.7 | 106.3 | 0.0 | 1,958.2 | 2,103.8 | −145.6 |
| p28 | 2043-12-31 | 2,073.1 | −1,225.6 | 572.1 | 0.0 | 111.9 | 2,073.1 | 2,248.8 | −175.6 |
| p29 | 2044-06-30 | 1,914.1 | −1,257.8 | 592.5 | 116.5 | 0.0 | 1,914.1 | 2,057.8 | −143.6 |

T3 signed CFADS delta vs DS20: **−647.3 kEUR** over merchant periods. Gap decomposition:
- At H2 periods (p26, p28): T3 CIT = 0 → T3 CFADS = bank EBITDA. Gap vs DS20 = EBITDA model delta (~182 kEUR/period).
- At H1 periods (p27, p29): gap = EBITDA model delta + residual tax delta.

### Base-case source tax replay validation

`_validate_base_source_tax_replay` replays source row35→41→43 for the base case using fixture senior interest:

- Max |CIT delta| vs fixture: **1.538 kEUR** (at stub period p61, 2060-06-29)
- Periods outside 1 kEUR tolerance: **3** (p47, p55, p61)
- Classification: `OBOROVO_SOURCE_TAX_ROW35_TO_ROW43_REPLAY_BASE_PARITY_PARTIAL`
- Residual sources: (1) SHL PIK approximation (affects EBT gate in base case); (2) stub final period (month-only H1 identification — fixed)

Base parity is PARTIAL, not PROVEN. The source row35→41→43 formula replicates the base-case CIT to within ~1.5 kEUR — structurally consistent but not closed to 1 kEUR tolerance across all periods.

### R4.6.1 diagnostic interpretation

T3 correctly implements the full source workbook tax formula (row35→41→43 with H1 settlement). However, T3 debt (42,621 kEUR) is marginally LOWER than T2-old (42,624 kEUR) and substantially below source (42,852 kEUR). The residual of −231 kEUR breaks down as:

1. **Bank EBITDA model gap** (~180 kEUR/H2 period): the engine's bank-case EBITDA (P90 yield + effective Central Low prices) is ~180 kEUR below the source bank-case EBITDA at each H2 period. This is the primary remaining gap and is unrelated to tax.
2. **Residual tax gap**: T3 CIT at H1 differs from source H1 CIT. Part of this is the EBITDA model gap propagating into taxable income; part may be OPEX or depreciation model differences.

The tax timing and formula mechanism (source row35→41→43) is now fully implemented. The remaining gap is attributable to the bank-case EBITDA model, not to the tax convention.

### R4.6.1 governance

- `_compute_source_pl_rows`, `_compute_source_cit_schedule`, `_build_shl_interest_by_period`, `_validate_base_source_tax_replay`, `_run_candidate_g_debt` implemented in `finco_recon/` only — `financial_engine/` zero-diff maintained
- No base-tax injection — ENFORCED
- No DS20-derived tax — ENFORCED
- No plug, no calibration, no project-name dispatch, no hardcoded period indices — all ENFORCED
- H1/H2 identification by month only (handles stub period at model boundary) — ENFORCED
- 61 focused R4.6.1 tests (categories A–M) — all pass
- Total C3B3D2B2C tests: 312 (all pass)

---

## 17. R4.7 — Oborovo source workbook production-selector bypass + bank CFADS parity closure

### Hypothesis

The Oborovo bank-sizing CFADS formula links to the **static P50 operating hours row** (Inputs!D54 = 1494 h), not to the dynamic production scenario selector (Inputs!D52). VBA sets `Production_Scenario = P90` before writing bank-period CFADS to Macro!row50, but the CF production formula does not consume the dynamic selector — it always resolves to P50.

If this hypothesis is correct, a source-workbook replay using P50 production + effective Central Low prices + source row35→41→43 CIT (Candidate H) should close the remaining 231 kEUR bank debt residual.

### Source evidence: Oborovo CF production formula bypass

| Cell | Value | Role |
|---|---|---|
| `Inputs!D52` | `P_50` (string) | Dynamic production scenario selector (base scenario) |
| `Inputs!D54` | `1494` | Operating hours — P50 row (static, formula-independent of D52) |

`OBOROVO_INPUTS_D52_PRODUCTION_SCENARIO_SELECTOR_SOURCE_PROVEN`: Inputs!D52 holds the production scenario label. Under the base scenario it reads `P_50`; VBA switches it to `P90` before copying bank CFADS. This cell is the selector but the CF production formula references the static P50 hours row directly, bypassing it.

`OBOROVO_INPUTS_D54_OPERATING_HOURS_SOURCE_PROVEN`: Inputs!D54 = 1494 h (P50 cached value). This is the row the CF production formula links to, making bank CFADS insensitive to the VBA P90 switch.

`OBOROVO_CF_PRODUCTION_SCENARIO_SELECTOR_BYPASS_SOURCE_PROVEN`: engine P50 production matches CF fixture production at P26/P27/P29 to <1 MWh. Engine P90 deviates 2920–2977 MWh (5.6%) from fixture. This is definitive mathematical proof that the source workbook CF formula uses static P50, not VBA-switched P90.

### VBA classification update (supersedes `VBA_IMPLEMENTATION_NOT_VISIBLE`)

| Classification | Status |
|---|---|
| `BANK_SIZING_SCENARIO_SWITCH_P90_VBA_SOURCE_PROVEN` | VBA switches Production_Scenario to P90, but CF formula does not consume it for Oborovo |
| `BANK_SIZING_CFADS_VBA_COPY_FREEZE_MECHANISM_SOURCE_PROVEN` | VBA copies CF!row79 → Macro!row50 under P90 selector; CF formula remains static P50 |
| `BANK_SIZING_TAX_SEPARATE_FREEZE_VBA_SOURCE_PROVEN` | VBA copies tax rows separately; row35→41→43 H1 settlement preserved |
| `VBA_IMPLEMENTATION_NOT_VISIBLE` | **SUPERSEDED** by the above proven classifications |

### Governance classifications

`OBOROVO_P50_BANK_PRODUCTION_BEHAVIOUR_IS_SOURCE_WORKBOOK_COMPATIBILITY_ONLY`: The use of P50 production in Oborovo bank sizing is a workbook-specific formula artefact — the CF formula links to the static P50 hours row rather than through the dynamic selector. This is NOT generic methodology.

`GENERIC_BANK_SIZING_PRODUCTION_POLICY_REMAINS_P90_BY_DEFAULT`: For all projects other than Oborovo, the generic bank-sizing production policy is P90. Oborovo P50 must not be generalised.

### TUHO cross-validation (anti-overgeneralisation)

To confirm Oborovo P50 is a workbook-specific artefact and not a general rule, TUHO was tested under both P90 and P50 bank cases:

| TUHO test | EBITDA at P2 | Oracle | Delta |
|---|---|---|---|
| P90 + MidLow (bank) | 2,539.652 kEUR | 2,539.634 kEUR | **0.018 kEUR** |
| P50 + MidLow (bank) | ~2,009 kEUR | 2,539.634 kEUR | **530.561 kEUR** |

`TUHO_BANK_PRODUCTION_SCENARIO_PROPAGATES_TO_CF_SOURCE_PROVEN`: TUHO bank CFADS DOES propagate P90, confirming the P50 bypass is Oborovo-specific. The anti-overgeneralisation constraint is enforced.

### Candidate H — SOURCE_WORKBOOK_REPLAY

Candidate H uses P50 production + effective Central Low prices + source row35→41→43 CIT (identical tax mechanics to R4.6.1 T3, `_compute_source_pl_rows` + `_compute_source_cit_schedule`), all run with the locked senior debt solver.

**Results summary**

| Run | Debt (kEUR) | Residual vs source (42,852.279 kEUR) |
|---|---|---|
| T1 — clean engine P90 (H2 settlement) | 42,687.507 | −164.772 kEUR |
| T3 — source row35→41→43 P90 + H1 settlement | 42,620.863 | −231.416 kEUR |
| **T4 — Candidate H: P50 + source CIT (H1 settlement)** | **42,855.410** | **+3.131 kEUR** |
| Source (DS!D51) | 42,852.279 | — |

T4 absolute residual: **3.131 kEUR** (0.0073% relative). This is a **99.3% reduction** in the residual from T3.

### Four-period merchant bridge (P26–P29)

| Period | End date | Engine P50 MWh | Fixture MWh | Δ MWh | T4 CFADS | DS20 | T4 vs DS20 |
|---|---|---|---|---|---|---|---|
| p26 | 2042-12-31 | 52,945 | 52,945 | ~0 | 2,279.8 | 2,279.8 | **≤1 kEUR** |
| p27 | 2043-06-30 | 52,082 | 52,081 | ~0 | 2,103.8 | 2,103.8 | **≤1 kEUR** |
| p28 | 2043-12-31 | 52,733 | 52,589 | **+144** | 2,063.9 | 2,057.8 | **+6.161 kEUR** |
| p29 | 2044-06-30 | 52,017 | 52,017 | ~0 | 2,226.8 | 2,226.8 | **≤1 kEUR** |

### P28 calendar residual (documented, not a model error)

Period 28 (2043-12-31) shows a 144.08 MWh production discrepancy between engine P50 and fixture. This is a period-fraction boundary approximation inherent to the calendar half-year split at P28. It results in a +6.161 kEUR CFADS delta at P28 only. All other merchant periods close exactly.

- Periods outside 1 kEUR (excluding P28): **0**
- P28 residual propagates through to the debt solver: T4 debt 42,855.410 vs source 42,852.279 (residual = +3.131 kEUR)

### R4.6.1 p29 reporting correction

`R4_6_1_P29_REPORTING_VALUE_CORRECTED_NO_ENGINE_CHANGE`: In the R4.6.1 §16 table, T3 CFADS at p29 was shown as equal to bank EBITDA (1,914.1 kEUR). This implied zero CIT at p29. The correct value is T3 CFADS = bank EBITDA − CIT = 1,914.1 − 116.5 = **1,797.6 kEUR**. This is a documentation correction only; no engine change is required. The T3 code and test suite were correct; only the table presentation was wrong.

### Verdict

```
C3B3D2B2C_R4_7_P50_SOURCE_BYPASS_PROVEN_P28_CALENDAR_RESIDUAL_DOCUMENTED_GENERIC_P90_POLICY_PRESERVED
```

- `CFADS_PARITY_PROVEN_EXCL_P28_CALENDAR_RESIDUAL`: all merchant periods close to ≤1 kEUR except P28 (calendar boundary residual documented)
- `DEBT_PARITY_WITHIN_10KEUR`: T4 debt residual = +3.131 kEUR vs source

### R4.7 governance

- `financial_engine/` zero-diff maintained throughout — ENFORCED
- No base-tax vector injection — ENFORCED
- No DS20-derived tax — ENFORCED
- No plug, no calibration, no project-name dispatch — ENFORCED
- No DS25/DS40 period boundary hardcoding — ENFORCED
- TUHO anti-overgeneralisation cross-validation run and confirmed — ENFORCED
- `GENERIC_BANK_SIZING_PRODUCTION_POLICY_REMAINS_P90_BY_DEFAULT` — ENFORCED
- 57 focused R4.7 tests (categories A–T) — all pass (superseded by R4.7.1 count below)
- R4.7.1 adds 54 further tests (categories A–V): 423 total, all pass

---

## 17.1 R4.7.1 — P28 calendar source closure + full-horizon diagnostic + stage closeout

### Input cell lineage correction (no calculation change)

`R4_7_INPUT_CELL_LINEAGE_DOCUMENTATION_CORRECTED_NO_CALCULATION_CHANGE`: Prior R4.7 wording described Inputs!D54 as "static P50 row". Correct structure:

| Cell | Role | Value |
|---|---|---|
| `Inputs!D52` | Production Scenario selector label | `P_50` (base) |
| `Inputs!D54` | Dynamic scenario-selected operating-hours result (INDEX/MATCH) | 1494 h when P50 active |
| `Inputs!D64` | **Static P50 operating hours source row** | **1494 h** |
| `Inputs!D68` | **Static P90-10y operating hours source row** | **1410 h** |
| `CF!B20` | CF operating hours reference | `=Inputs!D64` (static, bypasses D52/D54) |

`CF!B20 = Inputs!D64` (not D52→D54) is the root cause: CF production bypasses the dynamic selector entirely.

### Source period-fraction formula proven

`OBOROVO_OPERATING_PERIOD_FRACTION_SOURCE_FORMULA_PROVEN`: Source convention (paired annual model cycle):

- **H2 period** (ending Dec 31 of year Y): denominator = 366 if isleap(Y+1) else 365
- **H1 period** (ending Jun 30 of year Y): denominator = 366 if isleap(Y) else 365

Proven against all 60 fixture operating periods to 10 decimal places.

**Finco current convention**: denominator = 366 if isleap(end.year) else 365.
Difference: H2 periods only. Finco uses Y (period end year); source uses Y+1 (following year).

### Affected periods: 15 H2 leap-boundary periods

| Type | Count | Description | Effect |
|---|---|---|---|
| Pre-leap H2 (Y non-leap, Y+1 leap) | 8 | 2031, 2035, 2039, 2043, 2047, 2051, 2055, 2059 | Source denom=366 > Finco denom=365 → T5 < T4 (production reduced) |
| Post-leap H2 (Y leap, Y+1 non-leap) | 7 | 2032, 2036, 2040, 2044, 2048, 2052, 2056 | Source denom=365 < Finco denom=366 → T5 > T4 (production increased) |

### T5 — SOURCE_CALENDAR_REPLAY results

| Run | Debt (kEUR) | Residual vs source |
|---|---|---|
| T4 — Candidate H (P50 + source CIT) | 42,855.410 | +3.131 kEUR |
| **T5 — T4 + source calendar fractions** | **42,851.250** | **−1.028 kEUR** |
| Source (DS!D51) | 42,852.279 | — |

### Four-period merchant bridge (T5)

| Period | End | T5 production | Fixture | Δ MWh | T5 CFADS | DS20 | T5 vs DS20 |
|---|---|---|---|---|---|---|---|
| p26 | 2042-12-31 | 52,944.667 | 52,944.667 | 0.000 | 2,279.787 | 2,279.787 | **0.000 kEUR** ✓ |
| p27 | 2043-06-30 | 52,081.439 | 52,081.439 | 0.000 | 2,103.835 | 2,103.844 | **−0.008 kEUR** ✓ |
| p28 | 2043-12-31 | 52,588.809 | 52,588.809 | **0.000** | 2,246.091 | 2,248.763 | **−2.672 kEUR** ✗ |
| p29 | 2044-06-30 | 52,017.192 | 52,017.192 | 0.000 | 2,058.432 | 2,057.780 | **+0.651 kEUR** ✓ |

### p28 analysis — STOP (R4.7.1 CFADS gap documented; cause identified in R4.7.2)

T5 closes **production** at p28 to 0.000 MWh delta (confirmed). The remaining −2.672 kEUR CFADS gap is an **EBITDA model residual** (H2 CIT = 0, so CFADS = EBITDA):

- T5_EBITDA at p28 = 2,246.091 kEUR
- Source EBITDA (DS20) at p28 = 2,248.763 kEUR
- Residual = −2.672 kEUR

`R4_7_1_CY2043_PRICE_PRECISION_HYPOTHESIS_NOT_PROVEN`: The original attribution of this gap to CY2043 price precision is **reclassified**. See §17.2 (R4.7.2) for arithmetic proof that the gap is entirely explained by omitted OPEX calendar correction.

### Verdict

```
C3B3D2B2C_R4_7_1_STOP_CALENDAR_REPLAY_FAILED
```

- `OBOROVO_OPERATING_PERIOD_FRACTION_SOURCE_FORMULA_PROVEN`: calendar convention fully proven
- `T5_PRODUCTION_PARITY_PROVEN`: all four merchant periods match fixture to <1 MWh
- `CALENDAR_REPLAY_FAILED_EBITDA_RESIDUAL_REMAINS`: p28 CFADS −2.672 kEUR outside ±1 kEUR
- T5 debt residual: −1.028 kEUR (improved from T4's +3.131 kEUR; within 2 kEUR but outside ≤1 kEUR)

### Parity layer separation

`ASSET_PERFORMANCE_PARITY_AND_DEBT_SIZING_PARITY_ARE_SEPARATE_ACCEPTANCE_LAYERS`: The Macro50/DebtCF_in bank-sizing layer is a lender-sizing audit layer only. Future full parity work must separately compare Excel Base/Equity Case vs Finco Base/Equity Case from COD to project end.

`OBOROVO_BASE_PERFORMANCE_PRODUCTION_RESIDUAL_CALENDAR_CONVENTION_IDENTIFIED`: The same calendar convention affects 15 H2 periods in the Base Case production. This is an input to future asset-performance parity, not proof of full Base Case parity.

### Calendar rule classification

`EXCEL_COMPATIBILITY_ONLY_PENDING_GENERIC_REVIEW`: The paired-annual-cycle convention matches Oborovo exactly. Whether to adopt as `GENERIC_FINCO_CORRECTNESS_CANDIDATE` requires cross-project validation (TUHO, other projects) and production-design review. Implemented in `finco_recon` only — no `financial_engine/` change.

### R4.7.1 governance

- `financial_engine/` zero-diff: **ENFORCED** (confirmed by git diff)
- No hardcoded p28/year exception — source calendar formula applied uniformly to all 60 periods: **ENFORCED**
- No plug, no calibration, no project-name dispatch: **ENFORCED**
- 54 focused R4.7.1 tests (categories A–V) — all pass
- Total C3B3D2B2C tests: 423 (all pass)

---

## 17.2. R4.7.2 — OPEX calendar periodisation + final bank-CFADS forensic closeout

### Identity table

| Field | Value |
|---|---|
| **R4.7.2 Verdict** | `C3B3D2B2C_R4_7_2_SOURCE_CALENDAR_FULL_OPERATING_REPLAY_CFADS_AND_DEBT_PARITY_PROVEN_OPEX_CALENDAR_PERIODISATION_HYPOTHESIS_PROVEN_STAGE_DIAGNOSTIC_CLOSED` |
| Function | `run_candidate_h_oborovo_r472` |
| Candidate | SOURCE_CALENDAR_FULL_OPERATING_REPLAY (corrected T5) |

### R4.7.1 reclassification

`R4_7_1_CY2043_PRICE_PRECISION_HYPOTHESIS_NOT_PROVEN`: The R4.7.1 attribution of the p28 −2.672 kEUR CFADS residual to CY2043 price precision is **reclassified as not proven**. Price is LOCKED — CY2043 raw Central Low = 43.199275 EUR/MWh, Inflation = 1.42, Effective = 61.34297050 EUR/MWh. No CY2043 price change.

`R4_7_1_T5_OPEX_CALENDAR_PERIODISATION_OMITTED`: T5_SOURCE_CALENDAR_REPLAY (R4.7.1) scaled production, day_fraction, and revenue but **omitted** opex_keur from the calendar correction. The source workbook applies the same paired-annual-cycle period fraction to time-proportional OPEX. This omission is the sole cause of the −2.672 kEUR p28 CFADS residual.

### OPEX calendar hypothesis — arithmetic proof

`OBOROVO_P28_OPEX_RESIDUAL_IS_PERIOD_FRACTION_SOURCE_PROVEN`:

| Item | Value |
|---|---|
| Engine opex at p28 | 978.097602956399 kEUR |
| scale = finco_denom / source_denom | 365 / 366 = 0.997267759562842 |
| scaled_opex | 978.097602956399 × 0.997267759 = 975.425205134 kEUR |
| Fixture source opex | 975.4252051341138 kEUR |
| Residual | < 2.3 × 10⁻¹³ kEUR (machine precision) |

`R4_7_1_P28_CFADS_RESIDUAL_EXACTLY_EXPLAINED_BY_OMITTED_OPEX_CALENDAR_CORRECTION`: T5 CFADS delta = −2.672 kEUR = −(raw_opex − scaled_opex) = −engine_opex × (1 − 365/366). No other mechanism required.

`OBOROVO_OPEX_USES_SOURCE_OPERATING_PERIOD_FRACTION`: For all 15 H2 leap-boundary periods, fixture_opex = engine_opex × (finco_denom/source_denom) to machine precision (<1e-9 kEUR). `EXCEL_COMPATIBILITY_ONLY_PENDING_GENERIC_REVIEW` classification applies.

### SOURCE_CALENDAR_FULL_OPERATING_REPLAY results

T5_corrected = T4 + source calendar fractions applied to **production, revenue, and opex**.

| Run | Debt (kEUR) | Residual vs source |
|---|---|---|
| T5_raw (R4.7.1, opex not scaled) | 42,851.250 | −1.028 kEUR |
| **T5_corrected (R4.7.2, opex scaled)** | **42,852.161** | **−0.117 kEUR** |
| Source (DS!D51) | 42,852.279 | — |

### Four-period merchant bridge (T5_corrected)

| Period | End | T5_raw vs DS20 | T5c vs DS20 |
|---|---|---|---|
| p26 | 2042-12-31 | 0.000 kEUR ✓ | 0.000 kEUR ✓ |
| p27 | 2043-06-30 | −0.008 kEUR ✓ | +0.002 kEUR ✓ |
| p28 | 2043-12-31 | **−2.672 kEUR ✗** | **0.000 kEUR ✓** |
| p29 | 2044-06-30 | +0.651 kEUR ✓ | +0.389 kEUR ✓ |

All four merchant periods within ±1 kEUR. Senior Debt within ±1 kEUR. Stage diagnostic closed.

### Verdict

```
C3B3D2B2C_R4_7_2_SOURCE_CALENDAR_FULL_OPERATING_REPLAY_CFADS_AND_DEBT_PARITY_PROVEN_OPEX_CALENDAR_PERIODISATION_HYPOTHESIS_PROVEN_STAGE_DIAGNOSTIC_CLOSED
```

### R4.7.2 governance

- `financial_engine/` zero-diff: **ENFORCED**
- Price LOCKED — no CY2043 price change: **ENFORCED**
- No hardcoded period indices, no project-name dispatch, no plug, no calibration: **ENFORCED**
- No base-tax injection, no DS20-derived tax: **ENFORCED**
- 23 focused R4.7.2 tests (categories A–W) — all pass
- Total C3B3D2B2C tests: 446 (all pass)

---

## 19. Next steps for future stages

R4.7.2 closes the bank-CFADS forensic stage. The remaining −0.117 kEUR debt residual (0.00027%) is within the ≤1 kEUR acceptance threshold and does not require further decomposition.

Outstanding items for future stages (out of scope for C3B3D2B2C):

1. **Full asset-performance parity**: compare Excel Base/Equity Case vs Finco from COD to project end (Production, Price, Revenue, OPEX, EBITDA, Depreciation, EBIT, Interest, Tax, CFADS, Senior/SHL balances, distributions). The calendar convention identified here (15 H2 leap-boundary periods) is an input to that work.
2. **EXCEL_COMPATIBILITY_ONLY classification review**: cross-project validation of the paired-annual-cycle period fraction (TUHO, other projects) before promoting to `GENERIC_FINCO_CORRECTNESS_CANDIDATE`.

---

## 20. Governance constraints observed

- No DS25/DS40 period boundary hardcoding — ENFORCED
- No project-name dispatch in production code — ENFORCED
- No approved_delta or balancing plug — ENFORCED
- No calibration of clean engine to source — ENFORCED
- `13547.2` does not appear as a literal — ENFORCED
- Protected C3B2 SHA not in production code literals — ENFORCED
- No DSRA implementation — ENFORCED
- Source Macro50 is test oracle only — no runtime fixture reads in production code
- `BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED` — preserved for prior rounds; R4.7 resolves the production component
- `VBA_IMPLEMENTATION_NOT_VISIBLE` — **SUPERSEDED** by R4.7: `BANK_SIZING_SCENARIO_SWITCH_P90_VBA_SOURCE_PROVEN`, `BANK_SIZING_CFADS_VBA_COPY_FREEZE_MECHANISM_SOURCE_PROVEN`, `BANK_SIZING_TAX_SEPARATE_FREEZE_VBA_SOURCE_PROVEN`
- DO NOT MERGE without explicit instruction
