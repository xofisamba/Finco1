# Phase 54G — UI-2 Implementation Boundary and Test Plan

## Context

Phase 54G defines exact implementation boundaries and tests for
each UI-2 runtime template change. **No runtime code changes. Docs/
report/test only.** Builds on 54F's template/context characterization.

## Current Main SHA

`cb9cad0c2693fff9e5dc2e0c13a1b85515fa73e6` (post-54F merge)

## UI-2 Item: State Clarity Banner Partial (UI-2.1)

### Files

**Allowed to create:**
- `app/templates/partials/_state_banner.html` (Jinja partial)

**Allowed to modify (additive only):**
- `app/templates/index.html` (add `{% include "partials/_state_banner.html" %}` near the top)
- `app/templates/partials/workspace_shell.html` (add include if applicable)

**NOT allowed:**
- Removing or rewriting existing templates
- Changing CSS variables
- Removing the existing `gov-banner` block
- Changing `static/styles.css` (UI-2.1 uses existing classes, OR may add new minimal classes — see below)

### Allowed context keys

- `banner_context: str` — one of: "factory_template", "user_created_project", "active_scenario", "saved_scenario", "browser_draft", "dirty_state", "stale_result", "last_run", "validation_failed", "display_only_row", "pending_runtime_source"
- `banner_data: dict` — additional data for placeholder substitution (`{timestamp}`, `{id}`, etc.)

**Missing key:** `is_browser_draft`, `is_saved` need backend verification
(see 54F § missing_context_keys). If backend doesn't expose them, the
partial must accept a default `False` and render conditionally.

### Allowed CSS class patterns

- `class="banner banner-{tone}"` where `tone` is one of: `info`, `success`, `warn`, `fail`, `neutral`
- New classes can be added to `static/styles.css` in a clearly marked `/* UI-2.1 banner */` block
- No modification of `:root` variables
- No modification of existing `.gov-banner`, `.error-banner`, etc.

### Whether CSS changes are allowed

**YES**, but only additive, minimal new classes. The pre-existing
`static/styles.css` is the **canonical CSS file**; new banner
classes go at the end with a clear comment block.

### Whether JS changes are allowed

**NO** in UI-2.1. Banner is a static partial.

### Required tests

1. **String tests:** Verify the partial renders expected HTML for each of the 11 banner contexts
2. **No-go copy tests:** Scan the partial for forbidden terms
3. **Snapshot test:** Capture rendered output and compare
4. **Visual review:** User reviews rendered output

### No-go copy checks

- `tests/test_phase54h_ui_no_go_copy_scanner.py` (if 54H implemented) will scan for forbidden terms
- Manual: review copy against the 11 locked banner contexts from 54C
- The "Active scenario" banner copy must NOT contain "real-time" or "live" — use "as you save" instead

### Manual review checklist

- [ ] All 11 banner contexts render correctly
- [ ] Tone colors match spec (info=blue, success=green, warn=amber, fail=red, neutral=slate)
- [ ] No forbidden UI claims
- [ ] Copy is from the locked 54C spec
- [ ] Dismissable when applicable (or not — TBD)
- [ ] Accessible (aria-* attributes)

### Rollback plan

- Revert the include in `index.html` and `workspace_shell.html`
- Delete `app/templates/partials/_state_banner.html`
- Revert any added CSS (if minimal, easy)
- Re-run guardrails to confirm clean

### Auto-merge policy

**NO.** First runtime template change after long docs/spec phase.

### Stop conditions

- Any test fails
- Any forbidden UI claim found
- Any forbidden file modified
- CI/Parity Guardrails fail
- Visual review fails

---

## UI-2 Item: Runtime Impact Chip Partial (UI-2.2)

### Files

**Allowed to create:**
- `app/templates/partials/_runtime_impact_chip.html` (Jinja partial)

**Allowed to modify (additive only):**
- `app/templates/partials/sheet_capex_detail.html` (replace inline chip with include; **keep** the `_rt_tooltip` helper until new partial is verified)
- `app/templates/partials/audit_reconciliation_tab.html` (optional: migrate "Drives model" `audit-row-status` to chip)

**NOT allowed:**
- Removing `_rt_tooltip` helper in `sheet_capex_detail.html` until new partial is verified
- Removing the `badge-rt-*` classes (backward compat)
- Changing `runtime_impact_taxonomy.py` (already correct)

### Allowed context keys

- `runtime_impact: str` — one of: "Drives model", "Display only", "Pending", "Needs review"
- `sub_reason: str` (optional) — for tooltip
- `inline: bool` (optional, default `False`) — if true, render inline (no block)

### Allowed CSS class patterns

- `class="chip chip-{state}"` where `state` is one of: `drives-model`, `display-only`, `pending`, `needs-review`
- Existing `.badge` and `.badge-rt-*` classes remain
- New `.chip` and `.chip-*` classes are added, NOT replacing `.badge`

### Whether CSS changes are allowed

**YES**, additive only. New `.chip` and `.chip-{state}` classes.

### Whether JS changes are allowed

**NO**.

### Required tests

1. **String tests:** Render the partial for all 4 states, verify HTML
2. **Taxonomy test:** Verify the 4 states from `runtime_impact_taxonomy.py` match the partial
3. **No-go copy tests:** No forbidden claims in chip copy
4. **Visual review:** User reviews the 4 chip variants

### No-go copy checks

- Chip labels: "Drives model", "Display only", "Pending", "Needs review" — from 54C spec
- Tooltips: must use locked 12 sub-reason text from 54C
- Must NOT use "validated", "audit-ready" anywhere

### Manual review checklist

- [ ] 4 chip variants render with correct color + icon
- [ ] Tooltip text matches 54C sub-reason spec
- [ ] Inline and block variants both work
- [ ] Old `badge-rt-*` chips still work (backward compat)

### Rollback plan

- Revert `sheet_capex_detail.html` to use inline chip
- Keep `_rt_tooltip` helper
- Delete `app/templates/partials/_runtime_impact_chip.html`
- Revert added CSS

### Auto-merge policy

**NO.**

### Stop conditions

- Same as UI-2.1, plus:
- Taxonomy test fails (chip labels don't match taxonomy)

---

## UI-2 Item: Validation Summary Bar (UI-2.3)

### Files

**Allowed to create:**
- `app/templates/partials/_validation_summary_bar.html` (Jinja partial)

**Allowed to modify (additive only):**
- `app/templates/partials/audit_reconciliation_tab.html` (add include at top)

**NOT allowed:**
- Changing `audit_reconciliation_tab.html` row content (only add the bar at top)
- Changing `validation_service` (UI-2.3 is presentation only)
- Backend changes (unless a `validation_summary` key needs to be exposed — see below)

### Allowed context keys

- `validation_summary: dict` with:
  - `pass_count: int`
  - `warn_count: int`
  - `fail_count: int`
  - `last_validated_at: str` (formatted timestamp)

**Missing key:** `validation_summary` needs backend addition.
**Workaround:** The partial can compute summary from existing
`audit_reconciliation_tab.html` context (counting PASS/WARN/FAIL
strings), OR be deferred until backend exposes it.

**Recommendation:** Start with the workaround (compute in partial or
in a small Jinja helper), then migrate to backend `validation_summary`
key in a follow-up.

### Allowed CSS class patterns

- `class="validation-summary-bar validation-summary-bar-{tone}"` where `tone` is one of: `pass`, `warn`, `fail`, `info`
- Existing classes remain

### Whether CSS changes are allowed

**YES**, additive only. New `.validation-summary-bar` classes.

### Whether JS changes are allowed

**NO**.

### Required tests

1. **String tests:** Render for 4 tones
2. **No-go copy tests:** No "validated" alone (must be "model check" / "internal validation")
3. **Visual review:** User reviews 4 tone variants

### No-go copy checks

- Bar title: "Internal validation summary" (not "Validation" alone, not "Audit summary")
- Tone descriptions: pass=green, warn=amber, fail=red
- No "audit-ready", "validated", "certified"

### Manual review checklist

- [ ] 4 tone variants render correctly
- [ ] Count and timestamp display correctly
- [ ] No forbidden claims
- [ ] Tone colors match spec

### Rollback plan

- Revert include in `audit_reconciliation_tab.html`
- Delete partial
- Revert added CSS

### Auto-merge policy

**NO.**

### Stop conditions

- Same as UI-2.1.

---

## UI-2 Item: Factory Lock Indicator (UI-2.4)

### Files

**Allowed to create:**
- `app/templates/partials/_factory_lock_indicator.html` (Jinja partial)

**Allowed to modify (additive only):**
- `app/templates/partials/workspace_shell.html` (add include)
- OR `app/templates/index.html` (add include)

**NOT allowed:**
- Removing the existing `pilot_limitations_notice.html` (it mentions factory template in text)
- Changing `data_source_label` (used by runtime_summary)

### Allowed context keys

- `is_factory_template: bool` — whether the current project is a factory template
- `factory_template_name: str` (optional) — e.g., "TUHO" or "Oborovo"

**Missing key:** `is_factory_template` needs backend verification.
**Workaround:** Use `data_source_label` from runtime_summary and check
if it contains "TUHO" or "Oborovo". OR defer until backend exposes it.

**Recommendation:** Start with workaround (check `data_source_label`),
then migrate to `is_factory_template` key in a follow-up.

### Allowed CSS class patterns

- `class="factory-lock-indicator factory-lock-indicator--{tone}"` where `tone` is `info` (or `neutral`)
- A lock icon (CSS-only, no JS)

### Whether CSS changes are allowed

**YES**, additive only. New `.factory-lock-indicator` class.

### Whether JS changes are allowed

**NO**.

### Required tests

1. **String tests:** Render for both `is_factory_template=True` and `False`
2. **No-go copy tests:** Lock indicator must NOT say "validated factory" or "trusted source" (use "Factory template" or "Frozen template")
3. **Visual review:** User reviews both states

### No-go copy checks

- "Factory template" (allowed)
- "Frozen template" (allowed)
- "Source-locked" (allowed)
- NOT "validated factory" / "trusted template" / "certified source"
- NOT "approved factory" / "lender-grade template"

### Manual review checklist

- [ ] Both states (factory and not) render correctly
- [ ] Lock icon visible
- [ ] No forbidden claims
- [ ] Tooltip explains "Source-locked / fixture-backed"

### Rollback plan

- Revert include
- Delete partial
- Revert added CSS

### Auto-merge policy

**NO.**

### Stop conditions

- Same as UI-2.1.

---

## UI-2 Item: Stale Result Warning (UI-2.5)

### Files

**Allowed to create:**
- **NONE** — reuses existing `empty_states_notice.html::stale_run()` macro

**Allowed to modify (additive only):**
- `app/templates/index.html` (add include `{% from "partials/empty_states_notice.html" import stale_run %}` and call `{{ stale_run() }}`)

**NOT allowed:**
- Modifying `empty_states_notice.html`
- Removing the existing macro

### Allowed context keys

- The `stale_run()` macro takes no arguments in its current form. If the implementation needs context, refactor carefully.

**Missing key:** `inputs_changed_since_run` for proper detection. The
workaround is to always show the warning when there is a runtime
summary but no fresh run indicator. **Verify with backend.**

### Allowed CSS class patterns

- Existing `.empty-state-notice` and `.empty-state-notice--warn` classes
- No new CSS needed

### Whether CSS changes are allowed

**NO** (uses existing classes).

### Whether JS changes are allowed

**NO**.

### Required tests

1. **String tests:** Verify `stale_run()` macro renders expected HTML
2. **No-go copy tests:** Existing copy is already safe
3. **Visual review:** User reviews the warning banner

### No-go copy checks

- Existing copy: "Stale run" + "⏱️" icon + warning text
- This copy is already approved (was added in `empty_states_notice.html`)

### Manual review checklist

- [ ] Banner shows when expected
- [ ] Copy is correct
- [ ] No forbidden claims

### Rollback plan

- Revert include in `index.html`
- No CSS to revert
- No partial to delete

### Auto-merge policy

**NO.**

### Stop conditions

- Same as UI-2.1.

---

## UI-2 Item: Run-Source Indicator (UI-2.6)

### Files

**Allowed to create:**
- `app/templates/partials/_last_run_indicator.html` (Jinja partial)

**Allowed to modify (additive only):**
- `app/templates/index.html` (add include)
- `app/templates/partials/scenario_workspace.html` (add include, optional)
- `app/templates/partials/kpis.html` (add include, optional)

**NOT allowed:**
- Removing the existing `rs-provenance-banner` in `runtime_summary.html`
- Changing `runtime_summary` dict shape
- Changing `run_service`

### Allowed context keys

- `runtime_summary.ran_at` (str, formatted timestamp)
- `runtime_summary.status` (str, "ok" or "error")
- `runtime_summary.active_scenario_name` (str, optional)
- `runtime_summary.data_source_label` (str, optional)
- `runtime_summary.run_id` (str, optional, may not be in current dict)

**Missing key:** `runtime_summary.run_id` may need backend addition.
**Workaround:** Use existing data only. The run ID can be added later.

### Allowed CSS class patterns

- `class="last-run-indicator last-run-indicator--{tone}"` where `tone` is `neutral` or `info`
- A small clock/run icon (CSS-only)

### Whether CSS changes are allowed

**YES**, additive only. New `.last-run-indicator` class.

### Whether JS changes are allowed

**NO**.

### Required tests

1. **String tests:** Render with and without `runtime_summary`
2. **No-go copy tests:** No "real-time" or "live"
3. **Visual review:** User reviews the indicator

### No-go copy checks

- "Last run: {timestamp}" (allowed)
- "Run completed at {timestamp}" (allowed)
- NOT "Real-time" / "Live" / "Current run"

### Manual review checklist

- [ ] Indicator shows when runtime_summary exists
- [ ] Timestamp displays correctly
- [ ] No forbidden claims
- [ ] Indicator is small and unobtrusive

### Rollback plan

- Revert includes
- Delete partial
- Revert added CSS

### Auto-merge policy

**NO.**

### Stop conditions

- Same as UI-2.1.

---

## Cross-cutting forbidden changes

These apply to ALL UI-2 items:

- **CSS `:root` variables:** not changed
- **Existing CSS classes (`.gov-banner`, `.badge-rt-*`, `.audit-row-status`, etc.):** not removed or modified
- **Existing Jinja helpers (`_rt_tooltip`):** not removed (may be deprecated in a follow-up after verification)
- **Existing `empty_states_notice.html` macros:** not modified
- **`runtime_impact_taxonomy.py`:** not changed
- **`runtime_summary` dict shape:** not changed
- **`run_service`:** not changed
- **Any service file:** not changed (UI-2.x is presentation only)
- **Any persistence file:** not changed
- **`main_web.py`:** not changed (route handlers unchanged)
- **No-go claims:** preserved
- **rc1 (b425a07):** untouched

## Required tests (per item, summary)

| Item | String | No-go copy | Snapshot | Visual | Taxonomy |
|---|---|---|---|---|---|
| UI-2.1 | yes | yes | yes | yes | n/a |
| UI-2.2 | yes | yes | yes | yes | yes |
| UI-2.3 | yes | yes | yes | yes | n/a |
| UI-2.4 | yes | yes | yes | yes | n/a |
| UI-2.5 | yes | yes | yes | yes | n/a |
| UI-2.6 | yes | yes | yes | yes | n/a |

## Manual review checklist (summary, per item)

Each item requires:

- [ ] All HTML variants render correctly
- [ ] No forbidden UI claims (per 54C list)
- [ ] Copy matches 54C locked spec
- [ ] Tone colors match 54C spec
- [ ] CSS additions are additive and clearly marked
- [ ] No existing classes/helpers removed
- [ ] No backend files modified

## Rollback plan (generic)

For each UI-2.x PR:

1. Revert the include in the parent template
2. Delete the new partial (if any)
3. Revert any added CSS
4. Run guardrails (51F, 52F, 53I, 54x) to confirm clean
5. Verify rc1 still untouched

## UI-2 auto-merge policy

**Default: NO** for all UI-2.x runtime template changes.

**Rationale:** First runtime change after long docs/spec phase.
Each PR must be reviewed by user before merge.

**Exception:** **None.** Even low-risk items (UI-2.5 stale warning)
require user review because they touch user-facing templates.

## Stop conditions (universal)

- Any test fails
- Any forbidden UI claim found
- Any forbidden file modified
- CI/Parity Guardrails fail
- Visual review fails
- Backend file changed (UI-2 is presentation only)
- Service file changed
- Template semantics changed (only additive includes allowed)
- `rc1` changed

## Recommendation for 54H

Proceed to **Phase 54H — UI no-go copy scanner specification**:

1. Specify the scanner approach
2. Decide whether to implement guardrail or defer
3. Document false positive strategy
4. Define scope (templates only, or also docs/reports)

## Hard Gates (54G)

- ✓ Only docs/report/test files added
- ✓ No templates/CSS/JS/services/persistence changes
- ✓ Branch based on post-54F main `cb9cad0c2693fff9e5dc2e0c13a1b85515fa73e6`
- ✓ Implementation boundaries defined for all 6 UI-2 items
- ✓ Allowed context keys specified
- ✓ Allowed CSS class patterns specified
- ✓ CSS / JS change policy per item
- ✓ Required tests per item
- ✓ No-go copy checks per item
- ✓ Manual review checklist per item
- ✓ Rollback plan per item
- ✓ Auto-merge policy: NO for all
- ✓ Stop conditions defined
- ✓ Cross-cutting forbidden changes listed
- ✓ rc1 (b425a07) untouched

## Files Created in 54G

- `docs/phase54g_ui2_implementation_boundary_test_plan.md` (this file)
- `reports/phase54g_ui2_implementation_boundary_test_plan.json`
- `tests/test_phase54g_ui2_implementation_boundary_test_plan.py` (guardrail)
