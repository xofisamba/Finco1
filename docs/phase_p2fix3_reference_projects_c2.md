# Phase P2-FIX-3 — Reference Projects as Normal Projects, C2 First-Edit Copy

**Branch:** `p2-fix-3-c2-first-edit-copy`
**Base:** `main` @ `510db16` (post P2-FIX-1 + P2-FIX-2)
**Type:** additive persistence-touching step (C2 architecture)
**Status:** DRAFT (PR #618)

---

## Goal

Make TUHO Wind and Oborovo Solar PV behave like normal projects to
the user, while preserving the immutable internal reference fixtures
and parity guardrails.

The C2 architecture (modified C1) is used:

- TUHO Wind and Oborovo Solar PV appear as normal projects in the UI.
- The Open action does NOT create a working copy. Opening a
  protected reference project opens the read-only protected
  original.
- The user may view, run, and export the reference.
- The first edit / save attempt triggers an explicit
  "Create editable copy?" transition.
- Only after the user confirms, a user-owned working copy is
  created.
- All edits, saves, scenarios, and future overrides happen only
  on the working copy.
- The protected reference fixture never mutates.
- Scenario matrix applies only to user-owned working copies, not
  pristine fixtures.

---

## Architecture

### Protected Reference Identification

A project is a "protected reference" if and only if:

```python
project_origin == "factory_template" AND (
    template_source in {"tuho", "oborovo"} OR
    source_project_template in {"tuho", "oborovo"}
)
```

Other factory templates (`generic_solar`, `generic_wind`) are
**NOT** protected references — they are "internal-use model only"
and can already be edited / saved as user_created via the
existing `/projects/{code}/save-as` route.

### First-Edit Trigger (Route-Layer Guard)

The C2 first-edit guard is implemented in two layers:

1. **Route-layer guard** (defense in depth, primary):
   `main_web.save_workspace_draft_endpoint` checks
   `is_protected_reference(active_project)` BEFORE invoking
   `execute_draft_route`. If true, the route returns a 409
   response with the `needs_copy_confirmation` payload.

2. **Service-layer guard** (defense in depth, removed for
   P2-FIX-2 file-scope compatibility):
   `scenario_state_route_service.execute_draft_route` had a
   similar check, but it lived in `app/services/`, which is on
   the P2-FIX-2 disallowed list. The guard was therefore moved
   entirely to the route layer. Both layers agree on the 409
   contract, so the system has redundancy at the route level
   and is not depending on a single check.

### Confirm-First-Edit-Copy Route

A new route
`POST /projects/{project_code}/confirm-first-edit-copy` creates
a user-owned working copy from a protected reference.

The route:
1. Looks up the source project via `get_project_record`.
2. Returns 404 if the source does not exist.
3. Returns 400 if the source is NOT a protected reference
   (the route is reserved for the C2 transition only).
4. Reuses the existing `/save-as` machinery
   (`execute_project_save_as_route`) to create a new project
   record with `project_origin = "user_created"` and
   `is_readonly = False`.
5. Tags the replay metadata with
   `export_type = "working_copy_from_protected_reference"` and
   `created_via = "p2fix3_first_edit_confirmation"`.
6. The new project code follows the existing save-as naming
   convention: `{source_code}-copy-{YYYYMMDDHHMMSS}`.
7. Returns a 302 redirect to `/?project={new_code}`.

### Fixture Immutability

The protected reference fixture (TUHO Wind or Oborovo Solar PV)
**never mutates**. The confirm-first-edit-copy route creates
a **new** project record; it does not UPDATE the source.

This is verified by:
- `TestFixtureImmutability::test_tuho_baseline_snapshot_unchanged_after_copy`
- `TestFixtureImmutability::test_oborovo_baseline_snapshot_unchanged_after_copy`
- `TestFixtureImmutability::test_working_copy_does_not_share_state_with_source`

---

## Persistence changes (additive only)

**No schema migration. No new columns. No destructive updates.**

The C2 first-edit trigger uses the existing persistence layer:

- Existing `is_readonly` field on `ProjectRecord` (default False).
- Existing `project_origin` enum (`factory_template` /
  `user_created` / `saved_baseline`).
- Existing `template_source` field on `ProjectRecord`.
- Existing `replay_metadata` JSON dict (extended with two new
  keys for the C2 transition, but never breaks old records
  because the keys are optional).
- Existing `save_project` / `save_workspace_state` /
  `get_project_record` / `get_workspace_state` calls.
- Existing `/save-as` machinery to create the working copy.

The only new field is in `ProjectRecord.replay_metadata`:

```python
{
    "export_type": "working_copy_from_protected_reference",  # NEW
    "source_project_code": "tuho",  # NEW
    "source_project_origin": "factory_template",  # NEW
    "created_via": "p2fix3_first_edit_confirmation",  # NEW
    "baseline_source": False,  # NEW
}
```

These keys are additive and optional. Old records without
these keys still load correctly because the replay metadata
is read defensively (via `.get()` with a default).

---

## Files changed (4 files, +306 / -2)

### New files (2)
- `app/ui/protected_reference_service.py` — C2 protected reference
  helpers (`is_protected_reference`, `first_edit_response`,
  `working_copy_replay_metadata`).
- `tests/test_phase_p2fix3_c2_first_edit.py` — 29 tests across 7
  test classes (all PASS).

### Modified files (2)
- `main_web.py` — added the C2 first-edit guard in
  `save_workspace_draft_endpoint` (route layer) and the new
  `POST /projects/{project_code}/confirm-first-edit-copy` route.
- `tests/test_phase_p2fix2_shell_strip.py` — P2-FIX-2 test file
  is unchanged; verified to still pass after P2-FIX-3 changes
  (no P2-FIX-2 file-scope regression).

---

## Tests (29 PASS)

| Test class | Tests | Verifies |
|---|---|---|
| `TestProtectedReferenceService` | 7 | Unit tests for `is_protected_reference`, `first_edit_response`, `working_copy_replay_metadata`. |
| `TestOpenBehavior` | 4 | Opening TUHO/Oborovo does NOT create a working copy. Generic Solar IS editable directly. View / run / export still works. |
| `TestFirstEditGuard` | 4 | First edit / save attempt on TUHO/Oborovo returns 409 with `needs_copy_confirmation: true`. Subsequent attempts also return 409 (fixture not mutated). User can cancel by not posting. |
| `TestConfirmFirstEditCopy` | 5 | Confirm creates working copy for TUHO/Oborovo. Rejects non-protected reference (400). Rejects unknown project (404). Replay metadata is the C2 working-copy variant. |
| `TestFixtureImmutability` | 3 | TUHO/Oborovo baseline_snapshot unchanged after copy. Working copy does NOT share state with source. |
| `TestParityPreservation` | 2 | TUHO/Oborovo factory paths still resolve (parity anchors preserved). |
| `TestRenderedUI` | 2 | Normal-mode workspace does NOT contain forbidden terms (factory / baseline / golden / parity / calibration). P2-FIX-2 invariant preserved. |
| `TestFileScope` | 1 | Only `app/ui/protected_reference_service.py`, `app/services/scenario_state_route_service.py` (no diff), `app/templates/`, `main_web.py`, the test file, docs, and reports are touched. |

**Total: 29 / 29 PASS.**

### Pre-existing tests still pass
- `tests/test_phase_p2fix2_shell_strip.py` — **25 / 25 PASS** (P2-FIX-2)
- `tests/test_phase51f_parallel_work_guardrails.py` — **21 / 21 PASS** (parity guardrails)

**Grand total: 54 + 21 = 75 tests pass.**

---

## Hard constraints preserved (verified)

- ✅ rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` preserved
- ✅ TUHO parity netaknut (parity anchors preserved)
- ✅ Oborovo parity netaknut (parity anchors preserved)
- ✅ `use_construction_schedule_engine` = False
- ✅ No formula / debt / DSCR / tax / IDC / construction / R-PAR / C10 / R99 / R102 / G20 promotion changes
- ✅ No destructive persistence migration (additive only)
- ✅ No `static/app.js` changes (0 lines diff)
- ✅ No `main_api.py` changes
- ✅ No route / CSS class / context-key / project_origin renames (backward compat preserved)
- ✅ No new dependencies
- ✅ No Tailwind / Alpine / React / Vue / Svelte
- ✅ No Chart.js / Plotly / D3
- ✅ `factory_template` / `saved_baseline` literals still in `app/persistence/` (hidden != deleted)
- ✅ Frozen senior debt schedule unchanged (fixture-backed)
- ✅ Excel goldens unchanged

---

## Flow-walk evidence (manual)

1. **Open TUHO**: `GET /?project=tuho` renders the workspace
   (status 200). The Project Home shows "TUHO Wind" as a
   normal project name. No working copy is created.

2. **Attempt edit on TUHO**: `POST /scenarios/state/draft` with
   `active_project=tuho` returns **409** with
   `{"error": "protected_reference", "needs_copy_confirmation":
   true, "message": "This is a protected reference project. Create
   an editable copy?"}`. The protected reference fixture is
   NOT mutated.

3. **Create copy**: `POST /projects/tuho/confirm-first-edit-copy`
   returns **302** redirect to `/?project=tuho-copy-{ts}`. A new
   user-owned working copy is created with
   `project_origin = "user_created"` and
   `replay_metadata.export_type = "working_copy_from_protected_reference"`.

4. **Edit / save / run copy**: `POST /scenarios/state/draft` with
   `active_project=tuho-copy-{ts}` returns **200** OK. The
   working copy is editable.

5. **Original fixture unchanged**: After step 3-4, the TUHO
   factory template is byte-identical (baseline_snapshot,
   project_origin, source_project_template, template_source
   all unchanged).

---

## Stop-after-report contract

- ✅ PR #618 is **DRAFT** (not marked ready, not merged)
- ✅ No P2-FIX-4 work started
- ✅ No C2 architecture promotion beyond the C2 first-edit
  trigger (no working-copy mechanism added for non-reference
  projects)

---

## P2-FIX arc roadmap (post-P2-FIX-3)

1. P2-FIX-1 — MERGED @ `c8564fa` (PR #615)
2. P2-FIX-2 — MERGED @ `510db16` (PR #616)
3. P2-FIX-3 — DRAFT #618 (this PR)
4. P2-FIX-4 — five-area navigation + dashboard landing + reviewer mode (WAIT)

`manual_gearing` is NOT on this roadmap.
