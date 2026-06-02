# Internal vs External Validation Boundaries

This file is the project's explicit statement of **what we will and
will not claim externally** about the model, and **where the line
sits** between internal validation work and external claims of any
kind.

It complements `docs/external_review/no_go_claims.md`, which is the
hard list of claims the project does not make. This file explains
*why* those claims are off-limits and *what is* on the table.

---

## 1. Definitions

For this file, the following terms have specific meanings. The terms
are scoped to the Finco1 project; they are not general-purpose
definitions.

* **Internal validation** — any evidence-gathering activity performed
  by the project team, including writing tests, running tests,
  comparing outputs to internal golden references, characterizing
  routes, piloting with internal users, and external review by a
  third party acting in a review (not assurance) capacity.
* **External claim** — any statement, written or oral, made to a
  party outside the project, that the model or any of its outputs
  are fit for a specific use, conform to a specific standard, are
  approved by a specific party, or carry any other assurance.
* **External validation** — an external claim backed by an external
  party that the project has engaged specifically to provide that
  assurance (e.g. an audit firm, a certification body, a regulatory
  filing, a lender's credit committee).

The internal / external line is **not** the same as the
internal-team / external-team line. A third-party reviewer doing an
*internal review* of the model is doing internal validation; a
third-party auditor signing off on the model is doing external
validation. The distinction is **who is making the assurance
claim**, not who is doing the work.

## 2. What the project does internally

The project performs, and the B-track workstreams document, the
following kinds of internal validation:

* **Code-level tests** under `tests/`. These are internal. They are
  evidence of internal testing; they are not external claims.
* **Golden-parity tests** (Phase 51F engine-output golden
  guardrail, plus any future golden pinning). These are internal.
  They pin the model against regression; they do not validate the
  model against any external benchmark.
* **Parity-core lock** (Phase 51F SHA-256 lock on the four
  parity-sensitive files). Internal refactor protection; not an
  external claim.
* **Route characterization** (Phase 51E-1, 51E-2, 51G-1 and
  successors). Internal documentation of current behavior; not an
  external claim.
* **Validation cases** under `validation/cases/`. Internal; not an
  external claim.
* **Pilot-user testing** (B7, future). Internal validation with a
  real human in the loop; not an external claim.
* **External review** (B1, future; the package is in place but no
  review has been performed yet at the time of writing). A
  third-party *opinion*, not an external *claim*; the reviewer is
  bound by the no-go claim list and is explicitly forbidden from
  producing any external-claim language.

## 3. What the project does not do, and will not do, at this time

The project does **not**, and will not, make any of the following
external claims. This is the same list as
`docs/external_review/no_go_claims.md`, restated for context.

### 3.1 Lender / bank / bankability

* lender-grade, bank-grade, bankable
* acceptable to any specific lender, bank, or financial institution
* sufficient for any loan-approval, debt-sizing, syndication, or
  refinancing decision
* aligned with any specific lender's credit policy, ICG, credit
  committee, or risk-rating framework

### 3.2 Audit / certification / regulatory

* audited, certified, accredited
* compliant with any regulatory regime (banking, securities, energy,
  tax, accounting, or otherwise)
* suitable for filing with any regulator, tax authority, or
  statistical agency
* aligned with IFRS, US GAAP, or any other accounting framework as a
  representation of compliance
* subject to any external assurance opinion

### 3.3 SaaS / product / commercial

* a SaaS product, a commercial offering
* production-ready for any specific customer
* covered by any SLA, warranty, support commitment, or service-level
  objective
* fit for any specific commercial, operational, or production use

### 3.4 Approval-of-not-approved-areas

The following are not approved, period: G20, R99, R102,
`partial_pay_sweep`, flat / min DSCR sculpting, generic solar (for
external claim), generic wind (for external claim). Internal
references to these areas are not approvals.

## 4. The line, in one sentence

> The project can make a written statement that *"we have internally
> tested this area, with these tests, and the tests pass"*; the
> project **cannot** make a written statement that *"this area is
> suitable for your specific use, in your specific context, with
> these specific consequences if you rely on it."*

The first kind of statement is internal validation. The second kind
is an external claim, and the project does not make it.

## 5. What the matrix is for

The Validation Evidence Matrix
(`reports/validation/validation_evidence_matrix.json`) is a working
artifact for the project team. It is:

* an internal record of what we know about each area;
* a planning tool for the next internal validation work;
* a transparency document for any future internal review.

It is **not**:

* a marketing or sales artifact;
* a deliverable for any external party;
* a substitute for the no-go claim list;
* a substitute for the B1 external review package.

## 6. What the pilot is for (B7)

The controlled pilot (B7) is an internal-validation activity with a
real human in the loop. It is the appropriate next step for areas
that are at least `internally tested` and want to graduate toward
`pilot-user tested`.

A pilot is **not**:

* a production rollout;
* a customer reference;
* an endorsement by the pilot user of the model as fit for any
  external purpose;
* an opportunity to relax the no-go claim list.

The pilot user's feedback is internal evidence. It is recorded,
categorized, and used to improve the model. It is not used to make
external claims.

## 7. What the external review is for (B1)

The B1 external review package
(`docs/external_review/external_review_package_index.md`) is the
scaffolding for a third-party *opinion* on the model. The opinion is
internal validation: the reviewer is asked to confirm or contest the
project's documented posture, not to provide an external assurance
opinion.

A successful external review produces:

* a written reviewer output, addressing each row in the readiness
  matrix;
* an explicit per-area go / conditional-go / no-go opinion;
* an explicit acknowledgement of the no-go claim list.

A successful external review does **not** produce:

* a lender-grade, bank-grade, audit-grade, certification-grade,
  regulatory-grade, or SaaS-grade statement;
* a relaxation of any no-go claim;
* a relaxation of any guardrail.

## 8. How this boundary is enforced

The boundary is enforced by:

* the no-go claim list (`docs/external_review/no_go_claims.md`);
* the B1 reviewer's required acknowledgement of the no-go claims;
* the validation evidence matrix's
  `external_claim_allowed: true/false` flags;
* the B7 pilot protocol's no-go enforcement;
* the project's general posture of conservative language in
  customer-facing materials.

A breach of the boundary is a serious issue. It is not a
documentation bug; it is a process failure. The remedy is to
revert the breach, identify how it happened, and update the
process to prevent recurrence.

## 9. What changes the boundary

The boundary is changed only by:

* a dedicated, future governance change, with explicit approval
  recorded;
* a corresponding update to the no-go claim list and the
  internal-vs-external boundaries document;
* an updated matrix where appropriate.

The boundary is **not** changed by:

* a passing test;
* a successful pilot;
* an internal reviewer's go-opinion on a specific area;
* a customer's request;
* a sales opportunity.

## 10. Cross-references

* `docs/external_review/no_go_claims.md` — the hard no-go list.
* `docs/external_review/external_review_package_index.md` — B1
  external review package.
* `docs/validation/validation_evidence_matrix.md` — narrative
  companion to the matrix.
* `docs/validation/model_evidence_taxonomy.md` — evidence category
  definitions.
* `reports/validation/validation_evidence_matrix.json` — the matrix.

---

*End of internal vs external validation boundaries.*
