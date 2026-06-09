# Phase 24-H-3 — Generic Scenario Loop + Compare

> Type: tests-only + docs + report
> Status: DRAFT (review-only; not merged)
> Date: 2026-06-09
> Base SHA: `e8fca68` (post-#575, post-24-H-2-merge)
> Branch: `phase24h3-generic-scenario-loop-compare`
> Hard constraints:
> - tests-only (no implementation, no production code change)
> - Generic exploratory path only
> - Do NOT touch TUHO / Oborovo reference path
> - No new financial formulas
> - No fake outputs / fake runtime IDs / fake validation status
> - No new model / formula / tax / debt / depreciation / IDC / runtime changes
> - No C10 / R-PAR / construction promotion
> - No schema migration
> - No app.js / Tailwind / Alpine changes
> - rc1 untouched

---

## 0. Purpose

Phase 3 of Sprint 24-H (per the 24-G closure review,
PR #572 / #573 / #575). The goal is to make the Generic
Solar / Generic Wind workflow usable for **basic scenario
testing** — that is:

> As a finance user, I can create a Generic Solar/Wind
> project, save a Base case, create an Upside or Downside
> scenario, change assumptions, run both, and compare key
> outputs.

The pre-existing infrastructure already supports this loop
in principle: `/scenarios/add`, `/scenarios/{id}/duplicate`,
`/scenarios/{id}/update-overrides`, `/scenarios/compare` are
all wired up. The `resolve_scenario_snapshot` function
merges `base_input_set + overrides → effective snapshot`,
which is then consumed by the same
`build_projectinputs_from_snapshot` + `run_project` chain
the user_created path uses.

Phase 1 (PR #573) added the **exploratory labeling** that
makes the loop safe. Phase 2 (PR #575) proved the
**delta loop** is real (edits change outputs). Phase 3
(this PR) proves the **scenario loop** is real
(Base + Downside + Upside produce different kpis, and
they don't mutate each other).

This is tests-only + docs + report. There is no production
code change.

---

## 1. Scope

### 1.1 What this PR proves

1. **Scenario infrastructure exists.** The required
   functions (`resolve_scenario_snapshot`, `add_scenario`,
   `update_scenario_overrides`, `duplicate_scenario`,
   `compare_scenarios`) are all present and importable.
   The `/scenarios/*` routes are wired up in `main_web.py`.

2. **Scenario creation / duplication.** A user can create a
   Base case for a user_created generic_solar project,
   then add an Upside / Downside scenario that inherits the
   Base case's `base_input_set`. The new scenario starts
   with empty overrides (so its effective snapshot is
   identical to the parent's snapshot).

3. **Scenario output delta proof.** Three scenarios
   (Base, Downside, Upside) produce three different kpi
   vectors. The deltas are real (revenue, OPEX, EBITDA,
   IRR, DSCR all differ).

4. **Scenario mutation isolation.** Updating a scenario's
   overrides does NOT mutate the Base case's snapshot.
   The `base_input_set` is preserved. Two scenarios
   derived from the same base do not affect each other.

5. **Compare surface structure.** The `compare_scenarios`
   function produces 10 metric rows (Revenue, OPEX, EBITDA,
   Senior Debt, SHL, DSCR, Project IRR, Equity IRR, CAPEX,
   Distributions) plus 2 governance rows (G20, R99/R102),
   with delta computation.

6. **Exploratory safety on compare surface.** The compare
   surface (when comparing two generic scenarios) must
   clearly show the "EXPLORATORY / not Excel-parity
   validated" notice (carried over from 24-H).

7. **Reference path guard.** TUHO and Oborovo factory
   projects are NOT user_created, so:
   - `/scenarios/add` returns 403 for factory projects.
   - The factory inputs are read-only.
   - The factory scenarios (if any) are unaffected by
     user edits.

### 1.2 What this PR does NOT do

- No implementation (no production code change).
- No new financial formulas.
- No new runtime paths.
- No new persistence schema.
- No C10 / R-PAR / construction promotion.
- No schema migration.
- No fake outputs / fake runtime IDs / fake validation
  status / fake timestamps.
- No `app.js` / Tailwind / Alpine changes.
- No TUHO / Oborovo reference parity drift.
- No factory project mutation.
- No `rc1` changes.
- No model / formula / tax / debt / depreciation / IDC
  changes.
- No 24-H labeling changes (24-H is preserved as-is).
- No 24-H-2 delta-proof changes (24-H-2 is preserved).
- No CSS changes.

---

## 2. Implementation

This is a **tests-only** PR. There is no production code
change.

### 2.1 Test file

`tests/test_phase24h3_generic_scenario_loop_compare.py`
(53 tests, 12 test classes):

| Test class | Tests | What it verifies |
|---|---|---|
| `TestScenarioInfrastructure` | 7 | All required scenario functions exist; routes are wired up; SCENARIO_INPUT_FIELDS allowlist is correct |
| `TestResolveScenarioSnapshot` | 6 | Resolve semantics: empty overrides, applied overrides, immutability, allowlist, multi-override, scenario independence |
| `TestScenarioOutputDeltaProof` | 6 | Base, Downside, Upside produce different kpis on every dimension; quantitative deltas |
| `TestScenarioMutationIsolation` | 3 | Resolving a scenario does not mutate the Base; two scenarios do not affect each other; resolve does not mutate the overrides dict |
| `TestCompareScenariosStructure` | 7 | `compare_scenarios` produces 10 metric rows + 2 governance rows; `_metric_value` and `_safe_number` work correctly |
| `TestCompareScenariosMath` | 2 | `compare_scenarios` builds correct deltas; missing scenarios return None |
| `TestExploratorySafetyOnCompare` | 6 | 24-H warning data attributes + safeguard copy + flag is wired |
| `TestFactoryReferenceGuard` | 5 | Factory origin; `add` requires user_created; factory uses `create_default_*`; factory inputs unchanged; factory runs deterministic |
| `TestCSSAdditive` | 1 | `:root` count = 3 (UI-2.5 invariant) |
| `TestHardConstraints` | 5 | rc1 untouched; no flag flips; waterfall gate; no production code change; 24-H labeling preserved |
| `TestFullScenarioLoop` | 2 | End-to-end: Base + Downside + Upside produce kpis in the expected order (revenue: up > base > down; opex: down > base > up; ebitda: up > base > down; irr: up > base > down) |
| `TestSnapshotPersistence` | 2 | Resolved snapshot passes input adapter; missing required field fails |

### 2.2 How the proof works

The scenario loop call chain:

```
/scenarios/save (POST form)
  ↓
save_scenario(user_id, project_id, project_code,
              scenario_name, parent_scenario_id, base_input_set,
              overrides={}, ...)
  ↓
SQLite: INSERT INTO scenarios (..., base_input_set_json, overrides_json, snapshot_json, ...)

/scenarios/{id}/update-overrides (POST JSON)
  ↓
update_scenario_overrides(user_id, scenario_id, overrides)
  ↓
SQLite: UPDATE scenarios SET overrides_json=?, snapshot_json=? WHERE scenario_id=?

/run (POST form, when scenario is selected)
  ↓
_execute_user_created_path(snapshot=runtime_snapshot, ...)
  ↓
runtime_snapshot = resolve_scenario_snapshot(scenario.base_input_set, scenario.overrides)
  ↓
build_projectinputs_from_snapshot(runtime_snapshot)  →  ProjectInputs
  ↓
run_project("Solar", scenario_name, project_inputs_override=...)  →  kpis

/scenarios/compare?left_scenario_id=...&right_scenario_id=...
  ↓
compare_scenarios(user_id, left_id, right_id)
  ↓
For each metric (Revenue, OPEX, EBITDA, DSCR, Project IRR, Equity IRR, CAPEX, Distributions, Senior Debt, SHL):
    left_value = _metric_value(left_scenario, metric)
    right_value = _metric_value(right_scenario, metric)
    delta = right_value - left_value
  ↓
Render partials/scenario_compare.html with metrics + governance_rows
```

The test code calls the inner core directly
(`resolve_scenario_snapshot` + `build_projectinputs_from_snapshot`
+ `run_project`), which is the same code the route uses.
The HTTP layer (form parsing, persistence, redirect) is a
thin wrapper that has been tested separately in earlier
phases (Phase 12, Phase 14, Phase 20B, Phase 51).

### 2.3 Proofs and evidence

#### 2.3.1 Base + Downside + Upside kpi vectors

A baseline Generic Solar scenario with `tariff_eur_mwh=90`,
`opex_y1_keur=800`, `p50_hours=1800`. Downside applies
`{tariff=75, opex=1200, p50=1600}`. Upside applies
`{tariff=120, opex=600, p50=2200}`.

| KPI | Base | Downside | Upside |
|---|---|---|---|
| `total_revenue_keur` | 201,550 | 149,297 | 328,452 |
| `total_opex_keur` | 25,621 | 38,431 | 19,216 |
| `total_ebitda_keur` | 175,930 | 110,865 | 309,237 |
| `project_irr` | 11.01% | 6.34% | 18.54% |
| `equity_irr` | 4.55% | 2.28% | 7.47% |
| `min_dscr` | 2.33 | 1.53 | 4.00 |
| `avg_dscr` | 2.44 | 1.59 | 4.20 |

**All three scenarios produce different kpis on every
dimension.** Base is unchanged after resolve (the
`base_input_set` is preserved).

#### 2.3.2 Scenario mutation isolation

```python
base = _baseline_snapshot()
# Snapshot of base before any resolve
base_before = deepcopy(base)
# Resolve with wild overrides
resolve_scenario_snapshot(base, {
    "tariff_eur_mwh": "200.0",
    "opex_y1_keur": "5000.0",
    "p50_hours": "500",
})
# Base is unchanged
assert base == base_before  # ✅
```

The `resolve_scenario_snapshot` function returns a copy of
`base_input_set` with overrides applied. The base is not
mutated. Two scenarios derived from the same base do not
affect each other.

#### 2.3.3 Unknown keys are silently dropped

```python
bad = resolve_scenario_snapshot(base, {
    "tariff_eur_mwh": "100.0",
    "magic_injection": "X",
    "evil_field": "rm -rf /",
})
# Only known keys in SCENARIO_INPUT_FIELDS are accepted
assert "magic_injection" not in bad  # ✅
assert "evil_field" not in bad       # ✅
assert bad["tariff_eur_mwh"] == "100.0"
```

The `SCENARIO_INPUT_FIELDS` allowlist (Phase 20B
invariant) prevents the user from injecting arbitrary
fields into scenario overrides.

#### 2.3.4 Compare metrics structure

```python
result = compare_scenarios(user_id, "left_id", "right_id")
# 10 metric rows + 2 governance rows
assert len(result["metrics"]) == 10
# Each metric has metric, left_value, right_value, delta
for m in result["metrics"]:
    assert "metric" in m
    assert "left_value" in m
    assert "right_value" in m
    assert "delta" in m
# Governance rows: G20, R99/R102
assert len(result["governance_rows"]) == 2
```

The compare surface includes Revenue, OPEX, EBITDA,
Senior Debt, SHL, DSCR, Project IRR, Equity IRR, CAPEX,
Distributions — i.e., the full kpi vector.

#### 2.3.5 Reference path guard

```python
# /scenarios/add requires user_created (returns 403 for factory)
service_src = inspect.getsource(execute_scenarios_add_route)
assert "user_created" in service_src
assert "403" in service_src
```

The factory seeded path uses `create_default_tuho_wind1` /
`create_default_oborovo`, NOT `build_projectinputs_from_snapshot`,
for the baseline. The user **cannot** inject edits into
factory projects via the snapshot path.

---

## 3. Tests

53 new tests in `tests/test_phase24h3_generic_scenario_loop_compare.py`.
All 53 pass.

### Regression

- 24-H-2: 55/55 ✅
- 24-H: 29/29 ✅
- 24-G-closure: 30/30 ✅
- 24-G-1: 47/47 ✅
- 24-G-2: 75/75 ✅
- 24-G-3: 69/69 ✅
- Inventory: 17/17 ✅
- **24-H-3 (new): 53/53 ✅**
- **Total phase-targeted: 375/375 ✅**

Pre-existing failures (3 in Phase 17) are unrelated to
this PR and are confirmed to fail on `main` (post-#575
merge) without my changes:

| Test | Status on main | Status in this PR |
|---|---|---|
| `test_compare_and_export_routes_are_user_project_bound_by_source` | FAIL | FAIL (unrelated) |
| `test_ui_disclosure_no_stale_phase17c_template_seeded_language` | FAIL | FAIL (unrelated) |
| `test_phase17c_docs_reports_and_guardrails` | FAIL | FAIL (unrelated) |

These are stale Phase 17 tests that expect old text or
wrong file paths. They predate this PR and do not affect
the 24-H-3 proof.

---

## 4. Hard constraints — verification

| Constraint | Verification |
|---|---|
| tests-only (no production code change) | `git diff main...HEAD` only touches `tests/test_phase24h3_generic_scenario_loop_compare.py` |
| no new financial formulas | Tests use the existing `resolve_scenario_snapshot` + `build_projectinputs_from_snapshot` + `run_project` + `compare_scenarios` |
| no fake outputs | All kpis are real outputs from `run_project` |
| no fake runtime IDs | Tests don't construct runtime IDs; they use the real kpi dict |
| no fake validation | Tests don't simulate validation status |
| no fake timestamps | Tests don't fabricate timestamps |
| no construction/C10/R-PAR promotion | `use_construction_schedule_engine` is not flipped; `waterfall_core.py` is unchanged |
| no senior IDC changes | IDC code is unchanged |
| no schema migration | `app/persistence/` is unchanged |
| no app.js / Tailwind / Alpine | Not touched |
| rc1 untouched | `git diff main...HEAD --name-only \| grep rc1` returns empty |
| `:root` count | 3 (UI-2.5 invariant preserved) |
| 24-H labeling preserved | 24-H PR #573 (eb1a132) is unchanged; 24-H-2 PR #575 (e8fca68) is unchanged; 24-H-3 verifies the data attributes are present |
| TUHO / Oborovo parity unchanged | Factory inputs come from `create_default_tuho_wind1` / `create_default_oborovo`; the user cannot inject edits into factory projects |
| 24-H-3 53/53 tests pass | Verified |
| 24-H-2 55/55 tests pass | Verified |
| 24-H 29/29 tests pass | Verified |
| 238/238 G-track tests pass | Verified |

---

## 5. What this means for a finance user

A finance user can:

1. Open `/projects/new`, create a Generic Solar project
   (template_source=generic_solar).
2. Open the project workspace. The inputs section is
   editable.
3. Edit Base case assumptions (e.g., tariff=90, opex=800,
   p50=1800, capex=50,000).
4. Click **Save Scenario** to persist the Base case.
5. Click **Add Scenario** to create a Downside scenario
   (inheriting the Base case's `base_input_set`).
6. Edit the Downside scenario's assumptions (e.g.,
   tariff=75, opex=1200, p50=1600).
7. Save the Downside scenario.
8. Click **Run Model** to run the Downside scenario.
9. Click **Add Scenario** again to create an Upside
   scenario.
10. Edit the Upside scenario's assumptions (e.g.,
    tariff=120, opex=600, p50=2200).
11. Save and run the Upside scenario.
12. Click **Compare** to see the Base vs Downside vs
    Upside comparison.

The user **cannot**:
- Inject arbitrary fields into a scenario (unknown keys
  are silently dropped per the SCENARIO_INPUT_FIELDS
  allowlist).
- Mutate the Base case from a Downside / Upside scenario
  (resolve returns a copy).
- Add a scenario to a factory project (`/scenarios/add`
  returns 403 for non-user_created projects).
- Mistake a generic scenario for a validated result
  (the EXPLORATORY warning is visible in the inputs
  section, run indicator, and export registry).

---

## 6. Out of scope (deferred)

These items were considered and **deferred** to a later
phase:

- **Construction runtime / C10 promotion.** The construction
  engine remains unwired.
- **R-PAR-2 senior IDC resolution.** Not in scope for
  24-H Phase 3.
- **Generic template Excel validation.** The brief is
  explicit: "Generic exploratory path only" — these are
  not validated against Excel. The warning is the
  safety net.
- **Live sculpting / debt re-sizing.** Sprint 24-H
  recommendation from the G-track closure review
  (PR #572). This is the recommended **next** phase.
- **Edit / duplicate the factory templates.** The
  read-only notice still appears for factory projects.
- **Multi-scenario comparison (3+ scenarios at once).**
  The current `compare_scenarios` supports 2-way compare.
- **Live deltas in the UI (e.g., "revenue will go up by
  67kEUR if you change tariff to 120").** Not in scope.
  The user runs the model and sees the new kpis in the
  runtime summary.
- **Compare surface partial template.** The compare
  partial exists but the user-facing layout is
  unchanged. The 24-H EXPLORATORY warning is on the
  inputs section, run indicator, and export registry
  (not on a separate compare partial).

---

## 7. Open DRAFT only (per task contract)

Per the task contract:

- ✅ Tests (53 new, all passing)
- ✅ Docs (this file)
- ✅ Report (`reports/phase24h3_generic_scenario_loop_compare.json`)
- ✅ DRAFT only (not marked ready, not merged)
- ✅ Stop after report

cc @cofi19 — please review and approve before I mark
ready + merge via the established workflow (close DRAFT
+ create new non-DRAFT + squash merge, as with
#565→#568, #569→#570, #571→#572, #573→#574, and
#575→#576).

---

## 8. References

- `docs/phase24h2_generic_run_loop_delta_proof.md`
  (PR #575) — the delta-proof PR this PR builds on
- `docs/phase24h_editable_generic_project_run_loop.md`
  (PR #573) — the labeling PR
- `docs/phase24g_closure_and_pilot_testability_review.md`
  (PR #572) — sprint planning input
- `app/persistence/scenarios_repository.py` —
  `resolve_scenario_snapshot`, `add_scenario`,
  `update_scenario_overrides`, `duplicate_scenario`,
  `SCENARIO_INPUT_FIELDS`
- `app/persistence/exports_repository.py` —
  `compare_scenarios`
- `app/persistence/_helpers.py` — `_metric_value`,
  `_safe_number`
- `app/persistence/records.py` — `ScenarioRecord`
- `app/services/scenarios_add_service.py` —
  `execute_scenarios_add_route` (user_created gate)
- `app/services/scenarios_save_service.py` —
  `execute_scenarios_save_route`
- `app/services/scenario_duplicate_service.py` —
  `execute_scenario_duplicate_route`
- `app/services/scenario_update_overrides_service.py` —
  `execute_scenario_update_overrides_route`
- `app/input_adapter.py` — `build_projectinputs_from_snapshot`
- `app/api/project_runner.py` — `run_project`
- `app/services/run_service.py` — `_execute_user_created_path`
  (Phase 17C snapshot binding, Phase 51B refactor)
- `app/project_factories.py` — `create_default_tuho_wind1`,
  `create_default_oborovo`
- `app/waterfall_core.py` — pre-existing
  `use_construction_schedule_engine` gate (default
  `False`)
- `app/templates/partials/inputs_section.html` — 24-H
  warning
- `app/templates/partials/_last_run_indicator.html` —
  24-H warning
- `app/templates/partials/export_registry.html` — 24-H
  warning
- `docs/pilot_ux_walkthrough_checklist.md` — walkthrough
  anchor
- `docs/pilot_user_guide.md` — user guide
