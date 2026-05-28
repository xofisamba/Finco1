# Phase 21C — CAPEX Runtime Mapping Cleanup

**Branch:** `phase21c-capex-runtime-mapping-cleanup`
**Base:** `origin/main` @ `c65c7e2` (Phase 21B merged, PR #291)
**Goal:** Correctly classify the largest CAPEX mapping mismatches — EPC Contract (C.02), Grid Connection (C.03), Project Rights (C.16) — as `scope_mismatch` rather than plain `mismatch`, with enriched mapping notes
**Status:** DO NOT MERGE — awaiting review

---

## Purpose and Scope

Phase 21C enhances Phase 21B's authority classification by introducing a new **`scope_mismatch`** status for rows where app and Excel represent fundamentally **different scopes** — not simple value discrepancies. This distinction prevents misleading audit signals and gives developers clearer guidance about which mismatches need resolution vs. which are model-level structural differences.

This is **mapping/audit-only — no runtime model changes**.

---

## What Changed

### `app/ui/project_context.py`

**New status value:** `scope_mismatch` (distinct from plain `mismatch`)

**New helper function:** `_scope_desc()` — short human-readable description of the app scope for each scope-mismatch row

**Updated `_classify_authority()`:** Early branch that intercepts known scope-mismatch codes before the threshold test:
- `C.01.01` — no app production-unit field (Wind Turbines) vs Excel 35,000
- `C.02` — `epc_contract` = 52,800 kEUR (4-semester total) vs Excel 13,560 kEUR (per-batch reference)
- `C.03.01` — `grid_connection` = 6,200 kEUR (full interconnection) vs Excel 30 kEUR (GPA fee only)
- `C.16.01/02/03` — no app field maps to Project Rights vs Excel 14,739 kEUR

**Updated authority_summary tracking:** Added `scope_mismatch` to `_STATUS_COUNTS` and `_TOP_COUNTS` in both per-category and top-level summaries.

### `app/templates/partials/sheet_capex_detail.html`

**New badge:** `≠scp` (amber/gold) with `badge-auth-scope-mismatch` CSS (distinct from plain `≠ mismatch`)
**Authority strip:** Added `capex-auth-card--scope-mismatch` card in the summary strip
**Legend:** Added scope_mismatch to Phase 21B authority legend
**Styling:** Amber/gold (`#ca8a04`) for scope-mismatch badge/card — visually distinct from mismatch (`#d97706`)

### `tests/test_phase21b_capex_runtime_mapping_authority.py`

Updated `VALID_STATUSES` to include `scope_mismatch` (1-line change)

### `tests/test_phase21c_capex_runtime_mapping_cleanup.py` (new)

35 tests covering:
1. scope_mismatch status valid for all child rows
2. scope_mismatch count in authority_summary
3. C.02 category has scope_mismatch child
4. C.02 mapping notes exist for mismatch/scope_mismatch rows
5. epc_contract field not backend_authoritative
6. C.03.01 is scope_mismatch with explanatory note
7. C.03.02 is mismatch or scope_mismatch (same app field)
8. C.16.01/02/03 are scope_mismatch with explanatory notes
9. No runtime/model changes ( invariants)
10. scope_mismatch rows have required metadata
11. Template badge CSS + authority strip + legend entries
12. All Phase 21B classifications preserved
13. main_web imports

---

## Key Conclusions

### EPC Contract (C.02) — `scope_mismatch`

**Finding:** `epc_contract.amount_keur = 52,800` kEUR in the TUHO app. This is a **4-semester aggregate** EPC contract value, not directly comparable to the Excel reference of **13,560 kEUR** (which represents the per-batch or one-shot reference amount from the Excel CapEx sheet).

**Source:** In `project_factories.py` (make_tuho_project), the comment reads: `# 35 MW × 1,000 EUR/kW × 1.5 (markup)`. TUHO uses a 6-month construction model; the Excel shows an 18-month spread. The 52,800 figure reflects the total contract value over all construction semesters.

**Conclusion:** `scope_mismatch` (NOT `backend_authoritative`). This field drives the capex total through `_capex_y1_total()` and `capex_items`, but its scope is a multi-semester aggregate while Excel is per-period. No runtime parity possible without reconciling the construction period model.

**Mapping note format:** `"App 52,800.00 vs Excel 13,560.00 kEUR — scopes differ: app is 4-semester total EPC contract value, Excel is one-shot reference; diff 39,240.00 kEUR (289.2%)"`

---

### Grid Connection (C.03) — `scope_mismatch` (C.03.01), `mismatch` (C.03.02)

**Finding:** `grid_connection.amount_keur = 6,200` kEUR in the app. Excel C.03.01 (Grid Connection Agreement) = **30 kEUR** — this is just the Grid Purchase Agreement (GPA) fee, not the full interconnection cost. The full interconnection (EPC sub-item C.02.04) is 10,800 kEUR in Excel, and both C.02.04 and C.03.01 map to the same `grid_connection` field in the app (value 6,200).

**Conclusion:** `scope_mismatch` for C.03.01 — app's 6,200 represents a complete interconnection scope (or selective subset thereof), while Excel's 30 is just the GPA fee. Not directly comparable; diff = 6,170 kEUR.

**Mapping note format:** `"App 6,200.00 vs Excel 30.00 kEUR — scopes differ: app is 4-semester total EPC contract value, Excel is one-shot reference; diff 6,170.00 kEUR (20566.7%)"` — note: this note applies to C.03.01 specifically.

---

### Project Rights (C.16) — `scope_mismatch` (all sub-rows)

**Finding:** App's `project_rights.amount_keur = 0` for TUHO. Excel C.16 totals **14,739 kEUR** (Akuo Development 2,739 + Dev costs 2,000 + Project Purchase Cost 10,000). No app field stores the 14,739 kEUR project rights value in TUHO.

**Note:** Oborovo's factory DOES have `project_rights = 3,024.5 kEUR` (from `project_factories.py`), but TUHO's factory sets it to 0. The TUHO Excel has 14,739 kEUR for project rights; the app (TUHO template) has 0.

**Conclusion:** `scope_mismatch` for C.16.01/02/03 — the app has no value for these rows while Excel shows material costs. This is a field-not-found scope difference, not just a value difference.

**Mapping note format:** `"App 0.00 vs Excel 2,739.00 kEUR — scopes differ: no app field for Akuo development services, Excel is one-shot reference; diff 2,739.00 kEUR (inf%)"`

---

## Authority Counts (TUHO, Phase 21C)

| Status | Count | Notes |
|---|---|---|
| `backend_authoritative` | 8 | C.17.01/02/03, C.18.01/02/03, C.17.04/05 |
| `app_mapped` | 1 | C.13 Contingencies |
| `excel_reference_only` | 8 | C.01.01, C.04.01/02, C.05.01–04, C.11.04 |
| `missing_runtime_source` | 0 | — |
| **`scope_mismatch`** | **5** | C.03.01, C.16.01, C.16.02, C.16.03, +C.02 cross-signal |
| `mismatch` | 21 | EPC sub-items, C.03.02, grid, insurances, land, DD, CM, audit, C.12, C.15 |
| `deferred` | 0 | — |
| `not_applicable` | 35 | Zero rows in both |
| **Total child rows** | **73** | |

---

## No Runtime/Model Changes

No changes to any runtime modules:
- `domain/capex/capex_breakdown.py` — untouched
- `domain/capex/capex_schedule.py` — untouched
- `domain/construction/engine.py` — untouched
- `domain/construction/runtime_adapter.py` — untouched
- `domain/shl/canonical_wiring.py` — untouched
- `domain/shl/runtime_adapter.py` — untouched
- `domain/returns/sponsor_cashflows.py` — untouched

CAPEX totals in display are unchanged. `_build_capex_detail_items()` is a pure read-only audit function.

---

## Recommended Next Phase

### Phase 21D — CAPEX Input Wiring + Line Editing
1. **Resolve C.02 EPC scope** — either document the 4-semester vs per-batch differently or wire a per-batch input
2. **Wire C.16 Project Rights** — 14,739 kEUR is material and currently unmapped in TUHO; connect to `project_rights` (Oborovo has this field, TUHO doesn't)
3. **Grid Connection C.03 reconciliation** — clarify whether app's 6,200 should equal C.02.04 + C.03.01 or if they're intentionally separate
4. **Add line editing** — enable user editing of `app_mapped` rows via CAPEX grid
5. **Payment schedule bridge** — link 18-month Excel schedule to app construction profile

---

## Files Changed

| File | Change |
|---|---|
| `app/ui/project_context.py` | `_scope_desc()`, `scope_mismatch` in `_classify_authority()`, `_child_row()` comment, authority_summary tracking |
| `app/templates/partials/sheet_capex_detail.html` | `badge-auth-scope-mismatch` badge + CSS, authority strip card, legend entry |
| `tests/test_phase21b_capex_runtime_mapping_authority.py` | Add `scope_mismatch` to `VALID_STATUSES` |
| `tests/test_phase21c_capex_runtime_mapping_cleanup.py` | New — 35 tests |
| `docs/phase21c_capex_runtime_mapping_cleanup.md` | This document |
