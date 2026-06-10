# Phase 25C-3 — Pilot Feedback Capture (Generic Solar / Wind)

**Type**: UI only. **No** autosave. **No** backend change. **No** feature flag enablement. **No** schema change. **No** model formula change. **No** model output computation. **No** DB writes. **No** ticket IDs. **No** PII capture. The helper is a copy-paste template; the user pastes it into email, chat, or feedback form.

**Status**: DRAFT PR. **Do NOT mark ready.** Do NOT merge. Do NOT start any further runtime work before review and explicit go-ahead.

**Base**: `c80fa3391e1c475d575c981244812e16c859a8dc` (post-25B Closure merge, 25B-4/5/6 + Closure all merged).

**Branch**: `phase25c-3-feedback-capture`

## 1. Goal

Provide a structured, copyable feedback template for the Generic Solar / Generic Wind exploratory pilot. The template:
- has 6 fields: project, scenario, what I tried, what I expected, what happened, screenshot
- has a 3-line short summary template
- carries an exploratory disclaimer that mentions the channel is read by humans, is not a support channel, and warns against secrets / PII
- does NOT write to a database
- does NOT generate fake ticket IDs
- does NOT capture PII

## 2. The 6 fields (per the user's 25C-3 brief)

1. **Project name** — `e.g. 'My Solar 1'`
2. **Scenario name (or N/A)** — `e.g. 'Base', 'Downside'`
3. **What I tried** — `1-3 sentences`
4. **What I expected** — `1-3 sentences`
5. **What happened** — `1-3 sentences`
6. **Screenshot (optional)** — `attach to email/chat`

## 3. The 3-line short summary

```
Project:
What I tried:
What happened:
```

## 4. Exploratory disclaimer (descriptive scope language, not a no-go claim)

> This feedback channel is for the Generic Solar / Generic Wind exploratory pilot only. It is not a support channel for production use. DO NOT include secrets or customer PII. Your feedback is read by humans; it is not automatically processed.

## 5. Changed files (4 files, +978 / -0)

| Status | File | Lines | Rationale |
|---|---|---|---|
| A | `app/ui/feedback_capture.py` | +220 | Pure read-side helper. 6 field vocabulary (FIELD_*). 3-line short summary. `build_feedback_template()`. `is_supported_field(key)`. `is_short_line(line)`. Frozen `FeedbackField` / `FeedbackTemplate` dataclasses. NO persistence calls, NO mutation, NO imports from `app.persistence` / `app.services` / `app.waterfall` / `app.construction` / `app.debt` / `app.tax` / `app.depreciation` / `app.idc`. |
| A | `app/templates/partials/_feedback_capture_panel.html` | +60 | Jinja partial. Renders nothing if `feedback_template` is missing. Otherwise renders disclaimer + 6 ordered fields + short summary template. No JS, no Tailwind, no Alpine, no inline script. No new HTMX endpoints. |
| A | `tests/test_phase25c3_feedback_capture_helpers.py` | +400 | 62 helper unit tests pinning: field vocabulary, is_supported_field, is_short_line, short template, exploratory disclaimer (mentions humans, secrets, PII, not-a-support-channel), build_feedback_template, no forbidden imports, no feature flag enablement, no fake ticket IDs / run IDs / validation, no PII capture, field help text. |
| A | `tests/test_phase25c3_feedback_capture_factory_safety.py` | +390 | 24 factory safety tests pinning: determinism, no forbidden imports, partial: no JS / no Alpine / no HTMX, partial: renders nothing when context missing, partial: renders 6 fields + 3 short lines, rc1 frozen, no schema changes, no DB writes, no ticket IDs, no PII capture, factory projects safe. |
| A | `docs/phase25c3_pilot_feedback_capture.md` | this file | 8-section design + change doc. |
| A | `reports/phase25c3_pilot_feedback_capture.json` | +40 | Machine-readable summary. |

**ZERO changes to**:
- `app/persistence/`
- `app/services/`
- `app/waterfall_core.py`
- `app/waterfall_runner.py`
- `app/construction/`, `app/debt/`, `app/tax/`, `app/depreciation/`, `app/idc/`
- `static/app.js`, `static/styles.css`
- `main_web.py`, `main_api.py`, `domain/`
- `app/excel_export.py`

## 6. Self-review findings

- The 6 fields are stable; the test `test_field_order_count` pins the count at 6.
- The 3-line short template is exposed via `SHORT_TEMPLATE_LINES` (frozen tuple); the test `test_short_template_count` pins the count at 3.
- The exploratory disclaimer mentions "humans", "secrets", "PII", and "not a support channel". The test `test_disclaimer_*` enforces all four.
- The helper does not import any forbidden module. The test `test_forbidden_module_not_imported` is parametrized over 8 forbidden modules.
- The helper does not generate ticket IDs / issue IDs / feedback IDs. The test `test_helper_does_not_invent_ticket_ids` enforces this.
- The helper does not capture PII. The test `test_helper_does_not_capture_pii` enforces this.
- The partial has no JS, no Tailwind, no Alpine, no inline script. The tests `test_partial_no_script_tag`, `test_partial_no_alpine`, `test_partial_no_htmx` enforce this.

## 7. Pre-merge audit (all green)

- **Scope**: UI only. No backend change. No autosave. No DB writes.
- **Forbidden paths**: zero changes (all forbidden-paths tests pass)
- **Feature flags**: none enabled (`use_construction_schedule_engine=False`)
- **Schema**: zero migrations
- **rc1 SHA**: `b425a0708719eaa5e1d922b1008e5609758e0ad4` verified untouched
- **Tests**: 62 helper tests + 24 factory safety tests = **86/86 new tests PASS**
- **No regressions**: 25B Closure 30/30 + 51F 21/21 + route smoke 50/17 = **166 passed / 38 skipped** in the focused run
- **Factory safety**: TUHO / Oborovo inputs unchanged; helper is a pure read-side classifier

## 8. Hard no-go (15 items, all verified pre-push)

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

**Plus 25C-3-specific no-go**:
- no_db_writes
- no_ticket_id_generation
- no_pii_capture

## 9. Stop-after-report contract

This PR is DRAFT. Do NOT mark ready. Do NOT merge. Do NOT start any further work before review and explicit go-ahead. After approval, the recommended next step is **Phase 25C Closure — Third-Party Test Readiness Gate** as a separate DRAFT PR.
