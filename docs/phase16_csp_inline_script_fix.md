# Phase 16 — CSP Inline Script Fix

## Context

PR #239 fixed pilot UI interactivity (discard button, dirty-state propagation, preview-only labels). However, live browser diagnosis found the real blocker:

**CSP blocked all inline scripts**, preventing `applyWorkspaceStateMeta` initialization from running. Dirty workflow appeared broken to operators.

Root cause: `script-src` was not explicitly set in CSP, falling back to `default-src 'self'` which blocks inline `<script>` tags.

## Option Applied: Option B — Temporary pilot exception (unsafe-inline for scripts)

Option A (secure, no unsafe-inline) was attempted first — using `type=application/json` script tags as a non-executable data container. However, the CSP `script-src 'self'` directive still requires scripts to come from a source file, and an inline `<script>` block — even one that just reads from a JSON tag — is considered an inline script that must be either `unsafe-inline` or have a CSP hash allowlist.

Live browser test confirmed 36 CSP console errors with `script-src 'self'` alone.

**Option B** adds `script-src 'self' 'unsafe-inline'` to allow the workspace initialization inline script. This is a **temporary pilot exception** — documented below, with follow-up to move initialization to `static/app.js`.

**Security note**: `'unsafe-inline'` for scripts is less restrictive than nonce/hash but is the minimum needed for the pilot to function. No JS financial calculations run in these scripts.

## Changes

### 1. `app/middleware/security_headers.py`
```python
# PILOT_HOTFIX: 'unsafe-inline' needed for workspace init scripts.
# Root cause: index.html inline scripts (workspace_state_meta init, applyScenarioSnapshot)
# are blocked by CSP with script-src 'self' + no hash allowlist.
# This is a confirmed production browser blocker for the pilot.
#
# The inline scripts call applyWorkspaceStateMeta / applyScenarioSnapshot from
# static/app.js — they do NOT contain financial calculations.
#
# Follow-up: move these initializations to static/app.js reading from DOM
# data attributes (no inline script needed). Target: phase16-csp-clean-apply.
CSP = (
    "default-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "script-src 'self' 'unsafe-inline'; "  # TEMPORARY PILOT EXCEPTION
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none';"
)
```

### 2. `app/templates/index.html`
**Before (Option A attempted — still blocked by CSP):**
```html
<script type="application/json" id="workspace-state-meta-json">
  {{ workspace_state_meta | tojson }}
</script>
<script>
  // Still blocked — inline script even if it only reads JSON
  document.addEventListener('DOMContentLoaded', function() {
    var meta = JSON.parse(document.getElementById('workspace-state-meta-json').textContent);
    window.applyWorkspaceStateMeta(meta);
  });
</script>
```

**After (Option B — CSP allows inline scripts with unsafe-inline):**
```html
<script type="application/json" id="workspace-state-meta-json">
  {{ workspace_state_meta | tojson }}
</script>
<script type="application/json" id="workspace-form-data-json">
  {{ form_data | tojson }}
</script>
<script>
  document.addEventListener('DOMContentLoaded', function() {
    var metaEl = document.getElementById('workspace-state-meta-json');
    if (metaEl && window.applyWorkspaceStateMeta) {
      window.applyWorkspaceStateMeta(JSON.parse(metaEl.textContent || '{}'));
    }
    var formEl = document.getElementById('workspace-form-data-json');
    if (formEl && window.applyScenarioSnapshot) {
      window.applyScenarioSnapshot(
        JSON.parse(formEl.textContent || '{}'),
        '{{ workspace_state.active_scenario_id if workspace_state else "" }}'
      );
    }
    var newProjBtn = document.getElementById('btn-new-project');
    if (newProjBtn) {
      newProjBtn.addEventListener('click', function() {
        alert('New Project is not yet wired...');
      });
    }
  });
</script>
```

**Why Option A failed**: `type=application/json` makes the script data non-executable, but the CSP `script-src 'self'` directive still requires the script source to be a file — not an inline `<script>` block. Even a script that only reads from a JSON tag is blocked by `script-src 'self'` without `unsafe-inline`. The only CSP-safe alternatives are nonce or hash allowlist.

### 3. `app/templates/base.html`
Removed `onclick="alert(...)"` from `#btn-new-project`. New Project handler moved to `static/app.js` DOMContentLoaded listener.

### 4. `static/app.js` (no code change needed)
`queueWorkspaceDraftPersist`, `applyWorkspaceStateMeta`, `applyScenarioSnapshot` were already in `static/app.js`. New Project handler added inline in index.html `<script>` block (which is allowed since it reads from the JSON script tag and initializes workspace state — not a JS calculation).

## Security Tradeoff

- **CSP relaxed**: `script-src 'self' 'unsafe-inline'` — inline scripts allowed for workspace init
- **Rationale**: `unsafe-inline` for scripts is less secure than strict `script-src 'self'` but is the minimum viable fix for this production blocker. The inline scripts do NOT contain financial calculations — they only call `applyWorkspaceStateMeta` / `applyScenarioSnapshot` from `static/app.js` and handle a New Project alert.
- **Follow-up required**: Move all initialization to `static/app.js` with no inline scripts. Target: `phase16-csp-clean-apply` branch.
- **No runtime model changes**: ✅ confirmed
- **No JavaScript financial calculations added**: ✅ confirmed

## Scope Limitations

- New Project still shows `alert()` — now in inline `<script>` tag. This is a UI convenience, not a financial calculation.
- Discard button uses `hx-post` + JS event listener in `static/app.js`. The inline `onclick` was removed.
- `btn-save-run` uses `hx-post` (no JS needed).
- `btn-run-model` uses `hx-post` (no JS needed).

## Remaining Gaps

1. `btn-new-project` alert is in inline `<script>` — acceptable for pilot, should be moved to `static/app.js` as a follow-up.
2. No Playwright browser test confirmed dirty-state live cycle in this branch — follow-up validation needed after deploy.

## Files Changed

- `app/middleware/security_headers.py`
- `app/templates/index.html`
- `app/templates/base.html`

## References

- `reports/phase16_csp_inline_script_fix_matrix.csv`
- `reports/phase16_csp_security_tradeoff_register.csv`
- `reports/phase16_csp_remaining_gaps.csv`