# Phase 24C.1 / 24F Pilot Safety Decision

## Base SHA
`cf9e6e2ae94ca7fd0bd42f13252aa8e6502c535b` (after PR #323 merge)

## Decision pass scope
Inspect3 pilot-safety concerns before proceeding to Phase 24E.

---

## Finding 1: Frozen Excel schedule vs derived path warning

**File:** `app/templates/partials/debt_dscr_shl_panel.html`

**Current state:**
- ✅ "Frozen Senior DS Path" in sub-label
- ✅ "Fixture-backed · No sculpting" badge
- ✅ "No sculpting solver active" in tooltip
- ✅ "DSCR is backward-computed from frozen senior debt service" notice
- ❌ **NO warning** that editing/duplicating a fixture-backed project may not re-sculpt senior debt unless switched to derived/sculpted mode

**Classification:** Phase 24C.1 required fix — small UI warning addition.

---

## Finding 2: Generic/new project labeling

**File:** `app/templates/partials/new_project_form.html` + `app/ui/project_context.py`

**Current state:**
- Generic wind/solar templates exist (`generic_wind`, `generic_solar`)
- `data_source` field says "Generic wind template - user-project starter defaults"
- ❌ **NO visible warning** to users that generic projects are unvalidated / use derived sizing path
- ❌ **NO distinction** between Excel-parity-backed frozen path (TUHO/Oborovo) and derived/EBITDA-sizing path (generic)

**Classification:** Phase 24C.1 required fix — add "Unvalidated · Derived path" label to generic project selector.

---

## Finding 3: SQLite backup/restore

**File:** `app/persistence/db.py`

**Current state:**
- SQLite database exists at `FINCO_DB_PATH` (`finco_runs.db`)
- ❌ **NO backup/restore mechanism** in the app
- ❌ **NO export/import** of project/scenario state
- Scenario history is persisted but not exportable

**Classification:** Phase 24F backup/restore quick win — defer to after Phase 24E.

---

## Recommendation

| Phase | Action | Reason |
|-------|--------|--------|
| **24C.1** | Frozen-vs-derived warning + generic project labeling | Pilot-safety critical — user confusion risk |
| **24E** | Audit/Reconciliation Tab | Can start in parallel; doesn't conflict |
| **24F** | SQLite backup/restore | Important but not pilot-safety critical |

**Phase 24E is safe to start now** — the audit tab is independent of the frozen/derived warning.

**Recommended next branch:** `phase24c1-frozen-vs-derived-warning` (this branch)

---

## Phase 24C.1 implementation plan

1. Add warning to `debt_dscr_shl_panel.html`:
   - "Editing or duplicating a fixture-backed project will not re-sculpt senior debt. To use derived sizing, switch to a non-fixture project type."

2. Add "Unvalidated · Derived path" badge to generic project selector in `new_project_form.html` or template partial.

3. Add test in `test_phase24c1_*.py` verifying the warning text exists.

---

## Phase 24E status

**Safe to start concurrently** — Phase 24E (Audit/Reconciliation Tab) is independent of the frozen/derived path issue. It can be started on a separate branch while Phase 24C.1 is merged.

---

## Guardrails preserved

- ✅ No runtime formula changes
- ✅ No JS financial calculations
- ✅ G20 BLOCKED
- ✅ R99/R102 NOT APPROVED
- ✅ PR #299 remains draft
