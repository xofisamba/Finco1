# Phase 24C: Debt / DSCR / SHL UI

## Base SHA
`6f21145` (after PR #322 merge)

## Why Phase 24C
Phase 24A established the Runtime Impact taxonomy. Phase 24B documented scenario state banner + validation bar. Phase 24C surfaces the now-stable debt/DSCR/SHL backend behavior in a dedicated UI panel.

## Objective
Add Debt / DSCR / SHL UI visibility. UI/reporting only — no formula/runtime changes unless a regression is discovered.

## New Partial

`app/templates/partials/debt_dscr_shl_panel.html`

A small, self-contained partial that surfaces:
- Senior debt anchor (from `runtime_summary`)
- Senior debt schedule table (from `debt_table`)
- SHL status (balance, service, interest/PIK, lock-up)
- Distribution lock-up status (blocked/active, first valid distribution)

## Panel Sections

### Provenance / Runtime Impact Banner
- Badge: "Drives model" (Runtime Impact: Phase 24A taxonomy)
- Badge: "Fixture-backed · No sculpting" (explicitly states no sculpting solver)
- Note: "DSCR is backward-computed from frozen senior debt service"

### Senior Debt Anchor
From `runtime_summary`:
| Field | Source |
|-------|--------|
| Senior Debt | `runtime_summary.senior_debt_keur` |
| SHL Opening | `runtime_summary.shl_opening_keur` |
| Avg DSCR | `runtime_summary.avg_dscr` |
| Min DSCR | `runtime_summary.min_dscr` |

### Senior Debt Schedule Table
From `debt_table` (built via `build_debt_table()` in `output_tables.py`):
| Row | Field |
|-----|-------|
| Senior Interest | `senior_interest_keur` |
| Senior Principal | `senior_principal_keur` |
| Senior Debt Service | `senior_debt_service_keur` |
| Senior Debt Balance | `senior_debt_balance_keur` |
| DSCR | `dscr` |
| LLCR | `llcr` |
| PLCR | `plcr` |

DSCR infinity display: `n/a — debt repaid` (for merchant periods where debt is repaid).

### SHL Status
| Field | Description |
|-------|-------------|
| SHL Balance | Opening/current SHL balance |
| SHL Service | SHL service amount |
| SHL Interest / PIK | Interest or PIK accrued |
| Lock-up Status | "Distribution blocked" (SHL outstanding) or "SHL cleared" |

### Distribution Lock-up Status
| State | Badge |
|-------|-------|
| SHL outstanding | `badge-warn` "Distribution blocked — SHL outstanding" |
| SHL cleared | `badge-pass` "Distributions active" |
| First valid distribution | Date + amount (e.g., "2050-06-30 · 2,994 kEUR") |

## Frozen Senior DS Treatment

- **Runtime Impact**: Drives model
- **Sub-reason**: Fixture-backed frozen Excel schedule
- **No sculpting claim**: Explicitly states "No sculpting" in badge

## DSCR Infinity Display

`n/a — debt repaid` or equivalent — for periods where debt is fully repaid and DSCR is infinite.

## Oborovo First Valid Distribution

- **op_idx 39** / **2050-06-30** / **~2,994 kEUR**
- Lock-up: op_idx 0-37 blocked, op_idx 38 guard, op_idx 39 first dist
- SHL cleared at op_idx 38 (2049-12-31)

## TUHO SHL / Distribution Regression Status

- TUHO uses PIK+Sweep SHL — balance grows over time (PIK bullet)
- No distributions while SHL outstanding — confirmed by test
- No runtime changes from Phase 23U baseline

## Runtime Impact Taxonomy Reuse

Phase 24A `app/runtime_impact_taxonomy.py` is reused:
- `RuntimeImpactStatus.DRIVES_MODEL` for the panel badge
- `get_frozen_senior_ds_taxonomy()` for sub-reason text
- No new primary labels invented

## JS Limitations

- JS may toggle/expand tables
- JS must NOT calculate financial results
- Backend remains source of truth

## UI Surfaces Touched

| Surface | Change |
|---------|--------|
| `app/templates/partials/debt_dscr_shl_panel.html` | NEW — Debt/DSCR/SHL panel |
| `app/ui/runtime_summary.py` | Unchanged — provides `runtime_summary` context |
| `app/output_tables.py` | Unchanged — provides `debt_table` via `build_debt_table()` |
| `static/app.js` | No financial calculations added |

## Guardrails

- ✅ No financial formula changes
- ✅ No runtime calculation changes
- ✅ No factory flag changes
- ✅ No fixture value changes
- ✅ No Revenue/OPEX/CAPEX/Tax changes
- ✅ G20 BLOCKED
- ✅ R99/R102 NOT APPROVED
- ✅ partial_pay_sweep not promoted
- ✅ flat/min DSCR sculpting not promoted
- ✅ PR #299 remains draft / not merged / superseded
- ✅ Backend remains source of truth
- ✅ No JS financial calculations

## Tests

10 tests in `tests/test_phase24c_debt_dscr_shl_ui.py`:
1. `test_debt_dscr_shl_panel_exists_or_renders` ✅
2. `test_frozen_senior_ds_status_uses_runtime_impact_taxonomy` ✅
3. `test_dscr_inf_rendered_as_debt_repaid` ✅
4. `test_oborovo_distribution_lockup_status_rendered` ✅
5. `test_tuho_no_distribution_leak_status_rendered` ✅
6. `test_senior_debt_schedule_fields_present` ✅
7. `test_shl_fields_present` ✅
8. `test_no_js_financial_calculations_added` ✅
9. `test_no_runtime_output_changes` ✅
10. `test_guardrails_unchanged` ✅

Full suite: **157 passed, 2 xfailed, 1 xpassed**

## Known Limitations

- `debt_dscr_shl_panel.html` is a new partial — it needs to be wired into a route/workspace tab to appear in the UI. This phase creates the partial and tests; routing into the workspace is a subsequent step.
- `debt_table` from `build_debt_table()` provides the debt schedule rows — the partial uses Jinja2 loop `{% for row_label, row_data in debt_table.rows.items() %}` which requires the table to be serialized as a dict-of-lists or similar structure in the route context.
- DSCR infinity / "n/a — debt repaid" display is implemented in the partial as a CSS class + label; the actual infinite value from the backend is `float('inf')`.

## Recommended Next Phase

**Phase 24D — Shared LineItemGrid**
- Extract shared grid rendering logic for CAPEX/OPEX/Revenue line items
- Reduce duplication across sheet partials
- The debt panel reveals that multiple sheets use similar table-rendering patterns

**Phase 24E — Audit / Reconciliation Tab** (alternative)
- Apply the audit/reconciliation surface on top of the debt panel
- Standardize the gap register display
