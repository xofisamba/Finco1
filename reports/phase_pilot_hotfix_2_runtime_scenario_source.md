# Phase PILOT-HOTFIX-2 — Runtime honours scenario overrides

> **Status:** DRAFT (not yet merged)
> **Branch:** `phase/pilot-hotfix-2-runtime-scenario-source`
> **Base:** main @ `8758d3e0c6e447a76386190cc3ed99dd55cd2229` (post-S1-C)
> **Date:** 2026-06-17

---

## 1. TL;DR

The post-S1-C pilot walkthrough surfaced a **P0 blocker**: when a user
creates a Downside scenario with a tariff override, saves it via
`/scenarios/save`, and then runs `/run`, the runtime result reflects
the **Base** scenario's values, not the override. The pilot walkthrough
recorded this in section "P0 #1: Runtime ignores scenario overrides" of
its walkthrough report.

This PR implements a small, contained fix in
`app/services/run_service.execute_run_route`: a new **Section 2b** that
auto-selects the form's `scenario_id` (if the workspace's
`active_scenario_id` is stale) and synchronises the `saved_snapshot` to
the form snapshot so the runtime guard accepts the boundary with
`runtime_origin="saved_state"`. With this, the runtime resolver
correctly reads the active scenario's resolved snapshot (base +
overrides) and the override flows through.

11 new tests + 582/582 relevant tests pass; 8 pre-existing failures +
12 pre-existing errors are out of scope and were present on
`origin/main` before this PR.

---

## 2. Constraints honoured

- ✅ rc1 frozen SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4`
- ✅ `app/waterfall_core.py` MD5 `6bf49f33efc989736c17cea0cb9b7723`
- ✅ `app/project_factories.py` MD5 `cf73065b8a26aa3f19629829e46260d9`
  (post-S1-C)
- ✅ `app/persistence/repository.py` **unchanged** (P1 file-scope
  constraint)
- ✅ No persistence schema change
- ✅ No financial formula / IDC / debt / tax / sponsor / construction /
  R99 / R102 / G20 / waterfall change
- ✅ No factory change
- ✅ No static / template / route change
- ✅ TUHO / Oborovo frozen-schedule parity preserved bit-identical

---

## 3. Files changed

| File | Status | Lines | Purpose |
|---|---|---|---|
| `app/services/run_service.py` | M | +110 / -0 | Section 2b auto-select + saved-snapshot sync |
| `tests/test_phase_pilot_hotfix_2_runtime_scenario_source.py` | A | +892 / -0 | 11 tests across 7 test classes |
| `docs/phase_pilot_hotfix_2_runtime_scenario_source.md` | A | +250 / -0 | Design + validation doc |
| `reports/phase_pilot_hotfix_2_runtime_scenario_source.md` | A | this file | Walkthrough + results |

Total: **2 source files** (1 modified, 1 added) + **2 doc files**.

---

## 4. Live walkthrough (post-fix, on this branch)

A new working copy of TUHO Wind 1 was created. The form was submitted
with the Base scenario (tariff 75), then with a Downside scenario
(override tariff 50).

| Project | Scenario | Tariff | `project_irr` | `total_revenue` | `avg_dscr` |
|---|---|---|---|---|---|
| TUHO Wind 1 (Copy) | Base | 75 | **7.33%** | **323,640 kEUR** | **1.51x** |
| TUHO Wind 1 (Copy) | Downside | 50 (override) | **6.24%** | **304,085 kEUR** | **1.53x** |
| **Delta** | | | **−1.09 pp** | **−19,555 kEUR** | **+0.02x** |

The override now flows through the runtime path correctly. The
`workspace_state.active_scenario_id` is updated to the Downside
scenario's id after `/run`, and `last_runtime_origin` is
`saved_state` (not `None`).

### 4.1 Pre-fix reproduction (for contrast)

Same walkthrough before the fix produced:

| Project | Scenario | Tariff | `project_irr` | `total_revenue` |
|---|---|---|---|---|
| TUHO Wind 1 (Copy) | Base | 75 | 7.33% | 323,640 kEUR |
| TUHO Wind 1 (Copy) | Downside | 50 (override) | **7.33%** | **323,640 kEUR** |
| **Delta** | | | **0 pp** | **0 kEUR** |

The runtime was ignoring the form's `scenario_id` because the
workspace's `active_scenario_id` was still the Base scenario's id from
the previous run.

---

## 5. Test coverage

11 new tests in
`tests/test_phase_pilot_hotfix_2_runtime_scenario_source.py`:

| Test class | Tests | Purpose |
|---|---|---|
| `TestBaseVsDownsideRunDifferentResults` | 1 | Base then Downside produce different results; Downside has lower revenue/IRR |
| `TestLastRuntimeSnapshotUpdated` | 1 | `last_runtime_snapshot_json` carries override tariff (50) after Downside run |
| `TestTuhoOborovoParityPreserved` | 2 | TUHO/Oborovo debt values unchanged |
| `TestEngineMD5Unchanged` | 2 | Engine MD5 `6bf49f33...`; rc1 ancestor intact |
| `TestNoPersistenceSchemaChanges` | 1 | No new tables in `finco_runs.db` |
| `TestAutoSelectTriggerLogic` | 3 | Auto-select skips when already active, skips for factory, skips when no `scenario_id` in form |
| `TestScenarioOverrideFlowsIntoExport` | 1 | `last_runtime_summary` flows into export |

---

## 6. Pre-existing failures (NOT regressions of this PR)

8 pre-existing test failures + 12 pre-existing errors (mostly missing
`httpx2` dependency for `TestClient` fixtures) were present on
`origin/main` before this PR and are out of scope.

| Test | Status | Root cause |
|---|---|---|
| `test_phase25b4_dirty_state_helpers.py::TestScenarioDirtyIndicator::test_factory_project_never_dirty` | FAIL | pre-existing |
| `test_phase25b4_dirty_state_helpers.py::TestChangesNotSavedNotice::test_factory_project_returns_factory_notice` | FAIL | pre-existing |
| `test_phase25b4_dirty_state_helpers.py::TestChangesNotSavedNotice::test_factory_clean_returns_factory_notice` | FAIL | pre-existing |
| `test_phase25b4_dirty_state_helpers.py::TestBuildDirtyStateUi::test_factory_project` | FAIL | pre-existing |
| `test_phase25b4_factory_safety.py::TestFactoryNoticeReadOnly::test_factory_notice_does_not_say_unsaved` | FAIL | pre-existing |
| `test_phase25b6_review_template.py::TestClassificationRendering::test_factory_template_classification_renders` | FAIL | pre-existing |
| `test_phase25b6_review_template.py::TestExploratoryAndExclusionsRendering::test_exploratory_limitations_rendered_for_generic` | FAIL | pre-existing |
| `test_phase25b6_review_template.py::TestExploratoryAndExclusionsRendering::test_exploratory_limitations_rendered_for_factory` | FAIL | pre-existing |
| Various `TestClient`-based tests (12 errors) | ERROR | pre-existing, missing `httpx2` dependency |

---

## 7. Stop-after-report contract

This PR is the **runtime-source fix** for P0 #1 (runtime ignores
scenario overrides). Do **NOT** mark ready, do **NOT** merge before
review. P0 #2 (exact-match run gate) and the two P1 issues are
explicitly **out of scope** for this PR.
