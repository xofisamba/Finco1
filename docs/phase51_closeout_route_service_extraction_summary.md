# Phase 51 Closeout — Route service extraction summary and residual main_web hotspot map

## Current main SHA

`66d52dd74bd795639207140c63af8e7478741077` (origin/main @ PR #384 merge,
Phase 51D-2 /validate vertical extraction)

## Objective

Close out Phase 51 with a summary document that:

1. Captures the final state of the three Phase 51 vertical route
   extractions (`/run`, `/compare`, `/validate`).
2. Verifies the canonical route/service extraction pattern holds across
   all three extractions.
3. Confirms the three extracted routes remain thin and
   behavior-preserving.
4. Maps the remaining `main_web.py` god-module hotspots for the next
   phase (Phase 51E family).

This phase is **documentation and verification only**. No production
code, model output, runtime flag, fixture CSV, schema, migration,
JavaScript, or persistence behavior is changed.

## Phase 51 completed PRs

| Phase | PR | Title | Service module created | Route shrunk to |
|---|---|---|---|---|
| 51A | #379 | Phase 51A: /run route golden characterization | (none — characterization only) | (unchanged, ~380 non-blank pre-extraction) |
| 51B | #380 | Phase 51B: Extract /run route orchestration | `app/services/run_service.py` | thin route body |
| 51C-1 | #381 | Phase 51C-1: /compare route golden characterization | (none — characterization only) | (unchanged, ~89 non-blank pre-extraction) |
| 51C-2 | #382 | Phase 51C-2: Extract compare route orchestration | `app/services/compare_service.py` | thin route body (95 -> 36 non-blank) |
| 51D-1 | #383 | Phase 51D-1: Validate route golden characterization | (none — characterization only) | (unchanged, ~77 non-blank pre-extraction) |
| 51D-2 | #384 | Phase 51D-2: Extract validate route orchestration | `app/services/validation_service.py` | thin route body (77 -> 35 non-blank) |

Total: 6 merged PRs in Phase 51 (3 characterizations + 3 extractions).

## Final service modules

### `app/services/run_service.py` (Phase 51B)

Owns the orchestration body for `POST /run`. Three execution paths
(user_created, TUHO/Oborovo template-seeded, generic template-seeded).
Read-then-write: resolves runtime snapshot, executes model, persists
runtime to `record_workspace_runtime` and scenario state to
`update_scenario_last_run_summary`.

Public API:

```python
@dataclass
class RunRouteOutcome:
    template_name: str
    context: dict
    status_code: int = 200
    prepend_html: Optional[str] = None
    headers: dict = field(default_factory=dict)


@dataclass
class RunRouteDeps:
    collect_form_snapshot: Callable
    project_workspace_from_snapshot: Callable
    normalize_template_source: Callable
    canonical_project_type: Callable
    check_runtime_allowed: Callable
    resolve_runtime_snapshot_source: Callable
    build_schema_from_form: Callable
    validate_form: Callable
    format_kpis: Callable
    default_workspace_snapshot: Callable
    replay_metadata_for_project: Callable
    governance_snapshot: Callable
    scenario_provenance_for_record: Callable
    run_project: Callable
    build_projectinputs: Callable
    build_projectinputs_from_snapshot: Callable
    record_workspace_runtime: Callable
    update_scenario_last_run_summary: Callable
    runtime_summary_to_dict: Callable
    snapshot_input_error: type


async def execute_run_route(*, request, form, user, deps) -> RunRouteOutcome:
    ...
```

### `app/services/compare_service.py` (Phase 51C-2)

Owns the orchestration body for `POST /compare`. Read-only: iterates
SCENARIOS (Base/Downside/Upside), executes model, captures 6 KPIs per
scenario, soft-error per scenario. Two explicit latent bug fixes from
Phase 51C-1: user_created NameError and saved_state resolved snapshot.

Public API:

```python
@dataclass
class CompareRouteOutcome:
    template_name: str
    context: dict
    status_code: int = 200
    headers: dict = field(default_factory=dict)


@dataclass
class CompareRouteDeps:
    collect_form_snapshot: Callable
    project_workspace_from_snapshot: Callable
    canonical_project_type: Callable
    normalize_template_source: Callable
    check_runtime_allowed: Callable
    resolve_runtime_snapshot_source: Callable
    build_schema_from_form: Callable
    build_projectinputs: Callable
    build_projectinputs_from_snapshot: Callable
    scenarios: list[str]
    project_types: list[str]
    snapshot_input_error: type
    run_project: Callable


async def execute_compare_route(*, request, form, user, deps) -> CompareRouteOutcome:
    ...
```

### `app/services/validation_service.py` (Phase 51D-2)

Owns the orchestration body for `POST /validate`. Read-only: three
validation stages (A: enum, B: numeric, C: schema build) with errors
accumulating, Stage C gated by `if not errors:`, catches `ValueError`
specifically (NOT bare `Exception`). Runtime-snapshot parity call
preserved exactly (snapshot captured, unused downstream).

Public API:

```python
@dataclass
class ValidateRouteOutcome:
    template_name: str
    context: dict
    status_code: int = 200
    headers: dict = field(default_factory=dict)


@dataclass
class ValidateRouteDeps:
    collect_form_snapshot: Callable
    project_workspace_from_snapshot: Callable
    canonical_project_type: Callable            # NOT used; parity
    normalize_template_source: Callable         # NOT used; parity
    check_runtime_allowed: Callable
    resolve_runtime_snapshot_source: Callable   # parity call IS used
    build_schema_from_form: Callable
    validate_numeric_field: Callable             # per-field helper (Stage B)
    project_types: list[str]                     # PROJECT_TYPES
    scenarios: list[str]                         # SCENARIOS
    snapshot_input_error: type                   # NOT used; parity


async def execute_validate_route(*, request, form, user, deps) -> ValidateRouteOutcome:
    ...
```

## Route boundary pattern (canonical)

All three extractions follow the same shape:

1. **main_web.py** keeps the route **thin**:
   - auth/session wrapper (already route-owned)
   - `await request.form()`
   - constructing the `*RouteDeps` dataclass with all helpers from
     main_web's module scope
   - calling `await execute_*_route(request=..., form=..., user=..., deps=deps)`
   - rendering `templates.TemplateResponse(request, name=outcome.template_name, context=outcome.context, status_code=outcome.status_code)`

2. **Service module** owns the **orchestration body**:
   - form parsing semantics
   - project/workspace resolution
   - runtime guard semantics
   - validation / override construction
   - model execution (where applicable)
   - template response assembly
   - return value: a `*RouteOutcome` dataclass (NOT a Response)

3. **Dependency bundle** (`*RouteDeps`) injects main_web helpers:
   - One-way import direction: `main_web` -> service.
   - Service does NOT import main_web.
   - Service does NOT import main_api.
   - All helpers stay in main_web.py and are passed as callables.

4. **Backend remains source of truth**:
   - No JS-side financial calculations.
   - No new validation framework.
   - No new persistence helpers beyond what already existed.

## Final route-size summary

Post-extraction route line counts (from `main_web.py` after PR #384
merge at SHA `66d52dd74bd795639207140c63af8e7478741077`):

| Route | Service module | Non-blank body lines | Reduction |
|---|---|---|---|
| `POST /run` | `app/services/run_service.py` | ~65 (route-only, deps construction + service call) | ~388 -> ~65 (83% reduction) |
| `POST /compare` | `app/services/compare_service.py` | ~33 | 95 -> 33 (65% reduction) |
| `POST /validate` | `app/services/validation_service.py` | ~32 | 77 -> 32 (58% reduction) |

The reduction percentages differ by route because each route has
different helper call counts and docstring sizes, but all three are
clearly "thin" by Phase 51's threshold criteria.

## Behavior preservation summary

Across all three extractions, no production behavior was changed.
Specifically:

* ✅ **No financial formulas changed.** All formula code in
  `app/waterfall_core.py`, `app/project_factories.py`,
  `app/input_schema.py`, `app/input_adapter.py` is untouched.
* ✅ **No model output changes.** The model execution paths
  (`run_project`, `build_projectinputs`,
  `build_projectinputs_from_snapshot`) are passed in as deps; their
  semantics are unchanged.
* ✅ **No fixture CSV changes.** `git diff --name-only origin/main
  -- "*.csv"` is empty for any commit in Phase 51 except pre-existing
  reports/ files.
* ✅ **No schema / migration changes.** No Alembic, no SQL DDL, no
  Pydantic schema additions.
* ✅ **No new JavaScript financial calculations.** No `.js` files
  added or changed.
* ✅ **No runtime flag promotion.** G20, R99, R102, partial_pay_sweep,
  flat / min DSCR sculpting — all remain in their pre-Phase-51
  status (BLOCKED / NOT APPROVED / not promoted).
* ✅ **No lender / bank / audit / certification / SaaS claims.** No
  new README, no new doc copy, no new claim anywhere.
* ✅ **No persistence behavior changes.** `/run` continues to call
  `record_workspace_runtime` and `update_scenario_last_run_summary`
  through the deps bundle (not as direct calls in main_web). `/compare`
  and `/validate` remain read-only.

## Specific parity notes

### /run (Phase 51A → 51B)

* All 11 (`Phase 51A`) -> 11 (`Phase 51B`) integration tests passed.
* Stage 0 (auth), Stage 1 (form parse), Stage 2 (snapshot), Stage 3
  (runtime guard), Stage 4 (runtime snapshot), Stage 5 (three
  execution paths) all preserved.
* `prepend_html` (sessionStorage save script) is preserved on the
  user_created and template-seeded paths.
* Persistence side effects (`record_workspace_runtime`,
  `update_scenario_last_run_summary`) preserved.

### /compare (Phase 51C-1 → 51C-2)

* Two **explicitly allowed** bug fixes (per Phase 51C-1
  characterization):
  - **Bug A** — user_created path no longer raises NameError
    because `runtime_snapshot` is now resolved via
    `deps.resolve_runtime_snapshot_source` early in
    `execute_compare_route`.
  - **Bug B** — saved_state + active_scenario path now uses the
    resolved snapshot, not raw form values.
* Per-scenario soft-error semantics preserved (failing scenario
  becomes `{"error": str(e)}` and the loop continues).
* Read-only invariant preserved (no persistence side effects).

### /validate (Phase 51D-1 → 51D-2)

* **Runtime-snapshot parity call preserved EXACTLY** (per Phase 51D-1
  characterization requirement). The service:
  1. Calls `deps.resolve_runtime_snapshot_source(...)` when
     (saved_state + active_scenario_id) OR (user_created).
  2. Captures only the first tuple element as `runtime_snapshot`
     (annotated with `noqa: F841` to make the intentional
     non-use explicit).
  3. Does NOT use the captured snapshot downstream.
* Stage A -> B -> C order preserved exactly.
* Stage C only runs when Stage A and B have no errors (gated by
  `if not errors:`).
* Stage C catches `ValueError` specifically (NOT bare `Exception`).
* All 9 numeric max values preserved exactly:
  capacity_mw=2000.0, tariff_eur_mwh=1000.0, p50_hours=10000.0,
  total_capex_keur=1_000_000.0, opex_y1_keur=500_000.0,
  gearing_pct=100.0, target_dscr=10.0,
  interest_rate_pct=30.0, tenor_years=50.0.
* Read-only invariant preserved.

## Guardrails that remain true

* Generic solar / wind remain exploratory and unvalidated.
* G20 remains **BLOCKED**.
* R99 / R102 remain **NOT APPROVED**.
* `partial_pay_sweep` remains not promoted.
* flat / min DSCR sculpting remains not promoted.
* Backend remains source of truth (no JS-side financial calculations).
* `rc1` remains **frozen** and was not touched by any Phase 51 commit.
* PR #299 has been closed and is no longer treated as an active
  open/draft PR guardrail (per the explicit Phase 51 closeout
  context update).

## Test status

| Suite | Pass | Fail | xfail | Notes |
|---|---|---|---|---|
| Phase 51A (/run golden) | 25 | 0 | 0 | unchanged |
| Phase 51B (/run extraction) | 22 | 0 | 0 | unchanged |
| Phase 51C-1 (/compare golden) | 37 | 0 | 0 | xfail converted to passing (user_created NameError fix) |
| Phase 51C-2 (/compare extraction) | 49 | 0 | 0 | new |
| Phase 51D-1 (/validate golden) | 51 | 0 | 0 | structural tests re-pointed to validation_service.py |
| Phase 51D-2 (/validate extraction) | 52 | 0 | 0 | new |
| **Total Phase 51** | **236** | **0** | **0** | |

Local: `python -m pytest tests/test_phase51*.py` -> **236 passed**.

`import main_web`, `from app.services import run_service`,
`from app.services import compare_service`, and
`from app.services import validation_service` all work.

Structural guard tests all pass:
- `run_service.py` does NOT import `main_web` ✅
- `compare_service.py` does NOT import `main_web` ✅
- `validation_service.py` does NOT import `main_web` ✅
- `main_web.py` has zero direct `record_export(...)` calls ✅

## Known pre-existing issue

**`tests/test_persistence.py` and `tests/test_repository.py` fail to
collect with `ImportError: No module named 'persistence'`.**

* This is a pre-existing environment / refactor residue, NOT a
  regression introduced by any Phase 51 commit.
* Confirmed reproducible on `origin/main` HEAD (verified by
  `git checkout main && python -m pytest -m legacy_excel
  tests/test_persistence.py` -> same ImportError).
* Out of scope for Phase 51.

This issue is documented here for traceability but is **not part of
the Phase 51 deliverable**.

## Residual main_web.py hotspot map

After Phase 51D-2, `main_web.py` is **2893 lines** with 16
`@app.post(...)` routes and ~30 helper functions. The following
routes are the largest remaining hotspots, in order of body size
(non-blank lines as measured by structural inspection):

| Rank | Route | Line | Non-blank lines | Notes |
|---|---|---|---|---|
| 1 | `POST /download` | 1582 | 132 | Generates Excel export with current form values. Complex body, multiple scenarios. |
| 2 | `POST /save-run` | 2724 | 125 | Persists a model run to the database. Read-then-write with multiple side effects. |
| 3 | `POST /scenarios/save` | 2210 | 86 | Saves a scenario with full snapshot + provenance. |
| 4 | `POST /scenarios/{scenario_id}/duplicate` | 2340 | 65 | Duplicates a scenario with all overrides. |
| 5 | `POST /scenarios/add` | 2414 | 60 | Adds a new scenario to a project. |
| 6 | `POST /scenarios/{scenario_id}/rename` | 2595 | 49 | Renames a scenario. |
| 7 | `POST /projects/{project_code}/save-as` | 2544 | 47 | Saves a new project from current form values. |
| 8 | `POST /scenarios/{scenario_id}/archive` | 2651 | 45 | Archives a scenario. |
| 9 | `POST /scenarios/state/draft` | 2075 | 31 | Updates scenario draft state (small but persistence-heavy). |
| 10 | `POST /scenarios/state/discard` | 2111 | 29 | Discards scenario draft state. |
| 11 | `POST /scenarios/{scenario_id}/update-overrides` | 2513 | 23 | Updates scenario overrides. |
| 12 | `POST /scenarios/{scenario_id}/select` | 2487 | 19 | Selects active scenario. |

(Already extracted: `/run` ~65 non-blank, `/compare` ~33 non-blank,
`/validate` ~32 non-blank.)

Helper function clusters in `main_web.py` that may be candidates
for **decomposition** (not necessarily route extraction, but
isolating large helpers into modules):

| Helper | Line | Non-blank | Notes |
|---|---|---|---|
| `_project_baseline_snapshot` | 343 | 109 | Builds a project's baseline snapshot dict. |
| `_build_export_lineage_ui_context` | 699 | 94 | Builds the export lineage context for UI. |
| `_validate_new_project_payload` | 544 | 80 | Validates a new project payload. |
| `_collect_form_snapshot` | 267 | 74 | Collects form snapshot dict. |
| `_build_schema_from_form` | 1119 | 59 | Builds ProjectInputsSchema from form values. |
| `_replay_metadata_for_project` | 857 | 53 | Builds replay metadata for a project. |
| `_build_compare_ui_context` | 807 | 47 | Builds compare UI context. |

These helpers are passed as deps to the Phase 51 service modules
(where used) and remain in main_web module scope. They are not in
the critical path for the next route-family extraction but may be
candidates for future decomposition.

## Recommended next sequence

1. **Phase 51 closeout merge** — this PR (#385, the current closeout
   document) merges into main. No production code changes; this is
   documentation only.

2. **Claude / architecture review checkpoint** — pause and review
   the Phase 51 results. The pattern is now well-established with
   three concrete reference implementations. Confirm the pattern
   holds before scaling to the next route family.

3. **Phase 51E-1 — characterization of `POST /scenarios/state/draft`**
   — pin current behavior before any extraction. Mirror Phase 51A /
   51C-1 / 51D-1 structure: structural + integration tests,
   docs/phase51e1_*.md, reports/phase51e1_*_summary.json. Note that
   the route is only ~31 non-blank today, so this is a smaller
   hotspot than /download or /save-run, but it has persistence side
   effects (unlike /compare and /validate).

4. **Phase 51E-2 — vertical extraction of `POST /scenarios/state/draft`**
   — extract into `app/services/scenario_state_draft_service.py`
   (or similar). Same DI pattern as the three Phase 51 services.
   `/scenarios/state/draft` is a good first candidate for the
   scenario-route family because it's structurally simple and the
   persistence side effects are well-scoped.

5. **Continue with scenario save / duplicate / add routes** — after
   the state-draft pattern is proven, follow the same shape for:
   - `POST /scenarios/save` (Phase 51F-1 + 51F-2) — note this is
     larger (~86 non-blank) and has more side effects.
   - `POST /scenarios/{scenario_id}/duplicate` (Phase 51G-1 + 51G-2).
   - `POST /scenarios/add` (Phase 51H-1 + 51H-2).

6. **Then consider the download/save-run family** — these are
   larger and have more complex side effects:
   - `POST /download` (~132 non-blank, Excel export with multiple
     scenarios) — Phase 51I.
   - `POST /save-run` (~125 non-blank, persists model run) —
     Phase 51J.

7. **Consider helper decomposition** as a parallel track — the
   largest helpers in main_web.py (`_project_baseline_snapshot`,
   `_build_export_lineage_ui_context`, etc.) are not in the route
   extraction critical path but isolating them into helper modules
   would shrink `main_web.py` further and make it easier to read.

## Summary

Phase 51 successfully extracted three god-module routes from
`main_web.py` into service modules using a consistent
behavior-preserving pattern. All guardrails (no formula, model
output, fixture CSV, schema, JS, runtime flag, lender/bank/audit
changes) are preserved. PR #299 is no longer an active guardrail
(closed). `rc1` frozen code was not touched. 236 phase51 tests
pass.

The recommended next sequence is to characterize and extract
`POST /scenarios/state/draft` (Phase 51E-1 + 51E-2), then continue
through the scenario-route family, then consider the
download/save-run family and helper decomposition.

`/run`, `/compare`, and `/validate` now serve as the canonical
templates for the next phase. The pattern is: thin route (auth +
form + deps + service call + render), service owns orchestration,
deps bundle injects helpers from main_web module scope, one-way
import direction.
