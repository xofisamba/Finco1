# TUHO / Oborovo — Frozen-Template and Phase 51F Pin Summary

This file describes the **TUHO / Oborovo** frozen-template reference
case: what it is, what is and is not pinned, what the Phase 51F
guardrails cover for it, and what the external reviewer is being asked
to check.

TUHO / Oborovo is treated as a **frozen reference template** for
regression protection, not as a live deal and not as evidence of any
external validation.

---

## 1. What TUHO / Oborovo is

TUHO / Oborovo are two specific project configurations constructed by
`app/project_factories.py`:

* `create_default_tuho_wind1()` — TUHO Wind 1 (35 MW × 5 turbines).
* `create_default_oborovo()` — Oborovo Solar PV (75.26 MWp).

Their purpose is to give the project a stable, internally agreed-upon
input set and expected output shape against which:

* internal tests can be written;
* future refactors (route extraction, service extraction, `/save-run`,
  repository extraction) can be checked for unintended output drift;
* the Phase 51F engine-output golden guardrail can pin specific
  numeric outputs.

TUHO / Oborovo are **not**:

* a real-world executed transaction;
* a representation of any actual TUHO or Oborovo entity's financial
  position;
* a representation of any third party's data;
* a model claim about any specific technology, market, or jurisdiction;
* evidence of any external validation, certification, or approval;
* a guarantee that the entire model is correct — only that this
  specific template behaves as pinned.

## 2. Frozen-template posture

* The TUHO / Oborovo input set is in `app/project_factories.py`. Any
  change to the factory functions is a model change and must follow
  the Phase 51F intentional-update protocol (see
  `docs/phase51f_parallel_work_guardrails.md`).
* The senior-debt schedule CSVs at
  `reports/phase7_tuho_senior_debt_sizing_extraction.csv` and
  `reports/phase23q_oborovo_senior_debt_sizing_extraction.csv` are
  parity-core-locked by Phase 51F.
* The reviewer must **not** propose changes to TUHO / Oborovo as part
  of this review. Any change requires a separate, future PR with its
  own review path.
* If a refactor (e.g. Agent A's `/save-run` work, repository
  extraction) would alter TUHO / Oborovo outputs, that change must be
  visible in that track's diff and is not the responsibility of this
  package.

## 3. Phase 51F pinned golden values (engine-output golden guardrail)

The Phase 51F engine-output golden guardrail pins the following values
for TUHO and Oborovo. Source:
`tests/test_phase51f_parallel_work_guardrails.py` (on the current base
SHA).

### 3.1 TUHO (Wind 1, 35 MW × 5 turbines)

| Field | Golden | Tolerance | Description |
|---|---|---|---|
| First finite DSCR | 1.450695 | ±0.001 | Period idx 0, year 1 |
| First distribution op idx | 35 | exact | First op period with positive distribution_keur |
| Total operating periods | 61 | exact | Semiannual, 30y + construction overhang |
| OpEx total | 85,408.27 kEUR | ±0.5 kEUR | Sum over operating periods |
| OpEx year 1 (semiannual sum) | 1,998.01 kEUR | ±0.5 kEUR | First 2 operating periods |

### 3.2 Oborovo (Solar PV, 75.26 MWp)

| Field | Golden | Tolerance | Description |
|---|---|---|---|
| First finite DSCR | 1.150038 | ±0.001 | Period idx 0, year 1 |
| First distribution op idx | 39 | exact | First op period with positive distribution_keur |
| Total operating periods | 60 | exact | Semiannual, 30y + construction overhang |
| OpEx total | 48,847.50 kEUR | ±0.5 kEUR | Sum over operating periods |
| OpEx year 1 (semiannual sum) | 1,338.56 kEUR | ±0.5 kEUR | First 2 operating periods |

### 3.3 What "pinned" means and does not mean

**Means:**

* Any silent change to these values during a refactor will fail the
  Phase 51F test on the base SHA.
* An intentional change requires updating the pin via the documented
  protocol.

**Does not mean:**

* The values are externally verified. They are pinned against
  regression, not validated against any external benchmark.
* The values are accurate in any absolute sense. They reflect the
  current model's output, not any third-party truth.
* The model is correct beyond these five values per project. The pin
  covers only what it covers.

## 4. Phase 51F parity-core lock (TUHO / Oborovo)

The Phase 51F parity-core lock guardrail pins the SHA-256 of the
following files at the current base SHA:

| File | Role |
|---|---|
| `app/waterfall_core.py` | Parity-core engine (TUHO/Oborovo and others) |
| `app/project_factories.py` | Factory that produces TUHO and Oborovo |
| `reports/phase7_tuho_senior_debt_sizing_extraction.csv` | TUHO senior-debt schedule |
| `reports/phase23q_oborovo_senior_debt_sizing_extraction.csv` | Oborovo senior-debt schedule |

The reviewer must confirm that the SHA-256 hashes in the test file
match the SHA-256 of the corresponding files at the current base SHA,
and that the parametrized parity-core tests pass when run.

If a hash does not match, the guardrail has already been broken — the
lock did not detect the change before the test was run, or the pin
itself is stale. Either case is a real issue and must be flagged.

## 5. What is in scope for the reviewer to verify

The reviewer is asked to verify, **at the current base SHA**, that:

1. The Phase 51F engine-output golden values match the model's
   observed output for both TUHO and Oborovo.
2. The Phase 51F parity-core lock SHA-256 values match the actual
   SHA-256 of the four files at the base SHA.
3. The no-service-imports guardrail passes (this does not directly
   touch TUHO / Oborovo, but is part of the same Phase 51F test
   file).
4. The TUHO / Oborovo input set in `app/project_factories.py` is
   unchanged from the project's documented frozen-template
   definition.
5. The model behavior for TUHO / Oborovo is consistent with the
   `model_scope_and_limitations.md` split, i.e. TUHO / Oborovo is
   treated as pinned (not externally validated).

## 6. What is explicitly out of scope

* The reviewer is **not** being asked to:
  * validate TUHO / Oborovo against any real-world data;
  * certify TUHO / Oborovo for any external use;
  * recommend changes to the frozen template;
  * reconcile TUHO / Oborovo with any third-party dataset;
  * extend TUHO / Oborovo to additional scenarios (e.g. generic
    solar / wind) — those are exploratory and unvalidated;
  * use TUHO / Oborovo as a basis for any G20, R99, R102,
    `partial_pay_sweep`, or flat / min DSCR sculpting claim.

## 7. What TUHO / Oborovo does NOT prove

The presence and pass-state of TUHO / Oborovo does **not** prove any
of the following, and the reviewer must not infer any of them:

* External validation of the model.
* Suitability for any specific lender, bank, audit, certification,
  regulatory, or SaaS use case.
* Coverage of edge cases beyond what the template's inputs exercise.
* Accuracy of any inputs that are themselves approximations or
  placeholders.
* Compatibility with future refactors on parallel branches.
* Bankability, "investment-grade" status, or any similar external
  claim.
* That the model as a whole is correct — only that this specific
  template behaves as pinned.

## 8. Required reviewer questions (TUHO / Oborovo specific)

The reviewer must answer the following, citing files and line ranges
at the current base SHA:

1. **Engine-output pin integrity.** Do the pinned TUHO and Oborovo
   values in
   `tests/test_phase51f_parallel_work_guardrails.py` match the
   model's observed output when the test is run at the current base
   SHA? List any pin that fails, with observed value, golden value,
   tolerance, and the resulting delta.
2. **Parity-core lock integrity.** Do the SHA-256 hashes in
   `TestParityCoreLock` match the SHA-256 of the four parity-core
   files at the current base SHA? Compute the actual hashes
   yourself, do not trust the package or the test file's recorded
   hashes blindly. Note that Phase 51G-1 (current main) is
   characterization only and did not modify any parity-core file;
   the four pinned files (`app/waterfall_core.py`,
   `app/project_factories.py`, and the two senior-debt extraction
   CSVs) are unchanged from `a541d447`.
3. **Test run.** Did the reviewer run
   `tests/test_phase51f_parallel_work_guardrails.py` and observe it
   pass? If the test was skipped (e.g. engine not importable in the
   reviewer's environment), which guardrails were skipped and which
   were not?
4. **Test relevance.** Does the engine-output golden test exercise
   TUHO / Oborovo end-to-end, or only pieces of it? Identify any
   gap in the pin coverage.
5. **Refactor sensitivity.** Without modifying TUHO / Oborovo, does
   the reviewer see any code in the current base SHA that would
   produce different TUHO / Oborovo outputs than the pinned values?
   If so, where?
6. **No-go leakage.** Does any TUHO / Oborovo-related file, fixture,
   report, or comment reproduce, imply, or hint at any claim listed
   in `no_go_claims.md`?
7. **Template change proposals.** The reviewer is asked **not** to
   propose template changes in this review. If they believe a change
   is required, they should flag it as a follow-up rather than a
   blocker of this PR.
8. **Parallel-track effect.** Does the parallel Agent A track
   propose any TUHO / Oborovo change? The reviewer is asked only to
   note this if it is visible at the base SHA; it is otherwise out of
   scope.

## 9. Where the reviewer should look (named paths, no passing claim)

* `app/project_factories.py` — defines `create_default_tuho_wind1` and
  `create_default_oborovo`.
* `app/waterfall_core.py` — produces the model output that the
  engine-output golden guardrail tests.
* `reports/phase7_tuho_senior_debt_sizing_extraction.csv` — TUHO
  senior-debt schedule (parity-core-locked).
* `reports/phase23q_oborovo_senior_debt_sizing_extraction.csv` —
  Oborovo senior-debt schedule (parity-core-locked).
* `tests/test_phase51f_parallel_work_guardrails.py` — the test file
  that enforces the pins and the no-service-imports guardrail.
* `docs/phase51f_parallel_work_guardrails.md` — project documentation
  of the Phase 51F guardrails and the intentional-update protocol.

The reviewer should enumerate, in their output, every TUHO /
Oborovo-related file they actually opened and the SHA at which they
opened it.

## 10. Package-author pre-flight run (informational only)

The package author executed the Phase 51F test file at the current
base SHA in a fresh environment with the project's `requirements.txt`
installed, before sending the package to the reviewer. The result is
recorded here for the reviewer's reference, **not** as a substitute
for the reviewer's own run.

* Command: `python3 -m pytest tests/test_phase51f_parallel_work_guardrails.py -v`
* Base SHA at pre-flight: `a541d447063cf288b1a9ea0a7bbf199755e40d53` (Phase 51F, the base when the pre-flight was run)
* Current base SHA: `2e41b24f8c47ec544e1ef52e35084646df4d4d8f` (Phase 51G-1, current; pre-flight was not re-run at this base because Phase 51G-1 does not modify any parity-core file or any TUHO/Oborovo pin)
* Result: **21 passed in 0.81s** at the pre-flight base (5 TUHO engine-output golden + 5
  Oborovo engine-output golden + 4 parametrized parity-core lock + 1
  no-service-imports + 6 guardrail-inventory and docs-cross-check
  tests).
* Interpretation: at the moment the package was prepared, the three
  Phase 51F guardrails (engine-output golden, parity-core lock,
  no-service-imports) all fired green on the current base SHA. The
  pins in the test file matched the model's observed output for both
  TUHO and Oborovo, the SHA-256 of the four parity-core files matched
  their recorded pins, and no `app/services/*.py` file imported
  `main_web` or `main_api`.

The reviewer is asked to re-run the tests in their own environment
and report results, with their own SHA verification statement
attached. The package-author pre-flight run is **not** reviewer
evidence; it is a sanity check that the package's description of the
guardrails is at least consistent with what the test file does.

---

*End of TUHO / Oborovo pin summary.*
