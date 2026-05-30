# Phase 25A — Pilot Product Polish / Guided Workflow

## Base SHA
`8b07b18dff5edfdc806d6ae117a567179c8c2558` (after PR #329 merge)

## Why Phase 25A Follows Phase 26B

Phase 26B completed the auth/single-user mode boundary (pilot mode fail-fast on insecure secrets). Phase 25A follows naturally: with the security and honesty layer in place, the next step toward Trusted Pilot is improving the guided user experience — workflow clarity, limitations language, and empty/error states.

---

## Guided Workflow Steps

A new `pilot_workflow_guide.html` partial shows a 7-step horizontal stepper:

| Step | Label | Purpose |
|------|-------|---------|
| 1 | Select project | Choose TUHO/Oborovo template or generic |
| 2 | Review assumptions | Check inputs before running |
| 3 | Save scenario | Create a named snapshot |
| 4 | Run model | Backend calculates outputs |
| 5 | Review results | Check KPIs and DSCR |
| 6 | Review audit | Audit / Parity tab |
| 7 | Export | Downloads tab |

The stepper is included on the **Overview** tab of the workspace shell.

---

## Limitations Language

### New: `pilot_limitations_notice.html`

Shared partial included in the **Downloads** tab and available for reuse across views. States clearly:

| Claim | Status |
|-------|--------|
| TUHO/Oborovo frozen-template | ✅ Parity-validated |
| Generic projects | ⚠️ Unvalidated |
| Frozen Excel schedule | ❌ Not a sculpting solver |
| Bank/lender approval | ❌ Not provided |
| External audit / certification | ❌ Not provided |
| Multi-tenant / RBAC / Enterprise SaaS | ❌ Not implemented |

### Existing: `audit_reconciliation_tab.html`

Already contains an explicit disclaimer: *"This tab summarizes current parity evidence. It is not an external model audit, bank approval, lender approval, or certified audit."*

### Existing: `debt_dscr_shl_panel.html`

Already contains a frozen-vs-derived warning and fixture-backed notice.

---

## Empty / Error State Improvements

### New: `empty_states_notice.html`

Macro-based reusable partial providing clear copy for:

| State | Message |
|-------|---------|
| No scenario selected | Open a project and select/create a scenario to see outputs |
| No run yet | Save scenario → Run model; exports use last backend run, not unsaved edits |
| Unsaved edits | Draft differs from saved snapshot; run again to update outputs |
| Stale run | Outputs from previous run; re-run if draft changed after last run |
| No validation run | Validation results appear after a successful model run |
| No export available | Run the model first; exports use last backend run |
| Generic project | Unvalidated path; outputs should be reviewed independently |

### Updated: Distributions and Sponsor tabs

Placeholder copy updated to include limitations context (R99/R102 NOT APPROVED) rather than generic "Future phase" language.

---

## Export/Download Guidance

The **Downloads** tab already had good lineage context. Phase 25A strengthens it with:
- `pilot_limitations_notice.html` banner at the top of Downloads
- Export items already state: *"Uses the last clean backend runtime context. Save and run again before sharing if the current draft should be reflected."*

---

## JS Display-Only Policy

`static/app.js` remains display-only:
- No IRR, NPV, PMT, FV, PV calculations
- No Math.pow, Math.exp, Math.log for financial computations
- Only DOM manipulation, HTMX swaps, fetch calls, and state management

---

## What Remains Out of Scope

| Item | Reason |
|------|--------|
| Shared LineItemGrid | Refactor-oriented; not pilot-readiness critical |
| Generic project Excel validation | Separate workstream |
| Sculpting solver | Not implemented; frozen schedule is explicit |
| Full auth/RBAC | Phase 26B established boundary; enterprise features later |
| Enterprise SaaS | Single-user mode; multi-tenant deferred |
| CSS framework migration | No scope creep |

---

## Guardrails

- ✅ No runtime formula changes
- ✅ No financial formula changes
- ✅ No JS financial calculations
- ✅ No factory flag changes
- ✅ No fixture value changes
- ✅ No Revenue/OPEX/CAPEX/Tax formula changes
- ✅ G20 BLOCKED
- ✅ R99/R102 NOT APPROVED
- ✅ `partial_pay_sweep` not promoted
- ✅ `flat_dscr_sculpted` not promoted
- ✅ `minimum_dscr_sculpted` not promoted
- ✅ PR #299 remains draft / not merged / superseded
- ✅ Backend remains source of truth
- ✅ No lender/bank/audit/SaaS claims

---

## Changed Files

| File | Change |
|------|--------|
| `app/templates/partials/pilot_workflow_guide.html` | **NEW** — 7-step horizontal stepper |
| `app/templates/partials/pilot_limitations_notice.html` | **NEW** — shared limitations partial |
| `app/templates/partials/empty_states_notice.html` | **NEW** — reusable empty/error state macros |
| `app/templates/partials/workspace_shell.html` | Added workflow guide to Overview; improved placeholder copy; added limitations notice to Downloads |
| `docs/phase25a_pilot_product_polish_guided_workflow.md` | **NEW** |
| `tests/test_phase25a_pilot_product_polish_guided_workflow.py` | **NEW** — 10 tests |

---

## Recommended Next Phase

| Option | Description |
|--------|-------------|
| **A: Phase 26C — Deployment/CI/Config Hardening** | Docker, TLS, CI guardrails, production deployment |
| **B: Phase 24F.1 — Auto-Backup Scheduling** | Scheduled/automated SQLite backups |
| **C: Phase 25B — Onboarding / Help / Demo Mode** | User-facing help, demo workflow |

**Recommended: Option A (Phase 26C)** — Security and deployment hardening completes the pilot-readiness foundation before broader use.
