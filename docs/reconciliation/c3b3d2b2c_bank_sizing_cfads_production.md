# C3B3D2B2C — Bank-Sizing CFADS Production: Reconciliation

## Stage identity

| Field | Value |
|---|---|
| Stage | C3B3D2B2C |
| Branch | `stage-c3b3d2b2c-bank-sizing-cfads-production` |
| Base SHA (C3B3D2B2B locked) | `6e06498…` |
| Protected C3B2 SHA | `f8f244c0660495bfb4115d4e32ba329c291ab829d1d0693e614c889457b5add7` |
| PR | #925 (DRAFT — DO NOT MERGE without explicit instruction) |

---

## 1. Problem statement

Prior stage C3B3D2B2B (PR #924, locked) proved that the Oborovo senior-debt sizing gap
to the source Excel (42,852 kEUR) is entirely explained by the bank-case CFADS, not by
mechanics (ACT/360, DSCR rounding, opex, rates).

Specifically:
- CF2 (DSCR mechanics) = 0 kEUR
- CF3 (ACT/360 day-count) = 0 kEUR
- CF4 (operating assumptions) = 0 kEUR
- CF5 (interest rate) = 0 kEUR
- CF1 (CFADS / bank case) = **sole source of the sizing gap**

Classification: `BANK_SIZING_CFADS_AUTHORITY_IS_SOLE_CURRENT_SIZING_GAP_SOURCE_PROVEN`

This stage (C3B3D2B2C) implements a generic typed bank-sizing CFADS scenario layer and
investigates whether any candidate rule reproduces the source Macro50 CFADS vector.

---

## 2. Source evidence

**Source oracle**: DS!row20 = Macro!row50, loaded from
`tests/fixtures/excel_oborovo_debt_interest_truth.json`
key path: `workstream_a.ds_row20_cfads.period_values_keur`

The fixture contains 61 values:
- Index [0]: 0.0 (construction, not used for sizing)
- Index [1–24]: 2,533–2,920 kEUR (PPA periods — approximately equal to base P50 CFADS)
- Index [25–29]: 2,279 / 2,104 / 2,249 / 2,058 / 2,226 kEUR (merchant periods — substantially lower)

Excel total debt (source): **42,852.279 kEUR**

---

## 3. Candidate rules investigated

### Candidate A — ALL_PRODUCTION (P90-10y for all periods)

All operating periods (PPA and merchant) use the P90-10y yield scenario.

| Metric | Value |
|---|---|
| Candidate debt | 40,950 kEUR |
| Max \|delta\| vs DS!row20 | **690 kEUR** |
| Gap to Excel debt | −1,902 kEUR |

Result: `OBOROVO_ALL_PRODUCTION_BANK_CASE_RULE_CANDIDATE_ONLY`

The gap is large and systematic: P90 applied to PPA periods produces CFADS below
the source (DS!row20 PPA periods ≈ base P50, not P90). The candidate rule
contradicts source evidence.

### Candidate B — MERCHANT_ONLY (P90-10y for merchant periods only)

PPA periods (rank < `first_merchant_operating_period_index`) retain base P50 yield.
Merchant periods use P90-10y yield.

| Metric | Value |
|---|---|
| Candidate debt | 43,622 kEUR |
| Max \|delta\| vs DS!row20 | **690 kEUR** |
| Gap to Excel debt | +770 kEUR |

Per-period merchant delta (bank CFADS − source):

| Period | Bank CFADS (kEUR) | Source DS!row20 (kEUR) | Delta (kEUR) |
|---|---|---|---|
| 26 | 2,546 | 2,280 | +266 |
| 27 | 2,759 | 2,104 | +655 |
| 28 | 2,531 | 2,249 | +283 |
| 29 | 2,748 | 2,058 | +690 |

Result: `OBOROVO_MERCHANT_ONLY_BANK_CASE_RULE_CANDIDATE_ONLY`

The PPA period match is good (delta ≈ 0). The merchant period mismatch is large and
positive — our P90-10y CFADS exceeds the source Macro50 by 266–690 kEUR per period.
The source applies an additional merchant-period downside not captured by yield-scenario
substitution alone.

---

## 4. Root cause of merchant period gap

### PPA periods

For PPA periods (1–24), DS!row20 decomposition from CF-sheet components confirms:

```
source_cfads[p] ≈ revenue_component[p] − opex_component[p] − cit_component[p]
```

The sum matches DS!row20 within fixture precision. This confirms that for PPA periods,
the source bank CFADS equals the clean-engine base-case CFADS (P50).

Classification: source bank CFADS ≈ base CFADS for PPA periods.

### Merchant periods

For merchant periods (25+), the CF-sheet component sum is substantially **higher** than DS!row20:

```
revenue_component[25] + opex_component[25] + cit_component[25] >> DS!row20[25]
```

The additional downside is applied by the Excel VBA Macro50 macro to the merchant
revenue/CFADS rows. The exact transformation mechanism is not visible in the
data-only worksheet extraction.

Classification: `VBA_IMPLEMENTATION_NOT_VISIBLE`
`BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED`

---

## 5. Stop verdict

```
C3B3D2B2C_STOP_BANK_CASE_TRANSFORMATION_NOT_SOURCE_PROVEN
```

Neither Candidate A (ALL_PRODUCTION) nor Candidate B (MERCHANT_ONLY) reproduces the
source DS!row20 / Macro50 vector. The VBA merchant transformation mechanism is not
identifiable from data-only worksheet extraction.

**Consequences:**

1. The generic bank-sizing CFADS layer (inputs, orchestrator, results, provenance) is
   implemented and tested but NOT wired into the canonical adapter
   (`build_senior_debt_model_input_from_project_inputs`) for any project.

2. Production adapter wiring is BLOCKED until a source-proven rule is identified.

3. The STOP verdict is the authoritative output of this stage.

---

## 6. Architecture implemented

### New input types (`financial_engine/inputs.py`)

- `ProductionScenarioScope` (Enum): `ALL_PRODUCTION` | `MERCHANT_ONLY`
- `DebtSizingScenario` (frozen dataclass): `yield_scenario` + `scope` (both required)
- `SeniorDebtModelInput.bank_sizing_scenario`: `DebtSizingScenario | None = None`

### Orchestrator (`financial_engine/orchestrator.py`)

- `_derive_bank_operating_input()`: pure transformer — swaps only `yield_scenario`;
  all other fields shared by reference from base `OperatingModelInput`
- `_is_ppa_for_bank_splice()`: uses `first_merchant_operating_period_index` (same
  authority as revenue engine) rather than `is_ppa_active` (calendar-based)
- `MERCHANT_ONLY` path: PPA periods take base P50 periods; merchant periods take P90 periods
- Fail-closed: raises `BANK_SIZING_CFADS_REQUIRED_PERIOD_MISSING` — no 0.0 fallback
- `bank_sizing_dscr`: bank CFADS / debt service (sizing DSCR)
- `senior_dscr`: base P50 CFADS / debt service (actual/economic DSCR) when bank active
- Base economic authority: after solver convergence, re-runs base-case tax/CFADS;
  `ProjectModelResult.tax_and_cfads` is always P50 economic CFADS

### Results (`financial_engine/results.py`)

`SeniorDebtSchedules` additions:
- `bank_sizing_cfads_keur: tuple[float, ...] | None = None`
- `bank_sizing_dscr: tuple[float | None, ...] | None = None`

### Provenance (`financial_engine/provenance.py`)

`compute_senior_debt_fingerprint` includes `bank_sizing_scenario.yield_scenario` +
`.scope` in the payload. Two runs differing only in bank scenario produce different
fingerprints.

---

## 7. Revenue-regime authority

The bank splice boundary uses `first_merchant_operating_period_index` (an explicit
input field that drives the revenue engine) rather than `is_ppa_active` (which reflects
calendar-based PPA date computation and may diverge from the revenue engine's boundary).

This is critical for projects where the PPA contract date creates a half-period boundary
that `is_ppa_active` resolves differently from the revenue engine.

---

## 8. DSCR semantics (when bank scenario active)

| Field | Definition | Populated when |
|---|---|---|
| `senior_dscr` | base P50 CFADS / debt service | always |
| `bank_sizing_dscr` | bank CFADS / debt service | bank scenario active |

The `bank_sizing_dscr` is the SIZING/bank DSCR (what the solver targets).
The `senior_dscr` is the ACTUAL/economic DSCR (for project economic assessment).

For Oborovo MERCHANT_ONLY merchant periods:
- `bank_sizing_dscr` ≈ 1.35 (solver target)
- `senior_dscr` ≈ 1.45–1.47 (actual P50)

---

## 9. C3B3D2B2B regression lock

The protected C3B2 SHA `f8f244c0660495bfb4115d4e32ba329c291ab829d1d0693e614c889457b5add7`
must not appear in any production output (no literal). The C3B3D2B2B findings
(CF2=CF3=CF4=CF5=0) are preserved and locked.

---

## 10. Governance constraints observed

- No DS25/DS40 period boundary hardcoding — ENFORCED
- No project-name dispatch in production code — ENFORCED
- No approved_delta or balancing plug — ENFORCED
- No calibration of clean engine to source — ENFORCED
- `13547.2` does not appear as a literal — ENFORCED
- No DSRA implementation — ENFORCED
- Source Macro50 is test oracle only — no runtime fixture reads in production code
- `BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED` — preserved
- `VBA_IMPLEMENTATION_NOT_VISIBLE` — preserved
- DO NOT MERGE without explicit instruction
