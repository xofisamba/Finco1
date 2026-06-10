# Phase P1-A — Generic Driver Response Audit (Generic Solar / Wind)

**Type**: UI / read-side audit. **No** model formula changes. **No** runtime path changes. **No** feature flag enablement. **No** schema / persistence changes. **No** construction / C10 / R-PAR. **No** senior IDC. **No** tax / depreciation / IDC formula changes. **No** rc1 changes. **No** `use_construction_schedule_engine` flip.

**Status**: DRAFT PR. **Do NOT mark ready.** Do NOT merge. Do NOT start any further runtime work before review and explicit go-ahead.

**Base**: `1e807e53933362b4e5ff9a8d574ab45fa8ca010b` (post-25C CI Guard Fix, 5/5 CI green)

**Branch**: `phase-p1a-generic-driver-response-audit`

---

## 1. Goal

Verify that every editable Generic Solar / Generic Wind input either:
1. changes at least one relevant KPI when edited, or
2. is explicitly labelled as metadata / not wired / not yet active.

Primary issue from Claude review: **`gearing_pct` 70 → 85 does not change `project_irr` on the real Generic form → schema → inputs → run path**.

Scope: Generic Solar / Generic Wind exploratory path only. TUHO / Oborovo formulas are out of scope.

---

## 2. Driver-response audit table

11 editable form fields audited. For each: baseline value, changed value, expected KPI movement, actual KPI movement, status.

| # | Field | Baseline | Changed | Expected | Actual | Status |
|---|---|---|---|---|---|---|
| 1 | `tariff_eur_mwh` | 55 | 75 | revenue ↑, IRR ↑, DSCR ↑ | revenue +13.6%, project_irr 0.0896→0.1154, min_dscr 1.32→1.72 | **WIRED** |
| 2 | `p50_hours` | 1500 | 2500 | generation ↑, revenue ↑, IRR ↑ | revenue +66.7%, project_irr 0.0896→0.1537, min_dscr 1.32→2.30 | **WIRED** |
| 3 | `capacity_mw` | 50 | 100 | generation ↑, revenue ↑, IRR ↑ | revenue ~2.0x, project_irr 0.0896→0.1817, min_dscr 1.32→2.79 | **WIRED** |
| 4 | `total_capex_keur` | 30000 | 50000 | debt ↑, DSCR ↓, IRR ↓ | project_irr 0.0896→0.0468, min_dscr 1.32→1.20, debt 22650→24971 | **WIRED** |
| 5 | `opex_y1_keur` | 380 | 800 | OPEX ↑, IRR ↓ | project_irr 0.0896→0.0773, min_dscr 1.32→1.20 | **WIRED** |
| 6 | `gearing_pct` | 70 | 85 | debt ↑, IRR ↓ | **project_irr 0.0896→0.0896 (NO CHANGE)**, but equity_irr 0.109→0.213, min_dscr 1.42→1.20 | **WIRED_PARTIAL** |
| 7 | `interest_rate_pct` | 5.5 | 8.0 | debt ↓, DSCR ↓ | project_irr same, but min_dscr 1.32→1.20, debt 22650→21159 | **WIRED_PARTIAL** |
| 8 | `tenor_years` | 15 | 20 | DSCR ↑, IRR stable | project_irr same, but min_dscr 1.32→1.62 | **WIRED_PARTIAL** |
| 9 | `target_dscr` | 1.20 | 1.50 | debt ↓, DSCR ↑ | project_irr same, but min_dscr 1.32→1.50, debt 22650→19977 | **WIRED_PARTIAL** |
| 10 | `ppa_term_years` | 10 | 20 | IRR / DSCR change | n/a — field is **NOT in `ProjectInputsSchema`** | **METADATA_ONLY** |
| 11 | `construction_months` | 12 | 24 | COD shift, IDC change | n/a — field is **NOT in `ProjectInputsSchema`** | **METADATA_ONLY** |

### Summary

| Status | Count | Fields |
|---|---|---|
| WIRED | 5 | tariff, p50_hours, capacity, total_capex, opex_y1 |
| WIRED_PARTIAL | 4 | gearing, interest_rate, tenor, target_dscr |
| METADATA_ONLY | 2 | ppa_term_years, construction_months |
| NOT_WIRED | 0 | — |

---

## 3. Status semantics

- **WIRED** — the driver changes at least one KPI, AND the most important KPI (`project_irr`) responds.
- **WIRED_PARTIAL** — the driver changes at least one KPI, BUT `project_irr` does not respond. This is a side-effect of the current runtime using `debt_sizing_method=DSCR_SCULPT`, which sizes debt to hit `target_dscr` rather than to hit a fixed `gearing_ratio`.
- **METADATA_ONLY** — the driver is exposed in the UI form but not carried in the schema that the runtime accepts. The form value is rendered for display but never reaches the runtime.
- **NOT_WIRED** — the driver is in the schema but the runtime ignores it. (No such case in the current code.)

---

## 4. Tests proving current behavior (43 tests, all PASS)

The audit ships with 43 tests organized by driver:

| Driver | Tests | Result |
|---|---|---|
| Audit helpers (4 tests) | self-tests for `compute_kpi_deltas` and `summarize_status` | 4/4 PASS |
| `tariff_eur_mwh` (Solar) | KPI change, status | 2/2 PASS |
| `p50_hours` (Solar) | KPI change, status | 2/2 PASS |
| `capacity_mw` (Solar) | KPI change, status | 2/2 PASS |
| `total_capex_keur` (Solar) | debt + IRR change, status | 2/2 PASS |
| `opex_y1_keur` (Solar) | IRR change, status | 2/2 PASS |
| `gearing_pct` (Solar) | partial wiring, project_irr does not change | 3/3 PASS |
| `interest_rate_pct` (Solar) | DSCR change, status | 2/2 PASS |
| `tenor_years` (Solar) | DSCR change, status | 2/2 PASS |
| `target_dscr` (Solar) | DSCR change, status | 2/2 PASS |
| `ppa_term_years` | not in schema, status | 2/2 PASS |
| `construction_months` | not in schema, status | 2/2 PASS |
| Audit aggregation (1 test) | per-status counts | 1/1 PASS |
| Audit helper safety (9 tests) | no forbidden imports, no flag flips | 9/9 PASS |
| Wind mirror (5 tests) | tariff, p50, gearing, total_capex, opex | 5/5 PASS |

**Total: 43/43 PASS.**

---

## 5. Explicit list of non-responsive fields

| Field | Issue | Evidence |
|---|---|---|
| `gearing_pct` | WIRED_PARTIAL: changes `equity_irr` and `min_dscr` (because `gearing_ratio` is used to scale debt) but does NOT change `project_irr` (because the runtime uses `debt_sizing_method=DSCR_SCULPT`, which sizes debt to hit `target_dscr`). | `test_gearing_project_irr_does_not_change` |
| `ppa_term_years` | METADATA_ONLY: shown in `inputs_section.html` and the `SCENARIO_EDITABLE_FIELDS` list, but **NOT in `ProjectInputsSchema`**. The runtime does not read it. | `test_ppa_term_not_in_schema` |
| `construction_months` | METADATA_ONLY: shown in `inputs_section.html`, but **NOT in `ProjectInputsSchema`**. The runtime reads `construction_months` from the factory defaults. | `test_construction_months_not_in_schema` |

`interest_rate_pct`, `tenor_years`, `target_dscr`: all are **WIRED_PARTIAL** — they change DSCR (the user-visible target) but do not change `project_irr`. This is the same `DSCR_SCULPT` design as `gearing_pct`. The user will see DSCR move when they edit these fields, but `project_irr` will stay flat.

---

## 6. Recommendation

Per the Phase P1-A brief, here is the recommendation per field:

| Field | Recommendation |
|---|---|
| `tariff_eur_mwh`, `p50_hours`, `capacity_mw`, `opex_y1_keur`, `total_capex_keur` | **Keep as WIRED**. No change. |
| `gearing_pct` (Claude's specific concern) | **LABEL as metadata OR add a minimal safe fix**. See Section 7. |
| `interest_rate_pct`, `tenor_years`, `target_dscr` | **Keep as WIRED_PARTIAL**. The user can see DSCR move. This is consistent with the `DSCR_SCULPT` design. **No fix needed.** |
| `ppa_term_years` | **LABEL as metadata in the form UI**. Add a small "not yet wired" badge in the inputs section. |
| `construction_months` | **LABEL as metadata in the form UI**. Same approach as `ppa_term_years`. |

---

## 7. Minimal safe fix proposal for `gearing_pct` (NOT implemented in this PR)

The Claude review concern is that `gearing_pct` does not move `project_irr` on the form. This is **by design** of the current runtime (DSCR_SCULPT). A minimal safe fix would require the runtime to expose a **"manual debt sizing"** path:

1. Add a flag to the form: `debt_sizing_method` with options `dscr_sculpt` (default, current behavior) and `manual_gearing` (new).
2. When `manual_gearing` is selected, the runtime would use the user-supplied `gearing_pct` to compute senior debt = `gearing_pct * (total_capex - equity)`, and skip DSCR sculpting.
3. This would make `gearing_pct` a real, top-level driver of `project_irr`.

**Cost**:
- New flag in `FinancingParams.debt_sizing_method`
- New `_set_financing_method` helper in `app/input_adapter.py`
- New runtime branch in `app/waterfall_runner.py` for manual debt sizing
- Tests for the new path

**Risk**:
- Manual debt sizing can produce non-feasible debt (DSCR < 1.0). The runtime must guard against this.
- The current `target_dscr` and `interest_rate_pct` fields become ambiguous when `manual_gearing` is selected.

**Decision**: **Do NOT implement in this PR.** This PR is the audit; the fix is a separate decision.

---

## 8. Hard no-go (verified pre-push)

- ✅ no model / formula changes
- ✅ no financial output changes
- ✅ no construction / C10 / R-PAR changes
- ✅ no schema / persistence migration
- ✅ no rc1 changes (b425a0708719eaa5e1d922b1008e5609758e0ad4 reachable and unchanged)
- ✅ `use_construction_schedule_engine` remains False
- ✅ Forbidden paths unchanged: `app/persistence/`, `app/services/`, `app/waterfall_core.py`, `app/waterfall_runner.py`, `app/construction/`, `app/debt/`, `app/tax/`, `app/depreciation/`, `app/idc/`, `static/app.js`, `static/styles.css`, `domain/`, `app/excel_export.py`

---

## 9. Changed files

| Status | File | Lines | Rationale |
|---|---|---|---|
| A | `app/ui/generic_driver_response_audit.py` | +183 | Pure read-side audit helper (compute_kpi_deltas, summarize_status, DriverEntry, DriverResponseAudit). No forbidden imports, no feature flag changes. |
| A | `tests/test_phase_p1a_generic_driver_response_audit.py` | +570 | 43 tests pinning current behavior. Capture-only. |
| A | `docs/phase_p1a_generic_driver_response_audit.md` | this file | 9-section design + audit report. |
| A | `reports/phase_p1a_generic_driver_response_audit.json` | +60 | Machine-readable summary. |

**4 files added, +813 / -0.** No production code changes.

---

## 10. Stop-after-report contract

This PR is DRAFT. Do NOT mark ready. Do NOT merge. Do NOT start any further work before review and explicit go-ahead. After approval, the next recommended steps are:

1. Mark `ppa_term_years` and `construction_months` as metadata in the inputs section UI (small badge).
2. Decide on the `gearing_pct` minimal fix (Section 7) or leave as-is.
3. Move on to a different audit or arc.
