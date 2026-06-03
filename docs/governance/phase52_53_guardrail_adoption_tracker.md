# Phase 52/53 Guardrail Adoption Tracker

This file is the **Phase 52/53 guardrail adoption tracker**.
It tracks the 6 structural guardrails (G1-G6) implemented
in Phase 52F, the 4 existing guardrails from Phase 51F
(behavior guardrail tests 21 → 31), and the 4 deferred
guardrails (D1-D4) that are tracked but not implemented.

> **Agent B does not implement guardrails. Agent A
> implements the guardrails.** Agent B tracks the
> guardrail adoption status and the guardrail refresh
> triggers.
>
> **No persistence or repository code changes by Agent B.**
> Agent B is docs-only. The guardrail adoption tracker is
> the B-track governance wrapper for the Agent A guardrail
> work.

---

## 1. Source

The guardrail data is sourced from
`reports/phase52f_persistence_guardrail_specifications.json`
(field `existing_guardrails`, count 4; field
`proposed_guardrails`, count 10; field
`implemented_guardrails`, count 6; field
`deferred_guardrails`, count 4; field
`phase53_required_guardrails`, count 6; field
`false_positive_risks`).

The 21 → 31 behavior guardrail test count change is the
project's internal self-assessment. The behavior guardrail
test count is the **total** count (existing + implemented),
per the Phase 52F report. Specifically:

* Existing guardrails (Phase 51F): 21 tests.
* Implemented guardrails (Phase 52F): 10 tests.
* **Total:** 31 tests.

## 2. Status values

The guardrail status values are:

* `active` — guardrail is implemented and enforced.
* `proposed` — guardrail is proposed but not implemented.
* `deferred` — guardrail is explicitly deferred to a later
  phase.
* `soft_check` — guardrail is implemented as a soft check
  only (e.g., a manual review checklist, not a CI test).
* `not_applicable` — guardrail is not applicable.

## 3. Existing guardrails (Phase 51F, 21 tests)

The 4 existing guardrails from Phase 51F are:

| # | Name | Source | Tests | Status |
|---|---|---|---|---|
| EX-01 | Engine-output golden (TUHO + Oborovo) | `tests/test_phase51f_parallel_work_guardrails.py::TestEngineOutputGoldenTUHO + TestEngineOutputGoldenOborovo` | 6 | active |
| EX-02 | Parity-core lock (4 SHA-256 files) | `tests/test_phase51f_parallel_work_guardrails.py::TestParityCoreLock` | 4 | active |
| EX-03 | No-service-imports-main_web/main_api | `tests/test_phase51f_parallel_work_guardrails.py::TestNoServiceImportsMainWeb` | 6 | active |
| EX-04 | Phase 51 doc cross-check | `tests/test_phase51f_parallel_work_guardrails.py::TestGuardrailDocsCrossCheck` | 5 | active |
| | **Total** | | **21** | |

The 21 tests are the Phase 51F behavior guardrail test
count. The Phase 52F report records this as
`total_existing_guardrail_tests: 21`.

## 4. Implemented structural guardrails (Phase 52F, G1-G6, 10 tests)

The 6 implemented structural guardrails from Phase 52F are:

### G1 — no direct sqlite3 / sqlalchemy imports outside app/persistence/*

* **Test class:** `TestG1NoDirectDbImportsOutsidePersistence`.
* **Test count:** 2.
* **Implementation status:** implemented.
* **False-positive risk:** none.
* **Required before Phase 53:** yes.
* **Enforcement scope:** all files outside
  `app/persistence/*` must not import `sqlite3` or
  `sqlalchemy` directly.
* **Owner:** Agent A (implementation) / Agent B (tracker
  update).
* **Phase 53 relevance:** high (every Phase 53 PR must
  satisfy G1).
* **Pilot relevance:** high (any pilot code change must
  satisfy G1).
* **External review relevance:** medium.

### G2 — no service imports main_web or main_api

* **Test class:** `TestG2NoServiceImportsMainWebOrApi`.
* **Test count:** 2.
* **Implementation status:** implemented.
* **False-positive risk:** none.
* **Required before Phase 53:** yes.
* **Enforcement scope:** no service imports in `main_web.py`
  or `main_api.py`; complements the existing 51F guardrail.
* **Owner:** Agent A (implementation) / Agent B (tracker
  update).
* **Phase 53 relevance:** high.
* **Pilot relevance:** high.
* **External review relevance:** medium.

### G3 — no sqlite3.Connection or sqlite3.connect instantiation outside app/persistence/*

* **Test class:** `TestG3NoDirectConnectionInstantiationOutsidePersistence`.
* **Test count:** 1.
* **Implementation status:** implemented.
* **False-positive risk:** none.
* **Required before Phase 53:** yes.
* **Enforcement scope:** no `sqlite3.Connection` or
  `sqlite3.connect` instantiation outside
  `app/persistence/*`.
* **Owner:** Agent A (implementation) / Agent B (tracker
  update).
* **Phase 53 relevance:** high.
* **Pilot relevance:** high.
* **External review relevance:** medium.

### G4 — no service or route imports get_cursor directly

* **Test class:** `TestG4NoServiceImportsGetCursor`.
* **Test count:** 1.
* **Implementation status:** implemented.
* **False-positive risk:** low (would only trigger on
  unusual variable name use of `get_cursor` outside
  persistence).
* **Required before Phase 53:** yes.
* **Enforcement scope:** no service or route may import
  `get_cursor` directly; they must use the public surface
  of the persistence layer.
* **Owner:** Agent A (implementation) / Agent B (tracker
  update).
* **Phase 53 relevance:** high.
* **Pilot relevance:** high.
* **External review relevance:** medium.

### G5 — repository.py has the single-transaction pattern

* **Test class:** `TestG5RepositorySingleTransactionPattern`.
* **Test count:** 3.
* **Implementation status:** implemented.
* **False-positive risk:** none.
* **Required before Phase 53:** yes.
* **Enforcement scope:** `repository.py` must use the
  single-transaction pattern (3 tests).
* **Owner:** Agent A (implementation) / Agent B (tracker
  update).
* **Phase 53 relevance:** high.
* **Pilot relevance:** high.
* **External review relevance:** medium.

### G6 — services use public surface of repository only

* **Test class:** `TestG6ServicesUsePublicSurfaceOnly`.
* **Test count:** 1.
* **Implementation status:** implemented.
* **False-positive risk:** none.
* **Required before Phase 53:** yes.
* **Enforcement scope:** services must use the public
  surface of the repository only; no private attribute or
  function access.
* **Owner:** Agent A (implementation) / Agent B (tracker
  update).
* **Phase 53 relevance:** high.
* **Pilot relevance:** high.
* **External review relevance:** medium.

### Summary

* **Total G1-G6 tests:** 10.
* **Total existing + implemented tests:** 21 + 10 = 31.

The 21 → 31 behavior guardrail test count change is the
project's internal self-assessment. The change is verified
by the Phase 52F report.

## 5. Deferred guardrails (Phase 52F, D1-D4, not implemented)

The 4 deferred guardrails from Phase 52F are:

### D1 — route no-refattening

* **Implementation status:** deferred.
* **Deferred to:** Phase 53G/53J (manual). *(As of branch
  creation, 53F and 53G were planned but not yet executed
  by Agent A; 53A and 53B have since merged on main. The
  deferral target is a planning convention.)*
* **False-positive risk:** high.
* **Reason for deferral:** sensitive to inline comments,
  blank lines, and docstring counting; would be brittle.
* **Owner:** Agent A (deferral owner) / Agent B (tracker
  update).
* **Phase 53 relevance:** low (manual review only).
* **Pilot relevance:** low.
* **External review relevance:** low.

### D2 — service-count / no-new-service-without-justification

* **Implementation status:** deferred.
* **Deferred to:** Phase 53F (soft check). *(As of branch
  creation, 53F was planned but not yet executed by Agent A;
  53A and 53B have since merged on main. The deferral target
  is a planning convention.)*
* **False-positive risk:** medium.
* **Reason for deferral:** count-only check is brittle;
  justification check is too opinionated.
* **Owner:** Agent A (deferral owner) / Agent B (tracker
  update).
* **Phase 53 relevance:** medium.
* **Pilot relevance:** low.
* **External review relevance:** low.

### D3 — UI context key contract

* **Implementation status:** deferred.
* **Deferred to:** Phase 54.
* **False-positive risk:** high.
* **Reason for deferral:** context surface is large; key
  names not documented in a single place.
* **Owner:** Agent A (deferral owner) / Agent B (tracker
  update).
* **Phase 53 relevance:** low.
* **Pilot relevance:** low.
* **External review relevance:** low.

### D4 — docs no-go scanner

* **Implementation status:** deferred.
* **Deferred to:** Phase 54+.
* **False-positive risk:** high.
* **Reason for deferral:** docs surface is large;
  regex-based scanner would have high false-positive risk.
* **Owner:** Agent A (deferral owner) / Agent B (tracker
  update).
* **Phase 53 relevance:** low.
* **Pilot relevance:** low.
* **External review relevance:** high (a docs no-go scanner
  would help the B-track governance review process; the
  tracker is the manual process that fills that gap until
  the scanner is implemented).

## 6. Future governance guardrails (proposed, not implemented)

The following are future governance guardrails that are
**not** implemented in this branch and are explicitly
**not** implemented as a part of B27:

* **Route-thinness guardrail** — measure the post-Phase 51
  route thinness; a soft check that flags routes that
  exceed a line threshold. Post-51 lessons, not
  implemented here.
* **Service-count guardrail** — measure the post-Phase 51
  service count; a soft check that flags when a new
  service is created without a justification. Post-51
  lessons, not implemented here.

These are post-51 lessons, **not** implemented as a part
of B27. The D1 and D2 deferred guardrails track similar
concerns.

## 7. Phase 53 required guardrails

The Phase 52F report lists the following as required before
Phase 53:

* G1, G2, G3, G4, G5, G6.

All 6 are already implemented. The Phase 53 PRs must
continue to satisfy the 6 guardrails. If a Phase 53 PR
breaks a guardrail, the PR is blocked per the B25 hard-
stop conditions.

## 8. Phase 54 required guardrails

The Phase 52F report lists the following as required before
Phase 54:

* D3 (UI context key contract).

D3 is the only Phase 54 guardrail. D1, D2, D4 are not
required before Phase 54.

## 9. What this tracker is not

* It is not a code change. Agent B does not implement
  guardrails.
* It is not a contract. The guardrail adoption tracker is
  the B-track governance wrapper for the Agent A guardrail
  work.
* It is not external validation. The guardrail adoption
  tracker is internal governance.
* It is not a substitute for the Phase 52F report or any
  other B-track artifact.
* It is not Claude review. Claude review is separate.
* It is not the post-51T review. The post-51T review is
  separate.

## 10. Cross-references

* `reports/governance/phase52_53_guardrail_adoption_tracker.json`
  (B27, machine-readable)
* `docs/governance/post_phase52_governance_refresh.md` (B24)
* `docs/governance/phase53_risk_gate_matrix.md` (B25)
* `docs/validation/phase53_must_pin_evidence_tracker.md` (B26)
* `docs/pilot/post_phase52_pilot_external_readiness_delta.md`
  (B28)
* `docs/governance/phase53_change_control_checklist.md` (B29)
* `reports/phase52f_persistence_guardrail_specifications.json`
  (Phase 52F source)
* `docs/external_review/external_review_closeout_tracker.md`
  (B16)

---

*End of Phase 52/53 guardrail adoption tracker.*
