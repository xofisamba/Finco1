# Phase 25C Closure — Third-Party Test Readiness Gate

**Type**: UI only. **No** autosave. **No** backend change. **No** feature flag enablement. **No** schema change. **No** model formula change. **No** model output computation. The helper is a pure read-side audit; it does not run the model and does not call the runtime.

**Status**: DRAFT PR. **Do NOT mark ready.** Do NOT merge. Do NOT start any further runtime work before review and explicit go-ahead.

**Base**: `c80fa3391e1c475d575c981244812e16c859a8dc` (post-25B Closure merge, 25B-4/5/6 + Closure all merged).

**Branch**: `phase25c-closure-third-party-gate`

## 1. Goal

Audit 10 workflows of the Generic Solar / Wind exploratory pilot. For each workflow, score four dimensions:
- helper present (25 pts)
- partial present (25 pts)
- helper tests pass (25 pts)
- factory safety tests pass (25 pts)

Compute the overall score (average across workflows), map to a readiness bucket, and emit a Go / No-Go verdict, an exact pilot test checklist, remaining blockers, and suggested tester instructions.

## 2. The 10 workflows audited

| # | Workflow | Description | Phase link |
|---|---|---|---|
| 1 | create_project | User creates a new project | 25C-1 (step 1) |
| 2 | prefill_defaults | User accepts generic defaults | 25C-1 (step 2) |
| 3 | save | User saves a Base scenario | 25C-1 (step 3) |
| 4 | run | User runs the model | 25C-1 (step 4) |
| 5 | edit | User edits scenario inputs | 25C-1 (step 6) |
| 6 | rerun | User re-runs a scenario | 25C-1 (step 7) |
| 7 | compare | User opens the compare view | 25C-1 (step 8) |
| 8 | export | User exports the workbook | 25C-1 (step 9) |
| 9 | understand_limitations | User reads the exploratory disclaimer | 25C-1 + 25C-2 |
| 10 | report_feedback | User reports feedback via the 25C-3 panel | 25C-3 |

## 3. The 4 readiness buckets (per the user brief)

| Bucket | Threshold | Meaning |
|---|---|---|
| `pilot_ready` | >= 90 | Go for third-party pilot test |
| `close_to_pilot` | >= 70 | Go with caveat (user must read disclaimer) |
| `pilot_blocked` | >= 50 | No-Go; address blockers first |
| `not_ready` | < 50 | No-Go; fundamental gaps remain |

## 4. Scoring

Each workflow scores 0-100 (25 per dimension). The overall score is the average across the 10 workflows.

## 5. Pilot test checklist (10 items)

For each of the 10 workflows, the helper emits a 1-line expected outcome. The tester can use this as a smoke-test checklist.

## 6. Suggested tester instructions (11 lines)

The helper exposes 11 specific instructions the tester can follow. The instructions cover:
1. Create a new project
2. Accept generic defaults
3. Save Base
4. Run Base
5. Duplicate Base as Downside
6. Run Downside
7. Open compare
8. Export
9. Read exploratory disclaimer
10. Use feedback panel
11. Submit feedback

## 7. Changed files (4 files, +1503 / -0)

| Status | File | Lines | Rationale |
|---|---|---|---|
| A | `app/ui/third_party_test_readiness.py` | +580 | Pure read-side audit helper. 10 workflow vocabulary. 4 readiness buckets with thresholds. `WorkflowEntry` input. `WorkflowScore` / `TestChecklistItem` / `ThirdPartyTestReadiness` output. `build_third_party_test_readiness(entries)`. NO persistence calls, NO mutation, NO forbidden imports. |
| A | `app/templates/partials/_third_party_test_readiness.html` | +120 | Jinja partial. Renders nothing if `third_party_test_readiness` is missing. Otherwise renders verdict, per-workflow scores, checklist, blockers, tester instructions, phase 25C summary. No JS, no Tailwind, no Alpine, no inline script. No new HTMX endpoints. |
| A | `tests/test_phase25c_closure_third_party_test_readiness.py` | +610 | 62 helper unit tests pinning: workflow vocabulary, phase links, readiness buckets, is_supported_workflow, is_supported_bucket, scoring, bucket mapping, Go/No-Go, pilot test checklist, remaining blockers, tester instructions, phase 25C summary, no forbidden imports, no feature flag enablement, no fake run IDs / validation, no audit / lender / bank claims. |
| A | `tests/test_phase25c_closure_third_party_test_readiness_factory_safety.py` | +310 | 22 factory safety tests pinning: determinism, no forbidden imports, partial: no JS / no Alpine / no HTMX, partial: renders nothing when context missing, partial: renders verdict + 10 workflow labels, rc1 frozen, no schema changes, no autosave, factory projects safe. |
| A | `docs/phase25c_closure_third_party_test_readiness.md` | this file | 11-section design + change doc. |
| A | `reports/phase25c_closure_third_party_test_readiness.json` | +40 | Machine-readable summary. |

**ZERO changes to**:
- `app/persistence/`
- `app/services/`
- `app/waterfall_core.py`
- `app/waterfall_runner.py`
- `app/construction/`, `app/debt/`, `app/tax/`, `app/depreciation/`, `app/idc/`
- `static/app.js`, `static/styles.css`
- `main_web.py`, `main_api.py`, `domain/`
- `app/excel_export.py`

## 8. Self-review findings

- The 10 workflows are stable; the test `test_workflow_count` pins the count at 10.
- The 4 readiness buckets have correct thresholds: 90 / 70 / 50. The test `test_thresholds` enforces this.
- Scoring is 25 per dimension. The test `test_score` is parametrized over 8 score values.
- The Go / No-Go verdict is correct: `is_go` is True only if bucket is `pilot_ready` or `close_to_pilot`. The test `test_go_when_pilot_ready` and `test_no_go_when_not_ready` enforce this.
- The audit does not invent fake run IDs / validation / outputs. The tests `test_helper_does_not_invent_run_ids`, `test_helper_does_not_invent_validation`, `test_audit_does_not_claim_audit_readiness` enforce this.
- The audit does not claim the project IS audit-ready / lender-ready / bank-approved. The test `test_audit_does_not_claim_audit_readiness` enforces this.

## 9. Pre-merge audit (all green)

- **Scope**: UI only. No backend change. No autosave.
- **Forbidden paths**: zero changes (all forbidden-paths tests pass)
- **Feature flags**: none enabled (`use_construction_schedule_engine=False`)
- **Schema**: zero migrations
- **rc1 SHA**: `b425a0708719eaa5e1d922b1008e5609758e0ad4` verified untouched
- **Tests**: 62 helper tests + 22 factory safety tests = **84/84 new tests PASS**
- **No regressions**: 25B Closure 30/30 + 51F 21/21 + route smoke 50/17 = **164 passed / 38 skipped** in the focused run
- **Factory safety**: TUHO / Oborovo inputs unchanged; helper is a pure read-side classifier

## 10. Hard no-go (15 items, all verified pre-push)

1. no_autosave
2. no_persistence_schema_change
3. no_feature_flag_enablement
4. no_formula_changes
5. no_depreciation_changes
6. no_tax_changes
7. no_debt_changes
8. no_idc_changes
9. no_construction_promotion
10. no_rpar_changes
11. no_waterfall_core_changes
12. no_waterfall_runner_changes
13. no_services_changes
14. no_generic_depreciation_claims
15. rc1_frozen (`b425a0708719eaa5e1d922b1008e5609758e0ad4`)

## 11. Stop-after-report contract

This PR is the **last** of the 25C arc. **Do NOT mark ready.** Do NOT merge. Do NOT start any further work before review and explicit go-ahead.

**After approval**:
- The 25C arc (25C-1 + 25C-2 + 25C-3 + Closure) is closed.
- The 4 PRs are DRAFT and ready for review.
- A third-party pilot test can be initiated once the 4 PRs are merged.
- **Do NOT** start C10, construction, R-PAR, debt, tax, IDC, or runtime enablement. The 25C arc is the *last* work for the pilot-readiness wave.
