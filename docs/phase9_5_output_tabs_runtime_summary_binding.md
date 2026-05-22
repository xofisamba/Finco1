# Phase 9.5 — Output Tabs Runtime Summary Binding

## Overview

After a user runs TUHO or Oborovo via **Run Model**, output tabs (P&L, Cash Flow, Balance Sheet, Senior Debt, SHL, Tax, Distributions, Sponsor/Equity) now display a **runtime summary block** showing live calculated values from the waterfall engine — not static factory preview data.

## What was implemented

### Runtime Summary Propagation

The `runtime_summary` dict (already produced by `run_project()`) is now propagated to all output tabs via `sessionStorage`:

1. `POST /run` response receives an injected `<script>` that calls `sessionStorage.setItem("lastRuntimeSummary", JSON.stringify(runtime_summary))`
2. Each output tab's sheet partial contains an inline `<script>` that reads from `sessionStorage` and populates the runtime block DOM on page load and after HTMX swaps

This avoids new endpoints, complex HTMX routing, or full financial statement generation.

### Runtime Summary Object

Exposed fields in `runtime_summary` (via `runtime_summary_to_dict()` in `app/ui/runtime_summary.py`):

| Field | Source | Note |
|---|---|---|
| `active_project` | `run_project()` arg | `"tuho"` or `"oborovo"` |
| `project_name` | Project factory | Human-readable name |
| `run_status` | waterfall result | `"ok"` or error string |
| `project_irr` | `result["kpis"]["project_irr"]` | e.g. `9.41` |
| `equity_irr` | `result["kpis"]["equity_irr"]` | e.g. `11.15` |
| `total_revenue_keur` | waterfall | Sum over full horizon |
| `total_opex_keur` | waterfall | Sum over full horizon |
| `total_ebitda_keur` | waterfall | Sum over full horizon |
| `avg_dscr` | waterfall | Mean DSCR |
| `min_dscr` | waterfall | Min DSCR |
| `senior_debt_keur` | waterfall | Opening senior debt |
| `total_distributions_keur` | waterfall | Total equity distributions |
| `shl_opening_keur` | waterfall | SHL opening balance |
| `shl_total_interest_keur` | waterfall | Total SHL PIK interest |
| `shl_total_principal_keur` | waterfall | Total SHL principal |
| `tax_cash_keur` | waterfall | Total CIT paid |
| `cfads_keur` | waterfall | Total CFADS |
| `total_equity_irr_received_keur` | waterfall | Total equity CF |
| `equity_invested_keur` | waterfall | Total equity invested |

Unavailable metrics (not yet in runtime summary) show `"NOT_AVAILABLE"` — **not** zero, not fabricated.

### Output Tabs with Runtime Blocks

Each of 8 output tabs now includes a `{% include "partials/shared_runtime_block.html" %}` block at the top, with inline JS that reads from `sessionStorage`:

| Tab | Primary KPIs shown | Secondary metrics |
|---|---|---|
| **P&L** | Project IRR, Equity IRR, Avg DSCR, Revenue, EBITDA, OPEX | Total Distributions, SHL Opening |
| **Cash Flow** | Project IRR, Equity IRR, Avg DSCR, Revenue, EBITDA, OPEX | Total Distributions, SHL Opening |
| **Balance Sheet** | Project IRR, Equity IRR, Avg DSCR, Revenue, EBITDA, OPEX | Total Distributions, SHL Opening |
| **Senior Debt** | Project IRR, Equity IRR, Avg DSCR, Min DSCR | Senior Debt amount, Avg DSCR, Min DSCR |
| **SHL** | Project IRR, Equity IRR, Avg DSCR, Revenue | SHL Opening, Total Distributions |
| **Tax** | Project IRR, Equity IRR, Avg DSCR, Revenue, EBITDA, OPEX | CIT Status, G20 Gate, R99/R102 status |
| **Distributions** | (shared runtime block) | Total Distributions, DA-wired staging |
| **Sponsor/Equity** | (shared runtime block) | Equity IRR, Total Distributions, R99/R102 |

### HTMX Behavior

- After `POST /run`, the server injects a `<script>` into the HTMX response body that stores the `runtime_summary` in `sessionStorage` and calls `window._populateRuntimeBlock()`
- `htmx:afterSwap` event listener on `document` triggers `_populateRuntimeBlock()` when `#model-output-area` is swapped
- On page load, each tab's inline JS calls its populate function via `DOMContentLoaded`

### Preview vs Runtime Distinction

Every output tab follows this pattern:

```
┌─ RUNTIME SUMMARY BLOCK ──────────────────────────────────┐
│ [badge: Runtime summary] — last run                      │
│ Project: TUHO Wind 1                                     │
│ Project IRR: 9.41% | Equity IRR: 11.15% | Avg DSCR: 1.45 │
│ Revenue: 423,844 kEUR | EBITDA: 361,436 kEUR | OPEX: 85,408 │
└──────────────────────────────────────────────────────────┘

┌─ PREVIEW ───────────────────────────────────────────────┐
│ [badge: Template preview] Static TUHO factory snapshot   │
│ (static hardcoded P&L/CF/BS preview tables)              │
└──────────────────────────────────────────────────────────┘
```

All preview tables are labeled: **"Preview schedule — not live runtime output"**
All runtime blocks are labeled: **"Runtime summary — last run"**

## TUHO / Oborovo behavior

- **Run TUHO** → runtime blocks show TUHO values (Project IRR ~9.41%, Equity IRR ~11.15%, Revenue ~423,844 kEUR)
- **Run Oborovo** → runtime blocks show Oborovo values (Project IRR ~7.98%, Equity IRR ~9.17%, Revenue ~238,735 kEUR)
- Active project label in runtime block header
- No TUHO value leakage into Oborovo runtime blocks — each project's `run_project()` produces independent results

Guardrail values (not hardcoded in UI):

| Metric | TUHO | Oborovo |
|---|---|---|
| Project IRR | ~9.41% | ~7.98% |
| Equity IRR | ~11.15% | ~9.17% |
| Total Revenue | ~423,844 kEUR | ~238,735 kEUR |
| Total OPEX | ~85,408 kEUR | ~51,221 kEUR |
| Total Distributions | ~173,572 kEUR | ~104,699 kEUR |

## Missing Metric Policy

Unavailable metrics (not yet produced by runtime summary):
- Display as `NOT_AVAILABLE`
- **Never** display as 0 unless the metric is truly zero in the model
- Display as `BLOCKED` for G20 gate status
- Display as `NOT APPROVED` for R99/R102 status

## What was NOT changed

- ❌ No financial formula changes
- ❌ No waterfall logic changes
- ❌ No model engine rewrites
- ❌ No SHL mechanics changes
- ❌ No TaxBridge changes
- ❌ No DistributionAccount changes
- ❌ No SeniorDebtSizing changes
- ❌ No OPEX engine changes
- ❌ No R99/R102 promotion
- ❌ No G20 gate approval
- ❌ No database / persistence backend
- ❌ No Streamlit
- ❌ No React/Vue/Angular
- ❌ No spreadsheet engine
- ❌ No full financial statement generation (future phase)

## Future work

- Full P&L/CF/BS period-by-period output (Phase 10+)
- Tax period detail with R67 bridge visualization
- Distribution schedule period detail with lockup/sweep chart
- Sponsor waterfall with MoIC, TVPI, equity CF timeline
- Balance sheet period balances via `waterfall_core`

## Files changed

| File | Change |
|---|---|
| `app/templates/partials/shared_runtime_block.html` | **NEW** — shared runtime block partial with inline JS |
| `app/templates/partials/sheet_financials.html` | Runtime block + secondary metrics + inline JS |
| `app/templates/partials/sheet_senior_debt.html` | Runtime block + secondary metrics + inline JS |
| `app/templates/partials/sheet_shl.html` | Runtime block + secondary metrics + inline JS |
| `app/templates/partials/sheet_tax.html` | Runtime block + secondary metrics + inline JS |
| `app/templates/partials/workspace_shell.html` | Added `{% include %}` to 8 tab panels |
| `main_web.py` | Fixed SyntaxWarning, improved `save_tag` construction |

## Tests added

See `tests/test_phase9_5_output_tabs_runtime_summary_binding.py`:
1. Run TUHO returns runtime summary
2. Run Oborovo returns runtime summary
3. TUHO and Oborovo runtime summaries differ
4–11. Output tabs contain "Runtime summary — last run" text
12. Preview sections remain labeled as preview
13. Unavailable metrics show NOT_AVAILABLE
14. G20 BLOCKED remains visible
15. R99/R102 NOT APPROVED remains visible
16. No runtime model files changed

## PR

- PR #187: https://github.com/xofisamba/Finco1/pull/187 — squash-merged into `main`