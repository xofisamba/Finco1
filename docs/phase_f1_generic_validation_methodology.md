# Phase F1 — Generic Solar / Wind Validation Methodology

> Type: docs-only, design-only
> Branch: `phase-f1-generic-validation-methodology`
> Base SHA: `647818f66de00a35605f0609e1450883f29ae5f2` (post-closure-review)
> Status: DRAFT, do not mark ready, do not merge
> Scope: **framework definition only** + high-level migration sketch
> Hard boundary: Generic Wind and Generic Solar **remain Exploratory / Unvalidated** after F1. F1 does NOT promote either project.

## 0. Why F1 exists

The depreciation arc (D1 + D2 redo + D3 redo + closure review) is now
closed on `main`. The closure review recommended, in order, the
following next roadmap arc:

1. **Generic Solar / Wind validation methodology** ← this document
2. CAPEX schedule / construction IDC design gate
3. OPEX line-item visibility expansion
4. Formula transparency expansion

F1 implements item (1). It defines a formal validation framework
that allows FincoGPT to evolve from its current "TUHO + Oborovo as
frozen-template parity references, Generic Wind/Solar as exploratory"
posture toward a posture where Generic Wind and Generic Solar can
be promoted to "Reference" and ultimately "Validated" status —
**without weakening the parity or audit standards** that the existing
two reference projects (TUHO, Oborovo) are held to.

F1 is **not** a runtime implementation, not a schema change, not a
UI change, and not a parity change. F1 is a governance /
validation framework. The actual Generic Wind / Generic Solar
migration execution belongs to F2 (Wind) and F3 (Solar), which
will be scoped in their own follow-up prompts.

## 1. Terminology — inherited from existing codebase

F1 inherits and formalizes the existing terminology. F1 does **not**
introduce replacement terminology.

| Term | Existing usage in codebase | F1 status |
|---|---|---|
| `Validated` | used in `docs/external_review/model_scope_and_limitations.md` and the D1 audit sheet to describe a project whose outputs have been verified end-to-end | **inherited** |
| `Reference` | D1 sheet uses "Reference-status only" and "frozen-template parity references" to describe TUHO/Oborovo | **inherited** |
| `Exploratory / Unvalidated` | D1 sheet uses `EXPLORATORY / UNVALIDATED` badge for Generic Wind / Generic Solar; "Generic projects are out of scope for the active runtime path" | **inherited** |

These three terms form the **F1 status taxonomy** (§3 below). F1
adds a fourth level — `Concept` — to cover projects that do not
yet have an input pack. See §3.

F1 explicitly **does not** use "Production Ready", "Bankable",
"Lender-Approved", or any synonym of these terms. F1 does not
claim and does not allow future phases to claim such status. See
§9 (forbidden claims) and the existing
`docs/external_review/no_go_claims.md` floor.

## 2. What "Validated" means

A project is **Validated** if and only if **all** of the following
objective criteria are met:

1. **Excel parity achieved** — the model outputs match the pinned
   reference Excel workbook to within the documented tolerance
   (Phase 51F parity guardrails must be green for the project).
2. **Test coverage threshold** — a per-feature test pack exists
   with documented coverage threshold; the project's dedicated
   test files must pass in isolation and in the full 57-arc stack.
3. **Audit exports available** — the project produces a
   `Depreciation Audit` sheet (D1) and a full export with the
   parity-validated sheets.
4. **Known limitations documented** — a `KNOWN_LIMITATIONS.md`
   file in `docs/validation/<project>/` enumerates every documented
   limitation, with a risk rating and a mitigation.
5. **Reviewer sign-off completed** — at least one external
   reviewer (per the project's external review process) has
   signed off on the validation pack. The sign-off must include
   the closure review format used for the depreciation arc.
6. **Golden dataset exists** — a frozen input set and frozen
   expected output set, both versioned, both committed to the
   repository, both referenced by the test pack.

All six criteria are required. A project missing any one is
**not** Validated; it is one of the lower levels (§3).

### 2.1 What "Validated" does not mean

- "Validated" does **not** mean lender-approved, bank-grade, or
  bankable. See §9 and `docs/external_review/no_go_claims.md`.
- "Validated" does **not** mean the project is correct under all
  possible inputs. It means correct for the frozen input set
  documented in the validation pack.
- "Validated" does **not** mean the model is complete. New
  features may require a new validation pass.

## 3. Maturity ladder

F1 defines a **4-level maturity ladder**. F1 does **not** use
"Production Ready" as a level (see §C of the design brief: the
"Production Ready" label may overclaim commercial / bankability
status).

| Level | Name | One-line definition | F1 status |
|---|---|---|---|
| 0 | Concept | A project idea exists; no input pack, no Excel reference, no test pack. | new in F1 |
| 1 | Exploratory / Unvalidated | An input pack exists; the model can run the project; no parity, no test pack, no known-limitation doc. | inherited |
| 2 | Reference | Excel parity achieved and pinned; audit exports available; known limitations documented; test pack exists and passes; rc1-level freeze applies. | inherited (TUHO, Oborovo) |
| 3 | Validated | All six §2 criteria met, including external reviewer sign-off and a golden dataset. | inherited |

A project moves **up** the ladder by satisfying the criteria of
the next level. A project moves **down** the ladder if any of the
criteria for its current level are violated (e.g. a parity
regression, a test failure, a stale limitation doc). Movement
between levels is **explicit** and **gated**; see §10.

### 3.1 Level 0 — Concept

A project is at Level 0 if:

- A project idea exists (e.g. "Generic Wind 80MW", "Generic Solar
  50MW").
- There is no committed input pack, no Excel reference, no
  test pack, and no known-limitation doc.
- The project may or may not be constructable by the project
  factories; if it is, it is treated as Level 1.

F1 does not require Level 0 projects to be in the codebase. The
Level 0 definition is for future reference, not for current
Generic Wind / Generic Solar (which are Level 1 today).

### 3.2 Level 1 — Exploratory / Unvalidated

A project is at Level 1 if:

- A committed input pack exists (under `domain/inputs.py` /
  `app/project_factories.py` or equivalent).
- The model can run the project end-to-end.
- The project can be selected in the UI (today's Generic Wind
  and Generic Solar are Level 1).
- The D1 audit sheet correctly shows the project as
  `EXPLORATORY / UNVALIDATED`.
- **No** parity evidence exists.
- **No** test pack exists, or the test pack is limited to
  smoke / non-parity tests.
- **No** known-limitation doc exists, or it is incomplete.

Today (post-closure-review): **Generic Wind and Generic Solar are
both at Level 1.** F1 does not change this. F1 only defines the
framework and the migration sketch (§6, §7).

### 3.3 Level 2 — Reference

A project is at Level 2 if all of the following are true:

- An Excel reference workbook is committed and pinned.
- The Phase 51F parity guardrails are green for the project.
- The project's outputs are bit-for-bit identical (or within
  the documented tolerance) to the Excel reference for the
  frozen input set.
- A `KNOWN_LIMITATIONS.md` exists and is current.
- A test pack exists; the project's dedicated tests pass in
  isolation and in the full 57-arc stack.
- The project is referenced by the closure-review-style audit
  posture (D1 sheet, D2 redo discipline, D3 redo shadow).
- The project does **not** have a "Validated" sign-off from an
  external reviewer.

Today: **TUHO and Oborovo are at Level 2.**

### 3.4 Level 3 — Validated

A project is at Level 3 if, in addition to all Level 2 criteria:

- A golden dataset exists (frozen input set + frozen expected
  output set, both committed and versioned).
- An external reviewer has signed off on the validation pack
  using the closure-review format.
- The validation pack is referenced from
  `docs/validation/<project>/` and is current.

Today: **no project is at Level 3.** TUHO and Oborovo are at
Level 2 pending external review.

## 4. Validation pack contents

For a project to be promoted to Level 2 or Level 3, a
**validation pack** must exist. The pack is a directory under
`docs/validation/<project>/` with the following structure:

```
docs/validation/<project>/
├── README.md                    # project status, level, governance
├── KNOWN_LIMITATIONS.md         # every documented limitation
├── excel_reference/
│   ├── README.md                # which workbook, which version
│   └── <workbook>.xlsx          # pinned reference workbook
├── parity/
│   ├── README.md                # parity methodology + tolerance
│   ├── extraction.csv           # extracted reference values
│   └── results.json             # last-run parity results
├── test_pack/
│   ├── README.md                # test pack scope and threshold
│   └── test_<project>_<feature>.py  # dedicated tests
├── golden_dataset/              # required for Level 3 only
│   ├── inputs.json              # frozen input set
│   ├── expected_outputs.json    # frozen expected outputs
│   └── README.md                # how to reproduce
└── reviewer_signoff/            # required for Level 3 only
    ├── README.md
    └── <reviewer>_<date>.md
```

A Level 2 pack is the same minus the `golden_dataset/` and
`reviewer_signoff/` directories.

## 5. Reference projects today

| Project | Level | Reference workbook | Parity | Test pack | Sign-off |
|---|---|---|---|---|---|
| TUHO Wind 1 | 2 | `tuho_excel_1.xlsm` (or current pinned) | within tolerance | exists | pending |
| Oborovo Solar PV | 2 | `excel_oborovo.xlsx` (or current pinned) | within tolerance | exists | pending |

TUHO and Oborovo are the **only** Level 2 projects today. Any
claim that another project is at Level 2 is unsupported by F1
and by the closure review.

## 6. Migration sketch — Generic Wind (Exploratory → Reference → Validated)

This is a **high-level migration sketch only.** F1 does **not**
design the Generic Wind validation pack. The detailed execution
belongs to F2.

### 6.1 Generic Wind — current state (Level 1)

- Input pack exists in `app/project_factories.py`
  (`create_default_generic_wind` or equivalent).
- D1 audit sheet shows `EXPLORATORY / UNVALIDATED`.
- No Excel reference workbook.
- No parity evidence.
- No dedicated test pack (or smoke-only).
- No `KNOWN_LIMITATIONS.md`.

### 6.2 Generic Wind — Level 1 → Level 2 (Reference)

The Generic Wind migration to Level 2 requires, at minimum:

1. **Excel reference workbook.** Either (a) acquire or build a
   representative Wind Excel model with the same primitives
   (revenue, OPEX, CAPEX, debt, waterfall, distributions) that
   the FincoGPT model implements, or (b) construct a synthetic
   reference workbook from the FincoGPT model itself, with all
   formulas documented.
2. **Parity comparison.** Run the FincoGPT model against the
   frozen input set; extract the relevant outputs; compare to
   the Excel reference; document the deltas. The Phase 51F
   parity workflow is the gate.
3. **Known-limitations doc.** Every Generic-Wind-specific
   limitation must be enumerated. At minimum: parameter
   coverage (does Generic Wind cover all the cases the user
   would expect?); formula coverage (which Excel formulas
   are / are not implemented?); parity tolerance (which
   differences are within / outside the documented tolerance?).
4. **Dedicated test pack.** A new test file or set of test
   files dedicated to Generic Wind, covering smoke,
   parameter-validation, and parity. The test pack must
   pass in isolation and in the full 57-arc stack.
5. **D1 audit sheet update.** The Generic Wind row in the
   audit sheet must continue to show
   `EXPLORATORY / UNVALIDATED` until Level 2 is achieved;
   the update to `REFERENCE` is part of the F2 PR that
   achieves Level 2.

F1 does not execute any of the above. F1 only defines the
criteria.

### 6.3 Generic Wind — Level 2 → Level 3 (Validated)

After Level 2 is achieved, Generic Wind can be promoted to
Level 3 with:

1. **Golden dataset.** Freeze an input set and an expected
   output set; commit both; reference both from the test pack.
2. **External reviewer sign-off.** Per the project's external
   review process; sign-off format follows the closure-review
   style (D1 + D2 redo + D3 redo stack).
3. **Update to the model_scope_and_limitations doc.** The
   Generic Wind column moves from "exploratory" to "validated".

F1 does not execute any of the above.

## 7. Migration sketch — Generic Solar (Exploratory → Reference → Validated)

This is a **high-level migration sketch only.** F1 does **not**
design the Generic Solar validation pack. The detailed execution
belongs to F3.

The Generic Solar migration is structurally identical to the
Generic Wind migration (§6). The differences are:

- The input pack is in `app/project_factories.py`
  (`create_default_generic_solar` or equivalent).
- The Excel reference workbook is a Solar model
  (`excel_oborovo.xlsx` is the current Solar pinned
  reference, but it is the Oborovo-specific instance, not
  a generic reference).
- The known limitations for Generic Solar will differ
  from Generic Wind in parameter coverage (e.g. DC/AC ratio,
  tracker, albedo) and in tax-treatment specifics.
- The dedicated test pack is similarly Solar-specific.

F1 does not execute any of the above.

## 8. UI / export / audit labeling

F1 inherits the existing D1 audit-sheet language and recommends
**no change** to the user-facing wording. F1 only formalizes
the labels and their placement.

### 8.1 Project selector

| Project | Label | Source |
|---|---|---|
| TUHO Wind 1 | `REFERENCE` | D1 audit sheet (TUHO specific row) |
| Oborovo Solar PV | `REFERENCE` | D1 audit sheet (Oborovo specific row) |
| Generic Wind | `EXPLORATORY / UNVALIDATED` | D1 audit sheet (generic project row) |
| Generic Solar | `EXPLORATORY / UNVALIDATED` | D1 audit sheet (generic project row) |

### 8.2 Run banner

The run banner shows the project's current level (as
`REFERENCE` or `EXPLORATORY / UNVALIDATED`). The banner must
**not** show `VALIDATED` for any project today, because no
project is at Level 3.

### 8.3 Exports

Each export workbook shows the project's level in the
`Depreciation Audit` sheet (D1) and in any other audit sheet
that references project status. The level is shown as
`REFERENCE` or `EXPLORATORY / UNVALIDATED`, not as
`VALIDATED`.

### 8.4 Audit sheets

The D1 audit sheet already has the
`Generic_Project_Support: NO` row. F1 recommends that this
row be re-titled to a more accurate wording in a future
phase (e.g. `Generic_Project_Validation_Status`) — but
**not** in F1, because F1 is docs-only and does not modify
the export sheet code.

### 8.5 Runtime summary

The runtime summary (the validation-summary bar) shows the
project's level as part of the governance guard summary.
Existing wording — "Governance / Feature Guards" — is
preserved.

## 9. Forbidden claims

F1 explicitly **does not** allow the following claims to be
made about any project, regardless of its level. These
forbidden claims are an **extension** of the existing
`docs/external_review/no_go_claims.md` floor, not a
replacement.

A project is **not** allowed to be marketed, described, or
labelled as:

- `BANKABLE` / `BANK-GRADE` / `LENDER-APPROVED` / `LENDER-GRADE`
- `AUDITED` / `CERTIFIED` / `ACCREDITED`
- `PRODUCTION-READY` (for commercial / customer use)
- `REGULATORY-COMPLIANT` (under any regime)
- `INVESTMENT-GRADE`
- `IFRS-COMPLIANT` / `US-GAAP-COMPLIANT` (as a representation
  of compliance)

These claims are forbidden at all four levels (Concept,
Exploratory, Reference, Validated). The F1 framework
deliberately does not include a "Production Ready" level
(see §3) so that the framework itself does not invite such
claims.

In addition, the following are forbidden for Level 1
(Exploratory / Unvalidated) and Level 0 (Concept) projects
specifically:

- `VALIDATED` (the level name itself must not be applied
  to these projects)
- `REFERENCE` (the level name itself must not be applied
  to these projects)
- `PARITY ACHIEVED` (any parity-achieved claim requires
  Level 2 or above)
- `PARITY-LOCKED` (requires Level 2 or above, with all
  parity-locked files committed)
- `TRUSTED OUTPUT` (the D1 sheet's "trusted TUHO/Oborovo
  parity evidence" wording is forbidden for generic projects)

These claims are forbidden by the existing codebase wording
in D1, D2 redo, and D3 redo. F1 formalizes the list and
extends it with the F1-specific terms (`PARITY-LOCKED`,
`TRUSTED OUTPUT`).

## 10. Governance gates

Movement between levels is **explicit** and **gated**. F1
defines the gates; F1 does not implement any governance
process.

### 10.1 Promotion to Level 2 (Reference)

Requires:

- Validation pack (§4) is complete for Level 2 (without
  golden dataset or reviewer sign-off).
- All dedicated tests pass in isolation and in the full
  57-arc stack.
- Phase 51F parity guardrails are green for the project.
- The project's D1 audit sheet row is updated to `REFERENCE`
  (this update is part of the promotion PR, not a separate
  change).
- User sign-off (the human driving the project) explicitly
  approves the promotion.

### 10.2 Promotion to Level 3 (Validated)

Requires, in addition to §10.1:

- Golden dataset exists and is referenced by the test pack.
- External reviewer sign-off exists in the
  `reviewer_signoff/` directory.
- The model's `model_scope_and_limitations` doc column for
  the project is updated from "exploratory" to "validated".
- User sign-off (the human driving the project) explicitly
  approves the promotion.

### 10.3 Demotion from Level 2 or Level 3

Demotion is automatic if any of the following are detected:

- A parity regression in the Phase 51F parity guardrails.
- A dedicated test failure in the test pack that cannot be
  fixed within one sprint.
- A `KNOWN_LIMITATIONS.md` that has not been updated for
  more than 90 days while the project is still in active
  use.
- An external reviewer revokes their sign-off (Level 3 only).

Demotion is a **separate PR** that updates the project's
audit-sheet row back to `EXPLORATORY / UNVALIDATED` and
updates the `model_scope_and_limitations` doc column. The
demotion PR must include a written rationale.

## 11. Relationship to existing roadmap

The F1 framework interacts with the existing roadmap items
as follows.

### 11.1 CAPEX 2.0 / CAPEX sub-lines

CAPEX sub-lines (Phase 57A-9B/9C/9D/9E) are merged on main.
The CAPEX sub-lines work is **runtime-orthogonal** to F1:
it does not change the validation framework. However, the
CAPEX sub-line UX is part of the runtime surface that a
Level 2 / Level 3 Generic Wind / Generic Solar pack will
need to test. F2 / F3 should include CAPEX sub-line
coverage in the dedicated test pack.

### 11.2 Depreciation enablement

The depreciation arc is closed (closure review merged).
Depreciation is **runtime-orthogonal** to F1: it does not
change the validation framework. However, Generic Wind /
Generic Solar depreciation is a known open question
(canonicity, tax-bridge, book-pnl bridge); F2 / F3 must
either (a) keep the existing D1 sheet's `Generic_Project_Support: NO`
position and document the limitation, or (b) extend the
deprecation arc to cover generic projects in a future
governance review.

### 11.3 IDC schedule work

IDC (interest-during-construction) is a CAPEX-schedule
question. The CAPEX schedule / IDC design gate is the
**second** item on the closure-review-recommended roadmap
arc. F1 is **independent** of IDC; the two can proceed
in parallel. F2 / F3 should re-evaluate Generic Wind /
Generic Solar after the IDC design gate is settled, so
that the validation pack does not need to be re-validated
when IDC is added.

### 11.4 OPEX runtime

The OPEX runtime is the third item on the closure-review-
recommended roadmap arc. F1 is **independent** of OPEX
runtime. F2 / F3 should re-evaluate Generic Wind / Generic
Solar after the OPEX runtime is settled, for the same
reason as §11.3.

### 11.5 Formula transparency

Formula transparency is the fourth item on the closure-
review-recommended roadmap arc. F1 is **independent** of
formula transparency. Formula transparency will likely
**help** F2 / F3 because it will make it easier to write
the `KNOWN_LIMITATIONS.md` for each project, but the two
are independent.

## 12. Recommended sequence

The recommended sequence for the broader roadmap after F1:

### F1 (this PR)
Validation framework + migration sketch only. No runtime /
schema / UI / persistence / formula changes. Generic Wind and
Generic Solar remain at Level 1.

### F2 (next, Generic Wind → Reference)
Detailed design and execution of the Generic Wind migration
to Level 2. Includes: Excel reference workbook selection /
construction; parity comparison; known-limitations doc;
dedicated test pack; D1 sheet update. F2 is a
**multi-PR** phase; F1's job is to define what F2 must
deliver, not to deliver it.

### F3 (Generic Solar → Reference)
Same as F2, but for Generic Solar. F3 can run in parallel
with F2 if the team has the bandwidth; otherwise F3
follows F2 sequentially.

### F4 (TUHO / Oborovo → Validated, external sign-off)
External reviewer sign-off on the existing TUHO and Oborovo
Level 2 packs. F4 produces the `reviewer_signoff/`
directories for TUHO and Oborovo and updates the
`model_scope_and_limitations` doc to mark them as Validated.
F4 is the first phase that may legitimately use the
"Validated" label.

### F5 and beyond
After F4, the maturity ladder has been used end-to-end at
least once. F5 and beyond are governed by the F1 framework
and use the F1 promotion / demotion gates (§10).

## 13. Hard no-go list (F1)

- no code changes
- no runtime changes
- no UI implementation
- no schema changes
- no persistence changes
- no formula changes
- no parity changes
- no feature flags enabled
- no Generic project promotion (Generic Wind and Generic
  Solar remain at Level 1)
- no "bankable" / "lender-grade" / "production-ready" claims
- no modification of existing validation status (TUHO and
  Oborovo remain at Level 2; no project moves to Level 3
  in F1)

## 14. Forbidden paths (F1)

F1 does **not** modify:

- `app/**`
- `domain/**`
- `static/**`
- `main_web.py`
- `main_api.py`
- `tests/**`
- `reports/**` (except for the new F1 report file)

F1 only adds:

- `docs/phase_f1_generic_validation_methodology.md` (this file)
- `reports/phase_f1_generic_validation_methodology.json`

## 15. Stop-after-report contract

F1 is:

- A docs-only, design-only review.
- A framework definition + migration sketch only.
- No implementation, no runtime change, no flag enablement,
  no F2 / F3 start.
- No new tests, no new code, no new persistence, no new
  schema, no new export surface, no new UI.

Branch: `phase-f1-generic-validation-methodology`
PR: DRAFT only, do not mark ready, do not merge.
rc1 SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4` — untouched.

## 16. Appendix — terminology cross-reference

| Term | First defined in | F1 status |
|---|---|---|
| `Validated` | `docs/external_review/model_scope_and_limitations.md` | inherited as Level 3 |
| `Reference` | D1 audit sheet ("Reference-status only") | inherited as Level 2 |
| `Exploratory / Unvalidated` | D1 audit sheet ("EXPLORATORY / UNVALIDATED") | inherited as Level 1 |
| `Concept` | F1 | new in F1, Level 0 |
| `Production Ready` | rejected in F1 | explicitly NOT used |
| `Bankable` / `Lender-grade` | `docs/external_review/no_go_claims.md` | inherited, forbidden at all levels |

## 17. Appendix — open questions for F2 / F3

These are intentionally not answered in F1. They are
listed here as a starting point for the F2 / F3 prompts.

1. Where does the Generic Wind Excel reference workbook
   come from? (Acquire / build / synthesize)
2. What is the parity tolerance for Generic Wind?
3. What is the parity tolerance for Generic Solar?
4. Does Generic Wind need a CAPEX sub-line test, or is
   that out of scope for the F2 PR?
5. Does Generic Solar need a tracker / albedo test?
6. What is the depreciation strategy for Generic Wind /
   Generic Solar (deferred, or extended from D1-D3)?
7. How does the F2 / F3 PR interact with the existing
   `test_no_persistence_directory_changed` file-scope test?
8. Does F2 / F3 introduce any new D1 sheet rows, or only
   update existing rows?

These questions are intentionally open. F1's job is to
**define the framework**, not to answer them.
