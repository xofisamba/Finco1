# Pilot Pass / Fail Criteria

This file is the **per-area pass/fail criteria** for the controlled
pilot. It builds on the B3 validation evidence matrix
(`reports/validation/validation_evidence_matrix.json`) and the B7
issue categories. It is the rulebook for the per-metric
`pass / fail / investigate` decision that the pilot operator
records per run.

> **A pass is a positive internal signal. It is not external
> validation, not a customer reference, and not a
> production-readiness statement.** See
> `docs/pilot/controlled_pilot_runbook.md` and
> `docs/external_review/no_go_claims.md`.

---

## 1. Definitions

* **Must-pass metric.** A metric whose failure, in the per-area
  criterion, blocks pilot continuation.
* **Should-pass metric.** A metric whose failure records as
  `investigate` and is reviewed at the end of the run window; it
  does not block the pilot mid-run.
* **Informational metric.** A metric whose value is recorded for
  evidence but does not affect pass / fail.
* **Investigation trigger.** A condition that, when observed,
  moves the decision from `pass` to `investigate`. Investigated
  metrics are reviewed at the end of the run window.

Decisions are recorded per metric. The pilot run is `pass` if all
`must-pass` metrics pass. The pilot run is `fail` if any
`must-pass` metric fails. The pilot run is `investigate` if any
`should-pass` metric fails and no `must-pass` metric fails.

## 2. Per-area criteria

For each area, the per-area pass/fail criterion defines a short list
of metrics, their pass threshold, and their classification. The areas
below mirror the B3 matrix areas. Areas that are not
`pilot_claim_allowed: true` are out of pilot scope; their criteria
are not enforced.

### 2.1 AREA-001 — TUHO (Wind 1, 35 MW × 5 turbines)

| Metric | Source | Pass threshold | Classification |
|---|---|---|---|
| first_finite_dscr | Phase 51F pin | 1.450695 ± 0.001 | must-pass |
| first_distribution_op_idx | Phase 51F pin | = 35 (exact) | must-pass |
| total_operating_periods | Phase 51F pin | = 61 (exact) | must-pass |
| opex_total_keur | Phase 51F pin | 85408.27 ± 0.5 | must-pass |
| opex_y1_keur | Phase 51F pin | 1998.01 ± 0.5 | must-pass |

If the model output for any `must-pass` metric is outside the pass
threshold, the run is `fail` for TUHO.

### 2.2 AREA-002 — Oborovo (Solar PV, 75.26 MWp)

| Metric | Source | Pass threshold | Classification |
|---|---|---|---|
| first_finite_dscr | Phase 51F pin | 1.150038 ± 0.001 | must-pass |
| first_distribution_op_idx | Phase 51F pin | = 39 (exact) | must-pass |
| total_operating_periods | Phase 51F pin | = 60 (exact) | must-pass |
| opex_total_keur | Phase 51F pin | 48847.50 ± 0.5 | must-pass |
| opex_y1_keur | Phase 51F pin | 1338.56 ± 0.5 | must-pass |

Same `fail` rule as AREA-001.

### 2.3 AREA-003 / AREA-004 — Generic solar / generic wind

Out of pilot scope. `pilot_claim_allowed: false`. No criteria
enforced. If the pilot user attempts to run a generic-solar or
generic-wind input set, the run is recorded as `scope` per the B7
issue categories and not evaluated against pass/fail criteria.

### 2.4 AREA-007 — Tax (per-sub-area)

Tax is internally tested but not pilot-claim-allowed for the broad
area (per the patch to AREA-007 in the B3 matrix). If a tax
sub-area has been decomposed and the project-internal pilot
sub-scope is approved, the criteria are recorded in the per-sub-area
entry. Until then, no tax criteria are enforced at the pilot level.

### 2.5 AREA-008 — Senior debt (TUHO / Oborovo scope)

| Metric | Source | Pass threshold | Classification |
|---|---|---|---|
| Senior debt schedule (TUHO) | Phase 51F pin (parity-core SHA-256) | matches `reports/phase7_tuho_senior_debt_sizing_extraction.csv` exactly | must-pass |
| Senior debt schedule (Oborovo) | Phase 51F pin (parity-core SHA-256) | matches `reports/phase23q_oborovo_senior_debt_sizing_extraction.csv` exactly | must-pass |
| Senior debt schedule (any other input set) | not pinned | out of pilot scope until pin is added | n/a |

Senior debt claims are pinned for TUHO and Oborovo only. Generic
senior-debt claims are out of pilot scope.

### 2.6 AREA-010 — Sponsor economics (Project IRR, Equity IRR,
Sponsor IRR, NPV)

| Metric | Source | Pass threshold | Classification |
|---|---|---|---|
| Equity IRR (TUHO inputs) | internal | within ± 25 bps of pre-pilot reference value (recorded at pilot start) | should-pass |
| Equity IRR (Oborovo inputs) | internal | within ± 25 bps of pre-pilot reference value | should-pass |
| Project IRR (TUHO inputs) | internal | within ± 25 bps of pre-pilot reference value | should-pass |
| Project IRR (Oborovo inputs) | internal | within ± 25 bps of pre-pilot reference value | should-pass |

The pre-pilot reference value is recorded in the pilot summary.
Returns are not pinned by Phase 51F, so the criterion is
`should-pass` (not `must-pass`). A failure moves the decision to
`investigate`.

### 2.7 AREA-011 — Distributions (TUHO / Oborovo scope)

| Metric | Source | Pass threshold | Classification |
|---|---|---|---|
| first_distribution_op_idx (TUHO) | Phase 51F pin | = 35 (exact) | must-pass |
| first_distribution_op_idx (Oborovo) | Phase 51F pin | = 39 (exact) | must-pass |
| total distributions (TUHO) | internal | within ± 0.5% of pre-pilot reference value | should-pass |
| total distributions (Oborovo) | internal | within ± 0.5% of pre-pilot reference value | should-pass |

Same `fail` rule as AREA-001 for the pinned metrics; `investigate`
for the unpinned metrics.

### 2.8 AREA-012 — Excel export

| Metric | Source | Pass threshold | Classification |
|---|---|---|---|
| Excel export completes without error | internal | no exceptions | must-pass |
| Excel export contains required worksheets | internal | worksheet list matches the documented export spec | must-pass |
| Excel export numeric values match the model output | internal | all values match within the same tolerance as the corresponding model metric | must-pass |

Excel format drift is a known risk. A drift that does not break
numeric content is recorded as `investigate`; a drift that breaks
numeric content is `must-pass` failure.

### 2.9 AREA-013 — Scenario persistence (out of pilot scope)

Per the B3 matrix patch, `pilot_claim_allowed` for scenario
persistence is `true`, but the underlying area is in flux. The
criteria are: pin refresh and forward-compatibility decision must
be in place before pilot criteria are enforced. Until then, no
criteria are enforced at the pilot level.

### 2.10 AREA-016 — B1 external review package (documentation)

| Metric | Source | Pass threshold | Classification |
|---|---|---|---|
| B1 package present in repo at base SHA | internal | all 6 B1 files exist | must-pass |
| B1 readiness matrix has 28 areas (or current count) | internal | shape consistent with B1 package at base SHA | must-pass |
| No-go list is acknowledged by the pilot user and operator | internal | signed acknowledgement on file | must-pass |

### 2.11 AREA-017 — UI warnings

| Metric | Source | Pass threshold | Classification |
|---|---|---|---|
| UI warning behavior is exercised by at least one documented pilot run | internal | recorded in feedback | informational |
| Pilot user's UX feedback does not include unresolved warnings | internal | no `pilot-blocker` UX issue | should-pass |

UI warnings are presentation; the model is the source of truth.
Pilot user feedback is the appropriate evidence-gathering step for
UI warnings.

## 3. Pass / fail decision rules

The pilot run decision is the intersection of per-area decisions:

* If all `must-pass` metrics across all pilot-claim-allowed areas
  pass, the run decision is `pass`.
* If any `must-pass` metric fails, the run decision is `fail`.
* If no `must-pass` metric fails and any `should-pass` metric
  fails, the run decision is `investigate`.
* If the run is `scope` for any area (e.g. generic solar input set
  attempted), the area is recorded as `scope-out` but does not
  affect the run decision.

The run decision is recorded per run. The pilot overall is
`pass` if all runs in the run window are `pass`. The pilot overall
is `fail` if any run is `fail` and the failure is not accepted via
the B7 triage process. The pilot overall is `investigate` if any
run is `investigate` and no run is `fail`.

## 4. Investigation triggers

A run is moved from `pass` to `investigate` when any of the
following is observed:

* a `should-pass` metric fails;
* the model output is borderline (within 50% of the pass tolerance);
* an undocumented deviation is observed and the source is not yet
  known (B7 issue category `unexpected-behavior`);
* the run produces warnings not previously recorded;
* a TBD input is left in the run input set;
* the Excel export differs in worksheet count from the documented
  spec, even if numeric content matches.

A run in `investigate` is reviewed at the end of the run window.
The review may resolve to `pass` (with rationale), `fail` (with
rationale), or `defer` (with a recorded follow-up plan).

## 5. What this document is not

* It is not a contract. The criteria may be updated as part of
  normal B-track work; the reviewer should check the latest version.
* It is not external validation.
* It is not a substitute for the runbook, the feedback protocol, the
  triage process, or the support / incident response procedure.

## 6. Cross-references

* `docs/pilot/pilot_validation_execution_pack.md` (B9)
* `docs/pilot/pilot_evidence_capture_template.md` (B9)
* `docs/pilot/controlled_pilot_runbook.md` (B7)
* `docs/validation/validation_evidence_matrix.md` (B3 narrative)
* `reports/validation/validation_evidence_matrix.json` (B3 matrix)
* `docs/external_review/no_go_claims.md`

---

*End of pilot pass / fail criteria.*
