# Enterprise SaaS Readiness Tracker

This file is the **roadmap tracker** from the current state to a paid
pilot and eventually to enterprise SaaS. It tracks eleven
dimensions, each with a current percentage, a target percentage,
blockers, dependencies, next actions, gate criteria, and the
relevant no-go claims.

> **The roadmap is internal planning. The percentages are
> self-assessments, not external claims. Reaching 100% on a
> dimension does not authorize an external claim of any kind.**
> See `docs/validation/internal_vs_external_validation_boundaries.md`
> and `docs/external_review/no_go_claims.md` for the no-go scope.

---

## 1. How to read this tracker

Each of the eleven dimensions is in
`reports/roadmap/enterprise_saas_readiness_tracker.json` and has:

* **`current_percentage`** — the project's self-assessed current
  state, 0–100. Conservative by intent.
* **`target_percentage`** — the project's self-assessed target
  state for the dimension. Targets are internal goals, not external
  commitments.
* **`blockers`** — what is preventing further progress. A blocker
  may be technical, organizational, evidence-based, or
  governance-based.
* **`dependencies`** — other dimensions or external workstreams
  that this dimension depends on.
* **`next_actions`** — concrete, time-bounded actions. Each action
  has an owner, a target date, and a status.
* **`gate_criteria`** — what must be true to consider the
  dimension "ready" (current_percentage == target_percentage).
* **`no_go_claims`** — the relevant subset of the no-go claim list
  that applies to this dimension.

The percentages are **self-assessments by the project team**. They
are not externally validated. They are not customer-facing metrics.
They are an internal planning tool.

## 2. The eleven dimensions

The dimensions, in the order they appear in the JSON:

1. **Architecture** — backend as source of truth, services extracted
   from `main_web.py` (Phase 51+), import direction enforced
   (Phase 51F).
2. **Model confidence** — internal tests, golden-parity pins
   (Phase 51F), route characterizations (Phase 51E-1, 51E-2,
   51G-1).
3. **Generic validation** — B2 workstream: acquisition framework
   for generic solar / wind reference models. No references
   acquired yet.
4. **UI / product** — Streamlit UI, web layer, error handling, UX.
5. **Persistence** — saved scenarios, scenario state, future
   `/save-run` extraction (Phase 51G-2).
6. **Governance** — no-go claim list, validation evidence matrix,
   B-track workstream discipline, internal vs external validation
   boundaries.
7. **Deployment** — pilot deployment, observability, infrastructure
   as code, environment management.
8. **Observability** — logs, metrics, traces for the pilot
   environment.
9. **Security** — authentication, authorization, rate limiting,
   secret management, audit logging.
10. **Paid pilot readiness** — B7 workstream: controlled pilot
    runbook, feedback protocol, triage, support. B3 matrix has
    `pilot_claim_allowed` flags.
11. **Enterprise SaaS readiness** — long-term: multi-tenant,
    SLA-backed, audit-grade. **Explicitly not the current goal.**
    This dimension exists to track how far we are from it, not to
    claim we are near it.

## 3. What this tracker is not

* It is not a customer-facing roadmap. It is internal.
* It is not a sales or marketing artifact. It does not make
  external claims.
* It is not a project-management tool. The percentages are
  self-assessments, not Gantt-chart-driven.
* It is not a substitute for the B3 matrix. The matrix is the
  authoritative evidence inventory; this tracker rolls the
  evidence up into a planning view.
* It is not a guarantee of forward progress. Blockers and
  dependencies are real; the roadmap will be updated as the
  picture changes.

## 4. How a dimension is updated

A dimension is updated as a normal B-track operation. The
procedure:

1. The dimension owner re-assesses `current_percentage` based on
   the latest evidence in the B3 matrix and any new artifacts.
2. The dimension owner updates `next_actions` and removes any
   action that is no longer relevant.
3. The dimension owner records the change in the JSON's
   `update_log` field, with date and a short rationale.
4. The dimension owner confirms that `no_go_claims` is still
   accurate. If a no-go claim should be added or removed, that is
   a separate governance change (see
   `docs/external_review/no_go_claims.md` §11).

The tracker is a working artifact. Like the B3 matrix, it should
be honest about demotions. A dimension moving from 50% to 45% is
useful information, not a failure.

## 5. What changes the no-go claims

The no-go claims are **not** changed by reaching 100% on any
dimension. They are changed only by a dedicated governance change
with explicit approval (see
`docs/validation/internal_vs_external_validation_boundaries.md`
§9).

In particular:

* Reaching 100% on **model confidence** does not authorize a
  lender, bank, audit, certification, regulatory, or SaaS claim.
* Reaching 100% on **generic validation** does not authorize a
  generic solar or generic wind claim that the project is not
  making today.
* Reaching 100% on **paid pilot readiness** does not authorize
  any external claim based on the pilot.
* Reaching 100% on **enterprise SaaS readiness** would still
  require an explicit, separate governance change to begin
  relaxing any no-go claim.

## 6. Cross-references

* `reports/roadmap/enterprise_saas_readiness_tracker.json` — the
  machine-readable tracker.
* `reports/validation/validation_evidence_matrix.json` — the
  authoritative evidence inventory.
* `docs/validation/validation_evidence_matrix.md` — the matrix
  narrative.
* `docs/validation/internal_vs_external_validation_boundaries.md` —
  the boundary.
* `docs/external_review/no_go_claims.md` — the no-go list.
* `docs/pilot/controlled_pilot_runbook.md` — B7 runbook (paid
  pilot readiness).
* `docs/generic_validation/generic_reference_acquisition_plan.md` —
  B2 acquisition plan (generic validation).
* `docs/phase51f_parallel_work_guardrails.md` — Phase 51F
  guardrails (architecture, model confidence).

---

*End of enterprise SaaS readiness tracker narrative.*
