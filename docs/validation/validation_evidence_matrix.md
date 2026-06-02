# Validation Evidence Matrix

This file is the **narrative companion** to
`reports/validation/validation_evidence_matrix.json`. It explains how to
read the matrix, what each evidence category means, and which areas of
the model are covered. The JSON is the working artifact; this file
sets context, scope, and reading order.

> **No external validation is claimed anywhere in this file or its
> companion JSON.** The categories below describe *internal*
> validation posture only. See
> `docs/validation/internal_vs_external_validation_boundaries.md` for
> the explicit boundary between internal and external claims.

---

## 1. Purpose

The matrix answers the question: *for each area of the model, what
evidence do we have that the area behaves as documented, and what
evidence is missing?* It is intentionally conservative: a missing test
file is treated as missing evidence, not as "probably fine."

The matrix is not a sales, lender, audit, certification, regulatory,
or SaaS deliverable. It is a working artifact for the project team
and for future internal reviewers.

## 2. Companion documents

| File | Role |
|---|---|
| `docs/validation/validation_evidence_matrix.md` (this file) | Narrative companion and reading guide |
| `docs/validation/model_evidence_taxonomy.md` | Definition of every evidence category used in the matrix |
| `docs/validation/internal_vs_external_validation_boundaries.md` | What we will and will not claim externally |
| `reports/validation/validation_evidence_matrix.json` | Structured matrix (one row per area) |

The matrix JSON is the canonical artifact. This file and the other two
narrative documents explain it; they do not override it.

## 3. How to read a matrix row

Each row in the JSON has the following fields. Their meaning is
defined here, not in the JSON, to keep the JSON small.

| Field | Meaning |
|---|---|
| `area_id` | Stable identifier (`AREA-001`, `AREA-002`, ...). Referenced from other docs. |
| `area_name` | Human-readable area name. |
| `current_status` | The project's *documented* current state of the area (one short sentence). |
| `evidence_category` | The strongest evidence category that applies. See `model_evidence_taxonomy.md`. |
| `evidence_files` | Specific files in the repo that constitute evidence for this row. |
| `tests_or_reports_to_check` | Specific tests or report files the reviewer should open. |
| `missing_evidence` | What we know is missing. Empty list if the area is fully evidenced. |
| `external_claim_allowed` | `true`/`false`. Whether ANY external claim is permitted at this evidence level. |
| `pilot_claim_allowed` | `true`/`false`. Whether pilot-user testing is permitted as a next step. |
| `blockers` | Things that block promotion to a stronger evidence category. |
| `dependencies` | Other areas or workstreams that this row depends on. |
| `notes` | Free text, including any caveats. |

The matrix is **conservative by intent**: where a stronger category
*might* apply, the row is filed under the weaker one. A row that says
`current_status: "internally tested"` is the project's own
classification; the reviewer is expected to verify pass/fail locally
and is welcome to disagree.

## 4. Evidence categories (summary; full list in taxonomy)

The full taxonomy is in `model_evidence_taxonomy.md`. A short summary,
ordered from weakest to strongest:

1. `not implemented` — code is not present.
2. `implemented but unvalidated` — code is present; no test touches it.
3. `exploratory` — code is present; tested only at research level.
4. `internally tested` — at least one test exercises the area, with
   observed pass/fail to be confirmed by the reviewer.
5. `golden-parity tested` — outputs are pinned against a known
   reference (TUHO, Oborovo, or other). Pinned outputs are *not*
   externally validated.
6. `pinned / regression-protected` — Phase 51F guardrails cover this
   area; the parity-core lock or engine-output golden guardrail
   prevents silent regression. Still not externally validated.
7. `pilot-user tested` — a real human has used the feature in a
   controlled setting. Still not externally validated.
8. `externally reviewed` — a third party has read the code and
   produced a written opinion. Still not externally validated in the
   lender/bank/audit/regulatory sense.
9. `approved for narrow scope` — the area is approved for one or
   more explicitly named narrow use cases (e.g. TUHO Wind 1 only).
10. `approved for generic scope` — the area is approved for general
    use. **No area in this matrix currently claims this level.**
11. `blocked` — the area is intentionally not advancing. G20 is the
    canonical example.
12. `not approved` — the area exists in some form but has not been
    approved for any scope. R99, R102, `partial_pay_sweep`, and
    flat/min DSCR sculpting are canonical examples.

Categories 9 and 10 are project-internal approvals, **not** external
or third-party approvals. They do not authorize any external claim,
lender statement, audit assertion, regulatory filing, or SaaS
representation.

## 5. Scope of the matrix

The matrix covers the following areas (full list in the JSON):

* **Reference projects:** TUHO, Oborovo
* **Technology verticals:** generic solar, generic wind, BESS / hybrid
* **Financial areas:** tax, senior debt, SHL, sponsor economics,
  distributions
* **Output / UX areas:** Excel export, scenario persistence, UI
  warnings, governance
* **Project-internal guardrails:** Phase 51F guardrails, Phase 51G-1
  `/save-run` golden characterization
* **Documentation / evidence prep:** B1 external review package
  (PR #390, merged)

Each row is filed under the strongest evidence category that
honestly applies. The matrix deliberately lists areas even when the
strongest applicable category is `not implemented` or `exploratory`,
because the absence of a row would be misleading.

## 6. What this matrix is not

* It is not a sales artifact. It does not claim the model is
  production-ready for any specific customer.
* It is not a lender, bank, audit, certification, regulatory, or
  SaaS deliverable. It does not enable any external claim.
* It is not a substitute for the B1 external review package. B1 is
  the *documentation* layer; this matrix is the *evidence inventory*
  layer. They reference each other; they do not replace each other.
* It is not a complete inventory. A row is included only if the area
  is in scope of Finco1 today, or is on the explicit no-go list
  (G20, R99, R102, `partial_pay_sweep`, flat/min DSCR sculpting).

## 7. Updating the matrix

The matrix is a working artifact. Updating it is a normal B-track
operation, not a code change. A future update must:

* keep the JSON schema (field names and types) backward compatible;
* add a new `area_id` for any new area, do not reuse old IDs;
* move a row to a *stronger* evidence category only with explicit
  evidence (a passing test, a signed-off review, a piloted run);
* move a row to a *weaker* evidence category freely when evidence is
  found insufficient;
* never add an `external_claim_allowed: true` row without the
  corresponding external review;
* never weaken the no-go rows (G20, R99, R102, etc.) without a
  dedicated, explicitly approved PR.

## 8. Cross-references

* `docs/validation/model_evidence_taxonomy.md` — taxonomy details.
* `docs/validation/internal_vs_external_validation_boundaries.md` —
  what we do and do not claim externally.
* `reports/validation/validation_evidence_matrix.json` — the matrix.
* `docs/external_review/no_go_claims.md` — the no-go claim list.
* `docs/external_review/model_scope_and_limitations.md` — the B1
  description of model scope and limitations.
* `docs/phase51f_parallel_work_guardrails.md` — Phase 51F guardrail
  design (on the base SHA, not modified by this branch).

---

*End of validation evidence matrix narrative.*
