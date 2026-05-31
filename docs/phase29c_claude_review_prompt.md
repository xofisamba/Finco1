# Phase 29C: Claude Review Prompt

Ready-to-copy prompt for Claude to review the finco1 codebase post-Phase 29.

---

## Prompt

```
You are reviewing the finco1 codebase — a financial model for renewable energy projects (solar/wind), built in Python/Streamlit with a .NET/SQLite backend.

## Current State

**Main branch SHA:** `6b9451ec8732d2543b53d88e130e5a61850641ab`

The codebase has been under active development since Phase 23. Key validated work includes TUHO (wind, Croatia) and Oborovo (solar, Croatia) frozen-template paths. Generic solar/wind projects are unvalidated.

## What I Need From You

### 1. Compare Against Phase 24/26A Review

A previous strict scoring review was done around Phase 24/26A. Compare the current state against that review:
- What has improved?
- What has regressed or stayed the same?
- What new blockers have appeared?

### 2. Score These Categories (1–10)

For each, give a score and a 1-sentence explanation:

- **Model accuracy** — TUHO/Oborovo frozen path fidelity to Excel
- **Validation quality** — evidence, anchors, documentation
- **CO2 revenue handling** — TUHO CO2 architecture and Y1 ~611 kEUR anchor
- **CAPEX/OPEX handling** — TUHO and Oborovo factories, Oborovo OpEx double-count gap
- **Debt/DSCR/SHL** — frozen senior DS, SHL calibration, distribution lockup
- **Generic path** — SOLAR-001/WIND-001 live sculpting, unvalidated status
- **Product completeness** — onboarding, backup, observability, auth
- **Security posture** — single-user auth, dependency pinning, no enterprise claims
- **Documentation quality** — phase docs, validation packs, readiness matrices

### 3. Estimate Completion % Toward These Milestones

- **Trusted pilot** (single user, frozen TUHO/Oborovo, no multi-user): __%
- **Paid pilot** (resolved OpEx gap, scenario persistence, no RBAC yet): __%
- **Internal working product** (all frozen paths validated, basic multi-user): __%
- **Full working product** (live sculpting validated, full OPEX parity): __%
- **Enterprise SaaS** (multi-user, RBAC, SSO, audit cert, deployment ready): __%

### 4. Assess These Specific Areas

**Codebase value and build cost:**
- How many lines of meaningful code were added since Phase 23?
- What is the implied build cost / value ratio?

**Validation quality:**
- Is the TUHO/Oborovo frozen path validation convincing?
- Are the anchors (debt, IRR, DSCR, CO2) well-documented?
- Is there a risk of overclaiming validation?

**Model risk:**
- What are the top 3 model risks (formula errors, data gaps, architectural issues)?
- Is the frozen vs. live path boundary clear enough to prevent misuse?

**Product readiness:**
- Is the product ready for a trusted pilot? What is missing?
- Is the product ready for a paid pilot? What must be resolved first?

**Deployment/operational readiness:**
- Is the deployment runbook complete?
- Is `/readyz` working properly?
- Are backup/restore procedures validated?

**Security/governance:**
- Is single-user mode properly bounded?
- Are there any security regressions since Phase 24/26A?
- Are guardrails (G20 BLOCKED, R99/R102 NOT APPROVED) properly enforced?

### 5. Top 10 Blockers

List the top 10 blockers in priority order. For each:
- What is it?
- Why is it blocking?
- What is the fix?

### 6. Proposed Roadmap (Next 5 Phases)

Based on your assessment, propose the next 5 phases in priority order. For each:
- What to do
- Why now
- What it unlocks

### 7. What Should NOT Be Built Yet

List things that are tempting but should NOT be built given the current maturity level. Be specific about why.

### 8. Explicit Scope Boundaries

Please explicitly confirm or correct these statements:
- ✅ TUHO frozen-template path is validated (debt, IRR, DSCR, CO2)
- ✅ Oborovo frozen-template path is validated (debt, distributions, SHL)
- ⚠️ Oborovo CAPEX sensitivity is diagnostic only (not Excel-validated)
- ⚠️ TUHO CO2 per-period is not exposed in output struct (co2_revenue_keur missing)
- ❌ Generic solar (SOLAR-001) is unvalidated
- ❌ Generic wind (WIND-001) is unvalidated
- ❌ Construction IDC (M1–M18) is not wired into runtime
- ❌ Live sculpting / debt re-sizing is not promoted
- ❌ Multi-user / RBAC / SSO is not implemented
- ❌ Enterprise SaaS / audit certification claims are not valid

If any of these are incorrect or misleading, correct them.

### 9. Guardrail Compliance Check

Confirm:
- G20 remains BLOCKED
- R99/R102 remain NOT APPROVED
- partial_pay_sweep is not promoted
- flat/min DSCR sculpting is not promoted
- No lender/bank/audit/SaaS/certification claims in the codebase
- Backend remains source of truth (no JS financial calculations)

---

## Context Files

If you are running in Claude with access to the codebase, the key files are:
- `docs/phase29c_post_validation_closeout.md` — this closeout summary
- `docs/phase27_frozen_path_external_validation_pack.md` — TUHO/Oborovo validation
- `docs/phase28_generic_project_path_validation.md` — generic path characterization
- `docs/phase29a_tuho_co2_revenue_deep_dive.md` — TUHO CO2 deep-dive
- `docs/phase29b_oborovo_capex_sensitivity.md` — CAPEX sensitivity diagnostic
- `docs/phase29c_readiness_matrix.md` — readiness matrix
- `app/project_factories.py` — TUHO and Oborovo factories (frozen path)
- `app/templates/partials/workspace_shell.html` — guardrail enforcement

---

## Your Response Format

Please structure your response as:

1. **Comparison vs Phase 24/26A** (bullets)
2. **Scores** (table: category | score | explanation)
3. **Completion estimates** (milestone | % | comment)
4. **Area assessments** (bullets per area)
5. **Top 10 blockers** (numbered list)
6. **Proposed roadmap** (numbered list with rationale)
7. **What not to build** (bullets with reasons)
8. **Scope boundary confirmation** (list any corrections)
9. **Guardrail compliance** (confirm or correct)
10. **Any other observations**

Be direct. Don't soften your assessment. If something is a 3/10, say so and explain why.
```