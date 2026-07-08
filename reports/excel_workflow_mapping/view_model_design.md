# View Model Design — PR A (revised)

Source: `reports/excel_workflow_mapping/implementation_plan.md` + actual ProjectContext field inspection.

---

## Files Created / Updated

| File | Purpose |
|------|---------|
| `app/ui/capex_view_model.py` | CAPEX dataclasses + `build_capex_view_model()` + command types |
| `app/ui/opex_view_model.py` | OPEX dataclasses + `build_opex_view_model()` + `compute_year_values()` + command types |
| `tests/test_capex_view_model.py` | 68 tests — structure, row identity, flags, editability, totals, commands |
| `tests/test_opex_view_model.py` | 89 tests — formula, structure, row identity, flags, display years, totals, KPIs, editability, commands |

---

## Data Sources

Both view models build from `ProjectContext` without engine changes:

| View model | Source field | Builder |
|-----------|-------------|---------|
| `CapexViewModel` | `project_ctx.capex_detail_items` | `build_capex_view_model(ctx, is_user_project)` |
| `OpexViewModel` | `project_ctx.opex_detail_items` | `build_opex_view_model(ctx, is_user_project, display_years)` |

`is_user_project` is a parameter — not on `ProjectContext` (set per-session in `project_review.py`).

---

## CAPEX Data Model

```
CapexLineVM
  row_id              ← Deterministic: "{project_code}:{parent_code}:{code}"
  code, parent_code, name
  source              ← from child["source_type"]: "excel_reference" | "app_input" | …
  unit                ← always "kEUR"
  notes               ← from child["comments"] or child["mapping_note"]
  display_order       ← 1-based index within parent group
  validation_status   ← "ok" | "unmapped" | "partial" | "mismatch" | "backend_calculated" | "unknown"
  amount_keur         ← editable for user projects on non-derived lines
  per_mw              ← derived: amount_keur / capacity_mw (never submitted)
  is_group            ← always False (group headers are not CapexLineVM)
  is_editable         ← True iff is_user_project AND NOT is_derived
  is_read_only        ← True iff is_derived OR NOT is_user_project
  is_derived          ← True for C.13, C.17, C.18 lines
  is_contingency      ← True for C.13 sub-lines
  is_financing        ← True for C.17 sub-lines
  is_reserve          ← True for C.18 sub-lines
  is_readonly_financing  ← True for C.17 or C.18 sub-lines (alias)
  is_custom           ← False for all template lines (future: user-added)
  is_active           ← True for all template lines (future: deactivation)

CapexGroupVM
  code, name
  lines: tuple[CapexLineVM]
  subtotal_keur       ← sum of active line amounts
  subtotal_per_mw     ← subtotal_keur / capacity_mw
  is_readonly         ← True for C.17, C.18
  is_contingency      ← True for C.13
  is_financing        ← True for C.17
  is_reserve          ← True for C.18

CapexViewModel
  project_name, capacity_mw
  groups: tuple[CapexGroupVM]     ← C.01–C.18 in Excel order
  hard_capex_keur                 ← groups C.01–C.16
  hard_capex_per_mw
  financing_keur                  ← C.17 subtotal
  reserve_keur                    ← C.18 subtotal
  total_capex_keur                ← hard + financing + reserve
  total_per_mw
  editable_total_keur             ← sum of active lines where is_editable=True
  derived_total_keur              ← sum of active lines where is_derived=True
  is_user_project
```

---

## OPEX Data Model

```
OpexLineVM
  row_id              ← Deterministic: "{project_code}:{parent_code}:{code}"
  code, parent_code, name
  source              ← from child["source"]: "factory" | …
  unit                ← always "kEUR"
  notes               ← from child["notes"]
  display_order       ← 1-based index within parent group
  validation_status   ← "ok" (OPEX source is factory-generated)
  y1_keur             ← editable for non-contingency lines in user projects
  inflation_pct       ← display column; line-level (falls back to group default)
  wht_flag            ← bool; display only (wth_rate > 0)
  is_group            ← always False
  is_editable         ← True iff is_user_project AND NOT is_contingency
  is_read_only        ← True iff is_derived OR NOT is_user_project
  is_derived          ← True for B.13 lines
  is_contingency      ← True for B.13 sub-lines
  is_fixed            ← True (v1 default; future: read from line metadata)
  is_variable         ← False (v1 default)
  is_custom           ← False (future)
  is_active           ← True (future)
  year_values: tuple  ← index 0 = Y1, …, index display_years-1 = YN

OpexGroupVM
  code, name, inflation_pct
  is_contingency, contingency_pct
  lines: tuple[OpexLineVM]
  subtotal_per_year: tuple    ← sum of active non-contingency line year_values

OpexViewModel
  project_name, capacity_mw
  p50_annual_mwh              ← operating_hours_p50 × capacity_mw
  groups: tuple[OpexGroupVM]  ← B.01–B.13
  contingency_rate
  total_excl_contingency      ← per year
  contingency_by_year         ← total_excl × contingency_rate/100 per year
  total_incl_contingency      ← total_excl + contingency_by_year per year
  y1_total_opex               ← total_incl[0]
  final_year_total_opex       ← total_incl[-1]
  display_years               ← 1–30 (default 30)
  opex_per_mw_y1              ← y1_total / capacity_mw, or None if capacity=0
  opex_per_mwh_y1             ← y1_total × 1000 / p50_annual_mwh, or None if p50=0
  is_user_project
```

---

## Row Identity

`row_id` format: `"{project_code}:{parent_code}:{line_code}"`

Example: `"tuho:C.01:C.01.01"`, `"tuho:B.06:B.06.01"`

Properties:
- Deterministic — same result on repeated builder calls
- Unique within a project (codes are unique within capex_detail_items / opex_detail_items)
- Distinct across projects (project_code prefix)
- Safe for HTML `id` attributes

---

## Year Value Strategy

**Primary:** use `yearly_values` from `opex_detail_items` child dicts (pre-computed, length = `horizon_years`). Handles step schedules and conditional activation correctly.

**Fallback:** `compute_year_values(y1_keur, inflation_pct, n_years)`:
```
Yn = Y1 × (1 + inflation_pct/100)^(n-1)
```

**Out of scope v1:** custom step schedule editing (future extension point).

---

## Contingency Treatment

**CAPEX (C.13):**
- `amount_keur` on C.13 children is already the computed contingency amount (rate × sum C.01–C.12).
- View model marks these lines `is_contingency=True`, `is_derived=True`, `is_read_only=True`.
- C.13 subtotal is included in `hard_capex_keur` and `derived_total_keur`.

**OPEX (B.13):**
- B.13 group `subtotal_per_year` = 0 (contingency not summed from sub-line year_values).
- `contingency_by_year[yr] = total_excl[yr] × contingency_rate / 100`
- `total_incl[yr] = total_excl[yr] + contingency_by_year[yr]`
- Three separate tuples expose the full arithmetic — no hidden multiplier.

---

## KPI Denominator Contract

| KPI | Denominator | Missing → |
|-----|------------|-----------|
| `opex_per_mw_y1` | `capacity_mw` | `None` (not `0.0`) |
| `opex_per_mwh_y1` | `p50_annual_mwh` | `None` (not `0.0`) |

Templates must guard: `{% if vm.opex_per_mw_y1 is not none %}`.

---

## Mutation Contract

### CAPEX
```python
AddCapexLineCommand(project_code, parent_group_code, name, amount_keur, notes)
UpdateCapexLineCommand(project_code, line_code, new_amount_keur, notes)
DeactivateCapexLineCommand(project_code, line_code)  # only is_custom=True lines
```

### OPEX
```python
AddOpexLineCommand(project_code, parent_group_code, name, y1_keur, inflation_pct, wht_flag, notes)
UpdateOpexLineCommand(project_code, line_code, new_y1_keur, notes)
DeactivateOpexLineCommand(project_code, line_code)   # only is_custom=True lines
```

All commands are frozen dataclasses. Persistence is out of scope for this module.

---

## Future Extension Points

| Feature | Field to set | Implementation |
|---------|-------------|----------------|
| User-added custom lines | `is_custom = True` | Merge from user storage before totals |
| Line deactivation | `is_active = False` | Exclude from subtotal sum |
| Per-scenario CAPEX/OPEX overrides | Override dict parameter | Override `amount_keur`/`y1_keur` before summing |
| OPEX step schedule editing | `schedule_overrides` on line | Override `year_values` from user-stored breakpoints |
| Variable cost classification | `is_variable = True` | Read from line metadata |

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
