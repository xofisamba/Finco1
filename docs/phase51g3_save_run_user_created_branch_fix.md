# Phase 51G-3 — /save-run user_created branch latent bug fix

## Base SHA

`ecdb699716fc7bdce58f06358a96e8fe32a7cf44` (origin/main @ PR #391
merge, Phase 51G-2 /save-run vertical extraction)

## Objective

Fix the pre-existing latent bug
``_clean_user_project_runtime_snapshot`` that was referenced in
``app/services/save_run_service.py``'s user_created branch but
was never defined anywhere.

This is a **narrow bugfix**. No refactors, no behavior changes
elsewhere, no factory_template changes, no
save_run/save_project ordering changes, no replay_metadata
export_type changes, no parity-core file changes, no schema
changes, no JS changes, no financial formula changes.

## Bug description

The user_created branch in ``execute_save_run_route`` contained
this code (Phase 51G-1 / 51G-2):

```python
runtime_snapshot = _clean_user_project_runtime_snapshot(  # noqa: F821
    project_record, workspace_state, runtime_origin
)
```

The symbol ``_clean_user_project_runtime_snapshot`` was never
defined in the service, in ``main_web.py``, or anywhere else in
the codebase. The ``# noqa: F821`` comment suppressed the
linter warning, but at runtime the function was undefined.

When a user_created project hit the /save-run route, the broad
``except Exception as e:`` in the model-execution block caught
the resulting ``NameError`` and the user got back a
**200 + ``save_result-err``** with message:

```
Model error: name '_clean_user_project_runtime_snapshot' is not defined
```

This was a pre-existing bug, NOT introduced by Phase 51G-1
(characterization) or Phase 51G-2 (extraction).

## Why it was not fixed in 51G-2

User decision (verbatim):

> "51G-2 je extraction PR. Ako u istoj fazi i preselimo /save-run
> i popravljamo latentni bug, miješamo refaktor + behavior change.
> Bolje je: 51G-2: extract /save-run 1:1, uključujući postojeći
> latentni bug kao documented/pinned behavior. 51G-3: zaseban mali
> bugfix PR za user_created branch, s jasnim testom i sign-offom."

The fix is intentionally kept in a separate PR for cleaner
audit trail. Phase 51G-2 documented and pinned the bug. Phase
51G-3 fixes it.

## What changed now

### main_web.py

Added a thin adapter that delegates to the canonical Phase 50C-2
implementation:

```python
def _clean_user_project_runtime_snapshot(
    user, project_record, workspace_state, runtime_origin: str
) -> dict:
    """Return the clean backend-authored runtime snapshot for a
    user_created project used by the /save-run user_created branch.
    ...
    """
    snapshot, _scenario_record, _warning, _effective_origin = (
        _resolve_runtime_snapshot_source(
            user=user,
            project_record=project_record,
            workspace_state=workspace_state,
            runtime_origin=runtime_origin,
        )
    )
    return dict(snapshot or {})
```

This adapter:

- Reuses the existing ``_resolve_runtime_snapshot_source`` wrapper
  (which itself delegates to ``scenario_state_service.resolve_runtime_snapshot``,
  the Phase 50C-2 canonical implementation).
- Returns only the snapshot dict (the first element of the tuple),
  which is what ``build_projectinputs_from_snapshot`` consumes.
- Does not mutate state. Does not introduce new persistence side
  effects.

The new dep is wired into the /save-run route's
``SaveRunRouteDeps(...)`` construction:

```python
deps = SaveRunRouteDeps(
    project_workspace_from_snapshot=_project_workspace_from_snapshot,
    check_runtime_allowed=check_runtime_allowed,
    validate_form=_validate_form,
    project_types=PROJECT_TYPES,
    scenarios=SCENARIOS,
    clean_user_project_runtime_snapshot=_clean_user_project_runtime_snapshot,  # NEW
    canonical_project_type=_canonical_project_type,
    build_projectinputs_from_snapshot=build_projectinputs_from_snapshot,
    build_schema_from_form=_build_schema_from_form,
    ...
)
```

### app/services/save_run_service.py

Added a new field to ``SaveRunRouteDeps``:

```python
# User_created branch
# Phase 51G-3: clean_user_project_runtime_snapshot is now an
# explicit dep. ...
clean_user_project_runtime_snapshot: Callable[..., dict]
canonical_project_type: Callable[..., str]
build_projectinputs_from_snapshot: Callable[..., Any]
```

Replaced the bare, undefined module-level reference in
``execute_save_run_route`` with the deps-injected version:

```python
if project_record.project_origin == "user_created":
    # ── user_created branch ──────────────────────────────
    # Phase 51G-3 bugfix: previously this branch referenced
    # ``_clean_user_project_runtime_snapshot`` (a module-level
    # symbol that was never defined) and so failed with a
    # NameError on every save for user_created projects. ...
    runtime_snapshot = deps.clean_user_project_runtime_snapshot(
        user, project_record, workspace_state, runtime_origin
    )
    override = deps.build_projectinputs_from_snapshot(runtime_snapshot)
    runtime_project_key = (
        "Solar"
        if deps.canonical_project_type(effective_project_type) == "Solar"
        else "Wind"
    )
```

Updated the module docstring to reflect the fix (the 7
characterized quirks list no longer has a "preserved latent
bug" entry; quirk 1 is now resolved).

### tests

- **tests/test_phase51g1_save_run_route_golden_characterization.py**:
  Updated ``test_user_created_branch_has_latent_name_error``
  to assert the FIXED state: the function IS defined in
  main_web.py AND wired into SaveRunRouteDeps. The test
  name is preserved for regression history.

- **tests/test_phase51g2_save_run_route_vertical_extraction.py**:
  Renamed ``TestLatentBugNotFixed`` →
  ``TestLatentBugFixedIn51G3``. Updated
  ``test_quirk_1_user_created_branch_undefined_function_preserved``
  to assert the FIXED state: the service uses
  ``deps.clean_user_project_runtime_snapshot`` and the
  bare, undefined name is gone. The test name is preserved
  for regression history.

- **tests/test_phase51g3_save_run_user_created_branch_fix.py**
  (NEW): 53 tests pinning the fix, the regression history,
  the deps bundle update, the route remaining thin, the
  factory_template branch remaining unchanged, the
  save_run/save_project ordering remaining preserved, the
  forbidden side effects remaining absent, the
  no-service-imports-main_web/main_api invariant, the
  parity-core files remaining unchanged, and rc1 remaining
  untouched.

## Before / after behavior

### Before Phase 51G-3 (Phases 51G-1, 51G-2)

When a user_created project hits /save-run with valid form
data:

```text
1. POST /save-run
2. auth check passes (user is authenticated)
3. form is parsed, snapshot is collected
4. SaveRunRouteDeps is constructed (15 callables + 2 constants,
   no clean_user_project_runtime_snapshot dep)
5. execute_save_run_route is called
6. project_record is resolved
7. runtime guard is checked (3-tuple: allow_run,
   runtime_origin, guard_message) — allow_run=True
8. user_id = user.user_id
9. inputs dict is constructed from form (9 fields)
10. _validate_form returns True
11. project_record.project_origin == "user_created" branch
12. Code attempts to call _clean_user_project_runtime_snapshot(
       project_record, workspace_state, runtime_origin
    ) ← NameError (function not defined)
13. Broad except Exception catches the NameError
14. Returns SaveRunRouteOutcome(
        context={"success": False,
                 "error": "Model error: name "
                          "'_clean_user_project_runtime_snapshot' "
                          "is not defined"},
    )
15. Route renders partials/save_result.html with
    success=False and the error message
```

Result: **200 + save_result-err**, no save_run or
save_project call, no RunRecord, no ProjectRecord update.

### After Phase 51G-3

When a user_created project hits /save-run with valid form
data:

```text
1. POST /save-run
2. auth check passes (user is authenticated)
3. form is parsed, snapshot is collected
4. SaveRunRouteDeps is constructed (15 callables + 2 constants,
   WITH clean_user_project_runtime_snapshot dep wired to
   main_web._clean_user_project_runtime_snapshot)
5. execute_save_run_route is called
6. project_record is resolved
7. runtime guard is checked — allow_run=True
8. user_id = user.user_id
9. inputs dict is constructed from form (9 fields)
10. _validate_form returns True
11. project_record.project_origin == "user_created" branch
12. Code calls deps.clean_user_project_runtime_snapshot(
        user, project_record, workspace_state, runtime_origin
    ) ← defined, returns a clean snapshot dict
13. deps.build_projectinputs_from_snapshot(runtime_snapshot) is
    called with the clean snapshot
14. runtime_project_key is set to "Solar" or "Wind"
15. deps.run_project(runtime_project_key, scenario,
        project_inputs_override=override) is called
16. result["kpis"] is extracted
17. deps.save_run(user_id, project_type, scenario, inputs,
        kpis, replay_metadata) is called
    - replay_metadata.export_type = "saved_run_metadata"
    - runtime_timestamp = deps.utc_now_iso()
18. deps.save_project(user_id, project_code, project_name,
        source_project_template, governance_state,
        last_run_summary=kpis, replay_metadata) is called
    - replay_metadata.export_type = "saved_run_project_state"
    - replay_metadata.project_id = None
    - runtime_timestamp = run_record.created_at.isoformat()
19. Returns SaveRunRouteOutcome(
        context={"success": True, "run_id": ...,
                 "project_type": ..., "scenario": ...,
                 "created_at": ...},
    )
20. Route renders partials/save_result.html with success=True
```

Result: **200 + save_result-ok**, 1 RunRecord + 1
ProjectRecord update.

If the user_created project's baseline_snapshot is malformed
(missing required fields), step 13 raises
``SnapshotInputError`` from
``build_projectinputs_from_snapshot``. The broad
``except Exception`` (Behavior 12) still wraps the
model-execution block, and the service returns
**200 + save_result-err** with the message from
SnapshotInputError — not a NameError. This is a clean,
user-actionable error message, not an internal undefined-name
crash.

## Test evidence

| Suite | Result |
|---|---|
| `pytest tests/test_phase51g3_save_run_user_created_branch_fix.py` | **53 passed**, 0 failed |
| `pytest tests/test_phase51g1_save_run_route_golden_characterization.py` | **59 passed**, 0 failed |
| `pytest tests/test_phase51g2_save_run_route_vertical_extraction.py` | **63 passed**, 0 failed |
| `pytest tests/test_phase51f_parallel_work_guardrails.py` | **21 passed**, 0 failed |
| `pytest tests/test_phase51*.py` | **549 passed**, 0 failed, 0 xfail |

The 51G-3 suite covers:
- Bug history (4 tests)
- user_created branch reaches persistence (5 tests)
- factory_template branch unchanged (2 tests)
- save_run / save_project ordering (2 tests)
- Intended persistence side effects (5 tests)
- Forbidden side effects absent (parametrized, 6 + 1 + 1 tests)
- Route remains thin (2 tests)
- No service imports main_web / main_api (4 tests)
- Deps bundle updated (3 tests)
- Phase 51F guardrails smoke check (2 tests)
- Required behavior after fix (10 tests)
- Regression pin for historical bug (3 tests)
- Service sanity smoke (3 tests)

## Guardrail status (Phase 51F)

| Guardrail | Status |
|---|---|
| Engine-output golden (TUHO + Oborovo) | ✅ PASS — all 5+5 golden values still match (not touched) |
| Parity-core lock (4 SHA-256 files) | ✅ PASS — all 4 files unchanged (SHA verified) |
| No-service-imports-main_web/main_api | ✅ PASS — save_run_service.py still does NOT import main_web or main_api |

## Confirmation: no model / parity-core changes

- `app/waterfall_core.py` — NOT MODIFIED (parity-core, SHA unchanged)
- `app/project_factories.py` — NOT MODIFIED (parity-core, SHA unchanged)
- `reports/phase7_tuho_senior_debt_sizing_extraction.csv` — NOT MODIFIED (parity-core, SHA unchanged)
- `reports/phase23q_oborovo_senior_debt_sizing_extraction.csv` — NOT MODIFIED (parity-core, SHA unchanged)
- No financial formula changes
- No model output changes
- No fixture CSV changes (other than parity-core)
- No schema / migration changes
- No JS changes
- No runtime flag changes
- No route family refactors (only 1 new dep + 1 new helper)
- factory_template behavior: UNCHANGED
- save_run / save_project ordering: UNCHANGED (save_run first)
- replay_metadata export_type values: UNCHANGED
  - save_run: "saved_run_metadata"
  - save_project: "saved_run_project_state"
- save_project.runtime_timestamp: UNCHANGED
  (run_record.created_at.isoformat())

## Confirmation: rc1 untouched

```
b425a0708719eaa5e1d922b1008e5609758e0ad4	refs/heads/rc1
```

Verified unchanged on origin (pinned in
``TestPhase51FGuardrailsSmokeCheck::test_rc1_untouched`` in
the 51G-3 suite).

## Confirmation: forbidden side effects remain absent

In ``app/services/save_run_service.py`` (after stripping
docstrings, comments, and string literals):

- `record_export`: 0 occurrences
- `record_download_export`: 0 occurrences
- `record_runtime_summary_export`: 0 occurrences
- `record_institutional_workbook_export`: 0 occurrences
- `record_workspace_runtime`: 0 occurrences
- `update_scenario_last_run_summary`: 0 occurrences
- `db.add / db.commit / db.flush / session.add / session.commit`: 0 occurrences

The 51G-3 fix only changes which dep the user_created branch
calls. It does not add new persistence, audit, or recording
side effects.

## Confirmation: factory_template behavior unchanged

The factory_template branch's deps calls are byte-identical
to Phase 51G-2:

- `deps.build_schema_from_form(...)` — same kwargs
- `deps.build_projectinputs(schema)` — same args
- `deps.normalize_template_source(...)` — same args
- `runtime_seed == "tuho"` → `runtime_project_key = "TUHO"`
- `runtime_seed == "oborovo"` → `runtime_project_key = "Oborovo"`
- otherwise → `Solar` or `Wind` based on
  `deps.canonical_project_type(effective_project_type)`

Pinned in 51G-3's
`TestFactoryTemplateBranchUnchanged`.

## Confirmation: save_run / save_project ordering preserved

- `deps.save_run(...)` is called BEFORE
  `deps.save_project(...)` (byte-level position).
- No `deps.run_project(...)` call between them.
- save_run is called exactly once per successful save.
- save_project is called exactly once per successful save.
- save_project.runtime_timestamp =
  `run_record.created_at.isoformat()` (NOT `utc_now_iso()`).
- save_project.replay_metadata.project_id is explicitly
  `None`.

Pinned in 51G-3's
`TestSaveRunSaveProjectOrdering` and
`TestIntendedPersistenceSideEffectsPreserved`.

## Guardrails preserved

- No financial formula / model / project factory / fixture CSV
  changes.
- No schema / migration changes.
- No new JavaScript financial calculations.
- /run route+service from Phase 51B remain thin and intact.
- /compare route+service from Phase 51C-2 remain thin and intact.
- /validate route+service from Phase 51D-2 remain thin and intact.
- /download route+service from Phase 51E-2 remain thin and intact.
- /save-run route+service from Phase 51G-2 remain thin (route is
  the only thing that got 1 new dep wiring line added).
- run_service.py, compare_service.py, validation_service.py,
  download_service.py, export_service.py,
  export_audit_service.py, scenario_state_service.py all
  remain intact (unchanged).
- save_run_service.py does NOT import main_web or main_api
  (one-way import direction preserved).
- main_web.py has zero direct record_export calls.
- G20 remains BLOCKED.
- R99/R102 remain NOT APPROVED.
- partial_pay_sweep not promoted.
- flat / min DSCR sculpting not promoted.
- Generic solar / wind remain exploratory / unvalidated.
- No lender / bank / audit / certification / SaaS claims.
- Backend remains source of truth.
- rc1 remains frozen (SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  verified unchanged).
- PR #299 remains closed (no longer active guardrail).

## Recommended next phase

After 51G-3, the natural next extractions are:

1. **Phase 51H-1 + 51H-2** — Scenario state service family
   (`/scenarios/state/draft`, `/scenarios/state/discard`,
   `/scenarios/{scenario_id}/update-overrides`,
   `/scenarios/{scenario_id}/select`,
   `/scenarios/{scenario_id}/archive`,
   `/scenarios/{scenario_id}/rename`,
   `/scenarios/{scenario_id}/duplicate`,
   `/scenarios/add`,
   `/scenarios/save`).

2. **Phase 51I-1 + 51I-2** — Project save-as service
   (`/projects/{project_code}/save-as`,
   `/projects/create`).

3. **Phase 51J** — Optional: structural guardrail phase to add
   `export_service.py` / `export_audit_service.py` does NOT
   import `main_web` (per Phase 51E-1 / 51F recommendation).

`/run`, `/compare`, `/validate`, `/download` (Phases 51A-51E-2)
and `/save-run` (Phases 51G-1 / 51G-2 / 51G-3) now serve as
the canonical templates for vertical extraction, with a known
narrow bugfix phase pattern for any latent bugs that are
discovered along the way.

The pattern is:

- thin route (auth + form + snapshot + deps + service call +
  render)
- service owns orchestration
- deps bundle (callable injection)
- one-way import direction
- preserve all characterized behaviors and quirks
- preserve intended persistence side effects with exact ordering
- preserve factory_template behavior (Phase 51G-3 fix is
  narrow and only touches the user_created branch)
- for latent bugs discovered: characterize in N, preserve in
  N+1, fix in N+2 (separate PR with explicit user sign-off)
