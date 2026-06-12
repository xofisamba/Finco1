# Phase P2-FIX-6 — Execution Report

## Branch
- **Name:** `p2-fix-6-c2-create-copy-ui`
- **Worktree:** `.worktrees/p2-fix-6`
- **Base SHA:** `09ca2417bf1856803aeb9e0c3547af7877d53f8c` (post P2-FIX-5E)
- **PR:** #624 (DRAFT)
- **Type:** presentation only

## Implementation

### 1. `app/templates/partials/_state_banner.html` (M, +27)

Added a conditional CTA form inside the `factory_template`
banner block. The form POSTs to
`/projects/{active_project_code}/confirm-first-edit-copy`
which is the existing P2-FIX-3 backend route.

The button is gated by THREE conditions (all must hold):
1. `_ctx == 'factory_template'` — banner context indicates
   a non-user-created project is active
2. `is_protected_reference` — the project is TUHO or
   Oborovo (per `PROTECTED_REFERENCE_TEMPLATE_SOURCES`)
3. `not is_user_project` — the user is NOT already viewing
   a user-created working copy of the reference

The `data-p2fix6-cta="create-editable-copy"` marker is
present for testability and future analytics.

### 2. `main_web.py` (M, +7)

- Added global import: `from app.ui.protected_reference_service import is_protected_reference`
- Added `"is_protected_reference": is_protected_reference(project_record)` to the
  GET `/` render context (alongside `is_user_project` and
  `active_project_code` which were already present)

No financial logic, no route handler signature changes,
no model changes.

### 3. Test file (NEW, +311)

15 tests in 5 classes:
- 5 visibility tests (button present on TUHO/Oborovo,
  correct form attributes, marker present)
- 3 absence tests (button NOT on Generic Solar/Wind,
  no confirm link)
- 4 backend regression tests (C2 confirm route still
  works for protected, rejects non-protected, rejects
  unknown)
- 2 first-edit guard tests (P2-FIX-3 409 contract
  preserved for TUHO/Oborovo)
- 1 file-scope test (only allowed files changed)

### 4. Cross-arc allowlist patches (5 tests, +29)

Each of the 5 prior P2-FIX-* file-scope tests had to
gain the new P2-FIX-6 entry in their `allowed_prefixes`
tuple so the cross-arc CI is green.

## Test Results

- 15/15 P2-FIX-6 tests PASS
- 89/89 P2-FIX-{3,5B,5C,5D,5E,6} cross-arc PASS
- 21/21 Phase 51F parallel-work guardrails PASS

Total: **110+ tests green** for the stacked arc.

## Hard Constraints Preserved

- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` verified unchanged
- No `app/persistence/` changes
- No `app/services/` changes
- No `app/waterfall_core.py` changes
- No `app/project_factories.py` changes
- No `app/excel_export.py` changes
- No `app/capex_engine.py` changes
- No `app/ui/protected_reference_service.py` changes
- No `app/ui/project_review.py` changes
- No `main_api.py` changes
- No `static/app.js` changes
- No `static/styles.css` changes
- No formula / debt / DSCR / tax / IDC / construction / R-PAR / C10 / R99/R102 / G20 changes
- No schema migration
- No new dependencies

## Stop-after-report Contract

- This PR is DRAFT, not marked ready, not merged
- Do NOT start P2-FIX-7 until review/approval
- 5E merge SHA `09ca2417bf1856803aeb9e0c3547af7877d53f8c` is base
- P2-FIX-3 backend (route + service) is the source of truth
- P2-FIX-6 only renders the button — does NOT change the
  backend behaviour
