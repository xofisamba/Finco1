# Phase 57-pre — Route-render smoke and index context-contract tests

## Goal

Add broad `GET` route-render smoke coverage and a focused
`GET /` context-contract test, so that future UI / template
work (UI-3.1 LineItemGrid, the post-UX-cleanup token
consolidation, anything else) cannot ship a
`TemplateResponse` regression of the same shape as the 56H-1
`NameError` bug.

This is a **test/docs/report only PR**. No runtime code,
templates, CSS, JS, backend, service, persistence, schema,
or fixture changes.

## Why 56H-1 was missed

PR #475 (Phase 55G, merge `12b82ca9`) introduced
`banner_context` to the `index` route's `TemplateResponse`
context. The implementation referenced the bare name
`validation_errors` as the third argument to
`_banner_context_for_index(...)`, inside a dict literal:

```python
return templates.TemplateResponse(
    request=request, name='index.html',
    context={
        ...
        'validation_errors': [],            # ← key, not a binding
        ...
        'banner_context': _banner_context_for_index(
            project_record, workspace_state, validation_errors  # ← NameError
        ),
    },
)
```

Python does **not** bind dict-literal keys to names in the
enclosing scope. The bare-name reference therefore raised
`NameError: name 'validation_errors' is not defined` at
runtime, returning HTTP 500 on every `GET /` since the 55G
merge. The bug lived on `main` for **5 days** before the
post-merge visual QA pass (Phase 56H) caught it.

### Root cause: the 55G/55F/55E test gap

Every test in the 55G / 55F / 55E family imports the helper
function in isolation:

```python
# 55G test (paraphrased)
def test_helper_returns_none_for_missing_data():
    # Doesn't go through FastAPI; tests the helper in isolation
    assert helper(...) is None
```

None of them render the full `index` route via FastAPI's
`TestClient`. None of them invoke
`templates.TemplateResponse(...)` with the full context
dict. So the dict-literal reference was never executed
during the test run.

The CI / Parity Guardrails suite runs:

- Phase 51F parallel-work guardrails
- Phase 51M-1 / 51M-2 route golden characterization
- Phase 23A / 23C frozen Excel tests
- SHL waterfall, revenue, opex unit tests

…all of which test business logic, not HTTP response
rendering. The exception handler middleware catches
`NameError` and renders a JSON 500 body. So even the
readiness check (`/readyz`) didn't catch it because
`/readyz` doesn't render the `index` template.

The 56H-1 fix (PR #485, merge `3086a18`) hoists
`validation_errors` to a local variable before the context
dict, then binds the dict value to that local:

```python
validation_errors: list[str] = []  # ← hoisted
return templates.TemplateResponse(
    request=request, name='index.html',
    context={
        ...
        'validation_errors': validation_errors,  # ← bound
        ...
    },
)
```

## What the new smoke tests cover

### 1. Broad GET route smoke (15 routes, parametrized)

The test
`test_phase57pre_route_render_smoke::test_get_route_smoke`
exercises every safe GET route discoverable in
`main_web.py` with an authenticated test session, and:

- asserts the status is **not 500**;
- for HTML responses, asserts the body contains **no
  unhandled exception marker** (`Traceback`, `NameError`,
  `UnboundLocalError`, `Internal Server Error`,
  `ExceptionGroup`, `unhandled`, `exception_type=`).

### 2. Index context contract (10 focused tests)

`TestIndexContextContract` covers the specific 55E / 55F /
55G / 56E / 56F / 56H-1 context contract for `GET /`:

- `GET /` returns 200 when authenticated.
- Response includes at least one workspace marker
  (`ps-ap-name`, `data-tab="help"`, `banner-56f`,
  `panel-overview`, or `panel-help`).
- The 56H-1 NameError is gone.
- `banner_context` path does not crash.
- `runtime_summary` path does not crash.
- `validation_summary` path does not crash.
- The Help tab + project switch + state banner partials
  render (or are safely not rendered) without exception.
- Content type is `text/html`.
- `GET /?project=tuho` and `GET /?project=oborovo` both
  render.

### 3. 56H-1 regression pin (3 structural tests)

`Test56H1RegressionPin` pins the exact shape of the 56H-1
fix at the source level so a future refactor cannot silently
undo it:

- `validation_errors: list[str] = []` is declared as a
  local variable before the
  `templates.TemplateResponse(...)` call.
- The dict value is bound to the local variable
  (`"validation_errors": validation_errors,`).
- `_banner_context_for_index(...)` receives the local
  `validation_errors` as its third argument.

### 4. Guardrail tests (8 tests)

`TestGuardrails` confirms the 57pre PR did not touch any
runtime / template / CSS / JS / backend / service /
persistence / schema file. The full set of forbidden files
is listed in the test module.

### 5. Skip documentation (6 routes)

Routes that need a real `scenario_id` / `run_id` (or that
return binary streams) are documented in
`SKIPPED_ROUTES` with explicit reasons, so future
maintainers can extend the smoke suite safely.

### 6. rc1 status (3 tests)

`TestRc1Untouched` pins `b425a07` and asserts it is still
in the git history.

### 7. Closeout artifact presence (4 tests)

`TestCloseoutArtifacts` confirms the 57pre doc + JSON exist
and have the required sections / keys.

## Routes covered (15 GET routes)

| Path | Label | Auth | Tested |
|---|---|---|---|
| `/login` | login | no | ✅ |
| `/public-health` | public health | no | ✅ |
| `/readyz` | readyz | no | ✅ |
| `/health` | private health | yes | ✅ |
| `/` | index | yes | ✅ (also 10 focused tests) |
| `/download` | download GET | yes | ✅ status only |
| `/exports/runtime-summary.csv` | runtime summary CSV | yes | ✅ status only |
| `/exports/institutional-workbook.xlsx` | institutional workbook | yes | ✅ status only |
| `/projects/new` | new project form | yes | ✅ |
| `/projects/browse` | project browser | yes | ✅ |
| `/scenarios` | scenarios | yes | ✅ |
| `/scenarios/history` | scenarios history | yes | ✅ |
| `/scenarios/compare` | scenarios compare | yes | ✅ |
| `/runs` | runs list | yes | ✅ |

## Routes skipped and why

| Path | Skip reason |
|---|---|
| `/scenarios/{scenario_id}/load` | requires a real scenario_id; the smoke test would need to seed a scenario fixture. Future: add a real seed-scenario fixture and a parametrized test. |
| `/run/{run_id}` | requires a real run_id; the smoke test would need to seed a run. Future: add a real seed-run fixture and a parametrized test. |
| `/download` (binary) | returns a streaming XLSX response; status is checked but content is not asserted (asserting XLSX format / structure is the job of the run tests). |
| `/exports/runtime-summary.csv` (binary) | returns a streaming CSV response; status is checked but content is not asserted (asserting CSV format is the job of the export tests). |
| `/exports/institutional-workbook.xlsx` (binary) | returns a streaming XLSX response; status is checked but content is not asserted. |

These are documented in `SKIPPED_ROUTES` inside
`tests/test_phase57pre_route_render_smoke.py` and pinned
by `TestSkipDocumentation` so a maintainer who adds a new
GET route can see the convention immediately.

## How future UI PRs should use this test

Every UI / template / context-key PR (UI-3.1, post-UX
token consolidation, anything that adds or renames a
context key on the `index` route) **must** run the
following test list before requesting merge:

```bash
python -m pytest \
  tests/test_phase57pre_route_render_smoke.py \
  tests/test_phase56h1_index_validation_errors_hotfix.py \
  tests/test_phase56h_post_merge_visual_qa.py \
  tests/test_phase56g_ux_cleanup_closeout_visual_review.py \
  tests/test_phase56f_state_banner_visual_hierarchy.py \
  tests/test_phase56e_project_switch_simplification.py \
  tests/test_phase56d_cod_derived_field.py \
  tests/test_phase56c_new_project_v1_form_simplification.py \
  tests/test_phase56b_help_section.py \
  tests/test_phase55e_runtime_summary_index_context.py \
  tests/test_phase55f_validation_summary_context.py \
  tests/test_phase55g_banner_context.py \
  tests/test_phase54*.py \
  tests/test_phase51f_parallel_work_guardrails.py \
  tests/test_phase52f_persistence_guardrail_specifications.py \
  tests/test_phase53i4_records_relocation_closeout.py
```

The parametrized `test_get_route_smoke` will fail if any
of the 15 safe GET routes return 500 or include an
unhandled exception marker. The
`TestIndexContextContract` tests will fail if the `GET /`
context contract is broken. The `Test56H1RegressionPin`
tests will fail if the local-variable hoist is undone.

## UI-3.1 must include this smoke suite in its test list

**UI-3.1 LineItemGrid CAPEX summary pilot** (the first
post-56G UI work) MUST include this smoke suite in its
test list. The UI-3.1 branch will:

- Add a new `lineitemgrid.html` partial (CSS + template).
- Add a new context key on the `index` route (likely
  `lineitemgrid_summary` or similar).
- Possibly add a new `GET /lineitemgrid/...` endpoint
  (depending on the design).

Any of these can re-introduce the 56H-1 bug class. The
smoke suite is the canary.

### What UI-3.1 must add to the smoke suite

- The new endpoint(s) added by UI-3.1 (e.g.
  `/lineitemgrid/...`) must be added to `GET_ROUTES` in
  the test module.
- The new context key on `GET /` must be added to
  `TestIndexContextContract` (a test that asserts the
  response body includes a UI-3.1 marker, e.g.
  `class="lineitemgrid"`).
- The 56H-1 regression pin (3 tests) must continue to
  pass.

## What 57pre does NOT cover

- POST / PUT / DELETE / PATCH routes. They are tested
  in the run / save / scenario / project-create test
  suites. Adding a POST smoke pass would require
  building form-data fixtures for every route and is
  out of scope for 57pre.
- Streaming binary responses (CSV / XLSX) content. The
  smoke test only checks the not-500 invariant and the
  no-exception-marker invariant; format assertions are
  the job of the export tests.
- Routes requiring a real `scenario_id` / `run_id`. These
  need seed fixtures, which the integration tests already
  have.

## Recommendation

**UI-3.1 can start conditionally.** The 57pre smoke suite
is in place. UI-3.1 work must include the smoke suite in
its test list and add the new endpoint(s) / context key
to the parametrized table. The 56H-1 regression class
cannot re-reach main undetected by the 57pre suite.

If a future PR breaks the 57pre smoke suite, the PR is
rejected at the smoke-test step, before it reaches the
post-merge visual QA pass. This is the protection the
57pre PR adds.

## Hard no-go preserved

- No runtime code changes (only `tests/`, `docs/`,
  `reports/`).
- No templates / CSS / JS changes.
- No `app/waterfall_core.py` or `app/project_factories.py`
  changes.
- No `app/persistence/*` changes.
- No `app/services/*` changes.
- No schema / migration / fixture changes.
- No frontend dependencies added.
- No financial formula / model output changes.
- G20 BLOCKED, R99/R102 NOT APPROVED preserved.
- Generic Solar / Wind remain exploratory.
- Backend remains source of truth.
- No JS financial calculations.
- rc1 (`b425a07`) frozen.

## Files in this PR

| File | Change | Lines |
|---|---|---|
| `tests/test_phase57pre_route_render_smoke.py` | New | +600 |
| `docs/phase57pre_route_render_smoke_context_contract.md` | New | +250 |
| `reports/phase57pre_route_render_smoke_context_contract.json` | New | +120 |
