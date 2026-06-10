# Phase 25B-4 — Dirty State + Save Clarity

**Type**: UI only. **No** autosave. **No** backend change. **No**
feature flag enablement. **No** schema change. **No** model
formula change.

**Status**: DRAFT PR. **Do NOT mark ready.** Do NOT merge. Do NOT
start any further runtime work before review and explicit
go-ahead.

**Base**: `361b4fad63119a7183d9071b7ee0fa0035d5ffc9` (post-25B-3
+ Agent B pilot consolidation).

**Branch**: `phase25b4-dirty-state-save-clarity`

## 1. Goal

A finance user always knows the save / run state of the
active scenario:

- **Saved** — clean, latest run reflects the current saved state
- **Unsaved edits** — draft has changes not yet saved
- **Stale — rerun** — saved snapshot is older than the last run
- **Rerun recommended** — draft has unsaved changes AND a prior
  run exists; outputs reflect a previous state, not the current
  draft
- **Unsaved** — no saved scenario and no prior run

## 2. Scope

**In scope**:
- New pure read-side helper module `app/ui/dirty_state.py`
- New Jinja partial `app/templates/partials/_dirty_state_badge.html`
- 4-state machine + 1 fallback (`unknown`) + 1 edge (`unsaved`)
- Read-only classification of `workspace_state` +
  `runtime_summary` + optional save context

**Out of scope (do NOT touch)**:
- Autosave
- Persistence schema
- Feature flag enablement
- Construction / C10 / R-PAR
- Tax / debt / depreciation / IDC
- TUHO / Oborovo reference path (factory must remain SAFE)
- Run / save / scenario persistence services
- Model formulas
- Runtime authority

## 3. State machine

| State | When | Tone | Rerun? | Unsaved? |
|---|---|---|---|---|
| `saved` | clean + save record | `pass` | No | No |
| `dirty` | dirty + save record + no prior run | `dirty` | No | Yes |
| `unsaved` | dirty + no save record + no prior run | `dirty` | No | Yes |
| `needs_rerun` | dirty + prior run | `warn` | Yes | Yes |
| `stale` | reserved for future timestamp-aware logic | `warn` | Yes | No |
| `unknown` | workspace_state is None | `none` | No | No |

## 4. Changed files (4 files, +1241 / -0)

| Status | File | Lines |
|---|---|---|
| A | `app/ui/dirty_state.py` | +340 |
| A | `app/templates/partials/_dirty_state_badge.html` | +72 |
| A | `tests/test_phase25b4_dirty_state_helpers.py` | +400 |
| A | `tests/test_phase25b4_dirty_state_template.py` | +200 |
| A | `tests/test_phase25b4_factory_safety.py` | +220 |
| A | `docs/phase25b4_dirty_state_save_clarity.md` | this file |
| A | `reports/phase25b4_dirty_state_save_clarity.json` | summary |

**ZERO changes to**:
- `app/persistence/`
- `app/services/`
- `app/waterfall_core.py`
- `app/waterfall_runner.py`
- `app/construction/`
- `app/debt/`, `app/tax/`, `app/depreciation/`
- `static/app.js`, `static/styles.css`
- `main_web.py`, `main_api.py`, `domain/`
- `app/excel_export.py`

## 5. Self-review findings

- Initial draft proposed auto-wiring the partial into
  `app/templates/index.html`. **Mitigation**: the partial is
  intentionally not wired into `index.html` in this phase.
  The helper is exported and the partial is in place, but
  the wiring step is deferred to a future phase that has
  explicit go-ahead for live UI integration. This phase
  ships the building blocks only.
- The `stale` state is reserved for future timestamp-aware
  logic (e.g. comparing `last_saved_at` vs `last_run_at`).
  In this phase, the conservative classifier treats
  `clean + prior run + save record` as `saved` and never
  invents a `stale` classification.
- The helper is exposed as a pure function with no side
  effects, so it is safe to call from any context (partial
  wiring, future JS, future tests, future API).

## 6. Pre-merge audit

- **Scope**: UI only. No backend change. No autosave.
- **Forbidden paths**: zero changes (all forbidden-paths tests pass)
- **Feature flags**: none enabled (`use_construction_schedule_engine=False`)
- **Schema**: zero migrations
- **rc1 SHA**: `b425a0708719eaa5e1d922b1008e5609758e0ad4` verified untouched
- **Tests**: 25B-4 helper tests + 25B-4 template tests + 25B-4 factory safety tests + 25B-3 (no regression) + D-series (no regression)
- **Factory safety**: TUHO / Oborovo inputs unchanged; helper is a pure read-side classifier

## 7. Hard no-go (15 items)

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

## 8. Stop-after-report contract

This PR is DRAFT. Do NOT mark ready. Do NOT merge. Do NOT start
any further work before review and explicit go-ahead.
