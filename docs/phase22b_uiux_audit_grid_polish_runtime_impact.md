# Phase 22B — UI/UX Audit Grid Polish: Runtime Impact

## Executive Summary

Adds user-facing `Runtime Impact` labels to CAPEX detail grid rows, a display-only warning banner, and badge consolidation. Finance users can now quickly identify whether a row drives the model or is display/reference/pending treatment. No runtime calculations changed.

## Why This Phase Exists

Phase 20/21 added a rich display/schema layer (authority badges, scope badges, mapping notes, schedules). The risk: users may interpret display/reference/schema rows as runtime-effective model inputs. This phase reduces that confusion.

> "Product is getting very good at showing structure it does not yet calculate."

## Runtime Impact Mapping

| Internal Status | User-facing Label | Priority |
|---|---|---|
| scope = project_rights + treatment_resolved=false | **Pending treatment** | 1 (highest) |
| scope = aggregate_total | **Drives model** | 2 |
| authority_status = backend_authoritative | **Drives model** | 3 |
| timing_only=True (non-project_rights) | **Timing only** | 4 |
| authority_status = app_mapped + affects_runtime=true | **Drives model** | 5 |
| authority_status = app_mapped + affects_runtime=false | **Display only** | 6 |
| authority_status = excel_reference_only | **Reference only** | 7 |
| authority_status = missing_runtime_source | **Pending runtime source** | 8 |
| authority_status = scope_mismatch | **Not comparable** | 9 |
| authority_status = mismatch | **Needs review** | 10 |
| authority_status = not_applicable | **Not applicable** | 11 |
| authority_status = deferred | **Deferred** | 12 |

**Priority order**: project_rights > aggregate_total > backend_authoritative > timing_only > app_mapped > excel_reference_only > ...

**Why this priority?**
- project_rights (C.16) must be explicitly treated before use
- aggregate_total is a real period-spanning CAPEX total
- timing_only rows have schedules but those schedules are construction-draw/IDC-timing references, not duplicate CAPEX totals

## UI Changes

### Display-only banner
Added at top of CAPEX detail grid (before the grid):
```
⚠ CAPEX detail grid is an audit/display view.
Rows marked Display only, Reference only, Pending treatment, or Not comparable
do not affect runtime calculations today.

C.16 Project Rights is not runtime-effective.
M1–M18 schedule is timing-only (not summed into CAPEX total, not wired to IDC).
Treatment options are design-only until explicitly wired.
```

### Runtime Impact column
Each row now shows a Runtime Impact pill badge (primary visual cue, before authority badges):
- 🟢 Drives model (green) — backend_authoritative or aggregate_total
- ⚪ Display only (gray) — app_mapped but not affecting runtime
- 🟣 Reference only (purple) — excel_reference_only
- 🟠 Pending treatment (orange) — C.16 Project Rights with unresolved treatment
- 🟡 Pending runtime source (amber) — missing_runtime_source
- 🟡 Not comparable (amber) — scope_mismatch
- 🔴 Needs review (red) — mismatch
- 🔵 Timing only (teal) — M1-M18 schedule row (IDC/construction draw)
- ⚫ Not applicable (dark gray)
- ⚫ Unknown (light gray)

### Badge hierarchy (status cell)
1. **Runtime Impact pill** — primary, most visible
2. **Scope badge** — secondary (agg✓, pymt, fee, rights, tim)
3. **Authority badge** — tertiary (auth✓, app, excel, ?src, ≠, ≠scp, defer, N/A)
4. Source type label (4-char)

### Legend update
Added "Runtime Impact (Phase 22B)" row to the existing legend below the grid.

## C.16 Project Rights Status
- `affects_runtime = false` — unchanged
- `scope = project_rights` — unchanged
- `runtime_impact = "Pending treatment"` — NEW
- NOT editable — unchanged
- NOT wired to runtime — unchanged

## M1–M18 Schedule Status
- `timing_only = true` — unchanged
- `runtime_impact = "Timing only"` — NEW (for non-project_rights rows)
- Not summed into CAPEX total — unchanged
- Not wired to IDC — unchanged

## What Was NOT Changed
- ❌ No runtime calculations changed
- ❌ No CAPEX totals changed
- ❌ No treatment dropdowns added
- ❌ No line editing enabled
- ❌ C.16 not wired to runtime
- ❌ M1-M18 not wired to IDC
- ❌ No JS financial calculations added
- ❌ G20 BLOCKED
- ❌ R99/R102 NOT APPROVED

## Recommended Next Phase
- **Phase 22C**: Add compact/audit mode toggle to CAPEX grid, wire C.16 treatment to runtime after user confirmation, bridge M1-M18 to construction IDC draw schedule.
- Or: **Phase 21G** — treatment panel UI with per-dimension dropdowns (if user confirms scope)