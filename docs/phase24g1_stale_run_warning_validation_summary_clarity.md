# Phase 24-G-1 — Stale Run Warning + Validation Summary Clarity

> Type: UI-ONLY IMPLEMENTATION
> Status: DRAFT (not yet merged)
> Date: 2026-06-09
> Base SHA: `a421ab5` (post-pilot-readiness stack, after #564)
> Branch: `phase24g1-stale-run-warning-validation-summary-clarity`
> Source inventory: PR #564 (Phase pilot-ux-safe-track-inventory)
> Sprint: 24-G-1 (parallel to C10/R-PAR-2 chain, per PR #561 §4.2)

---

## 0. Purpose

Implement the first two items from the Pilot UX Safe Track
inventory (PR #564, composite scores 9 and 9):

1. **Stale run warning** — clearly visible warning when
   displayed outputs are older than current inputs.
2. **Validation summary clarity (Part 1)** — group validation
   messages by severity (Error / Warning / Information) and
   reduce duplicated wording.

Hard constraints (from the user request):
- No model / formula / tax / debt / depreciation / IDC changes
- No persistence changes
- No runtime changes
- No project status changes
- No Generic promotion
- No C10 promotion
- No construction flag changes
- UI-only (templates + CSS + tests)

Sprint plan position: **24-G-1 of the G (Pilot UX hardening)
track**, per PR #561 §4.2 (G runs in parallel with A/B/C/D/E
of the C10 chain).

---

## 1. Stale run warning — implementation

### 1.1 What was already there

- The `stale_run()` macro in
  `app/templates/partials/empty_states_notice.html` was already
  wired into `index.html` (Phase 25A / 55G work).
- The gate was already correct: it renders only when
  `workspace_state.dirty` AND
  `workspace_state.last_runtime_snapshot_id` are both present.
- The copy was conservative ("previous run", "run again",
  "export will use the last clean run") and matched the UI-2.5
  characterization test invariants.

### 1.2 What changed in Phase 24-G-1

1. **Visible "STALE" badge** — replaced the ⏱️ emoji icon with
   a styled `.esn-stale-badge` span that reads "STALE" in
   bold uppercase amber. Reason: the emoji was small and easy
   to miss on busy dashboards; a textual badge is
   unambiguous.
2. **Re-run anchor link** — added an `<a>` element that links
   to `#btn-run-model-sidebar` (the existing Run button in
   the sidebar). Reason: the user needs a one-click path to
   the action. The link is a plain anchor — no JS, no fetch,
   no auto-run, no form submit.
3. **What-changed hint** — added an optional
   `.esn-stale-changed` span that renders
   `workspace_state_meta.dirty_label` when it is non-empty.
   Reason: the existing `_workspace_state_meta()` already
   computes a `dirty_label` (e.g. "older than current draft (3
   fields changed)"); Phase 24-G-1 surfaces it next to the
   Re-run link, so the user knows *what* is stale.
4. **Macro signature** — `stale_run()` now accepts an
   optional `workspace_state_meta=None` keyword argument for
   forward compatibility. The default is `None`, so the
   "what-changed" hint renders only when the caller supplies
   a meta dict with a non-empty `dirty_label`. Callers that
   do not supply the argument continue to work (the macro
   renders without the hint).
5. **index.html call site** — `{{ stale_run() }}` was updated
   to `{{ stale_run(workspace_state_meta) }}` to pass the
   existing context variable.

### 1.3 What did NOT change

- The gate logic (`workspace_state.dirty` AND
  `last_runtime_snapshot_id`).
- The conservative copy ("Stale run", "previous run",
  "run again").
- The macro location (still in
  `empty_states_notice.html`).
- The macro being imported (not redefined) in `index.html`.
- Any backend service, persistence, model, formula, or
  runtime path.
- The `use_construction_schedule_engine` flag (still `False`).

### 1.4 CSS

All styles are additive — no `:root` modifications, no
removal of existing rules, no `.stale-result-*` class names
(those are still banned by the UI-2.5 test invariants).

New classes added:
- `.empty-state-notice--stale` (modifier on the container)
- `.esn-icon--stale` (icon container)
- `.esn-stale-badge` (the "STALE" badge)
- `.esn-stale-actions` (the action row)
- `.esn-stale-rerun` (the Re-run link)
- `.esn-stale-changed` (the what-changed hint)

All classes are pure-additive. The `:root` block count
remains at 5.

### 1.5 Test coverage

`tests/test_phase24g1_stale_run_warning.py` covers:
- STALE badge present and visible
- Re-run link uses an anchor (no JS, no fetch, no form)
- What-changed hint renders only when `dirty_label` is
  non-empty
- Original "Stale run" / "previous run" / "run again" copy
  preserved
- CSS additive (no `:root` mods, no forbidden class names)
- index.html still uses the existing macro and gate
- No production code change

---

## 2. Validation summary clarity — implementation

### 2.1 What was already there

- `_validation_summary_bar.html` already grouped by
  `pass_count` / `warn_count` / `fail_count` and used 4
  tones (pass / warn / fail / info).
- `validation.html` rendered a flat list of errors with no
  grouping, no dedup, and inconsistent visual hierarchy.

### 2.2 What changed in Phase 24-G-1

1. **Grouped rendering** — `validation.html` now groups
   messages by severity:
   - **Error** (red, with `!` icon and count badge)
   - **Warning** (amber, with `⚠` icon and count badge)
   - **Information** (blue, with `i` icon and count badge)
2. **Backward-compatible input** — the partial accepts:
   - Plain string errors (treated as `error` severity) — the
     existing `/validate` route produces this format.
   - Structured dict errors with `severity` and `message`
     fields — for forward compatibility with future
     validation routes that may emit structured issues.
3. **Deduplication (Error group only)** — repeated error
   strings are collapsed into one entry with a count badge
   `×N`. This reduces visual noise for the most common case
   (a missing field surfaced by multiple checks).
4. **Group structure** — each group has:
   - Header with icon, title, and count badge
   - Body with one row per item
   - Aria label for screen readers
5. **Original copy preserved** — the existing
   "Validation failed" / "Input checks passed" copy is kept
   at the top/bottom of the partial for backward-compat with
   existing characterization tests.

### 2.3 What did NOT change

- The `_validation_summary_bar.html` partial (untouched).
- The `/validate` route's input shape (still
  `valid: bool, errors: list[str]`).
- The `validation_service.py` logic.
- Any backend service, persistence, model, formula, or
  runtime path.
- The `use_construction_schedule_engine` flag (still `False`).
- The `validation_summary` context variable on the index
  page.

### 2.4 CSS

New classes added (all additive):
- `.validation-group` (container)
- `.validation-group--error` / `.validation-group--warning`
  / `.validation-group--information` (severity modifiers)
- `.validation-group-header` (header row)
- `.validation-group-icon` (severity icon)
- `.validation-group-title` (severity name)
- `.validation-group-count` (count badge)
- `.validation-group-body` (body)
- `.validation-item` (single message row)
- `.validation-item-message` (the message text)
- `.validation-item-count` (the `×N` repetition badge)
- `.validation-header` (top-level "Validation failed" header)

All classes are pure-additive. The `:root` block count
remains at 5.

### 2.5 Test coverage

`tests/test_phase24g1_validation_summary_clarity.py` covers:
- Plain string errors render as Error group
- Structured dict errors render in their severity group
- `warn` and `info` aliases are accepted
- Mixed severities are grouped separately
- Repeated errors are collapsed with a count badge
- Unique errors are not collapsed
- Each group has an icon, header, title, and count badge
- CSS additive (no `:root` mods, new classes exist)
- Original "Validation failed" / "Input checks passed" copy
  preserved
- No production code change

---

## 3. Test counts

| File | Count | Status |
|---|---|---|
| `test_phase24g1_stale_run_warning.py` | 19 | ✅ pass |
| `test_phase24g1_validation_summary_clarity.py` | 28 | ✅ pass |
| `test_ui2_5_stale_result_warning.py` (relaxed) | 48 | ✅ pass |
| `test_ui2_3_validation_summary_bar.py` (untouched) | 38 | ✅ pass |
| `test_ui2_1_state_banner_partial.py` (untouched) | 39 | ✅ pass |
| Other related UI-2.x tests | 153 | ✅ pass |
| **Total** | **325** | **✅ pass** |

---

## 4. Files changed

| File | Change | Why |
|---|---|---|
| `app/templates/partials/empty_states_notice.html` | macro enhanced | Stale run warning |
| `app/templates/partials/validation.html` | rewritten with grouping | Validation summary clarity |
| `app/templates/index.html` | `stale_run(workspace_state_meta)` | Pass context to macro |
| `static/styles.css` | new classes appended | Style the new UI elements |
| `tests/test_ui2_5_stale_result_warning.py` | relaxed 2 assertions | Allow Phase 24-G-1 macro change |
| `tests/test_phase24g1_stale_run_warning.py` | new | Test stale run warning |
| `tests/test_phase24g1_validation_summary_clarity.py` | new | Test validation summary clarity |
| `docs/phase24g1_*.md` | new | Documentation |
| `reports/phase24g1_*.json` | new | Machine-readable report |

No production code change:
- `main_web.py` — untouched
- `app/services/` — untouched
- `app/persistence/` — untouched
- `app/api/` — untouched
- `domain/` — untouched
- `tax_bridge/` — untouched
- `waterfall_core.py` — untouched
- `static/app.js` — untouched

---

## 5. Hard-rule coverage

| Hard rule | How this PR complies |
|---|---|
| No model changes | No `domain/`, `tax_bridge/`, `waterfall_core.py` change |
| No formula changes | No computation logic in templates |
| No tax/debt/depreciation/IDC changes | Templates are presentation only |
| No persistence changes | No `app/persistence/` change |
| No runtime changes | No `main_web.py` change, no service change |
| No project status changes | No `project_status` mutation |
| No Generic promotion | No `project_origin` mutation |
| No C10 promotion | No C10 field changes |
| No construction flag changes | `use_construction_schedule_engine` remains `False` |
| Stale warning does not alter calculations | Templates only read context |
| Stale warning does not trigger auto-runs | Anchor link, no JS / fetch / form |
| Stale warning disappears after successful run | `workspace_state.dirty` is cleared on run (existing backend behavior, not changed) |
| Validation groups by severity | Three groups: Error / Warning / Information |
| Reduces duplicated wording | Error dedup with `×N` count badge |
| Improves visual readability | Grouped headers with icons and count badges |
| No regression in existing UI tests | All UI-2.1..UI-2.5 tests pass (relaxed only where Phase 24-G-1 explicitly changes the macro) |
| TUHO parity unchanged | No model / formula / tax / debt / depreciation / IDC / persistence change |
| Oborovo parity unchanged | Same as above |
