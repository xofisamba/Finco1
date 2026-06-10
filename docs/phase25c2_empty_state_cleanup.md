# Phase 25C-2 — User-Facing Error / Empty State Cleanup (Generic Solar / Wind)

**Type**: UI only. **No** autosave. **No** backend change. **No** feature flag enablement. **No** schema change. **No** model formula change. **No** model output computation. The helper is a pure read-side message classifier; the runtime is the source of truth for all outputs.

**Status**: DRAFT PR. **Do NOT mark ready.** Do NOT merge. Do NOT start any further runtime work before review and explicit go-ahead.

**Base**: `c80fa3391e1c475d575c981244812e16c859a8dc` (post-25B Closure merge, 25B-4/5/6 + Closure all merged).

**Branch**: `phase25c-2-empty-state-cleanup`

## 1. Goal

Provide 7 user-facing empty / error state messages for the Generic Solar / Generic Wind exploratory workflow. Each message:
- shows a clear, friendly title
- explains the situation in 1-2 sentences
- points the user to the next action via a pre-existing app route
- has a severity in {info, warning, error}
- does NOT contain stack traces, UndefinedError, AttributeError, or internal error codes
- does NOT make audit / lender / bank / parity claims

## 2. The 7 conditions (per the user's 25C-2 brief)

| Condition | Severity | When | Next action |
|---|---|---|---|
| `no_project` | info | User opens the app without a project | Create a project (`/projects/create`) |
| `no_scenario` | info | Project exists, no scenarios | Save a Base scenario (`/scenarios/save`) |
| `not_run` | info | Scenario exists, no run | Run the model (`/scenarios/run`) |
| `lt_2_scenarios` | info | Compare page open with <2 scenarios | Duplicate a scenario (`/scenarios/add`) |
| `export_before_run` | warning | User tries to export before running | Run the model first (`/scenarios/run`) |
| `dirty_unsaved` | warning | Scenario has unsaved changes | Save the draft (`/scenarios/save`) |
| `stale_run` | warning | One of two compared scenarios has a stale run | Re-run the affected scenario (`/scenarios/run`) |

## 3. Changed files (4 files, +1130 / -0)

| Status | File | Lines | Rationale |
|---|---|---|---|
| A | `app/ui/empty_state_messages.py` | +320 | Pure read-side helper. 7 condition vocabulary (CONDITION_*). 3 severity vocabulary (SEVERITY_*). 9 action vocabulary (ACTION_*). `build_message(condition, project_label)`. `build_all_messages(project_label)`. `is_supported_condition(cond)`. Frozen `Message` dataclass. NO persistence calls, NO mutation, NO imports from `app.persistence` / `app.services` / `app.waterfall` / `app.construction` / `app.debt` / `app.tax` / `app.depreciation` / `app.idc`. |
| A | `app/templates/partials/_empty_state_message.html` | +45 | Jinja partial. Renders nothing if `empty_state_message` is missing. Otherwise renders severity badge + title + body + next-action link. No JS, no Tailwind, no Alpine, no inline script. No new HTMX endpoints. |
| A | `tests/test_phase25c2_empty_state_messages.py` | +400 | 72 helper unit tests pinning: condition vocabulary, is_supported_condition, message shape, no stack trace in body/title, pre-existing routes, severity distribution, exploratory note, build_all_messages, no forbidden imports, no feature flag enablement, no fake run IDs / validation / outputs. |
| A | `tests/test_phase25c2_empty_state_factory_safety.py` | +365 | 41 factory safety tests pinning: determinism, no forbidden imports, partial: no JS / no Tailwind / no Alpine / no HTMX, partial: renders nothing when context missing, partial: renders title + body + action, rc1 frozen, no schema changes, no autosave, factory projects safe. |
| A | `docs/phase25c2_empty_state_cleanup.md` | this file | 8-section design + change doc with goal, condition list, file change list, self-review findings, pre-merge audit, hard no-go list, stop-after-report contract. |
| A | `reports/phase25c2_empty_state_cleanup.json` | +40 | Machine-readable summary. |

**ZERO changes to**:
- `app/persistence/`
- `app/services/`
- `app/waterfall_core.py`
- `app/waterfall_runner.py`
- `app/construction/`, `app/debt/`, `app/tax/`, `app/depreciation/`, `app/idc/`
- `static/app.js`, `static/styles.css`
- `main_web.py`, `main_api.py`, `domain/`
- `app/excel_export.py`

## 4. Self-review findings

- The 7 conditions are stable; the test `test_all_conditions_count` pins the count at 7.
- Severity distribution matches the user brief: 4 info + 3 warning.
- All next-action routes are **pre-existing** app routes; we never invent new ones. The test `test_message_routes_are_pre_existing` is parametrized over all 7 conditions.
- The body text never contains `traceback`, `UndefinedError`, `AttributeError`, `TypeError`, or `KeyError`. The test `test_message_body_does_not_contain_stack_trace` is parametrized over all 7 conditions.
- The export_before_run condition carries the exploratory scope language; the body never claims the project IS audit-ready. The test `test_messages_dont_claim_audit` enforces this.
- The helper does not import any forbidden module. The test `test_forbidden_module_not_imported` is parametrized over 8 forbidden modules.
- The helper does not enable any feature flag. The test `test_helper_does_not_set_construction_flag` pins `use_construction_schedule_engine` is not set.

## 5. Pre-merge audit (all green)

- **Scope**: UI only. No backend change. No autosave.
- **Forbidden paths**: zero changes (all forbidden-paths tests pass)
- **Feature flags**: none enabled (`use_construction_schedule_engine=False`)
- **Schema**: zero migrations
- **rc1 SHA**: `b425a0708719eaa5e1d922b1008e5609758e0ad4` verified untouched
- **Tests**: 72 helper tests + 41 factory safety tests = **113/113 new tests PASS**
- **No regressions**: 25B Closure 30/30 + 51F 21/21 + route smoke 50/17 = **193 passed / 38 skipped** in the focused run
- **Factory safety**: TUHO / Oborovo inputs unchanged; helper is a pure read-side classifier

## 6. Hard no-go (15 items, all verified pre-push)

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

## 7. Stop-after-report contract

This PR is DRAFT. Do NOT mark ready. Do NOT merge. Do NOT start any further work before review and explicit go-ahead. After approval, the recommended next step is **Phase 25C-3 — Pilot Feedback Capture** as a separate DRAFT PR.
