# Phase P2-FIX-3 — Test Report

**Branch:** `p2-fix-3-c2-first-edit-copy`
**Date:** 2026-06-11
**Author:** Mavis
**Status:** DRAFT PR #618 (not yet merged)

---

## 1. Test results

| Suite | Tests | Pass | Skip | Fail |
|---|---|---|---|---|
| `tests/test_phase_p2fix3_c2_first_edit.py` | 29 | 29 | 0 | 0 |
| `tests/test_phase_p2fix2_shell_strip.py` (regression) | 25 | 25 | 0 | 0 |
| `tests/test_phase51f_parallel_work_guardrails.py` (regression) | 21 | 21 | 0 | 0 |
| **Total** | **75** | **75** | **0** | **0** |

**75 / 75 PASS, 0 FAIL.**

P2-FIX-3 test breakdown:

| Test class | Tests | All pass? |
|---|---|---|
| `TestProtectedReferenceService` | 7 | ✅ |
| `TestOpenBehavior` | 4 | ✅ |
| `TestFirstEditGuard` | 4 | ✅ |
| `TestConfirmFirstEditCopy` | 5 | ✅ |
| `TestFixtureImmutability` | 3 | ✅ |
| `TestParityPreservation` | 2 | ✅ |
| `TestRenderedUI` | 2 | ✅ |
| `TestFileScope` | 1 | ✅ |

---

## 2. Persistence change (additive only)

**No schema migration. No new columns. No destructive updates.**

The C2 first-edit trigger uses the existing persistence layer
plus an additive `replay_metadata` extension:

| Field | Status |
|---|---|
| `is_readonly` | Existing; default False. New working copy sets it to False. |
| `project_origin` | Existing enum; new working copy uses `user_created`. |
| `template_source` | Existing; copied from source. |
| `replay_metadata` (JSON) | Existing JSON dict; new keys added for the C2 transition. |

`replay_metadata` new keys (additive, optional):

```python
{
    "export_type": "working_copy_from_protected_reference",  # NEW
    "source_project_code": "tuho",  # NEW
    "source_project_origin": "factory_template",  # NEW
    "created_via": "p2fix3_first_edit_confirmation",  # NEW
    "baseline_source": False,  # NEW
}
```

These keys are read defensively (`dict.get(key, default)`) by
the rest of the codebase, so old records without these keys
load correctly.

---

## 3. Open behavior (verified)

- `GET /?project=tuho` → 200, renders workspace. **No working
  copy is created.**
- `GET /?project=oborovo` → 200, renders workspace. **No working
  copy is created.**
- View, run, and export still work for the reference.

## 4. First-edit behavior (verified)

- `POST /scenarios/state/draft` with `active_project=tuho`
  → **409** with
  `{"error": "protected_reference",
   "needs_copy_confirmation": true,
   "message": "This is a protected reference project. Create an
   editable copy?"}`.
- Same for Oborovo.
- Generic Solar (factory template) → 200 OK (NOT a protected
  reference; can be edited directly).
- The 409 is the same on every attempt (fixture not mutated).

## 5. Copy creation behavior (verified)

- `POST /projects/tuho/confirm-first-edit-copy` → **302 redirect
  to `/?project=tuho-copy-{YYYYMMDDHHMMSS}`**.
- A new project record is created with
  `project_origin = "user_created"` and
  `is_readonly = False`.
- The new project has
  `replay_metadata.export_type = "working_copy_from_protected_reference"`.
- The new working copy is editable (draft save returns 200).
- Same for Oborovo.

## 6. Fixture immutability proof (verified)

- `test_tuho_baseline_snapshot_unchanged_after_copy`: After
  creating a working copy, the TUHO factory template's
  `baseline_snapshot`, `project_origin`, and
  `source_project_template` are byte-identical to before.
- `test_oborovo_baseline_snapshot_unchanged_after_copy`: same
  for Oborovo.
- `test_working_copy_does_not_share_state_with_source`: editing
  the working copy does NOT affect the source's workspace_state.

## 7. Parity proof (verified)

- `test_tuho_factory_path_still_resolves`: TUHO factory path
  renders the workspace without errors.
- `test_oborovo_factory_path_still_resolves`: same for Oborovo.
- All 21 Phase 51F parity guardrails still pass.

---

## 8. Files changed (4 files, +306 / -2)

| File | Status | Notes |
|---|---|---|
| `app/ui/protected_reference_service.py` | NEW (90 lines) | C2 protected reference helpers. |
| `tests/test_phase_p2fix3_c2_first_edit.py` | NEW (29 tests, ~750 lines) | All 29 tests pass. |
| `main_web.py` | MODIFIED (+89 lines) | Added C2 first-edit guard in `save_workspace_draft_endpoint` and new `POST /projects/{code}/confirm-first-edit-copy` route. |
| `docs/phase_p2fix3_reference_projects_c2.md` | NEW | Design + implementation doc. |
| `reports/phase_p2fix3_reference_projects_c2.md` | NEW | This report. |

No changes to:
- `app/services/scenario_state_route_service.py` (P2-FIX-2 file-scope)
- `app/persistence/` (no schema migration, no destructive updates)
- `app/waterfall_core.py`, `app/project_factories.py`,
  `app/excel_export.py` (P2-FIX-2 forbidden paths)
- `main_api.py` (P2-FIX-2 forbidden)
- `static/app.js` (P2-FIX-2 forbidden; 0 lines diff)
- Any other route / CSS class / context-key / project_origin renames

---

## 9. Hard constraints preserved (verified)

- ✅ rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` preserved
- ✅ TUHO parity netaknut
- ✅ Oborovo parity netaknut
- ✅ `use_construction_schedule_engine` = False
- ✅ No formula / debt / DSCR / tax / IDC / construction / R-PAR / C10 / R99 / R102 / G20 promotion changes
- ✅ No destructive persistence migration
- ✅ No `static/app.js` changes (0 lines diff)
- ✅ No `main_api.py` changes
- ✅ No new dependencies
- ✅ No Tailwind / Alpine / React / Vue / Svelte
- ✅ No Chart.js / Plotly / D3
- ✅ `factory_template` / `saved_baseline` literals still in `app/persistence/` (hidden != deleted)

---

## 10. Stop-after-report

- ✅ PR #618 is **DRAFT**
- ✅ Do NOT mark ready
- ✅ Do NOT merge
- ✅ Do NOT start P2-FIX-4 until P2-FIX-3 is approved
