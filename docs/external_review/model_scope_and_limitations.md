# Model Scope and Limitations

This file describes the current model scope at the current base SHA
(`2e41b24f8c47ec544e1ef52e35084646df4d4d8f`), separated into
**validated**, **pinned**, **internally tested**, **exploratory**, and
**unvalidated** areas, followed by the Phase 51F guardrails, known
limitations, and required reviewer questions.

The split below is **conservative by intent.** Where the project's
confidence is unclear, the area is moved one column to the right
(e.g. from "internally tested" to "exploratory"), not the other way.

---

## 1. Architecture, in one paragraph

Finco1 (FincoGPT) is a Python backend project-finance screening service
with a Streamlit UI and a Flask web layer (`main_web.py`, `main_api.py`).
The web layer is being progressively refactored in Phase 50/51/51E-2
into extracted services under `app/services/**`. The backend is the
**source of truth** for all financial calculations. The web layer and
templates must not perform any financial calculation; specifically,
**no JavaScript financial calculations** are present or planned in this
package's scope.

The model is parameterized by fixtures, project factories
(`app/project_factories.py`), and a `domain/**` package that produces
model runs consumed by `app/waterfall_core.py` and supporting
services. Persistence and reconciliation live under
`app/persistence/` and `app/reconciliation/`.

A release candidate `rc1` is **frozen**. Anything in `rc1` is not
modified by this PR or by the parallel Agent A track.

The Phase 51F guardrails (see §3.4) are project-internal refactor
protection. They are not external validation.

## 2. What's in scope at the current base SHA

The following areas are in the model and are exercisable at the current
base SHA. The list is descriptive, not exhaustive.

* Standard project / loan / debt modeling primitives exposed by
  `domain/**` and `app/project_factories.py`.
* Senior debt and core waterfall behavior implemented in
  `app/waterfall_core.py`, driven by the engines under
  `app/services/`.
* TUHO Wind 1 and Oborovo Solar PV reference projects constructed by
  `app/project_factories.py` (`create_default_tuho_wind1`,
  `create_default_oborovo`).
* Senior-debt sizing extraction CSVs at
  `reports/phase7_tuho_senior_debt_sizing_extraction.csv` and
  `reports/phase23q_oborovo_senior_debt_sizing_extraction.csv`. Both
  are pinned by Phase 51F.
* Web routes and services under `main_web.py`, `main_api.py`, and
  `app/services/**` (owned by Agent A; **not** modified by this PR, but
  listed for context).
  * `/download` route orchestration is on main (Phase 51E-2, `dfe13ab`).
  * `/save-run` route is now characterized on main (Phase 51G-1,
    `2e41b24`): `POST /save-run` exists in `main_web.py` lines
    2624–2760, and is pinned by 58 tests in
    `tests/test_phase51g1_save_run_route_golden_characterization.py`.
    Phase 51G-1 is **characterization only** — no production code
    change, no extraction, no financial formula or model output
    change. The future extraction is Phase 51G-2, owned by Agent A.
    Agent B does not own `/save-run` and does not touch it in this
    PR.
* Internal test suites under `tests/`, including:
  * Phase 51F guardrail tests at
    `tests/test_phase51f_parallel_work_guardrails.py`.
  * Phase 51G-1 golden characterization tests at
    `tests/test_phase51g1_save_run_route_golden_characterization.py`
    (58 tests, characterization only).
* Validation cases under `validation/cases/` (solar and wind cases).

## 3. Validated, pinned, internally tested, exploratory, unvalidated

For each area below, the status reflects the project's **documented**
posture. The reviewer must independently confirm by inspecting the
code, fixtures, and test outcomes at the current base SHA.

### 3.1 Validated

*No area is presented as externally validated by this package.* The
project does not, at the current base SHA, assert external validation
by any independent lender, bank, audit, certification, regulatory, or
SaaS party. The reviewer should not interpret "validated" in any
external or third-party sense.

### 3.2 Pinned by Phase 51F (engine-output golden + parity-core lock)

The following outputs and files are **pinned** at the current base
SHA by the Phase 51F guardrails. Pinning means: any change to these
values or files will cause a test failure on the base SHA, and such a
change must be made via a dedicated, intentional model-change PR
(per the protocol in
`docs/phase51f_parallel_work_guardrails.md`).

This is **regression protection**, not external validation. The values
are pinned so the next refactor does not silently change them; they
are not pinned because an external party has verified them.

| Pinned item | File / test | Notes |
|---|---|---|
| TUHO first finite DSCR ≈ 1.450695 (±0.001) | `tests/test_phase51f_parallel_work_guardrails.py` `TestEngineOutputGoldenTUHO` | Period idx 0, year 1 |
| TUHO first distribution op idx = 35 (exact) | same | First operating period with positive distribution_keur |
| TUHO total operating periods = 61 (exact) | same | Semiannual, 30y + construction overhang |
| TUHO OpEx total ≈ 85,408.27 kEUR (±0.5) | same | Sum over operating periods |
| TUHO OpEx year 1 (semiannual sum) ≈ 1,998.01 kEUR (±0.5) | same | First 2 operating periods |
| Oborovo first finite DSCR ≈ 1.150038 (±0.001) | `TestEngineOutputGoldenOborovo` | Matches target_dscr=1.15 policy |
| Oborovo first distribution op idx = 39 (exact) | same | |
| Oborovo total operating periods = 60 (exact) | same | |
| Oborovo OpEx total ≈ 48,847.50 kEUR (±0.5) | same | |
| Oborovo OpEx year 1 (semiannual sum) ≈ 1,338.56 kEUR (±0.5) | same | |
| `app/waterfall_core.py` SHA-256 lock | `TestParityCoreLock` | Locks parity-core engine |
| `app/project_factories.py` SHA-256 lock | same | Locks TUHO/Oborovo factory |
| `reports/phase7_tuho_senior_debt_sizing_extraction.csv` SHA-256 lock | same | Locks TUHO senior-debt schedule |
| `reports/phase23q_oborovo_senior_debt_sizing_extraction.csv` SHA-256 lock | same | Locks Oborovo senior-debt schedule |

The reviewer must run `pytest tests/test_phase51f_parallel_work_guardrails.py`
at the base SHA and confirm the guardrails pass.

### 3.3 Internally tested (other)

Other test suites exist in `tests/` beyond the Phase 51F guardrails.
The package names them for orientation (see §5.1) and explicitly does
**not** claim any specific pass/fail outcome. The reviewer must run
them.

### 3.4 Exploratory and unvalidated (must not be claimed externally)

The following areas exist in the repository or are referenced in
discussions, but are **not validated** and must not be treated as such.
The reviewer should treat these as research-stage, not as features that
can be relied on for any external claim.

| Area | Posture |
|---|---|
| Generic solar / wind modeling | **Exploratory and unvalidated** for external claim. The README describes solar/wind as "Full model" for screening purposes, and `validation/cases/` contains `solar_case_1.py`, `solar_case_2.py`, `wind_case_1.py`; **none of this constitutes external validation**, and the project explicitly does not make external claims about generic solar/wind. |
| G20 | **BLOCKED.** Code may exist; not approved, not validated, not externally claimable. |
| R99 / R102 | **NOT APPROVED.** Internal references only. |
| `partial_pay_sweep` | **Not promoted.** Internal reference only. |
| Flat / min DSCR sculpting | **Not promoted.** Internal reference only. |
| Any closed PR not merged at the current base SHA (e.g. PR #299) | Closed, not active, not part of the baseline. |

### 3.5 Unvalidated (general)

* All exploratory items in §3.4 are also unvalidated.
* Anything in this document marked "to be verified" is, by definition,
  unvalidated at the time of writing.
* Any template-, static-, or JavaScript-layer presentation of model
  output is presentation only; the model's correctness rests on the
  Python backend, and presentation correctness is not a substitute for
  validation.
* The Phase 51F pinned values are regression protection, not
  validation. Pinning the current output does not validate it.

## 4. Phase 51F guardrails — what they protect, and what they do not

The Phase 51F guardrails (full description in
`docs/phase51f_parallel_work_guardrails.md`; test file
`tests/test_phase51f_parallel_work_guardrails.py`) protect three
specific things against silent regression during refactor:

1. **Engine outputs of the TUHO and Oborovo reference projects.**
   Pinned values are listed in `tuho_oborovo_validation_summary.md`
   §3 and in the readiness matrix.
2. **Parity-core file content.** Pinned via SHA-256 of
   `app/waterfall_core.py`, `app/project_factories.py`, and the two
   senior-debt extraction CSVs.
3. **One-way import direction.** AST-walked check that
   `app/services/*.py` does not `import main_web` or `import main_api`.

What they do **not** cover (and the reviewer must not infer that they
do):

* They do not validate the model against any external benchmark.
* They do not validate the model for any lender, bank, audit,
  certification, regulatory, or SaaS use.
* They do not protect against intended model changes — those are
  expected to update the pins via the documented intentional-update
  protocol.
* They do not cover routes (`main_web.py`, `main_api.py`) directly;
  they cover the services that those routes call.
* They do not cover generic solar/wind; they cover TUHO (wind) and
  Oborovo (solar) reference projects specifically, and only for the
  five pinned metrics each.
* They do not cover frontend, templates, or static assets.
* They do not guarantee that the pins were correct at the time they
  were set; they guarantee that the model has not silently regressed
  since.

## 5. Known limitations (as of current base SHA)

* **No external validation.** No lender, bank, audit, certification,
  regulatory, or SaaS-grade review has been completed or is implied.
* **rc1 is frozen.** Any bug, gap, or limitation present in `rc1`
  propagates to anything built on it until `rc1` is explicitly
  unfrozen via a future, separately reviewed change.
* **PR #299 is closed.** It is not an active branch and must not be
  treated as a reference for the current state.
* **Parallel track isolation.** Agent A's branch and Agent B's branch
  (this package) do not share files. A reviewer evaluating the current
  base SHA should not assume behavior from either parallel branch.
* **Exploratory features are present in the repository but not
  approved.** Their presence is not an endorsement.
* **G20, R99, R102, `partial_pay_sweep`, and flat / min DSCR sculpting
  are not approved.** Internal references do not constitute approval.
* **No JavaScript financial calculations.** Any client-side numeric
  behavior is presentation only. If a reviewer sees a calculation in
  the templates or static assets, that is a bug, not a feature.
* **No fixture CSV changes are part of this PR.** Any number the
  reviewer sees in this package that depends on a fixture is, by
  construction, not re-baselined by this PR.
* **No schema / migration changes are part of this PR.** The
  reviewer's conclusions should not depend on a schema change
  introduced by either parallel track.
* **Pin correctness is not self-evident.** The Phase 51F pins were set
  on a specific prior commit. They may be wrong, or they may have
  drifted if the pins were updated without the documented intentional
  protocol. The reviewer should confirm that the pins in the test file
  match the SHA-256 of the corresponding files at the base SHA, and
  should run the test file to confirm it passes.

## 6. Test suites and reports the reviewer is pointed at (for reference)

The following test files and reports are relevant to the current
base-SHA review. The reviewer should:

1. Confirm each file exists at the current base SHA.
2. Run each suite and observe results locally.
3. **Not** treat their existence as evidence of passing.

### 6.1 Test files (named for orientation; not a passing claim)

* `tests/test_phase51f_parallel_work_guardrails.py` — **on the base
  SHA**; enforces engine-output golden, parity-core lock, and
  no-service-imports guardrails. The reviewer is asked to run this
  and report outcomes (see §3.4 and readiness matrix A25–A28).
* `tests/test_phase51*.py`, `tests/test_phase52*.py` — earlier Phase
  51 test files. Their presence and current pass/fail status must be
  confirmed by the reviewer at the base SHA. These are **not** owned
  by this PR.
* Other tests under `tests/` that are present on the current base SHA
  — to be enumerated by the reviewer.

### 6.2 Reports

* `reports/phase7_tuho_senior_debt_sizing_extraction.csv` — TUHO
  senior-debt schedule, **parity-core-locked** by Phase 51F.
* `reports/phase23q_oborovo_senior_debt_sizing_extraction.csv` —
  Oborovo senior-debt schedule, **parity-core-locked** by Phase 51F.
* Other reports under `reports/` — to be enumerated by the reviewer;
  the senior-debt CSVs above are the only ones explicitly
  parity-locked.

The reviewer is asked to **list, in their output, every test file and
report they actually opened**, with the SHA they opened it at, rather
than rely on the lists above.

## 7. Required reviewer questions

The reviewer must answer the following questions in their final output.
Answers should cite files and line ranges at the current base SHA.

1. **Scope reality check.** Does the code at the current base SHA
   match the scope described in §2 and §3? If not, where does it
   diverge?
2. **Pin integrity.** Do the Phase 51F pinned golden values in
   `tests/test_phase51f_parallel_work_guardrails.py` actually match
   the model's output when the test is run at the current base SHA?
   List any pin that fails, with the observed value and the
   difference.
3. **Parity-core lock integrity.** Do the SHA-256 hashes in
   `TestParityCoreLock` match the SHA-256 of the corresponding files
   at the current base SHA? If any does not, the guardrail is broken.
4. **No-service-imports integrity.** Does
   `TestNoServiceImportsMainWebOrMainApi` pass at the current base
   SHA? Are there any service files that actually import
   `main_web` or `main_api`?
5. **Validated vs. exploratory split.** Is the §3 split conservative
   enough? In particular, are any items currently in §3.3 ("internally
   tested") actually only exploratory, or vice versa?
6. **Guardrail coverage.** Are the guardrails in `no_go_claims.md`
   actually enforced in the code at the current base SHA (e.g.
   absence of JS financial calculations, blocking of G20, R99, R102,
   `partial_pay_sweep`, flat / min DSCR sculpting)?
7. **TUHO / Oborovo posture.** Is the frozen-template posture
   described in `tuho_oborovo_validation_summary.md` consistent with
   the code and fixtures at the current base SHA?
8. **Test existence vs. test outcomes.** For every test file the
   reviewer opens, do they pass on the current base SHA? List any
   that fail or are skipped.
9. **Documentation / code mismatches.** List any documentation claim
   in this package that is contradicted by the code, fixtures, or
   test outcomes at the current base SHA.
10. **No-go claim reproduction risk.** Does any file in the repo
    (docs, comments, fixtures, reports) reproduce, imply, or hint at
    any claim listed in `no_go_claims.md`?
11. **Parallel-track leakage.** Does this PR (or its base) contain any
    change that touches Agent A's owned files? (Expected answer: no.)

The reviewer is encouraged to add their own questions and to mark any
question they consider inadequately answered by the package.

---

*End of model scope and limitations.*
