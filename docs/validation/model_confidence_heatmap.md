# Model Confidence Heatmap

This file is the **management-level heatmap** of model confidence
by area. It is a roll-up view, not a replacement for the B3
validation evidence matrix
(`reports/validation/validation_evidence_matrix.json`). The
heatmap is for management and project-internal communication; the
B3 matrix is the authoritative evidence inventory.

> **The heatmap is internal planning. It is not external
> validation, not a customer reference, and not a
> production-readiness statement.** Confidence labels are
> project-internal self-assessments. Reaching a high confidence
> label does not authorize any external claim. See
> `docs/external_review/no_go_claims.md`.

---

## 1. Confidence labels

The heatmap uses the following conservative labels. Labels that
imply bankability, certification, audit approval, or external
validation are **not** used.

| Label | Meaning |
|---|---|
| `high_internal_confidence` | Internally pinned or golden-parity tested, internal-only; not externally validated. |
| `medium_internal_confidence` | Internally tested, with documented evidence; not externally validated. |
| `low_internal_confidence` | Implemented and tested at the broadest level only; sub-areas may vary. |
| `exploratory` | Research-stage or pre-validation; no parity evidence. |
| `blocked` | Intentionally not advancing. |
| `not_approved` | Exists in some form but not approved for any scope. |
| `external_review_needed` | Area is candidate for the next external review cycle. |
| `not_applicable` | The area does not apply to the current scope. |

The `external_review_needed` label is **not** a positive claim; it
is a forward-looking note that the area is on the project's list
for the next external review cycle. It does not authorize any
external claim.

## 2. Areas covered

The heatmap covers the following 18 areas:

* **Reference projects:** TUHO, Oborovo
* **Technology verticals:** generic solar, generic wind, BESS /
  hybrid
* **Financial areas:** senior debt, SHL, tax, sponsor economics,
  distributions
* **Output / UX areas:** Excel export, persistence / scenarios, UI
  warnings
* **Process areas:** governance, external review readiness,
  commercial claims readiness, paid pilot readiness, enterprise
  SaaS readiness

Each area is mapped to a single confidence label. The mapping
is the strongest label that honestly applies; conservative by
intent.

## 3. The heatmap

| Area | Confidence label | Source |
|---|---|---|
| TUHO (Wind 1) | `high_internal_confidence` | B3 AREA-001, Phase 51F pin |
| Oborovo (Solar PV) | `high_internal_confidence` | B3 AREA-002, Phase 51F pin |
| Generic solar | `exploratory` | B3 AREA-003, B2 framework only |
| Generic wind | `exploratory` | B3 AREA-004, B2 framework only |
| BESS / hybrid | `low_internal_confidence` | B3 AREA-005/006, waterfall in progress |
| Senior debt (TUHO / Oborovo scope) | `high_internal_confidence` | B3 AREA-008, Phase 51F pin |
| SHL | `low_internal_confidence` | B3 AREA-009, internally tested, not pinned |
| Tax | `low_internal_confidence` | B3 AREA-007, sub-area decomposition pending |
| Sponsor economics | `medium_internal_confidence` | B3 AREA-010, internally tested, not pinned |
| Distributions (TUHO / Oborovo scope) | `high_internal_confidence` | B3 AREA-011, partial Phase 51F pin |
| Excel export | `medium_internal_confidence` | B3 AREA-012, internally tested, not pinned |
| Persistence / scenarios | `low_internal_confidence` | B3 AREA-013, pin refresh pending after 51G-2/3/51H-1 |
| UI warnings | `low_internal_confidence` | B3 AREA-017, `implemented_but_unvalidated` at internal-test level |
| Governance | `high_internal_confidence` | B3 AREA-018, B1/B3/B2/B7/B8/B9–B14 governance in place |
| External review readiness | `external_review_needed` | B1 scaffolding in place; review not yet performed |
| Commercial claims readiness | `high_internal_confidence` | B11 commercial messaging guardrail in place |
| Paid pilot readiness | `low_internal_confidence` | B13 paid pilot gate defined; pilot not yet run |
| Enterprise SaaS readiness | `not_applicable` | B8 tracker: enterprise_saas_readiness is intentionally 10% with null target |

The heatmap is conservative. Areas that could plausibly be
labelled `high_internal_confidence` are labelled
`medium_internal_confidence` if they are internally tested but
not pinned. The reviewer is asked to disagree if they see a
stronger label applies.

## 4. What the heatmap is not

* It is not a marketing or sales artifact.
* It is not a customer reference.
* It is not external validation.
* It is not a substitute for the B3 matrix.
* It is not a guarantee of any specific output.

## 5. What the heatmap does

* Provides a management-level roll-up of model confidence.
* Cross-references the B3 matrix for each area.
* Uses conservative labels that do not imply bankability,
  certification, audit approval, or external validation.
* Is updated as part of normal B-track work (per the B14
  governance refresh plan).

## 6. Updating the heatmap

The heatmap is updated as part of normal B-track work, not as a
code change. The procedure:

1. Identify the area whose label is changing.
2. Update the area's row in the narrative file and the row in
   the JSON matrix.
3. Record the change in the JSON's `update_log` field.
4. Confirm that the new label is consistent with the B3 matrix's
   `evidence_category` for the same area.
5. If the new label introduces `external_review_needed` for a
   new area, ensure the B1 package and the B10 data room index
   are updated.

A label change that introduces a new green / yellow / red
boundary in the B11 commercial messaging guardrail is also a
B11 update.

## 7. Cross-references

* `reports/validation/model_confidence_heatmap.json` (B12,
  machine-readable)
* `docs/validation/validation_evidence_matrix.md` (B3 narrative)
* `reports/validation/validation_evidence_matrix.json` (B3
  matrix, authoritative)
* `docs/external_review/no_go_claims.md` (B1)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/governance/agent_a_b_governance_refresh_plan.md` (B14)

---

*End of model confidence heatmap narrative.*
