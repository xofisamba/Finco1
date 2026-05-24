# Phase 15 Pilot Feedback Instrumentation

## Scope

This feedback instrumentation pack is for a **single-user guided internal pilot** only.

It does **not** introduce or claim:

- lender-ready operating status
- audit-certified operating status
- SaaS or customer-support readiness
- multi-user approval workflow readiness
- governance approval power
- runtime authority
- replay-engine behavior

The goal is to give pilot reviewers and operators a consistent, lightweight way to record findings without relying on memory, chat history, or ad hoc notes.

## Why Feedback Is Collected

Pilot feedback is collected so the team can separate:

- runtime trust concerns
- export readability concerns
- compare clarity concerns
- workflow friction
- documentation gaps
- environment or deployment issues

Feedback helps prioritize follow-up work. It does **not** approve model behavior, governance state, or runtime outputs.

## Who Records Feedback

Feedback may be recorded by:

- the pilot reviewer
- the pilot operator
- the observing project owner or facilitator

Only record what is needed for internal issue tracking and reproduction.

## What Not To Record

Do **not** record unnecessary personal data.

Avoid:

- unrelated personal details
- credentials or secrets
- copied sensitive files when a filename or reference is enough
- approval language that implies governance promotion

## Authority Boundaries

- Runtime remains backend-owned and is the only source of financial truth.
- Persistence remains workflow metadata and saved-boundary storage only.
- Workbook/export remains descriptive and reviewer-facing.
- Scenario compare remains descriptive only.
- Export provenance and export lineage remain descriptive only.
- Feedback records are non-authoritative.
- Feedback records are not governance approvals.
- Feedback records do not alter runtime authority.
- Feedback does not trigger automatic model changes.
- `audit_economic_mode` remains audit/reconciliation-only.
- `runtime_economic_mode` remains the only explicit runtime staging path.
- `G20` remains `BLOCKED`.
- `R99/R102` remain `NOT APPROVED`.

## When To Record Feedback

Record feedback:

- during the pilot session when something is confusing, wrong, or unexpectedly hard to interpret
- immediately after a step if the behavior may be hard to reproduce later
- after export, compare, or runtime review if the issue is easier to describe with artifact context
- at the end of the session when summarizing smaller UX or documentation friction

## How To Classify Feedback

Use one primary category per issue:

- `runtime_trust`
- `export_readability`
- `workbook_numeric`
- `scenario_compare`
- `dirty_state_or_stale_runtime`
- `governance_label_confusion`
- `reviewer_handoff_gap`
- `deployment_or_environment`
- `browser_or_htmx`
- `performance`
- `UX_only`
- `documentation_only`

Choose the category that best captures the main follow-up owner. If more than one area is affected, note the extra context in `resolution_notes` or `suggested_follow_up`.

## Severity And Blocker Semantics

Use these severity levels:

- `LOW`: minor friction or wording issue that does not threaten pilot trust
- `MEDIUM`: meaningful confusion or usability issue that may slow the pilot or reduce clarity
- `HIGH`: serious issue affecting confidence, interpretation, or reliable guided use
- `BLOCKER`: issue prevents safe or credible continuation of the current pilot step

Important boundary notes:

- feedback severity is **not** governance approval
- feedback blocker is **not** the same as `G20` or `R99/R102` governance state
- feedback does **not** alter runtime authority
- feedback does **not** trigger automatic model changes

## Linking Feedback To Review Context

Where available, link feedback to:

- project
- scenario name
- scenario id
- runtime snapshot id
- export filename
- workflow step
- governance label involved
- screenshot or artifact reference

If a field is not available, leave it blank or mark it with the existing descriptive language such as `unavailable` or `not_applicable`. Do not substitute zero for missing context.

## Pilot Session Log

In addition to issue-level feedback, use a session-level log to capture:

- which project was used
- which scenarios were touched
- whether exports were created
- whether compares were run
- whether the smoke test passed
- how many issues were logged
- whether backup was completed

This helps separate isolated reviewer findings from environment-wide or session-wide problems.

## Triage Workflow

After each pilot session:

1. collect issue rows and the session log
2. group issues by category and severity
3. review authority-impacting issues first, especially `runtime_trust`, `workbook_numeric`, and `scenario_compare`
4. separate documentation or UX confusion from true runtime-trust concerns
5. confirm whether the issue is reproducible
6. open a cleanup branch only for verified follow-up work
7. preserve governance boundaries during triage:
   - `G20` remains `BLOCKED`
   - `R99/R102` remain `NOT APPROVED`
8. do not treat issue resolution as governance approval

## Practical Recording Guidance

Good pilot feedback usually answers:

- what step was being attempted
- what the reviewer expected
- what actually happened
- whether it affected runtime trust, export readability, compare clarity, or UX only
- whether it is reproducible
- what artifact or screenshot can help the next person understand it

## No-Claims

This pack supports guided internal pilot feedback only.

It does **not** create:

- lender-ready claims
- audit-certified claims
- SaaS support-desk scope
- customer support operations
- automatic remediation or auto-triage logic
- governance approval power

## Outcome

This instrumentation pack gives reviewers and operators a consistent way to capture, classify, and triage internal pilot findings while keeping runtime authority, governance boundaries, and descriptive export/compare semantics intact.
