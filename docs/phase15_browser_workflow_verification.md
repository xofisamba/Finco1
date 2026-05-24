# Phase 15 Browser Workflow Verification

## Scope

This branch adds the strongest available browser-workflow verification pack without introducing heavy browser automation dependencies.

The repository already proves backend and workflow integrity through repository-driven tests. This pack extends that coverage to the UI/HTMX honesty layer by checking:

- project-selection visibility
- dirty-state messaging and browser-side action blocking semantics
- HTMX rebinding hooks and editable-grid mirror synchronization
- save/revert browser guidance
- runtime/export/compare honesty copy
- mobile and narrow-viewport fallback styling

## Verification Approach

Real Playwright or Selenium automation was **not** added in this branch.

Reason:

- `requirements.txt` does not provide a browser automation dependency set
- adding a heavy browser stack would widen scope beyond the Phase 15 prerequisite
- the current repository can still support a meaningful browser-smoke suite by testing template, HTMX, JavaScript, and responsive semantics directly

This branch therefore uses a **strongest-available browser smoke substitute**:

- rendered UI surface checks through template coverage
- client-state hook checks in `static/app.js`
- responsive fallback checks in `static/styles.css`
- explicit remaining-gap reporting for future full browser automation

## Browser Workflow Coverage

The verification pack covers the guided internal pilot path at the browser-honesty layer:

1. project selection remains visible and reviewer-readable
2. editable-grid changes are clearly draft-only
3. dirty badge and unsaved-changes guidance remain visible
4. run / compare / save-run actions stay blocked while dirty
5. HTMX rebinding hooks remain idempotent and mirror inputs stay synchronized
6. save and revert guidance states that neither action auto-runs runtime
7. export lineage remains descriptive only and does not treat draft state as runtime truth
8. scenario compare remains descriptive only and excludes unsaved browser drafts
9. mobile fallback keeps grids scrollable and state strips readable

## Authority Boundaries Confirmed

- Runtime remains backend-authoritative.
- Frontend/browser state does not become runtime authority.
- Save does not auto-run runtime.
- Export does not auto-run runtime.
- Compare does not auto-save and does not auto-run.
- Dirty drafts are not exported or compared as runtime truth.
- Workbook/export remains descriptive and reviewer-facing.
- No JavaScript financial calculations were added.
- `audit_economic_mode` remains audit/reconciliation-only.
- `runtime_economic_mode` remains the only explicit runtime staging path.
- `G20` remains `BLOCKED`.
- `R99/R102` remain `NOT APPROVED`.

## Remaining Gaps

This branch does **not** claim full browser automation coverage.

Remaining future work:

- full Playwright or equivalent browser automation once dependency posture allows it
- true download-event verification in a live browser session
- real viewport interaction verification across desktop and mobile browsers
- cross-browser behavior checks beyond the current HTMX/template smoke layer

## Outcome

Phase 15 now has:

- repository-driven end-to-end workflow verification
- browser-honesty and HTMX/mobile smoke verification

That is enough for the current guided internal pilot entry checklist, while still documenting the remaining gap to full browser automation.
