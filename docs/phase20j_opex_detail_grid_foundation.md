# Phase 20J — OPEX Detail Grid Foundation

**Branch:** `phase20j-opex-detail-grid-foundation`
**Base SHA:** `73dd983e52ff96fdb4e99afac5f38ed1a63e9a23` (Phase 20I merge)
**Head SHA:** `<head>` (work in progress)

## Goal

Build the OPEX counterpart to the Phase 20I CAPEX Detail Grid — a structured, workbook-style OPEX line-item surface using the Phase 20H `fc-*` design system, matching the CAPEX grid UX.

---

## What was built

### 1. OPEX Detail Grid (`app/templates/partials/sheet_opex.html`)

**Before:** 110-line simple table with one editable `opex_y1_keur` input
**After:** 500+ line workbook grid with:

- **Sticky header row** (`fc-grid-header`)
- **Sticky first column** (`fc-grid-col-label`) — line item names stay fixed
- **Section bands** (`fc-section-band`): Operations & Maintenance, Insurance, Land & Lease, Grid & Balancing, Administration, Environmental & Social, Contingency
- **`fc-input-native`** — native `<input type="number">` inside cells (read-only for baselines, editable for `is_user_project`)
- **Subtotal rows** per section + **`fc-grand-total`** row for Total OPEX Y1
- **`fc-cell--num`** — center-aligned numeric columns (Start Year, End Year)
- **`fc-cell--notes`** — italic muted notes column
- **Delta warning row** — if grid sum ≠ `opex_y1_total_keur`, shows warning (backend authoritative)
- **Readonly notice** for factory templates with "Duplicate / Save As" guidance

### 2. `ProjectContext.opex_items` — Extended Structure

**File:** `app/ui/project_context.py`

Enhanced `_build_opex_items()` to include full per-item metadata:

```python
{
    "code": "technical_management",     # slugified key for form naming
    "name": "Technical Management",
    "y1_keur": 279.99,
    "inflation_pct": 0.02,
    "group": "Operations & Maintenance",  # inferred from name patterns
    "unit": "kEUR",
    "fixed_variable": "Fixed",
    "recurring_oneoff": "Recurring",
    "escalation_pct": 2.0,              # from annual_inflation × 100
    "start_year": 1,
    "end_year": 30,                     # from project horizon_years
    "notes": "",
}
```

Added helpers:
- `_slugify_code(name)` — creates URL-safe code from item name
- `_infer_opex_group(name)` — maps item names to OPEX groups (best-effort)

### 3. Individual OPEX Fields in `_collect_form_snapshot`

**File:** `main_web.py`

Added 12 new form fields to enable fine-grained OPEX editing:
`opex_technical_management_y1_keur`, `opex_o_and_m_preventive_and_corrective_y1_keur`, `opex_maintain_site_y1_keur`, `opex_clean_material_y1_keur`, `opex_security_y1_keur`, `opex_insurance_y1_keur`, `opex_lease_and_property_tax_y1_keur`, `opex_power_expenses_y1_keur`, `opex_audit_and_accounting_and_legal_y1_keur`, `opex_bank_fees_opex_y1_keur`, `opex_environmental_and_social_management_y1_keur`, `opex_contingencies_y1_keur`

### 4. CSS Extensions (`static/styles.css`)

Added Phase 20J CSS block:
- `.fc-opex-grid-wrapper` — grid wrapper variant
- `.fc-cell--num` — center-aligned numeric cells (start/end year)
- `.fc-cell--notes` — italic muted notes column
- `.fc-subtotal-label` — subtotal label styling
- `.inp-readonly-notice--opex` — readonly notice override
- `.table-note` + `.table-note__text` — footer grid note
- `.delta-warning-icon` — delta warning icon

---

## Changed files

| File | Change |
|------|--------|
| `app/templates/partials/sheet_opex.html` | Complete redesign: 110 → 500+ lines |
| `app/ui/project_context.py` | Extended `opex_items` structure + `_slugify_code()` + `_infer_opex_group()` |
| `main_web.py` | +12 individual opex fields in `_collect_form_snapshot()` |
| `static/styles.css` | +83 lines Phase 20J CSS |
| `tests/test_phase20j_opex_grid.py` | New test file |
| `docs/phase20j_opex_detail_grid_foundation.md` | Phase doc |

---

## What was NOT changed

- No domain engine changes (opex_engine.py unchanged)
- No waterfall engine changes
- No construction/IDC/debt logic changes
- No Excel export/build logic changes
- No JS financial calculations
- Backend remains source of truth

---

## Known Limitations

1. **Delta warning shown but not actionable**: The delta between grid sum and `opex_y1_total_keur` is displayed (backend authoritative), but the backend reconciliation is not wired yet — planned for a later phase
2. **Group inference is name-based**: `_infer_opex_group()` maps names to groups heuristically; factory templates with non-standard naming may not group correctly
3. **No per-line scenario compare**: Phase 20J does not implement per-line scenario comparison for OPEX — future phase
4. **No escalation editing**: Escalation % is read-only in this phase (driven by `annual_inflation` from factory template)

---

## Visual Description

```
┌──────────────────────────────────┬──────────────┬──────────┬──────┬────────┬──────────┬───────┬───────┬───────┐
│ Line Item                   [sticky│  Code        │ Y1 kEUR  │ Unit │ F/V    │ Rec/Onef│ Esc % │ Start │ End   │
├──────────────────────────────────┼──────────────┼──────────┼──────┼────────┼──────────┼───────┼───────┼───────┤
│ Operations & Maintenance    [BAND]│              │          │      │        │          │       │       │       │
│  Technical Management              │ techn_...   │  279.99  │ kEUR │ Fixed  │ Recurring│   2%  │   1   │  30   │
│  O&M Preventive & Corrective      │ o_and_m_... │  426.60  │ kEUR │ Fixed  │ Recurring│   2%  │   1   │  30   │
│  Maintain Site                    │ maintain_...│   68.00  │ kEUR │ Fixed  │ Recurring│   2%  │   1   │  30   │
│  Clean Material                  │ clean_...   │    5.00  │ kEUR │ Fixed  │ Recurring│   2%  │   1   │  30   │
│  Security                        │ security    │   50.00  │ kEUR │ Fixed  │ Recurring│   2%  │   1   │  30   │
│ O&M Subtotal                    │              │  829.59  │      │        │          │       │       │       │
├──────────────────────────────────┼──────────────┼──────────┼──────┼────────┼──────────┼───────┼───────┼───────┤
│ Insurance                    [BAND]│              │          │      │        │          │       │       │       │
│  Insurance                         │ insurance   │  468.74  │ kEUR │ Fixed  │ Recurring│   2%  │   1   │  30   │
│ ...                                      │              │          │      │        │          │       │       │       │
│ Total OPEX (Y1)                         │              │ 1,997.01  │      │        │          │       │       │       │
└──────────────────────────────────┴──────────────┴──────────┴──────┴────────┴──────────┴───────┴───────┴───────┘
```

---

## Recommended Next Phase

**Phase 20K — Revenue Detail Grid Foundation**

Apply same pattern as Phase 20I/20J for Revenue:
- `fc-grid` workbook surface for revenue line items
- PPA tariff, p50 hours, degradation, availability
- `fc-cell-input` for editable values
- `fc-badge--runtime` for read-only computed values

---
