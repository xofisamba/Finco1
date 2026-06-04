# Phase 54J — UI-2 Readiness Closeout and First Implementation Prompt Pack

## Context

Phase 54J closes UI-2 readiness and produces the exact prompt for
the first UI-2 runtime PR (UI-2.1 State clarity banner partial).
**No runtime code changes. Docs/report/test only.** This is the
final phase of the 54F-54J pre-implementation characterization
block.

## Current Main SHA

`f8390e423927c0d4acd9d247bfb6e83f975fd063` (post-54I merge)

## Summary of 54F-54I

### 54F — Template/context characterization

- 6 UI-2 items mapped to target templates
- 6 missing context keys identified
- Existing status patterns documented
- Must-not-change list extended

### 54G — Implementation boundary and test plan

- Per-UI-2-item: files allowed, files NOT allowed, allowed context
  keys, missing keys + workaround, allowed CSS class patterns,
  CSS/JS change policy, required tests, no-go copy checks, manual
  review checklist, rollback plan
- UI-2 auto-merge policy: NO for all 6 items
- Cross-cutting forbidden changes list

### 54H — UI no-go copy scanner specification

- 15 forbidden terms documented
- Current state of templates audited (clean)
- Allowed contexts (negation + qualification) defined
- Scanner implementation DEFERRED to 54H-2 or UI-3
- Manual no-go review per UI-2 PR is sufficient until automated

### 54I — PR sequence and manual review plan

- 6 UI-2 PRs in sequence with per-PR detail
- All 6 marked draft-only + auto-merge NO
- Stack policy: draft-only stacking allowed
- Manual review policy: user diff + rendered HTML + no-go + rollback + sign-off

## Final UI-2 boundaries (locked)

These are the locked boundaries for the 6 UI-2 PRs:

| Item | Files | Auto-merge | Draft-only | Stackable |
|---|---|---|---|---|
| UI-2.1 | _state_banner.html (NEW), index.html, workspace_shell.html, .banner-* | NO | YES | YES |
| UI-2.2 | _runtime_impact_chip.html (NEW), sheet_capex_detail.html, .chip-* | NO | YES | YES |
| UI-2.3 | _validation_summary_bar.html (NEW), audit_reconciliation_tab.html, .validation-summary-bar | NO | YES | YES |
| UI-2.4 | _factory_lock_indicator.html (NEW), workspace_shell.html OR index.html, .factory-lock-indicator | NO | YES | YES |
| UI-2.5 | index.html only (reuses stale_run() macro) | NO | YES | YES |
| UI-2.6 | _last_run_indicator.html (NEW), index.html + scenario_workspace.html + kpis.html, .last-run-indicator | NO | YES | YES |

## Final target templates (locked)

The 6 UI-2 PRs touch at most these templates (additive only):

- `app/templates/index.html`
- `app/templates/partials/workspace_shell.html`
- `app/templates/partials/sheet_capex_detail.html`
- `app/templates/partials/audit_reconciliation_tab.html`
- `app/templates/partials/scenario_workspace.html` (UI-2.6 only, optional)
- `app/templates/partials/kpis.html` (UI-2.6 only, optional)

**All other templates are NOT touched by UI-2.**

## Final context keys (locked)

| Key | Used by | Status |
|---|---|---|
| `banner_context` | UI-2.1 | NEW (parent template supplies) |
| `banner_data` | UI-2.1 | NEW (parent template supplies) |
| `runtime_impact` | UI-2.2 | existing |
| `sub_reason` | UI-2.2 | likely existing, verify |
| `validation_summary` | UI-2.3 | **MISSING** (workaround: compute in partial) |
| `is_factory_template` | UI-2.4 | **MISSING** (workaround: check data_source_label) |
| `inputs_changed_since_run` | UI-2.5 | **MISSING** (workaround: always show when runtime_summary exists) |
| `runtime_summary.run_id` | UI-2.6 | **MISSING** (workaround: omit) |
| `runtime_summary.ran_at` | UI-2.6 | existing |
| `runtime_summary.status` | UI-2.6 | existing |

## Final no-go copy scanner status

- **Spec:** complete (54H)
- **Implementation:** DEFERRED to 54H-2 or UI-3
- **Current enforcement:** manual no-go review per UI-2 PR
- **Templates current state:** CLEAN (no positive forbidden claims)

## Final manual review policy

Each UI-2.x PR requires:

1. User review of the diff
2. User review of rendered HTML
3. Confirmation that no-go copy checks pass
4. Confirmation that rollback plan is feasible
5. Sign-off before merge

## First implementation prompt: UI-2.1 State clarity banner partial

> **Phase UI-2.1: State clarity banner partial**
>
> You are implementing the first UI-2 runtime change. This is a
> docs-only / runtime-template change. **Open as DRAFT PR, not
> auto-merge.**
>
> **Branch:** `phase-ui2-1-state-clarity-banner`
> **Base:** `f8390e423927c0d4acd9d247bfb6e83f975fd063` (post-54I main)
> **Type:** runtime template change (additive only)
>
> **Files allowed to create:**
> - `app/templates/partials/_state_banner.html` (Jinja partial)
>
> **Files allowed to modify (additive only):**
> - `app/templates/index.html` (add `{% include "partials/_state_banner.html" %}` near the top, after the existing `gov-banner` block)
> - `app/templates/partials/workspace_shell.html` (add include if applicable)
> - `static/styles.css` (additive `.banner-*` classes only, at the end with `/* UI-2.1 banner */` comment)
>
> **Files NOT allowed to modify:**
> - Existing `gov-banner` block in `index.html`
> - CSS `:root` variables
> - Any other template
> - Any service file, persistence file, or `main_web.py`
> - `app/runtime_impact_taxonomy.py`
>
> **Banner partial spec (from 54C):**
> - 11 banner contexts: factory_template, user_created_project, active_scenario, saved_scenario, browser_draft, dirty_state, stale_result, last_run, validation_failed, display_only_row, pending_runtime_source
> - 5 tones: info, success, warn, fail, neutral
> - HTML structure: `<div class="banner banner-{tone}">` with icon, title, optional description, optional action
>
> **Allowed context keys:**
> - `banner_context: str` (one of 11)
> - `banner_data: dict` (optional, for placeholder substitution like `{timestamp}` and `{id}`)
>
> **Missing keys workaround:**
> - If `is_browser_draft` or `is_saved` not present, default to False, render conditionally
>
> **No-go copy checks (per 54C, 54H):**
> - No "bankable", "lender-ready", "certified", "audit-ready", "validated" (alone)
> - No "investor-ready", "SaaS-ready", "production-ready"
> - No "guaranteed returns", "investment advice", "customer reference"
> - "Active scenario" banner must NOT contain "real-time" or "live" (use "as you save")
> - Bar title: must use the 54C locked copy
>
> **Required tests:**
> 1. 11 string tests (one per banner context)
> 2. 5 tone tests (info, success, warn, fail, neutral)
> 3. No-go copy tests
> 4. Snapshot test (rendered HTML for at least 3 contexts)
> 5. Visual review (user reviews at least 3 contexts)
>
> **Manual review checklist:**
> - [ ] All 5 tones render with correct color
> - [ ] Icon visible in each context
> - [ ] Copy matches 54C locked spec exactly
> - [ ] No forbidden UI claims
> - [ ] Accessible (aria-label or role)
> - [ ] No regression in existing `gov-banner`
>
> **Rollback plan:**
> 1. Revert include in `index.html` and `workspace_shell.html`
> 2. Delete `app/templates/partials/_state_banner.html`
> 3. Revert added CSS
> 4. Run guardrails (51F, 52F, 53I, 54x) to confirm clean
>
> **Auto-merge:** NO. This is a runtime template change.
>
> **Stop conditions:** any test fails, any forbidden claim found,
> any forbidden file modified, CI/Parity fail, visual review fails.
>
> **Hard gates (universal):**
> - changed files are templates/CSS only (no service/persistence)
> - Phase 51F + 52F G1-G6 + 53I + 54x guardrails pass
> - rc1 (b425a07) untouched
> - No production code changed except allowed template/CSS
> - PR is mergeable as DRAFT (not auto-merged)
> - User has reviewed rendered HTML

## Second prompt preview: UI-2.2 Runtime Impact chip partial

> **Phase UI-2.2: Runtime Impact chip partial**
>
> You are implementing the second UI-2 runtime change. **Open as
> DRAFT PR, can be stacked with UI-2.1 as drafts.**
>
> **Branch:** `phase-ui2-2-runtime-impact-chip` (based on UI-2.1's branch, OR on main if UI-2.1 merged)
>
> **Files allowed to create:**
> - `app/templates/partials/_runtime_impact_chip.html` (Jinja partial)
>
> **Files allowed to modify (additive only):**
> - `app/templates/partials/sheet_capex_detail.html` (replace inline `badge-rt-*` chip with the include; **KEEP** the `_rt_tooltip(rt)` helper until new partial is verified)
> - `static/styles.css` (additive `.chip-*` classes only)
>
> **Chip spec (from 54C, 54D):**
> - 4 chip states: drives-model (green, ✓), display-only (slate, ◯), pending (amber, ⏳), needs-review (red, ⚠)
> - HTML structure: `<span class="chip chip-{state}" title="...">{label}</span>`
> - Tooltip: from 12 sub-reason text list in 54C
>
> **Allowed context keys:**
> - `runtime_impact: str` (one of 4 states)
> - `sub_reason: str` (optional, for tooltip)
> - `inline: bool` (optional, default False)
>
> **Required tests:** 4 string tests, 1 taxonomy test, 1 backward-compat test, no-go copy tests, visual review.
>
> **No-go copy:** chip labels must match 54C spec exactly, tooltips use locked 12 sub-reason text, no positive claims.
>
> **Auto-merge:** NO.

## Hard gates for UI-2 runtime PRs

Each UI-2.x PR must pass:

- ✓ changed files are templates/CSS only (no service/persistence)
- ✓ Phase 51F guardrails pass
- ✓ Phase 52F G1-G6 pass
- ✓ Phase 53I records guardrails pass
- ✓ Phase 54A-54J tests pass
- ✓ rc1 (b425a07) untouched
- ✓ No production code changed except allowed template/CSS
- ✓ No backend files modified
- ✓ No service files modified
- ✓ PR is mergeable (CI green)
- ✓ User has reviewed rendered HTML
- ✓ User has signed off

## Visual review checklist (per UI-2 PR)

- [ ] HTML variants render correctly
- [ ] No forbidden UI claims
- [ ] Copy matches 54C locked spec
- [ ] Tone colors match 54C spec
- [ ] CSS additions are additive and clearly marked
- [ ] No existing classes/helpers removed
- [ ] No backend files modified
- [ ] Rollback plan feasible

## Recommendation: stackable as draft-only?

**YES, UI-2.1 and UI-2.2 can be stacked as draft-only PRs.**

- Both are additive (no conflicts)
- UI-2.1 doesn't touch `sheet_capex_detail.html`
- UI-2.2 doesn't touch `index.html` or `workspace_shell.html`
- They share only `static/styles.css` (different class names)

**However, only ONE PR can be ready for review at a time.** This
means:

1. Open UI-2.1 as draft
2. Open UI-2.2 as draft (based on UI-2.1's branch, OR on main if UI-2.1 merged)
3. Mark UI-2.1 as ready for review
4. After UI-2.1 is approved and merged, mark UI-2.2 as ready

## Recommendation: start UI-2.1 or wait?

**Recommendation: WAIT for user/Claude review before starting UI-2.1.**

Rationale:

1. **First runtime change after long docs/spec phase.** UI-2.1 will
   be the first template modification in many months. User should
   approve the approach before implementation begins.
2. **Locked specs.** All 54F-54I specs are now locked. User
   should verify they are correct before code is written.
3. **Claude review recommended.** 7 questions from 53H-2 / 54E
   should be re-asked with the 54F-54I specs in mind.
4. **Pilot implications.** Even a banner partial is a user-facing
   change. Pilot users will see it. User should confirm the visual
   direction.

**Recommended next steps (in priority order):**

1. **User reviews 54F-54J specs** (this stack) — verify locked
   boundaries, context keys, no-go copy
2. **Optional: Claude review checkpoint** (7 questions) — second
   opinion on the 54F-54I specs
3. **After approval:** start UI-2.1 (state clarity banner partial)
4. **After UI-2.1 merge:** start UI-2.2 (runtime impact chip partial)
5. **Continue through UI-2.6**

If user wants to skip the Claude review and go directly to UI-2.1,
that's fine — the 54F-54I specs are sufficient. The recommendation
is to **at least do the user review**.

## Hard Gates (54J)

- ✓ Only docs/report/test files added
- ✓ No templates/CSS/JS/services/persistence changes
- ✓ Branch based on post-54I main `f8390e423927c0d4acd9d247bfb6e83f975fd063`
- ✓ Summary of 54F-54I provided
- ✓ Final UI-2 boundaries locked
- ✓ Final target templates locked
- ✓ Final context keys locked
- ✓ Final no-go copy scanner status documented
- ✓ Final manual review policy documented
- ✓ First implementation prompt for UI-2.1 complete
- ✓ Second prompt preview for UI-2.2 complete
- ✓ Exact hard gates for UI-2 runtime PRs
- ✓ Visual review checklist
- ✓ Recommendation: wait for user/Claude review before UI-2.1
- ✓ rc1 (b425a07) untouched

## Files Created in 54J

- `docs/phase54j_ui2_readiness_closeout_prompt_pack.md` (this file)
- `reports/phase54j_ui2_readiness_closeout_prompt_pack.json`
- `tests/test_phase54j_ui2_readiness_closeout_prompt_pack.py` (guardrail)
