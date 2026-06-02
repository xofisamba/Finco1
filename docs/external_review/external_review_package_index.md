# External Review Package — Index

| Field | Value |
|---|---|
| Project | FincoGPT / Finco1 |
| Repository | `xofisamba/Finco1` |
| Branch (this package) | `parallel-b1-external-review-prep` |
| **Current base SHA (latest main)** | `2e41b24f8c47ec544e1ef52e35084646df4d4d8f` |
| **Prior base SHAs (provenance chain)** | `a53d278263f1f9e134d500e1a7915e9bde615626` (= Phase 51E-1) → `dfe13ab` (Phase 51E-2) → `a541d447063cf288b1a9ea0a7bbf199755e40d53` (Phase 51F) → `2e41b24f8c47ec544e1ef52e35084646df4d4d8f` (Phase 51G-1, current) |
| Workstream | B1 — external review preparation (docs/report only) |
| Owner of this PR | Agent B (parallel track; does **not** touch Agent A files) |
| Document type | External review preparation package |
| Status | Draft for external reviewer — **not** a marketing, lender, certification, audit, regulatory, or SaaS deliverable |

> The base SHA was rebased from `a53d278` to `2e41b24` because main moved
> through Phase 51E-2, Phase 51F, and Phase 51G-1. The prior SHAs are
> preserved in this index for provenance. **All reviewer verification
> must use the current base SHA.**

---

## 1. Purpose

This package assembles the current, conservative description of the Finco1
model state for an **independent external technical reviewer**. The goal
is to enable the reviewer to form a grounded opinion on:

1. what the model is, and is not, currently scoped to do;
2. what is internally pinned, internally tested, exploratory, or
   unvalidated;
3. what the project's own refactor-protection guardrails cover, and what
   they do not cover;
4. what claims the project explicitly does **not** support at this time.

The package does **not** itself contain model source, fixtures, or test
runs. Those live in the repository at the current base SHA. This package
is a **map**, not a copy of the territory.

## 2. Document map (read in this order)

| # | File | Role |
|---|---|---|
| 1 | `external_review_package_index.md` (this file) | Entry point, package map, base state |
| 2 | `reviewer_instructions.md` | How to use the package; what the reviewer must and must not assume |
| 3 | `model_scope_and_limitations.md` | Current model scope; validated / pinned / exploratory / unvalidated split; known limitations |
| 4 | `tuho_oborovo_validation_summary.md` | TUHO / Oborovo frozen-template scope and the Phase 51F golden values that pin them |
| 5 | `no_go_claims.md` | Hard list of claims the project does **not** support at this time |
| 6 | `external_review_readiness_matrix.json` | Structured readiness matrix (area × status × evidence × reviewer question) |

A structured, machine-readable form of the matrix is at:

```
reports/external_review/external_review_readiness_matrix.json
```

## 3. Branch and base

* **Current base commit:** `2e41b24f8c47ec544e1ef52e35084646df4d4d8f`
* **Branch:** `parallel-b1-external-review-prep`
* **PR intent:** docs and report only.

The reviewer must verify the current base SHA locally before forming
conclusions (see `reviewer_instructions.md` §2).

### 3.1 Base-SHA transition (since the prior draft)

The earliest draft of this package was prepared against
`a53d278263f1f9e134d500e1a7915e9bde615626`. Since then, main has moved
forward through the following merges:

| SHA (short) | Phase | Note |
|---|---|---|
| `a53d278` | (earliest base) | Phase 51E-1 — Download route golden characterization |
| `dfe13ab` | Phase 51E-2 | Extract download route orchestration — **on main**, not future work |
| `a541d44` | Phase 51F | Parallel-work and runtime-refactor guardrails — **on main and active** |
| `2e41b24` | **Phase 51G-1** (current) | POST /save-run golden characterization — **on main**, characterization only, no production code change |

Material changes across the provenance chain that affect this package:

* `/download` route orchestration is on main as of `dfe13ab` and is
  part of the code the reviewer inspects.
* **Three Phase 51F guardrails are active on main** and form part of
  the state the reviewer evaluates (see §4 below and
  `model_scope_and_limitations.md` §3.4).
* **Phase 51G-1 is on main as of `2e41b24`**: `POST /save-run` route
  is now characterized (pinned by 58 tests) but **not** extracted or
  re-implemented. The future extraction is Phase 51G-2, owned by
  Agent A. Agent B does not own `/save-run` and does not touch it in
  this PR.
* `a53d278` is no longer the tip of main and is preserved in this
  package only as provenance.

The package's substantive scope split (validated / pinned / exploratory
/ unvalidated) was rewritten at the Phase 51F rebase to reflect the
new base, and was patched at the Phase 51G-1 rebase to add the
`/save-run` characterization to the base state description. Statements
that were true at the prior base but false at the current base have
been removed or corrected.

## 4. Active guardrails at the current base (Phase 51F)

Phase 51F, merged at the current base, introduces three behavior-level
guardrails. They are documented in detail in
`docs/phase51f_parallel_work_guardrails.md` and enforced by
`tests/test_phase51f_parallel_work_guardrails.py`. They are part of the
state under review.

1. **Engine-output golden guardrail.** Pins current model outputs (DSCR,
   first distribution period, total operating periods, OpEx totals)
   for the TUHO and Oborovo reference projects. Refactors of
   routes/services must not change these. Only an intentional model
   change updates them. Exact golden values are listed in
   `tuho_oborovo_validation_summary.md` §3.
2. **Parity-core lock guardrail.** Pins SHA-256 of four
   parity-sensitive files. Any unintended edit triggers the test.
   The locked files are:
   * `app/waterfall_core.py`
   * `app/project_factories.py`
   * `reports/phase7_tuho_senior_debt_sizing_extraction.csv`
   * `reports/phase23q_oborovo_senior_debt_sizing_extraction.csv`
3. **No-service-imports-main_web/main_api guardrail.** AST-walks every
   file in `app/services/*.py` and fails on any actual `import` of
   `main_web` or `main_api` (docstrings and comments are allowed). This
   preserves the one-way import direction established in Phase 51.

These guardrails are **not** external validation. They are
refactor-protection for the project itself, and the reviewer is
explicitly asked to evaluate them as such (see
`model_scope_and_limitations.md` §3.4 and the readiness matrix A25).

## 5. Scope of this PR (what is in, what is out)

### 5.1 In this PR (only these files)

* `docs/external_review/external_review_package_index.md`
* `docs/external_review/reviewer_instructions.md`
* `docs/external_review/model_scope_and_limitations.md`
* `docs/external_review/tuho_oborovo_validation_summary.md`
* `docs/external_review/no_go_claims.md`
* `reports/external_review/external_review_readiness_matrix.json`

### 5.2 Explicitly NOT in this PR

* No source-code changes.
* No route or service changes.
* No template or static-asset changes.
* No financial formula changes.
* No model output changes.
* No JavaScript financial calculations.
* No fixture CSV changes.
* No schema or migration changes.
* No persistence / repository changes.
* No changes to files owned by the parallel Agent A track.
* `rc1` is frozen and is **not** touched.
* No changes to Phase 51F parity-core files or to TUHO/Oborovo golden
  values. The golden values are described in this package for the
  reviewer's reference, not modified.

## 6. Parallel-track context (for the reviewer's awareness only)

The repository is being developed on two strictly separated parallel
tracks. The reviewer should understand this so they do not confuse
in-flight, isolated work with the validated baseline.

* **Agent A track.** Owns `main_web.py`, `main_api.py`, `app/services/**`,
  and the Phase 51+ route/service refactor work. The `/download`
  extraction (Phase 51E-2) is now on main and is part of the base. The
  next planned work is `/save-run`, scenario routes, project save-as,
  guardrails, and repository extraction. Agent A's in-flight branch and
  its outputs are **not** part of the base SHA used for this package.
* **Agent B track (this package).** Owns `docs/**` and `reports/**`
  work only. This external review preparation package is the first B1
  deliverable. No code, route, service, template, or fixture is touched.

The reviewer is being asked to evaluate the model as it exists at the
current base SHA, not as it might exist after any pending parallel work
merges.

## 7. Key guardrails (summary; full list in `no_go_claims.md`)

* `rc1` is frozen and must not be modified.
* PR #299 is closed and no longer active.
* Backend remains the source of truth.
* No JavaScript financial calculations.
* No financial formula changes; no model output changes; no fixture CSV
  changes; no schema/migration changes.
* G20 remains **BLOCKED**.
* R99 / R102 remain **NOT APPROVED**.
* `partial_pay_sweep` is **not** promoted.
* Flat / min DSCR sculpting is **not** promoted.
* Generic solar / wind remain **exploratory and unvalidated** for any
  external claim (see `model_scope_and_limitations.md` §3.4).
* **No** lender, bank, audit, certification, regulatory, or SaaS claims
  are made or implied by this package or by the model at the current
  base SHA.
* Phase 51F guardrails are project-internal refactor protection. They
  are not external validation.

## 8. What the reviewer is being asked to produce

See `reviewer_instructions.md` §6 for the full required output. At a
high level:

1. A signed statement that the current base SHA was verified.
2. A line-by-line response to the readiness matrix
   (`external_review_readiness_matrix.json`).
3. Answers to the required reviewer questions
   (see `model_scope_and_limitations.md` §6,
   `tuho_oborovo_validation_summary.md` §6, and the Phase 51F section
   in `model_scope_and_limitations.md` §3.4).
4. A clear go / conditional-go / no-go opinion per area.
5. An explicit confirmation that the reviewer has read and understood
   `no_go_claims.md` and will not reproduce, endorse, or imply any
   no-go claim in their output.

## 9. Versioning of this package

* This is the **fourth** version of the external review preparation
  package (v0.4.0). Version history:
  * v0.1.0 drafted at prior base SHA `a53d278` (no local repo
    available, drafted from project rules).
  * v0.2.0 rebased to base SHA `a541d447`; package rewritten to
    reflect the Phase 51F guardrails and the merge of Phase 51E-2.
  * v0.3.0 added a pre-flight test run by the package author at the
    base SHA: `tests/test_phase51f_parallel_work_guardrails.py` was
    executed locally and all **21 tests passed**.
  * v0.4.0 (this version) rebases the package onto the current base
    SHA `2e41b24` and adds the Phase 51G-1 `/save-run`
    characterization to the base state description. No new files
    were added; only the six existing B1 files were patched. The
    pre-flight result of 21/21 Phase 51F tests passing remains
    valid; Phase 51G-1 does not modify any parity-core file.
* Any future revision must be opened as a new branch and a new PR,
  never by rewriting history on `parallel-b1-external-review-prep`
  after a reviewer has already received the package.

---

*End of index.*
