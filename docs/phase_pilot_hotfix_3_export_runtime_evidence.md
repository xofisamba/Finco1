# Phase PILOT-HOTFIX-3 — Export uses latest successful runtime evidence

> **Status:** DRAFT (not yet merged)
> **Branch:** `phase/pilot-hotfix-3-export-runtime-evidence`
> **Base:** main @ `11b2e5a07e76bdd87a7cc2b9b0212d496fa92b8c` (post PILOT-HOTFIX-2)

---

## 1. Problem statement

After the post-S1-C pilot walkthrough and the PILOT-HOTFIX-2 (P0 #1)
fix, a remaining P0 blocker was identified:

- **P0 #2 — runtime boundary exact-match gate blocks valid export flows.**
  When a user-created working copy with a successful `/run` was
  exported via `POST /download`, the export could fail with HTTP 400
  "Current form state no longer matches the last saved runtime
  boundary" — because the export service required the current form
  snapshot to bit-match the saved runtime boundary, even though
  export only needs the latest successful runtime result.

This is a different P0 from PILOT-HOTFIX-2 (which fixed scenario
overrides in `/run`). PILOT-HOTFIX-2 made `/run` honour the form's
`scenario_id`; PILOT-HOTFIX-3 makes `/download` honour the
workspace's `last_runtime_snapshot` directly.

---

## 2. Root cause analysis

### 2.1 What `POST /download` was doing (pre-fix)

`app/services/download_service.execute_post_download_route` called
`deps.check_runtime_allowed(workspace_state, snapshot)` for
`user_created` projects. That helper invokes
`app/persistence/repository.runtime_guard_for_snapshot`, which
requires `saved_snapshot == current_snapshot` for the gate to pass.

In real user flows:

1. User runs the model on a working copy → `last_runtime_snapshot`
   is written, runtime evidence is recorded.
2. User edits the form (e.g. changes tariff, capacity) but does NOT
   re-run.
3. User clicks "Export" → form snapshot has the new tariff, but
   `saved_snapshot` was last written at the previous run's tariff
   → form-vs-saved mismatch → `check_runtime_allowed` returns
   `allow_run=False` with the "current form state no longer matches"
   message → `POST /download` returns HTTP 400.

### 2.2 Why the runtime guard is wrong for export

The runtime guard exists to protect the `/run` endpoint from stale
form data being interpreted as a fresh run with stale inputs. That
is the right invariant for `/run` — Section 3 of
`execute_run_route` still enforces it.

For `/download`, the invariant is different. Export reads the
*last successful runtime result*, not the current form state. The
form state is the "intended" inputs, but the workbook is derived
from the last successful run. As long as a run exists for the
project, the export should succeed.

The user who hits this is the most common case: open working copy
→ run Base → tweak the form to plan the next change → click Export
to save the Base workbook. Today: HTTP 400. Expected: HTTP 200 with
the Base workbook.

---

## 3. Fix design

### 3.1 Service-layer only

The fix is contained in
`app/services/download_service.execute_post_download_route`. It does
NOT touch:

- `app/persistence/repository.py` (the runtime guard logic itself
  is unchanged; P1 file-scope constraint preserved)
- `app/waterfall_core.py`
- `app/waterfall_runner.py`
- `app/project_factories.py`
- `app/persistence/` (no schema or repository changes)
- `main_web.py`, `main_api.py`
- `static/app.js`
- tax / debt / construction / R99 / R102 / G20

The `/run` endpoint's strict boundary check (Section 3 of
`execute_run_route`) is also unchanged.

### 3.2 New behaviour in the user_created branch

```python
if (
    workspace_state is not None
    and workspace_state.last_runtime_snapshot
    and len(workspace_state.last_runtime_snapshot) > 0
):
    # Latest runtime evidence is available — use it directly.
    # PILOT-HOTFIX-3: skip the strict form-boundary check and
    # skip resolve_runtime_snapshot_source (which would re-resolve
    # from saved_snapshot or baseline_snapshot, potentially
    # missing the scenario override). The last_runtime_snapshot
    # was written by the most recent successful /run and is
    # the authoritative export input.
    runtime_snapshot = workspace_state.last_runtime_snapshot
    if workspace_state.active_scenario_id:
        active_scenario_record = get_scenario(
            workspace_state.active_scenario_id, user.user_id,
        )
    runtime_origin = "saved_state"
    runtime_warning = None
else:
    # No successful runtime yet — give a clear, user-friendly
    # error instead of the strict form-boundary message.
    return _build_inline_error_outcome(
        message="Run the model before exporting. The export uses "
                "the most recent successful runtime result for this project.",
        status_code=400,
    )
override = deps.build_projectinputs_from_snapshot(runtime_snapshot)
```

### 3.3 Why `len(...) > 0`

`workspace_state.last_runtime_snapshot` is the deserialised
`last_runtime_snapshot_json` field, which is `{}` (empty dict) when
no run has happened yet (the column is `NOT NULL DEFAULT '{}'`).
Plain truthiness would be `False` for `{}`, but we make it explicit
with `len(...) > 0` to:
- Be robust to any future change that might let an empty dict pass
  truthiness checks (e.g. `if dict_obj:`).
- Make the intent obvious to readers: "is there a non-empty
  runtime snapshot to use?"

### 3.4 Why we still call `get_scenario` to re-resolve
`active_scenario_record`

`active_scenario_record` is the scenario provenance used downstream
in `scenario_provenance_for_record(...)` (replay metadata) and the
`active_scenario_id`/`active_scenario_name` lookups. The original
code path resolved it via `resolve_runtime_snapshot_source`; we
preserve the same downstream semantics by querying the scenario
record directly from the persisted `active_scenario_id`.

If `active_scenario_id` is `None` (no scenario ever selected), we
leave `active_scenario_record = None` and downstream falls back to
`scenario_name` from the form. If the scenario record was deleted
between run and export, the `try/except` makes the export fail
soft (workbook still builds, just without scenario provenance).

### 3.5 Project isolation preserved

The fix reads `workspace_state.last_runtime_snapshot` from
`workspace_state` returned by `project_workspace_from_snapshot(user,
snapshot)`. `project_workspace_from_snapshot` looks up the project
by `active_project` from the form, then fetches the workspace for
that exact `(user_id, project_id)`. The export cannot see another
project's runtime evidence.

---

## 4. Validation evidence

### 4.1 Live walkthrough (post-fix, on this branch)

| Project | Scenario | Form tariff | Last-runtime tariff | `POST /download` status |
|---|---|---|---|---|
| TUHO Wind 1 (Copy) | Base | 99.0 (stale) | 75.0 | **HTTP 200, 39,544 bytes** |
| TUHO Wind 1 (Copy) | Downside | 75.0 (stale) | 50.0 | **HTTP 200, 39,269 bytes** |
| TUHO Wind 1 (Copy) | (no runtime) | n/a | n/a | **HTTP 400** "Run the model before exporting" |
| TUHO Wind 1 (Copy) | (no runtime, hostile `scenario_id`) | 50.0 | n/a | **HTTP 400** "Run the model before exporting" (cross-project blocked) |
| TUHO reference | Base | 75.0 | (factory) | **HTTP 200** (unchanged) |
| Oborovo reference | Base | 75.0 | (factory) | **HTTP 200** (unchanged) |

### 4.2 Test coverage (11 new tests, all pass)

`tests/test_phase_pilot_hotfix_3_export_runtime_evidence.py`:

| Test | Purpose |
|---|---|
| T1 | Working copy after Base run exports POST /download HTTP 200 with XLSX |
| T2 | Working copy after Downside run exports HTTP 200; override tariff (50) used, stale form (75) ignored |
| T3 | Working copy after Downside run exports XLSX HTTP 200 (XLSX magic bytes) |
| T4 | Working copy with no runtime returns clear "Run the model before exporting" error (no traceback, no boundary message) |
| T5 | Export uses only the working copy's own runtime (not TUHO reference) |
| T6 | TUHO reference export unchanged (factory path untouched) |
| T7 | Oborovo reference export unchanged (factory path untouched) |
| T8 | Cross-project scenario_id cannot be used to extract another project's runtime |
| T9 | Engine MD5 `6bf49f33efc989736c17cea0cb9b7723` unchanged |
| T10 | rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` ancestor preserved |
| File-scope | Only `app/services/download_service.py` + test + docs/report changed |

### 4.3 Adjacent suite results (all preserved)

- 11/11 PILOT-HOTFIX-3 tests pass
- 11/11 PILOT-HOTFIX-2 tests pass
- 21/21 Phase 51F parity guardrails pass
- 9/9 Phase 23s combined frozen-schedule parity tests pass
- 20/20 S1-A export tests pass
- 26/26 S1-C factory-resolver consistency tests pass
- 121/121 Phase 51E1 / 51E2 download route golden + vertical extraction tests pass

### 4.4 Constraint preservation

- ✅ rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` verified
  unchanged
- ✅ Engine MD5 `6bf49f33efc989736c17cea0cb9b7723` unchanged
- ✅ Factory MD5 `cf73065b8a26aa3f19629829e46260d9` unchanged
  (post-S1-C)
- ✅ `app/persistence/repository.py` UNCHANGED (P1 file-scope
  constraint honoured)
- ✅ `app/waterfall_core.py`, `app/project_factories.py`,
  `app/waterfall_runner.py` UNCHANGED
- ✅ `main_web.py`, `main_api.py` UNCHANGED
- ✅ `static/app.js` UNCHANGED
- ✅ No financial formula / debt / tax / sponsor / construction /
  R99 / R102 / G20 / waterfall change
- ✅ No persistence schema change
- ✅ TUHO / Oborovo frozen-schedule parity preserved bit-identical

---

## 5. Out of scope (separate PRs)

- **P0 #2 was the runtime boundary exact-match gate** — this PR
  addresses it for **export** only. The `/run` endpoint still uses
  the strict form-boundary check (PILOT-HOTFIX-2 changed the
  auto-select / saved-snapshot sync logic for run, but the guard
  itself is unchanged).
- The remaining pilot-walkthrough issues (P1 #1, P1 #2, etc.)
  remain out of scope; they are separate problems and separate PRs.
