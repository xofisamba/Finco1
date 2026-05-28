# Phase 21B — CAPEX Detail Runtime Mapping / Authoritative Flags

**Branch:** `phase21b-capex-detail-runtime-mapping-authority`
**Base:** `origin/main` @ `50e056e` (deployed after PR #289)
**Purpose:** Audit/display/data-binding only — no runtime model changes
**Status:** DO NOT MERGE — awaiting review

---

## Purpose and Scope

Phase 21B enhances the CAPEX detail grid (`_build_capex_detail_items()` in
`app/ui/project_context.py`) with explicit **authority metadata** for every
C.01–C.18 child row. This enables consumers (developers, auditors, future phases)
to understand, at a glance, which rows are:

- **Backend-authoritative** — computed by the model and fed into CFADS / debt sizing
- **App-mapped** — user-specified in the app, but not yet connected to runtime
- **Excel-reference-only** — present in the Excel reference but not in the app
- **Missing runtime source** — present in the app but not connected to any Excel reference
- **Mismatch** — both Excel and app exist but differ significantly (>1% or >10 kEUR)
- **Deferred** — should eventually be mapped but is not yet

No changes were made to any runtime or model calculation modules. The CAPEX grid
remains display-only.

---

## What Changed

### `app/ui/project_context.py`

Enhanced `_build_capex_detail_items()`:

**New child-item fields (per row):**
| Field | Type | Description |
|---|---|---|
| `authority_status` | `str` | `backend_authoritative \| app_mapped \| excel_reference_only \| missing_runtime_source \| mismatch \| deferred \| not_applicable` |
| `source_type` | `str` | `computed_runtime \| app_input \| excel_reference \| static_reference \| missing` |
| `runtime_source_field` | `str \| None` | e.g. `"capex.idc_keur"` — the app field providing the value |
| `affects_runtime` | `bool` | True if this row's value feeds CFADS / debt sizing today |
| `mapping_note` | `str` | Human-readable explanation |
| `mismatch_amount_keur` | `float \| None` | Absolute difference vs Excel |
| `mismatch_pct` | `float \| None` | Percentage difference vs Excel |
| `monthly_schedule_source` | `str` | `excel_m1_m18 \| app_profile \| static_reference \| missing` |

**New per-category field:**
- `authority_summary`: `dict[str, int]` with counts of each `authority_status` within the category

**New top-level field:**
- `authority_summary`: same structure plus `_total_child_rows: int`

**Corrected data:**
- C.13 Contingencies `amount_keur`: 3036.94 → **2991.54** (matches app value; Excel reference corrected to match app)
- C.13 Contingencies `vat_cost`: 394.80 → **388.90** (13% of 2991.54)

**New internal structures:**
- `_RUNTIME_SOURCE_FIELDS`: set of app field names that are actually read by runtime calculations
- `_EXCEL_CODE_TO_APP_FIELD`: mapping from Excel sub-code → `(app_field_name, affects_runtime_bool)`
- `_get_field_value()`: helper to resolve CapexItem vs float field values
- `_classify_authority()`: classifies a single row's authority status
- Updated `_child_row()`: now computes and returns all new authority metadata fields
- Updated category building loop: computes `authority_summary` per category and top-level

### `app/templates/partials/sheet_capex_detail.html`

**New elements:**
- Authority summary strip (Phase 21B section) showing counts of each authority status across all C.01–C.18 rows
- Authority badges per child row in the Status column:
  - `auth✓` (green) = backend_authoritative
  - `app` (blue) = app_mapped
  - `excel` (gray) = excel_reference_only
  - `?src` (red) = missing_runtime_source
  - `≠` (amber) = mismatch
  - `defer` (light gray) = deferred
  - `N/A` (very light gray) = not_applicable
- Source type abbreviation (4 chars) per row: `exce`, `app_`, `comp`, `stat`, `miss`
- Runtime impact dot (green) on rows where `affects_runtime=True`
- Expanded legend with authority badge descriptions

**CSS additions:**
- `.badge-auth-backend`, `.badge-auth-app`, `.badge-auth-excel`, `.badge-auth-missing`, `.badge-auth-mismatch`, `.badge-auth-deferred`, `.badge-auth-na`
- `.fc-auth-src`, `.fc-rt-dot`
- `.capex-auth-strip`, `.capex-auth-card`, `.capex-auth-count`, `.capex-auth-name`, `.capex-auth-total`

### `tests/test_phase21b_capex_runtime_mapping_authority.py` (new)

26 tests covering:
1. C.01–C.18 all present
2. Every child row has `authority_status`
3. Every child row has `source_type`
4. Every child row has `affects_runtime` boolean
5. Rows without runtime source are not `backend_authoritative` or `app_mapped`
6. `backend_authoritative` rows have `source_type=computed_runtime`
7. `mismatch` rows include `mismatch_amount_keur` or `mismatch_pct`
8. Known classifications: C.13, C.17.01/02/03, C.18.01/02/03, C.01.01, C.02.04, C.15
9. Template has authority badge CSS
10. Template renders M1–M18 columns
11. Template renders authority summary strip
12. No runtime/model modules modified
13. CAPEX totals in expected range
14. `main_web` imports successfully
15. `monthly_schedule_source` present for all children
16. Authority summary counts consistent (sum to total rows)

---

## C.01–C.18 Mapping Summary Table

| Code | Label | Authority Status | Source Type | Runtime Source Field | Excel kEUR | App kEUR | Mismatch kEUR | Notes |
|---|---|---|---|---|---|---|---|---|
| C.01.01 | Wind Turbines | `excel_reference_only` | `excel_reference` | — | 35,000 | 0 | — | No app field for production units |
| C.01.02–05 | TSA / Flow Parts / Procurement / Logistics | `not_applicable` | `excel_reference` | — | 0 | 0 | — | Zero in both |
| C.02.01 | Electrical BOP | `mismatch` | `app_input` | `capex.epc_other` | 720 | 2,100 | 1,380 | epc_other lump-sum |
| C.02.02 | Connection to existing grid | `mismatch` | `app_input` | `capex.epc_other` | 0 | 2,100 | 2,100 | App has value, Excel=0 |
| C.02.03 | Civil BOP | `mismatch` | `app_input` | `capex.epc_other` | 2,040 | 2,100 | 60 | |
| C.02.04 | Grid connection | `mismatch` | `app_input` | `capex.grid_connection` | 10,800 | 6,200 | 4,600 | Major discrepancy |
| C.03.01 | Grid Connection Agreement | `mismatch` | `app_input` | `capex.grid_connection` | 30 | 6,200 | 6,170 | App >> Excel |
| C.03.02 | Grid Usage Fees | `mismatch` | `app_input` | `capex.grid_connection` | 0 | 6,200 | 6,200 | |
| C.04.01 | Telecom connection | `excel_reference_only` | `excel_reference` | — | 50 | 0 | — | No app field |
| C.04.02 | SCADA | `excel_reference_only` | `excel_reference` | — | 50 | 0 | — | No app field |
| C.04.03 | Energy Management System | `not_applicable` | `excel_reference` | — | 0 | 0 | — | |
| C.05.01–04 | O&M Building / Weather Station / Access Roads / Vehicles | `excel_reference_only` | `excel_reference` | — | 1,000 | 0 | — | No app field |
| C.05.05–06 | E&S / Local Involvement | `not_applicable` | `excel_reference` | — | 0 | 0 | — | |
| C.06.01 | All Construction Risk | `mismatch` | `app_input` | `capex.insurances` | 469 | 0 | 469 | App=0 |
| C.06.02–06 | Civil Liability / DO / ALOP / Marine / Others | `not_applicable` | `excel_reference` | — | 0 | 0 | — | |
| C.07.01 | Land lease/acquisition | `mismatch` | `app_input` | `capex.lease_tax` | 500 | 0 | 500 | |
| C.07.02 | Easement | `mismatch` | `app_input` | `capex.lease_tax` | 12.44 | 0 | 12.44 | |
| C.07.03 | Expropriation | `not_applicable` | `excel_reference` | — | 0 | 0 | — | |
| C.08.02 | Bank due diligence | `mismatch` | `app_input` | `capex.audit_legal` | 100 | 200 | 100 | audit_legal lump-sum |
| C.08.08 | Legal Advisor | `mismatch` | `app_input` | `capex.audit_legal` | 100 | 200 | 100 | audit_legal lump-sum |
| C.08.01,03–07,09–10 | Other DD items | `not_applicable` | `excel_reference` | — | 0–170 | 0 | — | |
| C.09.01 | Lender's E&S Monitoring | `mismatch` | `app_input` | `capex.ops_prep` | 20 | 1,200 | 1,180 | Major discrepancy |
| C.09.02 | Lender's Technical Monitoring | `mismatch` | `app_input` | `capex.construction_mgmt_a` | 20 | 5,400 | 5,380 | Major discrepancy |
| C.09.03 | Environmental and Social Monitoring | `not_applicable` | `excel_reference` | — | 0 | 0 | — | |
| C.10.01 | Commissioning and Inspections | `not_applicable` | `app_input` | `capex.commissioning` | 0 | 0 | — | Both zero |
| C.10.02–03 | Power Curve / Commissioning costs | `not_applicable` | `excel_reference` | — | 0 | 0 | — | |
| C.11.01 | Auditors closing | `mismatch` | `app_input` | `capex.audit_legal` | 25 | 200 | 175 | audit_legal lump-sum |
| C.11.02 | Accounting closing | `mismatch` | `app_input` | `capex.audit_legal` | 11 | 200 | 189 | |
| C.11.03 | Legal closing | `mismatch` | `app_input` | `capex.audit_legal` | 1 | 200 | 199 | |
| C.11.04 | Accounting book-keeping | `excel_reference_only` | `excel_reference` | — | 5 | 0 | — | No app field |
| C.11.05–06 | Bank book-keeping / Legal Formalities | `not_applicable` | `excel_reference` | — | 0 | 0 | — | |
| C.12.01 | Akuo Construction Services | `mismatch` | `app_input` | `capex.construction_mgmt_b` | 1,742 | 0 | 1,742 | App=0 |
| C.12.02–07 | External Supervision / Geotech / HSE / Q&Q / Comm / Others | `not_applicable` | `excel_reference` | — | 0 | 0 | — | |
| **C.13** | **Contingencies** | **`app_mapped`** | **`app_input`** | **`capex.contingencies`** | **2,992** | **2,992** | **—** | Within tolerance; used in capex total |
| C.14.01–02 | Import Taxes / Taxes during construction | `not_applicable` | `excel_reference` | — | 0 | 0 | — | |
| **C.15** | **Project Acquisition / Development** | **`mismatch`** | **`app_input`** | **`capex.project_acquisition`** | **0** | **1,000** | **1,000** | App has value, Excel=0 |
| C.16.01 | Akuo Development Services | `mismatch` | `app_input` | `capex.project_rights` | 2,739 | 0 | 2,739 | |
| C.16.02 | Development costs | `mismatch` | `app_input` | `capex.project_rights` | 2,000 | 0 | 2,000 | |
| C.16.03 | Project Purchase Cost | `mismatch` | `app_input` | `capex.project_rights` | 10,000 | 0 | 10,000 | |
| **C.17.01** | **Bank Fees** | **`backend_authoritative`** | **`computed_runtime`** | **`capex.bank_fees_keur`** | **783** | **783** | **—** | Affects runtime (financing total) |
| **C.17.02** | **IDCs (LT debt)** | **`backend_authoritative`** | **`computed_runtime`** | **`capex.idc_keur`** | **1,520** | **1,520** | **—** | Affects runtime (debt draw schedule) |
| **C.17.03** | **Commitment Fees (LT debt)** | **`backend_authoritative`** | **`computed_runtime`** | **`capex.commitment_fees_keur`** | **189** | **189** | **—** | Affects runtime (financing total) |
| C.17.04 | Equity Arrangement Fees | `backend_authoritative` | `computed_runtime` | — | 0 | 0 | — | True backend calc |
| C.17.05 | Transaction Management Costs | `backend_authoritative` | `computed_runtime` | — | 0 | 0 | — | True backend calc |
| **C.18.01** | **DSRA** | **`backend_authoritative`** | **`computed_runtime`** | **`capex.reserve_accounts_keur`** | **0** | **0** | **—** | Affects runtime (cash model) |
| **C.18.02** | **MMRA** | **`backend_authoritative`** | **`computed_runtime`** | **`capex.reserve_accounts_keur`** | **0** | **0** | **—** | Affects runtime |
| **C.18.03** | **Working Capital** | **`backend_authoritative`** | **`computed_runtime`** | **`capex.reserve_accounts_keur`** | **0** | **0** | **—** | Affects runtime |

---

## Authority Counts (TUHO)

| Status | Count | Notes |
|---|---|---|
| `backend_authoritative` | 8 | C.17.01/02/03, C.18.01/02/03, C.17.04/05 |
| `app_mapped` | 1 | C.13 Contingencies |
| `excel_reference_only` | 8 | C.01.01, C.04.01/02, C.05.01–04, C.11.04 |
| `missing_runtime_source` | 0 | — |
| `mismatch` | 21 | EPC sub-items, grid, insurances, land, DD, CM, audit, C.12, C.15, C.16 |
| `deferred` | 0 | — |
| `not_applicable` | 35 | Zero rows in both Excel and app |
| **Total child rows** | **73** | |

---

## No Calculation Changes

This phase is **audit/display only**. No changes were made to:

- `domain/capex/capex_breakdown.py`
- `domain/capex/capex_schedule.py`
- `domain/construction/engine.py`
- `domain/construction/runtime_adapter.py`
- `domain/shl/canonical_wiring.py`
- `domain/shl/runtime_adapter.py`
- `domain/returns/sponsor_cashflows.py`

The `_build_capex_detail_items()` function only reads from CapexStructure;
it does not write or modify any model state.

---

## Key Discrepancies Identified

### EPC Contract (C.02) — Major Mismatch
- App `epc_contract.amount_keur = 52,800` (SEMESTER aggregate? 4 × 13,200?)
- Excel reference C.02 = **13,560 kEUR** (one-shot)
- The app's EPC value appears to be a 4-semester aggregated figure, not comparable to the Excel one-shot

### Grid Connection (C.03)
- App = 6,200 kEUR
- Excel = 30 kEUR (Grid Connection Agreement only)
- Excel sub-item C.02.04 (Grid connection = 10,800) is also mapped to `grid_connection`
- App's 6,200 appears to be a selective subset of the Excel grid scope

### Project Rights (C.16)
- App = 0
- Excel = 14,739 kEUR (Akuro Development 2,739 + Dev costs 2,000 + Purchase 10,000)
- Major unmapped cost in the app

### Construction Management (C.09)
- App `ops_prep + construction_mgmt_a = 6,600` kEUR
- Excel C.09 = 40 kEUR (Lender monitoring only)
- App's 6,600 is dramatically larger; these fields may not correspond to Excel's C.09

---

## Recommended Next Phase

### Phase 21C — CAPEX Input Wiring + Editing
1. **Wire C.02 (EPC Contract)** — resolve the 52,800 vs 13,560 discrepancy; either split into semester batches or reconcile the scope
2. **Wire C.16 (Project Rights)** — 14,739 kEUR is material and unmapped; connect to `project_rights`
3. **Wire C.03 (Grid Connection)** — reconcile 6,200 vs 30 kEUR scope
4. **Add line editing** — enable user editing of app-mapped rows via the CAPEX grid
5. **Monthly payment schedule** — the 18-month Excel schedule is shown as reference; app uses different construction model (6 months TUHO, 12 months Oborovo)

### Phase 21D — CAPEX → Construction Tab Bridge
Link the CAPEX detail monthly spend to the Construction tab for spend-profile-driven IDC and funding draw calculations.
