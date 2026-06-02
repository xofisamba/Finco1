# Generic Validation No-Go Boundaries

This file is the explicit list of claims and behaviours the project
will **not** make, will **not** infer, and will **not** allow a
third party to make on the project's behalf, regarding generic solar
and wind validation.

It is a focused supplement to `docs/external_review/no_go_claims.md`,
restricted to generic validation. The B1 no-go list is the
general-purpose list; this file expands the generic-solar and
generic-wind entries with the boundaries specific to the B2
acquisition process.

---

## 1. What this file covers

* Generic solar PV (utility-scale, ground-mounted, fixed-tilt or
  single-axis tracker).
* Generic onshore wind (utility-scale; offshore only if a dedicated
  source produces a reference).
* Generic BESS / hybrid (Solar+BESS, Wind+BESS) is partially
  covered where the BESS portion interacts with the generic solar
  or wind portion. The full BESS / hybrid no-go boundary is in
  `docs/external_review/no_go_claims.md`.

Out of scope of this file:

* the project-internal reference templates TUHO and Oborovo, which
  are pinned (Phase 51F) and have their own boundaries documented
  in the B1 package;
* specific lender, bank, audit, certification, regulatory, or SaaS
  claims, which are covered by the general no-go list.

## 2. The hard no-go rules

### 2.1 No claim of "generic solar validation" until parity exists

The project will **not** make any claim — written, oral, marketing,
sales, internal, or external — that "generic solar is validated,"
"the model is correct for any solar project," or any equivalent
statement, until:

* at least three independent generic-solar references are accepted
  in the inventory with `parity-pass` status;
* the parity results have been internally reviewed;
* the B3 validation evidence matrix has been updated to move
  `AREA-003 (generic solar modeling)` from `exploratory` to a
  stronger category, with the documented evidence;
* a dedicated governance change has been recorded.

Until then, the strongest claim the project makes about generic
solar is: *"the model is implemented, exercised by internal
validation cases, and is being prepared for generic parity
validation. Generic solar claims are not supported."*

### 2.2 No claim of "generic wind validation" until parity exists

The same boundary as §2.1 applies to generic wind, with respect to
`AREA-004 (generic wind modeling)` in the B3 matrix.

### 2.3 No use of TUHO or Oborovo as generic-solar or generic-wind evidence

TUHO is a specific wind project configuration. Oborovo is a
specific solar project configuration. Neither constitutes evidence
for *generic* solar or *generic* wind parity. The project will not
use TUHO or Oborovo outputs to support any generic claim, and will
not allow a third party to do so.

### 2.4 No relaxation of acceptance thresholds without governance

The default acceptance thresholds in
`generic_solar_reference_requirements.md` §5 and
`generic_wind_reference_requirements.md` §5 are project defaults.
Relaxing them for a specific reference (e.g. to accept a wider
tolerance) requires:

* a recorded rationale in the inventory entry;
* an internal review of the rationale;
* an explicit, separate entry in the readiness matrix
  (`generic_validation_readiness_matrix.json`) recording the
  relaxation.

Relaxations are tracked and visible. They are not silent.

### 2.5 No acceptance of "essentially TUHO" or "essentially Oborovo" references

A reference that is a minor variation of TUHO, Oborovo, or any other
Finco1-produced model is rejected as a generic-solar or
generic-wind reference. The inventory records the rejection
rationale.

### 2.6 No representation of reference outputs as the Finco1 model's outputs

A reference is used to validate the Finco1 model, not to *be* the
Finco1 model. The project will not present reference outputs as
Finco1 model outputs, and will not allow a third party to do so.

### 2.7 No external-claim language in any pilot or B7 run

The B7 controlled pilot may use a generic-solar or generic-wind
reference as a *scenario* (not as a generic validation). The
pilot is an internal-validation activity with a real human in the
loop; it does not produce a generic-validation claim.

## 3. The enforcement boundary

The boundaries in §2 are enforced by:

* the B3 validation evidence matrix
  (`reports/validation/validation_evidence_matrix.json`) — the
  `external_claim_allowed` and `pilot_claim_allowed` flags on
  `AREA-003` and `AREA-004` remain `false` until the criteria in
  §2.1 and §2.2 are met;
* the B2 acquisition workflow — the inventory records the
  rejection rationale for any rejected candidate, including
  §2.5;
* the B2 readiness matrix
  (`reports/generic_validation/generic_validation_readiness_matrix.json`)
  — the count of accepted references per technology is the gate
  for promotion;
* the B1 no-go claim list — applies in full to any B2-related
  language;
* the B7 pilot protocol — applies in full to any B2-related
  scenario.

A breach of any of these is a serious issue. The remedy is to
revert the breach, identify how it happened, and update the
process to prevent recurrence.

## 4. What changes the boundary

The boundary is changed only by:

* a dedicated, future governance change, with explicit approval
  recorded;
* a corresponding update to this file and to the B3 matrix;
* at least three accepted generic references per technology, with
  parity results internally reviewed;
* a relaxation entry in
  `generic_validation_readiness_matrix.json` for any tolerance
  relaxation.

The boundary is **not** changed by:

* a single accepted reference;
* a successful pilot;
* an internal reviewer's go-opinion;
* a sales opportunity or customer request.

## 5. Cross-references

* `docs/generic_validation/generic_reference_acquisition_plan.md`
* `docs/generic_validation/generic_solar_reference_requirements.md`
* `docs/generic_validation/generic_wind_reference_requirements.md`
* `reports/generic_validation/reference_model_inventory_template.json`
* `reports/generic_validation/generic_validation_readiness_matrix.json`
* `docs/validation/validation_evidence_matrix.md`
* `reports/validation/validation_evidence_matrix.json`
* `docs/external_review/no_go_claims.md`
* `docs/validation/internal_vs_external_validation_boundaries.md`

---

*End of generic validation no-go boundaries.*
