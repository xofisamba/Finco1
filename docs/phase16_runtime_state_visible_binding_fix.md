# Phase 16 — Runtime State Visible Binding Fix

## Investigation Summary

### Truth Sources for Revenue Tab Values

| Value | Element | Source | Updated from Saved Scenario? | Runtime-bound? |
|-------|---------|--------|-------------------------------|----------------|
| `tariff_eur_mwh` (draft input) | Editable grid input | `form_data.tariff_eur_mwh` → hidden field → JS mirror | ✅ Yes (after save/load) | ✅ Yes |
| `ppa_term_years` (draft input) | Editable grid input | `form_data.ppa_term_years` → hidden field → JS mirror | ✅ Yes (after save/load) | ❌ Preview only |
| `p50_hours` (draft input) | Editable grid input | `form_data.p50_hours` → hidden field → JS mirror | ✅ Yes (after save/load) | ✅ Yes (runtime-bound via RevenueInput) |
| `project_ctx.ppa_tariff_eur_mwh` | Lower assumption card | Factory calibration (`pi.revenue.ppa_base_tariff`) | ❌ Never | N/A |
| `project_ctx.ppa_term_years` | Lower assumption card | Factory calibration | ❌ Never | N/A |
| `project_ctx.ppa_index_pct` | Lower assumption card | Factory calibration | ❌ Never | N/A |
| Total Revenue (KPI) | Runtime summary | Runtime model output | ✅ After run | ✅ Yes |

### Root Cause

The lower assumption cards in `sheet_revenue.html` rendered `project_ctx.ppa_tariff_eur_mwh`, `project_ctx.ppa_term_years`, etc. — always the **factory reference values** from project calibration. They were NEVER updated from the saved scenario snapshot.

After a user edits PPA Tariff to 100 and saves:
1. ✅ Draft input shows 100 (correct)
2. ✅ Hidden form field `#tariff_eur_mwh` holds 100 (correct)
3. ✅ Runtime summary shows changed Total Revenue after run (correct)
4. ❌ Lower assumption card showed 60.00 EUR/MWh — stale factory value (misleading)

### Questions Answered

1. **Are lower Revenue summary values from project_ctx factory reference?** → YES
2. **Are they updated from saved scenario snapshot?** → NO, never
3. **Are they updated from runtime output?** → NO, never
4. **Where is runtime summary rendered after Run?** → `#model-output-area` via HTMX swap from `/run`
5. **Does user have to scroll to see changed revenue?** → YES, runtime summary is below the Revenue tab content
6. **Is PPA Tariff runtime-bound?** → YES (`tariff_eur_mwh` is in `_collect_form_snapshot` and passed to `RevenueInput`)
7. **Is P50 Hours runtime-bound?** → YES (`p50_hours` is in `_collect_form_snapshot` and passed to `RevenueInput`)
8. **Is PPA Term preview-only/not runtime-bound?** → YES (explicitly marked "Preview only — not runtime-bound yet")

## Fixes Applied

### Fix 1: Rename Lower Section to "Saved Scenario / Factory Reference Values"

**File:** `app/templates/partials/sheet_revenue.html`

The lower section now displays both saved scenario values AND factory reference values. Renamed to reflect this duality:
- Section header: "Saved Scenario / Factory Reference Values"
- The section no longer implies all values are factory-only

### Fix 2: Show Saved Scenario Values with Factory Fallback

**File:** `app/templates/partials/sheet_revenue.html`

PPA Tariff and PPA Term now show saved scenario values when available, with factory reference as fallback:

```
{% if form_data.get('tariff_eur_mwh') %}
  {{ form_data.get('tariff_eur_mwh') }} EUR/MWh  (saved scenario)
{% else %}
  {{ project_ctx.ppa_tariff_eur_mwh }} EUR/MWh  (factory reference)
{% endif %}
```

Each value is labeled: "saved scenario", "saved — preview only", or "factory reference".

### Fix 3: Clear Explanatory Note

**File:** `app/templates/partials/sheet_revenue.html`

Factory reference note now explains the dual-source behavior:
> "Saved scenario values are shown when available. Factory reference values are shown only when no saved scenario value exists. Runtime output appears in the Runtime Summary after Run."

### Fix 4: p50_hours Classification Fixed

**File:** `app/templates/partials/sheet_revenue.html`

Updated p50_hours note from vague "Runtime authority stays in the model layer" to:
> "Runtime-bound — used by model to calculate revenue."

`p50_hours` IS runtime-bound: it appears in `_collect_form_snapshot`, is passed to `RevenueInput`, and the runtime model uses it to calculate revenue. The output is shown as Total Revenue KPI.

### Fix 5: Runtime Anchor Notice

**File:** `app/templates/partials/sheet_revenue.html`

Output Preview placeholder now directs users to scroll to Runtime Summary after running.

## Files Changed

- `app/templates/partials/sheet_revenue.html`
- `docs/phase16_runtime_state_visible_binding_fix.md` (this document)
- `reports/phase16_runtime_state_render_matrix.csv`
- `reports/phase16_revenue_tab_truth_sources.csv`
- `reports/phase16_runtime_state_visible_remaining_gaps.csv`
- `tests/test_phase16_runtime_state_visible_binding_fix.py`

No changes to `main_web.py`, `app.js`, or backend logic — purely a presentation layer fix.
