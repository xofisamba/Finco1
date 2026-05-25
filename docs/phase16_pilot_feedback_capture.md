# Phase 16 Pilot Feedback Capture

## Scope

This branch covers pilot feedback capture status only.

It is limited to documentation, report updates, and validation.

It does **not** change:

- runtime or model formulas
- workbook calculations
- export calculation logic
- persistence authority
- governance behavior
- editable surfaces
- replay-engine behavior

It also does **not** introduce lender-ready, audit-certified, SaaS, or multi-user claims.

## Capture Outcome

This branch follows outcome **B: feedback capture pending**.

No real operator or reviewer pilot evidence is available in this environment.

Because no real guided pilot execution evidence exists here:

- feedback capture status is explicitly `PENDING_REAL_PILOT_EXECUTION`
- TUHO remains `NOT_EXECUTED_IN_THIS_ENVIRONMENT`
- Oborovo remains `NOT_EXECUTED_IN_THIS_ENVIRONMENT`
- no fake `PASS` session status is recorded
- no template/example issue row is promoted into a real finding

## Why Pending Status Was Chosen

The current available artifacts still show the same evidence posture:

- `reports/phase16_pilot_session_log_tuho.csv` is an execution-ready placeholder
- `reports/phase16_pilot_session_log_oborovo.csv` is an execution-ready placeholder
- `reports/phase15_pilot_feedback_issue_template.csv` contains a template example row
- `reports/phase15_pilot_session_log_template.csv` contains a template example row

That means the project has a ready pilot apparatus, but not real captured pilot evidence yet.

## Authority Boundaries

- Runtime remains backend-owned and is the only source of financial truth.
- Workbook/export remains descriptive and reviewer-facing.
- Scenario compare remains descriptive only.
- Export provenance and export lineage remain descriptive only.
- Pilot feedback records remain non-authoritative.
- Pilot feedback records are not governance approvals.
- Pilot feedback does not alter runtime authority.
- Pilot feedback capture does not approve `G20`.
- Pilot feedback capture does not promote `R99/R102`.
- `audit_economic_mode` remains audit/reconciliation-only.
- `runtime_economic_mode` remains the only explicit runtime staging path.
- `G20` remains `BLOCKED`.
- `R99/R102` remain `NOT APPROVED`.

## Capture Status Model

Allowed capture status values:

- `REAL_FEEDBACK_CAPTURED`
- `PENDING_REAL_PILOT_EXECUTION`
- `PARTIAL_FEEDBACK_CAPTURED`

Allowed session status values:

- `PASS`
- `PASS_WITH_NOTES`
- `FAIL`
- `NOT_EXECUTED_IN_THIS_ENVIRONMENT`
- `unavailable`

If real evidence does not exist, do **not** substitute:

- fake `PASS`
- zero issue count as if a session occurred
- populated blocker fields as if a reviewer actually observed them

Use explicit pending or unavailable markers instead.

## Current Project-Level Capture Status

Current truthful capture status:

- TUHO: `PENDING_REAL_PILOT_EXECUTION`
- Oborovo: `PENDING_REAL_PILOT_EXECUTION`

Current truthful session status:

- TUHO: `NOT_EXECUTED_IN_THIS_ENVIRONMENT`
- Oborovo: `NOT_EXECUTED_IN_THIS_ENVIRONMENT`

## How A Real Operator Should Update These Reports

When a real guided pilot session is executed:

1. replace the project capture status only if actual reviewer/operator evidence exists
2. update the session status honestly to `PASS`, `PASS_WITH_NOTES`, or `FAIL`
3. add real issue rows only for real observed issues
4. preserve `unavailable` and `not_applicable` where evidence is genuinely missing
5. keep governance labels descriptive only:
   - `G20` remains `BLOCKED`
   - `R99/R102` remain `NOT APPROVED`

## Issue Log Guidance

If no real issues exist yet:

- keep only the header row, or
- keep rows explicitly labeled as `TEMPLATE_EXAMPLE_ONLY`

Do **not** treat template rows as real pilot findings.

## Remaining Gaps

The following gaps remain after this branch:

- real pilot execution evidence still needs to be captured
- live browser automation remains future work
- workbook-wide numeric audit remains future work
- real operator issue evidence is still needed beyond template/example rows

## Outcome

This branch keeps the Phase 16 pilot feedback record honest: the capture apparatus exists, but real guided pilot evidence is still pending and is not fabricated here.
