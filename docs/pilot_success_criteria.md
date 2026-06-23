# Pilot Success Criteria

Measurable criteria for judging whether the External Friendly Pilot
succeeded. Intended to be reviewed against the collected
`docs/pilot_feedback_form.md` responses and `docs/pilot_issue_log_template.md`
entries at the end of the pilot round (see `docs/pilot_execution_plan.md`).

## Workflow completion

For each pilot user, record whether they completed each step
unaided (i.e. without needing direct help from the pilot facilitator):

| Step | Target |
|---|---|
| Create project | 100% of pilot users complete unaided |
| Edit assumptions | 100% of pilot users complete unaided |
| Save / reopen project | 100% of pilot users complete unaided |
| Run model | 100% of pilot users complete unaided |
| Create scenario | At least 80% of pilot users complete unaided |
| Compare scenarios | At least 80% of pilot users complete unaided |
| Export workbook | 100% of pilot users complete unaided |

A pilot round where any "Create project / Run model / Export workbook"
target is missed should be treated as **not yet ready** for a wider
pilot, regardless of other scores.

## Trust

From the feedback form ratings (1-5 scale), averaged across pilot
users:

| Measure | Target average |
|---|---|
| Understand validation status (Q7) | ≥ 3.5 |
| Understand known limitations (Q8) | ≥ 3.5 |
| Confidence in outputs / overall trust (Q9) | ≥ 3.0 |

A low trust score combined with high workflow completion suggests a
communication/wording problem, not a functionality problem — see
`docs/pilot_issue_log_template.md` categories **Validation** and
**Documentation**.

## Adoption signal

From the closing questions on the feedback form:

| Measure | Target |
|---|---|
| Would use again (1-5) | ≥ 3.5 average |
| Would recommend (1-5) | ≥ 3.5 average |
| Would replace a spreadsheet for early-stage modelling | At least 1 "yes" or "not yet" (not all "no") across the pilot group |

## Issue severity threshold

| Severity found during pilot | Acceptable outcome |
|---|---|
| Blocker | Zero open Blockers at the end of the pilot round |
| Major | All Major issues triaged with an owner and status by end of round |
| Minor / Suggestion | Logged, no action required before declaring pilot success |

## Overall pilot round verdict

At the end of a pilot round, classify the result as one of:

- **Success** — workflow targets met, trust/adoption averages met,
  zero open Blockers.
- **Success with follow-up** — workflow and trust targets met, but one
  or more Major issues remain open with an owner and plan.
- **Not ready** — any workflow target missed, trust average below
  target, or an unresolved Blocker.

This verdict feeds directly into the follow-up review step in
`docs/pilot_execution_plan.md`.
