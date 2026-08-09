# C3B3D2A — Oborovo SHL Source Truth & Construction→Operating Seam

**Stage:** C3B3D2A
**Branch:** `stage-c3b3d2a-oborovo-shl-source-truth`
**Blockers resolved:** `OBOROVO_SHL_BALANCE_LINEAGE_UNRESOLVED` (resolved); `C3B3D2A_OBOROVO_PAYMENT_SOURCE_SEMANTICS_PROVEN` (source mode classified); canonical runtime remains `C3B3D2B_CANONICAL_SHL_RUNTIME_BLOCKED_BY_WATERFALL_COUPLING`
**Scope:** Source-evidence classification only. No production runtime promotion.

---

## 1. Purpose

C3B3D1 left three blockers unresolved:
1. `OBOROVO_SHL_BALANCE_LINEAGE_UNRESOLVED` — exact construction→operating opening balance unknown
2. `C3B3D1_BLOCKED_PAYMENT_MODE_SEMANTICS` — `shl_pik_switch_period=0` has no proven mapping to CASH_PAID
3. Five conflicting SHL values in the repository with undocumented provenance

C3B3D2A resolves these by extracting the authoritative schedule from committed Excel fixtures and classifying every value by its workbook source. No Python model output is used as source truth. No production paths are changed.

---

## 2. Source Workbook Identity

| Field | Value |
|---|---|
| Filename | `d49af8ee-20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm` |
| SHA-256 | `15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920` |
| Primary fixture | `tests/fixtures/excel_oborovo_financial_truth.json` |
| Period date fixture | `tests/fixtures/interest_limitation/oborovo_interest_limitation_fixture.json` |
| Extraction method | openpyxl `data_only=True` (cached values); `data_only=False` (formula text) |
| Workbook NOT in repo | Raw XLSM not committed; all evidence from committed fixtures |

---

## 3. Five Conflicting Values — Classification

| Value (kEUR) | Source | Cell / Origin | Status |
|---|---|---|---|
| **14,620.77** | Excel Inputs!D325 | `d49af8ee-...xlsm` cached value | **AUTHORITATIVE — Excel raw SHL draw** |
| **1,169.66** | Excel DS[0].cap | Construction PIK = 14620.77 × 0.08 × 1.0 | **AUTHORITATIVE — construction IDC** |
| **15,790.44** | Excel DS[0].end = DS[1].beg | 14620.77 + 1169.66 | **AUTHORITATIVE — operating opening balance** |
| **13,547.2** | `app/project_factories.py:373` | Legacy Python calibration value; origin unresolved | **NOT EXCEL SOURCE — C3B3D2A_FACTORY_VALUE_UNEXPLAINED_GAP** |
| **1,169.0** | `app/project_factories.py:393` comment | Rounded IDC in stale comment | **STALE COMMENT — corrected** |

The ~1,073.6 kEUR gap between 14,620.77 (Excel) and 13,547.2 (factory) is unexplained in C3B3D2A scope. Label: `C3B3D2A_FACTORY_VALUE_UNEXPLAINED_GAP`. Deferred to C3B3D2B.

---

## 4. Construction→Operating Balance Seam

The construction→operating opening balance seam (`C3B3D2_CONSTRUCTION_SEAM` from C3B3D1) is now resolved for Oborovo:

```
DS[0].beg  = 0.0                         (SHL opens at zero)
DS[0].fund = 14,620.773894815633         (Excel Inputs!D325 — full SHL draw at construction close)
DS[0].dcf  = 1.0                         (365 calendar days; actual/365 = 1.0 exactly)
DS[0].cap  = 14620.77 x 0.08 x 1.0 = 1,169.6619115852516   (100% PIK — construction)
DS[0].end  = 0 + 14620.77 + 1169.66 = 15,790.435806400885  (construction closing balance)

DS[1].beg  = 15,790.435806400885         (= DS[0].end; no gap)
```

**`OBOROVO_SHL_BALANCE_LINEAGE_RESOLVED`**: The operating opening balance is **15,790.435806400885 kEUR**, proven from the committed fixture roll-forward. The C3B3D1 label `OBOROVO_SHL_BALANCE_LINEAGE_UNRESOLVED` is retired.

---

## 5. Field Classification: Raw vs Derived

All fields in `excel_oborovo_shl_operating_truth.json` are classified:

**SOURCE_RAW_CACHED_VALUE** (extracted directly from committed Excel cached values):
- `opening_balance_keur` from `shl_beginning_keur`
- `drawdown_keur` from `shl_funding_keur`
- `gross_accrued_interest_keur` from `shl_net_interest_keur`
- `pik_interest_keur` from `shl_interest_capitalised_keur`
- `closing_balance_keur` from `shl_ending_keur`
- `shl_service_keur` from `shl_service_keur`
- `sd_period_fraction_actual_360` from `sd_period_fraction`

**DETERMINISTIC_DERIVATION_FROM_SOURCE_VALUES** (computed from raw values only):
- `cash_interest_keur` = `gross_accrued_interest_keur` - `pik_interest_keur`
- `principal_repaid_keur` = `shl_service_keur` - `cash_interest_keur`
- `shl_dcf_derived_actual_365` = gross / ((opening + drawdown) x 0.08)

No derived field is labelled as independently extracted from an Excel cell.

---

## 6. Roll-Forward Identity

Verified exact for all 41 non-zero DS periods:

```
closing_balance = opening_balance + drawdown + pik_interest - principal_repaid
```

Equivalent reduced identity (where those exact definitions apply):

```
closing_balance = opening_balance + drawdown + gross_interest - shl_service
```

---

## 7. Rate and Day-Count Convention

| Parameter | Value | Source |
|---|---|---|
| Annual rate | 8.0% | Excel Inputs!F328 (SOURCE_RAW_CACHED_VALUE) |
| Day-count (SHL) | actual/365 | SHL_DAY_COUNT_DERIVED_FROM_SOURCE_VALUES |
| Day-count (senior debt) | actual/360 | sd_period_fraction column (SOURCE_RAW_CACHED_VALUE) |
| Construction DCF | 1.0 exactly | 365 days / 365 = 1.0 |

**`SHL_DAY_COUNT_DERIVED_FROM_SOURCE_VALUES`**: actual/365 is **inferred** — `gross / ((opening + drawdown) x 0.08)` matches actual calendar days / 365 for all periods. It is NOT proven by committed workbook formula text. The numerical conclusion holds; formula provenance is not directly committed.

**`SHL_SOURCE_DAY_COUNT_MISMATCH`**: SHL and senior debt use different day-count bases in the source workbook. Do not unify in C3B3D2A or later without explicit workbook formula evidence.

---

## 8. Payment Mode Classification

| DS Period Range | Mode | Evidence |
|---|---|---|
| DS[0] (construction) | `PIK` | cap == gross exactly; cash_interest = 0 |
| DS[1..24] (operating P1-P24) | `PARTIAL_CASH_PARTIAL_PIK` | 0 < cap < gross; cash_interest = gross - cap; cap fraction ~47-67% (waterfall-driven) |
| DS[25..40] (operating P25-P40) | `CASH_PAID` | cap = 0.0 exactly for all 16 periods |

**PIK to CASH switch at DS[25]** (period_end_date 2042-12-31): First period with `cap = 0`. The switch is driven by FCF waterfall availability. The `shl_pik_switch_period` field is **not** the trigger — it is unused by any runtime code.

**Payment-mode status — two separate questions:**

1. **`C3B3D2A_OBOROVO_PAYMENT_SOURCE_SEMANTICS_PROVEN`** — The source mode for each DS period is now classified from committed Excel DS values. This question is resolved.

2. **`C3B3D2B_CANONICAL_SHL_RUNTIME_BLOCKED_BY_WATERFALL_COUPLING`** — The canonical `financial_engine/shl/engine.py` supports only `CASH_PAID` or `PIK` (full). `PARTIAL_CASH_PARTIAL_PIK` (DS[1..24]) requires FCF waterfall coupling. Runtime promotion is deferred to C3B3D2B.

Do NOT interpret `C3B3D2A_OBOROVO_PAYMENT_SOURCE_SEMANTICS_PROVEN` as implying that `ProjectInputs` canonical mapping is now executable.

---

## 9. PARTIAL_CASH_PARTIAL_PIK Arithmetic — DS1 Numerical Proof

For DS[1] (period_end_date 2030-12-31):

```
gross_accrued_interest   = 636.8088084115645   (SOURCE_RAW: shl_net_interest_keur)
pik_interest_capitalised = 300.9387964834111   (SOURCE_RAW: shl_interest_capitalised_keur)
cash_interest            = gross - cap          (DERIVED)
                         = 636.8088084115645 - 300.9387964834111
                         = 335.8700119281534
principal_repaid         = 0.0                  (no principal in early operating periods)
shl_service              = 335.8700119281534    (= cash_interest + principal_repaid)
```

**The correct identity is `cash_interest = gross - cap`, NOT `service - cap`.**

`shl_service_keur` covers both cash interest payment and principal repayment:

```
shl_service = cash_interest + principal_repaid
```

For DS[25+] where principal > 0:

```
principal_repaid = shl_service - cash_interest
                 = shl_service - (gross - cap)
                 = shl_service - gross           (since cap=0 in CASH_PAID periods)
```

---

## 10. Maturity Convention — SWEEP_NOT_BULLET

DS[40] (period_end_date 2050-06-30):
- Opening balance: 2,108.1666964607866 kEUR
- Closing balance: 0.0 (exact)
- Mechanism: **SWEEP_NOT_BULLET**

The balance is not repaid in a single bullet. From DS[25] onward, each period's `shl_service` includes cash interest plus incremental principal swept from available FCF. First period with `principal_repaid > 0` is DS[25] (approximately 224.1 kEUR). By DS[40] the balance reaches exactly 0.0.

The `shl_tenor_years=20` factory field is a legacy Python configuration value. The source repayment mechanics are NOT a bullet.

---

## 11. Period Mapping (DS to Clean Index)

**Status: `C3B3D2A_PERIOD_MAPPING_FULL_HORIZON_PROVEN`**

All 40 operating period dates (DS[1..40]) are source-proven from the committed interest_limitation fixture. P1..P12 are also independently verified in `excel_oborovo_periods.json`.

| DS index | Excel period | Clean index (C3B2) | Period end date |
|---|---|---|---|
| 0 | Construction | N/A | (end inferred ~2030-06-30; not directly committed) |
| 1 | P1 | 2 | 2030-12-31 |
| 2 | P2 | 3 | 2031-06-30 |
| ... | ... | ... | ... |
| 24 | P24 | 25 | 2042-06-30 |
| 25 | P25 | 26 | 2042-12-31 (PIK to CASH switch) |
| 40 | P40 | 41 | 2050-06-30 (maturity) |

---

## 12. D2B Architecture Note — SHL Balance Depends on Waterfall

**`C3B3D2B_CANONICAL_SHL_RUNTIME_BLOCKED_BY_WATERFALL_COUPLING`**

The Oborovo gross SHL interest vector **cannot** be generated from the standalone C3B3D1 canonical schedule using only opening balance, rate, and day count fraction, because future opening balances depend on:

- partial PIK (DS[1..24]), and
- later principal sweep (DS[25..40])

both of which are driven by downstream cash availability.

Therefore D2B must NOT:
- Simply inject the Excel SHL vector into production as a static exogenous input
- Assume `run_shl_schedule()` to static gross interest vector to Tax is sufficient for Oborovo

The SHL balance trajectory depends on prior-period waterfall outcome. D2B must design the generic causal seam before any runtime promotion.

---

## 13. Stale Comment Corrections Applied in C3B3D2A

### `financial_engine/adapters/tax_inputs.py`

Removed stale "SHL cancels with fiscal reintegration" framing. SHL interest was omitted from `period_interest` because no authoritative canonical per-period SHL interest source existed before C3B3D1/D2B. Once D2B supplies `gross_accrued_interest_keur`, TaxPolicy determines deductibility. For Oborovo (`FULLY_NON_DEDUCTIBLE`) deductible SHL = 0. This is NOT a cancellation through reintegration.

### `app/project_factories.py` — `shl_amount_keur` comment

Before: `# Excel SHL draw: 13,547.2 kEUR (from oborovo_baseline.json fixture...)`

After: `# Legacy Python calibration value. Authoritative Excel Inputs!D325 = 14,620.773895 kEUR. Difference ~1073.6 kEUR remains C3B3D2A_FACTORY_VALUE_UNEXPLAINED_GAP. No runtime value change in D2A.`

### `app/project_factories.py` — `shl_tenor_years` comment

Before: `# Oborovo Excel: SHL is a 20-year bullet (Excel BS clears at 2050-06-30)...`

After: `# Legacy Python field. Source SHL clears at 2050-06-30 (Excel DS[40]). Source repayment is incremental FCF sweep (DS[25..40]), NOT a contractual bullet. No runtime value change in D2A.`

---

## 14. TUHO Secondary Evidence Inventory

TUHO status remains **`TUHO_SHL_BALANCE_LINEAGE_UNRESOLVED`** + **`C3B3D1_BLOCKED_FCF_REPAYMENT`**.

| Item | Status |
|---|---|
| TUHO SHL repayment method | `pik_then_sweep` — blocked at C3B3D1 adapter (FCF waterfall) |
| TUHO Excel workbook | Not committed; no DS fixture analogous to Oborovo |
| TUHO construction seam | Not proven; no source fixture to extract from |
| TUHO production path | Legacy waterfall engine, unchanged |
| C3B3D2A scope | No changes to TUHO; deferred to later SHL/waterfall scope |

---

## 15. Deferred to C3B3D2B

| Item | Label |
|---|---|
| Factory 13,547.2 vs Excel 14,620.77 gap origin | `C3B3D2A_FACTORY_VALUE_UNEXPLAINED_GAP` |
| PARTIAL_CASH_PARTIAL_PIK modelling in canonical engine | Requires waterfall integration |
| PIK to CASH switch trigger formalization in canonical engine | Waterfall-coupling scope |
| Runtime promotion: gross SHL interest to PeriodInterestInput | `C3B3D2_TAX_WIRING` |
| Generic causal seam design for Oborovo SHL trajectory | D2B architecture prerequisite |
| TUHO opening balance proof | `C3B3D2B_TUHO_BALANCE_PROOF` |

---

## 16. C3B3D2A Delivery Summary

| Deliverable | Status |
|---|---|
| `tests/fixtures/excel_oborovo_shl_operating_truth.json` | Provenance-locked 41-period fixture |
| `finco_recon/derive_c3b3d2a_oborovo_shl_truth.py` | Deterministic derivation script; idempotency verified |
| `tests/test_stage_c3b3d2a_oborovo_shl_source_truth.py` | Source-provenance locked tests (A-X) |
| `docs/reconciliation/c3b3d2a_oborovo_shl_source_truth.md` | This document |
| CI workflow | `c3b3d2a_oborovo_shl_source_truth_check.yml` |
| `financial_engine/adapters/tax_inputs.py` | Comment-only corrections |
| `app/project_factories.py` | Comment-only corrections |
| `OBOROVO_SHL_BALANCE_LINEAGE_RESOLVED` | 15,790.435806400885 kEUR |
| `C3B3D2A_OBOROVO_PAYMENT_SOURCE_SEMANTICS_PROVEN` | Source mode proven for all 41 DS periods |
| `C3B3D2B_CANONICAL_SHL_RUNTIME_BLOCKED_BY_WATERFALL_COUPLING` | Documented; deferred |
| `C3B3D2A_PERIOD_MAPPING_FULL_HORIZON_PROVEN` | All 40 operating dates source-proven |
| Production runtime promotion | NOT DONE (C3B3D2B scope) |
