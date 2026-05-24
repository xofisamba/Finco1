# Phase 15 Reviewer Handoff Pack

## Scope

This handoff pack is for a **single-user guided internal pilot** only.

It does **not** introduce or claim:

- lender-ready status
- audit-certified status
- SaaS or multi-tenant readiness
- multi-user approval workflow readiness
- replay-engine behavior

The goal is to help an internal reviewer use the application without relying on chat history or direct developer explanation.

## What The App Is For

The application supports guided internal review of selected project scenarios, saved scenario boundaries, backend runtime output, workbook export, and descriptive scenario comparison.

Supported pilot scope includes:

- selecting TUHO or Oborovo
- editing supported assumptions from the existing editable surfaces
- saving scenarios explicitly
- running the model from a clean saved boundary
- inspecting runtime summary output
- exporting reviewer-facing workbook artifacts
- comparing saved scenarios and saved runtime summaries

## Authority Boundaries

- Runtime remains backend-owned and is the only source of financial truth.
- Persistence stores workflow metadata and saved boundaries only.
- Workbook/export remains descriptive and reviewer-facing.
- Scenario compare remains descriptive only.
- Export provenance and export lineage remain descriptive only.
- Editable grids remain draft-only until explicitly saved.
- Save does not run the model.
- Compare does not auto-save or auto-run.
- `audit_economic_mode` remains audit/reconciliation-only.
- `runtime_economic_mode` remains the only explicit runtime staging path.
- `G20` remains `BLOCKED`.
- `R99/R102` remain `NOT APPROVED`.

## Reviewer Quickstart

Use the deployment runbook first to start the application and log in.

Recommended reviewer flow:

1. open the app and sign in using the guided pilot credentials provided by the operator
2. choose either TUHO or Oborovo as the active project
3. load an existing scenario or create a new saved scenario boundary
4. edit one supported assumption in the current editable grid surface
5. confirm the workspace becomes dirty and the unsaved changes banner appears
6. save the scenario explicitly
7. run the model from the clean saved boundary
8. inspect the runtime summary and related governance labels
9. export the workbook if review artifacts are needed
10. compare scenarios when saved-boundary comparison is needed
11. record any issue using the issue template in this pack

## How To Read Dirty State

When you edit a supported assumption, the workspace may become dirty.

Dirty state means:

- the current browser draft differs from the saved scenario boundary
- the current browser draft is **not** runtime truth
- the current browser draft is **not** part of workbook export truth
- the current browser draft is **not** part of scenario compare truth

The unsaved changes banner is there to warn you that:

- Save is needed before a clean runtime run
- Save is needed before the draft becomes a saved scenario boundary
- stale runtime may still reflect the last clean run rather than your newest draft edits

## Save, Run, Export, and Compare

### Save Scenario

Save creates a persisted scenario boundary. Save does **not** run the model.

### Run Model

Run uses the clean saved scenario boundary and creates or updates backend runtime output.

### Export Workbook

Workbook export is reviewer-facing and descriptive. It reflects backend runtime/export context. It does **not** make the workbook authoritative.

### Compare Scenarios

Scenario compare is descriptive only. It compares saved scenario snapshots and saved runtime summaries where available. It does **not** include unsaved browser drafts. It does **not** auto-save. It does **not** auto-run.

## How To Read Export Lineage and Provenance

Export lineage and provenance help you interpret what produced an exported artifact.

Look for:

- active project
- scenario name or scenario id
- scenario revision or saved boundary marker
- runtime timestamp or runtime boundary marker
- export timestamp
- runtime origin
- provenance flags where available

If a provenance field shows `unavailable`, `SOURCE_NOT_AVAILABLE`, or `not_applicable`, treat that as a true availability note. It is **not** zero and it is **not** approval.

## How To Read Workbook Cover Notes

Workbook cover notes explain:

- that runtime remains backend-owned
- that workbook/export is descriptive only
- that later draft edits do not rewrite an already exported artifact
- that governance blockers still apply
- that unavailable or not_applicable markers are intentional and not zero

## Governance Status Interpretation

Use these plain-language meanings:

- `BLOCKED`: a governed item is still blocked and must not be treated as approved or promoted
- `NOT APPROVED`: an item is still under a non-approved state and must not be treated as accepted runtime logic
- `PASS`: the checked item passed the stated check in its current context
- `WARN`: review attention is needed, but the item is not automatically approved or blocked solely by the warning label
- `ACCEPTED_CONVENTION`: an explanatory convention is being used; it is **not** approval
- `SOURCE_NOT_AVAILABLE`: the source value or evidence is unavailable; it must not be read as zero
- `MISSING_EVIDENCE`: may appear in legacy-frozen historical artifacts and must be interpreted using current governance docs rather than as an active approval state

Current explicit guardrails:

- `G20` remains `BLOCKED`.
- `R99/R102` remain `NOT APPROVED`.
- `ACCEPTED_CONVENTION` is explanatory, not approval.
- `SOURCE_NOT_AVAILABLE`, `unavailable`, and `not_applicable` must not be read as zero.
- legacy-frozen historical labels must be interpreted using current documentation, not as live approval signals

## Reviewer FAQ

### Why is workbook/export descriptive instead of authoritative?

Because runtime remains backend-owned. The workbook is for review, traceability, and interpretation. It does not become the financial calculation authority.

### Why does save not run the model?

Because save creates a clean persisted scenario boundary. Running the model is a separate explicit action.

### Why does compare not include unsaved drafts?

Because scenario compare is restricted to saved snapshots and saved runtime summaries. Unsaved drafts are not trustworthy as saved or runtime truth.

### Why is unavailable or not_applicable not zero?

Because those markers communicate missing context or non-applicability. They are availability markers, not numeric substitutes.

### Why are G20 and R99/R102 still not approved?

Because current governance posture still blocks or withholds approval for those items. Review notes and conventions do not soften those blockers.

### Why is this not lender-ready or audit-certified?

Because the app is still positioned as a guided internal pilot tool and does not claim external certification or formal lender-grade readiness.

### Why is this single-user guided pilot only?

Because multi-user governance, approval workflow, and broader operating controls are not part of the current supported scope.

### What should I do if export provenance is unavailable?

Record the missing provenance detail in the issue template and note the project, scenario, and export artifact involved.

### What should I do if runtime appears stale?

Confirm whether the workspace is dirty. If it is, save the scenario and then run the model explicitly. Stale runtime means the displayed runtime may still reflect the last clean run.

## Issue Reporting

When something looks wrong or unclear, record:

- project
- scenario
- step
- expected behavior
- actual behavior
- screenshot or reference
- export filename if relevant
- governance label involved
- severity
- blocker yes or no
- whether the issue affects runtime trust, export readability, compare clarity, or UX only

## How To Stop and Report Problems

If you cannot continue safely:

1. stop making further edits in the current session
2. record the issue using the issue template
3. attach the relevant export filename or screenshot when available
4. note whether the concern affects runtime trust, export readability, compare clarity, or workflow UX
5. hand the issue to the operator or project owner for triage

## Outcome

This handoff pack is meant to let an internal reviewer complete the guided pilot workflow, interpret statuses correctly, and report issues clearly without changing product behavior or overstating product maturity.
