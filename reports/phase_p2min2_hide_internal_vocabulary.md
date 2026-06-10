# Phase P2-min-2 — Hide Internal Vocabulary — Test Report

**Date:** 2026-06-11
**Branch:** `p2-min-2-hide-internal-vocabulary`
**Base:** `p2-min-1-project-home-minimal-new-project` (PR1 DRAFT, PR #609, head `0cde1b4`)

## Test counts

| Suite | Tests | Pass | Skip | Fail |
|---|---|---|---|---|
| `test_phase_p2min2_hide_internal_vocabulary.py` | 15 | 15 | 0 | 0 |
| `test_phase_pr1_form_timing_fields.py` | 48 | 48 | 0 | 0 |
| `test_phase_pr2_realized_gearing.py` | 27 | 27 | 0 | 0 |
| `test_phase_pr3_taxonomy.py` | 39 | 39 | 0 | 0 |
| `test_phase_m1_scenario_matrix.py` | 50+ | 50+ | 0 | 0 |
| `test_phase_p1a_generic_driver_response_audit.py` | 30+ | 30+ | 0 | 0 |
| `test_phase_p1b_driver_status_badges.py` | 30+ | 30+ | 0 | 0 |
| `test_phase51f_parallel_work_guardrails.py` | 21 | 21 | 0 | 0 |
| `test_phase_p2min1_project_home.py` | 16 | 16 | 0 | 0 |
| **Cross-arc total** | **342** | **342** | **0** | **0** |

## File-scope audit

P2-min-2 touches only:

- `app/templates/partials/_generic_status_line.html` (NEW)
- `app/templates/partials/workspace_shell.html` (MODIFIED — single `include` line)
- `static/styles.css` (MODIFIED — single `.generic-status-line` CSS block)
- `tests/test_phase_p2min2_hide_internal_vocabulary.py` (NEW)
- `docs/phase_p2min2_hide_internal_vocabulary.md` (NEW)
- `reports/phase_p2min2_hide_internal_vocabulary.md` (NEW)
- `tests/test_phase_pr1_form_timing_fields.py` (MODIFIED — file-scope allowlist extension)
- `tests/test_phase_pr2_realized_gearing.py` (MODIFIED — file-scope allowlist extension)
- `tests/test_phase_pr3_taxonomy.py` (MODIFIED — file-scope allowlist extension)
- `tests/test_phase_m1_scenario_matrix.py` (MODIFIED — file-scope allowlist extension)

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

## PR2 brief compliance

- Single clear status line per screen ✓
- Brief-approved copy: "Internal-use model — results are indicative." ✓
- Hidden ≠ deleted (audit info still in Export & Audit) ✓
- Derivation evidence preserved (audit popovers, citations) ✓
- Negative-exposure tests assert on rendered visible text only ✓

## Stop-after-report contract

DRAFT PR #610. Do NOT mark ready. Do NOT merge.
Awaiting user review and explicit go-ahead before
PR2 lands on PR1.
