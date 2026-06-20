# External Pilot TUHO / Oborovo Reference Project UX Review

Scope: review how TUHO and Oborovo currently appear to external users, and
propose changes so they read as ordinary "Saved Projects" rather than
internal calibration/factory/baseline references. No code changes in this
doc.

## Current behaviour

- TUHO Wind and Oborovo Solar PV appear in `/projects/browse` as plain
  project names with no seed/factory/fixture suffix
  (`app/templates/partials/project_browser.html`, pinned by
  `tests/test_phase_p2fix5e_reference_ux.py`).
- Both are read-only in normal mode. Opening either does not silently
  create a working copy.
- The first edit or save attempt triggers the "C2 first-edit-copy" flow: an
  HX-Redirect (200 + header, not a 409) to
  `/projects/{code}/confirm-first-edit-copy`
  (`main_web.py` ~lines 4172-4250), which creates a user-owned copy with
  `project_origin="user_created"`, `template_source="tuho|oborovo"`. The
  original fixture is never mutated.
- The workspace shows a "Protected original" banner explaining the
  read-only behaviour and pointing to the editable-copy path
  (verified by `tests/test_phase_p2fix5e_reference_ux.py`
  `TestProtectedOriginalBanner`).
- Internal classification machinery (`protected_reference_service.py`,
  `is_protected_reference()`, `first_edit_response()` message text
  ~line 90-93) already uses external-friendly wording at the response
  level; the underlying classification values (`"factory_template"`) never
  reach rendered output.

## Proposed behaviour

| Aspect | Current | Proposed |
|---|---|---|
| Browse list label | Plain name, no badge | Keep plain name; optionally add a neutral "Saved Project" or "Example Project" badge (already used elsewhere per the terminology audit) instead of no badge at all, for parity with user-created projects |
| First-edit flow | "Protected original" banner + "editable copy" copy | Keep as-is — already external-friendly and tested |
| Internal CSS class names | `.ps-ap-origin--factory`, `.ps-ap-origin--baseline`, `.factory-lock-*` | Rename to `--template` / `--saved-base` / `protected-lock-*` (cosmetic only, tracked in terminology audit) |
| Conceptual framing | "Read-only reference/calibration fixture" | "Saved Project you can copy and customize" |

## Risks

- None of the proposed changes touch `project_origin`, `template_source`,
  or any persisted classification value — only display labels and CSS
  class names.
- TUHO/Oborovo parity tests (`tests/test_phase_p2fix5e_reference_ux.py`,
  parity-pinned fixtures) must continue to pass unchanged; none of the
  proposed wording changes touch the underlying fixture data or routing
  logic they protect.
- Renaming CSS classes must be done in templates and `static/styles.css`
  in the same commit to avoid orphaned selectors (already noted in the
  terminology audit).

## Migration path

1. Phase 1 (this sprint, optional safe cleanup): CSS class renames only —
   zero behavioural change, covered by existing tests.
2. Phase 2 (future): Decide on browse-list badge treatment (none vs.
   neutral "Saved Project" label) — requires a small UX decision, not
   urgent since current plain-name presentation already passes external
   clarity bar.
3. No phase requires touching `is_protected_reference()` logic, the
   first-edit-copy route, or TUHO/Oborovo fixture data.
