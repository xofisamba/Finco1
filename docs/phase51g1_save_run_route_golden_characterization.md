# Phase 51G-1 — POST /save-run golden characterization

## Why this phase matters

POST /save-run is the **runtime-persistence sensitive** sibling of
/download, /compare, /validate, and /run. It is the primary entry
point for user-driven persistence. Unlike the other routes, it is
EXPECTED to perform INTENDED runtime writes:

- `save_run(...)` — persists the run record
- `save_project(...)` — updates the project's last_run_summary

These writes are NOT forbidden. They are the route's primary
purpose. The Phase 51F guardrails explicitly distinguish
"intended runtime persistence" from "forbidden persistence
regression" — and /save-run is the first route we characterize
that sits on the intended side of that line.

This phase pins the current /save-run behavior **before** any
extraction to `app/services/save_run_service.py` (which is
Phase 51G-2). After Phase 51G-1, the route is fully
characterized: any extraction in 51G-2 must preserve all 15
characterized behaviors or fail the test suite.

## Current route size

- **Location:** `main_web.py:2624–2760`
- **Total lines:** 137 (137 incl. blank lines)
- **Non-blank lines:** **127** (pinned in test)

## Route responsibilities (in order)

1. **Auth check** — `get_current_user(request)`, redirect to
   `/login` with 302 if missing.
2. **Form parse** — `await request.form()`, build snapshot via
   `_collect_form_snapshot(form)`.
3. **Project + workspace resolution** — call
   `_project_workspace_from_snapshot(user, snapshot)` to get
   `project_record` and `workspace_state`.
4. **Runtime guard** — call `check_runtime_allowed(workspace_state,
   snapshot)` → unpack 3-tuple
   `(allow_run, runtime_origin, guard_message)`. If `not allow_run`,
   return 200 + save_result-err with HX-Trigger.
5. **Build inputs dict** — read 9 form fields exactly:
   `capacity_mw, tariff_eur_mwh, p50_hours, total_capex_keur,
   opex_y1_keur, gearing_pct, target_dscr, interest_rate_pct,
   tenor_years`. user_id is **NEVER** read from form — always
   derived from `user.user_id`.
6. **Form validation** — call `_validate_form(effective_project_type,
   scenario, errors)`. If invalid, return 200 + save_result-err.
7. **Model execution (branched):**
   - **user_created branch:** call
     `_clean_user_project_runtime_snapshot(...)` → `build_projectinputs_from_snapshot(...)`
     → `runtime_project_key = "Solar" if Solar else "Wind"`.
     **KNOWN BUG:** `_clean_user_project_runtime_snapshot` is
     referenced but **NOT DEFINED** in main_web.py. This is a
     pre-existing latent bug, NOT introduced by Phase 51G-1. Any
     user_created project hitting /save-run will hit a `NameError`
     inside the broad `except Exception` and get back a
     save_result-err with message "Model error: name
     '_clean_user_project_runtime_snapshot' is not defined".
     This is pinned in
     `test_user_created_branch_has_latent_name_error`.
   - **factory_template branch:** call
     `_build_schema_from_form(effective_project_type, scenario,
     ...9 fields)` → `build_projectinputs(schema)` →
     `_normalize_template_source(project_record.template_source or
     project_record.source_project_template,
     effective_project_type)` → `runtime_seed in {"tuho",
     "oborovo", else}` → `runtime_project_key in {"TUHO",
     "Oborovo", "Solar"/"Wind"}`.
   - Both branches converge at `result = run_project(runtime_project_key,
     scenario, project_inputs_override=override)`.
   - KPI extraction: `kpis = result["kpis"]`.
8. **Persistence (try block, INTENDED writes):**
   - **save_run** with kwargs:
     `user_id, project_type=effective_project_type, scenario, inputs, kpis, replay_metadata=(_replay_metadata_for_project(project_code, export_type="saved_run_metadata", runtime_timestamp=utc_now_iso()))`
   - **save_project** with kwargs:
     `user_id, project_code, project_name, source_project_template=project_code, governance_state=_governance_snapshot(project_code), last_run_summary=kpis, replay_metadata=(_replay_metadata_for_project(project_code, project_id=None, export_type="saved_run_project_state", runtime_timestamp=run_record.created_at.isoformat()))`
   - **Order:** save_run FIRST, then save_project. If save_run
     raises, save_project is NOT called. If save_project raises
     after save_run succeeded, the run row is still committed.
9. **Success response (200)** — `save_result.html` partial with
   `success=True, run_id, project_type, scenario, created_at`,
   `HX-Trigger: refreshHistory`.
10. **Error response (200)** — `save_result.html` partial with
    `success=False, error`, `HX-Trigger: refreshHistory`. Used by
    all 4 error paths (allow_run, validate, model except, persist
    except).

## Form / session / project / scenario inputs

### Form fields (read)
| Field | Type | Used for |
|---|---|---|
| `active_project` | text | snapshot (for project resolution) |
| `project_name` | text | snapshot only |
| `project_type` | text | snapshot + effective fallback |
| `project_origin` | text | snapshot (branches execution) |
| `template_source` | text | snapshot (factory_template branch) |
| `country_market` | text | snapshot only |
| `scenario` | text | scenario + validation + run |
| `capacity_mw` | text | inputs dict |
| `tariff_eur_mwh` | text | inputs dict |
| `p50_hours` | text | inputs dict |
| `total_capex_keur` | text | inputs dict |
| `opex_y1_keur` | text | inputs dict |
| `gearing_pct` | text | inputs dict |
| `target_dscr` | text | inputs dict |
| `interest_rate_pct` | text | inputs dict |
| `tenor_years` | text | inputs dict |
| `cod_date, construction_months, horizon_years, capacity_factor, ppa_term_years` | text | snapshot only |
| (CAPEX line items, OPEX line items) | text | snapshot only |

### Session-derived (NOT from form)
- `user = get_current_user(request)`
- `user_id = user.user_id` (security: never trust form)

### Snapshot-derived
- `project_record = _project_workspace_from_snapshot(user, snapshot)[0]`
- `workspace_state = _project_workspace_from_snapshot(user, snapshot)[1]`
- `project_code = project_record.project_code`
- `project_name = project_record.project_name`
- `effective_project_type = project_record.project_type or project_type` (form fallback)
- `allow_run, runtime_origin, guard_message = check_runtime_allowed(workspace_state, snapshot)`

## Dependency / helper map

| Helper | Source | Used in /save-run |
|---|---|---|
| `get_current_user` | main_web.py | auth check |
| `_collect_form_snapshot` | main_web.py | form parsing |
| `_project_workspace_from_snapshot` | main_web.py | project resolution |
| `check_runtime_allowed` | app.services.scenario_state_service | runtime guard |
| `_validate_form` | main_web.py | form validation |
| `_canonical_project_type` | main_web.py | user_created runtime key |
| `_clean_user_project_runtime_snapshot` | **NOT DEFINED** (latent bug) | user_created branch |
| `build_projectinputs_from_snapshot` | app.input_adapter | user_created branch |
| `_build_schema_from_form` | main_web.py | factory_template branch |
| `build_projectinputs` | app.input_adapter | factory_template branch |
| `_normalize_template_source` | main_web.py | factory_template branch |
| `run_project` | app.api.project_runner | model execution |
| `save_run` | app.persistence.repository | persistence (intended) |
| `save_project` | app.persistence.repository | persistence (intended) |
| `_replay_metadata_for_project` | main_web.py | replay metadata |
| `_governance_snapshot` | main_web.py | project governance |
| `utc_now_iso` | app.persistence.provenance | timestamp |

## Runtime persistence side-effect map (INTENDED)

| Side effect | Class | Pin |
|---|---|---|
| `save_run(...)` | **INTENDED** | 1 call per success; `RunRecord` row created |
| `save_project(...)` | **INTENDED** | 1 call per success; `ProjectRecord.last_run_summary` updated |
| `run_project(...)` | model exec (in-memory) | not persistence, just memory + KPIs |
| `_replay_metadata_for_project` export_type="saved_run_metadata" | audit metadata | on save_run only |
| `_replay_metadata_for_project` export_type="saved_run_project_state" | audit metadata | on save_project only |
| `utc_now_iso()` | timestamp | save_run.replay_metadata.runtime_timestamp |
| `run_record.created_at.isoformat()` | timestamp | save_project.replay_metadata.runtime_timestamp (must match run timestamp) |

## Forbidden side effects (must NOT be introduced)

| Forbidden | Why |
|---|---|
| `record_export` | Export-audit, not save-audit |
| `record_download_export` | /download only |
| `record_runtime_summary_export` | /export only |
| `record_institutional_workbook_export` | /export only |
| `record_workspace_runtime` | /run only (already characterized) |
| `update_scenario_last_run_summary` | /run only (already characterized) |
| `db.add / db.commit / db.flush / session.add / session.commit` | /save-run uses the `save_run/save_project` repository functions, not raw SQLAlchemy |

## Exact intended write behavior

```text
on success:
    save_run(
        user_id=user.user_id,                  # session-derived
        project_type=effective_project_type,   # record.project_type or form
        scenario=scenario,                     # from form
        inputs=inputs,                          # 9 form fields
        kpis=kpis,                              # result["kpis"] from run_project
        replay_metadata={
            ..._replay_metadata_for_project(project_code,
                export_type="saved_run_metadata",
                runtime_timestamp=utc_now_iso())...
        },
    )
    save_project(
        user_id=user.user_id,
        project_code=project_code,             # from project_record
        project_name=project_name,             # from project_record
        source_project_template=project_code,  # SAME as project_code
        governance_state=_governance_snapshot(project_code),
        last_run_summary=kpis,                 # SAME kpis as save_run
        replay_metadata={
            ..._replay_metadata_for_project(project_code,
                project_id=None,               # explicit None
                export_type="saved_run_project_state",
                runtime_timestamp=run_record.created_at.isoformat())  # SAME timestamp as save_run
        },
    )
```

The `runtime_timestamp` used by save_project is the SAME as the
one used by save_run (via `run_record.created_at.isoformat()`), not
`utc_now_iso()`. This is a subtle quirk — the two writes are
locked to the run's commit time, not a fresh `now()` call.

## Response / redirect / template behavior

| Path | Status | Body | Headers |
|---|---|---|---|
| unauthenticated | 302 | empty | Location: /login |
| `not allow_run` | 200 | save_result-err (guard_message) | HX-Trigger: refreshHistory |
| invalid form | 200 | save_result-err (first error) | HX-Trigger: refreshHistory |
| model except | 200 | save_result-err ("Model error: {e}") | HX-Trigger: refreshHistory |
| success | 200 | save_result-ok (run_id, project_type, scenario, created_at) | HX-Trigger: refreshHistory |
| persist except | 200 | save_result-err ("Save failed: {e}") | HX-Trigger: refreshHistory |

All non-auth responses use the `partials/save_result.html`
template. The template uses `{% if success %}` to switch between
✅-icon (success) and ⚠️-icon (error) layouts. The HX-Trigger
header is `refreshHistory` on all 4 non-auth paths so HTMX
refreshes the run history panel.

## Error / fallback behavior

Two broad `except Exception` blocks:

1. **Model execution** wraps the user_created / factory_template
   branches. Returns 200 + save_result-err with message
   `Model error: {str(e)}`. This is the block that catches the
   `_clean_user_project_runtime_snapshot` NameError in the
   user_created branch.

2. **Persistence** wraps the `save_run + save_project` pair.
   Returns 200 + save_result-err with message
   `Save failed: {str(e)}`. The order of writes is critical:
   if save_run raises, save_project is NOT called. If
   save_project raises after save_run succeeded, the run row is
   already committed.

The `_validate_form` check is **not** wrapped in try/except — it
returns a save_result-err if invalid.

The `check_runtime_allowed` check is **not** wrapped in try/except
— it returns a save_result-err if `not allow_run`.

## Behavior quirks (pinned in tests)

1. **`runtime_origin` is captured but used only for the gate** —
   the 3-tuple is unpacked but `runtime_origin` is not used to
   mutate any state.
2. **`_clean_user_project_runtime_snapshot` is referenced but not
   defined** — pre-existing latent bug. The user_created branch
   of /save-run will hit a `NameError` and return
   "Model error: name '_clean_user_project_runtime_snapshot'
   is not defined". Pinned in
   `test_user_created_branch_has_latent_name_error`.
3. **`save_project.runtime_timestamp = run_record.created_at`** —
   not `utc_now_iso()`. The two writes are locked to the run's
   commit time. Pinned in
   `test_save_project_uses_run_record_created_at`.
4. **`save_project.replay_metadata.project_id = None` explicitly**
   — the repository fills it in based on the existing row. Pinned
   in `test_save_project_replay_metadata_includes_project_id_none`.
5. **All 4 non-auth responses use the same partial template** —
   `partials/save_result.html`. They differ only in context
   (success, error). Pinned in
   `test_all_responses_use_save_result_html` and
   `test_all_responses_use_hx_trigger_refresh_history`.
6. **`_validate_form` uses a hardcoded `PROJECT_TYPES` and
   `SCENARIOS` set** — not the project record's actual values.
   This means a `project_type` from the form that is not in
   `PROJECT_TYPES` will fail validation, even if the project
   record has that type. Pinned via the existing
   `_validate_form` behavior.
7. **Order of writes: save_run → save_project** — pinned in
   `test_save_run_called_first_save_project_second`.

## Recommended extraction boundary for 51G-2

When extracting to `app/services/save_run_service.py`, the
following should move:

| Should move to service | Should stay in route |
|---|---|
| `save_run` orchestration (kwargs assembly) | `auth check (get_current_user)` |
| `save_project` orchestration (kwargs assembly) | `form parsing (request.form())` |
| `_replay_metadata_for_project` calls | `snapshot collection` |
| `_governance_snapshot` call | `template response construction` |
| `_validate_form` call | `redirect on no user` |
| user_created / factory_template branch dispatch | `HTMX HX-Trigger header` |
| `run_project` call + KPI extraction | |
| `runtime_origin` 3-tuple unpacking | |
| broad `except Exception` for model + persist | |

**Recommended service API (51G-2):**

```python
@dataclass
class SaveRunRouteOutcome:
    template_name: str = "partials/save_result.html"
    context: dict = field(default_factory=dict)
    status_code: int = 200
    hx_trigger: str = "refreshHistory"
    is_redirect: bool = False
    redirect_url: Optional[str] = None


@dataclass
class SaveRunRouteDeps:
    # 16 callables:
    project_workspace_from_snapshot: Callable
    check_runtime_allowed: Callable
    validate_form: Callable
    canonical_project_type: Callable
    clean_user_project_runtime_snapshot: Callable  # may be a stub returning empty dict
    build_projectinputs_from_snapshot: Callable
    build_schema_from_form: Callable
    build_projectinputs: Callable
    normalize_template_source: Callable
    run_project: Callable
    save_run: Callable
    save_project: Callable
    replay_metadata_for_project: Callable
    governance_snapshot: Callable
    utc_now_iso: Callable


async def execute_save_run_route(
    *, request, form, user, deps: SaveRunRouteDeps,
) -> SaveRunRouteOutcome: ...
```

The route becomes a thin wrapper that:

1. Calls `get_current_user` (auth — route-owned).
2. Calls `await request.form()` (form parsing — route-owned).
3. Calls `execute_save_run_route(request=request, form=form, user=user, deps=deps)`.
4. If `outcome.is_redirect`, returns `RedirectResponse(outcome.redirect_url)`.
5. Otherwise, returns `templates.TemplateResponse(
       request=request,
       name=outcome.template_name,
       context=outcome.context,
       headers={"HX-Trigger": outcome.hx_trigger},
       status_code=outcome.status_code,
   )`.

The latency bug (`_clean_user_project_runtime_snapshot`) should
be FIXED in 51G-2 by injecting a stub (e.g.
`lambda *_: {}`) into the deps bundle. This is a behavior
change — it removes the NameError and lets the user_created
branch actually save. **Discuss with the user before doing this
in 51G-2.** It is NOT done in 51G-1 (characterization only).

## Risks for extraction

1. **Latent NameError** — `_clean_user_project_runtime_snapshot`
   is not defined. If we inject a stub, the user_created branch
   will start working. If we don't, we perpetuate the bug. The
   user should decide before 51G-2.
2. **Phase 51F guardrails** — extraction must not change model
   output, must not modify parity-core files, must not import
   main_web from the new service.
3. **Two-template-branches complexity** — the
   user_created/factory_template branch is already complex
   (~30 lines). It must move as a unit, not be split.
4. **save_run → save_project ordering** — if extraction
   accidentally reverses the order, `save_project.runtime_timestamp
   = run_record.created_at` will fail. Pinned in
   `test_save_run_called_first_save_project_second`.
5. **HTMX HX-Trigger header** — must be preserved on all
   responses, not just success. Pinned in
   `test_all_responses_use_hx_trigger_refresh_history`.

## Test results

| Command | Result |
|---|---|
| `python -m pytest tests/test_phase51g1_save_run_route_golden_characterization.py` | 55 passed (out of 58 — 3 are docs/summary self-inventory, written after the test) |
| `python -m pytest tests/test_phase51f_parallel_work_guardrails.py` | 21 passed |
| `python -m pytest tests/test_phase51*.py` | 357 + 21 + 55 = **433 passed** |

## Guardrails preserved

- No financial formula / model / project factory / fixture CSV
  changes.
- No schema / migration changes.
- No new JavaScript financial calculations.
- /run, /compare, /validate, /download route+service from Phases
  51A–51E-2 remain intact.
- run_service.py, compare_service.py, validation_service.py,
  download_service.py remain intact.
- export_service.py, export_audit_service.py,
  scenario_state_service.py remain intact.
- main_web.py is **not** modified (Phase 51G-1 is
  characterization only).
- /save-run remains in main_web.py (no extraction yet).
- rc1 remains frozen (SHA b425a0708719eaa5e1d922b1008e5609758e0ad4
  verified unchanged).
- PR #299 remains closed.
- G20 / R99 / R102 / partial_pay_sweep / DSCR sculpting
  guardrails preserved.
- No lender / bank / audit / certification / SaaS claims.
- Backend remains source of truth.
- Generic solar / wind remain exploratory / unvalidated.

## Recommended next phase

**Phase 51G-2** — Extract /save-run route orchestration into
`app/services/save_run_service.py`, following the 51B/51C-2/51D-2/51E-2
pattern:

- thin route (auth + form + deps + service call + render)
- service owns orchestration
- deps bundle (callable injection)
- one-way import direction
- preserve all 15 characterized behaviors (pinned by 55 tests)
- preserve save_run → save_project ordering
- preserve `runtime_timestamp = run_record.created_at.isoformat()` quirk
- preserve all 4 non-auth response shapes (success, allow_run, validate, model, persist)

**Latent bug to discuss:** Should 51G-2 also fix the
`_clean_user_project_runtime_snapshot` NameError, or perpetuate
the bug? Recommendation: **fix it** (inject a stub dep), because
the user_created branch is currently dead. But this is a
behavior change and needs user sign-off.
