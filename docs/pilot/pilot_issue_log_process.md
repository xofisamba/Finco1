# Pilot Issue Log & Evidence Register Process

This file is the **operating process** for logging issues and
registering evidence during a controlled pilot. It is a
companion to the B7 runbook, the B9 execution pack, the B18
controlled pilot launch checklist, the B19 post-pilot evidence
update template, and the B19 demo script guardrail.

> **Pilot issue logs are internal evidence. They are not external
> validation, not a customer reference, and not a substitute
> for any B-track governance artifact.** The process is
> internal governance, not a marketing or sales artifact.
>
> **Claude review is separate.** The Phase 51N checkpoint
> includes a Claude review preparation pack on the Agent A
> side; Claude review itself is handled outside this branch.
> Pilot issue logs do not represent Claude review as
> completed.
>
> **Do not claim a pilot has happened unless actual pilot
> results are later provided.** The templates in this process
> are empty at package creation. They are populated only when
> a controlled pilot has actually run.

---

## 1. Scope and audience

This process covers:

* the **issue log** for the controlled pilot (per-run issues
  with category, severity, owner, status, resolution);
* the **evidence register** for the controlled pilot (per-run
  evidence with checksums, retention, sensitivity flag);
* the **mapping** from a logged issue to the B3 matrix, the B12
  heatmap, the B13 paid pilot gate, the B15-B19 governance
  artifacts, and the no-go claim list.

The process applies to the **controlled internal pilot** (B7 +
B9 + B18). It does **not** apply to the paid pilot, which is
gated by B13 and requires additional gates (PG-01 through PG-14)
to be passed. The process does not authorize the paid pilot.

## 2. Issue ID format

Each issue gets a unique identifier. The format is:

```
ISS-<pilot_run_id>-<sequence_number>
```

* `pilot_run_id` — the unique identifier of the pilot run
  (assigned by the pilot operator).
* `sequence_number` — a 4-digit zero-padded sequence number,
  starting at 0001.

Examples: `ISS-PR-2026-Q3-001-0001`, `ISS-PR-2026-Q3-001-0002`.

The pilot operator assigns the sequence number. The full
`issue_id` is recorded in the issue log template JSON and in
the evidence register template JSON.

## 3. Issue severity taxonomy

The severity taxonomy mirrors the B7 issue triage process. The
levels are:

| Severity | Definition | Resolution window |
|---|---|---|
| `pilot-blocker` | Issue blocks pilot continuation. Must be resolved or accepted before the pilot continues. | Immediate |
| `high` | Issue affects a significant portion of the pilot scope. | 3 business days |
| `medium` | Issue affects a small portion of the pilot scope or has a clear workaround. | 1 week |
| `low` | Issue is cosmetic or doc-only. | 2 weeks |

A `pilot-blocker` failure on a metric that the per-area pass /
fail criterion defines as `must-pass` is a `pilot-blocker`. A
`pilot-blocker` failure on a metric defined as `informational`
is recorded but does not block the pilot.

## 4. Issue category taxonomy

The category taxonomy mirrors the B7 issue categories. The
categories are:

| Category | Definition |
|---|---|
| `bug` | A defect in the model, the routes, the services, or the persistence layer. |
| `unexpected-behavior` | The model produces output that is outside the documented range, but the cause is not yet known. |
| `ux` | A user-experience issue that does not affect model correctness. |
| `doc` | A documentation gap or inconsistency. |
| `infra` | An environment, deployment, or observability issue. |
| `scope` | A scope misalignment (e.g. the pilot user attempts a generic-solar or generic-wind input set). |

A `scope` category is recorded but does not affect the
per-area pass / fail criteria. A `bug` or `unexpected-behavior`
category triggers a triage review.

## 5. Affected area / module

Each issue is mapped to:

* **affected area / module** — the specific code area or
  service module affected (e.g. `app/services/scenarios_save_service.py`,
  `app/persistence/`, `app/services/save_run_service.py`).
* **affected B3 validation area** (if applicable) — the B3
  matrix area ID (e.g. AREA-001 for TUHO, AREA-002 for Oborovo,
  AREA-008 for senior debt, AREA-013 for persistence, AREA-019
  for recent Agent A work, AREA-020 for Phase 51N checkpoint).
* **affected B12 heatmap area** (if applicable) — the B12
  heatmap area ID (e.g. HC-001, HC-012, HC-019).
* **affected B13 paid pilot gate** (if applicable) — the
  specific gate (PG-01 through PG-14) that the issue affects.
* **affected B15-B19 governance artifacts** (if applicable) —
  the specific artifact (e.g. B17 remaining hotspots tracker,
  B18 launch checklist, B19 post-pilot template, B19 demo
  script guardrail).

If the issue is in a B3 area that is not in pilot scope, the
issue is recorded with `b3_area: null` and is treated as
informational (does not affect the pilot run decision).

## 6. Evidence attached

Each issue has a list of evidence items. Each evidence item
has:

* **evidence_id** — unique identifier (e.g. `EV-PR-2026-Q3-001-0001-LOG`,
  `EV-PR-2026-Q3-001-0001-XLSX`).
* **evidence_type** — `run_log`, `validation_record`, `export`,
  `screenshot`, `user_feedback`, `issue_log`, `no_go_acknowledgement`,
  `other`.
* **evidence_path** — path to the evidence file.
* **evidence_sha256** — SHA-256 checksum of the evidence file.
* **evidence_size_bytes** — size of the evidence file in bytes.
* **evidence_created_at** — ISO-8601 timestamp of the evidence
  creation.
* **evidence_retention_until** — ISO-8601 date of the evidence
  retention expiry (per `docs/pilot/pilot_user_feedback_protocol.md` §5).
* **evidence_sensitivity** — `public`, `internal`, `confidential`,
  `restricted`. See §11 for the sensitivity taxonomy.
* **evidence_notes** — short text.

The evidence is stored in the pilot-only location defined in
the pilot scope. The evidence register is the source of truth
for the per-issue evidence list.

## 7. Reproduction steps

Each issue has a short text field for the reproduction steps.
The format is:

```
1. Step 1
2. Step 2
3. ...
```

A reproducible issue has at least 3 steps. A non-reproducible
issue has `repro_steps: "non_reproducible"` and is recorded
with `outcome: "cannot_reproduce"`.

## 8. Expected behavior

A short text field describing the expected behavior per the
documentation. A reference to the file and section is recorded
in the format `path/to/file.md §X.Y` or
`path/to/json_file.json §key_path`.

## 9. Actual behavior

A short text field describing the observed behavior. The
observed value, the expected value, and the delta are recorded
in the validation record (per the B9 evidence-capture
template).

## 10. Pass / fail impact

Each issue records the pass / fail impact:

* **per-area impact** — `pass` / `fail` / `investigate` /
  `not_evaluated`. This is the per-area decision per the B9
  pass / fail criteria.
* **per-run impact** — `pass` / `fail` / `investigate` /
  `incomplete`. This is the per-run decision per the B9 pass /
  fail criteria.
* **pilot-overall impact** — `pass` / `fail` / `investigate` /
  `not_evaluated`. This is the pilot overall decision per the
  B9 result summary template.
* **metric classification** — `must-pass` / `should-pass` /
  `informational`. A `must-pass` failure is a `pilot-blocker`.

## 11. Owner, status, resolution, post-resolution evidence

Each issue has:

* **owner** — the responsible owner placeholder (`project_lead`,
  `pilot_operator`, `b_track_owner`, `legal_placeholder`,
  `security_placeholder`). For Agent A code issues, the owner
  is `agent_a_coordination` (a placeholder; actual triage is
  via the agent_a_b_governance_refresh_plan).
* **status** — `reported` / `acknowledged` / `investigating` /
  `decided` / `resolved` / `closed` / `escalated`.
* **resolution** — short text describing the fix or
  workaround.
* **resolution_at** — ISO-8601 timestamp.
* **post_resolution_evidence** — list of evidence items
  (per §6) that confirm the resolution.
* **post_resolution_decision** — `pass` / `fail` /
  `investigate` / `not_evaluated` after the resolution.

A `closed` status means the issue is fully resolved and the
post-resolution decision is `pass`. A `cancelled` status (not
listed; reserved for future use) means the issue is not
actioned. An `escalated` status means the issue is escalated
to a higher-level owner (e.g. legal, security, project lead).

## 12. Whether B3 / B12 / B13 / B15-B19 artifacts require update

Each issue records whether the B-track governance artifacts
require update:

* **b3_matrix_update_required** — `true` if the issue changes
  the B3 matrix `current_status`, `evidence_category`,
  `missing_evidence`, `blockers`, or `notes` for any area.
* **b12_heatmap_update_required** — `true` if the issue
  changes the B12 heatmap `confidence_label` for any area.
* **b13_paid_pilot_gate_update_required** — `true` if the
  issue changes the B13 gate status for any PG-XX gate.
* **b15_b19_artifacts_update_required** — `true` if the issue
  changes any B15-B19 governance artifact (e.g. B17 remaining
  hotspots tracker, B18 launch checklist, B19 post-pilot
  template, B19 demo script guardrail).
* **b14_refresh_tracker_update_required** — `true` if the
  issue is a new Agent A phase that requires a B-track
  governance refresh.

If any of the above is `true`, the pilot operator coordinates
with the B-track owner to perform the update. The update is a
normal B-track governance refresh (B14 plan §5).

## 13. No-go claim impact

Each issue records whether the no-go claim list is impacted:

* **no_go_claim_impact** — `none`, `new_claim_category`,
  `existing_claim_strengthened`, `existing_claim_weakened`,
  `requires_dedicated_governance_change`.

A `none` impact is the common case (the issue is a defect, a
documentation gap, or a scope misalignment; it does not change
the no-go claim list). A `new_claim_category` impact requires
a B11 commercial messaging guardrail update. An
`existing_claim_weakened` impact requires a dedicated
governance change and is rare.

## 14. Confidentiality / data sensitivity flag

Each issue records the data sensitivity flag:

* **sensitivity** — `public`, `internal`, `confidential`,
  `restricted`. The flag determines the access controls, the
  retention policy, and the sharing rules.
* **public** — no redaction required. May be shared in any
  context.
* **internal** — internal use only. May be shared within the
  project team. Not for external use.
* **confidential** — sensitive. May be shared with the project
  lead, the pilot operator, and the B-track owner. Not for
  reviewer-facing or external use.
* **restricted** — highly sensitive. May be shared with the
  project lead only. Includes any pilot user data, any
  production data references, any NDA-protected data, any
  security incident details.

The sensitivity flag is recorded in the issue log and in the
evidence register. The retention policy is per
`docs/pilot/pilot_user_feedback_protocol.md` §5.

## 15. Pilot issue logs are internal evidence, not external
    validation, not customer reference

**Pilot issue logs are internal evidence. They are not external
validation, not a customer reference, and not a substitute
for any B-track governance artifact.**

A pilot issue log is the pilot operator's record of the pilot.
It is internal governance. It is not a marketing or sales
artifact. It is not external validation. It is not a customer
reference. The pilot issue log feeds the B3 matrix update, the
B12 heatmap update, the B13 paid pilot gate update, and the
B15-B19 governance refresh. It does not authorize any external
claim.

A pilot user is bound by the no-go language acknowledgement
(B21) and the no-go claim list (B1). A pilot issue log does
not record any external-claim language. A pilot issue log
does not record any customer reference. A pilot issue log
does not record any production-readiness claim. A pilot issue
log is not used in any external review document, in any
marketing material, in any sales conversation, or in any
website copy, without the pilot user's explicit written
consent.

## 16. What this process is not

* It is not a contract. The pilot user agreement is the
  contract (B21).
* It is not external validation. The pilot issue log is
  internal evidence.
* It is not a customer reference. The pilot is not a customer
  relationship.
* It is not a substitute for the B7 runbook, the B9 execution
  pack, the B18 launch checklist, the B19 post-pilot
  template, or the B19 demo script guardrail.
* It is not paid pilot authorization. The paid pilot gate
  (B13) is a separate stage.
* It is not Claude review. Claude review is separate.

## 17. Cross-references

* `reports/pilot/pilot_issue_log_template.json` (B20,
  machine-readable)
* `reports/pilot/pilot_evidence_register_template.json` (B20,
  machine-readable)
* `docs/pilot/controlled_pilot_runbook.md` (B7)
* `docs/pilot/pilot_user_feedback_protocol.md` (B7)
* `docs/pilot/pilot_issue_triage_process.md` (B7)
* `docs/ops/support_and_incident_response.md` (B7)
* `docs/pilot/pilot_validation_execution_pack.md` (B9)
* `docs/pilot/pilot_pass_fail_criteria.md` (B9)
* `docs/pilot/pilot_evidence_capture_template.md` (B9)
* `reports/pilot/pilot_execution_checklist.json` (B9)
* `reports/pilot/pilot_result_summary_template.json` (B9)
* `docs/validation/validation_evidence_matrix.md` (B3 narrative)
* `reports/validation/validation_evidence_matrix.json` (B3
  matrix)
* `docs/validation/model_confidence_heatmap.md` (B12)
* `reports/validation/model_confidence_heatmap.json` (B12)
* `docs/pilot/paid_pilot_readiness_gate.md` (B13)
* `docs/pilot/controlled_pilot_launch_checklist.md` (B18)
* `docs/pilot/post_pilot_evidence_update_template.md` (B19)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/external_review/no_go_claims.md` (B1)

---

*End of pilot issue log & evidence register process.*
