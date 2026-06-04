# Phase 57C — Validation bar semantics design

## Status

DRAFT → marked ready → squash merged in the 57C overnight branch
(see `reports/phase57c_validation_bar_semantics_design.json`
for the merge SHA).

This is a **design document only**. No runtime changes are
implemented in 57C. The proposed runtime change is a follow-up
PR (57C-1 or similar) that must be approved by the user before
implementation.

## Current main SHA (start of 57C)

`4036b62dbcffd576b9ce4808123e775bd9726185` (post-57B, Agent B
post-56 / post-57A governance refresh merged)

## Current main SHA (after 57C)

Reported in the 57C combined report.

## rc1 frozen SHA

`b425a0708719eaa5e1d922b1008e5609758e0ad4` — must remain
untouched throughout the 57C-1 future runtime work as well.

## Problem statement

The current `_validation_summary_for_context` helper (in
`main_web.py`, line 904) maps two **permanent governance
guards** — G20 BLOCKED and R99/R102 NOT APPROVED — to
`fail_count` for every project. This is technically true: G20
is BLOCKED in the project state machine, and R99/R102 are NOT
APPROVED for every project that hasn't been through the
(unrun) R99/R102 approval process.

But it creates **permanent red warning / alarm fatigue**:

- Every project shows `fail_count = 2` regardless of any
  per-run or per-model issue.
- The validation bar (UI-2.3) shows red for every project
  by default.
- Users (internal and pilot) cannot tell whether a project's
  red bar means "a real issue you should look at" or "this
  is the permanent governance baseline, ignore it".

This is not a correctness bug (the counts are correct), but
it is a **semantic / UX problem**: the same UI affordance
communicates both "per-run check failed" and "permanent
guard exists", and the user has no way to distinguish them.

## Goal

Design a safer semantics split for the validation summary
bar that:

1. Separates **permanent governance guards** (G20 BLOCKED,
   R99/R102 NOT APPROVED, generic Solar/Wind unvalidated) from
   **per-run validation issues** (per-run/model/check issues).
2. Avoids the word "validated" in positive user-facing context.
3. Uses safe copy: "Governance guard", "Requires review",
   "Model evidence", "Internal check".
4. Does not promote G20/R99/R102 to anything other than
   "Governance guard" status.
5. Defines exact UI states and tests for the future runtime
   PR (57C-1).
6. Does NOT change runtime behavior in 57C.

## Proposed split

### Current: one `validation_summary` dict
```python
{
    "pass_count": ...,
    "warn_count": ...,
    "fail_count": ...,   # includes G20 + R99/R102 always
    "last_validated_at": "",
}
```

### Proposed: two separate dicts

#### 1. `governance_guard_summary` (NEW)

Represents the **permanent, project-scoped governance
state** that does not change with each run. This is the
"baseline" the project was created under.

```python
{
    "g20_status": "BLOCKED" | "OK" | "N/A",
    "r99_r102_status": "NOT APPROVED" | "APPROVED" | "N/A",
    "generic_unvalidated": True | False,  # generic Solar/Wind
    "guarded": True | False,  # ANY guard active?
    "guard_count": int,  # number of active guards
    "labels": [
        # Safe copy, e.g.:
        "Governance guard: G20",
        "Governance guard: R99/R102",
        "Reference only: generic Solar/Wind",
    ],
}
```

#### 2. `validation_summary` (REFINED, existing)

Represents **per-run / per-model / per-check** issues
only. This is what changes with each run.

```python
{
    "pass_count": int,  # checks that passed
    "warn_count": int,  # checks that warned
    "fail_count": int,  # checks that failed
    "last_validated_at": str,  # ISO timestamp
    "labels": [
        # Safe copy, e.g.:
        "Model evidence: 3 internal checks passed",
        "Requires review: 1 internal check failed",
    ],
}
```

### Why this split is the right design

1. **The two state classes have different change cadences.**
   Governance guards are project-scoped and rarely change
   (only when the project moves to a new lifecycle state).
   Per-run checks are computed on each run and change with
   every input edit. Mixing them in a single bar hides this
   distinction.

2. **The two state classes have different remediations.**
   A governance guard (e.g. R99/R102 NOT APPROVED) cannot be
   fixed by the user; it requires an external review process.
   A per-run check failure can be fixed by editing inputs
   and re-running. Conflating them teaches the user that
   "red" can be ignored, which is the opposite of what we
   want for per-run issues.

3. **The two state classes have different audiences.**
   Governance guards are for compliance and pilot review.
   Per-run checks are for the user who is iterating on a
   model. Showing both in the same bar mixes audiences and
   creates noise.

4. **Safe copy is easier to maintain.** "Governance guard"
   is a fact about the system, not a positive claim. "Model
   evidence" is internal check language, not a third-party
   validation seal. "Requires review" is neutral. None of
   these terms appear in the forbidden positive-claim list.

5. **It avoids the word "validated"** in positive user-facing
   context. The existing 55F `last_validated_at` field is
   blank intentionally. The new design uses
   `last_validated_at` only for the per-run `validation_summary`
   and only as a timestamp (not a positive claim).

## Recommended UI states

The proposed UI-2.3 validation bar has three sections:

### Section A: Governance guard summary (NEW, optional)
- Renders ONLY if at least one guard is active.
- Uses neutral/warn visual state (NOT fail).
- Text: "Governance guard: G20" / "Governance guard: R99/R102".
- Action: "Requires review" link to a docs page (e.g. the
  `docs/governance/phase53_stop_go_checklist.md`).
- Pilot docs that describe the prior red bar can be
  refreshed to describe this new neutral/warn state.

### Section B: Per-run validation summary (REFINED, existing)
- Renders ALWAYS.
- Uses pass/warn/fail visual state based on the per-run
  check counts.
- Text: "Model evidence: N internal checks" / "Requires
  review: 1 internal check failed".
- Action: "View run details" link to the audit/run-detail
  page.

### Section C: Last run indicator (existing, separate)
- Renders the timestamp and run id of the last computation.
- Already implemented in UI-2.6.

### Why Section A is neutral/warn, not fail

The decision to render Section A in **neutral/warn** (not
fail) is deliberate:

- The guards are project-scoped and permanent. They are
  not "failures" in the same sense as per-run check
  failures.
- A red bar on every project trains users to ignore red
  bars, which is the opposite of the desired effect for
  per-run issues.
- A neutral/warn bar (yellow / orange) communicates
  "this is a known baseline state, not a per-run issue"
  without the alarm of red.
- If a future change promotes a guard to a per-run check
  (e.g. G20 becomes run-conditional), the design can be
  extended to also include it in the per-run section.

## Safe copy catalog

The new copy avoids the forbidden positive-claim list:

| Old copy (forbidden or alarmist) | New copy (safe) |
|---|---|
| "Validation failed" | "Requires review" |
| "Validated" | "Model evidence" or "Internal check" |
| "Validation summary" | "Internal check summary" |
| "Failed checks" | "Requires review: N internal checks" |
| "Validation bar" | "Internal check bar" |
| "Validation passed" | "Model evidence: N internal checks passed" |
| "Audited" | (removed) |
| "Approved" | "Internal review status: APPROVED" (only in negative context) |
| "G20 BLOCKED" (as headline) | "Governance guard: G20 (BLOCKED)" |
| "R99/R102 NOT APPROVED" (as headline) | "Governance guard: R99/R102 (NOT APPROVED)" |

The new copy uses "Reference", "parity evidence", "Model
evidence", "Internal check", "Requires review", "Governance
guard" — all of which are not in the forbidden positive-claim
list.

## Tests required for the future runtime PR (57C-1)

The future runtime PR must add the following tests to
`tests/test_phase55f_validation_summary_context.py` (or a new
file `tests/test_phase57c1_validation_summary_split.py`):

### Splitting tests
- `test_governance_guard_summary_is_separate_from_validation_summary`
  — assert the index context has both keys, and the
  `validation_summary` no longer includes G20/R99/R102 in
  its counts.
- `test_governance_guard_summary_g20_blocked` — when G20
  status is BLOCKED, `governance_guard_summary.g20_status
  == "BLOCKED"` and `guarded == True`.
- `test_governance_guard_summary_r99_r102_not_approved` —
  same for R99/R102.
- `test_governance_guard_summary_generic_unvalidated` — for
  a generic Solar/Wind project, `generic_unvalidated ==
  True` and the labels list includes "Reference only:
  generic Solar/Wind".
- `test_governance_guard_summary_inactive` — for a fully
  approved, validated project, `governance_guard_summary
  == None` (no banner).
- `test_validation_summary_purely_per_run` — for a project
  with no real per-run issues, `validation_summary.fail_count
  == 0` and `warn_count == 0` (no G20/R99/R102 leak).
- `test_validation_summary_per_run_with_real_issue` — for a
  project with one real per-run issue, `fail_count == 1` and
  `warn_count == 0`.

### UI contract tests (for the partial template)
- `test_validation_bar_shows_governance_guard_section_when_active`
- `test_validation_bar_shows_per_run_section_always`
- `test_validation_bar_does_not_show_red_when_only_guards_active`
- `test_validation_bar_shows_red_when_per_run_check_fails`
- `test_validation_bar_safe_copy_for_each_section`

### Backward-compat / regression tests
- `test_55f_validation_summary_helper_still_returns_dict` —
  the helper signature is unchanged.
- `test_56h1_hoist_preserved` — the `validation_errors`
  local-variable hoist is still in place.
- `test_no_runtime_model_or_formula_changes` — the runtime
  computation is unchanged.
- `test_no_css_or_js_changes` — the visual look is
  consistent (no Tailwind/Alpine/etc.).
- `test_no_g20_r99_r102_promotion` — G20 remains BLOCKED
  in the project state machine; R99/R102 remain NOT
  APPROVED.

### Hard no-go / scope for 57C-1 (future runtime PR)
- No `app/waterfall_core.py` changes.
- No `app/project_factories.py` changes.
- No `app/persistence/` changes (other than the helper
  update if absolutely needed; default NO).
- No `app/services/` changes.
- No `static/app.js` changes.
- No `static/styles.css` changes.
- No schema / migration changes.
- No fixture CSV changes.
- No Tailwind / Alpine / React / Vue / Svelte.
- No G20/R99/R102 guard promotion.
- No generic Solar/Wind runtime work.
- No BESS/Hybrid/Portfolio work.
- No forbidden user-facing claims.
- rc1 frozen.

## Why this design is safer than the alternatives

### Alternative A: keep one summary, change wording
**Rejected.** The semantic problem is that the same UI
affordance communicates two different state classes. Just
changing the wording does not solve the alarm fatigue.

### Alternative B: suppress the validation bar when only guards are active
**Rejected.** Hiding the bar entirely is more alarming
than a neutral/warn state. Users will wonder "is the system
broken?" when the bar disappears. The neutral/warn state
is a clearer signal.

### Alternative C: make G20/R99/R102 pass_count=1 instead of fail
**Rejected.** That would be a forbidden positive claim
(equating "BLOCKED" with "pass"). The state is BLOCKED; the
design must not pretend otherwise.

### Alternative D: introduce a new "lifecycle" status for the project
**Rejected.** That would require a project state machine
change, which is out of scope for the validation bar UX work
and may have downstream consequences (e.g. on persistence,
on the run pipeline).

## Recommended next step

This 57C design is the **prerequisite for the 57C-1 runtime
PR**. The user should:

1. Review this design.
2. Approve / reject / refine.
3. If approved, schedule 57C-1 as a future runtime PR
   (with the test list above).

In the meantime, the 57D, 57E, 57F phases of the overnight
stack do not depend on this design change; they are
docs/report-only or test-only and proceed regardless.

## Open questions for the user

1. **Section A visual state**: is neutral/warn the right
   color? Or should it be a quieter "info" / "blue" state
   to distinguish it from per-run warnings?
2. **Section A action link**: should the "Requires review"
   link go to a docs page, or to a future R99/R102 status
   detail page, or both?
3. **`last_validated_at` semantics**: should this field be
   removed entirely (avoiding "validated" wording), or
   kept as a per-run timestamp (not a positive claim)?
4. **Generic Solar/Wind**: should the `generic_unvalidated`
   flag be a separate banner section, or merged into the
   governance guard section, or both?
5. **Rollout**: should 57C-1 be a single PR, or split into
   (a) helper change + tests, (b) template change +
   visual review?

These are documented as open questions and do not block
the 57C design PR.

## Hard no-go / scope

- No financial model changes.
- No `app/waterfall_core.py` changes.
- No `app/project_factories.py` changes.
- No `app/persistence/` changes.
- No `app/services/` changes.
- No `main_web.py` changes.
- No `static/app.js` changes.
- No `static/styles.css` changes.
- No schema / migration changes.
- No fixture CSV changes.
- No frontend dependency changes.
- No Tailwind / Alpine / React / Vue / Svelte.
- No G20/R99/R102 guard promotion.
- No generic Solar/Wind runtime work.
- No BESS / Hybrid / Portfolio work.
- No forbidden positive user-facing claims.
- rc1 frozen.
