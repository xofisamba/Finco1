# Phase 25B — Onboarding / Help / Demo Mode

## Base SHA
`a49236bb5b586c3523b23d7680fc065bacbc1fbb` (after PR #332 merge)

## Why Phase 25B

Phase 25A added a guided workflow stepper and limitations notice. Phase 25B adds a dedicated collapsible help/onboarding panel and a user-facing guide document so trusted pilot users can orient themselves without relying on trial and error.

Phase 25B follows Phase 24F.1 (auto-backup scheduling) and Phase 26A/B/C which established the security and mode boundary. It is purely product/help polish — no financial model changes.

---

## Scope

**In scope:**
- New `pilot_help_onboarding.html` partial (collapsible, included on Overview tab)
- New `docs/pilot_user_guide.md` (user-facing 1-page guide)
- This implementation doc
- Tests for new surfaces

**Out of scope:**
- No financial formula changes
- No runtime calculation changes
- No factory flag changes
- No fixture value changes
- No new auth or user roles
- No broad UI redesign
- No Shared LineItemGrid
- No generic debt validation
- No external validation claims
- No RBAC / multi-tenant / SSO / OAuth / SAML

---

## Help / Onboarding Partial

### `app/templates/partials/pilot_help_onboarding.html`

Collapsible panel included on the Overview tab (below the workflow stepper). Covers:

| Topic | Content |
|-------|---------|
| What is FincoGPT | Internal pilot tool, backend Python engine, browser is display-only |
| Validated templates | TUHO Wind ✅ Oborovo Solar ✅ generic projects ⚠️ |
| Demo / Pilot mode | TUHO/Oborovo are validated; generic is exploratory; single-user mode |
| Pilot workflow | 7-step summary (select → review → save → run → results → audit → export) |
| Audit / Parity | Internal review tooling, not certified audit; tolerance table |
| Export / Download | Based on last clean run; re-run if draft changed |
| Backup and restore | Auto-backup every 24h, 10 retained, manual/pre-restore not pruned |
| Limitations | No lender/bank approval, no external audit, no SaaS, not a sculpting solver |

Styling: muted background, collapsible via toggle button, warn/error callout styles for limitations.

---

## Pilot User Guide

### `docs/pilot_user_guide.md`

Non-technical 1-page user-facing guide. Sections:

1. What is FincoGPT?
2. Quick Start (7 steps)
3. Validated Scope (TUHO/Oborovo vs generic)
4. How to Read Results (KPIs + Audit/Parity)
5. Export and Download (with stale-run warning)
6. Backup and Restore (scope: internal recovery only)
7. What FincoGPT is NOT (claims table)
8. If Results Look Stale (re-run guidance)
9. Getting Help

---

## Tests

### `tests/test_phase25b_onboarding_help_demo_mode.py`

11 test cases covering:
- `pilot_help_onboarding.html` exists
- Help partial contains all core topics
- `pilot_user_guide.md` exists
- User guide includes quick start
- TUHO/Oborovo are listed as validated; generic as unvalidated
- Non-claims are explicit (no bank/lender/audit/SaaS)
- Export/stale-run guidance present
- Backup/restore guidance present (no enterprise DR claim)
- Single-user boundary stated
- No JS financial calculations added
- Guardrails unchanged (G20 BLOCKED, R99/R102 NOT APPROVED, partial_pay_sweep not promoted, flat/min DSCR not promoted)

---

## Guardrails Preserved

- No runtime formula changes
- No financial formula changes
- No model files changed
- No JS financial calculations
- No factory flag changes
- No fixture value changes
- No Revenue/OPEX/CAPEX/Tax formula changes
- No SHL/distribution logic changes
- No senior debt sizing logic changes
- G20 BLOCKED
- R99/R102 NOT APPROVED
- partial_pay_sweep not promoted
- flat/min DSCR sculpting not promoted
- Backend remains source of truth
- No lender/bank/audit/SaaS claims

---

## Recommended Next Phase

**Phase 26D — Deployment / Observability**
- Metrics, health checks, operational runbooks
- Readiness for trusted pilot deployment

**or**

**Phase 27 — Frozen-Path External Validation Pack**
- Formal validation documentation for TUHO/Oborovo outputs
- External stakeholder presentation pack
