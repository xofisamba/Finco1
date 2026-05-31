# Phase 37 - Pilot UX Walkthrough / Friction Audit

## Summary

- **Base SHA:** `a46e117f48f4c37c5f600f4828c42763540f139c`
- **Phase type:** UX audit, documentation, tests, and small copy-only clarifications
- **Screenshots:** Skipped in this phase; this is a text-based walkthrough audit
- **Runtime / formula scope:** No financial formula changes, no runtime calculation changes, no model output changes, no schema migrations

## Scope

This phase reviews the trusted pilot journey for the currently validated frozen-template path:

- **Validated pilot scope:** TUHO and Oborovo frozen-template projects
- **Explicitly unvalidated / exploratory:** generic solar and generic wind projects
- **Non-claims preserved:** not lender-ready, not bank-approved, not externally audited or certified, not SaaS-ready, not enterprise-ready

This phase does not implement a broad UI redesign. Shared LineItemGrid work, large template refactors, navigation restructuring, and broader onboarding redesign are deferred.

## Methodology

The walkthrough was performed as a controlled review of the current pilot-facing flow and copy:

1. Review project selection and validated-scope messaging
2. Review assumption-editing and scenario-save guidance
3. Review dirty draft, saved snapshot, and runtime boundary language
4. Review run, runtime summary, validation, and DSCR/SHL surfaces
5. Review audit / reconciliation surfaces
6. Review scenario version history and stale-runtime warnings
7. Review export / download lineage language
8. Review pilot help, limitations, user guide, and deployment/runbook operator messaging
9. Note friction points, classify severity, and recommend only low-risk next steps

## Walkthrough Findings By Flow Step

### 1. Project selection

The app already contains the right substantive boundary: TUHO/Oborovo are trusted pilot templates and generic projects remain unvalidated. The friction is that this boundary was not consistently front-loaded in the shortest workflow hints. That increases the risk that an operator clicks into generic/new projects too casually.

**Phase 37 wording-only fix:** the workflow guide and help panel now say that TUHO/Oborovo are for trusted pilot runs, while generic projects are exploratory only.

### 2. Assumptions review

The user can review assumptions, but the pilot shell still relies on several different surfaces to explain what is editable, what is saved, and what is runtime-authoritative. The content is substantively correct; the friction is cognitive load, not missing logic.

### 3. Save scenario / versioning

Scenario save and version history semantics are present and well protected. The version history panel explains draft vs saved vs runtime behavior. The residual friction is that the user needs to mentally combine:

- the unsaved banner
- the state strip
- version history guidance
- export lineage guidance

That is workable for a guided internal pilot, but it is still heavier than ideal for an unassisted user.

### 4. Run model

The app correctly keeps the backend as the source of truth. Save does not auto-run and Run does not auto-save. Dirty draft state is clearly treated as separate from the last clean runtime.

This is a strength, but the wording is spread across multiple panels. The pilot operator likely understands it after a guided walkthrough, not instantly.

### 5. Runtime summary

The runtime summary exposes provenance labels and active scenario context. That is good. The friction is mostly explanatory density: users need to understand that the numbers come from the last clean backend run, not from the current browser draft.

### 6. Validation panel

The validation panel supports trust-building, but it sits alongside broader status language elsewhere in the workspace. The friction is not wrong output; it is that the app can feel like several different trust layers are speaking at once.

### 7. Debt / DSCR / SHL panel

This panel remains valuable for pilot review, but it is dense and specialist. For a trusted pilot operator, that is acceptable. For a non-specialist reviewer, it likely needs companion interpretation notes rather than more raw detail.

### 8. Audit / reconciliation tab

The audit tab is useful, but it mixes:

- validated frozen-path evidence
- generic-path warnings
- future / pending runtime items

That means the user must distinguish "good internal evidence for TUHO/Oborovo" from "not yet validated / not runtime-effective" rows. The tab is honest, but it is easy to over-read or misread without guidance.

### 9. Export / download

The export lineage panel is one of the strongest pilot trust surfaces in the app. It clearly ties exports to saved scenario boundaries and the last clean backend run.

The remaining friction is artifact ambiguity:

- "Parity Workbook"
- "Gap Register"
- "Source Map"

These names make sense to the team, but not necessarily to a pilot operator or reviewer without prior context.

### 10. Stale runtime / dirty draft state

This is covered well in substance. The remaining friction is repetition rather than absence. The user sees the same concept in several places, but each surface emphasizes a slightly different slice of the rule.

### 11. Backup / restore expectation

Operationally, backup language exists in docs and onboarding. The weak point is discoverability: the user is told restore exists, but the exact operator path is still more procedural than obvious. That is a documentation / operator-runbook issue, not a runtime issue.

### 12. Generic project warning / exclusion clarity

This remains the most important trust boundary. The app does say generic projects are unvalidated, but this must remain highly visible in any trusted pilot walkthrough, because using generic output as if it were validated would invalidate the pilot conclusion.

## Top Friction Findings

1. **Validated vs generic boundary still needs active operator emphasis**
   - Severity: High
   - Pilot blocker: **Yes, if generic projects are used for trusted pilot conclusions**

2. **Draft vs saved vs runtime semantics are accurate but cognitively heavy**
   - Severity: High
   - Pilot blocker: No, but this is a guided-pilot training risk

3. **Audit / Parity tab blends validated evidence with pending / unvalidated rows**
   - Severity: High
   - Pilot blocker: No, but easy to misread without facilitation

4. **Export artifact naming is team-friendly more than operator-friendly**
   - Severity: Medium
   - Pilot blocker: No

5. **Backup / restore discoverability is procedural rather than self-evident**
   - Severity: Medium
   - Pilot blocker: No

6. **Pilot-facing copy had visible encoding regressions on key screens**
   - Severity before fix: Blocker-level trust issue
   - Pilot blocker after Phase 37 copy cleanup: No

## Wording-Only Fixes Applied In Phase 37

These were intentionally small and non-behavioral:

- restored readable pilot-facing copy and symbols in:
  - `app/templates/index.html`
  - `app/templates/partials/pilot_workflow_guide.html`
  - `app/templates/partials/pilot_help_onboarding.html`
  - `app/templates/partials/pilot_limitations_notice.html`
  - `app/templates/partials/scenario_version_history.html`
  - `app/templates/partials/workspace_shell.html`
  - `docs/pilot_user_guide.md`
- clarified that:
  - TUHO/Oborovo are for trusted pilot runs
  - generic projects are exploratory / unvalidated
  - exports should follow a clean run
  - backup/restore is an internal recovery workflow, not enterprise DR

No layout, behavior, runtime, formula, or data-path logic was changed.

## Blocker Classification

### Trusted pilot blockers

- **Conditional blocker:** a pilot operator must not treat generic solar/wind outputs as validated
- **Resolved by wording-only fix:** pilot-facing encoding / mojibake in core guidance surfaces

### High-friction but not blockers

- draft vs saved vs runtime mental model is still complex
- audit / parity tab still asks the user to separate validated rows from pending / unvalidated rows
- export artifact naming is still somewhat insider-oriented

### Future polish only

- tighter information hierarchy across help, lineage, and versioning panels
- more role-targeted labels for reviewer vs operator audiences
- clearer download artifact descriptions

## Trusted Pilot Go / No-Go Impact

**Recommendation:** proceed with the trusted pilot dry-run for TUHO/Oborovo only, with guided operator facilitation and the new checklist.

Why this is still a **go**:

- validated frozen-template scope remains explicit
- backend-source-of-truth messaging remains intact
- stale runtime / dirty draft warnings are substantively correct
- export lineage remains clear about saved boundary vs runtime boundary
- Phase 37 removed the most visible copy/encoding regressions from key pilot-facing surfaces

Why this is still **not self-serve ready**:

- generic/unvalidated boundaries still need active reinforcement
- audit and export surfaces still benefit from guided explanation
- backup/restore expectations are still more operational than intuitive

## Deferred UI Refactor Items

These are intentionally deferred from Phase 37:

- Shared LineItemGrid / major UI harmonization
- broader navigation simplification
- full audit-tab information architecture redesign
- export catalog restructuring
- richer role-specific onboarding flows
- any runtime, formula, or model behavior changes

## Recommended Next Phases

1. **Phase 37B / 38A: Pilot copy and trust-surface polish**
   - tighten artifact descriptions
   - reduce duplicate stale-runtime explanations
   - make generic exclusion more visually prominent

2. **Audit output enhancement phase**
   - separate validated parity anchors from pending/unvalidated audit rows
   - improve reviewer-oriented takeaways

3. **External model review phase**
   - independent review of validated frozen-template outputs and operator-facing evidence pack

## Guardrail Confirmation

- No financial formula changes
- No runtime calculation changes
- No model output changes
- No project factory changes
- No fixture CSV changes
- No JavaScript financial calculations added
- No schema migrations
- G20 remains BLOCKED
- R99/R102 remain NOT APPROVED
- `partial_pay_sweep` remains not promoted
- flat/min DSCR sculpting remains not promoted
- Backend remains source of truth
