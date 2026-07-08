# View Model Design — PR A

Source: `reports/excel_workflow_mapping/implementation_plan.md` + actual ProjectContext field inspection.

---

## Files Created

| File | Purpose |
|------|---------|
| `app/ui/capex_view_model.py` | CAPEX dataclasses + `build_capex_view_model()` |
| `app/ui/opex_view_model.py` | OPEX dataclasses + `build_opex_view_model()` + `compute_year_values()` |
| `tests/test_capex_view_model.py` | 33 tests — structure, editability, derived totals |
| `tests/test_opex_view_model.py` | 52 tests — formula, structure, KPIs, editability, edge cases |

---

## Data Source

Both view models build from `ProjectContext` without engine changes:

| View model | Source field | Builder function |
|-----------|-------------|-----------------|
| `CapexViewModel` | `project_ctx.capex_detail_items` | `build_capex_view_model(ctx, is_user_project)` |
| `OpexViewModel` | `project_ctx.opex_detail_items` | `build_opex_view_model(ctx, is_user_project, display_years)` |

`is_user_project` is passed as a parameter — it is NOT on `ProjectContext` (it is set per-session in `project_review.py`).

---

## CAPEX Data Model

```
CapexLineVM
  code, parent_code, name
  amount_keur           ← editable input for user projects
  per_mw                ← derived: amount_keur / capacity_mw (never submitted)
  is_editable           ← True iff is_user_project AND NOT C.17/C.18 AND NOT backend_calculated
  is_group              ← always False (group header rows not represented as CapexLineVM)
  is_readonly_financing ← True for all lines under C.17 and C.18
  is_custom             ← False for all template lines (future: user-added lines)
  is_active             ← True for all template lines (future: deactivation)

CapexGroupVM
  code, name
  lines: tuple[CapexLineVM]
  subtotal_keur         ← sum of active line amounts
  subtotal_per_mw       ← subtotal_keur / capacity_mw
  is_readonly           ← True for C.17, C.18

CapexViewModel
  project_name, capacity_mw
  groups: tuple[CapexGroupVM]   ← C.01–C.18 in Excel order
  hard_capex_keur               ← sum of all groups except C.17, C.18
  hard_capex_per_mw
  financing_keur                ← C.17 subtotal
  reserve_keur                  ← C.18 subtotal
  total_capex_keur              ← hard + financing + reserve
  total_per_mw
  is_user_project
```

**Readonly groups:** `C.17` (Financing Costs) and `C.18` (Reserve Accounts) — both have `is_backend_calculated: True` in `capex_detail_items`. Their sub-line amounts flow from the engine, not from user input.

---

## OPEX Data Model

```
OpexLineVM
  code, parent_code, name
  y1_keur              ← editable for non-contingency lines in user projects
  inflation_pct        ← display column; group-level rate
  wht_flag             ← bool; display only (wth_rate > 0)
  is_editable          ← True iff is_user_project AND NOT is_contingency
  is_group             ← always False
  is_contingency       ← True for B.13 lines
  is_custom            ← False (future)
  is_active            ← True (future)
  year_values: tuple   ← index 0 = Y1, ..., index display_years-1 = YN

OpexGroupVM
  code, name, inflation_pct
  is_contingency, contingency_pct
  lines: tuple[OpexLineVM]
  subtotal_per_year: tuple   ← sum of active non-contingency line year_values per year

OpexViewModel
  project_name, capacity_mw
  p50_annual_mwh             ← operating_hours_p50 × capacity_mw
  groups: tuple[OpexGroupVM] ← B.01–B.13 in Excel order
  contingency_rate           ← from project_ctx.opex_contingency_pct
  total_excl_contingency     ← sum of non-contingency group subtotals per year
  total_incl_contingency     ← total_excl × (1 + contingency_rate/100) per year
  display_years              ← 1–30 (default 10)
  opex_per_mw_y1             ← total_incl[0] / capacity_mw
  opex_per_mwh_y1            ← total_incl[0] × 1000 / p50_annual_mwh
  is_user_project
```

---

## Year Value Strategy

**Primary:** use `yearly_values` from `opex_detail_items` child dicts (pre-computed, length = `horizon_years`). These correctly handle:
- Step schedules (e.g. TUHO B.02.1: Y1=385.6, Y3=465.6, Y6=588, Y11=628)
- Conditional activation (e.g. Oborovo B.08 Balancing: zero Y1–Y10)
- Any other template-defined overrides

**Fallback:** `compute_year_values(y1_keur, inflation_pct, n_years)` — simple escalation:
```
Yn = Y1 × (1 + inflation_pct/100)^(n-1)
```
Applied when `yearly_values` is absent or shorter than `display_years`.

**Out of scope for v1:** custom step schedule editing. Future requirement: allow user to set Y1, Y3, Y6, Y11 breakpoints for maintenance ramp lines.

---

## Contingency Treatment

**CAPEX (C.13):** The `amount_keur` on C.13 children is already the computed contingency amount (rate × sum C.01–C.12), populated by the existing `_build_capex_detail_items()` builder. The view model sums it as part of `hard_capex_keur`.

**OPEX (B.13):** The `subtotal_per_year` for B.13 is zero (contingency is not summed from B.13 sub-line year_values). Instead, the view model applies:
```
total_incl = total_excl × (1 + contingency_rate/100)
```
The B.13 `contingency_pct` from the source data and `opex_contingency_pct` on `ProjectContext` are both available. The view model uses `opex_contingency_pct` for the aggregated totals.

---

## Future Extension Points

| Feature | Field to set | Implementation |
|---------|-------------|----------------|
| User-added custom lines | `CapexLineVM.is_custom = True` | Add to group.lines from user storage |
| Line deactivation | `CapexLineVM.is_active = False` | Exclude from subtotal sum |
| Per-scenario overrides | Pass override dict to builder | Override `amount_keur` / `y1_keur` before summing |
| OPEX step schedule editing | New `OpexLineVM.schedule_overrides` | Override `year_values` from user-stored breakpoints |
| Inflation rate editing | `OpexGroupVM.inflation_pct` editable | Recompute `year_values` in builder |

---

## What PR A Does NOT Do

- No template changes
- No CSS changes
- No routes
- No `main_web.py` changes
- No `project_context.py` changes
- No engine changes
- No persistence changes
- No browser/UI claims
