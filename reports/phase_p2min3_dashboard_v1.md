# Phase P2-min-3 — Dashboard v1 — Test Report

**Date:** 2026-06-11
**Branch:** `p2-min-3-dashboard-v1`
**Base:** `p2-min-2-hide-internal-vocabulary` (PR2 DRAFT, PR #610, head `fcc366a`)

## Test counts

| Suite | Tests | Pass | Skip | Fail |
|---|---|---|---|---|
| `test_phase_p2min3_dashboard_v1.py` | 19 | 19 | 0 | 0 |
| `test_phase_p2min2_hide_internal_vocabulary.py` | 15 | 15 | 0 | 0 |
| `test_phase_p2min1_project_home.py` | 16 | 16 | 0 | 0 |
| `test_phase_pr1_form_timing_fields.py` | 48 | 48 | 0 | 0 |
| `test_phase_pr2_realized_gearing.py` | 27 | 27 | 0 | 0 |
| `test_phase_pr3_taxonomy.py` | 39 | 39 | 0 | 0 |
| `test_phase_m1_scenario_matrix.py` | 50+ | 50+ | 0 | 0 |
| `test_phase_p1a_generic_driver_response_audit.py` | 30+ | 30+ | 0 | 0 |
| `test_phase_p1b_driver_status_badges.py` | 30+ | 30+ | 0 | 0 |
| `test_phase51f_parallel_work_guardrails.py` | 21 | 21 | 0 | 0 |
| **Cross-arc total** | **361** | **361** | **0** | **0** |

## File-scope audit

P2-min-3 touches only:

- `app/ui/dashboard.py` (NEW)
- `app/templates/partials/_dashboard.html` (NEW)
- `app/templates/partials/workspace_shell.html` (MODIFIED — guarded `{% include %}`)
- `static/styles.css` (MODIFIED — small `.dashboard` CSS block)
- `main_web.py` (MODIFIED — `_build_index_dashboard_context` helper + dashboard data in `GET /` context)
- `tests/test_phase_p2min3_dashboard_v1.py` (NEW)
- `docs/phase_p2min3_dashboard_v1.md` (NEW)
- `reports/phase_p2min3_dashboard_v1.md` (NEW)
- `tests/test_phase_pr1_form_timing_fields.py` (MODIFIED — file-scope allowlist)
- `tests/test_phase_pr2_realized_gearing.py` (MODIFIED — file-scope allowlist)
- `tests/test_phase_pr3_taxonomy.py` (MODIFIED — file-scope allowlist)
- `tests/test_phase_m1_scenario_matrix.py` (MODIFIED — file-scope allowlist)

## Phase invariants verified

- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` resolvable ✓
- `use_construction_schedule_engine` remains False ✓
- 21/21 Phase 51F parity guardrails PASS ✓
- No formula / model / factory changes ✓
- No persistence schema migration ✓
- No `app/services/` downstream service code changes ✓
- No `static/app.js` changes ✓
- No `main_api.py` changes ✓
- No route / CSS class / context-key / test / project_origin renames ✓
- No Chart.js / Plotly / D3 / React / Vue / Svelte / Tailwind / Alpine ✓
- No JS calc ✓
- Realized gearing computed in Python (not in Jinja / JS / SVG) ✓
- Debt balance uses explicit result field (NOT `_find_debt_balance`) ✓

## PR3 brief compliance

- 8 KPI cards (project_irr, equity_irr, senior_debt, realized_gearing, min_dscr, avg_dscr, y1_revenue, y1_ebitda) ✓
- 3 inline-SVG charts (revenue/ebitda, dscr+target, debt balance) ✓
- Server-rendered inline SVG only ✓
- No Chart.js / Plotly / D3 / any JS library ✓
- Realized gearing computed in Python ✓
- Debt balance from explicit result field ✓
- Hidden != deleted (existing Overview KPI grid + Governance + Parity remain) ✓

## Stop-after-report contract

DRAFT PR #611. Do NOT mark ready. Do NOT merge.
Awaiting user review and explicit go-ahead before
PR3 lands on PR2.
