# Phase 51C-1 — /compare route golden characterization

## Base SHA

`542348307ee74df2dc73a854dc11588814f2c1e3` (origin/main @ PR #380 merge)

## Objective

Characterize the current `POST /compare` route behavior **before** any
extraction. This is characterization only. No production code changes,
no refactor, no extraction. The goal is to pin the current contract
(structural + behavioral) so that Phase 51C-2 can extract the
orchestration into `app/services/compare_service.py` with confidence
that behavior is preserved.

This phase follows the same pattern as Phase 51A (/run golden
characterization) and Phase 51B (/run vertical extraction). The /run
extraction is now merged; /compare is the next god-module hotspot.

## Current POST /compare route location

`main_web.py:1587` — `@app.post("/compare")` decorated async handler
`async def compare(request: Request)`.

Total body: 100 lines (decorator + def + body, including blank lines),
~89 non-blank. Comparable to the pre-extraction /run route body
size (~388 lines), though /compare is structurally simpler: no
sessionStorage script, no three execution paths, no per-scenario
side effects.

## Responsibilities currently in `main_web.py`

1. **Auth redirect** — `get_current_user(request)` →
   `RedirectResponse("/login", 302)` if unauthenticated.
2. **Form parsing** — reads the 10 form fields (project_type,
   capacity_mw, tariff_eur_mwh, p50_hours, total_capex_keur,
   opex_y1_keur, gearing_pct, target_dscr, interest_rate_pct,
   tenor_years) and `_collect_form_snapshot(form)`.
3. **Project/workspace resolution** —
   `_project_workspace_from_snapshot(user, snapshot)`.
4. **Runtime guard** — `check_runtime_allowed(workspace_state,
   snapshot)` → `errors.html` if not allowed.
5. **Validation** — `project_type` must be in `PROJECT_TYPES` →
   `errors.html` if not.
6. **Override construction** — two paths:
   - `user_created`: `build_projectinputs_from_snapshot(runtime_snapshot)`.
   - template-seeded: `build_projectinputs_from_snapshot(runtime_snapshot)`
     if `saved_state` + `active_scenario_id`, else build schema from
     form via `_build_schema_from_form(...)` and call
     `build_projectinputs(schema)`.
7. **Project key resolution** —
   `runtime_project_key = "TUHO" | "Oborovo" | "Solar" | "Wind"`
   based on `template_source` and canonical project type.
8. **Model execution loop** — `for sc in SCENARIOS: run_project(
   runtime_project_key, sc, project_inputs_override=override)`,
   capturing 6 KPIs per scenario.
9. **Template render** — `partials/comparison.html` with
   `project_type`, `scenarios`, `results` context.

## Input fields / form behavior

| Field | Type | Used for |
|---|---|---|
| `project_type` | str | schema build; project key resolution |
| `capacity_mw` | str (numeric) | schema build |
| `tariff_eur_mwh` | str (numeric) | schema build |
| `p50_hours` | str (numeric) | schema build |
| `total_capex_keur` | str (numeric) | schema build |
| `opex_y1_keur` | str (numeric) | schema build |
| `gearing_pct` | str (numeric) | schema build |
| `target_dscr` | str (numeric) | schema build |
| `interest_rate_pct` | str (numeric) | schema build |
| `tenor_years` | str (numeric) | schema build |

The form is parsed once at the top of the handler. All numeric fields
are read as strings; `_build_schema_from_form` is responsible for
coercion + validation.

`active_project` is **not** read by /compare (unlike /run). /compare
always uses the form's project_type and the project_record's
project_type/template_source.

## Scenario paths

`SCENARIOS = ["Base", "Downside", "Upside"]` (defined in
`main_web.py:138`). All three are always run — there is no
"select which scenarios to compare" UI; the loop iterates over the
hard-coded list.

## Model execution paths

For each scenario in `SCENARIOS`:

```python
r = run_project(
    runtime_project_key,
    sc,
    project_inputs_override=override,
)
```

Where `runtime_project_key ∈ {"TUHO", "Oborovo", "Solar", "Wind"}`.
`override` is the `ProjectInputs` instance built from either the saved
scenario snapshot (if `saved_state` + `active_scenario_id`) or the
form-built schema.

Each scenario's `kpis` are reduced to 6 fields:

| Field | Source |
|---|---|
| `project_irr` | `r["kpis"]["project_irr"]` |
| `equity_irr` | `r["kpis"]["equity_irr"]` |
| `min_dscr` | `r["kpis"]["min_dscr"]` |
| `avg_dscr` | `r["kpis"]["avg_dscr"]` |
| `total_revenue_keur` | `r["kpis"]["total_revenue_keur"]` |
| `total_ebitda_keur` | `r["kpis"]["total_ebitda_keur"]` |

Per-scenario errors are captured as `{"error": str(e)}` in the
`results[sc]` dict; the loop continues on exception (does not
short-circuit).

## Response template

`partials/comparison.html` with context:

```python
{
    "project_type": effective_project_type,
    "scenarios": SCENARIOS,  # ["Base", "Downside", "Upside"]
    "results": results,       # dict[scenario, dict[kpi_name, value]]
}
```

## Context keys

| Key | Type | Source |
|---|---|---|
| `project_type` | str | `effective_project_type` (project_record.project_type or form) |
| `scenarios` | list[str] | `SCENARIOS` constant |
| `results` | dict[str, dict] | 3 entries (Base / Downside / Upside), each with 6 KPIs or `{"error": str}` |

No messages, no integration_status, no replay metadata in /compare
context (unlike /run which has those).

## Warning / error behavior

Three error paths, all rendering `partials/errors.html` with
`{"errors": [...]}` context:

1. **Auth**: unauthenticated → redirect to `/login` (302).
2. **Runtime guard**: `check_runtime_allowed` returns
   `(False, _, guard_message)` → render with `[guard_message]`.
3. **Validation**: `project_type not in PROJECT_TYPES` → render
   with `[f"project_type must be one of {PROJECT_TYPES}"]`.
4. **SnapshotInputError** (user_created path): `str(e)` in errors.
5. **Schema build failure** (template-seeded path): `f"Invalid input:
   {str(e)}"` in errors. The `except` clause catches both `ValueError`
   and the bare `Exception` (anti-pattern — overly broad).
6. **Per-scenario model failure** (inside the loop): the scenario
   gets `{"error": str(e)}` in `results[sc]`; the loop continues.
   The response is still 200 with `partials/comparison.html`. This is
   "soft error" behavior, distinct from the hard-error paths above.

## Persistence side effects

**None.** The /compare route is purely read-only. There is no
`record_compare_run`, no scenario state update, no replay metadata
persistence. This is in contrast to /run, which calls
`record_workspace_runtime` and `update_scenario_last_run_summary`.

Verified by:
- `grep -n "record_" main_web.py | grep -i compare` → no matches
- `grep -rn "record_compare" app/` → no matches
- `grep -n "compare_run" app/persistence/repository.py` → no matches

This is an important characteristic for Phase 51C-2: extracting the
read-only /compare body into `compare_service.py` is structurally
simpler than /run because there are no persistence side effects to
preserve.

## Latent bug discovered (xfail)

`main_web.py` line 1612 references `runtime_snapshot` in the
`user_created` branch:

```python
if project_record.project_origin == "user_created":
    try:
        override = build_projectinputs_from_snapshot(runtime_snapshot)
    except SnapshotInputError as e:
        ...
```

But `runtime_snapshot` is **never defined** in the /compare handler.
The /run handler defines `runtime_snapshot` via
`resolve_runtime_snapshot_source(...)` after the runtime guard; the
/compare handler does not. This means the `user_created` path in
/compare would raise `NameError: name 'runtime_snapshot' is not
defined` on the first execution.

This is a **pre-existing latent bug** in the current /compare code
(not introduced by Phase 51C-1). It is NOT a Phase 51C-1 regression.
The /run path defines `runtime_snapshot` properly; the /compare path
was likely written before the runtime snapshot resolver was added and
was never updated.

Phase 51C-1 marks this as `xfail` in the characterization tests
(`test_compare_user_created_path_raises_nameerror` etc.). The fix is
out of scope for this phase — it would either be:

(a) Add a `runtime_snapshot = None` fallback at the top of /compare,
    or
(b) Properly resolve the runtime snapshot via
    `resolve_runtime_snapshot_source(...)` like /run does.

Option (b) is the correct fix and would belong in a future phase
(possibly 51C-2 as part of the extraction, with explicit
characterization before/after).

## Extraction risks

| Risk | Severity | Mitigation |
|---|---|---|
| Behavior drift in override construction (user_created vs template-seeded branches) | medium | Pin the branch logic + the order of checks in test_phase51c1 |
| `runtime_snapshot` NameError on user_created path | high (latent) | Document as xfail; fix in 51C-2 or later |
| Per-scenario `{"error": ...}` soft-error semantics lost during extraction | medium | Pin the "loop continues on exception" behavior |
| Bare `except Exception` swallowing real bugs | low (pre-existing) | Document; fix out of scope |
| `SCENARIOS` constant referenced via globals in handler | low | Move to deps bundle in 51C-2 |
| `PROJECT_TYPES` constant referenced via globals in handler | low | Move to deps bundle in 51C-2 |
| `_build_schema_from_form` order of 10 args | medium | Pin in test: arg order matters for Pydantic schema |
| Template context key shape changes during extraction | medium | Pin context keys: `project_type`, `scenarios`, `results` |
| `run_project` exception during one scenario short-circuits the whole compare | low | Pin: loop continues, others get their values |
| New test path in 51C-2 needs `runtime_snapshot` resolution added | medium | Document that 51C-2 must add this resolution; 51C-1 only characterizes what exists today |

## Proposed Phase 51C-2 `compare_service` boundary

Mirroring the Phase 51B /run pattern:

```python
# app/services/compare_service.py

@dataclass
class CompareRouteOutcome:
    template_name: str
    context: dict
    status_code: int = 200

@dataclass
class CompareRouteDeps:
    """DI bundle for helpers still in main_web.py."""
    collect_form_snapshot: Callable
    project_workspace_from_snapshot: Callable
    canonical_project_type: Callable
    normalize_template_source: Callable
    check_runtime_allowed: Callable
    build_schema_from_form: Callable
    build_projectinputs: Callable
    build_projectinputs_from_snapshot: Callable
    scenarios: list[str]      # PROJECT_SCENARIOS constant
    project_types: list[str]  # PROJECT_TYPES constant
    snapshot_input_error: type
    run_project: Callable

async def execute_compare_route(
    *,
    request,
    form,
    user,
    deps: CompareRouteDeps,
) -> CompareRouteOutcome:
    """Execute the /compare orchestration and return a CompareRouteOutcome.
    The route in main_web.py translates the outcome into a FastAPI response."""
```

The /compare route in main_web.py would shrink from ~89 non-blank
lines to roughly 30 lines (auth + form + deps build + service call +
template render).

The `runtime_snapshot` latent bug fix is **included in 51C-2**: the
service will receive a `resolve_runtime_snapshot_source` callable in
the deps bundle and call it at the right point in the orchestration
(mirroring /run's behavior).

## Guardrails

✅ Did NOT change production code.
✅ Did NOT refactor /compare.
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
✅ /run route from Phase 51B remains thin (76 lines).
✅ PR #299 remains draft / not merged.

## Recommended next phase

**Phase 51C-2** — `/compare` route vertical extraction into
`app/services/compare_service.py`, using the same behavior-first
approach as 51B:

1. Create `compare_service.py` with the API above.
2. Slim /compare route in main_web.py.
3. Fix the `runtime_snapshot` latent bug as part of the extraction
   (add proper `resolve_runtime_snapshot_source` resolution, mirroring
   /run).
4. Update Phase 50C/50D tests for the new contract (same relaxations
   as 51B).
5. Pin the new contract with a Phase 51C-2 test suite mirroring
   `test_phase51b_run_route_vertical_extraction.py`.
