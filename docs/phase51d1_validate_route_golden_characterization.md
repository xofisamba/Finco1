# Phase 51D-1 — /validate route golden characterization

## Base SHA

`d2130bfa3504b5c38ea1a182680a7da50871ad3e` (origin/main @ PR #382 merge,
Phase 51C-2 /compare extraction)

## Objective

Characterize the current `POST /validate` route behavior **before** any
extraction. This is characterization only. No production code changes,
no refactor, no extraction. The goal is to pin the current contract
(structural + behavioral) so that Phase 51D-2 can extract the
orchestration into `app/services/validation_service.py` with
confidence that behavior is preserved.

This phase follows the same pattern as Phase 51A (/run golden
characterization), Phase 51B (/run vertical extraction), Phase 51C-1
(/compare golden characterization), and Phase 51C-2 (/compare vertical
extraction). `/run` and `/compare` are now extracted; `/validate` is
the next god-module hotspot in `main_web.py`.

## Current POST /validate route location

`main_web.py:1428` — `@app.post("/validate")` decorated async handler
`async def validate(request: Request)`.

Total body: 85 lines (decorator + def + body, including blank lines),
76 non-blank. Comparable in size to the pre-extraction `/compare`
route (95 lines, 89 non-blank), though `/validate` is structurally
simpler: it does NOT call `run_project`, does NOT iterate scenarios,
and is purely read-only (no persistence side effects, no model
execution).

## Responsibilities currently in `main_web.py`

1. **Auth redirect** — `get_current_user(request)` →
   `RedirectResponse("/login", 302)` if unauthenticated.
2. **Form parsing** — reads 12 form fields (project_type, scenario,
   capacity_mw, tariff_eur_mwh, p50_hours, total_capex_keur,
   opex_y1_keur, gearing_pct, target_dscr, interest_rate_pct,
   tenor_years) and `_collect_form_snapshot(form)`.
3. **Project/workspace resolution** —
   `_project_workspace_from_snapshot(user, snapshot)`.
4. **Runtime guard** — `check_runtime_allowed(workspace_state,
   snapshot)` → `errors.html` if not allowed.
5. **Runtime snapshot resolution** — IF
   `(runtime_origin == "saved_state" and workspace_state.active_scenario_id) or project_record.project_origin == "user_created"`,
   THEN call `_resolve_runtime_snapshot_source(...)` and capture the
   resolved snapshot (the result tuple is unpacked; the snapshot is
   the first element; other elements discarded). Note: unlike `/run`
   and `/compare`, `/validate` does NOT use the resolved snapshot
   downstream — it is only resolved for parity with `/run` and
   `/compare`, but it is currently unused. This is a candidate
   simplification target for Phase 51D-2 if confirmed.
6. **Validation** — three stages, all contributing to an `errors`
   list:
   - **Stage A: enum validation** —
     `if project_type not in PROJECT_TYPES: errors.append(...)`,
     `if scenario not in SCENARIOS: errors.append(...)`.
   - **Stage B: numeric field validation** — for each of 9 numeric
     fields, call `_validate_numeric_field(name, val, max_val)`,
     append any returned error. The numeric max values are:
     capacity_mw=2000.0, tariff_eur_mwh=1000.0, p50_hours=10000.0,
     total_capex_keur=1_000_000.0, opex_y1_keur=500_000.0,
     gearing_pct=100.0, target_dscr=10.0, interest_rate_pct=30.0,
     tenor_years=50.0.
   - **Stage C: schema build validation** — IF no errors so far,
     call `_build_schema_from_form(project_type, scenario, 10
     numeric fields, ...)`. If it raises `ValueError`, append
     `str(ve)` to errors.
7. **Template render** — `partials/validation.html` with `valid`
   (bool), `errors` (list), and `form_data` (dict subset) context.

## Input fields / form behavior

| Field | Type | Used for |
|---|---|---|
| `project_type` | str (enum) | enum validation (`PROJECT_TYPES`); schema build |
| `scenario` | str (enum) | enum validation (`SCENARIOS`); schema build |
| `capacity_mw` | str (numeric) | numeric field validation; schema build |
| `tariff_eur_mwh` | str (numeric) | numeric field validation; schema build |
| `p50_hours` | str (numeric) | numeric field validation; schema build |
| `total_capex_keur` | str (numeric) | numeric field validation; schema build |
| `opex_y1_keur` | str (numeric) | numeric field validation; schema build |
| `gearing_pct` | str (numeric) | numeric field validation; schema build |
| `target_dscr` | str (numeric) | numeric field validation; schema build |
| `interest_rate_pct` | str (numeric) | numeric field validation; schema build |
| `tenor_years` | str (numeric) | numeric field validation; schema build |

The form is parsed once at the top of the handler. All numeric fields
are read as strings; `_validate_numeric_field` and
`_build_schema_from_form` are responsible for coercion + validation.

`active_project` is **not** read by /validate (unlike /run). /validate
operates on the form's `project_type` and `scenario` directly.

## Project / workspace / scenario dependencies

`/validate` depends on:
- `_project_workspace_from_snapshot` — to resolve the
  project_record and workspace_state for the current user.
- `check_runtime_allowed` — to enforce the runtime guard.
- `_resolve_runtime_snapshot_source` — for parity with /run and
  /compare (the resolved snapshot is captured but currently unused
  downstream in /validate).
- `_build_schema_from_form` — for Stage C schema build validation.
- `_validate_numeric_field` — for Stage B numeric field validation.
- `PROJECT_TYPES` constant = `["Solar", "Wind"]`.
- `SCENARIOS` constant = `["Base", "Downside", "Upside"]`.

`/validate` does NOT depend on:
- `run_project` (no model execution).
- `build_projectinputs` / `build_projectinputs_from_snapshot`
  (no ProjectInputs construction).
- `_normalize_template_source` (no template-seeded branching).
- `_canonical_project_type` (no project_key resolution).
- `_scenario_provenance_for_record` (no persistence).
- Any `record_*` helper (no persistence side effects).

## Validation flow

```
POST /validate
    │
    ├── 1. Auth check
    │   └── not authenticated → 302 redirect to /login
    │
    ├── 2. Form parse (12 fields) + snapshot
    │
    ├── 3. Project/workspace resolution
    │   └── _project_workspace_from_snapshot(user, snapshot)
    │
    ├── 4. Runtime guard
    │   └── check_runtime_allowed(workspace_state, snapshot)
    │       └── not allowed → errors.html with [guard_message]
    │
    ├── 5. Runtime snapshot resolution (captured, not used)
    │   └── _resolve_runtime_snapshot_source(...)
    │
    ├── 6. Stage A: enum validation
    │   ├── project_type not in PROJECT_TYPES → "project_type must be one of [...]"
    │   └── scenario not in SCENARIOS → "scenario must be one of [...]"
    │
    ├── 7. Stage B: numeric field validation
    │   └── for each of 9 numeric fields:
    │       └── _validate_numeric_field(name, val, max_val) → error if non-empty string fails
    │
    ├── 8. Stage C: schema build validation (only if no errors so far)
    │   └── _build_schema_from_form(...)
    │       └── ValueError → str(ve) appended
    │
    └── 9. Template render
        └── partials/validation.html with {valid, errors, form_data}
```

## Response template

`partials/validation.html` with context:

```python
{
    "valid": bool,        # len(errors) == 0
    "errors": list[str],  # all errors from stages A, B, C
    "form_data": {
        "project_type": str,
        "scenario": str,
    },
}
```

The template (verified at `app/templates/partials/validation.html`):

```html
{% if not valid %}
  <div class="alert alert-error">Validation failed - please fix the following:</div>
{% endif %}
{% for err in errors %}
  <div class="alert alert-error">{{ err }}</div>
{% endfor %}
{% if valid %}
  <div class="alert alert-info">Input checks passed. Click <strong>Run Model</strong> when ready.</div>
{% endif %}
```

## Context keys

| Key | Type | Source |
|---|---|---|
| `valid` | bool | `len(errors) == 0` |
| `errors` | list[str] | Stage A, B, C errors |
| `form_data` | dict | `{"project_type": project_type, "scenario": scenario}` (subset of form fields) |

No `messages`, no `integration_status`, no replay metadata, no
project_type outside the form_data subset.

## Warning / error behavior

Three validation stages contribute to the `errors` list. The
`partials/validation.html` template renders ALL errors as a list. No
short-circuit on first error — every validation rule is checked.

1. **Auth**: unauthenticated → redirect to `/login` (302).
2. **Runtime guard**: `check_runtime_allowed` returns
   `(False, _, guard_message)` → render with `[guard_message]`.
3. **Stage A (enum)**:
   - `project_type not in PROJECT_TYPES` → `"project_type must be one of {PROJECT_TYPES}"`
   - `scenario not in SCENARIOS` → `"scenario must be one of {SCENARIOS}"`
4. **Stage B (numeric)** — for each of 9 numeric fields:
   - empty/None → no error (treated as optional)
   - non-numeric → `"{name} must be a number"`
   - negative → `"{name} must be non-negative"`
   - above max → `"{name} must be <= {max_val}"`
5. **Stage C (schema build)** — only run if no Stage A/B errors:
   - `ValueError` from `_build_schema_from_form` → `str(ve)` appended.

The response is always `partials/validation.html` with status 200
(regardless of `valid` being True or False). There is no `errors.html`
response except for the runtime guard block path.

## Persistence side effects

**None.** The `/validate` route is purely read-only. There is no
`record_*` helper called, no DB write, no scenario state update.
This is similar to `/compare` (also read-only) and in contrast to
`/run` (which calls `record_workspace_runtime` and
`update_scenario_last_run_summary`).

Verified by:
- `grep "record_\|db\.\|session\." main_web.py` for the /validate
  route body → no matches.
- `grep "_validate_numeric_field" main_web.py` outside the route
  definition → only used inside the /validate route (line 1486).

This is an important characteristic for Phase 51D-2: extracting
`/validate` into `validation_service.py` is structurally simpler
than `/run` (no persistence) and slightly different from `/compare`
(no scenario loop, no model execution).

## Current test coverage

There are NO existing golden tests for the `/validate` route. The
only `/validate` references in the test suite are:

* `tests/test_api.py` — tests for the JSON API route
  `POST /api/v1/validate` (different from the web form route
  `POST /validate`). These are not in scope for Phase 51D-1.
* Pre-compiled bytecode files in `tests/__pycache__/` referencing
  `/validate` (legacy, no longer maintained).

Phase 51D-1 introduces the FIRST golden characterization test suite
for `POST /validate` at
`tests/test_phase51d1_validate_route_golden_characterization.py`.

## Latent issues / candidates for Phase 51D-2

* **Runtime snapshot resolved but unused (latent)** — Line ~1462 of
  main_web.py resolves `runtime_snapshot` via
  `_resolve_runtime_snapshot_source(...)` for parity with `/run` and
  `/compare`, but the resolved snapshot is never used downstream.
  This means the call is a no-op for `/validate`. Phase 51D-2 may
  preserve this behavior (parity) OR drop the call if it's confirmed
  dead. The behavior-preserving choice is to keep it; the cleanup
  choice is to drop it. **Phase 51D-1 only characterizes; the
  decision is deferred to 51D-2.**

* **Empty numeric field behavior** — empty string passes Stage B
  silently (returns `(None, None)`). This means a form with
  `capacity_mw=""` will pass Stage B and potentially fail Stage C
  (schema build) instead. This is a current behavior; it is
  preserved.

* **Bare-`Exception` discipline** — Stage C catches only
  `ValueError`. There is no bare-`Exception` catch. This is BETTER
  discipline than `/compare` (which has a bare-`Exception` catch on
  the schema build path). Preserved.

* **`runtime_origin` from runtime guard is the only source of
  truth for the snapshot resolution branch** — the current logic
  uses `runtime_origin == "saved_state" and
  workspace_state.active_scenario_id` exactly as `/run` and
  `/compare` do. Preserved.

* **No "all-scenarios error" path** — unlike `/compare`, `/validate`
  does not iterate scenarios. The validation is one-shot. No
  per-scenario soft-error semantics. Preserved.

## Extraction risks

| Risk | Severity | Mitigation |
|---|---|---|
| Behavior drift in three validation stages (A, B, C) | medium | Pin stage order and rule output in test_phase51d1 |
| Numeric field max values change silently | low | Pin all 9 numeric max values in test_phase51d1 |
| `_validate_numeric_field` signature change | low | Pin: returns `(value, error_message)`; `value=None` for empty input |
| Runtime snapshot resolution dropped (cleanup) instead of preserved | low | Phase 51D-1 only characterizes; 51D-2 must preserve for parity unless explicitly removed |
| `PROJECT_TYPES` / `SCENARIOS` constants moved | low | Move to deps bundle in 51D-2 (mirror compare_service.py) |
| `_build_schema_from_form` arg order change | medium | Pin 10-arg order; identical to /compare |
| Template context key shape change | medium | Pin context keys: `valid`, `errors`, `form_data` (with `project_type` + `scenario` subset) |
| `form_data` subset changes (e.g. adding more fields) | low | Pin: only `project_type` and `scenario` in `form_data` |
| Stage C skipped when Stage A/B has errors | low | Pin: schema build only runs when `not errors` |
| Validation flow becomes "short-circuit on first error" | low | Pin: all rules are checked, errors accumulate |
| `valid` bool computed differently | low | Pin: `valid = len(errors) == 0` |

## Proposed Phase 51D-2 `validation_service` boundary

Mirroring the Phase 51B (`run_service`) and Phase 51C-2
(`compare_service`) pattern:

```python
# app/services/validation_service.py

@dataclass
class ValidateRouteOutcome:
    template_name: str
    context: dict
    status_code: int = 200

@dataclass
class ValidateRouteDeps:
    """DI bundle for helpers still in main_web.py."""
    collect_form_snapshot: Callable
    project_workspace_from_snapshot: Callable
    canonical_project_type: Callable           # (currently unused, kept for future parity with /compare)
    normalize_template_source: Callable        # (currently unused, kept for future parity with /run)
    check_runtime_allowed: Callable
    resolve_runtime_snapshot_source: Callable  # (currently captured but unused, kept for parity)
    build_schema_from_form: Callable
    validate_numeric_field: Callable            # <-- NEW vs. compare_service: validate_form maps to _validate_numeric_field
    project_types: list[str]                    # PROJECT_TYPES constant
    scenarios: list[str]                        # SCENARIOS constant
    snapshot_input_error: type                  # (currently unused by /validate, but in deps for parity)

async def execute_validate_route(
    *,
    request,
    form,
    user,
    deps: ValidateRouteDeps,
) -> ValidateRouteOutcome:
    """Execute the /validate orchestration and return a ValidateRouteOutcome.
    The route in main_web.py translates the outcome into a FastAPI response."""
```

**Notes on deps:**

* `validate_numeric_field` is the analog of `validate_form` in the
  proposed spec above. The /validate route uses
  `_validate_numeric_field(name, val, max_val)` to validate each
  numeric field. This is a per-field helper, not a whole-form helper
  like `/run`'s `validate_form`. The deps field is renamed to
  `validate_numeric_field` to be explicit about the per-field
  granularity.

* `canonical_project_type`, `normalize_template_source`,
  `snapshot_input_error` are NOT used by /validate today but are
  included in the deps for parity with `compare_service` and
  `run_service` patterns. Phase 51D-2 may choose to either keep
  these in the deps bundle (parity) or drop them (YAGNI). Both are
  acceptable; the characterization pin is that the route does NOT
  use them today.

* The 9 numeric max values
  (`2000.0 / 1000.0 / 10000.0 / 1_000_000.0 / 500_000.0 / 100.0 /
  10.0 / 30.0 / 50.0`) are hard-coded in the current route. Phase
  51D-2 may either keep them hard-coded in the service (current
  behavior) or move them to a deps field (refactor, out of scope
  for behavior-preserving extraction). The proposed deps bundle
  does NOT include them as a separate field; they stay inside the
  service, matching the current route's behavior.

* `resolve_runtime_snapshot_source` IS called in the current
  /validate route (line ~1463) for parity with /run and /compare,
  but the resolved snapshot is unused. The proposed deps bundle
  includes it; the service will call it for parity and discard the
  result. This preserves the current behavior exactly. (An
  alternative 51D-2 simplification would be to drop the call; this
  is documented in 51D-1 as a "candidate for cleanup" but is
  explicitly NOT done in 51D-1.)

The /validate route in main_web.py would shrink from ~76 non-blank
lines to roughly 30 lines (auth + form + deps build + service call
+ template render), mirroring the /compare extraction pattern.

## Guardrails

✅ Did NOT change production code.
✅ Did NOT refactor /validate.
✅ Did NOT change validation behavior.
✅ Did NOT change financial formulas.
✅ Did NOT change runtime calculations.
✅ Did NOT change model outputs.
✅ Did NOT change scenario behavior.
✅ Did NOT change export behavior.
✅ Did NOT change project factories.
✅ Did NOT change fixture CSVs.
✅ Did NOT change schema / migrations.
✅ Did NOT add JavaScript financial calculations.
✅ Did NOT implement generic validation.
✅ Did NOT promote G20 / R99 / R102.
✅ Did NOT promote partial_pay_sweep.
✅ Did NOT promote flat / min DSCR sculpting.
✅ Backend remains source of truth.
✅ `run_service.py` from Phase 51B remains intact.
✅ `compare_service.py` from Phase 51C-2 remains intact.
✅ `/run` route from Phase 51B remains thin.
✅ `/compare` route from Phase 51C-2 remains thin.
✅ PR #299 remains draft / not merged.

## Recommended next phase

**Phase 51D-2** — `/validate` route vertical extraction into
`app/services/validation_service.py`, using the same
behavior-first approach as 51B and 51C-2:

1. Create `validation_service.py` with the API above.
2. Slim /validate route in main_web.py.
3. Decide on the runtime-snapshot-resolved-but-unused call:
   preserve for parity (recommended) or drop for cleanup
   (alternative). Document the choice in the 51D-2 PR.
4. Pin the new contract with a Phase 51D-2 test suite mirroring
   `test_phase51c2_compare_route_vertical_extraction.py`.
5. Update Phase 51A/B/C/51C-2 tests for the new contract (same
   relaxations as 51B and 51C-2).
