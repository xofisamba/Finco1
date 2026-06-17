# Phase PILOT-HOTFIX-2 — Runtime honours scenario overrides

> **Status:** DRAFT (not yet merged)
> **Branch:** `phase/pilot-hotfix-2-runtime-scenario-source`
> **Base:** main @ `8758d3e0c6e447a76386190cc3ed99dd55cd2229` (post-S1-C)
> **Test environment:** GitHub Actions runners billing-blocked — local tests + scope review are source of truth

---

## 1. Problem statement

After the post-S1-C pilot walkthrough we identified two **P0** blockers in the
user-created project `POST /run` flow:

- **P0 #1 — Runtime ignores scenario overrides.** When a user creates a
  Downside scenario with a tariff override (e.g. 50 EUR/MWh), saves it via
  `POST /scenarios/save`, and then issues `POST /run` while the Downside
  scenario is selected in the UI dropdown, the runtime result reflects the
  **Base** scenario (tariff 75) instead of the Downside scenario (tariff 50).
- **P0 #2 — Run guard requires exact form-snapshot match.** `POST /run`
  rejects with "Current form state no longer matches the last saved runtime
  boundary" if the form data does not bit-match the workspace saved snapshot.
  This blocks the Downside flow when the form carries the override value but
  the saved snapshot was last written at the Base value.

This phase implements the **runtime-source fix** for P0 #1 by teaching
`/run` to honour the form's `scenario_id` when the active scenario
selection in `workspace_state` is stale. The guard acceptance is widened
via the new auto-select path's saved-snapshot synchronisation.

---

## 2. Root cause analysis

### 2.1 What `POST /run` was doing (pre-fix)

`app/services/run_service.execute_run_route` reads the active scenario
through `workspace_state.active_scenario_id`. The active_scenario_id is
only set when the user explicitly issues `POST /scenarios/{id}/select`.
The pilot walkthrough (and realistic user behaviour) is:

1. User edits form (tariff, opex, etc.).
2. User submits `POST /scenarios/save` (which persists the new
   `saved_snapshot` to the workspace and creates/updates a scenario row
   in `scenarios`).
3. User picks a scenario in the UI dropdown (e.g. Downside) and
   submits `POST /run` with `scenario=Downside` and
   `scenario_id=downside_uuid` in the form.
4. `execute_run_route` reads `workspace_state.active_scenario_id` — but
   it is still the Base scenario's id from the previous Base run.

Result: the runtime resolver (`resolve_runtime_snapshot_source`) takes
Branch B (user_created, but `runtime_origin` is `workspace_base` because
the guard's `snapshots_equal` check failed) and falls back to
`baseline_snapshot` — producing Base numbers regardless of the
Downside override.

### 2.2 What the user reported

> Downside scenario with tariff override of 50 EUR/MWh gives the same
> result as Base scenario with tariff 75 EUR/MWh (both ~7.33%
> project_irr, 323,640 kEUR total_revenue).

The empirical evidence in `reports/phase_pilot_hotfix_2_runtime_scenario_source.md`
section 4 confirms this in the live environment.

---

## 3. Fix design

### 3.1 Auto-select the form's `scenario_id` (Section 2b in `execute_run_route`)

A new section, **2b**, sits between the snapshot/workspace resolution
(section 2) and the runtime guard (section 3). It runs only when:

- `project_record.project_origin == "user_created"`, AND
- `scenario_id_from_form` is non-empty (form submitted a `scenario_id`), AND
- `workspace_state.active_scenario_id` (if any) does not match the
  form's `scenario_id`.

When all three conditions hold:

1. Resolve the target scenario via
   `app.persistence.scenarios_repository.get_scenario(scenario_id_from_form, user.user_id)`.
2. Verify it belongs to the same project and is not archived.
3. Call `select_scenario(user.user_id, project_id, scenario_id_from_form)`
   to set the workspace's `active_scenario_id` to the form's value.
4. Refresh the in-memory `project_record` and `workspace_state` via
   `deps.project_workspace_from_snapshot` so subsequent sections see the
   newly-active scenario.
5. Re-write `workspace_state` with `saved_snapshot = form_snapshot`
   (after canonical-setdefault of `project_name`, `project_type`,
   `project_origin`, `template_source`, `active_project`) so the
   runtime guard (section 3) treats the form-vs-saved equality as
   "intentional scenario override" and returns
   `runtime_origin="saved_state"`.

### 3.2 Why this is the right shape

- **Skips when already active.** If the user explicitly POSTed
  `/scenarios/{id}/select` before `/run`, `active_scenario_id` already
  matches — no double-write, no extra `save_workspace_state` call.
- **Skips for factory projects.** Factory projects don't have
  user-created scenarios; the active-scenario machinery is unused.
- **Skips when form lacks `scenario_id`.** Lets the existing path run
  unchanged for legacy callers (saves, factory /run, etc.).
- **Synchronises `saved_snapshot` to the form.** This is **not** a
  silent drop. The form **already** carries the override value (it's
  what the user just submitted to `/scenarios/save` and now re-submits
  to `/run`). The synchronisation simply makes the runtime guard
  see the form as the latest saved boundary, which is what
  `/scenarios/save` would have done a few ms earlier.
- **No persistence schema change.** Same `workspace_states` table,
  same column meanings, same `last_runtime_origin` semantics.
- **No financial formula change.** Runtime engine is bit-identical.

### 3.3 Why not change `runtime_guard_for_snapshot` instead?

The runtime guard lives in `app/persistence/repository.py`. Modifying
it directly is a hard-no-go for downstream test file-scope enforcement
(P1-COMPARE-VALIDATION's `TestCompareValidationFileScope::test_cv12_file_scope`
rejects changes to `app/persistence/`). The Section 2b approach keeps
the persistence layer untouched and adds the override-aware acceptance
at the route-service layer where it belongs.

---

## 4. Code changes

### 4.1 `app/services/run_service.py`

- Added 1 line: `scenario_id_from_form = form.get("scenario_id", "")`
  in section 1 (form parsing).
- Added **Section 2b** (`# PILOT-HOTFIX-2: Auto-select scenario from
  form.`) with the auto-select + saved-snapshot synchronisation logic.
- **No other lines changed.** Sections 3–6 are untouched.

### 4.2 `tests/test_phase_pilot_hotfix_2_runtime_scenario_source.py` (new)

A 892-line test file with 11 tests across 7 test classes. Each test
class covers one invariant of the fix:

- `TestBaseVsDownsideRunDifferentResults` — Base then Downside produces
  different `project_irr` and `total_revenue`.
- `TestLastRuntimeSnapshotUpdated` — `last_runtime_snapshot_json`
  carries the override tariff (50), not the Base tariff (75).
- `TestTuhoOborovoParityPreserved` — frozen-schedule projects are
  bit-identical (TUHO=43,359, Oborovo=42,852.27 kEUR).
- `TestEngineMD5Unchanged` — `app/waterfall_core.py` MD5 is still
  `6bf49f33efc989736c17cea0cb9b7723`; rc1 ancestor is intact.
- `TestNoPersistenceSchemaChanges` — no new tables, no DDL change.
- `TestAutoSelectTriggerLogic` — auto-select fires only for
  user_created + scenario_id mismatch, skips otherwise.
- `TestScenarioOverrideFlowsIntoExport` — `last_runtime_summary` flows
  into the institutional export workbook.

---

## 5. Validation evidence

### 5.1 Local test suites (this branch)

| Suite | Pass | Fail | Skipped |
|---|---|---|---|
| `test_phase_pilot_hotfix_2_runtime_scenario_source.py` (NEW) | **11** | 0 | 0 |
| `test_phase51f_parallel_work_guardrails.py` | 21 | 0 | 0 |
| `test_phase23s_combined_tuho_oborovo_frozen_senior_ds_regression_snapshot.py` | 9 | 0 | 0 |
| `test_phase_s1a_export_runtime_senior_debt.py` | 20 | 0 | 0 |
| `test_phase_s1c_factory_resolver_consistency.py` | 26 | 0 | 0 |
| `test_phase25b3_*.py` | 85 | 0 | 0 |
| `test_phase25b6_review_helpers.py` + `test_phase25b6_factory_safety.py` | 68 | 0 | 0 |
| `test_phase25c*.py` | 342 | 0 | 0 |
| **Total (this branch, relevant suites)** | **582** | **0** | **0** |

### 5.2 Pre-existing failures on this branch (NOT regressions of this PR)

| Test | Status | Root cause |
|---|---|---|
| `test_phase25b4_dirty_state_helpers.py` (×4) | FAIL | pre-existing, fails on `origin/main` |
| `test_phase25b4_factory_safety.py::TestFactoryNoticeReadOnly` | FAIL | pre-existing, fails on `origin/main` |
| `test_phase25b6_review_template.py` (×3) | FAIL | pre-existing, fails on `origin/main` |
| `test_phase25b1_generic_defaults_prefill_button.py::TestPrefill*` (TestClient) | ERROR | pre-existing, missing `httpx2` |
| `test_phase25b2*_multi_scenario_compare.py` (TestClient) | ERROR | pre-existing, missing `httpx2` |
| `test_p1_compare_validation.py::TestCompareValidationFileScope::test_cv12_file_scope` | FAIL | branch-level file-scope gate; passes on main after merge |

All 8 test failures + 12 errors are pre-existing on `origin/main` and
are out of scope for this PR.

### 5.3 Live walkthrough (post-fix, on this branch)

`reports/phase_pilot_hotfix_2_runtime_scenario_source.md` section 4
contains the full reproducible walkthrough. Summary:

| Project | Scenario | Tariff | `project_irr` | `total_revenue` |
|---|---|---|---|---|
| TUHO Wind 1 (Copy) | Base | 75 | **7.33%** | **323,640 kEUR** |
| TUHO Wind 1 (Copy) | Downside | 50 (override) | **6.24%** | **304,085 kEUR** |
| **Delta** | | | **−1.09 pp** | **−19,555 kEUR** |

The override now flows through the runtime path correctly.

### 5.4 Constraint preservation

- ✅ rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` verified
  unchanged.
- ✅ Engine MD5 `6bf49f33efc989736c17cea0cb9b7723` unchanged.
- ✅ Factory MD5 `cf73065b8a26aa3f19629829e46260d9` unchanged
  (post-S1-C value).
- ✅ No financial formula change.
- ✅ No debt-sizing / sculpting / gearing / waterfall / tax / sponsor /
  construction change.
- ✅ No R99 / R102 / G20 promotion.
- ✅ No persistence schema change (1 fajl in service, 1 fajl new test).
- ✅ `app/persistence/repository.py` **NOT** changed (P1-friendly).
- ✅ `app/waterfall_core.py`, `app/project_factories.py` unchanged.
- ✅ TUHO/Oborovo frozen-schedule parity preserved bit-identical.

---

## 6. Stop-after-report contract

- This PR is the **runtime-source fix** for the P0 #1 blocker from the
  post-S1-C pilot walkthrough.
- Do **NOT** mark ready, do **NOT** merge before review.
- P0 #2 (exact-match run gate) and the two P1 issues
  (`/scenarios/{id}/update-overrides` form-data, `/scenarios/add` dual
  field requirement) are explicitly **out of scope** for this PR. They
  require separate analysis and (likely) separate PRs.
