# Pilot Readiness — FincoGPT HTMX Internal Demo

**Branch:** `feature/pilot-readiness`
**Date:** 2026-05-08
**Status:** Ready for review

---

## What Was Built

### 1. `/run/{run_id}/detail` — Run Detail Page
Full detail view for a saved run, showing:
- Timestamp (UTC)
- Project type + scenario badge (color-coded: Base=blue, Downside=red, Upside=green)
- All model inputs as a grid (capacity, tariff, P50 hours, CAPEX, OPEX, gearing, DSCR, interest rate, tenor)
- KPI results card
- "Export to Excel" button

Clicking a run in the history panel loads its detail into `#results-area`.

### 2. `POST /run/{run_id}/export` — Export to Excel
Reconstructs `ProjectInputsSchema` from the stored inputs JSON, re-runs the model, returns the generated `.xlsx` file with filename including run ID.

### 3. Run History Panel Updates (`run_history.html`)
- Project IRR and Equity IRR shown per run (formatted as %)
- Scenario badge colors: **Base**=blue, **Downside**=red, **Upside**=green
- Hover effect: left blue border + slight background change + padding inset
- Clicking a run navigates to `/run/{run_id}/detail`

### 4. Empty State UI (`run_history.html`)
New CSS-only folder icon (no emoji) with text:
> "No saved runs yet. Fill the form and click **Save Run**"

### 5. CSS Spinner for `.htmx-indicator`
CSS keyframe spin animation on `::before` pseudo-element of `.htmx-indicator`. Works without JavaScript. Spinner replaces the "Validating..." text during HTMX requests.

### 6. Error Banner Partial (`error_banner.html`)
Red banner for model errors with:
- Warning icon + error messages
- Dismiss button (✕) that removes the element from DOM
- Slide-down entrance animation
- Used by `/run` endpoint and `/run/{run_id}/detail` on not-found

### 7. Mobile CSS (`@media max-width: 768px`)
- Sidebar becomes a top nav (stacked layout, full width)
- KPI grid: 2 columns
- Run history items and detail actions stack vertically
- Caveats icon decorations hidden on mobile

### 8. Collapsible Caveats Banner (`index.html`)
- Top of page, muted amber styling
- Summary line: "Screening-grade model — for advisory use only. Validate with project-specific data."
- "▼ Hide caveats" / "▶ Show caveats" toggle button
- Expanded body lists the caveats + TUHO CO2 and Oborovo OpEx detail note
- Pre-existing `CAVEATS` list from `main_web.py` rendered inside the collapsible body

---

## Caveats Banner Text

> ⚠️ Screening-grade model — for advisory use only. Validate with project-specific data.

Expanded details:
- **TUHO CO2 caveat:** 611 kEUR Y1 CO2 revenue missing — model understates revenue for TUHO wind assets.
- **Oborovo OpEx caveat:** 660 kEUR Y1 OpEx duplication — model overstates OpEx for Oborovo solar.

---

## Files Changed

| File | Change |
|------|--------|
| `main_web.py` | Added `GET /run/{run_id}/detail` and `POST /run/{run_id}/export` endpoints; switched `/run` model error to use `error_banner.html` |
| `app/templates/partials/error_banner.html` | **New** — red dismissible error banner partial |
| `app/templates/partials/run_detail.html` | **New** — run detail card with inputs grid, KPIs, export button |
| `app/templates/partials/run_history.html` | Scenario badge colors, hover effect, empty state with CSS-only icon, IRR display per run |
| `app/templates/index.html` | Collapsible caveats banner replacing static one |
| `static/styles.css` | CSS spinner for `.htmx-indicator`, collapsible caveats CSS, mobile layout (`@media 768px`) |

---

## Test Results

```
60 passed in 8.58s
```

Tests cover: persistence layer (save/get/list/delete, user isolation), all HTMX routes (`/validate`, `/run`, `/compare`, `/download`, auth guards), and behavioral assertions (custom inputs change outputs, no traceback leakage, no silent defaults).

---

## Merge Recommendation

**Do not merge to `main` yet.** Recommended next steps:

1. **Review** the collapsible caveats wording with the business — the summary line "Screening-grade model — for advisory use only" is intentionally prominent; confirm it matches compliance/legal requirements
2. **Database migration** not needed — persistence layer uses existing schema (`runs` table already has `inputs_json`/`kpis_json` columns)
3. **Session auth required** for all new endpoints (`/run/{run_id}/detail`, `/run/{run_id}/export`) — enforced by `get_current_user` dependency, consistent with existing routes
4. **No DB schema changes** — all data flows through existing repository functions
5. **Export endpoint**: re-runs model on export to ensure Excel reflects current codebase (not stale cached values) — intentional design
