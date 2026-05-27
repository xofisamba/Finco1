# Phase 20I — CAPEX Detail Grid Foundation

**Branch:** `phase20i-capex-detail-grid-foundation`
**Base SHA:** `b654113e03c706255b2c63b500ee36c552013f69` (Phase 20H HEAD)
**Head SHA:** `<head>` (work in progress)

## Goal

Build the first major "Excel workbook grid" UI using the Phase 20H `fc-*` design system — a structured CAPEX detail grid that replaces the summary-only CAPEX panel with a hierarchical, workbook-style line-item surface.

---

## What was built

### 1. CAPEX Detail Grid (`app/templates/partials/sheet_capex.html`)

**Before:** 51-line summary table (epc_contract, IDC, bank_fees, total)
**After:** 200+ line workbook grid with:

- **Sticky header row** (`fc-grid-header`)
- **Sticky first column** (`fc-grid-col-label`) — line item names stay fixed
- **Section bands** (`fc-section-band`) — Construction, Development, Construction Mgmt, Civil & Land, Insurances & Risk, Financing Costs
- **`fc-input-native`** — native `<input type="number">` inside cells (read-only for baselines, editable for `is_user_project`)
- **`fc-total-row`** subtotals per section
- **`fc-grand-total`** row for hard CAPEX + grand total
- **`fc-subtotal-row`** per section
- **Delta warning** — if grid total differs from `project_ctx.total_capex_keur`, shows warning (backend authoritative)
- **Readonly notice** for factory templates with "Duplicate / Save As" guidance
- **Dirty indicator** placeholder (`inp-dirty-indicator`)

**Hierarchy:**
```
Construction          [section band]
  EPC Contract         [item]  [code]  [amount input]
  Production Units     [item]  [code]  [amount input]
  EPC Other            [item]  [code]  [amount input]
Construction Subtotal [subtotal]
Development          [section band]
  ...
Hard CAPEX Total      [total]
Financing Costs       [section band]
  IDC                  [readonly]
  Bank Fees            [readonly]
  ...                  [readonly]
Financing Costs Total [subtotal]
Total CAPEX           [grand total]
```

### 2. `ProjectContext.capex_items` field

**File:** `app/ui/project_context.py`

- Added `capex_items: tuple[dict[str, Any], ...] = field(default_factory=lambda: ())`
- Added `_build_capex_items(capex)` helper — builds serializable list from `CapexStructure._CAPEX_ITEM_FIELDS` + financing/legal fields (idc, bank_fees, etc.)
- `capex_items` is passed to all `ProjectContext` instances

Each `capex_items` dict:
```python
{
    "code": "epc_contract",    # field name key
    "name": "EPC Contract",    # CapexItem.name
    "amount_keur": 52800.0,  # CapexItem.amount_keur
    "y0_share": 0.4,          # CapexItem.y0_share
}
```

### 3. Individual CAPEX fields in `_collect_form_snapshot`

**File:** `main_web.py`

Added 18 new form fields to enable fine-grained CAPEX editing:
`capex_epc_contract_keur`, `capex_production_units_keur`, `capex_epc_other_keur`, `capex_grid_connection_keur`, `capex_ops_prep_keur`, `capex_insurances_keur`, `capex_lease_tax_keur`, `capex_construction_mgmt_a_keur`, `capex_commissioning_keur`, `capex_audit_legal_keur`, `capex_construction_mgmt_b_keur`, `capex_contingencies_keur`, `capex_taxes_keur`, `capex_project_acquisition_keur`, `capex_project_rights_keur`, `capex_idc_keur`, `capex_bank_fees_keur`, `capex_commitment_fees_keur`, `capex_other_financial_keur`, `capex_vat_costs_keur`, `capex_reserve_accounts_keur`

### 4. CSS Extensions (`static/styles.css`)

Added Phase 20I CSS block (~148 lines):
- `.fc-section-band__label` — section band label styling
- `.fc-cell--code` — narrow monospace column for code
- `.fc-cell--amount` — right-aligned numeric cell
- `.fc-th--code`, `.fc-th--amount` — header column widths
- `.fc-subtotal-row` — subtotal row tint
- `.fc-total-cell`, `.fc-total-value` — total cell properties
- `.fc-hard-capex-total` — hard CAPEX total row (subtle accent tint)
- `.fc-grand-total` — grand total row (stronger accent tint, bold)
- `.fc-grand-total__label`, `.fc-grand-total__value` — label/value variants
- `.fc-delta-row`, `.fc-delta-label`, `.fc-delta-warning` — delta warning row
- `.fc-input-native` — native `input[type=number]` inside `.fc-cell`
- `.fc-capex-grid-wrapper` — grid wrapper variant
- `.inp-dirty-indicator` — dirty state indicator

---

## Changed files

| File | Change |
|------|--------|
| `app/ui/project_context.py` | Add `capex_items` field, `_build_capex_items()` helper, add `field` import, add defaults to `ProjectContext` fields |
| `main_web.py` | Add 18 individual capex fields to `_collect_form_snapshot()` |
| `app/templates/partials/sheet_capex.html` | Complete redesign: 51→200+ lines |
| `static/styles.css` | +148 lines Phase 20I CSS extensions |
| `tests/test_phase20i_capex_grid.py` | New test file (10 tests) |

---

## What was NOT changed

- No formula changes
- No IDC timing logic changes
- No debt draw logic changes
- No construction schedule engine changes
- No workbook calculation changes
- No JS financial calculations
- Backend remains source of truth
- Save does not auto-run; Run does not auto-save

---

## Persistence / Schema

- `ProjectContext.capex_items` is a **computed view** from existing `CapexStructure` data — no new schema
- Editing works through existing `_collect_form_snapshot` → `save_workspace_draft_endpoint` flow
- Named form fields (`capex_<code>_keur`) flow into workspace draft state
- TUHO/Oborovo baselines remain read-only (`is_user_project=False`)

---

## Known Limitations

1. **Delta warning shown but not actionable**: The delta between grid sum and `total_capex_keur` is displayed (backend authoritative), but the backend reconciliation is not wired yet — planned for a later phase
2. **No per-line scenario compare**: Phase 20I does not implement per-line scenario comparison for CAPEX — future phase
3. **`is_user_project=False` editing**: Factory template editing requires "Duplicate / Save As" flow; the edit inputs are disabled but present

---

## Visual Description

```
┌──────────────────────────────────┬──────────┬────────────┐
│ Line Item                  [sticky│  Code    │ Amount kEUR│
├──────────────────────────────────┼──────────┼────────────┤
│ Construction                 [BAND]        │            │
│  EPC Contract                    │ epc_... │  52,800   │
│  Production Units                │ prod_...│  [input]   │
│  EPC Other                       │ epc_oth.│     2,100  │
│ Construction Subtotal           │          │  54,900   │
├──────────────────────────────────┼──────────┼────────────┤
│ Development                  [BAND]        │            │
│  Project Acquisition            │ proj_a...│  [input]   │
│  ...                                      │            │
│ Hard CAPEX Total                       │  70,692   │
├──────────────────────────────────┼──────────┼────────────┤
│ Financing Costs                [BAND]        │            │
│  IDC                            │ idc      │  1,519.56 │
│  Bank Fees                      │ bank_fee.│    782.61 │
│  ...                                      │            │
│ Total CAPEX                         │  72,994   │
└──────────────────────────────────┴──────────┴────────────┘
```

---

## Recommended Next Phase

**Phase 20J — OPEX Detail Grid Foundation**

Apply same pattern as Phase 20I for OPEX:
- `fc-grid` workbook surface for OPEX line items
- `fc-cell-input` for editable Y1 amounts and inflation rates
- `fc-total-row` for group subtotals and grand total OPEX
- `fc-badge--runtime` for read-only computed values
- Persist via existing `opex_y1_keur` form field (already in `_collect_form_snapshot`)

---

## Tests

| Suite | Result |
|-------|--------|
| `test_phase20i_capex_grid.py` | 10 passed |
| `test_phase20h_design_system_rendering.py` | 23 passed, 1 skipped |
| `main_web.py` compile | OK |
| **Total** | **33 passed, 1 skipped** |
