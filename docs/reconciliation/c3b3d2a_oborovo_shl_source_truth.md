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

**Period date fixture identity note:** The IL fixture uses source workbook name
`20260414_BP_Oborovo_Sensitivity_FINAL for PPT (1).xlsm` (no SHA). It is not
cryptographically tied to the primary fixture's SHA. Cross-verification via exact gross
interest match (r27 == shl_net_interest for all 40 operating periods) provides strong
evidence linkage but not binary-identity proof.

---

## 3. Five Conflicting Values — Classification

| Value (kEUR) | Source | Cell / Origin | Status |
|---|---|---|---|
| **14,620.77** | Excel Inputs!D325 | `d49af8ee-...xlsm` cached value | **AUTHORITATIVE — Excel raw SHL draw** |
| **1,169.66** | Excel DS[0].cap | Construction PIK = 14620.77 × rate × 1.0 | **AUTHORITATIVE — construction IDC** |
| **15,790.44** | Excel DS[0].end = DS[1].beg | 14620.77 + 1169.66 | **AUTHORITATIVE — operating opening balance** |
| **13,547.2** | `app/project_factories.py:373` | Parity-baseline calibration reversion (see provenance below) | **KNOWN_SOURCE_CONFLICT — C3B3D2A_FACTORY_CALIBRATION_REVERSION_PROVEN** |
| **1,169.0** | `app/project_factories.py:393` comment | Rounded IDC in stale comment | **STALE COMMENT — corrected** |

### Factory Value Provenance Chronology

The ~1,073.6 kEUR gap between 14,620.77 (Excel) and 13,547.2 (factory) has a known history:

- **PR #309** (Phase 23L, commit `34ed6d0b22084e16d4c42d2c7fbf0ea68b1ac5fe`):
  corrected `shl_amount_keur` from `13547.2` → `14621` (moving toward Excel source).

- **PR #752** (Stack D, commit `099e4a14f920cf618b06d850f567374c0c8b9a95`):
  reverted `14621` → `13547.2` to restore parity with `oborovo_baseline.json`
  (`shl_amount_keur: 13547.2`). The reversion was a deliberate calibration decision,
  not a mistake.

**`C3B3D2A_FACTORY_CALIBRATION_REVERSION_PROVEN`**: The factory value 13,547.2 is a
deliberate parity-baseline calibration value. Its divergence from Excel Inputs!D325
(14,620.77) is a **KNOWN_SOURCE_CONFLICT** (`C3B3D2A_FACTORY_VALUE_CONFLICTS_WITH_AUTHORITATIVE_SOURCE`).
Resolution deferred to C3B3D2B. Do NOT change `shl_amount_keur=13547.2` in D2A.

---

## 4. Construction→Operating Balance Seam

The construction→operating opening balance seam (`C3B3D2_CONSTRUCTION_SEAM` from C3B3D1) is now resolved for Oborovo:

```
DS[0].beg  = 0.0                         (SHL opens at zero)
DS[0].fund = 14,620.773894815633         (Excel Inputs!D325 — full SHL draw at construction close)
DS[0].dcf  = 1.0                         (CONSTRUCTION_SHL_DCF_SOURCE_IMPLIED_1_0; see Section 7)
DS[0].cap  = 14620.77 x rate x 1.0 = 1,169.6619115852516   (100% PIK — construction)
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
- `shl_annual_rate` (0.08) from `Inputs!F328`

**DETERMINISTIC_DERIVATION_FROM_SOURCE_VALUES** (computed from raw values only):
- `cash_interest_keur` = `gross_accrued_interest_keur` - `pik_interest_keur`
- `principal_repaid_keur` = `shl_service_keur` - `cash_interest_keur`
- `shl_dcf_derived_actual_365` = gross / ((opening + drawdown) x shl_rate_from_Inputs_F328)

No derived field is labelled as independently extracted from an Excel cell.
The derivation script uses the rate from `inp["shl_interest_rate"]["value"]` — no hardcoded constant.

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
| Day-count (SHL, operating) | actual/365 | OPERATING_SHL_DAY_COUNT_DERIVED_FROM_SOURCE_VALUES |
| Day-count (senior debt) | actual/360 | sd_period_fraction column (SOURCE_RAW_CACHED_VALUE) |
| Construction DCF | 1.0 exactly | CONSTRUCTION_SHL_DCF_SOURCE_IMPLIED_1_0 (see below) |

**`OPERATING_SHL_DAY_COUNT_DERIVED_FROM_SOURCE_VALUES`**: actual/365 is **inferred** for
all operating periods — `gross / ((opening + drawdown) x shl_rate)` matches actual calendar
days / 365 for all DS[1..40]. It is NOT proven by committed workbook formula text.

**`CONSTRUCTION_SHL_DCF_SOURCE_IMPLIED_1_0`**: The construction DCF = 1.0 is **implied by
arithmetic**: `gross / (draw x rate) = 1169.66 / (14620.77 x 0.08) = 1.0` exactly. This
does NOT rest on a claimed 365-calendar-day count. The exact construction interval dates are
not directly committed in this fixture. Known date evidence: construction_parity fixture shows
2029-06-29 → 2030-06-29; IL fixture shows DS[1].start = 2030-07-01 — potential 2-day gap at
the construction/operating seam. This is unresolved at C3B3D2A scope.

**`SHL_SOURCE_DAY_COUNT_MISMATCH`**: SHL and senior debt use different day-count bases in the
source workbook. Do not unify in C3B3D2A or later without explicit workbook formula evidence.

---

## 8. Payment Mode Classification

| DS Period Range | Mode | Evidence |
|---|---|---|
| DS[0] (construction) | `PIK` | cap >= gross (tol 1e-9); cash_interest = 0 |
| DS[1..24] (operating P1-P24) | `PARTIAL_CASH_PARTIAL_PIK` | cap > 0 and cash > 0; cash_interest = gross - cap; cap fraction ~47-67% (waterfall-driven) |
| DS[25..40] (operating P25-P40) | `CASH_PAID` | cap = 0.0 exactly for all 16 periods |

**Classification method**: payment mode is VALUE-DERIVED from `cap` vs `gross` source values
(tolerance 1e-9), NOT from a hardcoded `ds_idx <= 24` comparison. The DS[25] boundary is
**discovered from data** — the derivation script discovers `first_cash_paid_ds_index = 25`
as a result, not an input.

**PIK to CASH switch at DS[25]** (period_end_date 2042-12-31): First period with `cap = 0`.
The switch is driven by FCF waterfall availability. The `shl_pik_switch_period` field is
**not** the trigger — it is unused by any runtime code.

**Payment-mode status — two separate questions:**

1. **`C3B3D2A_OBOROVO_PAYMENT_SOURCE_SEMANTICS_PROVEN`** — The source mode for each DS period
is now classified from committed Excel DS values. This question is resolved.

2. **`C3B3D2B_CANONICAL_SHL_RUNTIME_BLOCKED_BY_WATERFALL_COUPLING`** — The canonical
`financial_engine/shl/engine.py` supports only `CASH_PAID` or `PIK` (full).
`PARTIAL_CASH_PARTIAL_PIK` (DS[1..24]) requires FCF waterfall coupling. Runtime promotion
is deferred to C3B3D2B.

Do NOT interpret `C3B3D2A_OBOROVO_PAYMENT_SOURCE_SEMANTICS_PROVEN` as implying that
`ProjectInputs` canonical mapping is now executable.

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

The balance is not repaid in a single bullet. From DS[25] onward, each period's `shl_service`
includes cash interest plus incremental principal swept from available FCF. First period with
`principal_repaid > 0` is DS[25] (approximately 224.1 kEUR) — discovered from data, not asserted
by a hardcoded index. By DS[40] the balance reaches exactly 0.0.

The `shl_tenor_years=20` factory field is a legacy Python configuration value. The source
repayment mechanics are NOT a bullet.

---

## 11. Period Mapping (DS to Clean Index)

**Status: `C3B3D2A_PERIOD_MAPPING_FULL_HORIZON_COMMITTED_FIXTURE_PROVEN`**

All 40 operating period dates (DS[1..40]) are proven from the committed IL fixture
(`tests/fixtures/interest_limitation/oborovo_interest_limitation_fixture.json`).
P1..P12 are also independently verified in `excel_oborovo_periods.json`.

**Fixture identity caveat:** The IL fixture uses a source workbook filename without a SHA
(`20260414_BP_Oborovo_Sensitivity_FINAL for PPT (1).xlsm`). The status is
`C3B3D2A_PERIOD_MAPPING_FULL_HORIZON_COMMITTED_FIXTURE_PROVEN` — proven from a committed
fixture, not from a single cryptographically-identified workbook binary.

| DS index | Excel period | Clean index (C3B2) | Period end date |
|---|---|---|---|
| 0 | Construction | N/A | (end inferred ~2030-06-30; not directly committed) |
| 1 | P1 | 2 | 2030-12-31 |
| 2 | P2 | 3 | 2031-06-30 |
| ... | ... | ... | ... |
| 24 | P24 | 25 | 2042-06-30 |
| 25 | P25 | 26 | 2042-12-31 (PIK to CASH switch — discovered from data) |
| 40 | P40 | 41 | 2050-06-30 (maturity) |

---

## 12. D2B Architecture Note — SHL Balance Depends on Waterfall

**`C3B3D2B_CANONICAL_SHL_RUNTIME_BLOCKED_BY_WATERFALL_COUPLING`**

The Oborovo gross SHL interest vector **cannot** be generated from the standalone C3B3D1
canonical schedule using only opening balance, rate, and day count fraction, because future
opening balances depend on:

- partial PIK (DS[1..24]), and
- later principal sweep (DS[25..40])

both of which are driven by downstream cash availability.

Therefore D2B must NOT:
- Simply inject the Excel SHL vector into production as a static exogenous input
- Assume `run_shl_schedule()` to static gross interest vector to Tax is sufficient for Oborovo

The SHL balance trajectory depends on prior-period waterfall outcome. D2B must design the
generic causal seam before any runtime promotion.

**D2B Prerequisites (A–E):**

A. **Generic causal seam design**: Define the interface by which the waterfall engine supplies
   `cash_available_for_shl` to the SHL scheduler on a per-period basis.

B. **PARTIAL_CASH_PARTIAL_PIK modelling**: Extend `financial_engine/shl/engine.py` to accept
   a per-period cash_available input, allowing partial PIK when cash < gross.

C. **PIK-to-CASH switch trigger**: Formalize the FCF waterfall trigger condition
   (`cf_for_shl > shl_balance * rate`) in the canonical engine.

D. **KNOWN_SOURCE_CONFLICT resolution**: Reconcile `factory shl_amount_keur=13547.2` vs
   `Excel Inputs!D325=14620.77`. Not required before D2B runtime work, but must be resolved
   before any production SHL balance trajectory is computed.

E. **TUHO balance proof**: `TUHO_SHL_BALANCE_LINEAGE_UNRESOLVED` must be resolved before
   TUHO SHL can be promoted to canonical runtime.

---

## 13. Stale Comment Corrections Applied in C3B3D2A

### `financial_engine/adapters/tax_inputs.py`

Removed stale "SHL cancels with fiscal reintegration" framing. SHL interest was omitted from
`period_interest` because no authoritative canonical per-period SHL interest source existed
before C3B3D1/D2B. Once D2B supplies `gross_accrued_interest_keur`, TaxPolicy determines
deductibility. For Oborovo (`FULLY_NON_DEDUCTIBLE`) deductible SHL = 0. This is NOT a
cancellation through reintegration.

### `app/project_factories.py` — `shl_amount_keur` comment (R2 update)

Updated to document provenance chronology:
`C3B3D2A_FACTORY_CALIBRATION_REVERSION_PROVEN / KNOWN_SOURCE_CONFLICT.
Excel Inputs!D325=14620.77 kEUR. PR #309 (34ed6d0b) corrected to 14621; PR #752 (099e4a14)
reverted to 13547.2 to match oborovo_baseline.json parity. No runtime value change in D2A.`

### `app/project_factories.py` — `shl_idc_keur` comment (R2 update)

Updated label from `C3B3D2A_FACTORY_VALUE_UNEXPLAINED_GAP` to `KNOWN_SOURCE_CONFLICT /
C3B3D2A_FACTORY_CALIBRATION_REVERSION_PROVEN`.

### `app/project_factories.py` — `shl_tenor_years` comment

`# Legacy Python field. Source SHL clears at 2050-06-30 (Excel DS[40]). Source repayment
is incremental FCF sweep (DS[25..40]), NOT a contractual bullet. No runtime value change in D2A.`

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
| Factory 13,547.2 vs Excel 14,620.77 conflict resolution | `KNOWN_SOURCE_CONFLICT` (provenance now documented; runtime resolution deferred) |
| PARTIAL_CASH_PARTIAL_PIK modelling in canonical engine | Requires waterfall integration (D2B Prereq B) |
| PIK to CASH switch trigger formalization in canonical engine | Waterfall-coupling scope (D2B Prereq C) |
| Runtime promotion: gross SHL interest to PeriodInterestInput | `C3B3D2_TAX_WIRING` |
| Generic causal seam design for Oborovo SHL trajectory | D2B architecture prerequisite A |
| TUHO opening balance proof | `C3B3D2B_TUHO_BALANCE_PROOF` (D2B Prereq E) |
| Construction interval date ambiguity (cod_date vs DS[1].start) | Unresolved; does not block D2A |

---

## 16. C3B3D2A Delivery Summary

| Deliverable | Status |
|---|---|
| `tests/fixtures/excel_oborovo_shl_operating_truth.json` | Provenance-locked 41-period fixture |
| `finco_recon/derive_c3b3d2a_oborovo_shl_truth.py` | Deterministic derivation; rate from fixture (not hardcoded); value-derived payment classification; idempotency verified |
| `tests/test_stage_c3b3d2a_oborovo_shl_source_truth.py` | 55 tests (A-X + governance + IL cross-check) |
| `docs/reconciliation/c3b3d2a_oborovo_shl_source_truth.md` | This document |
| CI workflow | `c3b3d2a_oborovo_shl_source_truth_check.yml` |
| `financial_engine/adapters/tax_inputs.py` | Comment-only corrections |
| `app/project_factories.py` | Comment-only corrections (R2: provenance chronology) |
| `OBOROVO_SHL_BALANCE_LINEAGE_RESOLVED` | 15,790.435806400885 kEUR |
| `C3B3D2A_OBOROVO_PAYMENT_SOURCE_SEMANTICS_PROVEN` | Source mode proven; DS25 boundary discovered from data |
| `C3B3D2A_FACTORY_CALIBRATION_REVERSION_PROVEN` | PR #309 / PR #752 provenance documented |
| `C3B3D2A_FACTORY_VALUE_CONFLICTS_WITH_AUTHORITATIVE_SOURCE` | KNOWN_SOURCE_CONFLICT labeled; deferred to D2B |
| `CONSTRUCTION_SHL_DCF_SOURCE_IMPLIED_1_0` | DCF=1.0 proven by arithmetic; no false calendar-day claim |
| `OPERATING_SHL_DAY_COUNT_DERIVED_FROM_SOURCE_VALUES` | Separated from construction label |
| `C3B3D2B_CANONICAL_SHL_RUNTIME_BLOCKED_BY_WATERFALL_COUPLING` | Documented; D2B Prereqs A-E listed |
| `C3B3D2A_PERIOD_MAPPING_FULL_HORIZON_COMMITTED_FIXTURE_PROVEN` | All 40 operating dates proven from committed fixture |
| Production runtime promotion | NOT DONE (C3B3D2B scope) |
| `C3B3D2A_OBOROVO_SHL_SOURCE_TRUTH_READY_FOR_SQUASH_MERGE` | **YES** |
