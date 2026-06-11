# Phase P2-min-4 — Navigation Compression — Test Report

**Date:** 2026-06-11
**Branch:** `p2-min-4-navigation-compression`
**Base:** `p2-min-3-dashboard-v1` (PR3 DRAFT, PR #611, head `9074601`)

## Test counts

| Suite | Tests | Pass | Skip | Fail |
|---|---|---|---|---|
| `test_phase_p2min4_navigation_compression.py` | 16 | 16 | 0 | 0 |
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

## File-scope audit

P2-min-4 touches only:

- `app/templates/partials/_nav_compression.html` (NEW)
- `app/templates/base.html` (MODIFIED — guarded `{% include %}`)
- `static/styles.css` (MODIFIED — small `.nav-compression` CSS block)
- `main_web.py` (MODIFIED — `nav_compression_enabled` in `GET /` context)
- `tests/test_phase_p2min4_navigation_compression.py` (NEW)
- `docs/phase_p2min4_navigation_compression.md` (NEW)
- `reports/phase_p2min4_navigation_compression.md` (NEW)
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
- No route / panel / ws-tab button deletion (hidden != deleted) ✓
- All 20 ws-tab buttons preserved ✓
- All 20 panel-... elements preserved ✓

## PR4 brief compliance

- 5-6 compressed top-level tabs (Dashboard, Inputs, Scenarios, Outputs, Export & Audit, Help) ✓
- Dashboard is the default view ✓
- Underlying ws-tab buttons preserved (hidden != deleted) ✓
- All 20 panel panels preserved ✓
- No route deletion / no backend deletion ✓
- Uses existing switchTab JS function (no new JS lib) ✓
- No Tailwind / Alpine / React / Vue / Svelte / Chart.js / Plotly / D3 ✓

## Stop-after-report contract

DRAFT PR #612. Do NOT mark ready. Do NOT merge.
Awaiting user review and explicit go-ahead before
PR4 lands on PR3. This is the final PR of the
P2-min stacked UX simplification arc.
