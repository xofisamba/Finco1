# Phase 15 Test Marker Upgrade

## Scope

This branch improves test quality only.

It does **not** change:

- production application behavior
- runtime or model formulas
- workbook calculations
- export calculation logic
- persistence behavior
- governance behavior
- editable surface area
- `audit_economic_mode` or `runtime_economic_mode` contracts

## Goal

Several Phase 14 and Phase 15 tests were intentionally fast, narrow marker tests. That was acceptable while the related features were landing, but before Phase 15 closeout we can strengthen the highest-value ones into more behavioral or artifact-structure checks.

The aim here is not to rewrite the entire suite. It is to upgrade the checks that most directly improve confidence in:

- workbook/export artifact integrity
- scenario compare honesty
- export lineage structure
- browser-layer state honesty
- reviewer/deployment/feedback template structure

## Upgrades Applied

### Scenario compare

Upgraded from template-phrase assertions toward:

- helper-driven compare context checks
- rendered compare template checks using structured compare data
- explicit distinction between `pending / unavailable`, `not_applicable`, and true zero

### Export lineage

Upgraded from static phrase checks toward:

- helper-driven export lineage context checks
- recent export record normalization checks
- dirty vs clean action-note behavior checks

### Browser workflow smoke

Upgraded from generic text markers toward:

- JavaScript hook to DOM target consistency checks
- dirty-state action ID coverage checks
- editable-grid partial selector consistency checks
- CSS mobile fallback selector checks

### Handoff, runbook, and feedback templates

These remain document and CSV oriented by design, but were strengthened to validate:

- actual CSV header structure
- enumerated categories and severity values
- ordered workflow steps where practical
- explicit no-claims and guardrail language

## Why Some Marker Tests Remain

Some Phase 14/15 branches are intentionally docs-and-reports closeout branches. For those, a document/report existence check plus specific guardrail wording remains appropriate because:

- the branch deliverable is the artifact itself
- there is no richer runtime behavior to exercise
- replacing document checks with fake behavioral tests would not add meaningful confidence

Examples that remain acceptable as marker-heavy:

- closeout forensic pack docs
- reviewer handoff wording
- deployment runbook wording
- feedback process guidance

## Guardrails Preserved

- No authority-boundary tests were weakened.
- Runtime remains backend-authoritative.
- Workbook/export remains descriptive only.
- Scenario compare remains descriptive only.
- Export provenance and export lineage remain descriptive only.
- No replay engine behavior was introduced.
- `G20` remains `BLOCKED`.
- `R99/R102` remain `NOT APPROVED`.

## Outcome

This branch upgrades the highest-value marker tests into stronger behavioral, rendered-template, workbook-artifact, helper-structure, and CSV-schema checks where practical, while honestly documenting the remaining marker-style tests that still make sense.
