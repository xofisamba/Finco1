# C3B3D2A — Oborovo SHL Source Truth & Construction→Operating Seam

**Stage:** C3B3D2A  
**Branch:** `stage-c3b3d2a-oborovo-shl-source-truth`  
**Blockers resolved:** `OBOROVO_SHL_BALANCE_LINEAGE_UNRESOLVED`, `C3B3D1_BLOCKED_PAYMENT_MODE_SEMANTICS` (evidence gathered, mode classified)  
**Scope:** Source-evidence classification only. No production runtime promotion.

---

## 1. Purpose

C3B3D1 left three blockers unresolved:
1. `OBOROVO_SHL_BALANCE_LINEAGE_UNRESOLVED` — exact construction→operating opening balance unknown
2. `C3B3D1_BLOCKED_PAYMENT_MODE_SEMANTICS` — `shl_pik_switch_period=0` has no proven mapping to CASH_PAID
3. Five conflicting SHL values in the repository with undocumented provenance

C3B3D2A resolves these by extracting the authoritative schedule from the committed Excel fixture and classifying every value by its workbook source. No Python model output is used as source truth. No production paths are changed.

---

## 2. Source Workbook Identity

| Field | Value |
|---|---|
| Filename | `d49af8ee-20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm` |
| SHA-256 | `15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920` |
| Committed fixture | `tests/fixtures/excel_oborovo_financial_truth.json` |
| Extraction method | openpyxl `data_only=True` (cached values); `data_only=False` (formula text) |
| Workbook NOT in repo | Raw XLSM not committed; all evidence from committed fixtures |

---

## 3. Five Conflicting Values — Classification

| Value (kEUR) | Source | Cell / Origin | Status |
|---|---|---|---|
| **14,620.77** | Excel Inputs!D325 | `d49af8ee-...xlsm` cached value | **AUTHORITATIVE — Excel raw SHL draw** |
| **1,169.66** | Excel DS[0].cap | Construction PIK = 14620.77 × 0.08 × 1.0 | **AUTHORITATIVE — construction IDC** |
| **15,790.44** | Excel DS[0].end = DS[1].beg | 14620.77 + 1169.66 | **AUTHORITATIVE — operating opening balance** |
| **13,547.2** | `app/project_factories.py:373` | Labelled "from oborovo_baseline.json fixture" | **PYTHON CALIBRATION — NOT Excel source** |
| **1,169.0** | `app/project_factories.py:393` comment | Rounded IDC in stale comment | **STALE COMMENT — not a standalone source value** |

The ~1,073.6 kEUR gap between 14,620.77 (Excel) and 13,547.2 (factory) is unexplained in C3B3D2A scope. Origin deferred to C3B3D2B with committed oborovo_baseline.json lineage evidence. Label: `C3B3D2A_FACTORY_VALUE_UNEXPLAINED_GAP`.

---

## 4. Construction→Operating Balance Seam

The construction→operating opening balance seam (`C3B3D2_CONSTRUCTION_SEAM` from C3B3D1) is now resolved for Oborovo:

```
DS[0].beg  = 0.0                         (SHL opens at zero)
DS[0].fund = 14,620.773894815633         (Excel Inputs!D325 — full SHL draw at construction close)
DS[0].dcf  = 1.0                         (365 calendar days → actual/365 = 1.0 exactly)
DS[0].cap  = 14620.77 × 0.08 × 1.0 = 1,169.6619115852516   (100% PIK — construction)
DS[0].end  = 0 + 14620.77 + 1169.66 = 15,790.435806400885  (construction closing balance)

DS[1].beg  = 15,790.435806400885         (= DS[0].end — no gap)
```

**`OBOROVO_SHL_BALANCE_LINEAGE_RESOLVED`**: The operating opening balance is **15,790.435806400885 kEUR**, proven from the committed fixture roll-forward. The C3B3D1 label `OBOROVO_SHL_BALANCE_LINEAGE_UNRESOLVED` is retired.

---

## 5. Roll-Forward Identity

The balance roll-forward identity is verified exact for all 41 non-zero DS periods:

```
end = beg + fund + cap - principal_repaid
    = beg + fund + (gross - cash_interest) - (svc - cash_interest)
    = beg + fund + gross - svc          [for periods with cash interest]
    = beg + fund + cap                  [for PIK-only periods]
```

where `principal_repaid = svc - cash_interest` (service covers interest first; residual is principal).

No period fails this identity. All arithmetic is in the committed fixture.

---

## 6. Rate and Day-Count Convention

| Parameter | Value | Source |
|---|---|---|
| Annual rate | 8.0% | Excel Inputs!F328 |
| Day-count (SHL) | actual/365 | Derived: gross / (beg × 0.08) = actual days / 365 |
| Day-count (senior debt) | actual/360 | `sd_period_fraction` column in DS fixture |
| Construction DCF | 1.0 exactly | 365 days / 365 = 1.0 |

**`SHL_SOURCE_DAY_COUNT_MISMATCH`**: SHL and senior debt use different day-count bases in the source workbook. This is source fact — do not unify in C3B3D2A or later without explicit workbook formula evidence.

---

## 7. Payment Mode Classification

| DS Period Range | Mode | Evidence |
|---|---|---|
| DS[0] (construction) | `PIK` | `cap = gross` exactly; `cash_interest = 0` |
| DS[1..24] (operating P1–P24) | `PARTIAL_CASH_PARTIAL_PIK` | `0 < cap < gross`; cash settled = `svc - cap`; cap fraction ≈ 47–67% |
| DS[25..40] (operating P25–P40) | `CASH_PAID` | `cap = 0.0` exactly for all 16 periods |

**PIK→CASH switch at DS[25]**: First period with `cap = 0`. The switch is driven by FCF waterfall availability (legacy engine computes `pik_switch_triggered` from `cf_for_shl > shl_balance × shl_rate`). The `shl_pik_switch_period` field is **not** the trigger — it is unused by any runtime code.

**Implication for canonical engine**: The canonical `financial_engine/shl/engine.py` supports only `CASH_PAID` or `PIK` (full). `PARTIAL_CASH_PARTIAL_PIK` (DS[1..24]) requires FCF waterfall coupling. The canonical engine **cannot** reproduce the Oborovo operating schedule for periods DS[1..24] in C3B3D1/D2A scope. This is deferred to C3B3D2B waterfall integration.

---

## 8. Maturity Convention

| Field | Value |
|---|---|
| Maturity DS index | 40 |
| Closing balance | 0.0 (exact) |
| Opening balance | 2,108.1666964607866 kEUR |
| Mechanism | `SWEEP_NOT_BULLET` |

The balance is not repaid in a single bullet. From DS[25] onward, each period's `svc` includes cash interest plus incremental principal (swept from FCF). By DS[40] the balance reaches exactly 0.0. The term "bullet" in `shl_repayment_method` field context does not describe the actual repayment mechanics in the workbook.

Clean period index mapping (C3B2 convention): DS[40] = Excel operating period 40 = `clean_period_index` 41 (offset +1 for operating periods).

---

## 9. Period Mapping (DS → Clean Index)

| DS index | Excel period label | Clean period index (C3B2) | Period end approx. |
|---|---|---|---|
| 0 | Construction | N/A | ~2029-12-31 |
| 1 | P1 | 2 | 2030-12-31 |
| 2 | P2 | 3 | 2031-06-30 |
| … | … | … | … |
| 25 | P25 | 26 | ~2042-12-31 (PIK→CASH) |
| 40 | P40 | 41 | 2050-06-30 (maturity) |

Source for period-end dates P1–P12: `tests/fixtures/excel_oborovo_periods.json`. Dates P13–P40 are not committed and are estimated from the semiannual pattern (Jun/Dec alternating).

---

## 10. Gross Interest Vector (DS[0..40])

Full vector is in `tests/fixtures/excel_oborovo_shl_operating_truth.json` → `periods[*].gross_accrued_interest_keur`.

This vector is the authoritative source for `PeriodInterestInput.shl_interest_keur` once D2B wiring is complete. In C3B3D2A it is read-only source evidence.

---

## 11. Stale Comment Corrections Applied in C3B3D2A

### `financial_engine/adapters/tax_inputs.py`

**Before (stale):**
```
# FR = full SHL reintegration (thin_cap_enabled=False → C59=1.0, D59=True)
# For ATAD=False + thin_cap=False: TI = EBITDA - tax_dep - senior_interest (SHL cancels)
...
# SHL interest is excluded
# because for ATAD=False projects it cancels with fiscal reintegration.
```

**After (corrected):**
```
# SHL interest is omitted from period_interest here because no authoritative
# canonical per-period SHL interest source existed before C3B3D1/D2B.
# Once D2B supplies gross_accrued_interest_keur, TaxPolicy determines deductibility.
# For Oborovo: ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE → deductible SHL = 0.
# This is NOT a "cancellation through fiscal reintegration."
```

The original framing conflated deductibility policy (TaxPolicy) with the reason SHL was absent from the input struct. The absence was a data availability gap, not a modelling identity.

### `app/project_factories.py`

**Before (stale comment at line 393):**
```python
shl_idc_keur=1169.0,  # opening SHL balance = 14,621 + 1,169 = 15,790
```

**After (corrected):**
```python
shl_idc_keur=1169.0,  # C3B3D2A: Excel construction IDC = 1169.66; rounded here; factory shl_amount_keur=13547.2 differs from Excel D325=14620.77 by ~1073.6 kEUR (C3B3D2A_FACTORY_VALUE_UNEXPLAINED_GAP)
```

---

## 12. TUHO Secondary Evidence Inventory

TUHO status remains **`TUHO_SHL_BALANCE_LINEAGE_UNRESOLVED`** + **`C3B3D1_BLOCKED_FCF_REPAYMENT`**.

| Item | Status |
|---|---|
| TUHO SHL repayment method | `pik_then_sweep` — blocked at C3B3D1 adapter (FCF waterfall) |
| TUHO Excel workbook | Not committed; no fixture analogous to `excel_oborovo_financial_truth.json` |
| TUHO construction seam | Not proven; no DS fixture to extract from |
| TUHO production path | Legacy waterfall engine, unchanged |
| C3B3D2A scope | No changes to TUHO; deferred to later SHL/waterfall scope |

---

## 13. Deferred to C3B3D2B

| Item | Label |
|---|---|
| Factory 13,547.2 vs Excel 14,620.77 gap origin | `C3B3D2A_FACTORY_VALUE_UNEXPLAINED_GAP` |
| PARTIAL_CASH_PARTIAL_PIK modelling in canonical engine | Requires waterfall integration |
| Exact PIK→CASH switch trigger formalization | `C3B1_BLOCKED_PAYMENT_MODE_SEMANTICS` |
| Wiring gross_accrued_interest → PeriodInterestInput | `C3B3D2_TAX_WIRING` |
| TUHO opening balance proof | `C3B3D2B_TUHO_BALANCE_PROOF` |
| Period-end dates DS[13..40] | Not committed; estimated from semiannual pattern |

---

## 14. C3B3D2A Delivery Summary

| Deliverable | Status |
|---|---|
| `tests/fixtures/excel_oborovo_shl_operating_truth.json` | Created — 41-period immutable fixture |
| `docs/reconciliation/c3b3d2a_oborovo_shl_source_truth.md` | Created — this document |
| `financial_engine/adapters/tax_inputs.py` stale comments | Corrected — no logic change |
| `app/project_factories.py` stale comment | Corrected — no logic change |
| Source-truth tests (`TestC3B3D2AFixtureCoherence`) | Added |
| CI workflow (`c3b3d2a_oborovo_shl_source_truth_check.yml`) | Added |
| Zero financial drift (Oborovo, TUHO, Solar, Wind) | Verified |
| `OBOROVO_SHL_BALANCE_LINEAGE_UNRESOLVED` | **RESOLVED** → 15,790.435806400885 kEUR |
| `C3B3D2A_FACTORY_VALUE_UNEXPLAINED_GAP` | Documented, deferred to C3B3D2B |
| Production runtime promotion | **NOT DONE** — C3B3D2B scope |
