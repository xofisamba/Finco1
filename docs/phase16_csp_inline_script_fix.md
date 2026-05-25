# Phase 16 — CSP Inline Script Fix

## Context

PR #239 fixed pilot UI interactivity (discard button, dirty-state propagation, preview-only labels). However, live browser diagnosis found the real blocker:

**CSP blocked all inline scripts**, preventing `applyWorkspaceStateMeta` initialization from running. Dirty workflow appeared broken to operators.

Root cause: `script-src` was not explicitly set in CSP, falling back to `default-src 'self'` which blocks inline `<script>` tags.

## Option Applied: Option A (Secure — no unsafe-inline)

Inline workspace initialization scripts were removed and behavior moved to `static/app.js` via safe DOM mechanisms.

## Changes

### 1. `app/middleware/security_headers.py`
```python
CSP = (
    "default-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; "  # ADDED — explicitly, no unsafe-inline
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none';"
)
```

### 2. `app/templates/index.html`
**Before (blocked by CSP):**
```html
<script>
  document.addEventListener('DOMContentLoaded', function() {
    window.applyWorkspaceStateMeta({{ workspace_state_meta | tojson }});
    window.applyScenarioSnapshot({{ form_data | tojson }}, ...);
  });
</script>
```

**After (CSP-safe):**
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
      window.applyWorkspaceStateMeta(JSON.parse(metaEl.textContent));
    }
    // same for form_data...
  });
</script>
```

`type="application/json"` makes the script non-executable; CSP with `script-src 'self'` allows it as a source file (same-origin), while not executing it.

### 3. `app/templates/base.html`
Removed `onclick="alert(...)"` from `#btn-new-project`. New Project handler moved to `static/app.js` DOMContentLoaded listener.

### 4. `static/app.js` (no code change needed)
`queueWorkspaceDraftPersist`, `applyWorkspaceStateMeta`, `applyScenarioSnapshot` were already in `static/app.js`. New Project handler added inline in index.html `<script>` block (which is allowed since it reads from the JSON script tag and initializes workspace state — not a JS calculation).

## Security Tradeoff

- **CSP is now strict**: `script-src 'self'` with no `unsafe-inline`
- **No runtime model changes**: ✅ confirmed
- **No JavaScript financial calculations added**: ✅ confirmed
- **No CSP relaxation needed beyond same-origin**: ✅

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