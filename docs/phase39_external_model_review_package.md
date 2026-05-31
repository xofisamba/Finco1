# Phase 39 - External Model Review Package / Reviewer Run

## Base SHA

`ae08938e80b3b16055c842cb86689e7e70cbfaec`

## Review objective

Phase 39 prepares a structured reviewer package for the validated frozen-template
pilot scope. The goal is to let an external or independent internal reviewer assess:

- what is in the validated pilot scope
- what is outside review scope
- which anchors should be checked
- which documents and tests support each claim
- how to log questions, exceptions, and sign-off

This phase is documentation, reviewer workflow, evidence packaging, and tests only.

## Type / scope

Phase 39 includes:

- reviewer workflow documentation
- reviewer checklist materials
- issue log template
- reviewer package manifest
- package metadata
- tests for package completeness and non-overclaiming

This phase does **not** change:

- financial formulas
- runtime calculations
- model outputs
- data paths
- project factories
- senior debt sizing logic
- DSCR / sculpting logic
- SHL / distribution logic
- Revenue / OPEX / CAPEX / Tax formulas
- fixture CSVs
- schema

No JavaScript financial calculations were added.

## Validated review scope

The validated reviewer scope is limited to the frozen-template pilot paths and their
supporting evidence:

- TUHO frozen-template path
- Oborovo frozen-template path
- TUHO CO2 revenue treatment
- Oborovo OpEx
- Senior debt / DSCR / SHL frozen path
- scenario / export / audit evidence as pilot support material

Trusted pilot conclusions apply only to TUHO and Oborovo frozen-template paths.

## Explicitly out of review scope

The following are excluded from the Phase 39 reviewer run:

- generic solar / wind validation
- generic wind CO2
- construction IDC
- C.16 Project Rights
- M1-M18 IDC
- live sculpting / debt re-sizing promotion
- multi-user / RBAC / SSO
- SaaS / enterprise readiness
- bank / lender / certified audit / certification approval

Generic solar and wind remain exploratory and unvalidated.

## Reviewer prerequisites

Before starting, the reviewer should:

1. understand that this is an internal pilot evidence package, not a bank or lender approval package
2. understand that TUHO and Oborovo are the only validated frozen-template projects in scope
3. understand that exports and summaries are tied to the last clean backend run
4. understand that generic projects remain excluded from trusted pilot conclusions
5. have access to the Markdown document set listed in the package manifest

No PDF generator or new dependency is required. The package remains Markdown-first and
PDF-ready if converted outside this phase.

## Document reading order

Recommended reading order:

1. `docs/validation_pack_executive_summary.md`
2. `docs/validation_pack_index.md`
3. `docs/phase39_external_model_review_package.md`
4. `docs/model_reviewer_package_manifest.md`
5. `docs/model_reviewer_run_checklist.md`
6. `docs/external_reviewer_checklist.md`
7. `docs/phase27_frozen_path_external_validation_pack.md`
8. `docs/phase27_validation_evidence_matrix.md`
9. optional deep dives as needed

## Reviewer workflow

### Step 1 - Scope acknowledgement

The reviewer confirms:

- TUHO and Oborovo frozen-template paths are the only validated review scope
- generic solar / wind are out of scope and unvalidated
- this package does not provide bank, lender, audit, certification, SaaS, or enterprise approval

### Step 2 - Read the executive summary and index

Use:

- `docs/validation_pack_executive_summary.md`
- `docs/validation_pack_index.md`

These establish the validated scope, non-claims, key anchors, and reading order.

### Step 3 - Read the Phase 39 package instructions

Use:

- `docs/phase39_external_model_review_package.md`
- `docs/model_reviewer_package_manifest.md`

These explain what to review, what not to review, and how the evidence is organized.

### Step 4 - Perform anchor checks

Use:

- `docs/model_reviewer_run_checklist.md`
- `docs/external_reviewer_checklist.md`

Check the required TUHO and Oborovo anchors before drawing any conclusion.

### Step 5 - Use deep-dive documents only where needed

Use optional deep dives only when a question cannot be resolved from the summary or
primary validation pack.

### Step 6 - Log questions and exceptions

Use:

- `docs/model_reviewer_issue_log_template.md`

Any uncertainty, disagreement, or required follow-up should be logged there instead of
being implied informally.

### Step 7 - Sign off with non-claims intact

The reviewer can sign off on the limited pilot scope only after:

- scope acknowledgement
- anchor review
- issue log review
- explicit acknowledgement of excluded scope and non-claims

## Anchor checks

The reviewer run must include these anchor checks:

### TUHO anchors

- TUHO senior debt amount: 43,359.0 kEUR
- TUHO senior debt service fixture parity for validated periods
- TUHO CO2 Y1 revenue: about 611 kEUR
- TUHO DSCR inflation classified as expected under frozen-path architecture

### Oborovo anchors

- Oborovo senior debt amount: 42,852.27 kEUR
- Oborovo SHL opening balance: about 15,790 kEUR
- Oborovo OpEx Y1: about 1,338 kEUR
- Oborovo distribution lock-up while SHL outstanding
- Oborovo first valid distribution: op_idx 39 / 2050-06-30

### Cross-cutting anchors

- exports are tied to the last clean backend run
- audit and trust surfaces separate validated pilot evidence from pending or unvalidated scope
- backend remains the source of truth

## Exception logging process

When a reviewer finds an issue, question, or ambiguity:

1. record it in `docs/model_reviewer_issue_log_template.md`
2. classify it using the provided severity guidance
3. attach the exact evidence source
4. mark whether it is in-scope, expected, or out-of-scope
5. request owner response before sign-off if unresolved

Expected architecture differences should be logged as:

- `expected convention difference`, or
- `out-of-scope`

instead of being escalated as formula defects without evidence.

## Sign-off process

The reviewer sign-off should confirm:

- scope was understood
- TUHO anchors were reviewed
- Oborovo anchors were reviewed
- generic exclusion was acknowledged
- non-claims were acknowledged
- any open issues were captured in the issue log

Sign-off in this phase is an internal or independent review acknowledgement only.

## Non-claims

This package is **not**:

- a bank approval
- a lender approval
- a credit opinion
- a certified audit
- an audit certification
- a SaaS-ready claim
- an enterprise-ready claim
- a multi-tenant readiness claim

This package also does **not** validate:

- generic solar / wind
- generic wind CO2
- construction IDC
- C.16 Project Rights
- M1-M18 IDC
- live sculpting promotion

## Guardrails

- no financial formula changes
- no runtime/model changes
- no data-path changes
- no schema migrations
- no project factory changes
- no fixture CSV changes
- no JavaScript financial calculations
- TUHO / Oborovo validation behavior unchanged
- generic validation status unchanged
- G20 remains BLOCKED
- R99/R102 remain NOT APPROVED
- `partial_pay_sweep` remains not promoted
- flat/min DSCR sculpting remains not promoted
- backend remains source of truth

## Manifest decision

Phase 39 includes a small JSON manifest:

- `reports/phase39_model_reviewer_package_manifest.json`

It is included because this phase benefits from a static machine-readable package index
without adding any runtime behavior or new dependency.

## Recommended next phase

**Phase 39B / 40 - Reviewer run execution and issue triage**

Recommended focus:

- perform the structured reviewer run on TUHO / Oborovo
- capture questions and exceptions in the issue log
- separate review outcomes from any approval-style language
- keep generic path exclusion explicit
