# Phase 54I — UI-2 PR Sequence and Manual Review Plan

## Context

Phase 54I defines the exact UI-2 PR sequence and manual review
process. **No runtime code changes. Docs/report/test only.**
Builds on 54F, 54G, 54H.

## Current Main SHA

`04aa09368ad22766f94dae0a3954c23975ba872d` (post-54H merge)

## UI-2 PR sequence (from 54E, locked by 54G)

The 6 UI-2 items in implementation order:

1. **UI-2.1** State clarity banner partial
2. **UI-2.2** Runtime Impact chip partial
3. **UI-2.3** Validation summary bar
4. **UI-2.4** Factory lock indicator
5. **UI-2.5** Stale result warning
6. **UI-2.6** Run-source indicator

## Per-PR detail

### UI-2.1 — State clarity banner partial

**Purpose:** Add a general-purpose banner partial that renders
state-clarity messages (factory, user, active, saved, draft, etc.).

**Expected changed files:**
- `app/templates/partials/_state_banner.html` (NEW)
- `app/templates/index.html` (additive: `{% include "partials/_state_banner.html" %}`)
- `app/templates/partials/workspace_shell.html` (additive, optional)
- `static/styles.css` (additive: `.banner-*` classes only)

**Tests required:**
- 11 string tests (one per banner context)
- 5 tone tests (info, success, warn, fail, neutral)
- No-go copy tests (no positive forbidden claims)
- Snapshot test (rendered HTML for at least 3 contexts)
- Visual review (user reviews at least 3 contexts)

**No-go copy checks required:**
- Manual checklist: 13 forbidden terms from 54C
- The "Active scenario" banner must NOT contain "real-time" or "live"

**Visual review checklist:**
- [ ] All 5 tones render with correct color
- [ ] Icon visible in each context
- [ ] Dismissable when applicable
- [ ] Accessible (aria-label or role)
- [ ] Copy matches 54C locked spec exactly

**Backend/context dependency:**
- `banner_context` (one of 11 strings) — supplied by parent template
- `banner_data` (optional dict for placeholder substitution) — supplied by parent template
- **Missing keys** (`is_browser_draft`, `is_saved`): use workaround (default False)

**Rollback plan:**
1. Revert include in `index.html` and `workspace_shell.html`
2. Delete `app/templates/partials/_state_banner.html`
3. Revert added CSS
4. Run guardrails to confirm clean

**Draft-only:** YES (open as draft)
**Auto-merge allowed:** NO (requires user review)

**Stackable:** YES as draft-only (UI-2.1 + UI-2.2 can be open as
drafts at the same time). NEVER stack auto-merges.

---

### UI-2.2 — Runtime Impact chip partial

**Purpose:** Replace the inline `badge-rt-*` chip in
`sheet_capex_detail.html` with a shared, standardized Runtime
Impact chip partial.

**Expected changed files:**
- `app/templates/partials/_runtime_impact_chip.html` (NEW)
- `app/templates/partials/sheet_capex_detail.html` (replace inline chip; KEEP `_rt_tooltip` helper until new partial verified)
- `static/styles.css` (additive: `.chip-*` classes only)

**Tests required:**
- 4 string tests (one per chip state)
- 1 taxonomy test (chip labels match `runtime_impact_taxonomy.py`)
- 1 backward-compat test (old `badge-rt-*` still works)
- No-go copy tests
- Visual review

**No-go copy checks required:**
- Manual: 13 forbidden terms
- Chip labels: must match 54C locked spec exactly ("Drives model", "Display only", "Pending", "Needs review")
- Tooltips: must use locked 12 sub-reason text from 54C

**Visual review checklist:**
- [ ] 4 chip variants render with correct color + icon
- [ ] Tooltip shows on hover (or title attribute)
- [ ] Inline and block variants both work
- [ ] Old `badge-rt-*` chips still render (backward compat)

**Backend/context dependency:**
- `runtime_impact: str` (4-state value) — supplied by child dict
- `sub_reason: str` (optional) — for tooltip, may not be present
- **Missing keys** (`sub_reason`): if not present, use just state label

**Rollback plan:**
1. Revert `sheet_capex_detail.html` to inline chip
2. Keep `_rt_tooltip` helper
3. Delete `app/templates/partials/_runtime_impact_chip.html`
4. Revert added CSS

**Draft-only:** YES
**Auto-merge allowed:** NO

**Stackable:** YES as draft-only (with UI-2.1)

---

### UI-2.3 — Validation summary bar

**Purpose:** Add a summary bar at the top of `audit_reconciliation_tab.html`
that shows pass/warn/fail counts and last-validated timestamp.

**Expected changed files:**
- `app/templates/partials/_validation_summary_bar.html` (NEW)
- `app/templates/partials/audit_reconciliation_tab.html` (additive: include at top)
- `static/styles.css` (additive: `.validation-summary-bar` classes)

**Tests required:**
- 4 string tests (one per tone)
- No-go copy tests
- Visual review
- **Optional:** integration test (render audit_reconciliation_tab.html with the bar)

**No-go copy checks required:**
- Bar title: must use "Internal validation summary" (not "Validation" alone, not "Audit summary")
- No "validated" / "audit-ready" / "certified"
- Tone descriptions: pass / warn / fail only

**Visual review checklist:**
- [ ] 4 tone variants render correctly
- [ ] Pass count, warn count, fail count display
- [ ] Timestamp displays correctly
- [ ] No forbidden claims
- [ ] Tone colors match 54C spec

**Backend/context dependency:**
- `validation_summary: dict` with `pass_count`, `warn_count`, `fail_count`, `last_validated_at`
- **Missing key:** `validation_summary`. **Workaround:** compute in partial from existing `audit_row_status` context. **Recommendation:** start with workaround, migrate to backend key in follow-up.

**Rollback plan:**
1. Revert include in `audit_reconciliation_tab.html`
2. Delete `app/templates/partials/_validation_summary_bar.html`
3. Revert added CSS

**Draft-only:** YES
**Auto-merge allowed:** NO

**Stackable:** YES as draft-only (with UI-2.1, UI-2.2)

---

### UI-2.4 — Factory lock indicator

**Purpose:** Show a "Factory template" lock indicator on factory
projects (TUHO, Oborovo).

**Expected changed files:**
- `app/templates/partials/_factory_lock_indicator.html` (NEW)
- `app/templates/partials/workspace_shell.html` (additive: include) OR `app/templates/index.html` (additive: include)
- `static/styles.css` (additive: `.factory-lock-indicator` class)

**Tests required:**
- 2 string tests (factory / not)
- No-go copy tests
- Visual review

**No-go copy checks required:**
- "Factory template" (allowed)
- "Frozen template" (allowed)
- "Source-locked" (allowed)
- NOT "validated factory" / "trusted template" / "certified source"
- NOT "approved factory" / "lender-grade template"

**Visual review checklist:**
- [ ] Both states (factory / not) render correctly
- [ ] Lock icon visible
- [ ] Tooltip explains "Source-locked / fixture-backed"
- [ ] No forbidden claims

**Backend/context dependency:**
- `is_factory_template: bool` — whether the current project is a factory template
- `factory_template_name: str` (optional) — e.g., "TUHO" or "Oborovo"
- **Missing key:** `is_factory_template`. **Workaround:** check `runtime_summary.data_source_label` for "TUHO" or "Oborovo". **Recommendation:** start with workaround, migrate to `is_factory_template` key in follow-up.

**Rollback plan:**
1. Revert include
2. Delete `app/templates/partials/_factory_lock_indicator.html`
3. Revert added CSS

**Draft-only:** YES
**Auto-merge allowed:** NO

**Stackable:** YES as draft-only (with UI-2.1, UI-2.2, UI-2.3)

---

### UI-2.5 — Stale result warning

**Purpose:** Show "Stale run" warning when there is a runtime
summary but the result may be stale. **Reuses existing
`empty_states_notice.html::stale_run()` macro.**

**Expected changed files:**
- `app/templates/index.html` (additive: import macro + call it)
- No new partial, no CSS changes

**Tests required:**
- 1 string test (verify `stale_run()` macro renders expected HTML)
- No-go copy tests
- Visual review

**No-go copy checks required:**
- Existing copy: "Stale run" + "⏱️" icon + warning text
- This copy is already approved (was added in `empty_states_notice.html`)
- No new copy in this PR

**Visual review checklist:**
- [ ] Banner shows when expected
- [ ] Copy is correct
- [ ] No forbidden claims
- [ ] No regression in other macros

**Backend/context dependency:**
- The `stale_run()` macro takes no arguments in its current form
- **Missing key:** `inputs_changed_since_run`. **Workaround:** always show the warning when there is a runtime summary but no fresh run indicator. **Verify with backend** (this is presentation only; backend may need to expose dirty state in a follow-up).

**Rollback plan:**
1. Revert include in `index.html`
2. No CSS to revert
3. No partial to delete

**Draft-only:** YES
**Auto-merge allowed:** NO

**Stackable:** YES as draft-only

---

### UI-2.6 — Run-source indicator

**Purpose:** Show "Last run: {timestamp} / Run ID: {id}" on
relevant views, as a compact indicator.

**Expected changed files:**
- `app/templates/partials/_last_run_indicator.html` (NEW)
- `app/templates/index.html` (additive: include)
- `app/templates/partials/scenario_workspace.html` (additive, optional)
- `app/templates/partials/kpis.html` (additive, optional)
- `static/styles.css` (additive: `.last-run-indicator` class)

**Tests required:**
- 2 string tests (with and without `runtime_summary`)
- No-go copy tests
- Visual review

**No-go copy checks required:**
- "Last run: {timestamp}" (allowed)
- "Run completed at {timestamp}" (allowed)
- NOT "Real-time" / "Live" / "Current run"

**Visual review checklist:**
- [ ] Indicator shows when `runtime_summary` exists
- [ ] Timestamp displays correctly
- [ ] No forbidden claims
- [ ] Indicator is small and unobtrusive
- [ ] Doesn't conflict with the existing `rs-provenance-banner` in `runtime_summary.html`

**Backend/context dependency:**
- `runtime_summary.ran_at`, `.status`, `.active_scenario_name`, `.data_source_label`
- `runtime_summary.run_id` (optional, may not be in current dict)
- **Missing key:** `runtime_summary.run_id`. **Workaround:** omit Run ID if not present, show only timestamp.

**Rollback plan:**
1. Revert includes
2. Delete `app/templates/partials/_last_run_indicator.html`
3. Revert added CSS

**Draft-only:** YES
**Auto-merge allowed:** NO

**Stackable:** YES as draft-only

---

## Stack policy

**Draft-only stacking is allowed** for UI-2 PRs. This means:

- UI-2.1, UI-2.2, UI-2.3, UI-2.4, UI-2.5, UI-2.6 can all be open
  as drafts at the same time
- Each PR is **based on the previous PR's head** (rebase required
  after each merge)
- Only **one** UI-2 PR is in "ready for review" state at a time
- Once a PR is approved, it merges, and the next PR rebases
- NEVER auto-merge any UI-2 PR

**Pattern:**

```
main
  └─ UI-2.1 (draft) ─┐
       └─ UI-2.2 (draft) ─┐
            └─ UI-2.3 (draft) ─┐
                 └─ UI-2.4 (draft) ─┐
                      └─ UI-2.5 (draft) ─┐
                           └─ UI-2.6 (draft) ─ ready
```

After each UI-2.x is approved, it merges. The next PR rebases
onto updated main.

## Manual review policy

Each UI-2.x PR requires:

1. **User review of the diff** (required for all 6 items)
2. **User review of rendered HTML** (screenshot or rendered output)
3. **Confirmation that no-go copy checks pass**
4. **Confirmation that rollback plan is feasible**
5. **Sign-off** before merge

The user (or Claude review) can:

- Approve as-is
- Request changes
- Reject and request re-design

## Cross-cutting tests (run before each UI-2 PR merge)

- All 51F guardrails
- All 52F G1-G6
- All 53I records guardrails
- All 54A-54H tests
- 54I tests (this phase)
- 54J tests (after this phase)

## Recommendation for 54J

Proceed to **Phase 54J — UI-2 readiness closeout and first implementation prompt pack**:

1. Summarize 54F-54I
2. Lock the final UI-2 boundaries
3. Produce the exact prompt for UI-2.1 (state clarity banner partial)
4. Produce a preview for UI-2.2 (Runtime Impact chip partial)
5. Document exact hard gates for UI-2 runtime PRs
6. Recommend whether to start UI-2.1 or wait for user/Claude review

## Hard Gates (54I)

- ✓ Only docs/report/test files added
- ✓ No templates/CSS/JS/services/persistence changes
- ✓ Branch based on post-54H main `04aa09368ad22766f94dae0a3954c23975ba872d`
- ✓ 6 UI-2 PR sequence with per-PR detail
- ✓ Expected changed files per PR
- ✓ Tests required per PR
- ✓ No-go copy checks per PR
- ✓ Visual review checklist per PR
- ✓ Backend/context dependency per PR
- ✓ Rollback plan per PR
- ✓ Draft-only / auto-merge policy per PR (NO for all)
- ✓ Stack policy: draft-only stacking allowed
- ✓ Manual review policy defined
- ✓ rc1 (b425a07) untouched

## Files Created in 54I

- `docs/phase54i_ui2_pr_sequence_manual_review_plan.md` (this file)
- `reports/phase54i_ui2_pr_sequence_manual_review_plan.json`
- `tests/test_phase54i_ui2_pr_sequence_manual_review_plan.py` (guardrail)
